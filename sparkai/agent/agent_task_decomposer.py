"""
SparkLabs Agent - Task Decomposer Engine

Hierarchical task decomposition engine that breaks complex game development
tasks into manageable subtasks with dependency tracking, parallel execution
planning, and progress monitoring. Designed for orchestrating multi-agent
workflows in game creation pipelines.

Architecture:
  TaskDecomposerEngine (Singleton)
    |-- TaskNode (hierarchical task tree node with dependencies)
    |-- DecompositionStrategy (pluggable strategy for task breakdown)
    |-- ExecutionPlan (ordered task execution plan with parallelism)
    |-- ProgressTracker (real-time progress monitoring across the tree)

Decomposition Strategies:
  - TOP_DOWN: break from root goal into sub-tasks
  - BOTTOM_UP: compose from atomic tasks upward
  - HYBRID: combine top-down and bottom-up approaches
  - ADAPTIVE: dynamically adjust based on task complexity

Task Types:
  - DESIGN, IMPLEMENTATION, TESTING, DEPLOYMENT, REVIEW
  - ASSET_CREATION, CODE_GENERATION, LEVEL_DESIGN, NARRATIVE

Usage:
    td = get_task_decomposer()
    td.initialize()

    plan = td.decompose(
        goal="Create a 2D platformer game with 3 levels",
        strategy=DecompositionStrategy.HYBRID,
        max_depth=4,
    )

    progress = td.get_progress(plan.plan_id)
    td.shutdown()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class DecompositionStrategy(Enum):
    """Strategies for decomposing tasks."""
    TOP_DOWN = "top_down"        # Break from root goal into sub-tasks
    BOTTOM_UP = "bottom_up"      # Compose from atomic tasks upward
    HYBRID = "hybrid"            # Combine top-down and bottom-up
    ADAPTIVE = "adaptive"        # Dynamically adjust based on complexity


class TaskType(Enum):
    """Types of game development tasks."""
    DESIGN = "design"
    IMPLEMENTATION = "implementation"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    REVIEW = "review"
    ASSET_CREATION = "asset_creation"
    CODE_GENERATION = "code_generation"
    LEVEL_DESIGN = "level_design"
    NARRATIVE = "narrative"
    AUDIO = "audio"
    UI_UX = "ui_ux"
    OPTIMIZATION = "optimization"


class TaskStatus(Enum):
    """Execution status of a task."""
    PENDING = "pending"
    BLOCKED = "blocked"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class TaskPriority(Enum):
    """Priority level for task execution."""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4
    OPTIONAL = 5


class DependencyType(Enum):
    """Types of dependencies between tasks."""
    HARD = "hard"              # Must complete before dependent starts
    SOFT = "soft"              # Should complete, but not blocking
    RESOURCE = "resource"      # Shares a resource constraint
    TEMPORAL = "temporal"      # Time-based ordering


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class TaskDependency:
    """A dependency relationship between two tasks."""
    dependency_id: str
    source_task_id: str
    target_task_id: str
    dependency_type: DependencyType = DependencyType.HARD
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "dependency_id": self.dependency_id,
            "source_task_id": self.source_task_id,
            "target_task_id": self.target_task_id,
            "dependency_type": self.dependency_type.value,
            "description": self.description,
        }


@dataclass
class TaskNode:
    """A node in the hierarchical task tree."""
    task_id: str
    name: str
    description: str
    task_type: TaskType = TaskType.DESIGN
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    dependencies: List[TaskDependency] = field(default_factory=list)
    assigned_agent: Optional[str] = None
    estimated_duration: float = 0.0
    actual_duration: float = 0.0
    progress: float = 0.0
    depth: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    retry_count: int = 0
    max_retries: int = 3

    @property
    def is_leaf(self) -> bool:
        return len(self.child_ids) == 0

    @property
    def is_root(self) -> bool:
        return self.parent_id is None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "task_type": self.task_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "dependencies": [d.to_dict() for d in self.dependencies],
            "assigned_agent": self.assigned_agent,
            "estimated_duration": self.estimated_duration,
            "actual_duration": self.actual_duration,
            "progress": self.progress,
            "depth": self.depth,
            "is_leaf": self.is_leaf,
            "is_root": self.is_root,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "retry_count": self.retry_count,
        }


@dataclass
class ExecutionPlan:
    """Complete task execution plan with ordering and parallelism."""
    plan_id: str
    goal: str
    strategy: DecompositionStrategy
    root_task: Optional[TaskNode] = None
    all_tasks: Dict[str, TaskNode] = field(default_factory=dict)
    execution_order: List[List[str]] = field(default_factory=list)
    parallel_groups: List[List[str]] = field(default_factory=list)
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    overall_progress: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "strategy": self.strategy.value,
            "root_task": self.root_task.to_dict() if self.root_task else None,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "overall_progress": self.overall_progress,
            "execution_order": self.execution_order,
            "parallel_groups": self.parallel_groups,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


# =============================================================================
# Predefined Decomposition Templates
# =============================================================================

# Templates for common game development goals
_DECOMPOSITION_TEMPLATES: Dict[str, List[Dict[str, Any]]] = {
    "platformer": [
        {"name": "Core Mechanics Design", "type": TaskType.DESIGN, "children": [
            {"name": "Player Movement System", "type": TaskType.IMPLEMENTATION},
            {"name": "Jump Physics Tuning", "type": TaskType.IMPLEMENTATION},
            {"name": "Collision Detection", "type": TaskType.IMPLEMENTATION},
        ]},
        {"name": "Level Design", "type": TaskType.LEVEL_DESIGN, "children": [
            {"name": "Level 1 Layout", "type": TaskType.LEVEL_DESIGN},
            {"name": "Level 2 Layout", "type": TaskType.LEVEL_DESIGN},
            {"name": "Level 3 Layout", "type": TaskType.LEVEL_DESIGN},
        ]},
        {"name": "Asset Creation", "type": TaskType.ASSET_CREATION, "children": [
            {"name": "Player Character Sprite", "type": TaskType.ASSET_CREATION},
            {"name": "Environment Tileset", "type": TaskType.ASSET_CREATION},
            {"name": "UI Elements", "type": TaskType.UI_UX},
        ]},
        {"name": "Testing & Polish", "type": TaskType.TESTING, "children": [
            {"name": "Playtesting", "type": TaskType.TESTING},
            {"name": "Bug Fixing", "type": TaskType.IMPLEMENTATION},
            {"name": "Performance Optimization", "type": TaskType.OPTIMIZATION},
        ]},
    ],
    "rpg": [
        {"name": "Combat System Design", "type": TaskType.DESIGN, "children": [
            {"name": "Turn-Based Mechanics", "type": TaskType.IMPLEMENTATION},
            {"name": "Damage Calculation", "type": TaskType.IMPLEMENTATION},
            {"name": "Enemy AI", "type": TaskType.IMPLEMENTATION},
        ]},
        {"name": "World Building", "type": TaskType.LEVEL_DESIGN, "children": [
            {"name": "Overworld Map", "type": TaskType.LEVEL_DESIGN},
            {"name": "Dungeon Generation", "type": TaskType.LEVEL_DESIGN},
            {"name": "Town Design", "type": TaskType.LEVEL_DESIGN},
        ]},
        {"name": "Narrative Development", "type": TaskType.NARRATIVE, "children": [
            {"name": "Main Storyline", "type": TaskType.NARRATIVE},
            {"name": "Side Quests", "type": TaskType.NARRATIVE},
            {"name": "Character Dialogue", "type": TaskType.NARRATIVE},
        ]},
        {"name": "Inventory & Items", "type": TaskType.IMPLEMENTATION, "children": [
            {"name": "Item System", "type": TaskType.IMPLEMENTATION},
            {"name": "Equipment System", "type": TaskType.IMPLEMENTATION},
            {"name": "Shop System", "type": TaskType.IMPLEMENTATION},
        ]},
    ],
    "puzzle": [
        {"name": "Puzzle Mechanics", "type": TaskType.DESIGN, "children": [
            {"name": "Core Puzzle Logic", "type": TaskType.IMPLEMENTATION},
            {"name": "Hint System", "type": TaskType.IMPLEMENTATION},
            {"name": "Difficulty Scaling", "type": TaskType.DESIGN},
        ]},
        {"name": "Level Progression", "type": TaskType.LEVEL_DESIGN, "children": [
            {"name": "Tutorial Levels", "type": TaskType.LEVEL_DESIGN},
            {"name": "Intermediate Levels", "type": TaskType.LEVEL_DESIGN},
            {"name": "Challenge Levels", "type": TaskType.LEVEL_DESIGN},
        ]},
        {"name": "Visual Feedback", "type": TaskType.UI_UX, "children": [
            {"name": "Puzzle Animations", "type": TaskType.IMPLEMENTATION},
            {"name": "Success Effects", "type": TaskType.IMPLEMENTATION},
            {"name": "Progress Tracking UI", "type": TaskType.UI_UX},
        ]},
    ],
}


# =============================================================================
# Task Decomposer Engine
# =============================================================================


class TaskDecomposerEngine:
    """
    Hierarchical task decomposition engine for game development workflows.
    Breaks complex goals into executable subtask trees with dependency management.
    """

    _instance: Optional["TaskDecomposerEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if TaskDecomposerEngine._instance is not None:
            raise RuntimeError("Use TaskDecomposerEngine.get_instance()")
        self._initialized: bool = False
        self._plans: Dict[str, ExecutionPlan] = {}
        self._custom_strategies: Dict[str, Callable] = {}
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "TaskDecomposerEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the task decomposer."""
        with self._lock:
            if self._initialized:
                return
            self._initialized = True

    def decompose(
        self,
        goal: str,
        strategy: DecompositionStrategy = DecompositionStrategy.HYBRID,
        max_depth: int = 4,
        context: Optional[Dict[str, Any]] = None,
        template: Optional[str] = None,
    ) -> ExecutionPlan:
        """
        Decompose a goal into a hierarchical task tree.

        Args:
            goal: The high-level goal to decompose.
            strategy: Decomposition strategy to use.
            max_depth: Maximum depth of the task tree.
            context: Additional context for task decomposition.
            template: Optional template name for predefined decomposition.

        Returns:
            ExecutionPlan with the complete task tree and execution order.
        """
        with self._lock:
            plan_id = uuid.uuid4().hex[:12]

            # Create root task
            root_task = TaskNode(
                task_id=uuid.uuid4().hex[:12],
                name="Root: " + goal[:80],
                description=goal,
                task_type=TaskType.DESIGN,
                depth=0,
            )

            plan = ExecutionPlan(
                plan_id=plan_id,
                goal=goal,
                strategy=strategy,
                root_task=root_task,
                all_tasks={root_task.task_id: root_task},
                metadata=context or {},
            )

            # Apply template if provided
            if template and template in _DECOMPOSITION_TEMPLATES:
                self._apply_template(plan, root_task, template, max_depth)
            else:
                # Apply strategy-based decomposition
                if strategy == DecompositionStrategy.TOP_DOWN:
                    self._decompose_top_down(plan, root_task, max_depth, context)
                elif strategy == DecompositionStrategy.BOTTOM_UP:
                    self._decompose_bottom_up(plan, root_task, max_depth, context)
                elif strategy == DecompositionStrategy.HYBRID:
                    self._decompose_hybrid(plan, root_task, max_depth, context)
                elif strategy == DecompositionStrategy.ADAPTIVE:
                    self._decompose_adaptive(plan, root_task, max_depth, context)

            # Compute execution order
            plan.execution_order = self._compute_execution_order(plan)
            plan.parallel_groups = self._compute_parallel_groups(plan)
            plan.total_tasks = len(plan.all_tasks)

            self._plans[plan_id] = plan
            return plan

    def _apply_template(
        self,
        plan: ExecutionPlan,
        parent: TaskNode,
        template_name: str,
        max_depth: int,
        current_depth: int = 0,
    ) -> None:
        """Apply a predefined decomposition template."""
        template = _DECOMPOSITION_TEMPLATES.get(template_name, [])
        for item in template:
            if current_depth >= max_depth:
                break
            child = TaskNode(
                task_id=uuid.uuid4().hex[:12],
                name=item["name"],
                description=item.get("description", item["name"]),
                task_type=item.get("type", TaskType.DESIGN),
                parent_id=parent.task_id,
                depth=current_depth + 1,
            )
            parent.child_ids.append(child.task_id)
            plan.all_tasks[child.task_id] = child

            if "children" in item and current_depth + 1 < max_depth:
                self._apply_template(plan, child, template_name, max_depth, current_depth + 1)

    def _decompose_top_down(
        self,
        plan: ExecutionPlan,
        parent: TaskNode,
        max_depth: int,
        context: Optional[Dict[str, Any]],
        current_depth: int = 0,
    ) -> None:
        """Top-down decomposition: break goal into sub-tasks recursively."""
        if current_depth >= max_depth:
            return

        sub_tasks = self._generate_sub_tasks(parent.description, parent.task_type, context)
        for sub_task_def in sub_tasks:
            child = TaskNode(
                task_id=uuid.uuid4().hex[:12],
                name=sub_task_def["name"],
                description=sub_task_def.get("description", ""),
                task_type=sub_task_def.get("type", TaskType.IMPLEMENTATION),
                parent_id=parent.task_id,
                depth=current_depth + 1,
                priority=sub_task_def.get("priority", TaskPriority.MEDIUM),
                estimated_duration=sub_task_def.get("estimated_duration", 0.0),
            )
            parent.child_ids.append(child.task_id)
            plan.all_tasks[child.task_id] = child

            # Recursively decompose
            if sub_task_def.get("decomposable", True):
                self._decompose_top_down(plan, child, max_depth, context, current_depth + 1)

    def _decompose_bottom_up(
        self,
        plan: ExecutionPlan,
        root: TaskNode,
        max_depth: int,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Bottom-up decomposition: compose from atomic tasks."""
        atomic_tasks = self._generate_atomic_tasks(root.description, context)
        groups: Dict[str, List[TaskNode]] = {}

        for atomic_def in atomic_tasks:
            group = atomic_def.get("group", "default")
            if group not in groups:
                groups[group] = []

            task = TaskNode(
                task_id=uuid.uuid4().hex[:12],
                name=atomic_def["name"],
                description=atomic_def.get("description", ""),
                task_type=atomic_def.get("type", TaskType.IMPLEMENTATION),
                depth=1,
                priority=atomic_def.get("priority", TaskPriority.MEDIUM),
            )
            groups[group].append(task)
            root.child_ids.append(task.task_id)
            plan.all_tasks[task.task_id] = task

    def _decompose_hybrid(
        self,
        plan: ExecutionPlan,
        root: TaskNode,
        max_depth: int,
        context: Optional[Dict[str, Any]],
    ) -> None:
        """Hybrid decomposition: combine top-down and bottom-up."""
        self._decompose_top_down(plan, root, max_depth // 2, context)
        self._decompose_bottom_up(plan, root, max_depth, context)

    def _decompose_adaptive(
        self,
        plan: ExecutionPlan,
        parent: TaskNode,
        max_depth: int,
        context: Optional[Dict[str, Any]],
        current_depth: int = 0,
    ) -> None:
        """Adaptive decomposition: dynamically adjust based on complexity."""
        if current_depth >= max_depth:
            return

        complexity = self._estimate_complexity(parent.description)
        if complexity < 0.3 and current_depth > 0:
            return

        if complexity > 0.7:
            self._decompose_top_down(plan, parent, max_depth, context, current_depth)
        else:
            self._decompose_bottom_up(plan, parent, max_depth, context)

    def _generate_sub_tasks(
        self,
        goal: str,
        parent_type: TaskType,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate sub-tasks for a given goal."""
        sub_tasks: List[Dict[str, Any]] = []

        if "game" in goal.lower() or "level" in goal.lower():
            sub_tasks.extend([
                {"name": "Define Game Mechanics", "type": TaskType.DESIGN, "decomposable": True},
                {"name": "Create Level Layout", "type": TaskType.LEVEL_DESIGN, "decomposable": True},
                {"name": "Implement Core Systems", "type": TaskType.IMPLEMENTATION, "decomposable": True},
                {"name": "Design Visual Assets", "type": TaskType.ASSET_CREATION, "decomposable": True},
            ])
        elif "asset" in goal.lower() or "sprite" in goal.lower():
            sub_tasks.extend([
                {"name": "Create Asset Draft", "type": TaskType.ASSET_CREATION},
                {"name": "Apply Style Guidelines", "type": TaskType.DESIGN},
                {"name": "Export in Required Formats", "type": TaskType.IMPLEMENTATION},
            ])
        elif "test" in goal.lower() or "quality" in goal.lower():
            sub_tasks.extend([
                {"name": "Write Test Cases", "type": TaskType.TESTING},
                {"name": "Execute Test Suite", "type": TaskType.TESTING},
                {"name": "Report Issues", "type": TaskType.REVIEW},
            ])
        else:
            sub_tasks.extend([
                {"name": f"Analyze: {goal[:50]}", "type": TaskType.DESIGN},
                {"name": f"Implement: {goal[:50]}", "type": TaskType.IMPLEMENTATION},
                {"name": f"Verify: {goal[:50]}", "type": TaskType.TESTING},
            ])

        return sub_tasks

    def _generate_atomic_tasks(
        self,
        goal: str,
        context: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate atomic (non-decomposable) tasks."""
        return [
            {"name": f"Setup project for: {goal[:40]}", "type": TaskType.IMPLEMENTATION, "group": "setup"},
            {"name": f"Create main file for: {goal[:40]}", "type": TaskType.CODE_GENERATION, "group": "code"},
            {"name": f"Write basic tests for: {goal[:40]}", "type": TaskType.TESTING, "group": "test"},
            {"name": f"Document: {goal[:40]}", "type": TaskType.DESIGN, "group": "docs"},
        ]

    def _estimate_complexity(self, goal: str) -> float:
        """Estimate task complexity based on goal description."""
        complexity_indicators = [
            "multiplayer", "physics", "ai", "procedural", "dynamic",
            "real-time", "simulation", "network", "3d", "open world",
        ]
        score = 0.3
        for indicator in complexity_indicators:
            if indicator in goal.lower():
                score += 0.15
        return min(score, 1.0)

    def _compute_execution_order(self, plan: ExecutionPlan) -> List[List[str]]:
        """Compute the execution order for tasks in the plan."""
        order: List[List[str]] = []
        levels: Dict[int, List[str]] = {}

        for task in plan.all_tasks.values():
            depth = task.depth
            if depth not in levels:
                levels[depth] = []
            levels[depth].append(task.task_id)

        for depth in sorted(levels.keys()):
            order.append(levels[depth])

        return order

    def _compute_parallel_groups(self, plan: ExecutionPlan) -> List[List[str]]:
        """Identify tasks that can be executed in parallel."""
        groups: List[List[str]] = []
        for level in plan.execution_order:
            if len(level) > 1:
                groups.append(level)
        return groups

    def update_task_status(
        self,
        plan_id: str,
        task_id: str,
        status: TaskStatus,
        progress: Optional[float] = None,
    ) -> Optional[TaskNode]:
        """Update the status of a task in the plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if not plan:
                return None
            task = plan.all_tasks.get(task_id)
            if not task:
                return None

            old_status = task.status
            task.status = status

            if progress is not None:
                task.progress = progress

            if status == TaskStatus.IN_PROGRESS and task.started_at is None:
                task.started_at = time.time()
            elif status == TaskStatus.COMPLETED:
                task.completed_at = time.time()
                if task.started_at:
                    task.actual_duration = task.completed_at - task.started_at
                task.progress = 1.0
                plan.completed_tasks += 1
            elif status == TaskStatus.FAILED:
                plan.failed_tasks += 1
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING

            # Recalculate overall progress
            plan.overall_progress = self._calculate_progress(plan)
            plan.updated_at = time.time()

            return task

    def _calculate_progress(self, plan: ExecutionPlan) -> float:
        """Calculate overall plan progress."""
        if plan.total_tasks == 0:
            return 0.0
        total_progress = sum(t.progress for t in plan.all_tasks.values())
        return total_progress / plan.total_tasks

    def get_plan(self, plan_id: str) -> Optional[ExecutionPlan]:
        """Retrieve an execution plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(self) -> List[ExecutionPlan]:
        """List all execution plans."""
        return list(self._plans.values())

    def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """Execute all ready tasks in a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found", "success": False}
        executed = []
        for task in plan.all_tasks.values():
            if task.status == TaskStatus.READY:
                task.status = TaskStatus.IN_PROGRESS
                task.started_at = time.time()
                executed.append(task.task_id)
        plan.overall_progress = self._calculate_progress(plan)
        return {
            "success": True,
            "plan_id": plan_id,
            "tasks_started": len(executed),
            "task_ids": executed,
            "progress": plan.overall_progress,
        }

    def get_progress(self, plan_id: str) -> Dict[str, Any]:
        """Get detailed progress report for a plan."""
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        status_counts = {s.value: 0 for s in TaskStatus}
        for task in plan.all_tasks.values():
            status_counts[task.status.value] += 1

        return {
            "plan_id": plan_id,
            "goal": plan.goal,
            "overall_progress": plan.overall_progress,
            "total_tasks": plan.total_tasks,
            "completed_tasks": plan.completed_tasks,
            "failed_tasks": plan.failed_tasks,
            "status_breakdown": status_counts,
            "next_tasks": self._get_next_ready_tasks(plan),
        }

    def _get_next_ready_tasks(self, plan: ExecutionPlan) -> List[str]:
        """Get tasks that are ready for execution."""
        ready: List[str] = []
        for task in plan.all_tasks.values():
            if task.status == TaskStatus.READY:
                # Check dependencies
                all_deps_met = True
                for dep in task.dependencies:
                    dep_task = plan.all_tasks.get(dep.source_task_id)
                    if dep_task and dep_task.status != TaskStatus.COMPLETED:
                        if dep.dependency_type == DependencyType.HARD:
                            all_deps_met = False
                            break
                if all_deps_met:
                    ready.append(task.task_id)
        return ready

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the task decomposer."""
        return {
            "initialized": self._initialized,
            "total_plans": len(self._plans),
            "active_plans": len([
                p for p in self._plans.values()
                if p.overall_progress < 1.0
            ]),
            "completed_plans": len([
                p for p in self._plans.values()
                if p.overall_progress >= 1.0
            ]),
            "templates": list(_DECOMPOSITION_TEMPLATES.keys()),
        }

    def shutdown(self) -> None:
        """Shutdown the task decomposer."""
        with self._lock:
            self._plans.clear()
            self._custom_strategies.clear()
            self._initialized = False


# =============================================================================
# Singleton Accessor
# =============================================================================

def get_task_decomposer() -> TaskDecomposerEngine:
    """Get the singleton TaskDecomposerEngine instance."""
    return TaskDecomposerEngine.get_instance()