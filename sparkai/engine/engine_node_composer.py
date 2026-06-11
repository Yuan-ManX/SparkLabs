"""
SparkLabs Engine - Node Composer

A node-based scene composition system that enables hierarchical game
object construction through a tree of composable nodes. Each node
represents a functional unit — rendering, physics, audio, logic, or
transformation — that can be arranged in parent-child hierarchies
to create complex game scenes with reusable component structures.

The node composer follows a scene-tree architecture where nodes form
a rooted tree with scene nodes at the top, branch nodes for organization,
and leaf nodes for concrete game objects. Nodes communicate through
signals, inherit transforms, and can be dynamically created, moved,
grouped, and destroyed during runtime.

Architecture:
  EngineNodeComposer (Singleton)
    |-- SceneNode (base unit of composition)
    |-- NodeTree (rooted tree of scene nodes)
    |-- NodeType (categorization of node functionality)
    |-- NodeSignal (decoupled inter-node communication)
    |-- NodePath (hierarchical addressing like filesystem paths)
    |-- Transform2D (2D position, rotation, scale with inheritance)
    |-- NodeGroup (logical grouping for batch operations)

Core Capabilities:
  - create_node: Instantiate a node of a given type
  - build_tree: Construct a node tree from a scene definition
  - add_child: Attach a child node with inherited transform
  - reparent: Move a node to a different parent
  - send_signal: Emit a signal down/up the tree
  - query_nodes: Find nodes by type, name, or path
  - freeze_branch: Pause processing for a sub-tree
  - export_tree: Serialize a node tree to a portable format
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class NodeType(Enum):
    """Categorization of node functionality."""
    ROOT = "root"
    SCENE = "scene"
    SPRITE = "sprite"
    TEXT = "text"
    CAMERA = "camera"
    AUDIO = "audio"
    PHYSICS_BODY = "physics_body"
    COLLIDER = "collider"
    ANIMATION = "animation"
    LIGHT = "light"
    PARTICLE = "particle"
    UI = "ui"
    TIMER = "timer"
    GROUP = "group"
    PATH = "path"
    CUSTOM = "custom"


class NodeState(Enum):
    """Runtime lifecycle state of a node."""
    CREATED = "created"
    READY = "ready"
    ACTIVE = "active"
    PROCESSING = "processing"
    FROZEN = "frozen"
    DESTROYED = "destroyed"


class SignalDirection(Enum):
    """Direction for signal propagation through the tree."""
    DOWNWARD = "downward"
    UPWARD = "upward"
    BROADCAST = "broadcast"
    TARGETED = "targeted"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class Transform2D:
    """2D transform with parent-inherited world position.

    Attributes:
        position_x: Local X position.
        position_y: Local Y position.
        rotation_degrees: Local rotation in degrees.
        scale_x: Local horizontal scale.
        scale_y: Local vertical scale.
        world_x: Computed world X (position + parent chain).
        world_y: Computed world Y (position + parent chain).
        world_rotation: Computed world rotation.
        world_scale_x: Computed world horizontal scale.
        world_scale_y: Computed world vertical scale.
    """
    position_x: float = 0.0
    position_y: float = 0.0
    rotation_degrees: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    world_x: float = 0.0
    world_y: float = 0.0
    world_rotation: float = 0.0
    world_scale_x: float = 1.0
    world_scale_y: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "local": {
                "x": self.position_x,
                "y": self.position_y,
                "rotation": self.rotation_degrees,
                "scale_x": self.scale_x,
                "scale_y": self.scale_y,
            },
            "world": {
                "x": round(self.world_x, 4),
                "y": round(self.world_y, 4),
                "rotation": round(self.world_rotation, 4),
                "scale_x": round(self.world_scale_x, 4),
                "scale_y": round(self.world_scale_y, 4),
            },
        }


@dataclass
class NodeSignal:
    """A decoupled message sent between nodes.

    Attributes:
        signal_id: Unique signal identifier.
        name: Signal name (e.g., 'collided', 'clicked', 'finished').
        source_node_id: Node that emitted the signal.
        data: Signal payload.
        direction: Propagation direction.
        target_node_id: Target for directed signals.
    """
    signal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    source_node_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    direction: SignalDirection = SignalDirection.DOWNWARD
    target_node_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "signal_id": self.signal_id,
            "name": self.name,
            "source_node_id": self.source_node_id,
            "data": dict(self.data),
            "direction": self.direction.value,
            "target_node_id": self.target_node_id,
        }


@dataclass
class SceneNode:
    """The base unit of scene composition in the node tree.

    Nodes form a rooted tree where each node can have children that
    inherit transforms. Nodes communicate via signals and can carry
    type-specific properties for rendering, physics, audio, and logic.

    Attributes:
        node_id: Unique node identifier.
        name: Display name.
        node_type: Functional category.
        transform: Local and world transform.
        parent_id: Parent node identifier (empty string for root).
        children_ids: Ordered child node identifiers.
        state: Runtime lifecycle state.
        properties: Type-specific configuration.
        tags: Searchable labels.
        signals: Connected signal handlers (signal_name → handler_callable).
        z_index: Rendering order within siblings.
        visible: Whether the node is rendered.
        paused: Whether node processing is paused.
    """
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: NodeType = NodeType.GROUP
    transform: Transform2D = field(default_factory=Transform2D)
    parent_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    state: NodeState = NodeState.CREATED
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    signals: Dict[str, List[str]] = field(default_factory=dict)
    z_index: int = 0
    visible: bool = True
    paused: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "transform": self.transform.to_dict(),
            "parent_id": self.parent_id,
            "children_count": len(self.children_ids),
            "state": self.state.value,
            "properties": dict(self.properties),
            "tags": list(self.tags),
            "z_index": self.z_index,
            "visible": self.visible,
            "paused": self.paused,
        }


@dataclass
class NodeGroup:
    """A logical grouping of nodes for batch operations.

    Attributes:
        group_id: Unique group identifier.
        name: Group display name.
        node_ids: Member node identifiers.
        enabled: Whether the group is active.
        locked: Prevent modifications to group members.
    """
    group_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_ids: List[str] = field(default_factory=list)
    enabled: bool = True
    locked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "node_count": len(self.node_ids),
            "enabled": self.enabled,
            "locked": self.locked,
        }


@dataclass
class NodeTree:
    """A rooted tree of scene nodes representing a complete composition.

    Attributes:
        tree_id: Unique tree identifier.
        name: Tree display name.
        root_node_id: Root node identifier.
        nodes: All nodes keyed by node_id.
        groups: Logical node groupings.
        signal_handlers: Global signal handler registry.
        created_at: Creation timestamp.
        metadata: Arbitrary tree metadata.
    """
    tree_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_node_id: str = ""
    nodes: Dict[str, SceneNode] = field(default_factory=dict)
    groups: List[NodeGroup] = field(default_factory=list)
    signal_handlers: Dict[str, Callable] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes),
            "group_count": len(self.groups),
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
            "nodes": {
                nid: node.to_dict() for nid, node in self.nodes.items()
            },
            "groups": [g.to_dict() for g in self.groups],
        }


# ---------------------------------------------------------------------------
# Engine Node Composer (Singleton)
# ---------------------------------------------------------------------------


class EngineNodeComposer:
    """
    Node-based scene composition system for hierarchical game construction.

    Provides a scene-tree architecture where composable nodes form a rooted
    tree, enabling complex game scenes through reusable component hierarchies.
    Nodes communicate via signals, inherit transforms, and support dynamic
    creation, reparenting, grouping, and destruction during runtime.

    Features:
      - Node tree with hierarchical transform inheritance
      - Signal-based decoupled inter-node communication
      - Spatial path-based node addressing (/root/scene/player)
      - Dynamic reparenting and tree restructuring
      - Batch operations via node groups
      - Freeze/thaw for sub-tree processing control
      - Portable tree export and import
      - Comprehensive node query by type, name, path, or tag
    """

    _instance: Optional["EngineNodeComposer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineNodeComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._trees: Dict[str, NodeTree] = {}
        self._signal_queue: List[NodeSignal] = []
        self._total_nodes_created: int = 0
        self._total_nodes_destroyed: int = 0

    # ------------------------------------------------------------------
    # Node Creation
    # ------------------------------------------------------------------

    def create_node(
        self,
        name: str = "",
        node_type: NodeType = NodeType.GROUP,
        position_x: float = 0.0,
        position_y: float = 0.0,
        rotation_degrees: float = 0.0,
        scale_x: float = 1.0,
        scale_y: float = 1.0,
        properties: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
    ) -> SceneNode:
        """
        Create a new scene node.

        Args:
            name: Display name.
            node_type: Functional category.
            position_x: Local X position.
            position_y: Local Y position.
            rotation_degrees: Local rotation.
            scale_x: Horizontal scale.
            scale_y: Vertical scale.
            properties: Type-specific configuration.
            tags: Searchable labels.

        Returns:
            Created SceneNode.
        """
        transform = Transform2D(
            position_x=position_x,
            position_y=position_y,
            rotation_degrees=rotation_degrees,
            scale_x=scale_x,
            scale_y=scale_y,
            world_x=position_x,
            world_y=position_y,
            world_rotation=rotation_degrees,
            world_scale_x=scale_x,
            world_scale_y=scale_y,
        )

        node = SceneNode(
            name=name,
            node_type=node_type,
            transform=transform,
            properties=properties or {},
            tags=tags or [],
        )
        self._total_nodes_created += 1
        return node

    # ------------------------------------------------------------------
    # Tree Management
    # ------------------------------------------------------------------

    def build_tree(
        self,
        name: str,
        root_name: str = "Root",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> NodeTree:
        """
        Create a new node tree with a root node.

        Args:
            name: Tree display name.
            root_name: Root node name.
            metadata: Tree-level metadata.

        Returns:
            Created NodeTree.
        """
        root = self.create_node(name=root_name, node_type=NodeType.ROOT)
        root.state = NodeState.ACTIVE

        tree = NodeTree(
            name=name,
            root_node_id=root.node_id,
            metadata=metadata or {},
        )
        tree.nodes[root.node_id] = root
        self._trees[tree.tree_id] = tree
        return tree

    def get_tree(self, tree_id: str) -> Optional[NodeTree]:
        """Retrieve a node tree by identifier."""
        return self._trees.get(tree_id)

    def list_trees(self) -> List[Dict[str, Any]]:
        """List all node trees."""
        return [
            {
                "tree_id": t.tree_id,
                "name": t.name,
                "node_count": len(t.nodes),
                "group_count": len(t.groups),
            }
            for t in self._trees.values()
        ]

    def delete_tree(self, tree_id: str) -> bool:
        """Delete an entire node tree."""
        return self._trees.pop(tree_id, None) is not None

    # ------------------------------------------------------------------
    # Node Hierarchy
    # ------------------------------------------------------------------

    def add_child(
        self, tree_id: str, parent_id: str, child: SceneNode
    ) -> bool:
        """
        Attach a child node to a parent with transform inheritance.

        Args:
            tree_id: Tree to modify.
            parent_id: Parent node identifier.
            child: Child node to attach.

        Returns:
            True if successfully attached.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return False

        parent = tree.nodes.get(parent_id)
        if not parent:
            return False

        # Remove from old parent
        if child.parent_id:
            old_parent = tree.nodes.get(child.parent_id)
            if old_parent and child.node_id in old_parent.children_ids:
                old_parent.children_ids.remove(child.node_id)

        # Attach to new parent
        child.parent_id = parent_id
        parent.children_ids.append(child.node_id)
        tree.nodes[child.node_id] = child

        # Propagate world transform
        self._propagate_transform(tree, child.node_id)

        return True

    def reparent(
        self, tree_id: str, node_id: str, new_parent_id: str
    ) -> bool:
        """
        Move a node to a different parent in the tree.

        Args:
            tree_id: Tree containing the node.
            node_id: Node to move.
            new_parent_id: Target parent node.

        Returns:
            True if reparented successfully.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return False

        node = tree.nodes.get(node_id)
        if not node:
            return False
        if node_id == new_parent_id:
            return False  # Cannot parent to self

        # Detach from old parent
        if node.parent_id:
            old_parent = tree.nodes.get(node.parent_id)
            if old_parent and node_id in old_parent.children_ids:
                old_parent.children_ids.remove(node_id)

        # Attach to new parent
        new_parent = tree.nodes.get(new_parent_id)
        if not new_parent:
            return False

        node.parent_id = new_parent_id
        new_parent.children_ids.append(node_id)

        # Propagate transform to reparented node and its subtree
        self._propagate_transform(tree, node_id)

        return True

    def remove_node(self, tree_id: str, node_id: str, recursive: bool = True) -> bool:
        """
        Remove a node from the tree.

        Args:
            tree_id: Tree containing the node.
            node_id: Node to remove.
            recursive: Also remove children.

        Returns:
            True if removed.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return False

        node = tree.nodes.get(node_id)
        if not node:
            return False

        # Cannot remove root
        if node_id == tree.root_node_id:
            return False

        if recursive:
            self._remove_subtree(tree, node_id)
        else:
            # Reparent children to node's parent
            for child_id in list(node.children_ids):
                self.reparent(tree_id, child_id, node.parent_id)

            # Remove from parent
            if node.parent_id:
                parent = tree.nodes.get(node.parent_id)
                if parent and node_id in parent.children_ids:
                    parent.children_ids.remove(node_id)

            del tree.nodes[node_id]

        self._total_nodes_destroyed += 1
        return True

    def _remove_subtree(self, tree: NodeTree, node_id: str):
        """Recursively remove a node and all its descendants."""
        node = tree.nodes.get(node_id)
        if not node:
            return

        for child_id in list(node.children_ids):
            self._remove_subtree(tree, child_id)

        if node.parent_id:
            parent = tree.nodes.get(node.parent_id)
            if parent and node_id in parent.children_ids:
                parent.children_ids.remove(node_id)

        del tree.nodes[node_id]

    def _propagate_transform(self, tree: NodeTree, node_id: str):
        """Recursively update world transforms for a node and its children."""
        node = tree.nodes.get(node_id)
        if not node:
            return

        # Compute world transform from parent
        if node.parent_id:
            parent = tree.nodes.get(node.parent_id)
            if parent:
                pw = parent.transform
                # World position
                cos_r = __import__("math").cos(__import__("math").radians(pw.world_rotation))
                sin_r = __import__("math").sin(__import__("math").radians(pw.world_rotation))
                node.transform.world_x = pw.world_x + node.transform.position_x * pw.world_scale_x * cos_r - node.transform.position_y * pw.world_scale_y * sin_r
                node.transform.world_y = pw.world_y + node.transform.position_x * pw.world_scale_x * sin_r + node.transform.position_y * pw.world_scale_y * cos_r
                # World rotation and scale
                node.transform.world_rotation = pw.world_rotation + node.transform.rotation_degrees
                node.transform.world_scale_x = pw.world_scale_x * node.transform.scale_x
                node.transform.world_scale_y = pw.world_scale_y * node.transform.scale_y
            else:
                self._set_world_to_local(node)
        else:
            self._set_world_to_local(node)

        # Propagate to children
        for child_id in node.children_ids:
            self._propagate_transform(tree, child_id)

    @staticmethod
    def _set_world_to_local(node: SceneNode):
        """Set world transform equal to local transform (root nodes)."""
        node.transform.world_x = node.transform.position_x
        node.transform.world_y = node.transform.position_y
        node.transform.world_rotation = node.transform.rotation_degrees
        node.transform.world_scale_x = node.transform.scale_x
        node.transform.world_scale_y = node.transform.scale_y

    # ------------------------------------------------------------------
    # Node Queries
    # ------------------------------------------------------------------

    def get_node(self, tree_id: str, node_id: str) -> Optional[SceneNode]:
        """Get a node by its identifier."""
        tree = self._trees.get(tree_id)
        return tree.nodes.get(node_id) if tree else None

    def get_node_by_path(self, tree_id: str, path: str) -> Optional[SceneNode]:
        """
        Find a node by its hierarchical path (e.g., '/root/scene/player').

        Args:
            tree_id: Tree to search.
            path: Slash-separated node path.

        Returns:
            Found node or None.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        parts = [p for p in path.strip("/").split("/") if p]
        if not parts:
            return None

        # Find root
        current = tree.nodes.get(tree.root_node_id)
        if not current or current.name != parts[0]:
            # Search for matching root-level node
            for nid in tree.nodes:
                node = tree.nodes[nid]
                if node.name == parts[0] and not node.parent_id:
                    current = node
                    break

        if not current:
            return None

        # Walk down the path
        for part in parts[1:]:
            found = None
            for child_id in current.children_ids:
                child = tree.nodes.get(child_id)
                if child and child.name == part:
                    found = child
                    break
            if not found:
                return None
            current = found

        return current

    def query_nodes(
        self,
        tree_id: str,
        node_type: Optional[NodeType] = None,
        name_pattern: Optional[str] = None,
        tags: Optional[List[str]] = None,
        state: Optional[NodeState] = None,
    ) -> List[SceneNode]:
        """
        Find nodes by type, name, tags, or state.

        Args:
            tree_id: Tree to search.
            node_type: Filter by node type.
            name_pattern: Filter by name (substring match).
            tags: Filter by tags (any match).
            state: Filter by lifecycle state.

        Returns:
            Matching nodes.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return []

        results: List[SceneNode] = []
        for node in tree.nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if name_pattern and name_pattern.lower() not in node.name.lower():
                continue
            if tags and not any(t in node.tags for t in tags):
                continue
            if state and node.state != state:
                continue
            results.append(node)

        return results

    def get_children(self, tree_id: str, node_id: str) -> List[SceneNode]:
        """Get all direct children of a node."""
        tree = self._trees.get(tree_id)
        if not tree:
            return []

        node = tree.nodes.get(node_id)
        if not node:
            return []

        return [
            tree.nodes[cid]
            for cid in node.children_ids
            if cid in tree.nodes
        ]

    def get_siblings(self, tree_id: str, node_id: str) -> List[SceneNode]:
        """Get all siblings of a node (excluding self)."""
        tree = self._trees.get(tree_id)
        if not tree:
            return []

        node = tree.nodes.get(node_id)
        if not node or not node.parent_id:
            return []

        parent = tree.nodes.get(node.parent_id)
        if not parent:
            return []

        return [
            tree.nodes[cid]
            for cid in parent.children_ids
            if cid in tree.nodes and cid != node_id
        ]

    # ------------------------------------------------------------------
    # Signal System
    # ------------------------------------------------------------------

    def connect_signal(
        self, tree_id: str, node_id: str, signal_name: str, handler_id: str
    ):
        """Register a signal handler on a node."""
        tree = self._trees.get(tree_id)
        if not tree:
            return
        node = tree.nodes.get(node_id)
        if not node:
            return
        if signal_name not in node.signals:
            node.signals[signal_name] = []
        node.signals[signal_name].append(handler_id)

    def disconnect_signal(
        self, tree_id: str, node_id: str, signal_name: str, handler_id: str
    ):
        """Unregister a signal handler from a node."""
        tree = self._trees.get(tree_id)
        if not tree:
            return
        node = tree.nodes.get(node_id)
        if node and signal_name in node.signals:
            if handler_id in node.signals[signal_name]:
                node.signals[signal_name].remove(handler_id)

    def send_signal(
        self,
        tree_id: str,
        signal_name: str,
        source_node_id: str,
        data: Optional[Dict[str, Any]] = None,
        direction: SignalDirection = SignalDirection.DOWNWARD,
        target_node_id: Optional[str] = None,
    ) -> List[str]:
        """
        Emit a signal through the node tree.

        The signal propagates according to the specified direction:
        - DOWNWARD: from source to all descendants
        - UPWARD: from source to ancestors
        - BROADCAST: to all nodes in the tree
        - TARGETED: to a specific node

        Args:
            tree_id: Tree to propagate through.
            signal_name: Signal identifier.
            source_node_id: Emitting node.
            data: Signal payload.
            direction: Propagation direction.
            target_node_id: Specific target for TARGETED direction.

        Returns:
            List of node IDs that received the signal.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return []

        signal = NodeSignal(
            name=signal_name,
            source_node_id=source_node_id,
            data=data or {},
            direction=direction,
            target_node_id=target_node_id,
        )

        recipients: List[str] = []

        if direction == SignalDirection.TARGETED and target_node_id:
            target = tree.nodes.get(target_node_id)
            if target and signal_name in target.signals:
                recipients.append(target_node_id)
        elif direction == SignalDirection.DOWNWARD:
            source = tree.nodes.get(source_node_id)
            if source:
                recipients = self._propagate_downward(tree, source.node_id, signal_name)
        elif direction == SignalDirection.UPWARD:
            node = tree.nodes.get(source_node_id)
            while node and node.parent_id:
                node = tree.nodes.get(node.parent_id)
                if node and signal_name in node.signals:
                    recipients.append(node.node_id)
        elif direction == SignalDirection.BROADCAST:
            for nid, node in tree.nodes.items():
                if signal_name in node.signals:
                    recipients.append(nid)

        self._signal_queue.append(signal)
        return recipients

    def _propagate_downward(
        self, tree: NodeTree, node_id: str, signal_name: str
    ) -> List[str]:
        """Recursively propagate a signal downward through children."""
        recipients: List[str] = []
        node = tree.nodes.get(node_id)
        if not node:
            return recipients

        if signal_name in node.signals:
            recipients.append(node_id)

        for child_id in node.children_ids:
            recipients.extend(
                self._propagate_downward(tree, child_id, signal_name)
            )

        return recipients

    # ------------------------------------------------------------------
    # Node Groups
    # ------------------------------------------------------------------

    def create_group(
        self, tree_id: str, name: str, node_ids: Optional[List[str]] = None
    ) -> Optional[NodeGroup]:
        """Create a logical group of nodes for batch operations."""
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        group = NodeGroup(
            name=name,
            node_ids=node_ids or [],
        )
        tree.groups.append(group)
        return group

    def add_to_group(self, tree_id: str, group_id: str, node_id: str) -> bool:
        """Add a node to a group."""
        tree = self._trees.get(tree_id)
        if not tree:
            return False
        for group in tree.groups:
            if group.group_id == group_id:
                if node_id not in group.node_ids:
                    group.node_ids.append(node_id)
                return True
        return False

    def set_group_visibility(
        self, tree_id: str, group_id: str, visible: bool
    ) -> int:
        """Toggle visibility for all nodes in a group."""
        tree = self._trees.get(tree_id)
        if not tree:
            return 0

        count = 0
        for group in tree.groups:
            if group.group_id == group_id:
                if group.locked:
                    return 0
                for nid in group.node_ids:
                    node = tree.nodes.get(nid)
                    if node:
                        node.visible = visible
                        count += 1
                break
        return count

    def freeze_branch(self, tree_id: str, node_id: str) -> int:
        """
        Pause processing for a node and all its descendants.

        Args:
            tree_id: Tree containing the branch.
            node_id: Root of the branch to freeze.

        Returns:
            Number of nodes frozen.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return 0

        node = tree.nodes.get(node_id)
        if not node:
            return 0

        count = self._set_branch_state(tree, node_id, NodeState.FROZEN)
        return count

    def thaw_branch(self, tree_id: str, node_id: str) -> int:
        """Resume processing for a frozen branch."""
        tree = self._trees.get(tree_id)
        if not tree:
            return 0

        node = tree.nodes.get(node_id)
        if not node:
            return 0

        count = self._set_branch_state(tree, node_id, NodeState.ACTIVE)
        return count

    def _set_branch_state(
        self, tree: NodeTree, node_id: str, state: NodeState
    ) -> int:
        """Recursively set state for a branch."""
        node = tree.nodes.get(node_id)
        if not node:
            return 0
        count = 1
        node.state = state
        for child_id in node.children_ids:
            count += self._set_branch_state(tree, child_id, state)
        return count

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_tree(self, tree_id: str) -> Optional[Dict[str, Any]]:
        """
        Serialize a complete node tree to a portable format.

        Args:
            tree_id: Tree to export.

        Returns:
            Serialized tree dict, or None if not found.
        """
        tree = self._trees.get(tree_id)
        if not tree:
            return None

        def _serialize_node(node_id: str) -> Dict[str, Any]:
            node = tree.nodes.get(node_id)
            if not node:
                return {}
            return {
                **node.to_dict(),
                "children": [
                    _serialize_node(cid) for cid in node.children_ids
                ],
            }

        return {
            "tree": {
                "tree_id": tree.tree_id,
                "name": tree.name,
                "metadata": dict(tree.metadata),
                "created_at": tree.created_at,
            },
            "root": _serialize_node(tree.root_node_id),
            "groups": [g.to_dict() for g in tree.groups],
            "node_count": len(tree.nodes),
            "exported_at": _time_module.time(),
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate node composer statistics."""
        total_nodes = sum(len(t.nodes) for t in self._trees.values())
        type_counts: Dict[str, int] = {}
        for tree in self._trees.values():
            for node in tree.nodes.values():
                t = node.node_type.value
                type_counts[t] = type_counts.get(t, 0) + 1

        return {
            "total_trees": len(self._trees),
            "total_nodes": total_nodes,
            "nodes_created": self._total_nodes_created,
            "nodes_destroyed": self._total_nodes_destroyed,
            "active_nodes": total_nodes,
            "node_types": type_counts,
            "total_groups": sum(len(t.groups) for t in self._trees.values()),
            "trees": [
                {
                    "tree_id": t.tree_id,
                    "name": t.name,
                    "node_count": len(t.nodes),
                    "group_count": len(t.groups),
                }
                for t in self._trees.values()
            ],
        }

    # ------------------------------------------------------------------
    # Singleton & Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineNodeComposer":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset the node composer to initial state."""
        with self._lock:
            self._trees.clear()
            self._signal_queue.clear()
            self._total_nodes_created = 0
            self._total_nodes_destroyed = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_node_composer() -> EngineNodeComposer:
    """Return the singleton EngineNodeComposer instance."""
    return EngineNodeComposer()