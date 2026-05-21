"""
SparkLabs Engine - Node Tree System

Godot-style hierarchical scene node tree system providing parent-child
spatial transforms, signal propagation with configurable scope, lifecycle
state management, and flexible tree traversal patterns. Designed as the
core scene graph backbone for all visual and logical game objects.

Architecture:
  NodeTreeSystem
    |-- SceneNode (hierarchical node with transforms and metadata)
    |-- NodeSignal (event payload with source, name, and data)
    |-- SignalConnection (registered callback binding between nodes)
    |-- SceneDefinition (serializable scene blueprint for export/import)

Node Tree Features:
  - HIERARCHY: parent-child relationships with recursive removal
  - TRANSFORMS: local and world-space position, scale, and rotation
  - SIGNALS: node-scoped, upward/downward, group, and scene broadcast
  - LIFECYCLE: seven-stage state machine from creation to free
  - TRAVERSAL: pre-order, post-order, and breadth-first ordering
  - SERIALIZATION: full scene export/import for layout persistence
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class NodeType(Enum):
    ROOT = "root"
    SPATIAL = "spatial"
    SPRITE = "sprite"
    CAMERA = "camera"
    UI = "ui"
    AUDIO = "audio"
    PHYSICS = "physics"
    SCRIPT = "script"
    ANIMATION = "animation"
    LIGHT = "light"
    CUSTOM = "custom"


class NodeLifecycle(Enum):
    CREATED = "created"
    ENTERING_TREE = "entering_tree"
    READY = "ready"
    ACTIVE = "active"
    PAUSED = "paused"
    EXITING_TREE = "exiting_tree"
    FREED = "freed"


class TraversalOrder(Enum):
    PRE_ORDER = "pre_order"
    POST_ORDER = "post_order"
    BREADTH_FIRST = "breadth_first"


class SignalScope(Enum):
    NODE_ONLY = "node_only"
    UPWARD = "upward"
    DOWNWARD = "downward"
    GROUP_BROADCAST = "group_broadcast"
    SCENE_BROADCAST = "scene_broadcast"


@dataclass
class SceneNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: NodeType = NodeType.SPATIAL
    parent_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    local_position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    local_scale: Dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    local_rotation: float = 0.0
    global_position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    global_scale: Dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    global_rotation: float = 0.0
    lifecycle: NodeLifecycle = NodeLifecycle.CREATED
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    visible: bool = True
    paused: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "local_position": dict(self.local_position),
            "local_scale": dict(self.local_scale),
            "local_rotation": self.local_rotation,
            "global_position": dict(self.global_position),
            "global_scale": dict(self.global_scale),
            "global_rotation": self.global_rotation,
            "lifecycle": self.lifecycle.value,
            "properties": dict(self.properties),
            "tags": list(self.tags),
            "visible": self.visible,
            "paused": self.paused,
        }


@dataclass
class NodeSignal:
    source_id: str = ""
    signal_name: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    scope: SignalScope = SignalScope.NODE_ONLY

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "signal_name": self.signal_name,
            "data": self.data,
            "timestamp": self.timestamp,
            "scope": self.scope.value,
        }


@dataclass
class SignalConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_id: str = ""
    signal_name: str = ""
    target_id: str = ""
    callback: str = ""
    scope: SignalScope = SignalScope.NODE_ONLY
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "signal_name": self.signal_name,
            "target_id": self.target_id,
            "callback": self.callback,
            "scope": self.scope.value,
            "is_active": self.is_active,
        }


@dataclass
class SceneDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    roots: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    exported_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": self.nodes,
            "roots": list(self.roots),
            "metadata": self.metadata,
            "exported_at": self.exported_at,
        }


class NodeTreeSystem:
    """Godot-style hierarchical scene node tree with signals and lifecycle."""

    _instance: Optional["NodeTreeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._nodes: Dict[str, SceneNode] = {}
        self._roots: List[str] = []
        self._signals: Dict[str, List[SignalConnection]] = {}

    @classmethod
    def get_instance(cls) -> "NodeTreeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Node Creation and Removal ----

    def create_node(self,
                    name: str,
                    node_type: str = "spatial",
                    parent_id: str = "",
                    position: Optional[Dict[str, float]] = None,
                    properties: Optional[Dict[str, Any]] = None) -> SceneNode:
        try:
            nt = NodeType(node_type.lower())
        except ValueError:
            nt = NodeType.SPATIAL

        node = SceneNode(
            name=name,
            node_type=nt,
            parent_id=parent_id,
            local_position=position or {"x": 0.0, "y": 0.0, "z": 0.0},
            properties=properties or {},
        )

        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            parent.children_ids.append(node.id)
            self._recompute_global_transform(node)
        else:
            node.parent_id = ""
            node.global_position = dict(node.local_position)
            node.global_scale = dict(node.local_scale)
            node.global_rotation = node.local_rotation
            self._roots.append(node.id)

        self._nodes[node.id] = node
        return node

    def remove_node(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False

        descendant_ids = self._collect_descendant_ids(node_id)

        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            if node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        if node_id in self._roots:
            self._roots.remove(node_id)

        for nid in descendant_ids:
            self._remove_signals_for_node(nid)
            self._nodes.pop(nid, None)

        return True

    def _collect_descendant_ids(self, node_id: str) -> List[str]:
        result: List[str] = []
        node = self._nodes.get(node_id)
        if node is None:
            return result
        result.append(node_id)
        for child_id in node.children_ids:
            result.extend(self._collect_descendant_ids(child_id))
        return result

    # ---- Hierarchy Operations ----

    def set_parent(self, node_id: str, new_parent_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        new_parent = self._nodes.get(new_parent_id)
        if new_parent is None and new_parent_id != "":
            return False

        if node.parent_id and node.parent_id in self._nodes:
            old_parent = self._nodes[node.parent_id]
            if node_id in old_parent.children_ids:
                old_parent.children_ids.remove(node_id)

        if node_id in self._roots:
            self._roots.remove(node_id)

        if new_parent_id:
            new_parent.children_ids.append(node_id)
            node.parent_id = new_parent_id
        else:
            node.parent_id = ""
            self._roots.append(node_id)

        self._recompute_global_transform(node)
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child:
                self._propagate_transform_down(child)

        return True

    def reparent_node(self, node_id: str, new_parent_id: str) -> bool:
        if node_id == new_parent_id:
            return False
        if new_parent_id and self._is_descendant_of(new_parent_id, node_id):
            return False
        return self.set_parent(node_id, new_parent_id)

    def _is_descendant_of(self, ancestor_id: str, target_id: str) -> bool:
        ancestor = self._nodes.get(ancestor_id)
        if ancestor is None:
            return False
        if target_id in ancestor.children_ids:
            return True
        for child_id in ancestor.children_ids:
            if self._is_descendant_of(child_id, target_id):
                return True
        return False

    # ---- Node Access ----

    def get_node(self, node_id: str) -> Optional[SceneNode]:
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> List[SceneNode]:
        node = self._nodes.get(node_id)
        if node is None:
            return []
        return [
            self._nodes[cid] for cid in node.children_ids
            if cid in self._nodes
        ]

    def get_root_nodes(self) -> List[SceneNode]:
        return [
            self._nodes[rid] for rid in self._roots
            if rid in self._nodes
        ]

    # ---- Tree Traversal ----

    def traverse(self, node_id: str, order: str = "pre_order") -> List[SceneNode]:
        try:
            to = TraversalOrder(order.lower())
        except ValueError:
            to = TraversalOrder.PRE_ORDER

        if to == TraversalOrder.PRE_ORDER:
            return self._traverse_pre_order(node_id)
        elif to == TraversalOrder.POST_ORDER:
            return self._traverse_post_order(node_id)
        else:
            return self._traverse_breadth_first(node_id)

    def _traverse_pre_order(self, node_id: str) -> List[SceneNode]:
        result: List[SceneNode] = []
        node = self._nodes.get(node_id)
        if node is None:
            return result
        result.append(node)
        for child_id in node.children_ids:
            result.extend(self._traverse_pre_order(child_id))
        return result

    def _traverse_post_order(self, node_id: str) -> List[SceneNode]:
        result: List[SceneNode] = []
        node = self._nodes.get(node_id)
        if node is None:
            return result
        for child_id in node.children_ids:
            result.extend(self._traverse_post_order(child_id))
        result.append(node)
        return result

    def _traverse_breadth_first(self, node_id: str) -> List[SceneNode]:
        result: List[SceneNode] = []
        node = self._nodes.get(node_id)
        if node is None:
            return result
        queue: deque = deque([node_id])
        while queue:
            current_id = queue.popleft()
            current = self._nodes.get(current_id)
            if current is None:
                continue
            result.append(current)
            for child_id in current.children_ids:
                queue.append(child_id)
        return result

    # ---- Transform Operations ----

    def update_transform(self,
                         node_id: str,
                         position: Optional[Dict[str, float]] = None,
                         scale: Optional[Dict[str, float]] = None,
                         rotation: Optional[float] = None) -> Optional[SceneNode]:
        node = self._nodes.get(node_id)
        if node is None:
            return None

        if position is not None:
            node.local_position = {
                "x": position.get("x", node.local_position["x"]),
                "y": position.get("y", node.local_position["y"]),
                "z": position.get("z", node.local_position["z"]),
            }
        if scale is not None:
            node.local_scale = {
                "x": scale.get("x", node.local_scale["x"]),
                "y": scale.get("y", node.local_scale["y"]),
                "z": scale.get("z", node.local_scale["z"]),
            }
        if rotation is not None:
            node.local_rotation = rotation

        self._recompute_global_transform(node)
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child:
                self._propagate_transform_down(child)

        return node

    def _recompute_global_transform(self, node: SceneNode) -> None:
        if node.parent_id and node.parent_id in self._nodes:
            parent = self._nodes[node.parent_id]
            node.global_position = {
                "x": parent.global_position["x"] + node.local_position["x"],
                "y": parent.global_position["y"] + node.local_position["y"],
                "z": parent.global_position["z"] + node.local_position["z"],
            }
            node.global_scale = {
                "x": parent.global_scale["x"] * node.local_scale["x"],
                "y": parent.global_scale["y"] * node.local_scale["y"],
                "z": parent.global_scale["z"] * node.local_scale["z"],
            }
            node.global_rotation = parent.global_rotation + node.local_rotation
        else:
            node.global_position = dict(node.local_position)
            node.global_scale = dict(node.local_scale)
            node.global_rotation = node.local_rotation

    def _propagate_transform_down(self, node: SceneNode) -> None:
        self._recompute_global_transform(node)
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child:
                self._propagate_transform_down(child)

    # ---- Signal System ----

    def connect_signal(self,
                       source_id: str,
                       signal_name: str,
                       target_id: str,
                       callback: str = "",
                       scope: str = "node_only") -> Optional[SignalConnection]:
        if source_id not in self._nodes:
            return None
        if target_id not in self._nodes:
            return None

        try:
            sc = SignalScope(scope.lower())
        except ValueError:
            sc = SignalScope.NODE_ONLY

        connection = SignalConnection(
            source_id=source_id,
            signal_name=signal_name,
            target_id=target_id,
            callback=callback,
            scope=sc,
        )

        key = f"{source_id}:{signal_name}"
        if key not in self._signals:
            self._signals[key] = []
        self._signals[key].append(connection)

        return connection

    def emit_signal(self,
                    source_id: str,
                    signal_name: str,
                    data: Optional[Dict[str, Any]] = None) -> int:
        if source_id not in self._nodes:
            return 0

        signal = NodeSignal(
            source_id=source_id,
            signal_name=signal_name,
            data=data or {},
        )

        key = f"{source_id}:{signal_name}"
        connections = self._signals.get(key, [])
        if not connections:
            return 0

        handlers_invoked = 0
        for conn in connections:
            if not conn.is_active:
                continue

            if conn.scope == SignalScope.NODE_ONLY:
                if conn.target_id == source_id:
                    handlers_invoked += 1
            elif conn.scope == SignalScope.UPWARD:
                if self._is_ancestor_of(conn.target_id, source_id):
                    handlers_invoked += 1
            elif conn.scope == SignalScope.DOWNWARD:
                if conn.target_id == source_id or self._is_descendant_of(source_id, conn.target_id):
                    handlers_invoked += 1
            elif conn.scope == SignalScope.GROUP_BROADCAST:
                source_node = self._nodes.get(source_id)
                if source_node:
                    source_tags = set(source_node.tags)
                    target_node = self._nodes.get(conn.target_id)
                    if target_node:
                        target_tags = set(target_node.tags)
                        if source_tags.intersection(target_tags):
                            handlers_invoked += 1
            elif conn.scope == SignalScope.SCENE_BROADCAST:
                handlers_invoked += 1

        return handlers_invoked

    def disconnect_signal(self, connection_id: str) -> bool:
        for key, connections in self._signals.items():
            for i, conn in enumerate(connections):
                if conn.id == connection_id:
                    connections.pop(i)
                    if not connections:
                        del self._signals[key]
                    return True
        return False

    def _remove_signals_for_node(self, node_id: str) -> None:
        keys_to_remove = []
        for key, connections in self._signals.items():
            connections[:] = [
                c for c in connections
                if c.source_id != node_id and c.target_id != node_id
            ]
            if not connections:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._signals[key]

    def _is_ancestor_of(self, ancestor_id: str, target_id: str) -> bool:
        current_id = target_id
        while current_id:
            current = self._nodes.get(current_id)
            if current is None:
                break
            if current.parent_id == ancestor_id:
                return True
            current_id = current.parent_id
        return False

    # ---- Lifecycle Management ----

    def set_lifecycle(self, node_id: str, state: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False

        try:
            new_state = NodeLifecycle(state.lower())
        except ValueError:
            return False

        if node.lifecycle == new_state:
            return True

        if node.lifecycle == NodeLifecycle.FREED:
            return False

        node.lifecycle = new_state

        if new_state == NodeLifecycle.ENTERING_TREE:
            for child_id in node.children_ids:
                child = self._nodes.get(child_id)
                if child and child.lifecycle == NodeLifecycle.CREATED:
                    child.lifecycle = NodeLifecycle.ENTERING_TREE

        if new_state == NodeLifecycle.FREED:
            self._remove_signals_for_node(node_id)

        return True

    # ---- Scene Export and Import ----

    def export_scene(self, root_id: str) -> Optional[SceneDefinition]:
        root = self._nodes.get(root_id)
        if root is None:
            return None

        node_dicts: Dict[str, Dict[str, Any]] = {}
        descendants = self._traverse_pre_order(root_id)
        for node in descendants:
            node_dicts[node.id] = node.to_dict()

        return SceneDefinition(
            name=root.name,
            nodes=node_dicts,
            roots=[root_id],
            metadata={
                "node_count": len(node_dicts),
                "source_node_id": root_id,
            },
        )

    def import_scene(self, definition: SceneDefinition) -> Optional[SceneNode]:
        if not definition.nodes:
            return None

        id_map: Dict[str, str] = {}

        nodes_to_create = sorted(
            definition.nodes.values(),
            key=lambda n: len(n.get("children_ids", [])),
        )

        created_root: Optional[SceneNode] = None

        for node_data in nodes_to_create:
            old_id = node_data["id"]
            new_id = uuid.uuid4().hex
            id_map[old_id] = new_id

            mapped_parent_id = ""
            old_parent = node_data.get("parent_id", "")
            if old_parent and old_parent in id_map:
                mapped_parent_id = id_map[old_parent]

            try:
                nt = NodeType(node_data.get("node_type", "spatial"))
            except ValueError:
                nt = NodeType.SPATIAL

            try:
                lc = NodeLifecycle(node_data.get("lifecycle", "created"))
            except ValueError:
                lc = NodeLifecycle.CREATED

            node = SceneNode(
                id=new_id,
                name=node_data.get("name", ""),
                node_type=nt,
                parent_id=mapped_parent_id if mapped_parent_id else "",
                local_position=node_data.get("local_position", {"x": 0.0, "y": 0.0, "z": 0.0}),
                local_scale=node_data.get("local_scale", {"x": 1.0, "y": 1.0, "z": 1.0}),
                local_rotation=node_data.get("local_rotation", 0.0),
                global_position=node_data.get("global_position", {"x": 0.0, "y": 0.0, "z": 0.0}),
                global_scale=node_data.get("global_scale", {"x": 1.0, "y": 1.0, "z": 1.0}),
                global_rotation=node_data.get("global_rotation", 0.0),
                lifecycle=lc,
                properties=node_data.get("properties", {}),
                tags=node_data.get("tags", []),
                visible=node_data.get("visible", True),
                paused=node_data.get("paused", False),
            )

            if old_id in definition.roots:
                self._roots.append(new_id)
                created_root = node

            self._nodes[new_id] = node

        for node_data in nodes_to_create:
            old_id = node_data["id"]
            new_id = id_map[old_id]
            node = self._nodes.get(new_id)
            if node is None:
                continue
            mapped_children = []
            for old_child_id in node_data.get("children_ids", []):
                if old_child_id in id_map:
                    mapped_children.append(id_map[old_child_id])
            node.children_ids = mapped_children

        for node_data in nodes_to_create:
            old_id = node_data["id"]
            new_id = id_map[old_id]
            node = self._nodes.get(new_id)
            if node and node.parent_id:
                parent = self._nodes.get(node.parent_id)
                if parent and new_id not in parent.children_ids:
                    parent.children_ids.append(new_id)
            if node:
                self._recompute_global_transform(node)

        return created_root

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = len(self._nodes)
        total_connections = sum(
            len(conns) for conns in self._signals.values()
        )
        lifecycle_counts: Dict[str, int] = {}
        type_counts: Dict[str, int] = {}
        for node in self._nodes.values():
            lc = node.lifecycle.value
            lifecycle_counts[lc] = lifecycle_counts.get(lc, 0) + 1
            nt = node.node_type.value
            type_counts[nt] = type_counts.get(nt, 0) + 1

        return {
            "total_nodes": total_nodes,
            "root_count": len(self._roots),
            "total_signal_connections": total_connections,
            "signal_groups": len(self._signals),
            "lifecycle_distribution": lifecycle_counts,
            "type_distribution": type_counts,
            "orphan_nodes": sum(
                1 for n in self._nodes.values()
                if not n.parent_id and n.id not in self._roots
            ),
        }


def get_node_tree() -> NodeTreeSystem:
    return NodeTreeSystem.get_instance()