"""
SparkLabs Agent - Hierarchical Task Network Planner

A hierarchical task network (HTN) planner for game AI agent decision-making
that decomposes high-level goals into executable primitive actions through
recursive method expansion. The planner supports multiple decomposition
strategies, plan validation, stepwise execution, dynamic replanning, and
a shared blackboard for inter-task communication at runtime.

Core capabilities:
  - Hierarchical decomposition of compound and goal tasks into primitives
  - Multi-strategy planning (depth-first, breadth-first, best-first, cost-based)
  - Method selection with success-rate weighting and cost optimization
  - Precondition checking with rich comparison operators against world state
  - Effect application with set/add/mul/delete/toggle semantics
  - Axiom-based invariant enforcement across all world state transitions
  - Plan execution with step-by-step blackboard state propagation
  - Dynamic replanning from current world state when plans fail
  - Plan validation with structural and semantic integrity checks
  - Thread-safe singleton engine with reentrant locking

Architecture:
  HTNPlannerEngine (Singleton)
    |-- HTNTask (primitive, compound, or goal with preconditions and effects)
    |-- HTNMethod (decomposition rule with precondition and subtask sequence)
    |-- HTNDomain (task/method container with axioms and defaults)
    |-- HTNPlan (ordered step sequence with blackboard and status tracking)
    |-- HTNWorldState (versioned fact store with timestamp)
    |-- PlanStatus / TaskType / DecompositionStrategy (enums)
    |-- generate_plan() / step_plan() / execute_plan() / replan()
    |-- validate_plan() / get_stats() / get_running_plans()

Usage:
    planner = get_htn_planner()

    domain = planner.create_domain("combat_ai", tasks={}, methods={})
    planner.add_task(domain.domain_id, HTNTask(
        task_id="attack_enemy",
        name="Attack Enemy",
        is_primitive=True,
        preconditions=[{"key": "enemy_visible", "op": "eq", "value": True}],
        effects=[{"key": "enemy_health", "op": "add", "value": -30}],
        cost=3.0,
    ))
    planner.add_method(domain.domain_id, HTNMethod(
        method_id="engage_combat_method",
        name="Engage Combat",
        task_id="engage_enemy",
        preconditions=[{"key": "enemy_in_range", "op": "eq", "value": True}],
        subtask_sequence=["move_to_enemy", "attack_enemy"],
        cost=5.0,
        success_rate=0.85,
    ))

    world_state = {"enemy_visible": True, "enemy_in_range": True, "enemy_health": 100}
    plan = planner.generate_plan(domain.domain_id, "engage_enemy", world_state)
    if plan.status == PlanStatus.COMPLETED:
        planner.execute_plan(plan.plan_id, world_state)
"""

from __future__ import annotations

import copy
import heapq
import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PlanStatus(Enum):
    """Lifecycle status of an HTN plan."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class TaskType(Enum):
    """Classification of tasks within the HTN domain."""
    PRIMITIVE = "primitive"
    COMPOUND = "compound"
    GOAL = "goal"


class DecompositionStrategy(Enum):
    """Strategies for ordering task decomposition during planning."""
    DEPTH_FIRST = "depth_first"
    BREADTH_FIRST = "breadth_first"
    BEST_FIRST = "best_first"
    COST_BASED = "cost_based"


# ---------------------------------------------------------------------------
# Condition and Effect Operators
# ---------------------------------------------------------------------------

_CONDITION_OPS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": lambda actual, expected: actual == expected,
    "neq": lambda actual, expected: actual != expected,
    "gt": lambda actual, expected: isinstance(actual, (int, float)) and actual > expected,
    "lt": lambda actual, expected: isinstance(actual, (int, float)) and actual < expected,
    "gte": lambda actual, expected: isinstance(actual, (int, float)) and actual >= expected,
    "lte": lambda actual, expected: isinstance(actual, (int, float)) and actual <= expected,
    "exists": lambda actual, _expected: True,
    "not_exists": lambda actual, _expected: False,
    "in": lambda actual, expected: actual in expected if hasattr(expected, "__contains__") else False,
    "contains": lambda actual, expected: expected in actual if hasattr(actual, "__contains__") else False,
}


def _apply_effect_op(state: Dict[str, Any], key: str, op: str, value: Any) -> None:
    """Apply a single effect to a mutable world state dictionary in place."""
    if op == "set":
        state[key] = value
    elif op == "add":
        current = state.get(key, 0)
        if isinstance(current, (int, float)):
            state[key] = current + value
        else:
            state[key] = value
    elif op == "mul":
        current = state.get(key, 0)
        if isinstance(current, (int, float)):
            state[key] = current * value
        else:
            state[key] = value
    elif op == "delete":
        state.pop(key, None)
    elif op == "toggle":
        state[key] = not state.get(key, False)
    elif op == "min":
        current = state.get(key, 0)
        if isinstance(current, (int, float)):
            state[key] = min(current, value)
        else:
            state[key] = value
    elif op == "max":
        current = state.get(key, 0)
        if isinstance(current, (int, float)):
            state[key] = max(current, value)
        else:
            state[key] = value
    elif op == "append":
        existing = state.get(key, [])
        if isinstance(existing, list):
            existing.append(value)
            state[key] = existing
        else:
            state[key] = [value]
    else:
        state[key] = value


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class HTNTask:
    """A task node in the HTN domain hierarchy.

    Primitive tasks are directly executable and carry preconditions,
    effects, cost, and timeout. Compound and goal tasks are decomposed
    by methods into subtask sequences.

    Attributes:
        task_id: Unique identifier for this task.
        name: Human-readable task name.
        parameters: Named parameters that can be bound at planning time.
        preconditions: List of condition dicts with keys: key, op, value.
        effects: List of effect dicts with keys: key, op, value.
        subtasks: For compound tasks, the default subtask IDs if no
            method is specified; for primitives, empty.
        is_primitive: Whether this task is directly executable.
        cost: Base execution cost for this task.
        priority: Task priority (higher = tried first).
        timeout: Maximum execution time in seconds.
        max_retries: Maximum retry attempts on execution failure.
        metadata: Arbitrary key-value metadata for extensions.
    """
    task_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    preconditions: List[Dict[str, Any]] = field(default_factory=list)
    effects: List[Dict[str, Any]] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    is_primitive: bool = False
    cost: float = 1.0
    priority: int = 0
    timeout: float = 0.0
    max_retries: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "parameters": copy.deepcopy(self.parameters),
            "preconditions": copy.deepcopy(self.preconditions),
            "effects": copy.deepcopy(self.effects),
            "subtasks": list(self.subtasks),
            "is_primitive": self.is_primitive,
            "cost": self.cost,
            "priority": self.priority,
            "timeout": self.timeout,
            "max_retries": self.max_retries,
            "metadata": copy.deepcopy(self.metadata),
        }

    def get_task_type(self) -> TaskType:
        if self.is_primitive:
            return TaskType.PRIMITIVE
        if self.subtasks:
            return TaskType.COMPOUND
        return TaskType.GOAL


@dataclass
class HTNMethod:
    """A decomposition method for a compound or goal task.

    Each method specifies how a parent task decomposes into an ordered
    sequence of subtask IDs. Methods are tried in priority order, with
    success_rate used as a tiebreaker in best-first/cost-based strategies.

    Attributes:
        method_id: Unique identifier for this method.
        name: Human-readable method name.
        task_id: The parent task this method decomposes.
        preconditions: List of condition dicts that must hold for this
            method to be applicable.
        subtask_sequence: Ordered list of subtask IDs to execute.
        cost: Additional cost incurred when using this method.
        success_rate: Estimated probability of success (0.0 to 1.0).
        metadata: Arbitrary key-value metadata for extensions.
    """
    method_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    task_id: str = ""
    preconditions: List[Dict[str, Any]] = field(default_factory=list)
    subtask_sequence: List[str] = field(default_factory=list)
    cost: float = 0.0
    success_rate: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "method_id": self.method_id,
            "name": self.name,
            "task_id": self.task_id,
            "preconditions": copy.deepcopy(self.preconditions),
            "subtask_sequence": list(self.subtask_sequence),
            "cost": self.cost,
            "success_rate": self.success_rate,
            "metadata": copy.deepcopy(self.metadata),
        }


@dataclass
class HTNDomain:
    """A complete HTN domain definition.

    Encapsulates all tasks, methods, axioms, and world state defaults
    for a planning problem domain. Multiple domains can coexist in the
    planner engine simultaneously.

    Attributes:
        domain_id: Unique identifier for this domain.
        name: Human-readable domain name.
        tasks: Dictionary mapping task_id to HTNTask.
        methods: Dictionary mapping method_id to HTNMethod.
        axioms: List of always-true rules (applied after every effect).
        world_state_defaults: Default world state facts for this domain.
    """
    domain_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tasks: Dict[str, HTNTask] = field(default_factory=dict)
    methods: Dict[str, HTNMethod] = field(default_factory=dict)
    axioms: List[Dict[str, Any]] = field(default_factory=list)
    world_state_defaults: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain_id": self.domain_id,
            "name": self.name,
            "tasks": {tid: t.to_dict() for tid, t in self.tasks.items()},
            "methods": {mid: m.to_dict() for mid, m in self.methods.items()},
            "axioms": copy.deepcopy(self.axioms),
            "world_state_defaults": copy.deepcopy(self.world_state_defaults),
        }

    def get_methods_for_task(self, task_id: str) -> List[HTNMethod]:
        return [
            m for m in self.methods.values() if m.task_id == task_id
        ]


@dataclass
class HTNPlan:
    """A generated plan ready for execution or currently executing.

    Contains the ordered sequence of primitive task IDs to execute,
    along with execution state tracking, a shared blackboard for
    inter-task data sharing, and plan-level metadata.

    Attributes:
        plan_id: Unique identifier for this plan.
        domain_id: The domain this plan was generated from.
        goal_task_id: The root goal task that was decomposed.
        steps: Ordered list of primitive task IDs to execute.
        current_step_index: Index of the next step to execute.
        status: Current lifecycle status of the plan.
        blackboard: Shared runtime state accessible by all tasks.
        start_time: Timestamp when plan execution began.
        total_cost: Accumulated cost of all primitive tasks in the plan.
        metadata: Arbitrary key-value metadata for extensions.
    """
    plan_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    domain_id: str = ""
    goal_task_id: str = ""
    steps: List[str] = field(default_factory=list)
    current_step_index: int = 0
    status: PlanStatus = PlanStatus.PENDING
    blackboard: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    total_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "domain_id": self.domain_id,
            "goal_task_id": self.goal_task_id,
            "steps": list(self.steps),
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "blackboard": copy.deepcopy(self.blackboard),
            "start_time": self.start_time,
            "total_cost": self.total_cost,
            "metadata": copy.deepcopy(self.metadata),
        }

    def remaining_steps(self) -> List[str]:
        return self.steps[self.current_step_index:]

    def is_terminal(self) -> bool:
        return self.status in (PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.ABORTED)


@dataclass
class HTNWorldState:
    """A versioned snapshot of the world state for HTN planning.

    Each mutation increments the version counter, enabling efficient
    change detection and caching in the planning engine.

    Attributes:
        state_id: Unique identifier for this state snapshot.
        facts: Dictionary of key-value fact pairs.
        version: Monotonically increasing version counter.
        timestamp: When this state was created or last updated.
    """
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    facts: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "facts": copy.deepcopy(self.facts),
            "version": self.version,
            "timestamp": self.timestamp,
        }

    def snapshot(self) -> HTNWorldState:
        return HTNWorldState(
            state_id=uuid.uuid4().hex,
            facts=copy.deepcopy(self.facts),
            version=self.version,
            timestamp=_time_module.time(),
        )

    def update(self, key: str, value: Any) -> None:
        self.facts[key] = value
        self.version += 1
        self.timestamp = _time_module.time()

    def delete(self, key: str) -> None:
        self.facts.pop(key, None)
        self.version += 1
        self.timestamp = _time_module.time()

    def get(self, key: str, default: Any = None) -> Any:
        return self.facts.get(key, default)


# ---------------------------------------------------------------------------
# HTN Planner Engine (Singleton)
# ---------------------------------------------------------------------------


class HTNPlannerEngine:
    """Hierarchical Task Network planner engine for game AI.

    Manages HTN domains, generates plans from goal tasks by recursively
    decomposing compound tasks via applicable methods, and executes plans
    step-by-step with shared blackboard state. Supports dynamic replanning
    when the world state changes mid-execution.

    The engine is a thread-safe singleton accessed via get_htn_planner().
    """

    _instance: Optional["HTNPlannerEngine"] = None
    _lock = threading.RLock()

    _MAX_DECOMPOSITION_DEPTH: int = 64
    _MAX_PLAN_STEPS: int = 512
    _MAX_MTR_SIZE: int = 256

    def __init__(self) -> None:
        self._domains: Dict[str, HTNDomain] = {}
        self._plans: Dict[str, HTNPlan] = {}
        self._running_plans: Set[str] = set()
        self._default_strategy: DecompositionStrategy = DecompositionStrategy.DEPTH_FIRST

        self._total_domains_created: int = 0
        self._total_domains_deleted: int = 0
        self._total_plans_generated: int = 0
        self._total_plans_completed: int = 0
        self._total_plans_failed: int = 0
        self._total_plans_aborted: int = 0
        self._total_replans: int = 0
        self._total_steps_executed: int = 0

    @classmethod
    def get_instance(cls) -> "HTNPlannerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Domain Management
    # ------------------------------------------------------------------

    def create_domain(
        self,
        name: str,
        tasks: Optional[Dict[str, HTNTask]] = None,
        methods: Optional[Dict[str, HTNMethod]] = None,
        axioms: Optional[List[Dict[str, Any]]] = None,
        world_state_defaults: Optional[Dict[str, Any]] = None,
    ) -> HTNDomain:
        with self._lock:
            domain = HTNDomain(
                name=name,
                tasks=tasks or {},
                methods=methods or {},
                axioms=axioms or [],
                world_state_defaults=world_state_defaults or {},
            )
            self._domains[domain.domain_id] = domain
            self._total_domains_created += 1
            return domain

    def delete_domain(self, domain_id: str) -> bool:
        with self._lock:
            if domain_id not in self._domains:
                return False

            plan_ids_to_remove = [
                pid for pid, plan in self._plans.items()
                if plan.domain_id == domain_id
            ]
            for pid in plan_ids_to_remove:
                self._running_plans.discard(pid)
                del self._plans[pid]

            del self._domains[domain_id]
            self._total_domains_deleted += 1
            return True

    def add_task(self, domain_id: str, task: HTNTask) -> bool:
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False
            domain.tasks[task.task_id] = task
            return True

    def add_method(self, domain_id: str, method: HTNMethod) -> bool:
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False
            domain.methods[method.method_id] = method
            return True

    def get_domain(self, domain_id: str) -> Optional[HTNDomain]:
        with self._lock:
            return self._domains.get(domain_id)

    # ------------------------------------------------------------------
    # Plan Generation
    # ------------------------------------------------------------------

    def generate_plan(
        self,
        domain_id: str,
        goal_task_id: str,
        initial_world_state: Dict[str, Any],
        strategy: Optional[DecompositionStrategy] = None,
    ) -> HTNPlan:
        with self._lock:
            self._total_plans_generated += 1
            active_strategy = strategy or self._default_strategy

            domain = self._domains.get(domain_id)
            plan = HTNPlan(
                domain_id=domain_id,
                goal_task_id=goal_task_id,
                status=PlanStatus.FAILED,
            )
            self._plans[plan.plan_id] = plan

            if domain is None:
                self._total_plans_failed += 1
                return plan

            if goal_task_id not in domain.tasks:
                self._total_plans_failed += 1
                return plan

            sim_state = copy.deepcopy(initial_world_state)

            for axiom in domain.axioms:
                _apply_effect_op(
                    sim_state,
                    axiom.get("key", ""),
                    axiom.get("op", "set"),
                    axiom.get("value"),
                )

            mtr: Set[Tuple[str, str]] = set()

            active_strategy_val = active_strategy or self._default_strategy
            result = self._decompose_task(
                goal_task_id,
                domain,
                sim_state,
                mtr,
                0,
                active_strategy_val,
            )

            if result is None:
                self._total_plans_failed += 1
                return plan

            primitive_steps, total_cost = result
            plan.steps = primitive_steps
            plan.total_cost = total_cost
            plan.status = PlanStatus.COMPLETED
            plan.current_step_index = 0
            self._total_plans_completed += 1
            return plan

    def _decompose_task(
        self,
        task_id: str,
        domain: HTNDomain,
        world_state: Dict[str, Any],
        mtr: Set[Tuple[str, str]],
        depth: int,
        strategy: DecompositionStrategy,
    ) -> Optional[Tuple[List[str], float]]:
        if depth > self._MAX_DECOMPOSITION_DEPTH:
            return None

        if len(mtr) > self._MAX_MTR_SIZE:
            return None

        task = domain.tasks.get(task_id)
        if task is None:
            return None

        if task.is_primitive:
            if not self._check_preconditions(task, world_state):
                return None
            for effect in task.effects:
                _apply_effect_op(
                    world_state,
                    effect.get("key", ""),
                    effect.get("op", "set"),
                    effect.get("value"),
                )
            for axiom in domain.axioms:
                _apply_effect_op(
                    world_state,
                    axiom.get("key", ""),
                    axiom.get("op", "set"),
                    axiom.get("value"),
                )
            return ([task_id], task.cost)

        methods = domain.get_methods_for_task(task_id)
        ordered_methods = self._rank_methods(methods, strategy)

        if task.subtasks:
            methods.append(HTNMethod(
                method_id=f"__inline__{task_id}",
                name=f"Inline: {task.name}",
                task_id=task_id,
                subtask_sequence=task.subtasks,
                cost=0.0,
                success_rate=1.0,
            ))
            ordered_methods = self._rank_methods(
                domain.get_methods_for_task(task_id) + methods[-1:],
                strategy,
            )
            methods = domain.get_methods_for_task(task_id) + [methods[-1]]

        if not ordered_methods:
            return None

        for method in ordered_methods:
            if not self._check_method_preconditions(method, world_state):
                continue

            mtr_key = (task_id, method.method_id)
            if mtr_key in mtr:
                continue

            saved_state = copy.deepcopy(world_state)
            new_mtr = mtr | {mtr_key}

            result = self._decompose_sequence(
                method.subtask_sequence,
                domain,
                world_state,
                new_mtr,
                depth + 1,
                strategy,
            )

            if result is not None:
                sub_steps, sub_cost = result
                return (sub_steps, sub_cost + method.cost)

            world_state.clear()
            world_state.update(saved_state)

        return None

    def _decompose_sequence(
        self,
        subtask_ids: List[str],
        domain: HTNDomain,
        world_state: Dict[str, Any],
        mtr: Set[Tuple[str, str]],
        depth: int,
        strategy: DecompositionStrategy,
    ) -> Optional[Tuple[List[str], float]]:
        all_steps: List[str] = []
        total_cost: float = 0.0

        if len(all_steps) > self._MAX_PLAN_STEPS:
            return None

        for sub_id in subtask_ids:
            result = self._decompose_task(
                sub_id,
                domain,
                world_state,
                mtr,
                depth,
                strategy,
            )
            if result is None:
                return None
            substeps, subcost = result
            all_steps.extend(substeps)
            total_cost += subcost

            if len(all_steps) > self._MAX_PLAN_STEPS:
                return None

        return (all_steps, total_cost)

    def _rank_methods(
        self,
        methods: List[HTNMethod],
        strategy: DecompositionStrategy,
    ) -> List[HTNMethod]:
        if not methods:
            return []

        if strategy == DecompositionStrategy.COST_BASED:
            return sorted(
                methods,
                key=lambda m: (m.cost / max(m.success_rate, 0.01), -m.success_rate),
            )
        elif strategy == DecompositionStrategy.BEST_FIRST:
            return sorted(
                methods,
                key=lambda m: (-m.success_rate, m.cost),
            )
        elif strategy == DecompositionStrategy.BREADTH_FIRST:
            return sorted(methods, key=lambda m: len(m.subtask_sequence))
        else:
            return sorted(methods, key=lambda m: (-m.success_rate, m.cost))

    def _check_preconditions(
        self,
        task: HTNTask,
        world_state: Dict[str, Any],
    ) -> bool:
        return self._evaluate_conditions(task.preconditions, world_state)

    def _check_method_preconditions(
        self,
        method: HTNMethod,
        world_state: Dict[str, Any],
    ) -> bool:
        return self._evaluate_conditions(method.preconditions, world_state)

    def _evaluate_conditions(
        self,
        conditions: List[Dict[str, Any]],
        world_state: Dict[str, Any],
    ) -> bool:
        if not conditions:
            return True

        for condition in conditions:
            key = condition.get("key", "")
            op = condition.get("op", "eq")
            expected = condition.get("value")

            op_func = _CONDITION_OPS.get(op)
            if op_func is None:
                return False

            if op == "exists":
                if key not in world_state:
                    return False
                continue
            if op == "not_exists":
                if key in world_state:
                    return False
                continue

            actual = world_state.get(key)
            if not op_func(actual, expected):
                return False

        return True

    def _apply_effects(
        self,
        effects: List[Dict[str, Any]],
        world_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        for effect in effects:
            _apply_effect_op(
                world_state,
                effect.get("key", ""),
                effect.get("op", "set"),
                effect.get("value"),
            )
        return world_state

    # ------------------------------------------------------------------
    # Plan Execution
    # ------------------------------------------------------------------

    def step_plan(self, plan_id: str) -> Optional[str]:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            if plan.is_terminal():
                return None
            if plan.status == PlanStatus.PENDING:
                plan.status = PlanStatus.IN_PROGRESS
                plan.start_time = _time_module.time()
                self._running_plans.add(plan_id)

            if plan.current_step_index >= len(plan.steps):
                plan.status = PlanStatus.COMPLETED
                self._running_plans.discard(plan_id)
                self._total_plans_completed += 1
                return None

            next_task_id = plan.steps[plan.current_step_index]
            plan.current_step_index += 1
            self._total_steps_executed += 1

            if plan.current_step_index >= len(plan.steps):
                plan.status = PlanStatus.COMPLETED
                self._running_plans.discard(plan_id)
                self._total_plans_completed += 1

            return next_task_id

    def execute_plan(
        self,
        plan_id: str,
        world_state: Dict[str, Any],
    ) -> List[HTNTask]:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []

            domain = self._domains.get(plan.domain_id)
            if domain is None:
                plan.status = PlanStatus.FAILED
                self._total_plans_failed += 1
                return []

            if plan.status == PlanStatus.PENDING:
                plan.status = PlanStatus.IN_PROGRESS
                plan.start_time = _time_module.time()
                self._running_plans.add(plan_id)

            completed_tasks: List[HTNTask] = []
            sim_state = copy.deepcopy(world_state)

            for axiom in domain.axioms:
                _apply_effect_op(
                    sim_state,
                    axiom.get("key", ""),
                    axiom.get("op", "set"),
                    axiom.get("value"),
                )

            for step_id in plan.steps[plan.current_step_index:]:
                task = domain.tasks.get(step_id)
                if task is None:
                    plan.status = PlanStatus.FAILED
                    self._running_plans.discard(plan_id)
                    self._total_plans_failed += 1
                    return completed_tasks

                if not self._check_preconditions(task, sim_state):
                    if task.max_retries > 0:
                        for _ in range(task.max_retries):
                            if self._check_preconditions(task, sim_state):
                                break
                        else:
                            plan.status = PlanStatus.FAILED
                            self._running_plans.discard(plan_id)
                            self._total_plans_failed += 1
                            return completed_tasks
                    else:
                        plan.status = PlanStatus.FAILED
                        self._running_plans.discard(plan_id)
                        self._total_plans_failed += 1
                        return completed_tasks

                for effect in task.effects:
                    _apply_effect_op(
                        sim_state,
                        effect.get("key", ""),
                        effect.get("op", "set"),
                        effect.get("value"),
                    )

                for axiom in domain.axioms:
                    _apply_effect_op(
                        sim_state,
                        axiom.get("key", ""),
                        axiom.get("op", "set"),
                        axiom.get("value"),
                    )

                completed_tasks.append(task)
                plan.current_step_index += 1
                self._total_steps_executed += 1

            world_state.clear()
            world_state.update(sim_state)
            plan.blackboard = {**plan.blackboard, **sim_state}
            plan.status = PlanStatus.COMPLETED
            self._running_plans.discard(plan_id)
            self._total_plans_completed += 1
            return completed_tasks

    def replan(
        self,
        plan_id: str,
        current_world_state: Dict[str, Any],
    ) -> Optional[HTNPlan]:
        with self._lock:
            old_plan = self._plans.get(plan_id)
            if old_plan is None:
                return None

            domain = self._domains.get(old_plan.domain_id)
            if domain is None:
                return None

            self._running_plans.discard(plan_id)
            old_plan.status = PlanStatus.ABORTED
            self._total_plans_aborted += 1

            new_plan = self.generate_plan(
                domain_id=old_plan.domain_id,
                goal_task_id=old_plan.goal_task_id,
                initial_world_state=current_world_state,
                strategy=self._default_strategy,
            )

            new_plan.blackboard = copy.deepcopy(old_plan.blackboard)
            new_plan.metadata["replan_of"] = plan_id
            new_plan.metadata["replan_reason"] = "world_state_changed"

            self._total_replans += 1
            return new_plan

    def abort_plan(self, plan_id: str) -> bool:
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False
            if plan.is_terminal():
                return False
            plan.status = PlanStatus.ABORTED
            self._running_plans.discard(plan_id)
            self._total_plans_aborted += 1
            return True

    def validate_plan(self, plan_id: str) -> List[str]:
        with self._lock:
            issues: List[str] = []
            plan = self._plans.get(plan_id)
            if plan is None:
                issues.append("Plan not found.")
                return issues

            domain = self._domains.get(plan.domain_id)
            if domain is None:
                issues.append("Domain not found for plan.")
                return issues

            if plan.goal_task_id not in domain.tasks:
                issues.append(f"Goal task '{plan.goal_task_id}' missing from domain.")

            for i, step_id in enumerate(plan.steps):
                task = domain.tasks.get(step_id)
                if task is None:
                    issues.append(f"Step {i}: task '{step_id}' not found in domain.")
                    continue
                if not task.is_primitive:
                    issues.append(
                        f"Step {i}: task '{step_id}' ({task.name}) is not primitive "
                        f"but appears in the plan's primitive step list."
                    )

            if len(plan.steps) > self._MAX_PLAN_STEPS:
                issues.append(
                    f"Plan has {len(plan.steps)} steps, exceeding limit of "
                    f"{self._MAX_PLAN_STEPS}."
                )

            if len(plan.steps) == 0:
                issues.append("Plan has no steps.")

            if plan.status == PlanStatus.FAILED:
                issues.append("Plan is in FAILED status.")

            if plan.status == PlanStatus.ABORTED:
                issues.append("Plan was aborted.")

            return issues

    def get_plan(self, plan_id: str) -> Optional[HTNPlan]:
        with self._lock:
            return self._plans.get(plan_id)

    def get_running_plans(self) -> List[HTNPlan]:
        with self._lock:
            return [
                self._plans[pid]
                for pid in self._running_plans
                if pid in self._plans
            ]

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_domains": len(self._domains),
                "total_domains_created": self._total_domains_created,
                "total_domains_deleted": self._total_domains_deleted,
                "total_plans": len(self._plans),
                "total_plans_generated": self._total_plans_generated,
                "total_plans_completed": self._total_plans_completed,
                "total_plans_failed": self._total_plans_failed,
                "total_plans_aborted": self._total_plans_aborted,
                "total_replans": self._total_replans,
                "running_plans": len(self._running_plans),
                "total_steps_executed": self._total_steps_executed,
                "max_decomposition_depth": self._MAX_DECOMPOSITION_DEPTH,
                "max_plan_steps": self._MAX_PLAN_STEPS,
                "default_strategy": self._default_strategy.value,
            }

    def set_default_strategy(self, strategy: DecompositionStrategy) -> None:
        with self._lock:
            self._default_strategy = strategy

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._domains.clear()
            self._plans.clear()
            self._running_plans.clear()
            self._total_domains_created = 0
            self._total_domains_deleted = 0
            self._total_plans_generated = 0
            self._total_plans_completed = 0
            self._total_plans_failed = 0
            self._total_plans_aborted = 0
            self._total_replans = 0
            self._total_steps_executed = 0


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_htn_planner() -> HTNPlannerEngine:
    """Return the singleton HTNPlannerEngine instance.

    This is the primary access point for the HTN planner throughout
    the SparkLabs game AI ecosystem.

    Returns:
        The singleton HTNPlannerEngine.
    """
    return HTNPlannerEngine.get_instance()