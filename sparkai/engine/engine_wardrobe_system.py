"""
SparkLabs Engine - Wardrobe System

A cosmetic appearance, transmog, and dye system for the SparkLabs AI-native
game engine. Manages cosmetic skins that override item visuals without
changing stats, outfit presets that bundle multiple cosmetics, dye channels
for color customization, and wardrobe slots for per-character appearance
profiles. Supports unlock-based acquisition, rarity tiers, and seasonal
cosmetic collections.

Each cosmetic skin maps to an equipment slot (head, chest, legs, etc.) and
overrides the visual appearance of whatever stat-bearing item is equipped.
Dyes are applied to specific dye channels on cosmetics to customize colors.
Outfits bundle a complete set of cosmetics into a single preset that can be
swapped instantly.

Architecture:
  WardrobeSystem (singleton)
    |-- CosmeticRarity, EquipmentSlot, DyeChannel, WardrobeEventKind
    |-- DyeDefinition, CosmeticSkin, OutfitPreset, WardrobeProfile,
       WardrobeConfig, WardrobeStats, WardrobeSnapshot, WardrobeEvent
    |-- get_wardrobe_system

Core Capabilities:
  - register_dye / remove_dye / get_dye / list_dyes: manage the dye catalog.
  - register_cosmetic / remove_cosmetic / get_cosmetic / list_cosmetics:
    manage the cosmetic skin catalog.
  - register_outfit / remove_outfit / get_outfit / list_outfits: manage
    outfit presets.
  - register_profile / remove_profile / get_profile / list_profiles: manage
    per-character wardrobe profiles.
  - equip_cosmetic / unequip_cosmetic: equip/unequip cosmetics on profiles.
  - apply_dye / remove_dye_from_slot: apply/remove dyes on cosmetic slots.
  - activate_outfit: apply a full outfit preset to a profile.
  - unlock_cosmetic: mark a cosmetic as unlocked for a profile.
  - tick: advance time-based features.
  - set_config / get_config: global tuning.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`WardrobeSystem.get_instance` or the module-level
:func:`get_wardrobe_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_DYES: int = 200
_MAX_COSMETICS: int = 1000
_MAX_OUTFITS: int = 200
_MAX_PROFILES: int = 500
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class CosmeticRarity(str, Enum):
    """Rarity tier of a cosmetic skin."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class EquipmentSlot(str, Enum):
    """Equipment slot that a cosmetic overrides."""
    HEAD = "head"
    CHEST = "chest"
    LEGS = "legs"
    FEET = "feet"
    HANDS = "hands"
    SHOULDERS = "shoulders"
    BACK = "back"
    WEAPON = "weapon"
    OFFHAND = "offhand"


class WardrobeEventKind(str, Enum):
    """Audit event types emitted by the wardrobe system."""
    DYE_REGISTERED = "dye_registered"
    DYE_REMOVED = "dye_removed"
    COSMETIC_REGISTERED = "cosmetic_registered"
    COSMETIC_REMOVED = "cosmetic_removed"
    OUTFIT_REGISTERED = "outfit_registered"
    OUTFIT_REMOVED = "outfit_removed"
    PROFILE_REGISTERED = "profile_registered"
    PROFILE_REMOVED = "profile_removed"
    COSMETIC_EQUIPPED = "cosmetic_equipped"
    COSMETIC_UNEQUIPPED = "cosmetic_unequipped"
    DYE_APPLIED = "dye_applied"
    DYE_REMOVED_FROM_SLOT = "dye_removed_from_slot"
    OUTFIT_ACTIVATED = "outfit_activated"
    COSMETIC_UNLOCKED = "cosmetic_unlocked"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class DyeDefinition:
    """A dye catalog entry."""
    dye_id: str
    name: str = ""
    color: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    hex_color: str = "#FFFFFF"
    rarity: str = CosmeticRarity.COMMON.value
    description: str = ""
    metallic: float = 0.0
    emissive: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CosmeticSkin:
    """A cosmetic skin catalog entry."""
    cosmetic_id: str
    name: str = ""
    slot: str = EquipmentSlot.HEAD.value
    rarity: str = CosmeticRarity.COMMON.value
    description: str = ""
    mesh_path: str = ""
    texture_path: str = ""
    icon: str = ""
    dye_channels: int = 1
    source: str = ""
    collection: str = ""
    seasonal: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class OutfitPreset:
    """A saved outfit preset bundling multiple cosmetics."""
    outfit_id: str
    name: str = ""
    description: str = ""
    cosmetics: Dict[str, str] = field(default_factory=dict)
    dyes: Dict[str, str] = field(default_factory=dict)
    created_by: str = ""
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WardrobeProfile:
    """A per-character wardrobe profile."""
    profile_id: str
    character_id: str
    name: str = ""
    equipped_cosmetics: Dict[str, str] = field(default_factory=dict)
    applied_dyes: Dict[str, str] = field(default_factory=dict)
    unlocked_cosmetics: List[str] = field(default_factory=list)
    active_outfit_id: str = ""
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WardrobeConfig:
    """Global tuning parameters for the wardrobe system."""
    max_dyes: int = 200
    max_cosmetics: int = 1000
    max_outfits: int = 200
    max_profiles: int = 500
    max_unlocked_per_profile: int = 500
    default_dye_channels: int = 2
    allow_free_cosmetics: bool = True
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WardrobeStats:
    """Aggregate statistics for the wardrobe system."""
    total_dyes: int = 0
    total_cosmetics: int = 0
    total_outfits: int = 0
    total_profiles: int = 0
    total_equipped: int = 0
    total_unlocked: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WardrobeSnapshot:
    """Full state snapshot of the wardrobe system."""
    dyes: List[Dict[str, Any]] = field(default_factory=list)
    cosmetics: List[Dict[str, Any]] = field(default_factory=list)
    outfits: List[Dict[str, Any]] = field(default_factory=list)
    profiles: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class WardrobeEvent:
    """An audit event emitted by the wardrobe system."""
    event_id: str
    kind: str
    timestamp: float
    dye_id: Optional[str] = None
    cosmetic_id: Optional[str] = None
    outfit_id: Optional[str] = None
    profile_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Wardrobe System
# ---------------------------------------------------------------------------

class WardrobeSystem:
    """Manages cosmetic skins, dyes, outfits, and wardrobe profiles."""

    _instance: Optional["WardrobeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._dyes: Dict[str, DyeDefinition] = {}
        self._cosmetics: Dict[str, CosmeticSkin] = {}
        self._outfits: Dict[str, OutfitPreset] = {}
        self._profiles: Dict[str, WardrobeProfile] = {}
        self._events: List[WardrobeEvent] = []
        self._stats = WardrobeStats()
        self._config = WardrobeConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "WardrobeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample dyes, cosmetics, outfits, and profiles."""
        with self._init_lock:
            if self._initialized:
                return

            dyes = [
                DyeDefinition(
                    dye_id="dye_crimson",
                    name="Crimson Red",
                    color=(0.8, 0.1, 0.1),
                    hex_color="#CC1A1A",
                    rarity=CosmeticRarity.COMMON.value,
                    description="A vibrant crimson dye.",
                ),
                DyeDefinition(
                    dye_id="dye_ocean",
                    name="Ocean Blue",
                    color=(0.1, 0.3, 0.8),
                    hex_color="#1A4DCC",
                    rarity=CosmeticRarity.COMMON.value,
                    description="A deep ocean blue dye.",
                ),
                DyeDefinition(
                    dye_id="dye_gold",
                    name="Royal Gold",
                    color=(1.0, 0.84, 0.0),
                    hex_color="#FFD700",
                    rarity=CosmeticRarity.RARE.value,
                    metallic=0.8,
                    description="A lustrous gold dye.",
                ),
                DyeDefinition(
                    dye_id="dye_void",
                    name="Void Black",
                    color=(0.05, 0.05, 0.05),
                    hex_color="#0D0D0D",
                    rarity=CosmeticRarity.EPIC.value,
                    emissive=0.2,
                    description="A darkness-infused dye.",
                ),
            ]
            for d in dyes:
                self._dyes[d.dye_id] = d

            cosmetics = [
                CosmeticSkin(
                    cosmetic_id="cosmic_knight_helm",
                    name="Knight Helm",
                    slot=EquipmentSlot.HEAD.value,
                    rarity=CosmeticRarity.UNCOMMON.value,
                    description="A classic knight helmet.",
                    mesh_path="mesh/helm_knight",
                    texture_path="tex/helm_knight",
                    dye_channels=2,
                    source="shop",
                    collection="knight_set",
                ),
                CosmeticSkin(
                    cosmetic_id="cosmic_knight_chest",
                    name="Knight Armor",
                    slot=EquipmentSlot.CHEST.value,
                    rarity=CosmeticRarity.UNCOMMON.value,
                    description="Classic knight chest armor.",
                    mesh_path="mesh/chest_knight",
                    texture_path="tex/chest_knight",
                    dye_channels=2,
                    source="shop",
                    collection="knight_set",
                ),
                CosmeticSkin(
                    cosmetic_id="cosmic_dragon_sword",
                    name="Dragon Sword Skin",
                    slot=EquipmentSlot.WEAPON.value,
                    rarity=CosmeticRarity.LEGENDARY.value,
                    description="A fearsome dragon-themed sword skin.",
                    mesh_path="mesh/sword_dragon",
                    texture_path="tex/sword_dragon",
                    dye_channels=3,
                    source="achievement",
                    collection="dragon_set",
                    seasonal=True,
                ),
                CosmeticSkin(
                    cosmetic_id="cosmic_cloak_mystery",
                    name="Mystery Cloak",
                    slot=EquipmentSlot.BACK.value,
                    rarity=CosmeticRarity.EPIC.value,
                    description="A cloak shrouded in mystery.",
                    mesh_path="mesh/cloak_mystery",
                    texture_path="tex/cloak_mystery",
                    dye_channels=1,
                    source="event",
                    collection="mystery_set",
                    seasonal=True,
                ),
            ]
            for c in cosmetics:
                self._cosmetics[c.cosmetic_id] = c

            outfit = OutfitPreset(
                outfit_id="outfit_knight_full",
                name="Full Knight Set",
                description="Complete knight armor with dragon sword.",
                cosmetics={
                    EquipmentSlot.HEAD.value: "cosmic_knight_helm",
                    EquipmentSlot.CHEST.value: "cosmic_knight_chest",
                    EquipmentSlot.WEAPON.value: "cosmic_dragon_sword",
                },
                dyes={
                    f"{EquipmentSlot.HEAD.value}_0": "dye_gold",
                    f"{EquipmentSlot.CHEST.value}_0": "dye_gold",
                },
                created_by="system",
            )
            self._outfits[outfit.outfit_id] = outfit

            profile = WardrobeProfile(
                profile_id="profile_starter_01",
                character_id="player_starter",
                name="Starter Profile",
                equipped_cosmetics={
                    EquipmentSlot.HEAD.value: "cosmic_knight_helm",
                },
                applied_dyes={
                    f"{EquipmentSlot.HEAD.value}_0": "dye_crimson",
                },
                unlocked_cosmetics=["cosmic_knight_helm", "cosmic_knight_chest", "cosmic_cloak_mystery"],
                active_outfit_id="",
            )
            self._profiles[profile.profile_id] = profile

            self._stats.total_dyes = len(dyes)
            self._stats.total_cosmetics = len(cosmetics)
            self._stats.total_outfits = 1
            self._stats.total_profiles = 1
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._stats.total_unlocked = sum(len(p.unlocked_cosmetics) for p in self._profiles.values())
            self._initialized = True

    # ------------------------------------------------------------------
    # Dye Catalog
    # ------------------------------------------------------------------

    def register_dye(self, dye: DyeDefinition) -> Dict[str, Any]:
        if not dye.dye_id:
            return {"success": False, "reason": "missing_dye_id"}
        with self._lock:
            if dye.dye_id in self._dyes:
                return {"success": False, "reason": "dye_id_exists"}
            if len(self._dyes) >= self._config.max_dyes:
                return {"success": False, "reason": "max_dyes_reached"}
            self._dyes[dye.dye_id] = dye
            self._stats.total_dyes = len(self._dyes)
            self._emit_event(WardrobeEventKind.DYE_REGISTERED.value, dye_id=dye.dye_id,
                             details={"name": dye.name})
            return {"dye_id": dye.dye_id, "registered": True}

    def remove_dye(self, dye_id: str) -> Dict[str, Any]:
        with self._lock:
            if dye_id not in self._dyes:
                return {"removed": False, "reason": "dye_not_found"}
            del self._dyes[dye_id]
            self._stats.total_dyes = len(self._dyes)
            self._emit_event(WardrobeEventKind.DYE_REMOVED.value, dye_id=dye_id)
            return {"dye_id": dye_id, "removed": True}

    def get_dye(self, dye_id: str) -> Optional[DyeDefinition]:
        return self._dyes.get(dye_id)

    def list_dyes(self, rarity: Optional[str] = None, limit: int = 100) -> List[DyeDefinition]:
        dyes = list(self._dyes.values())
        if rarity:
            dyes = [d for d in dyes if d.rarity == rarity]
        return dyes[:limit]

    # ------------------------------------------------------------------
    # Cosmetic Catalog
    # ------------------------------------------------------------------

    def register_cosmetic(self, cosmetic: CosmeticSkin) -> Dict[str, Any]:
        if not cosmetic.cosmetic_id:
            return {"success": False, "reason": "missing_cosmetic_id"}
        with self._lock:
            if cosmetic.cosmetic_id in self._cosmetics:
                return {"success": False, "reason": "cosmetic_id_exists"}
            if len(self._cosmetics) >= self._config.max_cosmetics:
                return {"success": False, "reason": "max_cosmetics_reached"}
            self._cosmetics[cosmetic.cosmetic_id] = cosmetic
            self._stats.total_cosmetics = len(self._cosmetics)
            self._emit_event(WardrobeEventKind.COSMETIC_REGISTERED.value, cosmetic_id=cosmetic.cosmetic_id,
                             details={"name": cosmetic.name, "slot": cosmetic.slot})
            return {"cosmetic_id": cosmetic.cosmetic_id, "registered": True}

    def remove_cosmetic(self, cosmetic_id: str) -> Dict[str, Any]:
        with self._lock:
            if cosmetic_id not in self._cosmetics:
                return {"removed": False, "reason": "cosmetic_not_found"}
            del self._cosmetics[cosmetic_id]
            self._stats.total_cosmetics = len(self._cosmetics)
            self._emit_event(WardrobeEventKind.COSMETIC_REMOVED.value, cosmetic_id=cosmetic_id)
            return {"cosmetic_id": cosmetic_id, "removed": True}

    def get_cosmetic(self, cosmetic_id: str) -> Optional[CosmeticSkin]:
        return self._cosmetics.get(cosmetic_id)

    def list_cosmetics(self, slot: Optional[str] = None, rarity: Optional[str] = None,
                      collection: Optional[str] = None, limit: int = 100) -> List[CosmeticSkin]:
        cosmetics = list(self._cosmetics.values())
        if slot:
            cosmetics = [c for c in cosmetics if c.slot == slot]
        if rarity:
            cosmetics = [c for c in cosmetics if c.rarity == rarity]
        if collection:
            cosmetics = [c for c in cosmetics if c.collection == collection]
        return cosmetics[:limit]

    # ------------------------------------------------------------------
    # Outfit Management
    # ------------------------------------------------------------------

    def register_outfit(self, outfit: OutfitPreset) -> Dict[str, Any]:
        if not outfit.outfit_id:
            return {"success": False, "reason": "missing_outfit_id"}
        with self._lock:
            if outfit.outfit_id in self._outfits:
                return {"success": False, "reason": "outfit_id_exists"}
            if len(self._outfits) >= self._config.max_outfits:
                return {"success": False, "reason": "max_outfits_reached"}
            self._outfits[outfit.outfit_id] = outfit
            self._stats.total_outfits = len(self._outfits)
            self._emit_event(WardrobeEventKind.OUTFIT_REGISTERED.value, outfit_id=outfit.outfit_id,
                             details={"name": outfit.name})
            return {"outfit_id": outfit.outfit_id, "registered": True}

    def remove_outfit(self, outfit_id: str) -> Dict[str, Any]:
        with self._lock:
            if outfit_id not in self._outfits:
                return {"removed": False, "reason": "outfit_not_found"}
            del self._outfits[outfit_id]
            self._stats.total_outfits = len(self._outfits)
            self._emit_event(WardrobeEventKind.OUTFIT_REMOVED.value, outfit_id=outfit_id)
            return {"outfit_id": outfit_id, "removed": True}

    def get_outfit(self, outfit_id: str) -> Optional[OutfitPreset]:
        return self._outfits.get(outfit_id)

    def list_outfits(self, limit: int = 100) -> List[OutfitPreset]:
        return list(self._outfits.values())[:limit]

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def register_profile(self, profile: WardrobeProfile) -> Dict[str, Any]:
        if not profile.profile_id:
            return {"success": False, "reason": "missing_profile_id"}
        with self._lock:
            if profile.profile_id in self._profiles:
                return {"success": False, "reason": "profile_id_exists"}
            if len(self._profiles) >= self._config.max_profiles:
                return {"success": False, "reason": "max_profiles_reached"}
            self._profiles[profile.profile_id] = profile
            self._stats.total_profiles = len(self._profiles)
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._stats.total_unlocked = sum(len(p.unlocked_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.PROFILE_REGISTERED.value, profile_id=profile.profile_id,
                             details={"character_id": profile.character_id})
            return {"profile_id": profile.profile_id, "registered": True}

    def remove_profile(self, profile_id: str) -> Dict[str, Any]:
        with self._lock:
            if profile_id not in self._profiles:
                return {"removed": False, "reason": "profile_not_found"}
            del self._profiles[profile_id]
            self._stats.total_profiles = len(self._profiles)
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._stats.total_unlocked = sum(len(p.unlocked_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.PROFILE_REMOVED.value, profile_id=profile_id)
            return {"profile_id": profile_id, "removed": True}

    def get_profile(self, profile_id: str) -> Optional[WardrobeProfile]:
        return self._profiles.get(profile_id)

    def list_profiles(self, character_id: Optional[str] = None, limit: int = 100) -> List[WardrobeProfile]:
        profiles = list(self._profiles.values())
        if character_id:
            profiles = [p for p in profiles if p.character_id == character_id]
        return profiles[:limit]

    # ------------------------------------------------------------------
    # Equip / Unequip / Dye / Unlock
    # ------------------------------------------------------------------

    def equip_cosmetic(self, profile_id: str, slot: str, cosmetic_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            cosmetic = self._cosmetics.get(cosmetic_id)
            if cosmetic is None:
                return {"success": False, "reason": "cosmetic_not_found"}
            if cosmetic.slot != slot:
                return {"success": False, "reason": "slot_mismatch"}
            if cosmetic_id not in profile.unlocked_cosmetics and not self._config.allow_free_cosmetics:
                return {"success": False, "reason": "cosmetic_locked"}
            profile.equipped_cosmetics[slot] = cosmetic_id
            profile.updated_at = _now()
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.COSMETIC_EQUIPPED.value, cosmetic_id=cosmetic_id,
                             profile_id=profile_id, details={"slot": slot})
            return {"profile_id": profile_id, "slot": slot, "cosmetic_id": cosmetic_id, "success": True}

    def unequip_cosmetic(self, profile_id: str, slot: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            if slot not in profile.equipped_cosmetics:
                return {"success": False, "reason": "slot_empty"}
            old_cosmetic = profile.equipped_cosmetics.pop(slot)
            dye_key = f"{slot}_0"
            if dye_key in profile.applied_dyes:
                del profile.applied_dyes[dye_key]
            profile.updated_at = _now()
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.COSMETIC_UNEQUIPPED.value, cosmetic_id=old_cosmetic,
                             profile_id=profile_id, details={"slot": slot})
            return {"profile_id": profile_id, "slot": slot, "cosmetic_id": old_cosmetic, "success": True}

    def apply_dye(self, profile_id: str, slot: str, channel: int, dye_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            dye = self._dyes.get(dye_id)
            if dye is None:
                return {"success": False, "reason": "dye_not_found"}
            if slot not in profile.equipped_cosmetics:
                return {"success": False, "reason": "no_cosmetic_equipped"}
            dye_key = f"{slot}_{channel}"
            profile.applied_dyes[dye_key] = dye_id
            profile.updated_at = _now()
            self._emit_event(WardrobeEventKind.DYE_APPLIED.value, dye_id=dye_id, profile_id=profile_id,
                             details={"slot": slot, "channel": channel})
            return {"profile_id": profile_id, "dye_key": dye_key, "dye_id": dye_id, "success": True}

    def remove_dye_from_slot(self, profile_id: str, slot: str, channel: int) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            dye_key = f"{slot}_{channel}"
            if dye_key not in profile.applied_dyes:
                return {"success": False, "reason": "no_dye_applied"}
            old_dye = profile.applied_dyes.pop(dye_key)
            profile.updated_at = _now()
            self._emit_event(WardrobeEventKind.DYE_REMOVED_FROM_SLOT.value, dye_id=old_dye,
                             profile_id=profile_id, details={"slot": slot, "channel": channel})
            return {"profile_id": profile_id, "dye_key": dye_key, "dye_id": old_dye, "success": True}

    def unlock_cosmetic(self, profile_id: str, cosmetic_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            cosmetic = self._cosmetics.get(cosmetic_id)
            if cosmetic is None:
                return {"success": False, "reason": "cosmetic_not_found"}
            if cosmetic_id in profile.unlocked_cosmetics:
                return {"success": False, "reason": "already_unlocked"}
            if len(profile.unlocked_cosmetics) >= self._config.max_unlocked_per_profile:
                return {"success": False, "reason": "max_unlocked_reached"}
            profile.unlocked_cosmetics.append(cosmetic_id)
            profile.updated_at = _now()
            self._stats.total_unlocked = sum(len(p.unlocked_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.COSMETIC_UNLOCKED.value, cosmetic_id=cosmetic_id,
                             profile_id=profile_id)
            return {"profile_id": profile_id, "cosmetic_id": cosmetic_id, "unlocked": True}

    def activate_outfit(self, profile_id: str, outfit_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return {"success": False, "reason": "profile_not_found"}
            outfit = self._outfits.get(outfit_id)
            if outfit is None:
                return {"success": False, "reason": "outfit_not_found"}
            profile.equipped_cosmetics.clear()
            profile.applied_dyes.clear()
            for slot, cosmetic_id in outfit.cosmetics.items():
                profile.equipped_cosmetics[slot] = cosmetic_id
            for dye_key, dye_id in outfit.dyes.items():
                profile.applied_dyes[dye_key] = dye_id
            profile.active_outfit_id = outfit_id
            profile.updated_at = _now()
            self._stats.total_equipped = sum(len(p.equipped_cosmetics) for p in self._profiles.values())
            self._emit_event(WardrobeEventKind.OUTFIT_ACTIVATED.value, outfit_id=outfit_id,
                             profile_id=profile_id)
            return {"profile_id": profile_id, "outfit_id": outfit_id, "cosmetics_applied": len(outfit.cosmetics), "success": True}

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        self._emit_event(WardrobeEventKind.TICK.value, details={"delta_time": delta_time})
        return {"tick": self._tick_count}

    def get_config(self) -> WardrobeConfig:
        return self._config

    def set_config(self, config: WardrobeConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(WardrobeEventKind.CONFIG_UPDATED.value)
            return {"updated": True}

    def _emit_event(self, kind: str, dye_id: Optional[str] = None,
                    cosmetic_id: Optional[str] = None,
                    outfit_id: Optional[str] = None,
                    profile_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = WardrobeEvent(
            event_id=f"we_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            dye_id=dye_id,
            cosmetic_id=cosmetic_id,
            outfit_id=outfit_id,
            profile_id=profile_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, profile_id: Optional[str] = None, cosmetic_id: Optional[str] = None,
                    limit: int = 100) -> List[WardrobeEvent]:
        events = self._events
        if profile_id:
            events = [e for e in events if e.profile_id == profile_id]
        if cosmetic_id:
            events = [e for e in events if e.cosmetic_id == cosmetic_id]
        return list(reversed(events[-limit:]))

    def get_stats(self) -> WardrobeStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_dyes": len(self._dyes),
            "total_cosmetics": len(self._cosmetics),
            "total_outfits": len(self._outfits),
            "total_profiles": len(self._profiles),
            "total_equipped": self._stats.total_equipped,
            "total_unlocked": self._stats.total_unlocked,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> WardrobeSnapshot:
        return WardrobeSnapshot(
            dyes=[d.to_dict() for d in self._dyes.values()],
            cosmetics=[c.to_dict() for c in self._cosmetics.values()],
            outfits=[o.to_dict() for o in self._outfits.values()],
            profiles=[p.to_dict() for p in self._profiles.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._dyes.clear()
            self._cosmetics.clear()
            self._outfits.clear()
            self._profiles.clear()
            self._events.clear()
            self._stats = WardrobeStats()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._emit_event(WardrobeEventKind.RESET.value)
            return {"reset": True, "status": self.get_status()}


def get_wardrobe_system() -> WardrobeSystem:
    return WardrobeSystem.get_instance()
