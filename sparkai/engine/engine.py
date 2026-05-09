"""
SparkAI Engine - Python Engine Interface

The SparkEngine integrates the ECS World with scene management,
providing a unified game engine API. AI agents interact with
the engine through this interface to create worlds, spawn entities,
and control the simulation loop.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.engine.ecs.world import World
from sparkai.engine.ecs.entity import Entity
from sparkai.engine.ecs.component import Component, ComponentRegistry
from sparkai.engine.ecs.system import System, SystemRegistry
from sparkai.engine.ecs.resource import ResourceManager
from sparkai.engine.game_loop import GameLoop, get_game_loop, ExecutionPhase
from sparkai.engine.signal_system import SignalBus, get_signal_bus
from sparkai.engine.animation_system import AnimationPlayer, get_animation_player
from sparkai.engine.collision_system import CollisionSystem, get_collision_system
from sparkai.engine.input_manager import InputManager, get_input_manager
from sparkai.engine.physics_system import PhysicsSystem, get_physics_system
from sparkai.engine.particle_system import ParticleSystem, get_particle_system
from sparkai.engine.pathfinding_system import PathfindingSystem, get_pathfinding
from sparkai.engine.audio_system import AudioSystem, get_audio_system
from sparkai.engine.state_machine import StateMachine, get_state_machine
from sparkai.engine.resource_manager import ResourceManager as EngineResourceManager, get_resource_manager
from sparkai.engine.behavior_system import BehaviorSystem, get_behavior_system
from sparkai.engine.tilemap_system import TilemapSystem, get_tilemap_system
from sparkai.engine.camera_system import CameraSystem, get_camera_system
from sparkai.engine.serialization import Serializer, get_serializer
from sparkai.engine.ui_system import UISystem, get_ui_system
from sparkai.engine.layer_system import LayerSystem, get_layer_system
from sparkai.engine.profiler import Profiler, get_profiler
from sparkai.engine.event_scripting import EventScriptingSystem, get_event_scripting_system
from sparkai.engine.scene_tree import SceneTree, get_scene_tree
from sparkai.engine.shader_system import ShaderSystem, get_shader_system
from sparkai.engine.variable_system import VariableSystem, get_variable_system
from sparkai.engine.resource_loader import ResourceLoader, get_resource_loader
from sparkai.engine.inventory_system import InventorySystem, get_inventory_system
from sparkai.engine.localization_system import LocalizationSystem, get_localization_system
from sparkai.engine.achievement_system import AchievementSystem, get_achievement_system
from sparkai.engine.cloud_sync import CloudSync, get_cloud_sync
from sparkai.engine.object_pool import ObjectPoolSystem, get_object_pool_system
from sparkai.engine.lighting_system import LightingSystem, get_lighting_system
from sparkai.engine.font_system import FontSystem, get_font_system
from sparkai.engine.plugin_system import PluginSystem, get_plugin_system
from sparkai.engine.effects_system import EffectsSystem, get_effects_system
from sparkai.engine.input_mapping import InputMappingSystem, get_input_mapping
from sparkai.engine.undo_redo_system import UndoRedoSystem, get_undo_redo_system
from sparkai.engine.sprite_sheet import SpriteSheetSystem, get_sprite_sheet_system
from sparkai.engine.tween_system import TweenSystem, get_tween_system
from sparkai.engine.node_path_system import NodePathSystem, get_node_path_system
from sparkai.engine.project_template import ProjectTemplateSystem, get_project_template_system
from sparkai.engine.asset_pipeline import AssetPipeline, get_asset_pipeline
from sparkai.engine.rendering_server import RenderingServer, get_rendering_server
from sparkai.engine.input_event_system import InputEventSystem, get_input_event_system
from sparkai.engine.game_object import GameObject, GameObjectRegistry, get_game_object_registry
from sparkai.engine.scene_manager import SceneManager, get_scene_manager
from sparkai.engine.terrain_system import TerrainSystem, get_terrain_system
from sparkai.engine.save_system import SaveSystem, get_save_system
from sparkai.engine.network_sync import NetworkSync, get_network_sync
from sparkai.engine.behavior_tree import BehaviorTree, get_behavior_tree
from sparkai.engine.math_utils import MathUtils, Vector2, Vector3, Rect2, Transform2D, get_math_utils
from sparkai.engine.gui_system import GUISystem, Widget, Container, Button, Label, get_gui_system
from sparkai.engine.config_manager import ConfigManager, ConfigScope, ConfigEntry, get_config_manager
from sparkai.engine.animation_controller import AnimationController, AnimState, AnimClip, get_animation_controller
from sparkai.engine.debug_draw_system import DebugDrawSystem, DrawCategory, get_debug_draw_system
from sparkai.engine.prefab_system import PrefabSystem, PrefabTemplate, PrefabInstance, get_prefab_system
from sparkai.engine.physics_constraints import PhysicsConstraints, Constraint, ConstraintType, get_physics_constraints
from sparkai.engine.spatial_index import SpatialIndex, SpatialEntry, get_spatial_index
from sparkai.engine.procedural_generation import ProceduralGenerator, TerrainMap, DungeonMap, get_procedural_generator
from sparkai.engine.ragdoll_physics import RagdollSystem, RagdollSkeleton, BoneBody, get_ragdoll_system
from sparkai.engine.game_telemetry import TelemetryEngine, TelemetryEvent, PlaySession, get_telemetry_engine
from sparkai.engine.network_rpc import NetworkRPC, RPCMessage, RPCCallType, get_network_rpc
from sparkai.engine.console_system import ConsoleSystem, CommandDef, ConsoleLogLevel, get_console_system
from sparkai.engine.input_recorder import InputRecorder, RecordingSession, InputEventType, get_input_recorder
from sparkai.engine.collision_layers import CollisionLayerManager, LayerFlag, LayerMask, get_collision_layer_manager


class SparkEngine:
    """
    Core game engine for SparkLabs.

    Manages ECS worlds, scenes, and the game loop.
    Provides the primary API for AI agents to interact with
    the game simulation.
    """

    _instance: Optional["SparkEngine"] = None

    def __init__(self):
        self._worlds: Dict[str, World] = {}
        self._active_world_id: Optional[str] = None
        self._resource_manager: ResourceManager = ResourceManager()
        self._running: bool = False
        self._delta_time: float = 0.016
        self._frame_count: int = 0
        self._scenes: Dict[str, "Scene"] = {}
        self._active_scene_id: Optional[str] = None
        self._game_loop: GameLoop = get_game_loop()
        self._signal_bus: SignalBus = get_signal_bus()
        self._animation_player: AnimationPlayer = get_animation_player()
        self._collision_system: CollisionSystem = get_collision_system()
        self._input_manager: InputManager = get_input_manager()
        self._physics_system: PhysicsSystem = get_physics_system()
        self._particle_system: ParticleSystem = get_particle_system()
        self._pathfinding: PathfindingSystem = get_pathfinding()
        self._audio_system: AudioSystem = get_audio_system()
        self._state_machine: StateMachine = get_state_machine()
        self._engine_resource_manager: EngineResourceManager = get_resource_manager()
        self._behavior_system: BehaviorSystem = get_behavior_system()
        self._tilemap_system: TilemapSystem = get_tilemap_system()
        self._camera_system: CameraSystem = get_camera_system()
        self._serializer: Serializer = get_serializer()
        self._ui_system: UISystem = get_ui_system()
        self._layer_system: LayerSystem = get_layer_system()
        self._profiler: Profiler = get_profiler()
        self._event_scripting: EventScriptingSystem = get_event_scripting_system()
        self._scene_tree: SceneTree = get_scene_tree()
        self._shader_system: ShaderSystem = get_shader_system()
        self._variable_system: VariableSystem = get_variable_system()
        self._resource_loader: ResourceLoader = get_resource_loader()
        self._inventory_system: InventorySystem = get_inventory_system()
        self._localization_system: LocalizationSystem = get_localization_system()
        self._achievement_system: AchievementSystem = get_achievement_system()
        self._cloud_sync: CloudSync = get_cloud_sync()
        self._object_pool_system: ObjectPoolSystem = get_object_pool_system()
        self._lighting_system: LightingSystem = get_lighting_system()
        self._font_system: FontSystem = get_font_system()
        self._plugin_system: PluginSystem = get_plugin_system()
        self._effects_system: EffectsSystem = get_effects_system()
        self._input_mapping: InputMappingSystem = get_input_mapping()
        self._undo_redo_system: UndoRedoSystem = get_undo_redo_system()
        self._sprite_sheet: SpriteSheetSystem = get_sprite_sheet_system()
        self._tween_system: TweenSystem = get_tween_system()
        self._node_path_system: NodePathSystem = get_node_path_system()
        self._project_template_system: ProjectTemplateSystem = get_project_template_system()
        self._asset_pipeline: AssetPipeline = get_asset_pipeline()
        self._rendering_server: RenderingServer = get_rendering_server()
        self._input_event_system: InputEventSystem = get_input_event_system()
        self._game_object_registry: GameObjectRegistry = get_game_object_registry()
        self._scene_manager: SceneManager = get_scene_manager()
        self._terrain_system: TerrainSystem = get_terrain_system()
        self._save_system: SaveSystem = get_save_system()
        self._network_sync: NetworkSync = get_network_sync()
        self._behavior_tree: BehaviorTree = get_behavior_tree()
        self._math_utils: MathUtils = get_math_utils()
        self._gui_system: GUISystem = get_gui_system()
        self._config_manager: ConfigManager = get_config_manager()
        self._animation_controller: AnimationController = get_animation_controller()
        self._debug_draw_system: DebugDrawSystem = get_debug_draw_system()
        self._prefab_system: PrefabSystem = get_prefab_system()
        self._physics_constraints: PhysicsConstraints = get_physics_constraints()
        self._spatial_index: SpatialIndex = get_spatial_index()
        self._procedural_generator: ProceduralGenerator = get_procedural_generator()
        self._ragdoll_system: RagdollSystem = get_ragdoll_system()
        self._telemetry_engine: TelemetryEngine = get_telemetry_engine()
        self._network_rpc: NetworkRPC = get_network_rpc()
        self._console_system: ConsoleSystem = get_console_system()
        self._input_recorder: InputRecorder = get_input_recorder()
        self._collision_layer_manager: CollisionLayerManager = get_collision_layer_manager()
        self._wire_engine_phases()

    def _wire_engine_phases(self) -> None:
        self._game_loop.register_phase_handler(
            ExecutionPhase.INPUT,
            lambda dt, stats: self._input_manager.post_update(),
        )
        self._game_loop.register_phase_handler(
            ExecutionPhase.INPUT,
            lambda dt, stats: self._input_event_system.dispatch_events(dt),
        )
        self._game_loop.register_phase_handler(
            ExecutionPhase.STEP,
            lambda dt, stats: self._step_simulation(dt),
        )

    def _step_simulation(self, dt: float) -> None:
        self._rendering_server.begin_frame()
        self._physics_system.step(dt)
        self._particle_system.update(dt)
        self._tween_system.update(dt)
        self._behavior_system.step_pre(dt)
        self._game_object_registry.update_all(dt)
        self._tick_worlds(dt)
        self._behavior_system.step_post(dt)
        self._behavior_tree.tick_all()
        self._animation_controller.update(dt)
        self._physics_constraints.step(dt)
        self._ragdoll_system.step(dt)
        self._network_sync.tick()
        self._rendering_server.end_frame()
        self._game_loop.register_phase_handler(
            ExecutionPhase.POST_STEP,
            lambda dt, stats: self._update_collision_and_animation(dt),
        )
        self._game_loop.register_phase_handler(
            ExecutionPhase.CLEANUP,
            lambda dt, stats: self._signal_bus.flush_deferred(),
        )

    def _tick_worlds(self, dt: float) -> None:
        for world in self._worlds.values():
            world.tick(dt)
        scene = self.get_active_scene()
        if scene:
            scene.update(dt)

    def _update_collision_and_animation(self, dt: float) -> None:
        self._collision_system.update()
        self._animation_player.update(dt)

    @classmethod
    def get_instance(cls) -> "SparkEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_world(self, name: str = "World") -> World:
        world = World(name=name)
        self._worlds[world.id] = world
        if not self._active_world_id:
            self._active_world_id = world.id
        return world

    def get_world(self, world_id: str) -> Optional[World]:
        return self._worlds.get(world_id)

    def get_active_world(self) -> Optional[World]:
        if self._active_world_id:
            return self._worlds.get(self._active_world_id)
        return None

    def set_active_world(self, world_id: str) -> bool:
        if world_id in self._worlds:
            self._active_world_id = world_id
            return True
        return False

    def list_worlds(self) -> List[Dict[str, Any]]:
        return [w.get_status() for w in self._worlds.values()]

    def delete_world(self, world_id: str) -> bool:
        if world_id in self._worlds:
            del self._worlds[world_id]
            if self._active_world_id == world_id:
                self._active_world_id = next(iter(self._worlds), None)
            return True
        return False

    @property
    def resources(self) -> ResourceManager:
        return self._resource_manager

    def create_scene(self, name: str = "Untitled Scene") -> "Scene":
        scene = Scene(name=name)
        self._scenes[scene.id] = scene
        if not self._active_scene_id:
            self._active_scene_id = scene.id
        return scene

    def get_scene(self, scene_id: str) -> Optional["Scene"]:
        return self._scenes.get(scene_id)

    def get_active_scene(self) -> Optional["Scene"]:
        if self._active_scene_id:
            return self._scenes.get(self._active_scene_id)
        return None

    def set_active_scene(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            self._active_scene_id = scene_id
            return True
        return False

    def list_scenes(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._scenes.values()]

    def delete_scene(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            if self._active_scene_id == scene_id:
                self._active_scene_id = next(iter(self._scenes), None)
            return True
        return False

    def start(self) -> None:
        self._running = True
        for world in self._worlds.values():
            world.start()
        self._game_loop.start()

    def stop(self) -> None:
        self._running = False
        for world in self._worlds.values():
            world.stop()
        self._game_loop.stop()

    def update(self, delta_time: Optional[float] = None) -> None:
        if not self._running:
            return
        self._delta_time = delta_time or self._delta_time
        self._frame_count += 1
        stats = self._game_loop.tick()
        if stats:
            self._frame_count = stats.frame_count

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "world_count": len(self._worlds),
            "scene_count": len(self._scenes),
            "active_world": self._active_world_id,
            "active_scene": self._active_scene_id,
            "delta_time": self._delta_time,
            "component_types": ComponentRegistry.list_types(),
            "system_types": SystemRegistry.list_types(),
            "resource_count": self._resource_manager.count,
            "game_loop": self._game_loop.get_statistics(),
            "signal_bus_connections": self._signal_bus.get_connection_count(),
            "animation_state": self._animation_player.get_status(),
            "collision_colliders": len(self._collision_system._colliders),
            "input_snapshot": self._input_manager.get_snapshot(),
            "physics": self._physics_system.get_stats(),
            "particles": self._particle_system.get_stats(),
            "pathfinding": self._pathfinding.get_stats(),
            "audio": self._audio_system.get_stats(),
            "state_machine": self._state_machine.get_stats(),
            "resources": self._engine_resource_manager.get_stats(),
            "behaviors": self._behavior_system.get_stats(),
            "tilemap": self._tilemap_system.get_stats(),
            "camera": self._camera_system.get_stats(),
            "serializer": self._serializer.get_stats(),
            "ui": self._ui_system.get_stats(),
            "layer": self._layer_system.get_stats(),
            "profiler": self._profiler.get_snapshot(),
            "event_scripting": self._event_scripting.get_stats(),
            "scene_tree": self._scene_tree.get_stats(),
            "shader_system": self._shader_system.get_stats(),
            "variable_system": self._variable_system.get_stats(),
            "resource_loader": self._resource_loader.get_stats(),
            "inventory_system": self._inventory_system.get_stats(),
            "localization_system": self._localization_system.get_stats(),
            "achievement_system": self._achievement_system.get_stats(),
            "cloud_sync": self._cloud_sync.get_stats(),
            "object_pool": self._object_pool_system.get_stats(),
            "lighting_system": self._lighting_system.get_stats(),
            "font_system": self._font_system.get_stats(),
            "plugin_system": self._plugin_system.get_stats(),
            "effects_system": self._effects_system.get_stats(),
            "input_mapping": self._input_mapping.get_stats(),
            "undo_redo_system": self._undo_redo_system.get_stats(),
            "sprite_sheet": self._sprite_sheet.get_stats(),
            "tween_system": self._tween_system.get_stats(),
            "node_path_system": self._node_path_system.get_stats(),
            "project_template_system": self._project_template_system.get_stats(),
            "asset_pipeline": self._asset_pipeline.get_stats(),
            "rendering_server": self._rendering_server.get_stats(),
            "input_event_system": self._input_event_system.get_stats(),
            "game_object_registry": self._game_object_registry.get_stats(),
            "scene_manager": self._scene_manager.get_stats(),
            "terrain_system": self._terrain_system.get_stats(),
            "save_system": self._save_system.get_stats(),
            "network_sync": self._network_sync.get_stats(),
            "behavior_tree": self._behavior_tree.get_stats(),
            "math_utils": self._math_utils.get_stats(),
            "gui_system": self._gui_system.get_stats(),
            "config_manager": self._config_manager.get_stats(),
            "animation_controller": self._animation_controller.get_stats(),
            "debug_draw_system": self._debug_draw_system.get_stats(),
            "prefab_system": self._prefab_system.get_stats(),
            "physics_constraints": self._physics_constraints.get_stats(),
            "spatial_index": self._spatial_index.get_stats(),
            "procedural_generator": self._procedural_generator.get_stats(),
            "ragdoll_system": self._ragdoll_system.get_stats(),
            "telemetry_engine": self._telemetry_engine.get_stats(),
            "network_rpc": self._network_rpc.get_stats(),
            "console_system": self._console_system.get_stats(),
            "input_recorder": self._input_recorder.get_stats(),
            "collision_layer_manager": self._collision_layer_manager.get_stats(),
        }

    @property
    def game_loop(self) -> GameLoop:
        return self._game_loop

    @property
    def signal_bus(self) -> SignalBus:
        return self._signal_bus

    @property
    def animation_player(self) -> AnimationPlayer:
        return self._animation_player

    @property
    def collision_system(self) -> CollisionSystem:
        return self._collision_system

    @property
    def input_manager(self) -> InputManager:
        return self._input_manager

    @property
    def physics_system(self) -> PhysicsSystem:
        return self._physics_system

    @property
    def particle_system(self) -> ParticleSystem:
        return self._particle_system

    @property
    def pathfinding(self) -> PathfindingSystem:
        return self._pathfinding

    @property
    def audio_system(self) -> AudioSystem:
        return self._audio_system

    @property
    def state_machine(self) -> StateMachine:
        return self._state_machine

    @property
    def engine_resource_manager(self) -> EngineResourceManager:
        return self._engine_resource_manager

    @property
    def behavior_system(self) -> BehaviorSystem:
        return self._behavior_system

    @property
    def tilemap_system(self) -> TilemapSystem:
        return self._tilemap_system

    @property
    def camera_system(self) -> CameraSystem:
        return self._camera_system

    @property
    def serializer(self) -> Serializer:
        return self._serializer

    @property
    def ui_system(self) -> UISystem:
        return self._ui_system

    @property
    def layer_system(self) -> LayerSystem:
        return self._layer_system

    @property
    def profiler(self) -> Profiler:
        return self._profiler

    @property
    def event_scripting(self) -> EventScriptingSystem:
        return self._event_scripting

    @property
    def scene_tree(self) -> SceneTree:
        return self._scene_tree

    @property
    def shader_system(self) -> ShaderSystem:
        return self._shader_system

    @property
    def variable_system(self) -> VariableSystem:
        return self._variable_system

    @property
    def resource_loader(self) -> ResourceLoader:
        return self._resource_loader

    @property
    def inventory_system(self) -> InventorySystem:
        return self._inventory_system

    @property
    def localization_system(self) -> LocalizationSystem:
        return self._localization_system

    @property
    def achievement_system(self) -> AchievementSystem:
        return self._achievement_system

    @property
    def cloud_sync(self) -> CloudSync:
        return self._cloud_sync

    @property
    def object_pool_system(self) -> ObjectPoolSystem:
        return self._object_pool_system

    @property
    def lighting_system(self) -> LightingSystem:
        return self._lighting_system

    @property
    def font_system(self) -> FontSystem:
        return self._font_system

    @property
    def plugin_system(self) -> PluginSystem:
        return self._plugin_system

    @property
    def tween_system(self) -> TweenSystem:
        return self._tween_system

    @property
    def node_path_system(self) -> NodePathSystem:
        return self._node_path_system

    @property
    def project_template_system(self) -> ProjectTemplateSystem:
        return self._project_template_system

    @property
    def asset_pipeline(self) -> AssetPipeline:
        return self._asset_pipeline

    @property
    def rendering_server(self) -> RenderingServer:
        return self._rendering_server

    @property
    def input_event_system(self) -> InputEventSystem:
        return self._input_event_system

    @property
    def game_object_registry(self) -> GameObjectRegistry:
        return self._game_object_registry

    @property
    def scene_manager(self) -> SceneManager:
        return self._scene_manager

    @property
    def terrain_system(self) -> TerrainSystem:
        return self._terrain_system

    @property
    def save_system(self) -> SaveSystem:
        return self._save_system

    @property
    def network_sync(self) -> NetworkSync:
        return self._network_sync

    @property
    def behavior_tree(self) -> BehaviorTree:
        return self._behavior_tree

    @property
    def math_utils(self) -> MathUtils:
        return self._math_utils

    @property
    def gui_system(self) -> GUISystem:
        return self._gui_system

    @property
    def config_manager(self) -> ConfigManager:
        return self._config_manager

    @property
    def animation_controller(self) -> AnimationController:
        return self._animation_controller

    @property
    def debug_draw_system(self) -> DebugDrawSystem:
        return self._debug_draw_system

    @property
    def prefab_system(self) -> PrefabSystem:
        return self._prefab_system

    @property
    def physics_constraints(self) -> PhysicsConstraints:
        return self._physics_constraints

    @property
    def spatial_index(self) -> SpatialIndex:
        return self._spatial_index

    @property
    def procedural_generator(self) -> ProceduralGenerator:
        return self._procedural_generator

    @property
    def ragdoll_system(self) -> RagdollSystem:
        return self._ragdoll_system

    @property
    def telemetry_engine(self) -> TelemetryEngine:
        return self._telemetry_engine

    @property
    def network_rpc(self) -> NetworkRPC:
        return self._network_rpc

    @property
    def console_system(self) -> ConsoleSystem:
        return self._console_system

    @property
    def input_recorder(self) -> InputRecorder:
        return self._input_recorder

    @property
    def collision_layer_manager(self) -> CollisionLayerManager:
        return self._collision_layer_manager


@dataclass
class Scene:
    name: str = "Untitled Scene"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entities: Dict[str, "SceneEntity"] = field(default_factory=dict)

    def create_entity(self, name: str = "Entity", **kwargs) -> "SceneEntity":
        entity = SceneEntity(name=name, scene_id=self.id, **kwargs)
        self.entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional["SceneEntity"]:
        return self.entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional["SceneEntity"]:
        for entity in self.entities.values():
            if entity.name == name:
                return entity
        return None

    def find_entities_by_tag(self, tag: str) -> List["SceneEntity"]:
        return [e for e in self.entities.values() if tag in e.tags]

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def update(self, delta_time: float) -> None:
        for entity in self.entities.values():
            entity.update(delta_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_count": len(self.entities),
            "entities": [e.to_dict() for e in self.entities.values()],
        }


@dataclass
class SceneEntity:
    name: str = "Entity"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scene_id: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    tags: List[str] = field(default_factory=list)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, component_type: str, data: Optional[Dict] = None) -> None:
        self.components[component_type] = data or {}

    def remove_component(self, component_type: str) -> bool:
        if component_type in self.components:
            del self.components[component_type]
            return True
        return False

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = [x, y, z]

    def set_rotation(self, x: float, y: float, z: float) -> None:
        self.rotation = [x, y, z]

    def set_scale(self, x: float, y: float, z: float) -> None:
        self.scale = [x, y, z]

    def update(self, delta_time: float) -> None:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "tags": self.tags,
            "components": self.components,
            "properties": self.properties,
        }
