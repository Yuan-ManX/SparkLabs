"""
SparkLabs Agent - Coalition Formation and Negotiation Engine

This module implements a game-theoretic system where AI agents dynamically
form coalitions, negotiate resource sharing, and distribute rewards fairly
using Shapley value computation. It is part of the SparkLabs AI-native game
engine and provides the coordination layer through which autonomous agents
collaborate on shared objectives.

Core concepts:

  1. Coalition Formation
       Agents propose coalitions with specific task objectives, resource
       needs, and reward splits. Target agents respond to proposals, and
       once enough acceptances are gathered, a coalition is formally
       established with a leader, members, roles, and a shared resource
       pool. Formation patterns include top-down, bottom-up, emergent,
       auction-based, and consensus-driven approaches.

  2. Negotiation
       Within and across coalitions, agents negotiate through structured
       rounds. Each round carries a proposal and a set of responses. The
       engine supports cooperative, competitive, compromising,
       accommodating, and avoiding negotiation strategies, each influencing
       how the engine evaluates counter-offers and resolve thresholds.

  3. Contribution Tracking
       Every agent action inside a coalition is recorded as a contribution
       along one of six metric axes: task completion, quality, speed,
       innovation, reliability, and collaboration. Contributions feed
       directly into reward distribution and Shapley value computation.

  4. Shapley Value Computation
       For coalitions of eight or fewer members, the engine computes exact
       Shapley values by enumerating all member permutations. The Shapley
       value represents each agent's average marginal contribution to the
       coalition and serves as the basis for fair reward distribution.

  5. Fairness Evaluation
       Reward fairness is measured by comparing the reward share vector
       against the contribution share vector. The engine derives a Gini-style
       discrepancy score and reports a fairness score in [0.0, 1.0], where
       1.0 indicates a perfectly proportional distribution.

  6. Dynamic Reconfiguration
       Coalitions can be reconfigured mid-lifecycle: members may be added or
       removed, roles reassigned, and resources rebalanced. The engine
       recomputes Shapley values and fairness scores after each
       reconfiguration to keep distribution current.

  7. Lifecycle Management
       A tick-driven loop expires stale proposals, auto-dissolves inactive
       coalitions, and advances negotiation rounds past their timeout. All
       state mutations emit observable events that consumers can inspect or
       replay for debugging and analytics.

Architecture:
  AgentCoalitionNegotiator (Singleton, double-checked locking with
                            threading.RLock)
    |-- AgentProfile            -- registered agent with skills and resources
    |-- CoalitionProposal       -- a proposal to form or modify a coalition
    |-- NegotiationRound        -- one round of structured negotiation
    |-- Coalition               -- an active or historical coalition
    |-- ContributionRecord      -- a single contribution measurement
    |-- RewardDistribution      -- a completed reward payout
    |-- CoalitionStats          -- aggregate engine statistics
    |-- CoalitionConfig         -- runtime configuration
    |-- CoalitionSnapshot       -- point-in-time engine state
    |-- CoalitionEvent          -- observable lifecycle event

All public mutating methods are protected by a reentrant lock so the
negotiator is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.

Usage:
    negotiator = get_coalition_negotiator()
    ok, msg, profile = negotiator.register_agent(
        "agent_001", "Aria", AgentRole.LEADER,
        ["strategy", "planning"], 0.92,
    )
    ok, msg, proposal = negotiator.propose_coalition(
        "agent_001", ["agent_002", "agent_003"],
        "Clear the dungeon of the red dragon",
        {"compute": 50.0, "knowledge": 30.0},
        NegotiationStrategy.COOPERATIVE,
    )
    ok, msg, coalition = negotiator.form_coalition(proposal.proposal_id)
    ok, msg, shapley = negotiator.compute_shapley_value(coalition.coalition_id)
    ok, msg, dist = negotiator.distribute_rewards(
        coalition.coalition_id, 1000.0, "shapley",
    )
"""

from __future__ import annotations

import itertools
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Module-Level Singleton Lock and Instance
# ---------------------------------------------------------------------------

_lock = threading.RLock()
_instance: Optional["AgentCoalitionNegotiator"] = None


# ---------------------------------------------------------------------------
# Capacity Constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 2000
_MAX_PROPOSALS: int = 3000
_MAX_COALITIONS: int = 1000
_MAX_NEGOTIATIONS: int = 4000
_MAX_CONTRIBUTIONS: int = 10000
_MAX_DISTRIBUTIONS: int = 5000
_MAX_EVENTS: int = 8000
_MAX_HISTORY_PER_AGENT: int = 200

_SHAPLEY_MAX_MEMBERS: int = 8
_NEGOTIATION_DEFAULT_TIMEOUT: int = 100
_INACTIVITY_DISSOLVE_TICKS: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current Unix timestamp as a float."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:10]
    return f"{prefix}_{base}" if prefix else base


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
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a list until within bounds."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _safe_div(numerator: float, denominator: float) -> float:
    """Return numerator / denominator, or 0.0 if denominator is zero."""
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _gini_coefficient(values: List[float]) -> float:
    """Compute the Gini coefficient for a list of non-negative values.

    Returns a value in [0.0, 1.0] where 0.0 means perfect equality and
    1.0 means maximal inequality. An empty or all-zero list yields 0.0.
    """
    n = len(values)
    if n == 0:
        return 0.0
    sorted_vals = sorted(v for v in values if v >= 0)
    total = sum(sorted_vals)
    if total == 0:
        return 0.0
    cumulative = 0.0
    weighted_sum = 0.0
    for index, val in enumerate(sorted_vals, start=1):
        cumulative += val
        weighted_sum += index * val
    gini = (2.0 * weighted_sum) / (n * total) - (n + 1.0) / n
    return _clamp(gini, 0.0, 1.0)


def _cosine_similarity(vec_a: Dict[str, float],
                       vec_b: Dict[str, float]) -> float:
    """Compute cosine similarity between two sparse vectors."""
    if not vec_a or not vec_b:
        return 0.0
    dot = sum(vec_a.get(k, 0.0) * vec_b.get(k, 0.0) for k in vec_a)
    norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
    norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return _clamp(dot / (norm_a * norm_b), 0.0, 1.0)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CoalitionStatus(str, Enum):
    """Lifecycle status of a coalition."""

    FORMING = "forming"
    ACTIVE = "active"
    NEGOTIATING = "negotiating"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"


class NegotiationStatus(str, Enum):
    """Lifecycle status of a proposal or negotiation round."""

    PENDING = "pending"
    ACTIVE = "active"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"
    COUNTERED = "countered"


class AgentRole(str, Enum):
    """Roles an agent can hold within a coalition."""

    LEADER = "leader"
    CONTRIBUTOR = "contributor"
    SPECIALIST = "specialist"
    SUPPORTER = "supporter"
    NEGOTIATOR = "negotiator"


class ResourceType(str, Enum):
    """Categories of resources that agents can pool into a coalition."""

    COMPUTE = "compute"
    KNOWLEDGE = "knowledge"
    SKILL = "skill"
    TIME = "time"
    ASSET = "asset"
    INFLUENCE = "influence"


class ContributionMetric(str, Enum):
    """Axes along which agent contributions are measured."""

    TASK_COMPLETION = "task_completion"
    QUALITY = "quality"
    SPEED = "speed"
    INNOVATION = "innovation"
    RELIABILITY = "reliability"
    COLLABORATION = "collaboration"


class CoalitionEventKind(str, Enum):
    """Observable lifecycle events emitted by the negotiator."""

    COALITION_FORMED = "coalition_formed"
    COALITION_DISSOLVED = "coalition_dissolved"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    NEGOTIATION_STARTED = "negotiation_started"
    NEGOTIATION_RESOLVED = "negotiation_resolved"
    REWARD_DISTRIBUTED = "reward_distributed"
    ROLE_ASSIGNED = "role_assigned"
    RESOURCE_POOLED = "resource_pooled"
    STRATEGY_UPDATED = "strategy_updated"


class NegotiationStrategy(str, Enum):
    """Negotiation strategies influencing offer evaluation and resolution."""

    COOPERATIVE = "cooperative"
    COMPETITIVE = "competitive"
    COMPROMISING = "compromising"
    ACCOMMODATING = "accommodating"
    AVOIDING = "avoiding"


class FormationPattern(str, Enum):
    """Patterns through which a coalition can be assembled."""

    TOP_DOWN = "top_down"
    BOTTOM_UP = "bottom_up"
    EMERGENT = "emergent"
    AUCTION_BASED = "auction_based"
    CONSENSUS = "consensus"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class AgentProfile:
    """A registered AI agent available for coalition participation.

    Each agent has a unique identifier, a display name, a primary role, a
    set of skills, a resource contribution profile, a reliability score,
    and a history of coalitions it has participated in.
    """

    agent_id: str = ""
    name: str = ""
    role: AgentRole = AgentRole.CONTRIBUTOR
    skills: List[str] = field(default_factory=list)
    resource_contribution: Dict[str, float] = field(default_factory=dict)
    reliability_score: float = 0.5
    past_coalitions: List[str] = field(default_factory=list)
    current_coalition_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this agent profile to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value if isinstance(self.role, AgentRole)
            else str(self.role),
            "skills": list(self.skills),
            "resource_contribution": dict(self.resource_contribution),
            "reliability_score": self.reliability_score,
            "past_coalitions": list(self.past_coalitions),
            "current_coalition_id": self.current_coalition_id,
        }


@dataclass
class CoalitionProposal:
    """A proposal to form a coalition with target agents.

    The proposer specifies target agents, a task description, resource
    needs, a proposed reward split, a negotiation strategy, and an expiry
    tick after which the proposal is considered stale.
    """

    proposal_id: str = ""
    proposer_id: str = ""
    target_ids: List[str] = field(default_factory=list)
    task_description: str = ""
    resource_needs: Dict[str, float] = field(default_factory=dict)
    reward_split: Dict[str, float] = field(default_factory=dict)
    strategy: NegotiationStrategy = NegotiationStrategy.COOPERATIVE
    expiry_tick: int = 0
    status: NegotiationStatus = NegotiationStatus.PENDING
    responses: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    formation_pattern: FormationPattern = FormationPattern.TOP_DOWN

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this proposal to a JSON-friendly dictionary."""
        return {
            "proposal_id": self.proposal_id,
            "proposer_id": self.proposer_id,
            "target_ids": list(self.target_ids),
            "task_description": self.task_description,
            "resource_needs": dict(self.resource_needs),
            "reward_split": dict(self.reward_split),
            "strategy": self.strategy.value if isinstance(
                self.strategy, NegotiationStrategy
            ) else str(self.strategy),
            "expiry_tick": self.expiry_tick,
            "status": self.status.value if isinstance(
                self.status, NegotiationStatus
            ) else str(self.status),
            "responses": dict(self.responses),
            "created_at": self.created_at,
            "formation_pattern": self.formation_pattern.value if isinstance(
                self.formation_pattern, FormationPattern
            ) else str(self.formation_pattern),
        }


@dataclass
class NegotiationRound:
    """A single round of structured negotiation within a coalition.

    The proposer issues a proposal, and each target agent responds. The
    round remains active until all targets have responded or the timeout
    expires.
    """

    round_id: str = ""
    coalition_id: str = ""
    proposer_id: str = ""
    proposal: CoalitionProposal = field(
        default_factory=CoalitionProposal
    )
    responses: Dict[str, str] = field(default_factory=dict)
    status: NegotiationStatus = NegotiationStatus.PENDING
    timestamp: float = field(default_factory=_now)
    expiry_tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this negotiation round to a JSON-friendly dictionary."""
        return {
            "round_id": self.round_id,
            "coalition_id": self.coalition_id,
            "proposer_id": self.proposer_id,
            "proposal": self.proposal.to_dict()
            if self.proposal else {},
            "responses": dict(self.responses),
            "status": self.status.value if isinstance(
                self.status, NegotiationStatus
            ) else str(self.status),
            "timestamp": self.timestamp,
            "expiry_tick": self.expiry_tick,
        }


@dataclass
class Coalition:
    """An active or historical coalition of agents.

    The coalition has a leader, a set of members each holding a role, a
    shared resource pool, a task objective, and tracks Shapley values and
    total contributions per member for reward distribution.
    """

    coalition_id: str = ""
    name: str = ""
    leader_id: str = ""
    members: Dict[str, AgentRole] = field(default_factory=dict)
    formation_pattern: FormationPattern = FormationPattern.TOP_DOWN
    shared_resources: Dict[str, float] = field(default_factory=dict)
    task_objective: str = ""
    status: CoalitionStatus = CoalitionStatus.FORMING
    formed_at_tick: int = 0
    shapley_values: Dict[str, float] = field(default_factory=dict)
    total_contributions: Dict[str, float] = field(default_factory=dict)
    last_activity_tick: int = 0
    dissolved_at_tick: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this coalition to a JSON-friendly dictionary."""
        return {
            "coalition_id": self.coalition_id,
            "name": self.name,
            "leader_id": self.leader_id,
            "members": {
                aid: role.value if isinstance(role, AgentRole)
                else str(role)
                for aid, role in self.members.items()
            },
            "formation_pattern": self.formation_pattern.value if isinstance(
                self.formation_pattern, FormationPattern
            ) else str(self.formation_pattern),
            "shared_resources": dict(self.shared_resources),
            "task_objective": self.task_objective,
            "status": self.status.value if isinstance(
                self.status, CoalitionStatus
            ) else str(self.status),
            "formed_at_tick": self.formed_at_tick,
            "shapley_values": dict(self.shapley_values),
            "total_contributions": dict(self.total_contributions),
            "last_activity_tick": self.last_activity_tick,
            "dissolved_at_tick": self.dissolved_at_tick,
        }


@dataclass
class ContributionRecord:
    """A single contribution measurement for one agent in one coalition."""

    agent_id: str = ""
    coalition_id: str = ""
    metric: ContributionMetric = ContributionMetric.TASK_COMPLETION
    value: float = 0.0
    tick: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this contribution record to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "coalition_id": self.coalition_id,
            "metric": self.metric.value if isinstance(
                self.metric, ContributionMetric
            ) else str(self.metric),
            "value": self.value,
            "tick": self.tick,
        }


@dataclass
class RewardDistribution:
    """A completed reward payout for a coalition.

    The total reward is split among members according to a distribution
    method. The fairness score compares the actual shares against
    contribution shares.
    """

    distribution_id: str = ""
    coalition_id: str = ""
    total_reward: float = 0.0
    shares: Dict[str, float] = field(default_factory=dict)
    method: str = "shapley"
    timestamp: float = field(default_factory=_now)
    fairness_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this reward distribution to a JSON-friendly dictionary."""
        return {
            "distribution_id": self.distribution_id,
            "coalition_id": self.coalition_id,
            "total_reward": self.total_reward,
            "shares": dict(self.shares),
            "method": self.method,
            "timestamp": self.timestamp,
            "fairness_score": self.fairness_score,
        }


@dataclass
class CoalitionStats:
    """Aggregate statistics about the coalition negotiator engine."""

    total_coalitions_formed: int = 0
    total_dissolved: int = 0
    active_coalitions: int = 0
    total_negotiations: int = 0
    successful_negotiations: int = 0
    failed_negotiations: int = 0
    total_rewards_distributed: float = 0.0
    average_fairness_score: float = 0.0
    average_formation_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_coalitions_formed": self.total_coalitions_formed,
            "total_dissolved": self.total_dissolved,
            "active_coalitions": self.active_coalitions,
            "total_negotiations": self.total_negotiations,
            "successful_negotiations": self.successful_negotiations,
            "failed_negotiations": self.failed_negotiations,
            "total_rewards_distributed": self.total_rewards_distributed,
            "average_fairness_score": self.average_fairness_score,
            "average_formation_time": self.average_formation_time,
        }


@dataclass
class CoalitionConfig:
    """Runtime configuration for the coalition negotiator."""

    max_coalitions: int = 100
    max_members_per_coalition: int = 12
    negotiation_timeout_ticks: int = 100
    enable_dynamic_reconfiguration: bool = True
    enable_shapley_calculation: bool = True
    fairness_threshold: float = 0.7
    min_coalition_size: int = 2
    max_coalition_size: int = 8
    reward_pool_base: float = 1000.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this configuration to a JSON-friendly dictionary."""
        return {
            "max_coalitions": self.max_coalitions,
            "max_members_per_coalition": self.max_members_per_coalition,
            "negotiation_timeout_ticks": self.negotiation_timeout_ticks,
            "enable_dynamic_reconfiguration":
                self.enable_dynamic_reconfiguration,
            "enable_shapley_calculation":
                self.enable_shapley_calculation,
            "fairness_threshold": self.fairness_threshold,
            "min_coalition_size": self.min_coalition_size,
            "max_coalition_size": self.max_coalition_size,
            "reward_pool_base": self.reward_pool_base,
        }


@dataclass
class CoalitionSnapshot:
    """A point-in-time snapshot of the negotiator engine state."""

    tick_count: int = 0
    active_coalitions: int = 0
    total_members: int = 0
    total_negotiations: int = 0
    total_rewards: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "tick_count": self.tick_count,
            "active_coalitions": self.active_coalitions,
            "total_members": self.total_members,
            "total_negotiations": self.total_negotiations,
            "total_rewards": self.total_rewards,
        }


@dataclass
class CoalitionEvent:
    """An observable lifecycle event emitted by the negotiator."""

    event_id: str = ""
    kind: CoalitionEventKind = CoalitionEventKind.COALITION_FORMED
    tick: int = 0
    coalition_id: str = ""
    agent_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value if isinstance(
                self.kind, CoalitionEventKind
            ) else str(self.kind),
            "tick": self.tick,
            "coalition_id": self.coalition_id,
            "agent_id": self.agent_id,
            "payload": dict(self.payload) if self.payload else {},
        }


# ---------------------------------------------------------------------------
# Agent Coalition Negotiator (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class AgentCoalitionNegotiator:
    """Game-theoretic coalition formation and negotiation engine.

    The negotiator maintains a registry of agents, a pool of coalition
    proposals, active and historical coalitions, contribution records,
    reward distributions, and negotiation rounds. It computes Shapley
    values for fair reward distribution, evaluates fairness using a Gini
    coefficient, and drives the simulation forward through a tick loop
    that expires stale proposals, dissolves inactive coalitions, and
    advances negotiation rounds.

    The class implements the singleton pattern with double-checked
    locking using ``threading.RLock``. Consumers should obtain the
    instance through :meth:`get_instance` or the module-level
    :func:`get_coalition_negotiator` factory.
    """

    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction and Singleton
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        # Primary stores keyed by id.
        self._agents: Dict[str, AgentProfile] = {}
        self._proposals: Dict[str, CoalitionProposal] = {}
        self._coalitions: Dict[str, Coalition] = {}
        self._negotiations: Dict[str, NegotiationRound] = {}
        self._contributions: List[ContributionRecord] = []
        self._distributions: Dict[str, RewardDistribution] = {}

        # Auxiliary stores.
        self._events: List[CoalitionEvent] = []
        self._config = CoalitionConfig()
        self._tick_count: int = 0

        # Statistics accumulators.
        self._total_coalitions_formed: int = 0
        self._total_dissolved: int = 0
        self._total_negotiations: int = 0
        self._successful_negotiations: int = 0
        self._failed_negotiations: int = 0
        self._total_rewards_distributed: float = 0.0
        self._fairness_scores: List[float] = []
        self._formation_times: List[float] = []

        # Agent coalition history for quick lookup.
        self._agent_history: Dict[str, List[str]] = {}

        # Flags.
        self._initialized: bool = False
        self._seeded: bool = False

        # Seed baseline data.
        self._seed_data()

    @classmethod
    def get_instance(cls) -> "AgentCoalitionNegotiator":
        """Return the singleton AgentCoalitionNegotiator instance."""
        global _instance
        if _instance is None:
            with _lock:
                if _instance is None:
                    _instance = cls()
        return _instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: CoalitionEventKind,
        coalition_id: str = "",
        agent_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a lifecycle event in the event log."""
        event = CoalitionEvent(
            event_id=_new_id("evt"),
            kind=kind,
            tick=self._tick_count,
            coalition_id=coalition_id,
            agent_id=agent_id,
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _touch_coalition(self, coalition_id: str) -> None:
        """Update the last-activity tick for a coalition."""
        coalition = self._coalitions.get(coalition_id)
        if coalition is not None:
            coalition.last_activity_tick = self._tick_count

    def _agent_contribution_value(
        self, coalition: Coalition, agent_id: str
    ) -> float:
        """Return the total contribution value for an agent in a coalition.

        If no contributions have been recorded, the agent's reliability
        score (scaled by 100) is used as a fallback estimate so that
        Shapley computation still produces meaningful results.
        """
        recorded = coalition.total_contributions.get(agent_id)
        if recorded is not None and recorded > 0:
            return recorded
        profile = self._agents.get(agent_id)
        if profile is not None:
            return profile.reliability_score * 100.0
        return 0.0

    def _coalition_value(
        self, coalition: Coalition, subset: frozenset
    ) -> float:
        """Compute the worth of a subset of coalition members.

        The worth is the sum of individual contribution values, with a
        synergy bonus proportional to subset size to model cooperative
        gains.
        """
        total = 0.0
        for agent_id in subset:
            total += self._agent_contribution_value(coalition, agent_id)
        # Synergy bonus: cooperative gain grows with subset size.
        size = len(subset)
        if size > 1:
            total *= 1.0 + 0.05 * (size - 1)
        return total

    def _compute_fairness_from_shares(
        self,
        shares: Dict[str, float],
        contributions: Dict[str, float],
    ) -> float:
        """Compute a fairness score comparing reward shares to contributions.

        Returns a value in [0.0, 1.0] where 1.0 means the reward shares
        are perfectly proportional to contributions.
        """
        agents = set(shares.keys()) | set(contributions.keys())
        if not agents:
            return 1.0
        total_reward = sum(shares.values())
        total_contrib = sum(contributions.values())
        if total_reward == 0 and total_contrib == 0:
            return 1.0
        discrepancies: List[float] = []
        for agent_id in agents:
            reward_share = _safe_div(
                shares.get(agent_id, 0.0), total_reward
            )
            contrib_share = _safe_div(
                contributions.get(agent_id, 0.0), total_contrib
            )
            discrepancies.append(abs(reward_share - contrib_share))
        # Sum of absolute share discrepancies ranges from 0 to 2.
        # Normalize to [0, 1] and invert so 1.0 is fair.
        total_discrepancy = sum(discrepancies) / 2.0
        return _clamp(1.0 - total_discrepancy, 0.0, 1.0)

    # ------------------------------------------------------------------
    # Agent Management
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        name: str,
        role: AgentRole,
        skills: List[str],
        reliability_score: float,
    ) -> Tuple[bool, str, Optional[AgentProfile]]:
        """Register a new agent in the negotiator.

        Returns (success, message, profile). If the agent_id already
        exists, registration fails.
        """
        with _lock:
            if not agent_id:
                return False, "agent_id is required", None
            if agent_id in self._agents:
                return (
                    False,
                    f"agent '{agent_id}' is already registered",
                    None,
                )
            if len(self._agents) >= _MAX_AGENTS:
                return False, "agent capacity reached", None
            clamped_score = _clamp(reliability_score, 0.0, 1.0)
            profile = AgentProfile(
                agent_id=agent_id,
                name=name or agent_id,
                role=role if isinstance(role, AgentRole)
                else AgentRole(role),
                skills=list(skills) if skills else [],
                resource_contribution={},
                reliability_score=clamped_score,
                past_coalitions=[],
                current_coalition_id=None,
            )
            self._agents[agent_id] = profile
            self._agent_history.setdefault(agent_id, [])
            self._emit(
                CoalitionEventKind.ROLE_ASSIGNED,
                agent_id=agent_id,
                payload={
                    "name": profile.name,
                    "role": profile.role.value,
                    "skills": list(profile.skills),
                    "reliability_score": profile.reliability_score,
                },
            )
            return True, "agent registered", profile

    def remove_agent(self, agent_id: str) -> Tuple[bool, str]:
        """Remove an agent from the negotiator.

        The agent is also removed from any coalition it belongs to.
        """
        with _lock:
            if agent_id not in self._agents:
                return False, f"agent '{agent_id}' not found"
            profile = self._agents[agent_id]
            # Remove from current coalition if applicable.
            if profile.current_coalition_id:
                coalition = self._coalitions.get(
                    profile.current_coalition_id
                )
                if coalition and agent_id in coalition.members:
                    del coalition.members[agent_id]
                    coalition.total_contributions.pop(agent_id, None)
                    coalition.shapley_values.pop(agent_id, None)
                    self._emit(
                        CoalitionEventKind.MEMBER_LEFT,
                        coalition_id=coalition.coalition_id,
                        agent_id=agent_id,
                        payload={"reason": "agent_removed"},
                    )
                    # If the coalition is now below minimum size, dissolve.
                    if len(coalition.members) < self._config.min_coalition_size:
                        coalition.status = CoalitionStatus.DISSOLVED
                        coalition.dissolved_at_tick = self._tick_count
                        self._total_dissolved += 1
                        self._emit(
                            CoalitionEventKind.COALITION_DISSOLVED,
                            coalition_id=coalition.coalition_id,
                            payload={"reason": "below_minimum_size"},
                        )
            del self._agents[agent_id]
            return True, "agent removed"

    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Return the agent profile for the given id, or None."""
        with _lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentProfile]:
        """Return all registered agent profiles."""
        with _lock:
            return list(self._agents.values())

    def list_agents_by_role(self, role: AgentRole) -> List[AgentProfile]:
        """Return all agents matching the given role."""
        with _lock:
            target = role.value if isinstance(role, AgentRole) else str(role)
            return [
                p for p in self._agents.values()
                if (p.role.value if isinstance(p.role, AgentRole)
                    else str(p.role)) == target
            ]

    # ------------------------------------------------------------------
    # Proposal Management
    # ------------------------------------------------------------------

    def propose_coalition(
        self,
        proposer_id: str,
        target_ids: List[str],
        task_description: str,
        resource_needs: Dict[str, float],
        strategy: NegotiationStrategy,
    ) -> Tuple[bool, str, Optional[CoalitionProposal]]:
        """Create a new coalition proposal.

        The proposer specifies target agents, a task description, resource
        needs, and a negotiation strategy. The reward split is initialized
        evenly and can be adjusted through negotiation. Returns
        (success, message, proposal).
        """
        with _lock:
            if proposer_id not in self._agents:
                return False, f"proposer '{proposer_id}' not registered", None
            if not target_ids:
                return False, "at least one target agent is required", None
            for tid in target_ids:
                if tid not in self._agents:
                    return False, f"target '{tid}' not registered", None
            if len(target_ids) + 1 > self._config.max_members_per_coalition:
                return False, "too many targets for max coalition size", None
            if len(self._proposals) >= _MAX_PROPOSALS:
                return False, "proposal capacity reached", None
            strat = strategy if isinstance(strategy, NegotiationStrategy) \
                else NegotiationStrategy(strategy)
            all_members = [proposer_id] + list(target_ids)
            even_share = _safe_div(1.0, float(len(all_members)))
            reward_split = {aid: round(even_share, 4) for aid in all_members}
            proposal = CoalitionProposal(
                proposal_id=_new_id("prp"),
                proposer_id=proposer_id,
                target_ids=list(target_ids),
                task_description=task_description or "",
                resource_needs=dict(resource_needs) if resource_needs else {},
                reward_split=reward_split,
                strategy=strat,
                expiry_tick=self._tick_count
                + self._config.negotiation_timeout_ticks,
                status=NegotiationStatus.PENDING,
                responses={},
                created_at=_now(),
                formation_pattern=FormationPattern.TOP_DOWN,
            )
            self._proposals[proposal.proposal_id] = proposal
            self._emit(
                CoalitionEventKind.NEGOTIATION_STARTED,
                agent_id=proposer_id,
                payload={
                    "proposal_id": proposal.proposal_id,
                    "target_ids": list(target_ids),
                    "task_description": task_description,
                    "strategy": strat.value,
                },
            )
            return True, "proposal created", proposal

    def respond_to_proposal(
        self,
        agent_id: str,
        proposal_id: str,
        response: str,
        counter_offer: Optional[Dict[str, float]] = None,
    ) -> Tuple[bool, str]:
        """Record an agent's response to a coalition proposal.

        Valid responses are "accept", "reject", and "counter". When a
        counter-offer is supplied, the reward split is updated and the
        proposal status becomes COUNTERED.
        """
        with _lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                return False, f"proposal '{proposal_id}' not found"
            if proposal.status in (
                NegotiationStatus.ACCEPTED,
                NegotiationStatus.REJECTED,
                NegotiationStatus.EXPIRED,
            ):
                return False, f"proposal is already {proposal.status.value}"
            if agent_id not in proposal.target_ids \
                    and agent_id != proposal.proposer_id:
                return False, "agent is not a target of this proposal"
            if self._tick_count > proposal.expiry_tick:
                proposal.status = NegotiationStatus.EXPIRED
                return False, "proposal has expired"
            normalized = response.lower().strip()
            if normalized not in ("accept", "reject", "counter"):
                return False, "response must be 'accept', 'reject', or 'counter'"
            proposal.responses[agent_id] = normalized
            if normalized == "counter" and counter_offer:
                # Apply the counter-offer to the reward split.
                for aid, share in counter_offer.items():
                    if aid in proposal.reward_split:
                        proposal.reward_split[aid] = float(share)
                proposal.status = NegotiationStatus.COUNTERED
                self._emit(
                    CoalitionEventKind.STRATEGY_UPDATED,
                    agent_id=agent_id,
                    payload={
                        "proposal_id": proposal_id,
                        "counter_offer": dict(counter_offer),
                    },
                )
                return True, "counter-offer recorded"
            # Evaluate whether all targets have responded.
            all_responded = all(
                tid in proposal.responses for tid in proposal.target_ids
            )
            if all_responded:
                all_accepted = all(
                    proposal.responses.get(tid) == "accept"
                    for tid in proposal.target_ids
                )
                if all_accepted:
                    proposal.status = NegotiationStatus.ACCEPTED
                else:
                    proposal.status = NegotiationStatus.REJECTED
            self._emit(
                CoalitionEventKind.NEGOTIATION_RESOLVED,
                agent_id=agent_id,
                payload={
                    "proposal_id": proposal_id,
                    "response": normalized,
                    "status": proposal.status.value,
                },
            )
            return True, f"response '{normalized}' recorded"

    def get_proposal(self, proposal_id: str) -> Optional[CoalitionProposal]:
        """Return the proposal for the given id, or None."""
        with _lock:
            return self._proposals.get(proposal_id)

    def list_proposals(
        self, status: Optional[NegotiationStatus] = None
    ) -> List[CoalitionProposal]:
        """Return proposals, optionally filtered by status."""
        with _lock:
            if status is None:
                return list(self._proposals.values())
            target = status.value if isinstance(
                status, NegotiationStatus
            ) else str(status)
            return [
                p for p in self._proposals.values()
                if (p.status.value if isinstance(p.status, NegotiationStatus)
                    else str(p.status)) == target
            ]

    # ------------------------------------------------------------------
    # Coalition Lifecycle
    # ------------------------------------------------------------------

    def form_coalition(
        self, proposal_id: str
    ) -> Tuple[bool, str, Optional[Coalition]]:
        """Form a coalition from an accepted proposal.

        The proposer becomes the leader and all target agents become
        contributors. Resources from the proposal are seeded into the
        shared pool. Returns (success, message, coalition).
        """
        with _lock:
            proposal = self._proposals.get(proposal_id)
            if proposal is None:
                return False, f"proposal '{proposal_id}' not found", None
            if proposal.status != NegotiationStatus.ACCEPTED:
                return (
                    False,
                    f"proposal status is '{proposal.status.value}', "
                    "must be 'accepted'",
                    None,
                )
            if len(self._coalitions) >= _MAX_COALITIONS:
                return False, "coalition capacity reached", None
            active_count = sum(
                1 for c in self._coalitions.values()
                if c.status == CoalitionStatus.ACTIVE
            )
            if active_count >= self._config.max_coalitions:
                return False, "max active coalitions reached", None
            all_members = [proposal.proposer_id] + list(proposal.target_ids)
            if len(all_members) < self._config.min_coalition_size:
                return False, "coalition below minimum size", None
            members: Dict[str, AgentRole] = {}
            for aid in all_members:
                if aid == proposal.proposer_id:
                    members[aid] = AgentRole.LEADER
                else:
                    profile = self._agents.get(aid)
                    if profile and profile.role == AgentRole.SPECIALIST:
                        members[aid] = AgentRole.SPECIALIST
                    else:
                        members[aid] = AgentRole.CONTRIBUTOR
            coalition = Coalition(
                coalition_id=_new_id("col"),
                name=f"Coalition-{proposal.proposal_id[:6]}",
                leader_id=proposal.proposer_id,
                members=members,
                formation_pattern=proposal.formation_pattern,
                shared_resources=dict(proposal.resource_needs),
                task_objective=proposal.task_description,
                status=CoalitionStatus.ACTIVE,
                formed_at_tick=self._tick_count,
                shapley_values={},
                total_contributions={aid: 0.0 for aid in all_members},
                last_activity_tick=self._tick_count,
                dissolved_at_tick=None,
            )
            self._coalitions[coalition.coalition_id] = coalition
            self._total_coalitions_formed += 1
            # Update agent profiles.
            for aid in all_members:
                profile = self._agents.get(aid)
                if profile:
                    profile.current_coalition_id = coalition.coalition_id
                    if coalition.coalition_id not in profile.past_coalitions:
                        profile.past_coalitions.append(
                            coalition.coalition_id
                        )
                    self._agent_history.setdefault(aid, []).append(
                        coalition.coalition_id
                    )
                    _evict_fifo_list(
                        self._agent_history[aid],
                        _MAX_HISTORY_PER_AGENT,
                    )
            # Compute initial Shapley values if enabled.
            if self._config.enable_shapley_calculation:
                self._compute_shapley_internal(coalition)
            self._emit(
                CoalitionEventKind.COALITION_FORMED,
                coalition_id=coalition.coalition_id,
                agent_id=proposal.proposer_id,
                payload={
                    "name": coalition.name,
                    "members": list(members.keys()),
                    "task_objective": coalition.task_objective,
                    "formation_pattern": coalition.formation_pattern.value,
                },
            )
            return True, "coalition formed", coalition

    def dissolve_coalition(
        self, coalition_id: str, reason: str = ""
    ) -> Tuple[bool, str]:
        """Dissolve a coalition, releasing all members.

        Shapley values and contributions are preserved for historical
        analysis, but the coalition status becomes DISSOLVED and all
        members' current_coalition_id is cleared.
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if coalition.status == CoalitionStatus.DISSOLVED:
                return False, "coalition is already dissolved"
            coalition.status = CoalitionStatus.DISSOLVED
            coalition.dissolved_at_tick = self._tick_count
            # Clear agent coalition assignments.
            for aid in list(coalition.members.keys()):
                profile = self._agents.get(aid)
                if profile and profile.current_coalition_id == coalition_id:
                    profile.current_coalition_id = None
                self._emit(
                    CoalitionEventKind.MEMBER_LEFT,
                    coalition_id=coalition_id,
                    agent_id=aid,
                    payload={"reason": reason or "coalition_dissolved"},
                )
            self._total_dissolved += 1
            self._emit(
                CoalitionEventKind.COALITION_DISSOLVED,
                coalition_id=coalition_id,
                payload={"reason": reason or "manual_dissolution"},
            )
            return True, "coalition dissolved"

    def get_coalition(self, coalition_id: str) -> Optional[Coalition]:
        """Return the coalition for the given id, or None."""
        with _lock:
            return self._coalitions.get(coalition_id)

    def list_coalitions(
        self, status: Optional[CoalitionStatus] = None
    ) -> List[Coalition]:
        """Return coalitions, optionally filtered by status."""
        with _lock:
            if status is None:
                return list(self._coalitions.values())
            target = status.value if isinstance(
                status, CoalitionStatus
            ) else str(status)
            return [
                c for c in self._coalitions.values()
                if (c.status.value if isinstance(c.status, CoalitionStatus)
                    else str(c.status)) == target
            ]

    # ------------------------------------------------------------------
    # Member and Resource Management
    # ------------------------------------------------------------------

    def add_member(
        self,
        coalition_id: str,
        agent_id: str,
        role: AgentRole,
    ) -> Tuple[bool, str]:
        """Add an agent to an existing coalition with a specified role."""
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if coalition.status != CoalitionStatus.ACTIVE:
                return False, "coalition is not active"
            if agent_id not in self._agents:
                return False, f"agent '{agent_id}' not registered"
            if agent_id in coalition.members:
                return False, "agent is already a member"
            if len(coalition.members) >= self._config.max_members_per_coalition:
                return False, "coalition at max capacity"
            profile = self._agents[agent_id]
            if profile.current_coalition_id is not None:
                return False, "agent is already in another coalition"
            actual_role = role if isinstance(role, AgentRole) \
                else AgentRole(role)
            coalition.members[agent_id] = actual_role
            coalition.total_contributions.setdefault(agent_id, 0.0)
            profile.current_coalition_id = coalition_id
            if coalition_id not in profile.past_coalitions:
                profile.past_coalitions.append(coalition_id)
            self._agent_history.setdefault(agent_id, []).append(coalition_id)
            _evict_fifo_list(
                self._agent_history[agent_id], _MAX_HISTORY_PER_AGENT
            )
            self._touch_coalition(coalition_id)
            # Recompute Shapley values with the new member.
            if self._config.enable_shapley_calculation:
                self._compute_shapley_internal(coalition)
            self._emit(
                CoalitionEventKind.MEMBER_JOINED,
                coalition_id=coalition_id,
                agent_id=agent_id,
                payload={"role": actual_role.value},
            )
            return True, "member added"

    def remove_member(
        self,
        coalition_id: str,
        agent_id: str,
        reason: str = "",
    ) -> Tuple[bool, str]:
        """Remove an agent from a coalition."""
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if agent_id not in coalition.members:
                return False, "agent is not a member of this coalition"
            del coalition.members[agent_id]
            coalition.shapley_values.pop(agent_id, None)
            profile = self._agents.get(agent_id)
            if profile and profile.current_coalition_id == coalition_id:
                profile.current_coalition_id = None
            self._emit(
                CoalitionEventKind.MEMBER_LEFT,
                coalition_id=coalition_id,
                agent_id=agent_id,
                payload={"reason": reason or "manual_removal"},
            )
            # If the leader left, promote the first remaining member.
            if coalition.leader_id == agent_id:
                remaining = list(coalition.members.keys())
                if remaining:
                    coalition.leader_id = remaining[0]
                    coalition.members[remaining[0]] = AgentRole.LEADER
                    self._emit(
                        CoalitionEventKind.ROLE_ASSIGNED,
                        coalition_id=coalition_id,
                        agent_id=remaining[0],
                        payload={"role": "leader", "reason": "leader_left"},
                    )
            # If below minimum size, dissolve.
            if len(coalition.members) < self._config.min_coalition_size:
                coalition.status = CoalitionStatus.DISSOLVED
                coalition.dissolved_at_tick = self._tick_count
                self._total_dissolved += 1
                self._emit(
                    CoalitionEventKind.COALITION_DISSOLVED,
                    coalition_id=coalition_id,
                    payload={"reason": "below_minimum_size"},
                )
            else:
                self._touch_coalition(coalition_id)
                if self._config.enable_shapley_calculation:
                    self._compute_shapley_internal(coalition)
            return True, "member removed"

    def assign_role(
        self,
        coalition_id: str,
        agent_id: str,
        role: AgentRole,
    ) -> Tuple[bool, str]:
        """Assign a new role to an agent within a coalition."""
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if agent_id not in coalition.members:
                return False, "agent is not a member of this coalition"
            actual_role = role if isinstance(role, AgentRole) \
                else AgentRole(role)
            old_role = coalition.members[agent_id]
            coalition.members[agent_id] = actual_role
            # If assigning leader, demote the previous leader.
            if actual_role == AgentRole.LEADER \
                    and coalition.leader_id != agent_id:
                old_leader = coalition.leader_id
                if old_leader in coalition.members:
                    coalition.members[old_leader] = AgentRole.CONTRIBUTOR
                coalition.leader_id = agent_id
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.ROLE_ASSIGNED,
                coalition_id=coalition_id,
                agent_id=agent_id,
                payload={
                    "old_role": old_role.value if isinstance(
                        old_role, AgentRole
                    ) else str(old_role),
                    "new_role": actual_role.value,
                },
            )
            return True, "role assigned"

    def pool_resource(
        self,
        coalition_id: str,
        agent_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> Tuple[bool, str, float]:
        """Add resources from an agent into the coalition shared pool.

        Returns (success, message, new_pool_total_for_resource).
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", 0.0
            if agent_id not in coalition.members:
                return False, "agent is not a member of this coalition", 0.0
            if amount <= 0:
                return False, "amount must be positive", 0.0
            rtype = resource_type.value if isinstance(
                resource_type, ResourceType
            ) else str(resource_type)
            current = coalition.shared_resources.get(rtype, 0.0)
            coalition.shared_resources[rtype] = current + amount
            # Also track in agent profile.
            profile = self._agents.get(agent_id)
            if profile:
                profile.resource_contribution[rtype] = \
                    profile.resource_contribution.get(rtype, 0.0) + amount
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.RESOURCE_POOLED,
                coalition_id=coalition_id,
                agent_id=agent_id,
                payload={
                    "resource_type": rtype,
                    "amount": amount,
                    "new_total": coalition.shared_resources[rtype],
                },
            )
            return True, "resource pooled", coalition.shared_resources[rtype]

    def withdraw_resource(
        self,
        coalition_id: str,
        agent_id: str,
        resource_type: ResourceType,
        amount: float,
    ) -> Tuple[bool, str, float]:
        """Withdraw resources from the coalition shared pool.

        Returns (success, message, remaining_pool_total_for_resource).
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", 0.0
            if agent_id not in coalition.members:
                return False, "agent is not a member of this coalition", 0.0
            if amount <= 0:
                return False, "amount must be positive", 0.0
            rtype = resource_type.value if isinstance(
                resource_type, ResourceType
            ) else str(resource_type)
            current = coalition.shared_resources.get(rtype, 0.0)
            if amount > current:
                return (
                    False,
                    f"insufficient {rtype} in pool "
                    f"(have {current}, need {amount})",
                    current,
                )
            coalition.shared_resources[rtype] = current - amount
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.RESOURCE_POOLED,
                coalition_id=coalition_id,
                agent_id=agent_id,
                payload={
                    "resource_type": rtype,
                    "amount": -amount,
                    "new_total": coalition.shared_resources[rtype],
                    "action": "withdraw",
                },
            )
            return True, "resource withdrawn", coalition.shared_resources[rtype]

    # ------------------------------------------------------------------
    # Contribution Tracking
    # ------------------------------------------------------------------

    def record_contribution(
        self,
        agent_id: str,
        coalition_id: str,
        metric: ContributionMetric,
        value: float,
    ) -> Tuple[bool, str]:
        """Record a contribution for an agent in a coalition.

        The contribution value is added to the agent's total in the
        coalition, which feeds into Shapley value computation.
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if agent_id not in coalition.members:
                return False, "agent is not a member of this coalition"
            if len(self._contributions) >= _MAX_CONTRIBUTIONS:
                _evict_fifo_list(self._contributions, _MAX_CONTRIBUTIONS)
            actual_metric = metric if isinstance(
                metric, ContributionMetric
            ) else ContributionMetric(metric)
            record = ContributionRecord(
                agent_id=agent_id,
                coalition_id=coalition_id,
                metric=actual_metric,
                value=value,
                tick=self._tick_count,
            )
            self._contributions.append(record)
            # Update total contributions.
            current_total = coalition.total_contributions.get(agent_id, 0.0)
            coalition.total_contributions[agent_id] = current_total + value
            self._touch_coalition(coalition_id)
            return True, "contribution recorded"

    def get_contributions(
        self, coalition_id: str
    ) -> List[ContributionRecord]:
        """Return all contribution records for a coalition."""
        with _lock:
            return [
                r for r in self._contributions
                if r.coalition_id == coalition_id
            ]

    def get_agent_contributions(
        self,
        coalition_id: str,
        agent_id: str,
    ) -> List[ContributionRecord]:
        """Return contribution records for a specific agent in a coalition."""
        with _lock:
            return [
                r for r in self._contributions
                if r.coalition_id == coalition_id and r.agent_id == agent_id
            ]

    # ------------------------------------------------------------------
    # Shapley Value and Reward Distribution
    # ------------------------------------------------------------------

    def _compute_shapley_internal(
        self, coalition: Coalition
    ) -> Dict[str, float]:
        """Compute Shapley values for all members of a coalition.

        For coalitions with at most ``_SHAPLEY_MAX_MEMBERS`` members, all
        permutations are enumerated for an exact computation. For larger
        coalitions, a sampling-based approximation is used.
        """
        members = list(coalition.members.keys())
        n = len(members)
        if n == 0:
            coalition.shapley_values = {}
            return {}
        shapley: Dict[str, float] = {m: 0.0 for m in members}
        if n <= _SHAPLEY_MAX_MEMBERS:
            # Exact computation via full permutation enumeration.
            perm_count = math.factorial(n)
            for perm in itertools.permutations(members):
                current_set: set = set()
                value_before = self._coalition_value(
                    coalition, frozenset(current_set)
                )
                for agent_id in perm:
                    current_set.add(agent_id)
                    value_after = self._coalition_value(
                        coalition, frozenset(current_set)
                    )
                    marginal = value_after - value_before
                    shapley[agent_id] += marginal
                    value_before = value_after
            for agent_id in members:
                shapley[agent_id] /= perm_count
        else:
            # Sampling-based approximation for large coalitions.
            import random as _random
            sample_size = min(10000, math.factorial(n))
            for _ in range(sample_size):
                perm = list(members)
                _random.shuffle(perm)
                current_set: set = set()
                value_before = self._coalition_value(
                    coalition, frozenset(current_set)
                )
                for agent_id in perm:
                    current_set.add(agent_id)
                    value_after = self._coalition_value(
                        coalition, frozenset(current_set)
                    )
                    marginal = value_after - value_before
                    shapley[agent_id] += marginal
                    value_before = value_after
            for agent_id in members:
                shapley[agent_id] /= sample_size
        # Normalize so values sum to 1.0 for proportional distribution.
        total = sum(shapley.values())
        if total > 0:
            shapley = {k: _safe_div(v, total) for k, v in shapley.items()}
        coalition.shapley_values = shapley
        return shapley

    def compute_shapley_value(
        self, coalition_id: str
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Compute and store Shapley values for all members of a coalition.

        Returns (success, message, shapley_values_dict).
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", {}
            if not coalition.members:
                return False, "coalition has no members", {}
            if not self._config.enable_shapley_calculation:
                return False, "Shapley calculation is disabled", {}
            shapley = self._compute_shapley_internal(coalition)
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.STRATEGY_UPDATED,
                coalition_id=coalition_id,
                payload={
                    "shapley_values": dict(shapley),
                    "method": "permutation_exact"
                    if len(coalition.members) <= _SHAPLEY_MAX_MEMBERS
                    else "permutation_sampled",
                },
            )
            return True, "Shapley values computed", dict(shapley)

    def distribute_rewards(
        self,
        coalition_id: str,
        total_reward: float,
        method: str = "shapley",
    ) -> Tuple[bool, str, Optional[RewardDistribution]]:
        """Distribute rewards among coalition members.

        Supported methods:
          - "shapley": distribute proportionally to Shapley values
          - "equal": distribute equally among all members
          - "proportional": distribute proportionally to total contributions
          - "hybrid": blend 70% Shapley with 30% equal share

        Returns (success, message, distribution).
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", None
            if not coalition.members:
                return False, "coalition has no members", None
            if total_reward <= 0:
                return False, "total_reward must be positive", None
            if len(self._distributions) >= _MAX_DISTRIBUTIONS:
                _evict_fifo_dict(self._distributions, _MAX_DISTRIBUTIONS)
            members = list(coalition.members.keys())
            shares: Dict[str, float] = {}
            if method == "shapley":
                if not coalition.shapley_values:
                    self._compute_shapley_internal(coalition)
                shapley = coalition.shapley_values
                total_shapley = sum(shapley.values())
                if total_shapley > 0:
                    for aid in members:
                        shares[aid] = _safe_div(
                            shapley.get(aid, 0.0), total_shapley
                        ) * total_reward
                else:
                    # Fall back to equal if Shapley is zero.
                    even = total_reward / len(members)
                    shares = {aid: even for aid in members}
            elif method == "equal":
                even = total_reward / len(members)
                shares = {aid: even for aid in members}
            elif method == "proportional":
                total_contrib = sum(
                    coalition.total_contributions.get(aid, 0.0)
                    for aid in members
                )
                if total_contrib > 0:
                    for aid in members:
                        shares[aid] = _safe_div(
                            coalition.total_contributions.get(aid, 0.0),
                            total_contrib,
                        ) * total_reward
                else:
                    even = total_reward / len(members)
                    shares = {aid: even for aid in members}
            elif method == "hybrid":
                if not coalition.shapley_values:
                    self._compute_shapley_internal(coalition)
                shapley = coalition.shapley_values
                total_shapley = sum(shapley.values())
                even_share = total_reward / len(members)
                for aid in members:
                    shapley_share = _safe_div(
                        shapley.get(aid, 0.0), total_shapley
                    ) * total_reward if total_shapley > 0 else even_share
                    shares[aid] = 0.7 * shapley_share + 0.3 * even_share
            else:
                return False, f"unknown method '{method}'", None
            # Round shares to 2 decimal places for clarity.
            shares = {k: round(v, 2) for k, v in shares.items()}
            # Compute fairness score.
            fairness = self._compute_fairness_from_shares(
                shares, coalition.total_contributions
            )
            distribution = RewardDistribution(
                distribution_id=_new_id("rew"),
                coalition_id=coalition_id,
                total_reward=total_reward,
                shares=shares,
                method=method,
                timestamp=_now(),
                fairness_score=round(fairness, 4),
            )
            self._distributions[distribution.distribution_id] = distribution
            self._total_rewards_distributed += total_reward
            self._fairness_scores.append(fairness)
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.REWARD_DISTRIBUTED,
                coalition_id=coalition_id,
                payload={
                    "distribution_id": distribution.distribution_id,
                    "total_reward": total_reward,
                    "method": method,
                    "fairness_score": round(fairness, 4),
                    "shares": dict(shares),
                },
            )
            return True, "rewards distributed", distribution

    def get_reward_distribution(
        self, distribution_id: str
    ) -> Optional[RewardDistribution]:
        """Return the reward distribution for the given id, or None."""
        with _lock:
            return self._distributions.get(distribution_id)

    def list_reward_distributions(
        self, coalition_id: str
    ) -> List[RewardDistribution]:
        """Return all reward distributions for a coalition."""
        with _lock:
            return [
                d for d in self._distributions.values()
                if d.coalition_id == coalition_id
            ]

    def evaluate_fairness(
        self, coalition_id: str
    ) -> Tuple[bool, str, float]:
        """Evaluate the fairness of the most recent reward distribution.

        Compares reward shares against contribution shares and returns a
        fairness score in [0.0, 1.0]. If no distribution exists, fairness
        is computed from Shapley values vs contributions.
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", 0.0
            distributions = self.list_reward_distributions(coalition_id)
            if distributions:
                latest = distributions[-1]
                fairness = self._compute_fairness_from_shares(
                    latest.shares, coalition.total_contributions
                )
                return True, "fairness evaluated", round(fairness, 4)
            # No distribution yet: evaluate based on Shapley vs contributions.
            if not coalition.shapley_values:
                self._compute_shapley_internal(coalition)
            fairness = self._compute_fairness_from_shares(
                coalition.shapley_values, coalition.total_contributions
            )
            return True, "fairness evaluated from Shapley values", round(
                fairness, 4
            )

    # ------------------------------------------------------------------
    # Negotiation Management
    # ------------------------------------------------------------------

    def start_negotiation(
        self,
        coalition_id: str,
        proposer_id: str,
        proposal: CoalitionProposal,
    ) -> Tuple[bool, str, Optional[NegotiationRound]]:
        """Start a new negotiation round within a coalition.

        The proposer issues a proposal and all members except the proposer
        are expected to respond. Returns (success, message, round).
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", None
            if coalition.status not in (
                CoalitionStatus.ACTIVE,
                CoalitionStatus.NEGOTIATING,
            ):
                return False, "coalition is not active for negotiation", None
            if proposer_id not in coalition.members:
                return False, "proposer is not a member of this coalition", None
            # Convert dict input to CoalitionProposal for API compatibility
            if isinstance(proposal, dict):
                strat_raw = proposal.get("strategy", "cooperative")
                strat = strat_raw if isinstance(strat_raw, NegotiationStrategy) \
                    else NegotiationStrategy(strat_raw)
                proposal = CoalitionProposal(
                    proposal_id=proposal.get("proposal_id", ""),
                    proposer_id=proposal.get("proposer_id", proposer_id),
                    target_ids=proposal.get("target_ids", []),
                    task_description=proposal.get("task_description", ""),
                    resource_needs=proposal.get("resource_needs", {}),
                    reward_split=proposal.get("reward_split", {}),
                    strategy=strat,
                    expiry_tick=proposal.get("expiry_tick", 0),
                )
            if len(self._negotiations) >= _MAX_NEGOTIATIONS:
                _evict_fifo_dict(self._negotiations, _MAX_NEGOTIATIONS)
            round_id = _new_id("neg")
            round_obj = NegotiationRound(
                round_id=round_id,
                coalition_id=coalition_id,
                proposer_id=proposer_id,
                proposal=proposal,
                responses={},
                status=NegotiationStatus.ACTIVE,
                timestamp=_now(),
                expiry_tick=self._tick_count
                + self._config.negotiation_timeout_ticks,
            )
            self._negotiations[round_id] = round_obj
            self._total_negotiations += 1
            # Transition coalition to negotiating status.
            if coalition.status == CoalitionStatus.ACTIVE:
                coalition.status = CoalitionStatus.NEGOTIATING
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.NEGOTIATION_STARTED,
                coalition_id=coalition_id,
                agent_id=proposer_id,
                payload={
                    "round_id": round_id,
                    "proposal_id": proposal.proposal_id,
                    "strategy": proposal.strategy.value
                    if isinstance(proposal.strategy, NegotiationStrategy)
                    else str(proposal.strategy),
                },
            )
            return True, "negotiation started", round_obj

    def resolve_negotiation(
        self, round_id: str
    ) -> Tuple[bool, str]:
        """Resolve a negotiation round.

        The round is marked as accepted if a majority of members accepted,
        otherwise rejected. The coalition status returns to ACTIVE.
        """
        with _lock:
            round_obj = self._negotiations.get(round_id)
            if round_obj is None:
                return False, f"negotiation '{round_id}' not found"
            if round_obj.status not in (
                NegotiationStatus.ACTIVE,
                NegotiationStatus.PENDING,
            ):
                return False, f"negotiation is already {round_obj.status.value}"
            coalition = self._coalitions.get(round_obj.coalition_id)
            if coalition is None:
                return False, "coalition no longer exists"
            # Count accept vs reject responses.
            accept_count = sum(
                1 for r in round_obj.responses.values()
                if r == "accept"
            )
            reject_count = sum(
                1 for r in round_obj.responses.values()
                if r == "reject"
            )
            total_members = len(coalition.members)
            threshold = max(1, total_members // 2)
            if accept_count > reject_count and accept_count >= threshold:
                round_obj.status = NegotiationStatus.ACCEPTED
                self._successful_negotiations += 1
                result_msg = "negotiation accepted"
            else:
                round_obj.status = NegotiationStatus.REJECTED
                self._failed_negotiations += 1
                result_msg = "negotiation rejected"
            # Return coalition to active status.
            if coalition.status == CoalitionStatus.NEGOTIATING:
                coalition.status = CoalitionStatus.ACTIVE
            self._touch_coalition(round_obj.coalition_id)
            self._emit(
                CoalitionEventKind.NEGOTIATION_RESOLVED,
                coalition_id=round_obj.coalition_id,
                agent_id=round_obj.proposer_id,
                payload={
                    "round_id": round_id,
                    "status": round_obj.status.value,
                    "accept_count": accept_count,
                    "reject_count": reject_count,
                },
            )
            return True, result_msg

    def get_negotiation(
        self, round_id: str
    ) -> Optional[NegotiationRound]:
        """Return the negotiation round for the given id, or None."""
        with _lock:
            return self._negotiations.get(round_id)

    def list_negotiations(
        self, coalition_id: str
    ) -> List[NegotiationRound]:
        """Return all negotiation rounds for a coalition."""
        with _lock:
            return [
                n for n in self._negotiations.values()
                if n.coalition_id == coalition_id
            ]

    # ------------------------------------------------------------------
    # Recommendation and Assessment
    # ------------------------------------------------------------------

    def recommend_coalition(
        self,
        task_description: str,
        required_skills: List[str],
    ) -> Tuple[bool, str, List[str]]:
        """Recommend agents for a task based on skill match and reliability.

        Returns a list of agent ids sorted by suitability score (best first).
        """
        with _lock:
            if not required_skills:
                return False, "at least one required skill is needed", []
            scored: List[Tuple[str, float]] = []
            required_set = set(s.lower() for s in required_skills)
            for profile in self._agents.values():
                # Skip agents already in a coalition.
                if profile.current_coalition_id is not None:
                    continue
                agent_skills = set(s.lower() for s in profile.skills)
                matched = required_set & agent_skills
                if not matched:
                    continue
                # Score: skill coverage ratio * 0.6 + reliability * 0.4.
                coverage = len(matched) / len(required_set)
                score = coverage * 0.6 + profile.reliability_score * 0.4
                scored.append((profile.agent_id, score))
            scored.sort(key=lambda x: (-x[1], x[0]))
            max_size = self._config.max_coalition_size
            recommended = [aid for aid, _ in scored[:max_size]]
            if not recommended:
                return True, "no matching agents found", []
            return True, f"recommended {len(recommended)} agents", recommended

    def find_best_coalition(
        self,
        task_description: str,
        required_skills: List[str],
        max_size: int = 4,
    ) -> Tuple[bool, str, Optional[CoalitionProposal]]:
        """Find the best coalition composition for a task.

        Recommends agents and auto-creates a proposal. Returns
        (success, message, proposal).
        """
        with _lock:
            if not required_skills:
                return False, "at least one required skill is needed", None
            ok, msg, recommended = self.recommend_coalition(
                task_description, required_skills
            )
            if not ok or not recommended:
                return False, msg or "no suitable agents found", None
            # Limit to max_size (including the leader).
            leader_id = recommended[0]
            targets = recommended[1:max_size]
            if not targets:
                return False, "no target agents available for coalition", None
            # Build resource needs from required skills.
            resource_needs: Dict[str, float] = {}
            for skill in required_skills:
                resource_needs[skill.lower()] = 10.0
            # Determine strategy from task description keywords.
            task_lower = task_description.lower() if task_description else ""
            if any(w in task_lower for w in ("urgent", "fast", "quick")):
                strategy = NegotiationStrategy.COMPETITIVE
            elif any(w in task_lower for w in ("compromise", "balance")):
                strategy = NegotiationStrategy.COMPROMISING
            elif any(w in task_lower for w in ("support", "help", "assist")):
                strategy = NegotiationStrategy.ACCOMMODATING
            else:
                strategy = NegotiationStrategy.COOPERATIVE
            ok2, msg2, proposal = self.propose_coalition(
                leader_id,
                targets,
                task_description,
                resource_needs,
                strategy,
            )
            if not ok2:
                return False, msg2, None
            return True, "best coalition proposal created", proposal

    def assess_coalition_strength(
        self, coalition_id: str
    ) -> Tuple[bool, str, Dict[str, float]]:
        """Assess the aggregate strength of a coalition.

        Returns a dict with metrics: total_resources, average_reliability,
        skill_coverage, member_count, cohesion, and overall_strength.
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", {}
            members = list(coalition.members.keys())
            if not members:
                return False, "coalition has no members", {}
            # Total resources.
            total_resources = sum(coalition.shared_resources.values())
            # Average reliability.
            reliabilities: List[float] = []
            all_skills: set = set()
            for aid in members:
                profile = self._agents.get(aid)
                if profile:
                    reliabilities.append(profile.reliability_score)
                    all_skills.update(s.lower() for s in profile.skills)
            avg_reliability = _safe_div(
                sum(reliabilities), len(reliabilities)
            )
            # Skill coverage: number of distinct skills.
            skill_coverage = float(len(all_skills))
            # Cohesion: based on past coalition overlap among members.
            overlap_count = 0
            pair_count = 0
            for i, aid_a in enumerate(members):
                for aid_b in members[i + 1:]:
                    pair_count += 1
                    history_a = set(self._agent_history.get(aid_a, []))
                    history_b = set(self._agent_history.get(aid_b, []))
                    if history_a & history_b:
                        overlap_count += 1
            cohesion = _safe_div(overlap_count, pair_count) if pair_count else 0.0
            # Overall strength: weighted combination.
            member_count = float(len(members))
            overall = (
                0.25 * _clamp(total_resources / 100.0, 0.0, 1.0)
                + 0.30 * avg_reliability
                + 0.15 * _clamp(skill_coverage / 10.0, 0.0, 1.0)
                + 0.15 * _clamp(member_count / float(
                    self._config.max_members_per_coalition
                ), 0.0, 1.0)
                + 0.15 * cohesion
            )
            return True, "strength assessed", {
                "total_resources": round(total_resources, 2),
                "average_reliability": round(avg_reliability, 4),
                "skill_coverage": skill_coverage,
                "member_count": member_count,
                "cohesion": round(cohesion, 4),
                "overall_strength": round(overall, 4),
            }

    def check_coalition_health(
        self, coalition_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Check the health of a coalition.

        Returns a dict with health indicators: status, member_count,
        resource_levels, contribution_balance, fairness_score,
        activity_age, and overall_health.
        """
        with _lock:
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found", {}
            members = list(coalition.members.keys())
            member_count = len(members)
            # Resource levels.
            resource_levels = dict(coalition.shared_resources)
            total_resources = sum(resource_levels.values())
            # Contribution balance: Gini of total contributions.
            contrib_values = list(coalition.total_contributions.values())
            contribution_gini = _gini_coefficient(contrib_values)
            contribution_balance = round(1.0 - contribution_gini, 4)
            # Fairness score.
            _, _, fairness = self.evaluate_fairness(coalition_id)
            # Activity age: ticks since last activity.
            activity_age = self._tick_count - coalition.last_activity_tick
            # Overall health.
            health_factors: List[float] = []
            # Status health.
            if coalition.status == CoalitionStatus.ACTIVE:
                health_factors.append(1.0)
            elif coalition.status == CoalitionStatus.NEGOTIATING:
                health_factors.append(0.7)
            elif coalition.status == CoalitionStatus.FORMING:
                health_factors.append(0.5)
            elif coalition.status == CoalitionStatus.DISSOLVING:
                health_factors.append(0.2)
            else:
                health_factors.append(0.0)
            # Member count health.
            if member_count >= self._config.min_coalition_size:
                health_factors.append(1.0)
            else:
                health_factors.append(0.3)
            # Resource health.
            health_factors.append(_clamp(total_resources / 100.0, 0.0, 1.0))
            # Contribution balance health.
            health_factors.append(contribution_balance)
            # Fairness health.
            health_factors.append(fairness)
            # Activity health: penalize long inactivity.
            if activity_age < _INACTIVITY_DISSOLVE_TICKS // 2:
                health_factors.append(1.0)
            elif activity_age < _INACTIVITY_DISSOLVE_TICKS:
                health_factors.append(0.5)
            else:
                health_factors.append(0.1)
            overall_health = _safe_div(
                sum(health_factors), len(health_factors)
            )
            return True, "health checked", {
                "status": coalition.status.value
                if isinstance(coalition.status, CoalitionStatus)
                else str(coalition.status),
                "member_count": member_count,
                "resource_levels": resource_levels,
                "total_resources": round(total_resources, 2),
                "contribution_balance": contribution_balance,
                "fairness_score": round(fairness, 4),
                "activity_age": activity_age,
                "overall_health": round(overall_health, 4),
            }

    def reconfigure_coalition(
        self, coalition_id: str
    ) -> Tuple[bool, str]:
        """Dynamically reconfigure a coalition.

        This evaluates the coalition's current composition, removes
        underperforming members, and invites suitable replacements.
        Shapley values and fairness are recomputed afterwards.
        """
        with _lock:
            if not self._config.enable_dynamic_reconfiguration:
                return False, "dynamic reconfiguration is disabled"
            coalition = self._coalitions.get(coalition_id)
            if coalition is None:
                return False, f"coalition '{coalition_id}' not found"
            if coalition.status != CoalitionStatus.ACTIVE:
                return False, "coalition is not active"
            members = list(coalition.members.keys())
            if len(members) <= self._config.min_coalition_size:
                return True, "coalition at minimum size, no reconfiguration"
            # Identify underperforming members.
            # Underperforming: contribution below 25% of the average.
            contribs = coalition.total_contributions
            avg_contrib = _safe_div(
                sum(contribs.values()), len(contribs)
            ) if contribs else 0.0
            threshold = avg_contrib * 0.25
            removed: List[str] = []
            for aid in members:
                if aid == coalition.leader_id:
                    continue
                if contribs.get(aid, 0.0) < threshold and avg_contrib > 0:
                    removed.append(aid)
            for aid in removed:
                del coalition.members[aid]
                coalition.total_contributions.pop(aid, None)
                coalition.shapley_values.pop(aid, None)
                profile = self._agents.get(aid)
                if profile and profile.current_coalition_id == coalition_id:
                    profile.current_coalition_id = None
                self._emit(
                    CoalitionEventKind.MEMBER_LEFT,
                    coalition_id=coalition_id,
                    agent_id=aid,
                    payload={"reason": "reconfiguration_underperformance"},
                )
            # Recompute Shapley values.
            if self._config.enable_shapley_calculation:
                self._compute_shapley_internal(coalition)
            self._touch_coalition(coalition_id)
            self._emit(
                CoalitionEventKind.STRATEGY_UPDATED,
                coalition_id=coalition_id,
                payload={
                    "action": "reconfiguration",
                    "removed_members": removed,
                    "remaining_members": list(coalition.members.keys()),
                },
            )
            return True, f"reconfiguration complete, removed {len(removed)}"

    # ------------------------------------------------------------------
    # History, Stats, Snapshot, Config
    # ------------------------------------------------------------------

    def get_coalition_history(
        self, agent_id: str
    ) -> List[Coalition]:
        """Return all coalitions an agent has participated in."""
        with _lock:
            history_ids = self._agent_history.get(agent_id, [])
            if not history_ids:
                profile = self._agents.get(agent_id)
                if profile:
                    history_ids = profile.past_coalitions
            coalitions: List[Coalition] = []
            seen: set = set()
            for cid in history_ids:
                if cid in seen:
                    continue
                seen.add(cid)
                coalition = self._coalitions.get(cid)
                if coalition is not None:
                    coalitions.append(coalition)
            return coalitions

    def get_stats(self) -> CoalitionStats:
        """Return aggregate statistics about the negotiator engine."""
        with _lock:
            active = sum(
                1 for c in self._coalitions.values()
                if c.status == CoalitionStatus.ACTIVE
            )
            avg_fairness = _safe_div(
                sum(self._fairness_scores), len(self._fairness_scores)
            ) if self._fairness_scores else 0.0
            avg_formation = _safe_div(
                sum(self._formation_times), len(self._formation_times)
            ) if self._formation_times else 0.0
            return CoalitionStats(
                total_coalitions_formed=self._total_coalitions_formed,
                total_dissolved=self._total_dissolved,
                active_coalitions=active,
                total_negotiations=self._total_negotiations,
                successful_negotiations=self._successful_negotiations,
                failed_negotiations=self._failed_negotiations,
                total_rewards_distributed=round(
                    self._total_rewards_distributed, 2
                ),
                average_fairness_score=round(avg_fairness, 4),
                average_formation_time=round(avg_formation, 4),
            )

    def get_snapshot(self) -> CoalitionSnapshot:
        """Return a point-in-time snapshot of the negotiator state."""
        with _lock:
            active = sum(
                1 for c in self._coalitions.values()
                if c.status == CoalitionStatus.ACTIVE
            )
            total_members = sum(
                len(c.members)
                for c in self._coalitions.values()
                if c.status == CoalitionStatus.ACTIVE
            )
            total_negotiations = sum(
                1 for n in self._negotiations.values()
                if n.status in (
                    NegotiationStatus.ACTIVE,
                    NegotiationStatus.PENDING,
                )
            )
            total_rewards = self._total_rewards_distributed
            return CoalitionSnapshot(
                tick_count=self._tick_count,
                active_coalitions=active,
                total_members=total_members,
                total_negotiations=total_negotiations,
                total_rewards=round(total_rewards, 2),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary summarizing the engine state."""
        with _lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "total_agents": len(self._agents),
                "total_proposals": len(self._proposals),
                "total_coalitions": len(self._coalitions),
                "active_coalitions": stats.active_coalitions,
                "total_negotiations": len(self._negotiations),
                "total_contributions": len(self._contributions),
                "total_distributions": len(self._distributions),
                "total_events": len(self._events),
                "stats": stats.to_dict(),
            }

    def get_config(self) -> CoalitionConfig:
        """Return the current configuration."""
        with _lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, CoalitionConfig]:
        """Update configuration fields. Only known fields are applied."""
        with _lock:
            known_fields = {
                "max_coalitions",
                "max_members_per_coalition",
                "negotiation_timeout_ticks",
                "enable_dynamic_reconfiguration",
                "enable_shapley_calculation",
                "fairness_threshold",
                "min_coalition_size",
                "max_coalition_size",
                "reward_pool_base",
            }
            applied: List[str] = []
            ignored: List[str] = []
            for key, value in kwargs.items():
                if key in known_fields:
                    setattr(self._config, key, value)
                    applied.append(key)
                else:
                    ignored.append(key)
            self._emit(
                CoalitionEventKind.STRATEGY_UPDATED,
                payload={
                    "action": "config_updated",
                    "applied": applied,
                    "ignored": ignored,
                },
            )
            msg = f"updated {len(applied)} field(s)"
            if ignored:
                msg += f", ignored {len(ignored)} unknown field(s)"
            return True, msg, self._config

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: Optional[CoalitionEventKind] = None,
        limit: int = 100,
    ) -> List[CoalitionEvent]:
        """Return events, optionally filtered by kind, up to a limit."""
        with _lock:
            events = list(self._events)
            if kind is not None:
                target = kind.value if isinstance(
                    kind, CoalitionEventKind
                ) else str(kind)
                events = [
                    e for e in events
                    if (e.kind.value if isinstance(e.kind, CoalitionEventKind)
                        else str(e.kind)) == target
                ]
            if limit and limit > 0:
                events = events[-limit:]
            return events

    # ------------------------------------------------------------------
    # Tick and Lifecycle
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the negotiator by one tick.

        Performs the following automated actions:
          - Expires stale proposals past their expiry tick.
          - Auto-dissolves coalitions that have been inactive for too long.
          - Expires timed-out negotiation rounds.
          - Refreshes statistics.

        Returns a summary dictionary.
        """
        with _lock:
            self._tick_count += 1
            expired_proposals = 0
            dissolved_coalitions = 0
            expired_negotiations = 0
            # Expire stale proposals.
            for proposal in self._proposals.values():
                if proposal.status in (
                    NegotiationStatus.PENDING,
                    NegotiationStatus.COUNTERED,
                    NegotiationStatus.ACTIVE,
                ) and self._tick_count > proposal.expiry_tick:
                    proposal.status = NegotiationStatus.EXPIRED
                    expired_proposals += 1
            # Auto-dissolve inactive coalitions.
            for coalition in self._coalitions.values():
                if coalition.status != CoalitionStatus.ACTIVE:
                    continue
                age = self._tick_count - coalition.last_activity_tick
                if age >= _INACTIVITY_DISSOLVE_TICKS:
                    coalition.status = CoalitionStatus.DISSOLVED
                    coalition.dissolved_at_tick = self._tick_count
                    for aid in list(coalition.members.keys()):
                        profile = self._agents.get(aid)
                        if profile and profile.current_coalition_id == \
                                coalition.coalition_id:
                            profile.current_coalition_id = None
                    self._total_dissolved += 1
                    dissolved_coalitions += 1
                    self._emit(
                        CoalitionEventKind.COALITION_DISSOLVED,
                        coalition_id=coalition.coalition_id,
                        payload={"reason": "inactivity_timeout"},
                    )
            # Expire timed-out negotiations.
            for round_obj in self._negotiations.values():
                if round_obj.status in (
                    NegotiationStatus.ACTIVE,
                    NegotiationStatus.PENDING,
                ) and self._tick_count > round_obj.expiry_tick:
                    round_obj.status = NegotiationStatus.EXPIRED
                    self._failed_negotiations += 1
                    expired_negotiations += 1
                    coalition = self._coalitions.get(round_obj.coalition_id)
                    if coalition and coalition.status == \
                            CoalitionStatus.NEGOTIATING:
                        coalition.status = CoalitionStatus.ACTIVE
            self._emit(
                CoalitionEventKind.STRATEGY_UPDATED,
                payload={
                    "action": "tick",
                    "tick_count": self._tick_count,
                    "expired_proposals": expired_proposals,
                    "dissolved_coalitions": dissolved_coalitions,
                    "expired_negotiations": expired_negotiations,
                },
            )
            stats = self.get_stats()
            return {
                "tick": self._tick_count,
                "dt": dt,
                "expired_proposals": expired_proposals,
                "dissolved_coalitions": dissolved_coalitions,
                "expired_negotiations": expired_negotiations,
                "active_coalitions": stats.active_coalitions,
                "total_agents": len(self._agents),
                "total_events": len(self._events),
            }

    def get_agent_coalition(
        self, agent_id: str
    ) -> Optional[Coalition]:
        """Return the coalition an agent currently belongs to, or None."""
        with _lock:
            profile = self._agents.get(agent_id)
            if profile is None or profile.current_coalition_id is None:
                return None
            return self._coalitions.get(profile.current_coalition_id)

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the negotiator with a canonical set of seed data."""
        with self._init_lock:
            if self._seeded:
                return

            # ----------------------------------------------------------
            # Agent Profiles (8)
            # ----------------------------------------------------------
            self._seed_agents()

            # ----------------------------------------------------------
            # Coalition Proposals (3)
            # ----------------------------------------------------------
            self._seed_proposals()

            # ----------------------------------------------------------
            # Active Coalitions (2)
            # ----------------------------------------------------------
            self._seed_coalitions()

            # ----------------------------------------------------------
            # Contribution Records (5)
            # ----------------------------------------------------------
            self._seed_contributions()

            # ----------------------------------------------------------
            # Reward Distributions (2)
            # ----------------------------------------------------------
            self._seed_distributions()

            # ----------------------------------------------------------
            # Negotiation Rounds (3)
            # ----------------------------------------------------------
            self._seed_negotiations()

            self._emit(
                CoalitionEventKind.STRATEGY_UPDATED,
                payload={
                    "action": "seed_data_loaded",
                    "agents": len(self._agents),
                    "proposals": len(self._proposals),
                    "coalitions": len(self._coalitions),
                    "contributions": len(self._contributions),
                    "distributions": len(self._distributions),
                    "negotiations": len(self._negotiations),
                },
            )
            self._initialized = True
            self._seeded = True

    def _seed_agents(self) -> None:
        """Seed eight agent profiles with diverse skills and roles."""
        agent_specs = [
            (
                "agent_aria",
                "Aria",
                AgentRole.LEADER,
                ["strategy", "planning", "tactics", "logistics"],
                {"compute": 40.0, "knowledge": 60.0, "influence": 80.0},
                0.95,
            ),
            (
                "agent_brun",
                "Brun",
                AgentRole.SPECIALIST,
                ["combat", "weapons", "defense", "survival"],
                {"compute": 70.0, "skill": 90.0, "asset": 50.0},
                0.88,
            ),
            (
                "agent_cael",
                "Cael",
                AgentRole.NEGOTIATOR,
                ["diplomacy", "trade", "persuasion", "languages"],
                {"knowledge": 75.0, "influence": 85.0, "time": 40.0},
                0.91,
            ),
            (
                "agent_dara",
                "Dara",
                AgentRole.CONTRIBUTOR,
                ["crafting", "gathering", "alchemy", "exploration"],
                {"compute": 55.0, "skill": 70.0, "asset": 60.0},
                0.84,
            ),
            (
                "agent_elia",
                "Elia",
                AgentRole.SUPPORTER,
                ["healing", "protection", "buffs", "logistics"],
                {"knowledge": 65.0, "time": 80.0, "influence": 45.0},
                0.90,
            ),
            (
                "agent_fenn",
                "Fenn",
                AgentRole.SPECIALIST,
                ["stealth", "scouting", "traps", "lockpicking"],
                {"compute": 50.0, "skill": 85.0, "time": 55.0},
                0.82,
            ),
            (
                "agent_gret",
                "Gret",
                AgentRole.CONTRIBUTOR,
                ["engineering", "building", "repair", "analysis"],
                {"compute": 80.0, "knowledge": 60.0, "asset": 70.0},
                0.87,
            ),
            (
                "agent_halo",
                "Halo",
                AgentRole.SUPPORTER,
                ["music", "morale", "communication", "coordination"],
                {"influence": 70.0, "time": 60.0, "knowledge": 50.0},
                0.86,
            ),
        ]
        for agent_id, name, role, skills, resources, reliability in \
                agent_specs:
            profile = AgentProfile(
                agent_id=agent_id,
                name=name,
                role=role,
                skills=list(skills),
                resource_contribution=dict(resources),
                reliability_score=reliability,
                past_coalitions=[],
                current_coalition_id=None,
            )
            self._agents[agent_id] = profile
            self._agent_history.setdefault(agent_id, [])

    def _seed_proposals(self) -> None:
        """Seed three coalition proposals with different strategies."""
        # Proposal 1: Cooperative dragon-slaying coalition.
        proposal_1 = CoalitionProposal(
            proposal_id="prp_dragon_001",
            proposer_id="agent_aria",
            target_ids=["agent_brun", "agent_dara", "agent_elia"],
            task_description="Slay the red dragon terrorizing the "
                             "northern villages",
            resource_needs={"compute": 60.0, "skill": 80.0, "knowledge": 40.0},
            reward_split={
                "agent_aria": 0.30,
                "agent_brun": 0.30,
                "agent_dara": 0.20,
                "agent_elia": 0.20,
            },
            strategy=NegotiationStrategy.COOPERATIVE,
            expiry_tick=200,
            status=NegotiationStatus.ACCEPTED,
            responses={
                "agent_brun": "accept",
                "agent_dara": "accept",
                "agent_elia": "accept",
            },
            created_at=_now(),
            formation_pattern=FormationPattern.TOP_DOWN,
        )
        self._proposals[proposal_1.proposal_id] = proposal_1

        # Proposal 2: Competitive trade route monopoly.
        proposal_2 = CoalitionProposal(
            proposal_id="prp_trade_002",
            proposer_id="agent_cael",
            target_ids=["agent_gret", "agent_halo"],
            task_description="Establish a dominant trade route across "
                             "the eastern corridor",
            resource_needs={"knowledge": 70.0, "influence": 60.0,
                            "asset": 50.0},
            reward_split={
                "agent_cael": 0.40,
                "agent_gret": 0.35,
                "agent_halo": 0.25,
            },
            strategy=NegotiationStrategy.COMPETITIVE,
            expiry_tick=250,
            status=NegotiationStatus.ACCEPTED,
            responses={
                "agent_gret": "accept",
                "agent_halo": "accept",
            },
            created_at=_now(),
            formation_pattern=FormationPattern.AUCTION_BASED,
        )
        self._proposals[proposal_2.proposal_id] = proposal_2

        # Proposal 3: Compromising scouting expedition.
        proposal_3 = CoalitionProposal(
            proposal_id="prp_scout_003",
            proposer_id="agent_fenn",
            target_ids=["agent_dara", "agent_halo"],
            task_description="Scout the abandoned ruins for hidden "
                             "passages and treasure",
            resource_needs={"skill": 50.0, "time": 40.0, "knowledge": 30.0},
            reward_split={
                "agent_fenn": 0.35,
                "agent_dara": 0.35,
                "agent_halo": 0.30,
            },
            strategy=NegotiationStrategy.COMPROMISING,
            expiry_tick=300,
            status=NegotiationStatus.PENDING,
            responses={"agent_dara": "accept"},
            created_at=_now(),
            formation_pattern=FormationPattern.BOTTOM_UP,
        )
        self._proposals[proposal_3.proposal_id] = proposal_3

    def _seed_coalitions(self) -> None:
        """Seed two active coalitions with members and resources."""
        # Coalition 1: Dragon Slaying Squad
        coalition_1 = Coalition(
            coalition_id="col_dragon_001",
            name="Dragon Slaying Squad",
            leader_id="agent_aria",
            members={
                "agent_aria": AgentRole.LEADER,
                "agent_brun": AgentRole.SPECIALIST,
                "agent_dara": AgentRole.CONTRIBUTOR,
                "agent_elia": AgentRole.SUPPORTER,
            },
            formation_pattern=FormationPattern.TOP_DOWN,
            shared_resources={
                "compute": 100.0,
                "skill": 160.0,
                "knowledge": 100.0,
                "asset": 110.0,
                "time": 80.0,
                "influence": 125.0,
            },
            task_objective="Slay the red dragon terrorizing the "
                           "northern villages",
            status=CoalitionStatus.ACTIVE,
            formed_at_tick=10,
            shapley_values={},
            total_contributions={
                "agent_aria": 120.0,
                "agent_brun": 150.0,
                "agent_dara": 80.0,
                "agent_elia": 90.0,
            },
            last_activity_tick=50,
            dissolved_at_tick=None,
        )
        self._coalitions[coalition_1.coalition_id] = coalition_1
        self._total_coalitions_formed += 1
        # Update agent profiles.
        for aid in coalition_1.members:
            profile = self._agents.get(aid)
            if profile:
                profile.current_coalition_id = coalition_1.coalition_id
                if coalition_1.coalition_id not in profile.past_coalitions:
                    profile.past_coalitions.append(coalition_1.coalition_id)
                self._agent_history.setdefault(aid, []).append(
                    coalition_1.coalition_id
                )
        # Compute initial Shapley values.
        self._compute_shapley_internal(coalition_1)

        # Coalition 2: Trade Route Consortium
        coalition_2 = Coalition(
            coalition_id="col_trade_002",
            name="Trade Route Consortium",
            leader_id="agent_cael",
            members={
                "agent_cael": AgentRole.LEADER,
                "agent_gret": AgentRole.CONTRIBUTOR,
                "agent_halo": AgentRole.SUPPORTER,
            },
            formation_pattern=FormationPattern.AUCTION_BASED,
            shared_resources={
                "compute": 80.0,
                "knowledge": 135.0,
                "influence": 155.0,
                "asset": 70.0,
                "time": 60.0,
            },
            task_objective="Establish a dominant trade route across "
                           "the eastern corridor",
            status=CoalitionStatus.ACTIVE,
            formed_at_tick=20,
            shapley_values={},
            total_contributions={
                "agent_cael": 140.0,
                "agent_gret": 110.0,
                "agent_halo": 85.0,
            },
            last_activity_tick=45,
            dissolved_at_tick=None,
        )
        self._coalitions[coalition_2.coalition_id] = coalition_2
        self._total_coalitions_formed += 1
        for aid in coalition_2.members:
            profile = self._agents.get(aid)
            if profile:
                profile.current_coalition_id = coalition_2.coalition_id
                if coalition_2.coalition_id not in profile.past_coalitions:
                    profile.past_coalitions.append(coalition_2.coalition_id)
                self._agent_history.setdefault(aid, []).append(
                    coalition_2.coalition_id
                )
        self._compute_shapley_internal(coalition_2)

    def _seed_contributions(self) -> None:
        """Seed five contribution records across the two coalitions."""
        contrib_specs = [
            ("agent_brun", "col_dragon_001",
             ContributionMetric.TASK_COMPLETION, 55.0, 25),
            ("agent_aria", "col_dragon_001",
             ContributionMetric.INNOVATION, 45.0, 22),
            ("agent_elia", "col_dragon_001",
             ContributionMetric.COLLABORATION, 40.0, 28),
            ("agent_cael", "col_trade_002",
             ContributionMetric.QUALITY, 60.0, 30),
            ("agent_gret", "col_trade_002",
             ContributionMetric.SPEED, 50.0, 32),
        ]
        for agent_id, coalition_id, metric, value, tick in contrib_specs:
            record = ContributionRecord(
                agent_id=agent_id,
                coalition_id=coalition_id,
                metric=metric,
                value=value,
                tick=tick,
            )
            self._contributions.append(record)

    def _seed_distributions(self) -> None:
        """Seed two reward distributions for the two coalitions."""
        # Distribution 1: Dragon Slaying Squad - shapley method.
        coalition_1 = self._coalitions.get("col_dragon_001")
        if coalition_1 is not None:
            shapley = coalition_1.shapley_values
            total_shapley = sum(shapley.values()) if shapley else 0.0
            total_reward_1 = 1500.0
            shares_1: Dict[str, float] = {}
            if total_shapley > 0:
                for aid in coalition_1.members:
                    shares_1[aid] = round(
                        _safe_div(
                            shapley.get(aid, 0.0), total_shapley
                        ) * total_reward_1, 2
                    )
            else:
                even = total_reward_1 / len(coalition_1.members)
                shares_1 = {
                    aid: round(even, 2) for aid in coalition_1.members
                }
            fairness_1 = self._compute_fairness_from_shares(
                shares_1, coalition_1.total_contributions
            )
            dist_1 = RewardDistribution(
                distribution_id="rew_dragon_001",
                coalition_id="col_dragon_001",
                total_reward=total_reward_1,
                shares=shares_1,
                method="shapley",
                timestamp=_now(),
                fairness_score=round(fairness_1, 4),
            )
            self._distributions[dist_1.distribution_id] = dist_1
            self._total_rewards_distributed += total_reward_1
            self._fairness_scores.append(fairness_1)

        # Distribution 2: Trade Route Consortium - equal method.
        coalition_2 = self._coalitions.get("col_trade_002")
        if coalition_2 is not None:
            total_reward_2 = 900.0
            even_2 = total_reward_2 / len(coalition_2.members)
            shares_2 = {
                aid: round(even_2, 2) for aid in coalition_2.members
            }
            fairness_2 = self._compute_fairness_from_shares(
                shares_2, coalition_2.total_contributions
            )
            dist_2 = RewardDistribution(
                distribution_id="rew_trade_002",
                coalition_id="col_trade_002",
                total_reward=total_reward_2,
                shares=shares_2,
                method="equal",
                timestamp=_now(),
                fairness_score=round(fairness_2, 4),
            )
            self._distributions[dist_2.distribution_id] = dist_2
            self._total_rewards_distributed += total_reward_2
            self._fairness_scores.append(fairness_2)

    def _seed_negotiations(self) -> None:
        """Seed three negotiation rounds across the two coalitions."""
        # Negotiation 1: Resource rebalancing in dragon squad.
        proposal_1 = CoalitionProposal(
            proposal_id="prp_neg_001",
            proposer_id="agent_brun",
            target_ids=["agent_aria", "agent_dara"],
            task_description="Rebalance compute resources after "
                             "equipment losses",
            resource_needs={"compute": 30.0, "asset": 20.0},
            reward_split={
                "agent_brun": 0.35,
                "agent_aria": 0.35,
                "agent_dara": 0.30,
            },
            strategy=NegotiationStrategy.COOPERATIVE,
            expiry_tick=150,
            status=NegotiationStatus.ACCEPTED,
            responses={"agent_aria": "accept", "agent_dara": "accept"},
            created_at=_now(),
            formation_pattern=FormationPattern.TOP_DOWN,
        )
        round_1 = NegotiationRound(
            round_id="neg_001",
            coalition_id="col_dragon_001",
            proposer_id="agent_brun",
            proposal=proposal_1,
            responses={"agent_aria": "accept", "agent_dara": "accept"},
            status=NegotiationStatus.ACCEPTED,
            timestamp=_now(),
            expiry_tick=150,
        )
        self._negotiations[round_1.round_id] = round_1
        self._total_negotiations += 1
        self._successful_negotiations += 1

        # Negotiation 2: Reward split dispute in trade consortium.
        proposal_2 = CoalitionProposal(
            proposal_id="prp_neg_002",
            proposer_id="agent_gret",
            target_ids=["agent_cael", "agent_halo"],
            task_description="Adjust reward split to reflect "
                             "engineering contributions",
            resource_needs={},
            reward_split={
                "agent_cael": 0.30,
                "agent_gret": 0.45,
                "agent_halo": 0.25,
            },
            strategy=NegotiationStrategy.COMPETITIVE,
            expiry_tick=180,
            status=NegotiationStatus.ACTIVE,
            responses={"agent_cael": "counter", "agent_halo": "accept"},
            created_at=_now(),
            formation_pattern=FormationPattern.CONSENSUS,
        )
        round_2 = NegotiationRound(
            round_id="neg_002",
            coalition_id="col_trade_002",
            proposer_id="agent_gret",
            proposal=proposal_2,
            responses={"agent_cael": "counter", "agent_halo": "accept"},
            status=NegotiationStatus.ACTIVE,
            timestamp=_now(),
            expiry_tick=180,
        )
        self._negotiations[round_2.round_id] = round_2
        self._total_negotiations += 1

        # Negotiation 3: Scouting coalition formation.
        proposal_3 = CoalitionProposal(
            proposal_id="prp_neg_003",
            proposer_id="agent_fenn",
            target_ids=["agent_dara", "agent_halo"],
            task_description="Negotiate roles for the ruins scouting "
                             "expedition",
            resource_needs={"skill": 40.0, "time": 30.0},
            reward_split={
                "agent_fenn": 0.40,
                "agent_dara": 0.30,
                "agent_halo": 0.30,
            },
            strategy=NegotiationStrategy.COMPROMISING,
            expiry_tick=200,
            status=NegotiationStatus.PENDING,
            responses={"agent_dara": "accept"},
            created_at=_now(),
            formation_pattern=FormationPattern.BOTTOM_UP,
        )
        round_3 = NegotiationRound(
            round_id="neg_003",
            coalition_id="col_dragon_001",
            proposer_id="agent_fenn",
            proposal=proposal_3,
            responses={"agent_dara": "accept"},
            status=NegotiationStatus.PENDING,
            timestamp=_now(),
            expiry_tick=200,
        )
        self._negotiations[round_3.round_id] = round_3
        self._total_negotiations += 1


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_coalition_negotiator() -> AgentCoalitionNegotiator:
    """Return the singleton AgentCoalitionNegotiator instance.

    This is the primary entry point for obtaining the negotiator. It
    auto-initializes the singleton on first call.
    """
    return AgentCoalitionNegotiator.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "CoalitionStatus",
    "NegotiationStatus",
    "AgentRole",
    "ResourceType",
    "ContributionMetric",
    "CoalitionEventKind",
    "NegotiationStrategy",
    "FormationPattern",
    # Data classes
    "AgentProfile",
    "CoalitionProposal",
    "NegotiationRound",
    "Coalition",
    "ContributionRecord",
    "RewardDistribution",
    "CoalitionStats",
    "CoalitionConfig",
    "CoalitionSnapshot",
    "CoalitionEvent",
    # Main system class
    "AgentCoalitionNegotiator",
    # Factory
    "get_coalition_negotiator",
]
