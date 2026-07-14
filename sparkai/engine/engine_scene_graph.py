"""
SparkLabs Engine - Hierarchical Scene Graph

Node-based scene hierarchy with parent-child transform relationships,
supporting both 2D and 3D scenes. Provides the structural backbone for
AI-generated game worlds.

Architecture:
  SceneGraphSystem
    |-- SceneNode (transform, bounds, components, layer)
    |-- NodeTransform (local + cached world transform)
    |-- Component (mesh, light, camera, collider, particle, audio, ...)
    |-- Scene (named collection of nodes with a root)
    |-- Prefab (reusable scene template)
    |-- BoundingVolume (AABB with tree propagation)
    |-- Layer (visibility + collision filtering)
    |-- SignalHandler (node and scene level events)

Usage:
    sgs = SceneGraphSystem()
    sgs.initialize()
    root = sgs.create_node("Root", NodeType.ROOT)
    player = sgs.create_node("Player", NodeType.MESH, parent_id=root)
    sgs.set_local_transform(player, position=(0.0, 0.0, 5.0))
    sgs.tick(0.016)
    visible = sgs.frustum_cull(frustum_planes)
"""
from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Deque, Dict, Iterable, List, Optional, Set, Tuple
def _uid() -> str:
    return uuid.uuid4().hex[:12]

def _now_ts() -> float:
    return time.time()

def _clamp(value: float, low: float, high: float) -> float:
    return low if value < low else (high if value > high else value)


Vec3 = Tuple[float, float, float]
Quat = Tuple[float, float, float, float]
def _vadd(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

def _vsub(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

def _vscale(a: Vec3, s: float) -> Vec3:
    return (a[0] * s, a[1] * s, a[2] * s)

def _vmul(a: Vec3, b: Vec3) -> Vec3:
    return (a[0] * b[0], a[1] * b[1], a[2] * b[2])

def _vcross(a: Vec3, b: Vec3) -> Vec3:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

def _qnorm(q: Quat) -> Quat:
    n = math.sqrt(q[0] * q[0] + q[1] * q[1] + q[2] * q[2] + q[3] * q[3])
    return (q[0] / n, q[1] / n, q[2] / n, q[3] / n) if n >= 1e-9 else (0.0, 0.0, 0.0, 1.0)

def _qmul(a: Quat, b: Quat) -> Quat:
    # Hamilton product a * b
    x = a[3] * b[0] + a[0] * b[3] + a[1] * b[2] - a[2] * b[1]
    y = a[3] * b[1] - a[0] * b[2] + a[1] * b[3] + a[2] * b[0]
    z = a[3] * b[2] + a[0] * b[1] - a[1] * b[0] + a[2] * b[3]
    w = a[3] * b[3] - a[0] * b[0] - a[1] * b[1] - a[2] * b[2]
    return _qnorm((x, y, z, w))

def _qconj(q: Quat) -> Quat:
    return (-q[0], -q[1], -q[2], q[3])

def _euler_to_quat(pitch: float, yaw: float, roll: float) -> Quat:
    # Radians input. Rotation order ZYX.
    cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
    cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
    cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
    return _qnorm((sr * cp * cy - cr * sp * sy, cr * sp * cy + sr * cp * sy, cr * cp * sy - sr * sp * cy, cr * cp * cy + sr * sp * sy))

def _quat_to_euler(q: Quat) -> Vec3:
    # Return (pitch, yaw, roll) in radians.
    x, y, z, w = q
    roll = math.atan2(2.0 * (w * x + y * z), 1.0 - 2.0 * (x * x + y * y))
    pitch = math.asin(_clamp(2.0 * (w * y - z * x), -1.0, 1.0))
    yaw = math.atan2(2.0 * (w * z + x * y), 1.0 - 2.0 * (y * y + z * z))
    return (pitch, yaw, roll)

def _qrotate(q: Quat, v: Vec3) -> Vec3:
    # Rotate vector v by quaternion q.
    qv = (q[0], q[1], q[2])
    t = _vscale(_vcross(qv, v), 2.0)
    return _vadd(_vadd(v, _vscale(t, q[3])), _vcross(qv, t))

class NodeType(Enum):
    ROOT = auto()
    GROUP = auto()
    MESH = auto()
    LIGHT = auto()
    CAMERA = auto()
    COLLIDER = auto()
    TRIGGER = auto()
    PARTICLE_EMITTER = auto()
    AUDIO_SOURCE = auto()
    UI_ELEMENT = auto()

class ComponentType(Enum):
    MESH = auto()
    LIGHT = auto()
    CAMERA = auto()
    COLLIDER = auto()
    PARTICLE = auto()
    AUDIO = auto()
    SCRIPT = auto()
    ANIMATION = auto()
    RIGIDBODY = auto()
    UNKNOWN = auto()

class TransformInheritance(Enum):
    INHERIT = auto()
    IGNORE_PARENT = auto()

class TraversalOrder(Enum):
    DEPTH_FIRST = auto()
    BREADTH_FIRST = auto()

class UpdatePhase(Enum):
    PRE_PHYSICS = auto()
    PHYSICS = auto()
    POST_PHYSICS = auto()
    RENDER = auto()

class SceneState(Enum):
    UNLOADED = auto()
    LOADED = auto()
    ACTIVE = auto()
    PAUSED = auto()
    TRANSITIONING = auto()


def _coerce_node_type(value: Any) -> NodeType:
    """Coerce a string or unknown value into a NodeType enum member."""
    if isinstance(value, NodeType):
        return value
    if isinstance(value, str):
        key = value.strip().upper()
        if key in NodeType.__members__:
            return NodeType[key]
    return NodeType.GROUP


def _coerce_component_type(value: Any) -> "ComponentType":
    """Coerce a string or unknown value into a ComponentType enum member."""
    if isinstance(value, ComponentType):
        return value
    if isinstance(value, str):
        key = value.strip().upper()
        if key in ComponentType.__members__:
            return ComponentType[key]
    return ComponentType.UNKNOWN

@dataclass
class NodeTransform:
    position: Vec3 = (0.0, 0.0, 0.0)
    rotation_quat: Quat = (0.0, 0.0, 0.0, 1.0)
    scale: Vec3 = (1.0, 1.0, 1.0)
    rotation_euler: Vec3 = (0.0, 0.0, 0.0)
    inheritance: TransformInheritance = TransformInheritance.INHERIT
    def to_dict(self) -> Dict[str, Any]:
        return {"position": list(self.position), "rotation_quat": list(self.rotation_quat), "scale": list(self.scale), "rotation_euler": list(self.rotation_euler), "inheritance": self.inheritance.name}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "NodeTransform":
        return NodeTransform(tuple(data.get("position", [0.0, 0.0, 0.0])), tuple(data.get("rotation_quat", [0.0, 0.0, 0.0, 1.0])), tuple(data.get("scale", [1.0, 1.0, 1.0])), tuple(data.get("rotation_euler", [0.0, 0.0, 0.0])), TransformInheritance[data.get("inheritance", "INHERIT")])

@dataclass
class BoundingVolume:
    min: Vec3 = (0.0, 0.0, 0.0)
    max: Vec3 = (0.0, 0.0, 0.0)
    valid: bool = False
    def center(self) -> Vec3:
        return tuple((self.min[i] + self.max[i]) * 0.5 for i in range(3))  # type: ignore[return-value]

    def size(self) -> Vec3:
        return tuple(self.max[i] - self.min[i] for i in range(3))  # type: ignore[return-value]

    def to_dict(self) -> Dict[str, Any]:
        return {"min": list(self.min), "max": list(self.max), "valid": self.valid}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BoundingVolume":
        return BoundingVolume(tuple(data.get("min", [0.0, 0.0, 0.0])), tuple(data.get("max", [0.0, 0.0, 0.0])), bool(data.get("valid", False)))

    @staticmethod
    def union(a: "BoundingVolume", b: "BoundingVolume") -> "BoundingVolume":
        if not a.valid: return BoundingVolume(b.min, b.max, b.valid)
        if not b.valid: return BoundingVolume(a.min, a.max, a.valid)
        return BoundingVolume(tuple(min(a.min[i], b.min[i]) for i in range(3)), tuple(max(a.max[i], b.max[i]) for i in range(3)), True)

@dataclass
class Component:
    component_id: str = ""
    node_id: str = ""
    type: ComponentType = ComponentType.UNKNOWN
    properties: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    def to_dict(self) -> Dict[str, Any]:
        return {"component_id": self.component_id, "node_id": self.node_id, "type": self.type.name, "properties": self.properties, "enabled": self.enabled}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Component":
        return Component(data.get("component_id", _uid()), data.get("node_id", ""), ComponentType[data.get("type", "UNKNOWN")], dict(data.get("properties", {})), bool(data.get("enabled", True)))

@dataclass
class SceneNode:
    node_id: str = ""
    name: str = ""
    type: NodeType = NodeType.GROUP
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    active: bool = True
    visible: bool = True
    tags: Set[str] = field(default_factory=set)
    metadata: Dict[str, Any] = field(default_factory=dict)
    local_transform: NodeTransform = field(default_factory=NodeTransform)
    world_transform: NodeTransform = field(default_factory=NodeTransform)
    bounds: BoundingVolume = field(default_factory=BoundingVolume)
    layer_id: str = "default"
    components: List[Component] = field(default_factory=list)
    dirty: bool = True
    created_at: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return {"node_id": self.node_id, "name": self.name, "type": self.type.name, "parent_id": self.parent_id, "children_ids": list(self.children_ids), "active": self.active, "visible": self.visible, "tags": sorted(self.tags), "metadata": self.metadata, "local_transform": self.local_transform.to_dict(), "world_transform": self.world_transform.to_dict(), "bounds": self.bounds.to_dict(), "layer_id": self.layer_id, "components": [c.to_dict() for c in self.components], "dirty": self.dirty, "created_at": self.created_at}

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SceneNode":
        return SceneNode(data.get("node_id", _uid()), data.get("name", ""), NodeType[data.get("type", "GROUP")], data.get("parent_id"), list(data.get("children_ids", [])), bool(data.get("active", True)), bool(data.get("visible", True)), set(data.get("tags", [])), dict(data.get("metadata", {})), NodeTransform.from_dict(data.get("local_transform", {})), NodeTransform.from_dict(data.get("world_transform", {})), BoundingVolume.from_dict(data.get("bounds", {})), data.get("layer_id", "default"), [Component.from_dict(c) for c in data.get("components", [])], bool(data.get("dirty", True)), float(data.get("created_at", 0.0)))

@dataclass
class Layer:
    layer_id: str = ""
    name: str = ""
    index: int = 0
    visible: bool = True
    collision_mask: int = 0xFFFFFFFF
    def to_dict(self) -> Dict[str, Any]:
        return {"layer_id": self.layer_id, "name": self.name, "index": self.index, "visible": self.visible, "collision_mask": self.collision_mask}

@dataclass
class SignalHandler:
    handler_id: str = ""
    signal_name: str = ""
    node_id: Optional[str] = None
    callback: Optional[Callable[..., Any]] = None
    once: bool = False
    def matches(self, signal_name: str, node_id: Optional[str]) -> bool:
        return self.signal_name == signal_name and (self.node_id is None or self.node_id == node_id)

@dataclass
class SceneEventData:
    event_name: str = ""
    node_id: Optional[str] = None
    scene_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0

@dataclass
class Prefab:
    prefab_id: str = ""
    name: str = ""
    template: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return {"prefab_id": self.prefab_id, "name": self.name, "template": self.template, "metadata": self.metadata, "created_at": self.created_at}

@dataclass
class Scene:
    scene_id: str = ""
    name: str = ""
    root_node_id: Optional[str] = None
    state: SceneState = SceneState.UNLOADED
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    layers: Dict[str, Layer] = field(default_factory=dict)
    created_at: float = 0.0
    def to_dict(self) -> Dict[str, Any]:
        return {"scene_id": self.scene_id, "name": self.name, "root_node_id": self.root_node_id, "state": self.state.name, "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()}, "layers": {lid: l.to_dict() for lid, l in self.layers.items()}, "created_at": self.created_at}

class SceneGraphSystem:

    _DEFAULT_LAYERS: Tuple[Tuple[str, int], ...] = (
        ("default", 0), ("player", 1), ("enemy", 2),
        ("environment", 3), ("ui", 4), ("trigger", 5))
    _instance = None
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, seed_sample: bool = True) -> None:
        self._lock = threading.RLock()
        self._scenes: Dict[str, Scene] = {}
        self._active_scene_id: Optional[str] = None
        self._prefabs: Dict[str, Prefab] = {}
        self._handlers: List[SignalHandler] = []
        self._dirty_nodes: Set[str] = set()
        self._initialized: bool = False
        self._stats: Dict[str, int] = {"nodes_created": 0, "nodes_removed": 0,
            "components_added": 0, "transforms_updated": 0, "ticks": 0, "signals_emitted": 0}
        if seed_sample:
            self._seed_sample_scene()

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._initialized = True
            if not self._scenes:
                self._seed_sample_scene()

    def reset(self) -> None:
        with self._lock:
            self._scenes.clear()
            self._prefabs.clear()
            self._handlers.clear()
            self._dirty_nodes.clear()
            self._active_scene_id = None
            for key in list(self._stats.keys()):
                self._stats[key] = 0
            self._initialized = False

    def _seed_sample_scene(self) -> str:
        scene_id = self._new_scene("Main")
        scene = self._scenes[scene_id]
        root = self._make_node("Root", NodeType.ROOT)
        world = self._make_node("World", NodeType.GROUP, parent_id=root.node_id)
        terrain = self._make_node("Terrain", NodeType.MESH, parent_id=world.node_id)
        terrain.tags.add("static")
        terrain.metadata["mesh_asset"] = "terrain_base.glb"
        player = self._make_node("Player", NodeType.MESH, parent_id=world.node_id)
        player.tags.add("player")
        spawner = self._make_node("EnemySpawner", NodeType.GROUP, parent_id=world.node_id)
        spawner.tags.add("spawner")
        ui = self._make_node("UI", NodeType.GROUP, parent_id=root.node_id)
        hud = self._make_node("HUD", NodeType.UI_ELEMENT, parent_id=ui.node_id)
        menu = self._make_node("Menu", NodeType.UI_ELEMENT, parent_id=ui.node_id)
        hud.layer_id = menu.layer_id = "ui"
        for node in (root, world, terrain, player, spawner, ui, hud, menu):
            scene.nodes[node.node_id] = node
            if node.parent_id and node.parent_id in scene.nodes:
                scene.nodes[node.parent_id].children_ids.append(node.node_id)
        scene.root_node_id = root.node_id
        scene.state = SceneState.ACTIVE
        self._active_scene_id = scene_id
        self.set_local_transform(player.node_id, position=(0.0, 1.0, 0.0), scene_id=scene_id)
        self.add_component(player.node_id, ComponentType.CAMERA, scene_id=scene_id)
        self._invalidate_subtree(root.node_id, scene_id)
        return scene_id

    def _new_scene(self, name: str) -> str:
        scene_id = _uid()
        self._scenes[scene_id] = Scene(scene_id, name, created_at=_now_ts(), layers={
            lid: Layer(lid, lid, idx, True) for lid, idx in self._DEFAULT_LAYERS})
        return scene_id

    def create_scene(self, name: str) -> str:
        with self._lock:
            scene_id = self._new_scene(name)
            self._emit("scene_loaded", None, scene_id, {"name": name})
            return scene_id

    def load_scene(self, scene_data: Dict[str, Any], additive: bool = False) -> str:
        with self._lock:
            if not additive and self._active_scene_id:
                self.unload_scene(self._active_scene_id)
            scene = Scene(scene_data.get("scene_id", _uid()), scene_data.get("name", "ImportedScene"),
                          scene_data.get("root_node_id"), SceneState[scene_data.get("state", "LOADED")],
                          {nid: SceneNode.from_dict(nd) for nid, nd in scene_data.get("nodes", {}).items()},
                          {lid: Layer(lid, l.get("name", lid), int(l.get("index", 0)),
                                      bool(l.get("visible", True)), int(l.get("collision_mask", 0xFFFFFFFF)))
                           for lid, l in scene_data.get("layers", {}).items()},
                          float(scene_data.get("created_at", _now_ts())))
            self._scenes[scene.scene_id] = scene
            self._active_scene_id = scene.scene_id
            scene.state = SceneState.ACTIVE
            if scene.root_node_id:
                self._invalidate_subtree(scene.root_node_id, scene.scene_id)
            self._emit("scene_loaded", None, scene.scene_id, {"name": scene.name, "additive": additive})
            return scene.scene_id

    def unload_scene(self, scene_id: str) -> bool:
        with self._lock:
            scene = self._scenes.get(scene_id)
            if scene is None: return False
            scene.state = SceneState.UNLOADED
            self._emit("node_removed", None, scene_id, {"count": len(scene.nodes)})
            del self._scenes[scene_id]
            if self._active_scene_id == scene_id:
                remaining = list(self._scenes.keys())
                self._active_scene_id = remaining[0] if remaining else None
            self._dirty_nodes = {n for n in self._dirty_nodes if self._scene_of(n) != scene_id}
            return True

    def get_active_scene(self) -> Optional[Scene]:
        with self._lock:
            return self._scenes.get(self._active_scene_id) if self._active_scene_id else None

    def save_scene(self, scene_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return {}
            self._emit("scene_saved", None, scene.scene_id, {})
            return scene.to_dict()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {"scenes": {sid: s.to_dict() for sid, s in self._scenes.items()}, "active_scene_id": self._active_scene_id, "prefabs": {pid: p.to_dict() for pid, p in self._prefabs.items()}, "stats": dict(self._stats), "initialized": self._initialized}

    def _make_node(self, name: str, node_type: NodeType, parent_id: Optional[str] = None) -> SceneNode:
        node = SceneNode(_uid(), name, node_type, parent_id=parent_id, created_at=_now_ts())
        self._stats["nodes_created"] += 1
        return node

    def create_node(self, name: str, node_type: NodeType, parent_id: Optional[str] = None, scene_id: Optional[str] = None, tags: Optional[Iterable[str]] = None) -> str:
        node_type = _coerce_node_type(node_type)
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None:
                scene_id = self.create_scene("AutoScene")
                scene = self._scenes[scene_id]
            node = self._make_node(name, node_type, parent_id=parent_id)
            if tags:
                node.tags.update(tags)
            if parent_id and parent_id in scene.nodes:
                parent = scene.nodes[parent_id]
                parent.children_ids.append(node.node_id)
                node.layer_id = parent.layer_id
                self._emit("child_added", parent_id, scene.scene_id, {"child_id": node.node_id})
            scene.nodes[node.node_id] = node
            if scene.root_node_id is None:
                scene.root_node_id = node.node_id
            self._invalidate_subtree(node.node_id, scene.scene_id)
            self._emit("node_created", node.node_id, scene.scene_id, {"name": name, "type": node_type.name})
            self._emit("ready", node.node_id, scene.scene_id, {})
            self._emit("entered_tree", node.node_id, scene.scene_id, {})
            return node.node_id

    def remove_node(self, node_id: str, scene_id: Optional[str] = None, remove_children: bool = True) -> bool:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return False
            node = scene.nodes[node_id]
            children = list(node.children_ids)
            if remove_children:
                for child_id in children:
                    self.remove_node(child_id, scene.scene_id, True)
            else:
                # Promote children to the removed node's parent.
                for child_id in children:
                    child = scene.nodes.get(child_id)
                    if child is not None:
                        child.parent_id = node.parent_id
                        if node.parent_id and node.parent_id in scene.nodes:
                            scene.nodes[node.parent_id].children_ids.append(child_id)
            if node.parent_id and node.parent_id in scene.nodes:
                parent = scene.nodes[node.parent_id]
                if node_id in parent.children_ids:
                    parent.children_ids.remove(node_id)
                self._emit("child_removed", node.parent_id, scene.scene_id, {"child_id": node_id})
            self._emit("exited_tree", node_id, scene.scene_id, {})
            self._emit("node_removed", node_id, scene.scene_id, {})
            del scene.nodes[node_id]
            self._dirty_nodes.discard(node_id)
            self._stats["nodes_removed"] += 1
            if scene.root_node_id == node_id:
                scene.root_node_id = None
            return True

    def get_node(self, node_id: str, scene_id: Optional[str] = None) -> Optional[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return scene.nodes.get(node_id) if scene else None

    def reparent_node(self, node_id: str, new_parent_id: Optional[str], scene_id: Optional[str] = None, preserve_world_transform: bool = True) -> bool:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return False
            if new_parent_id is not None and (new_parent_id not in scene.nodes or new_parent_id == node_id): return False
            if new_parent_id and self._is_descendant(new_parent_id, node_id, scene): return False
            node = scene.nodes[node_id]
            old_world = node.world_transform if preserve_world_transform else None
            if node.parent_id and node.parent_id in scene.nodes:
                old_parent = scene.nodes[node.parent_id]
                if node_id in old_parent.children_ids:
                    old_parent.children_ids.remove(node_id)
            node.parent_id = new_parent_id
            if new_parent_id:
                scene.nodes[new_parent_id].children_ids.append(node_id)
                self._emit("child_added", new_parent_id, scene.scene_id, {"child_id": node_id})
            self._emit("parent_changed", node_id, scene.scene_id, {"new_parent_id": new_parent_id})
            self._invalidate_subtree(node_id, scene.scene_id)
            if preserve_world_transform and old_world is not None and new_parent_id:
                # Re-derive local transform so the world position stays fixed.
                parent = scene.nodes[new_parent_id]
                node.local_transform = self._world_to_local(old_world, parent.world_transform)
                self._invalidate_subtree(node_id, scene.scene_id)
            return True

    def find_node(self, path: str, scene_id: Optional[str] = None) -> Optional[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or not path: return None
            clean = path.strip("/")
            if not clean: return scene.nodes.get(scene.root_node_id) if scene.root_node_id else None
            parts = clean.split("/")
            root = scene.nodes.get(scene.root_node_id) if scene.root_node_id else None
            if root is not None and root.name == parts[0]:
                current: Optional[SceneNode] = root
            else:
                current = self.find_by_name(parts[0], scene.scene_id)
            if current is None: return None
            for part in parts[1:]:
                nxt: Optional[SceneNode] = None
                for child_id in current.children_ids:
                    child = scene.nodes.get(child_id)
                    if child is not None and child.name == part:
                        nxt = child
                        break
                if nxt is None: return None
                current = nxt
            return current

    def find_by_name(self, name: str, scene_id: Optional[str] = None) -> Optional[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return None
            return next((n for n in scene.nodes.values() if n.name == name), None)

    def find_by_tag(self, tag: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return [n for n in scene.nodes.values() if tag in n.tags] if scene else []

    def find_by_type(self, node_type: NodeType, scene_id: Optional[str] = None) -> List[SceneNode]:
        node_type = _coerce_node_type(node_type)
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return [n for n in scene.nodes.values() if n.type == node_type] if scene else []

    def get_children(self, node_id: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            node = scene.nodes.get(node_id)
            return [scene.nodes[cid] for cid in node.children_ids if cid in scene.nodes] if node else []

    def get_ancestors(self, node_id: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            result: List[SceneNode] = []
            node = scene.nodes.get(node_id)
            seen: Set[str] = set()
            while node and node.parent_id and node.parent_id not in seen:
                seen.add(node.parent_id)
                parent = scene.nodes.get(node.parent_id)
                if parent is None:
                    break
                result.append(parent)
                node = parent
            return result

    def get_descendants(self, node_id: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            node = scene.nodes.get(node_id)
            if node is None: return []
            result: List[SceneNode] = []
            stack: Deque[str] = deque(reversed(node.children_ids))
            while stack:
                child = scene.nodes.get(stack.pop())
                if child is None: continue
                result.append(child)
                stack.extend(reversed(child.children_ids))
            return result

    def get_siblings(self, node_id: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            node = scene.nodes.get(node_id)
            if node is None or node.parent_id is None: return []
            parent = scene.nodes.get(node.parent_id)
            return [scene.nodes[cid] for cid in parent.children_ids
                    if cid != node_id and cid in scene.nodes] if parent else []

    def get_depth(self, node_id: str, scene_id: Optional[str] = None) -> int:
        return len(self.get_ancestors(node_id, scene_id))

    def set_local_transform(self, node_id: str, position: Optional[Vec3] = None, rotation_euler: Optional[Vec3] = None, rotation_quat: Optional[Quat] = None, scale: Optional[Vec3] = None, inheritance: Optional[TransformInheritance] = None, scene_id: Optional[str] = None) -> bool:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return False
            t = scene.nodes[node_id].local_transform
            if position is not None:
                t.position = position
            if rotation_euler is not None:
                t.rotation_euler = rotation_euler
                t.rotation_quat = _euler_to_quat(*rotation_euler)
            if rotation_quat is not None:
                t.rotation_quat = _qnorm(rotation_quat)
                t.rotation_euler = _quat_to_euler(t.rotation_quat)
            if scale is not None:
                t.scale = scale
            if inheritance is not None:
                t.inheritance = inheritance
            self._invalidate_subtree(node_id, scene.scene_id)
            return True

    def get_local_transform(self, node_id: str, scene_id: Optional[str] = None) -> Optional[NodeTransform]:
        node = self.get_node(node_id, scene_id)
        return node.local_transform if node else None

    def get_world_transform(self, node_id: str, scene_id: Optional[str] = None) -> Optional[NodeTransform]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return None
            self.update_transforms(scene.scene_id)
            return scene.nodes[node_id].world_transform

    def invalidate_transform(self, node_id: str, scene_id: Optional[str] = None) -> None:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is not None:
                self._invalidate_subtree(node_id, scene.scene_id)

    def update_transforms(self, scene_id: Optional[str] = None) -> int:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or scene.root_node_id is None: return 0
            updated = 0

            def _update(node: SceneNode, parent_world: Optional[NodeTransform]) -> None:
                nonlocal updated
                lt = node.local_transform
                if parent_world is None or lt.inheritance == TransformInheritance.IGNORE_PARENT:
                    node.world_transform = NodeTransform(lt.position, lt.rotation_quat, lt.scale,
                                                         lt.rotation_euler, lt.inheritance)
                else:
                    pw = parent_world
                    new_rot = _qmul(pw.rotation_quat, lt.rotation_quat)
                    node.world_transform = NodeTransform(
                        _vadd(pw.position, _qrotate(pw.rotation_quat, _vmul(pw.scale, lt.position))),
                        new_rot, _vmul(pw.scale, lt.scale), _quat_to_euler(new_rot), lt.inheritance)
                node.dirty = False
                self._dirty_nodes.discard(node.node_id)
                updated += 1
                for cid in node.children_ids:
                    child = scene.nodes.get(cid)
                    if child is not None:
                        _update(child, node.world_transform)

            root = scene.nodes.get(scene.root_node_id)
            if root is not None:
                _update(root, None)
            self._stats["transforms_updated"] += updated
            return updated

    def _world_to_local(self, world: NodeTransform, parent_world: NodeTransform) -> NodeTransform:
        ps = parent_world.scale
        inv_scale = (1.0 / ps[0] if ps[0] else 1.0, 1.0 / ps[1] if ps[1] else 1.0, 1.0 / ps[2] if ps[2] else 1.0)
        inv_quat = _qconj(parent_world.rotation_quat)
        local_pos = _vmul(_qrotate(inv_quat, _vsub(world.position, parent_world.position)), inv_scale)
        local_rot = _qmul(inv_quat, world.rotation_quat)
        return NodeTransform(local_pos, local_rot, _vmul(world.scale, inv_scale), _quat_to_euler(local_rot), TransformInheritance.INHERIT)

    def add_component(self, node_id: str, component_type: ComponentType, properties: Optional[Dict[str, Any]] = None, scene_id: Optional[str] = None) -> Optional[str]:
        component_type = _coerce_component_type(component_type)
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return None
            component = Component(_uid(), node_id, component_type, dict(properties or {}))
            scene.nodes[node_id].components.append(component)
            self._stats["components_added"] += 1
            self._invalidate_subtree(node_id, scene.scene_id)
            return component.component_id

    def remove_component(self, node_id: str, component_id: str, scene_id: Optional[str] = None) -> bool:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return False
            node = scene.nodes[node_id]
            before = len(node.components)
            node.components = [c for c in node.components if c.component_id != component_id]
            if len(node.components) != before:
                self._invalidate_subtree(node_id, scene.scene_id)
                return True
            return False

    def get_component(self, node_id: str, component_id: str, scene_id: Optional[str] = None) -> Optional[Component]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return None
            return next((c for c in scene.nodes[node_id].components if c.component_id == component_id), None)

    def get_components_by_type(self, node_id: str, component_type: ComponentType, scene_id: Optional[str] = None) -> List[Component]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return []
            return [c for c in scene.nodes[node_id].components if c.type == component_type and c.enabled]

    def get_nodes_with_component(self, component_type: ComponentType, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            return [n for n in scene.nodes.values()
                    if any(c.type == component_type and c.enabled for c in n.components)]

    def compute_bounds(self, scene_id: Optional[str] = None) -> int:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or scene.root_node_id is None: return 0
            self.update_transforms(scene.scene_id)
            count = 0

            def _recurse(node: SceneNode) -> BoundingVolume:
                nonlocal count
                count += 1
                bv = self._node_self_bounds(node)
                for cid in node.children_ids:
                    child = scene.nodes.get(cid)
                    if child is not None:
                        bv = BoundingVolume.union(bv, _recurse(child))
                node.bounds = bv
                return bv

            root = scene.nodes.get(scene.root_node_id)
            if root is not None:
                _recurse(root)
            return count

    def get_bounds(self, node_id: str, scene_id: Optional[str] = None) -> Optional[BoundingVolume]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return None
            self.compute_bounds(scene.scene_id)
            return scene.nodes[node_id].bounds

    def frustum_cull(self, frustum: List[Tuple[Vec3, float]], scene_id: Optional[str] = None) -> List[SceneNode]:
        """Return nodes whose AABB intersects the frustum planes.

        Each plane is a (normal, distance) tuple such that a point p is
        inside the frustum when dot(normal, p) + distance >= 0.
        """
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            self.compute_bounds(scene.scene_id)
            result: List[SceneNode] = []
            for node in scene.nodes.values():
                if not node.visible or not node.bounds.valid: continue
                layer = scene.layers.get(node.layer_id)
                if layer is not None and not layer.visible: continue
                if self._aabb_in_frustum(node.bounds, frustum):
                    result.append(node)
            return result

    @staticmethod
    def _aabb_in_frustum(bv: BoundingVolume, frustum: List[Tuple[Vec3, float]]) -> bool:
        # Positive vertex test: if the AABB corner farthest along the plane
        # normal is outside the plane, the box is fully culled.
        for normal, dist in frustum:
            px = bv.max[0] if normal[0] >= 0 else bv.min[0]
            py = bv.max[1] if normal[1] >= 0 else bv.min[1]
            pz = bv.max[2] if normal[2] >= 0 else bv.min[2]
            if normal[0] * px + normal[1] * py + normal[2] * pz + dist < 0: return False
        return True

    def _node_self_bounds(self, node: SceneNode) -> BoundingVolume:
        local_min: Vec3 = (-0.5, -0.5, -0.5)
        local_max: Vec3 = (0.5, 0.5, 0.5)
        mesh_comp = next((c for c in node.components if c.type == ComponentType.MESH and c.enabled), None)
        if mesh_comp is not None:
            half = mesh_comp.properties.get("half_extent", (0.5, 0.5, 0.5))
            local_min = (-half[0], -half[1], -half[2])
            local_max = (half[0], half[1], half[2])
        elif node.type in (NodeType.LIGHT, NodeType.CAMERA):
            local_min, local_max = (-0.1, -0.1, -0.1), (0.1, 0.1, 0.1)
        elif node.type == NodeType.UI_ELEMENT:
            size = node.metadata.get("size", (1.0, 1.0))
            local_min, local_max = (-size[0] * 0.5, -size[1] * 0.5, 0.0), (size[0] * 0.5, size[1] * 0.5, 0.0)
        wt = node.world_transform
        corners = [
            (local_min[0], local_min[1], local_min[2]), (local_max[0], local_min[1], local_min[2]),
            (local_min[0], local_max[1], local_min[2]), (local_max[0], local_max[1], local_min[2]),
            (local_min[0], local_min[1], local_max[2]), (local_max[0], local_min[1], local_max[2]),
            (local_min[0], local_max[1], local_max[2]), (local_max[0], local_max[1], local_max[2])]
        wc = [_vadd(wt.position, _qrotate(wt.rotation_quat, _vmul(wt.scale, c))) for c in corners]
        return BoundingVolume((min(p[0] for p in wc), min(p[1] for p in wc), min(p[2] for p in wc)), (max(p[0] for p in wc), max(p[1] for p in wc), max(p[2] for p in wc)), True)

    def set_layer(self, node_id: str, layer_id: str, scene_id: Optional[str] = None, recursive: bool = False) -> bool:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or node_id not in scene.nodes: return False
            if layer_id not in scene.layers:
                scene.layers[layer_id] = Layer(layer_id, layer_id, len(scene.layers))
            node = scene.nodes[node_id]
            node.layer_id = layer_id
            if recursive:
                for child in self.get_descendants(node_id, scene.scene_id):
                    child.layer_id = layer_id
            return True

    def get_layer(self, node_id: str, scene_id: Optional[str] = None) -> Optional[Layer]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return scene.layers.get(scene.nodes[node_id].layer_id) if scene and node_id in scene.nodes else None

    def get_nodes_in_layer(self, layer_id: str, scene_id: Optional[str] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return [n for n in scene.nodes.values() if n.layer_id == layer_id] if scene else []

    def traverse(self, scene_id: Optional[str] = None, order: TraversalOrder = TraversalOrder.DEPTH_FIRST, predicate: Optional[Callable[[SceneNode], bool]] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or scene.root_node_id is None: return []
            if order == TraversalOrder.DEPTH_FIRST: return self.traverse_dfs(scene.root_node_id, scene.scene_id, predicate)
            return self.traverse_bfs(scene.root_node_id, scene.scene_id, predicate)

    def traverse_dfs(self, node_id: str, scene_id: Optional[str] = None, predicate: Optional[Callable[[SceneNode], bool]] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            result: List[SceneNode] = []

            def _visit(nid: str) -> None:
                node = scene.nodes.get(nid)
                if node is None:
                    return
                if predicate is None or predicate(node):
                    result.append(node)
                for cid in node.children_ids:
                    _visit(cid)

            _visit(node_id)
            return result

    def traverse_bfs(self, node_id: str, scene_id: Optional[str] = None, predicate: Optional[Callable[[SceneNode], bool]] = None) -> List[SceneNode]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            result: List[SceneNode] = []
            queue: Deque[str] = deque([node_id])
            while queue:
                node = scene.nodes.get(queue.popleft())
                if node is None: continue
                if predicate is None or predicate(node):
                    result.append(node)
                queue.extend(node.children_ids)
            return result

    def connect_signal(self, signal_name: str, callback: Callable[..., Any], node_id: Optional[str] = None, once: bool = False) -> str:
        with self._lock:
            handler = SignalHandler(_uid(), signal_name, node_id, callback, once)
            self._handlers.append(handler)
            return handler.handler_id

    def disconnect_signal(self, handler_id: str) -> bool:
        with self._lock:
            before = len(self._handlers)
            self._handlers = [h for h in self._handlers if h.handler_id != handler_id]
            return len(self._handlers) != before

    def emit_signal(self, signal_name: str, node_id: Optional[str] = None, payload: Optional[Dict[str, Any]] = None, scene_id: Optional[str] = None) -> int:
        with self._lock:
            return self._emit(signal_name, node_id, scene_id, payload or {})

    def _emit(self, signal_name: str, node_id: Optional[str], scene_id: Optional[str], payload: Dict[str, Any]) -> int:
        # Internal emitter that assumes the lock is already held.
        data = SceneEventData(signal_name, node_id, scene_id, dict(payload), _now_ts())
        called = 0
        remaining: List[SignalHandler] = []
        for handler in self._handlers:
            if not handler.matches(signal_name, node_id):
                remaining.append(handler)
                continue
            try:
                if handler.callback is not None:
                    handler.callback(data)
                    called += 1
            except Exception:
                # Swallow handler errors so a bad listener cannot break the graph.
                pass
            if not handler.once:
                remaining.append(handler)
        self._handlers = remaining
        self._stats["signals_emitted"] += called
        return called

    def create_prefab(self, name: str, root_node_id: str, scene_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None or root_node_id not in scene.nodes: return None
            prefab = Prefab(_uid(), name, self._serialize_subtree(root_node_id, scene),
                            dict(metadata or {}), _now_ts())
            self._prefabs[prefab.prefab_id] = prefab
            return prefab.prefab_id

    def instantiate_prefab(self, prefab_id: str, parent_id: Optional[str] = None, scene_id: Optional[str] = None, name_prefix: Optional[str] = None) -> Optional[str]:
        with self._lock:
            prefab = self._prefabs.get(prefab_id)
            if prefab is None: return None
            scene = self._resolve_scene(scene_id)
            if scene is None:
                scene_id = self.create_scene("AutoScene")
                scene = self._scenes[scene_id]
            return self._instantiate_template(prefab.template, parent_id, scene, name_prefix)

    def _instantiate_template(self, template: Dict[str, Any], parent_id: Optional[str], scene: Scene, name_prefix: Optional[str]) -> str:
        node = SceneNode.from_dict(template)
        node.node_id = _uid()
        node.parent_id = parent_id
        node.created_at = _now_ts()
        if name_prefix:
            node.name = f"{name_prefix}_{node.name}"
        node.children_ids = []
        scene.nodes[node.node_id] = node
        self._stats["nodes_created"] += 1
        if parent_id and parent_id in scene.nodes:
            scene.nodes[parent_id].children_ids.append(node.node_id)
        for child_template in template.get("children", []):
            node.children_ids.append(
                self._instantiate_template(child_template, node.node_id, scene, name_prefix))
        self._invalidate_subtree(node.node_id, scene.scene_id)
        return node.node_id

    def _serialize_subtree(self, node_id: str, scene: Scene) -> Dict[str, Any]:
        node = scene.nodes.get(node_id)
        if node is None: return {}
        data = node.to_dict()
        data["children"] = [self._serialize_subtree(cid, scene)
                            for cid in node.children_ids if cid in scene.nodes]
        return data

    def tick(self, delta_time: float, scene_id: Optional[str] = None, phase: UpdatePhase = UpdatePhase.RENDER) -> Dict[str, Any]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return {"transforms": 0, "bounds": 0, "components": 0}
            transforms = self.update_transforms(scene.scene_id)
            bounds = self.compute_bounds(scene.scene_id)
            components = 0
            for node in scene.nodes.values():
                if not node.active: continue
                for comp in node.components:
                    if not comp.enabled: continue
                    update_fn = comp.properties.get("on_update")
                    if callable(update_fn):
                        try:
                            update_fn(node, comp, delta_time, phase)
                            components += 1
                        except Exception:
                            pass
            self._stats["ticks"] += 1
            return {"transforms": transforms, "bounds": bounds, "components": components, "phase": phase.name}

    def get_dirty_nodes(self, scene_id: Optional[str] = None) -> List[str]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            return [n.node_id for n in scene.nodes.values() if n.dirty] if scene else []

    def clear_dirty(self, scene_id: Optional[str] = None) -> int:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return 0
            count = sum(1 for n in scene.nodes.values() if n.dirty)
            for node in scene.nodes.values():
                node.dirty = False
            self._dirty_nodes.clear()
            return count

    def get_snapshot(self, scene_id: Optional[str] = None) -> Dict[str, Any]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return {}
            return {"scene_id": scene.scene_id, "name": scene.name, "state": scene.state.name, "node_count": len(scene.nodes), "layer_count": len(scene.layers), "root_node_id": scene.root_node_id, "dirty_count": sum(1 for n in scene.nodes.values() if n.dirty), "tree": self._tree_snapshot(scene.root_node_id, scene) if scene.root_node_id else None}

    def _tree_snapshot(self, node_id: str, scene: Scene, depth: int = 0) -> Dict[str, Any]:
        node = scene.nodes.get(node_id)
        if node is None: return {}
        return {"name": node.name, "type": node.type.name, "layer": node.layer_id, "depth": depth, "children": [self._tree_snapshot(cid, scene, depth + 1) for cid in node.children_ids]}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            active = self.get_active_scene()
            return {"initialized": self._initialized, "scene_count": len(self._scenes), "active_scene": active.name if active else None, "active_scene_id": self._active_scene_id, "prefab_count": len(self._prefabs), "handler_count": len(self._handlers)}

    def get_stats(self) -> Dict[str, int]:
        with self._lock:
            return dict(self._stats)

    def ai_generate_scene(self, description: str, scene_name: str = "GeneratedScene") -> Optional[str]:
        """Generate a scene tree from a natural language description.

        Recognized keywords drive node creation: terrain, ground, player,
        enemy, spawner, camera, light, particle, audio, ui, hud, menu,
        sky, water, props. Unknown tokens become groups.
        """
        with self._lock:
            scene_id = self.create_scene(scene_name)
            scene = self._scenes[scene_id]
            root = self._make_node("Root", NodeType.ROOT)
            scene.nodes[root.node_id] = root
            scene.root_node_id = root.node_id
            tokens = [t.strip().lower() for t in description.replace(",", " ").split() if t.strip()]
            ui_parent: Optional[str] = None
            enemy_parent: Optional[str] = None
            for token in tokens:
                if token in ("root", "scene", "world", "level"): continue
                node_type, name = self._token_to_node(token)
                parent_id = root.node_id
                if node_type == NodeType.UI_ELEMENT:
                    if ui_parent is None:
                        ui_node = self._make_node("UI", NodeType.GROUP, parent_id=root.node_id)
                        scene.nodes[ui_node.node_id] = ui_node
                        root.children_ids.append(ui_node.node_id)
                        ui_parent = ui_node.node_id
                    parent_id = ui_parent
                elif name.lower().startswith("enemy"):
                    if enemy_parent is None:
                        sp = self._make_node("EnemySpawner", NodeType.GROUP, parent_id=root.node_id)
                        sp.tags.add("spawner")
                        scene.nodes[sp.node_id] = sp
                        root.children_ids.append(sp.node_id)
                        enemy_parent = sp.node_id
                    parent_id = enemy_parent
                node = self._make_node(name, node_type, parent_id=parent_id)
                scene.nodes[node.node_id] = node
                scene.nodes[parent_id].children_ids.append(node.node_id)
                self._apply_default_transform(node)
                self._apply_default_component(node)
            if any(t.startswith("player") for t in tokens):
                player = self.find_by_name("Player", scene_id)
                if player is not None:
                    self.set_local_transform(player.node_id, position=(0.0, 1.0, 0.0), scene_id=scene_id)
            self._invalidate_subtree(root.node_id, scene_id)
            self._emit("scene_loaded", None, scene_id, {"generated": True, "description": description})
            return scene_id

    @staticmethod
    def _token_to_node(token: str) -> Tuple[NodeType, str]:
        mapping: Dict[str, Tuple[NodeType, str]] = {
            "terrain": (NodeType.MESH, "Terrain"), "ground": (NodeType.MESH, "Ground"),
            "player": (NodeType.MESH, "Player"), "enemy": (NodeType.MESH, "Enemy"),
            "spawner": (NodeType.GROUP, "EnemySpawner"), "camera": (NodeType.CAMERA, "Camera"),
            "light": (NodeType.LIGHT, "Light"), "particle": (NodeType.PARTICLE_EMITTER, "Particles"),
            "audio": (NodeType.AUDIO_SOURCE, "AudioSource"), "ui": (NodeType.GROUP, "UI"),
            "hud": (NodeType.UI_ELEMENT, "HUD"), "menu": (NodeType.UI_ELEMENT, "Menu"),
            "sky": (NodeType.MESH, "SkyDome"), "water": (NodeType.MESH, "Water"),
            "props": (NodeType.GROUP, "Props")}
        return mapping.get(token, (NodeType.GROUP, token.capitalize()))

    def _apply_default_transform(self, node: SceneNode) -> None:
        if node.type == NodeType.CAMERA:
            node.local_transform.position = (0.0, 5.0, -10.0)
        elif node.type == NodeType.LIGHT:
            node.local_transform.position = (0.0, 10.0, 0.0)
        elif node.type == NodeType.UI_ELEMENT:
            node.layer_id = "ui"

    def _apply_default_component(self, node: SceneNode) -> None:
        defaults = {NodeType.MESH: (ComponentType.MESH, {"half_extent": (1.0, 1.0, 1.0)}),
                    NodeType.CAMERA: (ComponentType.CAMERA, {"fov": 60.0, "near": 0.1, "far": 1000.0}),
                    NodeType.LIGHT: (ComponentType.LIGHT, {"intensity": 1.0, "color": (1.0, 1.0, 1.0)})}
        if node.type in defaults:
            ctype, props = defaults[node.type]
            node.components.append(Component(_uid(), node.node_id, ctype, props))
            self._stats["components_added"] += 1

    def ai_optimize_scene(self, scene_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock:
            scene = self._resolve_scene(scene_id)
            if scene is None: return []
            suggestions: List[Dict[str, Any]] = []
            for node in scene.nodes.values():
                if node.type == NodeType.GROUP and len(node.children_ids) > 8:
                    suggestions.append({"kind": "split_group", "node_id": node.node_id, "name": node.name,
                        "child_count": len(node.children_ids),
                        "message": "Group has many direct children; split into sub-groups."})
                if node.type == NodeType.MESH and not node.components:
                    suggestions.append({"kind": "missing_mesh_component", "node_id": node.node_id,
                        "name": node.name, "message": "Mesh node has no mesh component attached."})
                if node.type == NodeType.GROUP and not node.children_ids:
                    suggestions.append({"kind": "empty_group", "node_id": node.node_id, "name": node.name,
                        "message": "Empty group node can be removed."})
            for node in scene.nodes.values():
                depth = self.get_depth(node.node_id, scene.scene_id)
                if depth > 6:
                    suggestions.append({"kind": "deep_chain", "node_id": node.node_id, "name": node.name,
                        "depth": depth, "message": "Node is deeply nested; consider flattening."})
                    break
            static_meshes = [n for n in scene.nodes.values()
                             if n.type == NodeType.MESH and "static" in n.tags]
            if len(static_meshes) > 4:
                suggestions.append({"kind": "merge_static", "count": len(static_meshes),
                    "message": "Many static mesh nodes detected; combine into one batched mesh."})
            return suggestions

    def _resolve_scene(self, scene_id: Optional[str]) -> Optional[Scene]:
        if scene_id is not None: return self._scenes.get(scene_id)
        if self._active_scene_id is not None: return self._scenes.get(self._active_scene_id)
        return next(iter(self._scenes.values()), None) if self._scenes else None

    def _scene_of(self, node_id: str) -> Optional[str]:
        for sid, scene in self._scenes.items():
            if node_id in scene.nodes: return sid
        return None

    def _is_descendant(self, candidate_id: str, ancestor_id: str, scene: Scene) -> bool:
        ancestor = scene.nodes.get(ancestor_id)
        stack = list(ancestor.children_ids) if ancestor else []
        seen: Set[str] = set()
        while stack:
            cid = stack.pop()
            if cid in seen: continue
            seen.add(cid)
            if cid == candidate_id: return True
            node = scene.nodes.get(cid)
            if node is not None:
                stack.extend(node.children_ids)
        return False

    def _invalidate_subtree(self, node_id: str, scene_id: str) -> None:
        scene = self._scenes.get(scene_id)
        if scene is None:
            return
        stack = [node_id]
        seen: Set[str] = set()
        while stack:
            nid = stack.pop()
            if nid in seen: continue
            seen.add(nid)
            node = scene.nodes.get(nid)
            if node is None: continue
            node.dirty = True
            self._dirty_nodes.add(nid)
            stack.extend(node.children_ids)

class Vector3:
    """3D vector for backward compatibility."""
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x, self.y, self.z = x, y, z

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z}


class Quaternion:
    """Quaternion rotation for backward compatibility."""
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, w: float = 1.0):
        self.x, self.y, self.z, self.w = x, y, z, w

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "z": self.z, "w": self.w}


class Transform3D:
    """3D transform for backward compatibility."""
    def __init__(self, position=None, rotation=None, scale=None):
        self.position = position or Vector3()
        self.rotation = rotation or Quaternion()
        self.scale = scale or Vector3(1.0, 1.0, 1.0)

    def to_dict(self) -> dict:
        return {"position": self.position.to_dict(), "rotation": self.rotation.to_dict(), "scale": self.scale.to_dict()}


class Transform2D:
    """2D transform for backward compatibility."""
    def __init__(self, x: float = 0.0, y: float = 0.0, rotation: float = 0.0, scale_x: float = 1.0, scale_y: float = 1.0):
        self.x, self.y = x, y
        self.rotation = rotation
        self.scale_x, self.scale_y = scale_x, scale_y

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "rotation": self.rotation, "scale_x": self.scale_x, "scale_y": self.scale_y}


def get_scene_graph() -> SceneGraphSystem:
    """Return the shared SceneGraphSystem singleton instance."""
    return SceneGraphSystem.get_instance()


# Backward-compatible aliases for code that imports the legacy names
SceneGraphEngine = SceneGraphSystem
GraphNode = SceneNode


__all__ = [
    "SceneGraphSystem", "SceneGraphEngine", "GraphNode", "get_scene_graph",
    "NodeTransform", "BoundingVolume", "Component", "SceneNode", "Layer",
    "SignalHandler", "SceneEventData", "Prefab", "Scene",
    "NodeType", "ComponentType", "TransformInheritance", "TraversalOrder",
    "UpdatePhase", "SceneState",
    # Backward compatibility
    "Vector3", "Quaternion", "Transform3D", "Transform2D",
]
