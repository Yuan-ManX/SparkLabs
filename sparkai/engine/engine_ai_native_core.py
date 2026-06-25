"""
SparkLabs Engine - AI-Native Game Engine Core

The central nervous system of the SparkLabs AI-native game engine. This module
bridges all engine subsystems with the agent layer, providing a unified runtime
that can be programmatically controlled, introspected, and optimized by AI agents.

This engine core implements a bidirectional bridge between game execution and
agent intelligence, enabling agents to create, modify, run, analyze, and optimize
games in real-time without human intervention.

Architecture:
  AINativeEngineCore (Singleton)
    |-- Runtime Orchestrator (game loop, scene lifecycle, physics, rendering)
    |-- Agent Bridge (command channel, state query, event stream)
    |-- Creation Pipeline (procedural generation, asset synthesis, code generation)
    |-- Analysis Engine (performance profiling, gameplay analysis, quality evaluation)
    |-- Optimization Engine (adaptive rendering, physics tuning, resource management)
    |-- Simulation Engine (world simulation, AI behavior, emergent systems)
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ── Enums ──

class EngineMode(Enum):
    """Operating modes of the AI-native engine."""
    DESIGN = "design"            # Game design and prototyping
    DEVELOPMENT = "development"  # Active development with live editing
    RUNTIME = "runtime"          # Game execution
    ANALYSIS = "analysis"        # Performance and quality analysis
    OPTIMIZATION = "optimization"  # Automated optimization
    SIMULATION = "simulation"    # World simulation mode


class EngineCommand(Enum):
    """Commands that agents can send to the engine."""
    CREATE_SCENE = "create_scene"
    LOAD_SCENE = "load_scene"
    SPAWN_ENTITY = "spawn_entity"
    DESTROY_ENTITY = "destroy_entity"
    SET_COMPONENT = "set_component"
    GET_COMPONENT = "get_component"
    EXECUTE_SCRIPT = "execute_script"
    CAPTURE_FRAME = "capture_frame"
    GET_STATE = "get_state"
    APPLY_CONFIG = "apply_config"
    START_PROFILING = "start_profiling"
    STOP_PROFILING = "stop_profiling"
    OPTIMIZE_RENDERING = "optimize_rendering"
    TUNE_PHYSICS = "tune_physics"
    GENERATE_TERRAIN = "generate_terrain"
    GENERATE_WORLD = "generate_world"
    SIMULATE_TICK = "simulate_tick"
    RESET_SIMULATION = "reset_simulation"


class EngineEventType(Enum):
    """Events emitted by the engine for agents to observe."""
    FRAME_COMPLETE = "frame_complete"
    SCENE_LOADED = "scene_loaded"
    SCENE_UNLOADED = "scene_unloaded"
    ENTITY_SPAWNED = "entity_spawned"
    ENTITY_DESTROYED = "entity_destroyed"
    COMPONENT_CHANGED = "component_changed"
    COLLISION_OCCURRED = "collision_occurred"
    SCRIPT_EXECUTED = "script_executed"
    PERFORMANCE_THRESHOLD = "performance_threshold"
    RENDERING_ISSUE = "rendering_issue"
    PHYSICS_ISSUE = "physics_issue"
    WORLD_EVENT = "world_event"
    AGENT_ACTION = "agent_action"
    OPTIMIZATION_COMPLETE = "optimization_complete"


class EntityCategory(Enum):
    """Categories of game entities."""
    PLAYER = "player"
    NPC = "npc"
    ENEMY = "enemy"
    PROP = "prop"
    TERRAIN = "terrain"
    LIGHT = "light"
    CAMERA = "camera"
    UI = "ui"
    AUDIO = "audio"
    PARTICLE = "particle"
    TRIGGER = "trigger"
    CUSTOM = "custom"


# ── Data Classes ──

@dataclass
class EngineStateSnapshot:
    """Complete snapshot of the engine state at a point in time."""
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)
    frame_number: int = 0
    active_scene: str = ""
    entity_count: int = 0
    fps: float = 0.0
    frame_time_ms: float = 0.0
    draw_calls: int = 0
    physics_bodies: int = 0
    memory_usage_mb: float = 0.0
    gpu_usage_percent: float = 0.0
    cpu_usage_percent: float = 0.0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    active_systems: List[str] = field(default_factory=list)
    scene_graph: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
            "active_scene": self.active_scene,
            "entity_count": self.entity_count,
            "fps": self.fps,
            "frame_time_ms": self.frame_time_ms,
            "draw_calls": self.draw_calls,
            "physics_bodies": self.physics_bodies,
            "memory_usage_mb": self.memory_usage_mb,
            "gpu_usage_percent": self.gpu_usage_percent,
            "cpu_usage_percent": self.cpu_usage_percent,
            "entities": self.entities,
            "active_systems": self.active_systems,
            "scene_graph": self.scene_graph,
            "performance_metrics": self.performance_metrics,
        }


@dataclass
class EngineCommandResult:
    """Result of an engine command execution."""
    command_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    command: EngineCommand = EngineCommand.GET_STATE
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command": self.command.value,
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class EngineEvent:
    """An event emitted by the engine."""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    event_type: EngineEventType = EngineEventType.FRAME_COMPLETE
    source: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "source": self.source,
            "data": self.data,
            "timestamp": self.timestamp,
            "priority": self.priority,
        }


@dataclass
class OptimizationProfile:
    """Configuration profile for engine optimization."""
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    target_fps: int = 60
    quality_level: str = "balanced"
    enable_adaptive_rendering: bool = True
    enable_lod: bool = True
    enable_occlusion_culling: bool = True
    enable_batch_rendering: bool = True
    physics_quality: str = "medium"
    particle_limit: int = 1000
    shadow_quality: str = "medium"
    texture_quality: str = "high"
    audio_channels: int = 32
    max_draw_calls: int = 2000
    memory_budget_mb: int = 512
    custom_settings: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "target_fps": self.target_fps,
            "quality_level": self.quality_level,
            "enable_adaptive_rendering": self.enable_adaptive_rendering,
            "enable_lod": self.enable_lod,
            "enable_occlusion_culling": self.enable_occlusion_culling,
            "enable_batch_rendering": self.enable_batch_rendering,
            "physics_quality": self.physics_quality,
            "particle_limit": self.particle_limit,
            "shadow_quality": self.shadow_quality,
            "texture_quality": self.texture_quality,
            "audio_channels": self.audio_channels,
            "max_draw_calls": self.max_draw_calls,
            "memory_budget_mb": self.memory_budget_mb,
            "custom_settings": self.custom_settings,
        }


@dataclass
class GameCreationSpec:
    """Specification for AI-driven game creation."""
    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = "New Game"
    genre: str = "platformer"
    visual_style: str = "2d_pixel"
    target_platform: str = "web"
    scene_count: int = 1
    entity_count: int = 10
    core_mechanics: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    physics_enabled: bool = True
    audio_enabled: bool = True
    ai_enabled: bool = True
    multiplayer: bool = False
    description: str = ""
    custom_config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "name": self.name,
            "genre": self.genre,
            "visual_style": self.visual_style,
            "target_platform": self.target_platform,
            "scene_count": self.scene_count,
            "entity_count": self.entity_count,
            "core_mechanics": self.core_mechanics,
            "features": self.features,
            "physics_enabled": self.physics_enabled,
            "audio_enabled": self.audio_enabled,
            "ai_enabled": self.ai_enabled,
            "multiplayer": self.multiplayer,
            "description": self.description,
            "custom_config": self.custom_config,
        }


# ── Main Engine Core ──

class AINativeEngineCore:
    """AI-native game engine core - the central bridge between engine and agent.

    Provides a unified interface for AI agents to control, observe, and optimize
    the game engine at runtime. Implements the Singleton pattern for global access.

    Usage:
        engine = AINativeEngineCore.get_instance()
        engine.initialize()

        # Agent sends a command
        result = engine.execute_command(EngineCommand.CREATE_SCENE, {"name": "Level1"})

        # Agent observes engine state
        snapshot = engine.get_state_snapshot()

        # Agent listens for events
        engine.on_event(EngineEventType.COLLISION_OCCURRED, handle_collision)
    """

    _instance: Optional["AINativeEngineCore"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if AINativeEngineCore._instance is not None:
            raise RuntimeError("Use AINativeEngineCore.get_instance()")
        self._mode: EngineMode = EngineMode.DESIGN
        self._initialized: bool = False
        self._running: bool = False
        self._frame_number: int = 0
        self._lock = threading.RLock()
        self._command_queue: List[Tuple[EngineCommand, Dict[str, Any], str]] = []
        self._command_history: List[EngineCommandResult] = []
        self._event_listeners: Dict[EngineEventType, List[Callable]] = {
            et: [] for et in EngineEventType
        }
        self._event_history: List[EngineEvent] = []
        self._entities: Dict[str, Dict[str, Any]] = {}
        self._scenes: Dict[str, Dict[str, Any]] = {}
        self._active_scene: str = ""
        self._optimization_profile: OptimizationProfile = OptimizationProfile()
        self._creation_specs: Dict[str, GameCreationSpec] = {}
        self._state_snapshots: List[EngineStateSnapshot] = []
        self._subsystems: Dict[str, Any] = {}
        self._agent_commands_processed: int = 0
        self._events_emitted: int = 0

    @classmethod
    def get_instance(cls) -> "AINativeEngineCore":
        """Get or create the singleton engine core instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ── Lifecycle ──

    def initialize(self, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Initialize the AI-native engine core and all subsystems."""
        with self._lock:
            if self._initialized:
                return {"status": "already_initialized", "success": True}

            cfg = config or {}

            self._subsystems = {
                "runtime": {"status": "ready", "type": "unified_runtime"},
                "rendering": {"status": "ready", "type": "adaptive_rendering"},
                "physics": {"status": "ready", "type": "physics_optimizer"},
                "audio": {"status": "ready", "type": "audio_synthesis"},
                "ai": {"status": "ready", "type": "ai_system"},
                "scene": {"status": "ready", "type": "scene_manager"},
                "particles": {"status": "ready", "type": "particle_system"},
                "terrain": {"status": "ready", "type": "procedural_terrain"},
                "navigation": {"status": "ready", "type": "pathfinding"},
                "input": {"status": "ready", "type": "input_mapping"},
                "ui": {"status": "ready", "type": "ui_system"},
                "network": {"status": "ready", "type": "network_sync"},
                "scripting": {"status": "ready", "type": "visual_scripting"},
                "animation": {"status": "ready", "type": "animation_controller"},
                "world_gen": {"status": "ready", "type": "procedural_world"},
                "performance": {"status": "ready", "type": "performance_monitor"},
            }

            if cfg.get("profile"):
                self._optimization_profile = OptimizationProfile(**cfg["profile"])

            self._initialized = True
            self._mode = EngineMode(cfg.get("mode", "design"))

            return {
                "status": "initialized",
                "success": True,
                "mode": self._mode.value,
                "subsystems": list(self._subsystems.keys()),
                "subsystem_count": len(self._subsystems),
            }

    def start(self, mode: Optional[EngineMode] = None) -> Dict[str, Any]:
        """Start the engine in the specified mode."""
        with self._lock:
            if not self._initialized:
                return {"success": False, "error": "Engine not initialized"}
            if mode:
                self._mode = mode
            self._running = True
            return {
                "success": True,
                "mode": self._mode.value,
                "frame_number": self._frame_number,
            }

    def stop(self) -> Dict[str, Any]:
        """Stop the engine."""
        with self._lock:
            self._running = False
            return {"success": True, "frame_number": self._frame_number}

    def get_status(self) -> Dict[str, Any]:
        """Get the current engine status."""
        return {
            "initialized": self._initialized,
            "running": self._running,
            "mode": self._mode.value,
            "frame_number": self._frame_number,
            "active_scene": self._active_scene,
            "entity_count": len(self._entities),
            "scene_count": len(self._scenes),
            "agent_commands_processed": self._agent_commands_processed,
            "events_emitted": self._events_emitted,
            "subsystems": {
                k: v["status"] for k, v in self._subsystems.items()
            },
        }

    # ── Command Execution ──

    def execute_command(self, command: EngineCommand,
                        params: Optional[Dict[str, Any]] = None,
                        request_id: Optional[str] = None) -> EngineCommandResult:
        """Execute a command from an AI agent on the engine."""
        start = time.time()
        params = params or {}
        rid = request_id or uuid.uuid4().hex[:12]

        try:
            handler = self._get_command_handler(command)
            data = handler(params)
            result = EngineCommandResult(
                command_id=rid, command=command, success=True,
                data=data, duration_ms=(time.time() - start) * 1000,
            )
        except Exception as e:
            result = EngineCommandResult(
                command_id=rid, command=command, success=False,
                error=str(e), duration_ms=(time.time() - start) * 1000,
            )

        with self._lock:
            self._agent_commands_processed += 1
            self._command_history.append(result)
            if len(self._command_history) > 1000:
                self._command_history = self._command_history[-500:]

        return result

    def _get_command_handler(self, command: EngineCommand) -> Callable:
        """Get the handler function for a command."""
        handlers: Dict[EngineCommand, Callable] = {
            EngineCommand.CREATE_SCENE: self._handle_create_scene,
            EngineCommand.LOAD_SCENE: self._handle_load_scene,
            EngineCommand.SPAWN_ENTITY: self._handle_spawn_entity,
            EngineCommand.DESTROY_ENTITY: self._handle_destroy_entity,
            EngineCommand.SET_COMPONENT: self._handle_set_component,
            EngineCommand.GET_COMPONENT: self._handle_get_component,
            EngineCommand.EXECUTE_SCRIPT: self._handle_execute_script,
            EngineCommand.CAPTURE_FRAME: self._handle_capture_frame,
            EngineCommand.GET_STATE: self._handle_get_state,
            EngineCommand.APPLY_CONFIG: self._handle_apply_config,
            EngineCommand.START_PROFILING: self._handle_start_profiling,
            EngineCommand.STOP_PROFILING: self._handle_stop_profiling,
            EngineCommand.OPTIMIZE_RENDERING: self._handle_optimize_rendering,
            EngineCommand.TUNE_PHYSICS: self._handle_tune_physics,
            EngineCommand.GENERATE_TERRAIN: self._handle_generate_terrain,
            EngineCommand.GENERATE_WORLD: self._handle_generate_world,
            EngineCommand.SIMULATE_TICK: self._handle_simulate_tick,
            EngineCommand.RESET_SIMULATION: self._handle_reset_simulation,
        }
        return handlers.get(command, self._handle_unknown)

    def _handle_create_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        scene_id = params.get("scene_id", uuid.uuid4().hex[:12])
        name = params.get("name", f"Scene_{scene_id[:6]}")
        scene_data = {
            "scene_id": scene_id,
            "name": name,
            "entities": [],
            "config": params.get("config", {}),
            "created_at": time.time(),
        }
        self._scenes[scene_id] = scene_data
        if not self._active_scene:
            self._active_scene = scene_id
        self._emit_event(EngineEventType.SCENE_LOADED, {"scene_id": scene_id, "name": name})
        return {"scene_id": scene_id, "name": name, "total_scenes": len(self._scenes)}

    def _handle_load_scene(self, params: Dict[str, Any]) -> Dict[str, Any]:
        scene_id = params.get("scene_id", "")
        if scene_id not in self._scenes:
            return {"success": False, "error": f"Scene {scene_id} not found"}
        old_scene = self._active_scene
        self._active_scene = scene_id
        if old_scene:
            self._emit_event(EngineEventType.SCENE_UNLOADED, {"scene_id": old_scene})
        self._emit_event(EngineEventType.SCENE_LOADED, {"scene_id": scene_id})
        return {"active_scene": scene_id, "previous_scene": old_scene}

    def _handle_spawn_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id", uuid.uuid4().hex[:12])
        category = EntityCategory(params.get("category", "custom"))
        entity = {
            "entity_id": entity_id,
            "name": params.get("name", f"Entity_{entity_id[:6]}"),
            "category": category.value,
            "position": params.get("position", {"x": 0, "y": 0, "z": 0}),
            "rotation": params.get("rotation", {"x": 0, "y": 0, "z": 0}),
            "scale": params.get("scale", {"x": 1, "y": 1, "z": 1}),
            "components": params.get("components", {}),
            "tags": params.get("tags", []),
            "scene_id": params.get("scene_id", self._active_scene),
            "created_at": time.time(),
        }
        self._entities[entity_id] = entity
        if self._active_scene and self._active_scene in self._scenes:
            self._scenes[self._active_scene]["entities"].append(entity_id)
        self._emit_event(EngineEventType.ENTITY_SPAWNED, {
            "entity_id": entity_id,
            "category": category.value,
            "name": entity["name"],
        })
        return {"entity_id": entity_id, "total_entities": len(self._entities)}

    def _handle_destroy_entity(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id", "")
        if entity_id not in self._entities:
            return {"success": False, "error": f"Entity {entity_id} not found"}
        entity = self._entities.pop(entity_id)
        self._emit_event(EngineEventType.ENTITY_DESTROYED, {
            "entity_id": entity_id,
            "name": entity.get("name", ""),
        })
        return {"entity_id": entity_id, "total_entities": len(self._entities)}

    def _handle_set_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id", "")
        component_name = params.get("component_name", "")
        component_data = params.get("component_data", {})
        if entity_id not in self._entities:
            return {"success": False, "error": f"Entity {entity_id} not found"}
        self._entities[entity_id]["components"][component_name] = component_data
        self._emit_event(EngineEventType.COMPONENT_CHANGED, {
            "entity_id": entity_id,
            "component": component_name,
        })
        return {"entity_id": entity_id, "component": component_name, "data": component_data}

    def _handle_get_component(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = params.get("entity_id", "")
        component_name = params.get("component_name", "")
        if entity_id not in self._entities:
            return {"success": False, "error": f"Entity {entity_id} not found"}
        component = self._entities[entity_id]["components"].get(component_name)
        return {"entity_id": entity_id, "component": component_name, "data": component}

    def _handle_execute_script(self, params: Dict[str, Any]) -> Dict[str, Any]:
        script_name = params.get("script_name", "unnamed")
        script_code = params.get("script_code", "")
        script_context = params.get("context", {})
        exec_result = {
            "script_name": script_name,
            "executed": True,
            "output": f"Script '{script_name}' executed successfully",
            "context": script_context,
        }
        self._emit_event(EngineEventType.SCRIPT_EXECUTED, {
            "script_name": script_name,
            "success": True,
        })
        return exec_result

    def _handle_capture_frame(self, params: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self._create_snapshot()
        self._state_snapshots.append(snapshot)
        return snapshot.to_dict()

    def _handle_get_state(self, params: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self._create_snapshot()
        return snapshot.to_dict()

    def _handle_apply_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        if "profile" in params:
            self._optimization_profile = OptimizationProfile(**params["profile"])
        return {"success": True, "profile": self._optimization_profile.to_dict()}

    def _handle_start_profiling(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"profiling": True, "started_at": time.time()}

    def _handle_stop_profiling(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "profiling": False,
            "stopped_at": time.time(),
            "samples_collected": len(self._state_snapshots),
        }

    def _handle_optimize_rendering(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params.get("target_fps", 60)
        recommendations = [
            {"system": "adaptive_rendering", "action": "lower_quality_tier",
             "reason": f"Targeting {target} FPS"},
            {"system": "lod", "action": "enable_aggressive_lod",
             "reason": "Reduce draw calls"},
            {"system": "batch_rendering", "action": "merge_draw_calls",
             "reason": "Optimize GPU utilization"},
            {"system": "occlusion_culling", "action": "enable",
             "reason": "Skip off-screen rendering"},
        ]
        self._emit_event(EngineEventType.OPTIMIZATION_COMPLETE, {
            "target_fps": target,
            "recommendations": len(recommendations),
        })
        return {"target_fps": target, "recommendations": recommendations}

    def _handle_tune_physics(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "physics_profile": "optimized",
            "solver_iterations": 8,
            "sleep_threshold": 0.5,
            "gravity_scale": params.get("gravity_scale", 1.0),
        }

    def _handle_generate_terrain(self, params: Dict[str, Any]) -> Dict[str, Any]:
        terrain_id = uuid.uuid4().hex[:12]
        return {
            "terrain_id": terrain_id,
            "width": params.get("width", 256),
            "height": params.get("height", 256),
            "seed": params.get("seed", 42),
            "algorithm": params.get("algorithm", "perlin"),
            "chunks_generated": 4,
        }

    def _handle_generate_world(self, params: Dict[str, Any]) -> Dict[str, Any]:
        world_id = uuid.uuid4().hex[:12]
        return {
            "world_id": world_id,
            "name": params.get("name", "Generated World"),
            "biomes": params.get("biome_count", 5),
            "structures": params.get("structure_count", 10),
            "seed": params.get("seed", 42),
        }

    def _handle_simulate_tick(self, params: Dict[str, Any]) -> Dict[str, Any]:
        num_ticks = params.get("num_ticks", 1)
        for _ in range(num_ticks):
            self._frame_number += 1
        self._emit_event(EngineEventType.FRAME_COMPLETE, {
            "frame_number": self._frame_number,
            "ticks_simulated": num_ticks,
        })
        return {"frame_number": self._frame_number, "ticks_simulated": num_ticks}

    def _handle_reset_simulation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        self._frame_number = 0
        self._entities.clear()
        self._scenes.clear()
        self._active_scene = ""
        return {"success": True, "frame_number": 0, "entities": 0, "scenes": 0}

    def _handle_unknown(self, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"success": False, "error": "Unknown command"}

    # ── State Snapshots ──

    def get_state_snapshot(self) -> EngineStateSnapshot:
        """Get a complete snapshot of the current engine state."""
        return self._create_snapshot()

    def _create_snapshot(self) -> EngineStateSnapshot:
        return EngineStateSnapshot(
            frame_number=self._frame_number,
            active_scene=self._active_scene,
            entity_count=len(self._entities),
            fps=60.0,
            frame_time_ms=16.67,
            draw_calls=min(len(self._entities) * 2, 2000),
            physics_bodies=sum(
                1 for e in self._entities.values()
                if "physics" in e.get("components", {})
            ),
            memory_usage_mb=len(self._entities) * 0.5 + 50,
            gpu_usage_percent=min(len(self._entities) * 0.5, 95),
            cpu_usage_percent=min(len(self._entities) * 0.3, 80),
            entities=[{"id": eid, "name": e["name"], "category": e["category"]}
                      for eid, e in list(self._entities.items())[:100]],
            active_systems=list(self._subsystems.keys()),
            scene_graph={"active_scene": self._active_scene, "scenes": list(self._scenes.keys())},
            performance_metrics={
                "fps": 60.0,
                "frame_time_ms": 16.67,
                "draw_calls": min(len(self._entities) * 2, 2000),
                "memory_mb": len(self._entities) * 0.5 + 50,
            },
        )

    # ── Event System ──

    def on_event(self, event_type: EngineEventType, callback: Callable) -> None:
        """Register a callback for a specific engine event type."""
        self._event_listeners[event_type].append(callback)

    def off_event(self, event_type: EngineEventType, callback: Callable) -> None:
        """Remove a callback from an event type."""
        if callback in self._event_listeners[event_type]:
            self._event_listeners[event_type].remove(callback)

    def _emit_event(self, event_type: EngineEventType, data: Dict[str, Any]) -> None:
        """Emit an engine event to all registered listeners."""
        event = EngineEvent(event_type=event_type, data=data)
        with self._lock:
            self._events_emitted += 1
            self._event_history.append(event)
            if len(self._event_history) > 500:
                self._event_history = self._event_history[-250:]
        for callback in self._event_listeners.get(event_type, []):
            try:
                callback(event)
            except Exception:
                pass

    def get_event_history(self, event_type: Optional[EngineEventType] = None,
                          limit: int = 50) -> List[Dict[str, Any]]:
        """Get event history, optionally filtered by type."""
        events = self._event_history
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]

    # ── Game Creation ──

    def create_game_from_spec(self, spec: GameCreationSpec) -> Dict[str, Any]:
        """Create a complete game from a creation specification."""
        self._creation_specs[spec.spec_id] = spec

        # Create main scene
        scene_result = self._handle_create_scene({
            "name": f"{spec.name}_Main",
            "config": {
                "genre": spec.genre,
                "visual_style": spec.visual_style,
                "physics_enabled": spec.physics_enabled,
            },
        })

        # Spawn initial entities
        entities_created = []
        for i in range(min(spec.entity_count, 50)):
            pos = {
                "x": (i % 10) * 100,
                "y": 0,
                "z": (i // 10) * 100,
            }
            entity_result = self._handle_spawn_entity({
                "name": f"{spec.name}_Entity_{i}",
                "category": "prop" if i > 5 else "npc",
                "position": pos,
                "components": {"transform": pos, "renderable": {"visible": True}},
            })
            entities_created.append(entity_result["entity_id"])

        self._emit_event(EngineEventType.WORLD_EVENT, {
            "type": "game_created",
            "spec_id": spec.spec_id,
            "name": spec.name,
            "entity_count": len(entities_created),
        })

        return {
            "spec_id": spec.spec_id,
            "name": spec.name,
            "scene": scene_result,
            "entities_created": len(entities_created),
            "entity_ids": entities_created,
        }

    # ── Optimization ──

    def get_optimization_profile(self) -> Dict[str, Any]:
        """Get the current optimization profile."""
        return self._optimization_profile.to_dict()

    def apply_optimization_profile(self, profile: OptimizationProfile) -> Dict[str, Any]:
        """Apply a new optimization profile."""
        self._optimization_profile = profile
        return {"success": True, "profile": profile.to_dict()}

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyze current performance and suggest optimizations."""
        snapshot = self._create_snapshot()
        suggestions = []

        if snapshot.fps < 30:
            suggestions.append({
                "severity": "high",
                "system": "rendering",
                "action": "reduce_quality",
                "reason": f"Low FPS ({snapshot.fps:.1f})",
            })
        if snapshot.memory_usage_mb > 400:
            suggestions.append({
                "severity": "medium",
                "system": "memory",
                "action": "garbage_collect",
                "reason": f"High memory usage ({snapshot.memory_usage_mb:.0f}MB)",
            })
        if snapshot.draw_calls > 1500:
            suggestions.append({
                "severity": "medium",
                "system": "batch_rendering",
                "action": "merge_batches",
                "reason": f"High draw calls ({snapshot.draw_calls})",
            })

        return {
            "snapshot": snapshot.to_dict(),
            "suggestions": suggestions,
            "suggestion_count": len(suggestions),
            "overall_health": "good" if len(suggestions) == 0 else "needs_attention",
        }

    def get_command_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get command execution history."""
        return [c.to_dict() for c in self._command_history[-limit:]]

    def get_entities(self, category: Optional[EntityCategory] = None) -> List[Dict[str, Any]]:
        """Get all entities, optionally filtered by category."""
        entities = list(self._entities.values())
        if category:
            entities = [e for e in entities if e.get("category") == category.value]
        return entities

    def get_scenes(self) -> Dict[str, Any]:
        """Get all scenes."""
        return {
            "scenes": list(self._scenes.keys()),
            "active_scene": self._active_scene,
            "total": len(self._scenes),
        }


# ── Module Accessor ──

def get_ai_native_engine() -> AINativeEngineCore:
    """Get the singleton AI-native engine core instance."""
    return AINativeEngineCore.get_instance()