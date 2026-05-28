"""
SparkLabs Engine - Prefab Composer

A composition system for creating reusable composite objects (prefabs) that
encapsulate child objects, behaviors, and logic as a single reusable unit.
Supports variants, nested prefab composition, instance-level overrides,
prefab extraction from existing objects, and a searchable prefab library.

Architecture:
  PrefabComposer
    |-- PrefabComponent (individual child object within a prefab)
    |-- PrefabDefinition (named reusable object template)
    |-- PrefabVariant (parameterized variation of a prefab)
    |-- PrefabInstance (runtime-spawned copy of a prefab)
    |-- Composition Engine (merges prefabs via MERGE/OVERRIDE/EXTEND/WRAP)
    |-- Prefab Library (searchable catalog with tag indexing)
"""

from __future__ import annotations

import json
import math
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


class PrefabType(Enum):
    GAME_OBJECT = "game_object"
    UI_ELEMENT = "ui_element"
    ENVIRONMENT_PROP = "environment_prop"
    CHARACTER = "character"
    PICKUP_ITEM = "pickup_item"
    TRIGGER_ZONE = "trigger_zone"
    PARTICLE_EFFECT = "particle_effect"
    SPAWN_POINT = "spawn_point"


class VariantSelection(Enum):
    DEFAULT = "default"
    RANDOM = "random"
    WEIGHTED = "weighted"
    CONTEXTUAL = "contextual"
    TIME_BASED = "time_based"


class PrefabStatus(Enum):
    DRAFT = "draft"
    REVIEWED = "reviewed"
    PUBLISHED = "published"
    MODIFIED = "modified"
    BROKEN = "broken"


class CompositionMode(Enum):
    MERGE = "merge"
    OVERRIDE = "override"
    EXTEND = "extend"
    WRAP = "wrap"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PrefabComponent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    object_type: str = "game_object"
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    properties: Dict[str, Any] = field(default_factory=dict)
    behaviors: List[str] = field(default_factory=list)
    children: List[str] = field(default_factory=list)
    visible: bool = True
    locked: bool = False
    layer: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "object_type": self.object_type,
            "position": list(self.position),
            "scale": list(self.scale),
            "rotation": list(self.rotation),
            "properties": dict(self.properties),
            "behaviors": list(self.behaviors),
            "children": list(self.children),
            "visible": self.visible,
            "locked": self.locked,
            "layer": self.layer,
        }


@dataclass
class PrefabDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    prefab_type: PrefabType = PrefabType.GAME_OBJECT
    components: Dict[str, PrefabComponent] = field(default_factory=dict)
    root_component_id: str = ""
    behaviors: List[str] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    variant_selection: VariantSelection = VariantSelection.DEFAULT
    status: PrefabStatus = PrefabStatus.DRAFT
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "prefab_type": self.prefab_type.value,
            "component_count": len(self.components),
            "components": {k: v.to_dict() for k, v in self.components.items()},
            "root_component_id": self.root_component_id,
            "behaviors": list(self.behaviors),
            "properties": dict(self.properties),
            "variant_selection": self.variant_selection.value,
            "status": self.status.value,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class PrefabVariant:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prefab_id: str = ""
    name: str = ""
    description: str = ""
    overrides: Dict[str, Any] = field(default_factory=dict)
    thumbnail: str = ""
    weight: float = 1.0
    condition_expression: str = ""
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prefab_id": self.prefab_id,
            "name": self.name,
            "description": self.description,
            "overrides": dict(self.overrides),
            "thumbnail": self.thumbnail,
            "weight": self.weight,
            "condition_expression": self.condition_expression,
            "created_at": self.created_at,
        }


@dataclass
class PrefabInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    prefab_id: str = ""
    variant_id: str = ""
    parent_scene_id: str = ""
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    rotation: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    overrides: Dict[str, Any] = field(default_factory=dict)
    instance_name: str = ""
    spawned_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prefab_id": self.prefab_id,
            "variant_id": self.variant_id,
            "parent_scene_id": self.parent_scene_id,
            "position": list(self.position),
            "scale": list(self.scale),
            "rotation": list(self.rotation),
            "overrides": dict(self.overrides),
            "instance_name": self.instance_name,
            "spawned_at": self.spawned_at,
        }


# ---------------------------------------------------------------------------
# Prefab Composer (Singleton)
# ---------------------------------------------------------------------------


class PrefabComposer:
    """A composition system for creating reusable composite game objects."""

    _instance: Optional["PrefabComposer"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._prefabs: Dict[str, PrefabDefinition] = {}
        self._variants: Dict[str, PrefabVariant] = {}
        self._instances: Dict[str, PrefabInstance] = {}
        self._type_index: Dict[str, List[str]] = {}
        self._tag_index: Dict[str, List[str]] = {}
        self._composition_graph: Dict[str, List[Tuple[str, str]]] = {}
        self._instance_scene_index: Dict[str, List[str]] = {}
        self._creation_count: int = 0
        self._instantiation_count: int = 0

    @classmethod
    def get_instance(cls) -> "PrefabComposer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Prefab Management
    # ------------------------------------------------------------------

    def create_prefab(
        self,
        name: str,
        prefab_type: str,
        description: str = "",
    ) -> PrefabDefinition:
        try:
            ptype = PrefabType(prefab_type.lower())
        except ValueError:
            ptype = PrefabType.GAME_OBJECT

        now = _time_module.time()
        prefab = PrefabDefinition(
            name=name,
            description=description,
            prefab_type=ptype,
            created_at=now,
            updated_at=now,
        )
        self._prefabs[prefab.id] = prefab
        self._index_prefab_type(prefab.id, ptype.value)
        self._composition_graph[prefab.id] = []
        self._creation_count += 1
        return prefab

    def delete_prefab(self, prefab_id: str) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False

        variant_ids = [
            vid for vid, v in self._variants.items() if v.prefab_id == prefab_id
        ]
        for vid in variant_ids:
            del self._variants[vid]

        instance_ids = [
            iid for iid, inst in self._instances.items()
            if inst.prefab_id == prefab_id
        ]
        for iid in instance_ids:
            self._unindex_instance_scene(iid)
            del self._instances[iid]

        self._unindex_prefab_type(prefab_id, prefab.prefab_type.value)
        for tag in prefab.tags:
            self._unindex_tag(prefab_id, tag)
        self._composition_graph.pop(prefab_id, None)
        for child_list in self._composition_graph.values():
            child_list[:] = [
                (cid, mode) for cid, mode in child_list if cid != prefab_id
            ]

        del self._prefabs[prefab_id]
        return True

    def get_prefab(self, prefab_id: str) -> Optional[PrefabDefinition]:
        return self._prefabs.get(prefab_id)

    def update_prefab(
        self,
        prefab_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[str] = None,
        variant_selection: Optional[str] = None,
    ) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        if name is not None:
            prefab.name = name
        if description is not None:
            prefab.description = description
        if status is not None:
            try:
                prefab.status = PrefabStatus(status.lower())
            except ValueError:
                pass
        if variant_selection is not None:
            try:
                prefab.variant_selection = VariantSelection(variant_selection.lower())
            except ValueError:
                pass
        prefab.updated_at = _time_module.time()
        return True

    def set_prefab_properties(
        self,
        prefab_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        prefab.properties.update(properties)
        prefab.updated_at = _time_module.time()
        return True

    def set_prefab_tags(self, prefab_id: str, tags: List[str]) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        for old_tag in prefab.tags:
            self._unindex_tag(prefab_id, old_tag)
        prefab.tags = list(tags)
        for new_tag in prefab.tags:
            self._index_tag(prefab_id, new_tag)
        prefab.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Component Management
    # ------------------------------------------------------------------

    def add_component(
        self,
        prefab_id: str,
        component: PrefabComponent,
    ) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        prefab.components[component.id] = component
        if not prefab.root_component_id:
            prefab.root_component_id = component.id
        prefab.updated_at = _time_module.time()
        return True

    def remove_component(self, prefab_id: str, component_id: str) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        if component_id not in prefab.components:
            return False
        component = prefab.components[component_id]
        for child_id in component.children:
            if child_id in prefab.components:
                prefab.components[child_id].children = [
                    c for c in prefab.components[child_id].children
                    if c != component_id
                ]
        for comp in prefab.components.values():
            comp.children = [c for c in comp.children if c != component_id]
        del prefab.components[component_id]
        if prefab.root_component_id == component_id:
            prefab.root_component_id = next(iter(prefab.components), "")
        prefab.updated_at = _time_module.time()
        return True

    def get_component(
        self,
        prefab_id: str,
        component_id: str,
    ) -> Optional[PrefabComponent]:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return None
        return prefab.components.get(component_id)

    def list_components(self, prefab_id: str) -> List[PrefabComponent]:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return []
        return list(prefab.components.values())

    def reparent_component(
        self,
        prefab_id: str,
        component_id: str,
        new_parent_id: str,
    ) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        if component_id not in prefab.components:
            return False
        if new_parent_id and new_parent_id not in prefab.components:
            return False
        if component_id == new_parent_id:
            return False
        for comp in prefab.components.values():
            if component_id in comp.children:
                comp.children.remove(component_id)
        visited: Set[str] = set()
        if new_parent_id and self._is_descendant(prefab, new_parent_id, component_id, visited):
            return False
        if new_parent_id:
            prefab.components[new_parent_id].children.append(component_id)
        prefab.updated_at = _time_module.time()
        return True

    def _is_descendant(
        self,
        prefab: PrefabDefinition,
        ancestor_id: str,
        target_id: str,
        visited: Set[str],
    ) -> bool:
        if ancestor_id in visited:
            return False
        visited.add(ancestor_id)
        comp = prefab.components.get(ancestor_id)
        if comp is None:
            return False
        for child_id in comp.children:
            if child_id == target_id:
                return True
            if target_id in visited:
                continue
            if self._is_descendant(prefab, child_id, target_id, visited):
                return True
        return False

    def set_root_component(self, prefab_id: str, component_id: str) -> bool:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return False
        if component_id not in prefab.components:
            return False
        prefab.root_component_id = component_id
        prefab.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Variant Management
    # ------------------------------------------------------------------

    def create_variant(
        self,
        prefab_id: str,
        name: str,
        overrides: Optional[Dict[str, Any]] = None,
        thumbnail: str = "",
        weight: float = 1.0,
        description: str = "",
        condition_expression: str = "",
    ) -> Optional[PrefabVariant]:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return None

        variant = PrefabVariant(
            prefab_id=prefab_id,
            name=name,
            description=description,
            overrides=dict(overrides) if overrides else {},
            thumbnail=thumbnail,
            weight=max(0.0, weight),
            condition_expression=condition_expression,
        )
        self._variants[variant.id] = variant
        return variant

    def delete_variant(self, variant_id: str) -> bool:
        if variant_id not in self._variants:
            return False
        del self._variants[variant_id]
        return True

    def get_variant(self, variant_id: str) -> Optional[PrefabVariant]:
        return self._variants.get(variant_id)

    def get_prefab_variants(self, prefab_id: str) -> List[PrefabVariant]:
        return [
            v for v in self._variants.values() if v.prefab_id == prefab_id
        ]

    def select_variant(
        self,
        prefab_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[PrefabVariant]:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return None

        variants = self.get_prefab_variants(prefab_id)
        if not variants:
            return None

        selection = prefab.variant_selection

        if selection == VariantSelection.DEFAULT:
            return variants[0]

        if selection == VariantSelection.RANDOM:
            import random
            return random.choice(variants)

        if selection == VariantSelection.WEIGHTED:
            import random
            total_weight = sum(v.weight for v in variants)
            if total_weight <= 0:
                return variants[0]
            r = random.uniform(0, total_weight)
            cumulative = 0.0
            for v in variants:
                cumulative += v.weight
                if r <= cumulative:
                    return v
            return variants[-1]

        if selection == VariantSelection.CONTEXTUAL:
            if context:
                for v in variants:
                    if v.condition_expression and self._evaluate_condition(
                        v.condition_expression, context
                    ):
                        return v
            return variants[0]

        if selection == VariantSelection.TIME_BASED:
            now = _time_module.time()
            index = int(now) % len(variants)
            return variants[index]

        return variants[0]

    def _evaluate_condition(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> bool:
        try:
            parts = expression.split()
            if len(parts) == 3:
                key, op, expected = parts
                actual = context.get(key)
                if actual is None:
                    return False
                if op == "==":
                    return str(actual) == expected
                if op == "!=":
                    return str(actual) != expected
                if op == ">=":
                    return float(actual) >= float(expected)
                if op == "<=":
                    return float(actual) <= float(expected)
                if op == ">":
                    return float(actual) > float(expected)
                if op == "<":
                    return float(actual) < float(expected)
                if op == "in":
                    return expected in str(actual)
            return False
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Instantiation
    # ------------------------------------------------------------------

    def instantiate_prefab(
        self,
        prefab_id: str,
        parent_scene_id: str,
        position: Optional[Tuple[float, float, float]] = None,
        variant_id: str = "",
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Optional[PrefabInstance]:
        prefab = self._prefabs.get(prefab_id)
        if prefab is None:
            return None

        pos = position if position else (0.0, 0.0, 0.0)
        instance = PrefabInstance(
            prefab_id=prefab_id,
            variant_id=variant_id,
            parent_scene_id=parent_scene_id,
            position=pos,
            overrides=dict(overrides) if overrides else {},
            instance_name=f"{prefab.name}_instance_{self._instantiation_count}",
        )
        self._instances[instance.id] = instance
        self._index_instance_scene(instance.id, parent_scene_id)
        self._instantiation_count += 1
        return instance

    def update_instance(
        self,
        instance_id: str,
        properties: Dict[str, Any],
    ) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        if "position" in properties:
            instance.position = tuple(properties["position"])
        if "scale" in properties:
            instance.scale = tuple(properties["scale"])
        if "rotation" in properties:
            instance.rotation = tuple(properties["rotation"])
        if "overrides" in properties:
            instance.overrides.update(properties["overrides"])
        if "instance_name" in properties:
            instance.instance_name = properties["instance_name"]
        return True

    def destroy_instance(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        self._unindex_instance_scene(instance_id)
        del self._instances[instance_id]
        return True

    def get_prefab_instance(self, instance_id: str) -> Optional[PrefabInstance]:
        return self._instances.get(instance_id)

    def get_scene_instances(self, scene_id: str) -> List[PrefabInstance]:
        instance_ids = self._instance_scene_index.get(scene_id, [])
        return [
            self._instances[iid]
            for iid in instance_ids
            if iid in self._instances
        ]

    # ------------------------------------------------------------------
    # Instance Overrides
    # ------------------------------------------------------------------

    def create_override(
        self,
        instance_id: str,
        property_path: str,
        value: Any,
    ) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.overrides[property_path] = value
        return True

    def remove_override(self, instance_id: str, property_path: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        if property_path not in instance.overrides:
            return False
        del instance.overrides[property_path]
        return True

    def get_overrides(self, instance_id: str) -> Dict[str, Any]:
        instance = self._instances.get(instance_id)
        if instance is None:
            return {}
        return dict(instance.overrides)

    def clear_overrides(self, instance_id: str) -> bool:
        instance = self._instances.get(instance_id)
        if instance is None:
            return False
        instance.overrides.clear()
        return True

    # ------------------------------------------------------------------
    # Prefab Composition
    # ------------------------------------------------------------------

    def compose_prefabs(
        self,
        parent_prefab_id: str,
        child_prefab_id: str,
        mode: str,
    ) -> bool:
        parent = self._prefabs.get(parent_prefab_id)
        child = self._prefabs.get(child_prefab_id)
        if parent is None or child is None:
            return False
        if parent_prefab_id == child_prefab_id:
            return False

        try:
            comp_mode = CompositionMode(mode.lower())
        except ValueError:
            comp_mode = CompositionMode.MERGE

        if comp_mode == CompositionMode.MERGE:
            self._compose_merge(parent, child)
        elif comp_mode == CompositionMode.OVERRIDE:
            self._compose_override(parent, child)
        elif comp_mode == CompositionMode.EXTEND:
            self._compose_extend(parent, child)
        elif comp_mode == CompositionMode.WRAP:
            self._compose_wrap(parent, child)

        parent.updated_at = _time_module.time()
        existing = self._composition_graph.get(parent_prefab_id, [])
        existing.append((child_prefab_id, comp_mode.value))
        self._composition_graph[parent_prefab_id] = existing
        return True

    def _compose_merge(
        self,
        parent: PrefabDefinition,
        child: PrefabDefinition,
    ) -> None:
        for comp in child.components.values():
            parent.components[comp.id] = comp
        for behavior in child.behaviors:
            if behavior not in parent.behaviors:
                parent.behaviors.append(behavior)
        for key, value in child.properties.items():
            if key not in parent.properties:
                parent.properties[key] = value

    def _compose_override(
        self,
        parent: PrefabDefinition,
        child: PrefabDefinition,
    ) -> None:
        for comp in child.components.values():
            parent.components[comp.id] = comp
        parent.behaviors = list(child.behaviors)
        parent.properties.update(child.properties)

    def _compose_extend(
        self,
        parent: PrefabDefinition,
        child: PrefabDefinition,
    ) -> None:
        for comp in child.components.values():
            if comp.id not in parent.components:
                parent.components[comp.id] = comp
        for behavior in child.behaviors:
            if behavior not in parent.behaviors:
                parent.behaviors.append(behavior)
        for key, value in child.properties.items():
            if key not in parent.properties:
                parent.properties[key] = value

    def _compose_wrap(
        self,
        parent: PrefabDefinition,
        child: PrefabDefinition,
    ) -> None:
        wrapper_id = uuid.uuid4().hex
        wrapper = PrefabComponent(
            id=wrapper_id,
            name=f"wrap_{child.name}",
            object_type="wrapper",
        )
        wrapper.children = list(child.components.keys())
        parent.components.update(child.components)
        parent.components[wrapper_id] = wrapper
        if not parent.root_component_id:
            parent.root_component_id = wrapper_id

    def get_composition_graph(
        self,
        prefab_id: str,
    ) -> List[Tuple[str, str]]:
        return list(self._composition_graph.get(prefab_id, []))

    def uncompose_prefabs(
        self,
        parent_prefab_id: str,
        child_prefab_id: str,
    ) -> bool:
        if parent_prefab_id not in self._composition_graph:
            return False
        entries = self._composition_graph[parent_prefab_id]
        new_entries = [
            (cid, mode) for cid, mode in entries if cid != child_prefab_id
        ]
        if len(new_entries) == len(entries):
            return False
        self._composition_graph[parent_prefab_id] = new_entries
        parent = self._prefabs.get(parent_prefab_id)
        if parent:
            parent.updated_at = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Prefab Extraction
    # ------------------------------------------------------------------

    def extract_prefab(
        self,
        instance_id: str,
        name: str,
    ) -> Optional[PrefabDefinition]:
        instance = self._instances.get(instance_id)
        if instance is None:
            return None

        now = _time_module.time()
        prefab = PrefabDefinition(
            name=name,
            description=f"Extracted from instance {instance_id[:8]}",
            created_at=now,
            updated_at=now,
        )
        source_prefab = self._prefabs.get(instance.prefab_id)
        if source_prefab:
            prefab.prefab_type = source_prefab.prefab_type
            prefab.components = {
                cid: PrefabComponent(
                    id=cid,
                    name=comp.name,
                    object_type=comp.object_type,
                    position=comp.position,
                    scale=comp.scale,
                    rotation=comp.rotation,
                    properties=dict(comp.properties),
                    behaviors=list(comp.behaviors),
                    children=list(comp.children),
                    visible=comp.visible,
                    locked=comp.locked,
                    layer=comp.layer,
                )
                for cid, comp in source_prefab.components.items()
            }
            for path, value in instance.overrides.items():
                keys = path.split(".")
                if len(keys) >= 2 and keys[0] in prefab.components:
                    comp = prefab.components[keys[0]]
                    nested = comp.properties
                    for k in keys[1:-1]:
                        if k not in nested:
                            nested[k] = {}
                        if isinstance(nested[k], dict):
                            nested = nested[k]
                        else:
                            break
                    if isinstance(nested, dict):
                        nested[keys[-1]] = value

        self._prefabs[prefab.id] = prefab
        self._index_prefab_type(prefab.id, prefab.prefab_type.value)
        self._composition_graph[prefab.id] = []
        self._creation_count += 1
        return prefab

    # ------------------------------------------------------------------
    # Search & Query
    # ------------------------------------------------------------------

    def search_prefabs(
        self,
        query: str = "",
        prefab_type: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> List[PrefabDefinition]:
        results: List[PrefabDefinition] = []

        query_lower = query.lower()
        type_filter = prefab_type.lower() if prefab_type else ""
        tag_filter_set = set(tags) if tags else set()

        for prefab in self._prefabs.values():
            if type_filter and prefab.prefab_type.value != type_filter:
                continue
            if tag_filter_set and not tag_filter_set.issubset(set(prefab.tags)):
                continue
            if query_lower:
                if query_lower not in prefab.name.lower() and query_lower not in prefab.description.lower():
                    continue
            results.append(prefab)

        return results

    def get_prefabs_by_type(self, prefab_type: str) -> List[PrefabDefinition]:
        type_lower = prefab_type.lower()
        prefab_ids = self._type_index.get(type_lower, [])
        return [
            self._prefabs[pid]
            for pid in prefab_ids
            if pid in self._prefabs
        ]

    def get_prefabs_by_tag(self, tag: str) -> List[PrefabDefinition]:
        tag_lower = tag.lower()
        prefab_ids = self._tag_index.get(tag_lower, [])
        return [
            self._prefabs[pid]
            for pid in prefab_ids
            if pid in self._prefabs
        ]

    def list_all_prefabs(self) -> List[PrefabDefinition]:
        return list(self._prefabs.values())

    # ------------------------------------------------------------------
    # Indexing Helpers
    # ------------------------------------------------------------------

    def _index_prefab_type(self, prefab_id: str, type_value: str) -> None:
        self._type_index.setdefault(type_value, []).append(prefab_id)

    def _unindex_prefab_type(self, prefab_id: str, type_value: str) -> None:
        type_list = self._type_index.get(type_value, [])
        if prefab_id in type_list:
            type_list.remove(prefab_id)

    def _index_tag(self, prefab_id: str, tag: str) -> None:
        tag_lower = tag.lower()
        self._tag_index.setdefault(tag_lower, []).append(prefab_id)

    def _unindex_tag(self, prefab_id: str, tag: str) -> None:
        tag_lower = tag.lower()
        tag_list = self._tag_index.get(tag_lower, [])
        if prefab_id in tag_list:
            tag_list.remove(prefab_id)

    def _index_instance_scene(self, instance_id: str, scene_id: str) -> None:
        self._instance_scene_index.setdefault(scene_id, []).append(instance_id)

    def _unindex_instance_scene(self, instance_id: str) -> None:
        for scene_list in self._instance_scene_index.values():
            if instance_id in scene_list:
                scene_list.remove(instance_id)

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_composer_stats(self) -> Dict[str, Any]:
        type_distribution: Dict[str, int] = {}
        for ptype in PrefabType:
            count = len(self._type_index.get(ptype.value, []))
            type_distribution[ptype.value] = count

        status_counts: Dict[str, int] = {}
        for prefab in self._prefabs.values():
            k = prefab.status.value
            status_counts[k] = status_counts.get(k, 0) + 1

        total_components = sum(
            len(p.components) for p in self._prefabs.values()
        )
        total_variants = len(self._variants)
        total_instances = len(self._instances)
        total_compositions = sum(
            len(entries) for entries in self._composition_graph.values()
        )

        scene_usage: Dict[str, int] = {}
        for inst in self._instances.values():
            sid = inst.parent_scene_id
            scene_usage[sid] = scene_usage.get(sid, 0) + 1

        return {
            "total_prefabs": len(self._prefabs),
            "total_components": total_components,
            "average_components_per_prefab": (
                total_components / len(self._prefabs) if self._prefabs else 0
            ),
            "total_variants": total_variants,
            "total_instances": total_instances,
            "total_compositions": total_compositions,
            "creation_count": self._creation_count,
            "instantiation_count": self._instantiation_count,
            "type_distribution": type_distribution,
            "status_distribution": status_counts,
            "scene_usage": scene_usage,
            "unique_tags": len(self._tag_index),
        }

    def get_stats(self) -> Dict[str, Any]:
        total_components = sum(
            len(p.components) for p in self._prefabs.values()
        )

        return {
            "total_prefabs": len(self._prefabs),
            "total_components": total_components,
            "variant_count": len(self._variants),
            "instance_count": len(self._instances),
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_prefab_composer() -> PrefabComposer:
    return PrefabComposer.get_instance()