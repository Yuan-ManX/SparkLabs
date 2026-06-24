"""
SparkLabs Engine - Spatial Partition Engine

Octree for 3D and quadtree for 2D spatial partitioning. Used for
efficient collision detection, frustum culling, and nearest-neighbor
queries. Supports grid-based and BVH partitioning strategies.

Architecture:
  SpatialPartitionEngine (Singleton)
    |-- TreeNode           — spatial tree node with bounds, entries, and children
    |-- SpatialEntry       — registered entity with bounding box and metadata
    |-- BoundingBox        — axis-aligned bounding box for 2D/3D queries
    |-- QueryResult        — result record from spatial queries

Query Pipeline:
  1. Range Query    — all entries within a given bounding box
  2. KNN Query      — k nearest neighbors to a point
  3. Frustum Query  — entries visible within a camera frustum
  4. Raycast Query  — entries intersected by a ray
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PartitionType(Enum):
    """Type of spatial partitioning structure."""
    QUADTREE = "quadtree"
    OCTREE = "octree"
    GRID = "grid"
    BVH = "bvh"


class QueryType(Enum):
    """Type of spatial query operation."""
    RANGE = "range"
    KNN = "knn"
    FRUSTUM = "frustum"
    RAYCAST = "raycast"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BoundingBox:
    """Axis-aligned bounding box for 2D or 3D spatial queries."""

    min_x: float = 0.0
    min_y: float = 0.0
    min_z: float = 0.0
    max_x: float = 0.0
    max_y: float = 0.0
    max_z: float = 0.0

    def center(self) -> Tuple[float, float, float]:
        """Return the center point of the bounding box."""
        return (
            (self.min_x + self.max_x) * 0.5,
            (self.min_y + self.max_y) * 0.5,
            (self.min_z + self.max_z) * 0.5,
        )

    def size(self) -> Tuple[float, float, float]:
        """Return the dimensions (width, height, depth) of the bounding box."""
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
        )

    def volume(self) -> float:
        """Return the volume of the bounding box."""
        w, h, d = self.size()
        return w * h * d

    def contains_point(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a point lies within this bounding box."""
        return (
            self.min_x <= x <= self.max_x
            and self.min_y <= y <= self.max_y
            and self.min_z <= z <= self.max_z
        )

    def contains(self, other: BoundingBox) -> bool:
        """Check if another bounding box is fully contained within this one."""
        return (
            self.min_x <= other.min_x
            and self.min_y <= other.min_y
            and self.min_z <= other.min_z
            and self.max_x >= other.max_x
            and self.max_y >= other.max_y
            and self.max_z >= other.max_z
        )

    def intersects(self, other: BoundingBox) -> bool:
        """Check if another bounding box overlaps with this one."""
        return (
            self.max_x > other.min_x
            and self.min_x < other.max_x
            and self.max_y > other.min_y
            and self.min_y < other.max_y
            and self.max_z > other.min_z
            and self.min_z < other.max_z
        )

    def expand(self, amount: float) -> BoundingBox:
        """Return a new bounding box expanded by the given amount on all sides."""
        return BoundingBox(
            min_x=self.min_x - amount,
            min_y=self.min_y - amount,
            min_z=self.min_z - amount,
            max_x=self.max_x + amount,
            max_y=self.max_y + amount,
            max_z=self.max_z + amount,
        )

    def distance_to_point(self, x: float, y: float, z: float = 0.0) -> float:
        """Compute the minimum distance from a point to this bounding box."""
        dx = max(self.min_x - x, 0.0, x - self.max_x)
        dy = max(self.min_y - y, 0.0, y - self.max_y)
        dz = max(self.min_z - z, 0.0, z - self.max_z)
        return math.sqrt(dx * dx + dy * dy + dz * dz)

    def to_dict(self) -> Dict[str, float]:
        return {
            "min_x": self.min_x,
            "min_y": self.min_y,
            "min_z": self.min_z,
            "max_x": self.max_x,
            "max_y": self.max_y,
            "max_z": self.max_z,
        }

    @classmethod
    def from_center_half(
        cls, cx: float, cy: float, cz: float, hw: float, hh: float, hd: float
    ) -> BoundingBox:
        """Create a bounding box from a center point and half-extents."""
        return cls(
            min_x=cx - hw, min_y=cy - hh, min_z=cz - hd,
            max_x=cx + hw, max_y=cy + hh, max_z=cz + hd,
        )


@dataclass
class SpatialEntry:
    """An entity registered in the spatial partition tree."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    bounds: BoundingBox = field(default_factory=BoundingBox)
    entity_id: str = ""
    entity_type: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bounds": self.bounds.to_dict(),
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
        }


@dataclass
class TreeNode:
    """A node in the spatial partition tree (octree or quadtree)."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    bounds: BoundingBox = field(default_factory=BoundingBox)
    depth: int = 0
    max_depth: int = 8
    entries: List[SpatialEntry] = field(default_factory=list)
    children: List[TreeNode] = field(default_factory=list)
    is_leaf: bool = True
    is_split: bool = False
    partition_type: PartitionType = PartitionType.OCTREE
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "bounds": self.bounds.to_dict(),
            "depth": self.depth,
            "max_depth": self.max_depth,
            "entry_count": len(self.entries),
            "child_count": len(self.children),
            "is_leaf": self.is_leaf,
            "is_split": self.is_split,
            "partition_type": self.partition_type.value,
            "metadata": dict(self.metadata),
        }


@dataclass
class QueryResult:
    """Result record from a spatial query operation."""

    entry_id: str = ""
    entity_id: str = ""
    distance: float = 0.0
    relevance: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "entity_id": self.entity_id,
            "distance": round(self.distance, 4),
            "relevance": round(self.relevance, 4),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Spatial Partition Engine
# ---------------------------------------------------------------------------

class SpatialPartitionEngine:
    """
    Spatial partitioning engine for efficient scene queries.

    Supports octree (3D) and quadtree (2D) partitioning, grid-based spatial
    hashing, and BVH structures. Provides range queries, k-nearest-neighbor
    searches, frustum culling, and raycast intersection tests.
    """

    _instance: Optional["SpatialPartitionEngine"] = None
    _lock = threading.RLock()

    _DEFAULT_MAX_DEPTH: int = 8
    _DEFAULT_MAX_ENTRIES_PER_NODE: int = 8
    _DEFAULT_MIN_NODE_SIZE: float = 0.01

    def __new__(cls) -> "SpatialPartitionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SpatialPartitionEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._trees: Dict[str, TreeNode] = {}
        self._entry_lookup: Dict[str, str] = {}  # entry_id -> tree_id
        self._grid: Dict[Tuple[int, int, int], List[str]] = {}
        self._grid_cell_size: float = 4.0
        self._query_count: int = 0
        self._insert_count: int = 0
        self._remove_count: int = 0
        self._creation_time: float = time.time()

    # ------------------------------------------------------------------
    # Tree Management
    # ------------------------------------------------------------------

    def create_tree(
        self,
        name: str,
        partition_type: PartitionType = PartitionType.OCTREE,
        bounds: Optional[BoundingBox] = None,
        max_depth: int = _DEFAULT_MAX_DEPTH,
        max_entries: int = _DEFAULT_MAX_ENTRIES_PER_NODE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> TreeNode:
        """Create a new spatial partition tree.

        Args:
            name: Unique identifier for the tree.
            partition_type: The type of partitioning structure to use.
            bounds: World-space bounds for the tree. Defaults to a large cube.
            max_depth: Maximum subdivision depth.
            max_entries: Maximum entries per leaf node before splitting.
            metadata: Optional arbitrary metadata for the tree.

        Returns:
            The newly created root TreeNode.
        """
        with self._lock:
            if bounds is None:
                bounds = BoundingBox(
                    min_x=-1000.0, min_y=-1000.0, min_z=-1000.0,
                    max_x=1000.0, max_y=1000.0, max_z=1000.0,
                )

            tree_id = uuid.uuid4().hex[:12]
            root = TreeNode(
                id=tree_id,
                bounds=bounds,
                depth=0,
                max_depth=max_depth,
                entries=[],
                children=[],
                is_leaf=True,
                is_split=False,
                partition_type=partition_type,
                metadata={
                    "name": name,
                    "max_entries_per_node": max_entries,
                    **(metadata or {}),
                },
            )
            self._trees[tree_id] = root
            return root

    def insert(self, tree_id: str, entry: SpatialEntry) -> bool:
        """Insert a spatial entry into the specified tree.

        The entry is placed into the deepest node whose bounds fully contain
        the entry's bounds. If the node exceeds the maximum entry count, it
        is split into children.
        """
        with self._lock:
            root = self._trees.get(tree_id)
            if root is None:
                return False
            if entry.id in self._entry_lookup:
                return False
            success = self._insert_into_node(root, entry)
            if success:
                self._entry_lookup[entry.id] = tree_id
                self._insert_count += 1
            return success

    def _insert_into_node(self, node: TreeNode, entry: SpatialEntry) -> bool:
        """Recursively insert an entry into the appropriate tree node."""
        if not node.bounds.contains(entry.bounds):
            full_enclosure = (
                entry.bounds.min_x >= node.bounds.min_x
                and entry.bounds.min_y >= node.bounds.min_y
                and entry.bounds.min_z >= node.bounds.min_z
                and entry.bounds.max_x <= node.bounds.max_x
                and entry.bounds.max_y <= node.bounds.max_y
                and entry.bounds.max_z <= node.bounds.max_z
            )
            if not full_enclosure:
                expanded = node.bounds
                expanded = BoundingBox(
                    min_x=min(expanded.min_x, entry.bounds.min_x),
                    min_y=min(expanded.min_y, entry.bounds.min_y),
                    min_z=min(expanded.min_z, entry.bounds.min_z),
                    max_x=max(expanded.max_x, entry.bounds.max_x),
                    max_y=max(expanded.max_y, entry.bounds.max_y),
                    max_z=max(expanded.max_z, entry.bounds.max_z),
                )
                node.bounds = expanded

        if node.is_leaf:
            max_entries = node.metadata.get("max_entries_per_node", self._DEFAULT_MAX_ENTRIES_PER_NODE)
            node.entries.append(entry)

            # Check if we should split
            w, h, d = node.bounds.size()
            min_dim = min(w, h, d)
            if (
                len(node.entries) > max_entries
                and node.depth < node.max_depth
                and min_dim > self._DEFAULT_MIN_NODE_SIZE
            ):
                self._split_node(node)
            return True

        # Find the child that contains the entry
        inserted = False
        for child in node.children:
            if child.bounds.contains(entry.bounds):
                inserted = self._insert_into_node(child, entry)
                if inserted:
                    return True

        if not inserted:
            # Entry doesn't fit perfectly in any child, store at this node
            node.entries.append(entry)
            return True

        return False

    def _split_node(self, node: TreeNode) -> None:
        """Split a leaf node into children based on the partition type."""
        if node.partition_type == PartitionType.OCTREE:
            self._split_octree(node)
        elif node.partition_type == PartitionType.QUADTREE:
            self._split_quadtree(node)
        elif node.partition_type == PartitionType.BVH:
            self._split_bvh(node)
        elif node.partition_type == PartitionType.GRID:
            self._split_grid(node)

    def _split_octree(self, node: TreeNode) -> None:
        """Split a node into 8 octants for 3D space."""
        cx, cy, cz = node.bounds.center()
        node.is_leaf = False
        node.is_split = True

        for i in range(8):
            lx = i & 1
            ly = (i >> 1) & 1
            lz = (i >> 2) & 1

            child_bounds = BoundingBox(
                min_x=node.bounds.min_x if lx == 0 else cx,
                min_y=node.bounds.min_y if ly == 0 else cy,
                min_z=node.bounds.min_z if lz == 0 else cz,
                max_x=cx if lx == 0 else node.bounds.max_x,
                max_y=cy if ly == 0 else node.bounds.max_y,
                max_z=cz if lz == 0 else node.bounds.max_z,
            )

            child = TreeNode(
                id=uuid.uuid4().hex[:12],
                bounds=child_bounds,
                depth=node.depth + 1,
                max_depth=node.max_depth,
                entries=[],
                children=[],
                is_leaf=True,
                is_split=False,
                partition_type=PartitionType.OCTREE,
                metadata={"max_entries_per_node": node.metadata.get("max_entries_per_node", self._DEFAULT_MAX_ENTRIES_PER_NODE)},
            )
            node.children.append(child)

        # Redistribute entries to children
        redistributed: List[SpatialEntry] = []
        for entry in node.entries:
            placed = False
            for child in node.children:
                if child.bounds.contains(entry.bounds):
                    child.entries.append(entry)
                    placed = True
                    break
            if not placed:
                redistributed.append(entry)

        node.entries = redistributed

    def _split_quadtree(self, node: TreeNode) -> None:
        """Split a node into 4 quadrants for 2D space (ignoring Z)."""
        cx, cy, _ = node.bounds.center()
        node.is_leaf = False
        node.is_split = True

        for i in range(4):
            lx = i & 1
            ly = (i >> 1) & 1

            child_bounds = BoundingBox(
                min_x=node.bounds.min_x if lx == 0 else cx,
                min_y=node.bounds.min_y if ly == 0 else cy,
                min_z=node.bounds.min_z,
                max_x=cx if lx == 0 else node.bounds.max_x,
                max_y=cy if ly == 0 else node.bounds.max_y,
                max_z=node.bounds.max_z,
            )

            child = TreeNode(
                id=uuid.uuid4().hex[:12],
                bounds=child_bounds,
                depth=node.depth + 1,
                max_depth=node.max_depth,
                entries=[],
                children=[],
                is_leaf=True,
                is_split=False,
                partition_type=PartitionType.QUADTREE,
                metadata={"max_entries_per_node": node.metadata.get("max_entries_per_node", self._DEFAULT_MAX_ENTRIES_PER_NODE)},
            )
            node.children.append(child)

        redistributed: List[SpatialEntry] = []
        for entry in node.entries:
            placed = False
            for child in node.children:
                # For quadtree, check 2D containment (ignore Z)
                if (
                    child.bounds.min_x <= entry.bounds.min_x
                    and child.bounds.min_y <= entry.bounds.min_y
                    and child.bounds.max_x >= entry.bounds.max_x
                    and child.bounds.max_y >= entry.bounds.max_y
                ):
                    child.entries.append(entry)
                    placed = True
                    break
            if not placed:
                redistributed.append(entry)

        node.entries = redistributed

    def _split_bvh(self, node: TreeNode) -> None:
        """Split a node into two children using a simple BVH median split."""
        if len(node.entries) < 2:
            return

        node.is_leaf = False
        node.is_split = True

        # Sort entries by the longest axis of the node
        w, h, d = node.bounds.size()
        if w >= h and w >= d:
            node.entries.sort(key=lambda e: (e.bounds.min_x + e.bounds.max_x) * 0.5)
        elif h >= d:
            node.entries.sort(key=lambda e: (e.bounds.min_y + e.bounds.max_y) * 0.5)
        else:
            node.entries.sort(key=lambda e: (e.bounds.min_z + e.bounds.max_z) * 0.5)

        mid = len(node.entries) // 2
        left_entries = node.entries[:mid]
        right_entries = node.entries[mid:]

        for entries in (left_entries, right_entries):
            if not entries:
                continue
            child_bounds = BoundingBox(
                min_x=min(e.bounds.min_x for e in entries),
                min_y=min(e.bounds.min_y for e in entries),
                min_z=min(e.bounds.min_z for e in entries),
                max_x=max(e.bounds.max_x for e in entries),
                max_y=max(e.bounds.max_y for e in entries),
                max_z=max(e.bounds.max_z for e in entries),
            )
            child = TreeNode(
                id=uuid.uuid4().hex[:12],
                bounds=child_bounds,
                depth=node.depth + 1,
                max_depth=node.max_depth,
                entries=list(entries),
                children=[],
                is_leaf=True,
                is_split=False,
                partition_type=PartitionType.BVH,
                metadata={"max_entries_per_node": node.metadata.get("max_entries_per_node", self._DEFAULT_MAX_ENTRIES_PER_NODE)},
            )
            node.children.append(child)

        node.entries = []

    def _split_grid(self, node: TreeNode) -> None:
        """Split a node into a uniform grid of sub-cells."""
        w, h, d = node.bounds.size()
        divs = 2
        cell_w = w / divs
        cell_h = h / divs
        cell_d = d / divs

        node.is_leaf = False
        node.is_split = True

        for ix in range(divs):
            for iy in range(divs):
                for iz in range(divs):
                    child_bounds = BoundingBox(
                        min_x=node.bounds.min_x + ix * cell_w,
                        min_y=node.bounds.min_y + iy * cell_h,
                        min_z=node.bounds.min_z + iz * cell_d,
                        max_x=node.bounds.min_x + (ix + 1) * cell_w,
                        max_y=node.bounds.min_y + (iy + 1) * cell_h,
                        max_z=node.bounds.min_z + (iz + 1) * cell_d,
                    )
                    child = TreeNode(
                        id=uuid.uuid4().hex[:12],
                        bounds=child_bounds,
                        depth=node.depth + 1,
                        max_depth=node.max_depth,
                        entries=[],
                        children=[],
                        is_leaf=True,
                        is_split=False,
                        partition_type=PartitionType.GRID,
                        metadata={"max_entries_per_node": node.metadata.get("max_entries_per_node", self._DEFAULT_MAX_ENTRIES_PER_NODE)},
                    )
                    node.children.append(child)

        redistributed: List[SpatialEntry] = []
        for entry in node.entries:
            placed = False
            for child in node.children:
                if child.bounds.contains(entry.bounds):
                    child.entries.append(entry)
                    placed = True
                    break
            if not placed:
                redistributed.append(entry)

        node.entries = redistributed

    def remove(self, entry_id: str) -> bool:
        """Remove a spatial entry from its tree."""
        with self._lock:
            tree_id = self._entry_lookup.pop(entry_id, None)
            if tree_id is None:
                return False
            root = self._trees.get(tree_id)
            if root is None:
                return False
            removed = self._remove_from_node(root, entry_id)
            if removed:
                self._remove_count += 1
            return removed

    def _remove_from_node(self, node: TreeNode, entry_id: str) -> bool:
        """Recursively remove an entry from the tree node."""
        # Check this node's entries
        for i, entry in enumerate(node.entries):
            if entry.id == entry_id:
                node.entries.pop(i)
                return True

        # Check children
        for child in node.children:
            if self._remove_from_node(child, entry_id):
                return True

        return False

    def update(self, entry_id: str, new_bounds: BoundingBox) -> bool:
        """Update the bounding box of an existing entry.

        Since the entry's position in the tree depends on its bounds,
        this removes and re-inserts the entry.
        """
        with self._lock:
            tree_id = self._entry_lookup.get(entry_id)
            if tree_id is None:
                return False
            root = self._trees.get(tree_id)
            if root is None:
                return False

            # Find the existing entry
            old_entry = self._find_entry(root, entry_id)
            if old_entry is None:
                return False

            # Remove and re-insert with new bounds
            self._remove_from_node(root, entry_id)
            old_entry.bounds = new_bounds
            success = self._insert_into_node(root, old_entry)
            if success:
                self._entry_lookup[entry_id] = tree_id
            return success

    def _find_entry(self, node: TreeNode, entry_id: str) -> Optional[SpatialEntry]:
        """Find an entry by ID in the tree."""
        for entry in node.entries:
            if entry.id == entry_id:
                return entry
        for child in node.children:
            result = self._find_entry(child, entry_id)
            if result is not None:
                return result
        return None

    def get_tree(self, tree_id: str) -> Optional[TreeNode]:
        """Get the root node of a tree by its ID."""
        return self._trees.get(tree_id)

    def rebuild(self, tree_id: str) -> bool:
        """Rebuild the tree from scratch, re-inserting all entries."""
        with self._lock:
            root = self._trees.get(tree_id)
            if root is None:
                return False

            # Collect all entries
            all_entries = self._collect_entries(root)
            entry_ids = {e.id for e in all_entries}

            # Clear the tree
            root.entries = []
            root.children = []
            root.is_leaf = True
            root.is_split = False

            # Re-insert all entries
            for entry in all_entries:
                self._entry_lookup.pop(entry.id, None)
                self._insert_into_node(root, entry)
                self._entry_lookup[entry.id] = tree_id

            return True

    def _collect_entries(self, node: TreeNode) -> List[SpatialEntry]:
        """Recursively collect all entries from a tree node."""
        result = list(node.entries)
        for child in node.children:
            result.extend(self._collect_entries(child))
        return result

    # ------------------------------------------------------------------
    # Range Query
    # ------------------------------------------------------------------

    def query_range(
        self,
        tree_id: str,
        query_bounds: BoundingBox,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[QueryResult]:
        """Query all entries whose bounding box intersects the given bounds."""
        with self._lock:
            self._query_count += 1
            root = self._trees.get(tree_id)
            if root is None:
                return []

            results: List[QueryResult] = []
            self._query_range_recursive(root, query_bounds, results, entry_type, tags)

            # Sort by distance to query center
            cx, cy, cz = query_bounds.center()
            results.sort(key=lambda r: r.distance)

            return results

    def _query_range_recursive(
        self,
        node: TreeNode,
        query_bounds: BoundingBox,
        results: List[QueryResult],
        entry_type: Optional[str],
        tags: Optional[List[str]],
    ) -> None:
        """Recursively collect entries within the query bounds."""
        if not node.bounds.intersects(query_bounds):
            return

        cx, cy, cz = query_bounds.center()

        for entry in node.entries:
            if entry_type is not None and entry.entity_type != entry_type:
                continue
            if tags is not None:
                if not any(t in entry.tags for t in tags):
                    continue
            if entry.bounds.intersects(query_bounds):
                dist = entry.bounds.distance_to_point(cx, cy, cz)
                results.append(QueryResult(
                    entry_id=entry.id,
                    entity_id=entry.entity_id,
                    distance=dist,
                    relevance=1.0,
                    metadata=dict(entry.metadata),
                ))

        for child in node.children:
            self._query_range_recursive(child, query_bounds, results, entry_type, tags)

    # ------------------------------------------------------------------
    # K-Nearest-Neighbor Query
    # ------------------------------------------------------------------

    def query_knn(
        self,
        tree_id: str,
        x: float,
        y: float,
        z: float,
        k: int = 10,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[QueryResult]:
        """Query the k nearest neighbors to a point.

        Uses a priority queue approach: each node is visited in order of
        distance from the query point to the node's bounding box.
        """
        with self._lock:
            self._query_count += 1
            root = self._trees.get(tree_id)
            if root is None:
                return []

            # Priority queue: (distance, node)
            candidates: List[Tuple[float, TreeNode]] = []
            dist = root.bounds.distance_to_point(x, y, z)
            candidates.append((dist, root))

            results: List[QueryResult] = []
            k = max(1, min(k, 1000))

            while candidates and len(results) < k:
                # Sort and take the closest node
                candidates.sort(key=lambda item: item[0])
                dist_to_node, node = candidates.pop(0)

                # If results already have k items and the closest node is farther,
                # we can stop early
                if len(results) >= k and dist_to_node > results[-1].distance:
                    break

                if node.is_leaf:
                    for entry in node.entries:
                        if entry_type is not None and entry.entity_type != entry_type:
                            continue
                        if tags is not None:
                            if not any(t in entry.tags for t in tags):
                                continue
                        entry_dist = entry.bounds.distance_to_point(x, y, z)
                        results.append(QueryResult(
                            entry_id=entry.id,
                            entity_id=entry.entity_id,
                            distance=entry_dist,
                            relevance=1.0 / max(0.0001, entry_dist),
                            metadata=dict(entry.metadata),
                        ))
                else:
                    for child in node.children:
                        child_dist = child.bounds.distance_to_point(x, y, z)
                        candidates.append((child_dist, child))

                # Keep only top k results
                results.sort(key=lambda r: r.distance)
                if len(results) > k:
                    results = results[:k]

            return results[:k]

    # ------------------------------------------------------------------
    # Frustum Query
    # ------------------------------------------------------------------

    def query_frustum(
        self,
        tree_id: str,
        camera_pos: Tuple[float, float, float],
        camera_dir: Tuple[float, float, float],
        camera_up: Tuple[float, float, float],
        fov: float = 90.0,
        aspect_ratio: float = 1.7778,
        near_plane: float = 0.1,
        far_plane: float = 1000.0,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[QueryResult]:
        """Query entries visible within a perspective camera frustum.

        Uses a fast axis-aligned frustum bounding box as a conservative
        pre-filter, then checks each candidate against the frustum planes.
        """
        with self._lock:
            self._query_count += 1
            root = self._trees.get(tree_id)
            if root is None:
                return []

            # Compute frustum AABB as a conservative estimate
            frustum_bounds = self._compute_frustum_aabb(
                camera_pos, camera_dir, camera_up, fov, aspect_ratio, near_plane, far_plane
            )

            # First, get range query candidates
            results: List[QueryResult] = []
            self._query_range_recursive(root, frustum_bounds, results, entry_type, tags)

            # Filter by frustum planes
            planes = self._compute_frustum_planes(
                camera_pos, camera_dir, camera_up, fov, aspect_ratio, near_plane, far_plane
            )

            filtered: List[QueryResult] = []
            for result in results:
                entry = self._find_entry(root, result.entry_id)
                if entry is None:
                    continue
                if self._bounds_in_frustum(entry.bounds, planes):
                    filtered.append(result)

            filtered.sort(key=lambda r: r.distance)
            return filtered

    def _compute_frustum_aabb(
        self,
        camera_pos: Tuple[float, float, float],
        camera_dir: Tuple[float, float, float],
        camera_up: Tuple[float, float, float],
        fov: float,
        aspect_ratio: float,
        near_plane: float,
        far_plane: float,
    ) -> BoundingBox:
        """Compute a conservative world-space AABB that encloses the frustum."""
        fov_rad = math.radians(fov * 0.5)
        tan_fov = math.tan(fov_rad)

        far_height = tan_fov * far_plane
        far_width = far_height * aspect_ratio

        near_height = tan_fov * near_plane
        near_width = near_height * aspect_ratio

        # Compute camera basis vectors
        forward = self._normalize_vec3(camera_dir)
        up = self._normalize_vec3(camera_up)
        right = self._cross_vec3(forward, up)
        up = self._cross_vec3(right, forward)

        far_center = self._add_vec3(
            camera_pos, self._scale_vec3(forward, far_plane)
        )
        near_center = self._add_vec3(
            camera_pos, self._scale_vec3(forward, near_plane)
        )

        all_points: List[Tuple[float, float, float]] = []

        # Far plane corners
        for dx in (-1, 1):
            for dy in (-1, 1):
                corner = self._add_vec3(
                    far_center,
                    self._add_vec3(
                        self._scale_vec3(right, dx * far_width),
                        self._scale_vec3(up, dy * far_height),
                    ),
                )
                all_points.append(corner)

        # Near plane corners
        for dx in (-1, 1):
            for dy in (-1, 1):
                corner = self._add_vec3(
                    near_center,
                    self._add_vec3(
                        self._scale_vec3(right, dx * near_width),
                        self._scale_vec3(up, dy * near_height),
                    ),
                )
                all_points.append(corner)

        all_points.append(camera_pos)

        min_x = min(p[0] for p in all_points)
        min_y = min(p[1] for p in all_points)
        min_z = min(p[2] for p in all_points)
        max_x = max(p[0] for p in all_points)
        max_y = max(p[1] for p in all_points)
        max_z = max(p[2] for p in all_points)

        return BoundingBox(
            min_x=min_x, min_y=min_y, min_z=min_z,
            max_x=max_x, max_y=max_y, max_z=max_z,
        )

    def _compute_frustum_planes(
        self,
        camera_pos: Tuple[float, float, float],
        camera_dir: Tuple[float, float, float],
        camera_up: Tuple[float, float, float],
        fov: float,
        aspect_ratio: float,
        near_plane: float,
        far_plane: float,
    ) -> List[Tuple[Tuple[float, float, float], float]]:
        """Compute the six frustum planes (normal, distance)."""
        fov_rad = math.radians(fov * 0.5)
        tan_fov = math.tan(fov_rad)

        far_height = tan_fov * far_plane
        far_width = far_height * aspect_ratio

        near_height = tan_fov * near_plane
        near_width = near_height * aspect_ratio

        forward = self._normalize_vec3(camera_dir)
        up = self._normalize_vec3(camera_up)
        right = self._cross_vec3(forward, up)
        up = self._cross_vec3(right, forward)

        far_center = self._add_vec3(camera_pos, self._scale_vec3(forward, far_plane))
        near_center = self._add_vec3(camera_pos, self._scale_vec3(forward, near_plane))

        planes: List[Tuple[Tuple[float, float, float], float]] = []

        # Near plane
        planes.append((forward, self._dot_vec3(forward, near_center)))
        # Far plane
        planes.append((self._scale_vec3(forward, -1.0), -self._dot_vec3(forward, far_center)))

        # Top plane
        top_normal = self._normalize_vec3(
            self._cross_vec3(
                self._subtract_vec3(
                    self._add_vec3(far_center, self._scale_vec3(up, far_height)),
                    camera_pos,
                ),
                right,
            )
        )
        planes.append((top_normal, self._dot_vec3(top_normal, camera_pos)))

        # Bottom plane
        bottom_normal = self._normalize_vec3(
            self._cross_vec3(
                right,
                self._subtract_vec3(
                    self._add_vec3(far_center, self._scale_vec3(up, -far_height)),
                    camera_pos,
                ),
            )
        )
        planes.append((bottom_normal, self._dot_vec3(bottom_normal, camera_pos)))

        # Left plane
        left_normal = self._normalize_vec3(
            self._cross_vec3(
                self._subtract_vec3(
                    self._add_vec3(far_center, self._scale_vec3(right, -far_width)),
                    camera_pos,
                ),
                up,
            )
        )
        planes.append((left_normal, self._dot_vec3(left_normal, camera_pos)))

        # Right plane
        right_normal = self._normalize_vec3(
            self._cross_vec3(
                up,
                self._subtract_vec3(
                    self._add_vec3(far_center, self._scale_vec3(right, far_width)),
                    camera_pos,
                ),
            )
        )
        planes.append((right_normal, self._dot_vec3(right_normal, camera_pos)))

        return planes

    def _bounds_in_frustum(
        self,
        bounds: BoundingBox,
        planes: List[Tuple[Tuple[float, float, float], float]],
    ) -> bool:
        """Check if a bounding box is at least partially inside the frustum."""
        corners = [
            (bounds.min_x, bounds.min_y, bounds.min_z),
            (bounds.min_x, bounds.min_y, bounds.max_z),
            (bounds.min_x, bounds.max_y, bounds.min_z),
            (bounds.min_x, bounds.max_y, bounds.max_z),
            (bounds.max_x, bounds.min_y, bounds.min_z),
            (bounds.max_x, bounds.min_y, bounds.max_z),
            (bounds.max_x, bounds.max_y, bounds.min_z),
            (bounds.max_x, bounds.max_y, bounds.max_z),
        ]

        for normal, dist in planes:
            all_outside = True
            for cx, cy, cz in corners:
                if self._dot_vec3(normal, (cx, cy, cz)) >= dist:
                    all_outside = False
                    break
            if all_outside:
                return False

        return True

    # ------------------------------------------------------------------
    # Raycast Query
    # ------------------------------------------------------------------

    def query_raycast(
        self,
        tree_id: str,
        origin_x: float,
        origin_y: float,
        origin_z: float,
        direction_x: float,
        direction_y: float,
        direction_z: float,
        max_distance: float = 1000.0,
        entry_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[QueryResult]:
        """Query entries intersected by a ray, sorted by distance.

        Uses a recursive tree traversal that only visits nodes whose
        bounding boxes are intersected by the ray.
        """
        with self._lock:
            self._query_count += 1
            root = self._trees.get(tree_id)
            if root is None:
                return []

            # Normalize direction
            length = math.sqrt(
                direction_x * direction_x + direction_y * direction_y + direction_z * direction_z
            )
            if length < 0.0000001:
                return []
            dx = direction_x / length
            dy = direction_y / length
            dz = direction_z / length

            results: List[QueryResult] = []
            self._raycast_recursive(
                root,
                (origin_x, origin_y, origin_z),
                (dx, dy, dz),
                max_distance,
                results,
                entry_type,
                tags,
            )

            results.sort(key=lambda r: r.distance)
            return results

    def _raycast_recursive(
        self,
        node: TreeNode,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float,
        results: List[QueryResult],
        entry_type: Optional[str],
        tags: Optional[List[str]],
    ) -> None:
        """Recursively traverse the tree for raycast hits."""
        t_hit = self._ray_aabb_intersect(node.bounds, origin, direction, max_distance)
        if t_hit is None:
            return

        for entry in node.entries:
            if entry_type is not None and entry.entity_type != entry_type:
                continue
            if tags is not None:
                if not any(t in entry.tags for t in tags):
                    continue
            t_entry = self._ray_aabb_intersect(entry.bounds, origin, direction, max_distance)
            if t_entry is not None:
                results.append(QueryResult(
                    entry_id=entry.id,
                    entity_id=entry.entity_id,
                    distance=t_entry,
                    relevance=1.0 / max(0.001, t_entry),
                    metadata=dict(entry.metadata),
                ))

        for child in node.children:
            self._raycast_recursive(child, origin, direction, max_distance, results, entry_type, tags)

    def _ray_aabb_intersect(
        self,
        bounds: BoundingBox,
        origin: Tuple[float, float, float],
        direction: Tuple[float, float, float],
        max_distance: float,
    ) -> Optional[float]:
        """Ray vs AABB intersection test using slab method. Returns t_min or None."""
        t_min = 0.0
        t_max = max_distance

        ox, oy, oz = origin
        dx, dy, dz = direction

        # X slab
        if abs(dx) < 0.0000001:
            if ox < bounds.min_x or ox > bounds.max_x:
                return None
        else:
            inv_d = 1.0 / dx
            t1 = (bounds.min_x - ox) * inv_d
            t2 = (bounds.max_x - ox) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

        if t_min > t_max:
            return None

        # Y slab
        if abs(dy) < 0.0000001:
            if oy < bounds.min_y or oy > bounds.max_y:
                return None
        else:
            inv_d = 1.0 / dy
            t1 = (bounds.min_y - oy) * inv_d
            t2 = (bounds.max_y - oy) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

        if t_min > t_max:
            return None

        # Z slab
        if abs(dz) < 0.0000001:
            if oz < bounds.min_z or oz > bounds.max_z:
                return None
        else:
            inv_d = 1.0 / dz
            t1 = (bounds.min_z - oz) * inv_d
            t2 = (bounds.max_z - oz) * inv_d
            if t1 > t2:
                t1, t2 = t2, t1
            t_min = max(t_min, t1)
            t_max = min(t_max, t2)

        if t_min > t_max:
            return None

        return t_min

    # ------------------------------------------------------------------
    # Vector Math Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_vec3(v: Tuple[float, float, float]) -> Tuple[float, float, float]:
        x, y, z = v
        length = math.sqrt(x * x + y * y + z * z)
        if length < 0.0000001:
            return (0.0, 0.0, 0.0)
        return (x / length, y / length, z / length)

    @staticmethod
    def _cross_vec3(
        a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        return (
            a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0],
        )

    @staticmethod
    def _dot_vec3(
        a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> float:
        return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]

    @staticmethod
    def _add_vec3(
        a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        return (a[0] + b[0], a[1] + b[1], a[2] + b[2])

    @staticmethod
    def _subtract_vec3(
        a: Tuple[float, float, float], b: Tuple[float, float, float]
    ) -> Tuple[float, float, float]:
        return (a[0] - b[0], a[1] - b[1], a[2] - b[2])

    @staticmethod
    def _scale_vec3(
        v: Tuple[float, float, float], s: float
    ) -> Tuple[float, float, float]:
        return (v[0] * s, v[1] * s, v[2] * s)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics including tree counts and query metrics."""
        with self._lock:
            total_entries = 0
            total_nodes = 0
            tree_details: List[Dict[str, Any]] = []

            for tree_id, root in self._trees.items():
                entries = self._count_entries(root)
                nodes = self._count_nodes(root)
                total_entries += entries
                total_nodes += nodes
                tree_details.append({
                    "tree_id": tree_id,
                    "name": root.metadata.get("name", ""),
                    "partition_type": root.partition_type.value,
                    "entry_count": entries,
                    "node_count": nodes,
                    "max_depth": root.max_depth,
                    "bounds": root.bounds.to_dict(),
                })

            return {
                "tree_count": len(self._trees),
                "total_entries": total_entries,
                "total_nodes": total_nodes,
                "entry_lookup_size": len(self._entry_lookup),
                "query_count": self._query_count,
                "insert_count": self._insert_count,
                "remove_count": self._remove_count,
                "uptime_seconds": round(time.time() - self._creation_time, 1),
                "trees": tree_details,
            }

    def _count_entries(self, node: TreeNode) -> int:
        count = len(node.entries)
        for child in node.children:
            count += self._count_entries(child)
        return count

    def _count_nodes(self, node: TreeNode) -> int:
        count = 1
        for child in node.children:
            count += self._count_nodes(child)
        return count

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset the entire spatial partition engine state."""
        with self._lock:
            self._trees.clear()
            self._entry_lookup.clear()
            self._grid.clear()
            self._query_count = 0
            self._insert_count = 0
            self._remove_count = 0
            self._creation_time = time.time()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_spatial_partition() -> SpatialPartitionEngine:
    """Get or create the singleton SpatialPartitionEngine instance."""
    return SpatialPartitionEngine.get_instance()