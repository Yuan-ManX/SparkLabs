"""
SparkLabs Engine - Event Scripting System

Visual event-based scripting system using a declarative
event-driven architecture. Enables no-code game logic creation
through conditions, actions, and sub-events — making AI-generated
game behavior accessible through a structured, composable model.

Architecture:
  EventScriptingSystem
    |-- EventSheet (ordered list of events with conditions/actions)
    |-- Condition (evaluable predicate testing game state)
    |-- Action (executable operation modifying game state)
    |-- Trigger (event that activates when condition becomes true)

Condition Types:
  - COMPARISON: numeric/string comparison between expressions
  - STATE_CHECK: boolean check of entity/scene/variable state
  - COLLISION: entity overlap or proximity detection
  - INPUT: key press, mouse, or touch detection
  - TIMER: time-based conditions (elapsed, interval)

Action Types:
  - TRANSFORM: position/rotation/scale modification
  - PROPERTY: set entity or scene property
  - VARIABLE: assign/increment/toggle variable
  - SPAWN: create or destroy entities
  - TRANSITION: scene change, camera transition
  - AUDIO: play sound, set volume, stop music

Usage:
    es = EventScriptingSystem()
    sheet = es.create_sheet("player_controls")
    evt = sheet.add_event("Move Right")
    evt.add_condition("input", key="ArrowRight", state="pressed")
    evt.add_action("transform", entity="player", property="x", operation="add", value=5)
    es.run_sheet("player_controls", dt)
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


class ConditionType(Enum):
    COMPARISON = auto()
    STATE_CHECK = auto()
    COLLISION = auto()
    INPUT = auto()
    TIMER = auto()
    ALWAYS = auto()


class ActionType(Enum):
    TRANSFORM = auto()
    PROPERTY = auto()
    VARIABLE = auto()
    SPAWN = auto()
    TRANSITION = auto()
    AUDIO = auto()
    CAMERA = auto()
    LAYER = auto()
    CUSTOM = auto()


class Operator(Enum):
    EQUAL = "=="
    NOT_EQUAL = "!="
    GREATER = ">"
    LESS = "<"
    GREATER_OR_EQUAL = ">="
    LESS_OR_EQUAL = "<="
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class Condition:
    condition_id: str = ""
    condition_type: ConditionType = ConditionType.ALWAYS
    operator: Operator = Operator.EQUAL
    parameters: Dict[str, Any] = field(default_factory=dict)
    inverted: bool = False

    def evaluate(self, context: Dict[str, Any]) -> bool:
        if self.condition_type == ConditionType.ALWAYS:
            result = True
        elif self.condition_type == ConditionType.INPUT:
            key = self.parameters.get("key", "")
            state = self.parameters.get("state", "pressed")
            inputs = context.get("inputs", {})
            result = inputs.get(key, {}).get(state, False)
        elif self.condition_type == ConditionType.COMPARISON:
            left = self._resolve_expression(self.parameters.get("left", 0), context)
            right = self._resolve_expression(self.parameters.get("right", 0), context)
            result = self._apply_operator(left, right)
        elif self.condition_type == ConditionType.STATE_CHECK:
            entity_id = self.parameters.get("entity", "")
            property_name = self.parameters.get("property", "")
            entities = context.get("entities", {})
            entity = entities.get(entity_id, {})
            result = bool(entity.get(property_name, False))
        elif self.condition_type == ConditionType.TIMER:
            timer_name = self.parameters.get("timer", "")
            timers = context.get("timers", {})
            timer = timers.get(timer_name, {})
            elapsed = timer.get("elapsed", 0)
            interval = self.parameters.get("interval", 0)
            result = elapsed >= interval
        else:
            result = False

        return not result if self.inverted else result

    def _resolve_expression(self, expr: Any, context: Dict[str, Any]) -> Any:
        if isinstance(expr, str) and expr.startswith("$"):
            var_name = expr[1:]
            variables = context.get("variables", {})
            return variables.get(var_name, 0)
        return expr

    def _apply_operator(self, left: Any, right: Any) -> bool:
        try:
            if self.operator == Operator.EQUAL:
                return left == right
            elif self.operator == Operator.NOT_EQUAL:
                return left != right
            elif self.operator == Operator.GREATER:
                return float(left) > float(right)
            elif self.operator == Operator.LESS:
                return float(left) < float(right)
            elif self.operator == Operator.GREATER_OR_EQUAL:
                return float(left) >= float(right)
            elif self.operator == Operator.LESS_OR_EQUAL:
                return float(left) <= float(right)
        except (ValueError, TypeError):
            return False
        return False


@dataclass
class Action:
    action_id: str = ""
    action_type: ActionType = ActionType.CUSTOM
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0
    _scheduled_at: float = 0.0

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        mutations: Dict[str, Any] = {}

        if self.action_type == ActionType.TRANSFORM:
            entity_id = self.parameters.get("entity", "")
            prop = self.parameters.get("property", "x")
            op = self.parameters.get("operation", "set")
            value = self.parameters.get("value", 0)
            mutations["entity_transforms"] = {(entity_id, prop): (op, value)}
        elif self.action_type == ActionType.PROPERTY:
            entity_id = self.parameters.get("entity", "")
            prop = self.parameters.get("property", "")
            value = self.parameters.get("value")
            mutations["entity_properties"] = {(entity_id, prop): value}
        elif self.action_type == ActionType.VARIABLE:
            var_name = self.parameters.get("name", "")
            op = self.parameters.get("operation", "set")
            value = self.parameters.get("value", 0)
            mutations["variables"] = {(var_name, op): value}
        elif self.action_type == ActionType.SPAWN:
            template = self.parameters.get("template", "")
            x = self.parameters.get("x", 0)
            y = self.parameters.get("y", 0)
            mutations["spawn"] = {"template": template, "position": (x, y)}
        elif self.action_type == ActionType.AUDIO:
            sound = self.parameters.get("sound", "")
            action = self.parameters.get("action", "play")
            mutations["audio"] = {"sound": sound, "action": action}

        return mutations

    @property
    def is_ready(self) -> bool:
        if self.delay <= 0:
            return True
        return (time.monotonic() - self._scheduled_at) >= self.delay


@dataclass
class GameEvent:
    event_id: str = ""
    name: str = ""
    conditions: List[Condition] = field(default_factory=list)
    actions: List[Action] = field(default_factory=list)
    sub_events: List["GameEvent"] = field(default_factory=list)
    trigger_once: bool = False
    _has_triggered: bool = False
    cooldown: float = 0.0
    _last_triggered: float = 0.0

    def add_condition(self, condition_type: str, **params) -> Condition:
        ct = ConditionType[condition_type.upper()] if condition_type.upper() in ConditionType.__members__ else ConditionType.ALWAYS
        cond = Condition(
            condition_id=str(uuid.uuid4())[:8],
            condition_type=ct,
            parameters=params,
        )
        self.conditions.append(cond)
        return cond

    def add_action(self, action_type: str, **params) -> Action:
        at = ActionType[action_type.upper()] if action_type.upper() in ActionType.__members__ else ActionType.CUSTOM
        act = Action(
            action_id=str(uuid.uuid4())[:8],
            action_type=at,
            parameters=params,
        )
        self.actions.append(act)
        return act

    def add_sub_event(self, name: str) -> "GameEvent":
        sub = GameEvent(event_id=str(uuid.uuid4())[:8], name=name)
        self.sub_events.append(sub)
        return sub

    def evaluate(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if self.trigger_once and self._has_triggered:
            return []

        if self.cooldown > 0:
            since_last = time.monotonic() - self._last_triggered
            if since_last < self.cooldown:
                return []

        all_conditions_met = all(c.evaluate(context) for c in self.conditions)
        if not all_conditions_met:
            return []

        self._has_triggered = True
        self._last_triggered = time.monotonic()

        mutations = []
        for action in self.actions:
            if action.is_ready:
                result = action.execute(context)
                mutations.append(result)

        for sub in self.sub_events:
            sub_mutations = sub.evaluate(context)
            mutations.extend(sub_mutations)

        return mutations


@dataclass
class EventSheet:
    sheet_id: str = ""
    name: str = ""
    events: List[GameEvent] = field(default_factory=list)
    description: str = ""
    enabled: bool = True

    def add_event(self, name: str) -> GameEvent:
        evt = GameEvent(event_id=str(uuid.uuid4())[:8], name=name)
        self.events.append(evt)
        return evt

    def run(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.enabled:
            return []
        all_mutations = []
        for event in self.events:
            mutations = event.evaluate(context)
            all_mutations.extend(mutations)
        return all_mutations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sheet_id": self.sheet_id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "event_count": len(self.events),
        }


class EventScriptingSystem:
    _instance: Optional["EventScriptingSystem"] = None

    def __init__(self):
        self._sheets: Dict[str, EventSheet] = {}
        self._global_variables: Dict[str, Any] = {}
        self._timers: Dict[str, Dict[str, Any]] = {}
        self._execution_order: List[str] = []
        self._total_executions: int = 0

    @classmethod
    def get_instance(cls) -> "EventScriptingSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_sheet(self, name: str, description: str = "") -> EventSheet:
        sheet_id = str(uuid.uuid4())[:8]
        sheet = EventSheet(sheet_id=sheet_id, name=name, description=description)
        self._sheets[sheet_id] = sheet
        self._execution_order.append(sheet_id)
        return sheet

    def get_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        return self._sheets.get(sheet_id)

    def delete_sheet(self, sheet_id: str) -> bool:
        if sheet_id in self._sheets:
            del self._sheets[sheet_id]
            if sheet_id in self._execution_order:
                self._execution_order.remove(sheet_id)
            return True
        return False

    def set_variable(self, name: str, value: Any) -> None:
        self._global_variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self._global_variables.get(name, default)

    def setup_timer(self, name: str, interval: float) -> None:
        self._timers[name] = {"elapsed": 0.0, "interval": interval, "active": True}

    def run_all(self, dt: float, game_context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        for timer in self._timers.values():
            if timer.get("active"):
                timer["elapsed"] += dt

        context = game_context or {}
        context["variables"] = self._global_variables
        context["timers"] = self._timers

        all_mutations = []
        for sheet_id in self._execution_order:
            sheet = self._sheets.get(sheet_id)
            if sheet:
                mutations = sheet.run(context)
                all_mutations.extend(mutations)

        self._total_executions += 1
        return all_mutations

    def run_sheet(self, sheet_id_or_name: str, dt: float, context: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id_or_name)
        if not sheet:
            for s in self._sheets.values():
                if s.name == sheet_id_or_name:
                    sheet = s
                    break
        if not sheet:
            return []

        ctx = context or {}
        ctx["variables"] = self._global_variables
        ctx["timers"] = self._timers

        for timer in self._timers.values():
            if timer.get("active"):
                timer["elapsed"] += dt

        return sheet.run(ctx)

    def import_from_json(self, data: Dict[str, Any]) -> EventSheet:
        sheet = self.create_sheet(data.get("name", "Imported Sheet"), data.get("description", ""))
        for evt_data in data.get("events", []):
            evt = sheet.add_event(evt_data.get("name", "Event"))
            evt.trigger_once = evt_data.get("trigger_once", False)
            evt.cooldown = evt_data.get("cooldown", 0.0)
            for cond_data in evt_data.get("conditions", []):
                ct = cond_data.pop("type", "always")
                evt.add_condition(ct, **cond_data)
            for act_data in evt_data.get("actions", []):
                at = act_data.pop("type", "custom")
                evt.add_action(at, **act_data)
        return sheet

    def export_to_json(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return None
        return {
            "name": sheet.name,
            "description": sheet.description,
            "events": [
                {
                    "name": e.name,
                    "trigger_once": e.trigger_once,
                    "cooldown": e.cooldown,
                    "conditions": [
                        {"type": c.condition_type.name.lower(), **c.parameters}
                        for c in e.conditions
                    ],
                    "actions": [
                        {"type": a.action_type.name.lower(), **a.parameters}
                        for a in e.actions
                    ],
                }
                for e in sheet.events
            ],
        }

    def get_all_sheets(self) -> List[Dict[str, Any]]:
        return [
            {"sheet_id": s.sheet_id, "name": s.name, "description": s.description,
             "event_count": len(s.events), "enabled": s.enabled}
            for s in self._sheets.values()
        ]

    def list_sheets(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sheets.values()]

    def import_sheet_from_json(self, sheet_id: str, events_json: List[Dict[str, Any]]) -> None:
        sheet = self._sheets.get(sheet_id)
        if not sheet:
            return
        for evt_data in events_json:
            evt = sheet.add_event(evt_data.get("name", "Event"))
            evt.trigger_once = evt_data.get("trigger_once", False)
            evt.cooldown = evt_data.get("cooldown", 0.0)
            for cond_data in evt_data.get("conditions", []):
                ct = cond_data.pop("type", "always")
                evt.add_condition(ct, **cond_data)
            for act_data in evt_data.get("actions", []):
                at = act_data.pop("type", "custom")
                evt.add_action(at, **act_data)

    def get_stats(self) -> Dict[str, Any]:
        total_events = sum(len(s.events) for s in self._sheets.values())
        return {
            "sheet_count": len(self._sheets),
            "total_events": total_events,
            "total_executions": self._total_executions,
            "variable_count": len(self._global_variables),
            "timer_count": len(self._timers),
        }


def get_event_scripting_system() -> EventScriptingSystem:
    return EventScriptingSystem.get_instance()
