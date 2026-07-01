"""
SparkLabs Agent - Memory Consolidation & Dream System

Offline memory consolidation engine that processes short-term episodic
memories into stabilized long-term memories, mirroring how the human
brain consolidates experience during sleep. The system replays,
integrates, and prunes memory fragments, and additionally generates
"dream" sequences that creatively recombine memory fragments to
discover novel associations and strengthen important memory pathways.

Architecture:
  MemoryConsolidatorEngine (thread-safe singleton)
    |-- MemoryFragment       (atomic memory unit with salience & strength)
    |-- ConsolidationTask    (offline consolidation work item)
    |-- ReplaySession        (ordered re-retrieval of fragments)
    |-- DreamSequence        (creatively recombined memory narrative)
    |-- SleepCycle           (a single sleep stage execution window)
    |-- Event System         (consolidation lifecycle notifications)
    |-- Forgetting Curve     (Ebbinghaus-style retention modeling)

Consolidation Lifecycle:
  1. register_fragment      - ingest a short-term episodic memory
  2. start_consolidation    - schedule a consolidation task (encode/stabilize/...)
  3. complete_consolidation - finalize a task with a result summary
  4. start_replay           - replay fragments to reinforce pathways
  5. complete_replay        - apply strengthening from a replay session
  6. integrate_fragments    - merge several fragments into a single one
  7. prune_fragment         - retire a low-strength fragment
  8. generate_dream         - recombine fragments into a dream sequence
  9. start_sleep_cycle      - open a sleep stage window
 10. complete_sleep_cycle   - close a sleep stage window

Sleep stages loosely mirror human sleep:
  LIGHT - light encoding & stabilization
  DEEP  - slow-wave stabilization & integration
  REM   - dreaming and associative replay
  AWAKE - active retrieval & pruning

Usage:
    engine = get_memory_consolidator()
    frag = engine.register_fragment(
        agent_id="agent_alpha",
        memory_type=MemoryType.EPISODIC,
        content="Discovered a shortcut through the canyon",
        salience=0.8,
        emotional_weight=0.3,
    )
    task = engine.start_consolidation(
        agent_id="agent_alpha",
        fragment_ids=[frag.id],
        phase=ConsolidationPhase.STABILIZE,
    )
    engine.complete_consolidation(task.id, result_summary="Stabilized 1 fragment")
    dream = engine.generate_dream("agent_alpha", [frag.id])
"""

from __future__ import annotations

import datetime
import math
import random
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.datetime.utcnow().isoformat()


def _parse_iso(value: str) -> Optional[datetime.datetime]:
    """Best-effort parse of an ISO-8601 timestamp string."""
    if not value:
        return None
    try:
        return datetime.datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SleepStage(Enum):
    """Sleep stage mirrors human sleep architecture."""
    LIGHT = "light"
    DEEP = "deep"
    REM = "rem"
    AWAKE = "awake"


class ConsolidationPhase(Enum):
    """Phase of a consolidation task in the offline pipeline."""
    ENCODE = "encode"
    STABILIZE = "stabilize"
    INTEGRATE = "integrate"
    PRUNE = "prune"
    REPLAY = "replay"
    DREAM = "dream"


class MemoryType(Enum):
    """Taxonomy of memory fragment kinds."""
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"
    EMOTIONAL = "emotional"
    SPATIAL = "spatial"


class ReplayStrategy(Enum):
    """Strategy used to order fragments during a replay session."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    PRIORITIZED = "prioritized"
    SPATIOTEMPORAL = "spatiotemporal"


class ConsolidationStatus(Enum):
    """Lifecycle status of a consolidation task."""
    PENDING = "pending"
    PROCESSING = "processing"
    CONSOLIDATED = "consolidated"
    INTEGRATED = "integrated"
    PRUNED = "pruned"
    ARCHIVED = "archived"


class MemoryEventKind(Enum):
    """Kinds of events emitted by the consolidation engine."""
    CONSOLIDATION_STARTED = "consolidation_started"
    CONSOLIDATION_COMPLETED = "consolidation_completed"
    MEMORY_STRENGTHENED = "memory_strengthened"
    MEMORY_INTEGRATED = "memory_integrated"
    MEMORY_PRUNED = "memory_pruned"
    DREAM_GENERATED = "dream_generated"
    REPLAY_COMPLETED = "replay_completed"
    SLEEP_CYCLE_STARTED = "sleep_cycle_started"
    SLEEP_CYCLE_COMPLETED = "sleep_cycle_completed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class MemoryFragment:
    """An atomic memory unit with salience, emotion, and a strength score.

    Salience drives replay prioritization, emotional weight biases which
    memories survive pruning, and strength is the stabilized long-term
    retention score that decays over time per the Ebbinghaus curve.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    memory_type: MemoryType = MemoryType.EPISODIC
    content: str = ""
    salience: float = 0.5
    emotional_weight: float = 0.0
    timestamp: str = field(default_factory=_now_iso)
    access_count: int = 0
    last_accessed: str = field(default_factory=_now_iso)
    strength: float = 0.5
    source_fragments: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type.value,
            "content": self.content,
            "salience": self.salience,
            "emotional_weight": self.emotional_weight,
            "timestamp": self.timestamp,
            "access_count": self.access_count,
            "last_accessed": self.last_accessed,
            "strength": self.strength,
            "source_fragments": list(self.source_fragments),
            "metadata": dict(self.metadata),
        }


@dataclass
class ConsolidationTask:
    """A single offline consolidation work item spanning one phase."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    phase: ConsolidationPhase = ConsolidationPhase.STABILIZE
    fragment_ids: List[str] = field(default_factory=list)
    status: ConsolidationStatus = ConsolidationStatus.PENDING
    started_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    result_summary: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "phase": self.phase.value,
            "fragment_ids": list(self.fragment_ids),
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "result_summary": self.result_summary,
        }


@dataclass
class DreamSequence:
    """A creatively recombined memory narrative generated during REM sleep."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    fragment_ids: List[str] = field(default_factory=list)
    narrative: str = ""
    novelty_score: float = 0.0
    coherence_score: float = 0.0
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "fragment_ids": list(self.fragment_ids),
            "narrative": self.narrative,
            "novelty_score": self.novelty_score,
            "coherence_score": self.coherence_score,
            "created_at": self.created_at,
        }


@dataclass
class ReplaySession:
    """An ordered re-retrieval of fragments that strengthens their pathways."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    strategy: ReplayStrategy = ReplayStrategy.SEQUENTIAL
    fragment_ids: List[str] = field(default_factory=list)
    order: List[int] = field(default_factory=list)
    started_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    strengthening_applied: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "strategy": self.strategy.value,
            "fragment_ids": list(self.fragment_ids),
            "order": list(self.order),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "strengthening_applied": dict(self.strengthening_applied),
        }


@dataclass
class SleepCycle:
    """A single sleep stage execution window for an agent."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    stage: SleepStage = SleepStage.LIGHT
    started_at: str = field(default_factory=_now_iso)
    completed_at: str = ""
    duration_seconds: float = 0.0
    fragments_processed: int = 0
    dreams_generated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "stage": self.stage.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "fragments_processed": self.fragments_processed,
            "dreams_generated": self.dreams_generated,
        }


@dataclass
class ConsolidationStats:
    """Aggregate statistics for the consolidation engine."""
    total_fragments: int = 0
    total_consolidated: int = 0
    total_integrated: int = 0
    total_pruned: int = 0
    total_dreams: int = 0
    total_replays: int = 0
    total_sleep_cycles: int = 0
    avg_strength: float = 0.0
    last_updated_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_fragments": self.total_fragments,
            "total_consolidated": self.total_consolidated,
            "total_integrated": self.total_integrated,
            "total_pruned": self.total_pruned,
            "total_dreams": self.total_dreams,
            "total_replays": self.total_replays,
            "total_sleep_cycles": self.total_sleep_cycles,
            "avg_strength": self.avg_strength,
            "last_updated_at": self.last_updated_at,
        }


@dataclass
class ConsolidationSnapshot:
    """Point-in-time snapshot of the engine state."""
    agent_count: int = 0
    total_fragments: int = 0
    total_tasks: int = 0
    total_dreams: int = 0
    stats: ConsolidationStats = field(default_factory=ConsolidationStats)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_count": self.agent_count,
            "total_fragments": self.total_fragments,
            "total_tasks": self.total_tasks,
            "total_dreams": self.total_dreams,
            "stats": self.stats.to_dict(),
            "timestamp": self.timestamp,
        }


@dataclass
class MemoryEvent:
    """A consolidation lifecycle event emitted to subscribed handlers."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    kind: MemoryEventKind = MemoryEventKind.CONSOLIDATION_STARTED
    agent_id: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "kind": self.kind.value,
            "agent_id": self.agent_id,
            "payload": dict(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# MemoryConsolidatorEngine Singleton
# ---------------------------------------------------------------------------


class MemoryConsolidatorEngine:
    """Offline memory consolidation and dream system for AI agents.

    The engine ingests short-term episodic fragments, processes them
    through a consolidation pipeline (encode, stabilize, integrate,
    prune, replay), models forgetting via the Ebbinghaus retention
    curve, and generates dream sequences that creatively recombine
    memory fragments to surface novel associations.

    Thread-safe singleton usable concurrently from multiple agents.
    All public methods are guarded by a re-entrant lock.
    """

    _instance: Optional["MemoryConsolidatorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    _MAX_FRAGMENTS = 10000
    _MAX_TASKS = 5000
    _MAX_REPLAYS = 5000
    _MAX_DREAMS = 5000
    _MAX_SLEEP_CYCLES = 5000
    _MAX_EVENTS = 2000

    # Strengthening applied per replay, scaled by fragment salience.
    _REPLAY_STRENGTHEN_BASE = 0.12
    # Cap so a single fragment never exceeds unit strength.
    _MAX_STRENGTH = 1.0
    _MIN_STRENGTH = 0.0
    # Fragments below this strength threshold are candidates for pruning.
    _PRUNE_STRENGTH_THRESHOLD = 0.15
    # Stability scaling for the Ebbinghaus forgetting curve (hours per unit strength).
    _FORGETTING_STABILITY_HOURS = 240.0

    @classmethod
    def get_instance(cls) -> "MemoryConsolidatorEngine":
        """Get or create the global singleton engine (double-checked locking)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._fragments: Dict[str, MemoryFragment] = {}
        self._fragment_order: List[str] = []
        self._tasks: Dict[str, ConsolidationTask] = {}
        self._task_order: List[str] = []
        self._replays: Dict[str, ReplaySession] = {}
        self._dreams: Dict[str, DreamSequence] = {}
        self._dream_order: List[str] = []
        self._sleep_cycles: Dict[str, SleepCycle] = {}
        self._pruned_ids: set = set()
        self._event_handlers: Dict[str, List[Tuple[str, Callable[[Dict[str, Any]], None]]]] = {}
        self._events: List[MemoryEvent] = []
        self._counters: Dict[str, int] = {
            "fragments_registered": 0,
            "consolidations_started": 0,
            "consolidations_completed": 0,
            "fragments_strengthened": 0,
            "fragments_integrated": 0,
            "fragments_pruned": 0,
            "dreams_generated": 0,
            "replays_completed": 0,
            "sleep_cycles_started": 0,
            "sleep_cycles_completed": 0,
        }
        self._initialized: bool = True
        self._seed_default_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_default_data(self) -> None:
        """Seed demo agents, fragments, tasks, a replay, a dream, and a
        sleep cycle so the engine is immediately useful without setup."""
        now = _now_iso()

        # --- Agent alpha: 5 fragments (mix of EPISODIC, SEMANTIC, PROCEDURAL) ---
        alpha_fragments: List[MemoryFragment] = []

        alpha_fragments.append(MemoryFragment(
            agent_id="agent_alpha",
            memory_type=MemoryType.EPISODIC,
            content="Located a hidden supply cache behind the waterfall at grid H7",
            salience=0.82,
            emotional_weight=0.35,
            strength=0.74,
            metadata={"location": "H7", "session": "alpha_session_1"},
        ))
        alpha_fragments.append(MemoryFragment(
            agent_id="agent_alpha",
            memory_type=MemoryType.SEMANTIC,
            content="Waterfalls in this region frequently conceal cave systems",
            salience=0.61,
            emotional_weight=0.10,
            strength=0.66,
            metadata={"domain": "geography", "confidence": 0.8},
        ))
        alpha_fragments.append(MemoryFragment(
            agent_id="agent_alpha",
            memory_type=MemoryType.PROCEDURAL,
            content="Sequence to disarm the southern gate trap: lever, lever, plate, plate",
            salience=0.90,
            emotional_weight=0.20,
            strength=0.88,
            metadata={"steps": 4, "success_rate": 0.95},
        ))
        alpha_fragments.append(MemoryFragment(
            agent_id="agent_alpha",
            memory_type=MemoryType.EPISODIC,
            content="Ally agent_beta warned of a patrol approaching the ridge at dusk",
            salience=0.71,
            emotional_weight=0.55,
            strength=0.60,
            metadata={"source": "agent_beta", "time_of_day": "dusk"},
        ))
        alpha_fragments.append(MemoryFragment(
            agent_id="agent_alpha",
            memory_type=MemoryType.PROCEDURAL,
            content="Crafting a smoke bomb requires sulfur, charcoal, and a wet binding agent",
            salience=0.55,
            emotional_weight=0.05,
            strength=0.52,
            metadata={"recipe": True, "yield": 1},
        ))

        # --- Agent beta: 5 fragments (mix of EPISODIC, SEMANTIC, PROCEDURAL) ---
        beta_fragments: List[MemoryFragment] = []

        beta_fragments.append(MemoryFragment(
            agent_id="agent_beta",
            memory_type=MemoryType.EPISODIC,
            content="Witnessed the southern gate trap triggering on a stray animal at dawn",
            salience=0.78,
            emotional_weight=0.40,
            strength=0.69,
            metadata={"location": "southern_gate", "time_of_day": "dawn"},
        ))
        beta_fragments.append(MemoryFragment(
            agent_id="agent_beta",
            memory_type=MemoryType.SEMANTIC,
            content="Patrol routes rotate clockwise every three hours around the central keep",
            salience=0.84,
            emotional_weight=0.15,
            strength=0.80,
            metadata={"domain": "tactics", "rotation_hours": 3},
        ))
        beta_fragments.append(MemoryFragment(
            agent_id="agent_beta",
            memory_type=MemoryType.PROCEDURAL,
            content="To cross the moat silently, time movement with the wind gusts at 12-second intervals",
            salience=0.67,
            emotional_weight=0.10,
            strength=0.58,
            metadata={"interval_seconds": 12},
        ))
        beta_fragments.append(MemoryFragment(
            agent_id="agent_beta",
            memory_type=MemoryType.EPISODIC,
            content="Discovered a sealed cellar entrance beneath the abandoned tavern",
            salience=0.73,
            emotional_weight=0.45,
            strength=0.63,
            metadata={"location": "abandoned_tavern"},
        ))
        beta_fragments.append(MemoryFragment(
            agent_id="agent_beta",
            memory_type=MemoryType.SEMANTIC,
            content="Tavern cellars in this district historically connect to the old aqueduct network",
            salience=0.59,
            emotional_weight=0.08,
            strength=0.50,
            metadata={"domain": "history", "confidence": 0.6},
        ))

        for fragment in alpha_fragments + beta_fragments:
            self._fragments[fragment.id] = fragment
            self._fragment_order.append(fragment.id)

        self._counters["fragments_registered"] = len(self._fragments)

        # --- 2 consolidation tasks ---
        task1 = ConsolidationTask(
            agent_id="agent_alpha",
            phase=ConsolidationPhase.STABILIZE,
            fragment_ids=[alpha_fragments[0].id, alpha_fragments[2].id],
            status=ConsolidationStatus.PROCESSING,
            started_at=now,
        )
        self._tasks[task1.id] = task1
        self._task_order.append(task1.id)

        task2 = ConsolidationTask(
            agent_id="agent_beta",
            phase=ConsolidationPhase.INTEGRATE,
            fragment_ids=[beta_fragments[3].id, beta_fragments[4].id],
            status=ConsolidationStatus.CONSOLIDATED,
            started_at=now,
            completed_at=now,
            result_summary="Merged tavern cellar discovery with historical aqueduct knowledge",
        )
        self._tasks[task2.id] = task2
        self._task_order.append(task2.id)

        self._counters["consolidations_started"] = 2
        self._counters["consolidations_completed"] = 1

        # --- 1 replay session (already completed, strengthening applied) ---
        replay_fragments = [alpha_fragments[2].id, alpha_fragments[0].id, alpha_fragments[3].id]
        replay = ReplaySession(
            agent_id="agent_alpha",
            strategy=ReplayStrategy.PRIORITIZED,
            fragment_ids=list(replay_fragments),
            order=[0, 1, 2],
            started_at=now,
            completed_at=now,
            strengthening_applied={
                alpha_fragments[2].id: 0.108,
                alpha_fragments[0].id: 0.098,
                alpha_fragments[3].id: 0.085,
            },
        )
        self._replays[replay.id] = replay
        self._counters["replays_completed"] = 1
        self._counters["fragments_strengthened"] = 3

        # --- 1 dream sequence ---
        dream = DreamSequence(
            agent_id="agent_beta",
            fragment_ids=[beta_fragments[0].id, beta_fragments[1].id, beta_fragments[2].id],
            narrative=(
                "In the dream, the patrol route rotated around a silent moat "
                "while a stray animal crossed at dawn, revealing a hidden path "
                "beneath the abandoned tavern cellar."
            ),
            novelty_score=0.62,
            coherence_score=0.71,
            created_at=now,
        )
        self._dreams[dream.id] = dream
        self._dream_order.append(dream.id)
        self._counters["dreams_generated"] = 1

        # --- 1 sleep cycle (completed REM cycle) ---
        cycle = SleepCycle(
            agent_id="agent_alpha",
            stage=SleepStage.REM,
            started_at=now,
            completed_at=now,
            duration_seconds=1800.0,
            fragments_processed=3,
            dreams_generated=1,
        )
        self._sleep_cycles[cycle.id] = cycle
        self._counters["sleep_cycles_started"] = 1
        self._counters["sleep_cycles_completed"] = 1

    # ------------------------------------------------------------------
    # Event dispatch
    # ------------------------------------------------------------------

    def _emit_event(
        self,
        kind: MemoryEventKind,
        agent_id: str,
        payload: Dict[str, Any],
    ) -> MemoryEvent:
        """Record an event and invoke any registered handlers.

        A faulty handler must never break engine operation; all handler
        exceptions are swallowed.
        """
        event = MemoryEvent(
            kind=kind,
            agent_id=agent_id,
            payload=payload,
        )
        self._events.append(event)
        if len(self._events) > self._MAX_EVENTS:
            self._events = self._events[-self._MAX_EVENTS:]
        handlers = self._event_handlers.get(kind.value, [])
        for _handler_id, handler in handlers:
            try:
                handler(event.to_dict())
            except Exception:
                pass
        return event

    # ------------------------------------------------------------------
    # Fragment management
    # ------------------------------------------------------------------

    def register_fragment(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        salience: float = 0.5,
        emotional_weight: float = 0.0,
        source_fragments: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryFragment:
        """Register a new memory fragment for an agent.

        Salience and emotional weight are clamped to [0, 1]. Newly
        registered fragments start at a baseline strength equal to their
        salience, reflecting that salient events form stronger initial
        traces.
        """
        with self._lock:
            fragment = MemoryFragment(
                agent_id=agent_id,
                memory_type=memory_type,
                content=content,
                salience=max(0.0, min(1.0, salience)),
                emotional_weight=max(0.0, min(1.0, emotional_weight)),
                strength=max(0.0, min(1.0, salience)),
                source_fragments=list(source_fragments or []),
                metadata=dict(metadata or {}),
            )
            self._fragments[fragment.id] = fragment
            self._fragment_order.append(fragment.id)
            self._enforce_fragment_capacity()
            self._counters["fragments_registered"] += 1
            return fragment

    def get_fragment(self, fragment_id: str) -> Optional[MemoryFragment]:
        """Retrieve a fragment by id, updating access statistics.

        Returns None if the fragment does not exist.
        """
        with self._lock:
            fragment = self._fragments.get(fragment_id)
            if fragment is None:
                return None
            fragment.access_count += 1
            fragment.last_accessed = _now_iso()
            return fragment

    def list_fragments(
        self,
        agent_id: Optional[str] = None,
        memory_type: Optional[MemoryType] = None,
        min_strength: float = 0.0,
        include_pruned: bool = False,
    ) -> List[MemoryFragment]:
        """List fragments, optionally filtered by agent, type, and strength.

        Pruned fragments are excluded by default; pass include_pruned=True
        to surface them.
        """
        with self._lock:
            results: List[MemoryFragment] = []
            for fragment in self._fragments.values():
                if agent_id is not None and fragment.agent_id != agent_id:
                    continue
                if memory_type is not None and fragment.memory_type != memory_type:
                    continue
                if fragment.strength < min_strength:
                    continue
                if not include_pruned and fragment.id in self._pruned_ids:
                    continue
                results.append(fragment)
            results.sort(key=lambda f: (f.agent_id, f.timestamp))
            return results

    def remove_fragment(self, fragment_id: str) -> bool:
        """Remove a fragment entirely from the engine.

        Returns True if a fragment was removed, False otherwise.
        """
        with self._lock:
            if fragment_id not in self._fragments:
                return False
            self._fragments.pop(fragment_id, None)
            if fragment_id in self._fragment_order:
                self._fragment_order.remove(fragment_id)
            self._pruned_ids.discard(fragment_id)
            return True

    def strengthen_fragment(
        self, fragment_id: str, amount: float = 0.1
    ) -> Optional[MemoryFragment]:
        """Increase a fragment's strength by a given amount.

        Strength is clamped to [0, 1]. Emits a MEMORY_STRENGTHENED event.
        Returns the updated fragment, or None if not found.
        """
        with self._lock:
            fragment = self._fragments.get(fragment_id)
            if fragment is None:
                return None
            fragment.strength = max(
                self._MIN_STRENGTH, min(self._MAX_STRENGTH, fragment.strength + amount)
            )
            self._counters["fragments_strengthened"] += 1
            self._emit_event(
                MemoryEventKind.MEMORY_STRENGTHENED,
                fragment.agent_id,
                {
                    "fragment_id": fragment.id,
                    "amount": amount,
                    "new_strength": fragment.strength,
                },
            )
            return fragment

    # ------------------------------------------------------------------
    # Consolidation tasks
    # ------------------------------------------------------------------

    def start_consolidation(
        self,
        agent_id: str,
        fragment_ids: List[str],
        phase: ConsolidationPhase = ConsolidationPhase.STABILIZE,
    ) -> ConsolidationTask:
        """Start a new consolidation task in the PROCESSING state.

        Emits a CONSOLIDATION_STARTED event. The task references the
        provided fragment ids; missing ids are silently ignored.
        """
        with self._lock:
            valid_ids = [fid for fid in fragment_ids if fid in self._fragments]
            task = ConsolidationTask(
                agent_id=agent_id,
                phase=phase,
                fragment_ids=valid_ids,
                status=ConsolidationStatus.PROCESSING,
            )
            self._tasks[task.id] = task
            self._task_order.append(task.id)
            self._enforce_task_capacity()
            self._counters["consolidations_started"] += 1
            self._emit_event(
                MemoryEventKind.CONSOLIDATION_STARTED,
                agent_id,
                {
                    "task_id": task.id,
                    "phase": phase.value,
                    "fragment_ids": list(valid_ids),
                },
            )
            return task

    def complete_consolidation(
        self, task_id: str, result_summary: str = ""
    ) -> Optional[ConsolidationTask]:
        """Complete a consolidation task, marking it CONSOLIDATED.

        Strengthens the associated fragments slightly to reflect
        stabilization. Emits CONSOLIDATION_COMPLETED. Returns the task,
        or None if not found or already completed.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None or task.status == ConsolidationStatus.CONSOLIDATED:
                return None
            task.status = ConsolidationStatus.CONSOLIDATED
            task.completed_at = _now_iso()
            task.result_summary = result_summary
            for fragment_id in task.fragment_ids:
                fragment = self._fragments.get(fragment_id)
                if fragment is not None:
                    fragment.strength = min(
                        self._MAX_STRENGTH,
                        fragment.strength + self._REPLAY_STRENGTHEN_BASE * 0.5,
                    )
            self._counters["consolidations_completed"] += 1
            self._emit_event(
                MemoryEventKind.CONSOLIDATION_COMPLETED,
                task.agent_id,
                {
                    "task_id": task.id,
                    "result_summary": result_summary,
                    "fragment_count": len(task.fragment_ids),
                },
            )
            return task

    def integrate_fragments(
        self,
        agent_id: str,
        source_ids: List[str],
        target_content: str,
        salience: Optional[float] = None,
        memory_type: MemoryType = MemoryType.SEMANTIC,
    ) -> Optional[MemoryFragment]:
        """Integrate several source fragments into a single new fragment.

        The new fragment inherits the maximum strength of its sources plus
        a small integration bonus. Source fragments are marked as
        integrated (tracked via metadata and reduced strength). Emits a
        MEMORY_INTEGRATED event. Returns the new fragment, or None if no
        valid source fragments were supplied.
        """
        with self._lock:
            sources: List[MemoryFragment] = []
            for source_id in source_ids:
                fragment = self._fragments.get(source_id)
                if fragment is not None and fragment.agent_id == agent_id:
                    sources.append(fragment)
            if not sources:
                return None
            inherited_strength = max(s.strength for s in sources)
            inherited_emotion = max(s.emotional_weight for s in sources)
            effective_salience = (
                salience if salience is not None else max(s.salience for s in sources)
            )
            integrated = MemoryFragment(
                agent_id=agent_id,
                memory_type=memory_type,
                content=target_content,
                salience=max(0.0, min(1.0, effective_salience)),
                emotional_weight=max(0.0, min(1.0, inherited_emotion)),
                strength=min(
                    self._MAX_STRENGTH,
                    inherited_strength + self._REPLAY_STRENGTHEN_BASE,
                ),
                source_fragments=[s.id for s in sources],
                metadata={
                    "integrated_from": [s.id for s in sources],
                    "integration_time": _now_iso(),
                },
            )
            self._fragments[integrated.id] = integrated
            self._fragment_order.append(integrated.id)
            for source in sources:
                source.metadata["integrated_into"] = integrated.id
                source.strength = max(
                    self._MIN_STRENGTH, source.strength - self._REPLAY_STRENGTHEN_BASE
                )
            self._enforce_fragment_capacity()
            self._counters["fragments_integrated"] += 1
            self._emit_event(
                MemoryEventKind.MEMORY_INTEGRATED,
                agent_id,
                {
                    "new_fragment_id": integrated.id,
                    "source_ids": [s.id for s in sources],
                    "memory_type": memory_type.value,
                },
            )
            return integrated

    def prune_fragment(self, fragment_id: str) -> Optional[MemoryFragment]:
        """Mark a fragment as pruned due to low strength.

        The fragment is retained for audit purposes but flagged as pruned
        and its strength is driven to zero. Emits MEMORY_PRUNED. Returns
        the fragment, or None if not found.
        """
        with self._lock:
            fragment = self._fragments.get(fragment_id)
            if fragment is None:
                return None
            self._pruned_ids.add(fragment_id)
            fragment.strength = self._MIN_STRENGTH
            fragment.metadata["pruned"] = True
            fragment.metadata["pruned_at"] = _now_iso()
            self._counters["fragments_pruned"] += 1
            self._emit_event(
                MemoryEventKind.MEMORY_PRUNED,
                fragment.agent_id,
                {
                    "fragment_id": fragment.id,
                    "memory_type": fragment.memory_type.value,
                },
            )
            return fragment

    # ------------------------------------------------------------------
    # Replay sessions
    # ------------------------------------------------------------------

    def start_replay(
        self,
        agent_id: str,
        fragment_ids: List[str],
        strategy: ReplayStrategy = ReplayStrategy.SEQUENTIAL,
    ) -> ReplaySession:
        """Start a replay session that re-retrieves fragments in a
        strategy-defined order.

        Emits no dedicated event until completion; the session is opened
        in a non-terminal state.
        """
        with self._lock:
            valid_ids = [
                fid
                for fid in fragment_ids
                if fid in self._fragments
                and self._fragments[fid].agent_id == agent_id
            ]
            order = self._compute_replay_order(valid_ids, strategy)
            session = ReplaySession(
                agent_id=agent_id,
                strategy=strategy,
                fragment_ids=list(valid_ids),
                order=list(order),
            )
            self._replays[session.id] = session
            self._enforce_replay_capacity()
            return session

    def complete_replay(self, replay_id: str) -> Optional[ReplaySession]:
        """Complete a replay session and apply strengthening to fragments.

        Each fragment receives a strength boost proportional to its
        salience. Updates access statistics. Emits REPLAY_COMPLETED.
        Returns the session, or None if not found or already completed.
        """
        with self._lock:
            session = self._replays.get(replay_id)
            if session is None or session.completed_at:
                return None
            strengthening: Dict[str, float] = {}
            for fragment_id in session.fragment_ids:
                fragment = self._fragments.get(fragment_id)
                if fragment is None:
                    continue
                boost = self._REPLAY_STRENGTHEN_BASE * fragment.salience
                fragment.strength = min(
                    self._MAX_STRENGTH, fragment.strength + boost
                )
                fragment.access_count += 1
                fragment.last_accessed = _now_iso()
                strengthening[fragment_id] = round(boost, 4)
            session.strengthening_applied = strengthening
            session.completed_at = _now_iso()
            self._counters["replays_completed"] += 1
            self._counters["fragments_strengthened"] += len(strengthening)
            self._emit_event(
                MemoryEventKind.REPLAY_COMPLETED,
                session.agent_id,
                {
                    "replay_id": session.id,
                    "strategy": session.strategy.value,
                    "strengthened_count": len(strengthening),
                },
            )
            return session

    def _compute_replay_order(
        self, fragment_ids: List[str], strategy: ReplayStrategy
    ) -> List[int]:
        """Compute the playback order (indices into fragment_ids) for a
        replay session based on the chosen strategy."""
        n = len(fragment_ids)
        if n == 0:
            return []
        if strategy == ReplayStrategy.SEQUENTIAL:
            return list(range(n))
        if strategy == ReplayStrategy.RANDOM:
            order = list(range(n))
            random.shuffle(order)
            return order
        if strategy == ReplayStrategy.PRIORITIZED:
            fragments = [self._fragments[fid] for fid in fragment_ids]
            indexed = list(enumerate(fragments))
            indexed.sort(
                key=lambda pair: (pair[1].salience, pair[1].strength),
                reverse=True,
            )
            return [index for index, _ in indexed]
        # SPATIOTEMPORAL: chronological by timestamp, then salience desc
        fragments = [self._fragments[fid] for fid in fragment_ids]
        indexed = list(enumerate(fragments))
        indexed.sort(
            key=lambda pair: (pair[1].timestamp, -pair[1].salience)
        )
        return [index for index, _ in indexed]

    # ------------------------------------------------------------------
    # Dream generation
    # ------------------------------------------------------------------

    def generate_dream(
        self,
        agent_id: str,
        fragment_ids: List[str],
    ) -> Optional[DreamSequence]:
        """Generate a dream sequence by creatively recombining fragments.

        The narrative weaves fragment content snippets together and
        surfaces a novel association. Novelty is estimated from how
        dissimilar the combined fragments are; coherence is estimated
        from average strength. Emits DREAM_GENERATED.
        """
        with self._lock:
            sources: List[MemoryFragment] = []
            for fid in fragment_ids:
                fragment = self._fragments.get(fid)
                if fragment is not None and fragment.agent_id == agent_id:
                    sources.append(fragment)
            if not sources:
                return None
            narrative = self._build_dream_narrative(agent_id, sources)
            novelty = self._compute_novelty_score(sources)
            coherence = self._compute_coherence_score(sources)
            dream = DreamSequence(
                agent_id=agent_id,
                fragment_ids=[s.id for s in sources],
                narrative=narrative,
                novelty_score=round(novelty, 4),
                coherence_score=round(coherence, 4),
            )
            self._dreams[dream.id] = dream
            self._dream_order.append(dream.id)
            self._enforce_dream_capacity()
            self._counters["dreams_generated"] += 1
            # Dreaming lightly reinforces the pathways it touched.
            for source in sources:
                source.access_count += 1
                source.last_accessed = _now_iso()
                source.strength = min(
                    self._MAX_STRENGTH,
                    source.strength + self._REPLAY_STRENGTHEN_BASE * 0.25,
                )
            self._emit_event(
                MemoryEventKind.DREAM_GENERATED,
                agent_id,
                {
                    "dream_id": dream.id,
                    "fragment_count": len(sources),
                    "novelty_score": dream.novelty_score,
                    "coherence_score": dream.coherence_score,
                },
            )
            return dream

    def _build_dream_narrative(
        self, agent_id: str, fragments: List[MemoryFragment]
    ) -> str:
        """Weave a creative narrative from fragment content snippets.

        Snippets are trimmed and joined with dreamlike connective tissue,
        and a novel association is appended that links the two highest
        salience fragments.
        """
        snippets: List[str] = []
        for fragment in fragments:
            snippet = fragment.content.strip().replace("\n", " ")
            if len(snippet) > 90:
                snippet = snippet[:87] + "..."
            snippets.append(snippet)
        body = ". ".join(snippets)
        # Identify the two most salient fragments to surface an association.
        ranked = sorted(fragments, key=lambda f: f.salience, reverse=True)
        association = ""
        if len(ranked) >= 2:
            a = ranked[0].memory_type.value
            b = ranked[1].memory_type.value
            association = (
                f" A novel association surfaces between a {a} thread and a "
                f"{b} thread, hinting at an unseen connection."
            )
        elif ranked:
            association = (
                f" A lone {ranked[0].memory_type.value} memory echoes "
                f"through the dreamscape."
            )
        return f"Dream of {agent_id}: {body}.{association}"

    def _compute_novelty_score(
        self, fragments: List[MemoryFragment]
    ) -> float:
        """Estimate novelty from the diversity of memory types involved.

        More distinct memory types and a wider spread of salience values
        yield a higher novelty score in [0, 1].
        """
        if not fragments:
            return 0.0
        type_diversity = len({f.memory_type for f in fragments}) / len(MemoryType)
        salience_values = [f.salience for f in fragments]
        if len(salience_values) > 1:
            mean = sum(salience_values) / len(salience_values)
            variance = sum((v - mean) ** 2 for v in salience_values) / len(salience_values)
            spread = min(1.0, math.sqrt(variance) * 2.0)
        else:
            spread = 0.0
        return max(0.0, min(1.0, 0.6 * type_diversity + 0.4 * spread))

    def _compute_coherence_score(
        self, fragments: List[MemoryFragment]
    ) -> float:
        """Estimate coherence from average strength and shared agent scope.

        Stronger, more emotionally consistent fragments produce a more
        coherent dream narrative.
        """
        if not fragments:
            return 0.0
        avg_strength = sum(f.strength for f in fragments) / len(fragments)
        emotional_values = [f.emotional_weight for f in fragments]
        if len(emotional_values) > 1:
            mean = sum(emotional_values) / len(emotional_values)
            variance = sum((v - mean) ** 2 for v in emotional_values) / len(emotional_values)
            consistency = max(0.0, 1.0 - math.sqrt(variance) * 2.0)
        else:
            consistency = 1.0
        return max(0.0, min(1.0, 0.7 * avg_strength + 0.3 * consistency))

    # ------------------------------------------------------------------
    # Sleep cycles
    # ------------------------------------------------------------------

    def start_sleep_cycle(
        self,
        agent_id: str,
        stage: SleepStage = SleepStage.LIGHT,
        duration_seconds: float = 0.0,
    ) -> SleepCycle:
        """Open a sleep cycle window for an agent.

        Emits SLEEP_CYCLE_STARTED. The cycle is left open until
        complete_sleep_cycle is called.
        """
        with self._lock:
            cycle = SleepCycle(
                agent_id=agent_id,
                stage=stage,
                duration_seconds=max(0.0, duration_seconds),
            )
            self._sleep_cycles[cycle.id] = cycle
            self._enforce_sleep_cycle_capacity()
            self._counters["sleep_cycles_started"] += 1
            self._emit_event(
                MemoryEventKind.SLEEP_CYCLE_STARTED,
                agent_id,
                {
                    "cycle_id": cycle.id,
                    "stage": stage.value,
                    "duration_seconds": cycle.duration_seconds,
                },
            )
            return cycle

    def complete_sleep_cycle(
        self,
        cycle_id: str,
        fragments_processed: int = 0,
        dreams_generated: int = 0,
    ) -> Optional[SleepCycle]:
        """Close a sleep cycle window with final statistics.

        Emits SLEEP_CYCLE_COMPLETED. Returns the cycle, or None if not
        found or already completed.
        """
        with self._lock:
            cycle = self._sleep_cycles.get(cycle_id)
            if cycle is None or cycle.completed_at:
                return None
            cycle.completed_at = _now_iso()
            cycle.fragments_processed = max(0, fragments_processed)
            cycle.dreams_generated = max(0, dreams_generated)
            # Infer duration from timestamps if not explicitly provided.
            if cycle.duration_seconds <= 0.0:
                started = _parse_iso(cycle.started_at)
                completed = _parse_iso(cycle.completed_at)
                if started is not None and completed is not None:
                    cycle.duration_seconds = max(
                        0.0, (completed - started).total_seconds()
                    )
            self._counters["sleep_cycles_completed"] += 1
            self._emit_event(
                MemoryEventKind.SLEEP_CYCLE_COMPLETED,
                cycle.agent_id,
                {
                    "cycle_id": cycle.id,
                    "stage": cycle.stage.value,
                    "fragments_processed": cycle.fragments_processed,
                    "dreams_generated": cycle.dreams_generated,
                },
            )
            return cycle

    # ------------------------------------------------------------------
    # Forgetting curve
    # ------------------------------------------------------------------

    def compute_forgetting_curve(
        self,
        fragment_id: str,
        time_elapsed_hours: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Compute retention for a fragment using the Ebbinghaus curve.

        R = e^(-t / S), where t is elapsed hours and S is the memory
        stability derived from the fragment's strength. Stronger
        memories decay more slowly. Returns a dictionary with the
        retention ratio, stability, and inputs, or None if the fragment
        is not found.
        """
        with self._lock:
            fragment = self._fragments.get(fragment_id)
            if fragment is None:
                return None
            stability_hours = max(
                1.0, fragment.strength * self._FORGETTING_STABILITY_HOURS
            )
            elapsed = max(0.0, time_elapsed_hours)
            retention = math.exp(-elapsed / stability_hours)
            return {
                "fragment_id": fragment.id,
                "time_elapsed_hours": elapsed,
                "stability_hours": round(stability_hours, 4),
                "retention": round(retention, 4),
                "current_strength": fragment.strength,
                "salience": fragment.salience,
            }

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_consolidation_tasks(
        self,
        agent_id: Optional[str] = None,
        status: Optional[ConsolidationStatus] = None,
    ) -> List[ConsolidationTask]:
        """List consolidation tasks, optionally filtered by agent/status."""
        with self._lock:
            results: List[ConsolidationTask] = []
            for task_id in reversed(self._task_order):
                task = self._tasks.get(task_id)
                if task is None:
                    continue
                if agent_id is not None and task.agent_id != agent_id:
                    continue
                if status is not None and task.status != status:
                    continue
                results.append(task)
            return list(reversed(results))

    def get_dreams(
        self,
        agent_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[DreamSequence]:
        """List dream sequences, optionally filtered by agent, most recent first."""
        with self._lock:
            results: List[DreamSequence] = []
            for dream_id in reversed(self._dream_order):
                dream = self._dreams.get(dream_id)
                if dream is None:
                    continue
                if agent_id is not None and dream.agent_id != agent_id:
                    continue
                results.append(dream)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    def get_replays(
        self, agent_id: Optional[str] = None, limit: int = 50
    ) -> List[ReplaySession]:
        """List replay sessions, optionally filtered by agent."""
        with self._lock:
            results: List[ReplaySession] = []
            for session in reversed(list(self._replays.values())):
                if agent_id is not None and session.agent_id != agent_id:
                    continue
                results.append(session)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    def get_sleep_cycles(
        self, agent_id: Optional[str] = None, limit: int = 50
    ) -> List[SleepCycle]:
        """List sleep cycles, optionally filtered by agent."""
        with self._lock:
            results: List[SleepCycle] = []
            for cycle in reversed(list(self._sleep_cycles.values())):
                if agent_id is not None and cycle.agent_id != agent_id:
                    continue
                results.append(cycle)
                if len(results) >= limit:
                    break
            return list(reversed(results))

    # ------------------------------------------------------------------
    # Event handlers and event listing
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        kind: MemoryEventKind,
        handler: Callable[[Dict[str, Any]], None],
    ) -> str:
        """Register a handler for a specific event kind.

        Returns a handler id that can be used for future de-registration.
        """
        with self._lock:
            handler_id = uuid.uuid4().hex
            key = kind.value
            if key not in self._event_handlers:
                self._event_handlers[key] = []
            self._event_handlers[key].append((handler_id, handler))
            return handler_id

    def unregister_event_handler(self, handler_id: str) -> bool:
        """Remove a previously registered handler by id.

        Returns True if a handler was removed, False otherwise.
        """
        with self._lock:
            for key, handlers in self._event_handlers.items():
                for index, (existing_id, _handler) in enumerate(handlers):
                    if existing_id == handler_id:
                        handlers.pop(index)
                        return True
            return False

    def list_events(
        self,
        event_kind: Optional[MemoryEventKind] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return recent events, optionally filtered by kind."""
        with self._lock:
            events = list(self._events)
            if event_kind is not None:
                events = [e for e in events if e.kind == event_kind]
            return [e.to_dict() for e in events[-limit:]]

    # ------------------------------------------------------------------
    # Stats, status, snapshot, and lifecycle
    # ------------------------------------------------------------------

    def _compute_stats(self) -> ConsolidationStats:
        """Compute aggregate statistics from the current engine state."""
        fragments = list(self._fragments.values())
        total_fragments = len(fragments)
        avg_strength = (
            sum(f.strength for f in fragments) / total_fragments
            if total_fragments
            else 0.0
        )
        total_pruned = len(self._pruned_ids)
        total_integrated = sum(
            1 for f in fragments if f.metadata.get("integrated_into")
        )
        return ConsolidationStats(
            total_fragments=total_fragments,
            total_consolidated=self._counters["consolidations_completed"],
            total_integrated=total_integrated,
            total_pruned=total_pruned,
            total_dreams=len(self._dreams),
            total_replays=len(self._replays),
            total_sleep_cycles=len(self._sleep_cycles),
            avg_strength=round(avg_strength, 4),
            last_updated_at=_now_iso(),
        )

    def get_stats(self) -> ConsolidationStats:
        """Compute and return aggregate consolidation statistics."""
        with self._lock:
            return self._compute_stats()

    def get_status(self) -> Dict[str, Any]:
        """Return the current operational status of the engine."""
        with self._lock:
            stats = self._compute_stats()
            agents = {f.agent_id for f in self._fragments.values()}
            return {
                "engine_id": id(self),
                "initialized": self._initialized,
                "agent_count": len(agents),
                "total_fragments": len(self._fragments),
                "total_tasks": len(self._tasks),
                "total_replays": len(self._replays),
                "total_dreams": len(self._dreams),
                "total_sleep_cycles": len(self._sleep_cycles),
                "total_events": len(self._events),
                "pruned_fragment_count": len(self._pruned_ids),
                "counters": dict(self._counters),
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> ConsolidationSnapshot:
        """Capture a point-in-time snapshot of the engine state."""
        with self._lock:
            stats = self._compute_stats()
            agents = {f.agent_id for f in self._fragments.values()}
            return ConsolidationSnapshot(
                agent_count=len(agents),
                total_fragments=len(self._fragments),
                total_tasks=len(self._tasks),
                total_dreams=len(self._dreams),
                stats=stats,
            )

    def reset(self) -> None:
        """Reset the engine to its initial seeded state."""
        with self._lock:
            self._fragments.clear()
            self._fragment_order.clear()
            self._tasks.clear()
            self._task_order.clear()
            self._replays.clear()
            self._dreams.clear()
            self._dream_order.clear()
            self._sleep_cycles.clear()
            self._pruned_ids.clear()
            self._event_handlers.clear()
            self._events.clear()
            self._counters = {
                "fragments_registered": 0,
                "consolidations_started": 0,
                "consolidations_completed": 0,
                "fragments_strengthened": 0,
                "fragments_integrated": 0,
                "fragments_pruned": 0,
                "dreams_generated": 0,
                "replays_completed": 0,
                "sleep_cycles_started": 0,
                "sleep_cycles_completed": 0,
            }
            self._seed_default_data()

    # ------------------------------------------------------------------
    # Capacity management
    # ------------------------------------------------------------------

    def _enforce_fragment_capacity(self) -> None:
        """Evict the oldest fragments when the capacity is exceeded."""
        while len(self._fragment_order) > self._MAX_FRAGMENTS:
            oldest_id = self._fragment_order.pop(0)
            self._fragments.pop(oldest_id, None)
            self._pruned_ids.discard(oldest_id)

    def _enforce_task_capacity(self) -> None:
        """Evict the oldest tasks when the capacity is exceeded."""
        while len(self._task_order) > self._MAX_TASKS:
            oldest_id = self._task_order.pop(0)
            self._tasks.pop(oldest_id, None)

    def _enforce_replay_capacity(self) -> None:
        """Evict the oldest replay sessions when the capacity is exceeded."""
        replay_ids = list(self._replays.keys())
        while len(replay_ids) > self._MAX_REPLAYS:
            oldest_id = replay_ids.pop(0)
            self._replays.pop(oldest_id, None)

    def _enforce_dream_capacity(self) -> None:
        """Evict the oldest dream sequences when the capacity is exceeded."""
        while len(self._dream_order) > self._MAX_DREAMS:
            oldest_id = self._dream_order.pop(0)
            self._dreams.pop(oldest_id, None)

    def _enforce_sleep_cycle_capacity(self) -> None:
        """Evict the oldest sleep cycles when the capacity is exceeded."""
        cycle_ids = list(self._sleep_cycles.keys())
        while len(cycle_ids) > self._MAX_SLEEP_CYCLES:
            oldest_id = cycle_ids.pop(0)
            self._sleep_cycles.pop(oldest_id, None)


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------


def get_memory_consolidator() -> MemoryConsolidatorEngine:
    """Get or create the global MemoryConsolidatorEngine singleton."""
    return MemoryConsolidatorEngine.get_instance()


# Backward-compatible alias used by legacy callers that reference the
# original short class name.
MemoryConsolidator = MemoryConsolidatorEngine
