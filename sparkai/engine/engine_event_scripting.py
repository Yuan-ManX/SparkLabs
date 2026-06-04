"""
SparkLabs Engine - Visual Event Scripting System

Visual event scripting system for authoring game logic through declarative
event sheets composed of conditions and actions. Creators define event-driven
behavior by assembling condition→action pairs into named sheets that the
runtime evaluates against live game state each tick.

Architecture:
  EngineEventScripting
    |-- EventSheet (named collection of event definitions with metadata)
    |-- EventCondition (evaluable predicate with operators and sub-conditions)
    |-- EventAction (executable operation with parameters and ordering)
    |-- EventLink (inter-sheet linking for composition and inheritance)
    |-- EventVariable (scoped variable with type, default, and runtime value)

Sheet Features:
  - DECLARATIVE: events defined by condition→action rule pairs
  - HIERARCHICAL: sub-conditions and sub-actions for nested logic
  - LINKED: sheets can include, reference, inherit, extend, or override
  - COMPILABLE: sheets compile to Python, JavaScript, or Lua source code
  - IMPORT/EXPORT: JSON serialization for sheet portability

Usage:
    es = get_engine_event_scripting()
    sheet = es.create_event_sheet("gameplay_core", "Core gameplay logic")
    event_id = es.add_event_to_sheet(sheet.sheet_id, conditions, actions, "on_start")
    es.execute_sheet(sheet.sheet_id, {"player_x": 0, "player_y": 0})
"""

from __future__ import annotations

import copy
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


# ---------------------------------------------------------------------------
# Helper: unique ID stub
# ---------------------------------------------------------------------------


def _generate_uid_stub() -> str:
    """Generate a unique identifier for event scripting entities."""
    return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class ConditionType(Enum):
    """Types of conditions that can be evaluated against game state."""
    OBJECT_COLLISION = "object_collision"
    OBJECT_POSITION = "object_position"
    VARIABLE_COMPARISON = "variable_comparison"
    TIMER = "timer"
    INPUT = "input"
    SCENE_LOADED = "scene_loaded"
    TRIGGER_ZONE = "trigger_zone"
    ANIMATION_FINISHED = "animation_finished"
    NETWORK_EVENT = "network_event"
    CUSTOM = "custom"


class ActionType(Enum):
    """Types of actions that can be dispatched by event rules."""
    CREATE_OBJECT = "create_object"
    DELETE_OBJECT = "delete_object"
    MOVE_OBJECT = "move_object"
    CHANGE_VARIABLE = "change_variable"
    PLAY_ANIMATION = "play_animation"
    PLAY_SOUND = "play_sound"
    CHANGE_SCENE = "change_scene"
    APPLY_FORCE = "apply_force"
    TRIGGER_EVENT = "trigger_event"
    SPAWN_PARTICLE = "spawn_particle"
    MODIFY_PROPERTY = "modify_property"
    EXECUTE_SCRIPT = "execute_script"
    WAIT = "wait"
    CALL_FUNCTION = "call_function"
    SEND_MESSAGE = "send_message"
    CUSTOM = "custom"


class OperatorType(Enum):
    """Comparison operators for condition evaluation."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    GREATER_EQUAL = "greater_equal"
    LESS = "less"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    BETWEEN = "between"
    IN_RANGE = "in_range"
    IS_NULL = "is_null"
    IS_NOT_NULL = "is_not_null"


class VariableScope(Enum):
    """Scope at which an event variable is defined and accessible."""
    GLOBAL = "global"
    SCENE = "scene"
    OBJECT = "object"
    LOCAL = "local"
    TEMPORARY = "temporary"


class LinkType(Enum):
    """Types of relationships between event sheets."""
    INCLUDE = "include"
    REFERENCE = "reference"
    INHERIT = "inherit"
    EXTEND = "extend"
    OVERRIDE = "override"


# ---------------------------------------------------------------------------
# Operator Function Map
# ---------------------------------------------------------------------------

_OPERATOR_FUNCTIONS = {
    OperatorType.EQUAL: lambda a, b: a == b,
    OperatorType.NOT_EQUAL: lambda a, b: a != b,
    OperatorType.GREATER: lambda a, b: float(a) > float(b),
    OperatorType.GREATER_EQUAL: lambda a, b: float(a) >= float(b),
    OperatorType.LESS: lambda a, b: float(a) < float(b),
    OperatorType.LESS_EQUAL: lambda a, b: float(a) <= float(b),
    OperatorType.CONTAINS: lambda a, b: str(b) in str(a) if a is not None else False,
    OperatorType.STARTS_WITH: lambda a, b: str(a).startswith(str(b)) if a is not None else False,
    OperatorType.ENDS_WITH: lambda a, b: str(a).endswith(str(b)) if a is not None else False,
    OperatorType.BETWEEN: lambda a, b: (b[0] <= a <= b[1]) if isinstance(b, (list, tuple)) and len(b) >= 2 else False,
    OperatorType.IN_RANGE: lambda a, b: (b[0] <= a <= b[1]) if isinstance(b, (list, tuple)) and len(b) >= 2 else False,
    OperatorType.IS_NULL: lambda a, b: a is None,
    OperatorType.IS_NOT_NULL: lambda a, b: a is not None,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class EventCondition:
    """Evaluable condition that tests a property or variable against a value."""

    condition_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    condition_type: ConditionType = ConditionType.CUSTOM
    target_object: str = ""
    property: str = ""
    operator: OperatorType = OperatorType.EQUAL
    value: Any = None
    sub_conditions: List[EventCondition] = field(default_factory=list)
    logic_operator: str = "and"
    invert: bool = False
    is_template: bool = False
    category: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "name": self.name,
            "condition_type": self.condition_type.value,
            "target_object": self.target_object,
            "property": self.property,
            "operator": self.operator.value,
            "value": self.value,
            "sub_conditions": [sc.to_dict() for sc in self.sub_conditions],
            "logic_operator": self.logic_operator,
            "invert": self.invert,
            "is_template": self.is_template,
            "category": self.category,
            "description": self.description,
        }


@dataclass
class EventAction:
    """Executable operation dispatched when a condition set is satisfied."""

    action_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    action_type: ActionType = ActionType.CUSTOM
    target_object: str = ""
    method: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    sub_actions: List[EventAction] = field(default_factory=list)
    execution_order: int = 0
    is_async: bool = False
    timeout: float = 0.0
    error_behavior: str = "ignore"
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "action_type": self.action_type.value,
            "target_object": self.target_object,
            "method": self.method,
            "parameters": dict(self.parameters),
            "sub_actions": [sa.to_dict() for sa in self.sub_actions],
            "execution_order": self.execution_order,
            "is_async": self.is_async,
            "timeout": self.timeout,
            "error_behavior": self.error_behavior,
            "description": self.description,
        }


@dataclass
class EventSheet:
    """Named collection of event definitions with scope and metadata."""

    sheet_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    description: str = ""
    events: List[Dict[str, Any]] = field(default_factory=list)
    is_active: bool = True
    is_global: bool = False
    linked_objects: List[str] = field(default_factory=list)
    priority: int = 0
    execution_order: int = 0
    category: str = ""
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    compiled_code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "name": self.name,
            "description": self.description,
            "event_count": len(self.events),
            "is_active": self.is_active,
            "is_global": self.is_global,
            "linked_objects": list(self.linked_objects),
            "priority": self.priority,
            "execution_order": self.execution_order,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "compiled_code": self.compiled_code,
        }


@dataclass
class EventLink:
    """Directed relationship between two event sheets."""

    link_id: str = field(default_factory=_generate_uid_stub)
    source_sheet_id: str = ""
    target_sheet_id: str = ""
    link_type: LinkType = LinkType.INCLUDE
    condition: str = ""
    is_active: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "link_id": self.link_id,
            "source_sheet_id": self.source_sheet_id,
            "target_sheet_id": self.target_sheet_id,
            "link_type": self.link_type.value,
            "condition": self.condition,
            "is_active": self.is_active,
            "description": self.description,
        }


@dataclass
class EventVariable:
    """Scoped variable definition with type, default, and runtime value."""

    variable_id: str = field(default_factory=_generate_uid_stub)
    name: str = ""
    variable_type: str = "any"
    scope: VariableScope = VariableScope.LOCAL
    initial_value: Any = None
    current_value: Any = None
    is_system: bool = False
    is_readonly: bool = False
    description: str = ""
    group_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "variable_id": self.variable_id,
            "name": self.name,
            "variable_type": self.variable_type,
            "scope": self.scope.value,
            "initial_value": self.initial_value,
            "current_value": self.current_value,
            "is_system": self.is_system,
            "is_readonly": self.is_readonly,
            "description": self.description,
            "group_name": self.group_name,
        }


# ---------------------------------------------------------------------------
# EngineEventScripting (Singleton)
# ---------------------------------------------------------------------------


class EngineEventScripting:
    """Visual event scripting runtime for declarative game logic authoring.

    Manages creation, evaluation, and execution of event sheets composed of
    condition→action rule pairs. Supports hierarchical sub-conditions and
    sub-actions, inter-sheet linking, code compilation, and JSON import/export.

    Usage:
        es = EngineEventScripting.get_instance()
        sheet = es.create_event_sheet("core_logic", "Core gameplay events")
        cond = es.create_condition(sheet.sheet_id, "check_position",
                                    ConditionType.OBJECT_POSITION,
                                    "player", "x", OperatorType.GREATER, 100)
        act = es.create_action(sheet.sheet_id, None, "move_camera",
                                ActionType.MOVE_OBJECT, "camera",
                                parameters={"x": 200, "y": 0})
        es.add_event_to_sheet(sheet.sheet_id, [cond], [act], "follow_player")
    """

    _instance: Optional["EngineEventScripting"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SHEETS = 512
    MAX_EVENTS_PER_SHEET = 256
    MAX_CONDITIONS_PER_EVENT = 64
    MAX_ACTIONS_PER_EVENT = 128
    MAX_LINKS = 1024
    MAX_VARIABLES = 4096
    MAX_SUB_CONDITION_DEPTH = 8
    MAX_SUB_ACTION_DEPTH = 8

    def __new__(cls) -> "EngineEventScripting":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._sheets: Dict[str, EventSheet] = {}
        self._conditions: Dict[str, EventCondition] = {}
        self._actions: Dict[str, EventAction] = {}
        self._links: Dict[str, EventLink] = {}
        self._variables: Dict[str, EventVariable] = {}
        self._event_index: Dict[str, Dict[str, Any]] = {}
        self._execution_count: int = 0
        self._total_execution_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "EngineEventScripting":
        """Thread-safe singleton accessor with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Event Sheet Management
    # ------------------------------------------------------------------

    def create_event_sheet(
        self,
        name: str,
        description: str = "",
        is_global: bool = False,
        linked_objects: Optional[List[str]] = None,
        priority: int = 0,
    ) -> Optional[EventSheet]:
        """Create a new event sheet for organizing event definitions.

        Args:
            name: Human-readable name for the sheet.
            description: Optional description of the sheet's purpose.
            is_global: Whether the sheet applies globally across scenes.
            linked_objects: Object IDs this sheet is bound to.
            priority: Execution priority (higher runs first).

        Returns:
            The created EventSheet, or None if the sheet limit is reached.
        """
        if len(self._sheets) >= self.MAX_SHEETS:
            return None
        now = _time_module.time()
        sheet = EventSheet(
            name=name,
            description=description,
            is_global=is_global,
            linked_objects=linked_objects or [],
            priority=priority,
            created_at=now,
            updated_at=now,
        )
        self._sheets[sheet.sheet_id] = sheet
        return sheet

    def get_event_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        """Retrieve an event sheet by its identifier."""
        return self._sheets.get(sheet_id)

    def list_event_sheets(self, active_only: bool = False) -> List[EventSheet]:
        """List all event sheets, optionally filtering to active only."""
        sheets = list(self._sheets.values())
        if active_only:
            sheets = [s for s in sheets if s.is_active]
        return sorted(sheets, key=lambda s: (-s.priority, s.execution_order))

    def remove_event_sheet(self, sheet_id: str) -> bool:
        """Remove an event sheet and all its associated events."""
        sheet = self._sheets.pop(sheet_id, None)
        if sheet is None:
            return False
        for event_data in sheet.events:
            eid = event_data.get("event_id", "")
            self._event_index.pop(eid, None)
            for cond in event_data.get("conditions", []):
                cid = cond.condition_id if hasattr(cond, "condition_id") else cond.get("condition_id", "")
                self._conditions.pop(cid, None)
            for act in event_data.get("actions", []):
                aid = act.action_id if hasattr(act, "action_id") else act.get("action_id", "")
                self._actions.pop(aid, None)
        links_to_remove = [
            lid for lid, link in self._links.items()
            if link.source_sheet_id == sheet_id or link.target_sheet_id == sheet_id
        ]
        for lid in links_to_remove:
            self._links.pop(lid, None)
        return True

    def set_sheet_active(self, sheet_id: str, active: bool) -> bool:
        """Enable or disable an event sheet."""
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return False
        sheet.is_active = active
        sheet.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Condition Management
    # ------------------------------------------------------------------

    def create_condition(
        self,
        sheet_id: str,
        name: str = "",
        condition_type: ConditionType = ConditionType.CUSTOM,
        target_object: str = "",
        property: str = "",
        operator: OperatorType = OperatorType.EQUAL,
        value: Any = None,
        sub_conditions: Optional[List[EventCondition]] = None,
        logic_operator: str = "and",
    ) -> Optional[EventCondition]:
        """Create a new condition for use in event rules.

        Args:
            sheet_id: The sheet this condition belongs to.
            name: Human-readable name for the condition.
            condition_type: The type of condition to evaluate.
            target_object: The target object or variable to test.
            property: The property path on the target to evaluate.
            operator: The comparison operator.
            value: The expected value to compare against.
            sub_conditions: Nested sub-conditions for compound logic.
            logic_operator: Logic operator for sub-conditions ("and" or "or").

        Returns:
            The created EventCondition, or None if the sheet is not found.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        condition = EventCondition(
            name=name,
            condition_type=condition_type,
            target_object=target_object,
            property=property,
            operator=operator,
            value=value,
            sub_conditions=sub_conditions or [],
            logic_operator=logic_operator,
        )
        self._conditions[condition.condition_id] = condition
        return condition

    def get_condition(self, condition_id: str) -> Optional[EventCondition]:
        """Retrieve a condition by its identifier."""
        return self._conditions.get(condition_id)

    def remove_condition(self, condition_id: str) -> bool:
        """Remove a condition from the system."""
        if condition_id not in self._conditions:
            return False
        del self._conditions[condition_id]
        for sheet in self._sheets.values():
            for event_data in sheet.events:
                conds = event_data.get("conditions", [])
                for i, c in enumerate(conds):
                    cid = c.condition_id if hasattr(c, "condition_id") else c.get("condition_id", "")
                    if cid == condition_id:
                        conds.pop(i)
                        sheet.updated_at = _time_module.time()
                        return True
        return False

    # ------------------------------------------------------------------
    # Action Management
    # ------------------------------------------------------------------

    def create_action(
        self,
        sheet_id: str,
        event_id: Optional[str] = None,
        name: str = "",
        action_type: ActionType = ActionType.CUSTOM,
        target_object: str = "",
        method: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        sub_actions: Optional[List[EventAction]] = None,
        is_async: bool = False,
    ) -> Optional[EventAction]:
        """Create a new action for use in event rules.

        Args:
            sheet_id: The sheet this action belongs to.
            event_id: Optional event to attach the action to directly.
            name: Human-readable name for the action.
            action_type: The type of action to dispatch.
            target_object: The target object for the action.
            method: The method or function to invoke.
            parameters: Key-value parameters for the action.
            sub_actions: Nested sub-actions for sequential execution.
            is_async: Whether the action runs asynchronously.

        Returns:
            The created EventAction, or None if the sheet is not found.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        action = EventAction(
            name=name,
            action_type=action_type,
            target_object=target_object,
            method=method,
            parameters=parameters or {},
            sub_actions=sub_actions or [],
            is_async=is_async,
        )
        self._actions[action.action_id] = action
        if event_id:
            for event_data in sheet.events:
                if event_data.get("event_id") == event_id:
                    actions = event_data.setdefault("actions", [])
                    action.execution_order = len(actions)
                    actions.append(action)
                    sheet.updated_at = _time_module.time()
                    break
        return action

    def get_action(self, action_id: str) -> Optional[EventAction]:
        """Retrieve an action by its identifier."""
        return self._actions.get(action_id)

    def remove_action(self, action_id: str) -> bool:
        """Remove an action from the system."""
        if action_id not in self._actions:
            return False
        del self._actions[action_id]
        for sheet in self._sheets.values():
            for event_data in sheet.events:
                acts = event_data.get("actions", [])
                for i, a in enumerate(acts):
                    aid = a.action_id if hasattr(a, "action_id") else a.get("action_id", "")
                    if aid == action_id:
                        acts.pop(i)
                        sheet.updated_at = _time_module.time()
                        return True
        return False

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def add_event_to_sheet(
        self,
        sheet_id: str,
        conditions: Optional[List[EventCondition]] = None,
        actions: Optional[List[EventAction]] = None,
        name: str = "",
    ) -> str:
        """Add a new event rule to a sheet, composed of conditions and actions.

        Args:
            sheet_id: The target event sheet.
            conditions: List of conditions that must be met.
            actions: List of actions to execute when conditions are met.
            name: Optional name for the event.

        Returns:
            The generated event_id string, or empty string on failure.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return ""
        if len(sheet.events) >= self.MAX_EVENTS_PER_SHEET:
            return ""
        event_id = _generate_uid_stub()
        condition_list = conditions or []
        action_list = actions or []
        event_data: Dict[str, Any] = {
            "event_id": event_id,
            "name": name,
            "conditions": condition_list,
            "actions": action_list,
        }
        sheet.events.append(event_data)
        sheet.updated_at = _time_module.time()
        self._event_index[event_id] = event_data
        for cond in condition_list:
            if cond.condition_id not in self._conditions:
                self._conditions[cond.condition_id] = cond
        for act in action_list:
            if act.action_id not in self._actions:
                self._actions[act.action_id] = act
        return event_id

    def remove_event_from_sheet(self, sheet_id: str, event_id: str) -> bool:
        """Remove an event from a sheet by its event identifier.

        Args:
            sheet_id: The sheet containing the event.
            event_id: The event to remove.

        Returns:
            True if the event was found and removed, False otherwise.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return False
        for i, event_data in enumerate(sheet.events):
            if event_data.get("event_id") == event_id:
                for cond in event_data.get("conditions", []):
                    cid = cond.condition_id if hasattr(cond, "condition_id") else cond.get("condition_id", "")
                    self._conditions.pop(cid, None)
                for act in event_data.get("actions", []):
                    aid = act.action_id if hasattr(act, "action_id") else act.get("action_id", "")
                    self._actions.pop(aid, None)
                sheet.events.pop(i)
                sheet.updated_at = _time_module.time()
                self._event_index.pop(event_id, None)
                return True
        return False

    def get_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an event definition by its identifier."""
        return self._event_index.get(event_id)

    # ------------------------------------------------------------------
    # Variable Management
    # ------------------------------------------------------------------

    def create_variable(
        self,
        name: str,
        variable_type: str = "any",
        scope: VariableScope = VariableScope.LOCAL,
        initial_value: Any = None,
        description: str = "",
        group_name: str = "",
    ) -> Optional[EventVariable]:
        """Create a scoped event variable.

        Args:
            name: Unique name for the variable.
            variable_type: Type hint for the variable (e.g. "int", "float", "string").
            scope: The visibility scope of the variable.
            initial_value: The default/initial value.
            description: Optional description of the variable's purpose.
            group_name: Optional group name for organization.

        Returns:
            The created EventVariable, or None if the limit is reached.
        """
        if len(self._variables) >= self.MAX_VARIABLES:
            return None
        variable = EventVariable(
            name=name,
            variable_type=variable_type,
            scope=scope,
            initial_value=initial_value,
            current_value=initial_value,
            is_system=False,
            is_readonly=False,
            description=description,
            group_name=group_name,
        )
        self._variables[variable.variable_id] = variable
        return variable

    def set_variable(self, variable_id: str, value: Any) -> bool:
        """Set the runtime value of an event variable.

        Args:
            variable_id: The variable to update.
            value: The new value to assign.

        Returns:
            True if the variable was found and updated, False otherwise.
        """
        variable = self._variables.get(variable_id)
        if variable is None:
            return False
        if variable.is_readonly:
            return False
        variable.current_value = value
        return True

    def get_variable(self, variable_id: str) -> Any:
        """Retrieve the current value of an event variable.

        Args:
            variable_id: The variable to read.

        Returns:
            The current value of the variable, or None if not found.
        """
        variable = self._variables.get(variable_id)
        if variable is None:
            return None
        return variable.current_value

    def get_variable_by_name(self, name: str, scope: Optional[VariableScope] = None) -> Optional[EventVariable]:
        """Find a variable by name, optionally filtering by scope."""
        for var in self._variables.values():
            if var.name == name:
                if scope is None or var.scope == scope:
                    return var
        return None

    def list_variables(self, scope: Optional[VariableScope] = None) -> List[EventVariable]:
        """List all variables, optionally filtered by scope."""
        if scope is None:
            return list(self._variables.values())
        return [v for v in self._variables.values() if v.scope == scope]

    def remove_variable(self, variable_id: str) -> bool:
        """Remove an event variable by its identifier."""
        if variable_id not in self._variables:
            return False
        del self._variables[variable_id]
        return True

    # ------------------------------------------------------------------
    # Condition Evaluation
    # ------------------------------------------------------------------

    def evaluate_condition(
        self,
        condition_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Evaluate a single condition against the provided context.

        Args:
            condition_id: The condition to evaluate.
            context: Game state context providing property values.

        Returns:
            True if the condition passes, False otherwise.
        """
        condition = self._conditions.get(condition_id)
        if condition is None:
            return False
        return self._evaluate_single_condition(condition, context or {})

    def _evaluate_single_condition(
        self,
        condition: EventCondition,
        context: Dict[str, Any],
        depth: int = 0,
    ) -> bool:
        """Recursively evaluate a condition and its sub-conditions."""
        if depth >= self.MAX_SUB_CONDITION_DEPTH:
            return False

        raw_result = self._evaluate_condition_primitive(condition, context)

        if condition.sub_conditions:
            sub_results = [
                self._evaluate_single_condition(sc, context, depth + 1)
                for sc in condition.sub_conditions
            ]
            if condition.logic_operator == "or":
                raw_result = raw_result or any(sub_results)
            else:
                raw_result = raw_result and all(sub_results)

        if condition.invert:
            raw_result = not raw_result

        return raw_result

    def _evaluate_condition_primitive(
        self,
        condition: EventCondition,
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate the base condition without considering sub-conditions or invert."""
        ct = condition.condition_type
        target = condition.target_object
        prop = condition.property
        op = condition.operator
        expected = condition.value

        if ct == ConditionType.OBJECT_COLLISION:
            collisions = context.get("collisions", [])
            pair = tuple(sorted([target, prop])) if target and prop else None
            if pair:
                return pair in [tuple(sorted(p)) for p in collisions] if collisions else False
            return any(target in str(p) for p in collisions)

        if ct == ConditionType.OBJECT_POSITION:
            objects = context.get("objects", {})
            obj = objects.get(target, {})
            actual = obj.get(prop, 0)
            return self._apply_operator(actual, op, expected)

        if ct == ConditionType.VARIABLE_COMPARISON:
            variables = context.get("variables", {})
            actual = variables.get(target)
            if actual is None:
                for var in self._variables.values():
                    if var.name == target:
                        actual = var.current_value
                        break
            return self._apply_operator(actual, op, expected)

        if ct == ConditionType.TIMER:
            timers = context.get("timers", {})
            timer = timers.get(target, {})
            elapsed = timer.get("elapsed", 0.0)
            interval = timer.get("interval", 0.0)
            if interval <= 0:
                return False
            return elapsed >= interval

        if ct == ConditionType.INPUT:
            inputs = context.get("inputs", {})
            key = target if target else prop
            return inputs.get(key, False)

        if ct == ConditionType.SCENE_LOADED:
            current_scene = context.get("scene", "")
            return current_scene == target

        if ct == ConditionType.TRIGGER_ZONE:
            zones = context.get("trigger_zones", {})
            zone = zones.get(target, {})
            objects_inside = zone.get("objects_inside", [])
            return prop in objects_inside

        if ct == ConditionType.ANIMATION_FINISHED:
            animations = context.get("animations", {})
            anim = animations.get(target)
            if anim is None:
                return False
            return anim.get("ended", False)

        if ct == ConditionType.NETWORK_EVENT:
            network_events = context.get("network_events", [])
            return any(
                e.get("type") == target and e.get("data", {}).get(prop) == expected
                for e in network_events
            )

        if ct == ConditionType.CUSTOM:
            custom_evaluators = context.get("_custom_evaluators", {})
            evaluator = custom_evaluators.get(target)
            if callable(evaluator):
                return bool(evaluator(context))
            return True

        return False

    def _apply_operator(self, actual: Any, operator: OperatorType, expected: Any) -> bool:
        """Apply an operator comparison between actual and expected values."""
        func = _OPERATOR_FUNCTIONS.get(operator)
        if func is None:
            return False
        try:
            if operator in (OperatorType.IS_NULL, OperatorType.IS_NOT_NULL):
                return func(actual, None)
            return func(actual, expected)
        except (ValueError, TypeError):
            return False

    # ------------------------------------------------------------------
    # Action Execution
    # ------------------------------------------------------------------

    def execute_action(
        self,
        action_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single action against the provided context.

        Args:
            action_id: The action to execute.
            context: Game state context for parameter resolution.

        Returns:
            Dictionary with result, output, and errors keys.
        """
        action = self._actions.get(action_id)
        if action is None:
            return {"result": False, "output": None, "errors": ["Action not found"]}
        return self._dispatch_single_action(action, context or {})

    def _dispatch_single_action(
        self,
        action: EventAction,
        context: Dict[str, Any],
        depth: int = 0,
    ) -> Dict[str, Any]:
        """Recursively dispatch an action and its sub-actions."""
        if depth >= self.MAX_SUB_ACTION_DEPTH:
            return {"result": False, "output": None, "errors": ["Max sub-action depth exceeded"]}

        errors: List[str] = []
        output: Any = None
        result = True

        try:
            output = self._execute_action_primitive(action, context)
        except Exception as exc:
            errors.append(f"Action '{action.name}' error: {exc}")
            result = False
            if action.error_behavior == "abort":
                return {"result": False, "output": None, "errors": errors}

        for sub_action in action.sub_actions:
            sub_result = self._dispatch_single_action(sub_action, context, depth + 1)
            if not sub_result["result"]:
                errors.extend(sub_result.get("errors", []))
                if action.error_behavior == "abort":
                    break

        return {
            "result": result and len(errors) == 0,
            "output": output,
            "errors": errors,
        }

    def _execute_action_primitive(
        self,
        action: EventAction,
        context: Dict[str, Any],
    ) -> Any:
        """Execute the base action without considering sub-actions."""
        at = action.action_type
        target = action.target_object
        params = dict(action.parameters)

        for key, val in params.items():
            if isinstance(val, str) and val.startswith("$"):
                var_name = val[1:]
                for var in self._variables.values():
                    if var.name == var_name:
                        params[key] = var.current_value
                        break
                else:
                    params[key] = context.get(var_name, val)

        if at == ActionType.CREATE_OBJECT:
            created = {
                "template": params.get("template", target),
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "created": True,
            }
            context.setdefault("created_objects", []).append(created)
            return created

        if at == ActionType.DELETE_OBJECT:
            context.setdefault("deleted_objects", []).append(target)
            return {"deleted": target}

        if at == ActionType.MOVE_OBJECT:
            return {
                "target": target,
                "dx": params.get("dx", 0),
                "dy": params.get("dy", 0),
            }

        if at == ActionType.CHANGE_VARIABLE:
            var_name = target if target else params.get("variable", "")
            value = params.get("value")
            operation = params.get("operation", "set")
            for var in self._variables.values():
                if var.name == var_name:
                    if var.is_readonly:
                        return {"variable": var_name, "changed": False, "reason": "readonly"}
                    if operation == "set":
                        var.current_value = value
                    elif operation == "add":
                        var.current_value = (var.current_value or 0) + value
                    elif operation == "subtract":
                        var.current_value = (var.current_value or 0) - value
                    elif operation == "toggle":
                        var.current_value = not var.current_value
                    return {"variable": var_name, "changed": True, "new_value": var.current_value}
            context.setdefault("variables", {})[var_name] = value
            return {"variable": var_name, "changed": True, "new_value": value}

        if at == ActionType.PLAY_ANIMATION:
            return {
                "target": target,
                "animation": params.get("animation", "default"),
                "loop": params.get("loop", False),
            }

        if at == ActionType.PLAY_SOUND:
            return {
                "sound": target if target else params.get("sound", ""),
                "volume": params.get("volume", 1.0),
                "pitch": params.get("pitch", 1.0),
            }

        if at == ActionType.CHANGE_SCENE:
            return {"scene": target if target else params.get("scene", "")}

        if at == ActionType.APPLY_FORCE:
            return {
                "target": target,
                "fx": params.get("fx", 0),
                "fy": params.get("fy", 0),
            }

        if at == ActionType.TRIGGER_EVENT:
            triggered_event_id = target if target else params.get("event_id", "")
            if triggered_event_id:
                return self.execute_event(triggered_event_id, context)
            return {"triggered": False}

        if at == ActionType.SPAWN_PARTICLE:
            return {
                "effect": params.get("effect", target),
                "x": params.get("x", 0),
                "y": params.get("y", 0),
                "count": params.get("count", 10),
            }

        if at == ActionType.MODIFY_PROPERTY:
            return {
                "target": target,
                "property": params.get("property", action.method),
                "value": params.get("value"),
            }

        if at == ActionType.EXECUTE_SCRIPT:
            return {"script": params.get("script", action.method), "executed": True}

        if at == ActionType.WAIT:
            duration = params.get("duration", 0.0)
            return {"waited": duration}

        if at == ActionType.CALL_FUNCTION:
            return {
                "function": action.method,
                "parameters": params,
                "called": True,
            }

        if at == ActionType.SEND_MESSAGE:
            return {
                "message": params.get("message", action.method),
                "recipient": target,
                "sent": True,
            }

        if at == ActionType.CUSTOM:
            custom_handlers = context.get("_custom_handlers", {})
            handler = custom_handlers.get(target)
            if callable(handler):
                return handler(context, params)
            return {"custom": True}

        return None

    # ------------------------------------------------------------------
    # Event Execution
    # ------------------------------------------------------------------

    def execute_event(
        self,
        event_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a single event by evaluating its conditions and dispatching actions.

        Args:
            event_id: The event to execute.
            context: Game state context.

        Returns:
            Dictionary with executed, triggered, and errors keys.
        """
        ctx = context or {}
        event_data = self._event_index.get(event_id)
        if event_data is None:
            return {"executed": False, "triggered": False, "errors": ["Event not found"]}

        conditions = event_data.get("conditions", [])
        actions = event_data.get("actions", [])

        conditions_met = True
        for cond in conditions:
            cond_id = cond.condition_id if hasattr(cond, "condition_id") else cond.get("condition_id", "")
            if not self.evaluate_condition(cond_id, ctx):
                conditions_met = False
                break

        if not conditions_met:
            return {"executed": False, "triggered": False, "errors": []}

        errors: List[str] = []
        action_results: List[Dict[str, Any]] = []
        for act in actions:
            act_id = act.action_id if hasattr(act, "action_id") else act.get("action_id", "")
            result = self.execute_action(act_id, ctx)
            action_results.append(result)
            if not result["result"]:
                errors.extend(result.get("errors", []))

        return {
            "executed": True,
            "triggered": True,
            "action_results": action_results,
            "errors": errors,
        }

    def execute_sheet(
        self,
        sheet_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute all events in a sheet against the provided context.

        Args:
            sheet_id: The sheet to execute.
            context: Game state context.

        Returns:
            Dictionary with total_events, executed, triggered, errors, duration.
        """
        ctx = context or {}
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return {
                "total_events": 0,
                "executed": 0,
                "triggered": 0,
                "errors": ["Sheet not found"],
                "duration": 0.0,
            }

        if not sheet.is_active:
            return {
                "total_events": 0,
                "executed": 0,
                "triggered": 0,
                "errors": [],
                "duration": 0.0,
            }

        start_time = _time_module.time()
        total_events = len(sheet.events)
        executed = 0
        triggered = 0
        all_errors: List[str] = []

        for event_data in sheet.events:
            executed += 1
            event_id = event_data.get("event_id", "")
            result = self.execute_event(event_id, ctx)
            if result["triggered"]:
                triggered += 1
            all_errors.extend(result.get("errors", []))

        elapsed = _time_module.time() - start_time
        self._execution_count += 1
        self._total_execution_time += elapsed

        return {
            "total_events": total_events,
            "executed": executed,
            "triggered": triggered,
            "errors": all_errors,
            "duration": elapsed,
        }

    # ------------------------------------------------------------------
    # Code Compilation
    # ------------------------------------------------------------------

    def compile_sheet_to_code(
        self,
        sheet_id: str,
        target_language: str = "python",
    ) -> str:
        """Compile an event sheet into executable source code.

        Args:
            sheet_id: The sheet to compile.
            target_language: One of "python", "javascript", or "lua".

        Returns:
            Source code string in the target language, or empty string on failure.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return ""

        target_language = target_language.lower()
        if target_language == "python":
            compiled = self._compile_to_python(sheet)
        elif target_language == "javascript":
            compiled = self._compile_to_javascript(sheet)
        elif target_language == "lua":
            compiled = self._compile_to_lua(sheet)
        else:
            return ""

        sheet.compiled_code = compiled
        sheet.updated_at = _time_module.time()
        return compiled

    def _compile_to_python(self, sheet: EventSheet) -> str:
        """Compile a sheet to Python source code."""
        lines: List[str] = [
            f"# Auto-generated event sheet: {sheet.name}",
            f"# Description: {sheet.description}",
            "",
            "def execute_event_sheet(context):",
            "    triggered = []",
            "    errors = []",
            "",
        ]
        for event_data in sheet.events:
            event_name = event_data.get("name", "unnamed")
            conditions = event_data.get("conditions", [])
            actions = event_data.get("actions", [])

            cond_exprs: List[str] = []
            for cond in conditions:
                target = cond.target_object if hasattr(cond, "target_object") else ""
                prop = cond.property if hasattr(cond, "property") else ""
                op = cond.operator if hasattr(cond, "operator") else ""
                val = cond.value if hasattr(cond, "value") else None
                op_str = "=" * 2 if str(op) == "equal" else "!" + "=" if str(op) == "not_equal" else str(op)
                cond_exprs.append(f"context.get('{target}', {{}}).get('{prop}') {op_str} {repr(val)}")

            lines.append(f"    # Event: {event_name}")
            if cond_exprs:
                lines.append(f"    if {' and '.join(cond_exprs)}:")
                indent = "        "
            else:
                indent = "    "

            for act in actions:
                act_type = act.action_type if hasattr(act, "action_type") else ""
                target = act.target_object if hasattr(act, "target_object") else ""
                lines.append(f"{indent}# Action: {act_type} on {target}")
                lines.append(f"{indent}triggered.append('{act_type}')")

            lines.append("")
            if cond_exprs:
                lines.append("")

        lines.append("    return {'triggered': len(triggered), 'errors': errors}")
        return "\n".join(lines)

    def _compile_to_javascript(self, sheet: EventSheet) -> str:
        """Compile a sheet to JavaScript source code."""
        lines: List[str] = [
            f"// Auto-generated event sheet: {sheet.name}",
            f"// Description: {sheet.description}",
            "",
            "function executeEventSheet(context) {",
            "    const triggered = [];",
            "    const errors = [];",
            "",
        ]
        for event_data in sheet.events:
            event_name = event_data.get("name", "unnamed")
            conditions = event_data.get("conditions", [])
            actions = event_data.get("actions", [])

            cond_exprs: List[str] = []
            for cond in conditions:
                target = cond.target_object if hasattr(cond, "target_object") else ""
                prop = cond.property if hasattr(cond, "property") else ""
                op = cond.operator if hasattr(cond, "operator") else ""
                val = cond.value if hasattr(cond, "value") else None
                op_str = "===" if str(op) == "equal" else "!==" if str(op) == "not_equal" else str(op)
                cond_exprs.append(f"context?.{target}?.{prop} {op_str} {json.dumps(val)}")

            lines.append(f"    // Event: {event_name}")
            if cond_exprs:
                lines.append(f"    if ({' && '.join(cond_exprs)}) {{")
                indent = "        "
            else:
                indent = "    "

            for act in actions:
                act_type = act.action_type if hasattr(act, "action_type") else ""
                lines.append(f"{indent}// Action: {act_type}")
                lines.append(f"{indent}triggered.push('{act_type}');")

            if cond_exprs:
                lines.append("    }")
            lines.append("")

        lines.append("    return { triggered: triggered.length, errors };")
        lines.append("}")
        return "\n".join(lines)

    def _compile_to_lua(self, sheet: EventSheet) -> str:
        """Compile a sheet to Lua source code."""
        lines: List[str] = [
            f"-- Auto-generated event sheet: {sheet.name}",
            f"-- Description: {sheet.description}",
            "",
            "function execute_event_sheet(context)",
            "    local triggered = {}",
            "    local errors = {}",
            "",
        ]
        for event_data in sheet.events:
            event_name = event_data.get("name", "unnamed")
            conditions = event_data.get("conditions", [])
            actions = event_data.get("actions", [])

            cond_exprs: List[str] = []
            for cond in conditions:
                target = cond.target_object if hasattr(cond, "target_object") else ""
                prop = cond.property if hasattr(cond, "property") else ""
                op = cond.operator if hasattr(cond, "operator") else ""
                cond_exprs.append(f"context['{target}']['{prop}'] {str(op)} {repr(getattr(cond, 'value', None))}")

            lines.append(f"    -- Event: {event_name}")
            if cond_exprs:
                lines.append(f"    if {' and '.join(cond_exprs)} then")
                indent = "        "
            else:
                indent = "    "

            for act in actions:
                act_type = act.action_type if hasattr(act, "action_type") else ""
                lines.append(f"{indent}-- Action: {act_type}")
                lines.append(f"{indent}table.insert(triggered, '{act_type}')")

            if cond_exprs:
                lines.append("    end")
            lines.append("")

        lines.append("    return { triggered = #triggered, errors = errors }")
        lines.append("end")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Sheet Linking
    # ------------------------------------------------------------------

    def create_link(
        self,
        source_sheet_id: str,
        target_sheet_id: str,
        link_type: LinkType = LinkType.INCLUDE,
        condition: str = "",
    ) -> Optional[EventLink]:
        """Create a link between two event sheets.

        Args:
            source_sheet_id: The source sheet that references another.
            target_sheet_id: The target sheet being referenced.
            link_type: The type of relationship.
            condition: Optional condition expression for conditional linking.

        Returns:
            The created EventLink, or None if sheets are not found or limit reached.
        """
        if len(self._links) >= self.MAX_LINKS:
            return None
        if source_sheet_id not in self._sheets:
            return None
        if target_sheet_id not in self._sheets:
            return None
        if source_sheet_id == target_sheet_id:
            return None
        link = EventLink(
            source_sheet_id=source_sheet_id,
            target_sheet_id=target_sheet_id,
            link_type=link_type,
            condition=condition,
        )
        self._links[link.link_id] = link
        return link

    def get_link(self, link_id: str) -> Optional[EventLink]:
        """Retrieve a link by its identifier."""
        return self._links.get(link_id)

    def get_links_for_sheet(self, sheet_id: str) -> List[EventLink]:
        """Get all links where the sheet is the source."""
        return [l for l in self._links.values() if l.source_sheet_id == sheet_id]

    def remove_link(self, link_id: str) -> bool:
        """Remove a link by its identifier."""
        if link_id not in self._links:
            return False
        del self._links[link_id]
        return True

    # ------------------------------------------------------------------
    # Sheet Cloning
    # ------------------------------------------------------------------

    def clone_sheet(
        self,
        sheet_id: str,
        new_name: str,
    ) -> Optional[EventSheet]:
        """Create a deep copy of an event sheet with a new name.

        Args:
            sheet_id: The sheet to clone.
            new_name: The name for the cloned sheet.

        Returns:
            The cloned EventSheet, or None if source not found or limit reached.
        """
        source = self._sheets.get(sheet_id)
        if source is None:
            return None
        if len(self._sheets) >= self.MAX_SHEETS:
            return None

        now = _time_module.time()
        cloned = EventSheet(
            name=new_name,
            description=f"Clone of: {source.description}",
            is_active=source.is_active,
            is_global=source.is_global,
            linked_objects=list(source.linked_objects),
            priority=source.priority,
            execution_order=source.execution_order,
            category=source.category,
            created_at=now,
            updated_at=now,
        )
        self._sheets[cloned.sheet_id] = cloned

        for event_data in source.events:
            new_conditions: List[EventCondition] = []
            new_actions: List[EventAction] = []
            name = event_data.get("name", "")

            for cond in event_data.get("conditions", []):
                new_cond = EventCondition(
                    name=getattr(cond, "name", ""),
                    condition_type=getattr(cond, "condition_type", ConditionType.CUSTOM),
                    target_object=getattr(cond, "target_object", ""),
                    property=getattr(cond, "property", ""),
                    operator=getattr(cond, "operator", OperatorType.EQUAL),
                    value=getattr(cond, "value", None),
                    sub_conditions=list(getattr(cond, "sub_conditions", [])),
                    logic_operator=getattr(cond, "logic_operator", "and"),
                    invert=getattr(cond, "invert", False),
                    is_template=getattr(cond, "is_template", False),
                    category=getattr(cond, "category", ""),
                    description=getattr(cond, "description", ""),
                )
                self._conditions[new_cond.condition_id] = new_cond
                new_conditions.append(new_cond)

            for act in event_data.get("actions", []):
                new_act = EventAction(
                    name=getattr(act, "name", ""),
                    action_type=getattr(act, "action_type", ActionType.CUSTOM),
                    target_object=getattr(act, "target_object", ""),
                    method=getattr(act, "method", ""),
                    parameters=dict(getattr(act, "parameters", {})),
                    sub_actions=list(getattr(act, "sub_actions", [])),
                    is_async=getattr(act, "is_async", False),
                    timeout=getattr(act, "timeout", 0.0),
                    error_behavior=getattr(act, "error_behavior", "ignore"),
                    description=getattr(act, "description", ""),
                )
                self._actions[new_act.action_id] = new_act
                new_actions.append(new_act)

            new_event_id = _generate_uid_stub()
            new_event_data: Dict[str, Any] = {
                "event_id": new_event_id,
                "name": name,
                "conditions": new_conditions,
                "actions": new_actions,
            }
            cloned.events.append(new_event_data)
            self._event_index[new_event_id] = new_event_data

        return cloned

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def import_sheet_from_json(
        self,
        json_data: Dict[str, Any],
    ) -> Optional[EventSheet]:
        """Create an event sheet from serialized JSON data.

        Args:
            json_data: Dictionary with sheet, events, variables, and links data.

        Returns:
            The imported EventSheet, or None if import fails or limit reached.
        """
        if len(self._sheets) >= self.MAX_SHEETS:
            return None

        sheet_data = json_data.get("sheet", {})
        now = _time_module.time()
        sheet = EventSheet(
            name=sheet_data.get("name", "Imported Sheet"),
            description=sheet_data.get("description", ""),
            is_global=sheet_data.get("is_global", False),
            linked_objects=sheet_data.get("linked_objects", []),
            priority=sheet_data.get("priority", 0),
            execution_order=sheet_data.get("execution_order", 0),
            category=sheet_data.get("category", ""),
            created_at=now,
            updated_at=now,
        )
        self._sheets[sheet.sheet_id] = sheet

        for event_entry in json_data.get("events", []):
            conditions: List[EventCondition] = []
            actions: List[EventAction] = []

            for cond_data in event_entry.get("conditions", []):
                try:
                    ct = ConditionType(cond_data.get("condition_type", "custom"))
                except ValueError:
                    ct = ConditionType.CUSTOM
                try:
                    op = OperatorType(cond_data.get("operator", "equal"))
                except ValueError:
                    op = OperatorType.EQUAL
                cond = EventCondition(
                    name=cond_data.get("name", ""),
                    condition_type=ct,
                    target_object=cond_data.get("target_object", ""),
                    property=cond_data.get("property", ""),
                    operator=op,
                    value=cond_data.get("value"),
                    logic_operator=cond_data.get("logic_operator", "and"),
                    invert=cond_data.get("invert", False),
                    is_template=cond_data.get("is_template", False),
                    category=cond_data.get("category", ""),
                    description=cond_data.get("description", ""),
                )
                self._conditions[cond.condition_id] = cond
                conditions.append(cond)

            for act_data in event_entry.get("actions", []):
                try:
                    at = ActionType(act_data.get("action_type", "custom"))
                except ValueError:
                    at = ActionType.CUSTOM
                act = EventAction(
                    name=act_data.get("name", ""),
                    action_type=at,
                    target_object=act_data.get("target_object", ""),
                    method=act_data.get("method", ""),
                    parameters=act_data.get("parameters", {}),
                    is_async=act_data.get("is_async", False),
                    timeout=act_data.get("timeout", 0.0),
                    error_behavior=act_data.get("error_behavior", "ignore"),
                    description=act_data.get("description", ""),
                )
                self._actions[act.action_id] = act
                actions.append(act)

            event_id = event_entry.get("event_id", _generate_uid_stub())
            event_data: Dict[str, Any] = {
                "event_id": event_id,
                "name": event_entry.get("name", ""),
                "conditions": conditions,
                "actions": actions,
            }
            sheet.events.append(event_data)
            self._event_index[event_id] = event_data

        for var_data in json_data.get("variables", []):
            try:
                scope = VariableScope(var_data.get("scope", "local"))
            except ValueError:
                scope = VariableScope.LOCAL
            variable = EventVariable(
                name=var_data.get("name", ""),
                variable_type=var_data.get("variable_type", "any"),
                scope=scope,
                initial_value=var_data.get("initial_value"),
                current_value=var_data.get("current_value"),
                is_system=var_data.get("is_system", False),
                is_readonly=var_data.get("is_readonly", False),
                description=var_data.get("description", ""),
                group_name=var_data.get("group_name", ""),
            )
            self._variables[variable.variable_id] = variable

        for link_data in json_data.get("links", []):
            try:
                lt = LinkType(link_data.get("link_type", "include"))
            except ValueError:
                lt = LinkType.INCLUDE
            link = EventLink(
                source_sheet_id=link_data.get("source_sheet_id", ""),
                target_sheet_id=link_data.get("target_sheet_id", ""),
                link_type=lt,
                condition=link_data.get("condition", ""),
                description=link_data.get("description", ""),
            )
            self._links[link.link_id] = link

        return sheet

    def export_sheet_to_json(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        """Export an event sheet to a serializable dictionary.

        Args:
            sheet_id: The sheet to export.

        Returns:
            Dictionary with all sheet data, or None if not found.
        """
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None

        events_data: List[Dict[str, Any]] = []
        for event_data in sheet.events:
            conditions_list: List[Dict[str, Any]] = []
            for cond in event_data.get("conditions", []):
                conditions_list.append(cond.to_dict() if hasattr(cond, "to_dict") else cond)
            actions_list: List[Dict[str, Any]] = []
            for act in event_data.get("actions", []):
                actions_list.append(act.to_dict() if hasattr(act, "to_dict") else act)
            events_data.append({
                "event_id": event_data.get("event_id", ""),
                "name": event_data.get("name", ""),
                "conditions": conditions_list,
                "actions": actions_list,
            })

        linked_links = [
            link.to_dict()
            for link in self._links.values()
            if link.source_sheet_id == sheet_id or link.target_sheet_id == sheet_id
        ]

        sheet_variables: List[Dict[str, Any]] = []
        for var in self._variables.values():
            if var.scope == VariableScope.GLOBAL:
                sheet_variables.append(var.to_dict())

        return {
            "format_version": 2,
            "sheet": sheet.to_dict(),
            "events": events_data,
            "variables": sheet_variables,
            "links": linked_links,
            "exported_at": _time_module.time(),
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_event_stats(self) -> Dict[str, Any]:
        """Return comprehensive event scripting subsystem statistics.

        Returns:
            Dictionary with total_sheets, total_events, total_conditions,
            total_actions, total_variables, active_sheets, execution_count,
            and avg_execution_time.
        """
        total_conditions = 0
        total_actions = 0
        active_sheets = 0
        scope_distribution: Dict[str, int] = {}
        link_type_distribution: Dict[str, int] = {}

        for sheet in self._sheets.values():
            if sheet.is_active:
                active_sheets += 1
            for event_data in sheet.events:
                total_conditions += len(event_data.get("conditions", []))
                total_actions += len(event_data.get("actions", []))
            scope_key = "global" if sheet.is_global else "local"
            scope_distribution[scope_key] = scope_distribution.get(scope_key, 0) + 1

        for link in self._links.values():
            lt = link.link_type.value
            link_type_distribution[lt] = link_type_distribution.get(lt, 0) + 1

        avg_time = (
            self._total_execution_time / self._execution_count
            if self._execution_count > 0
            else 0.0
        )

        return {
            "total_sheets": len(self._sheets),
            "total_events": len(self._event_index),
            "total_conditions": total_conditions,
            "total_actions": total_actions,
            "total_variables": len(self._variables),
            "active_sheets": active_sheets,
            "execution_count": self._execution_count,
            "avg_execution_time": round(avg_time, 6),
            "scope_distribution": scope_distribution,
            "link_type_distribution": link_type_distribution,
            "limits": {
                "max_sheets": self.MAX_SHEETS,
                "max_events_per_sheet": self.MAX_EVENTS_PER_SHEET,
                "max_conditions_per_event": self.MAX_CONDITIONS_PER_EVENT,
                "max_actions_per_event": self.MAX_ACTIONS_PER_EVENT,
                "max_links": self.MAX_LINKS,
                "max_variables": self.MAX_VARIABLES,
                "max_sub_condition_depth": self.MAX_SUB_CONDITION_DEPTH,
                "max_sub_action_depth": self.MAX_SUB_ACTION_DEPTH,
            },
        }

    # ------------------------------------------------------------------
    # Backward-Compatible Methods
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return scripting runtime statistics (backward-compatible alias)."""
        return self.get_event_stats()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all engine state, clearing sheets, events, variables, and links."""
        with self._lock:
            self._sheets.clear()
            self._conditions.clear()
            self._actions.clear()
            self._links.clear()
            self._variables.clear()
            self._event_index.clear()
            self._execution_count = 0
            self._total_execution_time = 0.0


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_event_scripting() -> EngineEventScripting:
    """Return the singleton EngineEventScripting instance."""
    return EngineEventScripting.get_instance()


# ---------------------------------------------------------------------------
# Backward-Compatible Aliases (for code that imports the old class names)
# ---------------------------------------------------------------------------

EventScripting = EngineEventScripting
get_event_scripting = get_engine_event_scripting