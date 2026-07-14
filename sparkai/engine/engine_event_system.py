"""
SparkLabs Engine - Event-Driven Game Logic System

A visual event system where game logic is expressed as condition-action
rules. Designers define events, attach conditions, and bind actions; the
runtime evaluates every rule once per tick and fires actions whose
conditions evaluate to true.

Core concepts:
  GameEvent/Condition/ConditionGroup/Action/EventRule - rule building blocks
  Variable/Timer/TriggerVolume/InputBinding - state and input
  EventBus/RuleTrace - dispatch and debugging

Thread safety:
  All mutating operations acquire an internal lock so the system can be
  ticked from a simulation thread while a scripting thread mutates rules.
"""

from __future__ import annotations

import math
import threading
import time
import uuid as _uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


def _uid(prefix: str = "id") -> str:
    """Generate a unique identifier with a readable prefix."""
    return f"{prefix}_{_uuid.uuid4().hex[:12]}"


def _now_ts() -> float:
    """Return the current timestamp in seconds."""
    return time.time()


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a numeric value into the inclusive [lo, hi] range."""
    return max(lo, min(hi, value))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return default if value is None else float(value)
    except (TypeError, ValueError):
        return default


def _to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {k: _to_dict(getattr(obj, k)) for k in obj.__dataclass_fields__}
    if isinstance(obj, list):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, dict):
        return {k: _to_dict(v) for k, v in obj.items()}
    if isinstance(obj, tuple):
        return [_to_dict(i) for i in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj


_MAX_EVENTS = 4000
_MAX_RULES = 4000
_MAX_VARIABLES = 8000
_MAX_TIMERS = 1000
_MAX_VOLUMES = 2000
_MAX_BINDINGS = 2000
_MAX_SUBSCRIBERS = 4000
_MAX_DISPATCH_HISTORY = 2000
_MAX_TRACE_RECORDS = 4000


class VariableScope(str, Enum):
    GLOBAL = "global"
    ENTITY = "entity"
    SCENE = "scene"
    TEAM = "team"


class ConditionType(str, Enum):
    VARIABLE_COMPARISON = "variable_comparison"
    ENTITY_STATE = "entity_state"
    DISTANCE_CHECK = "distance_check"
    INPUT_STATE = "input_state"
    TIMER_ELAPSED = "timer_elapsed"
    COUNTER_REACHED = "counter_reached"
    CUSTOM_EXPRESSION = "custom_expression"


class ActionType(str, Enum):
    SET_VARIABLE = "set_variable"
    MODIFY_VARIABLE = "modify_variable"
    SPAWN_ENTITY = "spawn_entity"
    DESTROY_ENTITY = "destroy_entity"
    PLAY_SOUND = "play_sound"
    PLAY_ANIMATION = "play_animation"
    APPLY_FORCE = "apply_force"
    SET_PROPERTY = "set_property"
    SEND_MESSAGE = "send_message"
    TRIGGER_EVENT = "trigger_event"
    RUN_SCRIPT = "run_script"
    CREATE_TIMER = "create_timer"
    MODIFY_STAT = "modify_stat"
    TELEPORT_ENTITY = "teleport_entity"
    ENABLE_EVENT = "enable_event"
    DISABLE_EVENT = "disable_event"
    CHANGE_SCENE = "change_scene"


class EventType(str, Enum):
    TRIGGER = "trigger"
    TIMER = "timer"
    COLLISION = "collision"
    INPUT = "input"
    STATE_CHANGE = "state_change"
    CUSTOM = "custom"


class TimerState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    FINISHED = "finished"


class TriggerShape(str, Enum):
    BOX = "box"
    SPHERE = "sphere"
    CAPSULE = "capsule"


class TriggerPhase(str, Enum):
    ON_ENTER = "on_enter"
    ON_STAY = "on_stay"
    ON_EXIT = "on_exit"


class InputType(str, Enum):
    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"


class LogicalOperator(str, Enum):
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class GameEvent:
    event_id: str
    name: str
    description: str = ""
    event_type: EventType = EventType.CUSTOM
    parameters: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    category: str = "general"
    parent_event_id: Optional[str] = None
    created_at: float = field(default_factory=_now_ts)


@dataclass
class Condition:
    condition_id: str
    condition_type: ConditionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    negate: bool = False


@dataclass
class ConditionGroup:
    group_id: str
    operator: LogicalOperator = LogicalOperator.AND
    conditions: List[Condition] = field(default_factory=list)
    sub_groups: List["ConditionGroup"] = field(default_factory=list)
    negate: bool = False


@dataclass
class Action:
    action_id: str
    action_type: ActionType
    parameters: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0
    order: int = 0


@dataclass
class EventRule:
    rule_id: str
    name: str
    trigger_event: str
    condition_group: Optional[ConditionGroup] = None
    actions: List[Action] = field(default_factory=list)
    enabled: bool = True
    priority: int = 0
    cooldown: float = 0.0
    max_executions: int = 0
    execution_count: int = 0
    last_fired_at: float = 0.0
    created_at: float = field(default_factory=_now_ts)
    description: str = ""


@dataclass
class Variable:
    variable_id: str
    name: str
    scope: VariableScope
    scope_owner: str = ""
    value: Any = 0
    variable_type: str = "number"
    created_at: float = field(default_factory=_now_ts)


@dataclass
class Timer:
    timer_id: str
    name: str
    duration: float
    repeat: bool = False
    state: TimerState = TimerState.IDLE
    elapsed: float = 0.0
    started_at: float = 0.0
    paused_at: float = 0.0
    associated_event: str = ""
    cycles: int = 0


@dataclass
class TriggerVolume:
    volume_id: str
    name: str
    shape: TriggerShape
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    associated_entity: Optional[str] = None
    occupants: List[str] = field(default_factory=list)
    on_enter_event: str = ""
    on_stay_event: str = ""
    on_exit_event: str = ""
    enabled: bool = True


@dataclass
class InputBinding:
    binding_id: str
    input_type: InputType
    input_name: str
    bound_event: str
    chord: List[str] = field(default_factory=list)
    hold_duration: float = 0.0
    sequence: List[str] = field(default_factory=list)
    sequence_window: float = 0.5
    sequence_progress: int = 0
    hold_elapsed: float = 0.0
    enabled: bool = True


@dataclass
class EventBusSubscription:
    subscription_id: str
    event_name: str
    callback: Callable[[Dict[str, Any]], None]
    priority: int = 0
    filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None
    active: bool = True


@dataclass
class EventDispatch:
    dispatch_id: str
    event_name: str
    payload: Dict[str, Any]
    timestamp: float
    delivered_to: int = 0
    cancelled: bool = False


@dataclass
class RuleTrace:
    trace_id: str
    tick_index: int
    rule_id: str
    rule_name: str
    evaluated: bool
    conditions_passed: bool
    fired: bool
    skipped_reason: str = ""
    actions_executed: List[str] = field(default_factory=list)
    actions_skipped: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_now_ts)


class EventDrivenLogicSystem:
    """Central runtime for event-driven game logic with thread-safe state."""

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        self._events: Dict[str, GameEvent] = {}
        self._rules: Dict[str, EventRule] = {}
        self._variables: Dict[str, Variable] = {}
        self._timers: Dict[str, Timer] = {}
        self._volumes: Dict[str, TriggerVolume] = {}
        self._bindings: Dict[str, InputBinding] = {}
        self._subscriptions: Dict[str, EventBusSubscription] = {}
        self._dispatch_history: List[EventDispatch] = []
        self._tracing_enabled = False
        self._traces: List[RuleTrace] = []
        self._step_through = False
        self._step_pending = False
        self._tick_index = 0
        self._total_dispatched = 0
        self._total_fired = 0
        self._last_tick_dt = 0.0
        self._input_states: Dict[str, bool] = {}
        self._entity_states: Dict[str, Dict[str, Any]] = {}
        self._entity_positions: Dict[str, Tuple[float, float, float]] = {}
        self._pending_actions: List[Tuple[float, Action, Dict[str, Any]]] = []
        self._rule_stats: Dict[str, Dict[str, int]] = {}
        self._action_handler: Optional[Callable[[Action, Dict[str, Any]], None]] = None

    def initialize(self) -> None:
        """Reset all state and seed the system with sample rules."""
        with self._lock:
            for attr in ("_events", "_rules", "_variables", "_timers", "_volumes",
                         "_bindings", "_subscriptions", "_dispatch_history", "_traces",
                         "_pending_actions", "_rule_stats", "_input_states",
                         "_entity_states", "_entity_positions"):
                getattr(self, attr).clear()
            self._tick_index = 0
            self._total_dispatched = 0
            self._total_fired = 0
            self._initialized = True
            self._seed_sample_rules()

    def reset(self) -> None:
        self.initialize()

    def set_action_handler(self, handler: Callable[[Action, Dict[str, Any]], None]) -> None:
        with self._lock:
            self._action_handler = handler

    def create_event(self, name: str, description: str = "",
                     event_type: EventType = EventType.CUSTOM,
                     parameters: Optional[Dict[str, Any]] = None,
                     category: str = "general", parent_event_id: Optional[str] = None,
                     enabled: bool = True, event_id: Optional[str] = None) -> str:
        with self._lock:
            if len(self._events) >= _MAX_EVENTS:
                raise RuntimeError("event capacity reached")
            eid = event_id or _uid("event")
            if eid in self._events:
                raise ValueError(f"event already exists: {eid}")
            self._events[eid] = GameEvent(
                event_id=eid, name=name, description=description,
                event_type=event_type, parameters=dict(parameters or {}),
                enabled=enabled, category=category, parent_event_id=parent_event_id)
            return eid

    def remove_event(self, event_id: str) -> bool:
        with self._lock:
            return self._events.pop(event_id, None) is not None

    def get_event(self, event_id: str) -> Optional[GameEvent]:
        with self._lock:
            return self._events.get(event_id)

    def list_events(self, category: Optional[str] = None,
                    event_type: Optional[EventType] = None) -> List[GameEvent]:
        with self._lock:
            return [ev for ev in self._events.values()
                    if (category is None or ev.category == category)
                    and (event_type is None or ev.event_type == event_type)]

    def create_condition(self, condition_type: ConditionType,
                         parameters: Optional[Dict[str, Any]] = None,
                         negate: bool = False) -> Condition:
        return Condition(condition_id=_uid("cond"), condition_type=condition_type,
                         parameters=dict(parameters or {}), negate=negate)

    def create_condition_group(self, operator: LogicalOperator = LogicalOperator.AND,
                               conditions: Optional[List[Condition]] = None,
                               sub_groups: Optional[List[ConditionGroup]] = None,
                               negate: bool = False) -> ConditionGroup:
        return ConditionGroup(group_id=_uid("group"), operator=operator,
                              conditions=list(conditions or []),
                              sub_groups=list(sub_groups or []), negate=negate)

    def create_action(self, action_type: ActionType,
                      parameters: Optional[Dict[str, Any]] = None,
                      delay: float = 0.0, order: int = 0) -> Action:
        return Action(action_id=_uid("action"), action_type=action_type,
                      parameters=dict(parameters or {}), delay=delay, order=order)

    def create_rule(self, name: str, trigger_event: str,
                    conditions: Optional[List[Dict[str, Any]]] = None,
                    actions: Optional[List[Dict[str, Any]]] = None,
                    condition_group: Optional[ConditionGroup] = None,
                    action_list: Optional[List[Action]] = None,
                    enabled: bool = True, priority: int = 0, cooldown: float = 0.0,
                    max_executions: int = 0, description: str = "",
                    rule_id: Optional[str] = None) -> str:
        """Register a new rule from dicts or pre-built Condition/Action objects."""
        with self._lock:
            if len(self._rules) >= _MAX_RULES:
                raise RuntimeError("rule capacity reached")
            rid = rule_id or _uid("rule")
            if condition_group is None:
                if conditions:
                    built = [self.create_condition(
                        ConditionType(c["type"]),
                        {k: v for k, v in c.items() if k != "type"}) for c in conditions]
                    condition_group = self.create_condition_group(LogicalOperator.AND, built)
                else:
                    condition_group = self.create_condition_group()
            final_actions: List[Action] = list(action_list or [])
            if actions:
                for idx, act in enumerate(actions):
                    final_actions.append(self.create_action(
                        ActionType(act["type"]),
                        {k: v for k, v in act.items() if k != "type"},
                        act.get("delay", 0.0), act.get("order", idx)))
            self._rules[rid] = EventRule(
                rule_id=rid, name=name, trigger_event=trigger_event,
                condition_group=condition_group, actions=final_actions,
                enabled=enabled, priority=priority, cooldown=cooldown,
                max_executions=max_executions, description=description)
            self._rule_stats[rid] = {"evaluated": 0, "conditions_passed": 0,
                                     "fired": 0, "actions_executed": 0, "actions_skipped": 0}
            return rid

    def get_rule(self, rule_id: str) -> Optional[EventRule]:
        with self._lock:
            return self._rules.get(rule_id)

    def remove_rule(self, rule_id: str) -> bool:
        with self._lock:
            self._rule_stats.pop(rule_id, None)
            return self._rules.pop(rule_id, None) is not None

    def enable_rule(self, rule_id: str) -> bool:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.enabled = True
            return True

    def disable_rule(self, rule_id: str) -> bool:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.enabled = False
            return True

    def set_rule_priority(self, rule_id: str, priority: int) -> bool:
        with self._lock:
            rule = self._rules.get(rule_id)
            if rule is None:
                return False
            rule.priority = priority
            return True

    def list_rules(self, enabled_only: bool = False) -> List[EventRule]:
        with self._lock:
            rules = [r for r in self._rules.values() if not enabled_only or r.enabled]
            rules.sort(key=lambda r: r.priority, reverse=True)
            return rules

    def _variable_key(self, name: str, scope: VariableScope, owner: str) -> str:
        return f"global::{name}" if scope == VariableScope.GLOBAL else f"{scope.value}::{owner}::{name}"

    def _resolve_token(self, token: str) -> Tuple[str, VariableScope, str]:
        """Resolve '$player.health' -> ('health', ENTITY, 'player')."""
        clean = token[1:] if token.startswith("$") else token
        if "#" in clean:
            owner, name = clean.split("#", 1)
            return (name, VariableScope.SCENE, owner)
        if "." in clean:
            owner, name = clean.split(".", 1)
            return (name, VariableScope.ENTITY, owner)
        return (clean, VariableScope.GLOBAL, "")

    def get_variable(self, name: str, default: Any = None) -> Any:
        with self._lock:
            var = self._variables.get(self._variable_key(name, VariableScope.GLOBAL, ""))
            return var.value if var is not None else default

    def set_variable(self, name: str, value: Any) -> None:
        with self._lock:
            if len(self._variables) >= _MAX_VARIABLES:
                raise RuntimeError("variable capacity reached")
            key = self._variable_key(name, VariableScope.GLOBAL, "")
            if key in self._variables:
                self._variables[key].value = value
            else:
                self._variables[key] = Variable(
                    variable_id=_uid("var"), name=name, scope=VariableScope.GLOBAL,
                    value=value, variable_type=self._infer_type(value))

    def modify_variable(self, name: str, delta: Any) -> Any:
        with self._lock:
            key = self._variable_key(name, VariableScope.GLOBAL, "")
            var = self._variables.get(key)
            if var is None:
                self.set_variable(name, delta)
                return delta
            if isinstance(var.value, (int, float)) and isinstance(delta, (int, float)):
                var.value += delta
            elif isinstance(var.value, list) and isinstance(delta, list):
                var.value.extend(delta)
            elif isinstance(var.value, str) and isinstance(delta, str):
                var.value += delta
            else:
                var.value = delta
            return var.value

    def get_scoped_variable(self, name: str, scope: VariableScope,
                            owner: str, default: Any = None) -> Any:
        with self._lock:
            var = self._variables.get(self._variable_key(name, scope, owner))
            return var.value if var is not None else default

    def set_scoped_variable(self, name: str, scope: VariableScope,
                            owner: str, value: Any) -> None:
        with self._lock:
            if len(self._variables) >= _MAX_VARIABLES:
                raise RuntimeError("variable capacity reached")
            key = self._variable_key(name, scope, owner)
            if key in self._variables:
                self._variables[key].value = value
            else:
                self._variables[key] = Variable(
                    variable_id=_uid("var"), name=name, scope=scope,
                    scope_owner=owner, value=value, variable_type=self._infer_type(value))

    def list_variables(self, scope: Optional[VariableScope] = None,
                       owner: Optional[str] = None) -> List[Variable]:
        with self._lock:
            return [v for v in self._variables.values()
                    if (scope is None or v.scope == scope)
                    and (owner is None or v.scope_owner == owner)]

    def _infer_type(self, value: Any) -> str:
        if isinstance(value, bool):
            return "boolean"
        if isinstance(value, (int, float)):
            return "number"
        if isinstance(value, str):
            return "string"
        if isinstance(value, list):
            return "list"
        if isinstance(value, dict):
            return "struct"
        return "number"

    def _lookup_value(self, token: Any) -> Any:
        if isinstance(token, str) and token.startswith("$"):
            name, scope, owner = self._resolve_token(token)
            return self.get_scoped_variable(name, scope, owner)
        return token

    def create_timer(self, name: str, duration: float, repeat: bool = False,
                     associated_event: str = "", timer_id: Optional[str] = None) -> str:
        with self._lock:
            if len(self._timers) >= _MAX_TIMERS:
                raise RuntimeError("timer capacity reached")
            tid = timer_id or _uid("timer")
            self._timers[tid] = Timer(timer_id=tid, name=name, duration=duration,
                                      repeat=repeat, associated_event=associated_event)
            return tid

    def start_timer(self, timer_id: str) -> bool:
        with self._lock:
            timer = self._timers.get(timer_id)
            if timer is None:
                return False
            timer.state = TimerState.RUNNING
            timer.elapsed = 0.0
            timer.started_at = _now_ts()
            return True

    def pause_timer(self, timer_id: str) -> bool:
        with self._lock:
            timer = self._timers.get(timer_id)
            if timer is None:
                return False
            if timer.state == TimerState.RUNNING:
                timer.state = TimerState.PAUSED
                timer.paused_at = _now_ts()
            return True

    def resume_timer(self, timer_id: str) -> bool:
        with self._lock:
            timer = self._timers.get(timer_id)
            if timer is None:
                return False
            if timer.state == TimerState.PAUSED:
                timer.state = TimerState.RUNNING
                timer.paused_at = 0.0
            return True

    def reset_timer(self, timer_id: str) -> bool:
        with self._lock:
            timer = self._timers.get(timer_id)
            if timer is None:
                return False
            timer.state = TimerState.IDLE
            timer.elapsed = 0.0
            timer.cycles = 0
            timer.started_at = 0.0
            timer.paused_at = 0.0
            return True

    def get_timer_state(self, timer_id: str) -> Optional[TimerState]:
        with self._lock:
            timer = self._timers.get(timer_id)
            return timer.state if timer is not None else None

    def create_trigger_volume(self, name: str, shape: TriggerShape,
                              position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
                              dimensions: Tuple[float, float, float] = (1.0, 1.0, 1.0),
                              associated_entity: Optional[str] = None,
                              on_enter_event: str = "", on_stay_event: str = "",
                              on_exit_event: str = "",
                              volume_id: Optional[str] = None) -> str:
        with self._lock:
            if len(self._volumes) >= _MAX_VOLUMES:
                raise RuntimeError("volume capacity reached")
            vid = volume_id or _uid("volume")
            self._volumes[vid] = TriggerVolume(
                volume_id=vid, name=name, shape=shape, position=position,
                dimensions=dimensions, associated_entity=associated_entity,
                on_enter_event=on_enter_event, on_stay_event=on_stay_event,
                on_exit_event=on_exit_event)
            return vid

    def remove_trigger_volume(self, volume_id: str) -> bool:
        with self._lock:
            return self._volumes.pop(volume_id, None) is not None

    def get_trigger_volume(self, volume_id: str) -> Optional[TriggerVolume]:
        with self._lock:
            return self._volumes.get(volume_id)

    def check_trigger(self, volume_id: str, entity_id: str,
                      position: Optional[Tuple[float, float, float]] = None) -> TriggerPhase:
        """Test entity occupancy in a volume. Returns ON_ENTER, ON_STAY, or ON_EXIT."""
        with self._lock:
            volume = self._volumes.get(volume_id)
            if volume is None or not volume.enabled:
                return TriggerPhase.ON_EXIT
            if position is None:
                position = self._entity_positions.get(entity_id, (0.0, 0.0, 0.0))
            inside = self._point_in_volume(volume, position)
            was_inside = entity_id in volume.occupants
            if inside and not was_inside:
                volume.occupants.append(entity_id)
                if volume.on_enter_event:
                    self.publish(volume.on_enter_event, {"entity": entity_id})
                return TriggerPhase.ON_ENTER
            if inside and was_inside:
                if volume.on_stay_event:
                    self.publish(volume.on_stay_event, {"entity": entity_id})
                return TriggerPhase.ON_STAY
            if not inside and was_inside:
                volume.occupants.remove(entity_id)
                if volume.on_exit_event:
                    self.publish(volume.on_exit_event, {"entity": entity_id})
                return TriggerPhase.ON_EXIT
            return TriggerPhase.ON_EXIT

    def _point_in_volume(self, volume: TriggerVolume,
                         point: Tuple[float, float, float]) -> bool:
        cx, cy, cz = volume.position
        px, py, pz = point
        if volume.shape == TriggerShape.SPHERE:
            r = volume.dimensions[0]
            dx, dy, dz = px - cx, py - cy, pz - cz
            return (dx * dx + dy * dy + dz * dz) <= r * r
        if volume.shape == TriggerShape.BOX:
            sx, sy, sz = volume.dimensions
            return abs(px - cx) <= sx * 0.5 and abs(py - cy) <= sy * 0.5 and abs(pz - cz) <= sz * 0.5
        if volume.shape == TriggerShape.CAPSULE:
            r, h, _ = volume.dimensions
            dx, dz = px - cx, pz - cz
            return math.sqrt(dx * dx + dz * dz) <= r and abs(py - cy) <= (h * 0.5 + r)
        return False

    def bind_input(self, input_type: InputType, input_name: str, bound_event: str,
                   chord: Optional[List[str]] = None, hold_duration: float = 0.0,
                   sequence: Optional[List[str]] = None, sequence_window: float = 0.5,
                   enabled: bool = True, binding_id: Optional[str] = None) -> str:
        with self._lock:
            if len(self._bindings) >= _MAX_BINDINGS:
                raise RuntimeError("binding capacity reached")
            bid = binding_id or _uid("binding")
            self._bindings[bid] = InputBinding(
                binding_id=bid, input_type=input_type, input_name=input_name,
                bound_event=bound_event, chord=list(chord or []),
                hold_duration=hold_duration, sequence=list(sequence or []),
                sequence_window=sequence_window, enabled=enabled)
            return bid

    def unbind_input(self, binding_id: str) -> bool:
        with self._lock:
            return self._bindings.pop(binding_id, None) is not None

    def get_input_bindings(self, input_type: Optional[InputType] = None,
                           bound_event: Optional[str] = None) -> List[InputBinding]:
        with self._lock:
            return [b for b in self._bindings.values()
                    if (input_type is None or b.input_type == input_type)
                    and (bound_event is None or b.bound_event == bound_event)]

    def subscribe(self, event_name: str, callback: Callable[[Dict[str, Any]], None],
                  priority: int = 0,
                  filter_fn: Optional[Callable[[Dict[str, Any]], bool]] = None) -> str:
        with self._lock:
            if len(self._subscriptions) >= _MAX_SUBSCRIBERS:
                raise RuntimeError("subscriber capacity reached")
            sid = _uid("sub")
            self._subscriptions[sid] = EventBusSubscription(
                subscription_id=sid, event_name=event_name, callback=callback,
                priority=priority, filter_fn=filter_fn)
            return sid

    def unsubscribe(self, subscription_id: str) -> bool:
        with self._lock:
            return self._subscriptions.pop(subscription_id, None) is not None

    def publish(self, event_name: str, payload: Optional[Dict[str, Any]] = None,
                cancelable: bool = True) -> str:
        """Dispatch an event to subscribers by priority. Supports cancellation."""
        payload = dict(payload or {})
        dispatch_id = _uid("dispatch")
        cancelled = False
        delivered = 0
        with self._lock:
            subs = sorted([s for s in self._subscriptions.values()
                           if s.active and s.event_name == event_name],
                          key=lambda s: s.priority, reverse=True)
        for sub in subs:
            if cancelled:
                break
            if sub.filter_fn is not None and not sub.filter_fn(payload):
                continue
            try:
                sub.callback(payload)
            except Exception:
                pass
            delivered += 1
            if cancelable and payload.get("__cancel__"):
                cancelled = True
        with self._lock:
            self._dispatch_history.append(EventDispatch(
                dispatch_id=dispatch_id, event_name=event_name, payload=payload,
                timestamp=_now_ts(), delivered_to=delivered, cancelled=cancelled))
            if len(self._dispatch_history) > _MAX_DISPATCH_HISTORY:
                self._dispatch_history.pop(0)
            self._total_dispatched += 1
        return dispatch_id

    def get_dispatch_history(self, event_name: Optional[str] = None,
                             limit: int = 100) -> List[EventDispatch]:
        with self._lock:
            result = list(self._dispatch_history)
        if event_name is not None:
            result = [d for d in result if d.event_name == event_name]
        return result[-limit:]

    def enable_tracing(self, step_through: bool = False) -> None:
        """Enable per-rule execution tracing. Optionally enable step-through mode."""
        with self._lock:
            self._tracing_enabled = True
            self._step_through = step_through
            self._step_pending = False

    def disable_tracing(self) -> None:
        with self._lock:
            self._tracing_enabled = False
            self._step_through = False
            self._step_pending = False

    def get_trace(self, rule_id: Optional[str] = None,
                  limit: int = 200) -> List[RuleTrace]:
        with self._lock:
            result = list(self._traces)
        if rule_id is not None:
            result = [t for t in result if t.rule_id == rule_id]
        return result[-limit:]

    def get_rule_statistics(self, rule_id: str) -> Optional[Dict[str, int]]:
        with self._lock:
            stats = self._rule_stats.get(rule_id)
            return dict(stats) if stats is not None else None

    def _evaluate_condition(self, condition: Condition) -> bool:
        """Evaluate a single condition against the current game state."""
        p = condition.parameters
        ct = condition.condition_type
        if ct == ConditionType.VARIABLE_COMPARISON:
            result = self._compare(self._lookup_value(p.get("var")),
                                   p.get("op", "=="), self._lookup_value(p.get("value")))
        elif ct == ConditionType.ENTITY_STATE:
            states = self._entity_states.get(p.get("entity_id", ""), {})
            st = p.get("state", "")
            result = states.get(st) is True or states.get(st) == st
        elif ct == ConditionType.DISTANCE_CHECK:
            pa = self._entity_positions.get(p.get("entity_a", ""), (0.0, 0.0, 0.0))
            pb = self._entity_positions.get(p.get("entity_b", ""), (0.0, 0.0, 0.0))
            dist = math.sqrt((pa[0]-pb[0])**2 + (pa[1]-pb[1])**2 + (pa[2]-pb[2])**2)
            result = dist <= _safe_float(p.get("distance", 0.0))
        elif ct == ConditionType.INPUT_STATE:
            result = bool(self._input_states.get(p.get("input_name", ""), False))
        elif ct == ConditionType.TIMER_ELAPSED:
            result = any(t.name == p.get("timer_name", "") and
                         t.elapsed >= _safe_float(p.get("duration", 0.0))
                         for t in self._timers.values())
        elif ct == ConditionType.COUNTER_REACHED:
            try:
                result = float(self._lookup_value(p.get("counter"))) >= _safe_float(
                    self._lookup_value(p.get("target")))
            except (TypeError, ValueError):
                result = False
        elif ct == ConditionType.CUSTOM_EXPRESSION:
            try:
                result = bool(eval(p.get("expression", "False"),
                                   {"__builtins__": {}}, dict(self._flat_variables())))
            except Exception:
                result = False
        else:
            result = False
        return (not result) if condition.negate else result

    def _evaluate_group(self, group: ConditionGroup) -> bool:
        results = [self._evaluate_condition(c) for c in group.conditions]
        results += [self._evaluate_group(g) for g in group.sub_groups]
        if group.operator == LogicalOperator.AND:
            result = all(results) if results else True
        elif group.operator == LogicalOperator.OR:
            result = any(results) if results else False
        else:
            result = not (any(results) if results else False)
        return (not result) if group.negate else result

    def _compare(self, left: Any, op: str, right: Any) -> bool:
        try:
            if op == "==": return left == right
            if op == "!=": return left != right
            if op == "<":  return left < right
            if op == "<=": return left <= right
            if op == ">":  return left > right
            if op == ">=": return left >= right
        except TypeError:
            return False
        return False

    def _flat_variables(self) -> Dict[str, Any]:
        flat: Dict[str, Any] = {}
        for v in self._variables.values():
            if v.scope == VariableScope.GLOBAL:
                flat[v.name] = v.value
            else:
                flat[f"{v.scope_owner}_{v.name}"] = v.value
        return flat

    def _execute_action(self, action: Action, context: Dict[str, Any]) -> None:
        stats = self._rule_stats.get(context.get("rule_id", ""), {})
        stats["actions_executed"] = stats.get("actions_executed", 0) + 1
        if action.delay > 0.0:
            self._pending_actions.append((_now_ts() + action.delay, action, context))
            return
        at = action.action_type
        p = action.parameters
        if at == ActionType.SET_VARIABLE:
            self.set_variable(p.get("name", ""), self._lookup_value(p.get("value")))
        elif at == ActionType.MODIFY_VARIABLE:
            self.modify_variable(p.get("name", ""), self._lookup_value(p.get("delta")))
        elif at == ActionType.SET_PROPERTY:
            self._entity_states.setdefault(p.get("target", ""), {})[p.get("property", "")] = self._lookup_value(p.get("value"))
        elif at == ActionType.MODIFY_STAT:
            target, stat = p.get("target", ""), p.get("stat", "")
            cur = _safe_float(self._entity_states.get(target, {}).get(stat))
            self._entity_states.setdefault(target, {})[stat] = cur + _safe_float(self._lookup_value(p.get("delta")))
        elif at == ActionType.TELEPORT_ENTITY:
            self._entity_positions[p.get("target", "")] = tuple(p.get("position", (0.0, 0.0, 0.0)))
        elif at == ActionType.CREATE_TIMER:
            self.create_timer(p.get("name", "timer"), _safe_float(p.get("duration", 1.0)),
                              bool(p.get("repeat", False)), p.get("associated_event", ""))
        elif at == ActionType.TRIGGER_EVENT:
            self.publish(p.get("event_name", ""), p.get("payload", {}))
        elif at == ActionType.SEND_MESSAGE:
            self.publish("message", {"to": p.get("to", ""), "data": p.get("data", {})})
        elif at == ActionType.ENABLE_EVENT:
            ev = self._events.get(p.get("event_id", ""))
            if ev: ev.enabled = True
        elif at == ActionType.DISABLE_EVENT:
            ev = self._events.get(p.get("event_id", ""))
            if ev: ev.enabled = False
        elif at == ActionType.CHANGE_SCENE:
            self.publish("change_scene", {"scene": p.get("scene", "")})
        if at in (ActionType.SPAWN_ENTITY, ActionType.DESTROY_ENTITY, ActionType.PLAY_SOUND,
                  ActionType.PLAY_ANIMATION, ActionType.APPLY_FORCE, ActionType.RUN_SCRIPT):
            if self._action_handler:
                try: self._action_handler(action, context)
                except Exception: pass

    def tick(self, dt: float) -> None:
        """Advance simulation: update timers, run delayed actions, evaluate rules."""
        with self._lock:
            self._tick_index += 1
            self._last_tick_dt = dt
            self._advance_timers(dt)
            self._run_pending_actions()
        pending: List[str] = []
        with self._lock:
            recent = self._dispatch_history[-50:] if self._dispatch_history else []
            cutoff = _now_ts() - max(dt, 0.001)
            pending = [d.event_name for d in recent if d.timestamp >= cutoff]
        fired_one = False
        for rule in self.list_rules(enabled_only=True):
            if rule.trigger_event not in pending and rule.trigger_event != "every_tick":
                continue
            if self._step_through and fired_one and not self._step_pending:
                continue
            self._evaluate_rule(rule)
            if self._step_through:
                fired_one = True
                self._step_pending = False
        with self._lock:
            if self._tracing_enabled and len(self._traces) > _MAX_TRACE_RECORDS:
                self._traces = self._traces[-_MAX_TRACE_RECORDS:]

    def _advance_timers(self, dt: float) -> None:
        for timer in self._timers.values():
            if timer.state != TimerState.RUNNING:
                continue
            timer.elapsed += dt
            if timer.elapsed >= timer.duration:
                if timer.repeat:
                    timer.elapsed = 0.0
                    timer.cycles += 1
                else:
                    timer.elapsed = timer.duration
                    timer.state = TimerState.FINISHED
                if timer.associated_event:
                    self.publish(timer.associated_event, {"timer": timer.name})

    def _run_pending_actions(self) -> None:
        now = _now_ts()
        ready = [e for e in self._pending_actions if e[0] <= now]
        self._pending_actions = [e for e in self._pending_actions if e[0] > now]
        for _, action, ctx in ready:
            self._execute_action(action, ctx)

    def _evaluate_rule(self, rule: EventRule) -> None:
        trace = RuleTrace(trace_id=_uid("trace"), tick_index=self._tick_index,
                          rule_id=rule.rule_id, rule_name=rule.name,
                          evaluated=True, conditions_passed=False, fired=False)
        stats = self._rule_stats.setdefault(rule.rule_id, {
            "evaluated": 0, "conditions_passed": 0, "fired": 0,
            "actions_executed": 0, "actions_skipped": 0})
        stats["evaluated"] += 1
        if rule.cooldown > 0.0 and (_now_ts() - rule.last_fired_at) < rule.cooldown:
            trace.skipped_reason = "cooldown"
            trace.actions_skipped = [a.action_id for a in rule.actions]
            self._record_trace(trace)
            return
        if rule.max_executions > 0 and rule.execution_count >= rule.max_executions:
            trace.skipped_reason = "max_executions"
            trace.actions_skipped = [a.action_id for a in rule.actions]
            self._record_trace(trace)
            return
        passed = self._evaluate_group(rule.condition_group) if rule.condition_group else True
        trace.conditions_passed = passed
        if passed:
            stats["conditions_passed"] += 1
            rule.execution_count += 1
            rule.last_fired_at = _now_ts()
            ctx = {"rule_id": rule.rule_id, "rule_name": rule.name, "tick": self._tick_index}
            for action in sorted(rule.actions, key=lambda a: a.order):
                try:
                    self._execute_action(action, ctx)
                    trace.actions_executed.append(action.action_id)
                except Exception:
                    trace.actions_skipped.append(action.action_id)
            trace.fired = True
            stats["fired"] += 1
            with self._lock:
                self._total_fired += 1
        else:
            trace.actions_skipped = [a.action_id for a in rule.actions]
            stats["actions_skipped"] += len(rule.actions)
        self._record_trace(trace)

    def _record_trace(self, trace: RuleTrace) -> None:
        if self._tracing_enabled:
            with self._lock:
                self._traces.append(trace)

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized, "tick_index": self._tick_index,
                "events": len(self._events), "rules": len(self._rules),
                "variables": len(self._variables), "timers": len(self._timers),
                "volumes": len(self._volumes), "bindings": len(self._bindings),
                "subscriptions": len(self._subscriptions),
                "tracing": self._tracing_enabled, "step_through": self._step_through,
            }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "total_dispatched": self._total_dispatched,
                "total_fired": self._total_fired, "tick_index": self._tick_index,
                "last_tick_dt": self._last_tick_dt,
                "pending_actions": len(self._pending_actions),
                "traces": len(self._traces),
            }

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "status": self.get_status(), "stats": self.get_stats(),
                "events": [_to_dict(e) for e in self._events.values()],
                "rules": [_to_dict(r) for r in self._rules.values()],
                "variables": [_to_dict(v) for v in self._variables.values()],
                "timers": [_to_dict(t) for t in self._timers.values()],
                "volumes": [_to_dict(v) for v in self._volumes.values()],
                "bindings": [_to_dict(b) for b in self._bindings.values()],
                "subscriptions": [{"subscription_id": s.subscription_id,
                                  "event_name": s.event_name, "priority": s.priority,
                                  "active": s.active} for s in self._subscriptions.values()],
            }

    def to_dict(self) -> Dict[str, Any]:
        return self.get_snapshot()

    def ai_generate_rules(self, description: str) -> List[str]:
        """Generate event rules from a natural-language description via keyword matching."""
        desc = description.lower()
        created: List[str] = []
        patterns: List[Tuple[List[str], str, str, List[Dict], List[Dict], int, float]] = [
            (["damage", "enemy"], "Player takes damage on enemy contact", "on_collision",
             [{"type": "variable_comparison", "var": "$player.invincible", "op": "==", "value": False}],
             [{"type": "modify_stat", "target": "player", "stat": "health", "delta": -10},
              {"type": "play_sound", "name": "hit"}], 10, 0.5),
            (["door", "key"], "Door opens when player has key", "on_interact",
             [{"type": "variable_comparison", "var": "$player.has_key", "op": "==", "value": True}],
             [{"type": "set_property", "target": "door", "property": "open", "value": True},
              {"type": "play_sound", "name": "door_open"}], 20, 0.0),
            (["health", "over"], "Game over when health <= 0", "every_tick",
             [{"type": "variable_comparison", "var": "$player.health", "op": "<=", "value": 0}],
             [{"type": "trigger_event", "event_name": "game_over",
               "payload": {"reason": "health_depleted"}},
              {"type": "change_scene", "scene": "game_over_screen"}], 100, 0.0),
        ]
        with self._lock:
            for keywords, name, trigger, conds, acts, prio, cd in patterns:
                if all(k in desc for k in keywords):
                    if "damage" in desc and "enemy" in desc:
                        self.set_scoped_variable("health", VariableScope.ENTITY, "player", 100)
                        self.set_scoped_variable("invincible", VariableScope.ENTITY, "player", False)
                    if "door" in desc and "key" in desc:
                        self.set_scoped_variable("has_key", VariableScope.ENTITY, "player", False)
                    created.append(self.create_rule(
                        name=name, trigger_event=trigger, conditions=conds,
                        actions=acts, priority=prio, cooldown=cd))
            if not created:
                for kw in ("jump", "shoot", "open", "collect", "die"):
                    if kw in desc:
                        created.append(self.create_rule(
                            name=f"Auto rule for {kw}", trigger_event=f"on_{kw}",
                            actions=[{"type": "trigger_event", "event_name": f"{kw}_performed"}]))
                        break
        return created

    def ai_debug_rules(self) -> List[Dict[str, Any]]:
        """Analyze trace data and suggest fixes for non-firing rules."""
        suggestions: List[Dict[str, Any]] = []
        with self._lock:
            by_rule: Dict[str, List[RuleTrace]] = {}
            for t in self._traces:
                by_rule.setdefault(t.rule_id, []).append(t)
            for rule in self._rules.values():
                traces = by_rule.get(rule.rule_id, [])
                if not traces:
                    suggestions.append({"rule_id": rule.rule_id, "rule_name": rule.name,
                        "diagnosis": "no trace recorded; rule never evaluated",
                        "recommendation": "ensure the trigger event is published and tracing is enabled"})
                    continue
                if any(t.fired for t in traces):
                    continue
                if all(not t.conditions_passed for t in traces):
                    suggestions.append({"rule_id": rule.rule_id, "rule_name": rule.name,
                        "diagnosis": "conditions never evaluated to true",
                        "recommendation": "inspect variable values and comparison operators"})
                cd_skips = sum(1 for t in traces if t.skipped_reason == "cooldown")
                if cd_skips > len(traces) * 0.5:
                    suggestions.append({"rule_id": rule.rule_id, "rule_name": rule.name,
                        "diagnosis": f"skipped {cd_skips} times due to cooldown",
                        "recommendation": "reduce cooldown duration or raise priority"})
                cap_skips = sum(1 for t in traces if t.skipped_reason == "max_executions")
                if cap_skips > 0:
                    suggestions.append({"rule_id": rule.rule_id, "rule_name": rule.name,
                        "diagnosis": f"hit execution cap {cap_skips} times",
                        "recommendation": "raise max_executions or reset the rule"})
        return suggestions

    def _seed_sample_rules(self) -> None:
        self.set_scoped_variable("health", VariableScope.ENTITY, "player", 100)
        self.set_scoped_variable("has_key", VariableScope.ENTITY, "player", False)
        self.set_scoped_variable("invincible", VariableScope.ENTITY, "player", False)
        self.set_variable("score", 0)
        self.create_rule(
            name="Player takes damage on enemy contact", trigger_event="on_collision",
            conditions=[{"type": "variable_comparison", "var": "$player.invincible",
                         "op": "==", "value": False}],
            actions=[{"type": "modify_stat", "target": "player", "stat": "health", "delta": -10},
                     {"type": "play_sound", "name": "hit"},
                     {"type": "play_animation", "target": "player", "animation": "hurt"}],
            priority=10, cooldown=0.5,
            description="Reduce player health when colliding with an enemy.")
        self.create_rule(
            name="Door opens when player has key", trigger_event="on_interact",
            conditions=[{"type": "variable_comparison", "var": "$player.has_key",
                         "op": "==", "value": True}],
            actions=[{"type": "set_property", "target": "door", "property": "open", "value": True},
                     {"type": "play_sound", "name": "door_open"}],
            priority=20, description="Open the door after the player collects the key.")
        self.create_rule(
            name="Game over when health <= 0", trigger_event="every_tick",
            conditions=[{"type": "variable_comparison", "var": "$player.health",
                         "op": "<=", "value": 0}],
            actions=[{"type": "trigger_event", "event_name": "game_over",
                      "payload": {"reason": "health_depleted"}},
                     {"type": "change_scene", "scene": "game_over_screen"}],
            priority=100, description="End the game when player health reaches zero.")
        for name, desc, etype in [
            ("on_collision", "Fired when two entities collide.", EventType.COLLISION),
            ("on_interact", "Fired when the player interacts with an object.", EventType.INPUT),
            ("every_tick", "Fired every tick for continuous checks.", EventType.TRIGGER),
            ("game_over", "Fired when the game ends.", EventType.STATE_CHANGE),
            ("on_heartbeat", "Fired by the heartbeat timer.", EventType.TIMER),
        ]:
            self.create_event(name=name, description=desc, event_type=etype,
                              category="system" if etype != EventType.COLLISION else "gameplay")
        self.create_timer(name="heartbeat", duration=1.0, repeat=True,
                          associated_event="on_heartbeat")


# Backward-compatible aliases for existing __init__.py imports
EventSystemEngine = EventDrivenLogicSystem
EventRecord = EventDispatch
EventListener = EventBusSubscription


class EventPriority(str, Enum):
    """Backward-compatible priority enum."""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class EventChannel(str, Enum):
    """Backward-compatible channel enum."""
    GLOBAL = "global"
    GAMEPLAY = "gameplay"
    UI = "ui"
    AUDIO = "audio"
    NETWORK = "network"


class DispatchMode(str, Enum):
    """Backward-compatible dispatch mode enum."""
    BROADCAST = "broadcast"
    FIRST_ONLY = "first_only"
    ROUND_ROBIN = "round_robin"


def get_event_system() -> EventDrivenLogicSystem:
    """Get or create the global EventDrivenLogicSystem singleton instance."""
    return EventDrivenLogicSystem.get_instance()

