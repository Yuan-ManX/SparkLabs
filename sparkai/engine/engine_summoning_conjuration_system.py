"""
SparkLabs Engine - Summoning & Conjuration System

Manages summonable entities conjured through rituals, contracts, and
focusing artifacts. Summoners bind templates into active servants via
rituals that consume mana and reagents, then deploy them in combat,
harvesting, or scouting scenarios. Contracts gate how often a summoner
may conjure a given template, while focuses amplify power, reduce mana
cost, and bias the resulting rarity.

Architecture:
  SummoningConjurationSystem (singleton)
    |-- SummonType, SummonRarity, ContractStatus, SummonState,
       SummoningEventKind
    |-- SummonTemplate, SummonContract, ActiveSummon, SummoningRitual,
       SummoningFocus, SummoningStats, SummoningConfig, SummoningSnapshot,
       SummoningEvent
    |-- get_summoning_conjuration_system

Core Capabilities:
  - register_summon_template / get_summon_template / list_summon_templates /
    remove_summon_template
  - register_ritual / get_ritual / list_rituals / remove_ritual
  - register_focus / get_focus / list_focuses / remove_focus
  - create_contract / get_contract / list_contracts / break_contract
  - perform_summoning (summon using contract + ritual + focus)
  - banish_summon / get_active_summon / list_active_summons
  - calculate_summon_power / get_summon_abilities
  - tick / set_config / get_config / list_events / get_stats
  - get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SummoningConjurationSystem.get_instance` or the module-level
:func:`get_summoning_conjuration_system` factory.
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

_MAX_TEMPLATES: int = 1000
_MAX_RITUALS: int = 500
_MAX_FOCUSES: int = 1000
_MAX_CONTRACTS: int = 100000
_MAX_ACTIVE_SUMMONS: int = 200000
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

class SummonType(str, Enum):
    """Taxonomic family of a summonable entity."""
    ELEMENTAL = "elemental"
    CONSTRUCT = "construct"
    BEAST = "beast"
    SPIRIT = "spirit"
    UNDEAD = "undead"
    DEMON = "demon"
    CELESTIAL = "celestial"
    VOID = "void"


class SummonRarity(str, Enum):
    """Rarity tier that gates base stats and summoning difficulty."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class ContractStatus(str, Enum):
    """Lifecycle state of a summoning contract."""
    ACTIVE = "active"
    BROKEN = "broken"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class SummonState(str, Enum):
    """Deployment state of an active summon."""
    IDLE = "idle"
    SUMMONED = "summoned"
    BANISHED = "banished"
    RESTING = "resting"
    DEFEATED = "defeated"


class SummoningEventKind(str, Enum):
    """Audit event types emitted by the summoning system."""
    TEMPLATE_REGISTERED = "template_registered"
    TEMPLATE_REMOVED = "template_removed"
    RITUAL_REGISTERED = "ritual_registered"
    RITUAL_REMOVED = "ritual_removed"
    FOCUS_REGISTERED = "focus_registered"
    FOCUS_REMOVED = "focus_removed"
    CONTRACT_CREATED = "contract_created"
    CONTRACT_BROKEN = "contract_broken"
    SUMMON_PERFORMED = "summon_performed"
    SUMMON_BANISHED = "summon_banished"
    SUMMON_DEFEATED = "summon_defeated"
    FOCUS_DAMAGED = "focus_damaged"
    FOCUS_BROKEN = "focus_broken"
    CONTRACT_EXPIRED = "contract_expired"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SummonTemplate:
    """Definition of a summonable entity that can be conjured."""
    template_id: str
    name: str
    summon_type: str = SummonType.ELEMENTAL.value
    rarity: str = SummonRarity.COMMON.value
    description: str = ""
    base_health: float = 100.0
    base_attack: float = 20.0
    base_defense: float = 15.0
    base_speed: float = 10.0
    base_mana_cost: float = 50.0
    base_duration: float = 60.0
    min_summoner_level: int = 1
    element: str = ""
    abilities: List[str] = field(default_factory=list)
    icon: str = ""
    model_id: str = ""
    color: str = "#FFFFFF"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SummonContract:
    """A binding contract permitting a summoner to conjure a template."""
    contract_id: str
    summoner_id: str
    template_id: str
    status: str = ContractStatus.ACTIVE.value
    duration: float = 60.0
    mana_cost: float = 50.0
    power_multiplier: float = 1.0
    max_summons: int = 100
    summon_count: int = 0
    created_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ActiveSummon:
    """A live summon currently deployed in the world."""
    summon_id: str
    contract_id: str
    summoner_id: str
    template_id: str
    name: str = ""
    state: str = SummonState.SUMMONED.value
    current_health: float = 100.0
    max_health: float = 100.0
    attack: float = 20.0
    defense: float = 15.0
    speed: float = 10.0
    power: float = 0.0
    abilities: List[str] = field(default_factory=list)
    summoned_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        if self.expires_at <= 0.0:
            return False
        return _now() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_expired"] = self.is_expired
        return d


@dataclass
class SummoningRitual:
    """A ritual that shapes the conjuration process."""
    ritual_id: str
    name: str
    description: str = ""
    required_focus_tier: int = 1
    duration: float = 10.0
    mana_cost: float = 100.0
    power_bonus: float = 1.0
    success_rate: float = 0.9
    rarity_bias: str = ""
    summon_type_restriction: str = ""
    reagents: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SummoningFocus:
    """A focusing artifact that amplifies summoning outcomes."""
    focus_id: str
    name: str
    description: str = ""
    tier: int = 1
    power_multiplier: float = 1.0
    mana_efficiency: float = 1.0
    durability: float = 100.0
    max_durability: float = 100.0
    summon_type_bonus: str = ""
    rarity_bonus: float = 0.0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_broken(self) -> bool:
        return self.durability <= 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["is_broken"] = self.is_broken
        return d


@dataclass
class SummoningConfig:
    """Global tuning parameters."""
    max_templates: int = 1000
    max_rituals: int = 500
    max_focuses: int = 1000
    max_contracts: int = 100000
    max_active_summons: int = 200000
    max_summons_per_summoner: int = 3
    base_mana_cost: float = 50.0
    base_duration: float = 60.0
    durability_decay_per_summon: float = 5.0
    power_decay_per_hour: float = 2.0
    summon_cooldown: float = 5.0
    contract_expiry_seconds: float = 86400.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SummoningStats:
    """Aggregate statistics."""
    total_templates: int = 0
    total_rituals: int = 0
    total_focuses: int = 0
    total_contracts: int = 0
    total_active_summons: int = 0
    total_summons_performed: int = 0
    total_summons_banished: int = 0
    total_contracts_broken: int = 0
    total_defeated: int = 0
    total_focuses_broken: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SummoningSnapshot:
    """Full state snapshot."""
    templates: List[Dict[str, Any]] = field(default_factory=list)
    rituals: List[Dict[str, Any]] = field(default_factory=list)
    focuses: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SummoningEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    template_id: str = ""
    contract_id: str = ""
    summon_id: str = ""
    summoner_id: str = ""
    ritual_id: str = ""
    focus_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Summoning & Conjuration System
# ---------------------------------------------------------------------------

class SummoningConjurationSystem:
    """Manages summon templates, rituals, focuses, contracts, and active summons."""

    _instance: Optional["SummoningConjurationSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._templates: Dict[str, SummonTemplate] = {}
        self._rituals: Dict[str, SummoningRitual] = {}
        self._focuses: Dict[str, SummoningFocus] = {}
        self._contracts: Dict[str, SummonContract] = {}
        self._active_summons: Dict[str, ActiveSummon] = {}
        self._summoner_summons: Dict[str, List[str]] = {}
        self._events: List[SummoningEvent] = []
        self._stats = SummoningStats()
        self._config = SummoningConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "SummoningConjurationSystem":
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

            template_data = [
                ("tmpl_fire_elemental", "Fire Elemental",
                 "A blazing spirit of flame that scorches foes.",
                 SummonType.ELEMENTAL.value, SummonRarity.UNCOMMON.value,
                 120.0, 30.0, 10.0, 14.0, 60.0, 90.0, 5, "fire",
                 ["abil_fireball", "abil_flame_shield"], "icon_fire",
                 "model_fire_elem", "#FF4500"),
                ("tmpl_water_elemental", "Water Elemental",
                 "A flowing guardian of water that heals and freezes.",
                 SummonType.ELEMENTAL.value, SummonRarity.UNCOMMON.value,
                 140.0, 22.0, 18.0, 9.0, 65.0, 100.0, 5, "water",
                 ["abil_frost_nova", "abil_mend"], "icon_water",
                 "model_water_elem", "#1E90FF"),
                ("tmpl_earth_elemental", "Earth Elemental",
                 "A towering bulwark of stone and soil.",
                 SummonType.ELEMENTAL.value, SummonRarity.RARE.value,
                 220.0, 18.0, 35.0, 4.0, 80.0, 120.0, 10, "earth",
                 ["abil_stone_skin", "abil_quake"], "icon_earth",
                 "model_earth_elem", "#8B4513"),
                ("tmpl_air_elemental", "Air Elemental",
                 "A swift zephyr that strikes from a distance.",
                 SummonType.ELEMENTAL.value, SummonRarity.UNCOMMON.value,
                 90.0, 26.0, 8.0, 22.0, 55.0, 80.0, 5, "air",
                 ["abil_gust", "abil_lightning"], "icon_air",
                 "model_air_elem", "#E0FFFF"),
                ("tmpl_iron_golem", "Iron Golem",
                 "A heavy construct forged from tempered iron plates.",
                 SummonType.CONSTRUCT.value, SummonRarity.EPIC.value,
                 300.0, 28.0, 45.0, 3.0, 120.0, 180.0, 20, "metal",
                 ["abil_slam", "abil_iron_wall"], "icon_golem",
                 "model_iron_golem", "#708090"),
                ("tmpl_spirit_wolf", "Spirit Wolf",
                 "An ethereal wolf that hunts the boundaries of life.",
                 SummonType.SPIRIT.value, SummonRarity.RARE.value,
                 110.0, 34.0, 12.0, 24.0, 70.0, 90.0, 8, "spirit",
                 ["abil_phase_bite", "abil_howl"], "icon_wolf",
                 "model_spirit_wolf", "#9370DB"),
                ("tmpl_dire_wolf", "Dire Wolf",
                 "A massive feral beast with crushing jaws.",
                 SummonType.BEAST.value, SummonRarity.UNCOMMON.value,
                 160.0, 32.0, 16.0, 20.0, 60.0, 95.0, 6, "beast",
                 ["abil_savage_bite", "abil_pounce"], "icon_dire_wolf",
                 "model_dire_wolf", "#696969"),
                ("tmpl_skeleton", "Risen Skeleton",
                 "A skeletal warrior bound to unlife by dark pact.",
                 SummonType.UNDEAD.value, SummonRarity.COMMON.value,
                 80.0, 18.0, 10.0, 12.0, 40.0, 120.0, 1, "death",
                 ["abil_bone_strike", "abil_unholy_vigor"], "icon_skeleton",
                 "model_skeleton", "#C0C0C0"),
                ("tmpl_celestial_guardian", "Celestial Guardian",
                 "A radiant servant of the higher planes.",
                 SummonType.CELESTIAL.value, SummonRarity.LEGENDARY.value,
                 260.0, 32.0, 30.0, 16.0, 150.0, 150.0, 30, "holy",
                 ["abil_smite", "abil_radiant_ward", "abil_mend"], "icon_guardian",
                 "model_celestial", "#FFD700"),
                ("tmpl_void_horror", "Void Horror",
                 "A writhing tear in reality given terrible form.",
                 SummonType.VOID.value, SummonRarity.MYTHIC.value,
                 200.0, 40.0, 20.0, 18.0, 180.0, 110.0, 40, "void",
                 ["abil_void_rift", "abil_annihilate"], "icon_void",
                 "model_void_horror", "#4B0082"),
                ("tmpl_lesser_demon", "Lesser Demon",
                 "A horned fiend summoned through blood and sulfur.",
                 SummonType.DEMON.value, SummonRarity.EPIC.value,
                 180.0, 36.0, 18.0, 14.0, 110.0, 130.0, 18, "fire",
                 ["abil_hellfire", "abil_demonic_frenzy"], "icon_demon",
                 "model_demon", "#8B0000"),
            ]

            for (tid, name, desc, stype, rarity,
                 bhp, batk, bdef, bspd, bmana, bdur, mlevel, elem,
                 abils, icon, model, color) in template_data:
                tmpl = SummonTemplate(
                    template_id=tid, name=name, description=desc,
                    summon_type=stype, rarity=rarity,
                    base_health=bhp, base_attack=batk,
                    base_defense=bdef, base_speed=bspd,
                    base_mana_cost=bmana, base_duration=bdur,
                    min_summoner_level=mlevel, element=elem,
                    abilities=list(abils), icon=icon,
                    model_id=model, color=color,
                )
                self._templates[tid] = tmpl

            ritual_data = [
                ("ritual_lesser_call", "Lesser Calling",
                 "A short rite to summon common entities.",
                 1, 5.0, 50.0, 1.0, 0.85, SummonRarity.COMMON.value, "",
                 ["reagent_salt", "reagent_candle"]),
                ("ritual_greater_bond", "Greater Bonding",
                 "A sustained ritual binding potent servants.",
                 2, 15.0, 120.0, 1.5, 0.75, SummonRarity.RARE.value, "",
                 ["reagent_crystal", "reagent_incense", "reagent_blood"]),
                ("ritual_forbidden_pact", "Forbidden Pact",
                 "A dangerous rite that calls forth demons and void horrors.",
                 3, 30.0, 220.0, 2.2, 0.55, SummonRarity.MYTHIC.value, "",
                 ["reagent_soul_shard", "reagent_abyssal_ink", "reagent_black_candle"]),
            ]

            for (rid, name, desc, ftier, dur, mana, pbonus, srate,
                 rbias, restrict, reagents) in ritual_data:
                rit = SummoningRitual(
                    ritual_id=rid, name=name, description=desc,
                    required_focus_tier=ftier, duration=dur,
                    mana_cost=mana, power_bonus=pbonus,
                    success_rate=srate, rarity_bias=rbias,
                    summon_type_restriction=restrict,
                    reagents=list(reagents),
                )
                self._rituals[rid] = rit

            focus_data = [
                ("focus_apprentice_orb", "Apprentice Orb",
                 "A simple crystal orb for novice summoners.",
                 1, 1.0, 1.05, 100.0, 100.0, "", 0.0, "icon_orb"),
                ("focus_journeyman_crystal", "Journeyman Crystal",
                 "A faceted crystal that steadies the conjuring flow.",
                 2, 1.15, 1.1, 120.0, 120.0, SummonType.ELEMENTAL.value, 0.05,
                 "icon_crystal"),
                ("focus_warlock_talisman", "Warlock Talisman",
                 "A bone talisman favored by demonologists.",
                 2, 1.2, 1.05, 110.0, 110.0, SummonType.DEMON.value, 0.1,
                 "icon_talisman"),
                ("focus_necromancer_staff", "Necromancer Staff",
                 "A staff threaded with deathly resonance.",
                 3, 1.3, 1.15, 140.0, 140.0, SummonType.UNDEAD.value, 0.1,
                 "icon_staff"),
                ("focus_celestial_sigil", "Celestial Sigil",
                 "A glowing sigil blessed by celestial hands.",
                 3, 1.35, 1.2, 150.0, 150.0, SummonType.CELESTIAL.value, 0.15,
                 "icon_sigil"),
            ]

            for (fid, name, desc, tier, pmult, meff, dur, mdur,
                 stbonus, rbonus, icon) in focus_data:
                foc = SummoningFocus(
                    focus_id=fid, name=name, description=desc,
                    tier=tier, power_multiplier=pmult,
                    mana_efficiency=meff, durability=dur,
                    max_durability=mdur, summon_type_bonus=stbonus,
                    rarity_bonus=rbonus, icon=icon,
                )
                self._focuses[fid] = foc

            # Seed active contracts
            contract1 = SummonContract(
                contract_id="contract_starter_fire",
                summoner_id="summoner_starter",
                template_id="tmpl_fire_elemental",
                status=ContractStatus.ACTIVE.value,
                duration=90.0,
                mana_cost=60.0,
                power_multiplier=1.0,
                max_summons=100,
                summon_count=12,
                expires_at=_now() + 86400.0,
            )
            self._contracts[contract1.contract_id] = contract1

            contract2 = SummonContract(
                contract_id="contract_veteran_guardian",
                summoner_id="summoner_veteran",
                template_id="tmpl_celestial_guardian",
                status=ContractStatus.ACTIVE.value,
                duration=150.0,
                mana_cost=160.0,
                power_multiplier=1.2,
                max_summons=50,
                summon_count=8,
                expires_at=_now() + 86400.0 * 7.0,
            )
            self._contracts[contract2.contract_id] = contract2

            # Seed one active summon tied to the starter contract
            fire_tmpl = self._templates.get("tmpl_fire_elemental")
            if fire_tmpl is not None:
                active = ActiveSummon(
                    summon_id="summon_starter_fire_01",
                    contract_id=contract1.contract_id,
                    summoner_id="summoner_starter",
                    template_id="tmpl_fire_elemental",
                    name=fire_tmpl.name,
                    state=SummonState.SUMMONED.value,
                    current_health=fire_tmpl.base_health,
                    max_health=fire_tmpl.base_health,
                    attack=fire_tmpl.base_attack,
                    defense=fire_tmpl.base_defense,
                    speed=fire_tmpl.base_speed,
                    power=self._compute_power(fire_tmpl, 1.0),
                    abilities=list(fire_tmpl.abilities),
                    summoned_at=_now() - 600.0,
                    expires_at=_now() + fire_tmpl.base_duration,
                )
                self._active_summons[active.summon_id] = active
                self._summoner_summons.setdefault("summoner_starter", []).append(
                    active.summon_id
                )

            self._update_stats()
            self._initialized = True

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    def _emit(self, kind: str, details: Dict[str, Any],
              template_id: str = "", contract_id: str = "",
              summon_id: str = "", summoner_id: str = "",
              ritual_id: str = "", focus_id: str = "",
              description: str = "") -> None:
        self._event_counter += 1
        ev = SummoningEvent(
            event_id=f"sevt_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            template_id=template_id, contract_id=contract_id,
            summon_id=summon_id, summoner_id=summoner_id,
            ritual_id=ritual_id, focus_id=focus_id,
            description=description, details=details,
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_templates = len(self._templates)
        self._stats.total_rituals = len(self._rituals)
        self._stats.total_focuses = len(self._focuses)
        self._stats.total_contracts = len(self._contracts)
        self._stats.total_active_summons = len(self._active_summons)

    # ------------------------------------------------------------------
    # Power Calculation Helpers
    # ------------------------------------------------------------------

    def _compute_power(self, template: SummonTemplate,
                       multiplier: float) -> float:
        base = (template.base_attack * 2.0
                + template.base_defense * 1.5
                + template.base_speed
                + template.base_health * 0.1)
        rarity_mult = self._rarity_multiplier(template.rarity)
        return round(base * rarity_mult * multiplier, 1)

    def _rarity_multiplier(self, rarity: str) -> float:
        mapping = {
            SummonRarity.COMMON.value: 1.0,
            SummonRarity.UNCOMMON.value: 1.15,
            SummonRarity.RARE.value: 1.35,
            SummonRarity.EPIC.value: 1.6,
            SummonRarity.LEGENDARY.value: 2.0,
            SummonRarity.MYTHIC.value: 2.6,
        }
        return mapping.get(rarity, 1.0)

    # ------------------------------------------------------------------
    # Template Management
    # ------------------------------------------------------------------

    def register_summon_template(self, template_id: str, name: str,
                                 summon_type: str = SummonType.ELEMENTAL.value,
                                 rarity: str = SummonRarity.COMMON.value,
                                 description: str = "",
                                 base_health: float = 100.0,
                                 base_attack: float = 20.0,
                                 base_defense: float = 15.0,
                                 base_speed: float = 10.0,
                                 base_mana_cost: float = 50.0,
                                 base_duration: float = 60.0,
                                 min_summoner_level: int = 1,
                                 element: str = "",
                                 abilities: Optional[List[str]] = None,
                                 icon: str = "", model_id: str = "",
                                 color: str = "#FFFFFF"
                                 ) -> Tuple[bool, str, Optional[SummonTemplate]]:
        with _LOCK:
            if template_id in self._templates:
                return False, "template_exists", None
            if len(self._templates) >= _MAX_TEMPLATES:
                return False, "max_templates", None
            tmpl = SummonTemplate(
                template_id=template_id, name=name, description=description,
                summon_type=summon_type, rarity=rarity,
                base_health=base_health, base_attack=base_attack,
                base_defense=base_defense, base_speed=base_speed,
                base_mana_cost=base_mana_cost, base_duration=base_duration,
                min_summoner_level=min_summoner_level, element=element,
                abilities=list(abilities or []), icon=icon,
                model_id=model_id, color=color,
            )
            self._templates[template_id] = tmpl
            self._emit(SummoningEventKind.TEMPLATE_REGISTERED.value,
                       {"name": name}, template_id=template_id,
                       description=name)
            self._update_stats()
            return True, "registered", tmpl

    def get_summon_template(self, template_id: str) -> Optional[SummonTemplate]:
        with _LOCK:
            return self._templates.get(template_id)

    def list_summon_templates(self, summon_type: str = "",
                              rarity: str = "",
                              element: str = "") -> List[SummonTemplate]:
        with _LOCK:
            results = list(self._templates.values())
            if summon_type:
                results = [t for t in results if t.summon_type == summon_type]
            if rarity:
                results = [t for t in results if t.rarity == rarity]
            if element:
                results = [t for t in results if t.element == element]
            return results

    def remove_summon_template(self, template_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if template_id not in self._templates:
                return False, "template_not_found"
            del self._templates[template_id]
            self._emit(SummoningEventKind.TEMPLATE_REMOVED.value,
                       {"template_id": template_id},
                       template_id=template_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Ritual Management
    # ------------------------------------------------------------------

    def register_ritual(self, ritual_id: str, name: str,
                        description: str = "",
                        required_focus_tier: int = 1,
                        duration: float = 10.0,
                        mana_cost: float = 100.0,
                        power_bonus: float = 1.0,
                        success_rate: float = 0.9,
                        rarity_bias: str = "",
                        summon_type_restriction: str = "",
                        reagents: Optional[List[str]] = None
                        ) -> Tuple[bool, str, Optional[SummoningRitual]]:
        with _LOCK:
            if ritual_id in self._rituals:
                return False, "ritual_exists", None
            if len(self._rituals) >= _MAX_RITUALS:
                return False, "max_rituals", None
            rit = SummoningRitual(
                ritual_id=ritual_id, name=name, description=description,
                required_focus_tier=required_focus_tier,
                duration=duration, mana_cost=mana_cost,
                power_bonus=power_bonus, success_rate=success_rate,
                rarity_bias=rarity_bias,
                summon_type_restriction=summon_type_restriction,
                reagents=list(reagents or []),
            )
            self._rituals[ritual_id] = rit
            self._emit(SummoningEventKind.RITUAL_REGISTERED.value,
                       {"name": name}, ritual_id=ritual_id,
                       description=name)
            self._update_stats()
            return True, "registered", rit

    def get_ritual(self, ritual_id: str) -> Optional[SummoningRitual]:
        with _LOCK:
            return self._rituals.get(ritual_id)

    def list_rituals(self, summon_type_restriction: str = "") -> List[SummoningRitual]:
        with _LOCK:
            results = list(self._rituals.values())
            if summon_type_restriction:
                results = [r for r in results
                           if r.summon_type_restriction == summon_type_restriction]
            return results

    def remove_ritual(self, ritual_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if ritual_id not in self._rituals:
                return False, "ritual_not_found"
            del self._rituals[ritual_id]
            self._emit(SummoningEventKind.RITUAL_REMOVED.value,
                       {"ritual_id": ritual_id}, ritual_id=ritual_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Focus Management
    # ------------------------------------------------------------------

    def register_focus(self, focus_id: str, name: str,
                       description: str = "",
                       tier: int = 1,
                       power_multiplier: float = 1.0,
                       mana_efficiency: float = 1.0,
                       durability: float = 100.0,
                       max_durability: float = 100.0,
                       summon_type_bonus: str = "",
                       rarity_bonus: float = 0.0,
                       icon: str = ""
                       ) -> Tuple[bool, str, Optional[SummoningFocus]]:
        with _LOCK:
            if focus_id in self._focuses:
                return False, "focus_exists", None
            if len(self._focuses) >= _MAX_FOCUSES:
                return False, "max_focuses", None
            foc = SummoningFocus(
                focus_id=focus_id, name=name, description=description,
                tier=tier, power_multiplier=power_multiplier,
                mana_efficiency=mana_efficiency,
                durability=durability, max_durability=max_durability,
                summon_type_bonus=summon_type_bonus,
                rarity_bonus=rarity_bonus, icon=icon,
            )
            self._focuses[focus_id] = foc
            self._emit(SummoningEventKind.FOCUS_REGISTERED.value,
                       {"name": name}, focus_id=focus_id,
                       description=name)
            self._update_stats()
            return True, "registered", foc

    def get_focus(self, focus_id: str) -> Optional[SummoningFocus]:
        with _LOCK:
            return self._focuses.get(focus_id)

    def list_focuses(self, summon_type_bonus: str = "",
                     min_tier: int = 0) -> List[SummoningFocus]:
        with _LOCK:
            results = list(self._focuses.values())
            if summon_type_bonus:
                results = [f for f in results
                           if f.summon_type_bonus == summon_type_bonus]
            if min_tier > 0:
                results = [f for f in results if f.tier >= min_tier]
            return results

    def remove_focus(self, focus_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if focus_id not in self._focuses:
                return False, "focus_not_found"
            del self._focuses[focus_id]
            self._emit(SummoningEventKind.FOCUS_REMOVED.value,
                       {"focus_id": focus_id}, focus_id=focus_id)
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Contract Management
    # ------------------------------------------------------------------

    def create_contract(self, summoner_id: str, template_id: str,
                        duration: float = 0.0,
                        mana_cost: float = 0.0,
                        power_multiplier: float = 1.0,
                        max_summons: int = 100,
                        expires_in: float = 0.0
                        ) -> Tuple[bool, str, Optional[SummonContract]]:
        with _LOCK:
            tmpl = self._templates.get(template_id)
            if tmpl is None:
                return False, "template_not_found", None
            if duration <= 0.0:
                duration = tmpl.base_duration
            if mana_cost <= 0.0:
                mana_cost = tmpl.base_mana_cost
            contract_id = _new_id("contract")
            contract = SummonContract(
                contract_id=contract_id,
                summoner_id=summoner_id,
                template_id=template_id,
                status=ContractStatus.ACTIVE.value,
                duration=duration,
                mana_cost=mana_cost,
                power_multiplier=power_multiplier,
                max_summons=max_summons,
                summon_count=0,
                expires_at=(_now() + expires_in) if expires_in > 0.0 else 0.0,
            )
            self._contracts[contract_id] = contract
            self._emit(SummoningEventKind.CONTRACT_CREATED.value,
                       {"template_id": template_id, "summoner_id": summoner_id},
                       contract_id=contract_id, summoner_id=summoner_id,
                       template_id=template_id,
                       description=f"Contract created for {tmpl.name}")
            self._update_stats()
            return True, "created", contract

    def get_contract(self, contract_id: str) -> Optional[SummonContract]:
        with _LOCK:
            return self._contracts.get(contract_id)

    def list_contracts(self, summoner_id: str = "",
                       status: str = "") -> List[SummonContract]:
        with _LOCK:
            results = list(self._contracts.values())
            if summoner_id:
                results = [c for c in results if c.summoner_id == summoner_id]
            if status:
                results = [c for c in results if c.status == status]
            return results

    def break_contract(self, contract_id: str) -> Tuple[bool, str]:
        with _LOCK:
            contract = self._contracts.get(contract_id)
            if contract is None:
                return False, "contract_not_found"
            if contract.status == ContractStatus.BROKEN.value:
                return False, "already_broken"
            contract.status = ContractStatus.BROKEN.value
            # Banish any active summons tied to this contract
            banished_ids: List[str] = []
            for summon in self._active_summons.values():
                if summon.contract_id == contract_id:
                    summon.state = SummonState.BANISHED.value
                    banished_ids.append(summon.summon_id)
            self._stats.total_contracts_broken += 1
            self._emit(SummoningEventKind.CONTRACT_BROKEN.value,
                       {"contract_id": contract_id,
                        "banished_summons": len(banished_ids)},
                       contract_id=contract_id,
                       summoner_id=contract.summoner_id)
            self._update_stats()
            return True, "broken"

    # ------------------------------------------------------------------
    # Summoning
    # ------------------------------------------------------------------

    def perform_summoning(self, summoner_id: str, contract_id: str,
                          ritual_id: str = "",
                          focus_id: str = ""
                          ) -> Tuple[bool, str, Optional[ActiveSummon]]:
        with _LOCK:
            contract = self._contracts.get(contract_id)
            if contract is None:
                return False, "contract_not_found", None
            if contract.status != ContractStatus.ACTIVE.value:
                return False, "contract_inactive", None
            if contract.summon_count >= contract.max_summons:
                return False, "contract_exhausted", None
            if contract.expires_at > 0.0 and _now() >= contract.expires_at:
                contract.status = ContractStatus.EXPIRED.value
                self._emit(SummoningEventKind.CONTRACT_EXPIRED.value,
                           {"contract_id": contract_id},
                           contract_id=contract_id, summoner_id=summoner_id)
                return False, "contract_expired", None

            tmpl = self._templates.get(contract.template_id)
            if tmpl is None:
                return False, "template_not_found", None

            ritual = self._rituals.get(ritual_id) if ritual_id else None
            focus = self._focuses.get(focus_id) if focus_id else None

            # Validate ritual constraints
            if ritual is not None:
                if (ritual.summon_type_restriction
                        and ritual.summon_type_restriction != tmpl.summon_type):
                    return False, "ritual_type_mismatch", None
                if focus is not None and focus.tier < ritual.required_focus_tier:
                    return False, "focus_tier_too_low", None

            # Validate focus
            if focus is not None and focus.is_broken:
                return False, "focus_broken", None

            # Enforce per-summoner active summon cap
            active_for_summoner = self._summoner_summons.get(summoner_id, [])
            live_active = [sid for sid in active_for_summoner
                           if sid in self._active_summons
                           and self._active_summons[sid].state
                           in (SummonState.SUMMONED.value,
                               SummonState.IDLE.value)]
            if len(live_active) >= self._config.max_summons_per_summoner:
                return False, "max_active_summons", None

            # Compute power multiplier from contract, ritual, and focus
            power_mult = contract.power_multiplier
            mana_cost = contract.mana_cost
            if ritual is not None:
                power_mult *= ritual.power_bonus
                mana_cost += ritual.mana_cost
            if focus is not None:
                power_mult *= focus.power_multiplier
                mana_cost /= max(0.1, focus.mana_efficiency)
                if focus.summon_type_bonus and focus.summon_type_bonus == tmpl.summon_type:
                    power_mult *= 1.1
                if focus.rarity_bonus > 0.0:
                    power_mult += focus.rarity_bonus
            mana_cost = max(1.0, round(mana_cost, 1))

            # Apply focus durability decay
            if focus is not None:
                decay = self._config.durability_decay_per_summon
                before_dur = focus.durability
                focus.durability = _clamp(focus.durability - decay,
                                          0.0, focus.max_durability)
                self._emit(SummoningEventKind.FOCUS_DAMAGED.value,
                           {"focus_id": focus.focus_id,
                            "before": before_dur,
                            "after": focus.durability},
                           focus_id=focus.focus_id, summoner_id=summoner_id)
                if focus.is_broken:
                    self._stats.total_focuses_broken += 1
                    self._emit(SummoningEventKind.FOCUS_BROKEN.value,
                               {"focus_id": focus.focus_id},
                               focus_id=focus.focus_id, summoner_id=summoner_id)

            # Build the active summon
            summon_id = _new_id("summon")
            power = self._compute_power(tmpl, power_mult)
            expires_at = _now() + contract.duration
            summon = ActiveSummon(
                summon_id=summon_id,
                contract_id=contract_id,
                summoner_id=summoner_id,
                template_id=tmpl.template_id,
                name=tmpl.name,
                state=SummonState.SUMMONED.value,
                current_health=tmpl.base_health,
                max_health=tmpl.base_health,
                attack=round(tmpl.base_attack * power_mult, 1),
                defense=round(tmpl.base_defense * power_mult, 1),
                speed=round(tmpl.base_speed * power_mult, 1),
                power=power,
                abilities=list(tmpl.abilities),
                summoned_at=_now(),
                expires_at=expires_at,
                metadata={
                    "mana_cost": mana_cost,
                    "ritual_id": ritual_id,
                    "focus_id": focus_id,
                    "rarity": tmpl.rarity,
                },
            )
            self._active_summons[summon_id] = summon
            bucket = self._summoner_summons.setdefault(summoner_id, [])
            bucket.append(summon_id)
            _evict_fifo_list(bucket, _MAX_ACTIVE_SUMMONS)

            contract.summon_count += 1
            self._stats.total_summons_performed += 1
            self._emit(SummoningEventKind.SUMMON_PERFORMED.value,
                       {"summon_id": summon_id,
                        "template_id": tmpl.template_id,
                        "power": power,
                        "mana_cost": mana_cost},
                       summon_id=summon_id, contract_id=contract_id,
                       summoner_id=summoner_id,
                       template_id=tmpl.template_id,
                       ritual_id=ritual_id, focus_id=focus_id,
                       description=f"Summoned {tmpl.name}")
            self._update_stats()
            return True, "summoned", summon

    def banish_summon(self, summon_id: str) -> Tuple[bool, str, Optional[ActiveSummon]]:
        with _LOCK:
            summon = self._active_summons.get(summon_id)
            if summon is None:
                return False, "summon_not_found", None
            if summon.state == SummonState.BANISHED.value:
                return False, "already_banished", summon
            summon.state = SummonState.BANISHED.value
            self._stats.total_summons_banished += 1
            self._emit(SummoningEventKind.SUMMON_BANISHED.value,
                       {"summon_id": summon_id},
                       summon_id=summon_id,
                       summoner_id=summon.summoner_id,
                       contract_id=summon.contract_id)
            self._update_stats()
            return True, "banished", summon

    def get_active_summon(self, summon_id: str) -> Optional[ActiveSummon]:
        with _LOCK:
            return self._active_summons.get(summon_id)

    def list_active_summons(self, summoner_id: str = "",
                            state: str = "") -> List[ActiveSummon]:
        with _LOCK:
            results = list(self._active_summons.values())
            if summoner_id:
                results = [s for s in results if s.summoner_id == summoner_id]
            if state:
                results = [s for s in results if s.state == state]
            return results

    # ------------------------------------------------------------------
    # Power & Abilities
    # ------------------------------------------------------------------

    def calculate_summon_power(self, summon_id: str) -> Optional[float]:
        with _LOCK:
            summon = self._active_summons.get(summon_id)
            if summon is None:
                return None
            # Recompute live power accounting for current health ratio
            health_ratio = 1.0
            if summon.max_health > 0.0:
                health_ratio = _clamp(
                    summon.current_health / summon.max_health, 0.0, 1.0
                )
            live_power = summon.power * (0.5 + 0.5 * health_ratio)
            return round(live_power, 1)

    def get_summon_abilities(self, summon_id: str) -> List[str]:
        with _LOCK:
            summon = self._active_summons.get(summon_id)
            if summon is None:
                return []
            return list(summon.abilities)

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            power_decay = self._config.power_decay_per_hour * (dt / 3600.0)
            now = _now()
            expired_summons: List[str] = []
            for summon in self._active_summons.values():
                if summon.state != SummonState.SUMMONED.value:
                    continue
                # Expire summons whose duration has elapsed
                if summon.expires_at > 0.0 and now >= summon.expires_at:
                    summon.state = SummonState.RESTING.value
                    expired_summons.append(summon.summon_id)
                    continue
                # Gradual power decay over time
                if summon.power > 0.0:
                    summon.power = round(
                        max(0.0, summon.power - power_decay), 1
                    )
            for sid in expired_summons:
                self._emit(SummoningEventKind.SUMMON_DEFEATED.value,
                           {"summon_id": sid, "reason": "expired"},
                           summon_id=sid)
                self._stats.total_defeated += 1
            # Expire contracts whose timer has elapsed
            expired_contracts: List[str] = []
            for contract in self._contracts.values():
                if contract.status != ContractStatus.ACTIVE.value:
                    continue
                if contract.expires_at > 0.0 and now >= contract.expires_at:
                    contract.status = ContractStatus.EXPIRED.value
                    expired_contracts.append(contract.contract_id)
            for cid in expired_contracts:
                self._emit(SummoningEventKind.CONTRACT_EXPIRED.value,
                           {"contract_id": cid}, contract_id=cid)
            if self._tick_count % 60 == 0:
                self._emit(SummoningEventKind.TICK.value,
                           {"tick": self._tick_count, "dt": dt,
                            "expired_summons": len(expired_summons),
                            "expired_contracts": len(expired_contracts)})
            self._update_stats()
            return {
                "tick_count": self._tick_count,
                "expired_summons": len(expired_summons),
                "expired_contracts": len(expired_contracts),
            }

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, SummoningConfig]:
        with _LOCK:
            changed = []
            for k, v in config.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._emit(SummoningEventKind.CONFIG_UPDATED.value,
                           {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> SummoningConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[SummoningEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> SummoningStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_templates": len(self._templates),
                "total_rituals": len(self._rituals),
                "total_focuses": len(self._focuses),
                "total_contracts": len(self._contracts),
                "total_active_summons": len(self._active_summons),
                "total_summons_performed": self._stats.total_summons_performed,
                "total_summons_banished": self._stats.total_summons_banished,
                "total_contracts_broken": self._stats.total_contracts_broken,
                "total_defeated": self._stats.total_defeated,
                "total_focuses_broken": self._stats.total_focuses_broken,
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> SummoningSnapshot:
        with _LOCK:
            return SummoningSnapshot(
                templates=[t.to_dict() for t in list(self._templates.values())[:20]],
                rituals=[r.to_dict() for r in list(self._rituals.values())[:20]],
                focuses=[f.to_dict() for f in list(self._focuses.values())[:20]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> None:
        with _LOCK:
            self._templates.clear()
            self._rituals.clear()
            self._focuses.clear()
            self._contracts.clear()
            self._active_summons.clear()
            self._summoner_summons.clear()
            self._events.clear()
            self._stats = SummoningStats()
            self._config = SummoningConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._emit(SummoningEventKind.RESET.value, {})
            self._seed()


def get_summoning_conjuration_system() -> SummoningConjurationSystem:
    """Factory that returns the singleton SummoningConjurationSystem instance."""
    return SummoningConjurationSystem.get_instance()
