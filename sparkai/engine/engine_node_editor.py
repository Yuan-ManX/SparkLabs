"""
SparkLabs Engine Node Editor

Provides a visual node-based editing system for game logic composition.
Nodes can be connected to form complex behaviors, event chains, and
gameplay systems without writing code. Supports real-time preview
and hot-reloading of node graphs.

Core architecture:
  - Node Graph: Directed graph of interconnected nodes
  - Node Types: Input, output, condition, action, variable, event
  - Connection System: Type-safe connections between node ports
  - Graph Execution: Topological execution of node graphs
  - Serialization: JSON-based graph persistence
  - Template System: Reusable node graph templates
"""

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NodeCategory(Enum):
    """Categories of nodes in the editor."""
    INPUT = "input"
    OUTPUT = "output"
    CONDITION = "condition"
    ACTION = "action"
    VARIABLE = "variable"
    EVENT = "event"
    MATH = "math"
    LOGIC = "logic"
    CONTROL = "control"
    CUSTOM = "custom"


class PortDirection(Enum):
    """Direction of a node port."""
    INPUT = "input"
    OUTPUT = "output"


class PortDataType(Enum):
    """Data types for node ports."""
    BOOLEAN = "boolean"
    INTEGER = "integer"
    FLOAT = "float"
    STRING = "string"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    COLOR = "color"
    OBJECT = "object"
    ARRAY = "array"
    TRIGGER = "trigger"
    ANY = "any"


class GraphExecutionState(Enum):
    """Execution states for a node graph."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class NodePort:
    """A port on a node for connecting to other nodes."""
    port_id: str
    name: str
    direction: PortDirection
    data_type: PortDataType
    default_value: Any = None
    description: str = ""
    is_required: bool = False


@dataclass
class NodeConnection:
    """A connection between two node ports."""
    connection_id: str
    source_node_id: str
    source_port_id: str
    target_node_id: str
    target_port_id: str
    is_active: bool = True
    created_at: float = field(default_factory=time.time)


@dataclass
class GraphNode:
    """A node in the visual editor graph."""
    node_id: str
    name: str
    category: NodeCategory
    node_type: str
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    ports: List[NodePort] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    description: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


@dataclass
class NodeGraph:
    """A complete node graph representing a game logic system."""
    graph_id: str
    name: str
    description: str
    nodes: Dict[str, GraphNode] = field(default_factory=dict)
    connections: Dict[str, NodeConnection] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    execution_state: GraphExecutionState = GraphExecutionState.IDLE
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class NodeTemplate:
    """A reusable node graph template."""
    template_id: str
    name: str
    description: str
    category: NodeCategory
    node_type: str
    default_ports: List[NodePort] = field(default_factory=list)
    default_properties: Dict[str, Any] = field(default_factory=dict)
    usage_count: int = 0
    created_at: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Node Editor Engine
# ---------------------------------------------------------------------------

class NodeEditorEngine:
    """Visual node-based game logic editor for the SparkLabs engine.

    Enables composing game behaviors, event chains, and gameplay
    systems through a visual node graph interface. Supports real-time
    execution preview and hot-reloading of node graphs.

    Usage:
        engine = get_node_editor_engine()
        graph = engine.create_graph("Player Movement", "Handles player input")
        node = engine.create_node(graph.graph_id, "Move Input", "input", NodeCategory.INPUT)
        engine.connect_nodes(graph.graph_id, source_node, source_port, target_node, target_port)
        result = engine.execute_graph(graph.graph_id)
    """

    _instance: Optional["NodeEditorEngine"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_NODES_PER_GRAPH: int = 500
    MAX_CONNECTIONS_PER_GRAPH: int = 2000
    MAX_TEMPLATES: int = 200

    def __new__(cls) -> "NodeEditorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "NodeEditorEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        time.sleep(0.001)
        if not hasattr(self, "_initialized"):
            self._graphs: Dict[str, NodeGraph] = {}
            self._templates: Dict[str, NodeTemplate] = {}
            self._total_graphs: int = 0
            self._total_nodes: int = 0
            self._total_connections: int = 0
            self._initialized = True
            self._register_default_templates()

    def _register_default_templates(self) -> None:
        """Register built-in node templates."""
        defaults = [
            ("On Start", "Triggered when the game starts", NodeCategory.EVENT, "event_start",
             [NodePort("out", "Trigger", PortDirection.OUTPUT, PortDataType.TRIGGER)]),
            ("On Update", "Triggered every frame", NodeCategory.EVENT, "event_update",
             [NodePort("out", "Trigger", PortDirection.OUTPUT, PortDataType.TRIGGER),
              NodePort("dt", "Delta Time", PortDirection.OUTPUT, PortDataType.FLOAT)]),
            ("Key Press", "Triggered when a key is pressed", NodeCategory.INPUT, "input_key",
             [NodePort("key", "Key", PortDirection.INPUT, PortDataType.STRING, default_value="space"),
              NodePort("out", "Trigger", PortDirection.OUTPUT, PortDataType.TRIGGER)]),
            ("Move Object", "Move an object to a position", NodeCategory.ACTION, "action_move",
             [NodePort("in", "Execute", PortDirection.INPUT, PortDataType.TRIGGER),
              NodePort("target", "Target", PortDirection.INPUT, PortDataType.OBJECT),
              NodePort("position", "Position", PortDirection.INPUT, PortDataType.VECTOR2),
              NodePort("out", "Next", PortDirection.OUTPUT, PortDataType.TRIGGER)]),
            ("Condition", "Branch based on a condition", NodeCategory.CONDITION, "condition_branch",
             [NodePort("in", "Execute", PortDirection.INPUT, PortDataType.TRIGGER),
              NodePort("condition", "Condition", PortDirection.INPUT, PortDataType.BOOLEAN),
              NodePort("true", "True", PortDirection.OUTPUT, PortDataType.TRIGGER),
              NodePort("false", "False", PortDirection.OUTPUT, PortDataType.TRIGGER)]),
        ]

        for name, desc, cat, ntype, ports in defaults:
            self._templates[ntype] = NodeTemplate(
                template_id=uuid.uuid4().hex,
                name=name,
                description=desc,
                category=cat,
                node_type=ntype,
                default_ports=ports,
            )

    # ------------------------------------------------------------------
    # Graph Management
    # ------------------------------------------------------------------

    def create_graph(
        self,
        name: str,
        description: str = "",
    ) -> NodeGraph:
        """Create a new node graph.

        Args:
            name: Graph name.
            description: Graph description.

        Returns:
            The created NodeGraph.
        """
        time.sleep(0.001)
        with self._lock:
            graph = NodeGraph(
                graph_id=uuid.uuid4().hex,
                name=name,
                description=description,
            )
            self._graphs[graph.graph_id] = graph
            self._total_graphs += 1
            return graph

    def get_graph(self, graph_id: str) -> Optional[NodeGraph]:
        """Get a graph by ID."""
        with self._lock:
            return self._graphs.get(graph_id)

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def create_node(
        self,
        graph_id: str,
        name: str,
        node_type: str,
        category: str,
        position: Optional[Dict[str, float]] = None,
        properties: Optional[Dict[str, Any]] = None,
    ) -> Optional[GraphNode]:
        """Create a node in a graph.

        Args:
            graph_id: Parent graph ID.
            name: Node display name.
            node_type: Type identifier for the node.
            category: Node category.
            position: Visual position in the editor.
            properties: Custom properties.

        Returns:
            The created GraphNode, or None if graph not found.
        """
        with self._lock:
            if graph_id not in self._graphs:
                return None

            graph = self._graphs[graph_id]
            if len(graph.nodes) >= self.MAX_NODES_PER_GRAPH:
                return None

            # Use template if available
            ports = []
            template = self._templates.get(node_type)
            if template:
                ports = [NodePort(
                    port_id=uuid.uuid4().hex,
                    name=p.name,
                    direction=p.direction,
                    data_type=p.data_type,
                    default_value=p.default_value,
                    description=p.description,
                    is_required=p.is_required,
                ) for p in template.default_ports]
                template.usage_count += 1

            node = GraphNode(
                node_id=uuid.uuid4().hex,
                name=name,
                category=NodeCategory(category),
                node_type=node_type,
                position=position or {"x": 0.0, "y": 0.0},
                ports=ports,
                properties=properties or {},
            )

            graph.nodes[node.node_id] = node
            graph.updated_at = time.time()
            self._total_nodes += 1
            return node

    def update_node(
        self,
        graph_id: str,
        node_id: str,
        updates: Dict[str, Any],
    ) -> Optional[GraphNode]:
        """Update node properties.

        Args:
            graph_id: Parent graph ID.
            node_id: Node to update.
            updates: Properties to update.

        Returns:
            The updated node, or None if not found.
        """
        with self._lock:
            if graph_id not in self._graphs:
                return None
            graph = self._graphs[graph_id]
            if node_id not in graph.nodes:
                return None

            node = graph.nodes[node_id]
            if "name" in updates:
                node.name = updates["name"]
            if "position" in updates:
                node.position.update(updates["position"])
            if "properties" in updates:
                node.properties.update(updates["properties"])
            if "is_enabled" in updates:
                node.is_enabled = updates["is_enabled"]

            graph.updated_at = time.time()
            return node

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Remove a node and its connections from a graph."""
        with self._lock:
            if graph_id not in self._graphs:
                return False
            graph = self._graphs[graph_id]
            if node_id not in graph.nodes:
                return False

            # Remove connections
            to_remove = [
                cid for cid, conn in graph.connections.items()
                if conn.source_node_id == node_id or conn.target_node_id == node_id
            ]
            for cid in to_remove:
                del graph.connections[cid]

            del graph.nodes[node_id]
            graph.updated_at = time.time()
            return True

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def connect_nodes(
        self,
        graph_id: str,
        source_node_id: str,
        source_port_id: str,
        target_node_id: str,
        target_port_id: str,
    ) -> Optional[NodeConnection]:
        """Create a connection between two node ports.

        Args:
            graph_id: Parent graph ID.
            source_node_id: Source node ID.
            source_port_id: Source port ID.
            target_node_id: Target node ID.
            target_port_id: Target port ID.

        Returns:
            The created NodeConnection, or None on failure.
        """
        with self._lock:
            if graph_id not in self._graphs:
                return None

            graph = self._graphs[graph_id]
            if len(graph.connections) >= self.MAX_CONNECTIONS_PER_GRAPH:
                return None

            # Validate nodes exist
            if source_node_id not in graph.nodes or target_node_id not in graph.nodes:
                return None

            source_node = graph.nodes[source_node_id]
            target_node = graph.nodes[target_node_id]

            # Validate ports exist
            source_port = next((p for p in source_node.ports if p.port_id == source_port_id), None)
            target_port = next((p for p in target_node.ports if p.port_id == target_port_id), None)

            if not source_port or not target_port:
                return None

            # Validate directions
            if source_port.direction != PortDirection.OUTPUT:
                return None
            if target_port.direction != PortDirection.INPUT:
                return None

            # Validate type compatibility
            if not self._types_compatible(source_port.data_type, target_port.data_type):
                return None

            connection = NodeConnection(
                connection_id=uuid.uuid4().hex,
                source_node_id=source_node_id,
                source_port_id=source_port_id,
                target_node_id=target_node_id,
                target_port_id=target_port_id,
            )

            graph.connections[connection.connection_id] = connection
            graph.updated_at = time.time()
            self._total_connections += 1
            return connection

    def _types_compatible(self, source: PortDataType, target: PortDataType) -> bool:
        """Check if two port data types are compatible."""
        if source == target:
            return True
        if source == PortDataType.ANY or target == PortDataType.ANY:
            return True
        # Numeric compatibility
        if source in (PortDataType.INTEGER, PortDataType.FLOAT) and target in (PortDataType.INTEGER, PortDataType.FLOAT):
            return True
        return False

    def disconnect_nodes(self, graph_id: str, connection_id: str) -> bool:
        """Remove a connection from a graph."""
        with self._lock:
            if graph_id not in self._graphs:
                return False
            graph = self._graphs[graph_id]
            if connection_id not in graph.connections:
                return False

            del graph.connections[connection_id]
            graph.updated_at = time.time()
            return True

    # ------------------------------------------------------------------
    # Graph Execution
    # ------------------------------------------------------------------

    def execute_graph(
        self,
        graph_id: str,
        inputs: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute a node graph with given inputs.

        Performs topological execution of the node graph, processing
        each node in order based on connections.

        Args:
            graph_id: Graph to execute.
            inputs: Input values for input nodes.

        Returns:
            Execution results with node outputs.
        """
        with self._lock:
            if graph_id not in self._graphs:
                return {"error": "Graph not found", "success": False}

            graph = self._graphs[graph_id]
            graph.execution_state = GraphExecutionState.RUNNING

            try:
                # Topological sort
                execution_order = self._topological_sort(graph)
                node_outputs: Dict[str, Any] = {}
                node_outputs.update(inputs or {})

                for node_id in execution_order:
                    node = graph.nodes[node_id]
                    if not node.is_enabled:
                        continue

                    # Execute node
                    result = self._execute_node(node, node_outputs, graph)
                    if result is not None:
                        node_outputs[node_id] = result

                graph.execution_state = GraphExecutionState.COMPLETED
                return {
                    "success": True,
                    "outputs": node_outputs,
                    "nodes_executed": len(execution_order),
                }
            except Exception as e:
                graph.execution_state = GraphExecutionState.ERROR
                return {"error": str(e), "success": False}

    def _topological_sort(self, graph: NodeGraph) -> List[str]:
        """Perform topological sort of nodes based on connections."""
        in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        adjacency: Dict[str, List[str]] = {nid: [] for nid in graph.nodes}

        for conn in graph.connections.values():
            if conn.is_active:
                adjacency.setdefault(conn.source_node_id, []).append(conn.target_node_id)
                in_degree[conn.target_node_id] = in_degree.get(conn.target_node_id, 0) + 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result = []

        while queue:
            current = queue.pop(0)
            result.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Add remaining nodes without connections
        for nid in graph.nodes:
            if nid not in result:
                result.append(nid)

        return result

    def _execute_node(
        self,
        node: GraphNode,
        inputs: Dict[str, Any],
        graph: NodeGraph,
    ) -> Any:
        """Execute a single node."""
        node_type = node.node_type

        handlers = {
            "event_start": lambda: True,
            "event_update": lambda: inputs.get("delta_time", 0.016),
            "input_key": lambda: inputs.get("key_pressed", False),
            "action_move": lambda: {
                "position": inputs.get("position", {"x": 0, "y": 0}),
                "target": node.properties.get("target", ""),
            },
            "condition_branch": lambda: inputs.get("condition", False),
        }

        handler = handlers.get(node_type, lambda: node.properties)
        return handler()

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def serialize_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Serialize a graph to JSON-compatible format."""
        with self._lock:
            if graph_id not in self._graphs:
                return None

            graph = self._graphs[graph_id]
            return {
                "graph_id": graph.graph_id,
                "name": graph.name,
                "description": graph.description,
                "version": graph.version,
                "nodes": {
                    nid: {
                        "node_id": n.node_id,
                        "name": n.name,
                        "category": n.category.value,
                        "node_type": n.node_type,
                        "position": n.position,
                        "ports": [
                            {
                                "port_id": p.port_id,
                                "name": p.name,
                                "direction": p.direction.value,
                                "data_type": p.data_type.value,
                                "default_value": p.default_value,
                            }
                            for p in n.ports
                        ],
                        "properties": n.properties,
                        "is_enabled": n.is_enabled,
                    }
                    for nid, n in graph.nodes.items()
                },
                "connections": {
                    cid: {
                        "connection_id": c.connection_id,
                        "source_node_id": c.source_node_id,
                        "source_port_id": c.source_port_id,
                        "target_node_id": c.target_node_id,
                        "target_port_id": c.target_port_id,
                    }
                    for cid, c in graph.connections.items()
                },
                "variables": graph.variables,
                "created_at": graph.created_at,
                "updated_at": graph.updated_at,
            }

    def deserialize_graph(self, data: Dict[str, Any]) -> NodeGraph:
        """Deserialize a graph from JSON data."""
        with self._lock:
            graph = NodeGraph(
                graph_id=data.get("graph_id", uuid.uuid4().hex),
                name=data.get("name", "Imported Graph"),
                description=data.get("description", ""),
                version=data.get("version", 1),
                variables=data.get("variables", {}),
            )

            for nid, ndata in data.get("nodes", {}).items():
                ports = [
                    NodePort(
                        port_id=p.get("port_id", uuid.uuid4().hex),
                        name=p.get("name", ""),
                        direction=PortDirection(p.get("direction", "input")),
                        data_type=PortDataType(p.get("data_type", "any")),
                        default_value=p.get("default_value"),
                    )
                    for p in ndata.get("ports", [])
                ]
                graph.nodes[nid] = GraphNode(
                    node_id=ndata.get("node_id", nid),
                    name=ndata.get("name", "Node"),
                    category=NodeCategory(ndata.get("category", "custom")),
                    node_type=ndata.get("node_type", "custom"),
                    position=ndata.get("position", {"x": 0.0, "y": 0.0}),
                    ports=ports,
                    properties=ndata.get("properties", {}),
                    is_enabled=ndata.get("is_enabled", True),
                )

            for cid, cdata in data.get("connections", {}).items():
                graph.connections[cid] = NodeConnection(
                    connection_id=cdata.get("connection_id", cid),
                    source_node_id=cdata.get("source_node_id", ""),
                    source_port_id=cdata.get("source_port_id", ""),
                    target_node_id=cdata.get("target_node_id", ""),
                    target_port_id=cdata.get("target_port_id", ""),
                )

            self._graphs[graph.graph_id] = graph
            return graph

    # ------------------------------------------------------------------
    # Template System
    # ------------------------------------------------------------------

    def register_template(
        self,
        name: str,
        description: str,
        category: str,
        node_type: str,
        ports: List[Dict[str, Any]],
        default_properties: Optional[Dict[str, Any]] = None,
    ) -> NodeTemplate:
        """Register a custom node template."""
        time.sleep(0.001)
        with self._lock:
            template = NodeTemplate(
                template_id=uuid.uuid4().hex,
                name=name,
                description=description,
                category=NodeCategory(category),
                node_type=node_type,
                default_ports=[
                    NodePort(
                        port_id=uuid.uuid4().hex,
                        name=p.get("name", ""),
                        direction=PortDirection(p.get("direction", "input")),
                        data_type=PortDataType(p.get("data_type", "any")),
                        default_value=p.get("default_value"),
                        description=p.get("description", ""),
                        is_required=p.get("is_required", False),
                    )
                    for p in ports
                ],
                default_properties=default_properties or {},
            )
            self._templates[node_type] = template
            return template

    def get_templates(self, category: Optional[str] = None) -> List[NodeTemplate]:
        """Get node templates, optionally filtered by category."""
        with self._lock:
            templates = list(self._templates.values())
            if category:
                cat_enum = NodeCategory(category)
                templates = [t for t in templates if t.category == cat_enum]
            return templates

    # ------------------------------------------------------------------
    # Query API
    # ------------------------------------------------------------------

    def get_editor_stats(self) -> Dict[str, Any]:
        """Get comprehensive editor statistics."""
        with self._lock:
            return {
                "total_graphs": self._total_graphs,
                "total_nodes": self._total_nodes,
                "total_connections": self._total_connections,
                "templates": len(self._templates),
                "stored_graphs": len(self._graphs),
            }

    def get_graph_summary(self, graph_id: str) -> Optional[Dict[str, Any]]:
        """Get a summary of a graph."""
        with self._lock:
            if graph_id not in self._graphs:
                return None
            graph = self._graphs[graph_id]
            return {
                "graph_id": graph.graph_id,
                "name": graph.name,
                "description": graph.description,
                "node_count": len(graph.nodes),
                "connection_count": len(graph.connections),
                "execution_state": graph.execution_state.value,
                "version": graph.version,
                "created_at": graph.created_at,
                "updated_at": graph.updated_at,
            }

    def get_stats(self) -> Dict[str, Any]:
        """Alias for get_editor_stats to maintain API consistency."""
        return self.get_editor_stats()

    def list_graphs(self) -> List[Dict[str, Any]]:
        """List all node graphs."""
        with self._lock:
            result: List[Dict[str, Any]] = []
            for graph in self._graphs.values():
                result.append({
                    "graph_id": graph.graph_id,
                    "name": graph.name,
                    "description": graph.description,
                    "node_count": len(graph.nodes),
                    "connection_count": len(graph.connections),
                    "created_at": graph.created_at,
                });
            return result


# ---------------------------------------------------------------------------
# Singleton Accessor
# ---------------------------------------------------------------------------

def get_node_editor_engine() -> NodeEditorEngine:
    """Get the singleton NodeEditorEngine instance."""
    return NodeEditorEngine.get_instance()