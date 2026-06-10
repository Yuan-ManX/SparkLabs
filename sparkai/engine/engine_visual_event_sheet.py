"""
SparkLabs Engine - Visual Event Sheet System

A visual scripting system that enables game logic creation through
condition-action event sheets. Each sheet contains events with trigger
conditions and corresponding action sequences, allowing designers and
agents to compose game behavior without writing traditional code.

The event sheet runtime evaluates conditions each frame and executes
matched action sequences, supporting nested sub-events, event groups,
variable scoping, and event linking for complex game logic flows.

Architecture:
  EngineVisualEventSheet (Singleton)
    |-- EventSheet (container of events with metadata)
    |-- GameEvent (single condition→actions rule)
    |-- EventCondition (trigger predicate)
    |-- EventAction (executable operation)
    |-- SubEvent (nested conditional event)
    |-- EventGroup (logically grouped events)
    |-- ConditionOperator (comparison operators)
    |-- ActionType (action categories)
    |-- EventScope (visibility and lifetime scope)

Core Capabilities:
  - create_sheet: Create a new event sheet with metadata
  - add_event: Add a condition→actions event to a sheet
  - add_sub_event: Nest a sub-event under a parent event
  - evaluate_sheet: Process all events in a sheet for the current frame
  - link_events: Enable/disable events based on conditions
  - clone_sheet: Deep-copy an event sheet
  - validate_sheet: Check sheet for logical errors
  - compile_sheet: Pre-compile sheet for runtime efficiency
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ConditionOperator(Enum):
    """Comparison operators for event conditions."""
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    GREATER_EQUAL = "greater_equal"
    LESS_EQUAL = "less_equal"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    BETWEEN = "between"
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"
    TRIGGER_ONCE = "trigger_once"
    EVERY_FRAMES = "every_frames"


class ActionType(Enum):
    """Categories of executable actions."""
    OBJECT = "object"
    SCENE = "scene"
    VARIABLE = "variable"
    CAMERA = "camera"
    AUDIO = "audio"
    ANIMATION = "animation"
    PHYSICS = "physics"
    UI = "ui"
    TIMING = "timing"
    INPUT = "input"
    SCRIPT = "script"
    CUSTOM = "custom"


class EventScope(Enum):
    """Visibility and lifetime scope for event sheets."""
    GLOBAL = "global"
    SCENE = "scene"
    OBJECT = "object"
    GROUP = "group"
    TEMPORARY = "temporary"


class SheetStatus(Enum):
    """Runtime status of an event sheet."""
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"
    ERROR = "error"


class EventTrigger(Enum):
    """When an event's conditions are evaluated."""
    EVERY_FRAME = "every_frame"
    ON_START = "on_start"
    ON_TRIGGER = "on_trigger"
    ON_COLLISION = "on_collision"
    ON_TIMER = "on_timer"
    ON_INPUT = "on_input"
    ON_SIGNAL = "on_signal"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class EventCondition:
    """A condition predicate for triggering event actions.

    Attributes:
        condition_id: Unique condition identifier.
        operator: Comparison operator.
        left_operand: Left-side expression or variable.
        right_operand: Right-side value or variable.
        invert: Negate the condition result.
        description: Human-readable condition description.
    """
    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    operator: ConditionOperator = ConditionOperator.EQUAL
    left_operand: str = ""
    right_operand: Any = None
    invert: bool = False
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "operator": self.operator.value,
            "left_operand": self.left_operand,
            "right_operand": self.right_operand,
            "invert": self.invert,
            "description": self.description,
        }


@dataclass
class EventAction:
    """An executable operation within an event.

    Attributes:
        action_id: Unique action identifier.
        action_type: Category of action.
        action_name: Specific operation to perform.
        parameters: Action parameters.
        target_object: Optional target object reference.
        delay_ms: Execution delay in milliseconds.
        repeat_count: Number of repetitions (0 for none, -1 for infinite).
    """
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: ActionType = ActionType.OBJECT
    action_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    target_object: str = ""
    delay_ms: float = 0.0
    repeat_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "action_type": self.action_type.value,
            "action_name": self.action_name,
            "parameters": dict(self.parameters),
            "target_object": self.target_object,
            "delay_ms": self.delay_ms,
            "repeat_count": self.repeat_count,
        }


@dataclass
class SubEvent:
    """A nested conditional event under a parent event.

    Sub-events are only evaluated when their parent event's conditions
    are met, enabling hierarchical conditional logic.

    Attributes:
        sub_event_id: Unique sub-event identifier.
        conditions: Trigger conditions (AND logic).
        actions: Executed when conditions pass.
        enabled: Whether this sub-event is active.
    """
    sub_event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sub_event_id": self.sub_event_id,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "enabled": self.enabled,
        }


@dataclass
class GameEvent:
    """A single condition-action event rule.

    When all conditions evaluate true (AND logic), the action sequence
    executes. Supports sub-events for nested conditional branching.

    Attributes:
        event_id: Unique event identifier.
        name: Display name.
        trigger: When to evaluate this event.
        conditions: Trigger conditions.
        actions: Execution actions.
        sub_events: Nested conditional events.
        enabled: Whether this event is active.
        trigger_once: Fire only once per activation.
        cooldown_ms: Minimum time between activations.
        priority: Execution order within the sheet (lower = first).
        group_id: Optional parent event group.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    trigger: EventTrigger = EventTrigger.EVERY_FRAME
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    sub_events: List[SubEvent] = field(default_factory=list)
    enabled: bool = True
    trigger_once: bool = False
    cooldown_ms: float = 0.0
    priority: int = 0
    group_id: str = ""
    _last_triggered: float = field(default_factory=lambda: 0.0)
    _has_fired: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "name": self.name,
            "trigger": self.trigger.value,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "sub_events": [s.to_dict() for s in self.sub_events],
            "enabled": self.enabled,
            "trigger_once": self.trigger_once,
            "cooldown_ms": self.cooldown_ms,
            "priority": self.priority,
            "group_id": self.group_id,
        }


@dataclass
class EventGroup:
    """A logical grouping of related events.

    Attributes:
        group_id: Unique group identifier.
        name: Group display name.
        description: Group purpose description.
        event_ids: Member event identifiers.
        enabled: Whether the group is active.
        collapsed: UI display state.
        color_tag: Visual identifier color.
    """
    group_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    event_ids: List[str] = field(default_factory=list)
    enabled: bool = True
    collapsed: bool = False
    color_tag: str = "#4a9eff"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "group_id": self.group_id,
            "name": self.name,
            "description": self.description,
            "event_count": len(self.event_ids),
            "enabled": self.enabled,
            "collapsed": self.collapsed,
            "color_tag": self.color_tag,
        }


@dataclass
class EventSheet:
    """A complete event sheet containing game logic rules.

    Attributes:
        sheet_id: Unique sheet identifier.
        name: Sheet display name.
        scope: Visibility scope.
        status: Runtime activation status.
        events: All game events in this sheet.
        groups: Logical event groupings.
        variables: Sheet-scoped variables.
        linked_sheets: Sheets triggered by events here.
        description: Sheet purpose description.
        created_at: Creation timestamp.
        version: Incremental version counter.
    """
    sheet_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    scope: EventScope = EventScope.SCENE
    status: SheetStatus = SheetStatus.DRAFT
    events: List[GameEvent] = field(default_factory=list)
    groups: List[EventGroup] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    linked_sheets: List[str] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=_time_module.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "name": self.name,
            "scope": self.scope.value,
            "status": self.status.value,
            "event_count": len(self.events),
            "group_count": len(self.groups),
            "linked_sheets": list(self.linked_sheets),
            "description": self.description,
            "version": self.version,
            "events": [e.to_dict() for e in self.events],
            "groups": [g.to_dict() for g in self.groups],
        }


# ---------------------------------------------------------------------------
# Condition Evaluator
# ---------------------------------------------------------------------------


class ConditionEvaluator:
    """Evaluates event conditions against runtime state."""

    @staticmethod
    def evaluate(
        condition: EventCondition,
        runtime_state: Dict[str, Any],
    ) -> bool:
        """Evaluate a single condition against current runtime state."""
        left = runtime_state.get(condition.left_operand)
        right = condition.right_operand

        # Resolve right operand if it's a variable reference
        if isinstance(right, str) and right.startswith("$"):
            right = runtime_state.get(right[1:])

        op = condition.operator
        result = False

        try:
            if op == ConditionOperator.EQUAL:
                result = left == right
            elif op == ConditionOperator.NOT_EQUAL:
                result = left != right
            elif op == ConditionOperator.GREATER:
                result = float(left) > float(right) if left is not None else False
            elif op == ConditionOperator.LESS:
                result = float(left) < float(right) if left is not None else False
            elif op == ConditionOperator.GREATER_EQUAL:
                result = float(left) >= float(right) if left is not None else False
            elif op == ConditionOperator.LESS_EQUAL:
                result = float(left) <= float(right) if left is not None else False
            elif op == ConditionOperator.CONTAINS:
                result = right in left if left else False
            elif op == ConditionOperator.NOT_CONTAINS:
                result = right not in left if left else True
            elif op == ConditionOperator.EXISTS:
                result = left is not None
            elif op == ConditionOperator.NOT_EXISTS:
                result = left is None
            elif op == ConditionOperator.BETWEEN:
                if isinstance(right, list) and len(right) == 2:
                    result = float(right[0]) <= float(left) <= float(right[1])
            elif op == ConditionOperator.TRIGGER_ONCE:
                result = True  # Managed by event lifecycle
            elif op == ConditionOperator.EVERY_FRAMES:
                if isinstance(right, (int, float)) and right > 0:
                    import time
                    frame = runtime_state.get("_frame_count", 0)
                    result = frame % int(right) == 0
        except (ValueError, TypeError):
            result = False

        return not result if condition.invert else result

    @staticmethod
    def evaluate_all(
        conditions: List[EventCondition],
        runtime_state: Dict[str, Any],
    ) -> bool:
        """Evaluate all conditions with AND logic."""
        if not conditions:
            return True
        return all(
            ConditionEvaluator.evaluate(c, runtime_state)
            for c in conditions
        )


# ---------------------------------------------------------------------------
# Engine Visual Event Sheet (Singleton)
# ---------------------------------------------------------------------------


class EngineVisualEventSheet:
    """
    Visual scripting system for condition-action game logic composition.

    Enables designers and AI agents to compose game behavior through
    event sheets containing trigger conditions and action sequences.
    The runtime evaluates conditions each frame and executes matched
    actions, supporting nested sub-events, event groups, variable
    scoping, and cross-sheet linking.

    Features:
      - Condition-action event sheets for visual game logic
      - Nested sub-events for hierarchical conditional branching
      - Event groups for logical organization
      - Variable scoping per sheet
      - Cross-sheet event linking
      - Per-event trigger modes (every_frame, on_start, on_trigger, etc.)
      - Cooldown and trigger-once semantics
      - Pre-compilation for runtime efficiency
      - Sheet validation for logic errors
    """

    _instance: Optional["EngineVisualEventSheet"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineVisualEventSheet":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._sheets: Dict[str, EventSheet] = {}
        self._runtime_state: Dict[str, Any] = {
            "_frame_count": 0,
            "_delta_time": 0.0,
            "_total_time": 0.0,
        }
        self._execution_log: List[Dict[str, Any]] = []
        self._max_log_entries: int = 500
        self._total_evaluations: int = 0
        self._total_actions_executed: int = 0

    # ------------------------------------------------------------------
    # Sheet Management
    # ------------------------------------------------------------------

    def create_sheet(
        self,
        name: str,
        scope: EventScope = EventScope.SCENE,
        description: str = "",
    ) -> EventSheet:
        """
        Create a new event sheet.

        Args:
            name: Display name for the sheet.
            scope: Visibility and lifetime scope.
            description: Human-readable purpose.

        Returns:
            The created EventSheet.
        """
        sheet = EventSheet(
            name=name,
            scope=scope,
            description=description,
        )
        self._sheets[sheet.sheet_id] = sheet
        return sheet

    def get_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        """Retrieve an event sheet by identifier."""
        return self._sheets.get(sheet_id)

    def list_sheets(
        self, scope: Optional[EventScope] = None
    ) -> List[Dict[str, Any]]:
        """List event sheets, optionally filtered by scope."""
        results = []
        for sheet in self._sheets.values():
            if scope and sheet.scope != scope:
                continue
            results.append({
                "sheet_id": sheet.sheet_id,
                "name": sheet.name,
                "scope": sheet.scope.value,
                "status": sheet.status.value,
                "event_count": len(sheet.events),
            })
        return results

    def set_sheet_status(self, sheet_id: str, status: SheetStatus) -> bool:
        """Change the runtime status of an event sheet."""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return False
        sheet.status = status
        return True

    def clone_sheet(self, sheet_id: str, new_name: str) -> Optional[EventSheet]:
        """
        Deep-copy an event sheet.

        Args:
            sheet_id: Source sheet to clone.
            new_name: Name for the cloned sheet.

        Returns:
            The new cloned EventSheet, or None if source not found.
        """
        original = self._sheets.get(sheet_id)
        if not original:
            return None

        cloned = EventSheet(
            name=new_name,
            scope=original.scope,
            status=SheetStatus.DRAFT,
            variables=dict(original.variables),
            linked_sheets=list(original.linked_sheets),
            description=f"Clone of '{original.name}'",
        )

        # Deep copy events and sub-events
        for event in original.events:
            new_event = GameEvent(
                name=event.name,
                trigger=event.trigger,
                conditions=[
                    EventCondition(
                        operator=c.operator,
                        left_operand=c.left_operand,
                        right_operand=c.right_operand,
                        invert=c.invert,
                        description=c.description,
                    )
                    for c in event.conditions
                ],
                actions=[
                    EventAction(
                        action_type=a.action_type,
                        action_name=a.action_name,
                        parameters=dict(a.parameters),
                        target_object=a.target_object,
                        delay_ms=a.delay_ms,
                    )
                    for a in event.actions
                ],
                sub_events=[
                    SubEvent(
                        conditions=[
                            EventCondition(
                                operator=sc.operator,
                                left_operand=sc.left_operand,
                                right_operand=sc.right_operand,
                                invert=sc.invert,
                                description=sc.description,
                            )
                            for sc in s.conditions
                        ],
                        actions=[
                            EventAction(
                                action_type=sa.action_type,
                                action_name=sa.action_name,
                                parameters=dict(sa.parameters),
                                target_object=sa.target_object,
                                delay_ms=sa.delay_ms,
                            )
                            for sa in s.actions
                        ],
                        enabled=s.enabled,
                    )
                    for s in event.sub_events
                ],
                enabled=event.enabled,
                trigger_once=event.trigger_once,
                cooldown_ms=event.cooldown_ms,
                priority=event.priority,
            )
            cloned.events.append(new_event)

        # Deep copy groups
        for group in original.groups:
            cloned.groups.append(EventGroup(
                name=group.name,
                description=group.description,
                color_tag=group.color_tag,
            ))

        self._sheets[cloned.sheet_id] = cloned
        return cloned

    def delete_sheet(self, sheet_id: str) -> bool:
        """Delete an event sheet."""
        return self._sheets.pop(sheet_id, None) is not None

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def add_event(
        self,
        sheet_id: str,
        name: str,
        trigger: EventTrigger = EventTrigger.EVERY_FRAME,
        conditions: Optional[List[EventCondition]] = None,
        actions: Optional[List[EventAction]] = None,
        priority: int = 0,
    ) -> Optional[GameEvent]:
        """
        Add a condition-action event to a sheet.

        Args:
            sheet_id: Target sheet identifier.
            name: Event display name.
            trigger: When to evaluate this event.
            conditions: Trigger conditions.
            actions: Execution actions.
            priority: Execution order (lower = first).

        Returns:
            Created GameEvent, or None if sheet not found.
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None

        event = GameEvent(
            name=name,
            trigger=trigger,
            conditions=conditions or [],
            actions=actions or [],
            priority=priority,
        )
        sheet.events.append(event)
        sheet.version += 1
        return event

    def add_sub_event(
        self,
        sheet_id: str,
        event_id: str,
        conditions: Optional[List[EventCondition]] = None,
        actions: Optional[List[EventAction]] = None,
    ) -> Optional[SubEvent]:
        """
        Nest a sub-event under a parent event.

        Sub-events are evaluated only when the parent event's conditions
        are met, enabling hierarchical conditional logic.

        Args:
            sheet_id: Target sheet identifier.
            event_id: Parent event identifier.
            conditions: Sub-event conditions.
            actions: Sub-event actions.

        Returns:
            Created SubEvent, or None if parent not found.
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None

        for event in sheet.events:
            if event.event_id == event_id:
                sub = SubEvent(
                    conditions=conditions or [],
                    actions=actions or [],
                )
                event.sub_events.append(sub)
                sheet.version += 1
                return sub

        return None

    def remove_event(self, sheet_id: str, event_id: str) -> bool:
        """Remove an event from a sheet."""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return False
        before = len(sheet.events)
        sheet.events = [e for e in sheet.events if e.event_id != event_id]
        if len(sheet.events) < before:
            sheet.version += 1
            return True
        return False

    # ------------------------------------------------------------------
    # Event Groups
    # ------------------------------------------------------------------

    def create_group(
        self,
        sheet_id: str,
        name: str,
        description: str = "",
        color_tag: str = "#4a9eff",
    ) -> Optional[EventGroup]:
        """Create a logical event group within a sheet."""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None

        group = EventGroup(
            name=name,
            description=description,
            color_tag=color_tag,
        )
        sheet.groups.append(group)
        sheet.version += 1
        return group

    def assign_event_to_group(
        self, sheet_id: str, event_id: str, group_id: str
    ) -> bool:
        """Assign an event to a group."""
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return False

        event_found = False
        for event in sheet.events:
            if event.event_id == event_id:
                event.group_id = group_id
                event_found = True
                break

        if event_found:
            for group in sheet.groups:
                if group.group_id == group_id:
                    if event_id not in group.event_ids:
                        group.event_ids.append(event_id)
                    return True

        return False

    # ------------------------------------------------------------------
    # Runtime Evaluation
    # ------------------------------------------------------------------

    def set_runtime_variable(self, key: str, value: Any) -> None:
        """Set a value in the global runtime state."""
        self._runtime_state[key] = value

    def evaluate_sheet(
        self,
        sheet_id: str,
        custom_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process all events in a sheet against current runtime state.

        Evaluates conditions for all active events, executes action sequences
        for matching events, processes sub-events, and handles trigger-once
        and cooldown semantics.

        Args:
            sheet_id: Sheet to evaluate.
            custom_state: Optional override runtime state.

        Returns:
            Execution report with triggered events and action counts.
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet or sheet.status != SheetStatus.ACTIVE:
            return {"triggered": 0, "actions_executed": 0, "sheet_status": sheet.status.value if sheet else "not_found"}

        state = custom_state or self._runtime_state

        # Sort events by priority
        sorted_events = sorted(
            [e for e in sheet.events if e.enabled],
            key=lambda e: e.priority,
        )

        current_time = _time_module.time()
        triggered_count = 0
        actions_count = 0
        executed_events: List[str] = []

        for event in sorted_events:
            # Check group enabled
            if event.group_id:
                group_enabled = True
                for group in sheet.groups:
                    if group.group_id == event.group_id:
                        group_enabled = group.enabled
                        break
                if not group_enabled:
                    continue

            # Trigger-once check
            if event.trigger_once and event._has_fired:
                continue

            # Cooldown check
            if event.cooldown_ms > 0:
                elapsed = (current_time - event._last_triggered) * 1000
                if elapsed < event.cooldown_ms:
                    continue

            # Evaluate conditions
            conditions_met = ConditionEvaluator.evaluate_all(
                event.conditions, state
            )

            if not conditions_met:
                continue

            # Execute actions
            triggered_count += 1
            event._last_triggered = current_time
            if event.trigger_once:
                event._has_fired = True

            for action in event.actions:
                self._execute_action(action, sheet, state)
                actions_count += 1

            # Process sub-events
            if event.sub_events:
                for sub in event.sub_events:
                    if not sub.enabled:
                        continue
                    if ConditionEvaluator.evaluate_all(sub.conditions, state):
                        for sub_action in sub.actions:
                            self._execute_action(sub_action, sheet, state)
                            actions_count += 1

            executed_events.append(event.event_id)

        self._total_evaluations += 1
        self._total_actions_executed += actions_count

        report = {
            "sheet_id": sheet_id,
            "sheet_name": sheet.name,
            "total_events": len(sheet.events),
            "triggered": triggered_count,
            "actions_executed": actions_count,
            "executed_events": executed_events,
            "frame": state.get("_frame_count", 0),
        }

        self._log_execution(report)
        return report

    def evaluate_all_active(self) -> Dict[str, Any]:
        """Evaluate all active event sheets."""
        results: Dict[str, Any] = {}
        total_triggered = 0
        total_actions = 0

        for sheet_id, sheet in self._sheets.items():
            if sheet.status == SheetStatus.ACTIVE:
                result = self.evaluate_sheet(sheet_id)
                results[sheet.name] = result
                total_triggered += result["triggered"]
                total_actions += result["actions_executed"]

        self._runtime_state["_frame_count"] += 1
        return {
            "sheets_evaluated": len(results),
            "total_triggered": total_triggered,
            "total_actions_executed": total_actions,
            "per_sheet": results,
        }

    def _execute_action(
        self, action: EventAction, sheet: EventSheet, state: Dict[str, Any]
    ):
        """Execute a single action against the runtime state."""
        # Variable actions modify sheet or runtime state
        if action.action_type == ActionType.VARIABLE:
            var_name = action.parameters.get("variable", "")
            value = action.parameters.get("value")
            scope = action.parameters.get("scope", "sheet")

            if action.action_name == "set":
                if scope == "sheet":
                    sheet.variables[var_name] = value
                else:
                    state[var_name] = value
            elif action.action_name == "increment":
                current = sheet.variables.get(var_name, 0)
                sheet.variables[var_name] = current + float(value or 0)
            elif action.action_name == "toggle":
                current = sheet.variables.get(var_name, False)
                sheet.variables[var_name] = not current

        # Scene actions
        elif action.action_type == ActionType.SCENE:
            if action.action_name == "switch_scene":
                state["_pending_scene"] = action.parameters.get("scene_name", "")
            elif action.action_name == "pause":
                state["_paused"] = True
            elif action.action_name == "resume":
                state["_paused"] = False

        # Object actions are handled by the game engine
        elif action.action_type in (ActionType.OBJECT, ActionType.CAMERA,
                                      ActionType.AUDIO, ActionType.ANIMATION,
                                      ActionType.PHYSICS):
            # These are dispatched to engine subsystems
            pass

    def _log_execution(self, report: Dict[str, Any]):
        """Record execution results for debugging."""
        self._execution_log.append(report)
        if len(self._execution_log) > self._max_log_entries:
            self._execution_log = self._execution_log[-250:]

    # ------------------------------------------------------------------
    # Sheet Linking
    # ------------------------------------------------------------------

    def link_sheets(self, source_id: str, target_id: str) -> bool:
        """
        Link two sheets so one can trigger the other.

        Args:
            source_id: Sheet that triggers the link.
            target_id: Sheet to be triggered.

        Returns:
            True if link was established.
        """
        source = self._sheets.get(source_id)
        target = self._sheets.get(target_id)
        if not source or not target:
            return False

        if target_id not in source.linked_sheets:
            source.linked_sheets.append(target_id)
            source.version += 1
        return True

    def unlink_sheets(self, source_id: str, target_id: str) -> bool:
        """Remove a link between two sheets."""
        source = self._sheets.get(source_id)
        if not source:
            return False
        if target_id in source.linked_sheets:
            source.linked_sheets.remove(target_id)
            source.version += 1
            return True
        return False

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_sheet(self, sheet_id: str) -> Dict[str, Any]:
        """
        Check an event sheet for logical errors and warnings.

        Returns:
            Dict with validation results, error count, and issue details.
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return {"valid": False, "errors": ["Sheet not found"]}

        errors: List[str] = []
        warnings: List[str] = []

        if not sheet.name:
            errors.append("Sheet has no name")

        if not sheet.events:
            warnings.append("Sheet has no events")

        for i, event in enumerate(sheet.events):
            prefix = f"Event [{i}] '{event.name or 'unnamed'}'"
            if not event.name:
                errors.append(f"{prefix}: has no name")
            if not event.trigger:
                errors.append(f"{prefix}: has no trigger mode")
            if not event.actions and not event.sub_events:
                warnings.append(f"{prefix}: has no actions or sub-events")
            if event.conditions:
                for j, cond in enumerate(event.conditions):
                    if not cond.left_operand:
                        errors.append(f"{prefix}: condition [{j}] has no left operand")
                    if cond.operator in (ConditionOperator.EQUAL, ConditionOperator.NOT_EQUAL,
                                         ConditionOperator.GREATER, ConditionOperator.LESS,
                                         ConditionOperator.GREATER_EQUAL, ConditionOperator.LESS_EQUAL):
                        if cond.right_operand is None:
                            warnings.append(f"{prefix}: condition [{j}] has no right operand")

        return {
            "valid": len(errors) == 0,
            "error_count": len(errors),
            "warning_count": len(warnings),
            "errors": errors,
            "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Compilation
    # ------------------------------------------------------------------

    def compile_sheet(self, sheet_id: str) -> Dict[str, Any]:
        """
        Pre-compile an event sheet for runtime efficiency.

        Validates the sheet and produces a compiled structure with
        pre-resolved references and indexed events.

        Returns:
            Compilation result with success, event count, and warnings.
        """
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return {"compiled": False, "error": "Sheet not found"}

        validation = self.validate_sheet(sheet_id)
        if not validation["valid"]:
            return {
                "compiled": False,
                "error": "Validation failed",
                "validation": validation,
            }

        # Build compiled index
        compiled = {
            "sheet_id": sheet.sheet_id,
            "name": sheet.name,
            "scope": sheet.scope.value,
            "version": sheet.version,
            "event_count": len(sheet.events),
            "events_by_priority": {},
            "events_by_trigger": {},
            "linked_sheets": list(sheet.linked_sheets),
        }

        for event in sheet.events:
            # Index by priority
            prio = event.priority
            if prio not in compiled["events_by_priority"]:
                compiled["events_by_priority"][prio] = []
            compiled["events_by_priority"][prio].append(event.event_id)

            # Index by trigger
            trig = event.trigger.value
            if trig not in compiled["events_by_trigger"]:
                compiled["events_by_trigger"][trig] = []
            compiled["events_by_trigger"][trig].append(event.event_id)

        return {
            "compiled": True,
            "sheet_name": sheet.name,
            "event_count": len(sheet.events),
            "sub_event_count": sum(len(e.sub_events) for e in sheet.events),
            "action_count": sum(len(e.actions) for e in sheet.events),
            "priority_levels": len(compiled["events_by_priority"]),
            "trigger_types": len(compiled["events_by_trigger"]),
            "compiled_data": compiled,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_statistics(self) -> Dict[str, Any]:
        """Return aggregate event sheet system statistics."""
        total_events = sum(len(s.events) for s in self._sheets.values())
        total_actions = sum(
            len(e.actions) + sum(len(se.actions) for se in e.sub_events)
            for s in self._sheets.values()
            for e in s.events
        )
        total_conditions = sum(
            len(e.conditions) + sum(len(se.conditions) for se in e.sub_events)
            for s in self._sheets.values()
            for e in s.events
        )

        return {
            "total_sheets": len(self._sheets),
            "active_sheets": sum(1 for s in self._sheets.values()
                                if s.status == SheetStatus.ACTIVE),
            "total_events": total_events,
            "total_actions": total_actions,
            "total_conditions": total_conditions,
            "total_evaluations": self._total_evaluations,
            "total_actions_executed": self._total_actions_executed,
            "runtime_variables": list(self._runtime_state.keys()),
        }

    # ------------------------------------------------------------------
    # Execution Log
    # ------------------------------------------------------------------

    def get_execution_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent execution history."""
        return list(self._execution_log[-limit:])

    # ------------------------------------------------------------------
    # Singleton & Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "EngineVisualEventSheet":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Reset the event sheet system to initial state."""
        with self._lock:
            self._sheets.clear()
            self._runtime_state = {
                "_frame_count": 0,
                "_delta_time": 0.0,
                "_total_time": 0.0,
            }
            self._execution_log.clear()
            self._total_evaluations = 0
            self._total_actions_executed = 0


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_visual_event_sheet() -> EngineVisualEventSheet:
    """Return the singleton EngineVisualEventSheet instance."""
    return EngineVisualEventSheet()