"""
SparkLabs Engine - Scene Tree System

Hierarchical scene graph management inspired by Godot's scene
tree architecture. Manages the node tree structure, group
membership, scene transitions, and signal propagation —
providing the structural backbone for AI-generated game worlds.

Architecture:
  SceneTree
    |-- SceneNode (base node with parent/child hierarchy)
      |-- RootNode (top-level scene container)
      |-- GroupNode (logical grouping with shared properties)
      |-- EntityNode (game entity representation)
    |-- GroupManager (node group assignment and queries)
    |-- SceneStack (push/pop scene navigation)

Node Lifecycle:
  ENTER_TREE → READY → PROCESS → PHYSICS_PROCESS → EXIT_TREE
                                    ↳ PAUSED

Usage:
    st = SceneTree()
    root = st.get_root()
    player = st.create_node("Player", parent=root, node_type="entity")
    world = st.create_node("World", node_type="group")
    st.reparent(player.node_id, world.node_id)
    group_nodes = st.get_nodes_in_group("enemies")
    st.change_scene("Level2")
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class NodeLifecycle(Enum):
    ENTERING = auto()
    READY = auto()
    ACTIVE = auto()
    PAUSED = auto()
    EXITING = auto()
    REMOVED = auto()


@dataclass
class NodeTransform:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0

    def clone(self) -> "NodeTransform":
        return NodeTransform(self.x, self.y, self.z, self.rotation, self.scale_x, self.scale_y)


class SceneNode:
    __slots__ = (
        "node_id", "name", "node_type", "parent", "children",
        "transform", "lifecycle", "visible", "paused",
        "groups", "properties", "metadata", "signals",
        "_creation_time", "_enter_time",
    )

    def __init__(self, node_id: str = "", name: str = "Node", node_type: str = "node"):
        self.node_id: str = node_id or str(uuid.uuid4())[:8]
        self.name: str = name
        self.node_type: str = node_type
        self.parent: Optional["SceneNode"] = None
        self.children: List["SceneNode"] = []
        self.transform: NodeTransform = NodeTransform()
        self.lifecycle: NodeLifecycle = NodeLifecycle.ENTERING
        self.visible: bool = True
        self.paused: bool = False
        self.groups: Set[str] = set()
        self.properties: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.signals: Dict[str, List[Callable]] = {}
        self._creation_time: float = time.monotonic()
        self._enter_time: float = 0.0

    def add_child(self, child: "SceneNode") -> None:
        child.parent = self
        self.children.append(child)
        child.lifecycle = NodeLifecycle.ENTERING
        child._enter_time = time.monotonic()

    def remove_child(self, node_id: str) -> Optional["SceneNode"]:
        for i, child in enumerate(self.children):
            if child.node_id == node_id:
                child.lifecycle = NodeLifecycle.EXITING
                child.parent = None
                return self.children.pop(i)
        return None

    def get_child(self, node_id: str) -> Optional["SceneNode"]:
        for child in self.children:
            if child.node_id == node_id:
                return child
            found = child.get_child(node_id)
            if found:
                return found
        return None

    def find_by_name(self, name: str) -> Optional["SceneNode"]:
        if self.name == name:
            return self
        for child in self.children:
            found = child.find_by_name(name)
            if found:
                return found
        return None

    def find_by_type(self, node_type: str) -> List["SceneNode"]:
        result = []
        if self.node_type == node_type:
            result.append(self)
        for child in self.children:
            result.extend(child.find_by_type(node_type))
        return result

    def get_path(self) -> str:
        if self.parent is None:
            return f"/root/{self.name}"
        return f"{self.parent.get_path()}/{self.name}"

    def get_depth(self) -> int:
        depth = 0
        current = self.parent
        while current:
            depth += 1
            current = current.parent
        return depth

    def is_descendant_of(self, ancestor: "SceneNode") -> bool:
        current = self.parent
        while current:
            if current.node_id == ancestor.node_id:
                return True
            current = current.parent
        return False

    def connect(self, signal_name: str, callback: Callable) -> None:
        if signal_name not in self.signals:
            self.signals[signal_name] = []
        self.signals[signal_name].append(callback)

    def emit(self, signal_name: str, *args, **kwargs) -> None:
        handlers = self.signals.get(signal_name, [])
        for handler in handlers:
            try:
                handler(*args, **kwargs)
            except Exception:
                pass

    def get_flattened_hierarchy(self) -> List[Dict[str, Any]]:
        result = [{
            "node_id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "depth": self.get_depth(),
            "child_count": len(self.children),
            "visible": self.visible,
            "groups": list(self.groups),
            "lifecycle": self.lifecycle.name.lower(),
        }]
        for child in self.children:
            result.extend(child.get_flattened_hierarchy())
        return result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "type": self.node_type,
            "path": self.get_path(),
            "depth": self.get_depth(),
            "child_count": len(self.children),
            "visible": self.visible,
            "paused": self.paused,
            "groups": list(self.groups),
            "lifecycle": self.lifecycle.name.lower(),
            "transform": {
                "x": self.transform.x,
                "y": self.transform.y,
                "rotation": self.transform.rotation,
                "scale_x": self.transform.scale_x,
                "scale_y": self.transform.scale_y,
            },
        }


class SceneTree:
    _instance: Optional["SceneTree"] = None

    def __init__(self):
        self._root: Optional[SceneNode] = None
        self._group_membership: Dict[str, Set[str]] = {}
        self._node_registry: Dict[str, SceneNode] = {}
        self._scene_stack: List[SceneNode] = []
        self._current_scene_root: Optional[SceneNode] = None
        self._initialize()

    def _initialize(self) -> None:
        self._root = SceneNode(node_id="root", name="Root", node_type="root")
        self._root.lifecycle = NodeLifecycle.ACTIVE
        self._node_registry["root"] = self._root
        self._current_scene_root = self._root

    @classmethod
    def get_instance(cls) -> "SceneTree":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def root(self) -> SceneNode:
        return self._root

    @property
    def current_scene(self) -> SceneNode:
        return self._current_scene_root

    def create_node(
        self,
        name: str,
        parent: Optional[SceneNode] = None,
        node_type: str = "node",
        **properties,
    ) -> SceneNode:
        node = SceneNode(name=name, node_type=node_type)
        for key, value in properties.items():
            node.properties[key] = value

        parent = parent or self._root
        parent.add_child(node)
        node.lifecycle = NodeLifecycle.ACTIVE
        self._node_registry[node.node_id] = node
        return node

    def get_node(self, node_id: str) -> Optional[SceneNode]:
        if node_id == "root":
            return self._root
        return self._root.get_child(node_id) if self._root else None

    def find_node(self, path: str) -> Optional[SceneNode]:
        if not self._root:
            return None
        parts = path.strip("/").split("/")
        current = self._root
        for part in parts:
            found = None
            for child in current.children:
                if child.name == part:
                    found = child
                    break
            if not found:
                return None
            current = found
        return current

    def remove_node(self, node_id: str) -> bool:
        node = self.get_node(node_id)
        if not node or not node.parent:
            return False
        node.lifecycle = NodeLifecycle.EXITING

        for group in node.groups:
            self._group_membership.get(group, set()).discard(node_id)

        node.parent.remove_child(node_id)
        self._node_registry.pop(node_id, None)
        node.lifecycle = NodeLifecycle.REMOVED
        return True

    def reparent(self, node_id: str, new_parent_id: str) -> bool:
        node = self.get_node(node_id)
        new_parent = self.get_node(new_parent_id)
        if not node or not new_parent or not node.parent:
            return False
        if new_parent.is_descendant_of(node):
            return False
        node.parent.remove_child(node_id)
        node.lifecycle = NodeLifecycle.EXITING
        new_parent.add_child(node)
        node.lifecycle = NodeLifecycle.ACTIVE
        return True

    def add_to_group(self, node_id: str, group: str) -> bool:
        node = self.get_node(node_id)
        if not node:
            return False
        node.groups.add(group)
        if group not in self._group_membership:
            self._group_membership[group] = set()
        self._group_membership[group].add(node_id)
        return True

    def remove_from_group(self, node_id: str, group: str) -> bool:
        node = self.get_node(node_id)
        if not node:
            return False
        node.groups.discard(group)
        self._group_membership.get(group, set()).discard(node_id)
        return True

    def get_nodes_in_group(self, group: str) -> List[SceneNode]:
        node_ids = self._group_membership.get(group, set())
        return [self.get_node(nid) for nid in node_ids if self.get_node(nid)]

    def push_scene(self, scene_node: SceneNode) -> None:
        self._scene_stack.append(self._current_scene_root)
        self._current_scene_root = scene_node

    def pop_scene(self) -> Optional[SceneNode]:
        if self._scene_stack:
            self._current_scene_root = self._scene_stack.pop()
            return self._current_scene_root
        return None

    def change_scene(self, new_root: SceneNode) -> None:
        if self._current_scene_root:
            self._current_scene_root.lifecycle = NodeLifecycle.EXITING
        self._current_scene_root = new_root
        new_root.lifecycle = NodeLifecycle.ACTIVE

    def get_all_nodes(self) -> List[SceneNode]:
        if not self._root:
            return []
        nodes = [self._root]
        queue = [self._root]
        while queue:
            current = queue.pop(0)
            nodes.extend(current.children)
            queue.extend(current.children)
        return nodes

    def get_hierarchy(self) -> List[Dict[str, Any]]:
        if not self._root:
            return []
        return self._root.get_flattened_hierarchy()

    def get_stats(self) -> Dict[str, Any]:
        all_nodes = self.get_all_nodes()
        total = len(all_nodes) - 1

        return {
            "total_nodes": total,
            "depth": max((n.get_depth() for n in all_nodes[1:]), default=0),
            "scene_stack_depth": len(self._scene_stack),
            "groups": {
                g: len(members) for g, members in self._group_membership.items()
            },
            "registry_size": len(self._node_registry),
            "node_types": {
                t: len([n for n in all_nodes[1:] if n.node_type == t])
                for t in set(n.node_type for n in all_nodes[1:])
            },
        }


def get_scene_tree() -> SceneTree:
    return SceneTree.get_instance()
