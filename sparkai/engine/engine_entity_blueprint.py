"""
SparkLabs Engine - Entity Blueprint System

Templated game entity creation with variant inheritance and composition.
Provides a data-driven approach to defining reusable entity archetypes
that can be instantiated with parameter overrides, variant specialization,
and multi-blueprint composition into hybrid entities.

Architecture:
  EntityBlueprintSystem
    |-- BlueprintTemplate (named entity archetype with component definitions)
    |-- ComponentDefinition (individual component slot with parameters)
    |-- EntityVariant (parameter override set for a specific blueprint)
    |-- BlueprintInstance (runtime-spawned entity from a blueprint)
    |-- Composition Engine (merges blueprints via OVERRIDE/EXTEND/MERGE/REPLACE)
"""

from __future__ import annotations

import copy
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class BlueprintCategory(Enum):
    CHARACTER = "character"
    ITEM = "item"
    ENVIRONMENT = "environment"
    UI = "ui"
    PROJECTILE = "projectile"
    EFFECT = "effect"
    TRIGGER = "trigger"


class ComponentType(Enum):
    TRANSFORM = "transform"
    RENDERER = "renderer"
    COLLIDER = "collider"
    RIGIDBODY = "rigidbody"
    ANIMATOR = "animator"
    AUDIO = "audio"
    SCRIPT = "script"


class CompositionMode(Enum):
    OVERRIDE = "override"
    EXTEND = "extend"
    MERGE = "merge"
    REPLACE = "replace"


@dataclass
class ComponentDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    component_type: ComponentType = ComponentType.SCRIPT
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_required: bool = False
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "component_type": self.component_type.value,
            "parameters": dict(self.parameters),
            "is_required": self.is_required,
            "dependencies": list(self.dependencies),
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class BlueprintTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    category: BlueprintCategory = BlueprintCategory.CHARACTER
    description: str = ""
    components: Dict[str, ComponentDefinition] = field(default_factory=dict)
    variants: Dict[str, EntityVariant] = field(default_factory=dict)
    parent_blueprint_id: str = ""
    tags: List[str] = field(default_factory=list)
    is_abstract: bool = False
    version: int = 1
    created_at: float = field(default_factory=time.time)
    modified_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "description": self.description,
            "components": {
                k: v.to_dict() for k, v in self.components.items()
            },
            "variant_count": len(self.variants),
            "variants": {k: v.to_dict() for k, v in self.variants.items()},
            "parent_blueprint_id": self.parent_blueprint_id,
            "tags": list(self.tags),
            "is_abstract": self.is_abstract,
            "version": self.version,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
        }


@dataclass
class EntityVariant:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    blueprint_id: str = ""
    variant_name: str = ""
    overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    excluded_components: List[str] = field(default_factory=list)
    added_components: Dict[str, ComponentDefinition] = field(default_factory=dict)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "variant_name": self.variant_name,
            "overrides": {k: dict(v) for k, v in self.overrides.items()},
            "excluded_components": list(self.excluded_components),
            "added_components": {
                k: v.to_dict() for k, v in self.added_components.items()
            },
            "description": self.description,
        }


@dataclass
class BlueprintInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    blueprint_id: str = ""
    variant_id: str = ""
    instance_name: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    rotation: float = 0.0
    scale: Tuple[float, float] = (1.0, 1.0)
    components: Dict[str, ComponentDefinition] = field(default_factory=dict)
    resolved_parameters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    scene_id: str = ""
    is_active: bool = True
    spawned_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "blueprint_id": self.blueprint_id,
            "variant_id": self.variant_id,
            "instance_name": self.instance_name,
            "position": list(self.position),
            "rotation": self.rotation,
            "scale": list(self.scale),
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "resolved_parameters": {
                k: dict(v) for k, v in self.resolved_parameters.items()
            },
            "scene_id": self.scene_id,
            "is_active": self.is_active,
            "spawned_at": self.spawned_at,
        }


class EntityBlueprintSystem:
    """Templated game entity creation with variant inheritance and composition."""

    _instance: Optional["EntityBlueprintSystem"] = None
    _lock = threading.RLock()

    _PRESET_BLUEPRINTS = {
        "player_character": {
            "name": "Player Character",
            "category": "character",
            "description": "Default player-controlled character archetype",
            "components": [
                ("transform", ComponentType.TRANSFORM,
                 {"position": (0.0, 0.0), "layer": 0}),
                ("renderer", ComponentType.RENDERER,
                 {"sprite": "default_player", "color": "#00FF00"}),
                ("collider", ComponentType.COLLIDER,
                 {"shape": "capsule", "width": 32, "height": 64}),
                ("rigidbody", ComponentType.RIGIDBODY,
                 {"mass": 70.0, "gravity_scale": 1.0, "drag": 0.2}),
                ("animator", ComponentType.ANIMATOR,
                 {"controller": "player_anim_controller"}),
                ("player_input", ComponentType.SCRIPT,
                 {"move_speed": 300.0, "jump_force": 600.0}),
            ],
        },
        "static_prop": {
            "name": "Static Prop",
            "category": "environment",
            "description": "Non-interactive environment decoration",
            "components": [
                ("transform", ComponentType.TRANSFORM, {}),
                ("renderer", ComponentType.RENDERER,
                 {"sprite": "default_prop", "cast_shadows": False}),
                ("collider", ComponentType.COLLIDER,
                 {"shape": "box", "is_trigger": False}),
            ],
        },
        "interactable_item": {
            "name": "Interactable Item",
            "category": "item",
            "description": "Pickup item with interaction trigger",
            "components": [
                ("transform", ComponentType.TRANSFORM, {}),
                ("renderer", ComponentType.RENDERER,
                 {"sprite": "default_item", "color": "#FFFFFF"}),
                ("collider", ComponentType.COLLIDER,
                 {"shape": "circle", "radius": 16, "is_trigger": True}),
                ("item_behavior", ComponentType.SCRIPT,
                 {"pickup_range": 80.0, "auto_rotate": True, "bob_amplitude": 4.0}),
            ],
        },
    }

    def __init__(self) -> None:
        self._blueprints: Dict[str, BlueprintTemplate] = {}
        self._instances: Dict[str, BlueprintInstance] = {}
        self._category_index: Dict[str, List[str]] = {}
        self._composition_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "EntityBlueprintSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Blueprint Management ----

    def create_blueprint(self,
                         name: str,
                         category: str = "character",
                         description: str = "") -> BlueprintTemplate:
        try:
            cat = BlueprintCategory(category.lower())
        except ValueError:
            cat = BlueprintCategory.CHARACTER

        blueprint = BlueprintTemplate(
            name=name,
            category=cat,
            description=description,
        )
        self._blueprints[blueprint.id] = blueprint
        self._category_index.setdefault(cat.value, []).append(blueprint.id)
        return blueprint

    def add_component(self,
                      blueprint_id: str,
                      component_name: str,
                      component_type: str = "script",
                      parameters: Optional[Dict[str, Any]] = None) -> Optional[ComponentDefinition]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return None

        try:
            ctype = ComponentType(component_type.lower())
        except ValueError:
            ctype = ComponentType.SCRIPT

        component = ComponentDefinition(
            name=component_name,
            component_type=ctype,
            parameters=dict(parameters) if parameters else {},
        )
        blueprint.components[component.id] = component
        blueprint.modified_at = time.time()
        return component

    def remove_component(self,
                         blueprint_id: str,
                         component_id: str) -> bool:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return False
        if component_id not in blueprint.components:
            return False
        del blueprint.components[component_id]
        blueprint.modified_at = time.time()
        return True

    def update_component_parameters(self,
                                    blueprint_id: str,
                                    component_id: str,
                                    parameters: Dict[str, Any]) -> bool:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return False
        component = blueprint.components.get(component_id)
        if component is None:
            return False
        component.parameters.update(parameters)
        blueprint.modified_at = time.time()
        return True

    # ---- Variant Management ----

    def create_variant(self,
                       blueprint_id: str,
                       variant_name: str,
                       overrides: Optional[Dict[str, Any]] = None) -> Optional[EntityVariant]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return None

        resolved_overrides: Dict[str, Dict[str, Any]] = {}
        if overrides:
            for key, value in overrides.items():
                if isinstance(value, dict):
                    resolved_overrides[key] = dict(value)
                else:
                    resolved_overrides[key] = {"value": value}

        variant = EntityVariant(
            blueprint_id=blueprint_id,
            variant_name=variant_name,
            overrides=resolved_overrides,
        )
        blueprint.variants[variant.id] = variant
        blueprint.modified_at = time.time()
        return variant

    def remove_variant(self,
                       blueprint_id: str,
                       variant_id: str) -> bool:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return False
        if variant_id not in blueprint.variants:
            return False
        del blueprint.variants[variant_id]
        blueprint.modified_at = time.time()
        return True

    def get_variant(self,
                    blueprint_id: str,
                    variant_id: str) -> Optional[EntityVariant]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return None
        return blueprint.variants.get(variant_id)

    def list_variants(self, blueprint_id: str) -> List[EntityVariant]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return []
        return list(blueprint.variants.values())

    # ---- Instantiation ----

    def instantiate(self,
                    blueprint_id: str,
                    position: Tuple[float, float] = (0.0, 0.0),
                    variant_id: str = "",
                    instance_name: str = "") -> Optional[BlueprintInstance]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return None

        resolved_components: Dict[str, ComponentDefinition] = {}
        resolved_params: Dict[str, Dict[str, Any]] = {}

        parent_chain = self._resolve_inheritance_chain(blueprint_id)
        for parent_id in parent_chain:
            parent_bp = self._blueprints.get(parent_id)
            if parent_bp is None:
                continue
            for comp in parent_bp.components.values():
                if comp.id not in resolved_components:
                    resolved_components[comp.id] = copy.deepcopy(comp)
                    resolved_params[comp.id] = dict(comp.parameters)

        variant = blueprint.variants.get(variant_id) if variant_id else None

        if variant:
            for comp_id, param_overrides in variant.overrides.items():
                if comp_id in resolved_params:
                    resolved_params[comp_id].update(param_overrides)
            for excluded in variant.excluded_components:
                resolved_components.pop(excluded, None)
                resolved_params.pop(excluded, None)
            for added_id, added_comp in variant.added_components.items():
                resolved_components[added_id] = copy.deepcopy(added_comp)
                resolved_params[added_id] = dict(added_comp.parameters)

        instance = BlueprintInstance(
            blueprint_id=blueprint_id,
            variant_id=variant_id,
            instance_name=instance_name or f"{blueprint.name}_{len(self._instances)}",
            position=position,
            components=resolved_components,
            resolved_parameters=resolved_params,
        )
        self._instances[instance.id] = instance
        return instance

    def _resolve_inheritance_chain(self, blueprint_id: str) -> List[str]:
        chain: List[str] = [blueprint_id]
        visited: set = {blueprint_id}
        current = blueprint_id
        while True:
            bp = self._blueprints.get(current)
            if bp is None or not bp.parent_blueprint_id:
                break
            parent_id = bp.parent_blueprint_id
            if parent_id in visited:
                break
            visited.add(parent_id)
            chain.append(parent_id)
            current = parent_id
        chain.reverse()
        return chain

    def get_blueprint_instance(self, instance_id: str) -> Optional[BlueprintInstance]:
        return self._instances.get(instance_id)

    def destroy_instance(self, instance_id: str) -> bool:
        if instance_id not in self._instances:
            return False
        del self._instances[instance_id]
        return True

    def list_instances(self,
                       blueprint_id: Optional[str] = None) -> List[BlueprintInstance]:
        instances = list(self._instances.values())
        if blueprint_id:
            return [i for i in instances if i.blueprint_id == blueprint_id]
        return instances

    # ---- Composition ----

    def compose_blueprints(self,
                           source_ids: Optional[List[str]] = None,
                           composition_mode: str = "merge",
                           new_name: str = "") -> Optional[BlueprintTemplate]:
        if not source_ids:
            return None

        try:
            mode = CompositionMode(composition_mode.lower())
        except ValueError:
            mode = CompositionMode.MERGE

        sources: List[BlueprintTemplate] = []
        for sid in source_ids:
            bp = self._blueprints.get(sid)
            if bp is not None:
                sources.append(bp)

        if not sources:
            return None

        composed_name = new_name or "_".join(bp.name.replace(" ", "_")
                                             for bp in sources) + "_composed"
        composed = BlueprintTemplate(
            name=composed_name,
            category=sources[0].category,
            description=f"Composed from {len(sources)} blueprints",
        )

        if mode == CompositionMode.OVERRIDE:
            composed.components = self._compose_override(sources)
        elif mode == CompositionMode.EXTEND:
            composed.components = self._compose_extend(sources)
        elif mode == CompositionMode.REPLACE:
            composed.components = dict(sources[-1].components)
        else:
            composed.components = self._compose_merge(sources)

        self._blueprints[composed.id] = composed
        self._category_index.setdefault(composed.category.value, []).append(composed.id)

        self._composition_log.append({
            "action": "compose",
            "source_ids": source_ids,
            "mode": mode.value,
            "result_id": composed.id,
            "result_name": composed_name,
            "component_count": len(composed.components),
            "timestamp": time.time(),
        })
        return composed

    def _compose_override(self,
                          sources: List[BlueprintTemplate]) -> Dict[str, ComponentDefinition]:
        result: Dict[str, ComponentDefinition] = {}
        for bp in sources:
            for comp in bp.components.values():
                existing = result.get(comp.id)
                if existing is not None:
                    for key, value in comp.parameters.items():
                        existing.parameters[key] = value
                else:
                    result[comp.id] = copy.deepcopy(comp)
        return result

    def _compose_extend(self,
                        sources: List[BlueprintTemplate]) -> Dict[str, ComponentDefinition]:
        result: Dict[str, ComponentDefinition] = {}
        base = sources[0]
        result = {cid: copy.deepcopy(c) for cid, c in base.components.items()}
        for bp in sources[1:]:
            for comp in bp.components.values():
                name_match = [
                    cid for cid, c in result.items()
                    if c.name == comp.name and c.component_type == comp.component_type
                ]
                if name_match:
                    for key, value in comp.parameters.items():
                        mcomp = result[name_match[0]]
                        mcomp.parameters.setdefault(key, value)
                else:
                    result[comp.id] = copy.deepcopy(comp)
        return result

    def _compose_merge(self,
                       sources: List[BlueprintTemplate]) -> Dict[str, ComponentDefinition]:
        result: Dict[str, ComponentDefinition] = {}
        for bp in sources:
            for comp in bp.components.values():
                similar = None
                for rid, rc in result.items():
                    if rc.name == comp.name:
                        similar = rid
                        break
                if similar is not None:
                    for key, value in comp.parameters.items():
                        existing_value = result[similar].parameters.get(key)
                        if existing_value is None:
                            result[similar].parameters[key] = value
                        elif isinstance(existing_value, (int, float)) and isinstance(value, (int, float)):
                            result[similar].parameters[key] = max(existing_value, value)
                else:
                    result[comp.id] = copy.deepcopy(comp)
        return result

    def get_composition_log(self, limit: int = 20) -> List[Dict[str, Any]]:
        return self._composition_log[-limit:]

    # ---- Inheritance ----

    def set_parent(self,
                   blueprint_id: str,
                   parent_blueprint_id: str) -> bool:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return False
        parent = self._blueprints.get(parent_blueprint_id)
        if parent is None:
            return False
        if blueprint_id == parent_blueprint_id:
            return False

        chain = self._resolve_inheritance_chain(parent_blueprint_id)
        if blueprint_id in chain:
            return False

        blueprint.parent_blueprint_id = parent_blueprint_id
        blueprint.modified_at = time.time()
        return True

    def clear_parent(self, blueprint_id: str) -> bool:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return False
        blueprint.parent_blueprint_id = ""
        blueprint.modified_at = time.time()
        return True

    def get_inheritance_tree(self, blueprint_id: str) -> Dict[str, Any]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return {}
        chain = self._resolve_inheritance_chain(blueprint_id)
        children = [
            bpid for bpid, bp in self._blueprints.items()
            if bp.parent_blueprint_id == blueprint_id
        ]
        return {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint.name,
            "parent_chain": chain[:-1] if len(chain) > 1 else [],
            "parent_id": blueprint.parent_blueprint_id,
            "children": children,
            "child_count": len(children),
            "depth": len(chain),
        }

    # ---- Component Tree ----

    def get_component_tree(self, blueprint_id: str) -> Dict[str, Any]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return {"error": "Blueprint not found"}

        chain = self._resolve_inheritance_chain(blueprint_id)
        component_tree: Dict[str, Any] = {
            "blueprint_id": blueprint_id,
            "blueprint_name": blueprint.name,
            "total_components": 0,
            "inheritance_layers": [],
        }

        for parent_id in chain:
            parent_bp = self._blueprints.get(parent_id)
            if parent_bp is None:
                continue
            layer_entry = {
                "blueprint_id": parent_id,
                "blueprint_name": parent_bp.name,
                "components": {},
            }
            for comp in parent_bp.components.values():
                layer_entry["components"][comp.id] = {
                    "name": comp.name,
                    "type": comp.component_type.value,
                    "parameter_keys": list(comp.parameters.keys()),
                    "is_required": comp.is_required,
                    "dependencies": comp.dependencies,
                }
            component_tree["inheritance_layers"].append(layer_entry)
            component_tree["total_components"] += len(parent_bp.components)

        return component_tree

    # ---- Export ----

    def export_blueprint(self,
                         blueprint_id: str,
                         format: str = "json") -> Dict[str, Any]:
        blueprint = self._blueprints.get(blueprint_id)
        if blueprint is None:
            return {"error": "Blueprint not found"}

        exported = blueprint.to_dict()
        exported["inheritance"] = self.get_inheritance_tree(blueprint_id)
        exported["format_version"] = "1.0"

        return exported

    def import_blueprint(self, data: Dict[str, Any]) -> Optional[BlueprintTemplate]:
        try:
            cat_str = data.get("category", "character")
            cat = BlueprintCategory(cat_str)
        except ValueError:
            cat = BlueprintCategory.CHARACTER

        blueprint = BlueprintTemplate(
            name=data.get("name", "Imported Blueprint"),
            category=cat,
            description=data.get("description", ""),
        )
        for cdef in data.get("components", {}).values():
            if isinstance(cdef, dict):
                ctype_str = cdef.get("component_type", "script")
                try:
                    ctype = ComponentType(ctype_str)
                except ValueError:
                    ctype = ComponentType.SCRIPT
                comp = ComponentDefinition(
                    name=cdef.get("name", ""),
                    component_type=ctype,
                    parameters=cdef.get("parameters", {}),
                )
                blueprint.components[comp.id] = comp

        self._blueprints[blueprint.id] = blueprint
        self._category_index.setdefault(cat.value, []).append(blueprint.id)
        return blueprint

    # ---- Listing and Querying ----

    def list_blueprints(self,
                        category: str = "") -> List[BlueprintTemplate]:
        if not category:
            return list(self._blueprints.values())
        try:
            cat = BlueprintCategory(category.lower())
        except ValueError:
            return []
        blueprint_ids = self._category_index.get(cat.value, [])
        return [bp for bid in blueprint_ids
                if (bp := self._blueprints.get(bid)) is not None]

    def get_blueprint(self, blueprint_id: str) -> Optional[BlueprintTemplate]:
        return self._blueprints.get(blueprint_id)

    def find_blueprints_by_tag(self, tag: str) -> List[BlueprintTemplate]:
        return [bp for bp in self._blueprints.values() if tag in bp.tags]

    def find_blueprints_by_component(self,
                                     component_type: str) -> List[BlueprintTemplate]:
        try:
            ctype = ComponentType(component_type.lower())
        except ValueError:
            return []
        results: List[BlueprintTemplate] = []
        for bp in self._blueprints.values():
            for comp in bp.components.values():
                if comp.component_type == ctype:
                    results.append(bp)
                    break
        return results

    # ---- Preset Loading ----

    def load_preset(self, preset_key: str) -> Optional[BlueprintTemplate]:
        preset = self._PRESET_BLUEPRINTS.get(preset_key)
        if preset is None:
            return None

        bp = self.create_blueprint(
            preset["name"],
            category=preset.get("category", "character"),
            description=preset.get("description", ""),
        )
        for name, ctype, params in preset.get("components", []):
            self.add_component(
                bp.id,
                component_name=name,
                component_type=ctype.value,
                parameters=params,
            )
        return bp

    def list_presets(self) -> List[str]:
        return list(self._PRESET_BLUEPRINTS.keys())

    # ---- Cleanup and Reset ----

    def delete_blueprint(self, blueprint_id: str) -> bool:
        if blueprint_id not in self._blueprints:
            return False
        bp = self._blueprints[blueprint_id]
        cat_value = bp.category.value
        if cat_value in self._category_index:
            self._category_index[cat_value] = [
                bid for bid in self._category_index[cat_value]
                if bid != blueprint_id
            ]
        to_remove = [iid for iid, inst in self._instances.items()
                     if inst.blueprint_id == blueprint_id]
        for iid in to_remove:
            del self._instances[iid]
        for child_bp in self._blueprints.values():
            if child_bp.parent_blueprint_id == blueprint_id:
                child_bp.parent_blueprint_id = ""
        del self._blueprints[blueprint_id]
        return True

    def reset(self) -> None:
        with self._lock:
            self._blueprints.clear()
            self._instances.clear()
            self._category_index.clear()
            self._composition_log.clear()

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        total_components = sum(
            len(bp.components) for bp in self._blueprints.values()
        )
        total_variants = sum(
            len(bp.variants) for bp in self._blueprints.values()
        )
        categories = {}
        for bp in self._blueprints.values():
            cat = bp.category.value
            categories[cat] = categories.get(cat, 0) + 1

        parents = sum(
            1 for bp in self._blueprints.values()
            if bp.parent_blueprint_id
        )
        children = sum(
            1 for bp in self._blueprints.values()
            if any(cb.parent_blueprint_id == bp.id
                   for cb in self._blueprints.values())
        )

        component_type_counts = {}
        for bp in self._blueprints.values():
            for comp in bp.components.values():
                ct = comp.component_type.value
                component_type_counts[ct] = component_type_counts.get(ct, 0) + 1

        tags: Dict[str, int] = {}
        for bp in self._blueprints.values():
            for tag in bp.tags:
                tags[tag] = tags.get(tag, 0) + 1

        return {
            "total_blueprints": len(self._blueprints),
            "total_components": total_components,
            "total_variants": total_variants,
            "total_instances": len(self._instances),
            "active_instances": sum(
                1 for i in self._instances.values() if i.is_active
            ),
            "categories": categories,
            "blueprints_with_parent": parents,
            "blueprints_with_children": children,
            "abstract_blueprints": sum(
                1 for bp in self._blueprints.values() if bp.is_abstract
            ),
            "component_type_distribution": component_type_counts,
            "tag_distribution": tags,
            "composition_log_entries": len(self._composition_log),
            "presets_available": len(self._PRESET_BLUEPRINTS),
        }


def get_entity_blueprint() -> EntityBlueprintSystem:
    return EntityBlueprintSystem.get_instance()