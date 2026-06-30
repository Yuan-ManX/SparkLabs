"""
SparkLabs Agent - Cognitive Attention Allocator

Cognitive attention allocation system for AI agents operating inside the
SparkLabs game engine. Agents have limited attention capacity and must
dynamically allocate focus across competing stimuli in the game world.
The system computes salience scores for each potential attention target
based on novelty, intensity, relevance, urgency, social salience and
threat, then selects which targets to attend to based on the current
attention mode (FOCUSED, SCANNING, DIVIDED, SUSTAINED, VIGILANT).

Architecture:
  AttentionAllocatorEngine (Singleton)
    |-- AttentionTarget Registry (per-agent stimuli with salience factors)
    |-- FocusState Manager (per-agent attention budget and active targets)
    |-- Salience Computer (weighted aggregation of multi-factor salience)
    |-- Attention Shifter (mode-aware selection of the next target)
    |-- Distraction Tracker (resistance vs. capture of competing stimuli)
    |-- Audit Trail (history of attention shifts and distractions)
    |-- Event Bus (handlers for attention lifecycle events)

Core Capabilities:
  - register_target / remove_target / get_target / list_targets
  - compute_salience / update_salience (per-factor recomputation)
  - acquire_focus / release_focus (budget-bounded attention capture)
  - shift_attention (mode-aware re-targeting with audit trail)
  - set_mode / get_focus_state (FOCUSED, SCANNING, DIVIDED, SUSTAINED, VIGILANT)
  - register_distraction (resistance vs. capture decisions)
  - tick (one attention cycle: recompute salience, shift if needed)
  - get_audit_trail (per-agent history of attention shifts)
  - register_event_handler / list_events (event subscriptions)
  - get_status / get_snapshot / reset (lifecycle and observability)

Usage:
    engine = get_attention_allocator()
    target = engine.register_target(
        agent_id="agent_1",
        target_id="enemy_scout",
        label="Enemy scout spotted near the ridge",
        position=(120.0, 64.0, 12.0),
        salience=0.6,
        factors={SalienceFactor.THREAT.value: 0.9, SalienceFactor.URGENCY.value: 0.7},
        priority=0.8,
    )
    engine.set_mode("agent_1", AttentionMode.FOCUSED)
    engine.acquire_focus("agent_1", target.id, budget_cost=0.5)
    engine.tick("agent_1")
"""

from __future__ import annotations

import datetime, threading, uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class AttentionMode(Enum):
    """High-level attention strategy that controls how an agent allocates focus."""
    FOCUSED = "focused"
    SCANNING = "scanning"
    DIVIDED = "divided"
    SUSTAINED = "sustained"
    VIGILANT = "vigilant"


class SalienceFactor(Enum):
    """Factors that contribute to the aggregate salience of an attention target."""
    NOVELTY = "novelty"
    INTENSITY = "intensity"
    RELEVANCE = "relevance"
    URGENCY = "urgency"
    SOCIAL = "social"
    THREAT = "threat"


class AttentionEventKind(Enum):
    """Kinds of events emitted by the attention allocator engine."""
    TARGET_REGISTERED = "target_registered"
    TARGET_REMOVED = "target_removed"
    FOCUS_ACQUIRED = "focus_acquired"
    FOCUS_RELEASED = "focus_released"
    ATTENTION_SHIFT = "attention_shift"
    MODE_CHANGED = "mode_changed"
    DISTRACTION = "distraction"
    SALIENCE_UPDATED = "salience_updated"


# ---------------------------------------------------------------------------
# Default salience weights per factor
# ---------------------------------------------------------------------------

_DEFAULT_FACTOR_WEIGHTS: Dict[str, float] = {
    SalienceFactor.NOVELTY.value: 0.15,
    SalienceFactor.INTENSITY.value: 0.20,
    SalienceFactor.RELEVANCE.value: 0.25,
    SalienceFactor.URGENCY.value: 0.20,
    SalienceFactor.SOCIAL.value: 0.10,
    SalienceFactor.THREAT.value: 0.10,
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class AttentionTarget:
    """A potential focus target for an AI agent in the game world.

    Each target tracks the salience factors that make it worth attending to,
    the aggregate salience score, and an optional priority modifier used to
    bias selection during attention shifts.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    target_id: str = ""
    label: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    salience: float = 0.0
    factors: Dict[str, float] = field(default_factory=dict)
    priority: float = 0.5
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    last_updated: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "label": self.label,
            "position": list(self.position),
            "salience": round(self.salience, 4),
            "factors": {k: round(v, 4) for k, v in self.factors.items()},
            "priority": round(self.priority, 4),
            "timestamp": self.timestamp,
            "last_updated": self.last_updated,
            "metadata": dict(self.metadata),
        }


@dataclass
class FocusState:
    """Per-agent attention focus state.

    Tracks the current attention mode, the set of targets the agent is
    actively attending to, and how much of the agent's attention budget
    has been consumed versus the total available budget.
    """
    agent_id: str = ""
    mode: AttentionMode = AttentionMode.SCANNING
    active_target_ids: List[str] = field(default_factory=list)
    attention_budget: float = 1.0
    used_budget: float = 0.0
    last_shift_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")
    shift_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "mode": self.mode.value,
            "active_target_ids": list(self.active_target_ids),
            "attention_budget": round(self.attention_budget, 4),
            "used_budget": round(self.used_budget, 4),
            "remaining_budget": round(max(0.0, self.attention_budget - self.used_budget), 4),
            "last_shift_at": self.last_shift_at,
            "shift_count": self.shift_count,
        }


@dataclass
class AttentionShift:
    """A recorded transition of an agent's focus from one target to another."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    from_target_id: str = ""
    to_target_id: str = ""
    reason: str = ""
    mode: AttentionMode = AttentionMode.SCANNING
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "from_target_id": self.from_target_id,
            "to_target_id": self.to_target_id,
            "reason": self.reason,
            "mode": self.mode.value,
            "timestamp": self.timestamp,
        }


@dataclass
class DistractionEvent:
    """A competing stimulus that may or may not have captured the agent's focus."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    target_id: str = ""
    strength: float = 0.0
    resisted: bool = True
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "target_id": self.target_id,
            "strength": round(self.strength, 4),
            "resisted": self.resisted,
            "timestamp": self.timestamp,
        }


@dataclass
class AttentionStats:
    """Aggregate statistics across the attention allocator engine."""
    total_targets_registered: int = 0
    total_targets_removed: int = 0
    total_focus_acquired: int = 0
    total_focus_released: int = 0
    total_shifts: int = 0
    total_distractions: int = 0
    total_resisted: int = 0
    last_updated_at: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_targets_registered": self.total_targets_registered,
            "total_targets_removed": self.total_targets_removed,
            "total_focus_acquired": self.total_focus_acquired,
            "total_focus_released": self.total_focus_released,
            "total_shifts": self.total_shifts,
            "total_distractions": self.total_distractions,
            "total_resisted": self.total_resisted,
            "last_updated_at": self.last_updated_at,
        }


@dataclass
class AttentionSnapshot:
    """Point-in-time snapshot of the attention allocator state."""
    agent_count: int = 0
    total_targets: int = 0
    total_active_focus: int = 0
    stats: AttentionStats = field(default_factory=AttentionStats)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_targets": self.total_targets,
            "total_active_focus": self.total_active_focus,
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class AttentionEvent:
    """An event emitted by the attention allocator for handler dispatch."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: str = ""
    agent_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind,
            "agent_id": self.agent_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Attention Allocator Engine (Singleton)
# ---------------------------------------------------------------------------


class AttentionAllocatorEngine:
    """Singleton engine that allocates cognitive attention for AI agents.

    The engine maintains a registry of attention targets per agent, tracks
    per-agent focus state and budget consumption, computes salience from
    multiple factors, decides attention shifts based on the current mode,
    and records a full audit trail of shifts and distractions. All public
    methods are thread-safe and guarded by a re-entrant lock.
    """

    _instance: Optional["AttentionAllocatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    # Configuration constants
    _MAX_TARGETS: int = 5000
    _MAX_SHIFTS_PER_AGENT: int = 500
    _MAX_DISTRACTIONS_PER_AGENT: int = 500
    _MAX_EVENTS: int = 2000
    _DEFAULT_BUDGET: float = 1.0
    _DEFAULT_BUDGET_COST: float = 0.3
    _DISTRACTION_RESISTANCE_BASE: float = 0.5
    _SALIENCE_DECAY_RATE: float = 0.02
    _NOVELTY_DECAY_PER_TICK: float = 0.05

    def __new__(cls) -> "AttentionAllocatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AttentionAllocatorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized: bool = True

        # Core registries
        self._targets: Dict[str, AttentionTarget] = {}
        self._focus_states: Dict[str, FocusState] = {}
        self._shifts: Dict[str, AttentionShift] = {}
        self._distractions: Dict[str, DistractionEvent] = {}

        # Per-agent indices
        self._agent_targets: Dict[str, List[str]] = {}
        self._agent_active_targets: Dict[str, List[str]] = {}
        self._agent_shifts: Dict[str, List[str]] = {}
        self._agent_distractions: Dict[str, List[str]] = {}

        # Event system
        self._events: List[AttentionEvent] = []
        self._event_handlers: Dict[str, List[Tuple[str, Callable[[AttentionEvent], None]]]] = {}

        # Statistics
        self._stats: AttentionStats = AttentionStats()

        # Seed default demo data
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Seed two demo agents with three targets each and acquire initial focus.

        This populates the engine with example data so it is immediately
        useful without further configuration, and so tests can exercise the
        read paths out of the box.
        """
        # Agent alpha: a vigilant guard scanning the perimeter
        self._ensure_focus_state("agent_alpha", AttentionMode.VIGILANT, budget=1.0)
        alpha_targets = [
            (
                "alpha_enemy_scout",
                "Enemy scout near the eastern ridge",
                (120.0, 64.0, 12.0),
                {
                    SalienceFactor.THREAT.value: 0.92,
                    SalienceFactor.URGENCY.value: 0.78,
                    SalienceFactor.NOVELTY.value: 0.65,
                    SalienceFactor.RELEVANCE.value: 0.88,
                },
                0.85,
            ),
            (
                "alpha_friendly_patrol",
                "Friendly patrol returning to base",
                (60.0, 32.0, 4.0),
                {
                    SalienceFactor.SOCIAL.value: 0.55,
                    SalienceFactor.RELEVANCE.value: 0.40,
                    SalienceFactor.INTENSITY.value: 0.20,
                },
                0.30,
            ),
            (
                "alpha_resource_cache",
                "Resource cache detected in the cave",
                (88.0, 12.0, -8.0),
                {
                    SalienceFactor.NOVELTY.value: 0.72,
                    SalienceFactor.INTENSITY.value: 0.45,
                    SalienceFactor.RELEVANCE.value: 0.60,
                },
                0.55,
            ),
        ]
        for target_id, label, position, factors, priority in alpha_targets:
            self._register_target_internal(
                agent_id="agent_alpha",
                target_id=target_id,
                label=label,
                position=position,
                salience=0.5,
                factors=dict(factors),
                priority=priority,
                metadata={"seeded": True},
            )

        # Agent bravo: a focused crafter working on a complex build
        self._ensure_focus_state("agent_bravo", AttentionMode.FOCUSED, budget=1.0)
        bravo_targets = [
            (
                "bravo_craft_bench",
                "Crafting bench the agent is operating",
                (10.0, 10.0, 2.0),
                {
                    SalienceFactor.RELEVANCE.value: 0.95,
                    SalienceFactor.INTENSITY.value: 0.70,
                    SalienceFactor.URGENCY.value: 0.30,
                },
                0.90,
            ),
            (
                "bravo_npc_visitor",
                "NPC visitor approaching the workshop",
                (22.0, 14.0, 2.0),
                {
                    SalienceFactor.SOCIAL.value: 0.80,
                    SalienceFactor.NOVELTY.value: 0.60,
                    SalienceFactor.URGENCY.value: 0.45,
                },
                0.50,
            ),
            (
                "bravo_alarm_bell",
                "Distant alarm bell ringing",
                (200.0, 180.0, 30.0),
                {
                    SalienceFactor.THREAT.value: 0.85,
                    SalienceFactor.URGENCY.value: 0.90,
                    SalienceFactor.INTENSITY.value: 0.65,
                },
                0.75,
            ),
        ]
        for target_id, label, position, factors, priority in bravo_targets:
            self._register_target_internal(
                agent_id="agent_bravo",
                target_id=target_id,
                label=label,
                position=position,
                salience=0.5,
                factors=dict(factors),
                priority=priority,
                metadata={"seeded": True},
            )

        # Acquire initial focus on the most salient target for each agent
        alpha_top = self._highest_salience_target("agent_alpha")
        if alpha_top is not None:
            self._acquire_focus_internal(
                agent_id="agent_alpha",
                target_id=alpha_top.id,
                budget_cost=0.4,
            )

        bravo_top = self._highest_salience_target("agent_bravo")
        if bravo_top is not None:
            self._acquire_focus_internal(
                agent_id="agent_bravo",
                target_id=bravo_top.id,
                budget_cost=0.5,
            )

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: AttentionEventKind,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> AttentionEvent:
        """Record an event and invoke any registered handlers.

        A faulty handler must never break engine operation; exceptions are
        swallowed silently to preserve attention allocation continuity.
        """
        event = AttentionEvent(
            kind=kind.value,
            agent_id=agent_id,
            payload=dict(payload),
        )
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            # Drop the oldest events to stay within capacity
            overflow = len(self._events) - self._MAX_EVENTS
            del self._events[:overflow]
        handlers = self._event_handlers.get(kind.value, [])
        for _handler_id, handler in handlers:
            try:
                handler(event)
            except Exception:
                pass
        return event

    def register_event_handler(
        self,
        kind: AttentionEventKind,
        handler: Callable[[AttentionEvent], None],
    ) -> str:
        """Register a handler for a specific attention event kind.

        Returns a handler id that can be used for future de-registration
        via :meth:`unregister_event_handler`.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            key = kind.value
            if key not in self._event_handlers:
                self._event_handlers[key] = []
            self._event_handlers[key].append((handler_id, handler))
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Remove a previously registered handler by its id.

        Returns True if the handler was found and removed.
        """
        with self._lock:
            for key, handlers in self._event_handlers.items():
                for index, (existing_id, _existing_handler) in enumerate(handlers):
                    if existing_id == handler_id:
                        handlers.pop(index)
                        return True
            return False

    def list_events(
        self,
        event_kind: Optional[AttentionEventKind] = None,
        limit: int = 100,
    ) -> List[AttentionEvent]:
        """Return recent events, optionally filtered by kind."""
        with self._lock:
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e.kind == event_kind.value]
            return events[-limit:]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_focus_state(
        self,
        agent_id: str,
        mode: AttentionMode = AttentionMode.SCANNING,
        budget: Optional[float] = None,
    ) -> FocusState:
        """Get or create the FocusState for an agent."""
        state = self._focus_states.get(agent_id)
        if state is None:
            state = FocusState(
                agent_id=agent_id,
                mode=mode,
                attention_budget=budget if budget is not None else self._DEFAULT_BUDGET,
            )
            self._focus_states[agent_id] = state
            self._agent_targets.setdefault(agent_id, [])
            self._agent_active_targets.setdefault(agent_id, [])
            self._agent_shifts.setdefault(agent_id, [])
            self._agent_distractions.setdefault(agent_id, [])
        return state

    def _register_target_internal(
        self,
        agent_id: str,
        target_id: str,
        label: str,
        position: Tuple[float, float, float],
        salience: float,
        factors: Dict[str, float],
        priority: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttentionTarget:
        """Internal target registration without lock acquisition."""
        self._enforce_target_capacity()

        target = AttentionTarget(
            agent_id=agent_id,
            target_id=target_id,
            label=label,
            position=position,
            salience=salience,
            factors={k: max(0.0, min(1.0, v)) for k, v in factors.items()},
            priority=max(0.0, min(1.0, priority)),
            metadata=dict(metadata or {}),
        )
        # Compute aggregate salience from factors
        target.salience = self._compute_salience_from_factors(target.factors, target.priority)
        self._targets[target.id] = target

        self._agent_targets.setdefault(agent_id, [])
        if target.id not in self._agent_targets[agent_id]:
            self._agent_targets[agent_id].append(target.id)

        # Ensure the focus state exists so the agent is tracked
        self._ensure_focus_state(agent_id)

        self._stats.total_targets_registered += 1
        self._stats.last_updated_at = datetime.datetime.utcnow().isoformat() + "Z"
        return target

    def _acquire_focus_internal(
        self,
        agent_id: str,
        target_id: str,
        budget_cost: float,
    ) -> bool:
        """Internal focus acquisition without lock acquisition."""
        state = self._ensure_focus_state(agent_id)
        cost = max(0.0, min(1.0, budget_cost))
        if state.used_budget + cost > state.attention_budget + 1e-9:
            # Not enough remaining budget to acquire this target
            return False
        if target_id in state.active_target_ids:
            return True
        state.active_target_ids.append(target_id)
        state.used_budget = min(state.attention_budget, state.used_budget + cost)
        self._agent_active_targets.setdefault(agent_id, [])
        if target_id not in self._agent_active_targets[agent_id]:
            self._agent_active_targets[agent_id].append(target_id)
        self._stats.total_focus_acquired += 1
        self._stats.last_updated_at = datetime.datetime.utcnow().isoformat() + "Z"
        return True

    def _compute_salience_from_factors(
        self,
        factors: Dict[str, float],
        priority: float,
    ) -> float:
        """Aggregate salience factors into a single score in [0, 1].

        Uses a weighted average across known SalienceFactor entries,
        then blends in the explicit priority modifier.
        """
        if not factors:
            return max(0.0, min(1.0, priority))
        total_weight = 0.0
        weighted_sum = 0.0
        for factor_key, raw_value in factors.items():
            weight = _DEFAULT_FACTOR_WEIGHTS.get(factor_key, 0.05)
            value = max(0.0, min(1.0, raw_value))
            weighted_sum += value * weight
            total_weight += weight
        if total_weight <= 0.0:
            factor_average = 0.0
        else:
            factor_average = weighted_sum / total_weight
        # Blend factor-derived salience with explicit priority (60/40)
        blended = factor_average * 0.6 + max(0.0, min(1.0, priority)) * 0.4
        return max(0.0, min(1.0, blended))

    def _highest_salience_target(self, agent_id: str) -> Optional[AttentionTarget]:
        """Return the highest-salience target for an agent (ties broken by priority)."""
        candidate_ids = self._agent_targets.get(agent_id, [])
        best: Optional[AttentionTarget] = None
        for target_id in candidate_ids:
            target = self._targets.get(target_id)
            if target is None:
                continue
            if best is None or target.salience > best.salience or (
                target.salience == best.salience and target.priority > best.priority
            ):
                best = target
        return best

    def _enforce_target_capacity(self) -> None:
        """Evict the oldest targets when capacity is exceeded."""
        if len(self._targets) < self._MAX_TARGETS:
            return
        # Sort by last_updated ascending and drop the oldest entries
        sorted_targets = sorted(
            self._targets.items(),
            key=lambda item: item[1].last_updated,
        )
        overflow = len(self._targets) - self._MAX_TARGETS + 1
        for tid, target in sorted_targets[:overflow]:
            self._targets.pop(tid, None)
            agent_targets = self._agent_targets.get(target.agent_id)
            if agent_targets and tid in agent_targets:
                agent_targets.remove(tid)
            active = self._agent_active_targets.get(target.agent_id)
            if active and tid in active:
                active.remove(tid)

    def _now_iso(self) -> str:
        return datetime.datetime.utcnow().isoformat() + "Z"

    # ------------------------------------------------------------------
    # Target management
    # ------------------------------------------------------------------

    def register_target(
        self,
        agent_id: str,
        target_id: str,
        label: str,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        salience: float = 0.0,
        factors: Optional[Dict[str, float]] = None,
        priority: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AttentionTarget:
        """Register a new attention target for an agent.

        If a target with the same ``target_id`` already exists for the
        given agent it is replaced with the new entry. The aggregate
        salience is recomputed from the supplied factors and priority
        unless an explicit non-zero ``salience`` override is supplied.
        """
        with self._lock:
            # Remove any prior target with the same logical id for this agent
            existing = self._find_target_by_logical_id(agent_id, target_id)
            if existing is not None:
                self._remove_target_internal(existing.id, emit=False)

            target = self._register_target_internal(
                agent_id=agent_id,
                target_id=target_id,
                label=label,
                position=position,
                salience=salience,
                factors=dict(factors or {}),
                priority=priority,
                metadata=metadata,
            )
            # Allow an explicit salience override when supplied
            if salience > 0.0:
                target.salience = max(0.0, min(1.0, salience))

            self._emit_event(
                AttentionEventKind.TARGET_REGISTERED,
                agent_id,
                {
                    "target_id": target.id,
                    "logical_target_id": target.target_id,
                    "label": target.label,
                    "salience": target.salience,
                },
            )
            return target

    def remove_target(self, target_id: str) -> bool:
        """Remove a target by its internal id. Releases focus if active."""
        with self._lock:
            return self._remove_target_internal(target_id, emit=True)

    def _remove_target_internal(self, target_id: str, emit: bool) -> bool:
        """Internal target removal without lock acquisition."""
        target = self._targets.get(target_id)
        if target is None:
            return False
        agent_id = target.agent_id
        # Release focus if the agent was attending to it
        self._release_focus_internal(agent_id, target_id, emit=emit)
        self._targets.pop(target_id, None)

        agent_targets = self._agent_targets.get(agent_id, [])
        if target_id in agent_targets:
            agent_targets.remove(target_id)

        active = self._agent_active_targets.get(agent_id, [])
        if target_id in active:
            active.remove(target_id)

        self._stats.total_targets_removed += 1
        self._stats.last_updated_at = self._now_iso()
        if emit:
            self._emit_event(
                AttentionEventKind.TARGET_REMOVED,
                agent_id,
                {"target_id": target_id, "logical_target_id": target.target_id},
            )
        return True

    def _find_target_by_logical_id(
        self,
        agent_id: str,
        logical_target_id: str,
    ) -> Optional[AttentionTarget]:
        """Find an existing target by agent and logical target id."""
        for target_id in self._agent_targets.get(agent_id, []):
            target = self._targets.get(target_id)
            if target is not None and target.target_id == logical_target_id:
                return target
        return None

    def get_target(self, target_id: str) -> Optional[AttentionTarget]:
        """Retrieve a registered target by its internal id."""
        with self._lock:
            return self._targets.get(target_id)

    def list_targets(
        self,
        agent_id: str,
        min_salience: float = 0.0,
    ) -> List[AttentionTarget]:
        """List targets for an agent, filtered by a minimum salience threshold.

        Results are sorted by descending salience (ties broken by priority).
        """
        with self._lock:
            results: List[AttentionTarget] = []
            for target_id in self._agent_targets.get(agent_id, []):
                target = self._targets.get(target_id)
                if target is None:
                    continue
                if target.salience < min_salience:
                    continue
                results.append(target)
            results.sort(
                key=lambda t: (t.salience, t.priority),
                reverse=True,
            )
            return results

    # ------------------------------------------------------------------
    # Salience computation
    # ------------------------------------------------------------------

    def compute_salience(self, target_id: str) -> float:
        """Recompute and store the aggregate salience for a target.

        Returns 0.0 if the target does not exist.
        """
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                return 0.0
            target.salience = self._compute_salience_from_factors(
                target.factors, target.priority
            )
            target.last_updated = self._now_iso()
            self._stats.last_updated_at = self._now_iso()
            self._emit_event(
                AttentionEventKind.SALIENCE_UPDATED,
                target.agent_id,
                {
                    "target_id": target_id,
                    "salience": target.salience,
                    "factors": dict(target.factors),
                },
            )
            return target.salience

    def update_salience(
        self,
        target_id: str,
        factor: SalienceFactor,
        value: float,
    ) -> Optional[AttentionTarget]:
        """Update a single salience factor for a target and recompute.

        Returns the updated target, or None if the target was not found.
        """
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                return None
            target.factors[factor.value] = max(0.0, min(1.0, value))
            target.salience = self._compute_salience_from_factors(
                target.factors, target.priority
            )
            target.last_updated = self._now_iso()
            self._stats.last_updated_at = self._now_iso()
            self._emit_event(
                AttentionEventKind.SALIENCE_UPDATED,
                target.agent_id,
                {
                    "target_id": target_id,
                    "factor": factor.value,
                    "value": target.factors[factor.value],
                    "salience": target.salience,
                },
            )
            return target

    # ------------------------------------------------------------------
    # Focus management
    # ------------------------------------------------------------------

    def acquire_focus(
        self,
        agent_id: str,
        target_id: str,
        budget_cost: float = 0.3,
    ) -> bool:
        """Acquire focus on a target, consuming attention budget.

        Returns False if the target does not exist, the agent has no
        remaining budget, or the target is already actively attended.
        """
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                return False
            success = self._acquire_focus_internal(agent_id, target_id, budget_cost)
            if success:
                self._emit_event(
                    AttentionEventKind.FOCUS_ACQUIRED,
                    agent_id,
                    {
                        "target_id": target_id,
                        "budget_cost": budget_cost,
                        "used_budget": self._focus_states[agent_id].used_budget,
                    },
                )
            return success

    def release_focus(self, agent_id: str, target_id: str) -> bool:
        """Release focus on a target, freeing attention budget.

        Returns False if the agent was not attending to the target.
        """
        with self._lock:
            return self._release_focus_internal(agent_id, target_id, emit=True)

    def _release_focus_internal(
        self,
        agent_id: str,
        target_id: str,
        emit: bool,
    ) -> bool:
        """Internal focus release without lock acquisition."""
        state = self._focus_states.get(agent_id)
        if state is None:
            return False
        if target_id not in state.active_target_ids:
            return False
        state.active_target_ids.remove(target_id)
        active = self._agent_active_targets.get(agent_id, [])
        if target_id in active:
            active.remove(target_id)
        # Recompute used budget from the remaining active targets using
        # a simple proportional model: each remaining target consumes an
        # equal share of the total budget.
        if state.active_target_ids:
            share = state.attention_budget / max(1, len(state.active_target_ids))
            state.used_budget = min(state.attention_budget, share * len(state.active_target_ids))
        else:
            state.used_budget = 0.0
        self._stats.total_focus_released += 1
        self._stats.last_updated_at = self._now_iso()
        if emit:
            self._emit_event(
                AttentionEventKind.FOCUS_RELEASED,
                agent_id,
                {
                    "target_id": target_id,
                    "remaining_active": len(state.active_target_ids),
                },
            )
        return True

    def shift_attention(
        self,
        agent_id: str,
        to_target_id: str,
        reason: str = "",
    ) -> Optional[AttentionShift]:
        """Shift attention from the current primary target to a new target.

        Releases the previous primary focus, acquires focus on the new
        target (subject to budget availability), and records an audit
        trail entry. Returns the recorded AttentionShift or None if the
        target does not exist or budget was insufficient.
        """
        with self._lock:
            target = self._targets.get(to_target_id)
            if target is None:
                return None
            state = self._ensure_focus_state(agent_id)
            from_target_id = state.active_target_ids[0] if state.active_target_ids else ""

            # Release the current primary target if any
            if from_target_id:
                self._release_focus_internal(agent_id, from_target_id, emit=False)

            # Determine the budget cost based on the current mode
            budget_cost = self._mode_budget_cost(state.mode)
            acquired = self._acquire_focus_internal(agent_id, to_target_id, budget_cost)
            if not acquired:
                # Try with a smaller budget cost to avoid leaving the agent unfocused
                acquired = self._acquire_focus_internal(
                    agent_id, to_target_id, min(budget_cost, 0.1)
                )
            if not acquired:
                return None

            shift = AttentionShift(
                agent_id=agent_id,
                from_target_id=from_target_id,
                to_target_id=to_target_id,
                reason=reason or "manual_shift",
                mode=state.mode,
            )
            self._shifts[shift.id] = shift
            self._agent_shifts.setdefault(agent_id, [])
            self._agent_shifts[agent_id].append(shift.id)
            # Bound the per-agent shift history
            if len(self._agent_shifts[agent_id]) > self._MAX_SHIFTS_PER_AGENT:
                overflow = len(self._agent_shifts[agent_id]) - self._MAX_SHIFTS_PER_AGENT
                dropped_ids = self._agent_shifts[agent_id][:overflow]
                for dropped_id in dropped_ids:
                    self._shifts.pop(dropped_id, None)
                self._agent_shifts[agent_id] = self._agent_shifts[agent_id][overflow:]

            state.shift_count += 1
            state.last_shift_at = self._now_iso()
            self._stats.total_shifts += 1
            self._stats.last_updated_at = self._now_iso()

            self._emit_event(
                AttentionEventKind.ATTENTION_SHIFT,
                agent_id,
                {
                    "shift_id": shift.id,
                    "from_target_id": from_target_id,
                    "to_target_id": to_target_id,
                    "reason": shift.reason,
                    "mode": shift.mode.value,
                },
            )
            return shift

    def _mode_budget_cost(self, mode: AttentionMode) -> float:
        """Map an attention mode to a default focus acquisition cost."""
        if mode == AttentionMode.FOCUSED:
            return 0.6
        if mode == AttentionMode.SUSTAINED:
            return 0.5
        if mode == AttentionMode.DIVIDED:
            return 0.25
        if mode == AttentionMode.VIGILANT:
            return 0.2
        # SCANNING
        return 0.3

    # ------------------------------------------------------------------
    # Mode management
    # ------------------------------------------------------------------

    def set_mode(
        self,
        agent_id: str,
        mode: AttentionMode,
    ) -> FocusState:
        """Set the attention mode for an agent.

        The mode influences how ``tick`` decides whether to shift attention
        and how much budget each new focus acquisition consumes.
        """
        with self._lock:
            state = self._ensure_focus_state(agent_id)
            previous_mode = state.mode
            state.mode = mode
            self._emit_event(
                AttentionEventKind.MODE_CHANGED,
                agent_id,
                {
                    "previous_mode": previous_mode.value,
                    "new_mode": mode.value,
                },
            )
            return state

    def get_focus_state(self, agent_id: str) -> FocusState:
        """Get the current focus state for an agent.

        Creates a default state if the agent has not been seen before.
        """
        with self._lock:
            return self._ensure_focus_state(agent_id)

    # ------------------------------------------------------------------
    # Distraction handling
    # ------------------------------------------------------------------

    def register_distraction(
        self,
        agent_id: str,
        target_id: str,
        strength: float,
    ) -> Optional[DistractionEvent]:
        """Register a distraction event for an agent.

        The agent decides whether to resist the distraction based on the
        current attention mode, the strength of the distracting target,
        and the salience of the agent's current primary focus. A resisted
        distraction is recorded for audit; a captured distraction forces
        an attention shift to the distracting target.
        """
        with self._lock:
            target = self._targets.get(target_id)
            if target is None:
                return None
            state = self._ensure_focus_state(agent_id)
            normalized_strength = max(0.0, min(1.0, strength))

            resistance = self._compute_distraction_resistance(agent_id, state.mode)
            resisted = normalized_strength < resistance

            event = DistractionEvent(
                agent_id=agent_id,
                target_id=target_id,
                strength=normalized_strength,
                resisted=resisted,
            )
            self._distractions[event.id] = event
            self._agent_distractions.setdefault(agent_id, [])
            self._agent_distractions[agent_id].append(event.id)
            if len(self._agent_distractions[agent_id]) > self._MAX_DISTRACTIONS_PER_AGENT:
                overflow = len(self._agent_distractions[agent_id]) - self._MAX_DISTRACTIONS_PER_AGENT
                dropped_ids = self._agent_distractions[agent_id][:overflow]
                for dropped_id in dropped_ids:
                    self._distractions.pop(dropped_id, None)
                self._agent_distractions[agent_id] = self._agent_distractions[agent_id][overflow:]

            self._stats.total_distractions += 1
            if resisted:
                self._stats.total_resisted += 1
            self._stats.last_updated_at = self._now_iso()

            self._emit_event(
                AttentionEventKind.DISTRACTION,
                agent_id,
                {
                    "distraction_id": event.id,
                    "target_id": target_id,
                    "strength": normalized_strength,
                    "resisted": resisted,
                },
            )

            if not resisted:
                # The distraction captured the agent's attention
                self.shift_attention(
                    agent_id=agent_id,
                    to_target_id=target_id,
                    reason="distracted",
                )
            return event

    def _compute_distraction_resistance(
        self,
        agent_id: str,
        mode: AttentionMode,
    ) -> float:
        """Compute the agent's resistance to a distraction based on its mode.

        FOCUSED agents resist strongly; SCANNING agents resist weakly.
        The base resistance is also raised when the agent has an active
        primary target with high salience.
        """
        mode_resistance = {
            AttentionMode.FOCUSED: 0.85,
            AttentionMode.SUSTAINED: 0.75,
            AttentionMode.VIGILANT: 0.6,
            AttentionMode.DIVIDED: 0.45,
            AttentionMode.SCANNING: 0.3,
        }.get(mode, self._DISTRACTION_RESISTANCE_BASE)

        # Boost resistance based on the salience of the current primary target
        state = self._focus_states.get(agent_id)
        if state and state.active_target_ids:
            primary_id = state.active_target_ids[0]
            primary_target = self._targets.get(primary_id)
            if primary_target is not None:
                salience_bonus = primary_target.salience * 0.2
                mode_resistance = min(1.0, mode_resistance + salience_bonus)
        return mode_resistance

    # ------------------------------------------------------------------
    # Tick / attention cycle
    # ------------------------------------------------------------------

    def tick(self, agent_id: str) -> Dict[str, Any]:
        """Process one attention cycle for an agent.

        Each tick recomputes salience for all of the agent's targets
        (applying a small novelty decay), then decides whether to shift
        attention based on the current mode. Returns a summary of the
        cycle for inspection.
        """
        with self._lock:
            state = self._ensure_focus_state(agent_id)
            agent_target_ids = list(self._agent_targets.get(agent_id, []))

            # Recompute salience and apply novelty decay
            shifted_targets: List[str] = []
            for target_id in agent_target_ids:
                target = self._targets.get(target_id)
                if target is None:
                    continue
                # Apply novelty decay so repeated stimuli become less salient
                if SalienceFactor.NOVELTY.value in target.factors:
                    decayed = max(
                        0.0,
                        target.factors[SalienceFactor.NOVELTY.value] - self._NOVELTY_DECAY_PER_TICK,
                    )
                    target.factors[SalienceFactor.NOVELTY.value] = decayed
                target.salience = self._compute_salience_from_factors(
                    target.factors, target.priority
                )
                target.last_updated = self._now_iso()
                shifted_targets.append(target_id)

            # Decide whether to shift attention based on the mode
            shift_summary: Optional[Dict[str, Any]] = None
            should_shift = self._should_shift_on_tick(state, agent_target_ids)
            if should_shift:
                best_target = self._highest_salience_target(agent_id)
                if best_target is not None:
                    current_primary = state.active_target_ids[0] if state.active_target_ids else ""
                    if best_target.id != current_primary:
                        shift = self.shift_attention(
                            agent_id=agent_id,
                            to_target_id=best_target.id,
                            reason="tick_shift",
                        )
                        if shift is not None:
                            shift_summary = shift.to_dict()

            return {
                "agent_id": agent_id,
                "mode": state.mode.value,
                "targets_recomputed": len(shifted_targets),
                "active_focus": list(state.active_target_ids),
                "shift": shift_summary,
                "timestamp": self._now_iso(),
            }

    def _should_shift_on_tick(
        self,
        state: FocusState,
        agent_target_ids: List[str],
    ) -> bool:
        """Decide whether attention should shift during this tick.

        Mode-driven shift probabilities:
          - FOCUSED: very unlikely to shift unless current focus is weak
          - SUSTAINED: unlikely to shift
          - VIGILANT: occasionally shifts toward high-threat stimuli
          - DIVIDED: rotates between targets more frequently
          - SCANNING: most likely to shift to the next salient target
        """
        if not agent_target_ids:
            return False

        mode_shift_probability = {
            AttentionMode.FOCUSED: 0.1,
            AttentionMode.SUSTAINED: 0.15,
            AttentionMode.VIGILANT: 0.35,
            AttentionMode.DIVIDED: 0.5,
            AttentionMode.SCANNING: 0.6,
        }.get(state.mode, 0.3)

        # If the agent has no active focus, always try to shift
        if not state.active_target_ids:
            return True

        primary_id = state.active_target_ids[0]
        primary_target = self._targets.get(primary_id)
        if primary_target is None:
            return True

        # Find the best alternative target
        best_alternative: Optional[AttentionTarget] = None
        for target_id in agent_target_ids:
            if target_id == primary_id:
                continue
            candidate = self._targets.get(target_id)
            if candidate is None:
                continue
            if best_alternative is None or candidate.salience > best_alternative.salience:
                best_alternative = candidate

        if best_alternative is None:
            return False

        # If the alternative is substantially more salient, increase the shift probability
        salience_gap = best_alternative.salience - primary_target.salience
        if salience_gap > 0.2:
            mode_shift_probability = min(1.0, mode_shift_probability + 0.3)
        elif salience_gap < -0.2:
            mode_shift_probability = max(0.0, mode_shift_probability - 0.2)

        # Deterministic decision based on the salience gap and shift count parity
        # so that tick results are reproducible without a random source.
        threshold = 1.0 - mode_shift_probability
        score = (best_alternative.salience - primary_target.salience + 1.0) / 2.0
        return score >= threshold

    # ------------------------------------------------------------------
    # Audit trail
    # ------------------------------------------------------------------

    def get_audit_trail(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return the attention shift history for an agent.

        Each entry pairs the recorded shift with the matching focus
        state snapshot at the time of the shift.
        """
        with self._lock:
            trail: List[Dict[str, Any]] = []
            shift_ids = list(self._agent_shifts.get(agent_id, []))
            for shift_id in reversed(shift_ids[-limit:]):
                shift = self._shifts.get(shift_id)
                if shift is None:
                    continue
                trail.append(shift.to_dict())
            return trail

    def get_distractions(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[DistractionEvent]:
        """Return the distraction history for an agent, most recent first."""
        with self._lock:
            distraction_ids = list(self._agent_distractions.get(agent_id, []))
            results: List[DistractionEvent] = []
            for distraction_id in reversed(distraction_ids[-limit:]):
                distraction = self._distractions.get(distraction_id)
                if distraction is not None:
                    results.append(distraction)
            return results

    # ------------------------------------------------------------------
    # Status, snapshot, and lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine."""
        with self._lock:
            mode_distribution: Dict[str, int] = {}
            for state in self._focus_states.values():
                key = state.mode.value
                mode_distribution[key] = mode_distribution.get(key, 0) + 1

            total_active_focus = sum(
                len(state.active_target_ids) for state in self._focus_states.values()
            )

            return {
                "engine_id": id(self),
                "initialized": self._initialized,
                "total_targets": len(self._targets),
                "total_agents": len(self._focus_states),
                "total_shifts": len(self._shifts),
                "total_distractions": len(self._distractions),
                "total_active_focus": total_active_focus,
                "total_events": len(self._events),
                "total_event_handlers": sum(
                    len(handlers) for handlers in self._event_handlers.values()
                ),
                "mode_distribution": mode_distribution,
                "stats": self._stats.to_dict(),
            }

    def get_snapshot(self) -> AttentionSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            total_active_focus = sum(
                len(state.active_target_ids) for state in self._focus_states.values()
            )
            snapshot = AttentionSnapshot(
                agent_count=len(self._focus_states),
                total_targets=len(self._targets),
                total_active_focus=total_active_focus,
                stats=AttentionStats(
                    total_targets_registered=self._stats.total_targets_registered,
                    total_targets_removed=self._stats.total_targets_removed,
                    total_focus_acquired=self._stats.total_focus_acquired,
                    total_focus_released=self._stats.total_focus_released,
                    total_shifts=self._stats.total_shifts,
                    total_distractions=self._stats.total_distractions,
                    total_resisted=self._stats.total_resisted,
                    last_updated_at=self._stats.last_updated_at,
                ),
            )
            return snapshot

    def reset(self) -> None:
        """Reset the engine to its initial seeded state."""
        with self._lock:
            self._targets.clear()
            self._focus_states.clear()
            self._shifts.clear()
            self._distractions.clear()
            self._agent_targets.clear()
            self._agent_active_targets.clear()
            self._agent_shifts.clear()
            self._agent_distractions.clear()
            self._events.clear()
            self._event_handlers.clear()
            self._stats = AttentionStats()
            self._seed_default_data()


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------


def get_attention_allocator() -> AttentionAllocatorEngine:
    """Get or create the global AttentionAllocatorEngine singleton."""
    return AttentionAllocatorEngine.get_instance()
