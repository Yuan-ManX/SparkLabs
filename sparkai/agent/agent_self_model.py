"""
SparkLabs Agent - Unified Self-Model Engine

This module implements a unified self-model engine for AI agents operating
inside the SparkLabs AI-native game engine. The self-model integrates an
agent's capabilities, limits, current state, and self-knowledge into a
single coherent model that other subsystems can reason about.

The self-model is distinct from (and complementary to) other SparkLabs
agent subsystems:

  * Metacognition tracks confidence and uncertainty about external claims.
  * Capability Registry tracks what capabilities are available globally.
  * Self-Model (this module) unifies per-agent capabilities, limits, state,
    goals, and beliefs into a single coherent self-description.

Core concepts:

  1. Capabilities
       Each registered capability has a proficiency (how well the agent can
       perform it) and a confidence (how certain the agent is about that
       proficiency). Both are in [0.0, 1.0]. Usage updates both fields.

  2. Limits
       Limits describe hard or soft constraints on the agent (stamina,
       attention, mana, authority, ethics, etc.). Each limit has a numeric
       threshold, a current load, and a "breached" flag derived from those
       values.

  3. State
       State captures the agent's current condition along several dimensions
       (physical, mental, emotional, social, temporal) with a trend marker
       so callers can reason about whether the agent is improving, stable,
       or declining.

  4. Goals
       Goals capture the agent's intentions with a priority and progress
       (0-1). Goals transition through active, achieved, and abandoned.

  5. Beliefs
       Beliefs are propositions the agent holds, with a confidence score
       and a provenance source. Beliefs can be updated over time as new
       evidence arrives.

  6. Revisions
       Revisions record when the agent's self-model was significantly
       updated, with a trigger description, a human-readable reason, and
       a list of change dicts.

Architecture:
  SelfModelEngine (Singleton, double-checked locking with threading.RLock)
    |-- CapabilityEntry        -- a registered agent capability
    |-- LimitEntry             -- a registered agent limit
    |-- StateEntry             -- a state dimension reading
    |-- GoalEntry              -- an active/achieved/abandoned goal
    |-- BeliefEntry            -- a proposition the agent holds
    |-- SelfModelRevision      -- a recorded self-model revision
    |-- SelfModel              -- the unified per-agent self-model
    |-- SelfModelStats         -- aggregate engine statistics
    |-- SelfModelSnapshot      -- complete engine state snapshot
    |-- SelfModelEvent         -- observable engine lifecycle event

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
from typing import Any, Dict, List, Optional, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_AGENTS: int = 500
_MAX_CAPABILITIES_PER_AGENT: int = 200
_MAX_LIMITS_PER_AGENT: int = 200
_MAX_STATES_PER_AGENT: int = 50
_MAX_GOALS_PER_AGENT: int = 200
_MAX_BELIEFS_PER_AGENT: int = 500
_MAX_REVISIONS_PER_AGENT: int = 200
_MAX_EVENTS: int = 2000


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
    return float(value)


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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ModelComponent(Enum):
    """The major components that make up a unified self-model."""
    CAPABILITIES = "capabilities"
    LIMITS = "limits"
    STATE = "state"
    GOALS = "goals"
    RESOURCES = "resources"
    BELIEFS = "beliefs"
    HISTORY = "history"


class LimitType(Enum):
    """The category of a limit entry."""
    COMPUTATIONAL = "computational"
    MEMORY = "memory"
    TEMPORAL = "temporal"
    AUTHORITY = "authority"
    ETHICAL = "ethical"
    PHYSICAL = "physical"


class StateDimension(Enum):
    """The dimension of an agent's state being tracked."""
    PHYSICAL = "physical"
    MENTAL = "mental"
    EMOTIONAL = "emotional"
    SOCIAL = "social"
    TEMPORAL = "temporal"


class StateTrend(Enum):
    """Direction of change for a state dimension reading."""
    RISING = "rising"
    STABLE = "stable"
    FALLING = "falling"


class BeliefSource(Enum):
    """The origin of a belief entry."""
    INFERENCE = "inference"
    COMMUNICATION = "communication"
    OBSERVATION = "observation"
    INSTRUCTION = "instruction"


class GoalStatus(Enum):
    """The lifecycle status of a goal."""
    ACTIVE = "active"
    ACHIEVED = "achieved"
    ABANDONED = "abandoned"


class SelfModelEventKind(Enum):
    """Observable lifecycle events emitted by the self-model engine."""
    AGENT_REGISTERED = "agent_registered"
    CAPABILITY_ADDED = "capability_added"
    LIMIT_REGISTERED = "limit_registered"
    STATE_UPDATED = "state_updated"
    GOAL_RECORDED = "goal_recorded"
    BELIEF_FORMED = "belief_formed"
    MODEL_INSPECTED = "model_inspected"
    REVISION_APPLIED = "revision_applied"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CapabilityEntry:
    """A registered capability possessed by an agent."""
    capability_id: str
    agent_id: str
    name: str
    description: str
    proficiency: float
    confidence: float
    first_observed: str
    last_used: str
    success_count: int
    failure_count: int
    enabled: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this capability entry to a JSON-friendly dictionary."""
        return {
            "capability_id": self.capability_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "description": self.description,
            "proficiency": self.proficiency,
            "confidence": self.confidence,
            "first_observed": self.first_observed,
            "last_used": self.last_used,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "enabled": self.enabled,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LimitEntry:
    """A registered limit on an agent's behaviour or resources."""
    limit_id: str
    agent_id: str
    name: str
    limit_type: LimitType
    threshold: float
    unit: str
    hard_limit: bool
    current_load: float
    breached: bool
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this limit entry to a JSON-friendly dictionary."""
        return {
            "limit_id": self.limit_id,
            "agent_id": self.agent_id,
            "name": self.name,
            "limit_type": self.limit_type.value,
            "threshold": self.threshold,
            "unit": self.unit,
            "hard_limit": self.hard_limit,
            "current_load": self.current_load,
            "breached": self.breached,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class StateEntry:
    """A reading for a single state dimension of an agent."""
    agent_id: str
    dimension: StateDimension
    value: float
    trend: StateTrend
    updated_at: str
    history: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this state entry to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "dimension": self.dimension.value,
            "value": self.value,
            "trend": self.trend.value,
            "updated_at": self.updated_at,
            "history": list(self.history) if self.history else [],
        }


@dataclass
class GoalEntry:
    """An agent goal with priority, progress, and lifecycle status."""
    goal_id: str
    agent_id: str
    description: str
    priority: int
    progress: float
    status: GoalStatus
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this goal entry to a JSON-friendly dictionary."""
        return {
            "goal_id": self.goal_id,
            "agent_id": self.agent_id,
            "description": self.description,
            "priority": self.priority,
            "progress": self.progress,
            "status": self.status.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class BeliefEntry:
    """A proposition an agent holds with a confidence and a source."""
    belief_id: str
    agent_id: str
    statement: str
    confidence: float
    source: BeliefSource
    evidence_count: int
    formed_at: str
    last_updated: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this belief entry to a JSON-friendly dictionary."""
        return {
            "belief_id": self.belief_id,
            "agent_id": self.agent_id,
            "statement": self.statement,
            "confidence": self.confidence,
            "source": self.source.value,
            "evidence_count": self.evidence_count,
            "formed_at": self.formed_at,
            "last_updated": self.last_updated,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class SelfModelRevision:
    """A recorded revision of an agent's self-model."""
    revision_id: str
    agent_id: str
    trigger: str
    reason: str
    changes: List[Dict[str, Any]]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this revision to a JSON-friendly dictionary."""
        return {
            "revision_id": self.revision_id,
            "agent_id": self.agent_id,
            "trigger": self.trigger,
            "reason": self.reason,
            "changes": [dict(c) if isinstance(c, dict) else c for c in self.changes],
            "timestamp": self.timestamp,
        }


@dataclass
class SelfModel:
    """The unified per-agent self-model.

    Aggregates the agent's capabilities, limits, state, goals, and beliefs
    together with quality scores that summarise how accurate and consistent
    the model is.
    """
    agent_id: str
    capabilities: Dict[str, CapabilityEntry]
    limits: Dict[str, LimitEntry]
    state: Dict[str, StateEntry]
    goals: List[GoalEntry]
    beliefs: List[BeliefEntry]
    accuracy: float
    consistency: float
    last_self_check: Optional[str]
    created_at: str
    updated_at: str
    revisions: List[SelfModelRevision] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this self-model to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "capabilities": {k: v.to_dict() for k, v in self.capabilities.items()},
            "limits": {k: v.to_dict() for k, v in self.limits.items()},
            "state": {k: v.to_dict() for k, v in self.state.items()},
            "goals": [g.to_dict() for g in self.goals],
            "beliefs": [b.to_dict() for b in self.beliefs],
            "accuracy": self.accuracy,
            "consistency": self.consistency,
            "last_self_check": self.last_self_check,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "revisions": [r.to_dict() for r in self.revisions],
        }


@dataclass
class SelfModelStats:
    """Aggregate statistics about the self-model engine."""
    total_agents: int
    total_capabilities: int
    total_limits: int
    total_goals: int
    total_beliefs: int
    total_revisions: int
    avg_capability_proficiency: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these statistics to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_capabilities": self.total_capabilities,
            "total_limits": self.total_limits,
            "total_goals": self.total_goals,
            "total_beliefs": self.total_beliefs,
            "total_revisions": self.total_revisions,
            "avg_capability_proficiency": self.avg_capability_proficiency,
        }


@dataclass
class SelfModelSnapshot:
    """A complete snapshot of the self-model engine state."""
    initialized: bool
    models: List[SelfModel]
    events: List[SelfModelEvent]
    stats: SelfModelStats

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "initialized": self.initialized,
            "models": [m.to_dict() for m in self.models],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


@dataclass
class SelfModelEvent:
    """An observable lifecycle event emitted by the self-model engine."""
    event_id: str
    kind: SelfModelEventKind
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


# ---------------------------------------------------------------------------
# Self-Model Engine (Singleton with double-checked locking)
# ---------------------------------------------------------------------------


class SelfModelEngine:
    """Unified self-model engine for AI game agents.

    The engine maintains a per-agent self-model that unifies capabilities,
    limits, state, goals, beliefs, and revision history into a single
    coherent self-description. Other subsystems (planner, dialogue, etc.)
    can read the model via :meth:`inspect_self` or :meth:`get_model` to
    ground their behaviour in the agent's understanding of itself.

    It is a thread-safe singleton accessed via :meth:`get_instance` or the
    module-level :func:`get_self_model` helper.

    Usage:
        engine = get_self_model()
        model = engine.register_agent("agent_alpha")
        engine.add_capability("agent_alpha", "combat", proficiency=0.8)
        engine.set_state("agent_alpha", StateDimension.PHYSICAL, 0.9)
        description = engine.inspect_self("agent_alpha")
    """

    _instance: Optional["SelfModelEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # -- Construction (double-checked locking) ---------------------------

    def __new__(cls) -> "SelfModelEngine":
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

            # Per-agent self-models keyed by agent_id.
            self._models: Dict[str, SelfModel] = {}

            # Observable lifecycle events.
            self._events: List[SelfModelEvent] = []

            # Aggregate counters for diagnostics.
            self._capability_counter: int = 0
            self._limit_counter: int = 0
            self._goal_counter: int = 0
            self._belief_counter: int = 0
            self._revision_counter: int = 0
            self._state_counter: int = 0
            self._agent_counter: int = 0

            self._initialized: bool = True

            # Seed baseline self-model data.
            self._seed_data()

    @classmethod
    def get_instance(cls) -> "SelfModelEngine":
        """Return the singleton SelfModelEngine instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Agent registration and lookup
    # ------------------------------------------------------------------

    def register_agent(self, agent_id: str) -> SelfModel:
        """Create (or return an existing) self-model for an agent.

        Args:
            agent_id: Unique identifier of the agent to register.

        Returns:
            The :class:`SelfModel` for the agent. If the agent was already
            registered, the existing model is returned unchanged.
        """
        with self._lock:
            if agent_id in self._models:
                return self._models[agent_id]
            now = _now()
            model = SelfModel(
                agent_id=agent_id,
                capabilities={},
                limits={},
                state={},
                goals=[],
                beliefs=[],
                accuracy=0.0,
                consistency=1.0,
                last_self_check=None,
                created_at=now,
                updated_at=now,
                revisions=[],
            )
            self._models[agent_id] = model
            self._agent_counter += 1
            _evict_fifo_dict(self._models, _MAX_AGENTS)
            self._record_event(
                SelfModelEventKind.AGENT_REGISTERED,
                {"agent_id": agent_id},
            )
            return model

    def get_model(self, agent_id: str) -> Optional[SelfModel]:
        """Return the self-model for an agent, or None if not registered."""
        with self._lock:
            return self._models.get(agent_id)

    def list_agents(self) -> List[SelfModel]:
        """Return all registered agent self-models."""
        with self._lock:
            return list(self._models.values())

    def delete_model(self, agent_id: str) -> bool:
        """Remove the self-model for an agent. Returns True if removed."""
        with self._lock:
            removed = self._models.pop(agent_id, None)
            return removed is not None

    def _ensure_model(self, agent_id: str) -> SelfModel:
        """Return the model for an agent, creating one if missing.

        Assumes the caller already holds ``self._lock``.
        """
        model = self._models.get(agent_id)
        if model is not None:
            return model
        now = _now()
        model = SelfModel(
            agent_id=agent_id,
            capabilities={},
            limits={},
            state={},
            goals=[],
            beliefs=[],
            accuracy=0.0,
            consistency=1.0,
            last_self_check=None,
            created_at=now,
            updated_at=now,
            revisions=[],
        )
        self._models[agent_id] = model
        self._agent_counter += 1
        _evict_fifo_dict(self._models, _MAX_AGENTS)
        self._record_event(
            SelfModelEventKind.AGENT_REGISTERED,
            {"agent_id": agent_id},
        )
        return model

    def _touch_model(self, model: SelfModel) -> None:
        """Refresh the model's updated_at timestamp.

        Assumes the caller already holds ``self._lock``.
        """
        model.updated_at = _now()

    # ------------------------------------------------------------------
    # Capability management
    # ------------------------------------------------------------------

    def add_capability(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        proficiency: float = 0.5,
        confidence: float = 0.5,
    ) -> Optional[CapabilityEntry]:
        """Add a capability to an agent's self-model.

        Args:
            agent_id: Identifier of the agent.
            name: Short name of the capability.
            description: Optional longer description of the capability.
            proficiency: Initial proficiency in [0.0, 1.0] (clamped).
            confidence: Initial confidence in the proficiency in [0.0, 1.0]
                (clamped).

        Returns:
            The newly created :class:`CapabilityEntry`, or ``None`` if the
            agent is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            now = _now()
            entry = CapabilityEntry(
                capability_id=_new_id(),
                agent_id=agent_id,
                name=name,
                description=description or "",
                proficiency=_clamp(float(proficiency)),
                confidence=_clamp(float(confidence)),
                first_observed=now,
                last_used=now,
                success_count=0,
                failure_count=0,
                enabled=True,
                metadata={},
            )
            model.capabilities[entry.capability_id] = entry
            self._capability_counter += 1
            _evict_fifo_dict(model.capabilities, _MAX_CAPABILITIES_PER_AGENT)
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.CAPABILITY_ADDED,
                {
                    "agent_id": agent_id,
                    "capability_id": entry.capability_id,
                    "name": name,
                    "proficiency": entry.proficiency,
                    "confidence": entry.confidence,
                },
            )
            return entry

    def get_capability(
        self, agent_id: str, capability_id: str
    ) -> Optional[CapabilityEntry]:
        """Return a single capability entry by id, or None if not found."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            return model.capabilities.get(capability_id)

    def list_capabilities(self, agent_id: str) -> List[CapabilityEntry]:
        """Return all capabilities known for an agent."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            return list(model.capabilities.values())

    def update_capability(
        self,
        agent_id: str,
        capability_id: str,
        **kwargs: Any,
    ) -> Optional[CapabilityEntry]:
        """Update fields on a capability entry.

        Recognised keyword arguments mirror the fields on
        :class:`CapabilityEntry`: ``name``, ``description``, ``proficiency``,
        ``confidence``, ``enabled``, and ``metadata``.

        Args:
            agent_id: Identifier of the agent.
            capability_id: Identifier of the capability to update.
            **kwargs: Field updates. Proficiency and confidence are clamped
                to [0.0, 1.0].

        Returns:
            The updated :class:`CapabilityEntry`, or ``None`` if either the
            agent or the capability is not found.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            entry = model.capabilities.get(capability_id)
            if entry is None:
                return None
            for key, value in kwargs.items():
                if not hasattr(entry, key):
                    continue
                if key in ("proficiency", "confidence"):
                    value = _clamp(float(value))
                elif key == "metadata" and value is not None:
                    value = dict(value)
                setattr(entry, key, value)
            self._touch_model(model)
            return entry

    def record_capability_use(
        self, agent_id: str, capability_id: str, success: bool
    ) -> Optional[CapabilityEntry]:
        """Record a use of a capability and update derived statistics.

        Increments ``success_count`` or ``failure_count``, updates
        ``last_used``, and nudges ``proficiency`` toward 1.0 on success or
        toward 0.0 on failure using a small step so the value reflects
        observed outcomes.

        Args:
            agent_id: Identifier of the agent.
            capability_id: Identifier of the capability that was used.
            success: Whether the use was successful.

        Returns:
            The updated :class:`CapabilityEntry`, or ``None`` if either the
            agent or the capability is not found.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            entry = model.capabilities.get(capability_id)
            if entry is None:
                return None
            now = _now()
            entry.last_used = now
            step = 0.05
            if success:
                entry.success_count += 1
                entry.proficiency = _clamp(entry.proficiency + step)
            else:
                entry.failure_count += 1
                entry.proficiency = _clamp(entry.proficiency - step)
            self._touch_model(model)
            return entry

    # ------------------------------------------------------------------
    # Limit management
    # ------------------------------------------------------------------

    def register_limit(
        self,
        agent_id: str,
        name: str,
        limit_type: LimitType,
        threshold: float = 0.0,
        unit: str = "",
        hard_limit: bool = True,
    ) -> Optional[LimitEntry]:
        """Register a limit on an agent's self-model.

        Args:
            agent_id: Identifier of the agent.
            name: Short name of the limit (e.g. ``"stamina"``).
            limit_type: The :class:`LimitType` category.
            threshold: Numeric threshold for the limit.
            unit: Optional unit string (e.g. ``"hp"``, ``"mana"``).
            hard_limit: When ``True``, the limit cannot be exceeded safely.

        Returns:
            The newly created :class:`LimitEntry`, or ``None`` if the agent
            is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            now = _now()
            entry = LimitEntry(
                limit_id=_new_id(),
                agent_id=agent_id,
                name=name,
                limit_type=limit_type,
                threshold=float(threshold),
                unit=unit or "",
                hard_limit=bool(hard_limit),
                current_load=0.0,
                breached=False,
                created_at=now,
                updated_at=now,
                metadata={},
            )
            model.limits[entry.limit_id] = entry
            self._limit_counter += 1
            _evict_fifo_dict(model.limits, _MAX_LIMITS_PER_AGENT)
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.LIMIT_REGISTERED,
                {
                    "agent_id": agent_id,
                    "limit_id": entry.limit_id,
                    "name": name,
                    "limit_type": limit_type.value,
                    "threshold": entry.threshold,
                    "hard_limit": entry.hard_limit,
                },
            )
            return entry

    def list_limits(
        self,
        agent_id: str,
        limit_type: Optional[LimitType] = None,
    ) -> List[LimitEntry]:
        """Return limits for an agent, optionally filtered by type."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            results: List[LimitEntry] = []
            for limit in model.limits.values():
                if limit_type is not None and limit.limit_type != limit_type:
                    continue
                results.append(limit)
            return results

    def update_limit_load(
        self,
        agent_id: str,
        limit_id: str,
        current_load: float,
    ) -> Optional[LimitEntry]:
        """Update the current load of a limit and recompute the breach flag.

        A limit is considered breached when ``current_load >= threshold`` for
        positive thresholds, or when ``current_load <= threshold`` for
        negative thresholds. The ``breached`` field is set accordingly and
        returned in the updated entry.

        Args:
            agent_id: Identifier of the agent.
            limit_id: Identifier of the limit to update.
            current_load: New current load value (not clamped).

        Returns:
            The updated :class:`LimitEntry`, or ``None`` if either the agent
            or the limit is not found.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            entry = model.limits.get(limit_id)
            if entry is None:
                return None
            entry.current_load = float(current_load)
            entry.updated_at = _now()
            if entry.threshold >= 0:
                entry.breached = entry.current_load >= entry.threshold
            else:
                entry.breached = entry.current_load <= entry.threshold
            self._touch_model(model)
            return entry

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def set_state(
        self,
        agent_id: str,
        dimension: StateDimension,
        value: float,
    ) -> Optional[StateEntry]:
        """Set the value of a state dimension for an agent.

        The trend is derived by comparing the new value to the previous
        value (if any): a small change keeps the previous trend, a rise
        switches to :attr:`StateTrend.RISING`, and a fall switches to
        :attr:`StateTrend.FALLING`.

        Args:
            agent_id: Identifier of the agent.
            dimension: The :class:`StateDimension` being updated.
            value: New value of the dimension.

        Returns:
            The :class:`StateEntry` representing the updated state, or
            ``None`` if the agent is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            key = dimension.value
            existing = model.state.get(key)
            previous_value = existing.value if existing is not None else None
            if previous_value is None:
                trend = StateTrend.STABLE
            else:
                delta = float(value) - previous_value
                if abs(delta) < 1e-6:
                    trend = existing.trend if existing is not None else StateTrend.STABLE
                elif delta > 0:
                    trend = StateTrend.RISING
                else:
                    trend = StateTrend.FALLING
            history_entry: Dict[str, Any] = {
                "value": float(value),
                "timestamp": _now(),
            }
            history: List[Dict[str, Any]] = []
            if existing is not None:
                history = list(existing.history)
            history.append(history_entry)
            # Keep only the last 50 history points per dimension.
            if len(history) > 50:
                history = history[-50:]
            entry = StateEntry(
                agent_id=agent_id,
                dimension=dimension,
                value=float(value),
                trend=trend,
                updated_at=_now(),
                history=history,
            )
            model.state[key] = entry
            self._state_counter += 1
            _evict_fifo_dict(model.state, _MAX_STATES_PER_AGENT)
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.STATE_UPDATED,
                {
                    "agent_id": agent_id,
                    "dimension": dimension.value,
                    "value": entry.value,
                    "trend": entry.trend.value,
                },
            )
            return entry

    def get_state(
        self,
        agent_id: str,
        dimension: Optional[StateDimension] = None,
    ) -> List[StateEntry]:
        """Return state entries for an agent, optionally filtered by dimension."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            if dimension is None:
                return list(model.state.values())
            entry = model.state.get(dimension.value)
            return [entry] if entry is not None else []

    # ------------------------------------------------------------------
    # Goal management
    # ------------------------------------------------------------------

    def record_goal(
        self,
        agent_id: str,
        description: str,
        priority: int = 3,
    ) -> Optional[GoalEntry]:
        """Record a new goal for an agent.

        Args:
            agent_id: Identifier of the agent.
            description: Human-readable description of the goal.
            priority: Priority value, higher means more important. The
                engine stores the value as-is without clamping.

        Returns:
            The newly created :class:`GoalEntry`, or ``None`` if the agent
            is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            now = _now()
            entry = GoalEntry(
                goal_id=_new_id(),
                agent_id=agent_id,
                description=description,
                priority=int(priority),
                progress=0.0,
                status=GoalStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                metadata={},
            )
            model.goals.append(entry)
            # FIFO-evict oldest goals when over capacity.
            if len(model.goals) > _MAX_GOALS_PER_AGENT:
                model.goals = model.goals[-_MAX_GOALS_PER_AGENT:]
            self._goal_counter += 1
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.GOAL_RECORDED,
                {
                    "agent_id": agent_id,
                    "goal_id": entry.goal_id,
                    "description": description,
                    "priority": entry.priority,
                },
            )
            return entry

    def update_goal(
        self,
        agent_id: str,
        goal_id: str,
        **kwargs: Any,
    ) -> Optional[GoalEntry]:
        """Update fields on an existing goal.

        Recognised keyword arguments mirror the fields on
        :class:`GoalEntry`: ``description``, ``priority``, ``progress``,
        ``status``, and ``metadata``. ``progress`` is clamped to [0.0, 1.0].
        ``status`` may be provided as a :class:`GoalStatus` enum or its
        string value.

        Returns:
            The updated :class:`GoalEntry`, or ``None`` if either the agent
            or the goal is not found.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            target: Optional[GoalEntry] = None
            for goal in model.goals:
                if goal.goal_id == goal_id:
                    target = goal
                    break
            if target is None:
                return None
            for key, value in kwargs.items():
                if not hasattr(target, key):
                    continue
                if key == "progress":
                    value = _clamp(float(value))
                elif key == "status":
                    if isinstance(value, GoalStatus):
                        pass
                    elif isinstance(value, str):
                        value = GoalStatus(value)
                    else:
                        continue
                elif key == "metadata" and value is not None:
                    value = dict(value)
                setattr(target, key, value)
            target.updated_at = _now()
            self._touch_model(model)
            return target

    def list_goals(
        self,
        agent_id: str,
        status: Optional[GoalStatus] = None,
    ) -> List[GoalEntry]:
        """Return goals for an agent, optionally filtered by status."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            if status is None:
                return list(model.goals)
            return [g for g in model.goals if g.status == status]

    # ------------------------------------------------------------------
    # Belief management
    # ------------------------------------------------------------------

    def form_belief(
        self,
        agent_id: str,
        statement: str,
        source: Union[BeliefSource, str] = BeliefSource.INFERENCE,
        confidence: float = 0.5,
    ) -> Optional[BeliefEntry]:
        """Form a new belief for an agent.

        Args:
            agent_id: Identifier of the agent.
            statement: The propositional content of the belief.
            source: A :class:`BeliefSource` enum or its string value. The
                string ``"inference"`` is the default.
            confidence: Initial confidence in the belief in [0.0, 1.0]
                (clamped).

        Returns:
            The newly created :class:`BeliefEntry`, or ``None`` if the
            agent is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            if isinstance(source, str):
                try:
                    resolved_source = BeliefSource(source)
                except ValueError:
                    resolved_source = BeliefSource.INFERENCE
            else:
                resolved_source = source
            now = _now()
            entry = BeliefEntry(
                belief_id=_new_id(),
                agent_id=agent_id,
                statement=statement,
                confidence=_clamp(float(confidence)),
                source=resolved_source,
                evidence_count=0,
                formed_at=now,
                last_updated=now,
                metadata={},
            )
            model.beliefs.append(entry)
            if len(model.beliefs) > _MAX_BELIEFS_PER_AGENT:
                model.beliefs = model.beliefs[-_MAX_BELIEFS_PER_AGENT:]
            self._belief_counter += 1
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.BELIEF_FORMED,
                {
                    "agent_id": agent_id,
                    "belief_id": entry.belief_id,
                    "statement": statement,
                    "source": resolved_source.value,
                    "confidence": entry.confidence,
                },
            )
            return entry

    def update_belief(
        self,
        agent_id: str,
        belief_id: str,
        confidence: Optional[float] = None,
    ) -> Optional[BeliefEntry]:
        """Update an existing belief's confidence and evidence count.

        Each call increments ``evidence_count`` by one and, if a new
        ``confidence`` is provided, clamps it into [0.0, 1.0] and stores
        it. ``last_updated`` is refreshed.

        Returns:
            The updated :class:`BeliefEntry`, or ``None`` if either the
            agent or the belief is not found.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            target: Optional[BeliefEntry] = None
            for belief in model.beliefs:
                if belief.belief_id == belief_id:
                    target = belief
                    break
            if target is None:
                return None
            target.evidence_count += 1
            if confidence is not None:
                target.confidence = _clamp(float(confidence))
            target.last_updated = _now()
            self._touch_model(model)
            return target

    def list_beliefs(
        self,
        agent_id: str,
        min_confidence: float = 0.0,
    ) -> List[BeliefEntry]:
        """Return beliefs for an agent with confidence >= ``min_confidence``."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            threshold = float(min_confidence)
            return [b for b in model.beliefs if b.confidence >= threshold]

    # ------------------------------------------------------------------
    # Self inspection and quality scores
    # ------------------------------------------------------------------

    def inspect_self(self, agent_id: str) -> Dict[str, Any]:
        """Return a structured self-description for an agent.

        The output contains:

          * ``agent_id`` -- the agent identifier
          * ``capabilities`` -- list of capability summaries
          * ``limits`` -- list of limit summaries
          * ``state`` -- list of state dimension readings
          * ``top_goals`` -- active goals ordered by priority desc, capped
            at five
          * ``top_beliefs`` -- beliefs ordered by confidence desc, capped
            at five
          * ``accuracy`` -- the agent's accuracy score
          * ``consistency`` -- the agent's consistency score
          * ``last_self_check`` -- timestamp of the most recent self check

        Records a :attr:`SelfModelEventKind.MODEL_INSPECTED` event and
        refreshes the ``last_self_check`` timestamp.

        Returns:
            A dictionary describing the agent's self-model, or an empty
            dictionary if the agent is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return {}
            capabilities = [c.to_dict() for c in model.capabilities.values()]
            limits = [l.to_dict() for l in model.limits.values()]
            state = [s.to_dict() for s in model.state.values()]
            top_goals = sorted(
                [g for g in model.goals if g.status == GoalStatus.ACTIVE],
                key=lambda g: g.priority,
                reverse=True,
            )[:5]
            top_beliefs = sorted(
                model.beliefs,
                key=lambda b: b.confidence,
                reverse=True,
            )[:5]
            now = _now()
            model.last_self_check = now
            self._touch_model(model)
            description: Dict[str, Any] = {
                "agent_id": agent_id,
                "capabilities": capabilities,
                "limits": limits,
                "state": state,
                "top_goals": [g.to_dict() for g in top_goals],
                "top_beliefs": [b.to_dict() for b in top_beliefs],
                "accuracy": model.accuracy,
                "consistency": model.consistency,
                "last_self_check": model.last_self_check,
            }
            self._record_event(
                SelfModelEventKind.MODEL_INSPECTED,
                {"agent_id": agent_id},
            )
            return description

    def compute_accuracy(self, agent_id: str) -> float:
        """Compute the accuracy of an agent's self-model.

        Accuracy is defined as the average of per-capability success rates
        (success_count / total_uses). Capabilities with no recorded uses
        contribute 0.5 (a neutral prior) so newly added capabilities do
        not collapse the score. The result is stored on the model and
        returned in the range [0.0, 1.0].

        Returns:
            The computed accuracy in [0.0, 1.0], or ``0.0`` if the agent is
            not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return 0.0
            if not model.capabilities:
                model.accuracy = 0.0
                self._touch_model(model)
                return 0.0
            total = 0.0
            count = 0
            for cap in model.capabilities.values():
                uses = cap.success_count + cap.failure_count
                if uses <= 0:
                    rate = 0.5
                else:
                    rate = cap.success_count / float(uses)
                total += rate
                count += 1
            avg = total / count if count else 0.0
            model.accuracy = _clamp(round(avg, 4))
            self._touch_model(model)
            return model.accuracy

    def compute_consistency(self, agent_id: str) -> float:
        """Compute the consistency of an agent's self-model.

        Consistency is a heuristic in [0.0, 1.0] that summarises how well
        the agent's state, beliefs, and goals agree with one another. The
        formula is::

            base = 1.0
            - 0.1 * number of breached hard limits
            - 0.05 * number of breached soft limits
            - 0.05 * number of state dimensions in FALLING trend
            + 0.02 * number of state dimensions in RISING trend
            + 0.01 * number of high-confidence beliefs (>= 0.8)

        Clamped to [0.0, 1.0]. When the agent has no state, beliefs, or
        limits the base is 1.0.

        Returns:
            The computed consistency in [0.0, 1.0], or ``0.0`` if the agent
            is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return 0.0
            base = 1.0
            breached_hard = 0
            breached_soft = 0
            for limit in model.limits.values():
                if not limit.breached:
                    continue
                if limit.hard_limit:
                    breached_hard += 1
                else:
                    breached_soft += 1
            rising = 0
            falling = 0
            for state in model.state.values():
                if state.trend == StateTrend.RISING:
                    rising += 1
                elif state.trend == StateTrend.FALLING:
                    falling += 1
            high_conf_beliefs = sum(1 for b in model.beliefs if b.confidence >= 0.8)
            score = (
                base
                - 0.1 * breached_hard
                - 0.05 * breached_soft
                - 0.05 * falling
                + 0.02 * rising
                + 0.01 * high_conf_beliefs
            )
            model.consistency = _clamp(round(score, 4))
            self._touch_model(model)
            return model.consistency

    # ------------------------------------------------------------------
    # Revisions
    # ------------------------------------------------------------------

    def apply_revision(
        self,
        agent_id: str,
        trigger: str,
        reason: str,
        changes: List[Dict[str, Any]],
    ) -> Optional[SelfModelRevision]:
        """Record a self-model revision for an agent.

        Args:
            agent_id: Identifier of the agent whose model is being revised.
            trigger: Short label describing what triggered the revision.
            reason: Human-readable reason for the revision.
            changes: A list of change dictionaries describing the
                modification in detail.

        Returns:
            The newly created :class:`SelfModelRevision`, or ``None`` if
            the agent is not registered.
        """
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return None
            revision = SelfModelRevision(
                revision_id=_new_id(),
                agent_id=agent_id,
                trigger=trigger,
                reason=reason,
                changes=[dict(c) if isinstance(c, dict) else c for c in (changes or [])],
                timestamp=_now(),
            )
            model.revisions.append(revision)
            if len(model.revisions) > _MAX_REVISIONS_PER_AGENT:
                model.revisions = model.revisions[-_MAX_REVISIONS_PER_AGENT:]
            self._revision_counter += 1
            self._touch_model(model)
            self._record_event(
                SelfModelEventKind.REVISION_APPLIED,
                {
                    "agent_id": agent_id,
                    "revision_id": revision.revision_id,
                    "trigger": trigger,
                    "change_count": len(revision.changes),
                },
            )
            return revision

    def list_revisions(
        self,
        agent_id: str,
        limit: int = 20,
    ) -> List[SelfModelRevision]:
        """Return recent revisions for an agent, newest first."""
        with self._lock:
            model = self._models.get(agent_id)
            if model is None:
                return []
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(model.revisions))[:n]

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: SelfModelEventKind,
        payload: Dict[str, Any],
    ) -> None:
        """Record an observable self-model event.

        Assumes the caller already holds ``self._lock``. The event log is
        bounded by ``_MAX_EVENTS`` with FIFO eviction.
        """
        event = SelfModelEvent(
            event_id=_new_id(),
            kind=kind,
            timestamp=_now(),
            payload=dict(payload) if payload else {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, limit: int = 100) -> List[SelfModelEvent]:
        """Return the most recent self-model events, newest first."""
        with self._lock:
            n = max(0, int(limit))
            if n == 0:
                return []
            return list(reversed(self._events))[:n]

    def get_stats(self) -> SelfModelStats:
        """Return aggregate statistics about the self-model engine."""
        with self._lock:
            total_capabilities = 0
            total_limits = 0
            total_goals = 0
            total_beliefs = 0
            total_revisions = 0
            proficiency_sum = 0.0
            for model in self._models.values():
                total_capabilities += len(model.capabilities)
                total_limits += len(model.limits)
                total_goals += len(model.goals)
                total_beliefs += len(model.beliefs)
                total_revisions += len(model.revisions)
                for cap in model.capabilities.values():
                    proficiency_sum += cap.proficiency
            avg_prof = (
                proficiency_sum / total_capabilities if total_capabilities else 0.0
            )
            return SelfModelStats(
                total_agents=len(self._models),
                total_capabilities=total_capabilities,
                total_limits=total_limits,
                total_goals=total_goals,
                total_beliefs=total_beliefs,
                total_revisions=total_revisions,
                avg_capability_proficiency=round(avg_prof, 4),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a comprehensive status dictionary for diagnostics."""
        with self._lock:
            stats = self.get_stats()
            status: Dict[str, Any] = {
                "initialized": self._initialized,
                "total_agents": len(self._models),
                "total_capabilities": stats.total_capabilities,
                "total_limits": stats.total_limits,
                "total_goals": stats.total_goals,
                "total_beliefs": stats.total_beliefs,
                "total_revisions": stats.total_revisions,
                "total_events": len(self._events),
                "agent_counter": self._agent_counter,
                "capability_counter": self._capability_counter,
                "limit_counter": self._limit_counter,
                "goal_counter": self._goal_counter,
                "belief_counter": self._belief_counter,
                "revision_counter": self._revision_counter,
                "state_counter": self._state_counter,
                "avg_capability_proficiency": stats.avg_capability_proficiency,
                "capacities": {
                    "max_agents": _MAX_AGENTS,
                    "max_capabilities_per_agent": _MAX_CAPABILITIES_PER_AGENT,
                    "max_limits_per_agent": _MAX_LIMITS_PER_AGENT,
                    "max_states_per_agent": _MAX_STATES_PER_AGENT,
                    "max_goals_per_agent": _MAX_GOALS_PER_AGENT,
                    "max_beliefs_per_agent": _MAX_BELIEFS_PER_AGENT,
                    "max_revisions_per_agent": _MAX_REVISIONS_PER_AGENT,
                    "max_events": _MAX_EVENTS,
                },
            }
            return status

    def get_snapshot(self) -> SelfModelSnapshot:
        """Return a complete snapshot of the self-model engine state."""
        with self._lock:
            return SelfModelSnapshot(
                initialized=self._initialized,
                models=list(self._models.values()),
                events=list(self._events),
                stats=self.get_stats(),
            )

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all tracked state and re-seed baseline data.

        Unlike a one-shot clear, ``reset`` re-seeds the baseline self-model
        data so the engine returns to a freshly initialised state.
        """
        with self._lock:
            self._models.clear()
            self._events.clear()
            self._capability_counter = 0
            self._limit_counter = 0
            self._goal_counter = 0
            self._belief_counter = 0
            self._revision_counter = 0
            self._state_counter = 0
            self._agent_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seed data
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with baseline SparkLabs self-model data.

        Seeds two agents (``agent_alpha`` -- a warrior, ``agent_beta`` -- a
        mage) with capabilities, limits, state dimensions, goals, and one
        revision history entry, providing a useful out-of-the-box demo.
        """
        # --- Agent Alpha: the warrior ---------------------------------
        alpha = self.register_agent("agent_alpha")
        combat = self.add_capability(
            "agent_alpha",
            "combat",
            description="Engaging in melee and ranged combat",
            proficiency=0.8,
            confidence=0.75,
        )
        stealth = self.add_capability(
            "agent_alpha",
            "stealth",
            description="Moving unseen and avoiding detection",
            proficiency=0.5,
            confidence=0.6,
        )
        self.add_capability(
            "agent_alpha",
            "navigation",
            description="Traversing wilderness and urban environments",
            proficiency=0.7,
            confidence=0.7,
        )
        # Record a few uses of combat and stealth so accuracy has signal.
        if combat is not None:
            for _ in range(7):
                self.record_capability_use("agent_alpha", combat.capability_id, True)
            for _ in range(2):
                self.record_capability_use("agent_alpha", combat.capability_id, False)
        if stealth is not None:
            for _ in range(3):
                self.record_capability_use("agent_alpha", stealth.capability_id, True)
            for _ in range(3):
                self.record_capability_use("agent_alpha", stealth.capability_id, False)

        # Two limits for alpha.
        self.register_limit(
            "agent_alpha",
            "stamina",
            LimitType.PHYSICAL,
            threshold=100.0,
            unit="points",
            hard_limit=False,
        )
        self.register_limit(
            "agent_alpha",
            "attention",
            LimitType.MEMORY,
            threshold=0.0,
            unit="normalized",
            hard_limit=False,
        )

        # Two state dimensions for alpha.
        self.set_state("agent_alpha", StateDimension.PHYSICAL, 0.85)
        self.set_state("agent_alpha", StateDimension.MENTAL, 0.7)

        # Two goals for alpha.
        self.record_goal(
            "agent_alpha",
            "Defeat the dragon threatening the kingdom",
            priority=5,
        )
        self.record_goal(
            "agent_alpha",
            "Train with the master swordsman",
            priority=3,
        )

        # --- Agent Beta: the mage -------------------------------------
        self.register_agent("agent_beta")
        self.add_capability(
            "agent_beta",
            "magic",
            description="Casting spells and weaving magical effects",
            proficiency=0.9,
            confidence=0.85,
        )
        self.add_capability(
            "agent_beta",
            "alchemy",
            description="Brewing potions and transmuting reagents",
            proficiency=0.6,
            confidence=0.55,
        )

        # One limit for beta.
        self.register_limit(
            "agent_beta",
            "mana",
            LimitType.COMPUTATIONAL,
            threshold=100.0,
            unit="points",
            hard_limit=False,
        )

        # Two state dimensions for beta.
        self.set_state("agent_beta", StateDimension.MENTAL, 0.9)
        self.set_state("agent_beta", StateDimension.EMOTIONAL, 0.65)

        # One goal for beta.
        self.record_goal(
            "agent_beta",
            "Master the forbidden art of chronomancy",
            priority=4,
        )

        # --- A revision history entry for alpha -----------------------
        self.apply_revision(
            "agent_alpha",
            trigger="initial_assessment",
            reason="Baseline self-model established from training data",
            changes=[
                {"component": ModelComponent.CAPABILITIES.value, "action": "seeded"},
                {"component": ModelComponent.LIMITS.value, "action": "seeded"},
                {"component": ModelComponent.STATE.value, "action": "seeded"},
            ],
        )


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_self_model() -> SelfModelEngine:
    """Return the singleton SelfModelEngine instance."""
    return SelfModelEngine.get_instance()
