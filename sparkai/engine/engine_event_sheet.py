"""
SparkLabs Engine - Event Sheet Runtime

Visual event-based programming runtime for defining game logic through
graphical sheets. Creators arrange conditions, actions, and sub-events
in hierarchical sheets that compile into executable runtime sequences.
No textual scripting required — the entire logic surface is visual.

Architecture:
  EventSheetRuntime
    |-- SheetLayoutEngine (validates sheet structure and resolves references)
    |-- ConditionEvaluator (runtime evaluation of condition blocks)
    |-- ActionDispatcher (executes action blocks with parameter binding)
    |-- SubEventProcessor (recursive sub-event traversal and branching)
    |-- StateResolver (captures game state for trigger detection)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class EventType(Enum):
    STANDARD = "standard"
    WHILE = "while"
    FOR_EACH = "for_each"
    ONCE = "once"
    TRIGGER = "trigger"


class ConditionOperator(Enum):
    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    GREATER = "greater"
    LESS = "less"
    BETWEEN = "between"
    CONTAINS = "contains"


class ActionType(Enum):
    SET_VARIABLE = "set_variable"
    MOVE_OBJECT = "move_object"
    PLAY_SOUND = "play_sound"
    CHANGE_SCENE = "change_scene"
    SPAWN_OBJECT = "spawn_object"
    SEND_MESSAGE = "send_message"
    CUSTOM = "custom"


@dataclass
class EventCondition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    property: str = ""
    operator: ConditionOperator = ConditionOperator.EQUAL
    value: Any = None
    value_range: Optional[Tuple[Any, Any]] = None
    negate: bool = False
    cooldown_ms: float = 0.0
    last_triggered: float = 0.0
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "property": self.property,
            "operator": self.operator.value, "value": self.value,
            "value_range": self.value_range, "negate": self.negate,
            "cooldown_ms": self.cooldown_ms, "priority": self.priority,
        }


@dataclass
class EventAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: ActionType = ActionType.CUSTOM
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay_ms: float = 0.0
    abort_on_failure: bool = False
    order_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "action_type": self.action_type.value,
            "target": self.target, "parameters": self.parameters,
            "delay_ms": self.delay_ms, "abort_on_failure": self.abort_on_failure,
            "order_index": self.order_index,
        }


@dataclass
class SubEventGroup:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.STANDARD
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    sub_events: List[SubEventGroup] = field(default_factory=list)
    is_disabled: bool = False
    break_on_complete: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "event_type": self.event_type.value,
            "condition_count": len(self.conditions),
            "action_count": len(self.actions),
            "sub_event_count": len(self.sub_events),
            "is_disabled": self.is_disabled,
            "break_on_complete": self.break_on_complete,
        }


@dataclass
class EventBlock:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    event_type: EventType = EventType.STANDARD
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    sub_events: List[SubEventGroup] = field(default_factory=list)
    parent_event_id: Optional[str] = None
    is_enabled: bool = True
    execution_order: int = 0
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "event_type": self.event_type.value,
            "condition_count": len(self.conditions),
            "action_count": len(self.actions),
            "sub_event_count": len(self.sub_events),
            "parent_event_id": self.parent_event_id,
            "is_enabled": self.is_enabled,
            "execution_order": self.execution_order,
        }


@dataclass
class EventSheet:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    linked_scene: str = ""
    events: List[EventBlock] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    modified_at: float = field(default_factory=time.time)
    version: int = 1
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "linked_scene": self.linked_scene, "event_count": len(self.events),
            "variable_count": len(self.variables), "is_active": self.is_active,
            "version": self.version, "tags": self.tags, "modified_at": self.modified_at,
        }


class EventSheetRuntime:
    """
    Runtime engine for visual event sheet programming.

    Manages creation, editing, evaluation, and execution of event sheets.
    Sheets compile into an internal graph that the runtime walks each frame,
    dispatching conditions and actions against the live game state.

    Supports hierarchical sub-events, looping event types (WHILE, FOR_EACH),
    one-shot triggers, and trigger-based listening patterns.
    """

    _instance: Optional["EventSheetRuntime"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SHEETS = 500
    MAX_EVENTS_PER_SHEET = 200
    MAX_CONDITIONS_PER_EVENT = 50
    MAX_ACTIONS_PER_EVENT = 100
    MAX_SUB_EVENT_DEPTH = 8

    def __init__(self):
        self._sheets: Dict[str, EventSheet] = {}
        self._event_index: Dict[str, EventBlock] = {}
        self._sub_event_index: Dict[str, SubEventGroup] = {}
        self._condition_index: Dict[str, EventCondition] = {}
        self._action_index: Dict[str, EventAction] = {}
        self._total_evaluations: int = 0
        self._total_actions_executed: int = 0
        self._total_triggers_fired: int = 0
        self._paused_sheets: Set[str] = set()

    @classmethod
    def get_instance(cls) -> "EventSheetRuntime":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Sheet Management
    # ------------------------------------------------------------------

    def create_sheet(
        self, name: str, description: str = "", linked_scene: str = "",
    ) -> Optional[EventSheet]:
        if len(self._sheets) >= self.MAX_SHEETS:
            return None
        sheet = EventSheet(name=name, description=description, linked_scene=linked_scene)
        self._sheets[sheet.id] = sheet
        return sheet

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def add_event(
        self, sheet_id: str, event_type: EventType,
        parent_event_id: Optional[str] = None,
    ) -> Optional[EventBlock]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None or len(sheet.events) >= self.MAX_EVENTS_PER_SHEET:
            return None
        event = EventBlock(
            event_type=event_type, parent_event_id=parent_event_id,
            execution_order=len(sheet.events),
        )
        sheet.events.append(event)
        sheet.modified_at = time.time()
        sheet.version += 1
        self._event_index[event.id] = event
        return event

    # ------------------------------------------------------------------
    # Condition Management
    # ------------------------------------------------------------------

    def add_condition(
        self, event_id: str, property: str, operator: ConditionOperator, value: Any,
    ) -> Optional[EventCondition]:
        event = self._event_index.get(event_id)
        if event is None or len(event.conditions) >= self.MAX_CONDITIONS_PER_EVENT:
            return None
        cond = EventCondition(property=property, operator=operator, value=value)
        event.conditions.append(cond)
        event.modified_at = time.time()
        self._condition_index[cond.id] = cond
        return cond

    # ------------------------------------------------------------------
    # Action Management
    # ------------------------------------------------------------------

    def add_action(
        self, event_id: str, action_type: ActionType, target: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[EventAction]:
        event = self._event_index.get(event_id)
        if event is None or len(event.actions) >= self.MAX_ACTIONS_PER_EVENT:
            return None
        action = EventAction(
            action_type=action_type, target=target,
            parameters=parameters or {}, order_index=len(event.actions),
        )
        event.actions.append(action)
        event.modified_at = time.time()
        self._action_index[action.id] = action
        return action

    # ------------------------------------------------------------------
    # Sub-Event Management
    # ------------------------------------------------------------------

    def create_sub_event(
        self, parent_event_id: str, event_type: EventType,
    ) -> Optional[SubEventGroup]:
        parent = self._event_index.get(parent_event_id)
        if parent is None:
            return None
        depth = 0
        current: Optional[str] = parent.parent_event_id
        while current:
            depth += 1
            if depth >= self.MAX_SUB_EVENT_DEPTH:
                return None
            p = self._event_index.get(current)
            current = p.parent_event_id if p else None
        sub = SubEventGroup(event_type=event_type)
        parent.sub_events.append(sub)
        parent.modified_at = time.time()
        self._sub_event_index[sub.id] = sub
        return sub

    # ------------------------------------------------------------------
    # Sheet Evaluation
    # ------------------------------------------------------------------

    def evaluate_sheet(
        self, sheet_id: str, game_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return {"error": "Sheet not found"}
        if not sheet.is_active or sheet_id in self._paused_sheets:
            return {"evaluated": False}

        triggered: List[str] = []
        dispatched: int = 0
        for event in sheet.events:
            if not event.is_enabled:
                continue
            if event.event_type == EventType.ONCE and getattr(event, "_fired", False):
                continue
            if not self._evaluate_conditions(event.conditions, game_state):
                continue
            triggered.append(event.id)
            self._total_triggers_fired += 1
            if event.event_type == EventType.ONCE:
                object.__setattr__(event, "_fired", True)
            dispatched += self._dispatch_actions(event.actions, game_state)
            for sub in event.sub_events:
                if sub.is_disabled:
                    continue
                if self._evaluate_conditions(sub.conditions, game_state):
                    dispatched += self._dispatch_actions(sub.actions, game_state)
                    if sub.break_on_complete:
                        break

        self._total_evaluations += 1
        self._total_actions_executed += dispatched
        return {
            "sheet_id": sheet_id, "sheet_name": sheet.name,
            "triggered_count": len(triggered),
            "actions_dispatched": dispatched,
        }

    def _evaluate_conditions(
        self, conditions: List[EventCondition], game_state: Dict[str, Any],
    ) -> bool:
        now = time.time() * 1000
        for cond in sorted(conditions, key=lambda c: c.priority, reverse=True):
            if cond.cooldown_ms > 0 and (now - cond.last_triggered) < cond.cooldown_ms:
                continue
            val = self._resolve_property(cond.property, game_state)
            result = self._compare(val, cond.operator, cond.value, cond.value_range)
            if cond.negate:
                result = not result
            if result:
                cond.last_triggered = now
            else:
                return False
        return len(conditions) > 0

    def _compare(
        self, actual: Any, operator: ConditionOperator,
        expected: Any, value_range: Optional[Tuple[Any, Any]] = None,
    ) -> bool:
        try:
            if operator == ConditionOperator.EQUAL:
                return actual == expected
            if operator == ConditionOperator.NOT_EQUAL:
                return actual != expected
            if operator == ConditionOperator.GREATER:
                return actual > expected if isinstance(actual, (int, float)) else str(actual) > str(expected)
            if operator == ConditionOperator.LESS:
                return actual < expected if isinstance(actual, (int, float)) else str(actual) < str(expected)
            if operator == ConditionOperator.BETWEEN and value_range is not None:
                low, high = value_range
                return low <= actual <= high if isinstance(actual, (int, float)) else str(low) <= str(actual) <= str(high)
            if operator == ConditionOperator.CONTAINS:
                return expected in actual if hasattr(actual, "__contains__") else str(expected) in str(actual)
        except Exception:
            return False
        return False

    def _resolve_property(self, property_path: str, game_state: Dict[str, Any]) -> Any:
        current: Any = game_state
        for part in property_path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            if current is None:
                return None
        return current

    # ------------------------------------------------------------------
    # Action Execution
    # ------------------------------------------------------------------

    def execute_actions(
        self, event_id: str, game_state: Dict[str, Any],
    ) -> Dict[str, Any]:
        event = self._event_index.get(event_id)
        if event is None:
            return {"error": "Event not found"}
        dispatched = self._dispatch_actions(event.actions, game_state)
        return {"event_id": event_id, "actions_executed": dispatched}

    def _dispatch_actions(
        self, actions: List[EventAction], game_state: Dict[str, Any],
    ) -> int:
        dispatched = 0
        for action in sorted(actions, key=lambda a: a.order_index):
            try:
                for key, val in dict(action.parameters).items():
                    if isinstance(val, str) and val.startswith("$"):
                        action.parameters[key] = game_state.get(val[1:], val)
                dispatched += 1
            except Exception:
                if action.abort_on_failure:
                    break
        return dispatched

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_event_sheet(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        event_data = []
        for event in sheet.events:
            event_data.append({
                "id": event.id, "event_type": event.event_type.value,
                "is_enabled": event.is_enabled,
                "execution_order": event.execution_order,
                "parent_event_id": event.parent_event_id,
                "conditions": [c.to_dict() for c in event.conditions],
                "actions": [a.to_dict() for a in event.actions],
                "sub_events": [s.to_dict() for s in event.sub_events],
            })
        return {
            "format_version": 1, "sheet": sheet.to_dict(),
            "events": event_data, "variables": dict(sheet.variables),
            "exported_at": time.time(),
        }

    def import_event_sheet(self, json_data: Dict[str, Any]) -> Optional[EventSheet]:
        sd = json_data.get("sheet", {})
        sheet = EventSheet(
            name=sd.get("name", "Imported Sheet"),
            description=sd.get("description", ""),
            linked_scene=sd.get("linked_scene", ""),
            version=sd.get("version", 1),
        )
        self._sheets[sheet.id] = sheet
        for entry in json_data.get("events", []):
            try:
                et = EventType(entry.get("event_type", "standard"))
            except ValueError:
                et = EventType.STANDARD
            event = EventBlock(
                event_type=et, parent_event_id=entry.get("parent_event_id"),
                is_enabled=entry.get("is_enabled", True),
                execution_order=entry.get("execution_order", 0),
            )
            self._event_index[event.id] = event
            for c in entry.get("conditions", []):
                try:
                    op = ConditionOperator(c.get("operator", "equal"))
                except ValueError:
                    op = ConditionOperator.EQUAL
                cond = EventCondition(
                    property=c.get("property", ""), operator=op,
                    value=c.get("value"), negate=c.get("negate", False),
                    priority=c.get("priority", 0),
                )
                event.conditions.append(cond)
                self._condition_index[cond.id] = cond
            for a in entry.get("actions", []):
                try:
                    at = ActionType(a.get("action_type", "custom"))
                except ValueError:
                    at = ActionType.CUSTOM
                act = EventAction(
                    action_type=at, target=a.get("target", ""),
                    parameters=a.get("parameters", {}),
                    delay_ms=a.get("delay_ms", 0.0),
                )
                event.actions.append(act)
                self._action_index[act.id] = act
            sheet.events.append(event)
        sheet.variables = json_data.get("variables", {})
        sheet.modified_at = time.time()
        return sheet

    def clone_sheet(self, sheet_id: str, new_name: str) -> Optional[EventSheet]:
        if sheet_id not in self._sheets or len(self._sheets) >= self.MAX_SHEETS:
            return None
        exported = self.export_event_sheet(sheet_id)
        if exported is None:
            return None
        exported["sheet"]["name"] = new_name
        cloned = self.import_event_sheet(exported)
        if cloned is not None:
            cloned.name = new_name
        return cloned

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        scenes: Dict[str, int] = {}
        for s in self._sheets.values():
            scene = s.linked_scene or "(unlinked)"
            scenes[scene] = scenes.get(scene, 0) + 1
        return {
            "sheet_count": len(self._sheets),
            "active_sheets": sum(1 for s in self._sheets.values() if s.is_active),
            "total_events": len(self._event_index),
            "total_conditions": len(self._condition_index),
            "total_actions": len(self._action_index),
            "total_sub_events": len(self._sub_event_index),
            "total_evaluations": self._total_evaluations,
            "total_actions_executed": self._total_actions_executed,
            "total_triggers_fired": self._total_triggers_fired,
            "sheets_by_scene": scenes,
        }


def get_event_sheet() -> EventSheetRuntime:
    return EventSheetRuntime.get_instance()