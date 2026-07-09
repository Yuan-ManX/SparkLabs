"""
SparkLabs Engine - Raid, Bounty & Expedition System

Provides PvE raid encounters with boss mechanics, bounty hunting contracts,
and expedition adventures. Designed as a self-contained singleton system
with seed data for immediate integration testing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


_MAX_RAIDS = 500
_MAX_BOSSES = 300
_MAX_BOUNTIES = 1000
_MAX_EXPEDITIONS = 500
_MAX_PARTICIPANTS = 2000


def _evict_fifo_list(items: List[Any], max_size: int) -> None:
    while len(items) > max_size:
        items.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if hasattr(val, "to_dict") and callable(val.to_dict):
                result[field_name] = val.to_dict()
            elif isinstance(val, list):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, tuple):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, dict):
                result[field_name] = {k: _dataclass_to_dict(v) for k, v in val.items()}
            else:
                result[field_name] = val
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RaidDifficulty(str, Enum):
    NORMAL = "normal"
    HARD = "hard"
    HEROIC = "heroic"
    MYTHIC = "mythic"


class RaidState(str, Enum):
    SCHEDULED = "scheduled"
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class BossState(str, Enum):
    IDLE = "idle"
    ENGAGED = "engaged"
    DEFEATED = "defeated"
    ENRAGED = "enraged"


class BountyType(str, Enum):
    KILL_TARGET = "kill_target"
    COLLECT_ITEMS = "collect_items"
    CAPTURE_TARGET = "capture_target"
    ESCORT_TARGET = "escort_target"
    SURVIVE_WAVES = "survive_waves"


class BountyStatus(str, Enum):
    AVAILABLE = "available"
    ACCEPTED = "accepted"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"
    CLAIMED = "claimed"


class ExpeditionType(str, Enum):
    SCOUTING = "scouting"
    GATHERING = "gathering"
    COMBAT = "combat"
    DIPLOMATIC = "diplomatic"
    RESCUE = "rescue"
    EXPLORATION = "exploration"


class ExpeditionState(str, Enum):
    PENDING = "pending"
    DEPLOYED = "deployed"
    RETURNED = "returned"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RaidEventKind(str, Enum):
    RAID_CREATED = "raid_created"
    RAID_STARTED = "raid_started"
    RAID_COMPLETED = "raid_completed"
    RAID_FAILED = "raid_failed"
    BOSS_ENGAGED = "boss_engaged"
    BOSS_DEFEATED = "boss_defeated"
    BOSS_ENRAGED = "boss_enraged"
    PLAYER_JOINED = "player_joined"
    PLAYER_LEFT = "player_left"
    BOUNTY_POSTED = "bounty_posted"
    BOUNTY_ACCEPTED = "bounty_accepted"
    BOUNTY_COMPLETED = "bounty_completed"
    BOUNTY_CLAIMED = "bounty_claimed"
    EXPEDITION_LAUNCHED = "expedition_launched"
    EXPEDITION_RETURNED = "expedition_returned"
    EXPEDITION_FAILED = "expedition_failed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class BossMechanic:
    mechanic_id: str
    name: str
    description: str = ""
    trigger_phase: int = 1
    damage_multiplier: float = 1.0
    cooldown_seconds: float = 10.0
    last_triggered: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BossDefinition:
    boss_id: str
    name: str
    max_health: float = 100000.0
    current_health: float = 100000.0
    armor: float = 100.0
    damage: float = 5000.0
    level: int = 50
    state: str = BossState.IDLE.value
    phase: int = 1
    max_phases: int = 3
    enrage_timer: float = 600.0
    mechanics: List[BossMechanic] = field(default_factory=list)
    loot_table: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidParticipant:
    player_id: str
    player_name: str = ""
    role: str = "dps"
    level: int = 50
    joined_at: float = field(default_factory=_now)
    damage_dealt: float = 0.0
    damage_taken: float = 0.0
    healing_done: float = 0.0
    is_alive: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidEncounter:
    raid_id: str
    name: str
    boss_id: str
    difficulty: str = RaidDifficulty.NORMAL.value
    state: str = RaidState.SCHEDULED.value
    max_players: int = 8
    min_players: int = 1
    participants: List[RaidParticipant] = field(default_factory=list)
    scheduled_at: float = field(default_factory=_now)
    started_at: float = 0.0
    ended_at: float = 0.0
    duration: float = 0.0
    attempts: int = 0
    successful: bool = False
    rewards_distributed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BountyContract:
    bounty_id: str
    name: str
    bounty_type: str = BountyType.KILL_TARGET.value
    description: str = ""
    target_name: str = ""
    target_count: int = 1
    current_count: int = 0
    reward_gold: float = 1000.0
    reward_xp: int = 500
    reward_items: List[Dict[str, Any]] = field(default_factory=list)
    status: str = BountyStatus.AVAILABLE.value
    posted_by: str = "system"
    accepted_by: str = ""
    posted_at: float = field(default_factory=_now)
    accepted_at: float = 0.0
    expires_at: float = 0.0
    completed_at: float = 0.0
    difficulty: str = "normal"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ExpeditionMember:
    member_id: str
    name: str = ""
    role: str = "fighter"
    level: int = 50
    health: float = 100.0
    morale: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Expedition:
    expedition_id: str
    name: str
    expedition_type: str = ExpeditionType.SCOUTING.value
    destination: str = ""
    description: str = ""
    state: str = ExpeditionState.PENDING.value
    members: List[ExpeditionMember] = field(default_factory=list)
    max_members: int = 5
    duration_seconds: float = 3600.0
    launched_at: float = 0.0
    return_at: float = 0.0
    success_chance: float = 0.5
    success: bool = False
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    findings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidBountyConfig:
    max_raids: int = 500
    max_bosses: int = 300
    max_bounties: int = 1000
    max_expeditions: int = 500
    max_participants_per_raid: int = 24
    max_members_per_expedition: int = 10
    bounty_expiry_seconds: float = 86400.0
    expedition_tick_rate: float = 1.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidBountyStats:
    total_raids: int = 0
    active_raids: int = 0
    completed_raids: int = 0
    failed_raids: int = 0
    total_bosses: int = 0
    defeated_bosses: int = 0
    total_bounties: int = 0
    active_bounties: int = 0
    completed_bounties: int = 0
    total_expeditions: int = 0
    active_expeditions: int = 0
    completed_expeditions: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidBountySnapshot:
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    raids: List[Dict[str, Any]] = field(default_factory=list)
    bosses: List[Dict[str, Any]] = field(default_factory=list)
    bounties: List[Dict[str, Any]] = field(default_factory=list)
    expeditions: List[Dict[str, Any]] = field(default_factory=list)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RaidEvent:
    event_id: str
    kind: str
    timestamp: float
    raid_id: str = ""
    boss_id: str = ""
    bounty_id: str = ""
    expedition_id: str = ""
    player_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Raid Bounty System
# ---------------------------------------------------------------------------

class RaidBountySystem:
    """Manages PvE raids, boss encounters, bounty contracts, and expeditions."""

    _instance: Optional["RaidBountySystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._bosses: Dict[str, BossDefinition] = {}
        self._raids: Dict[str, RaidEncounter] = {}
        self._bounties: Dict[str, BountyContract] = {}
        self._expeditions: Dict[str, Expedition] = {}
        self._events: List[RaidEvent] = []
        self._stats = RaidBountyStats()
        self._config = RaidBountyConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "RaidBountySystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial bosses, raids, bounties, and expeditions."""
        with self._init_lock:
            if self._initialized:
                return

            # Bosses
            boss1 = BossDefinition(
                boss_id="boss_flame_lord",
                name="Flame Lord Ignar",
                max_health=500000.0,
                current_health=500000.0,
                armor=200.0,
                damage=15000.0,
                level=60,
                state=BossState.IDLE.value,
                phase=1,
                max_phases=3,
                enrage_timer=600.0,
                mechanics=[
                    BossMechanic(
                        mechanic_id="mech_fireball",
                        name="Fireball Volley",
                        description="Rains fireballs on the raid.",
                        trigger_phase=1,
                        damage_multiplier=1.2,
                        cooldown_seconds=15.0,
                    ),
                    BossMechanic(
                        mechanic_id="mech_enrage",
                        name="Berserk",
                        description="Doubles damage when enraged.",
                        trigger_phase=3,
                        damage_multiplier=2.0,
                        cooldown_seconds=0.0,
                    ),
                ],
                loot_table=[
                    {"item_id": "item_flame_crown", "drop_chance": 0.1, "quantity": 1},
                    {"item_id": "item_ember_shard", "drop_chance": 0.5, "quantity": 3},
                ],
            )
            self._bosses[boss1.boss_id] = boss1

            boss2 = BossDefinition(
                boss_id="boss_ice_queen",
                name="Ice Queen Veyra",
                max_health=750000.0,
                current_health=750000.0,
                armor=350.0,
                damage=12000.0,
                level=65,
                state=BossState.IDLE.value,
                phase=1,
                max_phases=4,
                enrage_timer=720.0,
                mechanics=[
                    BossMechanic(
                        mechanic_id="mech_blizzard",
                        name="Eternal Blizzard",
                        description="Slows all raid members.",
                        trigger_phase=2,
                        damage_multiplier=0.8,
                        cooldown_seconds=20.0,
                    ),
                ],
                loot_table=[
                    {"item_id": "item_frost_scepter", "drop_chance": 0.08, "quantity": 1},
                    {"item_id": "item_ice_core", "drop_chance": 0.45, "quantity": 2},
                ],
            )
            self._bosses[boss2.boss_id] = boss2

            boss3 = BossDefinition(
                boss_id="boss_shadow_titan",
                name="Shadow Titan Mor'gul",
                max_health=1200000.0,
                current_health=1200000.0,
                armor=500.0,
                damage=25000.0,
                level=70,
                state=BossState.IDLE.value,
                phase=1,
                max_phases=5,
                enrage_timer=480.0,
                mechanics=[
                    BossMechanic(
                        mechanic_id="mech_void_pull",
                        name="Void Pull",
                        description="Pulls players into the void.",
                        trigger_phase=3,
                        damage_multiplier=1.5,
                        cooldown_seconds=25.0,
                    ),
                ],
                loot_table=[
                    {"item_id": "item_void_blade", "drop_chance": 0.05, "quantity": 1},
                    {"item_id": "item_shadow_essence", "drop_chance": 0.6, "quantity": 5},
                ],
            )
            self._bosses[boss3.boss_id] = boss3

            # Raids
            raid1 = RaidEncounter(
                raid_id="raid_starter_01",
                name="Assault on Flame Peak",
                boss_id="boss_flame_lord",
                difficulty=RaidDifficulty.NORMAL.value,
                state=RaidState.SCHEDULED.value,
                max_players=8,
                min_players=1,
                participants=[
                    RaidParticipant(
                        player_id="player_starter",
                        player_name="Starter Hero",
                        role="tank",
                        level=55,
                    ),
                    RaidParticipant(
                        player_id="player_healer",
                        player_name="Healer Mira",
                        role="healer",
                        level=53,
                    ),
                ],
                scheduled_at=_now(),
            )
            self._raids[raid1.raid_id] = raid1

            raid2 = RaidEncounter(
                raid_id="raid_starter_02",
                name="Frozen Throne Siege",
                boss_id="boss_ice_queen",
                difficulty=RaidDifficulty.HARD.value,
                state=RaidState.COMPLETED.value,
                max_players=10,
                min_players=1,
                participants=[
                    RaidParticipant(
                        player_id="player_starter",
                        player_name="Starter Hero",
                        role="dps",
                        level=62,
                        damage_dealt=250000.0,
                    ),
                ],
                started_at=_now() - 1800.0,
                ended_at=_now() - 600.0,
                duration=1200.0,
                attempts=2,
                successful=True,
                rewards_distributed=True,
            )
            self._raids[raid2.raid_id] = raid2

            # Bounties
            bounty1 = BountyContract(
                bounty_id="bounty_starter_01",
                name="Wanted: Goblin Chief",
                bounty_type=BountyType.KILL_TARGET.value,
                description="Defeat the goblin chief terrorizing the village.",
                target_name="Goblin Chief Grok",
                target_count=1,
                current_count=0,
                reward_gold=1500.0,
                reward_xp=800,
                reward_items=[{"item_id": "item_goblin_ear", "quantity": 1}],
                status=BountyStatus.AVAILABLE.value,
                posted_by="village_elder",
                expires_at=_now() + 86400.0,
                difficulty="normal",
            )
            self._bounties[bounty1.bounty_id] = bounty1

            bounty2 = BountyContract(
                bounty_id="bounty_starter_02",
                bounty_type=BountyType.COLLECT_ITEMS.value,
                name="Herb Collection",
                description="Collect 10 moonpetal herbs for the alchemist.",
                target_name="Moonpetal Herb",
                target_count=10,
                current_count=3,
                reward_gold=500.0,
                reward_xp=300,
                reward_items=[{"item_id": "item_potion_major", "quantity": 5}],
                status=BountyStatus.ACCEPTED.value,
                posted_by="alchemist_zen",
                accepted_by="player_starter",
                posted_at=_now() - 3600.0,
                accepted_at=_now() - 1800.0,
                expires_at=_now() + 64800.0,
                difficulty="easy",
            )
            self._bounties[bounty2.bounty_id] = bounty2

            bounty3 = BountyContract(
                bounty_id="bounty_starter_03",
                name="Escort the Merchant",
                bounty_type=BountyType.ESCORT_TARGET.value,
                description="Escort the merchant caravan safely to the next town.",
                target_name="Merchant Caravan",
                target_count=1,
                current_count=0,
                reward_gold=2500.0,
                reward_xp=1200,
                reward_items=[{"item_id": "item_rare_gem", "quantity": 2}],
                status=BountyStatus.AVAILABLE.value,
                posted_by="merchant_guild",
                expires_at=_now() + 172800.0,
                difficulty="hard",
            )
            self._bounties[bounty3.bounty_id] = bounty3

            # Expeditions
            exp1 = Expedition(
                expedition_id="exp_starter_01",
                name="Northern Reconnaissance",
                expedition_type=ExpeditionType.SCOUTING.value,
                destination="Northern Wastes",
                description="Scout the northern wastes for enemy activity.",
                state=ExpeditionState.PENDING.value,
                members=[
                    ExpeditionMember(
                        member_id="member_scout_01",
                        name="Scout Rina",
                        role="scout",
                        level=40,
                    ),
                ],
                max_members=5,
                duration_seconds=1800.0,
                success_chance=0.75,
            )
            self._expeditions[exp1.expedition_id] = exp1

            exp2 = Expedition(
                expedition_id="exp_starter_02",
                name="Lost Mine Expedition",
                expedition_type=ExpeditionType.GATHERING.value,
                destination="Abandoned Mine",
                description="Explore the abandoned mine for rare ores.",
                state=ExpeditionState.RETURNED.value,
                members=[
                    ExpeditionMember(
                        member_id="member_miner_01",
                        name="Miner Dorin",
                        role="gatherer",
                        level=45,
                    ),
                    ExpeditionMember(
                        member_id="member_guard_01",
                        name="Guard Kael",
                        role="fighter",
                        level=48,
                    ),
                ],
                max_members=5,
                duration_seconds=3600.0,
                launched_at=_now() - 7200.0,
                return_at=_now() - 3600.0,
                success_chance=0.6,
                success=True,
                rewards=[
                    {"item_id": "item_gold_ore", "quantity": 20},
                    {"item_id": "item_rare_gem", "quantity": 3},
                ],
                findings=["Hidden chamber", "Ancient map fragment"],
            )
            self._expeditions[exp2.expedition_id] = exp2

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_raids = len(self._raids)
        self._stats.active_raids = sum(
            1 for r in self._raids.values() if r.state == RaidState.ACTIVE.value
        )
        self._stats.completed_raids = sum(
            1 for r in self._raids.values() if r.state == RaidState.COMPLETED.value
        )
        self._stats.failed_raids = sum(
            1 for r in self._raids.values() if r.state == RaidState.FAILED.value
        )
        self._stats.total_bosses = len(self._bosses)
        self._stats.defeated_bosses = sum(
            1 for b in self._bosses.values() if b.state == BossState.DEFEATED.value
        )
        self._stats.total_bounties = len(self._bounties)
        self._stats.active_bounties = sum(
            1
            for b in self._bounties.values()
            if b.status in (BountyStatus.AVAILABLE.value, BountyStatus.ACCEPTED.value)
        )
        self._stats.completed_bounties = sum(
            1
            for b in self._bounties.values()
            if b.status in (BountyStatus.COMPLETED.value, BountyStatus.CLAIMED.value)
        )
        self._stats.total_expeditions = len(self._expeditions)
        self._stats.active_expeditions = sum(
            1 for e in self._expeditions.values() if e.state == ExpeditionState.DEPLOYED.value
        )
        self._stats.completed_expeditions = sum(
            1 for e in self._expeditions.values() if e.state == ExpeditionState.RETURNED.value
        )
        self._stats.tick_count = self._tick_count

    def _record_event(
        self,
        kind: str,
        raid_id: str = "",
        boss_id: str = "",
        bounty_id: str = "",
        expedition_id: str = "",
        player_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> RaidEvent:
        """Record an audit event."""
        self._event_counter += 1
        event = RaidEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            raid_id=raid_id,
            boss_id=boss_id,
            bounty_id=bounty_id,
            expedition_id=expedition_id,
            player_id=player_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, 5000)
        return event

    # ------------------------------------------------------------------
    # Boss Management
    # ------------------------------------------------------------------

    def register_boss(
        self,
        boss_id: str,
        name: str,
        max_health: float = 100000.0,
        armor: float = 100.0,
        damage: float = 5000.0,
        level: int = 50,
        max_phases: int = 3,
        enrage_timer: float = 600.0,
        mechanics: Optional[List[Dict[str, Any]]] = None,
        loot_table: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BossDefinition]]:
        """Register a new boss definition."""
        if not boss_id or not name:
            return False, "boss_id and name required", None
        if boss_id in self._bosses:
            return False, "boss_id already exists", None
        if len(self._bosses) >= _MAX_BOSSES:
            return False, "boss capacity reached", None
        boss = BossDefinition(
            boss_id=boss_id,
            name=name,
            max_health=_safe_float(max_health, 100000.0),
            current_health=_safe_float(max_health, 100000.0),
            armor=_safe_float(armor, 100.0),
            damage=_safe_float(damage, 5000.0),
            level=_safe_int(level, 50),
            state=BossState.IDLE.value,
            phase=1,
            max_phases=_safe_int(max_phases, 3),
            enrage_timer=_safe_float(enrage_timer, 600.0),
            mechanics=[
                BossMechanic(
                    mechanic_id=m.get("mechanic_id", _new_id("mech")),
                    name=m.get("name", ""),
                    description=m.get("description", ""),
                    trigger_phase=_safe_int(m.get("trigger_phase"), 1),
                    damage_multiplier=_safe_float(m.get("damage_multiplier"), 1.0),
                    cooldown_seconds=_safe_float(m.get("cooldown_seconds"), 10.0),
                )
                for m in (mechanics or [])
            ],
            loot_table=loot_table or [],
            metadata=metadata or {},
        )
        self._bosses[boss_id] = boss
        self._refresh_stats()
        self._record_event(
            RaidEventKind.BOSS_ENGAGED.value,
            boss_id=boss_id,
            description=f"Boss registered: {name}",
        )
        return True, "registered", boss

    def remove_boss(self, boss_id: str) -> Tuple[bool, str]:
        """Remove a boss definition."""
        if boss_id not in self._bosses:
            return False, "not_found"
        del self._bosses[boss_id]
        self._refresh_stats()
        self._record_event(
            RaidEventKind.RESET.value,
            boss_id=boss_id,
            description=f"Boss removed: {boss_id}",
        )
        return True, "removed"

    def get_boss(self, boss_id: str) -> Optional[BossDefinition]:
        """Get a boss definition by ID."""
        return self._bosses.get(boss_id)

    def list_bosses(
        self, state: Optional[str] = None, limit: int = 100
    ) -> List[BossDefinition]:
        """List bosses optionally filtered by state."""
        bosses = list(self._bosses.values())
        if state:
            bosses = [b for b in bosses if b.state == state]
        return bosses[:limit]

    def engage_boss(self, boss_id: str) -> Tuple[bool, str, Optional[BossDefinition]]:
        """Engage a boss, transitioning it to ENGAGED state."""
        boss = self._bosses.get(boss_id)
        if boss is None:
            return False, "not_found", None
        if boss.state == BossState.DEFEATED.value:
            return False, "already_defeated", None
        if boss.state == BossState.ENGAGED.value:
            return False, "already_engaged", None
        boss.state = BossState.ENGAGED.value
        boss.current_health = boss.max_health
        boss.phase = 1
        self._record_event(
            RaidEventKind.BOSS_ENGAGED.value,
            boss_id=boss_id,
            description=f"Boss engaged: {boss.name}",
        )
        return True, "engaged", boss

    def damage_boss(
        self, boss_id: str, damage: float, player_id: str = ""
    ) -> Tuple[bool, str, Optional[BossDefinition]]:
        """Apply damage to a boss and advance phases."""
        boss = self._bosses.get(boss_id)
        if boss is None:
            return False, "not_found", None
        if boss.state != BossState.ENGAGED.value:
            return False, "not_engaged", None
        dmg = max(0.0, _safe_float(damage, 0.0))
        boss.current_health = max(0.0, boss.current_health - dmg)
        # Advance phase based on health percentage
        health_pct = boss.current_health / boss.max_health if boss.max_health > 0 else 0.0
        new_phase = min(
            boss.max_phases,
            max(1, int((1.0 - health_pct) * boss.max_phases) + 1),
        )
        if new_phase > boss.phase:
            boss.phase = new_phase
        if boss.current_health <= 0:
            return self.defeat_boss(boss_id, player_id=player_id)
        self._record_event(
            RaidEventKind.TICK.value,
            boss_id=boss_id,
            player_id=player_id,
            description=f"Boss damaged for {dmg}",
            details={"damage": dmg, "remaining": boss.current_health},
        )
        return True, "damaged", boss

    def defeat_boss(
        self, boss_id: str, player_id: str = ""
    ) -> Tuple[bool, str, Optional[BossDefinition]]:
        """Mark a boss as defeated."""
        boss = self._bosses.get(boss_id)
        if boss is None:
            return False, "not_found", None
        if boss.state == BossState.DEFEATED.value:
            return False, "already_defeated", None
        boss.state = BossState.DEFEATED.value
        boss.current_health = 0.0
        self._refresh_stats()
        self._record_event(
            RaidEventKind.BOSS_DEFEATED.value,
            boss_id=boss_id,
            player_id=player_id,
            description=f"Boss defeated: {boss.name}",
        )
        return True, "defeated", boss

    def enrage_boss(self, boss_id: str) -> Tuple[bool, str, Optional[BossDefinition]]:
        """Enrage a boss, doubling its damage."""
        boss = self._bosses.get(boss_id)
        if boss is None:
            return False, "not_found", None
        if boss.state == BossState.DEFEATED.value:
            return False, "already_defeated", None
        boss.state = BossState.ENRAGED.value
        boss.damage *= 2.0
        self._record_event(
            RaidEventKind.BOSS_ENRAGED.value,
            boss_id=boss_id,
            description=f"Boss enraged: {boss.name}",
        )
        return True, "enraged", boss

    # ------------------------------------------------------------------
    # Raid Management
    # ------------------------------------------------------------------

    def register_raid(
        self,
        raid_id: str,
        name: str,
        boss_id: str,
        difficulty: str = RaidDifficulty.NORMAL.value,
        max_players: int = 8,
        min_players: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[RaidEncounter]]:
        """Register a new raid encounter."""
        if not raid_id or not name or not boss_id:
            return False, "raid_id, name, and boss_id required", None
        if raid_id in self._raids:
            return False, "raid_id already exists", None
        if len(self._raids) >= _MAX_RAIDS:
            return False, "raid capacity reached", None
        raid = RaidEncounter(
            raid_id=raid_id,
            name=name,
            boss_id=boss_id,
            difficulty=difficulty,
            state=RaidState.SCHEDULED.value,
            max_players=_safe_int(max_players, 8),
            min_players=_safe_int(min_players, 1),
            metadata=metadata or {},
        )
        self._raids[raid_id] = raid
        self._refresh_stats()
        self._record_event(
            RaidEventKind.RAID_CREATED.value,
            raid_id=raid_id,
            boss_id=boss_id,
            description=f"Raid created: {name}",
        )
        return True, "registered", raid

    def remove_raid(self, raid_id: str) -> Tuple[bool, str]:
        """Remove a raid encounter."""
        if raid_id not in self._raids:
            return False, "not_found"
        del self._raids[raid_id]
        self._refresh_stats()
        return True, "removed"

    def get_raid(self, raid_id: str) -> Optional[RaidEncounter]:
        """Get a raid encounter by ID."""
        return self._raids.get(raid_id)

    def list_raids(
        self, state: Optional[str] = None, limit: int = 100
    ) -> List[RaidEncounter]:
        """List raids optionally filtered by state."""
        raids = list(self._raids.values())
        if state:
            raids = [r for r in raids if r.state == state]
        return raids[:limit]

    def join_raid(
        self,
        raid_id: str,
        player_id: str,
        player_name: str = "",
        role: str = "dps",
        level: int = 50,
    ) -> Tuple[bool, str, Optional[RaidEncounter]]:
        """Add a participant to a raid."""
        raid = self._raids.get(raid_id)
        if raid is None:
            return False, "not_found", None
        if raid.state not in (RaidState.SCHEDULED.value, RaidState.FORMING.value):
            return False, "raid_not_open", None
        if len(raid.participants) >= raid.max_players:
            return False, "raid_full", None
        if any(p.player_id == player_id for p in raid.participants):
            return False, "already_joined", None
        if raid.state == RaidState.SCHEDULED.value:
            raid.state = RaidState.FORMING.value
        participant = RaidParticipant(
            player_id=player_id,
            player_name=player_name,
            role=role,
            level=_safe_int(level, 50),
        )
        raid.participants.append(participant)
        self._refresh_stats()
        self._record_event(
            RaidEventKind.PLAYER_JOINED.value,
            raid_id=raid_id,
            player_id=player_id,
            description=f"Player joined raid: {player_id}",
        )
        return True, "joined", raid

    def leave_raid(
        self, raid_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[RaidEncounter]]:
        """Remove a participant from a raid."""
        raid = self._raids.get(raid_id)
        if raid is None:
            return False, "not_found", None
        idx = -1
        for i, p in enumerate(raid.participants):
            if p.player_id == player_id:
                idx = i
                break
        if idx < 0:
            return False, "player_not_in_raid", None
        raid.participants.pop(idx)
        self._record_event(
            RaidEventKind.PLAYER_LEFT.value,
            raid_id=raid_id,
            player_id=player_id,
            description=f"Player left raid: {player_id}",
        )
        return True, "left", raid

    def start_raid(self, raid_id: str) -> Tuple[bool, str, Optional[RaidEncounter]]:
        """Start a raid encounter, engaging the boss."""
        raid = self._raids.get(raid_id)
        if raid is None:
            return False, "not_found", None
        if raid.state != RaidState.FORMING.value and raid.state != RaidState.SCHEDULED.value:
            return False, "not_forming", None
        if len(raid.participants) < raid.min_players:
            return False, "not_enough_players", None
        raid.state = RaidState.ACTIVE.value
        raid.started_at = _now()
        # Engage the boss
        boss = self._bosses.get(raid.boss_id)
        if boss is not None and boss.state == BossState.IDLE.value:
            boss.state = BossState.ENGAGED.value
            boss.current_health = boss.max_health
        self._refresh_stats()
        self._record_event(
            RaidEventKind.RAID_STARTED.value,
            raid_id=raid_id,
            boss_id=raid.boss_id,
            description=f"Raid started: {raid.name}",
        )
        return True, "started", raid

    def end_raid(
        self, raid_id: str, successful: bool = True
    ) -> Tuple[bool, str, Optional[RaidEncounter]]:
        """End a raid encounter."""
        raid = self._raids.get(raid_id)
        if raid is None:
            return False, "not_found", None
        if raid.state != RaidState.ACTIVE.value:
            return False, "not_active", None
        raid.state = RaidState.COMPLETED.value if successful else RaidState.FAILED.value
        raid.ended_at = _now()
        raid.duration = raid.ended_at - raid.started_at
        raid.successful = successful
        raid.attempts += 1
        if successful:
            boss = self._bosses.get(raid.boss_id)
            if boss is not None and boss.state != BossState.DEFEATED.value:
                boss.state = BossState.DEFEATED.value
                boss.current_health = 0.0
        self._refresh_stats()
        self._record_event(
            RaidEventKind.RAID_COMPLETED.value if successful else RaidEventKind.RAID_FAILED.value,
            raid_id=raid_id,
            boss_id=raid.boss_id,
            description=f"Raid {'completed' if successful else 'failed'}: {raid.name}",
            details={"successful": successful, "duration": raid.duration},
        )
        return True, "ended", raid

    # ------------------------------------------------------------------
    # Bounty Management
    # ------------------------------------------------------------------

    def post_bounty(
        self,
        bounty_id: str,
        name: str,
        bounty_type: str = BountyType.KILL_TARGET.value,
        description: str = "",
        target_name: str = "",
        target_count: int = 1,
        reward_gold: float = 1000.0,
        reward_xp: int = 500,
        reward_items: Optional[List[Dict[str, Any]]] = None,
        posted_by: str = "system",
        expires_at: float = 0.0,
        difficulty: str = "normal",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BountyContract]]:
        """Post a new bounty contract."""
        if not bounty_id or not name:
            return False, "bounty_id and name required", None
        if bounty_id in self._bounties:
            return False, "bounty_id already exists", None
        if len(self._bounties) >= _MAX_BOUNTIES:
            return False, "bounty capacity reached", None
        bounty = BountyContract(
            bounty_id=bounty_id,
            name=name,
            bounty_type=bounty_type,
            description=description,
            target_name=target_name,
            target_count=_safe_int(target_count, 1),
            current_count=0,
            reward_gold=_safe_float(reward_gold, 1000.0),
            reward_xp=_safe_int(reward_xp, 500),
            reward_items=reward_items or [],
            status=BountyStatus.AVAILABLE.value,
            posted_by=posted_by,
            expires_at=expires_at if expires_at > 0 else _now() + 86400.0,
            difficulty=difficulty,
            metadata=metadata or {},
        )
        self._bounties[bounty_id] = bounty
        self._refresh_stats()
        self._record_event(
            RaidEventKind.BOUNTY_POSTED.value,
            bounty_id=bounty_id,
            description=f"Bounty posted: {name}",
        )
        return True, "posted", bounty

    def remove_bounty(self, bounty_id: str) -> Tuple[bool, str]:
        """Remove a bounty contract."""
        if bounty_id not in self._bounties:
            return False, "not_found"
        del self._bounties[bounty_id]
        self._refresh_stats()
        return True, "removed"

    def get_bounty(self, bounty_id: str) -> Optional[BountyContract]:
        """Get a bounty contract by ID."""
        return self._bounties.get(bounty_id)

    def list_bounties(
        self, status: Optional[str] = None, limit: int = 100
    ) -> List[BountyContract]:
        """List bounties optionally filtered by status."""
        bounties = list(self._bounties.values())
        if status:
            bounties = [b for b in bounties if b.status == status]
        return bounties[:limit]

    def accept_bounty(
        self, bounty_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[BountyContract]]:
        """Accept a bounty contract."""
        bounty = self._bounties.get(bounty_id)
        if bounty is None:
            return False, "not_found", None
        if bounty.status != BountyStatus.AVAILABLE.value:
            return False, "not_available", None
        bounty.status = BountyStatus.ACCEPTED.value
        bounty.accepted_by = player_id
        bounty.accepted_at = _now()
        self._record_event(
            RaidEventKind.BOUNTY_ACCEPTED.value,
            bounty_id=bounty_id,
            player_id=player_id,
            description=f"Bounty accepted: {bounty.name}",
        )
        return True, "accepted", bounty

    def update_bounty_progress(
        self, bounty_id: str, count: int
    ) -> Tuple[bool, str, Optional[BountyContract]]:
        """Update bounty progress count."""
        bounty = self._bounties.get(bounty_id)
        if bounty is None:
            return False, "not_found", None
        if bounty.status != BountyStatus.ACCEPTED.value:
            return False, "not_accepted", None
        bounty.current_count = max(0, _safe_int(count, 0))
        if bounty.current_count >= bounty.target_count:
            bounty.status = BountyStatus.COMPLETED.value
            bounty.completed_at = _now()
        return True, "updated", bounty

    def complete_bounty(
        self, bounty_id: str
    ) -> Tuple[bool, str, Optional[BountyContract]]:
        """Mark a bounty as completed."""
        bounty = self._bounties.get(bounty_id)
        if bounty is None:
            return False, "not_found", None
        if bounty.status != BountyStatus.ACCEPTED.value:
            return False, "not_accepted", None
        bounty.status = BountyStatus.COMPLETED.value
        bounty.current_count = bounty.target_count
        bounty.completed_at = _now()
        self._refresh_stats()
        self._record_event(
            RaidEventKind.BOUNTY_COMPLETED.value,
            bounty_id=bounty_id,
            player_id=bounty.accepted_by,
            description=f"Bounty completed: {bounty.name}",
        )
        return True, "completed", bounty

    def claim_bounty(
        self, bounty_id: str
    ) -> Tuple[bool, str, Optional[BountyContract]]:
        """Claim rewards for a completed bounty."""
        bounty = self._bounties.get(bounty_id)
        if bounty is None:
            return False, "not_found", None
        if bounty.status != BountyStatus.COMPLETED.value:
            return False, "not_completed", None
        bounty.status = BountyStatus.CLAIMED.value
        self._refresh_stats()
        self._record_event(
            RaidEventKind.BOUNTY_CLAIMED.value,
            bounty_id=bounty_id,
            player_id=bounty.accepted_by,
            description=f"Bounty claimed: {bounty.name}",
            details={
                "reward_gold": bounty.reward_gold,
                "reward_xp": bounty.reward_xp,
            },
        )
        return True, "claimed", bounty

    # ------------------------------------------------------------------
    # Expedition Management
    # ------------------------------------------------------------------

    def register_expedition(
        self,
        expedition_id: str,
        name: str,
        expedition_type: str = ExpeditionType.SCOUTING.value,
        destination: str = "",
        description: str = "",
        max_members: int = 5,
        duration_seconds: float = 3600.0,
        success_chance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Expedition]]:
        """Register a new expedition."""
        if not expedition_id or not name:
            return False, "expedition_id and name required", None
        if expedition_id in self._expeditions:
            return False, "expedition_id already exists", None
        if len(self._expeditions) >= _MAX_EXPEDITIONS:
            return False, "expedition capacity reached", None
        expedition = Expedition(
            expedition_id=expedition_id,
            name=name,
            expedition_type=expedition_type,
            destination=destination,
            description=description,
            state=ExpeditionState.PENDING.value,
            max_members=_safe_int(max_members, 5),
            duration_seconds=_safe_float(duration_seconds, 3600.0),
            success_chance=_clamp(_safe_float(success_chance, 0.5), 0.0, 1.0),
            metadata=metadata or {},
        )
        self._expeditions[expedition_id] = expedition
        self._refresh_stats()
        self._record_event(
            RaidEventKind.EXPEDITION_LAUNCHED.value,
            expedition_id=expedition_id,
            description=f"Expedition registered: {name}",
        )
        return True, "registered", expedition

    def remove_expedition(self, expedition_id: str) -> Tuple[bool, str]:
        """Remove an expedition."""
        if expedition_id not in self._expeditions:
            return False, "not_found"
        del self._expeditions[expedition_id]
        self._refresh_stats()
        return True, "removed"

    def get_expedition(self, expedition_id: str) -> Optional[Expedition]:
        """Get an expedition by ID."""
        return self._expeditions.get(expedition_id)

    def list_expeditions(
        self, state: Optional[str] = None, limit: int = 100
    ) -> List[Expedition]:
        """List expeditions optionally filtered by state."""
        expeditions = list(self._expeditions.values())
        if state:
            expeditions = [e for e in expeditions if e.state == state]
        return expeditions[:limit]

    def add_member(
        self,
        expedition_id: str,
        member_id: str,
        name: str = "",
        role: str = "fighter",
        level: int = 50,
    ) -> Tuple[bool, str, Optional[Expedition]]:
        """Add a member to an expedition."""
        expedition = self._expeditions.get(expedition_id)
        if expedition is None:
            return False, "not_found", None
        if expedition.state != ExpeditionState.PENDING.value:
            return False, "not_pending", None
        if len(expedition.members) >= expedition.max_members:
            return False, "full", None
        if any(m.member_id == member_id for m in expedition.members):
            return False, "already_member", None
        member = ExpeditionMember(
            member_id=member_id,
            name=name,
            role=role,
            level=_safe_int(level, 50),
        )
        expedition.members.append(member)
        return True, "added", expedition

    def remove_member(
        self, expedition_id: str, member_id: str
    ) -> Tuple[bool, str, Optional[Expedition]]:
        """Remove a member from an expedition."""
        expedition = self._expeditions.get(expedition_id)
        if expedition is None:
            return False, "not_found", None
        idx = -1
        for i, m in enumerate(expedition.members):
            if m.member_id == member_id:
                idx = i
                break
        if idx < 0:
            return False, "member_not_found", None
        expedition.members.pop(idx)
        return True, "removed", expedition

    def launch_expedition(
        self, expedition_id: str
    ) -> Tuple[bool, str, Optional[Expedition]]:
        """Launch a pending expedition."""
        expedition = self._expeditions.get(expedition_id)
        if expedition is None:
            return False, "not_found", None
        if expedition.state != ExpeditionState.PENDING.value:
            return False, "not_pending", None
        if not expedition.members:
            return False, "no_members", None
        expedition.state = ExpeditionState.DEPLOYED.value
        expedition.launched_at = _now()
        expedition.return_at = _now() + expedition.duration_seconds
        self._refresh_stats()
        self._record_event(
            RaidEventKind.EXPEDITION_LAUNCHED.value,
            expedition_id=expedition_id,
            description=f"Expedition launched: {expedition.name}",
        )
        return True, "launched", expedition

    def return_expedition(
        self, expedition_id: str, success: Optional[bool] = None
    ) -> Tuple[bool, str, Optional[Expedition]]:
        """Return a deployed expedition."""
        expedition = self._expeditions.get(expedition_id)
        if expedition is None:
            return False, "not_found", None
        if expedition.state != ExpeditionState.DEPLOYED.value:
            return False, "not_deployed", None
        if success is None:
            # Determine success based on success_chance
            import random
            success = random.random() < expedition.success_chance
        expedition.state = ExpeditionState.RETURNED.value if success else ExpeditionState.FAILED.value
        expedition.success = success
        if success:
            expedition.rewards = [
                {"item_id": "item_exploration_reward", "quantity": 1},
                {"item_id": "item_gold_pouch", "quantity": 1},
            ]
            expedition.findings.append(f"Returned successfully at tick {self._tick_count}")
        self._refresh_stats()
        self._record_event(
            RaidEventKind.EXPEDITION_RETURNED.value if success else RaidEventKind.EXPEDITION_FAILED.value,
            expedition_id=expedition_id,
            description=f"Expedition {'returned' if success else 'failed'}: {expedition.name}",
            details={"success": success},
        )
        return True, "returned" if success else "failed", expedition

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats, Status, Snapshot, Reset
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the simulation by dt seconds."""
        self._tick_count += 1
        now = _now()
        # Check for expeditions that should auto-return
        for expedition in self._expeditions.values():
            if (
                expedition.state == ExpeditionState.DEPLOYED.value
                and expedition.return_at > 0
                and now >= expedition.return_at
            ):
                self.return_expedition(expedition.expedition_id)
        # Check for expired bounties
        for bounty in self._bounties.values():
            if (
                bounty.status in (BountyStatus.AVAILABLE.value, BountyStatus.ACCEPTED.value)
                and bounty.expires_at > 0
                and now >= bounty.expires_at
            ):
                bounty.status = BountyStatus.EXPIRED.value
        self._refresh_stats()
        self._record_event(
            RaidEventKind.TICK.value,
            description=f"Tick {self._tick_count}",
            details={"dt": dt, "tick_count": self._tick_count},
        )
        return {
            "tick_count": self._tick_count,
            "active_raids": self._stats.active_raids,
            "active_expeditions": self._stats.active_expeditions,
        }

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, RaidBountyConfig]:
        """Update configuration parameters."""
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        self._record_event(
            RaidEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
            details=kwargs,
        )
        return True, "updated", self._config

    def get_config(self) -> RaidBountyConfig:
        """Get current configuration."""
        return self._config

    def list_events(
        self, kind: Optional[str] = None, limit: int = 100
    ) -> List[RaidEvent]:
        """List events optionally filtered by kind."""
        events = list(self._events)
        if kind:
            events = [e for e in events if e.kind == kind]
        return events[-limit:]

    def get_stats(self) -> RaidBountyStats:
        """Get aggregate statistics."""
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Get system status summary."""
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_bosses": len(self._bosses),
            "total_raids": len(self._raids),
            "total_bounties": len(self._bounties),
            "total_expeditions": len(self._expeditions),
            "active_raids": self._stats.active_raids,
            "active_bounties": self._stats.active_bounties,
            "active_expeditions": self._stats.active_expeditions,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> RaidBountySnapshot:
        """Get full state snapshot."""
        self._refresh_stats()
        return RaidBountySnapshot(
            config=self._config.to_dict(),
            stats=self._stats.to_dict(),
            raids=[r.to_dict() for r in list(self._raids.values())[:50]],
            bosses=[b.to_dict() for b in list(self._bosses.values())[:50]],
            bounties=[b.to_dict() for b in list(self._bounties.values())[:50]],
            expeditions=[e.to_dict() for e in list(self._expeditions.values())[:50]],
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        """Reset the system to seed state."""
        with self._init_lock:
            self._bosses.clear()
            self._raids.clear()
            self._bounties.clear()
            self._expeditions.clear()
            self._events.clear()
            self._stats = RaidBountyStats()
            self._config = RaidBountyConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            RaidEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_raid_bounty_system() -> RaidBountySystem:
    """Factory function to get the RaidBountySystem singleton instance."""
    return RaidBountySystem.get_instance()
