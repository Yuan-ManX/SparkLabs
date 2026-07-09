"""
SparkLabs Engine - Title, Honor & Prestige System

Manages player titles, badges, medals, honor points, and prestige ranks.
Players earn titles through achievements, collect badges for completing
milestones, receive medals for exceptional accomplishments, accumulate
honor points through PvP and PvE activities, and progress through
prestige ranks by resetting progress for permanent bonuses.

Each title can be displayed alongside a player name, badges appear on
the player profile, medals are showcased in a trophy case, honor points
contribute to a global honor ranking, and prestige ranks unlock new
content and multipliers.

Architecture:
  TitleHonorSystem (singleton)
    |-- TitleCategory, TitleRarity, BadgeType, MedalTier,
       HonorSource, PrestigeTier, TitleHonorEventKind
    |-- TitleDefinition, PlayerTitle, BadgeDefinition, PlayerBadge,
       MedalDefinition, PlayerMedal, HonorRecord, PrestigeRank,
       TitleHonorConfig, TitleHonorStats, TitleHonorSnapshot,
       TitleHonorEvent
    |-- get_title_honor_system

Core Capabilities:
  - register_title / remove_title / get_title / list_titles: manage the
    catalog of obtainable titles with categories and rarities.
  - award_title / revoke_title / activate_title / get_player_titles:
    manage titles held by individual players.
  - register_badge / remove_badge / get_badge / list_badges: manage the
    badge definition catalog.
  - award_badge / revoke_badge / get_player_badges: manage player badges.
  - register_medal / remove_medal / get_medal / list_medals: manage the
    medal definition catalog.
  - award_medal / revoke_medal / get_player_medals: manage player medals.
  - award_honor / spend_honor / get_honor_balance / get_honor_ranking:
    track honor points and leaderboard rankings.
  - register_prestige_rank / get_prestige_rank / prestige_player /
    get_player_prestige: manage prestige progression.
  - tick / set_config / get_config: lifecycle and tuning.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TitleHonorSystem.get_instance` or the module-level
:func:`get_title_honor_system` factory.
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

_MAX_TITLES: int = 500
_MAX_BADGES: int = 500
_MAX_MEDALS: int = 300
_MAX_PLAYER_TITLES: int = 100
_MAX_HONOR_RECORDS: int = 10000
_MAX_PRESTIGE_RANKS: int = 50
_MAX_EVENTS: int = 8000


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

class TitleCategory(str, Enum):
    """Category of a title."""
    ACHIEVEMENT = "achievement"
    PVP = "pvp"
    PVE = "pve"
    SOCIAL = "social"
    CRAFTING = "crafting"
    EXPLORATION = "exploration"
    SEASONAL = "seasonal"
    SPECIAL = "special"


class TitleRarity(str, Enum):
    """Rarity level of a title."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class BadgeType(str, Enum):
    """Type of badge."""
    MILESTONE = "milestone"
    COLLECTION = "collection"
    MASTERY = "mastery"
    VETERAN = "veteran"
    FOUNDER = "founder"
    EVENT = "event"
    COMMUNITY = "community"


class MedalTier(str, Enum):
    """Tier of a medal."""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"


class HonorSource(str, Enum):
    """Source of honor points."""
    PVP_KILL = "pvp_kill"
    PVP_WIN = "pvp_win"
    RAID_COMPLETION = "raid_completion"
    BOSS_DEFEAT = "boss_defeat"
    QUEST_COMPLETION = "quest_completion"
    TOURNAMENT_WIN = "tournament_win"
    DAILY_CHALLENGE = "daily_challenge"
    GUILD_CONTRIBUTION = "guild_contribution"
    ADMIN_GRANT = "admin_grant"
    PENALTY = "penalty"


class PrestigeTier(str, Enum):
    """Prestige tier names."""
    NOVICE = "novice"
    APPRENTICE = "apprentice"
    ADEPT = "adept"
    EXPERT = "expert"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    LEGEND = "legend"
    MYTHIC = "mythic"


class TitleHonorEventKind(str, Enum):
    """Audit event types emitted by the title honor system."""
    TITLE_REGISTERED = "title_registered"
    TITLE_REMOVED = "title_removed"
    TITLE_AWARDED = "title_awarded"
    TITLE_REVOKED = "title_revoked"
    TITLE_ACTIVATED = "title_activated"
    BADGE_REGISTERED = "badge_registered"
    BADGE_REMOVED = "badge_removed"
    BADGE_AWARDED = "badge_awarded"
    BADGE_REVOKED = "badge_revoked"
    MEDAL_REGISTERED = "medal_registered"
    MEDAL_REMOVED = "medal_removed"
    MEDAL_AWARDED = "medal_awarded"
    MEDAL_REVOKED = "medal_revoked"
    HONOR_AWARDED = "honor_awarded"
    HONOR_SPENT = "honor_spent"
    PRESTIGE_REGISTERED = "prestige_registered"
    PRESTIGE_PROMOTED = "prestige_promoted"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class TitleDefinition:
    """A title definition in the catalog."""
    title_id: str
    name: str
    category: str = TitleCategory.ACHIEVEMENT.value
    rarity: str = TitleRarity.COMMON.value
    description: str = ""
    prefix: str = ""
    suffix: str = ""
    icon: str = ""
    color_hex: str = "#FFFFFF"
    is_secret: bool = False
    obtainable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerTitle:
    """A title held by a player."""
    player_id: str
    title_id: str
    obtained_at: float = field(default_factory=_now)
    is_active: bool = False
    source: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BadgeDefinition:
    """A badge definition in the catalog."""
    badge_id: str
    name: str
    badge_type: str = BadgeType.MILESTONE.value
    description: str = ""
    icon: str = ""
    rarity: str = TitleRarity.COMMON.value
    requirement: str = ""
    reward_honor: int = 0
    obtainable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerBadge:
    """A badge earned by a player."""
    player_id: str
    badge_id: str
    earned_at: float = field(default_factory=_now)
    progress: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MedalDefinition:
    """A medal definition in the catalog."""
    medal_id: str
    name: str
    tier: str = MedalTier.BRONZE.value
    description: str = ""
    icon: str = ""
    requirement: str = ""
    reward_honor: int = 0
    reward_prestige_xp: int = 0
    obtainable: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerMedal:
    """A medal earned by a player."""
    player_id: str
    medal_id: str
    earned_at: float = field(default_factory=_now)
    showcase_slot: int = -1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HonorRecord:
    """A single honor point transaction."""
    record_id: str
    player_id: str
    source: str = HonorSource.PVP_KILL.value
    amount: int = 0
    description: str = ""
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HonorBalance:
    """Honor balance and history for a player."""
    player_id: str
    balance: int = 0
    total_earned: int = 0
    total_spent: int = 0
    records: List[HonorRecord] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PrestigeRank:
    """A prestige rank definition."""
    rank_id: str
    name: str
    tier: str = PrestigeTier.NOVICE.value
    level: int = 1
    required_prestige_xp: int = 0
    honor_multiplier: float = 1.0
    xp_multiplier: float = 1.0
    unlock_description: str = ""
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerPrestige:
    """Prestige progression for a player."""
    player_id: str
    current_rank_id: str = ""
    prestige_xp: int = 0
    prestige_level: int = 1
    times_prestiged: int = 0
    total_prestige_xp: int = 0
    unlocked_ranks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TitleHonorConfig:
    """Global tuning parameters for the title honor system."""
    max_titles: int = 500
    max_badges: int = 500
    max_medals: int = 300
    max_player_titles: int = 100
    max_honor_records: int = 10000
    max_prestige_ranks: int = 50
    base_honor_per_pvp_kill: int = 10
    base_honor_per_raid: int = 50
    honor_decay_rate: float = 0.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TitleHonorStats:
    """Aggregate statistics for the title honor system."""
    total_titles: int = 0
    total_badges: int = 0
    total_medals: int = 0
    total_player_titles: int = 0
    total_player_badges: int = 0
    total_player_medals: int = 0
    total_honor_records: int = 0
    total_honor_awarded: int = 0
    total_honor_spent: int = 0
    total_prestige_ranks: int = 0
    total_prestiged_players: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TitleHonorSnapshot:
    """Full state snapshot of the title honor system."""
    titles: List[Dict[str, Any]] = field(default_factory=list)
    badges: List[Dict[str, Any]] = field(default_factory=list)
    medals: List[Dict[str, Any]] = field(default_factory=list)
    prestige_ranks: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TitleHonorEvent:
    """An audit event emitted by the title honor system."""
    event_id: str
    kind: str
    timestamp: float
    player_id: str = ""
    title_id: str = ""
    badge_id: str = ""
    medal_id: str = ""
    rank_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Title Honor System
# ---------------------------------------------------------------------------

class TitleHonorSystem:
    """Manages titles, badges, medals, honor points, and prestige ranks."""

    _instance: Optional["TitleHonorSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._titles: Dict[str, TitleDefinition] = {}
        self._badges: Dict[str, BadgeDefinition] = {}
        self._medals: Dict[str, MedalDefinition] = {}
        self._player_titles: Dict[str, List[PlayerTitle]] = {}
        self._player_badges: Dict[str, List[PlayerBadge]] = {}
        self._player_medals: Dict[str, List[PlayerMedal]] = {}
        self._honor_balances: Dict[str, HonorBalance] = {}
        self._prestige_ranks: Dict[str, PrestigeRank] = {}
        self._player_prestige: Dict[str, PlayerPrestige] = {}
        self._events: List[TitleHonorEvent] = []
        self._stats = TitleHonorStats()
        self._config = TitleHonorConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "TitleHonorSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial titles, badges, medals, honor, and prestige."""
        with self._init_lock:
            if self._initialized:
                return

            # Titles
            t1 = TitleDefinition(
                title_id="title_starter_warrior",
                name="Brave Warrior",
                category=TitleCategory.ACHIEVEMENT.value,
                rarity=TitleRarity.COMMON.value,
                description="Awarded for reaching level 10.",
                prefix="",
                suffix="the Brave",
                color_hex="#AAAAAA",
            )
            self._titles[t1.title_id] = t1

            t2 = TitleDefinition(
                title_id="title_pvp_champion",
                name="Arena Champion",
                category=TitleCategory.PVP.value,
                rarity=TitleRarity.EPIC.value,
                description="Won 100 arena duels.",
                prefix="Champion",
                suffix="",
                color_hex="#A335EE",
            )
            self._titles[t2.title_id] = t2

            t3 = TitleDefinition(
                title_id="title_dragon_slayer",
                name="Dragon Slayer",
                category=TitleCategory.PVE.value,
                rarity=TitleRarity.LEGENDARY.value,
                description="Defeated the ancient dragon.",
                prefix="",
                suffix="Dragonslayer",
                color_hex="#FF8000",
            )
            self._titles[t3.title_id] = t3

            t4 = TitleDefinition(
                title_id="title_explorer",
                name="World Explorer",
                category=TitleCategory.EXPLORATION.value,
                rarity=TitleRarity.RARE.value,
                description="Discovered all map regions.",
                prefix="Explorer",
                suffix="",
                color_hex="#0070DD",
            )
            self._titles[t4.title_id] = t4

            # Badges
            b1 = BadgeDefinition(
                badge_id="badge_first_blood",
                name="First Blood",
                badge_type=BadgeType.MILESTONE.value,
                description="Won your first PvP battle.",
                icon="icon_first_blood",
                rarity=TitleRarity.COMMON.value,
                requirement="Win 1 PvP match",
                reward_honor=20,
            )
            self._badges[b1.badge_id] = b1

            b2 = BadgeDefinition(
                badge_id="badge_raid_veteran",
                name="Raid Veteran",
                badge_type=BadgeType.VETERAN.value,
                description="Completed 50 raids.",
                icon="icon_raid_vet",
                rarity=TitleRarity.RARE.value,
                requirement="Complete 50 raids",
                reward_honor=200,
            )
            self._badges[b2.badge_id] = b2

            b3 = BadgeDefinition(
                badge_id="badge_founder",
                name="Founder",
                badge_type=BadgeType.FOUNDER.value,
                description="Joined during launch season.",
                icon="icon_founder",
                rarity=TitleRarity.LEGENDARY.value,
                requirement="Play during launch season",
                reward_honor=500,
            )
            self._badges[b3.badge_id] = b3

            # Medals
            m1 = MedalDefinition(
                medal_id="medal_bronze_hero",
                name="Bronze Hero Medal",
                tier=MedalTier.BRONZE.value,
                description="For basic heroism in battle.",
                icon="icon_medal_bronze",
                requirement="Earn 1000 honor",
                reward_honor=50,
                reward_prestige_xp=100,
            )
            self._medals[m1.medal_id] = m1

            m2 = MedalDefinition(
                medal_id="medal_silver_guardian",
                name="Silver Guardian Medal",
                tier=MedalTier.SILVER.value,
                description="For outstanding defense of allies.",
                icon="icon_medal_silver",
                requirement="Earn 5000 honor",
                reward_honor=200,
                reward_prestige_xp=500,
            )
            self._medals[m2.medal_id] = m2

            m3 = MedalDefinition(
                medal_id="medal_gold_legend",
                name="Gold Legend Medal",
                tier=MedalTier.GOLD.value,
                description="For legendary deeds recognized server-wide.",
                icon="icon_medal_gold",
                requirement="Earn 20000 honor",
                reward_honor=1000,
                reward_prestige_xp=2000,
            )
            self._medals[m3.medal_id] = m3

            # Player titles (starter player)
            self._player_titles["player_starter"] = [
                PlayerTitle(
                    player_id="player_starter",
                    title_id="title_starter_warrior",
                    is_active=True,
                    source="level_up",
                ),
                PlayerTitle(
                    player_id="player_starter",
                    title_id="title_explorer",
                    is_active=False,
                    source="exploration",
                ),
            ]

            # Player badges
            self._player_badges["player_starter"] = [
                PlayerBadge(
                    player_id="player_starter",
                    badge_id="badge_first_blood",
                ),
                PlayerBadge(
                    player_id="player_starter",
                    badge_id="badge_founder",
                ),
            ]

            # Player medals
            self._player_medals["player_starter"] = [
                PlayerMedal(
                    player_id="player_starter",
                    medal_id="medal_bronze_hero",
                    showcase_slot=0,
                ),
            ]

            # Honor balances
            self._honor_balances["player_starter"] = HonorBalance(
                player_id="player_starter",
                balance=1500,
                total_earned=2000,
                total_spent=500,
                records=[
                    HonorRecord(
                        record_id="hr_starter_01",
                        player_id="player_starter",
                        source=HonorSource.PVP_WIN.value,
                        amount=100,
                        description="Won 10 PvP matches",
                    ),
                    HonorRecord(
                        record_id="hr_starter_02",
                        player_id="player_starter",
                        source=HonorSource.RAID_COMPLETION.value,
                        amount=200,
                        description="Completed first raid",
                    ),
                    HonorRecord(
                        record_id="hr_starter_03",
                        player_id="player_starter",
                        source=HonorSource.ADMIN_GRANT.value,
                        amount=-500,
                        description="Spent honor on reward",
                    ),
                ],
            )

            self._honor_balances["player_veteran"] = HonorBalance(
                player_id="player_veteran",
                balance=8000,
                total_earned=10000,
                total_spent=2000,
                records=[
                    HonorRecord(
                        record_id="hr_vet_01",
                        player_id="player_veteran",
                        source=HonorSource.BOSS_DEFEAT.value,
                        amount=500,
                        description="Defeated raid boss",
                    ),
                ],
            )

            # Prestige ranks
            pr1 = PrestigeRank(
                rank_id="prestige_novice",
                name="Novice",
                tier=PrestigeTier.NOVICE.value,
                level=1,
                required_prestige_xp=0,
                honor_multiplier=1.0,
                xp_multiplier=1.0,
                unlock_description="Starting prestige rank",
                icon="icon_prestige_novice",
            )
            self._prestige_ranks[pr1.rank_id] = pr1

            pr2 = PrestigeRank(
                rank_id="prestige_apprentice",
                name="Apprentice",
                tier=PrestigeTier.APPRENTICE.value,
                level=2,
                required_prestige_xp=1000,
                honor_multiplier=1.1,
                xp_multiplier=1.05,
                unlock_description="5% XP bonus, 10% honor bonus",
                icon="icon_prestige_apprentice",
            )
            self._prestige_ranks[pr2.rank_id] = pr2

            pr3 = PrestigeRank(
                rank_id="prestige_adept",
                name="Adept",
                tier=PrestigeTier.ADEPT.value,
                level=3,
                required_prestige_xp=5000,
                honor_multiplier=1.25,
                xp_multiplier=1.10,
                unlock_description="10% XP bonus, 25% honor bonus",
                icon="icon_prestige_adept",
            )
            self._prestige_ranks[pr3.rank_id] = pr3

            pr4 = PrestigeRank(
                rank_id="prestige_expert",
                name="Expert",
                tier=PrestigeTier.EXPERT.value,
                level=4,
                required_prestige_xp=15000,
                honor_multiplier=1.5,
                xp_multiplier=1.20,
                unlock_description="20% XP bonus, 50% honor bonus",
                icon="icon_prestige_expert",
            )
            self._prestige_ranks[pr4.rank_id] = pr4

            pr5 = PrestigeRank(
                rank_id="prestige_master",
                name="Master",
                tier=PrestigeTier.MASTER.value,
                level=5,
                required_prestige_xp=50000,
                honor_multiplier=2.0,
                xp_multiplier=1.35,
                unlock_description="35% XP bonus, 100% honor bonus",
                icon="icon_prestige_master",
            )
            self._prestige_ranks[pr5.rank_id] = pr5

            # Player prestige
            self._player_prestige["player_starter"] = PlayerPrestige(
                player_id="player_starter",
                current_rank_id="prestige_apprentice",
                prestige_xp=1200,
                prestige_level=2,
                times_prestiged=1,
                total_prestige_xp=1200,
                unlocked_ranks=["prestige_novice", "prestige_apprentice"],
            )

            self._player_prestige["player_veteran"] = PlayerPrestige(
                player_id="player_veteran",
                current_rank_id="prestige_adept",
                prestige_xp=6000,
                prestige_level=3,
                times_prestiged=2,
                total_prestige_xp=6000,
                unlocked_ranks=["prestige_novice", "prestige_apprentice", "prestige_adept"],
            )

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_titles = len(self._titles)
        self._stats.total_badges = len(self._badges)
        self._stats.total_medals = len(self._medals)
        self._stats.total_player_titles = sum(
            len(tl) for tl in self._player_titles.values()
        )
        self._stats.total_player_badges = sum(
            len(bl) for bl in self._player_badges.values()
        )
        self._stats.total_player_medals = sum(
            len(ml) for ml in self._player_medals.values()
        )
        self._stats.total_honor_records = sum(
            len(b.records) for b in self._honor_balances.values()
        )
        self._stats.total_honor_awarded = sum(
            b.total_earned for b in self._honor_balances.values()
        )
        self._stats.total_honor_spent = sum(
            b.total_spent for b in self._honor_balances.values()
        )
        self._stats.total_prestige_ranks = len(self._prestige_ranks)
        self._stats.total_prestiged_players = len(self._player_prestige)
        self._stats.tick_count = self._tick_count

    def _record_event(
        self,
        kind: str,
        player_id: str = "",
        title_id: str = "",
        badge_id: str = "",
        medal_id: str = "",
        rank_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> TitleHonorEvent:
        """Record an audit event."""
        self._event_counter += 1
        event = TitleHonorEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            player_id=player_id,
            title_id=title_id,
            badge_id=badge_id,
            medal_id=medal_id,
            rank_id=rank_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # ------------------------------------------------------------------
    # Title Management
    # ------------------------------------------------------------------

    def register_title(
        self,
        title_id: str,
        name: str,
        category: str = TitleCategory.ACHIEVEMENT.value,
        rarity: str = TitleRarity.COMMON.value,
        description: str = "",
        prefix: str = "",
        suffix: str = "",
        icon: str = "",
        color_hex: str = "#FFFFFF",
        is_secret: bool = False,
        obtainable: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TitleDefinition]]:
        """Register a new title definition."""
        if not title_id or not name:
            return False, "title_id and name required", None
        if title_id in self._titles:
            return False, "title_id already exists", None
        if len(self._titles) >= _MAX_TITLES:
            return False, "title capacity reached", None
        title = TitleDefinition(
            title_id=title_id,
            name=name,
            category=category,
            rarity=rarity,
            description=description,
            prefix=prefix,
            suffix=suffix,
            icon=icon,
            color_hex=color_hex,
            is_secret=is_secret,
            obtainable=obtainable,
            metadata=metadata or {},
        )
        self._titles[title_id] = title
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.TITLE_REGISTERED.value,
            title_id=title_id,
            description=f"Title registered: {name}",
        )
        return True, "registered", title

    def remove_title(self, title_id: str) -> Tuple[bool, str]:
        """Remove a title definition."""
        if title_id not in self._titles:
            return False, "not_found"
        del self._titles[title_id]
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.TITLE_REMOVED.value,
            title_id=title_id,
            description=f"Title removed: {title_id}",
        )
        return True, "removed"

    def get_title(self, title_id: str) -> Optional[TitleDefinition]:
        """Get a title definition by ID."""
        return self._titles.get(title_id)

    def list_titles(
        self,
        category: Optional[str] = None,
        rarity: Optional[str] = None,
        limit: int = 100,
    ) -> List[TitleDefinition]:
        """List titles optionally filtered by category and rarity."""
        titles = list(self._titles.values())
        if category:
            titles = [t for t in titles if t.category == category]
        if rarity:
            titles = [t for t in titles if t.rarity == rarity]
        return titles[:limit]

    def award_title(
        self,
        player_id: str,
        title_id: str,
        source: str = "manual",
    ) -> Tuple[bool, str, Optional[PlayerTitle]]:
        """Award a title to a player."""
        if title_id not in self._titles:
            return False, "title_not_found", None
        if player_id not in self._player_titles:
            self._player_titles[player_id] = []
        titles = self._player_titles[player_id]
        if any(t.title_id == title_id for t in titles):
            return False, "already_owned", None
        if len(titles) >= self._config.max_player_titles:
            return False, "player_title_capacity", None
        pt = PlayerTitle(
            player_id=player_id,
            title_id=title_id,
            is_active=False,
            source=source,
        )
        titles.append(pt)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.TITLE_AWARDED.value,
            player_id=player_id,
            title_id=title_id,
            description=f"Title awarded: {title_id} to {player_id}",
        )
        return True, "awarded", pt

    def revoke_title(
        self, player_id: str, title_id: str
    ) -> Tuple[bool, str]:
        """Revoke a title from a player."""
        titles = self._player_titles.get(player_id, [])
        idx = -1
        for i, t in enumerate(titles):
            if t.title_id == title_id:
                idx = i
                break
        if idx < 0:
            return False, "not_found"
        titles.pop(idx)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.TITLE_REVOKED.value,
            player_id=player_id,
            title_id=title_id,
            description=f"Title revoked: {title_id} from {player_id}",
        )
        return True, "revoked"

    def activate_title(
        self, player_id: str, title_id: str
    ) -> Tuple[bool, str]:
        """Set a title as the active display title for a player."""
        titles = self._player_titles.get(player_id, [])
        found = False
        for t in titles:
            if t.title_id == title_id:
                t.is_active = True
                found = True
            else:
                t.is_active = False
        if not found:
            return False, "not_found"
        self._record_event(
            TitleHonorEventKind.TITLE_ACTIVATED.value,
            player_id=player_id,
            title_id=title_id,
            description=f"Title activated: {title_id}",
        )
        return True, "activated"

    def get_player_titles(self, player_id: str) -> List[PlayerTitle]:
        """Get all titles held by a player."""
        return list(self._player_titles.get(player_id, []))

    # ------------------------------------------------------------------
    # Badge Management
    # ------------------------------------------------------------------

    def register_badge(
        self,
        badge_id: str,
        name: str,
        badge_type: str = BadgeType.MILESTONE.value,
        description: str = "",
        icon: str = "",
        rarity: str = TitleRarity.COMMON.value,
        requirement: str = "",
        reward_honor: int = 0,
        obtainable: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BadgeDefinition]]:
        """Register a new badge definition."""
        if not badge_id or not name:
            return False, "badge_id and name required", None
        if badge_id in self._badges:
            return False, "badge_id already exists", None
        if len(self._badges) >= _MAX_BADGES:
            return False, "badge capacity reached", None
        badge = BadgeDefinition(
            badge_id=badge_id,
            name=name,
            badge_type=badge_type,
            description=description,
            icon=icon,
            rarity=rarity,
            requirement=requirement,
            reward_honor=_safe_int(reward_honor, 0),
            obtainable=obtainable,
            metadata=metadata or {},
        )
        self._badges[badge_id] = badge
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.BADGE_REGISTERED.value,
            badge_id=badge_id,
            description=f"Badge registered: {name}",
        )
        return True, "registered", badge

    def remove_badge(self, badge_id: str) -> Tuple[bool, str]:
        """Remove a badge definition."""
        if badge_id not in self._badges:
            return False, "not_found"
        del self._badges[badge_id]
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.BADGE_REMOVED.value,
            badge_id=badge_id,
            description=f"Badge removed: {badge_id}",
        )
        return True, "removed"

    def get_badge(self, badge_id: str) -> Optional[BadgeDefinition]:
        """Get a badge definition by ID."""
        return self._badges.get(badge_id)

    def list_badges(
        self, badge_type: Optional[str] = None, limit: int = 100
    ) -> List[BadgeDefinition]:
        """List badges optionally filtered by type."""
        badges = list(self._badges.values())
        if badge_type:
            badges = [b for b in badges if b.badge_type == badge_type]
        return badges[:limit]

    def award_badge(
        self,
        player_id: str,
        badge_id: str,
        progress: float = 1.0,
    ) -> Tuple[bool, str, Optional[PlayerBadge]]:
        """Award a badge to a player."""
        if badge_id not in self._badges:
            return False, "badge_not_found", None
        if player_id not in self._player_badges:
            self._player_badges[player_id] = []
        badges = self._player_badges[player_id]
        if any(b.badge_id == badge_id for b in badges):
            return False, "already_earned", None
        pb = PlayerBadge(
            player_id=player_id,
            badge_id=badge_id,
            progress=_clamp(_safe_float(progress, 1.0), 0.0, 1.0),
        )
        badges.append(pb)
        # Award bonus honor from badge
        badge = self._badges[badge_id]
        if badge.reward_honor > 0:
            self.award_honor(
                player_id,
                badge.reward_honor,
                source=HonorSource.ADMIN_GRANT.value,
                description=f"Badge reward: {badge.name}",
            )
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.BADGE_AWARDED.value,
            player_id=player_id,
            badge_id=badge_id,
            description=f"Badge awarded: {badge_id} to {player_id}",
        )
        return True, "awarded", pb

    def revoke_badge(
        self, player_id: str, badge_id: str
    ) -> Tuple[bool, str]:
        """Revoke a badge from a player."""
        badges = self._player_badges.get(player_id, [])
        idx = -1
        for i, b in enumerate(badges):
            if b.badge_id == badge_id:
                idx = i
                break
        if idx < 0:
            return False, "not_found"
        badges.pop(idx)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.BADGE_REVOKED.value,
            player_id=player_id,
            badge_id=badge_id,
            description=f"Badge revoked: {badge_id} from {player_id}",
        )
        return True, "revoked"

    def get_player_badges(self, player_id: str) -> List[PlayerBadge]:
        """Get all badges earned by a player."""
        return list(self._player_badges.get(player_id, []))

    # ------------------------------------------------------------------
    # Medal Management
    # ------------------------------------------------------------------

    def register_medal(
        self,
        medal_id: str,
        name: str,
        tier: str = MedalTier.BRONZE.value,
        description: str = "",
        icon: str = "",
        requirement: str = "",
        reward_honor: int = 0,
        reward_prestige_xp: int = 0,
        obtainable: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[MedalDefinition]]:
        """Register a new medal definition."""
        if not medal_id or not name:
            return False, "medal_id and name required", None
        if medal_id in self._medals:
            return False, "medal_id already exists", None
        if len(self._medals) >= _MAX_MEDALS:
            return False, "medal capacity reached", None
        medal = MedalDefinition(
            medal_id=medal_id,
            name=name,
            tier=tier,
            description=description,
            icon=icon,
            requirement=requirement,
            reward_honor=_safe_int(reward_honor, 0),
            reward_prestige_xp=_safe_int(reward_prestige_xp, 0),
            obtainable=obtainable,
            metadata=metadata or {},
        )
        self._medals[medal_id] = medal
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.MEDAL_REGISTERED.value,
            medal_id=medal_id,
            description=f"Medal registered: {name}",
        )
        return True, "registered", medal

    def remove_medal(self, medal_id: str) -> Tuple[bool, str]:
        """Remove a medal definition."""
        if medal_id not in self._medals:
            return False, "not_found"
        del self._medals[medal_id]
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.MEDAL_REMOVED.value,
            medal_id=medal_id,
            description=f"Medal removed: {medal_id}",
        )
        return True, "removed"

    def get_medal(self, medal_id: str) -> Optional[MedalDefinition]:
        """Get a medal definition by ID."""
        return self._medals.get(medal_id)

    def list_medals(
        self, tier: Optional[str] = None, limit: int = 100
    ) -> List[MedalDefinition]:
        """List medals optionally filtered by tier."""
        medals = list(self._medals.values())
        if tier:
            medals = [m for m in medals if m.tier == tier]
        return medals[:limit]

    def award_medal(
        self,
        player_id: str,
        medal_id: str,
        showcase_slot: int = -1,
    ) -> Tuple[bool, str, Optional[PlayerMedal]]:
        """Award a medal to a player."""
        if medal_id not in self._medals:
            return False, "medal_not_found", None
        if player_id not in self._player_medals:
            self._player_medals[player_id] = []
        medals = self._player_medals[player_id]
        if any(m.medal_id == medal_id for m in medals):
            return False, "already_earned", None
        pm = PlayerMedal(
            player_id=player_id,
            medal_id=medal_id,
            showcase_slot=_safe_int(showcase_slot, -1),
        )
        medals.append(pm)
        # Award bonus honor and prestige XP from medal
        medal = self._medals[medal_id]
        if medal.reward_honor > 0:
            self.award_honor(
                player_id,
                medal.reward_honor,
                source=HonorSource.ADMIN_GRANT.value,
                description=f"Medal reward: {medal.name}",
            )
        if medal.reward_prestige_xp > 0:
            self._add_prestige_xp(player_id, medal.reward_prestige_xp)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.MEDAL_AWARDED.value,
            player_id=player_id,
            medal_id=medal_id,
            description=f"Medal awarded: {medal_id} to {player_id}",
        )
        return True, "awarded", pm

    def revoke_medal(
        self, player_id: str, medal_id: str
    ) -> Tuple[bool, str]:
        """Revoke a medal from a player."""
        medals = self._player_medals.get(player_id, [])
        idx = -1
        for i, m in enumerate(medals):
            if m.medal_id == medal_id:
                idx = i
                break
        if idx < 0:
            return False, "not_found"
        medals.pop(idx)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.MEDAL_REVOKED.value,
            player_id=player_id,
            medal_id=medal_id,
            description=f"Medal revoked: {medal_id} from {player_id}",
        )
        return True, "revoked"

    def get_player_medals(self, player_id: str) -> List[PlayerMedal]:
        """Get all medals earned by a player."""
        return list(self._player_medals.get(player_id, []))

    # ------------------------------------------------------------------
    # Honor Management
    # ------------------------------------------------------------------

    def award_honor(
        self,
        player_id: str,
        amount: int,
        source: str = HonorSource.ADMIN_GRANT.value,
        description: str = "",
    ) -> Tuple[bool, str, Optional[HonorBalance]]:
        """Award honor points to a player. Negative amounts are penalties."""
        if not player_id:
            return False, "player_id required", None
        amt = _safe_int(amount, 0)
        if amt == 0:
            return False, "amount_must_be_nonzero", None
        if player_id not in self._honor_balances:
            self._honor_balances[player_id] = HonorBalance(player_id=player_id)
        balance = self._honor_balances[player_id]
        record = HonorRecord(
            record_id=_new_id("hr"),
            player_id=player_id,
            source=source,
            amount=amt,
            description=description,
        )
        balance.records.append(record)
        _evict_fifo_list(balance.records, _MAX_HONOR_RECORDS)
        if amt > 0:
            balance.balance += amt
            balance.total_earned += amt
        else:
            balance.balance = max(0, balance.balance + amt)
            balance.total_spent += abs(amt)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.HONOR_AWARDED.value if amt > 0 else TitleHonorEventKind.HONOR_SPENT.value,
            player_id=player_id,
            description=f"Honor {'awarded' if amt > 0 else 'spent'}: {amt} to {player_id}",
            details={"amount": amt, "source": source},
        )
        return True, "awarded" if amt > 0 else "spent", balance

    def spend_honor(
        self,
        player_id: str,
        amount: int,
        description: str = "",
    ) -> Tuple[bool, str, Optional[HonorBalance]]:
        """Spend honor points from a player's balance."""
        if not player_id:
            return False, "player_id required", None
        amt = _safe_int(amount, 0)
        if amt <= 0:
            return False, "amount_must_be_positive", None
        balance = self._honor_balances.get(player_id)
        if balance is None:
            return False, "player_not_found", None
        if balance.balance < amt:
            return False, "insufficient_honor", None
        balance.balance -= amt
        balance.total_spent += amt
        record = HonorRecord(
            record_id=_new_id("hr"),
            player_id=player_id,
            source=HonorSource.PENALTY.value,
            amount=-amt,
            description=description or "Honor spent",
        )
        balance.records.append(record)
        _evict_fifo_list(balance.records, _MAX_HONOR_RECORDS)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.HONOR_SPENT.value,
            player_id=player_id,
            description=f"Honor spent: {amt} by {player_id}",
            details={"amount": amt},
        )
        return True, "spent", balance

    def get_honor_balance(self, player_id: str) -> Optional[HonorBalance]:
        """Get the honor balance for a player."""
        return self._honor_balances.get(player_id)

    def get_honor_ranking(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get the honor ranking sorted by balance descending."""
        sorted_balances = sorted(
            self._honor_balances.values(),
            key=lambda b: b.balance,
            reverse=True,
        )
        ranking = []
        for rank_idx, b in enumerate(sorted_balances[:limit], 1):
            ranking.append({
                "rank": rank_idx,
                "player_id": b.player_id,
                "balance": b.balance,
                "total_earned": b.total_earned,
            })
        return ranking

    # ------------------------------------------------------------------
    # Prestige Management
    # ------------------------------------------------------------------

    def register_prestige_rank(
        self,
        rank_id: str,
        name: str,
        tier: str = PrestigeTier.NOVICE.value,
        level: int = 1,
        required_prestige_xp: int = 0,
        honor_multiplier: float = 1.0,
        xp_multiplier: float = 1.0,
        unlock_description: str = "",
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PrestigeRank]]:
        """Register a new prestige rank."""
        if not rank_id or not name:
            return False, "rank_id and name required", None
        if rank_id in self._prestige_ranks:
            return False, "rank_id already exists", None
        if len(self._prestige_ranks) >= _MAX_PRESTIGE_RANKS:
            return False, "prestige rank capacity reached", None
        rank = PrestigeRank(
            rank_id=rank_id,
            name=name,
            tier=tier,
            level=_safe_int(level, 1),
            required_prestige_xp=_safe_int(required_prestige_xp, 0),
            honor_multiplier=_safe_float(honor_multiplier, 1.0),
            xp_multiplier=_safe_float(xp_multiplier, 1.0),
            unlock_description=unlock_description,
            icon=icon,
            metadata=metadata or {},
        )
        self._prestige_ranks[rank_id] = rank
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.PRESTIGE_REGISTERED.value,
            rank_id=rank_id,
            description=f"Prestige rank registered: {name}",
        )
        return True, "registered", rank

    def get_prestige_rank(self, rank_id: str) -> Optional[PrestigeRank]:
        """Get a prestige rank definition by ID."""
        return self._prestige_ranks.get(rank_id)

    def list_prestige_ranks(
        self, tier: Optional[str] = None, limit: int = 100
    ) -> List[PrestigeRank]:
        """List prestige ranks optionally filtered by tier."""
        ranks = list(self._prestige_ranks.values())
        if tier:
            ranks = [r for r in ranks if r.tier == tier]
        return ranks[:limit]

    def _add_prestige_xp(self, player_id: str, xp: int) -> None:
        """Add prestige XP to a player and check for rank promotion."""
        if player_id not in self._player_prestige:
            self._player_prestige[player_id] = PlayerPrestige(
                player_id=player_id,
                current_rank_id="prestige_novice" if "prestige_novice" in self._prestige_ranks else "",
            )
            if self._player_prestige[player_id].current_rank_id:
                self._player_prestige[player_id].unlocked_ranks.append(
                    self._player_prestige[player_id].current_rank_id
                )
        pp = self._player_prestige[player_id]
        pp.prestige_xp += xp
        pp.total_prestige_xp += xp
        # Check for rank promotion
        sorted_ranks = sorted(
            self._prestige_ranks.values(),
            key=lambda r: r.required_prestige_xp,
        )
        for rank in sorted_ranks:
            if pp.prestige_xp >= rank.required_prestige_xp and rank.rank_id not in pp.unlocked_ranks:
                pp.unlocked_ranks.append(rank.rank_id)
                pp.current_rank_id = rank.rank_id
                pp.prestige_level = rank.level
                self._record_event(
                    TitleHonorEventKind.PRESTIGE_PROMOTED.value,
                    player_id=player_id,
                    rank_id=rank.rank_id,
                    description=f"Prestige promoted: {player_id} to {rank.name}",
                    details={"new_rank": rank.name, "level": rank.level},
                )

    def prestige_player(
        self, player_id: str
    ) -> Tuple[bool, str, Optional[PlayerPrestige]]:
        """Prestige a player, resetting XP for permanent bonuses."""
        if player_id not in self._player_prestige:
            return False, "player_not_found", None
        pp = self._player_prestige[player_id]
        pp.times_prestiged += 1
        pp.prestige_xp = 0
        # Keep current rank but reset to the lowest unlocked rank
        if pp.unlocked_ranks:
            sorted_ranks = sorted(
                [self._prestige_ranks[rid] for rid in pp.unlocked_ranks if rid in self._prestige_ranks],
                key=lambda r: r.required_prestige_xp,
            )
            if sorted_ranks:
                pp.current_rank_id = sorted_ranks[0].rank_id
                pp.prestige_level = sorted_ranks[0].level
        self._record_event(
            TitleHonorEventKind.PRESTIGE_PROMOTED.value,
            player_id=player_id,
            rank_id=pp.current_rank_id,
            description=f"Player prestiged: {player_id}, total: {pp.times_prestiged}",
        )
        return True, "prestiged", pp

    def get_player_prestige(self, player_id: str) -> Optional[PlayerPrestige]:
        """Get the prestige progression for a player."""
        return self._player_prestige.get(player_id)

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats, Status, Snapshot, Reset
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the simulation by dt seconds."""
        self._tick_count += 1
        # Apply honor decay if configured
        if self._config.honor_decay_rate > 0:
            for balance in self._honor_balances.values():
                decay = int(balance.balance * self._config.honor_decay_rate * dt)
                if decay > 0:
                    balance.balance = max(0, balance.balance - decay)
        self._refresh_stats()
        self._record_event(
            TitleHonorEventKind.TICK.value,
            description=f"Tick {self._tick_count}",
            details={"dt": dt, "tick_count": self._tick_count},
        )
        return {
            "tick_count": self._tick_count,
            "total_titles": self._stats.total_titles,
            "total_honor_records": self._stats.total_honor_records,
        }

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, TitleHonorConfig]:
        """Update configuration parameters."""
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        self._record_event(
            TitleHonorEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
            details=kwargs,
        )
        return True, "updated", self._config

    def get_config(self) -> TitleHonorConfig:
        """Get current configuration."""
        return self._config

    def list_events(
        self, kind: Optional[str] = None, limit: int = 100
    ) -> List[TitleHonorEvent]:
        """List events optionally filtered by kind."""
        events = list(self._events)
        if kind:
            events = [e for e in events if e.kind == kind]
        return events[-limit:]

    def get_stats(self) -> TitleHonorStats:
        """Get aggregate statistics."""
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Get system status summary."""
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_titles": len(self._titles),
            "total_badges": len(self._badges),
            "total_medals": len(self._medals),
            "total_prestige_ranks": len(self._prestige_ranks),
            "total_honor_balances": len(self._honor_balances),
            "total_prestiged_players": len(self._player_prestige),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> TitleHonorSnapshot:
        """Get full state snapshot."""
        self._refresh_stats()
        return TitleHonorSnapshot(
            titles=[t.to_dict() for t in list(self._titles.values())[:50]],
            badges=[b.to_dict() for b in list(self._badges.values())[:50]],
            medals=[m.to_dict() for m in list(self._medals.values())[:50]],
            prestige_ranks=[r.to_dict() for r in list(self._prestige_ranks.values())[:50]],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        """Reset the system to seed state."""
        with self._init_lock:
            self._titles.clear()
            self._badges.clear()
            self._medals.clear()
            self._player_titles.clear()
            self._player_badges.clear()
            self._player_medals.clear()
            self._honor_balances.clear()
            self._prestige_ranks.clear()
            self._player_prestige.clear()
            self._events.clear()
            self._stats = TitleHonorStats()
            self._config = TitleHonorConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            TitleHonorEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_title_honor_system() -> TitleHonorSystem:
    """Factory function to get the TitleHonorSystem singleton instance."""
    return TitleHonorSystem.get_instance()
