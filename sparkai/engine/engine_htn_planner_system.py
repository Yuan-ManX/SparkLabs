"""
SparkLabs Engine - HTN Planner System

Hierarchical Task Network (HTN) planner for AI decision-making inside the
SparkLabs AI-native game engine. The system lets designers register HTN
domains that describe how high-level compound tasks break down into
primitive actions through prioritized methods guarded by world-state
preconditions. At runtime the planner decomposes a root task into a
concrete sequence of primitive steps, then executes those steps one at a
time while applying their effects back onto the live world state.

Architecture:
  HTNPlannerSystem (singleton)
    |-- TaskType, TaskStatus, MethodStatus, OperatorType,
       ConditionType, PlanStatus, DomainStatus, HTNEventKind
    |-- WorldStateVariable, WorldState, Condition, Operator,
       PrimitiveTask, Method, CompoundTask, PlanStep, Plan,
       Domain, HTNConfig, HTNStats, HTNSnapshot, HTNEvent
    |-- get_htn_planner_system

Core Capabilities:
  - register_domain / remove_domain / get_domain / list_domains
  - register_primitive_task / register_compound_task / remove_task /
    get_task / list_tasks
  - add_method / remove_method / list_methods
  - init_world_state / get_world_state / set_world_state_variable /
    get_world_state_variable / check_condition / apply_operator
  - decompose_task / find_satisfied_method / build_plan / replan
  - start_plan / pause_plan / resume_plan / cancel_plan /
    advance_plan / execute_step
  - get_plan / list_plans / get_plan_status / get_plan_steps
  - tick / get_status / get_stats / get_snapshot / get_config /
    set_config / list_events

HTN Algorithm:
  Decomposition starts at a root task and proceeds recursively. For a
  compound task the planner selects the first method (in priority order)
  whose preconditions are satisfied by the working world state, then
  decomposes each of that method's subtasks in sequence. For a primitive
  task the planner verifies the preconditions, appends a plan step, and
  applies the task's effects to the working world state so that later
  tasks observe the updated state. The working state is a deep copy of
  the live world state, so planning never mutates the actual game state
  until a step is executed.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`HTNPlannerSystem.get_instance` or the module-level
:func:`get_htn_planner_system` factory.
"""

from __future__ import annotations

import copy
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_DOMAINS: int = 500
_MAX_TASKS_PER_DOMAIN: int = 1000
_MAX_METHODS_PER_TASK: int = 200
_MAX_PLANS: int = 5000
_MAX_EVENTS: int = 10000
_MAX_VARIABLES_PER_STATE: int = 500

# Planning safety limits used to prevent runaway recursion.
_DEFAULT_MAX_PLAN_DEPTH: int = 32
_DEFAULT_MAX_PLAN_STEPS: int = 128


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable primitives."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked BEFORE ``to_dict``
    so that dataclasses which also expose ``to_dict`` do not recurse
    through their own serializer.
    """
    if instance is None:
        return {}
    if hasattr(instance, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(instance, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(instance, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(instance, dict):
        return {str(k): _to_jsonable(v) for k, v in instance.items()}
    if hasattr(instance, "to_dict") and callable(instance.to_dict):
        return instance.to_dict()
    return {}


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse a float, returning default on failure or non-finite input."""
    try:
        if value is None:
            return default
        f = float(value)
        if f != f or f in (float("inf"), float("-inf")):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Parse an int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    """Coerce a value into a bool, returning default on failure."""
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "1", "yes", "on"):
            return True
        if low in ("false", "0", "no", "off"):
            return False
    return default


def _compare(value: Any, condition_type: str, expected: Any) -> bool:
    """Evaluate a single condition against a concrete value."""
    ct = str(condition_type)
    if ct == ConditionType.EQUAL.value:
        return value == expected
    if ct == ConditionType.NOT_EQUAL.value:
        return value != expected
    if ct == ConditionType.GREATER.value:
        try:
            return value > expected
        except TypeError:
            return False
    if ct == ConditionType.LESS.value:
        try:
            return value < expected
        except TypeError:
            return False
    if ct == ConditionType.GREATER_EQUAL.value:
        try:
            return value >= expected
        except TypeError:
            return False
    if ct == ConditionType.LESS_EQUAL.value:
        try:
            return value <= expected
        except TypeError:
            return False
    if ct == ConditionType.IS_TRUE.value:
        return bool(value) is True
    if ct == ConditionType.IS_FALSE.value:
        return bool(value) is False
    if ct == ConditionType.IN.value:
        try:
            return value in expected
        except TypeError:
            return False
    if ct == ConditionType.NOT_IN.value:
        try:
            return value not in expected
        except TypeError:
            return True
    return False


def _apply_op(variables: Dict[str, Any], name: str, op_type: str, value: Any) -> Any:
    """Apply an operator to a raw value dict and return the new value."""
    ot = str(op_type)
    if ot == OperatorType.SET.value:
        variables[name] = value
        return value
    if ot == OperatorType.INCREMENT.value:
        current = variables.get(name, 0)
        try:
            result = current + value
        except TypeError:
            result = value
        variables[name] = result
        return result
    if ot == OperatorType.DECREMENT.value:
        current = variables.get(name, 0)
        try:
            result = current - value
        except TypeError:
            result = value
        variables[name] = result
        return result
    if ot == OperatorType.PUSH.value:
        current = variables.get(name, [])
        if not isinstance(current, list):
            current = []
        current = list(current)
        current.append(value)
        variables[name] = current
        return current
    if ot == OperatorType.POP.value:
        current = variables.get(name, [])
        if isinstance(current, list) and current:
            current = list(current)
            current.pop()
            variables[name] = current
        return variables.get(name)
    return variables.get(name)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TaskType(str, Enum):
    """Distinguishes leaf actions from branching task definitions."""

    PRIMITIVE = "primitive"
    COMPOUND = "compound"


class TaskStatus(str, Enum):
    """Lifecycle status of a single plan step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class MethodStatus(str, Enum):
    """Validity of a decomposition method against the world state."""

    VALID = "valid"
    INVALID = "invalid"
    UNKNOWN = "unknown"


class OperatorType(str, Enum):
    """How an effect mutates a world-state variable."""

    SET = "set"
    INCREMENT = "increment"
    DECREMENT = "decrement"
    PUSH = "push"
    POP = "pop"


class ConditionType(str, Enum):
    """Comparison kinds used by task preconditions and method guards."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    IS_TRUE = "is_true"
    IS_FALSE = "is_false"
    IN = "in"
    NOT_IN = "not_in"


class PlanStatus(str, Enum):
    """Lifecycle status of a plan."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class DomainStatus(str, Enum):
    """Load status of a registered HTN domain."""

    LOADED = "loaded"
    UNLOADED = "unloaded"
    ERROR = "error"


class HTNEventKind(str, Enum):
    """Audit event kinds emitted by the planner."""

    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    PLAN_STARTED = "plan_started"
    PLAN_COMPLETED = "plan_completed"
    PLAN_FAILED = "plan_failed"
    METHOD_SELECTED = "method_selected"
    WORLD_STATE_CHANGED = "world_state_changed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class WorldStateVariable:
    """A single typed variable stored inside a world state."""

    name: str
    value: Any = None
    type: str = "any"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WorldState:
    """Collection of world-state variables with condition and operator helpers.

    The planner deep-copies a world state before decomposition so that
    simulated effects never leak into the live game state. Methods on this
    class operate on the ``variables`` dict, which maps variable names to
    their current values.
    """

    variables: Dict[str, Any] = field(default_factory=dict)

    def get(self, name: str, default: Any = None) -> Any:
        """Return the raw value of a variable, or default if absent."""
        return self.variables.get(name, default)

    def set(self, name: str, value: Any, var_type: str = "any") -> None:
        """Set a variable value, creating it if necessary."""
        self.variables[name] = value

    def has(self, name: str) -> bool:
        """Return True when the variable exists in this state."""
        return name in self.variables

    def remove(self, name: str) -> None:
        """Remove a variable if present."""
        self.variables.pop(name, None)

    def check_condition(self, condition: "Condition") -> bool:
        """Evaluate a Condition against this world state."""
        value = self.variables.get(condition.variable_name)
        return _compare(value, condition.condition_type, condition.expected_value)

    def apply_operator(self, operator: "Operator") -> Any:
        """Apply an Operator to this world state and return the new value."""
        return _apply_op(
            self.variables,
            operator.variable_name,
            operator.operator_type,
            operator.value,
        )

    def clone(self) -> "WorldState":
        """Return a deep copy of this world state for simulation."""
        return WorldState(variables=copy.deepcopy(self.variables))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variables": {
                str(k): _to_jsonable(v) for k, v in self.variables.items()
            }
        }


@dataclass
class Condition:
    """A single precondition clause comparing a variable to an expected value."""

    variable_name: str
    condition_type: str = ConditionType.EQUAL.value
    expected_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Operator:
    """A single effect clause that mutates a world-state variable."""

    variable_name: str
    operator_type: str = OperatorType.SET.value
    value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PrimitiveTask:
    """A leaf task that can be executed directly.

    Preconditions must all hold before the task runs. Effects are applied
    to the world state when the task executes (or to a simulated copy
    during planning).
    """

    task_id: str
    name: str
    preconditions: List[Condition] = field(default_factory=list)
    effects: List[Operator] = field(default_factory=list)
    cost: float = 1.0
    execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Method:
    """A decomposition rule for a compound task.

    A method is applicable when every precondition holds against the
    working world state. When selected, the planner decomposes each
    subtask name in order. Higher priority values are tried first.
    """

    method_id: str
    name: str
    task_name: str = ""
    preconditions: List[Condition] = field(default_factory=list)
    subtasks: List[str] = field(default_factory=list)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CompoundTask:
    """A branching task resolved by selecting exactly one of its methods."""

    task_id: str
    name: str
    methods: List[Method] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlanStep:
    """A single primitive action entry inside a plan."""

    step_index: int
    task_id: str
    task_name: str
    task_type: str = TaskType.PRIMITIVE.value
    status: str = TaskStatus.PENDING.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Plan:
    """A fully decomposed sequence of primitive steps for a root task."""

    plan_id: str
    root_task: str
    steps: List[PlanStep] = field(default_factory=list)
    status: str = PlanStatus.IDLE.value
    total_cost: float = 0.0
    created_at: str = field(default_factory=_now)
    # Auxiliary fields used during execution.
    domain_id: str = ""
    current_step: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Domain:
    """A named collection of primitive tasks, compound tasks, and a
    world-state template used to initialize live state for an agent."""

    domain_id: str
    name: str
    primitive_tasks: Dict[str, PrimitiveTask] = field(default_factory=dict)
    compound_tasks: Dict[str, CompoundTask] = field(default_factory=dict)
    world_state_template: WorldState = field(default_factory=WorldState)
    status: str = DomainStatus.LOADED.value
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HTNConfig:
    """Tunable configuration for the HTN planner system."""

    max_plan_depth: int = _DEFAULT_MAX_PLAN_DEPTH
    max_plan_steps: int = _DEFAULT_MAX_PLAN_STEPS
    allow_replan: bool = True
    replan_on_failure: bool = True
    debug_logging: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HTNStats:
    """Roll-up statistics maintained across the system lifetime."""

    total_domains: int = 0
    total_plans: int = 0
    active_plans: int = 0
    completed_plans: int = 0
    failed_plans: int = 0
    total_tasks_executed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HTNSnapshot:
    """A point-in-time snapshot of the full system state."""

    timestamp: str = field(default_factory=_now)
    domains: int = 0
    plans: int = 0
    world_states: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HTNEvent:
    """An internal audit event emitted by the planner."""

    event_id: str
    kind: str
    timestamp: str = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# HTN Planner System
# ---------------------------------------------------------------------------

class HTNPlannerSystem:
    """Hierarchical Task Network planner for AI decision-making.

    The system is thread-safe and implemented as a singleton with
    double-checked locking. ``_init_lock`` guards singleton creation and
    seeding; ``_lock`` guards all mutating operations to keep internal
    dictionaries consistent.
    """

    _instance: Optional["HTNPlannerSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._domains: Dict[str, Domain] = {}
        self._world_states: Dict[str, WorldState] = {}
        self._plans: Dict[str, Plan] = {}
        self._events: List[HTNEvent] = []
        self._config = HTNConfig()
        self._stats = HTNStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._plan_counter: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "HTNPlannerSystem":
        """Return the shared singleton, creating and seeding it if needed."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Discard the current singleton so the next access creates a fresh one."""
        with cls._init_lock:
            cls._instance = None

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Seed the system with canonical domain data if not yet seeded."""
        if self._initialized:
            return
        with self._init_lock:
            if self._initialized:
                return
            self._seed()

    def _seed(self) -> None:
        """Populate the system with three canonical HTN domains."""
        with self._lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # Domain 1: Combat
            # ----------------------------------------------------------
            self._seed_combat_domain()

            # ----------------------------------------------------------
            # Domain 2: Exploration
            # ----------------------------------------------------------
            self._seed_explore_domain()

            # ----------------------------------------------------------
            # Domain 3: Survival
            # ----------------------------------------------------------
            self._seed_survival_domain()

            # ----------------------------------------------------------
            # Seed events
            # ----------------------------------------------------------
            seed_events: List[Tuple[str, Dict[str, Any]]] = [
                (HTNEventKind.PLAN_STARTED.value, {"domain_id": "domain_combat"}),
                (HTNEventKind.METHOD_SELECTED.value, {"domain_id": "domain_combat"}),
                (HTNEventKind.WORLD_STATE_CHANGED.value, {"domain_id": "domain_explore"}),
                (HTNEventKind.TASK_COMPLETED.value, {"domain_id": "domain_survival"}),
            ]
            for kind, payload in seed_events:
                self._emit(kind, payload)

            self._refresh_stats()
            self._initialized = True

    def _seed_combat_domain(self) -> None:
        """Build the combat domain with Behave/Combat compound tasks."""
        domain = Domain(
            domain_id="domain_combat",
            name="Combat Domain",
        )

        # World state template for a combatant agent.
        domain.world_state_template = WorldState(variables={
            "health": 100,
            "enemy_visible": True,
            "enemy_distance": 5,
            "has_weapon": True,
            "is_in_danger": False,
            "target_alive": True,
            "stamina": 50,
            "target_reached": False,
        })

        # Primitive tasks.
        domain.primitive_tasks["MoveTo"] = PrimitiveTask(
            task_id="ptask_combat_moveto",
            name="MoveTo",
            preconditions=[
                Condition("has_weapon", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("enemy_distance", OperatorType.SET.value, 1),
                Operator("target_reached", OperatorType.SET.value, True),
            ],
            cost=2.0,
            execution_time=1.0,
        )
        domain.primitive_tasks["Attack"] = PrimitiveTask(
            task_id="ptask_combat_attack",
            name="Attack",
            preconditions=[
                Condition("target_reached", ConditionType.IS_TRUE.value, True),
                Condition("target_alive", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("target_alive", OperatorType.SET.value, False),
            ],
            cost=3.0,
            execution_time=0.5,
        )
        domain.primitive_tasks["Flee"] = PrimitiveTask(
            task_id="ptask_combat_flee",
            name="Flee",
            preconditions=[
                Condition("is_in_danger", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("is_in_danger", OperatorType.SET.value, False),
                Operator("health", OperatorType.SET.value, 100),
            ],
            cost=5.0,
            execution_time=2.0,
        )
        domain.primitive_tasks["Wait"] = PrimitiveTask(
            task_id="ptask_combat_wait",
            name="Wait",
            preconditions=[],
            effects=[
                Operator("stamina", OperatorType.INCREMENT.value, 10),
            ],
            cost=1.0,
            execution_time=1.0,
        )

        # Compound task: Combat
        combat = CompoundTask(
            task_id="ctask_combat_combat",
            name="Combat",
            methods=[
                Method(
                    method_id="method_combat_approach",
                    name="CombatApproach",
                    task_name="Combat",
                    priority=10,
                    preconditions=[
                        Condition("enemy_visible", ConditionType.IS_TRUE.value, True),
                        Condition("has_weapon", ConditionType.IS_TRUE.value, True),
                        Condition("target_reached", ConditionType.IS_FALSE.value, True),
                    ],
                    subtasks=["MoveTo", "Attack"],
                ),
                Method(
                    method_id="method_combat_direct",
                    name="CombatDirect",
                    task_name="Combat",
                    priority=5,
                    preconditions=[
                        Condition("enemy_visible", ConditionType.IS_TRUE.value, True),
                        Condition("has_weapon", ConditionType.IS_TRUE.value, True),
                        Condition("target_reached", ConditionType.IS_TRUE.value, True),
                    ],
                    subtasks=["Attack"],
                ),
            ],
        )
        domain.compound_tasks["Combat"] = combat

        # Compound task: Behave
        behave = CompoundTask(
            task_id="ctask_combat_behave",
            name="Behave",
            methods=[
                Method(
                    method_id="method_behave_combat",
                    name="BehaveCombat",
                    task_name="Behave",
                    priority=10,
                    preconditions=[
                        Condition("enemy_visible", ConditionType.IS_TRUE.value, True),
                    ],
                    subtasks=["Combat"],
                ),
                Method(
                    method_id="method_behave_flee",
                    name="BehaveFlee",
                    task_name="Behave",
                    priority=5,
                    preconditions=[
                        Condition("is_in_danger", ConditionType.IS_TRUE.value, True),
                    ],
                    subtasks=["Flee"],
                ),
                Method(
                    method_id="method_behave_rest",
                    name="BehaveRest",
                    task_name="Behave",
                    priority=1,
                    preconditions=[],
                    subtasks=["Wait"],
                ),
            ],
        )
        domain.compound_tasks["Behave"] = behave

        self._domains[domain.domain_id] = domain
        self._world_states[domain.domain_id] = domain.world_state_template.clone()

    def _seed_explore_domain(self) -> None:
        """Build the exploration domain with Explore/Gather compound tasks."""
        domain = Domain(
            domain_id="domain_explore",
            name="Exploration Domain",
        )

        domain.world_state_template = WorldState(variables={
            "position_x": 0,
            "position_y": 0,
            "has_key": False,
            "door_locked": True,
            "item_visible": True,
            "inventory_full": False,
            "items_collected": 0,
            "door_open": False,
            "at_door": False,
            "at_item": False,
        })

        # Primitive tasks.
        domain.primitive_tasks["MoveTo"] = PrimitiveTask(
            task_id="ptask_explore_moveto",
            name="MoveTo",
            preconditions=[],
            effects=[
                Operator("at_door", OperatorType.SET.value, True),
                Operator("at_item", OperatorType.SET.value, True),
            ],
            cost=2.0,
            execution_time=1.0,
        )
        domain.primitive_tasks["OpenDoor"] = PrimitiveTask(
            task_id="ptask_explore_opendoor",
            name="OpenDoor",
            preconditions=[
                Condition("door_locked", ConditionType.IS_TRUE.value, True),
                Condition("has_key", ConditionType.IS_TRUE.value, True),
                Condition("at_door", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("door_locked", OperatorType.SET.value, False),
                Operator("door_open", OperatorType.SET.value, True),
            ],
            cost=1.5,
            execution_time=0.5,
        )
        domain.primitive_tasks["PickupItem"] = PrimitiveTask(
            task_id="ptask_explore_pickup",
            name="PickupItem",
            preconditions=[
                Condition("item_visible", ConditionType.IS_TRUE.value, True),
                Condition("inventory_full", ConditionType.IS_FALSE.value, True),
                Condition("at_item", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("items_collected", OperatorType.INCREMENT.value, 1),
                Operator("item_visible", OperatorType.SET.value, False),
            ],
            cost=1.0,
            execution_time=0.5,
        )
        domain.primitive_tasks["Wait"] = PrimitiveTask(
            task_id="ptask_explore_wait",
            name="Wait",
            preconditions=[],
            effects=[
                Operator("position_x", OperatorType.INCREMENT.value, 0),
            ],
            cost=1.0,
            execution_time=1.0,
        )

        # Compound task: Gather
        gather = CompoundTask(
            task_id="ctask_explore_gather",
            name="Gather",
            methods=[
                Method(
                    method_id="method_gather_item",
                    name="GatherItem",
                    task_name="Gather",
                    priority=10,
                    preconditions=[
                        Condition("item_visible", ConditionType.IS_TRUE.value, True),
                        Condition("inventory_full", ConditionType.IS_FALSE.value, True),
                    ],
                    subtasks=["MoveTo", "PickupItem"],
                ),
            ],
        )
        domain.compound_tasks["Gather"] = gather

        # Compound task: Explore
        explore = CompoundTask(
            task_id="ctask_explore_explore",
            name="Explore",
            methods=[
                Method(
                    method_id="method_explore_gather",
                    name="ExploreGather",
                    task_name="Explore",
                    priority=10,
                    preconditions=[
                        Condition("item_visible", ConditionType.IS_TRUE.value, True),
                    ],
                    subtasks=["Gather"],
                ),
                Method(
                    method_id="method_explore_door",
                    name="ExploreDoor",
                    task_name="Explore",
                    priority=5,
                    preconditions=[
                        Condition("door_locked", ConditionType.IS_TRUE.value, True),
                        Condition("has_key", ConditionType.IS_TRUE.value, True),
                    ],
                    subtasks=["MoveTo", "OpenDoor"],
                ),
                Method(
                    method_id="method_explore_wander",
                    name="ExploreWander",
                    task_name="Explore",
                    priority=1,
                    preconditions=[],
                    subtasks=["MoveTo"],
                ),
            ],
        )
        domain.compound_tasks["Explore"] = explore

        self._domains[domain.domain_id] = domain
        self._world_states[domain.domain_id] = domain.world_state_template.clone()

    def _seed_survival_domain(self) -> None:
        """Build the survival domain with a Behave compound task."""
        domain = Domain(
            domain_id="domain_survival",
            name="Survival Domain",
        )

        domain.world_state_template = WorldState(variables={
            "health": 80,
            "stamina": 30,
            "threat_level": 5,
            "has_potion": True,
            "is_safe": False,
            "enemy_nearby": True,
            "position_changed": False,
        })

        # Primitive tasks.
        domain.primitive_tasks["Flee"] = PrimitiveTask(
            task_id="ptask_survival_flee",
            name="Flee",
            preconditions=[
                Condition("enemy_nearby", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("is_safe", OperatorType.SET.value, True),
                Operator("threat_level", OperatorType.SET.value, 0),
                Operator("enemy_nearby", OperatorType.SET.value, False),
            ],
            cost=4.0,
            execution_time=2.0,
        )
        domain.primitive_tasks["Wait"] = PrimitiveTask(
            task_id="ptask_survival_wait",
            name="Wait",
            preconditions=[],
            effects=[
                Operator("stamina", OperatorType.INCREMENT.value, 15),
            ],
            cost=1.0,
            execution_time=1.0,
        )
        domain.primitive_tasks["PickupItem"] = PrimitiveTask(
            task_id="ptask_survival_pickup",
            name="PickupItem",
            preconditions=[
                Condition("has_potion", ConditionType.IS_TRUE.value, True),
            ],
            effects=[
                Operator("has_potion", OperatorType.SET.value, False),
                Operator("health", OperatorType.INCREMENT.value, 20),
            ],
            cost=1.0,
            execution_time=0.5,
        )
        domain.primitive_tasks["MoveTo"] = PrimitiveTask(
            task_id="ptask_survival_moveto",
            name="MoveTo",
            preconditions=[],
            effects=[
                Operator("position_changed", OperatorType.SET.value, True),
            ],
            cost=2.0,
            execution_time=1.0,
        )

        # Compound task: Behave
        behave = CompoundTask(
            task_id="ctask_survival_behave",
            name="Behave",
            methods=[
                Method(
                    method_id="method_survival_flee",
                    name="BehaveSurvive",
                    task_name="Behave",
                    priority=10,
                    preconditions=[
                        Condition("enemy_nearby", ConditionType.IS_TRUE.value, True),
                        Condition("health", ConditionType.LESS.value, 50),
                    ],
                    subtasks=["Flee"],
                ),
                Method(
                    method_id="method_survival_heal",
                    name="BehaveHeal",
                    task_name="Behave",
                    priority=8,
                    preconditions=[
                        Condition("has_potion", ConditionType.IS_TRUE.value, True),
                        Condition("health", ConditionType.LESS.value, 100),
                    ],
                    subtasks=["PickupItem"],
                ),
                Method(
                    method_id="method_survival_rest",
                    name="BehaveRest",
                    task_name="Behave",
                    priority=5,
                    preconditions=[
                        Condition("stamina", ConditionType.LESS.value, 50),
                    ],
                    subtasks=["Wait"],
                ),
                Method(
                    method_id="method_survival_explore",
                    name="BehaveExplore",
                    task_name="Behave",
                    priority=1,
                    preconditions=[],
                    subtasks=["MoveTo"],
                ),
            ],
        )
        domain.compound_tasks["Behave"] = behave

        self._domains[domain.domain_id] = domain
        self._world_states[domain.domain_id] = domain.world_state_template.clone()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        kind: str,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append an audit event and trim the event log to capacity."""
        self._event_counter += 1
        event = HTNEvent(
            event_id=f"htnevt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current stores."""
        self._stats.total_domains = len(self._domains)
        self._stats.total_plans = len(self._plans)
        self._stats.active_plans = sum(
            1 for p in self._plans.values()
            if p.status in (PlanStatus.EXECUTING.value, PlanStatus.PLANNING.value, PlanStatus.PAUSED.value)
        )
        self._stats.completed_plans = sum(
            1 for p in self._plans.values()
            if p.status == PlanStatus.COMPLETED.value
        )
        self._stats.failed_plans = sum(
            1 for p in self._plans.values()
            if p.status == PlanStatus.FAILED.value
        )
        self._stats.total_tasks_executed = self._stats.total_tasks_executed

    def _next_plan_id(self) -> str:
        """Return a monotonically increasing plan identifier."""
        self._plan_counter += 1
        return f"plan_{self._plan_counter:08d}"

    @staticmethod
    def _resolve_task(
        domain: Domain,
        task_name: str,
    ) -> Tuple[Optional[Any], str]:
        """Look up a task by name and return (task_or_None, task_type)."""
        if task_name in domain.primitive_tasks:
            return domain.primitive_tasks[task_name], TaskType.PRIMITIVE.value
        if task_name in domain.compound_tasks:
            return domain.compound_tasks[task_name], TaskType.COMPOUND.value
        return None, ""

    # ------------------------------------------------------------------
    # Domain Management
    # ------------------------------------------------------------------

    def register_domain(
        self,
        domain_id: str,
        name: str,
        world_state_template: Optional[WorldState] = None,
    ) -> Tuple[bool, str, Optional[Domain]]:
        """Register a new HTN domain.

        Returns (success, message, domain_or_None). A fresh world state is
        initialized from the supplied template (or an empty one) so the
        domain is immediately usable for planning.
        """
        with self._lock:
            if not domain_id:
                return False, "domain_id_required", None
            if domain_id in self._domains:
                return False, "already_exists", None
            if len(self._domains) >= _MAX_DOMAINS:
                _evict_fifo_dict(self._domains, _MAX_DOMAINS)

            template = world_state_template if world_state_template is not None else WorldState()
            domain = Domain(
                domain_id=domain_id,
                name=name or domain_id,
                world_state_template=template,
                status=DomainStatus.LOADED.value,
            )
            self._domains[domain_id] = domain
            self._world_states[domain_id] = template.clone()
            self._refresh_stats()
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "domain_id": domain_id,
                "action": "domain_registered",
            })
            return True, "registered", domain

    def remove_domain(self, domain_id: str) -> Tuple[bool, str]:
        """Remove a domain and its associated world state and plans."""
        with self._lock:
            if domain_id not in self._domains:
                return False, "not_found"
            del self._domains[domain_id]
            self._world_states.pop(domain_id, None)
            # Remove plans that belong to this domain.
            stale_ids = [
                pid for pid, plan in self._plans.items()
                if plan.domain_id == domain_id
            ]
            for pid in stale_ids:
                del self._plans[pid]
            self._refresh_stats()
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "domain_id": domain_id,
                "action": "domain_removed",
            })
            return True, "removed"

    def get_domain(self, domain_id: str) -> Optional[Domain]:
        """Return the domain for the given id, or None."""
        with self._lock:
            return self._domains.get(domain_id)

    def list_domains(self) -> List[Domain]:
        """Return all registered domains."""
        with self._lock:
            return list(self._domains.values())

    # ------------------------------------------------------------------
    # Task Management
    # ------------------------------------------------------------------

    def register_primitive_task(
        self,
        domain_id: str,
        task_id: str,
        name: str,
        preconditions: Optional[List[Condition]] = None,
        effects: Optional[List[Operator]] = None,
        cost: float = 1.0,
        execution_time: float = 0.0,
    ) -> Tuple[bool, str, Optional[PrimitiveTask]]:
        """Register a primitive task within a domain."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", None
            if not task_id:
                return False, "task_id_required", None
            key = name or task_id
            if key in domain.primitive_tasks:
                return False, "already_exists", None
            if len(domain.primitive_tasks) >= _MAX_TASKS_PER_DOMAIN:
                return False, "task_limit_reached", None
            task = PrimitiveTask(
                task_id=task_id,
                name=key,
                preconditions=list(preconditions) if preconditions else [],
                effects=list(effects) if effects else [],
                cost=max(0.0, _safe_float(cost, 1.0)),
                execution_time=max(0.0, _safe_float(execution_time, 0.0)),
            )
            domain.primitive_tasks[key] = task
            self._emit(HTNEventKind.TASK_STARTED.value, {
                "domain_id": domain_id,
                "task_name": key,
                "task_type": TaskType.PRIMITIVE.value,
            })
            return True, "registered", task

    def register_compound_task(
        self,
        domain_id: str,
        task_id: str,
        name: str,
        methods: Optional[List[Method]] = None,
    ) -> Tuple[bool, str, Optional[CompoundTask]]:
        """Register a compound task within a domain."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", None
            if not task_id:
                return False, "task_id_required", None
            key = name or task_id
            if key in domain.compound_tasks:
                return False, "already_exists", None
            if len(domain.compound_tasks) >= _MAX_TASKS_PER_DOMAIN:
                return False, "task_limit_reached", None
            task = CompoundTask(
                task_id=task_id,
                name=key,
                methods=list(methods) if methods else [],
            )
            # Ensure each method knows its owning task name.
            for m in task.methods:
                m.task_name = key
            domain.compound_tasks[key] = task
            self._emit(HTNEventKind.TASK_STARTED.value, {
                "domain_id": domain_id,
                "task_name": key,
                "task_type": TaskType.COMPOUND.value,
            })
            return True, "registered", task

    def remove_task(self, domain_id: str, task_name: str) -> Tuple[bool, str]:
        """Remove a primitive or compound task from a domain."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found"
            if task_name in domain.primitive_tasks:
                del domain.primitive_tasks[task_name]
                self._emit(HTNEventKind.TASK_FAILED.value, {
                    "domain_id": domain_id,
                    "task_name": task_name,
                    "action": "removed",
                })
                return True, "removed"
            if task_name in domain.compound_tasks:
                del domain.compound_tasks[task_name]
                self._emit(HTNEventKind.TASK_FAILED.value, {
                    "domain_id": domain_id,
                    "task_name": task_name,
                    "action": "removed",
                })
                return True, "removed"
            return False, "not_found"

    def get_task(
        self,
        domain_id: str,
        task_name: str,
    ) -> Tuple[Optional[Any], str]:
        """Return (task_or_None, task_type) for the named task."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return None, "domain_not_found"
            return self._resolve_task(domain, task_name)

    def list_tasks(
        self,
        domain_id: str,
        task_type: Optional[str] = None,
    ) -> List[Any]:
        """List tasks in a domain, optionally filtered by type."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return []
            tt = str(task_type) if task_type else ""
            out: List[Any] = []
            if tt in ("", TaskType.PRIMITIVE.value):
                out.extend(domain.primitive_tasks.values())
            if tt in ("", TaskType.COMPOUND.value):
                out.extend(domain.compound_tasks.values())
            return out

    # ------------------------------------------------------------------
    # Method Management
    # ------------------------------------------------------------------

    def add_method(
        self,
        domain_id: str,
        task_name: str,
        method_id: str,
        name: str,
        preconditions: Optional[List[Condition]] = None,
        subtasks: Optional[List[str]] = None,
        priority: int = 0,
    ) -> Tuple[bool, str, Optional[Method]]:
        """Add a decomposition method to an existing compound task."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", None
            compound = domain.compound_tasks.get(task_name)
            if compound is None:
                return False, "compound_task_not_found", None
            if not method_id:
                return False, "method_id_required", None
            # Reject duplicate method ids within the same task.
            if any(m.method_id == method_id for m in compound.methods):
                return False, "already_exists", None
            if len(compound.methods) >= _MAX_METHODS_PER_TASK:
                return False, "method_limit_reached", None
            method = Method(
                method_id=method_id,
                name=name or method_id,
                task_name=task_name,
                preconditions=list(preconditions) if preconditions else [],
                subtasks=list(subtasks) if subtasks else [],
                priority=_safe_int(priority, 0),
            )
            compound.methods.append(method)
            # Keep methods sorted by descending priority so the planner can
            # iterate in selection order without re-sorting each call.
            compound.methods.sort(key=lambda m: m.priority, reverse=True)
            self._emit(HTNEventKind.METHOD_SELECTED.value, {
                "domain_id": domain_id,
                "task_name": task_name,
                "method_id": method_id,
                "action": "added",
            })
            return True, "added", method

    def remove_method(
        self,
        domain_id: str,
        task_name: str,
        method_id: str,
    ) -> Tuple[bool, str]:
        """Remove a method from a compound task."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found"
            compound = domain.compound_tasks.get(task_name)
            if compound is None:
                return False, "compound_task_not_found"
            before = len(compound.methods)
            compound.methods = [
                m for m in compound.methods if m.method_id != method_id
            ]
            if len(compound.methods) == before:
                return False, "not_found"
            self._emit(HTNEventKind.METHOD_SELECTED.value, {
                "domain_id": domain_id,
                "task_name": task_name,
                "method_id": method_id,
                "action": "removed",
            })
            return True, "removed"

    def list_methods(
        self,
        domain_id: str,
        task_name: str,
    ) -> List[Method]:
        """Return all methods for a compound task in priority order."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return []
            compound = domain.compound_tasks.get(task_name)
            if compound is None:
                return []
            return list(compound.methods)

    # ------------------------------------------------------------------
    # World State Management
    # ------------------------------------------------------------------

    def init_world_state(
        self,
        domain_id: str,
        template: Optional[WorldState] = None,
    ) -> Tuple[bool, str, Optional[WorldState]]:
        """Initialize (or reset) the live world state for a domain."""
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", None
            source = template if template is not None else domain.world_state_template
            state = source.clone()
            self._world_states[domain_id] = state
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "domain_id": domain_id,
                "action": "init",
            })
            return True, "initialized", state

    def get_world_state(self, domain_id: str) -> Optional[WorldState]:
        """Return the live world state for a domain, or None."""
        with self._lock:
            return self._world_states.get(domain_id)

    def set_world_state_variable(
        self,
        domain_id: str,
        name: str,
        value: Any,
    ) -> Tuple[bool, str, Optional[WorldStateVariable]]:
        """Set a single variable on the live world state."""
        with self._lock:
            state = self._world_states.get(domain_id)
            if state is None:
                return False, "domain_not_found", None
            if not name:
                return False, "variable_name_required", None
            if len(state.variables) >= _MAX_VARIABLES_PER_STATE and name not in state.variables:
                return False, "variable_limit_reached", None
            state.set(name, value)
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "domain_id": domain_id,
                "variable": name,
                "value": _to_jsonable(value),
            })
            return True, "set", WorldStateVariable(name=name, value=value)

    def get_world_state_variable(
        self,
        domain_id: str,
        name: str,
    ) -> Optional[WorldStateVariable]:
        """Return a single variable from the live world state."""
        with self._lock:
            state = self._world_states.get(domain_id)
            if state is None:
                return None
            if not state.has(name):
                return None
            return WorldStateVariable(name=name, value=state.get(name))

    def check_condition(
        self,
        domain_id: str,
        condition: Condition,
    ) -> bool:
        """Evaluate a Condition against the live world state of a domain."""
        with self._lock:
            state = self._world_states.get(domain_id)
            if state is None:
                return False
            return state.check_condition(condition)

    def apply_operator(
        self,
        domain_id: str,
        operator: Operator,
    ) -> Tuple[bool, str, Optional[WorldStateVariable]]:
        """Apply an Operator directly to the live world state."""
        with self._lock:
            state = self._world_states.get(domain_id)
            if state is None:
                return False, "domain_not_found", None
            new_value = state.apply_operator(operator)
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "domain_id": domain_id,
                "variable": operator.variable_name,
                "operator": operator.operator_type,
                "value": _to_jsonable(new_value),
            })
            return True, "applied", WorldStateVariable(
                name=operator.variable_name,
                value=new_value,
            )

    # ------------------------------------------------------------------
    # Planning
    # ------------------------------------------------------------------

    def find_satisfied_method(
        self,
        compound_task: CompoundTask,
        world_state: WorldState,
    ) -> Optional[Method]:
        """Return the first method whose preconditions hold.

        Methods are expected to be stored in descending priority order;
        the first match wins.
        """
        for method in compound_task.methods:
            all_hold = True
            for cond in method.preconditions:
                if not world_state.check_condition(cond):
                    all_hold = False
                    break
            if all_hold:
                return method
        return None

    def decompose_task(
        self,
        domain_id: str,
        task_name: str,
        world_state: WorldState,
        depth: int = 0,
    ) -> Tuple[bool, str, List[PlanStep]]:
        """Recursively decompose a task into primitive plan steps.

        The supplied ``world_state`` is mutated in place to reflect
        simulated effects so that downstream subtasks observe the updated
        state. Callers should pass a clone of the live state.
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", []
            max_depth = max(1, int(self._config.max_plan_depth))
            if depth > max_depth:
                return False, "max_depth_exceeded", []

            task, task_type = self._resolve_task(domain, task_name)
            if task is None:
                return False, "task_not_found", []

            steps: List[PlanStep] = []

            if task_type == TaskType.PRIMITIVE.value:
                primitive: PrimitiveTask = task
                # Verify all preconditions against the working state.
                for cond in primitive.preconditions:
                    if not world_state.check_condition(cond):
                        return False, "precondition_failed", []
                step = PlanStep(
                    step_index=0,
                    task_id=primitive.task_id,
                    task_name=primitive.name,
                    task_type=TaskType.PRIMITIVE.value,
                    status=TaskStatus.PENDING.value,
                )
                steps.append(step)
                # Apply simulated effects so later tasks see the change.
                for op in primitive.effects:
                    world_state.apply_operator(op)
                return True, "ok", steps

            # Compound task: select a method and decompose its subtasks.
            compound: CompoundTask = task
            method = self.find_satisfied_method(compound, world_state)
            if method is None:
                return False, "no_valid_method", []
            self._emit(HTNEventKind.METHOD_SELECTED.value, {
                "domain_id": domain_id,
                "task_name": task_name,
                "method_id": method.method_id,
                "method_name": method.name,
            })
            for subtask_name in method.subtasks:
                ok, msg, substeps = self.decompose_task(
                    domain_id, subtask_name, world_state, depth + 1,
                )
                if not ok:
                    return False, msg, []
                steps.extend(substeps)
            return True, "ok", steps

    def build_plan(
        self,
        domain_id: str,
        root_task: str,
    ) -> Tuple[bool, str, Optional[Plan]]:
        """Decompose a root task into an executable plan.

        A deep copy of the live world state is used for simulation so the
        actual game state is not modified. Returns the plan on success.
        """
        with self._lock:
            domain = self._domains.get(domain_id)
            if domain is None:
                return False, "domain_not_found", None
            live_state = self._world_states.get(domain_id)
            if live_state is None:
                return False, "world_state_not_found", None

            sim_state = live_state.clone()
            ok, msg, steps = self.decompose_task(
                domain_id, root_task, sim_state, 0,
            )
            if not ok:
                return False, msg, None

            max_steps = max(1, int(self._config.max_plan_steps))
            if len(steps) > max_steps:
                return False, "max_steps_exceeded", None

            # Re-index steps sequentially and compute total cost.
            total_cost = 0.0
            for i, step in enumerate(steps):
                step.step_index = i
                step.status = TaskStatus.PENDING.value
                primitive = domain.primitive_tasks.get(step.task_name)
                if primitive is not None:
                    total_cost += primitive.cost

            plan = Plan(
                plan_id=self._next_plan_id(),
                root_task=root_task,
                steps=steps,
                status=PlanStatus.IDLE.value,
                total_cost=total_cost,
                created_at=_now(),
                domain_id=domain_id,
                current_step=0,
            )
            self._plans[plan.plan_id] = plan
            _evict_fifo_dict(self._plans, _MAX_PLANS)
            self._refresh_stats()
            self._emit(HTNEventKind.PLAN_STARTED.value, {
                "plan_id": plan.plan_id,
                "domain_id": domain_id,
                "root_task": root_task,
                "steps": len(steps),
                "total_cost": total_cost,
            })
            return True, "ok", plan

    def replan(self, plan_id: str) -> Tuple[bool, str, Optional[Plan]]:
        """Rebuild a plan from its root task using the current world state.

        The original plan is replaced by the new plan. If the system
        disallows replanning, the call fails without changes.
        """
        with self._lock:
            if not self._config.allow_replan:
                return False, "replan_disabled", None
            old_plan = self._plans.get(plan_id)
            if old_plan is None:
                return False, "plan_not_found", None
            domain_id = old_plan.domain_id
            root_task = old_plan.root_task
            # Build a fresh plan.
            ok, msg, new_plan = self.build_plan(domain_id, root_task)
            if not ok or new_plan is None:
                return False, msg, None
            # Remove the old plan and carry over the plan id so callers
            # can keep using the same handle.
            del self._plans[new_plan.plan_id]
            new_plan.plan_id = plan_id
            self._plans[plan_id] = new_plan
            self._refresh_stats()
            self._emit(HTNEventKind.PLAN_STARTED.value, {
                "plan_id": plan_id,
                "domain_id": domain_id,
                "root_task": root_task,
                "action": "replan",
            })
            return True, "replanned", new_plan

    # ------------------------------------------------------------------
    # Plan Execution
    # ------------------------------------------------------------------

    def start_plan(
        self,
        domain_id: str,
        root_task: str,
    ) -> Tuple[bool, str, Optional[Plan]]:
        """Build a plan and immediately transition it to EXECUTING."""
        with self._lock:
            ok, msg, plan = self.build_plan(domain_id, root_task)
            if not ok or plan is None:
                return False, msg, None
            if not plan.steps:
                plan.status = PlanStatus.COMPLETED.value
                self._emit(HTNEventKind.PLAN_COMPLETED.value, {
                    "plan_id": plan.plan_id,
                    "reason": "empty_plan",
                })
                self._refresh_stats()
                return True, "completed", plan
            plan.status = PlanStatus.EXECUTING.value
            self._emit(HTNEventKind.PLAN_STARTED.value, {
                "plan_id": plan.plan_id,
                "domain_id": domain_id,
                "root_task": root_task,
                "action": "start",
            })
            self._refresh_stats()
            return True, "started", plan

    def pause_plan(self, plan_id: str) -> Tuple[bool, str, Optional[Plan]]:
        """Pause an executing plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False, "plan_not_found", None
            if plan.status != PlanStatus.EXECUTING.value:
                return False, "not_executing", plan
            plan.status = PlanStatus.PAUSED.value
            self._refresh_stats()
            return True, "paused", plan

    def resume_plan(self, plan_id: str) -> Tuple[bool, str, Optional[Plan]]:
        """Resume a paused plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False, "plan_not_found", None
            if plan.status != PlanStatus.PAUSED.value:
                return False, "not_paused", plan
            plan.status = PlanStatus.EXECUTING.value
            self._refresh_stats()
            return True, "resumed", plan

    def cancel_plan(self, plan_id: str) -> Tuple[bool, str]:
        """Cancel a plan, marking any pending steps as failed."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False, "plan_not_found"
            plan.status = PlanStatus.FAILED.value
            for step in plan.steps:
                if step.status == TaskStatus.PENDING.value:
                    step.status = TaskStatus.FAILURE.value
            self._emit(HTNEventKind.PLAN_FAILED.value, {
                "plan_id": plan_id,
                "action": "cancelled",
            })
            self._refresh_stats()
            return True, "cancelled"

    def advance_plan(self, plan_id: str) -> Tuple[bool, str, Optional[Plan]]:
        """Execute the next pending step of a plan.

        If the step succeeds and it was the final step, the plan is
        marked COMPLETED. If the step fails and replan-on-failure is
        enabled, the system attempts a single replan; otherwise the
        plan is marked FAILED.
        """
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False, "plan_not_found", None
            if plan.status not in (PlanStatus.EXECUTING.value, PlanStatus.PLANNING.value):
                return False, f"plan_not_executable:{plan.status}", plan

            # Find the next pending step.
            next_index = plan.current_step
            if next_index >= len(plan.steps):
                plan.status = PlanStatus.COMPLETED.value
                self._emit(HTNEventKind.PLAN_COMPLETED.value, {
                    "plan_id": plan_id,
                })
                self._refresh_stats()
                return True, "completed", plan

            ok, msg, step = self._execute_step_internal(plan, next_index)
            if ok:
                plan.current_step = next_index + 1
                if plan.current_step >= len(plan.steps):
                    plan.status = PlanStatus.COMPLETED.value
                    self._emit(HTNEventKind.PLAN_COMPLETED.value, {
                        "plan_id": plan_id,
                    })
                self._refresh_stats()
                return True, "advanced", plan

            # Step failed.
            if self._config.replan_on_failure and self._config.allow_replan:
                ok2, msg2, new_plan = self.replan(plan_id)
                if ok2 and new_plan is not None:
                    new_plan.status = PlanStatus.EXECUTING.value
                    self._refresh_stats()
                    return True, "replanned", new_plan

            plan.status = PlanStatus.FAILED.value
            self._emit(HTNEventKind.PLAN_FAILED.value, {
                "plan_id": plan_id,
                "reason": msg,
            })
            self._refresh_stats()
            return False, msg, plan

    def execute_step(
        self,
        plan_id: str,
        step_index: int,
    ) -> Tuple[bool, str, Optional[PlanStep]]:
        """Execute a specific step by index within a plan."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return False, "plan_not_found", None
            if step_index < 0 or step_index >= len(plan.steps):
                return False, "step_out_of_range", None
            ok, msg, step = self._execute_step_internal(plan, step_index)
            return ok, msg, step

    def _execute_step_internal(
        self,
        plan: Plan,
        step_index: int,
    ) -> Tuple[bool, str, Optional[PlanStep]]:
        """Apply the effects of a step to the live world state.

        This helper assumes the caller already holds ``self._lock``.
        """
        step = plan.steps[step_index]
        domain = self._domains.get(plan.domain_id)
        if domain is None:
            step.status = TaskStatus.FAILURE.value
            return False, "domain_not_found", step
        primitive = domain.primitive_tasks.get(step.task_name)
        if primitive is None:
            step.status = TaskStatus.FAILURE.value
            return False, "primitive_task_not_found", step

        state = self._world_states.get(plan.domain_id)
        if state is None:
            step.status = TaskStatus.FAILURE.value
            return False, "world_state_not_found", step

        # Re-check preconditions against the live state before applying.
        for cond in primitive.preconditions:
            if not state.check_condition(cond):
                step.status = TaskStatus.FAILURE.value
                self._emit(HTNEventKind.TASK_FAILED.value, {
                    "plan_id": plan.plan_id,
                    "step_index": step_index,
                    "task_name": step.task_name,
                    "reason": "precondition_failed",
                })
                return False, "precondition_failed", step

        # Mark running, then apply effects, then mark success.
        step.status = TaskStatus.RUNNING.value
        self._emit(HTNEventKind.TASK_STARTED.value, {
            "plan_id": plan.plan_id,
            "step_index": step_index,
            "task_name": step.task_name,
        })
        for op in primitive.effects:
            state.apply_operator(op)
        step.status = TaskStatus.SUCCESS.value
        self._stats.total_tasks_executed += 1
        self._emit(HTNEventKind.TASK_COMPLETED.value, {
            "plan_id": plan.plan_id,
            "step_index": step_index,
            "task_name": step.task_name,
        })
        self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
            "domain_id": plan.domain_id,
            "task_name": step.task_name,
            "action": "effects_applied",
        })
        return True, "executed", step

    # ------------------------------------------------------------------
    # Plan Queries
    # ------------------------------------------------------------------

    def get_plan(self, plan_id: str) -> Optional[Plan]:
        """Return a plan by id, or None."""
        with self._lock:
            return self._plans.get(plan_id)

    def list_plans(self, domain_id: Optional[str] = None) -> List[Plan]:
        """Return all plans, optionally filtered by domain."""
        with self._lock:
            if domain_id is None:
                return list(self._plans.values())
            return [
                p for p in self._plans.values()
                if p.domain_id == domain_id
            ]

    def get_plan_status(self, plan_id: str) -> Optional[str]:
        """Return the status string of a plan, or None if not found."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return None
            return plan.status

    def get_plan_steps(self, plan_id: str) -> List[PlanStep]:
        """Return the step list of a plan, or empty list if not found."""
        with self._lock:
            plan = self._plans.get(plan_id)
            if plan is None:
                return []
            return list(plan.steps)

    # ------------------------------------------------------------------
    # System Operations
    # ------------------------------------------------------------------

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the simulation by one tick.

        Every executing plan has its next pending step executed. Plans
        that complete or fail are transitioned accordingly.
        """
        with self._lock:
            self._tick_count += 1
            step = max(0.0, _safe_float(dt, 0.016))
            advanced: List[str] = []
            completed: List[str] = []
            failed: List[str] = []

            # Snapshot plan ids to avoid mutating while iterating.
            plan_ids = [
                pid for pid, p in self._plans.items()
                if p.status == PlanStatus.EXECUTING.value
            ]
            for pid in plan_ids:
                ok, msg, plan = self.advance_plan(pid)
                if ok:
                    if plan is not None and plan.status == PlanStatus.COMPLETED.value:
                        completed.append(pid)
                    else:
                        advanced.append(pid)
                else:
                    failed.append(pid)

            self._refresh_stats()
            return {
                "status": "ok",
                "tick": self._tick_count,
                "dt": step,
                "advanced": advanced,
                "completed": completed,
                "failed": failed,
                "active_plans": self._stats.active_plans,
                "stats": self._stats.to_dict(),
            }

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "domains": len(self._domains),
                "plans": len(self._plans),
                "world_states": len(self._world_states),
                "events": len(self._events),
                "tick_count": self._tick_count,
                "active_plans": sum(
                    1 for p in self._plans.values()
                    if p.status == PlanStatus.EXECUTING.value
                ),
                "completed_plans": sum(
                    1 for p in self._plans.values()
                    if p.status == PlanStatus.COMPLETED.value
                ),
            }

    def get_stats(self) -> HTNStats:
        """Return aggregate statistics."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> HTNSnapshot:
        """Return a point-in-time snapshot of the system."""
        with self._lock:
            self._refresh_stats()
            recent_events = [e.to_dict() for e in self._events[-20:]]
            return HTNSnapshot(
                timestamp=_now(),
                domains=len(self._domains),
                plans=len(self._plans),
                world_states=len(self._world_states),
                events=recent_events,
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> HTNConfig:
        """Return the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, HTNConfig]:
        """Update tunable configuration fields by keyword."""
        with self._lock:
            known = set(self._config.__dataclass_fields__.keys())
            applied: List[str] = []
            for key, value in kwargs.items():
                if key not in known:
                    continue
                if key in ("max_plan_depth", "max_plan_steps"):
                    setattr(self._config, key, max(1, _safe_int(value, getattr(self._config, key))))
                elif key in ("allow_replan", "replan_on_failure", "debug_logging"):
                    setattr(self._config, key, _safe_bool(value, getattr(self._config, key)))
                else:
                    continue
                applied.append(key)
            if not applied:
                return False, "no_valid_config_fields_supplied", self._config
            self._emit(HTNEventKind.WORLD_STATE_CHANGED.value, {
                "action": "config_updated",
                "fields": applied,
            })
            return True, "updated", self._config

    def list_events(self, limit: Optional[int] = None) -> List[HTNEvent]:
        """Return recent events, optionally capped to a limit."""
        with self._lock:
            if limit is None:
                return list(self._events)
            n = max(0, _safe_int(limit, 0))
            if n == 0:
                return []
            return list(self._events[-n:])

    def reset(self) -> None:
        """Clear all system state and re-seed the canonical dataset."""
        with self._lock:
            self._domains.clear()
            self._world_states.clear()
            self._plans.clear()
            self._events.clear()
            self._config = HTNConfig()
            self._stats = HTNStats()
            self._tick_count = 0
            self._event_counter = 0
            self._plan_counter = 0
            self._initialized = False
            self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_htn_planner_system() -> HTNPlannerSystem:
    """Return the shared HTNPlannerSystem singleton instance."""
    return HTNPlannerSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "TaskType",
    "TaskStatus",
    "MethodStatus",
    "OperatorType",
    "ConditionType",
    "PlanStatus",
    "DomainStatus",
    "HTNEventKind",
    # Data classes
    "WorldStateVariable",
    "WorldState",
    "Condition",
    "Operator",
    "PrimitiveTask",
    "Method",
    "CompoundTask",
    "PlanStep",
    "Plan",
    "Domain",
    "HTNConfig",
    "HTNStats",
    "HTNSnapshot",
    "HTNEvent",
    # System
    "HTNPlannerSystem",
    "get_htn_planner_system",
]
