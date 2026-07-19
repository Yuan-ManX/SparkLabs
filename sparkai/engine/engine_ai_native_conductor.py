"""
SparkLabs - AI-Native Engine Conductor

A unified conductor that bridges the cognitive kernel with the engine's
physics, rendering, and scene subsystems. The conductor translates brain
directives and kernel decisions into concrete engine adjustments, closing
the loop between cognition and runtime.

Core responsibilities:
  1. Physics Conductor - predict, tune, and resolve physics scenarios using
     the kernel's reasoning engine and the brain's player model.
  2. Render Conductor - adaptively adjust rendering quality, effects, and
     post-processing based on player state, pacing, and performance headroom.
  3. Scene Conductor - dynamically compose, modify, and orchestrate scenes
     based on narrative beats, emergence signals, and player progression.
  4. Conductor Cycle - a single tick that runs observe → analyze → adjust →
     verify, producing a ConductorDecision with applied adjustments.
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ConductorPhase(Enum):
    """Phases of a single conductor cycle."""
    OBSERVE = "observe"
    ANALYZE = "analyze"
    ADJUST = "adjust"
    VERIFY = "verify"


class PhysicsAdjustmentKind(Enum):
    """Kinds of physics adjustments the conductor can make."""
    TUNE_GRAVITY = "tune_gravity"
    TUNE_FRICTION = "tune_friction"
    TUNE_RESTITUTION = "tune_restitution"
    TUNE_DAMPING = "tune_damping"
    RESOLVE_PENETRATION = "resolve_penetration"
    ADJUST_TIMESTEP = "adjust_timestep"
    FREEZE_REGION = "freeze_region"


class RenderAdjustmentKind(Enum):
    """Kinds of render adjustments the conductor can make."""
    SET_QUALITY_LEVEL = "set_quality_level"
    TOGGLE_POST_PROCESSING = "toggle_post_processing"
    ADAPT_RESOLUTION_SCALE = "adapt_resolution_scale"
    ADJUST_PARTICLE_DENSITY = "adjust_particle_density"
    TOGGLE_SHADOWS = "toggle_shadows"
    ADJUST_LOD_BIAS = "adjust_lod_bias"
    SET_VFX_INTENSITY = "set_vfx_intensity"


class SceneAdjustmentKind(Enum):
    """Kinds of scene adjustments the conductor can make."""
    SPAWN_ENTITY = "spawn_entity"
    DESPAWN_ENTITY = "despawn_entity"
    MOVE_ENTITY = "move_entity"
    SET_LIGHTING = "set_lighting"
    SET_WEATHER = "set_weather"
    TRIGGER_EVENT = "trigger_event"
    TRANSITION_SCENE = "transition_scene"
    SET_AMBIENCE = "set_ambience"


class QualityLevel(Enum):
    """Rendering quality levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PhysicsState:
    """A snapshot of the physics system state."""
    body_count: int = 0
    active_body_count: int = 0
    collision_count: int = 0
    penetration_count: int = 0
    avg_velocity: float = 0.0
    max_velocity: float = 0.0
    gravity: float = 9.8
    friction: float = 0.5
    restitution: float = 0.3
    timestep: float = 0.016
    stability_score: float = 1.0     # 0..1, lower means unstable


@dataclass
class RenderState:
    """A snapshot of the render system state."""
    fps: float = 60.0
    frame_time_ms: float = 16.6
    draw_calls: int = 0
    triangles: int = 0
    quality_level: QualityLevel = QualityLevel.HIGH
    resolution_scale: float = 1.0
    particle_density: float = 1.0
    shadows_enabled: bool = True
    post_processing_enabled: bool = True
    lod_bias: float = 1.0
    vfx_intensity: float = 1.0
    gpu_utilization: float = 0.0


@dataclass
class SceneState:
    """A snapshot of the scene state."""
    entity_count: int = 0
    active_entity_count: int = 0
    scene_name: str = ""
    lighting_preset: str = "default"
    weather_preset: str = "clear"
    ambience_preset: str = "neutral"
    player_position: Tuple[float, float] = (0.0, 0.0)
    camera_position: Tuple[float, float] = (0.0, 0.0)
    narrative_beat: str = ""
    emergence_signals: int = 0


@dataclass
class PhysicsAdjustment:
    """A single physics adjustment."""
    adjustment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: PhysicsAdjustmentKind = PhysicsAdjustmentKind.TUNE_GRAVITY
    target: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    applied: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class RenderAdjustment:
    """A single render adjustment."""
    adjustment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: RenderAdjustmentKind = RenderAdjustmentKind.SET_QUALITY_LEVEL
    target: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    applied: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class SceneAdjustment:
    """A single scene adjustment."""
    adjustment_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    kind: SceneAdjustmentKind = SceneAdjustmentKind.SPAWN_ENTITY
    target: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    applied: bool = False
    timestamp: float = field(default_factory=time.time)


@dataclass
class ConductorDecision:
    """The outcome of one conductor cycle."""
    cycle_id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    phase: ConductorPhase = ConductorPhase.OBSERVE
    physics_adjustments: List[PhysicsAdjustment] = field(default_factory=list)
    render_adjustments: List[RenderAdjustment] = field(default_factory=list)
    scene_adjustments: List[SceneAdjustment] = field(default_factory=list)
    duration_s: float = 0.0
    notes: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Physics Conductor
# ---------------------------------------------------------------------------

class PhysicsConductor:
    """Predicts, tunes, and resolves physics scenarios using the kernel."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_state: PhysicsState = PhysicsState()
        self._history: Deque[PhysicsState] = deque(maxlen=32)
        self._adjustment_history: Deque[PhysicsAdjustment] = deque(maxlen=64)
        self._stability_threshold = 0.5
        self._penetration_threshold = 5

    def update_state(self, state: PhysicsState) -> None:
        """Update the current physics state snapshot."""
        with self._lock:
            self._history.append(self._current_state)
            self._current_state = state

    def analyze(self) -> List[PhysicsAdjustment]:
        """Analyze the current state and propose adjustments."""
        with self._lock:
            state = self._current_state

        adjustments: List[PhysicsAdjustment] = []

        # Check for instability
        if state.stability_score < self._stability_threshold:
            adjustments.append(PhysicsAdjustment(
                kind=PhysicsAdjustmentKind.ADJUST_TIMESTEP,
                target="physics_world",
                args={"timestep": max(0.008, state.timestep * 0.5)},
                rationale=f"stability_score={state.stability_score:.2f} below threshold",
            ))
            adjustments.append(PhysicsAdjustment(
                kind=PhysicsAdjustmentKind.TUNE_DAMPING,
                target="physics_world",
                args={"damping": 0.9},
                rationale="increase damping to stabilize bodies",
            ))

        # Check for penetration issues
        if state.penetration_count > self._penetration_threshold:
            adjustments.append(PhysicsAdjustment(
                kind=PhysicsAdjustmentKind.RESOLVE_PENETRATION,
                target="collision_solver",
                args={"iterations": 8, "bias": 0.2},
                rationale=f"{state.penetration_count} penetrations detected",
            ))

        # Check for excessive velocities
        if state.max_velocity > 50.0:
            adjustments.append(PhysicsAdjustment(
                kind=PhysicsAdjustmentKind.TUNE_FRICTION,
                target="physics_world",
                args={"friction": min(1.0, state.friction + 0.1)},
                rationale=f"max_velocity={state.max_velocity:.1f} too high",
            ))

        # Adaptive gravity based on body count (more bodies = gentler gravity)
        if state.active_body_count > 50:
            target_gravity = max(5.0, state.gravity * 0.9)
            if abs(state.gravity - target_gravity) > 0.5:
                adjustments.append(PhysicsAdjustment(
                    kind=PhysicsAdjustmentKind.TUNE_GRAVITY,
                    target="physics_world",
                    args={"gravity": target_gravity},
                    rationale=f"reduce gravity for {state.active_body_count} active bodies",
                ))

        return adjustments

    def apply(self, adjustment: PhysicsAdjustment) -> bool:
        """Apply a physics adjustment (simulated)."""
        adjustment.applied = True
        with self._lock:
            self._adjustment_history.append(adjustment)
            # Apply the adjustment to the current state
            if adjustment.kind == PhysicsAdjustmentKind.TUNE_GRAVITY:
                self._current_state.gravity = adjustment.args.get("gravity", self._current_state.gravity)
            elif adjustment.kind == PhysicsAdjustmentKind.TUNE_FRICTION:
                self._current_state.friction = adjustment.args.get("friction", self._current_state.friction)
            elif adjustment.kind == PhysicsAdjustmentKind.ADJUST_TIMESTEP:
                self._current_state.timestep = adjustment.args.get("timestep", self._current_state.timestep)
            elif adjustment.kind == PhysicsAdjustmentKind.TUNE_DAMPING:
                pass  # Damping is not tracked in state, just applied
        logger.info("Physics adjustment applied: %s -> %s", adjustment.kind.value, adjustment.target)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_state": {
                    "body_count": self._current_state.body_count,
                    "active_body_count": self._current_state.active_body_count,
                    "collision_count": self._current_state.collision_count,
                    "penetration_count": self._current_state.penetration_count,
                    "stability_score": round(self._current_state.stability_score, 3),
                    "gravity": round(self._current_state.gravity, 2),
                    "friction": round(self._current_state.friction, 2),
                    "timestep": round(self._current_state.timestep, 4),
                },
                "history_size": len(self._history),
                "adjustments_applied": len(self._adjustment_history),
            }


# ---------------------------------------------------------------------------
# Render Conductor
# ---------------------------------------------------------------------------

class RenderConductor:
    """Adaptively adjusts rendering based on player state and performance."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_state: RenderState = RenderState()
        self._history: Deque[RenderState] = deque(maxlen=32)
        self._adjustment_history: Deque[RenderAdjustment] = deque(maxlen=64)
        self._target_fps = 60.0
        self._fps_floor = 30.0
        self._fps_ceiling = 120.0
        self._gpu_utilization_ceiling = 0.9

    def update_state(self, state: RenderState) -> None:
        """Update the current render state snapshot."""
        with self._lock:
            self._history.append(self._current_state)
            self._current_state = state

    def analyze(self, player_mood: Optional[str] = None, pacing_zone: Optional[str] = None) -> List[RenderAdjustment]:
        """Analyze the current state and propose adjustments."""
        with self._lock:
            state = self._current_state

        adjustments: List[RenderAdjustment] = []

        # FPS-driven quality adaptation
        if state.fps < self._fps_floor:
            # Degrade quality
            if state.quality_level != QualityLevel.LOW:
                new_level = QualityLevel.LOW
                adjustments.append(RenderAdjustment(
                    kind=RenderAdjustmentKind.SET_QUALITY_LEVEL,
                    target="render_pipeline",
                    args={"level": new_level.value},
                    rationale=f"fps={state.fps:.1f} below floor {self._fps_floor}",
                ))
            adjustments.append(RenderAdjustment(
                kind=RenderAdjustmentKind.ADAPT_RESOLUTION_SCALE,
                target="render_pipeline",
                args={"scale": max(0.5, state.resolution_scale - 0.1)},
                rationale="reduce resolution scale to recover fps",
            ))
            if state.shadows_enabled:
                adjustments.append(RenderAdjustment(
                    kind=RenderAdjustmentKind.TOGGLE_SHADOWS,
                    target="render_pipeline",
                    args={"enabled": False},
                    rationale="disable shadows to recover fps",
                ))
        elif state.fps > self._fps_ceiling and state.quality_level != QualityLevel.ULTRA:
            # Upgrade quality
            upgrades = {
                QualityLevel.LOW: QualityLevel.MEDIUM,
                QualityLevel.MEDIUM: QualityLevel.HIGH,
                QualityLevel.HIGH: QualityLevel.ULTRA,
            }
            new_level = upgrades.get(state.quality_level, state.quality_level)
            if new_level != state.quality_level:
                adjustments.append(RenderAdjustment(
                    kind=RenderAdjustmentKind.SET_QUALITY_LEVEL,
                    target="render_pipeline",
                    args={"level": new_level.value},
                    rationale=f"fps={state.fps:.1f} above ceiling, upgrade quality",
                ))

        # GPU utilization ceiling
        if state.gpu_utilization > self._gpu_utilization_ceiling:
            adjustments.append(RenderAdjustment(
                kind=RenderAdjustmentKind.ADJUST_PARTICLE_DENSITY,
                target="particle_system",
                args={"density": max(0.3, state.particle_density - 0.2)},
                rationale=f"gpu_utilization={state.gpu_utilization:.2f} too high",
            ))

        # Player-mood-driven VFX intensity
        if player_mood == "frustrated":
            adjustments.append(RenderAdjustment(
                kind=RenderAdjustmentKind.SET_VFX_INTENSITY,
                target="vfx_system",
                args={"intensity": max(0.3, state.vfx_intensity - 0.2)},
                rationale="reduce VFX intensity for frustrated player",
            ))
        elif player_mood == "delighted":
            adjustments.append(RenderAdjustment(
                kind=RenderAdjustmentKind.SET_VFX_INTENSITY,
                target="vfx_system",
                args={"intensity": min(1.5, state.vfx_intensity + 0.2)},
                rationale="increase VFX intensity for delighted player",
            ))

        # Pacing-driven post-processing
        if pacing_zone == "peak" and not state.post_processing_enabled:
            adjustments.append(RenderAdjustment(
                kind=RenderAdjustmentKind.TOGGLE_POST_PROCESSING,
                target="render_pipeline",
                args={"enabled": True},
                rationale="enable post-processing for peak pacing zone",
            ))

        return adjustments

    def apply(self, adjustment: RenderAdjustment) -> bool:
        """Apply a render adjustment (simulated)."""
        adjustment.applied = True
        with self._lock:
            self._adjustment_history.append(adjustment)
            if adjustment.kind == RenderAdjustmentKind.SET_QUALITY_LEVEL:
                level_str = adjustment.args.get("level", "high")
                try:
                    self._current_state.quality_level = QualityLevel(level_str)
                except ValueError:
                    pass
            elif adjustment.kind == RenderAdjustmentKind.ADAPT_RESOLUTION_SCALE:
                self._current_state.resolution_scale = adjustment.args.get(
                    "scale", self._current_state.resolution_scale,
                )
            elif adjustment.kind == RenderAdjustmentKind.TOGGLE_SHADOWS:
                self._current_state.shadows_enabled = adjustment.args.get(
                    "enabled", self._current_state.shadows_enabled,
                )
            elif adjustment.kind == RenderAdjustmentKind.TOGGLE_POST_PROCESSING:
                self._current_state.post_processing_enabled = adjustment.args.get(
                    "enabled", self._current_state.post_processing_enabled,
                )
            elif adjustment.kind == RenderAdjustmentKind.ADJUST_PARTICLE_DENSITY:
                self._current_state.particle_density = adjustment.args.get(
                    "density", self._current_state.particle_density,
                )
            elif adjustment.kind == RenderAdjustmentKind.SET_VFX_INTENSITY:
                self._current_state.vfx_intensity = adjustment.args.get(
                    "intensity", self._current_state.vfx_intensity,
                )
            elif adjustment.kind == RenderAdjustmentKind.ADJUST_LOD_BIAS:
                self._current_state.lod_bias = adjustment.args.get(
                    "bias", self._current_state.lod_bias,
                )
        logger.info("Render adjustment applied: %s -> %s", adjustment.kind.value, adjustment.target)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_state": {
                    "fps": round(self._current_state.fps, 1),
                    "frame_time_ms": round(self._current_state.frame_time_ms, 2),
                    "draw_calls": self._current_state.draw_calls,
                    "triangles": self._current_state.triangles,
                    "quality_level": self._current_state.quality_level.value,
                    "resolution_scale": round(self._current_state.resolution_scale, 2),
                    "particle_density": round(self._current_state.particle_density, 2),
                    "shadows_enabled": self._current_state.shadows_enabled,
                    "post_processing_enabled": self._current_state.post_processing_enabled,
                    "vfx_intensity": round(self._current_state.vfx_intensity, 2),
                    "gpu_utilization": round(self._current_state.gpu_utilization, 3),
                },
                "history_size": len(self._history),
                "adjustments_applied": len(self._adjustment_history),
            }


# ---------------------------------------------------------------------------
# Scene Conductor
# ---------------------------------------------------------------------------

class SceneConductor:
    """Dynamically composes, modifies, and orchestrates scenes."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._current_state: SceneState = SceneState()
        self._history: Deque[SceneState] = deque(maxlen=32)
        self._adjustment_history: Deque[SceneAdjustment] = deque(maxlen=64)
        self._entity_registry: Dict[str, Dict[str, Any]] = {}
        self._max_entities = 256

    def update_state(self, state: SceneState) -> None:
        """Update the current scene state snapshot."""
        with self._lock:
            self._history.append(self._current_state)
            self._current_state = state

    def analyze(
        self, narrative_beat: Optional[str] = None,
        emergence_signals: int = 0, player_skill: float = 0.5,
    ) -> List[SceneAdjustment]:
        """Analyze the current state and propose adjustments."""
        with self._lock:
            state = self._current_state

        adjustments: List[SceneAdjustment] = []

        # Entity count management
        if state.entity_count > self._max_entities * 0.9:
            # Cull distant entities
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.DESPAWN_ENTITY,
                target="distant_entities",
                args={"cull_distance": 50.0, "max_cull": 20},
                rationale=f"entity_count={state.entity_count} near capacity",
            ))

        # Narrative-beat-driven adjustments
        if narrative_beat == "climax":
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SET_LIGHTING,
                target="lighting_system",
                args={"preset": "dramatic", "intensity": 1.3},
                rationale="climax beat: dramatic lighting",
            ))
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SET_AMBIENCE,
                target="ambience_system",
                args={"preset": "intense", "intensity": 1.2},
                rationale="climax beat: intense ambience",
            ))
        elif narrative_beat == "breather":
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SET_LIGHTING,
                target="lighting_system",
                args={"preset": "soft", "intensity": 0.8},
                rationale="breather beat: soft lighting",
            ))
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SET_AMBIENCE,
                target="ambience_system",
                args={"preset": "calm", "intensity": 0.7},
                rationale="breather beat: calm ambience",
            ))
        elif narrative_beat == "finale":
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SET_LIGHTING,
                target="lighting_system",
                args={"preset": "epic", "intensity": 1.5},
                rationale="finale beat: epic lighting",
            ))
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.TRIGGER_EVENT,
                target="event_system",
                args={"event": "finale_sequence", "delay": 0.5},
                rationale="finale beat: trigger finale sequence",
            ))

        # Emergence-driven spawning
        if emergence_signals > 3 and state.entity_count < self._max_entities * 0.7:
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SPAWN_ENTITY,
                target="entity_spawner",
                args={"type": "emergent_event", "count": 1, "near_player": True},
                rationale=f"{emergence_signals} emergence signals detected",
            ))

        # Player-skill-driven difficulty spawn
        if player_skill > 0.7 and state.entity_count < self._max_entities * 0.6:
            adjustments.append(SceneAdjustment(
                kind=SceneAdjustmentKind.SPAWN_ENTITY,
                target="entity_spawner",
                args={"type": "challenge_obstacle", "count": 1, "difficulty": "hard"},
                rationale=f"high player_skill={player_skill:.2f}, spawn challenge",
            ))

        return adjustments

    def apply(self, adjustment: SceneAdjustment) -> bool:
        """Apply a scene adjustment (simulated)."""
        adjustment.applied = True
        with self._lock:
            self._adjustment_history.append(adjustment)
            if adjustment.kind == SceneAdjustmentKind.SPAWN_ENTITY:
                count = adjustment.args.get("count", 1)
                self._current_state.entity_count += count
                self._current_state.active_entity_count += count
            elif adjustment.kind == SceneAdjustmentKind.DESPAWN_ENTITY:
                count = adjustment.args.get("max_cull", 1)
                self._current_state.entity_count = max(0, self._current_state.entity_count - count)
                self._current_state.active_entity_count = max(0, self._current_state.active_entity_count - count)
            elif adjustment.kind == SceneAdjustmentKind.SET_LIGHTING:
                self._current_state.lighting_preset = adjustment.args.get("preset", "default")
            elif adjustment.kind == SceneAdjustmentKind.SET_WEATHER:
                self._current_state.weather_preset = adjustment.args.get("preset", "clear")
            elif adjustment.kind == SceneAdjustmentKind.SET_AMBIENCE:
                self._current_state.ambience_preset = adjustment.args.get("preset", "neutral")
        logger.info("Scene adjustment applied: %s -> %s", adjustment.kind.value, adjustment.target)
        return True

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "current_state": {
                    "entity_count": self._current_state.entity_count,
                    "active_entity_count": self._current_state.active_entity_count,
                    "scene_name": self._current_state.scene_name,
                    "lighting_preset": self._current_state.lighting_preset,
                    "weather_preset": self._current_state.weather_preset,
                    "ambience_preset": self._current_state.ambience_preset,
                    "narrative_beat": self._current_state.narrative_beat,
                    "emergence_signals": self._current_state.emergence_signals,
                },
                "history_size": len(self._history),
                "adjustments_applied": len(self._adjustment_history),
                "registered_entities": len(self._entity_registry),
                "max_entities": self._max_entities,
            }


# ---------------------------------------------------------------------------
# AI-Native Engine Conductor (Singleton)
# ---------------------------------------------------------------------------

class AINativeConductor:
    """
    Singleton conductor that unifies physics, render, and scene conductors
    into a single cycle, driven by the cognitive kernel and game brain.
    """

    _instance: Optional["AINativeConductor"] = None
    _instance_lock = threading.Lock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._kernel: Optional[Any] = None
        self._integrator: Optional[Any] = None
        self._brain: Optional[Any] = None
        self._architect: Optional[Any] = None
        self._physics = PhysicsConductor()
        self._render = RenderConductor()
        self._scene = SceneConductor()
        self._cycle_count = 0
        self._last_result: Optional[ConductorDecision] = None

    @classmethod
    def get_instance(cls) -> "AINativeConductor":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def initialize(self) -> None:
        """Initialize the conductor by acquiring the kernel, brain, and architect."""
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.agent.agent_unified_kernel import AgentKernel
                self._kernel = AgentKernel.get_instance()
            except Exception as exc:
                logger.warning("AgentKernel acquisition failed: %s", exc)
                self._kernel = None
            try:
                from sparkai.engine.engine_kernel_integration import (
                    KernelEngineIntegrator,
                )
                self._integrator = KernelEngineIntegrator.get_instance()
            except Exception as exc:
                logger.warning("KernelEngineIntegrator acquisition failed: %s", exc)
                self._integrator = None
            try:
                from sparkai.agent.agent_game_brain import GameBrain
                self._brain = GameBrain.get_instance()
            except Exception as exc:
                logger.warning("GameBrain acquisition failed: %s", exc)
                self._brain = None
            try:
                from sparkai.agent.agent_cognitive_architect import (
                    CognitiveArchitect,
                )
                self._architect = CognitiveArchitect.get_instance()
            except Exception as exc:
                logger.warning("CognitiveArchitect acquisition failed: %s", exc)
                self._architect = None
            self._initialized = True
            logger.info("AINativeConductor initialized")

    # -----------------------------------------------------------------
    # State Updates
    # -----------------------------------------------------------------

    def update_physics_state(self, state: PhysicsState) -> None:
        self._physics.update_state(state)

    def update_render_state(self, state: RenderState) -> None:
        self._render.update_state(state)

    def update_scene_state(self, state: SceneState) -> None:
        self._scene.update_state(state)

    # -----------------------------------------------------------------
    # Conductor Cycle
    # -----------------------------------------------------------------

    def cycle(self) -> ConductorDecision:
        """Run one conductor cycle: observe → analyze → adjust → verify."""
        if not self._initialized:
            self.initialize()
        start = time.time()
        with self._lock:
            self._cycle_count += 1
        decision = ConductorDecision()

        # Phase 1: Observe - gather player mood and pacing from the brain
        decision.phase = ConductorPhase.OBSERVE
        player_mood: Optional[str] = None
        pacing_zone: Optional[str] = None
        narrative_beat: Optional[str] = None
        emergence_signals = 0
        player_skill = 0.5

        if self._brain is not None:
            try:
                brain_status = self._brain.status()
                player_state = brain_status.get("player", {})
                pacing_state = brain_status.get("pacing", {})
                player_mood = player_state.get("mood")
                pacing_zone = pacing_state.get("zone")
                player_skill = player_state.get("skill", 0.5)
                emergence_signals = brain_status.get("emergence_recent", [])
                if isinstance(emergence_signals, list):
                    emergence_signals = len(emergence_signals)
                narrative_state = brain_status.get("narrative", {})
                if narrative_state.get("last_beat_time", 0) > 0:
                    narrative_beat = narrative_state.get("last_beat_kind", "")
            except Exception as exc:
                decision.notes.append(f"brain_observe_failed: {exc}")

        # Phase 2: Analyze - run each conductor's analysis
        decision.phase = ConductorPhase.ANALYZE
        physics_adjustments = self._physics.analyze()
        render_adjustments = self._render.analyze(player_mood, pacing_zone)
        scene_adjustments = self._scene.analyze(
            narrative_beat, emergence_signals, player_skill,
        )

        # Phase 3: Adjust - apply all adjustments
        decision.phase = ConductorPhase.ADJUST
        for adj in physics_adjustments:
            self._physics.apply(adj)
            decision.physics_adjustments.append(adj)
        for adj in render_adjustments:
            self._render.apply(adj)
            decision.render_adjustments.append(adj)
        for adj in scene_adjustments:
            self._scene.apply(adj)
            decision.scene_adjustments.append(adj)

        # Phase 4: Verify - emit the decision to the kernel via the integrator
        decision.phase = ConductorPhase.VERIFY
        decision.duration_s = time.time() - start
        with self._lock:
            self._last_result = decision

        # Record the decision in the kernel's episodic memory
        if self._kernel is not None:
            try:
                self._kernel.perceive(
                    source="conductor",
                    channel="engine_adjustment",
                    payload={
                        "physics_count": len(decision.physics_adjustments),
                        "render_count": len(decision.render_adjustments),
                        "scene_count": len(decision.scene_adjustments),
                        "duration_s": decision.duration_s,
                    },
                    salience=0.6,
                )
            except Exception as exc:
                decision.notes.append(f"kernel_perceive_failed: {exc}")

        return decision

    # -----------------------------------------------------------------
    # Manual Adjustments
    # -----------------------------------------------------------------

    def submit_physics_adjustment(
        self, kind: str, target: str, args: Dict[str, Any], rationale: str = "",
    ) -> PhysicsAdjustment:
        """Manually submit a physics adjustment."""
        try:
            kind_enum = PhysicsAdjustmentKind(kind)
        except ValueError:
            kind_enum = PhysicsAdjustmentKind.TUNE_GRAVITY
        adj = PhysicsAdjustment(
            kind=kind_enum, target=target, args=args, rationale=rationale,
        )
        self._physics.apply(adj)
        return adj

    def submit_render_adjustment(
        self, kind: str, target: str, args: Dict[str, Any], rationale: str = "",
    ) -> RenderAdjustment:
        """Manually submit a render adjustment."""
        try:
            kind_enum = RenderAdjustmentKind(kind)
        except ValueError:
            kind_enum = RenderAdjustmentKind.SET_QUALITY_LEVEL
        adj = RenderAdjustment(
            kind=kind_enum, target=target, args=args, rationale=rationale,
        )
        self._render.apply(adj)
        return adj

    def submit_scene_adjustment(
        self, kind: str, target: str, args: Dict[str, Any], rationale: str = "",
    ) -> SceneAdjustment:
        """Manually submit a scene adjustment."""
        try:
            kind_enum = SceneAdjustmentKind(kind)
        except ValueError:
            kind_enum = SceneAdjustmentKind.SPAWN_ENTITY
        adj = SceneAdjustment(
            kind=kind_enum, target=target, args=args, rationale=rationale,
        )
        self._scene.apply(adj)
        return adj

    # -----------------------------------------------------------------
    # Status and Inspection
    # -----------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "cycle_count": self._cycle_count,
                "kernel_attached": self._kernel is not None,
                "integrator_attached": self._integrator is not None,
                "brain_attached": self._brain is not None,
                "architect_attached": self._architect is not None,
                "physics": self._physics.stats(),
                "render": self._render.stats(),
                "scene": self._scene.stats(),
                "last_cycle": {
                    "phase": self._last_result.phase.value if self._last_result else None,
                    "physics_adjustments": len(self._last_result.physics_adjustments) if self._last_result else 0,
                    "render_adjustments": len(self._last_result.render_adjustments) if self._last_result else 0,
                    "scene_adjustments": len(self._last_result.scene_adjustments) if self._last_result else 0,
                    "duration_s": self._last_result.duration_s if self._last_result else 0,
                } if self._last_result else None,
            }

    def reset(self) -> None:
        """Reset the conductor state (preserves wiring)."""
        with self._lock:
            self._cycle_count = 0
            self._last_result = None


# ---------------------------------------------------------------------------
# Module-level Convenience
# ---------------------------------------------------------------------------

def get_conductor() -> AINativeConductor:
    return AINativeConductor.get_instance()


def quick_conductor_status() -> Dict[str, Any]:
    return get_conductor().status()
