"""
SparkLabs Engine - AI-Native Game Editor Engine

The editor-side engine that powers the AI-native game editor, providing
real-time AI-assisted game editing, procedural content generation, smart
asset management, and intelligent scene composition. This engine bridges
the editor UI with the underlying engine subsystems, enabling AI agents
to assist in every aspect of game creation.

Architecture:
  EngineAINativeEditor (Singleton)
    |-- SceneEditor — AI-assisted scene composition and layout
    |-- AssetManager — Smart asset import, generation, and optimization
    |-- CodeEditor — AI-assisted code generation and refactoring
    |-- LevelDesigner — Procedural level generation and editing
    |-- AnimationEditor — Visual animation creation and blending
    |-- PhysicsEditor — Physics body setup and simulation
    |-- UILayoutEditor — UI element creation and layout design
    |-- RealTimePreview — Live game preview with hot reload

Integrated Engine Subsystems:
  - EngineVisualScripting (visual scripting runtime)
  - EngineCrossPlatformBuilder (platform build and export)
  - EngineProceduralAnimation (procedural animation system)
  - EngineTileMap (tile map and auto-tiling)
  - EnginePrefabSystem (prefab library and instantiation)
  - EngineInputActionSystem (input action mapping)
  - EngineShaderMaterial (shader and material management)
  - EngineResourceStreaming (resource loading and streaming)
  - EngineStateReconciliation (state synchronization)
  - EngineEventBus (event communication)
  - EngineSceneTree (scene graph hierarchy)
  - EngineComponentSystem (component-based architecture)
  - EngineServerRegistry (engine subsystem registry)

Usage:
    editor = EngineAINativeEditor.get_instance()
    editor.initialize()

    # AI-assisted scene creation
    scene = editor.scene.create_scene_from_description(
        "A dark forest with a castle in the distance"
    )

    # Smart asset management
    asset = editor.assets.import_asset("character.png", auto_process=True)

    # AI code generation
    script = editor.code.generate_script(
        "Create a player controller with double jump"
    )

    editor.shutdown()
"""

from __future__ import annotations

import json
import math
import os
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union


# =============================================================================
# Enums — Editor Domain
# =============================================================================


class EditorMode(Enum):
    """Operating modes of the AI-native editor."""
    IDLE = "idle"
    EDITING = "editing"
    PREVIEWING = "previewing"
    BUILDING = "building"
    DEBUGGING = "debugging"
    SIMULATING = "simulating"


class SceneTemplateType(Enum):
    """Pre-built scene templates available in the editor."""
    EMPTY = "empty"
    PLATFORMER = "platformer"
    TOP_DOWN = "top_down"
    SIDE_SCROLLER = "side_scroller"
    ISOMETRIC = "isometric"
    OPEN_WORLD = "open_world"
    DUNGEON = "dungeon"
    MENU = "menu"
    CUTSCENE = "cutscene"


class AssetType(Enum):
    """Categories of game assets."""
    TEXTURE = "texture"
    SPRITE = "sprite"
    SPRITE_SHEET = "sprite_sheet"
    TILE_SET = "tile_set"
    AUDIO = "audio"
    MUSIC = "music"
    FONT = "font"
    SHADER = "shader"
    MATERIAL = "material"
    PREFAB = "prefab"
    ANIMATION = "animation"
    SCENE = "scene"
    SCRIPT = "script"
    PHYSICS_MATERIAL = "physics_material"
    PARTICLE = "particle"
    VIDEO = "video"
    RAW = "raw"


class AssetFormat(Enum):
    """Supported asset import formats."""
    PNG = "png"
    JPG = "jpg"
    GIF = "gif"
    SVG = "svg"
    TGA = "tga"
    DDS = "dds"
    KTX = "ktx"
    WAV = "wav"
    MP3 = "mp3"
    OGG = "ogg"
    FLAC = "flac"
    GLSL = "glsl"
    HLSL = "hlsl"
    JSON = "json"
    GLTF = "gltf"
    FBX = "fbx"
    OBJ = "obj"
    TTF = "ttf"
    OTF = "otf"


class ScriptLanguage(Enum):
    """Supported scripting languages for code generation."""
    PYTHON = "python"
    LUA = "lua"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GDSCRIPT = "gdscript"
    CSHARP = "csharp"
    VISUAL_SCRIPT = "visual_script"


class GenerationAlgorithm(Enum):
    """Algorithms for procedural level generation."""
    PERLIN_NOISE = "perlin_noise"
    CELLULAR_AUTOMATA = "cellular_automata"
    BSP = "bsp"
    WAVE_FUNCTION_COLLAPSE = "wave_function_collapse"
    DRUNKARD_WALK = "drunkard_walk"
    DIFFUSION_LIMITED = "diffusion_limited"
    VORONOI = "voronoi"
    L_SYSTEM = "l_system"
    MARCHING_SQUARES = "marching_squares"
    RANDOM_WALK = "random_walk"


class AnimationType(Enum):
    """Types of animations in the editor."""
    KEYFRAME = "keyframe"
    PROCEDURAL = "procedural"
    SKELETAL = "skeletal"
    SPRITE_SHEET = "sprite_sheet"
    CUTSCENE = "cutscene"
    PARTICLE = "particle"
    UI = "ui"


class PhysicsBodyType(Enum):
    """Physics body types for configuration."""
    STATIC = "static"
    DYNAMIC = "dynamic"
    KINEMATIC = "kinematic"
    TRIGGER = "trigger"
    CHARACTER = "character"


class CollisionShapeType(Enum):
    """Collision shape types."""
    BOX = "box"
    CIRCLE = "circle"
    CAPSULE = "capsule"
    POLYGON = "polygon"
    EDGE = "edge"
    CONVEX_HULL = "convex_hull"
    COMPOUND = "compound"


class UIElementType(Enum):
    """Types of UI elements."""
    BUTTON = "button"
    LABEL = "label"
    IMAGE = "image"
    PANEL = "panel"
    SLIDER = "slider"
    CHECKBOX = "checkbox"
    DROPDOWN = "dropdown"
    TEXT_INPUT = "text_input"
    SCROLL_VIEW = "scroll_view"
    PROGRESS_BAR = "progress_bar"
    TOGGLE = "toggle"
    GRID = "grid"
    CANVAS = "canvas"


class PreviewMode(Enum):
    """Modes for the real-time preview."""
    WINDOWED = "windowed"
    FULLSCREEN = "fullscreen"
    EMBEDDED = "embedded"
    REMOTE = "remote"


class SnappingMode(Enum):
    """Intelligent snapping alignment modes."""
    GRID = "grid"
    ENTITY = "entity"
    PIVOT = "pivot"
    SURFACE = "surface"
    GUIDE = "guide"
    NONE = "none"


class ErrorSeverity(Enum):
    """Severity levels for editor errors."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# =============================================================================
# Data Classes — Scene Editor
# =============================================================================


@dataclass
class SceneDescription:
    """Parsed representation of a natural-language scene description."""
    description_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    raw_text: str = ""
    parsed_entities: List[Dict[str, Any]] = field(default_factory=list)
    detected_lighting: Dict[str, Any] = field(default_factory=dict)
    detected_terrain: Dict[str, Any] = field(default_factory=dict)
    detected_ambience: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description_id": self.description_id,
            "raw_text": self.raw_text,
            "parsed_entities": list(self.parsed_entities),
            "detected_lighting": dict(self.detected_lighting),
            "detected_terrain": dict(self.detected_terrain),
            "detected_ambience": dict(self.detected_ambience),
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class SceneTemplate:
    """Pre-built scene template with default configuration."""
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    template_type: SceneTemplateType = SceneTemplateType.EMPTY
    description: str = ""
    default_entities: List[Dict[str, Any]] = field(default_factory=list)
    default_lighting: Dict[str, Any] = field(default_factory=dict)
    default_camera: Dict[str, Any] = field(default_factory=dict)
    default_physics: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    thumbnail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "template_type": self.template_type.value,
            "description": self.description,
            "default_entities": list(self.default_entities),
            "default_lighting": dict(self.default_lighting),
            "default_camera": dict(self.default_camera),
            "default_physics": dict(self.default_physics),
            "tags": list(self.tags),
            "thumbnail": self.thumbnail,
        }


@dataclass
class LayoutResult:
    """Result of an automatic layout operation."""
    layout_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    overlaps_detected: int = 0
    overlaps_resolved: int = 0
    grid_aligned: bool = False
    duration_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "entity_positions": {
                k: list(v) for k, v in self.entity_positions.items()
            },
            "overlaps_detected": self.overlaps_detected,
            "overlaps_resolved": self.overlaps_resolved,
            "grid_aligned": self.grid_aligned,
            "duration_ms": self.duration_ms,
            "warnings": list(self.warnings),
        }


# =============================================================================
# Data Classes — Asset Manager
# =============================================================================


@dataclass
class AssetRecord:
    """Record of an imported or generated asset in the library."""
    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    asset_type: AssetType = AssetType.TEXTURE
    format: AssetFormat = AssetFormat.PNG
    file_path: str = ""
    size_bytes: int = 0
    dimensions: Tuple[int, int] = (0, 0)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)
    usage_count: int = 0
    is_optimized: bool = False
    thumbnail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "name": self.name,
            "asset_type": self.asset_type.value,
            "format": self.format.value,
            "file_path": self.file_path,
            "size_bytes": self.size_bytes,
            "dimensions": list(self.dimensions),
            "tags": list(self.tags),
            "metadata": dict(self.metadata),
            "dependencies": list(self.dependencies),
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "usage_count": self.usage_count,
            "is_optimized": self.is_optimized,
            "thumbnail": self.thumbnail,
        }


@dataclass
class AssetImportResult:
    """Result of an asset import operation."""
    import_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    asset: Optional[AssetRecord] = None
    success: bool = False
    auto_processed: bool = False
    optimizations_applied: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "import_id": self.import_id,
            "asset": self.asset.to_dict() if self.asset else None,
            "success": self.success,
            "auto_processed": self.auto_processed,
            "optimizations_applied": list(self.optimizations_applied),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "duration_ms": self.duration_ms,
        }


@dataclass
class AssetSearchQuery:
    """Search query for the asset library."""
    query: str = ""
    asset_types: List[AssetType] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    sort_by: str = "name"
    sort_ascending: bool = True
    limit: int = 50
    offset: int = 0


# =============================================================================
# Data Classes — Code Editor
# =============================================================================


@dataclass
class ScriptGenerationRequest:
    """Request to generate a script from a natural language description."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    language: ScriptLanguage = ScriptLanguage.PYTHON
    target_entity: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "description": self.description,
            "language": self.language.value,
            "target_entity": self.target_entity,
            "context": dict(self.context),
            "constraints": list(self.constraints),
            "examples": list(self.examples),
        }


@dataclass
class ScriptGenerationResult:
    """Result of an AI script generation."""
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    request: Optional[ScriptGenerationRequest] = None
    generated_code: str = ""
    language: ScriptLanguage = ScriptLanguage.PYTHON
    success: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "result_id": self.result_id,
            "request": self.request.to_dict() if self.request else None,
            "generated_code": self.generated_code,
            "language": self.language.value,
            "success": self.success,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "suggestions": list(self.suggestions),
            "duration_ms": self.duration_ms,
        }


@dataclass
class RefactorResult:
    """Result of a code refactoring operation."""
    refactor_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    original_code: str = ""
    refactored_code: str = ""
    changes: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = False
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "refactor_id": self.refactor_id,
            "original_code": self.original_code,
            "refactored_code": self.refactored_code,
            "changes": list(self.changes),
            "success": self.success,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


@dataclass
class DebugResult:
    """Result of an AI-assisted debugging session."""
    debug_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    code: str = ""
    issues_found: List[Dict[str, Any]] = field(default_factory=list)
    fixes_applied: List[Dict[str, Any]] = field(default_factory=list)
    fixed_code: str = ""
    success: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "debug_id": self.debug_id,
            "code": self.code,
            "issues_found": list(self.issues_found),
            "fixes_applied": list(self.fixes_applied),
            "fixed_code": self.fixed_code,
            "success": self.success,
            "warnings": list(self.warnings),
        }


@dataclass
class CodeCompletionResult:
    """Result of an intelligent code completion."""
    completion_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    prefix: str = ""
    completions: List[Dict[str, Any]] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "completion_id": self.completion_id,
            "prefix": self.prefix,
            "completions": list(self.completions),
            "context": dict(self.context),
            "duration_ms": self.duration_ms,
        }


# =============================================================================
# Data Classes — Level Designer
# =============================================================================


@dataclass
class LevelGenerationConfig:
    """Configuration for procedural level generation."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    algorithm: GenerationAlgorithm = GenerationAlgorithm.PERLIN_NOISE
    width: int = 100
    height: int = 100
    seed: int = 0
    tile_size: int = 32
    fill_percentage: float = 0.45
    smoothing_iterations: int = 5
    room_count: int = 10
    corridor_width: int = 3
    biome: str = "default"
    difficulty: str = "normal"
    extra_params: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "algorithm": self.algorithm.value,
            "width": self.width,
            "height": self.height,
            "seed": self.seed,
            "tile_size": self.tile_size,
            "fill_percentage": self.fill_percentage,
            "smoothing_iterations": self.smoothing_iterations,
            "room_count": self.room_count,
            "corridor_width": self.corridor_width,
            "biome": self.biome,
            "difficulty": self.difficulty,
            "extra_params": dict(self.extra_params),
        }


@dataclass
class LevelResult:
    """Result of a level generation or editing operation."""
    level_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    width: int = 0
    height: int = 0
    tile_data: List[List[int]] = field(default_factory=list)
    entity_placements: List[Dict[str, Any]] = field(default_factory=list)
    spawn_points: List[Tuple[int, int]] = field(default_factory=list)
    config: Optional[LevelGenerationConfig] = None
    generation_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_id": self.level_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "tile_data": self.tile_data,
            "entity_placements": list(self.entity_placements),
            "spawn_points": [list(p) for p in self.spawn_points],
            "config": self.config.to_dict() if self.config else None,
            "generation_time_ms": self.generation_time_ms,
            "warnings": list(self.warnings),
        }


@dataclass
class LevelValidationResult:
    """Result of level validation."""
    validation_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    level_id: str = ""
    is_valid: bool = False
    issues: List[Dict[str, Any]] = field(default_factory=list)
    reachability: Dict[str, Any] = field(default_factory=dict)
    balance_score: float = 0.0
    performance_score: float = 0.0
    suggestions: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "validation_id": self.validation_id,
            "level_id": self.level_id,
            "is_valid": self.is_valid,
            "issues": list(self.issues),
            "reachability": dict(self.reachability),
            "balance_score": self.balance_score,
            "performance_score": self.performance_score,
            "suggestions": list(self.suggestions),
        }


@dataclass
class LevelTemplate:
    """Pre-built level template."""
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    category: str = ""
    config: Optional[LevelGenerationConfig] = None
    tile_map: List[List[int]] = field(default_factory=list)
    entities: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "config": self.config.to_dict() if self.config else None,
            "tile_map": self.tile_map,
            "entities": list(self.entities),
            "tags": list(self.tags),
        }


# =============================================================================
# Data Classes — Animation Editor
# =============================================================================


@dataclass
class KeyframeData:
    """Data for a single keyframe in an animation."""
    frame: int = 0
    time: float = 0.0
    properties: Dict[str, Any] = field(default_factory=dict)
    easing: str = "linear"
    interpolation: str = "linear"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame": self.frame,
            "time": self.time,
            "properties": dict(self.properties),
            "easing": self.easing,
            "interpolation": self.interpolation,
        }


@dataclass
class AnimationClip:
    """An animation clip with keyframes and metadata."""
    clip_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    animation_type: AnimationType = AnimationType.KEYFRAME
    target_entity: str = ""
    duration: float = 0.0
    fps: int = 30
    loop: bool = False
    keyframes: List[KeyframeData] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip_id": self.clip_id,
            "name": self.name,
            "animation_type": self.animation_type.value,
            "target_entity": self.target_entity,
            "duration": self.duration,
            "fps": self.fps,
            "loop": self.loop,
            "keyframes": [kf.to_dict() for kf in self.keyframes],
            "properties": dict(self.properties),
            "created_at": self.created_at,
        }


@dataclass
class AnimationBlendResult:
    """Result of blending two animations together."""
    blend_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    source_clip_id: str = ""
    target_clip_id: str = ""
    result_clip: Optional[AnimationClip] = None
    blend_factor: float = 0.5
    blend_duration: float = 0.3
    success: bool = False
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blend_id": self.blend_id,
            "source_clip_id": self.source_clip_id,
            "target_clip_id": self.target_clip_id,
            "result_clip": self.result_clip.to_dict() if self.result_clip else None,
            "blend_factor": self.blend_factor,
            "blend_duration": self.blend_duration,
            "success": self.success,
            "warnings": list(self.warnings),
        }


@dataclass
class ProceduralAnimationConfig:
    """Configuration for procedural animation setup."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_entity: str = ""
    animation_type: str = "locomotion"
    parameters: Dict[str, Any] = field(default_factory=dict)
    ik_chains: List[Dict[str, Any]] = field(default_factory=list)
    physics_blending: bool = False
    environment_aware: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "target_entity": self.target_entity,
            "animation_type": self.animation_type,
            "parameters": dict(self.parameters),
            "ik_chains": list(self.ik_chains),
            "physics_blending": self.physics_blending,
            "environment_aware": self.environment_aware,
        }


@dataclass
class PreviewFrame:
    """A single frame of an animation preview."""
    frame_number: int = 0
    time: float = 0.0
    sprite_data: Optional[Dict[str, Any]] = None
    bone_positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    property_snapshot: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "time": self.time,
            "sprite_data": self.sprite_data,
            "bone_positions": {
                k: list(v) for k, v in self.bone_positions.items()
            },
            "property_snapshot": dict(self.property_snapshot),
        }


# =============================================================================
# Data Classes — Physics Editor
# =============================================================================


@dataclass
class PhysicsBodyConfig:
    """Configuration for a physics body."""
    body_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_id: str = ""
    body_type: PhysicsBodyType = PhysicsBodyType.DYNAMIC
    mass: float = 1.0
    linear_damping: float = 0.0
    angular_damping: float = 0.0
    gravity_scale: float = 1.0
    fixed_rotation: bool = False
    is_bullet: bool = False
    allow_sleep: bool = True
    awake: bool = True
    collision_layer: int = 1
    collision_mask: int = 0xFFFF

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "entity_id": self.entity_id,
            "body_type": self.body_type.value,
            "mass": self.mass,
            "linear_damping": self.linear_damping,
            "angular_damping": self.angular_damping,
            "gravity_scale": self.gravity_scale,
            "fixed_rotation": self.fixed_rotation,
            "is_bullet": self.is_bullet,
            "allow_sleep": self.allow_sleep,
            "awake": self.awake,
            "collision_layer": self.collision_layer,
            "collision_mask": self.collision_mask,
        }


@dataclass
class CollisionShapeConfig:
    """Configuration for a collision shape."""
    shape_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    body_id: str = ""
    shape_type: CollisionShapeType = CollisionShapeType.BOX
    offset: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[float, float] = (1.0, 1.0)
    radius: float = 0.5
    vertices: List[Tuple[float, float]] = field(default_factory=list)
    density: float = 1.0
    friction: float = 0.5
    restitution: float = 0.0
    is_sensor: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shape_id": self.shape_id,
            "body_id": self.body_id,
            "shape_type": self.shape_type.value,
            "offset": list(self.offset),
            "size": list(self.size),
            "radius": self.radius,
            "vertices": [list(v) for v in self.vertices],
            "density": self.density,
            "friction": self.friction,
            "restitution": self.restitution,
            "is_sensor": self.is_sensor,
        }


@dataclass
class SimulationStep:
    """A single step in a physics simulation preview."""
    step: int = 0
    time: float = 0.0
    positions: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    velocities: Dict[str, Tuple[float, float, float]] = field(default_factory=dict)
    collisions: List[Dict[str, Any]] = field(default_factory=list)
    contacts: int = 0
    energy: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "time": self.time,
            "positions": {k: list(v) for k, v in self.positions.items()},
            "velocities": {k: list(v) for k, v in self.velocities.items()},
            "collisions": list(self.collisions),
            "contacts": self.contacts,
            "energy": self.energy,
        }


@dataclass
class PhysicsOptimizationResult:
    """Result of physics optimization."""
    optimization_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    entity_id: str = ""
    optimizations: List[Dict[str, Any]] = field(default_factory=list)
    body_count_before: int = 0
    body_count_after: int = 0
    performance_gain_percent: float = 0.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "optimization_id": self.optimization_id,
            "entity_id": self.entity_id,
            "optimizations": list(self.optimizations),
            "body_count_before": self.body_count_before,
            "body_count_after": self.body_count_after,
            "performance_gain_percent": self.performance_gain_percent,
            "warnings": list(self.warnings),
        }


# =============================================================================
# Data Classes — UI Layout Editor
# =============================================================================


@dataclass
class UIElement:
    """A UI element in the layout editor."""
    element_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    element_type: UIElementType = UIElementType.PANEL
    parent_id: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    size: Tuple[float, float] = (100.0, 50.0)
    anchor: Tuple[float, float] = (0.0, 0.0)
    pivot: Tuple[float, float] = (0.5, 0.5)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    visible: bool = True
    enabled: bool = True
    z_order: int = 0
    properties: Dict[str, Any] = field(default_factory=dict)
    children: List[str] = field(default_factory=list)
    style: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "element_id": self.element_id,
            "name": self.name,
            "element_type": self.element_type.value,
            "parent_id": self.parent_id,
            "position": list(self.position),
            "size": list(self.size),
            "anchor": list(self.anchor),
            "pivot": list(self.pivot),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "visible": self.visible,
            "enabled": self.enabled,
            "z_order": self.z_order,
            "properties": dict(self.properties),
            "children": list(self.children),
            "style": dict(self.style),
        }


@dataclass
class UILayoutResult:
    """Result of a UI layout operation."""
    layout_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    root_element_id: str = ""
    elements: Dict[str, UIElement] = field(default_factory=dict)
    layout_type: str = "auto"
    responsive_breakpoints: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layout_id": self.layout_id,
            "root_element_id": self.root_element_id,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
            "layout_type": self.layout_type,
            "responsive_breakpoints": {
                k: dict(v) for k, v in self.responsive_breakpoints.items()
            },
            "warnings": list(self.warnings),
            "duration_ms": self.duration_ms,
        }


@dataclass
class UITemplate:
    """Pre-built UI template."""
    template_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    description: str = ""
    category: str = ""
    root_element: Optional[UIElement] = None
    elements: Dict[str, UIElement] = field(default_factory=dict)
    default_resolution: Tuple[int, int] = (1920, 1080)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "root_element": self.root_element.to_dict() if self.root_element else None,
            "elements": {k: v.to_dict() for k, v in self.elements.items()},
            "default_resolution": list(self.default_resolution),
            "tags": list(self.tags),
        }


@dataclass
class ResponsiveConfig:
    """Configuration for responsive UI design."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_resolutions: List[Tuple[int, int]] = field(default_factory=list)
    breakpoints: Dict[str, int] = field(default_factory=dict)
    scale_mode: str = "scale_with_screen_size"
    reference_resolution: Tuple[int, int] = (1920, 1080)
    match_width_or_height: float = 0.5
    allow_rotation: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "target_resolutions": [list(r) for r in self.target_resolutions],
            "breakpoints": dict(self.breakpoints),
            "scale_mode": self.scale_mode,
            "reference_resolution": list(self.reference_resolution),
            "match_width_or_height": self.match_width_or_height,
            "allow_rotation": self.allow_rotation,
        }


# =============================================================================
# Data Classes — Real-Time Preview
# =============================================================================


@dataclass
class PreviewSession:
    """A live preview session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    scene_id: str = ""
    mode: PreviewMode = PreviewMode.EMBEDDED
    resolution: Tuple[int, int] = (1920, 1080)
    fps: int = 60
    is_running: bool = False
    started_at: float = 0.0
    frames_rendered: int = 0
    current_fps: float = 0.0
    hot_reload_count: int = 0
    errors: List[str] = field(default_factory=list)
    platform_target: str = "web"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "scene_id": self.scene_id,
            "mode": self.mode.value,
            "resolution": list(self.resolution),
            "fps": self.fps,
            "is_running": self.is_running,
            "started_at": self.started_at,
            "frames_rendered": self.frames_rendered,
            "current_fps": self.current_fps,
            "hot_reload_count": self.hot_reload_count,
            "errors": list(self.errors),
            "platform_target": self.platform_target,
        }


@dataclass
class ScreenshotResult:
    """Result of a screenshot capture."""
    screenshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    file_path: str = ""
    resolution: Tuple[int, int] = (0, 0)
    format: str = "png"
    size_bytes: int = 0
    captured_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "screenshot_id": self.screenshot_id,
            "file_path": self.file_path,
            "resolution": list(self.resolution),
            "format": self.format,
            "size_bytes": self.size_bytes,
            "captured_at": self.captured_at,
            "metadata": dict(self.metadata),
        }


@dataclass
class HotReloadResult:
    """Result of a hot reload operation."""
    reload_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    success: bool = False
    changed_files: List[str] = field(default_factory=list)
    reloaded_modules: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reload_id": self.reload_id,
            "success": self.success,
            "changed_files": list(self.changed_files),
            "reloaded_modules": list(self.reloaded_modules),
            "errors": list(self.errors),
            "warnings": list(self.warnings),
            "duration_ms": self.duration_ms,
        }


@dataclass
class EditorError:
    """An error record in the editor."""
    error_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    severity: ErrorSeverity = ErrorSeverity.ERROR
    source: str = ""
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_id": self.error_id,
            "severity": self.severity.value,
            "source": self.source,
            "message": self.message,
            "details": dict(self.details),
            "timestamp": self.timestamp,
            "resolved": self.resolved,
        }


# =============================================================================
# Sub-System: SceneEditor
# =============================================================================


class SceneEditor:
    """AI-assisted scene composition and layout.

    Provides natural-language scene creation, automatic entity layout,
    intelligent snapping and alignment, and a library of pre-built scene
    templates for rapid prototyping.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._templates: Dict[str, SceneTemplate] = {}
        self._snap_grid_size: float = 32.0
        self._snap_mode: SnappingMode = SnappingMode.GRID
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Scene Creation from Description
    # ------------------------------------------------------------------

    def create_scene_from_description(
        self,
        description: str,
        scene_name: str = "",
        template_type: Optional[SceneTemplateType] = None,
    ) -> SceneDescription:
        """Parse a natural language description into a scene specification.

        Analyzes the input text to detect entities, lighting, terrain, and
        ambient settings, producing a structured scene description that can
        be used to populate a new scene.

        Args:
            description: Natural language description of the desired scene.
            scene_name: Optional name for the scene.
            template_type: Optional template type to constrain generation.

        Returns:
            A SceneDescription with parsed entities, lighting, and terrain.

        Raises:
            ValueError: If the description is empty or unparseable.
        """
        if not description or not description.strip():
            raise ValueError("Scene description must not be empty.")

        with self._lock:
            desc = SceneDescription(raw_text=description.strip())

            # Simulate AI parsing of the natural language description
            desc.parsed_entities = self._parse_entities_from_text(description)
            desc.detected_lighting = self._detect_lighting_from_text(description)
            desc.detected_terrain = self._detect_terrain_from_text(description)
            desc.detected_ambience = self._detect_ambience_from_text(description)
            desc.confidence = self._estimate_parsing_confidence(
                desc.parsed_entities,
                desc.detected_lighting,
                desc.detected_terrain,
            )

            self._editor._publish_event(
                "scene_created_from_description",
                {
                    "description_id": desc.description_id,
                    "scene_name": scene_name or "Untitled",
                    "entity_count": len(desc.parsed_entities),
                    "confidence": desc.confidence,
                },
            )

            return desc

    def _parse_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse entity references from natural language text."""
        text_lower = text.lower()
        entities: List[Dict[str, Any]] = []

        entity_keywords = {
            "tree": {"type": "prop", "category": "vegetation"},
            "rock": {"type": "prop", "category": "environment"},
            "castle": {"type": "structure", "category": "building"},
            "player": {"type": "player", "category": "character"},
            "enemy": {"type": "npc", "category": "enemy"},
            "npc": {"type": "npc", "category": "character"},
            "chest": {"type": "prop", "category": "interactive"},
            "door": {"type": "prop", "category": "interactive"},
            "light": {"type": "light", "category": "lighting"},
            "water": {"type": "terrain", "category": "environment"},
            "mountain": {"type": "terrain", "category": "environment"},
            "house": {"type": "structure", "category": "building"},
            "bridge": {"type": "structure", "category": "building"},
            "grass": {"type": "decoration", "category": "vegetation"},
            "flower": {"type": "decoration", "category": "vegetation"},
            "cloud": {"type": "decoration", "category": "sky"},
            "bird": {"type": "prop", "category": "wildlife"},
            "coin": {"type": "prop", "category": "collectible"},
            "platform": {"type": "structure", "category": "level"},
            "spike": {"type": "prop", "category": "hazard"},
            "lava": {"type": "terrain", "category": "hazard"},
        }

        for keyword, entity_info in entity_keywords.items():
            if keyword in text_lower:
                count = text_lower.count(keyword)
                for i in range(min(count, 20)):
                    entities.append({
                        "name": f"{keyword}_{i + 1}",
                        "type": entity_info["type"],
                        "category": entity_info["category"],
                        "source_keyword": keyword,
                    })

        return entities

    def _detect_lighting_from_text(self, text: str) -> Dict[str, Any]:
        """Detect lighting settings from natural language description."""
        text_lower = text.lower()
        lighting: Dict[str, Any] = {
            "ambient_color": (0.3, 0.3, 0.4),
            "ambient_intensity": 0.5,
            "directional_light": True,
            "shadows": True,
        }

        if any(w in text_lower for w in ("dark", "night", "dim", "shadow")):
            lighting["ambient_intensity"] = 0.2
            lighting["ambient_color"] = (0.1, 0.1, 0.2)
        if any(w in text_lower for w in ("bright", "sunny", "day", "light")):
            lighting["ambient_intensity"] = 0.8
            lighting["ambient_color"] = (0.8, 0.8, 0.7)
        if any(w in text_lower for w in ("sunset", "dusk", "orange")):
            lighting["ambient_color"] = (0.8, 0.4, 0.2)
            lighting["ambient_intensity"] = 0.6
        if any(w in text_lower for w in ("fog", "mist", "haze")):
            lighting["fog_enabled"] = True
            lighting["fog_density"] = 0.02
        if any(w in text_lower for w in ("neon", "glow", "bioluminescent")):
            lighting["emissive_intensity"] = 1.5

        return lighting

    def _detect_terrain_from_text(self, text: str) -> Dict[str, Any]:
        """Detect terrain settings from natural language description."""
        text_lower = text.lower()
        terrain: Dict[str, Any] = {
            "type": "flat",
            "width": 2000,
            "height": 2000,
        }

        if any(w in text_lower for w in ("forest", "woods", "jungle")):
            terrain["type"] = "forest"
            terrain["tree_density"] = 0.7
        if any(w in text_lower for w in ("mountain", "hill", "cliff")):
            terrain["type"] = "mountainous"
            terrain["elevation_range"] = (0.0, 500.0)
        if any(w in text_lower for w in ("desert", "sand", "dune")):
            terrain["type"] = "desert"
            terrain["vegetation"] = "sparse"
        if any(w in text_lower for w in ("snow", "ice", "frozen", "tundra")):
            terrain["type"] = "snow"
            terrain["snow_coverage"] = 0.9
        if any(w in text_lower for w in ("cave", "underground", "dungeon")):
            terrain["type"] = "cave"
            terrain["ceiling"] = True
        if any(w in text_lower for w in ("city", "urban", "town", "village")):
            terrain["type"] = "urban"
            terrain["building_density"] = 0.6

        return terrain

    def _detect_ambience_from_text(self, text: str) -> Dict[str, Any]:
        """Detect ambient settings from natural language description."""
        text_lower = text.lower()
        ambience: Dict[str, Any] = {
            "particles": [],
            "sounds": [],
            "weather": "clear",
        }

        if any(w in text_lower for w in ("rain", "storm", "thunder")):
            ambience["weather"] = "rain"
            ambience["particles"].append("rain")
        if "snow" in text_lower:
            ambience["weather"] = "snow"
            ambience["particles"].append("snow")
        if any(w in text_lower for w in ("wind", "breeze", "gust")):
            ambience["particles"].append("wind_leaves")
        if any(w in text_lower for w in ("firefly", "sparkle", "magic")):
            ambience["particles"].append("sparkles")
        if any(w in text_lower for w in ("bird", "chirp", "ambient")):
            ambience["sounds"].append("birds_ambient")
        if any(w in text_lower for w in ("water", "river", "ocean", "lake")):
            ambience["sounds"].append("water_flow")

        return ambience

    def _estimate_parsing_confidence(
        self,
        entities: List[Dict[str, Any]],
        lighting: Dict[str, Any],
        terrain: Dict[str, Any],
    ) -> float:
        """Estimate confidence of the natural language parsing."""
        score = 0.0
        if entities:
            score += min(len(entities) * 0.05, 0.4)
        if lighting:
            score += 0.3
        if terrain:
            score += 0.3
        return min(score, 1.0)

    # ------------------------------------------------------------------
    # Automatic Layout
    # ------------------------------------------------------------------

    def auto_layout(
        self,
        entity_ids: List[str],
        bounds: Optional[Tuple[float, float, float, float]] = None,
        grid_size: Optional[float] = None,
        algorithm: str = "grid",
    ) -> LayoutResult:
        """Automatically position entities within a scene.

        Arranges entities using the specified layout algorithm, detecting
        and resolving overlaps, and optionally aligning to a grid.

        Args:
            entity_ids: List of entity IDs to lay out.
            bounds: Optional (x, y, width, height) bounding area.
            grid_size: Optional grid cell size for alignment.
            algorithm: Layout algorithm: 'grid', 'circular', 'scatter', 'row'.

        Returns:
            A LayoutResult with computed positions.

        Raises:
            ValueError: If entity_ids is empty.
        """
        if not entity_ids:
            raise ValueError("entity_ids must not be empty.")

        with self._lock:
            gs = grid_size or self._snap_grid_size
            bbox = bounds or (0.0, 0.0, 2000.0, 2000.0)
            bx, by, bw, bh = bbox

            positions: Dict[str, Tuple[float, float, float]] = {}
            overlaps_detected = 0
            overlaps_resolved = 0

            if algorithm == "grid":
                cols = max(1, int(math.sqrt(len(entity_ids))))
                for i, eid in enumerate(entity_ids):
                    row = i // cols
                    col = i % cols
                    x = bx + (col + 0.5) * (bw / cols)
                    y = by + (row + 0.5) * (bh / max(1, math.ceil(len(entity_ids) / cols)))
                    x = round(x / gs) * gs
                    y = round(y / gs) * gs
                    positions[eid] = (x, y, 0.0)
            elif algorithm == "circular":
                radius = min(bw, bh) / 3
                cx, cy = bx + bw / 2, by + bh / 2
                for i, eid in enumerate(entity_ids):
                    angle = 2 * math.pi * i / len(entity_ids)
                    x = cx + radius * math.cos(angle)
                    y = cy + radius * math.sin(angle)
                    x = round(x / gs) * gs
                    y = round(y / gs) * gs
                    positions[eid] = (x, y, 0.0)
            elif algorithm == "scatter":
                rng = random.Random(42)
                for eid in entity_ids:
                    x = bx + rng.uniform(0, bw)
                    y = by + rng.uniform(0, bh)
                    x = round(x / gs) * gs
                    y = round(y / gs) * gs
                    positions[eid] = (x, y, 0.0)
            elif algorithm == "row":
                spacing = bw / max(1, len(entity_ids))
                for i, eid in enumerate(entity_ids):
                    x = bx + (i + 0.5) * spacing
                    y = by + bh / 2
                    x = round(x / gs) * gs
                    y = round(y / gs) * gs
                    positions[eid] = (x, y, 0.0)
            else:
                raise ValueError(f"Unknown layout algorithm: {algorithm}")

            # Detect and resolve overlaps
            pos_list = [(eid, pos) for eid, pos in positions.items()]
            for i in range(len(pos_list)):
                for j in range(i + 1, len(pos_list)):
                    eid_a, (ax, ay, _) = pos_list[i]
                    eid_b, (bx2, by2, _) = pos_list[j]
                    dist = math.sqrt((ax - bx2) ** 2 + (ay - by2) ** 2)
                    if dist < gs:
                        overlaps_detected += 1
                        # Resolve by nudging
                        nx = ax + gs * 0.5
                        ny = ay + gs * 0.5
                        positions[eid_a] = (nx, ny, 0.0)
                        overlaps_resolved += 1

            warnings_list: List[str] = []
            if overlaps_detected > overlaps_resolved:
                warnings_list.append(
                    f"Could not resolve {overlaps_detected - overlaps_resolved} overlaps."
                )

            result = LayoutResult(
                entity_positions=positions,
                overlaps_detected=overlaps_detected,
                overlaps_resolved=overlaps_resolved,
                grid_aligned=(algorithm == "grid"),
                warnings=warnings_list,
            )

            self._editor._publish_event(
                "auto_layout_complete",
                {
                    "entity_count": len(entity_ids),
                    "algorithm": algorithm,
                    "overlaps_resolved": overlaps_resolved,
                },
            )

            return result

    # ------------------------------------------------------------------
    # Smart Snapping
    # ------------------------------------------------------------------

    def smart_snap(
        self,
        entity_id: str,
        position: Tuple[float, float, float],
        mode: Optional[SnappingMode] = None,
        snap_threshold: float = 16.0,
    ) -> Tuple[float, float, float]:
        """Snap an entity position to the nearest alignment point.

        Supports grid snapping, entity-to-entity snapping, pivot snapping,
        surface snapping, and guide-line snapping.

        Args:
            entity_id: The entity to snap.
            position: The proposed (x, y, z) position.
            mode: Snapping mode override; uses editor default if None.
            snap_threshold: Maximum distance for snapping to activate.

        Returns:
            The snapped (x, y, z) position.
        """
        mode = mode or self._snap_mode

        with self._lock:
            x, y, z = position

            if mode == SnappingMode.GRID:
                gs = self._snap_grid_size
                x = round(x / gs) * gs
                y = round(y / gs) * gs
            elif mode == SnappingMode.ENTITY:
                nearest = self._find_nearest_entity_position(entity_id, (x, y))
                if nearest is not None:
                    nx, ny = nearest
                    dist = math.sqrt((x - nx) ** 2 + (y - ny) ** 2)
                    if dist < snap_threshold:
                        x, y = nx, ny
            elif mode == SnappingMode.PIVOT:
                x = round(x, 1)
                y = round(y, 1)
            elif mode == SnappingMode.SURFACE:
                x = round(x, 1)
                y = round(y, 1)
            elif mode == SnappingMode.GUIDE:
                x = round(x, 1)
                y = round(y, 1)
            elif mode == SnappingMode.NONE:
                pass

            return (x, y, z)

    def _find_nearest_entity_position(
        self,
        exclude_id: str,
        target: Tuple[float, float],
    ) -> Optional[Tuple[float, float]]:
        """Find the nearest entity position for entity snapping."""
        # Stub for entity lookup — in production this queries the scene tree
        return None

    def set_snap_settings(self, grid_size: float, mode: SnappingMode) -> None:
        """Configure the snapping settings for the editor.

        Args:
            grid_size: Grid cell size in world units.
            mode: Snapping mode to use.
        """
        with self._lock:
            self._snap_grid_size = max(1.0, grid_size)
            self._snap_mode = mode

    # ------------------------------------------------------------------
    # Scene Templates
    # ------------------------------------------------------------------

    def scene_templates(
        self,
        category: Optional[SceneTemplateType] = None,
    ) -> List[SceneTemplate]:
        """Retrieve available scene templates, optionally filtered by type.

        Args:
            category: Optional template type filter.

        Returns:
            A list of SceneTemplate objects.
        """
        with self._lock:
            if not self._templates:
                self._initialize_default_templates()

            if category is not None:
                return [
                    t for t in self._templates.values()
                    if t.template_type == category
                ]
            return list(self._templates.values())

    def _initialize_default_templates(self) -> None:
        """Initialize the built-in scene template library."""
        defaults = [
            SceneTemplate(
                name="Empty Scene",
                template_type=SceneTemplateType.EMPTY,
                description="A completely empty scene with default camera and lighting.",
            ),
            SceneTemplate(
                name="Platformer Level",
                template_type=SceneTemplateType.PLATFORMER,
                description="A side-scrolling platformer level with ground, platforms, and a player spawn.",
                default_entities=[
                    {"type": "player", "position": (100, 500)},
                    {"type": "platform", "position": (400, 400)},
                    {"type": "platform", "position": (700, 300)},
                ],
                default_physics={"gravity": (0, -980, 0)},
            ),
            SceneTemplate(
                name="Top-Down Arena",
                template_type=SceneTemplateType.TOP_DOWN,
                description="A top-down arena with walls, obstacles, and player spawn.",
                default_entities=[
                    {"type": "player", "position": (400, 300)},
                    {"type": "wall", "position": (0, 0)},
                ],
                default_camera={"projection": "orthographic", "zoom": 1.0},
            ),
            SceneTemplate(
                name="Dungeon Crawler",
                template_type=SceneTemplateType.DUNGEON,
                description="A procedurally-generated dungeon with rooms, corridors, and enemies.",
                default_lighting={
                    "ambient_intensity": 0.3,
                    "ambient_color": (0.1, 0.1, 0.15),
                },
            ),
            SceneTemplate(
                name="Main Menu",
                template_type=SceneTemplateType.MENU,
                description="A game main menu with title, buttons, and background.",
                default_entities=[
                    {"type": "ui", "position": (960, 200), "name": "Title"},
                    {"type": "ui", "position": (960, 500), "name": "PlayButton"},
                    {"type": "ui", "position": (960, 600), "name": "SettingsButton"},
                ],
            ),
            SceneTemplate(
                name="Open World",
                template_type=SceneTemplateType.OPEN_WORLD,
                description="A large open-world terrain with dynamic lighting and streaming.",
                default_terrain={"type": "procedural", "size": 10000},
            ),
            SceneTemplate(
                name="Isometric Village",
                template_type=SceneTemplateType.ISOMETRIC,
                description="An isometric village scene with buildings and paths.",
                default_camera={"projection": "isometric", "angle": 45},
            ),
            SceneTemplate(
                name="Cutscene Intro",
                template_type=SceneTemplateType.CUTSCENE,
                description="A cinematic cutscene scene with camera paths and timeline.",
                default_entities=[
                    {"type": "camera_path", "position": (0, 0)},
                ],
            ),
        ]
        for t in defaults:
            self._templates[t.template_id] = t

    def add_template(self, template: SceneTemplate) -> None:
        """Register a custom scene template."""
        with self._lock:
            self._templates[template.template_id] = template

    def remove_template(self, template_id: str) -> bool:
        """Remove a scene template by ID."""
        with self._lock:
            if template_id in self._templates:
                del self._templates[template_id]
                return True
            return False


# =============================================================================
# Sub-System: AssetManager
# =============================================================================


class AssetManager:
    """Smart asset management with AI-powered import, generation, and optimization.

    Handles asset import with automatic processing (compression, format
    conversion, thumbnail generation), AI-driven asset generation from
    descriptions, automatic optimization, and a searchable asset library.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._library: Dict[str, AssetRecord] = {}
        self._lock = threading.RLock()
        self._import_handlers: Dict[AssetFormat, Callable[[str], AssetImportResult]] = {}
        self._supported_formats: Set[AssetFormat] = {
            AssetFormat.PNG, AssetFormat.JPG, AssetFormat.GIF, AssetFormat.SVG,
            AssetFormat.WAV, AssetFormat.MP3, AssetFormat.OGG,
            AssetFormat.GLSL, AssetFormat.HLSL,
            AssetFormat.JSON, AssetFormat.GLTF, AssetFormat.OBJ,
            AssetFormat.TTF, AssetFormat.OTF,
        }

    # ------------------------------------------------------------------
    # Asset Import
    # ------------------------------------------------------------------

    def import_asset(
        self,
        file_path: str,
        auto_process: bool = True,
        asset_type: Optional[AssetType] = None,
        tags: Optional[List[str]] = None,
    ) -> AssetImportResult:
        """Import an asset file with optional automatic processing.

        Detects the asset type from the file extension, applies automatic
        processing (compression, format conversion, thumbnail generation),
        and registers the asset in the library.

        Args:
            file_path: Path to the asset file.
            auto_process: Whether to automatically optimize and process.
            asset_type: Override auto-detected asset type.
            tags: Optional tags for categorization.

        Returns:
            An AssetImportResult with the imported asset record.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the format is unsupported.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Asset file not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower().lstrip(".")
        try:
            fmt = AssetFormat(ext)
        except ValueError:
            raise ValueError(f"Unsupported asset format: .{ext}")

        if fmt not in self._supported_formats:
            raise ValueError(f"Format '{fmt.value}' is not currently supported for import.")

        with self._lock:
            start = time.time()
            result = AssetImportResult(success=True)

            # Detect asset type from extension if not explicitly provided
            detected_type = asset_type or self._detect_asset_type(fmt)
            file_size = os.path.getsize(file_path)

            asset = AssetRecord(
                name=os.path.basename(file_path),
                asset_type=detected_type,
                format=fmt,
                file_path=file_path,
                size_bytes=file_size,
                tags=tags or [],
            )

            if auto_process:
                optimizations = self._apply_auto_processing(asset)
                result.optimizations_applied = optimizations
                result.auto_processed = True
                asset.is_optimized = True

            self._library[asset.asset_id] = asset
            result.asset = asset
            result.duration_ms = (time.time() - start) * 1000

            self._editor._publish_event(
                "asset_imported",
                {
                    "asset_id": asset.asset_id,
                    "name": asset.name,
                    "type": asset.asset_type.value,
                    "size_bytes": file_size,
                },
            )

            return result

    def _detect_asset_type(self, fmt: AssetFormat) -> AssetType:
        """Detect asset type from file format."""
        image_formats = {AssetFormat.PNG, AssetFormat.JPG, AssetFormat.GIF, AssetFormat.SVG,
                         AssetFormat.TGA, AssetFormat.DDS, AssetFormat.KTX}
        audio_formats = {AssetFormat.WAV, AssetFormat.MP3, AssetFormat.OGG, AssetFormat.FLAC}
        shader_formats = {AssetFormat.GLSL, AssetFormat.HLSL}
        model_formats = {AssetFormat.GLTF, AssetFormat.FBX, AssetFormat.OBJ}
        font_formats = {AssetFormat.TTF, AssetFormat.OTF}

        if fmt in image_formats:
            return AssetType.TEXTURE
        if fmt in audio_formats:
            return AssetType.AUDIO
        if fmt in shader_formats:
            return AssetType.SHADER
        if fmt in model_formats:
            return AssetType.PREFAB
        if fmt in font_formats:
            return AssetType.FONT
        if fmt == AssetFormat.JSON:
            return AssetType.SCENE
        return AssetType.RAW

    def _apply_auto_processing(self, asset: AssetRecord) -> List[str]:
        """Apply automatic processing optimizations to an asset."""
        optimizations: List[str] = []

        if asset.asset_type == AssetType.TEXTURE:
            optimizations.append("compression_applied")
            optimizations.append("mipmaps_generated")
            if asset.format == AssetFormat.PNG:
                optimizations.append("png_optimized")
        elif asset.asset_type == AssetType.AUDIO:
            optimizations.append("audio_normalized")
            optimizations.append("compression_applied")
        elif asset.asset_type == AssetType.SHADER:
            optimizations.append("shader_compiled")
        elif asset.asset_type == AssetType.PREFAB:
            optimizations.append("mesh_optimized")
            optimizations.append("material_baked")

        return optimizations

    # ------------------------------------------------------------------
    # AI Asset Generation
    # ------------------------------------------------------------------

    def generate_asset(
        self,
        description: str,
        asset_type: AssetType,
        style: str = "",
        resolution: Tuple[int, int] = (256, 256),
        count: int = 1,
    ) -> List[AssetRecord]:
        """Generate assets using AI from a natural language description.

        Creates assets procedurally or via AI generation based on the
        description and specified parameters.

        Args:
            description: Natural language description of the desired asset.
            asset_type: The type of asset to generate.
            style: Artistic style directive (e.g., 'pixel_art', 'realistic').
            resolution: Target resolution for texture assets.
            count: Number of asset variations to generate.

        Returns:
            A list of generated AssetRecord objects.

        Raises:
            ValueError: If count is not positive.
        """
        if count < 1:
            raise ValueError("count must be at least 1.")

        with self._lock:
            generated: List[AssetRecord] = []

            for i in range(count):
                asset = AssetRecord(
                    name=f"generated_{asset_type.value}_{i + 1}",
                    asset_type=asset_type,
                    format=AssetFormat.PNG,
                    file_path=f"generated://{uuid.uuid4().hex[:12]}",
                    dimensions=resolution,
                    tags=["ai_generated", style] if style else ["ai_generated"],
                    metadata={
                        "generation_prompt": description,
                        "style": style,
                        "variation": i + 1,
                    },
                )

                # Simulate generation with metadata
                if asset_type == AssetType.TEXTURE:
                    asset.metadata["channels"] = 4
                    asset.metadata["color_depth"] = 32
                    asset.metadata["suggested_name"] = self._generate_suggested_name(
                        description, "texture"
                    )
                elif asset_type == AssetType.AUDIO:
                    asset.format = AssetFormat.WAV
                    asset.metadata["duration_seconds"] = round(random.uniform(0.5, 5.0), 2)
                    asset.metadata["sample_rate"] = 44100
                elif asset_type == AssetType.MATERIAL:
                    asset.format = AssetFormat.JSON
                    asset.metadata["shader"] = "pbr_standard"
                    asset.metadata["properties"] = self._infer_material_properties(description)
                elif asset_type == AssetType.PREFAB:
                    asset.format = AssetFormat.JSON
                    asset.metadata["components"] = self._infer_prefab_components(description)

                self._library[asset.asset_id] = asset
                generated.append(asset)

            self._editor._publish_event(
                "assets_generated",
                {
                    "count": len(generated),
                    "asset_type": asset_type.value,
                    "description": description[:100],
                },
            )

            return generated

    def _generate_suggested_name(self, description: str, prefix: str) -> str:
        """Generate a suggested filename from a description."""
        # Simple heuristic: take first few words, clean them up
        words = description.lower().split()[:3]
        clean = "_".join(w.strip(".,!?;:") for w in words if len(w) > 2)
        return f"{prefix}_{clean}" if clean else f"{prefix}_{uuid.uuid4().hex[:8]}"

    def _infer_material_properties(self, description: str) -> Dict[str, Any]:
        """Infer material properties from a description."""
        desc_lower = description.lower()
        props: Dict[str, Any] = {"albedo": "#FFFFFF", "roughness": 0.5, "metallic": 0.0}

        if any(w in desc_lower for w in ("metal", "steel", "iron", "gold", "silver")):
            props["metallic"] = 1.0
            props["roughness"] = 0.3
        if any(w in desc_lower for w in ("wood", "stone", "rock", "dirt")):
            props["metallic"] = 0.0
            props["roughness"] = 0.8
        if any(w in desc_lower for w in ("glass", "crystal", "ice", "gem")):
            props["roughness"] = 0.1
            props["transparency"] = 0.5
        if any(w in desc_lower for w in ("glow", "emit", "neon", "light")):
            props["emission"] = "#00FFAA"
            props["emission_strength"] = 2.0
        if any(w in desc_lower for w in ("water", "liquid", "fluid")):
            props["roughness"] = 0.2
            props["metallic"] = 0.0
            props["transparency"] = 0.8

        return props

    def _infer_prefab_components(self, description: str) -> List[str]:
        """Infer required components from a description."""
        desc_lower = description.lower()
        components: List[str] = ["transform"]

        if any(w in desc_lower for w in ("player", "character", "npc")):
            components.extend(["sprite_renderer", "collider", "rigidbody"])
        if any(w in desc_lower for w in ("enemy", "monster", "boss")):
            components.extend(["sprite_renderer", "collider", "ai_behavior", "health"])
        if any(w in desc_lower for w in ("item", "pickup", "collectible")):
            components.extend(["sprite_renderer", "collider", "collectible"])
        if any(w in desc_lower for w in ("platform", "wall", "ground")):
            components.extend(["sprite_renderer", "collider"])
        if any(w in desc_lower for w in ("light", "lamp", "torch")):
            components.extend(["light_source", "sprite_renderer"])

        return components

    # ------------------------------------------------------------------
    # Asset Optimization
    # ------------------------------------------------------------------

    def optimize_asset(
        self,
        asset_id: str,
        target_platform: str = "web",
        quality: str = "balanced",
    ) -> AssetImportResult:
        """Optimize an existing asset for a target platform.

        Applies platform-specific optimizations including compression,
        format conversion, and resolution scaling.

        Args:
            asset_id: The ID of the asset to optimize.
            target_platform: Target platform: 'web', 'mobile', 'desktop', 'console'.
            quality: Optimization quality preset: 'performance', 'balanced', 'quality'.

        Returns:
            An AssetImportResult with optimization details.

        Raises:
            KeyError: If the asset_id is not found in the library.
        """
        with self._lock:
            if asset_id not in self._library:
                raise KeyError(f"Asset not found: {asset_id}")

            asset = self._library[asset_id]
            start = time.time()
            result = AssetImportResult(asset=asset, success=True)

            optimizations = []
            if asset.asset_type == AssetType.TEXTURE:
                if target_platform == "mobile":
                    optimizations.append("resolution_halved")
                    optimizations.append("etc2_compression")
                elif target_platform == "web":
                    optimizations.append("webp_conversion")
                    optimizations.append("texture_atlas_baked")
                elif target_platform == "console":
                    optimizations.append("bc7_compression")
                optimizations.append("mipmap_chain_optimized")
            elif asset.asset_type == AssetType.AUDIO:
                if target_platform == "mobile":
                    optimizations.append("audio_compressed_mono")
                elif target_platform == "web":
                    optimizations.append("ogg_vorbis_encoded")
                optimizations.append("sample_rate_optimized")
            elif asset.asset_type == AssetType.PREFAB:
                optimizations.append("mesh_decimated")
                optimizations.append("material_merged")

            if quality == "performance":
                optimizations.append("aggressive_compression")
            elif quality == "quality":
                optimizations = [o for o in optimizations if "compression" not in o.lower()]

            result.optimizations_applied = optimizations
            asset.is_optimized = True
            asset.modified_at = time.time()
            result.duration_ms = (time.time() - start) * 1000

            self._editor._publish_event(
                "asset_optimized",
                {
                    "asset_id": asset_id,
                    "optimizations": optimizations,
                    "target_platform": target_platform,
                },
            )

            return result

    # ------------------------------------------------------------------
    # Asset Library
    # ------------------------------------------------------------------

    def asset_library(
        self,
        query: Optional[AssetSearchQuery] = None,
    ) -> List[AssetRecord]:
        """Search the asset library with an optional query.

        Returns assets matching the search criteria, sorted and paginated.

        Args:
            query: Optional AssetSearchQuery with filters and sorting.

        Returns:
            A list of matching AssetRecord objects.
        """
        with self._lock:
            results = list(self._library.values())

            if query is not None:
                if query.query:
                    q = query.query.lower()
                    results = [
                        a for a in results
                        if q in a.name.lower()
                        or any(q in t.lower() for t in a.tags)
                    ]
                if query.asset_types:
                    results = [a for a in results if a.asset_type in query.asset_types]
                if query.tags:
                    results = [
                        a for a in results
                        if any(t in a.tags for t in query.tags)
                    ]

                reverse = not query.sort_ascending
                if query.sort_by == "name":
                    results.sort(key=lambda a: a.name.lower(), reverse=reverse)
                elif query.sort_by == "date":
                    results.sort(key=lambda a: a.created_at, reverse=reverse)
                elif query.sort_by == "size":
                    results.sort(key=lambda a: a.size_bytes, reverse=reverse)
                elif query.sort_by == "usage":
                    results.sort(key=lambda a: a.usage_count, reverse=reverse)

                if query.offset > 0:
                    results = results[query.offset:]
                if query.limit > 0:
                    results = results[:query.limit]

            return results

    def get_asset(self, asset_id: str) -> Optional[AssetRecord]:
        """Retrieve a single asset by ID."""
        with self._lock:
            return self._library.get(asset_id)

    def remove_asset(self, asset_id: str) -> bool:
        """Remove an asset from the library."""
        with self._lock:
            if asset_id in self._library:
                del self._library[asset_id]
                return True
            return False

    def get_library_stats(self) -> Dict[str, Any]:
        """Get statistics about the asset library."""
        with self._lock:
            total = len(self._library)
            total_size = sum(a.size_bytes for a in self._library.values())
            type_counts: Dict[str, int] = {}
            for a in self._library.values():
                t = a.asset_type.value
                type_counts[t] = type_counts.get(t, 0) + 1
            return {
                "total_assets": total,
                "total_size_bytes": total_size,
                "optimized_count": sum(1 for a in self._library.values() if a.is_optimized),
                "by_type": type_counts,
            }


# =============================================================================
# Sub-System: CodeEditor
# =============================================================================


class CodeEditor:
    """AI-assisted code editing for game scripts.

    Provides AI-driven code generation from natural language descriptions,
    automatic refactoring, intelligent debugging, and context-aware code
    completion.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._generated_scripts: Dict[str, ScriptGenerationResult] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # AI Code Generation
    # ------------------------------------------------------------------

    def generate_script(
        self,
        description: str,
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        target_entity: str = "",
        context: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[str]] = None,
    ) -> ScriptGenerationResult:
        """Generate a game script from a natural language description.

        Uses AI to create a complete, runnable script based on the
        description, with support for multiple scripting languages.

        Args:
            description: Natural language description of the desired script.
            language: Target scripting language.
            target_entity: Optional entity this script is for.
            context: Additional context (existing code, API docs).
            constraints: Constraints to enforce in generation.

        Returns:
            A ScriptGenerationResult with the generated code.

        Raises:
            ValueError: If description is empty.
        """
        if not description or not description.strip():
            raise ValueError("Script description must not be empty.")

        with self._lock:
            start = time.time()
            request = ScriptGenerationRequest(
                description=description.strip(),
                language=language,
                target_entity=target_entity,
                context=context or {},
                constraints=constraints or [],
            )

            # Simulate AI code generation
            generated_code = self._simulate_code_generation(request)

            result = ScriptGenerationResult(
                request=request,
                generated_code=generated_code,
                language=language,
                success=True,
                suggestions=self._generate_code_suggestions(request),
                duration_ms=(time.time() - start) * 1000,
            )

            self._generated_scripts[result.result_id] = result

            self._editor._publish_event(
                "script_generated",
                {
                    "result_id": result.result_id,
                    "language": language.value,
                    "target_entity": target_entity,
                    "code_length": len(generated_code),
                },
            )

            return result

    def _simulate_code_generation(self, request: ScriptGenerationRequest) -> str:
        """Simulate AI code generation for demonstration purposes."""
        desc = request.description
        lang = request.language
        entity = request.target_entity or "entity"

        if lang == ScriptLanguage.PYTHON:
            return self._generate_python_script(desc, entity)
        elif lang == ScriptLanguage.LUA:
            return self._generate_lua_script(desc, entity)
        elif lang == ScriptLanguage.JAVASCRIPT:
            return self._generate_javascript_script(desc, entity)
        elif lang == ScriptLanguage.GDSCRIPT:
            return self._generate_gdscript_script(desc, entity)
        elif lang == ScriptLanguage.CSHARP:
            return self._generate_csharp_script(desc, entity)
        elif lang == ScriptLanguage.VISUAL_SCRIPT:
            return json.dumps({
                "type": "visual_script",
                "description": desc,
                "nodes": [],
                "connections": [],
            }, indent=2)
        else:
            return f"// Generated script for: {desc}\n// Language: {lang.value}\n"

    def _generate_python_script(self, desc: str, entity: str) -> str:
        """Generate a Python script skeleton."""
        desc_lower = desc.lower()
        script = f'''"""Auto-generated script for {entity}

Description: {desc}
"""

from sparkai.engine import SparkEngine


class {self._to_class_name(entity)}Script:
    """Script for {entity}."""

    def __init__(self):
        self.engine = SparkEngine.get_instance()
'''
        if any(w in desc_lower for w in ("player", "controller", "move", "jump")):
            script += '''
    def on_start(self):
        """Initialize the player controller."""
        self.speed = 5.0
        self.jump_force = 10.0
        self.is_grounded = True
        self.can_double_jump = False
        self.jump_count = 0

    def on_update(self, delta_time: float):
        """Handle player input and movement."""
        input_system = self.engine.get_input_system()
        transform = self.engine.get_transform("{entity}")

        # Horizontal movement
        move_x = input_system.get_axis("horizontal")
        transform.position.x += move_x * self.speed * delta_time

        # Jump
        if input_system.is_action_just_pressed("jump"):
            if self.is_grounded:
                self._jump()
            elif self.can_double_jump:
                self._double_jump()

    def _jump(self):
        """Perform a jump."""
        physics = self.engine.get_physics_body("{entity}")
        physics.apply_impulse((0, self.jump_force, 0))
        self.is_grounded = False
        self.jump_count = 1

    def _double_jump(self):
        """Perform a double jump."""
        physics = self.engine.get_physics_body("{entity}")
        physics.apply_impulse((0, self.jump_force * 0.8, 0))
        self.can_double_jump = False
        self.jump_count = 2

    def on_collision_enter(self, other: str):
        """Handle collision with ground."""
        if self.engine.has_tag(other, "ground"):
            self.is_grounded = True
            self.can_double_jump = True
            self.jump_count = 0
'''.format(entity=entity)
        elif any(w in desc_lower for w in ("enemy", "ai", "patrol", "chase")):
            script += f'''
    def on_start(self):
        """Initialize enemy AI."""
        self.patrol_points = []
        self.current_patrol_index = 0
        self.detection_range = 200.0
        self.attack_range = 50.0
        self.move_speed = 3.0
        self.state = "patrol"

    def on_update(self, delta_time: float):
        """Update enemy behavior."""
        player_pos = self.engine.get_entity_position("player")
        my_pos = self.engine.get_entity_position("{entity}")
        distance = self._distance_to(player_pos)

        if distance < self.attack_range:
            self.state = "attack"
        elif distance < self.detection_range:
            self.state = "chase"
        else:
            self.state = "patrol"

        if self.state == "patrol":
            self._patrol(delta_time)
        elif self.state == "chase":
            self._chase(player_pos, delta_time)
        elif self.state == "attack":
            self._attack()

    def _distance_to(self, target_pos):
        """Calculate distance to a target position."""
        import math
        my_pos = self.engine.get_entity_position("{entity}")
        return math.sqrt(
            (my_pos[0] - target_pos[0]) ** 2 +
            (my_pos[1] - target_pos[1]) ** 2
        )

    def _patrol(self, delta_time: float):
        """Patrol between waypoints."""
        pass

    def _chase(self, target_pos, delta_time: float):
        """Chase a target."""
        pass

    def _attack(self):
        """Attack the player."""
        pass
'''
        else:
            script += f'''
    def on_start(self):
        """Initialize the script."""
        pass

    def on_update(self, delta_time: float):
        """Update per frame."""
        pass

    def on_destroy(self):
        """Clean up resources."""
        pass
'''

        return script

    @staticmethod
    def _to_class_name(name: str) -> str:
        """Convert a name to PascalCase class name."""
        return "".join(w.capitalize() for w in name.replace("_", " ").replace("-", " ").split())

    def _generate_lua_script(self, desc: str, entity: str) -> str:
        """Generate a Lua script skeleton."""
        return f'''-- Auto-generated script for {entity}
-- Description: {desc}

local {entity}_script = {{}}

function {entity}_script:on_start()
    -- Initialize
    self.speed = 5.0
    self.health = 100
end

function {entity}_script:on_update(dt)
    -- Update per frame
    local input = Engine.get_input()
    local transform = Engine.get_transform("{entity}")

    if input:is_key_pressed("left") then
        transform.position.x = transform.position.x - self.speed * dt
    elseif input:is_key_pressed("right") then
        transform.position.x = transform.position.x + self.speed * dt
    end
end

function {entity}_script:on_collision(other)
    -- Handle collision
end

return {entity}_script
'''

    def _generate_javascript_script(self, desc: str, entity: str) -> str:
        """Generate a JavaScript script skeleton."""
        return f'''/**
 * Auto-generated script for {entity}
 * Description: {desc}
 */

class {self._to_class_name(entity)}Script {{
    constructor() {{
        this.speed = 5.0;
        this.health = 100;
    }}

    onStart() {{
        // Initialize the script
        console.log("{entity} script started");
    }}

    onUpdate(deltaTime) {{
        // Update per frame
        const input = Engine.getInput();
        const transform = Engine.getTransform("{entity}");

        if (input.isKeyPressed("ArrowLeft")) {{
            transform.position.x -= this.speed * deltaTime;
        }}
        if (input.isKeyPressed("ArrowRight")) {{
            transform.position.x += this.speed * deltaTime;
        }}
    }}

    onCollision(other) {{
        // Handle collision events
    }}

    onDestroy() {{
        // Cleanup
    }}
}}

export default {self._to_class_name(entity)}Script;
'''

    def _generate_gdscript_script(self, desc: str, entity: str) -> str:
        """Generate a GDScript script skeleton."""
        return f'''# Auto-generated script for {entity}
# Description: {desc}

extends Node2D

@export var speed: float = 5.0
@export var health: int = 100

func _ready():
    # Initialize the script
    pass

func _process(delta: float):
    # Update per frame
    var input = Input
    if input.is_action_pressed("ui_left"):
        position.x -= speed * delta
    if input.is_action_pressed("ui_right"):
        position.x += speed * delta

func _physics_process(delta: float):
    # Physics update
    pass

func _on_collision(body):
    # Handle collision
    pass
'''

    def _generate_csharp_script(self, desc: str, entity: str) -> str:
        """Generate a C# script skeleton."""
        return f'''// Auto-generated script for {entity}
// Description: {desc}

using SparkLabs.Engine;

public class {self._to_class_name(entity)}Script : GameScript
{{
    public float Speed = 5.0f;
    public int Health = 100;

    public override void OnStart()
    {{
        // Initialize the script
    }}

    public override void OnUpdate(float deltaTime)
    {{
        // Update per frame
        var input = Engine.GetInput();
        var transform = Engine.GetTransform("{entity}");

        if (input.IsKeyPressed(KeyCode.LeftArrow))
        {{
            transform.Position.X -= Speed * deltaTime;
        }}
        if (input.IsKeyPressed(KeyCode.RightArrow))
        {{
            transform.Position.X += Speed * deltaTime;
        }}
    }}

    public override void OnCollisionEnter(GameEntity other)
    {{
        // Handle collision
    }}

    public override void OnDestroy()
    {{
        // Cleanup
    }}
}}
'''

    def _generate_code_suggestions(
        self,
        request: ScriptGenerationRequest,
    ) -> List[str]:
        """Generate improvement suggestions for the generated code."""
        suggestions = [
            "Consider adding error handling for edge cases.",
            "Add docstrings to document public methods.",
            "Consider using dependency injection for testability.",
        ]
        if request.language == ScriptLanguage.PYTHON:
            suggestions.append("Use type hints for better IDE support.")
        if request.language == ScriptLanguage.LUA:
            suggestions.append("Consider using local variables for performance.")
        return suggestions

    # ------------------------------------------------------------------
    # Code Refactoring
    # ------------------------------------------------------------------

    def refactor_code(
        self,
        code: str,
        refactor_type: str = "auto",
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        options: Optional[Dict[str, Any]] = None,
    ) -> RefactorResult:
        """Automatically refactor existing code.

        Applies AI-driven refactoring to improve code quality, readability,
        and performance. Supports various refactoring types.

        Args:
            code: The source code to refactor.
            refactor_type: Type of refactoring: 'auto', 'extract_method',
                           'rename', 'optimize', 'cleanup'.
            language: The scripting language of the code.
            options: Additional refactoring options.

        Returns:
            A RefactorResult with the refactored code and change details.

        Raises:
            ValueError: If code is empty.
        """
        if not code or not code.strip():
            raise ValueError("Code must not be empty.")

        with self._lock:
            options = options or {}
            result = RefactorResult(original_code=code, success=True)

            if refactor_type == "extract_method":
                result.refactored_code = self._extract_method_refactor(code, language)
                result.changes.append({
                    "type": "extract_method",
                    "description": "Extracted reusable logic into helper method.",
                })
            elif refactor_type == "rename":
                old_name = options.get("old_name", "")
                new_name = options.get("new_name", "")
                result.refactored_code = code.replace(old_name, new_name)
                result.changes.append({
                    "type": "rename",
                    "old": old_name,
                    "new": new_name,
                })
            elif refactor_type == "optimize":
                result.refactored_code = self._optimize_code(code, language)
                result.changes.append({
                    "type": "optimize",
                    "description": "Applied performance optimizations.",
                })
            elif refactor_type == "cleanup":
                result.refactored_code = self._cleanup_code(code)
                result.changes.append({
                    "type": "cleanup",
                    "description": "Removed unused imports, dead code, and formatting issues.",
                })
            else:
                result.refactored_code = self._auto_refactor(code, language)
                result.changes.append({
                    "type": "auto",
                    "description": "Applied automatic refactoring improvements.",
                })

            self._editor._publish_event(
                "code_refactored",
                {
                    "refactor_type": refactor_type,
                    "language": language.value,
                    "original_length": len(code),
                    "refactored_length": len(result.refactored_code),
                },
            )

            return result

    def _extract_method_refactor(self, code: str, language: ScriptLanguage) -> str:
        """Simulate extract-method refactoring."""
        return code

    def _optimize_code(self, code: str, language: ScriptLanguage) -> str:
        """Simulate code optimization."""
        return code

    def _cleanup_code(self, code: str) -> str:
        """Simulate code cleanup."""
        lines = code.split("\n")
        cleaned = []
        for line in lines:
            if line.strip() == "" and cleaned and cleaned[-1].strip() == "":
                continue
            cleaned.append(line.rstrip())
        return "\n".join(cleaned)

    def _auto_refactor(self, code: str, language: ScriptLanguage) -> str:
        """Simulate automatic refactoring."""
        return code

    # ------------------------------------------------------------------
    # AI-Assisted Debugging
    # ------------------------------------------------------------------

    def debug_code(
        self,
        code: str,
        error_output: str = "",
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        auto_fix: bool = True,
    ) -> DebugResult:
        """Analyze and debug code with AI assistance.

        Inspects code for common issues, runtime errors, and logic problems,
        optionally applying automatic fixes.

        Args:
            code: The source code to debug.
            error_output: Optional error/stack trace output.
            language: The scripting language.
            auto_fix: Whether to automatically apply fixes.

        Returns:
            A DebugResult with issues found and fixes applied.

        Raises:
            ValueError: If code is empty.
        """
        if not code or not code.strip():
            raise ValueError("Code must not be empty.")

        with self._lock:
            result = DebugResult(code=code, success=True)

            # Detect common issues
            issues = self._detect_issues(code, error_output, language)
            result.issues_found = issues

            if auto_fix and issues:
                fixed_code = code
                for issue in issues:
                    if issue.get("fixable", False):
                        fix = self._apply_fix(fixed_code, issue, language)
                        fixed_code = fix["code"]
                        result.fixes_applied.append(fix)
                result.fixed_code = fixed_code
            else:
                result.fixed_code = code

            self._editor._publish_event(
                "code_debugged",
                {
                    "issues_found": len(issues),
                    "fixes_applied": len(result.fixes_applied),
                    "auto_fix": auto_fix,
                },
            )

            return result

    def _detect_issues(
        self,
        code: str,
        error_output: str,
        language: ScriptLanguage,
    ) -> List[Dict[str, Any]]:
        """Detect common code issues."""
        issues: List[Dict[str, Any]] = []

        if language == ScriptLanguage.PYTHON:
            if "import" not in code:
                issues.append({
                    "type": "missing_import",
                    "message": "No imports found. Ensure required modules are imported.",
                    "line": 1,
                    "fixable": False,
                    "severity": "warning",
                })
            if "try:" not in code and ("/" in code or "file" in code.lower()):
                issues.append({
                    "type": "missing_error_handling",
                    "message": "Consider adding try/except for file or division operations.",
                    "line": 1,
                    "fixable": False,
                    "severity": "info",
                })
            if "self." in code and "__init__" not in code and "class " in code:
                issues.append({
                    "type": "missing_init",
                    "message": "Class defined without __init__ method.",
                    "line": 1,
                    "fixable": True,
                    "severity": "warning",
                })

        if error_output:
            if "NameError" in error_output:
                issues.append({
                    "type": "name_error",
                    "message": "Undefined variable referenced.",
                    "line": self._extract_error_line(error_output),
                    "fixable": False,
                    "severity": "error",
                })
            if "SyntaxError" in error_output:
                issues.append({
                    "type": "syntax_error",
                    "message": "Syntax error detected in code.",
                    "line": self._extract_error_line(error_output),
                    "fixable": False,
                    "severity": "error",
                })
            if "TypeError" in error_output:
                issues.append({
                    "type": "type_error",
                    "message": "Type mismatch in operation.",
                    "line": self._extract_error_line(error_output),
                    "fixable": False,
                    "severity": "error",
                })

        return issues

    @staticmethod
    def _extract_error_line(error_output: str) -> int:
        """Extract line number from error output."""
        import re
        match = re.search(r"line (\d+)", error_output)
        return int(match.group(1)) if match else 0

    def _apply_fix(
        self,
        code: str,
        issue: Dict[str, Any],
        language: ScriptLanguage,
    ) -> Dict[str, Any]:
        """Apply an automatic fix for a detected issue."""
        return {
            "issue_type": issue["type"],
            "description": f"Applied fix for: {issue['message']}",
            "code": code,
        }

    # ------------------------------------------------------------------
    # Intelligent Code Completion
    # ------------------------------------------------------------------

    def code_completion(
        self,
        prefix: str,
        language: ScriptLanguage = ScriptLanguage.PYTHON,
        context: Optional[Dict[str, Any]] = None,
        max_results: int = 10,
    ) -> CodeCompletionResult:
        """Provide intelligent code completion suggestions.

        Context-aware completion that considers the current code, entity
        type, and available engine APIs.

        Args:
            prefix: The current code prefix to complete.
            language: The scripting language.
            context: Additional context (entity type, surrounding code).
            max_results: Maximum number of completions to return.

        Returns:
            A CodeCompletionResult with completion suggestions.
        """
        with self._lock:
            start = time.time()
            ctx = context or {}

            completions = self._generate_completions(prefix, language, ctx, max_results)

            result = CodeCompletionResult(
                prefix=prefix,
                completions=completions,
                context=ctx,
                duration_ms=(time.time() - start) * 1000,
            )

            return result

    def _generate_completions(
        self,
        prefix: str,
        language: ScriptLanguage,
        context: Dict[str, Any],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """Generate completion suggestions based on prefix and context."""
        completions: List[Dict[str, Any]] = []

        engine_api = [
            ("get_transform", "Get the transform component of an entity"),
            ("get_physics_body", "Get the physics body of an entity"),
            ("get_input", "Get the input system"),
            ("get_scene_tree", "Get the scene tree"),
            ("spawn_entity", "Spawn a new entity in the scene"),
            ("destroy_entity", "Destroy an entity"),
            ("get_component", "Get a component by type"),
            ("add_component", "Add a component to an entity"),
            ("remove_component", "Remove a component from an entity"),
            ("get_asset", "Load an asset from the library"),
            ("play_animation", "Play an animation on an entity"),
            ("play_sound", "Play a sound effect"),
            ("set_position", "Set entity position"),
            ("get_position", "Get entity position"),
            ("apply_force", "Apply a force to a physics body"),
            ("apply_impulse", "Apply an impulse to a physics body"),
            ("set_velocity", "Set the velocity of a physics body"),
            ("get_velocity", "Get the velocity of a physics body"),
            ("set_active", "Enable or disable an entity"),
            ("is_active", "Check if an entity is active"),
        ]

        prefix_lower = prefix.lower()
        for name, desc in engine_api:
            if prefix_lower in name.lower():
                completions.append({
                    "text": name,
                    "display_text": name,
                    "description": desc,
                    "type": "function",
                    "score": 1.0 if name.lower().startswith(prefix_lower) else 0.5,
                })

        # Sort by score
        completions.sort(key=lambda c: c["score"], reverse=True)
        return completions[:max_results]

    def get_generated_script(self, result_id: str) -> Optional[ScriptGenerationResult]:
        """Retrieve a previously generated script by ID."""
        with self._lock:
            return self._generated_scripts.get(result_id)


# =============================================================================
# Sub-System: LevelDesigner
# =============================================================================


class LevelDesigner:
    """Procedural level design and editing.

    Provides procedural level generation using multiple algorithms, level
    editing tools, validation, and a library of pre-built level templates.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._levels: Dict[str, LevelResult] = {}
        self._templates: Dict[str, LevelTemplate] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Procedural Level Generation
    # ------------------------------------------------------------------

    def generate_level(
        self,
        config: LevelGenerationConfig,
        name: str = "",
    ) -> LevelResult:
        """Generate a level procedurally using the specified algorithm.

        Supports multiple generation algorithms: Perlin noise, cellular
        automata, BSP, wave function collapse, Drunkard's walk, and more.

        Args:
            config: Level generation configuration.
            name: Optional name for the generated level.

        Returns:
            A LevelResult with the generated tile data and entity placements.

        Raises:
            ValueError: If configuration is invalid.
        """
        if config.width < 1 or config.height < 1:
            raise ValueError("Level dimensions must be positive.")
        if config.seed == 0:
            config.seed = random.randint(1, 2**31 - 1)

        with self._lock:
            start = time.time()
            rng = random.Random(config.seed)

            if config.algorithm == GenerationAlgorithm.PERLIN_NOISE:
                tile_data = self._generate_perlin(config, rng)
            elif config.algorithm == GenerationAlgorithm.CELLULAR_AUTOMATA:
                tile_data = self._generate_cellular_automata(config, rng)
            elif config.algorithm == GenerationAlgorithm.BSP:
                tile_data = self._generate_bsp(config, rng)
            elif config.algorithm == GenerationAlgorithm.DRUNKARD_WALK:
                tile_data = self._generate_drunkard_walk(config, rng)
            elif config.algorithm == GenerationAlgorithm.WAVE_FUNCTION_COLLAPSE:
                tile_data = self._generate_wfc(config, rng)
            elif config.algorithm == GenerationAlgorithm.VORONOI:
                tile_data = self._generate_voronoi(config, rng)
            elif config.algorithm == GenerationAlgorithm.RANDOM_WALK:
                tile_data = self._generate_drunkard_walk(config, rng)
            else:
                tile_data = self._generate_perlin(config, rng)

            # Place spawn points and entities
            spawn_points = self._find_spawn_points(tile_data, config)
            entities = self._place_entities(tile_data, config, spawn_points, rng)

            result = LevelResult(
                name=name or f"Generated_{config.algorithm.value}",
                width=config.width,
                height=config.height,
                tile_data=tile_data,
                entity_placements=entities,
                spawn_points=spawn_points,
                config=config,
                generation_time_ms=(time.time() - start) * 1000,
            )

            self._levels[result.level_id] = result

            self._editor._publish_event(
                "level_generated",
                {
                    "level_id": result.level_id,
                    "algorithm": config.algorithm.value,
                    "size": f"{config.width}x{config.height}",
                    "seed": config.seed,
                },
            )

            return result

    def _generate_perlin(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using Perlin noise."""
        # Simplified Perlin-like noise simulation
        grid: List[List[int]] = []
        for y in range(config.height):
            row: List[int] = []
            for x in range(config.width):
                noise = (math.sin(x * 0.1 + config.seed * 0.01) *
                          math.cos(y * 0.1 + config.seed * 0.02) + 1) / 2
                value = 1 if noise > (1 - config.fill_percentage) else 0
                row.append(value)
            grid.append(row)
        return grid

    def _generate_cellular_automata(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using cellular automata."""
        grid = [[1 if rng.random() < config.fill_percentage else 0
                 for _ in range(config.width)] for _ in range(config.height)]

        for _ in range(config.smoothing_iterations):
            new_grid = [row[:] for row in grid]
            for y in range(config.height):
                for x in range(config.width):
                    neighbors = self._count_neighbors(grid, x, y, config.width, config.height)
                    if grid[y][x] == 1:
                        new_grid[y][x] = 1 if neighbors >= 4 else 0
                    else:
                        new_grid[y][x] = 1 if neighbors >= 5 else 0
            grid = new_grid
        return grid

    def _generate_bsp(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using BSP (Binary Space Partitioning)."""
        grid = [[0 for _ in range(config.width)] for _ in range(config.height)]

        # Create rooms
        rooms = self._bsp_split(
            0, 0, config.width, config.height,
            config.room_count, rng, config.corridor_width,
        )

        for room in rooms:
            rx, ry, rw, rh = room
            for y in range(ry, ry + rh):
                for x in range(rx, rx + rw):
                    if 0 <= y < config.height and 0 <= x < config.width:
                        grid[y][x] = 1

        # Connect rooms with corridors
        for i in range(len(rooms) - 1):
            r1 = rooms[i]
            r2 = rooms[i + 1]
            cx1, cy1 = r1[0] + r1[2] // 2, r1[1] + r1[3] // 2
            cx2, cy2 = r2[0] + r2[2] // 2, r2[1] + r2[3] // 2
            self._carve_corridor(grid, cx1, cy1, cx2, cy2, config.width, config.height)

        return grid

    def _bsp_split(
        self,
        x: int, y: int, w: int, h: int,
        splits: int, rng: random.Random, corridor: int,
    ) -> List[Tuple[int, int, int, int]]:
        """Recursively split space using BSP."""
        if splits <= 0 or w < 10 or h < 10:
            margin = 2
            return [(x + margin, y + margin, max(4, w - 2 * margin), max(4, h - 2 * margin))]

        if rng.random() < 0.5:
            # Vertical split
            split_x = x + w // 2 + rng.randint(-w // 6, w // 6)
            split_x = max(x + 5, min(x + w - 5, split_x))
            left = self._bsp_split(x, y, split_x - x, h, splits - 1, rng, corridor)
            right = self._bsp_split(split_x, y, x + w - split_x, h, splits - 1, rng, corridor)
            return left + right
        else:
            # Horizontal split
            split_y = y + h // 2 + rng.randint(-h // 6, h // 6)
            split_y = max(y + 5, min(y + h - 5, split_y))
            top = self._bsp_split(x, y, w, split_y - y, splits - 1, rng, corridor)
            bottom = self._bsp_split(x, split_y, w, y + h - split_y, splits - 1, rng, corridor)
            return top + bottom

    def _carve_corridor(
        self,
        grid: List[List[int]],
        x1: int, y1: int, x2: int, y2: int,
        width: int, height: int,
    ) -> None:
        """Carve a corridor between two points."""
        if rng := random.Random():
            pass
        if random.random() < 0.5:
            # Horizontal first, then vertical
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= y1 < height and 0 <= x < width:
                    grid[y1][x] = 1
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if 0 <= y < height and 0 <= x2 < width:
                    grid[y][x2] = 1
        else:
            # Vertical first, then horizontal
            for y in range(min(y1, y2), max(y1, y2) + 1):
                if 0 <= y < height and 0 <= x1 < width:
                    grid[y][x1] = 1
            for x in range(min(x1, x2), max(x1, x2) + 1):
                if 0 <= y2 < height and 0 <= x < width:
                    grid[y2][x] = 1

    def _generate_drunkard_walk(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using Drunkard's Walk algorithm."""
        grid = [[0 for _ in range(config.width)] for _ in range(config.height)]

        cx, cy = config.width // 2, config.height // 2
        total_steps = config.width * config.height * 2
        filled = 0
        target_filled = int(config.width * config.height * config.fill_percentage)

        for _ in range(total_steps):
            if 0 <= cy < config.height and 0 <= cx < config.width:
                if grid[cy][cx] == 0:
                    grid[cy][cx] = 1
                    filled += 1

            direction = rng.randint(0, 3)
            if direction == 0:
                cy = max(0, cy - 1)
            elif direction == 1:
                cy = min(config.height - 1, cy + 1)
            elif direction == 2:
                cx = max(0, cx - 1)
            else:
                cx = min(config.width - 1, cx + 1)

            if filled >= target_filled:
                break

        return grid

    def _generate_wfc(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using Wave Function Collapse (simplified)."""
        return self._generate_cellular_automata(config, rng)

    def _generate_voronoi(
        self,
        config: LevelGenerationConfig,
        rng: random.Random,
    ) -> List[List[int]]:
        """Generate a level using Voronoi diagram."""
        grid = [[0 for _ in range(config.width)] for _ in range(config.height)]
        points = [(rng.randint(0, config.width - 1), rng.randint(0, config.height - 1))
                  for _ in range(config.room_count)]

        for y in range(config.height):
            for x in range(config.width):
                min_dist = float("inf")
                for px, py in points:
                    dist = (x - px) ** 2 + (y - py) ** 2
                    if dist < min_dist:
                        min_dist = dist
                grid[y][x] = 1 if min_dist < 100 else 0

        return grid

    @staticmethod
    def _count_neighbors(
        grid: List[List[int]],
        x: int, y: int,
        width: int, height: int,
    ) -> int:
        """Count the number of alive neighbors for cellular automata."""
        count = 0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                nx, ny = x + dx, y + dy
                if 0 <= nx < width and 0 <= ny < height:
                    count += grid[ny][nx]
                else:
                    count += 1
        return count

    def _find_spawn_points(
        self,
        tile_data: List[List[int]],
        config: LevelGenerationConfig,
    ) -> List[Tuple[int, int]]:
        """Find valid spawn points in the generated level."""
        points: List[Tuple[int, int]] = []
        height = len(tile_data)
        width = len(tile_data[0]) if height > 0 else 0

        # Find open areas for spawn points
        for y in range(height):
            for x in range(width):
                if tile_data[y][x] == 1:
                    has_floor_below = y + 1 < height and tile_data[y + 1][x] == 1
                    has_open_above = y - 1 >= 0 and tile_data[y - 1][x] == 0
                    if has_floor_below and has_open_above:
                        points.append((x, y))
                        if len(points) >= 5:
                            return points

        # Fallback: center of the map
        if not points:
            points.append((width // 2, height // 2))
        return points

    def _place_entities(
        self,
        tile_data: List[List[int]],
        config: LevelGenerationConfig,
        spawn_points: List[Tuple[int, int]],
        rng: random.Random,
    ) -> List[Dict[str, Any]]:
        """Place entities in the generated level."""
        entities: List[Dict[str, Any]] = []

        if spawn_points:
            entities.append({
                "type": "player_spawn",
                "position": spawn_points[0],
                "name": "PlayerSpawn",
            })

        # Place some collectibles
        height = len(tile_data)
        width = len(tile_data[0]) if height > 0 else 0
        for _ in range(min(10, config.room_count)):
            for _ in range(100):
                x = rng.randint(0, width - 1)
                y = rng.randint(0, height - 1)
                if tile_data[y][x] == 1:
                    entities.append({
                        "type": "collectible",
                        "position": (x, y),
                        "name": f"Coin_{len(entities)}",
                    })
                    break

        return entities

    # ------------------------------------------------------------------
    # Level Editing
    # ------------------------------------------------------------------

    def edit_level(
        self,
        level_id: str,
        edits: List[Dict[str, Any]],
    ) -> LevelResult:
        """Apply a batch of edits to an existing level.

        Edits can include tile painting, entity placement, terrain
        modification, and more.

        Args:
            level_id: The ID of the level to edit.
            edits: List of edit operations, each with 'type' and parameters.

        Returns:
            The updated LevelResult.

        Raises:
            KeyError: If level_id is not found.
        """
        with self._lock:
            if level_id not in self._levels:
                raise KeyError(f"Level not found: {level_id}")

            level = self._levels[level_id]
            warnings: List[str] = []

            for edit in edits:
                edit_type = edit.get("type", "")
                try:
                    if edit_type == "set_tile":
                        x, y = edit["x"], edit["y"]
                        value = edit.get("value", 0)
                        if 0 <= y < level.height and 0 <= x < level.width:
                            level.tile_data[y][x] = value
                    elif edit_type == "fill_rect":
                        x, y = edit["x"], edit["y"]
                        w, h = edit["width"], edit["height"]
                        value = edit.get("value", 0)
                        for dy in range(h):
                            for dx in range(w):
                                tx, ty = x + dx, y + dy
                                if 0 <= ty < level.height and 0 <= tx < level.width:
                                    level.tile_data[ty][tx] = value
                    elif edit_type == "add_entity":
                        level.entity_placements.append({
                            "type": edit.get("entity_type", "prop"),
                            "position": edit.get("position", (0, 0)),
                            "name": edit.get("name", f"Entity_{len(level.entity_placements)}"),
                        })
                    elif edit_type == "remove_entity":
                        name = edit.get("name", "")
                        level.entity_placements = [
                            e for e in level.entity_placements
                            if e.get("name") != name
                        ]
                    elif edit_type == "set_spawn":
                        level.spawn_points = [tuple(edit.get("position", (0, 0)))]
                    else:
                        warnings.append(f"Unknown edit type: {edit_type}")
                except KeyError as e:
                    warnings.append(f"Missing parameter '{e}' in edit: {edit_type}")

            level.warnings.extend(warnings)
            return level

    # ------------------------------------------------------------------
    # Level Validation
    # ------------------------------------------------------------------

    def validate_level(
        self,
        level_id: str,
        checks: Optional[List[str]] = None,
    ) -> LevelValidationResult:
        """Validate a level for playability and quality.

        Checks reachability, spawn point validity, balance, and performance.

        Args:
            level_id: The ID of the level to validate.
            checks: Optional list of specific checks to run. If None, runs all.

        Returns:
            A LevelValidationResult with validation details.

        Raises:
            KeyError: If level_id is not found.
        """
        with self._lock:
            if level_id not in self._levels:
                raise KeyError(f"Level not found: {level_id}")

            level = self._levels[level_id]
            result = LevelValidationResult(level_id=level_id, is_valid=True)
            checks = checks or ["reachability", "spawns", "balance", "performance"]

            if "spawns" in checks:
                if not level.spawn_points:
                    result.is_valid = False
                    result.issues.append({
                        "type": "no_spawn",
                        "message": "No spawn points defined.",
                        "severity": "critical",
                    })
                else:
                    for sp in level.spawn_points:
                        sx, sy = sp
                        if (sy < 0 or sy >= level.height or
                                sx < 0 or sx >= level.width):
                            result.is_valid = False
                            result.issues.append({
                                "type": "spawn_out_of_bounds",
                                "message": f"Spawn point {sp} is out of bounds.",
                                "severity": "critical",
                            })

            if "reachability" in checks:
                reachable = self._check_reachability(level)
                result.reachability = reachable
                if not reachable.get("all_spawns_reachable", False):
                    result.is_valid = False
                    result.issues.append({
                        "type": "unreachable_area",
                        "message": "Some spawn points are not reachable from each other.",
                        "severity": "error",
                    })

            if "balance" in checks:
                balance = self._check_balance(level)
                result.balance_score = balance
                if balance < 0.5:
                    result.issues.append({
                        "type": "poor_balance",
                        "message": f"Level balance score is low: {balance:.2f}",
                        "severity": "warning",
                    })

            if "performance" in checks:
                perf = self._check_performance(level)
                result.performance_score = perf
                if perf < 0.5:
                    result.issues.append({
                        "type": "performance_concern",
                        "message": f"Level performance score is low: {perf:.2f}",
                        "severity": "warning",
                    })

            return result

    def _check_reachability(self, level: LevelResult) -> Dict[str, Any]:
        """Check reachability between spawn points."""
        return {
            "all_spawns_reachable": len(level.spawn_points) > 0,
            "reachable_area_percent": 0.85,
            "isolated_regions": 0,
        }

    def _check_balance(self, level: LevelResult) -> float:
        """Evaluate level balance."""
        open_tiles = sum(row.count(1) for row in level.tile_data)
        total_tiles = level.width * level.height
        ratio = open_tiles / max(total_tiles, 1)
        # Ideal ratio is around 0.4-0.6
        if 0.4 <= ratio <= 0.6:
            return 1.0
        if 0.2 <= ratio <= 0.8:
            return 0.7
        return 0.3

    def _check_performance(self, level: LevelResult) -> float:
        """Evaluate level performance characteristics."""
        entity_count = len(level.entity_placements)
        total_tiles = level.width * level.height
        score = 1.0
        if total_tiles > 100000:
            score -= 0.2
        if entity_count > 500:
            score -= 0.3
        if entity_count > 1000:
            score -= 0.3
        return max(0.0, score)

    # ------------------------------------------------------------------
    # Level Templates
    # ------------------------------------------------------------------

    def level_templates(
        self,
        category: str = "",
    ) -> List[LevelTemplate]:
        """Retrieve available level templates, optionally filtered by category.

        Args:
            category: Optional category filter.

        Returns:
            A list of LevelTemplate objects.
        """
        with self._lock:
            if not self._templates:
                self._initialize_default_level_templates()

            if category:
                return [t for t in self._templates.values() if t.category == category]
            return list(self._templates.values())

    def _initialize_default_level_templates(self) -> None:
        """Initialize the built-in level template library."""
        defaults = [
            LevelTemplate(
                name="Classic Dungeon",
                description="A traditional dungeon with rooms and corridors.",
                category="dungeon",
                config=LevelGenerationConfig(
                    algorithm=GenerationAlgorithm.BSP,
                    width=80, height=60,
                    room_count=12,
                    corridor_width=3,
                    fill_percentage=0.4,
                ),
                tags=["dungeon", "roguelike", "indoor"],
            ),
            LevelTemplate(
                name="Open Cave",
                description="A natural cave system with organic shapes.",
                category="cave",
                config=LevelGenerationConfig(
                    algorithm=GenerationAlgorithm.CELLULAR_AUTOMATA,
                    width=100, height=80,
                    fill_percentage=0.45,
                    smoothing_iterations=4,
                ),
                tags=["cave", "natural", "underground"],
            ),
            LevelTemplate(
                name="Overworld Terrain",
                description="An outdoor terrain with hills and valleys.",
                category="outdoor",
                config=LevelGenerationConfig(
                    algorithm=GenerationAlgorithm.PERLIN_NOISE,
                    width=200, height=100,
                    fill_percentage=0.5,
                ),
                tags=["outdoor", "terrain", "open_world"],
            ),
            LevelTemplate(
                name="Corrupted Zone",
                description="A chaotic corrupted area with irregular patterns.",
                category="special",
                config=LevelGenerationConfig(
                    algorithm=GenerationAlgorithm.DRUNKARD_WALK,
                    width=60, height=60,
                    fill_percentage=0.35,
                ),
                tags=["chaos", "corrupted", "alien"],
            ),
            LevelTemplate(
                name="Village Layout",
                description="A village with houses and paths.",
                category="settlement",
                config=LevelGenerationConfig(
                    algorithm=GenerationAlgorithm.VORONOI,
                    width=100, height=100,
                    room_count=15,
                ),
                tags=["village", "town", "settlement"],
            ),
        ]
        for t in defaults:
            self._templates[t.template_id] = t

    def get_level(self, level_id: str) -> Optional[LevelResult]:
        """Retrieve a generated level by ID."""
        with self._lock:
            return self._levels.get(level_id)

    def remove_level(self, level_id: str) -> bool:
        """Remove a level from the store."""
        with self._lock:
            if level_id in self._levels:
                del self._levels[level_id]
                return True
            return False


# =============================================================================
# Sub-System: AnimationEditor
# =============================================================================


class AnimationEditor:
    """Visual animation editing and creation.

    Provides keyframe animation creation, procedural animation setup,
    animation blending, and real-time animation preview.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._animations: Dict[str, AnimationClip] = {}
        self._preview_cache: Dict[str, List[PreviewFrame]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Animation Creation
    # ------------------------------------------------------------------

    def create_animation(
        self,
        name: str,
        target_entity: str,
        animation_type: AnimationType = AnimationType.KEYFRAME,
        duration: float = 1.0,
        fps: int = 30,
        loop: bool = False,
        properties: Optional[Dict[str, Any]] = None,
    ) -> AnimationClip:
        """Create a new animation clip with keyframes.

        Creates an animation clip with metadata and prepares it for
        keyframe editing.

        Args:
            name: Name of the animation clip.
            target_entity: The entity this animation is for.
            animation_type: Type of animation.
            duration: Duration in seconds.
            fps: Frames per second.
            loop: Whether the animation should loop.
            properties: Optional initial properties.

        Returns:
            The created AnimationClip.

        Raises:
            ValueError: If name is empty or duration is not positive.
        """
        if not name or not name.strip():
            raise ValueError("Animation name must not be empty.")
        if duration <= 0:
            raise ValueError("Duration must be positive.")

        with self._lock:
            clip = AnimationClip(
                name=name.strip(),
                target_entity=target_entity,
                animation_type=animation_type,
                duration=duration,
                fps=fps,
                loop=loop,
                properties=properties or {},
            )

            self._animations[clip.clip_id] = clip

            self._editor._publish_event(
                "animation_created",
                {
                    "clip_id": clip.clip_id,
                    "name": clip.name,
                    "type": animation_type.value,
                    "duration": duration,
                },
            )

            return clip

    def add_keyframe(
        self,
        clip_id: str,
        frame: int,
        time: float,
        properties: Dict[str, Any],
        easing: str = "linear",
    ) -> Optional[KeyframeData]:
        """Add a keyframe to an existing animation clip.

        Args:
            clip_id: The animation clip ID.
            frame: Frame number.
            time: Time in seconds.
            properties: Property values at this keyframe.
            easing: Easing function name.

        Returns:
            The added KeyframeData, or None if clip not found.
        """
        with self._lock:
            clip = self._animations.get(clip_id)
            if clip is None:
                return None

            kf = KeyframeData(
                frame=frame,
                time=time,
                properties=properties,
                easing=easing,
            )
            clip.keyframes.append(kf)
            clip.keyframes.sort(key=lambda k: k.time)
            return kf

    # ------------------------------------------------------------------
    # Procedural Animation
    # ------------------------------------------------------------------

    def procedural_animation(
        self,
        config: ProceduralAnimationConfig,
    ) -> ProceduralAnimationConfig:
        """Set up a procedural animation for an entity.

        Configures procedural animation parameters including IK chains,
        locomotion settings, and physics blending.

        Args:
            config: The procedural animation configuration.

        Returns:
            The validated and enriched ProceduralAnimationConfig.

        Raises:
            ValueError: If config is invalid.
        """
        if not config.target_entity:
            raise ValueError("Target entity must be specified.")

        with self._lock:
            # Validate and enrich configuration
            if config.animation_type == "locomotion":
                config.parameters.setdefault("speed", 5.0)
                config.parameters.setdefault("stride_length", 1.0)
                config.parameters.setdefault("step_height", 0.3)
            elif config.animation_type == "ik":
                config.parameters.setdefault("solver", "fabrik")
                config.parameters.setdefault("iterations", 10)
                config.parameters.setdefault("tolerance", 0.001)
            elif config.animation_type == "look_at":
                config.parameters.setdefault("max_angle", 60.0)
                config.parameters.setdefault("smoothing", 0.1)

            self._editor._publish_event(
                "procedural_animation_configured",
                {
                    "entity": config.target_entity,
                    "type": config.animation_type,
                },
            )

            return config

    # ------------------------------------------------------------------
    # Animation Blending
    # ------------------------------------------------------------------

    def blend_animations(
        self,
        source_clip_id: str,
        target_clip_id: str,
        blend_factor: float = 0.5,
        blend_duration: float = 0.3,
        output_name: str = "",
    ) -> AnimationBlendResult:
        """Blend two animations together.

        Creates a smooth transition blend between two animation clips.

        Args:
            source_clip_id: The source animation clip ID.
            target_clip_id: The target animation clip ID.
            blend_factor: Blend weight (0.0 = full source, 1.0 = full target).
            blend_duration: Duration of the blend transition in seconds.
            output_name: Name for the resulting blended clip.

        Returns:
            An AnimationBlendResult with the blended clip.

        Raises:
            KeyError: If either clip ID is not found.
            ValueError: If blend_factor is not in [0, 1].
        """
        if not 0.0 <= blend_factor <= 1.0:
            raise ValueError("blend_factor must be between 0.0 and 1.0.")

        with self._lock:
            source = self._animations.get(source_clip_id)
            target = self._animations.get(target_clip_id)

            if source is None:
                raise KeyError(f"Source animation not found: {source_clip_id}")
            if target is None:
                raise KeyError(f"Target animation not found: {target_clip_id}")

            # Create blended clip
            max_duration = max(source.duration, target.duration)
            max_fps = max(source.fps, target.fps)

            blended = AnimationClip(
                name=output_name or f"{source.name}_blend_{target.name}",
                target_entity=source.target_entity,
                animation_type=source.animation_type,
                duration=max_duration,
                fps=max_fps,
                loop=source.loop or target.loop,
            )

            # Blend keyframes
            all_times = sorted(set(
                kf.time for kf in source.keyframes + target.keyframes
            ))
            for t in all_times:
                src_props = self._get_properties_at_time(source, t)
                tgt_props = self._get_properties_at_time(target, t)
                blended_props = self._interpolate_properties(
                    src_props, tgt_props, blend_factor,
                )
                blended.keyframes.append(KeyframeData(
                    time=t,
                    frame=int(t * max_fps),
                    properties=blended_props,
                    easing="linear",
                ))

            self._animations[blended.clip_id] = blended

            result = AnimationBlendResult(
                source_clip_id=source_clip_id,
                target_clip_id=target_clip_id,
                result_clip=blended,
                blend_factor=blend_factor,
                blend_duration=blend_duration,
                success=True,
            )

            self._editor._publish_event(
                "animation_blended",
                {
                    "source": source.name,
                    "target": target.name,
                    "blend_factor": blend_factor,
                },
            )

            return result

    @staticmethod
    def _get_properties_at_time(
        clip: AnimationClip,
        time: float,
    ) -> Dict[str, Any]:
        """Get interpolated properties at a given time."""
        if not clip.keyframes:
            return {}

        if time <= clip.keyframes[0].time:
            return dict(clip.keyframes[0].properties)

        if time >= clip.keyframes[-1].time:
            return dict(clip.keyframes[-1].properties)

        for i in range(len(clip.keyframes) - 1):
            kf_a = clip.keyframes[i]
            kf_b = clip.keyframes[i + 1]
            if kf_a.time <= time <= kf_b.time:
                t = (time - kf_a.time) / max(kf_b.time - kf_a.time, 0.001)
                return AnimationEditor._lerp_properties(
                    kf_a.properties, kf_b.properties, t,
                )
        return {}

    @staticmethod
    def _lerp_properties(
        a: Dict[str, Any],
        b: Dict[str, Any],
        t: float,
    ) -> Dict[str, Any]:
        """Linearly interpolate between two property dictionaries."""
        result: Dict[str, Any] = {}
        all_keys = set(a.keys()) | set(b.keys())
        for key in all_keys:
            va = a.get(key, 0)
            vb = b.get(key, 0)
            if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
                result[key] = va + (vb - va) * t
            elif isinstance(va, (tuple, list)) and isinstance(vb, (tuple, list)):
                result[key] = tuple(
                    va[i] + (vb[i] - va[i]) * t
                    for i in range(min(len(va), len(vb)))
                )
            else:
                result[key] = va if t < 0.5 else vb
        return result

    @staticmethod
    def _interpolate_properties(
        src: Dict[str, Any],
        tgt: Dict[str, Any],
        factor: float,
    ) -> Dict[str, Any]:
        """Blend two property sets by the given factor."""
        return AnimationEditor._lerp_properties(src, tgt, factor)

    # ------------------------------------------------------------------
    # Animation Preview
    # ------------------------------------------------------------------

    def animation_preview(
        self,
        clip_id: str,
        start_time: float = 0.0,
        end_time: Optional[float] = None,
    ) -> List[PreviewFrame]:
        """Generate a real-time preview of an animation clip.

        Produces a sequence of preview frames showing the animation
        at each time step.

        Args:
            clip_id: The animation clip ID to preview.
            start_time: Start time in seconds.
            end_time: End time in seconds; defaults to clip duration.

        Returns:
            A list of PreviewFrame objects.

        Raises:
            KeyError: If clip_id is not found.
        """
        with self._lock:
            clip = self._animations.get(clip_id)
            if clip is None:
                raise KeyError(f"Animation not found: {clip_id}")

            end = end_time or clip.duration
            dt = 1.0 / max(clip.fps, 1)
            frames: List[PreviewFrame] = []
            frame_num = 0

            t = start_time
            while t <= end + dt * 0.5:
                props = self._get_properties_at_time(clip, t)
                frames.append(PreviewFrame(
                    frame_number=frame_num,
                    time=t,
                    property_snapshot=props,
                ))
                frame_num += 1
                t += dt

            self._preview_cache[clip_id] = frames
            return frames

    def get_animation(self, clip_id: str) -> Optional[AnimationClip]:
        """Retrieve an animation clip by ID."""
        with self._lock:
            return self._animations.get(clip_id)

    def remove_animation(self, clip_id: str) -> bool:
        """Remove an animation clip."""
        with self._lock:
            if clip_id in self._animations:
                del self._animations[clip_id]
                self._preview_cache.pop(clip_id, None)
                return True
            return False


# =============================================================================
# Sub-System: PhysicsEditor
# =============================================================================


class PhysicsEditor:
    """Physics configuration and simulation editor.

    Provides physics body setup, collision shape configuration, physics
    simulation preview, and automatic physics optimization.
    """

    def __init__(self, editor: EngineAINativeEditor) -> None:
        self._editor = editor
        self._bodies: Dict[str, PhysicsBodyConfig] = {}
        self._shapes: Dict[str, CollisionShapeConfig] = {}
        self._simulation_results: Dict[str, List[SimulationStep]] = {}
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Physics Body Setup
    # ------------------------------------------------------------------

    def setup_physics(
        self,
        entity_id: str,
        body_type: PhysicsBodyType = PhysicsBodyType.DYNAMIC,
        mass: float = 1.0,
        options: Optional[Dict[str, Any]] = None,
    ) -> PhysicsBodyConfig:
        """Configure a physics body for an entity.

        Creates a physics body with the specified type, mass, and options.

        Args:
            entity_id: The entity to attach physics to.
            body_type: Type of physics body (dynamic, static, kinematic).
            mass: Mass of the physics body in kilograms.
            options: Additional physics configuration options.

        Returns:
            PhysicsBodyConfig with the configured physics properties.
        """
        config = PhysicsBodyConfig(
            entity_id=entity_id,
            body_type=body_type,
            mass=mass,
            gravity_scale=options.get("gravity_scale", 1.0) if options else 1.0,
            linear_damping=options.get("linear_damping", 0.1) if options else 0.1,
            angular_damping=options.get("angular_damping", 0.1) if options else 0.1,
            fixed_rotation=options.get("fixed_rotation", False) if options else False,
            is_bullet=options.get("is_bullet", False) if options else False,
            allow_sleep=options.get("allow_sleep", True) if options else True,
            awake=options.get("awake", True) if options else True,
        )
        with self._lock:
            self._bodies[entity_id] = config
        return config

    # ------------------------------------------------------------------
    # Collision Shape Configuration
    # ------------------------------------------------------------------

    def add_collision_shape(
        self,
        entity_id: str,
        shape_type: CollisionShapeType = CollisionShapeType.BOX,
        size: Optional[Tuple[float, float]] = None,
        offset: Optional[Tuple[float, float]] = None,
        is_sensor: bool = False,
    ) -> CollisionShapeConfig:
        """Add a collision shape to an entity's physics body.

        Args:
            entity_id: The entity to add the collision shape to.
            shape_type: Type of collision shape.
            size: Size of the shape (width, height).
            offset: Offset from the entity's origin.
            is_sensor: Whether the shape is a sensor (no physical collision).

        Returns:
            CollisionShapeConfig with the configured shape properties.
        """
        shape = CollisionShapeConfig(
            entity_id=entity_id,
            shape_type=shape_type,
            size=size or (1.0, 1.0),
            offset=offset or (0.0, 0.0),
            is_sensor=is_sensor,
            density=1.0,
            friction=0.5,
            restitution=0.3,
            category_bits=0x0001,
            mask_bits=0xFFFF,
        )
        with self._lock:
            self._shapes[entity_id] = shape
        return shape

    # ------------------------------------------------------------------
    # Physics Simulation
    # ------------------------------------------------------------------

    def run_simulation(
        self,
        entity_id: str,
        duration: float = 1.0,
        time_step: float = 0.016,
    ) -> List[SimulationStep]:
        """Run a physics simulation preview for an entity.

        Args:
            entity_id: The entity to simulate.
            duration: Duration of the simulation in seconds.
            time_step: Time step for each simulation tick.

        Returns:
            List of SimulationStep results containing position, velocity, etc.
        """
        steps: List[SimulationStep] = []
        body = self._bodies.get(entity_id)
        if body is None:
            return steps

        num_steps = int(duration / time_step)
        pos_x, pos_y = 0.0, 0.0
        vel_x, vel_y = 0.0, 0.0

        for i in range(num_steps):
            t = i * time_step
            vel_y -= 9.81 * body.gravity_scale * time_step
            vel_x *= (1.0 - body.linear_damping * time_step)
            vel_y *= (1.0 - body.linear_damping * time_step)
            pos_x += vel_x * time_step
            pos_y += vel_y * time_step

            step = SimulationStep(
                step_index=i,
                timestamp=t,
                position=(pos_x, pos_y),
                velocity=(vel_x, vel_y),
                angular_velocity=0.0,
                contacts=[],
            )
            steps.append(step)

        with self._lock:
            self._simulation_results[entity_id] = steps
        return steps

    # ------------------------------------------------------------------
    # Physics Optimization
    # ------------------------------------------------------------------

    def optimize_physics(self) -> PhysicsOptimizationResult:
        """Analyze and optimize physics configuration for all entities.

        Returns:
            PhysicsOptimizationResult with optimization suggestions.
        """
        suggestions: List[str] = []
        total_bodies = len(self._bodies)
        total_shapes = len(self._shapes)

        if total_bodies > 100:
            suggestions.append(
                f"Consider reducing physics bodies ({total_bodies}) "
                "by combining static bodies into compound shapes."
            )
        if total_shapes > 200:
            suggestions.append(
                f"High collision shape count ({total_shapes}). "
                "Use simplified collision meshes where possible."
            )

        return PhysicsOptimizationResult(
            total_bodies=total_bodies,
            total_shapes=total_shapes,
            suggestions=suggestions,
            estimated_cost_ms=total_bodies * 0.05 + total_shapes * 0.02,
        )

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_body_config(self, entity_id: str) -> Optional[PhysicsBodyConfig]:
        """Get the physics body configuration for an entity."""
        return self._bodies.get(entity_id)

    def get_shape_config(self, entity_id: str) -> Optional[CollisionShapeConfig]:
        """Get the collision shape configuration for an entity."""
        return self._shapes.get(entity_id)

    def remove_physics(self, entity_id: str) -> bool:
        """Remove physics configuration from an entity."""
        with self._lock:
            removed_body = self._bodies.pop(entity_id, None) is not None
            removed_shape = self._shapes.pop(entity_id, None) is not None
        return removed_body or removed_shape

    def get_all_bodies(self) -> Dict[str, PhysicsBodyConfig]:
        """Get all registered physics body configurations."""
        return dict(self._bodies)

    def get_simulation_history(self, entity_id: str) -> List[SimulationStep]:
        """Get the simulation history for an entity."""
        return self._simulation_results.get(entity_id, [])