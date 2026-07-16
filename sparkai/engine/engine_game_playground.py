"""
SparkLabs Engine - Game Playground

A Sandbox Game Runtime for the SparkLabs AI-native game engine. It enables
instant preview and testing of game mechanics in a sandboxed environment
for rapid iteration and testing.

Architecture:
  EngineGamePlayground (Singleton)
    |-- SandboxRuntime:      isolated game runtime for preview
    |-- SceneLoader:         scene loading and instantiation
    |-- PhysicsSimulator:    simple 2D physics for testing mechanics
    |-- InputSimulator:      automated input testing and replay
    |-- GameLoop:            fixed-timestep game loop with delta time
    |-- PerformanceMonitor:  FPS, memory, and frame timing
    |-- HotReload:           watch for scene changes and reload automatically
    |-- DebugOverlay:        runtime debug information overlay

Data Classes:
    PlaygroundSession  — active preview session with state
    RuntimeEntity      — game entity in the sandbox
    PhysicsConfig      — physics configuration parameters
    FrameMetrics       — per-frame performance data
    InputSequence      — automated input replay sequence
    DebugInfo          — runtime debug information

Enums:
    PlaygroundState    — IDLE, LOADING, RUNNING, PAUSED, STOPPED, ERROR
    PhysicsMode        — NONE, SIMPLE, FULL
    InputMode          — MANUAL, RECORDING, PLAYBACK

Usage:
    playground = get_game_playground()
    session = playground.create_session(scene_data)
    playground.start_session(session.session_id)
    metrics = playground.step_frame(session.session_id)
    playground.stop_session(session.session_id)
"""

from __future__ import annotations

import math
import os
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlaygroundState(str, Enum):
    """Lifecycle states of a playground session.

    States:
        IDLE:     Session created but not yet started.
        LOADING:  Scene data is being loaded into the sandbox.
        RUNNING:  Session is actively running the game loop.
        PAUSED:   Session is paused (game loop suspended).
        STOPPED:  Session has been explicitly stopped.
        ERROR:    Session encountered an unrecoverable error.
    """
    IDLE = "idle"
    LOADING = "loading"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PhysicsMode(str, Enum):
    """Physics simulation fidelity levels.

    Modes:
        NONE:   No physics simulation (static entities only).
        SIMPLE: Basic 2D physics (gravity, velocity, AABB collision).
        FULL:   Advanced 2D physics (forces, constraints, angular velocity).
    """
    NONE = "none"
    SIMPLE = "simple"
    FULL = "full"


class InputMode(str, Enum):
    """Input handling modes for the playground session.

    Modes:
        MANUAL:    User provides real-time input via keyboard/mouse.
        RECORDING: Input is being captured for later playback.
        PLAYBACK:  Input is being replayed from a recorded sequence.
    """
    MANUAL = "manual"
    RECORDING = "recording"
    PLAYBACK = "playback"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlaygroundSession:
    """Active preview session with full runtime state.

    Attributes:
        session_id:    Unique identifier for the session.
        scene_data:    Raw scene definition data loaded into the sandbox.
        state:         Current lifecycle state of the session.
        created_at:    Unix timestamp when the session was created.
        started_at:    Unix timestamp when the session was started (0 if not started).
        paused_at:     Unix timestamp when the session was last paused (0 if not paused).
        total_frames:  Total number of frames processed since start.
        total_time:    Total elapsed time in seconds since start.
        physics_mode:  Physics simulation fidelity level.
        input_mode:    Current input handling mode.
        entity_count:  Number of entities in the sandbox.
        error_message: Error description if state is ERROR, empty otherwise.
        metadata:      Arbitrary key-value metadata for engine extensions.
    """
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_data: Dict[str, Any] = field(default_factory=dict)
    state: PlaygroundState = PlaygroundState.IDLE
    created_at: float = field(default_factory=_time_module.time)
    started_at: float = 0.0
    paused_at: float = 0.0
    total_frames: int = 0
    total_time: float = 0.0
    physics_mode: PhysicsMode = PhysicsMode.SIMPLE
    input_mode: InputMode = InputMode.MANUAL
    entity_count: int = 0
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "paused_at": self.paused_at,
            "total_frames": self.total_frames,
            "total_time": self.total_time,
            "physics_mode": self.physics_mode.value,
            "input_mode": self.input_mode.value,
            "entity_count": self.entity_count,
            "error_message": self.error_message,
            "metadata": dict(self.metadata),
        }


@dataclass
class RuntimeEntity:
    """A game entity running inside the sandbox.

    Attributes:
        entity_id:   Unique identifier for the entity.
        name:        Human-readable entity name.
        position:    Current (x, y) position in world space.
        velocity:    Current (vx, vy) velocity in units per second.
        rotation:    Current rotation angle in radians.
        scale:       Current (sx, sy) scale factors.
        active:      Whether the entity is currently active.
        layer:       Render layer index for z-ordering.
        tags:        List of string tags for categorization.
        components:  Arbitrary component data attached to the entity.
    """
    entity_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    velocity: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    active: bool = True
    layer: int = 0
    tags: List[str] = field(default_factory=list)
    components: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "position": list(self.position),
            "velocity": list(self.velocity),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "active": self.active,
            "layer": self.layer,
            "tags": list(self.tags),
            "components": dict(self.components),
        }


@dataclass
class PhysicsConfig:
    """Physics simulation configuration parameters.

    Attributes:
        gravity:         Gravity vector (gx, gy) in units per second squared.
        time_step:       Fixed physics timestep in seconds.
        velocity_iterations: Number of velocity solver iterations per step.
        position_iterations: Number of position solver iterations per step.
        enable_sleep:    Whether to allow sleeping of stationary bodies.
        sleep_threshold: Velocity threshold below which bodies can sleep.
        collision_mask:  Default collision bitmask for new entities.
        world_bounds:    (min_x, min_y, max_x, max_y) world boundary.
    """
    gravity: Tuple[float, float] = (0.0, -9.81)
    time_step: float = 0.016
    velocity_iterations: int = 8
    position_iterations: int = 3
    enable_sleep: bool = True
    sleep_threshold: float = 0.01
    collision_mask: int = 0xFFFFFFFF
    world_bounds: Tuple[float, float, float, float] = (-1000.0, -1000.0, 1000.0, 1000.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "gravity": list(self.gravity),
            "time_step": self.time_step,
            "velocity_iterations": self.velocity_iterations,
            "position_iterations": self.position_iterations,
            "enable_sleep": self.enable_sleep,
            "sleep_threshold": self.sleep_threshold,
            "collision_mask": self.collision_mask,
            "world_bounds": list(self.world_bounds),
        }


@dataclass
class FrameMetrics:
    """Per-frame performance data captured during a session.

    Attributes:
        frame_id:         Monotonically increasing frame number.
        delta_time:       Frame delta time in seconds.
        fps:              Frames per second averaged over recent samples.
        update_time_ms:   Time spent in the update phase in milliseconds.
        physics_time_ms:  Time spent in physics simulation in milliseconds.
        render_time_ms:   Time spent in the render phase in milliseconds.
        entity_count:     Number of active entities in the frame.
        memory_usage_mb:  Estimated memory usage in megabytes.
        timestamp:        Unix timestamp when this frame was captured.
    """
    frame_id: int = 0
    delta_time: float = 0.0
    fps: float = 0.0
    update_time_ms: float = 0.0
    physics_time_ms: float = 0.0
    render_time_ms: float = 0.0
    entity_count: int = 0
    memory_usage_mb: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "delta_time": self.delta_time,
            "fps": self.fps,
            "update_time_ms": self.update_time_ms,
            "physics_time_ms": self.physics_time_ms,
            "render_time_ms": self.render_time_ms,
            "entity_count": self.entity_count,
            "memory_usage_mb": self.memory_usage_mb,
            "timestamp": self.timestamp,
        }


@dataclass
class InputSequence:
    """A recorded sequence of input events for automated replay.

    Attributes:
        sequence_id:  Unique identifier for the input sequence.
        events:       List of input events with timestamps and data.
        duration:     Total duration of the sequence in seconds.
        created_at:   Unix timestamp when the sequence was recorded.
        metadata:     Arbitrary key-value metadata.
    """
    sequence_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    events: List[Dict[str, Any]] = field(default_factory=list)
    duration: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "events": list(self.events),
            "duration": self.duration,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class DebugInfo:
    """Runtime debug information for the playground overlay.

    Attributes:
        session_id:    The session this debug info belongs to.
        state:         Current playground state.
        fps:           Current frames per second.
        frame_time_ms: Current frame time in milliseconds.
        entity_count:  Number of active entities.
        physics_bodies: Number of active physics bodies.
        memory_usage_mb: Estimated memory usage in megabytes.
        draw_calls:    Estimated number of draw calls.
        active_inputs: List of currently active input identifiers.
        hot_reload_enabled: Whether hot reload is active.
        hot_reload_path:    Watch path for hot reload (empty if disabled).
        warnings:      List of warning messages.
        errors:        List of error messages.
    """
    session_id: str = ""
    state: PlaygroundState = PlaygroundState.IDLE
    fps: float = 0.0
    frame_time_ms: float = 0.0
    entity_count: int = 0
    physics_bodies: int = 0
    memory_usage_mb: float = 0.0
    draw_calls: int = 0
    active_inputs: List[str] = field(default_factory=list)
    hot_reload_enabled: bool = False
    hot_reload_path: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "entity_count": self.entity_count,
            "physics_bodies": self.physics_bodies,
            "memory_usage_mb": self.memory_usage_mb,
            "draw_calls": self.draw_calls,
            "active_inputs": list(self.active_inputs),
            "hot_reload_enabled": self.hot_reload_enabled,
            "hot_reload_path": self.hot_reload_path,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


# ---------------------------------------------------------------------------
# Internal Subsystems
# ---------------------------------------------------------------------------


class SandboxRuntime:
    """Isolated runtime environment for game preview.

    Maintains a collection of RuntimeEntity instances and provides
    lifecycle management (add, remove, update, query) in an isolated
    sandboxed context.
    """

    def __init__(self) -> None:
        self._entities: Dict[str, RuntimeEntity] = {}
        self._entity_counter: int = 0

    def add_entity(self, entity: RuntimeEntity) -> str:
        """Add an entity to the sandbox and return its entity_id."""
        self._entities[entity.entity_id] = entity
        self._entity_counter += 1
        return entity.entity_id

    def remove_entity(self, entity_id: str) -> bool:
        """Remove an entity from the sandbox by ID. Returns True if removed."""
        if entity_id in self._entities:
            del self._entities[entity_id]
            return True
        return False

    def get_entity(self, entity_id: str) -> Optional[RuntimeEntity]:
        """Retrieve an entity by its ID, or None if not found."""
        return self._entities.get(entity_id)

    def get_all_entities(self) -> List[RuntimeEntity]:
        """Return all active entities in the sandbox."""
        return list(self._entities.values())

    def get_entities_by_tag(self, tag: str) -> List[RuntimeEntity]:
        """Return all entities matching a given tag."""
        return [e for e in self._entities.values() if tag in e.tags]

    def get_entities_by_layer(self, layer: int) -> List[RuntimeEntity]:
        """Return all entities on a given render layer."""
        return [e for e in self._entities.values() if e.layer == layer]

    def entity_count(self) -> int:
        """Return the total number of entities in the sandbox."""
        return len(self._entities)

    def update_entity(
        self,
        entity_id: str,
        position: Optional[Tuple[float, float]] = None,
        velocity: Optional[Tuple[float, float]] = None,
        rotation: Optional[float] = None,
        scale: Optional[Tuple[float, float]] = None,
        active: Optional[bool] = None,
    ) -> bool:
        """Update mutable properties of an entity. Returns True if updated."""
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        if position is not None:
            entity.position = position
        if velocity is not None:
            entity.velocity = velocity
        if rotation is not None:
            entity.rotation = rotation
        if scale is not None:
            entity.scale = scale
        if active is not None:
            entity.active = active
        return True

    def clear(self) -> None:
        """Remove all entities from the sandbox."""
        self._entities.clear()
        self._entity_counter = 0


class SceneLoader:
    """Loads scene definitions into the sandbox runtime.

    Parses raw scene data and instantiates RuntimeEntity objects
    from the scene graph definition.
    """

    def __init__(self) -> None:
        self._loaded_scenes: Dict[str, Dict[str, Any]] = {}

    def load_scene(self, scene_data: Dict[str, Any]) -> List[RuntimeEntity]:
        """Parse scene data and return a list of instantiated entities.

        The scene_data dict is expected to have an 'entities' key
        containing a list of entity definitions. Each definition
        should include name, position, velocity, rotation, scale,
        layer, tags, and optional components.
        """
        entities: List[RuntimeEntity] = []
        entity_defs = scene_data.get("entities", [])

        if not isinstance(entity_defs, list):
            return entities

        for entity_def in entity_defs:
            if not isinstance(entity_def, dict):
                continue

            entity = RuntimeEntity(
                name=entity_def.get("name", ""),
                position=tuple(entity_def.get("position", (0.0, 0.0))),
                velocity=tuple(entity_def.get("velocity", (0.0, 0.0))),
                rotation=entity_def.get("rotation", 0.0),
                scale=tuple(entity_def.get("scale", (1.0, 1.0))),
                active=entity_def.get("active", True),
                layer=entity_def.get("layer", 0),
                tags=entity_def.get("tags", []),
                components=entity_def.get("components", {}),
            )
            entities.append(entity)

        return entities

    def load_scene_from_dict(self, scene_id: str, scene_data: Dict[str, Any]) -> List[RuntimeEntity]:
        """Load and cache a scene definition, returning its entities."""
        self._loaded_scenes[scene_id] = scene_data
        return self.load_scene(scene_data)

    def get_scene_data(self, scene_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve cached scene data by ID."""
        return self._loaded_scenes.get(scene_id)

    def unload_scene(self, scene_id: str) -> bool:
        """Remove a cached scene definition. Returns True if removed."""
        if scene_id in self._loaded_scenes:
            del self._loaded_scenes[scene_id]
            return True
        return False

    def clear(self) -> None:
        """Remove all cached scene definitions."""
        self._loaded_scenes.clear()


class PhysicsSimulator:
    """Simple 2D physics simulator for testing game mechanics.

    Supports gravity, velocity integration, and basic AABB collision
    detection. Designed for sandbox preview — not for production physics.
    """

    def __init__(self) -> None:
        self._config = PhysicsConfig()
        self._bodies: Dict[str, RuntimeEntity] = {}
        self._elapsed: float = 0.0

    def configure(self, config: PhysicsConfig) -> None:
        """Apply a new physics configuration."""
        self._config = config

    def get_config(self) -> PhysicsConfig:
        """Return the current physics configuration."""
        return self._config

    def add_body(self, entity: RuntimeEntity) -> None:
        """Register an entity as a physics body."""
        self._bodies[entity.entity_id] = entity

    def remove_body(self, entity_id: str) -> bool:
        """Remove a physics body by entity ID. Returns True if removed."""
        if entity_id in self._bodies:
            del self._bodies[entity_id]
            return True
        return False

    def step(self, delta_time: float) -> List[Tuple[str, str]]:
        """Advance the physics simulation by delta_time seconds.

        Integrates velocity and position, applies gravity, and
        performs AABB collision detection.

        Returns:
            A list of (entity_id_a, entity_id_b) collision pairs.
        """
        if self._config.gravity == (0.0, 0.0):
            return []

        self._elapsed += delta_time
        collisions: List[Tuple[str, str]] = []

        # Integrate velocities and positions
        gx, gy = self._config.gravity
        for entity in self._bodies.values():
            if not entity.active:
                continue

            vx, vy = entity.velocity
            vx += gx * delta_time
            vy += gy * delta_time

            # Apply sleep threshold
            speed = math.sqrt(vx * vx + vy * vy)
            if self._config.enable_sleep and speed < self._config.sleep_threshold:
                vx, vy = 0.0, 0.0

            entity.velocity = (vx, vy)

            px, py = entity.position
            entity.position = (px + vx * delta_time, py + vy * delta_time)

            # Clamp to world bounds
            min_x, min_y, max_x, max_y = self._config.world_bounds
            cx, cy = entity.position
            cx = max(min_x, min(max_x, cx))
            cy = max(min_y, min(max_y, cy))
            entity.position = (cx, cy)

        # AABB collision detection
        body_list = list(self._bodies.values())
        for i in range(len(body_list)):
            for j in range(i + 1, len(body_list)):
                a = body_list[i]
                b = body_list[j]
                if not a.active or not b.active:
                    continue
                if self._check_aabb_collision(a, b):
                    collisions.append((a.entity_id, b.entity_id))

        return collisions

    @staticmethod
    def _check_aabb_collision(a: RuntimeEntity, b: RuntimeEntity) -> bool:
        """Check Axis-Aligned Bounding Box collision between two entities.

        Uses position as center and scale as half-extents for the AABB.
        """
        ax, ay = a.position
        asx, asy = a.scale
        a_half_w = abs(asx) * 0.5
        a_half_h = abs(asy) * 0.5

        bx, by = b.position
        bsx, bsy = b.scale
        b_half_w = abs(bsx) * 0.5
        b_half_h = abs(bsy) * 0.5

        return (
            abs(ax - bx) < (a_half_w + b_half_w)
            and abs(ay - by) < (a_half_h + b_half_h)
        )

    def body_count(self) -> int:
        """Return the number of active physics bodies."""
        return len(self._bodies)

    def clear(self) -> None:
        """Remove all physics bodies."""
        self._bodies.clear()
        self._elapsed = 0.0


class InputSimulator:
    """Simulates input for automated testing of game mechanics.

    Supports recording user input as InputSequence objects and
    replaying them for deterministic testing.
    """

    def __init__(self) -> None:
        self._recording: bool = False
        self._recorded_events: List[Dict[str, Any]] = []
        self._record_start_time: float = 0.0
        self._playback_sequence: Optional[InputSequence] = None
        self._playback_index: int = 0
        self._playback_start_time: float = 0.0
        self._active_inputs: Dict[str, bool] = {}

    def start_recording(self) -> None:
        """Begin recording input events."""
        self._recording = True
        self._recorded_events = []
        self._record_start_time = _time_module.time()

    def stop_recording(self) -> InputSequence:
        """Stop recording and return the captured InputSequence."""
        self._recording = False
        duration = _time_module.time() - self._record_start_time
        sequence = InputSequence(
            events=list(self._recorded_events),
            duration=duration,
        )
        self._recorded_events = []
        return sequence

    def record_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Record a single input event during a recording session."""
        if not self._recording:
            return
        self._recorded_events.append({
            "timestamp": _time_module.time() - self._record_start_time,
            "type": event_type,
            "data": dict(event_data),
        })

    def load_playback(self, sequence: InputSequence) -> None:
        """Load an InputSequence for playback."""
        self._playback_sequence = sequence
        self._playback_index = 0
        self._playback_start_time = _time_module.time()

    def stop_playback(self) -> None:
        """Stop the current input playback."""
        self._playback_sequence = None
        self._playback_index = 0
        self._active_inputs.clear()

    def get_playback_events(self) -> List[Dict[str, Any]]:
        """Get the next batch of events that should fire in this frame.

        Returns events whose timestamp falls within the elapsed time
        since the previous call.
        """
        if self._playback_sequence is None:
            return []

        elapsed = _time_module.time() - self._playback_start_time
        events: List[Dict[str, Any]] = []

        while self._playback_index < len(self._playback_sequence.events):
            event = self._playback_sequence.events[self._playback_index]
            if event["timestamp"] <= elapsed:
                events.append(event)
                self._playback_index += 1
            else:
                break

        # Update active inputs based on key events
        for event in events:
            if event["type"] in ("key_down", "key_press"):
                key = event["data"].get("key", "")
                if key:
                    self._active_inputs[key] = True
            elif event["type"] == "key_up":
                key = event["data"].get("key", "")
                if key:
                    self._active_inputs[key] = False

        return events

    def is_playback_complete(self) -> bool:
        """Check whether the current playback has finished."""
        if self._playback_sequence is None:
            return True
        elapsed = _time_module.time() - self._playback_start_time
        return elapsed >= self._playback_sequence.duration

    def get_active_inputs(self) -> List[str]:
        """Return a list of currently active input identifiers."""
        return [k for k, v in self._active_inputs.items() if v]

    def is_recording(self) -> bool:
        """Return whether the simulator is currently recording."""
        return self._recording

    def is_playing(self) -> bool:
        """Return whether the simulator is currently playing back."""
        return self._playback_sequence is not None

    def reset(self) -> None:
        """Reset all input state."""
        self._recording = False
        self._recorded_events = []
        self._playback_sequence = None
        self._playback_index = 0
        self._active_inputs.clear()


class GameLoop:
    """Fixed-timestep game loop with delta time for sandbox execution.

    Provides a deterministic update/render cycle with fixed-rate
    physics updates and variable-rate rendering.
    """

    def __init__(self) -> None:
        self._fixed_timestep: float = 0.016  # ~60 Hz
        self._accumulator: float = 0.0
        self._last_time: float = 0.0
        self._frame_count: int = 0
        self._total_time: float = 0.0
        self._fps_samples: List[float] = []
        self._max_delta: float = 0.25  # Cap to prevent spiral of death

        # Callback registries
        self._update_callbacks: List[Callable[[float], None]] = []
        self._fixed_update_callbacks: List[Callable[[float], None]] = []
        self._render_callbacks: List[Callable[[float], None]] = []

    def set_fixed_timestep(self, timestep: float) -> None:
        """Set the fixed physics timestep in seconds."""
        self._fixed_timestep = max(0.001, timestep)

    def on_update(self, callback: Callable[[float], None]) -> None:
        """Register a variable-rate update callback."""
        self._update_callbacks.append(callback)

    def on_fixed_update(self, callback: Callable[[float], None]) -> None:
        """Register a fixed-rate update callback."""
        self._fixed_update_callbacks.append(callback)

    def on_render(self, callback: Callable[[float], None]) -> None:
        """Register a render callback."""
        self._render_callbacks.append(callback)

    def step(self) -> FrameMetrics:
        """Execute one tick of the game loop and return FrameMetrics.

        Handles frame timing, accumulator-based fixed updates,
        variable updates, and rendering.
        """
        current_time = _time_module.time()

        if self._last_time == 0.0:
            self._last_time = current_time
            self._frame_count += 1
            return FrameMetrics(frame_id=self._frame_count)

        frame_delta = current_time - self._last_time
        self._last_time = current_time

        # Clamp delta to prevent spiral of death
        if frame_delta > self._max_delta:
            frame_delta = self._max_delta

        self._total_time += frame_delta
        self._frame_count += 1

        # Track FPS
        self._fps_samples.append(1.0 / max(frame_delta, 0.0001))
        if len(self._fps_samples) > 60:
            self._fps_samples = self._fps_samples[-30:]

        # Fixed update phase
        self._accumulator += frame_delta
        fixed_updates = 0
        physics_start = _time_module.time()
        while self._accumulator >= self._fixed_timestep:
            self._accumulator -= self._fixed_timestep
            fixed_updates += 1
            for callback in self._fixed_update_callbacks:
                callback(self._fixed_timestep)
        physics_time = (_time_module.time() - physics_start) * 1000.0

        # Variable update phase
        update_start = _time_module.time()
        for callback in self._update_callbacks:
            callback(frame_delta)
        update_time = (_time_module.time() - update_start) * 1000.0

        # Render phase
        render_start = _time_module.time()
        for callback in self._render_callbacks:
            callback(frame_delta)
        render_time = (_time_module.time() - render_start) * 1000.0

        avg_fps = sum(self._fps_samples) / len(self._fps_samples) if self._fps_samples else 0.0

        return FrameMetrics(
            frame_id=self._frame_count,
            delta_time=frame_delta,
            fps=avg_fps,
            update_time_ms=update_time,
            physics_time_ms=physics_time,
            render_time_ms=render_time,
        )

    def get_frame_count(self) -> int:
        """Return the total number of frames processed."""
        return self._frame_count

    def get_total_time(self) -> float:
        """Return the total elapsed time in seconds."""
        return self._total_time

    def reset(self) -> None:
        """Reset the game loop state."""
        self._accumulator = 0.0
        self._last_time = 0.0
        self._frame_count = 0
        self._total_time = 0.0
        self._fps_samples.clear()


class PerformanceMonitor:
    """Monitors FPS, memory, and frame timing for the playground.

    Tracks frame metrics over time and provides statistical summaries
    for runtime performance analysis.
    """

    MAX_FRAME_HISTORY: int = 600

    def __init__(self) -> None:
        self._frame_history: List[FrameMetrics] = []
        self._total_frames: int = 0
        self._min_fps: float = float("inf")
        self._max_fps: float = 0.0
        self._memory_baseline: float = 0.0

    def record_frame(self, metrics: FrameMetrics) -> None:
        """Record a frame's metrics for performance tracking."""
        metrics.memory_usage_mb = self._estimate_memory_usage()
        self._frame_history.append(metrics)
        self._total_frames += 1

        # Track min/max FPS
        if metrics.fps > 0:
            if metrics.fps < self._min_fps:
                self._min_fps = metrics.fps
            if metrics.fps > self._max_fps:
                self._max_fps = metrics.fps

        # Trim history
        if len(self._frame_history) > self.MAX_FRAME_HISTORY:
            self._frame_history = self._frame_history[-self.MAX_FRAME_HISTORY:]

    def get_latest_metrics(self) -> Optional[FrameMetrics]:
        """Return the most recent FrameMetrics, or None if no frames recorded."""
        return self._frame_history[-1] if self._frame_history else None

    def get_frame_history(self, limit: int = 100) -> List[FrameMetrics]:
        """Return the most recent frame metrics, newest first."""
        frames = list(self._frame_history)
        return frames[-limit:][::-1]

    def get_stats(self) -> Dict[str, Any]:
        """Compute and return aggregate performance statistics."""
        recent = self._frame_history[-60:]
        if not recent:
            return {
                "total_frames": self._total_frames,
                "avg_fps": 0.0,
                "min_fps": 0.0,
                "max_fps": 0.0,
                "avg_frame_time_ms": 0.0,
                "avg_update_time_ms": 0.0,
                "avg_physics_time_ms": 0.0,
                "avg_render_time_ms": 0.0,
                "avg_memory_usage_mb": 0.0,
            }

        n = len(recent)
        avg_fps = sum(m.fps for m in recent) / n
        avg_frame_time = sum(m.delta_time for m in recent) / n * 1000.0
        avg_update_time = sum(m.update_time_ms for m in recent) / n
        avg_physics_time = sum(m.physics_time_ms for m in recent) / n
        avg_render_time = sum(m.render_time_ms for m in recent) / n
        avg_memory = sum(m.memory_usage_mb for m in recent) / n

        return {
            "total_frames": self._total_frames,
            "avg_fps": round(avg_fps, 1),
            "min_fps": round(self._min_fps, 1) if self._min_fps != float("inf") else 0.0,
            "max_fps": round(self._max_fps, 1),
            "avg_frame_time_ms": round(avg_frame_time, 2),
            "avg_update_time_ms": round(avg_update_time, 2),
            "avg_physics_time_ms": round(avg_physics_time, 2),
            "avg_render_time_ms": round(avg_render_time, 2),
            "avg_memory_usage_mb": round(avg_memory, 2),
        }

    @staticmethod
    def _estimate_memory_usage() -> float:
        """Estimate memory usage in megabytes (placeholder)."""
        # In a real implementation this would query system APIs.
        return 64.0

    def reset(self) -> None:
        """Reset all performance tracking data."""
        self._frame_history.clear()
        self._total_frames = 0
        self._min_fps = float("inf")
        self._max_fps = 0.0


class HotReload:
    """Watches for scene changes and reloads automatically.

    Monitors a file path for modifications and triggers scene reload
    callbacks when changes are detected. Uses polling-based file
    modification time tracking.
    """

    def __init__(self) -> None:
        self._enabled: bool = False
        self._watch_path: str = ""
        self._last_mtime: float = 0.0
        self._poll_interval: float = 1.0
        self._last_poll: float = 0.0
        self._change_callbacks: List[Callable[[str], None]] = []
        self._error_callbacks: List[Callable[[str, str], None]] = []

    def enable(self, watch_path: str, poll_interval: float = 1.0) -> None:
        """Enable hot reload monitoring on the given path.

        Args:
            watch_path:     File or directory path to monitor.
            poll_interval:  Seconds between modification time checks.
        """
        self._enabled = True
        self._watch_path = watch_path
        self._poll_interval = max(0.1, poll_interval)
        self._last_poll = _time_module.time()

        if os.path.exists(watch_path):
            self._last_mtime = os.path.getmtime(watch_path)

    def disable(self) -> None:
        """Disable hot reload monitoring."""
        self._enabled = False
        self._watch_path = ""
        self._last_mtime = 0.0

    def is_enabled(self) -> bool:
        """Return whether hot reload is currently active."""
        return self._enabled

    def get_watch_path(self) -> str:
        """Return the current watch path, or empty string if disabled."""
        return self._watch_path if self._enabled else ""

    def on_change(self, callback: Callable[[str], None]) -> None:
        """Register a callback invoked when a file change is detected.

        The callback receives the watch path as its argument.
        """
        self._change_callbacks.append(callback)

    def on_error(self, callback: Callable[[str, str], None]) -> None:
        """Register a callback invoked when a watch error occurs.

        The callback receives (watch_path, error_message).
        """
        self._error_callbacks.append(callback)

    def poll(self) -> bool:
        """Check for file changes and invoke callbacks if detected.

        Returns True if a change was detected, False otherwise.
        """
        if not self._enabled or not self._watch_path:
            return False

        current_time = _time_module.time()
        if current_time - self._last_poll < self._poll_interval:
            return False

        self._last_poll = current_time

        try:
            if not os.path.exists(self._watch_path):
                for cb in self._error_callbacks:
                    cb(self._watch_path, "Watch path does not exist")
                return False

            current_mtime = os.path.getmtime(self._watch_path)
            if current_mtime != self._last_mtime:
                self._last_mtime = current_mtime
                for cb in self._change_callbacks:
                    cb(self._watch_path)
                return True
        except OSError as e:
            for cb in self._error_callbacks:
                cb(self._watch_path, str(e))

        return False

    def reset(self) -> None:
        """Reset hot reload state."""
        self._enabled = False
        self._watch_path = ""
        self._last_mtime = 0.0
        self._change_callbacks.clear()
        self._error_callbacks.clear()


class DebugOverlay:
    """Runtime debug information overlay for in-game display.

    Collects and formats debug information from all subsystems
    for display as an on-screen overlay during playtesting.
    """

    def __init__(self) -> None:
        self._visible: bool = True
        self._warnings: List[str] = []
        self._errors: List[str] = []
        self._custom_info: Dict[str, str] = {}

    def set_visible(self, visible: bool) -> None:
        """Show or hide the debug overlay."""
        self._visible = visible

    def is_visible(self) -> bool:
        """Return whether the debug overlay is currently visible."""
        return self._visible

    def add_warning(self, message: str) -> None:
        """Add a warning message to the overlay."""
        self._warnings.append(message)
        if len(self._warnings) > 100:
            self._warnings = self._warnings[-50:]

    def add_error(self, message: str) -> None:
        """Add an error message to the overlay."""
        self._errors.append(message)
        if len(self._errors) > 100:
            self._errors = self._errors[-50:]

    def set_custom_info(self, key: str, value: str) -> None:
        """Set a custom key-value pair for display in the overlay."""
        self._custom_info[key] = value

    def remove_custom_info(self, key: str) -> bool:
        """Remove a custom info entry. Returns True if removed."""
        if key in self._custom_info:
            del self._custom_info[key]
            return True
        return False

    def get_info(self) -> Dict[str, Any]:
        """Return all current debug overlay information."""
        return {
            "visible": self._visible,
            "warnings": list(self._warnings),
            "errors": list(self._errors),
            "custom": dict(self._custom_info),
        }

    def get_warnings(self) -> List[str]:
        """Return current warning messages."""
        return list(self._warnings)

    def get_errors(self) -> List[str]:
        """Return current error messages."""
        return list(self._errors)

    def clear(self) -> None:
        """Clear all warnings, errors, and custom info."""
        self._warnings.clear()
        self._errors.clear()
        self._custom_info.clear()


# ---------------------------------------------------------------------------
# EngineGamePlayground — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineGamePlayground:
    """
    Sandbox Game Runtime for the SparkLabs AI-native game engine.

    Provides instant preview and testing of game mechanics in a
    sandboxed environment. Manages the full lifecycle of preview
    sessions including scene loading, physics simulation, input
    simulation, game loop execution, performance monitoring,
    hot reload, and debug overlay.

    Thread-safe via a reentrant lock. Use get_game_playground() or
    EngineGamePlayground.get_instance() to obtain the singleton.

    Usage:
        playground = get_game_playground()
        session = playground.create_session(scene_data)
        playground.start_session(session.session_id)
        metrics = playground.step_frame(session.session_id)
        playground.stop_session(session.session_id)
    """

    _instance: Optional["EngineGamePlayground"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "EngineGamePlayground":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        # Session registry
        self._sessions: Dict[str, PlaygroundSession] = {}

        # Per-session subsystems
        self._sandbox_runtimes: Dict[str, SandboxRuntime] = {}
        self._scene_loaders: Dict[str, SceneLoader] = {}
        self._physics_simulators: Dict[str, PhysicsSimulator] = {}
        self._input_simulators: Dict[str, InputSimulator] = {}
        self._game_loops: Dict[str, GameLoop] = {}
        self._performance_monitors: Dict[str, PerformanceMonitor] = {}
        self._hot_reloads: Dict[str, HotReload] = {}
        self._debug_overlays: Dict[str, DebugOverlay] = {}

        # Global statistics
        self._total_sessions_created: int = 0
        self._total_sessions_started: int = 0
        self._total_frames_processed: int = 0

    @classmethod
    def get_instance(cls) -> "EngineGamePlayground":
        """Return the singleton EngineGamePlayground instance."""
        return cls()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_session(self, session_id: str) -> PlaygroundSession:
        """Retrieve a session by ID, raising KeyError if not found."""
        if session_id not in self._sessions:
            raise KeyError(f"Playground session not found: {session_id}")
        return self._sessions[session_id]

    def _get_or_create_subsystem(self, registry: Dict[str, Any], session_id: str,
                                  factory: Callable[[], Any]) -> Any:
        """Get or create a subsystem instance for a session."""
        if session_id not in registry:
            registry[session_id] = factory()
        return registry[session_id]

    def _ensure_session_running(self, session_id: str) -> PlaygroundSession:
        """Verify a session exists and is in RUNNING state."""
        session = self._get_session(session_id)
        if session.state != PlaygroundState.RUNNING:
            raise RuntimeError(
                f"Session {session_id} is not running (state: {session.state.value})"
            )
        return session

    def _cleanup_session_subsystems(self, session_id: str) -> None:
        """Remove all subsystem instances for a session."""
        self._sandbox_runtimes.pop(session_id, None)
        self._scene_loaders.pop(session_id, None)
        self._physics_simulators.pop(session_id, None)
        self._input_simulators.pop(session_id, None)
        self._game_loops.pop(session_id, None)
        self._performance_monitors.pop(session_id, None)
        self._hot_reloads.pop(session_id, None)
        self._debug_overlays.pop(session_id, None)

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def create_session(
        self,
        scene_data: Dict[str, Any],
        physics_mode: PhysicsMode = PhysicsMode.SIMPLE,
        input_mode: InputMode = InputMode.MANUAL,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlaygroundSession:
        """Create a new playground session with the given scene data.

        Instantiates all subsystems for the session and loads the
        scene entities into the sandbox runtime.

        Args:
            scene_data:   Raw scene definition containing entity data.
            physics_mode: Physics simulation fidelity level.
            input_mode:   Input handling mode.
            metadata:     Optional metadata for the session.

        Returns:
            A new PlaygroundSession in IDLE state.
        """
        with self._lock:
            session = PlaygroundSession(
                scene_data=dict(scene_data),
                state=PlaygroundState.IDLE,
                physics_mode=physics_mode,
                input_mode=input_mode,
                metadata=metadata or {},
            )

            self._sessions[session.session_id] = session
            self._total_sessions_created += 1

            # Initialize subsystems
            sandbox = self._get_or_create_subsystem(
                self._sandbox_runtimes, session.session_id, SandboxRuntime
            )
            scene_loader = self._get_or_create_subsystem(
                self._scene_loaders, session.session_id, SceneLoader
            )
            physics = self._get_or_create_subsystem(
                self._physics_simulators, session.session_id, PhysicsSimulator
            )
            self._get_or_create_subsystem(
                self._input_simulators, session.session_id, InputSimulator
            )
            self._get_or_create_subsystem(
                self._game_loops, session.session_id, GameLoop
            )
            self._get_or_create_subsystem(
                self._performance_monitors, session.session_id, PerformanceMonitor
            )
            self._get_or_create_subsystem(
                self._hot_reloads, session.session_id, HotReload
            )
            self._get_or_create_subsystem(
                self._debug_overlays, session.session_id, DebugOverlay
            )

            # Load scene entities into sandbox
            entities = scene_loader.load_scene(scene_data)
            for entity in entities:
                sandbox.add_entity(entity)
                if physics_mode != PhysicsMode.NONE:
                    physics.add_body(entity)

            session.entity_count = sandbox.entity_count()

            return session

    def get_session(self, session_id: str) -> Optional[PlaygroundSession]:
        """Retrieve a session by its ID, or None if not found."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(
        self,
        state: Optional[PlaygroundState] = None,
    ) -> List[PlaygroundSession]:
        """List all sessions, optionally filtered by state."""
        with self._lock:
            if state is not None:
                return [s for s in self._sessions.values() if s.state == state]
            return list(self._sessions.values())

    def remove_session(self, session_id: str) -> bool:
        """Remove a session and all its subsystems. Returns True if removed."""
        with self._lock:
            if session_id not in self._sessions:
                return False

            session = self._sessions[session_id]
            if session.state == PlaygroundState.RUNNING:
                self._stop_session_internal(session_id)

            del self._sessions[session_id]
            self._cleanup_session_subsystems(session_id)
            return True

    # ------------------------------------------------------------------
    # Session Lifecycle
    # ------------------------------------------------------------------

    def start_session(self, session_id: str) -> PlaygroundSession:
        """Start a playground session, transitioning it to RUNNING.

        Initializes the game loop and begins frame processing.

        Args:
            session_id: The session to start.

        Returns:
            The updated PlaygroundSession.

        Raises:
            KeyError: If the session does not exist.
            RuntimeError: If the session is not in IDLE or STOPPED state.
        """
        with self._lock:
            session = self._get_session(session_id)

            if session.state not in (PlaygroundState.IDLE, PlaygroundState.STOPPED):
                raise RuntimeError(
                    f"Cannot start session in state: {session.state.value}"
                )

            session.state = PlaygroundState.LOADING

            # Re-load entities if needed
            sandbox = self._sandbox_runtimes.get(session_id)
            scene_loader = self._scene_loaders.get(session_id)
            physics = self._physics_simulators.get(session_id)

            if sandbox is not None and scene_loader is not None:
                sandbox.clear()
                entities = scene_loader.load_scene(session.scene_data)
                for entity in entities:
                    sandbox.add_entity(entity)
                    if session.physics_mode != PhysicsMode.NONE and physics is not None:
                        physics.add_body(entity)
                session.entity_count = sandbox.entity_count()

            # Reset game loop
            game_loop = self._game_loops.get(session_id)
            if game_loop is not None:
                game_loop.reset()

            # Reset performance monitor
            perf_monitor = self._performance_monitors.get(session_id)
            if perf_monitor is not None:
                perf_monitor.reset()

            session.state = PlaygroundState.RUNNING
            session.started_at = _time_module.time()
            session.total_frames = 0
            session.total_time = 0.0
            session.error_message = ""
            self._total_sessions_started += 1

            return session

    def pause_session(self, session_id: str) -> PlaygroundSession:
        """Pause a running playground session.

        Args:
            session_id: The session to pause.

        Returns:
            The updated PlaygroundSession.

        Raises:
            KeyError: If the session does not exist.
            RuntimeError: If the session is not running.
        """
        with self._lock:
            session = self._ensure_session_running(session_id)
            session.state = PlaygroundState.PAUSED
            session.paused_at = _time_module.time()
            return session

    def resume_session(self, session_id: str) -> PlaygroundSession:
        """Resume a paused playground session.

        Args:
            session_id: The session to resume.

        Returns:
            The updated PlaygroundSession.

        Raises:
            KeyError: If the session does not exist.
            RuntimeError: If the session is not paused.
        """
        with self._lock:
            session = self._get_session(session_id)
            if session.state != PlaygroundState.PAUSED:
                raise RuntimeError(
                    f"Cannot resume session in state: {session.state.value}"
                )

            session.state = PlaygroundState.RUNNING
            session.paused_at = 0.0

            # Reset game loop timing to avoid huge delta
            game_loop = self._game_loops.get(session_id)
            if game_loop is not None:
                game_loop.reset()

            return session

    def stop_session(self, session_id: str) -> PlaygroundSession:
        """Stop a running or paused playground session.

        Args:
            session_id: The session to stop.

        Returns:
            The updated PlaygroundSession.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            return self._stop_session_internal(session_id)

    def _stop_session_internal(self, session_id: str) -> PlaygroundSession:
        """Internal session stop without lock acquisition."""
        session = self._get_session(session_id)

        if session.state in (PlaygroundState.STOPPED, PlaygroundState.IDLE):
            return session

        # Disable hot reload if active
        hot_reload = self._hot_reloads.get(session_id)
        if hot_reload is not None and hot_reload.is_enabled():
            hot_reload.disable()

        session.state = PlaygroundState.STOPPED
        return session

    # ------------------------------------------------------------------
    # Frame Execution
    # ------------------------------------------------------------------

    def step_frame(self, session_id: str) -> FrameMetrics:
        """Execute a single frame of the game loop for a session.

        Processes input replay, runs the game loop (updates, fixed
        updates, render), polls hot reload, and records performance
        metrics.

        Args:
            session_id: The session to step.

        Returns:
            FrameMetrics for the processed frame.

        Raises:
            KeyError: If the session does not exist.
            RuntimeError: If the session is not running.
        """
        with self._lock:
            session = self._ensure_session_running(session_id)

            game_loop = self._game_loops.get(session_id)
            if game_loop is None:
                raise RuntimeError(f"Game loop not initialized for session {session_id}")

            physics = self._physics_simulators.get(session_id)
            input_sim = self._input_simulators.get(session_id)
            sandbox = self._sandbox_runtimes.get(session_id)
            perf_monitor = self._performance_monitors.get(session_id)
            hot_reload = self._hot_reloads.get(session_id)
            debug_overlay = self._debug_overlays.get(session_id)

            # Process input playback
            if input_sim is not None and input_sim.is_playing():
                input_sim.get_playback_events()
                if input_sim.is_playback_complete():
                    input_sim.stop_playback()
                    session.input_mode = InputMode.MANUAL

            # Run game loop
            metrics = game_loop.step()

            # Update session counters
            session.total_frames = game_loop.get_frame_count()
            session.total_time = game_loop.get_total_time()

            # Populate entity count
            if sandbox is not None:
                metrics.entity_count = sandbox.entity_count()
                session.entity_count = sandbox.entity_count()

            # Record performance
            if perf_monitor is not None:
                perf_monitor.record_frame(metrics)

            # Poll hot reload
            if hot_reload is not None and hot_reload.is_enabled():
                hot_reload.poll()

            # Update debug overlay
            if debug_overlay is not None and debug_overlay.is_visible():
                if physics is not None:
                    debug_overlay.set_custom_info("physics_bodies", str(physics.body_count()))
                debug_overlay.set_custom_info("fps", f"{metrics.fps:.1f}")
                debug_overlay.set_custom_info("frame_time", f"{metrics.delta_time * 1000.0:.1f}ms")

            self._total_frames_processed += 1

            return metrics

    # ------------------------------------------------------------------
    # Input Simulation
    # ------------------------------------------------------------------

    def simulate_input(
        self,
        session_id: str,
        input_sequence: InputSequence,
    ) -> bool:
        """Load an input sequence for playback in the session.

        The session's input mode is set to PLAYBACK and the sequence
        will be replayed frame by frame as step_frame() is called.

        Args:
            session_id:     The session to simulate input in.
            input_sequence: The recorded InputSequence to replay.

        Returns:
            True if playback started, False otherwise.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            session = self._get_session(session_id)
            input_sim = self._input_simulators.get(session_id)

            if input_sim is None:
                return False

            input_sim.load_playback(input_sequence)
            session.input_mode = InputMode.PLAYBACK
            return True

    def record_input(self, session_id: str) -> InputSequence:
        """Start recording input for a session and return the sequence.

        Begins capturing input events. The recording continues until
        stop_recording() is called on the input simulator.

        Args:
            session_id: The session to record input from.

        Returns:
            An empty InputSequence that will be populated during recording.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            session = self._get_session(session_id)
            input_sim = self._input_simulators.get(session_id)

            if input_sim is None:
                input_sim = InputSimulator()
                self._input_simulators[session_id] = input_sim

            input_sim.start_recording()
            session.input_mode = InputMode.RECORDING

            # Return a placeholder; actual data is filled during recording
            return InputSequence()

    def stop_recording(self, session_id: str) -> Optional[InputSequence]:
        """Stop recording and return the captured InputSequence.

        Args:
            session_id: The session to stop recording.

        Returns:
            The captured InputSequence, or None if not recording.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            session = self._get_session(session_id)
            input_sim = self._input_simulators.get(session_id)

            if input_sim is None or not input_sim.is_recording():
                return None

            sequence = input_sim.stop_recording()
            session.input_mode = InputMode.MANUAL
            return sequence

    def record_input_event(
        self,
        session_id: str,
        event_type: str,
        event_data: Dict[str, Any],
    ) -> bool:
        """Record a single input event during an active recording session.

        Args:
            session_id:  The session being recorded.
            event_type:  Type of input event (e.g., 'key_down', 'mouse_move').
            event_data:  Event-specific data.

        Returns:
            True if recorded, False if not currently recording.
        """
        with self._lock:
            input_sim = self._input_simulators.get(session_id)
            if input_sim is None or not input_sim.is_recording():
                return False
            input_sim.record_event(event_type, event_data)
            return True

    def get_active_inputs(self, session_id: str) -> List[str]:
        """Get currently active input identifiers for a session.

        Returns a list of active keys/buttons during playback or manual mode.
        """
        with self._lock:
            input_sim = self._input_simulators.get(session_id)
            if input_sim is None:
                return []
            return input_sim.get_active_inputs()

    # ------------------------------------------------------------------
    # Debug & Performance
    # ------------------------------------------------------------------

    def get_debug_info(self, session_id: str) -> DebugInfo:
        """Get comprehensive runtime debug information for a session.

        Aggregates data from all subsystems including FPS, entity count,
        physics bodies, memory usage, input state, and hot reload status.

        Args:
            session_id: The session to query.

        Returns:
            DebugInfo with current runtime state.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            session = self._get_session(session_id)

            sandbox = self._sandbox_runtimes.get(session_id)
            physics = self._physics_simulators.get(session_id)
            input_sim = self._input_simulators.get(session_id)
            perf_monitor = self._performance_monitors.get(session_id)
            hot_reload = self._hot_reloads.get(session_id)
            debug_overlay = self._debug_overlays.get(session_id)

            latest_metrics = perf_monitor.get_latest_metrics() if perf_monitor else None

            return DebugInfo(
                session_id=session_id,
                state=session.state,
                fps=latest_metrics.fps if latest_metrics else 0.0,
                frame_time_ms=latest_metrics.delta_time * 1000.0 if latest_metrics else 0.0,
                entity_count=sandbox.entity_count() if sandbox else 0,
                physics_bodies=physics.body_count() if physics else 0,
                memory_usage_mb=latest_metrics.memory_usage_mb if latest_metrics else 0.0,
                draw_calls=0,
                active_inputs=input_sim.get_active_inputs() if input_sim else [],
                hot_reload_enabled=hot_reload.is_enabled() if hot_reload else False,
                hot_reload_path=hot_reload.get_watch_path() if hot_reload else "",
                warnings=debug_overlay.get_warnings() if debug_overlay else [],
                errors=debug_overlay.get_errors() if debug_overlay else [],
            )

    def get_performance(self, session_id: str) -> Optional[FrameMetrics]:
        """Get the latest frame metrics for a session.

        Args:
            session_id: The session to query.

        Returns:
            The most recent FrameMetrics, or None if no frames processed.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            perf_monitor = self._performance_monitors.get(session_id)
            if perf_monitor is None:
                return None
            return perf_monitor.get_latest_metrics()

    def get_performance_stats(self, session_id: str) -> Dict[str, Any]:
        """Get aggregate performance statistics for a session.

        Args:
            session_id: The session to query.

        Returns:
            Dict with FPS, frame time, memory, and other stats.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            perf_monitor = self._performance_monitors.get(session_id)
            if perf_monitor is None:
                return {}
            return perf_monitor.get_stats()

    # ------------------------------------------------------------------
    # Hot Reload
    # ------------------------------------------------------------------

    def enable_hot_reload(
        self,
        session_id: str,
        watch_path: str,
        poll_interval: float = 1.0,
    ) -> bool:
        """Enable hot reload monitoring for a session.

        When a change is detected on the watch path, the scene data is
        automatically reloaded into the sandbox.

        Args:
            session_id:    The session to enable hot reload on.
            watch_path:    File or directory path to monitor.
            poll_interval: Seconds between checks.

        Returns:
            True if enabled, False if session not found.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            session = self._get_session(session_id)
            hot_reload = self._hot_reloads.get(session_id)

            if hot_reload is None:
                hot_reload = HotReload()
                self._hot_reloads[session_id] = hot_reload

            # Register auto-reload callback
            def auto_reload(path: str) -> None:
                with self._lock:
                    sandbox = self._sandbox_runtimes.get(session_id)
                    scene_loader = self._scene_loaders.get(session_id)
                    physics = self._physics_simulators.get(session_id)
                    debug_overlay = self._debug_overlays.get(session_id)

                    if sandbox is None or scene_loader is None:
                        return

                    try:
                        sandbox.clear()
                        if physics is not None:
                            physics.clear()

                        entities = scene_loader.load_scene(session.scene_data)
                        for entity in entities:
                            sandbox.add_entity(entity)
                            if session.physics_mode != PhysicsMode.NONE and physics is not None:
                                physics.add_body(entity)

                        session.entity_count = sandbox.entity_count()

                        if debug_overlay is not None:
                            debug_overlay.set_custom_info(
                                "hot_reload", f"Reloaded at {_time_module.time():.0f}"
                            )
                    except Exception as e:
                        if debug_overlay is not None:
                            debug_overlay.add_error(f"Hot reload failed: {e}")

            hot_reload.on_change(auto_reload)

            def on_watch_error(path: str, error: str) -> None:
                debug_overlay = self._debug_overlays.get(session_id)
                if debug_overlay is not None:
                    debug_overlay.add_error(f"Hot reload watch error: {error}")

            hot_reload.on_error(on_watch_error)

            hot_reload.enable(watch_path, poll_interval)
            return True

    def disable_hot_reload(self, session_id: str) -> bool:
        """Disable hot reload monitoring for a session.

        Args:
            session_id: The session to disable hot reload on.

        Returns:
            True if disabled, False if not enabled.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            hot_reload = self._hot_reloads.get(session_id)
            if hot_reload is None or not hot_reload.is_enabled():
                return False
            hot_reload.disable()
            return True

    # ------------------------------------------------------------------
    # Physics Configuration
    # ------------------------------------------------------------------

    def set_physics_config(
        self,
        session_id: str,
        config: PhysicsConfig,
    ) -> bool:
        """Apply a physics configuration to a session.

        Args:
            session_id: The session to configure.
            config:     The physics configuration to apply.

        Returns:
            True if applied, False if session not found.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            physics = self._physics_simulators.get(session_id)
            if physics is None:
                return False
            physics.configure(config)
            return True

    def get_physics_config(self, session_id: str) -> Optional[PhysicsConfig]:
        """Get the current physics configuration for a session.

        Args:
            session_id: The session to query.

        Returns:
            The PhysicsConfig, or None if not available.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            physics = self._physics_simulators.get(session_id)
            if physics is None:
                return None
            return physics.get_config()

    # ------------------------------------------------------------------
    # Debug Overlay
    # ------------------------------------------------------------------

    def set_debug_overlay_visible(self, session_id: str, visible: bool) -> bool:
        """Show or hide the debug overlay for a session.

        Args:
            session_id: The session to configure.
            visible:    True to show, False to hide.

        Returns:
            True if toggled, False if session not found.

        Raises:
            KeyError: If the session does not exist.
        """
        with self._lock:
            self._get_session(session_id)
            debug_overlay = self._debug_overlays.get(session_id)
            if debug_overlay is None:
                return False
            debug_overlay.set_visible(visible)
            return True

    def add_debug_warning(self, session_id: str, message: str) -> bool:
        """Add a warning message to the session's debug overlay.

        Args:
            session_id: The session to add the warning to.
            message:    The warning message.

        Returns:
            True if added, False if session not found.
        """
        with self._lock:
            self._get_session(session_id)
            debug_overlay = self._debug_overlays.get(session_id)
            if debug_overlay is None:
                return False
            debug_overlay.add_warning(message)
            return True

    def add_debug_error(self, session_id: str, message: str) -> bool:
        """Add an error message to the session's debug overlay.

        Args:
            session_id: The session to add the error to.
            message:    The error message.

        Returns:
            True if added, False if session not found.
        """
        with self._lock:
            self._get_session(session_id)
            debug_overlay = self._debug_overlays.get(session_id)
            if debug_overlay is None:
                return False
            debug_overlay.add_error(message)
            return True

    # ------------------------------------------------------------------
    # Status & Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the entire playground.

        Returns:
            Dict with session counts, state distribution, and global stats.
        """
        with self._lock:
            state_distribution: Dict[str, int] = {}
            for session in self._sessions.values():
                state_key = session.state.value
                state_distribution[state_key] = state_distribution.get(state_key, 0) + 1

            active_sessions = [
                s for s in self._sessions.values()
                if s.state == PlaygroundState.RUNNING
            ]

            return {
                "total_sessions": len(self._sessions),
                "total_sessions_created": self._total_sessions_created,
                "total_sessions_started": self._total_sessions_started,
                "total_frames_processed": self._total_frames_processed,
                "state_distribution": state_distribution,
                "active_sessions": len(active_sessions),
                "active_session_ids": [s.session_id for s in active_sessions],
                "paused_sessions": sum(
                    1 for s in self._sessions.values()
                    if s.state == PlaygroundState.PAUSED
                ),
                "error_sessions": sum(
                    1 for s in self._sessions.values()
                    if s.state == PlaygroundState.ERROR
                ),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics (alias for get_status)."""
        return self.get_status()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire playground, clearing all sessions and subsystems."""
        with self._lock:
            for session_id in list(self._sessions.keys()):
                hot_reload = self._hot_reloads.get(session_id)
                if hot_reload is not None:
                    hot_reload.disable()

            self._sessions.clear()
            self._sandbox_runtimes.clear()
            self._scene_loaders.clear()
            self._physics_simulators.clear()
            self._input_simulators.clear()
            self._game_loops.clear()
            self._performance_monitors.clear()
            self._hot_reloads.clear()
            self._debug_overlays.clear()

            self._total_sessions_created = 0
            self._total_sessions_started = 0
            self._total_frames_processed = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_game_playground() -> EngineGamePlayground:
    """Return the singleton EngineGamePlayground instance.

    Usage:
        playground = get_game_playground()
        session = playground.create_session(scene_data)
        playground.start_session(session.session_id)
    """
    return EngineGamePlayground.get_instance()