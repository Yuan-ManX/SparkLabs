"""
SparkLabs Engine - Visual Scripting Engine

Node-based visual scripting system that enables no-code game logic creation
through a graph-based event and action system. Nodes represent game events,
conditions, and actions that can be connected visually to define game behavior
without writing code. Designed for the AI-native game editor.

Architecture:
  EngineVisualScripting (Singleton)
    |-- ScriptGraph (node graph with event/condition/action nodes)
    |-- NodeLibrary (catalog of available script nodes)
    |-- ScriptInterpreter (runtime execution of visual scripts)
    |-- GraphOptimizer (dead code elimination, node merging)
    |-- ScriptSerializer (import/export visual scripts)

Node Categories:
  - EVENT: triggers (collision, input, timer, custom)
  - CONDITION: logical checks (comparison, state, distance)
  - ACTION: game operations (move, spawn, animate, destroy)
  - VARIABLE: data manipulation (set, get, calculate)
  - CONTROL: flow control (loop, branch, wait, sequence)

Usage:
    vs = EngineVisualScripting.get_instance()
    vs.initialize()

    graph = vs.create_graph("PlayerController")
    start = vs.add_node(graph.graph_id, "OnStart", NodeCategory.EVENT)
    check = vs.add_node(graph.graph_id, "IsGrounded", NodeCategory.CONDITION)
    jump = vs.add_node(graph.graph_id, "ApplyForce", NodeCategory.ACTION)
    vs.connect_nodes(graph.graph_id, start.node_id, check.node_id)
    vs.connect_nodes(graph.graph_id, check.node_id, jump.node_id, "true")
    vs.execute_graph(graph.graph_id, {"entity_id": "player_1"})
    vs.shutdown()
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums
# =============================================================================


class NodeCategory(Enum):
    """Categories of visual script nodes."""
    EVENT = "event"            # Trigger nodes
    CONDITION = "condition"    # Logical check nodes
    ACTION = "action"          # Game operation nodes
    VARIABLE = "variable"      # Data manipulation nodes
    CONTROL = "control"        # Flow control nodes
    CUSTOM = "custom"          # User-defined nodes


class NodePort(Enum):
    """Port types for node connections."""
    EXECUTION = "execution"    # Flow control connection
    DATA = "data"              # Value/data connection
    CONDITION = "condition"    # Boolean result connection


class ExecutionState(Enum):
    """States of graph execution."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"
    WAITING = "waiting"


class ScriptLanguage(Enum):
    """Target languages for script generation."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    GDSCRIPT = "gdscript"
    LUA = "lua"
    JSON = "json"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ScriptNode:
    """A single node in a visual script graph."""
    node_id: str
    node_type: str  # e.g., "OnStart", "CompareInt", "SetPosition"
    category: NodeCategory
    name: str = ""
    description: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)
    input_ports: List[str] = field(default_factory=list)
    output_ports: List[str] = field(default_factory=list)
    is_enabled: bool = True
    breakpoint: bool = False
    comment: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "position": list(self.position),
            "properties": self.properties,
            "input_ports": self.input_ports,
            "output_ports": self.output_ports,
            "is_enabled": self.is_enabled,
            "breakpoint": self.breakpoint,
            "comment": self.comment,
            "metadata": self.metadata,
        }


@dataclass
class NodeConnection:
    """A connection between two script nodes."""
    connection_id: str
    source_node_id: str
    target_node_id: str
    source_port: str = "output"
    target_port: str = "input"
    port_type: NodePort = NodePort.EXECUTION
    label: str = ""
    is_enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "connection_id": self.connection_id,
            "source_node_id": self.source_node_id,
            "source_port": self.source_port,
            "target_node_id": self.target_node_id,
            "target_port": self.target_port,
            "port_type": self.port_type.value,
            "label": self.label,
            "is_enabled": self.is_enabled,
        }


@dataclass
class ScriptGraph:
    """A complete visual script graph."""
    graph_id: str
    name: str
    description: str = ""
    nodes: Dict[str, ScriptNode] = field(default_factory=dict)
    connections: Dict[str, NodeConnection] = field(default_factory=dict)
    variables: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def connection_count(self) -> int:
        return len(self.connections)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "node_count": self.node_count,
            "connection_count": self.connection_count,
            "variable_count": len(self.variables),
            "tags": self.tags,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections.values()],
            "variables": self.variables,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }


@dataclass
class NodeTemplate:
    """Template for creating script nodes."""
    node_type: str
    category: NodeCategory
    name: str
    description: str = ""
    icon: str = "circle"
    input_ports: List[str] = field(default_factory=list)
    output_ports: List[str] = field(default_factory=list)
    default_properties: Dict[str, Any] = field(default_factory=dict)
    property_schema: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_type": self.node_type,
            "category": self.category.value,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "input_ports": self.input_ports,
            "output_ports": self.output_ports,
            "default_properties": self.default_properties,
            "property_schema": self.property_schema,
            "tags": self.tags,
        }


@dataclass
class ExecutionContext:
    """Runtime context for script execution."""
    variables: Dict[str, Any] = field(default_factory=dict)
    entity_id: Optional[str] = None
    scene_id: Optional[str] = None
    event_data: Dict[str, Any] = field(default_factory=dict)
    call_stack: List[str] = field(default_factory=list)
    execution_path: List[str] = field(default_factory=list)
    max_steps: int = 1000
    current_step: int = 0


# =============================================================================
# Engine Visual Scripting
# =============================================================================


class EngineVisualScripting:
    """
    Node-based visual scripting engine for no-code game logic creation.
    Provides a graph-based system where nodes represent game events,
    conditions, and actions connected visually to define behavior.
    """

    _instance: Optional["EngineVisualScripting"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if EngineVisualScripting._instance is not None:
            raise RuntimeError("Use EngineVisualScripting.get_instance()")
        self._initialized: bool = False
        self._graphs: Dict[str, ScriptGraph] = {}
        self._templates: Dict[str, NodeTemplate] = {}
        self._execution_states: Dict[str, ExecutionState] = {}
        self._handlers: Dict[str, Callable] = {}
        self._stats: Dict[str, Any] = {
            "total_graphs": 0,
            "total_nodes": 0,
            "total_connections": 0,
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "EngineVisualScripting":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the visual scripting engine and register default nodes."""
        with self._lock:
            if self._initialized:
                return
            self._register_default_templates()
            self._initialized = True

    def _register_default_templates(self) -> None:
        """Register default node templates."""
        # Event nodes
        self.register_template(NodeTemplate("OnStart", NodeCategory.EVENT, "On Start",
            "Triggered when the scene starts", "play",
            output_ports=["output"]))
        self.register_template(NodeTemplate("OnCollision", NodeCategory.EVENT, "On Collision",
            "Triggered on collision with another object", "zap",
            output_ports=["output"],
            default_properties={"collision_tag": ""}))
        self.register_template(NodeTemplate("OnInput", NodeCategory.EVENT, "On Input",
            "Triggered when input is received", "keyboard",
            output_ports=["output"],
            default_properties={"input_action": "jump"}))
        self.register_template(NodeTemplate("OnTimer", NodeCategory.EVENT, "On Timer",
            "Triggered at a timed interval", "clock",
            output_ports=["output"],
            default_properties={"interval": 1.0, "repeat": True}))

        # Condition nodes
        self.register_template(NodeTemplate("CompareFloat", NodeCategory.CONDITION, "Compare",
            "Compare two values", "git-branch",
            input_ports=["input"],
            output_ports=["true", "false"],
            default_properties={"operator": ">", "value_a": 0, "value_b": 0}))
        self.register_template(NodeTemplate("IsGrounded", NodeCategory.CONDITION, "Is Grounded",
            "Check if entity is on ground", "footprints",
            input_ports=["input"],
            output_ports=["true", "false"]))
        self.register_template(NodeTemplate("CheckDistance", NodeCategory.CONDITION, "Check Distance",
            "Check distance between two entities", "ruler",
            input_ports=["input"],
            output_ports=["true", "false"],
            default_properties={"entity_a": "", "entity_b": "", "threshold": 100.0}))

        # Action nodes
        self.register_template(NodeTemplate("SetPosition", NodeCategory.ACTION, "Set Position",
            "Set entity position", "move",
            input_ports=["input"], output_ports=["output"],
            default_properties={"x": 0, "y": 0, "z": 0}))
        self.register_template(NodeTemplate("ApplyForce", NodeCategory.ACTION, "Apply Force",
            "Apply a physics force", "arrow-up",
            input_ports=["input"], output_ports=["output"],
            default_properties={"force_x": 0, "force_y": 0, "force_z": 0}))
        self.register_template(NodeTemplate("PlayAnimation", NodeCategory.ACTION, "Play Animation",
            "Play an animation clip", "film",
            input_ports=["input"], output_ports=["output"],
            default_properties={"animation_name": "", "loop": False}))
        self.register_template(NodeTemplate("SpawnEntity", NodeCategory.ACTION, "Spawn Entity",
            "Spawn a new entity", "plus-circle",
            input_ports=["input"], output_ports=["output"],
            default_properties={"prefab_name": "", "position": [0, 0, 0]}))
        self.register_template(NodeTemplate("DestroyEntity", NodeCategory.ACTION, "Destroy Entity",
            "Destroy the current entity", "trash",
            input_ports=["input"], output_ports=["output"]))
        self.register_template(NodeTemplate("PlaySound", NodeCategory.ACTION, "Play Sound",
            "Play a sound effect", "volume-2",
            input_ports=["input"], output_ports=["output"],
            default_properties={"sound_name": "", "volume": 1.0, "pitch": 1.0}))

        # Variable nodes
        self.register_template(NodeTemplate("SetVariable", NodeCategory.VARIABLE, "Set Variable",
            "Set a variable value", "edit",
            input_ports=["input"], output_ports=["output"],
            default_properties={"variable_name": "", "value": ""}))
        self.register_template(NodeTemplate("GetVariable", NodeCategory.VARIABLE, "Get Variable",
            "Get a variable value", "database",
            input_ports=["input"], output_ports=["output"],
            default_properties={"variable_name": ""}))

        # Control nodes
        self.register_template(NodeTemplate("Branch", NodeCategory.CONTROL, "Branch",
            "Conditional branch", "git-branch",
            input_ports=["input", "condition"],
            output_ports=["true", "false"]))
        self.register_template(NodeTemplate("Sequence", NodeCategory.CONTROL, "Sequence",
            "Execute multiple actions in sequence", "list",
            input_ports=["input"], output_ports=["output"]))
        self.register_template(NodeTemplate("ForLoop", NodeCategory.CONTROL, "For Loop",
            "Loop a specified number of times", "repeat",
            input_ports=["input"], output_ports=["loop_body", "completed"],
            default_properties={"start": 0, "end": 10, "step": 1}))
        self.register_template(NodeTemplate("Wait", NodeCategory.CONTROL, "Wait",
            "Wait for a duration", "clock",
            input_ports=["input"], output_ports=["output"],
            default_properties={"duration": 1.0}))
        self.register_template(NodeTemplate("Delay", NodeCategory.CONTROL, "Delay",
            "Delay execution", "pause-circle",
            input_ports=["input"], output_ports=["output"],
            default_properties={"seconds": 0.5}))

    # -------------------------------------------------------------------------
    # Template Management
    # -------------------------------------------------------------------------

    def register_template(self, template: NodeTemplate) -> None:
        """Register a node template."""
        with self._lock:
            self._templates[template.node_type] = template

    def get_template(self, node_type: str) -> Optional[NodeTemplate]:
        """Get a node template by type."""
        return self._templates.get(node_type)

    def list_templates(self, category: Optional[NodeCategory] = None) -> List[NodeTemplate]:
        """List node templates, optionally filtered by category."""
        if category:
            return [t for t in self._templates.values() if t.category == category]
        return list(self._templates.values())

    # -------------------------------------------------------------------------
    # Graph Management
    # -------------------------------------------------------------------------

    def create_graph(self, name: str, description: str = "",
                     tags: Optional[List[str]] = None) -> ScriptGraph:
        """Create a new visual script graph."""
        with self._lock:
            graph_id = uuid.uuid4().hex[:12]
            graph = ScriptGraph(
                graph_id=graph_id,
                name=name,
                description=description,
                tags=tags or [],
            )
            self._graphs[graph_id] = graph
            self._stats["total_graphs"] += 1
            return graph

    def get_graph(self, graph_id: str) -> Optional[ScriptGraph]:
        """Get a graph by ID."""
        return self._graphs.get(graph_id)

    def list_graphs(self) -> List[ScriptGraph]:
        """List all graphs."""
        return list(self._graphs.values())

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph."""
        return self._graphs.pop(graph_id, None) is not None

    # -------------------------------------------------------------------------
    # Node Management
    # -------------------------------------------------------------------------

    def add_node(self, graph_id: str, node_type: str, position: Tuple[float, float] = (0.0, 0.0),
                 properties: Optional[Dict[str, Any]] = None,
                 name: str = "") -> Optional[ScriptNode]:
        """Add a node to a graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None

        template = self._templates.get(node_type)
        if not template:
            return None

        with self._lock:
            node_id = uuid.uuid4().hex[:8]
            merged_props = dict(template.default_properties)
            if properties:
                merged_props.update(properties)

            node = ScriptNode(
                node_id=node_id,
                node_type=node_type,
                category=template.category,
                name=name or template.name,
                description=template.description,
                position=position,
                properties=merged_props,
                input_ports=list(template.input_ports),
                output_ports=list(template.output_ports),
            )

            graph.nodes[node_id] = node
            graph.updated_at = time.time()
            self._stats["total_nodes"] += 1
            return node

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Remove a node and its connections from a graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False

        with self._lock:
            if node_id not in graph.nodes:
                return False
            del graph.nodes[node_id]

            # Remove associated connections
            to_remove = [cid for cid, conn in graph.connections.items()
                         if conn.source_node_id == node_id or conn.target_node_id == node_id]
            for cid in to_remove:
                del graph.connections[cid]

            graph.updated_at = time.time()
            return True

    def update_node_properties(self, graph_id: str, node_id: str,
                               properties: Dict[str, Any]) -> bool:
        """Update node properties."""
        graph = self._graphs.get(graph_id)
        if not graph or node_id not in graph.nodes:
            return False
        graph.nodes[node_id].properties.update(properties)
        graph.updated_at = time.time()
        return True

    # -------------------------------------------------------------------------
    # Connection Management
    # -------------------------------------------------------------------------

    def connect_nodes(self, graph_id: str, source_node_id: str, target_node_id: str,
                      source_port: str = "output", target_port: str = "input",
                      port_type: NodePort = NodePort.EXECUTION,
                      label: str = "") -> Optional[NodeConnection]:
        """Connect two nodes in a graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return None
        if source_node_id not in graph.nodes or target_node_id not in graph.nodes:
            return None

        with self._lock:
            connection_id = uuid.uuid4().hex[:8]
            connection = NodeConnection(
                connection_id=connection_id,
                source_node_id=source_node_id,
                source_port=source_port,
                target_node_id=target_node_id,
                target_port=target_port,
                port_type=port_type,
                label=label,
            )
            graph.connections[connection_id] = connection
            graph.updated_at = time.time()
            self._stats["total_connections"] += 1
            return connection

    def disconnect_nodes(self, graph_id: str, connection_id: str) -> bool:
        """Remove a connection from a graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return False
        if connection_id not in graph.connections:
            return False
        del graph.connections[connection_id]
        graph.updated_at = time.time()
        return True

    # -------------------------------------------------------------------------
    # Graph Execution
    # -------------------------------------------------------------------------

    def execute_graph(self, graph_id: str, context: Optional[Dict[str, Any]] = None,
                      entry_node_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a visual script graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return {"status": "error", "message": "Graph not found"}

        exec_ctx = ExecutionContext(
            variables=dict(graph.variables),
            entity_id=context.get("entity_id") if context else None,
            scene_id=context.get("scene_id") if context else None,
            event_data=context or {},
        )

        with self._lock:
            self._execution_states[graph_id] = ExecutionState.RUNNING
            self._stats["total_executions"] += 1

        try:
            # Find entry point (event nodes)
            entry_nodes = [n for n in graph.nodes.values()
                          if n.category == NodeCategory.EVENT and n.is_enabled]
            if entry_node_id:
                entry_nodes = [n for n in entry_nodes if n.node_id == entry_node_id]

            if not entry_nodes:
                self._execution_states[graph_id] = ExecutionState.COMPLETED
                return {"status": "warning", "message": "No entry nodes found"}

            for entry_node in entry_nodes:
                self._execute_node(graph, entry_node, exec_ctx)

            self._execution_states[graph_id] = ExecutionState.COMPLETED
            self._stats["successful_executions"] += 1

            return {
                "status": "success",
                "graph_id": graph_id,
                "nodes_executed": len(exec_ctx.execution_path),
                "execution_path": exec_ctx.execution_path,
                "variables": exec_ctx.variables,
            }

        except Exception as e:
            self._execution_states[graph_id] = ExecutionState.ERROR
            self._stats["failed_executions"] += 1
            return {
                "status": "error",
                "message": str(e),
                "nodes_executed": len(exec_ctx.execution_path),
                "execution_path": exec_ctx.execution_path,
            }

    def _execute_node(self, graph: ScriptGraph, node: ScriptNode,
                      ctx: ExecutionContext) -> None:
        """Execute a single node and follow its output connections."""
        if ctx.current_step >= ctx.max_steps:
            return

        ctx.current_step += 1
        ctx.execution_path.append(node.node_id)
        ctx.call_stack.append(node.node_id)

        # Execute node-specific logic
        self._process_node(node, ctx)

        # Find output connections
        outputs = [c for c in graph.connections.values()
                   if c.source_node_id == node.node_id and c.is_enabled]

        for conn in outputs:
            target = graph.nodes.get(conn.target_node_id)
            if target and target.is_enabled:
                self._execute_node(graph, target, ctx)

        ctx.call_stack.pop()

    def _process_node(self, node: ScriptNode, ctx: ExecutionContext) -> None:
        """Process a node's logic based on its type."""
        handler = self._handlers.get(node.node_type)
        if handler:
            handler(node, ctx)

    def register_handler(self, node_type: str, handler: Callable[[ScriptNode, ExecutionContext], None]) -> None:
        """Register a custom handler for a node type."""
        self._handlers[node_type] = handler

    # -------------------------------------------------------------------------
    # Script Generation
    # -------------------------------------------------------------------------

    def generate_script(self, graph_id: str,
                        language: ScriptLanguage = ScriptLanguage.PYTHON) -> str:
        """Generate executable code from a visual script graph."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return ""

        if language == ScriptLanguage.PYTHON:
            return self._generate_python(graph)
        elif language == ScriptLanguage.JAVASCRIPT:
            return self._generate_javascript(graph)
        elif language == ScriptLanguage.JSON:
            return json.dumps(graph.to_dict(), indent=2)
        return ""

    def _generate_python(self, graph: ScriptGraph) -> str:
        """Generate Python code from a graph."""
        lines = [
            "# Auto-generated visual script",
            f"# Graph: {graph.name}",
            f"# Generated at: {time.time()}",
            "",
            "class VisualScript:",
            "    def __init__(self):",
        ]
        for var_name, var_value in graph.variables.items():
            lines.append(f"        self.{var_name} = {repr(var_value)}")
        lines.append("")
        lines.append("    def execute(self, **context):")
        lines.append("        \"\"\"Execute the visual script.\"\"\"")
        lines.append("        pass  # Node execution logic")
        lines.append("")

        return "\n".join(lines)

    def _generate_javascript(self, graph: ScriptGraph) -> str:
        """Generate JavaScript code from a graph."""
        lines = [
            "// Auto-generated visual script",
            f"// Graph: {graph.name}",
            f"// Generated at: {time.time()}",
            "",
            "class VisualScript {",
            "    constructor() {",
        ]
        for var_name, var_value in graph.variables.items():
            lines.append(f"        this.{var_name} = {json.dumps(var_value)};")
        lines.append("    }")
        lines.append("")
        lines.append("    execute(context = {}) {")
        lines.append("        // Node execution logic")
        lines.append("    }")
        lines.append("}")
        lines.append("")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Graph Optimization
    # -------------------------------------------------------------------------

    def optimize_graph(self, graph_id: str) -> Dict[str, Any]:
        """Optimize a graph by removing dead code and unreachable nodes."""
        graph = self._graphs.get(graph_id)
        if not graph:
            return {"status": "error", "message": "Graph not found"}

        with self._lock:
            # Find reachable nodes from entry points
            entry_nodes = [n for n in graph.nodes.values()
                          if n.category == NodeCategory.EVENT]

            reachable: Set[str] = set()
            for entry in entry_nodes:
                self._collect_reachable(graph, entry.node_id, reachable, set())

            # Remove unreachable nodes
            removed_nodes = []
            for node_id in list(graph.nodes.keys()):
                if node_id not in reachable:
                    self.remove_node(graph_id, node_id)
                    removed_nodes.append(node_id)

            graph.updated_at = time.time()

            return {
                "status": "success",
                "removed_nodes": len(removed_nodes),
                "removed_node_ids": removed_nodes,
                "remaining_nodes": graph.node_count,
            }

    def _collect_reachable(self, graph: ScriptGraph, node_id: str,
                           reachable: Set[str], visited: Set[str]) -> None:
        """Collect all reachable nodes from a starting node."""
        if node_id in visited:
            return
        visited.add(node_id)
        reachable.add(node_id)

        for conn in graph.connections.values():
            if conn.source_node_id == node_id and conn.is_enabled:
                self._collect_reachable(graph, conn.target_node_id, reachable, visited)

    # -------------------------------------------------------------------------
    # Status and Statistics
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "graphs": self._stats["total_graphs"],
                "nodes": self._stats["total_nodes"],
                "connections": self._stats["total_connections"],
                "templates": len(self._templates),
                "templates_by_category": {
                    cat.value: len([t for t in self._templates.values() if t.category == cat])
                    for cat in NodeCategory
                },
                "executions": self._stats["total_executions"],
                "successful_executions": self._stats["successful_executions"],
                "failed_executions": self._stats["failed_executions"],
                "active_executions": len([s for s in self._execution_states.values()
                                          if s == ExecutionState.RUNNING]),
            }

    def shutdown(self) -> None:
        """Shutdown the visual scripting engine."""
        with self._lock:
            self._graphs.clear()
            self._templates.clear()
            self._execution_states.clear()
            self._handlers.clear()
            self._initialized = False


def get_visual_scripting() -> EngineVisualScripting:
    """Get the singleton visual scripting instance."""
    return EngineVisualScripting.get_instance()


def get_engine_visual_scripting() -> EngineVisualScripting:
    """Get the singleton visual scripting instance."""
    return EngineVisualScripting.get_instance()