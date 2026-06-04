"""
SparkLabs Engine - State Machine Engine

A comprehensive hierarchical finite state machine system for game
entity behavior, animation control, AI decision-making, and
gameplay logic. Supports nested states, parallel sub-states,
parameterized transitions, and visual debug output.

Architecture:
  EngineStateMachine (Singleton)
    |-- State Definition (entry/update/exit callbacks with conditions)
    |-- Transition System (conditional, timed, event-driven transitions)
    |-- Hierarchical States (parent-child state nesting)
    |-- Parallel Sub-States (concurrent state execution)
    |-- State History (deep/shallow history pseudo-states)
    |-- Parameter System (typed parameters for transition conditions)
    |-- Visual Debugger (state graph export and active state tracking)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class StateMachineType(Enum):
    CLASSIC = "classic"
    HIERARCHICAL = "hierarchical"
    PUSH_DOWN_AUTOMATON = "push_down_automaton"
    BEHAVIOR_TREE_BACKED = "behavior_tree_backed"


class TransitionTrigger(Enum):
    CONDITION = "condition"
    EVENT = "event"
    TIMER = "timer"
    AUTO = "auto"
    PARAMETER_CHANGE = "parameter_change"
    ANIMATION_FINISHED = "animation_finished"
    EXTERNAL = "external"
    ANY_STATE = "any_state"


class StateType(Enum):
    NORMAL = "normal"
    ENTRY = "entry"
    EXIT = "exit"
    HISTORY = "history"
    PARALLEL = "parallel"
    BLEND_TREE = "blend_tree"


class ParameterType(Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STRING = "string"
    TRIGGER = "trigger"
    ENUM = "enum"


class ComparisonOperator(Enum):
    EQUALS = "equals"
    NOT_EQUALS = "not_equals"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    GREATER_OR_EQUAL = "greater_or_equal"
    LESS_OR_EQUAL = "less_or_equal"


class TransitionMode(Enum):
    IMMEDIATE = "immediate"
    BLEND = "blend"
    CROSSFADE = "crossfade"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MachineParameter:
    """A typed parameter for a state machine."""
    param_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "param"
    param_type: ParameterType = ParameterType.BOOL
    default_value: Any = None
    current_value: Any = None

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "param_id": self.param_id,
            "name": self.name,
            "type": self.param_type.value,
            "value": self.current_value,
            "default": self.default_value,
        }


@dataclass
class TransitionCondition:
    """A condition for evaluating whether a transition should fire."""
    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    parameter_name: str = ""
    operator: ComparisonOperator = ComparisonOperator.EQUALS
    compare_value: Any = None
    invert: bool = False

    def evaluate(self, params: Dict[str, MachineParameter]) -> bool:
        param = params.get(self.parameter_name)
        if param is None:
            return False
        val = param.current_value
        cmp = self.compare_value

        result = False
        try:
            if self.operator == ComparisonOperator.EQUALS:
                result = val == cmp
            elif self.operator == ComparisonOperator.NOT_EQUALS:
                result = val != cmp
            elif self.operator == ComparisonOperator.GREATER_THAN:
                result = float(val) > float(cmp)
            elif self.operator == ComparisonOperator.LESS_THAN:
                result = float(val) < float(cmp)
            elif self.operator == ComparisonOperator.GREATER_OR_EQUAL:
                result = float(val) >= float(cmp)
            elif self.operator == ComparisonOperator.LESS_OR_EQUAL:
                result = float(val) <= float(cmp)
        except (TypeError, ValueError):
            result = False

        return not result if self.invert else result

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "parameter": self.parameter_name,
            "operator": self.operator.value,
            "compare_value": self.compare_value,
            "invert": self.invert,
        }


@dataclass
class MachineTransition:
    """A transition between two states."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    from_state: str = ""
    to_state: str = ""
    trigger: TransitionTrigger = TransitionTrigger.CONDITION
    conditions: List[TransitionCondition] = field(default_factory=list)
    event_name: str = ""
    timer_duration: float = 0.0
    blend_duration: float = 0.0
    transition_mode: TransitionMode = TransitionMode.IMMEDIATE
    is_any_state: bool = False
    priority: int = 0
    on_transition_callbacks: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "name": self.name,
            "from": self.from_state,
            "to": self.to_state,
            "trigger": self.trigger.value,
            "condition_count": len(self.conditions),
            "priority": self.priority,
        }


@dataclass
class MachineState:
    """A state node in the state machine."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "State"
    state_type: StateType = StateType.NORMAL
    parent_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    on_enter_actions: List[str] = field(default_factory=list)
    on_update_actions: List[str] = field(default_factory=list)
    on_exit_actions: List[str] = field(default_factory=list)
    is_initial: bool = False
    is_active: bool = False
    active_child_id: str = ""
    enter_time: float = 0.0
    total_active_time: float = 0.0
    labels: List[str] = field(default_factory=list)
    color: str = "#4a9eff"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "type": self.state_type.value,
            "is_active": self.is_active,
            "is_initial": self.is_initial,
            "active_time": round(self.total_active_time, 3),
            "child_count": len(self.children_ids),
            "labels": self.labels,
            "color": self.color,
        }


@dataclass
class StateMachineDefinition:
    """A complete state machine definition."""
    machine_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "State Machine"
    machine_type: StateMachineType = StateMachineType.CLASSIC
    states: Dict[str, MachineState] = field(default_factory=dict)
    transitions: List[MachineTransition] = field(default_factory=list)
    parameters: Dict[str, MachineParameter] = field(default_factory=dict)
    initial_state_id: str = ""
    current_state_id: str = ""
    previous_state_id: str = ""
    is_running: bool = False
    create_time: float = field(default_factory=_time_module.time)
    update_count: int = 0
    labels: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "machine_id": self.machine_id,
            "name": self.name,
            "type": self.machine_type.value,
            "state_count": len(self.states),
            "transition_count": len(self.transitions),
            "parameter_count": len(self.parameters),
            "current_state": self.current_state_id,
            "is_running": self.is_running,
            "update_count": self.update_count,
        }

    def get_active_state(self) -> Optional[MachineState]:
        return self.states.get(self.current_state_id)

    def get_active_path(self) -> List[str]:
        """Get the full hierarchical path of active states."""
        path: List[str] = []
        current_id = self.current_state_id
        while current_id:
            state = self.states.get(current_id)
            if state is None:
                break
            path.append(state.name)
            if state.active_child_id:
                current_id = state.active_child_id
            else:
                break
        return path


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

class EngineStateMachine:
    """Singleton state machine orchestration engine."""

    _instance: Optional["EngineStateMachine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineStateMachine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._machines: Dict[str, StateMachineDefinition] = {}
        self._event_queue: Dict[str, List[str]] = {}
        self._transition_count: int = 0
        self._total_updates: int = 0

    @classmethod
    def get_instance(cls) -> "EngineStateMachine":
        return cls()

    # -- Machine Management --------------------------------------------------

    def create_machine(self, name: str = "State Machine",
                       machine_type: StateMachineType = StateMachineType.CLASSIC,
                       labels: Optional[List[str]] = None) -> StateMachineDefinition:
        with self._lock:
            machine = StateMachineDefinition(
                name=name,
                machine_type=machine_type,
                labels=labels or [],
            )
            self._machines[machine.machine_id] = machine
            return machine

    def get_machine(self, machine_id: str) -> Optional[StateMachineDefinition]:
        return self._machines.get(machine_id)

    def remove_machine(self, machine_id: str) -> bool:
        with self._lock:
            if machine_id in self._machines:
                del self._machines[machine_id]
                self._event_queue.pop(machine_id, None)
                return True
            return False

    def list_machines(self) -> List[StateMachineDefinition]:
        return list(self._machines.values())

    # -- Parameter Management ------------------------------------------------

    def add_parameter(self, machine_id: str, name: str,
                      param_type: ParameterType = ParameterType.BOOL,
                      default_value: Any = None) -> Optional[MachineParameter]:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return None
            param = MachineParameter(
                name=name, param_type=param_type,
                default_value=default_value,
            )
            machine.parameters[name] = param
            return param

    def set_parameter(self, machine_id: str, name: str,
                      value: Any) -> bool:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            param = machine.parameters.get(name)
            if param is None:
                return False
            param.current_value = value
            return True

    def get_parameter(self, machine_id: str,
                      name: str) -> Optional[MachineParameter]:
        machine = self._machines.get(machine_id)
        if machine is None:
            return None
        return machine.parameters.get(name)

    def trigger_parameter(self, machine_id: str, name: str) -> bool:
        """Set a trigger-type parameter to True (auto-resets after evaluation)."""
        return self.set_parameter(machine_id, name, True)

    # -- State Management ----------------------------------------------------

    def add_state(self, machine_id: str, name: str,
                  state_type: StateType = StateType.NORMAL,
                  parent_id: str = "",
                  is_initial: bool = False,
                  labels: Optional[List[str]] = None,
                  color: str = "#4a9eff") -> Optional[MachineState]:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return None
            state = MachineState(
                name=name, state_type=state_type,
                parent_id=parent_id, is_initial=is_initial,
                labels=labels or [], color=color,
            )
            machine.states[state.state_id] = state

            # Register as child of parent
            if parent_id and parent_id in machine.states:
                parent = machine.states[parent_id]
                if state.state_id not in parent.children_ids:
                    parent.children_ids.append(state.state_id)

            # Set as initial if needed
            if is_initial:
                if parent_id:
                    parent = machine.states.get(parent_id)
                    if parent:
                        parent.active_child_id = state.state_id
                else:
                    machine.initial_state_id = state.state_id
                    if not machine.current_state_id:
                        machine.current_state_id = state.state_id

            return state

    def get_state(self, machine_id: str, state_id: str) -> Optional[MachineState]:
        machine = self._machines.get(machine_id)
        if machine is None:
            return None
        return machine.states.get(state_id)

    # -- Transition Management -----------------------------------------------

    def add_transition(self, machine_id: str, name: str,
                       from_state: str, to_state: str,
                       trigger: TransitionTrigger = TransitionTrigger.CONDITION,
                       conditions: Optional[List[TransitionCondition]] = None,
                       event_name: str = "",
                       timer_duration: float = 0.0,
                       blend_duration: float = 0.0,
                       transition_mode: TransitionMode = TransitionMode.IMMEDIATE,
                       is_any_state: bool = False,
                       priority: int = 0) -> Optional[MachineTransition]:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return None
            trans = MachineTransition(
                name=name, from_state=from_state, to_state=to_state,
                trigger=trigger, conditions=conditions or [],
                event_name=event_name, timer_duration=timer_duration,
                blend_duration=blend_duration,
                transition_mode=transition_mode,
                is_any_state=is_any_state, priority=priority,
            )
            machine.transitions.append(trans)
            machine.transitions.sort(key=lambda t: t.priority, reverse=True)
            return trans

    def add_condition(self, machine_id: str, transition_id: str,
                      parameter_name: str,
                      operator: ComparisonOperator = ComparisonOperator.EQUALS,
                      compare_value: Any = None,
                      invert: bool = False) -> Optional[TransitionCondition]:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return None
            trans = None
            for t in machine.transitions:
                if t.transition_id == transition_id:
                    trans = t
                    break
            if trans is None:
                return None
            cond = TransitionCondition(
                parameter_name=parameter_name,
                operator=operator,
                compare_value=compare_value,
                invert=invert,
            )
            trans.conditions.append(cond)
            return cond

    def set_transition_callback(self, machine_id: str,
                                transition_id: str,
                                callback_name: str) -> bool:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            for t in machine.transitions:
                if t.transition_id == transition_id:
                    t.on_transition_callbacks.append(callback_name)
                    return True
            return False

    # -- Event System --------------------------------------------------------

    def send_event(self, machine_id: str, event_name: str) -> bool:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            if machine_id not in self._event_queue:
                self._event_queue[machine_id] = []
            self._event_queue[machine_id].append(event_name)
            return True

    def _consume_events(self, machine_id: str) -> List[str]:
        events = self._event_queue.get(machine_id, [])
        self._event_queue[machine_id] = []
        return events

    # -- State Machine Update ------------------------------------------------

    def start_machine(self, machine_id: str) -> bool:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            if not machine.current_state_id and machine.initial_state_id:
                machine.current_state_id = machine.initial_state_id
            machine.is_running = True
            # Activate initial state
            current = machine.states.get(machine.current_state_id)
            if current:
                current.is_active = True
                current.enter_time = _time_module.time()
            return True

    def stop_machine(self, machine_id: str) -> bool:
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            machine.is_running = False
            # Deactivate all states
            for state in machine.states.values():
                state.is_active = False
            return True

    def tick(self, machine_id: str, delta_time: float = 0.016) -> bool:
        """Update the state machine, evaluate transitions, and advance states."""
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None or not machine.is_running:
                return False

            # Update active state time
            current = machine.states.get(machine.current_state_id)
            if current:
                current.total_active_time += delta_time

            # Consume events
            events = self._consume_events(machine_id)

            # Evaluate transitions by priority
            fired = False
            candidate_transitions = machine.transitions
            # Sort by priority descending
            candidate_transitions.sort(key=lambda t: t.priority, reverse=True)

            for trans in candidate_transitions:
                if fired:
                    break
                if not trans.from_state:
                    continue

                # Check if from_state matches current state or is "any state"
                if not trans.is_any_state and trans.from_state != machine.current_state_id:
                    continue

                can_fire = False

                if trans.trigger == TransitionTrigger.EVENT:
                    can_fire = trans.event_name in events
                elif trans.trigger == TransitionTrigger.CONDITION:
                    can_fire = all(
                        c.evaluate(machine.parameters)
                        for c in trans.conditions
                    ) if trans.conditions else True
                elif trans.trigger == TransitionTrigger.TIMER:
                    if current and current.total_active_time >= trans.timer_duration:
                        can_fire = True
                elif trans.trigger == TransitionTrigger.AUTO:
                    can_fire = True
                elif trans.trigger == TransitionTrigger.ANY_STATE:
                    can_fire = True

                if can_fire:
                    self._execute_transition(machine, trans)
                    fired = True

            # Handle hierarchical children
            if current and current.active_child_id:
                child = machine.states.get(current.active_child_id)
                if child:
                    child.total_active_time += delta_time

            # Reset trigger parameters
            for param in machine.parameters.values():
                if param.param_type == ParameterType.TRIGGER:
                    param.current_value = False

            machine.update_count += 1
            self._total_updates += 1
            return True

    def _execute_transition(self, machine: StateMachineDefinition,
                            trans: MachineTransition) -> None:
        """Execute a state transition within a machine."""
        from_state = machine.states.get(machine.current_state_id)
        to_state = machine.states.get(trans.to_state)

        # Exit old state
        if from_state:
            from_state.is_active = False

        # Update machine state
        machine.previous_state_id = machine.current_state_id
        machine.current_state_id = trans.to_state

        # Enter new state
        if to_state:
            to_state.is_active = True
            to_state.enter_time = _time_module.time()
            to_state.total_active_time = 0.0

        self._transition_count += 1

    def force_state(self, machine_id: str, state_id: str) -> bool:
        """Force the machine to a specific state."""
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None or state_id not in machine.states:
                return False
            trans = MachineTransition(
                from_state=machine.current_state_id,
                to_state=state_id,
                trigger=TransitionTrigger.EXTERNAL,
            )
            self._execute_transition(machine, trans)
            return True

    def reset_machine(self, machine_id: str) -> bool:
        """Reset the machine to its initial state."""
        with self._lock:
            machine = self._machines.get(machine_id)
            if machine is None:
                return False
            for state in machine.states.values():
                state.is_active = False
                state.total_active_time = 0.0
                state.active_child_id = ""
            machine.current_state_id = machine.initial_state_id
            machine.previous_state_id = ""
            if machine.initial_state_id:
                initial = machine.states.get(machine.initial_state_id)
                if initial:
                    initial.is_active = True
                    initial.enter_time = _time_module.time()
            return True

    # -- Export / Debug ------------------------------------------------------

    def export_machine_graph(self, machine_id: str) -> Optional[Dict[str, Any]]:
        """Export a machine's state graph for visualization."""
        machine = self._machines.get(machine_id)
        if machine is None:
            return None
        return {
            "machine": machine.to_dict(),
            "states": [s.to_dict() for s in machine.states.values()],
            "transitions": [t.to_dict() for t in machine.transitions],
            "parameters": [p.to_dict() for p in machine.parameters.values()],
            "active_path": machine.get_active_path(),
        }

    def get_system_stats(self) -> Dict[str, Any]:
        """Return system-wide statistics."""
        return {
            "machine_count": len(self._machines),
            "total_transitions": self._transition_count,
            "total_updates": self._total_updates,
            "running_machines": sum(
                1 for m in self._machines.values() if m.is_running
            ),
            "machines": [
                {
                    "id": m.machine_id,
                    "name": m.name,
                    "current_state": m.current_state_id,
                    "is_running": m.is_running,
                    "state_count": len(m.states),
                }
                for m in self._machines.values()
            ],
        }


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_state_machine_engine() -> EngineStateMachine:
    return EngineStateMachine.get_instance()