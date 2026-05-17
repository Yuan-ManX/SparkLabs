"""
SparkLabs Engine - Event System

Combines GDevelop-style event sheets (visual behavior programming)
with Godot-style signal/slot communication. Event sheets are ordered
lists of conditions and actions evaluated top-down each frame. The
signal bus provides decoupled node-to-node communication via
named signals.

Architecture:
  EventSystem
    |-- EventSheet (ordered collection of game events)
    |-- GameEvent (conditions + actions + optional sub-events)
    |-- EventCondition (predicate evaluated against game context)
    |-- EventAction (operation executed when conditions are met)
    |-- SignalSlot (emitter-to-receiver connection with data passing)

Condition Types:
  - COLLISION, INPUT, TIMER, COMPARISON, VARIABLE, TRIGGER, ALWAYS,
    DISTANCE, STATE

Action Types:
  - MOVE, ROTATE, SCALE, SPAWN, DESTROY, PLAY_SOUND, CHANGE_SCENE,
    SET_VARIABLE, EMIT_SIGNAL, ANIMATE, APPLY_FORCE, TELEPORT,
    TOGGLE_VISIBILITY, SET_TEXT, SET_COLOR

Event Flow:
  1. evaluate_sheet(sheet_id, context) — top-down pass
  2. For each event, evaluate_event(event_id, context)
  3. If conditions pass, execute_event(event_id, context)
  4. Sub-events are evaluated recursively when parent fires
  5. Signal emissions are dispatched to connected slots
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ConditionType(Enum):
    COLLISION = "collision"
    INPUT = "input"
    TIMER = "timer"
    COMPARISON = "comparison"
    VARIABLE = "variable"
    TRIGGER = "trigger"
    ALWAYS = "always"
    DISTANCE = "distance"
    STATE = "state"


class ActionType(Enum):
    MOVE = "move"
    ROTATE = "rotate"
    SCALE = "scale"
    SPAWN = "spawn"
    DESTROY = "destroy"
    PLAY_SOUND = "play_sound"
    CHANGE_SCENE = "change_scene"
    SET_VARIABLE = "set_variable"
    EMIT_SIGNAL = "emit_signal"
    ANIMATE = "animate"
    APPLY_FORCE = "apply_force"
    TELEPORT = "teleport"
    TOGGLE_VISIBILITY = "toggle_visibility"
    SET_TEXT = "set_text"
    SET_COLOR = "set_color"


class RepeatMode(Enum):
    ONCE = "once"
    REPEAT = "repeat"
    WHILE_TRUE = "while_true"
    COUNTED = "counted"


OPERATOR_FUNCTIONS = {
    "eq": lambda a, b: a == b,
    "neq": lambda a, b: a != b,
    "gt": lambda a, b: float(a) > float(b),
    "lt": lambda a, b: float(a) < float(b),
    "gte": lambda a, b: float(a) >= float(b),
    "lte": lambda a, b: float(a) <= float(b),
    "contains": lambda a, b: str(b) in str(a),
}


@dataclass
class EventCondition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    condition_type: str = ConditionType.ALWAYS.value
    target_object: Optional[str] = None
    operator: str = "eq"
    expected_value: Any = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def evaluate(self, context: Dict[str, Any]) -> bool:
        ct = self.condition_type

        if ct == ConditionType.ALWAYS.value:
            return True

        if ct == ConditionType.INPUT.value:
            return self._evaluate_input(context)

        if ct == ConditionType.COLLISION.value:
            return self._evaluate_collision(context)

        if ct == ConditionType.TIMER.value:
            return self._evaluate_timer(context)

        if ct == ConditionType.COMPARISON.value:
            return self._evaluate_comparison(context)

        if ct == ConditionType.VARIABLE.value:
            return self._evaluate_variable(context)

        if ct == ConditionType.TRIGGER.value:
            return self._evaluate_trigger(context)

        if ct == ConditionType.DISTANCE.value:
            return self._evaluate_distance(context)

        if ct == ConditionType.STATE.value:
            return self._evaluate_state(context)

        return False

    def _resolve_value(self, context: Dict[str, Any]) -> Any:
        if self.target_object is None:
            return None
        objects = context.get("objects", {})
        return objects.get(self.target_object, {})

    def _evaluate_input(self, context: Dict[str, Any]) -> bool:
        inputs = context.get("input", {})
        key = self.parameters.get("key")
        state = self.parameters.get("state", "pressed")
        if key and key in inputs:
            return inputs[key] == state
        if self.expected_value is not None:
            actual = inputs.get(self.target_object or "")
            return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a == b)(
                actual, self.expected_value
            )
        return False

    def _evaluate_collision(self, context: Dict[str, Any]) -> bool:
        collisions = context.get("collisions", [])
        target = self.target_object
        other = self.parameters.get("other_object")
        for entry in collisions:
            a = entry.get("object_a")
            b = entry.get("object_b")
            if (a == target and b == other) or (a == other and b == target):
                return True
        return False

    def _evaluate_timer(self, context: Dict[str, Any]) -> bool:
        timers = context.get("timers", {})
        timer_name = self.parameters.get("timer_name", self.target_object)
        threshold = self.expected_value
        if timer_name and timer_name in timers:
            actual = timers[timer_name]
            if threshold is not None:
                return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a >= b)(
                    actual, threshold
                )
            return True
        return False

    def _evaluate_comparison(self, context: Dict[str, Any]) -> bool:
        lhs = self.parameters.get("left_value", 0)
        rhs = self.parameters.get("right_value", self.expected_value)
        return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a == b)(lhs, rhs)

    def _evaluate_variable(self, context: Dict[str, Any]) -> bool:
        variables = context.get("variables", {})
        var_name = self.parameters.get("variable_name", self.target_object)
        actual = variables.get(var_name) if var_name else None
        if actual is None:
            return self.operator == "neq"
        if self.expected_value is not None:
            return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a == b)(
                actual, self.expected_value
            )
        return True

    def _evaluate_trigger(self, context: Dict[str, Any]) -> bool:
        fired_triggers = context.get("fired_triggers", [])
        trigger_name = self.parameters.get("trigger_name", self.target_object)
        return trigger_name in fired_triggers

    def _evaluate_distance(self, context: Dict[str, Any]) -> bool:
        objects = context.get("objects", {})
        obj_a = objects.get(self.target_object) if self.target_object else None
        obj_b_name = self.parameters.get("other_object")
        obj_b = objects.get(obj_b_name) if obj_b_name else None
        if obj_a is None or obj_b is None:
            return False
        ax = obj_a.get("x", 0.0)
        ay = obj_a.get("y", 0.0)
        bx = obj_b.get("x", 0.0)
        by = obj_b.get("y", 0.0)
        dist = ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
        threshold = self.parameters.get("distance", self.expected_value)
        if threshold is not None:
            return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a <= b)(
                dist, float(threshold)
            )
        return True

    def _evaluate_state(self, context: Dict[str, Any]) -> bool:
        obj = self._resolve_value(context)
        if not obj:
            return False
        state_key = self.parameters.get("state_key", "state")
        actual = obj.get(state_key)
        return OPERATOR_FUNCTIONS.get(self.operator, lambda a, b: a == b)(
            actual, self.expected_value
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "condition_type": self.condition_type,
            "target_object": self.target_object,
            "operator": self.operator,
            "expected_value": self.expected_value,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventCondition:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            condition_type=data.get("condition_type", ConditionType.ALWAYS.value),
            target_object=data.get("target_object"),
            operator=data.get("operator", "eq"),
            expected_value=data.get("expected_value"),
            parameters=data.get("parameters", {}),
        )


@dataclass
class EventAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: str = ActionType.SET_VARIABLE.value
    target_object: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        at = self.action_type
        result = {
            "action_id": self.id,
            "action_type": at,
            "target": self.target_object,
            "status": "executed",
        }

        if at == ActionType.MOVE.value:
            result.update(self._execute_move(context))
        elif at == ActionType.ROTATE.value:
            result["detail"] = self._update_object_property(context, "rotation", "add")
        elif at == ActionType.SCALE.value:
            result["detail"] = self._update_object_property(context, "scale", "multiply")
        elif at == ActionType.SPAWN.value:
            result["spawned"] = self._execute_spawn(context)
        elif at == ActionType.DESTROY.value:
            result["destroyed"] = self._execute_destroy(context)
        elif at == ActionType.PLAY_SOUND.value:
            result["sound"] = self.parameters.get("sound_id", "")
        elif at == ActionType.CHANGE_SCENE.value:
            result["scene"] = self.parameters.get("scene_name", "")
        elif at == ActionType.SET_VARIABLE.value:
            result["variable"] = self._execute_set_variable(context)
        elif at == ActionType.EMIT_SIGNAL.value:
            result["signal"] = self.parameters.get("signal_name", "")
        elif at == ActionType.ANIMATE.value:
            result["animation"] = self.parameters.get("animation_name", "")
        elif at == ActionType.APPLY_FORCE.value:
            result["force"] = self._execute_apply_force(context)
        elif at == ActionType.TELEPORT.value:
            result["detail"] = self._execute_teleport(context)
        elif at == ActionType.TOGGLE_VISIBILITY.value:
            result["detail"] = self._execute_toggle_visibility(context)
        elif at == ActionType.SET_TEXT.value:
            result["text"] = self.parameters.get("text", "")
        elif at == ActionType.SET_COLOR.value:
            result["color"] = self._execute_set_color(context)

        return result

    def _get_target(self, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        objects = context.get("objects", {})
        return objects.get(self.target_object) if self.target_object else None

    def _update_object_property(
        self, context: Dict[str, Any], prop: str, mode: str
    ) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"updated": False, "reason": "target not found"}
        value = self.parameters.get("value", 0)
        current = obj.get(prop, 0)
        if mode == "add":
            obj[prop] = current + value
        elif mode == "multiply":
            obj[prop] = current * value
        else:
            obj[prop] = value
        return {"updated": True, prop: obj[prop]}

    def _execute_move(self, context: Dict[str, Any]) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"updated": False, "reason": "target not found"}
        dx = self.parameters.get("dx", 0)
        dy = self.parameters.get("dy", 0)
        dz = self.parameters.get("dz", 0)
        obj["x"] = obj.get("x", 0) + dx
        obj["y"] = obj.get("y", 0) + dy
        obj["z"] = obj.get("z", 0) + dz
        return {"updated": True, "position": (obj["x"], obj["y"], obj["z"])}

    def _execute_spawn(self, context: Dict[str, Any]) -> Optional[str]:
        objects = context.setdefault("objects", {})
        template = self.parameters.get("template", "default")
        spawn_id = uuid.uuid4().hex
        x = self.parameters.get("x", 0)
        y = self.parameters.get("y", 0)
        objects[spawn_id] = {
            "id": spawn_id,
            "template": template,
            "x": x,
            "y": y,
            "z": 0,
            "state": "active",
            "visible": True,
        }
        return spawn_id

    def _execute_destroy(self, context: Dict[str, Any]) -> Optional[str]:
        objects = context.get("objects", {})
        target = self.target_object
        if target and target in objects:
            del objects[target]
            return target
        return None

    def _execute_set_variable(self, context: Dict[str, Any]) -> Dict[str, Any]:
        variables = context.setdefault("variables", {})
        var_name = self.parameters.get("variable_name", self.target_object)
        value = self.parameters.get("value", 0)
        operation = self.parameters.get("operation", "set")
        if var_name:
            if operation == "add":
                variables[var_name] = variables.get(var_name, 0) + value
            elif operation == "subtract":
                variables[var_name] = variables.get(var_name, 0) - value
            elif operation == "toggle":
                variables[var_name] = not variables.get(var_name, False)
            else:
                variables[var_name] = value
            return {"name": var_name, "value": variables[var_name], "operation": operation}
        return {"name": None, "value": None, "operation": operation}

    def _execute_apply_force(self, context: Dict[str, Any]) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"applied": False}
        fx = self.parameters.get("fx", 0)
        fy = self.parameters.get("fy", 0)
        fz = self.parameters.get("fz", 0)
        forces = obj.setdefault("forces", [])
        forces.append({"fx": fx, "fy": fy, "fz": fz})
        return {"applied": True, "force": (fx, fy, fz)}

    def _execute_teleport(self, context: Dict[str, Any]) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"teleported": False}
        obj["x"] = self.parameters.get("x", obj.get("x", 0))
        obj["y"] = self.parameters.get("y", obj.get("y", 0))
        obj["z"] = self.parameters.get("z", obj.get("z", 0))
        return {"teleported": True, "position": (obj["x"], obj["y"], obj["z"])}

    def _execute_toggle_visibility(self, context: Dict[str, Any]) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"toggled": False}
        current = obj.get("visible", True)
        obj["visible"] = not current
        return {"toggled": True, "visible": obj["visible"]}

    def _execute_set_color(self, context: Dict[str, Any]) -> Dict[str, Any]:
        obj = self._get_target(context)
        if obj is None:
            return {"set": False}
        r = self.parameters.get("r", 255)
        g = self.parameters.get("g", 255)
        b = self.parameters.get("b", 255)
        a = self.parameters.get("a", 255)
        obj["color"] = (r, g, b, a)
        return {"set": True, "color": obj["color"]}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type,
            "target_object": self.target_object,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventAction:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            action_type=data.get("action_type", ActionType.SET_VARIABLE.value),
            target_object=data.get("target_object"),
            parameters=data.get("parameters", {}),
        )


@dataclass
class EventSheet:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    events: List[str] = field(default_factory=list)
    description: str = ""
    is_enabled: bool = True
    priority: int = 0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "events": self.events,
            "description": self.description,
            "is_enabled": self.is_enabled,
            "priority": self.priority,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventSheet:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            events=data.get("events", []),
            description=data.get("description", ""),
            is_enabled=data.get("is_enabled", True),
            priority=data.get("priority", 0),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class GameEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sheet_id: str = ""
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    sub_events: List[str] = field(default_factory=list)
    is_enabled: bool = True
    repeat_mode: str = RepeatMode.ONCE.value
    trigger_count: int = 0
    max_triggers: int = -1
    created_at: float = field(default_factory=time.time)

    def _has_fired(self) -> bool:
        if self.repeat_mode == RepeatMode.ONCE.value:
            return self.trigger_count > 0
        if self.repeat_mode == RepeatMode.COUNTED.value:
            return self.max_triggers > 0 and self.trigger_count >= self.max_triggers
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sheet_id": self.sheet_id,
            "conditions": [c.to_dict() for c in self.conditions],
            "actions": [a.to_dict() for a in self.actions],
            "sub_events": self.sub_events,
            "is_enabled": self.is_enabled,
            "repeat_mode": self.repeat_mode,
            "trigger_count": self.trigger_count,
            "max_triggers": self.max_triggers,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GameEvent:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            sheet_id=data.get("sheet_id", ""),
            conditions=[EventCondition.from_dict(c) for c in data.get("conditions", [])],
            actions=[EventAction.from_dict(a) for a in data.get("actions", [])],
            sub_events=data.get("sub_events", []),
            is_enabled=data.get("is_enabled", True),
            repeat_mode=data.get("repeat_mode", RepeatMode.ONCE.value),
            trigger_count=data.get("trigger_count", 0),
            max_triggers=data.get("max_triggers", -1),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class SignalSlot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    signal_name: str = ""
    emitter_node_id: str = ""
    receiver_node_id: str = ""
    slot_method: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_connected: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "signal_name": self.signal_name,
            "emitter_node_id": self.emitter_node_id,
            "receiver_node_id": self.receiver_node_id,
            "slot_method": self.slot_method,
            "parameters": self.parameters,
            "is_connected": self.is_connected,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SignalSlot:
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            signal_name=data.get("signal_name", ""),
            emitter_node_id=data.get("emitter_node_id", ""),
            receiver_node_id=data.get("receiver_node_id", ""),
            slot_method=data.get("slot_method", ""),
            parameters=data.get("parameters", {}),
            is_connected=data.get("is_connected", True),
        )


class EventSystem:
    """
    Event sheet and signal/slot engine for game behavior programming.

    Manages event sheets (ordered condition-action lists evaluated
    each frame) and signal connections (decoupled node-to-node
    communication). Integrates both GDevelop-style visual scripting
    and Godot-style observer patterns into one system.

    Usage:
        es = EventSystem.get_instance()
        sid = es.create_sheet("player_logic")
        es.add_event(sid, [condition1], [action1], RepeatMode.ONCE.value)
        results = es.evaluate_sheet(sid, context)
        cid = es.connect_signal("node_a", "health_zero", "node_b", "on_death")
        es.emit_signal("node_a", "health_zero", {"hp": 0})
    """

    _instance: Optional["EventSystem"] = None
    _lock: threading.RLock = threading.RLock()

    @classmethod
    def get_instance(cls) -> EventSystem:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._sheets: Dict[str, EventSheet] = {}
        self._events: Dict[str, GameEvent] = {}
        self._signals: Dict[str, SignalSlot] = {}
        self._event_count: int = 0
        self._sheet_count: int = 0
        self._trigger_log: List[Dict[str, Any]] = []
        self._signal_count: int = 0
        self._pending_signal_queue: List[Dict[str, Any]] = []
        self._seed_templates()

    # ------------------------------------------------------------------
    # Sheet Management
    # ------------------------------------------------------------------

    def create_sheet(
        self,
        name: str,
        description: str = "",
        priority: int = 0,
    ) -> str:
        with self._lock:
            sheet = EventSheet(
                name=name,
                description=description,
                priority=priority,
            )
            self._sheets[sheet.id] = sheet
            self._sheet_count = len(self._sheets)
            return sheet.id

    def get_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        return self._sheets.get(sheet_id)

    def delete_sheet(self, sheet_id: str) -> bool:
        with self._lock:
            sheet = self._sheets.pop(sheet_id, None)
            if sheet is None:
                return False
            for event_id in sheet.events:
                event = self._events.pop(event_id, None)
                if event:
                    self._event_count = max(0, self._event_count - 1)
                    for sub_id in event.sub_events:
                        self._events.pop(sub_id, None)
                        self._event_count = max(0, self._event_count - 1)
            self._sheet_count = len(self._sheets)
            return True

    # ------------------------------------------------------------------
    # Event Management
    # ------------------------------------------------------------------

    def add_event(
        self,
        sheet_id: str,
        conditions: List[EventCondition],
        actions: List[EventAction],
        repeat_mode: str = RepeatMode.ONCE.value,
        max_triggers: int = -1,
    ) -> Optional[str]:
        with self._lock:
            sheet = self._sheets.get(sheet_id)
            if sheet is None:
                return None
            event = GameEvent(
                sheet_id=sheet_id,
                conditions=conditions,
                actions=actions,
                repeat_mode=repeat_mode,
                max_triggers=max_triggers,
            )
            self._events[event.id] = event
            sheet.events.append(event.id)
            self._event_count = len(self._events)
            return event.id

    def add_sub_event(
        self,
        parent_event_id: str,
        conditions: List[EventCondition],
        actions: List[EventAction],
        repeat_mode: str = RepeatMode.ONCE.value,
    ) -> Optional[str]:
        with self._lock:
            parent = self._events.get(parent_event_id)
            if parent is None:
                return None
            child = GameEvent(
                sheet_id=parent.sheet_id,
                conditions=conditions,
                actions=actions,
                repeat_mode=repeat_mode,
            )
            self._events[child.id] = child
            parent.sub_events.append(child.id)
            self._event_count = len(self._events)
            return child.id

    def add_condition(
        self,
        event_id: str,
        condition_type: str,
        target_object: Optional[str] = None,
        operator: str = "eq",
        expected_value: Any = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            cond = EventCondition(
                condition_type=condition_type,
                target_object=target_object,
                operator=operator,
                expected_value=expected_value,
                parameters=parameters or {},
            )
            event.conditions.append(cond)
            return cond.id

    def add_action(
        self,
        event_id: str,
        action_type: str,
        target_object: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        with self._lock:
            event = self._events.get(event_id)
            if event is None:
                return None
            action = EventAction(
                action_type=action_type,
                target_object=target_object,
                parameters=parameters or {},
            )
            event.actions.append(action)
            return action.id

    def get_event(self, event_id: str) -> Optional[GameEvent]:
        return self._events.get(event_id)

    def remove_event(self, event_id: str) -> bool:
        with self._lock:
            event = self._events.pop(event_id, None)
            if event is None:
                return False
            sheet = self._sheets.get(event.sheet_id)
            if sheet and event_id in sheet.events:
                sheet.events.remove(event_id)
            for sub_id in event.sub_events:
                self._events.pop(sub_id, None)
            self._event_count = len(self._events)
            return True

    # ------------------------------------------------------------------
    # Evaluation and Execution
    # ------------------------------------------------------------------

    def evaluate_event(self, event_id: str, context: Dict[str, Any]) -> bool:
        event = self._events.get(event_id)
        if event is None or not event.is_enabled:
            return False
        if event._has_fired():
            return False
        if not event.conditions:
            return True
        return all(cond.evaluate(context) for cond in event.conditions)

    def execute_event(
        self, event_id: str, context: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        if not self.evaluate_event(event_id, context):
            return None
        event = self._events.get(event_id)
        if event is None:
            return None

        results: List[Dict[str, Any]] = []
        for action in event.actions:
            result = action.execute(context)
            results.append(result)

        event.trigger_count += 1
        self._log_trigger(event_id, event.sheet_id, results)

        for sub_event_id in event.sub_events:
            sub_result = self.execute_event(sub_event_id, context)
            if sub_result:
                results.append({"sub_event": sub_event_id, "result": sub_result})

        return {
            "event_id": event_id,
            "trigger_count": event.trigger_count,
            "action_results": results,
        }

    def evaluate_sheet(
        self, sheet_id: str, context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None or not sheet.is_enabled:
            return []

        ordered = sorted(
            sheet.events,
            key=lambda eid: sheet.priority,
        )

        results: List[Dict[str, Any]] = []
        for event_id in ordered:
            result = self.execute_event(event_id, context)
            if result:
                results.append(result)
        return results

    # ------------------------------------------------------------------
    # Signal / Slot Communication
    # ------------------------------------------------------------------

    def connect_signal(
        self,
        emitter_id: str,
        signal_name: str,
        receiver_id: str,
        slot_method: str,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        with self._lock:
            slot = SignalSlot(
                signal_name=signal_name,
                emitter_node_id=emitter_id,
                receiver_node_id=receiver_id,
                slot_method=slot_method,
                parameters=parameters or {},
            )
            self._signals[slot.id] = slot
            self._signal_count = len(self._signals)
            return slot.id

    def emit_signal(
        self,
        emitter_id: str,
        signal_name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        dispatches: List[Dict[str, Any]] = []
        for slot in self._signals.values():
            if (
                slot.is_connected
                and slot.emitter_node_id == emitter_id
                and slot.signal_name == signal_name
            ):
                dispatch = {
                    "signal_id": slot.id,
                    "receiver": slot.receiver_node_id,
                    "method": slot.slot_method,
                    "data": data or {},
                    "timestamp": time.time(),
                }
                dispatches.append(dispatch)
                self._pending_signal_queue.append(dispatch)
        return dispatches

    def disconnect_signal(self, signal_id: str) -> bool:
        with self._lock:
            slot = self._signals.pop(signal_id, None)
            if slot is not None:
                self._signal_count = len(self._signals)
                return True
            return False

    def get_signal(self, signal_id: str) -> Optional[SignalSlot]:
        return self._signals.get(signal_id)

    def flush_signal_queue(self) -> List[Dict[str, Any]]:
        queue = list(self._pending_signal_queue)
        self._pending_signal_queue.clear()
        return queue

    # ------------------------------------------------------------------
    # Logging and Stats
    # ------------------------------------------------------------------

    def _log_trigger(
        self, event_id: str, sheet_id: str, results: List[Dict[str, Any]]
    ) -> None:
        entry = {
            "event_id": event_id,
            "sheet_id": sheet_id,
            "timestamp": time.time(),
            "action_count": len(results),
            "results": results,
        }
        self._trigger_log.append(entry)
        max_log = 200
        if len(self._trigger_log) > max_log:
            self._trigger_log = self._trigger_log[-max_log:]

    def get_execution_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._trigger_log[-limit:]

    def get_stats(self) -> Dict[str, int]:
        return {
            "sheet_count": self._sheet_count,
            "event_count": self._event_count,
            "signal_count": self._signal_count,
            "total_triggers": len(self._trigger_log),
        }

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_sheet(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        event_data = []
        for event_id in sheet.events:
            event = self._events.get(event_id)
            if event:
                event_data.append(event.to_dict())
        return {
            "sheet": sheet.to_dict(),
            "events": event_data,
        }

    def import_sheet(self, data: Dict[str, Any]) -> Optional[str]:
        with self._lock:
            sheet_raw = data.get("sheet", {})
            events_raw = data.get("events", [])

            sheet = EventSheet.from_dict(sheet_raw)
            self._sheets[sheet.id] = sheet
            self._sheet_count = len(self._sheets)

            for evt_raw in events_raw:
                evt = GameEvent.from_dict(evt_raw)
                evt.sheet_id = sheet.id
                self._events[evt.id] = evt
                sheet.events.append(evt.id)
            self._event_count = len(self._events)
            return sheet.id

    # ------------------------------------------------------------------
    # Seeded Templates
    # ------------------------------------------------------------------

    def _seed_templates(self) -> None:
        self._seed_player_movement()
        self._seed_collision_response()
        self._seed_ui_button_click()
        self._seed_timer_spawner()
        self._seed_variable_watcher()

    def _seed_player_movement(self) -> None:
        sid = self.create_sheet(
            name="Player Movement",
            description="Reads input and moves the player character each frame.",
            priority=10,
        )
        right_cond = EventCondition(
            condition_type=ConditionType.INPUT.value,
            target_object=None,
            parameters={"key": "ArrowRight", "state": "pressed"},
        )
        right_action = EventAction(
            action_type=ActionType.MOVE.value,
            target_object="player",
            parameters={"dx": 5, "dy": 0, "dz": 0},
        )
        self.add_event(sid, [right_cond], [right_action], RepeatMode.REPEAT.value)

        left_cond = EventCondition(
            condition_type=ConditionType.INPUT.value,
            target_object=None,
            parameters={"key": "ArrowLeft", "state": "pressed"},
        )
        left_action = EventAction(
            action_type=ActionType.MOVE.value,
            target_object="player",
            parameters={"dx": -5, "dy": 0, "dz": 0},
        )
        self.add_event(sid, [left_cond], [left_action], RepeatMode.REPEAT.value)

        up_cond = EventCondition(
            condition_type=ConditionType.INPUT.value,
            target_object=None,
            parameters={"key": "ArrowUp", "state": "pressed"},
        )
        up_action = EventAction(
            action_type=ActionType.MOVE.value,
            target_object="player",
            parameters={"dx": 0, "dy": -5, "dz": 0},
        )
        self.add_event(sid, [up_cond], [up_action], RepeatMode.REPEAT.value)

        down_cond = EventCondition(
            condition_type=ConditionType.INPUT.value,
            target_object=None,
            parameters={"key": "ArrowDown", "state": "pressed"},
        )
        down_action = EventAction(
            action_type=ActionType.MOVE.value,
            target_object="player",
            parameters={"dx": 0, "dy": 5, "dz": 0},
        )
        self.add_event(sid, [down_cond], [down_action], RepeatMode.REPEAT.value)

    def _seed_collision_response(self) -> None:
        sid = self.create_sheet(
            name="Collision Response",
            description="Destroys projectiles on collision and bounces the player.",
            priority=20,
        )
        bullet_hit_cond = EventCondition(
            condition_type=ConditionType.COLLISION.value,
            target_object="bullet",
            parameters={"other_object": "enemy"},
        )
        bullet_hit_action = EventAction(
            action_type=ActionType.DESTROY.value,
            target_object="bullet",
        )
        self.add_event(
            sid, [bullet_hit_cond], [bullet_hit_action], RepeatMode.REPEAT.value
        )

        enemy_hit_cond = EventCondition(
            condition_type=ConditionType.COLLISION.value,
            target_object="player",
            parameters={"other_object": "enemy"},
        )
        enemy_hit_action = EventAction(
            action_type=ActionType.APPLY_FORCE.value,
            target_object="player",
            parameters={"fx": 0, "fy": -10, "fz": 0},
        )
        self.add_event(
            sid, [enemy_hit_cond], [enemy_hit_action], RepeatMode.REPEAT.value
        )

        enemy_destroy_cond = EventCondition(
            condition_type=ConditionType.COLLISION.value,
            target_object="bullet",
            parameters={"other_object": "boss"},
        )
        enemy_destroy_action = EventAction(
            action_type=ActionType.DESTROY.value,
            target_object="boss",
        )
        self.add_event(
            sid,
            [enemy_destroy_cond],
            [enemy_destroy_action],
            RepeatMode.ONCE.value,
        )

    def _seed_ui_button_click(self) -> None:
        sid = self.create_sheet(
            name="UI Button Click",
            description="Handles UI button triggers to change scenes.",
            priority=5,
        )
        play_cond = EventCondition(
            condition_type=ConditionType.TRIGGER.value,
            target_object=None,
            parameters={"trigger_name": "ui_play_button"},
        )
        play_action = EventAction(
            action_type=ActionType.CHANGE_SCENE.value,
            target_object=None,
            parameters={"scene_name": "level_01"},
        )
        self.add_event(sid, [play_cond], [play_action], RepeatMode.ONCE.value)

        settings_cond = EventCondition(
            condition_type=ConditionType.TRIGGER.value,
            target_object=None,
            parameters={"trigger_name": "ui_settings_button"},
        )
        settings_action = EventAction(
            action_type=ActionType.CHANGE_SCENE.value,
            target_object=None,
            parameters={"scene_name": "settings_menu"},
        )
        self.add_event(sid, [settings_cond], [settings_action], RepeatMode.ONCE.value)

        quit_cond = EventCondition(
            condition_type=ConditionType.TRIGGER.value,
            target_object=None,
            parameters={"trigger_name": "ui_quit_button"},
        )
        quit_action = EventAction(
            action_type=ActionType.CHANGE_SCENE.value,
            target_object=None,
            parameters={"scene_name": "quit"},
        )
        self.add_event(sid, [quit_cond], [quit_action], RepeatMode.ONCE.value)

    def _seed_timer_spawner(self) -> None:
        sid = self.create_sheet(
            name="Timer Spawner",
            description="Spawns enemies on a repeating timer interval.",
            priority=15,
        )
        timer_cond = EventCondition(
            condition_type=ConditionType.TIMER.value,
            target_object=None,
            operator="gte",
            expected_value=3.0,
            parameters={"timer_name": "spawn_timer"},
        )
        spawn_action = EventAction(
            action_type=ActionType.SPAWN.value,
            target_object=None,
            parameters={"template": "enemy_grunt", "x": 800, "y": 200},
        )
        self.add_event(
            sid,
            [timer_cond],
            [spawn_action],
            RepeatMode.REPEAT.value,
        )

    def _seed_variable_watcher(self) -> None:
        sid = self.create_sheet(
            name="Variable Watcher",
            description="Emits a signal when the score variable crosses a threshold.",
            priority=8,
        )
        score_cond = EventCondition(
            condition_type=ConditionType.VARIABLE.value,
            target_object=None,
            operator="gte",
            expected_value=100,
            parameters={"variable_name": "score"},
        )
        signal_action = EventAction(
            action_type=ActionType.EMIT_SIGNAL.value,
            target_object=None,
            parameters={"signal_name": "score_milestone", "data": {"milestone": 100}},
        )
        self.add_event(
            sid,
            [score_cond],
            [signal_action],
            RepeatMode.ONCE.value,
        )

        lives_cond = EventCondition(
            condition_type=ConditionType.VARIABLE.value,
            target_object=None,
            operator="lte",
            expected_value=0,
            parameters={"variable_name": "lives"},
        )
        lives_action = EventAction(
            action_type=ActionType.CHANGE_SCENE.value,
            target_object=None,
            parameters={"scene_name": "game_over"},
        )
        self.add_event(
            sid,
            [lives_cond],
            [lives_action],
            RepeatMode.ONCE.value,
        )


def get_event_system() -> EventSystem:
    return EventSystem.get_instance()