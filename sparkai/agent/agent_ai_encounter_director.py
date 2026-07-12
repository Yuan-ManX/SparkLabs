"""
SparkLabs Agent - AI Encounter Director

A runtime fusion module that designs and orchestrates dynamic boss fights,
combat scenarios, and adaptive encounters for the SparkLabs AI-native game
engine. The director treats every encounter as a living system: reusable
templates are assembled from multi-phase scripts and individual boss
mechanics, then instantiated into live encounters that track player state,
phase transitions, mechanic triggers, wipes, and rewards.

This module embodies the AI-native principle: an encounter is not a static
script but an adaptive construction that scales to party composition and
skill, reacts to player performance in real time, and records a full event
timeline that can be replayed, audited, and tuned.

Architecture:
  AIEncounterDirector (singleton)
    |-- BossMechanic, EncounterPhase, EncounterTemplate, EncounterInstance,
        AdaptiveScaling, RewardEntry, RewardTable, EncounterEvent,
        EncounterConfig, EncounterStats, EncounterSnapshot
    |-- EncounterType, EncounterPhaseType, MechanicType, EncounterStatus,
        DifficultyTier, RewardRarity

Core Capabilities:
  - register_mechanic / get_mechanic / list_mechanics / remove_mechanic:
    individual boss mechanic library management (dodge, telegraph, adds,
    shields, enrage, tank swaps, heal checks, chained abilities).
  - register_phase / get_phase / list_phases / remove_phase: multi-phase
    encounter script assembly with HP thresholds and enrage timers.
  - register_template / get_template / list_templates / remove_template:
    reusable encounter templates binding bosses, phases, mechanics, arenas,
    and reward tables together.
  - create_encounter / get_encounter / list_encounters / advance_phase /
    trigger_mechanic / deal_boss_damage / player_downed / player_revived /
    complete_encounter / wipe_encounter: live encounter lifecycle control.
  - calculate_adaptive_scaling: dynamic difficulty scaling derived from
    party size, average item level, and average skill score.
  - register_reward_table / get_reward_table / list_reward_tables /
    roll_rewards / remove_reward_table: loot table management and
    luck-modified reward rolling.
  - list_events / get_stats / get_status / get_snapshot / set_config /
    get_config / tick / reset: observability, tuning, and state management.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_MECHANICS: int = 2000
_MAX_PHASES: int = 4000
_MAX_TEMPLATES: int = 1000
_MAX_INSTANCES: int = 500
_MAX_SCALINGS: int = 2000
_MAX_REWARD_TABLES: int = 1000
_MAX_REWARD_ENTRIES_PER_TABLE: int = 200
_MAX_EVENTS: int = 8000


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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    """Best-effort conversion of a raw value into an enum member."""
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    # Check for dataclass fields BEFORE falling back to to_dict so that
    # nested dataclasses are unfolded without re-entering to_dict.
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """
    Convert a dataclass instance into a JSON-friendly dict.

    The __dataclass_fields__ attribute is inspected BEFORE any to_dict
    fallback so that a dataclass whose to_dict() calls _dataclass_to_dict
    cannot enter an infinite recursion loop.
    """
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class EncounterType(str, Enum):
    """High-level category of an encounter."""
    BOSS = "boss"
    MINIBOSS = "miniboss"
    ELITE_PACK = "elite_pack"
    AMBUSH = "ambush"
    GAUNTLET = "gauntlet"
    RITUAL = "ritual"
    SIEGE = "siege"
    CHASE = "chase"
    PUZZLE_COMBAT = "puzzle_combat"
    SURVIVAL = "survival"


class EncounterPhaseType(str, Enum):
    """Role a phase plays inside a multi-phase encounter script."""
    INTRO = "intro"
    PHASE_ONE = "phase_one"
    TRANSITION = "transition"
    PHASE_TWO = "phase_two"
    INTERMISSION = "intermission"
    PHASE_THREE = "phase_three"
    FINALE = "finale"
    ENRAGE = "enrage"


class MechanicType(str, Enum):
    """Concrete behaviour family for a boss mechanic."""
    AOE_DODGE = "aoe_dodge"
    TELEGRAPHED_STRIKE = "telegraphed_strike"
    ADD_SPAWNS = "add_spawns"
    SHIELD_MECHANIC = "shield_mechanic"
    ENRAGE_TIMER = "enrage_timer"
    POSITIONING = "positioning"
    RESOURCE_MGMT = "resource_mgmt"
    MECHANIC_COMBO = "mechanic_combo"
    TANK_SWAP = "tank_swap"
    HEAL_CHECK = "heal_check"
    DPS_CHECK = "dps_check"
    INTERRUPT_CAST = "interrupt_cast"
    LINE_OF_SIGHT = "line_of_sight"
    PLATFORMING = "platforming"


class EncounterStatus(str, Enum):
    """Lifecycle state of a live encounter instance."""
    DRAFT = "draft"
    ACTIVE = "active"
    PHASE_TRANSITION = "phase_transition"
    COMPLETED = "completed"
    WIPED = "wiped"
    ABANDONED = "abandoned"


class DifficultyTier(str, Enum):
    """Difficulty band that drives health, damage, and reward scaling."""
    STORY = "story"
    NORMAL = "normal"
    HARD = "hard"
    HEROIC = "heroic"
    MYTHIC = "mythic"
    LEGENDARY = "legendary"


class RewardRarity(str, Enum):
    """Rarity band for a reward entry."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class BossMechanic:
    """A single reusable boss mechanic with timing and counter-play data."""
    mechanic_id: str
    name: str
    mechanic_type: MechanicType
    description: str = ""
    telegraph_duration: float = 2.0
    active_duration: float = 1.0
    cooldown: float = 10.0
    damage_multiplier: float = 1.0
    target_type: str = "all"
    counter_strategy: str = ""
    is_avoidable: bool = True
    is_interruptible: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterPhase:
    """A single phase inside a multi-phase encounter script."""
    phase_id: str
    encounter_id: str
    phase_type: EncounterPhaseType
    name: str
    description: str = ""
    mechanic_ids: List[str] = field(default_factory=list)
    hp_threshold: float = 0.0
    enrage_timer: float = 0.0
    transition_message: str = ""
    is_final_phase: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterTemplate:
    """A reusable encounter blueprint binding boss, phases, and rewards."""
    template_id: str
    name: str
    encounter_type: EncounterType
    description: str = ""
    boss_name: str = ""
    boss_entity_id: str = ""
    boss_max_health: float = 100000.0
    boss_max_health_heroic: float = 250000.0
    phase_ids: List[str] = field(default_factory=list)
    base_mechanics: List[str] = field(default_factory=list)
    difficulty_tier: DifficultyTier = DifficultyTier.NORMAL
    arena_id: str = ""
    recommended_player_count: int = 5
    recommended_item_level: int = 0
    enrage_total_timer: float = 600.0
    reward_table_id: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterInstance:
    """A live encounter instantiated from a template."""
    instance_id: str
    template_id: str
    status: EncounterStatus
    current_phase_id: str = ""
    player_ids: List[str] = field(default_factory=list)
    start_time: str = field(default_factory=_now)
    phase_start_time: str = field(default_factory=_now)
    boss_current_health: float = 0.0
    players_alive: int = 0
    wipe_count: int = 0
    mechanic_triggers: int = 0
    completion_time: str = ""
    rewards_distributed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AdaptiveScaling:
    """Dynamic difficulty scaling derived from party metrics."""
    scaling_id: str
    encounter_id: str
    player_count: int
    avg_item_level: float
    avg_skill_score: float
    health_multiplier: float = 1.0
    damage_multiplier: float = 1.0
    mechanic_speed_multiplier: float = 1.0
    enrage_reduction: float = 0.0
    reward_bonus: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RewardEntry:
    """A single loot entry inside a reward table."""
    reward_id: str
    table_id: str
    item_id: str
    item_name: str
    rarity: RewardRarity
    drop_chance: float = 0.0
    quantity: int = 1
    is_guaranteed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RewardTable:
    """A loot table tied to an encounter type and difficulty tier."""
    table_id: str
    name: str
    encounter_type: EncounterType
    difficulty_tier: DifficultyTier
    entries: List[RewardEntry] = field(default_factory=list)
    currency_reward: int = 0
    experience_reward: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterEvent:
    """An audit event recorded on the encounter timeline."""
    event_id: str
    event_type: str
    timestamp: str
    encounter_id: str = ""
    phase_id: str = ""
    player_id: str = ""
    mechanic_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterConfig:
    """Global tuning parameters for the encounter director."""
    max_templates: int = 500
    max_instances: int = 200
    max_mechanics: int = 2000
    max_phases: int = 4000
    adaptive_scaling_enabled: bool = True
    wipe_recovery_time: float = 8.0
    enrage_default_timer: float = 600.0
    reward_roll_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterStats:
    """Aggregate counters describing director activity."""
    total_templates: int = 0
    total_instances: int = 0
    active_encounters: int = 0
    completed_encounters: int = 0
    wiped_encounters: int = 0
    total_mechanics: int = 0
    total_phases: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterSnapshot:
    """Full state snapshot for persistence and inspection."""
    timestamp: str = field(default_factory=_now)
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    templates: List[Dict[str, Any]] = field(default_factory=list)
    instances: List[Dict[str, Any]] = field(default_factory=list)
    reward_tables: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# AI Encounter Director Singleton
# ---------------------------------------------------------------------------


class AIEncounterDirector:
    """
    AI-native fusion module that designs and orchestrates adaptive combat
    encounters. The director owns the mechanic library, phase scripts,
    encounter templates, live instances, adaptive scaling calculations, and
    reward tables as a single coherent state machine.
    """

    _instance: Optional["AIEncounterDirector"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "AIEncounterDirector":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AIEncounterDirector":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._mechanics: Dict[str, BossMechanic] = {}
            self._phases: Dict[str, EncounterPhase] = {}
            self._templates: Dict[str, EncounterTemplate] = {}
            self._instances: Dict[str, EncounterInstance] = {}
            self._scalings: Dict[str, AdaptiveScaling] = {}
            self._reward_tables: Dict[str, RewardTable] = {}
            self._events: List[EncounterEvent] = []
            self._config = EncounterConfig()
            self._stats = EncounterStats()
            self._tick_count: int = 0
            self._seed()
            # _seed() sets self._initialized = True when it finishes.

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, data: Dict[str, Any],
              encounter_id: str = "", phase_id: str = "",
              player_id: str = "", mechanic_id: str = "") -> None:
        event = EncounterEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            encounter_id=encounter_id,
            phase_id=phase_id,
            player_id=player_id,
            mechanic_id=mechanic_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_templates = len(self._templates)
        self._stats.total_instances = len(self._instances)
        self._stats.active_encounters = sum(
            1 for i in self._instances.values()
            if i.status == EncounterStatus.ACTIVE
        )
        self._stats.completed_encounters = sum(
            1 for i in self._instances.values()
            if i.status == EncounterStatus.COMPLETED
        )
        self._stats.wiped_encounters = sum(
            1 for i in self._instances.values()
            if i.status == EncounterStatus.WIPED
        )
        self._stats.total_mechanics = len(self._mechanics)
        self._stats.total_phases = len(self._phases)
        self._stats.tick_count = self._tick_count

    def _complete_internal(self, inst: EncounterInstance) -> None:
        inst.status = EncounterStatus.COMPLETED
        inst.boss_current_health = 0.0
        inst.completion_time = _now()
        self._emit(
            "encounter_completed",
            {"instance_id": inst.instance_id, "template_id": inst.template_id},
            encounter_id=inst.instance_id,
        )

    def _wipe_internal(self, inst: EncounterInstance, reason: str) -> None:
        inst.status = EncounterStatus.WIPED
        inst.wipe_count += 1
        self._emit(
            "encounter_wiped",
            {"instance_id": inst.instance_id, "reason": reason},
            encounter_id=inst.instance_id,
        )

    def _check_phase_threshold(self, inst: EncounterInstance) -> None:
        """Auto-advance phases when boss health crosses HP thresholds."""
        tpl = self._templates.get(inst.template_id)
        if tpl is None or not tpl.phase_ids:
            return
        max_hp = inst.metadata.get("boss_max_health", tpl.boss_max_health)
        if max_hp <= 0:
            return
        try:
            idx = tpl.phase_ids.index(inst.current_phase_id)
        except ValueError:
            return
        while idx + 1 < len(tpl.phase_ids):
            next_phase_id = tpl.phase_ids[idx + 1]
            next_phase = self._phases.get(next_phase_id)
            threshold = next_phase.hp_threshold if next_phase else 0.0
            if threshold > 0.0 and inst.boss_current_health <= threshold * max_hp:
                inst.current_phase_id = next_phase_id
                inst.status = EncounterStatus.PHASE_TRANSITION
                inst.phase_start_time = _now()
                self._emit(
                    "phase_advanced",
                    {
                        "instance_id": inst.instance_id,
                        "phase_id": next_phase_id,
                        "reason": "hp_threshold",
                    },
                    encounter_id=inst.instance_id,
                    phase_id=next_phase_id,
                )
                idx += 1
            else:
                break

    # ------------------------------------------------------------------
    # Boss Mechanic Management
    # ------------------------------------------------------------------

    def register_mechanic(self, mechanic_id, name, mechanic_type,
                          description="", telegraph_duration=2.0,
                          active_duration=1.0, cooldown=10.0,
                          damage_multiplier=1.0, target_type="all",
                          counter_strategy="", is_avoidable=True,
                          is_interruptible=False,
                          metadata=None) -> Tuple[bool, str, Optional[BossMechanic]]:
        """Register a reusable boss mechanic in the director library."""
        with self._lock:
            if not mechanic_id:
                return False, "invalid_mechanic_id", None
            if mechanic_id in self._mechanics:
                return False, "mechanic_exists", None
            if len(self._mechanics) >= self._config.max_mechanics:
                return False, "mechanics_capacity", None
            mtype = _coerce_enum(MechanicType, mechanic_type, MechanicType.AOE_DODGE)
            mech = BossMechanic(
                mechanic_id=mechanic_id,
                name=name,
                mechanic_type=mtype,
                description=description,
                telegraph_duration=telegraph_duration,
                active_duration=active_duration,
                cooldown=cooldown,
                damage_multiplier=damage_multiplier,
                target_type=target_type,
                counter_strategy=counter_strategy,
                is_avoidable=is_avoidable,
                is_interruptible=is_interruptible,
                metadata=metadata or {},
            )
            self._mechanics[mechanic_id] = mech
            self._emit("mechanic_registered", {
                "mechanic_id": mechanic_id,
                "mechanic_type": mtype.value,
            }, mechanic_id=mechanic_id)
            return True, "registered", mech

    def get_mechanic(self, mechanic_id) -> Optional[BossMechanic]:
        with self._lock:
            return self._mechanics.get(mechanic_id)

    def list_mechanics(self, mechanic_type="") -> List[BossMechanic]:
        with self._lock:
            items = list(self._mechanics.values())
            if mechanic_type:
                mt = _coerce_enum(MechanicType, mechanic_type)
                if mt is not None:
                    items = [m for m in items if m.mechanic_type == mt]
                else:
                    items = [
                        m for m in items
                        if m.mechanic_type.value == mechanic_type
                    ]
            return items

    def remove_mechanic(self, mechanic_id) -> Tuple[bool, str]:
        with self._lock:
            if mechanic_id not in self._mechanics:
                return False, "not_found"
            del self._mechanics[mechanic_id]
            self._emit("mechanic_removed", {"mechanic_id": mechanic_id},
                       mechanic_id=mechanic_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Encounter Phase Management
    # ------------------------------------------------------------------

    def register_phase(self, phase_id, encounter_id, phase_type, name,
                       description="", mechanic_ids=None, hp_threshold=0.0,
                       enrage_timer=0.0, transition_message="",
                       is_final_phase=False,
                       metadata=None) -> Tuple[bool, str, Optional[EncounterPhase]]:
        """Register a phase in a multi-phase encounter script."""
        with self._lock:
            if not phase_id:
                return False, "invalid_phase_id", None
            if phase_id in self._phases:
                return False, "phase_exists", None
            if len(self._phases) >= self._config.max_phases:
                return False, "phases_capacity", None
            ptype = _coerce_enum(EncounterPhaseType, phase_type,
                                 EncounterPhaseType.PHASE_ONE)
            phase = EncounterPhase(
                phase_id=phase_id,
                encounter_id=encounter_id,
                phase_type=ptype,
                name=name,
                description=description,
                mechanic_ids=list(mechanic_ids) if mechanic_ids else [],
                hp_threshold=hp_threshold,
                enrage_timer=enrage_timer,
                transition_message=transition_message,
                is_final_phase=is_final_phase,
                metadata=metadata or {},
            )
            self._phases[phase_id] = phase
            self._emit("phase_registered", {
                "phase_id": phase_id,
                "encounter_id": encounter_id,
                "phase_type": ptype.value,
            }, phase_id=phase_id)
            return True, "registered", phase

    def get_phase(self, phase_id) -> Optional[EncounterPhase]:
        with self._lock:
            return self._phases.get(phase_id)

    def list_phases(self, encounter_id="") -> List[EncounterPhase]:
        with self._lock:
            items = list(self._phases.values())
            if encounter_id:
                items = [p for p in items if p.encounter_id == encounter_id]
            return items

    def remove_phase(self, phase_id) -> Tuple[bool, str]:
        with self._lock:
            if phase_id not in self._phases:
                return False, "not_found"
            del self._phases[phase_id]
            self._emit("phase_removed", {"phase_id": phase_id},
                       phase_id=phase_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Encounter Template Management
    # ------------------------------------------------------------------

    def register_template(self, template_id, name, encounter_type,
                          description="", boss_name="", boss_entity_id="",
                          boss_max_health=100000.0,
                          boss_max_health_heroic=250000.0, phase_ids=None,
                          base_mechanics=None, difficulty_tier="normal",
                          arena_id="", recommended_player_count=5,
                          recommended_item_level=0, enrage_total_timer=600.0,
                          reward_table_id="", tags=None,
                          metadata=None) -> Tuple[bool, str, Optional[EncounterTemplate]]:
        """Register a reusable encounter template."""
        with self._lock:
            if not template_id:
                return False, "invalid_template_id", None
            if template_id in self._templates:
                return False, "template_exists", None
            if len(self._templates) >= self._config.max_templates:
                return False, "templates_capacity", None
            etype = _coerce_enum(EncounterType, encounter_type, EncounterType.BOSS)
            dtier = _coerce_enum(DifficultyTier, difficulty_tier, DifficultyTier.NORMAL)
            tpl = EncounterTemplate(
                template_id=template_id,
                name=name,
                encounter_type=etype,
                description=description,
                boss_name=boss_name,
                boss_entity_id=boss_entity_id,
                boss_max_health=boss_max_health,
                boss_max_health_heroic=boss_max_health_heroic,
                phase_ids=list(phase_ids) if phase_ids else [],
                base_mechanics=list(base_mechanics) if base_mechanics else [],
                difficulty_tier=dtier,
                arena_id=arena_id,
                recommended_player_count=recommended_player_count,
                recommended_item_level=recommended_item_level,
                enrage_total_timer=enrage_total_timer,
                reward_table_id=reward_table_id,
                tags=list(tags) if tags else [],
                metadata=metadata or {},
            )
            self._templates[template_id] = tpl
            self._emit("template_registered", {
                "template_id": template_id,
                "encounter_type": etype.value,
                "difficulty_tier": dtier.value,
            })
            return True, "registered", tpl

    def get_template(self, template_id) -> Optional[EncounterTemplate]:
        with self._lock:
            return self._templates.get(template_id)

    def list_templates(self, encounter_type="",
                       difficulty_tier="") -> List[EncounterTemplate]:
        with self._lock:
            items = list(self._templates.values())
            if encounter_type:
                et = _coerce_enum(EncounterType, encounter_type)
                if et is not None:
                    items = [t for t in items if t.encounter_type == et]
                else:
                    items = [
                        t for t in items
                        if t.encounter_type.value == encounter_type
                    ]
            if difficulty_tier:
                dt = _coerce_enum(DifficultyTier, difficulty_tier)
                if dt is not None:
                    items = [t for t in items if t.difficulty_tier == dt]
                else:
                    items = [
                        t for t in items
                        if t.difficulty_tier.value == difficulty_tier
                    ]
            return items

    def remove_template(self, template_id) -> Tuple[bool, str]:
        with self._lock:
            if template_id not in self._templates:
                return False, "not_found"
            del self._templates[template_id]
            self._emit("template_removed", {"template_id": template_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Live Encounter Lifecycle
    # ------------------------------------------------------------------

    def create_encounter(self, template_id, player_ids=None,
                         difficulty_override="",
                         metadata=None) -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Instantiate a live encounter from a registered template."""
        with self._lock:
            tpl = self._templates.get(template_id)
            if tpl is None:
                return False, "template_not_found", None
            if len(self._instances) >= self._config.max_instances:
                return False, "instances_capacity", None
            players = list(player_ids) if player_ids else []
            health = tpl.boss_max_health
            if difficulty_override:
                dt = _coerce_enum(DifficultyTier, difficulty_override)
                if dt in (DifficultyTier.HEROIC, DifficultyTier.MYTHIC,
                          DifficultyTier.LEGENDARY):
                    health = tpl.boss_max_health_heroic
            instance_id = _new_id("enc")
            inst = EncounterInstance(
                instance_id=instance_id,
                template_id=template_id,
                status=EncounterStatus.ACTIVE,
                current_phase_id=tpl.phase_ids[0] if tpl.phase_ids else "",
                player_ids=players,
                boss_current_health=health,
                players_alive=len(players),
                metadata=metadata or {},
            )
            inst.metadata["boss_max_health"] = health
            inst.metadata["difficulty_tier"] = (
                difficulty_override or tpl.difficulty_tier.value
            )
            self._instances[instance_id] = inst
            self._emit("encounter_created", {
                "instance_id": instance_id,
                "template_id": template_id,
                "players": len(players),
            }, encounter_id=instance_id)
            return True, "created", inst

    def get_encounter(self, instance_id) -> Optional[EncounterInstance]:
        with self._lock:
            return self._instances.get(instance_id)

    def list_encounters(self, status="") -> List[EncounterInstance]:
        with self._lock:
            items = list(self._instances.values())
            if status:
                st = _coerce_enum(EncounterStatus, status)
                if st is not None:
                    items = [i for i in items if i.status == st]
                else:
                    items = [
                        i for i in items
                        if i.status.value == status
                    ]
            return items

    def advance_phase(self, instance_id) -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Manually advance an encounter to its next scripted phase."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            tpl = self._templates.get(inst.template_id)
            if tpl is None or not tpl.phase_ids:
                return False, "no_phases", inst
            try:
                idx = tpl.phase_ids.index(inst.current_phase_id)
            except ValueError:
                idx = -1
            if idx < 0 or idx >= len(tpl.phase_ids) - 1:
                return False, "final_phase", inst
            next_phase_id = tpl.phase_ids[idx + 1]
            inst.current_phase_id = next_phase_id
            inst.status = EncounterStatus.PHASE_TRANSITION
            inst.phase_start_time = _now()
            self._emit("phase_advanced", {
                "instance_id": instance_id,
                "phase_id": next_phase_id,
                "reason": "manual",
            }, encounter_id=instance_id, phase_id=next_phase_id)
            return True, "advanced", inst

    def trigger_mechanic(self, instance_id, mechanic_id,
                         player_id="") -> Tuple[bool, str]:
        """Record that a mechanic was triggered during a live encounter."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found"
            if mechanic_id not in self._mechanics:
                return False, "mechanic_not_found"
            if inst.status not in (EncounterStatus.ACTIVE,
                                   EncounterStatus.PHASE_TRANSITION):
                return False, "encounter_not_active"
            inst.mechanic_triggers += 1
            self._emit("mechanic_triggered", {
                "instance_id": instance_id,
                "mechanic_id": mechanic_id,
                "player_id": player_id,
            }, encounter_id=instance_id, mechanic_id=mechanic_id,
                player_id=player_id)
            return True, "triggered"

    def deal_boss_damage(self, instance_id, damage,
                         player_id="") -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Apply damage to the boss of a live encounter."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            if inst.status not in (EncounterStatus.ACTIVE,
                                   EncounterStatus.PHASE_TRANSITION):
                return False, "encounter_not_active", inst
            if damage < 0:
                return False, "invalid_damage", inst
            inst.boss_current_health = max(
                0.0, inst.boss_current_health - damage
            )
            self._emit("boss_damaged", {
                "instance_id": instance_id,
                "damage": damage,
                "player_id": player_id,
                "remaining": inst.boss_current_health,
            }, encounter_id=instance_id, player_id=player_id)
            if inst.boss_current_health <= 0.0:
                self._complete_internal(inst)
            else:
                self._check_phase_threshold(inst)
            return True, "damaged", inst

    def player_downed(self, instance_id,
                      player_id) -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Mark a player as downed inside a live encounter."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            if player_id not in inst.player_ids:
                return False, "player_not_in_encounter", inst
            inst.players_alive = max(0, inst.players_alive - 1)
            self._emit("player_downed", {
                "instance_id": instance_id,
                "player_id": player_id,
                "players_alive": inst.players_alive,
            }, encounter_id=instance_id, player_id=player_id)
            if inst.players_alive <= 0 and inst.status in (
                EncounterStatus.ACTIVE, EncounterStatus.PHASE_TRANSITION
            ):
                self._wipe_internal(inst, "all_players_down")
            return True, "downed", inst

    def player_revived(self, instance_id,
                       player_id) -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Mark a previously downed player as revived."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            if player_id not in inst.player_ids:
                return False, "player_not_in_encounter", inst
            total = len(inst.player_ids)
            inst.players_alive = min(total, inst.players_alive + 1)
            self._emit("player_revived", {
                "instance_id": instance_id,
                "player_id": player_id,
                "players_alive": inst.players_alive,
            }, encounter_id=instance_id, player_id=player_id)
            return True, "revived", inst

    def complete_encounter(self, instance_id) -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Force-complete a live encounter and record completion time."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            if inst.status == EncounterStatus.COMPLETED:
                return False, "already_completed", inst
            self._complete_internal(inst)
            return True, "completed", inst

    def wipe_encounter(self, instance_id,
                       reason="") -> Tuple[bool, str, Optional[EncounterInstance]]:
        """Force-wipe a live encounter with an optional reason."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "not_found", None
            self._wipe_internal(inst, reason or "manual_wipe")
            return True, "wiped", inst

    # ------------------------------------------------------------------
    # Adaptive Scaling
    # ------------------------------------------------------------------

    def calculate_adaptive_scaling(self, instance_id, player_count,
                                   avg_item_level,
                                   avg_skill_score) -> Optional[AdaptiveScaling]:
        """Compute dynamic difficulty scaling from party metrics."""
        with self._lock:
            inst = self._instances.get(instance_id)
            if inst is None:
                return None
            tpl = self._templates.get(inst.template_id)
            base_players = tpl.recommended_player_count if tpl else 5
            count_factor = max(0.5, player_count / max(1, base_players))
            if avg_item_level > 0:
                ilvl_factor = max(0.8, min(1.5, avg_item_level / 1000.0))
            else:
                ilvl_factor = 1.0
            if avg_skill_score > 0:
                skill_factor = max(0.7, min(1.3, avg_skill_score / 100.0))
            else:
                skill_factor = 1.0
            health_multiplier = round(count_factor * ilvl_factor, 3)
            damage_multiplier = round(count_factor * 0.9, 3)
            mechanic_speed_multiplier = round(1.0 / max(0.7, skill_factor), 3)
            enrage_reduction = round(
                max(0.0, (count_factor - 1.0)) * 60.0, 3
            )
            reward_bonus = round(
                max(0.0, (skill_factor - 1.0)) * 0.25, 3
            )
            scaling = AdaptiveScaling(
                scaling_id=_new_id("scale"),
                encounter_id=instance_id,
                player_count=player_count,
                avg_item_level=avg_item_level,
                avg_skill_score=avg_skill_score,
                health_multiplier=health_multiplier,
                damage_multiplier=damage_multiplier,
                mechanic_speed_multiplier=mechanic_speed_multiplier,
                enrage_reduction=enrage_reduction,
                reward_bonus=reward_bonus,
            )
            self._scalings[scaling.scaling_id] = scaling
            _evict_fifo_dict(self._scalings, _MAX_SCALINGS)
            self._emit("adaptive_scaling_calculated", {
                "instance_id": instance_id,
                "scaling_id": scaling.scaling_id,
                "health_multiplier": health_multiplier,
            }, encounter_id=instance_id)
            return scaling

    # ------------------------------------------------------------------
    # Reward Tables
    # ------------------------------------------------------------------

    def register_reward_table(self, table_id, name, encounter_type,
                              difficulty_tier, entries=None, currency_reward=0,
                              experience_reward=0,
                              metadata=None) -> Tuple[bool, str, Optional[RewardTable]]:
        """Register a loot table tied to an encounter type and tier."""
        with self._lock:
            if not table_id:
                return False, "invalid_table_id", None
            if table_id in self._reward_tables:
                return False, "table_exists", None
            if len(self._reward_tables) >= _MAX_REWARD_TABLES:
                return False, "tables_capacity", None
            etype = _coerce_enum(EncounterType, encounter_type, EncounterType.BOSS)
            dtier = _coerce_enum(DifficultyTier, difficulty_tier, DifficultyTier.NORMAL)
            clean_entries: List[RewardEntry] = []
            if entries:
                for entry in entries:
                    if isinstance(entry, RewardEntry):
                        clean_entries.append(entry)
                    elif isinstance(entry, dict):
                        rarity = _coerce_enum(
                            RewardRarity, entry.get("rarity"), RewardRarity.COMMON
                        )
                        clean_entries.append(RewardEntry(
                            reward_id=entry.get("reward_id") or _new_id("rew"),
                            table_id=table_id,
                            item_id=entry.get("item_id", ""),
                            item_name=entry.get("item_name", ""),
                            rarity=rarity,
                            drop_chance=float(entry.get("drop_chance", 0.0)),
                            quantity=int(entry.get("quantity", 1)),
                            is_guaranteed=bool(entry.get("is_guaranteed", False)),
                            metadata=entry.get("metadata") or {},
                        ))
                _evict_fifo_list(clean_entries, _MAX_REWARD_ENTRIES_PER_TABLE)
            table = RewardTable(
                table_id=table_id,
                name=name,
                encounter_type=etype,
                difficulty_tier=dtier,
                entries=clean_entries,
                currency_reward=currency_reward,
                experience_reward=experience_reward,
                metadata=metadata or {},
            )
            self._reward_tables[table_id] = table
            self._emit("reward_table_registered", {
                "table_id": table_id,
                "entries": len(clean_entries),
            })
            return True, "registered", table

    def get_reward_table(self, table_id) -> Optional[RewardTable]:
        with self._lock:
            return self._reward_tables.get(table_id)

    def list_reward_tables(self, encounter_type="",
                           difficulty_tier="") -> List[RewardTable]:
        with self._lock:
            items = list(self._reward_tables.values())
            if encounter_type:
                et = _coerce_enum(EncounterType, encounter_type)
                if et is not None:
                    items = [t for t in items if t.encounter_type == et]
                else:
                    items = [
                        t for t in items
                        if t.encounter_type.value == encounter_type
                    ]
            if difficulty_tier:
                dt = _coerce_enum(DifficultyTier, difficulty_tier)
                if dt is not None:
                    items = [t for t in items if t.difficulty_tier == dt]
                else:
                    items = [
                        t for t in items
                        if t.difficulty_tier.value == difficulty_tier
                    ]
            return items

    def roll_rewards(self, table_id,
                     luck_modifier=1.0) -> List[RewardEntry]:
        """Roll a reward table and return the entries that dropped."""
        with self._lock:
            table = self._reward_tables.get(table_id)
            if table is None:
                return []
            rng = random.Random()
            results: List[RewardEntry] = []
            for entry in table.entries:
                if entry.is_guaranteed:
                    results.append(entry)
                    continue
                chance = min(1.0, entry.drop_chance * max(0.0, luck_modifier))
                if rng.random() < chance:
                    results.append(entry)
            self._emit("rewards_rolled", {
                "table_id": table_id,
                "luck_modifier": luck_modifier,
                "drops": len(results),
            })
            return results

    def remove_reward_table(self, table_id) -> Tuple[bool, str]:
        with self._lock:
            if table_id not in self._reward_tables:
                return False, "not_found"
            del self._reward_tables[table_id]
            self._emit("reward_table_removed", {"table_id": table_id})
            return True, "removed"

    # ------------------------------------------------------------------
    # Tick / Config / Observability
    # ------------------------------------------------------------------

    def tick(self, dt=1.0) -> Dict[str, Any]:
        """Advance the director by one tick, resolving transient states."""
        with self._lock:
            self._tick_count += 1
            phase_resolved = 0
            completed = 0
            wiped = 0
            for inst in list(self._instances.values()):
                if inst.status == EncounterStatus.PHASE_TRANSITION:
                    inst.status = EncounterStatus.ACTIVE
                    phase_resolved += 1
                if inst.status == EncounterStatus.ACTIVE and \
                        inst.boss_current_health <= 0.0:
                    self._complete_internal(inst)
                    completed += 1
                if inst.status == EncounterStatus.WIPED and \
                        inst.boss_current_health <= 0.0:
                    wiped += 1
            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": dt,
                "phase_resolved": phase_resolved,
                "completed": completed,
                "wiped": wiped,
                "active_encounters": self._stats.active_encounters,
                "total_mechanics": self._stats.total_mechanics,
                "total_phases": self._stats.total_phases,
                "total_templates": self._stats.total_templates,
            }

    def set_config(self, updates) -> Tuple[bool, str, EncounterConfig]:
        """Apply a dictionary of config updates to the director."""
        with self._lock:
            if not isinstance(updates, dict):
                return False, "invalid_updates", self._config
            for key, value in updates.items():
                if key == "metadata" and isinstance(value, dict):
                    self._config.metadata.update(value)
                elif hasattr(self._config, key):
                    setattr(self._config, key, value)
            self._emit("config_updated", {"keys": list(updates.keys())})
            return True, "updated", self._config

    def get_config(self) -> EncounterConfig:
        with self._lock:
            return self._config

    def list_events(self, limit=100,
                    event_type="") -> List[EncounterEvent]:
        with self._lock:
            items = list(self._events)
            if event_type:
                items = [e for e in items if e.event_type == event_type]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def get_stats(self) -> EncounterStats:
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "mechanics": len(self._mechanics),
                "phases": len(self._phases),
                "templates": len(self._templates),
                "instances": len(self._instances),
                "active_encounters": self._stats.active_encounters,
                "completed_encounters": self._stats.completed_encounters,
                "wiped_encounters": self._stats.wiped_encounters,
                "reward_tables": len(self._reward_tables),
                "scalings": len(self._scalings),
                "events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> EncounterSnapshot:
        with self._lock:
            self._refresh_stats()
            return EncounterSnapshot(
                config=self._config.to_dict(),
                stats=self._stats.to_dict(),
                templates=[t.to_dict() for t in list(self._templates.values())[:50]],
                instances=[i.to_dict() for i in list(self._instances.values())[:50]],
                reward_tables=[
                    t.to_dict() for t in list(self._reward_tables.values())[:50]
                ],
            )

    def reset(self) -> Tuple[bool, str]:
        """Clear all director state and re-seed the canonical dataset."""
        with self._lock:
            self._mechanics.clear()
            self._phases.clear()
            self._templates.clear()
            self._instances.clear()
            self._scalings.clear()
            self._reward_tables.clear()
            self._events.clear()
            self._config = EncounterConfig()
            self._stats = EncounterStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()
            return True, "reset"

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the director with a canonical set of encounter content."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # Boss Mechanics (8)
            # ----------------------------------------------------------
            self._seed_mechanics()

            # ----------------------------------------------------------
            # Encounter Phases (5 per template, 15 total)
            # ----------------------------------------------------------
            self._seed_ashen_tyrant_phases()
            self._seed_voidwalker_phases()
            self._seed_colossus_phases()

            # ----------------------------------------------------------
            # Encounter Templates (3 multi-phase boss designs)
            # ----------------------------------------------------------
            self._seed_templates()

            # ----------------------------------------------------------
            # Reward Tables (3) with 13 reward entries
            # ----------------------------------------------------------
            self._seed_reward_tables()

            # ----------------------------------------------------------
            # One active live encounter instance
            # ----------------------------------------------------------
            self._seed_live_encounter()

            self._refresh_stats()
            self._emit("director_seeded", {
                "mechanics": len(self._mechanics),
                "phases": len(self._phases),
                "templates": len(self._templates),
                "instances": len(self._instances),
                "reward_tables": len(self._reward_tables),
            })
            self._initialized = True

    def _seed_mechanics(self) -> None:
        mechanics = [
            BossMechanic(
                mechanic_id="mech_fire_breath",
                name="Fire Breath",
                mechanic_type=MechanicType.AOE_DODGE,
                description="A wide cone of flame swept across the arena.",
                telegraph_duration=2.5,
                active_duration=1.5,
                cooldown=12.0,
                damage_multiplier=2.5,
                target_type="all",
                counter_strategy="Spread out and dodge through the cone edge.",
                is_avoidable=True,
                is_interruptible=False,
                metadata={"element": "fire", "cone_degrees": 120},
            ),
            BossMechanic(
                mechanic_id="mech_ground_slam",
                name="Ground Slam",
                mechanic_type=MechanicType.TELEGRAPHED_STRIKE,
                description="A heavy slam that ruptures the ground outward.",
                telegraph_duration=3.0,
                active_duration=1.0,
                cooldown=15.0,
                damage_multiplier=3.0,
                target_type="all",
                counter_strategy="Jump or move beyond the rupture ring.",
                is_avoidable=True,
                is_interruptible=False,
                metadata={"element": "physical", "ring_radius": 18.0},
            ),
            BossMechanic(
                mechanic_id="mech_add_spawns",
                name="Add Spawns",
                mechanic_type=MechanicType.ADD_SPAWNS,
                description="Reinforcing minions enter the arena.",
                telegraph_duration=1.0,
                active_duration=0.0,
                cooldown=30.0,
                damage_multiplier=0.5,
                target_type="adds",
                counter_strategy="Focus the adds before they overwhelm the party.",
                is_avoidable=False,
                is_interruptible=False,
                metadata={"add_count": 3, "add_entity": "ember_wyrm"},
            ),
            BossMechanic(
                mechanic_id="mech_shield_phase",
                name="Shield Phase",
                mechanic_type=MechanicType.SHIELD_MECHANIC,
                description="The boss raises a damage-absorbing shield.",
                telegraph_duration=0.0,
                active_duration=20.0,
                cooldown=45.0,
                damage_multiplier=0.0,
                target_type="boss",
                counter_strategy="Burn the shield down to resume damage.",
                is_avoidable=False,
                is_interruptible=False,
                metadata={"shield_hp": 50000, "shield_element": "arcane"},
            ),
            BossMechanic(
                mechanic_id="mech_enrage",
                name="Enrage",
                mechanic_type=MechanicType.ENRAGE_TIMER,
                description="The boss enters a furious burn state.",
                telegraph_duration=0.0,
                active_duration=0.0,
                cooldown=0.0,
                damage_multiplier=5.0,
                target_type="all",
                counter_strategy="Burn the boss before the party is overrun.",
                is_avoidable=False,
                is_interruptible=False,
                metadata={"soft_cap_seconds": 60},
            ),
            BossMechanic(
                mechanic_id="mech_tank_buster",
                name="Tank Buster",
                mechanic_type=MechanicType.TANK_SWAP,
                description="A heavy single-target strike aimed at the tank.",
                telegraph_duration=1.5,
                active_duration=0.5,
                cooldown=8.0,
                damage_multiplier=4.0,
                target_type="tank",
                counter_strategy="Swap tanks before the cast lands.",
                is_avoidable=False,
                is_interruptible=True,
                metadata={"armor_penetration": 0.6},
            ),
            BossMechanic(
                mechanic_id="mech_chain_lightning",
                name="Chain Lightning",
                mechanic_type=MechanicType.MECHANIC_COMBO,
                description="Arcing lightning that chains between nearby players.",
                telegraph_duration=2.0,
                active_duration=1.0,
                cooldown=18.0,
                damage_multiplier=2.0,
                target_type="all",
                counter_strategy="Break line of sight and spread apart.",
                is_avoidable=True,
                is_interruptible=True,
                metadata={"element": "storm", "chain_range": 8.0, "max_chains": 4},
            ),
            BossMechanic(
                mechanic_id="mech_heal_check",
                name="Heal Check",
                mechanic_type=MechanicType.HEAL_CHECK,
                description="A sustained damage aura that tests healer throughput.",
                telegraph_duration=0.0,
                active_duration=5.0,
                cooldown=25.0,
                damage_multiplier=1.5,
                target_type="all",
                counter_strategy="Sustain healing and use defensive cooldowns.",
                is_avoidable=False,
                is_interruptible=False,
                metadata={"dot_per_second": 1200},
            ),
        ]
        for mech in mechanics:
            self._mechanics[mech.mechanic_id] = mech

    def _seed_ashen_tyrant_phases(self) -> None:
        encounter_id = "tpl_ashen_tyrant"
        phases = [
            EncounterPhase(
                phase_id="phase_ashen_intro",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.INTRO,
                name="Awakening",
                description="The Ashen Tyrant stirs and tests the party.",
                mechanic_ids=["mech_fire_breath"],
                hp_threshold=1.0,
                enrage_timer=0.0,
                transition_message="The Ashen Tyrant takes to the sky.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_ashen_one",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_ONE,
                name="Onslaught of Embers",
                description="The Tyrant unleashes fire and tank-crushing blows.",
                mechanic_ids=["mech_fire_breath", "mech_tank_buster"],
                hp_threshold=0.85,
                enrage_timer=0.0,
                transition_message="The ground cracks as reinforcements arrive.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_ashen_transition",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.TRANSITION,
                name="Call of the Brood",
                description="The Tyrant calls ember wyrms to its aid.",
                mechanic_ids=["mech_add_spawns"],
                hp_threshold=0.65,
                enrage_timer=0.0,
                transition_message="The wyrms fall; the Tyrant descends anew.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_ashen_two",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_TWO,
                name="Storm of Ash",
                description="Slams and chain lightning tear across the arena.",
                mechanic_ids=["mech_ground_slam", "mech_chain_lightning",
                              "mech_tank_buster"],
                hp_threshold=0.40,
                enrage_timer=0.0,
                transition_message="The Tyrant roars, drunk on fury.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_ashen_enrage",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.ENRAGE,
                name="Burning Cataclysm",
                description="The Tyrant enters its final, enraged burn.",
                mechanic_ids=["mech_enrage", "mech_fire_breath"],
                hp_threshold=0.15,
                enrage_timer=60.0,
                transition_message="",
                is_final_phase=True,
            ),
        ]
        for phase in phases:
            self._phases[phase.phase_id] = phase

    def _seed_voidwalker_phases(self) -> None:
        encounter_id = "tpl_voidwalker_prime"
        phases = [
            EncounterPhase(
                phase_id="phase_void_intro",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.INTRO,
                name="Rift Opens",
                description="Voidwalker Prime tears into the arena.",
                mechanic_ids=["mech_chain_lightning"],
                hp_threshold=1.0,
                enrage_timer=0.0,
                transition_message="The voidwalker fixes its gaze on the party.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_void_one",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_ONE,
                name="Arcing Void",
                description="Chained bolts and tank bursts harry the party.",
                mechanic_ids=["mech_chain_lightning", "mech_tank_buster"],
                hp_threshold=0.80,
                enrage_timer=0.0,
                transition_message="The rift surges; the voidwalker shields itself.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_void_intermission",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.INTERMISSION,
                name="Rift Bastion",
                description="A shield forms as void adds pour through.",
                mechanic_ids=["mech_shield_phase", "mech_add_spawns"],
                hp_threshold=0.60,
                enrage_timer=0.0,
                transition_message="The bastion shatters.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_void_two",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_TWO,
                name="Collapse",
                description="Lightning and healing pressure intensify.",
                mechanic_ids=["mech_chain_lightning", "mech_heal_check"],
                hp_threshold=0.35,
                enrage_timer=0.0,
                transition_message="Reality buckles around the voidwalker.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_void_finale",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.FINALE,
                name="Total Void",
                description="The voidwalker enrages as it collapses inward.",
                mechanic_ids=["mech_enrage", "mech_heal_check"],
                hp_threshold=0.15,
                enrage_timer=75.0,
                transition_message="",
                is_final_phase=True,
            ),
        ]
        for phase in phases:
            self._phases[phase.phase_id] = phase

    def _seed_colossus_phases(self) -> None:
        encounter_id = "tpl_colossus_rust"
        phases = [
            EncounterPhase(
                phase_id="phase_colossus_intro",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.INTRO,
                name="The Rust Stirs",
                description="The Colossus of Rust awakens with a ground slam.",
                mechanic_ids=["mech_ground_slam"],
                hp_threshold=1.0,
                enrage_timer=0.0,
                transition_message="The Colossus turns its bulk toward the party.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_colossus_one",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_ONE,
                name="Iron Wrath",
                description="Slams and tank busters pound the frontline.",
                mechanic_ids=["mech_ground_slam", "mech_tank_buster"],
                hp_threshold=0.75,
                enrage_timer=0.0,
                transition_message="Plating sloughs off the Colossus.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_colossus_transition",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.TRANSITION,
                name="Rusted Bastion",
                description="A rusted shield forms as scrap adds swarm in.",
                mechanic_ids=["mech_shield_phase", "mech_add_spawns"],
                hp_threshold=0.55,
                enrage_timer=0.0,
                transition_message="The bastion cracks open.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_colossus_two",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.PHASE_TWO,
                name="Quake and Spark",
                description="Slams and chained lightning erupt together.",
                mechanic_ids=["mech_ground_slam", "mech_chain_lightning"],
                hp_threshold=0.30,
                enrage_timer=0.0,
                transition_message="The Colossus bellows its last challenge.",
                is_final_phase=False,
            ),
            EncounterPhase(
                phase_id="phase_colossus_finale",
                encounter_id=encounter_id,
                phase_type=EncounterPhaseType.FINALE,
                name="Final Collapse",
                description="The Colossus enrages as it crumbles.",
                mechanic_ids=["mech_enrage", "mech_ground_slam"],
                hp_threshold=0.10,
                enrage_timer=90.0,
                transition_message="",
                is_final_phase=True,
            ),
        ]
        for phase in phases:
            self._phases[phase.phase_id] = phase

    def _seed_templates(self) -> None:
        templates = [
            EncounterTemplate(
                template_id="tpl_ashen_tyrant",
                name="The Ashen Tyrant",
                encounter_type=EncounterType.BOSS,
                description="A three-phase dragon lord who rains fire, calls "
                            "her brood, and burns to a cataclysmic enrage.",
                boss_name="Vyrastrasza, the Ashen Tyrant",
                boss_entity_id="boss_vyrastrasza",
                boss_max_health=180000.0,
                boss_max_health_heroic=320000.0,
                phase_ids=[
                    "phase_ashen_intro",
                    "phase_ashen_one",
                    "phase_ashen_transition",
                    "phase_ashen_two",
                    "phase_ashen_enrage",
                ],
                base_mechanics=[
                    "mech_fire_breath", "mech_tank_buster",
                    "mech_add_spawns", "mech_ground_slam",
                    "mech_chain_lightning", "mech_enrage",
                ],
                difficulty_tier=DifficultyTier.HEROIC,
                arena_id="arena_ashen_lair",
                recommended_player_count=5,
                recommended_item_level=900,
                enrage_total_timer=540.0,
                reward_table_id="rt_heroic_boss",
                tags=["dragon", "fire", "multi_phase", "flagship"],
                metadata={"designer": "encounter_team", "launch_patch": "1.4"},
            ),
            EncounterTemplate(
                template_id="tpl_voidwalker_prime",
                name="Voidwalker Prime",
                encounter_type=EncounterType.BOSS,
                description="A two-phase void entity that shields behind a "
                            "rift bastion before collapsing into total void.",
                boss_name="Voidwalker Prime",
                boss_entity_id="boss_voidwalker_prime",
                boss_max_health=220000.0,
                boss_max_health_heroic=420000.0,
                phase_ids=[
                    "phase_void_intro",
                    "phase_void_one",
                    "phase_void_intermission",
                    "phase_void_two",
                    "phase_void_finale",
                ],
                base_mechanics=[
                    "mech_chain_lightning", "mech_tank_buster",
                    "mech_shield_phase", "mech_add_spawns",
                    "mech_heal_check", "mech_enrage",
                ],
                difficulty_tier=DifficultyTier.MYTHIC,
                arena_id="arena_void_rift",
                recommended_player_count=5,
                recommended_item_level=950,
                enrage_total_timer=600.0,
                reward_table_id="rt_mythic_boss",
                tags=["void", "arcane", "multi_phase", "flagship"],
                metadata={"designer": "encounter_team", "launch_patch": "1.5"},
            ),
            EncounterTemplate(
                template_id="tpl_colossus_rust",
                name="The Colossus of Rust",
                encounter_type=EncounterType.BOSS,
                description="A three-phase iron giant that slams, raises a "
                            "rusted bastion, and crumbles into a final enrage.",
                boss_name="The Colossus of Rust",
                boss_entity_id="boss_colossus_rust",
                boss_max_health=240000.0,
                boss_max_health_heroic=360000.0,
                phase_ids=[
                    "phase_colossus_intro",
                    "phase_colossus_one",
                    "phase_colossus_transition",
                    "phase_colossus_two",
                    "phase_colossus_finale",
                ],
                base_mechanics=[
                    "mech_ground_slam", "mech_tank_buster",
                    "mech_shield_phase", "mech_add_spawns",
                    "mech_chain_lightning", "mech_enrage",
                ],
                difficulty_tier=DifficultyTier.HARD,
                arena_id="arena_rust_yard",
                recommended_player_count=5,
                recommended_item_level=820,
                enrage_total_timer=570.0,
                reward_table_id="rt_normal_boss",
                tags=["giant", "physical", "multi_phase"],
                metadata={"designer": "encounter_team", "launch_patch": "1.3"},
            ),
        ]
        for tpl in templates:
            self._templates[tpl.template_id] = tpl

    def _seed_reward_tables(self) -> None:
        # Normal table ------------------------------------------------
        normal_entries = [
            RewardEntry(
                reward_id="rew_normal_shard",
                table_id="rt_normal_boss",
                item_id="item_resonant_shard",
                item_name="Resonant Shard",
                rarity=RewardRarity.COMMON,
                drop_chance=0.80,
                quantity=3,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_normal_pendant",
                table_id="rt_normal_boss",
                item_id="item_iron_ward_pendant",
                item_name="Iron Ward Pendant",
                rarity=RewardRarity.UNCOMMON,
                drop_chance=0.40,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_normal_scale",
                table_id="rt_normal_boss",
                item_id="item_tyrant_scale_fragment",
                item_name="Tyrant Scale Fragment",
                rarity=RewardRarity.RARE,
                drop_chance=0.15,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_normal_gold",
                table_id="rt_normal_boss",
                item_id="item_gold_pouch",
                item_name="Gold Pouch",
                rarity=RewardRarity.COMMON,
                drop_chance=1.0,
                quantity=1,
                is_guaranteed=True,
            ),
        ]
        self._reward_tables["rt_normal_boss"] = RewardTable(
            table_id="rt_normal_boss",
            name="Normal Boss Loot",
            encounter_type=EncounterType.BOSS,
            difficulty_tier=DifficultyTier.NORMAL,
            entries=normal_entries,
            currency_reward=5000,
            experience_reward=8000,
            metadata={"version": 1},
        )

        # Heroic table ------------------------------------------------
        heroic_entries = [
            RewardEntry(
                reward_id="rew_heroic_gauntlet",
                table_id="rt_heroic_boss",
                item_id="item_emberforged_gauntlet",
                item_name="Emberforged Gauntlet",
                rarity=RewardRarity.RARE,
                drop_chance=0.50,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_heroic_cloak",
                table_id="rt_heroic_boss",
                item_id="item_void_touched_cloak",
                item_name="Void-Touched Cloak",
                rarity=RewardRarity.EPIC,
                drop_chance=0.25,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_heroic_core",
                table_id="rt_heroic_boss",
                item_id="item_ashen_core",
                item_name="Ashen Core",
                rarity=RewardRarity.RARE,
                drop_chance=0.35,
                quantity=2,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_heroic_crest",
                table_id="rt_heroic_boss",
                item_id="item_heroic_crest",
                item_name="Heroic Crest",
                rarity=RewardRarity.UNCOMMON,
                drop_chance=1.0,
                quantity=1,
                is_guaranteed=True,
            ),
        ]
        self._reward_tables["rt_heroic_boss"] = RewardTable(
            table_id="rt_heroic_boss",
            name="Heroic Boss Loot",
            encounter_type=EncounterType.BOSS,
            difficulty_tier=DifficultyTier.HEROIC,
            entries=heroic_entries,
            currency_reward=12000,
            experience_reward=18000,
            metadata={"version": 2},
        )

        # Mythic table ------------------------------------------------
        mythic_entries = [
            RewardEntry(
                reward_id="rew_mythic_heart",
                table_id="rt_mythic_boss",
                item_id="item_voidwalker_heart",
                item_name="Voidwalker Heart",
                rarity=RewardRarity.LEGENDARY,
                drop_chance=0.20,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_mythic_matrix",
                table_id="rt_mythic_boss",
                item_id="item_colossus_core_matrix",
                item_name="Colossus Core Matrix",
                rarity=RewardRarity.LEGENDARY,
                drop_chance=0.15,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_mythic_crown",
                table_id="rt_mythic_boss",
                item_id="item_ashen_tyrant_crown",
                item_name="Ashen Tyrant Crown",
                rarity=RewardRarity.MYTHIC,
                drop_chance=0.05,
                quantity=1,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_mythic_essence",
                table_id="rt_mythic_boss",
                item_id="item_mythic_essence",
                item_name="Mythic Essence",
                rarity=RewardRarity.EPIC,
                drop_chance=0.60,
                quantity=3,
                is_guaranteed=False,
            ),
            RewardEntry(
                reward_id="rew_mythic_crest",
                table_id="rt_mythic_boss",
                item_id="item_mythic_crest",
                item_name="Mythic Crest",
                rarity=RewardRarity.EPIC,
                drop_chance=1.0,
                quantity=1,
                is_guaranteed=True,
            ),
        ]
        self._reward_tables["rt_mythic_boss"] = RewardTable(
            table_id="rt_mythic_boss",
            name="Mythic Boss Loot",
            encounter_type=EncounterType.BOSS,
            difficulty_tier=DifficultyTier.MYTHIC,
            entries=mythic_entries,
            currency_reward=30000,
            experience_reward=45000,
            metadata={"version": 2},
        )

    def _seed_live_encounter(self) -> None:
        tpl = self._templates.get("tpl_ashen_tyrant")
        if tpl is None:
            return
        players = [
            "player_tank_1",
            "player_healer_1",
            "player_dps_1",
            "player_dps_2",
            "player_dps_3",
        ]
        health = tpl.boss_max_health_heroic
        inst = EncounterInstance(
            instance_id="enc_ashen_live",
            template_id="tpl_ashen_tyrant",
            status=EncounterStatus.ACTIVE,
            current_phase_id="phase_ashen_intro",
            player_ids=players,
            boss_current_health=health,
            players_alive=len(players),
            metadata={
                "boss_max_health": health,
                "difficulty_tier": DifficultyTier.HEROIC.value,
                "session": "seed_session_001",
            },
        )
        self._instances[inst.instance_id] = inst
        self._emit("encounter_created", {
            "instance_id": inst.instance_id,
            "template_id": "tpl_ashen_tyrant",
            "players": len(players),
            "seeded": True,
        }, encounter_id=inst.instance_id)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_encounter_director() -> AIEncounterDirector:
    """Factory function returning the singleton AIEncounterDirector instance."""
    return AIEncounterDirector.get_instance()
