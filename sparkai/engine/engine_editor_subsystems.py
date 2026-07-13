"""
SparkLabs Engine - Editor Subsystems

This module extends the AI-native game editor with six additional critical
editor subsystems. The existing editor (engine_ai_native_editor.py) already
provides SceneEditor, AssetManager, CodeEditor, LevelDesigner,
AnimationEditor, and PhysicsEditor. This module adds the remaining pieces
that complete the editor surface: a material/shader graph editor, a
terrain sculpting editor, a particle effect designer, a visual script
node graph editor, an audio mixer editor, and a copilot conversational
panel.

Architecture:
  _EditorSubsystemsSystem (singleton)
    |-- MaterialShaderGraphEditor      -- node-based shader and material editing
    |-- TerrainSculptingEditor         -- heightmap terrain sculpting and painting
    |-- ParticleEffectDesigner         -- particle system design and simulation
    |-- VisualScriptNodeGraphEditor    -- node-based visual scripting for game logic
    |-- AudioMixerEditor               -- audio bus, channel, and cue mixing
    |-- CopilotConversationalPanel     -- natural-language design copilot

Thread Safety:
  The system is a singleton created with double-checked locking. The
  class-level ``_init_lock`` guards singleton creation and one-time
  seeding via the ``_seeded`` flag; each subsystem instance owns an
  ``RLock`` that guards all mutating operations to keep internal
  dictionaries consistent.

Serialization:
  Every data class exposes a ``to_dict`` method that returns a
  JSON-serializable dictionary. Enum fields are returned as their
  ``.value`` attribute and ``math.inf`` values are returned as ``None``.

Usage:
    from sparkai.engine.engine_editor_subsystems import get_editor_subsystems
    system = get_editor_subsystems()
    materials = system.get_material_editor()
    mat = materials.create_material("Wet Rock")
    terrain = system.get_terrain_editor()
    terrain.create_terrain("Mountain Valley", width=512, height=512)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits max_size."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Coerce a raw value into an enum member, falling back to default."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    """Convert arbitrary values into JSON-serializable primitives.

    Enum members are returned as their ``.value``. Floats that are NaN or
    infinity (including ``math.inf``) are returned as ``None``. Dataclass
    instances are serialized through ``_dataclass_to_dict``.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return str(value)


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a plain dict.

    The ``__dataclass_fields__`` attribute is checked before ``to_dict``
    so that dataclasses which also expose ``to_dict`` do not recurse
    through their own serializer.
    """
    if instance is None:
        return {}
    if hasattr(instance, "__dataclass_fields__"):
        out: Dict[str, Any] = {}
        for name in getattr(instance, "__dataclass_fields__", {}).keys():
            try:
                raw = getattr(instance, name)
            except Exception:
                continue
            out[name] = _to_jsonable(raw)
        return out
    if isinstance(instance, dict):
        return {str(k): _to_jsonable(v) for k, v in instance.items()}
    if hasattr(instance, "to_dict") and callable(instance.to_dict):
        return instance.to_dict()
    return {}


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a numeric value into the inclusive range [lo, hi]."""
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Parse a float, returning default on failure or non-finite input."""
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Parse an int, returning default on failure."""
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _lerp(a: float, b: float, t: float) -> float:
    """Linearly interpolate between a and b by t (clamped to [0, 1])."""
    t = _clamp(t, 0.0, 1.0)
    return a + (b - a) * t


def _smooth_noise(x: float, y: float, seed: int = 0) -> float:
    """Deterministic smooth pseudo-noise in [0, 1] for terrain generation."""
    n = math.sin(x * 12.9898 + y * 78.233 + seed * 37.719) * 43758.5453
    return (n - math.floor(n))


def _value_noise_2d(x: float, y: float, seed: int = 0) -> float:
    """Smoothed value noise sampled on a grid and bilinearly interpolated."""
    xi = int(math.floor(x))
    yi = int(math.floor(y))
    xf = x - xi
    yf = y - yi
    v00 = _smooth_noise(float(xi), float(yi), seed)
    v10 = _smooth_noise(float(xi + 1), float(yi), seed)
    v01 = _smooth_noise(float(xi), float(yi + 1), seed)
    v11 = _smooth_noise(float(xi + 1), float(yi + 1), seed)
    fx = xf * xf * (3.0 - 2.0 * xf)
    fy = yf * yf * (3.0 - 2.0 * yf)
    top = _lerp(v00, v10, fx)
    bottom = _lerp(v01, v11, fx)
    return _lerp(top, bottom, fy)


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MATERIALS: int = 2000
_MAX_NODES_PER_GRAPH: int = 500
_MAX_CONNECTIONS_PER_GRAPH: int = 1000
_MAX_PARAMETERS_PER_MATERIAL: int = 100
_MAX_INSTANCES_PER_MATERIAL: int = 200

_MAX_TERRAINS: int = 500
_MAX_LAYERS_PER_TERRAIN: int = 16
_MAX_STROKES_PER_TERRAIN: int = 5000
_MAX_FOLIAGE_PATCHES: int = 10000

_MAX_EFFECTS: int = 1000
_MAX_EMITTERS_PER_EFFECT: int = 32
_MAX_MODIFIERS_PER_EFFECT: int = 64
_MAX_CURVES_PER_EFFECT: int = 128

_MAX_GRAPHS: int = 1000
_MAX_NODES_PER_SCRIPT: int = 500
_MAX_CONNECTIONS_PER_SCRIPT: int = 1000
_MAX_VARIABLES_PER_GRAPH: int = 200
_MAX_FUNCTIONS_PER_GRAPH: int = 100

_MAX_BUSES: int = 64
_MAX_CHANNELS: int = 256
_MAX_CUES: int = 2000
_MAX_EFFECTS_PER_BUS: int = 32

_MAX_SESSIONS: int = 500
_MAX_MESSAGES_PER_SESSION: int = 5000

_MAX_EVENTS: int = 10000


# ===========================================================================
# 1. Material Shader Graph Editor
# ===========================================================================

class ShaderNodeType(Enum):
    """Types of nodes available in the shader graph."""
    MATH_ADD = "math_add"
    MATH_MULTIPLY = "math_multiply"
    MATH_SUBTRACT = "math_subtract"
    TEXTURE_SAMPLE = "texture_sample"
    COLOR_CONSTANT = "color_constant"
    UV_COORD = "uv_coord"
    VERTEX_POSITION = "vertex_position"
    NORMAL_VECTOR = "normal_vector"
    TIME = "time"
    SIN = "sin"
    COS = "cos"
    POW = "pow"
    LERP = "lerp"
    CLAMP = "clamp"
    FRESNEL = "fresnel"
    DEPTH_FADE = "depth_fade"
    OUTPUT_BASE_COLOR = "output_base_color"
    OUTPUT_NORMAL = "output_normal"
    OUTPUT_EMISSIVE = "output_emissive"
    OUTPUT_ROUGHNESS = "output_roughness"
    OUTPUT_METALLIC = "output_metallic"


class MaterialBlendMode(Enum):
    """Blend mode controlling how the material composites with the framebuffer."""
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"
    ADDITIVE = "additive"
    MODULATE = "modulate"


class MaterialShadingModel(Enum):
    """Lighting model used to evaluate the material."""
    UNLIT = "unlit"
    LIT = "lit"
    SUBSURFACE = "subsurface"
    CLOTH = "cloth"
    HAIR = "hair"


@dataclass
class ShaderNode:
    """A single node in the shader graph."""
    node_id: str
    node_type: str = ShaderNodeType.COLOR_CONSTANT.value
    label: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    value: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderConnection:
    """A directed connection between two shader graph nodes."""
    connection_id: str
    from_node: str = ""
    from_output: str = ""
    to_node: str = ""
    to_input: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialParameter:
    """A named, bindable parameter exposed by a material."""
    parameter_id: str
    name: str = ""
    param_type: str = "float"
    default_value: Any = 0.0
    current_value: Any = 0.0
    min_value: float = 0.0
    max_value: float = 1.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialInstance:
    """An instance of a material with overridden parameter values."""
    instance_id: str
    source_material_id: str = ""
    name: str = ""
    parameter_overrides: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MaterialGraph:
    """A complete material definition consisting of nodes and connections."""
    material_id: str
    name: str = ""
    description: str = ""
    shading_model: str = MaterialShadingModel.LIT.value
    blend_mode: str = MaterialBlendMode.OPAQUE.value
    two_sided: bool = False
    nodes: List[ShaderNode] = field(default_factory=list)
    connections: List[ShaderConnection] = field(default_factory=list)
    parameters: List[MaterialParameter] = field(default_factory=list)
    instances: List[MaterialInstance] = field(default_factory=list)
    is_compiled: bool = False
    shader_code: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShaderCompilationResult:
    """Result of compiling a material graph into shader code."""
    material_id: str = ""
    success: bool = False
    shader_code: str = ""
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0
    instruction_count: int = 0
    texture_samples: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class MaterialShaderGraphEditor:
    """Visual node-based shader and material editor.

    Manages shader graph nodes, material instances, parameter binding,
    and shader compilation. Provides AI-assisted material generation,
    shader optimization, and node suggestions.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._materials: Dict[str, MaterialGraph] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"mat_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed(self) -> None:
        """Populate the editor with a canonical set of materials."""
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_standard_pbr()
            self._seed_glass()
            self._seed_metal()
            self._seed_foliage()
            self._seed_hologram()
            self._seeded = True

    def _seed_standard_pbr(self) -> None:
        mat = MaterialGraph(
            material_id="mat_pbr_standard",
            name="Standard PBR",
            description="A standard physically based rendering material with base color, normal, roughness, and metallic outputs.",
            shading_model=MaterialShadingModel.LIT.value,
            blend_mode=MaterialBlendMode.OPAQUE.value,
        )
        color = ShaderNode(
            node_id="node_pbr_color", node_type=ShaderNodeType.COLOR_CONSTANT.value,
            label="Base Color", position_x=-300, position_y=-100,
            value={"r": 0.8, "g": 0.8, "b": 0.8, "a": 1.0},
        )
        tex = ShaderNode(
            node_id="node_pbr_tex", node_type=ShaderNodeType.TEXTURE_SAMPLE.value,
            label="Albedo Texture", position_x=-300, position_y=50,
            value={"texture_slot": 0},
        )
        uv = ShaderNode(
            node_id="node_pbr_uv", node_type=ShaderNodeType.UV_COORD.value,
            label="UV", position_x=-500, position_y=50,
        )
        rough = ShaderNode(
            node_id="node_pbr_rough", node_type=ShaderNodeType.COLOR_CONSTANT.value,
            label="Roughness", position_x=-300, position_y=200,
            value={"r": 0.5, "g": 0.5, "b": 0.5, "a": 1.0},
        )
        metallic = ShaderNode(
            node_id="node_pbr_metal", node_type=ShaderNodeType.COLOR_CONSTANT.value,
            label="Metallic", position_x=-300, position_y=350,
            value={"r": 0.0, "g": 0.0, "b": 0.0, "a": 1.0},
        )
        out_color = ShaderNode(
            node_id="node_pbr_out_color", node_type=ShaderNodeType.OUTPUT_BASE_COLOR.value,
            label="Output Base Color", position_x=0, position_y=-50,
        )
        out_rough = ShaderNode(
            node_id="node_pbr_out_rough", node_type=ShaderNodeType.OUTPUT_ROUGHNESS.value,
            label="Output Roughness", position_x=0, position_y=200,
        )
        out_metal = ShaderNode(
            node_id="node_pbr_out_metal", node_type=ShaderNodeType.OUTPUT_METALLIC.value,
            label="Output Metallic", position_x=0, position_y=350,
        )
        mat.nodes = [color, tex, uv, rough, metallic, out_color, out_rough, out_metal]
        mat.connections = [
            ShaderConnection(connection_id="conn_pbr_1", from_node="node_pbr_tex", from_output="color", to_node="node_pbr_out_color", to_input="color"),
            ShaderConnection(connection_id="conn_pbr_2", from_node="node_pbr_uv", from_output="uv", to_node="node_pbr_tex", to_input="uv"),
            ShaderConnection(connection_id="conn_pbr_3", from_node="node_pbr_rough", from_output="color", to_node="node_pbr_out_rough", to_input="roughness"),
            ShaderConnection(connection_id="conn_pbr_4", from_node="node_pbr_metal", from_output="color", to_node="node_pbr_out_metal", to_input="metallic"),
        ]
        mat.parameters = [
            MaterialParameter(parameter_id="param_pbr_rough", name="Roughness", param_type="float", default_value=0.5, current_value=0.5, min_value=0.0, max_value=1.0),
            MaterialParameter(parameter_id="param_pbr_metal", name="Metallic", param_type="float", default_value=0.0, current_value=0.0, min_value=0.0, max_value=1.0),
        ]
        self._materials[mat.material_id] = mat

    def _seed_glass(self) -> None:
        mat = MaterialGraph(
            material_id="mat_glass",
            name="Glass",
            description="A transparent glass material with fresnel-based edge highlight and depth fade.",
            shading_model=MaterialShadingModel.LIT.value,
            blend_mode=MaterialBlendMode.TRANSPARENT.value,
        )
        color = ShaderNode(node_id="node_glass_color", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Tint", position_x=-300, position_y=-100, value={"r": 0.9, "g": 0.95, "b": 1.0, "a": 0.3})
        fresnel = ShaderNode(node_id="node_glass_fresnel", node_type=ShaderNodeType.FRESNEL.value, label="Fresnel", position_x=-300, position_y=50)
        depth = ShaderNode(node_id="node_glass_depth", node_type=ShaderNodeType.DEPTH_FADE.value, label="Depth Fade", position_x=-300, position_y=200)
        out_color = ShaderNode(node_id="node_glass_out_color", node_type=ShaderNodeType.OUTPUT_BASE_COLOR.value, label="Output Base Color", position_x=0, position_y=0)
        out_emissive = ShaderNode(node_id="node_glass_out_emis", node_type=ShaderNodeType.OUTPUT_EMISSIVE.value, label="Output Emissive", position_x=0, position_y=150)
        mat.nodes = [color, fresnel, depth, out_color, out_emissive]
        mat.connections = [
            ShaderConnection(connection_id="conn_glass_1", from_node="node_glass_color", from_output="color", to_node="node_glass_out_color", to_input="color"),
            ShaderConnection(connection_id="conn_glass_2", from_node="node_glass_fresnel", from_output="fresnel", to_node="node_glass_out_emis", to_input="emissive"),
            ShaderConnection(connection_id="conn_glass_3", from_node="node_glass_depth", from_output="alpha", to_node="node_glass_out_color", to_input="alpha"),
        ]
        mat.parameters = [
            MaterialParameter(parameter_id="param_glass_opacity", name="Opacity", param_type="float", default_value=0.3, current_value=0.3, min_value=0.0, max_value=1.0),
            MaterialParameter(parameter_id="param_glass_ior", name="Index of Refraction", param_type="float", default_value=1.52, current_value=1.52, min_value=1.0, max_value=2.5),
        ]
        self._materials[mat.material_id] = mat

    def _seed_metal(self) -> None:
        mat = MaterialGraph(
            material_id="mat_metal",
            name="Metal",
            description="A polished metal material with high metallic and low roughness.",
            shading_model=MaterialShadingModel.LIT.value,
            blend_mode=MaterialBlendMode.OPAQUE.value,
        )
        color = ShaderNode(node_id="node_metal_color", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Base Color", position_x=-300, position_y=-100, value={"r": 0.7, "g": 0.7, "b": 0.75, "a": 1.0})
        rough = ShaderNode(node_id="node_metal_rough", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Roughness", position_x=-300, position_y=100, value={"r": 0.15, "g": 0.15, "b": 0.15, "a": 1.0})
        metallic = ShaderNode(node_id="node_metal_metal", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Metallic", position_x=-300, position_y=250, value={"r": 1.0, "g": 1.0, "b": 1.0, "a": 1.0})
        out_color = ShaderNode(node_id="node_metal_out_color", node_type=ShaderNodeType.OUTPUT_BASE_COLOR.value, label="Output Base Color", position_x=0, position_y=-100)
        out_rough = ShaderNode(node_id="node_metal_out_rough", node_type=ShaderNodeType.OUTPUT_ROUGHNESS.value, label="Output Roughness", position_x=0, position_y=100)
        out_metal = ShaderNode(node_id="node_metal_out_metal", node_type=ShaderNodeType.OUTPUT_METALLIC.value, label="Output Metallic", position_x=0, position_y=250)
        mat.nodes = [color, rough, metallic, out_color, out_rough, out_metal]
        mat.connections = [
            ShaderConnection(connection_id="conn_metal_1", from_node="node_metal_color", from_output="color", to_node="node_metal_out_color", to_input="color"),
            ShaderConnection(connection_id="conn_metal_2", from_node="node_metal_rough", from_output="color", to_node="node_metal_out_rough", to_input="roughness"),
            ShaderConnection(connection_id="conn_metal_3", from_node="node_metal_metal", from_output="color", to_node="node_metal_out_metal", to_input="metallic"),
        ]
        mat.parameters = [
            MaterialParameter(parameter_id="param_metal_rough", name="Roughness", param_type="float", default_value=0.15, current_value=0.15, min_value=0.0, max_value=1.0),
            MaterialParameter(parameter_id="param_metal_metal", name="Metallic", param_type="float", default_value=1.0, current_value=1.0, min_value=0.0, max_value=1.0),
        ]
        self._materials[mat.material_id] = mat

    def _seed_foliage(self) -> None:
        mat = MaterialGraph(
            material_id="mat_foliage",
            name="Foliage",
            description="A subsurface-scattering foliage material with wind-driven time animation.",
            shading_model=MaterialShadingModel.SUBSURFACE.value,
            blend_mode=MaterialBlendMode.OPAQUE.value,
            two_sided=True,
        )
        color = ShaderNode(node_id="node_fol_color", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Leaf Color", position_x=-400, position_y=-100, value={"r": 0.2, "g": 0.6, "b": 0.1, "a": 1.0})
        time_node = ShaderNode(node_id="node_fol_time", node_type=ShaderNodeType.TIME.value, label="Time", position_x=-600, position_y=100)
        sin_node = ShaderNode(node_id="node_fol_sin", node_type=ShaderNodeType.SIN.value, label="Wind Sine", position_x=-400, position_y=100)
        uv = ShaderNode(node_id="node_fol_uv", node_type=ShaderNodeType.UV_COORD.value, label="UV", position_x=-600, position_y=-100)
        tex = ShaderNode(node_id="node_fol_tex", node_type=ShaderNodeType.TEXTURE_SAMPLE.value, label="Leaf Texture", position_x=-400, position_y=-250, value={"texture_slot": 0})
        out_color = ShaderNode(node_id="node_fol_out_color", node_type=ShaderNodeType.OUTPUT_BASE_COLOR.value, label="Output Base Color", position_x=0, position_y=-100)
        out_normal = ShaderNode(node_id="node_fol_out_normal", node_type=ShaderNodeType.OUTPUT_NORMAL.value, label="Output Normal", position_x=0, position_y=100)
        mat.nodes = [color, time_node, sin_node, uv, tex, out_color, out_normal]
        mat.connections = [
            ShaderConnection(connection_id="conn_fol_1", from_node="node_fol_tex", from_output="color", to_node="node_fol_out_color", to_input="color"),
            ShaderConnection(connection_id="conn_fol_2", from_node="node_fol_uv", from_output="uv", to_node="node_fol_tex", to_input="uv"),
            ShaderConnection(connection_id="conn_fol_3", from_node="node_fol_time", from_output="time", to_node="node_fol_sin", to_input="input"),
            ShaderConnection(connection_id="conn_fol_4", from_node="node_fol_sin", from_output="output", to_node="node_fol_out_normal", to_input="normal"),
        ]
        mat.parameters = [
            MaterialParameter(parameter_id="param_fol_wind", name="Wind Strength", param_type="float", default_value=0.3, current_value=0.3, min_value=0.0, max_value=1.0),
            MaterialParameter(parameter_id="param_fol_sss", name="Subsurface Amount", param_type="float", default_value=0.5, current_value=0.5, min_value=0.0, max_value=1.0),
        ]
        self._materials[mat.material_id] = mat

    def _seed_hologram(self) -> None:
        mat = MaterialGraph(
            material_id="mat_hologram",
            name="Hologram",
            description="An unlit additive hologram material with fresnel rim and emissive scan lines.",
            shading_model=MaterialShadingModel.UNLIT.value,
            blend_mode=MaterialBlendMode.ADDITIVE.value,
        )
        color = ShaderNode(node_id="node_holo_color", node_type=ShaderNodeType.COLOR_CONSTANT.value, label="Hologram Color", position_x=-400, position_y=-100, value={"r": 0.0, "g": 0.8, "b": 1.0, "a": 1.0})
        fresnel = ShaderNode(node_id="node_holo_fresnel", node_type=ShaderNodeType.FRESNEL.value, label="Fresnel Rim", position_x=-400, position_y=50)
        time_node = ShaderNode(node_id="node_holo_time", node_type=ShaderNodeType.TIME.value, label="Time", position_x=-600, position_y=200)
        sin_node = ShaderNode(node_id="node_holo_sin", node_type=ShaderNodeType.SIN.value, label="Scan Line", position_x=-400, position_y=200)
        uv = ShaderNode(node_id="node_holo_uv", node_type=ShaderNodeType.UV_COORD.value, label="UV", position_x=-600, position_y=-100)
        out_emissive = ShaderNode(node_id="node_holo_out_emis", node_type=ShaderNodeType.OUTPUT_EMISSIVE.value, label="Output Emissive", position_x=0, position_y=0)
        out_color = ShaderNode(node_id="node_holo_out_color", node_type=ShaderNodeType.OUTPUT_BASE_COLOR.value, label="Output Base Color", position_x=0, position_y=150)
        mat.nodes = [color, fresnel, time_node, sin_node, uv, out_emissive, out_color]
        mat.connections = [
            ShaderConnection(connection_id="conn_holo_1", from_node="node_holo_color", from_output="color", to_node="node_holo_out_emis", to_input="emissive"),
            ShaderConnection(connection_id="conn_holo_2", from_node="node_holo_fresnel", from_output="fresnel", to_node="node_holo_out_color", to_input="color"),
            ShaderConnection(connection_id="conn_holo_3", from_node="node_holo_time", from_output="time", to_node="node_holo_sin", to_input="input"),
            ShaderConnection(connection_id="conn_holo_4", from_node="node_holo_sin", from_output="output", to_node="node_holo_out_emis", to_input="alpha"),
            ShaderConnection(connection_id="conn_holo_5", from_node="node_holo_uv", from_output="uv", to_node="node_holo_fresnel", to_input="uv"),
        ]
        mat.parameters = [
            MaterialParameter(parameter_id="param_holo_intensity", name="Emissive Intensity", param_type="float", default_value=2.0, current_value=2.0, min_value=0.0, max_value=10.0),
            MaterialParameter(parameter_id="param_holo_scan_speed", name="Scan Speed", param_type="float", default_value=1.0, current_value=1.0, min_value=0.0, max_value=10.0),
        ]
        self._materials[mat.material_id] = mat

    # ------------------------------------------------------------------
    # Material CRUD
    # ------------------------------------------------------------------

    def create_material(
        self,
        name: str,
        shading_model: MaterialShadingModel = MaterialShadingModel.LIT,
        blend_mode: MaterialBlendMode = MaterialBlendMode.OPAQUE,
        description: str = "",
    ) -> MaterialGraph:
        """Create a new material graph with default output nodes."""
        if not name or not name.strip():
            raise ValueError("Material name must not be empty.")
        with self._lock:
            mat_id = _new_id("mat")
            graph = MaterialGraph(
                material_id=mat_id,
                name=name.strip(),
                description=description,
                shading_model=_coerce_enum(MaterialShadingModel, shading_model, MaterialShadingModel.LIT).value,
                blend_mode=_coerce_enum(MaterialBlendMode, blend_mode, MaterialBlendMode.OPAQUE).value,
            )
            self._add_default_nodes(graph)
            self._materials[mat_id] = graph
            _evict_fifo_dict(self._materials, _MAX_MATERIALS)
            self._emit("material_created", material_id=mat_id, name=name.strip())
            return graph

    def _add_default_nodes(self, graph: MaterialGraph) -> None:
        """Add the default output nodes to a freshly created material."""
        outputs = [
            (ShaderNodeType.OUTPUT_BASE_COLOR, "Output Base Color", 0, 0),
            (ShaderNodeType.OUTPUT_NORMAL, "Output Normal", 0, 150),
            (ShaderNodeType.OUTPUT_ROUGHNESS, "Output Roughness", 0, 300),
            (ShaderNodeType.OUTPUT_METALLIC, "Output Metallic", 0, 450),
        ]
        for ntype, label, x, y in outputs:
            node = ShaderNode(
                node_id=_new_id("node"),
                node_type=ntype.value,
                label=label,
                position_x=x,
                position_y=y,
            )
            graph.nodes.append(node)

    def get_material(self, material_id: str) -> Optional[MaterialGraph]:
        """Return the material graph with the given ID, or None."""
        return self._materials.get(material_id)

    def list_materials(self) -> List[MaterialGraph]:
        """Return a list of all material graphs."""
        return list(self._materials.values())

    def update_material(self, material_id: str, **kwargs: Any) -> Optional[MaterialGraph]:
        """Update fields on an existing material graph by keyword."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return None
            for key, value in kwargs.items():
                if key == "name":
                    graph.name = str(value)
                elif key == "description":
                    graph.description = str(value)
                elif key == "shading_model":
                    model = _coerce_enum(MaterialShadingModel, value, None)
                    graph.shading_model = model.value if model else graph.shading_model
                elif key == "blend_mode":
                    mode = _coerce_enum(MaterialBlendMode, value, None)
                    graph.blend_mode = mode.value if mode else graph.blend_mode
                elif key == "two_sided":
                    graph.two_sided = bool(value)
                elif key == "metadata" and isinstance(value, dict):
                    graph.metadata = dict(value)
            graph.updated_at = _now()
            graph.is_compiled = False
            self._emit("material_updated", material_id=material_id)
            return graph

    def remove_material(self, material_id: str) -> bool:
        """Remove a material graph by ID. Returns True if it existed."""
        with self._lock:
            removed = self._materials.pop(material_id, None) is not None
            if removed:
                self._emit("material_removed", material_id=material_id)
            return removed

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(
        self,
        material_id: str,
        node_type: ShaderNodeType,
        label: str = "",
        position_x: float = 0.0,
        position_y: float = 0.0,
        value: Optional[Dict[str, Any]] = None,
    ) -> Optional[ShaderNode]:
        """Add a new shader node to a material graph."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return None
            if len(graph.nodes) >= _MAX_NODES_PER_GRAPH:
                return None
            ntype = _coerce_enum(ShaderNodeType, node_type, ShaderNodeType.COLOR_CONSTANT)
            node = ShaderNode(
                node_id=_new_id("node"),
                node_type=ntype.value,
                label=label or ntype.value,
                position_x=position_x,
                position_y=position_y,
                value=dict(value) if value else {},
            )
            graph.nodes.append(node)
            graph.updated_at = _now()
            graph.is_compiled = False
            self._emit("node_added", material_id=material_id, node_id=node.node_id, node_type=ntype.value)
            return node

    def remove_node(self, material_id: str, node_id: str) -> bool:
        """Remove a node and any connections touching it."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return False
            original_len = len(graph.nodes)
            graph.nodes = [n for n in graph.nodes if n.node_id != node_id]
            if len(graph.nodes) == original_len:
                return False
            graph.connections = [
                c for c in graph.connections
                if c.from_node != node_id and c.to_node != node_id
            ]
            graph.updated_at = _now()
            graph.is_compiled = False
            self._emit("node_removed", material_id=material_id, node_id=node_id)
            return True

    def connect_nodes(
        self,
        material_id: str,
        from_node: str,
        from_output: str,
        to_node: str,
        to_input: str,
    ) -> Optional[ShaderConnection]:
        """Create a directed connection between two nodes."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return None
            if from_node == to_node:
                return None
            if len(graph.connections) >= _MAX_CONNECTIONS_PER_GRAPH:
                return None
            node_ids = {n.node_id for n in graph.nodes}
            if from_node not in node_ids or to_node not in node_ids:
                return None
            conn = ShaderConnection(
                connection_id=_new_id("conn"),
                from_node=from_node,
                from_output=from_output,
                to_node=to_node,
                to_input=to_input,
            )
            graph.connections.append(conn)
            graph.updated_at = _now()
            graph.is_compiled = False
            self._emit("nodes_connected", material_id=material_id, connection_id=conn.connection_id)
            return conn

    def disconnect_nodes(self, material_id: str, connection_id: str) -> bool:
        """Remove a connection by ID."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return False
            original_len = len(graph.connections)
            graph.connections = [c for c in graph.connections if c.connection_id != connection_id]
            if len(graph.connections) == original_len:
                return False
            graph.updated_at = _now()
            graph.is_compiled = False
            self._emit("nodes_disconnected", material_id=material_id, connection_id=connection_id)
            return True

    # ------------------------------------------------------------------
    # Parameter management
    # ------------------------------------------------------------------

    def set_parameter(self, material_id: str, name: str, value: Any) -> bool:
        """Set the current value of a named parameter on a material."""
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return False
            for param in graph.parameters:
                if param.name == name:
                    param.current_value = value
                    graph.updated_at = _now()
                    graph.is_compiled = False
                    self._emit("parameter_set", material_id=material_id, name=name, value=value)
                    return True
            if len(graph.parameters) >= _MAX_PARAMETERS_PER_MATERIAL:
                return False
            param = MaterialParameter(
                parameter_id=_new_id("param"),
                name=name,
                param_type="float" if isinstance(value, (int, float)) else "color",
                default_value=value,
                current_value=value,
            )
            graph.parameters.append(param)
            graph.updated_at = _now()
            self._emit("parameter_created", material_id=material_id, name=name, value=value)
            return True

    def get_parameter(self, material_id: str, name: str) -> Optional[Any]:
        """Return the current value of a named parameter, or None."""
        graph = self._materials.get(material_id)
        if graph is None:
            return None
        for param in graph.parameters:
            if param.name == name:
                return param.current_value
        return None

    # ------------------------------------------------------------------
    # Compilation and code generation
    # ------------------------------------------------------------------

    def compile_shader(self, material_id: str) -> ShaderCompilationResult:
        """Compile a material graph into shader code."""
        start = time.time()
        with self._lock:
            graph = self._materials.get(material_id)
            if graph is None:
                return ShaderCompilationResult(
                    material_id=material_id,
                    success=False,
                    errors=["Material not found."],
                )
            validation = self.validate_graph(material_id)
            if not validation["valid"]:
                return ShaderCompilationResult(
                    material_id=material_id,
                    success=False,
                    errors=validation["errors"],
                    warnings=validation["warnings"],
                    duration_ms=(time.time() - start) * 1000.0,
                )
            code = self.get_shader_code(material_id)
            graph.shader_code = code
            graph.is_compiled = True
            tex_count = sum(1 for n in graph.nodes if n.node_type == ShaderNodeType.TEXTURE_SAMPLE.value)
            instr_count = len(graph.nodes) * 3 + len(graph.connections) * 2
            self._emit("shader_compiled", material_id=material_id, instruction_count=instr_count)
            return ShaderCompilationResult(
                material_id=material_id,
                success=True,
                shader_code=code,
                warnings=validation["warnings"],
                duration_ms=(time.time() - start) * 1000.0,
                instruction_count=instr_count,
                texture_samples=tex_count,
            )

    def get_shader_code(self, material_id: str) -> str:
        """Generate pseudo-shader code from a material graph."""
        graph = self._materials.get(material_id)
        if graph is None:
            return ""
        lines: List[str] = [
            f"// Shader: {graph.name}",
            f"// Shading Model: {graph.shading_model}",
            f"// Blend Mode: {graph.blend_mode}",
            f"// Two Sided: {graph.two_sided}",
            "",
            "uniform float time;",
            "uniform sampler2D textures[8];",
            "",
            "struct MaterialInput {",
            "    vec2 uv;",
            "    vec3 normal;",
            "    vec3 position;",
            "};",
            "",
            "struct MaterialOutput {",
            "    vec4 base_color;",
            "    vec3 normal;",
            "    vec3 emissive;",
            "    float roughness;",
            "    float metallic;",
            "};",
            "",
            "MaterialOutput evaluate_material(MaterialInput IN) {",
            "    MaterialOutput OUT;",
            "    OUT.base_color = vec4(1.0, 1.0, 1.0, 1.0);",
            "    OUT.normal = vec3(0.0, 0.0, 1.0);",
            "    OUT.emissive = vec3(0.0, 0.0, 0.0);",
            "    OUT.roughness = 0.5;",
            "    OUT.metallic = 0.0;",
            "",
        ]
        for node in graph.nodes:
            lines.append(f"    // Node: {node.label} ({node.node_type})")
            if node.node_type == ShaderNodeType.COLOR_CONSTANT.value:
                r = node.value.get("r", 1.0)
                g = node.value.get("g", 1.0)
                b = node.value.get("b", 1.0)
                a = node.value.get("a", 1.0)
                lines.append(f"    vec4 v_{node.node_id} = vec4({r}, {g}, {b}, {a});")
            elif node.node_type == ShaderNodeType.TEXTURE_SAMPLE.value:
                lines.append(f"    vec4 v_{node.node_id} = texture2D(textures[0], IN.uv);")
            elif node.node_type == ShaderNodeType.UV_COORD.value:
                lines.append(f"    vec2 v_{node.node_id} = IN.uv;")
            elif node.node_type == ShaderNodeType.VERTEX_POSITION.value:
                lines.append(f"    vec3 v_{node.node_id} = IN.position;")
            elif node.node_type == ShaderNodeType.NORMAL_VECTOR.value:
                lines.append(f"    vec3 v_{node.node_id} = IN.normal;")
            elif node.node_type == ShaderNodeType.TIME.value:
                lines.append(f"    float v_{node.node_id} = time;")
            elif node.node_type == ShaderNodeType.SIN.value:
                lines.append(f"    float v_{node.node_id} = sin(time);")
            elif node.node_type == ShaderNodeType.COS.value:
                lines.append(f"    float v_{node.node_id} = cos(time);")
            elif node.node_type == ShaderNodeType.FRESNEL.value:
                lines.append(f"    float v_{node.node_id} = pow(1.0 - dot(IN.normal, vec3(0.0, 0.0, 1.0)), 3.0);")
            elif node.node_type == ShaderNodeType.DEPTH_FADE.value:
                lines.append(f"    float v_{node.node_id} = 1.0; // depth fade placeholder")
            elif node.node_type == ShaderNodeType.MATH_ADD.value:
                lines.append(f"    vec4 v_{node.node_id} = vec4(0.0); // add")
            elif node.node_type == ShaderNodeType.MATH_MULTIPLY.value:
                lines.append(f"    vec4 v_{node.node_id} = vec4(0.0); // multiply")
            elif node.node_type == ShaderNodeType.MATH_SUBTRACT.value:
                lines.append(f"    vec4 v_{node.node_id} = vec4(0.0); // subtract")
            elif node.node_type == ShaderNodeType.POW.value:
                lines.append(f"    float v_{node.node_id} = pow(1.0, 2.0);")
            elif node.node_type == ShaderNodeType.LERP.value:
                lines.append(f"    vec4 v_{node.node_id} = mix(vec4(0.0), vec4(1.0), 0.5);")
            elif node.node_type == ShaderNodeType.CLAMP.value:
                lines.append(f"    vec4 v_{node.node_id} = clamp(vec4(0.0), vec4(0.0), vec4(1.0));")
            elif node.node_type == ShaderNodeType.OUTPUT_BASE_COLOR.value:
                lines.append(f"    OUT.base_color = v_{node.node_id}; // bound from inputs")
            elif node.node_type == ShaderNodeType.OUTPUT_NORMAL.value:
                lines.append(f"    OUT.normal = v_{node.node_id}; // bound from inputs")
            elif node.node_type == ShaderNodeType.OUTPUT_EMISSIVE.value:
                lines.append(f"    OUT.emissive = v_{node.node_id}.rgb; // bound from inputs")
            elif node.node_type == ShaderNodeType.OUTPUT_ROUGHNESS.value:
                lines.append(f"    OUT.roughness = v_{node.node_id}.r; // bound from inputs")
            elif node.node_type == ShaderNodeType.OUTPUT_METALLIC.value:
                lines.append(f"    OUT.metallic = v_{node.node_id}.r; // bound from inputs")
            lines.append("")
        for conn in graph.connections:
            lines.append(f"    // Connection: {conn.from_node}.{conn.from_output} -> {conn.to_node}.{conn.to_input}")
        lines.append("    return OUT;")
        lines.append("}")
        return "\n".join(lines)

    def preview_material(self, material_id: str) -> Dict[str, Any]:
        """Generate preview metadata for a material."""
        graph = self._materials.get(material_id)
        if graph is None:
            return {}
        return {
            "material_id": material_id,
            "name": graph.name,
            "shading_model": graph.shading_model,
            "blend_mode": graph.blend_mode,
            "is_compiled": graph.is_compiled,
            "node_count": len(graph.nodes),
            "connection_count": len(graph.connections),
            "parameter_count": len(graph.parameters),
            "thumbnail_url": f"preview://{material_id}",
        }

    def optimize_material(self, material_id: str) -> Dict[str, Any]:
        """Analyze a material graph and return optimization suggestions."""
        graph = self._materials.get(material_id)
        if graph is None:
            return {"success": False, "errors": ["Material not found."]}
        suggestions: List[str] = []
        node_count = len(graph.nodes)
        conn_count = len(graph.connections)
        tex_count = sum(1 for n in graph.nodes if n.node_type == ShaderNodeType.TEXTURE_SAMPLE.value)
        if tex_count > 4:
            suggestions.append("High texture sample count. Consider combining textures into an atlas.")
        if node_count > 30:
            suggestions.append("Large node graph. Consider simplifying by removing unused nodes.")
        unused = self._find_unused_nodes(graph)
        if unused:
            suggestions.append(f"Found {len(unused)} unused nodes that can be removed: {', '.join(unused[:5])}")
        redundant = self._find_redundant_constants(graph)
        if redundant:
            suggestions.append(f"Found {len(redundant)} constant nodes that could be merged into parameters.")
        return {
            "success": True,
            "material_id": material_id,
            "node_count": node_count,
            "connection_count": conn_count,
            "texture_samples": tex_count,
            "unused_nodes": unused,
            "redundant_constants": redundant,
            "suggestions": suggestions,
            "estimated_cost_ms": node_count * 0.02 + tex_count * 0.5,
        }

    def _find_unused_nodes(self, graph: MaterialGraph) -> List[str]:
        """Return IDs of nodes that are neither outputs nor connected to an output."""
        output_ids = {n.node_id for n in graph.nodes if n.node_type.startswith("output_")}
        connected: Set[str] = set()
        frontier = list(output_ids)
        while frontier:
            current = frontier.pop()
            for conn in graph.connections:
                if conn.to_node == current and conn.from_node not in connected:
                    connected.add(conn.from_node)
                    frontier.append(conn.from_node)
        all_ids = {n.node_id for n in graph.nodes}
        return sorted(all_ids - connected - output_ids)

    def _find_redundant_constants(self, graph: MaterialGraph) -> List[str]:
        """Return IDs of color-constant nodes with identical values."""
        seen: Dict[str, str] = {}
        redundant: List[str] = []
        for n in graph.nodes:
            if n.node_type != ShaderNodeType.COLOR_CONSTANT.value:
                continue
            key = str(sorted(n.value.items()))
            if key in seen:
                redundant.append(n.node_id)
            else:
                seen[key] = n.node_id
        return redundant

    def validate_graph(self, material_id: str) -> Dict[str, Any]:
        """Validate a material graph for correctness."""
        graph = self._materials.get(material_id)
        if graph is None:
            return {"valid": False, "errors": ["Material not found."], "warnings": []}
        errors: List[str] = []
        warnings: List[str] = []
        output_types = {ShaderNodeType.OUTPUT_BASE_COLOR.value, ShaderNodeType.OUTPUT_NORMAL.value,
                        ShaderNodeType.OUTPUT_EMISSIVE.value, ShaderNodeType.OUTPUT_ROUGHNESS.value,
                        ShaderNodeType.OUTPUT_METALLIC.value}
        has_output = any(n.node_type in output_types for n in graph.nodes)
        if not has_output:
            errors.append("Material graph has no output nodes.")
        node_ids = {n.node_id for n in graph.nodes}
        for conn in graph.connections:
            if conn.from_node not in node_ids:
                errors.append(f"Connection {conn.connection_id} references missing from_node '{conn.from_node}'.")
            if conn.to_node not in node_ids:
                errors.append(f"Connection {conn.connection_id} references missing to_node '{conn.to_node}'.")
        if self._has_cycles(graph):
            errors.append("Material graph contains a cycle.")
        unused = self._find_unused_nodes(graph)
        if unused:
            warnings.append(f"{len(unused)} node(s) are not connected to any output.")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _has_cycles(self, graph: MaterialGraph) -> bool:
        """Detect cycles in the shader graph using DFS."""
        adj: Dict[str, List[str]] = {}
        for conn in graph.connections:
            adj.setdefault(conn.from_node, []).append(conn.to_node)
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n.node_id: WHITE for n in graph.nodes}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color.get(neighbor, WHITE) == GRAY:
                    return True
                if color.get(neighbor, WHITE) == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for node_id in list(color.keys()):
            if color[node_id] == WHITE and dfs(node_id):
                return True
        return False

    def list_nodes(self, material_id: str) -> List[ShaderNode]:
        """Return all nodes in a material graph."""
        graph = self._materials.get(material_id)
        return list(graph.nodes) if graph else []

    def list_connections(self, material_id: str) -> List[ShaderConnection]:
        """Return all connections in a material graph."""
        graph = self._materials.get(material_id)
        return list(graph.connections) if graph else []

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_generate_material(self, description: str) -> MaterialGraph:
        """Generate a material graph from a natural-language description."""
        if not description or not description.strip():
            raise ValueError("Description must not be empty.")
        desc_lower = description.lower()
        if any(w in desc_lower for w in ("glass", "transparent", "crystal", "window")):
            shading = MaterialShadingModel.LIT
            blend = MaterialBlendMode.TRANSPARENT
        elif any(w in desc_lower for w in ("hologram", "holographic", "glow", "neon", "energy")):
            shading = MaterialShadingModel.UNLIT
            blend = MaterialBlendMode.ADDITIVE
        elif any(w in desc_lower for w in ("skin", "flesh", "wax", "subsurface", "foliage", "leaf", "plant")):
            shading = MaterialShadingModel.SUBSURFACE
            blend = MaterialBlendMode.OPAQUE
        elif any(w in desc_lower for w in ("cloth", "fabric", "cotton", "wool")):
            shading = MaterialShadingModel.CLOTH
            blend = MaterialBlendMode.OPAQUE
        elif any(w in desc_lower for w in ("hair", "fur")):
            shading = MaterialShadingModel.HAIR
            blend = MaterialBlendMode.OPAQUE
        else:
            shading = MaterialShadingModel.LIT
            blend = MaterialBlendMode.OPAQUE
        mat = self.create_material(description.strip()[:60], shading, blend, description.strip())
        if any(w in desc_lower for w in ("metal", "steel", "iron", "chrome")):
            self.set_parameter(mat.material_id, "Metallic", 0.9)
            self.set_parameter(mat.material_id, "Roughness", 0.2)
            self.add_node(mat.material_id, ShaderNodeType.FRESNEL, "Fresnel", -200, 100)
        if any(w in desc_lower for w in ("wet", "smooth", "polished", "glossy")):
            self.set_parameter(mat.material_id, "Roughness", 0.1)
        if any(w in desc_lower for w in ("rough", "rock", "stone", "concrete")):
            self.set_parameter(mat.material_id, "Roughness", 0.85)
            self.set_parameter(mat.material_id, "Metallic", 0.0)
        if any(w in desc_lower for w in ("emissive", "glow", "lava", "magma")):
            self.add_node(mat.material_id, ShaderNodeType.OUTPUT_EMISSIVE, "Output Emissive", 0, 600)
        if any(w in desc_lower for w in ("animated", "wind", "flow", "scroll")):
            self.add_node(mat.material_id, ShaderNodeType.TIME, "Time", -400, 200)
            self.add_node(mat.material_id, ShaderNodeType.SIN, "Sine Wave", -200, 200)
        self._emit("ai_generated_material", material_id=mat.material_id, description=description[:100])
        return mat

    def ai_optimize_shader(self, material_id: str) -> Dict[str, Any]:
        """Analyze and optimize the shader code for a material."""
        graph = self._materials.get(material_id)
        if graph is None:
            return {"success": False, "errors": ["Material not found."]}
        result = self.optimize_material(material_id)
        applied: List[str] = []
        unused = result.get("unused_nodes", [])
        for node_id in unused:
            self.remove_node(material_id, node_id)
            applied.append(f"Removed unused node {node_id}")
        tex_count = result.get("texture_samples", 0)
        if tex_count > 4:
            applied.append("Flagged for texture atlas consolidation")
        if not graph.is_compiled:
            self.compile_shader(material_id)
            applied.append("Recompiled shader after optimization")
        self._emit("ai_optimized_shader", material_id=material_id, applied=applied)
        return {
            "success": True,
            "material_id": material_id,
            "applied_optimizations": applied,
            "original_node_count": result.get("node_count", 0),
            "final_node_count": len(graph.nodes),
            "suggestions": result.get("suggestions", []),
        }

    def ai_suggest_nodes(self, description: str) -> List[Dict[str, Any]]:
        """Suggest shader node types based on a description."""
        if not description or not description.strip():
            return []
        desc_lower = description.lower()
        suggestions: List[Dict[str, Any]] = []
        suggestion_map: List[Tuple[List[str], ShaderNodeType, str]] = [
            (["metal", "steel", "chrome"], ShaderNodeType.FRESNEL, "Add a Fresnel node for realistic metal edge highlights."),
            (["water", "glass", "transparent"], ShaderNodeType.DEPTH_FADE, "Add a Depth Fade node for soft edges where the surface meets the background."),
            (["animated", "wind", "flow", "scroll"], ShaderNodeType.TIME, "Add a Time node to drive animated effects."),
            (["wave", "sine", "oscillate"], ShaderNodeType.SIN, "Add a Sine node for wave-based animations."),
            (["glow", "emissive", "lava"], ShaderNodeType.OUTPUT_EMISSIVE, "Add an Emissive output to make the material self-illuminating."),
            (["texture", "albedo", "color map"], ShaderNodeType.TEXTURE_SAMPLE, "Add a Texture Sample node for albedo or detail textures."),
            (["rough", "smooth", "polished"], ShaderNodeType.OUTPUT_ROUGHNESS, "Add a Roughness output to control surface smoothness."),
            (["normal", "bump", "detail"], ShaderNodeType.OUTPUT_NORMAL, "Add a Normal output for surface detail."),
            (["blend", "mix", "transition"], ShaderNodeType.LERP, "Add a Lerp node to blend between two inputs."),
            (["clamp", "limit", "range"], ShaderNodeType.CLAMP, "Add a Clamp node to constrain values to a range."),
            (["power", "exponent"], ShaderNodeType.POW, "Add a Pow node for exponential falloff effects."),
        ]
        for keywords, ntype, reason in suggestion_map:
            if any(w in desc_lower for w in keywords):
                suggestions.append({
                    "node_type": ntype.value,
                    "label": ntype.value.replace("_", " ").title(),
                    "reason": reason,
                })
        if not suggestions:
            suggestions.append({
                "node_type": ShaderNodeType.COLOR_CONSTANT.value,
                "label": "Color Constant",
                "reason": "A color constant is a good starting point for any material.",
            })
        self._emit("ai_suggested_nodes", description=description[:100], count=len(suggestions))
        return suggestions


# ===========================================================================
# 2. Terrain Sculpting Editor
# ===========================================================================

class BrushType(Enum):
    """Types of terrain sculpting brushes."""
    RAISE = "raise"
    LOWER = "lower"
    SMOOTH = "smooth"
    FLATTEN = "flatten"
    NOISE = "noise"
    ERODE = "erode"
    PAINT_TEXTURE = "paint_texture"
    PAINT_FOLIAGE = "paint_foliage"


class TerrainLayerType(Enum):
    """Types of terrain texture layers."""
    GRASS = "grass"
    ROCK = "rock"
    SAND = "sand"
    SNOW = "snow"
    DIRT = "dirt"
    WATER = "water"
    ROAD = "road"


@dataclass
class TerrainLayer:
    """A texture layer painted onto the terrain."""
    layer_id: str
    name: str = ""
    layer_type: str = TerrainLayerType.GRASS.value
    texture_path: str = ""
    tiling: float = 1.0
    slope_min: float = 0.0
    slope_max: float = 90.0
    height_min: float = 0.0
    height_max: float = math.inf
    opacity: float = 1.0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FoliagePatch:
    """A placed patch of foliage on the terrain."""
    patch_id: str
    foliage_type: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    density: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainBrush:
    """Configuration for a terrain sculpting brush."""
    brush_id: str = ""
    brush_type: str = BrushType.RAISE.value
    size: float = 50.0
    strength: float = 0.5
    falloff: float = 0.5
    target_height: float = 0.0
    noise_scale: float = 1.0
    layer_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainStroke:
    """A recorded sculpting stroke applied to the terrain."""
    stroke_id: str
    terrain_id: str = ""
    brush_type: str = BrushType.RAISE.value
    positions: List[Tuple[float, float]] = field(default_factory=list)
    size: float = 50.0
    strength: float = 0.5
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TerrainData:
    """A complete terrain definition with heightmap and layers."""
    terrain_id: str
    name: str = ""
    description: str = ""
    width: int = 512
    height: int = 512
    height_scale: float = 100.0
    heightmap: List[List[float]] = field(default_factory=list)
    layers: List[TerrainLayer] = field(default_factory=list)
    foliage: List[FoliagePatch] = field(default_factory=list)
    strokes: List[TerrainStroke] = field(default_factory=list)
    current_brush: TerrainBrush = field(default_factory=TerrainBrush)
    seed: int = 0
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class TerrainSculptingEditor:
    """Heightmap-based terrain editor with brush tools, texture splatting,
    foliage placement, and erosion simulation.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._terrains: Dict[str, TerrainData] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"ter_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed(self) -> None:
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_mountain_valley()
            self._seed_desert_dunes()
            self._seed_island()
            self._seeded = True

    def _seed_mountain_valley(self) -> None:
        ter = TerrainData(
            terrain_id="ter_mountain_valley",
            name="Mountain Valley",
            description="A mountainous valley terrain with grassy lowlands and rocky peaks.",
            width=512,
            height=512,
            height_scale=200.0,
            seed=42,
        )
        ter.heightmap = self._generate_mountain_heightmap(512, 512, 42)
        ter.layers = [
            TerrainLayer(layer_id="layer_mv_grass", name="Grass", layer_type=TerrainLayerType.GRASS.value, texture_path="textures/grass.dds", tiling=8.0, height_min=0.0, height_max=100.0, slope_max=30.0),
            TerrainLayer(layer_id="layer_mv_rock", name="Rock", layer_type=TerrainLayerType.ROCK.value, texture_path="textures/rock.dds", tiling=4.0, slope_min=30.0, height_min=50.0),
            TerrainLayer(layer_id="layer_mv_dirt", name="Dirt", layer_type=TerrainLayerType.DIRT.value, texture_path="textures/dirt.dds", tiling=6.0, slope_min=15.0, slope_max=35.0),
        ]
        for i in range(20):
            x = random.uniform(0, 512)
            y = random.uniform(0, 512)
            h = self._sample_heightmap(ter, x, y)
            ter.foliage.append(FoliagePatch(patch_id=f"fol_mv_{i:04d}", foliage_type="pine_tree", x=x, y=y, z=h, scale=random.uniform(0.8, 1.4), rotation=random.uniform(0, 360)))
        self._terrains[ter.terrain_id] = ter

    def _seed_desert_dunes(self) -> None:
        ter = TerrainData(
            terrain_id="ter_desert_dunes",
            name="Desert Dunes",
            description="Rolling sand dunes with wind-sculpted ridges.",
            width=512,
            height=512,
            height_scale=60.0,
            seed=99,
        )
        ter.heightmap = self._generate_dune_heightmap(512, 512, 99)
        ter.layers = [
            TerrainLayer(layer_id="layer_dd_sand", name="Sand", layer_type=TerrainLayerType.SAND.value, texture_path="textures/sand.dds", tiling=12.0, height_min=0.0),
            TerrainLayer(layer_id="layer_dd_rock", name="Desert Rock", layer_type=TerrainLayerType.ROCK.value, texture_path="textures/desert_rock.dds", tiling=4.0, slope_min=40.0),
        ]
        self._terrains[ter.terrain_id] = ter

    def _seed_island(self) -> None:
        ter = TerrainData(
            terrain_id="ter_island",
            name="Island",
            description="A tropical island with beaches, grassland, and a central mountain.",
            width=512,
            height=512,
            height_scale=150.0,
            seed=7,
        )
        ter.heightmap = self._generate_island_heightmap(512, 512, 7)
        ter.layers = [
            TerrainLayer(layer_id="layer_is_sand", name="Beach Sand", layer_type=TerrainLayerType.SAND.value, texture_path="textures/sand.dds", tiling=10.0, height_min=0.0, height_max=15.0),
            TerrainLayer(layer_id="layer_is_grass", name="Grass", layer_type=TerrainLayerType.GRASS.value, texture_path="textures/grass.dds", tiling=8.0, height_min=10.0, height_max=80.0),
            TerrainLayer(layer_id="layer_is_rock", name="Rock", layer_type=TerrainLayerType.ROCK.value, texture_path="textures/rock.dds", tiling=4.0, slope_min=35.0, height_min=60.0),
            TerrainLayer(layer_id="layer_is_water", name="Water", layer_type=TerrainLayerType.WATER.value, texture_path="textures/water.dds", tiling=2.0, height_max=0.0),
        ]
        for i in range(15):
            x = random.uniform(100, 412)
            y = random.uniform(100, 412)
            h = self._sample_heightmap(ter, x, y)
            ter.foliage.append(FoliagePatch(patch_id=f"fol_is_{i:04d}", foliage_type="palm_tree", x=x, y=y, z=h, scale=random.uniform(0.9, 1.3)))
        self._terrains[ter.terrain_id] = ter

    def _generate_mountain_heightmap(self, w: int, h: int, seed: int) -> List[List[float]]:
        hm: List[List[float]] = []
        for y in range(h):
            row: List[float] = []
            for x in range(w):
                nx = x / w * 4.0
                ny = y / h * 4.0
                val = 0.0
                amp = 1.0
                freq = 1.0
                for _ in range(4):
                    val += _value_noise_2d(nx * freq, ny * freq, seed) * amp
                    amp *= 0.5
                    freq *= 2.0
                row.append(val * 200.0)
            hm.append(row)
        return hm

    def _generate_dune_heightmap(self, w: int, h: int, seed: int) -> List[List[float]]:
        hm: List[List[float]] = []
        for y in range(h):
            row: List[float] = []
            for x in range(w):
                nx = x / w * 8.0
                ny = y / h * 8.0
                val = _value_noise_2d(nx, ny, seed) * 0.6 + _value_noise_2d(nx * 2.0, ny * 2.0, seed + 1) * 0.4
                row.append(val * 60.0)
            hm.append(row)
        return hm

    def _generate_island_heightmap(self, w: int, h: int, seed: int) -> List[List[float]]:
        hm: List[List[float]] = []
        cx, cy = w / 2.0, h / 2.0
        max_dist = math.sqrt(cx * cx + cy * cy)
        for y in range(h):
            row: List[float] = []
            for x in range(w):
                nx = x / w * 3.0
                ny = y / h * 3.0
                val = _value_noise_2d(nx, ny, seed)
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2) / max_dist
                falloff = _clamp(1.0 - dist * dist * 1.5, 0.0, 1.0)
                row.append(val * 150.0 * falloff - 20.0)
            hm.append(row)
        return hm

    def _sample_heightmap(self, terrain: TerrainData, x: float, y: float) -> float:
        ix = int(_clamp(x, 0, terrain.width - 1))
        iy = int(_clamp(y, 0, terrain.height - 1))
        if not terrain.heightmap or iy >= len(terrain.heightmap):
            return 0.0
        if ix >= len(terrain.heightmap[iy]):
            return 0.0
        return terrain.heightmap[iy][ix]

    # ------------------------------------------------------------------
    # Terrain CRUD
    # ------------------------------------------------------------------

    def create_terrain(
        self,
        name: str,
        width: int = 512,
        height: int = 512,
        height_scale: float = 100.0,
        seed: int = 0,
        description: str = "",
    ) -> TerrainData:
        """Create a new terrain with a generated heightmap."""
        if not name or not name.strip():
            raise ValueError("Terrain name must not be empty.")
        w = max(32, _safe_int(width, 512))
        h = max(32, _safe_int(height, 512))
        with self._lock:
            ter_id = _new_id("ter")
            ter = TerrainData(
                terrain_id=ter_id,
                name=name.strip(),
                description=description,
                width=w,
                height=h,
                height_scale=max(1.0, _safe_float(height_scale, 100.0)),
                seed=_safe_int(seed, 0),
            )
            ter.heightmap = self.generate_heightmap(ter_id, w, h, seed) if False else [[0.0] * w for _ in range(h)]
            ter.current_brush = TerrainBrush(brush_id=f"brush_{ter_id}")
            self._terrains[ter_id] = ter
            _evict_fifo_dict(self._terrains, _MAX_TERRAINS)
            self._emit("terrain_created", terrain_id=ter_id, name=name.strip())
            return ter

    def get_terrain(self, terrain_id: str) -> Optional[TerrainData]:
        """Return the terrain with the given ID, or None."""
        return self._terrains.get(terrain_id)

    def list_terrains(self) -> List[TerrainData]:
        """Return a list of all terrains."""
        return list(self._terrains.values())

    def update_terrain(self, terrain_id: str, **kwargs: Any) -> Optional[TerrainData]:
        """Update fields on an existing terrain by keyword."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return None
            for key, value in kwargs.items():
                if key == "name":
                    ter.name = str(value)
                elif key == "description":
                    ter.description = str(value)
                elif key == "height_scale":
                    ter.height_scale = max(1.0, _safe_float(value, ter.height_scale))
                elif key == "seed":
                    ter.seed = _safe_int(value, ter.seed)
                elif key == "metadata" and isinstance(value, dict):
                    ter.metadata = dict(value)
            ter.updated_at = _now()
            self._emit("terrain_updated", terrain_id=terrain_id)
            return ter

    def remove_terrain(self, terrain_id: str) -> bool:
        """Remove a terrain by ID."""
        with self._lock:
            removed = self._terrains.pop(terrain_id, None) is not None
            if removed:
                self._emit("terrain_removed", terrain_id=terrain_id)
            return removed

    # ------------------------------------------------------------------
    # Sculpting
    # ------------------------------------------------------------------

    def sculpt(
        self,
        terrain_id: str,
        x: float,
        y: float,
        brush_type: BrushType = BrushType.RAISE,
        size: float = 50.0,
        strength: float = 0.5,
        falloff: float = 0.5,
    ) -> bool:
        """Apply a sculpting brush at the given position on the terrain."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return False
            btype = _coerce_enum(BrushType, brush_type, BrushType.RAISE)
            radius = max(1.0, _safe_float(size, 50.0))
            str_val = _clamp(_safe_float(strength, 0.5))
            fall = _clamp(_safe_float(falloff, 0.5))
            ix = int(x)
            iy = int(y)
            r_int = int(radius)
            for dy in range(-r_int, r_int + 1):
                for dx in range(-r_int, r_int + 1):
                    px, py = ix + dx, iy + dy
                    if px < 0 or px >= ter.width or py < 0 or py >= ter.height:
                        continue
                    dist = math.sqrt(dx * dx + dy * dy)
                    if dist > radius:
                        continue
                    falloff_weight = 1.0 - (dist / radius)
                    falloff_weight = falloff_weight ** (1.0 + fall * 3.0)
                    if btype == BrushType.RAISE:
                        ter.heightmap[py][px] += str_val * falloff_weight * 10.0
                    elif btype == BrushType.LOWER:
                        ter.heightmap[py][px] -= str_val * falloff_weight * 10.0
                    elif btype == BrushType.FLATTEN:
                        ter.heightmap[py][px] = _lerp(ter.heightmap[py][px], ter.current_brush.target_height, falloff_weight * str_val)
                    elif btype == BrushType.SMOOTH:
                        neighbors: List[float] = []
                        for sy in range(max(0, py - 1), min(ter.height, py + 2)):
                            for sx in range(max(0, px - 1), min(ter.width, px + 2)):
                                neighbors.append(ter.heightmap[sy][sx])
                        if neighbors:
                            avg = sum(neighbors) / len(neighbors)
                            ter.heightmap[py][px] = _lerp(ter.heightmap[py][px], avg, falloff_weight * str_val)
                    elif btype == BrushType.NOISE:
                        ter.heightmap[py][px] += (random.random() - 0.5) * str_val * falloff_weight * 20.0
                    elif btype == BrushType.ERODE:
                        ter.heightmap[py][px] -= str_val * falloff_weight * 5.0
                        if py + 1 < ter.height:
                            ter.heightmap[py + 1][px] += str_val * falloff_weight * 2.0
            stroke = TerrainStroke(
                stroke_id=_new_id("stroke"),
                terrain_id=terrain_id,
                brush_type=btype.value,
                positions=[(x, y)],
                size=size,
                strength=strength,
            )
            ter.strokes.append(stroke)
            _evict_fifo_list(ter.strokes, _MAX_STROKES_PER_TERRAIN)
            ter.updated_at = _now()
            self._emit("terrain_sculpted", terrain_id=terrain_id, brush_type=btype.value, x=x, y=y)
            return True

    def paint_texture(
        self,
        terrain_id: str,
        x: float,
        y: float,
        layer_id: str,
        size: float = 50.0,
        strength: float = 0.5,
    ) -> bool:
        """Paint a texture layer onto the terrain at the given position."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return False
            layer = None
            for l in ter.layers:
                if l.layer_id == layer_id:
                    layer = l
                    break
            if layer is None:
                return False
            layer.opacity = _clamp(layer.opacity + _safe_float(strength, 0.1) * 0.1, 0.0, 1.0)
            stroke = TerrainStroke(
                stroke_id=_new_id("stroke"),
                terrain_id=terrain_id,
                brush_type=BrushType.PAINT_TEXTURE.value,
                positions=[(x, y)],
                size=size,
                strength=strength,
            )
            stroke.layer_id = layer_id if hasattr(stroke, "layer_id") else ""
            ter.strokes.append(stroke)
            _evict_fifo_list(ter.strokes, _MAX_STROKES_PER_TERRAIN)
            ter.updated_at = _now()
            self._emit("texture_painted", terrain_id=terrain_id, layer_id=layer_id, x=x, y=y)
            return True

    def paint_foliage(
        self,
        terrain_id: str,
        x: float,
        y: float,
        foliage_type: str,
        density: int = 5,
        size: float = 50.0,
    ) -> List[FoliagePatch]:
        """Place foliage patches on the terrain within a brush radius."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return []
            if len(ter.foliage) >= _MAX_FOLIAGE_PATCHES:
                return []
            placed: List[FoliagePatch] = []
            count = max(1, _safe_int(density, 5))
            radius = max(1.0, _safe_float(size, 50.0))
            for _ in range(count):
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(0, radius)
                fx = x + math.cos(angle) * r
                fy = y + math.sin(angle) * r
                if fx < 0 or fx >= ter.width or fy < 0 or fy >= ter.height:
                    continue
                fz = self._sample_heightmap(ter, fx, fy)
                patch = FoliagePatch(
                    patch_id=_new_id("fol"),
                    foliage_type=foliage_type,
                    x=fx,
                    y=fy,
                    z=fz,
                    scale=random.uniform(0.7, 1.5),
                    rotation=random.uniform(0, 360),
                    density=1,
                )
                ter.foliage.append(patch)
                placed.append(patch)
            _evict_fifo_list(ter.foliage, _MAX_FOLIAGE_PATCHES)
            ter.updated_at = _now()
            self._emit("foliage_painted", terrain_id=terrain_id, foliage_type=foliage_type, count=len(placed))
            return placed

    def apply_erosion(self, terrain_id: str, iterations: int = 100, strength: float = 0.1) -> Dict[str, Any]:
        """Simulate hydraulic erosion on the terrain heightmap."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return {"success": False, "errors": ["Terrain not found."]}
            iters = max(1, _safe_int(iterations, 100))
            str_val = _clamp(_safe_float(strength, 0.1))
            for _ in range(iters):
                x = random.randint(1, ter.width - 2)
                y = random.randint(1, ter.height - 2)
                sediment = 0.0
                for _step in range(32):
                    lowest_x, lowest_y = x, y
                    lowest_h = ter.heightmap[y][x]
                    for dx in (-1, 0, 1):
                        for dy in (-1, 0, 1):
                            if dx == 0 and dy == 0:
                                continue
                            nx, ny = x + dx, y + dy
                            if 0 <= nx < ter.width and 0 <= ny < ter.height:
                                if ter.heightmap[ny][nx] < lowest_h:
                                    lowest_h = ter.heightmap[ny][nx]
                                    lowest_x, lowest_y = nx, ny
                    if lowest_x == x and lowest_y == y:
                        ter.heightmap[y][x] += sediment * 0.5
                        break
                    diff = ter.heightmap[y][x] - lowest_h
                    carry = min(diff * str_val, ter.heightmap[y][x])
                    ter.heightmap[y][x] -= carry
                    sediment += carry
                    x, y = lowest_x, lowest_y
                if 0 <= x < ter.width and 0 <= y < ter.height:
                    ter.heightmap[y][x] += sediment * 0.5
            ter.updated_at = _now()
            self._emit("erosion_applied", terrain_id=terrain_id, iterations=iters)
            return {
                "success": True,
                "terrain_id": terrain_id,
                "iterations": iters,
                "strength": str_val,
            }

    # ------------------------------------------------------------------
    # Heightmap operations
    # ------------------------------------------------------------------

    def generate_heightmap(self, terrain_id: str, width: int, height: int, seed: int = 0) -> List[List[float]]:
        """Generate a procedural heightmap for a terrain."""
        w = max(32, _safe_int(width, 512))
        h = max(32, _safe_int(height, 512))
        s = _safe_int(seed, 0)
        hm: List[List[float]] = []
        for y in range(h):
            row: List[float] = []
            for x in range(w):
                nx = x / w * 4.0
                ny = y / h * 4.0
                val = 0.0
                amp = 1.0
                freq = 1.0
                for _ in range(5):
                    val += _value_noise_2d(nx * freq, ny * freq, s) * amp
                    amp *= 0.5
                    freq *= 2.0
                row.append(val * 100.0)
            hm.append(row)
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is not None:
                ter.heightmap = hm
                ter.width = w
                ter.height = h
                ter.seed = s
                ter.updated_at = _now()
                self._emit("heightmap_generated", terrain_id=terrain_id, width=w, height=h)
        return hm

    def import_heightmap(self, terrain_id: str, data: List[List[float]]) -> bool:
        """Import a heightmap from a 2D list of float values."""
        if not data or not data[0]:
            return False
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return False
            ter.heightmap = [list(row) for row in data]
            ter.height = len(data)
            ter.width = len(data[0]) if data else 0
            ter.updated_at = _now()
            self._emit("heightmap_imported", terrain_id=terrain_id, width=ter.width, height=ter.height)
            return True

    def export_heightmap(self, terrain_id: str) -> List[List[float]]:
        """Export the terrain heightmap as a 2D list of float values."""
        ter = self._terrains.get(terrain_id)
        if ter is None:
            return []
        return [list(row) for row in ter.heightmap]

    def get_height_at(self, terrain_id: str, x: float, y: float) -> float:
        """Sample the terrain height at the given world coordinates."""
        ter = self._terrains.get(terrain_id)
        if ter is None:
            return 0.0
        return self._sample_heightmap(ter, x, y)

    def get_normal_at(self, terrain_id: str, x: float, y: float) -> Tuple[float, float, float]:
        """Compute the surface normal at the given position via finite differences."""
        ter = self._terrains.get(terrain_id)
        if ter is None:
            return (0.0, 0.0, 1.0)
        ix = int(_clamp(x, 0, ter.width - 2))
        iy = int(_clamp(y, 0, ter.height - 2))
        hL = ter.heightmap[iy][max(0, ix - 1)] if ix > 0 else ter.heightmap[iy][ix]
        hR = ter.heightmap[iy][min(ter.width - 1, ix + 1)] if ix < ter.width - 1 else ter.heightmap[iy][ix]
        hD = ter.heightmap[max(0, iy - 1)][ix] if iy > 0 else ter.heightmap[iy][ix]
        hU = ter.heightmap[min(ter.height - 1, iy + 1)][ix] if iy < ter.height - 1 else ter.heightmap[iy][ix]
        nx = (hL - hR)
        ny = (hD - hU)
        nz = 2.0
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-9:
            return (0.0, 0.0, 1.0)
        return (nx / length, ny / length, nz / length)

    # ------------------------------------------------------------------
    # Layer management
    # ------------------------------------------------------------------

    def add_layer(
        self,
        terrain_id: str,
        name: str,
        layer_type: TerrainLayerType = TerrainLayerType.GRASS,
        texture_path: str = "",
        tiling: float = 1.0,
    ) -> Optional[TerrainLayer]:
        """Add a texture layer to a terrain."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return None
            if len(ter.layers) >= _MAX_LAYERS_PER_TERRAIN:
                return None
            ltype = _coerce_enum(TerrainLayerType, layer_type, TerrainLayerType.GRASS)
            layer = TerrainLayer(
                layer_id=_new_id("layer"),
                name=name,
                layer_type=ltype.value,
                texture_path=texture_path,
                tiling=max(0.1, _safe_float(tiling, 1.0)),
            )
            ter.layers.append(layer)
            ter.updated_at = _now()
            self._emit("layer_added", terrain_id=terrain_id, layer_id=layer.layer_id)
            return layer

    def remove_layer(self, terrain_id: str, layer_id: str) -> bool:
        """Remove a texture layer from a terrain."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return False
            original = len(ter.layers)
            ter.layers = [l for l in ter.layers if l.layer_id != layer_id]
            if len(ter.layers) == original:
                return False
            ter.updated_at = _now()
            self._emit("layer_removed", terrain_id=terrain_id, layer_id=layer_id)
            return True

    # ------------------------------------------------------------------
    # Brush settings
    # ------------------------------------------------------------------

    def set_brush(
        self,
        terrain_id: str,
        brush_type: BrushType = BrushType.RAISE,
        size: float = 50.0,
        strength: float = 0.5,
        falloff: float = 0.5,
        target_height: float = 0.0,
    ) -> bool:
        """Set the current brush settings for a terrain."""
        with self._lock:
            ter = self._terrains.get(terrain_id)
            if ter is None:
                return False
            btype = _coerce_enum(BrushType, brush_type, BrushType.RAISE)
            ter.current_brush = TerrainBrush(
                brush_id=ter.current_brush.brush_id or f"brush_{terrain_id}",
                brush_type=btype.value,
                size=max(1.0, _safe_float(size, 50.0)),
                strength=_clamp(_safe_float(strength, 0.5)),
                falloff=_clamp(_safe_float(falloff, 0.5)),
                target_height=_safe_float(target_height, 0.0),
            )
            self._emit("brush_set", terrain_id=terrain_id, brush_type=btype.value)
            return True

    def get_brush_settings(self, terrain_id: str) -> Optional[TerrainBrush]:
        """Return the current brush settings for a terrain."""
        ter = self._terrains.get(terrain_id)
        if ter is None:
            return None
        return ter.current_brush

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_generate_terrain(self, description: str, width: int = 512, height: int = 512) -> TerrainData:
        """Generate a terrain from a natural-language description."""
        if not description or not description.strip():
            raise ValueError("Description must not be empty.")
        desc_lower = description.lower()
        height_scale = 100.0
        seed = random.randint(0, 99999)
        if any(w in desc_lower for w in ("mountain", "alpine", "peak", "hill")):
            height_scale = 250.0
        elif any(w in desc_lower for w in ("desert", "dune", "sand")):
            height_scale = 60.0
        elif any(w in desc_lower for w in ("island", "tropical", "beach")):
            height_scale = 150.0
        elif any(w in desc_lower for w in ("flat", "plains", "field")):
            height_scale = 30.0
        elif any(w in desc_lower for w in ("canyon", "cliff", "gorge")):
            height_scale = 200.0
        ter = self.create_terrain(
            name=description.strip()[:60],
            width=width,
            height=height,
            height_scale=height_scale,
            seed=seed,
            description=description.strip(),
        )
        if any(w in desc_lower for w in ("mountain", "alpine", "peak")):
            ter.heightmap = self._generate_mountain_heightmap(width, height, seed)
        elif any(w in desc_lower for w in ("desert", "dune")):
            ter.heightmap = self._generate_dune_heightmap(width, height, seed)
        elif any(w in desc_lower for w in ("island", "tropical")):
            ter.heightmap = self._generate_island_heightmap(width, height, seed)
        else:
            ter.heightmap = self.generate_heightmap(ter.terrain_id, width, height, seed)
        if any(w in desc_lower for w in ("forest", "tree", "wood")):
            for i in range(30):
                fx = random.uniform(0, width)
                fy = random.uniform(0, height)
                fz = self._sample_heightmap(ter, fx, fy)
                ter.foliage.append(FoliagePatch(patch_id=_new_id("fol"), foliage_type="tree", x=fx, y=fy, z=fz, scale=random.uniform(0.8, 1.4)))
        self._emit("ai_generated_terrain", terrain_id=ter.terrain_id, description=description[:100])
        return ter

    def ai_optimize_terrain(self, terrain_id: str) -> Dict[str, Any]:
        """Analyze and optimize a terrain for performance and visual quality."""
        ter = self._terrains.get(terrain_id)
        if ter is None:
            return {"success": False, "errors": ["Terrain not found."]}
        suggestions: List[str] = []
        foliage_count = len(ter.foliage)
        if foliage_count > 5000:
            suggestions.append("High foliage count. Consider using impostors or reducing density in distant areas.")
        if foliage_count > 1000:
            ter.foliage = ter.foliage[:5000]
            suggestions.append("Capped foliage to 5000 instances for performance.")
        layer_count = len(ter.layers)
        if layer_count > 8:
            suggestions.append("Many texture layers detected. Consider merging similar layers.")
        resolution = ter.width * ter.height
        if resolution > 1024 * 1024:
            suggestions.append("Large heightmap resolution. Consider LOD streaming for distant terrain.")
        min_h = min(min(row) for row in ter.heightmap) if ter.heightmap else 0.0
        max_h = max(max(row) for row in ter.heightmap) if ter.heightmap else 0.0
        self._emit("ai_optimized_terrain", terrain_id=terrain_id, suggestions=suggestions)
        return {
            "success": True,
            "terrain_id": terrain_id,
            "foliage_count": len(ter.foliage),
            "layer_count": layer_count,
            "min_height": min_h,
            "max_height": max_h,
            "suggestions": suggestions,
        }

    def ai_suggest_features(self, description: str) -> List[Dict[str, Any]]:
        """Suggest terrain features based on a description."""
        if not description or not description.strip():
            return []
        desc_lower = description.lower()
        suggestions: List[Dict[str, Any]] = []
        feature_map: List[Tuple[List[str], str, str]] = [
            (["river", "stream", "creek"], "river", "Add a river by carving a descending path through the terrain."),
            (["lake", "pond", "water"], "lake", "Lower a basin area and add a water layer at the desired height."),
            (["cave", "tunnel", "underground"], "cave", "Add an underground cave system with a separate heightmap pass."),
            (["cliff", "drop", "precipice"], "cliff", "Create sharp vertical drops using the flatten brush at different target heights."),
            (["path", "road", "trail"], "road", "Add a road layer and carve a smooth path through the terrain."),
            (["snow", "ice", "frozen"], "snow", "Add a snow layer above a height threshold for mountain peaks."),
            (["volcano", "crater"], "volcano", "Raise a cone shape and carve a crater at the summit."),
            (["forest", "tree", "wood"], "forest", "Scatter tree foliage patches across grassy areas with slope filtering."),
            (["beach", "shore", "coast"], "beach", "Add a sand layer at low heights near the water line."),
            (["plateau", "mesa", "flat top"], "plateau", "Use the flatten brush to create elevated flat areas."),
        ]
        for keywords, feature, reason in feature_map:
            if any(w in desc_lower for w in keywords):
                suggestions.append({"feature": feature, "reason": reason})
        if not suggestions:
            suggestions.append({"feature": "erosion", "reason": "Apply hydraulic erosion to add natural detail to any terrain."})
        self._emit("ai_suggested_features", description=description[:100], count=len(suggestions))
        return suggestions


# ===========================================================================
# 3. Particle Effect Designer
# ===========================================================================

class EmitterShape(Enum):
    """Shapes defining the volume from which particles are emitted."""
    POINT = "point"
    BOX = "box"
    SPHERE = "sphere"
    CONE = "cone"
    MESH = "mesh"
    LINE = "line"


class ParticleModifierType(Enum):
    """Types of modifiers that affect particle behavior over their lifetime."""
    GRAVITY = "gravity"
    DRAG = "drag"
    TURBULENCE = "turbulence"
    VORTEX = "vortex"
    ATTRACTOR = "attractor"
    REPULSOR = "repulsor"
    COLOR_OVER_LIFE = "color_over_life"
    SIZE_OVER_LIFE = "size_over_life"
    VELOCITY_OVER_LIFE = "velocity_over_life"
    COLLISION = "collision"


class ParticleBlendMode(Enum):
    """Blend mode for particle rendering."""
    ADDITIVE = "additive"
    ALPHA = "alpha"
    OPAQUE = "opaque"
    SUBTRACTIVE = "subtractive"


@dataclass
class ParticleKeyframe:
    """A single keyframe in a particle parameter curve."""
    time: float = 0.0
    value: Any = 0.0
    interpolation: str = "linear"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleCurve:
    """A curve of keyframes animating a particle parameter over the particle lifetime."""
    curve_id: str
    name: str = ""
    keyframes: List[ParticleKeyframe] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleEmitter:
    """Configuration for a particle emitter within an effect."""
    emitter_id: str
    name: str = ""
    shape: str = EmitterShape.POINT.value
    rate: float = 10.0
    duration: float = 5.0
    max_particles: int = 1000
    lifetime_min: float = 1.0
    lifetime_max: float = 3.0
    speed_min: float = 1.0
    speed_max: float = 5.0
    size_min: float = 0.1
    size_max: float = 0.5
    start_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    end_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 0.0)
    shape_size: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleModifier:
    """A modifier that alters particle behavior over their lifetime."""
    modifier_id: str
    modifier_type: str = ParticleModifierType.GRAVITY.value
    name: str = ""
    strength: float = 1.0
    direction: Tuple[float, float, float] = (0.0, -1.0, 0.0)
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ParticleEffect:
    """A complete particle effect consisting of emitters, modifiers, and curves."""
    effect_id: str
    name: str = ""
    description: str = ""
    blend_mode: str = ParticleBlendMode.ADDITIVE.value
    emitters: List[ParticleEmitter] = field(default_factory=list)
    modifiers: List[ParticleModifier] = field(default_factory=list)
    curves: List[ParticleCurve] = field(default_factory=list)
    duration: float = 5.0
    looping: bool = True
    is_baked: bool = False
    baked_data: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class ParticleEffectDesigner:
    """Visual particle system editor with emitters, modifiers, and
    curve-based parameter animation.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._effects: Dict[str, ParticleEffect] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"pef_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed(self) -> None:
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_fire()
            self._seed_smoke()
            self._seed_explosion()
            self._seed_magic_sparkles()
            self._seed_rain()
            self._seeded = True

    def _seed_fire(self) -> None:
        eff = ParticleEffect(
            effect_id="pef_fire",
            name="Fire",
            description="A looping fire effect with upward-moving additive particles.",
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            duration=5.0,
            looping=True,
        )
        emitter = ParticleEmitter(
            emitter_id="emit_fire_01",
            name="Flame Emitter",
            shape=EmitterShape.SPHERE.value,
            rate=50.0,
            max_particles=500,
            lifetime_min=0.3,
            lifetime_max=0.8,
            speed_min=2.0,
            speed_max=5.0,
            size_min=0.3,
            size_max=0.8,
            start_color=(1.0, 0.4, 0.0, 1.0),
            end_color=(1.0, 0.0, 0.0, 0.0),
            shape_size=(0.5, 0.5, 0.5),
        )
        gravity = ParticleModifier(
            modifier_id="mod_fire_grav",
            modifier_type=ParticleModifierType.GRAVITY.value,
            name="Upward Draft",
            strength=-3.0,
            direction=(0.0, 1.0, 0.0),
        )
        size_curve = ParticleCurve(
            curve_id="curve_fire_size",
            name="Size Over Life",
            keyframes=[
                ParticleKeyframe(time=0.0, value=0.2, interpolation="linear"),
                ParticleKeyframe(time=0.3, value=0.8, interpolation="linear"),
                ParticleKeyframe(time=1.0, value=0.1, interpolation="linear"),
            ],
        )
        eff.emitters = [emitter]
        eff.modifiers = [gravity]
        eff.curves = [size_curve]
        self._effects[eff.effect_id] = eff

    def _seed_smoke(self) -> None:
        eff = ParticleEffect(
            effect_id="pef_smoke",
            name="Smoke",
            description="Rising smoke with alpha blending and drag.",
            blend_mode=ParticleBlendMode.ALPHA.value,
            duration=8.0,
            looping=True,
        )
        emitter = ParticleEmitter(
            emitter_id="emit_smoke_01",
            name="Smoke Emitter",
            shape=EmitterShape.CONE.value,
            rate=15.0,
            max_particles=300,
            lifetime_min=2.0,
            lifetime_max=5.0,
            speed_min=0.5,
            speed_max=2.0,
            size_min=0.5,
            size_max=2.0,
            start_color=(0.3, 0.3, 0.3, 0.7),
            end_color=(0.5, 0.5, 0.5, 0.0),
            shape_size=(1.0, 1.0, 1.0),
        )
        drag = ParticleModifier(modifier_id="mod_smoke_drag", modifier_type=ParticleModifierType.DRAG.value, name="Air Drag", strength=0.5)
        turb = ParticleModifier(modifier_id="mod_smoke_turb", modifier_type=ParticleModifierType.TURBULENCE.value, name="Turbulence", strength=0.3)
        eff.emitters = [emitter]
        eff.modifiers = [drag, turb]
        self._effects[eff.effect_id] = eff

    def _seed_explosion(self) -> None:
        eff = ParticleEffect(
            effect_id="pef_explosion",
            name="Explosion",
            description="A one-shot explosion with a burst of sparks and debris.",
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            duration=3.0,
            looping=False,
        )
        burst = ParticleEmitter(
            emitter_id="emit_expl_burst",
            name="Fireball Burst",
            shape=EmitterShape.SPHERE.value,
            rate=200.0,
            duration=0.2,
            max_particles=400,
            lifetime_min=0.5,
            lifetime_max=1.5,
            speed_min=5.0,
            speed_max=15.0,
            size_min=0.3,
            size_max=1.0,
            start_color=(1.0, 0.6, 0.0, 1.0),
            end_color=(0.5, 0.1, 0.0, 0.0),
            shape_size=(0.2, 0.2, 0.2),
        )
        sparks = ParticleEmitter(
            emitter_id="emit_expl_sparks",
            name="Sparks",
            shape=EmitterShape.POINT.value,
            rate=100.0,
            duration=0.1,
            max_particles=200,
            lifetime_min=0.3,
            lifetime_max=1.0,
            speed_min=10.0,
            speed_max=25.0,
            size_min=0.05,
            size_max=0.15,
            start_color=(1.0, 1.0, 0.5, 1.0),
            end_color=(1.0, 0.3, 0.0, 0.0),
        )
        gravity = ParticleModifier(modifier_id="mod_expl_grav", modifier_type=ParticleModifierType.GRAVITY.value, name="Gravity", strength=5.0, direction=(0.0, -1.0, 0.0))
        eff.emitters = [burst, sparks]
        eff.modifiers = [gravity]
        self._effects[eff.effect_id] = eff

    def _seed_magic_sparkles(self) -> None:
        eff = ParticleEffect(
            effect_id="pef_magic_sparkles",
            name="Magic Sparkles",
            description="Floating magical sparkles with vortex motion and additive blending.",
            blend_mode=ParticleBlendMode.ADDITIVE.value,
            duration=10.0,
            looping=True,
        )
        emitter = ParticleEmitter(
            emitter_id="emit_spark_01",
            name="Sparkle Emitter",
            shape=EmitterShape.SPHERE.value,
            rate=20.0,
            max_particles=200,
            lifetime_min=1.0,
            lifetime_max=3.0,
            speed_min=0.2,
            speed_max=1.0,
            size_min=0.05,
            size_max=0.2,
            start_color=(0.5, 0.8, 1.0, 1.0),
            end_color=(0.8, 0.5, 1.0, 0.0),
            shape_size=(2.0, 2.0, 2.0),
        )
        vortex = ParticleModifier(modifier_id="mod_spark_vortex", modifier_type=ParticleModifierType.VORTEX.value, name="Swirl", strength=1.0)
        color_curve = ParticleCurve(
            curve_id="curve_spark_color",
            name="Color Over Life",
            keyframes=[
                ParticleKeyframe(time=0.0, value=[0.5, 0.8, 1.0, 1.0]),
                ParticleKeyframe(time=0.5, value=[0.8, 0.5, 1.0, 0.8]),
                ParticleKeyframe(time=1.0, value=[1.0, 0.3, 0.8, 0.0]),
            ],
        )
        eff.emitters = [emitter]
        eff.modifiers = [vortex]
        eff.curves = [color_curve]
        self._effects[eff.effect_id] = eff

    def _seed_rain(self) -> None:
        eff = ParticleEffect(
            effect_id="pef_rain",
            name="Rain",
            description="Falling rain with alpha blending and strong downward gravity.",
            blend_mode=ParticleBlendMode.ALPHA.value,
            duration=10.0,
            looping=True,
        )
        emitter = ParticleEmitter(
            emitter_id="emit_rain_01",
            name="Rain Emitter",
            shape=EmitterShape.BOX.value,
            rate=200.0,
            max_particles=2000,
            lifetime_min=0.5,
            lifetime_max=1.5,
            speed_min=15.0,
            speed_max=25.0,
            size_min=0.02,
            size_max=0.05,
            start_color=(0.7, 0.8, 1.0, 0.6),
            end_color=(0.7, 0.8, 1.0, 0.0),
            shape_size=(10.0, 0.1, 10.0),
        )
        gravity = ParticleModifier(modifier_id="mod_rain_grav", modifier_type=ParticleModifierType.GRAVITY.value, name="Gravity", strength=20.0, direction=(0.0, -1.0, 0.0))
        drag = ParticleModifier(modifier_id="mod_rain_drag", modifier_type=ParticleModifierType.DRAG.value, name="Air Resistance", strength=0.1)
        eff.emitters = [emitter]
        eff.modifiers = [gravity, drag]
        self._effects[eff.effect_id] = eff

    # ------------------------------------------------------------------
    # Effect CRUD
    # ------------------------------------------------------------------

    def create_effect(
        self,
        name: str,
        blend_mode: ParticleBlendMode = ParticleBlendMode.ADDITIVE,
        description: str = "",
        duration: float = 5.0,
        looping: bool = True,
    ) -> ParticleEffect:
        """Create a new empty particle effect."""
        if not name or not name.strip():
            raise ValueError("Effect name must not be empty.")
        with self._lock:
            eff_id = _new_id("pef")
            eff = ParticleEffect(
                effect_id=eff_id,
                name=name.strip(),
                description=description,
                blend_mode=_coerce_enum(ParticleBlendMode, blend_mode, ParticleBlendMode.ADDITIVE).value,
                duration=max(0.1, _safe_float(duration, 5.0)),
                looping=looping,
            )
            self._effects[eff_id] = eff
            _evict_fifo_dict(self._effects, _MAX_EFFECTS)
            self._emit("effect_created", effect_id=eff_id, name=name.strip())
            return eff

    def get_effect(self, effect_id: str) -> Optional[ParticleEffect]:
        """Return the effect with the given ID, or None."""
        return self._effects.get(effect_id)

    def list_effects(self) -> List[ParticleEffect]:
        """Return a list of all particle effects."""
        return list(self._effects.values())

    def update_effect(self, effect_id: str, **kwargs: Any) -> Optional[ParticleEffect]:
        """Update fields on an existing effect by keyword."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return None
            for key, value in kwargs.items():
                if key == "name":
                    eff.name = str(value)
                elif key == "description":
                    eff.description = str(value)
                elif key == "blend_mode":
                    mode = _coerce_enum(ParticleBlendMode, value, None)
                    eff.blend_mode = mode.value if mode else eff.blend_mode
                elif key == "duration":
                    eff.duration = max(0.1, _safe_float(value, eff.duration))
                elif key == "looping":
                    eff.looping = bool(value)
                elif key == "metadata" and isinstance(value, dict):
                    eff.metadata = dict(value)
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("effect_updated", effect_id=effect_id)
            return eff

    def remove_effect(self, effect_id: str) -> bool:
        """Remove an effect by ID."""
        with self._lock:
            removed = self._effects.pop(effect_id, None) is not None
            if removed:
                self._emit("effect_removed", effect_id=effect_id)
            return removed

    # ------------------------------------------------------------------
    # Emitter management
    # ------------------------------------------------------------------

    def add_emitter(
        self,
        effect_id: str,
        name: str = "",
        shape: EmitterShape = EmitterShape.POINT,
        rate: float = 10.0,
        max_particles: int = 1000,
    ) -> Optional[ParticleEmitter]:
        """Add an emitter to a particle effect."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return None
            if len(eff.emitters) >= _MAX_EMITTERS_PER_EFFECT:
                return None
            emitter = ParticleEmitter(
                emitter_id=_new_id("emit"),
                name=name or f"Emitter {len(eff.emitters) + 1}",
                shape=_coerce_enum(EmitterShape, shape, EmitterShape.POINT).value,
                rate=max(0.0, _safe_float(rate, 10.0)),
                max_particles=max(1, _safe_int(max_particles, 1000)),
            )
            eff.emitters.append(emitter)
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("emitter_added", effect_id=effect_id, emitter_id=emitter.emitter_id)
            return emitter

    def remove_emitter(self, effect_id: str, emitter_id: str) -> bool:
        """Remove an emitter from an effect."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return False
            original = len(eff.emitters)
            eff.emitters = [e for e in eff.emitters if e.emitter_id != emitter_id]
            if len(eff.emitters) == original:
                return False
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("emitter_removed", effect_id=effect_id, emitter_id=emitter_id)
            return True

    # ------------------------------------------------------------------
    # Modifier management
    # ------------------------------------------------------------------

    def add_modifier(
        self,
        effect_id: str,
        modifier_type: ParticleModifierType = ParticleModifierType.GRAVITY,
        name: str = "",
        strength: float = 1.0,
    ) -> Optional[ParticleModifier]:
        """Add a modifier to a particle effect."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return None
            if len(eff.modifiers) >= _MAX_MODIFIERS_PER_EFFECT:
                return None
            mtype = _coerce_enum(ParticleModifierType, modifier_type, ParticleModifierType.GRAVITY)
            modifier = ParticleModifier(
                modifier_id=_new_id("mod"),
                modifier_type=mtype.value,
                name=name or mtype.value,
                strength=_safe_float(strength, 1.0),
            )
            eff.modifiers.append(modifier)
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("modifier_added", effect_id=effect_id, modifier_id=modifier.modifier_id)
            return modifier

    def remove_modifier(self, effect_id: str, modifier_id: str) -> bool:
        """Remove a modifier from an effect."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return False
            original = len(eff.modifiers)
            eff.modifiers = [m for m in eff.modifiers if m.modifier_id != modifier_id]
            if len(eff.modifiers) == original:
                return False
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("modifier_removed", effect_id=effect_id, modifier_id=modifier_id)
            return True

    # ------------------------------------------------------------------
    # Curve management
    # ------------------------------------------------------------------

    def set_curve(
        self,
        effect_id: str,
        curve_name: str,
        keyframes: List[Dict[str, Any]],
    ) -> Optional[ParticleCurve]:
        """Set or replace a named curve on an effect."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return None
            if len(eff.curves) >= _MAX_CURVES_PER_EFFECT and not any(c.name == curve_name for c in eff.curves):
                return None
            kfs: List[ParticleKeyframe] = []
            for kf in keyframes:
                kfs.append(ParticleKeyframe(
                    time=_safe_float(kf.get("time", 0.0)),
                    value=kf.get("value", 0.0),
                    interpolation=str(kf.get("interpolation", "linear")),
                ))
            curve = ParticleCurve(curve_id=_new_id("curve"), name=curve_name, keyframes=kfs)
            eff.curves = [c for c in eff.curves if c.name != curve_name]
            eff.curves.append(curve)
            eff.updated_at = _now()
            eff.is_baked = False
            self._emit("curve_set", effect_id=effect_id, curve_name=curve_name)
            return curve

    def get_curve(self, effect_id: str, curve_name: str) -> Optional[ParticleCurve]:
        """Return a named curve from an effect."""
        eff = self._effects.get(effect_id)
        if eff is None:
            return None
        for c in eff.curves:
            if c.name == curve_name:
                return c
        return None

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def simulate_effect(self, effect_id: str, dt: float = 0.016, steps: int = 60) -> Dict[str, Any]:
        """Simulate a particle effect for a number of steps and return summary data."""
        eff = self._effects.get(effect_id)
        if eff is None:
            return {"success": False, "errors": ["Effect not found."]}
        total_particles = 0
        peak_particles = 0
        for step in range(max(1, _safe_int(steps, 60))):
            step_dt = _safe_float(dt, 0.016)
            step_count = 0
            for emitter in eff.emitters:
                if not emitter.enabled:
                    continue
                emitted = int(emitter.rate * step_dt)
                alive = min(emitted, emitter.max_particles)
                step_count += alive
            total_particles += step_count
            if step_count > peak_particles:
                peak_particles = step_count
        self._emit("effect_simulated", effect_id=effect_id, steps=steps, peak=peak_particles)
        return {
            "success": True,
            "effect_id": effect_id,
            "steps": steps,
            "total_particle_frames": total_particles,
            "peak_particles": peak_particles,
            "emitter_count": len(eff.emitters),
            "modifier_count": len(eff.modifiers),
        }

    def get_particle_count(self, effect_id: str) -> int:
        """Return the estimated active particle count for an effect."""
        eff = self._effects.get(effect_id)
        if eff is None:
            return 0
        return sum(e.max_particles for e in eff.emitters if e.enabled)

    def bake_effect(self, effect_id: str) -> Dict[str, Any]:
        """Bake an effect into a static data cache for runtime playback."""
        with self._lock:
            eff = self._effects.get(effect_id)
            if eff is None:
                return {"success": False, "errors": ["Effect not found."]}
            baked: List[Dict[str, Any]] = []
            for emitter in eff.emitters:
                baked.append({
                    "emitter_id": emitter.emitter_id,
                    "name": emitter.name,
                    "shape": emitter.shape,
                    "rate": emitter.rate,
                    "max_particles": emitter.max_particles,
                    "lifetime": [emitter.lifetime_min, emitter.lifetime_max],
                    "speed": [emitter.speed_min, emitter.speed_max],
                    "size": [emitter.size_min, emitter.size_max],
                    "start_color": list(emitter.start_color),
                    "end_color": list(emitter.end_color),
                })
            for modifier in eff.modifiers:
                baked.append({
                    "modifier_id": modifier.modifier_id,
                    "modifier_type": modifier.modifier_type,
                    "strength": modifier.strength,
                    "direction": list(modifier.direction),
                })
            eff.baked_data = baked
            eff.is_baked = True
            self._emit("effect_baked", effect_id=effect_id, data_points=len(baked))
            return {
                "success": True,
                "effect_id": effect_id,
                "data_points": len(baked),
                "is_baked": True,
            }

    def load_effect(self, data: Dict[str, Any]) -> Optional[ParticleEffect]:
        """Load an effect from a serialized dictionary."""
        if not data:
            return None
        with self._lock:
            eff_id = data.get("effect_id", _new_id("pef"))
            eff = ParticleEffect(
                effect_id=eff_id,
                name=data.get("name", "Loaded Effect"),
                description=data.get("description", ""),
                blend_mode=data.get("blend_mode", ParticleBlendMode.ADDITIVE.value),
                duration=_safe_float(data.get("duration", 5.0), 5.0),
                looping=bool(data.get("looping", True)),
            )
            for ed in data.get("emitters", []):
                eff.emitters.append(ParticleEmitter(
                    emitter_id=ed.get("emitter_id", _new_id("emit")),
                    name=ed.get("name", ""),
                    shape=ed.get("shape", EmitterShape.POINT.value),
                    rate=_safe_float(ed.get("rate", 10.0), 10.0),
                    max_particles=_safe_int(ed.get("max_particles", 1000), 1000),
                    lifetime_min=_safe_float(ed.get("lifetime_min", 1.0), 1.0),
                    lifetime_max=_safe_float(ed.get("lifetime_max", 3.0), 3.0),
                    speed_min=_safe_float(ed.get("speed_min", 1.0), 1.0),
                    speed_max=_safe_float(ed.get("speed_max", 5.0), 5.0),
                    start_color=tuple(ed.get("start_color", (1, 1, 1, 1))),
                    end_color=tuple(ed.get("end_color", (1, 1, 1, 0))),
                ))
            for md in data.get("modifiers", []):
                eff.modifiers.append(ParticleModifier(
                    modifier_id=md.get("modifier_id", _new_id("mod")),
                    modifier_type=md.get("modifier_type", ParticleModifierType.GRAVITY.value),
                    name=md.get("name", ""),
                    strength=_safe_float(md.get("strength", 1.0), 1.0),
                    direction=tuple(md.get("direction", (0, -1, 0))),
                ))
            self._effects[eff.effect_id] = eff
            _evict_fifo_dict(self._effects, _MAX_EFFECTS)
            self._emit("effect_loaded", effect_id=eff.effect_id)
            return eff

    def save_effect(self, effect_id: str) -> Dict[str, Any]:
        """Serialize an effect to a dictionary for storage."""
        eff = self._effects.get(effect_id)
        if eff is None:
            return {}
        return eff.to_dict()

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_generate_effect(self, description: str) -> ParticleEffect:
        """Generate a particle effect from a natural-language description."""
        if not description or not description.strip():
            raise ValueError("Description must not be empty.")
        desc_lower = description.lower()
        if any(w in desc_lower for w in ("fire", "flame", "burn")):
            blend = ParticleBlendMode.ADDITIVE
        elif any(w in desc_lower for w in ("smoke", "fog", "mist", "cloud")):
            blend = ParticleBlendMode.ALPHA
        elif any(w in desc_lower for w in ("explosion", "blast", "detonation")):
            blend = ParticleBlendMode.ADDITIVE
        elif any(w in desc_lower for w in ("rain", "snow", "precipitation")):
            blend = ParticleBlendMode.ALPHA
        else:
            blend = ParticleBlendMode.ADDITIVE
        eff = self.create_effect(description.strip()[:60], blend, description.strip())
        if any(w in desc_lower for w in ("fire", "flame")):
            self.add_emitter(eff.effect_id, "Flames", EmitterShape.SPHERE, rate=50, max_particles=500)
            self.add_modifier(eff.effect_id, ParticleModifierType.GRAVITY, "Upward Draft", -3.0)
        elif any(w in desc_lower for w in ("smoke", "fog")):
            self.add_emitter(eff.effect_id, "Smoke", EmitterShape.CONE, rate=15, max_particles=300)
            self.add_modifier(eff.effect_id, ParticleModifierType.DRAG, "Drag", 0.5)
            self.add_modifier(eff.effect_id, ParticleModifierType.TURBULENCE, "Turbulence", 0.3)
        elif any(w in desc_lower for w in ("explosion", "blast")):
            self.add_emitter(eff.effect_id, "Burst", EmitterShape.SPHERE, rate=200, max_particles=400)
            self.add_emitter(eff.effect_id, "Sparks", EmitterShape.POINT, rate=100, max_particles=200)
            self.add_modifier(eff.effect_id, ParticleModifierType.GRAVITY, "Gravity", 5.0)
        elif any(w in desc_lower for w in ("rain", "snow")):
            self.add_emitter(eff.effect_id, "Precipitation", EmitterShape.BOX, rate=200, max_particles=2000)
            self.add_modifier(eff.effect_id, ParticleModifierType.GRAVITY, "Gravity", 20.0 if "rain" in desc_lower else 2.0)
        elif any(w in desc_lower for w in ("sparkle", "magic", "glitter")):
            self.add_emitter(eff.effect_id, "Sparkles", EmitterShape.SPHERE, rate=20, max_particles=200)
            self.add_modifier(eff.effect_id, ParticleModifierType.VORTEX, "Swirl", 1.0)
        else:
            self.add_emitter(eff.effect_id, "Default Emitter", EmitterShape.POINT, rate=10, max_particles=100)
        self._emit("ai_generated_effect", effect_id=eff.effect_id, description=description[:100])
        return eff

    def ai_optimize_particles(self, effect_id: str) -> Dict[str, Any]:
        """Optimize particle effect settings for performance."""
        eff = self._effects.get(effect_id)
        if eff is None:
            return {"success": False, "errors": ["Effect not found."]}
        suggestions: List[str] = []
        total_max = sum(e.max_particles for e in eff.emitters)
        if total_max > 5000:
            suggestions.append("High total particle count. Consider reducing max_particles on emitters.")
            for e in eff.emitters:
                e.max_particles = max(100, int(e.max_particles * 0.5))
            suggestions.append("Halved max_particles on all emitters.")
        emitter_count = len(eff.emitters)
        if emitter_count > 4:
            suggestions.append("Many emitters. Consider merging similar emitters into one.")
        modifier_count = len(eff.modifiers)
        if modifier_count > 6:
            suggestions.append("Many modifiers. Remove or combine modifiers to reduce per-particle cost.")
        if not eff.is_baked:
            self.bake_effect(effect_id)
            suggestions.append("Baked effect data for faster runtime playback.")
        eff.updated_at = _now()
        self._emit("ai_optimized_particles", effect_id=effect_id, suggestions=suggestions)
        return {
            "success": True,
            "effect_id": effect_id,
            "total_max_particles": sum(e.max_particles for e in eff.emitters),
            "suggestions": suggestions,
        }

    def ai_suggest_modifiers(self, description: str) -> List[Dict[str, Any]]:
        """Suggest particle modifiers based on a description."""
        if not description or not description.strip():
            return []
        desc_lower = description.lower()
        suggestions: List[Dict[str, Any]] = []
        modifier_map: List[Tuple[List[str], ParticleModifierType, str]] = [
            (["fall", "drop", "descend", "rain"], ParticleModifierType.GRAVITY, "Add a Gravity modifier to pull particles downward."),
            (["rise", "float", "ascend", "smoke"], ParticleModifierType.GRAVITY, "Add a negative Gravity modifier to push particles upward."),
            (["swirl", "spin", "vortex", "tornado"], ParticleModifierType.VORTEX, "Add a Vortex modifier for rotational motion."),
            (["chaotic", "random", "turbulent"], ParticleModifierType.TURBULENCE, "Add a Turbulence modifier for chaotic movement."),
            (["attract", "pull", "magnet"], ParticleModifierType.ATTRACTOR, "Add an Attractor modifier to pull particles toward a point."),
            (["repel", "push", "explode"], ParticleModifierType.REPULSOR, "Add a Repulsor modifier to push particles outward."),
            (["fade", "disappear", "vanish"], ParticleModifierType.COLOR_OVER_LIFE, "Add a Color Over Life modifier to fade particles out."),
            (["grow", "shrink", "size"], ParticleModifierType.SIZE_OVER_LIFE, "Add a Size Over Life modifier to animate particle scale."),
            (["slow", "drag", "resistance"], ParticleModifierType.DRAG, "Add a Drag modifier to slow particles over time."),
            (["bounce", "collide", "ground"], ParticleModifierType.COLLISION, "Add a Collision modifier for ground bouncing."),
        ]
        for keywords, mtype, reason in modifier_map:
            if any(w in desc_lower for w in keywords):
                suggestions.append({"modifier_type": mtype.value, "reason": reason})
        if not suggestions:
            suggestions.append({"modifier_type": ParticleModifierType.GRAVITY.value, "reason": "A Gravity modifier is a good default for most physical effects."})
        self._emit("ai_suggested_modifiers", description=description[:100], count=len(suggestions))
        return suggestions


# ===========================================================================
# 4. Visual Script Node Graph Editor
# ===========================================================================

class NodeType(Enum):
    """Types of nodes in a visual script graph."""
    EVENT_BEGIN = "event_begin"
    EVENT_TICK = "event_tick"
    EVENT_COLLISION = "event_collision"
    EVENT_TRIGGER = "event_trigger"
    EVENT_INPUT = "event_input"
    ACTION_PRINT = "action_print"
    ACTION_SPAWN = "action_spawn"
    ACTION_DESTROY = "action_destroy"
    ACTION_MOVE = "action_move"
    ACTION_ROTATE = "action_rotate"
    ACTION_SCALE = "action_scale"
    ACTION_SET_PROPERTY = "action_set_property"
    ACTION_GET_PROPERTY = "action_get_property"
    ACTION_CALL_FUNCTION = "action_call_function"
    ACTION_DELAY = "action_delay"
    BRANCH_BRANCH = "branch_branch"
    BRANCH_SEQUENCE = "branch_sequence"
    BRANCH_WHILE = "branch_while"
    BRANCH_FOR = "branch_for"
    FLOW_GATE = "flow_gate"
    FLOW_DELAY = "flow_delay"
    VARIABLE_GET = "variable_get"
    VARIABLE_SET = "variable_set"
    VARIABLE_MAKE = "variable_make"
    COMMENT = "comment"


class PinType(Enum):
    """Types of pins on a script node."""
    INPUT = "input"
    OUTPUT = "output"
    EXECUTION = "execution"
    DATA = "data"


@dataclass
class ScriptPin:
    """A pin on a script node that can be connected to other pins."""
    pin_id: str
    pin_type: str = PinType.DATA.value
    name: str = ""
    data_type: str = "any"
    direction: str = PinType.INPUT.value
    connected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScriptConnection:
    """A directed connection between two script pins."""
    connection_id: str
    from_node: str = ""
    from_pin: str = ""
    to_node: str = ""
    to_pin: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScriptNode:
    """A single node in a visual script graph."""
    node_id: str
    node_type: str = NodeType.ACTION_PRINT.value
    label: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    pins: List[ScriptPin] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScriptVariable:
    """A variable defined in a script graph."""
    variable_id: str
    name: str = ""
    data_type: str = "float"
    default_value: Any = 0.0
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScriptFunction:
    """A user-defined function in a script graph."""
    function_id: str
    name: str = ""
    return_type: str = "void"
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScriptGraph:
    """A complete visual script graph with nodes, connections, variables, and functions."""
    graph_id: str
    name: str = ""
    description: str = ""
    nodes: List[ScriptNode] = field(default_factory=list)
    connections: List[ScriptConnection] = field(default_factory=list)
    variables: List[ScriptVariable] = field(default_factory=list)
    functions: List[ScriptFunction] = field(default_factory=list)
    target_entity: str = ""
    is_compiled: bool = False
    compiled_code: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class VisualScriptNodeGraphEditor:
    """Node-based visual scripting editor for game logic without code.

    Manages event nodes, action nodes, flow control, variables, and
    function calls. Provides AI-assisted logic generation, graph
    optimization, and node suggestions.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._graphs: Dict[str, ScriptGraph] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"vsg_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _make_default_pins(self, node_type: str) -> List[ScriptPin]:
        """Create default input/output pins based on the node type."""
        pins: List[ScriptPin] = []
        if node_type.startswith("event_"):
            pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="out", direction=PinType.OUTPUT.value))
            if node_type == NodeType.EVENT_COLLISION.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="other", data_type="entity", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.EVENT_TRIGGER.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="activator", data_type="entity", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.EVENT_INPUT.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="action", data_type="string", direction=PinType.OUTPUT.value))
        elif node_type.startswith("action_"):
            pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="in", direction=PinType.INPUT.value))
            pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="out", direction=PinType.OUTPUT.value))
            if node_type == NodeType.ACTION_SPAWN.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="prefab", data_type="string", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="position", data_type="vector3", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="spawned", data_type="entity", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.ACTION_SET_PROPERTY.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="target", data_type="entity", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="property", data_type="string", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="value", data_type="any", direction=PinType.INPUT.value))
            elif node_type == NodeType.ACTION_CALL_FUNCTION.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="target", data_type="entity", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="function", data_type="string", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="result", data_type="any", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.ACTION_PRINT.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="message", data_type="string", direction=PinType.INPUT.value))
            elif node_type == NodeType.ACTION_MOVE.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="target", data_type="entity", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="direction", data_type="vector3", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="speed", data_type="float", direction=PinType.INPUT.value))
            elif node_type == NodeType.ACTION_DELAY.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="duration", data_type="float", direction=PinType.INPUT.value))
        elif node_type.startswith("branch_"):
            pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="in", direction=PinType.INPUT.value))
            if node_type == NodeType.BRANCH_BRANCH.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="condition", data_type="bool", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="true", direction=PinType.OUTPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="false", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.BRANCH_SEQUENCE.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="out_0", direction=PinType.OUTPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="out_1", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.BRANCH_WHILE.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="condition", data_type="bool", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="loop", direction=PinType.OUTPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="done", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.BRANCH_FOR.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="count", data_type="int", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="loop", direction=PinType.OUTPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="done", direction=PinType.OUTPUT.value))
        elif node_type.startswith("variable_"):
            if node_type == NodeType.VARIABLE_GET.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="value", data_type="any", direction=PinType.OUTPUT.value))
            elif node_type == NodeType.VARIABLE_SET.value:
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.DATA.value, name="value", data_type="any", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="in", direction=PinType.INPUT.value))
                pins.append(ScriptPin(pin_id=_new_id("pin"), pin_type=PinType.EXECUTION.value, name="out", direction=PinType.OUTPUT.value))
        return pins

    def _seed(self) -> None:
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_player_spawn()
            self._seed_door_trigger()
            self._seed_pickup_system()
            self._seed_enemy_patrol()
            self._seeded = True

    def _seed_player_spawn(self) -> None:
        g = ScriptGraph(graph_id="vsg_player_spawn", name="Player Spawn Logic", description="Spawns the player entity at game start and sets initial health.")
        begin = ScriptNode(node_id="node_ps_begin", node_type=NodeType.EVENT_BEGIN.value, label="On Game Begin", position_x=-400, position_y=0)
        spawn = ScriptNode(node_id="node_ps_spawn", node_type=NodeType.ACTION_SPAWN.value, label="Spawn Player", position_x=0, position_y=0, properties={"prefab": "player", "position": [0, 10, 0]})
        set_hp = ScriptNode(node_id="node_ps_set_hp", node_type=NodeType.ACTION_SET_PROPERTY.value, label="Set Health", position_x=300, position_y=0, properties={"property": "health", "value": 100})
        begin.pins = self._make_default_nodes_for(begin)
        spawn.pins = self._make_default_nodes_for(spawn)
        set_hp.pins = self._make_default_nodes_for(set_hp)
        g.nodes = [begin, spawn, set_hp]
        g.connections = [
            ScriptConnection(connection_id="conn_ps_1", from_node="node_ps_begin", from_pin="out", to_node="node_ps_spawn", to_pin="in"),
            ScriptConnection(connection_id="conn_ps_2", from_node="node_ps_spawn", from_pin="out", to_node="node_ps_set_hp", to_pin="in"),
        ]
        g.variables = [ScriptVariable(variable_id="var_ps_hp", name="PlayerHealth", data_type="float", default_value=100.0)]
        self._graphs[g.graph_id] = g

    def _seed_door_trigger(self) -> None:
        g = ScriptGraph(graph_id="vsg_door_trigger", name="Door Trigger", description="Opens or closes a door when a trigger volume is activated.")
        trigger = ScriptNode(node_id="node_dt_trig", node_type=NodeType.EVENT_TRIGGER.value, label="On Trigger", position_x=-400, position_y=0)
        branch = ScriptNode(node_id="node_dt_branch", node_type=NodeType.BRANCH_BRANCH.value, label="Is Open?", position_x=0, position_y=0)
        close = ScriptNode(node_id="node_dt_close", node_type=NodeType.ACTION_CALL_FUNCTION.value, label="Close Door", position_x=300, position_y=-100, properties={"function": "close"})
        open_n = ScriptNode(node_id="node_dt_open", node_type=NodeType.ACTION_CALL_FUNCTION.value, label="Open Door", position_x=300, position_y=100, properties={"function": "open"})
        trigger.pins = self._make_default_nodes_for(trigger)
        branch.pins = self._make_default_nodes_for(branch)
        close.pins = self._make_default_nodes_for(close)
        open_n.pins = self._make_default_nodes_for(open_n)
        g.nodes = [trigger, branch, close, open_n]
        g.connections = [
            ScriptConnection(connection_id="conn_dt_1", from_node="node_dt_trig", from_pin="out", to_node="node_dt_branch", to_pin="in"),
            ScriptConnection(connection_id="conn_dt_2", from_node="node_dt_branch", from_pin="true", to_node="node_dt_close", to_pin="in"),
            ScriptConnection(connection_id="conn_dt_3", from_node="node_dt_branch", from_pin="false", to_node="node_dt_open", to_pin="in"),
        ]
        g.variables = [ScriptVariable(variable_id="var_dt_open", name="IsOpen", data_type="bool", default_value=False)]
        self._graphs[g.graph_id] = g

    def _seed_pickup_system(self) -> None:
        g = ScriptGraph(graph_id="vsg_pickup_system", name="Pickup System", description="Handles item pickup on collision and adds to inventory.")
        collision = ScriptNode(node_id="node_pk_col", node_type=NodeType.EVENT_COLLISION.value, label="On Collision", position_x=-400, position_y=0)
        call = ScriptNode(node_id="node_pk_call", node_type=NodeType.ACTION_CALL_FUNCTION.value, label="Add to Inventory", position_x=0, position_y=0, properties={"function": "add_to_inventory"})
        destroy = ScriptNode(node_id="node_pk_dest", node_type=NodeType.ACTION_DESTROY.value, label="Destroy Pickup", position_x=300, position_y=0)
        collision.pins = self._make_default_nodes_for(collision)
        call.pins = self._make_default_nodes_for(call)
        destroy.pins = self._make_default_nodes_for(destroy)
        g.nodes = [collision, call, destroy]
        g.connections = [
            ScriptConnection(connection_id="conn_pk_1", from_node="node_pk_col", from_pin="out", to_node="node_pk_call", to_pin="in"),
            ScriptConnection(connection_id="conn_pk_2", from_node="node_pk_call", from_pin="out", to_node="node_pk_dest", to_pin="in"),
        ]
        self._graphs[g.graph_id] = g

    def _seed_enemy_patrol(self) -> None:
        g = ScriptGraph(graph_id="vsg_enemy_patrol", name="Enemy Patrol", description="Moves an enemy between patrol points on each tick.")
        tick = ScriptNode(node_id="node_ep_tick", node_type=NodeType.EVENT_TICK.value, label="On Tick", position_x=-400, position_y=0)
        move = ScriptNode(node_id="node_ep_move", node_type=NodeType.ACTION_MOVE.value, label="Move to Point", position_x=0, position_y=0, properties={"speed": 3.0})
        delay = ScriptNode(node_id="node_ep_delay", node_type=NodeType.ACTION_DELAY.value, label="Wait", position_x=300, position_y=0, properties={"duration": 1.0})
        tick.pins = self._make_default_nodes_for(tick)
        move.pins = self._make_default_nodes_for(move)
        delay.pins = self._make_default_nodes_for(delay)
        g.nodes = [tick, move, delay]
        g.connections = [
            ScriptConnection(connection_id="conn_ep_1", from_node="node_ep_tick", from_pin="out", to_node="node_ep_move", to_pin="in"),
            ScriptConnection(connection_id="conn_ep_2", from_node="node_ep_move", from_pin="out", to_node="node_ep_delay", to_pin="in"),
        ]
        g.variables = [
            ScriptVariable(variable_id="var_ep_idx", name="PatrolIndex", data_type="int", default_value=0),
            ScriptVariable(variable_id="var_ep_speed", name="PatrolSpeed", data_type="float", default_value=3.0),
        ]
        self._graphs[g.graph_id] = g

    def _make_default_nodes_for(self, node: ScriptNode) -> List[ScriptPin]:
        """Helper used during seeding to populate pins on a node."""
        return self._make_default_pins(node.node_type)

    # ------------------------------------------------------------------
    # Graph CRUD
    # ------------------------------------------------------------------

    def create_graph(self, name: str, description: str = "", target_entity: str = "") -> ScriptGraph:
        """Create a new empty visual script graph."""
        if not name or not name.strip():
            raise ValueError("Graph name must not be empty.")
        with self._lock:
            gid = _new_id("vsg")
            g = ScriptGraph(graph_id=gid, name=name.strip(), description=description, target_entity=target_entity)
            self._graphs[gid] = g
            _evict_fifo_dict(self._graphs, _MAX_GRAPHS)
            self._emit("graph_created", graph_id=gid, name=name.strip())
            return g

    def get_graph(self, graph_id: str) -> Optional[ScriptGraph]:
        """Return the graph with the given ID, or None."""
        return self._graphs.get(graph_id)

    def list_graphs(self) -> List[ScriptGraph]:
        """Return a list of all script graphs."""
        return list(self._graphs.values())

    def update_graph(self, graph_id: str, **kwargs: Any) -> Optional[ScriptGraph]:
        """Update fields on an existing graph by keyword."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return None
            for key, value in kwargs.items():
                if key == "name":
                    g.name = str(value)
                elif key == "description":
                    g.description = str(value)
                elif key == "target_entity":
                    g.target_entity = str(value)
                elif key == "metadata" and isinstance(value, dict):
                    g.metadata = dict(value)
            g.updated_at = _now()
            g.is_compiled = False
            self._emit("graph_updated", graph_id=graph_id)
            return g

    def remove_graph(self, graph_id: str) -> bool:
        """Remove a graph by ID."""
        with self._lock:
            removed = self._graphs.pop(graph_id, None) is not None
            if removed:
                self._emit("graph_removed", graph_id=graph_id)
            return removed

    # ------------------------------------------------------------------
    # Node management
    # ------------------------------------------------------------------

    def add_node(self, graph_id: str, node_type: NodeType, label: str = "", position_x: float = 0.0, position_y: float = 0.0, properties: Optional[Dict[str, Any]] = None) -> Optional[ScriptNode]:
        """Add a new node to a script graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return None
            if len(g.nodes) >= _MAX_NODES_PER_SCRIPT:
                return None
            ntype = _coerce_enum(NodeType, node_type, NodeType.ACTION_PRINT)
            node = ScriptNode(node_id=_new_id("node"), node_type=ntype.value, label=label or ntype.value.replace("_", " ").title(), position_x=position_x, position_y=position_y, properties=dict(properties) if properties else {})
            node.pins = self._make_default_pins(ntype.value)
            g.nodes.append(node)
            g.updated_at = _now()
            g.is_compiled = False
            self._emit("node_added", graph_id=graph_id, node_id=node.node_id, node_type=ntype.value)
            return node

    def remove_node(self, graph_id: str, node_id: str) -> bool:
        """Remove a node and any connections touching it."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return False
            original = len(g.nodes)
            g.nodes = [n for n in g.nodes if n.node_id != node_id]
            if len(g.nodes) == original:
                return False
            g.connections = [c for c in g.connections if c.from_node != node_id and c.to_node != node_id]
            g.updated_at = _now()
            g.is_compiled = False
            self._emit("node_removed", graph_id=graph_id, node_id=node_id)
            return True

    def connect_pins(self, graph_id: str, from_node: str, from_pin: str, to_node: str, to_pin: str) -> Optional[ScriptConnection]:
        """Create a directed connection between two pins."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return None
            if from_node == to_node:
                return None
            if len(g.connections) >= _MAX_CONNECTIONS_PER_SCRIPT:
                return None
            node_ids = {n.node_id for n in g.nodes}
            if from_node not in node_ids or to_node not in node_ids:
                return None
            conn = ScriptConnection(connection_id=_new_id("conn"), from_node=from_node, from_pin=from_pin, to_node=to_node, to_pin=to_pin)
            g.connections.append(conn)
            g.updated_at = _now()
            g.is_compiled = False
            self._emit("pins_connected", graph_id=graph_id, connection_id=conn.connection_id)
            return conn

    def disconnect_pins(self, graph_id: str, connection_id: str) -> bool:
        """Remove a connection by ID."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return False
            original = len(g.connections)
            g.connections = [c for c in g.connections if c.connection_id != connection_id]
            if len(g.connections) == original:
                return False
            g.updated_at = _now()
            g.is_compiled = False
            self._emit("pins_disconnected", graph_id=graph_id, connection_id=connection_id)
            return True

    # ------------------------------------------------------------------
    # Variable and function management
    # ------------------------------------------------------------------

    def add_variable(self, graph_id: str, name: str, data_type: str = "float", default_value: Any = 0.0) -> Optional[ScriptVariable]:
        """Add a variable to a script graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return None
            if len(g.variables) >= _MAX_VARIABLES_PER_GRAPH:
                return None
            var = ScriptVariable(variable_id=_new_id("var"), name=name, data_type=data_type, default_value=default_value)
            g.variables.append(var)
            g.updated_at = _now()
            self._emit("variable_added", graph_id=graph_id, variable_id=var.variable_id)
            return var

    def remove_variable(self, graph_id: str, variable_id: str) -> bool:
        """Remove a variable from a graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return False
            original = len(g.variables)
            g.variables = [v for v in g.variables if v.variable_id != variable_id]
            if len(g.variables) == original:
                return False
            g.updated_at = _now()
            self._emit("variable_removed", graph_id=graph_id, variable_id=variable_id)
            return True

    def add_function(self, graph_id: str, name: str, return_type: str = "void", parameters: Optional[List[Dict[str, Any]]] = None) -> Optional[ScriptFunction]:
        """Add a function definition to a script graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return None
            if len(g.functions) >= _MAX_FUNCTIONS_PER_GRAPH:
                return None
            func = ScriptFunction(function_id=_new_id("func"), name=name, return_type=return_type, parameters=list(parameters) if parameters else [])
            g.functions.append(func)
            g.updated_at = _now()
            self._emit("function_added", graph_id=graph_id, function_id=func.function_id)
            return func

    def remove_function(self, graph_id: str, function_id: str) -> bool:
        """Remove a function from a graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return False
            original = len(g.functions)
            g.functions = [f for f in g.functions if f.function_id != function_id]
            if len(g.functions) == original:
                return False
            g.updated_at = _now()
            self._emit("function_removed", graph_id=graph_id, function_id=function_id)
            return True

    # ------------------------------------------------------------------
    # Validation and compilation
    # ------------------------------------------------------------------

    def validate_graph(self, graph_id: str) -> Dict[str, Any]:
        """Validate a script graph for correctness."""
        g = self._graphs.get(graph_id)
        if g is None:
            return {"valid": False, "errors": ["Graph not found."], "warnings": []}
        errors: List[str] = []
        warnings: List[str] = []
        has_event = any(n.node_type.startswith("event_") for n in g.nodes)
        if not has_event:
            errors.append("Graph has no event entry point.")
        node_ids = {n.node_id for n in g.nodes}
        for conn in g.connections:
            if conn.from_node not in node_ids:
                errors.append(f"Connection {conn.connection_id} references missing from_node.")
            if conn.to_node not in node_ids:
                errors.append(f"Connection {conn.connection_id} references missing to_node.")
        if self._has_cycles(g):
            errors.append("Graph contains an execution cycle.")
        disconnected = [n for n in g.nodes if n.node_type != NodeType.COMMENT.value and not any(c.from_node == n.node_id or c.to_node == n.node_id for c in g.connections)]
        if disconnected:
            warnings.append(f"{len(disconnected)} node(s) are not connected.")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}

    def _has_cycles(self, graph: ScriptGraph) -> bool:
        """Detect cycles in the script graph using DFS."""
        adj: Dict[str, List[str]] = {}
        for conn in graph.connections:
            adj.setdefault(conn.from_node, []).append(conn.to_node)
        WHITE, GRAY, BLACK = 0, 1, 2
        color: Dict[str, int] = {n.node_id: WHITE for n in graph.nodes}

        def dfs(node: str) -> bool:
            color[node] = GRAY
            for neighbor in adj.get(node, []):
                if color.get(neighbor, WHITE) == GRAY:
                    return True
                if color.get(neighbor, WHITE) == WHITE and dfs(neighbor):
                    return True
            color[node] = BLACK
            return False

        for node_id in list(color.keys()):
            if color[node_id] == WHITE and dfs(node_id):
                return True
        return False

    def compile_to_code(self, graph_id: str) -> Dict[str, Any]:
        """Compile a visual script graph into pseudo-code."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return {"success": False, "errors": ["Graph not found."]}
            validation = self.validate_graph(graph_id)
            if not validation["valid"]:
                return {"success": False, "errors": validation["errors"], "warnings": validation["warnings"]}
            lines: List[str] = [f"# Compiled from graph: {g.name}", f"# Target entity: {g.target_entity or 'self'}", ""]
            for var in g.variables:
                lines.append(f"{var.data_type} {var.name} = {_to_jsonable(var.default_value)}")
            lines.append("")
            event_nodes = [n for n in g.nodes if n.node_type.startswith("event_")]
            for event in event_nodes:
                event_name = event.node_type.replace("event_", "on_")
                lines.append(f"def {event_name}():")
                current = event
                visited: Set[str] = set()
                while current and current.node_id not in visited:
                    visited.add(current.node_id)
                    lines.append(f"    # {current.label} ({current.node_type})")
                    if current.node_type == NodeType.ACTION_PRINT.value:
                        msg = current.properties.get("message", "Hello")
                        lines.append(f'    print("{msg}")')
                    elif current.node_type == NodeType.ACTION_SPAWN.value:
                        prefab = current.properties.get("prefab", "entity")
                        lines.append(f"    spawn('{prefab}')")
                    elif current.node_type == NodeType.ACTION_DESTROY.value:
                        lines.append("    destroy_self()")
                    elif current.node_type == NodeType.ACTION_MOVE.value:
                        lines.append("    move_forward()")
                    elif current.node_type == NodeType.ACTION_SET_PROPERTY.value:
                        prop = current.properties.get("property", "value")
                        val = current.properties.get("value", 0)
                        lines.append(f"    set_property('{prop}', {val})")
                    elif current.node_type == NodeType.ACTION_CALL_FUNCTION.value:
                        func = current.properties.get("function", "call")
                        lines.append(f"    {func}()")
                    elif current.node_type == NodeType.ACTION_DELAY.value:
                        dur = current.properties.get("duration", 1.0)
                        lines.append(f"    delay({dur})")
                    next_conn = next((c for c in g.connections if c.from_node == current.node_id and c.from_pin in ("out", "true", "loop")), None)
                    current = next((n for n in g.nodes if n.node_id == next_conn.to_node), None) if next_conn else None
                lines.append("")
            code = "\n".join(lines)
            g.compiled_code = code
            g.is_compiled = True
            self._emit("graph_compiled", graph_id=graph_id, code_length=len(code))
            return {"success": True, "graph_id": graph_id, "code": code, "warnings": validation["warnings"]}

    def get_graph_data(self, graph_id: str) -> Dict[str, Any]:
        """Return the full serialized data for a graph."""
        g = self._graphs.get(graph_id)
        if g is None:
            return {}
        return g.to_dict()

    def set_node_property(self, graph_id: str, node_id: str, property_name: str, value: Any) -> bool:
        """Set a property on a specific node in a graph."""
        with self._lock:
            g = self._graphs.get(graph_id)
            if g is None:
                return False
            for node in g.nodes:
                if node.node_id == node_id:
                    node.properties[property_name] = value
                    g.updated_at = _now()
                    g.is_compiled = False
                    self._emit("node_property_set", graph_id=graph_id, node_id=node_id, property=property_name)
                    return True
            return False

    # ------------------------------------------------------------------
    # AI Methods
    # ------------------------------------------------------------------

    def ai_generate_logic(self, description: str) -> ScriptGraph:
        """Generate a visual script graph from a natural-language description."""
        if not description or not description.strip():
            raise ValueError("Description must not be empty.")
        desc_lower = description.lower()
        g = self.create_graph(description.strip()[:60], description.strip())
        begin = self.add_node(g.graph_id, NodeType.EVENT_BEGIN, "On Begin", -400, 0)
        if any(w in desc_lower for w in ("spawn", "create", "instantiate")):
            self.add_node(g.graph_id, NodeType.ACTION_SPAWN, "Spawn Entity", 0, 0, properties={"prefab": "entity"})
        if any(w in desc_lower for w in ("move", "walk", "patrol", "travel")):
            self.add_node(g.graph_id, NodeType.ACTION_MOVE, "Move", 200, 0, properties={"speed": 3.0})
        if any(w in desc_lower for w in ("destroy", "remove", "delete", "despawn")):
            self.add_node(g.graph_id, NodeType.ACTION_DESTROY, "Destroy", 400, 0)
        if any(w in desc_lower for w in ("print", "log", "debug", "message")):
            self.add_node(g.graph_id, NodeType.ACTION_PRINT, "Print Message", -100, 100, properties={"message": "Hello World"})
        if any(w in desc_lower for w in ("delay", "wait", "pause")):
            self.add_node(g.graph_id, NodeType.ACTION_DELAY, "Wait", 200, 100, properties={"duration": 1.0})
        if any(w in desc_lower for w in ("if", "branch", "condition", "check")):
            self.add_node(g.graph_id, NodeType.BRANCH_BRANCH, "Branch", 100, 0)
        if any(w in desc_lower for w in ("health", "score", "count")):
            var_name = "Health" if "health" in desc_lower else "Score" if "score" in desc_lower else "Count"
            self.add_variable(g.graph_id, var_name, "float", 100.0 if var_name == "Health" else 0.0)
        nodes = g.nodes
        for i in range(len(nodes) - 1):
            from_n = nodes[i]
            to_n = nodes[i + 1]
            from_pin = "out" if from_n.node_type.startswith("event_") or from_n.node_type.startswith("action_") else "true"
            self.connect_pins(g.graph_id, from_n.node_id, from_pin, to_n.node_id, "in")
        self._emit("ai_generated_logic", graph_id=g.graph_id, description=description[:100])
        return g

    def ai_optimize_graph(self, graph_id: str) -> Dict[str, Any]:
        """Optimize a visual script graph for clarity and performance."""
        g = self._graphs.get(graph_id)
        if g is None:
            return {"success": False, "errors": ["Graph not found."]}
        suggestions: List[str] = []
        node_count = len(g.nodes)
        if node_count > 50:
            suggestions.append("Large node count. Consider splitting into sub-graphs.")
        disconnected = [n for n in g.nodes if n.node_type != NodeType.COMMENT.value and not any(c.from_node == n.node_id or c.to_node == n.node_id for c in g.connections)]
        if disconnected:
            for n in disconnected:
                self.remove_node(graph_id, n.node_id)
            suggestions.append(f"Removed {len(disconnected)} disconnected nodes.")
        if not g.is_compiled:
            self.compile_to_code(graph_id)
            suggestions.append("Compiled graph to code.")
        self._emit("ai_optimized_graph", graph_id=graph_id, suggestions=suggestions)
        return {"success": True, "graph_id": graph_id, "node_count": len(g.nodes), "suggestions": suggestions}

    def ai_suggest_nodes(self, description: str) -> List[Dict[str, Any]]:
        """Suggest script node types based on a description."""
        if not description or not description.strip():
            return []
        desc_lower = description.lower()
        suggestions: List[Dict[str, Any]] = []
        node_map: List[Tuple[List[str], NodeType, str]] = [
            (["start", "begin", "init", "spawn"], NodeType.EVENT_BEGIN, "Add a Begin event as the entry point."),
            (["tick", "update", "frame", "loop"], NodeType.EVENT_TICK, "Add a Tick event for per-frame logic."),
            (["collide", "hit", "touch"], NodeType.EVENT_COLLISION, "Add a Collision event for contact responses."),
            (["trigger", "enter", "zone", "area"], NodeType.EVENT_TRIGGER, "Add a Trigger event for zone activation."),
            (["input", "key", "button", "press"], NodeType.EVENT_INPUT, "Add an Input event for player controls."),
            (["spawn", "create", "instantiate"], NodeType.ACTION_SPAWN, "Add a Spawn action to create entities."),
            (["destroy", "remove", "delete"], NodeType.ACTION_DESTROY, "Add a Destroy action to remove entities."),
            (["move", "walk", "run"], NodeType.ACTION_MOVE, "Add a Move action for movement."),
            (["rotate", "turn", "spin"], NodeType.ACTION_ROTATE, "Add a Rotate action for rotation."),
            (["if", "branch", "condition"], NodeType.BRANCH_BRANCH, "Add a Branch node for conditional logic."),
            (["sequence", "series", "order"], NodeType.BRANCH_SEQUENCE, "Add a Sequence node for ordered execution."),
            (["while", "repeat", "loop"], NodeType.BRANCH_WHILE, "Add a While loop for conditional repetition."),
            (["for", "iterate", "count"], NodeType.BRANCH_FOR, "Add a For loop for counted iteration."),
            (["delay", "wait", "pause"], NodeType.ACTION_DELAY, "Add a Delay node for timed pauses."),
            (["print", "log", "debug"], NodeType.ACTION_PRINT, "Add a Print action for debugging."),
            (["set", "assign", "change"], NodeType.ACTION_SET_PROPERTY, "Add a Set Property action to modify values."),
            (["call", "invoke", "execute"], NodeType.ACTION_CALL_FUNCTION, "Add a Call Function action to run a named function."),
        ]
        for keywords, ntype, reason in node_map:
            if any(w in desc_lower for w in keywords):
                suggestions.append({"node_type": ntype.value, "label": ntype.value.replace("_", " ").title(), "reason": reason})
        if not suggestions:
            suggestions.append({"node_type": NodeType.EVENT_BEGIN.value, "label": "Begin Event", "reason": "Every graph needs an entry point."})
        self._emit("ai_suggested_nodes", description=description[:100], count=len(suggestions))
        return suggestions


# ===========================================================================
# 5. Audio Mixer Editor
# ===========================================================================

class AudioEffectType(Enum):
    """Types of audio effects that can be inserted into a bus chain."""
    REVERB = "reverb"
    DELAY = "delay"
    EQ_LOW = "eq_low"
    EQ_MID = "eq_mid"
    EQ_HIGH = "eq_high"
    COMPRESSOR = "compressor"
    LIMITER = "limiter"
    DISTORTION = "distortion"
    CHORUS = "chorus"
    FLANGER = "flanger"
    PITCH_SHIFT = "pitch_shift"
    TIME_STRETCH = "time_stretch"


class AudioBusType(Enum):
    """Logical grouping of an audio bus within the mix hierarchy."""
    MASTER = "master"
    MUSIC = "music"
    SFX = "sfx"
    DIALOGUE = "dialogue"
    AMBIENT = "ambient"
    UI = "ui"


@dataclass
class AudioEffect:
    """A single DSP effect placed in a bus effect chain."""
    effect_id: str
    effect_type: str = AudioEffectType.REVERB.value
    enabled: bool = True
    order: int = 0
    parameters: Dict[str, Any] = field(default_factory=dict)
    mix: float = 1.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioChannel:
    """A single audio channel routed through a bus."""
    channel_id: str
    name: str
    bus_id: str
    volume: float = 1.0
    pitch: float = 1.0
    pan: float = 0.0
    muted: bool = False
    soloed: bool = False
    looping: bool = False
    source_cue_id: str = ""
    playing: bool = False
    position: float = 0.0
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioBus:
    """A grouping of audio channels sharing a volume and effect chain."""
    bus_id: str
    name: str
    bus_type: str = AudioBusType.SFX.value
    parent_bus_id: str = ""
    volume: float = 1.0
    muted: bool = False
    soloed: bool = False
    effects: List[AudioEffect] = field(default_factory=list)
    channels: List[AudioChannel] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SoundCue:
    """A reusable audio asset definition with playback settings."""
    cue_id: str
    name: str
    source_path: str = ""
    duration: float = 0.0
    volume: float = 1.0
    pitch: float = 1.0
    pan: float = 0.0
    loop: bool = False
    streaming: bool = False
    spatialized: bool = False
    attenuation_radius: float = 1000.0
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AudioMixPreset:
    """A snapshot of bus volumes and effect states for recall."""
    preset_id: str
    name: str
    description: str = ""
    bus_volumes: Dict[str, float] = field(default_factory=dict)
    bus_mutes: Dict[str, bool] = field(default_factory=dict)
    effect_states: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class AudioMixerEditor:
    """Audio bus, channel, and cue mixing editor.

    Manages a hierarchical bus routing system (master, music, sfx,
    dialogue, ambient, ui), per-bus effect chains, sound cues, mix
    presets, and live level monitoring. Provides AI-assisted mix
    generation, level optimization, and effect suggestions.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._buses: Dict[str, AudioBus] = {}
        self._cues: Dict[str, SoundCue] = {}
        self._presets: Dict[str, AudioMixPreset] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"aud_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed(self) -> None:
        """Populate the mixer with a canonical bus hierarchy and cues."""
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_master_bus()
            self._seed_music_bus()
            self._seed_sfx_bus()
            self._seed_dialogue_bus()
            self._seed_ambient_bus()
            self._seed_ui_bus()
            self._seed_sound_cues()
            self._seeded = True

    def _seed_master_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_master",
            name="Master",
            bus_type=AudioBusType.MASTER.value,
            volume=1.0,
        )
        limiter = AudioEffect(
            effect_id="fx_master_limiter",
            effect_type=AudioEffectType.LIMITER.value,
            order=0,
            parameters={"threshold": -1.0, "release": 100.0},
            mix=1.0,
        )
        bus.effects.append(limiter)
        self._buses[bus.bus_id] = bus

    def _seed_music_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_music",
            name="Music",
            bus_type=AudioBusType.MUSIC.value,
            parent_bus_id="bus_master",
            volume=0.8,
        )
        comp = AudioEffect(
            effect_id="fx_music_comp",
            effect_type=AudioEffectType.COMPRESSOR.value,
            order=0,
            parameters={"ratio": 3.0, "threshold": -18.0, "attack": 10.0, "release": 100.0},
            mix=1.0,
        )
        eq = AudioEffect(
            effect_id="fx_music_eq",
            effect_type=AudioEffectType.EQ_MID.value,
            order=1,
            parameters={"frequency": 200.0, "gain": -2.0, "q": 0.7},
            mix=1.0,
        )
        bus.effects.extend([comp, eq])
        self._buses[bus.bus_id] = bus

    def _seed_sfx_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_sfx",
            name="SFX",
            bus_type=AudioBusType.SFX.value,
            parent_bus_id="bus_master",
            volume=0.9,
        )
        comp = AudioEffect(
            effect_id="fx_sfx_comp",
            effect_type=AudioEffectType.COMPRESSOR.value,
            order=0,
            parameters={"ratio": 4.0, "threshold": -12.0, "attack": 5.0, "release": 80.0},
            mix=1.0,
        )
        bus.effects.append(comp)
        self._buses[bus.bus_id] = bus

    def _seed_dialogue_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_dialogue",
            name="Dialogue",
            bus_type=AudioBusType.DIALOGUE.value,
            parent_bus_id="bus_master",
            volume=1.0,
        )
        comp = AudioEffect(
            effect_id="fx_dlg_comp",
            effect_type=AudioEffectType.COMPRESSOR.value,
            order=0,
            parameters={"ratio": 6.0, "threshold": -10.0, "attack": 3.0, "release": 60.0},
            mix=1.0,
        )
        eq_high = AudioEffect(
            effect_id="fx_dlg_eq_high",
            effect_type=AudioEffectType.EQ_HIGH.value,
            order=1,
            parameters={"frequency": 8000.0, "gain": 2.0, "q": 0.7},
            mix=1.0,
        )
        bus.effects.extend([comp, eq_high])
        self._buses[bus.bus_id] = bus

    def _seed_ambient_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_ambient",
            name="Ambient",
            bus_type=AudioBusType.AMBIENT.value,
            parent_bus_id="bus_master",
            volume=0.6,
        )
        reverb = AudioEffect(
            effect_id="fx_amb_reverb",
            effect_type=AudioEffectType.REVERB.value,
            order=0,
            parameters={"room_size": 0.8, "damping": 0.5, "wet": 0.4, "dry": 0.6},
            mix=0.5,
        )
        bus.effects.append(reverb)
        self._buses[bus.bus_id] = bus

    def _seed_ui_bus(self) -> None:
        bus = AudioBus(
            bus_id="bus_ui",
            name="UI",
            bus_type=AudioBusType.UI.value,
            parent_bus_id="bus_master",
            volume=0.7,
        )
        self._buses[bus.bus_id] = bus

    def _seed_sound_cues(self) -> None:
        cues = [
            SoundCue(
                cue_id="cue_music_main",
                name="Main Theme",
                source_path="audio/music/main_theme.ogg",
                duration=180.0,
                volume=0.8,
                loop=True,
                streaming=True,
                tags=["music", "theme"],
            ),
            SoundCue(
                cue_id="cue_sfx_explosion",
                name="Explosion",
                source_path="audio/sfx/explosion.wav",
                duration=2.5,
                volume=0.9,
                spatialized=True,
                attenuation_radius=3000.0,
                tags=["sfx", "combat", "explosion"],
            ),
            SoundCue(
                cue_id="cue_sfx_footstep",
                name="Footstep",
                source_path="audio/sfx/footstep.wav",
                duration=0.4,
                volume=0.5,
                spatialized=True,
                attenuation_radius=800.0,
                tags=["sfx", "movement", "footstep"],
            ),
            SoundCue(
                cue_id="cue_dlg_narrator",
                name="Narrator Line",
                source_path="audio/dialogue/narrator_01.wav",
                duration=12.0,
                volume=1.0,
                streaming=True,
                tags=["dialogue", "narrator"],
            ),
            SoundCue(
                cue_id="cue_ui_click",
                name="UI Click",
                source_path="audio/ui/click.wav",
                duration=0.15,
                volume=0.6,
                tags=["ui", "click"],
            ),
        ]
        for cue in cues:
            self._cues[cue.cue_id] = cue

    # ------------------------------------------------------------------
    # Bus management
    # ------------------------------------------------------------------

    def create_bus(self, name: str, bus_type: str = AudioBusType.SFX.value,
                   parent_bus_id: str = "", volume: float = 1.0) -> AudioBus:
        """Create a new audio bus."""
        bt = _coerce_enum(AudioBusType, bus_type, AudioBusType.SFX)
        vol = _clamp(_safe_float(volume, 1.0), 0.0, 2.0)
        with self._lock:
            bus_id = _new_id("bus")
            bus = AudioBus(
                bus_id=bus_id,
                name=name or f"Bus {bus_id[-6:]}",
                bus_type=bt.value if bt else AudioBusType.SFX.value,
                parent_bus_id=parent_bus_id,
                volume=vol,
            )
            self._buses[bus_id] = bus
            _evict_fifo_dict(self._buses, _MAX_BUSES)
            self._emit("bus_created", bus_id=bus_id, name=bus.name)
            return bus

    def get_bus(self, bus_id: str) -> Optional[AudioBus]:
        """Retrieve a bus by id."""
        with self._lock:
            return self._buses.get(bus_id)

    def list_buses(self, bus_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all buses, optionally filtered by type."""
        with self._lock:
            out: List[Dict[str, Any]] = []
            for bus in self._buses.values():
                if bus_type is not None and bus.bus_type != bus_type:
                    continue
                out.append(bus.to_dict())
            return out

    def update_bus(self, bus_id: str, **fields: Any) -> Optional[AudioBus]:
        """Update mutable fields of a bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return None
            if "name" in fields:
                bus.name = str(fields["name"]) or bus.name
            if "volume" in fields:
                bus.volume = _clamp(_safe_float(fields["volume"], bus.volume), 0.0, 2.0)
            if "parent_bus_id" in fields:
                new_parent = str(fields["parent_bus_id"])
                if new_parent != bus_id and new_parent != bus.parent_bus_id:
                    bus.parent_bus_id = new_parent
            if "bus_type" in fields:
                bt = _coerce_enum(AudioBusType, fields["bus_type"], None)
                if bt is not None:
                    bus.bus_type = bt.value
            if "metadata" in fields and isinstance(fields["metadata"], dict):
                bus.metadata.update(fields["metadata"])
            bus.updated_at = _now()
            self._emit("bus_updated", bus_id=bus_id)
            return bus

    def remove_bus(self, bus_id: str) -> bool:
        """Remove a bus. Child buses are re-parented to the master if present."""
        with self._lock:
            if bus_id not in self._buses:
                return False
            master_id = "bus_master" if "bus_master" in self._buses else ""
            for other in self._buses.values():
                if other.parent_bus_id == bus_id:
                    other.parent_bus_id = master_id
            del self._buses[bus_id]
            self._emit("bus_removed", bus_id=bus_id)
            return True

    # ------------------------------------------------------------------
    # Channel management
    # ------------------------------------------------------------------

    def create_channel(self, name: str, bus_id: str, source_cue_id: str = "",
                       volume: float = 1.0) -> Optional[AudioChannel]:
        """Create a new channel assigned to a bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return None
            channel_id = _new_id("ch")
            channel = AudioChannel(
                channel_id=channel_id,
                name=name or f"Channel {channel_id[-6:]}",
                bus_id=bus_id,
                source_cue_id=source_cue_id,
                volume=_clamp(_safe_float(volume, 1.0), 0.0, 2.0),
            )
            bus.channels.append(channel)
            _evict_fifo_list(bus.channels, _MAX_CHANNELS)
            self._emit("channel_created", channel_id=channel_id, bus_id=bus_id)
            return channel

    def remove_channel(self, bus_id: str, channel_id: str) -> bool:
        """Remove a channel from a bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for idx, ch in enumerate(bus.channels):
                if ch.channel_id == channel_id:
                    bus.channels.pop(idx)
                    self._emit("channel_removed", channel_id=channel_id, bus_id=bus_id)
                    return True
            return False

    def set_volume(self, bus_id: str, channel_id: str, volume: float) -> bool:
        """Set the volume of a channel within a bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for ch in bus.channels:
                if ch.channel_id == channel_id:
                    ch.volume = _clamp(_safe_float(volume, ch.volume), 0.0, 2.0)
                    self._emit("channel_volume_set", channel_id=channel_id, volume=ch.volume)
                    return True
            return False

    def set_mute(self, bus_id: str, channel_id: str, muted: bool) -> bool:
        """Mute or unmute a channel."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for ch in bus.channels:
                if ch.channel_id == channel_id:
                    ch.muted = bool(muted)
                    self._emit("channel_mute_set", channel_id=channel_id, muted=ch.muted)
                    return True
            return False

    def set_solo(self, bus_id: str, channel_id: str, soloed: bool) -> bool:
        """Solo or unsolo a channel. When any channel is soloed, others are attenuated."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for ch in bus.channels:
                if ch.channel_id == channel_id:
                    ch.soloed = bool(soloed)
                    self._emit("channel_solo_set", channel_id=channel_id, soloed=ch.soloed)
                    return True
            return False

    # ------------------------------------------------------------------
    # Effect management
    # ------------------------------------------------------------------

    def add_effect(self, bus_id: str, effect_type: str,
                   parameters: Optional[Dict[str, Any]] = None,
                   mix: float = 1.0, enabled: bool = True) -> Optional[AudioEffect]:
        """Add a DSP effect to the end of a bus effect chain."""
        et = _coerce_enum(AudioEffectType, effect_type, AudioEffectType.REVERB)
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return None
            effect_id = _new_id("fx")
            order = len(bus.effects)
            effect = AudioEffect(
                effect_id=effect_id,
                effect_type=et.value if et else AudioEffectType.REVERB.value,
                enabled=bool(enabled),
                order=order,
                parameters=dict(parameters) if parameters else {},
                mix=_clamp(_safe_float(mix, 1.0), 0.0, 1.0),
            )
            bus.effects.append(effect)
            _evict_fifo_list(bus.effects, _MAX_EFFECTS_PER_BUS)
            self._emit("effect_added", bus_id=bus_id, effect_id=effect_id, effect_type=effect.effect_type)
            return effect

    def remove_effect(self, bus_id: str, effect_id: str) -> bool:
        """Remove an effect from a bus chain and re-index remaining effects."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for idx, fx in enumerate(bus.effects):
                if fx.effect_id == effect_id:
                    bus.effects.pop(idx)
                    for i, remaining in enumerate(bus.effects):
                        remaining.order = i
                    self._emit("effect_removed", bus_id=bus_id, effect_id=effect_id)
                    return True
            return False

    def set_effect_parameter(self, bus_id: str, effect_id: str,
                             parameter_name: str, value: Any) -> bool:
        """Set a single parameter on a bus effect."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for fx in bus.effects:
                if fx.effect_id == effect_id:
                    fx.parameters[str(parameter_name)] = _to_jsonable(value)
                    self._emit("effect_parameter_set", bus_id=bus_id, effect_id=effect_id,
                               parameter=parameter_name)
                    return True
            return False

    # ------------------------------------------------------------------
    # Sound cue management
    # ------------------------------------------------------------------

    def create_cue(self, name: str, source_path: str = "", duration: float = 0.0,
                   volume: float = 1.0, loop: bool = False,
                   spatialized: bool = False, tags: Optional[List[str]] = None) -> SoundCue:
        """Create a new sound cue definition."""
        with self._lock:
            cue_id = _new_id("cue")
            cue = SoundCue(
                cue_id=cue_id,
                name=name or f"Cue {cue_id[-6:]}",
                source_path=str(source_path),
                duration=max(0.0, _safe_float(duration, 0.0)),
                volume=_clamp(_safe_float(volume, 1.0), 0.0, 2.0),
                loop=bool(loop),
                spatialized=bool(spatialized),
                tags=list(tags) if tags else [],
            )
            self._cues[cue_id] = cue
            _evict_fifo_dict(self._cues, _MAX_CUES)
            self._emit("cue_created", cue_id=cue_id, name=cue.name)
            return cue

    def get_cue(self, cue_id: str) -> Optional[SoundCue]:
        """Retrieve a sound cue by id."""
        with self._lock:
            return self._cues.get(cue_id)

    def list_cues(self, tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sound cues, optionally filtered by tag."""
        with self._lock:
            out: List[Dict[str, Any]] = []
            for cue in self._cues.values():
                if tag is not None and tag not in cue.tags:
                    continue
                out.append(cue.to_dict())
            return out

    def update_cue(self, cue_id: str, **fields: Any) -> Optional[SoundCue]:
        """Update mutable fields of a sound cue."""
        with self._lock:
            cue = self._cues.get(cue_id)
            if cue is None:
                return None
            if "name" in fields:
                cue.name = str(fields["name"]) or cue.name
            if "source_path" in fields:
                cue.source_path = str(fields["source_path"])
            if "duration" in fields:
                cue.duration = max(0.0, _safe_float(fields["duration"], cue.duration))
            if "volume" in fields:
                cue.volume = _clamp(_safe_float(fields["volume"], cue.volume), 0.0, 2.0)
            if "pitch" in fields:
                cue.pitch = _safe_float(fields["pitch"], cue.pitch)
            if "loop" in fields:
                cue.loop = bool(fields["loop"])
            if "spatialized" in fields:
                cue.spatialized = bool(fields["spatialized"])
            if "attenuation_radius" in fields:
                cue.attenuation_radius = max(0.0, _safe_float(fields["attenuation_radius"], cue.attenuation_radius))
            if "tags" in fields and isinstance(fields["tags"], list):
                cue.tags = [str(t) for t in fields["tags"]]
            if "metadata" in fields and isinstance(fields["metadata"], dict):
                cue.metadata.update(fields["metadata"])
            self._emit("cue_updated", cue_id=cue_id)
            return cue

    def remove_cue(self, cue_id: str) -> bool:
        """Remove a sound cue definition."""
        with self._lock:
            if cue_id not in self._cues:
                return False
            del self._cues[cue_id]
            self._emit("cue_removed", cue_id=cue_id)
            return True

    def play_cue(self, cue_id: str, bus_id: str = "") -> Optional[AudioChannel]:
        """Play a sound cue on a bus, creating a live channel for it."""
        with self._lock:
            cue = self._cues.get(cue_id)
            if cue is None:
                return None
            target_bus_id = bus_id
            if not target_bus_id:
                if cue.tags and "music" in cue.tags:
                    target_bus_id = "bus_music" if "bus_music" in self._buses else ""
                elif cue.tags and "dialogue" in cue.tags:
                    target_bus_id = "bus_dialogue" if "bus_dialogue" in self._buses else ""
                elif cue.tags and "ui" in cue.tags:
                    target_bus_id = "bus_ui" if "bus_ui" in self._buses else ""
                elif cue.tags and "ambient" in cue.tags:
                    target_bus_id = "bus_ambient" if "bus_ambient" in self._buses else ""
                else:
                    target_bus_id = "bus_sfx" if "bus_sfx" in self._buses else ""
            if not target_bus_id or target_bus_id not in self._buses:
                target_bus_id = next(iter(self._buses.keys()), "")
            if not target_bus_id:
                return None
            channel = self.create_channel(
                name=cue.name,
                bus_id=target_bus_id,
                source_cue_id=cue_id,
                volume=cue.volume,
            )
            if channel is not None:
                channel.playing = True
                channel.looping = cue.loop
                channel.pitch = cue.pitch
                channel.pan = cue.pan
                self._emit("cue_played", cue_id=cue_id, channel_id=channel.channel_id, bus_id=target_bus_id)
            return channel

    def stop_cue(self, bus_id: str, channel_id: str) -> bool:
        """Stop a playing channel by removing it from the bus."""
        with self._lock:
            bus = self._buses.get(bus_id)
            if bus is None:
                return False
            for ch in bus.channels:
                if ch.channel_id == channel_id:
                    ch.playing = False
                    ch.position = 0.0
                    self._emit("cue_stopped", channel_id=channel_id, bus_id=bus_id)
                    return True
            return False

    # ------------------------------------------------------------------
    # Mix levels and presets
    # ------------------------------------------------------------------

    def get_levels(self) -> Dict[str, Any]:
        """Compute simulated RMS and peak levels for every bus and channel."""
        with self._lock:
            bus_levels: List[Dict[str, Any]] = []
            for bus in self._buses.values():
                effective_vol = 0.0 if bus.muted else bus.volume
                has_solo = any(ch.soloed for ch in bus.channels)
                channel_levels: List[Dict[str, Any]] = []
                bus_rms = 0.0
                bus_peak = 0.0
                active_count = 0
                for ch in bus.channels:
                    if not ch.playing:
                        continue
                    if has_solo and not ch.soloed:
                        continue
                    ch_vol = 0.0 if ch.muted else ch.volume * effective_vol
                    # Deterministic pseudo-level derived from channel id hash
                    seed_val = abs(hash(ch.channel_id)) % 1000
                    rms = _clamp((seed_val / 1000.0) * ch_vol, 0.0, 1.0)
                    peak = _clamp(rms * 1.4, 0.0, 1.0)
                    channel_levels.append({
                        "channel_id": ch.channel_id,
                        "name": ch.name,
                        "rms": round(rms, 4),
                        "peak": round(peak, 4),
                        "volume": round(ch_vol, 4),
                        "muted": ch.muted,
                        "soloed": ch.soloed,
                    })
                    bus_rms = max(bus_rms, rms)
                    bus_peak = max(bus_peak, peak)
                    active_count += 1
                if active_count == 0:
                    bus_rms = 0.0
                    bus_peak = 0.0
                bus_levels.append({
                    "bus_id": bus.bus_id,
                    "name": bus.name,
                    "bus_type": bus.bus_type,
                    "rms": round(bus_rms, 4),
                    "peak": round(bus_peak, 4),
                    "volume": round(effective_vol, 4),
                    "muted": bus.muted,
                    "channel_count": len(bus.channels),
                    "active_channels": active_count,
                    "channels": channel_levels,
                })
            return {
                "timestamp": _now(),
                "buses": bus_levels,
                "total_buses": len(self._buses),
                "total_cues": len(self._cues),
            }

    def apply_mix_preset(self, preset_id: str) -> bool:
        """Apply a saved mix preset to restore bus volumes and effect states."""
        with self._lock:
            preset = self._presets.get(preset_id)
            if preset is None:
                return False
            for bus_id, vol in preset.bus_volumes.items():
                bus = self._buses.get(bus_id)
                if bus is not None:
                    bus.volume = _clamp(_safe_float(vol, bus.volume), 0.0, 2.0)
            for bus_id, muted in preset.bus_mutes.items():
                bus = self._buses.get(bus_id)
                if bus is not None:
                    bus.muted = bool(muted)
            for bus_id, effect_states in preset.effect_states.items():
                bus = self._buses.get(bus_id)
                if bus is None:
                    continue
                for fx in bus.effects:
                    state = effect_states.get(fx.effect_id)
                    if state is None:
                        continue
                    if "enabled" in state:
                        fx.enabled = bool(state["enabled"])
                    if "mix" in state:
                        fx.mix = _clamp(_safe_float(state["mix"], fx.mix), 0.0, 1.0)
                    if "parameters" in state and isinstance(state["parameters"], dict):
                        fx.parameters.update(state["parameters"])
            self._emit("preset_applied", preset_id=preset_id)
            return True

    def save_mix_preset(self, name: str, description: str = "") -> AudioMixPreset:
        """Capture the current bus volumes and effect states as a preset."""
        with self._lock:
            preset_id = _new_id("mix")
            bus_volumes: Dict[str, float] = {}
            bus_mutes: Dict[str, bool] = {}
            effect_states: Dict[str, Dict[str, Any]] = {}
            for bus in self._buses.values():
                bus_volumes[bus.bus_id] = bus.volume
                bus_mutes[bus.bus_id] = bus.muted
                states: Dict[str, Any] = {}
                for fx in bus.effects:
                    states[fx.effect_id] = {
                        "enabled": fx.enabled,
                        "mix": fx.mix,
                        "parameters": dict(fx.parameters),
                    }
                effect_states[bus.bus_id] = states
            preset = AudioMixPreset(
                preset_id=preset_id,
                name=name or f"Mix Preset {preset_id[-6:]}",
                description=description,
                bus_volumes=bus_volumes,
                bus_mutes=bus_mutes,
                effect_states=effect_states,
            )
            self._presets[preset_id] = preset
            self._emit("preset_saved", preset_id=preset_id, name=preset.name)
            return preset

    def list_presets(self) -> List[Dict[str, Any]]:
        """List all saved mix presets."""
        with self._lock:
            return [p.to_dict() for p in self._presets.values()]

    def remove_preset(self, preset_id: str) -> bool:
        """Remove a saved mix preset."""
        with self._lock:
            if preset_id not in self._presets:
                return False
            del self._presets[preset_id]
            self._emit("preset_removed", preset_id=preset_id)
            return True

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recent audio mixer events."""
        with self._lock:
            n = max(1, min(int(limit), len(self._events)))
            return list(self._events[-n:])

    # ------------------------------------------------------------------
    # AI methods
    # ------------------------------------------------------------------

    def ai_generate_mix(self, description: str) -> Dict[str, Any]:
        """Generate a bus hierarchy and effect setup from a description."""
        if not description or not description.strip():
            return {"success": False, "error": "Description is required."}
        desc_lower = description.lower()
        actions: List[str] = []
        # Detect scene type and adjust bus volumes
        if any(w in desc_lower for w in ["combat", "battle", "fight", "war"]):
            self.update_bus("bus_sfx", volume=1.0)
            self.update_bus("bus_music", volume=0.6)
            self.update_bus("bus_dialogue", volume=1.0)
            actions.append("Raised SFX bus to 1.0 for combat emphasis.")
            actions.append("Duck music bus to 0.6 to keep dialogue clear.")
            if "bus_sfx" in self._buses:
                has_limiter = any(fx.effect_type == AudioEffectType.LIMITER.value
                                  for fx in self._buses["bus_sfx"].effects)
                if not has_limiter:
                    self.add_effect("bus_sfx", AudioEffectType.LIMITER.value,
                                    {"threshold": -2.0, "release": 50.0})
                    actions.append("Added a limiter to the SFX bus to prevent clipping.")
        elif any(w in desc_lower for w in ["menu", "ui", "interface", "lobby"]):
            self.update_bus("bus_music", volume=0.8)
            self.update_bus("bus_ui", volume=0.9)
            self.update_bus("bus_sfx", volume=0.4)
            actions.append("Raised music and UI buses for menu ambience.")
            actions.append("Lowered SFX bus since gameplay sounds are inactive.")
        elif any(w in desc_lower for w in ["cutscene", "cinematic", "story", "narrative"]):
            self.update_bus("bus_music", volume=0.9)
            self.update_bus("bus_dialogue", volume=1.0)
            self.update_bus("bus_ambient", volume=0.5)
            actions.append("Emphasized music and dialogue for cinematic scene.")
            actions.append("Reduced ambient bus to avoid distraction.")
        elif any(w in desc_lower for w in ["explore", "ambient", "open world", "nature"]):
            self.update_bus("bus_ambient", volume=0.8)
            self.update_bus("bus_music", volume=0.6)
            actions.append("Raised ambient bus for exploration atmosphere.")
            actions.append("Set music to a gentle background level.")
        # Add reverb to ambient bus if description mentions caves or halls
        if any(w in desc_lower for w in ["cave", "cavern", "hall", "cathedral", "echo"]):
            if "bus_ambient" in self._buses:
                has_reverb = any(fx.effect_type == AudioEffectType.REVERB.value
                                 for fx in self._buses["bus_ambient"].effects)
                if not has_reverb:
                    self.add_effect("bus_ambient", AudioEffectType.REVERB.value,
                                    {"room_size": 0.9, "damping": 0.3, "wet": 0.6, "dry": 0.4})
                    actions.append("Added a large-space reverb to the ambient bus.")
        preset = self.save_mix_preset(
            name=f"AI Mix: {description[:40]}",
            description=f"Auto-generated mix for: {description[:120]}",
        )
        self._emit("ai_generated_mix", description=description[:100], preset_id=preset.preset_id)
        return {
            "success": True,
            "preset_id": preset.preset_id,
            "actions": actions,
            "bus_count": len(self._buses),
        }

    def ai_optimize_levels(self) -> Dict[str, Any]:
        """Analyze current levels and apply automatic gain adjustments."""
        with self._lock:
            levels = self.get_levels()
            adjustments: List[str] = []
            for bus_info in levels["buses"]:
                bus_id = bus_info["bus_id"]
                peak = bus_info["peak"]
                rms = bus_info["rms"]
                bus = self._buses.get(bus_id)
                if bus is None:
                    continue
                if peak > 0.95:
                    new_vol = _clamp(bus.volume * 0.85, 0.0, 2.0)
                    bus.volume = new_vol
                    adjustments.append(
                        f"Reduced '{bus.name}' bus from peak {peak:.2f} (volume lowered to {new_vol:.2f}).")
                elif rms < 0.1 and bus.volume < 1.5 and not bus.muted:
                    new_vol = _clamp(bus.volume * 1.15, 0.0, 2.0)
                    bus.volume = new_vol
                    adjustments.append(
                        f"Raised '{bus.name}' bus from rms {rms:.2f} (volume increased to {new_vol:.2f}).")
                bus.updated_at = _now()
            # Ensure master bus is not clipping
            master = self._buses.get("bus_master")
            if master is not None:
                master_peak = next(
                    (b["peak"] for b in levels["buses"] if b["bus_id"] == "bus_master"), 0.0)
                if master_peak > 0.98 and master.volume > 0.8:
                    master.volume = _clamp(master.volume * 0.9, 0.0, 2.0)
                    adjustments.append(
                        f"Limited master bus to avoid clipping (volume now {master.volume:.2f}).")
            self._emit("ai_optimized_levels", adjustments=adjustments)
            return {
                "success": True,
                "adjustments": adjustments,
                "levels": levels,
            }

    def ai_suggest_effects(self, description: str) -> List[Dict[str, Any]]:
        """Suggest audio effects based on a description of the desired sound."""
        if not description or not description.strip():
            return []
        desc_lower = description.lower()
        suggestions: List[Dict[str, Any]] = []
        effect_map: List[Tuple[List[str], AudioEffectType, str, Dict[str, Any]]] = [
            (["reverb", "echo", "space", "room", "hall", "cave"],
             AudioEffectType.REVERB, "Add reverb for spatial depth.",
             {"room_size": 0.7, "damping": 0.5, "wet": 0.4, "dry": 0.6}),
            (["delay", "repeat", "echoes"],
             AudioEffectType.DELAY, "Add delay for rhythmic echoes.",
             {"time": 250.0, "feedback": 0.3, "mix": 0.3}),
            (["bass", "low", "rumble", "boom"],
             AudioEffectType.EQ_LOW, "Boost low frequencies for bass presence.",
             {"frequency": 120.0, "gain": 3.0, "q": 0.7}),
            (["mid", "presence", "body", "warmth"],
             AudioEffectType.EQ_MID, "Shape midrange for vocal or instrument presence.",
             {"frequency": 1000.0, "gain": 2.0, "q": 0.7}),
            (["high", "treble", "bright", "crisp", "air"],
             AudioEffectType.EQ_HIGH, "Enhance high frequencies for clarity and brightness.",
             {"frequency": 8000.0, "gain": 2.0, "q": 0.7}),
            (["compress", "dynamic", "control", "even"],
             AudioEffectType.COMPRESSOR, "Compress dynamics for consistent loudness.",
             {"ratio": 4.0, "threshold": -12.0, "attack": 10.0, "release": 100.0}),
            (["limit", "clip", "protect", "ceiling"],
             AudioEffectType.LIMITER, "Add a limiter to prevent clipping.",
             {"threshold": -1.0, "release": 100.0}),
            (["distort", "overdrive", "fuzz", "grit"],
             AudioEffectType.DISTORTION, "Add distortion for aggressive character.",
             {"drive": 0.4, "tone": 0.5, "mix": 0.5}),
            (["chorus", "thicken", "ensemble", "shimmer"],
             AudioEffectType.CHORUS, "Add chorus for a thick, shimmering texture.",
             {"rate": 1.5, "depth": 0.3, "mix": 0.4}),
            (["flanger", "sweep", "jet", "metallic"],
             AudioEffectType.FLANGER, "Add flanger for a sweeping metallic effect.",
             {"rate": 0.5, "depth": 0.5, "feedback": 0.3, "mix": 0.4}),
            (["pitch", "shift", "harmonize", "octave"],
             AudioEffectType.PITCH_SHIFT, "Shift pitch for harmonic variation.",
             {"semitones": 7.0, "mix": 0.5}),
            (["stretch", "slow", "fast", "time"],
             AudioEffectType.TIME_STRETCH, "Stretch time for tempo adjustment.",
             {"ratio": 1.0, "mix": 1.0}),
        ]
        for keywords, etype, reason, params in effect_map:
            if any(w in desc_lower for w in keywords):
                suggestions.append({
                    "effect_type": etype.value,
                    "label": etype.value.replace("_", " ").title(),
                    "reason": reason,
                    "suggested_parameters": params,
                })
        if not suggestions:
            suggestions.append({
                "effect_type": AudioEffectType.COMPRESSOR.value,
                "label": "Compressor",
                "reason": "A compressor is a versatile starting point for mix control.",
                "suggested_parameters": {"ratio": 3.0, "threshold": -15.0, "attack": 10.0, "release": 100.0},
            })
        self._emit("ai_suggested_effects", description=description[:100], count=len(suggestions))
        return suggestions


# ===========================================================================
# 6. Copilot Conversational Panel
# ===========================================================================

class MessageType(Enum):
    """Role of a participant in a copilot conversation."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class SuggestionType(Enum):
    """Category of a design suggestion produced by the copilot."""
    DESIGN = "design"
    GAMEPLAY = "gameplay"
    BALANCE = "balance"
    TECHNICAL = "technical"
    NARRATIVE = "narrative"
    ASSET = "asset"


class GuidanceKind(Enum):
    """Kind of structured guidance the copilot can provide."""
    TUTORIAL = "tutorial"
    BEST_PRACTICE = "best_practice"
    PITFALL = "pitfall"
    OPTIMIZATION = "optimization"
    WORKFLOW = "workflow"


@dataclass
class ConversationMessage:
    """A single message within a copilot conversation."""
    message_id: str
    message_type: str = MessageType.USER.value
    content: str = ""
    timestamp: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesignContext:
    """Context describing the current design state for copilot queries."""
    project_name: str = ""
    genre: str = ""
    platform: str = ""
    scene_name: str = ""
    active_entity: str = ""
    active_component: str = ""
    target_audience: str = ""
    constraints: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SuggestionResult:
    """A structured suggestion returned by the copilot."""
    suggestion_id: str
    suggestion_type: str = SuggestionType.DESIGN.value
    title: str = ""
    description: str = ""
    priority: str = "medium"
    actionable: bool = True
    steps: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuidanceResult:
    """Structured guidance content returned by the copilot."""
    guidance_id: str
    guidance_kind: str = GuidanceKind.BEST_PRACTICE.value
    topic: str = ""
    summary: str = ""
    details: str = ""
    examples: List[str] = field(default_factory=list)
    related_concepts: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CopilotSession:
    """A conversation session with the design copilot."""
    session_id: str
    name: str
    messages: List[ConversationMessage] = field(default_factory=list)
    context: DesignContext = field(default_factory=DesignContext)
    suggestions: List[SuggestionResult] = field(default_factory=list)
    guidance: List[GuidanceResult] = field(default_factory=list)
    active: bool = True
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class CopilotConversationalPanel:
    """Natural-language design copilot for the editor.

    Provides a conversational interface that lets designers ask
    questions, request suggestions, analyze designs, generate ideas,
    review game balance, and search a knowledge base. The copilot
    parses natural language descriptions and returns structured,
    actionable results.
    """

    def __init__(self, system: Optional["_EditorSubsystemsSystem"] = None) -> None:
        self._system = system
        self._lock = threading.RLock()
        self._sessions: Dict[str, CopilotSession] = {}
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._seeded: bool = False
        self._seed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"cop_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _seed(self) -> None:
        """Populate the copilot with starter sessions and knowledge."""
        if self._seeded:
            return
        with self._lock:
            if self._seeded:
                return
            self._seed_level_design_session()
            self._seed_combat_balance_session()
            self._seed_onboarding_session()
            self._seeded = True

    def _seed_level_design_session(self) -> None:
        session = CopilotSession(
            session_id="session_level_design",
            name="Level Design Brainstorm",
        )
        session.context = DesignContext(
            project_name="SparkLabs Demo",
            genre="action_adventure",
            platform="pc",
            scene_name="forest_temple",
        )
        session.messages.append(ConversationMessage(
            message_id="msg_ld_1",
            message_type=MessageType.USER.value,
            content="How should I structure the pacing for the forest temple level?",
        ))
        session.messages.append(ConversationMessage(
            message_id="msg_ld_2",
            message_type=MessageType.ASSISTANT.value,
            content="A good pacing curve alternates tension and release. Start with "
                    "exploration and light combat, introduce a puzzle that teaches a "
                    "mechanic, then escalate to a mini-boss. Place a save point after "
                    "the mini-boss, followed by a harder combat encounter, and conclude "
                    "with the main boss. This gives players roughly 15-20 minutes of "
                    "content with clear emotional beats.",
        ))
        self._sessions[session.session_id] = session

    def _seed_combat_balance_session(self) -> None:
        session = CopilotSession(
            session_id="session_combat_balance",
            name="Combat Balance Review",
        )
        session.context = DesignContext(
            project_name="SparkLabs Demo",
            genre="action_rpg",
            platform="pc",
            active_component="combat_system",
        )
        session.messages.append(ConversationMessage(
            message_id="msg_cb_1",
            message_type=MessageType.USER.value,
            content="My warrior class feels too weak compared to the mage. How can I balance them?",
        ))
        session.messages.append(ConversationMessage(
            message_id="msg_cb_2",
            message_type=MessageType.ASSISTANT.value,
            content="Consider these approaches: (1) Increase the warrior's base health "
                    "and armor scaling so they survive longer in melee. (2) Add a "
                    "gap-closer ability so the warrior can reach ranged enemies. "
                    "(3) Reduce mage burst damage cooldown or add cast-time delays. "
                    "(4) Give the warrior crowd-control immunity during certain attacks. "
                    "Test each change in isolation to measure its impact.",
        ))
        self._sessions[session.session_id] = session

    def _seed_onboarding_session(self) -> None:
        session = CopilotSession(
            session_id="session_onboarding",
            name="Getting Started",
        )
        session.context = DesignContext(
            project_name="SparkLabs Demo",
            genre="platformer",
            platform="multi",
            target_audience="casual",
        )
        session.messages.append(ConversationMessage(
            message_id="msg_ob_1",
            message_type=MessageType.SYSTEM.value,
            content="Welcome to the SparkLabs Copilot. Ask me about level design, "
                    "gameplay mechanics, balance, or any aspect of your project.",
        ))
        session.messages.append(ConversationMessage(
            message_id="msg_ob_2",
            message_type=MessageType.USER.value,
            content="What are the first things I should set up for a new platformer?",
        ))
        session.messages.append(ConversationMessage(
            message_id="msg_ob_3",
            message_type=MessageType.ASSISTANT.value,
            content="Start with these foundations: (1) Define your core movement "
                    "parameters: run speed, jump height, gravity, and coyote time. "
                    "(2) Create a test level with flat ground, ramps, and gaps to "
                    "validate feel. (3) Set up input mapping for keyboard and "
                    "controller. (4) Add a basic camera follow script. (5) Create "
                    "placeholder art so you can iterate on gameplay before final assets.",
        ))
        self._sessions[session.session_id] = session

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_session(self, name: str = "", context: Optional[DesignContext] = None) -> CopilotSession:
        """Start a new copilot conversation session."""
        with self._lock:
            session_id = _new_id("session")
            session = CopilotSession(
                session_id=session_id,
                name=name or f"Session {session_id[-6:]}",
                context=context if context is not None else DesignContext(),
            )
            self._sessions[session_id] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._emit("session_started", session_id=session_id, name=session.name)
            return session

    def end_session(self, session_id: str) -> bool:
        """Mark a session as inactive without deleting it."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.active = False
            session.updated_at = _now()
            self._emit("session_ended", session_id=session_id)
            return True

    def get_session(self, session_id: str) -> Optional[CopilotSession]:
        """Retrieve a session by id."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, active_only: bool = False) -> List[Dict[str, Any]]:
        """List all sessions, optionally filtering to active ones."""
        with self._lock:
            out: List[Dict[str, Any]] = []
            for session in self._sessions.values():
                if active_only and not session.active:
                    continue
                out.append({
                    "session_id": session.session_id,
                    "name": session.name,
                    "active": session.active,
                    "message_count": len(session.messages),
                    "suggestion_count": len(session.suggestions),
                    "created_at": session.created_at,
                    "updated_at": session.updated_at,
                })
            return out

    def remove_session(self, session_id: str) -> bool:
        """Permanently remove a session."""
        with self._lock:
            if session_id not in self._sessions:
                return False
            del self._sessions[session_id]
            self._emit("session_removed", session_id=session_id)
            return True

    # ------------------------------------------------------------------
    # Messaging
    # ------------------------------------------------------------------

    def send_message(self, session_id: str, content: str,
                     message_type: str = MessageType.USER.value) -> Optional[ConversationMessage]:
        """Send a message in a session and generate an assistant response."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            mt = _coerce_enum(MessageType, message_type, MessageType.USER)
            user_msg = ConversationMessage(
                message_id=_new_id("msg"),
                message_type=mt.value if mt else MessageType.USER.value,
                content=content,
            )
            session.messages.append(user_msg)
            _evict_fifo_list(session.messages, _MAX_MESSAGES_PER_SESSION)
            session.updated_at = _now()
            self._emit("message_sent", session_id=session_id, message_id=user_msg.message_id)
            # Generate an assistant response for user messages
            if mt == MessageType.USER:
                response_text = self.ai_respond(session_id, content)
                assistant_msg = ConversationMessage(
                    message_id=_new_id("msg"),
                    message_type=MessageType.ASSISTANT.value,
                    content=response_text,
                )
                session.messages.append(assistant_msg)
                _evict_fifo_list(session.messages, _MAX_MESSAGES_PER_SESSION)
                self._emit("message_received", session_id=session_id,
                           message_id=assistant_msg.message_id)
                return assistant_msg
            return user_msg

    def get_history(self, session_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the message history for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            n = max(1, min(int(limit), len(session.messages)))
            return [m.to_dict() for m in session.messages[-n:]]

    def clear_history(self, session_id: str) -> bool:
        """Clear all messages from a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.messages.clear()
            session.updated_at = _now()
            self._emit("history_cleared", session_id=session_id)
            return True

    # ------------------------------------------------------------------
    # Context management
    # ------------------------------------------------------------------

    def set_context(self, session_id: str, **fields: Any) -> Optional[DesignContext]:
        """Update the design context for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            ctx = session.context
            for key in ("project_name", "genre", "platform", "scene_name",
                        "active_entity", "active_component", "target_audience"):
                if key in fields and fields[key] is not None:
                    setattr(ctx, key, str(fields[key]))
            if "constraints" in fields and isinstance(fields["constraints"], list):
                ctx.constraints = [str(c) for c in fields["constraints"]]
            if "metadata" in fields and isinstance(fields["metadata"], dict):
                ctx.metadata.update(fields["metadata"])
            session.updated_at = _now()
            self._emit("context_set", session_id=session_id)
            return ctx

    def get_context(self, session_id: str) -> Optional[DesignContext]:
        """Retrieve the design context for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            return session.context

    # ------------------------------------------------------------------
    # Suggestions and guidance
    # ------------------------------------------------------------------

    def get_suggestions(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Return suggestions stored for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            n = max(1, min(int(limit), len(session.suggestions)))
            return [s.to_dict() for s in session.suggestions[-n:]]

    def get_guidance(self, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Return guidance entries stored for a session."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            n = max(1, min(int(limit), len(session.guidance)))
            return [g.to_dict() for g in session.guidance[-n:]]

    def analyze_design(self, session_id: str, description: str) -> Dict[str, Any]:
        """Analyze a design description and return strengths, weaknesses, and tips."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"success": False, "error": "Session not found."}
            desc_lower = description.lower()
            strengths: List[str] = []
            weaknesses: List[str] = []
            tips: List[str] = []
            if any(w in desc_lower for w in ["clear", "simple", "intuitive", "accessible"]):
                strengths.append("The design prioritizes clarity and accessibility.")
            if any(w in desc_lower for w in ["complex", "deep", "layered", "strategic"]):
                strengths.append("The design offers strategic depth for engaged players.")
            if any(w in desc_lower for w in ["innovative", "unique", "novel", "original"]):
                strengths.append("The design introduces an original mechanic.")
            if any(w in desc_lower for w in ["tutorial", "onboarding", "guide", "teach"]):
                strengths.append("The design includes explicit player onboarding.")
            if any(w in desc_lower for w in ["grind", "repetitive", "tedious", "boring"]):
                weaknesses.append("The design may feel grindy or repetitive over time.")
            if any(w in desc_lower for w in ["steep", "difficult", "hard", "punishing"]):
                weaknesses.append("The difficulty curve may be too steep for new players.")
            if any(w in desc_lower for w in ["unclear", "confusing", "ambiguous"]):
                weaknesses.append("Some objectives may be unclear to players.")
            if any(w in desc_lower for w in ["cluttered", "overwhelming", "too many"]):
                weaknesses.append("The design may overwhelm players with too many systems.")
            tips.append("Prototype the core loop early and playtest with target-audience players.")
            tips.append("Instrument analytics to track where players drop off.")
            tips.append("Iterate on feedback in small, measurable increments.")
            suggestion = SuggestionResult(
                suggestion_id=_new_id("sug"),
                suggestion_type=SuggestionType.DESIGN.value,
                title=f"Design Analysis: {description[:40]}",
                description=f"Automated analysis of design description.",
                priority="medium",
                steps=tips,
            )
            session.suggestions.append(suggestion)
            session.updated_at = _now()
            self._emit("design_analyzed", session_id=session_id, suggestion_id=suggestion.suggestion_id)
            return {
                "success": True,
                "strengths": strengths,
                "weaknesses": weaknesses,
                "tips": tips,
                "suggestion_id": suggestion.suggestion_id,
            }

    def generate_ideas(self, session_id: str, topic: str, count: int = 5) -> List[Dict[str, Any]]:
        """Generate creative ideas for a given topic."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            topic_lower = topic.lower()
            ideas: List[Dict[str, Any]] = []
            idea_bank: List[Tuple[List[str], str, str]] = [
                (["level", "stage", "map"], "Procedural Variation",
                 "Generate small variations of the level layout each playthrough to keep it fresh."),
                (["level", "stage", "map"], "Branching Paths",
                 "Offer multiple routes with different risk/reward trade-offs."),
                (["level", "stage", "map"], "Environmental Storytelling",
                 "Use props and lighting to tell a story without dialogue."),
                (["character", "hero", "player"], "Asymmetric Abilities",
                 "Give the character distinct movement and combat abilities that complement each other."),
                (["character", "hero", "player"], "Progression Tree",
                 "Let players unlock abilities in a branching tree with meaningful choices."),
                (["enemy", "mob", "boss"], "Adaptive AI",
                 "Enemies that learn from player behavior and adjust their tactics."),
                (["enemy", "mob", "boss"], "Weak Point System",
                 "Design bosses with discoverable weak points that reward observation."),
                (["puzzle", "riddle", "challenge"], "Component Combination",
                 "Puzzles where players combine environmental components in unexpected ways."),
                (["puzzle", "riddle", "challenge"], "Time Manipulation",
                 "Puzzles that involve rewinding or pausing time to solve."),
                (["story", "narrative", "plot"], "Emergent Dialogue",
                 "Dialogue that changes based on player actions and world state."),
                (["story", "narrative", "plot"], "Multiple Endings",
                 "Branching conclusions based on key decisions throughout the game."),
                (["combat", "fight", "battle"], "Stance Switching",
                 "A combat system where players switch stances for different movesets."),
                (["combat", "fight", "battle"], "Combo Customization",
                 "Let players build their own combo strings from unlocked moves."),
                (["music", "audio", "sound"], "Reactive Score",
                 "Music that dynamically shifts intensity based on gameplay state."),
                (["ui", "interface", "hud"], "Diegetic UI",
                 "Integrate interface elements into the game world for immersion."),
            ]
            for keywords, title, desc in idea_bank:
                if any(w in topic_lower for w in keywords):
                    ideas.append({"title": title, "description": desc})
                    if len(ideas) >= count:
                        break
            if not ideas:
                ideas.append({
                    "title": "Core Loop Refinement",
                    "description": "Identify the single most engaging action and build the entire game around it.",
                })
                ideas.append({
                    "title": "Player Expression",
                    "description": "Give players multiple valid ways to approach every challenge.",
                })
            suggestion = SuggestionResult(
                suggestion_id=_new_id("sug"),
                suggestion_type=SuggestionType.DESIGN.value,
                title=f"Ideas for: {topic[:40]}",
                description=f"Generated {len(ideas)} ideas for the topic.",
                priority="low",
                steps=[i["title"] for i in ideas],
            )
            session.suggestions.append(suggestion)
            session.updated_at = _now()
            self._emit("ideas_generated", session_id=session_id, count=len(ideas))
            return ideas

    def review_balance(self, session_id: str, entity_a: str, entity_b: str,
                       stat_a: Optional[Dict[str, float]] = None,
                       stat_b: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Review the balance between two entities using optional stat dictionaries."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"success": False, "error": "Session not found."}
            findings: List[str] = []
            recommendations: List[str] = []
            if stat_a and stat_b:
                all_keys = set(stat_a.keys()) | set(stat_b.keys())
                for key in all_keys:
                    va = _safe_float(stat_a.get(key), 0.0)
                    vb = _safe_float(stat_b.get(key), 0.0)
                    if va == 0.0 and vb == 0.0:
                        continue
                    ratio = va / vb if vb != 0.0 else float("inf")
                    if ratio > 1.5:
                        findings.append(f"{entity_a} exceeds {entity_b} in '{key}' by {((ratio - 1) * 100):.0f}%.")
                        recommendations.append(
                            f"Consider reducing {entity_a}'s '{key}' or increasing {entity_b}'s '{key}'.")
                    elif ratio < 0.67:
                        findings.append(f"{entity_a} trails {entity_b} in '{key}' by {((1 - ratio) * 100):.0f}%.")
                        recommendations.append(
                            f"Consider increasing {entity_a}'s '{key}' or reducing {entity_b}'s '{key}'.")
            else:
                findings.append("No stat dictionaries provided; performing qualitative review.")
                recommendations.append("Define explicit numeric stats to enable quantitative comparison.")
                recommendations.append(f"Ensure {entity_a} and {entity_b} have distinct strengths and weaknesses.")
                recommendations.append("Playtest both entities in the same scenarios to surface disparities.")
            suggestion = SuggestionResult(
                suggestion_id=_new_id("sug"),
                suggestion_type=SuggestionType.BALANCE.value,
                title=f"Balance Review: {entity_a} vs {entity_b}",
                description=f"Compared {entity_a} and {entity_b} across available stats.",
                priority="high" if findings else "medium",
                steps=recommendations,
            )
            session.suggestions.append(suggestion)
            session.updated_at = _now()
            self._emit("balance_reviewed", session_id=session_id,
                       entity_a=entity_a, entity_b=entity_b)
            return {
                "success": True,
                "entity_a": entity_a,
                "entity_b": entity_b,
                "findings": findings,
                "recommendations": recommendations,
                "suggestion_id": suggestion.suggestion_id,
            }

    def explain_concept(self, session_id: str, concept: str) -> Dict[str, Any]:
        """Explain a game development concept with a summary and examples."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"success": False, "error": "Session not found."}
            concept_lower = concept.lower().strip()
            knowledge: List[Tuple[List[str], str, str, List[str]]] = [
                (["coyote time", "coyote"], "Coyote Time",
                 "A small grace period after walking off a ledge during which the player can still jump.",
                 ["Platformers like Celeste and Hollow Knight use coyote time for forgiving jumps.",
                  "Typically implemented as a 0.1-0.2 second timer after leaving ground."]),
                (["input buffer", "buffer"], "Input Buffering",
                 "Storing player inputs for a short time so they execute when the next valid action window opens.",
                 ["Pressing jump slightly before landing will queue the jump for the next frame.",
                  "Improves game feel by compensating for human timing imprecision."]),
                (["hitbox", "hurtbox"], "Hitbox and Hurtbox",
                 "Hitboxes detect when an attack connects; hurtboxes define where a character can be hit.",
                 ["Separating hit and hurt boxes allows fine control over combat reach and vulnerability.",
                  "Inactive hurtboxes during certain frames create invincibility windows (i-frames)."]),
                (["state machine", "fsm"], "Finite State Machine",
                 "A pattern where an entity exists in one state at a time and transitions based on events.",
                 ["A player character may be in Idle, Run, Jump, or Attack states.",
                  "Each state has its own update logic and valid transitions."]),
                (["object pooling", "pooling"], "Object Pooling",
                 "Reusing pre-allocated objects instead of creating and destroying them at runtime.",
                 ["Critical for particle systems and projectiles to avoid garbage collection spikes.",
                  "Objects are deactivated and returned to a pool rather than destroyed."]),
                (["lerp", "interpolation", "linear interpolation"], "Linear Interpolation (Lerp)",
                 "Blending between two values by a parameter t in the range [0, 1].",
                 ["Used for smooth camera movement, color transitions, and UI animations.",
                  "Lerp(a, b, t) = a + (b - a) * t."]),
                (["delta time", "deltatime", "frame independent"], "Delta Time",
                 "The time elapsed since the last frame, used to make motion frame-rate independent.",
                 ["Multiply velocities by delta time so movement is consistent across frame rates.",
                  "Essential for physics and animation that must behave identically on all hardware."]),
                (["navmesh", "navigation mesh"], "Navigation Mesh",
                 "A simplified polygonal mesh defining walkable areas for AI pathfinding.",
                 ["Agents pathfind across the mesh rather than pixel-by-pixel.",
                  "Generated from collision geometry with off-mesh links for jumps and drops."]),
            ]
            summary = ""
            details = ""
            examples: List[str] = []
            for keywords, title, desc, exs in knowledge:
                if any(k in concept_lower for k in keywords):
                    summary = title
                    details = desc
                    examples = exs
                    break
            if not summary:
                summary = concept[:60]
                details = (f"The concept '{concept}' is not in the built-in knowledge base. "
                           "Consider searching the web or consulting project documentation for details.")
                examples = ["Document the concept in your project wiki for future reference."]
            guidance = GuidanceResult(
                guidance_id=_new_id("guide"),
                guidance_kind=GuidanceKind.TUTORIAL.value,
                topic=summary,
                summary=summary,
                details=details,
                examples=examples,
                related_concepts=[],
            )
            session.guidance.append(guidance)
            session.updated_at = _now()
            self._emit("concept_explained", session_id=session_id, topic=summary)
            return {
                "success": True,
                "topic": summary,
                "summary": details,
                "examples": examples,
                "guidance_id": guidance.guidance_id,
            }

    def search_knowledge(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search the built-in knowledge base for matching concepts."""
        if not query or not query.strip():
            return []
        query_lower = query.lower()
        results: List[Dict[str, Any]] = []
        knowledge_entries: List[Tuple[str, str, List[str]]] = [
            ("Coyote Time", "Grace period for jumping after leaving a ledge.",
             ["coyote", "jump", "platformer", "ledge", "grace"]),
            ("Input Buffering", "Queuing inputs to execute on the next valid frame.",
             ["input", "buffer", "queue", "frame", "timing"]),
            ("Hitbox and Hurtbox", "Collision volumes for attacks and vulnerability.",
             ["hitbox", "hurtbox", "combat", "collision", "attack"]),
            ("Finite State Machine", "Pattern for entity behavior with discrete states.",
             ["fsm", "state", "machine", "behavior", "transition"]),
            ("Object Pooling", "Reusing objects to avoid allocation overhead.",
             ["pool", "object", "memory", "allocation", "performance"]),
            ("Linear Interpolation", "Blending between two values by a parameter.",
             ["lerp", "interpolation", "blend", "smooth", "animation"]),
            ("Delta Time", "Frame-independent time step for motion.",
             ["delta", "time", "frame", "independent", "physics"]),
            ("Navigation Mesh", "Walkable area representation for AI pathfinding.",
             ["navmesh", "navigation", "pathfinding", "ai", "walkable"]),
            ("State-Driven Animation", "Animation tied to logical entity states.",
             ["animation", "state", "sprite", "blend", "transition"]),
            ("Component Architecture", "Composing entities from reusable components.",
             ["component", "entity", "architecture", "ecs", "composition"]),
            ("Behavior Tree", "Hierarchical AI decision structure.",
             ["behavior", "tree", "ai", "decision", "node"]),
            ("Sensor Fusion", "Combining multiple input signals for robust detection.",
             ["sensor", "fusion", "input", "detection", "signal"]),
        ]
        for title, desc, keywords in knowledge_entries:
            score = 0
            if query_lower in title.lower():
                score += 3
            if query_lower in desc.lower():
                score += 2
            for kw in keywords:
                if kw in query_lower:
                    score += 1
            if score > 0:
                results.append({
                    "title": title,
                    "description": desc,
                    "keywords": keywords,
                    "score": score,
                })
        results.sort(key=lambda r: r["score"], reverse=True)
        n = max(1, min(int(limit), len(results)))
        return results[:n]

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recent copilot events."""
        with self._lock:
            n = max(1, min(int(limit), len(self._events)))
            return list(self._events[-n:])

    # ------------------------------------------------------------------
    # AI methods
    # ------------------------------------------------------------------

    def ai_respond(self, session_id: str, user_message: str) -> str:
        """Generate a natural-language response to a user message."""
        msg_lower = user_message.lower()
        session = self._sessions.get(session_id)
        ctx = session.context if session else DesignContext()
        # Match common question patterns
        if any(w in msg_lower for w in ["hello", "hi ", "hey", "greetings"]):
            return (f"Hello! I am the SparkLabs design copilot. I can help with "
                    f"level design, gameplay mechanics, balance, and more for "
                    f"your {ctx.genre or 'game'} project. What would you like to explore?")
        if any(w in msg_lower for w in ["how do i", "how to", "what is", "what are", "explain"]):
            # Delegate to explain_concept if we can identify a concept
            concept = user_message
            for prefix in ("how do i ", "how to ", "what is ", "what are ", "explain "):
                if msg_lower.startswith(prefix):
                    concept = user_message[len(prefix):]
                    break
            result = self.explain_concept(session_id, concept)
            if result.get("success"):
                return f"{result['topic']}: {result['summary']}"
            return "I can explain that concept. Let me look it up for you."
        if any(w in msg_lower for w in ["balance", "overpowered", "op ", "weak", "strong"]):
            return ("For balance questions, I recommend using the review_balance tool "
                    "with explicit stat dictionaries. Define health, damage, speed, "
                    "and cooldown for each entity, and I can quantify the disparities "
                    "and suggest adjustments.")
        if any(w in msg_lower for w in ["idea", "suggest", "brainstorm", "inspiration"]):
            ideas = self.generate_ideas(session_id, user_message, count=3)
            if ideas:
                lines = [f"- {i['title']}: {i['description']}" for i in ideas]
                return "Here are some ideas:\n" + "\n".join(lines)
            return "I can generate ideas once you tell me the topic you want to explore."
        if any(w in msg_lower for w in ["level", "stage", "map", "design"]):
            return ("For level design, focus on pacing: alternate tension and release, "
                    "teach mechanics through gameplay, and place save points after "
                    "significant challenges. Would you like me to analyze a specific "
                    "level description?")
        if any(w in msg_lower for w in ["combat", "fight", "enemy", "boss"]):
            return ("For combat design, define clear roles for each entity, ensure "
                    "telegraphed attacks, and tune damage-to-health ratios. Consider "
                    "adding weak points to bosses. Want me to review specific combat stats?")
        if any(w in msg_lower for w in ["performance", "optimization", "fps", "lag", "slow"]):
            return ("Common performance wins: use object pooling for projectiles and "
                    "particles, batch draw calls, simplify collision shapes, and "
                    "level-of-detail (LOD) your meshes. Profile before optimizing.")
        if any(w in msg_lower for w in ["narrative", "story", "plot", "character", "dialogue"]):
            return ("For narrative design, define your protagonist's arc, establish "
                    "stakes early, and ensure player agency in key decisions. "
                    "Consider branching dialogue that reflects world state.")
        if any(w in msg_lower for w in ["audio", "music", "sound", "sfx"]):
            return ("For audio, layer your mix into buses (master, music, sfx, dialogue, "
                    "ambient, ui). Duck music during dialogue, add reverb to ambient "
                    "for spatial depth, and use a limiter on the master bus.")
        # Default response
        return (f"I understand you are asking about: \"{user_message[:80]}\". "
                f"Based on your {ctx.genre or 'game'} project, I recommend breaking "
                f"the problem into smaller parts, prototyping the core interaction, "
                f"and playtesting with your target audience. Would you like specific "
                f"suggestions or a design analysis?")

    def ai_suggest_design(self, session_id: str, description: str) -> List[Dict[str, Any]]:
        """Suggest design improvements based on a description."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return []
            desc_lower = description.lower()
            suggestions: List[Dict[str, Any]] = []
            design_map: List[Tuple[List[str], SuggestionType, str, str, List[str]]] = [
                (["empty", "sparse", "barren", "blank"],
                 SuggestionType.DESIGN, "Add Environmental Detail",
                 "The described area feels sparse. Add props, foliage, and lighting variation to create visual interest.",
                 ["Place clusters of props near paths to guide the player.",
                  "Add ambient particle effects like dust or fireflies.",
                  "Vary lighting intensity to create focal points."]),
                (["confusing", "lost", "unclear", "maze"],
                 SuggestionType.DESIGN, "Improve Wayfinding",
                 "Players may get lost. Add landmarks, signposting, and clear sightlines.",
                 ["Place a distinctive landmark visible from multiple angles.",
                  "Use lighting to highlight the critical path.",
                  "Add environmental cues like footprints or arrows."]),
                (["difficult", "hard", "frustrating", "unfair"],
                 SuggestionType.BALANCE, "Smooth Difficulty Curve",
                 "The described section may be too difficult. Consider incremental challenge escalation.",
                 ["Add a safe zone before the challenging encounter.",
                  "Reduce enemy count or health by 20-30%.",
                  "Provide a checkpoint immediately before the challenge."]),
                (["boring", "repetitive", "tedious", "grind"],
                 SuggestionType.GAMEPLAY, "Add Variety",
                 "The described gameplay may feel repetitive. Introduce variety in encounters and rewards.",
                 ["Vary enemy compositions between encounters.",
                  "Add optional challenges with unique rewards.",
                  "Introduce a new mechanic every 5-10 minutes."]),
                (["slow", "laggy", "stutter", "frame"],
                 SuggestionType.TECHNICAL, "Optimize Performance",
                 "The described scene may have performance issues. Profile and optimize bottlenecks.",
                 ["Reduce draw calls by batching static geometry.",
                  "Use LOD meshes for distant objects.",
                  "Implement object pooling for frequently spawned entities."]),
            ]
            for keywords, stype, title, desc, steps in design_map:
                if any(w in desc_lower for w in keywords):
                    suggestion = SuggestionResult(
                        suggestion_id=_new_id("sug"),
                        suggestion_type=stype.value,
                        title=title,
                        description=desc,
                        priority="high" if stype == SuggestionType.TECHNICAL else "medium",
                        steps=steps,
                    )
                    session.suggestions.append(suggestion)
                    suggestions.append(suggestion.to_dict())
            if not suggestions:
                fallback = SuggestionResult(
                    suggestion_id=_new_id("sug"),
                    suggestion_type=SuggestionType.DESIGN.value,
                    title="Iterate and Playtest",
                    description="No specific issues detected. Continue iterating and playtesting.",
                    priority="low",
                    steps=["Playtest with 3-5 target-audience players.",
                           "Collect feedback on pacing, difficulty, and clarity.",
                           "Prioritize fixes based on frequency of feedback."],
                )
                session.suggestions.append(fallback)
                suggestions.append(fallback.to_dict())
            session.updated_at = _now()
            self._emit("ai_suggested_design", session_id=session_id, count=len(suggestions))
            return suggestions

    def ai_review_gameplay(self, session_id: str, description: str) -> Dict[str, Any]:
        """Review a gameplay description for fun, clarity, and balance."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"success": False, "error": "Session not found."}
            desc_lower = description.lower()
            fun_score = 5
            clarity_score = 5
            balance_score = 5
            notes: List[str] = []
            # Fun analysis
            if any(w in desc_lower for w in ["reward", "satisfying", "juicy", "feedback"]):
                fun_score = min(10, fun_score + 3)
                notes.append("Strong reward feedback detected, which boosts player engagement.")
            if any(w in desc_lower for w in ["variety", "choice", "options", "multiple"]):
                fun_score = min(10, fun_score + 2)
                notes.append("Player choice and variety increase long-term engagement.")
            if any(w in desc_lower for w in ["grind", "repetitive", "tedious"]):
                fun_score = max(1, fun_score - 3)
                notes.append("Repetitive elements may reduce enjoyment over time.")
            # Clarity analysis
            if any(w in desc_lower for w in ["tutorial", "guide", "explain", "clear"]):
                clarity_score = min(10, clarity_score + 3)
                notes.append("Explicit guidance helps players understand objectives.")
            if any(w in desc_lower for w in ["unclear", "confusing", "ambiguous", "hidden"]):
                clarity_score = max(1, clarity_score - 3)
                notes.append("Unclear objectives may frustrate players.")
            # Balance analysis
            if any(w in desc_lower for w in ["balanced", "fair", "symmetric"]):
                balance_score = min(10, balance_score + 3)
                notes.append("Explicit balance considerations improve competitive fairness.")
            if any(w in desc_lower for w in ["overpowered", "unfair", "one-sided", "dominant"]):
                balance_score = max(1, balance_score - 3)
                notes.append("Imbalance detected; review dominant strategies.")
            overall = round((fun_score + clarity_score + balance_score) / 3.0, 1)
            recommendation = "ship"
            if overall < 4.0:
                recommendation = "rework"
            elif overall < 6.5:
                recommendation = "iterate"
            suggestion = SuggestionResult(
                suggestion_id=_new_id("sug"),
                suggestion_type=SuggestionType.GAMEPLAY.value,
                title=f"Gameplay Review: {description[:40]}",
                description=f"Overall score: {overall}/10. Recommendation: {recommendation}.",
                priority="high" if recommendation == "rework" else "medium",
                steps=notes,
            )
            session.suggestions.append(suggestion)
            session.updated_at = _now()
            self._emit("ai_reviewed_gameplay", session_id=session_id,
                       overall=overall, recommendation=recommendation)
            return {
                "success": True,
                "fun_score": fun_score,
                "clarity_score": clarity_score,
                "balance_score": balance_score,
                "overall": overall,
                "recommendation": recommendation,
                "notes": notes,
                "suggestion_id": suggestion.suggestion_id,
            }


# ===========================================================================
# 7. Editor Subsystems System (singleton)
# ===========================================================================

class _EditorSubsystemsSystem:
    """Top-level singleton that owns and coordinates all editor subsystems.

    The system follows the same singleton pattern used across the
    SparkLabs engine: a class-level ``_init_lock`` guards creation
    via double-checked locking, and a ``_seeded`` flag ensures seed
    data is applied exactly once. Each subsystem receives a back
    reference to this system so it can publish cross-subsystem
    events when needed.
    """

    _instance: Optional["_EditorSubsystemsSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._seeded: bool = False
        self._config: Dict[str, Any] = {
            "auto_seed": True,
            "event_buffer_size": _MAX_EVENTS,
            "tick_interval_ms": 16,
        }
        self._events: List[Dict[str, Any]] = []
        self._event_counter: int = 0
        self._tick_count: int = 0
        self._last_tick_at: str = _now()
        # Subsystem instances
        self._material_editor: Optional[MaterialShaderGraphEditor] = None
        self._terrain_editor: Optional[TerrainSculptingEditor] = None
        self._particle_editor: Optional[ParticleEffectDesigner] = None
        self._visual_script_editor: Optional[VisualScriptNodeGraphEditor] = None
        self._audio_mixer: Optional[AudioMixerEditor] = None
        self._copilot_panel: Optional[CopilotConversationalPanel] = None
        self._initialize_subsystems()

    @classmethod
    def get_instance(cls) -> "_EditorSubsystemsSystem":
        """Return the singleton instance, creating it if necessary."""
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_subsystems(self) -> None:
        """Create all subsystem instances with a back-reference to this system."""
        with self._lock:
            self._material_editor = MaterialShaderGraphEditor(system=self)
            self._terrain_editor = TerrainSculptingEditor(system=self)
            self._particle_editor = ParticleEffectDesigner(system=self)
            self._visual_script_editor = VisualScriptNodeGraphEditor(system=self)
            self._audio_mixer = AudioMixerEditor(system=self)
            self._copilot_panel = CopilotConversationalPanel(system=self)
            self._seeded = True
            self._emit("system_initialized")

    def initialize(self) -> None:
        """Public initialization hook. Safe to call multiple times."""
        with self._lock:
            if self._seeded:
                return
            self._initialize_subsystems()

    # ------------------------------------------------------------------
    # Event bus
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, **data: Any) -> None:
        self._event_counter += 1
        self._events.append({
            "event_id": f"sys_evt_{self._event_counter:08d}",
            "timestamp": _now(),
            "event_type": event_type,
            "data": _to_jsonable(data),
        })
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Subsystem accessors
    # ------------------------------------------------------------------

    def get_material_editor(self) -> MaterialShaderGraphEditor:
        """Return the material/shader graph editor subsystem."""
        assert self._material_editor is not None, "Material editor not initialized"
        return self._material_editor

    def get_terrain_editor(self) -> TerrainSculptingEditor:
        """Return the terrain sculpting editor subsystem."""
        assert self._terrain_editor is not None, "Terrain editor not initialized"
        return self._terrain_editor

    def get_particle_editor(self) -> ParticleEffectDesigner:
        """Return the particle effect designer subsystem."""
        assert self._particle_editor is not None, "Particle editor not initialized"
        return self._particle_editor

    def get_visual_script_editor(self) -> VisualScriptNodeGraphEditor:
        """Return the visual script node graph editor subsystem."""
        assert self._visual_script_editor is not None, "Visual script editor not initialized"
        return self._visual_script_editor

    def get_audio_mixer(self) -> AudioMixerEditor:
        """Return the audio mixer editor subsystem."""
        assert self._audio_mixer is not None, "Audio mixer not initialized"
        return self._audio_mixer

    def get_copilot_panel(self) -> CopilotConversationalPanel:
        """Return the copilot conversational panel subsystem."""
        assert self._copilot_panel is not None, "Copilot panel not initialized"
        return self._copilot_panel

    # ------------------------------------------------------------------
    # System-level configuration and status
    # ------------------------------------------------------------------

    def get_config(self) -> Dict[str, Any]:
        """Return the current system configuration."""
        with self._lock:
            return dict(self._config)

    def set_config(self, **fields: Any) -> Dict[str, Any]:
        """Update system configuration fields and return the new config."""
        with self._lock:
            for key, value in fields.items():
                self._config[key] = _to_jsonable(value)
            self._emit("config_updated", fields=list(fields.keys()))
            return dict(self._config)

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the system status."""
        with self._lock:
            return {
                "seeded": self._seeded,
                "tick_count": self._tick_count,
                "last_tick_at": self._last_tick_at,
                "subsystems": {
                    "material_editor": self._material_editor is not None,
                    "terrain_editor": self._terrain_editor is not None,
                    "particle_editor": self._particle_editor is not None,
                    "visual_script_editor": self._visual_script_editor is not None,
                    "audio_mixer": self._audio_mixer is not None,
                    "copilot_panel": self._copilot_panel is not None,
                },
                "config": dict(self._config),
            }

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics across all subsystems."""
        with self._lock:
            stats: Dict[str, Any] = {
                "total_events": self._event_counter,
                "system_events": len(self._events),
                "tick_count": self._tick_count,
            }
            if self._material_editor is not None:
                stats["materials"] = len(self._material_editor._materials)
            if self._terrain_editor is not None:
                stats["terrains"] = len(self._terrain_editor._terrains) if hasattr(self._terrain_editor, "_terrains") else 0
            if self._particle_editor is not None:
                stats["particle_effects"] = len(self._particle_editor._effects) if hasattr(self._particle_editor, "_effects") else 0
            if self._visual_script_editor is not None:
                stats["script_graphs"] = len(self._visual_script_editor._graphs) if hasattr(self._visual_script_editor, "_graphs") else 0
            if self._audio_mixer is not None:
                stats["audio_buses"] = len(self._audio_mixer._buses)
                stats["sound_cues"] = len(self._audio_mixer._cues)
            if self._copilot_panel is not None:
                stats["copilot_sessions"] = len(self._copilot_panel._sessions)
            return stats

    def get_snapshot(self) -> Dict[str, Any]:
        """Return a full snapshot of all subsystem state."""
        with self._lock:
            snapshot: Dict[str, Any] = {
                "timestamp": _now(),
                "status": self.get_status(),
                "stats": self.get_stats(),
            }
            if self._material_editor is not None:
                raw = self._material_editor.list_materials() if hasattr(self._material_editor, "list_materials") else []
                snapshot["materials"] = [_to_jsonable(m) for m in raw]
            if self._terrain_editor is not None:
                raw = self._terrain_editor.list_terrains() if hasattr(self._terrain_editor, "list_terrains") else []
                snapshot["terrains"] = [_to_jsonable(t) for t in raw]
            if self._particle_editor is not None:
                raw = self._particle_editor.list_effects() if hasattr(self._particle_editor, "list_effects") else []
                snapshot["particle_effects"] = [_to_jsonable(e) for e in raw]
            if self._visual_script_editor is not None:
                raw = self._visual_script_editor.list_graphs() if hasattr(self._visual_script_editor, "list_graphs") else []
                snapshot["script_graphs"] = [_to_jsonable(g) for g in raw]
            if self._audio_mixer is not None:
                snapshot["audio_buses"] = self._audio_mixer.list_buses()
                snapshot["sound_cues"] = self._audio_mixer.list_cues()
            if self._copilot_panel is not None:
                snapshot["copilot_sessions"] = self._copilot_panel.list_sessions()
            return _to_jsonable(snapshot)

    def list_events(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Return the most recent system-level events."""
        with self._lock:
            n = max(1, min(int(limit), len(self._events)))
            return list(self._events[-n:])

    # ------------------------------------------------------------------
    # Tick and visualization
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.016) -> Dict[str, Any]:
        """Advance the system by one frame. Updates tick counters.

        This is a lightweight tick that updates counters and emits a
        tick event. Subsystems that require per-frame simulation (such
        as particle effects) can be advanced separately through their
        own simulate methods.
        """
        with self._lock:
            self._tick_count += 1
            self._last_tick_at = _now()
            dt = max(0.0, _safe_float(delta_time, 0.016))
            self._emit("tick", tick_count=self._tick_count, delta_time=dt)
            return {
                "tick_count": self._tick_count,
                "delta_time": dt,
                "timestamp": self._last_tick_at,
            }

    def get_visualization_data(self) -> Dict[str, Any]:
        """Return data suitable for rendering editor visualizations."""
        with self._lock:
            vis: Dict[str, Any] = {
                "timestamp": _now(),
                "tick_count": self._tick_count,
            }
            if self._audio_mixer is not None:
                vis["audio_levels"] = self._audio_mixer.get_levels()
            if self._material_editor is not None and hasattr(self._material_editor, "list_materials"):
                vis["material_count"] = len(self._material_editor.list_materials())
            if self._terrain_editor is not None and hasattr(self._terrain_editor, "list_terrains"):
                vis["terrain_count"] = len(self._terrain_editor.list_terrains())
            if self._particle_editor is not None and hasattr(self._particle_editor, "list_effects"):
                vis["particle_effect_count"] = len(self._particle_editor.list_effects())
            if self._visual_script_editor is not None and hasattr(self._visual_script_editor, "list_graphs"):
                vis["script_graph_count"] = len(self._visual_script_editor.list_graphs())
            if self._copilot_panel is not None:
                vis["copilot_session_count"] = len(self._copilot_panel.list_sessions())
            return vis

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Reset all subsystems to their initial seeded state.

        This recreates every subsystem, discarding all user-created
        content and restoring the canonical seed data.
        """
        with self._lock:
            self._material_editor = None
            self._terrain_editor = None
            self._particle_editor = None
            self._visual_script_editor = None
            self._audio_mixer = None
            self._copilot_panel = None
            self._events.clear()
            self._event_counter = 0
            self._tick_count = 0
            self._seeded = False
            self._initialize_subsystems()
            self._emit("system_reset")


# ---------------------------------------------------------------------------
# Module-level factory
# ---------------------------------------------------------------------------

def get_editor_subsystems() -> _EditorSubsystemsSystem:
    """Return the singleton :class:`_EditorSubsystemsSystem` instance.

    This is the primary entry point for consumers of the editor
    subsystems module. It uses double-checked locking to ensure
    thread-safe lazy initialization.
    """
    return _EditorSubsystemsSystem.get_instance()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

__all__ = [
    # System
    "get_editor_subsystems",
    "_EditorSubsystemsSystem",
    # Material shader graph editor
    "MaterialShaderGraphEditor",
    "ShaderNodeType",
    "MaterialBlendMode",
    "MaterialShadingModel",
    "ShaderNode",
    "ShaderConnection",
    "MaterialParameter",
    "MaterialInstance",
    "MaterialGraph",
    "ShaderCompilationResult",
    # Terrain sculpting editor
    "TerrainSculptingEditor",
    "BrushType",
    "TerrainLayerType",
    "TerrainLayer",
    "FoliagePatch",
    "TerrainBrush",
    "TerrainStroke",
    "TerrainData",
    # Particle effect designer
    "ParticleEffectDesigner",
    "EmitterShape",
    "ParticleModifierType",
    "ParticleBlendMode",
    "ParticleKeyframe",
    "ParticleCurve",
    "ParticleEmitter",
    "ParticleModifier",
    "ParticleEffect",
    # Visual script node graph editor
    "VisualScriptNodeGraphEditor",
    "NodeType",
    "PinType",
    "ScriptPin",
    "ScriptConnection",
    "ScriptNode",
    "ScriptVariable",
    "ScriptFunction",
    "ScriptGraph",
    # Audio mixer editor
    "AudioMixerEditor",
    "AudioEffectType",
    "AudioBusType",
    "AudioEffect",
    "AudioChannel",
    "AudioBus",
    "SoundCue",
    "AudioMixPreset",
    # Copilot conversational panel
    "CopilotConversationalPanel",
    "MessageType",
    "SuggestionType",
    "GuidanceKind",
    "ConversationMessage",
    "DesignContext",
    "SuggestionResult",
    "GuidanceResult",
    "CopilotSession",
]