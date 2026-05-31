"""
SparkLabs Engine - Collision Layers

Layer-based collision filtering system that controls which game
objects can interact with each other. Enables selective physics
interactions using bitmask-based layer checks, implementing
industry-standard collision management patterns.

Architecture:
  CollisionLayerManager
    |-- LayerDefinition (named layer with unique bit position)
    |-- LayerMask (bitmask for collision checks)
    |-- InteractionMatrix (which layers collide with which)
    |-- LayerAssigner (assign layers to game objects)
    |-- LayerQuery (find objects on specific layers)

Default Layers (32 available bit positions):
  - DEFAULT: all-around collision (bit 0, always set)
  - PLAYER: player character (bit 1)
  - ENEMY: hostile NPCs (bit 2)
  - PROJECTILE_PLAYER: player bullets (bit 3)
  - PROJECTILE_ENEMY: enemy bullets (bit 4)
  - PICKUP: collectible items (bit 5)
  - TERRAIN: ground, walls, platforms (bit 6)
  - TRIGGER: trigger zones (bit 7)
  - VEHICLE: driveable vehicles (bit 8)
  - UI: UI hit testing (bit 9)
  - SENSOR: sensor-only detection (bit 10)
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from enum import Enum, Flag, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class LayerFlag(Flag):
    DEFAULT = 1 << 0
    PLAYER = 1 << 1
    ENEMY = 1 << 2
    PROJECTILE_PLAYER = 1 << 3
    PROJECTILE_ENEMY = 1 << 4
    PICKUP = 1 << 5
    TERRAIN = 1 << 6
    TRIGGER = 1 << 7
    VEHICLE = 1 << 8
    UI = 1 << 9
    SENSOR = 1 << 10
    CUSTOM_11 = 1 << 11
    CUSTOM_12 = 1 << 12
    CUSTOM_13 = 1 << 13
    CUSTOM_14 = 1 << 14
    CUSTOM_15 = 1 << 15
    CUSTOM_16 = 1 << 16
    CUSTOM_17 = 1 << 17
    CUSTOM_18 = 1 << 18
    CUSTOM_19 = 1 << 19
    CUSTOM_20 = 1 << 20
    ALL = (1 << 32) - 1
    NONE = 0


default_interactions = (
    (LayerFlag.PLAYER, LayerFlag.PICKUP),
    (LayerFlag.PLAYER, LayerFlag.TRIGGER),
    (LayerFlag.PLAYER, LayerFlag.VEHICLE),
    (LayerFlag.PLAYER, LayerFlag.ENEMY),
    (LayerFlag.PLAYER, LayerFlag.TERRAIN),
    (LayerFlag.ENEMY, LayerFlag.TERRAIN),
    (LayerFlag.ENEMY, LayerFlag.PROJECTILE_PLAYER),
    (LayerFlag.PLAYER, LayerFlag.PROJECTILE_ENEMY),
    (LayerFlag.PROJECTILE_PLAYER, LayerFlag.TERRAIN),
    (LayerFlag.PROJECTILE_ENEMY, LayerFlag.TERRAIN),
)


@dataclass
class LayerDefinition:
    layer_name: str = ""
    flag: LayerFlag = LayerFlag.CUSTOM_11
    description: str = ""
    bit_position: int = 0


@dataclass
class LayerMask:
    mask_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    layer_bits: int = LayerFlag.DEFAULT.value
    description: str = ""

    @property
    def flag(self) -> LayerFlag:
        return LayerFlag(self.layer_bits)

    def has_layer(self, layer: LayerFlag) -> bool:
        return bool(self.layer_bits & layer.value)

    def add_layer(self, layer: LayerFlag) -> None:
        self.layer_bits |= layer.value

    def remove_layer(self, layer: LayerFlag) -> None:
        self.layer_bits &= ~layer.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mask_id": self.mask_id,
            "layer_bits": self.layer_bits,
            "active_layers": [f.name for f in LayerFlag if f not in (LayerFlag.ALL, LayerFlag.NONE) and self.has_layer(f)],
            "description": self.description,
        }


@dataclass
class CollisionRule:
    layer_a: LayerFlag = LayerFlag.DEFAULT
    layer_b: LayerFlag = LayerFlag.DEFAULT
    should_collide: bool = True
    generate_events: bool = False


class CollisionLayerManager:
    """Layer-based collision filtering for game objects."""

    _instance: Optional["CollisionLayerManager"] = None
    _lock = threading.Lock()

    MAX_LAYERS = 32
    MAX_RULES = 256

    def __init__(self):
        self._interaction_matrix: Dict[Tuple[LayerFlag, LayerFlag], bool] = {}
        self._custom_layers: Dict[str, LayerDefinition] = {}
        self._object_masks: Dict[str, LayerMask] = {}
        self._register_default_matrix()

    @classmethod
    def get_instance(cls) -> "CollisionLayerManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _register_default_matrix(self) -> None:
        self.set_interaction(LayerFlag.DEFAULT, LayerFlag.DEFAULT, True)
        self.set_interaction(LayerFlag.DEFAULT, LayerFlag.TERRAIN, True)
        for layer_a, layer_b in default_interactions:
            self.set_interaction(layer_a, layer_b, True)
            self.set_interaction(layer_b, layer_a, True)

    def set_interaction(
        self,
        layer_a: LayerFlag,
        layer_b: LayerFlag,
        should_collide: bool = True,
    ) -> None:
        self._interaction_matrix[(layer_a, layer_b)] = should_collide

    def should_collide(
        self,
        layer_a: LayerFlag,
        layer_b: LayerFlag,
    ) -> bool:
        result = self._interaction_matrix.get((layer_a, layer_b))
        if result is not None:
            return result
        result = self._interaction_matrix.get((layer_b, layer_a))
        if result is not None:
            return result
        return True

    def check_collision(
        self,
        mask_a: int,
        mask_b: int,
    ) -> bool:
        for flag_a in LayerFlag:
            if not (mask_a & flag_a.value):
                continue
            for flag_b in LayerFlag:
                if not (mask_b & flag_b.value):
                    continue
                if self.should_collide(flag_a, flag_b):
                    return True
        return False

    def assign_mask(
        self,
        object_id: str,
        layers: Optional[LayerFlag] = None,
        description: str = "",
    ) -> LayerMask:
        bits = layers.value if layers else LayerFlag.DEFAULT.value
        mask = LayerMask(
            layer_bits=bits,
            description=description,
        )
        self._object_masks[object_id] = mask
        return mask

    def get_mask(self, object_id: str) -> Optional[LayerMask]:
        return self._object_masks.get(object_id)

    def update_mask(
        self,
        object_id: str,
        layers: LayerFlag,
    ) -> Optional[LayerMask]:
        mask = self._object_masks.get(object_id)
        if mask:
            mask.layer_bits = layers.value
        return mask

    def remove_mask(self, object_id: str) -> bool:
        if object_id in self._object_masks:
            del self._object_masks[object_id]
            return True
        return False

    def find_objects_on_layer(self, layer: LayerFlag) -> List[str]:
        return [
            oid
            for oid, mask in self._object_masks.items()
            if mask.has_layer(layer)
        ]

    def create_custom_layer(
        self,
        name: str,
        description: str = "",
    ) -> Optional[LayerDefinition]:
        used_bits = {
            ld.bit_position
            for ld in self._custom_layers.values()
        }
        for pos in range(11, self.MAX_LAYERS):
            if pos not in used_bits:
                flag = LayerFlag(1 << pos)
                layer_def = LayerDefinition(
                    layer_name=name,
                    flag=flag,
                    description=description,
                    bit_position=pos,
                )
                self._custom_layers[name] = layer_def
                return layer_def
        return None

    def get_layer_flag(self, layer_name: str) -> Optional[LayerFlag]:
        try:
            return LayerFlag[layer_name.upper()]
        except KeyError:
            layer_def = self._custom_layers.get(layer_name)
            if layer_def:
                return layer_def.flag
        return None

    def list_layers(self) -> List[Dict[str, Any]]:
        layers = []
        for flag in LayerFlag:
            if flag == LayerFlag.ALL or flag == LayerFlag.NONE:
                continue
            layers.append({
                "name": flag.name,
                "bit_position": flag.value.bit_length() - 1 if flag.value > 0 else 0,
                "bit_value": flag.value,
                "is_default": True,
            })
        return layers

    def list_interactions(self) -> List[Dict[str, Any]]:
        return [
            {
                "layer_a": a.name,
                "layer_b": b.name,
                "should_collide": v,
            }
            for (a, b), v in self._interaction_matrix.items()
        ]

    def list_object_masks(self) -> List[Dict[str, Any]]:
        return [
            {"object_id": oid, "mask": mask.to_dict()}
            for oid, mask in self._object_masks.items()
        ]

    def clear_interactions(self) -> None:
        self._interaction_matrix.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "interaction_rules": len(self._interaction_matrix),
            "custom_layers": len(self._custom_layers),
            "object_masks": len(self._object_masks),
            "total_available_layers": self.MAX_LAYERS,
            "objects_by_layer": {
                f.name: len(self.find_objects_on_layer(f))
                for f in LayerFlag
                if f not in (LayerFlag.ALL, LayerFlag.NONE)
                and self.find_objects_on_layer(f)
            },
        }


def get_collision_layer_manager() -> CollisionLayerManager:
    return CollisionLayerManager.get_instance()