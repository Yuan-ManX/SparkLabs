"""
SparkLabs Agent - Goal Management System

A hierarchical goal management system that enables agents to decompose
complex objectives into manageable sub-goals, track progress, and select
the most valuable goals based on utility calculations. The system supports
dynamic goal prioritization, dependency tracking, and progress monitoring.

Architecture:
  GoalManagementSystem (Singleton)
    |-- GoalNode (individual goal with priority and dependencies)
    |-- GoalTree (hierarchical decomposition of goals)
    |-- GoalSelectionStrategy (utility-based goal selection)
    |-- GoalMonitor (real-time progress tracking)
"""

from __future__ import annotations

import heapq
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class GoalStatus(Enum):
    """State of a goal in the lifecycle."""
    DORMANT = "dormant"
    PENDING = "pending"
    ACTIVATED = "activated"
    IN_PROGRESS = "in_progress"
    SUSPENDED = "suspended"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"


class GoalPriority(Enum):
    """Priority tier for goal ordering."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    OPTIONAL = 4


class GoalCategory(Enum):
    """Domain classification of a goal."""
    STRATEGIC = "strategic"
    TACTICAL = "tactical"
    OPERATIONAL = "operational"
    REACTIVE = "reactive"
    EXPLORATORY = "exploratory"
    MAINTENANCE = "maintenance"


class DecompositionStrategy(Enum):
    """How a goal is decomposed into sub-goals."""
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    ITERATIVE = "iterative"


class SelectionCriterion(Enum):
    """Criteria used for goal selection."""
    UTILITY = "utility"
    URGENCY = "urgency"
    FEASIBILITY = "feasibility"
    DEPENDENCY = "dependency"
    BALANCED = "balanced"


@dataclass
class GoalNode:
    """A single goal entity in the goal hierarchy."""
    goal_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: GoalCategory = GoalCategory.TACTICAL
    priority: GoalPriority = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.DORMANT
    parent_id: Optional[str] = None
    sub_goals: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    preconditions: Dict[str, Any] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    failure_criteria: List[str] = field(default_factory=list)
    expected_utility: float = 0.5
    estimated_cost: float = 1.0
    estimated_duration: float = 0.0
    progress: float = 0.0
    attempts: int = 0
    max_attempts: int = 3
    created_at: float = field(default_factory=_time_module.time)
    activated_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal_id": self.goal_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "priority": self.priority.value,
            "priority_value": self.priority.value,
            "status": self.status.value,
            "parent_id": self.parent_id,
            "sub_goals": self.sub_goals,
            "dependencies": self.dependencies,
            "preconditions": self.preconditions,
            "success_criteria": self.success_criteria,
            "failure_criteria": self.failure_criteria,
            "expected_utility": self.expected_utility,
            "estimated_cost": self.estimated_cost,
            "estimated_duration": self.estimated_duration,
            "progress": self.progress,
            "attempts": self.attempts,
            "max_attempts": self.max_attempts,
            "created_at": self.created_at,
            "activated_at": self.activated_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
        }

    def compute_utility(self, urgency_weight: float = 0.3,
                        feasibility_weight: float = 0.3,
                        value_weight: float = 0.4) -> float:
        """Compute a composite utility score for this goal."""
        urgency = 1.0 if self.priority == GoalPriority.CRITICAL else (
            0.8 if self.priority == GoalPriority.HIGH else (
                0.5 if self.priority == GoalPriority.MEDIUM else (
                    0.3 if self.priority == GoalPriority.LOW else 0.1
                )
            )
        )
        feasibility = 1.0 - min(self.attempts / max(self.max_attempts, 1), 0.9)
        value = self.expected_utility
        return urgency * urgency_weight + feasibility * feasibility_weight + value * value_weight


class GoalTree:
    """
    Hierarchical goal decomposition structure.
    Manages parent-child relationships and dependency resolution
    for complex goal networks.
    """

    def __init__(self) -> None:
        self._goals: Dict[str, GoalNode] = {}
        self._root_goals: List[str] = []
        self._dependency_graph: Dict[str, Set[str]] = {}
        self._reverse_deps: Dict[str, Set[str]] = {}
        self._lock = threading.RLock()

    def add_goal(self, goal: GoalNode) -> GoalNode:
        """Add a goal to the tree."""
        with self._lock:
            self._goals[goal.goal_id] = goal
            if goal.parent_id is None:
                if goal.goal_id not in self._root_goals:
                    self._root_goals.append(goal.goal_id)
            else:
                parent = self._goals.get(goal.parent_id)
                if parent and goal.goal_id not in parent.sub_goals:
                    parent.sub_goals.append(goal.goal_id)
            for dep in goal.dependencies:
                if dep not in self._dependency_graph:
                    self._dependency_graph[dep] = set()
                self._dependency_graph[dep].add(goal.goal_id)
                if goal.goal_id not in self._reverse_deps:
                    self._reverse_deps[goal.goal_id] = set()
                self._reverse_deps[goal.goal_id].add(dep)
            return goal

    def create_goal(
        self,
        name: str,
        description: str = "",
        category: GoalCategory = GoalCategory.TACTICAL,
        priority: GoalPriority = GoalPriority.MEDIUM,
        parent_id: Optional[str] = None,
        dependencies: Optional[List[str]] = None,
        expected_utility: float = 0.5,
        estimated_cost: float = 1.0,
    ) -> GoalNode:
        """Create and add a new goal."""
        goal = GoalNode(
            name=name,
            description=description,
            category=category,
            priority=priority,
            parent_id=parent_id,
            dependencies=dependencies or [],
            expected_utility=expected_utility,
            estimated_cost=estimated_cost,
        )
        return self.add_goal(goal)

    def decompose(self, goal_id: str, sub_goal_specs: List[Dict[str, Any]],
                  strategy: DecompositionStrategy = DecompositionStrategy.SEQUENTIAL) -> List[GoalNode]:
        """Decompose a goal into sub-goals."""
        with self._lock:
            parent = self._goals.get(goal_id)
            if not parent:
                return []
            created: List[GoalNode] = []
            for i, spec in enumerate(sub_goal_specs):
                sub_deps: List[str] = []
                if strategy == DecompositionStrategy.SEQUENTIAL and i > 0:
                    sub_deps = [created[-1].goal_id]
                elif strategy == DecompositionStrategy.CONDITIONAL:
                    sub_deps = spec.get("depends_on", [])
                sub = self.create_goal(
                    name=spec.get("name", f"Sub-goal {i+1}"),
                    description=spec.get("description", ""),
                    category=spec.get("category", parent.category),
                    priority=spec.get("priority", parent.priority),
                    parent_id=goal_id,
                    dependencies=sub_deps,
                    expected_utility=spec.get("expected_utility", parent.expected_utility * 0.8),
                    estimated_cost=spec.get("estimated_cost", parent.estimated_cost * 0.5),
                )
                created.append(sub)
            return created

    def get_goal(self, goal_id: str) -> Optional[GoalNode]:
        with self._lock:
            return self._goals.get(goal_id)

    def get_sub_goals(self, goal_id: str) -> List[GoalNode]:
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return []
            return [self._goals[sid] for sid in goal.sub_goals if sid in self._goals]

    def get_root_goals(self) -> List[GoalNode]:
        with self._lock:
            return [self._goals[rid] for rid in self._root_goals if rid in self._goals]

    def get_dependents(self, goal_id: str) -> List[GoalNode]:
        """Get goals that depend on the given goal."""
        with self._lock:
            dep_ids = self._dependency_graph.get(goal_id, set())
            return [self._goals[did] for did in dep_ids if did in self._goals]

    def get_dependencies(self, goal_id: str) -> List[GoalNode]:
        """Get goals that the given goal depends on."""
        with self._lock:
            dep_ids = self._reverse_deps.get(goal_id, set())
            return [self._goals[did] for did in dep_ids if did in self._goals]

    def update_status(self, goal_id: str, status: GoalStatus) -> bool:
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            goal.status = status
            if status == GoalStatus.ACTIVATED and goal.activated_at is None:
                goal.activated_at = _time_module.time()
            if status == GoalStatus.COMPLETED:
                goal.completed_at = _time_module.time()
                goal.progress = 1.0
            elif status == GoalStatus.FAILED:
                goal.attempts += 1
            return True

    def update_progress(self, goal_id: str, progress: float) -> bool:
        with self._lock:
            goal = self._goals.get(goal_id)
            if not goal:
                return False
            goal.progress = max(0.0, min(1.0, progress))
            if goal.progress >= 1.0:
                goal.status = GoalStatus.COMPLETED
                goal.completed_at = _time_module.time()
            return True

    def get_active_goals(self) -> List[GoalNode]:
        with self._lock:
            active_statuses = {GoalStatus.ACTIVATED, GoalStatus.IN_PROGRESS}
            return [g for g in self._goals.values() if g.status in active_statuses]

    def get_ready_goals(self) -> List[GoalNode]:
        """Get goals whose dependencies are all satisfied."""
        with self._lock:
            ready: List[GoalNode] = []
            for goal in self._goals.values():
                if goal.status not in (GoalStatus.DORMANT, GoalStatus.PENDING):
                    continue
                deps_satisfied = all(
                    self._goals.get(dep) and self._goals[dep].status == GoalStatus.COMPLETED
                    for dep in goal.dependencies
                )
                if deps_satisfied:
                    ready.append(goal)
            return ready

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_goals": len(self._goals),
                "root_goals": len(self._root_goals),
                "goals": [g.to_dict() for g in self._goals.values()],
            }


class GoalSelectionStrategy:
    """
    Selects the most valuable goal to pursue based on utility
    calculations, dependency resolution, and resource constraints.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def select(
        self,
        tree: GoalTree,
        criterion: SelectionCriterion = SelectionCriterion.UTILITY,
        max_goals: int = 1,
    ) -> List[GoalNode]:
        """Select the best goals to pursue."""
        with self._lock:
            candidates = tree.get_ready_goals()
            if not candidates:
                return []

            if criterion == SelectionCriterion.UTILITY:
                candidates.sort(key=lambda g: g.compute_utility(), reverse=True)
            elif criterion == SelectionCriterion.URGENCY:
                candidates.sort(key=lambda g: g.priority.value)
            elif criterion == SelectionCriterion.FEASIBILITY:
                candidates.sort(key=lambda g: g.attempts)
            elif criterion == SelectionCriterion.DEPENDENCY:
                candidates.sort(key=lambda g: len(tree.get_dependents(g.goal_id)), reverse=True)
            elif criterion == SelectionCriterion.BALANCED:
                candidates.sort(
                    key=lambda g: (
                        g.compute_utility() * 0.4
                        + (1.0 - g.priority.value / 5.0) * 0.3
                        + (1.0 - g.attempts / max(g.max_attempts, 1)) * 0.3
                    ),
                    reverse=True,
                )

            return candidates[:max_goals]

    def select_by_utility_threshold(
        self,
        tree: GoalTree,
        min_utility: float = 0.3,
        max_goals: int = 5,
    ) -> List[GoalNode]:
        """Select goals that meet a minimum utility threshold."""
        candidates = tree.get_ready_goals()
        filtered = [g for g in candidates if g.compute_utility() >= min_utility]
        filtered.sort(key=lambda g: g.compute_utility(), reverse=True)
        return filtered[:max_goals]


class GoalMonitor:
    """
    Tracks goal progress and detects anomalies.
    Monitors execution of active goals, detects stalls, and
    triggers alerts when goals deviate from expected trajectories.
    """

    def __init__(self) -> None:
        self._progress_history: Dict[str, List[Tuple[float, float]]] = {}
        self._alerts: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

    def track_progress(self, goal_id: str, progress: float) -> None:
        """Record a progress update for a goal."""
        with self._lock:
            if goal_id not in self._progress_history:
                self._progress_history[goal_id] = []
            self._progress_history[goal_id].append((_time_module.time(), progress))

    def check_stalled(self, goal_id: str, stall_threshold: float = 300.0) -> bool:
        """Check if a goal has stalled (no progress in the threshold window)."""
        with self._lock:
            history = self._progress_history.get(goal_id, [])
            if len(history) < 2:
                return False
            recent = history[-2:]
            if len(recent) < 2:
                return False
            t1, p1 = recent[0]
            t2, p2 = recent[1]
            if p2 <= p1 and (t2 - t1) >= stall_threshold:
                self._alerts.append({
                    "goal_id": goal_id,
                    "type": "stalled",
                    "last_progress": p2,
                    "timestamp": _time_module.time(),
                })
                return True
            return False

    def get_progress_rate(self, goal_id: str) -> float:
        """Compute the rate of progress change."""
        with self._lock:
            history = self._progress_history.get(goal_id, [])
            if len(history) < 2:
                return 0.0
            first = history[0]
            last = history[-1]
            dt = last[0] - first[0]
            if dt <= 0:
                return 0.0
            return (last[1] - first[1]) / dt

    def get_alerts(self, clear: bool = False) -> List[Dict[str, Any]]:
        with self._lock:
            alerts = list(self._alerts)
            if clear:
                self._alerts.clear()
            return alerts

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tracked_goals": len(self._progress_history),
                "alert_count": len(self._alerts),
                "recent_alerts": self._alerts[-10:],
            }


class GoalManagementSystem:
    """
    Hierarchical goal management system for AI agents.

    Enables decomposition of complex objectives into manageable sub-goals,
    utility-based goal selection, and real-time progress monitoring.
    """

    _instance = None
    _lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._tree = GoalTree()
        self._selector = GoalSelectionStrategy()
        self._monitor = GoalMonitor()
        self._on_goal_completed: Optional[Callable] = None
        self._on_goal_failed: Optional[Callable] = None

    @classmethod
    def get_instance(cls) -> "GoalManagementSystem":
        return cls()

    @property
    def tree(self) -> GoalTree:
        return self._tree

    @property
    def selector(self) -> GoalSelectionStrategy:
        return self._selector

    @property
    def monitor(self) -> GoalMonitor:
        return self._monitor

    def create_goal(
        self,
        name: str,
        description: str = "",
        category: str = "tactical",
        priority: str = "medium",
        parent_id: Optional[str] = None,
    ) -> GoalNode:
        """Create a top-level goal."""
        with self._lock:
            return self._tree.create_goal(
                name=name,
                description=description,
                category=GoalCategory(category),
                priority=GoalPriority(priority),
                parent_id=parent_id,
            )

    def decompose_goal(
        self,
        goal_id: str,
        sub_goal_specs: List[Dict[str, Any]],
        strategy: str = "sequential",
    ) -> List[GoalNode]:
        """Decompose a goal into sub-goals."""
        with self._lock:
            return self._tree.decompose(
                goal_id=goal_id,
                sub_goal_specs=sub_goal_specs,
                strategy=DecompositionStrategy(strategy),
            )

    def activate_goal(self, goal_id: str) -> bool:
        self._monitor.track_progress(goal_id, 0.0)
        return self._tree.update_status(goal_id, GoalStatus.ACTIVATED)

    def start_goal(self, goal_id: str) -> bool:
        self._monitor.track_progress(goal_id, 0.0)
        return self._tree.update_status(goal_id, GoalStatus.IN_PROGRESS)

    def complete_goal(self, goal_id: str) -> bool:
        self._monitor.track_progress(goal_id, 1.0)
        result = self._tree.update_status(goal_id, GoalStatus.COMPLETED)
        if result and self._on_goal_completed:
            goal = self._tree.get_goal(goal_id)
            if goal:
                self._on_goal_completed(goal)
        return result

    def fail_goal(self, goal_id: str) -> bool:
        result = self._tree.update_status(goal_id, GoalStatus.FAILED)
        if result and self._on_goal_failed:
            goal = self._tree.get_goal(goal_id)
            if goal:
                self._on_goal_failed(goal)
        return result

    def update_progress(self, goal_id: str, progress: float) -> bool:
        self._monitor.track_progress(goal_id, progress)
        return self._tree.update_progress(goal_id, progress)

    def select_next_goals(self, criterion: str = "utility", max_goals: int = 1) -> List[GoalNode]:
        """Select the best goals to pursue next."""
        return self._selector.select(
            tree=self._tree,
            criterion=SelectionCriterion(criterion),
            max_goals=max_goals,
        )

    def get_active_goals(self) -> List[GoalNode]:
        return self._tree.get_active_goals()

    def get_ready_goals(self) -> List[GoalNode]:
        return self._tree.get_ready_goals()

    def check_stalled(self) -> List[str]:
        """Check all active goals for stalls."""
        stalled: List[str] = []
        for goal in self._tree.get_active_goals():
            if self._monitor.check_stalled(goal.goal_id):
                stalled.append(goal.goal_id)
        return stalled

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "tree": self._tree.to_dict(),
                "monitor": self._monitor.to_dict(),
                "active_count": len(self._tree.get_active_goals()),
                "ready_count": len(self._tree.get_ready_goals()),
            }


_global_goal_management: Optional[GoalManagementSystem] = None


def get_goal_management() -> GoalManagementSystem:
    global _global_goal_management
    if _global_goal_management is None:
        _global_goal_management = GoalManagementSystem()
    return _global_goal_management