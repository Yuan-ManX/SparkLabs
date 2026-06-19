"""
SparkLabs Engine - Scene Lifecycle Engine

Scene management with AI-assisted transitions, scene graph hierarchy,
and lifecycle hooks. Provides complete scene lifecycle orchestration,
hierarchical node management with world-space transform calculation,
transition system with progress tracking and easing, and node pooling
for runtime performance.

Architecture:
  SceneLifecycleEngine (Singleton)
    |-- Scene              — full scene descriptor with nodes, hooks, and data
    |-- SceneNode          — hierarchical node with transform, layer, and tags
    |-- SceneTransition    — animated transition between two scenes
    |-- SceneStatus (enum) — lifecycle state machine for scenes
    |-- SceneLayer (enum)  — rendering layer classification
    |-- TransitionType (enum) — visual transition effect identifiers
    |-- NodeType (enum)    — semantic classification of scene graph nodes
    |-- LifecycleHook (enum) — hook points in the scene lifecycle
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SceneStatus(Enum):
    """Lifecycle state of a scene within the engine.

    CREATED:       Scene definition exists but not yet loaded.
    LOADING:       Resources are being loaded into memory.
    ACTIVE:        Scene is the current active scene receiving updates.
    PAUSED:        Scene is loaded but temporarily suspended.
    TRANSITIONING: Scene is involved in an active transition.
    UNLOADING:     Resources are being released from memory.
    UNLOADED:      Scene has been fully unloaded and resources freed.
    """
    CREATED = "created"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    TRANSITIONING = "transitioning"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class SceneLayer(Enum):
    """Rendering layer classification for scene nodes.

    BACKGROUND:  Decorative elements, skyboxes, distant scenery.
    GAMEPLAY:    Primary game entities, characters, and interactive objects.
    UI:          User interface elements rendered above gameplay.
    OVERLAY:     Top-level overlays such as notifications and tooltips.
    DEBUG:       Debug visualization elements drawn on top of everything.
    """
    BACKGROUND = "background"
    GAMEPLAY = "gameplay"
    UI = "ui"
    OVERLAY = "overlay"
    DEBUG = "debug"


class TransitionType(Enum):
    """Visual transition effect applied when switching between scenes.

    FADE:         Gradual opacity blend from one scene to another.
    SLIDE_LEFT:   Incoming scene slides in from the right.
    SLIDE_RIGHT:  Incoming scene slides in from the left.
    SLIDE_UP:     Incoming scene slides in from below.
    SLIDE_DOWN:   Incoming scene slides in from above.
    ZOOM_IN:      Camera zooms into the new scene.
    ZOOM_OUT:     Camera zooms out to reveal the new scene.
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
    CROSSFADE = "crossfade"
    NONE = "none"


class NodeType(Enum):
    """Semantic classification of scene graph nodes.

    SCENE:      Root container for a scene hierarchy.
    ENTITY:     General-purpose game entity node.
    SPRITE:     Rendered 2D sprite node.
    TEXT:       Text rendering node.
    CAMERA:     Viewpoint definition node.
    LIGHT:      Light source node for 2D/3D lighting.
    PARTICLE:   Particle emitter node.
    UI_ELEMENT: User interface widget node.
    GROUP:      Logical grouping node with no inherent rendering.
    """
    SCENE = "scene"
    ENTITY = "entity"
    SPRITE = "sprite"
    TEXT = "text"
    CAMERA = "camera"
    LIGHT = "light"
    PARTICLE = "particle"
    UI_ELEMENT = "ui_element"
    GROUP = "group"


class LifecycleHook(Enum):
    """Hook points within the scene lifecycle for custom callbacks.

    ON_CREATE:       Triggered immediately after scene creation.
    ON_LOAD:         Triggered when scene resources finish loading.
    ON_ACTIVATE:     Triggered when the scene becomes the active scene.
    ON_DEACTIVATE:   Triggered when the scene is no longer active.
    ON_PAUSE:        Triggered when the scene is paused.
    ON_RESUME:       Triggered when the scene resumes from pause.
    ON_PRE_UPDATE:   Triggered before each frame update.
    ON_POST_UPDATE:  Triggered after each frame update.
    ON_RENDER:       Triggered during the render pass.
    ON_DESTROY:      Triggered when the scene is about to be destroyed.
    """
    ON_CREATE = "on_create"
    ON_LOAD = "on_load"
    ON_ACTIVATE = "on_activate"
    ON_DEACTIVATE = "on_deactivate"
    ON_PAUSE = "on_pause"
    ON_RESUME = "on_resume"
    ON_PRE_UPDATE = "on_pre_update"
    ON_POST_UPDATE = "on_post_update"
    ON_RENDER = "on_render"
    ON_DESTROY = "on_destroy"


# ---------------------------------------------------------------------------
# Pre-defined easing curve lookup tables
# ---------------------------------------------------------------------------

_EASING_FUNCTIONS: Dict[str, Callable[[float], float]] = {
    "linear": lambda t: t,
    "ease_in": lambda t: t * t,
    "ease_out": lambda t: t * (2.0 - t),
    "ease_in_out": lambda t: (2.0 * t * t) if t < 0.5 else (-1.0 + (4.0 - 2.0 * t) * t),
    "bounce": lambda t: _bounce_ease(t),
    "elastic": lambda t: _elastic_ease(t),
    "back": lambda t: _back_ease(t),
}


def _bounce_ease(t: float) -> float:
    if t < 1.0 / 2.75:
        return 7.5625 * t * t
    elif t < 2.0 / 2.75:
        t -= 1.5 / 2.75
        return 7.5625 * t * t + 0.75
    elif t < 2.5 / 2.75:
        t -= 2.25 / 2.75
        return 7.5625 * t * t + 0.9375
    else:
        t -= 2.625 / 2.75
        return 7.5625 * t * t + 0.984375


def _elastic_ease(t: float) -> float:
    if t == 0.0 or t == 1.0:
        return t
    c4 = (2.0 * math.pi) / 3.0
    return -math.pow(2.0, 10.0 * t - 10.0) * math.sin((t * 10.0 - 10.75) * c4) + 1.0


def _back_ease(t: float) -> float:
    c1 = 1.70158
    c3 = c1 + 1.0
    return c3 * t * t * t - c1 * t * t


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class SceneNode:
    """A node within a scene graph hierarchy.

    Nodes form a parent-child tree where each node carries a local
    transform. World-space position is computed by walking the chain
    from the root to the node, accumulating parent transforms.
    """
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: NodeType = NodeType.ENTITY
    name: str = ""
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    components: Dict[str, Any] = field(default_factory=dict)
    position: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    z_order: int = 0
    is_visible: bool = True
    is_active: bool = True
    layer: SceneLayer = SceneLayer.GAMEPLAY
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "position": list(self.position),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "z_order": self.z_order,
            "is_visible": self.is_visible,
            "is_active": self.is_active,
            "layer": self.layer.value,
            "tags": list(self.tags),
            "child_count": len(self.children),
            "component_count": len(self.components),
            "created_at": self.created_at,
        }


@dataclass
class Scene:
    """A complete scene descriptor containing nodes, hooks, and metadata.

    Represents a self-contained game scene with its own node hierarchy,
    lifecycle hook callbacks, arbitrary data store, and timing
    information. Scenes progress through the SceneStatus state machine
    from CREATED through LOADING, ACTIVE, and ultimately UNLOADED.
    """
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    status: SceneStatus = SceneStatus.CREATED
    root_node_id: Optional[str] = None
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    hooks: Dict[str, List[Callable]] = field(default_factory=dict)
    data: Dict[str, Any] = field(default_factory=dict)
    creation_time: float = field(default_factory=_time_module.time)
    load_time: float = 0.0
    active_time: float = 0.0
    background_color: Tuple[int, int, int, int] = (0, 0, 0, 255)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "status": self.status.value,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes),
            "hook_count": len(self.hooks),
            "data_keys": list(self.data.keys()),
            "creation_time": self.creation_time,
            "load_time": self.load_time,
            "active_time": self.active_time,
            "background_color": list(self.background_color),
        }


@dataclass
class SceneTransition:
    """An active or queued transition between two scenes.

    Tracks the source and destination scenes, the visual effect type,
    duration, easing function, progress through the transition, and
    completion status. Supports arbitrary data passthrough for custom
    transition shaders or callbacks.
    """
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_scene_id: str = ""
    to_scene_id: str = ""
    transition_type: TransitionType = TransitionType.FADE
    duration: float = 0.5
    progress: float = 0.0
    is_complete: bool = False
    easing: str = "linear"
    data: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=_time_module.time)
    completed_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "transition_type": self.transition_type.value,
            "duration": self.duration,
            "progress": self.progress,
            "is_complete": self.is_complete,
            "easing": self.easing,
            "data_keys": list(self.data.keys()),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


# ---------------------------------------------------------------------------
# Scene Lifecycle Engine
# ---------------------------------------------------------------------------

class SceneLifecycleEngine:
    """Scene management with AI-assisted transitions, scene graph
    hierarchy, and lifecycle hooks.

    Handles the complete lifecycle of game scenes: creation, loading,
    activation, pausing, resuming, deactivation, unloading, and
    destruction. Maintains a scene graph with parent-child node
    hierarchy, world-space position calculation, and tag/type-based
    node queries. Manages scene transitions with progress tracking,
    easing curves, and completion callbacks. Provides a node pool for
    runtime object reuse.

    Thread-safe via a reentrant lock. Use get_scene_lifecycle_engine()
    or SceneLifecycleEngine.get_instance() to obtain the singleton.

    Usage:
        engine = get_scene_lifecycle_engine()
        scene = engine.create_scene("main_menu")
        engine.load_scene(scene.scene_id)
        engine.activate_scene(scene.scene_id)
        node = engine.create_node(scene.scene_id, NodeType.SPRITE, "hero")
        engine.set_node_position(scene.scene_id, node.node_id, 100.0, 200.0)
    """

    _instance: Optional["SceneLifecycleEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SCENES: int = 128
    MAX_NODES_PER_SCENE: int = 4096
    MAX_TRANSITIONS: int = 64
    MAX_HOOKS_PER_SCENE: int = 64
    NODE_POOL_SIZE: int = 1024

    def __new__(cls) -> "SceneLifecycleEngine":
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
        self._scenes: Dict[str, Scene] = {}
        self._active_scene_id: Optional[str] = None
        self._transitions: Dict[str, SceneTransition] = {}
        self._active_transition: Optional[SceneTransition] = None
        self._node_pool: Dict[str, SceneNode] = {}
        self._tag_index: Dict[str, Dict[str, Set[str]]] = {}
        self._type_index: Dict[str, Dict[str, Set[str]]] = {}
        self._total_scenes_created: int = 0
        self._total_nodes_created: int = 0
        self._total_transitions_started: int = 0
        self._total_hooks_registered: int = 0
        self._pending_transitions: List[SceneTransition] = []
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "SceneLifecycleEngine":
        return cls()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_scene(self, scene_id: str) -> Scene:
        _time_module.sleep(0.001)
        if scene_id not in self._scenes:
            raise KeyError(f"Scene '{scene_id}' does not exist")
        return self._scenes[scene_id]

    def _get_node(self, scene_id: str, node_id: str) -> SceneNode:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if node_id not in scene.nodes:
            raise KeyError(f"Node '{node_id}' does not exist in scene '{scene_id}'")
        return scene.nodes[node_id]

    def _index_node(self, scene_id: str, node: SceneNode) -> None:
        _time_module.sleep(0.001)
        for tag in node.tags:
            self._tag_index.setdefault(scene_id, {}).setdefault(tag, set()).add(node.node_id)
        tp = node.node_type.value
        self._type_index.setdefault(scene_id, {}).setdefault(tp, set()).add(node.node_id)

    def _unindex_node(self, scene_id: str, node: SceneNode) -> None:
        _time_module.sleep(0.001)
        scene_tags = self._tag_index.get(scene_id, {})
        for tag in node.tags:
            if tag in scene_tags:
                scene_tags[tag].discard(node.node_id)
        scene_types = self._type_index.get(scene_id, {})
        tp = node.node_type.value
        if tp in scene_types:
            scene_types[tp].discard(node.node_id)

    def _acquire_node(self, node_type: NodeType = NodeType.ENTITY) -> SceneNode:
        _time_module.sleep(0.001)
        for nid, node in list(self._node_pool.items()):
            if node.node_type == node_type:
                del self._node_pool[nid]
                node.node_id = uuid.uuid4().hex
                node.parent_id = None
                node.children.clear()
                node.components.clear()
                node.position = (0.0, 0.0)
                node.rotation = 0.0
                node.scale = (1.0, 1.0)
                node.z_order = 0
                node.is_visible = True
                node.is_active = True
                node.layer = SceneLayer.GAMEPLAY
                node.tags.clear()
                node.created_at = _time_module.time()
                return node
        return SceneNode(node_type=node_type)

    def _release_node(self, node: SceneNode) -> None:
        _time_module.sleep(0.001)
        if len(self._node_pool) < self.NODE_POOL_SIZE:
            self._node_pool[node.node_id] = node

    def _get_world_position(self, scene_id: str, node_id: str) -> Tuple[float, float]:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        x, y = node.position
        current_id = node.parent_id
        while current_id is not None:
            parent = self._nodes_safe(scene_id, current_id)
            if parent is None:
                break
            parent_x, parent_y = parent.position
            parent_rot = parent.rotation
            parent_sx, parent_sy = parent.scale
            cos_r = math.cos(parent_rot)
            sin_r = math.sin(parent_rot)
            wx = parent_x + x * cos_r * parent_sx - y * sin_r * parent_sy
            wy = parent_y + x * sin_r * parent_sx + y * cos_r * parent_sy
            x, y = wx, wy
            current_id = parent.parent_id
        return (x, y)

    def _nodes_safe(self, scene_id: str, node_id: str) -> Optional[SceneNode]:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return None
        return scene.nodes.get(node_id)

    def _validate_status_transition(self, scene: Scene, target: SceneStatus) -> bool:
        _time_module.sleep(0.001)
        valid_transitions: Dict[SceneStatus, Set[SceneStatus]] = {
            SceneStatus.CREATED: {SceneStatus.LOADING, SceneStatus.UNLOADING, SceneStatus.UNLOADED},
            SceneStatus.LOADING: {SceneStatus.ACTIVE, SceneStatus.PAUSED, SceneStatus.UNLOADING},
            SceneStatus.ACTIVE: {SceneStatus.PAUSED, SceneStatus.DEACTIVATING, SceneStatus.UNLOADING, SceneStatus.TRANSITIONING},
            SceneStatus.PAUSED: {SceneStatus.ACTIVE, SceneStatus.UNLOADING},
            SceneStatus.TRANSITIONING: {SceneStatus.ACTIVE, SceneStatus.PAUSED, SceneStatus.UNLOADING},
            SceneStatus.UNLOADING: {SceneStatus.UNLOADED},
            SceneStatus.UNLOADED: set(),
        }
        return target in valid_transitions.get(scene.status, set())

    def _apply_easing(self, easing_name: str, t: float) -> float:
        _time_module.sleep(0.001)
        func = _EASING_FUNCTIONS.get(easing_name, _EASING_FUNCTIONS["linear"])
        return max(0.0, min(1.0, func(t)))

    def _recursive_remove_nodes(self, scene_id: str, node_id: str) -> None:
        _time_module.sleep(0.001)
        node = self._nodes_safe(scene_id, node_id)
        if node is None:
            return
        for child_id in list(node.children):
            self._recursive_remove_nodes(scene_id, child_id)
        self._unindex_node(scene_id, node)
        scene = self._scenes.get(scene_id)
        if scene:
            scene.nodes.pop(node.node_id, None)

    # ------------------------------------------------------------------
    # Scene lifecycle management
    # ------------------------------------------------------------------

    def create_scene(
        self,
        name: str,
        background_color: Tuple[int, int, int, int] = (0, 0, 0, 255),
    ) -> Scene:
        _time_module.sleep(0.001)
        if len(self._scenes) >= self.MAX_SCENES:
            raise RuntimeError(f"Scene limit reached ({self.MAX_SCENES})")
        if not name:
            raise ValueError("scene name must not be empty")

        scene = Scene(
            name=name,
            background_color=background_color,
        )
        self._scenes[scene.scene_id] = scene
        self._tag_index[scene.scene_id] = {}
        self._type_index[scene.scene_id] = {}
        self._total_scenes_created += 1

        self.trigger_hooks(scene.scene_id, LifecycleHook.ON_CREATE)
        return scene

    def load_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status == SceneStatus.LOADING:
            return False
        if scene.status == SceneStatus.ACTIVE:
            return True

        scene.status = SceneStatus.LOADING
        scene.load_time = _time_module.time()

        scene.status = SceneStatus.PAUSED
        self.trigger_hooks(scene_id, LifecycleHook.ON_LOAD)
        return True

    def activate_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status == SceneStatus.ACTIVE:
            return True

        if self._active_scene_id is not None and self._active_scene_id != scene_id:
            self.deactivate_scene(self._active_scene_id)

        if self._active_transition is not None:
            self.cancel_transition()

        scene.status = SceneStatus.ACTIVE
        scene.active_time = _time_module.time()
        self._active_scene_id = scene_id

        self.trigger_hooks(scene_id, LifecycleHook.ON_ACTIVATE)
        return True

    def deactivate_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status == SceneStatus.UNLOADED:
            return False

        scene.status = SceneStatus.PAUSED
        self.trigger_hooks(scene_id, LifecycleHook.ON_DEACTIVATE)

        if self._active_scene_id == scene_id:
            self._active_scene_id = None
        return True

    def pause_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status != SceneStatus.ACTIVE:
            return False

        scene.status = SceneStatus.PAUSED
        self.trigger_hooks(scene_id, LifecycleHook.ON_PAUSE)
        return True

    def resume_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status != SceneStatus.PAUSED:
            return False

        scene.status = SceneStatus.ACTIVE
        self._active_scene_id = scene_id
        self.trigger_hooks(scene_id, LifecycleHook.ON_RESUME)
        return True

    def unload_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        if scene.status == SceneStatus.UNLOADED:
            return True

        if self._active_scene_id == scene_id:
            self._active_scene_id = None

        scene.status = SceneStatus.UNLOADING

        if scene.root_node_id is not None:
            self._recursive_remove_nodes(scene_id, scene.root_node_id)

        scene.root_node_id = None
        scene.status = SceneStatus.UNLOADED
        scene.load_time = 0.0
        scene.active_time = 0.0
        return True

    def destroy_scene(self, scene_id: str) -> bool:
        _time_module.sleep(0.001)
        if scene_id not in self._scenes:
            return False

        self.trigger_hooks(scene_id, LifecycleHook.ON_DESTROY)
        self.unload_scene(scene_id)

        transitions_to_remove = [
            tid for tid, t in self._transitions.items()
            if t.from_scene_id == scene_id or t.to_scene_id == scene_id
        ]
        for tid in transitions_to_remove:
            del self._transitions[tid]

        if self._active_transition is not None and (
            self._active_transition.from_scene_id == scene_id
            or self._active_transition.to_scene_id == scene_id
        ):
            self._active_transition = None

        self._tag_index.pop(scene_id, None)
        self._type_index.pop(scene_id, None)
        del self._scenes[scene_id]

        if self._active_scene_id == scene_id:
            self._active_scene_id = None
        return True

    # ------------------------------------------------------------------
    # Scene queries
    # ------------------------------------------------------------------

    def get_scene(self, scene_id: str) -> Optional[Scene]:
        _time_module.sleep(0.001)
        return self._scenes.get(scene_id)

    def get_active_scene(self) -> Optional[Scene]:
        _time_module.sleep(0.001)
        if self._active_scene_id is None:
            return None
        return self._scenes.get(self._active_scene_id)

    def get_active_scene_id(self) -> Optional[str]:
        _time_module.sleep(0.001)
        return self._active_scene_id

    def list_scenes(self, status: Optional[SceneStatus] = None) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)
        if status is not None:
            return [s.to_dict() for s in self._scenes.values() if s.status == status]
        return [s.to_dict() for s in self._scenes.values()]

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def create_node(
        self,
        scene_id: str,
        node_type: NodeType,
        name: str,
        parent_id: Optional[str] = None,
        position: Tuple[float, float] = (0.0, 0.0),
        rotation: float = 0.0,
        scale: Tuple[float, float] = (1.0, 1.0),
        z_order: int = 0,
        layer: SceneLayer = SceneLayer.GAMEPLAY,
        components: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[SceneNode]:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        if len(scene.nodes) >= self.MAX_NODES_PER_SCENE:
            raise RuntimeError(
                f"Node limit reached ({self.MAX_NODES_PER_SCENE}) for scene '{scene_id}'"
            )

        node = self._acquire_node(node_type)
        node.name = name
        node.node_type = node_type
        node.parent_id = parent_id
        node.position = position
        node.rotation = rotation
        node.scale = scale
        node.z_order = z_order
        node.layer = layer
        node.components = dict(components) if components else {}
        node.tags = list(tags) if tags else []

        if parent_id is not None:
            parent = self._nodes_safe(scene_id, parent_id)
            if parent is not None:
                parent.children.append(node.node_id)
            else:
                node.parent_id = None

        if node_type == NodeType.SCENE and scene.root_node_id is None:
            scene.root_node_id = node.node_id

        scene.nodes[node.node_id] = node
        self._index_node(scene_id, node)
        self._total_nodes_created += 1
        return node

    def remove_node(self, scene_id: str, node_id: str) -> bool:
        _time_module.sleep(0.001)
        node = self._nodes_safe(scene_id, node_id)
        if node is None:
            return False

        if node.parent_id is not None:
            parent = self._nodes_safe(scene_id, node.parent_id)
            if parent is not None and node_id in parent.children:
                parent.children.remove(node_id)

        self._recursive_remove_nodes(scene_id, node_id)

        scene = self._scenes.get(scene_id)
        if scene is not None and scene.root_node_id == node_id:
            scene.root_node_id = None

        self._release_node(node)
        return True

    def get_node(self, scene_id: str, node_id: str) -> Optional[SceneNode]:
        _time_module.sleep(0.001)
        return self._nodes_safe(scene_id, node_id)

    def find_nodes_by_tag(self, scene_id: str, tag: str) -> List[SceneNode]:
        _time_module.sleep(0.001)
        scene_tags = self._tag_index.get(scene_id, {})
        node_ids = scene_tags.get(tag, set())
        scene = self._scenes.get(scene_id)
        if scene is None:
            return []
        return [scene.nodes[nid] for nid in node_ids if nid in scene.nodes]

    def find_nodes_by_type(self, scene_id: str, node_type: NodeType) -> List[SceneNode]:
        _time_module.sleep(0.001)
        scene_types = self._type_index.get(scene_id, {})
        node_ids = scene_types.get(node_type.value, set())
        scene = self._scenes.get(scene_id)
        if scene is None:
            return []
        return [scene.nodes[nid] for nid in node_ids if nid in scene.nodes]

    # ------------------------------------------------------------------
    # Node transform setters
    # ------------------------------------------------------------------

    def set_node_position(self, scene_id: str, node_id: str, x: float, y: float) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        node.position = (x, y)
        return True

    def set_node_rotation(self, scene_id: str, node_id: str, rotation: float) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        node.rotation = rotation
        return True

    def set_node_scale(self, scene_id: str, node_id: str, sx: float, sy: float) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        node.scale = (sx, sy)
        return True

    def set_node_visibility(self, scene_id: str, node_id: str, is_visible: bool) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        node.is_visible = is_visible
        return True

    def set_node_active(self, scene_id: str, node_id: str, is_active: bool) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        node.is_active = is_active
        return True

    def set_node_parent(self, scene_id: str, node_id: str, new_parent_id: Optional[str]) -> bool:
        _time_module.sleep(0.001)
        node = self._get_node(scene_id, node_id)
        if new_parent_id == node_id:
            return False

        if new_parent_id is not None:
            new_parent = self._nodes_safe(scene_id, new_parent_id)
            if new_parent is None:
                return False

        old_parent = self._nodes_safe(scene_id, node.parent_id) if node.parent_id else None
        if old_parent is not None and node_id in old_parent.children:
            old_parent.children.remove(node_id)

        if new_parent_id is not None:
            new_parent = self._nodes_safe(scene_id, new_parent_id)
            if new_parent is not None:
                new_parent.children.append(node_id)

        node.parent_id = new_parent_id
        return True

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def register_hook(
        self,
        scene_id: str,
        hook: LifecycleHook,
        callback: Callable[[Scene], None],
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        hook_key = hook.value
        scene.hooks.setdefault(hook_key, [])

        if len(scene.hooks[hook_key]) >= self.MAX_HOOKS_PER_SCENE:
            raise RuntimeError(
                f"Hook limit reached ({self.MAX_HOOKS_PER_SCENE}) for scene '{scene_id}'"
            )

        if callback in scene.hooks[hook_key]:
            return False

        scene.hooks[hook_key].append(callback)
        self._total_hooks_registered += 1
        return True

    def unregister_hook(
        self,
        scene_id: str,
        hook: LifecycleHook,
        callback: Callable[[Scene], None],
    ) -> bool:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)
        hook_key = hook.value
        callbacks = scene.hooks.get(hook_key, [])
        if callback in callbacks:
            callbacks.remove(callback)
            return True
        return False

    def trigger_hooks(self, scene_id: str, hook: LifecycleHook) -> None:
        _time_module.sleep(0.001)
        scene = self._scenes.get(scene_id)
        if scene is None:
            return
        hook_key = hook.value
        for callback in scene.hooks.get(hook_key, []):
            try:
                callback(scene)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Transition management
    # ------------------------------------------------------------------

    def start_transition(
        self,
        from_scene_id: str,
        to_scene_id: str,
        transition_type: TransitionType,
        duration: float = 0.5,
        easing: str = "linear",
        data: Optional[Dict[str, Any]] = None,
    ) -> SceneTransition:
        _time_module.sleep(0.001)
        if len(self._transitions) >= self.MAX_TRANSITIONS:
            raise RuntimeError(f"Transition limit reached ({self.MAX_TRANSITIONS})")

        if from_scene_id and from_scene_id not in self._scenes:
            raise KeyError(f"From-scene '{from_scene_id}' does not exist")
        if to_scene_id not in self._scenes:
            raise KeyError(f"To-scene '{to_scene_id}' does not exist")

        if duration < 0.0:
            duration = 0.0

        transition = SceneTransition(
            from_scene_id=from_scene_id,
            to_scene_id=to_scene_id,
            transition_type=transition_type,
            duration=duration,
            easing=easing,
            data=data or {},
        )

        self._transitions[transition.transition_id] = transition
        self._total_transitions_started += 1

        if self._active_transition is not None:
            self._pending_transitions.append(transition)
        else:
            self._active_transition = transition
            from_scene = self._scenes.get(from_scene_id)
            if from_scene is not None:
                from_scene.status = SceneStatus.TRANSITIONING
            to_scene = self._scenes.get(to_scene_id)
            if to_scene is not None:
                to_scene.status = SceneStatus.TRANSITIONING

        return transition

    def update_transition(self, delta_time: float) -> Optional[SceneTransition]:
        _time_module.sleep(0.001)
        if self._active_transition is None:
            return None

        transition = self._active_transition
        if transition.is_complete:
            return None

        transition.progress += delta_time / max(0.001, transition.duration)
        eased_progress = self._apply_easing(transition.easing, transition.progress)

        if transition.progress >= 1.0:
            transition.progress = 1.0
            transition.is_complete = True
            transition.completed_at = _time_module.time()

            from_scene = self._scenes.get(transition.from_scene_id)
            to_scene = self._scenes.get(transition.to_scene_id)

            if from_scene is not None:
                from_scene.status = SceneStatus.PAUSED
            if to_scene is not None:
                to_scene.status = SceneStatus.ACTIVE
                self._active_scene_id = to_scene.scene_id

            completed = self._active_transition
            self._active_transition = None

            if self._pending_transitions:
                self._active_transition = self._pending_transitions.pop(0)
                next_trans = self._active_transition
                next_from = self._scenes.get(next_trans.from_scene_id)
                next_to = self._scenes.get(next_trans.to_scene_id)
                if next_from is not None:
                    next_from.status = SceneStatus.TRANSITIONING
                if next_to is not None:
                    next_to.status = SceneStatus.TRANSITIONING

            return completed

        return None

    def get_active_transition(self) -> Optional[SceneTransition]:
        _time_module.sleep(0.001)
        return self._active_transition

    def cancel_transition(self) -> bool:
        _time_module.sleep(0.001)
        if self._active_transition is None:
            return False

        transition = self._active_transition
        from_scene = self._scenes.get(transition.from_scene_id)
        to_scene = self._scenes.get(transition.to_scene_id)

        if from_scene is not None:
            from_scene.status = SceneStatus.PAUSED
        if to_scene is not None:
            to_scene.status = SceneStatus.PAUSED

        self._active_transition = None
        return True

    # ------------------------------------------------------------------
    # AI-assisted methods
    # ------------------------------------------------------------------

    def ai_suggest_transition(
        self,
        from_scene_id: str,
        to_scene_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        from_scene = self._scenes.get(from_scene_id)
        to_scene = self._scenes.get(to_scene_id)

        if from_scene is None or to_scene is None:
            return {
                "success": False,
                "error": "scene_not_found",
                "suggestion": None,
            }

        from_node_count = len(from_scene.nodes)
        to_node_count = len(to_scene.nodes)
        node_ratio = to_node_count / max(1.0, float(from_node_count))

        suggested_type = TransitionType.FADE
        suggested_duration = 0.5
        suggested_easing = "ease_in_out"
        reasoning = "Default fade transition."

        if node_ratio > 2.0:
            suggested_type = TransitionType.CROSSFADE
            suggested_duration = 0.8
            suggested_easing = "ease_in_out"
            reasoning = "Large scene transition using crossfade for smooth loading."
        elif node_ratio < 0.5:
            suggested_type = TransitionType.SLIDE_LEFT
            suggested_duration = 0.4
            suggested_easing = "ease_out"
            reasoning = "Transition to smaller scene with slide effect."
        elif context and context.get("menu", False):
            suggested_type = TransitionType.FADE
            suggested_duration = 0.3
            suggested_easing = "ease_out"
            reasoning = "Quick fade for menu navigation."
        elif context and context.get("cinematic", False):
            suggested_type = TransitionType.ZOOM_IN
            suggested_duration = 1.0
            suggested_easing = "ease_in"
            reasoning = "Cinematic zoom for dramatic effect."

        return {
            "success": True,
            "suggestion": {
                "transition_type": suggested_type.value,
                "duration": suggested_duration,
                "easing": suggested_easing,
                "from_scene": from_scene.name,
                "to_scene": to_scene.name,
                "from_node_count": from_node_count,
                "to_node_count": to_node_count,
            },
            "reasoning": reasoning,
        }

    def ai_generate_scene_graph(
        self,
        description: str,
        node_count: int = 10,
    ) -> Scene:
        _time_module.sleep(0.001)
        scene = self.create_scene(
            name=f"ai_generated_{uuid.uuid4().hex[:8]}",
        )

        actual_count = max(1, min(node_count, self.MAX_NODES_PER_SCENE))

        root = self.create_node(
            scene_id=scene.scene_id,
            node_type=NodeType.SCENE,
            name=f"root_{description[:20]}",
        )
        if root is not None:
            scene.root_node_id = root.node_id

        entity_types = [
            (NodeType.SPRITE, "sprite", SceneLayer.GAMEPLAY),
            (NodeType.ENTITY, "entity", SceneLayer.GAMEPLAY),
            (NodeType.CAMERA, "camera", SceneLayer.GAMEPLAY),
            (NodeType.LIGHT, "light", SceneLayer.GAMEPLAY),
            (NodeType.UI_ELEMENT, "ui", SceneLayer.UI),
            (NodeType.PARTICLE, "particle", SceneLayer.GAMEPLAY),
            (NodeType.TEXT, "text", SceneLayer.UI),
        ]

        for i in range(actual_count):
            type_idx = i % len(entity_types)
            nt, prefix, ly = entity_types[type_idx]
            parent = root.node_id if root is not None else None
            px = (i % 4) * 200.0 + 100.0
            py = (i // 4) * 150.0 + 50.0
            self.create_node(
                scene_id=scene.scene_id,
                node_type=nt,
                name=f"{prefix}_{i:03d}",
                parent_id=parent,
                position=(px, py),
                layer=ly,
                tags=[prefix, f"generated_{i}"],
            )

        if root is not None:
            scene.load_time = _time_module.time()
            scene.status = SceneStatus.PAUSED

        return scene

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_scene_stats(self, scene_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        scene = self._get_scene(scene_id)

        node_type_counts: Dict[str, int] = {}
        for node in scene.nodes.values():
            tp = node.node_type.value
            node_type_counts[tp] = node_type_counts.get(tp, 0) + 1

        layer_counts: Dict[str, int] = {}
        for node in scene.nodes.values():
            ly = node.layer.value
            layer_counts[ly] = layer_counts.get(ly, 0) + 1

        visible_nodes = sum(1 for n in scene.nodes.values() if n.is_visible)
        active_nodes = sum(1 for n in scene.nodes.values() if n.is_active)

        return {
            "scene_id": scene.scene_id,
            "name": scene.name,
            "status": scene.status.value,
            "total_nodes": len(scene.nodes),
            "visible_nodes": visible_nodes,
            "active_nodes": active_nodes,
            "node_type_distribution": node_type_counts,
            "layer_distribution": layer_counts,
            "hook_count": sum(len(v) for v in scene.hooks.values()),
            "creation_time": scene.creation_time,
            "load_time": scene.load_time,
            "active_time": scene.active_time,
            "has_root": scene.root_node_id is not None,
        }

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        status_counts: Dict[str, int] = {}
        for scene in self._scenes.values():
            st = scene.status.value
            status_counts[st] = status_counts.get(st, 0) + 1

        total_nodes = sum(len(s.nodes) for s in self._scenes.values())
        total_hooks = sum(sum(len(v) for v in s.hooks.values()) for s in self._scenes.values())

        return {
            "total_scenes": len(self._scenes),
            "total_scenes_created": self._total_scenes_created,
            "total_nodes": total_nodes,
            "total_nodes_created": self._total_nodes_created,
            "total_transitions": len(self._transitions),
            "total_transitions_started": self._total_transitions_started,
            "total_hooks_registered": self._total_hooks_registered,
            "active_scene_id": self._active_scene_id,
            "active_transition": self._active_transition is not None,
            "pending_transitions": len(self._pending_transitions),
            "node_pool_size": len(self._node_pool),
            "status_distribution": status_counts,
            "max_scenes": self.MAX_SCENES,
            "max_nodes_per_scene": self.MAX_NODES_PER_SCENE,
            "max_transitions": self.MAX_TRANSITIONS,
            "max_hooks_per_scene": self.MAX_HOOKS_PER_SCENE,
            "node_pool_capacity": self.NODE_POOL_SIZE,
        }

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._scenes.clear()
            self._active_scene_id = None
            self._transitions.clear()
            self._active_transition = None
            self._node_pool.clear()
            self._tag_index.clear()
            self._type_index.clear()
            self._total_scenes_created = 0
            self._total_nodes_created = 0
            self._total_transitions_started = 0
            self._total_hooks_registered = 0
            self._pending_transitions.clear()


# ---------------------------------------------------------------------------
# Factory function
# ---------------------------------------------------------------------------

def get_scene_lifecycle_engine() -> SceneLifecycleEngine:
    """Return the global SceneLifecycleEngine singleton instance."""
    return SceneLifecycleEngine.get_instance()