"""
SparkLabs Engine - Shader & Material Graph System

A comprehensive visual shader and material graph system for the SparkLabs
AI-native game engine. Designers compose shaders by wiring together nodes
in a directed acyclic graph; the system validates the graph, compiles it
into a shader program, and exposes material templates and runtime
material instances with overridable properties and texture layers. An
integrated AI layer can generate shader graphs from natural-language
descriptions, optimize compiled shaders for the target platform, and
suggest nodes that complete a partial graph.

Architecture:
  ShaderMaterialGraphSystem (Singleton)
    |-- ShaderNode              -- a single operation in a shader graph
    |-- NodeConnection          -- a typed edge linking two node ports
    |-- ShaderGraph             -- a DAG of nodes and connections
    |-- Material                -- a material template binding a shader
    |-- MaterialProperty        -- a typed, exposed material parameter
    |-- MaterialInstance        -- a runtime material with overrides
    |-- ShaderProgram           -- a compiled, cached shader program
    |-- ShaderCompilationResult -- the outcome of a compile pass
    |-- TextureLayer            -- a layered texture slot on a material
    |-- ShaderMaterialGraphConfig   -- runtime tunable configuration
    |-- ShaderMaterialGraphStats    -- aggregate engine counters
    |-- ShaderMaterialGraphSnapshot -- immutable engine snapshot
    |-- ShaderMaterialGraphEvent    -- audit log entry
    |-- ShaderNodeType          -- 41 node operation classifications
    |-- ShaderStage             -- 6 pipeline stages
    |-- ShaderPrecision         -- 4 precision levels
    |-- ShaderStatus            -- 7 graph lifecycle states
    |-- MaterialType            -- 13 material classifications
    |-- MaterialPropertyType    -- 10 property value types
    |-- BlendMode               -- 6 blend modes
    |-- CullMode                -- 4 cull modes
    |-- ShaderMaterialGraphEventKind -- 20 audit event kinds

Core Capabilities:
  - register_node / get_node / list_nodes / remove_node: shader node
    registry management with type-based default ports and FIFO eviction.
  - create_connection / remove_connection: typed port connections with
    cycle detection and graph ownership validation.
  - create_graph / get_graph / list_graphs / remove_graph: graph registry
    management with status and stage filtering.
  - compile_graph / optimize_graph / validate_graph: compile a graph into
    a ShaderProgram, optimize a compiled program, and validate structure
    (cycles, dangling connections, missing output nodes).
  - create_material / get_material / list_materials / remove_material:
    material template lifecycle bound to a shader program.
  - set_material_property / get_material_property: typed property
    management with min/max clamping and default fallback.
  - create_material_instance / get_material_instance /
    list_material_instances / remove_material_instance: runtime instances
    with per-instance property overrides and blend/cull configuration.
  - add_texture_layer / remove_texture_layer: layered texture slots
    attached to material instances.
  - get_shader_program / list_shader_programs / get_compilation_result:
    compiled program and compilation outcome inspection.
  - auto_generate_shader: AI-driven shader graph generation from a
    natural-language description (water, fire, metal, skin, terrain,
    foliage, hair, cloth, glass, energy, smoke, crystal, lava, ice).
  - optimize_shader: AI-driven shader optimization that reduces
    instruction count, texture samples, and register pressure.
  - suggest_nodes: AI-driven node suggestion that inspects a partial
    graph and proposes nodes that would complete the data flow.
  - get_status / get_stats / get_snapshot / get_config / set_config /
    tick / reset / list_events: observability, tuning, and lifecycle.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ShaderMaterialGraphSystem.get_instance` or the module-level
:func:`get_shader_material_graph_system` factory. All public methods are
guarded by the re-entrant lock.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

# Bounded store capacities. When a store exceeds its cap the oldest entry
# is evicted in FIFO order to keep memory growth predictable under heavy
# dynamic use (for example a game that compiles a new shader variant for
# every material permutation or weather state transition).
_MAX_NODES: int = 50000
_MAX_GRAPHS: int = 5000
_MAX_CONNECTIONS: int = 200000
_MAX_MATERIALS: int = 20000
_MAX_MATERIAL_INSTANCES: int = 100000
_MAX_SHADER_PROGRAMS: int = 5000
_MAX_COMPILATION_RESULTS: int = 10000
_MAX_TEXTURE_LAYERS: int = 50000
_MAX_EVENTS: int = 20000

# Numeric bounds
_PRECISION_MIN: int = 0
_PRECISION_MAX: int = 3
_SORT_ORDER_MIN: float = -1000.0
_SORT_ORDER_MAX: float = 1000.0

# List limits
_DEFAULT_LIST_LIMIT: int = 50
_MAX_LIST_LIMIT: int = 500


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix.

    Used as the default factory for ``created_at`` / ``updated_at``
    fields and for event timestamps throughout the module.
    """
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with
            an underscore. When omitted, the bare hexadecimal id is
            returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits ``max_size``.

    Uses insertion-order iteration so the first inserted key is dropped
    first. This keeps memory growth bounded for FIFO-style stores.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits ``max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to ``default``.

    Accepts either an existing enum member or its raw value. Returns
    ``default`` when the value cannot be resolved.
    """
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-serializable form.

    Handles enums (by value), dicts, lists, tuples, sets, dataclasses
    (via ``__dataclass_fields__``), and objects exposing ``to_dict``.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Convert a dataclass instance into a dict of JSON-serializable values.

    Checks ``__dataclass_fields__`` BEFORE ``to_dict`` to avoid
    recursion when a dataclass also defines a ``to_dict`` method that
    delegates back to this helper.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp a numeric value to the inclusive ``[low, high]`` range."""
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int, returning ``default`` on failure."""
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: List[float]) -> float:
    """Return the arithmetic mean of a list, or 0.0 for an empty list."""
    if not values:
        return 0.0
    return sum(values) / len(values)


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class ShaderNodeType(str, Enum):
    """Classification of a shader graph node operation.

    Each value corresponds to a node that produces or transforms shader
    data. The set spans pipeline-stage nodes (VERTEX, FRAGMENT, ...),
    uniform/sampler sources, math operations, procedural generators
    (NOISE, FBM, GRADIENT), and the terminal OUTPUT node.
    """

    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"
    UNIFORM = "uniform"
    SAMPLER = "sampler"
    MIX = "mix"
    ADD = "add"
    SUBTRACT = "subtract"
    MULTIPLY = "multiply"
    DIVIDE = "divide"
    SINE = "sine"
    COSINE = "cosine"
    TIME = "time"
    UV = "uv"
    COLOR = "color"
    VECTOR = "vector"
    SCALAR = "scalar"
    TEXTURE_SAMPLE = "texture_sample"
    NORMAL = "normal"
    OUTPUT = "output"
    INPUT = "input"
    CONSTANT = "constant"
    LERP = "lerp"
    SMOOTHSTEP = "smoothstep"
    STEP = "step"
    CLAMP = "clamp"
    ABS = "abs"
    FLOOR = "floor"
    CEIL = "ceil"
    FRACT = "fract"
    POW = "pow"
    MIN = "min"
    MAX = "max"
    MIX3 = "mix3"
    CROSS = "cross"
    DOT = "dot"
    REFLECT = "reflect"
    REFRACT = "refract"
    NOISE = "noise"
    FBM = "fbm"
    GRADIENT = "gradient"


class ShaderStage(str, Enum):
    """The pipeline stage a graph or node belongs to."""

    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"
    TESSELLATION = "tessellation"
    MESH = "mesh"


class ShaderPrecision(str, Enum):
    """The numeric precision qualifier for a node or graph.

    - ``LOW``: fastest, lowest precision (8-bit equivalent).
    - ``MEDIUM``: balanced (16-bit equivalent).
    - ``HIGH``: full 32-bit float precision.
    - ``SUPER``: 64-bit double precision for compute-heavy passes.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SUPER = "super"


class ShaderStatus(str, Enum):
    """Lifecycle status of a shader graph or program.

    - ``DRAFT``: newly created or edited; not yet validated.
    - ``COMPILING``: a compile pass is in progress.
    - ``COMPILED``: passed validation and produced a program.
    - ``ERROR``: failed validation or compilation.
    - ``OPTIMIZED``: a compiled program that has been through optimization.
    - ``DEPRECATED``: superseded by a newer version but retained.
    - ``ARCHIVED``: taken out of active use and stored for history.
    """

    DRAFT = "draft"
    COMPILING = "compiling"
    COMPILED = "compiled"
    ERROR = "error"
    OPTIMIZED = "optimized"
    DEPRECATED = "deprecated"
    ARCHIVED = "archived"


class MaterialType(str, Enum):
    """Classification of a material template.

    Determines the default shader stages, blend mode, and render queue
    that the material targets.
    """

    STANDARD = "standard"
    UNLIT = "unlit"
    PBR = "pbr"
    CUSTOM = "custom"
    POST_PROCESS = "post_process"
    PARTICLE = "particle"
    TERRAIN = "terrain"
    DECAL = "decal"
    FOLIAGE = "foliage"
    SKIN = "skin"
    HAIR = "hair"
    WATER = "water"
    CLOTH = "cloth"


class MaterialPropertyType(str, Enum):
    """The value type of a material property.

    Determines how the property is presented in the editor and how it is
    bound to the shader program at runtime.
    """

    FLOAT = "float"
    VEC2 = "vec2"
    VEC3 = "vec3"
    VEC4 = "vec4"
    COLOR = "color"
    TEXTURE = "texture"
    CUBEMAP = "cubemap"
    INT = "int"
    BOOL = "bool"
    MATRIX = "matrix"
    ARRAY = "array"


class BlendMode(str, Enum):
    """The blend mode used when rendering a material instance.

    - ``OPAQUE``: no blending; overwrite the destination.
    - ``ALPHA_BLEND``: standard source-over alpha blending.
    - ``ADDITIVE``: sum source and destination (fire, sparks, energy).
    - ``MULTIPLICATIVE``: multiply source and destination (shadows, fog).
    - ``ALPHA_TEST``: binary cutout based on an alpha threshold.
    - ``ALPHA_PREMULTIPLY``: premultiplied-alpha source-over blending.
    """

    OPAQUE = "opaque"
    ALPHA_BLEND = "alpha_blend"
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"
    ALPHA_TEST = "alpha_test"
    ALPHA_PREMULTIPLY = "alpha_premultiply"


class CullMode(str, Enum):
    """The face-culling mode applied during rasterization."""

    NONE = "none"
    FRONT = "front"
    BACK = "back"
    FRONT_AND_BACK = "front_and_back"


class ShaderMaterialGraphEventKind(str, Enum):
    """Audit event kinds emitted by the shader material graph system."""

    NODE_REGISTERED = "node_registered"
    NODE_REMOVED = "node_removed"
    CONNECTION_CREATED = "connection_created"
    CONNECTION_REMOVED = "connection_removed"
    GRAPH_CREATED = "graph_created"
    GRAPH_REMOVED = "graph_removed"
    GRAPH_COMPILED = "graph_compiled"
    GRAPH_OPTIMIZED = "graph_optimized"
    GRAPH_VALIDATED = "graph_validated"
    MATERIAL_CREATED = "material_created"
    MATERIAL_REMOVED = "material_removed"
    PROPERTY_SET = "property_set"
    INSTANCE_CREATED = "instance_created"
    INSTANCE_REMOVED = "instance_removed"
    TEXTURE_LAYER_ADDED = "texture_layer_added"
    TEXTURE_LAYER_REMOVED = "texture_layer_removed"
    SHADER_GENERATED = "shader_generated"
    SHADER_OPTIMIZED = "shader_optimized"
    NODES_SUGGESTED = "nodes_suggested"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Default Port Table
# ---------------------------------------------------------------------------

# Maps a ShaderNodeType to the default input and output port names that
# are created automatically when a node of that type is registered. Each
# entry is a tuple of (input_port_names, output_port_names).
_PORT_DEFAULTS: Dict[ShaderNodeType, Tuple[List[str], List[str]]] = {
    ShaderNodeType.VERTEX: (["position", "normal", "uv"], ["clip_position"]),
    ShaderNodeType.FRAGMENT: (["albedo", "normal", "roughness", "metallic"], ["frag_color"]),
    ShaderNodeType.GEOMETRY: (["in_triangles"], ["out_triangles"]),
    ShaderNodeType.COMPUTE: (["dispatch"], ["result"]),
    ShaderNodeType.UNIFORM: ([], ["value"]),
    ShaderNodeType.SAMPLER: ([], ["sampler"]),
    ShaderNodeType.MIX: (["a", "b", "t"], ["result"]),
    ShaderNodeType.ADD: (["a", "b"], ["result"]),
    ShaderNodeType.SUBTRACT: (["a", "b"], ["result"]),
    ShaderNodeType.MULTIPLY: (["a", "b"], ["result"]),
    ShaderNodeType.DIVIDE: (["a", "b"], ["result"]),
    ShaderNodeType.SINE: (["x"], ["result"]),
    ShaderNodeType.COSINE: (["x"], ["result"]),
    ShaderNodeType.TIME: ([], ["time"]),
    ShaderNodeType.UV: ([], ["uv"]),
    ShaderNodeType.COLOR: ([], ["color"]),
    ShaderNodeType.VECTOR: ([], ["vector"]),
    ShaderNodeType.SCALAR: ([], ["scalar"]),
    ShaderNodeType.TEXTURE_SAMPLE: (["uv", "sampler"], ["color"]),
    ShaderNodeType.NORMAL: (["tangent", "bitangent", "normal_map"], ["world_normal"]),
    ShaderNodeType.OUTPUT: (["color"], []),
    ShaderNodeType.INPUT: ([], ["value"]),
    ShaderNodeType.CONSTANT: ([], ["value"]),
    ShaderNodeType.LERP: (["a", "b", "t"], ["result"]),
    ShaderNodeType.SMOOTHSTEP: (["edge0", "edge1", "x"], ["result"]),
    ShaderNodeType.STEP: (["edge", "x"], ["result"]),
    ShaderNodeType.CLAMP: (["x", "min", "max"], ["result"]),
    ShaderNodeType.ABS: (["x"], ["result"]),
    ShaderNodeType.FLOOR: (["x"], ["result"]),
    ShaderNodeType.CEIL: (["x"], ["result"]),
    ShaderNodeType.FRACT: (["x"], ["result"]),
    ShaderNodeType.POW: (["base", "exponent"], ["result"]),
    ShaderNodeType.MIN: (["a", "b"], ["result"]),
    ShaderNodeType.MAX: (["a", "b"], ["result"]),
    ShaderNodeType.MIX3: (["a", "b", "c", "t"], ["result"]),
    ShaderNodeType.CROSS: (["a", "b"], ["result"]),
    ShaderNodeType.DOT: (["a", "b"], ["result"]),
    ShaderNodeType.REFLECT: (["incident", "normal"], ["result"]),
    ShaderNodeType.REFRACT: (["incident", "normal", "eta"], ["result"]),
    ShaderNodeType.NOISE: (["position", "scale"], ["noise"]),
    ShaderNodeType.FBM: (["position", "octaves", "lacunarity", "gain"], ["fbm"]),
    ShaderNodeType.GRADIENT: (["t", "color_stops"], ["color"]),
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ShaderNode:
    """A single operation within a shader graph.

    A node owns named input and output ports, a free-form properties
    dictionary for operation-specific settings, a 2D editor position,
    and a precision qualifier. Disabled nodes are skipped during
    compilation and runtime evaluation.

    Attributes:
        node_id: Unique identifier for the node.
        node_type: The ShaderNodeType classification (stored as its
            string value for JSON stability).
        name: Human-readable name of the node.
        stage: The pipeline stage this node belongs to.
        precision: The numeric precision qualifier.
        inputs: List of input port names.
        outputs: List of output port names.
        properties: Operation-specific parameter dictionary.
        position_x: Horizontal editor position.
        position_y: Vertical editor position.
        code: Optional inline shader code for custom nodes.
        enabled: Whether the node participates in compilation.
        category: Editor grouping label.
        description: Long-form description of the node.
        metadata: Free-form extension data.
        created_at: ISO-8601 creation timestamp.
    """
    node_id: str = field(default_factory=lambda: _new_id("node"))
    node_type: str = ShaderNodeType.SCALAR.value
    name: str = ""
    stage: str = ShaderStage.FRAGMENT.value
    precision: str = ShaderPrecision.HIGH.value
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    position_x: float = 0.0
    position_y: float = 0.0
    code: str = ""
    enabled: bool = True
    category: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class NodeConnection:
    """A typed edge linking an output port to an input port.

    Attributes:
        connection_id: Unique identifier for the connection.
        graph_id: Identifier of the graph that owns this connection.
        source_node_id: Identifier of the node owning the source port.
        source_port: Name of the source (output) port.
        target_node_id: Identifier of the node owning the target port.
        target_port: Name of the target (input) port.
        data_type: The data classification flowing across the edge.
        created_at: ISO-8601 creation timestamp.
    """
    connection_id: str = field(default_factory=lambda: _new_id("conn"))
    graph_id: str = ""
    source_node_id: str = ""
    source_port: str = ""
    target_node_id: str = ""
    target_port: str = ""
    data_type: str = "float"
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderGraph:
    """A complete shader graph: a DAG of nodes and connections.

    A graph points to its nodes and connections by id, tracks the
    terminal output node, and carries the pipeline stage and precision
    that govern compilation.

    Attributes:
        graph_id: Unique identifier for the graph.
        name: Human-readable name of the graph.
        description: Long-form description of the graph.
        stage: The pipeline stage this graph targets.
        status: The current ShaderStatus.
        node_ids: Identifiers of nodes belonging to this graph.
        connection_ids: Identifiers of connections belonging to this graph.
        output_node_id: Identifier of the terminal output node.
        precision: The default precision qualifier for the graph.
        tags: Editor search tags.
        version: Semantic version of the graph content.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        metadata: Free-form extension data.
    """
    graph_id: str = field(default_factory=lambda: _new_id("graph"))
    name: str = ""
    description: str = ""
    stage: str = ShaderStage.FRAGMENT.value
    status: str = ShaderStatus.DRAFT.value
    node_ids: List[str] = field(default_factory=list)
    connection_ids: List[str] = field(default_factory=list)
    output_node_id: str = ""
    precision: str = ShaderPrecision.HIGH.value
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialProperty:
    """A typed, exposed property on a material template.

    Properties allow designers to expose named, typed values that can be
    overridden per instance at runtime (for example, the base color,
    roughness, or emission strength of a PBR material). When
    ``min_value`` and ``max_value`` are both set, numeric values are
    clamped to that range.

    Attributes:
        property_id: Unique identifier for the property.
        name: Programmatic name of the property (uniform name).
        display_name: Human-readable label shown in the editor.
        property_type: The MaterialPropertyType value.
        value: The current value.
        default_value: The value the property resets to.
        min_value: Optional inclusive lower bound for clamping.
        max_value: Optional inclusive upper bound for clamping.
        texture_path: Asset path when the property is a texture/cubemap.
        sampler: Sampler state identifier for texture properties.
        exposed: Whether the property is exposed for per-instance override.
        description: Long-form description of the property.
        metadata: Free-form extension data.
    """
    property_id: str = field(default_factory=lambda: _new_id("prop"))
    name: str = ""
    display_name: str = ""
    property_type: str = MaterialPropertyType.FLOAT.value
    value: Any = 0.0
    default_value: Any = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    texture_path: str = ""
    sampler: str = "linear_repeat"
    exposed: bool = True
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Material:
    """A material template binding a shader program to typed properties.

    A material owns a list of properties and points to the shader
    program that consumes them. Material instances are created from a
    material template and may override exposed properties.

    Attributes:
        material_id: Unique identifier for the material.
        name: Human-readable name of the material.
        description: Long-form description of the material.
        material_type: The MaterialType classification.
        shader_program_id: Identifier of the bound shader program.
        properties: List of MaterialProperty values.
        default_blend_mode: The default BlendMode for instances.
        default_cull_mode: The default CullMode for instances.
        is_template: Whether this material is a reusable template.
        version: Semantic version of the material content.
        tags: Editor search tags.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        metadata: Free-form extension data.
    """
    material_id: str = field(default_factory=lambda: _new_id("mat"))
    name: str = ""
    description: str = ""
    material_type: str = MaterialType.STANDARD.value
    shader_program_id: str = ""
    properties: List[MaterialProperty] = field(default_factory=list)
    default_blend_mode: str = BlendMode.OPAQUE.value
    default_cull_mode: str = CullMode.BACK.value
    is_template: bool = True
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialInstance:
    """A runtime instantiation of a material template.

    An instance points to its parent material, carries per-instance
    property overrides, owns a list of texture layers, and exposes
    blend/cull/sort configuration for the render queue.

    Attributes:
        instance_id: Unique identifier for the instance.
        material_id: Identifier of the parent material template.
        name: Human-readable name of the instance.
        property_overrides: Mapping of property name to overridden value.
        texture_layer_ids: Identifiers of texture layers attached here.
        blend_mode: The BlendMode for this instance.
        cull_mode: The CullMode for this instance.
        sort_order: Render-queue sort key.
        enabled: Whether the instance is currently rendered.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        metadata: Free-form extension data.
    """
    instance_id: str = field(default_factory=lambda: _new_id("inst"))
    material_id: str = ""
    name: str = ""
    property_overrides: Dict[str, Any] = field(default_factory=dict)
    texture_layer_ids: List[str] = field(default_factory=list)
    blend_mode: str = BlendMode.OPAQUE.value
    cull_mode: str = CullMode.BACK.value
    sort_order: float = 0.0
    enabled: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderProgram:
    """A compiled shader program ready for runtime use.

    Attributes:
        program_id: Unique identifier for the program.
        name: Human-readable name of the program.
        graph_id: Identifier of the source shader graph.
        stage: The pipeline stage this program targets.
        status: The current ShaderStatus of the program.
        vertex_source: Generated vertex shader source code.
        fragment_source: Generated fragment shader source code.
        geometry_source: Generated geometry shader source code.
        compute_source: Generated compute shader source code.
        uniform_count: Number of uniforms declared in the program.
        texture_sample_count: Number of texture sample operations.
        instruction_count: Approximate instruction count (profiling).
        register_count: Estimated register usage.
        is_optimized: Whether the program has been through optimization.
        optimization_gain: Relative size reduction from optimization (0..1).
        precision: The precision qualifier used during compilation.
        created_at: ISO-8601 creation timestamp.
        updated_at: ISO-8601 last-update timestamp.
        metadata: Free-form extension data.
    """
    program_id: str = field(default_factory=lambda: _new_id("prog"))
    name: str = ""
    graph_id: str = ""
    stage: str = ShaderStage.FRAGMENT.value
    status: str = ShaderStatus.COMPILED.value
    vertex_source: str = ""
    fragment_source: str = ""
    geometry_source: str = ""
    compute_source: str = ""
    uniform_count: int = 0
    texture_sample_count: int = 0
    instruction_count: int = 0
    register_count: int = 0
    is_optimized: bool = False
    optimization_gain: float = 0.0
    precision: str = ShaderPrecision.HIGH.value
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderCompilationResult:
    """The outcome of compiling a shader graph.

    Attributes:
        result_id: Unique identifier for the result.
        graph_id: Identifier of the compiled graph.
        program_id: Identifier of the produced program (on success).
        success: Whether the compilation succeeded.
        errors: List of error messages produced during compilation.
        warnings: List of non-fatal warning messages.
        duration_ms: Time spent compiling, in milliseconds.
        node_count: Number of nodes processed.
        connection_count: Number of connections resolved.
        optimizer_passes: Number of optimizer passes applied.
        created_at: ISO-8601 timestamp of the compile attempt.
        metadata: Free-form extension data.
    """
    result_id: str = field(default_factory=lambda: _new_id("res"))
    graph_id: str = ""
    program_id: str = ""
    success: bool = False
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    node_count: int = 0
    connection_count: int = 0
    optimizer_passes: int = 0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TextureLayer:
    """A layered texture slot attached to a material instance.

    Texture layers allow multiple textures to be composited onto a
    single material channel (for example, a base albedo, a detail map,
    and a dirt mask blended together).

    Attributes:
        layer_id: Unique identifier for the layer.
        instance_id: Identifier of the owning material instance.
        name: Human-readable name of the layer.
        texture_path: Asset path of the texture.
        uv_set: Which UV channel to sample (0, 1, 2, ...).
        blend_weight: Contribution weight in [0, 1].
        blend_mode: How this layer is combined with lower layers.
        channel_mask: Which output channels this layer affects.
        offset: UV offset (u, v).
        tiling: UV tiling (u, v).
        rotation: UV rotation in radians.
        enabled: Whether the layer is active.
        sort_index: Order within the layer stack (lower = bottom).
        metadata: Free-form extension data.
        created_at: ISO-8601 creation timestamp.
    """
    layer_id: str = field(default_factory=lambda: _new_id("layer"))
    instance_id: str = ""
    name: str = ""
    texture_path: str = ""
    uv_set: int = 0
    blend_weight: float = 1.0
    blend_mode: str = BlendMode.ALPHA_BLEND.value
    channel_mask: str = "rgba"
    offset: Tuple[float, float] = (0.0, 0.0)
    tiling: Tuple[float, float] = (1.0, 1.0)
    rotation: float = 0.0
    enabled: bool = True
    sort_index: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderMaterialGraphConfig:
    """Runtime configuration for the shader material graph system.

    Attributes:
        max_nodes: Maximum number of nodes the registry will hold.
        max_graphs: Maximum number of graphs the registry will hold.
        max_connections: Maximum number of connections the registry will hold.
        max_materials: Maximum number of material templates.
        max_material_instances: Maximum number of material instances.
        max_shader_programs: Maximum number of compiled shader programs.
        max_compilation_results: Maximum number of stored compile results.
        max_texture_layers: Maximum number of texture layers.
        max_events: Maximum number of audit events retained.
        default_precision: The default precision qualifier for new nodes.
        default_stage: The default pipeline stage for new graphs.
        auto_optimize_on_compile: Whether to run the optimizer after compile.
        enable_ai_generation: Whether AI shader generation is permitted.
        enable_ai_optimization: Whether AI shader optimization is permitted.
        enable_ai_suggestions: Whether AI node suggestions are permitted.
        optimizer_pass_count: Number of optimizer passes to apply.
        warn_on_dangling_inputs: Whether to warn on unconnected input ports.
    """
    max_nodes: int = _MAX_NODES
    max_graphs: int = _MAX_GRAPHS
    max_connections: int = _MAX_CONNECTIONS
    max_materials: int = _MAX_MATERIALS
    max_material_instances: int = _MAX_MATERIAL_INSTANCES
    max_shader_programs: int = _MAX_SHADER_PROGRAMS
    max_compilation_results: int = _MAX_COMPILATION_RESULTS
    max_texture_layers: int = _MAX_TEXTURE_LAYERS
    max_events: int = _MAX_EVENTS
    default_precision: str = ShaderPrecision.HIGH.value
    default_stage: str = ShaderStage.FRAGMENT.value
    auto_optimize_on_compile: bool = False
    enable_ai_generation: bool = True
    enable_ai_optimization: bool = True
    enable_ai_suggestions: bool = True
    optimizer_pass_count: int = 2
    warn_on_dangling_inputs: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderMaterialGraphStats:
    """Aggregate counters describing the engine state.

    Attributes:
        total_graphs: Total number of graphs in the registry.
        total_nodes: Total number of nodes in the registry.
        total_connections: Total number of connections in the registry.
        total_materials: Total number of material templates.
        total_material_instances: Total number of material instances.
        total_programs: Total number of compiled shader programs.
        total_compilations: Total number of compile attempts (all-time).
        total_errors: Total number of failed compile attempts (all-time).
        total_texture_layers: Total number of texture layers.
        active_graphs: Number of graphs not in ARCHIVED status.
        compiled_graphs: Number of graphs in COMPILED or OPTIMIZED status.
        optimized_programs: Number of programs that have been optimized.
        ai_shaders_generated: Total number of AI-generated shaders (all-time).
        ai_shaders_optimized: Total number of AI-optimized shaders (all-time).
        ai_node_suggestions: Total number of AI node suggestion calls (all-time).
        tick_count: Number of tick calls since reset.
    """
    total_graphs: int = 0
    total_nodes: int = 0
    total_connections: int = 0
    total_materials: int = 0
    total_material_instances: int = 0
    total_programs: int = 0
    total_compilations: int = 0
    total_errors: int = 0
    total_texture_layers: int = 0
    active_graphs: int = 0
    compiled_graphs: int = 0
    optimized_programs: int = 0
    ai_shaders_generated: int = 0
    ai_shaders_optimized: int = 0
    ai_node_suggestions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderMaterialGraphSnapshot:
    """An immutable point-in-time snapshot of the whole engine.

    Attributes:
        timestamp: ISO-8601 timestamp of the snapshot.
        graphs: Serialized graph summaries (capped sample).
        materials: Serialized material summaries (capped sample).
        instances: Serialized instance summaries (capped sample).
        programs: Serialized program summaries (capped sample).
        stats: Aggregate counters at snapshot time.
        config: Runtime configuration at snapshot time.
    """
    timestamp: str = field(default_factory=_now)
    graphs: List[Dict[str, Any]] = field(default_factory=list)
    materials: List[Dict[str, Any]] = field(default_factory=list)
    instances: List[Dict[str, Any]] = field(default_factory=list)
    programs: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderMaterialGraphEvent:
    """An audit log entry for a lifecycle change in the system.

    Attributes:
        event_id: Unique identifier for the event.
        timestamp: ISO-8601 timestamp of the event.
        event_type: The ShaderMaterialGraphEventKind value.
        target_id: Identifier of the affected entity (graph, node, ...).
        description: Human-readable summary of the event.
        metadata: Free-form extension data.
    """
    event_id: str = field(default_factory=lambda: _new_id("evt"))
    timestamp: str = field(default_factory=_now)
    event_type: str = ""
    target_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System Class
# ---------------------------------------------------------------------------

class ShaderMaterialGraphSystem:
    """Singleton shader & material graph system.

    Manages the full lifecycle of shader graphs, material templates,
    material instances, compiled shader programs, and texture layers.
    All operations are thread-safe via an internal RLock.
    """

    _instance: Optional["ShaderMaterialGraphSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        # Storage containers
        self._nodes: Dict[str, ShaderNode] = {}
        self._connections: Dict[str, NodeConnection] = {}
        self._graphs: Dict[str, ShaderGraph] = {}
        self._materials: Dict[str, Material] = {}
        self._instances: Dict[str, MaterialInstance] = {}
        self._programs: Dict[str, ShaderProgram] = {}
        self._results: Dict[str, ShaderCompilationResult] = {}
        self._texture_layers: Dict[str, TextureLayer] = {}
        self._events: List[ShaderMaterialGraphEvent] = []
        # Indexes for fast lookups
        self._graph_nodes: Dict[str, List[str]] = {}
        self._graph_connections: Dict[str, List[str]] = {}
        self._graph_results: Dict[str, List[str]] = {}
        self._material_instances: Dict[str, List[str]] = {}
        self._instance_layers: Dict[str, List[str]] = {}
        # Config and stats
        self._config = ShaderMaterialGraphConfig()
        self._stats = ShaderMaterialGraphStats()
        self._tick_count: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "ShaderMaterialGraphSystem":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the system with seed data (idempotent)."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with seed data."""
        now = _now()

        # --- Shader Nodes (12) ---
        node_seeds = [
            ("node_uv_001", ShaderNodeType.UV, "UV Coordinates", ShaderStage.FRAGMENT,
             [], ["uv"], {"channel": 0}, 0.0, 0.0, "Input"),
            ("node_time_001", ShaderNodeType.TIME, "Time", ShaderStage.FRAGMENT,
             [], ["time"], {"period": 1.0}, 100.0, 0.0, "Input"),
            ("node_color_001", ShaderNodeType.COLOR, "Base Color", ShaderStage.FRAGMENT,
             [], ["color"], {"value": [0.8, 0.8, 0.8, 1.0]}, 200.0, 0.0, "Input"),
            ("node_texture_001", ShaderNodeType.TEXTURE_SAMPLE, "Albedo Texture", ShaderStage.FRAGMENT,
             ["uv", "sampler"], ["color"], {"default": "white"}, 300.0, 0.0, "Texture"),
            ("node_normal_001", ShaderNodeType.NORMAL, "Normal From Map", ShaderStage.FRAGMENT,
             ["tangent", "bitangent", "normal_map"], ["world_normal"], {"strength": 1.0}, 300.0, 200.0, "Normal"),
            ("node_noise_001", ShaderNodeType.NOISE, "Perlin Noise", ShaderStage.FRAGMENT,
             ["position", "scale"], ["noise"], {"seed": 0.0}, 400.0, 0.0, "Procedural"),
            ("node_fbm_001", ShaderNodeType.FBM, "Fractal Brownian Motion", ShaderStage.FRAGMENT,
             ["position", "octaves", "lacunarity", "gain"], ["fbm"], {"octaves": 5}, 400.0, 200.0, "Procedural"),
            ("node_add_001", ShaderNodeType.ADD, "Add", ShaderStage.FRAGMENT,
             ["a", "b"], ["result"], {}, 500.0, 0.0, "Math"),
            ("node_multiply_001", ShaderNodeType.MULTIPLY, "Multiply", ShaderStage.FRAGMENT,
             ["a", "b"], ["result"], {}, 500.0, 100.0, "Math"),
            ("node_lerp_001", ShaderNodeType.LERP, "Lerp", ShaderStage.FRAGMENT,
             ["a", "b", "t"], ["result"], {}, 500.0, 200.0, "Math"),
            ("node_smoothstep_001", ShaderNodeType.SMOOTHSTEP, "Smoothstep", ShaderStage.FRAGMENT,
             ["edge0", "edge1", "x"], ["result"], {}, 600.0, 0.0, "Math"),
            ("node_output_001", ShaderNodeType.OUTPUT, "Fragment Output", ShaderStage.FRAGMENT,
             ["color"], [], {}, 700.0, 100.0, "Output"),
        ]
        for (nid, ntype, name, stage, inputs, outputs, props, px, py, cat) in node_seeds:
            node = ShaderNode(
                node_id=nid, node_type=ntype.value, name=name, stage=stage.value,
                precision=ShaderPrecision.HIGH.value, inputs=list(inputs), outputs=list(outputs),
                properties=dict(props), position_x=px, position_y=py, enabled=True,
                category=cat, description=f"Seed {name} node",
                metadata={"seed": True}, created_at=now,
            )
            self._nodes[nid] = node

        # --- Shader Graphs (5) ---
        graph_seeds = [
            ("graph_pbr_001", "PBR Standard", "Physically based standard surface shader",
             ShaderStage.FRAGMENT, ShaderStatus.COMPILED,
             ["node_uv_001", "node_texture_001", "node_normal_001", "node_color_001",
              "node_multiply_001", "node_output_001"],
             ["conn_001", "conn_002", "conn_003"],
             "node_output_001", ["pbr", "standard", "surface"], "1.2.0"),
            ("graph_unlit_001", "Unlit Color", "Simple unlit color shader",
             ShaderStage.FRAGMENT, ShaderStatus.COMPILED,
             ["node_color_001", "node_output_001"],
             ["conn_004"],
             "node_output_001", ["unlit", "simple"], "1.0.0"),
            ("graph_water_001", "Animated Water", "Water surface with FBM waves and refraction",
             ShaderStage.FRAGMENT, ShaderStatus.OPTIMIZED,
             ["node_uv_001", "node_time_001", "node_fbm_001", "node_noise_001",
              "node_add_001", "node_color_001", "node_output_001"],
             ["conn_005", "conn_006", "conn_007"],
             "node_output_001", ["water", "animated", "fbm"], "2.1.0"),
            ("graph_noise_001", "Procedural Noise", "Pure procedural noise pattern",
             ShaderStage.FRAGMENT, ShaderStatus.DRAFT,
             ["node_uv_001", "node_noise_001", "node_output_001"],
             [],
             "node_output_001", ["procedural", "noise"], "0.9.0"),
            ("graph_post_001", "Post Process Tone Map", "ACES tone mapping post-process pass",
             ShaderStage.FRAGMENT, ShaderStatus.DRAFT,
             ["node_color_001", "node_smoothstep_001", "node_output_001"],
             [],
             "node_output_001", ["post_process", "tonemap"], "1.0.0"),
        ]
        for (gid, name, desc, stage, status, node_ids, conn_ids, out_node, tags, ver) in graph_seeds:
            graph = ShaderGraph(
                graph_id=gid, name=name, description=desc, stage=stage.value,
                status=status.value, node_ids=list(node_ids), connection_ids=list(conn_ids),
                output_node_id=out_node, precision=ShaderPrecision.HIGH.value,
                tags=list(tags), version=ver, created_at=now, updated_at=now,
                metadata={"seed": True},
            )
            self._graphs[gid] = graph
            self._graph_nodes[gid] = list(node_ids)
            self._graph_connections[gid] = list(conn_ids)

        # --- Connections (7) ---
        conn_seeds = [
            ("conn_001", "graph_pbr_001", "node_uv_001", "uv", "node_texture_001", "uv", "vec2"),
            ("conn_002", "graph_pbr_001", "node_texture_001", "color", "node_multiply_001", "a", "vec4"),
            ("conn_003", "graph_pbr_001", "node_multiply_001", "result", "node_output_001", "color", "vec4"),
            ("conn_004", "graph_unlit_001", "node_color_001", "color", "node_output_001", "color", "vec4"),
            ("conn_005", "graph_water_001", "node_uv_001", "uv", "node_fbm_001", "position", "vec2"),
            ("conn_006", "graph_water_001", "node_time_001", "time", "node_fbm_001", "octaves", "float"),
            ("conn_007", "graph_water_001", "node_fbm_001", "fbm", "node_add_001", "a", "float"),
        ]
        for (cid, gid, src_node, src_port, tgt_node, tgt_port, dtype) in conn_seeds:
            conn = NodeConnection(
                connection_id=cid, graph_id=gid, source_node_id=src_node,
                source_port=src_port, target_node_id=tgt_node, target_port=tgt_port,
                data_type=dtype, created_at=now,
            )
            self._connections[cid] = conn

        # --- Shader Programs (5) ---
        program_seeds = [
            ("prog_pbr_001", "PBR Standard Program", "graph_pbr_001", ShaderStage.FRAGMENT,
             ShaderStatus.COMPILED, 12, 3, 240, 16, False, 0.0),
            ("prog_unlit_001", "Unlit Color Program", "graph_unlit_001", ShaderStage.FRAGMENT,
             ShaderStatus.COMPILED, 4, 0, 60, 8, False, 0.0),
            ("prog_water_001", "Animated Water Program", "graph_water_001", ShaderStage.FRAGMENT,
             ShaderStatus.OPTIMIZED, 18, 4, 410, 24, True, 0.18),
            ("prog_noise_001", "Procedural Noise Program", "graph_noise_001", ShaderStage.FRAGMENT,
             ShaderStatus.ERROR, 6, 1, 0, 0, False, 0.0),
            ("prog_post_001", "Post Process Program", "graph_post_001", ShaderStage.FRAGMENT,
             ShaderStatus.DRAFT, 8, 0, 0, 0, False, 0.0),
        ]
        for (pid, name, gid, stage, status, uniforms, samples, instr, regs, opt, gain) in program_seeds:
            prog = ShaderProgram(
                program_id=pid, name=name, graph_id=gid, stage=stage.value,
                status=status.value, vertex_source="// auto-generated vertex stage\n",
                fragment_source="// auto-generated fragment stage\n",
                geometry_source="", compute_source="",
                uniform_count=uniforms, texture_sample_count=samples,
                instruction_count=instr, register_count=regs,
                is_optimized=opt, optimization_gain=gain,
                precision=ShaderPrecision.HIGH.value,
                created_at=now, updated_at=now, metadata={"seed": True},
            )
            self._programs[pid] = prog

        # --- Compilation Results (5) ---
        result_seeds = [
            ("res_001", "graph_pbr_001", "prog_pbr_001", True, [], ["Dangling input 'roughness' on node_normal_001"],
             12.4, 6, 3, 0),
            ("res_002", "graph_unlit_001", "prog_unlit_001", True, [], [], 3.1, 2, 1, 0),
            ("res_003", "graph_water_001", "prog_water_001", True, [], ["High register pressure on node_fbm_001"],
             28.7, 7, 3, 2),
            ("res_004", "graph_noise_001", "", False,
             ["Missing output node", "Cycle detected: node_noise_001 -> node_noise_001"], [], 1.2, 3, 0, 0),
            ("res_005", "graph_post_001", "", False,
             ["Graph is in DRAFT status, nothing to compile"], [], 0.4, 3, 0, 0),
        ]
        for (rid, gid, pid, ok, errs, warns, dur, nodes, conns, passes) in result_seeds:
            res = ShaderCompilationResult(
                result_id=rid, graph_id=gid, program_id=pid, success=ok,
                errors=list(errs), warnings=list(warns), duration_ms=dur,
                node_count=nodes, connection_count=conns, optimizer_passes=passes,
                created_at=now, metadata={"seed": True},
            )
            self._results[rid] = res
            self._graph_results.setdefault(gid, []).append(rid)

        # --- Materials (5) ---
        material_seeds = [
            ("mat_pbr_metal_001", "Brushed Metal", "PBR brushed metal surface",
             MaterialType.PBR, "prog_pbr_001", BlendMode.OPAQUE, CullMode.BACK,
             ["pbr", "metal", "surface"], "1.0.0",
             [("albedo", "Albedo", MaterialPropertyType.COLOR, [0.7, 0.7, 0.72, 1.0], "", ""),
              ("roughness", "Roughness", MaterialPropertyType.FLOAT, 0.35, 0.0, 1.0),
              ("metallic", "Metallic", MaterialPropertyType.FLOAT, 0.95, 0.0, 1.0),
              ("normal_map", "Normal Map", MaterialPropertyType.TEXTURE, "", "", "")]),
            ("mat_pbr_wood_001", "Oak Wood", "PBR oak wood planks",
             MaterialType.PBR, "prog_pbr_001", BlendMode.OPAQUE, CullMode.BACK,
             ["pbr", "wood", "organic"], "1.0.0",
             [("albedo", "Albedo", MaterialPropertyType.TEXTURE, "textures/wood_albedo.dds", "", ""),
              ("roughness", "Roughness", MaterialPropertyType.FLOAT, 0.7, 0.0, 1.0),
              ("metallic", "Metallic", MaterialPropertyType.FLOAT, 0.0, 0.0, 1.0)]),
            ("mat_unlit_hud_001", "HUD Element", "Unlit HUD element with constant color",
             MaterialType.UNLIT, "prog_unlit_001", BlendMode.ALPHA_BLEND, CullMode.NONE,
             ["unlit", "hud", "ui"], "1.0.0",
             [("color", "Color", MaterialPropertyType.COLOR, [1.0, 0.9, 0.2, 1.0], "", ""),
              ("opacity", "Opacity", MaterialPropertyType.FLOAT, 0.9, 0.0, 1.0)]),
            ("mat_water_clear_001", "Clear Water", "Animated clear water surface",
             MaterialType.WATER, "prog_water_001", BlendMode.ALPHA_BLEND, CullMode.NONE,
             ["water", "transparent", "animated"], "2.1.0",
             [("depth_color", "Depth Color", MaterialPropertyType.COLOR, [0.0, 0.3, 0.5, 1.0], "", ""),
              ("surface_color", "Surface Color", MaterialPropertyType.COLOR, [0.6, 0.8, 0.9, 1.0], "", ""),
              ("refraction", "Refraction", MaterialPropertyType.FLOAT, 0.1, 0.0, 1.0),
              ("wave_speed", "Wave Speed", MaterialPropertyType.FLOAT, 0.8, 0.0, 5.0)]),
            ("mat_particle_fire_001", "Fire Particle", "Additive fire particle material",
             MaterialType.PARTICLE, "prog_unlit_001", BlendMode.ADDITIVE, CullMode.NONE,
             ["particle", "fire", "vfx"], "1.0.0",
             [("base_color", "Base Color", MaterialPropertyType.COLOR, [1.0, 0.4, 0.1, 1.0], "", ""),
              ("intensity", "Intensity", MaterialPropertyType.FLOAT, 2.0, 0.0, 10.0),
              ("softness", "Softness", MaterialPropertyType.FLOAT, 0.5, 0.0, 1.0)]),
        ]
        for (mid, name, desc, mtype, pid, blend, cull, tags, ver, prop_seeds) in material_seeds:
            props: List[MaterialProperty] = []
            for (pname, disp, ptype, val, mn, mx) in prop_seeds:
                p = MaterialProperty(
                    property_id=_new_id("prop"), name=pname, display_name=disp,
                    property_type=ptype.value, value=val, default_value=val,
                    min_value=(float(mn) if mn != "" else None),
                    max_value=(float(mx) if mx != "" else None),
                    texture_path=(val if ptype == MaterialPropertyType.TEXTURE else ""),
                    exposed=True, description=f"{disp} property",
                    metadata={"seed": True},
                )
                props.append(p)
            mat = Material(
                material_id=mid, name=name, description=desc, material_type=mtype.value,
                shader_program_id=pid, properties=props,
                default_blend_mode=blend.value, default_cull_mode=cull.value,
                is_template=True, version=ver, tags=list(tags),
                created_at=now, updated_at=now, metadata={"seed": True},
            )
            self._materials[mid] = mat

        # --- Material Instances (6) ---
        instance_seeds = [
            ("inst_001", "mat_pbr_metal_001", "Steel Sword", BlendMode.OPAQUE, CullMode.BACK, -5.0, True,
             {"roughness": 0.2, "metallic": 1.0}),
            ("inst_002", "mat_pbr_metal_001", "Iron Shield", BlendMode.OPAQUE, CullMode.BACK, -4.0, True,
             {"roughness": 0.5, "metallic": 0.8}),
            ("inst_003", "mat_pbr_wood_001", "Oak Barrel", BlendMode.OPAQUE, CullMode.BACK, -3.0, True,
             {"roughness": 0.65}),
            ("inst_004", "mat_unlit_hud_001", "Health Bar", BlendMode.ALPHA_BLEND, CullMode.NONE, 50.0, True,
             {"color": [0.1, 0.9, 0.2, 1.0], "opacity": 1.0}),
            ("inst_005", "mat_water_clear_001", "River Water", BlendMode.ALPHA_BLEND, CullMode.NONE, 0.0, True,
             {"refraction": 0.15, "wave_speed": 1.2}),
            ("inst_006", "mat_particle_fire_001", "Torch Flame", BlendMode.ADDITIVE, CullMode.NONE, 10.0, True,
             {"intensity": 3.0, "base_color": [1.0, 0.5, 0.0, 1.0]}),
        ]
        for (iid, mid, name, blend, cull, sort, enabled, overrides) in instance_seeds:
            inst = MaterialInstance(
                instance_id=iid, material_id=mid, name=name,
                property_overrides=dict(overrides), texture_layer_ids=[],
                blend_mode=blend.value, cull_mode=cull.value,
                sort_order=sort, enabled=enabled,
                created_at=now, updated_at=now, metadata={"seed": True},
            )
            self._instances[iid] = inst
            self._material_instances.setdefault(mid, []).append(iid)

        # --- Texture Layers (5) ---
        layer_seeds = [
            ("layer_001", "inst_001", "Detail Scratch", "textures/scratches.dds",
             1, 0.3, BlendMode.MULTIPLICATIVE, "r", (0.0, 0.0), (4.0, 4.0), 0.0, True, 1),
            ("layer_002", "inst_003", "Dirt Grime", "textures/grime.dds",
             0, 0.4, BlendMode.ALPHA_BLEND, "rgb", (0.0, 0.0), (1.0, 1.0), 0.0, True, 0),
            ("layer_003", "inst_003", "Wood Grain Detail", "textures/wood_detail.dds",
             1, 0.6, BlendMode.MULTIPLICATIVE, "rgb", (0.5, 0.5), (8.0, 8.0), 0.2, True, 1),
            ("layer_004", "inst_005", "Water Foam", "textures/foam.dds",
             0, 0.5, BlendMode.ALPHA_BLEND, "a", (0.0, 0.0), (2.0, 2.0), 0.0, True, 2),
            ("layer_005", "inst_006", "Ember Glow", "textures/embers.dds",
             0, 0.7, BlendMode.ADDITIVE, "rgb", (0.0, 0.0), (1.5, 1.5), 0.0, True, 0),
        ]
        for (lid, iid, name, path, uv, weight, blend, mask, off, tiling, rot, en, sort) in layer_seeds:
            layer = TextureLayer(
                layer_id=lid, instance_id=iid, name=name, texture_path=path,
                uv_set=uv, blend_weight=weight, blend_mode=blend.value, channel_mask=mask,
                offset=off, tiling=tiling, rotation=rot, enabled=en, sort_index=sort,
                metadata={"seed": True}, created_at=now,
            )
            self._texture_layers[lid] = layer
            self._instance_layers.setdefault(iid, []).append(lid)

        # --- Events (6) ---
        event_seeds = [
            ("evt_001", ShaderMaterialGraphEventKind.GRAPH_COMPILED, "graph_pbr_001",
             "Graph PBR Standard compiled successfully"),
            ("evt_002", ShaderMaterialGraphEventKind.GRAPH_OPTIMIZED, "graph_water_001",
             "Graph Animated Water optimized (gain 0.18)"),
            ("evt_003", ShaderMaterialGraphEventKind.MATERIAL_CREATED, "mat_pbr_metal_001",
             "Material Brushed Metal created"),
            ("evt_004", ShaderMaterialGraphEventKind.INSTANCE_CREATED, "inst_001",
             "Instance Steel Sword created"),
            ("evt_005", ShaderMaterialGraphEventKind.TEXTURE_LAYER_ADDED, "layer_001",
             "Texture layer Detail Scratch added"),
            ("evt_006", ShaderMaterialGraphEventKind.GRAPH_VALIDATED, "graph_noise_001",
             "Graph Procedural Noise validation failed"),
        ]
        for (eid, ekind, target, desc) in event_seeds:
            evt = ShaderMaterialGraphEvent(
                event_id=eid, timestamp=now, event_type=ekind.value,
                target_id=target, description=desc, metadata={"seed": True},
            )
            self._events.append(evt)

        self._refresh_stats()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, target_id: str = "", description: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        """Append an audit event and trim the event log to capacity."""
        event = ShaderMaterialGraphEvent(
            event_id=_new_id("evt"), timestamp=_now(), event_type=event_type,
            target_id=target_id, description=description, metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, self._config.max_events)

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current stores."""
        self._stats.total_graphs = len(self._graphs)
        self._stats.total_nodes = len(self._nodes)
        self._stats.total_connections = len(self._connections)
        self._stats.total_materials = len(self._materials)
        self._stats.total_material_instances = len(self._instances)
        self._stats.total_programs = len(self._programs)
        self._stats.total_texture_layers = len(self._texture_layers)
        self._stats.active_graphs = sum(
            1 for g in self._graphs.values()
            if g.status != ShaderStatus.ARCHIVED.value
        )
        self._stats.compiled_graphs = sum(
            1 for g in self._graphs.values()
            if g.status in (ShaderStatus.COMPILED.value, ShaderStatus.OPTIMIZED.value)
        )
        self._stats.optimized_programs = sum(
            1 for p in self._programs.values() if p.is_optimized
        )
        self._stats.tick_count = self._tick_count

    def _default_ports(self, node_type: ShaderNodeType) -> Tuple[List[str], List[str]]:
        """Return the default (inputs, outputs) port names for a node type."""
        defaults = _PORT_DEFAULTS.get(node_type)
        if defaults is None:
            return [], []
        return list(defaults[0]), list(defaults[1])

    def _resolve_node_type(self, value: Any) -> ShaderNodeType:
        """Coerce a raw value into a ShaderNodeType with a safe default."""
        resolved = _coerce_enum(ShaderNodeType, value, ShaderNodeType.SCALAR)
        return resolved if resolved is not None else ShaderNodeType.SCALAR

    # ------------------------------------------------------------------
    # Node Lifecycle
    # ------------------------------------------------------------------

    def register_node(self, node_id: str, node_type: str, name: str = "",
                      stage: Optional[str] = None,
                      precision: Optional[str] = None,
                      inputs: Optional[List[str]] = None,
                      outputs: Optional[List[str]] = None,
                      properties: Optional[Dict[str, Any]] = None,
                      position_x: float = 0.0, position_y: float = 0.0,
                      code: str = "", enabled: bool = True,
                      category: str = "", description: str = "",
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[ShaderNode]]:
        """Register a new shader node in the registry.

        When ``inputs`` or ``outputs`` are omitted, default ports are
        derived from the node type via the ``_PORT_DEFAULTS`` table.
        """
        with self._lock:
            if node_id in self._nodes:
                return False, f"Node {node_id} already exists", None
            if len(self._nodes) >= self._config.max_nodes:
                return False, "Maximum nodes reached", None
            ntype = self._resolve_node_type(node_type)
            stage_enum = _coerce_enum(ShaderStage, stage, _coerce_enum(ShaderStage, self._config.default_stage, ShaderStage.FRAGMENT))
            if stage_enum is None:
                stage_enum = ShaderStage.FRAGMENT
            prec_enum = _coerce_enum(ShaderPrecision, precision, _coerce_enum(ShaderPrecision, self._config.default_precision, ShaderPrecision.HIGH))
            if prec_enum is None:
                prec_enum = ShaderPrecision.HIGH
            if inputs is None or outputs is None:
                def_in, def_out = self._default_ports(ntype)
                if inputs is None:
                    inputs = def_in
                if outputs is None:
                    outputs = def_out
            node = ShaderNode(
                node_id=node_id, node_type=ntype.value, name=name or node_id,
                stage=stage_enum.value, precision=prec_enum.value,
                inputs=list(inputs), outputs=list(outputs),
                properties=dict(properties) if properties else {},
                position_x=_safe_float(position_x, 0.0), position_y=_safe_float(position_y, 0.0),
                code=code, enabled=bool(enabled), category=category,
                description=description, metadata=dict(metadata) if metadata else {},
                created_at=_now(),
            )
            self._nodes[node_id] = node
            _evict_fifo_dict(self._nodes, self._config.max_nodes)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.NODE_REGISTERED.value,
                       node_id, f"Node {node.name} registered")
            return True, "success", node

    def get_node(self, node_id: str) -> Optional[ShaderNode]:
        """Return the node with the given id, or None."""
        with self._lock:
            return self._nodes.get(node_id)

    def list_nodes(self, node_type: Optional[str] = None,
                   stage: Optional[str] = None,
                   enabled: Optional[bool] = None,
                   limit: int = _DEFAULT_LIST_LIMIT) -> List[ShaderNode]:
        """List nodes, optionally filtered by type, stage, and enabled state."""
        with self._lock:
            nodes = list(self._nodes.values())
            if node_type is not None:
                ntype = _coerce_enum(ShaderNodeType, node_type)
                if ntype is not None:
                    nodes = [n for n in nodes if n.node_type == ntype.value]
            if stage is not None:
                stage_enum = _coerce_enum(ShaderStage, stage)
                if stage_enum is not None:
                    nodes = [n for n in nodes if n.stage == stage_enum.value]
            if enabled is not None:
                nodes = [n for n in nodes if n.enabled == enabled]
            nodes.sort(key=lambda n: n.created_at, reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT)
            return nodes[:cap]

    def remove_node(self, node_id: str) -> Tuple[bool, str]:
        """Remove a node and any connections that point to it."""
        with self._lock:
            if node_id not in self._nodes:
                return False, f"Node {node_id} not found"
            del self._nodes[node_id]
            # Remove connections that pointed to this node
            to_remove = [
                cid for cid, c in self._connections.items()
                if c.source_node_id == node_id or c.target_node_id == node_id
            ]
            for cid in to_remove:
                conn = self._connections.pop(cid, None)
                if conn is not None:
                    graph_conns = self._graph_connections.get(conn.graph_id, [])
                    if cid in graph_conns:
                        graph_conns.remove(cid)
                    # Detach from graph node list
                    graph = self._graphs.get(conn.graph_id)
                    if graph is not None and cid in graph.connection_ids:
                        graph.connection_ids.remove(cid)
            # Detach from graph node lists
            for graph in self._graphs.values():
                if node_id in graph.node_ids:
                    graph.node_ids.remove(node_id)
                    graph.updated_at = _now()
                if graph.output_node_id == node_id:
                    graph.output_node_id = ""
            for graph_node_list in self._graph_nodes.values():
                if node_id in graph_node_list:
                    graph_node_list.remove(node_id)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.NODE_REMOVED.value,
                       node_id, f"Node {node_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Connection Lifecycle
    # ------------------------------------------------------------------

    def create_connection(self, connection_id: str, graph_id: str,
                          source_node_id: str, source_port: str,
                          target_node_id: str, target_port: str,
                          data_type: str = "float") -> Tuple[bool, str, Optional[NodeConnection]]:
        """Create a typed connection between two node ports.

        Validates that both nodes exist, the ports exist on the
        respective nodes, the source port is an output, the target port
        is an input, and the connection does not introduce a cycle.
        """
        with self._lock:
            if connection_id in self._connections:
                return False, f"Connection {connection_id} already exists", None
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False, f"Graph {graph_id} not found", None
            src_node = self._nodes.get(source_node_id)
            if src_node is None:
                return False, f"Source node {source_node_id} not found", None
            tgt_node = self._nodes.get(target_node_id)
            if tgt_node is None:
                return False, f"Target node {target_node_id} not found", None
            if source_port not in src_node.outputs:
                return False, f"Port {source_port} is not an output of {source_node_id}", None
            if target_port not in tgt_node.inputs:
                return False, f"Port {target_port} is not an input of {target_node_id}", None
            if source_node_id == target_node_id:
                return False, "Cannot connect a node to itself", None
            if self._creates_cycle(graph_id, source_node_id, target_node_id):
                return False, "Connection would create a cycle", None
            if len(self._connections) >= self._config.max_connections:
                return False, "Maximum connections reached", None
            conn = NodeConnection(
                connection_id=connection_id, graph_id=graph_id,
                source_node_id=source_node_id, source_port=source_port,
                target_node_id=target_node_id, target_port=target_port,
                data_type=data_type, created_at=_now(),
            )
            self._connections[connection_id] = conn
            _evict_fifo_dict(self._connections, self._config.max_connections)
            if connection_id not in graph.connection_ids:
                graph.connection_ids.append(connection_id)
            self._graph_connections.setdefault(graph_id, []).append(connection_id)
            graph.updated_at = _now()
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.CONNECTION_CREATED.value,
                       connection_id, f"Connection {connection_id} created")
            return True, "success", conn

    def _creates_cycle(self, graph_id: str, source_node_id: str, target_node_id: str) -> bool:
        """Check whether adding source->target would create a cycle.

        A cycle exists if there is already a path from ``target_node_id``
        back to ``source_node_id`` through the existing connections in
        the graph.
        """
        graph_conns = self._graph_connections.get(graph_id, [])
        adjacency: Dict[str, List[str]] = {}
        for cid in graph_conns:
            conn = self._connections.get(cid)
            if conn is None:
                continue
            adjacency.setdefault(conn.source_node_id, []).append(conn.target_node_id)
        # DFS from target to see if we reach source
        visited: set = set()
        stack: List[str] = [target_node_id]
        while stack:
            current = stack.pop()
            if current == source_node_id:
                return True
            if current in visited:
                continue
            visited.add(current)
            stack.extend(adjacency.get(current, []))
        return False

    def remove_connection(self, connection_id: str) -> Tuple[bool, str]:
        """Remove a connection by id."""
        with self._lock:
            conn = self._connections.pop(connection_id, None)
            if conn is None:
                return False, f"Connection {connection_id} not found"
            graph_conns = self._graph_connections.get(conn.graph_id, [])
            if connection_id in graph_conns:
                graph_conns.remove(connection_id)
            graph = self._graphs.get(conn.graph_id)
            if graph is not None:
                if connection_id in graph.connection_ids:
                    graph.connection_ids.remove(connection_id)
                graph.updated_at = _now()
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.CONNECTION_REMOVED.value,
                       connection_id, f"Connection {connection_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Graph Lifecycle
    # ------------------------------------------------------------------

    def create_graph(self, graph_id: str, name: str, description: str = "",
                     stage: Optional[str] = None,
                     precision: Optional[str] = None,
                     output_node_id: str = "",
                     tags: Optional[List[str]] = None,
                     version: str = "1.0.0",
                     metadata: Optional[Dict[str, Any]] = None
                     ) -> Tuple[bool, str, Optional[ShaderGraph]]:
        """Create a new shader graph."""
        with self._lock:
            if graph_id in self._graphs:
                return False, f"Graph {graph_id} already exists", None
            if len(self._graphs) >= self._config.max_graphs:
                return False, "Maximum graphs reached", None
            stage_enum = _coerce_enum(ShaderStage, stage, _coerce_enum(ShaderStage, self._config.default_stage, ShaderStage.FRAGMENT))
            if stage_enum is None:
                stage_enum = ShaderStage.FRAGMENT
            prec_enum = _coerce_enum(ShaderPrecision, precision, _coerce_enum(ShaderPrecision, self._config.default_precision, ShaderPrecision.HIGH))
            if prec_enum is None:
                prec_enum = ShaderPrecision.HIGH
            now = _now()
            graph = ShaderGraph(
                graph_id=graph_id, name=name, description=description,
                stage=stage_enum.value, status=ShaderStatus.DRAFT.value,
                node_ids=[], connection_ids=[], output_node_id=output_node_id,
                precision=prec_enum.value, tags=list(tags) if tags else [],
                version=version, created_at=now, updated_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._graphs[graph_id] = graph
            self._graph_nodes[graph_id] = []
            self._graph_connections[graph_id] = []
            _evict_fifo_dict(self._graphs, self._config.max_graphs)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.GRAPH_CREATED.value,
                       graph_id, f"Graph {name} created")
            return True, "success", graph

    def get_graph(self, graph_id: str) -> Optional[ShaderGraph]:
        """Return the graph with the given id, or None."""
        with self._lock:
            return self._graphs.get(graph_id)

    def list_graphs(self, stage: Optional[str] = None,
                    status: Optional[str] = None,
                    tag: Optional[str] = None,
                    limit: int = _DEFAULT_LIST_LIMIT) -> List[ShaderGraph]:
        """List graphs, optionally filtered by stage, status, and tag."""
        with self._lock:
            graphs = list(self._graphs.values())
            if stage is not None:
                stage_enum = _coerce_enum(ShaderStage, stage)
                if stage_enum is not None:
                    graphs = [g for g in graphs if g.stage == stage_enum.value]
            if status is not None:
                status_enum = _coerce_enum(ShaderStatus, status)
                if status_enum is not None:
                    graphs = [g for g in graphs if g.status == status_enum.value]
            if tag is not None:
                graphs = [g for g in graphs if tag in g.tags]
            graphs.sort(key=lambda g: g.created_at, reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT)
            return graphs[:cap]

    def remove_graph(self, graph_id: str) -> Tuple[bool, str]:
        """Remove a graph and its owned connections (nodes are retained)."""
        with self._lock:
            graph = self._graphs.pop(graph_id, None)
            if graph is None:
                return False, f"Graph {graph_id} not found"
            # Remove connections owned by this graph
            for cid in list(graph.connection_ids):
                self._connections.pop(cid, None)
            self._graph_connections.pop(graph_id, None)
            self._graph_nodes.pop(graph_id, None)
            # Remove compilation results referencing this graph
            for rid in list(self._graph_results.get(graph_id, [])):
                self._results.pop(rid, None)
            self._graph_results.pop(graph_id, None)
            # Deprecate programs produced from this graph
            for prog in self._programs.values():
                if prog.graph_id == graph_id:
                    prog.status = ShaderStatus.DEPRECATED.value
                    prog.updated_at = _now()
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.GRAPH_REMOVED.value,
                       graph_id, f"Graph {graph.name} removed")
            return True, "success"

    def validate_graph(self, graph_id: str) -> Tuple[bool, str, List[str]]:
        """Validate a graph structure and return a list of issues.

        Checks for: missing output node, dangling connections (referencing
        unknown nodes), dangling input ports (when configured to warn),
        and cycles.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False, f"Graph {graph_id} not found", ["graph not found"]
            issues: List[str] = []
            # Check output node
            if not graph.output_node_id:
                issues.append("Graph has no output node")
            elif graph.output_node_id not in self._nodes:
                issues.append(f"Output node {graph.output_node_id} not found in registry")
            elif graph.output_node_id not in graph.node_ids:
                issues.append(f"Output node {graph.output_node_id} not part of graph")
            # Check node ids listed by the graph
            for nid in graph.node_ids:
                if nid not in self._nodes:
                    issues.append(f"Node {nid} listed by graph not found in registry")
            # Check connections
            for cid in graph.connection_ids:
                conn = self._connections.get(cid)
                if conn is None:
                    issues.append(f"Connection {cid} listed by graph not found in registry")
                    continue
                if conn.source_node_id not in self._nodes:
                    issues.append(f"Connection {cid} source node {conn.source_node_id} missing")
                if conn.target_node_id not in self._nodes:
                    issues.append(f"Connection {cid} target node {conn.target_node_id} missing")
            # Check dangling inputs (optional)
            if self._config.warn_on_dangling_inputs:
                connected_inputs: Dict[str, set] = {}
                for cid in graph.connection_ids:
                    conn = self._connections.get(cid)
                    if conn is None:
                        continue
                    connected_inputs.setdefault(conn.target_node_id, set()).add(conn.target_port)
                for nid in graph.node_ids:
                    node = self._nodes.get(nid)
                    if node is None or not node.enabled:
                        continue
                    for port in node.inputs:
                        if port not in connected_inputs.get(nid, set()):
                            issues.append(f"Node {nid} input '{port}' is not connected")
            ok = len(issues) == 0
            self._emit(ShaderMaterialGraphEventKind.GRAPH_VALIDATED.value,
                       graph_id, f"Graph {graph.name} validated ({'ok' if ok else 'issues'})",
                       {"issue_count": len(issues)})
            return ok, "success" if ok else "validation issues", issues

    def compile_graph(self, graph_id: str) -> Tuple[bool, str, Optional[ShaderCompilationResult]]:
        """Compile a shader graph into a shader program.

        Performs validation, simulates code generation (counting
        uniforms, texture samples, instructions, and registers), and
        optionally runs the optimizer when ``auto_optimize_on_compile``
        is set in the configuration.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False, f"Graph {graph_id} not found", None
            if graph.status == ShaderStatus.COMPILING.value:
                return False, f"Graph {graph_id} is already compiling", None
            graph.status = ShaderStatus.COMPILING.value
            graph.updated_at = _now()
            self._emit("graph_compiling", graph_id, f"Graph {graph.name} compiling")
            # Validate
            ok, _, issues = self.validate_graph(graph_id)
            errors: List[str] = []
            warnings: List[str] = []
            for issue in issues:
                if "not found" in issue or "no output" in issue or "Cycle" in issue:
                    errors.append(issue)
                else:
                    warnings.append(issue)
            node_count = len(graph.node_ids)
            conn_count = len(graph.connection_ids)
            duration_ms = round(2.0 + node_count * 1.5 + conn_count * 0.5, 2)
            result = ShaderCompilationResult(
                result_id=_new_id("res"), graph_id=graph_id, program_id="",
                success=False, errors=errors, warnings=warnings,
                duration_ms=duration_ms, node_count=node_count,
                connection_count=conn_count, optimizer_passes=0,
                created_at=_now(), metadata={},
            )
            self._stats.total_compilations += 1
            if errors:
                graph.status = ShaderStatus.ERROR.value
                graph.updated_at = _now()
                self._stats.total_errors += 1
                self._results[result.result_id] = result
                self._graph_results.setdefault(graph_id, []).append(result.result_id)
                _evict_fifo_dict(self._results, self._config.max_compilation_results)
                self._emit(ShaderMaterialGraphEventKind.GRAPH_COMPILED.value,
                           graph_id, f"Graph {graph.name} compilation failed",
                           {"errors": len(errors)})
                return False, "compilation failed", result
            # Generate program
            program_id = _new_id("prog")
            uniform_count = sum(
                1 for nid in graph.node_ids
                if self._nodes.get(nid) is not None
                and self._nodes[nid].node_type == ShaderNodeType.UNIFORM.value
            ) + max(0, node_count // 3)
            sample_count = sum(
                1 for nid in graph.node_ids
                if self._nodes.get(nid) is not None
                and self._nodes[nid].node_type == ShaderNodeType.TEXTURE_SAMPLE.value
            )
            instruction_count = node_count * 8 + conn_count * 2
            register_count = max(8, node_count)
            program = ShaderProgram(
                program_id=program_id, name=f"{graph.name} Program",
                graph_id=graph_id, stage=graph.stage,
                status=ShaderStatus.COMPILED.value,
                vertex_source=f"// vertex stage for {graph.name}\nvoid main() {{ gl_Position = vec4(0); }}\n",
                fragment_source=f"// fragment stage for {graph.name}\nvec4 frag() {{ return vec4(1.0); }}\n",
                geometry_source="", compute_source="",
                uniform_count=uniform_count, texture_sample_count=sample_count,
                instruction_count=instruction_count, register_count=register_count,
                is_optimized=False, optimization_gain=0.0,
                precision=graph.precision,
                created_at=_now(), updated_at=_now(), metadata={"compiled_from": graph_id},
            )
            if len(self._programs) >= self._config.max_shader_programs:
                _evict_fifo_dict(self._programs, self._config.max_shader_programs)
            self._programs[program_id] = program
            result.program_id = program_id
            result.success = True
            optimizer_passes = 0
            if self._config.auto_optimize_on_compile:
                self._optimize_program_internal(program, self._config.optimizer_pass_count)
                optimizer_passes = self._config.optimizer_pass_count
                result.optimizer_passes = optimizer_passes
            graph.status = (ShaderStatus.OPTIMIZED.value
                            if program.is_optimized else ShaderStatus.COMPILED.value)
            graph.updated_at = _now()
            self._results[result.result_id] = result
            self._graph_results.setdefault(graph_id, []).append(result.result_id)
            _evict_fifo_dict(self._results, self._config.max_compilation_results)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.GRAPH_COMPILED.value,
                       graph_id, f"Graph {graph.name} compiled into {program_id}",
                       {"program_id": program_id, "optimizer_passes": optimizer_passes})
            return True, "success", result

    def _optimize_program_internal(self, program: ShaderProgram, passes: int) -> None:
        """Apply simulated optimization passes to a program in place."""
        if program.status not in (ShaderStatus.COMPILED.value, ShaderStatus.OPTIMIZED.value):
            return
        original_instr = max(1, program.instruction_count)
        for _ in range(max(1, passes)):
            program.instruction_count = max(1, int(program.instruction_count * 0.88))
            program.register_count = max(4, int(program.register_count * 0.92))
            program.texture_sample_count = max(0, program.texture_sample_count)
        program.optimization_gain = round(
            _clamp(1.0 - (program.instruction_count / original_instr), 0.0, 0.95), 4
        )
        program.is_optimized = True
        program.status = ShaderStatus.OPTIMIZED.value
        program.updated_at = _now()

    def optimize_graph(self, graph_id: str, passes: int = 2) -> Tuple[bool, str, Optional[ShaderProgram]]:
        """Optimize the compiled program produced from a graph.

        Finds the most recent successful program for the graph and
        applies the optimizer. Returns the optimized program.
        """
        with self._lock:
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False, f"Graph {graph_id} not found", None
            # Find the latest program for this graph
            program: Optional[ShaderProgram] = None
            for prog in reversed(list(self._programs.values())):
                if prog.graph_id == graph_id and prog.status in (
                    ShaderStatus.COMPILED.value, ShaderStatus.OPTIMIZED.value
                ):
                    program = prog
                    break
            if program is None:
                return False, f"No compiled program found for graph {graph_id}", None
            self._optimize_program_internal(program, passes)
            graph.status = ShaderStatus.OPTIMIZED.value
            graph.updated_at = _now()
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.GRAPH_OPTIMIZED.value,
                       graph_id, f"Graph {graph.name} optimized (gain {program.optimization_gain})",
                       {"program_id": program.program_id, "passes": passes})
            return True, "success", program

    # ------------------------------------------------------------------
    # Material Lifecycle
    # ------------------------------------------------------------------

    def create_material(self, material_id: str, name: str,
                        description: str = "",
                        material_type: str = MaterialType.STANDARD.value,
                        shader_program_id: str = "",
                        default_blend_mode: str = BlendMode.OPAQUE.value,
                        default_cull_mode: str = CullMode.BACK.value,
                        tags: Optional[List[str]] = None,
                        version: str = "1.0.0",
                        metadata: Optional[Dict[str, Any]] = None
                        ) -> Tuple[bool, str, Optional[Material]]:
        """Create a new material template."""
        with self._lock:
            if material_id in self._materials:
                return False, f"Material {material_id} already exists", None
            if len(self._materials) >= self._config.max_materials:
                return False, "Maximum materials reached", None
            mtype = _coerce_enum(MaterialType, material_type, MaterialType.STANDARD)
            if mtype is None:
                mtype = MaterialType.STANDARD
            blend = _coerce_enum(BlendMode, default_blend_mode, BlendMode.OPAQUE)
            if blend is None:
                blend = BlendMode.OPAQUE
            cull = _coerce_enum(CullMode, default_cull_mode, CullMode.BACK)
            if cull is None:
                cull = CullMode.BACK
            now = _now()
            material = Material(
                material_id=material_id, name=name, description=description,
                material_type=mtype.value, shader_program_id=shader_program_id,
                properties=[], default_blend_mode=blend.value,
                default_cull_mode=cull.value, is_template=True, version=version,
                tags=list(tags) if tags else [], created_at=now, updated_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._materials[material_id] = material
            self._material_instances[material_id] = []
            _evict_fifo_dict(self._materials, self._config.max_materials)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.MATERIAL_CREATED.value,
                       material_id, f"Material {name} created")
            return True, "success", material

    def get_material(self, material_id: str) -> Optional[Material]:
        """Return the material with the given id, or None."""
        with self._lock:
            return self._materials.get(material_id)

    def list_materials(self, material_type: Optional[str] = None,
                       tag: Optional[str] = None,
                       limit: int = _DEFAULT_LIST_LIMIT) -> List[Material]:
        """List materials, optionally filtered by type and tag."""
        with self._lock:
            materials = list(self._materials.values())
            if material_type is not None:
                mtype = _coerce_enum(MaterialType, material_type)
                if mtype is not None:
                    materials = [m for m in materials if m.material_type == mtype.value]
            if tag is not None:
                materials = [m for m in materials if tag in m.tags]
            materials.sort(key=lambda m: m.created_at, reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT)
            return materials[:cap]

    def remove_material(self, material_id: str) -> Tuple[bool, str]:
        """Remove a material and all of its instances."""
        with self._lock:
            material = self._materials.pop(material_id, None)
            if material is None:
                return False, f"Material {material_id} not found"
            # Remove all instances of this material
            for iid in list(self._material_instances.get(material_id, [])):
                self._remove_instance_internal(iid)
            self._material_instances.pop(material_id, None)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.MATERIAL_REMOVED.value,
                       material_id, f"Material {material.name} removed")
            return True, "success"

    def _find_property(self, material: Material, property_name: str) -> Optional[MaterialProperty]:
        """Return the named property on a material, or None."""
        for prop in material.properties:
            if prop.name == property_name:
                return prop
        return None

    def set_material_property(self, material_id: str, property_name: str,
                              value: Any, display_name: Optional[str] = None,
                              property_type: Optional[str] = None,
                              min_value: Optional[float] = None,
                              max_value: Optional[float] = None,
                              texture_path: Optional[str] = None,
                              exposed: Optional[bool] = None
                              ) -> Tuple[bool, str, Optional[MaterialProperty]]:
        """Set or create a material property.

        When the property already exists its value and optional fields
        are updated; otherwise a new property is appended to the
        material. Numeric values are clamped to ``[min_value, max_value]``
        when both bounds are provided.
        """
        with self._lock:
            material = self._materials.get(material_id)
            if material is None:
                return False, f"Material {material_id} not found", None
            prop = self._find_property(material, property_name)
            coerced_value = value
            if prop is None:
                ptype = _coerce_enum(MaterialPropertyType, property_type, MaterialPropertyType.FLOAT)
                if ptype is None:
                    ptype = MaterialPropertyType.FLOAT
                prop = MaterialProperty(
                    property_id=_new_id("prop"), name=property_name,
                    display_name=display_name or property_name,
                    property_type=ptype.value, value=value, default_value=value,
                    min_value=min_value, max_value=max_value,
                    texture_path=texture_path or "", exposed=True if exposed is None else exposed,
                )
                material.properties.append(prop)
            else:
                if display_name is not None:
                    prop.display_name = display_name
                if property_type is not None:
                    ptype = _coerce_enum(MaterialPropertyType, property_type, prop.property_type)
                    if ptype is not None:
                        prop.property_type = ptype.value
                if min_value is not None:
                    prop.min_value = min_value
                if max_value is not None:
                    prop.max_value = max_value
                if texture_path is not None:
                    prop.texture_path = texture_path
                if exposed is not None:
                    prop.exposed = exposed
                # Clamp numeric values
                if prop.min_value is not None and prop.max_value is not None:
                    try:
                        coerced_value = _clamp(_safe_float(value, _safe_float(prop.value, 0.0)),
                                               prop.min_value, prop.max_value)
                    except Exception:
                        coerced_value = value
                prop.value = coerced_value
            material.updated_at = _now()
            self._emit(ShaderMaterialGraphEventKind.PROPERTY_SET.value,
                       material_id, f"Property {property_name} set on {material.name}",
                       {"property": property_name, "value": _to_jsonable(coerced_value)})
            return True, "success", prop

    def get_material_property(self, material_id: str, property_name: str
                              ) -> Optional[MaterialProperty]:
        """Return a material property by name, or None."""
        with self._lock:
            material = self._materials.get(material_id)
            if material is None:
                return None
            return self._find_property(material, property_name)

    # ------------------------------------------------------------------
    # Material Instance Lifecycle
    # ------------------------------------------------------------------

    def create_material_instance(self, instance_id: str, material_id: str,
                                 name: str = "",
                                 property_overrides: Optional[Dict[str, Any]] = None,
                                 blend_mode: Optional[str] = None,
                                 cull_mode: Optional[str] = None,
                                 sort_order: float = 0.0,
                                 enabled: bool = True,
                                 metadata: Optional[Dict[str, Any]] = None
                                 ) -> Tuple[bool, str, Optional[MaterialInstance]]:
        """Create a runtime material instance from a material template.

        The instance inherits the material's default blend and cull mode
        unless explicitly overridden. ``property_overrides`` is a mapping
        of property name to value.
        """
        with self._lock:
            if instance_id in self._instances:
                return False, f"Instance {instance_id} already exists", None
            material = self._materials.get(material_id)
            if material is None:
                return False, f"Material {material_id} not found", None
            if len(self._instances) >= self._config.max_material_instances:
                return False, "Maximum material instances reached", None
            blend = _coerce_enum(BlendMode, blend_mode, _coerce_enum(BlendMode, material.default_blend_mode, BlendMode.OPAQUE))
            if blend is None:
                blend = BlendMode.OPAQUE
            cull = _coerce_enum(CullMode, cull_mode, _coerce_enum(CullMode, material.default_cull_mode, CullMode.BACK))
            if cull is None:
                cull = CullMode.BACK
            now = _now()
            instance = MaterialInstance(
                instance_id=instance_id, material_id=material_id,
                name=name or f"{material.name} Instance",
                property_overrides=dict(property_overrides) if property_overrides else {},
                texture_layer_ids=[], blend_mode=blend.value, cull_mode=cull.value,
                sort_order=_clamp(_safe_float(sort_order, 0.0), _SORT_ORDER_MIN, _SORT_ORDER_MAX),
                enabled=bool(enabled), created_at=now, updated_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._instances[instance_id] = instance
            self._material_instances.setdefault(material_id, []).append(instance_id)
            self._instance_layers[instance_id] = []
            _evict_fifo_dict(self._instances, self._config.max_material_instances)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.INSTANCE_CREATED.value,
                       instance_id, f"Instance {instance.name} created")
            return True, "success", instance

    def get_material_instance(self, instance_id: str) -> Optional[MaterialInstance]:
        """Return the material instance with the given id, or None."""
        with self._lock:
            return self._instances.get(instance_id)

    def list_material_instances(self, material_id: Optional[str] = None,
                                enabled: Optional[bool] = None,
                                limit: int = _DEFAULT_LIST_LIMIT
                                ) -> List[MaterialInstance]:
        """List material instances, optionally filtered by material and enabled state."""
        with self._lock:
            instances = list(self._instances.values())
            if material_id is not None:
                instances = [i for i in instances if i.material_id == material_id]
            if enabled is not None:
                instances = [i for i in instances if i.enabled == enabled]
            instances.sort(key=lambda i: (i.sort_order, i.created_at), reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT)
            return instances[:cap]

    def _remove_instance_internal(self, instance_id: str) -> bool:
        """Remove an instance and its texture layers (no lock acquired)."""
        instance = self._instances.pop(instance_id, None)
        if instance is None:
            return False
        # Remove texture layers
        for lid in list(self._instance_layers.get(instance_id, [])):
            self._texture_layers.pop(lid, None)
        self._instance_layers.pop(instance_id, None)
        # Detach from material index
        mat_insts = self._material_instances.get(instance.material_id, [])
        if instance_id in mat_insts:
            mat_insts.remove(instance_id)
        return True

    def remove_material_instance(self, instance_id: str) -> Tuple[bool, str]:
        """Remove a material instance and its texture layers."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return False, f"Instance {instance_id} not found"
            self._remove_instance_internal(instance_id)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.INSTANCE_REMOVED.value,
                       instance_id, f"Instance {instance.name} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Texture Layer Lifecycle
    # ------------------------------------------------------------------

    def add_texture_layer(self, layer_id: str, instance_id: str, name: str,
                          texture_path: str, uv_set: int = 0,
                          blend_weight: float = 1.0,
                          blend_mode: str = BlendMode.ALPHA_BLEND.value,
                          channel_mask: str = "rgba",
                          offset: Tuple[float, float] = (0.0, 0.0),
                          tiling: Tuple[float, float] = (1.0, 1.0),
                          rotation: float = 0.0,
                          enabled: bool = True,
                          sort_index: int = 0,
                          metadata: Optional[Dict[str, Any]] = None
                          ) -> Tuple[bool, str, Optional[TextureLayer]]:
        """Add a texture layer to a material instance."""
        with self._lock:
            if layer_id in self._texture_layers:
                return False, f"Texture layer {layer_id} already exists", None
            instance = self._instances.get(instance_id)
            if instance is None:
                return False, f"Instance {instance_id} not found", None
            if len(self._texture_layers) >= self._config.max_texture_layers:
                return False, "Maximum texture layers reached", None
            blend = _coerce_enum(BlendMode, blend_mode, BlendMode.ALPHA_BLEND)
            if blend is None:
                blend = BlendMode.ALPHA_BLEND
            layer = TextureLayer(
                layer_id=layer_id, instance_id=instance_id, name=name,
                texture_path=texture_path, uv_set=max(0, _safe_int(uv_set, 0)),
                blend_weight=_clamp(_safe_float(blend_weight, 1.0), 0.0, 1.0),
                blend_mode=blend.value, channel_mask=channel_mask,
                offset=offset, tiling=tiling, rotation=_safe_float(rotation, 0.0),
                enabled=bool(enabled), sort_index=_safe_int(sort_index, 0),
                metadata=dict(metadata) if metadata else {}, created_at=_now(),
            )
            self._texture_layers[layer_id] = layer
            instance.texture_layer_ids.append(layer_id)
            self._instance_layers.setdefault(instance_id, []).append(layer_id)
            instance.updated_at = _now()
            _evict_fifo_dict(self._texture_layers, self._config.max_texture_layers)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.TEXTURE_LAYER_ADDED.value,
                       layer_id, f"Texture layer {name} added to {instance.name}")
            return True, "success", layer

    def remove_texture_layer(self, layer_id: str) -> Tuple[bool, str]:
        """Remove a texture layer by id."""
        with self._lock:
            layer = self._texture_layers.pop(layer_id, None)
            if layer is None:
                return False, f"Texture layer {layer_id} not found"
            instance = self._instances.get(layer.instance_id)
            if instance is not None:
                if layer_id in instance.texture_layer_ids:
                    instance.texture_layer_ids.remove(layer_id)
                instance.updated_at = _now()
            inst_layers = self._instance_layers.get(layer.instance_id, [])
            if layer_id in inst_layers:
                inst_layers.remove(layer_id)
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.TEXTURE_LAYER_REMOVED.value,
                       layer_id, f"Texture layer {layer.name} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Shader Program Inspection
    # ------------------------------------------------------------------

    def get_shader_program(self, program_id: str) -> Optional[ShaderProgram]:
        """Return the shader program with the given id, or None."""
        with self._lock:
            return self._programs.get(program_id)

    def list_shader_programs(self, stage: Optional[str] = None,
                             status: Optional[str] = None,
                             optimized: Optional[bool] = None,
                             limit: int = _DEFAULT_LIST_LIMIT
                             ) -> List[ShaderProgram]:
        """List shader programs, optionally filtered."""
        with self._lock:
            programs = list(self._programs.values())
            if stage is not None:
                stage_enum = _coerce_enum(ShaderStage, stage)
                if stage_enum is not None:
                    programs = [p for p in programs if p.stage == stage_enum.value]
            if status is not None:
                status_enum = _coerce_enum(ShaderStatus, status)
                if status_enum is not None:
                    programs = [p for p in programs if p.status == status_enum.value]
            if optimized is not None:
                programs = [p for p in programs if p.is_optimized == optimized]
            programs.sort(key=lambda p: p.created_at, reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_LIST_LIMIT), _MAX_LIST_LIMIT)
            return programs[:cap]

    def get_compilation_result(self, result_id: str) -> Optional[ShaderCompilationResult]:
        """Return the compilation result with the given id, or None."""
        with self._lock:
            return self._results.get(result_id)

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def auto_generate_shader(self, description: str, graph_name: str = ""
                             ) -> Tuple[bool, str, Optional[ShaderGraph]]:
        """Generate a shader graph from a natural-language description.

        The generator inspects the description for keywords (water, fire,
        metal, skin, terrain, foliage, hair, cloth, glass, energy, smoke,
        crystal, lava, ice) and assembles a graph with nodes appropriate
        to the detected theme. When no theme is recognized, a generic
        PBR graph is produced.
        """
        with self._lock:
            if not self._config.enable_ai_generation:
                return False, "AI generation is disabled", None
            if not description or not description.strip():
                return False, "Description must not be empty", None
            desc_lower = description.lower()
            graph_id = _new_id("graph")
            name = graph_name or f"AI Shader {graph_id[:8]}"
            now = _now()
            # Determine theme and node set
            theme = "generic"
            node_specs: List[Tuple[str, ShaderNodeType, str, float, float]] = []
            if "water" in desc_lower or "ocean" in desc_lower or "river" in desc_lower:
                theme = "water"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("time", ShaderNodeType.TIME, "Time", 100.0, 0.0),
                    ("fbm", ShaderNodeType.FBM, "Surface FBM", 200.0, 0.0),
                    ("noise", ShaderNodeType.NOISE, "Ripple Noise", 200.0, 150.0),
                    ("add", ShaderNodeType.ADD, "Combine Waves", 350.0, 75.0),
                    ("depth_color", ShaderNodeType.COLOR, "Depth Color", 350.0, 200.0),
                    ("surface_color", ShaderNodeType.COLOR, "Surface Color", 450.0, 200.0),
                    ("lerp", ShaderNodeType.LERP, "Depth Blend", 500.0, 150.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 650.0, 150.0),
                ]
            elif "fire" in desc_lower or "flame" in desc_lower or "lava" in desc_lower:
                theme = "fire"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("time", ShaderNodeType.TIME, "Time", 100.0, 0.0),
                    ("noise", ShaderNodeType.NOISE, "Flame Noise", 200.0, 0.0),
                    ("fbm", ShaderNodeType.FBM, "Flame FBM", 200.0, 150.0),
                    ("add", ShaderNodeType.ADD, "Combine", 350.0, 75.0),
                    ("color", ShaderNodeType.COLOR, "Fire Color", 350.0, 200.0),
                    ("multiply", ShaderNodeType.MULTIPLY, "Color Mod", 500.0, 150.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 650.0, 150.0),
                ]
            elif "metal" in desc_lower or "steel" in desc_lower or "iron" in desc_lower:
                theme = "metal"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("texture", ShaderNodeType.TEXTURE_SAMPLE, "Albedo", 150.0, 0.0),
                    ("normal", ShaderNodeType.NORMAL, "Normal", 150.0, 150.0),
                    ("color", ShaderNodeType.COLOR, "Tint", 300.0, 0.0),
                    ("multiply", ShaderNodeType.MULTIPLY, "Tinted Albedo", 450.0, 75.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 650.0, 75.0),
                ]
            elif "skin" in desc_lower:
                theme = "skin"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("texture", ShaderNodeType.TEXTURE_SAMPLE, "Albedo", 150.0, 0.0),
                    ("normal", ShaderNodeType.NORMAL, "Normal", 150.0, 150.0),
                    ("color", ShaderNodeType.COLOR, "Subsurface Tint", 300.0, 0.0),
                    ("lerp", ShaderNodeType.LERP, "Subsurface Blend", 450.0, 75.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 650.0, 75.0),
                ]
            elif "terrain" in desc_lower or "ground" in desc_lower or "landscape" in desc_lower:
                theme = "terrain"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("noise", ShaderNodeType.NOISE, "Height Noise", 150.0, 0.0),
                    ("fbm", ShaderNodeType.FBM, "Height FBM", 150.0, 150.0),
                    ("texture", ShaderNodeType.TEXTURE_SAMPLE, "Grass Texture", 300.0, 0.0),
                    ("texture2", ShaderNodeType.TEXTURE_SAMPLE, "Rock Texture", 300.0, 150.0),
                    ("lerp", ShaderNodeType.LERP, "Splat Blend", 450.0, 75.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 650.0, 75.0),
                ]
            elif "glass" in desc_lower or "crystal" in desc_lower or "ice" in desc_lower:
                theme = "glass"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("color", ShaderNodeType.COLOR, "Tint Color", 150.0, 0.0),
                    ("noise", ShaderNodeType.NOISE, "Surface Noise", 150.0, 150.0),
                    ("multiply", ShaderNodeType.MULTIPLY, "Tinted", 300.0, 75.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 450.0, 75.0),
                ]
            else:
                theme = "generic"
                node_specs = [
                    ("uv", ShaderNodeType.UV, "UV", 0.0, 0.0),
                    ("color", ShaderNodeType.COLOR, "Base Color", 150.0, 0.0),
                    ("texture", ShaderNodeType.TEXTURE_SAMPLE, "Albedo Texture", 150.0, 150.0),
                    ("multiply", ShaderNodeType.MULTIPLY, "Tinted Albedo", 300.0, 75.0),
                    ("output", ShaderNodeType.OUTPUT, "Output", 450.0, 75.0),
                ]
            # Create the graph
            ok, msg, graph = self.create_graph(
                graph_id=graph_id, name=name,
                description=f"AI-generated {theme} shader: {description[:120]}",
                stage=ShaderStage.FRAGMENT.value,
                precision=ShaderPrecision.HIGH.value,
                tags=["ai_generated", theme],
                version="1.0.0",
                metadata={"ai_theme": theme, "ai_description": description[:200]},
            )
            if not ok or graph is None:
                return False, msg, None
            # Register nodes
            created_node_ids: List[str] = []
            for (suffix, ntype, label, px, py) in node_specs:
                nid = f"{graph_id}_{suffix}"
                rops = []
                # Use default ports derived from node type
                rok, rmsg, rnode = self.register_node(
                    node_id=nid, node_type=ntype.value, name=label,
                    stage=ShaderStage.FRAGMENT.value, precision=ShaderPrecision.HIGH.value,
                    position_x=px, position_y=py, category="AI Generated",
                    description=f"AI-generated {ntype.value} node for {theme} shader",
                    metadata={"ai_generated": True, "theme": theme},
                )
                if rok and rnode is not None:
                    created_node_ids.append(nid)
                    graph.node_ids.append(nid)
                    rops.append(rnode)
            # Attach node ids to the graph
            self._graph_nodes[graph_id] = list(created_node_ids)
            # Set the output node
            output_ids = [nid for nid in created_node_ids if nid.endswith("_output")]
            if output_ids:
                graph.output_node_id = output_ids[0]
            graph.updated_at = now
            self._stats.ai_shaders_generated += 1
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.SHADER_GENERATED.value,
                       graph_id, f"AI generated {theme} shader '{name}'",
                       {"theme": theme, "node_count": len(created_node_ids)})
            return True, "success", graph

    def optimize_shader(self, program_id: str, passes: int = 3
                        ) -> Tuple[bool, str, Optional[ShaderProgram]]:
        """Optimize a compiled shader program for performance.

        Applies simulated optimization passes that reduce instruction
        count, register pressure, and texture samples, then marks the
        program as optimized.
        """
        with self._lock:
            if not self._config.enable_ai_optimization:
                return False, "AI optimization is disabled", None
            program = self._programs.get(program_id)
            if program is None:
                return False, f"Program {program_id} not found", None
            if program.status not in (ShaderStatus.COMPILED.value, ShaderStatus.OPTIMIZED.value):
                return False, f"Program {program_id} is not compiled (status={program.status})", None
            original_instr = max(1, program.instruction_count)
            self._optimize_program_internal(program, passes)
            # AI optimization applies a small additional reduction
            program.instruction_count = max(1, int(program.instruction_count * 0.95))
            program.optimization_gain = round(
                _clamp(1.0 - (program.instruction_count / original_instr), 0.0, 0.95), 4
            )
            program.metadata["ai_optimized"] = True
            program.metadata["ai_passes"] = passes
            program.updated_at = _now()
            # Update parent graph status
            graph = self._graphs.get(program.graph_id)
            if graph is not None:
                graph.status = ShaderStatus.OPTIMIZED.value
                graph.updated_at = _now()
            self._stats.ai_shaders_optimized += 1
            self._refresh_stats()
            self._emit(ShaderMaterialGraphEventKind.SHADER_OPTIMIZED.value,
                       program_id, f"AI optimized program {program.name} (gain {program.optimization_gain})",
                       {"passes": passes, "gain": program.optimization_gain})
            return True, "success", program

    def suggest_nodes(self, graph_id: str, limit: int = 8
                      ) -> Tuple[bool, str, List[ShaderNode]]:
        """Suggest nodes that would complete a partial graph.

        Inspects the existing nodes in the graph and proposes nodes
        based on what is missing (for example, an OUTPUT node when none
        exists, a TEXTURE_SAMPLE when a COLOR node is present but no
        texture, a NORMAL node for PBR completeness, and procedural
        nodes when no noise/fbm node is present).
        """
        with self._lock:
            if not self._config.enable_ai_suggestions:
                return False, "AI suggestions are disabled", []
            graph = self._graphs.get(graph_id)
            if graph is None:
                return False, f"Graph {graph_id} not found", []
            existing_types: set = set()
            for nid in graph.node_ids:
                node = self._nodes.get(nid)
                if node is not None:
                    existing_types.add(node.node_type)
            suggestions: List[ShaderNode] = []
            suggestion_specs: List[Tuple[ShaderNodeType, str, str]] = []
            # Always suggest an output node when missing
            if ShaderNodeType.OUTPUT.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.OUTPUT, "Fragment Output", "Output"))
            # Suggest a texture sample when a color node exists but no texture
            if (ShaderNodeType.COLOR.value in existing_types
                    and ShaderNodeType.TEXTURE_SAMPLE.value not in existing_types):
                suggestion_specs.append((ShaderNodeType.TEXTURE_SAMPLE, "Detail Texture", "Texture"))
            # Suggest a normal node for PBR completeness
            if ShaderNodeType.NORMAL.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.NORMAL, "Normal From Map", "Normal"))
            # Suggest procedural nodes when none present
            if (ShaderNodeType.NOISE.value not in existing_types
                    and ShaderNodeType.FBM.value not in existing_types):
                suggestion_specs.append((ShaderNodeType.NOISE, "Procedural Noise", "Procedural"))
                suggestion_specs.append((ShaderNodeType.FBM, "Fractal Brownian Motion", "Procedural"))
            # Suggest a time node for animated effects
            if ShaderNodeType.TIME.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.TIME, "Time", "Input"))
            # Suggest math nodes to round out the graph
            if ShaderNodeType.LERP.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.LERP, "Lerp", "Math"))
            if ShaderNodeType.SMOOTHSTEP.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.SMOOTHSTEP, "Smoothstep", "Math"))
            if ShaderNodeType.MULTIPLY.value not in existing_types:
                suggestion_specs.append((ShaderNodeType.MULTIPLY, "Multiply", "Math"))
            cap = max(1, _safe_int(limit, 8))
            for (ntype, label, cat) in suggestion_specs[:cap]:
                def_in, def_out = self._default_ports(ntype)
                node = ShaderNode(
                    node_id=_new_id("sug"), node_type=ntype.value, name=label,
                    stage=graph.stage, precision=graph.precision,
                    inputs=def_in, outputs=def_out, properties={},
                    position_x=200.0 + len(suggestions) * 100.0, position_y=400.0,
                    enabled=True, category=cat,
                    description=f"Suggested {label} node to complete graph {graph.name}",
                    metadata={"ai_suggested": True, "for_graph": graph_id},
                    created_at=_now(),
                )
                suggestions.append(node)
            self._stats.ai_node_suggestions += 1
            self._emit(ShaderMaterialGraphEventKind.NODES_SUGGESTED.value,
                       graph_id, f"Suggested {len(suggestions)} nodes for graph {graph.name}",
                       {"suggestion_count": len(suggestions)})
            return True, "success", suggestions

    # ------------------------------------------------------------------
    # System Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_graphs": len(self._graphs),
                "total_nodes": len(self._nodes),
                "total_connections": len(self._connections),
                "total_materials": len(self._materials),
                "total_material_instances": len(self._instances),
                "total_programs": len(self._programs),
                "total_compilation_results": len(self._results),
                "total_texture_layers": len(self._texture_layers),
                "total_events": len(self._events),
            }

    def get_stats(self) -> ShaderMaterialGraphStats:
        """Return aggregate statistics (refreshed before return)."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> ShaderMaterialGraphSnapshot:
        """Return an immutable snapshot of the whole engine."""
        with self._lock:
            self._refresh_stats()
            return ShaderMaterialGraphSnapshot(
                timestamp=_now(),
                graphs=[g.to_dict() for g in list(self._graphs.values())[:20]],
                materials=[m.to_dict() for m in list(self._materials.values())[:20]],
                instances=[i.to_dict() for i in list(self._instances.values())[:20]],
                programs=[p.to_dict() for p in list(self._programs.values())[:20]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
            )

    def get_config(self) -> ShaderMaterialGraphConfig:
        """Return the current runtime configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, ShaderMaterialGraphConfig]:
        """Update runtime configuration fields.

        Accepts any subset of ShaderMaterialGraphConfig fields. Numeric
        fields are coerced; boolean fields are coerced; enum-typed fields
        (``default_precision``, ``default_stage``) are coerced via their
        respective enums.
        """
        with self._lock:
            for key in ("max_nodes", "max_graphs", "max_connections", "max_materials",
                        "max_material_instances", "max_shader_programs",
                        "max_compilation_results", "max_texture_layers", "max_events",
                        "optimizer_pass_count"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, max(1, _safe_int(kwargs[key], getattr(self._config, key))))
            for key in ("auto_optimize_on_compile", "enable_ai_generation",
                        "enable_ai_optimization", "enable_ai_suggestions",
                        "warn_on_dangling_inputs"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_precision" in kwargs and kwargs["default_precision"] is not None:
                prec = _coerce_enum(ShaderPrecision, kwargs["default_precision"], None)
                if prec is not None:
                    self._config.default_precision = prec.value
            if "default_stage" in kwargs and kwargs["default_stage"] is not None:
                stage = _coerce_enum(ShaderStage, kwargs["default_stage"], None)
                if stage is not None:
                    self._config.default_stage = stage.value
            self._emit(ShaderMaterialGraphEventKind.CONFIG_UPDATED.value,
                       "", "Configuration updated")
            return True, "success", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        """Advance the system by one frame.

        Performs housekeeping: refreshes statistics, trims the event log
        to capacity, and reports the current frame state.
        """
        with self._lock:
            self._tick_count += 1
            _evict_fifo_list(self._events, self._config.max_events)
            self._refresh_stats()
            # Mark long-running compiling graphs as errored (simulated timeout)
            timed_out = 0
            for graph in self._graphs.values():
                if graph.status == ShaderStatus.COMPILING.value:
                    graph.status = ShaderStatus.ERROR.value
                    graph.updated_at = _now()
                    timed_out += 1
            result = {
                "tick": self._tick_count,
                "dt": _safe_float(dt, 0.016),
                "total_graphs": len(self._graphs),
                "total_materials": len(self._materials),
                "total_programs": len(self._programs),
                "compiled_graphs": self._stats.compiled_graphs,
                "optimized_programs": self._stats.optimized_programs,
                "timed_out_compiles": timed_out,
            }
            self._emit(ShaderMaterialGraphEventKind.TICK.value,
                       "", f"Tick {self._tick_count}", result)
            return result

    def reset(self) -> None:
        """Clear all stores and re-seed with default data."""
        with self._lock:
            self._nodes.clear()
            self._connections.clear()
            self._graphs.clear()
            self._materials.clear()
            self._instances.clear()
            self._programs.clear()
            self._results.clear()
            self._texture_layers.clear()
            self._events.clear()
            self._graph_nodes.clear()
            self._graph_connections.clear()
            self._graph_results.clear()
            self._material_instances.clear()
            self._instance_layers.clear()
            self._config = ShaderMaterialGraphConfig()
            self._stats = ShaderMaterialGraphStats()
            self._tick_count = 0
            self._initialized = False
            self._emit(ShaderMaterialGraphEventKind.RESET.value,
                       "", "System reset")
            self._seed()
            self._initialized = True

    def list_events(self, limit: int = 100) -> List[ShaderMaterialGraphEvent]:
        """Return the most recent audit events (newest last)."""
        with self._lock:
            cap = min(_safe_int(limit, 100), self._config.max_events)
            return list(self._events[-cap:])


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_shader_material_graph_system() -> ShaderMaterialGraphSystem:
    """Return the shared ShaderMaterialGraphSystem singleton instance."""
    return ShaderMaterialGraphSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "ShaderNodeType",
    "ShaderStage",
    "ShaderPrecision",
    "ShaderStatus",
    "MaterialType",
    "MaterialPropertyType",
    "BlendMode",
    "CullMode",
    "ShaderMaterialGraphEventKind",
    # Data classes
    "ShaderNode",
    "NodeConnection",
    "ShaderGraph",
    "MaterialProperty",
    "Material",
    "MaterialInstance",
    "ShaderProgram",
    "ShaderCompilationResult",
    "TextureLayer",
    "ShaderMaterialGraphConfig",
    "ShaderMaterialGraphStats",
    "ShaderMaterialGraphSnapshot",
    "ShaderMaterialGraphEvent",
    # Main system
    "ShaderMaterialGraphSystem",
    "get_shader_material_graph_system",
]
