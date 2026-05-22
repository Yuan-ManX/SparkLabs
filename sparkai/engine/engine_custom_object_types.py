"""
SparkLabs Engine - Custom Object Type System

Modular game object type system providing property definitions, behavior
attachment, visual styling templates, and runtime instance creation. Types
form a composable inheritance chain with overwrite, extend, and final
locking modes for parent property sets and behaviors.

Architecture:
  CustomObjectTypeSystem
    |-- ObjectTypeDefinition (named type with base classification and metadata)
    |-- TypeProperty (typed properties with defaults, constraints, and UI hints)
    |-- BehaviorAttachment (named behavior modules with parameter profiles)
    |-- VisualTemplate (display configuration for editor and runtime views)
    |-- TypeInstance (runtime objects spawned from a type definition)
"""
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ObjectBaseType(Enum):
    SPRITE = "sprite"
    TILED_SPRITE = "tiled_sprite"
    TEXT = "text"
    PARTICLE = "particle"
    SHAPE = "shape"
    MESH = "mesh"
    VIDEO = "video"
    PANEL = "panel"


class PropertyType(Enum):
    STRING = "string"
    NUMBER = "number"
    BOOLEAN = "boolean"
    COLOR = "color"
    RESOURCE = "resource"
    ENUM = "enum"
    VECTOR2 = "vector2"
    VECTOR3 = "vector3"
    EXPRESSION = "expression"


class InheritMode(Enum):
    OVERWRITE = "overwrite"
    EXTEND = "extend"
    FINAL = "final"


@dataclass
class TypeProperty:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    property_type: PropertyType = PropertyType.STRING
    default_value: Any = ""
    config: Dict[str, Any] = field(default_factory=dict)
    required: bool = False
    tooltip: str = ""
    sort_order: int = 0
    parent_inherit: InheritMode = InheritMode.OVERWRITE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "property_type": self.property_type.value,
            "default_value": self.default_value,
            "config": dict(self.config), "required": self.required,
            "tooltip": self.tooltip, "sort_order": self.sort_order,
            "parent_inherit": self.parent_inherit.value,
        }


@dataclass
class BehaviorAttachment:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    behavior_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    is_enabled: bool = True
    priority: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "behavior_name": self.behavior_name,
            "parameters": dict(self.parameters),
            "is_enabled": self.is_enabled, "priority": self.priority,
        }


@dataclass
class VisualTemplate:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sprite_source: str = ""
    sprite_index: int = 0
    tint_color: str = "#FFFFFF"
    opacity: float = 1.0
    render_layer: int = 0
    z_index: int = 0
    scale: float = 1.0
    show_bounding_box: bool = False
    custom_material: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "sprite_source": self.sprite_source,
            "sprite_index": self.sprite_index,
            "tint_color": self.tint_color,
            "opacity": round(self.opacity, 2),
            "render_layer": self.render_layer,
            "z_index": self.z_index,
            "scale": round(self.scale, 2),
            "show_bounding_box": self.show_bounding_box,
            "custom_material": self.custom_material,
        }


@dataclass
class ObjectTypeDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    base_type: ObjectBaseType = ObjectBaseType.SPRITE
    description: str = ""
    icon: str = "default"
    properties: Dict[str, TypeProperty] = field(default_factory=dict)
    behaviors: Dict[str, BehaviorAttachment] = field(default_factory=dict)
    visual_template: Optional[VisualTemplate] = None
    parent_type_id: str = ""
    tags: List[str] = field(default_factory=list)
    is_abstract: bool = False
    created_at: float = field(default_factory=time.time)
    version: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "name": self.name,
            "base_type": self.base_type.value,
            "description": self.description, "icon": self.icon,
            "property_count": len(self.properties),
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "behavior_count": len(self.behaviors),
            "behaviors": {k: v.to_dict() for k, v in self.behaviors.items()},
            "visual_template": self.visual_template.to_dict() if self.visual_template else None,
            "parent_type_id": self.parent_type_id,
            "tags": list(self.tags), "is_abstract": self.is_abstract,
            "created_at": self.created_at, "version": self.version,
        }


@dataclass
class TypeInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    type_id: str = ""
    type_name: str = ""
    scene_id: str = ""
    position: Dict[str, float] = field(default_factory=lambda: {"x": 0.0, "y": 0.0})
    property_values: Dict[str, Any] = field(default_factory=dict)
    enabled_behaviors: List[str] = field(default_factory=list)
    is_active: bool = True
    spawn_time: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id, "type_id": self.type_id,
            "type_name": self.type_name, "scene_id": self.scene_id,
            "position": dict(self.position),
            "property_values": dict(self.property_values),
            "enabled_behaviors": list(self.enabled_behaviors),
            "is_active": self.is_active, "spawn_time": self.spawn_time,
        }


class CustomObjectTypeSystem:
    """Modular game object type system with property and behavior composition."""

    _instance: Optional["CustomObjectTypeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._types: Dict[str, ObjectTypeDefinition] = {}
        self._instances: Dict[str, TypeInstance] = {}
        self._visual_templates: Dict[str, VisualTemplate] = {}

    @classmethod
    def get_instance(cls) -> "CustomObjectTypeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Type Definition ----

    def define_type(self, name: str, base_type: str = "sprite",
                    description: str = "", icon: str = "default",
                    parent_type_id: str = "") -> ObjectTypeDefinition:
        try:
            bt = ObjectBaseType(base_type.lower())
        except ValueError:
            bt = ObjectBaseType.SPRITE
        type_def = ObjectTypeDefinition(
            name=name, base_type=bt, description=description,
            icon=icon, parent_type_id=parent_type_id)
        if parent_type_id and parent_type_id in self._types:
            parent = self._types[parent_type_id]
            for pn, pp in parent.properties.items():
                mode = pp.parent_inherit
                if mode == InheritMode.FINAL:
                    mode = InheritMode.FINAL
                elif mode == InheritMode.EXTEND:
                    mode = InheritMode.EXTEND
                else:
                    mode = InheritMode.OVERWRITE
                type_def.properties[pn] = TypeProperty(
                    name=pp.name, property_type=pp.property_type,
                    default_value=pp.default_value, config=dict(pp.config),
                    parent_inherit=mode)
            for bn, bh in parent.behaviors.items():
                type_def.behaviors[bn] = BehaviorAttachment(
                    behavior_name=bh.behavior_name,
                    parameters=dict(bh.parameters), priority=bh.priority)
        self._types[type_def.id] = type_def
        return type_def

    # ---- Property Management ----

    def add_property(self, type_id: str, name: str,
                     property_type: str = "string",
                     default_value: Any = "",
                     config: Optional[Dict[str, Any]] = None
                     ) -> Optional[TypeProperty]:
        td = self._types.get(type_id)
        if td is None:
            return None
        existing = td.properties.get(name)
        if existing and existing.parent_inherit == InheritMode.FINAL:
            return None
        try:
            pt = PropertyType(property_type.lower())
        except ValueError:
            pt = PropertyType.STRING
        prop = TypeProperty(name=name, property_type=pt,
                            default_value=default_value, config=config or {},
                            sort_order=len(td.properties))
        td.properties[name] = prop
        td.version += 1
        return prop

    def remove_property(self, type_id: str, property_name: str) -> bool:
        td = self._types.get(type_id)
        if td is None:
            return False
        prop = td.properties.get(property_name)
        if prop and prop.parent_inherit == InheritMode.FINAL:
            return False
        if property_name in td.properties:
            del td.properties[property_name]
            td.version += 1
            return True
        return False

    # ---- Behavior Management ----

    def attach_behavior(self, type_id: str, behavior_name: str,
                        parameters: Optional[Dict[str, Any]] = None
                        ) -> Optional[BehaviorAttachment]:
        td = self._types.get(type_id)
        if td is None:
            return None
        if behavior_name in td.behaviors:
            if parameters:
                td.behaviors[behavior_name].parameters.update(parameters)
            return td.behaviors[behavior_name]
        beh = BehaviorAttachment(behavior_name=behavior_name,
                                 parameters=parameters or {},
                                 priority=len(td.behaviors))
        td.behaviors[behavior_name] = beh
        td.version += 1
        return beh

    def detach_behavior(self, type_id: str, behavior_name: str) -> bool:
        td = self._types.get(type_id)
        if td is None:
            return False
        if behavior_name in td.behaviors:
            del td.behaviors[behavior_name]
            td.version += 1
            return True
        return False

    # ---- Instance Management ----

    def create_instance(self, type_id: str, scene_id: str = "",
                        position: Optional[Dict[str, float]] = None
                        ) -> Optional[TypeInstance]:
        td = self._types.get(type_id)
        if td is None or td.is_abstract:
            return None
        pos = position or {"x": 0.0, "y": 0.0}
        values = {pn: pp.default_value for pn, pp in td.properties.items()}
        instance = TypeInstance(
            type_id=type_id, type_name=td.name, scene_id=scene_id,
            position={"x": pos.get("x", 0.0), "y": pos.get("y", 0.0)},
            property_values=values,
            enabled_behaviors=list(td.behaviors.keys()))
        self._instances[instance.id] = instance
        return instance

    # ---- Visual Template ----

    def set_visual_template(self, type_id: str,
                            template_config: Dict[str, Any]) -> bool:
        td = self._types.get(type_id)
        if td is None:
            return False
        template = VisualTemplate(
            sprite_source=str(template_config.get("sprite_source", "")),
            sprite_index=int(template_config.get("sprite_index", 0)),
            tint_color=str(template_config.get("tint_color", "#FFFFFF")),
            opacity=float(template_config.get("opacity", 1.0)),
            render_layer=int(template_config.get("render_layer", 0)),
            z_index=int(template_config.get("z_index", 0)),
            scale=float(template_config.get("scale", 1.0)),
            show_bounding_box=bool(template_config.get("show_bounding_box", False)),
            custom_material=str(template_config.get("custom_material", "")))
        td.visual_template = template
        self._visual_templates[template.id] = template
        td.version += 1
        return True

    # ---- Validation ----

    def validate_instance_config(self, type_id: str,
                                  instance_config: Dict[str, Any]
                                  ) -> Dict[str, Any]:
        td = self._types.get(type_id)
        if td is None:
            return {"valid": False, "errors": ["Type not found"]}
        errors: List[str] = []
        for pn, pp in td.properties.items():
            value = instance_config.get(pn)
            if value is None:
                if pp.required:
                    errors.append(f"Required property '{pn}' is missing")
                continue
            err = self._validate_value(pp, value)
            if err:
                errors.append(f"Property '{pn}': {err}")
        return {"valid": len(errors) == 0, "errors": errors,
                "type_name": td.name, "type_id": type_id}

    def _validate_value(self, prop: TypeProperty, value: Any) -> str:
        pt = prop.property_type
        if pt == PropertyType.NUMBER:
            if not isinstance(value, (int, float)):
                return "expected number"
            mn, mx = prop.config.get("min"), prop.config.get("max")
            if mn is not None and value < mn:
                return f"value {value} below minimum {mn}"
            if mx is not None and value > mx:
                return f"value {value} above maximum {mx}"
        elif pt == PropertyType.STRING:
            if not isinstance(value, str):
                return "expected string"
            ml = prop.config.get("max_length")
            if ml is not None and len(value) > ml:
                return f"string too long ({len(value)} > {ml})"
        elif pt == PropertyType.BOOLEAN:
            if not isinstance(value, bool):
                return "expected boolean"
        elif pt == PropertyType.COLOR:
            if not isinstance(value, str) or not value.startswith("#"):
                return "expected hex color string"
        elif pt == PropertyType.ENUM:
            opts = prop.config.get("options", [])
            if opts and value not in opts:
                return f"'{value}' not in allowed options: {opts}"
        elif pt == PropertyType.VECTOR2:
            if not isinstance(value, dict) or "x" not in value or "y" not in value:
                return "expected {x, y} dict"
        elif pt == PropertyType.VECTOR3:
            if not isinstance(value, dict) or not all(
                    k in value for k in ("x", "y", "z")):
                return "expected {x, y, z} dict"
        elif pt == PropertyType.RESOURCE:
            if not isinstance(value, str):
                return "expected resource path string"
        return ""

    # ---- Querying ----

    def list_types(self, base_type: Optional[str] = None,
                   tag: Optional[str] = None) -> List[ObjectTypeDefinition]:
        types = list(self._types.values())
        if base_type:
            try:
                bt = ObjectBaseType(base_type.lower())
                types = [t for t in types if t.base_type == bt]
            except ValueError:
                return []
        if tag:
            types = [t for t in types if tag in t.tags]
        return types

    def get_type(self, type_id: str) -> Optional[ObjectTypeDefinition]:
        return self._types.get(type_id)

    def clone_type(self, type_id: str, new_name: str
                   ) -> Optional[ObjectTypeDefinition]:
        source = self._types.get(type_id)
        if source is None:
            return None
        cloned = ObjectTypeDefinition(
            name=new_name, base_type=source.base_type,
            description=f"Clone of {source.name}",
            icon=source.icon, tags=list(source.tags))
        for pn, pp in source.properties.items():
            cloned.properties[pn] = TypeProperty(
                name=pp.name, property_type=pp.property_type,
                default_value=pp.default_value, config=dict(pp.config),
                required=pp.required, tooltip=pp.tooltip,
                sort_order=pp.sort_order)
        for bn, bh in source.behaviors.items():
            cloned.behaviors[bn] = BehaviorAttachment(
                behavior_name=bh.behavior_name,
                parameters=dict(bh.parameters), priority=bh.priority)
        if source.visual_template:
            sv = source.visual_template
            cloned.visual_template = VisualTemplate(
                sprite_source=sv.sprite_source, sprite_index=sv.sprite_index,
                tint_color=sv.tint_color, opacity=sv.opacity,
                render_layer=sv.render_layer, z_index=sv.z_index,
                scale=sv.scale, show_bounding_box=sv.show_bounding_box,
                custom_material=sv.custom_material)
        self._types[cloned.id] = cloned
        return cloned

    def get_stats(self) -> Dict[str, Any]:
        btc: Dict[str, int] = {}
        for t in self._types.values():
            k = t.base_type.value
            btc[k] = btc.get(k, 0) + 1
        return {
            "total_types": len(self._types),
            "total_instances": len(self._instances),
            "total_properties": sum(
                len(t.properties) for t in self._types.values()),
            "total_behaviors": sum(
                len(t.behaviors) for t in self._types.values()),
            "total_visual_templates": sum(
                1 for t in self._types.values() if t.visual_template),
            "base_type_distribution": btc,
        }


def get_custom_object_types() -> CustomObjectTypeSystem:
    return CustomObjectTypeSystem.get_instance()