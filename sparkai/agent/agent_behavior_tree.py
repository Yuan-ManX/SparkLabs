"""
Agent Behavior Tree - Hierarchical behavior tree system for AI-driven game agents.
Provides composable behavior nodes, conditional branching, and parallel execution
for sophisticated NPC and game character AI.
"""

import threading
import uuid
import time as _time_module
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Callable


class BTNodeStatus(Enum):
    """Status returned by behavior tree nodes."""
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"
    IDLE = "idle"


class BTNodeType(Enum):
    """Types of behavior tree nodes."""
    SEQUENCE = "sequence"
    SELECTOR = "selector"
    PARALLEL = "parallel"
    CONDITION = "condition"
    ACTION = "action"
    DECORATOR = "decorator"
    INVERTER = "inverter"
    REPEATER = "repeater"
    RANDOM = "random"
    SUBTREE = "subtree"


@dataclass
class BTNode:
    """Base node for behavior tree."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: BTNodeType = BTNodeType.ACTION
    name: str = ""
    children: List['BTNode'] = field(default_factory=list)
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    action: Optional[Callable[[Dict[str, Any]], BTNodeStatus]] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    status: BTNodeStatus = BTNodeStatus.IDLE
    last_run: float = 0.0
    run_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "children": [c.to_dict() for c in self.children],
            "properties": self.properties,
            "status": self.status.value,
            "run_count": self.run_count,
        }


@dataclass
class BehaviorTree:
    """Complete behavior tree for an agent."""
    tree_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    agent_id: str = ""
    root: Optional[BTNode] = None
    blackboard: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    priority: int = 0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tree_id": self.tree_id,
            "name": self.name,
            "agent_id": self.agent_id,
            "root": self.root.to_dict() if self.root else None,
            "is_active": self.is_active,
            "priority": self.priority,
        }


class AgentBehaviorTree:
    """
    Behavior tree system for composing AI agent behaviors.
    Supports hierarchical behavior trees with sequences, selectors,
    parallel nodes, conditions, actions, and decorators.
    """

    _instance = None
    _lock = threading.RLock()
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._trees: Dict[str, BehaviorTree] = {}
            self._node_library: Dict[str, Callable] = {}
            self._tree_history: Dict[str, List[Dict[str, Any]]] = {}
            self._initialized = True

    @classmethod
    def get_instance(cls) -> 'AgentBehaviorTree':
        return cls()

    def create_tree(self, name: str, agent_id: str = "", priority: int = 0) -> BehaviorTree:
        """Create a new behavior tree."""
        tree = BehaviorTree(name=name, agent_id=agent_id, priority=priority)
        self._trees[tree.tree_id] = tree
        return tree

    def create_node(self, node_type: BTNodeType, name: str = "",
                    condition: Optional[Callable] = None,
                    action: Optional[Callable] = None,
                    properties: Optional[Dict[str, Any]] = None) -> BTNode:
        """Create a behavior tree node."""
        return BTNode(
            node_type=node_type,
            name=name,
            condition=condition,
            action=action,
            properties=properties or {},
        )

    def create_sequence(self, name: str, children: List[BTNode] = None) -> BTNode:
        """Create a sequence node (runs children in order until one fails)."""
        node = self.create_node(BTNodeType.SEQUENCE, name)
        if children:
            node.children = children
        return node

    def create_selector(self, name: str, children: List[BTNode] = None) -> BTNode:
        """Create a selector node (runs children until one succeeds)."""
        node = self.create_node(BTNodeType.SELECTOR, name)
        if children:
            node.children = children
        return node

    def create_parallel(self, name: str, children: List[BTNode] = None,
                        required_successes: int = 1) -> BTNode:
        """Create a parallel node (runs all children simultaneously)."""
        node = self.create_node(BTNodeType.PARALLEL, name)
        node.properties["required_successes"] = required_successes
        if children:
            node.children = children
        return node

    def create_condition(self, name: str, condition: Callable[[Dict[str, Any]], bool]) -> BTNode:
        """Create a condition node."""
        node = self.create_node(BTNodeType.CONDITION, name)
        node.condition = condition
        return node

    def create_action(self, name: str, action: Callable[[Dict[str, Any]], BTNodeStatus]) -> BTNode:
        """Create an action node."""
        node = self.create_node(BTNodeType.ACTION, name)
        node.action = action
        return node

    def create_inverter(self, name: str, child: BTNode) -> BTNode:
        """Create an inverter decorator (inverts child result)."""
        node = self.create_node(BTNodeType.INVERTER, name)
        node.children = [child]
        return node

    def create_repeater(self, name: str, child: BTNode, count: int = -1) -> BTNode:
        """Create a repeater decorator (repeats child n times)."""
        node = self.create_node(BTNodeType.REPEATER, name)
        node.children = [child]
        node.properties["repeat_count"] = count
        node.properties["current_count"] = 0
        return node

    def set_tree_root(self, tree_id: str, root: BTNode):
        """Set the root node of a behavior tree."""
        tree = self._trees.get(tree_id)
        if tree:
            tree.root = root

    def tick(self, tree_id: str, blackboard: Optional[Dict[str, Any]] = None) -> BTNodeStatus:
        """Execute one tick of the behavior tree."""
        tree = self._trees.get(tree_id)
        if not tree or not tree.root or not tree.is_active:
            return BTNodeStatus.FAILURE

        if blackboard:
            tree.blackboard.update(blackboard)

        status = self._tick_node(tree.root, tree.blackboard)
        self._record_history(tree_id, status)
        return status

    def _tick_node(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        """Execute a single node in the tree."""
        node.last_run = _time_module.time()
        node.run_count += 1

        if node.node_type == BTNodeType.SEQUENCE:
            return self._tick_sequence(node, blackboard)
        elif node.node_type == BTNodeType.SELECTOR:
            return self._tick_selector(node, blackboard)
        elif node.node_type == BTNodeType.PARALLEL:
            return self._tick_parallel(node, blackboard)
        elif node.node_type == BTNodeType.CONDITION:
            return self._tick_condition(node, blackboard)
        elif node.node_type == BTNodeType.ACTION:
            return self._tick_action(node, blackboard)
        elif node.node_type == BTNodeType.INVERTER:
            return self._tick_inverter(node, blackboard)
        elif node.node_type == BTNodeType.REPEATER:
            return self._tick_repeater(node, blackboard)

        return BTNodeStatus.FAILURE

    def _tick_sequence(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        for child in node.children:
            status = self._tick_node(child, blackboard)
            if status != BTNodeStatus.SUCCESS:
                node.status = status
                return status
        node.status = BTNodeStatus.SUCCESS
        return BTNodeStatus.SUCCESS

    def _tick_selector(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        for child in node.children:
            status = self._tick_node(child, blackboard)
            if status == BTNodeStatus.SUCCESS:
                node.status = BTNodeStatus.SUCCESS
                return BTNodeStatus.SUCCESS
            elif status == BTNodeStatus.RUNNING:
                node.status = BTNodeStatus.RUNNING
                return BTNodeStatus.RUNNING
        node.status = BTNodeStatus.FAILURE
        return BTNodeStatus.FAILURE

    def _tick_parallel(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        required = node.properties.get("required_successes", 1)
        successes = 0
        failures = 0
        running = False

        for child in node.children:
            status = self._tick_node(child, blackboard)
            if status == BTNodeStatus.SUCCESS:
                successes += 1
            elif status == BTNodeStatus.FAILURE:
                failures += 1
            elif status == BTNodeStatus.RUNNING:
                running = True

        if successes >= required:
            node.status = BTNodeStatus.SUCCESS
            return BTNodeStatus.SUCCESS
        if failures > len(node.children) - required:
            node.status = BTNodeStatus.FAILURE
            return BTNodeStatus.FAILURE
        if running:
            node.status = BTNodeStatus.RUNNING
            return BTNodeStatus.RUNNING

        node.status = BTNodeStatus.FAILURE
        return BTNodeStatus.FAILURE

    def _tick_condition(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        if node.condition:
            result = node.condition(blackboard)
            node.status = BTNodeStatus.SUCCESS if result else BTNodeStatus.FAILURE
            return node.status
        node.status = BTNodeStatus.FAILURE
        return BTNodeStatus.FAILURE

    def _tick_action(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        if node.action:
            node.status = node.action(blackboard)
            return node.status
        node.status = BTNodeStatus.FAILURE
        return BTNodeStatus.FAILURE

    def _tick_inverter(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        if not node.children:
            return BTNodeStatus.FAILURE
        child_status = self._tick_node(node.children[0], blackboard)
        if child_status == BTNodeStatus.SUCCESS:
            node.status = BTNodeStatus.FAILURE
            return BTNodeStatus.FAILURE
        elif child_status == BTNodeStatus.FAILURE:
            node.status = BTNodeStatus.SUCCESS
            return BTNodeStatus.SUCCESS
        node.status = child_status
        return child_status

    def _tick_repeater(self, node: BTNode, blackboard: Dict[str, Any]) -> BTNodeStatus:
        if not node.children:
            return BTNodeStatus.FAILURE
        max_count = node.properties.get("repeat_count", -1)
        current = node.properties.get("current_count", 0)

        child_status = self._tick_node(node.children[0], blackboard)
        if child_status != BTNodeStatus.RUNNING:
            current += 1
            node.properties["current_count"] = current

        if max_count > 0 and current >= max_count:
            node.status = BTNodeStatus.SUCCESS
            return BTNodeStatus.SUCCESS

        node.status = BTNodeStatus.RUNNING
        return BTNodeStatus.RUNNING

    def create_patrol_behavior(self, agent_id: str) -> BehaviorTree:
        """Create a standard patrol behavior tree."""
        tree = self.create_tree("Patrol", agent_id, priority=0)

        sequence = self.create_sequence("PatrolSequence", [
            self.create_condition("HasPath", lambda bb: bool(bb.get("has_path", False))),
            self.create_selector("MoveOrWait", [
                self.create_sequence("MoveToNext", [
                    self.create_action("Move", lambda bb: BTNodeStatus.SUCCESS),
                    self.create_action("LookAround", lambda bb: BTNodeStatus.SUCCESS),
                ]),
                self.create_action("IdleWait", lambda bb: BTNodeStatus.RUNNING),
            ]),
        ])

        tree.root = sequence
        return tree

    def create_combat_behavior(self, agent_id: str) -> BehaviorTree:
        """Create a standard combat behavior tree."""
        tree = self.create_tree("Combat", agent_id, priority=10)

        selector = self.create_selector("CombatBehavior", [
            self.create_sequence("AttackSequence", [
                self.create_condition("EnemyInRange", lambda bb: bool(bb.get("enemy_in_range", False))),
                self.create_selector("AttackOrFlee", [
                    self.create_sequence("HighHealthAttack", [
                        self.create_condition("HealthHigh", lambda bb: bb.get("health", 100) > 30),
                        self.create_action("AttackEnemy", lambda bb: BTNodeStatus.SUCCESS),
                    ]),
                    self.create_action("FleeCombat", lambda bb: BTNodeStatus.SUCCESS),
                ]),
            ]),
            self.create_sequence("ChaseEnemy", [
                self.create_condition("EnemyDetected", lambda bb: bool(bb.get("enemy_detected", False))),
                self.create_action("Chase", lambda bb: BTNodeStatus.RUNNING),
            ]),
            self.create_action("Idle", lambda bb: BTNodeStatus.SUCCESS),
        ])

        tree.root = selector
        return tree

    def _record_history(self, tree_id: str, status: BTNodeStatus):
        self._tree_history.setdefault(tree_id, []).append({
            "status": status.value,
            "timestamp": _time_module.time(),
        })
        history = self._tree_history[tree_id]
        if len(history) > 500:
            self._tree_history[tree_id] = history[-200:]

    def get_tree(self, tree_id: str) -> Optional[BehaviorTree]:
        """Get a behavior tree by ID."""
        return self._trees.get(tree_id)

    def list_trees(self, agent_id: str = "") -> List[BehaviorTree]:
        """List all behavior trees, optionally filtered by agent."""
        if agent_id:
            return [t for t in self._trees.values() if t.agent_id == agent_id]
        return list(self._trees.values())

    def deactivate_tree(self, tree_id: str):
        """Deactivate a behavior tree."""
        tree = self._trees.get(tree_id)
        if tree:
            tree.is_active = False

    def activate_tree(self, tree_id: str):
        """Activate a behavior tree."""
        tree = self._trees.get(tree_id)
        if tree:
            tree.is_active = True

    def get_stats(self) -> Dict[str, Any]:
        """Get behavior tree system statistics."""
        return {
            "total_trees": len(self._trees),
            "active_trees": sum(1 for t in self._trees.values() if t.is_active),
            "total_ticks": sum(len(h) for h in self._tree_history.values()),
            "trees_by_agent": {},
        }


def get_behavior_tree() -> AgentBehaviorTree:
    return AgentBehaviorTree.get_instance()