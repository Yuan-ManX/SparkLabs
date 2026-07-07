"""
SparkLabs Agent - Inter-Agent Goal Negotiation Engine with Commitment Ledger

This module implements a structured goal negotiation system that allows AI
agents operating inside the SparkLabs AI-native game engine to propose,
debate, pledge resources, and formally commit to shared goals. Unlike the
general-purpose voting-focused negotiation module, this engine is
specifically designed for goal-oriented multi-agent collaboration, tracking
explicit pledges and commitments throughout the negotiation lifecycle.

Core concepts:

  1. Goal Proposals with Priority
       Every goal begins as a :class:`GoalProposal` issued by a proposer
       agent. Each proposal carries a :class:`GoalPriority` rating and a
       list of required participants who must be involved to achieve it.

  2. Phased Negotiation Lifecycle
       Negotiations move through discrete :class:`NegotiationPhase` values
       (PROPOSAL -> COUNTER -> ACCEPT/REJECT -> COMMIT) so that the
       structure of debate is observable and auditable.

  3. Explicit Pledges
       During a negotiation, participants make :class:`Pledge` entries of
       various :class:`PledgeType` values (RESOURCE, ACTION, TIMELINE,
       COOPERATION, BLOCKING). Pledges have a commitment strength in [0, 1]
       and progress through ACTIVE -> FULFILLED / BROKEN / RELEASED states.

  4. Formal Commitments
       Agents may convert their pledges into a :class:`Commitment` which
       carries an aggregate commitment score and is registered against a
       goal. Commitments are the auditable record of who is on the hook.

  5. Progress Tracking
       Each goal has an associated :class:`GoalProgress` record capturing
       current progress, blockers, and estimated completion. Progress feeds
       the engine's statistics and success-rate calculation.

Architecture:
  GoalNegotiationLedgerEngine (Singleton, double-checked locking with threading.RLock)
    |-- GoalProposal            -- an initial goal proposal
    |-- Pledge                  -- a specific commitment of resource/action
    |-- Negotiation             -- a structured multi-agent debate
    |-- Commitment              -- a formal, registered commitment
    |-- GoalProgress            -- progress and blockers for a goal
    |-- GoalRecord              -- aggregate record for a goal
    |-- NegotiationStats        -- aggregate engine statistics
    |-- GoalNegotiationSnapshot -- complete engine state snapshot
    |-- GoalNegotiationEvent    -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_GOALS: int = 2000
_MAX_PROPOSALS: int = 2000
_MAX_NEGOTIATIONS: int = 2000
_MAX_PLEDGES: int = 5000
_MAX_COMMITMENTS: int = 5000
_MAX_PROGRESS_ENTRIES: int = 2000
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Scoring and default constants
# ---------------------------------------------------------------------------

_DEFAULT_COMMITMENT_STRENGTH: float = 0.5
_DEFAULT_PROGRESS: float = 0.0
_SUCCESS_RATE_FLOOR: float = 0.0
_SUCCESS_RATE_CEILING: float = 1.0
_MAX_COUNTER_PROPOSALS: int = 20
_MAX_PROPOSAL_HISTORY: int = 20


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id() -> str:
    """Generate a short unique identifier for a record."""
    return uuid.uuid4().hex[:16]


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds.

    Python dicts preserve insertion order (3.7+), so the first key returned
    by iteration is the oldest. This implements FIFO eviction.
    """
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    while len(store) > max_size:
        store.pop(0)


def _parse_priority(value: str) -> "GoalPriority":
    """Parse a priority string into a :class:`GoalPriority` enum.

    Falls back to :attr:`GoalPriority.MEDIUM` when the value is unknown.
    """
    if not value:
        return GoalPriority.MEDIUM
    normalized = str(value).strip().lower()
    for member in GoalPriority:
        if member.value == normalized:
            return member
    return GoalPriority.MEDIUM


def _parse_phase(value: str) -> "NegotiationPhase":
    """Parse a phase string into a :class:`NegotiationPhase` enum.

    Falls back to :attr:`NegotiationPhase.PROPOSAL` when unknown.
    """
    if not value:
        return NegotiationPhase.PROPOSAL
    normalized = str(value).strip().lower()
    for member in NegotiationPhase:
        if member.value == normalized:
            return member
    return NegotiationPhase.PROPOSAL


def _parse_pledge_status(value: str) -> "PledgeStatus":
    """Parse a pledge status string into a :class:`PledgeStatus` enum."""
    if not value:
        return PledgeStatus.ACTIVE
    normalized = str(value).strip().lower()
    for member in PledgeStatus:
        if member.value == normalized:
            return member
    return PledgeStatus.ACTIVE


def _parse_goal_status(value: str) -> "GoalStatus":
    """Parse a goal status string into a :class:`GoalStatus` enum."""
    if not value:
        return GoalStatus.PROPOSED
    normalized = str(value).strip().lower()
    for member in GoalStatus:
        if member.value == normalized:
            return member
    return GoalStatus.PROPOSED


def _parse_pledge_type(value: str) -> "PledgeType":
    """Parse a pledge type string into a :class:`PledgeType` enum."""
    if not value:
        return PledgeType.ACTION
    normalized = str(value).strip().lower()
    for member in PledgeType:
        if member.value == normalized:
            return member
    return PledgeType.ACTION


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class GoalPriority(Enum):
    """Priority classification of a proposed goal."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class GoalStatus(Enum):
    """Lifecycle status of a goal."""
    PROPOSED = "proposed"
    NEGOTIATING = "negotiating"
    PLEDGED = "pledged"
    COMMITTED = "committed"
    IN_PROGRESS = "in_progress"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"
    BLOCKED = "blocked"


class PledgeStatus(Enum):
    """Lifecycle status of a pledge."""
    ACTIVE = "active"
    FULFILLED = "fulfilled"
    BROKEN = "broken"
    RELEASED = "released"


class NegotiationPhase(Enum):
    """Current phase of a structured negotiation."""
    PROPOSAL = "proposal"
    COUNTER = "counter"
    ACCEPT = "accept"
    REJECT = "reject"
    COMMIT = "commit"


class PledgeType(Enum):
    """The kind of commitment a pledge represents."""
    RESOURCE = "resource"
    ACTION = "action"
    TIMELINE = "timeline"
    COOPERATION = "cooperation"
    BLOCKING = "blocking"


class GoalNegotiationEventKind(Enum):
    """Observable lifecycle events emitted by the negotiation engine."""
    GOAL_PROPOSED = "goal_proposed"
    GOAL_ACCEPTED = "goal_accepted"
    GOAL_REJECTED = "goal_rejected"
    PLEDGE_MADE = "pledge_made"
    PLEDGE_FULFILLED = "pledge_fulfilled"
    PLEDGE_BROKEN = "pledge_broken"
    NEGOTIATION_OPENED = "negotiation_opened"
    NEGOTIATION_CLOSED = "negotiation_closed"
    COMMITMENT_REGISTERED = "commitment_registered"
    GOAL_ACHIEVED = "goal_achieved"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class GoalProposal:
    """An initial goal proposal made by a proposer agent."""
    proposal_id: str
    goal_id: str
    proposer_id: str
    title: str
    description: str
    priority: GoalPriority
    required_participants: List[str]
    proposed_at: str
    deadline: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this proposal to a JSON-friendly dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "goal_id": self.goal_id,
            "proposer_id": self.proposer_id,
            "title": self.title,
            "description": self.description,
            "priority": self.priority.value,
            "required_participants": list(self.required_participants),
            "proposed_at": self.proposed_at,
            "deadline": self.deadline,
        }


@dataclass
class Pledge:
    """A specific commitment made by an agent during a negotiation."""
    pledge_id: str
    pledger_id: str
    goal_id: str
    pledge_type: PledgeType
    description: str
    commitment_strength: float
    resource_amount: Optional[str]
    action_steps: List[str]
    status: PledgeStatus
    created_at: str
    fulfilled_at: Optional[str] = None
    broken_at: Optional[str] = None
    negotiation_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pledge to a JSON-friendly dictionary."""
        return {
            "pledge_id": self.pledge_id,
            "pledger_id": self.pledger_id,
            "goal_id": self.goal_id,
            "pledge_type": self.pledge_type.value,
            "description": self.description,
            "commitment_strength": self.commitment_strength,
            "resource_amount": self.resource_amount,
            "action_steps": list(self.action_steps),
            "status": self.status.value,
            "created_at": self.created_at,
            "fulfilled_at": self.fulfilled_at,
            "broken_at": self.broken_at,
            "negotiation_id": self.negotiation_id,
        }


@dataclass
class Negotiation:
    """A structured multi-agent negotiation for a specific goal."""
    negotiation_id: str
    goal_id: str
    initiator_id: str
    participants: List[str]
    phase: NegotiationPhase
    proposal_history: List[str]
    counter_proposals: List[str]
    current_state: str
    opened_at: str
    closed_at: Optional[str] = None
    outcome: str = ""
    summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this negotiation to a JSON-friendly dictionary."""
        return {
            "negotiation_id": self.negotiation_id,
            "goal_id": self.goal_id,
            "initiator_id": self.initiator_id,
            "participants": list(self.participants),
            "phase": self.phase.value,
            "proposal_history": list(self.proposal_history),
            "counter_proposals": list(self.counter_proposals),
            "current_state": self.current_state,
            "opened_at": self.opened_at,
            "closed_at": self.closed_at,
            "outcome": self.outcome,
            "summary": self.summary,
        }


@dataclass
class Commitment:
    """A formal, registered commitment by an agent to a goal."""
    commitment_id: str
    agent_id: str
    goal_id: str
    pledge_ids: List[str]
    commitment_score: float
    status: str
    registered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this commitment to a JSON-friendly dictionary."""
        return {
            "commitment_id": self.commitment_id,
            "agent_id": self.agent_id,
            "goal_id": self.goal_id,
            "pledge_ids": list(self.pledge_ids),
            "commitment_score": self.commitment_score,
            "status": self.status,
            "registered_at": self.registered_at,
        }


@dataclass
class GoalProgress:
    """Progress and blocker information for a goal."""
    goal_id: str
    current_progress: float
    blockers: List[str]
    last_updated: str
    estimated_completion: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this progress entry to a JSON-friendly dictionary."""
        return {
            "goal_id": self.goal_id,
            "current_progress": self.current_progress,
            "blockers": list(self.blockers),
            "last_updated": self.last_updated,
            "estimated_completion": self.estimated_completion,
        }


@dataclass
class GoalRecord:
    """An aggregate record describing a goal and its current state."""
    goal_id: str
    title: str
    description: str
    proposer_id: str
    priority: GoalPriority
    status: GoalStatus
    negotiation_id: Optional[str]
    pledges: List[Pledge]
    commitments: List[Commitment]
    progress: Optional[GoalProgress]
    created_at: str
    achieved_at: Optional[str] = None
    abandoned_reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this goal record to a JSON-friendly dictionary."""
        return {
            "goal_id": self.goal_id,
            "title": self.title,
            "description": self.description,
            "proposer_id": self.proposer_id,
            "priority": self.priority.value,
            "status": self.status.value,
            "negotiation_id": self.negotiation_id,
            "pledges": [p.to_dict() for p in self.pledges],
            "commitments": [c.to_dict() for c in self.commitments],
            "progress": self.progress.to_dict() if self.progress else None,
            "created_at": self.created_at,
            "achieved_at": self.achieved_at,
            "abandoned_reason": self.abandoned_reason,
        }


@dataclass
class NegotiationStats:
    """Aggregate statistics about the goal negotiation engine."""
    total_goals: int
    total_negotiations: int
    total_pledges: int
    active_pledges: int
    broken_pledges: int
    goals_achieved: int
    success_rate: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_goals": self.total_goals,
            "total_negotiations": self.total_negotiations,
            "total_pledges": self.total_pledges,
            "active_pledges": self.active_pledges,
            "broken_pledges": self.broken_pledges,
            "goals_achieved": self.goals_achieved,
            "success_rate": self.success_rate,
        }


@dataclass
class GoalNegotiationEvent:
    """An observable lifecycle event emitted by the negotiation engine."""
    event_id: str
    kind: GoalNegotiationEventKind
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


@dataclass
class GoalNegotiationSnapshot:
    """A complete snapshot of the goal negotiation engine state."""
    initialized: bool
    goals: List[GoalRecord]
    proposals: List[GoalProposal]
    negotiations: List[Negotiation]
    pledges: List[Pledge]
    commitments: List[Commitment]
    events: List[GoalNegotiationEvent]
    stats: NegotiationStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "goals": [g.to_dict() for g in self.goals],
            "proposals": [p.to_dict() for p in self.proposals],
            "negotiations": [n.to_dict() for n in self.negotiations],
            "pledges": [p.to_dict() for p in self.pledges],
            "commitments": [c.to_dict() for c in self.commitments],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Goal Negotiation Ledger Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class GoalNegotiationLedgerEngine:
    """Inter-agent goal negotiation engine with an explicit commitment ledger.

    The engine accepts goal proposals, opens structured negotiations with
    phased state transitions, tracks individual pledges, registers formal
    commitments, and monitors progress toward each goal. All operations
    are thread-safe and the engine is a singleton accessed via
    :meth:`get_instance` or the module-level
    :func:`get_goal_negotiation_ledger` helper.

    Usage:
        engine = get_goal_negotiation_ledger()
        proposal = engine.propose_goal(
            proposer_id="architect_agent",
            title="Build the fortress",
            priority="high",
        )
        negotiation = engine.open_negotiation(
            goal_id=proposal.goal_id,
            initiator_id="architect_agent",
            participants=["warrior", "mage", "builder"],
        )
        engine.make_pledge(
            negotiation_id=negotiation.negotiation_id,
            pledger_id="warrior",
            pledge_type="action",
            description="Will defend the build site",
            commitment_strength=0.8,
        )
    """

    _instance: Optional["GoalNegotiationLedgerEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) -----------------------------

    def __new__(cls) -> "GoalNegotiationLedgerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        # Fast path: already initialized singleton.
        if self._initialized:
            return
        with self._lock:
            # Second check inside the lock to guard against concurrent
            # construction.
            if self._initialized:
                return

            # Primary stores keyed by id where it makes sense; lists where
            # ordering matters.
            self._goals: Dict[str, GoalRecord] = {}
            self._proposals: Dict[str, GoalProposal] = {}
            self._negotiations: Dict[str, Negotiation] = {}
            self._pledges: Dict[str, Pledge] = {}
            self._commitments: Dict[str, Commitment] = {}
            self._progress: Dict[str, GoalProgress] = {}
            self._events: List[GoalNegotiationEvent] = []

            # Per-goal pledge index to avoid scanning all pledges on
            # every goal lookup.
            self._pledge_index: Dict[str, List[str]] = {}
            self._commitment_index: Dict[str, List[str]] = {}

            # Aggregate counters.
            self._goal_counter: int = 0
            self._negotiation_counter: int = 0
            self._pledge_counter: int = 0
            self._commitment_counter: int = 0

            self._initialized: bool = True

            # Seed baseline negotiation data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "GoalNegotiationLedgerEngine":
        """Return the singleton GoalNegotiationLedgerEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Goal proposal and lookup
    # ------------------------------------------------------------------

    def propose_goal(
        self,
        proposer_id: str,
        title: str,
        description: str = "",
        priority: str = "medium",
        required_participants: Optional[List[str]] = None,
        deadline: Optional[str] = None,
    ) -> GoalProposal:
        """Propose a new goal to the negotiation ledger.

        A new :class:`GoalRecord` is created in the ``PROPOSED`` state and an
        associated :class:`GoalProposal` is registered.

        Args:
            proposer_id: Identifier of the agent proposing the goal.
            title: Short title of the goal.
            description: Free-form description of the goal.
            priority: Priority string. Accepted values correspond to
                :class:`GoalPriority` values (``critical``, ``high``,
                ``medium``, ``low``). Unknown values default to ``medium``.
            required_participants: Optional list of agent ids that must be
                involved to achieve the goal.
            deadline: Optional ISO-8601 deadline for the goal.

        Returns:
            The newly created :class:`GoalProposal` associated with the new
            goal.
        """
        with self._lock:
            parsed_priority = _parse_priority(priority)
            now = _now()
            goal_id = _new_id()
            proposal = GoalProposal(
                proposal_id=_new_id(),
                goal_id=goal_id,
                proposer_id=proposer_id,
                title=title,
                description=description or "",
                priority=parsed_priority,
                required_participants=list(required_participants) if required_participants else [],
                proposed_at=now,
                deadline=deadline,
            )
            goal = GoalRecord(
                goal_id=goal_id,
                title=title,
                description=description or "",
                proposer_id=proposer_id,
                priority=parsed_priority,
                status=GoalStatus.PROPOSED,
                negotiation_id=None,
                pledges=[],
                commitments=[],
                progress=None,
                created_at=now,
                achieved_at=None,
                abandoned_reason="",
            )
            self._goals[goal_id] = goal
            self._proposals[proposal.proposal_id] = proposal
            self._pledge_index[goal_id] = []
            self._commitment_index[goal_id] = []

            self._goal_counter += 1
            _evict_fifo_dict(self._goals, _MAX_GOALS)
            _evict_fifo_dict(self._proposals, _MAX_PROPOSALS)

            self._record_event(
                GoalNegotiationEventKind.GOAL_PROPOSED,
                {
                    "goal_id": goal_id,
                    "proposal_id": proposal.proposal_id,
                    "proposer_id": proposer_id,
                    "priority": parsed_priority.value,
                    "title": title,
                },
            )
            return proposal

    def list_goals(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> List[GoalRecord]:
        """List goals, optionally filtered by status and priority.

        Args:
            status: When provided, only goals with this status are returned.
                Accepts either a :class:`GoalStatus` member or its value.
            priority: When provided, only goals with this priority are
                returned. Accepts either a :class:`GoalPriority` member or
                its value.

        Returns:
            A list of :class:`GoalRecord` objects in insertion order.
        """
        with self._lock:
            parsed_status: Optional[GoalStatus] = None
            if status is not None:
                if isinstance(status, GoalStatus):
                    parsed_status = status
                else:
                    parsed_status = _parse_goal_status(str(status))

            parsed_priority: Optional[GoalPriority] = None
            if priority is not None:
                if isinstance(priority, GoalPriority):
                    parsed_priority = priority
                else:
                    parsed_priority = _parse_priority(str(priority))

            results: List[GoalRecord] = []
            for goal in self._goals.values():
                if parsed_status is not None and goal.status != parsed_status:
                    continue
                if parsed_priority is not None and goal.priority != parsed_priority:
                    continue
                results.append(self._hydrate_goal(goal))
            return results

    def get_goal(self, goal_id: str) -> Optional[GoalRecord]:
        """Return a single goal record by id, or None if not found."""
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            return self._hydrate_goal(goal)

    def _hydrate_goal(self, goal: GoalRecord) -> GoalRecord:
        """Return a copy of a goal with live pledges/commitments/progress.

        Assumes the caller already holds ``self._lock``.
        """
        pledge_ids = self._pledge_index.get(goal.goal_id, [])
        pledges = [self._pledges[pid] for pid in pledge_ids if pid in self._pledges]
        commitment_ids = self._commitment_index.get(goal.goal_id, [])
        commitments = [
            self._commitments[cid] for cid in commitment_ids if cid in self._commitments
        ]
        progress = self._progress.get(goal.goal_id)
        return GoalRecord(
            goal_id=goal.goal_id,
            title=goal.title,
            description=goal.description,
            proposer_id=goal.proposer_id,
            priority=goal.priority,
            status=goal.status,
            negotiation_id=goal.negotiation_id,
            pledges=pledges,
            commitments=commitments,
            progress=progress,
            created_at=goal.created_at,
            achieved_at=goal.achieved_at,
            abandoned_reason=goal.abandoned_reason,
        )

    # ------------------------------------------------------------------
    # Negotiation lifecycle
    # ------------------------------------------------------------------

    def open_negotiation(
        self,
        goal_id: str,
        initiator_id: str,
        participants: List[str],
    ) -> Optional[Negotiation]:
        """Open a structured negotiation for a goal.

        A new :class:`Negotiation` is created in the ``PROPOSAL`` phase and
        the associated goal transitions to ``NEGOTIATING``.

        Args:
            goal_id: Identifier of the goal to negotiate.
            initiator_id: Identifier of the agent opening the negotiation.
            participants: List of agent ids participating in the negotiation.

        Returns:
            The newly created :class:`Negotiation`, or ``None`` if the goal
            does not exist.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            now = _now()
            participants_list = [initiator_id] + [p for p in participants if p != initiator_id]
            negotiation = Negotiation(
                negotiation_id=_new_id(),
                goal_id=goal_id,
                initiator_id=initiator_id,
                participants=list(participants_list),
                phase=NegotiationPhase.PROPOSAL,
                proposal_history=[],
                counter_proposals=[],
                current_state="opened",
                opened_at=now,
                closed_at=None,
                outcome="",
                summary="",
            )
            self._negotiations[negotiation.negotiation_id] = negotiation
            self._negotiation_counter += 1
            _evict_fifo_dict(self._negotiations, _MAX_NEGOTIATIONS)

            goal.negotiation_id = negotiation.negotiation_id
            if goal.status == GoalStatus.PROPOSED:
                goal.status = GoalStatus.NEGOTIATING

            self._record_event(
                GoalNegotiationEventKind.NEGOTIATION_OPENED,
                {
                    "negotiation_id": negotiation.negotiation_id,
                    "goal_id": goal_id,
                    "initiator_id": initiator_id,
                    "participants": list(participants_list),
                },
            )
            return negotiation

    def get_negotiation(self, negotiation_id: str) -> Optional[Negotiation]:
        """Return a single negotiation by id, or None if not found."""
        with self._lock:
            return self._negotiations.get(negotiation_id)

    def list_negotiations(
        self,
        phase: Optional[str] = None,
        goal_id: Optional[str] = None,
    ) -> List[Negotiation]:
        """List negotiations, optionally filtered by phase and goal id."""
        with self._lock:
            parsed_phase: Optional[NegotiationPhase] = None
            if phase is not None:
                if isinstance(phase, NegotiationPhase):
                    parsed_phase = phase
                else:
                    parsed_phase = _parse_phase(str(phase))
            results: List[Negotiation] = []
            for neg in self._negotiations.values():
                if parsed_phase is not None and neg.phase != parsed_phase:
                    continue
                if goal_id is not None and neg.goal_id != goal_id:
                    continue
                results.append(neg)
            return results

    def submit_counter_proposal(
        self,
        negotiation_id: str,
        agent_id: str,
        counter_text: str,
    ) -> Optional[Negotiation]:
        """Submit a counter-proposal in a negotiation.

        The negotiation transitions to the ``COUNTER`` phase. The counter
        text is appended to ``counter_proposals`` and ``proposal_history``.

        Args:
            negotiation_id: Identifier of the target negotiation.
            agent_id: Identifier of the agent submitting the counter.
            counter_text: Free-form text of the counter-proposal.

        Returns:
            The updated :class:`Negotiation`, or ``None`` if not found or
            already closed.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return None
            if neg.closed_at is not None:
                return None
            neg.phase = NegotiationPhase.COUNTER
            neg.counter_proposals.append(
                f"{agent_id}: {counter_text}" if counter_text else agent_id
            )
            # Cap history lists to avoid unbounded growth.
            if len(neg.counter_proposals) > _MAX_COUNTER_PROPOSALS:
                neg.counter_proposals = neg.counter_proposals[-_MAX_COUNTER_PROPOSALS:]
            neg.proposal_history.append(
                f"{_now()}::counter::{agent_id}::{counter_text}" if counter_text
                else f"{_now()}::counter::{agent_id}"
            )
            if len(neg.proposal_history) > _MAX_PROPOSAL_HISTORY:
                neg.proposal_history = neg.proposal_history[-_MAX_PROPOSAL_HISTORY:]
            neg.current_state = "countered"
            return neg

    def accept_negotiation(
        self,
        negotiation_id: str,
        agent_id: str,
    ) -> Optional[Negotiation]:
        """Accept a negotiation and move it to the ``ACCEPT`` phase.

        The associated goal transitions to ``PLEDGED``.

        Args:
            negotiation_id: Identifier of the target negotiation.
            agent_id: Identifier of the agent accepting the negotiation.

        Returns:
            The updated :class:`Negotiation`, or ``None`` if not found or
            already closed.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return None
            if neg.closed_at is not None:
                return None
            neg.phase = NegotiationPhase.ACCEPT
            neg.proposal_history.append(f"{_now()}::accept::{agent_id}")
            if len(neg.proposal_history) > _MAX_PROPOSAL_HISTORY:
                neg.proposal_history = neg.proposal_history[-_MAX_PROPOSAL_HISTORY:]
            neg.current_state = "accepted"

            # Update the associated goal to PLEDGED.
            goal = self._goals.get(neg.goal_id)
            if goal is not None and goal.status in (
                GoalStatus.PROPOSED,
                GoalStatus.NEGOTIATING,
            ):
                goal.status = GoalStatus.PLEDGED

            self._record_event(
                GoalNegotiationEventKind.GOAL_ACCEPTED,
                {
                    "negotiation_id": negotiation_id,
                    "goal_id": neg.goal_id,
                    "agent_id": agent_id,
                },
            )
            return neg

    def reject_negotiation(
        self,
        negotiation_id: str,
        agent_id: str,
        reason: str = "",
    ) -> Optional[Negotiation]:
        """Reject a negotiation and close it with a REJECT outcome.

        The associated goal transitions to ``ABANDONED``.

        Args:
            negotiation_id: Identifier of the target negotiation.
            agent_id: Identifier of the agent rejecting the negotiation.
            reason: Optional human-readable reason for the rejection.

        Returns:
            The updated :class:`Negotiation`, or ``None`` if not found.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return None
            if neg.closed_at is not None:
                return None
            neg.phase = NegotiationPhase.REJECT
            neg.closed_at = _now()
            neg.outcome = "rejected"
            neg.summary = reason or ""
            neg.current_state = "rejected"
            neg.proposal_history.append(
                f"{_now()}::reject::{agent_id}::{reason}" if reason
                else f"{_now()}::reject::{agent_id}"
            )
            if len(neg.proposal_history) > _MAX_PROPOSAL_HISTORY:
                neg.proposal_history = neg.proposal_history[-_MAX_PROPOSAL_HISTORY:]

            goal = self._goals.get(neg.goal_id)
            if goal is not None:
                goal.status = GoalStatus.ABANDONED
                goal.abandoned_reason = reason or ""

            self._record_event(
                GoalNegotiationEventKind.GOAL_REJECTED,
                {
                    "negotiation_id": negotiation_id,
                    "goal_id": neg.goal_id,
                    "agent_id": agent_id,
                    "reason": reason,
                },
            )
            return neg

    def close_negotiation(
        self,
        negotiation_id: str,
        outcome: str,
        summary: str = "",
    ) -> Optional[Negotiation]:
        """Close a negotiation with a specific outcome.

        Args:
            negotiation_id: Identifier of the target negotiation.
            outcome: Outcome string. Accepted values are ``accept``,
                ``reject``, ``withdraw``, and ``commit``. The phase is set
                accordingly.
            summary: Optional human-readable summary of the closure.

        Returns:
            The updated :class:`Negotiation`, or ``None`` if not found.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return None
            if neg.closed_at is not None:
                return None
            normalized = (outcome or "").strip().lower()
            if normalized == "accept":
                neg.phase = NegotiationPhase.ACCEPT
            elif normalized == "reject":
                neg.phase = NegotiationPhase.REJECT
            elif normalized == "commit":
                neg.phase = NegotiationPhase.COMMIT
            else:
                neg.phase = NegotiationPhase.REJECT
                normalized = "withdraw"
            neg.closed_at = _now()
            neg.outcome = normalized
            neg.summary = summary or ""
            neg.current_state = "closed"
            neg.proposal_history.append(
                f"{_now()}::close::{normalized}::{summary}" if summary
                else f"{_now()}::close::{normalized}"
            )
            if len(neg.proposal_history) > _MAX_PROPOSAL_HISTORY:
                neg.proposal_history = neg.proposal_history[-_MAX_PROPOSAL_HISTORY:]

            goal = self._goals.get(neg.goal_id)
            if goal is not None:
                if normalized == "accept":
                    goal.status = GoalStatus.PLEDGED
                elif normalized == "commit":
                    goal.status = GoalStatus.COMMITTED
                elif normalized == "reject":
                    goal.status = GoalStatus.ABANDONED
                else:
                    goal.status = GoalStatus.ABANDONED

            self._record_event(
                GoalNegotiationEventKind.NEGOTIATION_CLOSED,
                {
                    "negotiation_id": negotiation_id,
                    "goal_id": neg.goal_id,
                    "outcome": normalized,
                    "summary": summary,
                },
            )
            return neg

    # ------------------------------------------------------------------
    # Pledges
    # ------------------------------------------------------------------

    def make_pledge(
        self,
        negotiation_id: str,
        pledger_id: str,
        pledge_type: str,
        description: str,
        commitment_strength: float = _DEFAULT_COMMITMENT_STRENGTH,
        resource_amount: Optional[str] = None,
        action_steps: Optional[List[str]] = None,
    ) -> Optional[Pledge]:
        """Register a new pledge within a negotiation.

        The pledge is associated with the goal of the negotiation, and the
        pledger is automatically added to the negotiation's participant
        list if not already present.

        Args:
            negotiation_id: Identifier of the parent negotiation.
            pledger_id: Identifier of the agent making the pledge.
            pledge_type: Pledge type string corresponding to
                :class:`PledgeType` values.
            description: Free-form description of the pledge.
            commitment_strength: Strength of the commitment in [0.0, 1.0].
            resource_amount: Optional free-form description of the
                committed resource (e.g. ``"50 gold"``, ``"3 swords"``).
            action_steps: Optional list of concrete action steps.

        Returns:
            The newly created :class:`Pledge`, or ``None`` if the
            negotiation does not exist or is already closed.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return None
            if neg.closed_at is not None:
                return None
            parsed_type = _parse_pledge_type(pledge_type)
            clamped_strength = _clamp(float(commitment_strength), 0.0, 1.0)
            now = _now()
            pledge = Pledge(
                pledge_id=_new_id(),
                pledger_id=pledger_id,
                goal_id=neg.goal_id,
                pledge_type=parsed_type,
                description=description or "",
                commitment_strength=clamped_strength,
                resource_amount=resource_amount,
                action_steps=list(action_steps) if action_steps else [],
                status=PledgeStatus.ACTIVE,
                created_at=now,
                fulfilled_at=None,
                broken_at=None,
                negotiation_id=negotiation_id,
            )
            self._pledges[pledge.pledge_id] = pledge
            self._pledge_index.setdefault(neg.goal_id, []).append(pledge.pledge_id)
            self._pledge_counter += 1
            _evict_fifo_dict(self._pledges, _MAX_PLEDGES)

            # Auto-add pledger to negotiation participants.
            if pledger_id not in neg.participants:
                neg.participants.append(pledger_id)
            neg.proposal_history.append(
                f"{now}::pledge::{pledger_id}::{parsed_type.value}"
            )
            if len(neg.proposal_history) > _MAX_PROPOSAL_HISTORY:
                neg.proposal_history = neg.proposal_history[-_MAX_PROPOSAL_HISTORY:]

            self._record_event(
                GoalNegotiationEventKind.PLEDGE_MADE,
                {
                    "pledge_id": pledge.pledge_id,
                    "negotiation_id": negotiation_id,
                    "goal_id": neg.goal_id,
                    "pledger_id": pledger_id,
                    "pledge_type": parsed_type.value,
                    "commitment_strength": clamped_strength,
                },
            )
            return pledge

    def list_pledges(
        self,
        goal_id: Optional[str] = None,
        pledger_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Pledge]:
        """List pledges, optionally filtered by goal, pledger, and status."""
        with self._lock:
            parsed_status: Optional[PledgeStatus] = None
            if status is not None:
                if isinstance(status, PledgeStatus):
                    parsed_status = status
                else:
                    parsed_status = _parse_pledge_status(str(status))
            results: List[Pledge] = []
            for pledge in self._pledges.values():
                if goal_id is not None and pledge.goal_id != goal_id:
                    continue
                if pledger_id is not None and pledge.pledger_id != pledger_id:
                    continue
                if parsed_status is not None and pledge.status != parsed_status:
                    continue
                results.append(pledge)
            return results

    def get_pledge(self, pledge_id: str) -> Optional[Pledge]:
        """Return a single pledge by id, or None if not found."""
        with self._lock:
            return self._pledges.get(pledge_id)

    def fulfill_pledge(self, pledge_id: str) -> Optional[Pledge]:
        """Mark a pledge as fulfilled.

        Args:
            pledge_id: Identifier of the pledge to fulfill.

        Returns:
            The updated :class:`Pledge`, or ``None`` if not found or
            already in a terminal state.
        """
        with self._lock:
            pledge = self._pledges.get(pledge_id)
            if pledge is None:
                return None
            if pledge.status in (
                PledgeStatus.FULFILLED,
                PledgeStatus.BROKEN,
                PledgeStatus.RELEASED,
            ):
                return None
            pledge.status = PledgeStatus.FULFILLED
            pledge.fulfilled_at = _now()
            self._record_event(
                GoalNegotiationEventKind.PLEDGE_FULFILLED,
                {
                    "pledge_id": pledge_id,
                    "goal_id": pledge.goal_id,
                    "pledger_id": pledge.pledger_id,
                },
            )
            return pledge

    def break_pledge(
        self,
        pledge_id: str,
        reason: str = "",
    ) -> Optional[Pledge]:
        """Mark a pledge as broken.

        Args:
            pledge_id: Identifier of the pledge to break.
            reason: Optional free-form reason for breaking the pledge.

        Returns:
            The updated :class:`Pledge`, or ``None`` if not found or
            already in a terminal state.
        """
        with self._lock:
            pledge = self._pledges.get(pledge_id)
            if pledge is None:
                return None
            if pledge.status in (
                PledgeStatus.FULFILLED,
                PledgeStatus.BROKEN,
                PledgeStatus.RELEASED,
            ):
                return None
            pledge.status = PledgeStatus.BROKEN
            pledge.broken_at = _now()
            self._record_event(
                GoalNegotiationEventKind.PLEDGE_BROKEN,
                {
                    "pledge_id": pledge_id,
                    "goal_id": pledge.goal_id,
                    "pledger_id": pledge.pledger_id,
                    "reason": reason,
                },
            )
            return pledge

    # ------------------------------------------------------------------
    # Commitments
    # ------------------------------------------------------------------

    def register_commitment(
        self,
        agent_id: str,
        goal_id: str,
        pledge_ids: Optional[List[str]] = None,
    ) -> Optional[Commitment]:
        """Register a formal commitment by an agent to a goal.

        The commitment score is computed as the average commitment strength
        of the associated pledges (or a default when no pledges are
        supplied).

        Args:
            agent_id: Identifier of the committing agent.
            goal_id: Identifier of the target goal.
            pledge_ids: Optional list of pledge ids being consolidated into
                this commitment. The pledges must already exist and belong
                to the same agent and goal.

        Returns:
            The newly created :class:`Commitment`, or ``None`` if the goal
            does not exist or any of the supplied pledge ids are invalid.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None

            resolved_pledge_ids: List[str] = []
            if pledge_ids:
                for pid in pledge_ids:
                    pledge = self._pledges.get(pid)
                    if pledge is None:
                        return None
                    if pledge.pledger_id != agent_id or pledge.goal_id != goal_id:
                        return None
                    if pid not in resolved_pledge_ids:
                        resolved_pledge_ids.append(pid)

            if resolved_pledge_ids:
                strengths = [
                    self._pledges[pid].commitment_strength
                    for pid in resolved_pledge_ids
                    if pid in self._pledges
                ]
                score = sum(strengths) / len(strengths) if strengths else 0.0
            else:
                # No pledges supplied: derive a default commitment score.
                score = _DEFAULT_COMMITMENT_STRENGTH

            score = _clamp(float(score), 0.0, 1.0)
            commitment = Commitment(
                commitment_id=_new_id(),
                agent_id=agent_id,
                goal_id=goal_id,
                pledge_ids=list(resolved_pledge_ids),
                commitment_score=score,
                status="active",
                registered_at=_now(),
            )
            self._commitments[commitment.commitment_id] = commitment
            self._commitment_index.setdefault(goal_id, []).append(commitment.commitment_id)
            self._commitment_counter += 1
            _evict_fifo_dict(self._commitments, _MAX_COMMITMENTS)

            # Move the goal to COMMITTED if it has at least one commitment
            # and is currently in a pre-commitment state.
            if goal.status in (
                GoalStatus.PROPOSED,
                GoalStatus.NEGOTIATING,
                GoalStatus.PLEDGED,
            ):
                goal.status = GoalStatus.COMMITTED

            self._record_event(
                GoalNegotiationEventKind.COMMITMENT_REGISTERED,
                {
                    "commitment_id": commitment.commitment_id,
                    "agent_id": agent_id,
                    "goal_id": goal_id,
                    "pledge_ids": list(resolved_pledge_ids),
                    "commitment_score": score,
                },
            )
            return commitment

    def list_commitments(
        self,
        agent_id: Optional[str] = None,
        goal_id: Optional[str] = None,
    ) -> List[Commitment]:
        """List commitments, optionally filtered by agent and goal id."""
        with self._lock:
            results: List[Commitment] = []
            for commitment in self._commitments.values():
                if agent_id is not None and commitment.agent_id != agent_id:
                    continue
                if goal_id is not None and commitment.goal_id != goal_id:
                    continue
                results.append(commitment)
            return results

    # ------------------------------------------------------------------
    # Progress and goal completion
    # ------------------------------------------------------------------

    def update_progress(
        self,
        goal_id: str,
        progress: float,
        blockers: Optional[List[str]] = None,
    ) -> Optional[GoalProgress]:
        """Update the progress entry for a goal.

        Args:
            goal_id: Identifier of the goal to update.
            progress: Progress fraction in [0.0, 1.0]. Values are clamped.
            blockers: Optional list of free-form blocker descriptions.

        Returns:
            The updated :class:`GoalProgress`, or ``None`` if the goal does
            not exist.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            clamped = _clamp(float(progress), 0.0, 1.0)
            now = _now()
            existing = self._progress.get(goal_id)
            estimated = existing.estimated_completion if existing is not None else None
            entry = GoalProgress(
                goal_id=goal_id,
                current_progress=clamped,
                blockers=list(blockers) if blockers else [],
                last_updated=now,
                estimated_completion=estimated,
            )
            self._progress[goal_id] = entry
            _evict_fifo_dict(self._progress, _MAX_PROGRESS_ENTRIES)

            # Reflect progress on the goal record itself.
            if goal.status in (
                GoalStatus.PROPOSED,
                GoalStatus.NEGOTIATING,
                GoalStatus.PLEDGED,
                GoalStatus.COMMITTED,
            ):
                goal.status = GoalStatus.IN_PROGRESS
            if clamped >= 1.0 and goal.status != GoalStatus.ACHIEVED:
                # Progress reached completion; auto-mark the goal achieved.
                self._mark_goal_achieved_unlocked(goal, now)
            return entry

    def get_progress(self, goal_id: str) -> Optional[GoalProgress]:
        """Return the progress entry for a goal, or None if missing."""
        with self._lock:
            return self._progress.get(goal_id)

    def mark_goal_achieved(self, goal_id: str) -> Optional[GoalRecord]:
        """Mark a goal as achieved.

        Args:
            goal_id: Identifier of the goal to mark achieved.

        Returns:
            The updated :class:`GoalRecord`, or ``None`` if the goal does
            not exist.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            self._mark_goal_achieved_unlocked(goal, _now())
            return self._hydrate_goal(goal)

    def _mark_goal_achieved_unlocked(self, goal: GoalRecord, now: str) -> None:
        """Helper that flips a goal to ACHIEVED and records the event.

        Assumes the caller already holds ``self._lock``.
        """
        goal.status = GoalStatus.ACHIEVED
        goal.achieved_at = now
        # Ensure progress reflects completion.
        existing = self._progress.get(goal.goal_id)
        if existing is None:
            self._progress[goal.goal_id] = GoalProgress(
                goal_id=goal.goal_id,
                current_progress=1.0,
                blockers=[],
                last_updated=now,
                estimated_completion=now,
            )
        else:
            self._progress[goal.goal_id] = GoalProgress(
                goal_id=existing.goal_id,
                current_progress=1.0,
                blockers=list(existing.blockers),
                last_updated=now,
                estimated_completion=existing.estimated_completion or now,
            )
        self._record_event(
            GoalNegotiationEventKind.GOAL_ACHIEVED,
            {
                "goal_id": goal.goal_id,
                "title": goal.title,
            },
        )

    def mark_goal_abandoned(
        self,
        goal_id: str,
        reason: str = "",
    ) -> Optional[GoalRecord]:
        """Mark a goal as abandoned with an optional reason.

        Args:
            goal_id: Identifier of the goal to abandon.
            reason: Optional free-form reason.

        Returns:
            The updated :class:`GoalRecord`, or ``None`` if the goal does
            not exist.
        """
        with self._lock:
            goal = self._goals.get(goal_id)
            if goal is None:
                return None
            goal.status = GoalStatus.ABANDONED
            goal.abandoned_reason = reason or ""
            return self._hydrate_goal(goal)

    # ------------------------------------------------------------------
    # Success metrics
    # ------------------------------------------------------------------

    def compute_negotiation_success_rate(self, negotiation_id: str) -> float:
        """Compute the success rate for a single negotiation.

        Success rate is the ratio of fulfilled/active pledges to total
        pledges registered under the negotiation's goal. Pledges that are
        broken or released count against success.

        Args:
            negotiation_id: Identifier of the target negotiation.

        Returns:
            A success rate in [0.0, 1.0]. Returns ``0.0`` if the
            negotiation does not exist or has no pledges.
        """
        with self._lock:
            neg = self._negotiations.get(negotiation_id)
            if neg is None:
                return 0.0
            pledge_ids = self._pledge_index.get(neg.goal_id, [])
            pledges = [self._pledges[pid] for pid in pledge_ids if pid in self._pledges]
            if not pledges:
                return 0.0
            positive = sum(
                1 for p in pledges
                if p.status in (PledgeStatus.ACTIVE, PledgeStatus.FULFILLED)
            )
            rate = positive / len(pledges)
            return _clamp(rate, _SUCCESS_RATE_FLOOR, _SUCCESS_RATE_CEILING)

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: GoalNegotiationEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable engine event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = GoalNegotiationEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[GoalNegotiationEvent]:
        """Return the most recent engine events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> NegotiationStats:
        """Return aggregate statistics about the goal negotiation engine."""
        with self._lock:
            total_goals = len(self._goals)
            total_negotiations = len(self._negotiations)
            total_pledges = len(self._pledges)
            active_pledges = sum(
                1 for p in self._pledges.values() if p.status == PledgeStatus.ACTIVE
            )
            broken_pledges = sum(
                1 for p in self._pledges.values() if p.status == PledgeStatus.BROKEN
            )
            goals_achieved = sum(
                1 for g in self._goals.values() if g.status == GoalStatus.ACHIEVED
            )

            if total_pledges > 0:
                positive = sum(
                    1 for p in self._pledges.values()
                    if p.status in (PledgeStatus.ACTIVE, PledgeStatus.FULFILLED)
                )
                success_rate = positive / total_pledges
            else:
                success_rate = 0.0
            success_rate = _clamp(success_rate, _SUCCESS_RATE_FLOOR, _SUCCESS_RATE_CEILING)

            return NegotiationStats(
                total_goals=total_goals,
                total_negotiations=total_negotiations,
                total_pledges=total_pledges,
                active_pledges=active_pledges,
                broken_pledges=broken_pledges,
                goals_achieved=goals_achieved,
                success_rate=round(success_rate, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            goals_by_status: Dict[str, int] = {}
            goals_by_priority: Dict[str, int] = {}
            for goal in self._goals.values():
                goals_by_status[goal.status.value] = goals_by_status.get(goal.status.value, 0) + 1
                goals_by_priority[goal.priority.value] = goals_by_priority.get(goal.priority.value, 0) + 1
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_goals": len(self._goals),
                "total_proposals": len(self._proposals),
                "total_negotiations": len(self._negotiations),
                "total_pledges": len(self._pledges),
                "total_commitments": len(self._commitments),
                "total_events": len(self._events),
                "goal_counter": self._goal_counter,
                "negotiation_counter": self._negotiation_counter,
                "pledge_counter": self._pledge_counter,
                "commitment_counter": self._commitment_counter,
                "goals_by_status": goals_by_status,
                "goals_by_priority": goals_by_priority,
                "stats": stats.to_dict(),
                "capacities": {
                    "max_goals": _MAX_GOALS,
                    "max_proposals": _MAX_PROPOSALS,
                    "max_negotiations": _MAX_NEGOTIATIONS,
                    "max_pledges": _MAX_PLEDGES,
                    "max_commitments": _MAX_COMMITMENTS,
                    "max_progress_entries": _MAX_PROGRESS_ENTRIES,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> GoalNegotiationSnapshot:
        """Return a complete snapshot of the goal negotiation engine state."""
        with self._lock:
            goals = [self._hydrate_goal(g) for g in self._goals.values()]
            return GoalNegotiationSnapshot(
                initialized=self._initialized,
                goals=goals,
                proposals=list(self._proposals.values()),
                negotiations=list(self._negotiations.values()),
                pledges=list(self._pledges.values()),
                commitments=list(self._commitments.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline negotiation data.

        Unlike some sibling engines, this method re-seeds the baseline
        negotiation data after clearing, restoring the engine to a freshly
        initialized state.
        """
        with self._lock:
            self._goals.clear()
            self._proposals.clear()
            self._negotiations.clear()
            self._pledges.clear()
            self._commitments.clear()
            self._progress.clear()
            self._events.clear()
            self._pledge_index.clear()
            self._commitment_index.clear()
            self._goal_counter = 0
            self._negotiation_counter = 0
            self._pledge_counter = 0
            self._commitment_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs goal negotiation data.

        Seeds two goals, one open negotiation, three pledges, two
        commitments, and a single progress entry.
        """
        # --- Goal 1: "Build the fortress" (HIGH) ------------------------
        fortress_proposal = self.propose_goal(
            proposer_id="architect_agent",
            title="Build the fortress",
            description=(
                "Construct a fortified stronghold on the northern ridge to "
                "defend against the encroaching threat."
            ),
            priority="high",
            required_participants=["warrior", "mage", "builder"],
        )
        fortress_goal_id = fortress_proposal.goal_id

        # Open a negotiation in NEGOTIATING phase with three participants.
        fortress_neg = self.open_negotiation(
            goal_id=fortress_goal_id,
            initiator_id="architect_agent",
            participants=["warrior", "mage", "builder"],
        )
        if fortress_neg is not None:
            # Move into the COUNTER/REJECT-loop then back to NEGOTIATING
            # state by re-opening on a counter. We keep the negotiation
            # in NEGOTIATING by switching to COUNTER, then setting the
            # goal back to NEGOTIATING so it visually reflects the seed
            # description ("1 negotiation in NEGOTIATING phase").
            self.submit_counter_proposal(
                negotiation_id=fortress_neg.negotiation_id,
                agent_id="builder",
                counter_text=(
                    "Foundation must be laid before walls; needs additional "
                    "stone resource pledge."
                ),
            )
            fortress_neg.phase = NegotiationPhase.PROPOSAL
            # The seed specifies "NEGOTIATING phase"; surface that label by
            # tagging the goal's status.
            goal = self._goals.get(fortress_goal_id)
            if goal is not None:
                goal.status = GoalStatus.NEGOTIATING

        # Three pledges: warrior, mage, builder.
        warrior_pledge = self.make_pledge(
            negotiation_id=fortress_neg.negotiation_id if fortress_neg else "",
            pledger_id="warrior",
            pledge_type="action",
            description=(
                "Will defend the build site and patrol the perimeter while "
                "construction is underway."
            ),
            commitment_strength=0.85,
            action_steps=[
                "Patrol the perimeter twice daily",
                "Intercept any hostile intruders",
                "Stand guard at the gate during off-hours",
            ],
        )
        mage_pledge = self.make_pledge(
            negotiation_id=fortress_neg.negotiation_id if fortress_neg else "",
            pledger_id="mage",
            pledge_type="resource",
            description=(
                "Will enchant the fortress walls with a warding glyph that "
                "weakens hostile spellcasting."
            ),
            commitment_strength=0.7,
            resource_amount="3 ward-stones and 200 mana",
        )
        builder_pledge = self.make_pledge(
            negotiation_id=fortress_neg.negotiation_id if fortress_neg else "",
            pledger_id="builder",
            pledge_type="action",
            description=(
                "Will lead the construction crew and personally oversee "
                "the foundation and wall phases."
            ),
            commitment_strength=0.95,
            action_steps=[
                "Lay the foundation within 3 days",
                "Coordinate stone deliveries",
                "Supervise wall construction to completion",
            ],
        )

        # --- Goal 2: "Defeat the dragon" (CRITICAL) ---------------------
        self.propose_goal(
            proposer_id="quest_giver",
            title="Defeat the dragon",
            description=(
                "Venture into the dragon's lair and slay the ancient wyrm "
                "threatening the kingdom."
            ),
            priority="critical",
            required_participants=["warrior", "mage", "cleric"],
        )

        # --- Two formal commitments: warrior and builder ---------------
        if warrior_pledge is not None:
            self.register_commitment(
                agent_id="warrior",
                goal_id=fortress_goal_id,
                pledge_ids=[warrior_pledge.pledge_id],
            )
        if builder_pledge is not None:
            self.register_commitment(
                agent_id="builder",
                goal_id=fortress_goal_id,
                pledge_ids=[builder_pledge.pledge_id],
            )

        # --- One progress entry: fortress at 30% -----------------------
        # We record the progress but keep the goal in NEGOTIATING status
        # because the negotiation is still open and the goal is being
        # actively debated even though some early work has begun.
        self.update_progress(
            goal_id=fortress_goal_id,
            progress=0.30,
            blockers=[
                "Awaiting additional stone delivery from the quarry",
            ],
        )
        if fortress_goal_id in self._goals:
            self._goals[fortress_goal_id].status = GoalStatus.NEGOTIATING

        # Reference mage_pledge to keep the linter happy about unused
        # variable in the seed.
        _ = mage_pledge


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_goal_negotiation_ledger() -> GoalNegotiationLedgerEngine:
    """Return the singleton GoalNegotiationLedgerEngine instance."""
    return GoalNegotiationLedgerEngine.get_instance()
