"""
SparkLabs Engine - Pet & Companion System

A comprehensive pet and companion management system for the SparkLabs
AI-native game engine. Manages companion creatures with species
definitions, individual pet instances, leveling and evolution, bonding
affinity, skill trees, mount riding capabilities, summon/dismiss state,
and cosmetic accessories.

Each pet species defines base stats, growth curves, learnable skills,
evolution paths, and mount eligibility. Individual pet instances track
level, experience, affinity, active skills, equipped accessories, and
summon state. Designed for RPG companion pets, combat familiars,
mountable creatures, and collection-based pet games.

Architecture:
  PetCompanionSystem (singleton)
    |-- PetSpecies, CompanionRole, PetEventKind, EvolutionTier
    |-- SpeciesSkill, PetSkillInstance, PetAccessory, PetInstance,
       BondingMilestone, PetConfig, PetStats, PetSnapshot, PetEvent
    |-- get_pet_companion_system

Core Capabilities:
  - register_species / remove_species / get_species / list_species: manage
    companion species definitions with stats, skills, and evolution paths.
  - register_pet / remove_pet / get_pet / list_pets: manage individual
    pet instances owned by players.
  - summon_pet / dismiss_pet: control pet active state in the world.
  - gain_experience / level_up: advance pet progression with XP and
    leveling.
  - evolve_pet: transform a pet to its next evolution tier.
  - increase_affinity / get_affinity: track and manage bonding milestones.
  - learn_skill / equip_skill / unequip_skill: manage pet skill loadouts.
  - equip_accessory / unequip_accessory: cosmetic and stat accessories.
  - set_mount / get_mount: configure mountable riding pets.
  - tick: advance simulation for passive affinity growth and cooldowns.
  - set_config / get_config: global tuning for max species, pets, and
    growth rates.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PetCompanionSystem.get_instance` or the module-level
:func:`get_pet_companion_system` factory.
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SPECIES: int = 500
_MAX_PETS: int = 5000
_MAX_SKILLS_PER_PET: int = 12
_MAX_ACCESSORIES_PER_PET: int = 6
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

class CompanionRole(str, Enum):
    """Combat role classification for a companion."""
    COMBAT = "combat"
    SUPPORT = "support"
    MOUNT = "mount"
    UTILITY = "utility"
    COSMETIC = "cosmetic"


class EvolutionTier(str, Enum):
    """Evolution stage of a pet species."""
    BASE = "base"
    JUVENILE = "juvenile"
    ADULT = "adult"
    PRIME = "prime"
    ASCENDED = "ascended"


class PetEventKind(str, Enum):
    """Audit event types emitted by the pet companion system."""
    SPECIES_REGISTERED = "species_registered"
    SPECIES_REMOVED = "species_removed"
    PET_REGISTERED = "pet_registered"
    PET_REMOVED = "pet_removed"
    PET_SUMMONED = "pet_summoned"
    PET_DISMISSED = "pet_dismissed"
    EXPERIENCE_GAINED = "experience_gained"
    PET_LEVELED_UP = "pet_leveled_up"
    PET_EVOLVED = "pet_evolved"
    AFFINITY_INCREASED = "affinity_increased"
    SKILL_LEARNED = "skill_learned"
    SKILL_EQUIPPED = "skill_equipped"
    SKILL_UNEQUIPPED = "skill_unequipped"
    ACCESSORY_EQUIPPED = "accessory_equipped"
    ACCESSORY_UNEQUIPPED = "accessory_unequipped"
    MOUNT_CONFIGURED = "mount_configured"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SpeciesSkill:
    """A learnable skill defined by a pet species."""
    skill_id: str
    name: str = ""
    description: str = ""
    unlock_level: int = 1
    skill_type: str = "active"
    cooldown: float = 5.0
    power: float = 10.0
    element: str = "neutral"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetSpecies:
    """A companion species definition with stats and skills."""
    species_id: str
    name: str = ""
    role: str = CompanionRole.COMBAT.value
    base_stats: Dict[str, float] = field(default_factory=dict)
    growth_rates: Dict[str, float] = field(default_factory=dict)
    learnable_skills: List[SpeciesSkill] = field(default_factory=list)
    evolution_path: List[str] = field(default_factory=list)
    mountable: bool = False
    mount_speed: float = 1.0
    rarity: str = "common"
    description: str = ""
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetSkillInstance:
    """An individual skill instance learned by a pet."""
    skill_id: str
    name: str = ""
    level: int = 1
    equipped: bool = False
    cooldown_remaining: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetAccessory:
    """A cosmetic or stat-granting accessory for pets."""
    accessory_id: str
    name: str = ""
    slot: str = "collar"
    stat_bonuses: Dict[str, float] = field(default_factory=dict)
    rarity: str = "common"
    icon: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetInstance:
    """An individual pet owned by a player."""
    pet_id: str
    species_id: str
    owner_id: str
    name: str = ""
    nickname: str = ""
    level: int = 1
    experience: int = 0
    evolution_tier: str = EvolutionTier.BASE.value
    affinity: float = 0.0
    summoned: bool = False
    current_stats: Dict[str, float] = field(default_factory=dict)
    learned_skills: List[PetSkillInstance] = field(default_factory=list)
    equipped_accessories: List[str] = field(default_factory=list)
    mount_enabled: bool = False
    hunger: float = 100.0
    mood: float = 100.0
    last_active_time: float = field(default_factory=_now)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BondingMilestone:
    """A bonding affinity milestone with rewards."""
    milestone_id: str
    affinity_threshold: float
    name: str = ""
    description: str = ""
    reward_type: str = "skill"
    reward_id: str = ""
    claimed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetConfig:
    """Global tuning parameters for the pet companion system."""
    max_species: int = 200
    max_pets: int = 2000
    max_skills_per_pet: int = 8
    max_accessories_per_pet: int = 4
    base_xp_per_level: int = 100
    xp_growth_multiplier: float = 1.5
    affinity_gain_per_tick: float = 0.1
    hunger_decay_per_tick: float = 0.5
    mood_decay_per_tick: float = 0.3
    max_affinity: float = 1000.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetStats:
    """Aggregate statistics for the pet companion system."""
    total_species: int = 0
    total_pets: int = 0
    summoned_pets: int = 0
    total_evolutions: int = 0
    total_skills_learned: int = 0
    total_mounts: int = 0
    avg_pet_level: float = 0.0
    avg_affinity: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetSnapshot:
    """Full state snapshot of the pet companion system."""
    species: List[Dict[str, Any]] = field(default_factory=list)
    pets: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetEvent:
    """An audit event emitted by the pet companion system."""
    event_id: str
    kind: str
    timestamp: float
    pet_id: Optional[str] = None
    species_id: Optional[str] = None
    owner_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Pet Companion System
# ---------------------------------------------------------------------------

class PetCompanionSystem:
    """Manages companion pets with species, leveling, evolution, and bonding."""

    _instance: Optional["PetCompanionSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._species: Dict[str, PetSpecies] = {}
        self._pets: Dict[str, PetInstance] = {}
        self._accessories: Dict[str, PetAccessory] = {}
        self._milestones: Dict[str, BondingMilestone] = {}
        self._events: List[PetEvent] = []
        self._stats = PetStats()
        self._config = PetConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "PetCompanionSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample species, pets, accessories, and milestones."""
        with self._init_lock:
            if self._initialized:
                return
            wolf_skills = [
                SpeciesSkill(skill_id="skl_howl", name="Howl", unlock_level=1,
                             skill_type="active", cooldown=8.0, power=15.0, element="neutral"),
                SpeciesSkill(skill_id="skl_bite", name="Savage Bite", unlock_level=3,
                             skill_type="active", cooldown=5.0, power=25.0, element="physical"),
                SpeciesSkill(skill_id="skl_pack_hunter", name="Pack Hunter", unlock_level=10,
                             skill_type="passive", cooldown=0.0, power=0.0, element="neutral"),
            ]
            wolf = PetSpecies(
                species_id="species_frost_wolf",
                name="Frost Wolf",
                role=CompanionRole.COMBAT.value,
                base_stats={"health": 200.0, "attack": 35.0, "defense": 20.0, "speed": 40.0},
                growth_rates={"health": 15.0, "attack": 3.0, "defense": 2.0, "speed": 2.5},
                learnable_skills=wolf_skills,
                evolution_path=[EvolutionTier.BASE.value, EvolutionTier.JUVENILE.value,
                                EvolutionTier.ADULT.value, EvolutionTier.PRIME.value],
                mountable=True,
                mount_speed=1.6,
                rarity="rare",
                description="A loyal frost wolf companion.",
                icon="frost_wolf_icon",
            )
            self._species[wolf.species_id] = wolf

            falcon_skills = [
                SpeciesSkill(skill_id="skl_dive", name="Dive Bomb", unlock_level=1,
                             skill_type="active", cooldown=6.0, power=20.0, element="wind"),
                SpeciesSkill(skill_id="skl_scout", name="Scout", unlock_level=5,
                             skill_type="utility", cooldown=15.0, power=0.0, element="neutral"),
            ]
            falcon = PetSpecies(
                species_id="species_sky_falcon",
                name="Sky Falcon",
                role=CompanionRole.SUPPORT.value,
                base_stats={"health": 120.0, "attack": 25.0, "defense": 10.0, "speed": 60.0},
                growth_rates={"health": 8.0, "attack": 2.0, "defense": 1.0, "speed": 4.0},
                learnable_skills=falcon_skills,
                evolution_path=[EvolutionTier.BASE.value, EvolutionTier.JUVENILE.value,
                                EvolutionTier.ADULT.value],
                mountable=False,
                rarity="uncommon",
                description="A swift aerial scout companion.",
                icon="sky_falcon_icon",
            )
            self._species[falcon.species_id] = falcon

            turtle = PetSpecies(
                species_id="species_iron_turtle",
                name="Iron Turtle",
                role=CompanionRole.MOUNT.value,
                base_stats={"health": 500.0, "attack": 15.0, "defense": 80.0, "speed": 10.0},
                growth_rates={"health": 30.0, "attack": 1.0, "defense": 5.0, "speed": 0.5},
                learnable_skills=[],
                evolution_path=[EvolutionTier.BASE.value, EvolutionTier.ADULT.value],
                mountable=True,
                mount_speed=0.8,
                rarity="common",
                description="A sturdy, slow-moving mount.",
                icon="iron_turtle_icon",
            )
            self._species[turtle.species_id] = turtle

            pet1 = PetInstance(
                pet_id="pet_starter_wolf",
                species_id="species_frost_wolf",
                owner_id="player_starter",
                name="Shadow",
                nickname="Shadow",
                level=5,
                experience=150,
                affinity=50.0,
                summoned=True,
                current_stats={"health": 275.0, "attack": 50.0, "defense": 30.0, "speed": 52.5},
                learned_skills=[
                    PetSkillInstance(skill_id="skl_howl", name="Howl", level=1, equipped=True),
                    PetSkillInstance(skill_id="skl_bite", name="Savage Bite", level=1, equipped=True),
                ],
                equipped_accessories=["acc_iron_collar"],
                mount_enabled=False,
                hunger=80.0,
                mood=90.0,
            )
            self._pets[pet1.pet_id] = pet1

            pet2 = PetInstance(
                pet_id="pet_starter_falcon",
                species_id="species_sky_falcon",
                owner_id="player_starter",
                name="Whirlwind",
                level=3,
                experience=60,
                affinity=20.0,
                summoned=False,
                current_stats={"health": 144.0, "attack": 31.0, "defense": 13.0, "speed": 72.0},
                learned_skills=[
                    PetSkillInstance(skill_id="skl_dive", name="Dive Bomb", level=1, equipped=True),
                ],
            )
            self._pets[pet2.pet_id] = pet2

            collar = PetAccessory(
                accessory_id="acc_iron_collar",
                name="Iron Collar",
                slot="collar",
                stat_bonuses={"defense": 5.0, "health": 20.0},
                rarity="common",
                icon="iron_collar_icon",
                description="A sturdy iron collar.",
            )
            self._accessories[collar.accessory_id] = collar

            self._milestones["ms_bond_1"] = BondingMilestone(
                milestone_id="ms_bond_1",
                affinity_threshold=100.0,
                name="Trusted Partner",
                description="Your pet trusts you deeply.",
                reward_type="skill",
                reward_id="skl_pack_hunter",
            )
            self._milestones["ms_bond_2"] = BondingMilestone(
                milestone_id="ms_bond_2",
                affinity_threshold=300.0,
                name="Soulbound",
                description="An unbreakable bond.",
                reward_type="stat",
                reward_id="all_stats_boost",
            )

            self._stats.total_species = len(self._species)
            self._stats.total_pets = len(self._pets)
            self._stats.summoned_pets = sum(1 for p in self._pets.values() if p.summoned)
            self._stats.total_skills_learned = sum(len(p.learned_skills) for p in self._pets.values())
            self._stats.avg_pet_level = sum(p.level for p in self._pets.values()) / max(1, len(self._pets))
            self._stats.avg_affinity = sum(p.affinity for p in self._pets.values()) / max(1, len(self._pets))
            self._initialized = True

    # ------------------------------------------------------------------
    # Species Management
    # ------------------------------------------------------------------

    def register_species(self, species: PetSpecies) -> Dict[str, Any]:
        with self._lock:
            if len(self._species) >= _MAX_SPECIES:
                return {"registered": False, "reason": "capacity_reached"}
            if species.species_id in self._species:
                return {"registered": False, "reason": "species_exists"}
            self._species[species.species_id] = species
            self._stats.total_species = len(self._species)
            self._emit_event(PetEventKind.SPECIES_REGISTERED.value, species_id=species.species_id)
            return {"registered": True, "species_id": species.species_id}

    def remove_species(self, species_id: str) -> Dict[str, Any]:
        with self._lock:
            if species_id not in self._species:
                return {"removed": False, "reason": "species_not_found"}
            del self._species[species_id]
            self._stats.total_species = len(self._species)
            self._emit_event(PetEventKind.SPECIES_REMOVED.value, species_id=species_id)
            return {"removed": True, "species_id": species_id}

    def get_species(self, species_id: str) -> Optional[PetSpecies]:
        with self._lock:
            return self._species.get(species_id)

    def list_species(self, role: Optional[str] = None, rarity: Optional[str] = None,
                     limit: int = 100) -> List[PetSpecies]:
        with self._lock:
            result = []
            for s in self._species.values():
                if role and s.role != role:
                    continue
                if rarity and s.rarity != rarity:
                    continue
                result.append(s)
            return result[:limit]

    # ------------------------------------------------------------------
    # Pet Instance Management
    # ------------------------------------------------------------------

    def register_pet(self, pet: PetInstance) -> Dict[str, Any]:
        with self._lock:
            if len(self._pets) >= _MAX_PETS:
                return {"registered": False, "reason": "capacity_reached"}
            if pet.pet_id in self._pets:
                return {"registered": False, "reason": "pet_exists"}
            if pet.species_id not in self._species:
                return {"registered": False, "reason": "species_not_found"}
            species = self._species[pet.species_id]
            if not pet.current_stats:
                pet.current_stats = dict(species.base_stats)
            self._pets[pet.pet_id] = pet
            self._stats.total_pets = len(self._pets)
            if pet.summoned:
                self._stats.summoned_pets += 1
            self._stats.total_skills_learned += len(pet.learned_skills)
            self._stats.avg_pet_level = sum(p.level for p in self._pets.values()) / max(1, len(self._pets))
            self._emit_event(PetEventKind.PET_REGISTERED.value, pet_id=pet.pet_id,
                             species_id=pet.species_id, owner_id=pet.owner_id)
            return {"registered": True, "pet_id": pet.pet_id}

    def remove_pet(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"removed": False, "reason": "pet_not_found"}
            if pet.summoned:
                self._stats.summoned_pets = max(0, self._stats.summoned_pets - 1)
            del self._pets[pet_id]
            self._stats.total_pets = len(self._pets)
            self._stats.summoned_pets = sum(1 for p in self._pets.values() if p.summoned)
            self._emit_event(PetEventKind.PET_REMOVED.value, pet_id=pet_id)
            return {"removed": True, "pet_id": pet_id}

    def get_pet(self, pet_id: str) -> Optional[PetInstance]:
        with self._lock:
            return self._pets.get(pet_id)

    def list_pets(self, owner_id: Optional[str] = None, species_id: Optional[str] = None,
                  summoned: Optional[bool] = None, limit: int = 100) -> List[PetInstance]:
        with self._lock:
            result = []
            for p in self._pets.values():
                if owner_id and p.owner_id != owner_id:
                    continue
                if species_id and p.species_id != species_id:
                    continue
                if summoned is not None and p.summoned != summoned:
                    continue
                result.append(p)
            return result[:limit]

    # ------------------------------------------------------------------
    # Summon / Dismiss
    # ------------------------------------------------------------------

    def summon_pet(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            if pet.summoned:
                return {"success": False, "reason": "already_summoned"}
            if pet.hunger <= 0:
                return {"success": False, "reason": "pet_hungry"}
            pet.summoned = True
            pet.last_active_time = _now()
            pet.updated_at = _now()
            self._stats.summoned_pets += 1
            self._emit_event(PetEventKind.PET_SUMMONED.value, pet_id=pet_id, owner_id=pet.owner_id)
            return {"success": True, "pet_id": pet_id, "summoned": True}

    def dismiss_pet(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            if not pet.summoned:
                return {"success": False, "reason": "not_summoned"}
            pet.summoned = False
            pet.updated_at = _now()
            self._stats.summoned_pets = max(0, self._stats.summoned_pets - 1)
            self._emit_event(PetEventKind.PET_DISMISSED.value, pet_id=pet_id)
            return {"success": True, "pet_id": pet_id, "summoned": False}

    # ------------------------------------------------------------------
    # Experience & Leveling
    # ------------------------------------------------------------------

    def gain_experience(self, pet_id: str, amount: int) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            pet.experience += max(0, amount)
            leveled_up = False
            levels_gained = 0
            while True:
                needed = int(self._config.base_xp_per_level * (self._config.xp_growth_multiplier ** (pet.level - 1)))
                if pet.experience >= needed and pet.level < 999:
                    pet.experience -= needed
                    pet.level += 1
                    levels_gained += 1
                    leveled_up = True
                    self._apply_growth(pet)
                else:
                    break
            pet.updated_at = _now()
            self._emit_event(PetEventKind.EXPERIENCE_GAINED.value, pet_id=pet_id,
                             details={"amount": amount, "leveled_up": leveled_up})
            if leveled_up:
                self._emit_event(PetEventKind.PET_LEVELED_UP.value, pet_id=pet_id,
                                 details={"new_level": pet.level, "levels_gained": levels_gained})
            self._stats.avg_pet_level = sum(p.level for p in self._pets.values()) / max(1, len(self._pets))
            return {"success": True, "pet_id": pet_id, "new_xp": pet.experience,
                    "level": pet.level, "leveled_up": leveled_up, "levels_gained": levels_gained}

    def _apply_growth(self, pet: PetInstance) -> None:
        species = self._species.get(pet.species_id)
        if species is None:
            return
        for stat, growth in species.growth_rates.items():
            pet.current_stats[stat] = pet.current_stats.get(stat, 0.0) + growth

    def level_up(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            pet.level += 1
            self._apply_growth(pet)
            pet.updated_at = _now()
            self._emit_event(PetEventKind.PET_LEVELED_UP.value, pet_id=pet_id,
                             details={"new_level": pet.level})
            self._stats.avg_pet_level = sum(p.level for p in self._pets.values()) / max(1, len(self._pets))
            return {"success": True, "pet_id": pet_id, "new_level": pet.level}

    # ------------------------------------------------------------------
    # Evolution
    # ------------------------------------------------------------------

    def evolve_pet(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            species = self._species.get(pet.species_id)
            if species is None:
                return {"success": False, "reason": "species_not_found"}
            path = species.evolution_path
            try:
                current_idx = path.index(pet.evolution_tier)
            except ValueError:
                return {"success": False, "reason": "invalid_tier"}
            if current_idx >= len(path) - 1:
                return {"success": False, "reason": "max_evolution"}
            new_tier = path[current_idx + 1]
            pet.evolution_tier = new_tier
            for stat in pet.current_stats:
                pet.current_stats[stat] *= 1.2
            pet.updated_at = _now()
            self._stats.total_evolutions += 1
            self._emit_event(PetEventKind.PET_EVOLVED.value, pet_id=pet_id,
                             details={"new_tier": new_tier})
            return {"success": True, "pet_id": pet_id, "new_tier": new_tier}

    # ------------------------------------------------------------------
    # Affinity & Bonding
    # ------------------------------------------------------------------

    def increase_affinity(self, pet_id: str, amount: float) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            pet.affinity = _clamp(pet.affinity + amount, 0.0, self._config.max_affinity)
            pet.updated_at = _now()
            milestones_reached = []
            for ms in self._milestones.values():
                if not ms.claimed and pet.affinity >= ms.affinity_threshold:
                    ms.claimed = True
                    milestones_reached.append(ms.milestone_id)
            self._emit_event(PetEventKind.AFFINITY_INCREASED.value, pet_id=pet_id,
                             details={"amount": amount, "new_affinity": pet.affinity,
                                      "milestones": milestones_reached})
            self._stats.avg_affinity = sum(p.affinity for p in self._pets.values()) / max(1, len(self._pets))
            return {"success": True, "pet_id": pet_id, "new_affinity": pet.affinity,
                    "milestones_reached": milestones_reached}

    def get_affinity(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"found": False, "reason": "pet_not_found"}
            return {"found": True, "pet_id": pet_id, "affinity": pet.affinity,
                    "max_affinity": self._config.max_affinity}

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    def learn_skill(self, pet_id: str, skill_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            species = self._species.get(pet.species_id)
            if species is None:
                return {"success": False, "reason": "species_not_found"}
            skill_def = None
            for s in species.learnable_skills:
                if s.skill_id == skill_id:
                    skill_def = s
                    break
            if skill_def is None:
                return {"success": False, "reason": "skill_not_learnable"}
            if pet.level < skill_def.unlock_level:
                return {"success": False, "reason": "level_too_low"}
            for existing in pet.learned_skills:
                if existing.skill_id == skill_id:
                    return {"success": False, "reason": "already_learned"}
            if len(pet.learned_skills) >= self._config.max_skills_per_pet:
                return {"success": False, "reason": "skill_capacity"}
            instance = PetSkillInstance(skill_id=skill_id, name=skill_def.name, level=1, equipped=False)
            pet.learned_skills.append(instance)
            pet.updated_at = _now()
            self._stats.total_skills_learned += 1
            self._emit_event(PetEventKind.SKILL_LEARNED.value, pet_id=pet_id,
                             details={"skill_id": skill_id})
            return {"success": True, "pet_id": pet_id, "skill_id": skill_id}

    def equip_skill(self, pet_id: str, skill_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            for s in pet.learned_skills:
                if s.skill_id == skill_id:
                    s.equipped = True
                    pet.updated_at = _now()
                    self._emit_event(PetEventKind.SKILL_EQUIPPED.value, pet_id=pet_id,
                                     details={"skill_id": skill_id})
                    return {"success": True, "pet_id": pet_id, "skill_id": skill_id}
            return {"success": False, "reason": "skill_not_learned"}

    def unequip_skill(self, pet_id: str, skill_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            for s in pet.learned_skills:
                if s.skill_id == skill_id:
                    s.equipped = False
                    pet.updated_at = _now()
                    self._emit_event(PetEventKind.SKILL_UNEQUIPPED.value, pet_id=pet_id,
                                     details={"skill_id": skill_id})
                    return {"success": True, "pet_id": pet_id, "skill_id": skill_id}
            return {"success": False, "reason": "skill_not_learned"}

    # ------------------------------------------------------------------
    # Accessories
    # ------------------------------------------------------------------

    def register_accessory(self, accessory: PetAccessory) -> Dict[str, Any]:
        with self._lock:
            self._accessories[accessory.accessory_id] = accessory
            return {"registered": True, "accessory_id": accessory.accessory_id}

    def get_accessory(self, accessory_id: str) -> Optional[PetAccessory]:
        with self._lock:
            return self._accessories.get(accessory_id)

    def list_accessories(self, slot: Optional[str] = None, limit: int = 100) -> List[PetAccessory]:
        with self._lock:
            result = []
            for a in self._accessories.values():
                if slot and a.slot != slot:
                    continue
                result.append(a)
            return result[:limit]

    def equip_accessory(self, pet_id: str, accessory_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            acc = self._accessories.get(accessory_id)
            if acc is None:
                return {"success": False, "reason": "accessory_not_found"}
            if accessory_id in pet.equipped_accessories:
                return {"success": False, "reason": "already_equipped"}
            if len(pet.equipped_accessories) >= self._config.max_accessories_per_pet:
                return {"success": False, "reason": "accessory_capacity"}
            pet.equipped_accessories.append(accessory_id)
            for stat, bonus in acc.stat_bonuses.items():
                pet.current_stats[stat] = pet.current_stats.get(stat, 0.0) + bonus
            pet.updated_at = _now()
            self._emit_event(PetEventKind.ACCESSORY_EQUIPPED.value, pet_id=pet_id,
                             details={"accessory_id": accessory_id})
            return {"success": True, "pet_id": pet_id, "accessory_id": accessory_id}

    def unequip_accessory(self, pet_id: str, accessory_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            if accessory_id not in pet.equipped_accessories:
                return {"success": False, "reason": "not_equipped"}
            pet.equipped_accessories.remove(accessory_id)
            acc = self._accessories.get(accessory_id)
            if acc:
                for stat, bonus in acc.stat_bonuses.items():
                    pet.current_stats[stat] = pet.current_stats.get(stat, 0.0) - bonus
            pet.updated_at = _now()
            self._emit_event(PetEventKind.ACCESSORY_UNEQUIPPED.value, pet_id=pet_id,
                             details={"accessory_id": accessory_id})
            return {"success": True, "pet_id": pet_id, "accessory_id": accessory_id}

    # ------------------------------------------------------------------
    # Mount Configuration
    # ------------------------------------------------------------------

    def set_mount(self, pet_id: str, enabled: bool) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"success": False, "reason": "pet_not_found"}
            species = self._species.get(pet.species_id)
            if species is None:
                return {"success": False, "reason": "species_not_found"}
            if enabled and not species.mountable:
                return {"success": False, "reason": "not_mountable"}
            pet.mount_enabled = enabled
            pet.updated_at = _now()
            if enabled:
                self._stats.total_mounts += 1
            else:
                self._stats.total_mounts = max(0, self._stats.total_mounts - 1)
            self._emit_event(PetEventKind.MOUNT_CONFIGURED.value, pet_id=pet_id,
                             details={"enabled": enabled, "mount_speed": species.mount_speed})
            return {"success": True, "pet_id": pet_id, "mount_enabled": enabled,
                    "mount_speed": species.mount_speed}

    def get_mount(self, pet_id: str) -> Dict[str, Any]:
        with self._lock:
            pet = self._pets.get(pet_id)
            if pet is None:
                return {"found": False, "reason": "pet_not_found"}
            species = self._species.get(pet.species_id)
            mount_speed = species.mount_speed if species else 0.0
            return {"found": True, "pet_id": pet_id, "mount_enabled": pet.mount_enabled,
                    "mount_speed": mount_speed, "mountable": species.mountable if species else False}

    # ------------------------------------------------------------------
    # Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            ticks = max(1, int(delta_time * self._config.tick_rate_hz))
            for pet in self._pets.values():
                if pet.summoned:
                    pet.affinity = _clamp(pet.affinity + self._config.affinity_gain_per_tick * ticks,
                                          0.0, self._config.max_affinity)
                    pet.hunger = _clamp(pet.hunger - self._config.hunger_decay_per_tick * ticks, 0.0, 100.0)
                    pet.mood = _clamp(pet.mood - self._config.mood_decay_per_tick * ticks, 0.0, 100.0)
                    pet.last_active_time = _now()
                for s in pet.learned_skills:
                    if s.cooldown_remaining > 0:
                        s.cooldown_remaining = max(0.0, s.cooldown_remaining - delta_time)
            self._stats.tick_count = self._tick_count
            self._stats.avg_affinity = sum(p.affinity for p in self._pets.values()) / max(1, len(self._pets))
            self._emit_event(PetEventKind.TICK.value, details={"delta_time": delta_time})
            return {"tick_count": self._tick_count, "delta_time": delta_time}

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def get_config(self) -> PetConfig:
        with self._lock:
            return self._config

    def set_config(self, config: PetConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(PetEventKind.CONFIG_UPDATED.value)
            return {"success": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, pet_id: Optional[str] = None,
                    species_id: Optional[str] = None, owner_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        self._event_counter += 1
        event = PetEvent(
            event_id=f"pe_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            pet_id=pet_id,
            species_id=species_id,
            owner_id=owner_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, pet_id: Optional[str] = None, species_id: Optional[str] = None,
                    limit: int = 100) -> List[PetEvent]:
        with self._lock:
            result = []
            for e in self._events:
                if pet_id and e.pet_id != pet_id:
                    continue
                if species_id and e.species_id != species_id:
                    continue
                result.append(e)
            return result[:limit]

    def get_stats(self) -> PetStats:
        with self._lock:
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_species": len(self._species),
                "total_pets": len(self._pets),
                "summoned_pets": sum(1 for p in self._pets.values() if p.summoned),
                "total_accessories": len(self._accessories),
                "total_milestones": len(self._milestones),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> PetSnapshot:
        with self._lock:
            return PetSnapshot(
                species=[s.to_dict() for s in self._species.values()],
                pets=[p.to_dict() for p in self._pets.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._species.clear()
            self._pets.clear()
            self._accessories.clear()
            self._milestones.clear()
            self._events.clear()
            self._stats = PetStats()
            self._config = PetConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._emit_event(PetEventKind.RESET.value)
            self._seed()
            return {"success": True, "reset": True}


def get_pet_companion_system() -> PetCompanionSystem:
    """Factory function for the PetCompanionSystem singleton."""
    return PetCompanionSystem.get_instance()
