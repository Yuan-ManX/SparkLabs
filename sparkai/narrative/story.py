"""
SparkAI Narrative - Story Graph System
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class StoryNodeType(Enum):
    BEGINNING = "beginning"
    PLOT_POINT = "plot_point"
    CHOICE = "choice"
    CLIMAX = "climax"
    RESOLUTION = "resolution"
    BRANCH = "branch"


@dataclass
class StoryNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Story Node"
    node_type: StoryNodeType = StoryNodeType.PLOT_POINT
    content: str = ""
    possible_next: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    conditions: Dict[str, Any] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)

    def add_next(self, node_id: str) -> None:
        if node_id not in self.possible_next:
            self.possible_next.append(node_id)

    def remove_next(self, node_id: str) -> None:
        if node_id in self.possible_next:
            self.possible_next.remove(node_id)

    def to_dict(self) -> Dict[str, Any]:
        type_value = self.node_type.value if isinstance(self.node_type, StoryNodeType) else str(self.node_type)
        return {
            "id": self.id,
            "name": self.name,
            "type": type_value,
            "content": self.content,
            "possible_next": self.possible_next,
            "properties": self.properties,
            "conditions": self.conditions,
            "variables": self.variables,
        }


@dataclass
class StoryDecision:
    node_id: str = ""
    choice_index: int = 0
    variables: Dict[str, Any] = field(default_factory=dict)


class StoryGraph:
    """
    Branching narrative graph for procedural story generation.
    Supports variable tracking, conditional branching, and player-driven traversal.
    """

    def __init__(self, name: str = "Untitled Story"):
        self.id = str(uuid.uuid4())
        self.name = name
        self._nodes: Dict[str, StoryNode] = {}
        self._current_node_id: Optional[str] = None
        self._variables: Dict[str, Any] = {}
        self._history: List[StoryDecision] = []

    def add_node(self, node: StoryNode) -> None:
        self._nodes[node.id] = node
        if len(self._nodes) == 1:
            self._current_node_id = node.id

    def remove_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            for node in self._nodes.values():
                node.remove_next(node_id)
            return True
        return False

    def get_node(self, node_id: str) -> Optional[StoryNode]:
        return self._nodes.get(node_id)

    def get_current_node(self) -> Optional[StoryNode]:
        if self._current_node_id:
            return self._nodes.get(self._current_node_id)
        return None

    def advance(self, choice_index: int = 0) -> Optional[StoryNode]:
        current = self.get_current_node()
        if not current:
            return None

        if choice_index < len(current.possible_next):
            next_id = current.possible_next[choice_index]
            next_node = self._nodes.get(next_id)
            if next_node:
                decision = StoryDecision(
                    node_id=current.id,
                    choice_index=choice_index,
                    variables=dict(self._variables),
                )
                self._history.append(decision)
                self._current_node_id = next_id
                self._apply_variables(next_node.variables)
                return next_node
        return None

    def set_variable(self, key: str, value: Any) -> None:
        self._variables[key] = value

    def get_variable(self, key: str, default: Any = None) -> Any:
        return self._variables.get(key, default)

    def get_history(self) -> List[Dict[str, Any]]:
        return [
            {"node_id": d.node_id, "choice_index": d.choice_index, "variables": d.variables}
            for d in self._history
        ]

    def reset(self) -> None:
        self._current_node_id = next(iter(self._nodes), None)
        self._variables = {}
        self._history = []

    def get_all_nodes(self) -> List[StoryNode]:
        return list(self._nodes.values())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "current_node": self._current_node_id,
            "variables": self._variables,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "history_length": len(self._history),
        }

    def _apply_variables(self, variables: Dict[str, Any]) -> None:
        for key, value in variables.items():
            self._variables[key] = value
