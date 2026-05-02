"""
SparkLabs Agent - Strategic Planner

Hierarchical task decomposition engine for game generation pipelines.
Breaks high-level game creation goals into ordered sub-tasks with
dependencies, estimated effort, and execution strategies. Enables
agents to plan multi-step game building workflows.

Architecture:
  StrategicPlanner
    |-- TaskGraph (DAG of tasks with prerequisites)
    |-- EffortEstimator (token/time estimate per task)
    |-- ExecutionStrategy (SEQUENTIAL, PARALLEL, CONDITIONAL)
    |-- PlanValidator (cycle detection, completeness check)

Decomposition Levels:
  - epic: multi-session project goal (build a complete game)
  - feature: single-session objective (create player controller)
  - task: individual agent action (write movement script)
  - step: atomic operation (set entity property)

Usage:
    planner = StrategicPlanner()
    plan = planner.decompose("Build a 2D platformer with 3 levels")
    for task in plan.tasks:
        print(f"[{task.priority}] {task.description}")
        for dep in task.depends_on:
            print(f"  depends on: {dep}")
"""

from __future__ import annotations

import itertools
import re
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class TaskStatus(Enum):
    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


class ExecutionStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"


@dataclass
class Subtask:
    task_id: str = ""
    description: str = ""
    category: str = ""
    estimated_tokens: int = 500
    depends_on: List[str] = field(default_factory=list)
    priority: int = 0
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    status: TaskStatus = TaskStatus.PENDING
    output_artifact: str = ""
    assigned_agent: str = ""
    context_hints: Dict[str, Any] = field(default_factory=dict)

    def is_ready(self, completed_ids: Set[str]) -> bool:
        return all(d in completed_ids for d in self.depends_on)


@dataclass
class ExecutionPlan:
    goal: str = ""
    plan_id: str = ""
    context: str = ""
    tasks: List[Subtask] = field(default_factory=list)
    total_estimated_tokens: int = 0
    estimated_steps: int = 0
    critical_path: List[str] = field(default_factory=list)
    parallel_opportunities: List[List[str]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_ready_tasks(self, completed_ids: Set[str]) -> List[Subtask]:
        return [
            t for t in self.tasks
            if t.status != TaskStatus.COMPLETED and t.is_ready(completed_ids)
        ]

    def get_next_action(self, completed_ids: Set[str]) -> Optional[Subtask]:
        ready = self.get_ready_tasks(completed_ids)
        if not ready:
            return None
        return sorted(ready, key=lambda t: t.priority)[0]

    def progress(self) -> float:
        if not self.tasks:
            return 1.0
        completed = sum(1 for t in self.tasks if t.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)

    def to_dict(self) -> dict:
        return {
            "goal": self.goal,
            "tasks": [
                {
                    "id": t.task_id, "description": t.description,
                    "category": t.category, "depends_on": t.depends_on,
                    "priority": t.priority, "status": t.status.value,
                }
                for t in self.tasks
            ],
            "estimated_tokens": self.total_estimated_tokens,
            "estimated_steps": self.estimated_steps,
            "critical_path": self.critical_path,
            "progress": round(self.progress() * 100, 1),
        }


# Game generation task decomposition templates
TASK_TEMPLATES: Dict[str, List[Tuple[str, List[str]]]] = {
    "2d_platformer": [
        ("Design player character entity with physics properties", []),
        ("Create ground and platform collision tiles", ["player_entity"]),
        ("Implement player movement controller", ["player_entity", "collision_setup"]),
        ("Design level 1 layout with progressive difficulty", ["collision_setup"]),
        ("Create collectible item system", ["player_entity"]),
        ("Implement scoring and HUD display", ["collectibles"]),
        ("Add enemy AI patrol patterns", ["collision_setup"]),
        ("Create level transition system", ["level_1", "scoring"]),
        ("Add background parallax scrolling", []),
        ("Implement sound effects and music triggers", ["player_controller"]),
    ],
    "top_down_rpg": [
        ("Design tilemap world with walkable areas", []),
        ("Create player character with stats system", []),
        ("Implement 8-directional movement", ["player_stats", "tilemap"]),
        ("Design NPC dialogue system", ["player_movement"]),
        ("Create inventory and item management", ["player_stats"]),
        ("Implement combat system with actions", ["player_stats", "enemy_setup"]),
        ("Design enemy entities with behavior patterns", ["tilemap"]),
        ("Create quest tracking and progression", ["npc_dialogue"]),
        ("Add fog of war / exploration mechanics", ["tilemap"]),
        ("Implement save/load game state", ["inventory", "quests"]),
    ],
    "puzzle_game": [
        ("Design core puzzle mechanic and rules", []),
        ("Create puzzle grid layout system", ["core_mechanic"]),
        ("Implement input and interaction system", ["puzzle_grid"]),
        ("Design progressive difficulty puzzles (5 levels)", ["puzzle_grid"]),
        ("Create visual feedback and animations", ["interaction"]),
        ("Implement scoring and star rating", ["puzzles"]),
        ("Add hint system", ["puzzles"]),
        ("Create level selection menu", ["scoring"]),
        ("Design tutorial level sequence", ["interaction"]),
        ("Implement accessibility options", ["tutorial"]),
    ],
}

CATEGORY_ESTIMATES: Dict[str, int] = {
    "entity_design": 800,
    "physics_setup": 500,
    "input_code": 600,
    "level_design": 1200,
    "item_system": 700,
    "ui_hud": 600,
    "ai_behavior": 900,
    "transition": 500,
    "visual_effects": 700,
    "audio_setup": 400,
    "world_layout": 1000,
    "dialogue": 800,
    "combat": 1000,
    "quest_system": 900,
    "saving": 700,
    "core_mechanic": 900,
    "grid_logic": 700,
    "scoring_system": 500,
    "menu_ui": 500,
}

CATEGORY_ID = itertools.count(1)


class StrategicPlanner:
    """
    Task decomposition engine for game building workflows.

    Converts high-level game creation goals into ordered subtask
    graphs with dependency management, effort estimation, and
    execution strategy selection.

    Usage:
        sp = StrategicPlanner()
        plan = sp.decompose(
            "Create a 2D platformer",
            context={"available_systems": ["physics", "input", "collision"]},
        )
        completed: Set[str] = set()
        while plan.progress() < 1.0:
            next_task = plan.get_next_action(completed)
            if not next_task:
                break
            execute(next_task)
            completed.add(next_task.task_id)
    """

    def __init__(self):
        self._plan_count: int = 0
        self._total_tasks_planned: int = 0
        self._active_plans: Dict[str, ExecutionPlan] = {}

    def decompose(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        max_tasks: int = 20,
    ) -> ExecutionPlan:
        self._plan_count += 1
        context = context or {}

        game_type = self._detect_game_type(goal)

        if game_type and game_type in TASK_TEMPLATES:
            tasks = self._from_template(game_type, goal)
        else:
            tasks = self._from_heuristic(goal, max_tasks)

        total_tokens = sum(t.estimated_tokens for t in tasks)
        critical = self._compute_critical_path(tasks)
        parallel_groups = self._find_parallel_opportunities(tasks)

        plan = ExecutionPlan(
            plan_id=str(uuid.uuid4())[:8],
            goal=goal,
            context=context.get("available_systems", "") if isinstance(context, dict) else str(context),
            tasks=tasks,
            total_estimated_tokens=total_tokens,
            estimated_steps=len(tasks),
            critical_path=critical,
            parallel_opportunities=parallel_groups,
        )

        self._total_tasks_planned += len(tasks)
        self._active_plans[goal[:50]] = plan
        return plan

    def continue_plan(self, plan: ExecutionPlan, next_steps: int = 5) -> ExecutionPlan:
        completed_ids = {
            t.task_id for t in plan.tasks
            if t.status == TaskStatus.COMPLETED
        }
        pending = [
            t for t in plan.tasks
            if t.status != TaskStatus.COMPLETED
        ]
        remaining_descriptions = [t.description for t in pending]

        new_tasks = self._from_descriptions(
            remaining_descriptions[:next_steps],
            len(plan.tasks),
        )
        plan.tasks.extend(new_tasks)
        plan.estimated_steps = len(plan.tasks)
        plan.total_estimated_tokens = sum(t.estimated_tokens for t in plan.tasks)
        plan.critical_path = self._compute_critical_path(plan.tasks)
        return plan

    def validate_plan(self, plan: ExecutionPlan) -> List[str]:
        issues: List[str] = []
        task_ids = {t.task_id for t in plan.tasks}

        for task in plan.tasks:
            for dep_id in task.depends_on:
                if dep_id not in task_ids:
                    issues.append(f"{task.task_id}: missing dependency '{dep_id}'")

        visited: Set[str] = set()
        rec_stack: Set[str] = set()
        deps_map = {t.task_id: set(t.depends_on) for t in plan.tasks}

        def _has_cycle(tid: str) -> bool:
            visited.add(tid)
            rec_stack.add(tid)
            for dep in deps_map.get(tid, set()):
                if dep not in visited:
                    if _has_cycle(dep):
                        return True
                elif dep in rec_stack:
                    return True
            rec_stack.discard(tid)
            return False

        for tid in task_ids:
            if tid not in visited:
                if _has_cycle(tid):
                    issues.append(f"Cycle detected involving '{tid}'")
                    break

        if not plan.tasks:
            issues.append("Plan has no tasks")

        return issues

    def get_active_plan(self, goal_key: str = "") -> Optional[ExecutionPlan]:
        if goal_key:
            return self._active_plans.get(goal_key)
        return next(iter(self._active_plans.values()), None)

    def get_stats(self) -> dict:
        return {
            "plans_created": self._plan_count,
            "total_tasks": self._total_tasks_planned,
            "active_plans": len(self._active_plans),
            "avg_tasks_per_plan": round(
                self._total_tasks_planned / max(self._plan_count, 1), 1,
            ),
        }

    def clear(self) -> None:
        self._plan_count = 0
        self._total_tasks_planned = 0
        self._active_plans.clear()

    def list_templates(self) -> List[str]:
        return list(TASK_TEMPLATES.keys())

    def create_plan(self, goal: str, game_type: str = "2d_platformer", max_depth: int = 5, metadata: dict = None) -> ExecutionPlan:
        return self.decompose(goal, game_type, max_depth)

    def get_plan(self, goal_key: str) -> Optional[ExecutionPlan]:
        return self.get_active_plan(goal_key)

    @staticmethod
    def _detect_game_type(goal: str) -> Optional[str]:
        gl = goal.lower()
        if any(k in gl for k in ["platformer", "platform", "jump", "side-scroll"]):
            return "2d_platformer"
        if any(k in gl for k in ["rpg", "role-playing", "dungeon", "adventure"]):
            return "top_down_rpg"
        if any(k in gl for k in ["puzzle", "match", "connect"]):
            return "puzzle_game"
        return None

    def _from_template(self, game_type: str, goal: str) -> List[Subtask]:
        template = TASK_TEMPLATES.get(game_type, [])
        tasks: List[Subtask] = []
        id_map: Dict[str, str] = {}

        for i, (desc, deps) in enumerate(template):
            task_id = f"task_{next(CATEGORY_ID):03d}"
            category = self._categorize(desc)
            tasks.append(Subtask(
                task_id=task_id,
                description=f"{desc} for: {goal[:40]}",
                category=category,
                estimated_tokens=CATEGORY_ESTIMATES.get(category, 500),
                depends_on=self._resolve_deps(deps, id_map),
                priority=i,
            ))
            id_map[desc.lower().replace(" ", "_")[:20]] = task_id

        return tasks

    @staticmethod
    def _from_heuristic(goal: str, max_tasks: int) -> List[Subtask]:
        tasks: List[Subtask] = []
        keywords = re.findall(r'\b(world|level|player|enemy|character|item|ui|sound|ai)\b', goal.lower())

        default_steps = [
            ("Define core game design parameters", "game_design"),
            ("Set up world/scene structure", "world_layout"),
            ("Create player entity with basic properties", "entity_design"),
            ("Implement primary input and movement", "input_code"),
            ("Design first level / play area", "level_design"),
            ("Add interactive elements / obstacles", "item_system"),
            ("Implement core game loop logic", "core_mechanic"),
            ("Add visual feedback and effects", "visual_effects"),
            ("Set up basic UI / HUD", "ui_hud"),
            ("Test and balance initial prototype", "scoring_system"),
        ]

        for i, (desc, cat) in enumerate(default_steps[:max_tasks]):
            deps = [tasks[-1].task_id] if tasks else []
            tasks.append(Subtask(
                task_id=f"task_h{next(CATEGORY_ID):03d}",
                description=f"{desc} for {goal[:30]}",
                category=cat,
                estimated_tokens=CATEGORY_ESTIMATES.get(cat, 600),
                depends_on=deps,
                priority=i,
            ))

        return tasks

    def _from_descriptions(
        self, descriptions: List[str], offset: int,
    ) -> List[Subtask]:
        tasks: List[Subtask] = []
        for i, desc in enumerate(descriptions):
            tasks.append(Subtask(
                task_id=f"task_c{next(CATEGORY_ID):03d}",
                description=f"Continue: {desc[:80]}",
                category=self._categorize(desc),
                estimated_tokens=600,
                depends_on=[],
                priority=offset + i,
            ))
        return tasks

    @staticmethod
    def _categorize(desc: str) -> str:
        dl = desc.lower()
        if any(k in dl for k in ["player", "character", "entity"]):
            return "entity_design"
        if any(k in dl for k in ["physics", "collision", "force"]):
            return "physics_setup"
        if any(k in dl for k in ["input", "controller", "movement"]):
            return "input_code"
        if any(k in dl for k in ["level", "layout", "map"]):
            return "level_design"
        if any(k in dl for k in ["item", "inventory", "collect"]):
            return "item_system"
        if any(k in dl for k in ["ui", "hud", "menu", "display"]):
            return "ui_hud"
        if any(k in dl for k in ["enemy", "ai", "behavior", "patrol"]):
            return "ai_behavior"
        if any(k in dl for k in ["sound", "audio", "music"]):
            return "audio_setup"
        if any(k in dl for k in ["transition", "scene", "change"]):
            return "transition"
        if any(k in dl for k in ["visual", "effect", "particle"]):
            return "visual_effects"
        if any(k in dl for k in ["save", "load", "persist"]):
            return "saving"
        if any(k in dl for k in ["combat", "attack", "damage"]):
            return "combat"
        return "core_mechanic"

    @staticmethod
    def _resolve_deps(
        deps: List[str], id_map: Dict[str, str],
    ) -> List[str]:
        resolved: List[str] = []
        for d in deps:
            mapped = id_map.get(d)
            if mapped:
                resolved.append(mapped)
        return resolved

    @staticmethod
    def _compute_critical_path(tasks: List[Subtask]) -> List[str]:
        if not tasks:
            return []
        deps_map = {t.task_id: t.depends_on for t in tasks}
        costs = {t.task_id: t.estimated_tokens for t in tasks}

        earliest_start: Dict[str, int] = {}
        for t in tasks:
            if not t.depends_on:
                earliest_start[t.task_id] = 0
            else:
                earliest_start[t.task_id] = max(
                    (earliest_start.get(d, 0) + costs.get(d, 0)
                     for d in t.depends_on),
                    default=0,
                )

        max_finish = max(
            (earliest_start.get(t.task_id, 0) + costs.get(t.task_id, 0)
             for t in tasks),
            default=0,
        )

        latest_start: Dict[str, int] = {t.task_id: max_finish for t in tasks}
        for t in reversed(tasks):
            if all(
                t.task_id not in tasks[i].depends_on
                for i in range(len(tasks))
            ):
                latest_start[t.task_id] = max_finish - costs.get(t.task_id, 0)

        return [
            t.task_id for t in tasks
            if earliest_start.get(t.task_id, 0) == latest_start.get(t.task_id, max_finish)
        ][:5]

    @staticmethod
    def _find_parallel_opportunities(
        tasks: List[Subtask],
    ) -> List[List[str]]:
        groups: Dict[int, List[str]] = {}
        for t in tasks:
            depth = len(t.depends_on)
            groups.setdefault(depth, []).append(t.task_id)
        return [ids for ids in groups.values() if len(ids) > 1]


_global_planner: Optional[StrategicPlanner] = None


def get_strategic_planner() -> StrategicPlanner:
    global _global_planner
    if _global_planner is None:
        _global_planner = StrategicPlanner()
    return _global_planner
