"""
SparkLabs Engine - Component Assembler

A composition-based entity assembly system
node-composition model and behavior system. Entities
are constructed by assembling reusable ComponentBlueprints into
EntityArchetypes, then instantiating AssembledEntity instances
with runtime state management and hierarchical parent/child trees.

Architecture:
  ComponentAssembler
    |-- ComponentBlueprint (reusable typed component definition)
    |-- EntityArchetype (named entity template composed of components)
    |-- AssembledEntity (runtime entity instance with state and hierarchy)
    |-- Dependency Validator (ensures component dependency chains are met)
    |-- Conflict Detector (flags incompatible component combinations)
    |-- Entity Tree Manager (tracks parent/child entity relationships)
    |-- Template Instantiation (quick-create from predefined EntityTemplate)
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class ComponentType(Enum):
    TRANSFORM = "transform"
    RENDERER = "renderer"
    COLLIDER = "collider"
    RIGIDBODY = "rigidbody"
    ANIMATOR = "animator"
    SCRIPT = "script"
    AUDIO_SOURCE = "audio_source"
    LIGHT = "light"
    CAMERA = "camera"
    UI_ELEMENT = "ui_element"
    PARTICLE_EMITTER = "particle_emitter"
    NAVIGATION = "navigation"
    CUSTOM = "custom"


class EntityTemplate(Enum):
    PLAYER_CHARACTER = "player_character"
    ENEMY = "enemy"
    COLLECTIBLE = "collectible"
    PLATFORM = "platform"
    DOOR = "door"
    TRIGGER_ZONE = "trigger_zone"
    UI_PANEL = "ui_panel"
    PARTICLE_SYSTEM = "particle_system"
    CAMERA_RIG = "camera_rig"
    LIGHT_SOURCE = "light_source"


# ---------------------------------------------------------------------------
# Incompatibility Rules (Conflict Detection)
# ---------------------------------------------------------------------------

_INCOMPATIBLE_PAIRS: Set[Tuple[ComponentType, ComponentType]] = {
    (ComponentType.RIGIDBODY, ComponentType.NAVIGATION),
    (ComponentType.COLLIDER, ComponentType.UI_ELEMENT),
    (ComponentType.CAMERA, ComponentType.LIGHT),
    (ComponentType.AUDIO_SOURCE, ComponentType.UI_ELEMENT),
    (ComponentType.PARTICLE_EMITTER, ComponentType.UI_ELEMENT),
    (ComponentType.RIGIDBODY, ComponentType.UI_ELEMENT),
    (ComponentType.NAVIGATION, ComponentType.PARTICLE_EMITTER),
}

_SINGLETON_COMPONENTS: Set[ComponentType] = {
    ComponentType.TRANSFORM,
    ComponentType.RIGIDBODY,
    ComponentType.CAMERA,
    ComponentType.NAVIGATION,
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ComponentBlueprint:
    """Reusable, typed component definition with dependency and capability metadata."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    component_type: ComponentType = ComponentType.SCRIPT
    properties: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    version: int = 1
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "component_type": self.component_type.value,
            "properties": dict(self.properties),
            "dependencies": list(self.dependencies),
            "provides": list(self.provides),
            "version": self.version,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class EntityArchetype:
    """Named entity template composed of ComponentBlueprints with optional inheritance."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    components: List[ComponentBlueprint] = field(default_factory=list)
    inherits_from: str = ""
    category: str = ""
    description: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "component_count": len(self.components),
            "components": [c.to_dict() for c in self.components],
            "inherits_from": self.inherits_from,
            "category": self.category,
            "description": self.description,
            "created_at": self.created_at,
        }


@dataclass
class AssembledEntity:
    """Runtime entity instance assembled from an archetype with state and tree hierarchy."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    archetype_id: str = ""
    components: List[str] = field(default_factory=list)
    state: Dict[str, Any] = field(default_factory=dict)
    parent_entity_id: str = ""
    children_ids: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "archetype_id": self.archetype_id,
            "components": list(self.components),
            "state": dict(self.state),
            "parent_entity_id": self.parent_entity_id,
            "children_ids": list(self.children_ids),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Preset Template Definitions
# ---------------------------------------------------------------------------

_PRESET_TEMPLATE_COMPONENTS: Dict[EntityTemplate, List[Tuple[str, ComponentType, Dict[str, Any], List[str], List[str], List[str]]]] = {
    EntityTemplate.PLAYER_CHARACTER: [
        ("player_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0), "layer": 0}, [], ["transform"], ["player", "core"]),
        ("player_renderer", ComponentType.RENDERER, {"sprite": "player_default", "color": "#00FF00"}, ["transform"], ["render"], ["player", "visual"]),
        ("player_collider", ComponentType.COLLIDER, {"shape": "capsule", "width": 32, "height": 64}, ["transform"], ["collision"], ["player", "physics"]),
        ("player_rigidbody", ComponentType.RIGIDBODY, {"mass": 70.0, "gravity_scale": 1.0}, ["transform"], ["physics_body"], ["player", "physics"]),
        ("player_animator", ComponentType.ANIMATOR, {"controller": "player_anim_ctrl"}, ["render"], ["animation"], ["player", "visual"]),
        ("player_script", ComponentType.SCRIPT, {"move_speed": 300.0, "jump_force": 600.0}, ["transform", "rigidbody"], ["player_controller"], ["player", "logic"]),
    ],
    EntityTemplate.ENEMY: [
        ("enemy_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0), "layer": 1}, [], ["transform"], ["enemy", "core"]),
        ("enemy_renderer", ComponentType.RENDERER, {"sprite": "enemy_default", "color": "#FF0000"}, ["transform"], ["render"], ["enemy", "visual"]),
        ("enemy_collider", ComponentType.COLLIDER, {"shape": "box", "width": 48, "height": 48}, ["transform"], ["collision"], ["enemy", "physics"]),
        ("enemy_rigidbody", ComponentType.RIGIDBODY, {"mass": 50.0, "gravity_scale": 1.0}, ["transform"], ["physics_body"], ["enemy", "physics"]),
        ("enemy_animator", ComponentType.ANIMATOR, {"controller": "enemy_anim_ctrl"}, ["render"], ["animation"], ["enemy", "visual"]),
        ("enemy_script", ComponentType.SCRIPT, {"patrol_speed": 100.0, "detection_range": 200.0}, ["transform", "rigidbody"], ["enemy_ai"], ["enemy", "logic"]),
    ],
    EntityTemplate.COLLECTIBLE: [
        ("collectible_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["collectible", "core"]),
        ("collectible_renderer", ComponentType.RENDERER, {"sprite": "collectible_default", "color": "#FFD700"}, ["transform"], ["render"], ["collectible", "visual"]),
        ("collectible_collider", ComponentType.COLLIDER, {"shape": "circle", "radius": 16, "is_trigger": True}, ["transform"], ["collision"], ["collectible", "physics"]),
        ("collectible_script", ComponentType.SCRIPT, {"pickup_range": 80.0, "auto_rotate": True, "bob_amplitude": 4.0}, ["transform"], ["collectible_behavior"], ["collectible", "logic"]),
    ],
    EntityTemplate.PLATFORM: [
        ("platform_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["platform", "core"]),
        ("platform_renderer", ComponentType.RENDERER, {"sprite": "platform_default", "color": "#888888"}, ["transform"], ["render"], ["platform", "visual"]),
        ("platform_collider", ComponentType.COLLIDER, {"shape": "box", "width": 128, "height": 32, "is_trigger": False}, ["transform"], ["collision"], ["platform", "physics"]),
    ],
    EntityTemplate.DOOR: [
        ("door_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["door", "core"]),
        ("door_renderer", ComponentType.RENDERER, {"sprite": "door_default", "color": "#8B4513"}, ["transform"], ["render"], ["door", "visual"]),
        ("door_collider", ComponentType.COLLIDER, {"shape": "box", "width": 64, "height": 96, "is_trigger": False}, ["transform"], ["collision"], ["door", "physics"]),
        ("door_animator", ComponentType.ANIMATOR, {"controller": "door_anim_ctrl"}, ["render"], ["animation"], ["door", "visual"]),
        ("door_script", ComponentType.SCRIPT, {"is_locked": False, "key_item_id": ""}, ["transform"], ["door_controller"], ["door", "logic"]),
    ],
    EntityTemplate.TRIGGER_ZONE: [
        ("trigger_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["trigger", "core"]),
        ("trigger_collider", ComponentType.COLLIDER, {"shape": "box", "width": 64, "height": 64, "is_trigger": True}, ["transform"], ["collision"], ["trigger", "physics"]),
        ("trigger_script", ComponentType.SCRIPT, {"trigger_tag": "player", "trigger_once": True, "event_name": "on_enter"}, ["transform"], ["trigger_handler"], ["trigger", "logic"]),
    ],
    EntityTemplate.UI_PANEL: [
        ("ui_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["ui", "core"]),
        ("ui_element", ComponentType.UI_ELEMENT, {"anchor": "center", "width": 400, "height": 300}, ["transform"], ["ui_layout"], ["ui", "layout"]),
        ("ui_renderer", ComponentType.RENDERER, {"sprite": "panel_default", "color": "#333333"}, ["transform"], ["render"], ["ui", "visual"]),
    ],
    EntityTemplate.PARTICLE_SYSTEM: [
        ("particle_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["particle", "core"]),
        ("particle_emitter", ComponentType.PARTICLE_EMITTER, {"max_particles": 200, "emission_rate": 50.0, "lifetime": 2.0}, ["transform"], ["particle_emission"], ["particle", "core"]),
        ("particle_renderer", ComponentType.RENDERER, {"sprite": "particle_default", "color": "#FFFFFF"}, ["transform"], ["render"], ["particle", "visual"]),
    ],
    EntityTemplate.CAMERA_RIG: [
        ("camera_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["camera", "core"]),
        ("camera_component", ComponentType.CAMERA, {"fov": 60.0, "near": 0.1, "far": 1000.0, "orthographic": False}, ["transform"], ["camera_view"], ["camera", "core"]),
        ("camera_script", ComponentType.SCRIPT, {"follow_target": "", "smooth_speed": 5.0, "offset_x": 0.0, "offset_y": 0.0}, ["transform", "camera"], ["camera_controller"], ["camera", "logic"]),
    ],
    EntityTemplate.LIGHT_SOURCE: [
        ("light_transform", ComponentType.TRANSFORM, {"position": (0.0, 0.0)}, [], ["transform"], ["light", "core"]),
        ("light_component", ComponentType.LIGHT, {"intensity": 1.0, "color": "#FFFFFF", "range": 300.0, "shadow_casting": False}, ["transform"], ["illumination"], ["light", "core"]),
    ],
}


# ---------------------------------------------------------------------------
# Component Assembler (Singleton via __new__)
# ---------------------------------------------------------------------------


class ComponentAssembler:
    """Composition-based entity assembly system for defining and instantiating game entities."""

    _instance: Optional["ComponentAssembler"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "ComponentAssembler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        with self._lock:
            if not hasattr(self, "_initialized"):
                self._component_registry: Dict[str, ComponentBlueprint] = {}
                self._archetypes: Dict[str, EntityArchetype] = {}
                self._entities: Dict[str, AssembledEntity] = {}
                self._component_name_index: Dict[str, List[str]] = {}
                self._entity_parent_index: Dict[str, str] = {}
                self._assembly_log: List[Dict[str, Any]] = []
                self._assembly_count: int = 0
                self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "ComponentAssembler":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Component Registration
    # ------------------------------------------------------------------

    def register_component(
        self,
        name: str,
        component_type: str = "script",
        properties: Optional[Dict[str, Any]] = None,
        dependencies: Optional[List[str]] = None,
        provides: Optional[List[str]] = None,
        version: int = 1,
        tags: Optional[List[str]] = None,
    ) -> ComponentBlueprint:
        """Register a reusable component blueprint in the global registry.

        Each component declares what capabilities it *provides* and what
        capabilities it *depends on*.  The dependency validator uses these
        fields to ensure entity validity during assembly.
        """
        try:
            ctype = ComponentType(component_type.lower())
        except ValueError:
            ctype = ComponentType.CUSTOM

        blueprint = ComponentBlueprint(
            name=name,
            component_type=ctype,
            properties=dict(properties) if properties else {},
            dependencies=list(dependencies) if dependencies else [],
            provides=list(provides) if provides else [],
            version=version,
            tags=list(tags) if tags else [],
        )
        self._component_registry[blueprint.id] = blueprint
        self._component_name_index.setdefault(name.lower(), []).append(blueprint.id)
        return blueprint

    def get_component(self, component_id: str) -> Optional[ComponentBlueprint]:
        return self._component_registry.get(component_id)

    def find_components_by_name(self, name: str) -> List[ComponentBlueprint]:
        ids = self._component_name_index.get(name.lower(), [])
        return [self._component_registry[cid] for cid in ids if cid in self._component_registry]

    def find_components_by_type(self, component_type: str) -> List[ComponentBlueprint]:
        try:
            ctype = ComponentType(component_type.lower())
        except ValueError:
            return []
        return [c for c in self._component_registry.values() if c.component_type == ctype]

    def unregister_component(self, component_id: str) -> bool:
        if component_id not in self._component_registry:
            return False
        blueprint = self._component_registry[component_id]
        name_key = blueprint.name.lower()
        if name_key in self._component_name_index:
            self._component_name_index[name_key] = [
                cid for cid in self._component_name_index[name_key] if cid != component_id
            ]
            if not self._component_name_index[name_key]:
                del self._component_name_index[name_key]
        del self._component_registry[component_id]
        return True

    def update_component(
        self,
        component_id: str,
        properties: Optional[Dict[str, Any]] = None,
        version: Optional[int] = None,
    ) -> bool:
        blueprint = self._component_registry.get(component_id)
        if blueprint is None:
            return False
        if properties is not None:
            blueprint.properties.update(properties)
        if version is not None:
            blueprint.version = version
        return True

    # ------------------------------------------------------------------
    # Archetype Management
    # ------------------------------------------------------------------

    def create_archetype(
        self,
        name: str,
        component_ids: List[str],
        inherits_from: str = "",
        category: str = "",
        description: str = "",
    ) -> Optional[EntityArchetype]:
        """Define a new entity archetype from a list of registered component IDs.

        Validates that all referenced components exist in the registry
        and that their dependencies are satisfiable within the archetype's
        component set before creation.
        """
        components: List[ComponentBlueprint] = []
        for cid in component_ids:
            comp = self._component_registry.get(cid)
            if comp is None:
                return None
            components.append(comp)

        valid, message = self.validate_dependencies(components)
        if not valid:
            return None

        archetype = EntityArchetype(
            name=name,
            components=list(components),
            inherits_from=inherits_from,
            category=category,
            description=description,
        )
        self._archetypes[archetype.id] = archetype
        return archetype

    def get_archetype(self, archetype_id: str) -> Optional[EntityArchetype]:
        return self._archetypes.get(archetype_id)

    def list_archetypes(self, category: str = "") -> List[EntityArchetype]:
        if not category:
            return list(self._archetypes.values())
        return [a for a in self._archetypes.values() if a.category == category]

    def delete_archetype(self, archetype_id: str) -> bool:
        if archetype_id not in self._archetypes:
            return False
        entity_ids = [
            eid for eid, ent in self._entities.items()
            if ent.archetype_id == archetype_id
        ]
        for eid in entity_ids:
            self._remove_entity(eid)
        del self._archetypes[archetype_id]
        return True

    def get_archetype_components(self, archetype_id: str) -> List[ComponentBlueprint]:
        archetype = self._archetypes.get(archetype_id)
        if archetype is None:
            return []
        return list(archetype.components)

    # ------------------------------------------------------------------
    # Entity Assembly
    # ------------------------------------------------------------------

    def assemble_entity(
        self,
        archetype_id: str,
        parent_entity_id: str = "",
        state_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[AssembledEntity]:
        """Instantiate a new entity from an archetype definition.

        Resolves the full component set (including inheritance) and
        creates an AssembledEntity with the resolved components.
        """
        archetype = self._archetypes.get(archetype_id)
        if archetype is None:
            return None

        resolved_components = self._resolve_archetype_components(archetype)
        valid, message = self.validate_dependencies(resolved_components)
        if not valid:
            return None

        component_ids = [c.id for c in resolved_components]
        now = _time_module.time()

        entity = AssembledEntity(
            archetype_id=archetype_id,
            components=component_ids,
            state=dict(state_overrides) if state_overrides else {},
            parent_entity_id=parent_entity_id,
            created_at=now,
            updated_at=now,
        )
        self._entities[entity.id] = entity

        if parent_entity_id and parent_entity_id in self._entities:
            parent = self._entities[parent_entity_id]
            if entity.id not in parent.children_ids:
                parent.children_ids.append(entity.id)
            self._entity_parent_index[entity.id] = parent_entity_id

        self._assembly_count += 1
        self._assembly_log.append({
            "action": "assemble",
            "entity_id": entity.id,
            "archetype_id": archetype_id,
            "component_count": len(component_ids),
            "parent_entity_id": parent_entity_id,
            "timestamp": now,
        })
        return entity

    def _resolve_archetype_components(
        self,
        archetype: EntityArchetype,
        visited: Optional[Set[str]] = None,
    ) -> List[ComponentBlueprint]:
        if visited is None:
            visited = set()
        if archetype.id in visited:
            return list(archetype.components)
        visited.add(archetype.id)

        components: Dict[str, ComponentBlueprint] = {}
        if archetype.inherits_from:
            parent = self._archetypes.get(archetype.inherits_from)
            if parent is not None:
                for comp in self._resolve_archetype_components(parent, visited):
                    components.setdefault(comp.id, comp)
        for comp in archetype.components:
            components[comp.id] = comp
        return list(components.values())

    def get_entity(self, entity_id: str) -> Optional[AssembledEntity]:
        return self._entities.get(entity_id)

    def destroy_entity(self, entity_id: str) -> bool:
        return self._remove_entity(entity_id)

    def _remove_entity(self, entity_id: str) -> bool:
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        for child_id in list(entity.children_ids):
            self._remove_entity(child_id)
        if entity.parent_entity_id and entity.parent_entity_id in self._entities:
            parent = self._entities[entity.parent_entity_id]
            if entity_id in parent.children_ids:
                parent.children_ids.remove(entity_id)
        self._entity_parent_index.pop(entity_id, None)
        del self._entities[entity_id]
        return True

    # ------------------------------------------------------------------
    # Add / Remove Component on Entity
    # ------------------------------------------------------------------

    def add_component_to_entity(
        self,
        entity_id: str,
        component_id: str,
    ) -> bool:
        """Attach a registered component to an already-assembled entity.

        Validates that the component exists, is not already attached,
        and that adding it does not violate dependency or conflict rules.
        """
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        if component_id in entity.components:
            return False
        blueprint = self._component_registry.get(component_id)
        if blueprint is None:
            return False

        current_components = [
            self._component_registry[cid] for cid in entity.components
            if cid in self._component_registry
        ]
        current_components.append(blueprint)

        conflicts = self._check_conflicts(current_components)
        if conflicts:
            return False

        entity.components.append(component_id)
        entity.updated_at = _time_module.time()
        return True

    def remove_component_from_entity(
        self,
        entity_id: str,
        component_id: str,
    ) -> bool:
        """Detach a component from an assembled entity.

        Refuses removal if any remaining component depends on the
        capability that the removed component provided.
        """
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        if component_id not in entity.components:
            return False
        blueprint = self._component_registry.get(component_id)
        if blueprint is None:
            entity.components.remove(component_id)
            entity.updated_at = _time_module.time()
            return True

        removed_provides = set(blueprint.provides)
        remaining_after_removal = [
            cid for cid in entity.components if cid != component_id
        ]
        remaining_deps: Set[str] = set()
        for cid in remaining_after_removal:
            comp = self._component_registry.get(cid)
            if comp is not None:
                remaining_deps.update(comp.dependencies)
        if removed_provides & remaining_deps:
            return False

        entity.components.remove(component_id)
        entity.updated_at = _time_module.time()
        return True

    def get_entity_components(self, entity_id: str) -> List[ComponentBlueprint]:
        entity = self._entities.get(entity_id)
        if entity is None:
            return []
        return [
            self._component_registry[cid] for cid in entity.components
            if cid in self._component_registry
        ]

    # ------------------------------------------------------------------
    # Dependency Validation
    # ------------------------------------------------------------------

    def validate_dependencies(
        self,
        components: List[ComponentBlueprint],
    ) -> Tuple[bool, str]:
        """Check that all required dependencies across a component set are satisfied.

        Each component may declare capabilities it *depends on* (dependencies)
        and capabilities it *provides*.  The validator ensures every demand is
        met by at least one provider in the set.
        """
        if not components:
            return True, "empty component set"

        all_provides: Set[str] = set()
        all_demands: Set[str] = set()
        component_type_counts: Dict[ComponentType, int] = {}

        for comp in components:
            all_provides.update(comp.provides)
            all_demands.update(comp.dependencies)
            ct = comp.component_type
            component_type_counts[ct] = component_type_counts.get(ct, 0) + 1

        for ct, count in component_type_counts.items():
            if ct in _SINGLETON_COMPONENTS and count > 1:
                return False, f"multiple {ct.value} components are not allowed"

        unsatisfied = all_demands - all_provides
        if unsatisfied:
            missing = ", ".join(sorted(unsatisfied))
            return False, f"unsatisfied dependencies: {missing}"

        return True, "all dependencies satisfied"

    def validate_entity_dependencies(self, entity_id: str) -> Tuple[bool, str]:
        entity = self._entities.get(entity_id)
        if entity is None:
            return False, "entity not found"
        components = self.get_entity_components(entity_id)
        if not components:
            return True, "entity has no components"
        return self.validate_dependencies(components)

    # ------------------------------------------------------------------
    # Conflict Detection
    # ------------------------------------------------------------------

    def detect_conflicts(
        self,
        components: List[ComponentBlueprint],
    ) -> List[Dict[str, Any]]:
        """Scan a component list for incompatible pairings.

        Returns a list of conflict descriptions so callers can decide
        whether to proceed or display warnings.
        """
        conflicts: List[Dict[str, Any]] = []
        comps_by_type: Dict[ComponentType, List[ComponentBlueprint]] = {}
        for comp in components:
            comps_by_type.setdefault(comp.component_type, []).append(comp)

        for (type_a, type_b) in _INCOMPATIBLE_PAIRS:
            if type_a in comps_by_type and type_b in comps_by_type:
                comp_a_names = [c.name for c in comps_by_type[type_a]]
                comp_b_names = [c.name for c in comps_by_type[type_b]]
                conflicts.append({
                    "type_a": type_a.value,
                    "type_b": type_b.value,
                    "components_a": comp_a_names,
                    "components_b": comp_b_names,
                    "severity": "incompatible",
                    "message": f"{type_a.value} is incompatible with {type_b.value}",
                })
        return conflicts

    def _check_conflicts(self, components: List[ComponentBlueprint]) -> List[Dict[str, Any]]:
        return self.detect_conflicts(components)

    def detect_entity_conflicts(self, entity_id: str) -> List[Dict[str, Any]]:
        entity = self._entities.get(entity_id)
        if entity is None:
            return [{"error": "entity not found"}]
        components = self.get_entity_components(entity_id)
        return self.detect_conflicts(components)

    # ------------------------------------------------------------------
    # Template Instantiation
    # ------------------------------------------------------------------

    def instantiate_template(
        self,
        template: EntityTemplate,
        position: Optional[Tuple[float, float]] = None,
        parent_entity_id: str = "",
    ) -> Optional[AssembledEntity]:
        """Quick-create an entity from a predefined EntityTemplate.

        Registers all required components in the registry, creates an
        ephemeral archetype, and assembles the entity in one call.
        """
        preset = _PRESET_TEMPLATE_COMPONENTS.get(template)
        if preset is None:
            return None

        component_ids: List[str] = []
        for comp_name, comp_type, props, deps, provs, tags in preset:
            effective_props = dict(props)
            if position is not None and comp_type == ComponentType.TRANSFORM:
                effective_props["position"] = position

            blueprint = self.register_component(
                name=comp_name,
                component_type=comp_type.value,
                properties=effective_props,
                dependencies=list(deps),
                provides=list(provs),
                tags=list(tags),
            )
            component_ids.append(blueprint.id)

        archetype = self.create_archetype(
            name=f"{template.value}_archetype",
            component_ids=component_ids,
            category=template.value,
            description=f"Auto-generated archetype for {template.value} template",
        )
        if archetype is None:
            return None

        entity = self.assemble_entity(
            archetype_id=archetype.id,
            parent_entity_id=parent_entity_id,
        )
        return entity

    # ------------------------------------------------------------------
    # Clone Entity
    # ------------------------------------------------------------------

    def clone_entity(
        self,
        source_entity_id: str,
        parent_entity_id: str = "",
        state_overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[AssembledEntity]:
        """Deep-copy an existing entity, preserving component composition and state."""
        source = self._entities.get(source_entity_id)
        if source is None:
            return None

        merged_state = dict(source.state)
        if state_overrides:
            merged_state.update(state_overrides)

        now = _time_module.time()
        clone = AssembledEntity(
            archetype_id=source.archetype_id,
            components=list(source.components),
            state=merged_state,
            parent_entity_id=parent_entity_id,
            created_at=now,
            updated_at=now,
        )
        self._entities[clone.id] = clone

        if parent_entity_id and parent_entity_id in self._entities:
            parent = self._entities[parent_entity_id]
            if clone.id not in parent.children_ids:
                parent.children_ids.append(clone.id)
            self._entity_parent_index[clone.id] = parent_entity_id

        for child_id in source.children_ids:
            self.clone_entity(child_id, parent_entity_id=clone.id)

        self._assembly_count += 1
        self._assembly_log.append({
            "action": "clone",
            "entity_id": clone.id,
            "source_entity_id": source_entity_id,
            "parent_entity_id": parent_entity_id,
            "timestamp": now,
        })
        return clone

    # ------------------------------------------------------------------
    # Entity Tree Management
    # ------------------------------------------------------------------

    def get_entity_tree(self, entity_id: str) -> Dict[str, Any]:
        """Recursively build a tree representation of an entity and its descendants."""
        entity = self._entities.get(entity_id)
        if entity is None:
            return {"error": "entity not found"}

        component_details: List[Dict[str, Any]] = []
        for cid in entity.components:
            comp = self._component_registry.get(cid)
            if comp is not None:
                component_details.append({
                    "id": comp.id,
                    "name": comp.name,
                    "type": comp.component_type.value,
                    "provides": comp.provides,
                    "dependencies": comp.dependencies,
                })

        archetype = self._archetypes.get(entity.archetype_id)
        archetype_name = archetype.name if archetype else "unknown"

        children_trees: List[Dict[str, Any]] = []
        for child_id in entity.children_ids:
            child_tree = self.get_entity_tree(child_id)
            children_trees.append(child_tree)

        return {
            "entity_id": entity.id,
            "archetype_id": entity.archetype_id,
            "archetype_name": archetype_name,
            "component_count": len(entity.components),
            "components": component_details,
            "state_keys": list(entity.state.keys()),
            "child_count": len(entity.children_ids),
            "children": children_trees,
            "parent_entity_id": entity.parent_entity_id,
            "created_at": entity.created_at,
            "updated_at": entity.updated_at,
        }

    def set_parent(
        self,
        entity_id: str,
        parent_entity_id: str,
    ) -> bool:
        """Reparent an entity within the entity tree.

        Detects and prevents circular parent relationships.
        """
        if entity_id == parent_entity_id:
            return False
        entity = self._entities.get(entity_id)
        if entity is None:
            return False
        if parent_entity_id and parent_entity_id not in self._entities:
            return False

        if parent_entity_id and self._is_descendant_of(parent_entity_id, entity_id):
            return False

        if entity.parent_entity_id:
            old_parent = self._entities.get(entity.parent_entity_id)
            if old_parent and entity_id in old_parent.children_ids:
                old_parent.children_ids.remove(entity_id)

        self._entity_parent_index.pop(entity_id, None)

        if parent_entity_id:
            parent = self._entities[parent_entity_id]
            if entity_id not in parent.children_ids:
                parent.children_ids.append(entity_id)
            self._entity_parent_index[entity_id] = parent_entity_id

        entity.parent_entity_id = parent_entity_id
        entity.updated_at = _time_module.time()
        return True

    def _is_descendant_of(self, ancestor_id: str, target_id: str) -> bool:
        visited: Set[str] = set()
        current = target_id
        while current:
            if current == ancestor_id:
                return True
            if current in visited:
                break
            visited.add(current)
            current = self._entity_parent_index.get(current, "")
        return False

    def get_root_entities(self) -> List[AssembledEntity]:
        return [e for e in self._entities.values() if not e.parent_entity_id]

    def get_child_entities(self, entity_id: str) -> List[AssembledEntity]:
        entity = self._entities.get(entity_id)
        if entity is None:
            return []
        return [
            self._entities[cid] for cid in entity.children_ids
            if cid in self._entities
        ]

    def get_descendant_count(self, entity_id: str) -> int:
        entity = self._entities.get(entity_id)
        if entity is None:
            return 0
        total = len(entity.children_ids)
        for child_id in entity.children_ids:
            total += self.get_descendant_count(child_id)
        return total

    def get_entity_depth(self, entity_id: str) -> int:
        depth = 0
        current = entity_id
        visited: Set[str] = set()
        while current:
            if current in visited:
                break
            visited.add(current)
            current = self._entity_parent_index.get(current, "")
            if current:
                depth += 1
        return depth

    # ------------------------------------------------------------------
    # Statistics & Reporting
    # ------------------------------------------------------------------

    def get_assembly_stats(self) -> Dict[str, Any]:
        """Return comprehensive statistics about the assembler's state."""
        component_type_distribution: Dict[str, int] = {}
        for comp in self._component_registry.values():
            ct = comp.component_type.value
            component_type_distribution[ct] = component_type_distribution.get(ct, 0) + 1

        total_archetype_components = sum(
            len(a.components) for a in self._archetypes.values()
        )

        archetype_categories: Dict[str, int] = {}
        for arch in self._archetypes.values():
            cat = arch.category or "uncategorized"
            archetype_categories[cat] = archetype_categories.get(cat, 0) + 1

        entity_count_by_archetype: Dict[str, int] = {}
        for ent in self._entities.values():
            aid = ent.archetype_id
            entity_count_by_archetype[aid] = entity_count_by_archetype.get(aid, 0) + 1

        entities_with_conflicts = 0
        total_conflicts = 0
        for ent in self._entities.values():
            comps = self.get_entity_components(ent.id)
            conflicts = self.detect_conflicts(comps)
            if conflicts:
                entities_with_conflicts += 1
                total_conflicts += len(conflicts)

        root_count = len(self.get_root_entities())
        max_depth = 0
        max_children = 0
        for ent in self._entities.values():
            depth = self.get_entity_depth(ent.id)
            if depth > max_depth:
                max_depth = depth
            child_count = len(ent.children_ids)
            if child_count > max_children:
                max_children = child_count

        return {
            "registered_components": len(self._component_registry),
            "component_type_distribution": component_type_distribution,
            "total_archetypes": len(self._archetypes),
            "archetype_categories": archetype_categories,
            "total_components_in_archetypes": total_archetype_components,
            "avg_components_per_archetype": (
                total_archetype_components / len(self._archetypes)
                if self._archetypes else 0.0
            ),
            "total_assembled_entities": len(self._entities),
            "total_assembly_operations": self._assembly_count,
            "assembly_log_entries": len(self._assembly_log),
            "root_entities": root_count,
            "max_tree_depth": max_depth,
            "max_children_per_entity": max_children,
            "entity_count_by_archetype": entity_count_by_archetype,
            "entities_with_conflicts": entities_with_conflicts,
            "total_detected_conflicts": total_conflicts,
            "templates_available": len(_PRESET_TEMPLATE_COMPONENTS),
        }

    def list_templates(self) -> List[str]:
        return [t.value for t in EntityTemplate]

    def get_assembly_log(self, limit: int = 50) -> List[Dict[str, Any]]:
        return self._assembly_log[-limit:]

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._component_registry.clear()
            self._archetypes.clear()
            self._entities.clear()
            self._component_name_index.clear()
            self._entity_parent_index.clear()
            self._assembly_log.clear()
            self._assembly_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return comprehensive ComponentAssembler subsystem statistics."""
        return {
            "total_components": len(self._component_registry),
            "total_archetypes": len(self._archetypes),
            "total_entities": len(self._entities),
            "total_assemblies": self._assembly_count,
            "components_by_type": {
                ct.value: sum(1 for c in self._component_registry.values() if c.component_type == ct)
                for ct in ComponentType
            },
            "archetypes": [a.to_dict() for a in self._archetypes.values()],
            "assembly_log_size": len(self._assembly_log),
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_component_assembler() -> ComponentAssembler:
    """Return the singleton ComponentAssembler instance."""
    return ComponentAssembler.get_instance()