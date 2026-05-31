"""
SparkLabs Engine - Event Scripting System

Event-driven game logic system visual event sheets
and signal system. Enables creators to define game behavior through
declarative event rules composed of conditions and actions, organized into
named event sheets that the runtime evaluates each game tick.

Architecture:
  EventScripting
    |-- EventSheet (named collection of rules with scope and metadata)
    |-- EventRule (condition-to-action mapping with repeat behavior)
    |-- EventCondition (evaluable predicate testing simulated game state)
    |-- EventAction (executable operation mutating game state)

Condition Types:
  - OBJECT_COLLISION: detect overlap between two game objects
  - KEY_PRESSED: check input key or button state
  - VARIABLE_COMPARE: compare numeric or string variables
  - TIMER_EXPIRED: fire when a named timer reaches its interval
  - RAYCAST_HIT: detect ray intersection with objects
  - DISTANCE_CHECK: measure distance between two objects
  - ANIMATION_END: trigger when an animation clip finishes
  - CUSTOM: user-defined condition with custom evaluation

Action Types:
  - MOVE_OBJECT: translate an object by offset or to target position
  - PLAY_SOUND: play an audio asset with optional volume and pitch
  - CHANGE_VARIABLE: assign, increment, decrement, or toggle variables
  - CREATE_OBJECT: instantiate a prefab at a given position
  - DESTROY_OBJECT: remove an object from the scene
  - APPLY_FORCE: apply a physics force vector to an object
  - PLAY_ANIMATION: start an animation clip on a target object
  - TRIGGER_EVENT: fire another event rule by reference
  - SWITCH_SCENE: transition to a different scene
  - SPAWN_PARTICLES: emit a particle burst at a location

Repeat Types:
  - ONCE: fire the rule a single time when conditions are met
  - REPEAT_WHILE_TRUE: keep executing every tick while conditions hold
  - EVERY_FRAME: execute unconditionally every game tick
  - EVERY_N_SECONDS: execute on a fixed time interval while conditions hold

Usage:
    es = get_event_scripting()
    sheet = es.create_event_sheet("player_movement", scope="gameplay")
    rule = es.create_rule("move_right_on_key", sheet.id, RepeatType.REPEAT_WHILE_TRUE)
    es.add_condition(rule.id, ConditionType.KEY_PRESSED, "input", "key", "==", "ArrowRight")
    es.add_action(rule.id, ActionType.MOVE_OBJECT, "player", {"dx": 5, "dy": 0}, order_index=0)
    es.simulate_game_tick(0.016)
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


class ConditionType(Enum):
    OBJECT_COLLISION = "object_collision"
    KEY_PRESSED = "key_pressed"
    VARIABLE_COMPARE = "variable_compare"
    TIMER_EXPIRED = "timer_expired"
    RAYCAST_HIT = "raycast_hit"
    DISTANCE_CHECK = "distance_check"
    ANIMATION_END = "animation_end"
    CUSTOM = "custom"


class ActionType(Enum):
    MOVE_OBJECT = "move_object"
    PLAY_SOUND = "play_sound"
    CHANGE_VARIABLE = "change_variable"
    CREATE_OBJECT = "create_object"
    DESTROY_OBJECT = "destroy_object"
    APPLY_FORCE = "apply_force"
    PLAY_ANIMATION = "play_animation"
    TRIGGER_EVENT = "trigger_event"
    SWITCH_SCENE = "switch_scene"
    SPAWN_PARTICLES = "spawn_particles"
    CUSTOM_ACTION = "custom_action"


class RepeatType(Enum):
    ONCE = "once"
    REPEAT_WHILE_TRUE = "repeat_while_true"
    EVERY_FRAME = "every_frame"
    EVERY_N_SECONDS = "every_n_seconds"


@dataclass
class EventCondition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    condition_type: ConditionType = ConditionType.CUSTOM
    target: str = ""
    property: str = ""
    operator: str = "=="
    value: Any = None
    negate: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "condition_type": self.condition_type.value,
            "target": self.target,
            "property": self.property,
            "operator": self.operator,
            "value": self.value,
            "negate": self.negate,
        }


@dataclass
class EventAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    action_type: ActionType = ActionType.CUSTOM_ACTION
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    order_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_type": self.action_type.value,
            "target": self.target,
            "parameters": self.parameters,
            "order_index": self.order_index,
        }


@dataclass
class EventRule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    conditions: List[EventCondition] = field(default_factory=list)
    actions: List[EventAction] = field(default_factory=list)
    repeat_type: RepeatType = RepeatType.ONCE
    priority: int = 0
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "condition_count": len(self.conditions),
            "action_count": len(self.actions),
            "repeat_type": self.repeat_type.value,
            "priority": self.priority,
            "enabled": self.enabled,
            "tags": self.tags,
            "created_at": self.created_at,
        }


@dataclass
class EventSheet:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    rules: List[EventRule] = field(default_factory=list)
    scope: str = "global"
    description: str = ""
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "rule_count": len(self.rules),
            "scope": self.scope,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


OPERATOR_FUNCTIONS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    ">": lambda a, b: float(a) > float(b),
    "<": lambda a, b: float(a) < float(b),
    ">=": lambda a, b: float(a) >= float(b),
    "<=": lambda a, b: float(a) <= float(b),
    "contains": lambda a, b: str(b) in str(a) if a is not None else False,
    "starts_with": lambda a, b: str(a).startswith(str(b)) if a is not None else False,
    "ends_with": lambda a, b: str(a).endswith(str(b)) if a is not None else False,
}


class EventScripting:
    """
    Event-driven game logic runtime that evaluates declarative event rules
    against a simulated game state and dispatches actions each tick.

    The system models declarative event sheets where each sheet contains
    ordered rules, each rule consists of conditions that must be met and
    actions that execute when they are. Rules support repeat behaviors
    including one-shot, while-true, every-frame, and interval-based firing.

    Usage:
        es = EventScripting.get_instance()
        sheet = es.create_event_sheet("core_loop", scope="gameplay",
                                       description="Main gameplay event sheet")
        rule = es.create_rule("spawn_enemy_wave", sheet.id,
                               RepeatType.ONCE, priority=10,
                               tags=["combat", "spawning"])
        es.add_condition(rule.id, ConditionType.VARIABLE_COMPARE,
                          "enemy_count", "value", "<", 5)
        es.add_action(rule.id, ActionType.CREATE_OBJECT, "enemy_spawner",
                       {"template": "goblin", "x": 100, "y": 200, "count": 3})
        es.simulate_game_tick(0.016)
    """

    _instance: Optional["EventScripting"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_SHEETS = 256
    MAX_RULES_PER_SHEET = 128
    MAX_CONDITIONS_PER_RULE = 32
    MAX_ACTIONS_PER_RULE = 64
    MAX_TIMERS = 128

    def __init__(self):
        self._sheets: Dict[str, EventSheet] = {}
        self._rule_index: Dict[str, EventRule] = {}
        self._condition_index: Dict[str, EventCondition] = {}
        self._action_index: Dict[str, EventAction] = {}
        self._rule_to_sheet: Dict[str, str] = {}
        self._fired_once_rules: Set[str] = set()
        self._rule_last_fired: Dict[str, float] = {}
        self._simulated_game_state: Dict[str, Any] = {
            "variables": {},
            "objects": {},
            "inputs": {},
            "timers": {},
            "collisions": [],
            "raycast_hits": [],
            "animations": {},
            "scene": "main",
            "tick_count": 0,
            "delta_time": 0.0,
        }
        self._total_evaluations: int = 0
        self._total_actions_executed: int = 0
        self._total_ticks_simulated: int = 0
        self._total_rules_triggered: int = 0

    @classmethod
    def get_instance(cls) -> "EventScripting":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Rule Management
    # ------------------------------------------------------------------

    def create_rule(
        self,
        name: str,
        sheet_id: str,
        repeat_type: RepeatType = RepeatType.ONCE,
        priority: int = 0,
        enabled: bool = True,
        tags: Optional[List[str]] = None,
    ) -> Optional[EventRule]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        if len(sheet.rules) >= self.MAX_RULES_PER_SHEET:
            return None

        rule = EventRule(
            name=name,
            repeat_type=repeat_type,
            priority=priority,
            enabled=enabled,
            tags=tags or [],
        )
        sheet.rules.append(rule)
        sheet.updated_at = _time_module.time()
        self._rule_index[rule.id] = rule
        self._rule_to_sheet[rule.id] = sheet_id
        return rule

    def get_rule(self, rule_id: str) -> Optional[EventRule]:
        return self._rule_index.get(rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        rule = self._rule_index.pop(rule_id, None)
        if rule is None:
            return False
        sheet_id = self._rule_to_sheet.pop(rule_id, None)
        if sheet_id and sheet_id in self._sheets:
            self._sheets[sheet_id].rules = [
                r for r in self._sheets[sheet_id].rules if r.id != rule_id
            ]
            self._sheets[sheet_id].updated_at = _time_module.time()
        for cond in rule.conditions:
            self._condition_index.pop(cond.id, None)
        for act in rule.actions:
            self._action_index.pop(act.id, None)
        self._fired_once_rules.discard(rule_id)
        self._rule_last_fired.pop(rule_id, None)
        return True

    def set_rule_enabled(self, rule_id: str, enabled: bool) -> bool:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return False
        rule.enabled = enabled
        return True

    def set_rule_repeat_type(self, rule_id: str, repeat_type: RepeatType) -> bool:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return False
        rule.repeat_type = repeat_type
        return True

    def set_rule_priority(self, rule_id: str, priority: int) -> bool:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return False
        rule.priority = priority
        return True

    def add_rule_tag(self, rule_id: str, tag: str) -> bool:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return False
        if tag not in rule.tags:
            rule.tags.append(tag)
        return True

    def remove_rule_tag(self, rule_id: str, tag: str) -> bool:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return False
        if tag in rule.tags:
            rule.tags.remove(tag)
            return True
        return False

    # ------------------------------------------------------------------
    # Event Sheet Management
    # ------------------------------------------------------------------

    def create_event_sheet(
        self,
        name: str,
        scope: str = "global",
        description: str = "",
    ) -> Optional[EventSheet]:
        if len(self._sheets) >= self.MAX_SHEETS:
            return None
        now = _time_module.time()
        sheet = EventSheet(
            name=name,
            scope=scope,
            description=description,
            created_at=now,
            updated_at=now,
        )
        self._sheets[sheet.id] = sheet
        return sheet

    def get_event_sheet(self, sheet_id: str) -> Optional[EventSheet]:
        return self._sheets.get(sheet_id)

    def list_event_sheets(self, scope: Optional[str] = None) -> List[EventSheet]:
        sheets = list(self._sheets.values())
        if scope is not None:
            sheets = [s for s in sheets if s.scope == scope]
        return sheets

    def remove_event_sheet(self, sheet_id: str) -> bool:
        sheet = self._sheets.pop(sheet_id, None)
        if sheet is None:
            return False
        for rule in sheet.rules:
            self._rule_index.pop(rule.id, None)
            self._rule_to_sheet.pop(rule.id, None)
            self._fired_once_rules.discard(rule.id)
            self._rule_last_fired.pop(rule.id, None)
            for cond in rule.conditions:
                self._condition_index.pop(cond.id, None)
            for act in rule.actions:
                self._action_index.pop(act.id, None)
        return True

    # ------------------------------------------------------------------
    # Condition Management
    # ------------------------------------------------------------------

    def add_condition(
        self,
        rule_id: str,
        condition_type: ConditionType,
        target: str,
        property: str,
        operator: str,
        value: Any,
        negate: bool = False,
    ) -> Optional[EventCondition]:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return None
        if len(rule.conditions) >= self.MAX_CONDITIONS_PER_RULE:
            return None
        condition = EventCondition(
            condition_type=condition_type,
            target=target,
            property=property,
            operator=operator,
            value=value,
            negate=negate,
        )
        rule.conditions.append(condition)
        self._condition_index[condition.id] = condition
        return condition

    def remove_condition(self, condition_id: str) -> bool:
        condition = self._condition_index.pop(condition_id, None)
        if condition is None:
            return False
        for rule in self._rule_index.values():
            if condition in rule.conditions:
                rule.conditions.remove(condition)
                return True
        return False

    # ------------------------------------------------------------------
    # Action Management
    # ------------------------------------------------------------------

    def add_action(
        self,
        rule_id: str,
        action_type: ActionType,
        target: str,
        parameters: Optional[Dict[str, Any]] = None,
        order_index: Optional[int] = None,
    ) -> Optional[EventAction]:
        rule = self._rule_index.get(rule_id)
        if rule is None:
            return None
        if len(rule.actions) >= self.MAX_ACTIONS_PER_RULE:
            return None
        idx = order_index if order_index is not None else len(rule.actions)
        action = EventAction(
            action_type=action_type,
            target=target,
            parameters=parameters or {},
            order_index=idx,
        )
        rule.actions.append(action)
        self._action_index[action.id] = action
        return action

    def remove_action(self, action_id: str) -> bool:
        action = self._action_index.pop(action_id, None)
        if action is None:
            return False
        for rule in self._rule_index.values():
            if action in rule.actions:
                rule.actions.remove(action)
                return True
        return False

    # ------------------------------------------------------------------
    # Simulated Game State Helpers
    # ------------------------------------------------------------------

    def set_variable(self, name: str, value: Any) -> None:
        self._simulated_game_state["variables"][name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        return self._simulated_game_state["variables"].get(name, default)

    def set_input(self, key: str, pressed: bool) -> None:
        self._simulated_game_state["inputs"][key] = pressed

    def set_timer(self, name: str, interval: float) -> None:
        self._simulated_game_state["timers"][name] = {
            "elapsed": 0.0,
            "interval": interval,
            "active": True,
        }

    def reset_timer(self, name: str) -> None:
        timer = self._simulated_game_state["timers"].get(name)
        if timer:
            timer["elapsed"] = 0.0
            timer["active"] = True

    def set_object_position(self, obj_id: str, x: float, y: float) -> None:
        if obj_id not in self._simulated_game_state["objects"]:
            self._simulated_game_state["objects"][obj_id] = {}
        self._simulated_game_state["objects"][obj_id]["x"] = x
        self._simulated_game_state["objects"][obj_id]["y"] = y

    def add_collision(self, obj_a: str, obj_b: str) -> None:
        pair = tuple(sorted([obj_a, obj_b]))
        if pair not in self._simulated_game_state["collisions"]:
            self._simulated_game_state["collisions"].append(pair)

    def clear_collisions(self) -> None:
        self._simulated_game_state["collisions"].clear()

    def add_raycast_hit(self, origin: str, hit_object: str) -> None:
        self._simulated_game_state["raycast_hits"].append({
            "origin": origin,
            "hit_object": hit_object,
        })

    def clear_raycast_hits(self) -> None:
        self._simulated_game_state["raycast_hits"].clear()

    def set_animation_state(self, obj_id: str, state: str, ended: bool = False) -> None:
        self._simulated_game_state["animations"][obj_id] = {
            "state": state,
            "ended": ended,
        }

    def set_scene(self, scene_name: str) -> None:
        self._simulated_game_state["scene"] = scene_name

    # ------------------------------------------------------------------
    # Condition Evaluation
    # ------------------------------------------------------------------

    def evaluate_conditions(
        self,
        conditions: List[EventCondition],
    ) -> bool:
        if not conditions:
            return True
        state = self._simulated_game_state
        for condition in conditions:
            raw_result = self._evaluate_single_condition(condition, state)
            result = not raw_result if condition.negate else raw_result
            if not result:
                return False
        self._total_evaluations += 1
        return True

    def _evaluate_single_condition(
        self,
        condition: EventCondition,
        state: Dict[str, Any],
    ) -> bool:
        ct = condition.condition_type

        if ct == ConditionType.OBJECT_COLLISION:
            target_parts = condition.target.split(",") if condition.target else []
            if len(target_parts) >= 2:
                pair = tuple(sorted(target_parts[:2]))
                return pair in state.get("collisions", [])
            return condition.target in str(state.get("collisions", []))

        if ct == ConditionType.KEY_PRESSED:
            inputs = state.get("inputs", {})
            key = condition.target if condition.target else condition.property
            return inputs.get(key, False)

        if ct == ConditionType.VARIABLE_COMPARE:
            variables = state.get("variables", {})
            actual = variables.get(condition.target, 0)
            return self._apply_operator(actual, condition.operator, condition.value)

        if ct == ConditionType.TIMER_EXPIRED:
            timers = state.get("timers", {})
            timer = timers.get(condition.target, {})
            elapsed = timer.get("elapsed", 0.0)
            interval = timer.get("interval", 0.0)
            if interval <= 0:
                return False
            return elapsed >= interval

        if ct == ConditionType.RAYCAST_HIT:
            hits = state.get("raycast_hits", [])
            for hit in hits:
                if hit.get("origin") == condition.target and hit.get("hit_object") == condition.value:
                    return True
            return False

        if ct == ConditionType.DISTANCE_CHECK:
            objects = state.get("objects", {})
            parts = condition.target.split(",") if condition.target else []
            if len(parts) < 2:
                return False
            obj_a = objects.get(parts[0].strip())
            obj_b = objects.get(parts[1].strip())
            if obj_a is None or obj_b is None:
                return False
            ax = obj_a.get("x", 0.0)
            ay = obj_a.get("y", 0.0)
            bx = obj_b.get("x", 0.0)
            by = obj_b.get("y", 0.0)
            distance = ((bx - ax) ** 2 + (by - ay) ** 2) ** 0.5
            return self._apply_operator(distance, condition.operator, condition.value)

        if ct == ConditionType.ANIMATION_END:
            animations = state.get("animations", {})
            anim = animations.get(condition.target)
            if anim is None:
                return False
            return anim.get("ended", False)

        if ct == ConditionType.CUSTOM:
            return True

        return False

    def _apply_operator(self, actual: Any, operator: str, expected: Any) -> bool:
        func = OPERATOR_FUNCTIONS.get(operator)
        if func is None:
            return False
        try:
            return func(actual, expected)
        except (ValueError, TypeError):
            return False

    # ------------------------------------------------------------------
    # Action Execution
    # ------------------------------------------------------------------

    def execute_actions(
        self,
        actions: List[EventAction],
    ) -> int:
        sorted_actions = sorted(actions, key=lambda a: a.order_index)
        dispatched = 0
        for action in sorted_actions:
            self._dispatch_single_action(action)
            dispatched += 1
        self._total_actions_executed += dispatched
        return dispatched

    def _dispatch_single_action(self, action: EventAction) -> None:
        at = action.action_type
        params = action.parameters
        target = action.target
        state = self._simulated_game_state

        if at == ActionType.MOVE_OBJECT:
            obj = state["objects"].get(target)
            if obj is None:
                state["objects"][target] = {"x": 0.0, "y": 0.0}
                obj = state["objects"][target]
            dx = params.get("dx", 0)
            dy = params.get("dy", 0)
            if "x_target" in params and "y_target" in params:
                obj["x"] = params["x_target"]
                obj["y"] = params["y_target"]
            else:
                obj["x"] = obj.get("x", 0.0) + dx
                obj["y"] = obj.get("y", 0.0) + dy

        elif at == ActionType.PLAY_SOUND:
            sound_name = target if target else params.get("sound", "")
            volume = params.get("volume", 1.0)
            pitch = params.get("pitch", 1.0)
            state.setdefault("audio_events", []).append({
                "sound": sound_name,
                "volume": volume,
                "pitch": pitch,
            })

        elif at == ActionType.CHANGE_VARIABLE:
            var_name = target
            operation = params.get("operation", "set")
            value = params.get("value", 0)
            variables = state["variables"]
            if operation == "set":
                variables[var_name] = value
            elif operation == "add":
                variables[var_name] = variables.get(var_name, 0) + value
            elif operation == "subtract":
                variables[var_name] = variables.get(var_name, 0) - value
            elif operation == "multiply":
                variables[var_name] = variables.get(var_name, 0) * value
            elif operation == "toggle":
                variables[var_name] = not variables.get(var_name, False)

        elif at == ActionType.CREATE_OBJECT:
            template = params.get("template", target)
            x = params.get("x", 0)
            y = params.get("y", 0)
            count = params.get("count", 1)
            for i in range(count):
                obj_id = f"{template}_{uuid.uuid4().hex[:6]}"
                state["objects"][obj_id] = {
                    "template": template,
                    "x": x + (i * params.get("spacing_x", 50)),
                    "y": y + (i * params.get("spacing_y", 0)),
                    "created_at": state["tick_count"],
                }

        elif at == ActionType.DESTROY_OBJECT:
            obj_id = target
            if obj_id in state["objects"]:
                del state["objects"][obj_id]
            elif params.get("by_template"):
                to_remove = [
                    oid for oid, obj in state["objects"].items()
                    if obj.get("template") == params["by_template"]
                ]
                for oid in to_remove:
                    del state["objects"][oid]

        elif at == ActionType.APPLY_FORCE:
            obj = state["objects"].get(target)
            if obj is not None:
                fx = params.get("fx", 0)
                fy = params.get("fy", 0)
                obj["vx"] = obj.get("vx", 0.0) + fx
                obj["vy"] = obj.get("vy", 0.0) + fy

        elif at == ActionType.PLAY_ANIMATION:
            anim_name = params.get("animation", "default")
            loop = params.get("loop", False)
            state["animations"][target] = {
                "state": anim_name,
                "loop": loop,
                "ended": False,
                "started_at": state["tick_count"],
            }

        elif at == ActionType.TRIGGER_EVENT:
            triggered_rule_id = target
            triggered_rule = self._rule_index.get(triggered_rule_id)
            if triggered_rule and triggered_rule.enabled:
                if self.evaluate_conditions(triggered_rule.conditions):
                    self.execute_actions(triggered_rule.actions)

        elif at == ActionType.SWITCH_SCENE:
            scene_name = target if target else params.get("scene", "")
            state["scene"] = scene_name
            state.setdefault("scene_transitions", []).append({
                "to": scene_name,
                "at_tick": state["tick_count"],
            })

        elif at == ActionType.SPAWN_PARTICLES:
            effect = params.get("effect", target)
            x = params.get("x", 0)
            y = params.get("y", 0)
            count = params.get("count", 10)
            state.setdefault("particle_events", []).append({
                "effect": effect,
                "x": x,
                "y": y,
                "count": count,
                "at_tick": state["tick_count"],
            })

        elif at == ActionType.CUSTOM_ACTION:
            pass

    # ------------------------------------------------------------------
    # Event Sheet Evaluation
    # ------------------------------------------------------------------

    def process_event_sheet(
        self,
        sheet_id: str,
    ) -> Dict[str, Any]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return {"success": False, "error": "Sheet not found", "sheet_id": sheet_id}

        state = self._simulated_game_state
        dt = state.get("delta_time", 0.016)
        rules_triggered: List[str] = []
        total_actions_dispatched = 0

        sorted_rules = sorted(sheet.rules, key=lambda r: r.priority, reverse=True)

        for rule in sorted_rules:
            if not rule.enabled:
                continue

            should_execute = self._determine_should_execute(rule, dt)
            if not should_execute:
                continue

            conditions_met = (rule.repeat_type == RepeatType.EVERY_FRAME) or self.evaluate_conditions(rule.conditions)

            if not conditions_met:
                continue

            self._rule_last_fired[rule.id] = state["tick_count"]
            dispatched = self.execute_actions(rule.actions)
            total_actions_dispatched += dispatched
            rules_triggered.append(rule.id)
            self._total_rules_triggered += 1

            if rule.repeat_type == RepeatType.ONCE:
                self._fired_once_rules.add(rule.id)

        sheet.updated_at = _time_module.time()

        return {
            "success": True,
            "sheet_id": sheet_id,
            "sheet_name": sheet.name,
            "rules_evaluated": len(sorted_rules),
            "rules_triggered": len(rules_triggered),
            "triggered_rule_ids": rules_triggered,
            "total_actions_dispatched": total_actions_dispatched,
        }

    def _determine_should_execute(self, rule: EventRule, dt: float) -> bool:
        if rule.repeat_type == RepeatType.ONCE:
            if rule.id in self._fired_once_rules:
                return False

        if rule.repeat_type == RepeatType.EVERY_N_SECONDS:
            interval = float(rule.conditions[0].value) if rule.conditions else 0.5
            last_fired = self._rule_last_fired.get(rule.id, -interval)
            ticks_since = self._simulated_game_state["tick_count"] - last_fired
            if ticks_since * dt < interval:
                return False

        return True

    # ------------------------------------------------------------------
    # Game Tick Simulation
    # ------------------------------------------------------------------

    def simulate_game_tick(
        self,
        delta_time: float = 0.016,
        active_sheet_ids: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        state = self._simulated_game_state
        state["delta_time"] = delta_time
        state["tick_count"] += 1

        for timer in state["timers"].values():
            if timer.get("active", False):
                timer["elapsed"] = timer.get("elapsed", 0.0) + delta_time

        state.setdefault("audio_events", []).clear()
        state.setdefault("particle_events", []).clear()

        results: List[Dict[str, Any]] = []

        sheet_ids = active_sheet_ids if active_sheet_ids is not None else list(self._sheets.keys())

        for sheet_id in sheet_ids:
            result = self.process_event_sheet(sheet_id)
            results.append(result)

        self._total_ticks_simulated += 1

        return {
            "tick": state["tick_count"],
            "delta_time": delta_time,
            "sheets_processed": len(results),
            "sheet_results": results,
            "total_rules_triggered": self._total_rules_triggered,
            "total_objects": len(state["objects"]),
            "total_variables": len(state["variables"]),
            "active_timers": sum(1 for t in state["timers"].values() if t.get("active")),
        }

    # ------------------------------------------------------------------
    # Rule Optimization
    # ------------------------------------------------------------------

    def optimize_event_sheets(
        self,
        sheet_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sheets_to_optimize: List[EventSheet]
        if sheet_id is not None:
            sheet = self._sheets.get(sheet_id)
            if sheet is None:
                return {"success": False, "error": "Sheet not found", "sheet_id": sheet_id}
            sheets_to_optimize = [sheet]
        else:
            sheets_to_optimize = list(self._sheets.values())

        total_reordered = 0
        total_unanchored = 0
        details: List[Dict[str, Any]] = []

        for sheet in sheets_to_optimize:
            before_order = [r.id for r in sheet.rules]
            rules_with_conditions = [r for r in sheet.rules if r.conditions]
            rules_without_conditions = [r for r in sheet.rules if not r.conditions]

            rules_with_conditions.sort(
                key=lambda r: (
                    -r.priority,
                    -len(r.conditions),
                    1 if r.repeat_type == RepeatType.EVERY_FRAME else 0,
                    1 if r.repeat_type == RepeatType.REPEAT_WHILE_TRUE else 0,
                    r.tags,
                )
            )

            rules_without_conditions.sort(
                key=lambda r: (
                    -r.priority,
                    1 if r.repeat_type == RepeatType.EVERY_FRAME else 0,
                    0 if r.repeat_type == RepeatType.ONCE else 1,
                )
            )

            sheet.rules = rules_with_conditions + rules_without_conditions
            after_order = [r.id for r in sheet.rules]
            reordered = sum(1 for i, rid in enumerate(after_order) if before_order[i] != rid if i < len(before_order))

            total_reordered += reordered
            total_unanchored += len(rules_without_conditions)
            details.append({
                "sheet_id": sheet.id,
                "sheet_name": sheet.name,
                "total_rules": len(sheet.rules),
                "rules_reordered": reordered,
                "unanchored_rules": len(rules_without_conditions),
            })

        return {
            "success": True,
            "sheets_optimized": len(sheets_to_optimize),
            "total_rules_reordered": total_reordered,
            "total_unanchored_rules": total_unanchored,
            "details": details,
        }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_scripting_stats(self) -> Dict[str, Any]:
        scope_distribution: Dict[str, int] = {}
        repeat_distribution: Dict[str, int] = {}
        condition_type_distribution: Dict[str, int] = {}
        action_type_distribution: Dict[str, int] = {}
        tag_distribution: Dict[str, int] = {}

        for sheet in self._sheets.values():
            scope = sheet.scope
            scope_distribution[scope] = scope_distribution.get(scope, 0) + 1
            for rule in sheet.rules:
                rt = rule.repeat_type.value
                repeat_distribution[rt] = repeat_distribution.get(rt, 0) + 1
                for tag in rule.tags:
                    tag_distribution[tag] = tag_distribution.get(tag, 0) + 1
                for cond in rule.conditions:
                    ct = cond.condition_type.value
                    condition_type_distribution[ct] = condition_type_distribution.get(ct, 0) + 1
                for act in rule.actions:
                    at = act.action_type.value
                    action_type_distribution[at] = action_type_distribution.get(at, 0) + 1

        total_rules = len(self._rule_index)
        total_conditions = len(self._condition_index)
        total_actions = len(self._action_index)
        total_fired_once = len(self._fired_once_rules)

        rules_without_conditions = sum(
            1 for r in self._rule_index.values() if not r.conditions
        )
        rules_without_actions = sum(
            1 for r in self._rule_index.values() if not r.actions
        )

        avg_conditions = total_conditions / total_rules if total_rules > 0 else 0.0
        avg_actions = total_actions / total_rules if total_rules > 0 else 0.0

        return {
            "total_sheets": len(self._sheets),
            "total_rules": total_rules,
            "total_conditions": total_conditions,
            "total_actions": total_actions,
            "total_fired_once_rules": total_fired_once,
            "rules_without_conditions": rules_without_conditions,
            "rules_without_actions": rules_without_actions,
            "avg_conditions_per_rule": round(avg_conditions, 2),
            "avg_actions_per_rule": round(avg_actions, 2),
            "total_evaluations": self._total_evaluations,
            "total_actions_executed": self._total_actions_executed,
            "total_ticks_simulated": self._total_ticks_simulated,
            "total_rules_triggered": self._total_rules_triggered,
            "scope_distribution": scope_distribution,
            "repeat_distribution": repeat_distribution,
            "condition_type_distribution": condition_type_distribution,
            "action_type_distribution": action_type_distribution,
            "tag_distribution": tag_distribution,
            "limits": {
                "max_sheets": self.MAX_SHEETS,
                "max_rules_per_sheet": self.MAX_RULES_PER_SHEET,
                "max_conditions_per_rule": self.MAX_CONDITIONS_PER_RULE,
                "max_actions_per_rule": self.MAX_ACTIONS_PER_RULE,
                "max_timers": self.MAX_TIMERS,
            },
        }

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_event_sheet(self, sheet_id: str) -> Optional[Dict[str, Any]]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return None
        rules_data = []
        for rule in sheet.rules:
            rules_data.append({
                "name": rule.name,
                "repeat_type": rule.repeat_type.value,
                "priority": rule.priority,
                "enabled": rule.enabled,
                "tags": rule.tags,
                "conditions": [
                    {
                        "condition_type": c.condition_type.value,
                        "target": c.target,
                        "property": c.property,
                        "operator": c.operator,
                        "value": c.value,
                        "negate": c.negate,
                    }
                    for c in rule.conditions
                ],
                "actions": [
                    {
                        "action_type": a.action_type.value,
                        "target": a.target,
                        "parameters": a.parameters,
                        "order_index": a.order_index,
                    }
                    for a in rule.actions
                ],
            })
        return {
            "format_version": 1,
            "sheet": sheet.to_dict(),
            "rules": rules_data,
            "exported_at": _time_module.time(),
        }

    def import_event_sheet(self, data: Dict[str, Any]) -> Optional[EventSheet]:
        sheet_info = data.get("sheet", {})
        sheet = self.create_event_sheet(
            name=sheet_info.get("name", "Imported Sheet"),
            scope=sheet_info.get("scope", "global"),
            description=sheet_info.get("description", ""),
        )
        if sheet is None:
            return None

        for rule_data in data.get("rules", []):
            try:
                rt = RepeatType(rule_data.get("repeat_type", "once"))
            except ValueError:
                rt = RepeatType.ONCE

            rule = self.create_rule(
                name=rule_data.get("name", "Imported Rule"),
                sheet_id=sheet.id,
                repeat_type=rt,
                priority=rule_data.get("priority", 0),
                enabled=rule_data.get("enabled", True),
                tags=rule_data.get("tags", []),
            )
            if rule is None:
                continue

            for cond_data in rule_data.get("conditions", []):
                try:
                    ct = ConditionType(cond_data.get("condition_type", "custom"))
                except ValueError:
                    ct = ConditionType.CUSTOM
                self.add_condition(
                    rule_id=rule.id,
                    condition_type=ct,
                    target=cond_data.get("target", ""),
                    property=cond_data.get("property", ""),
                    operator=cond_data.get("operator", "=="),
                    value=cond_data.get("value"),
                    negate=cond_data.get("negate", False),
                )

            for act_data in rule_data.get("actions", []):
                try:
                    at = ActionType(act_data.get("action_type", "custom_action"))
                except ValueError:
                    at = ActionType.CUSTOM_ACTION
                self.add_action(
                    rule_id=rule.id,
                    action_type=at,
                    target=act_data.get("target", ""),
                    parameters=act_data.get("parameters", {}),
                    order_index=act_data.get("order_index", 0),
                )

        return sheet

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def clear_sheet(self, sheet_id: str) -> Dict[str, Any]:
        sheet = self._sheets.get(sheet_id)
        if sheet is None:
            return {"success": False, "error": "Sheet not found"}
        for rule in sheet.rules:
            self._rule_index.pop(rule.id, None)
            self._rule_to_sheet.pop(rule.id, None)
            self._fired_once_rules.discard(rule.id)
            self._rule_last_fired.pop(rule.id, None)
            for cond in rule.conditions:
                self._condition_index.pop(cond.id, None)
            for act in rule.actions:
                self._action_index.pop(act.id, None)
        removed_count = len(sheet.rules)
        sheet.rules.clear()
        sheet.updated_at = _time_module.time()
        return {"success": True, "rules_removed": removed_count}

    def reset(self) -> None:
        with self._lock:
            self._sheets.clear()
            self._rule_index.clear()
            self._condition_index.clear()
            self._action_index.clear()
            self._rule_to_sheet.clear()
            self._fired_once_rules.clear()
            self._rule_last_fired.clear()
            self._simulated_game_state = {
                "variables": {},
                "objects": {},
                "inputs": {},
                "timers": {},
                "collisions": [],
                "raycast_hits": [],
                "animations": {},
                "scene": "main",
                "tick_count": 0,
                "delta_time": 0.0,
            }
            self._total_evaluations = 0
            self._total_actions_executed = 0
            self._total_ticks_simulated = 0
            self._total_rules_triggered = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive EventScripting subsystem statistics."""
        return {
            "total_sheets": len(self._sheets),
            "total_rules": sum(len(s.rules) for s in self._sheets.values()),
            "total_evaluations": self._total_evaluations,
            "total_actions_executed": self._total_actions_executed,
            "total_ticks_simulated": self._total_ticks_simulated,
            "total_rules_triggered": self._total_rules_triggered,
        }


def get_event_scripting() -> EventScripting:
    return EventScripting.get_instance()