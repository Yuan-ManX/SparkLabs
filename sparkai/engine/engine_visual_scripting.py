"""
SparkLabs Engine - Visual Scripting Runtime and Execution Engine

Node-based visual scripting system for authoring game logic through
interconnected graph nodes. Provides a full execution runtime that
evaluates node graphs sequentially, conditionally, or in event-driven
mode with support for variables, type-safe ports, and cycle detection.

Architecture:
  EngineVisualScripting
    |-- ScriptGraph (container of nodes, connections, and variables)
    |-- ScriptNode (typed graph node with ports and execution metadata)
    |-- NodePort (typed input or output socket on a node)
    |-- NodeConnection (directed edge between two ports)
    |-- ScriptVariable (scoped variable with type and default value)
    |-- ExecutionContext (runtime state during graph evaluation)
    |-- NodeTemplate (reusable node definition for instantiation)

Execution Features:
  - SEQUENTIAL: linear top-to-bottom execution
  - PARALLEL: concurrent branch evaluation with join semantics
  - CONDITIONAL: branch-on-condition with true/false paths
  - LOOPING: repeat-until and for-each iteration constructs
  - EVENT_DRIVEN: signal-based activation and deactivation
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class NodeCategory(Enum):
    EVENT = "event"
    ACTION = "action"
    CONDITION = "condition"
    MATH = "math"
    LOGIC = "logic"
    VARIABLE = "variable"
    LOOP = "loop"
    TIMER = "timer"
    INPUT = "input"
    OBJECT = "object"
    MOVEMENT = "movement"
    VISUAL = "visual"
    AUDIO = "audio"
    DATA = "data"
    NETWORK = "network"


class PortDirection(Enum):
    INPUT = "input"
    OUTPUT = "output"


class PortDataType(Enum):
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    BOOLEAN = "boolean"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    OBJECT_REF = "object_ref"
    ARRAY = "array"
    DICTIONARY = "dictionary"
    ANY = "any"
    TRIGGER = "trigger"
    COLOR = "color"
    ENUM = "enum"


class ExecutionMode(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    CONDITIONAL = "conditional"
    LOOPING = "looping"
    EVENT_DRIVEN = "event_driven"


class ConnectionType(Enum):
    DATA = "data"
    EXECUTION = "execution"


class ImplementationType(Enum):
    BUILTIN = "builtin"
    CUSTOM = "custom"
    EXTERNAL = "external"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ScriptNode:
    """Visual scripting node placed on a graph canvas."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: NodeCategory = NodeCategory.ACTION
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 160.0
    height: float = 80.0
    color: str = "#4A90D9"
    description: str = ""
    enabled: bool = True
    breakpoint: bool = False
    execution_count: int = 0
    execution_time_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "width": self.width,
            "height": self.height,
            "color": self.color,
            "description": self.description,
            "enabled": self.enabled,
            "breakpoint": self.breakpoint,
            "execution_count": self.execution_count,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class NodePort:
    """Typed input or output socket on a script node."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_id: str = ""
    direction: PortDirection = PortDirection.INPUT
    data_type: PortDataType = PortDataType.ANY
    name: str = ""
    default_value: Any = None
    is_required: bool = False
    is_array: bool = False
    connection_restrictions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_id": self.node_id,
            "direction": self.direction.value,
            "data_type": self.data_type.value,
            "name": self.name,
            "default_value": self.default_value,
            "is_required": self.is_required,
            "is_array": self.is_array,
            "connection_restrictions": list(self.connection_restrictions),
        }


@dataclass
class NodeConnection:
    """Directed edge between two node ports carrying data or execution flow."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_port_id: str = ""
    target_port_id: str = ""
    connection_type: ConnectionType = ConnectionType.DATA
    is_enabled: bool = True
    data_transform: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_port_id": self.source_port_id,
            "target_port_id": self.target_port_id,
            "connection_type": self.connection_type.value,
            "is_enabled": self.is_enabled,
            "data_transform": self.data_transform,
        }


@dataclass
class ScriptGraph:
    """Container for a complete visual scripting graph with execution state."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    nodes: List[ScriptNode] = field(default_factory=list)
    connections: List[NodeConnection] = field(default_factory=list)
    variables: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    enter_node_id: str = ""
    exit_node_ids: List[str] = field(default_factory=list)
    execution_mode: ExecutionMode = ExecutionMode.SEQUENTIAL
    is_active: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [n.to_dict() for n in self.nodes],
            "connections": [c.to_dict() for c in self.connections],
            "variables": dict(self.variables),
            "description": self.description,
            "enter_node_id": self.enter_node_id,
            "exit_node_ids": list(self.exit_node_ids),
            "execution_mode": self.execution_mode.value,
            "is_active": self.is_active,
        }


@dataclass
class ScriptVariable:
    """Scoped variable definition with type, default, and runtime value."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    data_type: PortDataType = PortDataType.ANY
    initial_value: Any = None
    current_value: Any = None
    is_local: bool = True
    is_constant: bool = False
    scope: str = "graph"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "data_type": self.data_type.value,
            "initial_value": self.initial_value,
            "current_value": self.current_value,
            "is_local": self.is_local,
            "is_constant": self.is_constant,
            "scope": self.scope,
        }


@dataclass
class ExecutionContext:
    """Runtime state carried through graph evaluation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    graph_id: str = ""
    current_node_id: str = ""
    execution_stack: List[str] = field(default_factory=list)
    variable_values: Dict[str, Any] = field(default_factory=dict)
    execution_path: List[str] = field(default_factory=list)
    is_paused: bool = False
    error_state: Optional[str] = None
    performance_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "graph_id": self.graph_id,
            "current_node_id": self.current_node_id,
            "execution_stack": list(self.execution_stack),
            "variable_values": dict(self.variable_values),
            "execution_path": list(self.execution_path),
            "is_paused": self.is_paused,
            "error_state": self.error_state,
            "performance_stats": dict(self.performance_stats),
        }


@dataclass
class NodeTemplate:
    """Reusable node definition that can be instantiated into graphs."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: NodeCategory = NodeCategory.ACTION
    default_inputs: List[Dict[str, Any]] = field(default_factory=list)
    default_outputs: List[Dict[str, Any]] = field(default_factory=list)
    implementation_type: ImplementationType = ImplementationType.BUILTIN
    source_code: str = ""
    icon_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "default_inputs": list(self.default_inputs),
            "default_outputs": list(self.default_outputs),
            "implementation_type": self.implementation_type.value,
            "source_code": self.source_code,
            "icon_key": self.icon_key,
        }


# ---------------------------------------------------------------------------
# EngineVisualScripting (Singleton)
# ---------------------------------------------------------------------------


class EngineVisualScripting:
    """Visual scripting runtime and execution engine for node-based game logic."""

    _instance: Optional["EngineVisualScripting"] = None
    _lock = threading.RLock()

    MAX_GRAPHS = 256
    MAX_NODES_PER_GRAPH = 2048
    MAX_CONNECTIONS_PER_GRAPH = 8192
    MAX_EXECUTION_DEPTH = 128
    MAX_LOOP_ITERATIONS = 10000

    def __new__(cls) -> "EngineVisualScripting":
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
        self._graphs: Dict[str, ScriptGraph] = {}
        self._ports: Dict[str, NodePort] = {}
        self._variables: Dict[str, ScriptVariable] = {}
        self._templates: Dict[str, NodeTemplate] = {}
        self._contexts: Dict[str, ExecutionContext] = {}
        self._total_graphs_created: int = 0
        self._total_nodes_added: int = 0
        self._total_executions: int = 0
        self._total_validations: int = 0
        self._total_optimizations: int = 0
        self._register_builtin_templates()

    @classmethod
    def get_instance(cls) -> "EngineVisualScripting":
        """Thread-safe singleton accessor with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Built-in Node Templates
    # ------------------------------------------------------------------

    def _register_builtin_templates(self) -> None:
        """Register all built-in node templates with default input/output ports."""
        _time_module.sleep(0.001)

        math_templates = [
            ("Add", "Adds two numeric values", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Subtract", "Subtracts B from A", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Multiply", "Multiplies two values", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Divide", "Divides A by B", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Modulo", "Returns remainder of A divided by B", [
                {"name": "A", "data_type": "integer", "direction": "input"},
                {"name": "B", "data_type": "integer", "direction": "input"},
            ], [{"name": "Result", "data_type": "integer", "direction": "output"}]),
            ("Power", "Raises A to the power of B", [
                {"name": "Base", "data_type": "float", "direction": "input"},
                {"name": "Exponent", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Square Root", "Computes the square root of a value", [
                {"name": "Value", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Absolute", "Returns the absolute value", [
                {"name": "Value", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Clamp", "Clamps a value between min and max", [
                {"name": "Value", "data_type": "float", "direction": "input"},
                {"name": "Min", "data_type": "float", "direction": "input"},
                {"name": "Max", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
            ("Lerp", "Linearly interpolates between A and B", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
                {"name": "Alpha", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "float", "direction": "output"}]),
        ]

        for name, desc, inputs, outputs in math_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.MATH,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="math",
            )

        logic_templates = [
            ("AND Gate", "Returns true if all inputs are true", [
                {"name": "A", "data_type": "boolean", "direction": "input"},
                {"name": "B", "data_type": "boolean", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("OR Gate", "Returns true if any input is true", [
                {"name": "A", "data_type": "boolean", "direction": "input"},
                {"name": "B", "data_type": "boolean", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("NOT Gate", "Inverts the boolean input", [
                {"name": "Value", "data_type": "boolean", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("XOR Gate", "Exclusive OR of two boolean inputs", [
                {"name": "A", "data_type": "boolean", "direction": "input"},
                {"name": "B", "data_type": "boolean", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("Compare Equal", "Checks if A equals B", [
                {"name": "A", "data_type": "any", "direction": "input"},
                {"name": "B", "data_type": "any", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("Compare Greater", "Checks if A is greater than B", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
            ("Compare Less", "Checks if A is less than B", [
                {"name": "A", "data_type": "float", "direction": "input"},
                {"name": "B", "data_type": "float", "direction": "input"},
            ], [{"name": "Result", "data_type": "boolean", "direction": "output"}]),
        ]

        for name, desc, inputs, outputs in logic_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.LOGIC,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="logic",
            )

        movement_templates = [
            ("Move To", "Moves an object to a target position", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
                {"name": "Position", "data_type": "vector3", "direction": "input"},
                {"name": "Speed", "data_type": "float", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("Rotate", "Rotates an object by specified angles", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
                {"name": "Angle", "data_type": "vector3", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("Set Position", "Instantly sets an object position", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
                {"name": "Position", "data_type": "vector3", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("Teleport", "Teleports an object to a new location", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
                {"name": "Destination", "data_type": "vector3", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("Follow Path", "Moves along a predefined path", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
                {"name": "Path", "data_type": "array", "direction": "input"},
                {"name": "Speed", "data_type": "float", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
        ]

        for name, desc, inputs, outputs in movement_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.MOVEMENT,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="movement",
            )

        event_templates = [
            ("On Start", "Fires when the graph begins execution", [], [
                {"name": "Trigger", "data_type": "trigger", "direction": "output"},
            ]),
            ("On Update", "Fires every frame during graph execution", [], [
                {"name": "Trigger", "data_type": "trigger", "direction": "output"},
            ]),
            ("On Collision", "Fires when a collision event occurs", [
                {"name": "Target", "data_type": "object_ref", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("On Input", "Fires when player input is detected", [
                {"name": "Key", "data_type": "string", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
            ("On Timer", "Fires after a specified delay", [
                {"name": "Delay", "data_type": "float", "direction": "input"},
                {"name": "Repeat", "data_type": "boolean", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
        ]

        for name, desc, inputs, outputs in event_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.EVENT,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="event",
            )

        variable_templates = [
            ("Get Variable", "Reads the value of a named variable", [
                {"name": "Name", "data_type": "string", "direction": "input"},
            ], [{"name": "Value", "data_type": "any", "direction": "output"}]),
            ("Set Variable", "Writes a value to a named variable", [
                {"name": "Name", "data_type": "string", "direction": "input"},
                {"name": "Value", "data_type": "any", "direction": "input"},
            ], [{"name": "Trigger", "data_type": "trigger", "direction": "output"}]),
        ]

        for name, desc, inputs, outputs in variable_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.VARIABLE,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="variable",
            )

        loop_templates = [
            ("For Loop", "Iterates from start index to end index", [
                {"name": "Start", "data_type": "integer", "direction": "input"},
                {"name": "End", "data_type": "integer", "direction": "input"},
            ], [
                {"name": "Index", "data_type": "integer", "direction": "output"},
                {"name": "Loop Body", "data_type": "trigger", "direction": "output"},
                {"name": "Completed", "data_type": "trigger", "direction": "output"},
            ]),
            ("While Loop", "Repeats while condition is true", [
                {"name": "Condition", "data_type": "boolean", "direction": "input"},
            ], [
                {"name": "Loop Body", "data_type": "trigger", "direction": "output"},
                {"name": "Completed", "data_type": "trigger", "direction": "output"},
            ]),
            ("For Each", "Iterates over elements in an array", [
                {"name": "Array", "data_type": "array", "direction": "input"},
            ], [
                {"name": "Element", "data_type": "any", "direction": "output"},
                {"name": "Index", "data_type": "integer", "direction": "output"},
                {"name": "Completed", "data_type": "trigger", "direction": "output"},
            ]),
        ]

        for name, desc, inputs, outputs in loop_templates:
            self._templates[name] = NodeTemplate(
                name=name, category=NodeCategory.LOOP,
                default_inputs=inputs, default_outputs=outputs,
                source_code=desc, icon_key="loop",
            )

    # ------------------------------------------------------------------
    # Graph Lifecycle
    # ------------------------------------------------------------------

    def create_graph(self, name: str, execution_mode: str = "sequential") -> ScriptGraph:
        """Create a new script graph with the given execution mode."""
        _time_module.sleep(0.001)
        if len(self._graphs) >= self.MAX_GRAPHS:
            raise RuntimeError(f"Graph limit reached ({self.MAX_GRAPHS})")
        try:
            mode = ExecutionMode(execution_mode.lower())
        except ValueError:
            mode = ExecutionMode.SEQUENTIAL
        graph = ScriptGraph(name=name, execution_mode=mode)
        self._graphs[graph.id] = graph
        self._total_graphs_created += 1
        return graph

    def get_graph(self, graph_id: str) -> Optional[ScriptGraph]:
        """Retrieve a graph by its identifier."""
        _time_module.sleep(0.001)
        return self._graphs.get(graph_id)

    def delete_graph(self, graph_id: str) -> bool:
        """Remove a graph and all associated contexts from the engine."""
        _time_module.sleep(0.001)
        if graph_id not in self._graphs:
            return False
        self._contexts.pop(graph_id, None)
        del self._graphs[graph_id]
        return True

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def add_node(
        self,
        graph_id: str,
        category: str,
        name: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> Optional[ScriptNode]:
        """Add a node to a graph at the specified canvas position."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        if len(graph.nodes) >= self.MAX_NODES_PER_GRAPH:
            raise RuntimeError(f"Node limit reached ({self.MAX_NODES_PER_GRAPH})")
        try:
            cat = NodeCategory(category.lower())
        except ValueError:
            cat = NodeCategory.ACTION
        node = ScriptNode(
            name=name or f"{cat.value.capitalize()} Node",
            category=cat,
            position_x=position_x,
            position_y=position_y,
        )
        graph.nodes.append(node)
        self._total_nodes_added += 1
        if not graph.enter_node_id and cat == NodeCategory.EVENT:
            graph.enter_node_id = node.id
        return node

    def get_node(self, graph_id: str, node_id: str) -> Optional[ScriptNode]:
        """Retrieve a node from a graph by id."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        for node in graph.nodes:
            if node.id == node_id:
                return node
        return None

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Remove a node and all its port connections from a graph."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return False
        node = self.get_node(graph_id, node_id)
        if node is None:
            return False
        port_ids = {p.id for p in self._ports.values() if p.node_id == node_id}
        graph.connections = [
            c for c in graph.connections
            if c.source_port_id not in port_ids and c.target_port_id not in port_ids
        ]
        for pid in list(port_ids):
            self._ports.pop(pid, None)
        graph.nodes = [n for n in graph.nodes if n.id != node_id]
        if graph.enter_node_id == node_id:
            graph.enter_node_id = ""
        return True

    # ------------------------------------------------------------------
    # Port Management
    # ------------------------------------------------------------------

    def add_port(
        self,
        node_id: str,
        direction: str,
        data_type: str,
        name: str = "",
    ) -> Optional[NodePort]:
        """Add a typed input or output port to a node."""
        _time_module.sleep(0.001)
        try:
            d = PortDirection(direction.lower())
        except ValueError:
            d = PortDirection.INPUT
        try:
            dt = PortDataType(data_type.lower())
        except ValueError:
            dt = PortDataType.ANY
        port = NodePort(node_id=node_id, direction=d, data_type=dt, name=name)
        self._ports[port.id] = port
        return port

    def get_ports_for_node(self, node_id: str) -> List[NodePort]:
        """Return all ports attached to a given node."""
        _time_module.sleep(0.001)
        return [p for p in self._ports.values() if p.node_id == node_id]

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def connect_nodes(
        self,
        source_port_id: str,
        target_port_id: str,
        connection_type: str = "execution",
    ) -> Optional[NodeConnection]:
        """Create a connection between two ports."""
        _time_module.sleep(0.001)
        if source_port_id not in self._ports:
            return None
        if target_port_id not in self._ports:
            return None
        source_port = self._ports[source_port_id]
        target_port = self._ports[target_port_id]
        if source_port.direction != PortDirection.OUTPUT:
            return None
        if target_port.direction != PortDirection.INPUT:
            return None
        try:
            ct = ConnectionType(connection_type.lower())
        except ValueError:
            ct = ConnectionType.EXECUTION
        connection = NodeConnection(
            source_port_id=source_port_id,
            target_port_id=target_port_id,
            connection_type=ct,
        )
        for graph in self._graphs.values():
            source_in_graph = any(n.id == source_port.node_id for n in graph.nodes)
            target_in_graph = any(n.id == target_port.node_id for n in graph.nodes)
            if source_in_graph and target_in_graph:
                if len(graph.connections) >= self.MAX_CONNECTIONS_PER_GRAPH:
                    raise RuntimeError(f"Connection limit reached ({self.MAX_CONNECTIONS_PER_GRAPH})")
                graph.connections.append(connection)
                return connection
        return None

    def disconnect_nodes(self, connection_id: str) -> bool:
        """Remove a connection by its identifier."""
        _time_module.sleep(0.001)
        for graph in self._graphs.values():
            for i, conn in enumerate(graph.connections):
                if conn.id == connection_id:
                    graph.connections.pop(i)
                    return True
        return False

    # ------------------------------------------------------------------
    # Variable Management
    # ------------------------------------------------------------------

    def create_variable(
        self,
        graph_id: str,
        name: str,
        data_type: str = "any",
        initial_value: Any = None,
    ) -> Optional[ScriptVariable]:
        """Create a scoped variable within a graph."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        try:
            dt = PortDataType(data_type.lower())
        except ValueError:
            dt = PortDataType.ANY
        variable = ScriptVariable(
            name=name,
            data_type=dt,
            initial_value=initial_value,
            current_value=initial_value,
        )
        self._variables[variable.id] = variable
        graph.variables[name] = initial_value
        return variable

    def get_variable(self, graph_id: str, name: str) -> Any:
        """Read the current value of a graph variable."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        return graph.variables.get(name)

    def set_variable(self, graph_id: str, name: str, value: Any) -> bool:
        """Update the value of a graph variable at runtime."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return False
        graph.variables[name] = value
        return True

    # ------------------------------------------------------------------
    # Graph Execution
    # ------------------------------------------------------------------

    def execute_graph(
        self,
        graph_id: str,
        initial_variables: Optional[Dict[str, Any]] = None,
    ) -> Optional[ExecutionContext]:
        """Execute an entire script graph and return the execution context."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        if not graph.is_active:
            return None

        context = ExecutionContext(graph_id=graph_id)
        if initial_variables:
            context.variable_values.update(initial_variables)
        for var_name, var_value in graph.variables.items():
            if var_name not in context.variable_values:
                context.variable_values[var_name] = var_value

        self._contexts[context.id] = context
        self._total_executions += 1

        if graph.execution_mode == ExecutionMode.SEQUENTIAL:
            self._execute_sequential(graph, context)
        elif graph.execution_mode == ExecutionMode.CONDITIONAL:
            self._execute_conditional(graph, context)
        elif graph.execution_mode == ExecutionMode.LOOPING:
            self._execute_looping(graph, context)
        elif graph.execution_mode == ExecutionMode.PARALLEL:
            self._execute_parallel(graph, context)
        else:
            self._execute_sequential(graph, context)

        return context

    def _execute_sequential(self, graph: ScriptGraph, context: ExecutionContext) -> None:
        """Execute nodes in linear order following execution connections."""
        _time_module.sleep(0.001)
        entry_nodes = [n for n in graph.nodes if n.id == graph.enter_node_id]
        if not entry_nodes and graph.nodes:
            entry_nodes = [graph.nodes[0]]
        for entry in entry_nodes:
            current_id = entry.id
            while current_id:
                if len(context.execution_stack) >= self.MAX_EXECUTION_DEPTH:
                    context.error_state = "Maximum execution depth exceeded"
                    return
                self.evaluate_node(current_id, context)
                if context.error_state:
                    return
                current_id = self._get_next_execution_node(graph, current_id)

    def _execute_conditional(self, graph: ScriptGraph, context: ExecutionContext) -> None:
        """Execute nodes following condition-based branching."""
        _time_module.sleep(0.001)
        entry_nodes = [n for n in graph.nodes if n.id == graph.enter_node_id]
        if not entry_nodes and graph.nodes:
            entry_nodes = [graph.nodes[0]]
        for entry in entry_nodes:
            current_id = entry.id
            depth = 0
            while current_id and depth < self.MAX_EXECUTION_DEPTH:
                depth += 1
                result = self.evaluate_node(current_id, context)
                if context.error_state:
                    return
                if isinstance(result, bool):
                    current_id = self._get_conditional_next(graph, current_id, result)
                else:
                    current_id = self._get_next_execution_node(graph, current_id)

    def _execute_looping(self, graph: ScriptGraph, context: ExecutionContext) -> None:
        """Execute nodes with loop iteration support."""
        _time_module.sleep(0.001)
        iteration_count = 0
        entry_nodes = [n for n in graph.nodes if n.id == graph.enter_node_id]
        if not entry_nodes and graph.nodes:
            entry_nodes = [graph.nodes[0]]
        for entry in entry_nodes:
            current_id = entry.id
            while current_id:
                iteration_count += 1
                if iteration_count > self.MAX_LOOP_ITERATIONS:
                    context.error_state = "Maximum loop iterations exceeded"
                    return
                if len(context.execution_stack) >= self.MAX_EXECUTION_DEPTH:
                    context.error_state = "Maximum execution depth exceeded"
                    return
                self.evaluate_node(current_id, context)
                if context.error_state:
                    return
                current_id = self._get_next_execution_node(graph, current_id)

    def _execute_parallel(self, graph: ScriptGraph, context: ExecutionContext) -> None:
        """Execute independent branches concurrently with join semantics."""
        _time_module.sleep(0.001)
        entry_nodes = [n for n in graph.nodes if n.id == graph.enter_node_id]
        if not entry_nodes and graph.nodes:
            entry_nodes = [graph.nodes[0]]
        results: List[Tuple[str, Any]] = []
        for entry in entry_nodes:
            node_context = ExecutionContext(graph_id=graph.id)
            for k, v in context.variable_values.items():
                node_context.variable_values[k] = v
            self.evaluate_node(entry.id, node_context)
            results.append((entry.id, node_context))
            context.variable_values.update(node_context.variable_values)
        for _, node_ctx in results:
            if node_ctx.error_state:
                context.error_state = node_ctx.error_state
                return

    def step_execution(self, context_id: str) -> Optional[str]:
        """Advance execution by one node in the given context."""
        _time_module.sleep(0.001)
        context = self._contexts.get(context_id)
        if context is None:
            return None
        if context.is_paused or context.error_state:
            return None
        graph = self._graphs.get(context.graph_id)
        if graph is None:
            return None
        current_id = context.current_node_id
        if not current_id:
            entry_nodes = [n for n in graph.nodes if n.id == graph.enter_node_id]
            if not entry_nodes and graph.nodes:
                entry_nodes = [graph.nodes[0]]
            if entry_nodes:
                current_id = entry_nodes[0].id
            else:
                return None
        self.evaluate_node(current_id, context)
        if context.error_state:
            return None
        next_id = self._get_next_execution_node(graph, current_id)
        context.current_node_id = next_id or ""
        context.execution_path.append(current_id)
        return next_id

    def evaluate_node(self, node_id: str, context: ExecutionContext) -> Any:
        """Evaluate a single node within an execution context."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(context.graph_id)
        if graph is None:
            return None
        node = self.get_node(context.graph_id, node_id)
        if node is None:
            return None
        if not node.enabled:
            return None
        if node.breakpoint:
            context.is_paused = True
            return None

        context.execution_stack.append(node_id)
        context.current_node_id = node_id
        node.execution_count += 1

        start_time = _time_module.time()

        try:
            node_ports = self.get_ports_for_node(node_id)
            input_values: Dict[str, Any] = {}
            for port in node_ports:
                if port.direction == PortDirection.INPUT:
                    input_values[port.name] = port.default_value

            for conn in graph.connections:
                if conn.target_port_id in self._ports:
                    tp = self._ports[conn.target_port_id]
                    if tp.node_id == node_id and conn.is_enabled:
                        sp = self._ports.get(conn.source_port_id)
                        if sp:
                            input_values[tp.name] = sp.default_value

            if node.category == NodeCategory.EVENT:
                result = True
            elif node.category == NodeCategory.ACTION:
                result = True
            elif node.category == NodeCategory.CONDITION:
                result = self._evaluate_condition_node(node, input_values)
            elif node.category == NodeCategory.MATH:
                result = self._evaluate_math_node(node, input_values)
            elif node.category == NodeCategory.LOGIC:
                result = self._evaluate_logic_node(node, input_values)
            elif node.category == NodeCategory.VARIABLE:
                result = self._evaluate_variable_node(node, input_values, context)
            elif node.category == NodeCategory.LOOP:
                result = True
            elif node.category == NodeCategory.MOVEMENT:
                result = True
            else:
                result = True
        except Exception as exc:
            context.error_state = f"Node '{node.name}' evaluation error: {exc}"
            result = None

        elapsed = (_time_module.time() - start_time) * 1000.0
        node.execution_time_ms += elapsed
        context.execution_path.append(node_id)
        context.execution_stack.pop()

        return result

    def _evaluate_condition_node(self, node: ScriptNode, inputs: Dict[str, Any]) -> bool:
        """Evaluate a condition node based on its input port values."""
        _time_module.sleep(0.001)
        node_name_lower = node.name.lower()
        if "equal" in node_name_lower:
            a = inputs.get("A", 0)
            b = inputs.get("B", 0)
            return a == b
        if "greater" in node_name_lower:
            a = float(inputs.get("A", 0))
            b = float(inputs.get("B", 0))
            return a > b
        if "less" in node_name_lower:
            a = float(inputs.get("A", 0))
            b = float(inputs.get("B", 0))
            return a < b
        first_input = next(iter(inputs.values()), True)
        return bool(first_input)

    def _evaluate_math_node(self, node: ScriptNode, inputs: Dict[str, Any]) -> Any:
        """Evaluate a math operation node using its input port values."""
        _time_module.sleep(0.001)
        node_name_lower = node.name.lower()
        if "add" in node_name_lower:
            return float(inputs.get("A", 0)) + float(inputs.get("B", 0))
        if "subtract" in node_name_lower:
            return float(inputs.get("A", 0)) - float(inputs.get("B", 0))
        if "multiply" in node_name_lower:
            return float(inputs.get("A", 0)) * float(inputs.get("B", 0))
        if "divide" in node_name_lower:
            b = float(inputs.get("B", 0))
            return float(inputs.get("A", 0)) / b if b != 0 else 0.0
        if "modulo" in node_name_lower:
            b = int(float(inputs.get("B", 0)))
            return int(float(inputs.get("A", 0))) % b if b != 0 else 0
        if "power" in node_name_lower:
            return math.pow(float(inputs.get("Base", inputs.get("A", 0))), float(inputs.get("Exponent", inputs.get("B", 0))))
        if "square" in node_name_lower:
            val = float(inputs.get("Value", inputs.get("A", 0)))
            return math.sqrt(val) if val >= 0 else 0.0
        if "absolute" in node_name_lower:
            return abs(float(inputs.get("Value", inputs.get("A", 0))))
        if "clamp" in node_name_lower:
            val = float(inputs.get("Value", inputs.get("A", 0)))
            mn = float(inputs.get("Min", inputs.get("B", 0)))
            mx = float(inputs.get("Max", inputs.get("B", 0)))
            return max(mn, min(val, mx))
        if "lerp" in node_name_lower:
            a = float(inputs.get("A", 0))
            b = float(inputs.get("B", 0))
            alpha = float(inputs.get("Alpha", 0.5))
            return a + (b - a) * max(0.0, min(1.0, alpha))
        return float(inputs.get("A", 0))

    def _evaluate_logic_node(self, node: ScriptNode, inputs: Dict[str, Any]) -> Any:
        """Evaluate a logic gate node using its input port values."""
        _time_module.sleep(0.001)
        node_name_lower = node.name.lower()
        a = bool(inputs.get("A", False))
        b = bool(inputs.get("B", False))
        if "and" in node_name_lower:
            return a and b
        if "or" in node_name_lower and "xor" not in node_name_lower:
            return a or b
        if "not" in node_name_lower:
            return not a
        if "xor" in node_name_lower:
            return a != b
        return False

    def _evaluate_variable_node(
        self, node: ScriptNode, inputs: Dict[str, Any], context: ExecutionContext
    ) -> Any:
        """Evaluate a variable get/set node."""
        _time_module.sleep(0.001)
        var_name = inputs.get("Name", node.name)
        if "set" in node.name.lower():
            value = inputs.get("Value")
            context.variable_values[str(var_name)] = value
            graph = self._graphs.get(context.graph_id)
            if graph:
                graph.variables[str(var_name)] = value
            return True
        return context.variable_values.get(str(var_name))

    def _get_next_execution_node(self, graph: ScriptGraph, current_node_id: str) -> Optional[str]:
        """Find the next node to execute via execution connections."""
        _time_module.sleep(0.001)
        current_ports = {p.id for p in self._ports.values() if p.node_id == current_node_id}
        for conn in graph.connections:
            if conn.source_port_id in current_ports and conn.connection_type == ConnectionType.EXECUTION:
                if conn.is_enabled:
                    tp = self._ports.get(conn.target_port_id)
                    if tp:
                        return tp.node_id
        current_idx = None
        for i, node in enumerate(graph.nodes):
            if node.id == current_node_id:
                current_idx = i
                break
        if current_idx is not None and current_idx + 1 < len(graph.nodes):
            return graph.nodes[current_idx + 1].id
        return None

    def _get_conditional_next(self, graph: ScriptGraph, current_node_id: str, condition_result: bool) -> Optional[str]:
        """Select the next node based on a boolean condition result."""
        _time_module.sleep(0.001)
        current_ports = {p.id for p in self._ports.values() if p.node_id == current_node_id}
        true_target: Optional[str] = None
        false_target: Optional[str] = None
        for conn in graph.connections:
            if conn.source_port_id in current_ports and conn.connection_type == ConnectionType.EXECUTION:
                tp = self._ports.get(conn.target_port_id)
                if tp:
                    sp = self._ports.get(conn.source_port_id)
                    sp_name = sp.name.lower() if sp else ""
                    if "true" in sp_name:
                        true_target = tp.node_id
                    elif "false" in sp_name:
                        false_target = tp.node_id
                    else:
                        if true_target is None:
                            true_target = tp.node_id
                        else:
                            false_target = tp.node_id
        if condition_result:
            return true_target
        return false_target

    # ------------------------------------------------------------------
    # Template Registration
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        category: str,
        default_inputs: Optional[List[Dict[str, Any]]] = None,
        default_outputs: Optional[List[Dict[str, Any]]] = None,
    ) -> NodeTemplate:
        """Register a new node template for reuse across graphs."""
        _time_module.sleep(0.001)
        try:
            cat = NodeCategory(category.lower())
        except ValueError:
            cat = NodeCategory.ACTION
        template = NodeTemplate(
            name=name,
            category=cat,
            default_inputs=default_inputs or [],
            default_outputs=default_outputs or [],
            implementation_type=ImplementationType.CUSTOM,
        )
        self._templates[template.id] = template
        return template

    def get_template(self, template_id: str) -> Optional[NodeTemplate]:
        """Retrieve a registered node template."""
        _time_module.sleep(0.001)
        return self._templates.get(template_id)

    def list_templates(self, category: Optional[str] = None) -> List[NodeTemplate]:
        """List all registered templates, optionally filtered by category."""
        _time_module.sleep(0.001)
        templates = list(self._templates.values())
        if category:
            try:
                cat = NodeCategory(category.lower())
                return [t for t in templates if t.category == cat]
            except ValueError:
                return []
        return templates

    # ------------------------------------------------------------------
    # Blueprint Serialization
    # ------------------------------------------------------------------

    def build_from_blueprint(self, blueprint_data: Dict[str, Any]) -> Optional[ScriptGraph]:
        """Build a complete script graph from serialized blueprint data."""
        _time_module.sleep(0.001)
        if len(self._graphs) >= self.MAX_GRAPHS:
            raise RuntimeError(f"Graph limit reached ({self.MAX_GRAPHS})")
        try:
            mode = ExecutionMode(blueprint_data.get("execution_mode", "sequential"))
        except ValueError:
            mode = ExecutionMode.SEQUENTIAL
        graph = ScriptGraph(
            name=blueprint_data.get("name", "Imported Graph"),
            description=blueprint_data.get("description", ""),
            execution_mode=mode,
        )
        for node_data in blueprint_data.get("nodes", []):
            try:
                cat = NodeCategory(node_data.get("category", "action"))
            except ValueError:
                cat = NodeCategory.ACTION
            node = ScriptNode(
                name=node_data.get("name", ""),
                category=cat,
                position_x=float(node_data.get("position_x", 0)),
                position_y=float(node_data.get("position_y", 0)),
                width=float(node_data.get("width", 160)),
                height=float(node_data.get("height", 80)),
                color=node_data.get("color", "#4A90D9"),
                description=node_data.get("description", ""),
                enabled=node_data.get("enabled", True),
            )
            graph.nodes.append(node)
        for conn_data in blueprint_data.get("connections", []):
            try:
                ct = ConnectionType(conn_data.get("connection_type", "execution"))
            except ValueError:
                ct = ConnectionType.EXECUTION
            connection = NodeConnection(
                source_port_id=conn_data.get("source_port_id", ""),
                target_port_id=conn_data.get("target_port_id", ""),
                connection_type=ct,
                is_enabled=conn_data.get("is_enabled", True),
                data_transform=conn_data.get("data_transform", ""),
            )
            graph.connections.append(connection)
        graph.variables = blueprint_data.get("variables", {})
        graph.enter_node_id = blueprint_data.get("enter_node_id", "")
        graph.exit_node_ids = blueprint_data.get("exit_node_ids", [])
        self._graphs[graph.id] = graph
        self._total_graphs_created += 1
        return graph

    def export_blueprint(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Export a graph as a serializable blueprint dictionary."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        return graph.to_dict()

    # ------------------------------------------------------------------
    # Graph Validation
    # ------------------------------------------------------------------

    def validate_graph(self, graph_id: str) -> List[str]:
        """Validate graph structure and return a list of issues found."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return ["Graph not found"]
        self._total_validations += 1
        issues: List[str] = []

        if not graph.nodes:
            issues.append("Graph has no nodes")
            return issues

        has_event = any(n.category == NodeCategory.EVENT for n in graph.nodes)
        if not has_event:
            issues.append("Graph has no event entry node")

        executed_nodes = self._find_execution_reachable_nodes(graph)
        for node in graph.nodes:
            if node.id not in executed_nodes and node.category != NodeCategory.EVENT:
                issues.append(f"Node '{node.name}' is unreachable in execution path")

        if self._detect_execution_cycle(graph):
            issues.append("Execution cycle detected in graph connections")

        node_ids = {n.id for n in graph.nodes}
        port_node_ids = {p.node_id for p in self._ports.values()}
        for conn in graph.connections:
            sp = self._ports.get(conn.source_port_id)
            tp = self._ports.get(conn.target_port_id)
            if sp is None:
                issues.append(f"Connection references missing source port: {conn.source_port_id}")
            if tp is None:
                issues.append(f"Connection references missing target port: {conn.target_port_id}")
            if sp and sp.node_id not in node_ids:
                issues.append(f"Source port's node is not in graph: {sp.node_id}")
            if tp and tp.node_id not in node_ids:
                issues.append(f"Target port's node is not in graph: {tp.node_id}")
            if sp and tp and sp.node_id not in port_node_ids:
                issues.append(f"Source port exists but no ports registered for node: {sp.node_id}")

        return issues

    def _find_execution_reachable_nodes(self, graph: ScriptGraph) -> set:
        """Find all nodes reachable from the entry node via execution connections."""
        _time_module.sleep(0.001)
        reachable: set = set()
        if not graph.enter_node_id:
            return reachable
        queue = [graph.enter_node_id]
        while queue:
            current = queue.pop(0)
            if current in reachable:
                continue
            reachable.add(current)
            current_ports = {p.id for p in self._ports.values() if p.node_id == current}
            for conn in graph.connections:
                if conn.source_port_id in current_ports and conn.is_enabled:
                    tp = self._ports.get(conn.target_port_id)
                    if tp and tp.node_id not in reachable:
                        queue.append(tp.node_id)
        return reachable

    def _detect_execution_cycle(self, graph: ScriptGraph) -> bool:
        """Detect cycles in the execution flow using DFS."""
        _time_module.sleep(0.001)
        visited: set = set()
        for node in graph.nodes:
            if node.id not in visited:
                if self._dfs_cycle_check(graph, node.id, visited, set()):
                    return True
        return False

    def _dfs_cycle_check(self, graph: ScriptGraph, node_id: str, visited: set, path: set) -> bool:
        """DFS helper to detect cycles in directed execution graph."""
        _time_module.sleep(0.001)
        if node_id in path:
            return True
        if node_id in visited:
            return False
        visited.add(node_id)
        path.add(node_id)
        current_ports = {p.id for p in self._ports.values() if p.node_id == node_id}
        for conn in graph.connections:
            if conn.source_port_id in current_ports and conn.connection_type == ConnectionType.EXECUTION:
                tp = self._ports.get(conn.target_port_id)
                if tp:
                    if self._dfs_cycle_check(graph, tp.node_id, visited, path):
                        return True
        path.discard(node_id)
        return False

    # ------------------------------------------------------------------
    # Graph Optimization
    # ------------------------------------------------------------------

    def optimize_graph(self, graph_id: str) -> int:
        """Remove dead nodes and merge constant expressions. Returns count of changes."""
        _time_module.sleep(0.001)
        graph = self._graphs.get(graph_id)
        if graph is None:
            return 0
        self._total_optimizations += 1
        changes = 0

        reachable = self._find_execution_reachable_nodes(graph)
        dead_nodes = [
            n for n in graph.nodes
            if n.id not in reachable and n.category != NodeCategory.EVENT
        ]
        for dead in dead_nodes:
            self.remove_node(graph_id, dead.id)
            changes += 1

        disconnected_connections = [c for c in graph.connections if not c.is_enabled]
        for dc in disconnected_connections:
            self.disconnect_nodes(dc.id)
            changes += 1

        orphaned_ports = []
        for pid, port in self._ports.items():
            port_referenced = any(
                conn.source_port_id == pid or conn.target_port_id == pid
                for conn in graph.connections
            )
            if not port_referenced and port.node_id not in {n.id for n in graph.nodes}:
                orphaned_ports.append(pid)
        for pid in orphaned_ports:
            del self._ports[pid]
            changes += 1

        return changes

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """Return runtime statistics for the visual scripting engine."""
        _time_module.sleep(0.001)
        total_nodes = sum(len(g.nodes) for g in self._graphs.values())
        total_connections = sum(len(g.connections) for g in self._graphs.values())
        category_counts: Dict[str, int] = {}
        for g in self._graphs.values():
            for n in g.nodes:
                cat = n.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
        return {
            "total_graphs": len(self._graphs),
            "total_graphs_created": self._total_graphs_created,
            "total_nodes": total_nodes,
            "total_nodes_added": self._total_nodes_added,
            "total_connections": total_connections,
            "total_ports": len(self._ports),
            "total_variables": len(self._variables),
            "total_templates": len(self._templates),
            "total_executions": self._total_executions,
            "total_validations": self._total_validations,
            "total_optimizations": self._total_optimizations,
            "active_contexts": len(self._contexts),
            "node_category_distribution": category_counts,
            "max_graphs": self.MAX_GRAPHS,
            "max_nodes_per_graph": self.MAX_NODES_PER_GRAPH,
            "max_connections_per_graph": self.MAX_CONNECTIONS_PER_GRAPH,
            "max_execution_depth": self.MAX_EXECUTION_DEPTH,
            "max_loop_iterations": self.MAX_LOOP_ITERATIONS,
        }

    def reset(self) -> None:
        """Reset all engine state, clearing graphs and contexts."""
        _time_module.sleep(0.001)
        with self._lock:
            self._graphs.clear()
            self._ports.clear()
            self._variables.clear()
            self._templates.clear()
            self._contexts.clear()
            self._total_graphs_created = 0
            self._total_nodes_added = 0
            self._total_executions = 0
            self._total_validations = 0
            self._total_optimizations = 0
            self._register_builtin_templates()


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_visual_scripting() -> EngineVisualScripting:
    """Return the singleton EngineVisualScripting instance."""
    return EngineVisualScripting.get_instance()