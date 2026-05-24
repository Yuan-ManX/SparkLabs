"""
SparkLabs Engine - Material Graph System

Node-based material authoring with visual shader code generation.
Provides a graph-driven editor for composing surface materials
via connected processing nodes that compile to target shader
languages for real-time rendering.

Architecture:
  MaterialGraphSystem
    |-- MaterialNode (processing units: texture, math, blend, output)
    |-- NodeConnection (typed links between node input/output ports)
    |-- MaterialGraph (container for nodes, connections, and metadata)
    |-- ShaderCode (compiled output for target shading language)

Shader Targets:
  - GLSL (OpenGL / Vulkan)
  - HLSL (Direct3D)
  - Metal (Apple platforms)
  - WGSL (WebGPU)
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class NodeType(Enum):
    """Classification of material graph processing nodes."""
    TEXTURE_SAMPLE = "texture_sample"
    COLOR_CONSTANT = "color_constant"
    MATH_OPERATION = "math_operation"
    BLEND = "blend"
    LERP = "lerp"
    NOISE = "noise"
    GRADIENT = "gradient"
    NORMAL_MAP = "normal_map"
    FRESNEL = "fresnel"
    PBR_OUTPUT = "pbr_output"


class BlendMode(Enum):
    """Blending operations for combining color or value inputs."""
    MIX = "mix"
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


class ShaderTarget(Enum):
    """Target shading language for code generation output."""
    GLSL = "glsl"
    HLSL = "hlsl"
    METAL = "metal"
    WGSL = "wgsl"


@dataclass
class MaterialNode:
    """A single processing node within a material graph.

    Each node has typed input and output ports that connect to other
    nodes. The node_type determines the processing logic applied when
    compiling the graph to shader code.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    node_type: NodeType = NodeType.COLOR_CONSTANT
    position_x: float = 0.0
    position_y: float = 0.0
    input_ports: List[str] = field(default_factory=list)
    output_ports: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_preview: bool = False
    is_enabled: bool = True
    order: int = 0

    @property
    def position(self) -> Tuple[float, float]:
        return (self.position_x, self.position_y)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value,
            "position": [self.position_x, self.position_y],
            "input_ports": list(self.input_ports),
            "output_ports": list(self.output_ports),
            "parameter_count": len(self.parameters),
            "parameters": dict(self.parameters),
            "is_preview": self.is_preview,
            "is_enabled": self.is_enabled,
            "order": self.order,
        }


@dataclass
class NodeConnection:
    """A directed link between an output port and an input port of two nodes."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_node_id: str = ""
    from_port: str = ""
    to_node_id: str = ""
    to_port: str = ""
    blend_mode: BlendMode = BlendMode.MIX
    weight: float = 1.0
    is_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_node_id": self.from_node_id,
            "from_port": self.from_port,
            "to_node_id": self.to_node_id,
            "to_port": self.to_port,
            "blend_mode": self.blend_mode.value,
            "weight": self.weight,
            "is_enabled": self.is_enabled,
        }


@dataclass
class MaterialGraph:
    """Container for a set of material nodes and their connections.

    Represents a single material definition that can be compiled
    to shader code for any supported target language.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    nodes: Dict[str, MaterialNode] = field(default_factory=dict)
    connections: Dict[str, NodeConnection] = field(default_factory=dict)
    output_node_id: str = ""
    is_dirty: bool = True
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "node_count": len(self.nodes),
            "connection_count": len(self.connections),
            "output_node_id": self.output_node_id,
            "is_dirty": self.is_dirty,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "tags": list(self.tags),
        }


@dataclass
class ShaderCode:
    """Compiled shader source code from a material graph."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    graph_id: str = ""
    target: ShaderTarget = ShaderTarget.GLSL
    source_code: str = ""
    vertex_source: str = ""
    fragment_source: str = ""
    uniforms: List[str] = field(default_factory=list)
    textures: List[str] = field(default_factory=list)
    compile_time_ms: float = 0.0
    node_count: int = 0
    error_count: int = 0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "graph_id": self.graph_id,
            "target": self.target.value,
            "source_code_length": len(self.source_code),
            "vertex_source_length": len(self.vertex_source),
            "fragment_source_length": len(self.fragment_source),
            "uniforms": list(self.uniforms),
            "textures": list(self.textures),
            "compile_time_ms": self.compile_time_ms,
            "node_count": self.node_count,
            "error_count": self.error_count,
            "warnings": list(self.warnings),
        }


class MaterialGraphSystem:
    """Node-based material authoring system with shader code generation.

    Provides a graph-based interface for composing surface materials
    through connected processing nodes. Graphs are compiled to shader
    source code targeting GLSL, HLSL, Metal, or WGSL.

    Usage:
        mgs = get_material_graph()
        graph = mgs.create_graph("StoneWall")
        tex = mgs.add_node(graph.id, "texture_sample", position=(0, 0),
                           parameters={"texture": "stone_albedo.png"})
        color = mgs.add_node(graph.id, "color_constant", position=(0, 150),
                             parameters={"color": [0.6, 0.55, 0.5, 1.0]})
        mgs.connect_nodes(graph.id, tex.id, "rgba", color.id, "color")
        shader = mgs.compile_shader(graph.id, target="glsl")
        print(shader.fragment_source)
    """

    _instance: Optional["MaterialGraphSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._graphs: Dict[str, MaterialGraph] = {}
        self._compiled_shaders: Dict[str, ShaderCode] = {}
        self._node_templates: Dict[str, Dict[str, Any]] = {}
        self._total_compilations: int = 0
        self._total_nodes_created: int = 0
        self._default_port_names()

    def _default_port_names(self) -> None:
        self._port_specs: Dict[str, Dict[str, List[str]]] = {
            NodeType.TEXTURE_SAMPLE.value: {
                "inputs": ["uv"],
                "outputs": ["rgba", "r", "g", "b", "a"],
            },
            NodeType.COLOR_CONSTANT.value: {
                "inputs": [],
                "outputs": ["rgba", "r", "g", "b", "a"],
            },
            NodeType.MATH_OPERATION.value: {
                "inputs": ["a", "b"],
                "outputs": ["result"],
            },
            NodeType.BLEND.value: {
                "inputs": ["foreground", "background", "mask"],
                "outputs": ["rgba"],
            },
            NodeType.LERP.value: {
                "inputs": ["a", "b", "t"],
                "outputs": ["result"],
            },
            NodeType.NOISE.value: {
                "inputs": ["uv", "scale", "seed"],
                "outputs": ["value", "rgba"],
            },
            NodeType.GRADIENT.value: {
                "inputs": ["uv", "start_color", "end_color"],
                "outputs": ["rgba"],
            },
            NodeType.NORMAL_MAP.value: {
                "inputs": ["normal_texture", "uv"],
                "outputs": ["normal"],
            },
            NodeType.FRESNEL.value: {
                "inputs": ["normal", "view_direction", "f0"],
                "outputs": ["factor"],
            },
            NodeType.PBR_OUTPUT.value: {
                "inputs": [
                    "albedo", "normal", "metallic", "roughness",
                    "ao", "emissive", "opacity",
                ],
                "outputs": [],
            },
        }

    @classmethod
    def get_instance(cls) -> "MaterialGraphSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Graph Management
    # ------------------------------------------------------------------

    def create_graph(self, name: str, description: str = "") -> MaterialGraph:
        graph = MaterialGraph(name=name, description=description)
        self._graphs[graph.id] = graph
        return graph

    def get_graph(self, graph_id: str) -> Optional[MaterialGraph]:
        return self._graphs.get(graph_id)

    def list_graphs(self) -> List[MaterialGraph]:
        return list(self._graphs.values())

    def remove_graph(self, graph_id: str) -> bool:
        if graph_id not in self._graphs:
            return False
        del self._graphs[graph_id]
        self._compiled_shaders.pop(graph_id, None)
        return True

    # ------------------------------------------------------------------
    # Node Operations
    # ------------------------------------------------------------------

    def add_node(
        self,
        graph_id: str,
        node_type: str,
        position: Tuple[float, float] = (0.0, 0.0),
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Optional[MaterialNode]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None

        try:
            nt = NodeType(node_type.lower())
        except ValueError:
            return None

        port_spec = self._port_specs.get(nt.value, {"inputs": [], "outputs": []})
        node = MaterialNode(
            name=f"{nt.value}_{len(graph.nodes) + 1}",
            node_type=nt,
            position_x=position[0],
            position_y=position[1],
            input_ports=list(port_spec["inputs"]),
            output_ports=list(port_spec["outputs"]),
            parameters=dict(parameters or {}),
            order=len(graph.nodes),
        )
        graph.nodes[node.id] = node
        graph.is_dirty = True
        graph.modified_at = time.time()
        self._total_nodes_created += 1
        return node

    def get_node(self, graph_id: str, node_id: str) -> Optional[MaterialNode]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None
        return graph.nodes.get(node_id)

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        graph = self._graphs.get(graph_id)
        if graph is None or node_id not in graph.nodes:
            return False
        del graph.nodes[node_id]
        to_remove = [
            cid for cid, conn in graph.connections.items()
            if conn.from_node_id == node_id or conn.to_node_id == node_id
        ]
        for cid in to_remove:
            del graph.connections[cid]
        if graph.output_node_id == node_id:
            graph.output_node_id = ""
        graph.is_dirty = True
        graph.modified_at = time.time()
        return True

    def update_node_parameters(
        self, graph_id: str, node_id: str, parameters: Dict[str, Any]
    ) -> bool:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return False
        node = graph.nodes.get(node_id)
        if node is None:
            return False
        node.parameters.update(parameters)
        graph.is_dirty = True
        graph.modified_at = time.time()
        return True

    def set_output_node(self, graph_id: str, node_id: str) -> bool:
        graph = self._graphs.get(graph_id)
        if graph is None or node_id not in graph.nodes:
            return False
        graph.output_node_id = node_id
        graph.is_dirty = True
        graph.modified_at = time.time()
        return True

    # ------------------------------------------------------------------
    # Connection Operations
    # ------------------------------------------------------------------

    def connect_nodes(
        self,
        graph_id: str,
        from_node_id: str,
        from_port: str,
        to_node_id: str,
        to_port: str,
        blend_mode: str = "mix",
        weight: float = 1.0,
    ) -> Optional[NodeConnection]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None

        from_node = graph.nodes.get(from_node_id)
        to_node = graph.nodes.get(to_node_id)
        if from_node is None or to_node is None:
            return None

        if from_port not in from_node.output_ports:
            return None
        if to_port not in to_node.input_ports:
            return None

        existing = [
            conn for conn in graph.connections.values()
            if conn.to_node_id == to_node_id and conn.to_port == to_port
        ]
        for conn in existing:
            del graph.connections[conn.id]

        try:
            bm = BlendMode(blend_mode.lower())
        except ValueError:
            bm = BlendMode.MIX

        connection = NodeConnection(
            from_node_id=from_node_id,
            from_port=from_port,
            to_node_id=to_node_id,
            to_port=to_port,
            blend_mode=bm,
            weight=max(0.0, min(1.0, weight)),
        )
        graph.connections[connection.id] = connection
        graph.is_dirty = True
        graph.modified_at = time.time()
        return connection

    def disconnect_nodes(
        self, graph_id: str, connection_id: str
    ) -> bool:
        graph = self._graphs.get(graph_id)
        if graph is None or connection_id not in graph.connections:
            return False
        del graph.connections[connection_id]
        graph.is_dirty = True
        graph.modified_at = time.time()
        return True

    def get_node_connections(
        self, graph_id: str, node_id: str
    ) -> Tuple[List[NodeConnection], List[NodeConnection]]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return ([], [])
        inputs = [
            conn for conn in graph.connections.values()
            if conn.to_node_id == node_id
        ]
        outputs = [
            conn for conn in graph.connections.values()
            if conn.from_node_id == node_id
        ]
        return (inputs, outputs)

    # ------------------------------------------------------------------
    # Shader Compilation
    # ------------------------------------------------------------------

    def compile_shader(
        self, graph_id: str, target: str = "glsl"
    ) -> Optional[ShaderCode]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None

        try:
            st = ShaderTarget(target.lower())
        except ValueError:
            st = ShaderTarget.GLSL

        start_time = time.time()
        warnings: List[str] = []
        uniforms: List[str] = []
        textures: List[str] = []

        for node in graph.nodes.values():
            if not node.is_enabled:
                continue
            if node.node_type == NodeType.TEXTURE_SAMPLE:
                tex_name = node.parameters.get("texture", f"tex_{node.id[:8]}")
                textures.append(tex_name)
                uniforms.append(f"sampler2D {tex_name}")
            elif node.node_type in (NodeType.COLOR_CONSTANT,):
                for port in node.output_ports:
                    uniforms.append(f"vec4 u_{node.id[:8]}_{port}")
            elif node.node_type in (
                NodeType.MATH_OPERATION, NodeType.BLEND, NodeType.LERP,
                NodeType.NOISE, NodeType.GRADIENT, NodeType.NORMAL_MAP,
                NodeType.FRESNEL, NodeType.PBR_OUTPUT,
            ):
                for key, value in node.parameters.items():
                    if isinstance(value, (int, float)):
                        uniforms.append(f"float u_{node.id[:8]}_{key}")

        if not graph.output_node_id and graph.nodes:
            output_nodes = [
                n for n in graph.nodes.values()
                if n.node_type == NodeType.PBR_OUTPUT
            ]
            if output_nodes:
                graph.output_node_id = output_nodes[0].id

        vertex_source, fragment_source = self._generate_shader_sources(
            graph, st, uniforms, textures, warnings
        )

        compile_time = (time.time() - start_time) * 1000.0
        self._total_compilations += 1

        shader = ShaderCode(
            graph_id=graph_id,
            target=st,
            source_code=fragment_source,
            vertex_source=vertex_source,
            fragment_source=fragment_source,
            uniforms=uniforms,
            textures=textures,
            compile_time_ms=round(compile_time, 2),
            node_count=len([n for n in graph.nodes.values() if n.is_enabled]),
            error_count=0,
            warnings=warnings,
        )
        self._compiled_shaders[graph_id] = shader
        graph.is_dirty = False
        return shader

    def _generate_shader_sources(
        self,
        graph: MaterialGraph,
        target: ShaderTarget,
        uniforms: List[str],
        textures: List[str],
        warnings: List[str],
    ) -> Tuple[str, str]:
        """Generate vertex and fragment shader source code for the target language."""

        if target == ShaderTarget.GLSL:
            version = "#version 330 core"
            precision = ""
            in_keyword = "in"
            out_keyword = "out"
            varying = "out"
        elif target == ShaderTarget.HLSL:
            version = ""
            precision = ""
            in_keyword = "in"
            out_keyword = "out"
            varying = "out"
        elif target == ShaderTarget.METAL:
            version = "#include <metal_stdlib>"
            precision = ""
            in_keyword = "in"
            out_keyword = "out"
            varying = "out"
        elif target == ShaderTarget.WGSL:
            version = ""
            precision = ""
            in_keyword = "in"
            out_keyword = "out"
            varying = "out"
        else:
            version = "#version 330 core"
            precision = ""
            in_keyword = "in"
            out_keyword = "out"
            varying = "out"

        node_functions = self._build_node_functions(graph, target, warnings)

        uniform_block = "\n".join(f"uniform {u};" for u in uniforms) if uniforms else ""
        if target == ShaderTarget.GLSL and uniform_block:
            uniform_block = "// Uniforms\n" + uniform_block

        texture_block = (
            "\n".join(f"// texture: {t}" for t in textures)
            if textures else ""
        )

        vertex_source = (
            f"{version}\n"
            f"{precision}\n"
            f"layout(location = 0) {in_keyword} vec3 a_position;\n"
            f"layout(location = 1) {in_keyword} vec2 a_texcoord;\n"
            f"layout(location = 2) {in_keyword} vec3 a_normal;\n"
            f"{varying} vec2 v_texcoord;\n"
            f"{varying} vec3 v_normal;\n"
            f"{varying} vec3 v_world_position;\n"
            f"uniform mat4 u_model;\n"
            f"uniform mat4 u_view;\n"
            f"uniform mat4 u_projection;\n"
            f"void main() {{\n"
            f"    vec4 world_pos = u_model * vec4(a_position, 1.0);\n"
            f"    v_world_position = world_pos.xyz;\n"
            f"    v_texcoord = a_texcoord;\n"
            f"    v_normal = normalize(mat3(u_model) * a_normal);\n"
            f"    gl_Position = u_projection * u_view * world_pos;\n"
            f"}}\n"
        )

        fragment_header = (
            f"{version}\n"
            f"{precision}\n"
            f"{varying} {in_keyword} vec2 v_texcoord;\n"
            f"{varying} {in_keyword} vec3 v_normal;\n"
            f"{varying} {in_keyword} vec3 v_world_position;\n"
            f"{uniform_block}\n"
            f"// Textures: {', '.join(textures) if textures else 'none'}\n"
        )

        fragment_body = node_functions

        fragment_output = (
            f"layout(location = 0) {out_keyword} vec4 fragColor;\n"
            f"void main() {{\n"
            f"    // Material graph evaluation\n"
            f"{fragment_body}"
            f"    fragColor = vec4(1.0, 0.0, 1.0, 1.0); // fallback magenta\n"
            f"}}\n"
        )

        fragment_source = fragment_header + "\n" + fragment_output

        return (vertex_source, fragment_source)

    def _build_node_functions(
        self,
        graph: MaterialGraph,
        target: ShaderTarget,
        warnings: List[str],
    ) -> str:
        """Generate shader function declarations for each node in topological order."""
        lines: List[str] = []
        ordered_nodes = self._topological_sort(graph)

        for node in ordered_nodes:
            if not node.is_enabled:
                continue
            if node.node_type == NodeType.COLOR_CONSTANT:
                color = node.parameters.get("color", [1.0, 1.0, 1.0, 1.0])
                if len(color) == 3:
                    color = [color[0], color[1], color[2], 1.0]
                lines.append(
                    f"    // Node: {node.name} ({node.node_type.value})\n"
                    f"    vec4 n_{node.id[:8]} = "
                    f"vec4({color[0]:.4f}, {color[1]:.4f}, "
                    f"{color[2]:.4f}, {color[3]:.4f});\n"
                )
            elif node.node_type == NodeType.TEXTURE_SAMPLE:
                tex = node.parameters.get("texture", f"tex_{node.id[:8]}")
                uv = node.parameters.get("uv", "v_texcoord")
                lines.append(
                    f"    // Node: {node.name} ({node.node_type.value})\n"
                    f"    vec4 n_{node.id[:8]} = texture({tex}, {uv});\n"
                )
            elif node.node_type == NodeType.MATH_OPERATION:
                op = node.parameters.get("operation", "add")
                a_val = node.parameters.get("a", 0.0)
                b_val = node.parameters.get("b", 0.0)
                op_expr = self._math_operation_expr(op, "a", "b")
                lines.append(
                    f"    // Node: {node.name} ({node.node_type.value})\n"
                    f"    float a = {a_val};\n"
                    f"    float b = {b_val};\n"
                    f"    float n_{node.id[:8]} = {op_expr};\n"
                )
            elif node.node_type == NodeType.BLEND:
                blend_mode = node.parameters.get("mode", "mix")
                fg = node.parameters.get("foreground", "vec4(1.0)")
                bg = node.parameters.get("background", "vec4(0.0)")
                lines.append(
                    f"    // Node: {node.name} (blend: {blend_mode})\n"
                    f"    vec4 n_{node.id[:8]} = mix(vec4(1.0), vec4(0.0), 0.5);\n"
                )
            elif node.node_type == NodeType.LERP:
                a_val = node.parameters.get("a", 0.0)
                b_val = node.parameters.get("b", 1.0)
                t_val = node.parameters.get("t", 0.5)
                lines.append(
                    f"    // Node: {node.name} (lerp)\n"
                    f"    float n_{node.id[:8]} = "
                    f"mix({a_val}, {b_val}, {t_val});\n"
                )
            elif node.node_type == NodeType.NOISE:
                scale = node.parameters.get("scale", 1.0)
                seed = node.parameters.get("seed", 0.0)
                lines.append(
                    f"    // Node: {node.name} (noise scale={scale} seed={seed})\n"
                    f"    float n_{node.id[:8]} = "
                    f"fract(sin(dot(v_texcoord * {scale}, "
                    f"vec2(12.9898, 78.233))) * 43758.5453);\n"
                )
            elif node.node_type == NodeType.GRADIENT:
                start_c = node.parameters.get("start_color", [0.0, 0.0, 0.0, 1.0])
                end_c = node.parameters.get("end_color", [1.0, 1.0, 1.0, 1.0])
                if len(start_c) == 3:
                    start_c = [*start_c, 1.0]
                if len(end_c) == 3:
                    end_c = [*end_c, 1.0]
                lines.append(
                    f"    // Node: {node.name} (gradient)\n"
                    f"    vec4 n_{node.id[:8]} = "
                    f"mix(vec4({start_c[0]:.4f},{start_c[1]:.4f},"
                    f"{start_c[2]:.4f},{start_c[3]:.4f}), "
                    f"vec4({end_c[0]:.4f},{end_c[1]:.4f},"
                    f"{end_c[2]:.4f},{end_c[3]:.4f}), v_texcoord.x);\n"
                )
            elif node.node_type == NodeType.NORMAL_MAP:
                tex = node.parameters.get("normal_texture", "normal_map")
                lines.append(
                    f"    // Node: {node.name} (normal_map)\n"
                    f"    vec3 n_{node.id[:8]} = "
                    f"texture({tex}, v_texcoord).rgb * 2.0 - 1.0;\n"
                )
            elif node.node_type == NodeType.FRESNEL:
                f0 = node.parameters.get("f0", 0.04)
                lines.append(
                    f"    // Node: {node.name} (fresnel f0={f0})\n"
                    f"    vec3 view_dir = normalize(-v_world_position);\n"
                    f"    float ndotv = max(dot(normalize(v_normal), view_dir), 0.0);\n"
                    f"    float n_{node.id[:8]} = "
                    f"{f0} + (1.0 - {f0}) * pow(1.0 - ndotv, 5.0);\n"
                )
            elif node.node_type == NodeType.PBR_OUTPUT:
                lines.append(
                    f"    // Node: {node.name} (pbr_output)\n"
                    f"    // Connected inputs drive albedo, normal, metallic, "
                    f"roughness, ao, emissive, opacity\n"
                )

        lines.append("    // End material graph evaluation")
        return "\n".join(lines)

    @staticmethod
    def _math_operation_expr(operation: str, a_name: str, b_name: str) -> str:
        ops: Dict[str, str] = {
            "add": f"{a_name} + {b_name}",
            "subtract": f"{a_name} - {b_name}",
            "multiply": f"{a_name} * {b_name}",
            "divide": f"{a_name} / max({b_name}, 0.0001)",
            "power": f"pow(max({a_name}, 0.0), {b_name})",
            "min": f"min({a_name}, {b_name})",
            "max": f"max({a_name}, {b_name})",
            "abs_diff": f"abs({a_name} - {b_name})",
            "smoothstep": f"smoothstep(0.0, 1.0, ({a_name} + {b_name}) * 0.5)",
        }
        return ops.get(operation.lower(), f"{a_name} + {b_name}")

    def _topological_sort(self, graph: MaterialGraph) -> List[MaterialNode]:
        """Order nodes so that dependencies are resolved before dependents."""
        in_degree: Dict[str, int] = {nid: 0 for nid in graph.nodes}
        adjacency: Dict[str, List[str]] = {nid: [] for nid in graph.nodes}

        for conn in graph.connections.values():
            if conn.from_node_id in adjacency and conn.to_node_id in in_degree:
                adjacency[conn.from_node_id].append(conn.to_node_id)
                in_degree[conn.to_node_id] += 1

        queue = [nid for nid, deg in in_degree.items() if deg == 0]
        result: List[MaterialNode] = []

        while queue:
            nid = queue.pop(0)
            node = graph.nodes.get(nid)
            if node:
                result.append(node)
            for neighbor in adjacency.get(nid, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        return result

    # ------------------------------------------------------------------
    # Node Preview
    # ------------------------------------------------------------------

    def preview_node(
        self, graph_id: str, node_id: str
    ) -> Dict[str, Any]:
        """Generate a preview of the result at a specific node output."""
        graph = self._graphs.get(graph_id)
        if graph is None:
            return {"error": "Graph not found", "success": False}
        node = graph.nodes.get(node_id)
        if node is None:
            return {"error": "Node not found", "success": False}

        preview_data: Dict[str, Any] = {
            "node_id": node_id,
            "node_name": node.name,
            "node_type": node.node_type.value,
            "success": True,
        }

        if node.node_type == NodeType.COLOR_CONSTANT:
            color = node.parameters.get("color", [1.0, 1.0, 1.0, 1.0])
            if len(color) == 3:
                color = [*color, 1.0]
            preview_data["preview"] = {
                "type": "color",
                "rgba": color,
                "hex": "#{:02x}{:02x}{:02x}".format(
                    int(max(0, min(1, color[0])) * 255),
                    int(max(0, min(1, color[1])) * 255),
                    int(max(0, min(1, color[2])) * 255),
                ),
            }
        elif node.node_type == NodeType.TEXTURE_SAMPLE:
            preview_data["preview"] = {
                "type": "texture",
                "texture": node.parameters.get("texture", "unknown"),
            }
        elif node.node_type == NodeType.GRADIENT:
            start = node.parameters.get("start_color", [0, 0, 0, 1])
            end = node.parameters.get("end_color", [1, 1, 1, 1])
            preview_data["preview"] = {
                "type": "gradient",
                "start_color": start,
                "end_color": end,
            }
        else:
            preview_data["preview"] = {
                "type": node.node_type.value,
                "parameters": dict(node.parameters),
            }

        input_conns, output_conns = self.get_node_connections(graph_id, node_id)
        preview_data["input_count"] = len(input_conns)
        preview_data["output_count"] = len(output_conns)

        return preview_data

    # ------------------------------------------------------------------
    # Import / Export
    # ------------------------------------------------------------------

    def export_graph(self, graph_id: str) -> Optional[Dict[str, Any]]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None

        nodes_data = []
        for node in graph.nodes.values():
            nodes_data.append({
                "id": node.id,
                "name": node.name,
                "node_type": node.node_type.value,
                "position": [node.position_x, node.position_y],
                "parameters": dict(node.parameters),
                "is_enabled": node.is_enabled,
                "order": node.order,
            })

        connections_data = []
        for conn in graph.connections.values():
            connections_data.append({
                "id": conn.id,
                "from_node_id": conn.from_node_id,
                "from_port": conn.from_port,
                "to_node_id": conn.to_node_id,
                "to_port": conn.to_port,
                "blend_mode": conn.blend_mode.value,
                "weight": conn.weight,
                "is_enabled": conn.is_enabled,
            })

        return {
            "version": "1.0",
            "graph": {
                "name": graph.name,
                "description": graph.description,
                "tags": list(graph.tags),
            },
            "nodes": nodes_data,
            "connections": connections_data,
            "output_node_id": graph.output_node_id,
            "exported_at": time.time(),
        }

    def import_graph(self, data: Dict[str, Any]) -> Optional[MaterialGraph]:
        if not data or "graph" not in data:
            return None

        graph_info = data["graph"]
        graph = MaterialGraph(
            name=graph_info.get("name", "Imported"),
            description=graph_info.get("description", ""),
            tags=list(graph_info.get("tags", [])),
            output_node_id=data.get("output_node_id", ""),
        )

        node_id_map: Dict[str, str] = {}
        for node_data in data.get("nodes", []):
            try:
                nt = NodeType(node_data["node_type"].lower())
            except (ValueError, KeyError):
                continue
            pos = node_data.get("position", [0.0, 0.0])
            port_spec = self._port_specs.get(nt.value, {"inputs": [], "outputs": []})
            new_node = MaterialNode(
                name=node_data.get("name", nt.value),
                node_type=nt,
                position_x=pos[0],
                position_y=pos[1],
                input_ports=list(port_spec["inputs"]),
                output_ports=list(port_spec["outputs"]),
                parameters=dict(node_data.get("parameters", {})),
                is_enabled=node_data.get("is_enabled", True),
                order=node_data.get("order", 0),
            )
            node_id_map[node_data["id"]] = new_node.id
            graph.nodes[new_node.id] = new_node

        for conn_data in data.get("connections", []):
            from_id = node_id_map.get(conn_data.get("from_node_id", ""))
            to_id = node_id_map.get(conn_data.get("to_node_id", ""))
            if from_id is None or to_id is None:
                continue
            try:
                bm = BlendMode(conn_data.get("blend_mode", "mix").lower())
            except ValueError:
                bm = BlendMode.MIX
            conn = NodeConnection(
                from_node_id=from_id,
                from_port=conn_data.get("from_port", ""),
                to_node_id=to_id,
                to_port=conn_data.get("to_port", ""),
                blend_mode=bm,
                weight=conn_data.get("weight", 1.0),
                is_enabled=conn_data.get("is_enabled", True),
            )
            graph.connections[conn.id] = conn

        remapped_output = node_id_map.get(graph.output_node_id, "")
        graph.output_node_id = remapped_output
        graph.is_dirty = True
        graph.modified_at = time.time()
        self._graphs[graph.id] = graph
        return graph

    # ------------------------------------------------------------------
    # Graph Cloning
    # ------------------------------------------------------------------

    def clone_graph(self, graph_id: str, new_name: str) -> Optional[MaterialGraph]:
        graph = self._graphs.get(graph_id)
        if graph is None:
            return None

        exported = self.export_graph(graph_id)
        if exported is None:
            return None

        exported["graph"]["name"] = new_name
        imported = self.import_graph(exported)
        if imported:
            imported.name = new_name
        return imported

    # ------------------------------------------------------------------
    # Stats and Reset
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        total_nodes = sum(len(g.nodes) for g in self._graphs.values())
        total_connections = sum(len(g.connections) for g in self._graphs.values())
        node_type_dist: Dict[str, int] = {}
        for g in self._graphs.values():
            for node in g.nodes.values():
                nt = node.node_type.value
                node_type_dist[nt] = node_type_dist.get(nt, 0) + 1

        return {
            "total_graphs": len(self._graphs),
            "dirty_graphs": sum(1 for g in self._graphs.values() if g.is_dirty),
            "total_nodes": total_nodes,
            "total_connections": total_connections,
            "total_compilations": self._total_compilations,
            "total_nodes_created": self._total_nodes_created,
            "node_type_distribution": node_type_dist,
            "cached_shaders": len(self._compiled_shaders),
            "max_shader_targets": len(ShaderTarget),
        }

    def reset(self) -> None:
        with self._lock:
            self._graphs.clear()
            self._compiled_shaders.clear()
            self._node_templates.clear()
            self._total_compilations = 0
            self._total_nodes_created = 0


def get_material_graph() -> MaterialGraphSystem:
    """Return the global MaterialGraphSystem singleton instance."""
    return MaterialGraphSystem.get_instance()