"""
SparkLabs Agent - Goal Decomposer

Two-phase goal decomposition engine with verification. Breaks
complex game development objectives into structured checklists,
evaluates item completion against verifiable criteria, and tracks
blocking dependency chains for AI-driven project planning.

Architecture:
  GoalDecomposer
    |-- Phase One: Structural Decomposition (goal → checklist items)
    |-- Phase Two: Verification (evidence-driven status evaluation)
    |-- Dependency Graph Analyzer (blocking chain computation)
    |-- Merge Engine (combine parent-child decompositions)

Goal Categories span the full game development lifecycle from
core mechanics through deployment, enabling comprehensive
coverage of all project dimensions.
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ChecklistStatus(Enum):
    COMPLETED = "completed"
    IMPOSSIBLE = "impossible"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"


class GoalCategory(Enum):
    MECHANICS = "mechanics"
    ASSETS = "assets"
    UI = "ui"
    AUDIO = "audio"
    OPTIMIZATION = "optimization"
    TESTING = "testing"
    DEPLOYMENT = "deployment"


class GoalLevel(Enum):
    EPIC = "epic"
    FEATURE = "feature"
    STORY = "story"
    TASK = "task"
    SUBTASK = "subtask"


@dataclass
class GoalNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    title: str = ""
    level: GoalLevel = GoalLevel.TASK
    parent_id: str = ""
    children: List[str] = field(default_factory=list)
    checklist_item: Optional[ChecklistItem] = None
    weight: float = 1.0
    estimated_hours: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "level": self.level.value,
            "parent_id": self.parent_id,
            "children": self.children,
            "weight": self.weight,
            "estimated_hours": self.estimated_hours,
        }


@dataclass
class GoalTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    root_goal: str = ""
    nodes: Dict[str, GoalNode] = field(default_factory=dict)
    max_depth: int = 0
    total_nodes: int = 0

    def add_node(self, node: GoalNode) -> None:
        self.nodes[node.id] = node
        self.total_nodes = len(self.nodes)
        self.max_depth = max(self.max_depth, self._compute_depth(node.id))

    def get_children(self, node_id: str) -> List[GoalNode]:
        node = self.nodes.get(node_id)
        if not node:
            return []
        return [self.nodes[c] for c in node.children if c in self.nodes]

    def _compute_depth(self, node_id: str, depth: int = 0) -> int:
        node = self.nodes.get(node_id)
        if not node:
            return depth
        if not node.parent_id:
            return depth
        return self._compute_depth(node.parent_id, depth + 1)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "root_goal": self.root_goal,
            "max_depth": self.max_depth,
            "total_nodes": self.total_nodes,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
        }


@dataclass
class ChecklistItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    status: ChecklistStatus = ChecklistStatus.PENDING
    category: GoalCategory = GoalCategory.MECHANICS
    dependencies: List[str] = field(default_factory=list)
    verification_criteria: str = ""
    assigned_agent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "status": self.status.value,
            "category": self.category.value,
            "dependencies": self.dependencies,
            "verification_criteria": self.verification_criteria,
            "assigned_agent": self.assigned_agent,
        }


@dataclass
class GoalDecomposition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    goal_text: str = ""
    items: List[ChecklistItem] = field(default_factory=list)
    total_items: int = 0
    completed_items: int = 0
    blocked_items: int = 0
    estimated_complexity: int = 1
    parent_goal_id: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "goal_text": self.goal_text,
            "total_items": self.total_items,
            "completed_items": self.completed_items,
            "blocked_items": self.blocked_items,
            "estimated_complexity": self.estimated_complexity,
            "parent_goal_id": self.parent_goal_id,
            "items": [it.to_dict() for it in self.items],
        }

    def _recompute_counts(self) -> None:
        self.total_items = len(self.items)
        self.completed_items = sum(
            1 for it in self.items if it.status == ChecklistStatus.COMPLETED
        )
        self.blocked_items = sum(
            1 for it in self.items if it.status == ChecklistStatus.BLOCKED
        )


class GoalDecomposer:
    """Two-phase goal decomposition with evidence-driven verification."""

    _instance: Optional["GoalDecomposer"] = None
    _lock = threading.Lock()

    MAX_DECOMPOSITIONS = 150
    MAX_ITEMS_PER_DECOMPOSITION = 300

    def __init__(self):
        self._decompositions: Dict[str, GoalDecomposition] = {}
        self._item_index: Dict[str, str] = {}
        self._total_decomposed: int = 0

    @classmethod
    def get_instance(cls) -> "GoalDecomposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def decompose(self, goal_str: str) -> GoalDecomposition:
        decomp = GoalDecomposition(goal_text=goal_str)

        category_keywords = {
            GoalCategory.MECHANICS: ["movement", "combat", "physics", "collision", "control", "input"],
            GoalCategory.ASSETS: ["sprite", "texture", "model", "mesh", "material", "animation"],
            GoalCategory.UI: ["menu", "hud", "button", "panel", "dialog", "overlay"],
            GoalCategory.AUDIO: ["sound", "music", "sfx", "voice", "ambient", "effect"],
            GoalCategory.OPTIMIZATION: ["performance", "fps", "memory", "batching", "lod", "culling"],
            GoalCategory.TESTING: ["test", "qa", "debug", "verify", "validate", "assert"],
            GoalCategory.DEPLOYMENT: ["build", "publish", "release", "bundle", "package", "deploy"],
        }

        goal_lower = goal_str.lower()
        primary_category = GoalCategory.MECHANICS
        for cat, kws in category_keywords.items():
            if any(kw in goal_lower for kw in kws):
                primary_category = cat
                break

        complexity = min(10, max(1, len(goal_str.split()) // 3))
        num_items = max(3, min(20, complexity * 2))

        for i in range(num_items):
            item = ChecklistItem(
                description=f"[Phase One] Subtask {i + 1} for: {goal_str[:60]}",
                category=primary_category,
                assigned_agent="",
            )
            decomp.items.append(item)
            self._item_index[item.id] = decomp.id

        decomp.estimated_complexity = complexity
        decomp._recompute_counts()
        self._decompositions[decomp.id] = decomp
        self._total_decomposed += 1

        if len(self._decompositions) > self.MAX_DECOMPOSITIONS:
            oldest = min(
                self._decompositions.values(),
                key=lambda d: d.created_at,
            )
            for it in oldest.items:
                self._item_index.pop(it.id, None)
            del self._decompositions[oldest.id]

        return decomp

    def evaluate_item(
        self, item_id: str, evidence: str
    ) -> ChecklistStatus:
        if item_id not in self._item_index:
            return ChecklistStatus.PENDING

        decomp_id = self._item_index[item_id]
        decomp = self._decompositions.get(decomp_id)
        if decomp is None:
            return ChecklistStatus.PENDING

        item = next((it for it in decomp.items if it.id == item_id), None)
        if item is None:
            return ChecklistStatus.PENDING

        evidence_lower = evidence.lower()
        positive_markers = ["done", "complete", "finished", "pass", "success", "works", "verified"]
        negative_markers = ["fail", "error", "broken", "cannot", "impossible", "blocked"]
        progress_markers = ["started", "working", "wip", "in progress", "ongoing"]

        if any(m in evidence_lower for m in negative_markers):
            if "impossible" in evidence_lower or "cannot" in evidence_lower:
                item.status = ChecklistStatus.IMPOSSIBLE
            else:
                item.status = ChecklistStatus.BLOCKED
                self._propagate_block(item, decomp)
        elif any(m in evidence_lower for m in positive_markers):
            item.status = ChecklistStatus.COMPLETED
            self._unblock_dependents(item, decomp)
        elif any(m in evidence_lower for m in progress_markers):
            item.status = ChecklistStatus.IN_PROGRESS
        else:
            item.status = ChecklistStatus.PENDING

        decomp._recompute_counts()
        return item.status

    def _propagate_block(
        self, blocked_item: ChecklistItem, decomp: GoalDecomposition
    ) -> None:
        for item in decomp.items:
            if blocked_item.id in item.dependencies:
                if item.status not in (
                    ChecklistStatus.COMPLETED,
                    ChecklistStatus.IMPOSSIBLE,
                ):
                    item.status = ChecklistStatus.BLOCKED
                    self._propagate_block(item, decomp)

    def _unblock_dependents(
        self, completed_item: ChecklistItem, decomp: GoalDecomposition
    ) -> None:
        for item in decomp.items:
            if completed_item.id in item.dependencies:
                if item.status == ChecklistStatus.BLOCKED:
                    all_deps_met = all(
                        dep_id == completed_item.id
                        or any(
                            d.id == dep_id and d.status == ChecklistStatus.COMPLETED
                            for d in decomp.items
                        )
                        for dep_id in item.dependencies
                    )
                    if all_deps_met:
                        item.status = ChecklistStatus.PENDING

    def get_progress(self, decomposition_id: str) -> dict:
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return {"error": "Decomposition not found"}

        status_counts = {
            s.value: sum(1 for it in decomp.items if it.status == s)
            for s in ChecklistStatus
        }
        category_counts: Dict[str, int] = defaultdict(int)
        for it in decomp.items:
            category_counts[it.category.value] += 1

        return {
            "decomposition_id": decomposition_id,
            "goal_text": decomp.goal_text[:100],
            "total_items": decomp.total_items,
            "completed_items": decomp.completed_items,
            "blocked_items": decomp.blocked_items,
            "progress_pct": round(
                decomp.completed_items / max(1, decomp.total_items) * 100, 1
            ),
            "status_breakdown": status_counts,
            "category_breakdown": dict(category_counts),
            "estimated_complexity": decomp.estimated_complexity,
        }

    def get_blocking_chain(self, decomposition_id: str) -> list:
        decomp = self._decompositions.get(decomposition_id)
        if decomp is None:
            return []

        incoming: Dict[str, List[str]] = defaultdict(list)
        for item in decomp.items:
            for dep_id in item.dependencies:
                incoming[dep_id].append(item.id)

        blocking_chain: List[Dict[str, Any]] = []
        visited: set = set()

        def dfs(item_id: str, depth: int) -> None:
            if item_id in visited or depth > 20:
                return
            visited.add(item_id)
            item = next((it for it in decomp.items if it.id == item_id), None)
            if item is None:
                return
            blocking_chain.append({
                "item_id": item_id,
                "description": item.description,
                "status": item.status.value,
                "depth": depth,
                "blocks": len(incoming.get(item_id, [])),
            })
            for child_id in incoming.get(item_id, []):
                child = next((it for it in decomp.items if it.id == child_id), None)
                if child and child.status == ChecklistStatus.BLOCKED:
                    dfs(child_id, depth + 1)

        for item in decomp.items:
            if item.status == ChecklistStatus.BLOCKED:
                is_root_blocker = not any(
                    dep_id in incoming
                    for dep_id in item.dependencies
                )
                if is_root_blocker:
                    dfs(item.id, 0)

        return blocking_chain

    def merge_decomposition(self, parent_id: str, child_id: str) -> bool:
        parent = self._decompositions.get(parent_id)
        child = self._decompositions.get(child_id)
        if parent is None or child is None:
            return False
        if len(parent.items) + len(child.items) > self.MAX_ITEMS_PER_DECOMPOSITION:
            return False

        for child_item in child.items:
            child_item.id = uuid.uuid4().hex
            self._item_index[child_item.id] = parent_id
            parent.items.append(child_item)

        for item in parent.items:
            if item.assigned_agent:
                item.dependencies.append(child.id)

        parent._recompute_counts()
        for it in child.items:
            self._item_index.pop(it.id, None)
        del self._decompositions[child_id]
        return True

    def get_stats(self) -> dict:
        total_items = sum(d.total_items for d in self._decompositions.values())
        total_completed = sum(d.completed_items for d in self._decompositions.values())
        total_blocked = sum(d.blocked_items for d in self._decompositions.values())
        category_dist: Dict[str, int] = defaultdict(int)
        for d in self._decompositions.values():
            for it in d.items:
                category_dist[it.category.value] += 1

        return {
            "total_decompositions": len(self._decompositions),
            "total_decomposed_ever": self._total_decomposed,
            "total_items": total_items,
            "total_completed": total_completed,
            "total_blocked": total_blocked,
            "overall_progress_pct": round(
                total_completed / max(1, total_items) * 100, 1
            ),
            "category_distribution": dict(category_dist),
            "max_decompositions": self.MAX_DECOMPOSITIONS,
            "max_items_per_decomposition": self.MAX_ITEMS_PER_DECOMPOSITION,
        }


def get_goal_decomposer() -> GoalDecomposer:
    return GoalDecomposer.get_instance()