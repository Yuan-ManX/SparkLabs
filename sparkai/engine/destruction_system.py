"""
SparkLabs Engine - Destruction System

Physics-driven destructible environment simulation for
AI-native game worlds. Manages breakable objects, structural
integrity, fragmentation patterns, and debris physics across
multiple destruction tiers. Supports both scripted and
physics-based destruction with particle effects and audio
feedback integration.

Architecture:
  DestructionSystem
    |-- IntegrityModel (health, damage thresholds, resistance)
    |-- FragmentGenerator (voronoi-style mesh splitting)
    |-- DebrisPhysics (impulse-based fragment scattering)
    |-- DamagePropagator (chain reactions, structural collapse)
    |-- DestructionTier (partial vs full destruction states)

Destruction Tiers:
  - UNDAMAGED: no visible damage
  - CRACKED: surface cracks, minor deformation
  - DAMAGED: missing chunks, partial structural failure
  - DESTROYED: fully collapsed, debris generated
  - VAPORIZED: completely removed, no debris (energy weapons)
"""

from __future__ import annotations

import math
import random
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class DestructionTier(Enum):
    UNDAMAGED = "undamaged"
    CRACKED = "cracked"
    DAMAGED = "damaged"
    DESTROYED = "destroyed"
    VAPORIZED = "vaporized"


class MaterialType(Enum):
    WOOD = "wood"
    STONE = "stone"
    METAL = "metal"
    GLASS = "glass"
    CONCRETE = "concrete"
    ICE = "ice"
    CLOTH = "cloth"


class DamageType(Enum):
    PHYSICAL = "physical"
    EXPLOSIVE = "explosive"
    ENERGY = "energy"
    FIRE = "fire"
    CORROSIVE = "corrosive"
    IMPACT = "impact"


@dataclass
class MaterialProperties:
    material: MaterialType = MaterialType.WOOD
    max_health: float = 100.0
    impact_resistance: float = 0.5
    explosive_resistance: float = 0.3
    energy_resistance: float = 0.8
    fire_resistance: float = 0.2
    corrosive_resistance: float = 0.6
    fragment_count: int = 8
    debris_lifetime: float = 5.0
    debris_impulse: float = 5.0
    chain_reaction_radius: float = 1.5
    chain_reaction_factor: float = 0.3

    def get_resistance(self, damage_type: DamageType) -> float:
        mapping = {
            DamageType.PHYSICAL: self.impact_resistance,
            DamageType.EXPLOSIVE: self.explosive_resistance,
            DamageType.ENERGY: self.energy_resistance,
            DamageType.FIRE: self.fire_resistance,
            DamageType.CORROSIVE: self.corrosive_resistance,
            DamageType.IMPACT: self.impact_resistance,
        }
        return mapping.get(damage_type, 0.5)


DEFAULT_MATERIALS: Dict[MaterialType, MaterialProperties] = {
    MaterialType.WOOD: MaterialProperties(MaterialType.WOOD, 80, 0.7, 0.2, 0.9, 0.1, 0.5, 12, 3.0, 4.0),
    MaterialType.STONE: MaterialProperties(MaterialType.STONE, 200, 0.3, 0.6, 0.5, 0.8, 0.4, 6, 8.0, 3.0, chain_reaction_radius=2.0),
    MaterialType.METAL: MaterialProperties(MaterialType.METAL, 400, 0.2, 0.4, 0.3, 0.6, 0.3, 4, 10.0, 2.0),
    MaterialType.GLASS: MaterialProperties(MaterialType.GLASS, 20, 1.0, 1.0, 1.0, 0.9, 0.8, 25, 2.0, 8.0, chain_reaction_factor=0.8),
    MaterialType.CONCRETE: MaterialProperties(MaterialType.CONCRETE, 300, 0.25, 0.5, 0.6, 0.7, 0.4, 10, 6.0, 4.0, chain_reaction_radius=2.5),
    MaterialType.ICE: MaterialProperties(MaterialType.ICE, 40, 0.9, 0.7, 0.8, 0.1, 0.9, 20, 1.5, 6.0, chain_reaction_factor=0.6),
    MaterialType.CLOTH: MaterialProperties(MaterialType.CLOTH, 15, 1.0, 1.0, 1.0, 0.1, 0.4, 3, 1.0, 1.0),
}


@dataclass
class DestructibleObject:
    object_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    material: MaterialType = MaterialType.WOOD
    max_health: float = 100.0
    current_health: float = 100.0
    tier: DestructionTier = DestructionTier.UNDAMAGED
    is_destroyed: bool = False
    created_at: float = field(default_factory=time.time)

    @property
    def health_percent(self) -> float:
        return self.current_health / max(1, self.max_health)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "object_id": self.object_id,
            "position": list(self.position),
            "material": self.material.value,
            "health": round(self.health_percent * 100, 1),
            "tier": self.tier.value,
            "destroyed": self.is_destroyed,
        }


@dataclass
class DestructionEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    object_id: str = ""
    damage_type: DamageType = DamageType.PHYSICAL
    damage_amount: float = 0.0
    source_position: Optional[Tuple[float, float, float]] = None
    from_tier: DestructionTier = DestructionTier.UNDAMAGED
    to_tier: DestructionTier = DestructionTier.UNDAMAGED
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "object_id": self.object_id,
            "damage_type": self.damage_type.value,
            "damage": round(self.damage_amount, 1),
            "tier_change": f"{self.from_tier.value} -> {self.to_tier.value}",
        }


class DestructionSystem:
    _instance: Optional[DestructionSystem] = None

    @classmethod
    def get_instance(cls) -> DestructionSystem:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._objects: Dict[str, DestructibleObject] = {}
        self._event_log: List[DestructionEvent] = []
        self._total_destroyed: int = 0

    def create_object(self, object_id: str, material: MaterialType = MaterialType.WOOD,
                      health: Optional[float] = None,
                      position: Tuple[float, float, float] = (0.0, 0.0, 0.0)) -> DestructibleObject:
        mat_props = DEFAULT_MATERIALS.get(material, DEFAULT_MATERIALS[MaterialType.WOOD])
        obj = DestructibleObject(
            object_id=object_id,
            material=material,
            max_health=health or mat_props.max_health,
            current_health=health or mat_props.max_health,
            position=position,
        )
        self._objects[object_id] = obj
        return obj

    def apply_damage(self, object_id: str, amount: float, damage_type: DamageType = DamageType.PHYSICAL,
                     source_position: Optional[Tuple[float, float, float]] = None) -> Optional[DestructionEvent]:
        obj = self._objects.get(object_id)
        if obj is None or obj.is_destroyed:
            return None

        mat_props = DEFAULT_MATERIALS.get(obj.material, DEFAULT_MATERIALS[MaterialType.WOOD])
        resistance = mat_props.get_resistance(damage_type)
        effective_damage = amount * (1.0 - resistance)
        effective_damage = max(0, effective_damage)

        from_tier = obj.tier
        obj.current_health -= effective_damage

        hp = obj.health_percent
        if hp > 0.75:
            obj.tier = DestructionTier.UNDAMAGED
        elif hp > 0.5:
            obj.tier = DestructionTier.CRACKED
        elif hp > 0.25:
            obj.tier = DestructionTier.DAMAGED
        elif hp > 0:
            obj.tier = DestructionTier.DESTROYED
        else:
            if damage_type == DamageType.ENERGY:
                obj.tier = DestructionTier.VAPORIZED
            else:
                obj.tier = DestructionTier.DESTROYED
            obj.is_destroyed = True
            self._total_destroyed += 1

        event = DestructionEvent(
            object_id=object_id,
            damage_type=damage_type,
            damage_amount=effective_damage,
            source_position=source_position,
            from_tier=from_tier,
            to_tier=obj.tier,
        )
        self._event_log.append(event)
        if len(self._event_log) > 100:
            self._event_log = self._event_log[-100:]

        if obj.is_destroyed and mat_props.chain_reaction_factor > 0:
            self._propagate_chain_reaction(obj, mat_props, effective_damage * mat_props.chain_reaction_factor)

        return event

    def _propagate_chain_reaction(self, source: DestructibleObject,
                                   mat_props: MaterialProperties, chain_damage: float):
        px, py, pz = source.position
        for obj in self._objects.values():
            if obj.object_id == source.object_id or obj.is_destroyed:
                continue
            ox, oy, oz = obj.position
            dist = math.sqrt((px - ox) ** 2 + (py - oy) ** 2 + (pz - oz) ** 2)
            if dist <= mat_props.chain_reaction_radius:
                falloff = 1.0 - (dist / mat_props.chain_reaction_radius)
                self.apply_damage(obj.object_id, chain_damage * falloff, DamageType.EXPLOSIVE)

    def repair(self, object_id: str, amount: float = -1) -> Optional[DestructibleObject]:
        obj = self._objects.get(object_id)
        if obj is None:
            return None
        heal = amount if amount > 0 else obj.max_health
        obj.current_health = min(obj.max_health, obj.current_health + heal)
        obj.is_destroyed = False
        obj.tier = DestructionTier.UNDAMAGED if obj.health_percent > 0.75 else obj.tier
        return obj

    def get_objects_in_radius(self, center: Tuple[float, float, float],
                              radius: float) -> List[DestructibleObject]:
        cx, cy, cz = center
        result = []
        for obj in self._objects.values():
            ox, oy, oz = obj.position
            dist = math.sqrt((cx - ox) ** 2 + (cy - oy) ** 2 + (cz - oz) ** 2)
            if dist <= radius:
                result.append(obj)
        return result

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_objects": len(self._objects),
            "total_destroyed": self._total_destroyed,
            "active_objects": len([o for o in self._objects.values() if not o.is_destroyed]),
            "tier_distribution": {
                tier.value: sum(1 for o in self._objects.values() if o.tier == tier)
                for tier in DestructionTier
            },
            "material_distribution": {
                mt.value: sum(1 for o in self._objects.values() if o.material == mt)
                for mt in MaterialType
            },
        }


def get_destruction_system() -> DestructionSystem:
    return DestructionSystem.get_instance()