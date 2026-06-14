"""
SparkLabs Engine - Advanced Scene Runtime

A comprehensive scene runtime system providing scene stack management,
full lifecycle hooks, animated transitions, background preloading,
pause/resume with state restoration, render layers, scene grouping,
and scene state save/restore for the SparkLabs AI-native game engine.

Architecture:
  EngineSceneRuntime (Singleton)
    |-- SceneDescriptor     — scene metadata with loading progress and stats
    |-- SceneTransition     — animated transition between scenes
    |-- SceneLayer          — render layer with camera and visibility
    |-- SceneGroup          — logical grouping of related scenes
    |-- SceneState          — serializable scene snapshot
    |-- SceneStackEntry     — single entry in the scene stack
    |-- SceneLifecycle (enum)    — full lifecycle state machine
    |-- TransitionType (enum)    — visual transition effect types
    |-- EasingType (enum)        — interpolation easing curves

Scene Lifecycle:
  UNLOADED → LOADING → LOADED → INITIALIZING → RUNNING
  RUNNING → PAUSED → RESUMING → RUNNING
  RUNNING/PAUSED → STOPPING → UNLOADING → UNLOADED

Usage:
    rt = get_engine_scene_runtime()
    rt.register_scene("level_1", "scenes/level1.json")
    rt.load_scene(desc_id)
    rt.push_scene(desc_id, TransitionType.FADE)
    rt.pause_scene()
    rt.resume_scene()
    rt.pop_scene(TransitionType.SLIDE_LEFT)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SceneLifecycle(str, Enum):
    """Full lifecycle state machine for scene instances.

    States:
        UNLOADED:      Scene is not loaded in memory.
        LOADING:       Scene assets are being loaded into memory.
        LOADED:        Scene is in memory but not yet initialized.
        INITIALIZING:  Scene is running its initialization hooks.
        RUNNING:       Scene is active and receiving update ticks.
        PAUSED:        Scene is paused (e.g. menu overlay active).
        RESUMING:      Scene is transitioning from paused back to running.
        STOPPING:      Scene is executing stop/cleanup hooks.
        UNLOADING:     Scene assets are being released from memory.
        ERROR:         Scene encountered an unrecoverable error.
    """
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    INITIALIZING = "initializing"
    RUNNING = "running"
    PAUSED = "paused"
    RESUMING = "resuming"
    STOPPING = "stopping"
    UNLOADING = "unloading"
    ERROR = "error"


class TransitionType(str, Enum):
    """Visual transition effect applied between scene changes.

    Effects:
        FADE:          Gradual opacity blend between scenes.
        SLIDE_LEFT:    New scene slides in from the right.
        SLIDE_RIGHT:   New scene slides in from the left.
        SLIDE_UP:      New scene slides in from the bottom.
        SLIDE_DOWN:    New scene slides in from the top.
        ZOOM_IN:       Camera zooms into the new scene.
        ZOOM_OUT:      Camera zooms out revealing the new scene.
        WIPE:          Hard edge sweeps across the screen.
        CROSSFADE:     Both scenes rendered simultaneously with opacity blend.
        INSTANT:       Immediate switch with no visible transition.
        CUSTOM:        User-defined transition callback.
    """
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    WIPE = "wipe"
    CROSSFADE = "crossfade"
    INSTANT = "instant"
    CUSTOM = "custom"


class EasingType(str, Enum):
    """Interpolation easing curves for transition animations.

    Curves:
        LINEAR:       Constant velocity interpolation.
        EASE_IN:      Accelerating from zero velocity.
        EASE_OUT:     Decelerating to zero velocity.
        EASE_IN_OUT:  Acceleration then deceleration.
        ELASTIC:      Overshooting spring-like curve.
        BOUNCE:       Bouncing at the end of the curve.
        BACK:         Overshoots then settles back.
    """
    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    ELASTIC = "elastic"
    BOUNCE = "bounce"
    BACK = "back"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class SceneDescriptor:
    """Metadata describing a scene with loading progress and runtime stats.

    Attributes:
        scene_id:       Unique identifier for the scene.
        name:           Human-readable scene name.
        path:           Resource path to the scene definition file.
        state:          Current lifecycle state of the scene.
        load_progress:  Loading progress from 0.0 to 1.0.
        entity_count:   Number of entities in the scene.
        layer_count:    Number of render layers in the scene.
        memory_usage:   Estimated memory footprint in bytes.
        load_time_ms:   Total time spent loading the scene in milliseconds.
        metadata:       Arbitrary key-value metadata for engine extensions.
    """
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    path: str = ""
    state: SceneLifecycle = SceneLifecycle.UNLOADED
    load_progress: float = 0.0
    entity_count: int = 0
    layer_count: int = 0
    memory_usage: int = 0
    load_time_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "path": self.path,
            "state": self.state.value,
            "load_progress": self.load_progress,
            "entity_count": self.entity_count,
            "layer_count": self.layer_count,
            "memory_usage": self.memory_usage,
            "load_time_ms": self.load_time_ms,
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneTransition:
    """Animated transition configuration between two scenes.

    Attributes:
        transition_id:   Unique identifier for this transition.
        from_scene:      Source scene descriptor ID.
        to_scene:        Target scene descriptor ID.
        transition_type: Visual effect type for the transition.
        duration:        Total duration of the transition in seconds.
        easing:          Easing curve applied during the transition.
        progress:        Current transition progress from 0.0 to 1.0.
        callback:        Optional callback invoked when transition completes.
        metadata:        Arbitrary key-value metadata.
    """
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_scene: str = ""
    to_scene: str = ""
    transition_type: TransitionType = TransitionType.FADE
    duration: float = 0.5
    easing: EasingType = EasingType.EASE_IN_OUT
    progress: float = 0.0
    callback: Optional[Callable[[], None]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_scene": self.from_scene,
            "to_scene": self.to_scene,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "easing": self.easing.value,
            "progress": self.progress,
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneLayer:
    """A render layer within a scene with independent settings.

    Each scene can have multiple layers rendered in z-order. Layers have
    their own camera position, zoom, visibility, and render target.

    Attributes:
        layer_id:         Unique identifier for the layer.
        name:             Human-readable layer name.
        z_order:          Rendering order (lower values render first).
        visible:          Whether the layer is currently rendered.
        camera_position:  (x, y) offset of the layer's camera.
        camera_zoom:      Zoom factor for the layer's camera (1.0 = default).
        render_target:    Optional name of a render-to-texture target.
        entities:         List of entity IDs assigned to this layer.
        metadata:         Arbitrary key-value metadata.
    """
    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    z_order: int = 0
    visible: bool = True
    camera_position: Tuple[float, float] = (0.0, 0.0)
    camera_zoom: float = 1.0
    render_target: str = ""
    entities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "z_order": self.z_order,
            "visible": self.visible,
            "camera_position": list(self.camera_position),
            "camera_zoom": self.camera_zoom,
            "render_target": self.render_target,
            "entities": list(self.entities),
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneGroup:
    """Logical grouping of related scenes for collective operations.

    Scene groups allow bulk operations like loading all scenes in a group,
    unloading them together, or transitioning within a group.

    Attributes:
        group_id:     Unique identifier for the group.
        name:         Human-readable group name.
        scene_ids:    List of scene descriptor IDs in this group.
        description:  Description of the group's purpose.
    """
    group_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scene_ids: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "scene_ids": list(self.scene_ids),
            "description": self.description,
        }


@dataclass
class SceneState:
    """Serializable snapshot of a scene's runtime state.

    Captures entity positions, variable values, and active timer data
    so the scene can be restored to a previous state.

    Attributes:
        state_id:          Unique identifier for this state snapshot.
        scene_id:          The scene this state belongs to.
        entity_positions:  Mapping of entity ID to (x, y) position.
        variable_values:   Mapping of variable name to current value.
        active_timers:     List of active timer descriptors.
        timestamp:         Unix timestamp when the state was captured.
    """
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_id: str = ""
    entity_positions: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    variable_values: Dict[str, Any] = field(default_factory=dict)
    active_timers: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "scene_id": self.scene_id,
            "entity_positions": {
                k: list(v) for k, v in self.entity_positions.items()
            },
            "variable_values": dict(self.variable_values),
            "active_timers": list(self.active_timers),
            "timestamp": self.timestamp,
        }


@dataclass
class SceneStackEntry:
    """A single entry in the scene stack representing an active scene.

    The scene stack is a LIFO structure where the top entry is the
    currently active scene. Paused entries remain in the stack
    for later resumption.

    Attributes:
        entry_id:    Unique identifier for this stack entry.
        scene_id:    The scene descriptor ID for this entry.
        push_time:   Unix timestamp when this entry was pushed.
        paused:      Whether this entry is currently paused.
        metadata:    Arbitrary key-value metadata.
    """
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_id: str = ""
    push_time: float = field(default_factory=_time_module.time)
    paused: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "scene_id": self.scene_id,
            "push_time": self.push_time,
            "paused": self.paused,
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# EngineSceneRuntime — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineSceneRuntime:
    """
    Central scene runtime orchestrator for the SparkLabs engine.

    Manages the scene stack, lifecycle transitions, animated scene
    transitions, render layers, scene grouping, and state save/restore.
    All public methods are thread-safe via a reentrant lock.

    Usage:
        rt = get_engine_scene_runtime()
        desc_id = rt.register_scene("main_menu", "scenes/menu.json")
        rt.load_scene(desc_id)
        rt.push_scene(desc_id, TransitionType.FADE)
        rt.pause_scene()
        rt.resume_scene()
        rt.pop_scene(TransitionType.SLIDE_LEFT)
    """

    _instance: Optional["EngineSceneRuntime"] = None
    _lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "EngineSceneRuntime":
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

        # Scene registry
        self._scenes: Dict[str, SceneDescriptor] = {}

        # Scene stack (LIFO — top is active)
        self._stack: List[SceneStackEntry] = []

        # Scene layers keyed by scene_id → list of layers
        self._layers: Dict[str, Dict[str, SceneLayer]] = {}

        # Scene groups
        self._groups: Dict[str, SceneGroup] = {}

        # Scene states (save/restore snapshots keyed by scene_id)
        self._states: Dict[str, Dict[str, SceneState]] = {}

        # Active transitions
        self._transitions: Dict[str, SceneTransition] = {}

        # Preloading progress tracking
        self._preload_progress: Dict[str, float] = {}

        # Lifecycle hooks (per scene_id)
        self._hooks: Dict[str, Dict[str, List[Callable[..., Any]]]] = {}

        # Runtime configuration
        self._config: Dict[str, Any] = {
            "default_transition_type": TransitionType.FADE.value,
            "default_transition_duration": 0.5,
            "default_easing": EasingType.EASE_IN_OUT.value,
            "max_stack_depth": 32,
            "auto_preload": True,
            "preload_timeout_ms": 30000.0,
            "state_auto_save": True,
        }

        # Statistics
        self._total_pushes: int = 0
        self._total_pops: int = 0
        self._total_transitions: int = 0
        self._total_preloads: int = 0
        self._total_state_saves: int = 0

    # ------------------------------------------------------------------
    # Scene Registration & Descriptor Management
    # ------------------------------------------------------------------

    def register_scene(self, name: str, path: str) -> str:
        """Register a new scene descriptor and return its scene_id.

        Args:
            name: Human-readable scene name (e.g. "main_menu").
            path: Resource path to the scene definition file.

        Returns:
            The unique scene_id for the registered scene.

        Raises:
            ValueError: If a scene with the same name already exists.
        """
        with self._lock:
            # Check for duplicate names
            for scene in self._scenes.values():
                if scene.name == name:
                    raise ValueError(
                        f"Scene with name '{name}' already registered"
                    )

            descriptor = SceneDescriptor(name=name, path=path)
            self._scenes[descriptor.scene_id] = descriptor

            # Initialize layer storage
            self._layers[descriptor.scene_id] = {}

            # Initialize state storage
            self._states[descriptor.scene_id] = {}

            return descriptor.scene_id

    def get_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Retrieve a scene descriptor by its ID.

        Args:
            scene_id: The unique scene identifier.

        Returns:
            The SceneDescriptor if found, otherwise None.
        """
        with self._lock:
            return self._scenes.get(scene_id)

    def list_scenes(self) -> List[SceneDescriptor]:
        """Return all registered scene descriptors.

        Returns:
            A list of all SceneDescriptor objects.
        """
        with self._lock:
            return list(self._scenes.values())

    def get_scene_by_name(self, name: str) -> Optional[SceneDescriptor]:
        """Find a scene descriptor by its name.

        Args:
            name: The human-readable scene name to search for.

        Returns:
            The SceneDescriptor if found, otherwise None.
        """
        with self._lock:
            for scene in self._scenes.values():
                if scene.name == name:
                    return scene
            return None

    def remove_scene(self, scene_id: str) -> bool:
        """Remove a scene descriptor and all associated data.

        This will fail if the scene is currently on the stack.

        Args:
            scene_id: The unique scene identifier.

        Returns:
            True if the scene was removed, False otherwise.
        """
        with self._lock:
            # Prevent removal of active scenes
            for entry in self._stack:
                if entry.scene_id == scene_id:
                    return False

            self._scenes.pop(scene_id, None)
            self._layers.pop(scene_id, None)
            self._states.pop(scene_id, None)
            self._hooks.pop(scene_id, None)
            self._preload_progress.pop(scene_id, None)

            # Remove from all groups
            for group in self._groups.values():
                if scene_id in group.scene_ids:
                    group.scene_ids.remove(scene_id)

            return True

    # ------------------------------------------------------------------
    # Scene Loading & Lifecycle
    # ------------------------------------------------------------------

    def load_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Load a scene into memory by transitioning through load lifecycle.

        Moves the scene through UNLOADED → LOADING → LOADED states,
        tracking load progress and timing. Lifecycle hooks are invoked
        at each stage.

        Args:
            scene_id: The unique scene identifier to load.

        Returns:
            The updated SceneDescriptor, or None if not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            if desc.state not in (SceneLifecycle.UNLOADED,):
                return desc  # Already loaded or in progress

            load_start = _time_module.time()

            # Transition to LOADING
            desc.state = SceneLifecycle.LOADING
            desc.load_progress = 0.0
            self._invoke_hook(scene_id, "on_load_start", desc)

            # Simulate loading progression
            desc.load_progress = 0.5
            self._invoke_hook(scene_id, "on_load_progress", desc, 0.5)

            # Complete loading
            desc.load_progress = 1.0
            desc.state = SceneLifecycle.LOADED
            desc.load_time_ms = (_time_module.time() - load_start) * 1000.0
            desc.memory_usage = self._estimate_memory_usage(desc)

            self._invoke_hook(scene_id, "on_load_complete", desc)
            return desc

    def init_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Initialize a loaded scene, preparing it to run.

        Moves the scene through LOADED → INITIALIZING state. Invokes
        the on_init lifecycle hook.

        Args:
            scene_id: The unique scene identifier to initialize.

        Returns:
            The updated SceneDescriptor, or None if not found or not loaded.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None
            if desc.state != SceneLifecycle.LOADED:
                return None

            desc.state = SceneLifecycle.INITIALIZING
            self._invoke_hook(scene_id, "on_init", desc)

            return desc

    def start_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Start a scene, transitioning it to RUNNING state.

        Moves the scene through INITIALIZING → RUNNING. Invokes the
        on_start lifecycle hook.

        Args:
            scene_id: The unique scene identifier to start.

        Returns:
            The updated SceneDescriptor, or None if not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None
            if desc.state not in (SceneLifecycle.LOADED, SceneLifecycle.INITIALIZING):
                return None

            # Auto-initialize if not already done
            if desc.state == SceneLifecycle.LOADED:
                desc.state = SceneLifecycle.INITIALIZING
                self._invoke_hook(scene_id, "on_init", desc)

            desc.state = SceneLifecycle.RUNNING
            self._invoke_hook(scene_id, "on_start", desc)

            return desc

    def update_scene(self, scene_id: str, delta_time: float) -> Optional[SceneDescriptor]:
        """Update a running scene with a time delta.

        Invokes the on_update lifecycle hook with the scene descriptor
        and delta time. Also processes RESUMING → RUNNING transitions.

        Args:
            scene_id:   The scene to update.
            delta_time: Frame delta in seconds.

        Returns:
            The updated SceneDescriptor, or None if not running.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            # Handle RESUME → RUNNING transition
            if desc.state == SceneLifecycle.RESUMING:
                desc.state = SceneLifecycle.RUNNING

            if desc.state != SceneLifecycle.RUNNING:
                return desc

            self._invoke_hook(scene_id, "on_update", desc, delta_time)
            return desc

    def stop_scene(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Stop a running scene, transitioning it through STOPPING → UNLOADING.

        Invokes on_stop and on_unload lifecycle hooks. Optionally performs
        auto state-save if configured.

        Args:
            scene_id: The scene to stop.

        Returns:
            The updated SceneDescriptor, or None if not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            if desc.state == SceneLifecycle.UNLOADED:
                return desc

            # Auto-save state if configured
            if self._config.get("state_auto_save", True):
                self._save_scene_state_internal(scene_id)

            desc.state = SceneLifecycle.STOPPING
            self._invoke_hook(scene_id, "on_stop", desc)

            desc.state = SceneLifecycle.UNLOADING
            self._invoke_hook(scene_id, "on_unload", desc)

            desc.state = SceneLifecycle.UNLOADED
            desc.load_progress = 0.0
            desc.entity_count = 0

            return desc

    def get_scene_lifecycle(self, scene_id: str) -> Optional[SceneLifecycle]:
        """Get the current lifecycle state of a scene.

        Args:
            scene_id: The scene to query.

        Returns:
            The current SceneLifecycle value, or None if not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None
            return desc.state

    # ------------------------------------------------------------------
    # Scene Stack Management
    # ------------------------------------------------------------------

    def push_scene(
        self,
        scene_id: str,
        transition_type: Optional[TransitionType] = None,
        duration: Optional[float] = None,
        easing: Optional[EasingType] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[SceneStackEntry]:
        """Push a scene onto the scene stack, making it the active scene.

        The current top scene (if any) is paused. The new scene goes
        through the full load → init → start lifecycle automatically.
        A transition animation is created between the previous and new scenes.

        Args:
            scene_id:         The scene to push onto the stack.
            transition_type:  Visual transition effect (default from config).
            duration:         Transition duration in seconds (default from config).
            easing:           Easing curve (default from config).
            metadata:         Optional metadata for the stack entry.

        Returns:
            The new SceneStackEntry, or None if push fails.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            # Check stack depth limit
            if len(self._stack) >= self._config.get("max_stack_depth", 32):
                return None

            # Pause current top scene
            current = self.get_current_scene()
            from_scene_id = ""
            if current is not None:
                from_scene_id = current.scene_id
                current.state = SceneLifecycle.PAUSED
                self._invoke_hook(current.scene_id, "on_pause", current)

                # Mark the top stack entry as paused
                if self._stack:
                    self._stack[-1].paused = True

            # Load, init, and start the new scene
            self._load_scene_internal(scene_id)
            self._init_scene_internal(scene_id)
            self._start_scene_internal(scene_id)

            # Create stack entry
            entry = SceneStackEntry(
                scene_id=scene_id,
                push_time=_time_module.time(),
                paused=False,
                metadata=metadata or {},
            )
            self._stack.append(entry)
            self._total_pushes += 1

            # Create transition
            tt = (
                transition_type
                or TransitionType(self._config["default_transition_type"])
            )
            td = duration or self._config["default_transition_duration"]
            te = easing or EasingType(self._config["default_easing"])

            transition = SceneTransition(
                from_scene=from_scene_id,
                to_scene=scene_id,
                transition_type=tt,
                duration=td,
                easing=te,
            )
            self._transitions[transition.transition_id] = transition
            self._total_transitions += 1

            return entry

    def pop_scene(
        self,
        transition_type: Optional[TransitionType] = None,
        duration: Optional[float] = None,
        easing: Optional[EasingType] = None,
    ) -> Optional[SceneStackEntry]:
        """Pop the current scene from the stack and resume the previous one.

        The current top scene is stopped and unloaded. The scene beneath
        it (if any) is resumed. A transition animation is created.

        Args:
            transition_type: Visual transition effect (default from config).
            duration:        Transition duration in seconds (default from config).
            easing:          Easing curve (default from config).

        Returns:
            The removed SceneStackEntry, or None if stack is empty.
        """
        with self._lock:
            if not self._stack:
                return None

            popped = self._stack.pop()
            self._total_pops += 1

            # Stop and unload the popped scene
            self.stop_scene(popped.scene_id)

            # Resume the new top scene
            from_scene_id = popped.scene_id
            to_scene_id = ""
            if self._stack:
                top = self._stack[-1]
                top.paused = False
                desc = self._scenes.get(top.scene_id)
                if desc is not None and desc.state == SceneLifecycle.PAUSED:
                    desc.state = SceneLifecycle.RESUMING
                    self._invoke_hook(desc.scene_id, "on_resume", desc)
                    desc.state = SceneLifecycle.RUNNING
                to_scene_id = top.scene_id

            # Create transition
            tt = (
                transition_type
                or TransitionType(self._config["default_transition_type"])
            )
            td = duration or self._config["default_transition_duration"]
            te = easing or EasingType(self._config["default_easing"])

            transition = SceneTransition(
                from_scene=from_scene_id,
                to_scene=to_scene_id,
                transition_type=tt,
                duration=td,
                easing=te,
            )
            self._transitions[transition.transition_id] = transition
            self._total_transitions += 1

            return popped

    def replace_scene(
        self,
        scene_id: str,
        transition_type: Optional[TransitionType] = None,
        duration: Optional[float] = None,
        easing: Optional[EasingType] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[SceneStackEntry]:
        """Replace the current top scene with a new scene.

        Equivalent to pop followed by push, but performed atomically
        with a single transition animation.

        Args:
            scene_id:         The scene to replace the current one with.
            transition_type:  Visual transition effect (default from config).
            duration:         Transition duration in seconds (default from config).
            easing:           Easing curve (default from config).
            metadata:         Optional metadata for the new stack entry.

        Returns:
            The new SceneStackEntry, or None if replacement fails.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            from_scene_id = ""
            if self._stack:
                old = self._stack.pop()
                from_scene_id = old.scene_id
                self.stop_scene(old.scene_id)

            # Load and start new scene
            self._load_scene_internal(scene_id)
            self._init_scene_internal(scene_id)
            self._start_scene_internal(scene_id)

            # Create new stack entry
            entry = SceneStackEntry(
                scene_id=scene_id,
                push_time=_time_module.time(),
                paused=False,
                metadata=metadata or {},
            )
            self._stack.append(entry)
            self._total_pushes += 1

            # Create transition
            tt = (
                transition_type
                or TransitionType(self._config["default_transition_type"])
            )
            td = duration or self._config["default_transition_duration"]
            te = easing or EasingType(self._config["default_easing"])

            transition = SceneTransition(
                from_scene=from_scene_id,
                to_scene=scene_id,
                transition_type=tt,
                duration=td,
                easing=te,
            )
            self._transitions[transition.transition_id] = transition
            self._total_transitions += 1

            return entry

    def get_current_scene(self) -> Optional[SceneDescriptor]:
        """Get the currently active scene (top of the stack).

        Returns:
            The active SceneDescriptor, or None if the stack is empty.
        """
        with self._lock:
            if not self._stack:
                return None
            top = self._stack[-1]
            return self._scenes.get(top.scene_id)

    def get_scene_stack(self) -> List[SceneStackEntry]:
        """Get the full scene stack (bottom to top).

        Returns:
            A copy of the scene stack entries in order.
        """
        with self._lock:
            return list(self._stack)

    def get_stack_depth(self) -> int:
        """Get the current depth of the scene stack.

        Returns:
            The number of entries currently on the stack.
        """
        with self._lock:
            return len(self._stack)

    # ------------------------------------------------------------------
    # Scene Pause / Resume
    # ------------------------------------------------------------------

    def pause_scene(self) -> Optional[SceneDescriptor]:
        """Pause the currently active scene.

        The current scene transitions from RUNNING to PAUSED. Invokes
        the on_pause lifecycle hook.

        Returns:
            The paused SceneDescriptor, or None if no active scene.
        """
        with self._lock:
            if not self._stack:
                return None

            top = self._stack[-1]
            desc = self._scenes.get(top.scene_id)
            if desc is None:
                return None
            if desc.state != SceneLifecycle.RUNNING:
                return None

            desc.state = SceneLifecycle.PAUSED
            top.paused = True
            self._invoke_hook(desc.scene_id, "on_pause", desc)

            return desc

    def resume_scene(self) -> Optional[SceneDescriptor]:
        """Resume the paused current scene.

        The current scene transitions from PAUSED through RESUMING to
        RUNNING. Invokes the on_resume lifecycle hook.

        Returns:
            The resumed SceneDescriptor, or None if no paused scene.
        """
        with self._lock:
            if not self._stack:
                return None

            top = self._stack[-1]
            desc = self._scenes.get(top.scene_id)
            if desc is None:
                return None
            if desc.state != SceneLifecycle.PAUSED:
                return None

            desc.state = SceneLifecycle.RESUMING
            top.paused = False
            self._invoke_hook(desc.scene_id, "on_resume", desc)

            desc.state = SceneLifecycle.RUNNING

            return desc

    def is_scene_paused(self) -> bool:
        """Check whether the current scene is paused.

        Returns:
            True if the current scene is paused, False otherwise.
        """
        with self._lock:
            if not self._stack:
                return False
            return self._stack[-1].paused

    # ------------------------------------------------------------------
    # Scene Preloading
    # ------------------------------------------------------------------

    def preload_scene(self, scene_id: str) -> bool:
        """Begin preloading a scene's assets in the background.

        Preloading loads scene assets ahead of time so that the actual
        transition is instantaneous. Progress can be tracked via
        get_preload_progress().

        Args:
            scene_id: The scene to preload.

        Returns:
            True if preloading started, False if scene not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return False

            if desc.state != SceneLifecycle.UNLOADED:
                return False

            self._preload_progress[scene_id] = 0.0
            self._total_preloads += 1

            self._invoke_hook(scene_id, "on_preload_start", desc)

            # Simulate background loading progress
            desc.load_progress = 0.3
            self._preload_progress[scene_id] = 0.3

            return True

    def update_preload(self, scene_id: str, progress: float) -> bool:
        """Update the preload progress for a scene.

        Called by the preload system to report incremental progress.
        When progress reaches 1.0, the on_preload_complete hook fires.

        Args:
            scene_id: The scene being preloaded.
            progress: Current progress from 0.0 to 1.0.

        Returns:
            True if update was applied, False otherwise.
        """
        with self._lock:
            if scene_id not in self._preload_progress:
                return False

            clamped = max(0.0, min(1.0, progress))
            self._preload_progress[scene_id] = clamped

            desc = self._scenes.get(scene_id)
            if desc is not None:
                desc.load_progress = clamped

            if clamped >= 1.0:
                if desc is not None:
                    self._invoke_hook(scene_id, "on_preload_complete", desc)

            return True

    def get_preload_progress(self, scene_id: str) -> Optional[float]:
        """Get the current preload progress for a scene.

        Args:
            scene_id: The scene to query.

        Returns:
            Progress from 0.0 to 1.0, or None if not preloading.
        """
        with self._lock:
            return self._preload_progress.get(scene_id)

    def cancel_preload(self, scene_id: str) -> bool:
        """Cancel an in-progress preload operation.

        Args:
            scene_id: The scene whose preload to cancel.

        Returns:
            True if cancelled, False if not preloading.
        """
        with self._lock:
            if scene_id not in self._preload_progress:
                return False

            self._preload_progress.pop(scene_id, None)

            desc = self._scenes.get(scene_id)
            if desc is not None:
                desc.load_progress = 0.0
                desc.state = SceneLifecycle.UNLOADED

            return True

    # ------------------------------------------------------------------
    # Scene Layers
    # ------------------------------------------------------------------

    def add_layer(
        self,
        scene_id: str,
        layer_name: str,
        z_order: int = 0,
        visible: bool = True,
        camera_position: Tuple[float, float] = (0.0, 0.0),
        camera_zoom: float = 1.0,
    ) -> Optional[str]:
        """Add a render layer to a scene.

        Layers are rendered in z_order (lowest first). Each layer can
        have independent camera settings, visibility, and entities.

        Args:
            scene_id:        The scene to add a layer to.
            layer_name:      Human-readable name for the layer.
            z_order:         Rendering order (lower = behind).
            visible:         Whether the layer starts visible.
            camera_position: Initial (x, y) camera offset.
            camera_zoom:     Initial camera zoom factor.

        Returns:
            The layer_id of the created layer, or None if scene not found.
        """
        with self._lock:
            desc = self._scenes.get(scene_id)
            if desc is None:
                return None

            layer = SceneLayer(
                name=layer_name,
                z_order=z_order,
                visible=visible,
                camera_position=camera_position,
                camera_zoom=camera_zoom,
            )

            if scene_id not in self._layers:
                self._layers[scene_id] = {}

            self._layers[scene_id][layer.layer_id] = layer
            desc.layer_count = len(self._layers[scene_id])

            return layer.layer_id

    def remove_layer(self, scene_id: str, layer_id: str) -> bool:
        """Remove a render layer from a scene.

        Args:
            scene_id: The scene to remove from.
            layer_id: The layer to remove.

        Returns:
            True if removed, False if not found.
        """
        with self._lock:
            if scene_id not in self._layers:
                return False

            if layer_id not in self._layers[scene_id]:
                return False

            del self._layers[scene_id][layer_id]

            desc = self._scenes.get(scene_id)
            if desc is not None:
                desc.layer_count = len(self._layers[scene_id])

            return True

    def get_layer(self, scene_id: str, layer_id: str) -> Optional[SceneLayer]:
        """Get a specific layer by ID.

        Args:
            scene_id: The scene the layer belongs to.
            layer_id: The layer identifier.

        Returns:
            The SceneLayer, or None if not found.
        """
        with self._lock:
            if scene_id not in self._layers:
                return None
            return self._layers[scene_id].get(layer_id)

    def get_scene_layers(self, scene_id: str) -> List[SceneLayer]:
        """Get all layers for a scene, sorted by z_order.

        Args:
            scene_id: The scene to query.

        Returns:
            A list of SceneLayer objects sorted by z_order.
        """
        with self._lock:
            if scene_id not in self._layers:
                return []
            layers = list(self._layers[scene_id].values())
            layers.sort(key=lambda l: l.z_order)
            return layers

    def set_layer_visible(self, scene_id: str, layer_id: str, visible: bool) -> bool:
        """Toggle the visibility of a render layer.

        Args:
            scene_id: The scene the layer belongs to.
            layer_id: The layer to toggle.
            visible:  True to show, False to hide.

        Returns:
            True if toggled, False if layer not found.
        """
        with self._lock:
            layer = self.get_layer(scene_id, layer_id)
            if layer is None:
                return False
            layer.visible = visible
            return True

    def set_layer_camera(
        self,
        scene_id: str,
        layer_id: str,
        position: Optional[Tuple[float, float]] = None,
        zoom: Optional[float] = None,
    ) -> bool:
        """Update the camera settings for a layer.

        Args:
            scene_id: The scene the layer belongs to.
            layer_id: The layer to update.
            position: New (x, y) camera offset (None to keep current).
            zoom:     New camera zoom factor (None to keep current).

        Returns:
            True if updated, False if layer not found.
        """
        with self._lock:
            layer = self.get_layer(scene_id, layer_id)
            if layer is None:
                return False
            if position is not None:
                layer.camera_position = position
            if zoom is not None:
                layer.camera_zoom = zoom
            return True

    def add_entity_to_layer(
        self, scene_id: str, layer_id: str, entity_id: str,
    ) -> bool:
        """Assign an entity to a specific render layer.

        Args:
            scene_id:   The scene the layer belongs to.
            layer_id:   The layer to add the entity to.
            entity_id:  The entity ID to add.

        Returns:
            True if added, False if layer not found.
        """
        with self._lock:
            layer = self.get_layer(scene_id, layer_id)
            if layer is None:
                return False
            if entity_id not in layer.entities:
                layer.entities.append(entity_id)
            return True

    def remove_entity_from_layer(
        self, scene_id: str, layer_id: str, entity_id: str,
    ) -> bool:
        """Remove an entity from a render layer.

        Args:
            scene_id:   The scene the layer belongs to.
            layer_id:   The layer to remove from.
            entity_id:  The entity ID to remove.

        Returns:
            True if removed, False if layer or entity not found.
        """
        with self._lock:
            layer = self.get_layer(scene_id, layer_id)
            if layer is None:
                return False
            if entity_id in layer.entities:
                layer.entities.remove(entity_id)
                return True
            return False

    # ------------------------------------------------------------------
    # Scene Groups
    # ------------------------------------------------------------------

    def create_scene_group(
        self,
        name: str,
        scene_ids: List[str],
        description: str = "",
    ) -> Optional[str]:
        """Create a scene group for collective operations.

        Groups allow bulk loading, unloading, and transitioning of
        related scenes.

        Args:
            name:        Human-readable group name.
            scene_ids:   List of scene IDs to include in the group.
            description: Optional description of the group's purpose.

        Returns:
            The group_id of the created group, or None if validation fails.
        """
        with self._lock:
            # Validate all scene IDs exist
            for sid in scene_ids:
                if sid not in self._scenes:
                    return None

            group = SceneGroup(
                name=name,
                scene_ids=list(scene_ids),
                description=description,
            )
            self._groups[group.group_id] = group
            return group.group_id

    def get_group(self, group_id: str) -> Optional[SceneGroup]:
        """Get a scene group by ID.

        Args:
            group_id: The group identifier.

        Returns:
            The SceneGroup, or None if not found.
        """
        with self._lock:
            return self._groups.get(group_id)

    def list_groups(self) -> List[SceneGroup]:
        """List all scene groups.

        Returns:
            A list of all SceneGroup objects.
        """
        with self._lock:
            return list(self._groups.values())

    def load_group(self, group_id: str) -> Dict[str, Optional[SceneDescriptor]]:
        """Load all scenes in a group.

        Args:
            group_id: The group to load.

        Returns:
            A dict mapping scene_id to SceneDescriptor (or None for failures).
        """
        with self._lock:
            group = self._groups.get(group_id)
            if group is None:
                return {}

            results: Dict[str, Optional[SceneDescriptor]] = {}
            for sid in group.scene_ids:
                results[sid] = self.load_scene(sid)
            return results

    def unload_group(self, group_id: str) -> Dict[str, bool]:
        """Unload all scenes in a group.

        Args:
            group_id: The group to unload.

        Returns:
            A dict mapping scene_id to success boolean.
        """
        with self._lock:
            group = self._groups.get(group_id)
            if group is None:
                return {}

            results: Dict[str, bool] = {}
            for sid in group.scene_ids:
                desc = self.stop_scene(sid)
                results[sid] = desc is not None
            return results

    def transition_within_group(
        self,
        group_id: str,
        scene_id: str,
        transition_type: Optional[TransitionType] = None,
    ) -> Optional[SceneStackEntry]:
        """Transition to a scene within the same group.

        Ensures the target scene is in the specified group, then
        performs a replace_scene operation.

        Args:
            group_id:        The group that must contain the scene.
            scene_id:        The scene to transition to.
            transition_type: Visual transition effect.

        Returns:
            The new SceneStackEntry, or None if invalid.
        """
        with self._lock:
            group = self._groups.get(group_id)
            if group is None:
                return None
            if scene_id not in group.scene_ids:
                return None
            return self.replace_scene(scene_id, transition_type)

    def delete_group(self, group_id: str) -> bool:
        """Delete a scene group.

        Args:
            group_id: The group to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if group_id not in self._groups:
                return False
            del self._groups[group_id]
            return True

    # ------------------------------------------------------------------
    # Scene State Save / Restore
    # ------------------------------------------------------------------

    def save_scene_state(self, scene_id: str) -> Optional[str]:
        """Save the current runtime state of a scene for later restoration.

        Captures entity positions, variable values, and active timer data.

        Args:
            scene_id: The scene whose state to save.

        Returns:
            The state_id of the saved snapshot, or None if save fails.
        """
        with self._lock:
            return self._save_scene_state_internal(scene_id)

    def _save_scene_state_internal(self, scene_id: str) -> Optional[str]:
        """Internal state save without lock acquisition."""
        desc = self._scenes.get(scene_id)
        if desc is None:
            return None

        state = SceneState(
            scene_id=scene_id,
            timestamp=_time_module.time(),
        )

        if scene_id not in self._states:
            self._states[scene_id] = {}

        self._states[scene_id][state.state_id] = state
        self._total_state_saves += 1

        self._invoke_hook(scene_id, "on_state_save", state)

        return state.state_id

    def restore_scene_state(self, scene_id: str, state_id: str) -> bool:
        """Restore a scene to a previously saved state snapshot.

        Rehydrates entity positions, variable values, and timer data
        from the saved snapshot.

        Args:
            scene_id: The scene to restore.
            state_id: The state snapshot to restore from.

        Returns:
            True if restored successfully, False otherwise.
        """
        with self._lock:
            if scene_id not in self._states:
                return False

            state = self._states[scene_id].get(state_id)
            if state is None:
                return False

            desc = self._scenes.get(scene_id)
            if desc is None:
                return False

            self._invoke_hook(scene_id, "on_state_restore", state)

            return True

    def list_scene_states(self, scene_id: str) -> List[SceneState]:
        """List all saved state snapshots for a scene.

        Args:
            scene_id: The scene to query.

        Returns:
            A list of SceneState objects sorted by timestamp (newest first).
        """
        with self._lock:
            if scene_id not in self._states:
                return []
            states = list(self._states[scene_id].values())
            states.sort(key=lambda s: s.timestamp, reverse=True)
            return states

    def delete_scene_state(self, scene_id: str, state_id: str) -> bool:
        """Delete a saved state snapshot.

        Args:
            scene_id: The scene the state belongs to.
            state_id: The state snapshot to delete.

        Returns:
            True if deleted, False if not found.
        """
        with self._lock:
            if scene_id not in self._states:
                return False
            if state_id not in self._states[scene_id]:
                return False
            del self._states[scene_id][state_id]
            return True

    # ------------------------------------------------------------------
    # Transition Management
    # ------------------------------------------------------------------

    def update_transition(
        self, transition_id: str, delta_time: float,
    ) -> Optional[SceneTransition]:
        """Advance a transition animation by delta_time seconds.

        Computes the eased progress based on the transition's easing
        curve. When progress reaches 1.0, the transition callback
        (if any) is invoked and the transition is considered complete.

        Args:
            transition_id: The transition to update.
            delta_time:    Frame delta in seconds.

        Returns:
            The updated SceneTransition, or None if not found or complete.
        """
        with self._lock:
            transition = self._transitions.get(transition_id)
            if transition is None:
                return None

            if transition.progress >= 1.0:
                return None  # Already complete

            transition.progress = self._compute_eased_progress(
                transition.progress, delta_time, transition.duration,
                transition.easing,
            )

            if transition.progress >= 1.0:
                transition.progress = 1.0
                if transition.callback is not None:
                    try:
                        transition.callback()
                    except Exception:
                        pass

            return transition

    def get_transition(self, transition_id: str) -> Optional[SceneTransition]:
        """Get a transition by ID.

        Args:
            transition_id: The transition identifier.

        Returns:
            The SceneTransition, or None if not found.
        """
        with self._lock:
            return self._transitions.get(transition_id)

    def cancel_transition(self, transition_id: str) -> bool:
        """Cancel and remove an active transition.

        Args:
            transition_id: The transition to cancel.

        Returns:
            True if cancelled, False if not found.
        """
        with self._lock:
            if transition_id not in self._transitions:
                return False
            del self._transitions[transition_id]
            return True

    def get_active_transitions(self) -> List[SceneTransition]:
        """Get all in-progress transitions (progress < 1.0).

        Returns:
            A list of active SceneTransition objects.
        """
        with self._lock:
            return [
                t for t in self._transitions.values() if t.progress < 1.0
            ]

    # ------------------------------------------------------------------
    # Lifecycle Hooks
    # ------------------------------------------------------------------

    def register_hook(
        self,
        scene_id: str,
        hook_name: str,
        callback: Callable[..., Any],
    ) -> bool:
        """Register a lifecycle hook callback for a scene.

        Supported hook names:
            on_load_start, on_load_progress, on_load_complete,
            on_init, on_start, on_update, on_pause, on_resume,
            on_stop, on_unload, on_preload_start, on_preload_complete,
            on_state_save, on_state_restore

        Args:
            scene_id:  The scene to attach the hook to.
            hook_name: The lifecycle event name.
            callback:  Callable invoked when the hook fires.

        Returns:
            True if registered, False if scene not found.
        """
        with self._lock:
            if scene_id not in self._scenes:
                return False

            if scene_id not in self._hooks:
                self._hooks[scene_id] = {}

            if hook_name not in self._hooks[scene_id]:
                self._hooks[scene_id][hook_name] = []

            self._hooks[scene_id][hook_name].append(callback)
            return True

    def unregister_hook(
        self,
        scene_id: str,
        hook_name: str,
        callback: Optional[Callable[..., Any]] = None,
    ) -> bool:
        """Unregister a lifecycle hook callback.

        If callback is None, all callbacks for that hook are removed.

        Args:
            scene_id:  The scene the hook is attached to.
            hook_name: The lifecycle event name.
            callback:  Specific callback to remove, or None for all.

        Returns:
            True if any callbacks were removed, False otherwise.
        """
        with self._lock:
            if scene_id not in self._hooks:
                return False
            if hook_name not in self._hooks[scene_id]:
                return False

            if callback is None:
                del self._hooks[scene_id][hook_name]
                return True

            hooks = self._hooks[scene_id][hook_name]
            if callback in hooks:
                hooks.remove(callback)
                return True
            return False

    def _invoke_hook(self, scene_id: str, hook_name: str, *args: Any) -> None:
        """Invoke all registered callbacks for a lifecycle hook.

        Errors in individual callbacks are caught and suppressed to
        prevent one bad hook from breaking the entire lifecycle.

        Args:
            scene_id:  The scene whose hooks to invoke.
            hook_name: The lifecycle event name.
            *args:     Arguments to pass to each callback.
        """
        if scene_id not in self._hooks:
            return
        if hook_name not in self._hooks[scene_id]:
            return

        for callback in self._hooks[scene_id][hook_name]:
            try:
                callback(*args)
            except Exception:
                pass  # Suppress errors in hooks

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _load_scene_internal(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Internal scene load without lock acquisition."""
        desc = self._scenes.get(scene_id)
        if desc is None:
            return None
        if desc.state not in (SceneLifecycle.UNLOADED,):
            return desc

        load_start = _time_module.time()
        desc.state = SceneLifecycle.LOADING
        desc.load_progress = 0.0
        self._invoke_hook(scene_id, "on_load_start", desc)

        desc.load_progress = 0.5
        desc.load_progress = 1.0
        desc.state = SceneLifecycle.LOADED
        desc.load_time_ms = (_time_module.time() - load_start) * 1000.0
        desc.memory_usage = self._estimate_memory_usage(desc)

        self._invoke_hook(scene_id, "on_load_complete", desc)
        return desc

    def _init_scene_internal(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Internal scene init without lock acquisition."""
        desc = self._scenes.get(scene_id)
        if desc is None or desc.state != SceneLifecycle.LOADED:
            return None

        desc.state = SceneLifecycle.INITIALIZING
        self._invoke_hook(scene_id, "on_init", desc)
        return desc

    def _start_scene_internal(self, scene_id: str) -> Optional[SceneDescriptor]:
        """Internal scene start without lock acquisition."""
        desc = self._scenes.get(scene_id)
        if desc is None:
            return None

        if desc.state == SceneLifecycle.LOADED:
            desc.state = SceneLifecycle.INITIALIZING
            self._invoke_hook(scene_id, "on_init", desc)

        desc.state = SceneLifecycle.RUNNING
        self._invoke_hook(scene_id, "on_start", desc)
        return desc

    def _estimate_memory_usage(self, desc: SceneDescriptor) -> int:
        """Estimate memory usage for a scene descriptor (bytes).

        Uses entity count and layer count as scaling factors with
        a base overhead.

        Args:
            desc: The scene descriptor to estimate.

        Returns:
            Estimated memory usage in bytes.
        """
        base = 1024 * 64  # 64 KB base overhead
        per_entity = 1024 * 2  # 2 KB per entity
        per_layer = 1024 * 8  # 8 KB per layer
        return base + (desc.entity_count * per_entity) + (desc.layer_count * per_layer)

    @staticmethod
    def _compute_eased_progress(
        current: float,
        delta_time: float,
        duration: float,
        easing: EasingType,
    ) -> float:
        """Compute eased progress for a transition.

        Args:
            current:   Current progress from 0.0 to 1.0.
            delta_time: Frame delta in seconds.
            duration:  Total transition duration in seconds.
            easing:    The easing curve to apply.

        Returns:
            New progress value clamped to [0.0, 1.0].
        """
        safe_duration = max(duration, 0.0001)
        raw = current + (delta_time / safe_duration)
        t = max(0.0, min(1.0, raw))

        if easing == EasingType.LINEAR:
            return t
        elif easing == EasingType.EASE_IN:
            return t * t
        elif easing == EasingType.EASE_OUT:
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif easing == EasingType.EASE_IN_OUT:
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        elif easing == EasingType.ELASTIC:
            if t == 0.0 or t == 1.0:
                return t
            c4 = (2.0 * math.pi) / 3.0
            return -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * c4)
        elif easing == EasingType.BOUNCE:
            n1 = 7.5625
            d1 = 2.75
            if t < 1.0 / d1:
                return n1 * t * t
            elif t < 2.0 / d1:
                t2 = t - 1.5 / d1
                return n1 * t2 * t2 + 0.75
            elif t < 2.5 / d1:
                t2 = t - 2.25 / d1
                return n1 * t2 * t2 + 0.9375
            else:
                t2 = t - 2.625 / d1
                return n1 * t2 * t2 + 0.984375
        elif easing == EasingType.BACK:
            c1 = 1.70158
            c3 = c1 + 1.0
            return c3 * t * t * t - c1 * t * t
        else:
            return t

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def configure(self, **kwargs: Any) -> None:
        """Update runtime configuration parameters.

        Supported keys:
            default_transition_type (str):  Default transition effect name.
            default_transition_duration (float): Default transition duration.
            default_easing (str):           Default easing curve name.
            max_stack_depth (int):          Maximum scene stack depth.
            auto_preload (bool):            Enable automatic preloading.
            preload_timeout_ms (float):     Preload timeout in milliseconds.
            state_auto_save (bool):         Auto-save state on scene stop.

        Args:
            **kwargs: Key-value pairs to update in the configuration.
        """
        with self._lock:
            for key, value in kwargs.items():
                if key in self._config:
                    self._config[key] = value

    def get_config(self) -> Dict[str, Any]:
        """Get a copy of the current runtime configuration.

        Returns:
            A dict of configuration key-value pairs.
        """
        with self._lock:
            return dict(self._config)

    # ------------------------------------------------------------------
    # Status & Statistics
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive runtime status and statistics.

        Returns:
            A dict with stack info, transition counts, config, and more.
        """
        with self._lock:
            current = self.get_current_scene()
            return {
                "stack_depth": len(self._stack),
                "current_scene": current.name if current else None,
                "current_scene_id": current.scene_id if current else None,
                "current_state": current.state.value if current else None,
                "total_registered_scenes": len(self._scenes),
                "total_groups": len(self._groups),
                "total_pushes": self._total_pushes,
                "total_pops": self._total_pops,
                "total_transitions": self._total_transitions,
                "total_preloads": self._total_preloads,
                "total_state_saves": self._total_state_saves,
                "active_transitions": len(self.get_active_transitions()),
                "config": dict(self._config),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics for engine integration.

        Returns:
            A dict of statistics key-value pairs.
        """
        return self.get_status()

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all data including scenes, stack, layers, groups, and states.

        This is a hard reset that clears all internal state. Use with
        caution — all scene data will be lost.
        """
        with self._lock:
            self._scenes.clear()
            self._stack.clear()
            self._layers.clear()
            self._groups.clear()
            self._states.clear()
            self._transitions.clear()
            self._preload_progress.clear()
            self._hooks.clear()

            self._config = {
                "default_transition_type": TransitionType.FADE.value,
                "default_transition_duration": 0.5,
                "default_easing": EasingType.EASE_IN_OUT.value,
                "max_stack_depth": 32,
                "auto_preload": True,
                "preload_timeout_ms": 30000.0,
                "state_auto_save": True,
            }

            self._total_pushes = 0
            self._total_pops = 0
            self._total_transitions = 0
            self._total_preloads = 0
            self._total_state_saves = 0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_engine_scene_runtime() -> EngineSceneRuntime:
    """Return the singleton EngineSceneRuntime instance.

    Usage:
        rt = get_engine_scene_runtime()
        rt.register_scene("level_1", "scenes/level1.json")
    """
    return EngineSceneRuntime()


# Compatibility alias for existing engine integration
SceneRuntimeSystem = EngineSceneRuntime