"""
SparkLabs Engine - Engine Unification Core

The centralized orchestration layer that unifies all SparkLabs game engine
subsystems into a single cohesive runtime. It synchronizes rendering,
physics, scene management, audio, ECS, animation, world systems, input/UI,
performance diagnostics, and resource/asset pipelines through a unified
control plane.

Architecture:
  EngineUnificationCore (Singleton)
    |-- RenderingOrchestrator    (render pipeline, passes, post-processing, GPU, shadows, lighting, skybox, decals, sprites, trails, parallax, particles, materials, shaders)
    |-- PhysicsOrchestrator      (dynamics, world-2d, materials, collision, ragdoll, constraints, vehicles, water simulation)
    |-- SceneOrchestrator        (scene manager, tree, stack, transitions, streaming, progressive loading, prefab composer)
    |-- AudioOrchestrator        (audio system, synthesis, spatial, layering, interactive, procedural, dynamic music)
    |-- ECSOrchestrator          (ECS, component assembler, entity blueprints, custom object types, game objects, node tree, node path)
    |-- AnimationOrchestrator    (animation system, curves, trees, controllers, skeleton deformer, camera shake, camera controller, tween system)
    |-- WorldOrchestrator        (terrain, biome generation, procedural world, procedural dungeon, tilemap, runtime tilemaps, tilesets, tile brushes, fog of war, weather, day/night cycle)
    |-- InputUIOrchestrator      (input manager, mapping, events, abstraction, input maps, gesture recognizers, UI system, UI layout)
    |-- PerformanceOrchestrator  (profiler, performance overlay, frame timer, debug draw, console system, telemetry)
    |-- ResourceOrchestrator     (resource manager, loader, asset pipeline, bundler, streamer, texture atlas, sprite sheet, font system, localization hub, serialization)
"""

from __future__ import annotations

import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sparkai.engine.engine_deterministic_core import EngineDeterministicCore, get_deterministic_core
from sparkai.engine.engine_gpu_compute import EngineGPUCompute, get_gpu_compute
from sparkai.engine.engine_skeletal_blending import EngineSkeletalBlending, get_skeletal_blending
from sparkai.engine.engine_volumetric_rendering import EngineVolumetricRendering, get_volumetric_rendering
from sparkai.engine.engine_crowd_dynamics import EngineCrowdDynamics, get_crowd_dynamics
from sparkai.engine.engine_fluid_dynamics import EngineFluidDynamics, get_fluid_dynamics


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class OrchestratorState(Enum):
    """Overall state for each orchestrator subsystem."""
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    DEGRADED = "degraded"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class EngineLifecycle(Enum):
    """Top-level engine lifecycle states."""
    COLD = "cold"
    BOOTING = "booting"
    RUNNING = "running"
    SUSPENDED = "suspended"
    SHUTTING_DOWN = "shutting_down"
    TERMINATED = "terminated"


class SystemCategory(Enum):
    """Categorization of orchestrated systems."""
    RENDERING = "rendering"
    PHYSICS = "physics"
    SCENE_MANAGEMENT = "scene_management"
    AUDIO = "audio"
    ECS = "ecs"
    ANIMATION = "animation"
    WORLD_SYSTEMS = "world_systems"
    INPUT_UI = "input_ui"
    PERFORMANCE_DIAGNOSTICS = "performance_diagnostics"
    RESOURCE_ASSETS = "resource_assets"
    VOLUMETRIC_RENDERING = "volumetric_rendering"
    CROWD_DYNAMICS = "crowd_dynamics"
    FLUID_DYNAMICS = "fluid_dynamics"


class InitializationMode(Enum):
    """Selective initialization strategies."""
    FULL = "full"
    HEADLESS = "headless"
    MINIMAL = "minimal"
    SERVER = "server"
    EDITOR = "editor"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Orchestrator Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class OrchestratorDescriptor:
    """Runtime descriptor for a single orchestrator subsystem."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: SystemCategory = SystemCategory.RENDERING
    name: str = ""
    state: OrchestratorState = OrchestratorState.UNINITIALIZED
    managed_subsystems: List[str] = field(default_factory=list)
    init_time_ms: float = 0.0
    last_tick_ms: float = 0.0
    tick_count: int = 0
    error_count: int = 0
    last_error: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "name": self.name,
            "state": self.state.value,
            "managed_subsystems": list(self.managed_subsystems),
            "init_time_ms": round(self.init_time_ms, 4),
            "last_tick_ms": round(self.last_tick_ms, 4),
            "tick_count": self.tick_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "enabled": self.enabled,
        }


@dataclass
class TickReport:
    """Unified delta-time tick report from all orchestrators."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    delta_time: float = 0.0
    timestamp: float = field(default_factory=_time_module.time)
    orchestrator_timings: Dict[str, float] = field(default_factory=dict)
    total_tick_ms: float = 0.0
    active_subsystems: int = 0
    degraded_subsystems: int = 0
    health_score: float = 100.0
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "delta_time": round(self.delta_time, 6),
            "timestamp": self.timestamp,
            "orchestrator_timings": {k: round(v, 4) for k, v in self.orchestrator_timings.items()},
            "total_tick_ms": round(self.total_tick_ms, 4),
            "active_subsystems": self.active_subsystems,
            "degraded_subsystems": self.degraded_subsystems,
            "health_score": round(self.health_score, 2),
            "warnings": list(self.warnings),
        }


@dataclass
class FrameReport:
    """Unified render-frame report from all rendering orchestrators."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_id: int = 0
    render_time_ms: float = 0.0
    frame_time_ms: float = 0.0
    fps: float = 0.0
    draw_calls: int = 0
    triangles: int = 0
    batches: int = 0
    visible_objects: int = 0
    post_process_effects: int = 0
    resolution_scale: float = 1.0
    culled_objects: int = 0
    shadow_casters: int = 0
    active_particle_systems: int = 0
    material_switches: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_id": self.frame_id,
            "render_time_ms": round(self.render_time_ms, 4),
            "frame_time_ms": round(self.frame_time_ms, 4),
            "fps": round(self.fps, 1),
            "draw_calls": self.draw_calls,
            "triangles": self.triangles,
            "batches": self.batches,
            "visible_objects": self.visible_objects,
            "post_process_effects": self.post_process_effects,
            "resolution_scale": self.resolution_scale,
            "culled_objects": self.culled_objects,
            "shadow_casters": self.shadow_casters,
            "active_particle_systems": self.active_particle_systems,
            "material_switches": self.material_switches,
        }


@dataclass
class EngineDiagnostics:
    """Comprehensive engine-level diagnostic data."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    lifecycle: EngineLifecycle = EngineLifecycle.COLD
    uptime_seconds: float = 0.0
    total_frames_rendered: int = 0
    total_ticks_processed: int = 0
    orchestrator_states: Dict[str, str] = field(default_factory=dict)
    memory_estimate_mb: float = 0.0
    subsystem_count: int = 0
    active_subsystems: int = 0
    subsystems_in_error: int = 0
    avg_fps: float = 0.0
    avg_frame_time_ms: float = 0.0
    avg_tick_time_ms: float = 0.0
    total_errors: int = 0
    collected_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "lifecycle": self.lifecycle.value,
            "uptime_seconds": round(self.uptime_seconds, 2),
            "total_frames_rendered": self.total_frames_rendered,
            "total_ticks_processed": self.total_ticks_processed,
            "orchestrator_states": dict(self.orchestrator_states),
            "memory_estimate_mb": round(self.memory_estimate_mb, 2),
            "subsystem_count": self.subsystem_count,
            "active_subsystems": self.active_subsystems,
            "subsystems_in_error": self.subsystems_in_error,
            "avg_fps": round(self.avg_fps, 1),
            "avg_frame_time_ms": round(self.avg_frame_time_ms, 4),
            "avg_tick_time_ms": round(self.avg_tick_time_ms, 4),
            "total_errors": self.total_errors,
            "collected_at": self.collected_at,
        }


# ---------------------------------------------------------------------------
# Engine Unification Core (Singleton)
# ---------------------------------------------------------------------------


class EngineUnificationCore:
    """
    Centralized orchestration layer that unifies all SparkLabs game engine
    subsystems into a cohesive runtime.

    Coordinates 10 orchestrator domains: Rendering, Physics, Scene Management,
    Audio, ECS, Animation, World Systems, Input & UI, Performance & Diagnostics,
    and Resource & Asset pipelines.

    Features:
      - Selective subsystem initialization
      - Unified game-loop tick with per-orchestrator timing
      - Coordinated render pipeline execution
      - Comprehensive engine health reporting
      - Graceful shutdown with dependency-aware ordering
    """

    _instance: Optional["EngineUnificationCore"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineUnificationCore":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # --- Engine-wide state ---
        self._lifecycle: EngineLifecycle = EngineLifecycle.COLD
        self._start_time: float = 0.0
        self._frame_count: int = 0
        self._tick_count: int = 0
        self._init_mode: InitializationMode = InitializationMode.FULL

        # --- Orchestrator registry ---
        self._orchestrators: Dict[str, OrchestratorDescriptor] = {}
        self._orchestrator_order: List[str] = []
        self._init_order: List[str] = []
        self._tick_order: List[str] = []
        self._shutdown_order: List[str] = []

        # --- Performance tracking ---
        self._tick_reports: List[TickReport] = []
        self._frame_reports: List[FrameReport] = []
        self._render_target_fps: int = 60
        self._tick_budget_ms: float = 16.667 / 2.0  # Half-frame for logic

        # --- Subsystem definitions ---
        self._define_orchestrators()

        # --- Subsystem instances ---
        self._deterministic_core: Optional[EngineDeterministicCore] = None
        self._gpu_compute: Optional[EngineGPUCompute] = None
        self._skeletal_blending: Optional[EngineSkeletalBlending] = None
        self._volumetric_rendering: Optional[EngineVolumetricRendering] = None
        self._crowd_dynamics: Optional[EngineCrowdDynamics] = None
        self._fluid_dynamics: Optional[EngineFluidDynamics] = None

        # --- Runtime statistics ---
        self._total_errors: int = 0
        self._avg_fps_accumulator: float = 0.0
        self._fps_sample_count: int = 0

    # ------------------------------------------------------------------
    # Orchestrator Definitions
    # ------------------------------------------------------------------

    def _define_orchestrators(self):
        """Register all 10 orchestrator subsystems with their managed subsystems."""

        rendering_subsystems = [
            "engine_render_pipeline", "engine_render_layer", "engine_render_pass",
            "engine_post_processing", "engine_gpu_batch_rendering",
            "engine_shadow_casting", "engine_lighting_2d", "engine_skybox_renderer",
            "engine_decal_system", "engine_sprite_animator", "engine_trail_renderer",
            "engine_parallax_background", "engine_particle_system",
            "engine_material_graph", "shader_system",
        ]

        physics_subsystems = [
            "engine_physics_dynamics", "engine_physics_world_2d",
            "engine_physics_material", "collision_system", "ragdoll_physics",
            "physics_constraints", "vehicle_system", "engine_water_simulation",
        ]

        scene_subsystems = [
            "engine_scene_manager", "scene_tree", "engine_scene_stack",
            "engine_scene_transition", "engine_scene_streamer",
            "engine_world_streamer", "engine_progressive_loading",
            "engine_prefab_composer",
        ]

        audio_subsystems = [
            "engine_audio_system", "engine_audio_synthesis",
            "engine_audio_spatial", "engine_audio_layering",
            "engine_interactive_audio", "engine_procedural_audio", "dynamic_music",
        ]

        ecs_subsystems = [
            "engine_entity_component_system", "engine_component_assembler",
            "engine_entity_blueprint", "engine_custom_object_types",
            "game_object", "engine_node_tree", "node_path_system",
        ]

        animation_subsystems = [
            "engine_animation_system", "engine_animation_curve",
            "engine_animation_tree", "animation_controller",
            "engine_skeleton_deformer", "camera_shake",
            "engine_camera_controller", "tween_system",
        ]

        world_subsystems = [
            "terrain_system", "engine_biome_generation",
            "engine_procedural_world", "engine_procedural_dungeon",
            "tilemap_system", "engine_tilemap_runtime", "tileset_system",
            "engine_tile_brush", "fog_of_war", "engine_weather_system",
            "day_night_cycle",
        ]

        input_ui_subsystems = [
            "input_manager", "input_mapping", "input_event_system",
            "engine_input_abstraction", "engine_input_map",
            "engine_gesture_recognizer", "ui_system", "ui_layout_system",
        ]

        performance_subsystems = [
            "profiler", "performance_overlay", "engine_frame_timer",
            "debug_draw_system", "console_system", "game_telemetry",
        ]

        resource_subsystems = [
            "resource_manager", "resource_loader", "asset_pipeline",
            "engine_asset_bundler", "engine_asset_streamer",
            "engine_texture_atlas", "sprite_sheet", "font_system",
            "engine_localization_hub", "serialization",
        ]

        categories: List[tuple[SystemCategory, str, List[str]]] = [
            (SystemCategory.RENDERING, "Rendering Orchestrator", rendering_subsystems),
            (SystemCategory.PHYSICS, "Physics Orchestrator", physics_subsystems),
            (SystemCategory.SCENE_MANAGEMENT, "Scene Management Orchestrator", scene_subsystems),
            (SystemCategory.AUDIO, "Audio Orchestrator", audio_subsystems),
            (SystemCategory.ECS, "ECS Orchestrator", ecs_subsystems),
            (SystemCategory.ANIMATION, "Animation Orchestrator", animation_subsystems),
            (SystemCategory.WORLD_SYSTEMS, "World Systems Orchestrator", world_subsystems),
            (SystemCategory.INPUT_UI, "Input & UI Orchestrator", input_ui_subsystems),
            (SystemCategory.PERFORMANCE_DIAGNOSTICS, "Performance & Diagnostics Orchestrator", performance_subsystems),
            (SystemCategory.RESOURCE_ASSETS, "Resource & Asset Orchestrator", resource_subsystems),
        ]

        for cat, name, subsystems in categories:
            descriptor = OrchestratorDescriptor(
                category=cat,
                name=name,
                managed_subsystems=list(subsystems),
            )
            self._orchestrators[descriptor.id] = descriptor
            self._orchestrator_order.append(descriptor.id)

        # Define init ordering: core infrastructure first, then gameplay, then presentation
        self._init_order = sorted(
            self._orchestrator_order,
            key=lambda oid: self._orchestrators[oid].category.value,
        )

        # Define tick ordering: input -> physics -> world -> ecs -> animation -> scene -> audio -> rendering -> perf -> resources
        self._tick_order = [
            self._find_orchestrator_by_category(SystemCategory.INPUT_UI),
            self._find_orchestrator_by_category(SystemCategory.PHYSICS),
            self._find_orchestrator_by_category(SystemCategory.WORLD_SYSTEMS),
            self._find_orchestrator_by_category(SystemCategory.ECS),
            self._find_orchestrator_by_category(SystemCategory.ANIMATION),
            self._find_orchestrator_by_category(SystemCategory.SCENE_MANAGEMENT),
            self._find_orchestrator_by_category(SystemCategory.AUDIO),
            self._find_orchestrator_by_category(SystemCategory.RENDERING),
            self._find_orchestrator_by_category(SystemCategory.PERFORMANCE_DIAGNOSTICS),
            self._find_orchestrator_by_category(SystemCategory.RESOURCE_ASSETS),
        ]

        # Define shutdown ordering: reverse of tick (render off first, input last)
        self._shutdown_order = list(reversed(self._tick_order))

    def _find_orchestrator_by_category(self, category: SystemCategory) -> str:
        """Internal: locate orchestrator ID by its SystemCategory."""
        for oid, desc in self._orchestrators.items():
            if desc.category == category:
                return oid
        return ""

    # ------------------------------------------------------------------
    # Status & Reporting
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """
        Return the current state of all 10 orchestrator subsystems.

        Returns:
            Dict keyed by category with state, subsystem count, error count,
            and tick performance per orchestrator.
        """
        result: Dict[str, Any] = {
            "lifecycle": self._lifecycle.value,
            "uptime_seconds": round(_time_module.time() - self._start_time, 2) if self._start_time > 0 else 0.0,
            "initialization_mode": self._init_mode.value,
            "orchestrators": {},
            "core_subsystems": {
                "deterministic_core": self._deterministic_core is not None,
                "gpu_compute": self._gpu_compute is not None,
                "skeletal_blending": self._skeletal_blending is not None,
                "volumetric_rendering": self._volumetric_rendering is not None,
                "crowd_dynamics": self._crowd_dynamics is not None,
                "fluid_dynamics": self._fluid_dynamics is not None,
            },
        }

        for oid in self._orchestrator_order:
            desc = self._orchestrators[oid]
            result["orchestrators"][desc.category.value] = {
                "state": desc.state.value,
                "name": desc.name,
                "subsystems_total": len(desc.managed_subsystems),
                "subsystems_active": len(desc.managed_subsystems) if desc.state == OrchestratorState.ACTIVE else 0,
                "error_count": desc.error_count,
                "last_error": desc.last_error,
                "last_tick_ms": round(desc.last_tick_ms, 4),
                "tick_count": desc.tick_count,
                "enabled": desc.enabled,
            }

        return result

    def get_engine_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive engine status report including diagnostics,
        orchestrator states, frame performance, and health metrics.

        Returns:
            Dict with full engine diagnostics, recent frame/tick data, and
            per-orchestrator breakdowns.
        """
        diagnostics = EngineDiagnostics(
            lifecycle=self._lifecycle,
            uptime_seconds=round(_time_module.time() - self._start_time, 2) if self._start_time > 0 else 0.0,
            total_frames_rendered=self._frame_count,
            total_ticks_processed=self._tick_count,
            orchestrator_states={
                desc.category.value: desc.state.value
                for desc in self._orchestrators.values()
            },
            memory_estimate_mb=self._estimate_memory_usage(),
            subsystem_count=sum(len(d.managed_subsystems) for d in self._orchestrators.values()),
            active_subsystems=sum(
                len(d.managed_subsystems)
                for d in self._orchestrators.values()
                if d.state == OrchestratorState.ACTIVE
            ),
            subsystems_in_error=sum(
                1 for d in self._orchestrators.values()
                if d.state == OrchestratorState.ERROR
            ),
            avg_fps=self._avg_fps_accumulator / max(1, self._fps_sample_count),
            avg_frame_time_ms=self._compute_avg_frame_time(),
            avg_tick_time_ms=self._compute_avg_tick_time(),
            total_errors=self._total_errors,
        )

        report: Dict[str, Any] = {
            "diagnostics": diagnostics.to_dict(),
            "orchestrators": self.get_status()["orchestrators"],
            "recent_frames": [r.to_dict() for r in self._frame_reports[-10:]],
            "recent_ticks": [r.to_dict() for r in self._tick_reports[-10:]],
        }

        # Add per-orchestrator detailed breakdown
        report["orchestrator_details"] = {}
        for oid in self._orchestrator_order:
            desc = self._orchestrators[oid]
            report["orchestrator_details"][desc.category.value] = desc.to_dict()

        return report

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, subsystems: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Selectively initialize engine subsystems by category name or 'all'.

        Args:
            subsystems: List of SystemCategory values to initialize, or None for full init.
                        Also accepts Special modes: 'headless', 'minimal', 'server', 'editor'.

        Returns:
            Dict with initialization results per orchestrator.
        """
        if self._lifecycle not in (EngineLifecycle.COLD, EngineLifecycle.TERMINATED):
            return {"success": False, "error": f"Engine already in lifecycle: {self._lifecycle.value}"}

        self._lifecycle = EngineLifecycle.BOOTING
        self._start_time = _time_module.time()

        # Determine which orchestrators to initialize
        target_categories: set[str] = set()

        if subsystems is None:
            self._init_mode = InitializationMode.FULL
            target_categories = {cat.value for cat in SystemCategory}
        elif len(subsystems) == 1 and subsystems[0].lower() in (
            "headless", "minimal", "server", "editor", "full",
        ):
            mode_map = {
                "headless": InitializationMode.HEADLESS,
                "minimal": InitializationMode.MINIMAL,
                "server": InitializationMode.SERVER,
                "editor": InitializationMode.EDITOR,
                "full": InitializationMode.FULL,
            }
            self._init_mode = mode_map[subsystems[0].lower()]
            target_categories = self._resolve_mode_categories(self._init_mode)
        else:
            self._init_mode = InitializationMode.CUSTOM
            target_categories = set(subsystems)

        init_results: Dict[str, Dict[str, Any]] = {}
        overall_success = True

        for oid in self._init_order:
            desc = self._orchestrators[oid]
            if desc.category.value not in target_categories:
                continue

            init_start = _time_module.time()
            try:
                desc.state = OrchestratorState.INITIALIZING
                # --- Simulate subsystem initialization ---
                self._simulate_orchestrator_init(desc)
                desc.state = OrchestratorState.ACTIVE
                desc.init_time_ms = round((_time_module.time() - init_start) * 1000, 4)
                init_results[desc.category.value] = {
                    "success": True,
                    "state": desc.state.value,
                    "init_time_ms": desc.init_time_ms,
                    "subsystems": len(desc.managed_subsystems),
                }
            except Exception as exc:
                desc.state = OrchestratorState.ERROR
                desc.error_count += 1
                desc.last_error = str(exc)
                self._total_errors += 1
                overall_success = False
                init_results[desc.category.value] = {
                    "success": False,
                    "state": desc.state.value,
                    "error": str(exc),
                }

        # Initialize core engine subsystem instances
        self._deterministic_core = get_deterministic_core()
        self._gpu_compute = get_gpu_compute()
        self._skeletal_blending = get_skeletal_blending()
        self._volumetric_rendering = get_volumetric_rendering()
        self._crowd_dynamics = get_crowd_dynamics()
        self._fluid_dynamics = get_fluid_dynamics()

        if overall_success and any(r.get("success") for r in init_results.values()):
            self._lifecycle = EngineLifecycle.RUNNING
        else:
            self._lifecycle = EngineLifecycle.SUSPENDED

        return {
            "success": overall_success,
            "lifecycle": self._lifecycle.value,
            "initialization_mode": self._init_mode.value,
            "total_init_time_ms": round(
                sum(r.get("init_time_ms", 0) for r in init_results.values()), 4,
            ),
            "orchestrators": init_results,
        }

    def _resolve_mode_categories(self, mode: InitializationMode) -> set[str]:
        """Map initialization mode presets to target category sets."""
        mode_sets = {
            InitializationMode.FULL: {cat.value for cat in SystemCategory},
            InitializationMode.HEADLESS: {
                SystemCategory.PHYSICS.value,
                SystemCategory.SCENE_MANAGEMENT.value,
                SystemCategory.ECS.value,
                SystemCategory.WORLD_SYSTEMS.value,
                SystemCategory.PERFORMANCE_DIAGNOSTICS.value,
                SystemCategory.RESOURCE_ASSETS.value,
            },
            InitializationMode.MINIMAL: {
                SystemCategory.PHYSICS.value,
                SystemCategory.ECS.value,
                SystemCategory.WORLD_SYSTEMS.value,
            },
            InitializationMode.SERVER: {
                SystemCategory.PHYSICS.value,
                SystemCategory.SCENE_MANAGEMENT.value,
                SystemCategory.ECS.value,
                SystemCategory.PERFORMANCE_DIAGNOSTICS.value,
                SystemCategory.RESOURCE_ASSETS.value,
            },
            InitializationMode.EDITOR: {cat.value for cat in SystemCategory},
            InitializationMode.CUSTOM: set(),
        }
        return mode_sets.get(mode, set())

    def _simulate_orchestrator_init(self, desc: OrchestratorDescriptor):
        """Simulated subsystem initialization; replace with actual engine wiring."""
        # In a full engine, this would instantiate and configure each listed subsystem
        _ = desc.managed_subsystems  # referenced during real initialization

    # ------------------------------------------------------------------
    # Unified Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float) -> Dict[str, Any]:
        """
        Execute a unified game-loop tick across all active orchestrators.

        Runs orchestrators in dependency order: input → physics → world →
        ecs → animation → scene → audio → rendering → performance → resources.

        Args:
            delta_time: Frame delta time in seconds.

        Returns:
            Dict with tick results, per-orchestrator timings, and health data.
        """
        if self._lifecycle != EngineLifecycle.RUNNING:
            return {"success": False, "error": f"Engine not running: {self._lifecycle.value}"}

        tick_start = _time_module.time()
        orchestrator_timings: Dict[str, float] = {}
        active_count = 0
        degraded_count = 0
        warnings: List[str] = []

        for oid in self._tick_order:
            desc = self._orchestrators.get(oid)
            if not desc or not desc.enabled:
                continue
            if desc.state != OrchestratorState.ACTIVE:
                if desc.state == OrchestratorState.ERROR:
                    degraded_count += 1
                continue

            orch_start = _time_module.time()
            try:
                self._simulate_orchestrator_tick(desc, delta_time)
                desc.tick_count += 1
            except Exception as exc:
                desc.state = OrchestratorState.DEGRADED
                desc.error_count += 1
                desc.last_error = str(exc)
                self._total_errors += 1
                degraded_count += 1
                warnings.append(f"{desc.name} tick failed: {exc}")

            elapsed = round((_time_module.time() - orch_start) * 1000, 4)
            desc.last_tick_ms = elapsed
            orchestrator_timings[desc.category.value] = elapsed
            active_count += 1

        total_tick_ms = round((_time_module.time() - tick_start) * 1000, 4)
        self._tick_count += 1

        # Compute health score (0-100)
        total_orchestrators = sum(1 for oid in self._tick_order
                                  if self._orchestrators.get(oid) and self._orchestrators[oid].enabled)
        health_score = 100.0
        if total_orchestrators > 0:
            health_penalty = (degraded_count / total_orchestrators) * 60.0
            time_penalty = max(0, (total_tick_ms - self._tick_budget_ms) / self._tick_budget_ms * 40.0)
            health_score = max(0.0, 100.0 - health_penalty - time_penalty)

        report = TickReport(
            frame_number=self._tick_count,
            delta_time=delta_time,
            orchestrator_timings=orchestrator_timings,
            total_tick_ms=total_tick_ms,
            active_subsystems=active_count,
            degraded_subsystems=degraded_count,
            health_score=health_score,
            warnings=warnings,
        )
        self._tick_reports.append(report)

        # Keep bounded history
        if len(self._tick_reports) > 900:
            self._tick_reports = self._tick_reports[-300:]

        return {
            "success": True,
            "frame_number": self._tick_count,
            "total_tick_ms": total_tick_ms,
            "orchestrator_timings": orchestrator_timings,
            "active_orchestrators": active_count,
            "degraded_orchestrators": degraded_count,
            "health_score": round(health_score, 2),
            "over_budget": total_tick_ms > self._tick_budget_ms,
            "warnings": warnings,
        }

    def _simulate_orchestrator_tick(self, desc: OrchestratorDescriptor, delta_time: float):
        """Simulated orchestrator tick; replace with actual subsystem updates."""
        # Different subsystems simulate different amounts of work
        base_work_map = {
            SystemCategory.RENDERING: 0.05,
            SystemCategory.PHYSICS: 0.1,
            SystemCategory.SCENE_MANAGEMENT: 0.03,
            SystemCategory.AUDIO: 0.02,
            SystemCategory.ECS: 0.06,
            SystemCategory.ANIMATION: 0.04,
            SystemCategory.WORLD_SYSTEMS: 0.05,
            SystemCategory.INPUT_UI: 0.01,
            SystemCategory.PERFORMANCE_DIAGNOSTICS: 0.01,
            SystemCategory.RESOURCE_ASSETS: 0.02,
        }
        _ = base_work_map.get(desc.category, 0.02) * delta_time
        # Real implementation would delegate to actual engine subsystems

    # ------------------------------------------------------------------
    # Coordinated Render Pipeline
    # ------------------------------------------------------------------

    def render_frame(self) -> Dict[str, Any]:
        """
        Execute the coordinated render pipeline across all rendering subsystems.

        Orquestrates: render pipeline → render layers → render passes →
        post-processing → GPU batches → shadows → lighting 2D → skybox →
        decals → sprite animation → trails → parallax → particles →
        material graph → shader system.

        Returns:
            Dict with frame report, render pipeline metrics, and performance data.
        """
        if self._lifecycle != EngineLifecycle.RUNNING:
            return {"success": False, "error": f"Engine not running: {self._lifecycle.value}"}

        frame_start = _time_module.time()

        # Orchestrate the complete render pipeline
        total_draw_calls = 0
        total_triangles = 0
        total_batches = 0
        visible_objects = 0
        culled_objects = 0
        shadow_casters = 0
        active_particles = 0
        material_switches = 0
        post_process_count = 0

        # Simulate render pipeline execution
        render_data = self._simulate_render_pipeline()
        total_draw_calls = render_data["draw_calls"]
        total_triangles = render_data["triangles"]
        total_batches = render_data["batches"]
        visible_objects = render_data["visible"]
        culled_objects = render_data["culled"]
        shadow_casters = render_data["shadows"]
        active_particles = render_data["particles"]
        material_switches = render_data["materials"]
        post_process_count = render_data["post_processes"]

        frame_time = (_time_module.time() - frame_start) * 1000
        fps = 1000.0 / max(0.001, frame_time)

        self._frame_count += 1
        self._avg_fps_accumulator += fps
        self._fps_sample_count += 1

        # Resolution scaling based on performance
        resolution_scale = self._compute_resolution_scale(fps)

        report = FrameReport(
            frame_id=self._frame_count,
            render_time_ms=frame_time,
            frame_time_ms=frame_time,
            fps=fps,
            draw_calls=total_draw_calls,
            triangles=total_triangles,
            batches=total_batches,
            visible_objects=visible_objects,
            post_process_effects=post_process_count,
            resolution_scale=resolution_scale,
            culled_objects=culled_objects,
            shadow_casters=shadow_casters,
            active_particle_systems=active_particles,
            material_switches=material_switches,
        )
        self._frame_reports.append(report)

        # Keep bounded history
        if len(self._frame_reports) > 600:
            self._frame_reports = self._frame_reports[-300:]

        # Mark rendering orchestrator activity
        rendering_oid = self._find_orchestrator_by_category(SystemCategory.RENDERING)
        if rendering_oid:
            desc = self._orchestrators[rendering_oid]
            desc.tick_count += 1
            desc.last_tick_ms = frame_time

        return {
            "success": True,
            "frame_report": report.to_dict(),
            "render_time_ms": round(frame_time, 4),
            "fps": round(fps, 1),
            "resolution_scale": resolution_scale,
        }

    def _simulate_render_pipeline(self) -> Dict[str, int]:
        """Simulate the coordinated render pipeline execution."""
        import random as _random

        base_draw_calls = 200
        base_triangles = 50000
        fidelity = 1.0 if self._frame_count % 10 != 0 else 0.85  # occasional perf dip

        return {
            "draw_calls": int(base_draw_calls * fidelity * (0.8 + _random.random() * 0.4)),
            "triangles": int(base_triangles * fidelity * (0.8 + _random.random() * 0.4)),
            "batches": int(base_draw_calls * fidelity * 0.15),
            "visible": int(base_draw_calls * fidelity * 1.5),
            "culled": int(base_draw_calls * fidelity * 2.0),
            "shadows": int(base_draw_calls * fidelity * 0.25),
            "particles": int(base_draw_calls * fidelity * 0.1),
            "materials": int(base_draw_calls * fidelity * 0.05),
            "post_processes": 5,
        }

    def _compute_resolution_scale(self, current_fps: float) -> float:
        """Dynamically adjust resolution scale to maintain target FPS."""
        if current_fps < self._render_target_fps * 0.75:
            return max(0.5, 1.0 - 0.1)
        elif current_fps < self._render_target_fps * 0.9:
            return 0.9
        elif current_fps > self._render_target_fps * 1.3:
            return min(1.0, 1.0 + 0.05)
        return 1.0

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> Optional[Dict[str, Any]]:
        """
        Gracefully shut down all engine orchestration and release resources.

        Orchestrators are stopped in reverse dependency order (rendering first,
        input last) to ensure dependent subsystems shut down cleanly.
        """
        if self._lifecycle in (EngineLifecycle.SHUTTING_DOWN, EngineLifecycle.TERMINATED):
            return None

        self._lifecycle = EngineLifecycle.SHUTTING_DOWN
        shutdown_results: Dict[str, Dict[str, Any]] = {}

        for oid in self._shutdown_order:
            desc = self._orchestrators.get(oid)
            if not desc:
                continue

            shutdown_start = _time_module.time()
            try:
                self._simulate_orchestrator_shutdown(desc)
                desc.state = OrchestratorState.SHUTDOWN
                elapsed = round((_time_module.time() - shutdown_start) * 1000, 4)
                shutdown_results[desc.category.value] = {
                    "success": True,
                    "shutdown_time_ms": elapsed,
                }
            except Exception as exc:
                desc.state = OrchestratorState.ERROR
                desc.error_count += 1
                desc.last_error = str(exc)
                self._total_errors += 1
                shutdown_results[desc.category.value] = {
                    "success": False,
                    "error": str(exc),
                }

        # Shutdown core subsystems
        if self._skeletal_blending:
            self._skeletal_blending = None
        if self._gpu_compute:
            self._gpu_compute = None
        if self._deterministic_core:
            self._deterministic_core = None
        if self._fluid_dynamics:
            self._fluid_dynamics = None
        if self._crowd_dynamics:
            self._crowd_dynamics = None
        if self._volumetric_rendering:
            self._volumetric_rendering = None

        self._lifecycle = EngineLifecycle.TERMINATED

        return {
            "success": True,
            "lifecycle": self._lifecycle.value,
            "shutdown_results": shutdown_results,
            "total_uptime_seconds": round(_time_module.time() - self._start_time, 2) if self._start_time > 0 else 0.0,
        }

    def _simulate_orchestrator_shutdown(self, desc: OrchestratorDescriptor):
        """Simulated orchestrator teardown; replace with actual subsystem shutdown."""
        _ = desc.managed_subsystems  # referenced during real shutdown

    # ------------------------------------------------------------------
    # Internal Utilities
    # ------------------------------------------------------------------

    def _estimate_memory_usage(self) -> float:
        """Estimate total engine memory footprint in MB."""
        base_mb = 50.0
        per_subsystem_mb = 2.5
        total_subsystems = sum(
            len(d.managed_subsystems)
            for d in self._orchestrators.values()
            if d.state == OrchestratorState.ACTIVE
        )
        return base_mb + total_subsystems * per_subsystem_mb

    def _compute_avg_frame_time(self) -> float:
        """Compute average frame time from recent frame reports."""
        if not self._frame_reports:
            return 0.0
        recent = self._frame_reports[-60:]
        return sum(r.frame_time_ms for r in recent) / len(recent)

    def _compute_avg_tick_time(self) -> float:
        """Compute average tick time from recent tick reports."""
        if not self._tick_reports:
            return 0.0
        recent = self._tick_reports[-60:]
        return sum(r.total_tick_ms for r in recent) / len(recent)

    # ------------------------------------------------------------------
    # Runtime Controls
    # ------------------------------------------------------------------

    def suspend(self) -> bool:
        """Suspend engine processing without full shutdown."""
        if self._lifecycle != EngineLifecycle.RUNNING:
            return False
        self._lifecycle = EngineLifecycle.SUSPENDED
        for desc in self._orchestrators.values():
            if desc.state == OrchestratorState.ACTIVE:
                desc.state = OrchestratorState.PAUSED
        return True

    def resume(self) -> bool:
        """Resume engine processing after suspension."""
        if self._lifecycle != EngineLifecycle.SUSPENDED:
            return False
        self._lifecycle = EngineLifecycle.RUNNING
        for desc in self._orchestrators.values():
            if desc.state == OrchestratorState.PAUSED:
                desc.state = OrchestratorState.ACTIVE
        return True

    def set_orchestrator_enabled(self, category: str, enabled: bool) -> bool:
        """Enable or disable an orchestrator by category name."""
        oid = self._find_orchestrator_by_category_string(category)
        if not oid:
            return False
        self._orchestrators[oid].enabled = enabled
        return True

    def _find_orchestrator_by_category_string(self, category_str: str) -> str:
        """Look up orchestrator ID by category string value."""
        for oid, desc in self._orchestrators.items():
            if desc.category.value == category_str:
                return oid
        try:
            category = SystemCategory(category_str)
            return self._find_orchestrator_by_category(category)
        except ValueError:
            return ""

    def get_orchestrator_state(self, category: str) -> Optional[str]:
        """Query the state of a specific orchestrator by category name."""
        oid = self._find_orchestrator_by_category_string(category)
        if not oid:
            return None
        return self._orchestrators[oid].state.value

    def get_lifecycle(self) -> str:
        """Return the current engine lifecycle state."""
        return self._lifecycle.value

    @classmethod
    def get_instance(cls) -> "EngineUnificationCore":
        """Return the singleton instance."""
        return cls()

    def reset(self) -> None:
        """Full engine reset: shutdown all orchestrators and clear state."""
        if self._lifecycle not in (EngineLifecycle.TERMINATED, EngineLifecycle.COLD):
            self.shutdown()

        with self._lock:
            self._lifecycle = EngineLifecycle.COLD
            self._frame_count = 0
            self._tick_count = 0
            self._start_time = 0.0
            self._tick_reports.clear()
            self._frame_reports.clear()
            self._total_errors = 0
            self._avg_fps_accumulator = 0.0
            self._fps_sample_count = 0

            for desc in self._orchestrators.values():
                desc.state = OrchestratorState.UNINITIALIZED
                desc.init_time_ms = 0.0
                desc.last_tick_ms = 0.0
                desc.tick_count = 0
                desc.error_count = 0
                desc.last_error = ""
                desc.enabled = True

            self._deterministic_core = None
            self._gpu_compute = None
            self._skeletal_blending = None
            self._volumetric_rendering = None
            self._crowd_dynamics = None
            self._fluid_dynamics = None

    def get_categories(self) -> List[str]:
        """Return all orchestrator category names."""
        return [cat.value for cat in SystemCategory]

    def list_subsystems(self, category: Optional[str] = None) -> Dict[str, List[str]]:
        """List managed subsystems per category, or for a specific category."""
        result: Dict[str, List[str]] = {}
        for desc in self._orchestrators.values():
            if category and desc.category.value != category:
                continue
            result[desc.category.value] = list(desc.managed_subsystems)
        return result

    def set_target_fps(self, fps: int) -> None:
        """Set the rendering target FPS for dynamic resolution scaling."""
        self._render_target_fps = max(30, min(240, fps))

    def set_tick_budget_ms(self, budget_ms: float) -> None:
        """Configure the per-tick time budget in milliseconds."""
        self._tick_budget_ms = max(1.0, min(16.0, budget_ms))


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_engine_unification_core() -> EngineUnificationCore:
    """
    Return the singleton EngineUnificationCore instance.

    This is the primary entry point for engine orchestration throughout
    the SparkLabs runtime.
    """
    return EngineUnificationCore()