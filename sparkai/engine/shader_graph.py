"""
SparkLabs Engine - Node-Based Shader Graph

Visual node-graph editor backend for constructing GLSL/HLSL shaders
without writing code. Supports arithmetic, utility, sampling, and
math nodes composable into a directed acyclic graph that compiles
to target shading languages.

Architecture:
  ShaderGraph
    |-- ShaderGraphDefinition (named container for nodes and connections)
    |-- ShaderGraphNode (typed processing unit with input/output pins)
    |-- GraphPin (typed data port on a node)
    |-- GraphConnection (directed edge between two pins)
    |-- ShaderNodeType (enumeration of all supported node types)

Supported Targets:
  - GLSL 330 (desktop OpenGL)
  - HLSL SM5 (DirectX 11)

Usage:
    sg = ShaderGraph()
    definition = sg.create_graph("MyShader")
    color_node = sg.add_node(definition.id, ShaderNodeType.COLOR, 100.0, 200.0)
    output_node = sg.add_node(definition.id, ShaderNodeType.OUTPUT, 400.0, 200.0)
    sg.add_connection(definition.id, color_node.id, color_node.outputs[0].id,
                      output_node.id, output_node.inputs[0].id)
    glsl = sg.compile_to_glsl(definition.id)
"""

from __future__ import annotations

import json
import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ShaderNodeType(Enum):
    COLOR = "color"
    TEXTURE = "texture"
    UV = "uv"
    TIME = "time"
    SINE = "sine"
    NOISE = "noise"
    MIX = "mix"
    MULTIPLY = "multiply"
    ADD = "add"
    SUBTRACT = "subtract"
    DIVIDE = "divide"
    LERP = "lerp"
    CLAMP = "clamp"
    STEP = "step"
    SMOOTHSTEP = "smoothstep"
    NORMALIZE = "normalize"
    DOT_PRODUCT = "dot_product"
    CROSS_PRODUCT = "cross_product"
    FRESNEL = "fresnel"
    OUTPUT = "output"


NODE_PIN_DEFINITIONS: Dict[ShaderNodeType, Dict[str, List[Dict[str, Any]]]] = {
    ShaderNodeType.COLOR: {
        "inputs": [],
        "outputs": [
            {"name": "Color", "type": "vec4"},
        ],
    },
    ShaderNodeType.TEXTURE: {
        "inputs": [
            {"name": "UV", "type": "vec2"},
        ],
        "outputs": [
            {"name": "Color", "type": "vec4"},
        ],
    },
    ShaderNodeType.UV: {
        "inputs": [],
        "outputs": [
            {"name": "UV", "type": "vec2"},
        ],
    },
    ShaderNodeType.TIME: {
        "inputs": [],
        "outputs": [
            {"name": "Time", "type": "float"},
        ],
    },
    ShaderNodeType.SINE: {
        "inputs": [
            {"name": "X", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.NOISE: {
        "inputs": [
            {"name": "Coord", "type": "vec2"},
            {"name": "Scale", "type": "float"},
        ],
        "outputs": [
            {"name": "Value", "type": "float"},
        ],
    },
    ShaderNodeType.MIX: {
        "inputs": [
            {"name": "A", "type": "vec4"},
            {"name": "B", "type": "vec4"},
            {"name": "T", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec4"},
        ],
    },
    ShaderNodeType.MULTIPLY: {
        "inputs": [
            {"name": "A", "type": "vec4"},
            {"name": "B", "type": "vec4"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec4"},
        ],
    },
    ShaderNodeType.ADD: {
        "inputs": [
            {"name": "A", "type": "vec4"},
            {"name": "B", "type": "vec4"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec4"},
        ],
    },
    ShaderNodeType.SUBTRACT: {
        "inputs": [
            {"name": "A", "type": "vec4"},
            {"name": "B", "type": "vec4"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec4"},
        ],
    },
    ShaderNodeType.DIVIDE: {
        "inputs": [
            {"name": "A", "type": "vec4"},
            {"name": "B", "type": "vec4"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec4"},
        ],
    },
    ShaderNodeType.LERP: {
        "inputs": [
            {"name": "A", "type": "float"},
            {"name": "B", "type": "float"},
            {"name": "T", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.CLAMP: {
        "inputs": [
            {"name": "X", "type": "float"},
            {"name": "Min", "type": "float"},
            {"name": "Max", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.STEP: {
        "inputs": [
            {"name": "Edge", "type": "float"},
            {"name": "X", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.SMOOTHSTEP: {
        "inputs": [
            {"name": "Edge0", "type": "float"},
            {"name": "Edge1", "type": "float"},
            {"name": "X", "type": "float"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.NORMALIZE: {
        "inputs": [
            {"name": "Vec", "type": "vec3"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec3"},
        ],
    },
    ShaderNodeType.DOT_PRODUCT: {
        "inputs": [
            {"name": "A", "type": "vec3"},
            {"name": "B", "type": "vec3"},
        ],
        "outputs": [
            {"name": "Result", "type": "float"},
        ],
    },
    ShaderNodeType.CROSS_PRODUCT: {
        "inputs": [
            {"name": "A", "type": "vec3"},
            {"name": "B", "type": "vec3"},
        ],
        "outputs": [
            {"name": "Result", "type": "vec3"},
        ],
    },
    ShaderNodeType.FRESNEL: {
        "inputs": [
            {"name": "Normal", "type": "vec3"},
            {"name": "ViewDir", "type": "vec3"},
            {"name": "Power", "type": "float"},
        ],
        "outputs": [
            {"name": "Factor", "type": "float"},
        ],
    },
    ShaderNodeType.OUTPUT: {
        "inputs": [
            {"name": "Color", "type": "vec4"},
        ],
        "outputs": [],
    },
}


@dataclass
class GraphPin:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    pin_type: str = "float"
    direction: str = "input"
    default_value: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "pin_type": self.pin_type,
            "direction": self.direction,
            "default_value": self.default_value,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphPin":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            pin_type=data.get("pin_type", "float"),
            direction=data.get("direction", "input"),
            default_value=data.get("default_value"),
        )


@dataclass
class ShaderGraphNode:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    node_type: ShaderNodeType = ShaderNodeType.COLOR
    position_x: float = 0.0
    position_y: float = 0.0
    label: str = ""
    inputs: List[GraphPin] = field(default_factory=list)
    outputs: List[GraphPin] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "position_x": self.position_x,
            "position_y": self.position_y,
            "label": self.label,
            "inputs": [pin.to_dict() for pin in self.inputs],
            "outputs": [pin.to_dict() for pin in self.outputs],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShaderGraphNode":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            node_type=ShaderNodeType(data.get("node_type", "color")),
            position_x=data.get("position_x", 0.0),
            position_y=data.get("position_y", 0.0),
            label=data.get("label", ""),
            inputs=[GraphPin.from_dict(p) for p in data.get("inputs", [])],
            outputs=[GraphPin.from_dict(p) for p in data.get("outputs", [])],
        )


@dataclass
class GraphConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    source_node_id: str = ""
    source_pin_id: str = ""
    target_node_id: str = ""
    target_pin_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "source_pin_id": self.source_pin_id,
            "target_node_id": self.target_node_id,
            "target_pin_id": self.target_pin_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GraphConnection":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            source_node_id=data.get("source_node_id", ""),
            source_pin_id=data.get("source_pin_id", ""),
            target_node_id=data.get("target_node_id", ""),
            target_pin_id=data.get("target_pin_id", ""),
        )


@dataclass
class ShaderGraphDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Shader Graph"
    nodes: Dict[str, ShaderGraphNode] = field(default_factory=dict)
    connections: List[GraphConnection] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "nodes": [node.to_dict() for node in self.nodes.values()],
            "connections": [conn.to_dict() for conn in self.connections],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ShaderGraphDefinition":
        nodes_data = data.get("nodes", [])
        nodes: Dict[str, ShaderGraphNode] = {}
        for nd in nodes_data:
            node = ShaderGraphNode.from_dict(nd)
            nodes[node.id] = node
        connections = [GraphConnection.from_dict(c) for c in data.get("connections", [])]
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", "New Shader Graph"),
            nodes=nodes,
            connections=connections,
        )


class ShaderGraph:
    """Node-based shader graph engine supporting GLSL and HLSL compilation."""

    _instance: Optional["ShaderGraph"] = None
    _lock: threading.RLock = threading.RLock()

    def __init__(self) -> None:
        self._graphs: Dict[str, ShaderGraphDefinition] = {}
        self._graph_count: int = 0
        self._node_count: int = 0
        self._connection_count: int = 0
        self._total_compilations: int = 0

    @classmethod
    def get_instance(cls) -> "ShaderGraph":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def create_graph(self, name: str = "New Shader Graph") -> ShaderGraphDefinition:
        with self._lock:
            definition = ShaderGraphDefinition(name=name)
            self._graphs[definition.id] = definition
            self._graph_count += 1
            return definition

    def get_graph(self, graph_id: str) -> Optional[ShaderGraphDefinition]:
        with self._lock:
            return self._graphs.get(graph_id)

    def add_node(
        self,
        graph_id: str,
        node_type: ShaderNodeType,
        position_x: float = 0.0,
        position_y: float = 0.0,
        label: str = "",
    ) -> Optional[ShaderGraphNode]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            pin_defs = NODE_PIN_DEFINITIONS.get(node_type, {"inputs": [], "outputs": []})

            inputs = [
                GraphPin(
                    name=p["name"],
                    pin_type=p["type"],
                    direction="input",
                )
                for p in pin_defs["inputs"]
            ]
            outputs = [
                GraphPin(
                    name=p["name"],
                    pin_type=p["type"],
                    direction="output",
                )
                for p in pin_defs["outputs"]
            ]

            node = ShaderGraphNode(
                node_type=node_type,
                position_x=position_x,
                position_y=position_y,
                label=label or node_type.value.title(),
                inputs=inputs,
                outputs=outputs,
            )
            graph.nodes[node.id] = node
            self._node_count += 1
            return node

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False
            if node_id not in graph.nodes:
                return False

            del graph.nodes[node_id]
            graph.connections = [
                c for c in graph.connections
                if c.source_node_id != node_id and c.target_node_id != node_id
            ]
            self._node_count = max(0, self._node_count - 1)
            return True

    def add_connection(
        self,
        graph_id: str,
        source_node_id: str,
        source_pin_id: str,
        target_node_id: str,
        target_pin_id: str,
    ) -> Optional[GraphConnection]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None

            source_node = graph.nodes.get(source_node_id)
            target_node = graph.nodes.get(target_node_id)
            if source_node is None or target_node is None:
                return None

            source_pin = _find_pin_by_id(source_node.outputs, source_pin_id)
            target_pin = _find_pin_by_id(target_node.inputs, target_pin_id)
            if source_pin is None or target_pin is None:
                return None

            for existing in graph.connections:
                if existing.target_node_id == target_node_id and existing.target_pin_id == target_pin_id:
                    return None

            connection = GraphConnection(
                source_node_id=source_node_id,
                source_pin_id=source_pin_id,
                target_node_id=target_node_id,
                target_pin_id=target_pin_id,
            )
            graph.connections.append(connection)
            self._connection_count += 1
            return connection

    def remove_connection(self, graph_id: str, connection_id: str) -> bool:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False

            for i, conn in enumerate(graph.connections):
                if conn.id == connection_id:
                    graph.connections.pop(i)
                    self._connection_count = max(0, self._connection_count - 1)
                    return True
            return False

    def validate_graph(self, graph_id: str) -> Dict[str, Any]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return {"valid": False, "errors": [f"Graph '{graph_id}' not found"]}

            errors: List[str] = []
            warnings: List[str] = []

            output_nodes = [
                n for n in graph.nodes.values()
                if n.node_type == ShaderNodeType.OUTPUT
            ]
            if not output_nodes:
                errors.append("Graph must contain at least one OUTPUT node")
            elif len(output_nodes) > 1:
                warnings.append("Graph has multiple OUTPUT nodes; only the first will be used")

            for node in graph.nodes.values():
                connected_input_ids: set = set()
                for conn in graph.connections:
                    if conn.target_node_id == node.id:
                        connected_input_ids.add(conn.target_pin_id)

                for pin in node.inputs:
                    if pin.id not in connected_input_ids and pin.default_value is None:
                        if node.node_type not in (
                            ShaderNodeType.COLOR,
                            ShaderNodeType.UV,
                            ShaderNodeType.TIME,
                        ):
                            errors.append(
                                f"Node '{node.label}' ({node.id}) has unconnected "
                                f"input '{pin.name}' with no default value"
                            )

            node_ids = set(graph.nodes.keys())
            for conn in graph.connections:
                if conn.source_node_id not in node_ids:
                    errors.append(
                        f"Connection '{conn.id}' references missing source node '{conn.source_node_id}'"
                    )
                if conn.target_node_id not in node_ids:
                    errors.append(
                        f"Connection '{conn.id}' references missing target node '{conn.target_node_id}'"
                    )

            if _detect_cycles(graph.nodes, graph.connections):
                errors.append("Graph contains a cycle; shader graphs must be acyclic")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "node_count": len(graph.nodes),
                "connection_count": len(graph.connections),
            }

    def compile_to_glsl(self, graph_id: str) -> Dict[str, Any]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return {"success": False, "error": f"Graph '{graph_id}' not found"}

            validation = self.validate_graph(graph_id)
            if not validation["valid"]:
                return {"success": False, "error": "Graph validation failed", "validation": validation}

            self._total_compilations += 1

            lines: List[str] = []
            lines.append("#version 330 core")
            lines.append("")
            lines.append("// Generated by SparkLabs ShaderGraph")
            lines.append(f"// Graph: {graph.name}")
            lines.append("")

            uniform_declarations: List[str] = []
            function_declarations: List[str] = []
            main_body: List[str] = []

            for node in graph.nodes.values():
                _append_node_glsl(node, uniform_declarations, function_declarations, main_body)

            in_declarations: List[str] = []
            in_declarations.append("in vec2 vUV;")
            in_declarations.append("in vec3 vWorldNormal;")
            in_declarations.append("in vec3 vViewDirection;")

            for line in in_declarations:
                lines.append(line)

            for line in uniform_declarations:
                lines.append(line)

            lines.append("")
            lines.append("out vec4 fragColor;")
            lines.append("")

            for line in function_declarations:
                lines.append(line)

            lines.append("void main()")
            lines.append("{")

            resolve_order = _topological_sort(graph.nodes, graph.connections)
            var_declarations: Dict[str, str] = {}
            for node_id in resolve_order:
                node = graph.nodes[node_id]
                _emit_node_body_glsl(graph, node, var_declarations, main_body, lines)

            for var_line in main_body:
                lines.append(f"    {var_line}")

            output_node = _find_output_node(graph.nodes)
            if output_node:
                connected_color = _find_connected_source_var(graph, output_node, "Color")
                if connected_color:
                    lines.append(f"    fragColor = {connected_color};")
                else:
                    lines.append("    fragColor = vec4(1.0, 1.0, 1.0, 1.0);")

            lines.append("}")

            source = "\n".join(lines)
            return {
                "success": True,
                "source": source,
                "graph_id": graph_id,
                "graph_name": graph.name,
            }

    def compile_to_hlsl(self, graph_id: str) -> Dict[str, Any]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return {"success": False, "error": f"Graph '{graph_id}' not found"}

            validation = self.validate_graph(graph_id)
            if not validation["valid"]:
                return {"success": False, "error": "Graph validation failed", "validation": validation}

            self._total_compilations += 1

            lines: List[str] = []
            lines.append("// Generated by SparkLabs ShaderGraph")
            lines.append(f"// Graph: {graph.name}")
            lines.append("")

            lines.append("struct VSOutput")
            lines.append("{")
            lines.append("    float4 position : SV_POSITION;")
            lines.append("    float2 uv : TEXCOORD0;")
            lines.append("    float3 worldNormal : TEXCOORD1;")
            lines.append("    float3 viewDirection : TEXCOORD2;")
            lines.append("};")
            lines.append("")

            cbuffer_entries: List[str] = []
            helper_functions: List[str] = []
            pixel_body: List[str] = []

            for node in graph.nodes.values():
                _append_node_hlsl(node, cbuffer_entries, helper_functions)

            if cbuffer_entries:
                lines.append("cbuffer ShaderGraphParams : register(b0)")
                lines.append("{")
                for entry in cbuffer_entries:
                    lines.append(f"    {entry}")
                lines.append("}")
                lines.append("")

            for fn in helper_functions:
                lines.append(fn)
                lines.append("")

            lines.append("float4 main(VSOutput input) : SV_TARGET")
            lines.append("{")

            resolve_order = _topological_sort(graph.nodes, graph.connections)
            var_declarations: Dict[str, str] = {}
            for node_id in resolve_order:
                node = graph.nodes[node_id]
                _emit_node_body_hlsl(graph, node, var_declarations, pixel_body)

            for var_line in pixel_body:
                lines.append(f"    {var_line}")

            output_node = _find_output_node(graph.nodes)
            if output_node:
                connected_color = _find_connected_source_var(graph, output_node, "Color")
                if connected_color:
                    lines.append(f"    return {connected_color};")
                else:
                    lines.append("    return float4(1.0, 1.0, 1.0, 1.0);")

            lines.append("}")

            source = "\n".join(lines)
            return {
                "success": True,
                "source": source,
                "graph_id": graph_id,
                "graph_name": graph.name,
            }

    def export_graph(self, graph_id: str) -> Optional[str]:
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return None
            return json.dumps(graph.to_dict(), indent=2)

    def import_graph(self, data: str) -> Optional[ShaderGraphDefinition]:
        with self._lock:
            try:
                parsed = json.loads(data)
                definition = ShaderGraphDefinition.from_dict(parsed)
                self._graphs[definition.id] = definition
                self._graph_count += 1
                self._node_count += len(definition.nodes)
                self._connection_count += len(definition.connections)
                return definition
            except (json.JSONDecodeError, KeyError, TypeError):
                return None

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_nodes = sum(len(g.nodes) for g in self._graphs.values())
            total_connections = sum(len(g.connections) for g in self._graphs.values())
            node_type_counts: Dict[str, int] = {}
            for g in self._graphs.values():
                for node in g.nodes.values():
                    key = node.node_type.value
                    node_type_counts[key] = node_type_counts.get(key, 0) + 1

            return {
                "total_graphs": len(self._graphs),
                "graph_count": self._graph_count,
                "total_nodes": total_nodes,
                "node_count": self._node_count,
                "total_connections": total_connections,
                "connection_count": self._connection_count,
                "total_compilations": self._total_compilations,
                "node_type_distribution": node_type_counts,
                "available_node_types": [t.value for t in ShaderNodeType],
            }

    def delete_graph(self, graph_id: str) -> bool:
        with self._lock:
            graph = self._graphs.pop(graph_id, None)
            if graph is None:
                return False
            self._graph_count = max(0, self._graph_count - 1)
            self._node_count = max(0, self._node_count - len(graph.nodes))
            self._connection_count = max(0, self._connection_count - len(graph.connections))
            return True

    def list_graphs(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "id": g.id,
                    "name": g.name,
                    "node_count": len(g.nodes),
                    "connection_count": len(g.connections),
                }
                for g in self._graphs.values()
            ]


def get_shader_graph() -> ShaderGraph:
    return ShaderGraph.get_instance()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _find_pin_by_id(pins: List[GraphPin], pin_id: str) -> Optional[GraphPin]:
    for pin in pins:
        if pin.id == pin_id:
            return pin
    return None


def _detect_cycles(
    nodes: Dict[str, ShaderGraphNode],
    connections: List[GraphConnection],
) -> bool:
    adjacency: Dict[str, List[str]] = {nid: [] for nid in nodes}
    for conn in connections:
        adjacency[conn.source_node_id].append(conn.target_node_id)

    WHITE, GRAY, BLACK = 0, 1, 2
    color: Dict[str, int] = {nid: WHITE for nid in nodes}

    def dfs(node_id: str) -> bool:
        color[node_id] = GRAY
        for neighbor in adjacency.get(node_id, []):
            if color.get(neighbor, BLACK) == GRAY:
                return True
            if color.get(neighbor, BLACK) == WHITE:
                if dfs(neighbor):
                    return True
        color[node_id] = BLACK
        return False

    for nid in nodes:
        if color[nid] == WHITE:
            if dfs(nid):
                return True
    return False


def _topological_sort(
    nodes: Dict[str, ShaderGraphNode],
    connections: List[GraphConnection],
) -> List[str]:
    adjacency: Dict[str, List[str]] = {nid: [] for nid in nodes}
    in_degree: Dict[str, int] = {nid: 0 for nid in nodes}
    for conn in connections:
        adjacency[conn.source_node_id].append(conn.target_node_id)
        in_degree[conn.target_node_id] = in_degree.get(conn.target_node_id, 0) + 1

    queue: List[str] = [nid for nid, deg in in_degree.items() if deg == 0]
    result: List[str] = []

    while queue:
        nid = queue.pop(0)
        result.append(nid)
        for neighbor in adjacency.get(nid, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def _find_output_node(nodes: Dict[str, ShaderGraphNode]) -> Optional[ShaderGraphNode]:
    for node in nodes.values():
        if node.node_type == ShaderNodeType.OUTPUT:
            return node
    return None


def _find_connected_source_var(
    graph: ShaderGraphDefinition,
    target_node: ShaderGraphNode,
    target_pin_name: str,
) -> Optional[str]:
    target_pin = next(
        (p for p in target_node.inputs if p.name == target_pin_name), None
    )
    if target_pin is None:
        return None

    for conn in graph.connections:
        if conn.target_node_id == target_node.id and conn.target_pin_id == target_pin.id:
            source_node = graph.nodes.get(conn.source_node_id)
            if source_node is None:
                continue
            source_pin = _find_pin_by_id(source_node.outputs, conn.source_pin_id)
            if source_pin is not None:
                return f"{_safe_var_name(source_node.id)}_{_safe_var_name(source_pin.name)}"
    return None


def _safe_var_name(raw: str) -> str:
    return raw.replace("-", "_").replace(" ", "_")


# ---------------------------------------------------------------------------
# GLSL code generation helpers
# ---------------------------------------------------------------------------

_GLSL_FUNC_MAP: Dict[ShaderNodeType, str] = {
    ShaderNodeType.SINE: "sin",
    ShaderNodeType.MIX: "mix",
    ShaderNodeType.MULTIPLY: "*",
    ShaderNodeType.ADD: "+",
    ShaderNodeType.SUBTRACT: "-",
    ShaderNodeType.DIVIDE: "/",
    ShaderNodeType.LERP: "mix",
    ShaderNodeType.CLAMP: "clamp",
    ShaderNodeType.STEP: "step",
    ShaderNodeType.SMOOTHSTEP: "smoothstep",
    ShaderNodeType.NORMALIZE: "normalize",
    ShaderNodeType.DOT_PRODUCT: "dot",
    ShaderNodeType.CROSS_PRODUCT: "cross",
}


def _append_node_glsl(
    node: ShaderGraphNode,
    uniforms: List[str],
    functions: List[str],
    main_body: List[str],
) -> None:
    if node.node_type == ShaderNodeType.COLOR:
        uniforms.append(f"uniform vec4 u_Color_{_safe_var_name(node.id)};")
    elif node.node_type == ShaderNodeType.TEXTURE:
        uniforms.append(f"uniform sampler2D u_Texture_{_safe_var_name(node.id)};")
    elif node.node_type == ShaderNodeType.TIME:
        uniforms.append(f"uniform float u_Time_{_safe_var_name(node.id)};")
    elif node.node_type == ShaderNodeType.NOISE and not _has_noise_function(functions):
        functions.append(
            "float hash2D(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }"
        )
        functions.append(
            "float noise2D(vec2 p) {\n"
            "    vec2 i = floor(p);\n"
            "    vec2 f = fract(p);\n"
            "    f = f * f * (3.0 - 2.0 * f);\n"
            "    return mix(mix(hash2D(i + vec2(0.0, 0.0)), hash2D(i + vec2(1.0, 0.0)), f.x),\n"
            "               mix(hash2D(i + vec2(0.0, 1.0)), hash2D(i + vec2(1.0, 1.0)), f.x), f.y);\n"
            "}"
        )


def _emit_node_body_glsl(
    graph: ShaderGraphDefinition,
    node: ShaderGraphNode,
    var_declarations: Dict[str, str],
    lines: List[str],
    graph_lines: List[str],
) -> None:
    var_prefix = _safe_var_name(node.id)

    if node.node_type == ShaderNodeType.COLOR:
        var_name = f"{var_prefix}_Color"
        lines.append(f"vec4 {var_name} = u_Color_{var_prefix};")
        var_declarations[f"{node.id}_Color"] = "vec4"
    elif node.node_type == ShaderNodeType.UV:
        var_name = f"{var_prefix}_UV"
        lines.append(f"vec2 {var_name} = vUV;")
        var_declarations[f"{node.id}_UV"] = "vec2"
    elif node.node_type == ShaderNodeType.TIME:
        var_name = f"{var_prefix}_Time"
        lines.append(f"float {var_name} = u_Time_{var_prefix};")
        var_declarations[f"{node.id}_Time"] = "float"
    elif node.node_type == ShaderNodeType.TEXTURE:
        uv_var = _get_input_var(graph, node, "UV", "vec2", var_declarations, lines)
        var_name = f"{var_prefix}_Color"
        lines.append(f"vec4 {var_name} = texture(u_Texture_{var_prefix}, {uv_var});")
        var_declarations[f"{node.id}_Color"] = "vec4"
    elif node.node_type == ShaderNodeType.NOISE:
        coord_var = _get_input_var(graph, node, "Coord", "vec2", var_declarations, lines)
        scale_var = _get_input_var(graph, node, "Scale", "float", var_declarations, lines)
        var_name = f"{var_prefix}_Value"
        lines.append(f"float {var_name} = noise2D({coord_var} * {scale_var});")
        var_declarations[f"{node.id}_Value"] = "float"
    elif node.node_type == ShaderNodeType.FRESNEL:
        normal_var = _get_input_var(graph, node, "Normal", "vec3", var_declarations, lines)
        view_var = _get_input_var(graph, node, "ViewDir", "vec3", var_declarations, lines)
        power_var = _get_input_var(graph, node, "Power", "float", var_declarations, lines)
        var_name = f"{var_prefix}_Factor"
        lines.append(
            f"float {var_name} = pow(1.0 - abs(dot(normalize({normal_var}), normalize({view_var}))), {power_var});"
        )
        var_declarations[f"{node.id}_Factor"] = "float"
    elif node.node_type == ShaderNodeType.OUTPUT:
        pass
    else:
        func = _GLSL_FUNC_MAP.get(node.node_type)
        if func is None:
            return

        input_vars: List[str] = []
        for pin in node.inputs:
            iv = _get_input_var(graph, node, pin.name, pin.pin_type, var_declarations, lines)
            input_vars.append(iv)

        output_pin = node.outputs[0] if node.outputs else None
        if output_pin is None:
            return

        if func in ("*", "+", "-", "/"):
            expr = f" {func} ".join(input_vars)
        else:
            args = ", ".join(input_vars)
            expr = f"{func}({args})"

        var_name = f"{var_prefix}_{_safe_var_name(output_pin.name)}"
        result_type = output_pin.pin_type
        lines.append(f"{result_type} {var_name} = {expr};")
        var_declarations[f"{node.id}_{output_pin.name}"] = result_type


def _get_input_var(
    graph: ShaderGraphDefinition,
    node: ShaderGraphNode,
    pin_name: str,
    pin_type: str,
    var_declarations: Dict[str, str],
    lines: List[str],
) -> str:
    target_pin = next((p for p in node.inputs if p.name == pin_name), None)
    if target_pin is None:
        return _default_value_for_type(pin_type)

    for conn in graph.connections:
        if conn.target_node_id == node.id and conn.target_pin_id == target_pin.id:
            source_node = graph.nodes.get(conn.source_node_id)
            if source_node is None:
                continue
            source_pin = _find_pin_by_id(source_node.outputs, conn.source_pin_id)
            if source_pin is not None:
                return f"{_safe_var_name(source_node.id)}_{_safe_var_name(source_pin.name)}"

    if target_pin.default_value is not None:
        return _literal_for_value(pin_type, target_pin.default_value)
    return _default_value_for_type(pin_type)


def _default_value_for_type(pin_type: str) -> str:
    defaults: Dict[str, str] = {
        "float": "0.0",
        "vec2": "vec2(0.0)",
        "vec3": "vec3(0.0)",
        "vec4": "vec4(0.0)",
    }
    return defaults.get(pin_type, "0.0")


def _literal_for_value(pin_type: str, value: Any) -> str:
    if isinstance(value, (list, tuple)):
        args = ", ".join(str(float(v)) for v in value)
        return f"{pin_type}({args})"
    if isinstance(value, str) and value.startswith("v"):
        return value
    return str(float(value))


def _has_noise_function(functions: List[str]) -> bool:
    for fn in functions:
        if "noise2D(" in fn:
            return True
    return False


# ---------------------------------------------------------------------------
# HLSL code generation helpers
# ---------------------------------------------------------------------------

_HLSL_FUNC_MAP: Dict[ShaderNodeType, str] = {
    ShaderNodeType.SINE: "sin",
    ShaderNodeType.MIX: "lerp",
    ShaderNodeType.MULTIPLY: "*",
    ShaderNodeType.ADD: "+",
    ShaderNodeType.SUBTRACT: "-",
    ShaderNodeType.DIVIDE: "/",
    ShaderNodeType.LERP: "lerp",
    ShaderNodeType.CLAMP: "clamp",
    ShaderNodeType.STEP: "step",
    ShaderNodeType.SMOOTHSTEP: "smoothstep",
    ShaderNodeType.NORMALIZE: "normalize",
    ShaderNodeType.DOT_PRODUCT: "dot",
    ShaderNodeType.CROSS_PRODUCT: "cross",
}

_HLSL_TYPE_MAP: Dict[str, str] = {
    "float": "float",
    "vec2": "float2",
    "vec3": "float3",
    "vec4": "float4",
}


def _hlsl_type(glsl_type: str) -> str:
    return _HLSL_TYPE_MAP.get(glsl_type, glsl_type)


def _hlsl_default(pin_type: str) -> str:
    defaults: Dict[str, str] = {
        "float": "0.0",
        "vec2": "float2(0.0, 0.0)",
        "vec3": "float3(0.0, 0.0, 0.0)",
        "vec4": "float4(0.0, 0.0, 0.0, 0.0)",
    }
    return defaults.get(pin_type, "0.0")


def _append_node_hlsl(
    node: ShaderGraphNode,
    cbuffer_entries: List[str],
    helper_functions: List[str],
) -> None:
    prefix = _safe_var_name(node.id)
    if node.node_type == ShaderNodeType.COLOR:
        cbuffer_entries.append(f"float4 u_Color_{prefix};")
    elif node.node_type == ShaderNodeType.TEXTURE:
        cbuffer_entries.append(f"Texture2D u_Texture_{prefix} : register(t0);")
    elif node.node_type == ShaderNodeType.TIME:
        cbuffer_entries.append(f"float u_Time_{prefix};")
    elif node.node_type == ShaderNodeType.NOISE and not _has_noise_function(helper_functions):
        helper_functions.append(
            "float hash2D(float2 p) { return frac(sin(dot(p, float2(127.1, 311.7))) * 43758.5453); }"
        )
        helper_functions.append(
            "float noise2D(float2 p) {\n"
            "    float2 i = floor(p);\n"
            "    float2 f = frac(p);\n"
            "    f = f * f * (3.0 - 2.0 * f);\n"
            "    return lerp(lerp(hash2D(i + float2(0.0, 0.0)), hash2D(i + float2(1.0, 0.0)), f.x),\n"
            "                lerp(hash2D(i + float2(0.0, 1.0)), hash2D(i + float2(1.0, 1.0)), f.x), f.y);\n"
            "}"
        )


def _emit_node_body_hlsl(
    graph: ShaderGraphDefinition,
    node: ShaderGraphNode,
    var_declarations: Dict[str, str],
    lines: List[str],
) -> None:
    var_prefix = _safe_var_name(node.id)

    if node.node_type == ShaderNodeType.COLOR:
        var_name = f"{var_prefix}_Color"
        lines.append(f"float4 {var_name} = u_Color_{var_prefix};")
        var_declarations[f"{node.id}_Color"] = "float4"
    elif node.node_type == ShaderNodeType.UV:
        var_name = f"{var_prefix}_UV"
        lines.append(f"float2 {var_name} = input.uv;")
        var_declarations[f"{node.id}_UV"] = "float2"
    elif node.node_type == ShaderNodeType.TIME:
        var_name = f"{var_prefix}_Time"
        lines.append(f"float {var_name} = u_Time_{var_prefix};")
        var_declarations[f"{node.id}_Time"] = "float"
    elif node.node_type == ShaderNodeType.TEXTURE:
        uv_var = _get_input_var_hlsl(graph, node, "UV", "float2", var_declarations, lines)
        var_name = f"{var_prefix}_Color"
        lines.append(f"float4 {var_name} = u_Texture_{var_prefix}.Sample(samplerState, {uv_var});")
        var_declarations[f"{node.id}_Color"] = "float4"
    elif node.node_type == ShaderNodeType.NOISE:
        coord_var = _get_input_var_hlsl(graph, node, "Coord", "float2", var_declarations, lines)
        scale_var = _get_input_var_hlsl(graph, node, "Scale", "float", var_declarations, lines)
        var_name = f"{var_prefix}_Value"
        lines.append(f"float {var_name} = noise2D({coord_var} * {scale_var});")
        var_declarations[f"{node.id}_Value"] = "float"
    elif node.node_type == ShaderNodeType.FRESNEL:
        normal_var = _get_input_var_hlsl(graph, node, "Normal", "float3", var_declarations, lines)
        view_var = _get_input_var_hlsl(graph, node, "ViewDir", "float3", var_declarations, lines)
        power_var = _get_input_var_hlsl(graph, node, "Power", "float", var_declarations, lines)
        var_name = f"{var_prefix}_Factor"
        lines.append(
            f"float {var_name} = pow(1.0 - abs(dot(normalize({normal_var}), normalize({view_var}))), {power_var});"
        )
        var_declarations[f"{node.id}_Factor"] = "float"
    elif node.node_type == ShaderNodeType.OUTPUT:
        pass
    else:
        func = _HLSL_FUNC_MAP.get(node.node_type)
        if func is None:
            return

        input_vars: List[str] = []
        for pin in node.inputs:
            iv = _get_input_var_hlsl(graph, node, pin.name, pin.pin_type, var_declarations, lines)
            input_vars.append(iv)

        output_pin = node.outputs[0] if node.outputs else None
        if output_pin is None:
            return

        if func in ("*", "+", "-", "/"):
            expr = f" {func} ".join(input_vars)
        else:
            args = ", ".join(input_vars)
            expr = f"{func}({args})"

        var_name = f"{var_prefix}_{_safe_var_name(output_pin.name)}"
        result_type = _hlsl_type(output_pin.pin_type)
        lines.append(f"{result_type} {var_name} = {expr};")
        var_declarations[f"{node.id}_{output_pin.name}"] = result_type


def _get_input_var_hlsl(
    graph: ShaderGraphDefinition,
    node: ShaderGraphNode,
    pin_name: str,
    pin_type: str,
    var_declarations: Dict[str, str],
    lines: List[str],
) -> str:
    target_pin = next((p for p in node.inputs if p.name == pin_name), None)
    if target_pin is None:
        return _hlsl_default(pin_type)

    for conn in graph.connections:
        if conn.target_node_id == node.id and conn.target_pin_id == target_pin.id:
            source_node = graph.nodes.get(conn.source_node_id)
            if source_node is None:
                continue
            source_pin = _find_pin_by_id(source_node.outputs, conn.source_pin_id)
            if source_pin is not None:
                return f"{_safe_var_name(source_node.id)}_{_safe_var_name(source_pin.name)}"

    if target_pin.default_value is not None:
        if isinstance(target_pin.default_value, (list, tuple)):
            args = ", ".join(str(float(v)) for v in target_pin.default_value)
            hlsl_t = _hlsl_type(pin_type)
            return f"{hlsl_t}({args})"
        return str(float(target_pin.default_value))
    return _hlsl_default(pin_type)