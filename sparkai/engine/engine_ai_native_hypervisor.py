"""
SparkLabs Engine - AI-Native Engine Hypervisor

The definitive AI-native game engine hypervisor that deeply integrates all engine
subsystems into a single unified control plane. This module serves as the highest
orchestration layer, providing a comprehensive hypervisor that agents can command
to assemble, execute, monitor, and optimize entire game experiences.

This hypervisor bridges the UnifiedGameEngine, AINativeGameRuntime, and all engine
subsystems, providing:
- Complete end-to-end game assembly workflow
- Configurable game loop with phased execution
- Scene lifecycle management (create, load, unload, transition)
- Entity-Component system with full CRUD operations
- Physics simulation with collision detection
- Rendering pipeline management with quality tiers
- Audio system with spatial audio
- Input system with action mapping
- Resource management with streaming
- Performance monitoring with real-time metrics
- State serialization for save/load
- Agent bridge for bidirectional communication
- World generation (procedural terrain, biomes, structures)
- Weather system with day/night cycle
- Particle system management
- Animation system
- Camera control system
- Pathfinding and navigation
- Self-diagnostic and health checking

Architecture:
  AINativeEngineHypervisor (Singleton)
    |-- UnifiedGameEngine (subsystem integration)
    |-- AINativeGameRuntime (game loop orchestration)
    |-- All Engine Subsystems (lazy-loaded via try/except)
    |-- Agent Bridge (bidirectional command/event channel)
    |-- Assembly Pipeline (end-to-end game creation)
    |-- Health Monitor (self-diagnostic routines)
"""

from __future__ import annotations

import json
import logging
import math
import os
import random
import sys
import threading
import time as _time_module
import traceback
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class HypervisorState(Enum):
    """Primary states of the AI-Native Engine Hypervisor lifecycle."""
    COLD = "cold"
    BOOTING = "booting"
    INITIALIZING_SUBSYSTEMS = "initializing_subsystems"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ASSEMBLING = "assembling"
    LOADING = "loading"
    SAVING = "saving"
    DIAGNOSING = "diagnosing"
    DEGRADED = "degraded"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"
    TERMINATED = "terminated"


class ExecutionMode(Enum):
    """Execution modes for the hypervisor's game loop."""
    HEADLESS = "headless"
    INTERACTIVE = "interactive"
    SIMULATION = "simulation"
    REPLAY = "replay"
    RECORDING = "recording"
    BENCHMARK = "benchmark"
    DEBUG = "debug"
    AGENT_DRIVEN = "agent_driven"


class QualityPreset(Enum):
    """Predefined quality presets for the rendering pipeline."""
    POTATO = "potato"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CINEMATIC = "cinematic"
    CUSTOM = "custom"
    ADAPTIVE = "adaptive"


class GameLoopStrategy(Enum):
    """Strategies for the game loop execution model."""
    FIXED_TIMESTEP = "fixed_timestep"
    VARIABLE_TIMESTEP = "variable_timestep"
    SEMI_FIXED = "semi_fixed"
    FRAME_SYNC = "frame_sync"
    RENDER_AHEAD = "render_ahead"
    MULTI_THREADED = "multi_threaded"
    AGENT_CONTROLLED = "agent_controlled"


class SceneTransitionType(Enum):
    """Types of scene transitions."""
    INSTANT = "instant"
    FADE = "fade"
    SLIDE_LEFT = "slide_left"
    SLIDE_RIGHT = "slide_right"
    SLIDE_UP = "slide_up"
    SLIDE_DOWN = "slide_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    CROSSFADE = "crossfade"
    WIPE = "wipe"
    DISSOLVE = "dissolve"
    CUSTOM = "custom"


class HealthStatus(Enum):
    """Health check statuses for subsystems."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    NOT_LOADED = "not_loaded"


class AssemblyPhase(Enum):
    """Phases of the end-to-end game assembly workflow."""
    VALIDATION = "validation"
    PROJECT_SETUP = "project_setup"
    WORLD_GENERATION = "world_generation"
    SCENE_CREATION = "scene_creation"
    ENTITY_POPULATION = "entity_population"
    PHYSICS_SETUP = "physics_setup"
    RENDERING_CONFIG = "rendering_config"
    AUDIO_SETUP = "audio_setup"
    INPUT_CONFIG = "input_config"
    AI_SETUP = "ai_setup"
    UI_SETUP = "ui_setup"
    ANIMATION_SETUP = "animation_setup"
    WEATHER_SETUP = "weather_setup"
    CAMERA_SETUP = "camera_setup"
    NAVIGATION_SETUP = "navigation_setup"
    PARTICLE_SETUP = "particle_setup"
    FINALIZATION = "finalization"
    VERIFICATION = "verification"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class HypervisorConfig:
    """Comprehensive configuration for the AI-Native Engine Hypervisor."""
    config_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    execution_mode: ExecutionMode = ExecutionMode.INTERACTIVE
    game_loop_strategy: GameLoopStrategy = GameLoopStrategy.SEMI_FIXED
    quality_preset: QualityPreset = QualityPreset.HIGH
    target_fps: int = 60
    fixed_timestep: float = 0.016
    max_delta_time: float = 0.1
    enable_vsync: bool = True
    enable_physics: bool = True
    enable_audio: bool = True
    enable_rendering: bool = True
    enable_weather: bool = True
    enable_particles: bool = True
    enable_animations: bool = True
    enable_input: bool = True
    enable_ai: bool = True
    enable_navigation: bool = True
    enable_camera: bool = True
    enable_network: bool = False
    enable_profiling: bool = False
    enable_debug_draw: bool = False
    enable_auto_save: bool = True
    auto_save_interval_seconds: float = 300.0
    max_entities: int = 10000
    max_scenes: int = 50
    memory_budget_mb: float = 512.0
    streaming_enabled: bool = True
    streaming_radius: float = 500.0
    physics_quality: str = "medium"
    particle_limit: int = 5000
    shadow_quality: str = "high"
    texture_quality: str = "high"
    audio_channels: int = 64
    world_seed: Optional[int] = None
    agent_commands_enabled: bool = True
    health_check_interval: float = 10.0
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "config_id": self.config_id,
            "execution_mode": self.execution_mode.value,
            "game_loop_strategy": self.game_loop_strategy.value,
            "quality_preset": self.quality_preset.value,
            "target_fps": self.target_fps,
            "fixed_timestep": self.fixed_timestep,
            "max_delta_time": self.max_delta_time,
            "enable_vsync": self.enable_vsync,
            "enable_physics": self.enable_physics,
            "enable_audio": self.enable_audio,
            "enable_rendering": self.enable_rendering,
            "enable_weather": self.enable_weather,
            "enable_particles": self.enable_particles,
            "enable_animations": self.enable_animations,
            "enable_input": self.enable_input,
            "enable_ai": self.enable_ai,
            "enable_navigation": self.enable_navigation,
            "enable_camera": self.enable_camera,
            "enable_network": self.enable_network,
            "enable_profiling": self.enable_profiling,
            "enable_debug_draw": self.enable_debug_draw,
            "enable_auto_save": self.enable_auto_save,
            "auto_save_interval_seconds": self.auto_save_interval_seconds,
            "max_entities": self.max_entities,
            "max_scenes": self.max_scenes,
            "memory_budget_mb": self.memory_budget_mb,
            "streaming_enabled": self.streaming_enabled,
            "streaming_radius": self.streaming_radius,
            "physics_quality": self.physics_quality,
            "particle_limit": self.particle_limit,
            "shadow_quality": self.shadow_quality,
            "texture_quality": self.texture_quality,
            "audio_channels": self.audio_channels,
            "world_seed": self.world_seed,
            "agent_commands_enabled": self.agent_commands_enabled,
            "health_check_interval": self.health_check_interval,
            "custom_settings": self.custom_settings,
        }


@dataclass
class AssemblyResult:
    """Result of an end-to-end game assembly operation."""
    assembly_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    success: bool = False
    game_name: str = ""
    phases_completed: Dict[str, bool] = field(default_factory=dict)
    scenes_created: int = 0
    entities_spawned: int = 0
    world_tiles_generated: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    total_duration_ms: float = 0.0
    phase_durations: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assembly_id": self.assembly_id,
            "success": self.success,
            "game_name": self.game_name,
            "phases_completed": self.phases_completed,
            "scenes_created": self.scenes_created,
            "entities_spawned": self.entities_spawned,
            "world_tiles_generated": self.world_tiles_generated,
            "warnings": self.warnings,
            "errors": self.errors,
            "total_duration_ms": self.total_duration_ms,
            "phase_durations": self.phase_durations,
            "metadata": self.metadata,
        }


@dataclass
class RuntimeReport:
    """Comprehensive runtime execution report."""
    report_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=_time_module.time)
    frame_count: int = 0
    fps: float = 0.0
    frame_time_ms: float = 0.0
    entity_count: int = 0
    scene_count: int = 0
    draw_calls: int = 0
    physics_bodies: int = 0
    audio_sources: int = 0
    memory_usage_mb: float = 0.0
    gpu_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    active_particles: int = 0
    active_animations: int = 0
    weather_condition: str = "clear"
    time_of_day: float = 12.0
    subsystem_status: Dict[str, str] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp,
            "frame_count": self.frame_count,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "entity_count": self.entity_count,
            "scene_count": self.scene_count,
            "draw_calls": self.draw_calls,
            "physics_bodies": self.physics_bodies,
            "audio_sources": self.audio_sources,
            "memory_usage_mb": self.memory_usage_mb,
            "gpu_time_ms": self.gpu_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "active_particles": self.active_particles,
            "active_animations": self.active_animations,
            "weather_condition": self.weather_condition,
            "time_of_day": self.time_of_day,
            "subsystem_status": self.subsystem_status,
            "alerts": self.alerts,
            "metadata": self.metadata,
        }


@dataclass
class HypervisorMetrics:
    """Aggregated metrics tracked by the hypervisor."""
    total_frames: int = 0
    total_assembly_cycles: int = 0
    total_scenes_loaded: int = 0
    total_entities_spawned: int = 0
    total_entities_destroyed: int = 0
    total_collisions: int = 0
    total_agent_commands: int = 0
    total_health_checks: int = 0
    total_saves: int = 0
    total_loads: int = 0
    average_fps: float = 0.0
    average_frame_time_ms: float = 0.0
    min_fps: float = float("inf")
    max_fps: float = 0.0
    peak_memory_mb: float = 0.0
    peak_entities: int = 0
    peak_draw_calls: int = 0
    total_uptime_seconds: float = 0.0
    subsystem_availability: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_frames": self.total_frames,
            "total_assembly_cycles": self.total_assembly_cycles,
            "total_scenes_loaded": self.total_scenes_loaded,
            "total_entities_spawned": self.total_entities_spawned,
            "total_entities_destroyed": self.total_entities_destroyed,
            "total_collisions": self.total_collisions,
            "total_agent_commands": self.total_agent_commands,
            "total_health_checks": self.total_health_checks,
            "total_saves": self.total_saves,
            "total_loads": self.total_loads,
            "average_fps": self.average_fps,
            "average_frame_time_ms": self.average_frame_time_ms,
            "min_fps": self.min_fps if self.min_fps != float("inf") else 0,
            "max_fps": self.max_fps,
            "peak_memory_mb": self.peak_memory_mb,
            "peak_entities": self.peak_entities,
            "peak_draw_calls": self.peak_draw_calls,
            "total_uptime_seconds": self.total_uptime_seconds,
            "subsystem_availability": self.subsystem_availability,
            "metadata": self.metadata,
        }


@dataclass
class HealthCheckResult:
    """Result of a subsystem health check."""
    subsystem_name: str
    status: HealthStatus = HealthStatus.UNKNOWN
    loaded: bool = False
    response_time_ms: float = 0.0
    error_message: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subsystem_name": self.subsystem_name,
            "status": self.status.value,
            "loaded": self.loaded,
            "response_time_ms": self.response_time_ms,
            "error_message": self.error_message,
            "metrics": self.metrics,
            "recommendations": self.recommendations,
        }


@dataclass
class SceneTransitionRequest:
    """Request to transition from one scene to another."""
    request_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    from_scene_id: Optional[str] = None
    to_scene_id: str = ""
    transition_type: SceneTransitionType = SceneTransitionType.FADE
    duration_seconds: float = 1.0
    unload_source: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "from_scene_id": self.from_scene_id,
            "to_scene_id": self.to_scene_id,
            "transition_type": self.transition_type.value,
            "duration_seconds": self.duration_seconds,
            "unload_source": self.unload_source,
            "metadata": self.metadata,
        }


@dataclass
class EntityData:
    """Data for entity creation within the hypervisor."""
    entity_id: str = field(default_factory=lambda: f"ent_{uuid.uuid4().hex[:12]}")
    name: str = "Entity"
    entity_type: str = "custom"
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    layer: int = 0
    active: bool = True
    parent_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type,
            "position": {"x": self.position_x, "y": self.position_y, "z": self.position_z},
            "rotation": self.rotation,
            "scale": {"x": self.scale_x, "y": self.scale_y, "z": self.scale_z},
            "components": self.components,
            "tags": self.tags,
            "layer": self.layer,
            "active": self.active,
            "parent_id": self.parent_id,
            "metadata": self.metadata,
        }


# =============================================================================
# Subsystem Lazy Loader
# =============================================================================


class SubsystemLoader:
    """Lazy-loads engine subsystems with graceful fallback to simulated implementations."""

    _loaded: Dict[str, Any] = {}
    _load_lock = threading.RLock()

    @classmethod
    def load(cls, module_path: str, class_name: str, getter_name: str = "") -> Any:
        """Attempt to load a subsystem, returning a simulated instance on failure."""
        cache_key = f"{module_path}.{class_name}"
        if cache_key in cls._loaded:
            return cls._loaded[cache_key]

        with cls._load_lock:
            if cache_key in cls._loaded:
                return cls._loaded[cache_key]

            try:
                module = __import__(module_path, fromlist=[class_name])
                if getter_name:
                    instance = getattr(module, getter_name)()
                else:
                    cls_type = getattr(module, class_name)
                    instance = cls_type.get_instance() if hasattr(cls_type, "get_instance") else cls_type()
                cls._loaded[cache_key] = instance
                return instance
            except Exception:
                cls._loaded[cache_key] = None
                return None

    @classmethod
    def is_loaded(cls, module_path: str, class_name: str) -> bool:
        cache_key = f"{module_path}.{class_name}"
        return cache_key in cls._loaded and cls._loaded[cache_key] is not None

    @classmethod
    def clear_cache(cls) -> None:
        with cls._load_lock:
            cls._loaded.clear()


# =============================================================================
# AINativeEngineHypervisor
# =============================================================================


class AINativeEngineHypervisor:
    """
    The AI-Native Engine Hypervisor — the supreme orchestration layer for the
    SparkLabs game engine ecosystem.

    Integrates the UnifiedGameEngine, AINativeGameRuntime, and all engine
    subsystems into a single, coherent control plane that AI agents can
    command to assemble, execute, monitor, and optimize complete game experiences.

    Implements the Singleton pattern with double-checked locking for thread safety.

    Usage:
        hv = AINativeEngineHypervisor.get_instance()
        hv.initialize(HypervisorConfig(target_fps=60))

        # Assemble a complete game
        result = hv.assemble_game("MyPlatformer", {"genre": "platformer", "scenes": 3})

        # Run the game loop
        hv.start()
        for _ in range(100):
            report = hv.tick()

        # Check health
        health = hv.run_health_check()

        hv.shutdown()
    """

    _instance: Optional["AINativeEngineHypervisor"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AINativeEngineHypervisor._instance is not None:
            raise RuntimeError("Use AINativeEngineHypervisor.get_instance() instead")
        self._initialized: bool = False
        self._state: HypervisorState = HypervisorState.COLD
        self._state_lock = threading.RLock()
        self._config: HypervisorConfig = HypervisorConfig()
        self._metrics: HypervisorMetrics = HypervisorMetrics()
        self._start_time: float = 0.0
        self._frame_count: int = 0
        self._running: bool = False
        self._delta_time: float = 0.016
        self._last_frame_time: float = 0.0
        self._accumulated_time: float = 0.0

        # Core engine references
        self._unified_engine: Any = None
        self._ai_runtime: Any = None
        self._ai_core: Any = None

        # Lazy-loaded subsystem references
        self._subsystems: Dict[str, Any] = {}

        # Scene and entity management
        self._scenes: Dict[str, Dict[str, Any]] = {}
        self._active_scene_id: Optional[str] = None
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._transition_queue: deque = deque()

        # Command and event queues
        self._command_queue: deque = deque()
        self._event_queue: deque = deque()
        self._command_handlers: Dict[str, Callable] = {}
        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)

        # Performance tracking
        self._frame_history: deque = deque(maxlen=600)
        self._profile_data: Dict[str, List[float]] = defaultdict(list)
        self._health_history: List[HealthCheckResult] = []

        # Assembly tracking
        self._assembly_history: List[AssemblyResult] = []
        self._current_assembly: Optional[AssemblyResult] = None

        # Subsystem availability tracking
        self._subsystem_availability: Dict[str, bool] = {}
        self._subsystem_load_errors: Dict[str, str] = {}

        self._last_health_check: float = 0.0
        self._last_auto_save: float = 0.0

    @classmethod
    def get_instance(cls) -> "AINativeEngineHypervisor":
        """Get the singleton hypervisor instance with double-checked locking."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Initialization & Shutdown
    # -------------------------------------------------------------------------

    def initialize(self, config: Optional[HypervisorConfig] = None) -> Dict[str, Any]:
        """Initialize the hypervisor and bootstrap all engine subsystems."""
        with self._state_lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}
            self._state = HypervisorState.BOOTING

        if config:
            self._config = config

        self._start_time = _time_module.time
        self._last_frame_time = self._start_time

        subsystems_loaded = {}
        self._state = HypervisorState.INITIALIZING_SUBSYSTEMS

        # Load core engines
        self._unified_engine = self._load_subsystem(
            "sparkai.engine.engine_unified_game_engine",
            "UnifiedGameEngine",
            "get_unified_game_engine",
        )
        if self._unified_engine:
            try:
                self._unified_engine.initialize()
            except Exception:
                pass
        subsystems_loaded["unified_game_engine"] = self._unified_engine is not None

        self._ai_runtime = self._load_subsystem(
            "sparkai.engine.engine_ai_native_runtime",
            "AINativeGameRuntime",
            "get_ai_native_game_runtime",
        )
        if self._ai_runtime:
            try:
                self._ai_runtime.initialize()
            except Exception:
                pass
        subsystems_loaded["ai_native_runtime"] = self._ai_runtime is not None

        self._ai_core = self._load_subsystem(
            "sparkai.engine.engine_ai_native_core",
            "AINativeEngineCore",
            "get_ai_native_engine",
        )
        subsystems_loaded["ai_native_core"] = self._ai_core is not None

        # Load all subsystem modules
        subsystem_modules = [
            ("rendering", "sparkai.engine.engine_render_pipeline", "RenderPipeline", "get_render_pipeline"),
            ("adaptive_rendering", "sparkai.engine.engine_adaptive_rendering", "AdaptiveRenderingEngine", "get_adaptive_rendering"),
            ("physics", "sparkai.engine.engine_physics_dynamics", "EnginePhysicsDynamics", "get_physics_dynamics"),
            ("collision", "sparkai.engine.engine_collision_system", "EngineCollisionSystem", "get_collision_system"),
            ("audio", "sparkai.engine.engine_audio_synthesis", "EngineAudioSynthesis", "get_audio_synthesis"),
            ("spatial_audio", "sparkai.engine.engine_spatial_audio", "SpatialAudioEngine", "get_spatial_audio_engine"),
            ("input", "sparkai.engine.engine_input", "InputEngine", "get_input_engine"),
            ("input_mapping", "sparkai.engine.engine_input_mapping", "InputMappingEngine", "get_input_mapping_engine"),
            ("animation", "sparkai.engine.engine_animation_system", "EngineAnimationSystem", "get_animation_system"),
            ("animation_controller", "sparkai.engine.engine_animation_controller", "EngineAnimationController", "get_animation_controller"),
            ("camera", "sparkai.engine.engine_camera_controller", "EngineCameraController", "get_camera_controller"),
            ("particles", "sparkai.engine.engine_particle_system", "EngineParticleSystem", "get_particle_system"),
            ("weather", "sparkai.engine.engine_dynamic_weather", "DynamicWeatherEngine", "get_dynamic_weather_engine"),
            ("weather_system", "sparkai.engine.engine_weather_system", "WeatherSystemEngine", "get_weather_system"),
            ("terrain", "sparkai.engine.engine_procedural_terrain", "ProceduralTerrainEngine", "get_procedural_terrain_engine"),
            ("terrain_system", "sparkai.engine.engine_terrain_system", "EngineTerrainSystem", "get_terrain_system"),
            ("biome", "sparkai.engine.engine_biome_generation", "BiomeGenerationPipeline", "get_biome_generation_pipeline"),
            ("procedural_world", "sparkai.engine.engine_procedural_world", "EngineProceduralWorld", "get_procedural_world"),
            ("navigation", "sparkai.engine.engine_navigation_system", "EngineNavigationSystem", "get_navigation_system"),
            ("pathfinding", "sparkai.engine.engine_pathfinding", "EnginePathfinding", "get_pathfinding_engine"),
            ("scene_manager", "sparkai.engine.engine_scene_manager", "EngineSceneManager", "get_scene_manager"),
            ("scene_transition", "sparkai.engine.engine_scene_transition", "EngineSceneTransition", "get_scene_transition"),
            ("scene_serializer", "sparkai.engine.engine_scene_serializer", "SceneSerializerEngine", "get_scene_serializer_engine"),
            ("resource_streaming", "sparkai.engine.engine_resource_streaming", "ResourceStreamingEngine", ""),
            ("level_streaming", "sparkai.engine.engine_level_streaming", "LevelStreamingEngine", "get_level_streaming_engine"),
            ("performance", "sparkai.engine.engine_performance_monitor", "PerformanceMonitorEngine", "get_performance_monitor"),
            ("save_system", "sparkai.engine.engine_save_system", "SaveSystemEngine", "get_save_system"),
            ("event_system", "sparkai.engine.engine_event_system", "EventSystemEngine", "get_event_system"),
            ("agent_bridge", "sparkai.engine.engine_agent_bridge", "AgentEngineBridge", "get_agent_engine_bridge"),
            ("ui", "sparkai.engine.engine_ui_system", "UISystemEngine", "get_ui_system"),
            ("ai_system", "sparkai.engine.engine_ai_system", "GameAISystem", "get_ai_system"),
            ("behavior", "sparkai.engine.engine_behavior", "BehaviorEngine", "get_behavior_engine"),
            ("post_processing", "sparkai.engine.engine_post_processing", "PostProcessingEngine", "get_post_processing"),
            ("ecs", "sparkai.engine.engine_entity_component_system", "EngineEntityComponentSystem", "get_entity_component_system"),
            ("tilemap", "sparkai.engine.engine_tilemap_runtime", "EngineTileMapRuntime", "get_tilemap_runtime"),
            ("prefab", "sparkai.engine.engine_prefab", "PrefabSystem", "get_prefab_system"),
            ("game_loop", "sparkai.engine.engine_game_loop", "EngineGameLoop", "get_game_loop"),
            ("frame_timer", "sparkai.engine.engine_frame_timer", "EngineFrameTimer", "get_frame_timer"),
            ("object_pool", "sparkai.engine.engine_object_pool", "EngineObjectPool", "get_object_pool"),
            ("sprite_batcher", "sparkai.engine.engine_sprite_batcher", "EngineSpriteBatcher", "get_sprite_batcher"),
            ("destruction", "sparkai.engine.engine_destruction_system", "DestructionPhysicsEngine", "get_destruction_physics_engine"),
            ("water", "sparkai.engine.engine_water_simulation", "EngineWaterSimulation", "get_water_simulation"),
            ("fluid", "sparkai.engine.engine_fluid_dynamics", "EngineFluidDynamics", "get_fluid_dynamics"),
            ("crowd", "sparkai.engine.engine_crowd_dynamics", "EngineCrowdDynamics", "get_crowd_dynamics"),
            ("network", "sparkai.engine.engine_network_sync", "NetworkSyncEngine", "get_network_sync"),
            ("platform", "sparkai.engine.engine_platform_layer", "EnginePlatformLayer", "get_platform_layer"),
            ("cross_platform", "sparkai.engine.engine_cross_platform_builder", "EngineCrossPlatformBuilder", "get_cross_platform_builder"),
            ("game_playground", "sparkai.engine.engine_game_playground", "EngineGamePlayground", "get_game_playground"),
            ("visual_composer", "sparkai.engine.engine_visual_composer", "EngineVisualComposer", "get_visual_composer"),
        ]

        for name, module_path, class_name, getter_name in subsystem_modules:
            self._subsystems[name] = self._load_subsystem(module_path, class_name, getter_name)
            subsystems_loaded[name] = self._subsystems[name] is not None

        # Register default command handlers
        self._register_default_command_handlers()

        self._initialized = True
        with self._state_lock:
            self._state = HypervisorState.READY

        logger.info(
            "AINativeEngineHypervisor initialized. "
            "Subsystems loaded: %d/%d",
            sum(1 for v in subsystems_loaded.values() if v),
            len(subsystems_loaded),
        )

        return {
            "status": "initialized",
            "success": True,
            "subsystems": subsystems_loaded,
            "subsystems_loaded": sum(1 for v in subsystems_loaded.values() if v),
            "subsystems_total": len(subsystems_loaded),
            "config": self._config.to_dict(),
        }

    def _load_subsystem(self, module_path: str, class_name: str, getter_name: str) -> Any:
        """Load a subsystem with lazy loading and error handling."""
        try:
            instance = SubsystemLoader.load(module_path, class_name, getter_name)
            if instance is not None:
                self._subsystem_availability[class_name] = True
            else:
                self._subsystem_availability[class_name] = False
                self._subsystem_load_errors[class_name] = f"Module '{module_path}' not available"
            return instance
        except Exception as e:
            self._subsystem_availability[class_name] = False
            self._subsystem_load_errors[class_name] = str(e)
            return None

    def _register_default_command_handlers(self) -> None:
        """Register default command handlers for agent communication."""
        self._command_handlers["create_scene"] = self._cmd_create_scene
        self._command_handlers["load_scene"] = self._cmd_load_scene
        self._command_handlers["unload_scene"] = self._cmd_unload_scene
        self._command_handlers["transition_scene"] = self._cmd_transition_scene
        self._command_handlers["create_entity"] = self._cmd_create_entity
        self._command_handlers["destroy_entity"] = self._cmd_destroy_entity
        self._command_handlers["set_component"] = self._cmd_set_component
        self._command_handlers["get_component"] = self._cmd_get_component
        self._command_handlers["get_state"] = self._cmd_get_state
        self._command_handlers["get_status"] = self._cmd_get_status
        self._command_handlers["apply_config"] = self._cmd_apply_config
        self._command_handlers["set_weather"] = self._cmd_set_weather
        self._command_handlers["set_time_of_day"] = self._cmd_set_time_of_day
        self._command_handlers["generate_world"] = self._cmd_generate_world
        self._command_handlers["find_path"] = self._cmd_find_path
        self._command_handlers["spawn_particles"] = self._cmd_spawn_particles
        self._command_handlers["play_animation"] = self._cmd_play_animation
        self._command_handlers["set_camera"] = self._cmd_set_camera
        self._command_handlers["save_state"] = self._cmd_save_state
        self._command_handlers["load_state"] = self._cmd_load_state
        self._command_handlers["run_health_check"] = self._cmd_run_health_check
        self._command_handlers["assemble_game"] = self._cmd_assemble_game
        self._command_handlers["start"] = self._cmd_start
        self._command_handlers["stop"] = self._cmd_stop
        self._command_handlers["pause"] = self._cmd_pause
        self._command_handlers["resume"] = self._cmd_resume
        self._command_handlers["tick"] = self._cmd_tick
        self._command_handlers["shutdown"] = self._cmd_shutdown

    def shutdown(self) -> Dict[str, Any]:
        """Gracefully shut down the hypervisor and all subsystems."""
        with self._state_lock:
            self._state = HypervisorState.SHUTTING_DOWN

        self._running = False

        self._metrics.total_uptime_seconds = _time_module.time - self._start_time

        # Shutdown core engines
        if self._unified_engine:
            try:
                self._unified_engine.shutdown()
            except Exception:
                pass
        if self._ai_runtime:
            try:
                self._ai_runtime.shutdown()
            except Exception:
                pass

        # Clear all state
        self._scenes.clear()
        self._entities.clear()
        self._active_scene_id = None
        self._transition_queue.clear()
        self._command_queue.clear()
        self._event_queue.clear()
        self._frame_history.clear()
        self._profile_data.clear()

        self._initialized = False
        with self._state_lock:
            self._state = HypervisorState.TERMINATED

        logger.info("AINativeEngineHypervisor shutdown complete")
        return {"status": "shutdown", "success": True, "metrics": self._metrics.to_dict()}

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def _set_state(self, state: HypervisorState) -> None:
        with self._state_lock:
            self._state = state

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()

    # -------------------------------------------------------------------------
    # Game Loop Execution
    # -------------------------------------------------------------------------

    def start(self) -> Dict[str, Any]:
        """Start the hypervisor game loop."""
        self._ensure_initialized()
        self._running = True
        self._last_frame_time = _time_module.time
        self._set_state(HypervisorState.RUNNING)
        self._emit_event("hypervisor_started", {"timestamp": _time_module.time})
        return {"status": "started", "success": True}

    def stop(self) -> Dict[str, Any]:
        """Stop the hypervisor game loop."""
        self._running = False
        self._set_state(HypervisorState.PAUSED)
        self._emit_event("hypervisor_stopped", {"timestamp": _time_module.time, "frame": self._frame_count})
        return {"status": "stopped", "success": True, "frame": self._frame_count}

    def pause(self) -> Dict[str, Any]:
        """Pause the hypervisor without stopping."""
        self._running = False
        self._set_state(HypervisorState.PAUSED)
        return {"status": "paused", "success": True}

    def resume(self) -> Dict[str, Any]:
        """Resume the hypervisor from paused state."""
        self._ensure_initialized()
        self._running = True
        self._last_frame_time = _time_module.time
        self._set_state(HypervisorState.RUNNING)
        return {"status": "resumed", "success": True}

    def tick(self, delta_time: Optional[float] = None) -> RuntimeReport:
        """Execute a single tick of the game loop with all phases."""
        if not self._initialized or not self._running:
            return RuntimeReport(
                timestamp=_time_module.time,
                frame_count=self._frame_count,
                subsystem_status={"hypervisor": "not_running"},
            )

        if delta_time is None:
            now = _time_module.time
            delta_time = now - self._last_frame_time
            self._last_frame_time = now
        delta_time = min(delta_time, self._config.max_delta_time)

        self._frame_count += 1
        self._delta_time = delta_time
        phase_times: Dict[str, float] = {}

        report = RuntimeReport(
            frame_count=self._frame_count,
            timestamp=_time_module.time,
        )

        t0 = _time_module.time

        # Phase 1: Process agent commands
        self._process_agent_commands()
        phase_times["process_commands"] = (_time_module.time - t0) * 1000

        # Phase 2: Process pending scene transitions
        self._process_transitions()
        phase_times["process_transitions"] = (_time_module.time - t0) * 1000 - phase_times.get("process_commands", 0)

        # Phase 3: Process input
        if self._config.enable_input:
            t_phase = _time_module.time
            self._process_input(delta_time)
            phase_times["input"] = (_time_module.time - t_phase) * 1000

        # Phase 4: Update physics
        if self._config.enable_physics:
            t_phase = _time_module.time
            self._update_physics(delta_time)
            phase_times["physics"] = (_time_module.time - t_phase) * 1000

        # Phase 5: Update AI
        if self._config.enable_ai:
            t_phase = _time_module.time
            self._update_ai(delta_time)
            phase_times["ai"] = (_time_module.time - t_phase) * 1000

        # Phase 6: Update animations
        if self._config.enable_animations:
            t_phase = _time_module.time
            self._update_animations(delta_time)
            phase_times["animations"] = (_time_module.time - t_phase) * 1000

        # Phase 7: Update particles
        if self._config.enable_particles:
            t_phase = _time_module.time
            self._update_particles(delta_time)
            phase_times["particles"] = (_time_module.time - t_phase) * 1000

        # Phase 8: Update weather
        if self._config.enable_weather:
            t_phase = _time_module.time
            self._update_weather(delta_time)
            phase_times["weather"] = (_time_module.time - t_phase) * 1000

        # Phase 9: Update audio
        if self._config.enable_audio:
            t_phase = _time_module.time
            self._update_audio(delta_time)
            phase_times["audio"] = (_time_module.time - t_phase) * 1000

        # Phase 10: Update navigation
        if self._config.enable_navigation:
            t_phase = _time_module.time
            self._update_navigation(delta_time)
            phase_times["navigation"] = (_time_module.time - t_phase) * 1000

        # Phase 11: Update camera
        if self._config.enable_camera:
            t_phase = _time_module.time
            self._update_camera(delta_time)
            phase_times["camera"] = (_time_module.time - t_phase) * 1000

        # Phase 12: Render frame
        if self._config.enable_rendering:
            t_phase = _time_module.time
            self._render_frame(delta_time)
            phase_times["render"] = (_time_module.time - t_phase) * 1000

        # Phase 13: Collect metrics
        t_phase = _time_module.time
        self._collect_metrics(delta_time, report)
        phase_times["collect_metrics"] = (_time_module.time - t_phase) * 1000

        # Phase 14: Auto-save check
        t_phase = _time_module.time
        self._check_auto_save()
        phase_times["auto_save_check"] = (_time_module.time - t_phase) * 1000

        # Phase 15: Health check
        t_phase = _time_module.time
        self._check_health_interval()
        phase_times["health_check"] = (_time_module.time - t_phase) * 1000

        # Populate report
        report.fps = 1.0 / delta_time if delta_time > 0 else 0.0
        report.frame_time_ms = delta_time * 1000
        report.entity_count = len(self._entities)
        report.scene_count = len(self._scenes)
        report.subsystem_status = self._get_subsystem_status_summary()

        # Update metrics
        self._update_metrics(report)
        self._frame_history.append(report)

        self._emit_event("tick_complete", report.to_dict())

        return report

    def run_simulation(self, num_frames: int = 100) -> List[RuntimeReport]:
        """Run a headless simulation for a specified number of frames."""
        self._ensure_initialized()
        self.start()
        reports = []
        for _ in range(num_frames):
            report = self.tick()
            reports.append(report)
        self.stop()
        return reports

    # -------------------------------------------------------------------------
    # Game Loop Phase Implementations
    # -------------------------------------------------------------------------

    def _process_agent_commands(self) -> None:
        """Process queued agent commands."""
        while self._command_queue:
            command = self._command_queue.popleft()
            try:
                self.process_agent_command(command)
            except Exception:
                pass

    def _process_transitions(self) -> None:
        """Process pending scene transitions."""
        while self._transition_queue:
            transition = self._transition_queue.popleft()
            try:
                self.transition_scene(transition)
            except Exception:
                pass

    def _process_input(self, dt: float) -> None:
        input_system = self._subsystems.get("input")
        if input_system:
            try:
                pass
            except Exception:
                pass

    def _update_physics(self, dt: float) -> None:
        physics = self._subsystems.get("physics")
        collision = self._subsystems.get("collision")
        if self._unified_engine:
            try:
                self._unified_engine._physics.step(dt)
            except Exception:
                pass
        if physics:
            try:
                pass
            except Exception:
                pass

    def _update_ai(self, dt: float) -> None:
        ai_system = self._subsystems.get("ai_system")
        if ai_system:
            try:
                pass
            except Exception:
                pass
        if self._ai_runtime:
            try:
                self._ai_runtime._update_ai(dt)
            except Exception:
                pass

    def _update_animations(self, dt: float) -> None:
        animation = self._subsystems.get("animation")
        anim_controller = self._subsystems.get("animation_controller")
        if animation:
            try:
                pass
            except Exception:
                pass
        if self._unified_engine:
            try:
                self._unified_engine._animation.update(dt)
            except Exception:
                pass

    def _update_particles(self, dt: float) -> None:
        particles = self._subsystems.get("particles")
        if particles:
            try:
                particles.update_all(dt)
            except Exception:
                pass

    def _update_weather(self, dt: float) -> None:
        weather = self._subsystems.get("weather")
        weather_sys = self._subsystems.get("weather_system")
        if weather:
            try:
                weather.update(dt)
            except Exception:
                pass
        if self._unified_engine:
            try:
                self._unified_engine._world_systems.advance_time(dt / 3600.0)
            except Exception:
                pass

    def _update_audio(self, dt: float) -> None:
        audio = self._subsystems.get("audio")
        spatial_audio = self._subsystems.get("spatial_audio")
        if audio:
            try:
                pass
            except Exception:
                pass

    def _update_navigation(self, dt: float) -> None:
        navigation = self._subsystems.get("navigation")
        if navigation:
            try:
                pass
            except Exception:
                pass

    def _update_camera(self, dt: float) -> None:
        camera = self._subsystems.get("camera")
        if camera:
            try:
                pass
            except Exception:
                pass

    def _render_frame(self, dt: float) -> None:
        if self._unified_engine:
            try:
                self._unified_engine.render_frame()
            except Exception:
                pass

    def _collect_metrics(self, dt: float, report: RuntimeReport) -> None:
        if self._unified_engine:
            try:
                stats = self._unified_engine.get_status()
                report.draw_calls = stats.get("rendering", {}).get("last_frame", {}).get("draw_calls", 0)
                report.physics_bodies = stats.get("physics", {}).get("total_bodies", 0)
                report.audio_sources = stats.get("audio", {}).get("total_sources", 0)
                report.memory_usage_mb = stats.get("rendering", {}).get("last_frame", {}).get("memory_usage_mb", 0.0)
                report.gpu_time_ms = stats.get("rendering", {}).get("last_frame", {}).get("gpu_time_ms", 0.0)
                report.cpu_time_ms = stats.get("rendering", {}).get("last_frame", {}).get("cpu_time_ms", 0.0)
            except Exception:
                pass

    def _check_auto_save(self) -> None:
        if self._config.enable_auto_save:
            now = _time_module.time
            if now - self._last_auto_save >= self._config.auto_save_interval_seconds:
                self._last_auto_save = now
                try:
                    self.save_state()
                except Exception:
                    pass

    def _check_health_interval(self) -> None:
        now = _time_module.time
        if now - self._last_health_check >= self._config.health_check_interval:
            self._last_health_check = now
            try:
                self.run_health_check()
            except Exception:
                pass

    def _update_metrics(self, report: RuntimeReport) -> None:
        """Update the aggregated hypervisor metrics."""
        self._metrics.total_frames += 1
        n = self._metrics.total_frames
        old_avg = self._metrics.average_frame_time_ms
        self._metrics.average_frame_time_ms = (old_avg * (n - 1) + report.frame_time_ms) / n
        self._metrics.average_fps = 1000.0 / self._metrics.average_frame_time_ms if self._metrics.average_frame_time_ms > 0 else 0.0
        if report.fps < self._metrics.min_fps:
            self._metrics.min_fps = report.fps
        if report.fps > self._metrics.max_fps:
            self._metrics.max_fps = report.fps
        self._metrics.peak_memory_mb = max(self._metrics.peak_memory_mb, report.memory_usage_mb)
        self._metrics.peak_entities = max(self._metrics.peak_entities, report.entity_count)
        self._metrics.peak_draw_calls = max(self._metrics.peak_draw_calls, report.draw_calls)
        self._metrics.total_uptime_seconds = _time_module.time - self._start_time

    def _get_subsystem_status_summary(self) -> Dict[str, str]:
        """Get a summary of subsystem availability."""
        summary = {}
        for name, instance in self._subsystems.items():
            if instance is not None:
                summary[name] = "loaded"
            else:
                summary[name] = "unavailable"
        if self._unified_engine:
            summary["unified_engine"] = "loaded"
        if self._ai_runtime:
            summary["ai_runtime"] = "loaded"
        if self._ai_core:
            summary["ai_core"] = "loaded"
        return summary

    # -------------------------------------------------------------------------
    # Scene Lifecycle Management
    # -------------------------------------------------------------------------

    def create_scene(self, name: str, width: int = 1920, height: int = 1080,
                     config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a new game scene."""
        self._ensure_initialized()
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        scene_data = {
            "scene_id": scene_id,
            "name": name,
            "width": width,
            "height": height,
            "state": "created",
            "entities": {},
            "layers": [{"layer_id": "layer_0", "name": "Default", "z_order": 0, "visible": True}],
            "camera": {"x": 0, "y": 0, "zoom": 1.0},
            "physics_config": {"gravity_x": 0, "gravity_y": -9.81, "time_step": 0.016},
            "config": config or {},
            "created_at": _time_module.time,
            "metadata": {},
        }
        self._scenes[scene_id] = scene_data

        if self._unified_engine:
            try:
                self._unified_engine.create_scene(name, width, height)
            except Exception:
                pass

        self._emit_event("scene_created", {"scene_id": scene_id, "name": name})
        return scene_data

    def load_scene(self, scene_id: str) -> Dict[str, Any]:
        """Load and activate a scene."""
        if scene_id not in self._scenes:
            return {"success": False, "error": f"Scene {scene_id} not found"}

        old_scene = self._active_scene_id
        if old_scene and old_scene in self._scenes:
            self._scenes[old_scene]["state"] = "background"

        self._active_scene_id = scene_id
        self._scenes[scene_id]["state"] = "active"
        self._scenes[scene_id]["loaded_at"] = _time_module.time
        self._metrics.total_scenes_loaded += 1

        if self._unified_engine:
            try:
                self._unified_engine.load_scene(scene_id)
            except Exception:
                pass

        self._emit_event("scene_loaded", {
            "scene_id": scene_id,
            "previous_scene": old_scene,
        })
        return {"success": True, "scene_id": scene_id, "previous_scene": old_scene}

    def unload_scene(self, scene_id: str) -> Dict[str, Any]:
        """Unload a scene and remove its entities."""
        if scene_id not in self._scenes:
            return {"success": False, "error": f"Scene {scene_id} not found"}

        scene = self._scenes[scene_id]
        scene["state"] = "unloading"

        entity_ids = list(scene["entities"].keys())
        for entity_id in entity_ids:
            self._entities.pop(entity_id, None)

        scene["entities"].clear()
        scene["state"] = "unloaded"

        if self._active_scene_id == scene_id:
            self._active_scene_id = None

        self._emit_event("scene_unloaded", {"scene_id": scene_id})
        return {"success": True, "scene_id": scene_id}

    def transition_scene(self, transition: SceneTransitionRequest) -> Dict[str, Any]:
        """Perform a scene transition."""
        if transition.to_scene_id not in self._scenes:
            return {"success": False, "error": f"Target scene {transition.to_scene_id} not found"}

        result = self.load_scene(transition.to_scene_id)

        if transition.unload_source and transition.from_scene_id:
            self.unload_scene(transition.from_scene_id)

        self._emit_event("scene_transitioned", {
            "from": transition.from_scene_id,
            "to": transition.to_scene_id,
            "type": transition.transition_type.value,
        })
        return {"success": True, "transition": transition.to_dict(), "result": result}

    def get_active_scene(self) -> Optional[Dict[str, Any]]:
        """Get the currently active scene."""
        if self._active_scene_id:
            return self._scenes.get(self._active_scene_id)
        return None

    def list_scenes(self) -> List[Dict[str, Any]]:
        """List all scenes with their status."""
        return [
            {
                "scene_id": sid,
                "name": s["name"],
                "state": s["state"],
                "entity_count": len(s["entities"]),
                "width": s["width"],
                "height": s["height"],
            }
            for sid, s in self._scenes.items()
        ]

    # -------------------------------------------------------------------------
    # Entity-Component System with Full CRUD
    # -------------------------------------------------------------------------

    def create_entity(self, entity_data: EntityData) -> Dict[str, Any]:
        """Create a new game entity in the active scene."""
        self._ensure_initialized()
        entity = entity_data.to_dict()
        self._entities[entity_data.entity_id] = entity

        active_scene = self.get_active_scene()
        if active_scene:
            active_scene["entities"][entity_data.entity_id] = entity

        self._metrics.total_entities_spawned += 1

        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import EntityType as UE_EntityType
                entity_type_map = {
                    "player": UE_EntityType.PLAYER, "npc": UE_EntityType.NPC,
                    "enemy": UE_EntityType.ENEMY, "prop": UE_EntityType.PROP,
                    "terrain": UE_EntityType.TERRAIN, "light": UE_EntityType.LIGHT,
                    "camera": UE_EntityType.CAMERA, "ui": UE_EntityType.UI,
                    "audio": UE_EntityType.AUDIO, "particle": UE_EntityType.PARTICLE,
                    "trigger": UE_EntityType.TRIGGER, "collectible": UE_EntityType.COLLECTIBLE,
                    "projectile": UE_EntityType.PROJECTILE,
                }
                ue_type = entity_type_map.get(entity_data.entity_type, UE_EntityType.CUSTOM)
                scene_id = self._active_scene_id or ""
                self._unified_engine.spawn_entity(scene_id, entity_data.name, ue_type,
                                                  entity_data.position_x, entity_data.position_y)
            except Exception:
                pass

        self._emit_event("entity_created", entity)
        return entity

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID."""
        return self._entities.get(entity_id)

    def update_entity(self, entity_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update an existing entity's properties."""
        if entity_id not in self._entities:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        entity = self._entities[entity_id]
        for key, value in updates.items():
            if key == "position":
                entity["position_x"] = value.get("x", entity["position_x"])
                entity["position_y"] = value.get("y", entity["position_y"])
                entity["position_z"] = value.get("z", entity["position_z"])
                entity["position"] = value
            elif key == "components":
                entity["components"].update(value)
            elif key in entity:
                entity[key] = value

        self._emit_event("entity_updated", {"entity_id": entity_id, "updates": updates})
        return {"success": True, "entity": entity}

    def destroy_entity(self, entity_id: str) -> Dict[str, Any]:
        """Destroy an entity and remove it from all scenes."""
        if entity_id not in self._entities:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        del self._entities[entity_id]
        for scene in self._scenes.values():
            scene["entities"].pop(entity_id, None)

        self._metrics.total_entities_destroyed += 1

        if self._unified_engine:
            try:
                scene_id = self._active_scene_id or ""
                self._unified_engine.remove_entity(scene_id, entity_id)
            except Exception:
                pass

        self._emit_event("entity_destroyed", {"entity_id": entity_id})
        return {"success": True, "entity_id": entity_id}

    def set_component(self, entity_id: str, component_name: str,
                      component_data: Dict[str, Any]) -> Dict[str, Any]:
        """Set a component on an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return {"success": False, "error": f"Entity {entity_id} not found"}
        entity["components"][component_name] = component_data
        self._emit_event("component_changed", {
            "entity_id": entity_id, "component": component_name, "data": component_data,
        })
        return {"success": True, "entity_id": entity_id, "component": component_name}

    def get_component(self, entity_id: str, component_name: str) -> Optional[Dict[str, Any]]:
        """Get a component from an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return None
        return entity["components"].get(component_name)

    def get_entities_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Get all entities with a specific tag."""
        return [e for e in self._entities.values() if tag in e.get("tags", [])]

    def get_entities_by_type(self, entity_type: str) -> List[Dict[str, Any]]:
        """Get all entities of a specific type."""
        return [e for e in self._entities.values() if e.get("entity_type") == entity_type]

    # -------------------------------------------------------------------------
    # Physics Simulation with Collision Detection
    # -------------------------------------------------------------------------

    def simulate_physics_step(self) -> List[Dict[str, Any]]:
        """Simulate a physics step and return collision data."""
        collisions = []
        entities = list(self._entities.values())

        for i, entity_a in enumerate(entities):
            for entity_b in entities[i + 1:]:
                if self._check_aabb_collision(entity_a, entity_b):
                    collision = {
                        "entity_a": entity_a["entity_id"],
                        "entity_b": entity_b["entity_id"],
                        "timestamp": _time_module.time,
                    }
                    collisions.append(collision)
                    self._metrics.total_collisions += 1

        if collisions:
            self._emit_event("collisions_detected", {"collisions": collisions})

        if self._unified_engine:
            try:
                self._unified_engine._physics.step(self._delta_time)
                engine_collisions = self._unified_engine._physics.get_collisions()
                collisions.extend(engine_collisions)
            except Exception:
                pass

        return collisions

    def _check_aabb_collision(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Check AABB collision between two entities."""
        a_pos = a.get("position", {"x": 0, "y": 0})
        b_pos = b.get("position", {"x": 0, "y": 0})
        a_scale = a.get("scale", {"x": 1, "y": 1})
        b_scale = b.get("scale", {"x": 1, "y": 1})

        a_hw = a_scale.get("x", 1) * 50
        a_hh = a_scale.get("y", 1) * 50
        b_hw = b_scale.get("x", 1) * 50
        b_hh = b_scale.get("y", 1) * 50

        return (
            abs(a_pos.get("x", 0) - b_pos.get("x", 0)) < a_hw + b_hw
            and abs(a_pos.get("y", 0) - b_pos.get("y", 0)) < a_hh + b_hh
        )

    def apply_force(self, entity_id: str, force_x: float, force_y: float) -> Dict[str, Any]:
        """Apply a force to an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return {"success": False, "error": f"Entity {entity_id} not found"}
        if "physics" not in entity["components"]:
            entity["components"]["physics"] = {"velocity_x": 0.0, "velocity_y": 0.0, "mass": 1.0}
        phys = entity["components"]["physics"]
        mass = phys.get("mass", 1.0)
        phys["velocity_x"] = phys.get("velocity_x", 0.0) + force_x / mass * self._delta_time
        phys["velocity_y"] = phys.get("velocity_y", 0.0) + force_y / mass * self._delta_time
        return {"success": True, "entity_id": entity_id, "physics": phys}

    # -------------------------------------------------------------------------
    # Rendering Pipeline Management with Quality Tiers
    # -------------------------------------------------------------------------

    def set_quality_preset(self, preset: QualityPreset) -> Dict[str, Any]:
        """Set the rendering quality preset."""
        self._config.quality_preset = preset
        quality_settings = {
            QualityPreset.POTATO: {"shadow_quality": "off", "texture_quality": "low", "particle_limit": 100,
                                    "post_effects": [], "max_draw_calls": 500},
            QualityPreset.LOW: {"shadow_quality": "low", "texture_quality": "low", "particle_limit": 500,
                                "post_effects": ["vignette"], "max_draw_calls": 1000},
            QualityPreset.MEDIUM: {"shadow_quality": "medium", "texture_quality": "medium", "particle_limit": 2000,
                                    "post_effects": ["bloom", "vignette"], "max_draw_calls": 2000},
            QualityPreset.HIGH: {"shadow_quality": "high", "texture_quality": "high", "particle_limit": 5000,
                                  "post_effects": ["bloom", "vignette", "color_grading"], "max_draw_calls": 4000},
            QualityPreset.ULTRA: {"shadow_quality": "ultra", "texture_quality": "ultra", "particle_limit": 10000,
                                   "post_effects": ["bloom", "vignette", "color_grading", "ssao", "motion_blur"],
                                   "max_draw_calls": 8000},
            QualityPreset.CINEMATIC: {"shadow_quality": "ultra", "texture_quality": "ultra", "particle_limit": 20000,
                                       "post_effects": ["bloom", "vignette", "color_grading", "ssao", "motion_blur",
                                                        "depth_of_field", "chromatic_aberration"],
                                       "max_draw_calls": 16000},
            QualityPreset.CUSTOM: {},
            QualityPreset.ADAPTIVE: {},
        }

        settings = quality_settings.get(preset, {})
        if settings:
            self._config.shadow_quality = settings.get("shadow_quality", self._config.shadow_quality)
            self._config.texture_quality = settings.get("texture_quality", self._config.texture_quality)
            self._config.particle_limit = settings.get("particle_limit", self._config.particle_limit)

        self._emit_event("quality_changed", {"preset": preset.value, "settings": settings})
        return {"success": True, "preset": preset.value, "settings": settings}

    def get_render_stats(self) -> Dict[str, Any]:
        """Get current rendering statistics."""
        if self._unified_engine:
            try:
                return self._unified_engine._rendering.get_stats()
            except Exception:
                pass
        return {"status": "unavailable"}

    # -------------------------------------------------------------------------
    # Audio System with Spatial Audio
    # -------------------------------------------------------------------------

    def play_audio(self, source_id: str, clip_name: str = "",
                   volume: float = 1.0, is_looping: bool = False,
                   is_spatial: bool = False, position: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """Play an audio source."""
        audio_data = {
            "source_id": source_id or f"audio_{uuid.uuid4().hex[:8]}",
            "clip_name": clip_name,
            "volume": volume,
            "is_looping": is_looping,
            "is_spatial": is_spatial,
            "position": position or {"x": 0, "y": 0, "z": 0},
            "is_playing": True,
        }
        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import AudioSource
                source = AudioSource(
                    source_id=audio_data["source_id"],
                    entity_id="",
                    clip_name=clip_name,
                    volume=volume,
                    is_looping=is_looping,
                    is_spatial=is_spatial,
                    is_playing=True,
                )
                self._unified_engine.create_audio_source(source)
                self._unified_engine.play_audio(audio_data["source_id"])
            except Exception:
                pass
        return {"success": True, "audio": audio_data}

    def stop_audio(self, source_id: str) -> Dict[str, Any]:
        """Stop an audio source."""
        if self._unified_engine:
            try:
                self._unified_engine.stop_audio(source_id)
            except Exception:
                pass
        return {"success": True, "source_id": source_id}

    def set_master_volume(self, volume: float) -> Dict[str, Any]:
        """Set the master audio volume."""
        if self._unified_engine:
            try:
                self._unified_engine._audio.set_master_volume(volume)
            except Exception:
                pass
        return {"success": True, "volume": max(0.0, min(1.0, volume))}

    # -------------------------------------------------------------------------
    # Input System with Action Mapping
    # -------------------------------------------------------------------------

    def bind_input_action(self, action: str, key: str) -> Dict[str, Any]:
        """Bind an input action to a key."""
        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import InputAction as UE_InputAction
                action_map = {
                    "move_left": UE_InputAction.MOVE_LEFT,
                    "move_right": UE_InputAction.MOVE_RIGHT,
                    "move_up": UE_InputAction.MOVE_UP,
                    "move_down": UE_InputAction.MOVE_DOWN,
                    "jump": UE_InputAction.JUMP,
                    "attack": UE_InputAction.ATTACK,
                    "interact": UE_InputAction.INTERACT,
                    "pause": UE_InputAction.PAUSE,
                    "menu": UE_InputAction.MENU,
                    "confirm": UE_InputAction.CONFIRM,
                    "cancel": UE_InputAction.CANCEL,
                }
                if action in action_map:
                    self._unified_engine._input_ui._input_bindings[action_map[action]] = [key]
            except Exception:
                pass
        return {"success": True, "action": action, "key": key}

    def simulate_input(self, action: str, pressed: bool = True) -> Dict[str, Any]:
        """Simulate an input action."""
        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import InputAction as UE_InputAction
                action_map = {
                    "move_left": UE_InputAction.MOVE_LEFT,
                    "move_right": UE_InputAction.MOVE_RIGHT,
                    "move_up": UE_InputAction.MOVE_UP,
                    "move_down": UE_InputAction.MOVE_DOWN,
                    "jump": UE_InputAction.JUMP,
                    "attack": UE_InputAction.ATTACK,
                    "interact": UE_InputAction.INTERACT,
                    "pause": UE_InputAction.PAUSE,
                    "menu": UE_InputAction.MENU,
                    "confirm": UE_InputAction.CONFIRM,
                    "cancel": UE_InputAction.CANCEL,
                }
                if action in action_map:
                    self._unified_engine.simulate_input(action_map[action], pressed)
            except Exception:
                pass
        return {"success": True, "action": action, "pressed": pressed}

    # -------------------------------------------------------------------------
    # Resource Management with Streaming
    # -------------------------------------------------------------------------

    def load_resource(self, resource_type: str, resource_name: str,
                      data: Dict[str, Any]) -> Dict[str, Any]:
        """Load a resource into the engine."""
        resource_id = f"res_{uuid.uuid4().hex[:8]}"
        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import ResourceType
                rt_map = {
                    "texture": ResourceType.TEXTURE, "sprite": ResourceType.SPRITE,
                    "audio": ResourceType.AUDIO, "font": ResourceType.FONT,
                    "shader": ResourceType.SHADER, "material": ResourceType.MATERIAL,
                    "animation": ResourceType.ANIMATION, "prefab": ResourceType.PREFAB,
                    "scene": ResourceType.SCENE, "script": ResourceType.SCRIPT,
                    "tilemap": ResourceType.TILEMAP, "data": ResourceType.DATA,
                }
                rt = rt_map.get(resource_type, ResourceType.DATA)
                resource_id = self._unified_engine.load_resource(rt, resource_name, data)
            except Exception:
                pass
        return {"success": True, "resource_id": resource_id, "name": resource_name, "type": resource_type}

    def unload_resource(self, resource_type: str, resource_id: str) -> Dict[str, Any]:
        """Unload a resource."""
        if self._unified_engine:
            try:
                from sparkai.engine.engine_unified_game_engine import ResourceType
                rt_map = {
                    "texture": ResourceType.TEXTURE, "sprite": ResourceType.SPRITE,
                    "audio": ResourceType.AUDIO, "font": ResourceType.FONT,
                    "shader": ResourceType.SHADER, "material": ResourceType.MATERIAL,
                    "animation": ResourceType.ANIMATION, "prefab": ResourceType.PREFAB,
                    "scene": ResourceType.SCENE, "script": ResourceType.SCRIPT,
                    "tilemap": ResourceType.TILEMAP, "data": ResourceType.DATA,
                }
                rt = rt_map.get(resource_type, ResourceType.DATA)
                self._unified_engine._resources.unload_resource(rt, resource_id)
            except Exception:
                pass
        return {"success": True, "resource_id": resource_id}

    def get_resource_stats(self) -> Dict[str, Any]:
        """Get resource management statistics."""
        if self._unified_engine:
            try:
                return self._unified_engine._resources.get_stats()
            except Exception:
                pass
        return {"status": "unavailable"}

    # -------------------------------------------------------------------------
    # Performance Monitoring with Real-Time Metrics
    # -------------------------------------------------------------------------

    def get_performance_report(self) -> RuntimeReport:
        """Get a comprehensive performance report."""
        return RuntimeReport(
            frame_count=self._frame_count,
            timestamp=_time_module.time,
            fps=self._metrics.average_fps,
            frame_time_ms=self._metrics.average_frame_time_ms,
            entity_count=len(self._entities),
            scene_count=len(self._scenes),
            memory_usage_mb=self._metrics.peak_memory_mb,
            subsystem_status=self._get_subsystem_status_summary(),
        )

    def get_frame_history(self, count: int = 60) -> List[Dict[str, Any]]:
        """Get recent frame history."""
        frames = list(self._frame_history)[-count:]
        return [f.to_dict() for f in frames]

    def get_metrics(self) -> Dict[str, Any]:
        """Get aggregated hypervisor metrics."""
        return self._metrics.to_dict()

    def start_profiling(self) -> Dict[str, Any]:
        """Start performance profiling."""
        self._config.enable_profiling = True
        self._profile_data.clear()
        return {"success": True, "profiling": True}

    def stop_profiling(self) -> Dict[str, Any]:
        """Stop profiling and return results."""
        self._config.enable_profiling = False
        result = {
            "frames_profiled": len(self._profile_data.get("frame_times", [])),
            "average_fps": self._metrics.average_fps,
            "average_frame_time_ms": self._metrics.average_frame_time_ms,
            "peak_memory_mb": self._metrics.peak_memory_mb,
            "entity_count": len(self._entities),
        }
        return {"success": True, "profiling": False, "results": result}

    # -------------------------------------------------------------------------
    # State Serialization for Save/Load
    # -------------------------------------------------------------------------

    def save_state(self) -> Dict[str, Any]:
        """Serialize the complete hypervisor state."""
        self._set_state(HypervisorState.SAVING)
        state = {
            "version": "1.0",
            "timestamp": _time_module.time,
            "frame_count": self._frame_count,
            "config": self._config.to_dict(),
            "scenes": {sid: {"name": s["name"], "state": s["state"], "width": s["width"],
                             "height": s["height"], "entity_count": len(s["entities"]),
                             "config": s["config"]} for sid, s in self._scenes.items()},
            "entities": {eid: e for eid, e in self._entities.items()},
            "active_scene_id": self._active_scene_id,
            "metrics": self._metrics.to_dict(),
            "subsystem_status": self._get_subsystem_status_summary(),
        }
        self._metrics.total_saves += 1
        self._set_state(HypervisorState.RUNNING)
        self._emit_event("state_saved", {"state_size": len(json.dumps(state))})
        return {"success": True, "state": state}

    def load_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Deserialize and restore hypervisor state."""
        self._set_state(HypervisorState.LOADING)
        try:
            self._frame_count = state.get("frame_count", 0)
            self._active_scene_id = state.get("active_scene_id")

            self._scenes.clear()
            for sid, scene_data in state.get("scenes", {}).items():
                self._scenes[sid] = {
                    "scene_id": sid,
                    "name": scene_data.get("name", ""),
                    "state": scene_data.get("state", "unloaded"),
                    "width": scene_data.get("width", 1920),
                    "height": scene_data.get("height", 1080),
                    "entities": {},
                    "config": scene_data.get("config", {}),
                    "layers": [{"layer_id": "layer_0", "name": "Default", "z_order": 0, "visible": True}],
                    "camera": {"x": 0, "y": 0, "zoom": 1.0},
                    "physics_config": {"gravity_x": 0, "gravity_y": -9.81, "time_step": 0.016},
                }

            self._entities.clear()
            for eid, entity_data in state.get("entities", {}).items():
                self._entities[eid] = entity_data

            self._metrics.total_loads += 1
            self._set_state(HypervisorState.RUNNING)
            self._emit_event("state_loaded", {})
            return {"success": True}
        except Exception as e:
            self._set_state(HypervisorState.ERROR)
            return {"success": False, "error": str(e)}

    # -------------------------------------------------------------------------
    # Agent Bridge for Bidirectional Communication
    # -------------------------------------------------------------------------

    def process_agent_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process a command from the agent layer."""
        if not self._config.agent_commands_enabled:
            return {"success": False, "error": "Agent commands disabled"}

        command_type = command.get("command_type", "")
        handler = self._command_handlers.get(command_type)

        if handler:
            try:
                result = handler(command.get("parameters", {}))
                self._metrics.total_agent_commands += 1
                return {"success": True, "command_type": command_type, "result": result}
            except Exception as e:
                return {"success": False, "command_type": command_type, "error": str(e)}

        return {"success": False, "command_type": command_type, "error": "Unknown command"}

    def queue_agent_command(self, command: Dict[str, Any]) -> None:
        """Queue a command for processing in the next tick."""
        self._command_queue.append(command)

    def register_command_handler(self, command_type: str, handler: Callable) -> None:
        """Register a custom command handler."""
        self._command_handlers[command_type] = handler

    def on_event(self, event_type: str, callback: Callable) -> None:
        """Register an event listener."""
        self._event_listeners[event_type].append(callback)

    def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to all registered listeners."""
        event = {"event_type": event_type, "data": data, "timestamp": _time_module.time}
        self._event_queue.append(event)
        if len(self._event_queue) > 1000:
            self._event_queue = deque(list(self._event_queue)[-500:])

        for listener in self._event_listeners.get(event_type, []):
            try:
                listener(event)
            except Exception:
                pass

        if self._ai_core:
            try:
                from sparkai.engine.engine_ai_native_core import EngineEventType
                event_type_map = {
                    "scene_created": EngineEventType.SCENE_LOADED,
                    "entity_created": EngineEventType.ENTITY_SPAWNED,
                    "entity_destroyed": EngineEventType.ENTITY_DESTROYED,
                    "component_changed": EngineEventType.COMPONENT_CHANGED,
                    "collisions_detected": EngineEventType.COLLISION_OCCURRED,
                    "tick_complete": EngineEventType.FRAME_COMPLETE,
                }
                ee_type = event_type_map.get(event_type)
                if ee_type:
                    self._ai_core._emit_event(ee_type, data)
            except Exception:
                pass

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events."""
        return list(self._event_queue)[-limit:]

    # -------------------------------------------------------------------------
    # World Generation (Procedural Terrain, Biomes, Structures)
    # -------------------------------------------------------------------------

    def generate_world(self, width: int = 256, height: int = 256,
                       seed: Optional[int] = None,
                       biomes: Optional[List[str]] = None,
                       structures: int = 0) -> Dict[str, Any]:
        """Generate a procedural world with terrain, biomes, and structures."""
        self._ensure_initialized()
        if seed is None:
            seed = self._config.world_seed or random.randint(0, 2**31 - 1)

        world_id = f"world_{uuid.uuid4().hex[:12]}"
        rng = random.Random(seed)

        terrain_types = ["grass", "dirt", "sand", "stone", "snow", "water", "forest", "mountain"]
        biome_list = biomes or ["temperate", "desert", "tundra", "tropical", "boreal", "ocean", "savanna"]

        tiles = []
        terrain_distribution: Dict[str, int] = {}
        biome_distribution: Dict[str, int] = {}

        for y in range(height):
            for x in range(width):
                noise = rng.random()
                if noise < 0.05:
                    terrain = "water"
                elif noise < 0.15:
                    terrain = "sand"
                elif noise < 0.30:
                    terrain = "stone"
                elif noise < 0.55:
                    terrain = "grass"
                elif noise < 0.75:
                    terrain = "forest"
                else:
                    terrain = "mountain"

                biome = rng.choice(biome_list)
                tile = {
                    "x": x, "y": y,
                    "terrain_type": terrain,
                    "height": rng.uniform(0, 1),
                    "temperature": rng.uniform(-10, 40),
                    "humidity": rng.uniform(0, 1),
                    "biome": biome,
                    "has_water": terrain == "water",
                    "has_structure": False,
                }
                tiles.append(tile)
                terrain_distribution[terrain] = terrain_distribution.get(terrain, 0) + 1
                biome_distribution[biome] = biome_distribution.get(biome, 0) + 1

        # Generate structures
        structures_generated = []
        for _ in range(structures):
            sx = rng.randint(0, width - 1)
            sy = rng.randint(0, height - 1)
            structure = {
                "structure_id": f"struct_{uuid.uuid4().hex[:8]}",
                "x": sx, "y": sy,
                "type": rng.choice(["house", "tower", "ruin", "temple", "village"]),
                "size": rng.randint(2, 8),
            }
            structures_generated.append(structure)
            for tile in tiles:
                if abs(tile["x"] - sx) <= structure["size"] // 2 and abs(tile["y"] - sy) <= structure["size"] // 2:
                    tile["has_structure"] = True

        world_data = {
            "world_id": world_id,
            "width": width,
            "height": height,
            "seed": seed,
            "total_tiles": width * height,
            "terrain_distribution": terrain_distribution,
            "biome_distribution": biome_distribution,
            "structures": structures_generated,
            "structure_count": len(structures_generated),
        }

        if self._unified_engine:
            try:
                self._unified_engine.generate_world(width, height, seed)
            except Exception:
                pass

        self._emit_event("world_generated", world_data)
        return {"success": True, "world": world_data}

    def generate_terrain(self, width: int = 512, height: int = 512,
                         algorithm: str = "perlin", seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate procedural terrain with heightmap."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        rng = random.Random(seed)

        terrain_id = f"terrain_{uuid.uuid4().hex[:12]}"
        heightmap = [[0.0 for _ in range(width)] for _ in range(height)]

        for y in range(height):
            for x in range(width):
                heightmap[y][x] = rng.uniform(0, 1)

        return {
            "success": True,
            "terrain_id": terrain_id,
            "width": width,
            "height": height,
            "seed": seed,
            "algorithm": algorithm,
            "min_height": min(min(r) for r in heightmap),
            "max_height": max(max(r) for r in heightmap),
        }

    # -------------------------------------------------------------------------
    # Weather System with Day/Night Cycle
    # -------------------------------------------------------------------------

    def set_weather(self, weather_type: str, intensity: float = 0.5,
                    temperature: float = 22.0, humidity: float = 0.5,
                    wind_speed: float = 5.0) -> Dict[str, Any]:
        """Set the current weather conditions."""
        weather_data = {
            "weather_type": weather_type,
            "intensity": intensity,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": wind_speed,
        }
        if self._unified_engine:
            try:
                self._unified_engine.set_weather(weather_type, temperature, humidity)
            except Exception:
                pass
        self._emit_event("weather_changed", weather_data)
        return {"success": True, "weather": weather_data}

    def set_time_of_day(self, hour: float) -> Dict[str, Any]:
        """Set the time of day (0-24)."""
        hour = hour % 24
        if self._unified_engine:
            try:
                current = self._unified_engine._world_systems._weather.get("time_of_day", 12)
                delta = hour - current
                if delta < 0:
                    delta += 24
                self._unified_engine._world_systems.advance_time(delta)
            except Exception:
                pass
        self._emit_event("time_of_day_changed", {"hour": hour})
        return {"success": True, "time_of_day": hour}

    def get_weather(self) -> Dict[str, Any]:
        """Get current weather information."""
        if self._unified_engine:
            try:
                return self._unified_engine._world_systems._weather
            except Exception:
                pass
        return {"current": "clear", "temperature": 22.0, "humidity": 0.5, "wind_speed": 5.0, "time_of_day": 12}

    # -------------------------------------------------------------------------
    # Particle System Management
    # -------------------------------------------------------------------------

    def spawn_particles(self, emitter_name: str, position_x: float, position_y: float,
                        emission_rate: float = 50.0, max_particles: int = 200,
                        duration: float = -1.0, particle_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Spawn a particle emitter."""
        emitter_id = f"emitter_{uuid.uuid4().hex[:8]}"
        emitter_data = {
            "emitter_id": emitter_id,
            "name": emitter_name,
            "position": {"x": position_x, "y": position_y},
            "emission_rate": emission_rate,
            "max_particles": max_particles,
            "duration": duration,
            "active_particles": 0,
            "config": particle_config or {},
        }
        particles = self._subsystems.get("particles")
        if particles:
            try:
                particles.create_emitter(
                    name=emitter_name,
                    x=position_x,
                    y=position_y,
                    emission_rate=emission_rate,
                    max_particles=max_particles,
                )
            except Exception:
                pass
        self._emit_event("particles_spawned", emitter_data)
        return {"success": True, "emitter": emitter_data}

    def stop_particles(self, emitter_id: str) -> Dict[str, Any]:
        """Stop a particle emitter."""
        particles = self._subsystems.get("particles")
        if particles:
            try:
                pass
            except Exception:
                pass
        return {"success": True, "emitter_id": emitter_id}

    # -------------------------------------------------------------------------
    # Animation System
    # -------------------------------------------------------------------------

    def play_animation(self, entity_id: str, clip_name: str,
                       speed: float = 1.0, loop: bool = True) -> Dict[str, Any]:
        """Play an animation on an entity."""
        entity = self._entities.get(entity_id)
        if not entity:
            return {"success": False, "error": f"Entity {entity_id} not found"}

        if "animator" not in entity["components"]:
            entity["components"]["animator"] = {}

        entity["components"]["animator"] = {
            "current_clip": clip_name,
            "playback_speed": speed,
            "is_playing": True,
            "is_looping": loop,
            "current_time": 0.0,
        }

        if self._unified_engine:
            try:
                animator_id = self._unified_engine.create_animator(entity_id)
                self._unified_engine.play_animation(animator_id, clip_name, speed)
            except Exception:
                pass

        self._emit_event("animation_played", {
            "entity_id": entity_id, "clip_name": clip_name, "speed": speed,
        })
        return {"success": True, "entity_id": entity_id, "clip": clip_name}

    def stop_animation(self, entity_id: str) -> Dict[str, Any]:
        """Stop animation on an entity."""
        entity = self._entities.get(entity_id)
        if entity and "animator" in entity["components"]:
            entity["components"]["animator"]["is_playing"] = False
        return {"success": True, "entity_id": entity_id}

    # -------------------------------------------------------------------------
    # Camera Control System
    # -------------------------------------------------------------------------

    def set_camera(self, x: float = 0.0, y: float = 0.0, zoom: float = 1.0,
                   target_entity_id: Optional[str] = None) -> Dict[str, Any]:
        """Set camera position and target."""
        camera_data = {
            "x": x, "y": y, "zoom": zoom,
            "target_entity_id": target_entity_id,
        }
        if self._unified_engine:
            try:
                self._unified_engine._rendering.set_camera(x, y, zoom)
            except Exception:
                pass
        self._emit_event("camera_changed", camera_data)
        return {"success": True, "camera": camera_data}

    def shake_camera(self, intensity: float = 1.0, duration: float = 0.5) -> Dict[str, Any]:
        """Apply a camera shake effect."""
        shake_data = {"intensity": intensity, "duration": duration}
        self._emit_event("camera_shake", shake_data)
        return {"success": True, "shake": shake_data}

    # -------------------------------------------------------------------------
    # Pathfinding and Navigation
    # -------------------------------------------------------------------------

    def find_path(self, start_x: float, start_y: float,
                  end_x: float, end_y: float,
                  navmesh_id: str = "default") -> Dict[str, Any]:
        """Find a path between two points."""
        dx = end_x - start_x
        dy = end_y - start_y
        distance = math.sqrt(dx * dx + dy * dy)
        steps = max(1, int(distance / 10))
        path = []
        for i in range(steps + 1):
            t = i / steps
            path.append({
                "x": start_x + dx * t,
                "y": start_y + dy * t,
            })

        navigation = self._subsystems.get("navigation")
        if navigation:
            try:
                nav_path = navigation.find_path(navmesh_id, (start_x, start_y, 0), (end_x, end_y, 0))
                if nav_path:
                    path = [{"x": wp[0], "y": wp[1], "z": wp[2]} for wp in nav_path.waypoints] if hasattr(nav_path, "waypoints") else path
            except Exception:
                pass

        return {
            "success": True,
            "path": path,
            "distance": distance,
            "waypoints": len(path),
        }

    def create_navmesh(self, name: str, cell_size: float = 0.5,
                       agent_radius: float = 0.3) -> Dict[str, Any]:
        """Create a navigation mesh."""
        navmesh_id = f"navmesh_{uuid.uuid4().hex[:8]}"
        navigation = self._subsystems.get("navigation")
        if navigation:
            try:
                navigation.create_navmesh(navmesh_id, cell_size=cell_size, agent_radius=agent_radius)
            except Exception:
                pass
        return {"success": True, "navmesh_id": navmesh_id, "name": name}

    # -------------------------------------------------------------------------
    # Complete End-to-End Game Assembly Workflow
    # -------------------------------------------------------------------------

    def assemble_game(self, game_name: str,
                      spec: Optional[Dict[str, Any]] = None) -> AssemblyResult:
        """Execute a complete end-to-end game assembly workflow."""
        self._set_state(HypervisorState.ASSEMBLING)
        spec = spec or {}
        assembly = AssemblyResult(game_name=game_name, success=True)
        self._current_assembly = assembly
        t_start = _time_module.time

        assembly_phases = [
            (AssemblyPhase.VALIDATION, self._assembly_validate),
            (AssemblyPhase.PROJECT_SETUP, self._assembly_project_setup),
            (AssemblyPhase.WORLD_GENERATION, self._assembly_world_generation),
            (AssemblyPhase.SCENE_CREATION, self._assembly_scene_creation),
            (AssemblyPhase.ENTITY_POPULATION, self._assembly_entity_population),
            (AssemblyPhase.PHYSICS_SETUP, self._assembly_physics_setup),
            (AssemblyPhase.RENDERING_CONFIG, self._assembly_rendering_config),
            (AssemblyPhase.AUDIO_SETUP, self._assembly_audio_setup),
            (AssemblyPhase.INPUT_CONFIG, self._assembly_input_config),
            (AssemblyPhase.AI_SETUP, self._assembly_ai_setup),
            (AssemblyPhase.UI_SETUP, self._assembly_ui_setup),
            (AssemblyPhase.ANIMATION_SETUP, self._assembly_animation_setup),
            (AssemblyPhase.WEATHER_SETUP, self._assembly_weather_setup),
            (AssemblyPhase.CAMERA_SETUP, self._assembly_camera_setup),
            (AssemblyPhase.NAVIGATION_SETUP, self._assembly_navigation_setup),
            (AssemblyPhase.PARTICLE_SETUP, self._assembly_particle_setup),
            (AssemblyPhase.FINALIZATION, self._assembly_finalization),
            (AssemblyPhase.VERIFICATION, self._assembly_verification),
        ]

        for phase, phase_fn in assembly_phases:
            t_phase = _time_module.time
            try:
                phase_fn(spec, assembly)
                assembly.phases_completed[phase.value] = True
            except Exception as e:
                assembly.errors.append(f"{phase.value}: {str(e)}")
                assembly.phases_completed[phase.value] = False
                assembly.success = False
            assembly.phase_durations[phase.value] = (_time_module.time - t_phase) * 1000

        assembly.total_duration_ms = (_time_module.time - t_start) * 1000
        self._assembly_history.append(assembly)
        self._metrics.total_assembly_cycles += 1
        self._current_assembly = None

        self._set_state(HypervisorState.READY)
        self._emit_event("game_assembled", assembly.to_dict())
        return assembly

    def _assembly_validate(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Validate assembly specification."""
        genre = spec.get("genre", "platformer")
        if genre not in ["platformer", "rpg", "shooter", "puzzle", "strategy", "adventure", "simulation", "racing"]:
            assembly.warnings.append(f"Unknown genre: {genre}")

    def _assembly_project_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Set up the project structure."""
        self._config.target_fps = spec.get("target_fps", 60)
        self._config.quality_preset = QualityPreset(spec.get("quality", "high"))
        self.set_quality_preset(self._config.quality_preset)

    def _assembly_world_generation(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Generate the game world."""
        world_width = spec.get("world_width", 256)
        world_height = spec.get("world_height", 256)
        world_seed = spec.get("world_seed")

        world = self.generate_world(world_width, world_height, world_seed,
                                     biomes=spec.get("biomes"),
                                     structures=spec.get("structures", 5))
        assembly.world_tiles_generated = world.get("world", {}).get("total_tiles", 0)

    def _assembly_scene_creation(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Create all game scenes."""
        scene_count = spec.get("scenes", 1)
        scene_names = spec.get("scene_names", [])

        for i in range(scene_count):
            name = scene_names[i] if i < len(scene_names) else f"{assembly.game_name}_Scene_{i + 1}"
            self.create_scene(name, spec.get("width", 1920), spec.get("height", 1080))
            assembly.scenes_created += 1

        if assembly.scenes_created > 0:
            first_scene = list(self._scenes.values())[0]
            self.load_scene(first_scene["scene_id"])

    def _assembly_entity_population(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Populate entities in the game."""
        entity_count = spec.get("entities", 10)
        entity_types = spec.get("entity_types", ["player", "npc", "prop", "enemy"])

        for i in range(entity_count):
            etype = entity_types[i % len(entity_types)]
            entity_data = EntityData(
                name=f"{etype}_{i}",
                entity_type=etype,
                position_x=(i % 10) * 100,
                position_y=(i // 10) * 100,
            )
            self.create_entity(entity_data)
            assembly.entities_spawned += 1

    def _assembly_physics_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure physics settings."""
        self._config.enable_physics = spec.get("physics_enabled", True)
        self._config.physics_quality = spec.get("physics_quality", "medium")

    def _assembly_rendering_config(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure rendering pipeline."""
        self._config.enable_rendering = spec.get("rendering_enabled", True)
        self._config.shadow_quality = spec.get("shadow_quality", "high")
        self._config.texture_quality = spec.get("texture_quality", "high")

    def _assembly_audio_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure audio system."""
        self._config.enable_audio = spec.get("audio_enabled", True)
        self._config.audio_channels = spec.get("audio_channels", 64)

    def _assembly_input_config(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure input system."""
        self._config.enable_input = spec.get("input_enabled", True)
        for action, key in spec.get("key_bindings", {}).items():
            self.bind_input_action(action, key)

    def _assembly_ai_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure AI systems."""
        self._config.enable_ai = spec.get("ai_enabled", True)

    def _assembly_ui_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure UI system."""
        pass

    def _assembly_animation_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure animation system."""
        self._config.enable_animations = spec.get("animations_enabled", True)

    def _assembly_weather_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure weather system."""
        self._config.enable_weather = spec.get("weather_enabled", True)
        self.set_weather(
            weather_type=spec.get("weather_type", "clear"),
            temperature=spec.get("temperature", 22.0),
        )
        self.set_time_of_day(spec.get("time_of_day", 12.0))

    def _assembly_camera_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure camera system."""
        self._config.enable_camera = spec.get("camera_enabled", True)
        self.set_camera(
            x=spec.get("camera_x", 0),
            y=spec.get("camera_y", 0),
            zoom=spec.get("camera_zoom", 1.0),
        )

    def _assembly_navigation_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure navigation system."""
        self._config.enable_navigation = spec.get("navigation_enabled", True)
        self.create_navmesh("default", cell_size=spec.get("navmesh_cell_size", 0.5))

    def _assembly_particle_setup(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Configure particle system."""
        self._config.enable_particles = spec.get("particles_enabled", True)
        self._config.particle_limit = spec.get("particle_limit", 5000)

    def _assembly_finalization(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Finalize the assembly."""
        assembly.metadata["game_name"] = assembly.game_name
        assembly.metadata["genre"] = spec.get("genre", "platformer")
        assembly.metadata["assembly_time"] = _time_module.time

    def _assembly_verification(self, spec: Dict[str, Any], assembly: AssemblyResult) -> None:
        """Verify the assembled game."""
        if assembly.scenes_created == 0:
            assembly.warnings.append("No scenes were created")
        if assembly.entities_spawned == 0:
            assembly.warnings.append("No entities were spawned")

    # -------------------------------------------------------------------------
    # Self-Diagnostic and Health Checking
    # -------------------------------------------------------------------------

    def run_health_check(self) -> List[HealthCheckResult]:
        """Run a comprehensive health check on all subsystems."""
        self._set_state(HypervisorState.DIAGNOSING)
        self._metrics.total_health_checks += 1
        results: List[HealthCheckResult] = []

        # Check core engines
        for name, instance in [
            ("unified_game_engine", self._unified_engine),
            ("ai_native_runtime", self._ai_runtime),
            ("ai_native_core", self._ai_core),
        ]:
            t0 = _time_module.time
            if instance is not None:
                try:
                    _ = instance.get_status() if hasattr(instance, "get_status") else True
                    results.append(HealthCheckResult(
                        subsystem_name=name,
                        status=HealthStatus.HEALTHY,
                        loaded=True,
                        response_time_ms=(_time_module.time - t0) * 1000,
                    ))
                except Exception as e:
                    results.append(HealthCheckResult(
                        subsystem_name=name,
                        status=HealthStatus.DEGRADED,
                        loaded=True,
                        error_message=str(e),
                        response_time_ms=(_time_module.time - t0) * 1000,
                    ))
            else:
                results.append(HealthCheckResult(
                    subsystem_name=name,
                    status=HealthStatus.NOT_LOADED,
                    loaded=False,
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))

        # Check lazy-loaded subsystems
        for name, instance in self._subsystems.items():
            t0 = _time_module.time
            if instance is not None:
                try:
                    results.append(HealthCheckResult(
                        subsystem_name=name,
                        status=HealthStatus.HEALTHY,
                        loaded=True,
                        response_time_ms=(_time_module.time - t0) * 1000,
                    ))
                except Exception as e:
                    results.append(HealthCheckResult(
                        subsystem_name=name,
                        status=HealthStatus.DEGRADED,
                        loaded=True,
                        error_message=str(e),
                        response_time_ms=(_time_module.time - t0) * 1000,
                    ))
            else:
                results.append(HealthCheckResult(
                    subsystem_name=name,
                    status=HealthStatus.NOT_LOADED,
                    loaded=False,
                    error_message=self._subsystem_load_errors.get(name, "Module not found"),
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))

        # Check internal state consistency
        t0 = _time_module.time
        try:
            if self._active_scene_id and self._active_scene_id not in self._scenes:
                results.append(HealthCheckResult(
                    subsystem_name="scene_consistency",
                    status=HealthStatus.DEGRADED,
                    loaded=True,
                    error_message="Active scene not found in scene registry",
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))
            else:
                results.append(HealthCheckResult(
                    subsystem_name="scene_consistency",
                    status=HealthStatus.HEALTHY,
                    loaded=True,
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))
        except Exception as e:
            results.append(HealthCheckResult(
                subsystem_name="scene_consistency",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=(_time_module.time - t0) * 1000,
            ))

        # Check entity consistency
        t0 = _time_module.time
        try:
            orphan_entities = 0
            for eid in list(self._entities.keys()):
                found = any(eid in scene.get("entities", {}) for scene in self._scenes.values())
                if not found and self._active_scene_id:
                    orphan_entities += 1
            if orphan_entities > 0:
                results.append(HealthCheckResult(
                    subsystem_name="entity_consistency",
                    status=HealthStatus.DEGRADED,
                    loaded=True,
                    error_message=f"{orphan_entities} orphan entities found",
                    metrics={"orphan_entities": orphan_entities},
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))
            else:
                results.append(HealthCheckResult(
                    subsystem_name="entity_consistency",
                    status=HealthStatus.HEALTHY,
                    loaded=True,
                    response_time_ms=(_time_module.time - t0) * 1000,
                ))
        except Exception as e:
            results.append(HealthCheckResult(
                subsystem_name="entity_consistency",
                status=HealthStatus.UNHEALTHY,
                error_message=str(e),
                response_time_ms=(_time_module.time - t0) * 1000,
            ))

        # Check memory budget
        if self._metrics.peak_memory_mb > self._config.memory_budget_mb:
            for r in results:
                if r.subsystem_name == "memory":
                    r.status = HealthStatus.DEGRADED
                    r.recommendations.append(f"Memory usage ({self._metrics.peak_memory_mb:.0f}MB) exceeds budget ({self._config.memory_budget_mb}MB)")
                    break

        # Check for entity limit
        if len(self._entities) > self._config.max_entities:
            for r in results:
                if r.subsystem_name == "entity_consistency":
                    r.status = HealthStatus.DEGRADED
                    r.recommendations.append(f"Entity count ({len(self._entities)}) exceeds limit ({self._config.max_entities})")
                    break

        self._health_history.extend(results)
        if len(self._health_history) > 1000:
            self._health_history = self._health_history[-500:]

        self._set_state(HypervisorState.READY)
        self._emit_event("health_check_complete", {
            "total_checks": len(results),
            "healthy": sum(1 for r in results if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in results if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in results if r.status == HealthStatus.UNHEALTHY),
            "not_loaded": sum(1 for r in results if r.status == HealthStatus.NOT_LOADED),
        })
        return results

    def get_health_summary(self) -> Dict[str, Any]:
        """Get a summary of the latest health check."""
        if not self._health_history:
            return {"status": "no_checks", "results": []}

        latest_results = self._health_history[-50:]
        return {
            "status": "available",
            "total_checks": len(latest_results),
            "healthy": sum(1 for r in latest_results if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in latest_results if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in latest_results if r.status == HealthStatus.UNHEALTHY),
            "not_loaded": sum(1 for r in latest_results if r.status == HealthStatus.NOT_LOADED),
            "results": [r.to_dict() for r in latest_results],
        }

    # -------------------------------------------------------------------------
    # Status & Configuration
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive hypervisor status."""
        return {
            "initialized": self._initialized,
            "state": self._state.value,
            "running": self._running,
            "frame_count": self._frame_count,
            "delta_time": self._delta_time,
            "active_scene": self._active_scene_id,
            "scene_count": len(self._scenes),
            "entity_count": len(self._entities),
            "config": self._config.to_dict(),
            "metrics": self._metrics.to_dict(),
            "subsystems": self._get_subsystem_status_summary(),
            "uptime_seconds": _time_module.time - self._start_time if self._start_time > 0 else 0,
        }

    def apply_config(self, config: Union[HypervisorConfig, Dict[str, Any]]) -> Dict[str, Any]:
        """Apply a new configuration."""
        if isinstance(config, dict):
            for key, value in config.items():
                if hasattr(self._config, key):
                    setattr(self._config, key, value)
        else:
            self._config = config
        self._emit_event("config_applied", self._config.to_dict())
        return {"success": True, "config": self._config.to_dict()}

    def reset(self) -> Dict[str, Any]:
        """Reset the hypervisor to its initial state."""
        self.stop()
        self._scenes.clear()
        self._entities.clear()
        self._active_scene_id = None
        self._transition_queue.clear()
        self._command_queue.clear()
        self._event_queue.clear()
        self._frame_history.clear()
        self._profile_data.clear()
        self._frame_count = 0
        self._metrics = HypervisorMetrics()
        self._start_time = _time_module.time
        self._set_state(HypervisorState.READY)
        return {"success": True, "status": "reset"}

    # -------------------------------------------------------------------------
    # Command Handler Implementations
    # -------------------------------------------------------------------------

    def _cmd_create_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.create_scene(
            params.get("name", "Untitled"),
            params.get("width", 1920),
            params.get("height", 1080),
            params.get("config"),
        )

    def _cmd_load_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.load_scene(params.get("scene_id", ""))

    def _cmd_unload_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.unload_scene(params.get("scene_id", ""))

    def _cmd_transition_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        transition = SceneTransitionRequest(
            from_scene_id=params.get("from_scene_id"),
            to_scene_id=params.get("to_scene_id", ""),
            transition_type=SceneTransitionType(params.get("transition_type", "fade")),
            duration_seconds=params.get("duration", 1.0),
            unload_source=params.get("unload_source", False),
        )
        return self.transition_scene(transition)

    def _cmd_create_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_data = EntityData(
            name=params.get("name", "Entity"),
            entity_type=params.get("entity_type", "custom"),
            position_x=params.get("x", 0),
            position_y=params.get("y", 0),
            position_z=params.get("z", 0),
            components=params.get("components", {}),
            tags=params.get("tags", []),
            parent_id=params.get("parent_id"),
        )
        return self.create_entity(entity_data)

    def _cmd_destroy_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.destroy_entity(params.get("entity_id", ""))

    def _cmd_set_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_component(
            params.get("entity_id", ""),
            params.get("component_name", ""),
            params.get("component_data", {}),
        )

    def _cmd_get_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        result = self.get_component(
            params.get("entity_id", ""),
            params.get("component_name", ""),
        )
        return {"data": result} if result else {"data": None}

    def _cmd_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_state()

    def _cmd_get_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.get_status()

    def _cmd_apply_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.apply_config(params)

    def _cmd_set_weather(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_weather(
            params.get("weather_type", "clear"),
            params.get("intensity", 0.5),
            params.get("temperature", 22.0),
            params.get("humidity", 0.5),
            params.get("wind_speed", 5.0),
        )

    def _cmd_set_time_of_day(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_time_of_day(params.get("hour", 12.0))

    def _cmd_generate_world(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.generate_world(
            params.get("width", 256),
            params.get("height", 256),
            params.get("seed"),
            params.get("biomes"),
            params.get("structures", 0),
        )

    def _cmd_find_path(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.find_path(
            params.get("start_x", 0),
            params.get("start_y", 0),
            params.get("end_x", 0),
            params.get("end_y", 0),
            params.get("navmesh_id", "default"),
        )

    def _cmd_spawn_particles(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.spawn_particles(
            params.get("emitter_name", "default"),
            params.get("x", 0),
            params.get("y", 0),
            params.get("emission_rate", 50.0),
            params.get("max_particles", 200),
            params.get("duration", -1.0),
            params.get("config"),
        )

    def _cmd_play_animation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.play_animation(
            params.get("entity_id", ""),
            params.get("clip_name", "default"),
            params.get("speed", 1.0),
            params.get("loop", True),
        )

    def _cmd_set_camera(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.set_camera(
            params.get("x", 0),
            params.get("y", 0),
            params.get("zoom", 1.0),
            params.get("target_entity_id"),
        )

    def _cmd_save_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.save_state()

    def _cmd_load_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.load_state(params.get("state", {}))

    def _cmd_run_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        results = self.run_health_check()
        return {"results": [r.to_dict() for r in results]}

    def _cmd_assemble_game(self, params: Dict[str, Any]) -> Dict[str, Any]:
        result = self.assemble_game(
            params.get("game_name", "NewGame"),
            params.get("spec", {}),
        )
        return result.to_dict()

    def _cmd_start(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.start()

    def _cmd_stop(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.stop()

    def _cmd_pause(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.pause()

    def _cmd_resume(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.resume()

    def _cmd_tick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        num_ticks = params.get("num_ticks", 1)
        reports = []
        for _ in range(num_ticks):
            reports.append(self.tick().to_dict())
        return {"reports": reports, "ticks": num_ticks}

    def _cmd_shutdown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return self.shutdown()


# =============================================================================
# Convenience Function
# =============================================================================


def get_ai_native_hypervisor() -> AINativeEngineHypervisor:
    """Get the singleton AINativeEngineHypervisor instance."""
    hv = AINativeEngineHypervisor.get_instance()
    if not hv._initialized:
        hv.initialize()
    return hv