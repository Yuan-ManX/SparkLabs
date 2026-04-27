"""
SparkAI Workflow - Graph-based Workflow System
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum


class PinType(Enum):
    ANY = "any"
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    TEXT = "text"
    MODEL = "model"
    NUMBER = "number"
    BOOLEAN = "boolean"
    TRIGGER = "trigger"


@dataclass
class WorkflowPin:
    id: str = ""
    name: str = ""
    pin_type: PinType = PinType.ANY
    is_input: bool = True
    value: Any = None

    def can_connect_to(self, other: "WorkflowPin") -> bool:
        if self.is_input == other.is_input:
            return False
        if self.pin_type == PinType.ANY or other.pin_type == PinType.ANY:
            return True
        return self.pin_type == other.pin_type


@dataclass
class WorkflowEdge:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source_node_id: str = ""
    source_pin_index: int = 0
    target_node_id: str = ""
    target_pin_index: int = 0


@dataclass
class WorkflowNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Node"
    category: str = "general"
    node_type: str = "default"
    position: List[float] = field(default_factory=lambda: [0.0, 0.0])
    properties: Dict[str, Any] = field(default_factory=dict)
    input_pins: List[WorkflowPin] = field(default_factory=list)
    output_pins: List[WorkflowPin] = field(default_factory=list)

    def set_property(self, key: str, value: Any) -> None:
        self.properties[key] = value

    def get_property(self, key: str, default: Any = None) -> Any:
        return self.properties.get(key, default)

    def add_input_pin(self, name: str, pin_type: PinType = PinType.ANY) -> None:
        self.input_pins.append(
            WorkflowPin(id=f"{self.id}_in_{len(self.input_pins)}", name=name, pin_type=pin_type, is_input=True)
        )

    def add_output_pin(self, name: str, pin_type: PinType = PinType.ANY) -> None:
        self.output_pins.append(
            WorkflowPin(id=f"{self.id}_out_{len(self.output_pins)}", name=name, pin_type=pin_type, is_input=False)
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "node_type": self.node_type,
            "position": self.position,
            "properties": self.properties,
            "input_pins": [{"name": p.name, "type": p.pin_type.value} for p in self.input_pins],
            "output_pins": [{"name": p.name, "type": p.pin_type.value} for p in self.output_pins],
        }


class WorkflowGraph:
    """
    Node-graph workflow for composing AI pipelines.
    Supports topological execution with typed pin connections.
    """

    def __init__(self, name: str = "Untitled Workflow"):
        self.id = str(uuid.uuid4())
        self.name = name
        self._nodes: Dict[str, WorkflowNode] = {}
        self._edges: List[WorkflowEdge] = []

    def add_node(self, node: WorkflowNode) -> None:
        self._nodes[node.id] = node

    def remove_node(self, node_id: str) -> bool:
        if node_id in self._nodes:
            del self._nodes[node_id]
            self._edges = [
                e for e in self._edges
                if e.source_node_id != node_id and e.target_node_id != node_id
            ]
            return True
        return False

    def get_node(self, node_id: str) -> Optional[WorkflowNode]:
        return self._nodes.get(node_id)

    def connect(
        self,
        source_node_id: str,
        source_pin: int,
        target_node_id: str,
        target_pin: int,
    ) -> Optional[WorkflowEdge]:
        source = self._nodes.get(source_node_id)
        target = self._nodes.get(target_node_id)
        if not source or not target:
            return None

        if source_pin < len(source.output_pins) and target_pin < len(target.input_pins):
            out_pin = source.output_pins[source_pin]
            in_pin = target.input_pins[target_pin]
            if out_pin.can_connect_to(in_pin):
                edge = WorkflowEdge(
                    source_node_id=source_node_id,
                    source_pin_index=source_pin,
                    target_node_id=target_node_id,
                    target_pin_index=target_pin,
                )
                self._edges.append(edge)
                return edge
        return None

    def disconnect(self, edge_id: str) -> bool:
        for i, edge in enumerate(self._edges):
            if edge.id == edge_id:
                self._edges.pop(i)
                return True
        return False

    def get_nodes(self) -> List[WorkflowNode]:
        return list(self._nodes.values())

    def get_edges(self) -> List[WorkflowEdge]:
        return list(self._edges)

    def get_execution_order(self) -> List[str]:
        in_degree: Dict[str, int] = {nid: 0 for nid in self._nodes}
        for edge in self._edges:
            if edge.target_node_id in in_degree:
                in_degree[edge.target_node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        order = []

        while queue:
            node_id = queue.pop(0)
            order.append(node_id)
            for edge in self._edges:
                if edge.source_node_id == node_id:
                    target = edge.target_node_id
                    in_degree[target] -= 1
                    if in_degree[target] == 0:
                        queue.append(target)

        return order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self._nodes.values()],
            "edges": [
                {
                    "id": e.id,
                    "source": e.source_node_id,
                    "source_pin": e.source_pin_index,
                    "target": e.target_node_id,
                    "target_pin": e.target_pin_index,
                }
                for e in self._edges
            ],
        }
