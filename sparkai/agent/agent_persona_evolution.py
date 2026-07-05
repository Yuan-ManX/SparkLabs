"""
SparkLabs Agent - Persona Evolution Engine

This module models how an AI agent's personality traits drift, reinforce,
and evolve over time based on lived experience. While the PersonalitySystem
holds a static trait profile, this engine records the trajectory of trait
changes: each significant experience (a success, a failure, a social
encounter, a creative breakthrough) exerts pressure on one or more traits,
nudging them in a direction. Over many experiences the trait landscape
shifts, producing an agent whose personality is shaped by its history.

The engine maintains:
  - A trait timeline (every trait change is recorded with timestamp,
    cause, and magnitude)
  - Reinforcement curves (traits that are repeatedly exercised grow
    stronger; neglected traits atrophy)
  - Mutation events (rare, high-impact experiences that can cause sudden
    trait shifts)
  - Evolution snapshots (periodic captures of the full trait landscape
    for comparison)

Architecture:
  PersonaEvolutionEngine (Singleton, double-checked locking, threading.RLock)
    |-- TraitPressure        -- a directional force on a trait
    |-- ExperienceRecord     -- a lived experience that shaped the agent
    |-- TraitChange          -- a single recorded trait value change
    |-- MutationEvent        -- a rare high-impact personality shift
    |-- EvolutionSnapshot    -- a periodic capture of all trait values
    |-- EvolutionStats       -- aggregate evolution statistics
    |-- EvolutionSnapshot2   -- full engine snapshot
    |-- EvolutionEvent       -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
engine is safe to call from multiple agent threads. Bounded in-memory
stores use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import math
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Capacity constants - bounded in-memory stores with FIFO eviction
# ---------------------------------------------------------------------------

_MAX_EXPERIENCES: int = 2000
_MAX_CHANGES: int = 5000
_MAX_MUTATIONS: int = 200
_MAX_SNAPSHOTS: int = 100
_MAX_EVENTS: int = 2000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "evo") -> str:
    """Generate a short unique identifier with a readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive [low, high] range."""
    if value < low:
        return float(low)
    if value > high:
        return float(high)
    return float(value)


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds."""
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_deque(store: deque, max_size: int) -> None:
    """Evict the oldest inserted entries from a deque until within bounds."""
    while len(store) > max_size:
        try:
            store.popleft()
        except IndexError:
            break


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TraitAxis(Enum):
    """The axes along which a trait can move."""
    CREATIVE_ANALYTICAL = "creative_analytical"
    PLAYFUL_SERIOUS = "playful_serious"
    CAUTIOUS_BOLD = "cautious_bold"
    CONCISE_ELABORATE = "concise_elaborate"
    INTROVERT_EXTROVERT = "introvert_extrovert"
    COOPERATIVE_INDEPENDENT = "cooperative_independent"


class ExperienceKind(Enum):
    """The kind of experience that shapes the agent."""
    SUCCESS = "success"
    FAILURE = "failure"
    SOCIAL = "social"
    CREATIVE = "creative"
    CONFLICT = "conflict"
    LEARNING = "learning"
    DISCOVERY = "discovery"
    CHALLENGE = "challenge"


class PressureDirection(Enum):
    """The direction of pressure on a trait axis."""
    INCREASE = "increase"
    DECREASE = "decrease"
    REINFORCE = "reinforce"


class MutationTrigger(Enum):
    """What triggered a rare high-impact personality mutation."""
    BREAKTHROUGH = "breakthrough"
    TRAUMA = "trauma"
    EPIPHANY = "epiphany"
    PARADIGM_SHIFT = "paradigm_shift"
    CRITICAL_FAILURE = "critical_failure"
    MENTOR_INFLUENCE = "mentor_influence"


class EvolutionEventKind(Enum):
    """Observable lifecycle events emitted by the evolution engine."""
    EXPERIENCE_RECORDED = "experience_recorded"
    TRAIT_CHANGED = "trait_changed"
    MUTATION_OCCURRED = "mutation_occurred"
    SNAPSHOT_CAPTURED = "snapshot_captured"
    AGENT_REGISTERED = "agent_registered"
    AGENT_RESET = "agent_reset"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class TraitPressure:
    """A directional force exerted on a trait axis by an experience."""
    axis: TraitAxis
    direction: PressureDirection
    magnitude: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this pressure to a JSON-friendly dictionary."""
        return {
            "axis": self.axis.value,
            "direction": self.direction.value,
            "magnitude": round(self.magnitude, 6),
        }


@dataclass
class ExperienceRecord:
    """A lived experience that shaped the agent's personality."""
    experience_id: str
    agent_id: str
    kind: ExperienceKind
    description: str
    pressures: List[TraitPressure]
    intensity: float
    recorded_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this experience to a JSON-friendly dictionary."""
        return {
            "experience_id": self.experience_id,
            "agent_id": self.agent_id,
            "kind": self.kind.value,
            "description": self.description,
            "pressures": [p.to_dict() for p in self.pressures],
            "intensity": round(self.intensity, 6),
            "recorded_at": self.recorded_at,
        }


@dataclass
class TraitChange:
    """A single recorded trait value change for an agent."""
    change_id: str
    agent_id: str
    axis: TraitAxis
    old_value: float
    new_value: float
    delta: float
    cause: str
    cause_id: str
    changed_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this change to a JSON-friendly dictionary."""
        return {
            "change_id": self.change_id,
            "agent_id": self.agent_id,
            "axis": self.axis.value,
            "old_value": round(self.old_value, 6),
            "new_value": round(self.new_value, 6),
            "delta": round(self.delta, 6),
            "cause": self.cause,
            "cause_id": self.cause_id,
            "changed_at": self.changed_at,
        }


@dataclass
class MutationEvent:
    """A rare high-impact personality shift."""
    mutation_id: str
    agent_id: str
    trigger: MutationTrigger
    description: str
    axis_changes: Dict[str, float]
    magnitude: float
    occurred_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this mutation to a JSON-friendly dictionary."""
        return {
            "mutation_id": self.mutation_id,
            "agent_id": self.agent_id,
            "trigger": self.trigger.value,
            "description": self.description,
            "axis_changes": {k: round(v, 6) for k, v in self.axis_changes.items()},
            "magnitude": round(self.magnitude, 6),
            "occurred_at": self.occurred_at,
        }


@dataclass
class EvolutionSnapshot:
    """A periodic capture of all trait values for an agent."""
    snapshot_id: str
    agent_id: str
    trait_values: Dict[str, float]
    experience_count: int
    mutation_count: int
    captured_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this snapshot to a JSON-friendly dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "trait_values": {k: round(v, 6) for k, v in self.trait_values.items()},
            "experience_count": self.experience_count,
            "mutation_count": self.mutation_count,
            "captured_at": self.captured_at,
        }


@dataclass
class AgentEvolutionState:
    """The evolution state of a single agent."""
    agent_id: str
    trait_values: Dict[str, float]
    trait_reinforcement: Dict[str, float]
    experience_count: int
    mutation_count: int
    last_experience_at: str
    last_mutation_at: str
    registered_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this state to a JSON-friendly dictionary."""
        return {
            "agent_id": self.agent_id,
            "trait_values": {k: round(v, 6) for k, v in self.trait_values.items()},
            "trait_reinforcement": {k: round(v, 6) for k, v in self.trait_reinforcement.items()},
            "experience_count": self.experience_count,
            "mutation_count": self.mutation_count,
            "last_experience_at": self.last_experience_at,
            "last_mutation_at": self.last_mutation_at,
            "registered_at": self.registered_at,
        }


@dataclass
class EvolutionStats:
    """Aggregate statistics about the evolution engine."""
    total_agents: int
    total_experiences: int
    total_changes: int
    total_mutations: int
    total_snapshots: int
    total_events: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a JSON-friendly dictionary."""
        return {
            "total_agents": self.total_agents,
            "total_experiences": self.total_experiences,
            "total_changes": self.total_changes,
            "total_mutations": self.total_mutations,
            "total_snapshots": self.total_snapshots,
            "total_events": self.total_events,
        }


@dataclass
class EvolutionEvent:
    """An observable lifecycle event emitted by the evolution engine."""
    event_id: str
    kind: EvolutionEventKind
    agent_id: str
    payload: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "agent_id": self.agent_id,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class PersonaEvolutionEngine:
    """Models how agent personality traits evolve through lived experience.

    Implemented as a thread-safe singleton with double-checked locking.
    All public mutating methods acquire ``self._lock`` (a re-entrant lock)
    so the engine is safe to call from multiple agent threads.
    """

    _instance: Optional["PersonaEvolutionEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Default starting trait values (midpoint of each axis)
    _DEFAULT_TRAITS: Dict[str, float] = {
        TraitAxis.CREATIVE_ANALYTICAL.value: 0.5,
        TraitAxis.PLAYFUL_SERIOUS.value: 0.5,
        TraitAxis.CAUTIOUS_BOLD.value: 0.5,
        TraitAxis.CONCISE_ELABORATE.value: 0.5,
        TraitAxis.INTROVERT_EXTROVERT.value: 0.5,
        TraitAxis.COOPERATIVE_INDEPENDENT.value: 0.5,
    }

    # How strongly each experience kind pushes each trait axis
    _PRESSURE_MAP: Dict[ExperienceKind, List[Tuple[TraitAxis, PressureDirection, float]]] = {
        ExperienceKind.SUCCESS: [
            (TraitAxis.CAUTIOUS_BOLD, PressureDirection.INCREASE, 0.05),
            (TraitAxis.INTROVERT_EXTROVERT, PressureDirection.INCREASE, 0.02),
        ],
        ExperienceKind.FAILURE: [
            (TraitAxis.CAUTIOUS_BOLD, PressureDirection.DECREASE, 0.04),
            (TraitAxis.PLAYFUL_SERIOUS, PressureDirection.DECREASE, 0.03),
        ],
        ExperienceKind.SOCIAL: [
            (TraitAxis.INTROVERT_EXTROVERT, PressureDirection.INCREASE, 0.06),
            (TraitAxis.COOPERATIVE_INDEPENDENT, PressureDirection.INCREASE, 0.04),
        ],
        ExperienceKind.CREATIVE: [
            (TraitAxis.CREATIVE_ANALYTICAL, PressureDirection.INCREASE, 0.07),
            (TraitAxis.PLAYFUL_SERIOUS, PressureDirection.INCREASE, 0.03),
        ],
        ExperienceKind.CONFLICT: [
            (TraitAxis.COOPERATIVE_INDEPENDENT, PressureDirection.DECREASE, 0.05),
            (TraitAxis.PLAYFUL_SERIOUS, PressureDirection.DECREASE, 0.02),
        ],
        ExperienceKind.LEARNING: [
            (TraitAxis.CREATIVE_ANALYTICAL, PressureDirection.DECREASE, 0.06),
            (TraitAxis.CONCISE_ELABORATE, PressureDirection.INCREASE, 0.03),
        ],
        ExperienceKind.DISCOVERY: [
            (TraitAxis.CREATIVE_ANALYTICAL, PressureDirection.INCREASE, 0.05),
            (TraitAxis.CAUTIOUS_BOLD, PressureDirection.INCREASE, 0.04),
        ],
        ExperienceKind.CHALLENGE: [
            (TraitAxis.CAUTIOUS_BOLD, PressureDirection.INCREASE, 0.04),
            (TraitAxis.PLAYFUL_SERIOUS, PressureDirection.DECREASE, 0.03),
        ],
    }

    def __new__(cls) -> "PersonaEvolutionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._initialized: bool = True
            self._agents: Dict[str, AgentEvolutionState] = {}
            self._experiences: Dict[str, ExperienceRecord] = {}
            self._changes: deque[TraitChange] = deque(maxlen=_MAX_CHANGES)
            self._changes_by_agent: Dict[str, deque[TraitChange]] = {}
            self._mutations: Dict[str, MutationEvent] = {}
            self._mutations_by_agent: Dict[str, deque[MutationEvent]] = {}
            self._snapshots: deque[EvolutionSnapshot] = deque(maxlen=_MAX_SNAPSHOTS)
            self._snapshots_by_agent: Dict[str, deque[EvolutionSnapshot]] = {}
            self._events: deque[EvolutionEvent] = deque(maxlen=_MAX_EVENTS)
            self._experience_counter = 0
            self._change_counter = 0
            self._mutation_counter = 0
            self._snapshot_counter = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed the engine with sample agents and evolution history."""
        self.register_agent("agent_alpha", {
            TraitAxis.CREATIVE_ANALYTICAL.value: 0.7,
            TraitAxis.PLAYFUL_SERIOUS.value: 0.4,
            TraitAxis.CAUTIOUS_BOLD.value: 0.6,
            TraitAxis.CONCISE_ELABORATE.value: 0.3,
            TraitAxis.INTROVERT_EXTROVERT.value: 0.65,
            TraitAxis.COOPERATIVE_INDEPENDENT.value: 0.55,
        })
        self.register_agent("agent_beta", {
            TraitAxis.CREATIVE_ANALYTICAL.value: 0.3,
            TraitAxis.PLAYFUL_SERIOUS.value: 0.7,
            TraitAxis.CAUTIOUS_BOLD.value: 0.35,
            TraitAxis.CONCISE_ELABORATE.value: 0.75,
            TraitAxis.INTROVERT_EXTROVERT.value: 0.4,
            TraitAxis.COOPERATIVE_INDEPENDENT.value: 0.45,
        })

    # ------------------------------------------------------------------
    # Internal event recording
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: EvolutionEventKind,
        agent_id: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EvolutionEvent:
        """Record an audit event (caller must hold ``self._lock``)."""
        event = EvolutionEvent(
            event_id=_new_id("ev"),
            kind=kind,
            agent_id=agent_id,
            payload=dict(payload) if payload else {},
            timestamp=_now(),
        )
        _evict_fifo_deque(self._events, _MAX_EVENTS)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Agent registration
    # ------------------------------------------------------------------

    def register_agent(
        self,
        agent_id: str,
        initial_traits: Optional[Dict[str, float]] = None,
    ) -> AgentEvolutionState:
        """Register a new agent for evolution tracking."""
        with self._lock:
            if agent_id in self._agents:
                return self._agents[agent_id]
            traits = dict(self._DEFAULT_TRAITS)
            if initial_traits:
                for k, v in initial_traits.items():
                    traits[k] = _clamp(float(v))
            reinforcement = {k: 0.0 for k in traits}
            state = AgentEvolutionState(
                agent_id=agent_id,
                trait_values=traits,
                trait_reinforcement=reinforcement,
                experience_count=0,
                mutation_count=0,
                last_experience_at="",
                last_mutation_at="",
                registered_at=_now(),
            )
            self._agents[agent_id] = state
            self._changes_by_agent[agent_id] = deque(maxlen=_MAX_CHANGES)
            self._mutations_by_agent[agent_id] = deque(maxlen=_MAX_MUTATIONS)
            self._snapshots_by_agent[agent_id] = deque(maxlen=_MAX_SNAPSHOTS)
            self._record_event(
                EvolutionEventKind.AGENT_REGISTERED,
                agent_id,
                {"initial_traits": dict(traits)},
            )
            return state

    def get_agent(self, agent_id: str) -> Optional[AgentEvolutionState]:
        """Return the evolution state for an agent."""
        with self._lock:
            return self._agents.get(agent_id)

    def list_agents(self) -> List[AgentEvolutionState]:
        """Return all registered agents."""
        with self._lock:
            return list(self._agents.values())

    def reset_agent(self, agent_id: str) -> Optional[AgentEvolutionState]:
        """Reset an agent's evolution to default traits."""
        with self._lock:
            if agent_id not in self._agents:
                return None
            state = self._agents[agent_id]
            state.trait_values = dict(self._DEFAULT_TRAITS)
            state.trait_reinforcement = {k: 0.0 for k in state.trait_values}
            state.experience_count = 0
            state.mutation_count = 0
            state.last_experience_at = ""
            state.last_mutation_at = ""
            self._changes_by_agent[agent_id] = deque(maxlen=_MAX_CHANGES)
            self._mutations_by_agent[agent_id] = deque(maxlen=_MAX_MUTATIONS)
            self._record_event(
                EvolutionEventKind.AGENT_RESET,
                agent_id,
                {},
            )
            return state

    # ------------------------------------------------------------------
    # Experience recording
    # ------------------------------------------------------------------

    def record_experience(
        self,
        agent_id: str,
        kind: Union[ExperienceKind, str],
        description: str = "",
        intensity: float = 0.5,
        custom_pressures: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[ExperienceRecord]:
        """Record a lived experience and apply its trait pressures.

        The experience kind determines default pressures on trait axes.
        Custom pressures can be supplied to override or augment defaults.
        The ``intensity`` multiplier scales how strongly the pressures
        affect the current trait values.
        """
        with self._lock:
            state = self._agents.get(agent_id)
            if state is None:
                return None
            exp_kind = _resolve_kind(kind)
            if exp_kind is None:
                return None
            intensity = _clamp(float(intensity))

            pressures: List[TraitPressure] = []
            for axis, direction, mag in self._PRESSURE_MAP.get(exp_kind, []):
                pressures.append(TraitPressure(
                    axis=axis,
                    direction=direction,
                    magnitude=mag * intensity,
                ))
            if custom_pressures:
                for cp in custom_pressures:
                    axis = _resolve_axis(cp.get("axis"))
                    direction = _resolve_direction(cp.get("direction"))
                    if axis is None or direction is None:
                        continue
                    magnitude = _clamp(float(cp.get("magnitude", 0.05)), 0.0, 1.0)
                    pressures.append(TraitPressure(
                        axis=axis,
                        direction=direction,
                        magnitude=magnitude * intensity,
                    ))

            experience = ExperienceRecord(
                experience_id=_new_id("exp"),
                agent_id=agent_id,
                kind=exp_kind,
                description=description,
                pressures=pressures,
                intensity=intensity,
                recorded_at=_now(),
            )
            self._experiences[experience.experience_id] = experience
            self._experience_counter += 1
            _evict_fifo_dict(self._experiences, _MAX_EXPERIENCES)

            state.experience_count += 1
            state.last_experience_at = experience.recorded_at

            for pressure in pressures:
                self._apply_pressure(state, pressure, experience.experience_id, "experience")

            self._record_event(
                EvolutionEventKind.EXPERIENCE_RECORDED,
                agent_id,
                {
                    "experience_id": experience.experience_id,
                    "kind": exp_kind.value,
                    "pressure_count": len(pressures),
                },
            )
            return experience

    def _apply_pressure(
        self,
        state: AgentEvolutionState,
        pressure: TraitPressure,
        cause_id: str,
        cause: str,
    ) -> None:
        """Apply a single trait pressure to an agent's state.

        The pressure magnitude is scaled by the agent's current reinforcement
        on that axis: well-exercised traits respond more strongly to relevant
        pressures. The resulting delta is clamped so the trait value stays
        within [0, 1].
        """
        # Caller must hold self._lock
        axis_key = pressure.axis.value
        old_value = state.trait_values.get(axis_key, 0.5)
        reinforcement = state.trait_reinforcement.get(axis_key, 0.0)
        reinforcement_boost = 1.0 + reinforcement * 0.3

        if pressure.direction == PressureDirection.REINFORCE:
            state.trait_reinforcement[axis_key] = _clamp(reinforcement + pressure.magnitude)
            return

        sign = 1.0 if pressure.direction == PressureDirection.INCREASE else -1.0
        delta = sign * pressure.magnitude * reinforcement_boost
        new_value = _clamp(old_value + delta)
        actual_delta = new_value - old_value

        if abs(actual_delta) < 1e-9:
            return

        state.trait_values[axis_key] = new_value
        change = TraitChange(
            change_id=_new_id("chg"),
            agent_id=state.agent_id,
            axis=pressure.axis,
            old_value=old_value,
            new_value=new_value,
            delta=actual_delta,
            cause=cause,
            cause_id=cause_id,
            changed_at=_now(),
        )
        self._changes.append(change)
        self._change_counter += 1
        agent_changes = self._changes_by_agent.setdefault(
            state.agent_id, deque(maxlen=_MAX_CHANGES)
        )
        _evict_fifo_deque(agent_changes, _MAX_CHANGES)
        agent_changes.append(change)
        self._record_event(
            EvolutionEventKind.TRAIT_CHANGED,
            state.agent_id,
            {
                "axis": axis_key,
                "old_value": round(old_value, 6),
                "new_value": round(new_value, 6),
                "delta": round(actual_delta, 6),
                "cause": cause,
            },
        )

    # ------------------------------------------------------------------
    # Mutation events
    # ------------------------------------------------------------------

    def record_mutation(
        self,
        agent_id: str,
        trigger: Union[MutationTrigger, str],
        description: str = "",
        axis_changes: Optional[Dict[str, float]] = None,
        magnitude: float = 0.2,
    ) -> Optional[MutationEvent]:
        """Record a rare high-impact personality mutation.

        Mutations apply large, sudden shifts to trait values, bypassing
        the gradual pressure model. They represent transformative
        experiences like breakthroughs, traumas, or paradigm shifts.
        """
        with self._lock:
            state = self._agents.get(agent_id)
            if state is None:
                return None
            mut_trigger = _resolve_trigger(trigger)
            if mut_trigger is None:
                return None
            magnitude = _clamp(float(magnitude), 0.0, 1.0)
            effective_changes: Dict[str, float] = {}
            if axis_changes:
                for k, v in axis_changes.items():
                    axis = _resolve_axis(k)
                    if axis is None:
                        continue
                    clamped = _clamp(float(v), -1.0, 1.0) * magnitude
                    effective_changes[axis.value] = clamped
            if not effective_changes:
                return None

            mutation = MutationEvent(
                mutation_id=_new_id("mut"),
                agent_id=agent_id,
                trigger=mut_trigger,
                description=description,
                axis_changes=dict(effective_changes),
                magnitude=magnitude,
                occurred_at=_now(),
            )
            self._mutations[mutation.mutation_id] = mutation
            self._mutation_counter += 1
            _evict_fifo_dict(self._mutations, _MAX_MUTATIONS)

            state.mutation_count += 1
            state.last_mutation_at = mutation.occurred_at

            for axis_key, change_val in effective_changes.items():
                old_value = state.trait_values.get(axis_key, 0.5)
                new_value = _clamp(old_value + change_val)
                actual_delta = new_value - old_value
                if abs(actual_delta) < 1e-9:
                    continue
                state.trait_values[axis_key] = new_value
                change = TraitChange(
                    change_id=_new_id("chg"),
                    agent_id=agent_id,
                    axis=TraitAxis(axis_key),
                    old_value=old_value,
                    new_value=new_value,
                    delta=actual_delta,
                    cause="mutation",
                    cause_id=mutation.mutation_id,
                    changed_at=_now(),
                )
                self._changes.append(change)
                self._change_counter += 1
                agent_changes = self._changes_by_agent.setdefault(
                    agent_id, deque(maxlen=_MAX_CHANGES)
                )
                _evict_fifo_deque(agent_changes, _MAX_CHANGES)
                agent_changes.append(change)

            self._record_event(
                EvolutionEventKind.MUTATION_OCCURRED,
                agent_id,
                {
                    "mutation_id": mutation.mutation_id,
                    "trigger": mut_trigger.value,
                    "axis_count": len(effective_changes),
                },
            )
            return mutation

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def capture_snapshot(self, agent_id: str) -> Optional[EvolutionSnapshot]:
        """Capture a snapshot of an agent's current trait landscape."""
        with self._lock:
            state = self._agents.get(agent_id)
            if state is None:
                return None
            snapshot = EvolutionSnapshot(
                snapshot_id=_new_id("snp"),
                agent_id=agent_id,
                trait_values=dict(state.trait_values),
                experience_count=state.experience_count,
                mutation_count=state.mutation_count,
                captured_at=_now(),
            )
            self._snapshots.append(snapshot)
            self._snapshot_counter += 1
            _evict_fifo_deque(self._snapshots, _MAX_SNAPSHOTS)
            agent_snaps = self._snapshots_by_agent.setdefault(
                agent_id, deque(maxlen=_MAX_SNAPSHOTS)
            )
            _evict_fifo_deque(agent_snaps, _MAX_SNAPSHOTS)
            agent_snaps.append(snapshot)
            self._record_event(
                EvolutionEventKind.SNAPSHOT_CAPTURED,
                agent_id,
                {"snapshot_id": snapshot.snapshot_id},
            )
            return snapshot

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_experience(self, experience_id: str) -> Optional[ExperienceRecord]:
        """Return a single experience by id."""
        with self._lock:
            return self._experiences.get(experience_id)

    def list_experiences(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[ExperienceRecord]:
        """Return experiences, optionally filtered by agent."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_EXPERIENCES))
            if agent_id:
                items = [e for e in self._experiences.values() if e.agent_id == agent_id]
            else:
                items = list(self._experiences.values())
            return items[-limit:]

    def list_changes(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[TraitChange]:
        """Return trait changes, optionally filtered by agent."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_CHANGES))
            if agent_id:
                items = list(self._changes_by_agent.get(agent_id, deque()))
            else:
                items = list(self._changes)
            return items[-limit:]

    def list_mutations(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[MutationEvent]:
        """Return mutation events, optionally filtered by agent."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_MUTATIONS))
            if agent_id:
                items = list(self._mutations_by_agent.get(agent_id, deque()))
            else:
                items = list(self._mutations.values())
            return items[-limit:]

    def list_snapshots(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[EvolutionSnapshot]:
        """Return evolution snapshots, optionally filtered by agent."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_SNAPSHOTS))
            if agent_id:
                items = list(self._snapshots_by_agent.get(agent_id, deque()))
            else:
                items = list(self._snapshots)
            return items[-limit:]

    def list_events(self, limit: int = 50) -> List[EvolutionEvent]:
        """Return the most recent engine lifecycle events."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_EVENTS))
            return list(self._events)[-limit:]

    def get_trait_timeline(
        self,
        agent_id: str,
        axis: Union[TraitAxis, str],
    ) -> List[TraitChange]:
        """Return the full change history for a single trait axis."""
        with self._lock:
            resolved = _resolve_axis(axis)
            if resolved is None:
                return []
            changes = self._changes_by_agent.get(agent_id, deque())
            return [c for c in changes if c.axis == resolved]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status summary for monitoring."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_agents": len(self._agents),
                "total_experiences": len(self._experiences),
                "total_changes": len(self._changes),
                "total_mutations": len(self._mutations),
                "total_snapshots": len(self._snapshots),
                "total_events": len(self._events),
                "experience_counter": self._experience_counter,
                "change_counter": self._change_counter,
                "mutation_counter": self._mutation_counter,
                "snapshot_counter": self._snapshot_counter,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_experiences": _MAX_EXPERIENCES,
                    "max_changes": _MAX_CHANGES,
                    "max_mutations": _MAX_MUTATIONS,
                    "max_snapshots": _MAX_SNAPSHOTS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_stats(self) -> EvolutionStats:
        """Return aggregate evolution statistics."""
        with self._lock:
            return EvolutionStats(
                total_agents=len(self._agents),
                total_experiences=len(self._experiences),
                total_changes=len(self._changes),
                total_mutations=len(self._mutations),
                total_snapshots=len(self._snapshots),
                total_events=len(self._events),
            )

    def reset(self) -> None:
        """Reset the engine to its seeded state."""
        with self._lock:
            self._agents.clear()
            self._experiences.clear()
            self._changes.clear()
            self._changes_by_agent.clear()
            self._mutations.clear()
            self._mutations_by_agent.clear()
            self._snapshots.clear()
            self._snapshots_by_agent.clear()
            self._events.clear()
            self._experience_counter = 0
            self._change_counter = 0
            self._mutation_counter = 0
            self._snapshot_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Enum resolvers
# ---------------------------------------------------------------------------


def _resolve_axis(value: Union[TraitAxis, str, None]) -> Optional[TraitAxis]:
    """Coerce a value into a :class:`TraitAxis` enum instance."""
    if value is None:
        return None
    if isinstance(value, TraitAxis):
        return value
    if isinstance(value, str):
        try:
            return TraitAxis(value)
        except ValueError:
            return None
    return None


def _resolve_kind(value: Union[ExperienceKind, str, None]) -> Optional[ExperienceKind]:
    """Coerce a value into an :class:`ExperienceKind` enum instance."""
    if value is None:
        return None
    if isinstance(value, ExperienceKind):
        return value
    if isinstance(value, str):
        try:
            return ExperienceKind(value)
        except ValueError:
            return None
    return None


def _resolve_direction(value: Union[PressureDirection, str, None]) -> Optional[PressureDirection]:
    """Coerce a value into a :class:`PressureDirection` enum instance."""
    if value is None:
        return None
    if isinstance(value, PressureDirection):
        return value
    if isinstance(value, str):
        try:
            return PressureDirection(value)
        except ValueError:
            return None
    return None


def _resolve_trigger(value: Union[MutationTrigger, str, None]) -> Optional[MutationTrigger]:
    """Coerce a value into a :class:`MutationTrigger` enum instance."""
    if value is None:
        return None
    if isinstance(value, MutationTrigger):
        return value
    if isinstance(value, str):
        try:
            return MutationTrigger(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


def get_persona_evolution() -> PersonaEvolutionEngine:
    """Return the shared :class:`PersonaEvolutionEngine` singleton instance."""
    return PersonaEvolutionEngine()
