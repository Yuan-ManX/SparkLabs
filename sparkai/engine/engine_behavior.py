"""
SparkLabs Engine - Engine Behavior System

Unified AI behavior system providing behavior trees, finite state machines,
and utility-based AI selection for game entities. Supports entity-level
behavior assignment, composite tick execution, and runtime behavior
orchestration.

Architecture:
  BehaviorEngine (Singleton)
    |-- BehaviorTree (hierarchical node graph with tick evaluation)
    |-- StateMachine (FSM with condition-based transitions)
    |-- UtilityAI (score-based action selection)
    |-- Entity Behavior Binding (per-entity behavior assignment)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BTStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class FSMStateType(Enum):
    ENTRY = "entry"
    ACTIVE = "active"
    EXIT = "exit"


class EvaluatorType(Enum):
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    LOGISTIC = "logistic"
    BOOLEAN = "boolean"


class BehaviorType(Enum):
    BEHAVIOR_TREE = "behavior_tree"
    STATE_MACHINE = "state_machine"
    UTILITY_AI = "utility_ai"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BTCondition:
    """A condition node for behavior tree evaluation."""
    condition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    evaluator: Callable[[Dict[str, Any]], bool] = field(default_factory=lambda: lambda _: True)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "parameters": dict(self.parameters),
        }


@dataclass
class BTAction:
    """An action node for behavior tree execution."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    executor: Callable[[Dict[str, Any]], BTStatus] = field(
        default_factory=lambda: lambda _: BTStatus.SUCCESS
    )
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "parameters": dict(self.parameters),
        }


@dataclass
class BTNode:
    """A node in a behavior tree graph."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    node_type: str = "action"  # sequence, selector, parallel, condition, action, decorator, inverter, repeater
    name: str = ""
    condition: Optional[BTCondition] = None
    action: Optional[BTAction] = None
    children: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "name": self.name,
            "children": list(self.children),
            "parameters": dict(self.parameters),
        }
        if self.condition is not None:
            result["condition"] = self.condition.to_dict()
        if self.action is not None:
            result["action"] = self.action.to_dict()
        return result


@dataclass
class BehaviorTree:
    """A complete behavior tree definition."""
    tree_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Behavior Tree"
    root_node_id: str = ""
    nodes: Dict[str, BTNode] = field(default_factory=dict)
    blackboard: Dict[str, Any] = field(default_factory=dict)
    _running_indices: Dict[str, int] = field(default_factory=dict)
    _repeat_counts: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "root_node_id": self.root_node_id,
            "node_count": len(self.nodes),
            "nodes": {nid: n.to_dict() for nid, n in self.nodes.items()},
            "blackboard": dict(self.blackboard),
        }


@dataclass
class FSMTransition:
    """A transition between two FSM states."""
    transition_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_state: str = ""
    to_state: str = ""
    conditions: List[BTCondition] = field(default_factory=list)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "transition_id": self.transition_id,
            "from_state": self.from_state,
            "to_state": self.to_state,
            "condition_count": len(self.conditions),
            "priority": self.priority,
        }


@dataclass
class FSMState:
    """A state within a finite state machine."""
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "State"
    on_enter: Optional[List[BTAction]] = None
    on_update: Optional[List[BTAction]] = None
    on_exit: Optional[List[BTAction]] = None
    transitions: List[FSMTransition] = field(default_factory=list)
    timeout: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "name": self.name,
            "has_enter": self.on_enter is not None and len(self.on_enter) > 0,
            "has_update": self.on_update is not None and len(self.on_update) > 0,
            "has_exit": self.on_exit is not None and len(self.on_exit) > 0,
            "transition_count": len(self.transitions),
            "timeout": self.timeout,
        }


@dataclass
class StateMachine:
    """A complete finite state machine definition."""
    fsm_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "State Machine"
    initial_state: str = ""
    states: Dict[str, FSMState] = field(default_factory=dict)
    current_state: str = ""
    state_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fsm_id": self.fsm_id,
            "name": self.name,
            "initial_state": self.initial_state,
            "current_state": self.current_state,
            "state_time": round(self.state_time, 4),
            "state_count": len(self.states),
        }


@dataclass
class UtilityAction:
    """A selectable action in a utility-based AI system."""
    action_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Action"
    evaluator: Callable[[Dict[str, Any]], float] = field(default_factory=lambda: lambda _: 0.0)
    executor: Callable[[Dict[str, Any]], BTStatus] = field(
        default_factory=lambda: lambda _: BTStatus.SUCCESS
    )
    parameters: Dict[str, Any] = field(default_factory=dict)
    cooldown: float = 0.0
    last_executed: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_id": self.action_id,
            "name": self.name,
            "cooldown": self.cooldown,
            "last_executed": self.last_executed,
            "parameters": dict(self.parameters),
        }


@dataclass
class UtilityAI:
    """A utility-based AI system with scored action selection."""
    utility_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "Utility AI"
    actions: Dict[str, UtilityAction] = field(default_factory=dict)
    selection_mode: str = "highest"  # highest, weighted_random, threshold
    threshold: float = 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "utility_id": self.utility_id,
            "name": self.name,
            "action_count": len(self.actions),
            "selection_mode": self.selection_mode,
            "threshold": self.threshold,
        }


# ---------------------------------------------------------------------------
# Behavior Engine Singleton
# ---------------------------------------------------------------------------

class BehaviorEngine:
    """Singleton engine for behavior tree, FSM, and utility AI orchestration."""

    _instance: Optional["BehaviorEngine"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "BehaviorEngine":
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
        self._behavior_trees: Dict[str, BehaviorTree] = {}
        self._state_machines: Dict[str, StateMachine] = {}
        self._utility_ais: Dict[str, UtilityAI] = {}
        self._entity_behaviors: Dict[str, Dict[str, str]] = {}
        self._tick_count: int = 0
        self._total_ticks: int = 0

    @classmethod
    def get_instance(cls) -> "BehaviorEngine":
        return cls()

    # ------------------------------------------------------------------
    # Behavior Tree Operations
    # ------------------------------------------------------------------

    def create_behavior_tree(
        self, name: str, root_node: Optional[BTNode] = None
    ) -> BehaviorTree:
        with self._lock:
            tree = BehaviorTree(name=name)
            if root_node is not None:
                tree.root_node_id = root_node.node_id
                tree.nodes[root_node.node_id] = root_node
            self._behavior_trees[tree.tree_id] = tree
            return tree

    def add_node(
        self, tree_id: str, node: BTNode, parent_id: Optional[str] = None
    ) -> bool:
        with self._lock:
            tree = self._behavior_trees.get(tree_id)
            if tree is None:
                return False
            if node.node_id in tree.nodes:
                return False
            tree.nodes[node.node_id] = node
            if parent_id is not None and parent_id in tree.nodes:
                parent = tree.nodes[parent_id]
                if node.node_id not in parent.children:
                    parent.children.append(node.node_id)
            if not tree.root_node_id or tree.root_node_id not in tree.nodes:
                tree.root_node_id = node.node_id
            return True

    def remove_node(self, tree_id: str, node_id: str) -> bool:
        with self._lock:
            tree = self._behavior_trees.get(tree_id)
            if tree is None:
                return False
            if node_id not in tree.nodes:
                return False
            if node_id == tree.root_node_id:
                return False
            # Remove from parent children lists
            for parent_node in tree.nodes.values():
                if node_id in parent_node.children:
                    parent_node.children.remove(node_id)
            # Remove node and its subtree
            self._remove_subtree(tree, node_id)
            tree._running_indices.pop(node_id, None)
            tree._repeat_counts.pop(node_id, None)
            return True

    def _remove_subtree(self, tree: BehaviorTree, node_id: str) -> None:
        node = tree.nodes.get(node_id)
        if node is None:
            return
        for child_id in list(node.children):
            self._remove_subtree(tree, child_id)
        tree.nodes.pop(node_id, None)

    def get_behavior_tree(self, tree_id: str) -> Optional[BehaviorTree]:
        return self._behavior_trees.get(tree_id)

    def tick_tree(
        self, tree_id: str, blackboard: Optional[Dict[str, Any]] = None
    ) -> BTStatus:
        tree = self._behavior_trees.get(tree_id)
        if tree is None:
            return BTStatus.FAILURE
        if blackboard is not None:
            tree.blackboard = blackboard
        root_node = tree.nodes.get(tree.root_node_id)
        if root_node is None:
            return BTStatus.FAILURE
        status = self._tick_node(tree, root_node)
        self._total_ticks += 1
        return status

    def _tick_node(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        node_type = node.node_type.lower()

        if node_type == "sequence":
            return self._tick_sequence(tree, node)
        elif node_type == "selector":
            return self._tick_selector(tree, node)
        elif node_type == "parallel":
            return self._tick_parallel(tree, node)
        elif node_type == "condition":
            return self._tick_condition(tree, node)
        elif node_type == "action":
            return self._tick_action(tree, node)
        elif node_type == "inverter":
            return self._tick_inverter(tree, node)
        elif node_type == "repeater":
            return self._tick_repeater(tree, node)
        elif node_type == "decorator":
            return self._tick_decorator(tree, node)
        else:
            return BTStatus.FAILURE

    def _tick_sequence(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        index = tree._running_indices.get(node.node_id, 0)
        while index < len(node.children):
            child_id = node.children[index]
            child = tree.nodes.get(child_id)
            if child is None:
                index += 1
                continue
            status = self._tick_node(tree, child)
            if status == BTStatus.FAILURE:
                tree._running_indices.pop(node.node_id, None)
                return BTStatus.FAILURE
            if status == BTStatus.RUNNING:
                tree._running_indices[node.node_id] = index
                return BTStatus.RUNNING
            index += 1
        tree._running_indices.pop(node.node_id, None)
        return BTStatus.SUCCESS

    def _tick_selector(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        index = tree._running_indices.get(node.node_id, 0)
        while index < len(node.children):
            child_id = node.children[index]
            child = tree.nodes.get(child_id)
            if child is None:
                index += 1
                continue
            status = self._tick_node(tree, child)
            if status == BTStatus.SUCCESS:
                tree._running_indices.pop(node.node_id, None)
                return BTStatus.SUCCESS
            if status == BTStatus.RUNNING:
                tree._running_indices[node.node_id] = index
                return BTStatus.RUNNING
            index += 1
        tree._running_indices.pop(node.node_id, None)
        return BTStatus.FAILURE

    def _tick_parallel(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        required_successes = node.parameters.get("required_successes", len(node.children))
        success_count = 0
        failure_count = 0
        any_running = False
        for child_id in node.children:
            child = tree.nodes.get(child_id)
            if child is None:
                failure_count += 1
                continue
            status = self._tick_node(tree, child)
            if status == BTStatus.SUCCESS:
                success_count += 1
            elif status == BTStatus.FAILURE:
                failure_count += 1
            elif status == BTStatus.RUNNING:
                any_running = True
        if success_count >= required_successes:
            return BTStatus.SUCCESS
        if failure_count > len(node.children) - required_successes:
            return BTStatus.FAILURE
        if any_running:
            return BTStatus.RUNNING
        return BTStatus.FAILURE

    def _tick_condition(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        if node.condition is None:
            return BTStatus.FAILURE
        try:
            result = node.condition.evaluator(tree.blackboard)
            return BTStatus.SUCCESS if result else BTStatus.FAILURE
        except Exception:
            return BTStatus.FAILURE

    def _tick_action(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        if node.action is None:
            return BTStatus.FAILURE
        try:
            return node.action.executor(tree.blackboard)
        except Exception:
            return BTStatus.FAILURE

    def _tick_inverter(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        if not node.children:
            return BTStatus.FAILURE
        child = tree.nodes.get(node.children[0])
        if child is None:
            return BTStatus.FAILURE
        status = self._tick_node(tree, child)
        if status == BTStatus.SUCCESS:
            return BTStatus.FAILURE
        if status == BTStatus.FAILURE:
            return BTStatus.SUCCESS
        return BTStatus.RUNNING

    def _tick_repeater(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        if not node.children:
            return BTStatus.FAILURE
        child = tree.nodes.get(node.children[0])
        if child is None:
            return BTStatus.FAILURE
        max_repeats = node.parameters.get("times", -1)
        count = tree._repeat_counts.get(node.node_id, 0)
        if max_repeats >= 0 and count >= max_repeats:
            tree._repeat_counts.pop(node.node_id, None)
            return BTStatus.SUCCESS
        status = self._tick_node(tree, child)
        if status == BTStatus.SUCCESS:
            count += 1
            tree._repeat_counts[node.node_id] = count
            if max_repeats >= 0 and count >= max_repeats:
                tree._repeat_counts.pop(node.node_id, None)
                return BTStatus.SUCCESS
            return BTStatus.RUNNING
        if status == BTStatus.FAILURE:
            tree._repeat_counts.pop(node.node_id, None)
            return BTStatus.FAILURE
        return BTStatus.RUNNING

    def _tick_decorator(self, tree: BehaviorTree, node: BTNode) -> BTStatus:
        if not node.children:
            return BTStatus.FAILURE
        child = tree.nodes.get(node.children[0])
        if child is None:
            return BTStatus.FAILURE
        decorator_type = node.parameters.get("type", "")

        if decorator_type == "timeout":
            timeout = node.parameters.get("timeout", 5.0)
            start_time = node.parameters.get("_start_time", time.time())
            node.parameters["_start_time"] = start_time
            if time.time() - start_time > timeout:
                return BTStatus.FAILURE
            return self._tick_node(tree, child)

        if decorator_type == "cooldown":
            cooldown = node.parameters.get("cooldown", 1.0)
            last_run = node.parameters.get("_last_run", 0.0)
            now = time.time()
            if now - last_run < cooldown:
                return BTStatus.RUNNING
            status = self._tick_node(tree, child)
            node.parameters["_last_run"] = now
            return status

        if decorator_type == "succeeder":
            self._tick_node(tree, child)
            return BTStatus.SUCCESS

        if decorator_type == "until_failure":
            status = self._tick_node(tree, child)
            if status == BTStatus.FAILURE:
                return BTStatus.SUCCESS
            return BTStatus.RUNNING

        # Default: pass through child status
        return self._tick_node(tree, child)

    # ------------------------------------------------------------------
    # State Machine Operations
    # ------------------------------------------------------------------

    def create_state_machine(self, name: str, initial_state: str) -> StateMachine:
        with self._lock:
            fsm = StateMachine(name=name, initial_state=initial_state)
            self._state_machines[fsm.fsm_id] = fsm
            return fsm

    def add_state(self, fsm_id: str, state: FSMState) -> bool:
        with self._lock:
            fsm = self._state_machines.get(fsm_id)
            if fsm is None:
                return False
            if state.state_id in fsm.states:
                return False
            fsm.states[state.state_id] = state
            if fsm.initial_state == state.state_id:
                fsm.current_state = state.state_id
            return True

    def add_transition(
        self,
        fsm_id: str,
        from_state: str,
        to_state: str,
        conditions: Optional[List[BTCondition]] = None,
        priority: int = 0,
    ) -> Optional[FSMTransition]:
        with self._lock:
            fsm = self._state_machines.get(fsm_id)
            if fsm is None:
                return None
            transition = FSMTransition(
                from_state=from_state,
                to_state=to_state,
                conditions=conditions or [],
                priority=priority,
            )
            state = fsm.states.get(from_state)
            if state is None:
                return None
            state.transitions.append(transition)
            state.transitions.sort(key=lambda t: t.priority, reverse=True)
            return transition

    def get_state_machine(self, fsm_id: str) -> Optional[StateMachine]:
        return self._state_machines.get(fsm_id)

    def tick_fsm(
        self,
        fsm_id: str,
        delta_time: float,
        blackboard: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        fsm = self._state_machines.get(fsm_id)
        if fsm is None:
            return None
        if not fsm.current_state:
            if fsm.initial_state:
                fsm.current_state = fsm.initial_state
                fsm.state_time = 0.0
                self._execute_state_enter(fsm, fsm.current_state, blackboard or {})
            return fsm.current_state

        current = fsm.states.get(fsm.current_state)
        if current is None:
            return fsm.current_state

        fsm.state_time += delta_time

        # Check timeout
        if current.timeout > 0.0 and fsm.state_time >= current.timeout:
            self._transition_to_state(fsm, current, fsm.initial_state, blackboard or {})
            return fsm.current_state

        # Evaluate transitions by priority
        fired_transition = None
        for trans in current.transitions:
            if self._evaluate_fsm_transition(trans, blackboard or {}):
                fired_transition = trans
                break

        if fired_transition is not None:
            self._transition_to_state(
                fsm, current, fired_transition.to_state, blackboard or {}
            )
        else:
            # Execute on_update actions for current state
            self._execute_state_update(fsm, fsm.current_state, blackboard or {})

        return fsm.current_state

    def _evaluate_fsm_transition(
        self, transition: FSMTransition, blackboard: Dict[str, Any]
    ) -> bool:
        if not transition.conditions:
            return True
        for cond in transition.conditions:
            try:
                if not cond.evaluator(blackboard):
                    return False
            except Exception:
                return False
        return True

    def _transition_to_state(
        self,
        fsm: StateMachine,
        current: FSMState,
        to_state_id: str,
        blackboard: Dict[str, Any],
    ) -> None:
        # Execute exit actions
        self._run_action_list(current.on_exit, blackboard)
        # Change state
        fsm.current_state = to_state_id
        fsm.state_time = 0.0
        # Execute enter actions
        self._execute_state_enter(fsm, to_state_id, blackboard)

    def _execute_state_enter(
        self, fsm: StateMachine, state_id: str, blackboard: Dict[str, Any]
    ) -> None:
        state = fsm.states.get(state_id)
        if state is None:
            return
        self._run_action_list(state.on_enter, blackboard)

    def _execute_state_update(
        self, fsm: StateMachine, state_id: str, blackboard: Dict[str, Any]
    ) -> None:
        state = fsm.states.get(state_id)
        if state is None:
            return
        self._run_action_list(state.on_update, blackboard)

    def _run_action_list(
        self, actions: Optional[List[BTAction]], blackboard: Dict[str, Any]
    ) -> None:
        if actions is None:
            return
        for action in actions:
            try:
                action.executor(blackboard)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Utility AI Operations
    # ------------------------------------------------------------------

    def create_utility_ai(
        self, name: str, selection_mode: str = "highest"
    ) -> UtilityAI:
        with self._lock:
            utility = UtilityAI(name=name, selection_mode=selection_mode)
            self._utility_ais[utility.utility_id] = utility
            return utility

    def add_utility_action(self, utility_id: str, action: UtilityAction) -> bool:
        with self._lock:
            utility = self._utility_ais.get(utility_id)
            if utility is None:
                return False
            if action.action_id in utility.actions:
                return False
            utility.actions[action.action_id] = action
            return True

    def get_utility_ai(self, utility_id: str) -> Optional[UtilityAI]:
        return self._utility_ais.get(utility_id)

    def evaluate_utility(
        self, utility_id: str, blackboard: Dict[str, Any]
    ) -> Optional[UtilityAction]:
        utility = self._utility_ais.get(utility_id)
        if utility is None:
            return None
        if not utility.actions:
            return None

        now = time.time()
        scored: List[Tuple[float, UtilityAction]] = []

        for action in utility.actions.values():
            # Check cooldown
            if action.cooldown > 0.0 and (now - action.last_executed) < action.cooldown:
                continue
            try:
                score = action.evaluator(blackboard)
            except Exception:
                score = 0.0
            scored.append((score, action))

        if not scored:
            return None

        mode = utility.selection_mode.lower()

        if mode == "highest":
            scored.sort(key=lambda item: item[0], reverse=True)
            selected = scored[0][1]
            selected.last_executed = now
            return selected

        elif mode == "weighted_random":
            total = sum(max(0.0, s) for s, _ in scored)
            if total <= 0.0:
                return None
            roll = random.random() * total
            cumulative = 0.0
            for score, action in scored:
                cumulative += max(0.0, score)
                if roll <= cumulative:
                    action.last_executed = now
                    return action
            return scored[-1][1] if scored else None

        elif mode == "threshold":
            eligible = [(s, a) for s, a in scored if s >= utility.threshold]
            if not eligible:
                return None
            eligible.sort(key=lambda item: item[0], reverse=True)
            selected = eligible[0][1]
            selected.last_executed = now
            return selected

        else:
            return None

    # ------------------------------------------------------------------
    # Entity Behavior Binding
    # ------------------------------------------------------------------

    def assign_behavior(
        self, entity_id: str, behavior_type: BehaviorType, behavior_id: str
    ) -> bool:
        with self._lock:
            if entity_id not in self._entity_behaviors:
                self._entity_behaviors[entity_id] = {}
            self._entity_behaviors[entity_id][behavior_type.value] = behavior_id
            return True

    def remove_behavior(
        self, entity_id: str, behavior_type: BehaviorType
    ) -> bool:
        with self._lock:
            behaviors = self._entity_behaviors.get(entity_id)
            if behaviors is None:
                return False
            if behavior_type.value not in behaviors:
                return False
            del behaviors[behavior_type.value]
            if not behaviors:
                del self._entity_behaviors[entity_id]
            return True

    def get_entity_behavior(self, entity_id: str) -> Dict[str, str]:
        return dict(self._entity_behaviors.get(entity_id, {}))

    def tick_entity(
        self,
        entity_id: str,
        delta_time: float,
        blackboard: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        bb = blackboard or {}
        behaviors = self._entity_behaviors.get(entity_id, {})
        result: Dict[str, Any] = {
            "entity_id": entity_id,
            "delta_time": delta_time,
            "tree_status": None,
            "fsm_state": None,
            "utility_action": None,
        }

        # Tick behavior tree if assigned
        tree_id = behaviors.get(BehaviorType.BEHAVIOR_TREE.value)
        if tree_id is not None:
            result["tree_status"] = self.tick_tree(tree_id, bb).value

        # Tick state machine if assigned
        fsm_id = behaviors.get(BehaviorType.STATE_MACHINE.value)
        if fsm_id is not None:
            result["fsm_state"] = self.tick_fsm(fsm_id, delta_time, bb)

        # Evaluate utility AI if assigned
        utility_id = behaviors.get(BehaviorType.UTILITY_AI.value)
        if utility_id is not None:
            selected = self.evaluate_utility(utility_id, bb)
            if selected is not None:
                result["utility_action"] = selected.action_id

        self._tick_count += 1
        return result

    # ------------------------------------------------------------------
    # Listing and Statistics
    # ------------------------------------------------------------------

    def list_behavior_trees(self) -> List[Dict[str, Any]]:
        return [tree.to_dict() for tree in self._behavior_trees.values()]

    def list_state_machines(self) -> List[Dict[str, Any]]:
        return [fsm.to_dict() for fsm in self._state_machines.values()]

    def list_utility_ais(self) -> List[Dict[str, Any]]:
        return [util.to_dict() for util in self._utility_ais.values()]

    def get_stats(self) -> Dict[str, Any]:
        entity_count = len(self._entity_behaviors)
        entity_with_trees = sum(
            1 for b in self._entity_behaviors.values()
            if BehaviorType.BEHAVIOR_TREE.value in b
        )
        entity_with_fsms = sum(
            1 for b in self._entity_behaviors.values()
            if BehaviorType.STATE_MACHINE.value in b
        )
        entity_with_utility = sum(
            1 for b in self._entity_behaviors.values()
            if BehaviorType.UTILITY_AI.value in b
        )
        return {
            "behavior_tree_count": len(self._behavior_trees),
            "state_machine_count": len(self._state_machines),
            "utility_ai_count": len(self._utility_ais),
            "entity_count": entity_count,
            "entities_with_trees": entity_with_trees,
            "entities_with_fsms": entity_with_fsms,
            "entities_with_utility": entity_with_utility,
            "tick_count": self._tick_count,
            "total_ticks": self._total_ticks,
        }

    def reset(self) -> None:
        with self._lock:
            self._behavior_trees.clear()
            self._state_machines.clear()
            self._utility_ais.clear()
            self._entity_behaviors.clear()
            self._tick_count = 0
            self._total_ticks = 0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------

def get_behavior_engine() -> BehaviorEngine:
    """Return the singleton BehaviorEngine instance."""
    return BehaviorEngine.get_instance()