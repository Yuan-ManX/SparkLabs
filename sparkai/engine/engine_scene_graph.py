"""
SparkLabs Engine - Scene Graph

Hierarchical node-based scene organization system for the SparkLabs
AI-native game engine. Provides a tree-structured scene graph with
3D transforms, path-based node addressing, serialization, and prefab
instantiation.

Architecture:
  SceneGraphEngine (Singleton)
    |-- GraphNode         — hierarchical node with transform, tags, and components
    |-- Transform3D       — 3D position/rotation/scale with local-to-world matrices
    |-- StarPath          — path-based node addressing with wildcard matching
    |-- NebulaSerializer  — scene persistence with JSON and binary formats
    |-- ConstellationLibrary — reusable prefab templates with variant support
    |-- Quaternion        — 4-component rotation representation
    |-- EulerAngles       — pitch/yaw/roll rotation representation
    |-- NodeSignal        — emitted when node properties change
    |-- TraversalOrder    — scene tree walk order enumeration
    |-- PathMatchMode     — wildcard matching strategy
    |-- SerialFormat      — serialization format identifiers
    |-- PrefabStatus      — prefab lifecycle state
"""

from __future__ import annotations

import copy
import math
import struct
import threading
import time as _time_module
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TraversalOrder(Enum):
    """Scene tree walk order."""
    PRE_ORDER = "pre_order"
    POST_ORDER = "post_order"
    LEVEL_ORDER = "level_order"


class NodeSignal(Enum):
    """Signals emitted when node state changes."""
    TRANSFORM_CHANGED = "transform_changed"
    PARENT_CHANGED = "parent_changed"
    NAME_CHANGED = "name_changed"
    ACTIVE_CHANGED = "active_changed"
    TAG_ADDED = "tag_added"
    TAG_REMOVED = "tag_removed"
    COMPONENT_ATTACHED = "component_attached"
    COMPONENT_DETACHED = "component_detached"
    CHILD_ADDED = "child_added"
    CHILD_REMOVED = "child_removed"


class PathMatchMode(Enum):
    """Wildcard matching strategy for StarPath resolution."""
    EXACT = "exact"
    WILDCARD = "wildcard"
    RECURSIVE = "recursive"
    REGEX = "regex"


class SerialFormat(Enum):
    """Serialization format identifiers."""
    JSON = "json"
    BINARY = "binary"
    DICT = "dict"


class PrefabStatus(Enum):
    """Lifecycle state of a prefab template."""
    DRAFT = "draft"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    BROKEN = "broken"


# ---------------------------------------------------------------------------
# Math Primitives
# ---------------------------------------------------------------------------

@dataclass
class Vector3:
    """3-component vector for position, scale, and direction."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vector3") -> "Vector3":
        return Vector3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vector3":
        return Vector3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vector3":
        return self.__mul__(scalar)

    def __neg__(self) -> "Vector3":
        return Vector3(-self.x, -self.y, -self.z)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector3):
            return False
        return self.x == other.x and self.y == other.y and self.z == other.z

    def __hash__(self) -> int:
        return hash((self.x, self.y, self.z))

    def length(self) -> float:
        return math.sqrt(self.x * self.x + self.y * self.y + self.z * self.z)

    def length_squared(self) -> float:
        return self.x * self.x + self.y * self.y + self.z * self.z

    def normalized(self) -> "Vector3":
        l = self.length()
        if l == 0:
            return Vector3(0.0, 0.0, 0.0)
        return Vector3(self.x / l, self.y / l, self.z / l)

    def dot(self, other: "Vector3") -> float:
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: "Vector3") -> "Vector3":
        return Vector3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def lerp(self, to: "Vector3", t: float) -> "Vector3":
        t = max(0.0, min(1.0, t))
        return Vector3(
            self.x + (to.x - self.x) * t,
            self.y + (to.y - self.y) * t,
            self.z + (to.z - self.z) * t,
        )

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "z": self.z}


@dataclass
class EulerAngles:
    """Euler angle rotation (pitch, yaw, roll) in radians."""
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0

    def to_quaternion(self) -> "Quaternion":
        return Quaternion.from_euler(self.pitch, self.yaw, self.roll)

    def to_dict(self) -> Dict[str, Any]:
        return {"pitch": self.pitch, "yaw": self.yaw, "roll": self.roll}


@dataclass
class Quaternion:
    """4-component rotation quaternion (x, y, z, w)."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    w: float = 1.0

    @classmethod
    def identity(cls) -> "Quaternion":
        return cls(0.0, 0.0, 0.0, 1.0)

    @classmethod
    def from_euler(cls, pitch: float, yaw: float, roll: float) -> "Quaternion":
        cy = math.cos(yaw * 0.5)
        sy = math.sin(yaw * 0.5)
        cp = math.cos(pitch * 0.5)
        sp = math.sin(pitch * 0.5)
        cr = math.cos(roll * 0.5)
        sr = math.sin(roll * 0.5)
        return cls(
            x=sr * cp * cy - cr * sp * sy,
            y=cr * sp * cy + sr * cp * sy,
            z=cr * cp * sy - sr * sp * cy,
            w=cr * cp * cy + sr * sp * sy,
        )

    def to_euler(self) -> EulerAngles:
        sinr_cosp = 2.0 * (self.w * self.x + self.y * self.z)
        cosr_cosp = 1.0 - 2.0 * (self.x * self.x + self.y * self.y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2.0 * (self.w * self.y - self.z * self.x)
        if abs(sinp) >= 1.0:
            pitch = math.copysign(math.pi / 2.0, sinp)
        else:
            pitch = math.asin(sinp)

        siny_cosp = 2.0 * (self.w * self.z + self.x * self.y)
        cosy_cosp = 1.0 - 2.0 * (self.y * self.y + self.z * self.z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return EulerAngles(pitch=pitch, yaw=yaw, roll=roll)

    def normalized(self) -> "Quaternion":
        magnitude = math.sqrt(self.x ** 2 + self.y ** 2 + self.z ** 2 + self.w ** 2)
        if magnitude == 0:
            return Quaternion.identity()
        return Quaternion(
            x=self.x / magnitude,
            y=self.y / magnitude,
            z=self.z / magnitude,
            w=self.w / magnitude,
        )

    def conjugate(self) -> "Quaternion":
        return Quaternion(x=-self.x, y=-self.y, z=-self.z, w=self.w)

    def __mul__(self, other: "Quaternion") -> "Quaternion":
        return Quaternion(
            x=self.w * other.x + self.x * other.w + self.y * other.z - self.z * other.y,
            y=self.w * other.y - self.x * other.z + self.y * other.w + self.z * other.x,
            z=self.w * other.z + self.x * other.y - self.y * other.x + self.z * other.w,
            w=self.w * other.w - self.x * other.x - self.y * other.y - self.z * self.z,
        )

    def rotate_vector(self, v: Vector3) -> Vector3:
        qv = Quaternion(x=v.x, y=v.y, z=v.z, w=0.0)
        conj = self.conjugate()
        result = self * qv * conj
        return Vector3(x=result.x, y=result.y, z=result.z)

    def to_dict(self) -> Dict[str, Any]:
        return {"x": self.x, "y": self.y, "z": self.z, "w": self.w}


# ---------------------------------------------------------------------------
# Transform3D
# ---------------------------------------------------------------------------

@dataclass
class Transform3D:
    """3D transformation with position, rotation, and scale.

    Maintains local and world-space representations. The world transform
    is computed by composing the local transform with the parent's world
    transform up the hierarchy chain.
    """
    position: Vector3 = field(default_factory=Vector3)
    rotation: Quaternion = field(default_factory=Quaternion.identity)
    scale: Vector3 = field(default_factory=lambda: Vector3(1.0, 1.0, 1.0))
    euler_rotation: EulerAngles = field(default_factory=EulerAngles)

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = Vector3(x, y, z)

    def set_rotation_euler(self, pitch: float, yaw: float, roll: float) -> None:
        self.euler_rotation = EulerAngles(pitch, yaw, roll)
        self.rotation = self.euler_rotation.to_quaternion()

    def set_rotation_quaternion(self, q: Quaternion) -> None:
        self.rotation = q.normalized()
        self.euler_rotation = self.rotation.to_euler()

    def set_scale(self, x: float, y: float, z: float) -> None:
        self.scale = Vector3(x, y, z)

    def get_local_matrix(self) -> List[List[float]]:
        """Compute the local 4x4 transformation matrix."""
        # Scale
        sx, sy, sz = self.scale.x, self.scale.y, self.scale.z
        # Rotation
        q = self.rotation
        xx, yy, zz = q.x * q.x, q.y * q.y, q.z * q.z
        xy, xz, yz = q.x * q.y, q.x * q.z, q.y * q.z
        wx, wy, wz = q.w * q.x, q.w * q.y, q.w * q.z

        return [
            [(1.0 - 2.0 * (yy + zz)) * sx, (2.0 * (xy - wz)) * sy, (2.0 * (xz + wy)) * sz, self.position.x],
            [(2.0 * (xy + wz)) * sx, (1.0 - 2.0 * (xx + zz)) * sy, (2.0 * (yz - wx)) * sz, self.position.y],
            [(2.0 * (xz - wy)) * sx, (2.0 * (yz + wx)) * sy, (1.0 - 2.0 * (xx + yy)) * sz, self.position.z],
            [0.0, 0.0, 0.0, 1.0],
        ]

    def get_world_matrix(self, parent_world: Optional[List[List[float]]] = None) -> List[List[float]]:
        """Compute world matrix by composing with parent world matrix."""
        local = self.get_local_matrix()
        if parent_world is None:
            return local
        return self._multiply_matrices(parent_world, local)

    @staticmethod
    def _multiply_matrices(a: List[List[float]], b: List[List[float]]) -> List[List[float]]:
        result = [[0.0] * 4 for _ in range(4)]
        for i in range(4):
            for j in range(4):
                for k in range(4):
                    result[i][j] += a[i][k] * b[k][j]
        return result

    def look_at(self, target: Vector3, up: Vector3 = None) -> None:
        """Orient the transform to look at a target position."""
        if up is None:
            up = Vector3(0.0, 1.0, 0.0)

        forward = (target - self.position).normalized()
        right = forward.cross(up).normalized()
        corrected_up = right.cross(forward).normalized()

        # Build rotation matrix
        m = [
            [right.x, corrected_up.x, -forward.x, 0.0],
            [right.y, corrected_up.y, -forward.y, 0.0],
            [right.z, corrected_up.z, -forward.z, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]

        # Extract quaternion from rotation matrix
        trace = m[0][0] + m[1][1] + m[2][2]
        if trace > 0.0:
            s = 0.5 / math.sqrt(trace + 1.0)
            self.rotation = Quaternion(
                x=(m[2][1] - m[1][2]) * s,
                y=(m[0][2] - m[2][0]) * s,
                z=(m[1][0] - m[0][1]) * s,
                w=0.25 / s,
            )
        elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
            s = 2.0 * math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2])
            self.rotation = Quaternion(
                x=0.25 * s,
                y=(m[0][1] + m[1][0]) / s,
                z=(m[0][2] + m[2][0]) / s,
                w=(m[2][1] - m[1][2]) / s,
            )
        elif m[1][1] > m[2][2]:
            s = 2.0 * math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2])
            self.rotation = Quaternion(
                x=(m[0][1] + m[1][0]) / s,
                y=0.25 * s,
                z=(m[1][2] + m[2][1]) / s,
                w=(m[0][2] - m[2][0]) / s,
            )
        else:
            s = 2.0 * math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1])
            self.rotation = Quaternion(
                x=(m[0][2] + m[2][0]) / s,
                y=(m[1][2] + m[2][1]) / s,
                z=0.25 * s,
                w=(m[1][0] - m[0][1]) / s,
            )
        self.rotation = self.rotation.normalized()
        self.euler_rotation = self.rotation.to_euler()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": self.position.to_dict(),
            "rotation": self.rotation.to_dict(),
            "scale": self.scale.to_dict(),
            "euler": self.euler_rotation.to_dict(),
        }


# ---------------------------------------------------------------------------
# GraphNode
# ---------------------------------------------------------------------------

@dataclass
class GraphNode:
    """A node in the hierarchical scene graph.

    Nodes form a tree structure where each node has a parent and zero or
    more children. Each node carries a local Transform3D, a computed world
    transform, name, tags, and a dictionary of attached components.
    """
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Node"
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    local_transform: Transform3D = field(default_factory=Transform3D)
    world_transform: Transform3D = field(default_factory=Transform3D)
    is_active: bool = True
    tags: List[str] = field(default_factory=list)
    components: Dict[str, Any] = field(default_factory=dict)
    signal_handlers: Dict[str, List[Callable[[GraphNode, Any], None]]] = field(
        default_factory=dict
    )
    _dirty: bool = True

    def connect(self, signal: NodeSignal, handler: Callable[[GraphNode, Any], None]) -> None:
        """Register a handler for a node signal."""
        key = signal.value
        self.signal_handlers.setdefault(key, []).append(handler)

    def disconnect(self, signal: NodeSignal, handler: Callable[[GraphNode, Any], None]) -> None:
        """Unregister a signal handler."""
        key = signal.value
        handlers = self.signal_handlers.get(key, [])
        if handler in handlers:
            handlers.remove(handler)

    def emit(self, signal: NodeSignal, data: Any = None) -> None:
        """Emit a signal to all registered handlers."""
        key = signal.value
        for handler in self.signal_handlers.get(key, []):
            try:
                handler(self, data)
            except Exception:
                pass

    def attach_component(self, component_type: str, component_data: Any) -> None:
        """Attach a component to this node."""
        self.components[component_type] = component_data
        self.emit(NodeSignal.COMPONENT_ATTACHED, {"type": component_type})

    def detach_component(self, component_type: str) -> Optional[Any]:
        """Remove a component from this node."""
        removed = self.components.pop(component_type, None)
        if removed is not None:
            self.emit(NodeSignal.COMPONENT_DETACHED, {"type": component_type})
        return removed

    def get_component(self, component_type: str) -> Optional[Any]:
        """Get a component by type."""
        return self.components.get(component_type)

    def has_component(self, component_type: str) -> bool:
        """Check if a component is attached."""
        return component_type in self.components

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "parent_id": self.parent_id,
            "children": list(self.children),
            "local_transform": self.local_transform.to_dict(),
            "world_transform": self.world_transform.to_dict(),
            "is_active": self.is_active,
            "tags": list(self.tags),
            "component_types": list(self.components.keys()),
        }


# ---------------------------------------------------------------------------
# StarPath
# ---------------------------------------------------------------------------

@dataclass
class StarPath:
    """Path-based node addressing for the scene graph.

    Supports absolute paths (/root/player/weapon), relative paths
    (../sibling/child), wildcard matching (*, //), and regex-based
    node selection. Provides path resolution against a scene graph
    context with validation and normalization.
    """
    path_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    original: str = ""
    segments: List[str] = field(default_factory=list)
    is_absolute: bool = False
    match_mode: PathMatchMode = PathMatchMode.EXACT

    @classmethod
    def parse(cls, path_str: str) -> "StarPath":
        """Parse a path string into a StarPath object."""
        is_absolute = path_str.startswith("/")
        cleaned = path_str.strip()
        if is_absolute:
            cleaned = cleaned[1:]

        segments = []
        for seg in cleaned.split("/"):
            seg = seg.strip()
            if seg:
                segments.append(seg)

        match_mode = PathMatchMode.EXACT
        if "//" in path_str:
            match_mode = PathMatchMode.RECURSIVE
        elif "*" in path_str or "?" in path_str:
            match_mode = PathMatchMode.WILDCARD

        return cls(
            original=path_str,
            segments=segments,
            is_absolute=is_absolute,
            match_mode=match_mode,
        )

    def resolve(self, current_node: GraphNode, root: GraphNode, nodes: Dict[str, GraphNode]) -> List[GraphNode]:
        """Resolve this path against a scene graph context.

        Args:
            current_node: The node from which relative paths start.
            root: The root node for absolute paths.
            nodes: All nodes keyed by node_id.

        Returns:
            List of matching GraphNode instances.
        """
        if self.is_absolute:
            context = root
        else:
            context = current_node

        if not self.segments:
            return [context]

        results = [context]
        for seg in self.segments:
            results = self._resolve_segment(results, seg, nodes)

        return results

    def _resolve_segment(
        self, contexts: List[GraphNode], segment: str, nodes: Dict[str, GraphNode]
    ) -> List[GraphNode]:
        new_results: List[GraphNode] = []

        if segment == "..":
            for ctx in contexts:
                parent = nodes.get(ctx.parent_id) if ctx.parent_id else None
                if parent:
                    new_results.append(parent)
            return new_results

        if segment == ".":
            return list(contexts)

        if segment == "*":
            for ctx in contexts:
                for child_id in ctx.children:
                    child = nodes.get(child_id)
                    if child:
                        new_results.append(child)
            return new_results

        if segment == "**":
            for ctx in contexts:
                new_results.extend(self._collect_descendants(ctx, nodes))
            return new_results

        for ctx in contexts:
            for child_id in ctx.children:
                child = nodes.get(child_id)
                if child and child.name == segment:
                    new_results.append(child)

        return new_results

    def _collect_descendants(self, node: GraphNode, nodes: Dict[str, GraphNode]) -> List[GraphNode]:
        result: List[GraphNode] = []
        for child_id in node.children:
            child = nodes.get(child_id)
            if child:
                result.append(child)
                result.extend(self._collect_descendants(child, nodes))
        return result

    def validate(self) -> bool:
        """Check if the path follows valid syntax."""
        if not self.original:
            return False
        illegal = {"<", ">", "|", "\\", "\"", "'"}
        for ch in illegal:
            if ch in self.original:
                return False
        return True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path_id": self.path_id,
            "original": self.original,
            "segments": list(self.segments),
            "is_absolute": self.is_absolute,
            "match_mode": self.match_mode.value,
        }


# ---------------------------------------------------------------------------
# Data Classes for Serialization and Prefabs
# ---------------------------------------------------------------------------

@dataclass
class SerializedScene:
    """Container for serialized scene data."""
    scene_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled"
    format_version: str = "1.0"
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    root_node_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "format_version": self.format_version,
            "nodes": list(self.nodes),
            "root_node_id": self.root_node_id,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PrefabOverride:
    """A tracked override on a prefab instance."""
    property_path: str = ""
    original_value: Any = None
    overridden_value: Any = None
    applied: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_path": self.property_path,
            "applied": self.applied,
        }


@dataclass
class ConstellationTemplate:
    """A reusable entity template (prefab) in the constellation library.

    Templates define a node hierarchy with default transforms, tags,
    and component configurations that can be instantiated into a scene
    graph. Supports variant inheritance and override tracking.
    """
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: str = "general"
    description: str = ""
    root_node: Optional[GraphNode] = None
    variant_of: Optional[str] = None
    status: PrefabStatus = PrefabStatus.DRAFT
    tags: List[str] = field(default_factory=list)
    overrides: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "description": self.description,
            "variant_of": self.variant_of,
            "status": self.status.value,
            "tags": list(self.tags),
            "override_count": len(self.overrides),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PrefabInstanceData:
    """Runtime data for an instantiated prefab."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    template_id: str = ""
    root_node_id: str = ""
    spawned_node_ids: List[str] = field(default_factory=list)
    overrides: List[PrefabOverride] = field(default_factory=list)
    spawned_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "root_node_id": self.root_node_id,
            "spawned_count": len(self.spawned_node_ids),
            "override_count": len(self.overrides),
            "spawned_at": self.spawned_at,
        }


# ---------------------------------------------------------------------------
# NebulaSerializer
# ---------------------------------------------------------------------------

class NebulaSerializer:
    """Scene persistence engine for the SparkLabs scene graph.

    Handles serialization and deserialization of scene graphs to JSON
    dictionaries and binary format. Supports format version migration
    and partial scene loading by node path.
    """

    _instance: Optional["NebulaSerializer"] = None
    _lock: threading.RLock = threading.RLock()

    CURRENT_VERSION: str = "2.0"
    MIGRATIONS: Dict[str, Dict[str, Any]] = {
        "1.0": {"nodes": "add_metadata", "root": "rename_root_id"},
    }

    def __new__(cls) -> "NebulaSerializer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "NebulaSerializer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._serialized_scenes: Dict[str, SerializedScene] = {}
        self._serialization_count: int = 0
        self._deserialization_count: int = 0

    def serialize_scene(
        self,
        root: GraphNode,
        nodes: Dict[str, GraphNode],
        scene_name: str = "Scene",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SerializedScene:
        """Serialize a scene graph to a SerializedScene container.

        Args:
            root: The root node of the scene graph.
            nodes: All nodes keyed by node_id.
            scene_name: Name for the serialized scene.
            metadata: Optional metadata dictionary.

        Returns:
            A SerializedScene container.
        """
        serialized_nodes = []
        for node_id, node in nodes.items():
            serialized_nodes.append(node.to_dict())

        scene = SerializedScene(
            name=scene_name,
            format_version=self.CURRENT_VERSION,
            nodes=serialized_nodes,
            root_node_id=root.node_id,
            metadata=metadata or {},
        )
        self._serialized_scenes[scene.scene_id] = scene
        self._serialization_count += 1
        return scene

    def serialize_to_dict(
        self,
        root: GraphNode,
        nodes: Dict[str, GraphNode],
        scene_name: str = "Scene",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Serialize a scene graph to a plain dictionary."""
        scene = self.serialize_scene(root, nodes, scene_name, metadata)
        return scene.to_dict()

    def serialize_to_binary(
        self,
        root: GraphNode,
        nodes: Dict[str, GraphNode],
        scene_name: str = "Scene",
    ) -> bytes:
        """Serialize a scene graph to a compact binary format.

        Binary layout:
            - 4 bytes: magic number (0x534C5347 = "SLSG")
            - 2 bytes: version major.minor
            - 4 bytes: node count (uint32)
            - For each node:
                - 16 bytes: node_id (raw hex)
                - 2 bytes: name length (uint16)
                - N bytes: name (UTF-8)
                - 16 bytes: parent_id (raw hex, 0-filled if none)
                - 4 bytes: child count (uint32)
                - For each child: 16 bytes child_id
                - 12 bytes: position (3x float32)
                - 16 bytes: rotation (4x float32)
                - 12 bytes: scale (3x float32)
                - 1 byte: is_active flag
                - 2 bytes: tag count (uint16)
                - For each tag: 2 bytes length + UTF-8 data
                - 2 bytes: component count (uint16)
                - For each component: 2 bytes type length + UTF-8 + 4 bytes data length + data
        """
        magic = b"\x53\x4C\x53\x47"  # "SLSG"
        version = b"\x02\x00"
        node_count = len(nodes)
        buf = bytearray()
        buf.extend(magic)
        buf.extend(version)
        buf.extend(struct.pack("<I", node_count))

        node_list = list(nodes.values())
        for node in node_list:
            # Node ID (16 bytes)
            nid_bytes = bytes.fromhex(node.node_id)
            buf.extend(nid_bytes[:16].ljust(16, b"\x00"))

            # Name
            name_bytes = node.name.encode("utf-8")
            buf.extend(struct.pack("<H", len(name_bytes)))
            buf.extend(name_bytes)

            # Parent ID
            pid_bytes = bytes.fromhex(node.parent_id) if node.parent_id else b"\x00" * 16
            buf.extend(pid_bytes[:16].ljust(16, b"\x00"))

            # Children
            buf.extend(struct.pack("<I", len(node.children)))
            for child_id in node.children:
                cid_bytes = bytes.fromhex(child_id)
                buf.extend(cid_bytes[:16].ljust(16, b"\x00"))

            # Position
            buf.extend(struct.pack("<fff",
                node.local_transform.position.x,
                node.local_transform.position.y,
                node.local_transform.position.z,
            ))

            # Rotation (quaternion)
            buf.extend(struct.pack("<ffff",
                node.local_transform.rotation.x,
                node.local_transform.rotation.y,
                node.local_transform.rotation.z,
                node.local_transform.rotation.w,
            ))

            # Scale
            buf.extend(struct.pack("<fff",
                node.local_transform.scale.x,
                node.local_transform.scale.y,
                node.local_transform.scale.z,
            ))

            # Active flag
            buf.extend(b"\x01" if node.is_active else b"\x00")

            # Tags
            buf.extend(struct.pack("<H", len(node.tags)))
            for tag in node.tags:
                tag_bytes = tag.encode("utf-8")
                buf.extend(struct.pack("<H", len(tag_bytes)))
                buf.extend(tag_bytes)

            # Components
            buf.extend(struct.pack("<H", len(node.components)))
            for comp_type, comp_data in node.components.items():
                type_bytes = comp_type.encode("utf-8")
                buf.extend(struct.pack("<H", len(type_bytes)))
                buf.extend(type_bytes)
                # Component data as JSON
                import json
                data_bytes = json.dumps(comp_data if isinstance(comp_data, dict) else str(comp_data)).encode("utf-8")
                buf.extend(struct.pack("<I", len(data_bytes)))
                buf.extend(data_bytes)

        self._serialization_count += 1
        return bytes(buf)

    def deserialize_scene(
        self,
        data: Dict[str, Any],
        scene_name: Optional[str] = None,
    ) -> Tuple[GraphNode, Dict[str, GraphNode]]:
        """Deserialize a scene from a dictionary.

        Args:
            data: Serialized scene dictionary.
            scene_name: Optional override for scene name.

        Returns:
            Tuple of (root_node, all_nodes_dict).
        """
        format_version = data.get("format_version", "1.0")
        migrated = self._migrate(data, format_version)

        nodes: Dict[str, GraphNode] = {}
        for node_dict in migrated.get("nodes", []):
            node = self._deserialize_node(node_dict)
            nodes[node.node_id] = node

        root_id = migrated.get("root_node_id", "")
        root = nodes.get(root_id)
        if not root and nodes:
            root = list(nodes.values())[0]

        self._deserialization_count += 1
        return root, nodes

    def deserialize_from_binary(self, data: bytes) -> Tuple[GraphNode, Dict[str, GraphNode]]:
        """Deserialize a scene from binary format.

        Args:
            data: Binary scene data.

        Returns:
            Tuple of (root_node, all_nodes_dict).
        """
        import json
        offset = 0

        # Magic
        magic = data[offset:offset + 4]
        offset += 4
        if magic != b"\x53\x4C\x53\x47":
            raise ValueError("Invalid binary scene data: bad magic number")

        # Version
        version = data[offset:offset + 2]
        offset += 2

        # Node count
        node_count = struct.unpack_from("<I", data, offset)[0]
        offset += 4

        nodes: Dict[str, GraphNode] = {}
        root_id = ""

        for _ in range(node_count):
            # Node ID
            nid_bytes = data[offset:offset + 16]
            offset += 16
            node_id = nid_bytes.rstrip(b"\x00").hex()

            # Name
            name_len = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            name = data[offset:offset + name_len].decode("utf-8")
            offset += name_len

            # Parent ID
            pid_bytes = data[offset:offset + 16]
            offset += 16
            parent_id = pid_bytes.rstrip(b"\x00").hex() if pid_bytes.rstrip(b"\x00") else None

            # Children
            child_count = struct.unpack_from("<I", data, offset)[0]
            offset += 4
            children = []
            for _ in range(child_count):
                cid_bytes = data[offset:offset + 16]
                offset += 16
                children.append(cid_bytes.rstrip(b"\x00").hex())

            # Position
            px, py, pz = struct.unpack_from("<fff", data, offset)
            offset += 12

            # Rotation
            rx, ry, rz, rw = struct.unpack_from("<ffff", data, offset)
            offset += 16

            # Scale
            sx, sy, sz = struct.unpack_from("<fff", data, offset)
            offset += 12

            # Active
            is_active = data[offset] == 1
            offset += 1

            # Tags
            tag_count = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            tags = []
            for _ in range(tag_count):
                tlen = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                tags.append(data[offset:offset + tlen].decode("utf-8"))
                offset += tlen

            # Components
            comp_count = struct.unpack_from("<H", data, offset)[0]
            offset += 2
            components = {}
            for _ in range(comp_count):
                ctlen = struct.unpack_from("<H", data, offset)[0]
                offset += 2
                comp_type = data[offset:offset + ctlen].decode("utf-8")
                offset += ctlen
                cdlen = struct.unpack_from("<I", data, offset)[0]
                offset += 4
                cd_bytes = data[offset:offset + cdlen]
                offset += cdlen
                try:
                    components[comp_type] = json.loads(cd_bytes.decode("utf-8"))
                except Exception:
                    components[comp_type] = cd_bytes.decode("utf-8")

            transform = Transform3D(
                position=Vector3(px, py, pz),
                rotation=Quaternion(rx, ry, rz, rw),
                scale=Vector3(sx, sy, sz),
            )

            node = GraphNode(
                node_id=node_id,
                name=name,
                parent_id=parent_id,
                children=children,
                local_transform=transform,
                is_active=is_active,
                tags=tags,
                components=components,
            )
            nodes[node_id] = node

            if parent_id is None:
                root_id = node_id

        root = nodes.get(root_id)
        if not root and nodes:
            root = list(nodes.values())[0]

        self._deserialization_count += 1
        return root, nodes

    def _deserialize_node(self, node_dict: Dict[str, Any]) -> GraphNode:
        """Create a GraphNode from a serialized node dictionary."""
        local_t = node_dict.get("local_transform", {})
        transform = Transform3D(
            position=Vector3(
                local_t.get("position", {}).get("x", 0.0),
                local_t.get("position", {}).get("y", 0.0),
                local_t.get("position", {}).get("z", 0.0),
            ),
            rotation=Quaternion(
                local_t.get("rotation", {}).get("x", 0.0),
                local_t.get("rotation", {}).get("y", 0.0),
                local_t.get("rotation", {}).get("z", 0.0),
                local_t.get("rotation", {}).get("w", 1.0),
            ),
            scale=Vector3(
                local_t.get("scale", {}).get("x", 1.0),
                local_t.get("scale", {}).get("y", 1.0),
                local_t.get("scale", {}).get("z", 1.0),
            ),
        )

        return GraphNode(
            node_id=node_dict.get("node_id", uuid.uuid4().hex),
            name=node_dict.get("name", "Node"),
            parent_id=node_dict.get("parent_id"),
            children=node_dict.get("children", []),
            local_transform=transform,
            is_active=node_dict.get("is_active", True),
            tags=node_dict.get("tags", []),
        )

    def _migrate(self, data: Dict[str, Any], from_version: str) -> Dict[str, Any]:
        """Migrate serialized data from an older format version."""
        if from_version == "1.0":
            return self._migrate_v1_to_v2(data)
        return data

    def _migrate_v1_to_v2(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from version 1.0 to 2.0."""
        if "metadata" not in data:
            data["metadata"] = {}
        if "root_node_id" not in data:
            # Old format used "root_id"
            data["root_node_id"] = data.get("root_id", "")
        data["format_version"] = "2.0"
        return data

    def partial_load(
        self,
        data: Dict[str, Any],
        path: StarPath,
    ) -> Tuple[Optional[GraphNode], Dict[str, GraphNode]]:
        """Load only a portion of a scene specified by a StarPath.

        Args:
            data: Serialized scene dictionary.
            path: StarPath identifying the subtree to load.

        Returns:
            Tuple of (subtree_root, loaded_nodes).
        """
        root, all_nodes = self.deserialize_scene(data)
        resolved = path.resolve(root, root, all_nodes)
        if not resolved:
            return None, {}

        subtree_root = resolved[0]
        collected = self._collect_subtree(subtree_root, all_nodes)
        return subtree_root, collected

    def _collect_subtree(self, root: GraphNode, all_nodes: Dict[str, GraphNode]) -> Dict[str, GraphNode]:
        """Collect all nodes in the subtree rooted at the given node."""
        result: Dict[str, GraphNode] = {root.node_id: root}
        for child_id in root.children:
            child = all_nodes.get(child_id)
            if child:
                result.update(self._collect_subtree(child, all_nodes))
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "serialization_count": self._serialization_count,
            "deserialization_count": self._deserialization_count,
            "stored_scenes": len(self._serialized_scenes),
            "current_format_version": self.CURRENT_VERSION,
        }


# ---------------------------------------------------------------------------
# ConstellationLibrary
# ---------------------------------------------------------------------------

class ConstellationLibrary:
    """Prefab template library for reusable entity templates.

    Manages a catalog of ConstellationTemplate prefabs with support for
    variant inheritance, override tracking, nesting, and batch instantiation
    into a scene graph. Templates are deep-copied on instantiation so that
    runtime instances remain independent of their source templates.
    """

    _instance: Optional["ConstellationLibrary"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ConstellationLibrary":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "ConstellationLibrary":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._templates: Dict[str, ConstellationTemplate] = {}
        self._instances: Dict[str, PrefabInstanceData] = {}
        self._category_index: Dict[str, Set[str]] = {}
        self._tag_index: Dict[str, Set[str]] = {}
        self._instantiation_count: int = 0

    def create_template(
        self,
        name: str,
        root_node: GraphNode,
        category: str = "general",
        description: str = "",
        tags: Optional[List[str]] = None,
    ) -> ConstellationTemplate:
        """Create a new prefab template from a node hierarchy.

        Args:
            name: Template name.
            root_node: The root GraphNode of the template.
            category: Category for organization.
            description: Human-readable description.
            tags: Search tags.

        Returns:
            The created ConstellationTemplate.
        """
        template = ConstellationTemplate(
            name=name,
            category=category,
            description=description,
            root_node=copy.deepcopy(root_node),
            tags=tags or [],
            status=PrefabStatus.DRAFT,
        )
        self._templates[template.template_id] = template
        self._category_index.setdefault(category, set()).add(template.template_id)
        for tag in (tags or []):
            self._tag_index.setdefault(tag, set()).add(template.template_id)
        return template

    def create_variant(
        self,
        parent_template_id: str,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
        description: str = "",
    ) -> Optional[ConstellationTemplate]:
        """Create a variant of an existing template.

        Variants inherit the parent template's structure and can override
        specific properties without modifying the original.

        Args:
            parent_template_id: The parent template to derive from.
            name: Name for the variant.
            overrides: Property overrides to apply.
            description: Human-readable description.

        Returns:
            The variant ConstellationTemplate, or None if parent not found.
        """
        parent = self._templates.get(parent_template_id)
        if not parent or not parent.root_node:
            return None

        variant_root = copy.deepcopy(parent.root_node)
        variant = ConstellationTemplate(
            name=name,
            category=parent.category,
            description=description or f"Variant of {parent.name}",
            root_node=variant_root,
            variant_of=parent_template_id,
            tags=list(parent.tags),
            overrides=overrides or {},
            status=PrefabStatus.DRAFT,
        )
        self._templates[variant.template_id] = variant
        self._category_index.setdefault(variant.category, set()).add(variant.template_id)
        for tag in variant.tags:
            self._tag_index.setdefault(tag, set()).add(variant.template_id)
        return variant

    def get_template(self, template_id: str) -> Optional[ConstellationTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def find_by_name(self, name: str) -> List[ConstellationTemplate]:
        """Find templates by name."""
        return [t for t in self._templates.values() if t.name == name]

    def find_by_category(self, category: str) -> List[ConstellationTemplate]:
        """Find templates by category."""
        template_ids = self._category_index.get(category, set())
        return [self._templates[tid] for tid in template_ids if tid in self._templates]

    def find_by_tag(self, tag: str) -> List[ConstellationTemplate]:
        """Find templates by tag."""
        template_ids = self._tag_index.get(tag, set())
        return [self._templates[tid] for tid in template_ids if tid in self._templates]

    def list_templates(self) -> List[ConstellationTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def remove_template(self, template_id: str) -> bool:
        """Remove a template from the library."""
        template = self._templates.pop(template_id, None)
        if not template:
            return False
        cat_set = self._category_index.get(template.category, set())
        cat_set.discard(template_id)
        for tag in template.tags:
            tag_set = self._tag_index.get(tag, set())
            tag_set.discard(template_id)
        return True

    def instantiate(
        self,
        template_id: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphNode]:
        """Instantiate a prefab template, producing a deep-copied node tree.

        Args:
            template_id: The template to instantiate.
            overrides: Optional property overrides for this instance.

        Returns:
            The root GraphNode of the instantiated tree, or None.
        """
        template = self._templates.get(template_id)
        if not template or not template.root_node:
            return None

        root = copy.deepcopy(template.root_node)
        self._remap_ids(root)
        self._apply_overrides(root, overrides or {})

        instance = PrefabInstanceData(
            template_id=template_id,
            root_node_id=root.node_id,
        )
        self._instances[instance.instance_id] = instance
        self._instantiation_count += 1

        return root

    def instantiate_into_scene(
        self,
        scene_graph: "SceneGraphEngine",
        template_id: str,
        parent_id: Optional[str] = None,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphNode]:
        """Instantiate a prefab directly into the scene graph.

        Args:
            scene_graph: The target SceneGraphEngine.
            template_id: The template to instantiate.
            parent_id: Optional parent node ID to attach to.
            overrides: Optional property overrides.

        Returns:
            The root node added to the scene graph, or None.
        """
        root = self.instantiate(template_id, overrides)
        if not root:
            return None

        # Register all nodes in the scene graph
        scene_graph._register_subtree(root)

        if parent_id:
            scene_graph.set_parent(root.node_id, parent_id)

        return root

    def _remap_ids(self, node: GraphNode) -> None:
        """Assign new IDs to all nodes in a subtree."""
        old_id = node.node_id
        node.node_id = uuid.uuid4().hex
        for child_id in node.children:
            for template in self._templates.values():
                if template.root_node and template.root_node.node_id == child_id:
                    self._remap_ids(template.root_node)
                    child_id = template.root_node.node_id
                    break
        for child_id in node.children:
            child = self._find_in_instances(child_id)
            if child:
                self._remap_ids(child)

    def _find_in_instances(self, node_id: str) -> Optional[GraphNode]:
        """Find a node by ID across all instantiated trees."""
        for inst in self._instances.values():
            if inst.root_node_id == node_id:
                return None  # Would need scene graph reference
        return None

    def _apply_overrides(self, node: GraphNode, overrides: Dict[str, Any]) -> None:
        """Apply property overrides to a node tree."""
        if node.name in overrides:
            node_overrides = overrides[node.name]
            if isinstance(node_overrides, dict):
                if "position" in node_overrides:
                    p = node_overrides["position"]
                    node.local_transform.set_position(p.get("x", 0), p.get("y", 0), p.get("z", 0))
                if "rotation" in node_overrides:
                    r = node_overrides["rotation"]
                    node.local_transform.set_rotation_quaternion(
                        Quaternion(r.get("x", 0), r.get("y", 0), r.get("z", 0), r.get("w", 1))
                    )
                if "scale" in node_overrides:
                    s = node_overrides["scale"]
                    node.local_transform.set_scale(s.get("x", 1), s.get("y", 1), s.get("z", 1))
                if "tags" in node_overrides:
                    node.tags = list(node_overrides["tags"])
                if "is_active" in node_overrides:
                    node.is_active = node_overrides["is_active"]

    def get_instance_data(self, instance_id: str) -> Optional[PrefabInstanceData]:
        """Get a prefab instance record by ID."""
        return self._instances.get(instance_id)

    def update_template(self, template_id: str, updates: Dict[str, Any]) -> Optional[ConstellationTemplate]:
        """Update a template's properties."""
        template = self._templates.get(template_id)
        if not template:
            return None
        for key, value in updates.items():
            if hasattr(template, key):
                setattr(template, key, value)
        template.updated_at = _time_module.time()
        return template

    def publish_template(self, template_id: str) -> bool:
        """Publish a draft template."""
        template = self._templates.get(template_id)
        if not template:
            return False
        template.status = PrefabStatus.PUBLISHED
        return True

    def get_categories(self) -> List[str]:
        """Get all template categories."""
        return sorted(self._category_index.keys())

    def get_stats(self) -> Dict[str, Any]:
        category_counts = {}
        for t in self._templates.values():
            cat = t.category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        return {
            "total_templates": len(self._templates),
            "total_instances": len(self._instances),
            "total_instantiations": self._instantiation_count,
            "variants": sum(1 for t in self._templates.values() if t.variant_of),
            "categories": len(self._category_index),
            "category_breakdown": category_counts,
            "published": sum(1 for t in self._templates.values() if t.status == PrefabStatus.PUBLISHED),
        }


# ---------------------------------------------------------------------------
# SceneGraphEngine
# ---------------------------------------------------------------------------

class SceneGraphEngine:
    """Hierarchical scene graph manager for the SparkLabs engine.

    Maintains a tree of GraphNode instances rooted at a single root node.
    Provides traversal, lookup, serialization, and dirty flag propagation.
    Uses a singleton pattern with double-checked locking for thread safety.

    Usage:
        sg = get_scene_graph()
        root = sg.get_root()
        player = sg.create_node("Player", parent_id=root.node_id)
        sg.set_transform(player.node_id, position=(10, 0, 5))
        found = sg.find_by_name("Player")
    """

    _instance: Optional["SceneGraphEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "SceneGraphEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SceneGraphEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True
        self._nodes: Dict[str, GraphNode] = {}
        self._root_id: str = ""
        self._tag_index: Dict[str, Set[str]] = {}
        self._name_index: Dict[str, Set[str]] = {}
        self._dirty_set: Set[str] = set()
        self._serializer: NebulaSerializer = NebulaSerializer.get_instance()
        self._prefab_library: ConstellationLibrary = ConstellationLibrary.get_instance()
        self._create_root()

    # ------------------------------------------------------------------
    # Root Management
    # ------------------------------------------------------------------

    def _create_root(self) -> None:
        """Create the root scene graph node."""
        root = GraphNode(
            name="__Root__",
        )
        self._nodes[root.node_id] = root
        self._root_id = root.node_id

    def get_root(self) -> GraphNode:
        """Get the root node of the scene graph."""
        return self._nodes[self._root_id]

    def get_root_id(self) -> str:
        """Get the root node's ID."""
        return self._root_id

    # ------------------------------------------------------------------
    # Node Creation and Removal
    # ------------------------------------------------------------------

    def create_node(
        self,
        name: str,
        parent_id: Optional[str] = None,
        transform: Optional[Transform3D] = None,
        tags: Optional[List[str]] = None,
    ) -> GraphNode:
        """Create a new node in the scene graph.

        Args:
            name: Node name.
            parent_id: ID of the parent node. Defaults to root.
            transform: Optional initial Transform3D.
            tags: Optional tag list.

        Returns:
            The created GraphNode.
        """
        node = GraphNode(
            name=name,
            parent_id=parent_id or self._root_id,
            local_transform=transform or Transform3D(),
            tags=tags or [],
        )

        self._nodes[node.node_id] = node
        self._index_node(node)

        # Attach to parent
        parent = self._nodes.get(node.parent_id)
        if parent:
            parent.children.append(node.node_id)
            parent.emit(NodeSignal.CHILD_ADDED, {"child_id": node.node_id})

        self._mark_dirty(node.node_id)
        self._update_world_transform(node.node_id)

        return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all descendants from the scene graph.

        Args:
            node_id: ID of the node to remove.

        Returns:
            True if removed, False if not found or is root.
        """
        if node_id == self._root_id:
            return False

        node = self._nodes.get(node_id)
        if not node:
            return False

        # Remove children recursively
        for child_id in list(node.children):
            self.remove_node(child_id)

        # Detach from parent
        parent = self._nodes.get(node.parent_id)
        if parent and node_id in parent.children:
            parent.children.remove(node_id)
            parent.emit(NodeSignal.CHILD_REMOVED, {"child_id": node_id})

        self._unindex_node(node)
        self._dirty_set.discard(node_id)
        del self._nodes[node_id]
        return True

    def _register_subtree(self, root_node: GraphNode) -> None:
        """Register a complete subtree of nodes into the scene graph.

        Recursively adds all nodes in the subtree, indexing them and
        computing world transforms.

        Args:
            root_node: Root of the subtree to register.
        """
        self._nodes[root_node.node_id] = root_node
        self._index_node(root_node)
        self._dirty_set.add(root_node.node_id)

        for child_id in root_node.children:
            child = self._nodes.get(child_id)
            if child:
                continue
            # Child might be a new node from prefab instantiation
            # We don't have the child object here, so we skip
            pass

        self._update_world_transform(root_node.node_id)

    def _register_subtree_recursive(self, node: GraphNode) -> None:
        """Recursively register a node and all its descendants."""
        self._nodes[node.node_id] = node
        self._index_node(node)
        self._dirty_set.add(node.node_id)
        for child_id in node.children:
            child = self._nodes.get(child_id)
            if child:
                self._register_subtree_recursive(child)

    # ------------------------------------------------------------------
    # Hierarchy Operations
    # ------------------------------------------------------------------

    def set_parent(self, node_id: str, new_parent_id: str) -> bool:
        """Change the parent of a node.

        Args:
            node_id: ID of the node to reparent.
            new_parent_id: ID of the new parent.

        Returns:
            True if successful, False if either node not found.
        """
        node = self._nodes.get(node_id)
        new_parent = self._nodes.get(new_parent_id)
        if not node or not new_parent:
            return False

        # Prevent circular references
        if self._is_ancestor(node_id, new_parent_id):
            return False

        # Detach from old parent
        old_parent = self._nodes.get(node.parent_id)
        if old_parent and node_id in old_parent.children:
            old_parent.children.remove(node_id)

        # Attach to new parent
        node.parent_id = new_parent_id
        new_parent.children.append(node_id)

        node.emit(NodeSignal.PARENT_CHANGED, {"old_parent": old_parent.node_id if old_parent else None, "new_parent": new_parent_id})
        self._mark_dirty(node_id)

        return True

    def _is_ancestor(self, potential_ancestor_id: str, node_id: str) -> bool:
        """Check if potential_ancestor_id is an ancestor of node_id."""
        current_id = node_id
        while current_id:
            if current_id == potential_ancestor_id:
                return True
            node = self._nodes.get(current_id)
            if not node:
                break
            current_id = node.parent_id
        return False

    def get_children(self, node_id: str) -> List[GraphNode]:
        """Get all direct children of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def get_parent(self, node_id: str) -> Optional[GraphNode]:
        """Get the parent of a node."""
        node = self._nodes.get(node_id)
        if not node or not node.parent_id:
            return None
        return self._nodes.get(node.parent_id)

    def get_descendants(self, node_id: str) -> List[GraphNode]:
        """Get all descendants of a node recursively."""
        result: List[GraphNode] = []
        node = self._nodes.get(node_id)
        if not node:
            return result
        for child_id in node.children:
            child = self._nodes.get(child_id)
            if child:
                result.append(child)
                result.extend(self.get_descendants(child_id))
        return result

    def get_ancestors(self, node_id: str) -> List[GraphNode]:
        """Get the ancestor chain from root to the node's parent."""
        result: List[GraphNode] = []
        current_id = self._nodes.get(node_id)
        if not current_id:
            return result
        while current_id.parent_id:
            parent = self._nodes.get(current_id.parent_id)
            if not parent:
                break
            result.insert(0, parent)
            current_id = parent
        return result

    # ------------------------------------------------------------------
    # Transform Operations
    # ------------------------------------------------------------------

    def set_transform(
        self,
        node_id: str,
        position: Optional[Union[Vector3, Tuple[float, float, float]]] = None,
        rotation: Optional[Quaternion] = None,
        scale: Optional[Union[Vector3, Tuple[float, float, float]]] = None,
        euler: Optional[Union[EulerAngles, Tuple[float, float, float]]] = None,
    ) -> bool:
        """Set the local transform of a node.

        Args:
            node_id: ID of the node.
            position: New position as Vector3 or (x, y, z).
            rotation: New rotation as Quaternion.
            scale: New scale as Vector3 or (x, y, z).
            euler: New rotation as EulerAngles or (pitch, yaw, roll).

        Returns:
            True if the node was found and updated.
        """
        node = self._nodes.get(node_id)
        if not node:
            return False

        if position is not None:
            if isinstance(position, tuple):
                node.local_transform.set_position(*position)
            else:
                node.local_transform.position = position

        if euler is not None:
            if isinstance(euler, tuple):
                node.local_transform.set_rotation_euler(*euler)
            else:
                node.local_transform.set_rotation_euler(euler.pitch, euler.yaw, euler.roll)

        if rotation is not None:
            node.local_transform.set_rotation_quaternion(rotation)

        if scale is not None:
            if isinstance(scale, tuple):
                node.local_transform.set_scale(*scale)
            else:
                node.local_transform.scale = scale

        node.emit(NodeSignal.TRANSFORM_CHANGED, None)
        self._mark_dirty(node_id)
        return True

    def get_world_transform(self, node_id: str) -> Optional[Transform3D]:
        """Get the computed world transform of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return None
        if node_id in self._dirty_set:
            self._update_world_transform(node_id)
        return node.world_transform

    def _mark_dirty(self, node_id: str) -> None:
        """Mark a node and all its descendants as dirty."""
        self._dirty_set.add(node_id)
        node = self._nodes.get(node_id)
        if node:
            for child_id in node.children:
                self._mark_dirty(child_id)

    def _update_world_transform(self, node_id: str) -> None:
        """Recalculate the world transform for a node."""
        node = self._nodes.get(node_id)
        if not node:
            return

        parent = self._nodes.get(node.parent_id)
        if parent:
            parent_world = self.get_world_transform(parent.node_id)
            if parent_world:
                parent_matrix = parent_world.get_world_matrix()
                node.world_transform = Transform3D(
                    position=self._transform_point(node.local_transform.position, parent_matrix),
                    rotation=Quaternion(
                        x=node.local_transform.rotation.x,
                        y=node.local_transform.rotation.y,
                        z=node.local_transform.rotation.z,
                        w=node.local_transform.rotation.w,
                    ),
                    scale=Vector3(
                        node.local_transform.scale.x * parent_world.scale.x,
                        node.local_transform.scale.y * parent_world.scale.y,
                        node.local_transform.scale.z * parent_world.scale.z,
                    ),
                )
        else:
            node.world_transform = Transform3D(
                position=Vector3(
                    node.local_transform.position.x,
                    node.local_transform.position.y,
                    node.local_transform.position.z,
                ),
                rotation=Quaternion(
                    node.local_transform.rotation.x,
                    node.local_transform.rotation.y,
                    node.local_transform.rotation.z,
                    node.local_transform.rotation.w,
                ),
                scale=Vector3(
                    node.local_transform.scale.x,
                    node.local_transform.scale.y,
                    node.local_transform.scale.z,
                ),
            )

        self._dirty_set.discard(node_id)

    @staticmethod
    def _transform_point(point: Vector3, matrix: List[List[float]]) -> Vector3:
        """Transform a Vector3 by a 4x4 matrix."""
        x = point.x * matrix[0][0] + point.y * matrix[0][1] + point.z * matrix[0][2] + matrix[0][3]
        y = point.x * matrix[1][0] + point.y * matrix[1][1] + point.z * matrix[1][2] + matrix[1][3]
        z = point.x * matrix[2][0] + point.y * matrix[2][1] + point.z * matrix[2][2] + matrix[2][3]
        return Vector3(x, y, z)

    def update_transforms(self) -> int:
        """Update all dirty world transforms. Called once per frame.

        Returns:
            Number of transforms updated.
        """
        sorted_dirty = self._topological_sort_dirty()
        for node_id in sorted_dirty:
            self._update_world_transform(node_id)
        count = len(sorted_dirty)
        self._dirty_set.clear()
        return count

    def _topological_sort_dirty(self) -> List[str]:
        """Sort dirty nodes so parents are processed before children."""
        sorted_nodes: List[str] = []
        visited: Set[str] = set()

        def visit(nid: str) -> None:
            if nid in visited or nid not in self._dirty_set:
                return
            node = self._nodes.get(nid)
            if node and node.parent_id and node.parent_id in self._dirty_set:
                visit(node.parent_id)
            visited.add(nid)
            sorted_nodes.append(nid)

        for nid in self._dirty_set:
            visit(nid)

        return sorted_nodes

    # ------------------------------------------------------------------
    # Traversal
    # ------------------------------------------------------------------

    def traverse(
        self,
        order: TraversalOrder = TraversalOrder.PRE_ORDER,
        start_node_id: Optional[str] = None,
    ) -> List[GraphNode]:
        """Traverse the scene graph in the specified order.

        Args:
            order: Traversal order.
            start_node_id: Starting node ID. Defaults to root.

        Returns:
            List of nodes in traversal order.
        """
        start_id = start_node_id or self._root_id
        if order == TraversalOrder.PRE_ORDER:
            return self._traverse_pre_order(start_id)
        elif order == TraversalOrder.POST_ORDER:
            return self._traverse_post_order(start_id)
        elif order == TraversalOrder.LEVEL_ORDER:
            return self._traverse_level_order(start_id)
        return []

    def _traverse_pre_order(self, node_id: str) -> List[GraphNode]:
        result: List[GraphNode] = []
        node = self._nodes.get(node_id)
        if node:
            result.append(node)
            for child_id in node.children:
                result.extend(self._traverse_pre_order(child_id))
        return result

    def _traverse_post_order(self, node_id: str) -> List[GraphNode]:
        result: List[GraphNode] = []
        node = self._nodes.get(node_id)
        if node:
            for child_id in node.children:
                result.extend(self._traverse_post_order(child_id))
            result.append(node)
        return result

    def _traverse_level_order(self, node_id: str) -> List[GraphNode]:
        result: List[GraphNode] = []
        queue = deque([node_id])
        while queue:
            current_id = queue.popleft()
            node = self._nodes.get(current_id)
            if node:
                result.append(node)
                for child_id in node.children:
                    queue.append(child_id)
        return result

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def find_by_name(self, name: str) -> List[GraphNode]:
        """Find all nodes with a given name."""
        node_ids = self._name_index.get(name, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_by_tag(self, tag: str) -> List[GraphNode]:
        """Find all nodes with a given tag."""
        node_ids = self._tag_index.get(tag, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_by_path(self, path_str: str, current_node: Optional[GraphNode] = None) -> List[GraphNode]:
        """Find nodes using a StarPath expression.

        Args:
            path_str: Path string (e.g., "/Root/Player", "../Enemy/*").
            current_node: Node to resolve relative paths from. Defaults to root.

        Returns:
            List of matching GraphNode instances.
        """
        star_path = StarPath.parse(path_str)
        ctx = current_node or self._nodes.get(self._root_id)
        if ctx is None:
            return []
        root = self._nodes.get(self._root_id)
        if root is None:
            return []
        return star_path.resolve(ctx, root, self._nodes)

    def find_by_component(self, component_type: str) -> List[GraphNode]:
        """Find all nodes that have a specific component type attached."""
        return [n for n in self._nodes.values() if n.has_component(component_type)]

    # ------------------------------------------------------------------
    # Node State
    # ------------------------------------------------------------------

    def set_active(self, node_id: str, active: bool) -> bool:
        """Set the active state of a node and all descendants.

        Args:
            node_id: ID of the node.
            active: New active state.

        Returns:
            True if the node was found.
        """
        node = self._nodes.get(node_id)
        if not node:
            return False
        node.is_active = active
        node.emit(NodeSignal.ACTIVE_CHANGED, {"active": active})
        for child_id in node.children:
            self.set_active(child_id, active)
        return True

    def set_name(self, node_id: str, name: str) -> bool:
        """Set the name of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return False
        # Update name index
        old_name_set = self._name_index.get(node.name, set())
        old_name_set.discard(node_id)
        node.name = name
        self._name_index.setdefault(name, set()).add(node_id)
        node.emit(NodeSignal.NAME_CHANGED, {"name": name})
        return True

    def add_tag(self, node_id: str, tag: str) -> bool:
        """Add a tag to a node."""
        node = self._nodes.get(node_id)
        if not node or tag in node.tags:
            return False
        node.tags.append(tag)
        self._tag_index.setdefault(tag, set()).add(node_id)
        node.emit(NodeSignal.TAG_ADDED, {"tag": tag})
        return True

    def remove_tag(self, node_id: str, tag: str) -> bool:
        """Remove a tag from a node."""
        node = self._nodes.get(node_id)
        if not node or tag not in node.tags:
            return False
        node.tags.remove(tag)
        tag_set = self._tag_index.get(tag, set())
        tag_set.discard(node_id)
        node.emit(NodeSignal.TAG_REMOVED, {"tag": tag})
        return True

    def get_path_to_root(self, node_id: str) -> List[GraphNode]:
        """Get the path from the root to a node."""
        path: List[GraphNode] = []
        current_id = node_id
        while current_id:
            node = self._nodes.get(current_id)
            if not node:
                break
            path.insert(0, node)
            current_id = node.parent_id
        return path

    def get_path_string(self, node_id: str) -> str:
        """Get the absolute path string of a node."""
        path = self.get_path_to_root(node_id)
        return "/" + "/".join(n.name for n in path)

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize(self, scene_name: str = "Scene", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Serialize the entire scene graph to a dictionary."""
        root = self._nodes.get(self._root_id)
        if not root:
            return {}
        return self._serializer.serialize_to_dict(root, self._nodes, scene_name, metadata)

    def serialize_binary(self, scene_name: str = "Scene") -> bytes:
        """Serialize the entire scene graph to binary format."""
        root = self._nodes.get(self._root_id)
        if not root:
            return b""
        return self._serializer.serialize_to_binary(root, self._nodes, scene_name)

    def deserialize(self, data: Dict[str, Any]) -> bool:
        """Deserialize a scene from a dictionary, replacing the current graph.

        Args:
            data: Serialized scene dictionary.

        Returns:
            True if successful.
        """
        root, nodes = self._serializer.deserialize_scene(data)
        if not root:
            return False

        self._nodes = nodes
        self._root_id = root.node_id
        self._rebuild_indexes()
        self._dirty_set = set(self._nodes.keys())
        return True

    def deserialize_binary(self, data: bytes) -> bool:
        """Deserialize a scene from binary format."""
        root, nodes = self._serializer.deserialize_from_binary(data)
        if not root:
            return False

        self._nodes = nodes
        self._root_id = root.node_id
        self._rebuild_indexes()
        self._dirty_set = set(self._nodes.keys())
        return True

    def _rebuild_indexes(self) -> None:
        """Rebuild tag and name indexes from the current node set."""
        self._tag_index.clear()
        self._name_index.clear()
        for node in self._nodes.values():
            self._index_node(node)

    def _index_node(self, node: GraphNode) -> None:
        """Index a node by its tags and name."""
        for tag in node.tags:
            self._tag_index.setdefault(tag, set()).add(node.node_id)
        self._name_index.setdefault(node.name, set()).add(node.node_id)

    def _unindex_node(self, node: GraphNode) -> None:
        """Remove a node from all indexes."""
        for tag in node.tags:
            tag_set = self._tag_index.get(tag, set())
            tag_set.discard(node.node_id)
        name_set = self._name_index.get(node.name, set())
        name_set.discard(node.node_id)

    # ------------------------------------------------------------------
    # Prefab Integration
    # ------------------------------------------------------------------

    def get_prefab_library(self) -> ConstellationLibrary:
        """Get the ConstellationLibrary for prefab management."""
        return self._prefab_library

    def instantiate_prefab(self, template_id: str, parent_id: Optional[str] = None) -> Optional[GraphNode]:
        """Instantiate a prefab template into the scene graph.

        Args:
            template_id: The prefab template ID.
            parent_id: Optional parent node to attach to.

        Returns:
            The root node of the instantiated prefab, or None.
        """
        return self._prefab_library.instantiate_into_scene(self, template_id, parent_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get scene graph statistics."""
        return {
            "total_nodes": len(self._nodes),
            "root_id": self._root_id,
            "dirty_transforms": len(self._dirty_set),
            "tags_indexed": len(self._tag_index),
            "names_indexed": len(self._name_index),
            "serializer": self._serializer.get_stats(),
            "prefab_library": self._prefab_library.get_stats(),
        }


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_scene_graph() -> SceneGraphEngine:
    """Get the singleton SceneGraphEngine instance."""
    return SceneGraphEngine.get_instance()