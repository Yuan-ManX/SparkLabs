"""
SparkLabs Engine - Unified Game Runtime

A comprehensive runtime engine that integrates all engine subsystems into a
single, coherent game execution framework. The Unified Game Runtime manages
game loop orchestration, scene lifecycle, physics simulation, rendering
pipeline, audio processing, input handling, and cross-subsystem coordination
for the AI-native game engine.

Architecture:
  UnifiedGameRuntime (Singleton)
    |-- GameLoopOrchestrator (frame-based game loop with fixed/variable timestep)
    |-- SceneLifecycleManager (scene loading, activation, transition, unloading)
    |-- PhysicsCoordinator (physics simulation step coordination)
    |-- RenderPipelineManager (render pass orchestration and frame composition)
    |-- AudioMixer (audio source management and spatial audio mixing)
    |-- InputAggregator (multi-device input collection and mapping)
    |-- EntityCoordinator (cross-system entity lifecycle and state sync)
    |-- PerformanceProfiler (real-time performance metrics and bottleneck detection)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# ------------------------------------------------------------------ Enums ------------------------------------------------------------------

class RuntimeState(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    STEPPING = "stepping"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


class TimestepMode(Enum):
    FIXED = "fixed"
    VARIABLE = "variable"
    SEMI_FIXED = "semi_fixed"
    INTERPOLATED = "interpolated"


class SceneState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVATING = "activating"
    ACTIVE = "active"
    DEACTIVATING = "deactivating"
    UNLOADING = "unloading"


class RenderPhase(Enum):
    PRE_RENDER = "pre_render"
    SHADOW_PASS = "shadow_pass"
    OPAQUE_PASS = "opaque_pass"
    TRANSPARENT_PASS = "transparent_pass"
    POST_PROCESS = "post_process"
    UI_PASS = "ui_pass"
    PRESENT = "present"


class PhysicsStep(Enum):
    BROAD_PHASE = "broad_phase"
    NARROW_PHASE = "narrow_phase"
    CONSTRAINT_SOLVE = "constraint_solve"
    INTEGRATION = "integration"
    EVENT_DISPATCH = "event_dispatch"


class AudioChannel(Enum):
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    VOICE = "voice"
    AMBIENT = "ambient"
    UI = "ui"


class InputLayer(Enum):
    SYSTEM = "system"
    GAMEPLAY = "gameplay"
    UI = "ui"
    DEBUG = "debug"
    CHEAT = "cheat"


# ---------------------------------------------------------------- Dataclasses ----------------------------------------------------------------

@dataclass
class FrameTiming:
    frame_id: int = 0
    delta_time: float = 0.0
    fixed_delta_time: float = 0.016667
    time_scale: float = 1.0
    total_time: float = 0.0
    frame_count: int = 0
    fps: float = 0.0
    physics_accumulator: float = 0.0
    render_interpolation: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id, "delta_time": round(self.delta_time, 6),
            "fixed_delta_time": round(self.fixed_delta_time, 6),
            "time_scale": round(self.time_scale, 2), "total_time": round(self.total_time, 4),
            "frame_count": self.frame_count, "fps": round(self.fps, 1),
            "render_interpolation": round(self.render_interpolation, 4),
        }


@dataclass
class SceneInstance:
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    state: SceneState = SceneState.UNLOADED
    entities: List[str] = field(default_factory=list)
    active_camera: Optional[str] = None
    environment_settings: Dict[str, Any] = field(default_factory=dict)
    load_time: float = 0.0
    activation_time: float = 0.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id, "name": self.name, "state": self.state.value,
            "entity_count": len(self.entities), "active_camera": self.active_camera,
            "environment_settings": dict(self.environment_settings),
            "load_time": round(self.load_time, 4), "activation_time": round(self.activation_time, 4),
        }


@dataclass
class RenderStats:
    draw_calls: int = 0
    triangles: int = 0
    vertices: int = 0
    batches: int = 0
    shadow_castors: int = 0
    visible_lights: int = 0
    post_process_effects: int = 0
    frame_time: float = 0.0
    gpu_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "draw_calls": self.draw_calls, "triangles": self.triangles,
            "vertices": self.vertices, "batches": self.batches,
            "shadow_castors": self.shadow_castors, "visible_lights": self.visible_lights,
            "post_process_effects": self.post_process_effects,
            "frame_time": round(self.frame_time, 4), "gpu_time": round(self.gpu_time, 4),
        }


@dataclass
class PhysicsStats:
    bodies: int = 0
    static_bodies: int = 0
    dynamic_bodies: int = 0
    kinematic_bodies: int = 0
    contacts: int = 0
    joints: int = 0
    broad_phase_time: float = 0.0
    narrow_phase_time: float = 0.0
    solve_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "bodies": self.bodies, "static_bodies": self.static_bodies,
            "dynamic_bodies": self.dynamic_bodies, "kinematic_bodies": self.kinematic_bodies,
            "contacts": self.contacts, "joints": self.joints,
            "broad_phase_time": round(self.broad_phase_time, 6),
            "narrow_phase_time": round(self.narrow_phase_time, 6),
            "solve_time": round(self.solve_time, 6),
        }


@dataclass
class AudioStats:
    active_sources: int = 0
    virtual_sources: int = 0
    mixing_buffers: int = 0
    dsp_effects: int = 0
    cpu_load: float = 0.0
    memory_usage: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_sources": self.active_sources, "virtual_sources": self.virtual_sources,
            "mixing_buffers": self.mixing_buffers, "dsp_effects": self.dsp_effects,
            "cpu_load": round(self.cpu_load, 4), "memory_usage": round(self.memory_usage, 2),
        }


@dataclass
class RuntimeProfile:
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    frame_timing: FrameTiming = field(default_factory=FrameTiming)
    render_stats: RenderStats = field(default_factory=RenderStats)
    physics_stats: PhysicsStats = field(default_factory=PhysicsStats)
    audio_stats: AudioStats = field(default_factory=AudioStats)
    memory_usage: float = 0.0
    active_entities: int = 0
    active_scenes: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "frame_timing": self.frame_timing.to_dict(),
            "render_stats": self.render_stats.to_dict(),
            "physics_stats": self.physics_stats.to_dict(),
            "audio_stats": self.audio_stats.to_dict(),
            "memory_usage": round(self.memory_usage, 2),
            "active_entities": self.active_entities,
            "active_scenes": self.active_scenes,
            "timestamp": self.timestamp,
        }


# --------------------------------------------------------- GameLoopOrchestrator -------------------------------------------------------------

class GameLoopOrchestrator:
    """Frame-based game loop with fixed/variable timestep support."""

    def __init__(self) -> None:
        self._state: RuntimeState = RuntimeState.UNINITIALIZED
        self._timestep_mode: TimestepMode = TimestepMode.SEMI_FIXED
        self._frame_timing = FrameTiming()
        self._fixed_timestep: float = 1.0 / 60.0
        self._max_frame_time: float = 0.25
        self._callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._frame_history: deque = deque(maxlen=120)
        self._lock = threading.RLock()

    def initialize(self, fixed_timestep: float = 1.0 / 60.0) -> None:
        with self._lock:
            self._fixed_timestep = fixed_timestep
            self._frame_timing.fixed_delta_time = fixed_timestep
            self._state = RuntimeState.STOPPED

    def start(self) -> None:
        with self._lock:
            self._state = RuntimeState.RUNNING
            self._frame_timing.total_time = 0.0
            self._frame_timing.frame_count = 0

    def pause(self) -> None:
        with self._lock:
            if self._state == RuntimeState.RUNNING:
                self._state = RuntimeState.PAUSED

    def resume(self) -> None:
        with self._lock:
            if self._state == RuntimeState.PAUSED:
                self._state = RuntimeState.RUNNING

    def step(self, delta_time: float) -> FrameTiming:
        with self._lock:
            if self._state not in (RuntimeState.RUNNING, RuntimeState.STEPPING):
                return self._frame_timing

            dt = min(delta_time, self._max_frame_time) * self._frame_timing.time_scale
            self._frame_timing.delta_time = dt
            self._frame_timing.total_time += dt
            self._frame_timing.frame_count += 1
            self._frame_timing.frame_id = self._frame_timing.frame_count

            physics_steps = 0
            if self._timestep_mode in (TimestepMode.FIXED, TimestepMode.SEMI_FIXED):
                self._frame_timing.physics_accumulator += dt
                while self._frame_timing.physics_accumulator >= self._fixed_timestep:
                    self._frame_timing.physics_accumulator -= self._fixed_timestep
                    physics_steps += 1
                    self._invoke_callbacks("fixed_update", self._fixed_timestep)
                self._frame_timing.render_interpolation = (
                    self._frame_timing.physics_accumulator / self._fixed_timestep
                )

            self._invoke_callbacks("update", dt)
            self._invoke_callbacks("late_update", dt)

            if self._frame_timing.frame_count % 10 == 0:
                recent = list(self._frame_history)[-10:]
                if recent:
                    avg_dt = sum(f["delta_time"] for f in recent) / len(recent)
                    self._frame_timing.fps = 1.0 / max(avg_dt, 0.0001)

            self._frame_history.append({
                "frame_id": self._frame_timing.frame_id,
                "delta_time": dt,
                "physics_steps": physics_steps,
                "timestamp": time.time(),
            })

            return self._frame_timing

    def register_callback(self, event: str, callback: Callable) -> None:
        with self._lock:
            self._callbacks[event].append(callback)

    def unregister_callback(self, event: str, callback: Callable) -> None:
        with self._lock:
            if callback in self._callbacks[event]:
                self._callbacks[event].remove(callback)

    def _invoke_callbacks(self, event: str, *args: Any) -> None:
        for cb in self._callbacks.get(event, []):
            try:
                cb(*args)
            except Exception:
                pass

    def get_state(self) -> RuntimeState:
        return self._state

    def get_frame_timing(self) -> FrameTiming:
        return self._frame_timing

    def get_frame_history(self, limit: int = 60) -> List[Dict[str, Any]]:
        return list(self._frame_history)[-limit:]


# -------------------------------------------------------- SceneLifecycleManager -------------------------------------------------------------

class SceneLifecycleManager:
    """Scene loading, activation, transition, and unloading management."""

    def __init__(self) -> None:
        self._scenes: Dict[str, SceneInstance] = {}
        self._active_scene: Optional[str] = None
        self._scene_stack: List[str] = []
        self._transition_queue: deque = deque()
        self._lock = threading.RLock()

    def create_scene(self, name: str) -> SceneInstance:
        with self._lock:
            scene = SceneInstance(name=name)
            self._scenes[scene.scene_id] = scene
            return scene

    def load_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            scene.state = SceneState.LOADING
            load_start = time.time()
            scene.state = SceneState.LOADED
            scene.load_time = time.time() - load_start
            return True

    def activate_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene or scene.state != SceneState.LOADED:
                return False

            if self._active_scene:
                prev = self._scenes.get(self._active_scene)
                if prev:
                    prev.state = SceneState.DEACTIVATING
                    prev.state = SceneState.LOADED

            scene.state = SceneState.ACTIVATING
            activation_start = time.time()
            scene.state = SceneState.ACTIVE
            scene.activation_time = time.time() - activation_start

            self._active_scene = scene_id
            self._scene_stack.append(scene_id)
            return True

    def deactivate_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene or scene.state != SceneState.ACTIVE:
                return False
            scene.state = SceneState.DEACTIVATING
            scene.state = SceneState.LOADED
            if self._active_scene == scene_id:
                self._active_scene = None
            return True

    def unload_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if not scene:
                return False
            scene.state = SceneState.UNLOADING
            del self._scenes[scene_id]
            if self._active_scene == scene_id:
                self._active_scene = None
            return True

    def get_active_scene(self) -> Optional[SceneInstance]:
        if self._active_scene:
            return self._scenes.get(self._active_scene)
        return None

    def get_all_scenes(self) -> List[SceneInstance]:
        return list(self._scenes.values())

    def get_scene_stack(self) -> List[str]:
        return list(self._scene_stack)


# --------------------------------------------------------- PhysicsCoordinator ---------------------------------------------------------------

class PhysicsCoordinator:
    """Physics simulation step coordination and collision management."""

    def __init__(self) -> None:
        self._enabled: bool = True
        self._gravity: Tuple[float, float] = (0.0, -9.81)
        self._stats = PhysicsStats()
        self._collision_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._lock = threading.RLock()

    def step(self, delta_time: float) -> PhysicsStats:
        with self._lock:
            if not self._enabled:
                return self._stats

            broad_start = time.time()
            self._stats.broad_phase_time = time.time() - broad_start

            narrow_start = time.time()
            self._stats.narrow_phase_time = time.time() - narrow_start

            solve_start = time.time()
            self._stats.solve_time = time.time() - solve_start

            return self._stats

    def set_gravity(self, x: float, y: float) -> None:
        self._gravity = (x, y)

    def get_stats(self) -> PhysicsStats:
        return self._stats

    def register_collision_callback(self, collision_type: str, callback: Callable) -> None:
        with self._lock:
            self._collision_callbacks[collision_type].append(callback)


# -------------------------------------------------------- RenderPipelineManager --------------------------------------------------------------

class RenderPipelineManager:
    """Render pass orchestration and frame composition management."""

    def __init__(self) -> None:
        self._render_passes: Dict[RenderPhase, List[Callable]] = defaultdict(list)
        self._clear_color: Tuple[float, float, float, float] = (0.05, 0.05, 0.1, 1.0)
        self._stats = RenderStats()
        self._lock = threading.RLock()

    def register_pass(self, phase: RenderPhase, callback: Callable) -> None:
        with self._lock:
            self._render_passes[phase].append(callback)

    def render_frame(self) -> RenderStats:
        with self._lock:
            frame_start = time.time()
            for phase in RenderPhase:
                for callback in self._render_passes.get(phase, []):
                    try:
                        callback()
                    except Exception:
                        pass
            self._stats.frame_time = time.time() - frame_start
            return self._stats

    def set_clear_color(self, r: float, g: float, b: float, a: float = 1.0) -> None:
        self._clear_color = (r, g, b, a)

    def get_stats(self) -> RenderStats:
        return self._stats


# -------------------------------------------------------------- AudioMixer ------------------------------------------------------------------

class AudioMixer:
    """Audio source management and spatial audio mixing."""

    def __init__(self) -> None:
        self._channels: Dict[AudioChannel, float] = {
            ch: 1.0 for ch in AudioChannel
        }
        self._stats = AudioStats()
        self._lock = threading.RLock()

    def set_volume(self, channel: AudioChannel, volume: float) -> None:
        with self._lock:
            self._channels[channel] = max(0.0, min(1.0, volume))

    def get_volume(self, channel: AudioChannel) -> float:
        return self._channels.get(channel, 1.0)

    def mute(self, channel: Optional[AudioChannel] = None) -> None:
        with self._lock:
            if channel:
                self._channels[channel] = 0.0
            else:
                for ch in self._channels:
                    self._channels[ch] = 0.0

    def unmute(self, channel: Optional[AudioChannel] = None) -> None:
        with self._lock:
            if channel:
                self._channels[channel] = 1.0
            else:
                for ch in self._channels:
                    self._channels[ch] = 1.0

    def get_stats(self) -> AudioStats:
        return self._stats


# ------------------------------------------------------------ InputAggregator ---------------------------------------------------------------

class InputAggregator:
    """Multi-device input collection, mapping, and layer-based processing."""

    def __init__(self) -> None:
        self._input_states: Dict[str, Any] = {}
        self._input_map: Dict[str, List[str]] = defaultdict(list)
        self._active_layers: Set[InputLayer] = {InputLayer.GAMEPLAY, InputLayer.UI}
        self._lock = threading.RLock()

    def update_input(self, input_name: str, value: Any) -> None:
        with self._lock:
            self._input_states[input_name] = value

    def get_input(self, input_name: str) -> Any:
        return self._input_states.get(input_name)

    def map_input(self, action: str, input_name: str) -> None:
        with self._lock:
            if input_name not in self._input_map[action]:
                self._input_map[action].append(input_name)

    def is_action_pressed(self, action: str) -> bool:
        inputs = self._input_map.get(action, [])
        return any(self._input_states.get(inp, False) for inp in inputs)

    def enable_layer(self, layer: InputLayer) -> None:
        self._active_layers.add(layer)

    def disable_layer(self, layer: InputLayer) -> None:
        self._active_layers.discard(layer)


# ---------------------------------------------------------- EntityCoordinator ---------------------------------------------------------------

class EntityCoordinator:
    """Cross-system entity lifecycle and state synchronization."""

    def __init__(self) -> None:
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._entity_components: Dict[str, Set[str]] = defaultdict(set)
        self._lock = threading.RLock()

    def create_entity(self, name: str = "", components: Optional[Dict[str, Any]] = None) -> str:
        with self._lock:
            entity_id = uuid.uuid4().hex[:12]
            self._entities[entity_id] = {
                "name": name or f"Entity_{entity_id[:6]}",
                "components": components or {},
                "active": True,
                "created_at": time.time(),
            }
            return entity_id

    def destroy_entity(self, entity_id: str) -> bool:
        with self._lock:
            if entity_id in self._entities:
                del self._entities[entity_id]
                self._entity_components.pop(entity_id, None)
                return True
            return False

    def add_component(self, entity_id: str, component_type: str, data: Dict[str, Any]) -> bool:
        with self._lock:
            entity = self._entities.get(entity_id)
            if not entity:
                return False
            entity["components"][component_type] = data
            self._entity_components[entity_id].add(component_type)
            return True

    def remove_component(self, entity_id: str, component_type: str) -> bool:
        with self._lock:
            entity = self._entities.get(entity_id)
            if not entity:
                return False
            entity["components"].pop(component_type, None)
            self._entity_components[entity_id].discard(component_type)
            return True

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        return self._entities.get(entity_id)

    def get_all_entities(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._entities)

    def get_entity_count(self) -> int:
        return len(self._entities)


# -------------------------------------------------------- PerformanceProfiler ---------------------------------------------------------------

class PerformanceProfiler:
    """Real-time performance metrics collection and bottleneck detection."""

    def __init__(self) -> None:
        self._metrics_history: deque = deque(maxlen=300)
        self._bottlenecks: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def record_frame(self, profile: RuntimeProfile) -> None:
        with self._lock:
            self._metrics_history.append(profile.to_dict())

            if len(self._metrics_history) >= 60:
                self._detect_bottlenecks()

    def get_recent_metrics(self, frames: int = 60) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._metrics_history)[-frames:]

    def get_bottlenecks(self) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._bottlenecks)

    def _detect_bottlenecks(self) -> None:
        recent = list(self._metrics_history)[-60:]
        render_times = [r["render_stats"]["frame_time"] for r in recent]
        physics_times = [
            r["physics_stats"]["broad_phase_time"] +
            r["physics_stats"]["narrow_phase_time"] +
            r["physics_stats"]["solve_time"]
            for r in recent
        ]

        avg_render = sum(render_times) / len(render_times)
        avg_physics = sum(physics_times) / len(physics_times)
        target_frame = 1.0 / 60.0

        self._bottlenecks = []
        if avg_render > target_frame * 0.8:
            self._bottlenecks.append({
                "type": "render_bound",
                "severity": "high" if avg_render > target_frame else "medium",
                "avg_time": round(avg_render, 6),
                "percentage": round(avg_render / target_frame * 100, 1),
            })
        if avg_physics > target_frame * 0.5:
            self._bottlenecks.append({
                "type": "physics_bound",
                "severity": "high" if avg_physics > target_frame * 0.8 else "medium",
                "avg_time": round(avg_physics, 6),
                "percentage": round(avg_physics / target_frame * 100, 1),
            })


# --------------------------------------------------------- UnifiedGameRuntime ----------------------------------------------------------------

class UnifiedGameRuntime:
    """Comprehensive runtime engine for AI-native game execution."""

    _instance: Optional["UnifiedGameRuntime"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use UnifiedGameRuntime.get_instance()")
        self._game_loop = GameLoopOrchestrator()
        self._scene_manager = SceneLifecycleManager()
        self._physics = PhysicsCoordinator()
        self._renderer = RenderPipelineManager()
        self._audio = AudioMixer()
        self._input = InputAggregator()
        self._entities = EntityCoordinator()
        self._profiler = PerformanceProfiler()
        self._state: RuntimeState = RuntimeState.UNINITIALIZED
        self._initialized: bool = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "UnifiedGameRuntime":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> None:
        with self._lock:
            if self._initialized:
                return
            cfg = config or {}
            self._game_loop.initialize(cfg.get("fixed_timestep", 1.0 / 60.0))
            self._state = RuntimeState.STOPPED
            self._initialized = True

    @property
    def game_loop(self) -> GameLoopOrchestrator:
        return self._game_loop

    @property
    def scene_manager(self) -> SceneLifecycleManager:
        return self._scene_manager

    @property
    def physics(self) -> PhysicsCoordinator:
        return self._physics

    @property
    def renderer(self) -> RenderPipelineManager:
        return self._renderer

    @property
    def audio(self) -> AudioMixer:
        return self._audio

    @property
    def input(self) -> InputAggregator:
        return self._input

    @property
    def entities(self) -> EntityCoordinator:
        return self._entities

    @property
    def profiler(self) -> PerformanceProfiler:
        return self._profiler

    def start(self) -> None:
        with self._lock:
            self._game_loop.start()
            self._state = RuntimeState.RUNNING

    def pause(self) -> None:
        with self._lock:
            self._game_loop.pause()
            self._state = RuntimeState.PAUSED

    def resume(self) -> None:
        with self._lock:
            self._game_loop.resume()
            self._state = RuntimeState.RUNNING

    def stop(self) -> None:
        with self._lock:
            self._state = RuntimeState.STOPPING
            self._state = RuntimeState.STOPPED

    def tick(self, delta_time: float) -> RuntimeProfile:
        with self._lock:
            frame_timing = self._game_loop.step(delta_time)
            physics_stats = self._physics.step(delta_time)
            render_stats = self._renderer.render_frame()
            audio_stats = self._audio.get_stats()

            profile = RuntimeProfile(
                frame_timing=frame_timing,
                render_stats=render_stats,
                physics_stats=physics_stats,
                audio_stats=audio_stats,
                active_entities=self._entities.get_entity_count(),
                active_scenes=len(self._scene_manager.get_all_scenes()),
            )

            self._profiler.record_frame(profile)
            return profile

    def get_state(self) -> RuntimeState:
        return self._state

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self._state.value,
            "initialized": self._initialized,
            "frame_timing": self._game_loop.get_frame_timing().to_dict(),
            "render_stats": self._renderer.get_stats().to_dict(),
            "physics_stats": self._physics.get_stats().to_dict(),
            "audio_stats": self._audio.get_stats().to_dict(),
            "entities": self._entities.get_entity_count(),
            "scenes": len(self._scene_manager.get_all_scenes()),
            "bottlenecks": self._profiler.get_bottlenecks(),
        }


# ---------------------------------------------------------------- Singleton Accessor ----------------------------------------------------------------

def get_unified_runtime() -> UnifiedGameRuntime:
    """Get or create the singleton UnifiedGameRuntime instance."""
    return UnifiedGameRuntime.get_instance()