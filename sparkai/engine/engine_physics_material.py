"""
SparkLabs Engine - Physics Material Library

Surface-based collision response and interaction properties system.
Defines physical surface types, pairwise material interactions,
contact response computation, and material templating for rapid
prototyping of physics behaviors.

Architecture:
  PhysicsMaterialLibrary
    |-- MaterialRegistry (catalog of named surface materials)
    |-- InteractionMatrix (pairwise material-to-material response curves)
    |-- ContactSolver (impact response computation from material pairs)
    |-- TemplateManager (material presets with override application)
    |-- FrictionEngine (model-aware friction coefficient calculation)

Material Properties:
  - DENSITY: mass per unit volume (kg/m^3)
  - FRICTION: coefficient of friction (0.0 to 1.0+)
  - RESTITUTION: bounciness coefficient (0.0 to 1.0)
  - ROUGHNESS: surface micro-texture scale
  - HARDNESS: resistance to deformation
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SurfaceType(Enum):
    """Physical surface classification for collision response lookup."""
    METAL = "metal"
    WOOD = "wood"
    ICE = "ice"
    RUBBER = "rubber"
    GLASS = "glass"
    FABRIC = "fabric"
    STONE = "stone"
    WATER = "water"


class FrictionModel(Enum):
    """Friction force computation model for sliding and static contacts."""
    COULOMB = "coulomb"
    STRIBECK = "stribeck"
    VISCOUS = "viscous"


class BounceProfile(Enum):
    """Restitution behavior profile for collision response."""
    ELASTIC = "elastic"
    SEMI_ELASTIC = "semi_elastic"
    PLASTIC = "plastic"
    ENERGY_ABSORBING = "energy_absorbing"


@dataclass
class PhysicsMaterial:
    """Named surface material with physical collision properties."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    surface_type: SurfaceType = SurfaceType.STONE
    density: float = 1.0
    friction: float = 0.5
    restitution: float = 0.3
    friction_model: FrictionModel = FrictionModel.COULOMB
    bounce_profile: BounceProfile = BounceProfile.SEMI_ELASTIC
    roughness: float = 0.3
    hardness: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "surface_type": self.surface_type.value,
            "density": self.density,
            "friction": self.friction,
            "restitution": self.restitution,
            "friction_model": self.friction_model.value,
            "bounce_profile": self.bounce_profile.value,
            "roughness": self.roughness,
            "hardness": self.hardness,
            "metadata": self.metadata,
        }


@dataclass
class SurfaceInteraction:
    """Pairwise interaction definition between two material surfaces."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    material_a_id: str = ""
    material_b_id: str = ""
    friction_coefficient: float = 0.5
    restitution: float = 0.3
    override_enabled: bool = True
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "material_a_id": self.material_a_id,
            "material_b_id": self.material_b_id,
            "friction_coefficient": self.friction_coefficient,
            "restitution": self.restitution,
            "override_enabled": self.override_enabled,
            "notes": self.notes,
        }


@dataclass
class MaterialTemplate:
    """Reusable material preset for applying property overrides."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    base_material_id: str = ""
    overrides: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "base_material_id": self.base_material_id,
            "overrides": self.overrides,
            "created_at": self.created_at,
        }


@dataclass
class ContactResponse:
    """Result of resolving a contact event between two surface materials."""
    contact_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    material_a_id: str = ""
    material_b_id: str = ""
    impact_velocity: float = 0.0
    normal_force: float = 0.0
    friction_force: float = 0.0
    bounce_velocity: float = 0.0
    energy_loss: float = 0.0
    stick_threshold: float = 0.0
    slide_direction: float = 0.0
    contact_normal: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contact_id": self.contact_id,
            "material_a_id": self.material_a_id,
            "material_b_id": self.material_b_id,
            "impact_velocity": self.impact_velocity,
            "normal_force": self.normal_force,
            "friction_force": self.friction_force,
            "bounce_velocity": self.bounce_velocity,
            "energy_loss": self.energy_loss,
            "stick_threshold": self.stick_threshold,
            "slide_direction": self.slide_direction,
            "contact_normal": self.contact_normal,
        }


class PhysicsMaterialLibrary:
    """
    Central registry for surface materials, pairwise interactions,
    contact response resolution, and material templating.

    Provides lookup-based collision response computation from named
    materials, enabling consistent physics behavior across all game
    objects. Supports template-based material authoring for rapid
    iteration on surface properties.
    """

    _instance: Optional["PhysicsMaterialLibrary"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_MATERIALS = 500
    MAX_INTERACTIONS = 2000
    MAX_TEMPLATES = 100

    # ------------------------------------------------------------------
    # Built-in default material names
    # ------------------------------------------------------------------

    _DEFAULT_MATERIALS = {
        "default": {
            "surface_type": SurfaceType.STONE, "density": 1.0,
            "friction": 0.5, "restitution": 0.3,
            "friction_model": FrictionModel.COULOMB,
            "bounce_profile": BounceProfile.SEMI_ELASTIC,
            "roughness": 0.3, "hardness": 0.7,
        },
        "steel": {
            "surface_type": SurfaceType.METAL, "density": 7.8,
            "friction": 0.42, "restitution": 0.25,
            "friction_model": FrictionModel.COULOMB,
            "bounce_profile": BounceProfile.SEMI_ELASTIC,
            "roughness": 0.15, "hardness": 0.95,
        },
        "ice": {
            "surface_type": SurfaceType.ICE, "density": 0.92,
            "friction": 0.05, "restitution": 0.1,
            "friction_model": FrictionModel.STRIBECK,
            "bounce_profile": BounceProfile.PLASTIC,
            "roughness": 0.02, "hardness": 0.2,
        },
        "rubber": {
            "surface_type": SurfaceType.RUBBER, "density": 1.2,
            "friction": 0.95, "restitution": 0.7,
            "friction_model": FrictionModel.COULOMB,
            "bounce_profile": BounceProfile.ELASTIC,
            "roughness": 0.5, "hardness": 0.35,
        },
        "glass": {
            "surface_type": SurfaceType.GLASS, "density": 2.5,
            "friction": 0.3, "restitution": 0.15,
            "friction_model": FrictionModel.COULOMB,
            "bounce_profile": BounceProfile.ENERGY_ABSORBING,
            "roughness": 0.05, "hardness": 0.85,
        },
        "wood": {
            "surface_type": SurfaceType.WOOD, "density": 0.7,
            "friction": 0.55, "restitution": 0.2,
            "friction_model": FrictionModel.COULOMB,
            "bounce_profile": BounceProfile.SEMI_ELASTIC,
            "roughness": 0.4, "hardness": 0.5,
        },
        "fabric": {
            "surface_type": SurfaceType.FABRIC, "density": 0.3,
            "friction": 0.75, "restitution": 0.05,
            "friction_model": FrictionModel.VISCOUS,
            "bounce_profile": BounceProfile.ENERGY_ABSORBING,
            "roughness": 0.7, "hardness": 0.1,
        },
        "water": {
            "surface_type": SurfaceType.WATER, "density": 1.0,
            "friction": 0.01, "restitution": 0.0,
            "friction_model": FrictionModel.VISCOUS,
            "bounce_profile": BounceProfile.ENERGY_ABSORBING,
            "roughness": 0.0, "hardness": 0.0,
        },
    }

    def __init__(self) -> None:
        self._materials: Dict[str, PhysicsMaterial] = {}
        self._interactions: Dict[str, SurfaceInteraction] = {}
        self._templates: Dict[str, MaterialTemplate] = {}
        self._interaction_lookup: Dict[str, Dict[str, str]] = {}
        self._total_contacts_resolved: int = 0
        self._total_templates_applied: int = 0

    @classmethod
    def get_instance(cls) -> "PhysicsMaterialLibrary":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Material Definition
    # ------------------------------------------------------------------

    def define_material(
        self,
        name: str,
        surface_type: str = "stone",
        density: float = 1.0,
        friction: float = 0.5,
        restitution: float = 0.3,
        friction_model: str = "coulomb",
        bounce_profile: str = "semi_elastic",
        roughness: float = 0.3,
        hardness: float = 0.7,
    ) -> PhysicsMaterial:
        if len(self._materials) >= self.MAX_MATERIALS:
            raise RuntimeError(
                f"Material limit reached ({self.MAX_MATERIALS}). "
                "Remove unused materials before defining new ones."
            )

        try:
            st = SurfaceType(surface_type.lower())
        except ValueError:
            st = SurfaceType.STONE

        try:
            fm = FrictionModel(friction_model.lower())
        except ValueError:
            fm = FrictionModel.COULOMB

        try:
            bp = BounceProfile(bounce_profile.lower())
        except ValueError:
            bp = BounceProfile.SEMI_ELASTIC

        material = PhysicsMaterial(
            name=name,
            surface_type=st,
            density=max(0.001, density),
            friction=max(0.0, min(2.0, friction)),
            restitution=max(0.0, min(1.0, restitution)),
            friction_model=fm,
            bounce_profile=bp,
            roughness=max(0.0, min(1.0, roughness)),
            hardness=max(0.0, min(1.0, hardness)),
        )
        self._materials[material.id] = material
        return material

    def get_material(self, material_id: str) -> Optional[PhysicsMaterial]:
        return self._materials.get(material_id)

    def find_material_by_name(self, name: str) -> Optional[PhysicsMaterial]:
        for mat in self._materials.values():
            if mat.name.lower() == name.lower():
                return mat
        return None

    def remove_material(self, material_id: str) -> bool:
        if material_id not in self._materials:
            return False
        del self._materials[material_id]
        to_remove = []
        for key, interaction in self._interactions.items():
            if interaction.material_a_id == material_id or interaction.material_b_id == material_id:
                to_remove.append(key)
        for key in to_remove:
            del self._interactions[key]
        self._interaction_lookup.pop(material_id, None)
        for lookup in self._interaction_lookup.values():
            lookup.pop(material_id, None)
        return True

    # ------------------------------------------------------------------
    # Material Palette
    # ------------------------------------------------------------------

    def get_material_palette(self) -> List[PhysicsMaterial]:
        return list(self._materials.values())

    def seed_default_materials(self) -> List[PhysicsMaterial]:
        seeded: List[PhysicsMaterial] = []
        for name, props in self._DEFAULT_MATERIALS.items():
            existing = self.find_material_by_name(name)
            if existing is not None:
                seeded.append(existing)
                continue
            mat = self.define_material(
                name=name,
                surface_type=props["surface_type"].value,
                density=props["density"],
                friction=props["friction"],
                restitution=props["restitution"],
                friction_model=props["friction_model"].value,
                bounce_profile=props["bounce_profile"].value,
                roughness=props["roughness"],
                hardness=props["hardness"],
            )
            seeded.append(mat)
        return seeded

    # ------------------------------------------------------------------
    # Surface Interactions
    # ------------------------------------------------------------------

    def define_interaction(
        self,
        material_a_id: str,
        material_b_id: str,
        friction_coefficient: float = 0.5,
        restitution: float = 0.3,
        notes: str = "",
    ) -> SurfaceInteraction:
        if len(self._interactions) >= self.MAX_INTERACTIONS:
            raise RuntimeError(
                f"Interaction limit reached ({self.MAX_INTERACTIONS})."
            )

        material_a = self._materials.get(material_a_id)
        material_b = self._materials.get(material_b_id)
        if material_a is None or material_b is None:
            raise ValueError("Both materials must be defined before creating an interaction.")

        a, b = sorted([material_a_id, material_b_id])
        interaction = SurfaceInteraction(
            material_a_id=a,
            material_b_id=b,
            friction_coefficient=max(0.0, friction_coefficient),
            restitution=max(0.0, min(1.0, restitution)),
            override_enabled=True,
            notes=notes,
        )
        self._interactions[interaction.id] = interaction

        if a not in self._interaction_lookup:
            self._interaction_lookup[a] = {}
        self._interaction_lookup[a][b] = interaction.id
        if b not in self._interaction_lookup:
            self._interaction_lookup[b] = {}
        self._interaction_lookup[b][a] = interaction.id

        return interaction

    def get_interaction(
        self, material_a_id: str, material_b_id: str,
    ) -> Optional[SurfaceInteraction]:
        a, b = sorted([material_a_id, material_b_id])
        lookup = self._interaction_lookup.get(a, {})
        interaction_id = lookup.get(b)
        if interaction_id is None:
            return None
        return self._interactions.get(interaction_id)

    # ------------------------------------------------------------------
    # Contact Resolution
    # ------------------------------------------------------------------

    def resolve_contact(
        self,
        material_a_id: str,
        material_b_id: str,
        impact_velocity: float = 0.0,
        normal_force: float = 0.0,
    ) -> ContactResponse:
        material_a = self._materials.get(material_a_id)
        material_b = self._materials.get(material_b_id)

        if material_a is None or material_b is None:
            raise ValueError("Both materials must be defined to resolve contact.")

        interaction = self.get_interaction(material_a_id, material_b_id)

        if interaction is not None and interaction.override_enabled:
            friction_coeff = interaction.friction_coefficient
            restitution_coeff = interaction.restitution
        else:
            friction_coeff = (material_a.friction + material_b.friction) * 0.5
            restitution_coeff = min(material_a.restitution, material_b.restitution)

        bounce_velocity = impact_velocity * restitution_coeff
        energy_loss = 0.5 * abs(impact_velocity) * (1.0 - restitution_coeff)

        friction_force = friction_coeff * max(0.0, normal_force)
        stick_threshold = friction_coeff * 0.15

        contact_id = uuid.uuid4().hex
        self._total_contacts_resolved += 1

        return ContactResponse(
            contact_id=contact_id,
            material_a_id=material_a_id,
            material_b_id=material_b_id,
            impact_velocity=impact_velocity,
            normal_force=normal_force,
            friction_force=friction_force,
            bounce_velocity=bounce_velocity,
            energy_loss=energy_loss,
            stick_threshold=stick_threshold,
            slide_direction=0.0,
            contact_normal=0.0,
        )

    # ------------------------------------------------------------------
    # Friction Computation
    # ------------------------------------------------------------------

    def compute_friction(
        self,
        material_a: PhysicsMaterial,
        material_b: PhysicsMaterial,
        sliding: bool = False,
    ) -> float:
        interaction = self.get_interaction(material_a.id, material_b.id)
        if interaction is not None and interaction.override_enabled:
            base = interaction.friction_coefficient
        else:
            base = (material_a.friction + material_b.friction) * 0.5

        model: FrictionModel = material_a.friction_model
        if material_b.friction_model.value == FrictionModel.STRIBECK.value:
            model = material_b.friction_model
        elif material_b.friction_model.value == FrictionModel.VISCOUS.value:
            model = material_b.friction_model

        if model == FrictionModel.COULOMB:
            return base
        elif model == FrictionModel.STRIBECK:
            if sliding:
                return base * 0.7
            else:
                return base * 0.95
        elif model == FrictionModel.VISCOUS:
            return base * (1.0 + (material_a.roughness + material_b.roughness) * 0.3)
        return base

    # ------------------------------------------------------------------
    # Material Templates
    # ------------------------------------------------------------------

    def create_template(
        self,
        name: str,
        base_material_id: str,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> MaterialTemplate:
        if len(self._templates) >= self.MAX_TEMPLATES:
            raise RuntimeError(
                f"Template limit reached ({self.MAX_TEMPLATES})."
            )

        if base_material_id not in self._materials:
            raise ValueError("Base material must exist to create a template.")

        template = MaterialTemplate(
            name=name,
            base_material_id=base_material_id,
            overrides=dict(overrides or {}),
        )
        self._templates[template.id] = template
        return template

    def apply_template_to_material(
        self, template_id: str, material_id: str,
    ) -> bool:
        template = self._templates.get(template_id)
        material = self._materials.get(material_id)
        if template is None or material is None:
            return False

        valid_attrs = {
            "density", "friction", "restitution", "roughness", "hardness",
        }
        for key, value in template.overrides.items():
            if key in valid_attrs:
                try:
                    clamped = max(0.0, min(2.0, float(value))) if key == "friction" else \
                               max(0.0, min(1.0, float(value)))
                    setattr(material, key, clamped)
                except (TypeError, ValueError):
                    continue
            elif key == "surface_type":
                try:
                    material.surface_type = SurfaceType(str(value).lower())
                except ValueError:
                    continue
            elif key == "friction_model":
                try:
                    material.friction_model = FrictionModel(str(value).lower())
                except ValueError:
                    continue
            elif key == "bounce_profile":
                try:
                    material.bounce_profile = BounceProfile(str(value).lower())
                except ValueError:
                    continue
            elif key == "metadata":
                material.metadata.update(value)

        self._total_templates_applied += 1
        return True

    def get_template(self, template_id: str) -> Optional[MaterialTemplate]:
        return self._templates.get(template_id)

    def list_templates(self) -> List[MaterialTemplate]:
        return list(self._templates.values())

    # ------------------------------------------------------------------
    # State Reset
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._materials.clear()
            self._interactions.clear()
            self._templates.clear()
            self._interaction_lookup.clear()
            self._total_contacts_resolved = 0
            self._total_templates_applied = 0

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        surface_counts: Dict[str, int] = {}
        for mat in self._materials.values():
            st = mat.surface_type.value
            surface_counts[st] = surface_counts.get(st, 0) + 1

        avg_friction = 0.0
        avg_restitution = 0.0
        if self._materials:
            avg_friction = sum(m.friction for m in self._materials.values()) / len(self._materials)
            avg_restitution = sum(m.restitution for m in self._materials.values()) / len(self._materials)

        return {
            "total_materials": len(self._materials),
            "max_materials": self.MAX_MATERIALS,
            "total_interactions": len(self._interactions),
            "max_interactions": self.MAX_INTERACTIONS,
            "total_templates": len(self._templates),
            "max_templates": self.MAX_TEMPLATES,
            "total_contacts_resolved": self._total_contacts_resolved,
            "total_templates_applied": self._total_templates_applied,
            "surface_type_distribution": surface_counts,
            "average_friction": round(avg_friction, 3),
            "average_restitution": round(avg_restitution, 3),
            "default_preset_count": len(self._DEFAULT_MATERIALS),
            "interaction_coverage": (
                round(
                    len(self._interaction_lookup) / max(1, len(self._materials)) * 100, 1
                )
            ),
        }


def get_physics_material() -> PhysicsMaterialLibrary:
    return PhysicsMaterialLibrary.get_instance()