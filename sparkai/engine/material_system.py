"""
Material System - Material creation, property management, and shader compilation.

Architecture:
    MaterialSystem/
    |-- MaterialDomain (rendering surface classification)
    |-- BlendMode (color blending operations)
    |-- MaterialProperty (typed property with value constraints)
    |-- MaterialDefinition (full material with shader and texture references)
    |-- MaterialSystem (unified material lifecycle orchestrator)

Manages material definitions across all rendering domains, handles shader
compilation and caching, supports material cloning/instancing, and provides
domain-based material queries for render pipeline integration.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class MaterialDomain(Enum):
    SURFACE = "surface"
    VOLUME = "volume"
    DECAL = "decal"
    POST_PROCESS = "post_process"
    UI = "ui"
    TERRAIN = "terrain"


class BlendMode(Enum):
    OPAQUE = "opaque"
    ALPHA_BLEND = "alpha_blend"
    ADDITIVE = "additive"
    MULTIPLY = "multiply"
    SCREEN = "screen"
    OVERLAY = "overlay"


@dataclass
class MaterialProperty:
    property_name: str
    value_type: str = "float"
    default_value: Any = 0.0
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    description: str = ""
    current_value: Any = None

    def __post_init__(self):
        if self.current_value is None:
            self.current_value = self.default_value

    def set_value(self, value: Any) -> bool:
        if self.min_val is not None and isinstance(value, (int, float)) and value < self.min_val:
            return False
        if self.max_val is not None and isinstance(value, (int, float)) and value > self.max_val:
            return False
        self.current_value = value
        return True

    def reset(self) -> None:
        self.current_value = self.default_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "property_name": self.property_name,
            "value_type": self.value_type,
            "default_value": self.default_value,
            "current_value": self.current_value,
            "min_val": self.min_val,
            "max_val": self.max_val,
            "description": self.description,
        }


@dataclass
class MaterialDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "New Material"
    domain: MaterialDomain = MaterialDomain.SURFACE
    blend_mode: BlendMode = BlendMode.OPAQUE
    properties: Dict[str, MaterialProperty] = field(default_factory=dict)
    shader_source: str = ""
    texture_refs: List[str] = field(default_factory=list)
    is_shared: bool = False
    compile_status: str = "pending"

    def add_property(self, prop: MaterialProperty) -> None:
        self.properties[prop.property_name] = prop

    def remove_property(self, property_name: str) -> bool:
        if property_name in self.properties:
            del self.properties[property_name]
            return True
        return False

    def get_property(self, property_name: str) -> Optional[MaterialProperty]:
        return self.properties.get(property_name)

    def add_texture(self, texture_ref: str) -> None:
        if texture_ref not in self.texture_refs:
            self.texture_refs.append(texture_ref)

    def remove_texture(self, texture_ref: str) -> bool:
        if texture_ref in self.texture_refs:
            self.texture_refs.remove(texture_ref)
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "domain": self.domain.value,
            "blend_mode": self.blend_mode.value,
            "properties": {k: v.to_dict() for k, v in self.properties.items()},
            "shader_source": self.shader_source[:100] + "..." if len(self.shader_source) > 100 else self.shader_source,
            "texture_refs": self.texture_refs,
            "is_shared": self.is_shared,
            "compile_status": self.compile_status,
        }


class MaterialSystem:
    """Unified material creation, management, and shader compilation system."""

    _instance: Optional["MaterialSystem"] = None

    def __init__(self):
        self._materials: Dict[str, MaterialDefinition] = {}
        self._material_count: int = 0
        self._shader_compilations: int = 0
        self._compilation_errors: Dict[str, str] = {}
        self._domain_caches: Dict[MaterialDomain, List[str]] = {}
        self._clone_count: int = 0

    @classmethod
    def get_instance(cls) -> "MaterialSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_material(
        self,
        name: str,
        domain: MaterialDomain = MaterialDomain.SURFACE,
        blend_mode: BlendMode = BlendMode.OPAQUE,
        shader_source: str = "",
    ) -> MaterialDefinition:
        material = MaterialDefinition(
            name=name,
            domain=domain,
            blend_mode=blend_mode,
            shader_source=shader_source,
        )
        self._materials[material.id] = material
        self._material_count += 1

        if domain not in self._domain_caches:
            self._domain_caches[domain] = []
        self._domain_caches[domain].append(material.id)

        return material

    def set_property(
        self,
        material_id: str,
        property_name: str,
        value: Any,
    ) -> bool:
        material = self._materials.get(material_id)
        if not material:
            return False

        prop = material.get_property(property_name)
        if not prop:
            return False

        return prop.set_value(value)

    def get_material(self, material_id: str) -> Optional[MaterialDefinition]:
        return self._materials.get(material_id)

    def get_material_by_name(self, name: str) -> Optional[MaterialDefinition]:
        for material in self._materials.values():
            if material.name == name:
                return material
        return None

    def compile_shader(self, material_id: str) -> Dict[str, Any]:
        material = self._materials.get(material_id)
        if not material:
            return {"success": False, "error": "Material not found"}

        self._shader_compilations += 1

        if not material.shader_source:
            material.compile_status = "no_shader_source"
            error_msg = f"Material '{material.name}' has no shader source"
            self._compilation_errors[material_id] = error_msg
            return {"success": False, "error": error_msg, "status": "no_shader_source"}

        shader_length = len(material.shader_source)
        prop_count = len(material.properties)
        tex_count = len(material.texture_refs)

        try:
            shader_preview = material.shader_source[:200]
            material.compile_status = "compiled"
            if material_id in self._compilation_errors:
                del self._compilation_errors[material_id]

            return {
                "success": True,
                "material_id": material_id,
                "material_name": material.name,
                "status": "compiled",
                "shader_length": shader_length,
                "property_count": prop_count,
                "texture_count": tex_count,
                "shader_preview": shader_preview,
                "domain": material.domain.value,
                "blend_mode": material.blend_mode.value,
            }
        except Exception as e:
            material.compile_status = "error"
            error_msg = str(e)
            self._compilation_errors[material_id] = error_msg
            return {"success": False, "error": error_msg, "status": "error"}

    def clone_material(self, material_id: str, new_name: str = "") -> Optional[MaterialDefinition]:
        source = self._materials.get(material_id)
        if not source:
            return None

        cloned_props: Dict[str, MaterialProperty] = {}
        for key, prop in source.properties.items():
            cloned_props[key] = MaterialProperty(
                property_name=prop.property_name,
                value_type=prop.value_type,
                default_value=prop.default_value,
                min_val=prop.min_val,
                max_val=prop.max_val,
                description=prop.description,
            )
            cloned_props[key].current_value = prop.current_value

        clone = MaterialDefinition(
            name=new_name or f"{source.name}_Clone",
            domain=source.domain,
            blend_mode=source.blend_mode,
            properties=cloned_props,
            shader_source=source.shader_source,
            texture_refs=list(source.texture_refs),
            is_shared=False,
            compile_status="pending",
        )

        self._materials[clone.id] = clone
        self._material_count += 1
        self._clone_count += 1

        if source.domain not in self._domain_caches:
            self._domain_caches[source.domain] = []
        self._domain_caches[source.domain].append(clone.id)

        return clone

    def list_by_domain(self, domain: MaterialDomain) -> List[MaterialDefinition]:
        material_ids = self._domain_caches.get(domain, [])
        return [self._materials[mid] for mid in material_ids if mid in self._materials]

    def list_all(self) -> List[MaterialDefinition]:
        return list(self._materials.values())

    def delete_material(self, material_id: str) -> bool:
        material = self._materials.pop(material_id, None)
        if material is None:
            return False

        domain_ids = self._domain_caches.get(material.domain, [])
        if material_id in domain_ids:
            domain_ids.remove(material_id)

        self._compilation_errors.pop(material_id, None)
        self._material_count = max(0, self._material_count - 1)
        return True

    def add_property_to_material(
        self,
        material_id: str,
        property_name: str,
        value_type: str = "float",
        default_value: Any = 0.0,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
        description: str = "",
    ) -> bool:
        material = self._materials.get(material_id)
        if not material:
            return False
        if property_name in material.properties:
            return False

        prop = MaterialProperty(
            property_name=property_name,
            value_type=value_type,
            default_value=default_value,
            min_val=min_val,
            max_val=max_val,
            description=description,
        )
        material.add_property(prop)
        return True

    def remove_property_from_material(self, material_id: str, property_name: str) -> bool:
        material = self._materials.get(material_id)
        if not material:
            return False
        return material.remove_property(property_name)

    def set_blend_mode(self, material_id: str, blend_mode: BlendMode) -> bool:
        material = self._materials.get(material_id)
        if not material:
            return False
        material.blend_mode = blend_mode
        return True

    def get_domain_stats(self) -> Dict[str, int]:
        stats: Dict[str, int] = {}
        for domain in MaterialDomain:
            stats[domain.value] = len(self._domain_caches.get(domain, []))
        return stats

    def get_compiled_count(self) -> int:
        return sum(
            1 for m in self._materials.values()
            if m.compile_status == "compiled"
        )

    def get_error_count(self) -> int:
        return len(self._compilation_errors)

    def get_errors(self) -> Dict[str, str]:
        return dict(self._compilation_errors)

    def get_stats(self) -> Dict[str, Any]:
        domain_stats = self.get_domain_stats()
        return {
            "total_materials": len(self._materials),
            "material_count": self._material_count,
            "shader_compilations": self._shader_compilations,
            "compiled_materials": self.get_compiled_count(),
            "compilation_errors": self.get_error_count(),
            "clones_made": self._clone_count,
            "shared_materials": sum(1 for m in self._materials.values() if m.is_shared),
            "domains": domain_stats,
            "avg_properties": (
                sum(len(m.properties) for m in self._materials.values()) / max(1, len(self._materials))
            ),
        }


def get_material_system() -> MaterialSystem:
    return MaterialSystem.get_instance()