"""
SparkLabs Engine - Behavior Orchestrator

Behavior tree orchestration system for AI-driven game entity logic.
Manages behavior trees, nodes, transitions, and runtime tick execution
for autonomous agent decision-making.

Architecture:
  EngineBehaviorOrchestrator (singleton)
    |-- BehaviorNode (tree node with condition/action/decorator logic)
    |-- BehaviorTree (rooted tree structure bound to an agent)
    |-- BehaviorContext (runtime tick context with sensor/world/goal data)
    |-- BehaviorTransition (cross-behavior transition rule)
    |-- NodeType / TransitionType / BehaviorResult (domain enums)
"""

from __future__ import annotations

import json
import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class NodeType(Enum):
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    PARALLEL = "parallel"
    CONDITION = "condition"
    ACTION = "action"
    DECORATOR = "decorator"
    INVERTER = "inverter"
    REPEATER = "repeater"
    SUCCEEDER = "succeeder"
    FAILER = "failer"
    RANDOM_SELECTOR = "random_selector"
    PRIORITY_SELECTOR = "priority_selector"
    UTILITY_SELECTOR = "utility_selector"
    STATE_CHECK = "state_check"
    SUB_TREE = "sub_tree"
    SERVICE = "service"


class TransitionType(Enum):
    IMMEDIATE = "immediate"
    BLENDED = "blended"
    CONDITIONAL = "conditional"
    TRIGGERED = "triggered"
    INTERRUPT = "interrupt"
    PROBABILISTIC = "probabilistic"


class BehaviorResult(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    SUSPENDED = "suspended"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class BehaviorNode:
    """A single node in a behavior tree."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: str = NodeType.ACTION.value
    name: str = ""
    description: str = ""
    parent_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    condition: str = ""
    action: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    cooldown: float = 0.0
    timeout: float = 0.0
    interruptible: bool = True
    success_count: int = 0
    failure_count: int = 0
    last_result: str = ""
    last_execution_time: float = 0.0
    tags: List[str] = field(default_factory=list)

    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    decorator_type: str = ""
    decorator_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "description": self.description,
            "parent_id": self.parent_id,
            "children_ids": list(self.children_ids),
            "condition": self.condition,
            "action": self.action,
            "params": dict(self.params),
            "priority": self.priority,
            "cooldown": self.cooldown,
            "timeout": self.timeout,
            "interruptible": self.interruptible,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "last_result": self.last_result,
            "last_execution_time": self.last_execution_time,
            "tags": list(self.tags),
        }


@dataclass
class BehaviorTree:
    """A rooted behavior tree bound to an agent."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    root_node_id: str = ""
    agent_id: str = ""
    is_active: bool = False
    tick_rate: float = 0.1
    total_nodes: int = 0
    total_ticks: int = 0
    success_rate: float = 0.0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_tick_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "root_node_id": self.root_node_id,
            "agent_id": self.agent_id,
            "is_active": self.is_active,
            "tick_rate": self.tick_rate,
            "total_nodes": self.total_nodes,
            "total_ticks": self.total_ticks,
            "success_rate": self.success_rate,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class BehaviorContext:
    """Runtime context provided to a behavior tree during a tick."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    agent_id: str = ""
    sensor_data: Dict[str, Any] = field(default_factory=dict)
    world_state: Dict[str, Any] = field(default_factory=dict)
    goal_stack: List[str] = field(default_factory=list)
    memory_snapshot: Dict[str, Any] = field(default_factory=dict)
    blackboard: Dict[str, Any] = field(default_factory=dict)
    personality_vector: Dict[str, float] = field(default_factory=dict)
    emotional_state: Dict[str, float] = field(default_factory=dict)
    delta_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "sensor_data": dict(self.sensor_data),
            "world_state": dict(self.world_state),
            "goal_stack": list(self.goal_stack),
            "memory_snapshot": dict(self.memory_snapshot),
            "blackboard": dict(self.blackboard),
            "personality_vector": dict(self.personality_vector),
            "emotional_state": dict(self.emotional_state),
            "delta_time": self.delta_time,
        }


@dataclass
class BehaviorTransition:
    """A transition rule between two behavior nodes."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_behavior_id: str = ""
    to_behavior_id: str = ""
    transition_type: str = TransitionType.IMMEDIATE.value
    condition: str = ""
    probability: float = 1.0
    priority: int = 0
    timer: float = 0.0
    trigger_event: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_behavior_id": self.from_behavior_id,
            "to_behavior_id": self.to_behavior_id,
            "transition_type": self.transition_type,
            "condition": self.condition,
            "probability": self.probability,
            "priority": self.priority,
            "timer": self.timer,
            "trigger_event": self.trigger_event,
        }


# ---------------------------------------------------------------------------
# Singleton Orchestrator
# ---------------------------------------------------------------------------


class EngineBehaviorOrchestrator:
    """
    Behavior tree orchestration engine.

    Creates, manages, and ticks behavior trees for game agents.
    Supports tree editing, transitions, optimization, and graph export.
    """

    _instance: Optional["EngineBehaviorOrchestrator"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineBehaviorOrchestrator":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._trees: Dict[str, BehaviorTree] = {}
        self._nodes: Dict[str, BehaviorNode] = {}
        self._transitions: Dict[str, BehaviorTransition] = {}
        self._contexts: Dict[str, BehaviorContext] = {}
        self._agent_tree_index: Dict[str, str] = {}
        self._tree_nodes_index: Dict[str, List[str]] = {}
        self._node_transitions_index: Dict[str, List[str]] = {}

        self._total_trees_created: int = 0
        self._total_nodes_created: int = 0
        self._total_transitions_created: int = 0
        self._total_ticks: int = 0
        self._total_optimizations: int = 0

    @classmethod
    def get_instance(cls) -> "EngineBehaviorOrchestrator":
        return cls()

    # ------------------------------------------------------------------
    # Tree Management
    # ------------------------------------------------------------------

    def create_behavior_tree(
        self,
        name: str,
        description: str = "",
        agent_id: str = "",
        tick_rate: float = 0.1,
    ) -> BehaviorTree:
        tree = BehaviorTree(
            name=name,
            description=description,
            agent_id=agent_id,
            tick_rate=tick_rate,
        )
        self._trees[tree.id] = tree
        self._agent_tree_index[agent_id] = tree.id
        self._tree_nodes_index[tree.id] = []
        self._total_trees_created += 1
        return tree

    def create_behavior_node(
        self,
        tree_id: str,
        node_type: str,
        name: str,
        description: str = "",
        parent_id: str = "",
        condition: str = "",
        action: str = "",
        params: Optional[Dict[str, Any]] = None,
        priority: int = 0,
        cooldown: float = 0.0,
        timeout: float = 0.0,
        interruptible: bool = True,
    ) -> Optional[BehaviorNode]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return None

        node = BehaviorNode(
            node_type=node_type,
            name=name,
            description=description,
            parent_id=parent_id,
            condition=condition,
            action=action,
            params=params or {},
            priority=priority,
            cooldown=cooldown,
            timeout=timeout,
            interruptible=interruptible,
        )
        self._nodes[node.id] = node
        self._tree_nodes_index.setdefault(tree_id, []).append(node.id)

        if parent_id and parent_id in self._nodes:
            parent = self._nodes[parent_id]
            parent.children_ids.append(node.id)

        if not tree.root_node_id:
            tree.root_node_id = node.id

        tree.total_nodes = len(self._tree_nodes_index[tree_id])
        tree.updated_at = _time_module.time()
        self._total_nodes_created += 1
        return node

    def connect_nodes(self, parent_id: str, child_id: str, index: int = -1) -> bool:
        parent = self._nodes.get(parent_id)
        child = self._nodes.get(child_id)
        if parent is None or child is None:
            return False
        if child.parent_id and child.parent_id != parent_id:
            old_parent = self._nodes.get(child.parent_id)
            if old_parent and child_id in old_parent.children_ids:
                old_parent.children_ids.remove(child_id)
        child.parent_id = parent_id
        if 0 <= index < len(parent.children_ids):
            parent.children_ids.insert(index, child_id)
        else:
            parent.children_ids.append(child_id)
        return True

    def disconnect_node(self, node_id: str) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        if node.parent_id:
            parent = self._nodes.get(node.parent_id)
            if parent and node_id in parent.children_ids:
                parent.children_ids.remove(node_id)
        node.parent_id = ""
        # Detach children as well
        for child_id in list(node.children_ids):
            child = self._nodes.get(child_id)
            if child:
                child.parent_id = ""
        node.children_ids.clear()
        return True

    # ------------------------------------------------------------------
    # Transitions
    # ------------------------------------------------------------------

    def add_transition(
        self,
        from_behavior_id: str,
        to_behavior_id: str,
        transition_type: str = TransitionType.IMMEDIATE.value,
        condition: str = "",
        probability: float = 1.0,
        priority: int = 0,
    ) -> Optional[BehaviorTransition]:
        if from_behavior_id not in self._nodes or to_behavior_id not in self._nodes:
            return None

        transition = BehaviorTransition(
            from_behavior_id=from_behavior_id,
            to_behavior_id=to_behavior_id,
            transition_type=transition_type,
            condition=condition,
            probability=max(0.0, min(1.0, probability)),
            priority=priority,
        )
        self._transitions[transition.id] = transition
        self._node_transitions_index.setdefault(from_behavior_id, []).append(transition.id)
        self._total_transitions_created += 1
        return transition

    # ------------------------------------------------------------------
    # Node Configuration
    # ------------------------------------------------------------------

    def set_node_action(self, node_id: str, action_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.action = action_name
        if params is not None:
            node.params = dict(params)
        return True

    def set_node_condition(self, node_id: str, condition_name: str, params: Optional[Dict[str, Any]] = None) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.condition = condition_name
        if params is not None:
            node.params = dict(params)
        return True

    def add_decorator(self, node_id: str, decorator_type: str, params: Optional[Dict[str, Any]] = None) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.decorator_type = decorator_type
        node.decorator_params = params or {}
        return True

    def set_priority(self, node_id: str, priority: int) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False
        node.priority = priority
        return True

    # ------------------------------------------------------------------
    # Runtime Tick
    # ------------------------------------------------------------------

    def tick_tree(self, tree_id: str, context: Optional[BehaviorContext] = None) -> BehaviorResult:
        tree = self._trees.get(tree_id)
        if tree is None:
            return BehaviorResult.FAILURE
        if not tree.root_node_id or tree.root_node_id not in self._nodes:
            return BehaviorResult.FAILURE

        if context is None:
            context = BehaviorContext(agent_id=tree.agent_id)

        root = self._nodes[tree.root_node_id]
        now = _time_module.time()

        if now - tree.last_tick_time < tree.tick_rate and tree.last_tick_time > 0:
            return BehaviorResult.RUNNING

        tree.last_tick_time = now
        tree.total_ticks += 1
        tree.updated_at = now
        self._total_ticks += 1

        result = self._tick_node(root, context, tree)

        successes = sum(
            1 for nid in self._tree_nodes_index.get(tree_id, [])
            if self._nodes.get(nid) and self._nodes[nid].last_result == BehaviorResult.SUCCESS.value
        )
        total = max(1, len(self._tree_nodes_index.get(tree_id, [])))
        tree.success_rate = successes / total

        return result

    def _tick_node(
        self,
        node: BehaviorNode,
        context: BehaviorContext,
        tree: BehaviorTree,
    ) -> BehaviorResult:
        node_type = node.node_type

        handler_map = {
            NodeType.SEQUENCE.value: self._tick_sequence,
            NodeType.SELECTOR.value: self._tick_selector,
            NodeType.PARALLEL.value: self._tick_parallel,
            NodeType.CONDITION.value: self._tick_condition,
            NodeType.ACTION.value: self._tick_action,
            NodeType.INVERTER.value: self._tick_inverter,
            NodeType.REPEATER.value: self._tick_repeater,
            NodeType.SUCCEEDER.value: self._tick_succeeder,
            NodeType.FAILER.value: self._tick_failer,
            NodeType.RANDOM_SELECTOR.value: self._tick_random_selector,
            NodeType.PRIORITY_SELECTOR.value: self._tick_priority_selector,
            NodeType.UTILITY_SELECTOR.value: self._tick_utility_selector,
            NodeType.STATE_CHECK.value: self._tick_state_check,
            NodeType.SUB_TREE.value: self._tick_sub_tree,
            NodeType.SERVICE.value: self._tick_service,
            NodeType.DECORATOR.value: self._tick_decorator,
        }

        handler = handler_map.get(node_type, self._tick_action)
        result = handler(node, context, tree)
        self._record_result(node, result)
        return result

    def _tick_sequence(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child is None:
                continue
            child_result = self._tick_node(child, context, tree)
            if child_result != BehaviorResult.SUCCESS:
                return child_result
        return BehaviorResult.SUCCESS

    def _tick_selector(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child is None:
                continue
            child_result = self._tick_node(child, context, tree)
            if child_result != BehaviorResult.FAILURE:
                return child_result
        return BehaviorResult.FAILURE

    def _tick_parallel(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        results = self.parallel_execute(node.id, context, len(node.children_ids))
        all_success = all(r == BehaviorResult.SUCCESS for r in results)
        any_failure = any(r == BehaviorResult.FAILURE for r in results)
        if all_success:
            return BehaviorResult.SUCCESS
        if any_failure:
            return BehaviorResult.FAILURE
        return BehaviorResult.RUNNING

    def _tick_condition(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        passed = self.evaluate_condition(node.id, context)
        return BehaviorResult.SUCCESS if passed else BehaviorResult.FAILURE

    def _tick_action(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        return self.execute_action(node.id, context)

    def _tick_inverter(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if not node.children_ids:
            return BehaviorResult.FAILURE
        child = self._nodes.get(node.children_ids[0])
        if child is None:
            return BehaviorResult.FAILURE
        child_result = self._tick_node(child, context, tree)
        if child_result == BehaviorResult.SUCCESS:
            return BehaviorResult.FAILURE
        if child_result == BehaviorResult.FAILURE:
            return BehaviorResult.SUCCESS
        return BehaviorResult.RUNNING

    def _tick_repeater(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if not node.children_ids:
            return BehaviorResult.FAILURE
        repeat_count = node.params.get("repeat_count", 1)
        child = self._nodes.get(node.children_ids[0])
        if child is None:
            return BehaviorResult.FAILURE
        for _ in range(repeat_count):
            result = self._tick_node(child, context, tree)
            if result == BehaviorResult.FAILURE:
                return BehaviorResult.FAILURE
        return BehaviorResult.SUCCESS

    def _tick_succeeder(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if node.children_ids:
            child = self._nodes.get(node.children_ids[0])
            if child:
                self._tick_node(child, context, tree)
        return BehaviorResult.SUCCESS

    def _tick_failer(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if node.children_ids:
            child = self._nodes.get(node.children_ids[0])
            if child:
                self._tick_node(child, context, tree)
        return BehaviorResult.FAILURE

    def _tick_random_selector(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if not node.children_ids:
            return BehaviorResult.FAILURE
        shuffled = list(node.children_ids)
        random.shuffle(shuffled)
        for child_id in shuffled:
            child = self._nodes.get(child_id)
            if child is None:
                continue
            result = self._tick_node(child, context, tree)
            if result != BehaviorResult.FAILURE:
                return result
        return BehaviorResult.FAILURE

    def _tick_priority_selector(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        sorted_children = sorted(
            node.children_ids,
            key=lambda cid: self._nodes[cid].priority if cid in self._nodes else 0,
            reverse=True,
        )
        for child_id in sorted_children:
            child = self._nodes.get(child_id)
            if child is None:
                continue
            result = self._tick_node(child, context, tree)
            if result != BehaviorResult.FAILURE:
                return result
        return BehaviorResult.FAILURE

    def _tick_utility_selector(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        if not node.children_ids:
            return BehaviorResult.FAILURE
        options = [self._nodes[cid].name for cid in node.children_ids if cid in self._nodes]
        selected = self.select_utility_option(node.id, context, options)
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child and child.name == selected:
                return self._tick_node(child, context, tree)
        return BehaviorResult.FAILURE

    def _tick_state_check(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        blackboard_key = node.params.get("blackboard_key", "")
        expected_value = node.params.get("expected_value")
        if blackboard_key and blackboard_key in context.blackboard:
            actual = context.blackboard[blackboard_key]
            if expected_value is not None and actual == expected_value:
                return BehaviorResult.SUCCESS
            return BehaviorResult.FAILURE
        returned = BehaviorResult.SUCCESS if node.condition else BehaviorResult.FAILURE
        return returned

    def _tick_sub_tree(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        sub_tree_id = node.params.get("sub_tree_id", "")
        if sub_tree_id and sub_tree_id in self._trees:
            return self.tick_tree(sub_tree_id, context)
        return BehaviorResult.FAILURE

    def _tick_service(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        self.execute_action(node.id, context)
        for child_id in node.children_ids:
            child = self._nodes.get(child_id)
            if child is None:
                continue
            return self._tick_node(child, context, tree)
        return BehaviorResult.SUCCESS

    def _tick_decorator(self, node: BehaviorNode, context: BehaviorContext, tree: BehaviorTree) -> BehaviorResult:
        decorator_type = node.decorator_type
        if decorator_type == "inverter":
            return self._tick_inverter(node, context, tree)
        if decorator_type == "repeater":
            return self._tick_repeater(node, context, tree)
        if decorator_type == "succeeder":
            return self._tick_succeeder(node, context, tree)
        if decorator_type == "failer":
            return self._tick_failer(node, context, tree)
        if decorator_type == "cooldown":
            now = _time_module.time()
            cooldown_secs = node.cooldown
            if now - node.last_execution_time < cooldown_secs and node.last_execution_time > 0:
                return BehaviorResult.FAILURE
        if decorator_type == "timeout":
            start_time = node.decorator_params.get("_start_time", _time_module.time())
            timeout_secs = node.timeout
            if _time_module.time() - start_time > timeout_secs:
                return BehaviorResult.FAILURE
        # Fall through to child
        if node.children_ids:
            child = self._nodes.get(node.children_ids[0])
            if child:
                return self._tick_node(child, context, tree)
        return BehaviorResult.SUCCESS

    def _record_result(self, node: BehaviorNode, result: BehaviorResult) -> None:
        node.last_result = result.value
        node.last_execution_time = _time_module.time()
        if result == BehaviorResult.SUCCESS:
            node.success_count += 1
        elif result == BehaviorResult.FAILURE:
            node.failure_count += 1
        node.execution_history.append({
            "timestamp": node.last_execution_time,
            "result": result.value,
        })
        if len(node.execution_history) > 100:
            node.execution_history = node.execution_history[-100:]

    # ------------------------------------------------------------------
    # Condition / Action Evaluation
    # ------------------------------------------------------------------

    def evaluate_condition(self, node_id: str, context: BehaviorContext) -> bool:
        node = self._nodes.get(node_id)
        if node is None:
            return False

        condition_name = node.condition
        if not condition_name:
            return False

        return self._resolve_condition(condition_name, node.params, context)

    def _resolve_condition(self, condition_name: str, params: Dict[str, Any], context: BehaviorContext) -> bool:
        # Resolve conditions from context data
        if condition_name == "has_enemy_in_range":
            range_val = params.get("range", 100.0)
            enemies = context.sensor_data.get("enemies", [])
            return any(e.get("distance", float("inf")) < range_val for e in enemies)

        if condition_name == "has_goal":
            goal_name = params.get("goal_name", "")
            return goal_name in context.goal_stack

        if condition_name == "blackboard_check":
            key = params.get("key", "")
            expected = params.get("expected_value")
            return context.blackboard.get(key) == expected

        if condition_name == "personality_threshold":
            trait = params.get("trait", "")
            threshold = params.get("threshold", 0.5)
            value = context.personality_vector.get(trait, 0.0)
            return value >= threshold

        if condition_name == "emotional_state_check":
            emotion = params.get("emotion", "")
            threshold = params.get("threshold", 0.5)
            value = context.emotional_state.get(emotion, 0.0)
            return value >= threshold

        if condition_name == "timer_expired":
            timer_key = params.get("timer_key", "")
            timer_value = context.blackboard.get(timer_key, float("inf"))
            return _time_module.time() >= timer_value

        if condition_name == "probability_check":
            prob = params.get("probability", 0.5)
            return random.random() < prob

        if condition_name == "always_true":
            return True

        if condition_name == "always_false":
            return False

        return True

    def execute_action(self, node_id: str, context: BehaviorContext) -> BehaviorResult:
        node = self._nodes.get(node_id)
        if node is None:
            return BehaviorResult.FAILURE

        action_name = node.action
        if not action_name:
            return BehaviorResult.SUCCESS

        return self._resolve_action(action_name, node.params, context)

    def _resolve_action(self, action_name: str, params: Dict[str, Any], context: BehaviorContext) -> BehaviorResult:
        if action_name == "set_blackboard":
            key = params.get("key", "")
            value = params.get("value")
            if key:
                context.blackboard[key] = value
            return BehaviorResult.SUCCESS

        if action_name == "push_goal":
            goal = params.get("goal", "")
            if goal:
                context.goal_stack.append(goal)
            return BehaviorResult.SUCCESS

        if action_name == "pop_goal":
            if context.goal_stack:
                context.goal_stack.pop()
            return BehaviorResult.SUCCESS

        if action_name == "set_timer":
            timer_key = params.get("timer_key", "")
            duration = params.get("duration", 0.0)
            if timer_key:
                context.blackboard[timer_key] = _time_module.time() + duration
            return BehaviorResult.SUCCESS

        if action_name == "emit_signal":
            signal_name = params.get("signal_name", "")
            context.blackboard.setdefault("_signals", []).append(signal_name)
            return BehaviorResult.SUCCESS

        if action_name == "wait":
            return BehaviorResult.RUNNING

        if action_name == "fail":
            return BehaviorResult.FAILURE

        if action_name == "succeed":
            return BehaviorResult.SUCCESS

        # Default: succeed for unrecognized actions
        return BehaviorResult.SUCCESS

    def select_utility_option(self, node_id: str, context: BehaviorContext, options: List[str]) -> str:
        node = self._nodes.get(node_id)
        if not options:
            return ""

        utility_scores: Dict[str, float] = {}
        for option in options:
            score = self._compute_utility(option, node.params if node else {}, context)
            utility_scores[option] = score

        return max(utility_scores, key=lambda k: utility_scores[k])

    def _compute_utility(self, option: str, params: Dict[str, Any], context: BehaviorContext) -> float:
        base_score = 0.5
        # Weight by personality
        for trait, weight in context.personality_vector.items():
            if trait.lower() in option.lower():
                base_score += weight * 0.2
        # Weight by goals
        for goal in context.goal_stack:
            if goal.lower() in option.lower():
                base_score += 0.3
        # Add noise for exploration
        base_score += random.random() * 0.1
        return base_score

    def parallel_execute(self, node_id: str, context: BehaviorContext, child_count: int) -> List[BehaviorResult]:
        node = self._nodes.get(node_id)
        if node is None:
            return [BehaviorResult.FAILURE]

        results: List[BehaviorResult] = []
        for i in range(min(child_count, len(node.children_ids))):
            child_id = node.children_ids[i]
            child = self._nodes.get(child_id)
            if child is None:
                results.append(BehaviorResult.FAILURE)
                continue
            results.append(self.execute_action(child.id, context))
        return results

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_active_trees(self) -> List[str]:
        return [tid for tid, tree in self._trees.items() if tree.is_active]

    def get_node_stats(self, node_id: str) -> Dict[str, Any]:
        node = self._nodes.get(node_id)
        if node is None:
            return {}
        total_executions = node.success_count + node.failure_count
        running_count = sum(
            1 for h in node.execution_history
            if h.get("result") == BehaviorResult.RUNNING.value
        )
        avg_exec = 0.0
        if total_executions > 0:
            history_times = [
                h["timestamp"] for h in node.execution_history
            ]
            if len(history_times) >= 2:
                avg_exec = (history_times[-1] - history_times[0]) / max(1, len(history_times) - 1)

        return {
            "success_count": node.success_count,
            "failure_count": node.failure_count,
            "running_count": running_count,
            "avg_execution_time": round(avg_exec, 4),
            "error_rate": round(node.failure_count / max(1, total_executions), 4),
        }

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def optimize_tree(self, tree_id: str) -> Dict[str, Any]:
        tree = self._trees.get(tree_id)
        if tree is None:
            return {"error": f"Tree '{tree_id}' not found"}

        node_ids = self._tree_nodes_index.get(tree_id, [])
        nodes_removed = 0
        nodes_restructured = 0

        # Remove orphaned nodes (nodes not reachable from root)
        reachable = self._collect_reachable(tree.root_node_id)
        for nid in list(node_ids):
            if nid not in reachable:
                self._nodes.pop(nid, None)
                node_ids.remove(nid)
                nodes_removed += 1

        # Restructure: promote single-child sequences/selectors
        for nid in list(node_ids):
            node = self._nodes.get(nid)
            if node is None:
                continue
            nt = node.node_type
            if nt in (NodeType.SEQUENCE.value, NodeType.SELECTOR.value) and len(node.children_ids) == 1:
                child_id = node.children_ids[0]
                if node.parent_id and node.parent_id in self._nodes:
                    parent = self._nodes[node.parent_id]
                    idx = next((i for i, c in enumerate(parent.children_ids) if c == nid), -1)
                    if idx >= 0:
                        parent.children_ids[idx] = child_id
                        self._nodes[child_id].parent_id = node.parent_id
                    if tree.root_node_id == nid:
                        tree.root_node_id = child_id
                    nodes_restructured += 1

        # Remove empty leaf nodes
        for nid in list(node_ids):
            node = self._nodes.get(nid)
            if node is None:
                continue
            nt = node.node_type
            if nt in (NodeType.SEQUENCE.value, NodeType.SELECTOR.value) and not node.children_ids:
                if nid in node_ids:
                    node_ids.remove(nid)
                    self._nodes.pop(nid, None)
                    nodes_removed += 1

        tree.total_nodes = len(node_ids)
        tree.updated_at = _time_module.time()
        self._total_optimizations += 1

        performance_gain = round(
            (nodes_removed * 0.05 + nodes_restructured * 0.03) * 100, 1
        )

        return {
            "nodes_removed": nodes_removed,
            "nodes_restructured": nodes_restructured,
            "performance_gain": performance_gain,
        }

    def _collect_reachable(self, root_id: str) -> set:
        reachable: set = set()
        if root_id not in self._nodes:
            return reachable
        stack = [root_id]
        while stack:
            nid = stack.pop()
            if nid in reachable:
                continue
            reachable.add(nid)
            node = self._nodes.get(nid)
            if node:
                stack.extend(node.children_ids)
        return reachable

    # ------------------------------------------------------------------
    # Graph Export / Import
    # ------------------------------------------------------------------

    def export_to_graph(self, tree_id: str, fmt: str = "json") -> str:
        tree = self._trees.get(tree_id)
        if tree is None:
            return "{}"

        if fmt == "dot":
            return self._export_dot(tree_id)
        return self._export_json(tree_id)

    def _export_json(self, tree_id: str) -> str:
        tree = self._trees.get(tree_id)
        if tree is None:
            return "{}"
        node_ids = self._tree_nodes_index.get(tree_id, [])
        graph = {
            "tree": tree.to_dict(),
            "nodes": [self._nodes[nid].to_dict() for nid in node_ids if nid in self._nodes],
        }
        return json.dumps(graph, indent=2)

    def _export_dot(self, tree_id: str) -> str:
        tree = self._trees.get(tree_id)
        if tree is None:
            return "digraph {}"
        node_ids = self._tree_nodes_index.get(tree_id, [])
        lines = [f'digraph "{tree.name}" {{']
        lines.append(f'  label="{tree.name}";')
        lines.append('  node [shape=box, style=filled, fillcolor=lightyellow];')
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node is None:
                continue
            label = f"{node.name}\\n[{node.node_type}]"
            lines.append(f'  "{nid}" [label="{label}"];')
        for nid in node_ids:
            node = self._nodes.get(nid)
            if node is None:
                continue
            for child_id in node.children_ids:
                lines.append(f'  "{nid}" -> "{child_id}";')
        lines.append("}")
        return "\n".join(lines)

    def import_from_graph(self, graph_data: str, fmt: str = "json") -> str:
        if fmt == "dot":
            return self._import_dot(graph_data)
        return self._import_json(graph_data)

    def _import_json(self, graph_data: str) -> str:
        try:
            data = json.loads(graph_data)
        except (json.JSONDecodeError, TypeError):
            return ""

        tree_data = data.get("tree", {})
        nodes_data = data.get("nodes", [])

        tree = BehaviorTree(
            name=tree_data.get("name", "Imported Tree"),
            description=tree_data.get("description", ""),
            agent_id=tree_data.get("agent_id", ""),
            tick_rate=tree_data.get("tick_rate", 0.1),
        )
        self._trees[tree.id] = tree
        self._tree_nodes_index[tree.id] = []

        old_to_new: Dict[str, str] = {}
        for node_data in nodes_data:
            old_id = node_data.get("id", "")
            node = BehaviorNode(
                node_type=node_data.get("node_type", NodeType.ACTION.value),
                name=node_data.get("name", ""),
                description=node_data.get("description", ""),
                condition=node_data.get("condition", ""),
                action=node_data.get("action", ""),
                params=node_data.get("params", {}),
                priority=node_data.get("priority", 0),
                cooldown=node_data.get("cooldown", 0.0),
                timeout=node_data.get("timeout", 0.0),
                interruptible=node_data.get("interruptible", True),
                tags=node_data.get("tags", []),
            )
            self._nodes[node.id] = node
            self._tree_nodes_index[tree.id].append(node.id)
            old_to_new[old_id] = node.id

        # Rebuild parent/child relationships
        for node_data in nodes_data:
            old_id = node_data.get("id", "")
            new_parent = old_to_new.get(node_data.get("parent_id", ""), "")
            new_node_id = old_to_new.get(old_id)
            if new_node_id:
                node = self._nodes[new_node_id]
                node.parent_id = new_parent
                for old_child in node_data.get("children_ids", []):
                    new_child = old_to_new.get(old_child)
                    if new_child:
                        node.children_ids.append(new_child)

        root_id = tree_data.get("root_node_id", "")
        tree.root_node_id = old_to_new.get(root_id, "")
        tree.total_nodes = len(self._tree_nodes_index[tree.id])
        self._total_trees_created += 1
        return tree.id

    def _import_dot(self, graph_data: str) -> str:
        tree = BehaviorTree(name="Imported DOT Tree")
        self._trees[tree.id] = tree
        self._tree_nodes_index[tree.id] = []

        dot_to_id: Dict[str, str] = {}
        for line in graph_data.splitlines():
            line = line.strip()
            if "->" in line:
                parts = line.split("->")
                from_part = parts[0].strip().strip('"')
                to_part = parts[1].strip().rstrip(";").strip('"')

                if from_part not in dot_to_id:
                    node = BehaviorNode(name=from_part)
                    self._nodes[node.id] = node
                    self._tree_nodes_index[tree.id].append(node.id)
                    dot_to_id[from_part] = node.id
                if to_part not in dot_to_id:
                    node = BehaviorNode(name=to_part)
                    self._nodes[node.id] = node
                    self._tree_nodes_index[tree.id].append(node.id)
                    dot_to_id[to_part] = node.id

                parent = self._nodes[dot_to_id[from_part]]
                child_id = dot_to_id[to_part]
                if child_id not in parent.children_ids:
                    parent.children_ids.append(child_id)
                    self._nodes[child_id].parent_id = parent.id

        if dot_to_id:
            # Set root as first node without a parent
            for dot_name, nid in dot_to_id.items():
                node = self._nodes.get(nid)
                if node and not node.parent_id:
                    tree.root_node_id = nid
                    break

        tree.total_nodes = len(self._tree_nodes_index[tree.id])
        self._total_trees_created += 1
        return tree.id

    # ------------------------------------------------------------------
    # Tree Operations
    # ------------------------------------------------------------------

    def clone_tree(self, tree_id: str, new_name: str) -> str:
        tree = self._trees.get(tree_id)
        if tree is None:
            return ""

        new_tree = BehaviorTree(
            name=new_name,
            description=f"Clone of '{tree.name}'",
            agent_id=tree.agent_id,
            tick_rate=tree.tick_rate,
        )
        self._trees[new_tree.id] = new_tree
        self._tree_nodes_index[new_tree.id] = []

        old_to_new: Dict[str, str] = {}
        node_ids = self._tree_nodes_index.get(tree_id, [])
        for nid in node_ids:
            original = self._nodes.get(nid)
            if original is None:
                continue
            cloned = BehaviorNode(
                node_type=original.node_type,
                name=original.name,
                description=original.description,
                condition=original.condition,
                action=original.action,
                params=dict(original.params),
                priority=original.priority,
                cooldown=original.cooldown,
                timeout=original.timeout,
                interruptible=original.interruptible,
                tags=list(original.tags),
            )
            self._nodes[cloned.id] = cloned
            self._tree_nodes_index[new_tree.id].append(cloned.id)
            old_to_new[nid] = cloned.id

        # Rebuild parent/child relationships
        for nid in node_ids:
            original = self._nodes.get(nid)
            if original is None:
                continue
            cloned_id = old_to_new.get(nid)
            if cloned_id:
                cloned = self._nodes[cloned_id]
                cloned.parent_id = old_to_new.get(original.parent_id, "")
                for oc in original.children_ids:
                    nc = old_to_new.get(oc)
                    if nc:
                        cloned.children_ids.append(nc)

        new_tree.root_node_id = old_to_new.get(tree.root_node_id, "")
        new_tree.total_nodes = len(self._tree_nodes_index[new_tree.id])
        self._total_trees_created += 1
        return new_tree.id

    # ------------------------------------------------------------------
    # Statistics & Reset
    # ------------------------------------------------------------------

    def get_orchestration_stats(self) -> Dict[str, Any]:
        total_nodes = len(self._nodes)
        active_trees = len(self.get_active_trees())
        total_trees = len(self._trees)

        all_tick_rates = [t.tick_rate for t in self._trees.values()]
        avg_tick_rate = round(
            sum(all_tick_rates) / max(1, len(all_tick_rates)), 4
        )

        all_success_rates = [t.success_rate for t in self._trees.values()]
        overall_success_rate = round(
            sum(all_success_rates) / max(1, len(all_success_rates)), 4
        )

        avg_tree_depth = 0.0
        if self._trees:
            depths = []
            for tree in self._trees.values():
                depth = self._compute_tree_depth(tree.root_node_id)
                depths.append(depth)
            avg_tree_depth = round(sum(depths) / len(depths), 1)

        return {
            "tree_count": total_trees,
            "active_trees": active_trees,
            "total_nodes": total_nodes,
            "avg_tick_rate": avg_tick_rate,
            "total_ticks": self._total_ticks,
            "success_rate": overall_success_rate,
            "optimization_count": self._total_optimizations,
            "avg_tree_depth": avg_tree_depth,
        }

    def _compute_tree_depth(self, root_id: str) -> int:
        if root_id not in self._nodes:
            return 0
        max_depth = 0
        stack: List[tuple] = [(root_id, 1)]
        while stack:
            nid, depth = stack.pop()
            max_depth = max(max_depth, depth)
            node = self._nodes.get(nid)
            if node:
                for cid in node.children_ids:
                    stack.append((cid, depth + 1))
        return max_depth

    def reset(self) -> None:
        self._trees.clear()
        self._nodes.clear()
        self._transitions.clear()
        self._contexts.clear()
        self._agent_tree_index.clear()
        self._tree_nodes_index.clear()
        self._node_transitions_index.clear()
        self._total_trees_created = 0
        self._total_nodes_created = 0
        self._total_transitions_created = 0
        self._total_ticks = 0
        self._total_optimizations = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_uid_stub() -> str:
        return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_behavior_orchestrator() -> EngineBehaviorOrchestrator:
    return EngineBehaviorOrchestrator.get_instance()