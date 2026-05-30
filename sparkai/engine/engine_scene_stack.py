"""
SparkLabs Engine - Scene Stack

A singleton scene management system for the SparkLabs game engine.
Provides hierarchical scene loading, unloading, persistence,
transition effects, and a scene stack for overlay/popup navigation.
Supports async scene streaming for seamless level transitions.

Architecture:
  SceneStack (singleton)
    |-- SceneNode (individual scene with entity tree and state)
    |-- SceneTransition (crossfade, wipe, zoom transition config)
    |-- SceneSnapshot (serializable scene state for save/load)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


_time_module = time


class SceneState(Enum):
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    BACKGROUND = "background"
    UNLOADING = "unloading"


class TransitionType(Enum):
    NONE = "none"
    FADE = "fade"
    CROSSFADE = "crossfade"
    WIPE_LEFT = "wipe_left"
    WIPE_RIGHT = "wipe_right"
    WIPE_UP = "wipe_up"
    WIPE_DOWN = "wipe_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"


class SceneLayer(Enum):
    BASE = "base"
    OVERLAY = "overlay"
    POPUP = "popup"
    HUD = "hud"
    SYSTEM = "system"
    LOADING_SCREEN = "loading_screen"


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class SceneTransition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    transition_type: TransitionType = TransitionType.FADE
    duration: float = 0.5
    easing: str = "ease_in_out"
    overlay_color: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])
    custom_curve: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "easing": self.easing,
            "overlay_color": list(self.overlay_color),
        }


@dataclass
class SceneSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scene_name: str = ""
    entity_states: Dict[str, Any] = field(default_factory=dict)
    camera_position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    camera_rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    timestamp: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "scene_name": self.scene_name,
            "entity_count": len(self.entity_states),
            "camera_position": list(self.camera_position),
            "camera_rotation": list(self.camera_rotation),
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass
class SceneNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    state: SceneState = SceneState.UNLOADED
    layer: SceneLayer = SceneLayer.BASE
    load_priority: int = 0
    entity_ids: List[str] = field(default_factory=list)
    transition: Optional[SceneTransition] = None
    duration_loaded: float = 0.0
    parent_scene: Optional[str] = None
    child_scenes: List[str] = field(default_factory=list)
    snapshot: Optional[SceneSnapshot] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "layer": self.layer.value,
            "load_priority": self.load_priority,
            "entity_count": len(self.entity_ids),
            "transition": self.transition.to_dict() if self.transition else None,
            "duration_loaded": self.duration_loaded,
            "parent_scene": self.parent_scene,
            "child_scenes": list(self.child_scenes),
            "metadata": dict(self.metadata),
        }


# ------------------------------------------------------------------
# Singleton
# ------------------------------------------------------------------

SCENE_LOAD_TIMEOUT: float = 30.0
TRANSITION_DEFAULT_DURATION: float = 0.5


class SceneStack:
    """Hierarchical scene management with transitions and persistence.

    Maintains a stack of active scenes with overlay/popup layering.
    Supports async loading, save/restore via snapshots, transition
    effects, and parent-child scene relationships for nested level
    structures.
    """

    _instance: Optional[SceneStack] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> SceneStack:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> SceneStack:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._scenes: Dict[str, SceneNode] = {}
        self._active_scene: Optional[str] = None
        self._transition_in_progress: bool = False
        self._transition_progress: float = 0.0
        self._snapshots: List[SceneSnapshot] = []
        self._transitions: List[SceneTransition] = []
        self._loading_queue: List[str] = []
        self._override_scenes: Dict[str, Callable] = {}
        self._initialize_default_transitions()

    def _get_or_create_singleton(self) -> SceneStack:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_scenes = len(self._scenes)
        active_count = sum(
            1 for s in self._scenes.values() if s.state == SceneState.ACTIVE
        )
        return {
            "total_scenes": total_scenes,
            "active_scenes": active_count,
            "snapshots": len(self._snapshots),
            "transitions": len(self._transitions),
            "transition_in_progress": self._transition_in_progress,
            "active_scene": self._active_scene,
            "loading_queue": len(self._loading_queue),
        }

    # --- Scene Operations ---

    def register_scene(
        self,
        name: str,
        layer: str = "base",
        load_priority: int = 0,
    ) -> SceneNode:
        if name in self._scenes:
            return self._scenes[name]

        node = SceneNode(
            name=name,
            layer=SceneLayer(layer),
            load_priority=load_priority,
        )
        self._scenes[name] = node
        return node

    def load_scene(
        self,
        name: str,
        transition_type: str = "fade",
        transition_duration: float = TRANSITION_DEFAULT_DURATION,
    ) -> SceneNode:
        if name not in self._scenes:
            self.register_scene(name)

        node = self._scenes[name]
        node.state = SceneState.LOADING
        self._loading_queue.append(name)

        transition = SceneTransition(
            transition_type=TransitionType(transition_type),
            duration=transition_duration,
        )
        node.transition = transition

        previous_active = self._active_scene
        if previous_active and previous_active in self._scenes:
            prev_node = self._scenes[previous_active]
            if prev_node.layer == SceneLayer.BASE:
                prev_node.state = SceneState.BACKGROUND

        node.state = SceneState.ACTIVE
        node.duration_loaded = 0.0
        self._active_scene = name

        self._transition_in_progress = True
        self._transition_progress = 0.0

        if name in self._loading_queue:
            self._loading_queue.remove(name)

        return node

    def unload_scene(self, name: str) -> bool:
        if name not in self._scenes:
            return False

        node = self._scenes[name]
        node.state = SceneState.UNLOADING
        self._save_snapshot(name)
        node.state = SceneState.UNLOADED

        if self._active_scene == name:
            self._active_scene = None

        del self._scenes[name]
        return True

    def pause_scene(self, name: str) -> bool:
        if name not in self._scenes:
            return False
        node = self._scenes[name]
        if node.state == SceneState.ACTIVE:
            node.state = SceneState.PAUSED
        return True

    def resume_scene(self, name: str) -> bool:
        if name not in self._scenes:
            return False
        node = self._scenes[name]
        if node.state == SceneState.PAUSED:
            node.state = SceneState.ACTIVE
            self._active_scene = name
        return True

    def get_scene(self, name: str) -> Optional[SceneNode]:
        return self._scenes.get(name)

    def get_active_scene(self) -> Optional[SceneNode]:
        if self._active_scene:
            return self._scenes.get(self._active_scene)
        return None

    def list_scenes(self) -> List[SceneNode]:
        return list(self._scenes.values())

    # --- Transition Operations ---

    def create_transition(
        self,
        transition_type: str = "fade",
        duration: float = TRANSITION_DEFAULT_DURATION,
        easing: str = "ease_in_out",
    ) -> SceneTransition:
        transition = SceneTransition(
            transition_type=TransitionType(transition_type),
            duration=duration,
            easing=easing,
        )
        self._transitions.append(transition)
        return transition

    def update_transition(self, delta_time: float) -> Dict[str, Any]:
        if not self._transition_in_progress:
            return {"in_progress": False, "progress": 1.0}

        node = self.get_active_scene()
        if not node or not node.transition:
            self._transition_in_progress = False
            return {"in_progress": False, "progress": 1.0}

        self._transition_progress += delta_time / max(0.001, node.transition.duration)
        self._transition_progress = min(1.0, self._transition_progress)

        if self._transition_progress >= 1.0:
            self._transition_in_progress = False
            self._transition_progress = 1.0

        return {
            "in_progress": self._transition_in_progress,
            "progress": self._transition_progress,
            "transition_type": node.transition.transition_type.value,
        }

    def is_transitioning(self) -> bool:
        return self._transition_in_progress

    # --- Snapshot Operations ---

    def save_snapshot(self, scene_name: str) -> Optional[SceneSnapshot]:
        if scene_name not in self._scenes:
            return None

        snapshot = SceneSnapshot(
            scene_name=scene_name,
            camera_position=[0.0, 0.0, 0.0],
        )
        self._snapshots.append(snapshot)
        self._scenes[scene_name].snapshot = snapshot
        return snapshot

    def restore_snapshot(self, snapshot_id: str) -> Optional[SceneSnapshot]:
        for snap in self._snapshots:
            if snap.id == snapshot_id:
                if snap.scene_name not in self._scenes:
                    self.register_scene(snap.scene_name)
                self._scenes[snap.scene_name].snapshot = snap
                return snap
        return None

    def list_snapshots(self) -> List[SceneSnapshot]:
        return list(self._snapshots)

    # --- Layer Operations ---

    def push_overlay(
        self,
        name: str,
        transition_type: str = "fade",
    ) -> Optional[SceneNode]:
        node = self.register_scene(name, layer="overlay")
        node.parent_scene = self._active_scene
        if self._active_scene and self._active_scene in self._scenes:
            self._scenes[self._active_scene].child_scenes.append(name)

        node.state = SceneState.ACTIVE
        node.transition = SceneTransition(
            transition_type=TransitionType(transition_type),
            duration=TRANSITION_DEFAULT_DURATION,
        )
        return node

    def pop_overlay(self, name: str) -> bool:
        if name not in self._scenes:
            return False

        node = self._scenes[name]
        if node.layer == SceneLayer.BASE:
            return False

        if node.parent_scene and node.parent_scene in self._scenes:
            parent = self._scenes[node.parent_scene]
            parent.child_scenes = [c for c in parent.child_scenes if c != name]

        self.unload_scene(name)
        return True

    # --- Query ---

    def find_scenes_by_layer(self, layer: str) -> List[SceneNode]:
        target = SceneLayer(layer)
        return [s for s in self._scenes.values() if s.layer == target]

    def find_scenes_by_state(self, state: str) -> List[SceneNode]:
        target = SceneState(state)
        return [s for s in self._scenes.values() if s.state == target]

    # --- Internal ---

    def _save_snapshot(self, scene_name: str) -> None:
        self.save_snapshot(scene_name)

    def _initialize_default_transitions(self) -> None:
        defaults: List[Tuple[str, float, str]] = [
            ("fade", 0.5, "ease_in_out"),
            ("crossfade", 0.8, "ease_in_out"),
            ("wipe_left", 0.6, "ease_out"),
            ("zoom_in", 0.4, "ease_in"),
        ]
        for t_type, duration, easing in defaults:
            transition = SceneTransition(
                transition_type=TransitionType(t_type),
                duration=duration,
                easing=easing,
            )
            self._transitions.append(transition)


def get_scene_stack() -> SceneStack:
    return SceneStack.get_instance()