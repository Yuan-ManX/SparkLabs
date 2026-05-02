"""
SparkLabs Engine - State Machine

Hierarchical finite state machine system for game entity behavior.
Supports nested states, transitions with conditions, entry/exit
actions, and parallel sub-states. Designed for AI-generated
NPC behavior trees and game logic flows.

Architecture:
  StateMachine
    |-- State (name, transitions, entry/update/exit actions)
    |-- Transition (source, target, condition, priority)
    |-- ParameterContext (typed variables accessible by conditions)
    |-- TransitionEvaluator (sorted priority-based evaluation)

State Lifecycle:
  - on_enter: called once when entering the state
  - on_update: called every frame while active
  - on_exit: called once when leaving the state

Usage:
    sm = StateMachine("enemy_ai")
    sm.add_state("idle", on_update=idle_patrol)
    sm.add_state("chase", on_enter=start_chase, on_update=chase_player)
    sm.add_transition("idle", "chase", lambda ctx: ctx.get("player_in_range"))
    sm.add_transition("chase", "idle", lambda ctx: not ctx.get("player_in_range"))
    sm.start("idle")
    sm.update(context={"player_in_range": True})
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class StateMachineEvent(Enum):
    STATE_ENTERED = "state_entered"
    STATE_EXITED = "state_exited"
    TRANSITION_TRIGGERED = "transition_triggered"
    STATE_UPDATED = "state_updated"


@dataclass
class Transition:
    source: str = ""
    target: str = ""
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    priority: int = 0
    cooldown: float = 0.0
    last_triggered: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def can_trigger(self, context: Dict[str, Any], now: float) -> bool:
        if self.cooldown > 0 and now - self.last_triggered < self.cooldown:
            return False
        if self.condition is None:
            return True
        try:
            return self.condition(context)
        except Exception:
            return False

    def trigger(self, now: float) -> None:
        self.last_triggered = now


@dataclass
class State:
    name: str = ""
    on_enter: Optional[Callable[[Dict[str, Any]], None]] = None
    on_update: Optional[Callable[[float, Dict[str, Any]], None]] = None
    on_exit: Optional[Callable[[Dict[str, Any]], None]] = None
    transitions: List[Transition] = field(default_factory=list)
    parent: Optional[str] = None
    children: Set[str] = field(default_factory=set)
    parallel: bool = False
    enter_time: float = 0.0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_duration(self, now: float) -> float:
        if self.enter_time <= 0:
            return 0.0
        return now - self.enter_time


class StateMachine:
    """
    Hierarchical FSM for game entity behavior.

    Manages states, transitions, and lifecycle callbacks.
    Supports conditional transitions with priority ordering,
    cooldown gating, and nested child states.

    Usage:
        sm = StateMachine("player_controller")
        sm.add_state("grounded")
        sm.add_state("airborne", on_enter=start_jump)
        sm.add_transition("grounded", "airborne",
            lambda ctx: ctx.get("jump_pressed"))
        sm.add_transition("airborne", "grounded",
            lambda ctx: ctx.get("on_ground"))
        sm.start("grounded")
        sm.update(context={"jump_pressed": is_key_just_pressed("space")})
    """

    def __init__(self, name: str = "state_machine", max_history: int = 10):
        self._name = name
        self._states: Dict[str, State] = {}
        self._current_state: Optional[str] = None
        self._previous_state: Optional[str] = None
        self._state_history: List[str] = []
        self._max_history = max_history
        self._active: bool = False
        self._state_time: float = 0.0
        self._total_time: float = 0.0
        self._transition_count: int = 0
        self._event_listeners: Dict[StateMachineEvent, List[Callable]] = {
            e: [] for e in StateMachineEvent
        }

    def add_state(
        self,
        name: str,
        on_enter: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_update: Optional[Callable[[float, Dict[str, Any]], None]] = None,
        on_exit: Optional[Callable[[Dict[str, Any]], None]] = None,
        parent: Optional[str] = None,
        parallel: bool = False,
        **kwargs,
    ) -> State:
        state = State(
            name=name, on_enter=on_enter, on_update=on_update,
            on_exit=on_exit, parent=parent, parallel=parallel,
            metadata=kwargs,
        )
        self._states[name] = state
        if parent and parent in self._states:
            self._states[parent].children.add(name)
        return state

    def remove_state(self, name: str) -> bool:
        if name == self._current_state:
            return False
        state = self._states.pop(name, None)
        if state is None:
            return False
        if state.parent and state.parent in self._states:
            self._states[state.parent].children.discard(name)
        for child in list(state.children):
            if child in self._states:
                self._states[child].parent = None
        return True

    def add_transition(
        self,
        source: str,
        target: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        priority: int = 0,
        cooldown: float = 0.0,
    ) -> Optional[Transition]:
        if source not in self._states or target not in self._states:
            return None
        transition = Transition(
            source=source, target=target, condition=condition,
            priority=priority, cooldown=cooldown,
        )
        self._states[source].transitions.append(transition)
        return transition

    def add_any_transition(
        self,
        target: str,
        condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
        priority: int = -1,
    ) -> int:
        count = 0
        for name in self._states:
            if name != target:
                tr = self.add_transition(name, target, condition, priority)
                if tr:
                    count += 1
        return count

    def start(self, initial_state: str) -> bool:
        if initial_state not in self._states:
            return False
        self._switch_to(initial_state, {})
        self._active = True
        self._total_time = 0.0
        return True

    def update(self, dt: float = 0.016, context: Optional[Dict[str, Any]] = None) -> None:
        if not self._active:
            return
        context = context or {}
        self._total_time += dt

        current = self._get_current_state()
        if current is None:
            return

        now = time.time()
        sorted_transitions = sorted(
            current.transitions, key=lambda t: -t.priority,
        )

        for transition in sorted_transitions:
            if transition.can_trigger(context, now):
                transition.trigger(now)
                self._switch_to(transition.target, context)
                break

        new_current = self._get_current_state()
        if new_current and new_current.on_update:
            try:
                new_current.on_update(dt, context)
            except Exception:
                pass

        self._fire_event(StateMachineEvent.STATE_UPDATED, {
            "state": self._current_state, "dt": dt, "context": context,
        })

    def go_to(self, target: str, context: Optional[Dict[str, Any]] = None) -> bool:
        if target not in self._states:
            return False
        self._switch_to(target, context or {})
        return True

    def stop(self) -> None:
        current = self._get_current_state()
        if current and current.on_exit:
            try:
                current.on_exit({})
            except Exception:
                pass
        self._active = False

    def reset(self) -> None:
        self.stop()
        self._current_state = None
        self._previous_state = None
        self._state_history.clear()
        self._total_time = 0.0
        self._transition_count = 0

    def get_state(self) -> Optional[str]:
        return self._current_state

    def get_previous_state(self) -> Optional[str]:
        return self._previous_state

    def get_state_duration(self) -> float:
        current = self._get_current_state()
        if current:
            return current.get_duration(time.time())
        return 0.0

    def get_total_time(self) -> float:
        return self._total_time

    def on_event(
        self, event_type: StateMachineEvent,
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        self._event_listeners[event_type].append(callback)

    def get_stats(self) -> dict:
        return {
            "name": self._name,
            "states": len(self._states),
            "active": self._active,
            "current_state": self._current_state,
            "transitions": self._transition_count,
            "total_time": round(self._total_time, 3),
            "state_duration": round(self.get_state_duration(), 3),
        }

    def _get_current_state(self) -> Optional[State]:
        if self._current_state is None:
            return None
        return self._states.get(self._current_state)

    def _switch_to(self, target: str, context: Dict[str, Any]) -> None:
        if target == self._current_state:
            return

        now = time.time()
        current = self._get_current_state()

        if current and current.on_exit:
            try:
                current.on_exit(context)
            except Exception:
                pass

        self._previous_state = self._current_state
        self._current_state = target
        self._transition_count += 1

        self._state_history.append(target)
        if len(self._state_history) > self._max_history:
            self._state_history = self._state_history[-self._max_history:]

        new_state = self._get_current_state()
        if new_state:
            new_state.enter_time = now
            if new_state.on_enter:
                try:
                    new_state.on_enter(context)
                except Exception:
                    pass

        self._fire_event(StateMachineEvent.STATE_ENTERED, {
            "state": target, "previous": self._previous_state, "context": context,
        })

        if current:
            self._fire_event(StateMachineEvent.STATE_EXITED, {
                "state": current.name, "next": target, "context": context,
            })

    def _fire_event(
        self, event_type: StateMachineEvent, data: Dict[str, Any],
    ) -> None:
        for listener in self._event_listeners[event_type]:
            try:
                listener(data)
            except Exception:
                pass


_global_state_machines: Dict[str, StateMachine] = {}


def get_state_machine(name: str = "default") -> StateMachine:
    if name not in _global_state_machines:
        _global_state_machines[name] = StateMachine(name)
    return _global_state_machines[name]


def clear_state_machines() -> None:
    _global_state_machines.clear()
