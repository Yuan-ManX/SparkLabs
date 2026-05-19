"""
SparkLabs Engine - Behavior Runtime

Runtime execution system for AI behavior trees and finite state machines.
Drives NPC logic, enemy AI, companion behavior, and environmental interactions
through composable behavior nodes with condition evaluation and parallel execution.

Architecture:
  BehaviorRuntime
    |-- TreeExecutor (traverses and evaluates behavior tree nodes)
    |-- StateMachineRuntime (FSM transitions and state callbacks)
    |-- Blackboard (shared data store for inter-node communication)
    |-- ConditionEvaluator (composite condition checking with caching)
    |-- ActionDispatcher (executes leaf actions with timing control)

Node Types:
  - SELECTOR: runs children until one succeeds (OR logic)
  - SEQUENCE: runs children until one fails (AND logic)
  - PARALLEL: runs all children concurrently with finish policies
  - CONDITION: evaluates a predicate, succeeds or fails
  - ACTION: performs a concrete behavior with duration
  - DECORATOR: modifies child behavior (inverter, repeater, timer)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


class NodeStatus(Enum):
    IDLE = "idle"
    RUNNING = "running"
    SUCCESS = "success"
    FAILURE = "failure"


class NodeCategory(Enum):
    COMPOSITE = "composite"
    DECORATOR = "decorator"
    CONDITION = "condition"
    ACTION = "action"


class ParallelPolicy(Enum):
    REQUIRE_ONE = "require_one"
    REQUIRE_ALL = "require_all"


class FSMTransitionTrigger(Enum):
    AUTO = "auto"
    CONDITION = "condition"
    EVENT = "event"
    TIMER = "timer"


@dataclass
class BehaviorNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: NodeCategory = NodeCategory.ACTION
    description: str = ""
    status: NodeStatus = NodeStatus.IDLE
    children: List[str] = field(default_factory=list)
    parent_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    last_run: float = 0.0
    cooldown: float = 0.0
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "status": self.status.value,
            "children": self.children,
            "parent_id": self.parent_id,
            "properties": self.properties,
            "last_run": self.last_run,
            "cooldown": self.cooldown,
            "priority": self.priority,
        }


@dataclass
class BehaviorTree:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    root_id: str = ""
    nodes: Dict[str, BehaviorNode] = field(default_factory=dict)
    owner_id: str = ""
    is_active: bool = False
    tick_rate: float = 0.1
    last_tick: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "root_id": self.root_id,
            "nodes": {k: v.to_dict() for k, v in self.nodes.items()},
            "owner_id": self.owner_id,
            "is_active": self.is_active,
            "tick_rate": self.tick_rate,
            "node_count": len(self.nodes),
        }


@dataclass
class FSMState:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    is_initial: bool = False
    entry_actions: List[str] = field(default_factory=list)
    exit_actions: List[str] = field(default_factory=list)
    update_action: str = ""
    transitions: Dict[str, FSMTransition] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "is_initial": self.is_initial,
            "entry_actions": self.entry_actions,
            "exit_actions": self.exit_actions,
            "update_action": self.update_action,
            "transition_count": len(self.transitions),
            "transitions": {
                t_name: {"target_state": t.target_state, "trigger": t.trigger.value}
                for t_name, t in self.transitions.items()
            },
        }


@dataclass
class FSMTransition:
    name: str = ""
    target_state: str = ""
    trigger: FSMTransitionTrigger = FSMTransitionTrigger.CONDITION
    condition: str = ""
    event_name: str = ""
    timer_seconds: float = 0.0
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "target_state": self.target_state,
            "trigger": self.trigger.value,
            "condition": self.condition,
            "event_name": self.event_name,
            "timer_seconds": self.timer_seconds,
            "priority": self.priority,
        }


@dataclass
class FiniteStateMachine:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    states: Dict[str, FSMState] = field(default_factory=dict)
    current_state_id: str = ""
    owner_id: str = ""
    is_active: bool = False
    state_history: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        current = self.states.get(self.current_state_id)
        return {
            "id": self.id,
            "name": self.name,
            "states": {k: v.to_dict() for k, v in self.states.items()},
            "current_state": current.name if current else None,
            "current_state_id": self.current_state_id,
            "owner_id": self.owner_id,
            "is_active": self.is_active,
            "state_count": len(self.states),
            "history_size": len(self.state_history),
        }


class BehaviorRuntime:
    """Runtime engine for executing behavior trees and state machines."""

    _instance: Optional["BehaviorRuntime"] = None
    _lock = threading.RLock()

    _PRESET_TREES = {
        "patrol_guard": {
            "name": "Patrol Guard AI",
            "nodes": [
                {"id": "r", "name": "Root Selector", "cat": "COMPOSITE", "children": ["s1", "s2"]},
                {"id": "s1", "name": "Combat Sequence", "cat": "COMPOSITE", "children": ["c1", "a1", "a2"]},
                {"id": "c1", "name": "Enemy In Range?", "cat": "CONDITION", "props": {"check": "target_in_range"}},
                {"id": "a1", "name": "Chase Target", "cat": "ACTION", "props": {"speed": "run", "duration": 0}},
                {"id": "a2", "name": "Attack", "cat": "ACTION", "props": {"damage": 10, "cooldown": 1.5}},
                {"id": "s2", "name": "Patrol Sequence", "cat": "COMPOSITE", "children": ["a3", "a4"]},
                {"id": "a3", "name": "Move To Waypoint", "cat": "ACTION", "props": {"speed": "walk", "duration": 2.0}},
                {"id": "a4", "name": "Wait At Waypoint", "cat": "ACTION", "props": {"duration": 3.0}},
            ],
        },
        "shopkeeper": {
            "name": "Shopkeeper AI",
            "nodes": [
                {"id": "r", "name": "Root Selector", "cat": "COMPOSITE", "children": ["s1", "s2"]},
                {"id": "s1", "name": "Interact Sequence", "cat": "COMPOSITE", "children": ["c1", "a1"]},
                {"id": "c1", "name": "Player Nearby?", "cat": "CONDITION", "props": {"check": "player_in_range", "radius": 5}},
                {"id": "a1", "name": "Open Shop", "cat": "ACTION", "props": {"menu": "shop_ui"}},
                {"id": "s2", "name": "Idle Animation", "cat": "ACTION", "props": {"anim": "idle_browse"}},
            ],
        },
    }

    _PRESET_FSMS = {
        "enemy_combat": {
            "name": "Enemy Combat FSM",
            "states": [
                {"id": "idle", "name": "Idle", "initial": True},
                {"id": "alert", "name": "Alert"},
                {"id": "chase", "name": "Chase"},
                {"id": "attack", "name": "Attack"},
                {"id": "flee", "name": "Flee"},
                {"id": "dead", "name": "Dead"},
            ],
            "transitions": [
                ("idle", "alert", "player_detected"),
                ("alert", "chase", "player_in_range"),
                ("chase", "attack", "player_in_attack_range"),
                ("attack", "chase", "player_out_of_attack_range"),
                ("chase", "idle", "player_lost"),
                ("*", "dead", "health_zero"),
            ],
        },
    }

    def __init__(self) -> None:
        self._trees: Dict[str, BehaviorTree] = {}
        self._fsms: Dict[str, FiniteStateMachine] = {}
        self._blackboard: Dict[str, Dict[str, Any]] = {}
        self._action_registry: Dict[str, Callable] = {}
        self._condition_registry: Dict[str, Callable] = {}
        self._execution_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "BehaviorRuntime":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Behavior Tree Management ----

    def create_tree(self,
                    name: str,
                    owner_id: str = "",
                    tick_rate: float = 0.1) -> BehaviorTree:
        tree = BehaviorTree(
            name=name,
            owner_id=owner_id,
            tick_rate=tick_rate,
        )
        self._trees[tree.id] = tree
        return tree

    def add_node(self,
                 tree_id: str,
                 name: str,
                 category: str = "action",
                 parent_id: str = "",
                 properties: Optional[Dict[str, Any]] = None,
                 priority: int = 0,
                 cooldown: float = 0.0) -> Optional[BehaviorNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None
        try:
            cat = NodeCategory(category.lower())
        except ValueError:
            cat = NodeCategory.ACTION

        node = BehaviorNode(
            name=name,
            category=cat,
            properties=properties or {},
            priority=priority,
            cooldown=cooldown,
            parent_id=parent_id,
        )
        tree.nodes[node.id] = node
        if parent_id:
            parent = tree.nodes.get(parent_id)
            if parent:
                parent.children.append(node.id)
        if not tree.root_id:
            tree.root_id = node.id
        return node

    def activate_tree(self, tree_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        tree.is_active = True
        self._execution_log.append({
            "action": "tree_activated",
            "tree_id": tree_id,
            "tree_name": tree.name,
            "timestamp": time.time(),
        })
        return True

    def deactivate_tree(self, tree_id: str) -> bool:
        tree = self._trees.get(tree_id)
        if tree is None:
            return False
        tree.is_active = False
        for node in tree.nodes.values():
            node.status = NodeStatus.IDLE
        return True

    def get_tree(self, tree_id: str) -> Optional[BehaviorTree]:
        return self._trees.get(tree_id)

    def list_trees(self,
                   owner_id: Optional[str] = None) -> List[BehaviorTree]:
        trees = list(self._trees.values())
        if owner_id:
            return [t for t in trees if t.owner_id == owner_id]
        return trees

    # ---- Behavior Tree Execution ----

    def tick_tree(self, tree_id: str, delta_time: float = 0.016) -> Dict[str, Any]:
        tree = self._trees.get(tree_id)
        if tree is None or not tree.is_active:
            return {"ticked": False, "reason": "tree not found or inactive"}

        tree.last_tick += delta_time
        if tree.last_tick < tree.tick_rate and tree.tick_rate > 0:
            return {"ticked": False, "reason": "tick rate cooldown"}

        tree.last_tick = 0.0
        root_status = self._evaluate_node(tree, tree.root_id, delta_time)
        self._execution_log.append({
            "action": "tree_ticked",
            "tree_id": tree_id,
            "root_status": root_status.value,
            "timestamp": time.time(),
        })
        active_nodes = sum(
            1 for n in tree.nodes.values()
            if n.status == NodeStatus.RUNNING
        )
        return {
            "ticked": True,
            "tree_id": tree_id,
            "root_status": root_status.value,
            "active_nodes": active_nodes,
        }

    def _evaluate_node(self,
                       tree: BehaviorTree,
                       node_id: str,
                       delta_time: float) -> NodeStatus:
        node = tree.nodes.get(node_id)
        if node is None:
            return NodeStatus.FAILURE

        if node.cooldown > 0 and time.time() - node.last_run < node.cooldown:
            return NodeStatus.IDLE

        node.last_run = time.time()

        if node.category == NodeCategory.COMPOSITE:
            return self._evaluate_composite(tree, node, delta_time)
        elif node.category == NodeCategory.DECORATOR:
            return self._evaluate_decorator(tree, node, delta_time)
        elif node.category == NodeCategory.CONDITION:
            return self._evaluate_condition(node)
        elif node.category == NodeCategory.ACTION:
            return self._evaluate_action(node, delta_time)

        return NodeStatus.FAILURE

    def _evaluate_composite(self,
                            tree: BehaviorTree,
                            node: BehaviorNode,
                            delta_time: float) -> NodeStatus:
        if not node.children:
            return NodeStatus.FAILURE

        if node.name.lower().startswith("select"):
            for child_id in sorted(node.children,
                                   key=lambda c: tree.nodes.get(c, BehaviorNode()).priority,
                                   reverse=True):
                status = self._evaluate_node(tree, child_id, delta_time)
                if status == NodeStatus.SUCCESS or status == NodeStatus.RUNNING:
                    node.status = status
                    return status
            node.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        elif node.name.lower().startswith("sequence"):
            for child_id in node.children:
                status = self._evaluate_node(tree, child_id, delta_time)
                if status == NodeStatus.FAILURE:
                    node.status = NodeStatus.FAILURE
                    return NodeStatus.FAILURE
                if status == NodeStatus.RUNNING:
                    node.status = NodeStatus.RUNNING
                    return NodeStatus.RUNNING
            node.status = NodeStatus.SUCCESS
            return NodeStatus.SUCCESS

        elif node.name.lower().startswith("parallel"):
            running_exists = False
            success_count = 0
            for child_id in node.children:
                status = self._evaluate_node(tree, child_id, delta_time)
                if status == NodeStatus.RUNNING:
                    running_exists = True
                elif status == NodeStatus.SUCCESS:
                    success_count += 1

            if success_count == len(node.children):
                node.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            if success_count > 0:
                node.status = NodeStatus.RUNNING
                return NodeStatus.RUNNING
            node.status = NodeStatus.FAILURE
            return NodeStatus.FAILURE

        node.status = NodeStatus.FAILURE
        return NodeStatus.FAILURE

    def _evaluate_decorator(self,
                            tree: BehaviorTree,
                            node: BehaviorNode,
                            delta_time: float) -> NodeStatus:
        if not node.children:
            return NodeStatus.FAILURE

        if node.name.lower().startswith("invert"):
            child_status = self._evaluate_node(tree, node.children[0], delta_time)
            if child_status == NodeStatus.SUCCESS:
                node.status = NodeStatus.FAILURE
                return NodeStatus.FAILURE
            if child_status == NodeStatus.FAILURE:
                node.status = NodeStatus.SUCCESS
                return NodeStatus.SUCCESS
            node.status = child_status
            return child_status

        child_status = self._evaluate_node(tree, node.children[0], delta_time)
        node.status = child_status
        return child_status

    def _evaluate_condition(self, node: BehaviorNode) -> NodeStatus:
        check = node.properties.get("check", "")
        threshold = node.properties.get("threshold", 0.5)
        if check in self._condition_registry:
            result = self._condition_registry[check]()
            node.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
            return node.status
        simulated = random.random() > (1.0 - threshold)
        node.status = NodeStatus.SUCCESS if simulated else NodeStatus.FAILURE
        return node.status

    def _evaluate_action(self,
                         node: BehaviorNode,
                         delta_time: float) -> NodeStatus:
        duration = node.properties.get("duration", 0)
        if node.status == NodeStatus.IDLE:
            if duration > 0:
                node.status = NodeStatus.RUNNING
            else:
                node.status = NodeStatus.SUCCESS
        elif node.status == NodeStatus.RUNNING:
            elapsed = node.properties.get("_elapsed", 0.0) + delta_time
            if elapsed >= duration:
                node.status = NodeStatus.SUCCESS
            else:
                node.properties["_elapsed"] = elapsed
        return node.status

    # ---- Finite State Machine ----

    def create_fsm(self,
                   name: str,
                   owner_id: str = "") -> FiniteStateMachine:
        fsm = FiniteStateMachine(
            name=name,
            owner_id=owner_id,
        )
        self._fsms[fsm.id] = fsm
        return fsm

    def add_fsm_state(self,
                      fsm_id: str,
                      name: str,
                      is_initial: bool = False) -> Optional[FSMState]:
        fsm = self._fsms.get(fsm_id)
        if fsm is None:
            return None
        state = FSMState(name=name, is_initial=is_initial)
        fsm.states[state.id] = state
        if is_initial and not fsm.current_state_id:
            fsm.current_state_id = state.id
        return state

    def add_fsm_transition(self,
                           fsm_id: str,
                           from_state_id: str,
                           to_state_id: str,
                           name: str = "",
                           trigger: str = "condition",
                           condition: str = "",
                           event_name: str = "",
                           timer_seconds: float = 0.0) -> bool:
        fsm = self._fsms.get(fsm_id)
        if fsm is None:
            return False
        from_state = fsm.states.get(from_state_id)
        if from_state is None:
            return False
        try:
            trig = FSMTransitionTrigger(trigger.lower())
        except ValueError:
            trig = FSMTransitionTrigger.CONDITION
        transition = FSMTransition(
            name=name,
            target_state=to_state_id,
            trigger=trig,
            condition=condition,
            event_name=event_name,
            timer_seconds=timer_seconds,
        )
        from_state.transitions[name or to_state_id] = transition
        return True

    def activate_fsm(self, fsm_id: str) -> bool:
        fsm = self._fsms.get(fsm_id)
        if fsm is None:
            return False
        fsm.is_active = True
        return True

    def trigger_fsm_event(self,
                          fsm_id: str,
                          event_name: str) -> bool:
        fsm = self._fsms.get(fsm_id)
        if fsm is None or not fsm.is_active:
            return False
        current = fsm.states.get(fsm.current_state_id)
        if current is None:
            return False
        for name, trans in current.transitions.items():
            if trans.trigger == FSMTransitionTrigger.EVENT and trans.event_name == event_name:
                fsm.state_history.append(fsm.current_state_id)
                fsm.current_state_id = trans.target_state
                self._execution_log.append({
                    "action": "fsm_transition",
                    "fsm_id": fsm_id,
                    "from": current.name,
                    "to": fsm.states.get(trans.target_state, FSMState()).name,
                    "via": event_name,
                    "timestamp": time.time(),
                })
                return True
        return False

    def get_fsm(self, fsm_id: str) -> Optional[FiniteStateMachine]:
        return self._fsms.get(fsm_id)

    def list_fsms(self,
                  owner_id: Optional[str] = None) -> List[FiniteStateMachine]:
        fsms = list(self._fsms.values())
        if owner_id:
            return [f for f in fsms if f.owner_id == owner_id]
        return fsms

    # ---- Preset Loading ----

    def load_preset_tree(self, preset_key: str) -> Optional[BehaviorTree]:
        preset = self._PRESET_TREES.get(preset_key)
        if preset is None:
            return None
        tree = self.create_tree(preset["name"])
        for ndef in preset["nodes"]:
            self.add_node(
                tree.id,
                ndef["name"],
                ndef["cat"].lower(),
                parent_id="" if ndef.get("id") == "r" else "r",
                properties=ndef.get("props", {}),
            )
        self._rebuild_tree_structure(tree, preset["nodes"])
        return tree

    def _rebuild_tree_structure(self,
                                tree: BehaviorTree,
                                node_defs: List[Dict[str, Any]]) -> None:
        name_to_id = {}
        for ndef in node_defs:
            for nid, node in tree.nodes.items():
                if node.name == ndef["name"] and nid not in name_to_id.values():
                    name_to_id[ndef["id"]] = nid
                    break
        for ndef in node_defs:
            if "children" in ndef:
                parent_id = name_to_id.get(ndef["id"], "")
                parent = tree.nodes.get(parent_id)
                if parent:
                    parent.children = [
                        name_to_id.get(c, c)
                        for c in ndef["children"]
                        if name_to_id.get(c)
                    ]

    def load_preset_fsm(self, preset_key: str) -> Optional[FiniteStateMachine]:
        preset = self._PRESET_FSMS.get(preset_key)
        if preset is None:
            return None
        fsm = self.create_fsm(preset["name"])
        state_map: Dict[str, str] = {}
        for sdef in preset["states"]:
            state = self.add_fsm_state(fsm.id, sdef["name"], sdef.get("initial", False))
            if state:
                state_map[sdef["id"]] = state.id
        for from_id, to_id, trigger in preset["transitions"]:
            if from_id == "*":
                for s_state_id in fsm.states:
                    self.add_fsm_transition(
                        fsm.id, s_state_id,
                        state_map.get(to_id, ""),
                        f"{from_id}_to_{to_id}",
                        "event", event_name=trigger,
                    )
            else:
                self.add_fsm_transition(
                    fsm.id,
                    state_map.get(from_id, ""),
                    state_map.get(to_id, ""),
                    trigger,
                    "event", event_name=trigger,
                )
        return fsm

    def list_presets(self) -> Dict[str, Any]:
        return {
            "trees": list(self._PRESET_TREES.keys()),
            "fsms": list(self._PRESET_FSMS.keys()),
        }

    # ---- Blackboard ----

    def set_blackboard(self,
                       owner_id: str,
                       key: str,
                       value: Any) -> None:
        if owner_id not in self._blackboard:
            self._blackboard[owner_id] = {}
        self._blackboard[owner_id][key] = value

    def get_blackboard(self,
                       owner_id: str,
                       key: str,
                       default: Any = None) -> Any:
        return self._blackboard.get(owner_id, {}).get(key, default)

    # ---- Execution Log ----

    def get_execution_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._execution_log[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(
            len(t.nodes) for t in self._trees.values()
        )
        total_states = sum(
            len(f.states) for f in self._fsms.values()
        )
        active_trees = sum(1 for t in self._trees.values() if t.is_active)
        active_fsms = sum(1 for f in self._fsms.values() if f.is_active)
        return {
            "behavior_trees": len(self._trees),
            "active_trees": active_trees,
            "total_nodes": total_nodes,
            "finite_state_machines": len(self._fsms),
            "active_fsms": active_fsms,
            "total_states": total_states,
            "blackboard_entries": sum(len(v) for v in self._blackboard.values()),
            "execution_log_entries": len(self._execution_log),
            "preset_trees": len(self._PRESET_TREES),
            "preset_fsms": len(self._PRESET_FSMS),
        }


def get_behavior_runtime() -> BehaviorRuntime:
    return BehaviorRuntime.get_instance()