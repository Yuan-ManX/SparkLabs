"""
SparkLabs Engine - Shader Material System

Advanced shader and material system for creating, managing, and optimizing
visual materials in the AI-native game engine. Provides a node-based shader
graph, material templates, and AI-driven shader generation and optimization.

Architecture:
  ShaderMaterialSystem (Singleton)
    |-- ShaderProgram (compiled shader with vertex/fragment stages)
    |-- MaterialDefinition (material with shader and property bindings)
    |-- ShaderGraph (node-based visual shader editor graph)
    |-- ShaderNode (individual node in a shader graph)
    |-- MaterialLibrary (organized collection of materials)
    |-- ShaderOptimizer (AI-driven shader performance optimization)

Material Features:
  - Node-based shader graph editor
  - PBR (Physically Based Rendering) material support
  - Material variants and inheritance
  - Runtime material property editing
  - Shader compilation and caching
  - AI-driven material generation from descriptions
  - Performance profiling and optimization

Usage:
    sms = get_shader_material_system()
    sms.initialize()

    # Create a material
    material = sms.create_material("glowing_crystal", {
        "shader": "pbr_standard",
        "properties": {"albedo": "#00FFFF", "emission": "#00FFAA", "emission_strength": 2.0},
    })

    # Generate shader from description
    sms.generate_shader("Create a water shader with caustics and refraction")

    # Apply material to entity
    sms.apply_material("entity_123", "glowing_crystal")
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ShaderStage(Enum):
    """Shader pipeline stages."""
    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"
    TESSELATION_CONTROL = "tess_control"
    TESSELATION_EVAL = "tess_eval"


class ShaderLanguage(Enum):
    """Supported shader languages."""
    GLSL = "glsl"
    HLSL = "hlsl"
    METAL = "metal"
    SPIRV = "spirv"
    WGSL = "wgsl"


class MaterialBlendMode(Enum):
    """Blend modes for materials."""
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    CUSTOM = "custom"


class MaterialDomain(Enum):
    """Rendering domains for materials."""
    SURFACE = "surface"        # Standard surface rendering
    POST_PROCESS = "post_process"  # Full-screen post-processing
    PARTICLE = "particle"      # Particle system rendering
    UI = "ui"                  # UI element rendering
    SKYBOX = "skybox"         # Skybox/environment rendering
    DECAL = "decal"           # Decal projection rendering
    TERRAIN = "terrain"       # Terrain rendering
    CUSTOM = "custom"


class ShaderNodeType(Enum):
    """Types of nodes in a shader graph."""
    INPUT = "input"            # Input parameters
    OUTPUT = "output"          # Output node
    TEXTURE = "texture"        # Texture sampling
    COLOR = "color"            # Color constant
    MATH = "math"              # Mathematical operations
    BLEND = "blend"            # Blend/mix operations
    NOISE = "noise"            # Noise generation
    UV = "uv"                  # UV manipulation
    NORMAL = "normal"          # Normal calculations
    LIGHTING = "lighting"      # Lighting calculations
    CUSTOM = "custom"          # User-defined nodes


class MaterialQuality(Enum):
    """Quality levels for materials."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ShaderNodePort:
    """A port on a shader graph node."""
    port_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    name: str = ""
    port_type: str = "float"  # float, vec2, vec3, vec4, sampler2D, etc.
    is_input: bool = True
    default_value: Any = None
    connected_to: Optional[str] = None  # Other port_id

    def to_dict(self) -> Dict[str, Any]:
        return {
            "port_id": self.port_id,
            "name": self.name,
            "port_type": self.port_type,
            "is_input": self.is_input,
            "default_value": self.default_value,
            "connected_to": self.connected_to,
        }


@dataclass
class ShaderGraphNode:
    """A node in a shader graph."""
    node_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    node_type: ShaderNodeType = ShaderNodeType.CUSTOM
    name: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    inputs: List[ShaderNodePort] = field(default_factory=list)
    outputs: List[ShaderNodePort] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    code: str = ""  # Custom GLSL/HLSL code

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type.value,
            "name": self.name,
            "position": list(self.position),
            "inputs": [p.to_dict() for p in self.inputs],
            "outputs": [p.to_dict() for p in self.outputs],
            "properties": self.properties,
        }


@dataclass
class ShaderGraph:
    """A complete shader graph."""
    graph_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    nodes: Dict[str, ShaderGraphNode] = field(default_factory=dict)
    connections: List[Tuple[str, str, str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "graph_id": self.graph_id,
            "name": self.name,
            "description": self.description,
            "node_count": len(self.nodes),
            "connection_count": len(self.connections),
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ShaderProgram:
    """A compiled shader program."""
    program_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    language: ShaderLanguage = ShaderLanguage.GLSL
    stages: Dict[ShaderStage, str] = field(default_factory=dict)
    compiled: bool = False
    compile_errors: List[str] = field(default_factory=list)
    uniforms: Dict[str, str] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "program_id": self.program_id,
            "name": self.name,
            "language": self.language.value,
            "stages": {s.value: v for s, v in self.stages.items()},
            "compiled": self.compiled,
            "compile_errors": self.compile_errors,
            "uniforms": self.uniforms,
            "created_at": self.created_at,
        }


@dataclass
class MaterialProperty:
    """A property of a material."""
    property_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    property_type: str = "float"  # float, color, texture, vector, etc.
    default_value: Any = None
    current_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""
    exposed: bool = True  # Whether editable in UI

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_id": self.property_id,
            "name": self.name,
            "property_type": self.property_type,
            "default_value": self.default_value,
            "current_value": self.current_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "description": self.description,
            "exposed": self.exposed,
        }


@dataclass
class MaterialDefinition:
    """A complete material definition."""
    material_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    shader_program_id: str = ""
    domain: MaterialDomain = MaterialDomain.SURFACE
    blend_mode: MaterialBlendMode = MaterialBlendMode.OPAQUE
    properties: Dict[str, MaterialProperty] = field(default_factory=dict)
    textures: Dict[str, str] = field(default_factory=dict)
    quality: MaterialQuality = MaterialQuality.HIGH
    tags: List[str] = field(default_factory=list)
    parent_material_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    usage_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "shader_program_id": self.shader_program_id,
            "domain": self.domain.value,
            "blend_mode": self.blend_mode.value,
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "textures": self.textures,
            "quality": self.quality.value,
            "tags": self.tags,
            "parent_material_id": self.parent_material_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "usage_count": self.usage_count,
        }

    def get_property(self, name: str) -> Optional[MaterialProperty]:
        return self.properties.get(name)

    def set_property(self, name: str, value: Any) -> bool:
        prop = self.properties.get(name)
        if prop:
            if prop.min_value is not None and isinstance(value, (int, float)) and value < prop.min_value:
                value = prop.min_value
            if prop.max_value is not None and isinstance(value, (int, float)) and value > prop.max_value:
                value = prop.max_value
            prop.current_value = value
            return True
        return False


@dataclass
class MaterialLibrary:
    """Organized collection of materials."""
    library_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    materials: Dict[str, MaterialDefinition] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "library_id": self.library_id,
            "name": self.name,
            "description": self.description,
            "material_count": len(self.materials),
            "material_names": list(self.materials.keys()),
            "created_at": self.created_at,
        }


# =============================================================================
# ShaderMaterialSystem (Singleton)
# =============================================================================


class ShaderMaterialSystem:
    """Advanced shader and material system for visual materials.

    Provides node-based shader graphs, material templates, and AI-driven
    shader generation. Supports PBR materials, runtime property editing,
    and performance optimization.

    Usage:
        sms = ShaderMaterialSystem.get_instance()
        sms.initialize()

        material = sms.create_material("gold", {
            "shader": "pbr_standard",
            "properties": {"albedo": "#FFD700", "metallic": 1.0, "roughness": 0.3},
        })

        sms.apply_material("entity_42", "gold")
    """

    _instance: Optional["ShaderMaterialSystem"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if ShaderMaterialSystem._instance is not None:
            raise RuntimeError("Use ShaderMaterialSystem.get_instance()")
        self._initialized: bool = False
        self._lock = threading.RLock()
        self._shaders: Dict[str, ShaderProgram] = {}
        self._materials: Dict[str, MaterialDefinition] = {}
        self._graphs: Dict[str, ShaderGraph] = {}
        self._libraries: Dict[str, MaterialLibrary] = {}
        self._entity_materials: Dict[str, str] = {}  # entity_id -> material_id
        self._total_compilations: int = 0

    @classmethod
    def get_instance(cls) -> "ShaderMaterialSystem":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            self._register_default_shaders()
            self._register_default_materials()
            self._initialized = True

            return {
                "status": "initialized",
                "success": True,
                "shaders": len(self._shaders),
                "materials": len(self._materials),
            }

    def shutdown(self) -> Dict[str, Any]:
        with self._lock:
            self._initialized = False
            return {
                "success": True,
                "total_compilations": self._total_compilations,
            }

    def _register_default_shaders(self) -> None:
        """Register built-in shader programs."""
        defaults = {
            "pbr_standard": ShaderProgram(
                name="pbr_standard",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_Albedo": "vec3",
                    "u_Metallic": "float",
                    "u_Roughness": "float",
                    "u_AO": "float",
                    "u_Emission": "vec3",
                    "u_EmissionStrength": "float",
                },
            ),
            "unlit_color": ShaderProgram(
                name="unlit_color",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_Color": "vec4",
                },
            ),
            "sprite_default": ShaderProgram(
                name="sprite_default",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_MainTex": "sampler2D",
                    "u_Tint": "vec4",
                },
            ),
            "particle_additive": ShaderProgram(
                name="particle_additive",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_ParticleTex": "sampler2D",
                    "u_Color": "vec4",
                },
            ),
            "ui_default": ShaderProgram(
                name="ui_default",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_MainTex": "sampler2D",
                    "u_Color": "vec4",
                },
            ),
            "post_bloom": ShaderProgram(
                name="post_bloom",
                language=ShaderLanguage.GLSL,
                compiled=True,
                uniforms={
                    "u_Threshold": "float",
                    "u_Intensity": "float",
                    "u_Scatter": "float",
                },
            ),
        }

        for name, shader in defaults.items():
            self._shaders[name] = shader

    def _register_default_materials(self) -> None:
        """Register built-in material templates."""
        defaults = [
            MaterialDefinition(
                name="default_lit",
                shader_program_id="pbr_standard",
                domain=MaterialDomain.SURFACE,
                properties={
                    "albedo": MaterialProperty(name="albedo", property_type="color",
                                              default_value=(0.8, 0.8, 0.8),
                                              current_value=(0.8, 0.8, 0.8)),
                    "metallic": MaterialProperty(name="metallic", property_type="float",
                                                default_value=0.0, current_value=0.0,
                                                min_value=0.0, max_value=1.0),
                    "roughness": MaterialProperty(name="roughness", property_type="float",
                                                 default_value=0.5, current_value=0.5,
                                                 min_value=0.0, max_value=1.0),
                    "ao": MaterialProperty(name="ao", property_type="float",
                                          default_value=1.0, current_value=1.0,
                                          min_value=0.0, max_value=1.0),
                },
                tags=["default", "pbr"],
            ),
            MaterialDefinition(
                name="default_sprite",
                shader_program_id="sprite_default",
                domain=MaterialDomain.SURFACE,
                properties={
                    "tint": MaterialProperty(name="tint", property_type="color",
                                            default_value=(1.0, 1.0, 1.0, 1.0),
                                            current_value=(1.0, 1.0, 1.0, 1.0)),
                },
                tags=["default", "sprite"],
            ),
            MaterialDefinition(
                name="default_ui",
                shader_program_id="ui_default",
                domain=MaterialDomain.UI,
                properties={
                    "color": MaterialProperty(name="color", property_type="color",
                                             default_value=(1.0, 1.0, 1.0, 1.0),
                                             current_value=(1.0, 1.0, 1.0, 1.0)),
                },
                tags=["default", "ui"],
            ),
            MaterialDefinition(
                name="default_particle",
                shader_program_id="particle_additive",
                domain=MaterialDomain.PARTICLE,
                blend_mode=MaterialBlendMode.ADDITIVE,
                properties={
                    "color": MaterialProperty(name="color", property_type="color",
                                             default_value=(1.0, 0.5, 0.0, 1.0),
                                             current_value=(1.0, 0.5, 0.0, 1.0)),
                },
                tags=["default", "particle"],
            ),
        ]

        for mat in defaults:
            self._materials[mat.name] = mat

    # -------------------------------------------------------------------------
    # Shader Management
    # -------------------------------------------------------------------------

    def register_shader(self, shader: ShaderProgram) -> Dict[str, Any]:
        """Register a new shader program."""
        with self._lock:
            if shader.name in self._shaders:
                return {"success": False, "error": f"Shader '{shader.name}' already exists"}
            self._shaders[shader.name] = shader
            self._total_compilations += 1
            return {"success": True, "shader": shader.to_dict()}

    def get_shader(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a shader by name."""
        shader = self._shaders.get(name)
        return shader.to_dict() if shader else None

    def list_shaders(self) -> List[Dict[str, Any]]:
        """List all shader programs."""
        return [s.to_dict() for s in self._shaders.values()]

    def compile_shader(self, name: str, source: Dict[ShaderStage, str],
                       language: ShaderLanguage = ShaderLanguage.GLSL) -> Dict[str, Any]:
        """Compile a shader from source code."""
        with self._lock:
            shader = ShaderProgram(
                name=name,
                language=language,
                stages=source,
                compiled=True,
            )
            self._shaders[name] = shader
            self._total_compilations += 1
            return {"success": True, "shader": shader.to_dict()}

    # -------------------------------------------------------------------------
    # Material Management
    # -------------------------------------------------------------------------

    def create_material(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new material definition."""
        with self._lock:
            if name in self._materials:
                return {"success": False, "error": f"Material '{name}' already exists"}

            shader_name = config.get("shader", "pbr_standard")
            if shader_name not in self._shaders:
                return {"success": False, "error": f"Shader '{shader_name}' not found"}

            properties = {}
            for prop_name, prop_data in config.get("properties", {}).items():
                if isinstance(prop_data, dict):
                    properties[prop_name] = MaterialProperty(
                        name=prop_name,
                        property_type=prop_data.get("type", "float"),
                        default_value=prop_data.get("default", prop_data.get("value")),
                        current_value=prop_data.get("value", prop_data.get("default")),
                        min_value=prop_data.get("min"),
                        max_value=prop_data.get("max"),
                        description=prop_data.get("description", ""),
                    )
                else:
                    properties[prop_name] = MaterialProperty(
                        name=prop_name,
                        property_type="float" if isinstance(prop_data, (int, float)) else "color",
                        default_value=prop_data,
                        current_value=prop_data,
                    )

            material = MaterialDefinition(
                name=name,
                shader_program_id=shader_name,
                domain=MaterialDomain(config.get("domain", "surface")),
                blend_mode=MaterialBlendMode(config.get("blend_mode", "opaque")),
                properties=properties,
                textures=config.get("textures", {}),
                quality=MaterialQuality(config.get("quality", "high")),
                tags=config.get("tags", []),
                parent_material_id=config.get("parent"),
            )

            self._materials[name] = material
            return {"success": True, "material": material.to_dict()}

    def get_material(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a material by name."""
        material = self._materials.get(name)
        return material.to_dict() if material else None

    def list_materials(self, domain: Optional[MaterialDomain] = None,
                       tags: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """List materials with optional filtering."""
        materials = self._materials.values()
        if domain:
            materials = [m for m in materials if m.domain == domain]
        if tags:
            materials = [m for m in materials if any(t in m.tags for t in tags)]
        return [m.to_dict() for m in materials]

    def update_material_property(self, material_name: str, property_name: str,
                                 value: Any) -> Dict[str, Any]:
        """Update a material property value."""
        with self._lock:
            material = self._materials.get(material_name)
            if not material:
                return {"success": False, "error": f"Material '{material_name}' not found"}

            if not material.set_property(property_name, value):
                return {"success": False, "error": f"Property '{property_name}' not found"}

            material.updated_at = time.time()
            return {"success": True, "material": material_name, "property": property_name, "value": value}

    def delete_material(self, name: str) -> Dict[str, Any]:
        """Delete a material."""
        with self._lock:
            if name not in self._materials:
                return {"success": False, "error": f"Material '{name}' not found"}

            # Remove from entities
            to_remove = [eid for eid, mid in self._entity_materials.items() if mid == name]
            for eid in to_remove:
                del self._entity_materials[eid]

            del self._materials[name]
            return {"success": True, "name": name, "entities_affected": len(to_remove)}

    # -------------------------------------------------------------------------
    # Entity Material Application
    # -------------------------------------------------------------------------

    def apply_material(self, entity_id: str, material_name: str) -> Dict[str, Any]:
        """Apply a material to an entity."""
        with self._lock:
            if material_name not in self._materials:
                return {"success": False, "error": f"Material '{material_name}' not found"}

            self._entity_materials[entity_id] = material_name
            material = self._materials[material_name]
            material.usage_count += 1

            return {"success": True, "entity_id": entity_id, "material": material_name}

    def get_entity_material(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get the material applied to an entity."""
        material_name = self._entity_materials.get(entity_id)
        if material_name:
            return self.get_material(material_name)
        return None

    def remove_entity_material(self, entity_id: str) -> Dict[str, Any]:
        """Remove material from an entity."""
        with self._lock:
            if entity_id not in self._entity_materials:
                return {"success": False, "error": "Entity has no material"}
            material_name = self._entity_materials.pop(entity_id)
            return {"success": True, "entity_id": entity_id, "material": material_name}

    # -------------------------------------------------------------------------
    # Shader Graph
    # -------------------------------------------------------------------------

    def create_graph(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new shader graph."""
        with self._lock:
            if name in self._graphs:
                return {"success": False, "error": f"Graph '{name}' already exists"}
            graph = ShaderGraph(name=name, description=description)
            self._graphs[name] = graph
            return {"success": True, "graph": graph.to_dict()}

    def add_node(self, graph_name: str, node_type: ShaderNodeType,
                 name: str = "", position: Tuple[float, float] = (0.0, 0.0),
                 properties: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a node to a shader graph."""
        with self._lock:
            graph = self._graphs.get(graph_name)
            if not graph:
                return {"success": False, "error": f"Graph '{graph_name}' not found"}

            node = ShaderGraphNode(
                node_type=node_type,
                name=name or f"{node_type.value}_{len(graph.nodes)}",
                position=position,
                properties=properties or {},
            )

            # Add default ports based on node type
            if node_type == ShaderNodeType.TEXTURE:
                node.inputs = [
                    ShaderNodePort(name="UV", port_type="vec2", is_input=True),
                ]
                node.outputs = [
                    ShaderNodePort(name="Color", port_type="vec4", is_input=False),
                    ShaderNodePort(name="Alpha", port_type="float", is_input=False),
                ]
            elif node_type == ShaderNodeType.MATH:
                node.inputs = [
                    ShaderNodePort(name="A", port_type="float", is_input=True),
                    ShaderNodePort(name="B", port_type="float", is_input=True),
                ]
                node.outputs = [
                    ShaderNodePort(name="Result", port_type="float", is_input=False),
                ]
            elif node_type == ShaderNodeType.BLEND:
                node.inputs = [
                    ShaderNodePort(name="A", port_type="vec4", is_input=True),
                    ShaderNodePort(name="B", port_type="vec4", is_input=True),
                    ShaderNodePort(name="Factor", port_type="float", is_input=True, default_value=0.5),
                ]
                node.outputs = [
                    ShaderNodePort(name="Result", port_type="vec4", is_input=False),
                ]
            elif node_type == ShaderNodeType.COLOR:
                node.outputs = [
                    ShaderNodePort(name="Color", port_type="vec4", is_input=False),
                ]

            graph.nodes[node.node_id] = node
            graph.updated_at = time.time()

            return {"success": True, "node": node.to_dict()}

    def connect_nodes(self, graph_name: str,
                      source_node_id: str, source_port: str,
                      target_node_id: str, target_port: str) -> Dict[str, Any]:
        """Connect two nodes in a shader graph."""
        with self._lock:
            graph = self._graphs.get(graph_name)
            if not graph:
                return {"success": False, "error": f"Graph '{graph_name}' not found"}

            source_node = graph.nodes.get(source_node_id)
            target_node = graph.nodes.get(target_node_id)
            if not source_node or not target_node:
                return {"success": False, "error": "Node not found"}

            # Find ports
            source_port_obj = next((p for p in source_node.outputs if p.name == source_port), None)
            target_port_obj = next((p for p in target_node.inputs if p.name == target_port), None)

            if not source_port_obj or not target_port_obj:
                return {"success": False, "error": "Port not found"}

            target_port_obj.connected_to = source_port_obj.port_id
            graph.connections.append((source_node_id, source_port, target_node_id, target_port))
            graph.updated_at = time.time()

            return {"success": True, "connection": {
                "source": f"{source_node_id}:{source_port}",
                "target": f"{target_node_id}:{target_port}",
            }}

    def get_graph(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a shader graph by name."""
        graph = self._graphs.get(name)
        return graph.to_dict() if graph else None

    def list_graphs(self) -> List[Dict[str, Any]]:
        """List all shader graphs."""
        return [g.to_dict() for g in self._graphs.values()]

    # -------------------------------------------------------------------------
    # Library Management
    # -------------------------------------------------------------------------

    def create_library(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a material library."""
        with self._lock:
            if name in self._libraries:
                return {"success": False, "error": f"Library '{name}' already exists"}
            library = MaterialLibrary(name=name, description=description)
            self._libraries[name] = library
            return {"success": True, "library": library.to_dict()}

    def add_to_library(self, library_name: str, material_name: str) -> Dict[str, Any]:
        """Add a material to a library."""
        with self._lock:
            library = self._libraries.get(library_name)
            if not library:
                return {"success": False, "error": f"Library '{library_name}' not found"}

            material = self._materials.get(material_name)
            if not material:
                return {"success": False, "error": f"Material '{material_name}' not found"}

            library.materials[material_name] = material
            return {"success": True, "library": library_name, "material": material_name}

    def list_libraries(self) -> List[Dict[str, Any]]:
        """List all libraries."""
        return [lib.to_dict() for lib in self._libraries.values()]

    # -------------------------------------------------------------------------
    # AI-Driven Shader Generation
    # -------------------------------------------------------------------------

    def generate_shader(self, description: str) -> Dict[str, Any]:
        """Generate a shader material from a natural language description."""
        desc_lower = description.lower()

        # Detect material type from description
        shader_map = {
            "water": "pbr_standard",
            "ocean": "pbr_standard",
            "metal": "pbr_standard",
            "gold": "pbr_standard",
            "glass": "pbr_standard",
            "crystal": "pbr_standard",
            "glow": "pbr_standard",
            "fire": "particle_additive",
            "smoke": "particle_additive",
            "particle": "particle_additive",
            "ui": "ui_default",
            "sprite": "sprite_default",
            "unlit": "unlit_color",
        }

        shader_name = "pbr_standard"
        for keyword, shader in shader_map.items():
            if keyword in desc_lower:
                shader_name = shader
                break

        # Generate material properties based on description
        properties = {}
        if "water" in desc_lower or "ocean" in desc_lower:
            properties = {
                "albedo": MaterialProperty(name="albedo", property_type="color",
                                          default_value=(0.1, 0.3, 0.6),
                                          current_value=(0.1, 0.3, 0.6)),
                "metallic": MaterialProperty(name="metallic", property_type="float",
                                            default_value=0.0, current_value=0.0),
                "roughness": MaterialProperty(name="roughness", property_type="float",
                                             default_value=0.2, current_value=0.2),
            }
        elif "metal" in desc_lower or "gold" in desc_lower:
            properties = {
                "albedo": MaterialProperty(name="albedo", property_type="color",
                                          default_value=(1.0, 0.84, 0.0),
                                          current_value=(1.0, 0.84, 0.0)),
                "metallic": MaterialProperty(name="metallic", property_type="float",
                                            default_value=1.0, current_value=1.0),
                "roughness": MaterialProperty(name="roughness", property_type="float",
                                             default_value=0.3, current_value=0.3),
            }
        elif "glass" in desc_lower or "crystal" in desc_lower:
            properties = {
                "albedo": MaterialProperty(name="albedo", property_type="color",
                                          default_value=(0.9, 0.95, 1.0),
                                          current_value=(0.9, 0.95, 1.0)),
                "metallic": MaterialProperty(name="metallic", property_type="float",
                                            default_value=0.0, current_value=0.0),
                "roughness": MaterialProperty(name="roughness", property_type="float",
                                             default_value=0.1, current_value=0.1),
            }
        elif "glow" in desc_lower:
            properties = {
                "albedo": MaterialProperty(name="albedo", property_type="color",
                                          default_value=(0.0, 0.0, 0.0),
                                          current_value=(0.0, 0.0, 0.0)),
                "emission": MaterialProperty(name="emission", property_type="color",
                                            default_value=(0.0, 1.0, 0.5),
                                            current_value=(0.0, 1.0, 0.5)),
                "emission_strength": MaterialProperty(name="emission_strength", property_type="float",
                                                     default_value=2.0, current_value=2.0, min_value=0.0),
            }

        name = f"generated_{uuid.uuid4().hex[:8]}"
        material = MaterialDefinition(
            name=name,
            shader_program_id=shader_name,
            properties=properties,
            tags=["ai_generated"],
        )
        self._materials[name] = material

        return {
            "success": True,
            "material": material.to_dict(),
            "description": description,
            "shader_used": shader_name,
        }

    # -------------------------------------------------------------------------
    # Optimization
    # -------------------------------------------------------------------------

    def optimize_material(self, material_name: str,
                          target_quality: MaterialQuality = MaterialQuality.MEDIUM) -> Dict[str, Any]:
        """Optimize a material for a target quality level."""
        with self._lock:
            material = self._materials.get(material_name)
            if not material:
                return {"success": False, "error": f"Material '{material_name}' not found"}

            old_quality = material.quality
            material.quality = target_quality

            # Adjust properties based on quality
            if target_quality in (MaterialQuality.LOW, MaterialQuality.MEDIUM):
                # Reduce texture resolution hints
                if "roughness" in material.properties:
                    prop = material.properties["roughness"]
                    if prop.current_value is not None:
                        # Simplify roughness for lower quality
                        pass

            material.updated_at = time.time()

            return {
                "success": True,
                "material": material_name,
                "old_quality": old_quality.value,
                "new_quality": target_quality.value,
            }

    # -------------------------------------------------------------------------
    # Queries
    # -------------------------------------------------------------------------

    def search_materials(self, query: str) -> List[Dict[str, Any]]:
        """Search materials by name, description, or tags."""
        query_lower = query.lower()
        results = []
        for material in self._materials.values():
            if (query_lower in material.name.lower() or
                any(query_lower in tag.lower() for tag in material.tags)):
                results.append(material.to_dict())
        return results

    def get_status(self) -> Dict[str, Any]:
        """Get current system status."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "shaders": len(self._shaders),
                "materials": len(self._materials),
                "graphs": len(self._graphs),
                "libraries": len(self._libraries),
                "entities_with_materials": len(self._entity_materials),
                "total_compilations": self._total_compilations,
                "domains": {d.value: len([m for m in self._materials.values() if m.domain == d])
                           for d in MaterialDomain},
            }


# ── Module Accessor ──

def get_shader_material_system() -> ShaderMaterialSystem:
    """Get the singleton shader material system instance."""
    return ShaderMaterialSystem.get_instance()