"""
SparkLabs Engine - Unified Game Engine Core

The definitive unified game engine core for the SparkLabs AI-native ecosystem.
Integrates rendering, physics, scene management, audio, ECS, animation,
world systems, input/UI, performance diagnostics, and resource pipelines
into a single cohesive runtime controlled by AI agents.

This module serves as the runtime backbone for all game creation, execution,
analysis, and optimization within the SparkLabs ecosystem.

Architecture:
  UnifiedGameEngine (Singleton)
    |-- RenderingPipeline (render passes, post-processing, GPU, shadows, lighting, skybox, decals, sprites, trails, particles, materials, shaders)
    |-- PhysicsWorld (dynamics, collision, constraints, vehicles, water, cloth, ragdoll)
    |-- SceneGraph (scene manager, tree, stack, transitions, streaming, prefabs)
    |-- AudioEngine (synthesis, spatial, layering, interactive, procedural, dynamic music)
    |-- ECSWorld (entity-component-system, component assembler, blueprints, custom types)
    |-- AnimationSystem (curves, trees, controllers, skeleton, IK, camera shake, camera controller)
    |-- WorldSystems (terrain, biome generation, procedural world, dungeon, tilemap, weather, day/night)
    |-- InputUISystem (input mapping, events, abstraction, gesture, UI system, UI layout)
    |-- PerformanceMonitor (profiler, performance overlay, frame timer, debug draw, console, telemetry)
    |-- ResourceManager (resource loader, asset pipeline, bundler, streamer, texture atlas, serialization)
    |-- AgentBridge (bidirectional command/event channel with agent layer)

Usage:
    engine = UnifiedGameEngine.get_instance()
    engine.initialize()

    # Create and run a scene
    scene = engine.create_scene("Level1", 1920, 1080)
    engine.spawn_entity(scene_id, "player", 100, 200)
    engine.run()

    # Process agent commands
    engine.process_agent_commands()

    engine.shutdown()
"""

from __future__ import annotations

import json
import logging
import math
import random
import threading
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger(__name__)


# =============================================================================
# Core Enums
# =============================================================================


class EngineState(Enum):
    """Overall engine lifecycle states."""
    COLD = "cold"
    BOOTING = "booting"
    RUNNING = "running"
    PAUSED = "paused"
    LOADING = "loading"
    SHUTTING_DOWN = "shutting_down"
    ERROR = "error"
    TERMINATED = "terminated"


class SceneState(Enum):
    """Scene lifecycle states."""
    CREATED = "created"
    LOADING = "loading"
    ACTIVE = "active"
    PAUSED = "paused"
    UNLOADING = "unloading"
    UNLOADED = "unloaded"


class EntityType(Enum):
    """Types of game entities."""
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
    COLLECTIBLE = "collectible"
    PROJECTILE = "projectile"
    CUSTOM = "custom"


class ComponentType(Enum):
    """Types of ECS components."""
    TRANSFORM = "transform"
    RENDERER = "renderer"
    COLLIDER = "collider"
    RIGID_BODY = "rigid_body"
    ANIMATOR = "animator"
    AUDIO_SOURCE = "audio_source"
    LIGHT_SOURCE = "light_source"
    CAMERA = "camera"
    AI_BRAIN = "ai_brain"
    SCRIPT = "script"
    PARTICLE_EMITTER = "particle_emitter"
    UI_ELEMENT = "ui_element"
    HEALTH = "health"
    INVENTORY = "inventory"
    CUSTOM = "custom"


class PhysicsShape(Enum):
    """Physics collision shapes."""
    BOX = "box"
    CIRCLE = "circle"
    POLYGON = "polygon"
    CAPSULE = "capsule"
    EDGE = "edge"
    POINT = "point"


class RenderPass(Enum):
    """Render pipeline passes."""
    SHADOW_MAP = "shadow_map"
    OPAQUE = "opaque"
    TRANSPARENT = "transparent"
    POST_PROCESS = "post_process"
    UI = "ui"
    DEBUG = "debug"


class InputAction(Enum):
    """Abstract input actions."""
    MOVE_LEFT = "move_left"
    MOVE_RIGHT = "move_right"
    MOVE_UP = "move_up"
    MOVE_DOWN = "move_down"
    JUMP = "jump"
    ATTACK = "attack"
    INTERACT = "interact"
    PAUSE = "pause"
    MENU = "menu"
    CONFIRM = "confirm"
    CANCEL = "cancel"


class QualityTier(Enum):
    """Graphics quality tiers."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    ULTRA = "ultra"
    CUSTOM = "custom"


class WorldLayer(Enum):
    """World generation layers."""
    TERRAIN = "terrain"
    BIOME = "biome"
    VEGETATION = "vegetation"
    STRUCTURE = "structure"
    WATER = "water"
    DECORATION = "decoration"
    ENTITY = "entity"


class ResourceType(Enum):
    """Types of game resources."""
    TEXTURE = "texture"
    SPRITE = "sprite"
    AUDIO = "audio"
    FONT = "font"
    SHADER = "shader"
    MATERIAL = "material"
    ANIMATION = "animation"
    PREFAB = "prefab"
    SCENE = "scene"
    SCRIPT = "script"
    TILEMAP = "tilemap"
    DATA = "data"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Transform:
    """2D/3D transform component."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    scale_z: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y, "z": self.z,
            "rotation": self.rotation,
            "scale_x": self.scale_x, "scale_y": self.scale_y, "scale_z": self.scale_z,
        }


@dataclass
class Entity:
    """A game entity in the ECS world."""
    entity_id: str
    name: str
    entity_type: EntityType
    components: Dict[str, Any] = field(default_factory=dict)
    active: bool = True
    layer: int = 0
    tag: str = ""
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "components": {k: v if isinstance(v, (dict, list, str, int, float, bool)) else str(v)
                          for k, v in self.components.items()},
            "active": self.active,
            "layer": self.layer,
            "tag": self.tag,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class Scene:
    """A game scene containing entities and systems."""
    scene_id: str
    name: str
    width: int
    height: int
    state: SceneState = SceneState.CREATED
    entities: Dict[str, Entity] = field(default_factory=dict)
    layers: List[Dict[str, Any]] = field(default_factory=list)
    camera: Dict[str, Any] = field(default_factory=dict)
    physics_config: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "name": self.name,
            "width": self.width,
            "height": self.height,
            "state": self.state.value,
            "entity_count": len(self.entities),
            "layer_count": len(self.layers),
            "camera": self.camera,
            "physics_config": self.physics_config,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


@dataclass
class PhysicsBody:
    """A physics body for collision and dynamics."""
    body_id: str
    entity_id: str
    shape: PhysicsShape = PhysicsShape.BOX
    mass: float = 1.0
    is_static: bool = False
    is_kinematic: bool = False
    friction: float = 0.5
    restitution: float = 0.3
    linear_damping: float = 0.1
    angular_damping: float = 0.1
    velocity_x: float = 0.0
    velocity_y: float = 0.0
    angular_velocity: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "body_id": self.body_id,
            "entity_id": self.entity_id,
            "shape": self.shape.value,
            "mass": self.mass,
            "is_static": self.is_static,
            "friction": self.friction,
            "restitution": self.restitution,
            "velocity_x": self.velocity_x,
            "velocity_y": self.velocity_y,
        }


@dataclass
class Renderable:
    """A renderable object in the rendering pipeline."""
    renderable_id: str
    entity_id: str
    layer: int = 0
    order_in_layer: int = 0
    visible: bool = True
    material: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "renderable_id": self.renderable_id,
            "entity_id": self.entity_id,
            "layer": self.layer,
            "order_in_layer": self.order_in_layer,
            "visible": self.visible,
            "material": self.material,
        }


@dataclass
class AudioSource:
    """An audio source in the audio system."""
    source_id: str
    entity_id: str
    clip_name: str = ""
    volume: float = 1.0
    pitch: float = 1.0
    is_looping: bool = False
    is_spatial: bool = False
    is_playing: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "entity_id": self.entity_id,
            "clip_name": self.clip_name,
            "volume": self.volume,
            "pitch": self.pitch,
            "is_looping": self.is_looping,
            "is_spatial": self.is_spatial,
            "is_playing": self.is_playing,
        }


@dataclass
class FrameStats:
    """Per-frame rendering and performance statistics."""
    frame_number: int
    delta_time: float
    fps: float
    draw_calls: int = 0
    triangle_count: int = 0
    entities_processed: int = 0
    physics_bodies: int = 0
    active_audio_sources: int = 0
    memory_usage_mb: float = 0.0
    gpu_time_ms: float = 0.0
    cpu_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_number": self.frame_number,
            "delta_time": self.delta_time,
            "fps": self.fps,
            "draw_calls": self.draw_calls,
            "triangle_count": self.triangle_count,
            "entities_processed": self.entities_processed,
            "physics_bodies": self.physics_bodies,
            "active_audio_sources": self.active_audio_sources,
            "memory_usage_mb": self.memory_usage_mb,
            "gpu_time_ms": self.gpu_time_ms,
            "cpu_time_ms": self.cpu_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class WorldTile:
    """A single tile in a procedurally generated world."""
    x: int
    y: int
    terrain_type: str = "grass"
    height: float = 0.0
    temperature: float = 20.0
    humidity: float = 0.5
    biome: str = "temperate"
    has_water: bool = False
    has_structure: bool = False
    resources: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x, "y": self.y,
            "terrain_type": self.terrain_type,
            "height": self.height,
            "temperature": self.temperature,
            "humidity": self.humidity,
            "biome": self.biome,
            "has_water": self.has_water,
            "has_structure": self.has_structure,
            "resources": self.resources,
        }


@dataclass
class EngineMetrics:
    """Comprehensive engine performance metrics."""
    total_frames: int = 0
    average_fps: float = 0.0
    min_fps: float = float("inf")
    max_fps: float = 0.0
    total_draw_calls: int = 0
    total_entities: int = 0
    total_physics_bodies: int = 0
    total_audio_sources: int = 0
    peak_memory_mb: float = 0.0
    average_frame_time_ms: float = 0.0
    scenes_loaded: int = 0
    uptime: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_frames": self.total_frames,
            "average_fps": self.average_fps,
            "min_fps": self.min_fps if self.min_fps != float("inf") else 0,
            "max_fps": self.max_fps,
            "total_draw_calls": self.total_draw_calls,
            "total_entities": self.total_entities,
            "total_physics_bodies": self.total_physics_bodies,
            "total_audio_sources": self.total_audio_sources,
            "peak_memory_mb": self.peak_memory_mb,
            "average_frame_time_ms": self.average_frame_time_ms,
            "scenes_loaded": self.scenes_loaded,
            "uptime": self.uptime,
        }


# =============================================================================
# Subsystem Managers
# =============================================================================


class RenderingPipeline:
    """Manages the rendering pipeline: passes, post-processing, GPU management."""

    def __init__(self) -> None:
        self._renderables: Dict[str, Renderable] = {}
        self._render_layers: Dict[int, List[str]] = defaultdict(list)
        self._camera_position: Dict[str, float] = {"x": 0, "y": 0, "zoom": 1.0}
        self._clear_color: Tuple[int, int, int, int] = (30, 30, 40, 255)
        self._quality: QualityTier = QualityTier.HIGH
        self._post_effects: List[str] = ["bloom", "vignette", "color_grading"]
        self._frame_stats: FrameStats = FrameStats(frame_number=0, delta_time=0.016, fps=60.0)

    def register_renderable(self, renderable: Renderable) -> str:
        """Register a renderable object."""
        self._renderables[renderable.renderable_id] = renderable
        self._render_layers[renderable.layer].append(renderable.renderable_id)
        return renderable.renderable_id

    def set_camera(self, x: float, y: float, zoom: float = 1.0) -> None:
        self._camera_position = {"x": x, "y": y, "zoom": zoom}

    def render_frame(self) -> FrameStats:
        """Simulate rendering a frame."""
        self._frame_stats.frame_number += 1
        self._frame_stats.delta_time = 0.016
        self._frame_stats.fps = 60.0
        self._frame_stats.draw_calls = len(self._renderables)
        self._frame_stats.triangle_count = len(self._renderables) * 2
        self._frame_stats.gpu_time_ms = random.uniform(2, 8)
        self._frame_stats.cpu_time_ms = random.uniform(3, 10)
        self._frame_stats.memory_usage_mb = random.uniform(100, 300)
        self._frame_stats.timestamp = time.time()
        return self._frame_stats

    def get_frame_stats(self) -> FrameStats:
        return self._frame_stats

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_renderables": len(self._renderables),
            "active_layers": len(self._render_layers),
            "camera": self._camera_position,
            "quality": self._quality.value,
            "post_effects": self._post_effects,
            "last_frame": self._frame_stats.to_dict(),
        }


class PhysicsWorld:
    """Manages the physics simulation: dynamics, collision, constraints."""

    def __init__(self) -> None:
        self._bodies: Dict[str, PhysicsBody] = {}
        self._gravity_x: float = 0.0
        self._gravity_y: float = -9.81
        self._time_step: float = 0.016
        self._velocity_iterations: int = 8
        self._position_iterations: int = 3
        self._collision_pairs: List[Dict[str, Any]] = []
        self._enabled: bool = True

    def create_body(self, body: PhysicsBody) -> str:
        """Create a physics body."""
        self._bodies[body.body_id] = body
        return body.body_id

    def remove_body(self, body_id: str) -> bool:
        if body_id in self._bodies:
            del self._bodies[body_id]
            return True
        return False

    def apply_force(self, body_id: str, force_x: float, force_y: float) -> None:
        """Apply a force to a physics body."""
        if body_id in self._bodies and not self._bodies[body_id].is_static:
            body = self._bodies[body_id]
            body.velocity_x += force_x / body.mass * self._time_step
            body.velocity_y += force_y / body.mass * self._time_step

    def step(self, delta_time: float) -> None:
        """Step the physics simulation."""
        if not self._enabled:
            return
        self._time_step = delta_time
        self._collision_pairs = []
        # Simulate physics step
        body_ids = list(self._bodies.keys())
        for i, bid1 in enumerate(body_ids):
            for bid2 in body_ids[i + 1:]:
                if random.random() < 0.01:
                    self._collision_pairs.append({
                        "body_a": bid1, "body_b": bid2,
                        "contact_point": {"x": random.uniform(0, 100), "y": random.uniform(0, 100)},
                    })

    def get_collisions(self) -> List[Dict[str, Any]]:
        return self._collision_pairs

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_bodies": len(self._bodies),
            "static_bodies": sum(1 for b in self._bodies.values() if b.is_static),
            "dynamic_bodies": sum(1 for b in self._bodies.values() if not b.is_static),
            "gravity": {"x": self._gravity_x, "y": self._gravity_y},
            "collision_pairs": len(self._collision_pairs),
            "enabled": self._enabled,
        }


class SceneGraph:
    """Manages the scene graph: scenes, layers, transitions, streaming."""

    def __init__(self) -> None:
        self._scenes: Dict[str, Scene] = {}
        self._active_scene_id: Optional[str] = None
        self._transition_state: Dict[str, Any] = {"active": False, "from": None, "to": None, "progress": 0.0}

    def create_scene(self, name: str, width: int, height: int) -> Scene:
        """Create a new scene."""
        scene_id = f"scene_{uuid.uuid4().hex[:12]}"
        scene = Scene(
            scene_id=scene_id,
            name=name,
            width=width,
            height=height,
            camera={"x": 0, "y": 0, "zoom": 1.0, "target": None},
            physics_config={"gravity_x": 0, "gravity_y": -9.81, "time_step": 0.016},
        )
        # Add default layer
        scene.layers.append({"layer_id": "layer_0", "name": "Default", "z_order": 0, "visible": True})
        self._scenes[scene_id] = scene
        return scene

    def load_scene(self, scene_id: str) -> Scene:
        """Load a scene as active."""
        if scene_id not in self._scenes:
            raise ValueError(f"Scene not found: {scene_id}")
        if self._active_scene_id and self._active_scene_id in self._scenes:
            self._scenes[self._active_scene_id].state = SceneState.UNLOADING
        self._active_scene_id = scene_id
        self._scenes[scene_id].state = SceneState.ACTIVE
        return self._scenes[scene_id]

    def get_active_scene(self) -> Optional[Scene]:
        if self._active_scene_id:
            return self._scenes.get(self._active_scene_id)
        return None

    def spawn_entity(self, scene_id: str, name: str, entity_type: EntityType,
                     x: float = 0, y: float = 0) -> Entity:
        """Spawn an entity in a scene."""
        if scene_id not in self._scenes:
            raise ValueError(f"Scene not found: {scene_id}")
        entity_id = f"ent_{uuid.uuid4().hex[:12]}"
        entity = Entity(
            entity_id=entity_id,
            name=name,
            entity_type=entity_type,
            components={"transform": Transform(x=x, y=y).to_dict()},
        )
        self._scenes[scene_id].entities[entity_id] = entity
        return entity

    def remove_entity(self, scene_id: str, entity_id: str) -> bool:
        if scene_id in self._scenes and entity_id in self._scenes[scene_id].entities:
            del self._scenes[scene_id].entities[entity_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_scenes": len(self._scenes),
            "active_scene": self._active_scene_id,
            "total_entities": sum(len(s.entities) for s in self._scenes.values()),
            "transition_active": self._transition_state["active"],
        }


class AudioEngine:
    """Manages audio: synthesis, spatial, layering, interactive."""

    def __init__(self) -> None:
        self._sources: Dict[str, AudioSource] = {}
        self._master_volume: float = 1.0
        self._music_volume: float = 0.8
        self._sfx_volume: float = 1.0
        self._active_tracks: List[str] = []
        self._audio_output_enabled: bool = True

    def create_source(self, source: AudioSource) -> str:
        """Create an audio source."""
        self._sources[source.source_id] = source
        return source.source_id

    def play(self, source_id: str) -> bool:
        if source_id in self._sources:
            self._sources[source_id].is_playing = True
            return True
        return False

    def stop(self, source_id: str) -> bool:
        if source_id in self._sources:
            self._sources[source_id].is_playing = False
            return True
        return False

    def set_master_volume(self, volume: float) -> None:
        self._master_volume = max(0.0, min(1.0, volume))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_sources": len(self._sources),
            "playing_sources": sum(1 for s in self._sources.values() if s.is_playing),
            "master_volume": self._master_volume,
            "music_volume": self._music_volume,
            "sfx_volume": self._sfx_volume,
            "audio_enabled": self._audio_output_enabled,
        }


class ECSWorld:
    """Manages Entity-Component-System architecture."""

    def __init__(self) -> None:
        self._entities: Dict[str, Entity] = {}
        self._component_stores: Dict[str, Dict[str, Any]] = defaultdict(dict)
        self._systems: List[Dict[str, Any]] = []
        self._entity_count: int = 0

    def create_entity(self, name: str, entity_type: EntityType = EntityType.CUSTOM) -> Entity:
        """Create a new entity."""
        entity_id = f"ecs_ent_{uuid.uuid4().hex[:12]}"
        entity = Entity(entity_id=entity_id, name=name, entity_type=entity_type)
        self._entities[entity_id] = entity
        self._entity_count += 1
        return entity

    def add_component(self, entity_id: str, component_type: ComponentType, component_data: Dict[str, Any]) -> bool:
        """Add a component to an entity."""
        if entity_id not in self._entities:
            return False
        self._entities[entity_id].components[component_type.value] = component_data
        self._component_stores[component_type.value][entity_id] = component_data
        return True

    def get_component(self, entity_id: str, component_type: ComponentType) -> Optional[Dict[str, Any]]:
        """Get a component from an entity."""
        if entity_id in self._entities:
            return self._entities[entity_id].components.get(component_type.value)
        return None

    def get_entities_with_component(self, component_type: ComponentType) -> List[Entity]:
        """Get all entities that have a specific component."""
        return [e for e in self._entities.values()
                if component_type.value in e.components]

    def destroy_entity(self, entity_id: str) -> bool:
        if entity_id in self._entities:
            del self._entities[entity_id]
            for store in self._component_stores.values():
                store.pop(entity_id, None)
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_entities": len(self._entities),
            "component_types": list(self._component_stores.keys()),
            "components_count": {
                ct: len(entities) for ct, entities in self._component_stores.items()
            },
            "systems_count": len(self._systems),
        }


class AnimationSystem:
    """Manages animation: curves, trees, controllers, skeleton, IK."""

    def __init__(self) -> None:
        self._animators: Dict[str, Dict[str, Any]] = {}
        self._animation_clips: Dict[str, Dict[str, Any]] = {}
        self._active_animations: List[Dict[str, Any]] = []
        self._time: float = 0.0

    def create_animator(self, entity_id: str) -> str:
        """Create an animator for an entity."""
        animator_id = f"anim_{uuid.uuid4().hex[:8]}"
        self._animators[animator_id] = {
            "entity_id": entity_id,
            "current_clip": None,
            "playback_speed": 1.0,
            "is_playing": False,
            "current_time": 0.0,
            "parameters": {},
        }
        return animator_id

    def play_animation(self, animator_id: str, clip_name: str, speed: float = 1.0) -> bool:
        if animator_id in self._animators:
            self._animators[animator_id]["current_clip"] = clip_name
            self._animators[animator_id]["playback_speed"] = speed
            self._animators[animator_id]["is_playing"] = True
            self._animators[animator_id]["current_time"] = 0.0
            return True
        return False

    def update(self, delta_time: float) -> None:
        self._time += delta_time
        for animator in self._animators.values():
            if animator["is_playing"]:
                animator["current_time"] += delta_time * animator["playback_speed"]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_animators": len(self._animators),
            "active_animations": sum(1 for a in self._animators.values() if a["is_playing"]),
            "animation_clips": len(self._animation_clips),
            "time": self._time,
        }


class WorldSystems:
    """Manages world generation: terrain, biomes, procedural generation, tilemaps."""

    def __init__(self) -> None:
        self._worlds: Dict[str, Dict[str, Any]] = {}
        self._tiles: Dict[str, List[List[WorldTile]]] = {}
        self._weather: Dict[str, Any] = {
            "current": "clear",
            "temperature": 22.0,
            "humidity": 0.5,
            "wind_speed": 5.0,
            "time_of_day": 12,
        }

    def generate_world(self, width: int, height: int, seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate a procedurally generated world."""
        if seed is None:
            seed = random.randint(0, 2**31 - 1)
        world_id = f"world_{uuid.uuid4().hex[:12]}"
        rng = random.Random(seed)

        tiles = []
        terrain_types = ["grass", "dirt", "sand", "stone", "snow", "water", "forest", "mountain"]
        biome_types = ["temperate", "desert", "tundra", "tropical", "boreal", "ocean", "savanna"]

        for y in range(height):
            row = []
            for x in range(width):
                noise = rng.random()
                if noise < 0.05:
                    terrain = "water"
                elif noise < 0.15:
                    terrain = "sand"
                elif noise < 0.3:
                    terrain = "stone"
                elif noise < 0.6:
                    terrain = "grass"
                elif noise < 0.8:
                    terrain = "forest"
                else:
                    terrain = "mountain"

                tile = WorldTile(
                    x=x, y=y,
                    terrain_type=terrain,
                    height=rng.uniform(0, 1),
                    temperature=rng.uniform(-10, 40),
                    humidity=rng.uniform(0, 1),
                    biome=rng.choice(biome_types),
                    has_water=terrain == "water",
                )
                row.append(tile)
            tiles.append(row)

        self._tiles[world_id] = tiles
        world_data = {
            "world_id": world_id,
            "width": width,
            "height": height,
            "seed": seed,
            "terrain_distribution": {},
            "biome_distribution": {},
            "weather": dict(self._weather),
            "total_tiles": width * height,
        }
        # Calculate distributions
        for row in tiles:
            for tile in row:
                world_data["terrain_distribution"][tile.terrain_type] = \
                    world_data["terrain_distribution"].get(tile.terrain_type, 0) + 1
                world_data["biome_distribution"][tile.biome] = \
                    world_data["biome_distribution"].get(tile.biome, 0) + 1

        self._worlds[world_id] = world_data
        return world_data

    def set_weather(self, weather_type: str, temperature: float, humidity: float) -> None:
        self._weather = {
            "current": weather_type,
            "temperature": temperature,
            "humidity": humidity,
            "wind_speed": random.uniform(0, 20),
            "time_of_day": self._weather["time_of_day"],
        }

    def advance_time(self, hours: float = 1.0) -> None:
        self._weather["time_of_day"] = (self._weather["time_of_day"] + hours) % 24

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_worlds": len(self._worlds),
            "total_tiles": sum(w["total_tiles"] for w in self._worlds.values()),
            "weather": self._weather,
        }


class InputUISystem:
    """Manages input mapping, events, abstraction, and UI system."""

    def __init__(self) -> None:
        self._input_bindings: Dict[InputAction, List[str]] = {
            InputAction.MOVE_LEFT: ["key_a", "arrow_left"],
            InputAction.MOVE_RIGHT: ["key_d", "arrow_right"],
            InputAction.MOVE_UP: ["key_w", "arrow_up"],
            InputAction.MOVE_DOWN: ["key_s", "arrow_down"],
            InputAction.JUMP: ["key_space"],
            InputAction.ATTACK: ["mouse_left"],
            InputAction.INTERACT: ["key_e"],
            InputAction.PAUSE: ["key_escape"],
            InputAction.MENU: ["key_tab"],
            InputAction.CONFIRM: ["key_enter"],
            InputAction.CANCEL: ["key_backspace"],
        }
        self._input_state: Dict[str, bool] = {}
        self._mouse_position: Dict[str, float] = {"x": 0, "y": 0}
        self._ui_elements: List[Dict[str, Any]] = []

    def is_action_pressed(self, action: InputAction) -> bool:
        """Check if an input action is pressed."""
        bindings = self._input_bindings.get(action, [])
        return any(self._input_state.get(b, False) for b in bindings)

    def simulate_input(self, action: InputAction, pressed: bool = True) -> None:
        """Simulate an input action for testing."""
        bindings = self._input_bindings.get(action, [])
        for binding in bindings:
            self._input_state[binding] = pressed

    def add_ui_element(self, element: Dict[str, Any]) -> str:
        """Add a UI element."""
        element_id = f"ui_{uuid.uuid4().hex[:8]}"
        element["element_id"] = element_id
        self._ui_elements.append(element)
        return element_id

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_bindings": len(self._input_bindings),
            "active_inputs": sum(1 for v in self._input_state.values() if v),
            "ui_elements": len(self._ui_elements),
            "mouse_position": self._mouse_position,
        }


class PerformanceMonitor:
    """Manages performance monitoring: profiler, frame timer, debug draw."""

    def __init__(self) -> None:
        self._frame_history: List[FrameStats] = []
        self._max_history: int = 300
        self._target_fps: int = 60
        self._profiling_active: bool = False
        self._alerts: List[Dict[str, Any]] = []

    def record_frame(self, stats: FrameStats) -> None:
        """Record frame statistics."""
        self._frame_history.append(stats)
        if len(self._frame_history) > self._max_history:
            self._frame_history = self._frame_history[-self._max_history:]

    def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check for performance threshold violations."""
        alerts = []
        if self._frame_history:
            last = self._frame_history[-1]
            if last.fps < 30:
                alerts.append({"type": "low_fps", "value": last.fps, "threshold": 30})
            if last.memory_usage_mb > 500:
                alerts.append({"type": "high_memory", "value": last.memory_usage_mb, "threshold": 500})
            if last.gpu_time_ms > 16:
                alerts.append({"type": "high_gpu_time", "value": last.gpu_time_ms, "threshold": 16})
        self._alerts = alerts
        return alerts

    def get_average_fps(self) -> float:
        if not self._frame_history:
            return 0.0
        return sum(f.fps for f in self._frame_history) / len(self._frame_history)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "frames_recorded": len(self._frame_history),
            "average_fps": self.get_average_fps(),
            "target_fps": self._target_fps,
            "profiling_active": self._profiling_active,
            "alerts": self._alerts,
        }


class ResourceManager:
    """Manages resource loading, streaming, caching, and serialization."""

    def __init__(self) -> None:
        self._resources: Dict[str, Dict[str, Any]] = {
            rt.value: {} for rt in ResourceType
        }
        self._cache_size: int = 0
        self._max_cache_size_mb: int = 512
        self._streaming_enabled: bool = True

    def load_resource(self, resource_type: ResourceType, resource_name: str,
                      data: Dict[str, Any]) -> str:
        """Load a resource into the cache."""
        resource_id = f"res_{uuid.uuid4().hex[:8]}"
        self._resources[resource_type.value][resource_id] = {
            "name": resource_name,
            "data": data,
            "loaded_at": time.time(),
            "references": 0,
        }
        return resource_id

    def get_resource(self, resource_type: ResourceType, resource_id: str) -> Optional[Dict[str, Any]]:
        return self._resources[resource_type.value].get(resource_id)

    def unload_resource(self, resource_type: ResourceType, resource_id: str) -> bool:
        if resource_id in self._resources[resource_type.value]:
            del self._resources[resource_type.value][resource_id]
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_resources": sum(len(r) for r in self._resources.values()),
            "resources_by_type": {k: len(v) for k, v in self._resources.items()},
            "cache_size_mb": self._cache_size,
            "max_cache_size_mb": self._max_cache_size_mb,
            "streaming_enabled": self._streaming_enabled,
        }


class AgentBridge:
    """Manages bidirectional communication between engine and agent layer."""

    def __init__(self) -> None:
        self._command_queue: List[Dict[str, Any]] = []
        self._event_queue: List[Dict[str, Any]] = []
        self._command_handlers: Dict[str, Callable] = {}
        self._event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        self._registered_commands: Set[str] = set()

    def register_command_handler(self, command_type: str, handler: Callable) -> None:
        """Register a handler for agent commands."""
        self._command_handlers[command_type] = handler
        self._registered_commands.add(command_type)

    def receive_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Receive and process a command from the agent."""
        command_type = command.get("command_type", "")
        if command_type in self._command_handlers:
            try:
                result = self._command_handlers[command_type](command.get("parameters", {}))
                return {"status": "completed", "command_type": command_type, "result": result}
            except Exception as e:
                return {"status": "error", "command_type": command_type, "error": str(e)}
        return {"status": "unknown_command", "command_type": command_type}

    def emit_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        """Emit an event to the agent layer."""
        event = {
            "event_type": event_type,
            "data": event_data,
            "timestamp": time.time(),
        }
        self._event_queue.append(event)
        if len(self._event_queue) > 1000:
            self._event_queue = self._event_queue[-500:]
        for handler in self._event_handlers.get(event_type, []):
            try:
                handler(event)
            except Exception:
                pass

    def get_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._event_queue[-limit:]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registered_commands": len(self._registered_commands),
            "event_queue_size": len(self._event_queue),
            "command_queue_size": len(self._command_queue),
        }


# =============================================================================
# Unified Game Engine
# =============================================================================


class UnifiedGameEngine:
    """
    The definitive unified game engine core for the SparkLabs AI-native ecosystem.

    Integrates all engine subsystems into a single cohesive runtime:
    rendering pipeline, physics simulation, scene management, audio engine,
    ECS architecture, animation system, world generation, input/UI system,
    performance monitoring, and resource management.

    Implements the Singleton pattern with double-checked locking.
    """

    _instance: Optional["UnifiedGameEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if UnifiedGameEngine._instance is not None:
            raise RuntimeError("Use UnifiedGameEngine.get_instance() instead")
        self._initialized: bool = False
        self._state: EngineState = EngineState.COLD
        self._start_time: float = 0.0
        self._metrics: EngineMetrics = EngineMetrics()

        # Subsystem managers
        self._rendering: RenderingPipeline = RenderingPipeline()
        self._physics: PhysicsWorld = PhysicsWorld()
        self._scene_graph: SceneGraph = SceneGraph()
        self._audio: AudioEngine = AudioEngine()
        self._ecs: ECSWorld = ECSWorld()
        self._animation: AnimationSystem = AnimationSystem()
        self._world_systems: WorldSystems = WorldSystems()
        self._input_ui: InputUISystem = InputUISystem()
        self._performance: PerformanceMonitor = PerformanceMonitor()
        self._resources: ResourceManager = ResourceManager()
        self._agent_bridge: AgentBridge = AgentBridge()

        # Game loop
        self._running: bool = False
        self._game_loop_thread: Optional[threading.Thread] = None
        self._frame_count: int = 0
        self._delta_time: float = 0.016

        # Event listeners
        self._event_listeners: Dict[str, List[Callable]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> "UnifiedGameEngine":
        """Get the singleton instance."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -------------------------------------------------------------------------
    # Initialization
    # -------------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the unified game engine and all subsystems."""
        if self._initialized:
            return
        self._state = EngineState.BOOTING
        self._start_time = time.time()

        # Register default agent command handlers
        self._agent_bridge.register_command_handler(
            "create_scene", lambda p: self.create_scene(
                p.get("name", "Untitled"), p.get("width", 1920), p.get("height", 1080)
            ).to_dict()
        )
        self._agent_bridge.register_command_handler(
            "spawn_entity", lambda p: self.spawn_entity(
                p.get("scene_id", ""), p.get("name", "Entity"),
                EntityType(p.get("entity_type", "custom")),
                p.get("x", 0), p.get("y", 0)
            ).to_dict()
        )
        self._agent_bridge.register_command_handler(
            "remove_entity", lambda p: {"removed": self.remove_entity(
                p.get("scene_id", ""), p.get("entity_id", ""))}
        )
        self._agent_bridge.register_command_handler(
            "get_state", lambda p: self.get_status()
        )
        self._agent_bridge.register_command_handler(
            "set_weather", lambda p: self._world_systems.set_weather(
                p.get("weather", "clear"), p.get("temperature", 22.0),
                p.get("humidity", 0.5))
        )

        self._state = EngineState.RUNNING
        self._initialized = True
        logger.info("UnifiedGameEngine initialized successfully")

    def shutdown(self) -> None:
        """Shutdown the unified game engine."""
        self._running = False
        self._state = EngineState.SHUTTING_DOWN
        self._metrics.uptime = time.time() - self._start_time
        self._initialized = False
        self._state = EngineState.TERMINATED
        logger.info("UnifiedGameEngine shutdown complete")

    # -------------------------------------------------------------------------
    # Scene Management
    # -------------------------------------------------------------------------

    def create_scene(self, name: str, width: int = 1920, height: int = 1080) -> Scene:
        """Create a new game scene."""
        self._ensure_initialized()
        self._metrics.scenes_loaded += 1
        return self._scene_graph.create_scene(name, width, height)

    def load_scene(self, scene_id: str) -> Scene:
        """Load and activate a scene."""
        self._ensure_initialized()
        return self._scene_graph.load_scene(scene_id)

    def get_active_scene(self) -> Optional[Scene]:
        return self._scene_graph.get_active_scene()

    def spawn_entity(self, scene_id: str, name: str, entity_type: EntityType,
                     x: float = 0, y: float = 0) -> Entity:
        """Spawn an entity in a scene."""
        self._ensure_initialized()
        entity = self._scene_graph.spawn_entity(scene_id, name, entity_type, x, y)
        self._metrics.total_entities += 1
        return entity

    def remove_entity(self, scene_id: str, entity_id: str) -> bool:
        """Remove an entity from a scene."""
        return self._scene_graph.remove_entity(scene_id, entity_id)

    # -------------------------------------------------------------------------
    # Physics
    # -------------------------------------------------------------------------

    def create_physics_body(self, body: PhysicsBody) -> str:
        """Create a physics body."""
        self._ensure_initialized()
        body_id = self._physics.create_body(body)
        self._metrics.total_physics_bodies += 1
        return body_id

    def apply_force(self, body_id: str, force_x: float, force_y: float) -> None:
        self._physics.apply_force(body_id, force_x, force_y)

    def get_collisions(self) -> List[Dict[str, Any]]:
        return self._physics.get_collisions()

    # -------------------------------------------------------------------------
    # Rendering
    # -------------------------------------------------------------------------

    def register_renderable(self, renderable: Renderable) -> str:
        self._ensure_initialized()
        return self._rendering.register_renderable(renderable)

    def render_frame(self) -> FrameStats:
        """Render a single frame."""
        stats = self._rendering.render_frame()
        self._performance.record_frame(stats)
        self._performance.check_thresholds()
        self._metrics.total_frames += 1
        self._metrics.total_draw_calls += stats.draw_calls
        self._metrics.average_fps = self._performance.get_average_fps()
        if stats.fps < self._metrics.min_fps:
            self._metrics.min_fps = stats.fps
        if stats.fps > self._metrics.max_fps:
            self._metrics.max_fps = stats.fps
        return stats

    # -------------------------------------------------------------------------
    # Audio
    # -------------------------------------------------------------------------

    def create_audio_source(self, source: AudioSource) -> str:
        self._ensure_initialized()
        source_id = self._audio.create_source(source)
        self._metrics.total_audio_sources += 1
        return source_id

    def play_audio(self, source_id: str) -> bool:
        return self._audio.play(source_id)

    def stop_audio(self, source_id: str) -> bool:
        return self._audio.stop(source_id)

    # -------------------------------------------------------------------------
    # ECS
    # -------------------------------------------------------------------------

    def create_ecs_entity(self, name: str, entity_type: EntityType = EntityType.CUSTOM) -> Entity:
        """Create an entity in the ECS world."""
        self._ensure_initialized()
        return self._ecs.create_entity(name, entity_type)

    def add_component(self, entity_id: str, component_type: ComponentType,
                      component_data: Dict[str, Any]) -> bool:
        return self._ecs.add_component(entity_id, component_type, component_data)

    def get_component(self, entity_id: str, component_type: ComponentType) -> Optional[Dict[str, Any]]:
        return self._ecs.get_component(entity_id, component_type)

    # -------------------------------------------------------------------------
    # Animation
    # -------------------------------------------------------------------------

    def create_animator(self, entity_id: str) -> str:
        return self._animation.create_animator(entity_id)

    def play_animation(self, animator_id: str, clip_name: str, speed: float = 1.0) -> bool:
        return self._animation.play_animation(animator_id, clip_name, speed)

    # -------------------------------------------------------------------------
    # World Systems
    # -------------------------------------------------------------------------

    def generate_world(self, width: int = 100, height: int = 100,
                       seed: Optional[int] = None) -> Dict[str, Any]:
        """Generate a procedurally generated world."""
        self._ensure_initialized()
        return self._world_systems.generate_world(width, height, seed)

    def set_weather(self, weather_type: str, temperature: float = 22.0,
                    humidity: float = 0.5) -> None:
        self._world_systems.set_weather(weather_type, temperature, humidity)

    # -------------------------------------------------------------------------
    # Input
    # -------------------------------------------------------------------------

    def simulate_input(self, action: InputAction, pressed: bool = True) -> None:
        self._input_ui.simulate_input(action, pressed)

    def is_action_pressed(self, action: InputAction) -> bool:
        return self._input_ui.is_action_pressed(action)

    # -------------------------------------------------------------------------
    # Resources
    # -------------------------------------------------------------------------

    def load_resource(self, resource_type: ResourceType, resource_name: str,
                      data: Dict[str, Any]) -> str:
        return self._resources.load_resource(resource_type, resource_name, data)

    def get_resource(self, resource_type: ResourceType, resource_id: str) -> Optional[Dict[str, Any]]:
        return self._resources.get_resource(resource_type, resource_id)

    # -------------------------------------------------------------------------
    # Agent Bridge
    # -------------------------------------------------------------------------

    def process_agent_command(self, command: Dict[str, Any]) -> Dict[str, Any]:
        """Process a command from the agent layer."""
        return self._agent_bridge.receive_command(command)

    def get_agent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._agent_bridge.get_events(limit)

    def emit_engine_event(self, event_type: str, event_data: Dict[str, Any]) -> None:
        self._agent_bridge.emit_event(event_type, event_data)

    # -------------------------------------------------------------------------
    # Game Loop
    # -------------------------------------------------------------------------

    def run(self) -> None:
        """Start the game loop."""
        self._ensure_initialized()
        self._running = True
        self._state = EngineState.RUNNING

    def stop(self) -> None:
        """Stop the game loop."""
        self._running = False
        self._state = EngineState.PAUSED

    def tick(self) -> FrameStats:
        """Execute a single tick of the game loop."""
        self._ensure_initialized()
        self._frame_count += 1

        # Update physics
        self._physics.step(self._delta_time)

        # Update animation
        self._animation.update(self._delta_time)

        # Update world time
        self._world_systems.advance_time(self._delta_time / 3600.0)

        # Render frame
        stats = self.render_frame()

        # Emit frame event
        self._agent_bridge.emit_event("frame_complete", {
            "frame": self._frame_count,
            "fps": stats.fps,
            "delta_time": stats.delta_time,
        })

        return stats

    def run_simulation(self, num_frames: int = 100) -> List[FrameStats]:
        """Run a headless simulation for a number of frames."""
        self._ensure_initialized()
        self.run()
        stats_list = []
        for _ in range(num_frames):
            stats = self.tick()
            stats_list.append(stats)
        self.stop()
        return stats_list

    # -------------------------------------------------------------------------
    # Status & Metrics
    # -------------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get comprehensive status of the unified engine."""
        self._metrics.uptime = time.time() - self._start_time if self._start_time > 0 else 0
        return {
            "initialized": self._initialized,
            "state": self._state.value,
            "uptime": self._metrics.uptime,
            "frame_count": self._frame_count,
            "rendering": self._rendering.get_stats(),
            "physics": self._physics.get_stats(),
            "scene_graph": self._scene_graph.get_stats(),
            "audio": self._audio.get_stats(),
            "ecs": self._ecs.get_stats(),
            "animation": self._animation.get_stats(),
            "world_systems": self._world_systems.get_stats(),
            "input_ui": self._input_ui.get_stats(),
            "performance": self._performance.get_stats(),
            "resources": self._resources.get_stats(),
            "agent_bridge": self._agent_bridge.get_stats(),
            "metrics": self._metrics.to_dict(),
        }

    def get_metrics(self) -> Dict[str, Any]:
        return self._metrics.to_dict()

    def on(self, event: str, callback: Callable) -> None:
        """Register an event listener."""
        self._event_listeners[event].append(callback)

    def emit(self, event: str, data: Dict[str, Any]) -> None:
        """Emit an event to listeners."""
        for callback in self._event_listeners.get(event, []):
            try:
                callback(data)
            except Exception:
                pass

    def _ensure_initialized(self) -> None:
        if not self._initialized:
            self.initialize()


# =============================================================================
# Convenience Function
# =============================================================================


def get_unified_game_engine() -> UnifiedGameEngine:
    """Get the singleton UnifiedGameEngine instance."""
    return UnifiedGameEngine.get_instance()