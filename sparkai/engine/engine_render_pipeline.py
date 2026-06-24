"""
SparkLabs Engine - Render Pipeline

Complete rendering pipeline for the SparkLabs AI-native game engine.
Orchestrates multi-pass rendering, material management, shader compilation,
draw call queuing, scene lighting, and post-processing effects for both
2D and 3D rendering.

Architecture:
  RenderPipeline (Singleton)
    |-- MaterialLibrary    — material definitions, instances, and caching
    |-- ShaderCompiler     — shader source management, compilation, and hot-reload
    |-- RenderQueue        — draw call sorting, batching, and LOD selection
    |-- LightManager       — scene lights, shadow maps, and light probes
    |-- PostProcessStack   — screen-space effect chain with quality presets
    |-- RenderPass         — individual render pass configuration
    |-- FrameTracker       — per-frame statistics and profiling

Render Pass Types:
  FORWARD    — standard forward rendering pass
  DEFERRED   — deferred shading G-buffer pass
  SHADOW     — shadow map generation pass
  POST       — post-processing compositing pass
  UI         — screen-space user interface pass
  SKYBOX     — skybox and environment pass
  CUSTOM     — user-defined rendering pass

Pass Execution Order:
  1. Shadow map passes (per-light shadow atlases)
  2. Skybox pass (background rendering)
  3. Deferred G-buffer pass (albedo, normal, depth, material)
  4. Forward pass (transparent, unlit, particles)
  5. Post-process pass (bloom, DOF, SSAO, tonemapping)
  6. UI pass (HUD, menus, overlays)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class RenderPassType(Enum):
    """Render pass classification for pipeline ordering."""
    FORWARD = "forward"
    DEFERRED = "deferred"
    SHADOW = "shadow"
    POST = "post"
    UI = "ui"
    SKYBOX = "skybox"
    CUSTOM = "custom"


class MaterialCategory(Enum):
    """Material classification for shader and pipeline selection."""
    PBR = "pbr"
    UNLIT = "unlit"
    TRANSPARENT = "transparent"
    PARTICLE = "particle"
    UI = "ui"
    TERRAIN = "terrain"
    FOLIAGE = "foliage"
    SKIN = "skin"
    WATER = "water"


class MaterialPropertyType(Enum):
    """Data type for material property values."""
    FLOAT = "float"
    FLOAT2 = "float2"
    FLOAT3 = "float3"
    FLOAT4 = "float4"
    COLOR = "color"
    TEXTURE = "texture"
    INTEGER = "integer"
    BOOLEAN = "boolean"


class ShaderStage(Enum):
    """Shader pipeline stages."""
    VERTEX = "vertex"
    FRAGMENT = "fragment"
    GEOMETRY = "geometry"
    COMPUTE = "compute"
    TESSELLATION_CONTROL = "tessellation_control"
    TESSELLATION_EVALUATION = "tessellation_evaluation"


class ShaderVariant(Enum):
    """Quality and platform shader variants."""
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    QUALITY = "quality"
    CINEMATIC = "cinematic"


class ShaderTarget(Enum):
    """Target shading language for compilation."""
    GLSL = "glsl"
    HLSL = "hlsl"
    METAL = "metal"
    WGSL = "wgsl"
    SPIRV = "spirv"


class QueueBucket(Enum):
    """Render queue draw order buckets."""
    BACKGROUND = "background"
    OPAQUE = "opaque"
    ALPHA_TEST = "alpha_test"
    TRANSPARENT = "transparent"
    OVERLAY = "overlay"
    UI = "ui"


class SortMode(Enum):
    """Draw call sort strategies within a render queue."""
    FRONT_TO_BACK = "front_to_back"
    BACK_TO_FRONT = "back_to_front"
    MATERIAL = "material"
    TEXTURE = "texture"
    STATE_CHANGE = "state_change"
    NONE = "none"


class LightKind(Enum):
    """Scene light source types."""
    DIRECTIONAL = "directional"
    POINT = "point"
    SPOT = "spot"
    AREA = "area"


class ShadowMapResolution(Enum):
    """Shadow map resolution presets."""
    LOW_256 = "256"
    MEDIUM_512 = "512"
    HIGH_1024 = "1024"
    ULTRA_2048 = "2048"
    EXTREME_4096 = "4096"


class PostEffectKind(Enum):
    """Screen-space post-processing effect types."""
    BLOOM = "bloom"
    DEPTH_OF_FIELD = "depth_of_field"
    MOTION_BLUR = "motion_blur"
    COLOR_GRADING = "color_grading"
    VIGNETTE = "vignette"
    SSAO = "ssao"
    SSR = "ssr"
    TONEMAPPING = "tonemapping"
    SHARPEN = "sharpen"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    FILM_GRAIN = "film_grain"
    LENS_FLARE = "lens_flare"


class QualityTier(Enum):
    """Global quality presets for the render pipeline."""
    PERFORMANCE = "performance"
    BALANCED = "balanced"
    QUALITY = "quality"
    CINEMATIC = "cinematic"


class CullingMode(Enum):
    """Culling strategy for draw commands."""
    NONE = "none"
    FRUSTUM = "frustum"
    OCCLUSION = "occlusion"
    DISTANCE = "distance"


class BlendOperation(Enum):
    """Framebuffer blend operations."""
    NONE = "none"
    ALPHA = "alpha"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"
    PREMULTIPLIED = "premultiplied"


# =============================================================================
# Internal General-Purpose Helpers
# =============================================================================


def _uid() -> str:
    """Generate a unique identifier string."""
    return uuid.uuid4().hex


def _now() -> float:
    """Return the current time as a float."""
    return _time_module.time()


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp a float value to the range [lo, hi]."""
    return max(lo, min(hi, value))


# =============================================================================
# Data Classes — Render Pass
# =============================================================================


@dataclass
class RenderPass:
    """Configuration for a single render pass in the pipeline.

    Each pass represents a distinct rendering stage with its own render
    target, clear settings, culling mode, blend operation, and execution
    ordering within the pipeline.
    """

    pass_id: str = field(default_factory=_uid)
    pass_type: RenderPassType = RenderPassType.FORWARD
    name: str = ""
    order: int = 0
    enabled: bool = True
    clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    clear_depth: bool = True
    clear_stencil: bool = False
    blend: BlendOperation = BlendOperation.NONE
    culling: CullingMode = CullingMode.FRUSTUM
    target_width: int = 1920
    target_height: int = 1080
    samples: int = 1
    draw_commands: int = 0
    triangles_submitted: int = 0
    execution_us: float = 0.0
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pass_id": self.pass_id,
            "pass_type": self.pass_type.value,
            "name": self.name,
            "order": self.order,
            "enabled": self.enabled,
            "clear_color": list(self.clear_color),
            "clear_depth": self.clear_depth,
            "clear_stencil": self.clear_stencil,
            "blend": self.blend.value,
            "culling": self.culling.value,
            "resolution": f"{self.target_width}x{self.target_height}",
            "samples": self.samples,
            "draw_commands": self.draw_commands,
            "triangles_submitted": self.triangles_submitted,
            "execution_us": self.execution_us,
            "dependencies": list(self.dependencies),
        }


# =============================================================================
# Data Classes — Material System
# =============================================================================


@dataclass
class MaterialProperty:
    """A single named property within a material definition.

    Properties are typed (float, color, texture, vector) and can carry
    default values, metadata constraints, and optional texture references.
    """

    name: str = ""
    prop_type: MaterialPropertyType = MaterialPropertyType.FLOAT
    default_float: float = 0.0
    default_color: Tuple[float, float, float, float] = (1.0, 1.0, 1.0, 1.0)
    default_texture: str = ""
    default_vector: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 0.0)
    default_int: int = 0
    default_bool: bool = False
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "prop_type": self.prop_type.value,
            "default_float": self.default_float,
            "default_color": list(self.default_color),
            "default_texture": self.default_texture,
            "default_vector": list(self.default_vector),
            "default_int": self.default_int,
            "default_bool": self.default_bool,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "description": self.description,
        }


@dataclass
class MaterialDefinition:
    """A named material template defining shader, textures, and properties.

    Material definitions serve as the blueprint for material instances.
    Each definition is associated with a shader program, a material
    category, and a set of typed properties with default values.
    """

    material_id: str = field(default_factory=_uid)
    name: str = ""
    category: MaterialCategory = MaterialCategory.PBR
    shader_name: str = ""
    textures: Dict[str, str] = field(default_factory=dict)
    properties: Dict[str, MaterialProperty] = field(default_factory=dict)
    blend: BlendOperation = BlendOperation.ALPHA
    two_sided: bool = False
    receive_shadows: bool = True
    cast_shadows: bool = True
    render_queue: QueueBucket = QueueBucket.OPAQUE
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "material_id": self.material_id,
            "name": self.name,
            "category": self.category.value,
            "shader_name": self.shader_name,
            "textures": dict(self.textures),
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "blend": self.blend.value,
            "two_sided": self.two_sided,
            "receive_shadows": self.receive_shadows,
            "cast_shadows": self.cast_shadows,
            "render_queue": self.render_queue.value,
            "created_at": self.created_at,
        }


@dataclass
class MaterialInstance:
    """A runtime instance of a material definition with parameter overrides.

    Each instance references a parent material definition and can override
    any subset of its properties. Instances are used for per-object material
    customization without duplicating full material data.
    """

    instance_id: str = field(default_factory=_uid)
    definition_id: str = ""
    name: str = ""
    property_overrides: Dict[str, Any] = field(default_factory=dict)
    texture_overrides: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "definition_id": self.definition_id,
            "name": self.name,
            "property_overrides": dict(self.property_overrides),
            "texture_overrides": dict(self.texture_overrides),
            "enabled": self.enabled,
            "created_at": self.created_at,
        }


# =============================================================================
# Data Classes — Shader System
# =============================================================================


@dataclass
class ShaderSource:
    """Raw shader source code with metadata.

    Each shader source is associated with a specific pipeline stage,
    a set of quality variants, and a target language. The source
    can be compiled to multiple variants and targets.
    """

    shader_id: str = field(default_factory=_uid)
    name: str = ""
    stage: ShaderStage = ShaderStage.FRAGMENT
    source_code: str = ""
    target: ShaderTarget = ShaderTarget.GLSL
    variants: List[ShaderVariant] = field(default_factory=list)
    defines: Dict[str, str] = field(default_factory=dict)
    includes: List[str] = field(default_factory=list)
    entry_point: str = "main"
    file_path: str = ""
    last_modified: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shader_id": self.shader_id,
            "name": self.name,
            "stage": self.stage.value,
            "source_code_length": len(self.source_code),
            "target": self.target.value,
            "variants": [v.value for v in self.variants],
            "defines": dict(self.defines),
            "includes": list(self.includes),
            "entry_point": self.entry_point,
            "file_path": self.file_path,
            "last_modified": self.last_modified,
        }


@dataclass
class CompiledShader:
    """A compiled shader object ready for GPU submission.

    Stores the compiled binary or bytecode, compilation metadata,
    and the source reference. Tracks compilation time and errors
    for debugging and hot-reload flows.
    """

    compiled_id: str = field(default_factory=_uid)
    shader_id: str = ""
    variant: ShaderVariant = ShaderVariant.BALANCED
    target: ShaderTarget = ShaderTarget.GLSL
    compiled_code: str = ""
    compilation_time_ms: float = 0.0
    compile_success: bool = True
    compile_errors: List[str] = field(default_factory=list)
    compile_warnings: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compiled_id": self.compiled_id,
            "shader_id": self.shader_id,
            "variant": self.variant.value,
            "target": self.target.value,
            "compiled_code_length": len(self.compiled_code),
            "compilation_time_ms": self.compilation_time_ms,
            "compile_success": self.compile_success,
            "compile_errors": list(self.compile_errors),
            "compile_warnings": list(self.compile_warnings),
            "created_at": self.created_at,
        }


# =============================================================================
# Data Classes — Render Queue
# =============================================================================


@dataclass
class DrawCommand:
    """A single draw call within the render queue.

    Encapsulates all state needed to issue a GPU draw call: mesh reference,
    material instance, transform matrix, sort key for ordering, and
    optional LOD level and instance count for instanced drawing.
    """

    command_id: str = field(default_factory=_uid)
    mesh_id: str = ""
    material_instance_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    sort_key: float = 0.0
    bucket: QueueBucket = QueueBucket.OPAQUE
    priority: int = 0
    lod_level: int = 0
    instance_count: int = 1
    bounding_radius: float = 1.0
    visible: bool = True
    layer_mask: int = 0xFFFFFFFF
    user_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "mesh_id": self.mesh_id,
            "material_instance_id": self.material_instance_id,
            "position": list(self.position),
            "rotation": list(self.rotation),
            "scale": list(self.scale),
            "sort_key": self.sort_key,
            "bucket": self.bucket.value,
            "priority": self.priority,
            "lod_level": self.lod_level,
            "instance_count": self.instance_count,
            "bounding_radius": self.bounding_radius,
            "visible": self.visible,
            "layer_mask": self.layer_mask,
        }


@dataclass
class RenderBatch:
    """A merged group of draw commands sharing material and state.

    Batching reduces GPU state changes by grouping commands that use
    the same material, mesh, and render state. The batch tracks the
    number of commands merged, total triangles, and state savings.
    """

    batch_id: str = field(default_factory=_uid)
    material_instance_id: str = ""
    mesh_id: str = ""
    command_ids: List[str] = field(default_factory=list)
    command_count: int = 0
    total_triangles: int = 0
    instance_count: int = 0
    state_changes_saved: int = 0
    bucket: QueueBucket = QueueBucket.OPAQUE
    sort_key: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "material_instance_id": self.material_instance_id,
            "mesh_id": self.mesh_id,
            "command_ids": list(self.command_ids),
            "command_count": self.command_count,
            "total_triangles": self.total_triangles,
            "instance_count": self.instance_count,
            "state_changes_saved": self.state_changes_saved,
            "bucket": self.bucket.value,
            "sort_key": self.sort_key,
        }


# =============================================================================
# Data Classes — Lighting
# =============================================================================


@dataclass
class SceneLight:
    """A light source in the scene with shadow configuration.

    Supports directional, point, spot, and area light types. Each light
    can be configured for shadow casting with a shadow map resolution
    preset, bias values, and softness parameters.
    """

    light_id: str = field(default_factory=_uid)
    name: str = ""
    kind: LightKind = LightKind.POINT
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    intensity: float = 1.0
    range: float = 10.0
    spot_angle: float = 45.0
    spot_inner_angle: float = 30.0
    direction: Tuple[float, float, float] = (0.0, 0.0, -1.0)
    area_width: float = 1.0
    area_height: float = 1.0
    casts_shadows: bool = False
    shadow_map_resolution: ShadowMapResolution = ShadowMapResolution.HIGH_1024
    shadow_bias: float = 0.005
    shadow_normal_bias: float = 0.02
    shadow_softness: float = 1.0
    shadow_near: float = 0.1
    shadow_far: float = 100.0
    enabled: bool = True
    importance: int = 0
    layer_mask: int = 0xFFFFFFFF
    created_at: float = field(default_factory=_now)

    @property
    def shadow_resolution_int(self) -> int:
        return int(self.shadow_map_resolution.value)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "light_id": self.light_id,
            "name": self.name,
            "kind": self.kind.value,
            "position": list(self.position),
            "color": list(self.color),
            "intensity": self.intensity,
            "range": self.range,
            "spot_angle": self.spot_angle,
            "spot_inner_angle": self.spot_inner_angle,
            "direction": list(self.direction),
            "area_width": self.area_width,
            "area_height": self.area_height,
            "casts_shadows": self.casts_shadows,
            "shadow_map_resolution": self.shadow_map_resolution.value,
            "shadow_bias": self.shadow_bias,
            "shadow_normal_bias": self.shadow_normal_bias,
            "shadow_softness": self.shadow_softness,
            "shadow_near": self.shadow_near,
            "shadow_far": self.shadow_far,
            "enabled": self.enabled,
            "importance": self.importance,
            "layer_mask": self.layer_mask,
            "created_at": self.created_at,
        }


@dataclass
class ShadowMap:
    """A shadow map resource associated with a scene light.

    Tracks the shadow map resolution, the owning light, cascade index
    (for directional lights), and the last update timestamp for
    incremental shadow map refresh strategies.
    """

    shadow_map_id: str = field(default_factory=_uid)
    light_id: str = ""
    resolution: int = 1024
    cascade_index: int = 0
    depth_bias: float = 0.005
    normal_bias: float = 0.02
    softness: float = 1.0
    last_updated: float = field(default_factory=_now)
    is_valid: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shadow_map_id": self.shadow_map_id,
            "light_id": self.light_id,
            "resolution": self.resolution,
            "cascade_index": self.cascade_index,
            "depth_bias": self.depth_bias,
            "normal_bias": self.normal_bias,
            "softness": self.softness,
            "last_updated": self.last_updated,
            "is_valid": self.is_valid,
        }


@dataclass
class LightProbe:
    """A light probe capturing spherical harmonics for indirect lighting.

    Light probes sample the irradiance environment at discrete positions
    in the scene. They store spherical harmonic coefficients (9 per color
    channel for 3rd-order SH), and are used to reconstruct ambient
    lighting for dynamic objects.
    """

    probe_id: str = field(default_factory=_uid)
    name: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    sh_coefficients: List[float] = field(default_factory=list)
    influence_radius: float = 5.0
    blend_distance: float = 1.0
    enabled: bool = True
    priority: int = 0
    last_updated: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "name": self.name,
            "position": list(self.position),
            "sh_coefficient_count": len(self.sh_coefficients),
            "influence_radius": self.influence_radius,
            "blend_distance": self.blend_distance,
            "enabled": self.enabled,
            "priority": self.priority,
            "last_updated": self.last_updated,
        }


# =============================================================================
# Data Classes — Post-Processing
# =============================================================================


@dataclass
class PostEffect:
    """A single post-processing effect with parameters and quality scaling.

    Each effect is assigned a priority for ordering within the chain,
    a set of adjustable parameters, and a quality tier that controls
    internal sample counts and precision. Effects can be toggled at
    runtime and track their own performance impact.
    """

    effect_id: str = field(default_factory=_uid)
    kind: PostEffectKind = PostEffectKind.BLOOM
    name: str = ""
    enabled: bool = True
    intensity: float = 1.0
    priority: int = 0
    quality: QualityTier = QualityTier.BALANCED
    parameters: Dict[str, Any] = field(default_factory=dict)
    average_execution_us: float = 0.0
    execution_count: int = 0
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "effect_id": self.effect_id,
            "kind": self.kind.value,
            "name": self.name,
            "enabled": self.enabled,
            "intensity": self.intensity,
            "priority": self.priority,
            "quality": self.quality.value,
            "parameters": dict(self.parameters),
            "average_execution_us": self.average_execution_us,
            "execution_count": self.execution_count,
            "created_at": self.created_at,
        }


# =============================================================================
# Data Classes — Frame Statistics
# =============================================================================


@dataclass
class FrameSnapshot:
    """Per-frame rendering statistics and metrics.

    Captures the complete rendering profile for a single frame: draw
    call counts, triangle throughput, batch savings, pass timings,
    and memory usage. Used for runtime profiling and auto-quality
    adjustment.
    """

    frame_id: int = 0
    timestamp: float = field(default_factory=_now)
    total_draw_commands: int = 0
    total_draw_batches: int = 0
    total_triangles: int = 0
    total_vertices: int = 0
    state_changes: int = 0
    state_changes_saved: int = 0
    culled_commands: int = 0
    visible_commands: int = 0
    frame_cpu_us: float = 0.0
    frame_gpu_us: float = 0.0
    pass_timings: Dict[str, float] = field(default_factory=dict)
    active_lights: int = 0
    shadow_maps_rendered: int = 0
    post_effects_applied: int = 0
    estimated_gpu_memory_mb: float = 0.0
    resolution_scale: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "total_draw_commands": self.total_draw_commands,
            "total_draw_batches": self.total_draw_batches,
            "total_triangles": self.total_triangles,
            "total_vertices": self.total_vertices,
            "state_changes": self.state_changes,
            "state_changes_saved": self.state_changes_saved,
            "culled_commands": self.culled_commands,
            "visible_commands": self.visible_commands,
            "frame_cpu_us": self.frame_cpu_us,
            "frame_gpu_us": self.frame_gpu_us,
            "pass_timings": dict(self.pass_timings),
            "active_lights": self.active_lights,
            "shadow_maps_rendered": self.shadow_maps_rendered,
            "post_effects_applied": self.post_effects_applied,
            "estimated_gpu_memory_mb": self.estimated_gpu_memory_mb,
            "resolution_scale": self.resolution_scale,
        }


# =============================================================================
# MaterialLibrary
# =============================================================================


class MaterialLibrary:
    """Material system managing definitions, instances, and caching.

    Maintains a registry of material definitions (templates) and their
    runtime instances. Supports material categories (PBR, unlit, transparent,
    particle, UI), property overrides on instances, and material caching
    for fast lookup.

    Each material definition specifies a shader, texture slots, typed
    properties, blend mode, and render queue bucket. Material instances
    reference a definition and override any subset of properties.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._definitions: Dict[str, MaterialDefinition] = OrderedDict()
        self._instances: Dict[str, MaterialInstance] = OrderedDict()
        self._definitions_by_name: Dict[str, str] = {}
        self._instance_cache: Dict[str, MaterialInstance] = OrderedDict()
        self._cache_max_size: int = 512
        self._stats: Dict[str, Any] = {
            "definitions_created": 0,
            "definitions_removed": 0,
            "instances_created": 0,
            "instances_removed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }

    # ---- Material Definitions ----

    def create_definition(
        self,
        name: str,
        category: MaterialCategory = MaterialCategory.PBR,
        shader_name: str = "",
        textures: Optional[Dict[str, str]] = None,
        properties: Optional[Dict[str, MaterialProperty]] = None,
        blend: BlendOperation = BlendOperation.ALPHA,
        two_sided: bool = False,
        receive_shadows: bool = True,
        cast_shadows: bool = True,
        render_queue: QueueBucket = QueueBucket.OPAQUE,
    ) -> MaterialDefinition:
        """Create a new material definition and register it."""
        with self._lock:
            definition = MaterialDefinition(
                name=name,
                category=category,
                shader_name=shader_name,
                textures=textures or {},
                properties=properties or {},
                blend=blend,
                two_sided=two_sided,
                receive_shadows=receive_shadows,
                cast_shadows=cast_shadows,
                render_queue=render_queue,
            )
            self._definitions[definition.material_id] = definition
            self._definitions_by_name[name] = definition.material_id
            self._stats["definitions_created"] += 1
            return definition

    def remove_definition(self, material_id: str) -> bool:
        """Remove a material definition by ID."""
        with self._lock:
            if material_id not in self._definitions:
                return False
            definition = self._definitions[material_id]
            if definition.name in self._definitions_by_name:
                del self._definitions_by_name[definition.name]
            del self._definitions[material_id]
            self._stats["definitions_removed"] += 1
            return True

    def get_definition(self, material_id: str) -> Optional[MaterialDefinition]:
        """Retrieve a material definition by ID."""
        with self._lock:
            return self._definitions.get(material_id)

    def get_definition_by_name(self, name: str) -> Optional[MaterialDefinition]:
        """Retrieve a material definition by name."""
        with self._lock:
            mid = self._definitions_by_name.get(name)
            if mid:
                return self._definitions.get(mid)
            return None

    def list_definitions(
        self, category: Optional[MaterialCategory] = None
    ) -> List[MaterialDefinition]:
        """List all material definitions, optionally filtered by category."""
        with self._lock:
            if category is None:
                return list(self._definitions.values())
            return [
                d for d in self._definitions.values()
                if d.category == category
            ]

    def add_property(
        self,
        material_id: str,
        name: str,
        prop_type: MaterialPropertyType,
        default_value: Any = None,
    ) -> Optional[MaterialProperty]:
        """Add a typed property to a material definition."""
        with self._lock:
            definition = self._definitions.get(material_id)
            if definition is None:
                return None
            prop = MaterialProperty(name=name, prop_type=prop_type)
            if default_value is not None:
                if prop_type == MaterialPropertyType.FLOAT:
                    prop.default_float = float(default_value)
                elif prop_type == MaterialPropertyType.COLOR:
                    prop.default_color = tuple(default_value)
                elif prop_type == MaterialPropertyType.TEXTURE:
                    prop.default_texture = str(default_value)
                elif prop_type == MaterialPropertyType.INTEGER:
                    prop.default_int = int(default_value)
                elif prop_type == MaterialPropertyType.BOOLEAN:
                    prop.default_bool = bool(default_value)
                else:
                    prop.default_vector = tuple(default_value)
            definition.properties[name] = prop
            return prop

    # ---- Material Instances ----

    def create_instance(
        self,
        definition_id: str,
        name: str = "",
        property_overrides: Optional[Dict[str, Any]] = None,
        texture_overrides: Optional[Dict[str, str]] = None,
    ) -> Optional[MaterialInstance]:
        """Create a new material instance from a definition with overrides."""
        with self._lock:
            if definition_id not in self._definitions:
                return None
            instance = MaterialInstance(
                definition_id=definition_id,
                name=name,
                property_overrides=property_overrides or {},
                texture_overrides=texture_overrides or {},
            )
            self._instances[instance.instance_id] = instance
            self._stats["instances_created"] += 1
            return instance

    def remove_instance(self, instance_id: str) -> bool:
        """Remove a material instance by ID."""
        with self._lock:
            if instance_id not in self._instances:
                return False
            del self._instances[instance_id]
            self._instance_cache.pop(instance_id, None)
            self._stats["instances_removed"] += 1
            return True

    def get_instance(self, instance_id: str) -> Optional[MaterialInstance]:
        """Retrieve a material instance, checking the cache first."""
        with self._lock:
            if instance_id in self._instance_cache:
                self._stats["cache_hits"] += 1
                return self._instance_cache[instance_id]
            self._stats["cache_misses"] += 1
            instance = self._instances.get(instance_id)
            if instance is not None:
                self._cache_instance(instance)
            return instance

    def update_instance_overrides(
        self,
        instance_id: str,
        property_overrides: Optional[Dict[str, Any]] = None,
        texture_overrides: Optional[Dict[str, str]] = None,
    ) -> Optional[MaterialInstance]:
        """Update property and texture overrides on a material instance."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return None
            if property_overrides is not None:
                instance.property_overrides.update(property_overrides)
            if texture_overrides is not None:
                instance.texture_overrides.update(texture_overrides)
            self._instance_cache.pop(instance_id, None)
            return instance

    def resolve_property(
        self, instance_id: str, property_name: str
    ) -> Optional[Any]:
        """Resolve a property value by checking instance overrides, then the definition default."""
        with self._lock:
            instance = self._instances.get(instance_id)
            if instance is None:
                return None
            if property_name in instance.property_overrides:
                return instance.property_overrides[property_name]
            definition = self._definitions.get(instance.definition_id)
            if definition is None:
                return None
            prop = definition.properties.get(property_name)
            if prop is None:
                return None
            if prop.prop_type == MaterialPropertyType.FLOAT:
                return prop.default_float
            elif prop.prop_type == MaterialPropertyType.COLOR:
                return prop.default_color
            elif prop.prop_type == MaterialPropertyType.TEXTURE:
                return prop.default_texture
            elif prop.prop_type == MaterialPropertyType.INTEGER:
                return prop.default_int
            elif prop.prop_type == MaterialPropertyType.BOOLEAN:
                return prop.default_bool
            else:
                return prop.default_vector

    def _cache_instance(self, instance: MaterialInstance) -> None:
        """Cache a material instance, evicting old entries if needed."""
        self._instance_cache[instance.instance_id] = instance
        while len(self._instance_cache) > self._cache_max_size:
            self._instance_cache.popitem(last=False)

    def set_cache_size(self, size: int) -> None:
        """Set the maximum material instance cache size."""
        with self._lock:
            self._cache_max_size = max(16, size)

    def get_stats(self) -> Dict[str, Any]:
        """Get material library statistics."""
        with self._lock:
            category_counts: Dict[str, int] = {}
            for d in self._definitions.values():
                cat = d.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
            return {
                "definitions": len(self._definitions),
                "instances": len(self._instances),
                "cache_size": len(self._instance_cache),
                "cache_max_size": self._cache_max_size,
                "category_distribution": category_counts,
                "definitions_created": self._stats["definitions_created"],
                "definitions_removed": self._stats["definitions_removed"],
                "instances_created": self._stats["instances_created"],
                "instances_removed": self._stats["instances_removed"],
                "cache_hits": self._stats["cache_hits"],
                "cache_misses": self._stats["cache_misses"],
            }

    def reset(self) -> None:
        """Reset the material library to initial state."""
        with self._lock:
            self._definitions.clear()
            self._instances.clear()
            self._definitions_by_name.clear()
            self._instance_cache.clear()
            self._stats = {
                "definitions_created": 0,
                "definitions_removed": 0,
                "instances_created": 0,
                "instances_removed": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }


# =============================================================================
# ShaderCompiler
# =============================================================================

# Built-in shader library names
_BUILTIN_SHADERS: Dict[str, Dict[str, str]] = {
    "standard": {
        "vertex": "// Standard vertex shader\nvoid main() { gl_Position = mvp * vec4(position, 1.0); }",
        "fragment": "// Standard fragment shader (PBR)\nvoid main() { outColor = vec4(baseColor.rgb, 1.0); }",
    },
    "sprite": {
        "vertex": "// Sprite vertex shader\nvoid main() { gl_Position = projection * modelView * vec4(position, 0.0, 1.0); }",
        "fragment": "// Sprite fragment shader\nvoid main() { outColor = texture(spriteTex, uv) * tintColor; }",
    },
    "particle": {
        "vertex": "// Particle vertex shader\nvoid main() { gl_Position = projection * view * model * vec4(position, 1.0); }",
        "fragment": "// Particle fragment shader\nvoid main() { outColor = texture(particleTex, uv) * particleColor; }",
    },
    "ui": {
        "vertex": "// UI vertex shader\nvoid main() { gl_Position = vec4(position.xy, 0.0, 1.0); }",
        "fragment": "// UI fragment shader\nvoid main() { outColor = texture(uiTex, uv) * uiColor; }",
    },
    "skybox": {
        "vertex": "// Skybox vertex shader\nvoid main() { gl_Position = projection * mat4(mat3(view)) * vec4(position, 1.0); }",
        "fragment": "// Skybox fragment shader\nvoid main() { outColor = texture(skyboxTex, direction); }",
    },
    "shadow_depth": {
        "vertex": "// Shadow depth vertex shader\nvoid main() { gl_Position = lightSpaceMatrix * model * vec4(position, 1.0); }",
        "fragment": "// Shadow depth fragment shader\nvoid main() { /* depth-only, no color output */ }",
    },
    "gbuffer": {
        "vertex": "// G-buffer vertex shader\nvoid main() { gl_Position = mvp * vec4(position, 1.0); }",
        "fragment": "// G-buffer fragment shader\nvoid main() { gAlbedo = vec4(baseColor.rgb, 1.0); gNormal = vec4(normal, 0.0); gMaterial = vec4(roughness, metallic, ao, 0.0); }",
    },
    "post_bloom": {
        "vertex": "// Bloom post-process vertex shader\nvoid main() { gl_Position = vec4(position.xy, 0.0, 1.0); }",
        "fragment": "// Bloom post-process fragment shader\nvoid main() { outColor = blurSample(bloomTex, uv, radius); }",
    },
    "post_tonemap": {
        "vertex": "// Tonemap vertex shader\nvoid main() { gl_Position = vec4(position.xy, 0.0, 1.0); }",
        "fragment": "// Tonemap fragment shader\nvoid main() { outColor = acesTonemap(texture(sceneTex, uv)); }",
    },
}


class ShaderCompiler:
    """Shader management system with compilation, caching, and hot-reload.

    Manages shader source code, compiles shaders to target languages,
    caches compiled output, supports quality variants, and provides
    hot-reload capability for iterative development. Includes a built-in
    shader library for standard, sprite, particle, UI, and skybox shaders.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._sources: Dict[str, ShaderSource] = OrderedDict()
        self._compiled: Dict[str, CompiledShader] = OrderedDict()
        self._sources_by_name: Dict[str, str] = {}
        self._hot_reload_callbacks: Dict[str, List[Callable[[str], None]]] = {}
        self._hot_reload_enabled: bool = False
        self._stats: Dict[str, Any] = {
            "sources_registered": 0,
            "sources_removed": 0,
            "compilations_performed": 0,
            "compilation_failures": 0,
            "compilation_total_ms": 0.0,
            "hot_reloads_triggered": 0,
            "cache_hits": 0,
            "cache_misses": 0,
        }
        self._register_builtin_shaders()

    def _register_builtin_shaders(self) -> None:
        """Register all built-in shader sources."""
        for name, stages in _BUILTIN_SHADERS.items():
            for stage_name, source_code in stages.items():
                stage = ShaderStage.FRAGMENT
                if stage_name == "vertex":
                    stage = ShaderStage.VERTEX
                elif stage_name == "fragment":
                    stage = ShaderStage.FRAGMENT
                elif stage_name == "geometry":
                    stage = ShaderStage.GEOMETRY
                elif stage_name == "compute":
                    stage = ShaderStage.COMPUTE
                shader_name = f"{name}_{stage_name}"
                source = ShaderSource(
                    name=shader_name,
                    stage=stage,
                    source_code=source_code,
                    variants=[ShaderVariant.PERFORMANCE, ShaderVariant.BALANCED,
                              ShaderVariant.QUALITY, ShaderVariant.CINEMATIC],
                )
                self._sources[source.shader_id] = source
                self._sources_by_name[shader_name] = source.shader_id
                self._stats["sources_registered"] += 1

    # ---- Shader Source Management ----

    def register_source(
        self,
        name: str,
        stage: ShaderStage,
        source_code: str,
        target: ShaderTarget = ShaderTarget.GLSL,
        variants: Optional[List[ShaderVariant]] = None,
        defines: Optional[Dict[str, str]] = None,
        includes: Optional[List[str]] = None,
        entry_point: str = "main",
        file_path: str = "",
    ) -> ShaderSource:
        """Register a new shader source for compilation."""
        with self._lock:
            source = ShaderSource(
                name=name,
                stage=stage,
                source_code=source_code,
                target=target,
                variants=variants or [ShaderVariant.BALANCED],
                defines=defines or {},
                includes=includes or [],
                entry_point=entry_point,
                file_path=file_path,
            )
            self._sources[source.shader_id] = source
            self._sources_by_name[name] = source.shader_id
            self._stats["sources_registered"] += 1
            return source

    def remove_source(self, shader_id: str) -> bool:
        """Remove a shader source and its compiled outputs."""
        with self._lock:
            if shader_id not in self._sources:
                return False
            source = self._sources[shader_id]
            if source.name in self._sources_by_name:
                del self._sources_by_name[source.name]
            del self._sources[shader_id]
            # Remove associated compiled shaders
            to_remove = [
                cid for cid, cs in self._compiled.items()
                if cs.shader_id == shader_id
            ]
            for cid in to_remove:
                del self._compiled[cid]
            self._stats["sources_removed"] += 1
            return True

    def update_source(
        self, shader_id: str, source_code: str
    ) -> Optional[ShaderSource]:
        """Update the source code of an existing shader, invalidating compiled output."""
        with self._lock:
            source = self._sources.get(shader_id)
            if source is None:
                return None
            source.source_code = source_code
            source.last_modified = _now()
            # Invalidate compiled shaders for this source
            to_remove = [
                cid for cid, cs in self._compiled.items()
                if cs.shader_id == shader_id
            ]
            for cid in to_remove:
                del self._compiled[cid]
            return source

    def get_source(self, shader_id: str) -> Optional[ShaderSource]:
        """Retrieve a shader source by ID."""
        with self._lock:
            return self._sources.get(shader_id)

    def get_source_by_name(self, name: str) -> Optional[ShaderSource]:
        """Retrieve a shader source by name."""
        with self._lock:
            sid = self._sources_by_name.get(name)
            if sid:
                return self._sources.get(sid)
            return None

    def list_sources(self) -> List[ShaderSource]:
        """List all registered shader sources."""
        with self._lock:
            return list(self._sources.values())

    # ---- Shader Compilation ----

    def compile(
        self,
        shader_id: str,
        variant: ShaderVariant = ShaderVariant.BALANCED,
        target: Optional[ShaderTarget] = None,
    ) -> Optional[CompiledShader]:
        """Compile a shader source for a specific variant and target.

        Checks the compilation cache first. Performs source preprocessing
        (define injection, include resolution), then simulates compilation
        to produce a CompiledShader. Tracks compilation time and errors.
        """
        cache_key = f"{shader_id}_{variant.value}_{(target or ShaderTarget.GLSL).value}"
        with self._lock:
            if cache_key in self._compiled:
                self._stats["cache_hits"] += 1
                return self._compiled[cache_key]
            self._stats["cache_misses"] += 1

            source = self._sources.get(shader_id)
            if source is None:
                return None

            resolved_target = target or source.target
            compile_start = _time_module.perf_counter()

            compile_errors: List[str] = []
            compile_warnings: List[str] = []

            try:
                # Preprocess: inject defines
                processed_code = source.source_code
                for define_key, define_val in source.defines.items():
                    processed_code = f"#define {define_key} {define_val}\n{processed_code}"

                # Preprocess: inject variant define
                processed_code = f"#define SHADER_VARIANT_{variant.value.upper()}\n{processed_code}"

                # Preprocess: include resolution (simulated)
                for include_path in source.includes:
                    processed_code = f"// @include: {include_path}\n{processed_code}"

                compile_success = bool(source.source_code.strip())
                if not compile_success:
                    compile_errors.append("Empty shader source code")

            except Exception as exc:
                compile_success = False
                compile_errors.append(str(exc))

            compile_end = _time_module.perf_counter()
            compilation_time_ms = (compile_end - compile_start) * 1000.0

            compiled = CompiledShader(
                shader_id=shader_id,
                variant=variant,
                target=resolved_target,
                compiled_code=processed_code if compile_success else "",
                compilation_time_ms=compilation_time_ms,
                compile_success=compile_success,
                compile_errors=compile_errors,
                compile_warnings=compile_warnings,
            )

            self._compiled[cache_key] = compiled
            self._stats["compilations_performed"] += 1
            self._stats["compilation_total_ms"] += compilation_time_ms
            if not compile_success:
                self._stats["compilation_failures"] += 1

            return compiled

    def get_compiled(
        self, shader_id: str, variant: ShaderVariant = ShaderVariant.BALANCED
    ) -> Optional[CompiledShader]:
        """Retrieve a compiled shader from the cache (no compilation)."""
        cache_key = f"{shader_id}_{variant.value}_{ShaderTarget.GLSL.value}"
        with self._lock:
            return self._compiled.get(cache_key)

    def compile_or_get(
        self, shader_id: str, variant: ShaderVariant = ShaderVariant.BALANCED
    ) -> Optional[CompiledShader]:
        """Get a compiled shader from cache, or compile it if not cached."""
        compiled = self.get_compiled(shader_id, variant)
        if compiled is not None:
            return compiled
        return self.compile(shader_id, variant)

    # ---- Hot Reload ----

    def enable_hot_reload(self) -> None:
        """Enable shader hot-reload monitoring."""
        with self._lock:
            self._hot_reload_enabled = True

    def disable_hot_reload(self) -> None:
        """Disable shader hot-reload monitoring."""
        with self._lock:
            self._hot_reload_enabled = False

    def is_hot_reload_enabled(self) -> bool:
        """Check if hot-reload is currently enabled."""
        with self._lock:
            return self._hot_reload_enabled

    def register_hot_reload_callback(
        self, shader_id: str, callback: Callable[[str], None]
    ) -> None:
        """Register a callback to be invoked when a shader is hot-reloaded."""
        with self._lock:
            if shader_id not in self._hot_reload_callbacks:
                self._hot_reload_callbacks[shader_id] = []
            self._hot_reload_callbacks[shader_id].append(callback)

    def unregister_hot_reload_callback(
        self, shader_id: str, callback: Callable[[str], None]
    ) -> None:
        """Remove a hot-reload callback for a shader."""
        with self._lock:
            if shader_id in self._hot_reload_callbacks:
                try:
                    self._hot_reload_callbacks[shader_id].remove(callback)
                except ValueError:
                    pass

    def trigger_hot_reload(self, shader_id: str) -> bool:
        """Trigger hot-reload for a shader, recompiling and notifying callbacks."""
        with self._lock:
            if not self._hot_reload_enabled:
                return False
            source = self._sources.get(shader_id)
            if source is None:
                return False
            # Invalidate and recompile all variants
            for variant in source.variants:
                cache_key = f"{shader_id}_{variant.value}_{source.target.value}"
                self._compiled.pop(cache_key, None)
                self.compile(shader_id, variant, source.target)
            self._stats["hot_reloads_triggered"] += 1
            # Notify callbacks
            for callback in self._hot_reload_callbacks.get(shader_id, []):
                try:
                    callback(shader_id)
                except Exception:
                    pass
            return True

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get shader compiler statistics."""
        with self._lock:
            total_compilations = self._stats["compilations_performed"]
            avg_compilation_ms = 0.0
            if total_compilations > 0:
                avg_compilation_ms = self._stats["compilation_total_ms"] / total_compilations
            stage_counts: Dict[str, int] = {}
            for s in self._sources.values():
                key = s.stage.value
                stage_counts[key] = stage_counts.get(key, 0) + 1
            return {
                "sources_registered": len(self._sources),
                "sources_removed": self._stats["sources_removed"],
                "compiled_shaders": len(self._compiled),
                "compilations_performed": total_compilations,
                "compilation_failures": self._stats["compilation_failures"],
                "avg_compilation_ms": round(avg_compilation_ms, 4),
                "compilation_total_ms": round(self._stats["compilation_total_ms"], 4),
                "hot_reloads_triggered": self._stats["hot_reloads_triggered"],
                "hot_reload_enabled": self._hot_reload_enabled,
                "cache_hits": self._stats["cache_hits"],
                "cache_misses": self._stats["cache_misses"],
                "stage_distribution": stage_counts,
            }

    def reset(self) -> None:
        """Reset the shader compiler, clearing all sources and compiled output."""
        with self._lock:
            self._sources.clear()
            self._compiled.clear()
            self._sources_by_name.clear()
            self._hot_reload_callbacks.clear()
            self._hot_reload_enabled = False
            self._stats = {
                "sources_registered": 0,
                "sources_removed": 0,
                "compilations_performed": 0,
                "compilation_failures": 0,
                "compilation_total_ms": 0.0,
                "hot_reloads_triggered": 0,
                "cache_hits": 0,
                "cache_misses": 0,
            }
            self._register_builtin_shaders()


# =============================================================================
# RenderQueue
# =============================================================================


class RenderQueue:
    """Draw call management with sorting, batching, culling, and LOD selection.

    Organizes draw commands into ordered buckets (opaque, transparent, overlay),
    sorts by configurable strategy (front-to-back, back-to-front, material,
    texture, state change), merges compatible commands into batches to reduce
    GPU state changes, and integrates frustum culling and LOD selection.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._commands: Dict[str, DrawCommand] = OrderedDict()
        self._batches: Dict[str, RenderBatch] = OrderedDict()
        self._sort_mode: SortMode = SortMode.STATE_CHANGE
        self._culling_mode: CullingMode = CullingMode.FRUSTUM
        self._max_batch_size: int = 64
        self._batch_enabled: bool = True
        self._camera_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
        self._camera_frustum_planes: Optional[List[Tuple[float, float, float, float]]] = None
        self._lod_distances: List[float] = [50.0, 150.0, 400.0, 1000.0]
        self._stats: Dict[str, Any] = {
            "commands_submitted": 0,
            "commands_removed": 0,
            "commands_culled": 0,
            "batches_created": 0,
            "state_changes_saved": 0,
            "total_sort_time_us": 0.0,
            "total_batch_time_us": 0.0,
            "total_cull_time_us": 0.0,
        }

    # ---- Command Management ----

    def submit(self, command: DrawCommand) -> DrawCommand:
        """Submit a draw command to the render queue."""
        with self._lock:
            self._commands[command.command_id] = command
            self._stats["commands_submitted"] += 1
            return command

    def submit_new(
        self,
        mesh_id: str = "",
        material_instance_id: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        bucket: QueueBucket = QueueBucket.OPAQUE,
        sort_key: float = 0.0,
        priority: int = 0,
        bounding_radius: float = 1.0,
        instance_count: int = 1,
    ) -> DrawCommand:
        """Create and submit a new draw command."""
        command = DrawCommand(
            mesh_id=mesh_id,
            material_instance_id=material_instance_id,
            position=position,
            sort_key=sort_key,
            bucket=bucket,
            priority=priority,
            bounding_radius=bounding_radius,
            instance_count=instance_count,
        )
        return self.submit(command)

    def remove(self, command_id: str) -> bool:
        """Remove a draw command from the queue."""
        with self._lock:
            if command_id not in self._commands:
                return False
            del self._commands[command_id]
            self._stats["commands_removed"] += 1
            return True

    def clear(self) -> None:
        """Clear all draw commands and batches."""
        with self._lock:
            self._commands.clear()
            self._batches.clear()

    def get_command(self, command_id: str) -> Optional[DrawCommand]:
        """Retrieve a draw command by ID."""
        with self._lock:
            return self._commands.get(command_id)

    def command_count(self) -> int:
        """Get the total number of queued draw commands."""
        with self._lock:
            return len(self._commands)

    # ---- Culling ----

    def set_culling_mode(self, mode: CullingMode) -> None:
        """Set the culling mode for frustum/distance culling."""
        with self._lock:
            self._culling_mode = mode

    def set_camera(self, position: Tuple[float, float, float]) -> None:
        """Set the camera position for distance-based culling."""
        with self._lock:
            self._camera_position = position

    def set_frustum(self, planes: Optional[List[Tuple[float, float, float, float]]]) -> None:
        """Set the camera frustum planes for frustum culling.

        Each plane is a tuple (nx, ny, nz, d) representing the plane
        equation nx*x + ny*y + nz*z + d = 0, where the positive half-space
        is considered inside the frustum.
        """
        with self._lock:
            self._camera_frustum_planes = planes

    def _is_in_frustum(
        self, position: Tuple[float, float, float], radius: float
    ) -> bool:
        """Test whether a bounding sphere is inside the camera frustum.

        Returns True if the sphere is at least partially visible.
        """
        if self._camera_frustum_planes is None:
            return True
        for nx, ny, nz, d in self._camera_frustum_planes:
            distance = nx * position[0] + ny * position[1] + nz * position[2] + d
            if distance < -radius:
                return False
        return True

    def _compute_distance_to_camera(
        self, position: Tuple[float, float, float]
    ) -> float:
        """Compute squared distance from a position to the camera."""
        dx = position[0] - self._camera_position[0]
        dy = position[1] - self._camera_position[1]
        dz = position[2] - self._camera_position[2]
        return dx * dx + dy * dy + dz * dz

    def cull_commands(self) -> int:
        """Perform culling on all queued commands.

        Returns the number of commands that were culled (marked invisible).
        Marked commands remain in the queue but are skipped during sorting
        and batching.
        """
        cull_start = _time_module.perf_counter()
        culled = 0
        with self._lock:
            if self._culling_mode == CullingMode.NONE:
                for cmd in self._commands.values():
                    cmd.visible = True
                return 0

            for cmd in self._commands.values():
                cmd.visible = True
                if self._culling_mode == CullingMode.FRUSTUM:
                    if not self._is_in_frustum(cmd.position, cmd.bounding_radius):
                        cmd.visible = False
                        culled += 1
                elif self._culling_mode == CullingMode.DISTANCE:
                    dist = self._compute_distance_to_camera(cmd.position)
                    max_dist = self._lod_distances[-1] if self._lod_distances else 1000.0
                    if dist > max_dist * max_dist:
                        cmd.visible = False
                        culled += 1
                elif self._culling_mode == CullingMode.OCCLUSION:
                    if not self._is_in_frustum(cmd.position, cmd.bounding_radius):
                        cmd.visible = False
                        culled += 1

            self._stats["commands_culled"] += culled
            cull_end = _time_module.perf_counter()
            self._stats["total_cull_time_us"] += (cull_end - cull_start) * 1_000_000.0
            return culled

    # ---- LOD Selection ----

    def set_lod_distances(self, distances: List[float]) -> None:
        """Set the LOD transition distances (must be sorted ascending)."""
        with self._lock:
            self._lod_distances = sorted(distances)

    def select_lod(self, command_id: str) -> int:
        """Select the LOD level for a command based on its distance to camera.

        Returns the LOD index (0 = highest detail, increasing = lower detail).
        """
        with self._lock:
            cmd = self._commands.get(command_id)
            if cmd is None:
                return 0
            dist = self._compute_distance_to_camera(cmd.position)
            for i, lod_dist in enumerate(self._lod_distances):
                if dist <= lod_dist * lod_dist:
                    cmd.lod_level = i
                    return i
            cmd.lod_level = len(self._lod_distances)
            return len(self._lod_distances)

    def select_all_lods(self) -> None:
        """Select LOD levels for all queued commands."""
        with self._lock:
            for cmd in self._commands.values():
                dist = self._compute_distance_to_camera(cmd.position)
                cmd.lod_level = len(self._lod_distances)
                for i, lod_dist in enumerate(self._lod_distances):
                    if dist <= lod_dist * lod_dist:
                        cmd.lod_level = i
                        break

    # ---- Sorting ----

    def set_sort_mode(self, mode: SortMode) -> None:
        """Set the draw command sort strategy."""
        with self._lock:
            self._sort_mode = mode

    def get_sort_mode(self) -> SortMode:
        """Get the current sort strategy."""
        with self._lock:
            return self._sort_mode

    def _sort_key_for_command(self, cmd: DrawCommand) -> float:
        """Compute a sort key for a single draw command based on the current sort mode."""
        if self._sort_mode == SortMode.NONE:
            return cmd.sort_key
        elif self._sort_mode == SortMode.FRONT_TO_BACK:
            return self._compute_distance_to_camera(cmd.position)
        elif self._sort_mode == SortMode.BACK_TO_FRONT:
            return -self._compute_distance_to_camera(cmd.position)
        elif self._sort_mode == SortMode.MATERIAL:
            return float(hash(cmd.material_instance_id) & 0x7FFFFFFF)
        elif self._sort_mode == SortMode.TEXTURE:
            return float(hash(cmd.material_instance_id) & 0x7FFFFFFF)
        elif self._sort_mode == SortMode.STATE_CHANGE:
            return float(hash(cmd.material_instance_id + cmd.mesh_id) & 0x7FFFFFFF)
        return cmd.sort_key

    def sort_commands(self) -> List[DrawCommand]:
        """Sort all visible commands and return the ordered list.

        Commands are grouped by bucket (background → opaque → alpha test →
        transparent → overlay → UI), then sorted within each bucket by the
        active sort mode. Culled (invisible) commands are excluded.
        """
        sort_start = _time_module.perf_counter()
        with self._lock:
            bucket_order = [
                QueueBucket.BACKGROUND,
                QueueBucket.OPAQUE,
                QueueBucket.ALPHA_TEST,
                QueueBucket.TRANSPARENT,
                QueueBucket.OVERLAY,
                QueueBucket.UI,
            ]
            visible = [cmd for cmd in self._commands.values() if cmd.visible]
            # Group by bucket
            by_bucket: Dict[QueueBucket, List[DrawCommand]] = {b: [] for b in bucket_order}
            for cmd in visible:
                bucket = cmd.bucket if cmd.bucket in bucket_order else QueueBucket.OPAQUE
                by_bucket[bucket].append(cmd)
            # Sort within each bucket
            sorted_list: List[DrawCommand] = []
            for bucket in bucket_order:
                bucket_cmds = by_bucket[bucket]
                # Sort by priority first (higher priority drawn first for opaque, last for transparent)
                bucket_cmds.sort(key=lambda c: c.priority, reverse=True)
                # Then sort by the active sort mode
                bucket_cmds.sort(key=lambda c: self._sort_key_for_command(c))
                sorted_list.extend(bucket_cmds)
            sort_end = _time_module.perf_counter()
            self._stats["total_sort_time_us"] += (sort_end - sort_start) * 1_000_000.0
            return sorted_list

    # ---- Batching ----

    def set_batch_enabled(self, enabled: bool) -> None:
        """Enable or disable draw command batching."""
        with self._lock:
            self._batch_enabled = enabled

    def set_max_batch_size(self, size: int) -> None:
        """Set the maximum number of commands that can be merged into one batch."""
        with self._lock:
            self._max_batch_size = max(1, size)

    def _can_batch(self, cmd_a: DrawCommand, cmd_b: DrawCommand) -> bool:
        """Check if two draw commands can be merged into the same batch.

        Commands are batchable when they share the same material instance,
        mesh, and bucket, and are close enough in sort key.
        """
        return (
            cmd_a.material_instance_id == cmd_b.material_instance_id
            and cmd_a.mesh_id == cmd_b.mesh_id
            and cmd_a.bucket == cmd_b.bucket
            and cmd_a.visible
            and cmd_b.visible
        )

    def build_batches(self, sorted_commands: List[DrawCommand]) -> List[RenderBatch]:
        """Merge sort-ordered commands into GPU-friendly batches.

        Commands that share material and mesh are grouped into batches
        to minimize state changes. Each batch tracks the number of commands
        merged, total triangles, and state change savings.

        Returns a list of RenderBatch objects in draw order.
        """
        batch_start = _time_module.perf_counter()
        with self._lock:
            self._batches.clear()
            if not self._batch_enabled:
                # Create one batch per command
                for cmd in sorted_commands:
                    batch = RenderBatch(
                        material_instance_id=cmd.material_instance_id,
                        mesh_id=cmd.mesh_id,
                        command_ids=[cmd.command_id],
                        command_count=1,
                        total_triangles=0,
                        instance_count=cmd.instance_count,
                        bucket=cmd.bucket,
                        sort_key=cmd.sort_key,
                    )
                    self._batches[batch.batch_id] = batch
                return list(self._batches.values())

            current_batch: Optional[RenderBatch] = None
            batches: List[RenderBatch] = []

            for cmd in sorted_commands:
                if current_batch is None:
                    current_batch = RenderBatch(
                        material_instance_id=cmd.material_instance_id,
                        mesh_id=cmd.mesh_id,
                        command_ids=[cmd.command_id],
                        command_count=1,
                        total_triangles=0,
                        instance_count=cmd.instance_count,
                        bucket=cmd.bucket,
                        sort_key=cmd.sort_key,
                    )
                elif (
                    self._can_batch(
                        self._commands.get(current_batch.command_ids[0], cmd),
                        cmd,
                    )
                    and current_batch.command_count < self._max_batch_size
                ):
                    current_batch.command_ids.append(cmd.command_id)
                    current_batch.command_count += 1
                    current_batch.instance_count += cmd.instance_count
                    current_batch.state_changes_saved += 1
                    self._stats["state_changes_saved"] += 1
                else:
                    self._batches[current_batch.batch_id] = current_batch
                    batches.append(current_batch)
                    current_batch = RenderBatch(
                        material_instance_id=cmd.material_instance_id,
                        mesh_id=cmd.mesh_id,
                        command_ids=[cmd.command_id],
                        command_count=1,
                        total_triangles=0,
                        instance_count=cmd.instance_count,
                        bucket=cmd.bucket,
                        sort_key=cmd.sort_key,
                    )

            if current_batch is not None:
                self._batches[current_batch.batch_id] = current_batch
                batches.append(current_batch)

            self._stats["batches_created"] += len(batches)
            batch_end = _time_module.perf_counter()
            self._stats["total_batch_time_us"] += (batch_end - batch_start) * 1_000_000.0
            return batches

    def get_batches(self) -> List[RenderBatch]:
        """Get all current render batches."""
        with self._lock:
            return list(self._batches.values())

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get render queue statistics."""
        with self._lock:
            visible = sum(1 for c in self._commands.values() if c.visible)
            culled = sum(1 for c in self._commands.values() if not c.visible)
            bucket_dist: Dict[str, int] = {}
            for cmd in self._commands.values():
                key = cmd.bucket.value
                bucket_dist[key] = bucket_dist.get(key, 0) + 1
            return {
                "total_commands": len(self._commands),
                "visible_commands": visible,
                "culled_commands": culled,
                "active_batches": len(self._batches),
                "sort_mode": self._sort_mode.value,
                "culling_mode": self._culling_mode.value,
                "batch_enabled": self._batch_enabled,
                "max_batch_size": self._max_batch_size,
                "bucket_distribution": bucket_dist,
                "commands_submitted": self._stats["commands_submitted"],
                "commands_removed": self._stats["commands_removed"],
                "commands_culled": self._stats["commands_culled"],
                "batches_created": self._stats["batches_created"],
                "state_changes_saved": self._stats["state_changes_saved"],
                "total_sort_time_us": round(self._stats["total_sort_time_us"], 2),
                "total_batch_time_us": round(self._stats["total_batch_time_us"], 2),
                "total_cull_time_us": round(self._stats["total_cull_time_us"], 2),
            }

    def reset(self) -> None:
        """Reset the render queue to initial state."""
        with self._lock:
            self._commands.clear()
            self._batches.clear()
            self._stats = {
                "commands_submitted": 0,
                "commands_removed": 0,
                "commands_culled": 0,
                "batches_created": 0,
                "state_changes_saved": 0,
                "total_sort_time_us": 0.0,
                "total_batch_time_us": 0.0,
                "total_cull_time_us": 0.0,
            }


# =============================================================================
# LightManager
# =============================================================================


class LightManager:
    """Scene lighting system with culling, shadow maps, and light probes.

    Manages all light sources in the scene (directional, point, spot, area),
    performs light culling and assignment to objects, manages shadow map
    allocation and invalidation, supports light probes for indirect lighting,
    and provides ambient light and environment map configuration.
    """

    _MAX_LIGHTS_PER_OBJECT: int = 8
    _MAX_SHADOW_MAPS: int = 16
    _MAX_LIGHT_PROBES: int = 256

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._lights: Dict[str, SceneLight] = OrderedDict()
        self._shadow_maps: Dict[str, ShadowMap] = OrderedDict()
        self._probes: Dict[str, LightProbe] = OrderedDict()
        self._ambient_color: Tuple[float, float, float] = (0.05, 0.05, 0.08)
        self._ambient_intensity: float = 1.0
        self._environment_map: str = ""
        self._environment_intensity: float = 1.0
        self._max_lights_per_object: int = self._MAX_LIGHTS_PER_OBJECT
        self._max_shadow_maps: int = self._MAX_SHADOW_MAPS
        self._max_probes: int = self._MAX_LIGHT_PROBES
        self._stats: Dict[str, Any] = {
            "lights_created": 0,
            "lights_removed": 0,
            "shadow_maps_allocated": 0,
            "shadow_maps_freed": 0,
            "probes_created": 0,
            "probes_removed": 0,
            "light_assignments": 0,
        }

    # ---- Light Registration ----

    def create_light(
        self,
        name: str = "",
        kind: LightKind = LightKind.POINT,
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        intensity: float = 1.0,
        range: float = 10.0,
        casts_shadows: bool = False,
        shadow_map_resolution: ShadowMapResolution = ShadowMapResolution.HIGH_1024,
        importance: int = 0,
    ) -> SceneLight:
        """Create and register a new scene light."""
        with self._lock:
            light = SceneLight(
                name=name,
                kind=kind,
                position=position,
                color=color,
                intensity=intensity,
                range=range,
                casts_shadows=casts_shadows,
                shadow_map_resolution=shadow_map_resolution,
                importance=importance,
            )
            self._lights[light.light_id] = light
            self._stats["lights_created"] += 1
            # Auto-allocate shadow map if needed
            if casts_shadows:
                self._allocate_shadow_map(light.light_id)
            return light

    def remove_light(self, light_id: str) -> bool:
        """Remove a light and its associated shadow map."""
        with self._lock:
            if light_id not in self._lights:
                return False
            del self._lights[light_id]
            self._stats["lights_removed"] += 1
            # Remove associated shadow map
            to_remove = [
                sid for sid, sm in self._shadow_maps.items()
                if sm.light_id == light_id
            ]
            for sid in to_remove:
                del self._shadow_maps[sid]
                self._stats["shadow_maps_freed"] += 1
            return True

    def update_light(
        self, light_id: str, **changes: Any
    ) -> Optional[SceneLight]:
        """Update properties of an existing light."""
        with self._lock:
            light = self._lights.get(light_id)
            if light is None:
                return None
            allowed = {
                "name", "kind", "position", "color", "intensity", "range",
                "spot_angle", "spot_inner_angle", "direction", "area_width",
                "area_height", "casts_shadows", "shadow_map_resolution",
                "shadow_bias", "shadow_normal_bias", "shadow_softness",
                "shadow_near", "shadow_far", "enabled", "importance",
                "layer_mask",
            }
            for key, value in changes.items():
                if key in allowed:
                    setattr(light, key, value)
            if "casts_shadows" in changes:
                if changes["casts_shadows"]:
                    self._allocate_shadow_map(light_id)
                else:
                    to_remove = [
                        sid for sid, sm in self._shadow_maps.items()
                        if sm.light_id == light_id
                    ]
                    for sid in to_remove:
                        del self._shadow_maps[sid]
                        self._stats["shadow_maps_freed"] += 1
            return light

    def get_light(self, light_id: str) -> Optional[SceneLight]:
        """Retrieve a light by ID."""
        with self._lock:
            return self._lights.get(light_id)

    def list_lights(
        self, kind: Optional[LightKind] = None, shadow_casting_only: bool = False
    ) -> List[SceneLight]:
        """List all lights, optionally filtered by type or shadow casting."""
        with self._lock:
            result = list(self._lights.values())
            if kind is not None:
                result = [l for l in result if l.kind == kind]
            if shadow_casting_only:
                result = [l for l in result if l.casts_shadows]
            return result

    def get_active_lights(
        self, position: Tuple[float, float, float], max_distance: float = 100.0
    ) -> List[SceneLight]:
        """Get lights active near a position, sorted by importance then intensity."""
        with self._lock:
            candidates = []
            for light in self._lights.values():
                if not light.enabled:
                    continue
                if light.kind in (LightKind.DIRECTIONAL,):
                    candidates.append(light)
                    continue
                dx = light.position[0] - position[0]
                dy = light.position[1] - position[1]
                dz = light.position[2] - position[2]
                sq_dist = dx * dx + dy * dy + dz * dz
                effective_range = light.range + max_distance
                if sq_dist <= effective_range * effective_range:
                    candidates.append(light)
            candidates.sort(key=lambda l: (-l.importance, -l.intensity))
            return candidates[: self._max_lights_per_object]

    # ---- Shadow Maps ----

    def _allocate_shadow_map(self, light_id: str) -> Optional[ShadowMap]:
        """Allocate a shadow map for a light if under the limit."""
        if len(self._shadow_maps) >= self._max_shadow_maps:
            return None
        light = self._lights.get(light_id)
        if light is None:
            return None
        sm = ShadowMap(
            light_id=light_id,
            resolution=light.shadow_resolution_int,
            depth_bias=light.shadow_bias,
            normal_bias=light.shadow_normal_bias,
            softness=light.shadow_softness,
        )
        self._shadow_maps[sm.shadow_map_id] = sm
        self._stats["shadow_maps_allocated"] += 1
        return sm

    def get_shadow_map(self, light_id: str) -> Optional[ShadowMap]:
        """Get the shadow map associated with a light."""
        with self._lock:
            for sm in self._shadow_maps.values():
                if sm.light_id == light_id:
                    return sm
            return None

    def list_shadow_maps(self) -> List[ShadowMap]:
        """List all allocated shadow maps."""
        with self._lock:
            return list(self._shadow_maps.values())

    def invalidate_shadow_map(self, light_id: str) -> bool:
        """Mark a shadow map as needing re-rendering."""
        with self._lock:
            for sm in self._shadow_maps.values():
                if sm.light_id == light_id:
                    sm.is_valid = False
                    return True
            return False

    def validate_shadow_map(self, light_id: str) -> bool:
        """Mark a shadow map as up-to-date after rendering."""
        with self._lock:
            for sm in self._shadow_maps.values():
                if sm.light_id == light_id:
                    sm.is_valid = True
                    sm.last_updated = _now()
                    return True
            return False

    def set_max_shadow_maps(self, limit: int) -> None:
        """Set the maximum number of simultaneous shadow maps."""
        with self._lock:
            self._max_shadow_maps = max(1, limit)

    # ---- Light Probes ----

    def create_probe(
        self,
        name: str = "",
        position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        sh_coefficients: Optional[List[float]] = None,
        influence_radius: float = 5.0,
        blend_distance: float = 1.0,
    ) -> Optional[LightProbe]:
        """Create a light probe at a position, if under the limit."""
        with self._lock:
            if len(self._probes) >= self._max_probes:
                return None
            probe = LightProbe(
                name=name,
                position=position,
                sh_coefficients=sh_coefficients or [0.0] * 27,
                influence_radius=influence_radius,
                blend_distance=blend_distance,
            )
            self._probes[probe.probe_id] = probe
            self._stats["probes_created"] += 1
            return probe

    def remove_probe(self, probe_id: str) -> bool:
        """Remove a light probe by ID."""
        with self._lock:
            if probe_id not in self._probes:
                return False
            del self._probes[probe_id]
            self._stats["probes_removed"] += 1
            return True

    def get_probe(self, probe_id: str) -> Optional[LightProbe]:
        """Retrieve a light probe by ID."""
        with self._lock:
            return self._probes.get(probe_id)

    def list_probes(self) -> List[LightProbe]:
        """List all light probes."""
        with self._lock:
            return list(self._probes.values())

    def get_probes_near(
        self, position: Tuple[float, float, float]
    ) -> List[LightProbe]:
        """Get light probes that influence a position."""
        with self._lock:
            result = []
            for probe in self._probes.values():
                if not probe.enabled:
                    continue
                dx = probe.position[0] - position[0]
                dy = probe.position[1] - position[1]
                dz = probe.position[2] - position[2]
                sq_dist = dx * dx + dy * dy + dz * dz
                max_dist = probe.influence_radius + probe.blend_distance
                if sq_dist <= max_dist * max_dist:
                    result.append(probe)
            result.sort(key=lambda p: p.priority, reverse=True)
            return result

    def set_max_probes(self, limit: int) -> None:
        """Set the maximum number of light probes."""
        with self._lock:
            self._max_probes = max(1, limit)

    # ---- Ambient Light ----

    def set_ambient(
        self,
        color: Tuple[float, float, float],
        intensity: float = 1.0,
    ) -> None:
        """Set the ambient light color and intensity."""
        with self._lock:
            self._ambient_color = color
            self._ambient_intensity = _clamp(intensity, 0.0, 10.0)

    def get_ambient(self) -> Dict[str, Any]:
        """Get the ambient light configuration."""
        with self._lock:
            return {
                "color": list(self._ambient_color),
                "intensity": self._ambient_intensity,
            }

    def set_environment_map(self, texture_path: str, intensity: float = 1.0) -> None:
        """Set the environment map texture and intensity."""
        with self._lock:
            self._environment_map = texture_path
            self._environment_intensity = _clamp(intensity, 0.0, 10.0)

    def get_environment_map(self) -> Dict[str, Any]:
        """Get the environment map configuration."""
        with self._lock:
            return {
                "texture": self._environment_map,
                "intensity": self._environment_intensity,
            }

    # ---- Light Assignment ----

    def assign_lights(
        self,
        position: Tuple[float, float, float],
        max_lights: Optional[int] = None,
    ) -> List[SceneLight]:
        """Assign the most relevant lights to a position in the scene.

        Returns a list of up to max_lights lights sorted by importance
        and intensity. Directional lights are always included. Other
        lights are filtered by range.
        """
        with self._lock:
            limit = max_lights if max_lights is not None else self._max_lights_per_object
            self._stats["light_assignments"] += 1
            return self.get_active_lights(position, 0.0)[:limit]

    def set_max_lights_per_object(self, limit: int) -> None:
        """Set the maximum number of lights that can affect a single object."""
        with self._lock:
            self._max_lights_per_object = max(1, limit)

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get light manager statistics."""
        with self._lock:
            kind_counts: Dict[str, int] = {}
            for light in self._lights.values():
                key = light.kind.value
                kind_counts[key] = kind_counts.get(key, 0) + 1
            shadow_lights = sum(1 for l in self._lights.values() if l.casts_shadows)
            enabled_lights = sum(1 for l in self._lights.values() if l.enabled)
            valid_shadow_maps = sum(1 for sm in self._shadow_maps.values() if sm.is_valid)
            return {
                "total_lights": len(self._lights),
                "enabled_lights": enabled_lights,
                "shadow_casting_lights": shadow_lights,
                "active_shadow_maps": len(self._shadow_maps),
                "valid_shadow_maps": valid_shadow_maps,
                "max_shadow_maps": self._max_shadow_maps,
                "total_probes": len(self._probes),
                "max_probes": self._max_probes,
                "max_lights_per_object": self._max_lights_per_object,
                "ambient_color": list(self._ambient_color),
                "ambient_intensity": self._ambient_intensity,
                "environment_map": self._environment_map,
                "environment_intensity": self._environment_intensity,
                "kind_distribution": kind_counts,
                "lights_created": self._stats["lights_created"],
                "lights_removed": self._stats["lights_removed"],
                "shadow_maps_allocated": self._stats["shadow_maps_allocated"],
                "shadow_maps_freed": self._stats["shadow_maps_freed"],
                "probes_created": self._stats["probes_created"],
                "probes_removed": self._stats["probes_removed"],
                "light_assignments": self._stats["light_assignments"],
            }

    def reset(self) -> None:
        """Reset the light manager to initial state."""
        with self._lock:
            self._lights.clear()
            self._shadow_maps.clear()
            self._probes.clear()
            self._ambient_color = (0.05, 0.05, 0.08)
            self._ambient_intensity = 1.0
            self._environment_map = ""
            self._environment_intensity = 1.0
            self._stats = {
                "lights_created": 0,
                "lights_removed": 0,
                "shadow_maps_allocated": 0,
                "shadow_maps_freed": 0,
                "probes_created": 0,
                "probes_removed": 0,
                "light_assignments": 0,
            }


# =============================================================================
# PostProcessStack
# =============================================================================


# Default parameters for each post-process effect kind
_DEFAULT_EFFECT_PARAMS: Dict[PostEffectKind, Dict[str, Any]] = {
    PostEffectKind.BLOOM: {
        "threshold": 0.8, "radius": 2.0, "scatter": 0.7,
        "tint": (1.0, 1.0, 1.0),
    },
    PostEffectKind.DEPTH_OF_FIELD: {
        "focus_distance": 10.0, "aperture": 2.8, "focal_length": 50.0,
        "max_blur": 4.0, "near_transition": 0.2, "far_transition": 0.8,
    },
    PostEffectKind.MOTION_BLUR: {
        "sample_count": 8, "shutter_speed": 0.02, "max_velocity": 10.0,
    },
    PostEffectKind.COLOR_GRADING: {
        "lookup_texture": "", "contrast": 1.0, "saturation": 1.0,
        "brightness": 0.0, "temperature": 6500.0,
    },
    PostEffectKind.VIGNETTE: {
        "radius": 0.8, "softness": 0.3, "color": (0.0, 0.0, 0.0),
    },
    PostEffectKind.SSAO: {
        "radius": 1.0, "intensity": 0.8, "bias": 0.025,
        "sample_count": 16, "occlusion_power": 2.0, "blur_radius": 2.0,
    },
    PostEffectKind.SSR: {
        "max_steps": 64, "stride": 1.0, "thickness": 0.5,
        "max_distance": 20.0, "fade_distance": 5.0,
    },
    PostEffectKind.TONEMAPPING: {
        "exposure": 1.0, "method": "aces", "white_point": 4.0, "gamma": 2.2,
    },
    PostEffectKind.SHARPEN: {
        "intensity": 0.5, "radius": 1.0, "threshold": 0.05,
    },
    PostEffectKind.CHROMATIC_ABERRATION: {
        "intensity": 0.3, "radial": 0.5,
    },
    PostEffectKind.FILM_GRAIN: {
        "intensity": 0.15, "grain_size": 1.6, "animate": True,
    },
    PostEffectKind.LENS_FLARE: {
        "ghost_count": 4, "halo_width": 0.5, "distortion": 0.3,
        "threshold": 0.9,
    },
}

# Default quality presets for post-processing
_QUALITY_PRESETS: Dict[QualityTier, Dict[str, Any]] = {
    QualityTier.PERFORMANCE: {
        "bloom": False,
        "dof": False,
        "motion_blur": False,
        "color_grading": True,
        "vignette": False,
        "ssao": False,
        "ssr": False,
        "tonemapping": True,
        "sharpen": False,
        "chromatic_aberration": False,
        "film_grain": False,
        "lens_flare": False,
    },
    QualityTier.BALANCED: {
        "bloom": True,
        "dof": False,
        "motion_blur": False,
        "color_grading": True,
        "vignette": True,
        "ssao": False,
        "ssr": False,
        "tonemapping": True,
        "sharpen": True,
        "chromatic_aberration": False,
        "film_grain": False,
        "lens_flare": False,
    },
    QualityTier.QUALITY: {
        "bloom": True,
        "dof": True,
        "motion_blur": True,
        "color_grading": True,
        "vignette": True,
        "ssao": True,
        "ssr": False,
        "tonemapping": True,
        "sharpen": True,
        "chromatic_aberration": False,
        "film_grain": False,
        "lens_flare": False,
    },
    QualityTier.CINEMATIC: {
        "bloom": True,
        "dof": True,
        "motion_blur": True,
        "color_grading": True,
        "vignette": True,
        "ssao": True,
        "ssr": True,
        "tonemapping": True,
        "sharpen": True,
        "chromatic_aberration": True,
        "film_grain": True,
        "lens_flare": True,
    },
}

# Mapping from PostEffectKind to quality preset key
_KIND_TO_PRESET_KEY: Dict[PostEffectKind, str] = {
    PostEffectKind.BLOOM: "bloom",
    PostEffectKind.DEPTH_OF_FIELD: "dof",
    PostEffectKind.MOTION_BLUR: "motion_blur",
    PostEffectKind.COLOR_GRADING: "color_grading",
    PostEffectKind.VIGNETTE: "vignette",
    PostEffectKind.SSAO: "ssao",
    PostEffectKind.SSR: "ssr",
    PostEffectKind.TONEMAPPING: "tonemapping",
    PostEffectKind.SHARPEN: "sharpen",
    PostEffectKind.CHROMATIC_ABERRATION: "chromatic_aberration",
    PostEffectKind.FILM_GRAIN: "film_grain",
    PostEffectKind.LENS_FLARE: "lens_flare",
}

# Estimated GPU cost per effect (relative units)
_KIND_COST: Dict[PostEffectKind, float] = {
    PostEffectKind.BLOOM: 3.0,
    PostEffectKind.DEPTH_OF_FIELD: 8.0,
    PostEffectKind.MOTION_BLUR: 6.0,
    PostEffectKind.COLOR_GRADING: 1.0,
    PostEffectKind.VIGNETTE: 0.5,
    PostEffectKind.SSAO: 12.0,
    PostEffectKind.SSR: 15.0,
    PostEffectKind.TONEMAPPING: 1.0,
    PostEffectKind.SHARPEN: 1.5,
    PostEffectKind.CHROMATIC_ABERRATION: 0.5,
    PostEffectKind.FILM_GRAIN: 0.5,
    PostEffectKind.LENS_FLARE: 2.0,
}


class PostProcessStack:
    """Post-processing effects chain with ordering, presets, and performance tracking.

    Manages a configurable chain of screen-space post-processing effects
    (bloom, DOF, motion blur, color grading, vignette, SSAO, SSR, tonemapping,
    sharpen, chromatic aberration, film grain, lens flare). Effects are ordered
    by priority and can be toggled at runtime. Quality presets provide
    predefined configurations. Performance impact is tracked per effect.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._effects: Dict[str, PostEffect] = OrderedDict()
        self._enabled: bool = True
        self._global_quality: QualityTier = QualityTier.BALANCED
        self._resolution_scale: float = 1.0
        self._stats: Dict[str, Any] = {
            "frames_processed": 0,
            "total_execution_us": 0.0,
            "effects_toggled": 0,
        }
        self._init_default_effects()

    def _init_default_effects(self) -> None:
        """Initialize all effect types with default parameters."""
        default_order = [
            PostEffectKind.SSAO,
            PostEffectKind.SSR,
            PostEffectKind.DEPTH_OF_FIELD,
            PostEffectKind.MOTION_BLUR,
            PostEffectKind.BLOOM,
            PostEffectKind.LENS_FLARE,
            PostEffectKind.COLOR_GRADING,
            PostEffectKind.VIGNETTE,
            PostEffectKind.CHROMATIC_ABERRATION,
            PostEffectKind.SHARPEN,
            PostEffectKind.FILM_GRAIN,
            PostEffectKind.TONEMAPPING,
        ]
        preset = _QUALITY_PRESETS.get(self._global_quality, _QUALITY_PRESETS[QualityTier.BALANCED])
        for i, kind in enumerate(default_order):
            defaults = dict(_DEFAULT_EFFECT_PARAMS.get(kind, {}))
            preset_key = _KIND_TO_PRESET_KEY.get(kind, "")
            enabled = preset.get(preset_key, False)
            effect = PostEffect(
                kind=kind,
                name=kind.value.replace("_", " ").title(),
                enabled=enabled,
                intensity=1.0,
                priority=i,
                quality=self._global_quality,
                parameters=defaults,
            )
            self._effects[effect.effect_id] = effect

    # ---- Effect Management ----

    def get_effect(self, effect_id: str) -> Optional[PostEffect]:
        """Retrieve a post-process effect by ID."""
        with self._lock:
            return self._effects.get(effect_id)

    def get_effect_by_kind(self, kind: PostEffectKind) -> Optional[PostEffect]:
        """Retrieve the first post-process effect matching a kind."""
        with self._lock:
            for effect in self._effects.values():
                if effect.kind == kind:
                    return effect
            return None

    def list_effects(self) -> List[PostEffect]:
        """List all effects ordered by priority."""
        with self._lock:
            return sorted(
                self._effects.values(), key=lambda e: e.priority
            )

    def enable_effect(self, effect_id: str) -> bool:
        """Enable a post-process effect at runtime."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.enabled = True
            self._stats["effects_toggled"] += 1
            return True

    def disable_effect(self, effect_id: str) -> bool:
        """Disable a post-process effect at runtime."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.enabled = False
            self._stats["effects_toggled"] += 1
            return True

    def toggle_effect(self, effect_id: str) -> Optional[bool]:
        """Toggle a post-process effect on/off. Returns the new state."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return None
            effect.enabled = not effect.enabled
            self._stats["effects_toggled"] += 1
            return effect.enabled

    def set_effect_intensity(self, effect_id: str, intensity: float) -> bool:
        """Set the intensity of a post-process effect (0.0 to 1.0)."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.intensity = _clamp(intensity, 0.0, 1.0)
            return True

    def set_effect_parameters(
        self, effect_id: str, parameters: Dict[str, Any]
    ) -> bool:
        """Update parameters of a post-process effect."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.parameters.update(parameters)
            return True

    def set_effect_priority(self, effect_id: str, priority: int) -> bool:
        """Set the priority (order) of a post-process effect."""
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return False
            effect.priority = priority
            return True

    def reorder_effects(self, effect_ids: List[str]) -> None:
        """Reorder effects by assigning priorities based on list order."""
        with self._lock:
            for i, eid in enumerate(effect_ids):
                effect = self._effects.get(eid)
                if effect is not None:
                    effect.priority = i

    # ---- Quality Presets ----

    def set_quality(self, tier: QualityTier) -> None:
        """Apply a quality preset that enables/disables effects."""
        with self._lock:
            self._global_quality = tier
            preset = _QUALITY_PRESETS.get(tier, _QUALITY_PRESETS[QualityTier.BALANCED])
            for effect in self._effects.values():
                key = _KIND_TO_PRESET_KEY.get(effect.kind)
                if key is not None and key in preset:
                    effect.enabled = preset[key]
                effect.quality = tier

    def get_quality(self) -> QualityTier:
        """Get the current global quality tier."""
        with self._lock:
            return self._global_quality

    def set_resolution_scale(self, scale: float) -> None:
        """Set the resolution scale for post-processing (0.25 to 1.0)."""
        with self._lock:
            self._resolution_scale = _clamp(scale, 0.25, 1.0)

    def get_resolution_scale(self) -> float:
        """Get the current resolution scale."""
        with self._lock:
            return self._resolution_scale

    def enable_stack(self) -> None:
        """Enable the entire post-process stack."""
        with self._lock:
            self._enabled = True

    def disable_stack(self) -> None:
        """Disable the entire post-process stack (skip all effects)."""
        with self._lock:
            self._enabled = False

    def is_stack_enabled(self) -> bool:
        """Check if the post-process stack is enabled."""
        with self._lock:
            return self._enabled

    # ---- Performance Tracking ----

    def get_enabled_effects(self) -> List[PostEffect]:
        """Get all enabled effects ordered by priority."""
        with self._lock:
            return sorted(
                [e for e in self._effects.values() if e.enabled],
                key=lambda e: e.priority,
            )

    def estimate_cost(self) -> float:
        """Estimate the total GPU cost of all enabled effects."""
        with self._lock:
            total = 0.0
            for effect in self._effects.values():
                if effect.enabled:
                    cost = _KIND_COST.get(effect.kind, 1.0)
                    total += cost * effect.intensity
            return total

    def record_execution(self, effect_id: str, execution_us: float) -> None:
        """Record the execution time of a post-process effect.

        Updates the running average execution time for the effect.
        """
        with self._lock:
            effect = self._effects.get(effect_id)
            if effect is None:
                return
            effect.execution_count += 1
            n = effect.execution_count
            effect.average_execution_us = (
                effect.average_execution_us * (n - 1) + execution_us
            ) / n

    def process_frame(self) -> Dict[str, float]:
        """Simulate processing a frame through the post-process stack.

        Returns a dict mapping effect IDs to their simulated execution
        times in microseconds. Disabled effects are skipped.
        """
        with self._lock:
            if not self._enabled:
                return {}
            self._stats["frames_processed"] += 1
            results: Dict[str, float] = {}
            for effect in sorted(
                self._effects.values(), key=lambda e: e.priority
            ):
                if not effect.enabled:
                    continue
                cost = _KIND_COST.get(effect.kind, 1.0)
                execution_us = cost * effect.intensity * 100.0 / self._resolution_scale
                self.record_execution(effect.effect_id, execution_us)
                results[effect.effect_id] = execution_us
                self._stats["total_execution_us"] += execution_us
            return results

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get post-process stack statistics."""
        with self._lock:
            enabled_count = sum(1 for e in self._effects.values() if e.enabled)
            total_cost = self.estimate_cost()
            kind_dist: Dict[str, int] = {}
            for e in self._effects.values():
                key = e.kind.value
                kind_dist[key] = kind_dist.get(key, 0) + 1
            return {
                "enabled": self._enabled,
                "global_quality": self._global_quality.value,
                "resolution_scale": self._resolution_scale,
                "total_effects": len(self._effects),
                "enabled_effects": enabled_count,
                "disabled_effects": len(self._effects) - enabled_count,
                "estimated_cost": round(total_cost, 2),
                "kind_distribution": kind_dist,
                "frames_processed": self._stats["frames_processed"],
                "total_execution_us": round(self._stats["total_execution_us"], 2),
                "effects_toggled": self._stats["effects_toggled"],
            }

    def get_effect_performance(self) -> List[Dict[str, Any]]:
        """Get per-effect performance tracking data."""
        with self._lock:
            return [
                {
                    "effect_id": e.effect_id,
                    "kind": e.kind.value,
                    "enabled": e.enabled,
                    "average_execution_us": round(e.average_execution_us, 2),
                    "execution_count": e.execution_count,
                    "estimated_cost": round(_KIND_COST.get(e.kind, 1.0) * e.intensity, 2),
                }
                for e in sorted(
                    self._effects.values(), key=lambda e: e.priority
                )
            ]

    def reset(self) -> None:
        """Reset the post-process stack to initial state."""
        with self._lock:
            self._effects.clear()
            self._enabled = True
            self._global_quality = QualityTier.BALANCED
            self._resolution_scale = 1.0
            self._stats = {
                "frames_processed": 0,
                "total_execution_us": 0.0,
                "effects_toggled": 0,
            }
            self._init_default_effects()


# =============================================================================
# RenderPipeline (Singleton)
# =============================================================================


class RenderPipeline:
    """Complete rendering pipeline orchestrating all subsystems.

    The central singleton that coordinates the full rendering pipeline:
    multi-pass rendering architecture, material management, shader
    compilation, draw call queuing and batching, scene lighting, and
    post-processing effects. Collects frame statistics for profiling
    and auto-quality adjustment.

    Subsystems:
        MaterialLibrary  — material definitions, instances, and caching
        ShaderCompiler   — shader sources, compilation, and hot-reload
        RenderQueue      — draw command sorting, batching, and culling
        LightManager     — scene lights, shadow maps, and probes
        PostProcessStack — screen-space effects chain

    Thread-safe via double-checked locking singleton pattern.
    """

    _instance: Optional["RenderPipeline"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "RenderPipeline":
        """Thread-safe singleton construction with double-checked locking."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        """Initialize all subsystems on first construction only."""
        if getattr(self, "_initialized", False):
            return
        self._initialized = True

        # Subsystems
        self._materials = MaterialLibrary()
        self._shaders = ShaderCompiler()
        self._queue = RenderQueue()
        self._lights = LightManager()
        self._post_process = PostProcessStack()

        # Pass management
        self._passes: Dict[str, RenderPass] = OrderedDict()
        self._pass_order: List[str] = []

        # Pipeline state
        self._quality: QualityTier = QualityTier.BALANCED
        self._resolution_scale: float = 1.0
        self._target_fps: int = 60
        self._current_fps: float = 60.0
        self._frame_count: int = 0
        self._is_rendering: bool = False
        self._clear_color: Tuple[float, float, float, float] = (0.05, 0.05, 0.08, 1.0)

        # Frame statistics
        self._frame_snapshots: List[FrameSnapshot] = []
        self._max_snapshots: int = 300

        # Initialize default render passes
        self._init_default_passes()

    @classmethod
    def get_instance(cls) -> "RenderPipeline":
        """Return the singleton RenderPipeline instance."""
        return cls()

    # ---- Subsystem Accessors ----

    @property
    def materials(self) -> MaterialLibrary:
        """Get the MaterialLibrary subsystem."""
        return self._materials

    @property
    def shaders(self) -> ShaderCompiler:
        """Get the ShaderCompiler subsystem."""
        return self._shaders

    @property
    def queue(self) -> RenderQueue:
        """Get the RenderQueue subsystem."""
        return self._queue

    @property
    def lights(self) -> LightManager:
        """Get the LightManager subsystem."""
        return self._lights

    @property
    def post_process(self) -> PostProcessStack:
        """Get the PostProcessStack subsystem."""
        return self._post_process

    # ---- Render Pass Management ----

    _PASS_ORDER_TEMPLATE: Dict[RenderPassType, int] = {
        RenderPassType.SHADOW: 0,
        RenderPassType.SKYBOX: 10,
        RenderPassType.DEFERRED: 20,
        RenderPassType.FORWARD: 30,
        RenderPassType.POST: 40,
        RenderPassType.UI: 50,
        RenderPassType.CUSTOM: 60,
    }

    def _init_default_passes(self) -> None:
        """Initialize the standard render pass pipeline."""
        defaults: List[Tuple[RenderPassType, str, Tuple[float, float, float, float], BlendOperation]] = [
            (RenderPassType.SHADOW, "Shadow Maps", (0.0, 0.0, 0.0, 1.0), BlendOperation.NONE),
            (RenderPassType.SKYBOX, "Skybox", (0.1, 0.15, 0.25, 1.0), BlendOperation.NONE),
            (RenderPassType.DEFERRED, "Deferred G-Buffer", (0.0, 0.0, 0.0, 1.0), BlendOperation.NONE),
            (RenderPassType.FORWARD, "Forward Transparent", (0.0, 0.0, 0.0, 0.0), BlendOperation.ALPHA),
            (RenderPassType.POST, "Post-Processing", (0.0, 0.0, 0.0, 1.0), BlendOperation.NONE),
            (RenderPassType.UI, "UI Overlay", (0.0, 0.0, 0.0, 0.0), BlendOperation.ALPHA),
        ]
        for pass_type, name, clear_color, blend in defaults:
            order = self._PASS_ORDER_TEMPLATE.get(pass_type, 50)
            rp = RenderPass(
                pass_type=pass_type,
                name=name,
                order=order,
                clear_color=clear_color,
                blend=blend,
            )
            self._passes[rp.pass_id] = rp
            self._pass_order.append(rp.pass_id)

    def add_pass(
        self,
        name: str,
        pass_type: RenderPassType = RenderPassType.CUSTOM,
        order: Optional[int] = None,
        clear_color: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0),
        blend: BlendOperation = BlendOperation.NONE,
        culling: CullingMode = CullingMode.FRUSTUM,
        target_width: int = 1920,
        target_height: int = 1080,
        dependencies: Optional[List[str]] = None,
    ) -> RenderPass:
        """Add a custom render pass to the pipeline."""
        with self._lock:
            if order is None:
                order = self._PASS_ORDER_TEMPLATE.get(pass_type, len(self._passes) * 10)
            rp = RenderPass(
                pass_type=pass_type,
                name=name,
                order=order,
                clear_color=clear_color,
                blend=blend,
                culling=culling,
                target_width=target_width,
                target_height=target_height,
                dependencies=dependencies or [],
            )
            self._passes[rp.pass_id] = rp
            self._pass_order.append(rp.pass_id)
            self._pass_order.sort(
                key=lambda pid: self._passes[pid].order
            )
            return rp

    def remove_pass(self, pass_id: str) -> bool:
        """Remove a render pass from the pipeline."""
        with self._lock:
            if pass_id not in self._passes:
                return False
            del self._passes[pass_id]
            if pass_id in self._pass_order:
                self._pass_order.remove(pass_id)
            return True

    def set_pass_enabled(self, pass_id: str, enabled: bool) -> bool:
        """Enable or disable a render pass."""
        with self._lock:
            rp = self._passes.get(pass_id)
            if rp:
                rp.enabled = enabled
                return True
            return False

    def get_passes(self) -> List[RenderPass]:
        """Get all render passes in execution order."""
        with self._lock:
            return [self._passes[pid] for pid in self._pass_order if pid in self._passes]

    def get_pass(self, pass_id: str) -> Optional[RenderPass]:
        """Get a render pass by ID."""
        with self._lock:
            return self._passes.get(pass_id)

    # ---- Pipeline Execution ----

    def render_frame(self) -> FrameSnapshot:
        """Execute the complete rendering pipeline for a single frame.

        Steps:
        1. Cull and sort draw commands
        2. Build render batches
        3. Execute render passes in order
        4. Run post-process stack
        5. Collect and return frame statistics
        """
        frame_start = _time_module.perf_counter()

        # Step 1: Cull and sort draw commands
        culled = self._queue.cull_commands()
        sorted_commands = self._queue.sort_commands()

        # Step 2: Build batches
        batches = self._queue.build_batches(sorted_commands)

        # Step 3: Execute render passes
        pass_timings: Dict[str, float] = {}
        total_draw_calls = 0
        total_triangles = 0
        total_state_changes = 0

        with self._lock:
            enabled_passes = [
                self._passes[pid] for pid in self._pass_order
                if pid in self._passes and self._passes[pid].enabled
            ]

            for rp in enabled_passes:
                pass_start = _time_module.perf_counter()
                # Simulate pass execution
                rp.draw_commands = len(sorted_commands) // max(1, len(enabled_passes))
                rp.triangles_submitted = rp.draw_commands * 1000
                total_draw_calls += rp.draw_commands
                total_triangles += rp.triangles_submitted
                rp.execution_us = (_time_module.perf_counter() - pass_start) * 1_000_000.0
                pass_timings[rp.name] = rp.execution_us

        # Step 4: Run post-process stack
        pp_timings = self._post_process.process_frame()
        pp_total_us = sum(pp_timings.values())

        # Step 5: Build frame snapshot
        frame_end = _time_module.perf_counter()
        frame_cpu_us = (frame_end - frame_start) * 1_000_000.0
        self._frame_count += 1

        if frame_cpu_us > 0:
            self._current_fps = 1_000_000.0 / frame_cpu_us

        # Auto-quality adjustment
        self._adjust_quality()

        snapshot = FrameSnapshot(
            frame_id=self._frame_count,
            total_draw_commands=len(sorted_commands),
            total_draw_batches=len(batches),
            total_triangles=total_triangles,
            total_vertices=total_triangles * 3,
            state_changes=total_draw_calls,
            state_changes_saved=sum(b.state_changes_saved for b in batches),
            culled_commands=culled,
            visible_commands=len(sorted_commands),
            frame_cpu_us=frame_cpu_us,
            frame_gpu_us=frame_cpu_us * 0.7,
            pass_timings=pass_timings,
            active_lights=sum(1 for l in self._lights.list_lights() if l.enabled),
            shadow_maps_rendered=len(self._lights.list_shadow_maps()),
            post_effects_applied=len(pp_timings),
            resolution_scale=self._resolution_scale,
        )

        with self._lock:
            self._frame_snapshots.append(snapshot)
            if len(self._frame_snapshots) > self._max_snapshots:
                self._frame_snapshots = self._frame_snapshots[-self._max_snapshots:]

        return snapshot

    def _adjust_quality(self) -> None:
        """Dynamically adjust resolution scale to maintain target FPS."""
        if self._current_fps < self._target_fps * 0.75:
            self._resolution_scale = max(0.5, self._resolution_scale - 0.05)
            self._post_process.set_resolution_scale(self._resolution_scale)
        elif self._current_fps > self._target_fps * 1.3 and self._resolution_scale < 1.0:
            self._resolution_scale = min(1.0, self._resolution_scale + 0.02)
            self._post_process.set_resolution_scale(self._resolution_scale)

    # ---- Quality Management ----

    def set_quality(self, tier: QualityTier) -> None:
        """Set the global quality tier for the entire pipeline."""
        with self._lock:
            self._quality = tier
            self._post_process.set_quality(tier)
            # Adjust resolution scale based on quality
            scale_map = {
                QualityTier.PERFORMANCE: 0.5,
                QualityTier.BALANCED: 0.75,
                QualityTier.QUALITY: 1.0,
                QualityTier.CINEMATIC: 1.0,
            }
            self._resolution_scale = scale_map.get(tier, 1.0)

    def get_quality(self) -> QualityTier:
        """Get the current global quality tier."""
        with self._lock:
            return self._quality

    def set_target_fps(self, fps: int) -> None:
        """Set the target frame rate for auto-quality adjustment."""
        self._target_fps = max(15, min(240, fps))

    def get_target_fps(self) -> int:
        """Get the target frame rate."""
        return self._target_fps

    def set_clear_color(
        self, r: float, g: float, b: float, a: float = 1.0
    ) -> None:
        """Set the default clear color for the pipeline."""
        with self._lock:
            self._clear_color = (
                _clamp(r, 0.0, 1.0),
                _clamp(g, 0.0, 1.0),
                _clamp(b, 0.0, 1.0),
                _clamp(a, 0.0, 1.0),
            )

    # ---- Rendering Control ----

    def start_rendering(self) -> None:
        """Signal the pipeline to begin rendering."""
        self._is_rendering = True

    def stop_rendering(self) -> None:
        """Signal the pipeline to stop rendering."""
        self._is_rendering = False

    def is_rendering(self) -> bool:
        """Check if the pipeline is currently rendering."""
        return self._is_rendering

    # ---- Frame Statistics ----

    def get_latest_snapshot(self) -> Optional[FrameSnapshot]:
        """Get the most recent frame snapshot."""
        with self._lock:
            if self._frame_snapshots:
                return self._frame_snapshots[-1]
            return None

    def get_snapshot_history(self, count: int = 60) -> List[FrameSnapshot]:
        """Get recent frame snapshots."""
        with self._lock:
            return self._frame_snapshots[-count:]

    def get_average_stats(self) -> Dict[str, Any]:
        """Get averaged frame statistics over recent history."""
        with self._lock:
            if not self._frame_snapshots:
                return {}
            count = len(self._frame_snapshots)
            avg_fps = sum(s.frame_cpu_us for s in self._frame_snapshots) / count
            avg_fps = 1_000_000.0 / avg_fps if avg_fps > 0 else 0.0
            avg_draw_calls = sum(s.total_draw_commands for s in self._frame_snapshots) / count
            avg_batches = sum(s.total_draw_batches for s in self._frame_snapshots) / count
            avg_triangles = sum(s.total_triangles for s in self._frame_snapshots) / count
            avg_cpu_us = sum(s.frame_cpu_us for s in self._frame_snapshots) / count
            avg_gpu_us = sum(s.frame_gpu_us for s in self._frame_snapshots) / count
            avg_state_saved = sum(s.state_changes_saved for s in self._frame_snapshots) / count
            return {
                "average_fps": round(avg_fps, 1),
                "average_draw_commands": int(avg_draw_calls),
                "average_batches": int(avg_batches),
                "average_triangles": int(avg_triangles),
                "average_cpu_us": round(avg_cpu_us, 2),
                "average_gpu_us": round(avg_gpu_us, 2),
                "average_state_changes_saved": int(avg_state_saved),
                "frame_count": count,
                "frame_id": self._frame_count,
            }

    # ---- Comprehensive Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive pipeline statistics from all subsystems."""
        with self._lock:
            return {
                "frame_count": self._frame_count,
                "current_fps": round(self._current_fps, 1),
                "target_fps": self._target_fps,
                "quality": self._quality.value,
                "resolution_scale": round(self._resolution_scale, 2),
                "is_rendering": self._is_rendering,
                "clear_color": list(self._clear_color),
                "render_passes": len(self._passes),
                "enabled_passes": sum(1 for p in self._passes.values() if p.enabled),
                "average_stats": self.get_average_stats(),
                "materials": self._materials.get_stats(),
                "shaders": self._shaders.get_stats(),
                "render_queue": self._queue.get_stats(),
                "lighting": self._lights.get_stats(),
                "post_processing": self._post_process.get_stats(),
            }

    def get_subsystem_stats(self) -> Dict[str, Any]:
        """Get per-subsystem statistics."""
        return {
            "materials": self._materials.get_stats(),
            "shaders": self._shaders.get_stats(),
            "render_queue": self._queue.get_stats(),
            "lighting": self._lights.get_stats(),
            "post_processing": self._post_process.get_stats(),
        }

    # ---- Reset ----

    def reset(self) -> None:
        """Reset the entire render pipeline to initial state."""
        with self._lock:
            self._materials.reset()
            self._shaders.reset()
            self._queue.reset()
            self._lights.reset()
            self._post_process.reset()
            self._passes.clear()
            self._pass_order.clear()
            self._frame_snapshots.clear()
            self._quality = QualityTier.BALANCED
            self._resolution_scale = 1.0
            self._frame_count = 0
            self._current_fps = 60.0
            self._is_rendering = False
            self._init_default_passes()


# =============================================================================
# Module-Level Accessor
# =============================================================================

_render_pipeline: Optional[RenderPipeline] = None


def get_render_pipeline() -> RenderPipeline:
    """Get the singleton RenderPipeline instance.

    Returns:
        The global RenderPipeline singleton.
    """
    global _render_pipeline
    if _render_pipeline is None:
        _render_pipeline = RenderPipeline()
    return _render_pipeline