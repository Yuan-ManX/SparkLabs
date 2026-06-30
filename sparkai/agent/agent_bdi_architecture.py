"""
SparkLabs Agent - BDI Architecture

Belief-Desire-Intention architecture for rational AI agents. Structures
agent reasoning around three mental attitudes: beliefs (what the agent
knows about the world), desires (what the agent wants to achieve), and
intentions (what the agent has committed to doing).

The BDI engine orchestrates the reasoning cycle: observe new
perceptions, update beliefs, generate candidate options from active
desires, filter options into committed intentions, execute actions,
and reflect on outcomes. This produces goal-directed, adaptive
behavior that responds to changing world conditions.

Each agent has its own BDI state. The engine supports multiple
concurrent agents, each with independent belief bases, desire sets,
and intention stacks. Reasoning cycles can be triggered manually or
through the tick() method for periodic processing.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BeliefSource(Enum):
    """How an agent acquired a belief."""
    PERCEPTION = "perception"
    INFERENCE = "inference"
    COMMUNICATION = "communication"
    DEFAULT = "default"
    ASSUMPTION = "assumption"


class BeliefStatus(Enum):
    """Lifecycle state of a belief."""
    ACTIVE = "active"
    DUBIOUS = "dubious"
    OBSOLETE = "obsolete"
    RETRACTED = "retracted"


class DesireStatus(Enum):
    """Lifecycle state of a desire."""
    PENDING = "pending"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    FAILED = "failed"
    ABANDONED = "abandoned"


class DesirePriority(Enum):
    """Relative importance of a desire."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class IntentionStatus(Enum):
    """Lifecycle state of an intention."""
    COMMITTED = "committed"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUSPENDED = "suspended"


class CommitmentStrategy(Enum):
    """Policy governing how many intentions an agent may hold at once."""
    SINGLE_MIND = "single_mind"
    BOUNDED = "bounded"
    OPEN = "open"


class ReasoningPhase(Enum):
    """A phase of the BDI reasoning cycle."""
    OBSERVE = "observe"
    DELIBERATE = "deliberate"
    SELECT = "select"
    EXECUTE = "execute"
    REFLECT = "reflect"


class BDIEventKind(Enum):
    """Kinds of events emitted by the BDI engine."""
    BELIEF_ADDED = "belief_added"
    BELIEF_UPDATED = "belief_updated"
    BELIEF_RETRACTED = "belief_retracted"
    DESIRE_ACTIVATED = "desire_activated"
    DESIRE_SATISFIED = "desire_satisfied"
    DESIRE_FAILED = "desire_failed"
    INTENTION_COMMITTED = "intention_committed"
    INTENTION_COMPLETED = "intention_completed"
    INTENTION_FAILED = "intention_failed"
    CYCLE_STARTED = "cycle_started"
    CYCLE_COMPLETED = "cycle_completed"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_PRIORITY_WEIGHTS: Dict[DesirePriority, float] = {
    DesirePriority.CRITICAL: 1.0,
    DesirePriority.HIGH: 0.8,
    DesirePriority.NORMAL: 0.6,
    DesirePriority.LOW: 0.4,
    DesirePriority.BACKGROUND: 0.2,
}


def _priority_weight(priority: DesirePriority) -> float:
    """Return the numeric weight for a desire priority."""
    return _PRIORITY_WEIGHTS.get(priority, 0.6)


def _now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string."""
    return datetime.datetime.utcnow().isoformat()


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the [low, high] interval."""
    return max(low, min(high, value))


def _compare(actual: Any, operator: str, expected: Any) -> bool:
    """Compare two values using a string operator."""
    try:
        if operator == "eq":
            return actual == expected
        if operator == "ne":
            return actual != expected
        if operator == "lt":
            return actual < expected
        if operator == "le":
            return actual <= expected
        if operator == "gt":
            return actual > expected
        if operator == "ge":
            return actual >= expected
        return False
    except TypeError:
        return False


def _evaluate_condition(
    beliefs: Dict[str, "Belief"], condition: Optional[Dict[str, Any]]
) -> bool:
    """Evaluate a predicate dict against an agent's beliefs.

    A condition is a mapping of ``"belief:<key>"`` entries to a spec dict
    holding an ``operator`` and a ``value``. An empty or None condition is
    always satisfied.
    """
    if not condition:
        return True
    for cond_key, spec in condition.items():
        if not isinstance(spec, dict):
            return False
        if not cond_key.startswith("belief:"):
            return False
        belief_key = cond_key[len("belief:"):]
        belief = beliefs.get(belief_key)
        if belief is None:
            return False
        operator = spec.get("operator", "eq")
        expected = spec.get("value")
        if not _compare(belief.value, operator, expected):
            return False
    return True


def _normalize_plan_steps(steps: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalize plan step dicts so each has action, parameters and status."""
    if not steps:
        return []
    normalized: List[Dict[str, Any]] = []
    for step in steps:
        if not isinstance(step, dict):
            continue
        copy = dict(step)
        copy.setdefault("action", "unknown")
        copy.setdefault("parameters", {})
        copy.setdefault("status", "pending")
        normalized.append(copy)
    return normalized


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Belief:
    """A piece of knowledge held by an agent about the world.

    The ``key`` identifies the proposition, ``value`` is its content, and
    ``confidence`` ranges from 0.0 to 1.0. ``supporting_beliefs`` holds the
    IDs of beliefs used to derive this one when it is the result of an
    inference.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    key: str = ""
    value: Any = None
    source: BeliefSource = BeliefSource.PERCEPTION
    confidence: float = 1.0
    timestamp: str = field(default_factory=_now_iso)
    last_updated: str = field(default_factory=_now_iso)
    status: BeliefStatus = BeliefStatus.ACTIVE
    supporting_beliefs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "key": self.key,
            "value": self.value,
            "source": self.source.value,
            "confidence": round(self.confidence, 4),
            "timestamp": self.timestamp,
            "last_updated": self.last_updated,
            "status": self.status.value,
            "supporting_beliefs": list(self.supporting_beliefs),
            "metadata": self.metadata,
        }


@dataclass
class Desire:
    """A goal an agent wants to achieve.

    ``utility`` in [0.0, 1.0] describes how desirable the goal is. The
    ``activation_condition`` is a predicate dict evaluated against beliefs
    that determines when a pending desire becomes active. The
    ``satisfaction_condition`` determines when the desire is fulfilled.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    name: str = ""
    description: str = ""
    priority: DesirePriority = DesirePriority.NORMAL
    utility: float = 0.5
    activation_condition: Optional[Dict[str, Any]] = None
    satisfaction_condition: Optional[Dict[str, Any]] = None
    status: DesireStatus = DesireStatus.PENDING
    created_at: str = field(default_factory=_now_iso)
    activated_at: Optional[str] = None
    satisfied_at: Optional[str] = None
    parent_desire_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "utility": round(self.utility, 4),
            "activation_condition": self.activation_condition,
            "satisfaction_condition": self.satisfaction_condition,
            "status": self.status.value,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "satisfied_at": self.satisfied_at,
            "parent_desire_id": self.parent_desire_id,
            "metadata": self.metadata,
        }


@dataclass
class Intention:
    """A commitment to pursue a desire through a sequence of plan steps.

    Each step in ``plan_steps`` is a dict with ``action``, ``parameters``
    and ``status``. ``current_step_index`` points at the next step to
    execute. ``commitment_level`` in [0.0, 1.0] records how strongly the
    agent is bound to this intention.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    desire_id: str = ""
    plan_steps: List[Dict[str, Any]] = field(default_factory=list)
    current_step_index: int = 0
    status: IntentionStatus = IntentionStatus.COMMITTED
    committed_at: str = field(default_factory=_now_iso)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    commitment_level: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "desire_id": self.desire_id,
            "plan_steps": [dict(s) for s in self.plan_steps],
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "committed_at": self.committed_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "commitment_level": round(self.commitment_level, 4),
            "metadata": self.metadata,
        }


@dataclass
class BDIEvent:
    """An event emitted during BDI reasoning."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    kind: BDIEventKind = BDIEventKind.CYCLE_STARTED
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "kind": self.kind.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentBDIState:
    """The full BDI state for a single agent."""
    agent_id: str = ""
    commitment_strategy: CommitmentStrategy = CommitmentStrategy.BOUNDED
    max_intentions: int = 5
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    desires: Dict[str, Desire] = field(default_factory=dict)
    intentions: Dict[str, Intention] = field(default_factory=dict)
    current_phase: ReasoningPhase = ReasoningPhase.OBSERVE
    last_cycle_at: Optional[str] = None
    cycle_count: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        self.stats = {
            "belief_count": len(self.beliefs),
            "desire_count": len(self.desires),
            "intention_count": len(self.intentions),
            "cycle_count": self.cycle_count,
            "current_phase": self.current_phase.value,
        }
        return {
            "agent_id": self.agent_id,
            "commitment_strategy": self.commitment_strategy.value,
            "max_intentions": self.max_intentions,
            "beliefs": {k: v.to_dict() for k, v in self.beliefs.items()},
            "desires": {k: v.to_dict() for k, v in self.desires.items()},
            "intentions": {k: v.to_dict() for k, v in self.intentions.items()},
            "current_phase": self.current_phase.value,
            "last_cycle_at": self.last_cycle_at,
            "cycle_count": self.cycle_count,
            "stats": self.stats,
        }


@dataclass
class BDISnapshot:
    """A point-in-time snapshot of the whole engine."""
    agent_count: int = 0
    total_beliefs: int = 0
    total_desires: int = 0
    total_intentions: int = 0
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_beliefs": self.total_beliefs,
            "total_desires": self.total_desires,
            "total_intentions": self.total_intentions,
            "stats": self.stats,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# BDIArchitectureEngine
# ---------------------------------------------------------------------------

class BDIArchitectureEngine:
    """Thread-safe singleton engine implementing the BDI reasoning model.

    Maintains independent belief bases, desire sets and intention stacks
    for each registered agent. All public operations are guarded by a
    re-entrant lock so the engine can be driven safely from multiple game
    threads.
    """

    _instance: Optional["BDIArchitectureEngine"] = None
    _lock = threading.RLock()

    _MAX_EVENTS: int = 10000
    _MAX_EVENTS_PER_AGENT: int = 2000

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return

        self._states: Dict[str, AgentBDIState] = {}
        self._events: List[BDIEvent] = []
        self._events_by_agent: Dict[str, List[BDIEvent]] = {}
        self._handlers: Dict[
            Optional[BDIEventKind], Dict[str, Callable[[BDIEvent], None]]
        ] = {}

        self._total_cycles: int = 0
        self._total_intentions_committed: int = 0
        self._total_intentions_completed: int = 0
        self._total_intentions_failed: int = 0
        self._total_beliefs_added: int = 0
        self._total_beliefs_updated: int = 0
        self._total_beliefs_retracted: int = 0
        self._total_desires_activated: int = 0
        self._total_desires_satisfied: int = 0
        self._total_desires_failed: int = 0
        self._last_cycle_at: Optional[str] = None

        self._initialized: bool = True

        self._seed_default_data()

    @classmethod
    def get_instance(cls) -> "BDIArchitectureEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers (assume lock is held)
    # ------------------------------------------------------------------

    def _require_state(self, agent_id: str) -> AgentBDIState:
        state = self._states.get(agent_id)
        if state is None:
            raise ValueError(f"Agent '{agent_id}' is not registered")
        return state

    def _emit_event(
        self, agent_id: str, kind: BDIEventKind, payload: Optional[Dict[str, Any]] = None
    ) -> BDIEvent:
        event = BDIEvent(
            agent_id=agent_id,
            kind=kind,
            payload=payload or {},
        )
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            self._events = self._events[-self._MAX_EVENTS:]
        agent_events = self._events_by_agent.setdefault(agent_id, [])
        agent_events.append(event)
        if len(agent_events) > self._MAX_EVENTS_PER_AGENT:
            self._events_by_agent[agent_id] = agent_events[-self._MAX_EVENTS_PER_AGENT:]

        exact = self._handlers.get(kind)
        if exact:
            for handler in list(exact.values()):
                try:
                    handler(event)
                except Exception:
                    pass
        wildcard = self._handlers.get(None)
        if wildcard:
            for handler in list(wildcard.values()):
                try:
                    handler(event)
                except Exception:
                    pass
        return event

    def _active_intentions(self, state: AgentBDIState) -> List[Intention]:
        return [
            i for i in state.intentions.values()
            if i.status in (IntentionStatus.COMMITTED, IntentionStatus.EXECUTING)
        ]

    def _intention_priority_score(self, state: AgentBDIState, intention: Intention) -> float:
        desire = state.desires.get(intention.desire_id)
        if desire is None:
            return 0.0
        return _priority_weight(desire.priority)

    def _find_lowest_priority_intention(
        self, state: AgentBDIState
    ) -> Optional[Intention]:
        active = self._active_intentions(state)
        if not active:
            return None
        active.sort(
            key=lambda i: (
                self._intention_priority_score(state, i),
                i.commitment_level,
                i.committed_at,
            )
        )
        return active[0]

    def _cancel_intention_locked(
        self, state: AgentBDIState, intention_id: str
    ) -> Optional[Intention]:
        intention = state.intentions.get(intention_id)
        if intention is None:
            return None
        if intention.status in (
            IntentionStatus.COMPLETED,
            IntentionStatus.FAILED,
            IntentionStatus.CANCELLED,
        ):
            return intention
        intention.status = IntentionStatus.CANCELLED
        intention.completed_at = _now_iso()
        return intention

    def _advance_intention_locked(
        self, state: AgentBDIState, intention: Intention
    ) -> Intention:
        steps = intention.plan_steps
        if not steps:
            if intention.status != IntentionStatus.COMPLETED:
                intention.status = IntentionStatus.COMPLETED
                intention.completed_at = _now_iso()
                self._total_intentions_completed += 1
                self._emit_event(
                    state.agent_id,
                    BDIEventKind.INTENTION_COMPLETED,
                    {"intention_id": intention.id, "desire_id": intention.desire_id},
                )
            return intention

        if intention.status == IntentionStatus.COMMITTED:
            intention.status = IntentionStatus.EXECUTING
            intention.started_at = _now_iso()

        if intention.status != IntentionStatus.EXECUTING:
            return intention

        idx = intention.current_step_index
        if idx < len(steps):
            steps[idx]["status"] = "completed"
            intention.current_step_index = idx + 1

        if intention.current_step_index >= len(steps) and intention.status != IntentionStatus.COMPLETED:
            intention.status = IntentionStatus.COMPLETED
            intention.completed_at = _now_iso()
            self._total_intentions_completed += 1
            self._emit_event(
                state.agent_id,
                BDIEventKind.INTENTION_COMPLETED,
                {"intention_id": intention.id, "desire_id": intention.desire_id},
            )
        return intention

    def _check_desire_conditions_locked(
        self, state: AgentBDIState
    ) -> Dict[str, List[str]]:
        activated: List[str] = []
        satisfied: List[str] = []
        failed: List[str] = []

        for desire in list(state.desires.values()):
            if desire.status == DesireStatus.PENDING:
                if _evaluate_condition(state.beliefs, desire.activation_condition):
                    desire.status = DesireStatus.ACTIVE
                    desire.activated_at = _now_iso()
                    activated.append(desire.id)
                    self._total_desires_activated += 1
                    self._emit_event(
                        state.agent_id,
                        BDIEventKind.DESIRE_ACTIVATED,
                        {"desire_id": desire.id, "name": desire.name},
                    )
            if desire.status == DesireStatus.ACTIVE:
                if _evaluate_condition(state.beliefs, desire.satisfaction_condition):
                    desire.status = DesireStatus.SATISFIED
                    desire.satisfied_at = _now_iso()
                    satisfied.append(desire.id)
                    self._total_desires_satisfied += 1
                    self._emit_event(
                        state.agent_id,
                        BDIEventKind.DESIRE_SATISFIED,
                        {"desire_id": desire.id, "name": desire.name},
                    )
                else:
                    has_failed = any(
                        i.desire_id == desire.id
                        and i.status == IntentionStatus.FAILED
                        for i in state.intentions.values()
                    )
                    if has_failed:
                        desire.status = DesireStatus.FAILED
                        failed.append(desire.id)
                        self._total_desires_failed += 1
                        self._emit_event(
                            state.agent_id,
                            BDIEventKind.DESIRE_FAILED,
                            {"desire_id": desire.id, "name": desire.name},
                        )
        return {"activated": activated, "satisfied": satisfied, "failed": failed}

    def _deliberate_locked(
        self, state: AgentBDIState
    ) -> List[Dict[str, Any]]:
        active_desire_ids = {
            i.desire_id for i in self._active_intentions(state)
        }
        options: List[Dict[str, Any]] = []
        for desire in state.desires.values():
            if desire.status != DesireStatus.ACTIVE:
                continue
            if desire.id in active_desire_ids:
                continue
            weight = _priority_weight(desire.priority)
            score = weight * desire.utility
            options.append({
                "desire_id": desire.id,
                "name": desire.name,
                "priority": desire.priority.value,
                "utility": round(desire.utility, 4),
                "score": round(score, 4),
            })
        options.sort(key=lambda o: o["score"], reverse=True)
        return options

    def _select_locked(
        self, state: AgentBDIState, options: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        strategy = state.commitment_strategy
        if strategy == CommitmentStrategy.SINGLE_MIND:
            limit = 1 if not self._active_intentions(state) else 0
        elif strategy == CommitmentStrategy.BOUNDED:
            remaining = state.max_intentions - len(self._active_intentions(state))
            limit = max(0, remaining)
        else:
            limit = len(options)

        committed: List[str] = []
        for option in options[:limit]:
            desire = state.desires.get(option["desire_id"])
            if desire is None:
                continue
            steps = _normalize_plan_steps([
                {"action": "pursue", "parameters": {"desire_id": desire.id}, "status": "pending"}
            ])
            intention = Intention(
                agent_id=state.agent_id,
                desire_id=desire.id,
                plan_steps=steps,
                current_step_index=0,
                status=IntentionStatus.COMMITTED,
                commitment_level=1.0,
            )
            state.intentions[intention.id] = intention
            self._total_intentions_committed += 1
            committed.append(intention.id)
            self._emit_event(
                state.agent_id,
                BDIEventKind.INTENTION_COMMITTED,
                {"intention_id": intention.id, "desire_id": desire.id},
            )
        return {"committed": committed, "options_considered": len(options)}

    def _execute_locked(self, state: AgentBDIState) -> Dict[str, Any]:
        advanced: List[str] = []
        for intention in list(state.intentions.values()):
            if intention.status in (IntentionStatus.COMMITTED, IntentionStatus.EXECUTING):
                self._advance_intention_locked(state, intention)
                advanced.append(intention.id)
        return {"advanced": advanced}

    def _reflect_locked(self, state: AgentBDIState) -> Dict[str, Any]:
        completed: List[str] = []
        failed: List[str] = []
        for intention in list(state.intentions.values()):
            if intention.status == IntentionStatus.COMPLETED:
                completed.append(intention.id)
                desire = state.desires.get(intention.desire_id)
                if desire and desire.status == DesireStatus.ACTIVE:
                    if desire.satisfaction_condition and _evaluate_condition(
                        state.beliefs, desire.satisfaction_condition
                    ):
                        desire.status = DesireStatus.SATISFIED
                        desire.satisfied_at = _now_iso()
                        self._total_desires_satisfied += 1
                        self._emit_event(
                            state.agent_id,
                            BDIEventKind.DESIRE_SATISFIED,
                            {"desire_id": desire.id, "name": desire.name},
                        )
            elif intention.status == IntentionStatus.FAILED:
                failed.append(intention.id)
                desire = state.desires.get(intention.desire_id)
                if desire and desire.status == DesireStatus.ACTIVE:
                    desire.status = DesireStatus.FAILED
                    self._total_desires_failed += 1
                    self._emit_event(
                        state.agent_id,
                        BDIEventKind.DESIRE_FAILED,
                        {"desire_id": desire.id, "name": desire.name},
                    )
        return {"completed": completed, "failed": failed}

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        commitment_strategy: CommitmentStrategy = CommitmentStrategy.BOUNDED,
        max_intentions: int = 5,
    ) -> AgentBDIState:
        """Initialize BDI state for an agent and return the new state."""
        with self._lock:
            existing = self._states.get(agent_id)
            if existing is not None:
                return existing
            state = AgentBDIState(
                agent_id=agent_id,
                commitment_strategy=commitment_strategy,
                max_intentions=max(1, max_intentions),
            )
            self._states[agent_id] = state
            return state

    def remove_agent(self, agent_id: str) -> bool:
        """Remove an agent and all of its BDI state."""
        with self._lock:
            if agent_id not in self._states:
                return False
            del self._states[agent_id]
            self._events_by_agent.pop(agent_id, None)
            return True

    def get_agent_state(self, agent_id: str) -> Optional[AgentBDIState]:
        """Return the BDI state for an agent, or None."""
        with self._lock:
            return self._states.get(agent_id)

    def list_agents(self) -> List[str]:
        """Return the IDs of all registered agents."""
        with self._lock:
            return list(self._states.keys())

    # ------------------------------------------------------------------
    # Belief operations
    # ------------------------------------------------------------------

    def add_belief(
        self,
        agent_id: str,
        key: str,
        value: Any,
        source: BeliefSource = BeliefSource.PERCEPTION,
        confidence: float = 1.0,
        supporting_beliefs: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Belief:
        """Add a new belief or update an existing one for an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            now = _now_iso()
            clamped = _clamp(confidence)
            existing = state.beliefs.get(key)
            if existing is not None:
                existing.value = value
                existing.source = source
                existing.confidence = clamped
                existing.last_updated = now
                existing.status = BeliefStatus.ACTIVE
                if supporting_beliefs is not None:
                    existing.supporting_beliefs = list(supporting_beliefs)
                if metadata is not None:
                    existing.metadata.update(metadata)
                self._total_beliefs_updated += 1
                self._emit_event(
                    agent_id,
                    BDIEventKind.BELIEF_UPDATED,
                    {"key": key, "value": value, "confidence": clamped},
                )
                return existing
            belief = Belief(
                agent_id=agent_id,
                key=key,
                value=value,
                source=source,
                confidence=clamped,
                timestamp=now,
                last_updated=now,
                status=BeliefStatus.ACTIVE,
                supporting_beliefs=list(supporting_beliefs) if supporting_beliefs else [],
                metadata=dict(metadata) if metadata else {},
            )
            state.beliefs[key] = belief
            self._total_beliefs_added += 1
            self._emit_event(
                agent_id,
                BDIEventKind.BELIEF_ADDED,
                {"key": key, "value": value, "confidence": clamped},
            )
            return belief

    def get_belief(self, agent_id: str, key: str) -> Optional[Belief]:
        """Return a single belief by key, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.beliefs.get(key)

    def query_beliefs(
        self, agent_id: str, predicate: Optional[Dict[str, Any]] = None
    ) -> List[Belief]:
        """Return beliefs matching a predicate dict, or all beliefs."""
        with self._lock:
            state = self._require_state(agent_id)
            beliefs = list(state.beliefs.values())
            if predicate is None:
                return beliefs
            matches: List[Belief] = []
            for belief in beliefs:
                view = {
                    "key": belief.key,
                    "value": belief.value,
                    "source": belief.source.value,
                    "status": belief.status.value,
                    "confidence": belief.confidence,
                }
                view.update(belief.metadata)
                ok = True
                for k, v in predicate.items():
                    if view.get(k) != v:
                        ok = False
                        break
                if ok:
                    matches.append(belief)
            return matches

    def retract_belief(self, agent_id: str, key: str) -> bool:
        """Mark a belief as retracted. Returns True if the belief existed."""
        with self._lock:
            state = self._require_state(agent_id)
            belief = state.beliefs.get(key)
            if belief is None:
                return False
            belief.status = BeliefStatus.RETRACTED
            belief.last_updated = _now_iso()
            self._total_beliefs_retracted += 1
            self._emit_event(
                agent_id,
                BDIEventKind.BELIEF_RETRACTED,
                {"key": key},
            )
            return True

    def update_belief_confidence(
        self, agent_id: str, key: str, confidence: float
    ) -> Belief:
        """Update the confidence of an existing belief."""
        with self._lock:
            state = self._require_state(agent_id)
            belief = state.beliefs.get(key)
            if belief is None:
                raise ValueError(
                    f"Belief '{key}' not found for agent '{agent_id}'"
                )
            belief.confidence = _clamp(confidence)
            belief.last_updated = _now_iso()
            self._total_beliefs_updated += 1
            self._emit_event(
                agent_id,
                BDIEventKind.BELIEF_UPDATED,
                {"key": key, "confidence": belief.confidence},
            )
            return belief

    def list_beliefs(
        self, agent_id: str, status: Optional[BeliefStatus] = None
    ) -> List[Belief]:
        """Return beliefs for an agent, optionally filtered by status."""
        with self._lock:
            state = self._require_state(agent_id)
            beliefs = list(state.beliefs.values())
            if status is None:
                return beliefs
            return [b for b in beliefs if b.status == status]

    # ------------------------------------------------------------------
    # Desire operations
    # ------------------------------------------------------------------

    def add_desire(
        self,
        agent_id: str,
        name: str,
        description: str,
        priority: DesirePriority = DesirePriority.NORMAL,
        utility: float = 0.5,
        activation_condition: Optional[Dict[str, Any]] = None,
        satisfaction_condition: Optional[Dict[str, Any]] = None,
        parent_desire_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Desire:
        """Create a new pending desire for an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = Desire(
                agent_id=agent_id,
                name=name,
                description=description,
                priority=priority,
                utility=_clamp(utility),
                activation_condition=dict(activation_condition) if activation_condition else None,
                satisfaction_condition=dict(satisfaction_condition) if satisfaction_condition else None,
                status=DesireStatus.PENDING,
                parent_desire_id=parent_desire_id,
                metadata=dict(metadata) if metadata else {},
            )
            state.desires[desire.id] = desire
            return desire

    def get_desire(self, agent_id: str, desire_id: str) -> Optional[Desire]:
        """Return a desire by ID, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.desires.get(desire_id)

    def activate_desire(self, agent_id: str, desire_id: str) -> Desire:
        """Activate a pending desire if its activation condition holds."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(desire_id)
            if desire is None:
                raise ValueError(
                    f"Desire '{desire_id}' not found for agent '{agent_id}'"
                )
            if desire.status == DesireStatus.PENDING:
                if _evaluate_condition(state.beliefs, desire.activation_condition):
                    desire.status = DesireStatus.ACTIVE
                    desire.activated_at = _now_iso()
                    self._total_desires_activated += 1
                    self._emit_event(
                        agent_id,
                        BDIEventKind.DESIRE_ACTIVATED,
                        {"desire_id": desire.id, "name": desire.name},
                    )
            return desire

    def satisfy_desire(self, agent_id: str, desire_id: str) -> Desire:
        """Mark a desire as satisfied."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(desire_id)
            if desire is None:
                raise ValueError(
                    f"Desire '{desire_id}' not found for agent '{agent_id}'"
                )
            if desire.status not in (DesireStatus.SATISFIED, DesireStatus.ABANDONED):
                desire.status = DesireStatus.SATISFIED
                desire.satisfied_at = _now_iso()
                if desire.activated_at is None:
                    desire.activated_at = desire.satisfied_at
                self._total_desires_satisfied += 1
                self._emit_event(
                    agent_id,
                    BDIEventKind.DESIRE_SATISFIED,
                    {"desire_id": desire.id, "name": desire.name},
                )
            return desire

    def fail_desire(self, agent_id: str, desire_id: str) -> Desire:
        """Mark a desire as failed."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(desire_id)
            if desire is None:
                raise ValueError(
                    f"Desire '{desire_id}' not found for agent '{agent_id}'"
                )
            if desire.status not in (DesireStatus.FAILED, DesireStatus.ABANDONED):
                desire.status = DesireStatus.FAILED
                self._total_desires_failed += 1
                self._emit_event(
                    agent_id,
                    BDIEventKind.DESIRE_FAILED,
                    {"desire_id": desire.id, "name": desire.name},
                )
            return desire

    def abandon_desire(self, agent_id: str, desire_id: str) -> Desire:
        """Mark a desire as abandoned."""
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(desire_id)
            if desire is None:
                raise ValueError(
                    f"Desire '{desire_id}' not found for agent '{agent_id}'"
                )
            desire.status = DesireStatus.ABANDONED
            return desire

    def list_desires(
        self, agent_id: str, status: Optional[DesireStatus] = None
    ) -> List[Desire]:
        """Return desires for an agent, optionally filtered by status."""
        with self._lock:
            state = self._require_state(agent_id)
            desires = list(state.desires.values())
            if status is None:
                return desires
            return [d for d in desires if d.status == status]

    def check_desire_conditions(
        self, agent_id: str
    ) -> Dict[str, List[str]]:
        """Check all desires and update their lifecycle state.

        Returns a dict with the IDs of desires that were activated,
        satisfied, or failed during this check.
        """
        with self._lock:
            state = self._require_state(agent_id)
            return self._check_desire_conditions_locked(state)

    # ------------------------------------------------------------------
    # Intention operations
    # ------------------------------------------------------------------

    def commit_intention(
        self,
        agent_id: str,
        desire_id: str,
        plan_steps: List[Dict[str, Any]],
        commitment_level: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Intention:
        """Create an intention to pursue a desire through plan steps.

        Honors the agent's commitment strategy, cancelling lower-priority
        intentions when capacity is exceeded.
        """
        with self._lock:
            state = self._require_state(agent_id)
            desire = state.desires.get(desire_id)
            if desire is None:
                raise ValueError(
                    f"Desire '{desire_id}' not found for agent '{agent_id}'"
                )
            if desire.status != DesireStatus.ACTIVE:
                raise ValueError(
                    f"Desire '{desire_id}' is not active "
                    f"(status={desire.status.value})"
                )

            strategy = state.commitment_strategy
            if strategy == CommitmentStrategy.SINGLE_MIND:
                for intention in self._active_intentions(state):
                    self._cancel_intention_locked(state, intention.id)
            elif strategy == CommitmentStrategy.BOUNDED:
                while len(self._active_intentions(state)) >= state.max_intentions:
                    victim = self._find_lowest_priority_intention(state)
                    if victim is None:
                        break
                    self._cancel_intention_locked(state, victim.id)

            steps = _normalize_plan_steps(plan_steps)
            intention = Intention(
                agent_id=agent_id,
                desire_id=desire_id,
                plan_steps=steps,
                current_step_index=0,
                status=IntentionStatus.COMMITTED,
                commitment_level=_clamp(commitment_level),
                metadata=dict(metadata) if metadata else {},
            )
            state.intentions[intention.id] = intention
            self._total_intentions_committed += 1
            self._emit_event(
                agent_id,
                BDIEventKind.INTENTION_COMMITTED,
                {"intention_id": intention.id, "desire_id": desire_id},
            )
            return intention

    def get_intention(
        self, agent_id: str, intention_id: str
    ) -> Optional[Intention]:
        """Return an intention by ID, or None."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.intentions.get(intention_id)

    def advance_intention(
        self, agent_id: str, intention_id: str
    ) -> Intention:
        """Advance an intention to its next plan step."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                raise ValueError(
                    f"Intention '{intention_id}' not found for agent '{agent_id}'"
                )
            return self._advance_intention_locked(state, intention)

    def fail_intention(
        self, agent_id: str, intention_id: str, reason: str = ""
    ) -> Intention:
        """Mark an intention as failed."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                raise ValueError(
                    f"Intention '{intention_id}' not found for agent '{agent_id}'"
                )
            intention.status = IntentionStatus.FAILED
            intention.completed_at = _now_iso()
            self._total_intentions_failed += 1
            self._emit_event(
                agent_id,
                BDIEventKind.INTENTION_FAILED,
                {"intention_id": intention_id, "desire_id": intention.desire_id, "reason": reason},
            )
            return intention

    def cancel_intention(
        self, agent_id: str, intention_id: str
    ) -> Intention:
        """Cancel an intention."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                raise ValueError(
                    f"Intention '{intention_id}' not found for agent '{agent_id}'"
                )
            self._cancel_intention_locked(state, intention_id)
            return intention

    def suspend_intention(
        self, agent_id: str, intention_id: str
    ) -> Intention:
        """Suspend an executing or committed intention."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                raise ValueError(
                    f"Intention '{intention_id}' not found for agent '{agent_id}'"
                )
            if intention.status in (IntentionStatus.COMMITTED, IntentionStatus.EXECUTING):
                intention.status = IntentionStatus.SUSPENDED
            return intention

    def resume_intention(
        self, agent_id: str, intention_id: str
    ) -> Intention:
        """Resume a suspended intention."""
        with self._lock:
            state = self._require_state(agent_id)
            intention = state.intentions.get(intention_id)
            if intention is None:
                raise ValueError(
                    f"Intention '{intention_id}' not found for agent '{agent_id}'"
                )
            if intention.status == IntentionStatus.SUSPENDED:
                intention.status = IntentionStatus.EXECUTING
            return intention

    def list_intentions(
        self, agent_id: str, status: Optional[IntentionStatus] = None
    ) -> List[Intention]:
        """Return intentions for an agent, optionally filtered by status."""
        with self._lock:
            state = self._require_state(agent_id)
            intentions = list(state.intentions.values())
            if status is None:
                return intentions
            return [i for i in intentions if i.status == status]

    # ------------------------------------------------------------------
    # Reasoning cycle
    # ------------------------------------------------------------------

    def get_current_phase(self, agent_id: str) -> ReasoningPhase:
        """Return the current reasoning phase for an agent."""
        with self._lock:
            state = self._require_state(agent_id)
            return state.current_phase

    def tick(self, agent_id: str) -> Dict[str, Any]:
        """Run one full BDI reasoning cycle for an agent.

        The cycle progresses through observe, deliberate, select, execute
        and reflect phases, returning a summary of what happened.
        """
        with self._lock:
            state = self._require_state(agent_id)
            self._emit_event(
                agent_id,
                BDIEventKind.CYCLE_STARTED,
                {"cycle_count": state.cycle_count + 1},
            )

            state.current_phase = ReasoningPhase.OBSERVE
            observe_result = self._check_desire_conditions_locked(state)

            state.current_phase = ReasoningPhase.DELIBERATE
            options = self._deliberate_locked(state)

            state.current_phase = ReasoningPhase.SELECT
            select_result = self._select_locked(state, options)

            state.current_phase = ReasoningPhase.EXECUTE
            execute_result = self._execute_locked(state)

            state.current_phase = ReasoningPhase.REFLECT
            reflect_result = self._reflect_locked(state)

            now = _now_iso()
            state.cycle_count += 1
            state.last_cycle_at = now
            state.current_phase = ReasoningPhase.REFLECT
            self._total_cycles += 1
            self._last_cycle_at = now
            self._emit_event(
                agent_id,
                BDIEventKind.CYCLE_COMPLETED,
                {"cycle_count": state.cycle_count},
            )

            return {
                "agent_id": agent_id,
                "phase": ReasoningPhase.REFLECT.value,
                "completed": True,
                "observe": observe_result,
                "deliberate": {
                    "options": options,
                    "option_count": len(options),
                },
                "select": select_result,
                "execute": execute_result,
                "reflect": reflect_result,
                "cycle_count": state.cycle_count,
            }

    def tick_all(self) -> Dict[str, Dict[str, Any]]:
        """Run one reasoning cycle for every registered agent."""
        with self._lock:
            agent_ids = list(self._states.keys())
        results: Dict[str, Dict[str, Any]] = {}
        for agent_id in agent_ids:
            results[agent_id] = self.tick(agent_id)
        return results

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: Optional[BDIEventKind],
        handler: Callable[[BDIEvent], None],
    ) -> str:
        """Subscribe to BDI events of a given kind (None for all kinds).

        Returns a handler ID that identifies the subscription.
        """
        handler_id = uuid.uuid4().hex
        with self._lock:
            bucket = self._handlers.setdefault(kind, {})
            bucket[handler_id] = handler
        return handler_id

    def list_events(
        self, agent_id: Optional[str] = None, limit: int = 100
    ) -> List[BDIEvent]:
        """Return recent events, optionally filtered by agent."""
        with self._lock:
            if agent_id is None:
                events = self._events
            else:
                events = self._events_by_agent.get(agent_id, [])
            if limit <= 0:
                return []
            return list(events[-limit:])

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def _compute_stats(self) -> Dict[str, Any]:
        total_beliefs = sum(len(s.beliefs) for s in self._states.values())
        total_desires = sum(len(s.desires) for s in self._states.values())
        total_intentions = sum(len(s.intentions) for s in self._states.values())
        return {
            "total_agents": len(self._states),
            "total_beliefs": total_beliefs,
            "total_desires": total_desires,
            "total_intentions": total_intentions,
            "total_cycles": self._total_cycles,
            "total_intentions_committed": self._total_intentions_committed,
            "total_intentions_completed": self._total_intentions_completed,
            "total_intentions_failed": self._total_intentions_failed,
            "total_beliefs_added": self._total_beliefs_added,
            "total_beliefs_updated": self._total_beliefs_updated,
            "total_beliefs_retracted": self._total_beliefs_retracted,
            "total_desires_activated": self._total_desires_activated,
            "total_desires_satisfied": self._total_desires_satisfied,
            "total_desires_failed": self._total_desires_failed,
            "last_cycle_at": self._last_cycle_at,
        }

    def get_status(self) -> Dict[str, Any]:
        """Return aggregate engine statistics."""
        with self._lock:
            return self._compute_stats()

    def get_snapshot(self) -> BDISnapshot:
        """Return a point-in-time snapshot of the engine."""
        with self._lock:
            stats = self._compute_stats()
            return BDISnapshot(
                agent_count=stats["total_agents"],
                total_beliefs=stats["total_beliefs"],
                total_desires=stats["total_desires"],
                total_intentions=stats["total_intentions"],
                stats=stats,
            )

    def reset(self) -> None:
        """Clear all agents, events, handlers and counters."""
        with self._lock:
            self._states.clear()
            self._events.clear()
            self._events_by_agent.clear()
            self._handlers.clear()
            self._total_cycles = 0
            self._total_intentions_committed = 0
            self._total_intentions_completed = 0
            self._total_intentions_failed = 0
            self._total_beliefs_added = 0
            self._total_beliefs_updated = 0
            self._total_beliefs_retracted = 0
            self._total_desires_activated = 0
            self._total_desires_satisfied = 0
            self._total_desires_failed = 0
            self._last_cycle_at = None

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Populate a demonstration agent with sample BDI state."""
        self.register_agent(
            "agent-demo",
            commitment_strategy=CommitmentStrategy.BOUNDED,
            max_intentions=5,
        )
        self.add_belief(
            "agent-demo",
            "health",
            80,
            source=BeliefSource.PERCEPTION,
            confidence=0.9,
        )
        self.add_belief(
            "agent-demo",
            "position",
            {"x": 50, "y": 30},
            source=BeliefSource.PERCEPTION,
            confidence=1.0,
        )
        self.add_belief(
            "agent-demo",
            "enemy_nearby",
            True,
            source=BeliefSource.INFERENCE,
            confidence=0.7,
        )
        self.add_desire(
            "agent-demo",
            "survive",
            "Maintain survivability under threat.",
            priority=DesirePriority.CRITICAL,
            utility=1.0,
            satisfaction_condition={
                "belief:health": {"operator": "gt", "value": 50}
            },
        )
        self.add_desire(
            "agent-demo",
            "reach_goal",
            "Reach the designated goal location.",
            priority=DesirePriority.HIGH,
            utility=0.8,
            activation_condition=None,
            satisfaction_condition={
                "belief:goal_reached": {"operator": "eq", "value": True}
            },
        )


def get_bdi_engine() -> BDIArchitectureEngine:
    """Return the shared BDIArchitectureEngine singleton instance."""
    return BDIArchitectureEngine.get_instance()
