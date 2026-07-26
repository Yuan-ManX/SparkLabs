"""
SparkLabs Agent - Engine Fusion Loop

The real-time bidirectional fusion layer that tightly couples the AgentKernel
with the AINativeEngineCore. This module is the defining innovation of the
SparkLabs AI-native game engine: the agent does not merely send commands to
the engine — it continuously perceives engine state, autonomously generates
goals based on what it observes, reasons about optimal interventions, and
executes engine commands in a closed feedback loop.

Architecture:
  AgentEngineFusionLoop (Singleton)
    |-- EngineStateObserver   -> captures engine snapshots as perceptions
    |-- GoalSynthesizer       -> generates autonomous goals from engine state
    |-- FusionReasoner        -> selects reasoning mode based on context
    |-- ActionTranslator      -> converts agent decisions to engine commands
    |-- OutcomeEvaluator      -> measures the impact of agent interventions
    |-- FusionMemory          -> cross-session learning of effective strategies

Fusion Cycle (per tick):
  1. OBSERVE  -> Capture engine state snapshot (FPS, entities, metrics, events)
  2. PERCEIVE -> Convert snapshot to multi-modal perceptions for the agent
  3. SYNTHESIZE -> Generate autonomous goals from perceived anomalies
  4. REASON   -> Select and apply the best reasoning mode for the context
  5. ACT      -> Translate agent decisions into engine commands
  6. EVALUATE -> Measure outcome delta from previous snapshot
  7. LEARN    -> Store effective strategies in fusion memory

The loop runs at a configurable frequency (default 10Hz) and is designed
to be non-blocking — each tick completes in <50ms to avoid frame stalls.

Thread-safe singleton: use get_instance().
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Deque, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Fusion Enums
# =============================================================================

class FusionPhase(Enum):
    """Phases of the fusion cycle."""
    OBSERVE = "observe"
    PERCEIVE = "perceive"
    SYNTHESIZE = "synthesize"
    REASON = "reason"
    ACT = "act"
    EVALUATE = "evaluate"
    LEARN = "learn"


class GoalType(Enum):
    """Types of autonomous goals the agent can generate."""
    PERFORMANCE_OPTIMIZE = "performance_optimize"
    ENTITY_BALANCE = "entity_balance"
    SCENE_ENRICH = "scene_enrich"
    PHYSICS_TUNE = "physics_tune"
    RENDER_OPTIMIZE = "render_optimize"
    SCENE_TRANSITION = "scene_transition"
    ANOMALY_RESOLVE = "anomaly_resolve"
    EXPLORATION = "exploration"


class AnomalyType(Enum):
    """Detected engine anomalies that trigger autonomous goals."""
    FPS_DROP = "fps_drop"
    HIGH_FRAME_TIME = "high_frame_time"
    ENTITY_OVERFLOW = "entity_overflow"
    MEMORY_PRESSURE = "memory_pressure"
    PHYSICS_INSTABILITY = "physics_instability"
    RENDER_BOTTLENECK = "render_bottleneck"
    SCENE_STAGNATION = "scene_stagnation"
    NONE = "none"


class ActionStatus(Enum):
    """Status of a fusion action."""
    PENDING = "pending"
    EXECUTING = "executing"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# =============================================================================
# Fusion Data Structures
# =============================================================================

@dataclass
class EngineSnapshot:
    """A captured snapshot of the engine state."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    timestamp: float = field(default_factory=time.time)
    fps: float = 0.0
    frame_time_ms: float = 0.0
    entity_count: int = 0
    draw_calls: int = 0
    physics_bodies: int = 0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: float = 0.0
    cpu_usage_percent: float = 0.0
    active_scene: str = ""
    active_systems: List[str] = field(default_factory=list)
    recent_events: List[str] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def delta_from(self, previous: "EngineSnapshot") -> "SnapshotDelta":
        """Compute delta from a previous snapshot."""
        return SnapshotDelta(
            fps_delta=self.fps - previous.fps,
            frame_time_delta=self.frame_time_ms - previous.frame_time_ms,
            entity_count_delta=self.entity_count - previous.entity_count,
            memory_delta=self.memory_usage_mb - previous.memory_usage_mb,
            gpu_delta=self.gpu_usage_percent - previous.gpu_usage_percent,
            cpu_delta=self.cpu_usage_percent - previous.cpu_usage_percent,
            draw_calls_delta=self.draw_calls - previous.draw_calls,
        )


@dataclass
class SnapshotDelta:
    """Delta between two engine snapshots."""
    fps_delta: float = 0.0
    frame_time_delta: float = 0.0
    entity_count_delta: int = 0
    memory_delta: float = 0.0
    gpu_delta: float = 0.0
    cpu_delta: float = 0.0
    draw_calls_delta: int = 0


@dataclass
class AutonomousGoal:
    """A goal generated autonomously by the agent from engine observations."""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    goal_type: GoalType = GoalType.EXPLORATION
    description: str = ""
    priority: float = 0.5
    anomaly: AnomalyType = AnomalyType.NONE
    trigger_metrics: Dict[str, float] = field(default_factory=dict)
    proposed_actions: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    status: ActionStatus = ActionStatus.PENDING
    outcome_delta: Optional[SnapshotDelta] = None
    effectiveness_score: float = 0.0


@dataclass
class FusionAction:
    """A single action executed by the fusion loop."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    goal_id: str = ""
    engine_command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    status: ActionStatus = ActionStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    executed_at: float = 0.0
    duration_ms: float = 0.0


@dataclass
class FusionTickResult:
    """Result of a single fusion tick."""
    tick_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    phase: FusionPhase = FusionPhase.OBSERVE
    snapshot: Optional[EngineSnapshot] = None
    delta: Optional[SnapshotDelta] = None
    anomalies_detected: List[AnomalyType] = field(default_factory=list)
    goals_generated: List[AutonomousGoal] = field(default_factory=list)
    actions_executed: List[FusionAction] = field(default_factory=list)
    reasoning_mode: str = ""
    effectiveness: float = 0.0
    duration_s: float = 0.0
    cycle_count: int = 0


# =============================================================================
# Anomaly Detector
# =============================================================================

class AnomalyDetector:
    """Detects engine anomalies from snapshot data.

    Each anomaly type has specific threshold rules. When a metric crosses
    its threshold, the detector flags the anomaly and the fusion loop
    generates an autonomous goal to resolve it.
    """

    # Threshold configuration
    FPS_DROP_THRESHOLD = 45.0       # Below this FPS = anomaly
    FPS_DROP_DELTA = -10.0          # Sudden FPS drop of 10+ = anomaly
    FRAME_TIME_THRESHOLD = 25.0     # Above 25ms = anomaly
    ENTITY_OVERFLOW_THRESHOLD = 500 # More than 500 entities = anomaly
    MEMORY_PRESSURE_THRESHOLD = 800 # Above 800MB = anomaly
    GPU_PRESSURE_THRESHOLD = 90.0   # Above 90% GPU = anomaly
    CPU_PRESSURE_THRESHOLD = 85.0   # Above 85% CPU = anomaly
    STAGNATION_TICKS = 30           # No entity count change for 30 ticks

    def __init__(self) -> None:
        self._entity_count_history: Deque[int] = deque(maxlen=40)
        self._fps_history: Deque[float] = deque(maxlen=20)

    def detect(
        self,
        snapshot: EngineSnapshot,
        delta: Optional[SnapshotDelta] = None,
    ) -> List[AnomalyType]:
        """Detect anomalies from the current snapshot and delta."""
        anomalies: List[AnomalyType] = []

        # FPS drop detection
        self._fps_history.append(snapshot.fps)
        if snapshot.fps > 0 and snapshot.fps < self.FPS_DROP_THRESHOLD:
            anomalies.append(AnomalyType.FPS_DROP)
        elif delta and delta.fps_delta < self.FPS_DROP_DELTA:
            anomalies.append(AnomalyType.FPS_DROP)

        # High frame time
        if snapshot.frame_time_ms > self.FRAME_TIME_THRESHOLD:
            anomalies.append(AnomalyType.HIGH_FRAME_TIME)

        # Entity overflow
        self._entity_count_history.append(snapshot.entity_count)
        if snapshot.entity_count > self.ENTITY_OVERFLOW_THRESHOLD:
            anomalies.append(AnomalyType.ENTITY_OVERFLOW)

        # Memory pressure
        if snapshot.memory_usage_mb > self.MEMORY_PRESSURE_THRESHOLD:
            anomalies.append(AnomalyType.MEMORY_PRESSURE)

        # GPU bottleneck
        if snapshot.gpu_usage_percent > self.GPU_PRESSURE_THRESHOLD:
            anomalies.append(AnomalyType.RENDER_BOTTLENECK)

        # Physics instability (high CPU with low FPS)
        if (
            snapshot.cpu_usage_percent > self.CPU_PRESSURE_THRESHOLD
            and snapshot.fps > 0
            and snapshot.fps < 50.0
        ):
            anomalies.append(AnomalyType.PHYSICS_INSTABILITY)

        # Scene stagnation (entity count hasn't changed for N ticks)
        if len(self._entity_count_history) >= self.STAGNATION_TICKS:
            recent = list(self._entity_count_history)[-self.STAGNATION_TICKS:]
            if len(set(recent)) == 1 and recent[0] > 0:
                anomalies.append(AnomalyType.SCENE_STAGNATION)

        return anomalies


# =============================================================================
# Goal Synthesizer
# =============================================================================

class GoalSynthesizer:
    """Generates autonomous goals from detected anomalies.

    Each anomaly type maps to a goal type and a set of proposed actions.
    The synthesizer prioritizes goals based on anomaly severity and the
    agent's past effectiveness with similar goals.
    """

    def __init__(self) -> None:
        self._goal_history: Deque[AutonomousGoal] = deque(maxlen=100)
        self._effectiveness_by_type: Dict[GoalType, float] = {}

    def synthesize(
        self,
        anomalies: List[AnomalyType],
        snapshot: EngineSnapshot,
    ) -> List[AutonomousGoal]:
        """Generate autonomous goals from detected anomalies."""
        goals: List[AutonomousGoal] = []

        for anomaly in anomalies:
            goal = self._create_goal_for_anomaly(anomaly, snapshot)
            if goal:
                # Adjust priority based on past effectiveness
                past_score = self._effectiveness_by_type.get(goal.goal_type, 0.5)
                goal.priority = min(1.0, goal.priority * (0.5 + past_score))
                goals.append(goal)

        # If no anomalies, occasionally generate exploration goals
        if not goals and snapshot.entity_count > 0:
            goals.append(AutonomousGoal(
                goal_type=GoalType.EXPLORATION,
                description="Observe and gather engine intelligence",
                priority=0.1,
                anomaly=AnomalyType.NONE,
                trigger_metrics={"entity_count": float(snapshot.entity_count)},
            ))

        # Sort by priority descending
        goals.sort(key=lambda g: g.priority, reverse=True)
        return goals

    def _create_goal_for_anomaly(
        self,
        anomaly: AnomalyType,
        snapshot: EngineSnapshot,
    ) -> Optional[AutonomousGoal]:
        """Create a specific goal for a detected anomaly."""
        if anomaly == AnomalyType.FPS_DROP:
            return AutonomousGoal(
                goal_type=GoalType.PERFORMANCE_OPTIMIZE,
                description=f"Restore FPS from {snapshot.fps:.1f} to 60",
                priority=0.9,
                anomaly=anomaly,
                trigger_metrics={"fps": snapshot.fps, "frame_time": snapshot.frame_time_ms},
                proposed_actions=[
                    {"command": "optimize_rendering", "params": {"target_fps": 60}},
                    {"command": "tune_physics", "params": {"quality": "low"}},
                ],
            )
        elif anomaly == AnomalyType.HIGH_FRAME_TIME:
            return AutonomousGoal(
                goal_type=GoalType.PERFORMANCE_OPTIMIZE,
                description=f"Reduce frame time from {snapshot.frame_time_ms:.1f}ms",
                priority=0.85,
                anomaly=anomaly,
                trigger_metrics={"frame_time": snapshot.frame_time_ms},
                proposed_actions=[
                    {"command": "optimize_rendering", "params": {"reduce_draw_calls": True}},
                ],
            )
        elif anomaly == AnomalyType.ENTITY_OVERFLOW:
            return AutonomousGoal(
                goal_type=GoalType.ENTITY_BALANCE,
                description=f"Reduce entity count from {snapshot.entity_count}",
                priority=0.8,
                anomaly=anomaly,
                trigger_metrics={"entity_count": float(snapshot.entity_count)},
                proposed_actions=[
                    {"command": "destroy_entity", "params": {"category": "particle", "batch": True}},
                ],
            )
        elif anomaly == AnomalyType.MEMORY_PRESSURE:
            return AutonomousGoal(
                goal_type=GoalType.PERFORMANCE_OPTIMIZE,
                description=f"Reduce memory from {snapshot.memory_usage_mb:.0f}MB",
                priority=0.85,
                anomaly=anomaly,
                trigger_metrics={"memory_mb": snapshot.memory_usage_mb},
                proposed_actions=[
                    {"command": "apply_config", "params": {"resource_cache": "aggressive"}},
                ],
            )
        elif anomaly == AnomalyType.RENDER_BOTTLENECK:
            return AutonomousGoal(
                goal_type=GoalType.RENDER_OPTIMIZE,
                description=f"Reduce GPU load from {snapshot.gpu_usage_percent:.0f}%",
                priority=0.8,
                anomaly=anomaly,
                trigger_metrics={"gpu_percent": snapshot.gpu_usage_percent},
                proposed_actions=[
                    {"command": "optimize_rendering", "params": {"lod_bias": "aggressive"}},
                ],
            )
        elif anomaly == AnomalyType.PHYSICS_INSTABILITY:
            return AutonomousGoal(
                goal_type=GoalType.PHYSICS_TUNE,
                description="Stabilize physics simulation",
                priority=0.75,
                anomaly=anomaly,
                trigger_metrics={"cpu_percent": snapshot.cpu_usage_percent, "fps": snapshot.fps},
                proposed_actions=[
                    {"command": "tune_physics", "params": {"quality": "low", "fixed_timestep": True}},
                ],
            )
        elif anomaly == AnomalyType.SCENE_STAGNATION:
            return AutonomousGoal(
                goal_type=GoalType.SCENE_ENRICH,
                description="Enrich stagnant scene with new content",
                priority=0.5,
                anomaly=anomaly,
                trigger_metrics={"entity_count": float(snapshot.entity_count)},
                proposed_actions=[
                    {"command": "spawn_entity", "params": {"category": "npc", "count": 3}},
                    {"command": "generate_terrain", "params": {"region": "expansion"}},
                ],
            )
        return None

    def record_outcome(self, goal: AutonomousGoal) -> None:
        """Record the outcome of a goal for future prioritization."""
        self._goal_history.append(goal)
        # Update rolling effectiveness score
        gtype = goal.goal_type
        current = self._effectiveness_by_type.get(gtype, 0.5)
        # Exponential moving average
        alpha = 0.3
        self._effectiveness_by_type[gtype] = (
            alpha * goal.effectiveness_score + (1 - alpha) * current
        )


# =============================================================================
# Fusion Reasoner
# =============================================================================

class FusionReasoner:
    """Selects the optimal reasoning mode based on the fusion context.

    Instead of always using chain-of-thought, the reasoner dynamically
    selects between deductive, inductive, causal, and heuristic modes
    based on the type of anomaly and the available data.
    """

    def __init__(self) -> None:
        self._mode_usage: Dict[str, int] = {}

    def select_mode(
        self,
        anomalies: List[AnomalyType],
        goals: List[AutonomousGoal],
    ) -> str:
        """Select the best reasoning mode for the current context."""
        if not anomalies or not goals:
            mode = "heuristic"
        elif AnomalyType.FPS_DROP in anomalies or AnomalyType.HIGH_FRAME_TIME in anomalies:
            # Performance issues need causal reasoning (root cause analysis)
            mode = "causal_reasoning"
        elif AnomalyType.SCENE_STAGNATION in anomalies:
            # Stagnation needs creative/inductive reasoning
            mode = "inductive"
        elif AnomalyType.ENTITY_OVERFLOW in anomalies:
            # Overflow needs deductive reasoning (apply known constraints)
            mode = "deductive"
        elif len(anomalies) > 2:
            # Multiple anomalies need meta-reasoning (prioritize)
            mode = "meta_reasoning"
        else:
            mode = "chain_of_thought"

        self._mode_usage[mode] = self._mode_usage.get(mode, 0) + 1
        return mode

    def mode_stats(self) -> Dict[str, int]:
        return dict(self._mode_usage)


# =============================================================================
# Agent-Engine Fusion Loop
# =============================================================================

class AgentEngineFusionLoop:
    """
    The singleton fusion loop that tightly couples the AgentKernel with
    the AINativeEngineCore in a real-time bidirectional feedback cycle.

    The loop observes the engine, generates autonomous goals, reasons
    about interventions, executes engine commands, and learns from
    outcomes — all without human intervention.
    """

    _instance: Optional["AgentEngineFusionLoop"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._anomaly_detector = AnomalyDetector()
        self._goal_synthesizer = GoalSynthesizer()
        self._fusion_reasoner = FusionReasoner()

        # Fusion state
        self._active: bool = False
        self._tick_frequency_hz: float = 10.0  # 10 Hz default
        self._cycle_count: int = 0
        self._last_snapshot: Optional[EngineSnapshot] = None
        self._tick_history: Deque[FusionTickResult] = deque(maxlen=200)
        self._active_goals: Dict[str, AutonomousGoal] = {}
        self._action_history: Deque[FusionAction] = deque(maxlen=300)

        # Statistics
        self._total_anomalies_detected: int = 0
        self._total_goals_generated: int = 0
        self._total_actions_executed: int = 0
        self._total_successful_actions: int = 0
        self._total_failed_actions: int = 0
        self._total_ticks: int = 0
        self._total_effective_interventions: int = 0

        # Engine and agent references (lazy-initialized)
        self._engine_core: Optional[Any] = None
        self._agent_kernel: Optional[Any] = None
        self._fusion_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

    @classmethod
    def get_instance(cls) -> "AgentEngineFusionLoop":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start(self, frequency_hz: float = 10.0) -> bool:
        """Start the fusion loop at the given frequency."""
        with self._lock:
            if self._active:
                return True
            self._tick_frequency_hz = frequency_hz
            self._stop_event.clear()
            self._active = True
            self._fusion_thread = threading.Thread(
                target=self._run_loop, daemon=True, name="fusion-loop"
            )
            self._fusion_thread.start()
            logger.info("Agent-Engine fusion loop started at %.1f Hz", frequency_hz)
            return True

    def stop(self) -> bool:
        """Stop the fusion loop."""
        with self._lock:
            if not self._active:
                return True
            self._stop_event.set()
            self._active = False
            if self._fusion_thread and self._fusion_thread.is_alive():
                self._fusion_thread.join(timeout=2.0)
            logger.info("Agent-Engine fusion loop stopped")
            return True

    @property
    def is_active(self) -> bool:
        return self._active

    # -------------------------------------------------------------------------
    # Engine / Agent connections
    # -------------------------------------------------------------------------

    def _get_engine_core(self) -> Optional[Any]:
        """Get the AINativeEngineCore singleton."""
        if self._engine_core is not None:
            return self._engine_core
        try:
            from sparkai.engine.engine_ai_native_core import AINativeEngineCore
            self._engine_core = AINativeEngineCore.get_instance()
            return self._engine_core
        except Exception as e:
            logger.debug("Engine core not available: %s", e)
            return None

    def _get_agent_kernel(self) -> Optional[Any]:
        """Get the AgentKernel singleton."""
        if self._agent_kernel is not None:
            return self._agent_kernel
        try:
            from sparkai.agent.agent_unified_kernel import AgentKernel
            self._agent_kernel = AgentKernel.get_instance()
            return self._agent_kernel
        except Exception as e:
            logger.debug("Agent kernel not available: %s", e)
            return None

    # -------------------------------------------------------------------------
    # Main fusion loop
    # -------------------------------------------------------------------------

    def _run_loop(self) -> None:
        """The main fusion loop thread."""
        interval = 1.0 / self._tick_frequency_hz
        while not self._stop_event.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.warning("Fusion tick error: %s", e)
            self._stop_event.wait(interval)

    def tick(self) -> FusionTickResult:
        """Execute one fusion tick: observe → perceive → synthesize → reason → act → evaluate → learn."""
        start = time.time()
        result = FusionTickResult()
        result.cycle_count = self._cycle_count
        self._cycle_count += 1
        self._total_ticks += 1

        # Phase 1: OBSERVE - capture engine snapshot
        snapshot = self._capture_snapshot()
        result.snapshot = snapshot

        # Compute delta from last snapshot
        delta = None
        if self._last_snapshot:
            delta = snapshot.delta_from(self._last_snapshot)
        result.delta = delta

        # Phase 2: PERCEIVE - detect anomalies
        anomalies = self._anomaly_detector.detect(snapshot, delta)
        result.anomalies_detected = anomalies
        self._total_anomalies_detected += len(anomalies)

        # Phase 3: SYNTHESIZE - generate autonomous goals
        goals = self._goal_synthesizer.synthesize(anomalies, snapshot)
        result.goals_generated = goals
        self._total_goals_generated += len(goals)

        # Register new goals
        for goal in goals:
            self._active_goals[goal.goal_id] = goal

        # Phase 4: REASON - select reasoning mode
        reasoning_mode = self._fusion_reasoner.select_mode(anomalies, goals)
        result.reasoning_mode = reasoning_mode

        # Feed perceptions to agent kernel if available
        self._feed_perceptions_to_agent(snapshot, anomalies, reasoning_mode)

        # Phase 5: ACT - execute highest-priority goal actions
        actions = self._execute_goal_actions(goals, snapshot)
        result.actions_executed = actions
        self._total_actions_executed += len(actions)
        for action in actions:
            self._action_history.append(action)
            if action.status == ActionStatus.SUCCESS:
                self._total_successful_actions += 1
            elif action.status == ActionStatus.FAILED:
                self._total_failed_actions += 1

        # Phase 6: EVALUATE - measure outcome
        if actions and self._last_snapshot:
            effectiveness = self._evaluate_outcome(actions, snapshot, delta)
            result.effectiveness = effectiveness
            if effectiveness > 0.3:
                self._total_effective_interventions += 1

            # Update goal outcomes
            for goal in goals:
                if goal.status == ActionStatus.SUCCESS:
                    goal.outcome_delta = delta
                    goal.effectiveness_score = effectiveness
                    self._goal_synthesizer.record_outcome(goal)

        # Phase 7: LEARN - store in fusion memory
        self._store_fusion_memory(snapshot, anomalies, goals, actions, reasoning_mode)

        # Update state
        self._last_snapshot = snapshot
        result.phase = FusionPhase.LEARN
        result.duration_s = time.time() - start

        # Store tick result
        with self._lock:
            self._tick_history.append(result)

        return result

    # -------------------------------------------------------------------------
    # Snapshot capture
    # -------------------------------------------------------------------------

    def _capture_snapshot(self) -> EngineSnapshot:
        """Capture a snapshot of the current engine state."""
        engine = self._get_engine_core()
        if not engine:
            return self._simulated_snapshot()

        try:
            from sparkai.engine.engine_ai_native_core import EngineCommand
            result = engine.execute_command(EngineCommand.GET_STATE)
            if result.success and result.data:
                data = result.data
                entity_count = data.get("entity_count", 0)
                active_scene = data.get("active_scene", "")
                # When the engine has no active scene or entities, it is idle.
                # Use simulated data so the fusion loop can still exercise its
                # anomaly detection and goal generation pathways.
                if not active_scene and entity_count == 0:
                    return self._simulated_snapshot()
                return EngineSnapshot(
                    fps=data.get("fps", 60.0),
                    frame_time_ms=data.get("frame_time_ms", 16.6),
                    entity_count=entity_count,
                    draw_calls=data.get("draw_calls", 0),
                    physics_bodies=data.get("physics_bodies", 0),
                    memory_usage_mb=data.get("memory_usage_mb", 0.0),
                    gpu_usage_percent=data.get("gpu_usage_percent", 0.0),
                    cpu_usage_percent=data.get("cpu_usage_percent", 0.0),
                    active_scene=active_scene,
                    active_systems=data.get("active_systems", []),
                    recent_events=data.get("recent_events", []),
                    performance_metrics=data.get("performance_metrics", {}),
                )
        except Exception as e:
            logger.debug("Snapshot capture failed: %s", e)

        return self._simulated_snapshot()

    def _simulated_snapshot(self) -> EngineSnapshot:
        """Generate a simulated snapshot for testing without a live engine."""
        import random as _r
        base_fps = 60.0
        entity_count = _r.randint(10, 80)
        memory_mb = _r.uniform(50, 200)
        gpu = _r.uniform(20, 70)
        cpu = _r.uniform(15, 60)

        # Simulate periodic anomalies to exercise the full fusion cycle
        cycle_mod = self._cycle_count % 20
        if cycle_mod == 5:
            # FPS drop anomaly
            base_fps = _r.uniform(25.0, 40.0)
        elif cycle_mod == 12:
            # High entity count anomaly
            entity_count = _r.randint(300, 600)
        elif cycle_mod == 17:
            # Memory pressure anomaly
            memory_mb = _r.uniform(850, 1200)

        return EngineSnapshot(
            fps=base_fps + _r.uniform(-3, 3),
            frame_time_ms=1000.0 / max(1.0, base_fps) + _r.uniform(-2, 2),
            entity_count=entity_count,
            draw_calls=_r.randint(5, 30),
            physics_bodies=_r.randint(5, 20),
            memory_usage_mb=memory_mb,
            gpu_usage_percent=gpu,
            cpu_usage_percent=cpu,
            active_scene="main",
            active_systems=["render", "physics", "audio"],
        )

    # -------------------------------------------------------------------------
    # Agent perception feeding
    # -------------------------------------------------------------------------

    def _feed_perceptions_to_agent(
        self,
        snapshot: EngineSnapshot,
        anomalies: List[AnomalyType],
        reasoning_mode: str,
    ) -> None:
        """Feed engine state as perceptions to the agent kernel."""
        kernel = self._get_agent_kernel()
        if not kernel:
            return

        try:
            salience_metric = 0.8 if anomalies else 0.3
            salience_event = 0.9 if anomalies else 0.2

            # Feed numeric metrics as a perception
            if hasattr(kernel, "perceive"):
                kernel.perceive(
                    source="engine_metric",
                    channel="numeric",
                    payload={
                        "fps": snapshot.fps,
                        "frame_time_ms": snapshot.frame_time_ms,
                        "entity_count": snapshot.entity_count,
                        "memory_mb": snapshot.memory_usage_mb,
                        "gpu_percent": snapshot.gpu_usage_percent,
                    },
                    salience=salience_metric,
                )
                # Feed anomaly events as a perception
                kernel.perceive(
                    source="engine_event",
                    channel="event",
                    payload={
                        "anomalies": [a.value for a in anomalies],
                        "active_scene": snapshot.active_scene,
                        "active_systems": snapshot.active_systems,
                        "reasoning_mode": reasoning_mode,
                    },
                    salience=salience_event,
                )
        except Exception as e:
            logger.debug("Feed perceptions failed: %s", e)

    # -------------------------------------------------------------------------
    # Goal action execution
    # -------------------------------------------------------------------------

    def _execute_goal_actions(
        self,
        goals: List[AutonomousGoal],
        snapshot: EngineSnapshot,
    ) -> List[FusionAction]:
        """Execute the proposed actions for the highest-priority goals."""
        actions: List[FusionAction] = []
        engine = self._get_engine_core()

        # Only execute top 3 goals per tick to avoid flooding
        for goal in goals[:3]:
            goal.status = ActionStatus.EXECUTING
            for proposed in goal.proposed_actions:
                action = FusionAction(
                    goal_id=goal.goal_id,
                    engine_command=proposed.get("command", ""),
                    params=proposed.get("params", {}),
                )

                start = time.time()
                try:
                    if engine:
                        result = self._dispatch_engine_command(
                            engine, proposed.get("command", ""), proposed.get("params", {})
                        )
                        action.result = result
                        action.status = ActionStatus.SUCCESS if (
                            result and result.get("success", True)
                        ) else ActionStatus.FAILED
                    else:
                        # Simulated execution
                        action.result = {"success": True, "simulated": True}
                        action.status = ActionStatus.SUCCESS

                except Exception as e:
                    action.result = {"error": str(e)}
                    action.status = ActionStatus.FAILED
                    logger.debug("Action failed: %s", e)

                action.executed_at = start
                action.duration_ms = (time.time() - start) * 1000
                actions.append(action)

            # Update goal status
            if any(a.status == ActionStatus.SUCCESS for a in actions if a.goal_id == goal.goal_id):
                goal.status = ActionStatus.SUCCESS
            elif all(a.status == ActionStatus.FAILED for a in actions if a.goal_id == goal.goal_id):
                goal.status = ActionStatus.FAILED

        return actions

    def _dispatch_engine_command(
        self,
        engine: Any,
        command_name: str,
        params: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Dispatch a command to the engine core."""
        try:
            from sparkai.engine.engine_ai_native_core import EngineCommand

            # Map string command names to EngineCommand enum values
            command_map = {
                "create_scene": EngineCommand.CREATE_SCENE,
                "load_scene": EngineCommand.LOAD_SCENE,
                "spawn_entity": EngineCommand.SPAWN_ENTITY,
                "destroy_entity": EngineCommand.DESTROY_ENTITY,
                "set_component": EngineCommand.SET_COMPONENT,
                "get_component": EngineCommand.GET_COMPONENT,
                "execute_script": EngineCommand.EXECUTE_SCRIPT,
                "capture_frame": EngineCommand.CAPTURE_FRAME,
                "get_state": EngineCommand.GET_STATE,
                "apply_config": EngineCommand.APPLY_CONFIG,
                "start_profiling": EngineCommand.START_PROFILING,
                "stop_profiling": EngineCommand.STOP_PROFILING,
                "optimize_rendering": EngineCommand.OPTIMIZE_RENDERING,
                "tune_physics": EngineCommand.TUNE_PHYSICS,
                "generate_terrain": EngineCommand.GENERATE_TERRAIN,
                "generate_world": EngineCommand.GENERATE_WORLD,
                "simulate_tick": EngineCommand.SIMULATE_TICK,
                "reset_simulation": EngineCommand.RESET_SIMULATION,
            }

            cmd = command_map.get(command_name)
            if cmd is None:
                return {"success": False, "error": f"Unknown command: {command_name}"}

            result = engine.execute_command(cmd, params)
            return {"success": result.success, "data": result.data, "error": result.error}

        except Exception as e:
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Outcome evaluation
    # -------------------------------------------------------------------------

    def _evaluate_outcome(
        self,
        actions: List[FusionAction],
        snapshot: EngineSnapshot,
        delta: Optional[SnapshotDelta],
    ) -> float:
        """Evaluate the effectiveness of executed actions.

        Returns a score from -1.0 (made things worse) to +1.0 (major improvement).
        """
        if not delta:
            return 0.0

        score = 0.0

        # FPS improvement is the primary metric
        if delta.fps_delta > 0:
            score += min(0.5, delta.fps_delta / 20.0)
        elif delta.fps_delta < 0:
            score += max(-0.3, delta.fps_delta / 20.0)

        # Frame time reduction
        if delta.frame_time_delta < 0:
            score += min(0.2, abs(delta.frame_time_delta) / 10.0)
        elif delta.frame_time_delta > 0:
            score += max(-0.2, -delta.frame_time_delta / 10.0)

        # Memory reduction
        if delta.memory_delta < 0:
            score += min(0.15, abs(delta.memory_delta) / 100.0)

        # Entity count management
        if delta.entity_count_delta < 0 and snapshot.entity_count > 200:
            score += 0.1

        # Check if actions succeeded
        successful = sum(1 for a in actions if a.status == ActionStatus.SUCCESS)
        if successful > 0:
            score += 0.1 * successful / max(1, len(actions))

        return max(-1.0, min(1.0, score))

    # -------------------------------------------------------------------------
    # Fusion memory
    # -------------------------------------------------------------------------

    def _store_fusion_memory(
        self,
        snapshot: EngineSnapshot,
        anomalies: List[AnomalyType],
        goals: List[AutonomousGoal],
        actions: List[FusionAction],
        reasoning_mode: str,
    ) -> None:
        """Store fusion outcomes for cross-session learning."""
        try:
            from sparkai.agent.agent_memory_orchestrator import AgentMemoryOrchestrator
            memory = AgentMemoryOrchestrator.get_instance()

            # Only store when there were meaningful events
            if not anomalies and not actions:
                return

            context = {
                "type": "fusion_outcome",
                "cycle": self._cycle_count,
                "fps": snapshot.fps,
                "frame_time_ms": snapshot.frame_time_ms,
                "entity_count": snapshot.entity_count,
                "anomalies": [a.value for a in anomalies],
                "goals": [
                    {
                        "type": g.goal_type.value,
                        "priority": g.priority,
                        "status": g.status.value,
                        "effectiveness": g.effectiveness_score,
                    }
                    for g in goals
                ],
                "actions_count": len(actions),
                "successful_actions": sum(1 for a in actions if a.status == ActionStatus.SUCCESS),
                "reasoning_mode": reasoning_mode,
            }

            memory.store_memory(
                category="fusion",
                content=context,
                tags=["fusion", reasoning_mode] + [a.value for a in anomalies],
            )
        except Exception as e:
            logger.debug("Fusion memory store failed: %s", e)

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Get the fusion loop status."""
        with self._lock:
            recent_ticks = list(self._tick_history)[-10:]
            avg_duration = (
                sum(t.duration_s for t in recent_ticks) / len(recent_ticks)
                if recent_ticks else 0.0
            )
            success_rate = (
                self._total_successful_actions / max(1, self._total_actions_executed)
            )
            return {
                "active": self._active,
                "frequency_hz": self._tick_frequency_hz,
                "cycle_count": self._cycle_count,
                "total_ticks": self._total_ticks,
                "total_anomalies_detected": self._total_anomalies_detected,
                "total_goals_generated": self._total_goals_generated,
                "total_actions_executed": self._total_actions_executed,
                "total_successful_actions": self._total_successful_actions,
                "total_failed_actions": self._total_failed_actions,
                "total_effective_interventions": self._total_effective_interventions,
                "action_success_rate": round(success_rate, 3),
                "avg_tick_duration_s": round(avg_duration, 4),
                "active_goals": len(self._active_goals),
                "reasoning_mode_stats": self._fusion_reasoner.mode_stats(),
                "last_snapshot": (
                    {
                        "fps": self._last_snapshot.fps,
                        "frame_time_ms": self._last_snapshot.frame_time_ms,
                        "entity_count": self._last_snapshot.entity_count,
                        "memory_mb": self._last_snapshot.memory_usage_mb,
                        "gpu_percent": self._last_snapshot.gpu_usage_percent,
                    }
                    if self._last_snapshot else None
                ),
            }

    def get_recent_ticks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fusion tick results."""
        with self._lock:
            ticks = list(self._tick_history)[-limit:]
        return [
            {
                "tick_id": t.tick_id,
                "cycle_count": t.cycle_count,
                "phase": t.phase.value,
                "fps": t.snapshot.fps if t.snapshot else 0.0,
                "anomalies": [a.value for a in t.anomalies_detected],
                "goals_count": len(t.goals_generated),
                "actions_count": len(t.actions_executed),
                "reasoning_mode": t.reasoning_mode,
                "effectiveness": round(t.effectiveness, 3),
                "duration_s": round(t.duration_s, 4),
            }
            for t in ticks
        ]

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get currently active goals."""
        with self._lock:
            return [
                {
                    "goal_id": g.goal_id,
                    "type": g.goal_type.value,
                    "description": g.description,
                    "priority": round(g.priority, 3),
                    "anomaly": g.anomaly.value,
                    "status": g.status.value,
                    "effectiveness": round(g.effectiveness_score, 3),
                    "proposed_actions": g.proposed_actions,
                }
                for g in self._active_goals.values()
            ]

    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent fusion actions."""
        with self._lock:
            actions = list(self._action_history)[-limit:]
        return [
            {
                "action_id": a.action_id,
                "goal_id": a.goal_id,
                "command": a.engine_command,
                "params": a.params,
                "status": a.status.value,
                "duration_ms": round(a.duration_ms, 2),
                "result": a.result,
            }
            for a in actions
        ]

    def reset(self) -> None:
        """Reset the fusion loop state."""
        with self._lock:
            self._cycle_count = 0
            self._total_ticks = 0
            self._total_anomalies_detected = 0
            self._total_goals_generated = 0
            self._total_actions_executed = 0
            self._total_successful_actions = 0
            self._total_failed_actions = 0
            self._total_effective_interventions = 0
            self._tick_history.clear()
            self._active_goals.clear()
            self._action_history.clear()
            self._last_snapshot = None
            self._anomaly_detector = AnomalyDetector()
            self._goal_synthesizer = GoalSynthesizer()
            self._fusion_reasoner = FusionReasoner()


# =============================================================================
# Module-level convenience functions
# =============================================================================

def get_fusion_loop() -> AgentEngineFusionLoop:
    """Get the singleton fusion loop instance."""
    return AgentEngineFusionLoop.get_instance()


def run_fusion_tick() -> FusionTickResult:
    """Run a single fusion tick."""
    return get_fusion_loop().tick()
