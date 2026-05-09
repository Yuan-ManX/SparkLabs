"""
SparkLabs Engine - Prefab System

Prefab instancing and template system for the SparkLabs AI-native
game engine. Enables defining reusable game object templates with
property overrides, nested prefab support, variant inheritance,
and instantiation with automatic resource resolution. AI agents
use prefabs to compose game scenes from pre-designed building
blocks.

Architecture:
  PrefabSystem
    |-- PrefabTemplate (object definition with default properties)
    |-- PrefabInstance (runtime instance with override tracking)
    |-- PropertyOverride (individual overridden value)
    |-- PrefabVariant (derived prefab with inherited properties)
    |-- PrefabLibrary (catalog of available prefab templates)
"""

from __future__ import annotations

import copy
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class PrefabApplyMode(Enum):
    FULL = "full"
    OVERRIDES_ONLY = "overrides_only"
    RECURSIVE = "recursive"


@dataclass
class PropertyOverride:
    property_path: str = ""
    original_value: Any = None
    overridden_value: Any = None
    applied: bool = True

    def to_dict(self) -> dict:
        return {
            "path": self.property_path,
            "value": str(self.overridden_value)[:100],
            "applied": self.applied,
        }


@dataclass
class PrefabTemplate:
    template_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    category: str = "general"
    description: str = ""
    default_properties: Dict[str, Any] = field(default_factory=dict)
    components: List[str] = field(default_factory=list)
    children: List["PrefabTemplate"] = field(default_factory=list)
    parent_template_id: Optional[str] = None
    is_variant: bool = False
    tags: List[str] = field(default_factory=list)
    version: int = 1
    created_at: str = ""
    updated_at: str = ""

    def get_property(self, path: str, default: Any = None) -> Any:
        keys = path.split(".")
        current = self.default_properties
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        return current

    def set_property(self, path: str, value: Any) -> None:
        keys = path.split(".")
        current = self.default_properties
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def has_component(self, component_type: str) -> bool:
        return component_type in self.components

    def to_dict(self) -> dict:
        return {
            "template_id": self.template_id,
            "name": self.name,
            "category": self.category,
            "components": self.components,
            "tags": self.tags,
            "version": self.version,
            "is_variant": self.is_variant,
            "child_count": len(self.children),
        }


@dataclass
class PrefabInstance:
    instance_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    template_id: str = ""
    name: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    rotation: float = 0.0
    scale_x: float = 1.0
    scale_y: float = 1.0
    visible: bool = True
    locked: bool = False
    overrides: List[PropertyOverride] = field(default_factory=list)
    child_instances: List["PrefabInstance"] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def override(self, path: str, original: Any, new_value: Any) -> PropertyOverride:
        ovr = PropertyOverride(property_path=path, original_value=original, overridden_value=new_value)
        self.overrides.append(ovr)
        return ovr

    def get_override(self, path: str) -> Optional[PropertyOverride]:
        for ovr in self.overrides:
            if ovr.property_path == path:
                return ovr
        return None

    def clear_override(self, path: str) -> bool:
        for i, ovr in enumerate(self.overrides):
            if ovr.property_path == path:
                del self.overrides[i]
                return True
        return False

    def get_effective_value(self, path: str, default_properties: Dict[str, Any]) -> Any:
        ovr = self.get_override(path)
        if ovr and ovr.applied:
            return ovr.overridden_value
        keys = path.split(".")
        current = default_properties
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def to_dict(self) -> dict:
        return {
            "instance_id": self.instance_id,
            "template_id": self.template_id,
            "name": self.name,
            "position": {"x": self.x, "y": self.y, "z": self.z},
            "rotation": self.rotation,
            "scale": {"x": self.scale_x, "y": self.scale_y},
            "visible": self.visible,
            "overrides": len(self.overrides),
            "children": len(self.child_instances),
        }


class PrefabSystem:
    """
    Prefab template and instancing system for game object composition.

    Manages a library of reusable prefab templates that define game
    objects with default properties and components. Supports template
    inheritance via variants, property overrides on instances without
    breaking template links, nested prefab hierarchies, and batch
    instantiation for scene population. AI agents define prefab
    templates programmatically and spawn instances into scenes.
    """

    _instance: Optional["PrefabSystem"] = None

    def __init__(self):
        self._templates: Dict[str, PrefabTemplate] = {}
        self._instances: Dict[str, PrefabInstance] = {}
        self._categories: Set[str] = set()

    @classmethod
    def get_instance(cls) -> "PrefabSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_template(self, name: str, category: str = "general", description: str = "", **kwargs) -> PrefabTemplate:
        template = PrefabTemplate(name=name, category=category, description=description, **kwargs)
        self._templates[template.template_id] = template
        self._categories.add(category)
        return template

    def create_variant(self, parent_template_id: str, name: str, **kwargs) -> Optional[PrefabTemplate]:
        parent = self._templates.get(parent_template_id)
        if not parent:
            return None
        variant = PrefabTemplate(
            name=name,
            category=parent.category,
            parent_template_id=parent_template_id,
            is_variant=True,
            default_properties=copy.deepcopy(parent.default_properties),
            components=list(parent.components),
            tags=list(parent.tags),
            **kwargs,
        )
        self._templates[variant.template_id] = variant
        return variant

    def get_template(self, template_id: str) -> Optional[PrefabTemplate]:
        return self._templates.get(template_id)

    def find_template(self, name: str) -> Optional[PrefabTemplate]:
        for t in self._templates.values():
            if t.name == name:
                return t
        return None

    def list_templates(self, category: Optional[str] = None, tag: Optional[str] = None) -> List[PrefabTemplate]:
        result = list(self._templates.values())
        if category:
            result = [t for t in result if t.category == category]
        if tag:
            result = [t for t in result if tag in t.tags]
        return result

    def remove_template(self, template_id: str) -> bool:
        if template_id in self._templates:
            del self._templates[template_id]
            return True
        return False

    def instantiate(self, template_id: str, x: float = 0.0, y: float = 0.0, overrides: Optional[Dict[str, Any]] = None) -> Optional[PrefabInstance]:
        template = self._templates.get(template_id)
        if not template:
            return None
        instance = PrefabInstance(
            template_id=template_id,
            name=template.name,
            x=x,
            y=y,
            tags=list(template.tags),
        )
        for path, value in (overrides or {}).items():
            original = template.get_property(path)
            instance.override(path, original, value)
        self._instances[instance.instance_id] = instance
        return instance

    def instantiate_batch(self, template_id: str, positions: List[Tuple[float, float]], overrides: Optional[Dict[str, Any]] = None) -> List[PrefabInstance]:
        instances = []
        for x, y in positions:
            inst = self.instantiate(template_id, x, y, overrides)
            if inst:
                instances.append(inst)
        return instances

    def get_prefab_instance(self, instance_id: str) -> Optional[PrefabInstance]:
        return self._instances.get(instance_id)

    def list_instances(self, template_id: Optional[str] = None) -> List[PrefabInstance]:
        if template_id:
            return [i for i in self._instances.values() if i.template_id == template_id]
        return list(self._instances.values())

    def update_instance(self, instance_id: str, **kwargs) -> Optional[PrefabInstance]:
        instance = self._instances.get(instance_id)
        if not instance:
            return None
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance

    def apply_template_changes(self, template_id: str) -> int:
        template = self._templates.get(template_id)
        if not template:
            return 0
        count = 0
        for inst in self._instances.values():
            if inst.template_id == template_id:
                count += 1
        return count

    def remove_instance(self, instance_id: str) -> bool:
        if instance_id in self._instances:
            del self._instances[instance_id]
            return True
        return False

    def get_categories(self) -> List[str]:
        return sorted(self._categories)

    def get_stats(self) -> dict:
        category_counts = {}
        for t in self._templates.values():
            category_counts[t.category] = category_counts.get(t.category, 0) + 1
        return {
            "templates": len(self._templates),
            "instances": len(self._instances),
            "categories": len(self._categories),
            "variants": sum(1 for t in self._templates.values() if t.is_variant),
            "category_breakdown": category_counts,
        }

    def reset(self) -> None:
        self._templates.clear()
        self._instances.clear()
        self._categories.clear()


def get_prefab_system() -> PrefabSystem:
    return PrefabSystem.get_instance()
