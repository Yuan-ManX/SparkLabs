"""
SparkLabs Engine - Pet & Companion System

Manages collectible pets and combat companions that follow players, assist
in battle, level up, learn abilities, wear equipment, and build loyalty.
Players tame wild creatures, hatch eggs, train pets, and deploy them as
active companions during gameplay.

Architecture:
  PetCompanionSystem (singleton)
    |-- PetSpecies, PetRole, PetMood, PetStatus, AcquireMethod, PetEventKind
    |-- PetAbility, PetSpeciesDefinition, PlayerPet, PetEquipmentSlot,
       PetTrainingSession, PetBondRecord, PetConfig, PetStats, PetSnapshot,
       PetEvent
    |-- get_pet_companion_system

Core Capabilities:
  - register_species / remove_species / get_species / list_species
  - register_ability / get_ability / list_abilities
  - acquire_pet / release_pet / get_pet / list_player_pets
  - summon_companion / dismiss_companion / get_active_companion
  - feed_pet / pet_mood_update / get_mood
  - train_pet / get_training_history
  - teach_ability / forget_ability / get_pet_abilities
  - equip_pet_item / unequip_pet_item
  - level_up_pet / gain_pet_xp / evolve_pet
  - calculate_combat_power / get_bond_level
  - record_bond_interaction / get_bond_history
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PetCompanionSystem.get_instance` or the module-level
:func:`get_pet_companion_system` factory.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SPECIES: int = 1000
_MAX_ABILITIES: int = 2000
_MAX_PLAYER_PETS: int = 200000
_MAX_TRAINING_RECORDS: int = 200000
_MAX_BOND_RECORDS: int = 500000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


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


def _dataclass_to_dict(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "__dataclass_fields__"):
                result[k] = _dataclass_to_dict(v)
            elif hasattr(v, "to_dict") and callable(v.to_dict):
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

class PetSpecies(str, Enum):
    """Taxonomic family of a pet creature."""
    BEAST = "beast"
    DRAGONKIN = "dragonkin"
    ELEMENTAL = "elemental"
    MECHANICAL = "mechanical"
    UNDEAD = "undead"
    HUMANOID = "humanoid"
    MAGIC = "magic"
    FLYING = "flying"
    AQUATIC = "aquatic"
    CRITTER = "critter"


class PetRole(str, Enum):
    """Combat role a pet fills when summoned."""
    TANK = "tank"
    DPS = "dps"
    SUPPORT = "support"
    UTILITY = "utility"
    BALANCED = "balanced"


class PetMood(str, Enum):
    """Emotional state of a pet."""
    ECSTATIC = "ecstatic"
    HAPPY = "happy"
    CONTENT = "content"
    NEUTRAL = "neutral"
    UNHAPPY = "unhappy"
    MISERABLE = "miserable"


class PetStatus(str, Enum):
    """Deployment status of a player pet."""
    STORED = "stored"
    SUMMONED = "summoned"
    RESTING = "resting"
    TRAINING = "training"
    INCUBATING = "incubating"


class AcquireMethod(str, Enum):
    """How a pet species can be obtained."""
    TAME = "tame"
    HATCH = "hatch"
    QUEST = "quest"
    PURCHASE = "purchase"
    DROP = "drop"
    EVENT = "event"
    CRAFT = "craft"


class PetEventKind(str, Enum):
    """Audit event types emitted by the pet companion system."""
    SPECIES_REGISTERED = "species_registered"
    SPECIES_REMOVED = "species_removed"
    ABILITY_REGISTERED = "ability_registered"
    PET_ACQUIRED = "pet_acquired"
    PET_RELEASED = "pet_released"
    PET_SUMMONED = "pet_summoned"
    PET_DISMISSED = "pet_dismissed"
    PET_FED = "pet_fed"
    PET_TRAINED = "pet_trained"
    ABILITY_TAUGHT = "ability_taught"
    ABILITY_FORGOTTEN = "ability_forgotten"
    EQUIPMENT_EQUIPPED = "equipment_equipped"
    EQUIPMENT_UNEQUIPPED = "equipment_unequipped"
    PET_LEVEL_UP = "pet_level_up"
    PET_EVOLVED = "pet_evolved"
    BOND_INTERACTION = "bond_interaction"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PetAbility:
    """A learnable ability that pets can use in combat."""
    ability_id: str
    name: str
    description: str = ""
    species_restriction: str = ""
    cooldown: float = 5.0
    damage_multiplier: float = 1.0
    healing_multiplier: float = 0.0
    duration: float = 0.0
    required_pet_level: int = 1
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetSpeciesDefinition:
    """Definition of a tameable creature species."""
    species_id: str
    name: str
    description: str = ""
    family: str = PetSpecies.BEAST.value
    role: str = PetRole.BALANCED.value
    rarity: str = "common"
    base_health: float = 100.0
    base_attack: float = 20.0
    base_defense: float = 15.0
    base_speed: float = 10.0
    growth_health: float = 10.0
    growth_attack: float = 2.0
    growth_defense: float = 1.5
    growth_speed: float = 1.0
    max_level: int = 60
    acquire_method: str = AcquireMethod.TAME.value
    acquire_cost: float = 0.0
    acquire_currency: str = "gold"
    evolve_target_id: str = ""
    evolve_required_level: int = 0
    diet: str = "omnivore"
    favorite_food: str = ""
    icon: str = ""
    model_id: str = ""
    color: str = "#FFFFFF"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetEquipmentSlot:
    """Equipment attached to a pet."""
    slot: str
    item_id: str = ""
    item_name: str = ""
    stat_bonuses: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerPet:
    """A pet owned by a player."""
    pet_id: str
    player_id: str
    species_id: str
    name: str = ""
    status: str = PetStatus.STORED.value
    level: int = 1
    experience: int = 0
    current_health: float = 100.0
    max_health: float = 100.0
    attack: float = 20.0
    defense: float = 15.0
    speed: float = 10.0
    mood: str = PetMood.CONTENT.value
    mood_value: float = 50.0
    loyalty: float = 50.0
    bond_level: int = 1
    bond_xp: int = 0
    learned_abilities: List[str] = field(default_factory=list)
    equipped_slots: Dict[str, PetEquipmentSlot] = field(default_factory=dict)
    custom_name: str = ""
    acquired_at: float = field(default_factory=_now)
    last_fed: float = 0.0
    last_summoned: float = 0.0
    summon_count: int = 0
    total_battles: int = 0
    total_victories: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def combat_power(self) -> float:
        base = self.attack * 2.0 + self.defense * 1.5 + self.speed + self.max_health * 0.1
        eq_bonus = 0.0
        for eq in self.equipped_slots.values():
            eq_bonus += eq.stat_bonuses.get("attack", 0.0) * 2.0
            eq_bonus += eq.stat_bonuses.get("defense", 0.0) * 1.5
            eq_bonus += eq.stat_bonuses.get("health", 0.0) * 0.1
        mood_mult = 1.0
        if self.mood == PetMood.ECSTATIC.value:
            mood_mult = 1.2
        elif self.mood == PetMood.HAPPY.value:
            mood_mult = 1.1
        elif self.mood == PetMood.UNHAPPY.value:
            mood_mult = 0.9
        elif self.mood == PetMood.MISERABLE.value:
            mood_mult = 0.75
        return round((base + eq_bonus) * mood_mult, 1)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["combat_power"] = self.combat_power
        return d


@dataclass
class PetTrainingSession:
    """Record of a training session for a pet."""
    session_id: str
    pet_id: str
    player_id: str
    training_type: str = "attack"
    xp_gained: int = 50
    stat_before: float = 0.0
    stat_after: float = 0.0
    cost: float = 25.0
    currency: str = "gold"
    trained_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetBondRecord:
    """A bond interaction between player and pet."""
    bond_id: str
    pet_id: str
    player_id: str
    interaction: str = "pet"
    bond_xp_gained: int = 5
    mood_change: float = 2.0
    interacted_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetConfig:
    """Global tuning parameters."""
    max_species: int = 1000
    max_abilities: int = 2000
    max_player_pets: int = 200000
    max_pets_per_player: int = 200
    max_equipped_slots: int = 4
    max_active_companions: int = 1
    base_feed_mood_gain: float = 10.0
    mood_decay_per_hour: float = 5.0
    loyalty_gain_per_battle: float = 0.5
    loyalty_max: float = 100.0
    bond_xp_per_interaction: int = 5
    bond_xp_per_level: int = 100
    xp_per_level: int = 500
    max_pet_level: int = 60
    summon_cooldown: float = 3.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetStats:
    """Aggregate statistics."""
    total_species: int = 0
    total_abilities: int = 0
    total_player_pets: int = 0
    total_summoned: int = 0
    total_training_sessions: int = 0
    total_bond_records: int = 0
    total_battles: int = 0
    total_victories: int = 0
    total_evolved: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetSnapshot:
    """Full state snapshot."""
    species: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PetEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    species_id: str = ""
    pet_id: str = ""
    player_id: str = ""
    ability_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Pet & Companion System
# ---------------------------------------------------------------------------

class PetCompanionSystem:
    """Manages pet species, player pets, summoning, training, and bonding."""

    _instance: Optional["PetCompanionSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._species: Dict[str, PetSpeciesDefinition] = {}
        self._abilities: Dict[str, PetAbility] = {}
        self._pets: Dict[str, PlayerPet] = {}
        self._training: Dict[str, PetTrainingSession] = {}
        self._bonds: Dict[str, PetBondRecord] = {}
        self._active_companions: Dict[str, str] = {}
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
        with self._init_lock:
            if self._initialized:
                return

            species_data = [
                ("pet_wolf", "Timber Wolf", "A loyal forest wolf that hunts in packs.",
                 PetSpecies.BEAST.value, PetRole.DPS.value, "common",
                 120.0, 25.0, 12.0, 15.0, 12.0, 2.5, 1.2, 1.5,
                 AcquireMethod.TAME.value, 0.0, "gold", "", 0, "carnivore", "raw_meat",
                 "icon_wolf", "model_wolf", "#808080"),
                ("pet_turtle", "Ancient Turtle", "A wise turtle with an impenetrable shell.",
                 PetSpecies.BEAST.value, PetRole.TANK.value, "common",
                 200.0, 12.0, 30.0, 5.0, 20.0, 1.2, 3.0, 0.5,
                 AcquireMethod.TAME.value, 0.0, "gold", "", 0, "herbivore", "seaweed",
                 "icon_turtle", "model_turtle", "#228B22"),
                ("pet_fairy", "Luminous Fairy", "A tiny fairy that heals its allies.",
                 PetSpecies.MAGIC.value, PetRole.SUPPORT.value, "uncommon",
                 80.0, 10.0, 8.0, 20.0, 8.0, 1.0, 0.8, 2.0,
                 AcquireMethod.QUEST.value, 0.0, "gold", "", 0, "omnivore", "nectar",
                 "icon_fairy", "model_fairy", "#FFD700"),
                ("pet_whelp", "Crimson Whelp", "A young dragon with fiery breath.",
                 PetSpecies.DRAGONKIN.value, PetRole.DPS.value, "rare",
                 150.0, 30.0, 15.0, 12.0, 15.0, 3.0, 1.5, 1.2,
                 AcquireMethod.HATCH.value, 500.0, "gold", "pet_drake", 30, "carnivore", "raw_meat",
                 "icon_whelp", "model_whelp", "#DC143C"),
                ("pet_golem", "Stone Golem", "A construct of animated stone.",
                 PetSpecies.ELEMENTAL.value, PetRole.TANK.value, "rare",
                 250.0, 18.0, 35.0, 3.0, 25.0, 2.5, 3.5, 0.3,
                 AcquireMethod.CRAFT.value, 1000.0, "gold", "", 0, "none", "",
                 "icon_golem", "model_golem", "#A0522D"),
            ]

            for (sid, name, desc, family, role, rarity,
                 bhp, batk, bdef, bspd, ghp, gatk, gdef, gspd,
                 acq, cost, cur, evolve, evo_lvl, diet, food,
                 icon, model, color) in species_data:
                spec = PetSpeciesDefinition(
                    species_id=sid, name=name, description=desc,
                    family=family, role=role, rarity=rarity,
                    base_health=bhp, base_attack=batk, base_defense=bdef, base_speed=bspd,
                    growth_health=ghp, growth_attack=gatk, growth_defense=gdef, growth_speed=gspd,
                    acquire_method=acq, acquire_cost=cost, acquire_currency=cur,
                    evolve_target_id=evolve, evolve_required_level=evo_lvl,
                    diet=diet, favorite_food=food, icon=icon, model_id=model, color=color,
                )
                self._species[sid] = spec

            abilities_data = [
                ("pet_ability_bite", "Bite", "Deals physical damage to the target.",
                 PetSpecies.BEAST.value, 4.0, 1.5, 0.0, 0.0, 1),
                ("pet_ability_shell", "Shell Shield", "Reduces incoming damage for a duration.",
                 PetSpecies.BEAST.value, 15.0, 0.0, 0.0, 8.0, 5),
                ("pet_ability_heal", "Mend", "Heals the owner for a portion of pet attack.",
                 PetSpecies.MAGIC.value, 10.0, 0.0, 1.2, 0.0, 1),
                ("pet_ability_fireball", "Fireball", "Launches a ball of fire at the target.",
                 PetSpecies.DRAGONKIN.value, 6.0, 2.0, 0.0, 0.0, 1),
                ("pet_ability_stone_skin", "Stone Skin", "Grants temporary damage immunity.",
                 PetSpecies.ELEMENTAL.value, 20.0, 0.0, 0.0, 5.0, 10),
                ("pet_ability_sprint", "Sprint", "Increases pet speed temporarily.",
                 "", 8.0, 0.0, 0.0, 6.0, 1),
                ("pet_ability_taunt", "Taunt", "Forces enemies to attack the pet.",
                 "", 10.0, 0.0, 0.0, 4.0, 5),
            ]

            for aid, name, desc, restriction, cd, dmg, heal, dur, req_lvl in abilities_data:
                ab = PetAbility(
                    ability_id=aid, name=name, description=desc,
                    species_restriction=restriction, cooldown=cd,
                    damage_multiplier=dmg, healing_multiplier=heal,
                    duration=dur, required_pet_level=req_lvl,
                )
                self._abilities[aid] = ab

            # Seed player pets
            pp1 = PlayerPet(
                pet_id="pp_starter_wolf",
                player_id="player_starter",
                species_id="pet_wolf",
                name="Timber Wolf",
                custom_name="Shadow",
                status=PetStatus.SUMMONED.value,
                level=5,
                experience=500,
                current_health=168.0,
                max_health=168.0,
                attack=35.0,
                defense=18.0,
                speed=22.5,
                mood=PetMood.HAPPY.value,
                mood_value=70.0,
                loyalty=65.0,
                bond_level=2,
                bond_xp=50,
                learned_abilities=["pet_ability_bite", "pet_ability_sprint"],
                summon_count=42,
                last_summoned=_now() - 3600,
                total_battles=30,
                total_victories=25,
            )
            self._pets[pp1.pet_id] = pp1
            self._active_companions["player_starter"] = pp1.pet_id

            pp2 = PlayerPet(
                pet_id="pp_veteran_whelp",
                player_id="player_veteran",
                species_id="pet_whelp",
                name="Crimson Whelp",
                custom_name="Ember",
                status=PetStatus.STORED.value,
                level=28,
                experience=8400,
                current_health=540.0,
                max_health=540.0,
                attack=112.0,
                defense=55.5,
                speed=45.0,
                mood=PetMood.CONTENT.value,
                mood_value=55.0,
                loyalty=80.0,
                bond_level=4,
                bond_xp=350,
                learned_abilities=["pet_ability_fireball", "pet_ability_taunt", "pet_ability_bite"],
                summon_count=150,
                last_summoned=_now() - 86400,
                total_battles=200,
                total_victories=170,
            )
            self._pets[pp2.pet_id] = pp2

            pp3 = PlayerPet(
                pet_id="pp_veteran_turtle",
                player_id="player_veteran",
                species_id="pet_turtle",
                name="Ancient Turtle",
                custom_name="Boulder",
                status=PetStatus.STORED.value,
                level=15,
                experience=3000,
                current_health=470.0,
                max_health=470.0,
                attack=30.0,
                defense=73.5,
                speed=12.5,
                mood=PetMood.HAPPY.value,
                mood_value=65.0,
                loyalty=70.0,
                bond_level=3,
                bond_xp=200,
                learned_abilities=["pet_ability_shell", "pet_ability_taunt"],
                summon_count=80,
                last_summoned=_now() - 7200,
                total_battles=100,
                total_victories=75,
            )
            self._pets[pp3.pet_id] = pp3

            # Seed training sessions
            ts1 = PetTrainingSession(
                session_id="training_starter_wolf_01",
                pet_id="pp_starter_wolf",
                player_id="player_starter",
                training_type="attack",
                xp_gained=100,
                stat_before=30.0,
                stat_after=35.0,
                cost=25.0,
            )
            self._training[ts1.session_id] = ts1

            # Seed bond records
            br1 = PetBondRecord(
                bond_id="bond_starter_wolf_01",
                pet_id="pp_starter_wolf",
                player_id="player_starter",
                interaction="pet",
                bond_xp_gained=5,
                mood_change=3.0,
            )
            self._bonds[br1.bond_id] = br1

            self._update_stats()
            self._initialized = True

    def _log_event(self, kind: str, details: Dict[str, Any],
                   species_id: str = "", pet_id: str = "", player_id: str = "",
                   ability_id: str = "", description: str = "") -> None:
        self._event_counter += 1
        ev = PetEvent(
            event_id=f"pevt_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            species_id=species_id, pet_id=pet_id, player_id=player_id,
            ability_id=ability_id, description=description, details=details,
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_species = len(self._species)
        self._stats.total_abilities = len(self._abilities)
        self._stats.total_player_pets = len(self._pets)
        self._stats.total_summoned = sum(
            1 for p in self._pets.values()
            if p.status == PetStatus.SUMMONED.value
        )
        self._stats.total_training_sessions = len(self._training)
        self._stats.total_bond_records = len(self._bonds)
        self._stats.total_battles = sum(p.total_battles for p in self._pets.values())
        self._stats.total_victories = sum(p.total_victories for p in self._pets.values())

    # ------------------------------------------------------------------
    # Species Management
    # ------------------------------------------------------------------

    def register_species(self, species_id: str, name: str, description: str = "",
                         family: str = PetSpecies.BEAST.value,
                         role: str = PetRole.BALANCED.value,
                         rarity: str = "common",
                         base_health: float = 100.0, base_attack: float = 20.0,
                         base_defense: float = 15.0, base_speed: float = 10.0,
                         growth_health: float = 10.0, growth_attack: float = 2.0,
                         growth_defense: float = 1.5, growth_speed: float = 1.0,
                         max_level: int = 60,
                         acquire_method: str = AcquireMethod.TAME.value,
                         acquire_cost: float = 0.0, acquire_currency: str = "gold",
                         evolve_target_id: str = "", evolve_required_level: int = 0,
                         diet: str = "omnivore", favorite_food: str = "",
                         icon: str = "", model_id: str = "", color: str = "#FFFFFF"
                         ) -> Tuple[bool, str, Optional[PetSpeciesDefinition]]:
        with _LOCK:
            if species_id in self._species:
                return False, "species_exists", None
            if len(self._species) >= _MAX_SPECIES:
                return False, "max_species", None
            spec = PetSpeciesDefinition(
                species_id=species_id, name=name, description=description,
                family=family, role=role, rarity=rarity,
                base_health=base_health, base_attack=base_attack,
                base_defense=base_defense, base_speed=base_speed,
                growth_health=growth_health, growth_attack=growth_attack,
                growth_defense=growth_defense, growth_speed=growth_speed,
                max_level=max_level,
                acquire_method=acquire_method, acquire_cost=acquire_cost,
                acquire_currency=acquire_currency,
                evolve_target_id=evolve_target_id,
                evolve_required_level=evolve_required_level,
                diet=diet, favorite_food=favorite_food,
                icon=icon, model_id=model_id, color=color,
            )
            self._species[species_id] = spec
            self._log_event(PetEventKind.SPECIES_REGISTERED.value,
                            {"name": name}, species_id=species_id, description=name)
            self._update_stats()
            return True, "registered", spec

    def remove_species(self, species_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if species_id not in self._species:
                return False, "species_not_found"
            del self._species[species_id]
            self._log_event(PetEventKind.SPECIES_REMOVED.value,
                            {"species_id": species_id}, species_id=species_id)
            self._update_stats()
            return True, "removed"

    def get_species(self, species_id: str) -> Optional[PetSpeciesDefinition]:
        with _LOCK:
            return self._species.get(species_id)

    def list_species(self, family: str = "", role: str = "",
                     rarity: str = "") -> List[PetSpeciesDefinition]:
        with _LOCK:
            results = list(self._species.values())
            if family:
                results = [s for s in results if s.family == family]
            if role:
                results = [s for s in results if s.role == role]
            if rarity:
                results = [s for s in results if s.rarity == rarity]
            return results

    # ------------------------------------------------------------------
    # Ability Management
    # ------------------------------------------------------------------

    def register_ability(self, ability_id: str, name: str, description: str = "",
                         species_restriction: str = "", cooldown: float = 5.0,
                         damage_multiplier: float = 1.0, healing_multiplier: float = 0.0,
                         duration: float = 0.0, required_pet_level: int = 1,
                         icon: str = ""
                         ) -> Tuple[bool, str, Optional[PetAbility]]:
        with _LOCK:
            if ability_id in self._abilities:
                return False, "ability_exists", None
            if len(self._abilities) >= _MAX_ABILITIES:
                return False, "max_abilities", None
            ab = PetAbility(
                ability_id=ability_id, name=name, description=description,
                species_restriction=species_restriction, cooldown=cooldown,
                damage_multiplier=damage_multiplier, healing_multiplier=healing_multiplier,
                duration=duration, required_pet_level=required_pet_level, icon=icon,
            )
            self._abilities[ability_id] = ab
            self._log_event(PetEventKind.ABILITY_REGISTERED.value,
                            {"name": name}, ability_id=ability_id, description=name)
            self._update_stats()
            return True, "registered", ab

    def get_ability(self, ability_id: str) -> Optional[PetAbility]:
        with _LOCK:
            return self._abilities.get(ability_id)

    def list_abilities(self, species_restriction: str = "") -> List[PetAbility]:
        with _LOCK:
            results = list(self._abilities.values())
            if species_restriction:
                results = [a for a in results if a.species_restriction == species_restriction]
            return results

    # ------------------------------------------------------------------
    # Player Pet Management
    # ------------------------------------------------------------------

    def acquire_pet(self, player_id: str, species_id: str,
                    custom_name: str = ""
                    ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            spec = self._species.get(species_id)
            if spec is None:
                return False, "species_not_found", None
            player_pets = [p for p in self._pets.values() if p.player_id == player_id]
            if len(player_pets) >= self._config.max_pets_per_player:
                return False, "max_pets", None
            pet_id = _new_id("pp")
            pet = PlayerPet(
                pet_id=pet_id, player_id=player_id, species_id=species_id,
                name=spec.name, custom_name=custom_name,
                level=1, experience=0,
                current_health=spec.base_health,
                max_health=spec.base_health,
                attack=spec.base_attack,
                defense=spec.base_defense,
                speed=spec.base_speed,
                mood=PetMood.CONTENT.value,
                mood_value=50.0,
                loyalty=50.0,
            )
            self._pets[pet_id] = pet
            self._log_event(PetEventKind.PET_ACQUIRED.value,
                            {"species_id": species_id, "name": spec.name},
                            species_id=species_id, pet_id=pet_id,
                            player_id=player_id, description=f"Acquired {spec.name}")
            self._update_stats()
            return True, "acquired", pet

    def release_pet(self, pet_id: str) -> Tuple[bool, str]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found"
            if pet.status == PetStatus.SUMMONED.value:
                return False, "pet_summoned"
            if self._active_companions.get(pet.player_id) == pet_id:
                del self._active_companions[pet.player_id]
            del self._pets[pet_id]
            self._log_event(PetEventKind.PET_RELEASED.value,
                            {"pet_id": pet_id}, pet_id=pet_id, player_id=pet.player_id)
            self._update_stats()
            return True, "released"

    def get_pet(self, pet_id: str) -> Optional[PlayerPet]:
        with _LOCK:
            return self._pets.get(pet_id)

    def list_player_pets(self, player_id: str, status: str = "") -> List[PlayerPet]:
        with _LOCK:
            results = [p for p in self._pets.values() if p.player_id == player_id]
            if status:
                results = [p for p in results if p.status == status]
            return results

    # ------------------------------------------------------------------
    # Summon / Dismiss
    # ------------------------------------------------------------------

    def summon_companion(self, player_id: str, pet_id: str
                         ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            if pet.player_id != player_id:
                return False, "not_owner", None
            if pet.status == PetStatus.TRAINING.value:
                return False, "pet_training", None
            current_active = self._active_companions.get(player_id)
            if current_active and current_active != pet_id:
                old_pet = self._pets.get(current_active)
                if old_pet:
                    old_pet.status = PetStatus.STORED.value
                    self._log_event(PetEventKind.PET_DISMISSED.value,
                                    {"pet_id": current_active, "reason": "replaced"},
                                    pet_id=current_active, player_id=player_id)
            pet.status = PetStatus.SUMMONED.value
            pet.summon_count += 1
            pet.last_summoned = _now()
            self._active_companions[player_id] = pet_id
            self._log_event(PetEventKind.PET_SUMMONED.value,
                            {"pet_id": pet_id}, pet_id=pet_id, player_id=player_id)
            self._update_stats()
            return True, "summoned", pet

    def dismiss_companion(self, player_id: str
                          ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet_id = self._active_companions.get(player_id)
            if not pet_id:
                return False, "no_active", None
            pet = self._pets.get(pet_id)
            if pet is None:
                del self._active_companions[player_id]
                return False, "pet_not_found", None
            pet.status = PetStatus.STORED.value
            del self._active_companions[player_id]
            self._log_event(PetEventKind.PET_DISMISSED.value,
                            {"pet_id": pet_id}, pet_id=pet_id, player_id=player_id)
            self._update_stats()
            return True, "dismissed", pet

    def get_active_companion(self, player_id: str) -> Optional[PlayerPet]:
        with _LOCK:
            pet_id = self._active_companions.get(player_id)
            if not pet_id:
                return None
            return self._pets.get(pet_id)

    # ------------------------------------------------------------------
    # Mood & Feeding
    # ------------------------------------------------------------------

    def feed_pet(self, pet_id: str, food_item: str = ""
                 ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            spec = self._species.get(pet.species_id)
            mood_gain = self._config.base_feed_mood_gain
            if spec and spec.favorite_food and spec.favorite_food == food_item:
                mood_gain *= 2.0
            pet.mood_value = _clamp(pet.mood_value + mood_gain, 0.0, 100.0)
            pet.mood = self._mood_from_value(pet.mood_value)
            pet.last_fed = _now()
            self._log_event(PetEventKind.PET_FED.value,
                            {"food": food_item, "mood_gain": mood_gain},
                            pet_id=pet_id, player_id=pet.player_id)
            return True, "fed", pet

    def pet_mood_update(self, pet_id: str, mood_value: float
                        ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            pet.mood_value = _clamp(mood_value, 0.0, 100.0)
            pet.mood = self._mood_from_value(pet.mood_value)
            return True, "updated", pet

    def get_mood(self, pet_id: str) -> Optional[Tuple[str, float]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return None
            return pet.mood, pet.mood_value

    def _mood_from_value(self, value: float) -> str:
        if value >= 90:
            return PetMood.ECSTATIC.value
        if value >= 70:
            return PetMood.HAPPY.value
        if value >= 50:
            return PetMood.CONTENT.value
        if value >= 30:
            return PetMood.NEUTRAL.value
        if value >= 15:
            return PetMood.UNHAPPY.value
        return PetMood.MISERABLE.value

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train_pet(self, pet_id: str, training_type: str = "attack",
                  cost: float = 25.0, currency: str = "gold"
                  ) -> Tuple[bool, str, Optional[PetTrainingSession]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            if pet.status == PetStatus.SUMMONED.value:
                return False, "pet_summoned", None
            spec = self._species.get(pet.species_id)
            if spec is None:
                return False, "species_not_found", None
            xp_gained = 50 + pet.level * 5
            stat_before = 0.0
            stat_after = 0.0
            if training_type == "attack":
                stat_before = pet.attack
                pet.attack += spec.growth_attack * 0.5
                stat_after = pet.attack
            elif training_type == "defense":
                stat_before = pet.defense
                pet.defense += spec.growth_defense * 0.5
                stat_after = pet.defense
            elif training_type == "speed":
                stat_before = pet.speed
                pet.speed += spec.growth_speed * 0.5
                stat_after = pet.speed
            elif training_type == "health":
                stat_before = pet.max_health
                pet.max_health += spec.growth_health * 0.5
                pet.current_health = pet.max_health
                stat_after = pet.max_health
            session = PetTrainingSession(
                session_id=_new_id("training"),
                pet_id=pet_id, player_id=pet.player_id,
                training_type=training_type, xp_gained=xp_gained,
                stat_before=stat_before, stat_after=stat_after,
                cost=cost, currency=currency,
            )
            self._training[session.session_id] = session
            _evict_fifo_list(list(self._training.values()), _MAX_TRAINING_RECORDS)
            self._gain_pet_xp(pet, xp_gained)
            self._log_event(PetEventKind.PET_TRAINED.value,
                            {"type": training_type, "xp": xp_gained},
                            pet_id=pet_id, player_id=pet.player_id)
            self._update_stats()
            return True, "trained", session

    def get_training_history(self, pet_id: str) -> List[PetTrainingSession]:
        with _LOCK:
            return [t for t in self._training.values() if t.pet_id == pet_id]

    # ------------------------------------------------------------------
    # Abilities
    # ------------------------------------------------------------------

    def teach_ability(self, pet_id: str, ability_id: str
                      ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            ab = self._abilities.get(ability_id)
            if ab is None:
                return False, "ability_not_found", None
            if ability_id in pet.learned_abilities:
                return False, "already_known", pet
            if pet.level < ab.required_pet_level:
                return False, "level_too_low", pet
            if ab.species_restriction:
                spec = self._species.get(pet.species_id)
                if spec and spec.family != ab.species_restriction:
                    return False, "species_restricted", pet
            pet.learned_abilities.append(ability_id)
            self._log_event(PetEventKind.ABILITY_TAUGHT.value,
                            {"ability_id": ability_id},
                            pet_id=pet_id, player_id=pet.player_id, ability_id=ability_id)
            return True, "taught", pet

    def forget_ability(self, pet_id: str, ability_id: str
                       ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            if ability_id not in pet.learned_abilities:
                return False, "not_known", pet
            pet.learned_abilities.remove(ability_id)
            self._log_event(PetEventKind.ABILITY_FORGOTTEN.value,
                            {"ability_id": ability_id},
                            pet_id=pet_id, player_id=pet.player_id, ability_id=ability_id)
            return True, "forgotten", pet

    def get_pet_abilities(self, pet_id: str) -> List[PetAbility]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return []
            return [self._abilities[a] for a in pet.learned_abilities
                    if a in self._abilities]

    # ------------------------------------------------------------------
    # Equipment
    # ------------------------------------------------------------------

    def equip_pet_item(self, pet_id: str, slot: str, item_id: str,
                       item_name: str = "",
                       stat_bonuses: Optional[Dict[str, float]] = None
                       ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            if len(pet.equipped_slots) >= self._config.max_equipped_slots \
                    and slot not in pet.equipped_slots:
                return False, "max_slots", pet
            pet.equipped_slots[slot] = PetEquipmentSlot(
                slot=slot, item_id=item_id, item_name=item_name,
                stat_bonuses=stat_bonuses or {},
            )
            self._log_event(PetEventKind.EQUIPMENT_EQUIPPED.value,
                            {"slot": slot, "item_id": item_id},
                            pet_id=pet_id, player_id=pet.player_id)
            return True, "equipped", pet

    def unequip_pet_item(self, pet_id: str, slot: str
                         ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            if slot not in pet.equipped_slots:
                return False, "slot_empty", pet
            del pet.equipped_slots[slot]
            self._log_event(PetEventKind.EQUIPMENT_UNEQUIPPED.value,
                            {"slot": slot}, pet_id=pet_id, player_id=pet.player_id)
            return True, "unequipped", pet

    # ------------------------------------------------------------------
    # Leveling & Evolution
    # ------------------------------------------------------------------

    def gain_pet_xp(self, pet_id: str, xp: int
                    ) -> Tuple[bool, str, int, List[int]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", 0, []
            return self._gain_pet_xp(pet, xp)

    def _gain_pet_xp(self, pet: PlayerPet, xp: int) -> Tuple[bool, str, int, List[int]]:
        spec = self._species.get(pet.species_id)
        max_lvl = spec.max_level if spec else self._config.max_pet_level
        xp_per_level = self._config.xp_per_level
        pet.experience += xp
        levels_gained: List[int] = []
        while pet.level < max_lvl and pet.experience >= xp_per_level * pet.level:
            pet.experience -= xp_per_level * pet.level
            pet.level += 1
            if spec:
                pet.max_health = spec.base_health + spec.growth_health * (pet.level - 1)
                pet.current_health = pet.max_health
                pet.attack = spec.base_attack + spec.growth_attack * (pet.level - 1)
                pet.defense = spec.base_defense + spec.growth_defense * (pet.level - 1)
                pet.speed = spec.base_speed + spec.growth_speed * (pet.level - 1)
            levels_gained.append(pet.level)
            self._log_event(PetEventKind.PET_LEVEL_UP.value,
                            {"level": pet.level},
                            pet_id=pet.pet_id, player_id=pet.player_id)
        msg = "gained"
        if levels_gained:
            msg = "leveled_up"
        return True, msg, xp, levels_gained

    def level_up_pet(self, pet_id: str
                     ) -> Tuple[bool, str, int, List[int]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", 0, []
            spec = self._species.get(pet.species_id)
            max_lvl = spec.max_level if spec else self._config.max_pet_level
            if pet.level >= max_lvl:
                return False, "max_level", 0, []
            xp_needed = self._config.xp_per_level * pet.level
            return self._gain_pet_xp(pet, xp_needed)

    def evolve_pet(self, pet_id: str
                   ) -> Tuple[bool, str, Optional[PlayerPet]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            spec = self._species.get(pet.species_id)
            if spec is None or not spec.evolve_target_id:
                return False, "no_evolution", pet
            if pet.level < spec.evolve_required_level:
                return False, "level_too_low", pet
            target = self._species.get(spec.evolve_target_id)
            if target is None:
                return False, "target_not_found", pet
            pet.species_id = target.species_id
            pet.name = target.name
            pet.max_health = target.base_health + target.growth_health * (pet.level - 1)
            pet.current_health = pet.max_health
            pet.attack = target.base_attack + target.growth_attack * (pet.level - 1)
            pet.defense = target.base_defense + target.growth_defense * (pet.level - 1)
            pet.speed = target.base_speed + target.growth_speed * (pet.level - 1)
            self._stats.total_evolved += 1
            self._log_event(PetEventKind.PET_EVOLVED.value,
                            {"target": target.species_id},
                            pet_id=pet_id, player_id=pet.player_id,
                            species_id=target.species_id)
            return True, "evolved", pet

    # ------------------------------------------------------------------
    # Combat Power & Bond
    # ------------------------------------------------------------------

    def calculate_combat_power(self, pet_id: str) -> Optional[float]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return None
            return pet.combat_power

    def get_bond_level(self, pet_id: str) -> Optional[int]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return None
            return pet.bond_level

    def record_bond_interaction(self, pet_id: str, interaction: str = "pet"
                                ) -> Tuple[bool, str, Optional[PetBondRecord]]:
        with _LOCK:
            pet = self._pets.get(pet_id)
            if pet is None:
                return False, "pet_not_found", None
            bond_xp = self._config.bond_xp_per_interaction
            mood_change = 2.0
            if interaction == "play":
                bond_xp = 10
                mood_change = 5.0
            elif interaction == "feed":
                bond_xp = 5
                mood_change = 3.0
            elif interaction == "battle":
                bond_xp = 15
                mood_change = 1.0
            pet.bond_xp += bond_xp
            while pet.bond_xp >= self._config.bond_xp_per_level * pet.bond_level:
                pet.bond_xp -= self._config.bond_xp_per_level * pet.bond_level
                pet.bond_level += 1
            pet.mood_value = _clamp(pet.mood_value + mood_change, 0.0, 100.0)
            pet.mood = self._mood_from_value(pet.mood_value)
            pet.loyalty = _clamp(pet.loyalty + mood_change * 0.5, 0.0,
                                 self._config.loyalty_max)
            record = PetBondRecord(
                bond_id=_new_id("bond"),
                pet_id=pet_id, player_id=pet.player_id,
                interaction=interaction, bond_xp_gained=bond_xp,
                mood_change=mood_change,
            )
            self._bonds[record.bond_id] = record
            _evict_fifo_list(list(self._bonds.values()), _MAX_BOND_RECORDS)
            self._log_event(PetEventKind.BOND_INTERACTION.value,
                            {"interaction": interaction, "bond_xp": bond_xp},
                            pet_id=pet_id, player_id=pet.player_id)
            self._update_stats()
            return True, "recorded", record

    def get_bond_history(self, pet_id: str) -> List[PetBondRecord]:
        with _LOCK:
            return [b for b in self._bonds.values() if b.pet_id == pet_id]

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            decay = self._config.mood_decay_per_hour * (dt / 3600.0)
            for pet in self._pets.values():
                if pet.status != PetStatus.SUMMONED.value:
                    continue
                pet.mood_value = _clamp(pet.mood_value - decay, 0.0, 100.0)
                pet.mood = self._mood_from_value(pet.mood_value)
            if self._tick_count % 60 == 0:
                self._log_event(PetEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt})
            self._update_stats()
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, PetConfig]:
        with _LOCK:
            changed = []
            for k, v in config.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._log_event(PetEventKind.CONFIG_UPDATED.value,
                                {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> PetConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[PetEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> PetStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_species": len(self._species),
                "total_abilities": len(self._abilities),
                "total_player_pets": len(self._pets),
                "total_summoned": sum(
                    1 for p in self._pets.values()
                    if p.status == PetStatus.SUMMONED.value
                ),
                "total_training_records": len(self._training),
                "total_bond_records": len(self._bonds),
                "total_evolved": self._stats.total_evolved,
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> PetSnapshot:
        with _LOCK:
            return PetSnapshot(
                species=[s.to_dict() for s in list(self._species.values())[:20]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> None:
        with _LOCK:
            self._species.clear()
            self._abilities.clear()
            self._pets.clear()
            self._training.clear()
            self._bonds.clear()
            self._active_companions.clear()
            self._events.clear()
            self._stats = PetStats()
            self._config = PetConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._log_event(PetEventKind.RESET.value, {})
            self._seed()


def get_pet_companion_system() -> PetCompanionSystem:
    """Factory that returns the singleton PetCompanionSystem instance."""
    return PetCompanionSystem.get_instance()
