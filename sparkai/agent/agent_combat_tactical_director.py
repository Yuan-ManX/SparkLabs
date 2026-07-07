"""
SparkLabs Agent - Combat Tactical Director

A combat and tactical orchestration agent for the SparkLabs AI-native
game engine. It choreographs boss encounters, tunes NPC combat
behaviors, designs combo systems, balances PvP engagements, and
coordinates encounter difficulty in real time. The director fuses
ability design, threat modeling, and arena choreography to produce
memorable, fair, and replayable combat encounters.

Architecture:
  CombatTacticalDirector (singleton)
    |-- Ability, Encounter, ComboChain, ThreatProfile, ArenaZone,
       CombatStats, CombatSnapshot, CombatEvent
    |-- AbilityType, EncounterRole, CombatPhase, ThreatStance,
       DifficultyTier, CombatEventKind

Core Capabilities:
  - register_ability / get_ability / list_abilities / update_ability /
    remove_ability: ability lifecycle with type, damage, cooldown, and tags.
  - register_encounter / get_encounter / list_encounters / update_encounter:
    encounter lifecycle with phase graph, participants, and rewards.
  - add_combo_link / get_combo_chain / list_combo_chains / remove_combo:
    combo chain composition with branching ability links.
  - register_threat_profile / get_threat_profile / list_threat_profiles:
    threat weighting profiles that drive NPC target selection.
  - register_arena_zone / get_arena_zone / list_arena_zones: spatial
    partitioning of an arena with hazard and cover metadata.
  - advance_encounter / set_encounter_phase: encounter phase machine
    control that triggers ability rotations and adds.
  - assess_balance / generate_tactics: balance scoring and tactic
    generation for an encounter.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CombatTacticalDirector.get_instance` or the module-level
:func:`get_combat_tactical_director` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_ABILITIES: int = 5000
_MAX_ENCOUNTERS: int = 1000
_MAX_COMBO_CHAINS: int = 2000
_MAX_THREAT_PROFILES: int = 500
_MAX_ARENA_ZONES: int = 2000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class AbilityType(Enum):
    """Functional classification of combat abilities."""
    AUTO_ATTACK = "auto_attack"
    SKILL = "skill"
    ULTIMATE = "ultimate"
    DEFENSIVE = "defensive"
    UTILITY = "utility"
    CROWD_CONTROL = "crowd_control"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    SUMMON = "summon"


class EncounterRole(Enum):
    """Role of a participant within an encounter."""
    TANK = "tank"
    HEALER = "healer"
    DPS = "dps"
    SUPPORT = "support"
    BOSS = "boss"
    ADD = "add"
    ELITE = "elite"
    OBJECT = "object"


class CombatPhase(Enum):
    """Phases of a multi-phase encounter."""
    INTRO = "intro"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    TRANSITION = "transition"
    ENRAGE = "enrage"
    DEFEAT = "defeat"
    VICTORY = "victory"


class ThreatStance(Enum):
    """Stance that controls how threat is generated and decayed."""
    PASSIVE = "passive"
    NORMAL = "normal"
    AGGRESSIVE = "aggressive"
    FOCUSED = "focused"
    TAUNT = "taunt"


class DifficultyTier(Enum):
    """Difficulty tier that scales encounter parameters."""
    STORY = "story"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"
    MASTER = "master"
    NIGHTMARE = "nightmare"


class CombatEventKind(Enum):
    """Audit event types emitted by the combat director."""
    ABILITY_REGISTERED = "ability_registered"
    ABILITY_UPDATED = "ability_updated"
    ABILITY_REMOVED = "ability_removed"
    ENCOUNTER_REGISTERED = "encounter_registered"
    ENCOUNTER_UPDATED = "encounter_updated"
    ENCOUNTER_PHASE_CHANGED = "encounter_phase_changed"
    COMBO_LINKED = "combo_linked"
    COMBO_REMOVED = "combo_removed"
    THREAT_PROFILE_REGISTERED = "threat_profile_registered"
    ARENA_ZONE_REGISTERED = "arena_zone_registered"
    TACTICS_GENERATED = "tactics_generated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Ability:
    """A combat ability with damage, cooldown, and effects."""
    ability_id: str = field(default_factory=lambda: _new_id("abl"))
    name: str = ""
    ability_type: str = AbilityType.SKILL.value
    damage_min: float = 0.0
    damage_max: float = 0.0
    cooldown_ms: int = 0
    cast_time_ms: int = 0
    range_m: float = 5.0
    radius_m: float = 0.0
    resource_cost: int = 0
    resource_type: str = "mana"
    tags: List[str] = field(default_factory=list)
    effects: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Encounter:
    """A scripted combat encounter with phases and participants."""
    encounter_id: str = field(default_factory=lambda: _new_id("enc"))
    name: str = ""
    description: str = ""
    difficulty: str = DifficultyTier.NORMAL.value
    current_phase: str = CombatPhase.INTRO.value
    phase_order: List[str] = field(default_factory=list)
    participant_roles: Dict[str, str] = field(default_factory=dict)
    ability_rotation: List[str] = field(default_factory=list)
    enrage_timer_ms: int = 0
    reward_table: Dict[str, Any] = field(default_factory=dict)
    arena_zone_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ComboChain:
    """A branching combo chain linking abilities together."""
    combo_id: str = field(default_factory=lambda: _new_id("cmb"))
    name: str = ""
    ability_links: List[Dict[str, Any]] = field(default_factory=list)
    total_damage_min: float = 0.0
    total_damage_max: float = 0.0
    total_duration_ms: int = 0
    difficulty_rating: float = 0.5
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ThreatProfile:
    """A threat weighting profile for NPC target selection."""
    profile_id: str = field(default_factory=lambda: _new_id("thr"))
    name: str = ""
    stance: str = ThreatStance.NORMAL.value
    base_threat_per_second: float = 10.0
    threat_multipliers: Dict[str, float] = field(default_factory=dict)
    decay_rate: float = 0.1
    description: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaZone:
    """A spatial partition of an arena with hazards and cover."""
    zone_id: str = field(default_factory=lambda: _new_id("zn"))
    name: str = ""
    arena_id: str = ""
    bounds: Dict[str, Any] = field(default_factory=dict)
    hazard_type: str = ""
    hazard_damage_per_second: float = 0.0
    cover_rating: float = 0.0
    los_blocked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CombatStats:
    """Aggregate counters for the combat director."""
    total_abilities: int = 0
    total_encounters: int = 0
    total_combo_chains: int = 0
    total_threat_profiles: int = 0
    total_arena_zones: int = 0
    total_tactics_generated: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CombatSnapshot:
    """Immutable point-in-time capture of combat state."""
    abilities: Dict[str, Any] = field(default_factory=dict)
    encounters: Dict[str, Any] = field(default_factory=dict)
    combo_chains: Dict[str, Any] = field(default_factory=dict)
    threat_profiles: Dict[str, Any] = field(default_factory=dict)
    arena_zones: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CombatEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = CombatEventKind.ABILITY_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Combat Tactical Director Singleton
# ---------------------------------------------------------------------------


class CombatTacticalDirector:
    """Singleton agent that orchestrates combat encounters and tactics.

    The director maintains ability definitions, encounter scripts, combo
    chains, threat profiles, and arena zones. It advances encounter
    phases, generates tactical recommendations, and assesses balance
    for fair, challenging combat.
    """

    _instance: Optional["CombatTacticalDirector"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._abilities: Dict[str, Ability] = {}
        self._encounters: Dict[str, Encounter] = {}
        self._combos: Dict[str, ComboChain] = {}
        self._threat_profiles: Dict[str, ThreatProfile] = {}
        self._arena_zones: Dict[str, ArenaZone] = {}
        self._tactics_generated: int = 0
        self._audit: List[CombatEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CombatTacticalDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_default_data()
            self._initialized = True

    def _seed_default_data(self) -> None:
        """Seed starter abilities, an encounter, and a threat profile."""
        # Default abilities
        for name, atype, dmin, dmax, cd, rt in [
            ("Slash", AbilityType.AUTO_ATTACK.value, 10, 15, 1000, ""),
            ("Power Strike", AbilityType.SKILL.value, 30, 40, 5000, ""),
            ("Heal", AbilityType.HEAL.value, 0, 0, 8000, ""),
            ("Taunt", AbilityType.UTILITY.value, 0, 0, 6000, ""),
            ("Whirlwind", AbilityType.ULTIMATE.value, 60, 90, 30000, ""),
        ]:
            self.register_ability(
                name=name, ability_type=atype,
                damage_min=dmin, damage_max=dmax,
                cooldown_ms=cd, resource_type=rt or "mana",
            )
        # Default threat profile
        self.register_threat_profile(
            name="Standard Tank Profile",
            stance=ThreatStance.AGGRESSIVE.value,
            base_threat_per_second=15.0,
            threat_multipliers={"heal": 1.5, "damage": 1.0, "taunt": 5.0},
        )

    def _emit_event(self, kind: CombatEventKind, payload: Dict[str, Any]) -> None:
        evt = CombatEvent(kind=kind.value, payload=payload)
        self._audit.append(evt)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Ability Lifecycle
    # ------------------------------------------------------------------

    def register_ability(self, ability_id: str = "", name: str = "",
                         ability_type: Any = AbilityType.SKILL.value,
                         damage_min: float = 0.0, damage_max: float = 0.0,
                         cooldown_ms: int = 0, cast_time_ms: int = 0,
                         range_m: float = 5.0, radius_m: float = 0.0,
                         resource_cost: int = 0, resource_type: str = "mana",
                         tags: List[str] = None,
                         effects: Dict[str, Any] = None,
                         description: str = "") -> Ability:
        with self._lock:
            aid = ability_id or _new_id("abl")
            type_val = self._coerce_ability_type(ability_type).value
            ability = Ability(
                ability_id=aid,
                name=name,
                ability_type=type_val,
                damage_min=max(0.0, _safe_float(damage_min, 0.0)),
                damage_max=max(0.0, _safe_float(damage_max, 0.0)),
                cooldown_ms=max(0, _safe_int(cooldown_ms, 0)),
                cast_time_ms=max(0, _safe_int(cast_time_ms, 0)),
                range_m=max(0.0, _safe_float(range_m, 5.0)),
                radius_m=max(0.0, _safe_float(radius_m, 0.0)),
                resource_cost=max(0, _safe_int(resource_cost, 0)),
                resource_type=resource_type,
                tags=list(tags) if tags else [],
                effects=dict(effects) if effects else {},
                description=description,
            )
            self._abilities[aid] = ability
            _evict_fifo_dict(self._abilities, _MAX_ABILITIES)
            self._emit_event(CombatEventKind.ABILITY_REGISTERED, {
                "ability_id": aid, "name": name, "type": type_val,
            })
            return ability

    def get_ability(self, ability_id: str) -> Optional[Ability]:
        with self._lock:
            return self._abilities.get(ability_id)

    def list_abilities(self, ability_type: Any = None, limit: int = 100) -> List[Ability]:
        with self._lock:
            items = list(self._abilities.values())
            if ability_type is not None and ability_type != "":
                type_val = self._coerce_ability_type(ability_type).value
                items = [a for a in items if a.ability_type == type_val]
            return items[-limit:]

    def update_ability(self, ability_id: str, **kwargs: Any) -> Optional[Ability]:
        with self._lock:
            ability = self._abilities.get(ability_id)
            if ability is None:
                return None
            for key in ("name", "ability_type", "damage_min", "damage_max",
                        "cooldown_ms", "cast_time_ms", "range_m", "radius_m",
                        "resource_cost", "resource_type", "tags", "effects",
                        "description"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "ability_type":
                        val = self._coerce_ability_type(val).value
                    elif key in ("damage_min", "damage_max", "range_m", "radius_m"):
                        val = max(0.0, _safe_float(val, getattr(ability, key)))
                    elif key in ("cooldown_ms", "cast_time_ms", "resource_cost"):
                        val = max(0, _safe_int(val, getattr(ability, key)))
                    elif key == "tags":
                        val = list(val) if val else []
                    elif key == "effects":
                        val = dict(val) if val else {}
                    setattr(ability, key, val)
            self._emit_event(CombatEventKind.ABILITY_UPDATED, {"ability_id": ability_id})
            return ability

    def remove_ability(self, ability_id: str) -> bool:
        with self._lock:
            existed = self._abilities.pop(ability_id, None) is not None
            if existed:
                self._emit_event(CombatEventKind.ABILITY_REMOVED, {"ability_id": ability_id})
            return existed

    # ------------------------------------------------------------------
    # Encounter Lifecycle
    # ------------------------------------------------------------------

    def register_encounter(self, encounter_id: str = "", name: str = "",
                           description: str = "",
                           difficulty: Any = DifficultyTier.NORMAL.value,
                           phase_order: List[str] = None,
                           participant_roles: Dict[str, str] = None,
                           ability_rotation: List[str] = None,
                           enrage_timer_ms: int = 0,
                           reward_table: Dict[str, Any] = None,
                           arena_zone_id: str = "",
                           metadata: Dict[str, Any] = None) -> Encounter:
        with self._lock:
            eid = encounter_id or _new_id("enc")
            diff_val = self._coerce_difficulty(difficulty).value
            phases = list(phase_order) if phase_order else [
                CombatPhase.INTRO.value, CombatPhase.PHASE_1.value,
                CombatPhase.PHASE_2.value, CombatPhase.VICTORY.value,
            ]
            encounter = Encounter(
                encounter_id=eid,
                name=name,
                description=description,
                difficulty=diff_val,
                current_phase=phases[0] if phases else CombatPhase.INTRO.value,
                phase_order=phases,
                participant_roles=dict(participant_roles) if participant_roles else {},
                ability_rotation=list(ability_rotation) if ability_rotation else [],
                enrage_timer_ms=max(0, _safe_int(enrage_timer_ms, 0)),
                reward_table=dict(reward_table) if reward_table else {},
                arena_zone_id=arena_zone_id,
                metadata=dict(metadata) if metadata else {},
            )
            self._encounters[eid] = encounter
            _evict_fifo_dict(self._encounters, _MAX_ENCOUNTERS)
            self._emit_event(CombatEventKind.ENCOUNTER_REGISTERED, {
                "encounter_id": eid, "name": name,
            })
            return encounter

    def get_encounter(self, encounter_id: str) -> Optional[Encounter]:
        with self._lock:
            return self._encounters.get(encounter_id)

    def list_encounters(self, difficulty: Any = None, limit: int = 100) -> List[Encounter]:
        with self._lock:
            items = list(self._encounters.values())
            if difficulty is not None and difficulty != "":
                diff_val = self._coerce_difficulty(difficulty).value
                items = [e for e in items if e.difficulty == diff_val]
            return items[-limit:]

    def update_encounter(self, encounter_id: str, **kwargs: Any) -> Optional[Encounter]:
        with self._lock:
            encounter = self._encounters.get(encounter_id)
            if encounter is None:
                return None
            for key in ("name", "description", "difficulty", "current_phase",
                        "phase_order", "participant_roles", "ability_rotation",
                        "enrage_timer_ms", "reward_table", "arena_zone_id", "metadata"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "difficulty":
                        val = self._coerce_difficulty(val).value
                    elif key == "current_phase":
                        val = self._coerce_phase(val).value
                    elif key == "phase_order":
                        val = list(val) if val else []
                    elif key == "participant_roles":
                        val = dict(val) if val else {}
                    elif key == "ability_rotation":
                        val = list(val) if val else []
                    elif key == "enrage_timer_ms":
                        val = max(0, _safe_int(val, getattr(encounter, key)))
                    elif key == "reward_table":
                        val = dict(val) if val else {}
                    elif key == "metadata":
                        val = dict(val) if val else {}
                    setattr(encounter, key, val)
            self._emit_event(CombatEventKind.ENCOUNTER_UPDATED, {"encounter_id": encounter_id})
            return encounter

    def set_encounter_phase(self, encounter_id: str, phase: Any) -> Optional[Encounter]:
        with self._lock:
            encounter = self._encounters.get(encounter_id)
            if encounter is None:
                return None
            phase_val = self._coerce_phase(phase).value
            encounter.current_phase = phase_val
            self._emit_event(CombatEventKind.ENCOUNTER_PHASE_CHANGED, {
                "encounter_id": encounter_id, "phase": phase_val,
            })
            return encounter

    def advance_encounter(self, encounter_id: str) -> Optional[Encounter]:
        with self._lock:
            encounter = self._encounters.get(encounter_id)
            if encounter is None:
                return None
            current = encounter.current_phase
            try:
                idx = encounter.phase_order.index(current)
            except ValueError:
                idx = -1
            if idx >= 0 and idx < len(encounter.phase_order) - 1:
                encounter.current_phase = encounter.phase_order[idx + 1]
                self._emit_event(CombatEventKind.ENCOUNTER_PHASE_CHANGED, {
                    "encounter_id": encounter_id,
                    "phase": encounter.current_phase,
                })
            return encounter

    # ------------------------------------------------------------------
    # Combo Chain Management
    # ------------------------------------------------------------------

    def add_combo_link(self, name: str = "",
                       ability_links: List[Dict[str, Any]] = None,
                       combo_id: str = "",
                       tags: List[str] = None) -> Optional[ComboChain]:
        with self._lock:
            cid = combo_id or _new_id("cmb")
            links = list(ability_links) if ability_links else []
            # Validate each ability_id exists
            validated_links: List[Dict[str, Any]] = []
            total_dmg_min = 0.0
            total_dmg_max = 0.0
            total_dur = 0
            for link in links:
                aid = link.get("ability_id", "")
                if aid and aid in self._abilities:
                    ability = self._abilities[aid]
                    total_dmg_min += ability.damage_min
                    total_dmg_max += ability.damage_max
                    total_dur += ability.cast_time_ms + ability.cooldown_ms
                    validated_links.append({
                        "ability_id": aid,
                        "branch": link.get("branch", "main"),
                        "condition": link.get("condition", ""),
                    })
            combo = ComboChain(
                combo_id=cid,
                name=name,
                ability_links=validated_links,
                total_damage_min=round(total_dmg_min, 4),
                total_damage_max=round(total_dmg_max, 4),
                total_duration_ms=total_dur,
                difficulty_rating=_clamp(len(validated_links) / 10.0),
                tags=list(tags) if tags else [],
            )
            self._combos[cid] = combo
            _evict_fifo_dict(self._combos, _MAX_COMBO_CHAINS)
            self._emit_event(CombatEventKind.COMBO_LINKED, {
                "combo_id": cid, "link_count": len(validated_links),
            })
            return combo

    def get_combo_chain(self, combo_id: str) -> Optional[ComboChain]:
        with self._lock:
            return self._combos.get(combo_id)

    def list_combo_chains(self, limit: int = 100) -> List[ComboChain]:
        with self._lock:
            return list(self._combos.values())[-limit:]

    def remove_combo(self, combo_id: str) -> bool:
        with self._lock:
            existed = self._combos.pop(combo_id, None) is not None
            if existed:
                self._emit_event(CombatEventKind.COMBO_REMOVED, {"combo_id": combo_id})
            return existed

    # ------------------------------------------------------------------
    # Threat Profile Management
    # ------------------------------------------------------------------

    def register_threat_profile(self, profile_id: str = "", name: str = "",
                                stance: Any = ThreatStance.NORMAL.value,
                                base_threat_per_second: float = 10.0,
                                threat_multipliers: Dict[str, float] = None,
                                decay_rate: float = 0.1,
                                description: str = "") -> ThreatProfile:
        with self._lock:
            pid = profile_id or _new_id("thr")
            stance_val = self._coerce_stance(stance).value
            profile = ThreatProfile(
                profile_id=pid,
                name=name,
                stance=stance_val,
                base_threat_per_second=max(0.0, _safe_float(base_threat_per_second, 10.0)),
                threat_multipliers={str(k): _safe_float(v, 1.0)
                                     for k, v in (threat_multipliers or {}).items()},
                decay_rate=_clamp(_safe_float(decay_rate, 0.1)),
                description=description,
            )
            self._threat_profiles[pid] = profile
            _evict_fifo_dict(self._threat_profiles, _MAX_THREAT_PROFILES)
            self._emit_event(CombatEventKind.THREAT_PROFILE_REGISTERED, {
                "profile_id": pid, "name": name,
            })
            return profile

    def get_threat_profile(self, profile_id: str) -> Optional[ThreatProfile]:
        with self._lock:
            return self._threat_profiles.get(profile_id)

    def list_threat_profiles(self, stance: Any = None,
                              limit: int = 100) -> List[ThreatProfile]:
        with self._lock:
            items = list(self._threat_profiles.values())
            if stance is not None and stance != "":
                stance_val = self._coerce_stance(stance).value
                items = [p for p in items if p.stance == stance_val]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Arena Zone Management
    # ------------------------------------------------------------------

    def register_arena_zone(self, zone_id: str = "", name: str = "",
                            arena_id: str = "",
                            bounds: Dict[str, Any] = None,
                            hazard_type: str = "",
                            hazard_damage_per_second: float = 0.0,
                            cover_rating: float = 0.0,
                            los_blocked: bool = False,
                            metadata: Dict[str, Any] = None) -> ArenaZone:
        with self._lock:
            zid = zone_id or _new_id("zn")
            zone = ArenaZone(
                zone_id=zid,
                name=name,
                arena_id=arena_id,
                bounds=dict(bounds) if bounds else {},
                hazard_type=hazard_type,
                hazard_damage_per_second=max(0.0, _safe_float(hazard_damage_per_second, 0.0)),
                cover_rating=_clamp(_safe_float(cover_rating, 0.0)),
                los_blocked=bool(los_blocked),
                metadata=dict(metadata) if metadata else {},
            )
            self._arena_zones[zid] = zone
            _evict_fifo_dict(self._arena_zones, _MAX_ARENA_ZONES)
            self._emit_event(CombatEventKind.ARENA_ZONE_REGISTERED, {
                "zone_id": zid, "name": name,
            })
            return zone

    def get_arena_zone(self, zone_id: str) -> Optional[ArenaZone]:
        with self._lock:
            return self._arena_zones.get(zone_id)

    def list_arena_zones(self, arena_id: str = "", limit: int = 100) -> List[ArenaZone]:
        with self._lock:
            items = list(self._arena_zones.values())
            if arena_id:
                items = [z for z in items if z.arena_id == arena_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Tactics Generation & Balance Assessment
    # ------------------------------------------------------------------

    def assess_balance(self, encounter_id: str) -> Dict[str, Any]:
        with self._lock:
            encounter = self._encounters.get(encounter_id)
            if encounter is None:
                return {}
            # Compute aggregate stats for the encounter's ability rotation
            total_dmg_min = 0.0
            total_dmg_max = 0.0
            total_cd = 0
            ability_count = 0
            for aid in encounter.ability_rotation:
                ability = self._abilities.get(aid)
                if ability:
                    total_dmg_min += ability.damage_min
                    total_dmg_max += ability.damage_max
                    total_cd += ability.cooldown_ms
                    ability_count += 1
            avg_dps = 0.0
            if total_cd > 0:
                avg_dps = (total_dmg_min + total_dmg_max) / 2.0 / (total_cd / 1000.0)
            # Difficulty scaling factor
            diff_mult = {
                DifficultyTier.STORY.value: 0.5,
                DifficultyTier.NORMAL.value: 1.0,
                DifficultyTier.HARD.value: 1.5,
                DifficultyTier.EXPERT.value: 2.0,
                DifficultyTier.MASTER.value: 2.5,
                DifficultyTier.NIGHTMARE.value: 3.0,
            }.get(encounter.difficulty, 1.0)
            scaled_dps = avg_dps * diff_mult
            # Balance score: 1.0 is perfectly balanced, >1 means too hard, <1 too easy
            balance_score = _clamp(scaled_dps / 100.0, 0.0, 2.0)
            return {
                "encounter_id": encounter_id,
                "ability_count": ability_count,
                "total_damage_min": round(total_dmg_min, 4),
                "total_damage_max": round(total_dmg_max, 4),
                "avg_dps": round(avg_dps, 4),
                "difficulty_multiplier": diff_mult,
                "scaled_dps": round(scaled_dps, 4),
                "balance_score": round(balance_score, 4),
                "assessment": "balanced" if 0.7 <= balance_score <= 1.3
                              else ("too_hard" if balance_score > 1.3 else "too_easy"),
            }

    def generate_tactics(self, encounter_id: str) -> List[Dict[str, Any]]:
        with self._lock:
            encounter = self._encounters.get(encounter_id)
            if encounter is None:
                return []
            balance = self.assess_balance(encounter_id)
            tactics: List[Dict[str, Any]] = []
            assessment = balance.get("assessment", "balanced")
            # Generate role-based tactics
            for participant, role in encounter.participant_roles.items():
                tactic: Dict[str, Any] = {
                    "participant": participant,
                    "role": role,
                    "priority": "normal",
                    "directives": [],
                }
                if role == EncounterRole.TANK.value:
                    tactic["directives"] = [
                        "Maintain aggro on the primary target",
                        "Use defensive cooldowns during enrage",
                    ]
                    if assessment == "too_hard":
                        tactic["priority"] = "critical"
                        tactic["directives"].append("Prioritize mitigation over threat")
                elif role == EncounterRole.HEALER.value:
                    tactic["directives"] = [
                        "Focus healing on the tank",
                        "Save cooldowns for phase transitions",
                    ]
                    if assessment == "too_hard":
                        tactic["priority"] = "critical"
                        tactic["directives"].append("Use AoE heals during high-damage phases")
                elif role == EncounterRole.DPS.value:
                    tactic["directives"] = [
                        "Execute ability rotation optimally",
                        "Avoid hazardous arena zones",
                    ]
                    if assessment == "too_easy":
                        tactic["priority"] = "high"
                        tactic["directives"].append("Push damage to meet enrage timer")
                elif role == EncounterRole.BOSS.value:
                    tactic["directives"] = [
                        f"Phase: {encounter.current_phase}",
                        f"Difficulty: {encounter.difficulty}",
                    ]
                tactics.append(tactic)
            self._tactics_generated += 1
            self._emit_event(CombatEventKind.TACTICS_GENERATED, {
                "encounter_id": encounter_id,
                "tactic_count": len(tactics),
            })
            return tactics

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_ability_type(value: Any) -> AbilityType:
        if isinstance(value, AbilityType):
            return value
        if isinstance(value, str):
            for at in AbilityType:
                if at.value == value:
                    return at
        return AbilityType.SKILL

    @staticmethod
    def _coerce_difficulty(value: Any) -> DifficultyTier:
        if isinstance(value, DifficultyTier):
            return value
        if isinstance(value, str):
            for dt in DifficultyTier:
                if dt.value == value:
                    return dt
        return DifficultyTier.NORMAL

    @staticmethod
    def _coerce_phase(value: Any) -> CombatPhase:
        if isinstance(value, CombatPhase):
            return value
        if isinstance(value, str):
            for ph in CombatPhase:
                if ph.value == value:
                    return ph
        return CombatPhase.INTRO

    @staticmethod
    def _coerce_stance(value: Any) -> ThreatStance:
        if isinstance(value, ThreatStance):
            return value
        if isinstance(value, str):
            for st in ThreatStance:
                if st.value == value:
                    return st
        return ThreatStance.NORMAL

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[CombatEvent]:
        with self._lock:
            return list(self._audit[-limit:])

    def get_stats(self) -> CombatStats:
        with self._lock:
            return CombatStats(
                total_abilities=len(self._abilities),
                total_encounters=len(self._encounters),
                total_combo_chains=len(self._combos),
                total_threat_profiles=len(self._threat_profiles),
                total_arena_zones=len(self._arena_zones),
                total_tactics_generated=self._tactics_generated,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "abilities": len(self._abilities),
                "encounters": len(self._encounters),
                "combo_chains": len(self._combos),
                "threat_profiles": len(self._threat_profiles),
                "arena_zones": len(self._arena_zones),
                "tactics_generated": self._tactics_generated,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> CombatSnapshot:
        with self._lock:
            return CombatSnapshot(
                abilities={k: v.to_dict() for k, v in self._abilities.items()},
                encounters={k: v.to_dict() for k, v in self._encounters.items()},
                combo_chains={k: v.to_dict() for k, v in self._combos.items()},
                threat_profiles={k: v.to_dict() for k, v in self._threat_profiles.items()},
                arena_zones={k: v.to_dict() for k, v in self._arena_zones.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._abilities.clear()
            self._encounters.clear()
            self._combos.clear()
            self._threat_profiles.clear()
            self._arena_zones.clear()
            self._tactics_generated = 0
            self._audit.clear()
            self._initialized = False
            self._initialize()


def get_combat_tactical_director() -> CombatTacticalDirector:
    """Module-level factory for the CombatTacticalDirector singleton."""
    return CombatTacticalDirector.get_instance()
