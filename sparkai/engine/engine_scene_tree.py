"""
SparkLabs Engine - Scene Tree System

Hierarchical scene graph management for the SparkLabs AI-native game
engine. Provides node parenting, scene lifecycle, node group management,
and scene switching. The design follows the scene tree concept from
Godot Engine and Phaser, with a flat-dict node storage model and
parent-child ID references.

Architecture:
  SceneTree (singleton, thread-safe)
    |-- SceneNode (dataclass) — individual node in the tree
    |-- NodeType (enum) — node classification
    |-- NodeLifecycle (enum) — node lifecycle state machine
    |-- Root node → children form the full scene graph

Usage:
    st = get_scene_tree()
    st.initialize()
    player = st.create_node("Player", NodeType.ENTITY, st.get_root().id)
    st.add_tag(player.id, "player")
    st.move_node(player.id, {"x": 10.0, "y": 0.0, "z": 5.0})
    tree = st.get_scene_graph()
    st.shutdown()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeType(Enum):
    """Classification of a node within the scene tree."""
    ROOT = "root"
    SCENE = "scene"
    ENTITY = "entity"
    CAMERA = "camera"
    LIGHT = "light"
    SPRITE = "sprite"
    UI = "ui"
    PARTICLE = "particle"
    AUDIO = "audio"
    PHYSICS = "physics"
    CUSTOM = "custom"


class NodeLifecycle(Enum):
    """Lifecycle states for scene tree nodes."""
    CREATED = "created"
    ENTERING_TREE = "entering_tree"
    READY = "ready"
    PROCESSING = "processing"
    EXITING_TREE = "exiting_tree"
    DESTROYED = "destroyed"


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SceneNode:
    """A node in the hierarchical scene tree.

    Each node maintains references to its parent and children via
    string IDs, enabling a flat storage model with fast lookups.
    Nodes carry a 3D transform, visibility and enabled flags, tags
    for group queries, and arbitrary property and metadata dicts.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Node"
    node_type: NodeType = NodeType.ENTITY
    lifecycle: NodeLifecycle = NodeLifecycle.CREATED
    parent_id: Optional[str] = None
    children_ids: List[str] = field(default_factory=list)
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    rotation: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0, "z": 0.0})
    scale: Dict[str, float] = field(default_factory=lambda: {"x": 1.0, "y": 1.0, "z": 1.0})
    visible: bool = True
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the node to a dictionary representation."""
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "lifecycle": self.lifecycle.value,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "position": dict(self.position),
            "rotation": dict(self.rotation),
            "scale": dict(self.scale),
            "visible": self.visible,
            "enabled": self.enabled,
            "tags": list(self.tags),
            "properties": dict(self.properties),
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def touch(self) -> None:
        """Update the last-modified timestamp."""
        self.updated_at = time.time()


# ---------------------------------------------------------------------------
# SceneTree (Singleton)
# ---------------------------------------------------------------------------

class SceneTree:
    """Main scene tree manager for the SparkLabs engine.

    Manages the full hierarchical node graph. Provides node creation,
    removal, reparenting, transform operations, tag-based queries, and
    lifecycle management. Uses a singleton pattern with double-checked
    locking and a ``threading.RLock`` for thread safety.
    """

    _instance: Optional["SceneTree"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized: bool = False
        self._nodes: Dict[str, SceneNode] = {}
        self._root_id: Optional[str] = None
        self._tag_index: Dict[str, List[str]] = {}
        self._is_running: bool = False

    @classmethod
    def get_instance(cls) -> "SceneTree":
        """Return the singleton SceneTree instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up the scene tree with a root node.

        Creates the root node and marks the tree as running. Safe to
        call multiple times — subsequent calls are no-ops.
        """
        with self._lock:
            if self._root_id is not None:
                return
            root = SceneNode(
                name="Root",
                node_type=NodeType.ROOT,
                lifecycle=NodeLifecycle.READY,
            )
            self._nodes[root.id] = root
            self._root_id = root.id
            self._is_running = True
            self._initialized = True

    def shutdown(self) -> None:
        """Perform a clean shutdown of the scene tree.

        Recursively marks all nodes as destroyed, clears the node
        registry and tag index, and resets internal state.
        """
        with self._lock:
            if self._root_id and self._root_id in self._nodes:
                self._destroy_recursive(self._root_id)
            self._nodes.clear()
            self._tag_index.clear()
            self._root_id = None
            self._is_running = False

    def _destroy_recursive(self, node_id: str) -> None:
        """Recursively mark a node and all descendants as DESTROYED."""
        node = self._nodes.get(node_id)
        if not node:
            return
        for child_id in list(node.children_ids):
            self._destroy_recursive(child_id)
        node.lifecycle = NodeLifecycle.DESTROYED

    # ------------------------------------------------------------------
    # Node Creation / Removal
    # ------------------------------------------------------------------

    def create_node(
        self,
        name: str,
        node_type: NodeType = NodeType.ENTITY,
        parent_id: Optional[str] = None,
        position: Optional[Dict[str, float]] = None,
        rotation: Optional[Dict[str, float]] = None,
        scale: Optional[Dict[str, float]] = None,
    ) -> Optional[SceneNode]:
        """Create a new node and attach it to the specified parent.

        Args:
            name: Human-readable name for the node.
            node_type: Classification from :class:`NodeType`.
            parent_id: ID of the parent node. Defaults to the root.
            position: Initial position ``{"x", "y", "z"}``.
            rotation: Initial rotation ``{"x", "y", "z"}`` in degrees.
            scale: Initial scale ``{"x", "y", "z"}``.

        Returns:
            The newly created :class:`SceneNode`, or None if the parent
            is not found or the tree is not initialized.
        """
        with self._lock:
            if self._root_id is None:
                return None
            target_parent_id = parent_id or self._root_id
            parent = self._nodes.get(target_parent_id)
            if parent is None:
                return None
            node = SceneNode(
                name=name,
                node_type=node_type,
                parent_id=target_parent_id,
                position=position or {"x": 0.0, "y": 0.0, "z": 0.0},
                rotation=rotation or {"x": 0.0, "y": 0.0, "z": 0.0},
                scale=scale or {"x": 1.0, "y": 1.0, "z": 1.0},
            )
            self._nodes[node.id] = node
            parent.children_ids.append(node.id)
            self._index_tags(node)
            node.lifecycle = NodeLifecycle.ENTERING_TREE
            node.lifecycle = NodeLifecycle.READY
            node.touch()
            return node

    def remove_node(self, node_id: str) -> bool:
        """Remove a node and all of its descendants.

        The root node cannot be removed. Returns True if removed.
        """
        with self._lock:
            if node_id == self._root_id:
                return False
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.lifecycle = NodeLifecycle.EXITING_TREE
            descendant_ids = self._collect_descendant_ids(node_id)

            if node.parent_id:
                parent = self._nodes.get(node.parent_id)
                if parent and node_id in parent.children_ids:
                    parent.children_ids.remove(node_id)

            for did in descendant_ids:
                removed = self._nodes.pop(did, None)
                if removed:
                    self._unindex_tags(removed)
            return True

    def _collect_descendant_ids(self, node_id: str) -> List[str]:
        """Collect a node and all its descendant IDs recursively."""
        ids: List[str] = [node_id]
        node = self._nodes.get(node_id)
        if node:
            for child_id in node.children_ids:
                ids.extend(self._collect_descendant_ids(child_id))
        return ids

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get_node(self, node_id: str) -> Optional[SceneNode]:
        """Get a node by its ID."""
        with self._lock:
            return self._nodes.get(node_id)

    def get_node_by_name(self, name: str) -> Optional[SceneNode]:
        """Find the first node whose name matches the given string.

        Performs a depth-first search from the root.
        """
        with self._lock:
            if self._root_id is None:
                return None
            return self._find_by_name_dfs(self._root_id, name)

    def _find_by_name_dfs(self, current_id: str, name: str) -> Optional[SceneNode]:
        """Depth-first search for a node by name."""
        node = self._nodes.get(current_id)
        if node is None:
            return None
        if node.name == name:
            return node
        for child_id in node.children_ids:
            found = self._find_by_name_dfs(child_id, name)
            if found is not None:
                return found
        return None

    def get_root(self) -> Optional[SceneNode]:
        """Get the root node of the scene tree."""
        with self._lock:
            if self._root_id is None:
                return None
            return self._nodes.get(self._root_id)

    # ------------------------------------------------------------------
    # Hierarchy
    # ------------------------------------------------------------------

    def set_parent(self, node_id: str, new_parent_id: str) -> bool:
        """Reparent a node to a different parent.

        Validates that the operation does not create a cycle. The root
        node cannot be reparented.
        """
        with self._lock:
            if node_id == self._root_id:
                return False
            node = self._nodes.get(node_id)
            new_parent = self._nodes.get(new_parent_id)
            if node is None or new_parent is None:
                return False
            if self._is_ancestor_of(node_id, new_parent_id):
                return False

            if node.parent_id:
                old_parent = self._nodes.get(node.parent_id)
                if old_parent and node_id in old_parent.children_ids:
                    old_parent.children_ids.remove(node_id)

            node.parent_id = new_parent_id
            new_parent.children_ids.append(node_id)
            node.touch()
            return True

    def _is_ancestor_of(self, ancestor_id: str, node_id: str) -> bool:
        """Check whether ancestor_id is an ancestor of node_id."""
        current_id = node_id
        while current_id:
            node = self._nodes.get(current_id)
            if node is None:
                return False
            if node.parent_id == ancestor_id:
                return True
            current_id = node.parent_id or ""
        return False

    def get_children(self, node_id: str) -> List[SceneNode]:
        """Get the direct children of a node."""
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return []
            return [
                self._nodes[cid]
                for cid in node.children_ids
                if cid in self._nodes
            ]

    # ------------------------------------------------------------------
    # Transform
    # ------------------------------------------------------------------

    def move_node(self, node_id: str, position: Dict[str, float]) -> bool:
        """Set the local position of a node.

        Args:
            node_id: ID of the node.
            position: New position ``{"x", "y", "z"}``.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.position["x"] = position.get("x", node.position["x"])
            node.position["y"] = position.get("y", node.position["y"])
            node.position["z"] = position.get("z", node.position["z"])
            node.touch()
            return True

    def rotate_node(self, node_id: str, rotation: Dict[str, float]) -> bool:
        """Set the local rotation of a node (Euler angles in degrees).

        Args:
            node_id: ID of the node.
            rotation: New rotation ``{"x", "y", "z"}`` in degrees.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.rotation["x"] = rotation.get("x", node.rotation["x"])
            node.rotation["y"] = rotation.get("y", node.rotation["y"])
            node.rotation["z"] = rotation.get("z", node.rotation["z"])
            node.touch()
            return True

    def scale_node(self, node_id: str, scale: Dict[str, float]) -> bool:
        """Set the local scale of a node.

        Args:
            node_id: ID of the node.
            scale: New scale ``{"x", "y", "z"}``.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.scale["x"] = scale.get("x", node.scale["x"])
            node.scale["y"] = scale.get("y", node.scale["y"])
            node.scale["z"] = scale.get("z", node.scale["z"])
            node.touch()
            return True

    # ------------------------------------------------------------------
    # Visibility / Enabled
    # ------------------------------------------------------------------

    def set_visible(self, node_id: str, visible: bool) -> bool:
        """Set the visibility state of a node.

        When a node is not visible, it and its children are excluded
        from rendering. This does not affect processing.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.visible = visible
            node.touch()
            return True

    def set_enabled(self, node_id: str, enabled: bool) -> bool:
        """Set the enabled state of a node.

        When a node is disabled, it and its children are excluded from
        processing and input handling.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            node.enabled = enabled
            node.touch()
            return True

    # ------------------------------------------------------------------
    # Tags
    # ------------------------------------------------------------------

    def add_tag(self, node_id: str, tag: str) -> bool:
        """Add a tag to a node for group-based queries.

        Duplicate tags are silently ignored.
        """
        with self._lock:
            node = self._nodes.get(node_id)
            if node is None:
                return False
            if tag in node.tags:
                return False
            node.tags.append(tag)
            self._tag_index.setdefault(tag, []).append(node_id)
            node.touch()
            return True

    def find_by_tag(self, tag: str) -> List[SceneNode]:
        """Find all nodes that carry a specific tag."""
        with self._lock:
            node_ids = self._tag_index.get(tag, [])
            return [
                self._nodes[nid]
                for nid in node_ids
                if nid in self._nodes
            ]

    def _index_tags(self, node: SceneNode) -> None:
        """Register a node's tags in the tag index."""
        for tag in node.tags:
            self._tag_index.setdefault(tag, []).append(node.id)

    def _unindex_tags(self, node: SceneNode) -> None:
        """Remove a node's tags from the tag index."""
        for tag in node.tags:
            entries = self._tag_index.get(tag)
            if entries and node.id in entries:
                entries.remove(node.id)

    # ------------------------------------------------------------------
    # Scene Graph
    # ------------------------------------------------------------------

    def get_scene_graph(self) -> Optional[Dict[str, Any]]:
        """Get the full hierarchical tree structure as a dictionary.

        The root node is rendered as the top-level entry, with each
        node's children nested under a ``"children"`` key.
        """
        with self._lock:
            if self._root_id is None:
                return None
            return self._build_tree_dict(self._root_id)

    def _build_tree_dict(self, node_id: str) -> Dict[str, Any]:
        """Recursively build a nested dictionary for a subtree."""
        node = self._nodes.get(node_id)
        if node is None:
            return {}
        return {
            "id": node.id,
            "name": node.name,
            "node_type": node.node_type.value,
            "lifecycle": node.lifecycle.value,
            "position": dict(node.position),
            "rotation": dict(node.rotation),
            "scale": dict(node.scale),
            "visible": node.visible,
            "enabled": node.enabled,
            "tags": list(node.tags),
            "properties": dict(node.properties),
            "metadata": dict(node.metadata),
            "children": [
                self._build_tree_dict(child_id)
                for child_id in node.children_ids
            ],
        }

    # ------------------------------------------------------------------
    # Status
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the scene tree's current state.

        Includes node counts, root information, tag index statistics,
        and a breakdown of node types and lifecycle states.
        """
        with self._lock:
            type_breakdown: Dict[str, int] = {}
            lifecycle_breakdown: Dict[str, int] = {}
            for node in self._nodes.values():
                t = node.node_type.value
                type_breakdown[t] = type_breakdown.get(t, 0) + 1
                lc = node.lifecycle.value
                lifecycle_breakdown[lc] = lifecycle_breakdown.get(lc, 0) + 1

            max_depth = 0
            if self._root_id:
                max_depth = self._compute_max_depth(self._root_id, 0)

            return {
                "running": self._is_running,
                "total_nodes": len(self._nodes),
                "root_id": self._root_id,
                "max_depth": max_depth,
                "tag_index_size": len(self._tag_index),
                "node_type_breakdown": type_breakdown,
                "lifecycle_breakdown": lifecycle_breakdown,
            }

    def _compute_max_depth(self, node_id: str, current_depth: int) -> int:
        """Compute the maximum depth of a subtree."""
        node = self._nodes.get(node_id)
        if node is None or not node.children_ids:
            return current_depth
        return max(
            self._compute_max_depth(child_id, current_depth + 1)
            for child_id in node.children_ids
        )


# ---------------------------------------------------------------------------
# Convenience Accessor
# ---------------------------------------------------------------------------

def get_scene_tree() -> SceneTree:
    """Get the singleton :class:`SceneTree` instance."""
    return SceneTree.get_instance()