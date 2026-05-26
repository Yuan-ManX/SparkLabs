"""
SparkLabs Engine - Visual Script Runtime

Node-graph based visual programming runtime that transpiles node graphs
into executable game code. Logic is represented as typed node trees and
transpiled to target languages rather than interpreted at runtime.

Architecture:
  VisualScriptRuntime
    |-- ScriptGraph (node graph container with connections and validation)
    |-- ScriptNode (typed node with parameters, children, position)
    |-- NodeParameter (typed parameter with default and description)
    |-- NodeConnection (directed edge between node ports)
    |-- ValidationIssue (structural and semantic graph problems)
"""

from __future__ import annotations

import json
import math
import random
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class NodeType(Enum):
    EVENT = "event"
    CONDITION = "condition"
    ACTION = "action"
    EXPRESSION = "expression"
    LOOP = "loop"
    BRANCH = "branch"
    SUB_GRAPH = "sub_graph"
    VARIABLE = "variable"
    COMMENT = "comment"
    TRIGGER = "trigger"


class ParameterType(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    OBJECT_REF = "object_ref"
    BEHAVIOR_REF = "behavior_ref"
    SCENE_REF = "scene_ref"
    VARIABLE_REF = "variable_ref"
    EXPRESSION = "expression"
    COLOR = "color"
    VECTOR2 = "vector2"
    ENUM = "enum"


class TargetLanguage(Enum):
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    GDSCRIPT = "gdscript"
    LUA = "lua"
    CSHARP = "csharp"


class ValidationResult(Enum):
    VALID = "valid"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class NodeParameter:
    """Typed parameter definition with default value and constraints."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    param_type: ParameterType = ParameterType.STRING
    value: Any = ""
    default_value: Any = ""
    required: bool = False
    description: str = ""
    enum_values: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "param_type": self.param_type.value,
            "value": self.value,
            "default_value": self.default_value,
            "required": self.required,
            "description": self.description,
            "enum_values": list(self.enum_values),
        }


@dataclass
class ScriptNode:
    """Typed node in a visual script graph with parameters and child nodes."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: NodeType = NodeType.ACTION
    name: str = ""
    params: List[NodeParameter] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    position_x: float = 0.0
    position_y: float = 0.0
    target_language: TargetLanguage = TargetLanguage.PYTHON
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "params": [p.to_dict() for p in self.params],
            "children": list(self.children),
            "position_x": self.position_x,
            "position_y": self.position_y,
            "target_language": self.target_language.value,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }


@dataclass
class NodeConnection:
    """Directed edge between two node ports with optional condition."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_node_id: str = ""
    source_port: str = "output"
    target_node_id: str = ""
    target_port: str = "input"
    condition: str = ""
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "source_port": self.source_port,
            "target_node_id": self.target_node_id,
            "target_port": self.target_port,
            "condition": self.condition,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class ValidationIssue:
    """Structural or semantic problem detected during graph validation."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    severity: ValidationResult = ValidationResult.WARNING
    node_id: str = ""
    message: str = ""
    suggestion: str = ""
    line_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "node_id": self.node_id,
            "message": self.message,
            "suggestion": self.suggestion,
            "line_number": self.line_number,
        }


@dataclass
class ScriptGraph:
    """Node graph container with nodes, connections, and transpiled output."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    root_node_id: str = ""
    nodes: Dict[str, ScriptNode] = field(default_factory=dict)
    connections: Dict[str, NodeConnection] = field(default_factory=dict)
    target_language: TargetLanguage = TargetLanguage.PYTHON
    transpiled_code: str = ""
    validation_errors: List[ValidationIssue] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "root_node_id": self.root_node_id,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections.values()],
            "target_language": self.target_language.value,
            "transpiled_code": self.transpiled_code,
            "validation_errors": [v.to_dict() for v in self.validation_errors],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Visual Script Runtime (Singleton)
# ---------------------------------------------------------------------------


class VisualScriptRuntime:
    """Node-graph based visual programming transpiler and execution engine."""

    _instance: Optional["VisualScriptRuntime"] = None
    _lock = threading.RLock()

    MAX_GRAPHS = 512
    MAX_NODES_PER_GRAPH = 1024
    MAX_CONNECTIONS_PER_GRAPH = 4096
    MAX_NESTING_DEPTH = 64
    DEFAULT_INDENT = "    "

    def __init__(self) -> None:
        self._graphs: Dict[str, ScriptGraph] = {}
        self._execution_contexts: Dict[str, Dict[str, Any]] = {}
        self._total_graphs_created: int = 0
        self._total_nodes_added: int = 0
        self._total_connections_made: int = 0
        self._total_transpilations: int = 0
        self._total_executions: int = 0
        self._total_validations: int = 0
        self._total_optimizations: int = 0

    @classmethod
    def get_instance(cls) -> "VisualScriptRuntime":
        """Thread-safe singleton accessor."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Graph Lifecycle
    # ------------------------------------------------------------------

    def create_graph(
        self,
        name: str,
        description: str = "",
        target_language: TargetLanguage = TargetLanguage.PYTHON,
    ) -> ScriptGraph:
        """Create a new node graph."""
        if len(self._graphs) >= self.MAX_GRAPHS:
            raise RuntimeError(f"Graph limit reached ({self.MAX_GRAPHS})")
        graph = ScriptGraph(
            name=name,
            description=description,
            target_language=target_language,
        )
        self._graphs[graph.id] = graph
        self._total_graphs_created += 1
        return graph

    def get_graph(self, graph_id: str) -> Optional[ScriptGraph]:
        """Retrieve a graph by id."""
        return self._graphs.get(graph_id)

    def delete_graph(self, graph_id: str) -> bool:
        """Delete a graph and all its contents."""
        if graph_id not in self._graphs:
            return False
        self._execution_contexts.pop(graph_id, None)
        del self._graphs[graph_id]
        return True

    def list_graphs(self) -> List[ScriptGraph]:
        """Return all registered graphs."""
        return list(self._graphs.values())

    # ------------------------------------------------------------------
    # Node Management
    # ------------------------------------------------------------------

    def add_node(
        self,
        graph_id: str,
        node_type: NodeType,
        name: str = "",
        params: Optional[List[NodeParameter]] = None,
        position_x: float = 0.0,
        position_y: float = 0.0,
    ) -> Optional[ScriptNode]:
        """Add a node to a graph."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        if len(graph.nodes) >= self.MAX_NODES_PER_GRAPH:
            raise RuntimeError(
                f"Node limit reached for graph ({self.MAX_NODES_PER_GRAPH})"
            )
        node = ScriptNode(
            node_type=node_type,
            name=name or self._default_name_for_type(node_type),
            params=list(params) if params else [],
            position_x=position_x,
            position_y=position_y,
            target_language=graph.target_language,
        )
        graph.nodes[node.id] = node
        graph.updated_at = _time_module.time()
        if not graph.root_node_id and node_type == NodeType.EVENT:
            graph.root_node_id = node.id
        self._total_nodes_added += 1
        return node

    def get_node(self, graph_id: str, node_id: str) -> Optional[ScriptNode]:
        """Retrieve a node from a graph."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        return graph.nodes.get(node_id)

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Safely remove a node and its connections from a graph."""
        graph = self._graphs.get(graph_id)
        if graph is None or node_id not in graph.nodes:
            return False
        connection_ids_to_remove = [
            cid for cid, conn in graph.connections.items()
            if conn.source_node_id == node_id or conn.target_node_id == node_id
        ]
        for cid in connection_ids_to_remove:
            del graph.connections[cid]
        if graph.root_node_id == node_id:
            graph.root_node_id = ""
        del graph.nodes[node_id]
        graph.updated_at = _time_module.time()
        return True

    def update_node(
        self,
        graph_id: str,
        node_id: str,
        name: Optional[str] = None,
        params: Optional[List[NodeParameter]] = None,
        position_x: Optional[float] = None,
        position_y: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Update properties of an existing node."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return False
        node = graph.nodes.get(node_id)
        if node is None:
            return False
        if name is not None:
            node.name = name
        if params is not None:
            node.params = list(params)
        if position_x is not None:
            node.position_x = position_x
        if position_y is not None:
            node.position_y = position_y
        if metadata is not None:
            node.metadata = dict(metadata)
        graph.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def connect_nodes(
        self,
        graph_id: str,
        source_node_id: str,
        source_port: str = "output",
        target_node_id: str,
        target_port: str = "input",
        condition: str = "",
    ) -> Optional[NodeConnection]:
        """Create a connection between two nodes."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        if source_node_id not in graph.nodes or target_node_id not in graph.nodes:
            return None
        if len(graph.connections) >= self.MAX_CONNECTIONS_PER_GRAPH:
            raise RuntimeError(
                f"Connection limit reached ({self.MAX_CONNECTIONS_PER_GRAPH})"
            )
        connection = NodeConnection(
            source_node_id=source_node_id,
            source_port=source_port,
            target_node_id=target_node_id,
            target_port=target_port,
            condition=condition,
        )
        graph.connections[connection.id] = connection
        graph.updated_at = _time_module.time()
        self._total_connections_made += 1
        return connection

    def disconnect_nodes(self, graph_id: str, connection_id: str) -> bool:
        """Remove a connection from a graph."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return False
        if connection_id not in graph.connections:
            return False
        del graph.connections[connection_id]
        graph.updated_at = _time_module.time()
        return True

    def get_connections_for_node(
        self, graph_id: str, node_id: str
    ) -> Tuple[List[NodeConnection], List[NodeConnection]]:
        """Get incoming and outgoing connections for a node."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return [], []
        incoming = [
            c for c in graph.connections.values()
            if c.target_node_id == node_id and c.enabled
        ]
        outgoing = [
            c for c in graph.connections.values()
            if c.source_node_id == node_id and c.enabled
        ]
        outgoing.sort(key=lambda c: c.priority, reverse=True)
        return incoming, outgoing

    # ------------------------------------------------------------------
    # Graph Validation
    # ------------------------------------------------------------------

    def validate_graph(self, graph_id: str) -> List[ValidationIssue]:
        """Check graph for structural and semantic issues."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return []
        graph.validation_errors = []
        self._total_validations += 1

        if not graph.nodes:
            graph.validation_errors.append(ValidationIssue(
                severity=ValidationResult.ERROR,
                message="Graph has no nodes",
                suggestion="Add at least one node to the graph",
            ))
            return graph.validation_errors

        has_event = any(
            n.node_type == NodeType.EVENT for n in graph.nodes.values()
        )
        if not has_event:
            graph.validation_errors.append(ValidationIssue(
                severity=ValidationResult.WARNING,
                message="Graph has no event node",
                suggestion="Add an event node as the graph entry point",
            ))

        visited: Set[str] = set()
        for node in graph.nodes.values():
            if self._node_has_cycle(graph, node.id, visited, set()):
                graph.validation_errors.append(ValidationIssue(
                    severity=ValidationResult.CRITICAL,
                    node_id=node.id,
                    message=f"Cycle detected involving node '{node.name}'",
                    suggestion="Break the cycle by removing one of the connections in the loop",
                ))

        for connection in graph.connections.values():
            if connection.source_node_id not in graph.nodes:
                graph.validation_errors.append(ValidationIssue(
                    severity=ValidationResult.ERROR,
                    node_id=connection.source_node_id,
                    message=f"Connection references missing source node",
                    suggestion="Remove or repair the broken connection",
                ))
            if connection.target_node_id not in graph.nodes:
                graph.validation_errors.append(ValidationIssue(
                    severity=ValidationResult.ERROR,
                    node_id=connection.target_node_id,
                    message=f"Connection references missing target node",
                    suggestion="Remove or repair the broken connection",
                ))

        for node in graph.nodes.values():
            if node.node_type == NodeType.LOOP:
                has_children = bool(node.children)
                has_outgoing = any(
                    c.source_node_id == node.id and c.enabled
                    for c in graph.connections.values()
                )
                if not has_children and not has_outgoing:
                    graph.validation_errors.append(ValidationIssue(
                        severity=ValidationResult.WARNING,
                        node_id=node.id,
                        message=f"Loop node '{node.name}' has no body",
                        suggestion="Connect a node to the loop body output",
                    ))

        for node in graph.nodes.values():
            for param in node.params:
                if param.required and param.value in (None, "", param.default_value):
                    if param.value == param.default_value:
                        graph.validation_errors.append(ValidationIssue(
                            severity=ValidationResult.WARNING,
                            node_id=node.id,
                            message=(
                                f"Required parameter '{param.name}' on node "
                                f"'{node.name}' has no value set"
                            ),
                            suggestion=f"Set a value for parameter '{param.name}'",
                        ))

        return graph.validation_errors

    def _node_has_cycle(
        self,
        graph: ScriptGraph,
        node_id: str,
        visited: Set[str],
        path: Set[str],
    ) -> bool:
        """Detect cycles in the node graph using DFS."""
        if node_id in path:
            return True
        if node_id in visited:
            return False
        visited.add(node_id)
        path.add(node_id)
        for conn in graph.connections.values():
            if conn.source_node_id == node_id and conn.enabled:
                if self._node_has_cycle(graph, conn.target_node_id, visited, path):
                    return True
        path.discard(node_id)
        return False

    # ------------------------------------------------------------------
    # Transpilation Engine
    # ------------------------------------------------------------------

    def transpile_graph(self, graph_id: str) -> str:
        """Convert node graph to target language code."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return ""
        self._total_transpilations += 1
        language = graph.target_language
        if language == TargetLanguage.PYTHON:
            code = self._transpile_python(graph)
        elif language == TargetLanguage.JAVASCRIPT:
            code = self._transpile_javascript(graph)
        elif language == TargetLanguage.GDSCRIPT:
            code = self._transpile_gdscript(graph)
        elif language == TargetLanguage.LUA:
            code = self._transpile_lua(graph)
        elif language == TargetLanguage.CSHARP:
            code = self._transpile_csharp(graph)
        else:
            code = self._transpile_python(graph)
        graph.transpiled_code = code
        graph.updated_at = _time_module.time()
        return code

    def _transpile_python(self, graph: ScriptGraph) -> str:
        """Transpile graph nodes to Python source code."""
        lines: List[str] = []
        lines.append("# Generated by SparkLabs Visual Script Runtime")
        lines.append("")
        var_declarations = self._collect_variable_nodes(graph)
        for var_name, var_value in var_declarations.items():
            lines.append(f"{var_name} = {self._format_python_value(var_value)}")
        if var_declarations:
            lines.append("")
        event_nodes = [
            n for n in graph.nodes.values()
            if n.node_type == NodeType.EVENT
        ]
        for event_node in event_nodes:
            lines.extend(self._transpile_node_python(graph, event_node, 0))
        if not event_nodes:
            lines.append("# No event entry point found")
        return "\n".join(lines)

    def _transpile_node_python(
        self,
        graph: ScriptGraph,
        node: ScriptNode,
        indent_level: int,
    ) -> List[str]:
        """Transpile a single node to Python code."""
        indent = self.DEFAULT_INDENT * indent_level
        lines: List[str] = []
        node_type = node.node_type

        if node_type == NodeType.EVENT:
            func_name = re.sub(r"[^a-zA-Z0-9_]", "_", node.name.lower()) or "on_event"
            func_name = f"on_{func_name}" if not func_name.startswith("on_") else func_name
            lines.append(f"def {func_name}(self, context):")
            lines.append(f'{indent}{self.DEFAULT_INDENT}"""Event: {node.name}"""')
            body_lines = self._transpile_children_python(graph, node, indent_level + 1)
            if body_lines:
                lines.extend(body_lines)
            else:
                lines.append(f"{indent}{self.DEFAULT_INDENT}pass")
            lines.append("")

        elif node_type == NodeType.CONDITION:
            condition_expr = self._get_param_value(node, "condition", "True")
            lines.append(f"{indent}if {condition_expr}:")
            lines.extend(self._transpile_children_python(graph, node, indent_level + 1))

        elif node_type == NodeType.ACTION:
            action_name = re.sub(r"[^a-zA-Z0-9_]", "_", node.name.lower())
            target = self._get_param_value(node, "target", "None")
            args = self._build_action_args_python(node)
            lines.append(f"{indent}{action_name}({args})")

        elif node_type == NodeType.LOOP:
            loop_type = self._get_param_value(node, "loop_type", "for")
            loop_var = self._get_param_value(node, "loop_var", "i")
            if loop_type == "for":
                start = self._get_param_value(node, "start", "0")
                end = self._get_param_value(node, "end", "10")
                lines.append(f"{indent}for {loop_var} in range({start}, {end}):")
            elif loop_type == "while":
                condition = self._get_param_value(node, "condition", "True")
                lines.append(f"{indent}while {condition}:")
            else:
                iterable = self._get_param_value(node, "iterable", "[]")
                lines.append(f"{indent}for {loop_var} in {iterable}:")
            lines.extend(self._transpile_children_python(graph, node, indent_level + 1))

        elif node_type == NodeType.BRANCH:
            branches = self._get_branch_definitions(node)
            if branches:
                first_condition, first_nodes = branches[0]
                lines.append(f"{indent}if {first_condition}:")
                for branch_node_id in first_nodes:
                    branch_node = graph.nodes.get(branch_node_id)
                    if branch_node:
                        lines.extend(
                            self._transpile_node_python(graph, branch_node, indent_level + 1)
                        )
                for condition, branch_nodes in branches[1:]:
                    if condition in ("else", "default", ""):
                        lines.append(f"{indent}else:")
                    else:
                        lines.append(f"{indent}elif {condition}:")
                    for branch_node_id in branch_nodes:
                        branch_node = graph.nodes.get(branch_node_id)
                        if branch_node:
                            lines.extend(
                                self._transpile_node_python(graph, branch_node, indent_level + 1)
                            )

        elif node_type == NodeType.EXPRESSION:
            expr = self._get_param_value(node, "expression", "None")
            assign_to = self._get_param_value(node, "assign_to", "")
            if assign_to:
                lines.append(f"{indent}{assign_to} = {expr}")
            else:
                lines.append(f"{indent}{expr}")

        elif node_type == NodeType.SUB_GRAPH:
            sub_name = self._get_param_value(node, "sub_graph_name", node.name)
            lines.append(f"{indent}# Sub-graph: {sub_name}")

        elif node_type == NodeType.TRIGGER:
            trigger_event = self._get_param_value(node, "event", "trigger")
            lines.append(f"{indent}self.emit('{trigger_event}', context)")

        elif node_type == NodeType.VARIABLE:
            var_name = self._get_param_value(node, "variable_name", "var")
            var_value = self._get_param_value(node, "value", "None")
            lines.append(f"{indent}{var_name} = {self._format_python_value(var_value)}")

        return lines

    def _transpile_children_python(
        self,
        graph: ScriptGraph,
        node: ScriptNode,
        indent_level: int,
    ) -> List[str]:
        """Transpile child nodes of a given node to Python."""
        lines: List[str] = []
        for child_id in node.children:
            child = graph.nodes.get(child_id)
            if child:
                lines.extend(self._transpile_node_python(graph, child, indent_level))
        _, outgoing = self.get_connections_for_node(graph.id, node.id)
        for conn in outgoing:
            target = graph.nodes.get(conn.target_node_id)
            if target:
                lines.extend(self._transpile_node_python(graph, target, indent_level))
        return lines

    def _transpile_javascript(self, graph: ScriptGraph) -> str:
        """Transpile graph nodes to JavaScript source code."""
        lines: List[str] = []
        lines.append("// Generated by SparkLabs Visual Script Runtime")
        lines.append("")
        var_declarations = self._collect_variable_nodes(graph)
        for var_name, var_value in var_declarations.items():
            lines.append(f"let {var_name} = {self._format_js_value(var_value)};")
        if var_declarations:
            lines.append("")
        event_nodes = [
            n for n in graph.nodes.values()
            if n.node_type == NodeType.EVENT
        ]
        for event_node in event_nodes:
            lines.extend(self._transpile_node_js(graph, event_node, 0))
        if not event_nodes:
            lines.append("// No event entry point found")
        return "\n".join(lines)

    def _transpile_node_js(
        self,
        graph: ScriptGraph,
        node: ScriptNode,
        indent_level: int,
    ) -> List[str]:
        """Transpile a single node to JavaScript code."""
        indent = self.DEFAULT_INDENT * indent_level
        lines: List[str] = []
        node_type = node.node_type

        if node_type == NodeType.EVENT:
            func_name = re.sub(r"[^a-zA-Z0-9_]", "_", node.name.lower()) or "onEvent"
            func_name = f"on{func_name[0].upper()}{func_name[1:]}" if func_name else "onEvent"
            lines.append(f"function {func_name}(context) {{")
            body_lines = self._transpile_children_js(graph, node, indent_level + 1)
            if body_lines:
                lines.extend(body_lines)
            else:
                lines.append(f"{indent}{self.DEFAULT_INDENT}// Event: {node.name}")
            lines.append(f"{indent}}}")
            lines.append("")

        elif node_type == NodeType.CONDITION:
            condition_expr = self._get_param_value(node, "condition", "true")
            lines.append(f"{indent}if ({condition_expr}) {{")
            lines.extend(self._transpile_children_js(graph, node, indent_level + 1))
            lines.append(f"{indent}}}")

        elif node_type == NodeType.ACTION:
            action_name = re.sub(r"[^a-zA-Z0-9_]", "_", node.name.lower())
            args = self._build_action_args_python(node)
            lines.append(f"{indent}{action_name}({args});")

        elif node_type == NodeType.LOOP:
            loop_type = self._get_param_value(node, "loop_type", "for")
            loop_var = self._get_param_value(node, "loop_var", "i")
            if loop_type == "for":
                start = self._get_param_value(node, "start", "0")
                end = self._get_param_value(node, "end", "10")
                lines.append(f"{indent}for (let {loop_var} = {start}; {loop_var} < {end}; {loop_var}++) {{")
            elif loop_type == "while":
                condition = self._get_param_value(node, "condition", "true")
                lines.append(f"{indent}while ({condition}) {{")
            else:
                iterable = self._get_param_value(node, "iterable", "[]")
                lines.append(f"{indent}for (let {loop_var} of {iterable}) {{")
            lines.extend(self._transpile_children_js(graph, node, indent_level + 1))
            lines.append(f"{indent}}}")

        elif node_type == NodeType.BRANCH:
            branches = self._get_branch_definitions(node)
            if branches:
                first_condition, first_nodes = branches[0]
                lines.append(f"{indent}if ({first_condition}) {{")
                for branch_node_id in first_nodes:
                    branch_node = graph.nodes.get(branch_node_id)
                    if branch_node:
                        lines.extend(self._transpile_node_js(graph, branch_node, indent_level + 1))
                lines.append(f"{indent}}}")
                for condition, branch_nodes in branches[1:]:
                    if condition in ("else", "default", ""):
                        lines.append(f"{indent} else {{")
                    else:
                        lines.append(f"{indent} else if ({condition}) {{")
                    for branch_node_id in branch_nodes:
                        branch_node = graph.nodes.get(branch_node_id)
                        if branch_node:
                            lines.extend(self._transpile_node_js(graph, branch_node, indent_level + 1))
                    lines.append(f"{indent}}}")

        elif node_type == NodeType.EXPRESSION:
            expr = self._get_param_value(node, "expression", "null")
            assign_to = self._get_param_value(node, "assign_to", "")
            if assign_to:
                lines.append(f"{indent}{assign_to} = {expr};")
            else:
                lines.append(f"{indent}{expr};")

        elif node_type == NodeType.TRIGGER:
            trigger_event = self._get_param_value(node, "event", "trigger")
            lines.append(f"{indent}this.emit('{trigger_event}', context);")

        elif node_type == NodeType.VARIABLE:
            var_name = self._get_param_value(node, "variable_name", "var")
            var_value = self._get_param_value(node, "value", "null")
            lines.append(f"{indent}let {var_name} = {self._format_js_value(var_value)};")

        return lines

    def _transpile_children_js(
        self,
        graph: ScriptGraph,
        node: ScriptNode,
        indent_level: int,
    ) -> List[str]:
        """Transpile child nodes of a given node to JavaScript."""
        lines: List[str] = []
        for child_id in node.children:
            child = graph.nodes.get(child_id)
            if child:
                lines.extend(self._transpile_node_js(graph, child, indent_level))
        _, outgoing = self.get_connections_for_node(graph.id, node.id)
        for conn in outgoing:
            target = graph.nodes.get(conn.target_node_id)
            if target:
                lines.extend(self._transpile_node_js(graph, target, indent_level))
        return lines

    def _transpile_gdscript(self, graph: ScriptGraph) -> str:
        """Transpile graph nodes to GDScript source code."""
        lines: List[str] = []
        lines.append("# Generated by SparkLabs Visual Script Runtime")
        lines.append("")
        event_nodes = [n for n in graph.nodes.values() if n.node_type == NodeType.EVENT]
        for event_node in event_nodes:
            func_name = re.sub(r"[^a-zA-Z0-9_]", "_", event_node.name.lower())
            func_name = f"_{func_name}" if func_name else "_on_event"
            lines.append(f"func {func_name}(context):")
            for param in event_node.params:
                lines.append(f"{self.DEFAULT_INDENT}var {param.name} = {self._format_gdscript_value(param.value)}")
            lines.append(f"{self.DEFAULT_INDENT}pass")
            lines.append("")
        if not event_nodes:
            lines.append("# No event entry point found")
        return "\n".join(lines)

    def _transpile_lua(self, graph: ScriptGraph) -> str:
        """Transpile graph nodes to Lua source code."""
        lines: List[str] = []
        lines.append("-- Generated by SparkLabs Visual Script Runtime")
        lines.append("")
        event_nodes = [n for n in graph.nodes.values() if n.node_type == NodeType.EVENT]
        for event_node in event_nodes:
            func_name = re.sub(r"[^a-zA-Z0-9_]", "_", event_node.name.lower())
            func_name = func_name or "on_event"
            lines.append(f"function {func_name}(context)")
            for param in event_node.params:
                lines.append(f"{self.DEFAULT_INDENT}local {param.name} = {self._format_lua_value(param.value)}")
            lines.append(f"{self.DEFAULT_INDENT}-- Event: {event_node.name}")
            lines.append("end")
            lines.append("")
        if not event_nodes:
            lines.append("-- No event entry point found")
        return "\n".join(lines)

    def _transpile_csharp(self, graph: ScriptGraph) -> str:
        """Transpile graph nodes to C# source code."""
        lines: List[str] = []
        lines.append("// Generated by SparkLabs Visual Script Runtime")
        lines.append("")
        event_nodes = [n for n in graph.nodes.values() if n.node_type == NodeType.EVENT]
        for event_node in event_nodes:
            class_name = re.sub(r"[^a-zA-Z0-9_]", "_", event_node.name) or "EventHandler"
            lines.append(f"public class {class_name}")
            lines.append("{")
            func_name = re.sub(r"[^a-zA-Z0-9_]", "_", event_node.name.lower())
            func_name = func_name or "OnEvent"
            lines.append(f"{self.DEFAULT_INDENT}public void {func_name}(object context)")
            lines.append(f"{self.DEFAULT_INDENT}{{")
            for param in event_node.params:
                lines.append(
                    f"{self.DEFAULT_INDENT}{self.DEFAULT_INDENT}var {param.name} = "
                    f"{self._format_csharp_value(param.value)};"
                )
            lines.append(f"{self.DEFAULT_INDENT}{self.DEFAULT_INDENT}// Event: {event_node.name}")
            lines.append(f"{self.DEFAULT_INDENT}}}")
            lines.append("}")
            lines.append("")
        if not event_nodes:
            lines.append("// No event entry point found")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Graph Execution
    # ------------------------------------------------------------------

    def execute_graph(
        self,
        graph_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Run the transpiled code in the given context."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return {"success": False, "error": "Graph not found"}
        self._total_executions += 1
        exec_context = dict(context) if context else {}
        self._execution_contexts[graph_id] = exec_context

        code = graph.transpiled_code or self.transpile_graph(graph_id)
        if not code:
            return {"success": False, "error": "No transpiled code available"}

        exec_globals: Dict[str, Any] = {
            "__builtins__": __builtins__,
            "math": math,
            "random": random,
            "json": json,
            "self": exec_context,
            "context": exec_context,
        }

        try:
            exec(code, exec_globals)
            return {"success": True, "context": exec_context}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_graph(self, graph_id: str, format: str = "json") -> str:
        """Export a graph as JSON, XML, or transpiled code string."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return ""
        if format == "json":
            return json.dumps(graph.to_dict(), indent=2, default=str)
        if format == "xml":
            return self._export_graph_xml(graph)
        if format == "code":
            return graph.transpiled_code or self.transpile_graph(graph_id)
        return json.dumps(graph.to_dict(), indent=2, default=str)

    def import_graph(
        self,
        data: str,
        format: str = "json",
    ) -> Optional[ScriptGraph]:
        """Import a graph from external format data."""
        if len(self._graphs) >= self.MAX_GRAPHS:
            raise RuntimeError(f"Graph limit reached ({self.MAX_GRAPHS})")
        try:
            if format == "json":
                graph = self._import_graph_json(data)
            elif format == "xml":
                graph = self._import_graph_xml(data)
            else:
                graph = self._import_graph_json(data)
            if graph:
                self._graphs[graph.id] = graph
                self._total_graphs_created += 1
            return graph
        except Exception:
            return None

    def _export_graph_xml(self, graph: ScriptGraph) -> str:
        """Export a graph to XML format."""
        parts = ['<?xml version="1.0" encoding="UTF-8"?>']
        parts.append(
            f'<script_graph id="{graph.id}" name="{graph.name}" '
            f'target_language="{graph.target_language.value}">'
        )
        parts.append(f"  <description>{graph.description}</description>")
        parts.append("  <nodes>")
        for node in graph.nodes.values():
            parts.append(
                f'    <node id="{node.id}" type="{node.node_type.value}" '
                f'name="{node.name}" x="{node.position_x}" y="{node.position_y}">'
            )
            for param in node.params:
                parts.append(
                    f'      <param name="{param.name}" type="{param.param_type.value}" '
                    f'value="{param.value}" required="{str(param.required).lower()}"/>'
                )
            for child_id in node.children:
                parts.append(f'      <child ref="{child_id}"/>')
            parts.append("    </node>")
        parts.append("  </nodes>")
        parts.append("  <connections>")
        for conn in graph.connections.values():
            parts.append(
                f'    <connection id="{conn.id}" source="{conn.source_node_id}" '
                f'source_port="{conn.source_port}" target="{conn.target_node_id}" '
                f'target_port="{conn.target_port}" enabled="{str(conn.enabled).lower()}"/>'
            )
        parts.append("  </connections>")
        parts.append("</script_graph>")
        return "\n".join(parts)

    def _import_graph_json(self, data: str) -> Optional[ScriptGraph]:
        """Import a graph from JSON data."""
        raw = json.loads(data)
        graph = ScriptGraph(
            name=raw.get("name", "Imported Graph"),
            description=raw.get("description", ""),
            root_node_id=raw.get("root_node_id", ""),
            target_language=TargetLanguage(raw.get("target_language", "python")),
        )
        for node_data in raw.get("nodes", []):
            params = [
                NodeParameter(
                    name=p.get("name", ""),
                    param_type=ParameterType(p.get("param_type", "string")),
                    value=p.get("value", ""),
                    default_value=p.get("default_value", ""),
                    required=p.get("required", False),
                    description=p.get("description", ""),
                    enum_values=p.get("enum_values", []),
                )
                for p in node_data.get("params", [])
            ]
            node = ScriptNode(
                id=node_data.get("id", uuid.uuid4().hex),
                node_type=NodeType(node_data.get("node_type", "action")),
                name=node_data.get("name", ""),
                params=params,
                children=node_data.get("children", []),
                position_x=node_data.get("position_x", 0.0),
                position_y=node_data.get("position_y", 0.0),
                metadata=node_data.get("metadata", {}),
            )
            graph.nodes[node.id] = node
        for conn_data in raw.get("connections", []):
            conn = NodeConnection(
                id=conn_data.get("id", uuid.uuid4().hex),
                source_node_id=conn_data.get("source_node_id", ""),
                source_port=conn_data.get("source_port", "output"),
                target_node_id=conn_data.get("target_node_id", ""),
                target_port=conn_data.get("target_port", "input"),
                condition=conn_data.get("condition", ""),
                priority=conn_data.get("priority", 0),
                enabled=conn_data.get("enabled", True),
            )
            graph.connections[conn.id] = conn
        return graph

    def _import_graph_xml(self, data: str) -> Optional[ScriptGraph]:
        """Import a graph from XML data."""
        import xml.etree.ElementTree as ET
        root = ET.fromstring(data)
        graph = ScriptGraph(
            id=root.get("id", uuid.uuid4().hex),
            name=root.get("name", "Imported Graph"),
            description="",
            target_language=TargetLanguage(root.get("target_language", "python")),
        )
        desc_el = root.find("description")
        if desc_el is not None and desc_el.text:
            graph.description = desc_el.text
        nodes_el = root.find("nodes")
        if nodes_el is not None:
            for node_el in nodes_el.findall("node"):
                params = []
                for param_el in node_el.findall("param"):
                    params.append(NodeParameter(
                        name=param_el.get("name", ""),
                        param_type=ParameterType(param_el.get("type", "string")),
                        value=param_el.get("value", ""),
                        required=param_el.get("required", "false").lower() == "true",
                    ))
                children = [c.get("ref", "") for c in node_el.findall("child")]
                node = ScriptNode(
                    id=node_el.get("id", uuid.uuid4().hex),
                    node_type=NodeType(node_el.get("type", "action")),
                    name=node_el.get("name", ""),
                    params=params,
                    children=children,
                    position_x=float(node_el.get("x", 0)),
                    position_y=float(node_el.get("y", 0)),
                )
                graph.nodes[node.id] = node
        conns_el = root.find("connections")
        if conns_el is not None:
            for conn_el in conns_el.findall("connection"):
                conn = NodeConnection(
                    id=conn_el.get("id", uuid.uuid4().hex),
                    source_node_id=conn_el.get("source", ""),
                    source_port=conn_el.get("source_port", "output"),
                    target_node_id=conn_el.get("target", ""),
                    target_port=conn_el.get("target_port", "input"),
                    enabled=conn_el.get("enabled", "true").lower() == "true",
                )
                graph.connections[conn.id] = conn
        return graph

    # ------------------------------------------------------------------
    # Graph Cloning and Optimization
    # ------------------------------------------------------------------

    def clone_graph(self, graph_id: str, new_name: str) -> Optional[ScriptGraph]:
        """Duplicate an existing graph with a new name."""
        source = self._graphs.get(graph_id)
        if source is None:
            return None
        if len(self._graphs) >= self.MAX_GRAPHS:
            raise RuntimeError(f"Graph limit reached ({self.MAX_GRAPHS})")
        exported = self.export_graph(graph_id, "json")
        cloned = self.import_graph(exported, "json")
        if cloned:
            cloned.name = new_name
            cloned.id = uuid.uuid4().hex
            cloned.created_at = _time_module.time()
            cloned.updated_at = _time_module.time()
            self._graphs[cloned.id] = cloned
        return cloned

    def optimize_graph(self, graph_id: str) -> int:
        """Remove dead branches, unreachable nodes, and simplify condition chains."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return 0
        self._total_optimizations += 1
        removed_count = 0

        dead_nodes = self._find_dead_nodes(graph)
        for node_id in dead_nodes:
            self.remove_node(graph_id, node_id)
            removed_count += 1

        empty_connections = [
            cid for cid, conn in graph.connections.items()
            if not conn.condition.strip() and not conn.enabled
        ]
        for cid in empty_connections:
            del graph.connections[cid]
            removed_count += 1

        graph.updated_at = _time_module.time()
        return removed_count

    def _find_dead_nodes(self, graph: ScriptGraph) -> List[str]:
        """Find nodes with no incoming connections that are not event nodes."""
        target_node_ids: Set[str] = set()
        for conn in graph.connections.values():
            if conn.enabled:
                target_node_ids.add(conn.target_node_id)
        dead = []
        for node_id, node in graph.nodes.items():
            if node.node_type == NodeType.EVENT:
                continue
            if node.node_type == NodeType.VARIABLE:
                continue
            if node.node_type == NodeType.COMMENT:
                continue
            if node_id not in target_node_ids and node.node_type != NodeType.SUB_GRAPH:
                dead.append(node_id)
        return dead

    def _get_branch_definitions(
        self, node: ScriptNode
    ) -> List[Tuple[str, List[str]]]:
        """Extract branch condition-to-child mappings from a branch node."""
        branches: List[Tuple[str, List[str]]] = []
        conditional_pairs: Dict[str, List[str]] = {}
        default_nodes: List[str] = []
        for child_id in node.children:
            conditions = self._get_param_value(node, f"condition_{child_id}", "")
            if conditions:
                conditional_pairs.setdefault(conditions, []).append(child_id)
            else:
                default_nodes.append(child_id)
        for condition, node_ids in conditional_pairs.items():
            branches.append((condition, node_ids))
        if default_nodes:
            branches.append(("else", default_nodes))
        return branches

    # ------------------------------------------------------------------
    # Sub-Graph Interface
    # ------------------------------------------------------------------

    def get_sub_graph_interface(self, graph_id: str) -> Dict[str, Any]:
        """Return the input/output interface for reusable sub-graphs."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return {}
        inputs: List[Dict[str, Any]] = []
        outputs: List[Dict[str, Any]] = []
        for node in graph.nodes.values():
            if node.node_type == NodeType.VARIABLE:
                var_name = self._get_param_value(node, "variable_name", "")
                var_type = self._get_param_value(node, "type", ParameterType.STRING.value)
                is_input = self._get_param_value(node, "is_input", "false")
                if bool(is_input) or is_input == "true" or not self._node_has_incoming(graph, node.id):
                    inputs.append({
                        "name": var_name or node.name,
                        "type": var_type,
                        "default": self._get_param_value(node, "value", ""),
                    })
                else:
                    outputs.append({
                        "name": var_name or node.name,
                        "type": var_type,
                    })
        return {
            "graph_name": graph.name,
            "graph_id": graph.id,
            "inputs": inputs,
            "outputs": outputs,
            "node_count": len(graph.nodes),
            "connection_count": len(graph.connections),
        }

    def _node_has_incoming(self, graph: ScriptGraph, node_id: str) -> bool:
        """Check if a node has any enabled incoming connections."""
        return any(
            conn.target_node_id == node_id and conn.enabled
            for conn in graph.connections.values()
        )

    # ------------------------------------------------------------------
    # Runtime Statistics
    # ------------------------------------------------------------------

    def get_runtime_stats(self) -> Dict[str, Any]:
        """Return transpilation and execution statistics."""
        total_nodes = sum(len(g.nodes) for g in self._graphs.values())
        total_connections = sum(len(g.connections) for g in self._graphs.values())
        language_counts: Dict[str, int] = {}
        node_type_counts: Dict[str, int] = {}
        for graph in self._graphs.values():
            lang = graph.target_language.value
            language_counts[lang] = language_counts.get(lang, 0) + 1
            for node in graph.nodes.values():
                nt = node.node_type.value
                node_type_counts[nt] = node_type_counts.get(nt, 0) + 1
        return {
            "total_graphs": len(self._graphs),
            "total_nodes": total_nodes,
            "total_connections": total_connections,
            "total_graphs_created": self._total_graphs_created,
            "total_nodes_added": self._total_nodes_added,
            "total_connections_made": self._total_connections_made,
            "total_transpilations": self._total_transpilations,
            "total_executions": self._total_executions,
            "total_validations": self._total_validations,
            "total_optimizations": self._total_optimizations,
            "language_distribution": language_counts,
            "node_type_distribution": node_type_counts,
            "max_graphs": self.MAX_GRAPHS,
            "max_nodes_per_graph": self.MAX_NODES_PER_GRAPH,
            "max_connections_per_graph": self.MAX_CONNECTIONS_PER_GRAPH,
        }

    # ------------------------------------------------------------------
    # Utility Methods
    # ------------------------------------------------------------------

    def _collect_variable_nodes(self, graph: ScriptGraph) -> Dict[str, str]:
        """Collect top-level variable declarations from the graph."""
        variables: Dict[str, str] = {}
        for node in graph.nodes.values():
            if node.node_type == NodeType.VARIABLE:
                var_name = self._get_param_value(node, "variable_name", "")
                var_value = self._get_param_value(node, "value", "None")
                if var_name:
                    variables[var_name] = var_value
        return variables

    def _get_param_value(
        self, node: ScriptNode, param_name: str, default: Any = ""
    ) -> Any:
        """Get the value of a named parameter from a node."""
        for param in node.params:
            if param.name == param_name:
                return param.value if param.value != "" else param.default_value
        return default

    def _build_action_args_python(self, node: ScriptNode) -> str:
        """Build argument string for a Python action call."""
        args: List[str] = []
        for param in node.params:
            if param.name in ("target", "condition", "loop_type", "loop_var", "start",
                              "end", "iterable", "expression", "assign_to", "variable_name",
                              "is_input", "type"):
                continue
            args.append(f"{param.name}={self._format_python_value(param.value)}")
        return ", ".join(args)

    def _format_python_value(self, value: Any) -> str:
        """Format a value for Python code output."""
        if isinstance(value, bool):
            return str(value)
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if value.lower() in ("true", "false", "none"):
                return value.capitalize() if value.lower() != "none" else "None"
            if value == "":
                return "None"
            return repr(value)
        return str(value)

    def _format_js_value(self, value: Any) -> str:
        """Format a value for JavaScript code output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if value.lower() in ("true", "false", "null", "undefined"):
                return value.lower()
            if value == "":
                return "null"
            return repr(value)
        return str(value)

    def _format_gdscript_value(self, value: Any) -> str:
        """Format a value for GDScript code output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if value == "":
                return "null"
            return f'"{value}"'
        return str(value)

    def _format_lua_value(self, value: Any) -> str:
        """Format a value for Lua code output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if value == "":
                return "nil"
            return f'"{value}"'
        return str(value)

    def _format_csharp_value(self, value: Any) -> str:
        """Format a value for C# code output."""
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        if isinstance(value, str):
            if value == "":
                return "null"
            return f'"{value}"'
        return str(value)

    def _default_name_for_type(self, node_type: NodeType) -> str:
        """Generate a default node name based on its type."""
        defaults = {
            NodeType.EVENT: "New Event",
            NodeType.CONDITION: "New Condition",
            NodeType.ACTION: "New Action",
            NodeType.EXPRESSION: "New Expression",
            NodeType.LOOP: "New Loop",
            NodeType.BRANCH: "New Branch",
            NodeType.SUB_GRAPH: "New Sub Graph",
            NodeType.VARIABLE: "New Variable",
            NodeType.COMMENT: "New Comment",
            NodeType.TRIGGER: "New Trigger",
        }
        return defaults.get(node_type, "New Node")

    def reset(self) -> None:
        """Reset all runtime state."""
        with self._lock:
            self._graphs.clear()
            self._execution_contexts.clear()
            self._total_graphs_created = 0
            self._total_nodes_added = 0
            self._total_connections_made = 0
            self._total_transpilations = 0
            self._total_executions = 0
            self._total_validations = 0
            self._total_optimizations = 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_graphs": len(self._graphs),
            "total_nodes": self._total_nodes_added,
            "transpiled_count": self._total_transpilations,
            "validation_issues_found": self._total_validations,
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_visual_script_runtime() -> VisualScriptRuntime:
    """Return the singleton VisualScriptRuntime instance."""
    return VisualScriptRuntime.get_instance()