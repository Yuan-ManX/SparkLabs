"""
SparkLabs Engine - Behavior Library

Pre-built behavior/extension system providing modular, reusable
behavior definitions that can be instantiated on game entities to add
movement, combat, AI, physics, visual, and utility logic without
writing custom code for each entity.

Architecture:
  BehaviorLibrary
    |-- BehaviorDefinition (named, categorized behavior with typed parameters)
    |-- BehaviorInstance (entity-bound instance with parameter overrides)
    |-- BehaviorCategory (domain classification for discovery and filtering)
    |-- Built-in Templates (13 curated behaviors for common game logic)

Action Lists:
  Each behavior definition carries three ordered action lists:
    - init_actions: executed once when a behavior instance is first activated
    - update_actions: executed every tick while the behavior is active
    - cleanup_actions: executed when the behavior instance is deactivated

Built-in Behavior Templates:
  - PLATFORMER_CHARACTER (MOVEMENT)    : side-scrolling gravity and jump
  - TOP_DOWN_MOVEMENT    (MOVEMENT)    : 8-directional free movement
  - HEALTH_SYSTEM        (COMBAT)      : HP management with damage/heal/death
  - PATHFINDING          (AI)          : A* path following with waypoints
  - PROJECTILE_SPAWNER   (COMBAT)      : timed projectile creation
  - FOLLOW_TARGET        (AI)          : chase behavior with speed control
  - ROTATE_TOWARD        (VISUAL)      : auto-rotation toward target or direction
  - FLOAT_BOB            (VISUAL)      : decorative sinusoidal vertical motion
  - DAMAGE_ON_COLLISION  (COMBAT)      : apply damage when colliding
  - DESTROY_AFTER_ANIMATION (VISUAL)   : self-destruct after animation completes
  - TILEMAP_COLLIDER     (PHYSICS)     : tile-based collision detection
  - GRID_SNAP            (UTILITY)     : snap position to a configurable grid
  - SCREEN_WRAP          (UTILITY)     : wrap position around screen boundaries

Usage:
    lib = get_behavior_library()
    lib.preload_builtins()
    instance = lib.instantiate_behavior("platformer_character", "player_1",
                                        {"speed": 300.0, "jump_force": 500.0})
    lib.activate_behavior(instance.id)
    lib.process_behavior(instance.id, 0.016)
"""

from __future__ import annotations

import json
import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

_time_module = time


class BehaviorCategory(Enum):
    MOVEMENT = "movement"
    COMBAT = "combat"
    PHYSICS = "physics"
    AI = "ai"
    INPUT = "input"
    UI = "ui"
    CAMERA = "camera"
    AUDIO = "audio"
    VISUAL = "visual"
    UTILITY = "utility"


@dataclass
class BehaviorDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    category: BehaviorCategory = BehaviorCategory.UTILITY
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    init_actions: List[Dict[str, Any]] = field(default_factory=list)
    update_actions: List[Dict[str, Any]] = field(default_factory=list)
    cleanup_actions: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": list(self.parameters),
            "init_actions": list(self.init_actions),
            "update_actions": list(self.update_actions),
            "cleanup_actions": list(self.cleanup_actions),
            "tags": list(self.tags),
            "version": self.version,
            "created_at": self.created_at,
        }


@dataclass
class BehaviorInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    definition_id: str = ""
    entity_id: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    active: bool = False
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "definition_id": self.definition_id,
            "entity_id": self.entity_id,
            "properties": dict(self.properties),
            "active": self.active,
            "created_at": self.created_at,
        }


class BehaviorLibrary:
    _instance: Optional["BehaviorLibrary"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "BehaviorLibrary":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._definitions: Dict[str, BehaviorDefinition] = {}
        self._instances: Dict[str, BehaviorInstance] = {}
        self._entity_index: Dict[str, List[str]] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._builtins_loaded: bool = False
        self._action_handlers: Dict[str, Callable] = {}
        self._tick_count: int = 0

    @classmethod
    def get_instance(cls) -> "BehaviorLibrary":
        return cls()

    # ------------------------------------------------------------------
    # Behavior Registration
    # ------------------------------------------------------------------

    def register_behavior(
        self,
        name: str,
        category: BehaviorCategory,
        description: str = "",
        parameters: Optional[List[Dict[str, Any]]] = None,
        init_actions: Optional[List[Dict[str, Any]]] = None,
        update_actions: Optional[List[Dict[str, Any]]] = None,
        cleanup_actions: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        version: str = "1.0.0",
    ) -> BehaviorDefinition:
        definition = BehaviorDefinition(
            name=name,
            category=category,
            description=description,
            parameters=parameters or [],
            init_actions=init_actions or [],
            update_actions=update_actions or [],
            cleanup_actions=cleanup_actions or [],
            tags=tags or [],
            version=version,
        )
        self._definitions[definition.id] = definition
        self._category_index.setdefault(category.value, []).append(definition.id)
        return definition

    # ------------------------------------------------------------------
    # Instance Management
    # ------------------------------------------------------------------

    def instantiate_behavior(
        self,
        definition_id: str,
        entity_id: str,
        property_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[BehaviorInstance]:
        definition = self._definitions.get(definition_id)
        if definition is None:
            return None
        properties: Dict[str, Any] = {}
        for param in definition.parameters:
            param_name = param.get("name", "")
            if param_name:
                properties[param_name] = param.get("default")
        if property_overrides:
            for key, value in property_overrides.items():
                properties[key] = value
        instance = BehaviorInstance(
            definition_id=definition_id,
            entity_id=entity_id,
            properties=properties,
        )
        self._instances[instance.id] = instance
        self._entity_index.setdefault(entity_id, []).append(instance.id)
        return instance

    def activate_behavior(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None or instance.active:
            return False
        instance.active = True
        definition = self._definitions.get(instance.definition_id)
        if definition is None:
            return False
        for action in definition.init_actions:
            self._dispatch_action(action, instance, 0.0)
        return True

    def deactivate_behavior(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None or not instance.active:
            return False
        instance.active = False
        definition = self._definitions.get(instance.definition_id)
        if definition is None:
            return False
        for action in definition.cleanup_actions:
            self._dispatch_action(action, instance, 0.0)
        return True

    def process_behavior(self, instance_id: str, delta_time: float = 0.016) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None or not instance.active:
            return False
        definition = self._definitions.get(instance.definition_id)
        if definition is None:
            return False
        self._tick_count += 1
        for action in definition.update_actions:
            self._dispatch_action(action, instance, delta_time)
        return True

    def remove_behavior(self, instance_id: str) -> bool:
        instance = self._instances.pop(instance_id, None)
        if instance is None:
            return False
        if instance.active:
            definition = self._definitions.get(instance.definition_id)
            if definition:
                for action in definition.cleanup_actions:
                    self._dispatch_action(action, instance, 0.0)
        eid = instance.entity_id
        if eid in self._entity_index and instance_id in self._entity_index[eid]:
            self._entity_index[eid].remove(instance_id)
            if not self._entity_index[eid]:
                del self._entity_index[eid]
        return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_behaviors_for_entity(self, entity_id: str) -> List[BehaviorInstance]:
        instance_ids = self._entity_index.get(entity_id, [])
        return [self._instances[iid] for iid in instance_ids if iid in self._instances]

    def get_behaviors_by_category(self, category: BehaviorCategory) -> List[BehaviorDefinition]:
        def_ids = self._category_index.get(category.value, [])
        return [self._definitions[did] for did in def_ids if did in self._definitions]

    # ------------------------------------------------------------------
    # Built-in Behaviors
    # ------------------------------------------------------------------

    def preload_builtins(self) -> None:
        if self._builtins_loaded:
            return
        self._register_platformer_character()
        self._register_top_down_movement()
        self._register_health_system()
        self._register_pathfinding()
        self._register_projectile_spawner()
        self._register_follow_target()
        self._register_rotate_toward()
        self._register_float_bob()
        self._register_damage_on_collision()
        self._register_destroy_after_animation()
        self._register_tilemap_collider()
        self._register_grid_snap()
        self._register_screen_wrap()
        self._builtins_loaded = True

    def _register_platformer_character(self) -> None:
        self.register_behavior(
            name="PlatformerCharacter",
            category=BehaviorCategory.MOVEMENT,
            description="Side-scrolling platformer movement with gravity, jump, and ground detection.",
            parameters=[
                {"name": "speed", "type": "float", "default": 200.0,
                 "description": "Horizontal movement speed in pixels per second"},
                {"name": "jump_force", "type": "float", "default": 450.0,
                 "description": "Initial vertical velocity applied on jump"},
                {"name": "gravity", "type": "float", "default": 980.0,
                 "description": "Downward acceleration in pixels per second squared"},
                {"name": "max_fall_speed", "type": "float", "default": 600.0,
                 "description": "Maximum downward velocity"},
                {"name": "acceleration", "type": "float", "default": 1200.0,
                 "description": "Horizontal acceleration rate"},
                {"name": "friction", "type": "float", "default": 800.0,
                 "description": "Horizontal deceleration when no input"},
                {"name": "jump_hold_time", "type": "float", "default": 0.2,
                 "description": "Maximum time jump button can be held for variable height"},
                {"name": "coyote_time", "type": "float", "default": 0.08,
                 "description": "Grace period after leaving ground to still jump"},
                {"name": "jump_buffer_time", "type": "float", "default": 0.1,
                 "description": "Grace period to press jump before landing"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
                {"type": "set_variable", "target": "is_grounded", "value": True},
                {"type": "set_variable", "target": "jump_hold_timer", "value": 0.0},
                {"type": "set_variable", "target": "coyote_timer", "value": 0.0},
                {"type": "set_variable", "target": "jump_buffer_timer", "value": 0.0},
                {"type": "set_variable", "target": "facing_right", "value": True},
                {"type": "set_variable", "target": "is_jumping", "value": False},
            ],
            update_actions=[
                {"type": "read_input", "target": "input_horizontal", "axis": "horizontal"},
                {"type": "read_input", "target": "input_jump", "action": "jump_pressed"},
                {"type": "read_input", "target": "input_jump_hold", "action": "jump_held"},
                {"type": "apply_horizontal_acceleration", "input": "input_horizontal",
                 "accel": "acceleration", "friction": "friction", "max_speed": "speed",
                 "velocity": "velocity_x"},
                {"type": "apply_gravity", "velocity_y": "velocity_y", "gravity": "gravity",
                 "max_fall": "max_fall_speed", "delta": True},
                {"type": "update_coyote_time", "timer": "coyote_timer",
                 "grounded": "is_grounded", "coyote": "coyote_time", "delta": True},
                {"type": "update_jump_buffer", "timer": "jump_buffer_timer",
                 "input": "input_jump", "buffer": "jump_buffer_time", "delta": True},
                {"type": "check_jump_condition", "can_jump": "can_jump",
                 "coyote_timer": "coyote_timer", "jump_buffer": "jump_buffer_timer",
                 "grounded": "is_grounded"},
                {"type": "execute_jump", "condition": "can_jump", "input": "input_jump",
                 "velocity_y": "velocity_y", "jump_force": "jump_force",
                 "hold_timer": "jump_hold_timer", "is_jumping": "is_jumping"},
                {"type": "apply_variable_jump_height", "velocity_y": "velocity_y",
                 "hold_timer": "jump_hold_timer", "hold_time": "jump_hold_time",
                 "gravity": "gravity", "input_hold": "input_jump_hold",
                 "is_jumping": "is_jumping", "delta": True},
                {"type": "commit_position", "velocity_x": "velocity_x",
                 "velocity_y": "velocity_y", "delta": True},
                {"type": "update_facing", "velocity_x": "velocity_x",
                 "facing_right": "facing_right"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
                {"type": "set_variable", "target": "is_jumping", "value": False},
            ],
            tags=["movement", "platformer", "jump", "gravity", "character"],
            version="1.0.0",
        )

    def _register_top_down_movement(self) -> None:
        self.register_behavior(
            name="TopDownMovement",
            category=BehaviorCategory.MOVEMENT,
            description="8-directional top-down movement with acceleration, friction, and diagonal normalization.",
            parameters=[
                {"name": "speed", "type": "float", "default": 200.0,
                 "description": "Maximum movement speed in pixels per second"},
                {"name": "acceleration", "type": "float", "default": 1500.0,
                 "description": "Acceleration rate when input is active"},
                {"name": "friction", "type": "float", "default": 1000.0,
                 "description": "Deceleration rate when no input"},
                {"name": "normalize_diagonal", "type": "bool", "default": True,
                 "description": "Whether to normalize diagonal input vectors"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
            ],
            update_actions=[
                {"type": "read_input", "target": "input_h", "axis": "horizontal"},
                {"type": "read_input", "target": "input_v", "axis": "vertical"},
                {"type": "normalize_diagonal", "h": "input_h", "v": "input_v",
                 "enabled": "normalize_diagonal"},
                {"type": "apply_acceleration_2d", "vel_x": "velocity_x", "vel_y": "velocity_y",
                 "input_x": "input_h", "input_v": "input_v",
                 "accel": "acceleration", "friction": "friction",
                 "max_speed": "speed", "delta": True},
                {"type": "commit_position_2d", "velocity_x": "velocity_x",
                 "velocity_y": "velocity_y", "delta": True},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
            ],
            tags=["movement", "top_down", "8-directional", "character"],
            version="1.0.0",
        )

    def _register_health_system(self) -> None:
        self.register_behavior(
            name="HealthSystem",
            category=BehaviorCategory.COMBAT,
            description="HP management with damage, healing, invincibility frames, auto-regeneration, and death trigger.",
            parameters=[
                {"name": "max_hp", "type": "float", "default": 100.0,
                 "description": "Maximum health points"},
                {"name": "current_hp", "type": "float", "default": 100.0,
                 "description": "Current health points"},
                {"name": "invincibility_duration", "type": "float", "default": 0.5,
                 "description": "Seconds of invincibility after taking damage"},
                {"name": "auto_regen_rate", "type": "float", "default": 0.0,
                 "description": "HP regenerated per second when not at max"},
                {"name": "auto_regen_delay", "type": "float", "default": 3.0,
                 "description": "Seconds after last damage before regen starts"},
                {"name": "death_delay", "type": "float", "default": 0.0,
                 "description": "Delay in seconds before death event fires"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "current_hp", "value": "max_hp"},
                {"type": "set_variable", "target": "is_alive", "value": True},
                {"type": "set_variable", "target": "is_invincible", "value": False},
                {"type": "set_variable", "target": "invincible_timer", "value": 0.0},
                {"type": "set_variable", "target": "regen_cooldown", "value": 0.0},
                {"type": "set_variable", "target": "death_timer", "value": 0.0},
            ],
            update_actions=[
                {"type": "update_invincibility", "timer": "invincible_timer",
                 "duration": "invincibility_duration", "is_invincible": "is_invincible",
                 "delta": True},
                {"type": "update_regen", "hp": "current_hp", "max_hp": "max_hp",
                 "rate": "auto_regen_rate", "cooldown": "regen_cooldown",
                 "regen_delay": "auto_regen_delay", "delta": True},
                {"type": "check_death_condition", "is_alive": "is_alive",
                 "hp": "current_hp", "death_timer": "death_timer",
                 "death_delay": "death_delay"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "is_alive", "value": False},
                {"type": "set_variable", "target": "is_invincible", "value": False},
            ],
            tags=["combat", "health", "damage", "heal", "death"],
            version="1.0.0",
        )

    def _register_pathfinding(self) -> None:
        self.register_behavior(
            name="Pathfinding",
            category=BehaviorCategory.AI,
            description="A* pathfinding with configurable speed, waypoint tolerance, and path recalculation.",
            parameters=[
                {"name": "move_speed", "type": "float", "default": 150.0,
                 "description": "Movement speed along the path in pixels per second"},
                {"name": "waypoint_tolerance", "type": "float", "default": 8.0,
                 "description": "Distance threshold to consider a waypoint reached"},
                {"name": "path_recalculate_interval", "type": "float", "default": 0.5,
                 "description": "Seconds between path recalculations for moving targets"},
                {"name": "target_entity_id", "type": "string", "default": "",
                 "description": "Entity ID to pathfind toward"},
                {"name": "target_x", "type": "float", "default": 0.0,
                 "description": "Static target X coordinate"},
                {"name": "target_y", "type": "float", "default": 0.0,
                 "description": "Static target Y coordinate"},
                {"name": "avoidance_radius", "type": "float", "default": 20.0,
                 "description": "Radius for local obstacle avoidance"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "current_path", "value": []},
                {"type": "set_variable", "target": "current_waypoint_index", "value": 0},
                {"type": "set_variable", "target": "recalculate_timer", "value": 0.0},
                {"type": "set_variable", "target": "is_pathfinding", "value": False},
            ],
            update_actions=[
                {"type": "resolve_target_position", "entity_id": "target_entity_id",
                 "static_x": "target_x", "static_y": "target_y",
                 "target_pos_x": "resolved_tx", "target_pos_y": "resolved_ty"},
                {"type": "update_recalculate_timer", "timer": "recalculate_timer",
                 "interval": "path_recalculate_interval",
                 "should_recalculate": "should_recalc", "delta": True},
                {"type": "compute_astar_path", "condition": "should_recalc",
                 "target_x": "resolved_tx", "target_y": "resolved_ty",
                 "path": "current_path", "waypoint_index": "current_waypoint_index",
                 "is_pathfinding": "is_pathfinding"},
                {"type": "move_toward_waypoint", "path": "current_path",
                 "index": "current_waypoint_index", "speed": "move_speed",
                 "tolerance": "waypoint_tolerance", "delta": True},
                {"type": "advance_waypoint", "path": "current_path",
                 "index": "current_waypoint_index", "tolerance": "waypoint_tolerance"},
                {"type": "apply_local_avoidance", "radius": "avoidance_radius",
                 "vel_x": "velocity_x", "vel_y": "velocity_y"},
                {"type": "commit_position_2d", "velocity_x": "velocity_x",
                 "velocity_y": "velocity_y", "delta": True},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "current_path", "value": []},
                {"type": "set_variable", "target": "is_pathfinding", "value": False},
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
            ],
            tags=["ai", "pathfinding", "astar", "navigation", "movement"],
            version="1.0.0",
        )

    def _register_projectile_spawner(self) -> None:
        self.register_behavior(
            name="ProjectileSpawner",
            category=BehaviorCategory.COMBAT,
            description="Timed projectile creation with configurable spawn rate, speed, direction, and lifetime.",
            parameters=[
                {"name": "projectile_prefab", "type": "string", "default": "bullet",
                 "description": "Prefab name of the projectile to spawn"},
                {"name": "fire_rate", "type": "float", "default": 0.3,
                 "description": "Seconds between projectile spawns"},
                {"name": "projectile_speed", "type": "float", "default": 500.0,
                 "description": "Initial speed of spawned projectiles"},
                {"name": "projectile_lifetime", "type": "float", "default": 3.0,
                 "description": "Seconds before the projectile is destroyed"},
                {"name": "spread_angle", "type": "float", "default": 0.0,
                 "description": "Random spread angle in degrees"},
                {"name": "projectiles_per_shot", "type": "int", "default": 1,
                 "description": "Number of projectiles per fire event"},
                {"name": "auto_fire", "type": "bool", "default": False,
                 "description": "Whether to fire automatically on interval"},
                {"name": "direction_x", "type": "float", "default": 1.0,
                 "description": "Default fire direction X component"},
                {"name": "direction_y", "type": "float", "default": 0.0,
                 "description": "Default fire direction Y component"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "fire_cooldown", "value": 0.0},
                {"type": "set_variable", "target": "projectiles_active", "value": []},
            ],
            update_actions=[
                {"type": "update_cooldown", "timer": "fire_cooldown",
                 "rate": "fire_rate", "delta": True},
                {"type": "read_input", "target": "input_fire", "action": "fire"},
                {"type": "check_fire_condition", "should_fire": "should_fire",
                 "cooldown": "fire_cooldown", "fire_rate": "fire_rate",
                 "input_fire": "input_fire", "auto_fire": "auto_fire"},
                {"type": "spawn_projectiles", "condition": "should_fire",
                 "prefab": "projectile_prefab", "count": "projectiles_per_shot",
                 "speed": "projectile_speed", "lifetime": "projectile_lifetime",
                 "spread": "spread_angle", "dir_x": "direction_x",
                 "dir_y": "direction_y", "active_list": "projectiles_active",
                 "reset_cooldown": "fire_cooldown"},
            ],
            cleanup_actions=[
                {"type": "destroy_all_projectiles", "list": "projectiles_active"},
                {"type": "set_variable", "target": "projectiles_active", "value": []},
            ],
            tags=["combat", "projectile", "shooting", "bullet", "spawner"],
            version="1.0.0",
        )

    def _register_follow_target(self) -> None:
        self.register_behavior(
            name="FollowTarget",
            category=BehaviorCategory.AI,
            description="Chase behavior that smoothly follows a target entity with configurable speed and distance thresholds.",
            parameters=[
                {"name": "target_entity_id", "type": "string", "default": "",
                 "description": "Entity ID to follow"},
                {"name": "follow_speed", "type": "float", "default": 180.0,
                 "description": "Maximum follow speed in pixels per second"},
                {"name": "min_distance", "type": "float", "default": 32.0,
                 "description": "Stop following when within this distance"},
                {"name": "max_distance", "type": "float", "default": 600.0,
                 "description": "Lose interest beyond this distance"},
                {"name": "offset_x", "type": "float", "default": 0.0,
                 "description": "Horizontal offset from target position"},
                {"name": "offset_y", "type": "float", "default": 0.0,
                 "description": "Vertical offset from target position"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
                {"type": "set_variable", "target": "is_following", "value": False},
            ],
            update_actions=[
                {"type": "get_entity_position", "entity_id": "target_entity_id",
                 "pos_x": "target_pos_x", "pos_y": "target_pos_y",
                 "found": "target_found"},
                {"type": "compute_distance_to_target", "found": "target_found",
                 "target_x": "target_pos_x", "target_y": "target_pos_y",
                 "offset_x": "offset_x", "offset_y": "offset_y",
                 "distance": "dist_to_target", "dir_x": "dir_x", "dir_y": "dir_y"},
                {"type": "check_follow_range", "distance": "dist_to_target",
                 "min_dist": "min_distance", "max_dist": "max_distance",
                 "is_following": "is_following"},
                {"type": "move_toward_target", "is_following": "is_following",
                 "dir_x": "dir_x", "dir_y": "dir_y", "speed": "follow_speed",
                 "distance": "dist_to_target", "min_dist": "min_distance",
                 "vel_x": "velocity_x", "vel_y": "velocity_y"},
                {"type": "commit_position_2d", "velocity_x": "velocity_x",
                 "velocity_y": "velocity_y", "delta": True},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "velocity_x", "value": 0.0},
                {"type": "set_variable", "target": "velocity_y", "value": 0.0},
                {"type": "set_variable", "target": "is_following", "value": False},
            ],
            tags=["ai", "follow", "chase", "movement", "target"],
            version="1.0.0",
        )

    def _register_rotate_toward(self) -> None:
        self.register_behavior(
            name="RotateToward",
            category=BehaviorCategory.VISUAL,
            description="Auto-rotation that smoothly turns an entity toward a target, movement direction, or a fixed angle.",
            parameters=[
                {"name": "rotation_mode", "type": "string", "default": "movement_direction",
                 "description": "Rotation mode: movement_direction, target, or fixed_angle"},
                {"name": "rotation_speed", "type": "float", "default": 360.0,
                 "description": "Rotation speed in degrees per second"},
                {"name": "target_entity_id", "type": "string", "default": "",
                 "description": "Target entity for look-at rotation mode"},
                {"name": "fixed_angle", "type": "float", "default": 0.0,
                 "description": "Fixed rotation angle in degrees"},
                {"name": "rotation_offset", "type": "float", "default": 0.0,
                 "description": "Offset angle added to computed rotation"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "current_angle", "value": 0.0},
                {"type": "set_variable", "target": "target_angle", "value": 0.0},
            ],
            update_actions=[
                {"type": "compute_target_angle", "mode": "rotation_mode",
                 "target_entity": "target_entity_id", "fixed": "fixed_angle",
                 "offset": "rotation_offset", "target_angle": "target_angle"},
                {"type": "slerp_rotation", "current": "current_angle",
                 "target": "target_angle", "speed": "rotation_speed", "delta": True},
                {"type": "apply_rotation", "angle": "current_angle"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "target_angle", "value": 0.0},
            ],
            tags=["visual", "rotation", "look_at", "auto_rotate", "transform"],
            version="1.0.0",
        )

    def _register_float_bob(self) -> None:
        self.register_behavior(
            name="FloatBob",
            category=BehaviorCategory.VISUAL,
            description="Decorative sinusoidal vertical floating motion with configurable amplitude and frequency.",
            parameters=[
                {"name": "amplitude", "type": "float", "default": 12.0,
                 "description": "Vertical bob amplitude in pixels"},
                {"name": "frequency", "type": "float", "default": 2.0,
                 "description": "Bob frequency in Hz"},
                {"name": "phase_offset", "type": "float", "default": 0.0,
                 "description": "Initial phase offset in radians"},
                {"name": "horizontal_amplitude", "type": "float", "default": 0.0,
                 "description": "Optional horizontal bob amplitude"},
                {"name": "horizontal_frequency", "type": "float", "default": 1.5,
                 "description": "Horizontal bob frequency in Hz"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "bob_timer", "value": 0.0},
                {"type": "set_variable", "target": "base_y", "value": 0.0},
                {"type": "set_variable", "target": "base_x", "value": 0.0},
                {"type": "capture_base_position", "target_x": "base_x", "target_y": "base_y"},
            ],
            update_actions=[
                {"type": "advance_timer", "timer": "bob_timer", "delta": True},
                {"type": "compute_sine_offset", "timer": "bob_timer",
                 "amplitude": "amplitude", "frequency": "frequency",
                 "phase": "phase_offset", "offset_y": "bob_offset_y"},
                {"type": "compute_sine_offset", "timer": "bob_timer",
                 "amplitude": "horizontal_amplitude", "frequency": "horizontal_frequency",
                 "phase": "phase_offset", "offset_y": "bob_offset_x"},
                {"type": "apply_bob_position", "base_x": "base_x", "base_y": "base_y",
                 "offset_x": "bob_offset_x", "offset_y": "bob_offset_y"},
            ],
            cleanup_actions=[
                {"type": "restore_base_position", "base_x": "base_x", "base_y": "base_y"},
            ],
            tags=["visual", "bobbing", "floating", "decoration", "movement"],
            version="1.0.0",
        )

    def _register_damage_on_collision(self) -> None:
        self.register_behavior(
            name="DamageOnCollision",
            category=BehaviorCategory.COMBAT,
            description="Apply damage to entities that collide with this entity, with configurable cooldown and target filtering.",
            parameters=[
                {"name": "damage_amount", "type": "float", "default": 25.0,
                 "description": "Amount of damage to apply per collision"},
                {"name": "damage_cooldown", "type": "float", "default": 0.0,
                 "description": "Minimum seconds between damage applications to the same target"},
                {"name": "target_tags", "type": "string", "default": "",
                 "description": "Comma-separated tags to filter which entities receive damage"},
                {"name": "destroy_on_hit", "type": "bool", "default": False,
                 "description": "Whether to destroy this entity after dealing damage"},
                {"name": "knockback_force", "type": "float", "default": 200.0,
                 "description": "Knockback force applied to damaged entities"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "hit_targets", "value": {}},
                {"type": "set_variable", "target": "cooldown_timers", "value": {}},
            ],
            update_actions=[
                {"type": "detect_collisions", "colliding": "collisions",
                 "target_tags": "target_tags"},
                {"type": "update_cooldown_timers", "timers": "cooldown_timers",
                 "delta": True},
                {"type": "apply_damage_to_collisions", "collisions": "collisions",
                 "damage": "damage_amount", "cooldown": "damage_cooldown",
                 "timers": "cooldown_timers", "hit_targets": "hit_targets",
                 "knockback": "knockback_force",
                 "destroy_self": "destroy_on_hit"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "hit_targets", "value": {}},
                {"type": "set_variable", "target": "cooldown_timers", "value": {}},
            ],
            tags=["combat", "damage", "collision", "hit", "trigger"],
            version="1.0.0",
        )

    def _register_destroy_after_animation(self) -> None:
        self.register_behavior(
            name="DestroyAfterAnimation",
            category=BehaviorCategory.VISUAL,
            description="Automatically destroy the entity after its current animation finishes playing.",
            parameters=[
                {"name": "animation_name", "type": "string", "default": "",
                 "description": "Specific animation to watch; empty means any animation"},
                {"name": "destroy_delay", "type": "float", "default": 0.0,
                 "description": "Additional delay in seconds after animation ends before destruction"},
                {"name": "spawn_effect", "type": "string", "default": "",
                 "description": "Effect prefab to spawn at entity position on destruction"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "animation_finished", "value": False},
                {"type": "set_variable", "target": "destroy_timer", "value": 0.0},
                {"type": "set_variable", "target": "destroy_initiated", "value": False},
            ],
            update_actions=[
                {"type": "check_animation_end", "anim_name": "animation_name",
                 "finished": "animation_finished"},
                {"type": "start_destroy_countdown", "finished": "animation_finished",
                 "initiated": "destroy_initiated", "timer": "destroy_timer"},
                {"type": "update_destroy_timer", "initiated": "destroy_initiated",
                 "timer": "destroy_timer", "delay": "destroy_delay",
                 "should_destroy": "should_destroy", "delta": True},
                {"type": "execute_destroy", "should_destroy": "should_destroy",
                 "spawn_effect": "spawn_effect"},
            ],
            cleanup_actions=[
                {"type": "spawn_destroy_effect", "effect": "spawn_effect"},
                {"type": "destroy_entity"},
            ],
            tags=["visual", "animation", "destroy", "cleanup", "vfx"],
            version="1.0.0",
        )

    def _register_tilemap_collider(self) -> None:
        self.register_behavior(
            name="TilemapCollider",
            category=BehaviorCategory.PHYSICS,
            description="Tile-based collision detection and resolution against a tilemap layer.",
            parameters=[
                {"name": "tilemap_layer", "type": "string", "default": "collision",
                 "description": "Name of the tilemap layer to collide against"},
                {"name": "collision_mask", "type": "string", "default": "",
                 "description": "Comma-separated tile IDs that count as solid"},
                {"name": "collision_margin", "type": "float", "default": 1.0,
                 "description": "Extra padding around entity bounds for collision detection"},
                {"name": "slope_enabled", "type": "bool", "default": False,
                 "description": "Whether to handle sloped tile surfaces"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "is_grounded", "value": False},
                {"type": "set_variable", "target": "collision_normal_x", "value": 0.0},
                {"type": "set_variable", "target": "collision_normal_y", "value": 0.0},
                {"type": "set_variable", "target": "touching_wall_left", "value": False},
                {"type": "set_variable", "target": "touching_wall_right", "value": False},
                {"type": "set_variable", "target": "touching_ceiling", "value": False},
            ],
            update_actions=[
                {"type": "resolve_tile_collisions", "layer": "tilemap_layer",
                 "mask": "collision_mask", "margin": "collision_margin",
                 "slope_enabled": "slope_enabled",
                 "is_grounded": "is_grounded",
                 "normal_x": "collision_normal_x",
                 "normal_y": "collision_normal_y",
                 "wall_left": "touching_wall_left",
                 "wall_right": "touching_wall_right",
                 "ceiling": "touching_ceiling"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "is_grounded", "value": False},
                {"type": "set_variable", "target": "touching_wall_left", "value": False},
                {"type": "set_variable", "target": "touching_wall_right", "value": False},
                {"type": "set_variable", "target": "touching_ceiling", "value": False},
            ],
            tags=["physics", "collision", "tilemap", "tile", "platformer"],
            version="1.0.0",
        )

    def _register_grid_snap(self) -> None:
        self.register_behavior(
            name="GridSnap",
            category=BehaviorCategory.UTILITY,
            description="Snap the entity's position to a configurable grid after movement, useful for tile-based games.",
            parameters=[
                {"name": "grid_size_x", "type": "float", "default": 32.0,
                 "description": "Grid cell width in pixels"},
                {"name": "grid_size_y", "type": "float", "default": 32.0,
                 "description": "Grid cell height in pixels"},
                {"name": "snap_origin_x", "type": "float", "default": 0.0,
                 "description": "Grid origin X offset"},
                {"name": "snap_origin_y", "type": "float", "default": 0.0,
                 "description": "Grid origin Y offset"},
                {"name": "snap_mode", "type": "string", "default": "center",
                 "description": "Snap mode: center, floor, ceil, or round"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "snap_enabled", "value": True},
            ],
            update_actions=[
                {"type": "compute_snapped_position", "mode": "snap_mode",
                 "grid_x": "grid_size_x", "grid_y": "grid_size_y",
                 "origin_x": "snap_origin_x", "origin_y": "snap_origin_y",
                 "snapped_x": "snapped_x", "snapped_y": "snapped_y"},
                {"type": "apply_snapped_position", "x": "snapped_x", "y": "snapped_y"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "snap_enabled", "value": False},
            ],
            tags=["utility", "grid", "snap", "alignment", "tile"],
            version="1.0.0",
        )

    def _register_screen_wrap(self) -> None:
        self.register_behavior(
            name="ScreenWrap",
            category=BehaviorCategory.UTILITY,
            description="Wrap the entity position around screen boundaries, useful for Asteroids-style games.",
            parameters=[
                {"name": "wrap_horizontal", "type": "bool", "default": True,
                 "description": "Whether to wrap on horizontal screen edges"},
                {"name": "wrap_vertical", "type": "bool", "default": True,
                 "description": "Whether to wrap on vertical screen edges"},
                {"name": "screen_width", "type": "float", "default": 1920.0,
                 "description": "Screen width in pixels"},
                {"name": "screen_height", "type": "float", "default": 1080.0,
                 "description": "Screen height in pixels"},
                {"name": "wrap_margin", "type": "float", "default": 0.0,
                 "description": "Extra margin outside screen before wrapping triggers"},
            ],
            init_actions=[
                {"type": "set_variable", "target": "was_wrapped_h", "value": False},
                {"type": "set_variable", "target": "was_wrapped_v", "value": False},
            ],
            update_actions=[
                {"type": "check_horizontal_wrap", "enabled": "wrap_horizontal",
                 "width": "screen_width", "margin": "wrap_margin",
                 "was_wrapped": "was_wrapped_h"},
                {"type": "check_vertical_wrap", "enabled": "wrap_vertical",
                 "height": "screen_height", "margin": "wrap_margin",
                 "was_wrapped": "was_wrapped_v"},
            ],
            cleanup_actions=[
                {"type": "set_variable", "target": "was_wrapped_h", "value": False},
                {"type": "set_variable", "target": "was_wrapped_v", "value": False},
            ],
            tags=["utility", "screen", "wrap", "boundary", "movement"],
            version="1.0.0",
        )

    # ------------------------------------------------------------------
    # Action Dispatch
    # ------------------------------------------------------------------

    def _dispatch_action(
        self,
        action: Dict[str, Any],
        instance: BehaviorInstance,
        delta_time: float,
    ) -> None:
        action_type = action.get("type", "")
        handler = self._action_handlers.get(action_type)
        if handler is not None:
            handler(action, instance, delta_time)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_behavior_library_stats(self) -> Dict[str, Any]:
        category_counts: Dict[str, int] = {}
        for def_id in self._definitions:
            cat = self._definitions[def_id].category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        active_count = sum(1 for inst in self._instances.values() if inst.active)
        return {
            "total_definitions": len(self._definitions),
            "total_instances": len(self._instances),
            "active_instances": active_count,
            "inactive_instances": len(self._instances) - active_count,
            "unique_entities": len(self._entity_index),
            "builtins_loaded": self._builtins_loaded,
            "tick_count": self._tick_count,
            "category_distribution": category_counts,
            "builtin_definition_ids": [
                did for did, d in self._definitions.items()
                if "builtin" in d.tags or d.version == "1.0.0"
            ],
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_behavior_library() -> BehaviorLibrary:
    return BehaviorLibrary.get_instance()