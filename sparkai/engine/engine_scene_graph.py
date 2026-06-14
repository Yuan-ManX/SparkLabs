"""
Engine Scene Graph - Hierarchical scene tree for game object management.
Provides parent-child transforms, scene traversal, node queries,
and spatial organization for the SparkLabs game engine.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any, Callable


class NodeType(Enum):
    """Types of scene graph nodes."""
    ROOT = "root"
    GROUP = "group"
    SPRITE = "sprite"
    CAMERA = "camera"
    LIGHT = "light"
    AUDIO = "audio"
    PARTICLE = "particle"
    UI = "ui"
    TRIGGER = "trigger"
    CUSTOM = "custom"


@dataclass
class Transform2D:
    """2D transform for scene graph nodes."""
    position: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    skew: Tuple[float, float] = (0.0, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "position": list(self.position),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "skew": list(self.skew),
        }


@dataclass
class SceneNode:
    """A node in the scene graph."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: NodeType = NodeType.GROUP
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    transform: Transform2D = field(default_factory=Transform2D)
    world_transform: Transform2D = field(default_factory=Transform2D)
    is_visible: bool = True
    is_active: bool = True
    z_order: int = 0
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    components: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "transform": self.transform.to_dict(),
            "world_transform": self.world_transform.to_dict(),
            "is_visible": self.is_visible,
            "is_active": self.is_active,
            "z_order": self.z_order,
            "tags": self.tags,
            "properties": self.properties,
        }


class EngineSceneGraph:
    """
    Hierarchical scene graph system for game object management.
    Provides parent-child transforms, scene traversal, node queries,
    and spatial organization using a tree structure.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._nodes: Dict[str, SceneNode] = {}
            self._root_id: str = ""
            self._tag_index: Dict[str, Set[str]] = {}
            self._type_index: Dict[str, Set[str]] = {}
            self._dirty_transforms: Set[str] = set()
            self._node_callbacks: Dict[str, List[Callable]] = {}
            self._initialized = True
            self._create_root()

    @classmethod
    def get_instance(cls) -> 'EngineSceneGraph':
        return cls()

    def _create_root(self):
        """Create the root scene node."""
        root = SceneNode(
            name="Root",
            node_type=NodeType.ROOT,
        )
        self._nodes[root.node_id] = root
        self._root_id = root.node_id
        self._index_node(root)

    def _index_node(self, node: SceneNode):
        """Index a node by its tags and type."""
        for tag in node.tags:
            self._tag_index.setdefault(tag, set()).add(node.node_id)
        self._type_index.setdefault(node.node_type.value, set()).add(node.node_id)

    def _unindex_node(self, node: SceneNode):
        """Remove a node from all indexes."""
        for tag in node.tags:
            tag_set = self._tag_index.get(tag, set())
            tag_set.discard(node.node_id)
        type_set = self._type_index.get(node.node_type.value, set())
        type_set.discard(node.node_id)

    def create_node(self, name: str, node_type: NodeType = NodeType.GROUP,
                    parent_id: Optional[str] = None,
                    transform: Optional[Transform2D] = None,
                    tags: List[str] = None) -> SceneNode:
        """Create a new scene graph node."""
        node = SceneNode(
            name=name,
            node_type=node_type,
            parent_id=parent_id or self._root_id,
            transform=transform or Transform2D(),
            tags=tags or [],
        )

        self._nodes[node.node_id] = node
        self._index_node(node)

        parent = self._nodes.get(node.parent_id)
        if parent:
            parent.children.append(node.node_id)

        self._dirty_transforms.add(node.node_id)
        self._update_world_transform(node.node_id)

        return node

    def remove_node(self, node_id: str):
        """Remove a node and all its children from the scene graph."""
        node = self._nodes.get(node_id)
        if not node or node_id == self._root_id:
            return

        for child_id in list(node.children):
            self.remove_node(child_id)

        parent = self._nodes.get(node.parent_id)
        if parent and node_id in parent.children:
            parent.children.remove(node_id)

        self._unindex_node(node)
        self._dirty_transforms.discard(node_id)
        del self._nodes[node_id]

    def set_parent(self, node_id: str, new_parent_id: str):
        """Change the parent of a node."""
        node = self._nodes.get(node_id)
        new_parent = self._nodes.get(new_parent_id)
        if not node or not new_parent:
            return

        old_parent = self._nodes.get(node.parent_id)
        if old_parent and node_id in old_parent.children:
            old_parent.children.remove(node_id)

        node.parent_id = new_parent_id
        new_parent.children.append(node_id)
        self._dirty_transforms.add(node_id)

    def set_transform(self, node_id: str, position: Tuple[float, float] = None,
                      rotation: float = None, scale: Tuple[float, float] = None):
        """Set the local transform of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return

        if position is not None:
            node.transform.position = position
        if rotation is not None:
            node.transform.rotation = rotation
        if scale is not None:
            node.transform.scale = scale

        self._dirty_transforms.add(node_id)
        self._propagate_dirty(node_id)

    def _propagate_dirty(self, node_id: str):
        """Mark all children as dirty when parent transform changes."""
        node = self._nodes.get(node_id)
        if not node:
            return
        for child_id in node.children:
            self._dirty_transforms.add(child_id)
            self._propagate_dirty(child_id)

    def _update_world_transform(self, node_id: str):
        """Recalculate the world transform for a node."""
        node = self._nodes.get(node_id)
        if not node:
            return

        parent = self._nodes.get(node.parent_id)
        if parent:
            px, py = parent.world_transform.position
            pr = parent.world_transform.rotation
            psx, psy = parent.world_transform.scale

            import math
            cos_r = math.cos(pr)
            sin_r = math.sin(pr)

            lx, ly = node.transform.position
            wx = px + lx * cos_r * psx - ly * sin_r * psy
            wy = py + lx * sin_r * psx + ly * cos_r * psy

            node.world_transform.position = (wx, wy)
            node.world_transform.rotation = pr + node.transform.rotation
            node.world_transform.scale = (
                node.transform.scale[0] * psx,
                node.transform.scale[1] * psy,
            )
        else:
            node.world_transform = Transform2D(
                position=node.transform.position,
                rotation=node.transform.rotation,
                scale=node.transform.scale,
            )

    def update_transforms(self):
        """Update all dirty world transforms."""
        sorted_dirty = self._topological_sort_dirty()
        for node_id in sorted_dirty:
            self._update_world_transform(node_id)
        self._dirty_transforms.clear()

    def _topological_sort_dirty(self) -> List[str]:
        """Sort dirty nodes so parents are processed before children."""
        sorted_nodes: List[str] = []
        visited: Set[str] = set()

        def visit(node_id: str):
            if node_id in visited or node_id not in self._dirty_transforms:
                return
            node = self._nodes.get(node_id)
            if node and node.parent_id in self._dirty_transforms:
                visit(node.parent_id)
            visited.add(node_id)
            sorted_nodes.append(node_id)

        for node_id in self._dirty_transforms:
            visit(node_id)

        return sorted_nodes

    def find_by_tag(self, tag: str) -> List[SceneNode]:
        """Find all nodes with a specific tag."""
        node_ids = self._tag_index.get(tag, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_by_type(self, node_type: NodeType) -> List[SceneNode]:
        """Find all nodes of a specific type."""
        node_ids = self._type_index.get(node_type.value, set())
        return [self._nodes[nid] for nid in node_ids if nid in self._nodes]

    def find_by_name(self, name: str) -> List[SceneNode]:
        """Find all nodes with a specific name."""
        return [n for n in self._nodes.values() if n.name == name]

    def get_node(self, node_id: str) -> Optional[SceneNode]:
        """Get a node by ID."""
        return self._nodes.get(node_id)

    def get_children(self, node_id: str) -> List[SceneNode]:
        """Get all children of a node."""
        node = self._nodes.get(node_id)
        if not node:
            return []
        return [self._nodes[cid] for cid in node.children if cid in self._nodes]

    def get_descendants(self, node_id: str) -> List[SceneNode]:
        """Get all descendants of a node recursively."""
        descendants = []
        for child_id in self._nodes.get(node_id, SceneNode()).children:
            if child_id in self._nodes:
                descendants.append(self._nodes[child_id])
                descendants.extend(self.get_descendants(child_id))
        return descendants

    def get_path(self, node_id: str) -> List[SceneNode]:
        """Get the path from root to a node."""
        path = []
        current_id = node_id
        while current_id:
            node = self._nodes.get(current_id)
            if not node:
                break
            path.insert(0, node)
            current_id = node.parent_id
        return path

    def set_active(self, node_id: str, active: bool):
        """Set a node's active state."""
        node = self._nodes.get(node_id)
        if node:
            node.is_active = active
            for child_id in node.children:
                self.set_active(child_id, active)

    def set_visible(self, node_id: str, visible: bool):
        """Set a node's visibility."""
        node = self._nodes.get(node_id)
        if node:
            node.is_visible = visible

    def add_tag(self, node_id: str, tag: str):
        """Add a tag to a node."""
        node = self._nodes.get(node_id)
        if node and tag not in node.tags:
            node.tags.append(tag)
            self._tag_index.setdefault(tag, set()).add(node_id)

    def remove_tag(self, node_id: str, tag: str):
        """Remove a tag from a node."""
        node = self._nodes.get(node_id)
        if node and tag in node.tags:
            node.tags.remove(tag)
            self._tag_index.get(tag, set()).discard(node_id)

    def get_root(self) -> SceneNode:
        """Get the root node."""
        return self._nodes.get(self._root_id, SceneNode(name="Root"))

    def get_stats(self) -> Dict[str, Any]:
        """Get scene graph statistics."""
        return {
            "total_nodes": len(self._nodes),
            "root_id": self._root_id,
            "dirty_transforms": len(self._dirty_transforms),
            "tags_indexed": len(self._tag_index),
            "type_distribution": self._get_type_distribution(),
        }

    def _get_type_distribution(self) -> Dict[str, int]:
        dist: Dict[str, int] = {}
        for n in self._nodes.values():
            t = n.node_type.value
            dist[t] = dist.get(t, 0) + 1
        return dist


def get_scene_graph() -> EngineSceneGraph:
    return EngineSceneGraph.get_instance()