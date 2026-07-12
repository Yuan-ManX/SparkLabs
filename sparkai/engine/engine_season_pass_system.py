"""
SparkLabs Engine - Season Pass System

Manages seasonal progression tracks with free and premium reward paths,
daily/weekly challenges, tier-based unlocks, XP earning, and season
metadata. Players earn season XP through gameplay and challenges to
progress through tiers, unlocking cosmetic and gameplay rewards.

Architecture:
  SeasonPassSystem (singleton)
    |-- SeasonTrack, ChallengeType, ChallengeStatus, SeasonStatus,
       SeasonEventKind
    |-- SeasonReward, SeasonTier, SeasonChallenge, PlayerSeasonProgress,
       ChallengeCompletion, SeasonDefinition, SeasonConfig, SeasonStats,
       SeasonSnapshot, SeasonEvent
    |-- get_season_pass_system

Core Capabilities:
  - register_season / remove_season / get_season / list_seasons
  - start_season / end_season / get_active_season
  - register_tier / get_tier / list_tiers
  - register_reward / remove_reward / get_reward / list_rewards
  - register_challenge / remove_challenge / get_challenge / list_challenges
  - register_player / get_player_progress / list_player_progress
  - add_season_xp / claim_tier_reward / claim_challenge_reward
  - complete_challenge / reset_challenge_progress
  - purchase_premium / get_premium_status
  - tick / set_config / get_config
  - list_events / get_stats / get_status / get_snapshot / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SeasonPassSystem.get_instance` or the module-level
:func:`get_season_pass_system` factory.
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

_MAX_SEASONS: int = 50
_MAX_TIERS_PER_SEASON: int = 200
_MAX_REWARDS_PER_SEASON: int = 2000
_MAX_CHALLENGES_PER_SEASON: int = 500
_MAX_PLAYER_PROGRESS: int = 100000
_MAX_COMPLETIONS: int = 500000
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

class SeasonTrack(str, Enum):
    """Reward track type."""
    FREE = "free"
    PREMIUM = "premium"


class ChallengeType(str, Enum):
    """Challenge frequency category."""
    DAILY = "daily"
    WEEKLY = "weekly"
    SEASON = "season"
    EVENT = "event"


class ChallengeStatus(str, Enum):
    """Status of a challenge for a player."""
    LOCKED = "locked"
    ACTIVE = "active"
    COMPLETED = "completed"
    CLAIMED = "claimed"
    EXPIRED = "expired"


class SeasonStatus(str, Enum):
    """Status of a season."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    ACTIVE = "active"
    ENDED = "ended"
    ARCHIVED = "archived"


class RewardType(str, Enum):
    """Type of reward."""
    COSMETIC = "cosmetic"
    CURRENCY = "currency"
    ITEM = "item"
    EXPERIENCE = "experience"
    MOUNT = "mount"
    TITLE = "title"
    EMOTE = "emote"
    BUNDLE = "bundle"


class SeasonEventKind(str, Enum):
    """Audit event types emitted by the season pass system."""
    SEASON_REGISTERED = "season_registered"
    SEASON_REMOVED = "season_removed"
    SEASON_STARTED = "season_started"
    SEASON_ENDED = "season_ended"
    TIER_REGISTERED = "tier_registered"
    REWARD_REGISTERED = "reward_registered"
    REWARD_REMOVED = "reward_removed"
    CHALLENGE_REGISTERED = "challenge_registered"
    CHALLENGE_REMOVED = "challenge_removed"
    PLAYER_REGISTERED = "player_registered"
    XP_ADDED = "xp_added"
    TIER_UNLOCKED = "tier_unlocked"
    REWARD_CLAIMED = "reward_claimed"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_CLAIMED = "challenge_claimed"
    PREMIUM_PURCHASED = "premium_purchased"
    CHALLENGE_RESET = "challenge_reset"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class SeasonReward:
    """A reward available at a specific tier on a specific track."""
    reward_id: str
    season_id: str
    tier_number: int
    track: str = SeasonTrack.FREE.value
    reward_type: str = RewardType.CURRENCY.value
    name: str = ""
    description: str = ""
    reward_data: Dict[str, Any] = field(default_factory=dict)
    icon: str = ""
    rarity: str = "common"
    claimed_by: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonTier:
    """A tier definition within a season."""
    season_id: str
    tier_number: int
    xp_required: int = 1000
    name: str = ""
    description: str = ""
    is_milestone: bool = False
    free_reward_ids: List[str] = field(default_factory=list)
    premium_reward_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonChallenge:
    """A challenge that grants season XP when completed."""
    challenge_id: str
    season_id: str
    name: str
    description: str = ""
    challenge_type: str = ChallengeType.DAILY.value
    xp_reward: int = 100
    target_value: int = 1
    metric: str = "kills"
    starts_at: float = 0.0
    ends_at: float = 0.0
    repeatable: bool = False
    max_repeats: int = 0
    required_tier: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ChallengeCompletion:
    """Tracks a player's progress on a specific challenge."""
    completion_id: str
    challenge_id: str
    player_id: str
    season_id: str
    current_value: int = 0
    status: str = ChallengeStatus.ACTIVE.value
    completed_at: float = 0.0
    claimed_at: float = 0.0
    repeat_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerSeasonProgress:
    """A player's progression through a season."""
    progress_id: str
    season_id: str
    player_id: str
    total_xp: int = 0
    current_tier: int = 0
    max_tier_reached: int = 0
    has_premium: bool = False
    premium_purchased_at: float = 0.0
    claimed_tier_rewards: List[int] = field(default_factory=list)
    claimed_track: Dict[str, bool] = field(default_factory=dict)
    challenge_completions: List[str] = field(default_factory=list)
    daily_streak: int = 0
    last_daily_reset: float = 0.0
    registered_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonDefinition:
    """Definition of a season."""
    season_id: str
    name: str
    description: str = ""
    season_number: int = 1
    status: str = SeasonStatus.DRAFT.value
    max_tiers: int = 50
    xp_per_tier: int = 1000
    starts_at: float = 0.0
    ends_at: float = 0.0
    premium_cost: float = 9.99
    premium_currency: str = "usd"
    theme: str = "default"
    banner_icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonConfig:
    """Global tuning parameters."""
    max_seasons: int = 50
    max_tiers_per_season: int = 200
    max_rewards_per_season: int = 2000
    max_challenges_per_season: int = 500
    max_player_progress: int = 100000
    daily_challenge_count: int = 3
    weekly_challenge_count: int = 5
    season_challenge_count: int = 10
    xp_multiplier: float = 1.0
    daily_reset_hour: int = 0
    weekly_reset_day: int = 1
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonStats:
    """Aggregate statistics."""
    total_seasons: int = 0
    active_seasons: int = 0
    total_tiers: int = 0
    total_rewards: int = 0
    total_challenges: int = 0
    total_player_progress: int = 0
    total_premium_players: int = 0
    total_xp_earned: int = 0
    total_rewards_claimed: int = 0
    total_challenges_completed: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonSnapshot:
    """Full state snapshot."""
    seasons: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SeasonEvent:
    """An audit event."""
    event_id: str
    kind: str
    timestamp: float
    season_id: str = ""
    player_id: str = ""
    tier_number: int = 0
    challenge_id: str = ""
    reward_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Season Pass System
# ---------------------------------------------------------------------------

class SeasonPassSystem:
    """Manages seasonal progression, challenges, and reward tracks."""

    _instance: Optional["SeasonPassSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._seasons: Dict[str, SeasonDefinition] = {}
        self._tiers: Dict[str, SeasonTier] = {}
        self._rewards: Dict[str, SeasonReward] = {}
        self._challenges: Dict[str, SeasonChallenge] = {}
        self._progress: Dict[str, PlayerSeasonProgress] = {}
        self._completions: Dict[str, ChallengeCompletion] = {}
        self._active_season_id: str = ""
        self._events: List[SeasonEvent] = []
        self._stats = SeasonStats()
        self._config = SeasonConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "SeasonPassSystem":
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

            # Season 1: Dragon Forge
            s1 = SeasonDefinition(
                season_id="season_dragon_forge",
                name="Dragon Forge",
                description="Forge your legend in the fires of the dragon season.",
                season_number=1,
                status=SeasonStatus.ACTIVE.value,
                max_tiers=50,
                xp_per_tier=1000,
                starts_at=_now() - 86400,
                ends_at=_now() + 86400 * 60,
                premium_cost=9.99,
                premium_currency="usd",
                theme="dragon",
                banner_icon="banner_dragon",
            )
            self._seasons[s1.season_id] = s1
            self._active_season_id = s1.season_id

            # Seed tiers 1-5 with rewards
            for tier_num in range(1, 6):
                xp_req = tier_num * s1.xp_per_tier
                tier = SeasonTier(
                    season_id=s1.season_id,
                    tier_number=tier_num,
                    xp_required=xp_req,
                    name=f"Tier {tier_num}",
                    description=f"Dragon Forge Tier {tier_num}",
                    is_milestone=(tier_num % 10 == 0),
                )
                tier_key = f"{s1.season_id}:{tier_num}"
                self._tiers[tier_key] = tier

                # Free reward for this tier
                free_rid = f"reward_s1_t{tier_num}_free"
                free_reward = SeasonReward(
                    reward_id=free_rid,
                    season_id=s1.season_id,
                    tier_number=tier_num,
                    track=SeasonTrack.FREE.value,
                    reward_type=RewardType.CURRENCY.value,
                    name=f"Free Reward T{tier_num}",
                    description=f"Gold coins for tier {tier_num}",
                    reward_data={"currency": "gold", "amount": 100 * tier_num},
                    icon=f"icon_free_t{tier_num}",
                    rarity="common" if tier_num < 3 else "uncommon",
                )
                self._rewards[free_rid] = free_reward
                tier.free_reward_ids.append(free_rid)

                # Premium reward for this tier
                prem_rid = f"reward_s1_t{tier_num}_premium"
                prem_reward = SeasonReward(
                    reward_id=prem_rid,
                    season_id=s1.season_id,
                    tier_number=tier_num,
                    track=SeasonTrack.PREMIUM.value,
                    reward_type=RewardType.COSMETIC.value if tier_num < 5 else RewardType.MOUNT.value,
                    name=f"Premium Reward T{tier_num}",
                    description=f"Exclusive cosmetic for tier {tier_num}",
                    reward_data={"item_id": f"cosmetic_s1_t{tier_num}", "rarity": "rare"},
                    icon=f"icon_prem_t{tier_num}",
                    rarity="rare" if tier_num < 5 else "epic",
                )
                self._rewards[prem_rid] = prem_reward
                tier.premium_reward_ids.append(prem_rid)

            # Seed challenges
            challenges_data = [
                ("challenge_s1_daily_01", "Daily Slay", "Defeat 10 enemies",
                 ChallengeType.DAILY.value, 100, 10, "kills"),
                ("challenge_s1_daily_02", "Daily Gather", "Gather 5 resources",
                 ChallengeType.DAILY.value, 100, 5, "gathers"),
                ("challenge_s1_daily_03", "Daily Explorer", "Discover 3 new locations",
                 ChallengeType.DAILY.value, 100, 3, "discoveries"),
                ("challenge_s1_weekly_01", "Weekly Boss", "Defeat 3 bosses",
                 ChallengeType.WEEKLY.value, 500, 3, "boss_kills"),
                ("challenge_s1_weekly_02", "Weekly Dungeon", "Complete 5 dungeons",
                 ChallengeType.WEEKLY.value, 500, 5, "dungeon_completions"),
                ("challenge_s1_season_01", "Season Legend", "Reach tier 25",
                 ChallengeType.SEASON.value, 5000, 25, "tier_reached"),
                ("challenge_s1_season_02", "Season Collector", "Collect 100 items",
                 ChallengeType.SEASON.value, 3000, 100, "items_collected"),
            ]
            for cid, name, desc, ctype, xp, target, metric in challenges_data:
                ch = SeasonChallenge(
                    challenge_id=cid,
                    season_id=s1.season_id,
                    name=name,
                    description=desc,
                    challenge_type=ctype,
                    xp_reward=xp,
                    target_value=target,
                    metric=metric,
                    starts_at=s1.starts_at,
                    ends_at=s1.ends_at,
                )
                self._challenges[cid] = ch

            # Seed player progress
            pp1 = PlayerSeasonProgress(
                progress_id="progress_player_starter_s1",
                season_id=s1.season_id,
                player_id="player_starter",
                total_xp=2500,
                current_tier=2,
                max_tier_reached=2,
                has_premium=False,
            )
            self._progress[pp1.progress_id] = pp1

            pp2 = PlayerSeasonProgress(
                progress_id="progress_player_veteran_s1",
                season_id=s1.season_id,
                player_id="player_veteran",
                total_xp=15000,
                current_tier=15,
                max_tier_reached=15,
                has_premium=True,
                premium_purchased_at=_now() - 86400 * 10,
                claimed_tier_rewards=[1, 2, 3, 4, 5],
            )
            self._progress[pp2.progress_id] = pp2

            # Seed a challenge completion
            cc1 = ChallengeCompletion(
                completion_id="completion_starter_daily_01",
                challenge_id="challenge_s1_daily_01",
                player_id="player_starter",
                season_id=s1.season_id,
                current_value=7,
                status=ChallengeStatus.ACTIVE.value,
            )
            self._completions[cc1.completion_id] = cc1

            cc2 = ChallengeCompletion(
                completion_id="completion_veteran_weekly_01",
                challenge_id="challenge_s1_weekly_01",
                player_id="player_veteran",
                season_id=s1.season_id,
                current_value=3,
                status=ChallengeStatus.COMPLETED.value,
                completed_at=_now() - 3600,
            )
            self._completions[cc2.completion_id] = cc2

            # Season 2 (scheduled, not yet active)
            s2 = SeasonDefinition(
                season_id="season_frost_realm",
                name="Frost Realm",
                description="Brave the frozen wastes of the frost realm.",
                season_number=2,
                status=SeasonStatus.SCHEDULED.value,
                max_tiers=50,
                xp_per_tier=1000,
                starts_at=s1.ends_at,
                ends_at=s1.ends_at + 86400 * 60,
                premium_cost=9.99,
                theme="frost",
                banner_icon="banner_frost",
            )
            self._seasons[s2.season_id] = s2

            self._update_stats()
            self._initialized = True

    def _update_stats(self) -> None:
        self._stats.total_seasons = len(self._seasons)
        self._stats.active_seasons = sum(
            1 for s in self._seasons.values()
            if s.status == SeasonStatus.ACTIVE.value
        )
        self._stats.total_tiers = len(self._tiers)
        self._stats.total_rewards = len(self._rewards)
        self._stats.total_challenges = len(self._challenges)
        self._stats.total_player_progress = len(self._progress)
        self._stats.total_premium_players = sum(
            1 for p in self._progress.values() if p.has_premium
        )
        self._stats.total_xp_earned = sum(p.total_xp for p in self._progress.values())
        self._stats.total_rewards_claimed = sum(
            len(p.claimed_tier_rewards) for p in self._progress.values()
        )
        self._stats.total_challenges_completed = sum(
            1 for c in self._completions.values()
            if c.status in (ChallengeStatus.COMPLETED.value, ChallengeStatus.CLAIMED.value)
        )

    def _log_event(self, kind: str, details: Dict[str, Any],
                   season_id: str = "", player_id: str = "",
                   tier_number: int = 0, challenge_id: str = "",
                   reward_id: str = "", description: str = "") -> None:
        event = SeasonEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            season_id=season_id,
            player_id=player_id,
            tier_number=tier_number,
            challenge_id=challenge_id,
            reward_id=reward_id,
            description=description,
            details=details,
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Season Management
    # ------------------------------------------------------------------

    def register_season(self, season_id: str, name: str, description: str = "",
                        season_number: int = 1, max_tiers: int = 50,
                        xp_per_tier: int = 1000, starts_at: float = 0.0,
                        ends_at: float = 0.0, premium_cost: float = 9.99,
                        premium_currency: str = "usd", theme: str = "default",
                        banner_icon: str = "") -> Tuple[bool, str, Optional[SeasonDefinition]]:
        with _LOCK:
            if season_id in self._seasons:
                return False, "season_exists", None
            if len(self._seasons) >= _MAX_SEASONS:
                return False, "max_seasons", None
            season = SeasonDefinition(
                season_id=season_id, name=name, description=description,
                season_number=season_number, status=SeasonStatus.DRAFT.value,
                max_tiers=max_tiers, xp_per_tier=xp_per_tier,
                starts_at=starts_at, ends_at=ends_at,
                premium_cost=premium_cost, premium_currency=premium_currency,
                theme=theme, banner_icon=banner_icon,
            )
            self._seasons[season_id] = season
            self._log_event(SeasonEventKind.SEASON_REGISTERED.value,
                            {"name": name}, season_id=season_id)
            self._update_stats()
            return True, "registered", season

    def remove_season(self, season_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if season_id not in self._seasons:
                return False, "season_not_found"
            if season_id == self._active_season_id:
                return False, "season_active"
            del self._seasons[season_id]
            # Clean up related data
            tier_keys_to_remove = [
                k for k in self._tiers if k.startswith(f"{season_id}:")
            ]
            for k in tier_keys_to_remove:
                del self._tiers[k]
            reward_ids_to_remove = [
                rid for rid, r in self._rewards.items() if r.season_id == season_id
            ]
            for rid in reward_ids_to_remove:
                del self._rewards[rid]
            challenge_ids_to_remove = [
                cid for cid, c in self._challenges.items() if c.season_id == season_id
            ]
            for cid in challenge_ids_to_remove:
                del self._challenges[cid]
            progress_ids_to_remove = [
                pid for pid, p in self._progress.items() if p.season_id == season_id
            ]
            for pid in progress_ids_to_remove:
                del self._progress[pid]
            completion_ids_to_remove = [
                cpid for cpid, c in self._completions.items() if c.season_id == season_id
            ]
            for cpid in completion_ids_to_remove:
                del self._completions[cpid]
            self._log_event(SeasonEventKind.SEASON_REMOVED.value,
                            {"season_id": season_id})
            self._update_stats()
            return True, "removed"

    def get_season(self, season_id: str) -> Optional[SeasonDefinition]:
        with _LOCK:
            return self._seasons.get(season_id)

    def list_seasons(self, status: str = "") -> List[SeasonDefinition]:
        with _LOCK:
            if status:
                return [s for s in self._seasons.values() if s.status == status]
            return list(self._seasons.values())

    def start_season(self, season_id: str) -> Tuple[bool, str, Optional[SeasonDefinition]]:
        with _LOCK:
            season = self._seasons.get(season_id)
            if season is None:
                return False, "season_not_found", None
            if season.status == SeasonStatus.ACTIVE.value:
                return False, "already_active", season
            if season.status == SeasonStatus.ENDED.value:
                return False, "season_ended", season
            season.status = SeasonStatus.ACTIVE.value
            self._active_season_id = season_id
            self._log_event(SeasonEventKind.SEASON_STARTED.value,
                            {"season_id": season_id}, season_id=season_id)
            self._update_stats()
            return True, "started", season

    def end_season(self, season_id: str) -> Tuple[bool, str, Optional[SeasonDefinition]]:
        with _LOCK:
            season = self._seasons.get(season_id)
            if season is None:
                return False, "season_not_found", None
            if season.status != SeasonStatus.ACTIVE.value:
                return False, "not_active", season
            season.status = SeasonStatus.ENDED.value
            if self._active_season_id == season_id:
                self._active_season_id = ""
            self._log_event(SeasonEventKind.SEASON_ENDED.value,
                            {"season_id": season_id}, season_id=season_id)
            self._update_stats()
            return True, "ended", season

    def get_active_season(self) -> Optional[SeasonDefinition]:
        with _LOCK:
            if self._active_season_id:
                return self._seasons.get(self._active_season_id)
            return None

    # ------------------------------------------------------------------
    # Tier Management
    # ------------------------------------------------------------------

    def register_tier(self, season_id: str, tier_number: int,
                      xp_required: int = 0, name: str = "",
                      description: str = "", is_milestone: bool = False
                      ) -> Tuple[bool, str, Optional[SeasonTier]]:
        with _LOCK:
            season = self._seasons.get(season_id)
            if season is None:
                return False, "season_not_found", None
            tier_key = f"{season_id}:{tier_number}"
            if tier_key in self._tiers:
                return False, "tier_exists", None
            if len(self._tiers) >= _MAX_TIERS_PER_SEASON * _MAX_SEASONS:
                return False, "max_tiers", None
            if xp_required <= 0:
                xp_required = tier_number * season.xp_per_tier
            tier = SeasonTier(
                season_id=season_id, tier_number=tier_number,
                xp_required=xp_required, name=name or f"Tier {tier_number}",
                description=description, is_milestone=is_milestone,
            )
            self._tiers[tier_key] = tier
            self._log_event(SeasonEventKind.TIER_REGISTERED.value,
                            {"tier_number": tier_number}, season_id=season_id,
                            tier_number=tier_number)
            self._update_stats()
            return True, "registered", tier

    def get_tier(self, season_id: str, tier_number: int) -> Optional[SeasonTier]:
        with _LOCK:
            return self._tiers.get(f"{season_id}:{tier_number}")

    def list_tiers(self, season_id: str) -> List[SeasonTier]:
        with _LOCK:
            return [
                t for k, t in self._tiers.items()
                if k.startswith(f"{season_id}:")
            ]

    # ------------------------------------------------------------------
    # Reward Management
    # ------------------------------------------------------------------

    def register_reward(self, reward_id: str, season_id: str, tier_number: int,
                        track: str = SeasonTrack.FREE.value,
                        reward_type: str = RewardType.CURRENCY.value,
                        name: str = "", description: str = "",
                        reward_data: Optional[Dict[str, Any]] = None,
                        icon: str = "", rarity: str = "common"
                        ) -> Tuple[bool, str, Optional[SeasonReward]]:
        with _LOCK:
            if reward_id in self._rewards:
                return False, "reward_exists", None
            if season_id not in self._seasons:
                return False, "season_not_found", None
            if len(self._rewards) >= _MAX_REWARDS_PER_SEASON * _MAX_SEASONS:
                return False, "max_rewards", None
            reward = SeasonReward(
                reward_id=reward_id, season_id=season_id, tier_number=tier_number,
                track=track, reward_type=reward_type, name=name,
                description=description, reward_data=reward_data or {},
                icon=icon, rarity=rarity,
            )
            self._rewards[reward_id] = reward
            # Link to tier
            tier_key = f"{season_id}:{tier_number}"
            tier = self._tiers.get(tier_key)
            if tier:
                if track == SeasonTrack.PREMIUM.value:
                    tier.premium_reward_ids.append(reward_id)
                else:
                    tier.free_reward_ids.append(reward_id)
            self._log_event(SeasonEventKind.REWARD_REGISTERED.value,
                            {"name": name}, season_id=season_id,
                            tier_number=tier_number, reward_id=reward_id)
            self._update_stats()
            return True, "registered", reward

    def remove_reward(self, reward_id: str) -> Tuple[bool, str]:
        with _LOCK:
            reward = self._rewards.get(reward_id)
            if reward is None:
                return False, "reward_not_found"
            del self._rewards[reward_id]
            # Unlink from tier
            tier_key = f"{reward.season_id}:{reward.tier_number}"
            tier = self._tiers.get(tier_key)
            if tier:
                if reward.track == SeasonTrack.PREMIUM.value:
                    if reward_id in tier.premium_reward_ids:
                        tier.premium_reward_ids.remove(reward_id)
                else:
                    if reward_id in tier.free_reward_ids:
                        tier.free_reward_ids.remove(reward_id)
            self._log_event(SeasonEventKind.REWARD_REMOVED.value,
                            {"reward_id": reward_id}, reward_id=reward_id)
            self._update_stats()
            return True, "removed"

    def get_reward(self, reward_id: str) -> Optional[SeasonReward]:
        with _LOCK:
            return self._rewards.get(reward_id)

    def list_rewards(self, season_id: str = "", tier_number: int = 0,
                     track: str = "") -> List[SeasonReward]:
        with _LOCK:
            results = list(self._rewards.values())
            if season_id:
                results = [r for r in results if r.season_id == season_id]
            if tier_number > 0:
                results = [r for r in results if r.tier_number == tier_number]
            if track:
                results = [r for r in results if r.track == track]
            return results

    # ------------------------------------------------------------------
    # Challenge Management
    # ------------------------------------------------------------------

    def register_challenge(self, challenge_id: str, season_id: str,
                           name: str, description: str = "",
                           challenge_type: str = ChallengeType.DAILY.value,
                           xp_reward: int = 100, target_value: int = 1,
                           metric: str = "kills", starts_at: float = 0.0,
                           ends_at: float = 0.0, repeatable: bool = False,
                           max_repeats: int = 0, required_tier: int = 0
                           ) -> Tuple[bool, str, Optional[SeasonChallenge]]:
        with _LOCK:
            if challenge_id in self._challenges:
                return False, "challenge_exists", None
            if season_id not in self._seasons:
                return False, "season_not_found", None
            if len(self._challenges) >= _MAX_CHALLENGES_PER_SEASON * _MAX_SEASONS:
                return False, "max_challenges", None
            ch = SeasonChallenge(
                challenge_id=challenge_id, season_id=season_id,
                name=name, description=description,
                challenge_type=challenge_type, xp_reward=xp_reward,
                target_value=target_value, metric=metric,
                starts_at=starts_at, ends_at=ends_at,
                repeatable=repeatable, max_repeats=max_repeats,
                required_tier=required_tier,
            )
            self._challenges[challenge_id] = ch
            self._log_event(SeasonEventKind.CHALLENGE_REGISTERED.value,
                            {"name": name}, season_id=season_id,
                            challenge_id=challenge_id)
            self._update_stats()
            return True, "registered", ch

    def remove_challenge(self, challenge_id: str) -> Tuple[bool, str]:
        with _LOCK:
            if challenge_id not in self._challenges:
                return False, "challenge_not_found"
            del self._challenges[challenge_id]
            # Remove completions for this challenge
            cids_to_remove = [
                cpid for cpid, c in self._completions.items()
                if c.challenge_id == challenge_id
            ]
            for cpid in cids_to_remove:
                del self._completions[cpid]
            self._log_event(SeasonEventKind.CHALLENGE_REMOVED.value,
                            {"challenge_id": challenge_id},
                            challenge_id=challenge_id)
            self._update_stats()
            return True, "removed"

    def get_challenge(self, challenge_id: str) -> Optional[SeasonChallenge]:
        with _LOCK:
            return self._challenges.get(challenge_id)

    def list_challenges(self, season_id: str = "",
                        challenge_type: str = "") -> List[SeasonChallenge]:
        with _LOCK:
            results = list(self._challenges.values())
            if season_id:
                results = [c for c in results if c.season_id == season_id]
            if challenge_type:
                results = [c for c in results if c.challenge_type == challenge_type]
            return results

    # ------------------------------------------------------------------
    # Player Progress Management
    # ------------------------------------------------------------------

    def register_player(self, season_id: str, player_id: str
                        ) -> Tuple[bool, str, Optional[PlayerSeasonProgress]]:
        with _LOCK:
            if season_id not in self._seasons:
                return False, "season_not_found", None
            # Check if player already registered for this season
            for p in self._progress.values():
                if p.season_id == season_id and p.player_id == player_id:
                    return False, "player_exists", p
            if len(self._progress) >= _MAX_PLAYER_PROGRESS:
                return False, "max_progress", None
            progress_id = _new_id("progress")
            progress = PlayerSeasonProgress(
                progress_id=progress_id, season_id=season_id,
                player_id=player_id,
            )
            self._progress[progress_id] = progress
            self._log_event(SeasonEventKind.PLAYER_REGISTERED.value,
                            {"player_id": player_id},
                            season_id=season_id, player_id=player_id)
            self._update_stats()
            return True, "registered", progress

    def get_player_progress(self, season_id: str, player_id: str
                            ) -> Optional[PlayerSeasonProgress]:
        with _LOCK:
            for p in self._progress.values():
                if p.season_id == season_id and p.player_id == player_id:
                    return p
            return None

    def list_player_progress(self, season_id: str = "",
                             player_id: str = "") -> List[PlayerSeasonProgress]:
        with _LOCK:
            results = list(self._progress.values())
            if season_id:
                results = [p for p in results if p.season_id == season_id]
            if player_id:
                results = [p for p in results if p.player_id == player_id]
            return results

    def add_season_xp(self, season_id: str, player_id: str,
                      amount: int) -> Tuple[bool, str, Optional[PlayerSeasonProgress], List[int]]:
        """Add XP to a player's season progress. Returns unlocked tier numbers."""
        with _LOCK:
            progress = self.get_player_progress(season_id, player_id)
            if progress is None:
                return False, "progress_not_found", None, []
            season = self._seasons.get(season_id)
            if season is None:
                return False, "season_not_found", None, []
            xp_to_add = int(amount * self._config.xp_multiplier)
            old_tier = progress.current_tier
            progress.total_xp += xp_to_add
            # Recalculate current tier
            new_tier = min(
                progress.total_xp // season.xp_per_tier,
                season.max_tiers
            )
            progress.current_tier = new_tier
            unlocked_tiers: List[int] = []
            if new_tier > old_tier:
                for t in range(old_tier + 1, new_tier + 1):
                    unlocked_tiers.append(t)
                progress.max_tier_reached = max(progress.max_tier_reached, new_tier)
                self._log_event(SeasonEventKind.TIER_UNLOCKED.value,
                                {"tier": new_tier, "unlocked": unlocked_tiers},
                                season_id=season_id, player_id=player_id,
                                tier_number=new_tier)
            self._log_event(SeasonEventKind.XP_ADDED.value,
                            {"amount": xp_to_add, "total": progress.total_xp},
                            season_id=season_id, player_id=player_id)
            self._update_stats()
            return True, "added", progress, unlocked_tiers

    def claim_tier_reward(self, season_id: str, player_id: str,
                          tier_number: int, track: str = SeasonTrack.FREE.value
                          ) -> Tuple[bool, str, Optional[SeasonReward]]:
        with _LOCK:
            progress = self.get_player_progress(season_id, player_id)
            if progress is None:
                return False, "progress_not_found", None
            if progress.current_tier < tier_number:
                return False, "tier_not_reached", None
            if track == SeasonTrack.PREMIUM.value and not progress.has_premium:
                return False, "no_premium", None
            claim_key = f"{tier_number}:{track}"
            if claim_key in progress.claimed_track:
                return False, "already_claimed", None
            # Find reward for this tier/track
            rewards = self.list_rewards(season_id=season_id, tier_number=tier_number, track=track)
            if not rewards:
                return False, "no_reward", None
            reward = rewards[0]
            progress.claimed_track[claim_key] = True
            if tier_number not in progress.claimed_tier_rewards:
                progress.claimed_tier_rewards.append(tier_number)
            reward.claimed_by.append(player_id)
            self._log_event(SeasonEventKind.REWARD_CLAIMED.value,
                            {"tier": tier_number, "track": track},
                            season_id=season_id, player_id=player_id,
                            tier_number=tier_number, reward_id=reward.reward_id)
            self._update_stats()
            return True, "claimed", reward

    def purchase_premium(self, season_id: str, player_id: str
                         ) -> Tuple[bool, str, Optional[PlayerSeasonProgress]]:
        with _LOCK:
            progress = self.get_player_progress(season_id, player_id)
            if progress is None:
                return False, "progress_not_found", None
            if progress.has_premium:
                return False, "already_premium", progress
            progress.has_premium = True
            progress.premium_purchased_at = _now()
            self._log_event(SeasonEventKind.PREMIUM_PURCHASED.value,
                            {"player_id": player_id},
                            season_id=season_id, player_id=player_id)
            self._update_stats()
            return True, "purchased", progress

    def get_premium_status(self, season_id: str, player_id: str) -> bool:
        with _LOCK:
            progress = self.get_player_progress(season_id, player_id)
            return progress is not None and progress.has_premium

    # ------------------------------------------------------------------
    # Challenge Progress
    # ------------------------------------------------------------------

    def complete_challenge(self, challenge_id: str, player_id: str,
                           value: int = 0) -> Tuple[bool, str, Optional[ChallengeCompletion]]:
        with _LOCK:
            ch = self._challenges.get(challenge_id)
            if ch is None:
                return False, "challenge_not_found", None
            progress = self.get_player_progress(ch.season_id, player_id)
            if progress is None:
                return False, "progress_not_found", None
            # Find or create completion
            completion: Optional[ChallengeCompletion] = None
            for c in self._completions.values():
                if c.challenge_id == challenge_id and c.player_id == player_id:
                    completion = c
                    break
            if completion is None:
                completion = ChallengeCompletion(
                    completion_id=_new_id("completion"),
                    challenge_id=challenge_id, player_id=player_id,
                    season_id=ch.season_id,
                )
                self._completions[completion.completion_id] = completion
                progress.challenge_completions.append(completion.completion_id)
            completion.current_value += value if value > 0 else ch.target_value
            if completion.current_value >= ch.target_value:
                if completion.status != ChallengeStatus.COMPLETED.value:
                    completion.status = ChallengeStatus.COMPLETED.value
                    completion.completed_at = _now()
                    # Award XP
                    self.add_season_xp(ch.season_id, player_id, ch.xp_reward)
                    self._log_event(SeasonEventKind.CHALLENGE_COMPLETED.value,
                                    {"challenge_id": challenge_id, "xp": ch.xp_reward},
                                    season_id=ch.season_id, player_id=player_id,
                                    challenge_id=challenge_id)
            self._update_stats()
            return True, "updated", completion

    def claim_challenge_reward(self, challenge_id: str, player_id: str
                               ) -> Tuple[bool, str, Optional[ChallengeCompletion]]:
        with _LOCK:
            ch = self._challenges.get(challenge_id)
            if ch is None:
                return False, "challenge_not_found", None
            completion: Optional[ChallengeCompletion] = None
            for c in self._completions.values():
                if c.challenge_id == challenge_id and c.player_id == player_id:
                    completion = c
                    break
            if completion is None:
                return False, "completion_not_found", None
            if completion.status != ChallengeStatus.COMPLETED.value:
                return False, "not_completed", completion
            if completion.status == ChallengeStatus.CLAIMED.value:
                return False, "already_claimed", completion
            completion.status = ChallengeStatus.CLAIMED.value
            completion.claimed_at = _now()
            self._log_event(SeasonEventKind.CHALLENGE_CLAIMED.value,
                            {"challenge_id": challenge_id},
                            season_id=ch.season_id, player_id=player_id,
                            challenge_id=challenge_id)
            return True, "claimed", completion

    def reset_challenge_progress(self, challenge_id: str, player_id: str
                                 ) -> Tuple[bool, str, Optional[ChallengeCompletion]]:
        with _LOCK:
            completion: Optional[ChallengeCompletion] = None
            for c in self._completions.values():
                if c.challenge_id == challenge_id and c.player_id == player_id:
                    completion = c
                    break
            if completion is None:
                return False, "completion_not_found", None
            completion.current_value = 0
            completion.status = ChallengeStatus.ACTIVE.value
            completion.completed_at = 0.0
            completion.claimed_at = 0.0
            self._log_event(SeasonEventKind.CHALLENGE_RESET.value,
                            {"challenge_id": challenge_id, "player_id": player_id},
                            challenge_id=challenge_id, player_id=player_id)
            return True, "reset", completion

    def get_challenge_completion(self, challenge_id: str, player_id: str
                                 ) -> Optional[ChallengeCompletion]:
        with _LOCK:
            for c in self._completions.values():
                if c.challenge_id == challenge_id and c.player_id == player_id:
                    return c
            return None

    def list_completions(self, player_id: str = "",
                         season_id: str = "") -> List[ChallengeCompletion]:
        with _LOCK:
            results = list(self._completions.values())
            if player_id:
                results = [c for c in results if c.player_id == player_id]
            if season_id:
                results = [c for c in results if c.season_id == season_id]
            return results

    # ------------------------------------------------------------------
    # System Operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        with _LOCK:
            self._tick_count += 1
            self._log_event(SeasonEventKind.TICK.value,
                            {"tick": self._tick_count})
            return {"tick_count": self._tick_count}

    def set_config(self, config: Dict[str, Any]) -> Tuple[bool, str, SeasonConfig]:
        with _LOCK:
            if "max_seasons" in config:
                self._config.max_seasons = _safe_int(config["max_seasons"], self._config.max_seasons)
            if "max_tiers_per_season" in config:
                self._config.max_tiers_per_season = _safe_int(config["max_tiers_per_season"], self._config.max_tiers_per_season)
            if "xp_multiplier" in config:
                self._config.xp_multiplier = _safe_float(config["xp_multiplier"], self._config.xp_multiplier)
            if "daily_challenge_count" in config:
                self._config.daily_challenge_count = _safe_int(config["daily_challenge_count"], self._config.daily_challenge_count)
            if "weekly_challenge_count" in config:
                self._config.weekly_challenge_count = _safe_int(config["weekly_challenge_count"], self._config.weekly_challenge_count)
            self._log_event(SeasonEventKind.CONFIG_UPDATED.value, dict(config))
            return True, "updated", self._config

    def get_config(self) -> SeasonConfig:
        with _LOCK:
            return self._config

    def list_events(self, limit: int = 100, kind: str = "") -> List[SeasonEvent]:
        with _LOCK:
            results = list(self._events)
            if kind:
                results = [e for e in results if e.kind == kind]
            if limit > 0:
                results = results[-limit:]
            return results

    def get_stats(self) -> SeasonStats:
        with _LOCK:
            self._update_stats()
            self._stats.tick_count = self._tick_count
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with _LOCK:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "active_season_id": self._active_season_id,
                "total_seasons": len(self._seasons),
                "total_tiers": len(self._tiers),
                "total_rewards": len(self._rewards),
                "total_challenges": len(self._challenges),
                "total_player_progress": len(self._progress),
                "total_completions": len(self._completions),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> SeasonSnapshot:
        with _LOCK:
            self._update_stats()
            return SeasonSnapshot(
                seasons=[s.to_dict() for s in self._seasons.values()],
                stats=self._stats.to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with _LOCK:
            self._seasons.clear()
            self._tiers.clear()
            self._rewards.clear()
            self._challenges.clear()
            self._progress.clear()
            self._completions.clear()
            self._events.clear()
            self._active_season_id = ""
            self._tick_count = 0
            self._event_counter = 0
            self._initialized = False
            self._seed()
            self._log_event(SeasonEventKind.RESET.value, {})
            return self.get_status()


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------

def get_season_pass_system() -> SeasonPassSystem:
    return SeasonPassSystem.get_instance()
