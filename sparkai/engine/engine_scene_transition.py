"""
SparkLabs Engine - Scene Transition System

A scene loading and unloading system providing transition effects,
easing curves, resource lifecycle management, and additive scene
compositing for seamless gameplay flow.

Architecture:
  EngineSceneTransition (Singleton)
    |-- TransitionConfig  — effect, duration, easing, and direction
    |-- SceneDescriptor   — scene metadata with dependencies and load mode
    |-- SceneInstance     — runtime scene state with loading progress
    |-- TransitionState   — active transition tracking elapsed and progress
    |-- TransitionResult  — outcome of a completed transition
    |-- SceneStats        — aggregate telemetry across all scenes
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TransitionEffect(str, Enum):
    """Visual effect applied during a scene transition."""
    FADE = "fade"
    SLIDE_LEFT = "slide-left"
    SLIDE_RIGHT = "slide-right"
    SLIDE_UP = "slide-up"
    SLIDE_DOWN = "slide-down"
    ZOOM_IN = "zoom-in"
    ZOOM_OUT = "zoom-out"
    WIPE = "wipe"
    CROSSFADE = "crossfade"
    DISSOLVE = "dissolve"
    NONE = "none"


class SceneState(str, Enum):
    """Lifecycle state of a scene instance."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSING = "pausing"
    PAUSED = "paused"
    RESUMING = "resuming"
    UNLOADING = "unloading"


class SceneLoadMode(str, Enum):
    """How a scene is loaded relative to other active scenes."""
    SINGLE = "single"
    ADDITIVE = "additive"


class TransitionDirection(str, Enum):
    """Direction of the transition effect."""
    IN = "in"
    OUT = "out"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class TransitionConfig:
    """Configuration for a scene transition effect."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    effect: TransitionEffect = TransitionEffect.FADE
    duration: float = 0.5
    easing: str = "linear"
    direction: TransitionDirection = TransitionDirection.IN
    color_rgba: Tuple[int, int, int, int] = (0, 0, 0, 255)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "effect": self.effect.value,
            "duration": self.duration,
            "easing": self.easing,
            "direction": self.direction.value,
            "color_rgba": list(self.color_rgba),
        }


@dataclass
class SceneDescriptor:
    """Metadata describing a scene and its dependencies."""
    descriptor_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    path: str = ""
    load_mode: SceneLoadMode = SceneLoadMode.SINGLE
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "descriptor_id": self.descriptor_id,
            "name": self.name,
            "path": self.path,
            "load_mode": self.load_mode.value,
            "dependencies": list(self.dependencies),
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneInstance:
    """Runtime representation of a loaded scene."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    descriptor_id: str = ""
    state: SceneState = SceneState.UNLOADED
    load_progress: float = 0.0
    start_time: float = 0.0
    active_since: float = 0.0
    transition_config: Optional[TransitionConfig] = None
    loading_tasks: int = 0
    completed_tasks: int = 0
    gc_references: List[str] = field(default_factory=list)
    is_additive: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "descriptor_id": self.descriptor_id,
            "state": self.state.value,
            "load_progress": self.load_progress,
            "start_time": self.start_time,
            "active_since": self.active_since,
            "transition_config": self.transition_config.to_dict() if self.transition_config else None,
            "loading_tasks": self.loading_tasks,
            "completed_tasks": self.completed_tasks,
            "gc_references": list(self.gc_references),
            "is_additive": self.is_additive,
        }


@dataclass
class TransitionState:
    """Active transition tracking progress between two scenes."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_scene_id: str = ""
    to_scene_id: str = ""
    config: TransitionConfig = field(default_factory=TransitionConfig)
    progress: float = 0.0
    elapsed: float = 0.0
    active: bool = True
    start_time: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "config": self.config.to_dict(),
            "progress": self.progress,
            "elapsed": self.elapsed,
            "active": self.active,
            "start_time": self.start_time,
        }


@dataclass
class TransitionResult:
    """Outcome of a completed scene transition."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    success: bool = False
    from_scene_id: str = ""
    to_scene_id: str = ""
    transition_time: float = 0.0
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "success": self.success,
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "transition_time": self.transition_time,
            "error_message": self.error_message,
        }


@dataclass
class SceneStats:
    """Aggregate telemetry across all scene operations."""
    active_scenes: int = 0
    total_loading_time: float = 0.0
    transition_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_scenes": self.active_scenes,
            "total_loading_time": self.total_loading_time,
            "transition_count": self.transition_count,
        }


# ---------------------------------------------------------------------------
# EngineSceneTransition — Thread-Safe Singleton
# ---------------------------------------------------------------------------

class EngineSceneTransition:
    """
    Central scene loading, unloading, and transition orchestrator.

    Manages scene descriptors, runtime instances, transition effects,
    and resource lifecycle (GC references). Thread-safe via reentrant lock.

    Usage:
        st = get_scene_transition()
        desc = st.register_scene(SceneDescriptor(name="level1", path="/levels/1.json"))
        inst = st.load_scene(desc.descriptor_id)
        cfg = st.create_default_transition()
        ts = st.transition_to(inst.instance_id, desc2.descriptor_id, cfg)
    """

    _instance: Optional["EngineSceneTransition"] = None
    _lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    def __new__(cls) -> "EngineSceneTransition":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineSceneTransition":
        """Return the singleton EngineSceneTransition instance."""
        return cls()

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        self._descriptors: Dict[str, SceneDescriptor] = {}
        self._instances: Dict[str, SceneInstance] = {}
        self._transitions: Dict[str, TransitionState] = {}
        self._results: List[TransitionResult] = []

        self._total_transitions: int = 0
        self._total_loading_time: float = 0.0

    # ------------------------------------------------------------------
    # Scene Registration & Loading
    # ------------------------------------------------------------------

    def register_scene(self, descriptor: SceneDescriptor) -> str:
        """Register a scene descriptor and return its id."""
        with self._lock:
            self._descriptors[descriptor.descriptor_id] = descriptor
            return descriptor.descriptor_id

    def load_scene(
        self,
        descriptor_id: str,
        load_mode: SceneLoadMode = SceneLoadMode.SINGLE,
        transition_config: Optional[TransitionConfig] = None,
    ) -> Optional[SceneInstance]:
        """Load a scene, creating a runtime instance."""
        desc = self._descriptors.get(descriptor_id)
        if desc is None:
            return None

        now = _time_module.time()

        # If SINGLE mode, unload all active non-additive scenes
        if load_mode == SceneLoadMode.SINGLE:
            for inst in list(self._instances.values()):
                if not inst.is_additive and inst.state in (
                    SceneState.ACTIVE, SceneState.LOADING,
                ):
                    inst.state = SceneState.UNLOADING
                    inst.gc_references.clear()

        instance = SceneInstance(
            descriptor_id=descriptor_id,
            state=SceneState.LOADING,
            start_time=now,
            transition_config=transition_config,
            is_additive=(load_mode == SceneLoadMode.ADDITIVE),
        )
        self._instances[instance.instance_id] = instance
        return instance

    def unload_scene(
        self,
        instance_id: str,
        transition_config: Optional[TransitionConfig] = None,
    ) -> Optional[TransitionState]:
        """Begin unloading a scene with an optional transition."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return None

        inst.state = SceneState.UNLOADING
        cfg = transition_config or self.create_default_transition()

        ts = TransitionState(
            from_scene_id=instance_id,
            to_scene_id="",
            config=cfg,
            start_time=_time_module.time(),
        )
        self._transitions[ts.transition_id] = ts
        return ts

    # ------------------------------------------------------------------
    # Transition Flow
    # ------------------------------------------------------------------

    def transition_to(
        self,
        from_instance_id: str,
        to_descriptor_id: str,
        config: TransitionConfig,
    ) -> Optional[TransitionState]:
        """Start a transition from one scene to another."""
        from_inst = self._instances.get(from_instance_id)
        if from_inst is None:
            return None
        if to_descriptor_id not in self._descriptors:
            return None

        ts = TransitionState(
            from_scene_id=from_instance_id,
            to_scene_id=to_descriptor_id,
            config=config,
            start_time=_time_module.time(),
        )
        self._transitions[ts.transition_id] = ts
        return ts

    def update_transition(
        self, transition_id: str, delta_time: float,
    ) -> Tuple[bool, Optional[TransitionResult]]:
        """Advance a transition; returns (is_complete, result) when done."""
        ts = self._transitions.get(transition_id)
        if ts is None or not ts.active:
            return (True, TransitionResult(
                success=False,
                from_scene_id=ts.from_scene_id if ts else "",
                to_scene_id=ts.to_scene_id if ts else "",
                error_message="transition not found or inactive",
            ))

        dt = max(0.0, delta_time)
        ts.elapsed += dt

        progress = self.compute_transition_progress(
            ts.elapsed, ts.config.duration, ts.config.easing,
        )
        ts.progress = min(1.0, progress)

        if ts.progress >= 1.0:
            ts.active = False
            now = _time_module.time()
            transition_time = now - ts.start_time
            self._total_loading_time += transition_time
            self._total_transitions += 1

            # Unload old scene
            from_inst = self._instances.get(ts.from_scene_id)
            if from_inst is not None:
                from_inst.state = SceneState.UNLOADED
                from_inst.gc_references.clear()

            # Activate new scene
            new_inst = self.load_scene(ts.to_scene_id, SceneLoadMode.ADDITIVE)
            if new_inst is not None:
                new_inst.state = SceneState.ACTIVE
                new_inst.active_since = now

            result = TransitionResult(
                success=True,
                from_scene_id=ts.from_scene_id,
                to_scene_id=ts.to_scene_id,
                transition_time=transition_time,
            )
            self._results.append(result)
            return (True, result)

        return (False, None)

    def cancel_transition(self, transition_id: str) -> bool:
        """Cancel an active transition."""
        ts = self._transitions.get(transition_id)
        if ts is None:
            return False
        ts.active = False
        ts.progress = 0.0
        return True

    # ------------------------------------------------------------------
    # Scene Lifecycle
    # ------------------------------------------------------------------

    def update_scene(
        self, instance_id: str, delta_time: float,
    ) -> Optional[SceneInstance]:
        """Update a scene's internal state machine."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return None

        if inst.state == SceneState.PAUSING:
            inst.state = SceneState.PAUSED
        elif inst.state == SceneState.RESUMING:
            inst.state = SceneState.ACTIVE

        return inst

    def pause_scene(self, instance_id: str) -> bool:
        """Request a scene to pause."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        if inst.state != SceneState.ACTIVE:
            return False
        inst.state = SceneState.PAUSING
        return True

    def resume_scene(self, instance_id: str) -> bool:
        """Request a scene to resume."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        if inst.state != SceneState.PAUSED:
            return False
        inst.state = SceneState.RESUMING
        return True

    def set_scene_progress(
        self, instance_id: str, progress: float,
    ) -> bool:
        """Set the loading progress of a scene (0.0 to 1.0)."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        inst.load_progress = max(0.0, min(1.0, progress))
        if inst.load_progress >= 1.0 and inst.state == SceneState.LOADING:
            inst.state = SceneState.ACTIVE
            inst.active_since = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Scene Query
    # ------------------------------------------------------------------

    def get_scene_state(self, instance_id: str) -> Optional[SceneState]:
        """Return the current state of a scene instance."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return None
        return inst.state

    def get_active_scenes(self) -> List[SceneInstance]:
        """Return all currently active or loading scenes."""
        return [
            inst for inst in self._instances.values()
            if inst.state in (SceneState.ACTIVE, SceneState.LOADING)
        ]

    def get_scene_by_name(self, name: str) -> Optional[SceneInstance]:
        """Find a scene instance by its descriptor name."""
        for inst in self._instances.values():
            desc = self._descriptors.get(inst.descriptor_id)
            if desc is not None and desc.name == name:
                return inst
        return None

    def get_all_descriptors(self) -> List[SceneDescriptor]:
        """Return all registered scene descriptors."""
        return list(self._descriptors.values())

    # ------------------------------------------------------------------
    # GC References
    # ------------------------------------------------------------------

    def set_scene_gc_references(
        self, instance_id: str, references: List[str],
    ) -> bool:
        """Set references to be garbage-collected when the scene unloads."""
        inst = self._instances.get(instance_id)
        if inst is None:
            return False
        inst.gc_references = list(references)
        return True

    # ------------------------------------------------------------------
    # Easing & Effect Computation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_transition_progress(
        elapsed: float, duration: float, easing: str,
    ) -> float:
        """Compute normalised progress (0.0–1.0) using the given easing."""
        safe_duration = max(duration, 0.0001)
        t = max(0.0, min(1.0, elapsed / safe_duration))

        if easing == "linear":
            return t
        elif easing == "ease-in":
            return t * t
        elif easing == "ease-out":
            return 1.0 - (1.0 - t) * (1.0 - t)
        elif easing == "ease-in-out":
            if t < 0.5:
                return 2.0 * t * t
            return 1.0 - (-2.0 * t + 2.0) ** 2 / 2.0
        elif easing == "cubic":
            return t * t * t
        elif easing == "elastic":
            if t == 0.0 or t == 1.0:
                return t
            c4 = (2.0 * math.pi) / 3.0
            return -(2.0 ** (10.0 * t - 10.0)) * math.sin((t * 10.0 - 10.75) * c4)
        else:
            return t

    @staticmethod
    def get_transition_alpha(
        config: TransitionConfig, progress: float,
    ) -> float:
        """Compute the alpha value for transition effects at a given progress."""
        p = max(0.0, min(1.0, progress))
        effect = config.effect

        if effect == TransitionEffect.FADE:
            return p
        elif effect == TransitionEffect.CROSSFADE:
            return p
        elif effect == TransitionEffect.DISSOLVE:
            # Dissolve ramps alpha based on a pseudo-random threshold
            return 1.0 if p > 0.5 else p * 2.0
        elif effect == TransitionEffect.ZOOM_IN:
            return p
        elif effect == TransitionEffect.ZOOM_OUT:
            return p
        elif effect == TransitionEffect.WIPE:
            return p
        elif effect == TransitionEffect.NONE:
            return 0.0
        else:
            # Slide effects don't use alpha; they use positional offset
            return 0.0

    @staticmethod
    def get_transition_offset(
        config: TransitionConfig, progress: float,
    ) -> Tuple[float, float]:
        """Compute the screen-space offset for slide and wipe effects."""
        p = max(0.0, min(1.0, progress))
        magnitude = 1.0 - p if config.direction == TransitionDirection.IN else p

        effect = config.effect
        if effect == TransitionEffect.SLIDE_LEFT:
            return (-magnitude, 0.0)
        elif effect == TransitionEffect.SLIDE_RIGHT:
            return (magnitude, 0.0)
        elif effect == TransitionEffect.SLIDE_UP:
            return (0.0, -magnitude)
        elif effect == TransitionEffect.SLIDE_DOWN:
            return (0.0, magnitude)
        elif effect == TransitionEffect.WIPE:
            return (magnitude - 1.0, 0.0)
        else:
            return (0.0, 0.0)

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_scene_stats(self) -> SceneStats:
        """Return aggregate scene telemetry."""
        active_count = sum(
            1 for inst in self._instances.values()
            if inst.state == SceneState.ACTIVE
        )
        return SceneStats(
            active_scenes=active_count,
            total_loading_time=self._total_loading_time,
            transition_count=self._total_transitions,
        )

    def get_stats(self) -> dict:
        """Return stats as dict for existing engine integration."""
        return self.get_scene_stats().to_dict()

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @staticmethod
    def create_default_transition() -> TransitionConfig:
        """Return a default FADE transition with ease-in-out easing."""
        return TransitionConfig(
            effect=TransitionEffect.FADE,
            duration=0.5,
            easing="ease-in-out",
            direction=TransitionDirection.IN,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Remove all descriptors, instances, and transitions."""
        with self._lock:
            self._descriptors.clear()
            self._instances.clear()
            self._transitions.clear()
            self._results.clear()
            self._total_transitions = 0
            self._total_loading_time = 0.0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_scene_transition() -> EngineSceneTransition:
    """Return the singleton EngineSceneTransition instance."""
    return EngineSceneTransition.get_instance()


# Compatibility alias for existing engine integration
SceneTransitionSystem = EngineSceneTransition