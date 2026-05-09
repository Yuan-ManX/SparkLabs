"""
SparkLabs Agent - Goal Decomposer

Hierarchical goal decomposition engine that breaks complex game
development objectives into structured, executable task trees.
Provides multi-level decomposition with dependency chains, effort
estimation, and milestone tracking for AI-driven game creation.

Architecture:
  GoalDecomposer
    |-- GoalNode (tree node with sub-goals and dependencies)
    |-- DecompositionStrategy (breadth-first, depth-first, hybrid)
    |-- DependencyResolver (topological ordering of tasks)
    |-- EffortEstimator (compute resource per task node)
    |-- MilestoneTracker (progress across goal tree)

Decomposition Depth:
  - EPIC: project-level objective (Complete RPG with 5 dungeons)
  - FEATURE: feature group (Combat system with abilities)
  - TASK: concrete unit of work (Implement sword attack)
  - STEP: indivisible action (Create attack animation clip)
"""

from __future__ import annotations

import copy
import heapq
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class GoalLevel(Enum):
    EPIC = (0, "Multi-session project goal")
    FEATURE = (1, "Feature group")
    TASK = (2, "Concrete unit of work")
    STEP = (3, "Indivisible atomic action")


class GoalStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DecompositionStrategy(Enum):
    BREADTH_FIRST = "breadth_first"
    DEPTH_FIRST = "depth_first"
    HYBRID = "hybrid"
    PRIORITY_DRIVEN = "priority_driven"


@dataclass
class Dependency:
    source_id: str
    target_id: str
    dependency_type: str = "requires"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source_id,
            "target": self.target_id,
            "type": self.dependency_type,
        }


@dataclass
class GoalNode:
    node_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    title: str = ""
    description: str = ""
    level: GoalLevel = GoalLevel.TASK
    status: GoalStatus = GoalStatus.PENDING
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    estimated_effort_ms: float = 60000.0
    priority: int = 5
    assigned_agent: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "title": self.title,
            "level": self.level.name,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "dependencies": self.dependencies,
            "priority": self.priority,
            "tags": self.tags,
        }


@dataclass
class GoalTree:
    tree_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    root_title: str = ""
    root_description: str = ""
    nodes: Dict[str, GoalNode] = field(default_factory=dict)
    dependencies: List[Dependency] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def total_nodes(self) -> int:
        return len(self.nodes)

    @property
    def completed_nodes(self) -> int:
        return sum(1 for n in self.nodes.values() if n.status == GoalStatus.COMPLETED)

    @property
    def progress(self) -> float:
        if self.total_nodes == 0:
            return 0.0
        return self.completed_nodes / self.total_nodes

    def get_execution_order(self) -> List[str]:
        in_degree: Dict[str, int] = {nid: 0 for nid in self.nodes}
        adj: Dict[str, List[str]] = {nid: [] for nid in self.nodes}
        for dep in self.dependencies:
            if dep.source_id in adj and dep.target_id in in_degree:
                adj[dep.source_id].append(dep.target_id)
                in_degree[dep.target_id] += 1
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order: List[str] = []
        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for neighbor in adj.get(node_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    def get_ready_nodes(self) -> List[GoalNode]:
        ready: List[GoalNode] = []
        for node in self.nodes.values():
            if node.status != GoalStatus.PENDING:
                continue
            blocked = False
            for dep_id in node.dependencies:
                dep_node = self.nodes.get(dep_id)
                if dep_node and dep_node.status != GoalStatus.COMPLETED:
                    blocked = True
                    break
            if not blocked:
                ready.append(node)
        ready.sort(key=lambda n: -n.priority)
        return ready

    def get_node_by_path(self, path: List[str]) -> Optional[GoalNode]:
        if not path:
            return None
        for node in self.nodes.values():
            if node.title.lower() == path[0].lower() and not node.parent_id:
                current = node
                for part in path[1:]:
                    found = False
                    for child_id in current.children:
                        child = self.nodes.get(child_id)
                        if child and child.title.lower() == part.lower():
                            current = child
                            found = True
                            break
                    if not found:
                        return None
                return current
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "root_title": self.root_title,
            "total_nodes": self.total_nodes,
            "completed_nodes": self.completed_nodes,
            "progress": round(self.progress, 3),
            "ready_nodes": len(self.get_ready_nodes()),
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            **self.to_dict(),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "execution_order": self.get_execution_order(),
        }


class GoalDecomposer:
    """Hierarchical goal decomposition for game development planning."""

    _instance: Optional["GoalDecomposer"] = None
    _lock = threading.Lock()

    MAX_TREES = 200
    MAX_NODES_PER_TREE = 500

    def __init__(self):
        self._goal_trees: Dict[str, GoalTree] = {}
        self._active_tree_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "GoalDecomposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_goal_tree(
        self,
        root_title: str,
        root_description: str = "",
    ) -> GoalTree:
        tree = GoalTree(root_title=root_title, root_description=root_description)
        root = GoalNode(
            title=root_title,
            description=root_description,
            level=GoalLevel.EPIC,
        )
        tree.nodes[root.node_id] = root
        self._goal_trees[tree.tree_id] = tree
        self._active_tree_id = tree.tree_id
        return tree

    def add_goal_node(
        self,
        tree_id: str,
        title: str,
        description: str = "",
        parent_id: Optional[str] = None,
        level: GoalLevel = GoalLevel.TASK,
        priority: int = 5,
        depends_on: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[GoalNode]:
        tree = self._goal_trees.get(tree_id)
        if not tree or len(tree.nodes) >= self.MAX_NODES_PER_TREE:
            return None

        node = GoalNode(
            title=title,
            description=description,
            level=level,
            parent_id=parent_id,
            priority=priority,
            tags=tags or [],
        )

        if depends_on:
            node.dependencies = depends_on
            for dep_id in depends_on:
                if dep_id in tree.nodes:
                    tree.dependencies.append(
                        Dependency(source_id=dep_id, target_id=node.node_id)
                    )

        if parent_id and parent_id in tree.nodes:
            tree.nodes[parent_id].children.append(node.node_id)

        tree.nodes[node.node_id] = node
        return node

    def update_node_status(
        self,
        tree_id: str,
        node_id: str,
        status: GoalStatus,
    ) -> Optional[GoalNode]:
        tree = self._goal_trees.get(tree_id)
        if not tree:
            return None
        node = tree.nodes.get(node_id)
        if node:
            node.status = status
            if status == GoalStatus.COMPLETED:
                parent_id = node.parent_id
                while parent_id and parent_id in tree.nodes:
                    parent = tree.nodes[parent_id]
                    if all(
                        tree.nodes.get(cid, GoalNode()).status == GoalStatus.COMPLETED
                        for cid in parent.children
                    ):
                        parent.status = GoalStatus.COMPLETED
                    parent_id = parent.parent_id
                else:
                    pass
            if status == GoalStatus.BLOCKED:
                for child_id in node.children:
                    child = tree.nodes.get(child_id)
                    if child and child.status != GoalStatus.COMPLETED:
                        child.status = GoalStatus.BLOCKED
        return node

    def decompose_epic(
        self,
        tree_id: str,
        epic_node_id: str,
        feature_titles: List[str],
    ) -> List[GoalNode]:
        nodes: List[GoalNode] = []
        for title in feature_titles:
            node = self.add_goal_node(
                tree_id=tree_id,
                title=title,
                level=GoalLevel.FEATURE,
                parent_id=epic_node_id,
            )
            if node:
                nodes.append(node)
        return nodes

    def decompose_feature(
        self,
        tree_id: str,
        feature_node_id: str,
        task_titles: List[Tuple[str, int]],
    ) -> List[GoalNode]:
        nodes: List[GoalNode] = []
        for title, priority in task_titles:
            node = self.add_goal_node(
                tree_id=tree_id,
                title=title,
                level=GoalLevel.TASK,
                parent_id=feature_node_id,
                priority=priority,
            )
            if node:
                nodes.append(node)
        return nodes

    def set_dependency(
        self,
        tree_id: str,
        source_id: str,
        target_id: str,
    ) -> bool:
        tree = self._goal_trees.get(tree_id)
        if not tree or source_id not in tree.nodes or target_id not in tree.nodes:
            return False
        tree.nodes[target_id].dependencies.append(source_id)
        tree.dependencies.append(Dependency(source_id=source_id, target_id=target_id))
        return True

    def get_tree(self, tree_id: str) -> Optional[GoalTree]:
        return self._goal_trees.get(tree_id)

    def list_trees(self) -> List[GoalTree]:
        return list(self._goal_trees.values())

    def get_next_tasks(
        self,
        tree_id: str,
        limit: int = 10,
    ) -> List[GoalNode]:
        tree = self._goal_trees.get(tree_id)
        if not tree:
            return []
        ready = tree.get_ready_nodes()
        ready.sort(key=lambda n: -n.priority)
        return ready[:limit]

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(t.total_nodes for t in self._goal_trees.values())
        completed = sum(t.completed_nodes for t in self._goal_trees.values())
        return {
            "goal_trees": len(self._goal_trees),
            "active_tree_id": self._active_tree_id,
            "total_nodes": total_nodes,
            "completed_nodes": completed,
            "overall_progress": round(
                completed / max(1, total_nodes), 3
            ),
        }

    def delete_tree(self, tree_id: str) -> bool:
        if tree_id in self._goal_trees:
            del self._goal_trees[tree_id]
            if self._active_tree_id == tree_id:
                self._active_tree_id = None
            return True
        return False


def get_goal_decomposer() -> GoalDecomposer:
    return GoalDecomposer.get_instance()