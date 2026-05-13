"""
SparkLabs Agent - Goal Planner Engine

Goal planning and milestone decomposition engine for AI-native
game development. Breaks high-level project goals into ordered
milestones with dependency tracking, progress monitoring, and
critical path analysis.

Architecture:
  GoalPlannerEngine
    |-- Goal Plan Management (create, query, update plans)
    |-- Milestone Graph (DAG of milestones with dependencies)
    |-- Critical Path Analysis (bottleneck identification)
    |-- Progress Estimation (time-to-completion forecasts)
    |-- Blockage Detection (dependency chain analysis)

Goal Categories:
  - GAME_DESIGN: core mechanics and design documents
  - LEVEL_BUILD: environment and level construction
  - SYSTEM_ARCH: engine and infrastructure decisions
  - CONTENT_CREATE: assets, audio, narrative content
  - TESTING: QA, playtesting, and validation
  - OPTIMIZATION: performance and resource tuning
  - RELEASE: publishing, packaging, deployment
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set


class GoalCategory(Enum):
    GAME_DESIGN = auto()
    LEVEL_BUILD = auto()
    SYSTEM_ARCH = auto()
    CONTENT_CREATE = auto()
    TESTING = auto()
    OPTIMIZATION = auto()
    RELEASE = auto()


class GoalPriority(Enum):
    CRITICAL = auto()
    HIGH = auto()
    MEDIUM = auto()
    LOW = auto()
    OPTIONAL = auto()
    STRETCH = auto()


class MilestoneStatus(Enum):
    PENDING = auto()
    IN_PROGRESS = auto()
    BLOCKED = auto()
    COMPLETED = auto()
    SKIPPED = auto()
    FAILED = auto()


@dataclass
class GoalMilestone:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str = ""
    target_date: float = 0.0
    status: MilestoneStatus = MilestoneStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    assigned_agent: str = ""
    completion_criteria: str = ""
    progress_pct: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "target_date": self.target_date,
            "status": self.status.name,
            "dependencies": self.dependencies,
            "assigned_agent": self.assigned_agent,
            "completion_criteria": self.completion_criteria,
            "progress_pct": self.progress_pct,
            "notes": self.notes,
        }


@dataclass
class GoalPlan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: GoalCategory = GoalCategory.GAME_DESIGN
    priority: GoalPriority = GoalPriority.MEDIUM
    description: str = ""
    milestones: List[GoalMilestone] = field(default_factory=list)
    total_estimated_hours: float = 0.0
    deadline: float = 0.0
    created_at: float = 0.0
    updated_at: float = 0.0
    parent_goal_id: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        now = time.time()
        if self.created_at == 0.0:
            self.created_at = now
        if self.updated_at == 0.0:
            self.updated_at = now

    @property
    def total_milestones(self) -> int:
        return len(self.milestones)

    @property
    def completed_milestones(self) -> int:
        return sum(1 for m in self.milestones if m.status == MilestoneStatus.COMPLETED)

    @property
    def overall_progress(self) -> float:
        if not self.milestones:
            return 0.0
        return self.completed_milestones / len(self.milestones)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.name,
            "priority": self.priority.name,
            "description": self.description,
            "milestones": [m.to_dict() for m in self.milestones],
            "total_estimated_hours": self.total_estimated_hours,
            "deadline": self.deadline,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_goal_id": self.parent_goal_id,
            "tags": self.tags,
            "overall_progress": round(self.overall_progress * 100, 1),
        }


class GoalPlannerEngine:
    _instance: Optional["GoalPlannerEngine"] = None

    def __init__(self):
        self._plans: Dict[str, GoalPlan] = {}
        self._plan_count: int = 0
        self._milestone_count: int = 0

    @classmethod
    def get_instance(cls) -> "GoalPlannerEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_plan(
        self,
        name: str,
        category: GoalCategory,
        priority: GoalPriority,
        description: str,
    ) -> GoalPlan:
        plan = GoalPlan(
            name=name,
            category=category,
            priority=priority,
            description=description,
        )
        self._plans[plan.id] = plan
        self._plan_count += 1
        return plan

    def add_milestone(
        self,
        plan_id: str,
        description: str,
        target_date: float = 0.0,
        dependencies: Optional[List[str]] = None,
    ) -> str:
        plan = self._plans.get(plan_id)
        if plan is None:
            return ""

        milestone = GoalMilestone(
            description=description,
            target_date=target_date,
            dependencies=dependencies or [],
        )
        plan.milestones.append(milestone)
        plan.updated_at = time.time()
        self._milestone_count += 1
        return milestone.id

    def update_milestone_status(
        self,
        plan_id: str,
        milestone_id: str,
        status: MilestoneStatus,
        progress_pct: float = 0.0,
    ) -> bool:
        plan = self._plans.get(plan_id)
        if plan is None:
            return False

        for milestone in plan.milestones:
            if milestone.id == milestone_id:
                milestone.status = status
                milestone.progress_pct = max(0.0, min(100.0, progress_pct))
                plan.updated_at = time.time()
                return True
        return False

    def get_critical_path(self, plan_id: str) -> List[GoalMilestone]:
        plan = self._plans.get(plan_id)
        if plan is None or not plan.milestones:
            return []

        milestone_map = {m.id: m for m in plan.milestones}
        in_degree: Dict[str, int] = {m.id: 0 for m in plan.milestones}
        forward: Dict[str, List[str]] = {m.id: [] for m in plan.milestones}

        for m in plan.milestones:
            for dep_id in m.dependencies:
                if dep_id in milestone_map:
                    in_degree[m.id] += 1
                    forward.setdefault(dep_id, []).append(m.id)

        longest_path: Dict[str, float] = {}
        predecessor: Dict[str, Optional[str]] = {}

        queue = [mid for mid, deg in in_degree.items() if deg == 0]
        if not queue:
            queue = [plan.milestones[0].id]

        while queue:
            current = queue.pop(0)
            if current not in longest_path:
                longest_path[current] = 1.0

            for neighbor in forward.get(current, []):
                new_len = longest_path[current] + 1.0
                if neighbor not in longest_path or new_len > longest_path[neighbor]:
                    longest_path[neighbor] = new_len
                    predecessor[neighbor] = current
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if not longest_path:
            return []

        end_milestone_id = max(longest_path, key=lambda k: longest_path[k])
        critical_ids: List[str] = []
        current_id: Optional[str] = end_milestone_id
        while current_id is not None:
            critical_ids.insert(0, current_id)
            current_id = predecessor.get(current_id)

        return [milestone_map[mid] for mid in critical_ids if mid in milestone_map]

    def estimate_completion(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if plan is None:
            return {"error": "plan not found"}

        remaining = sum(
            1 for m in plan.milestones
            if m.status not in (MilestoneStatus.COMPLETED, MilestoneStatus.SKIPPED)
        )
        completed_count = plan.completed_milestones
        total = len(plan.milestones)

        if completed_count == 0:
            estimated_hours = plan.total_estimated_hours or (total * 2.0)
        else:
            if plan.total_estimated_hours > 0:
                avg_per_milestone = plan.total_estimated_hours / total
            else:
                avg_per_milestone = 2.0
            estimated_hours = remaining * avg_per_milestone

        overdue = False
        if plan.deadline > 0 and estimated_hours > 0:
            now = time.time()
            target_completion = now + (estimated_hours * 3600)
            overdue = target_completion > plan.deadline

        return {
            "plan_id": plan_id,
            "total_milestones": total,
            "completed": completed_count,
            "remaining": remaining,
            "overall_progress_pct": round(plan.overall_progress * 100, 1),
            "estimated_remaining_hours": round(estimated_hours, 1),
            "overdue_risk": overdue,
            "deadline": plan.deadline,
        }

    def find_blocked_milestones(self, plan_id: str) -> List[GoalMilestone]:
        plan = self._plans.get(plan_id)
        if plan is None:
            return []

        blocked: List[GoalMilestone] = []
        completed_ids: Set[str] = {
            m.id for m in plan.milestones
            if m.status == MilestoneStatus.COMPLETED
        }

        for milestone in plan.milestones:
            if milestone.status == MilestoneStatus.COMPLETED:
                continue
            if milestone.dependencies:
                unmet = [d for d in milestone.dependencies if d not in completed_ids]
                if unmet:
                    milestone.status = MilestoneStatus.BLOCKED
                    blocked.append(milestone)

        return blocked

    def get_plan_progress(self, plan_id: str) -> Dict[str, Any]:
        plan = self._plans.get(plan_id)
        if plan is None:
            return {"error": "plan not found"}

        status_counts: Dict[str, int] = {}
        for m in plan.milestones:
            key = m.status.name
            status_counts[key] = status_counts.get(key, 0) + 1

        return {
            "plan_id": plan_id,
            "plan_name": plan.name,
            "category": plan.category.name,
            "priority": plan.priority.name,
            "status_counts": status_counts,
            "overall_progress_pct": round(plan.overall_progress * 100, 1),
            "total_milestones": plan.total_milestones,
            "completed_milestones": plan.completed_milestones,
        }

    def get_stats(self) -> Dict[str, Any]:
        total_milestones = sum(p.total_milestones for p in self._plans.values())
        completed_milestones = sum(
            p.completed_milestones for p in self._plans.values()
        )
        blocked_milestones = sum(
            1 for p in self._plans.values()
            for m in p.milestones
            if m.status == MilestoneStatus.BLOCKED
        )

        category_counts: Dict[str, int] = {}
        for plan in self._plans.values():
            key = plan.category.name
            category_counts[key] = category_counts.get(key, 0) + 1

        return {
            "total_plans": self._plan_count,
            "active_plans": len(self._plans),
            "total_milestones": total_milestones,
            "completed_milestones": completed_milestones,
            "blocked_milestones": blocked_milestones,
            "overall_progress_pct": round(
                (completed_milestones / max(total_milestones, 1)) * 100, 1
            ),
            "plans_by_category": category_counts,
            "plans_created": self._plan_count,
            "milestones_created": self._milestone_count,
        }


def get_goal_planner() -> GoalPlannerEngine:
    return GoalPlannerEngine.get_instance()