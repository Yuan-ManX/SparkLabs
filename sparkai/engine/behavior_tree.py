"""
SparkLabs Engine - Behavior Tree

Behavior tree AI system for NPC game characters. Enables
hierarchical, composable decision-making through tree-based
behavior definitions. AI agents use this to design and tune
enemy AI, NPC routines, and companion behaviors through
a modular node-based architecture.

Architecture:
  BehaviorTree
    |-- BehaviorNode (base: tick → SUCCESS/FAILURE/RUNNING)
    |-- Composite Nodes (Sequence, Selector, Parallel)
    |-- Decorator Nodes (Inverter, Repeater, Timeout, Cooldown)
    |-- Action Nodes (MoveTo, Attack, Patrol, Flee, UseItem)
    |-- Condition Nodes (IsNear, HasHealth, CanSee, IsDaytime)
    |-- Blackboard (shared key-value state between nodes)

Node Lifecycle:
  Each node has a tick() method returning:
  - SUCCESS: task completed successfully
  - FAILURE: task cannot be completed
  - RUNNING: task still in progress
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class NodeStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BehaviorNode:
    """Base class for all behavior tree nodes."""

    def __init__(self, name: str = ""):
        self.name: str = name or self.__class__.__name__
        self._parent: Optional["BehaviorNode"] = None

    def tick(self, blackboard: "Blackboard") -> NodeStatus:
        raise NotImplementedError

    def reset(self) -> None:
        pass


class Blackboard:
    """Shared key-value state store for behavior trees."""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._subscribers: Dict[str, List[Callable]] = {}

    def set(self, key: str, value: Any) -> None:
        old = self._data.get(key)
        self._data[key] = value
        if old != value and key in self._subscribers:
            for cb in self._subscribers[key]:
                try:
                    cb(key, old, value)
                except Exception:
                    pass

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._data

    def delete(self, key: str) -> None:
        self._data.pop(key, None)

    def watch(self, key: str, callback: Callable) -> None:
        self._subscribers.setdefault(key, []).append(callback)

    def to_dict(self) -> dict:
        return dict(self._data)

    def clear(self) -> None:
        self._data.clear()


class Sequence(BehaviorNode):
    """Executes children in order until one fails."""

    def __init__(self, children: List[BehaviorNode], name: str = ""):
        super().__init__(name)
        self.children = children
        for child in children:
            child._parent = self
        self._index: int = 0

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        while self._index < len(self.children):
            status = self.children[self._index].tick(blackboard)
            if status == NodeStatus.FAILURE:
                self._index = 0
                return NodeStatus.FAILURE
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            self._index += 1
        self._index = 0
        return NodeStatus.SUCCESS

    def reset(self) -> None:
        self._index = 0
        for child in self.children:
            child.reset()


class Selector(BehaviorNode):
    """Executes children in order until one succeeds."""

    def __init__(self, children: List[BehaviorNode], name: str = ""):
        super().__init__(name)
        self.children = children
        for child in children:
            child._parent = self
        self._index: int = 0

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        while self._index < len(self.children):
            status = self.children[self._index].tick(blackboard)
            if status == NodeStatus.SUCCESS:
                self._index = 0
                return NodeStatus.SUCCESS
            if status == NodeStatus.RUNNING:
                return NodeStatus.RUNNING
            self._index += 1
        self._index = 0
        return NodeStatus.FAILURE

    def reset(self) -> None:
        self._index = 0
        for child in self.children:
            child.reset()


class Parallel(BehaviorNode):
    """Executes all children concurrently."""

    def __init__(self, children: List[BehaviorNode], required_successes: int = -1, name: str = ""):
        super().__init__(name)
        self.children = children
        self.required_successes = required_successes if required_successes > 0 else len(children)
        for child in children:
            child._parent = self

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        successes = 0
        failures = 0
        for child in self.children:
            status = child.tick(blackboard)
            if status == NodeStatus.SUCCESS:
                successes += 1
            elif status == NodeStatus.FAILURE:
                failures += 1
        if successes >= self.required_successes:
            return NodeStatus.SUCCESS
        if failures > len(self.children) - self.required_successes:
            return NodeStatus.FAILURE
        return NodeStatus.RUNNING

    def reset(self) -> None:
        for child in self.children:
            child.reset()


class Inverter(BehaviorNode):
    """Inverts child node result (SUCCESS↔FAILURE)."""

    def __init__(self, child: BehaviorNode, name: str = ""):
        super().__init__(name)
        self.child = child
        child._parent = self

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            return NodeStatus.FAILURE
        if status == NodeStatus.FAILURE:
            return NodeStatus.SUCCESS
        return NodeStatus.RUNNING

    def reset(self) -> None:
        self.child.reset()


class Repeater(BehaviorNode):
    """Repeats child n times or forever (n=-1)."""

    def __init__(self, child: BehaviorNode, times: int = -1, name: str = ""):
        super().__init__(name)
        self.child = child
        self._times = times
        self._count = 0
        child._parent = self

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if self._times >= 0 and self._count >= self._times:
            self._count = 0
            return NodeStatus.SUCCESS
        status = self.child.tick(blackboard)
        if status == NodeStatus.SUCCESS:
            self._count += 1
            self.child.reset()
        elif status == NodeStatus.FAILURE:
            return NodeStatus.FAILURE
        return NodeStatus.RUNNING

    def reset(self) -> None:
        self._count = 0
        self.child.reset()


class Timeout(BehaviorNode):
    """Fails child after timeout seconds."""

    def __init__(self, child: BehaviorNode, seconds: float, name: str = ""):
        super().__init__(name)
        self.child = child
        self._timeout = seconds
        self._started: Optional[float] = None
        child._parent = self

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if self._started is None:
            self._started = time.time()
        elapsed = time.time() - self._started
        if elapsed > self._timeout:
            return NodeStatus.FAILURE
        return self.child.tick(blackboard)

    def reset(self) -> None:
        self._started = None
        self.child.reset()


class Cooldown(BehaviorNode):
    """Prevents child from running more than once per period."""

    def __init__(self, child: BehaviorNode, seconds: float, name: str = ""):
        super().__init__(name)
        self.child = child
        self._cooldown = seconds
        self._last_run: float = 0.0
        child._parent = self

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        now = time.time()
        if now - self._last_run < self._cooldown:
            return NodeStatus.RUNNING
        status = self.child.tick(blackboard)
        self._last_run = now
        return status

    def reset(self) -> None:
        self._last_run = 0.0
        self.child.reset()


class Condition(BehaviorNode):
    """Evaluates a boolean condition."""

    def __init__(self, condition: Callable[[Blackboard], bool], name: str = ""):
        super().__init__(name)
        self._condition = condition

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        return NodeStatus.SUCCESS if self._condition(blackboard) else NodeStatus.FAILURE


class Action(BehaviorNode):
    """Executes a custom action function."""

    def __init__(self, action: Callable[[Blackboard], NodeStatus], name: str = ""):
        super().__init__(name)
        self._action = action

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        return self._action(blackboard)


class Wait(BehaviorNode):
    """Waits for specified seconds."""

    def __init__(self, seconds: float, name: str = ""):
        super().__init__(name or f"Wait({seconds}s)")
        self._duration = seconds
        self._started: Optional[float] = None

    def tick(self, blackboard: Blackboard) -> NodeStatus:
        if self._started is None:
            self._started = time.time()
        if time.time() - self._started >= self._duration:
            self._started = None
            return NodeStatus.SUCCESS
        return NodeStatus.RUNNING

    def reset(self) -> None:
        self._started = None


class BehaviorTree:
    """
    Behavior tree with root node and blackboard.

    Provides tick-driven AI decision making for NPCs.
    AI agents construct behavior trees programmatically
    to define complex character behaviors through
    composable nodes — actions, conditions, composites.
    """

    _instance: Optional["BehaviorTree"] = None

    def __init__(self):
        self._trees: Dict[str, BehaviorNode] = {}
        self._blackboards: Dict[str, Blackboard] = {}
        self._active_trees: Dict[str, NodeStatus] = {}
        self._MAX_TREES = 100

    @classmethod
    def get_instance(cls) -> "BehaviorTree":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create(self, tree_id: str, root: BehaviorNode) -> Blackboard:
        self._trees[tree_id] = root
        bb = Blackboard()
        self._blackboards[tree_id] = bb
        if len(self._trees) > self._MAX_TREES:
            oldest = next(iter(self._trees))
            self._trees.pop(oldest, None)
            self._blackboards.pop(oldest, None)
        return bb

    def tick(self, tree_id: str) -> NodeStatus:
        root = self._trees.get(tree_id)
        bb = self._blackboards.get(tree_id)
        if not root or not bb:
            return NodeStatus.FAILURE
        status = root.tick(bb)
        self._active_trees[tree_id] = status
        return status

    def tick_all(self) -> Dict[str, NodeStatus]:
        results = {}
        for tree_id in list(self._trees.keys()):
            results[tree_id] = self.tick(tree_id)
        return results

    def get_blackboard(self, tree_id: str) -> Optional[Blackboard]:
        return self._blackboards.get(tree_id)

    def get_status(self, tree_id: str) -> Optional[NodeStatus]:
        return self._active_trees.get(tree_id)

    def reset(self, tree_id: str) -> None:
        root = self._trees.get(tree_id)
        if root:
            root.reset()
            self._active_trees.pop(tree_id, None)

    def remove(self, tree_id: str) -> None:
        self._trees.pop(tree_id, None)
        self._blackboards.pop(tree_id, None)
        self._active_trees.pop(tree_id, None)

    def list_trees(self) -> List[str]:
        return list(self._trees.keys())

    def get_stats(self) -> dict:
        return {
            "total_trees": len(self._trees),
            "active_trees": len(self._active_trees),
            "running": sum(
                1 for s in self._active_trees.values()
                if s == NodeStatus.RUNNING
            ),
            "blackboards": len(self._blackboards),
        }

    def clear(self) -> None:
        self._trees.clear()
        self._blackboards.clear()
        self._active_trees.clear()


def get_behavior_tree() -> BehaviorTree:
    return BehaviorTree.get_instance()
