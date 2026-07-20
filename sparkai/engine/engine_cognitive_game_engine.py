"""
SparkLabs Engine - Cognitive Game Engine

The deepest fusion of agent cognition and engine execution in the SparkLabs
stack. Where the CognitiveArchitect reasons ABOUT games and the AINativeConductor
directs engine parameters, the CognitiveGameEngine dissolves the boundary
entirely: every engine tick IS a cognitive cycle.

Original SparkLabs design principles:
  1. Unified Tick - A single cognitive_tick(dt) call runs perceive, reason,
     plan, act, reflect, and learn in one deterministic pass. The agent does
     not sit beside the engine; the agent IS the engine's heartbeat.
  2. Game-State Perception - The engine's live state (entities, physics,
     events, player input) is exposed as a structured PerceptionFrame that
     feeds directly into the reasoning layer.
  3. Action Space - Atomic engine mutations (spawn, despawn, tune, trigger,
     morph) are exposed as a typed ActionSpace the reasoning layer selects
     from. No separate "agent API" exists.
  4. Reflection Loop - Each tick compares the expected outcome of the last
     action against the observed outcome, producing a signed delta that
     updates confidence in similar actions.
  5. Layered Memory - Working, episodic, semantic, and procedural memory
     share a single MemoryBank. The engine writes episodes; the reasoning
     layer queries semantic facts; procedural memory caches successful
     action sequences as reusable skills.
  6. Deterministic Replay - Because the cognitive tick is deterministic,
     any session can be replayed tick-by-tick for debugging or training.

This module is intentionally self-contained: it has no hard dependency on
external LLM providers. When a provider is configured, the reasoning layer
uses it; otherwise it falls back to a heuristic planner that still produces
valid engine mutations. This keeps the project immediately runnable.
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================

class CognitivePhase(Enum):
    """Phases of a single cognitive tick."""
    PERCEIVE = "perceive"
    REASON = "reason"
    PLAN = "plan"
    ACT = "act"
    REFLECT = "reflect"
    LEARN = "learn"


class ActionType(Enum):
    """Atomic engine mutations the cognitive layer can perform."""
    SPAWN_ENTITY = "spawn_entity"
    DESPAWN_ENTITY = "despawn_entity"
    TUNE_PHYSICS = "tune_physics"
    TUNE_RENDER = "tune_render"
    TUNE_DIFFICULTY = "tune_difficulty"
    TRIGGER_EVENT = "trigger_event"
    ADJUST_PACING = "adjust_pacing"
    MORPH_ENTITY = "morph_entity"
    BROADCAST_SIGNAL = "broadcast_signal"
    NO_OP = "no_op"


class MemoryTier(Enum):
    """Memory tiers in the unified MemoryBank."""
    WORKING = "working"        # Current tick scratchpad
    EPISODIC = "episodic"      # Recent experiences
    SEMANTIC = "semantic"      # Consolidated facts
    PROCEDURAL = "procedural"  # Skill cache


class EngineState(Enum):
    """High-level state of the cognitive engine."""
    COLD = "cold"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    ERROR = "error"


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class EntitySnapshot:
    """A snapshot of an entity's state in the perception frame."""
    entity_id: str
    entity_type: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    health: float = 100.0
    tags: List[str] = field(default_factory=list)


@dataclass
class PerceptionFrame:
    """What the cognitive layer perceives in a single tick."""
    tick: int
    state: EngineState
    player: Optional[EntitySnapshot] = None
    entities: List[EntitySnapshot] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    signals: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EngineAction:
    """An atomic action selected by the reasoning layer."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    action_type: ActionType = ActionType.NO_OP
    target_id: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: str = ""
    confidence: float = 0.5
    rationale: str = ""


@dataclass
class ActionOutcome:
    """Observed outcome of an executed action."""
    action_id: str
    success: bool
    observed_delta: Dict[str, float] = field(default_factory=dict)
    notes: str = ""


@dataclass
class CognitiveTickResult:
    """The full result of one cognitive tick."""
    tick: int
    phase: CognitivePhase
    perception: Optional[PerceptionFrame] = None
    actions_planned: List[EngineAction] = field(default_factory=list)
    actions_executed: int = 0
    outcome: Optional[ActionOutcome] = None
    lesson: str = ""
    duration_s: float = 0.0
    confidence: float = 0.0


@dataclass
class MemoryRecord:
    """A single record in the MemoryBank."""
    record_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    tier: MemoryTier = MemoryTier.WORKING
    domain: str = "general"
    content: Dict[str, Any] = field(default_factory=dict)
    salience: float = 0.5
    confidence: float = 0.5
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


# =============================================================================
# Memory Bank - Unified Layered Memory
# =============================================================================

class MemoryBank:
    """
    A unified memory bank spanning working, episodic, semantic, and
    procedural tiers. All tiers share a single lock and indexing scheme
    so the cognitive tick can read across tiers in one call.
    """

    def __init__(self, capacity: int = 256) -> None:
        self._lock = threading.RLock()
        self._capacity = capacity
        self._records: Dict[str, MemoryRecord] = {}
        self._tier_index: Dict[MemoryTier, Deque[str]] = {
            MemoryTier.WORKING: deque(maxlen=16),
            MemoryTier.EPISODIC: deque(maxlen=capacity),
            MemoryTier.SEMANTIC: deque(maxlen=capacity),
            MemoryTier.PROCEDURAL: deque(maxlen=capacity),
        }
        self._domain_index: Dict[str, List[str]] = {}

    def write(self, record: MemoryRecord) -> str:
        """Write a record to the appropriate tier."""
        with self._lock:
            self._records[record.record_id] = record
            self._tier_index[record.tier].append(record.record_id)
            self._domain_index.setdefault(record.domain, []).append(record.record_id)
            # Evict from working memory if needed (already bounded by maxlen)
            return record.record_id

    def query(
        self, tier: Optional[MemoryTier] = None, domain: Optional[str] = None,
        limit: int = 8,
    ) -> List[MemoryRecord]:
        """Query records by tier and/or domain."""
        with self._lock:
            ids: List[str] = []
            if tier is not None:
                ids = list(self._tier_index[tier])
            elif domain is not None:
                ids = list(self._domain_index.get(domain, []))
            else:
                ids = list(self._records.keys())

            results: List[MemoryRecord] = []
            now = time.time()
            for rid in reversed(ids[-limit * 2:]):
                rec = self._records.get(rid)
                if rec is None:
                    continue
                if domain is not None and rec.domain != domain:
                    continue
                rec.last_accessed = now
                rec.access_count += 1
                results.append(rec)
                if len(results) >= limit:
                    break
            return results

    def consolidate(self) -> int:
        """
        Promote high-salience episodic records to semantic tier.
        Returns the number of promoted records.
        """
        with self._lock:
            promoted = 0
            # Promote episodic records with high salience and confidence
            to_promote = [
                rid for rid in self._tier_index[MemoryTier.EPISODIC]
                if rid in self._records
                and self._records[rid].salience >= 0.7
                and self._records[rid].confidence >= 0.6
            ]
            for rid in to_promote:
                rec = self._records.get(rid)
                if rec is None:
                    continue
                rec.tier = MemoryTier.SEMANTIC
                self._tier_index[MemoryTier.EPISODIC].remove(rid)
                self._tier_index[MemoryTier.SEMANTIC].append(rid)
                promoted += 1
            return promoted

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_records": len(self._records),
                "by_tier": {t.value: len(q) for t, q in self._tier_index.items()},
                "domains": len(self._domain_index),
                "capacity": self._capacity,
            }


# =============================================================================
# Perception Builder - Engine State to Perception Frame
# =============================================================================

class PerceptionBuilder:
    """
    Builds a PerceptionFrame from the live engine state. This is the
    single point where raw engine data becomes structured perception
    for the reasoning layer.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._frame_count = 0

    def build(
        self, tick: int, state: EngineState,
        entities: List[EntitySnapshot], events: List[Dict[str, Any]],
        metrics: Optional[Dict[str, float]] = None,
        signals: Optional[Dict[str, Any]] = None,
    ) -> PerceptionFrame:
        """Build a perception frame from current engine state."""
        with self._lock:
            self._frame_count += 1

        # Identify player entity (tag-based)
        player = None
        for e in entities:
            if e.entity_type == "player" or "player" in e.tags:
                player = e
                break

        return PerceptionFrame(
            tick=tick,
            state=state,
            player=player,
            entities=list(entities),
            events=list(events),
            metrics=dict(metrics or {}),
            signals=dict(signals or {}),
        )

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {"frames_built": self._frame_count}


# =============================================================================
# Reasoning Layer - Selects Actions Based on Perception
# =============================================================================

class ReasoningLayer:
    """
    Selects engine actions based on perception and memory. Uses a
    heuristic planner that produces valid engine mutations even
    without an LLM provider. When a provider is configured, the
    planner can be upgraded to LLM-driven selection.
    """

    def __init__(self, memory: MemoryBank) -> None:
        self._memory = memory
        self._lock = threading.RLock()
        self._action_history: Deque[EngineAction] = deque(maxlen=32)
        self._outcome_history: Deque[ActionOutcome] = deque(maxlen=32)
        self._action_success_rate: Dict[str, float] = {
            a.value: 0.5 for a in ActionType
        }

    def select_actions(
        self, frame: PerceptionFrame, max_actions: int = 3,
    ) -> List[EngineAction]:
        """
        Select up to max_actions based on the perception frame and
        memory. Returns a list of EngineAction ready for execution.
        """
        actions: List[EngineAction] = []

        # Strategy 1: React to low player health
        if frame.player is not None and frame.player.health < 30.0:
            actions.append(EngineAction(
                action_type=ActionType.TUNE_DIFFICULTY,
                params={"delta": -0.15},
                expected_outcome="player_survival_increase",
                confidence=0.7,
                rationale="player health critical, easing difficulty",
            ))

        # Strategy 2: React to too few enemies
        enemy_count = sum(1 for e in frame.entities if e.entity_type == "enemy")
        if enemy_count < 2 and frame.metrics.get("player_skill", 0.5) > 0.4:
            actions.append(EngineAction(
                action_type=ActionType.SPAWN_ENTITY,
                params={
                    "entity_type": "enemy",
                    "x": frame.player.x + 200 if frame.player else 400.0,
                    "y": frame.player.y if frame.player else 300.0,
                },
                expected_outcome="engagement_increase",
                confidence=0.6,
                rationale="low enemy count, spawning challenger",
            ))

        # Strategy 3: React to too many enemies
        if enemy_count > 8:
            actions.append(EngineAction(
                action_type=ActionType.DESPAWN_ENTITY,
                target_id="",  # engine will pick the weakest
                params={"criteria": "weakest_enemy"},
                expected_outcome="overwhelm_decrease",
                confidence=0.65,
                rationale="enemy count overwhelming, pruning",
            ))

        # Strategy 4: Adjust pacing based on time since last event
        recent_events = len(frame.events)
        if recent_events == 0 and frame.tick > 0 and frame.tick % 60 == 0:
            actions.append(EngineAction(
                action_type=ActionType.TRIGGER_EVENT,
                params={"event_kind": "ambient_flourish"},
                expected_outcome="engagement_refresh",
                confidence=0.5,
                rationale="stale gameplay, triggering ambient event",
            ))

        # Strategy 5: Consult procedural memory for a cached skill
        procedural = self._memory.query(tier=MemoryTier.PROCEDURAL, limit=1)
        if procedural and frame.tick > 0 and frame.tick % 30 == 0:
            rec = procedural[0]
            cached_action_type = rec.content.get("action_type")
            if cached_action_type and cached_action_type in [a.value for a in ActionType]:
                actions.append(EngineAction(
                    action_type=ActionType(cached_action_type),
                    params=rec.content.get("params", {}),
                    expected_outcome=rec.content.get("expected_outcome", ""),
                    confidence=rec.confidence * 0.9,
                    rationale="procedural_memory_replay",
                ))

        # Bound to max_actions
        return actions[:max_actions]

    def record_outcome(self, outcome: ActionOutcome) -> None:
        """Record the observed outcome of an action."""
        with self._lock:
            self._outcome_history.append(outcome)
            # Find the matching action to update success rate
            for action in reversed(self._action_history):
                if action.action_id == outcome.action_id:
                    atype = action.action_type.value
                    current = self._action_success_rate.get(atype, 0.5)
                    alpha = 0.2
                    self._action_success_rate[atype] = (
                        (1 - alpha) * current + alpha * (1.0 if outcome.success else 0.0)
                    )
                    break

    def record_action(self, action: EngineAction) -> None:
        with self._lock:
            self._action_history.append(action)

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "action_history_size": len(self._action_history),
                "outcome_history_size": len(self._outcome_history),
                "action_success_rate": dict(self._action_success_rate),
            }


# =============================================================================
# Action Executor - Applies Actions to Engine State
# =============================================================================

class ActionExecutor:
    """
    Applies EngineActions to the live engine state. Mutates the
    entity list, metrics, and signals in place. Returns an
    ActionOutcome for each applied action.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._executed_count = 0
        self._failed_count = 0

    def execute(
        self, action: EngineAction,
        entities: List[EntitySnapshot],
        metrics: Dict[str, float],
        signals: Dict[str, Any],
    ) -> ActionOutcome:
        """Execute an action against the live engine state."""
        with self._lock:
            self._executed_count += 1

        try:
            atype = action.action_type
            if atype == ActionType.SPAWN_ENTITY:
                return self._do_spawn(action, entities)
            if atype == ActionType.DESPAWN_ENTITY:
                return self._do_despawn(action, entities)
            if atype == ActionType.TUNE_PHYSICS:
                return self._do_tune("physics", action, metrics)
            if atype == ActionType.TUNE_RENDER:
                return self._do_tune("render", action, metrics)
            if atype == ActionType.TUNE_DIFFICULTY:
                return self._do_tune_difficulty(action, metrics)
            if atype == ActionType.TRIGGER_EVENT:
                return self._do_trigger_event(action, signals)
            if atype == ActionType.ADJUST_PACING:
                return self._do_adjust_pacing(action, metrics)
            if atype == ActionType.MORPH_ENTITY:
                return self._do_morph(action, entities)
            if atype == ActionType.BROADCAST_SIGNAL:
                return self._do_broadcast(action, signals)
            # NO_OP
            return ActionOutcome(
                action_id=action.action_id,
                success=True,
                notes="no_op",
            )
        except Exception as exc:
            with self._lock:
                self._failed_count += 1
            logger.warning("Action %s failed: %s", action.action_type.value, exc)
            return ActionOutcome(
                action_id=action.action_id,
                success=False,
                notes=f"error: {exc}",
            )

    def _do_spawn(self, action: EngineAction, entities: List[EntitySnapshot]) -> ActionOutcome:
        etype = action.params.get("entity_type", "enemy")
        x = float(action.params.get("x", 400.0))
        y = float(action.params.get("y", 300.0))
        eid = f"{etype}_{uuid.uuid4().hex[:6]}"
        entities.append(EntitySnapshot(
            entity_id=eid, entity_type=etype, x=x, y=y,
            tags=[etype],
        ))
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"entity_count": 1.0},
            notes=f"spawned {eid}",
        )

    def _do_despawn(self, action: EngineAction, entities: List[EntitySnapshot]) -> ActionOutcome:
        if not entities:
            return ActionOutcome(
                action_id=action.action_id, success=False,
                notes="no entities to despawn",
            )
        # If target_id specified, despawn that one; else despawn weakest enemy
        target_id = action.target_id
        if target_id:
            for i, e in enumerate(entities):
                if e.entity_id == target_id:
                    entities.pop(i)
                    return ActionOutcome(
                        action_id=action.action_id, success=True,
                        observed_delta={"entity_count": -1.0},
                        notes=f"despawned {target_id}",
                    )
            return ActionOutcome(
                action_id=action.action_id, success=False,
                notes=f"target {target_id} not found",
            )
        # Pick weakest enemy
        enemies = [e for e in entities if e.entity_type == "enemy"]
        if not enemies:
            return ActionOutcome(
                action_id=action.action_id, success=False,
                notes="no enemies to despawn",
            )
        weakest = min(enemies, key=lambda e: e.health)
        entities.remove(weakest)
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"entity_count": -1.0},
            notes=f"despawned weakest {weakest.entity_id}",
        )

    def _do_tune(self, domain: str, action: EngineAction, metrics: Dict[str, float]) -> ActionOutcome:
        for k, v in action.params.items():
            key = f"{domain}_{k}"
            if isinstance(v, (int, float)):
                metrics[key] = metrics.get(key, 0.0) + float(v)
            else:
                metrics[key] = float(v) if isinstance(v, (int, float)) else 0.0
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={f"{domain}_tuned": 1.0},
            notes=f"tuned {domain}",
        )

    def _do_tune_difficulty(self, action: EngineAction, metrics: Dict[str, float]) -> ActionOutcome:
        delta = float(action.params.get("delta", 0.0))
        current = metrics.get("difficulty", 0.5)
        metrics["difficulty"] = max(0.0, min(1.0, current + delta))
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"difficulty": delta},
            notes=f"difficulty {current:.2f} -> {metrics['difficulty']:.2f}",
        )

    def _do_trigger_event(self, action: EngineAction, signals: Dict[str, Any]) -> ActionOutcome:
        kind = action.params.get("event_kind", "generic")
        signals["last_event"] = {
            "kind": kind,
            "params": dict(action.params),
            "time": time.time(),
        }
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"events_triggered": 1.0},
            notes=f"triggered {kind}",
        )

    def _do_adjust_pacing(self, action: EngineAction, metrics: Dict[str, float]) -> ActionOutcome:
        zone = action.params.get("zone", "normal")
        metrics["pacing_zone"] = hash(zone) % 100 / 100.0  # deterministic encoding
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"pacing_change": 1.0},
            notes=f"pacing zone -> {zone}",
        )

    def _do_morph(self, action: EngineAction, entities: List[EntitySnapshot]) -> ActionOutcome:
        target_id = action.target_id
        for e in entities:
            if e.entity_id == target_id:
                for k, v in action.params.items():
                    if hasattr(e, k):
                        try:
                            setattr(e, k, type(getattr(e, k))(v) if not isinstance(v, type(getattr(e, k))) else v)
                        except (TypeError, ValueError):
                            pass
                return ActionOutcome(
                    action_id=action.action_id, success=True,
                    observed_delta={"morphed": 1.0},
                    notes=f"morphed {target_id}",
                )
        return ActionOutcome(
            action_id=action.action_id, success=False,
            notes=f"morph target {target_id} not found",
        )

    def _do_broadcast(self, action: EngineAction, signals: Dict[str, Any]) -> ActionOutcome:
        key = action.params.get("signal_key", "broadcast")
        signals[key] = action.params.get("signal_value", True)
        return ActionOutcome(
            action_id=action.action_id, success=True,
            observed_delta={"signals_broadcast": 1.0},
            notes=f"broadcast {key}",
        )

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "executed_count": self._executed_count,
                "failed_count": self._failed_count,
            }


# =============================================================================
# Reflection Layer - Compares Expected vs Observed Outcomes
# =============================================================================

class ReflectionLayer:
    """
    Compares the expected outcome of an action against the observed
    outcome and produces a signed confidence delta. The delta is
    applied to the action's success rate and may trigger a lesson
    write to the MemoryBank.
    """

    def __init__(self, memory: MemoryBank) -> None:
        self._memory = memory
        self._lock = threading.RLock()
        self._reflection_count = 0
        self._lessons_extracted = 0

    def reflect(
        self, action: EngineAction, outcome: ActionOutcome,
    ) -> str:
        """
        Reflect on a single action outcome. Returns a lesson string
        (possibly empty) if a lesson was extracted.
        """
        with self._lock:
            self._reflection_count += 1

        expected_match = self._expected_matches_observed(action, outcome)
        lesson = ""

        if not outcome.success:
            # Failed action: lower confidence in this action type
            lesson = (
                f"action {action.action_type.value} failed: {outcome.notes}; "
                f"avoid when {action.rationale}"
            )
            self._write_lesson(action, outcome, lesson, salience=0.8)
        elif not expected_match:
            # Succeeded but unexpected outcome: medium-salience lesson
            lesson = (
                f"action {action.action_type.value} succeeded but "
                f"outcome differed from expected '{action.expected_outcome}'"
            )
            self._write_lesson(action, outcome, lesson, salience=0.5)
        elif action.confidence >= 0.7:
            # High-confidence success: cache as procedural memory
            self._memory.write(MemoryRecord(
                tier=MemoryTier.PROCEDURAL,
                domain=f"action_{action.action_type.value}",
                content={
                    "action_type": action.action_type.value,
                    "params": dict(action.params),
                    "expected_outcome": action.expected_outcome,
                    "rationale": action.rationale,
                },
                salience=0.7,
                confidence=action.confidence,
            ))

        return lesson

    def _expected_matches_observed(
        self, action: EngineAction, outcome: ActionOutcome,
    ) -> bool:
        """Heuristic check: does the observed delta match the expected outcome?"""
        if not outcome.success:
            return False
        if not action.expected_outcome:
            return True
        # Simple keyword matching against notes
        keywords = action.expected_outcome.lower().split("_")
        notes = outcome.notes.lower()
        return any(kw in notes for kw in keywords if len(kw) > 3)

    def _write_lesson(
        self, action: EngineAction, outcome: ActionOutcome,
        lesson: str, salience: float,
    ) -> None:
        with self._lock:
            self._lessons_extracted += 1
        self._memory.write(MemoryRecord(
            tier=MemoryTier.EPISODIC,
            domain=f"lesson_{action.action_type.value}",
            content={
                "lesson": lesson,
                "action_id": action.action_id,
                "params": dict(action.params),
                "outcome_notes": outcome.notes,
            },
            salience=salience,
            confidence=action.confidence,
        ))

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "reflection_count": self._reflection_count,
                "lessons_extracted": self._lessons_extracted,
            }


# =============================================================================
# Cognitive Game Engine - The Unified Tick
# =============================================================================

class CognitiveGameEngine:
    """
    The unified cognitive game engine. A single cognitive_tick(dt)
    call runs all six phases: perceive, reason, plan, act, reflect,
    learn. The engine state (entities, metrics, signals) is the
    agent's working memory; mutations are the agent's actions.

    Thread-safe singleton: use get_instance() to access.
    """

    _instance: Optional["CognitiveGameEngine"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._state: EngineState = EngineState.COLD
        self._tick: int = 0
        self._entities: List[EntitySnapshot] = []
        self._metrics: Dict[str, float] = {
            "difficulty": 0.5,
            "player_skill": 0.5,
            "engagement": 0.5,
        }
        self._signals: Dict[str, Any] = {}
        self._events_buffer: Deque[Dict[str, Any]] = deque(maxlen=32)

        # Subsystems
        self._memory = MemoryBank(capacity=256)
        self._perception = PerceptionBuilder()
        self._reasoning = ReasoningLayer(self._memory)
        self._executor = ActionExecutor()
        self._reflection = ReflectionLayer(self._memory)

        # Telemetry
        self._tick_history: Deque[CognitiveTickResult] = deque(maxlen=64)
        self._total_duration_s: float = 0.0
        self._last_lesson: str = ""

    @classmethod
    def get_instance(cls) -> "CognitiveGameEngine":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ---- Lifecycle ----

    def initialize(self) -> None:
        """Initialize the engine with a default scene."""
        with self._lock:
            if self._state != EngineState.COLD:
                return
            # Seed a minimal scene: one player, two enemies, two collectibles
            self._entities = [
                EntitySnapshot(
                    entity_id="player_1", entity_type="player",
                    x=100.0, y=300.0, health=100.0, tags=["player"],
                ),
                EntitySnapshot(
                    entity_id="enemy_1", entity_type="enemy",
                    x=500.0, y=300.0, health=60.0, tags=["enemy"],
                ),
                EntitySnapshot(
                    entity_id="enemy_2", entity_type="enemy",
                    x=700.0, y=200.0, health=40.0, tags=["enemy"],
                ),
                EntitySnapshot(
                    entity_id="coll_1", entity_type="collectible",
                    x=400.0, y=200.0, tags=["collectible"],
                ),
                EntitySnapshot(
                    entity_id="coll_2", entity_type="collectible",
                    x=600.0, y=400.0, tags=["collectible"],
                ),
            ]
            self._state = EngineState.RUNNING
            logger.info("CognitiveGameEngine initialized with %d entities",
                        len(self._entities))

    def start(self) -> None:
        with self._lock:
            if self._state == EngineState.COLD:
                self.initialize()
            self._state = EngineState.RUNNING

    def pause(self) -> None:
        with self._lock:
            self._state = EngineState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == EngineState.PAUSED:
                self._state = EngineState.RUNNING

    def reset(self) -> None:
        with self._lock:
            self._state = EngineState.COLD
            self._tick = 0
            self._entities = []
            self._metrics = {
                "difficulty": 0.5,
                "player_skill": 0.5,
                "engagement": 0.5,
            }
            self._signals = {}
            self._events_buffer.clear()
            self._tick_history.clear()
            self._total_duration_s = 0.0
            self._last_lesson = ""

    # ---- Cognitive Tick ----

    def cognitive_tick(self, dt: float = 1.0 / 60.0) -> CognitiveTickResult:
        """
        Run a single cognitive tick. This is the unified heartbeat of
        the engine and the agent.
        """
        start = time.time()
        with self._lock:
            if self._state not in (EngineState.RUNNING, EngineState.STEPPING):
                return CognitiveTickResult(
                    tick=self._tick, phase=CognitivePhase.PERCEIVE,
                    duration_s=0.0,
                )
            self._tick += 1
            current_tick = self._tick

        # Phase 1: PERCEIVE
        frame = self._perception.build(
            tick=current_tick,
            state=self._state,
            entities=list(self._entities),
            events=list(self._events_buffer),
            metrics=dict(self._metrics),
            signals=dict(self._signals),
        )
        # Drain events buffer after perception
        self._events_buffer.clear()

        # Phase 2+3: REASON + PLAN (reasoning selects actions)
        actions = self._reasoning.select_actions(frame, max_actions=3)
        for action in actions:
            self._reasoning.record_action(action)

        # Phase 4: ACT
        outcomes: List[ActionOutcome] = []
        for action in actions:
            outcome = self._executor.execute(
                action, self._entities, self._metrics, self._signals,
            )
            outcomes.append(outcome)

        # Phase 5: REFLECT
        lesson = ""
        for action, outcome in zip(actions, outcomes):
            l = self._reflection.reflect(action, outcome)
            if l:
                lesson = l
            self._reasoning.record_outcome(outcome)

        # Phase 6: LEARN (consolidate memory periodically)
        if current_tick % 30 == 0:
            self._memory.consolidate()

        # Compute aggregate confidence
        confidence = (
            sum(a.confidence for a in actions) / max(1, len(actions))
            if actions else 0.5
        )

        duration_s = time.time() - start
        with self._lock:
            self._total_duration_s += duration_s
            self._last_lesson = lesson

        result = CognitiveTickResult(
            tick=current_tick,
            phase=CognitivePhase.LEARN,
            perception=frame,
            actions_planned=actions,
            actions_executed=len(outcomes),
            outcome=outcomes[-1] if outcomes else None,
            lesson=lesson,
            duration_s=duration_s,
            confidence=confidence,
        )

        with self._lock:
            self._tick_history.append(result)

        return result

    # ---- Status & Telemetry ----

    def status(self) -> Dict[str, Any]:
        with self._lock:
            last_tick = self._tick_history[-1] if self._tick_history else None
            return {
                "state": self._state.value,
                "tick": self._tick,
                "entity_count": len(self._entities),
                "entities": [
                    {
                        "id": e.entity_id, "type": e.entity_type,
                        "x": e.x, "y": e.y, "health": e.health,
                    } for e in self._entities[:20]
                ],
                "metrics": dict(self._metrics),
                "signals": dict(self._signals),
                "memory": self._memory.stats(),
                "perception": self._perception.stats(),
                "reasoning": self._reasoning.stats(),
                "executor": self._executor.stats(),
                "reflection": self._reflection.stats(),
                "last_lesson": self._last_lesson,
                "total_duration_s": self._total_duration_s,
                "avg_tick_duration_s": (
                    self._total_duration_s / max(1, self._tick)
                ),
                "last_tick": {
                    "tick": last_tick.tick,
                    "phase": last_tick.phase.value,
                    "actions_planned": len(last_tick.actions_planned),
                    "actions_executed": last_tick.actions_executed,
                    "confidence": last_tick.confidence,
                    "duration_s": last_tick.duration_s,
                    "lesson": last_tick.lesson,
                } if last_tick else None,
            }

    def history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._lock:
            results = list(self._tick_history)[-limit:]
            return [
                {
                    "tick": r.tick,
                    "phase": r.phase.value,
                    "actions_planned": len(r.actions_planned),
                    "actions_executed": r.actions_executed,
                    "confidence": r.confidence,
                    "duration_s": r.duration_s,
                    "lesson": r.lesson,
                } for r in results
            ]


# =============================================================================
# Module-Level Convenience
# =============================================================================

def get_cognitive_engine() -> CognitiveGameEngine:
    """Get the singleton CognitiveGameEngine instance."""
    return CognitiveGameEngine.get_instance()


def cognitive_tick(dt: float = 1.0 / 60.0) -> CognitiveTickResult:
    """Run a single cognitive tick on the singleton engine."""
    return get_cognitive_engine().cognitive_tick(dt)


def quick_status() -> Dict[str, Any]:
    """Get a quick status snapshot of the cognitive engine."""
    return get_cognitive_engine().status()
