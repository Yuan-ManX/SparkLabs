"""
SparkLabs Engine - Dungeon Instance System

Manages instanced dungeon encounters with difficulty scaling, party
formation, boss encounters, lockout tracking, completion records, and
reward distribution. Players form parties, enter dungeon instances,
progress through wings and boss encounters, and earn completion-based
rewards with weekly lockout timers.

Architecture:
  DungeonInstanceSystem (singleton)
    |-- DungeonDifficulty, InstanceStatus, EncounterState, DungeonEventKind
    |-- BossEncounter, DungeonWing, DungeonDefinition, PartyMember,
       DungeonInstance, CompletionRecord, LockoutEntry, DungeonConfig,
       DungeonStats, DungeonSnapshot, DungeonEvent
    |-- get_dungeon_instance_system

Core Capabilities:
  - register_dungeon / remove_dungeon / get_dungeon / list_dungeons
  - create_instance / destroy_instance / get_instance / list_instances
  - add_party_member / remove_party_member / get_party
  - start_instance / complete_instance / fail_instance
  - start_encounter / complete_encounter / fail_encounter
  - get_progress / get_encounter_state
  - check_lockout / get_lockout / clear_lockout
  - get_completion_record / list_completions
  - calculate_difficulty / scale_encounter
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`DungeonInstanceSystem.get_instance` or the module-level
:func:`get_dungeon_instance_system` factory.
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

_MAX_DUNGEONS: int = 500
_MAX_INSTANCES: int = 50000
_MAX_PARTY_MEMBERS: int = 6
_MAX_COMPLETIONS: int = 500000
_MAX_LOCKOUTS: int = 500000
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

class DungeonDifficulty(str, Enum):
    """Difficulty tier of a dungeon."""
    NORMAL = "normal"
    HEROIC = "heroic"
    MYTHIC = "mythic"
    ASCENDANT = "ascendant"


class InstanceStatus(str, Enum):
    """Lifecycle state of a dungeon instance."""
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    LOCKED = "locked"


class EncounterState(str, Enum):
    """State of a single boss encounter within a dungeon."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DEFEATED = "defeated"
    WIPED = "wiped"
    SKIPPED = "skipped"


class DungeonEventKind(str, Enum):
    """Audit event types emitted by the dungeon instance system."""
    DUNGEON_REGISTERED = "dungeon_registered"
    DUNGEON_REMOVED = "dungeon_removed"
    INSTANCE_CREATED = "instance_created"
    INSTANCE_DESTROYED = "instance_destroyed"
    PARTY_MEMBER_ADDED = "party_member_added"
    PARTY_MEMBER_REMOVED = "party_member_removed"
    INSTANCE_STARTED = "instance_started"
    INSTANCE_COMPLETED = "instance_completed"
    INSTANCE_FAILED = "instance_failed"
    ENCOUNTER_STARTED = "encounter_started"
    ENCOUNTER_DEFEATED = "encounter_defeated"
    ENCOUNTER_WIPED = "encounter_wiped"
    LOCKOUT_SET = "lockout_set"
    LOCKOUT_CLEARED = "lockout_cleared"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class BossEncounter:
    """A boss encounter within a dungeon wing."""
    encounter_id: str
    name: str
    description: str = ""
    boss_entity_id: str = ""
    base_health: float = 100000.0
    base_damage: float = 5000.0
    mechanic_ids: List[str] = field(default_factory=list)
    enrage_timer: float = 600.0
    required_item_level: int = 0
    position: int = 0
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonWing:
    """A wing section of a dungeon containing encounters."""
    wing_id: str
    name: str
    description: str = ""
    encounters: List[BossEncounter] = field(default_factory=list)
    required_progression: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonDefinition:
    """Definition of a dungeon."""
    dungeon_id: str
    name: str
    description: str = ""
    min_level: int = 1
    recommended_level: int = 50
    max_party_size: int = 5
    wings: List[DungeonWing] = field(default_factory=list)
    supported_difficulties: List[str] = field(default_factory=lambda: [DungeonDifficulty.NORMAL.value])
    lockout_duration_hours: float = 168.0
    ilvl_requirement_normal: int = 0
    ilvl_requirement_heroic: int = 200
    ilvl_requirement_mythic: int = 250
    ilvl_requirement_ascendant: int = 300
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PartyMember:
    """A member of a dungeon party."""
    player_id: str
    role: str = "dps"
    level: int = 1
    item_level: int = 0
    joined_at: float = field(default_factory=_now)
    is_leader: bool = False
    ready: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EncounterProgress:
    """Progress tracking for a single encounter."""
    encounter_id: str
    state: str = EncounterState.PENDING.value
    attempts: int = 0
    started_at: float = 0.0
    completed_at: float = 0.0
    damage_dealt: float = 0.0
    damage_taken: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonInstance:
    """A live instance of a dungeon for a specific party."""
    instance_id: str
    dungeon_id: str
    difficulty: str = DungeonDifficulty.NORMAL.value
    status: str = InstanceStatus.FORMING.value
    party: List[PartyMember] = field(default_factory=list)
    encounter_progress: Dict[str, EncounterProgress] = field(default_factory=dict)
    current_wing: str = ""
    current_encounter: str = ""
    created_at: float = field(default_factory=_now)
    started_at: float = 0.0
    completed_at: float = 0.0
    time_limit: float = 7200.0
    elapsed_time: float = 0.0
    total_wipes: int = 0
    total_encounters_defeated: int = 0
    loot_distributed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def party_size(self) -> int:
        return len(self.party)

    @property
    def is_active(self) -> bool:
        return self.status == InstanceStatus.ACTIVE.value

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["party_size"] = self.party_size
        d["is_active"] = self.is_active
        return d


@dataclass
class CompletionRecord:
    """Record of a completed dungeon run."""
    record_id: str
    instance_id: str
    dungeon_id: str
    difficulty: str = DungeonDifficulty.NORMAL.value
    player_ids: List[str] = field(default_factory=list)
    completion_time: float = 0.0
    total_wipes: int = 0
    encounters_defeated: int = 0
    total_encounters: int = 0
    completed_at: float = field(default_factory=_now)
    rewards_distributed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LockoutEntry:
    """Weekly lockout entry for a player on a specific dungeon/difficulty."""
    lockout_id: str
    player_id: str
    dungeon_id: str
    difficulty: str = DungeonDifficulty.NORMAL.value
    locked_until: float = 0.0
    encounters_defeated: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonConfig:
    """Global tuning parameters."""
    max_dungeons: int = 500
    max_instances: int = 50000
    max_party_size: int = 6
    lockout_duration_hours: float = 168.0
    time_limit_default: float = 7200.0
    difficulty_scale_normal: float = 1.0
    difficulty_scale_heroic: float = 1.5
    difficulty_scale_mythic: float = 2.0
    difficulty_scale_ascendant: float = 3.0
    allow_skip_encounters: bool = False
    max_wipes_per_encounter: int = 99
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonStats:
    """Aggregate statistics."""
    total_dungeons: int = 0
    total_instances_created: int = 0
    total_instances_active: int = 0
    total_instances_completed: int = 0
    total_instances_failed: int = 0
    total_encounters_defeated: int = 0
    total_wipes: int = 0
    total_lockouts: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonSnapshot:
    """Full state snapshot."""
    dungeons: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DungeonEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    dungeon_id: str = ""
    instance_id: str = ""
    player_id: str = ""
    encounter_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Dungeon Instance System
# ---------------------------------------------------------------------------

class DungeonInstanceSystem:
    """Manages dungeon definitions, live instances, party formation, and lockouts."""

    _instance: Optional["DungeonInstanceSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._dungeons: Dict[str, DungeonDefinition] = {}
        self._instances: Dict[str, DungeonInstance] = {}
        self._completions: Dict[str, CompletionRecord] = {}
        self._lockouts: Dict[str, LockoutEntry] = {}
        self._events: List[DungeonEvent] = []
        self._stats = DungeonStats()
        self._config = DungeonConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "DungeonInstanceSystem":
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

            # Dungeon 1: Shadow Crypt (normal/heroic)
            d1_encounters = [
                BossEncounter(
                    encounter_id="enc_crypt_w1_boss1",
                    name="Warden Kael",
                    description="The undead warden guards the crypt entrance.",
                    boss_entity_id="boss_warden_kael",
                    base_health=80000.0, base_damage=3000.0,
                    mechanic_ids=["cleave", "summon_adds"],
                    enrage_timer=420.0, required_item_level=180,
                    position=1,
                ),
                BossEncounter(
                    encounter_id="enc_crypt_w1_boss2",
                    name="Necromancer Vex",
                    description="A dark necromancer raising the dead.",
                    boss_entity_id="boss_necromancer_vex",
                    base_health=120000.0, base_damage=4500.0,
                    mechanic_ids=["void_zone", "soul_drain", "raise_dead"],
                    enrage_timer=480.0, required_item_level=190,
                    position=2,
                ),
                BossEncounter(
                    encounter_id="enc_crypt_w1_boss3",
                    name="The Crypt Lord",
                    description="Ancient ruler of the shadow crypt.",
                    boss_entity_id="boss_crypt_lord",
                    base_health=200000.0, base_damage=6500.0,
                    mechanic_ids=["swarm", "enrage", "phase_shift", "earthquake"],
                    enrage_timer=600.0, required_item_level=200,
                    position=3,
                ),
            ]
            d1_wing = DungeonWing(
                wing_id="wing_crypt_main",
                name="Main Crypt",
                description="The central wing of the shadow crypt.",
                encounters=d1_encounters,
            )
            d1 = DungeonDefinition(
                dungeon_id="dgn_shadow_crypt",
                name="Shadow Crypt",
                description="A haunted crypt filled with undead horrors.",
                min_level=45, recommended_level=50, max_party_size=5,
                wings=[d1_wing],
                supported_difficulties=[DungeonDifficulty.NORMAL.value, DungeonDifficulty.HEROIC.value],
                lockout_duration_hours=168.0,
                ilvl_requirement_normal=180,
                ilvl_requirement_heroic=210,
            )
            self._dungeons[d1.dungeon_id] = d1

            # Dungeon 2: Ember Forge (heroic/mythic)
            d2_encounters = [
                BossEncounter(
                    encounter_id="enc_forge_w1_boss1",
                    name="Forgemaster Dorn",
                    description="Master of the ember forge.",
                    boss_entity_id="boss_forgemaster_dorn",
                    base_health=150000.0, base_damage=5000.0,
                    mechanic_ids=["heat_wave", "molten_slam"],
                    enrage_timer=360.0, required_item_level=220,
                    position=1,
                ),
                BossEncounter(
                    encounter_id="enc_forge_w1_boss2",
                    name="Inferno Core",
                    description="The living heart of the forge.",
                    boss_entity_id="boss_inferno_core",
                    base_health=250000.0, base_damage=8000.0,
                    mechanic_ids=["burning_aura", "lava_geyser", "core_overload"],
                    enrage_timer=420.0, required_item_level=250,
                    position=2,
                ),
            ]
            d2_wing = DungeonWing(
                wing_id="wing_forge_main",
                name="The Great Forge",
                description="The central forge chamber.",
                encounters=d2_encounters,
            )
            d2 = DungeonDefinition(
                dungeon_id="dgn_ember_forge",
                name="Ember Forge",
                description="A volcanic forge where legendary weapons are born.",
                min_level=55, recommended_level=60, max_party_size=5,
                wings=[d2_wing],
                supported_difficulties=[DungeonDifficulty.HEROIC.value, DungeonDifficulty.MYTHIC.value],
                lockout_duration_hours=168.0,
                ilvl_requirement_heroic=240,
                ilvl_requirement_mythic=280,
            )
            self._dungeons[d2.dungeon_id] = d2

            # Dungeon 3: Sky Citadel (mythic/ascendant)
            d3_encounters = [
                BossEncounter(
                    encounter_id="enc_citadel_w1_boss1",
                    name="Storm Warden",
                    description="Guardian of the citadel gates.",
                    boss_entity_id="boss_storm_warden",
                    base_health=300000.0, base_damage=9000.0,
                    mechanic_ids=["lightning_chain", "wind_blast"],
                    enrage_timer=420.0, required_item_level=280,
                    position=1,
                ),
                BossEncounter(
                    encounter_id="enc_citadel_w1_boss2",
                    name="The Ascendant Council",
                    description="Three ascended beings ruling the citadel.",
                    boss_entity_id="boss_ascendant_council",
                    base_health=500000.0, base_damage=12000.0,
                    mechanic_ids=["council_split", "ascendant_fury", "lightning_storm", "phase_shift"],
                    enrage_timer=540.0, required_item_level=300,
                    position=2,
                ),
            ]
            d3_wing = DungeonWing(
                wing_id="wing_citadel_summit",
                name="Citadel Summit",
                description="The pinnacle of the sky citadel.",
                encounters=d3_encounters,
            )
            d3 = DungeonDefinition(
                dungeon_id="dgn_sky_citadel",
                name="Sky Citadel",
                description="A floating fortress above the clouds.",
                min_level=60, recommended_level=65, max_party_size=5,
                wings=[d3_wing],
                supported_difficulties=[DungeonDifficulty.MYTHIC.value, DungeonDifficulty.ASCENDANT.value],
                lockout_duration_hours=168.0,
                ilvl_requirement_mythic=300,
                ilvl_requirement_ascendant=330,
            )
            self._dungeons[d3.dungeon_id] = d3

            # Seed an active instance
            inst1 = DungeonInstance(
                instance_id="inst_starter_crypt_01",
                dungeon_id="dgn_shadow_crypt",
                difficulty=DungeonDifficulty.NORMAL.value,
                status=InstanceStatus.ACTIVE.value,
                party=[
                    PartyMember(player_id="player_starter", role="tank", level=50,
                                item_level=185, is_leader=True, ready=True),
                    PartyMember(player_id="player_starter_2", role="healer", level=50,
                                item_level=183, ready=True),
                    PartyMember(player_id="player_starter_3", role="dps", level=50,
                                item_level=188, ready=True),
                ],
                started_at=_now() - 1800,
                current_wing="wing_crypt_main",
                current_encounter="enc_crypt_w1_boss1",
            )
            for enc in d1_encounters:
                inst1.encounter_progress[enc.encounter_id] = EncounterProgress(
                    encounter_id=enc.encounter_id,
                )
            inst1.encounter_progress["enc_crypt_w1_boss1"].state = EncounterState.IN_PROGRESS.value
            inst1.encounter_progress["enc_crypt_w1_boss1"].started_at = _now() - 300
            self._instances[inst1.instance_id] = inst1

            # Seed a completion record
            cr1 = CompletionRecord(
                record_id="comp_veteran_forge_01",
                instance_id="inst_veteran_forge_01",
                dungeon_id="dgn_ember_forge",
                difficulty=DungeonDifficulty.HEROIC.value,
                player_ids=["player_veteran", "player_veteran_2", "player_veteran_3",
                           "player_veteran_4", "player_veteran_5"],
                completion_time=5400.0,
                total_wipes=2,
                encounters_defeated=2,
                total_encounters=2,
                completed_at=_now() - 86400,
                rewards_distributed=True,
            )
            self._completions[cr1.record_id] = cr1

            # Seed lockout for veteran
            lo1 = LockoutEntry(
                lockout_id="lockout_veteran_forge",
                player_id="player_veteran",
                dungeon_id="dgn_ember_forge",
                difficulty=DungeonDifficulty.HEROIC.value,
                locked_until=_now() + 86400 * 4,
                encounters_defeated=["enc_forge_w1_boss1", "enc_forge_w1_boss2"],
            )
            self._lockouts[f"{lo1.player_id}:{lo1.dungeon_id}:{lo1.difficulty}"] = lo1

            self._update_stats()
            self._initialized = True

    def _log_event(self, kind: str, details: Dict[str, Any],
                   dungeon_id: str = "", instance_id: str = "", player_id: str = "",
                   encounter_id: str = "", description: str = "") -> None:
        self._event_counter += 1
        ev = DungeonEvent(
            event_id=f"devt_{self._event_counter:06d}",
            kind=kind, timestamp=_now(),
            dungeon_id=dungeon_id, instance_id=instance_id, player_id=player_id,
            encounter_id=encounter_id, description=description, details=details,
        )
        self._events.append(ev)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_stats(self) -> None:
        self._stats.total_dungeons = len(self._dungeons)
        self._stats.total_instances_created = len(self._instances)
        self._stats.total_instances_active = sum(
            1 for i in self._instances.values()
            if i.status == InstanceStatus.ACTIVE.value
        )
        self._stats.total_instances_completed = sum(
            1 for i in self._instances.values()
            if i.status == InstanceStatus.COMPLETED.value
        )
        self._stats.total_instances_failed = sum(
            1 for i in self._instances.values()
            if i.status == InstanceStatus.FAILED.value
        )
        self._stats.total_encounters_defeated = sum(
            i.total_encounters_defeated for i in self._instances.values()
        )
        self._stats.total_wipes = sum(i.total_wipes for i in self._instances.values())
        self._stats.total_lockouts = len(self._lockouts)

    # ------------------------------------------------------------------
    # Dungeon Definition Management
    # ------------------------------------------------------------------

    def register_dungeon(self, dungeon_id: str, name: str, description: str = "",
                         min_level: int = 1, recommended_level: int = 50,
                         max_party_size: int = 5,
                         supported_difficulties: Optional[List[str]] = None,
                         lockout_duration_hours: float = 168.0
                         ) -> Tuple[bool, str, Optional[DungeonDefinition]]:
        with _LOCK:
            if dungeon_id in self._dungeons:
                return False, "dungeon_exists", None
            if len(self._dungeons) >= _MAX_DUNGEONS:
                return False, "max_dungeons", None
            dgn = DungeonDefinition(
                dungeon_id=dungeon_id, name=name, description=description,
                min_level=min_level, recommended_level=recommended_level,
                max_party_size=max_party_size,
                supported_difficulties=supported_difficulties or [DungeonDifficulty.NORMAL.value],
                lockout_duration_hours=lockout_duration_hours,
            )
            self._dungeons[dungeon_id] = dgn
            self._log_event(DungeonEventKind.DUNGEON_REGISTERED.value,
                            {"name": name}, dungeon_id=dungeon_id, description=name)
            self._update_stats()
            return True, "registered", dgn

    def remove_dungeon(self, dungeon_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if dungeon_id not in self._dungeons:
                return False, "dungeon_not_found"
            del self._dungeons[dungeon_id]
            self._log_event(DungeonEventKind.DUNGEON_REMOVED.value,
                            {"dungeon_id": dungeon_id}, dungeon_id=dungeon_id)
            self._update_stats()
            return True, "removed"

    def get_dungeon(self, dungeon_id: str) -> Optional[DungeonDefinition]:
        with _LOCK:
            return self._dungeons.get(dungeon_id)

    def list_dungeons(self, difficulty: str = "") -> List[DungeonDefinition]:
        with _LOCK:
            results = list(self._dungeons.values())
            if difficulty:
                results = [d for d in results if difficulty in d.supported_difficulties]
            return results

    # ------------------------------------------------------------------
    # Instance Management
    # ------------------------------------------------------------------

    def create_instance(self, dungeon_id: str,
                        difficulty: str = DungeonDifficulty.NORMAL.value
                        ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            dgn = self._dungeons.get(dungeon_id)
            if dgn is None:
                return False, "dungeon_not_found", None
            if difficulty not in dgn.supported_difficulties:
                return False, "difficulty_not_supported", None
            instance_id = _new_id("inst")
            inst = DungeonInstance(
                instance_id=instance_id, dungeon_id=dungeon_id,
                difficulty=difficulty,
                status=InstanceStatus.FORMING.value,
                time_limit=self._config.time_limit_default,
            )
            for wing in dgn.wings:
                for enc in wing.encounters:
                    inst.encounter_progress[enc.encounter_id] = EncounterProgress(
                        encounter_id=enc.encounter_id,
                    )
            self._instances[instance_id] = inst
            self._log_event(DungeonEventKind.INSTANCE_CREATED.value,
                            {"difficulty": difficulty},
                            dungeon_id=dungeon_id, instance_id=instance_id)
            self._update_stats()
            return True, "created", inst

    def destroy_instance(self, instance_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if instance_id not in self._instances:
                return False, "instance_not_found"
            del self._instances[instance_id]
            self._log_event(DungeonEventKind.INSTANCE_DESTROYED.value,
                            {"instance_id": instance_id}, instance_id=instance_id)
            self._update_stats()
            return True, "destroyed"

    def get_instance_by_id(self, instance_id: str) -> Optional[DungeonInstance]:
        with _LOCK:
            return self._instances.get(instance_id)

    def list_instances(self, dungeon_id: str = "", status: str = "",
                       difficulty: str = "") -> List[DungeonInstance]:
        with _LOCK:
            results = list(self._instances.values())
            if dungeon_id:
                results = [i for i in results if i.dungeon_id == dungeon_id]
            if status:
                results = [i for i in results if i.status == status]
            if difficulty:
                results = [i for i in results if i.difficulty == difficulty]
            return results

    # ------------------------------------------------------------------
    # Party Management
    # ------------------------------------------------------------------

    def add_party_member(self, instance_id: str, player_id: str,
                         role: str = "dps", level: int = 1, item_level: int = 0
                         ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            dgn = self._dungeons.get(inst.dungeon_id)
            if dgn is None:
                return False, "dungeon_not_found", None
            if len(inst.party) >= dgn.max_party_size:
                return False, "party_full", inst
            if any(m.player_id == player_id for m in inst.party):
                return False, "already_in_party", inst
            is_leader = len(inst.party) == 0
            member = PartyMember(
                player_id=player_id, role=role, level=level,
                item_level=item_level, is_leader=is_leader, ready=False,
            )
            inst.party.append(member)
            self._log_event(DungeonEventKind.PARTY_MEMBER_ADDED.value,
                            {"player_id": player_id, "role": role},
                            instance_id=instance_id, player_id=player_id)
            return True, "added", inst

    def remove_party_member(self, instance_id: str, player_id: str
                            ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            member = next((m for m in inst.party if m.player_id == player_id), None)
            if member is None:
                return False, "not_in_party", inst
            inst.party.remove(member)
            if member.is_leader and inst.party:
                inst.party[0].is_leader = True
            self._log_event(DungeonEventKind.PARTY_MEMBER_REMOVED.value,
                            {"player_id": player_id},
                            instance_id=instance_id, player_id=player_id)
            return True, "removed", inst

    def get_party(self, instance_id: str) -> List[PartyMember]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return []
            return list(inst.party)

    # ------------------------------------------------------------------
    # Instance Lifecycle
    # ------------------------------------------------------------------

    def start_instance(self, instance_id: str
                       ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            if inst.status != InstanceStatus.FORMING.value:
                return False, "not_forming", inst
            if not inst.party:
                return False, "empty_party", inst
            inst.status = InstanceStatus.ACTIVE.value
            inst.started_at = _now()
            dgn = self._dungeons.get(inst.dungeon_id)
            if dgn and dgn.wings:
                inst.current_wing = dgn.wings[0].wing_id
                if dgn.wings[0].encounters:
                    inst.current_encounter = dgn.wings[0].encounters[0].encounter_id
            self._log_event(DungeonEventKind.INSTANCE_STARTED.value,
                            {"party_size": inst.party_size},
                            instance_id=instance_id)
            self._update_stats()
            return True, "started", inst

    def complete_instance(self, instance_id: str
                          ) -> Tuple[bool, str, Optional[CompletionRecord]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            if inst.status != InstanceStatus.ACTIVE.value:
                return False, "not_active", None
            inst.status = InstanceStatus.COMPLETED.value
            inst.completed_at = _now()
            inst.elapsed_time = inst.completed_at - inst.started_at
            total_encounters = len(inst.encounter_progress)
            defeated = sum(
                1 for p in inst.encounter_progress.values()
                if p.state == EncounterState.DEFEATED.value
            )
            inst.total_encounters_defeated = defeated
            record = CompletionRecord(
                record_id=_new_id("comp"),
                instance_id=instance_id,
                dungeon_id=inst.dungeon_id,
                difficulty=inst.difficulty,
                player_ids=[m.player_id for m in inst.party],
                completion_time=inst.elapsed_time,
                total_wipes=inst.total_wipes,
                encounters_defeated=defeated,
                total_encounters=total_encounters,
            )
            self._completions[record.record_id] = record
            for member in inst.party:
                self._set_lockout(member.player_id, inst.dungeon_id,
                                  inst.difficulty, inst.elapsed_time,
                                  [eid for eid, p in inst.encounter_progress.items()
                                   if p.state == EncounterState.DEFEATED.value])
            self._log_event(DungeonEventKind.INSTANCE_COMPLETED.value,
                            {"completion_time": inst.elapsed_time,
                             "encounters_defeated": defeated},
                            instance_id=instance_id)
            self._update_stats()
            return True, "completed", record

    def fail_instance(self, instance_id: str, reason: str = "wipe"
                      ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            if inst.status != InstanceStatus.ACTIVE.value:
                return False, "not_active", inst
            inst.status = InstanceStatus.FAILED.value
            inst.completed_at = _now()
            inst.elapsed_time = inst.completed_at - inst.started_at
            self._log_event(DungeonEventKind.INSTANCE_FAILED.value,
                            {"reason": reason},
                            instance_id=instance_id, description=reason)
            self._update_stats()
            return True, "failed", inst

    # ------------------------------------------------------------------
    # Encounter Management
    # ------------------------------------------------------------------

    def start_encounter(self, instance_id: str, encounter_id: str
                        ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            if inst.status != InstanceStatus.ACTIVE.value:
                return False, "not_active", inst
            prog = inst.encounter_progress.get(encounter_id)
            if prog is None:
                return False, "encounter_not_found", inst
            if prog.state == EncounterState.DEFEATED.value:
                return False, "already_defeated", inst
            prog.state = EncounterState.IN_PROGRESS.value
            prog.started_at = _now()
            prog.attempts += 1
            inst.current_encounter = encounter_id
            self._log_event(DungeonEventKind.ENCOUNTER_STARTED.value,
                            {"encounter_id": encounter_id, "attempt": prog.attempts},
                            instance_id=instance_id, encounter_id=encounter_id)
            return True, "started", inst

    def complete_encounter(self, instance_id: str, encounter_id: str
                           ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            prog = inst.encounter_progress.get(encounter_id)
            if prog is None:
                return False, "encounter_not_found", inst
            if prog.state != EncounterState.IN_PROGRESS.value:
                return False, "not_in_progress", inst
            prog.state = EncounterState.DEFEATED.value
            prog.completed_at = _now()
            inst.total_encounters_defeated += 1
            self._log_event(DungeonEventKind.ENCOUNTER_DEFEATED.value,
                            {"encounter_id": encounter_id},
                            instance_id=instance_id, encounter_id=encounter_id)
            self._update_stats()
            return True, "defeated", inst

    def fail_encounter(self, instance_id: str, encounter_id: str
                       ) -> Tuple[bool, str, Optional[DungeonInstance]]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return False, "instance_not_found", None
            prog = inst.encounter_progress.get(encounter_id)
            if prog is None:
                return False, "encounter_not_found", inst
            prog.state = EncounterState.PENDING.value
            inst.total_wipes += 1
            self._log_event(DungeonEventKind.ENCOUNTER_WIPED.value,
                            {"encounter_id": encounter_id, "attempt": prog.attempts},
                            instance_id=instance_id, encounter_id=encounter_id)
            self._update_stats()
            return True, "wiped", inst

    def get_progress(self, instance_id: str) -> Dict[str, EncounterProgress]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return {}
            return dict(inst.encounter_progress)

    def get_encounter_state(self, instance_id: str, encounter_id: str) -> Optional[str]:
        with _LOCK:
            inst = self._instances.get(instance_id)
            if inst is None:
                return None
            prog = inst.encounter_progress.get(encounter_id)
            if prog is None:
                return None
            return prog.state

    # ------------------------------------------------------------------
    # Lockout Management
    # ------------------------------------------------------------------

    def _set_lockout(self, player_id: str, dungeon_id: str, difficulty: str,
                     elapsed: float, encounters_defeated: List[str]) -> None:
        lockout_key = f"{player_id}:{dungeon_id}:{difficulty}"
        lockout = self._lockouts.get(lockout_key)
        if lockout is None:
            lockout = LockoutEntry(
                lockout_id=lockout_key,
                player_id=player_id, dungeon_id=dungeon_id,
                difficulty=difficulty,
            )
            self._lockouts[lockout_key] = lockout
        lockout.locked_until = _now() + self._config.lockout_duration_hours * 3600.0
        lockout.encounters_defeated = encounters_defeated
        self._log_event(DungeonEventKind.LOCKOUT_SET.value,
                        {"player_id": player_id, "dungeon_id": dungeon_id,
                         "difficulty": difficulty},
                        dungeon_id=dungeon_id, player_id=player_id)

    def check_lockout(self, player_id: str, dungeon_id: str,
                      difficulty: str) -> bool:
        with _LOCK:
            lockout_key = f"{player_id}:{dungeon_id}:{difficulty}"
            lockout = self._lockouts.get(lockout_key)
            if lockout is None:
                return False
            return lockout.locked_until > _now()

    def get_lockout(self, player_id: str, dungeon_id: str,
                    difficulty: str) -> Optional[LockoutEntry]:
        with _LOCK:
            lockout_key = f"{player_id}:{dungeon_id}:{difficulty}"
            return self._lockouts.get(lockout_key)

    def clear_lockout(self, player_id: str, dungeon_id: str,
                      difficulty: str) -> Tuple[bool, str]:
        with _LOCK:
            lockout_key = f"{player_id}:{dungeon_id}:{difficulty}"
            if lockout_key not in self._lockouts:
                return False, "lockout_not_found"
            del self._lockouts[lockout_key]
            self._log_event(DungeonEventKind.LOCKOUT_CLEARED.value,
                            {"player_id": player_id, "dungeon_id": dungeon_id},
                            dungeon_id=dungeon_id, player_id=player_id)
            self._update_stats()
            return True, "cleared"

    # ------------------------------------------------------------------
    # Completion Records
    # ------------------------------------------------------------------

    def get_completion_record(self, record_id: str) -> Optional[CompletionRecord]:
        with _LOCK:
            return self._completions.get(record_id)

    def list_completions(self, player_id: str = "", dungeon_id: str = "",
                         difficulty: str = "") -> List[CompletionRecord]:
        with _LOCK:
            results = list(self._completions.values())
            if player_id:
                results = [c for c in results if player_id in c.player_ids]
            if dungeon_id:
                results = [c for c in results if c.dungeon_id == dungeon_id]
            if difficulty:
                results = [c for c in results if c.difficulty == difficulty]
            return results

    # ------------------------------------------------------------------
    # Difficulty Scaling
    # ------------------------------------------------------------------

    def calculate_difficulty(self, dungeon_id: str, difficulty: str
                             ) -> Optional[Dict[str, float]]:
        with _LOCK:
            dgn = self._dungeons.get(dungeon_id)
            if dgn is None:
                return None
            scales = {
                DungeonDifficulty.NORMAL.value: self._config.difficulty_scale_normal,
                DungeonDifficulty.HEROIC.value: self._config.difficulty_scale_heroic,
                DungeonDifficulty.MYTHIC.value: self._config.difficulty_scale_mythic,
                DungeonDifficulty.ASCENDANT.value: self._config.difficulty_scale_ascendant,
            }
            scale = scales.get(difficulty, 1.0)
            total_bosses = sum(len(w.encounters) for w in dgn.wings)
            return {
                "difficulty": difficulty,
                "health_multiplier": scale,
                "damage_multiplier": scale,
                "total_encounters": total_bosses,
                "estimated_time": total_bosses * 600.0 * scale,
            }

    def scale_encounter(self, encounter: BossEncounter, difficulty: str
                        ) -> Dict[str, float]:
        scales = {
            DungeonDifficulty.NORMAL.value: self._config.difficulty_scale_normal,
            DungeonDifficulty.HEROIC.value: self._config.difficulty_scale_heroic,
            DungeonDifficulty.MYTHIC.value: self._config.difficulty_scale_mythic,
            DungeonDifficulty.ASCENDANT.value: self._config.difficulty_scale_ascendant,
        }
        scale = scales.get(difficulty, 1.0)
        return {
            "encounter_id": encounter.encounter_id,
            "scaled_health": encounter.base_health * scale,
            "scaled_damage": encounter.base_damage * scale,
            "scaled_enrage": encounter.enrage_timer / max(scale, 0.5),
        }

    # ------------------------------------------------------------------
    # Tick / Config / Status
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            for inst in self._instances.values():
                if inst.status == InstanceStatus.ACTIVE.value:
                    inst.elapsed_time += dt
                    if inst.elapsed_time >= inst.time_limit:
                        inst.status = InstanceStatus.FAILED.value
                        inst.completed_at = _now()
                        self._log_event(DungeonEventKind.INSTANCE_FAILED.value,
                                        {"reason": "timeout"},
                                        instance_id=inst.instance_id,
                                        description="time_limit_exceeded")
            if self._tick_count % 60 == 0:
                self._log_event(DungeonEventKind.TICK.value,
                                {"tick": self._tick_count, "dt": dt})
            self._update_stats()
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, DungeonConfig]:
        with _LOCK:
            changed = []
            for k, v in config.items():
                if hasattr(self._config, k):
                    old_val = getattr(self._config, k)
                    setattr(self._config, k, v)
                    changed.append(f"{k}: {old_val}->{v}")
            if changed:
                self._log_event(DungeonEventKind.CONFIG_UPDATED.value,
                                {"changes": changed})
            return True, "updated", self._config

    def get_config(self) -> DungeonConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[DungeonEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> DungeonStats:
        with _LOCK:
            self._update_stats()
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_dungeons": len(self._dungeons),
                "total_instances": len(self._instances),
                "active_instances": sum(
                    1 for i in self._instances.values()
                    if i.status == InstanceStatus.ACTIVE.value
                ),
                "completed_instances": sum(
                    1 for i in self._instances.values()
                    if i.status == InstanceStatus.COMPLETED.value
                ),
                "total_completions": len(self._completions),
                "total_lockouts": len(self._lockouts),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> DungeonSnapshot:
        with _LOCK:
            return DungeonSnapshot(
                dungeons=[d.to_dict() for d in list(self._dungeons.values())[:20]],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> None:
        with _LOCK:
            self._dungeons.clear()
            self._instances.clear()
            self._completions.clear()
            self._lockouts.clear()
            self._events.clear()
            self._stats = DungeonStats()
            self._config = DungeonConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._log_event(DungeonEventKind.RESET.value, {})
            self._seed()


def get_dungeon_instance_system() -> DungeonInstanceSystem:
    """Factory that returns the singleton DungeonInstanceSystem instance."""
    return DungeonInstanceSystem.get_instance()
