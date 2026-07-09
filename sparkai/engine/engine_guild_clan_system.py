"""
SparkLabs Engine - Guild & Clan System

Provides guild creation, member management with ranks and permissions,
guild treasury, guild wars, guild quests, and guild perks. Designed as a
self-contained singleton system with seed data for immediate integration testing.
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


_MAX_GUILDS = 500
_MAX_MEMBERS_PER_GUILD = 200
_MAX_GUILD_WARS = 100
_MAX_GUILD_QUESTS = 500
_MAX_TREASURY_ENTRIES = 1000
_MAX_PERKS = 200


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

class GuildRank(str, Enum):
    LEADER = "leader"
    OFFICER = "officer"
    VETERAN = "veteran"
    MEMBER = "member"
    RECRUIT = "recruit"


class GuildPermission(str, Enum):
    INVITE = "invite"
    KICK = "kick"
    PROMOTE = "promote"
    DEMOTE = "demote"
    TREASURY_DEPOSIT = "treasury_deposit"
    TREASURY_WITHDRAW = "treasury_withdraw"
    DECLARE_WAR = "declare_war"
    ACCEPT_QUEST = "accept_quest"
    MANAGE_PERKS = "manage_perks"
    EDIT_INFO = "edit_info"


class GuildState(str, Enum):
    ACTIVE = "active"
    DISBANDED = "disbanded"
    SUSPENDED = "suspended"


class GuildWarState(str, Enum):
    DECLARED = "declared"
    ACTIVE = "active"
    ENDED = "ended"
    CANCELLED = "cancelled"


class GuildWarOutcome(str, Enum):
    PENDING = "pending"
    ATTACKER_WIN = "attacker_win"
    DEFENDER_WIN = "defender_win"
    DRAW = "draw"


class GuildQuestStatus(str, Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"
    CLAIMED = "claimed"


class GuildQuestType(str, Enum):
    KILL_BOSSES = "kill_bosses"
    GATHER_RESOURCES = "gather_resources"
    WIN_PVP = "win_pvp"
    COMPLETE_DUNGEONS = "complete_dungeons"
    DONATE_GOLD = "donate_gold"
    RECRUIT_MEMBERS = "recruit_members"


class TreasuryEntryType(str, Enum):
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    QUEST_REWARD = "quest_reward"
    WAR_PLUNDER = "war_plunder"
    DONATION = "donation"


class GuildEventKind(str, Enum):
    GUILD_CREATED = "guild_created"
    GUILD_DISBANDED = "guild_disbanded"
    MEMBER_JOINED = "member_joined"
    MEMBER_LEFT = "member_left"
    MEMBER_KICKED = "member_kicked"
    MEMBER_PROMOTED = "member_promoted"
    MEMBER_DEMOTED = "member_demoted"
    TREASURY_DEPOSIT = "treasury_deposit"
    TREASURY_WITHDRAW = "treasury_withdraw"
    WAR_DECLARED = "war_declared"
    WAR_ENDED = "war_ended"
    QUEST_ACCEPTED = "quest_accepted"
    QUEST_COMPLETED = "quest_completed"
    QUEST_CLAIMED = "quest_claimed"
    PERK_ACTIVATED = "perk_activated"
    PERK_DEACTIVATED = "perk_deactivated"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class GuildRankDefinition:
    rank_id: str
    name: str
    level: int = 0
    permissions: List[str] = field(default_factory=list)
    can_manage_ranks: bool = False
    max_members: int = 999

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildMember:
    player_id: str
    player_name: str = ""
    rank: str = GuildRank.MEMBER.value
    joined_at: float = field(default_factory=_now)
    contribution: float = 0.0
    last_active: float = field(default_factory=_now)
    weekly_contribution: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TreasuryEntry:
    entry_id: str
    entry_type: str = TreasuryEntryType.DEPOSIT.value
    player_id: str = ""
    currency: str = "gold"
    amount: float = 0.0
    item_id: str = ""
    item_quantity: int = 0
    description: str = ""
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildQuest:
    quest_id: str
    name: str
    quest_type: str = GuildQuestType.KILL_BOSSES.value
    description: str = ""
    target_count: int = 10
    current_count: int = 0
    reward_gold: float = 5000.0
    reward_xp: int = 2000
    reward_guild_xp: int = 1000
    reward_items: List[Dict[str, Any]] = field(default_factory=list)
    status: str = GuildQuestStatus.AVAILABLE.value
    difficulty: str = "normal"
    duration_seconds: float = 86400.0
    accepted_at: float = 0.0
    completed_at: float = 0.0
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildWarParticipant:
    guild_id: str
    guild_name: str = ""
    score: float = 0.0
    kills: int = 0
    deaths: int = 0
    objectives: int = 0
    is_attacker: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildWar:
    war_id: str
    attacker_id: str
    defender_id: str
    state: str = GuildWarState.DECLARED.value
    outcome: str = GuildWarOutcome.PENDING.value
    participants: List[GuildWarParticipant] = field(default_factory=list)
    declared_at: float = field(default_factory=_now)
    started_at: float = 0.0
    ended_at: float = 0.0
    duration_seconds: float = 3600.0
    stakes_gold: float = 10000.0
    winner_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildPerk:
    perk_id: str
    name: str
    description: str = ""
    perk_type: str = "passive"
    effect_value: float = 0.0
    duration_seconds: float = 0.0
    cost_gold: float = 1000.0
    required_guild_level: int = 1
    activated: bool = False
    activated_at: float = 0.0
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildDefinition:
    guild_id: str
    name: str
    tag: str = ""
    description: str = ""
    leader_id: str = ""
    state: str = GuildState.ACTIVE.value
    level: int = 1
    experience: float = 0.0
    members: List[GuildMember] = field(default_factory=list)
    treasury_balance: Dict[str, float] = field(default_factory=dict)
    treasury_entries: List[TreasuryEntry] = field(default_factory=list)
    quests: List[GuildQuest] = field(default_factory=list)
    active_wars: List[str] = field(default_factory=list)
    perks: List[GuildPerk] = field(default_factory=list)
    rank_definitions: List[GuildRankDefinition] = field(default_factory=list)
    created_at: float = field(default_factory=_now)
    motd: str = ""
    emblem: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildClanConfig:
    max_guilds: int = 500
    max_members_per_guild: int = 200
    max_wars: int = 100
    max_quests: int = 500
    max_treasury_entries: int = 1000
    max_perks: int = 200
    war_duration_seconds: float = 3600.0
    quest_expiry_seconds: float = 86400.0
    guild_xp_per_level: float = 10000.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildClanStats:
    total_guilds: int = 0
    active_guilds: int = 0
    disbanded_guilds: int = 0
    total_members: int = 0
    total_wars: int = 0
    active_wars: int = 0
    total_quests: int = 0
    active_quests: int = 0
    completed_quests: int = 0
    total_treasury_volume: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildClanSnapshot:
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    guilds: List[Dict[str, Any]] = field(default_factory=list)
    wars: List[Dict[str, Any]] = field(default_factory=list)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GuildEvent:
    event_id: str
    kind: str
    timestamp: float
    guild_id: str = ""
    player_id: str = ""
    war_id: str = ""
    quest_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

# ---------------------------------------------------------------------------
# Guild Clan System
# ---------------------------------------------------------------------------

class GuildClanSystem:
    """Manages guilds, clans, member management, treasury, wars, quests, and perks."""

    _instance: Optional["GuildClanSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._guilds: Dict[str, GuildDefinition] = {}
        self._wars: Dict[str, GuildWar] = {}
        self._events: List[GuildEvent] = []
        self._stats = GuildClanStats()
        self._config = GuildClanConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._war_counter: int = 0
        self._quest_counter: int = 0
        self._treasury_counter: int = 0
        self._perk_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "GuildClanSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial guilds, wars, quests, and perks."""
        with self._init_lock:
            if self._initialized:
                return

            default_ranks = [
                GuildRankDefinition(
                    rank_id="rank_leader",
                    name="Guild Leader",
                    level=5,
                    permissions=[p.value for p in GuildPermission],
                    can_manage_ranks=True,
                    max_members=1,
                ),
                GuildRankDefinition(
                    rank_id="rank_officer",
                    name="Officer",
                    level=4,
                    permissions=[
                        GuildPermission.INVITE.value,
                        GuildPermission.KICK.value,
                        GuildPermission.TREASURY_DEPOSIT.value,
                        GuildPermission.TREASURY_WITHDRAW.value,
                        GuildPermission.ACCEPT_QUEST.value,
                    ],
                    max_members=10,
                ),
                GuildRankDefinition(
                    rank_id="rank_veteran",
                    name="Veteran",
                    level=3,
                    permissions=[
                        GuildPermission.INVITE.value,
                        GuildPermission.TREASURY_DEPOSIT.value,
                    ],
                    max_members=30,
                ),
                GuildRankDefinition(
                    rank_id="rank_member",
                    name="Member",
                    level=2,
                    permissions=[GuildPermission.TREASURY_DEPOSIT.value],
                    max_members=100,
                ),
                GuildRankDefinition(
                    rank_id="rank_recruit",
                    name="Recruit",
                    level=1,
                    permissions=[],
                    max_members=50,
                ),
            ]

            # Guild 1: Crimson Vanguard
            guild1 = GuildDefinition(
                guild_id="guild_crimson_vanguard",
                name="Crimson Vanguard",
                tag="CRVN",
                description="An elite guild of seasoned warriors.",
                leader_id="player_starter",
                state=GuildState.ACTIVE.value,
                level=15,
                experience=140000.0,
                treasury_balance={"gold": 250000.0, "gems": 500.0},
                motd="Welcome to the Crimson Vanguard!",
                emblem="shield_crimson",
                rank_definitions=[r for r in default_ranks],
                created_at=_now() - 86400 * 30,
            )
            guild1.members = [
                GuildMember(
                    player_id="player_starter",
                    player_name="StarterHero",
                    rank=GuildRank.LEADER.value,
                    contribution=50000.0,
                    weekly_contribution=2000.0,
                ),
                GuildMember(
                    player_id="player_warrior",
                    player_name="IronFist",
                    rank=GuildRank.OFFICER.value,
                    contribution=32000.0,
                    weekly_contribution=1500.0,
                ),
                GuildMember(
                    player_id="player_mage",
                    player_name="ArcaneMind",
                    rank=GuildRank.VETERAN.value,
                    contribution=18000.0,
                    weekly_contribution=800.0,
                ),
                GuildMember(
                    player_id="player_healer",
                    player_name="LightTouch",
                    rank=GuildRank.MEMBER.value,
                    contribution=8000.0,
                    weekly_contribution=400.0,
                ),
            ]
            guild1.treasury_entries = [
                TreasuryEntry(
                    entry_id="tre_001",
                    entry_type=TreasuryEntryType.DEPOSIT.value,
                    player_id="player_starter",
                    currency="gold",
                    amount=50000.0,
                    description="Initial guild fund deposit",
                    timestamp=_now() - 86400 * 20,
                ),
                TreasuryEntry(
                    entry_id="tre_002",
                    entry_type=TreasuryEntryType.DONATION.value,
                    player_id="player_warrior",
                    currency="gold",
                    amount=25000.0,
                    description="Weekly donation",
                    timestamp=_now() - 86400 * 7,
                ),
            ]
            guild1.quests = [
                GuildQuest(
                    quest_id="gq_crimson_01",
                    name="Slay the Dragon Brood",
                    quest_type=GuildQuestType.KILL_BOSSES.value,
                    description="Defeat 10 dragon bosses in the Sunken Lair.",
                    target_count=10,
                    current_count=3,
                    reward_gold=20000.0,
                    reward_xp=5000,
                    reward_guild_xp=3000,
                    status=GuildQuestStatus.ACTIVE.value,
                    difficulty="hard",
                    accepted_at=_now() - 3600 * 12,
                    expires_at=_now() + 86400,
                ),
                GuildQuest(
                    quest_id="gq_crimson_02",
                    name="Gather Mystic Crystals",
                    quest_type=GuildQuestType.GATHER_RESOURCES.value,
                    description="Collect 50 mystic crystals from the Crystal Caverns.",
                    target_count=50,
                    current_count=0,
                    reward_gold=10000.0,
                    reward_xp=3000,
                    reward_guild_xp=1500,
                    status=GuildQuestStatus.AVAILABLE.value,
                    difficulty="normal",
                ),
            ]
            guild1.perks = [
                GuildPerk(
                    perk_id="perk_xp_boost",
                    name="Guild XP Boost",
                    description="Increases XP gain by 10% for all members.",
                    perk_type="passive",
                    effect_value=0.10,
                    cost_gold=5000.0,
                    required_guild_level=5,
                    activated=True,
                    activated_at=_now() - 86400 * 5,
                ),
                GuildPerk(
                    perk_id="perk_gold_find",
                    name="Gold Find Bonus",
                    description="Increases gold drop rate by 5%.",
                    perk_type="passive",
                    effect_value=0.05,
                    cost_gold=8000.0,
                    required_guild_level=10,
                    activated=False,
                ),
            ]
            self._guilds[guild1.guild_id] = guild1

            # Guild 2: Azure Sentinels
            guild2 = GuildDefinition(
                guild_id="guild_azure_sentinels",
                name="Azure Sentinels",
                tag="AZSN",
                description="Guardians of the eastern realm.",
                leader_id="player_veteran",
                state=GuildState.ACTIVE.value,
                level=20,
                experience=190000.0,
                treasury_balance={"gold": 500000.0, "gems": 1200.0},
                motd="Stand firm, stand together.",
                emblem="shield_azure",
                rank_definitions=[r for r in default_ranks],
                created_at=_now() - 86400 * 60,
            )
            guild2.members = [
                GuildMember(
                    player_id="player_veteran",
                    player_name="VeteranGuard",
                    rank=GuildRank.LEADER.value,
                    contribution=80000.0,
                    weekly_contribution=3000.0,
                ),
                GuildMember(
                    player_id="player_archer",
                    player_name="SharpEye",
                    rank=GuildRank.OFFICER.value,
                    contribution=45000.0,
                    weekly_contribution=2000.0,
                ),
                GuildMember(
                    player_id="player_rogue",
                    player_name="ShadowStep",
                    rank=GuildRank.VETERAN.value,
                    contribution=22000.0,
                    weekly_contribution=1000.0,
                ),
                GuildMember(
                    player_id="player_paladin",
                    player_name="HolyLight",
                    rank=GuildRank.MEMBER.value,
                    contribution=12000.0,
                    weekly_contribution=600.0,
                ),
                GuildMember(
                    player_id="player_recruit_01",
                    player_name="NewHope",
                    rank=GuildRank.RECRUIT.value,
                    contribution=500.0,
                    weekly_contribution=100.0,
                ),
            ]
            guild2.treasury_entries = [
                TreasuryEntry(
                    entry_id="tre_003",
                    entry_type=TreasuryEntryType.DEPOSIT.value,
                    player_id="player_veteran",
                    currency="gold",
                    amount=100000.0,
                    description="Initial guild fund deposit",
                    timestamp=_now() - 86400 * 50,
                ),
                TreasuryEntry(
                    entry_id="tre_004",
                    entry_type=TreasuryEntryType.QUEST_REWARD.value,
                    currency="gold",
                    amount=30000.0,
                    description="Guild quest completion reward",
                    timestamp=_now() - 86400 * 3,
                ),
            ]
            guild2.quests = [
                GuildQuest(
                    quest_id="gq_azure_01",
                    name="Conquer the Arena",
                    quest_type=GuildQuestType.WIN_PVP.value,
                    description="Win 20 PvP arena matches as a guild.",
                    target_count=20,
                    current_count=15,
                    reward_gold=30000.0,
                    reward_xp=8000,
                    reward_guild_xp=5000,
                    status=GuildQuestStatus.ACTIVE.value,
                    difficulty="hard",
                    accepted_at=_now() - 3600 * 6,
                    expires_at=_now() + 86400 * 2,
                ),
            ]
            guild2.perks = [
                GuildPerk(
                    perk_id="perk_dmg_boost",
                    name="Damage Boost",
                    description="Increases damage output by 8% for all members.",
                    perk_type="passive",
                    effect_value=0.08,
                    cost_gold=12000.0,
                    required_guild_level=15,
                    activated=True,
                    activated_at=_now() - 86400 * 10,
                ),
            ]
            self._guilds[guild2.guild_id] = guild2

            # Guild 3: Iron Brotherhood
            guild3 = GuildDefinition(
                guild_id="guild_iron_brotherhood",
                name="Iron Brotherhood",
                tag="IRON",
                description="Crafters and traders united.",
                leader_id="player_crafter",
                state=GuildState.ACTIVE.value,
                level=8,
                experience=70000.0,
                treasury_balance={"gold": 80000.0, "gems": 100.0},
                motd="Forge ahead!",
                emblem="hammer_iron",
                rank_definitions=[r for r in default_ranks],
                created_at=_now() - 86400 * 15,
            )
            guild3.members = [
                GuildMember(
                    player_id="player_crafter",
                    player_name="MasterForge",
                    rank=GuildRank.LEADER.value,
                    contribution=20000.0,
                    weekly_contribution=1000.0,
                ),
                GuildMember(
                    player_id="player_miner",
                    player_name="DeepDigger",
                    rank=GuildRank.MEMBER.value,
                    contribution=5000.0,
                    weekly_contribution=300.0,
                ),
            ]
            self._guilds[guild3.guild_id] = guild3

            # Wars
            war1 = GuildWar(
                war_id="war_starter_01",
                attacker_id="guild_crimson_vanguard",
                defender_id="guild_azure_sentinels",
                state=GuildWarState.ACTIVE.value,
                outcome=GuildWarOutcome.PENDING.value,
                declared_at=_now() - 3600,
                started_at=_now() - 1800,
                duration_seconds=7200.0,
                stakes_gold=50000.0,
                participants=[
                    GuildWarParticipant(
                        guild_id="guild_crimson_vanguard",
                        guild_name="Crimson Vanguard",
                        score=350.0,
                        kills=12,
                        deaths=8,
                        objectives=3,
                        is_attacker=True,
                    ),
                    GuildWarParticipant(
                        guild_id="guild_azure_sentinels",
                        guild_name="Azure Sentinels",
                        score=280.0,
                        kills=8,
                        deaths=12,
                        objectives=2,
                        is_attacker=False,
                    ),
                ],
            )
            self._wars[war1.war_id] = war1
            self._guilds["guild_crimson_vanguard"].active_wars.append(war1.war_id)
            self._guilds["guild_azure_sentinels"].active_wars.append(war1.war_id)

            war2 = GuildWar(
                war_id="war_starter_02",
                attacker_id="guild_azure_sentinels",
                defender_id="guild_iron_brotherhood",
                state=GuildWarState.ENDED.value,
                outcome=GuildWarOutcome.ATTACKER_WIN.value,
                declared_at=_now() - 86400,
                started_at=_now() - 86400 + 600,
                ended_at=_now() - 86400 + 4200,
                duration_seconds=3600.0,
                stakes_gold=20000.0,
                winner_id="guild_azure_sentinels",
                participants=[
                    GuildWarParticipant(
                        guild_id="guild_azure_sentinels",
                        guild_name="Azure Sentinels",
                        score=500.0,
                        kills=20,
                        deaths=5,
                        objectives=5,
                        is_attacker=True,
                    ),
                    GuildWarParticipant(
                        guild_id="guild_iron_brotherhood",
                        guild_name="Iron Brotherhood",
                        score=150.0,
                        kills=5,
                        deaths=20,
                        objectives=1,
                        is_attacker=False,
                    ),
                ],
            )
            self._wars[war2.war_id] = war2

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        self._stats.total_guilds = len(self._guilds)
        self._stats.active_guilds = sum(
            1 for g in self._guilds.values() if g.state == GuildState.ACTIVE.value
        )
        self._stats.disbanded_guilds = sum(
            1 for g in self._guilds.values() if g.state == GuildState.DISBANDED.value
        )
        self._stats.total_members = sum(len(g.members) for g in self._guilds.values())
        self._stats.total_wars = len(self._wars)
        self._stats.active_wars = sum(
            1 for w in self._wars.values() if w.state == GuildWarState.ACTIVE.value
        )
        self._stats.total_quests = sum(len(g.quests) for g in self._guilds.values())
        self._stats.active_quests = sum(
            1
            for g in self._guilds.values()
            for q in g.quests
            if q.status == GuildQuestStatus.ACTIVE.value
        )
        self._stats.completed_quests = sum(
            1
            for g in self._guilds.values()
            for q in g.quests
            if q.status == GuildQuestStatus.COMPLETED.value
        )
        self._stats.total_treasury_volume = sum(
            sum(g.treasury_balance.values()) for g in self._guilds.values()
        )

    def _record_event(
        self,
        kind: str,
        guild_id: str = "",
        player_id: str = "",
        war_id: str = "",
        quest_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> GuildEvent:
        event = GuildEvent(
            event_id=f"evt_{self._event_counter:06d}",
            kind=kind,
            timestamp=_now(),
            guild_id=guild_id,
            player_id=player_id,
            war_id=war_id,
            quest_id=quest_id,
            description=description,
            details=details or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, 2000)
        return event

    # ------------------------------------------------------------------
    # Guild management
    # ------------------------------------------------------------------

    def _create_default_ranks(self) -> List[GuildRankDefinition]:
        """Create the default set of rank definitions for a new guild."""
        return [
            GuildRankDefinition(
                rank_id="rank_leader",
                name="Guild Leader",
                level=5,
                permissions=[p.value for p in GuildPermission],
                can_manage_ranks=True,
                max_members=1,
            ),
            GuildRankDefinition(
                rank_id="rank_officer",
                name="Officer",
                level=4,
                permissions=[
                    GuildPermission.INVITE.value,
                    GuildPermission.KICK.value,
                    GuildPermission.TREASURY_DEPOSIT.value,
                    GuildPermission.TREASURY_WITHDRAW.value,
                    GuildPermission.ACCEPT_QUEST.value,
                ],
                max_members=10,
            ),
            GuildRankDefinition(
                rank_id="rank_veteran",
                name="Veteran",
                level=3,
                permissions=[
                    GuildPermission.INVITE.value,
                    GuildPermission.TREASURY_DEPOSIT.value,
                ],
                max_members=30,
            ),
            GuildRankDefinition(
                rank_id="rank_member",
                name="Member",
                level=2,
                permissions=[GuildPermission.TREASURY_DEPOSIT.value],
                max_members=100,
            ),
            GuildRankDefinition(
                rank_id="rank_recruit",
                name="Recruit",
                level=1,
                permissions=[],
                max_members=50,
            ),
        ]

    def register_guild(
        self,
        guild_id: str,
        name: str,
        tag: str = "",
        description: str = "",
        leader_id: str = "",
        motd: str = "",
        emblem: str = "",
    ) -> Tuple[bool, str, Optional[GuildDefinition]]:
        if guild_id in self._guilds:
            return False, "exists", None
        if len(self._guilds) >= _MAX_GUILDS:
            return False, "capacity", None
        guild = GuildDefinition(
            guild_id=guild_id,
            name=name,
            tag=tag,
            description=description,
            leader_id=leader_id,
            motd=motd,
            emblem=emblem,
        )
        guild.rank_definitions = self._create_default_ranks()
        if leader_id:
            guild.members.append(
                GuildMember(
                    player_id=leader_id,
                    player_name=leader_id,
                    rank=GuildRank.LEADER.value,
                )
            )
        self._guilds[guild_id] = guild
        self._record_event(
            GuildEventKind.GUILD_CREATED.value,
            guild_id=guild_id,
            player_id=leader_id,
            description=f"Guild '{name}' created",
        )
        return True, "registered", guild

    def remove_guild(self, guild_id: str) -> Tuple[bool, str]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "not_found"
        guild.state = GuildState.DISBANDED.value
        del self._guilds[guild_id]
        self._record_event(
            GuildEventKind.GUILD_DISBANDED.value,
            guild_id=guild_id,
            description=f"Guild '{guild.name}' disbanded",
        )
        return True, "removed"

    def get_guild(self, guild_id: str) -> Optional[GuildDefinition]:
        return self._guilds.get(guild_id)

    def list_guilds(
        self, state: str = "", limit: int = 50, offset: int = 0
    ) -> List[GuildDefinition]:
        guilds = list(self._guilds.values())
        if state:
            guilds = [g for g in guilds if g.state == state]
        return guilds[offset : offset + limit]

    def update_guild_info(
        self,
        guild_id: str,
        name: str = "",
        tag: str = "",
        description: str = "",
        motd: str = "",
        emblem: str = "",
    ) -> Tuple[bool, str, Optional[GuildDefinition]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "not_found", None
        if name:
            guild.name = name
        if tag:
            guild.tag = tag
        if description:
            guild.description = description
        if motd:
            guild.motd = motd
        if emblem:
            guild.emblem = emblem
        self._record_event(
            GuildEventKind.CONFIG_UPDATED.value,
            guild_id=guild_id,
            description="Guild info updated",
        )
        return True, "updated", guild

    # ------------------------------------------------------------------
    # Member management
    # ------------------------------------------------------------------

    def add_member(
        self,
        guild_id: str,
        player_id: str,
        player_name: str = "",
        rank: str = GuildRank.RECRUIT.value,
    ) -> Tuple[bool, str, Optional[GuildMember]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        existing = next((m for m in guild.members if m.player_id == player_id), None)
        if existing is not None:
            return False, "already_member", None
        if len(guild.members) >= self._config.max_members_per_guild:
            return False, "capacity", None
        member = GuildMember(
            player_id=player_id,
            player_name=player_name or player_id,
            rank=rank,
        )
        guild.members.append(member)
        self._record_event(
            GuildEventKind.MEMBER_JOINED.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Member '{player_name or player_id}' joined",
        )
        return True, "joined", member

    def remove_member(
        self, guild_id: str, player_id: str
    ) -> Tuple[bool, str]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found"
        member = next((m for m in guild.members if m.player_id == player_id), None)
        if member is None:
            return False, "not_member"
        guild.members.remove(member)
        self._record_event(
            GuildEventKind.MEMBER_LEFT.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Member '{member.player_name}' left",
        )
        return True, "left"

    def kick_member(
        self, guild_id: str, player_id: str, kicker_id: str = ""
    ) -> Tuple[bool, str]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found"
        member = next((m for m in guild.members if m.player_id == player_id), None)
        if member is None:
            return False, "not_member"
        if member.rank == GuildRank.LEADER.value:
            return False, "cannot_kick_leader"
        guild.members.remove(member)
        self._record_event(
            GuildEventKind.MEMBER_KICKED.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Member '{member.player_name}' kicked by {kicker_id}",
        )
        return True, "kicked"

    def promote_member(
        self, guild_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[GuildMember]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        member = next((m for m in guild.members if m.player_id == player_id), None)
        if member is None:
            return False, "not_member", None
        rank_order = [
            GuildRank.RECRUIT.value,
            GuildRank.MEMBER.value,
            GuildRank.VETERAN.value,
            GuildRank.OFFICER.value,
        ]
        idx = rank_order.index(member.rank) if member.rank in rank_order else -1
        if idx < 0 or idx >= len(rank_order) - 1:
            return False, "max_rank", None
        member.rank = rank_order[idx + 1]
        self._record_event(
            GuildEventKind.MEMBER_PROMOTED.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Member '{member.player_name}' promoted to {member.rank}",
        )
        return True, "promoted", member

    def demote_member(
        self, guild_id: str, player_id: str
    ) -> Tuple[bool, str, Optional[GuildMember]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        member = next((m for m in guild.members if m.player_id == player_id), None)
        if member is None:
            return False, "not_member", None
        if member.rank == GuildRank.LEADER.value:
            return False, "cannot_demote_leader", None
        rank_order = [
            GuildRank.RECRUIT.value,
            GuildRank.MEMBER.value,
            GuildRank.VETERAN.value,
            GuildRank.OFFICER.value,
        ]
        idx = rank_order.index(member.rank) if member.rank in rank_order else -1
        if idx <= 0:
            return False, "min_rank", None
        member.rank = rank_order[idx - 1]
        self._record_event(
            GuildEventKind.MEMBER_DEMOTED.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Member '{member.player_name}' demoted to {member.rank}",
        )
        return True, "demoted", member

    def get_member(self, guild_id: str, player_id: str) -> Optional[GuildMember]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return None
        return next((m for m in guild.members if m.player_id == player_id), None)

    def list_members(
        self, guild_id: str, rank: str = "", limit: int = 50, offset: int = 0
    ) -> List[GuildMember]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return []
        members = guild.members
        if rank:
            members = [m for m in members if m.rank == rank]
        return members[offset : offset + limit]

    # ------------------------------------------------------------------
    # Treasury
    # ------------------------------------------------------------------

    def deposit_treasury(
        self,
        guild_id: str,
        player_id: str,
        currency: str = "gold",
        amount: float = 0.0,
        description: str = "",
    ) -> Tuple[bool, str, Optional[TreasuryEntry]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        if amount <= 0:
            return False, "invalid_amount", None
        guild.treasury_balance[currency] = (
            guild.treasury_balance.get(currency, 0.0) + amount
        )
        entry = TreasuryEntry(
            entry_id=f"tre_{self._treasury_counter:06d}",
            entry_type=TreasuryEntryType.DEPOSIT.value,
            player_id=player_id,
            currency=currency,
            amount=amount,
            description=description or f"Deposit of {amount} {currency}",
        )
        self._treasury_counter += 1
        guild.treasury_entries.append(entry)
        _evict_fifo_list(guild.treasury_entries, self._config.max_treasury_entries)
        member = next((m for m in guild.members if m.player_id == player_id), None)
        if member:
            member.contribution += amount
            member.weekly_contribution += amount
        self._record_event(
            GuildEventKind.TREASURY_DEPOSIT.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Deposited {amount} {currency}",
            details={"currency": currency, "amount": amount},
        )
        return True, "deposited", entry

    def withdraw_treasury(
        self,
        guild_id: str,
        player_id: str,
        currency: str = "gold",
        amount: float = 0.0,
        description: str = "",
    ) -> Tuple[bool, str, Optional[TreasuryEntry]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        if amount <= 0:
            return False, "invalid_amount", None
        balance = guild.treasury_balance.get(currency, 0.0)
        if balance < amount:
            return False, "insufficient_funds", None
        guild.treasury_balance[currency] = balance - amount
        entry = TreasuryEntry(
            entry_id=f"tre_{self._treasury_counter:06d}",
            entry_type=TreasuryEntryType.WITHDRAWAL.value,
            player_id=player_id,
            currency=currency,
            amount=amount,
            description=description or f"Withdrawal of {amount} {currency}",
        )
        self._treasury_counter += 1
        guild.treasury_entries.append(entry)
        _evict_fifo_list(guild.treasury_entries, self._config.max_treasury_entries)
        self._record_event(
            GuildEventKind.TREASURY_WITHDRAW.value,
            guild_id=guild_id,
            player_id=player_id,
            description=f"Withdrew {amount} {currency}",
            details={"currency": currency, "amount": amount},
        )
        return True, "withdrawn", entry

    def get_treasury_balance(self, guild_id: str) -> Dict[str, float]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return {}
        return dict(guild.treasury_balance)

    def list_treasury_entries(
        self, guild_id: str, limit: int = 50, offset: int = 0
    ) -> List[TreasuryEntry]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return []
        return guild.treasury_entries[offset : offset + limit]

    # ------------------------------------------------------------------
    # Quest management
    # ------------------------------------------------------------------

    def register_quest(
        self,
        guild_id: str,
        quest_id: str,
        name: str,
        quest_type: str = GuildQuestType.KILL_BOSSES.value,
        description: str = "",
        target_count: int = 10,
        reward_gold: float = 5000.0,
        reward_xp: int = 2000,
        reward_guild_xp: int = 1000,
        difficulty: str = "normal",
        duration_seconds: float = 86400.0,
    ) -> Tuple[bool, str, Optional[GuildQuest]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        existing = next((q for q in guild.quests if q.quest_id == quest_id), None)
        if existing is not None:
            return False, "exists", None
        quest = GuildQuest(
            quest_id=quest_id,
            name=name,
            quest_type=quest_type,
            description=description,
            target_count=target_count,
            reward_gold=reward_gold,
            reward_xp=reward_xp,
            reward_guild_xp=reward_guild_xp,
            difficulty=difficulty,
            duration_seconds=duration_seconds,
        )
        guild.quests.append(quest)
        return True, "registered", quest

    def accept_quest(
        self, guild_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[GuildQuest]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        quest = next((q for q in guild.quests if q.quest_id == quest_id), None)
        if quest is None:
            return False, "quest_not_found", None
        if quest.status != GuildQuestStatus.AVAILABLE.value:
            return False, "not_available", None
        quest.status = GuildQuestStatus.ACTIVE.value
        quest.accepted_at = _now()
        quest.expires_at = _now() + quest.duration_seconds
        self._record_event(
            GuildEventKind.QUEST_ACCEPTED.value,
            guild_id=guild_id,
            quest_id=quest_id,
            description=f"Quest '{quest.name}' accepted",
        )
        return True, "accepted", quest

    def update_quest_progress(
        self, guild_id: str, quest_id: str, count: int = 1
    ) -> Tuple[bool, str, Optional[GuildQuest]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        quest = next((q for q in guild.quests if q.quest_id == quest_id), None)
        if quest is None:
            return False, "quest_not_found", None
        if quest.status != GuildQuestStatus.ACTIVE.value:
            return False, "not_active", None
        quest.current_count = min(quest.current_count + count, quest.target_count)
        if quest.current_count >= quest.target_count:
            quest.status = GuildQuestStatus.COMPLETED.value
            quest.completed_at = _now()
            self._record_event(
                GuildEventKind.QUEST_COMPLETED.value,
                guild_id=guild_id,
                quest_id=quest_id,
                description=f"Quest '{quest.name}' completed",
            )
        return True, "updated", quest

    def complete_quest(
        self, guild_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[GuildQuest]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        quest = next((q for q in guild.quests if q.quest_id == quest_id), None)
        if quest is None:
            return False, "quest_not_found", None
        if quest.status != GuildQuestStatus.ACTIVE.value:
            return False, "not_active", None
        quest.current_count = quest.target_count
        quest.status = GuildQuestStatus.COMPLETED.value
        quest.completed_at = _now()
        self._record_event(
            GuildEventKind.QUEST_COMPLETED.value,
            guild_id=guild_id,
            quest_id=quest_id,
            description=f"Quest '{quest.name}' completed",
        )
        return True, "completed", quest

    def claim_quest(
        self, guild_id: str, quest_id: str
    ) -> Tuple[bool, str, Optional[GuildQuest]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        quest = next((q for q in guild.quests if q.quest_id == quest_id), None)
        if quest is None:
            return False, "quest_not_found", None
        if quest.status != GuildQuestStatus.COMPLETED.value:
            return False, "not_completed", None
        quest.status = GuildQuestStatus.CLAIMED.value
        guild.treasury_balance["gold"] = (
            guild.treasury_balance.get("gold", 0.0) + quest.reward_gold
        )
        guild.experience += quest.reward_guild_xp
        self._check_guild_level_up(guild)
        entry = TreasuryEntry(
            entry_id=f"tre_{self._treasury_counter:06d}",
            entry_type=TreasuryEntryType.QUEST_REWARD.value,
            currency="gold",
            amount=quest.reward_gold,
            description=f"Quest reward from '{quest.name}'",
        )
        self._treasury_counter += 1
        guild.treasury_entries.append(entry)
        _evict_fifo_list(guild.treasury_entries, self._config.max_treasury_entries)
        self._record_event(
            GuildEventKind.QUEST_CLAIMED.value,
            guild_id=guild_id,
            quest_id=quest_id,
            description=f"Quest '{quest.name}' rewards claimed",
            details={"reward_gold": quest.reward_gold, "reward_guild_xp": quest.reward_guild_xp},
        )
        return True, "claimed", quest

    def get_quest(self, guild_id: str, quest_id: str) -> Optional[GuildQuest]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return None
        return next((q for q in guild.quests if q.quest_id == quest_id), None)

    def list_quests(
        self,
        guild_id: str,
        status: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[GuildQuest]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return []
        quests = guild.quests
        if status:
            quests = [q for q in quests if q.status == status]
        return quests[offset : offset + limit]

    def _check_guild_level_up(self, guild: GuildDefinition) -> None:
        xp_needed = guild.level * self._config.guild_xp_per_level
        while guild.experience >= xp_needed:
            guild.experience -= xp_needed
            guild.level += 1
            xp_needed = guild.level * self._config.guild_xp_per_level

    # ------------------------------------------------------------------
    # War management
    # ------------------------------------------------------------------

    def declare_war(
        self,
        war_id: str,
        attacker_id: str,
        defender_id: str,
        stakes_gold: float = 10000.0,
        duration_seconds: float = 3600.0,
    ) -> Tuple[bool, str, Optional[GuildWar]]:
        if war_id in self._wars:
            return False, "exists", None
        attacker = self._guilds.get(attacker_id)
        defender = self._guilds.get(defender_id)
        if attacker is None or defender is None:
            return False, "guild_not_found", None
        if attacker_id == defender_id:
            return False, "same_guild", None
        if len(self._wars) >= _MAX_GUILD_WARS:
            return False, "capacity", None
        war = GuildWar(
            war_id=war_id,
            attacker_id=attacker_id,
            defender_id=defender_id,
            stakes_gold=stakes_gold,
            duration_seconds=duration_seconds,
            participants=[
                GuildWarParticipant(
                    guild_id=attacker_id,
                    guild_name=attacker.name,
                    is_attacker=True,
                ),
                GuildWarParticipant(
                    guild_id=defender_id,
                    guild_name=defender.name,
                    is_attacker=False,
                ),
            ],
        )
        self._wars[war_id] = war
        attacker.active_wars.append(war_id)
        defender.active_wars.append(war_id)
        self._record_event(
            GuildEventKind.WAR_DECLARED.value,
            guild_id=attacker_id,
            war_id=war_id,
            description=f"War declared: {attacker.name} vs {defender.name}",
        )
        return True, "declared", war

    def start_war(self, war_id: str) -> Tuple[bool, str, Optional[GuildWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "war_not_found", None
        if war.state != GuildWarState.DECLARED.value:
            return False, "invalid_state", None
        war.state = GuildWarState.ACTIVE.value
        war.started_at = _now()
        return True, "started", war

    def end_war(
        self, war_id: str, winner_id: str = ""
    ) -> Tuple[bool, str, Optional[GuildWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "war_not_found", None
        if war.state not in (GuildWarState.ACTIVE.value, GuildWarState.DECLARED.value):
            return False, "invalid_state", None
        war.state = GuildWarState.ENDED.value
        war.ended_at = _now()
        war.winner_id = winner_id
        if winner_id == war.attacker_id:
            war.outcome = GuildWarOutcome.ATTACKER_WIN.value
        elif winner_id == war.defender_id:
            war.outcome = GuildWarOutcome.DEFENDER_WIN.value
        else:
            war.outcome = GuildWarOutcome.DRAW.value
        attacker = self._guilds.get(war.attacker_id)
        defender = self._guilds.get(war.defender_id)
        if attacker and war_id in attacker.active_wars:
            attacker.active_wars.remove(war_id)
        if defender and war_id in defender.active_wars:
            defender.active_wars.remove(war_id)
        self._record_event(
            GuildEventKind.WAR_ENDED.value,
            war_id=war_id,
            description=f"War ended. Winner: {winner_id or 'draw'}",
        )
        return True, "ended", war

    def cancel_war(self, war_id: str) -> Tuple[bool, str, Optional[GuildWar]]:
        war = self._wars.get(war_id)
        if war is None:
            return False, "war_not_found", None
        if war.state == GuildWarState.ENDED.value:
            return False, "already_ended", None
        war.state = GuildWarState.CANCELLED.value
        war.ended_at = _now()
        attacker = self._guilds.get(war.attacker_id)
        defender = self._guilds.get(war.defender_id)
        if attacker and war_id in attacker.active_wars:
            attacker.active_wars.remove(war_id)
        if defender and war_id in defender.active_wars:
            defender.active_wars.remove(war_id)
        return True, "cancelled", war

    def get_war(self, war_id: str) -> Optional[GuildWar]:
        return self._wars.get(war_id)

    def list_wars(
        self, state: str = "", limit: int = 50, offset: int = 0
    ) -> List[GuildWar]:
        wars = list(self._wars.values())
        if state:
            wars = [w for w in wars if w.state == state]
        return wars[offset : offset + limit]

    # ------------------------------------------------------------------
    # Perk management
    # ------------------------------------------------------------------

    def register_perk(
        self,
        guild_id: str,
        perk_id: str,
        name: str,
        description: str = "",
        perk_type: str = "passive",
        effect_value: float = 0.0,
        cost_gold: float = 1000.0,
        required_guild_level: int = 1,
        duration_seconds: float = 0.0,
    ) -> Tuple[bool, str, Optional[GuildPerk]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        existing = next((p for p in guild.perks if p.perk_id == perk_id), None)
        if existing is not None:
            return False, "exists", None
        perk = GuildPerk(
            perk_id=perk_id,
            name=name,
            description=description,
            perk_type=perk_type,
            effect_value=effect_value,
            cost_gold=cost_gold,
            required_guild_level=required_guild_level,
            duration_seconds=duration_seconds,
        )
        guild.perks.append(perk)
        return True, "registered", perk

    def activate_perk(
        self, guild_id: str, perk_id: str
    ) -> Tuple[bool, str, Optional[GuildPerk]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        perk = next((p for p in guild.perks if p.perk_id == perk_id), None)
        if perk is None:
            return False, "perk_not_found", None
        if perk.activated:
            return False, "already_active", None
        if guild.level < perk.required_guild_level:
            return False, "level_too_low", None
        balance = guild.treasury_balance.get("gold", 0.0)
        if balance < perk.cost_gold:
            return False, "insufficient_gold", None
        guild.treasury_balance["gold"] = balance - perk.cost_gold
        perk.activated = True
        perk.activated_at = _now()
        if perk.duration_seconds > 0:
            perk.expires_at = _now() + perk.duration_seconds
        self._record_event(
            GuildEventKind.PERK_ACTIVATED.value,
            guild_id=guild_id,
            description=f"Perk '{perk.name}' activated",
        )
        return True, "activated", perk

    def deactivate_perk(
        self, guild_id: str, perk_id: str
    ) -> Tuple[bool, str, Optional[GuildPerk]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        perk = next((p for p in guild.perks if p.perk_id == perk_id), None)
        if perk is None:
            return False, "perk_not_found", None
        if not perk.activated:
            return False, "not_active", None
        perk.activated = False
        perk.expires_at = 0.0
        self._record_event(
            GuildEventKind.PERK_DEACTIVATED.value,
            guild_id=guild_id,
            description=f"Perk '{perk.name}' deactivated",
        )
        return True, "deactivated", perk

    def get_perk(self, guild_id: str, perk_id: str) -> Optional[GuildPerk]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return None
        return next((p for p in guild.perks if p.perk_id == perk_id), None)

    def list_perks(
        self, guild_id: str, active_only: bool = False, limit: int = 50, offset: int = 0
    ) -> List[GuildPerk]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return []
        perks = guild.perks
        if active_only:
            perks = [p for p in perks if p.activated]
        return perks[offset : offset + limit]

    # ------------------------------------------------------------------
    # Rank definitions
    # ------------------------------------------------------------------

    def register_rank(
        self,
        guild_id: str,
        rank_id: str,
        name: str,
        level: int = 0,
        permissions: Optional[List[str]] = None,
        can_manage_ranks: bool = False,
        max_members: int = 999,
    ) -> Tuple[bool, str, Optional[GuildRankDefinition]]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return False, "guild_not_found", None
        existing = next((r for r in guild.rank_definitions if r.rank_id == rank_id), None)
        if existing is not None:
            return False, "exists", None
        rank_def = GuildRankDefinition(
            rank_id=rank_id,
            name=name,
            level=level,
            permissions=permissions or [],
            can_manage_ranks=can_manage_ranks,
            max_members=max_members,
        )
        guild.rank_definitions.append(rank_def)
        return True, "registered", rank_def

    def get_rank(self, guild_id: str, rank_id: str) -> Optional[GuildRankDefinition]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return None
        return next((r for r in guild.rank_definitions if r.rank_id == rank_id), None)

    def list_ranks(self, guild_id: str) -> List[GuildRankDefinition]:
        guild = self._guilds.get(guild_id)
        if guild is None:
            return []
        return guild.rank_definitions

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        now = _now()
        for guild in self._guilds.values():
            for quest in guild.quests:
                if (
                    quest.status == GuildQuestStatus.ACTIVE.value
                    and quest.expires_at > 0
                    and now > quest.expires_at
                ):
                    quest.status = GuildQuestStatus.EXPIRED.value
            for perk in guild.perks:
                if (
                    perk.activated
                    and perk.expires_at > 0
                    and now > perk.expires_at
                ):
                    perk.activated = False
        for war in self._wars.values():
            if (
                war.state == GuildWarState.ACTIVE.value
                and war.started_at > 0
                and now > war.started_at + war.duration_seconds
            ):
                war.state = GuildWarState.ENDED.value
                war.ended_at = now
                war.outcome = GuildWarOutcome.DRAW.value
        self._refresh_stats()
        self._record_event(GuildEventKind.TICK.value, description=f"Tick #{self._tick_count}")
        return self.get_status()

    def set_config(self, config: Dict[str, Any]) -> GuildClanConfig:
        if "max_guilds" in config:
            self._config.max_guilds = _safe_int(config["max_guilds"], self._config.max_guilds)
        if "max_members_per_guild" in config:
            self._config.max_members_per_guild = _safe_int(
                config["max_members_per_guild"], self._config.max_members_per_guild
            )
        if "max_wars" in config:
            self._config.max_wars = _safe_int(config["max_wars"], self._config.max_wars)
        if "max_quests" in config:
            self._config.max_quests = _safe_int(config["max_quests"], self._config.max_quests)
        if "war_duration_seconds" in config:
            self._config.war_duration_seconds = _safe_float(
                config["war_duration_seconds"], self._config.war_duration_seconds
            )
        if "guild_xp_per_level" in config:
            self._config.guild_xp_per_level = _safe_float(
                config["guild_xp_per_level"], self._config.guild_xp_per_level
            )
        self._record_event(
            GuildEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
        )
        return self._config

    def get_config(self) -> GuildClanConfig:
        return self._config

    def list_events(
        self, guild_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[GuildEvent]:
        events = self._events
        if guild_id:
            events = [e for e in events if e.guild_id == guild_id]
        return events[offset : offset + limit]

    def get_stats(self) -> GuildClanStats:
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_guilds": len(self._guilds),
            "active_guilds": sum(
                1 for g in self._guilds.values() if g.state == GuildState.ACTIVE.value
            ),
            "total_wars": len(self._wars),
            "active_wars": sum(
                1 for w in self._wars.values() if w.state == GuildWarState.ACTIVE.value
            ),
            "total_members": sum(len(g.members) for g in self._guilds.values()),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> GuildClanSnapshot:
        self._refresh_stats()
        return GuildClanSnapshot(
            config=self._config.to_dict(),
            stats=self._stats.to_dict(),
            guilds=[g.to_dict() for g in list(self._guilds.values())[:50]],
            wars=[w.to_dict() for w in list(self._wars.values())[:50]],
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._guilds.clear()
            self._wars.clear()
            self._events.clear()
            self._stats = GuildClanStats()
            self._config = GuildClanConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._war_counter = 0
            self._quest_counter = 0
            self._treasury_counter = 0
            self._perk_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            GuildEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_guild_clan_system() -> GuildClanSystem:
    """Factory function to get the GuildClanSystem singleton instance."""
    return GuildClanSystem.get_instance()
