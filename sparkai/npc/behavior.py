"""
SparkAI NPC - Behavior Tree System
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


class NodeStatus:
    SUCCESS = "success"
    FAILURE = "failure"
    RUNNING = "running"


class BehaviorNode:
    """
    A single node in a behavior tree.
    Supports selector, sequence, decorator, and action types.
    """

    def __init__(
        self,
        name: str = "Node",
        node_type: str = "action",
        action: Optional[Callable] = None,
    ):
        self.id = str(uuid.uuid4())
        self.name = name
        self.node_type = node_type
        self.action = action
        self.children: List[BehaviorNode] = []
        self.status = NodeStatus.FAILURE
        self.properties: Dict[str, Any] = {}

    def add_child(self, child: "BehaviorNode") -> None:
        self.children.append(child)

    def remove_child(self, child_id: str) -> bool:
        for i, child in enumerate(self.children):
            if child.id == child_id:
                self.children.pop(i)
                return True
        return False

    def evaluate(self) -> Optional[str]:
        if self.node_type == "selector":
            return self._evaluate_selector()
        elif self.node_type == "sequence":
            return self._evaluate_sequence()
        elif self.node_type == "decorator":
            return self._evaluate_decorator()
        elif self.node_type == "parallel":
            return self._evaluate_parallel()
        else:
            return self._evaluate_action()

    def _evaluate_selector(self) -> Optional[str]:
        for child in self.children:
            result = child.evaluate()
            if result is not None:
                self.status = NodeStatus.SUCCESS
                return result
        self.status = NodeStatus.FAILURE
        return None

    def _evaluate_sequence(self) -> Optional[str]:
        last_result = None
        for child in self.children:
            result = child.evaluate()
            if result is None:
                self.status = NodeStatus.FAILURE
                return None
            last_result = result
        self.status = NodeStatus.SUCCESS
        return last_result

    def _evaluate_decorator(self) -> Optional[str]:
        if not self.children:
            return None
        invert = self.properties.get("invert", False)
        repeat = self.properties.get("repeat", 1)

        for _ in range(repeat):
            result = self.children[0].evaluate()
            if invert:
                if result is None:
                    self.status = NodeStatus.SUCCESS
                    return "inverted_success"
                else:
                    self.status = NodeStatus.FAILURE
                    return None
        self.status = NodeStatus.SUCCESS
        return result

    def _evaluate_parallel(self) -> Optional[str]:
        results = []
        for child in self.children:
            result = child.evaluate()
            results.append(result)
        if any(r is not None for r in results):
            self.status = NodeStatus.SUCCESS
            return results[0] if results else None
        self.status = NodeStatus.FAILURE
        return None

    def _evaluate_action(self) -> Optional[str]:
        if self.action:
            try:
                result = self.action({})
                self.status = NodeStatus.SUCCESS if result else NodeStatus.FAILURE
                return self.name if result else None
            except Exception:
                self.status = NodeStatus.FAILURE
                return None
        self.status = NodeStatus.SUCCESS
        return self.name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.node_type,
            "status": self.status,
            "properties": self.properties,
            "children": [c.to_dict() for c in self.children],
        }


class BehaviorTree:
    """
    Behavior tree for NPC decision making.
    Supports selector, sequence, decorator, parallel, and action nodes.
    """

    def __init__(self):
        self.root: Optional[BehaviorNode] = None

    def set_root(self, node: BehaviorNode) -> None:
        self.root = node

    def evaluate(self) -> Optional[str]:
        if self.root:
            return self.root.evaluate()
        return None

    def find_node(self, node_id: str) -> Optional[BehaviorNode]:
        if not self.root:
            return None
        return self._find_node_recursive(self.root, node_id)

    def _find_node_recursive(self, node: BehaviorNode, node_id: str) -> Optional[BehaviorNode]:
        if node.id == node_id:
            return node
        for child in node.children:
            result = self._find_node_recursive(child, node_id)
            if result:
                return result
        return None

    def to_dict(self) -> Dict[str, Any]:
        if self.root:
            return self.root.to_dict()
        return {}
