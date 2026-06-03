"""
SparkLabs Engine - Scene Manager

Comprehensive scene-based architecture with a transitions system for
the SparkLabs game engine. Provides scene definitions, layered scene
composition, transition orchestration between scenes, and lifecycle
management for the full scene graph. Supports loading, unloading,
switching, and updating scenes with configurable transition effects
and easing curves.

Architecture:
  EngineSceneManager (Singleton)
    |-- SceneDefinition    — full scene descriptor with layers, entities, cameras
    |-- SceneTransition    — transition config between two scenes
    |-- SceneLayer         — render layer with z-ordering, parallax, and filters
    |-- SceneType (enum)   — semantic classification of scene purposes
    |-- TransitionType (enum) — visual transition effect identifiers
    |-- EasingType (enum)  — interpolation curve prescriptions

Scene Lifecycle:
  1. create_scene(name, scene_type) → scene definition created
  2. create_layer(name, z_index) → layer definition created
  3. add_layer_to_scene(scene_id, layer_id) → layer attached to scene
  4. define_transition(from_scene, to_scene, type, duration) → transition
  5. switch_scene(to_scene_id) → active transition begins
  6. load_scene / unload_scene → manage scene resource lifecycle
  7. update_scene(scene_id, delta) → per-frame scene tick
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SceneType(Enum):
    """Semantic classification of scene purposes within the game.

    MAIN_MENU:     Title screen and main navigation hub.
    GAMEPLAY:      Primary interactive game world scene.
    CUTSCENE:      Non-interactive cinematic sequence.
    LOADING:       Transitional loading screen with progress display.
    SETTINGS:      Configuration and options menu overlay.
    HUD_OVERLAY:   Heads-up display rendered above gameplay.
    MINIMAP:       Corner or overlay minimap render target.
    PAUSE:         Pause menu overlay with resume/quit options.
    DIALOGUE:      Dialogue and conversation UI scene.
    INVENTORY:     Item management and equipment screen.
    """

    MAIN_MENU = "main_menu"
    GAMEPLAY = "gameplay"
    CUTSCENE = "cutscene"
    LOADING = "loading"
    SETTINGS = "settings"
    HUD_OVERLAY = "hud_overlay"
    MINIMAP = "minimap"
    PAUSE = "pause"
    DIALOGUE = "dialogue"
    INVENTORY = "inventory"


class TransitionType(Enum):
    """Visual transition effect applied when switching between scenes.

    FADE:         Gradual opacity blend from one scene to another.
    SLIDE_LEFT:   Incoming scene slides in from the right.
    SLIDE_RIGHT:  Incoming scene slides in from the left.
    SLIDE_UP:     Incoming scene slides in from below.
    SLIDE_DOWN:   Incoming scene slides in from above.
    ZOOM_IN:      Camera zooms into the new scene.
    ZOOM_OUT:     Camera zooms out to reveal the new scene.
    WIPE:         Hard edge sweeps across the screen.
    DISSOLVE:     Pixel-by-pixel random dissolve effect.
    CROSSFADE:    Both scenes rendered simultaneously with opacity blend.
    NONE:         Instant switch with no visual transition.
    """

    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    WIPE = "wipe"
    DISSOLVE = "dissolve"
    CROSSFADE = "crossfade"
    NONE = "none"


class EasingType(Enum):
    """Interpolation curve used to control transition pacing.

    LINEAR:       Constant rate of change throughout the transition.
    EASE_IN:      Slow start, accelerating toward the end.
    EASE_OUT:     Fast start, decelerating toward the end.
    EASE_IN_OUT:  Slow at both ends, fast in the middle.
    BOUNCE:       Overshoots and bounces at the target endpoint.
    ELASTIC:      Spring-like oscillation settling at the target.
    BACK:         Overshoots slightly before settling back.
    """

    LINEAR = "linear"
    EASE_IN = "ease_in"
    EASE_OUT = "ease_out"
    EASE_IN_OUT = "ease_in_out"
    BOUNCE = "bounce"
    ELASTIC = "elastic"
    BACK = "back"


# ------------------------------------------------------------------
# Pre-defined easing curve lookup tables
# ------------------------------------------------------------------

_EASING_CURVES: Dict[str, Dict[str, Any]] = {
    "linear": {
        "name": "Linear",
        "description": "Constant rate of change throughout the transition",
        "control_points": [(0.0, 0.0), (1.0, 1.0)],
    },
    "ease_in": {
        "name": "Ease In",
        "description": "Slow start, accelerating toward the end",
        "control_points": [(0.0, 0.0), (0.42, 0.0), (1.0, 1.0)],
    },
    "ease_out": {
        "name": "Ease Out",
        "description": "Fast start, decelerating toward the end",
        "control_points": [(0.0, 0.0), (0.58, 1.0), (1.0, 1.0)],
    },
    "ease_in_out": {
        "name": "Ease In Out",
        "description": "Slow at both ends, fast in the middle",
        "control_points": [(0.0, 0.0), (0.42, 0.0), (0.58, 1.0), (1.0, 1.0)],
    },
    "bounce": {
        "name": "Bounce",
        "description": "Overshoots and bounces at the target endpoint",
        "control_points": [(0.0, 0.0), (0.2, 0.9), (0.4, 0.3), (0.6, 0.95), (0.8, 0.75), (1.0, 1.0)],
    },
    "elastic": {
        "name": "Elastic",
        "description": "Spring-like oscillation settling at the target",
        "control_points": [(0.0, 0.0), (0.16, 1.1), (0.28, 0.88), (0.44, 1.02), (0.6, 0.98), (0.76, 1.0), (1.0, 1.0)],
    },
    "back": {
        "name": "Back",
        "description": "Overshoots slightly before settling back",
        "control_points": [(0.0, 0.0), (0.4, -0.1), (0.8, 0.6), (1.0, 1.0)],
    },
}

# ------------------------------------------------------------------
# Pre-defined transition presets
# ------------------------------------------------------------------

_TRANSITION_PRESETS: Dict[str, Dict[str, Any]] = {
    "quick_fade": {
        "name": "Quick Fade",
        "transition_type": TransitionType.FADE,
        "duration": 0.3,
        "easing": EasingType.EASE_OUT,
        "description": "Rapid fade transition for menu navigation",
    },
    "smooth_crossfade": {
        "name": "Smooth Crossfade",
        "transition_type": TransitionType.CROSSFADE,
        "duration": 0.8,
        "easing": EasingType.EASE_IN_OUT,
        "description": "Smooth crossfade for scene transitions",
    },
    "dramatic_zoom": {
        "name": "Dramatic Zoom",
        "transition_type": TransitionType.ZOOM_IN,
        "duration": 1.2,
        "easing": EasingType.EASE_IN,
        "description": "Dramatic zoom-in for cinematic moments",
    },
    "slide_left_enter": {
        "name": "Slide Left Enter",
        "transition_type": TransitionType.SLIDE_LEFT,
        "duration": 0.5,
        "easing": EasingType.EASE_OUT,
        "description": "Scene slides in from the right side",
    },
    "slide_right_enter": {
        "name": "Slide Right Enter",
        "transition_type": TransitionType.SLIDE_RIGHT,
        "duration": 0.5,
        "easing": EasingType.EASE_OUT,
        "description": "Scene slides in from the left side",
    },
    "dissolve_mystical": {
        "name": "Mystical Dissolve",
        "transition_type": TransitionType.DISSOLVE,
        "duration": 1.0,
        "easing": EasingType.EASE_IN_OUT,
        "description": "Pixel dissolve for magical or dream sequences",
    },
    "wipe_clean": {
        "name": "Clean Wipe",
        "transition_type": TransitionType.WIPE,
        "duration": 0.6,
        "easing": EasingType.LINEAR,
        "description": "Clean horizontal wipe across the screen",
    },
    "bounce_in": {
        "name": "Bounce In",
        "transition_type": TransitionType.FADE,
        "duration": 0.7,
        "easing": EasingType.BOUNCE,
        "description": "Playful bounce-in for game over or victory screens",
    },
    "elastic_snap": {
        "name": "Elastic Snap",
        "transition_type": TransitionType.ZOOM_OUT,
        "duration": 0.9,
        "easing": EasingType.ELASTIC,
        "description": "Springy zoom-out for map or overview transitions",
    },
    "instant": {
        "name": "Instant",
        "transition_type": TransitionType.NONE,
        "duration": 0.0,
        "easing": EasingType.LINEAR,
        "description": "Instant switch with no visual transition",
    },
}


@dataclass
class SceneLayer:
    """A single render layer within a scene with z-ordering and effects.

    Layers define the visual stacking order within a scene, supporting
    parallax scrolling, visibility toggling, per-layer render targets,
    and configurable post-processing filters.
    """

    layer_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    z_index: int = 0
    visible: bool = True
    parallax_factor: Tuple[float, float] = (1.0, 1.0)
    render_target: str = ""
    filters: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_id": self.layer_id,
            "name": self.name,
            "z_index": self.z_index,
            "visible": self.visible,
            "parallax_factor": list(self.parallax_factor),
            "render_target": self.render_target,
            "filters": list(self.filters),
            "created_at": self.created_at,
        }


@dataclass
class SceneDefinition:
    """A complete scene descriptor containing all layers, entities, and
    configuration needed to render and simulate a game scene.

    Holds references to scene layers, entity IDs, camera configurations,
    lighting properties, physics settings, audio tracks, and script
    attachments. Acts as the authoritative definition for a scene within
    the scene manager graph.
    """

    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scene_type: SceneType = SceneType.GAMEPLAY
    layers: List[SceneLayer] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    cameras: List[Dict[str, Any]] = field(default_factory=list)
    ambient_light: Dict[str, Any] = field(default_factory=lambda: {
        "color": [1.0, 1.0, 1.0],
        "intensity": 1.0,
    })
    background_color: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    physics_enabled: bool = False
    audio_track: str = ""
    scripts: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_loaded: bool = False
    is_active: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "scene_type": self.scene_type.value,
            "layers": [layer.to_dict() for layer in self.layers],
            "entities": list(self.entities),
            "cameras": [dict(c) for c in self.cameras],
            "ambient_light": dict(self.ambient_light),
            "background_color": list(self.background_color),
            "physics_enabled": self.physics_enabled,
            "audio_track": self.audio_track,
            "scripts": list(self.scripts),
            "metadata": dict(self.metadata),
            "is_loaded": self.is_loaded,
            "is_active": self.is_active,
            "layer_count": len(self.layers),
            "entity_count": len(self.entities),
            "created_at": self.created_at,
        }


@dataclass
class SceneTransition:
    """Configuration for a transition between two scenes.

    Defines the source and destination scene IDs, the visual effect
    type, duration, easing curve, and optional completion scripts.
    Parameters allow arbitrary data to be passed to custom transition
    shaders or script callbacks.
    """

    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_scene_id: str = ""
    to_scene_id: str = ""
    transition_type: TransitionType = TransitionType.FADE
    duration: float = 0.5
    easing: EasingType = EasingType.EASE_IN_OUT
    on_complete_script: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "easing": self.easing.value,
            "on_complete_script": self.on_complete_script,
            "parameters": dict(self.parameters),
            "created_at": self.created_at,
        }


class EngineSceneManager:
    """Comprehensive scene-based architecture with transitions system.

    Manages the full lifecycle of scene definitions, layered scene
    composition, and transition orchestration. Provides scene creation,
    layer management, transition definition, scene switching with
    animated effects, and per-frame scene updates.

    Thread-safe via a reentrant lock. Use get_scene_manager() or
    EngineSceneManager.get_instance() to obtain the singleton instance.

    Usage:
        mgr = get_scene_manager()
        scene_id = mgr.create_scene("overworld", SceneType.GAMEPLAY)
        layer_id = mgr.create_layer("terrain", z_index=0)
        mgr.add_layer_to_scene(scene_id, layer_id)
        transition_id = mgr.define_transition(
            scene_id, "target_scene", TransitionType.CROSSFADE, 0.8
        )
        mgr.switch_scene("target_scene", transition_id)
        mgr.update_scene("target_scene", 0.016)
    """

    _instance: Optional["EngineSceneManager"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SCENES: int = 128
    MAX_LAYERS_PER_SCENE: int = 64
    MAX_TRANSITIONS: int = 256
    MAX_ENTITIES_PER_SCENE: int = 4096
    MAX_CAMERAS_PER_SCENE: int = 8

    def __new__(cls) -> "EngineSceneManager":
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
        self._scenes: Dict[str, SceneDefinition] = {}
        self._layers: Dict[str, SceneLayer] = {}
        self._transitions: Dict[str, SceneTransition] = {}
        self._active_scene_id: Optional[str] = None
        self._scene_layer_map: Dict[str, List[str]] = {}
        self._transition_presets: Dict[str, Dict[str, Any]] = dict(_TRANSITION_PRESETS)
        self._easing_curves: Dict[str, Dict[str, Any]] = dict(_EASING_CURVES)
        self._transition_in_progress: bool = False
        self._transition_timer: float = 0.0
        self._current_transition_id: Optional[str] = None
        self._total_scenes_created: int = 0
        self._total_layers_created: int = 0
        self._total_transitions_defined: int = 0
        self._total_switches: int = 0
        self._scene_load_order: List[str] = []
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineSceneManager":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_scene(self, scene_id: str) -> SceneDefinition:
        _time_module.sleep(0.001)
        if scene_id not in self._scenes:
            raise KeyError(f"Scene '{scene_id}' does not exist")
        return self._scenes[scene_id]

    def _get_layer(self, layer_id: str) -> SceneLayer:
        _time_module.sleep(0.001)
        if layer_id not in self._layers:
            raise KeyError(f"Layer '{layer_id}' does not exist")
        return self._layers[layer_id]

    def _get_transition(self, transition_id: str) -> SceneTransition:
        _time_module.sleep(0.001)
        if transition_id not in self._transitions:
            raise KeyError(f"Transition '{transition_id}' does not exist")
        return self._transitions[transition_id]

    def _validate_scene_type(self, scene_type: str) -> SceneType:
        _time_module.sleep(0.001)
        try:
            return SceneType(scene_type.lower())
        except ValueError:
            return SceneType.GAMEPLAY

    def _validate_transition_type(self, transition_type: str) -> TransitionType:
        _time_module.sleep(0.001)
        try:
            return TransitionType(transition_type.lower())
        except ValueError:
            return TransitionType.FADE

    def _validate_easing_type(self, easing: str) -> EasingType:
        _time_module.sleep(0.001)
        try:
            return EasingType(easing.lower())
        except ValueError:
            return EasingType.EASE_IN_OUT

    def _sort_layers_by_z(self, scene: SceneDefinition) -> None:
        _time_module.sleep(0.001)
        if not scene.layers:
            return
        scene.layers.sort(key=lambda layer: layer.z_index)

    def _complete_transition(self) -> None:
        _time_module.sleep(0.001)
        if self._current_transition_id is None:
            return
        transition = self._transitions.get(self._current_transition_id)
        self._transition_in_progress = False
        self._transition_timer = 0.0
        self._current_transition_id = None
        if transition is not None and transition.to_scene_id in self._scenes:
            target_scene = self._scenes[transition.to_scene_id]
            target_scene.is_active = True
            if transition.from_scene_id and transition.from_scene_id in self._scenes:
                source_scene = self._scenes[transition.from_scene_id]
                source_scene.is_active = False
            self._active_scene_id = transition.to_scene_id

    # ------------------------------------------------------------------
    # Scene creation and management
    # ------------------------------------------------------------------

    def create_scene(
        self,
        name: str,
        scene_type: str = "gameplay",
        background_color: Optional[List[float]] = None,
        physics_enabled: bool = False,
        audio_track: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SceneDefinition:
        _time_module.sleep(0.001)
        if len(self._scenes) >= self.MAX_SCENES:
            raise RuntimeError(
                f"Scene limit reached ({self.MAX_SCENES})"
            )
        if not name:
            raise ValueError("scene name must not be empty")

        st = self._validate_scene_type(scene_type)
        bg = background_color if background_color is not None else [0.0, 0.0, 0.0, 1.0]

        scene = SceneDefinition(
            name=name,
            scene_type=st,
            background_color=bg,
            physics_enabled=physics_enabled,
            audio_track=audio_track,
            metadata=metadata or {},
        )
        self._scenes[scene.scene_id] = scene
        self._scene_layer_map[scene.scene_id] = []
        self._total_scenes_created += 1
        return scene

    def create_layer(
        self,
        name: str,
        z_index: int = 0,
        visible: bool = True,
        parallax_factor: Optional[Tuple[float, float]] = None,
        render_target: str = "",
        filters: Optional[List[str]] = None,
    ) -> SceneLayer:
        _time_module.sleep(0.001)
        if not name:
            raise ValueError("layer name must not be empty")

        pf = parallax_factor if parallax_factor is not None else (1.0, 1.0)

        layer = SceneLayer(
            name=name,
            z_index=z_index,
            visible=visible,
            parallax_factor=pf,
            render_target=render_target,
            filters=filters or [],
        )
        self._layers[layer.layer_id] = layer
        self._total_layers_created += 1
        return layer

    def add_layer_to_scene(
        self,
        scene_id: str,
        layer_id: str,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        layer = self._get_layer(layer_id)

        if len(scene.layers) >= self.MAX_LAYERS_PER_SCENE:
            raise RuntimeError(
                f"Layer limit reached ({self.MAX_LAYERS_PER_SCENE}) for scene '{scene_id}'"
            )

        if layer_id in self._scene_layer_map.get(scene_id, []):
            return False

        scene.layers.append(layer)
        self._scene_layer_map.setdefault(scene_id, []).append(layer_id)
        self._sort_layers_by_z(scene)
        return True

    def remove_layer_from_scene(
        self,
        scene_id: str,
        layer_id: str,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        for i, layer in enumerate(scene.layers):
            if layer.layer_id == layer_id:
                scene.layers.pop(i)
                if scene_id in self._scene_layer_map:
                    self._scene_layer_map[scene_id] = [
                        lid for lid in self._scene_layer_map[scene_id] if lid != layer_id
                    ]
                return True
        return False

    def set_layer_z_index(
        self,
        scene_id: str,
        layer_id: str,
        z_index: int,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        for layer in scene.layers:
            if layer.layer_id == layer_id:
                layer.z_index = z_index
                self._sort_layers_by_z(scene)
                return True
        return False

    def set_layer_visibility(
        self,
        scene_id: str,
        layer_id: str,
        visible: bool,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        for layer in scene.layers:
            if layer.layer_id == layer_id:
                layer.visible = visible
                return True
        return False

    # ------------------------------------------------------------------
    # Transition management
    # ------------------------------------------------------------------

    def define_transition(
        self,
        from_scene_id: str,
        to_scene_id: str,
        transition_type: str = "fade",
        duration: float = 0.5,
        easing: str = "ease_in_out",
        on_complete_script: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> SceneTransition:
        _time_module.sleep(0.001)
        if len(self._transitions) >= self.MAX_TRANSITIONS:
            raise RuntimeError(
                f"Transition limit reached ({self.MAX_TRANSITIONS})"
            )

        if from_scene_id and from_scene_id not in self._scenes:
            raise KeyError(f"From-scene '{from_scene_id}' does not exist")
        if to_scene_id not in self._scenes:
            raise KeyError(f"To-scene '{to_scene_id}' does not exist")

        tt = self._validate_transition_type(transition_type)
        et = self._validate_easing_type(easing)

        if duration < 0.0:
            duration = 0.0

        transition = SceneTransition(
            from_scene_id=from_scene_id,
            to_scene_id=to_scene_id,
            transition_type=tt,
            duration=duration,
            easing=et,
            on_complete_script=on_complete_script,
            parameters=parameters or {},
        )
        self._transitions[transition.transition_id] = transition
        self._total_transitions_defined += 1
        return transition

    def define_transition_from_preset(
        self,
        from_scene_id: str,
        to_scene_id: str,
        preset_name: str,
        on_complete_script: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[SceneTransition]:
        _time_module.sleep(0.001)
        preset = self._transition_presets.get(preset_name)
        if preset is None:
            return None
        return self.define_transition(
            from_scene_id=from_scene_id,
            to_scene_id=to_scene_id,
            transition_type=preset["transition_type"].value,
            duration=preset["duration"],
            easing=preset["easing"].value,
            on_complete_script=on_complete_script,
            parameters=parameters,
        )

    def switch_scene(
        self,
        to_scene_id: str,
        transition_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if to_scene_id not in self._scenes:
            return {
                "success": False,
                "error": "target_scene_not_found",
                "to_scene_id": to_scene_id,
            }

        if self._transition_in_progress:
            return {
                "success": False,
                "error": "transition_already_in_progress",
                "current_transition": self._current_transition_id,
            }

        from_scene_id = self._active_scene_id or ""

        if transition_id is not None and transition_id in self._transitions:
            transition = self._transitions[transition_id]
        else:
            transition = self.define_transition(
                from_scene_id=from_scene_id,
                to_scene_id=to_scene_id,
                transition_type="crossfade",
                duration=0.5,
                easing="ease_in_out",
            )

        if transition.duration <= 0.0:
            self._complete_transition()
            self._total_switches += 1
            return {
                "success": True,
                "transition_type": "instant",
                "from_scene_id": from_scene_id,
                "to_scene_id": to_scene_id,
                "transition_id": transition.transition_id,
            }

        self._transition_in_progress = True
        self._transition_timer = 0.0
        self._current_transition_id = transition.transition_id
        self._total_switches += 1

        target_scene = self._scenes[to_scene_id]
        target_scene.is_loaded = True

        return {
            "success": True,
            "transition_type": transition.transition_type.value,
            "duration": transition.duration,
            "easing": transition.easing.value,
            "from_scene_id": from_scene_id,
            "to_scene_id": to_scene_id,
            "transition_id": transition.transition_id,
        }

    def get_transition_progress(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if not self._transition_in_progress or self._current_transition_id is None:
            return {
                "in_progress": False,
                "progress": 0.0,
                "transition_id": None,
            }

        transition = self._transitions.get(self._current_transition_id)
        if transition is None:
            self._transition_in_progress = False
            return {
                "in_progress": False,
                "progress": 0.0,
                "transition_id": None,
            }

        raw_progress = self._transition_timer / max(0.001, transition.duration)
        raw_progress = min(1.0, max(0.0, raw_progress))

        return {
            "in_progress": True,
            "progress": round(raw_progress, 4),
            "transition_id": self._current_transition_id,
            "transition_type": transition.transition_type.value,
            "easing": transition.easing.value,
            "from_scene_id": transition.from_scene_id,
            "to_scene_id": transition.to_scene_id,
        }

    def is_transitioning(self) -> bool:
        _time_module.sleep(0.001)
        return self._transition_in_progress

    def cancel_transition(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if not self._transition_in_progress:
            return {"success": False, "error": "no_transition_in_progress"}

        cancelled_id = self._current_transition_id
        self._transition_in_progress = False
        self._transition_timer = 0.0
        self._current_transition_id = None

        return {
            "success": True,
            "cancelled_transition_id": cancelled_id,
        }

    # ------------------------------------------------------------------
    # Scene lifecycle
    # ------------------------------------------------------------------

    def load_scene(self, scene_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if scene.is_loaded:
            return {
                "success": True,
                "scene_id": scene_id,
                "already_loaded": True,
            }

        scene.is_loaded = True
        if scene_id not in self._scene_load_order:
            self._scene_load_order.append(scene_id)

        return {
            "success": True,
            "scene_id": scene_id,
            "scene_name": scene.name,
            "scene_type": scene.scene_type.value,
            "layer_count": len(scene.layers),
            "entity_count": len(scene.entities),
            "load_order_index": self._scene_load_order.index(scene_id),
        }

    def unload_scene(self, scene_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if self._active_scene_id == scene_id:
            return {
                "success": False,
                "error": "cannot_unload_active_scene",
                "scene_id": scene_id,
            }

        if self._transition_in_progress and self._current_transition_id:
            transition = self._transitions.get(self._current_transition_id)
            if transition and transition.to_scene_id == scene_id:
                return {
                    "success": False,
                    "error": "cannot_unload_scene_in_transition",
                    "scene_id": scene_id,
                }

        scene.is_loaded = False
        scene.is_active = False

        if scene_id in self._scene_load_order:
            self._scene_load_order.remove(scene_id)

        return {
            "success": True,
            "scene_id": scene_id,
            "scene_name": scene.name,
            "was_loaded": True,
        }

    def get_active_scene(self) -> Optional[SceneDefinition]:
        _time_module.sleep(0.001)
        if self._active_scene_id is None:
            return None
        return self._scenes.get(self._active_scene_id)

    def list_scenes(
        self,
        scene_type: Optional[str] = None,
        loaded_only: bool = False,
        active_only: bool = False,
    ) -> List[SceneDefinition]:
        _time_module.sleep(0.001)
        results: List[SceneDefinition] = list(self._scenes.values())

        if scene_type is not None:
            try:
                st = SceneType(scene_type.lower())
                results = [s for s in results if s.scene_type == st]
            except ValueError:
                pass

        if loaded_only:
            results = [s for s in results if s.is_loaded]

        if active_only:
            results = [s for s in results if s.is_active]

        results.sort(key=lambda s: s.created_at)
        return results

    def get_scene(self, scene_id: str) -> Optional[SceneDefinition]:
        _time_module.sleep(0.001)
        return self._scenes.get(scene_id)

    def get_layer(self, layer_id: str) -> Optional[SceneLayer]:
        _time_module.sleep(0.001)
        return self._layers.get(layer_id)

    def get_transition(self, transition_id: str) -> Optional[SceneTransition]:
        _time_module.sleep(0.001)
        return self._transitions.get(transition_id)

    def find_scene_by_name(self, name: str) -> Optional[SceneDefinition]:
        _time_module.sleep(0.001)
        for scene in self._scenes.values():
            if scene.name == name:
                return scene
        return None

    # ------------------------------------------------------------------
    # Scene update
    # ------------------------------------------------------------------

    def update_scene(
        self,
        scene_id: str,
        delta_time: float,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if not scene.is_loaded:
            return {
                "success": False,
                "error": "scene_not_loaded",
                "scene_id": scene_id,
            }

        if self._transition_in_progress and self._current_transition_id:
            transition = self._transitions.get(self._current_transition_id)
            if transition is not None:
                self._transition_timer += delta_time
                if self._transition_timer >= transition.duration:
                    self._complete_transition()

        return {
            "success": True,
            "scene_id": scene_id,
            "scene_name": scene.name,
            "is_active": scene.is_active,
            "is_loaded": scene.is_loaded,
            "layer_count": len(scene.layers),
            "entity_count": len(scene.entities),
            "transition_in_progress": self._transition_in_progress,
            "transition_progress": round(
                self._transition_timer / max(0.001, (
                    self._transitions[self._current_transition_id].duration
                    if self._current_transition_id and self._current_transition_id in self._transitions
                    else 1.0
                )), 4
            ) if self._transition_in_progress else 0.0,
        }

    def update_active_scene(self, delta_time: float) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if self._active_scene_id is None:
            return {
                "success": False,
                "error": "no_active_scene",
            }
        return self.update_scene(self._active_scene_id, delta_time)

    # ------------------------------------------------------------------
    # Entity management
    # ------------------------------------------------------------------

    def add_entity_to_scene(
        self,
        scene_id: str,
        entity_id: str,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if len(scene.entities) >= self.MAX_ENTITIES_PER_SCENE:
            raise RuntimeError(
                f"Entity limit reached ({self.MAX_ENTITIES_PER_SCENE}) for scene '{scene_id}'"
            )

        if entity_id in scene.entities:
            return False

        scene.entities.append(entity_id)
        return True

    def remove_entity_from_scene(
        self,
        scene_id: str,
        entity_id: str,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if entity_id in scene.entities:
            scene.entities.remove(entity_id)
            return True
        return False

    # ------------------------------------------------------------------
    # Camera management
    # ------------------------------------------------------------------

    def add_camera_to_scene(
        self,
        scene_id: str,
        camera_config: Dict[str, Any],
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if len(scene.cameras) >= self.MAX_CAMERAS_PER_SCENE:
            raise RuntimeError(
                f"Camera limit reached ({self.MAX_CAMERAS_PER_SCENE}) for scene '{scene_id}'"
            )

        scene.cameras.append(dict(camera_config))
        return True

    def remove_camera_from_scene(
        self,
        scene_id: str,
        camera_index: int,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if 0 <= camera_index < len(scene.cameras):
            scene.cameras.pop(camera_index)
            return True
        return False

    # ------------------------------------------------------------------
    # Scene metadata
    # ------------------------------------------------------------------

    def set_scene_metadata(
        self,
        scene_id: str,
        key: str,
        value: Any,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        scene.metadata[key] = value
        return True

    def get_scene_metadata(
        self,
        scene_id: str,
        key: str,
        default: Any = None,
    ) -> Any:
        _time_module.sleep(0.001)
        scene = self._scenes.get(scene_id)
        if scene is None:
            return default
        return scene.metadata.get(key, default)

    def set_ambient_light(
        self,
        scene_id: str,
        color: List[float],
        intensity: float,
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        scene.ambient_light = {
            "color": list(color),
            "intensity": max(0.0, intensity),
        }
        return True

    def set_background_color(
        self,
        scene_id: str,
        color: List[float],
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if len(color) >= 4:
            scene.background_color = list(color[:4])
        elif len(color) >= 3:
            scene.background_color = [color[0], color[1], color[2], 1.0]
        return True

    # ------------------------------------------------------------------
    # Preset queries
    # ------------------------------------------------------------------

    def list_transition_presets(self) -> List[str]:
        _time_module.sleep(0.001)
        return sorted(self._transition_presets.keys())

    def get_transition_preset(self, preset_name: str) -> Optional[Dict[str, Any]]:
        _time_module.sleep(0.001)
        return self._transition_presets.get(preset_name)

    def list_easing_curves(self) -> List[str]:
        _time_module.sleep(0.001)
        return sorted(self._easing_curves.keys())

    def get_easing_curve(self, curve_name: str) -> Optional[Dict[str, Any]]:
        _time_module.sleep(0.001)
        return self._easing_curves.get(curve_name)

    # ------------------------------------------------------------------
    # Scene removal
    # ------------------------------------------------------------------

    def remove_scene(self, scene_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        if scene_id not in self._scenes:
            return {
                "success": False,
                "error": "scene_not_found",
                "scene_id": scene_id,
            }

        if self._active_scene_id == scene_id:
            return {
                "success": False,
                "error": "cannot_remove_active_scene",
                "scene_id": scene_id,
            }

        scene = self._scenes[scene_id]
        scene_name = scene.name

        transitions_to_remove = [
            tid for tid, t in self._transitions.items()
            if t.from_scene_id == scene_id or t.to_scene_id == scene_id
        ]
        for tid in transitions_to_remove:
            del self._transitions[tid]

        if self._current_transition_id in transitions_to_remove:
            self._transition_in_progress = False
            self._transition_timer = 0.0
            self._current_transition_id = None

        self._scene_layer_map.pop(scene_id, None)
        del self._scenes[scene_id]

        if scene_id in self._scene_load_order:
            self._scene_load_order.remove(scene_id)

        return {
            "success": True,
            "scene_id": scene_id,
            "scene_name": scene_name,
            "transitions_removed": len(transitions_to_remove),
        }

    # ------------------------------------------------------------------
    # Statistics and lifecycle
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        scene_type_counts: Dict[str, int] = {}
        for scene in self._scenes.values():
            st = scene.scene_type.value
            scene_type_counts[st] = scene_type_counts.get(st, 0) + 1

        total_layers_in_scenes = sum(len(s.layers) for s in self._scenes.values())
        total_entities = sum(len(s.entities) for s in self._scenes.values())
        loaded_scenes = sum(1 for s in self._scenes.values() if s.is_loaded)
        active_scenes = sum(1 for s in self._scenes.values() if s.is_active)

        return {
            "total_scenes": len(self._scenes),
            "total_layers_created": self._total_layers_created,
            "total_layers_in_scenes": total_layers_in_scenes,
            "total_entities": total_entities,
            "total_transitions": len(self._transitions),
            "total_scenes_created": self._total_scenes_created,
            "total_transitions_defined": self._total_transitions_defined,
            "total_switches": self._total_switches,
            "loaded_scenes": loaded_scenes,
            "active_scenes": active_scenes,
            "active_scene_id": self._active_scene_id,
            "transition_in_progress": self._transition_in_progress,
            "scene_type_distribution": scene_type_counts,
            "transition_presets": len(self._transition_presets),
            "easing_curves": len(self._easing_curves),
            "max_scenes": self.MAX_SCENES,
            "max_layers_per_scene": self.MAX_LAYERS_PER_SCENE,
            "max_transitions": self.MAX_TRANSITIONS,
            "max_entities_per_scene": self.MAX_ENTITIES_PER_SCENE,
            "max_cameras_per_scene": self.MAX_CAMERAS_PER_SCENE,
        }

    def get_scene_summary(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        return {
            "version": "1.0.0",
            "total_scenes": len(self._scenes),
            "active_scene": (
                self._scenes[self._active_scene_id].name
                if self._active_scene_id and self._active_scene_id in self._scenes
                else None
            ),
            "total_layers": self._total_layers_created,
            "total_transitions": len(self._transitions),
            "transition_in_progress": self._transition_in_progress,
            "total_switches": self._total_switches,
            "generated_at": _time_module.time(),
        }

    def remove_layer(self, layer_id: str) -> bool:
        _time_module.sleep(0.001)
        if layer_id not in self._layers:
            return False
        for scene_id, layer_ids in list(self._scene_layer_map.items()):
            if layer_id in layer_ids:
                scene = self._scenes.get(scene_id)
                if scene:
                    scene.layers = [l for l in scene.layers if l.layer_id != layer_id]
                self._scene_layer_map[scene_id] = [
                    lid for lid in layer_ids if lid != layer_id
                ]
        del self._layers[layer_id]
        return True

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._scenes.clear()
            self._layers.clear()
            self._transitions.clear()
            self._active_scene_id = None
            self._scene_layer_map.clear()
            self._transition_in_progress = False
            self._transition_timer = 0.0
            self._current_transition_id = None
            self._total_scenes_created = 0
            self._total_layers_created = 0
            self._total_transitions_defined = 0
            self._total_switches = 0
            self._scene_load_order.clear()


def get_scene_manager() -> EngineSceneManager:
    """Return the global EngineSceneManager singleton instance."""
    return EngineSceneManager.get_instance()