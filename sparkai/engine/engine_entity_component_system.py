"""
SparkLabs Engine - Entity Component System

High-performance, flexible Entity Component System (ECS) architecture
for game object management. Entities are lightweight identifiers that
gain behavior through composable components. Systems process entities
that possess matching component sets, enabling fully data-driven
gameplay logic with strict separation of data and behavior.

Architecture:
  EngineEntityComponentSystem
    |-- Entity (lightweight identifier with component map)
    |-- Component (typed data container with lifecycle phase)
    |-- ComponentBlueprint (reusable component template)
    |-- System (processing logic targeting matching entities)
    |-- EntityArchetype (predefined entity composition template)
    |-- World (container managing entities, systems, and hierarchy)
"""

from __future__ import annotations

import math
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Type


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class ComponentCategory(Enum):
    TRANSFORM = "transform"
    RENDER = "render"
    PHYSICS = "physics"
    AI = "ai"
    AUDIO = "audio"
    INPUT = "input"
    NETWORK = "network"
    UI = "ui"
    ANIMATION = "animation"
    LIFECYCLE = "lifecycle"


class ComponentUpdatePhase(Enum):
    PRE_UPDATE = "pre_update"
    UPDATE = "update"
    POST_UPDATE = "post_update"
    LATE_UPDATE = "late_update"
    PRE_RENDER = "pre_render"
    RENDER = "render"
    POST_RENDER = "post_render"


class SystemExecutionOrder(Enum):
    FIRST = 0
    EARLY = 25
    NORMAL = 50
    LATE = 75
    LAST = 100


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Entity:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    tag: str = ""
    active: bool = True
    components: Dict[str, str] = field(default_factory=dict)
    system_subscriptions: List[str] = field(default_factory=list)
    creation_frame: int = 0
    last_update_frame: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "tag": self.tag,
            "active": self.active,
            "components": dict(self.components),
            "system_subscriptions": list(self.system_subscriptions),
            "creation_frame": self.creation_frame,
            "last_update_frame": self.last_update_frame,
        }


@dataclass
class Component:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    category: ComponentCategory = ComponentCategory.LIFECYCLE
    active: bool = True
    data: Dict[str, Any] = field(default_factory=dict)
    update_phase: ComponentUpdatePhase = ComponentUpdatePhase.UPDATE
    order: int = 0
    dependencies: List[str] = field(default_factory=list)
    serialization_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "category": self.category.value,
            "active": self.active,
            "data": dict(self.data),
            "update_phase": self.update_phase.value,
            "order": self.order,
            "dependencies": list(self.dependencies),
            "serialization_data": dict(self.serialization_data),
        }


@dataclass
class ComponentBlueprint:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: ComponentCategory = ComponentCategory.LIFECYCLE
    default_data: Dict[str, Any] = field(default_factory=dict)
    required_components: List[str] = field(default_factory=list)
    incompatible_components: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "default_data": dict(self.default_data),
            "required_components": list(self.required_components),
            "incompatible_components": list(self.incompatible_components),
            "description": self.description,
        }


@dataclass
class System:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    required_components: List[str] = field(default_factory=list)
    update_phase: ComponentUpdatePhase = ComponentUpdatePhase.UPDATE
    execution_order: SystemExecutionOrder = SystemExecutionOrder.NORMAL
    active: bool = True
    entities_list: List[str] = field(default_factory=list)
    priority: int = 0
    performance_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "required_components": list(self.required_components),
            "update_phase": self.update_phase.value,
            "execution_order": self.execution_order.value,
            "active": self.active,
            "entities_list": list(self.entities_list),
            "priority": self.priority,
            "performance_stats": dict(self.performance_stats),
        }


@dataclass
class World:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    entities: Dict[str, Entity] = field(default_factory=dict)
    systems: Dict[str, System] = field(default_factory=dict)
    component_registry: Dict[str, Component] = field(default_factory=dict)
    blueprint_registry: Dict[str, ComponentBlueprint] = field(default_factory=dict)
    entity_hierarchy: Dict[str, str] = field(default_factory=dict)
    event_queue: List[Tuple[str, Dict[str, Any]]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_count": len(self.entities),
            "system_count": len(self.systems),
            "component_count": len(self.component_registry),
            "blueprint_count": len(self.blueprint_registry),
            "hierarchy_entries": len(self.entity_hierarchy),
            "event_queue_size": len(self.event_queue),
        }


@dataclass
class EntityArchetype:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    template_components: List[ComponentBlueprint] = field(default_factory=list)
    default_values: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    category: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "template_components": [
                {"id": c.id, "name": c.name, "category": c.category.value}
                for c in self.template_components
            ],
            "default_values": dict(self.default_values),
            "description": self.description,
            "category": self.category,
        }


# ---------------------------------------------------------------------------
# Pre-Defined Component Blueprints
# ---------------------------------------------------------------------------

_PREDEFINED_BLUEPRINTS: Dict[str, Dict[str, Any]] = {
    "Transform": {
        "name": "Transform",
        "category": ComponentCategory.TRANSFORM,
        "default_data": {
            "position_x": 0.0,
            "position_y": 0.0,
            "position_z": 0.0,
            "rotation_x": 0.0,
            "rotation_y": 0.0,
            "rotation_z": 0.0,
            "scale_x": 1.0,
            "scale_y": 1.0,
            "scale_z": 1.0,
        },
        "required_components": [],
        "incompatible_components": [],
        "description": "Spatial positioning, rotation, and scale for an entity in world space.",
    },
    "Sprite": {
        "name": "Sprite",
        "category": ComponentCategory.RENDER,
        "default_data": {
            "texture_id": "",
            "color_r": 255,
            "color_g": 255,
            "color_b": 255,
            "color_a": 255,
            "width": 32,
            "height": 32,
            "pivot_x": 0.5,
            "pivot_y": 0.5,
            "flip_x": False,
            "flip_y": False,
            "sorting_layer": 0,
            "sorting_order": 0,
            "visible": True,
        },
        "required_components": ["Transform"],
        "incompatible_components": [],
        "description": "2D visual representation of an entity with texture and color properties.",
    },
    "Rigidbody": {
        "name": "Rigidbody",
        "category": ComponentCategory.PHYSICS,
        "default_data": {
            "mass": 1.0,
            "drag": 0.0,
            "angular_drag": 0.05,
            "gravity_scale": 1.0,
            "is_kinematic": False,
            "velocity_x": 0.0,
            "velocity_y": 0.0,
            "angular_velocity": 0.0,
            "constraints": "none",
            "sleep_threshold": 0.005,
            "interpolation": "none",
        },
        "required_components": ["Transform"],
        "incompatible_components": [],
        "description": "Physics-driven motion with mass, drag, and velocity properties.",
    },
    "Collider": {
        "name": "Collider",
        "category": ComponentCategory.PHYSICS,
        "default_data": {
            "shape": "box",
            "width": 32.0,
            "height": 32.0,
            "radius": 16.0,
            "offset_x": 0.0,
            "offset_y": 0.0,
            "is_trigger": False,
            "physics_material": "default",
            "layer": 0,
            "sensor": False,
        },
        "required_components": ["Transform"],
        "incompatible_components": [],
        "description": "Collision boundary for entity with configurable shape and trigger behavior.",
    },
    "Health": {
        "name": "Health",
        "category": ComponentCategory.LIFECYCLE,
        "default_data": {
            "current_health": 100.0,
            "max_health": 100.0,
            "armor": 0.0,
            "shield": 0.0,
            "invulnerable": False,
            "invulnerability_duration": 0.0,
            "health_regen_rate": 0.0,
            "destroy_on_death": True,
            "death_delay": 0.0,
        },
        "required_components": [],
        "incompatible_components": [],
        "description": "Health and damage tracking with regeneration and death handling.",
    },
    "Animator": {
        "name": "Animator",
        "category": ComponentCategory.ANIMATION,
        "default_data": {
            "controller_id": "",
            "current_state": "idle",
            "speed": 1.0,
            "transition_time": 0.15,
            "parameters": {},
            "layer_count": 1,
            "apply_root_motion": False,
            "culling_mode": "always_animate",
            "update_mode": "normal",
        },
        "required_components": ["Transform"],
        "incompatible_components": [],
        "description": "Animation state machine controlling visual playback and transitions.",
    },
    "AIBrain": {
        "name": "AIBrain",
        "category": ComponentCategory.AI,
        "default_data": {
            "behavior_tree_id": "",
            "state": "idle",
            "detection_range": 200.0,
            "attack_range": 50.0,
            "patrol_path": [],
            "patrol_speed": 100.0,
            "chase_speed": 200.0,
            "target_entity_id": "",
            "awareness_level": 0.0,
            "decision_interval": 0.5,
            "team_id": 0,
            "personality_seed": 0.0,
        },
        "required_components": ["Transform"],
        "incompatible_components": [],
        "description": "AI decision-making component with behavior tree support and team awareness.",
    },
}


# ---------------------------------------------------------------------------
# Pre-Defined Entity Archetypes
# ---------------------------------------------------------------------------

_PREDEFINED_ARCHETYPES: Dict[str, Dict[str, Any]] = {
    "Player": {
        "name": "Player",
        "component_categories": [
            ComponentCategory.TRANSFORM,
            ComponentCategory.RENDER,
            ComponentCategory.PHYSICS,
            ComponentCategory.PHYSICS,
            ComponentCategory.LIFECYCLE,
            ComponentCategory.ANIMATION,
            ComponentCategory.INPUT,
        ],
        "defaults": {
            "transform": {"position_x": 0.0, "position_y": 0.0, "scale_x": 1.0, "scale_y": 1.0},
            "sprite": {"texture_id": "player_sprite", "width": 32, "height": 64},
            "rigidbody": {"mass": 70.0, "gravity_scale": 1.0, "drag": 0.2},
            "collider": {"shape": "capsule", "width": 32, "height": 64},
            "health": {"current_health": 100.0, "max_health": 100.0},
            "animator": {"controller_id": "player_anim_controller"},
        },
        "description": "Player-controlled character with full movement, combat, and animation systems.",
        "category": "character",
    },
    "Enemy": {
        "name": "Enemy",
        "component_categories": [
            ComponentCategory.TRANSFORM,
            ComponentCategory.RENDER,
            ComponentCategory.PHYSICS,
            ComponentCategory.PHYSICS,
            ComponentCategory.LIFECYCLE,
            ComponentCategory.ANIMATION,
            ComponentCategory.AI,
        ],
        "defaults": {
            "transform": {"position_x": 0.0, "position_y": 0.0, "scale_x": 1.0, "scale_y": 1.0},
            "sprite": {"texture_id": "enemy_sprite", "width": 48, "height": 48},
            "rigidbody": {"mass": 50.0, "gravity_scale": 1.0, "drag": 0.1},
            "collider": {"shape": "box", "width": 48, "height": 48},
            "health": {"current_health": 50.0, "max_health": 50.0},
            "animator": {"controller_id": "enemy_anim_controller"},
            "ai_brain": {"state": "patrol", "patrol_speed": 80.0, "detection_range": 200.0},
        },
        "description": "AI-driven enemy with patrol, detection, and combat behaviors.",
        "category": "character",
    },
    "Projectile": {
        "name": "Projectile",
        "component_categories": [
            ComponentCategory.TRANSFORM,
            ComponentCategory.RENDER,
            ComponentCategory.PHYSICS,
            ComponentCategory.PHYSICS,
            ComponentCategory.LIFECYCLE,
        ],
        "defaults": {
            "transform": {"position_x": 0.0, "position_y": 0.0, "scale_x": 0.5, "scale_y": 0.5},
            "sprite": {"texture_id": "projectile_sprite", "width": 16, "height": 16},
            "rigidbody": {"mass": 0.1, "gravity_scale": 0.0, "drag": 0.0},
            "collider": {"shape": "circle", "radius": 8.0, "is_trigger": True},
            "health": {"current_health": 1.0, "max_health": 1.0, "destroy_on_death": True},
        },
        "description": "Fast-moving projectile with trigger-based collision and single-hit destruction.",
        "category": "projectile",
    },
    "Collectible": {
        "name": "Collectible",
        "component_categories": [
            ComponentCategory.TRANSFORM,
            ComponentCategory.RENDER,
            ComponentCategory.PHYSICS,
            ComponentCategory.LIFECYCLE,
        ],
        "defaults": {
            "transform": {"position_x": 0.0, "position_y": 0.0, "scale_x": 1.0, "scale_y": 1.0},
            "sprite": {"texture_id": "collectible_sprite", "width": 24, "height": 24, "color_r": 255, "color_g": 215, "color_b": 0},
            "collider": {"shape": "circle", "radius": 16.0, "is_trigger": True},
            "health": {"current_health": 1.0, "max_health": 1.0, "destroy_on_death": True},
        },
        "description": "Pickup item with trigger-based collection and auto-destruction on pickup.",
        "category": "item",
    },
}


# ---------------------------------------------------------------------------
# EngineEntityComponentSystem — Thread-Safe Singleton
# ---------------------------------------------------------------------------


class EngineEntityComponentSystem:
    """High-performance ECS architecture for game object management.

    Entities are lightweight identifiers composed of data-only Components.
    Systems contain processing logic and operate on entities that possess
    matching component sets. ComponentBlueprints define reusable templates,
    and EntityArchetypes provide pre-configured entity compositions.

    Thread-safe via a reentrant lock. Use get_entity_component_system() or
    EngineEntityComponentSystem.get_instance() to obtain the singleton.

    Usage:
        ecs = get_entity_component_system()
        entity_id = ecs.create_entity("Hero", "player")
        ecs.add_component(entity_id, ComponentCategory.TRANSFORM,
                          {"position_x": 100.0, "position_y": 200.0})
        ecs.add_component(entity_id, ComponentCategory.RENDER,
                          {"texture_id": "hero_sprite", "visible": True})
        system_id = ecs.register_system("MovementSystem",
                                        ["Transform"], ComponentUpdatePhase.UPDATE)
        results = ecs.process_system(system_id)
    """

    _instance: Optional["EngineEntityComponentSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineEntityComponentSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._world: World = World(name="default_world")
        self._archetypes: Dict[str, EntityArchetype] = {}
        self._frame_counter: int = 0
        self._component_type_index: Dict[str, List[str]] = {}
        self._entity_tag_index: Dict[str, List[str]] = {}
        self._operation_log: List[Dict[str, Any]] = []
        self._initialized = True

    @classmethod
    def get_instance(cls) -> "EngineEntityComponentSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Entity Management
    # ------------------------------------------------------------------

    def create_entity(
        self,
        name: str = "",
        tag: str = "",
        parent_id: str = "",
    ) -> str:
        _time_module.sleep(0.001)
        entity = Entity(
            name=name,
            tag=tag,
            creation_frame=self._frame_counter,
            last_update_frame=self._frame_counter,
        )
        self._world.entities[entity.id] = entity

        if tag:
            self._entity_tag_index.setdefault(tag, []).append(entity.id)

        if parent_id and parent_id in self._world.entities:
            self._world.entity_hierarchy[entity.id] = parent_id

        self._operation_log.append({
            "action": "create_entity",
            "entity_id": entity.id,
            "name": name,
            "tag": tag,
            "parent_id": parent_id,
            "frame": self._frame_counter,
        })
        return entity.id

    def destroy_entity(self, entity_id: str) -> bool:
        _time_module.sleep(0.001)
        entity = self._world.entities.get(entity_id)
        if entity is None:
            return False

        child_ids = [
            cid for cid, pid in self._world.entity_hierarchy.items()
            if pid == entity_id
        ]
        for child_id in child_ids:
            self.destroy_entity(child_id)

        component_ids_to_remove = list(entity.components.values())
        for comp_id in component_ids_to_remove:
            self._remove_component_internal(entity_id, comp_id)

        if entity.tag and entity.tag in self._entity_tag_index:
            self._entity_tag_index[entity.tag] = [
                eid for eid in self._entity_tag_index[entity.tag]
                if eid != entity_id
            ]

        self._world.entity_hierarchy.pop(entity_id, None)
        del self._world.entities[entity_id]

        self._operation_log.append({
            "action": "destroy_entity",
            "entity_id": entity_id,
            "frame": self._frame_counter,
        })
        return True

    def _remove_component_internal(self, entity_id: str, component_id: str) -> bool:
        _time_module.sleep(0.001)
        if component_id not in self._world.component_registry:
            return False
        component = self._world.component_registry[component_id]
        cat_value = component.category.value
        del self._world.component_registry[component_id]
        if cat_value in self._component_type_index:
            self._component_type_index[cat_value] = [
                cid for cid in self._component_type_index[cat_value]
                if cid != component_id
            ]
        entity = self._world.entities.get(entity_id)
        if entity is not None:
            entity.components.pop(cat_value, None)
        for system in self._world.systems.values():
            if entity_id in system.entities_list:
                system.entities_list.remove(entity_id)
        return True

    # ------------------------------------------------------------------
    # Component Management
    # ------------------------------------------------------------------

    def add_component(
        self,
        entity_id: str,
        component_category: ComponentCategory,
        data: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        entity = self._world.entities.get(entity_id)
        if entity is None:
            return None

        cat_value = component_category.value
        if cat_value in entity.components:
            return None

        component = Component(
            entity_id=entity_id,
            category=component_category,
            data=dict(data) if data else {},
        )
        self._world.component_registry[component.id] = component
        self._component_type_index.setdefault(cat_value, []).append(component.id)
        entity.components[cat_value] = component.id
        entity.last_update_frame = self._frame_counter

        self._operation_log.append({
            "action": "add_component",
            "entity_id": entity_id,
            "component_id": component.id,
            "category": cat_value,
            "frame": self._frame_counter,
        })
        return component.id

    def remove_component(self, entity_id: str, component_id: str) -> bool:
        _time_module.sleep(0.001)
        return self._remove_component_internal(entity_id, component_id)

    def get_component(
        self,
        entity_id: str,
        category: ComponentCategory,
    ) -> Optional[Component]:
        _time_module.sleep(0.001)
        entity = self._world.entities.get(entity_id)
        if entity is None:
            return None
        component_id = entity.components.get(category.value)
        if component_id is None:
            return None
        return self._world.component_registry.get(component_id)

    # ------------------------------------------------------------------
    # Blueprint Management
    # ------------------------------------------------------------------

    def register_blueprint(
        self,
        name: str,
        category: ComponentCategory,
        default_data: Optional[Dict[str, Any]] = None,
        required_components: Optional[List[str]] = None,
        incompatible_components: Optional[List[str]] = None,
        description: str = "",
    ) -> str:
        _time_module.sleep(0.001)
        blueprint = ComponentBlueprint(
            name=name,
            category=category,
            default_data=dict(default_data) if default_data else {},
            required_components=list(required_components) if required_components else [],
            incompatible_components=list(incompatible_components) if incompatible_components else [],
            description=description,
        )
        self._world.blueprint_registry[blueprint.id] = blueprint
        return blueprint.id

    def create_from_blueprint(self, entity_id: str, blueprint_id: str) -> bool:
        _time_module.sleep(0.001)
        entity = self._world.entities.get(entity_id)
        if entity is None:
            return False

        blueprint = self._world.blueprint_registry.get(blueprint_id)
        if blueprint is None:
            return False

        for required in blueprint.required_components:
            if required not in entity.components:
                return False

        for incompatible in blueprint.incompatible_components:
            if incompatible in entity.components:
                return False

        component_id = self.add_component(
            entity_id=entity_id,
            component_category=blueprint.category,
            data=dict(blueprint.default_data),
        )

        self._operation_log.append({
            "action": "create_from_blueprint",
            "entity_id": entity_id,
            "blueprint_id": blueprint_id,
            "component_id": component_id,
            "frame": self._frame_counter,
        })
        return component_id is not None

    # ------------------------------------------------------------------
    # System Management
    # ------------------------------------------------------------------

    def register_system(
        self,
        name: str,
        required_components: List[str],
        update_phase: ComponentUpdatePhase = ComponentUpdatePhase.UPDATE,
        execution_order: SystemExecutionOrder = SystemExecutionOrder.NORMAL,
        priority: int = 0,
    ) -> str:
        _time_module.sleep(0.001)
        system_obj = System(
            name=name,
            required_components=list(required_components),
            update_phase=update_phase,
            execution_order=execution_order,
            priority=priority,
        )
        self._world.systems[system_obj.id] = system_obj

        self._rebuild_system_entity_list(system_obj.id)

        self._operation_log.append({
            "action": "register_system",
            "system_id": system_obj.id,
            "name": name,
            "phase": update_phase.value,
            "frame": self._frame_counter,
        })
        return system_obj.id

    def _rebuild_system_entity_list(self, system_id: str) -> None:
        _time_module.sleep(0.001)
        system_obj = self._world.systems.get(system_id)
        if system_obj is None:
            return
        matching_entities: List[str] = []
        for entity in self._world.entities.values():
            if not entity.active:
                continue
            if all(rc in entity.components for rc in system_obj.required_components):
                matching_entities.append(entity.id)
        system_obj.entities_list = matching_entities

    def process_system(self, system_id: str) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        system_obj = self._world.systems.get(system_id)
        if system_obj is None:
            return {"success": False, "error": "system_not_found", "system_id": system_id}

        if not system_obj.active:
            return {"success": False, "error": "system_inactive", "system_id": system_id}

        start_time = _time_module.perf_counter()
        self._frame_counter += 1

        self._rebuild_system_entity_list(system_id)

        processed_count = 0
        skipped_count = 0
        for entity_id in system_obj.entities_list:
            entity = self._world.entities.get(entity_id)
            if entity is None or not entity.active:
                skipped_count += 1
                continue
            entity.last_update_frame = self._frame_counter
            processed_count += 1

        elapsed_ms = (_time_module.perf_counter() - start_time) * 1000.0
        system_obj.performance_stats = {
            "last_processed": processed_count,
            "last_skipped": skipped_count,
            "last_elapsed_ms": round(elapsed_ms, 3),
            "total_entities": len(system_obj.entities_list),
            "frame": self._frame_counter,
        }

        return {
            "success": True,
            "system_id": system_id,
            "system_name": system_obj.name,
            "processed": processed_count,
            "skipped": skipped_count,
            "elapsed_ms": round(elapsed_ms, 3),
            "frame": self._frame_counter,
        }

    # ------------------------------------------------------------------
    # Archetype Management
    # ------------------------------------------------------------------

    def create_archetype(
        self,
        name: str,
        component_categories: List[ComponentCategory],
        defaults: Optional[Dict[str, Any]] = None,
        description: str = "",
        category: str = "",
    ) -> str:
        _time_module.sleep(0.001)
        template_components: List[ComponentBlueprint] = []
        for comp_cat in component_categories:
            blueprint = ComponentBlueprint(
                name=f"{name}_{comp_cat.value}",
                category=comp_cat,
                default_data=dict(defaults.get(comp_cat.value, {})) if defaults else {},
            )
            template_components.append(blueprint)

        archetype = EntityArchetype(
            name=name,
            template_components=template_components,
            default_values=dict(defaults) if defaults else {},
            description=description,
            category=category,
        )
        self._archetypes[archetype.id] = archetype

        self._operation_log.append({
            "action": "create_archetype",
            "archetype_id": archetype.id,
            "name": name,
            "component_count": len(component_categories),
            "frame": self._frame_counter,
        })
        return archetype.id

    def instantiate_archetype(
        self,
        archetype_id: str,
        name: str = "",
        tag: str = "",
        parent_id: str = "",
    ) -> Optional[str]:
        _time_module.sleep(0.001)
        archetype = self._archetypes.get(archetype_id)
        if archetype is None:
            return None

        entity_id = self.create_entity(
            name=name or archetype.name,
            tag=tag or archetype.name.lower(),
            parent_id=parent_id,
        )

        for blueprint in archetype.template_components:
            merged_data = dict(blueprint.default_data)
            if archetype.default_values and blueprint.category.value in archetype.default_values:
                merged_data.update(archetype.default_values[blueprint.category.value])
            self.add_component(
                entity_id=entity_id,
                component_category=blueprint.category,
                data=merged_data,
            )

        self._operation_log.append({
            "action": "instantiate_archetype",
            "archetype_id": archetype_id,
            "entity_id": entity_id,
            "archetype_name": archetype.name,
            "frame": self._frame_counter,
        })
        return entity_id

    # ------------------------------------------------------------------
    # Hierarchy Management
    # ------------------------------------------------------------------

    def set_parent(self, entity_id: str, parent_id: str) -> bool:
        _time_module.sleep(0.001)
        if entity_id == parent_id:
            return False

        entity = self._world.entities.get(entity_id)
        if entity is None:
            return False

        if parent_id and parent_id not in self._world.entities:
            return False

        if parent_id and self._is_descendant_of(parent_id, entity_id):
            return False

        self._world.entity_hierarchy[entity_id] = parent_id

        self._operation_log.append({
            "action": "set_parent",
            "entity_id": entity_id,
            "parent_id": parent_id,
            "frame": self._frame_counter,
        })
        return True

    def _is_descendant_of(self, ancestor_id: str, target_id: str) -> bool:
        _time_module.sleep(0.001)
        visited: set = set()
        current = target_id
        while current:
            if current == ancestor_id:
                return True
            if current in visited:
                return False
            visited.add(current)
            current = self._world.entity_hierarchy.get(current, "")
        return False

    # ------------------------------------------------------------------
    # Pre-Defined Blueprint Loading
    # ------------------------------------------------------------------

    def load_predefined_blueprint(self, blueprint_key: str) -> Optional[str]:
        _time_module.sleep(0.001)
        preset = _PREDEFINED_BLUEPRINTS.get(blueprint_key)
        if preset is None:
            return None
        return self.register_blueprint(
            name=preset["name"],
            category=preset["category"],
            default_data=preset["default_data"],
            required_components=preset["required_components"],
            incompatible_components=preset["incompatible_components"],
            description=preset["description"],
        )

    def load_predefined_archetype(self, archetype_key: str) -> Optional[str]:
        _time_module.sleep(0.001)
        preset = _PREDEFINED_ARCHETYPES.get(archetype_key)
        if preset is None:
            return None
        return self.create_archetype(
            name=preset["name"],
            component_categories=preset["component_categories"],
            defaults=preset["defaults"],
            description=preset["description"],
            category=preset["category"],
        )

    def load_all_predefined_blueprints(self) -> List[str]:
        _time_module.sleep(0.001)
        blueprint_ids: List[str] = []
        for key in _PREDEFINED_BLUEPRINTS:
            bp_id = self.load_predefined_blueprint(key)
            if bp_id is not None:
                blueprint_ids.append(bp_id)
        return blueprint_ids

    def load_all_predefined_archetypes(self) -> List[str]:
        _time_module.sleep(0.001)
        archetype_ids: List[str] = []
        for key in _PREDEFINED_ARCHETYPES:
            arch_id = self.load_predefined_archetype(key)
            if arch_id is not None:
                archetype_ids.append(arch_id)
        return archetype_ids

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_entity(self, entity_id: str) -> Optional[Entity]:
        _time_module.sleep(0.001)
        return self._world.entities.get(entity_id)

    def find_entities_by_tag(self, tag: str) -> List[Entity]:
        _time_module.sleep(0.001)
        entity_ids = self._entity_tag_index.get(tag, [])
        return [
            self._world.entities[eid] for eid in entity_ids
            if eid in self._world.entities
        ]

    def get_children(self, entity_id: str) -> List[Entity]:
        _time_module.sleep(0.001)
        child_ids = [
            cid for cid, pid in self._world.entity_hierarchy.items()
            if pid == entity_id
        ]
        return [
            self._world.entities[cid] for cid in child_ids
            if cid in self._world.entities
        ]

    def get_world(self) -> World:
        _time_module.sleep(0.001)
        return self._world

    def get_all_archetypes(self) -> List[EntityArchetype]:
        _time_module.sleep(0.001)
        return list(self._archetypes.values())

    def get_archetype(self, archetype_id: str) -> Optional[EntityArchetype]:
        _time_module.sleep(0.001)
        return self._archetypes.get(archetype_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)
        component_category_counts: Dict[str, int] = {}
        for comp in self._world.component_registry.values():
            cat = comp.category.value
            component_category_counts[cat] = component_category_counts.get(cat, 0) + 1

        active_entities = sum(
            1 for e in self._world.entities.values() if e.active
        )

        phase_distribution: Dict[str, int] = {}
        for system_obj in self._world.systems.values():
            ph = system_obj.update_phase.value
            phase_distribution[ph] = phase_distribution.get(ph, 0) + 1

        total_system_entities = sum(
            len(s.entities_list) for s in self._world.systems.values()
        )

        hierarchy_depth = 0
        for entity_id in self._world.entities:
            depth = 0
            current = entity_id
            visited: set = set()
            while current in self._world.entity_hierarchy:
                if current in visited:
                    break
                visited.add(current)
                current = self._world.entity_hierarchy[current]
                depth += 1
            if depth > hierarchy_depth:
                hierarchy_depth = depth

        root_entities = sum(
            1 for eid in self._world.entities
            if eid not in self._world.entity_hierarchy
        )

        return {
            "total_entities": len(self._world.entities),
            "active_entities": active_entities,
            "total_components": len(self._world.component_registry),
            "component_category_distribution": component_category_counts,
            "total_systems": len(self._world.systems),
            "system_phase_distribution": phase_distribution,
            "total_system_entity_references": total_system_entities,
            "total_blueprints": len(self._world.blueprint_registry),
            "total_archetypes": len(self._archetypes),
            "predefined_blueprints": list(_PREDEFINED_BLUEPRINTS.keys()),
            "predefined_archetypes": list(_PREDEFINED_ARCHETYPES.keys()),
            "hierarchy_entries": len(self._world.entity_hierarchy),
            "max_hierarchy_depth": hierarchy_depth,
            "root_entities": root_entities,
            "event_queue_size": len(self._world.event_queue),
            "frame_counter": self._frame_counter,
            "operation_log_entries": len(self._operation_log),
            "tag_groups": len(self._entity_tag_index),
        }

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        _time_module.sleep(0.001)
        with self._lock:
            self._world = World(name="default_world")
            self._archetypes.clear()
            self._frame_counter = 0
            self._component_type_index.clear()
            self._entity_tag_index.clear()
            self._operation_log.clear()


# ---------------------------------------------------------------------------
# Module-Level Accessor
# ---------------------------------------------------------------------------


def get_entity_component_system() -> EngineEntityComponentSystem:
    return EngineEntityComponentSystem.get_instance()