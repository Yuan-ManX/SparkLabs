"""
SparkLabs Engine - Achievement Progression System

A comprehensive achievement and progression system for the SparkLabs
AI-native game engine. Provides achievement tracking, player progression,
unlockable content, statistics tracking, and reward management.

Architecture:
    AchievementProgressionSystem (singleton)
    |-- Achievement (single achievement definition)
    |-- AchievementProgress (per-player achievement progress)
    |-- ProgressionTrack (progression track e.g. level, skill)
    |-- PlayerProgression (complete player progression data)
    |-- Reward (reward definition)
    |-- Statistic (tracked statistic)
    |-- AchievementSnapshot (complete system snapshot)

Core Capabilities:
    - register_achievement: Register a new achievement definition
    - update_progress: Update a player's progress on an achievement
    - check_unlocks: Evaluate and unlock newly completed achievements
    - grant_reward: Grant a reward to a player
    - add_experience: Add experience points to a progression track
    - track_statistic: Track a player statistic value
    - get_player_progress: Retrieve complete player progression data
    - get_achievements: Get all achievements for a player
    - get_status: Get achievement system status
    - shutdown: Graceful shutdown of the system
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class AchievementType(Enum):
    """Thematic classification for achievement types."""
    STORY = "story"
    COLLECTIBLE = "collectible"
    SKILL = "skill"
    EXPLORATION = "exploration"
    SOCIAL = "social"
    CHALLENGE = "challenge"
    HIDDEN = "hidden"
    TIME_LIMITED = "time_limited"
    MILESTONE = "milestone"
    COMMUNITY = "community"


class AchievementState(Enum):
    """Lifecycle states for an achievement."""
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    UNLOCKED = "unlocked"
    CLAIMED = "claimed"
    HIDDEN = "hidden"


class ProgressionCategory(Enum):
    """Categories of progression tracks."""
    LEVEL = "level"
    SKILL = "skill"
    REPUTATION = "reputation"
    BATTLE_PASS = "battle_pass"
    SEASON = "season"
    CAREER = "career"


class RewardType(Enum):
    """Types of rewards that can be granted to players."""
    CURRENCY = "currency"
    ITEM = "item"
    COSMETIC = "cosmetic"
    TITLE = "title"
    EXPERIENCE = "experience"
    UNLOCK = "unlock"
    BADGE = "badge"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Achievement:
    """A single achievement definition.

    Attributes:
        achievement_id: Unique identifier for the achievement.
        name: Display name of the achievement.
        description: Detailed description of what must be done.
        achievement_type: Category classification for the achievement.
        target_value: The numeric value required to complete the achievement.
        points: Points awarded upon completion.
        icon_path: Path to the achievement icon asset.
        is_hidden: Whether the achievement is hidden from players until unlocked.
        is_secret: Whether the achievement is a secret (implies hidden).
        prerequisite_ids: IDs of achievements that must be unlocked first.
        rewards: List of rewards granted upon completion.
        created_at: Timestamp when the achievement was created.
    """
    achievement_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    name: str = "Unknown Achievement"
    description: str = ""
    achievement_type: AchievementType = AchievementType.MILESTONE
    target_value: float = 1.0
    points: int = 0
    icon_path: str = ""
    is_hidden: bool = False
    is_secret: bool = False
    prerequisite_ids: List[str] = field(default_factory=list)
    rewards: List[Reward] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def __post_init__(self):
        if self.is_secret:
            self.is_hidden = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "achievement_id": self.achievement_id,
            "name": self.name,
            "description": self.description,
            "achievement_type": self.achievement_type.value,
            "target_value": self.target_value,
            "points": self.points,
            "icon_path": self.icon_path,
            "is_hidden": self.is_hidden,
            "is_secret": self.is_secret,
            "prerequisite_ids": self.prerequisite_ids,
            "rewards": [r.to_dict() for r in self.rewards],
            "created_at": self.created_at,
        }


@dataclass
class AchievementProgress:
    """Tracks a single player's progress toward a specific achievement.

    Attributes:
        progress_id: Unique identifier for this progress record.
        player_id: The player this progress belongs to.
        achievement_id: The achievement being tracked.
        state: Current lifecycle state of the achievement.
        current_value: Current progress value toward the target.
        target_value: The value required to complete the achievement.
        unlocked_at: Timestamp when the achievement was unlocked.
        claimed_at: Timestamp when the reward was claimed.
        times_completed: Number of times the achievement has been completed.
    """
    progress_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    player_id: str = ""
    achievement_id: str = ""
    state: AchievementState = AchievementState.LOCKED
    current_value: float = 0.0
    target_value: float = 1.0
    unlocked_at: Optional[float] = None
    claimed_at: Optional[float] = None
    times_completed: int = 0

    def progress_percent(self) -> float:
        """Calculate progress as a percentage of the target value."""
        if self.target_value <= 0:
            return 100.0
        return min(100.0, (self.current_value / self.target_value) * 100.0)

    def is_complete(self) -> bool:
        """Check whether the achievement target has been reached."""
        return self.current_value >= self.target_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "progress_id": self.progress_id,
            "player_id": self.player_id,
            "achievement_id": self.achievement_id,
            "state": self.state.value,
            "current_value": self.current_value,
            "target_value": self.target_value,
            "progress_percent": self.progress_percent(),
            "unlocked_at": self.unlocked_at,
            "claimed_at": self.claimed_at,
            "times_completed": self.times_completed,
        }


@dataclass
class ProgressionTrack:
    """A progression track that defines leveling or ranking within a category.

    Attributes:
        track_id: Unique identifier for the track.
        category: The progression category this track belongs to.
        name: Display name of the progression track.
        current_level: Current level on this track.
        current_experience: Experience points accumulated at the current level.
        experience_to_next: Experience required to reach the next level.
        total_experience: Total experience accumulated across all levels.
        max_level: Maximum attainable level on this track.
        level_multiplier: Scaling factor for experience requirements per level.
    """
    track_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    category: ProgressionCategory = ProgressionCategory.LEVEL
    name: str = "Default Track"
    current_level: int = 1
    current_experience: float = 0.0
    experience_to_next: float = 100.0
    total_experience: float = 0.0
    max_level: int = 100
    level_multiplier: float = 1.5

    def add_experience(self, amount: float) -> bool:
        """Add experience to the track. Returns True if a level-up occurred."""
        if self.current_level >= self.max_level:
            self.current_experience = self.experience_to_next
            return False

        self.total_experience += amount
        self.current_experience += amount
        leveled_up = False

        while self.current_experience >= self.experience_to_next and self.current_level < self.max_level:
            self.current_experience -= self.experience_to_next
            self.current_level += 1
            self.experience_to_next = self._calculate_next_threshold()
            leveled_up = True

        return leveled_up

    def _calculate_next_threshold(self) -> float:
        """Calculate the experience required for the next level."""
        return self.experience_to_next * self.level_multiplier

    def progress_percent(self) -> float:
        """Calculate progress toward the next level as a percentage."""
        if self.experience_to_next <= 0:
            return 100.0
        return min(100.0, (self.current_experience / self.experience_to_next) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "track_id": self.track_id,
            "category": self.category.value,
            "name": self.name,
            "current_level": self.current_level,
            "current_experience": self.current_experience,
            "experience_to_next": self.experience_to_next,
            "total_experience": self.total_experience,
            "max_level": self.max_level,
            "level_multiplier": self.level_multiplier,
            "progress_percent": self.progress_percent(),
        }


@dataclass
class PlayerProgression:
    """Complete progression data for a single player.

    Attributes:
        player_id: The player this progression data belongs to.
        tracks: Progression tracks keyed by category.
        achievement_progress: Achievement progress records keyed by achievement_id.
        statistics: Tracked statistics keyed by stat_name.
        total_achievement_points: Sum of all achievement points earned.
        achievements_unlocked: Total count of unlocked achievements.
        rewards_claimed: Total count of claimed rewards.
        last_updated: Timestamp of the last update to this progression.
    """
    player_id: str = ""
    tracks: Dict[str, ProgressionTrack] = field(default_factory=dict)
    achievement_progress: Dict[str, AchievementProgress] = field(default_factory=dict)
    statistics: Dict[str, float] = field(default_factory=dict)
    total_achievement_points: int = 0
    achievements_unlocked: int = 0
    rewards_claimed: int = 0
    last_updated: float = field(default_factory=time.time)

    def get_track(self, category: ProgressionCategory) -> Optional[ProgressionTrack]:
        """Get a progression track by category."""
        return self.tracks.get(category.value)

    def get_statistic(self, stat_name: str) -> float:
        """Get a tracked statistic value."""
        return self.statistics.get(stat_name, 0.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "tracks": {k: v.to_dict() for k, v in self.tracks.items()},
            "achievement_progress": {k: v.to_dict() for k, v in self.achievement_progress.items()},
            "statistics": dict(self.statistics),
            "total_achievement_points": self.total_achievement_points,
            "achievements_unlocked": self.achievements_unlocked,
            "rewards_claimed": self.rewards_claimed,
            "last_updated": self.last_updated,
        }


@dataclass
class Reward:
    """A reward that can be granted to players.

    Attributes:
        reward_id: Unique identifier for the reward.
        reward_type: The type of reward.
        name: Display name of the reward.
        description: Description of what the reward provides.
        value: Numeric value (e.g., amount of currency, experience points).
        item_id: Item identifier for ITEM-type rewards.
        data: Arbitrary additional data for the reward.
    """
    reward_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    reward_type: RewardType = RewardType.CURRENCY
    name: str = ""
    description: str = ""
    value: float = 0.0
    item_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reward_id": self.reward_id,
            "reward_type": self.reward_type.value,
            "name": self.name,
            "description": self.description,
            "value": self.value,
            "item_id": self.item_id,
            "data": self.data,
        }


@dataclass
class Statistic:
    """A tracked player statistic.

    Attributes:
        stat_name: Unique name identifying the statistic.
        display_name: Human-readable display name.
        category: The achievement type this statistic is associated with.
        default_value: Default starting value.
        is_cumulative: Whether the statistic accumulates over time.
        is_visible: Whether the statistic is visible to players.
    """
    stat_name: str = ""
    display_name: str = ""
    category: AchievementType = AchievementType.MILESTONE
    default_value: float = 0.0
    is_cumulative: bool = True
    is_visible: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stat_name": self.stat_name,
            "display_name": self.display_name,
            "category": self.category.value,
            "default_value": self.default_value,
            "is_cumulative": self.is_cumulative,
            "is_visible": self.is_visible,
        }


@dataclass
class AchievementSnapshot:
    """A complete snapshot of the achievement system state.

    Attributes:
        snapshot_id: Unique identifier for this snapshot.
        timestamp: When the snapshot was taken.
        total_achievements: Total number of registered achievements.
        total_players: Total number of players with progression data.
        total_unlocks: Total number of achievements unlocked across all players.
        total_rewards_granted: Total number of rewards granted.
        achievements_by_type: Count of achievements by type.
        statistics_registered: Total number of registered statistics.
        system_uptime: How long the system has been running in seconds.
    """
    snapshot_id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    timestamp: float = field(default_factory=time.time)
    total_achievements: int = 0
    total_players: int = 0
    total_unlocks: int = 0
    total_rewards_granted: int = 0
    achievements_by_type: Dict[str, int] = field(default_factory=dict)
    statistics_registered: int = 0
    system_uptime: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "timestamp": self.timestamp,
            "total_achievements": self.total_achievements,
            "total_players": self.total_players,
            "total_unlocks": self.total_unlocks,
            "total_rewards_granted": self.total_rewards_granted,
            "achievements_by_type": self.achievements_by_type,
            "statistics_registered": self.statistics_registered,
            "system_uptime": self.system_uptime,
        }


# ---------------------------------------------------------------------------
# Achievement Progression System (Singleton)
# ---------------------------------------------------------------------------


class AchievementProgressionSystem:
    """Comprehensive achievement and progression orchestration engine.

    Manages achievement definitions, player progress, progression tracks,
    rewards, and statistics. Implements the singleton pattern with
    double-checked locking for thread-safe access.
    """

    _instance: Optional["AchievementProgressionSystem"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "AchievementProgressionSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AchievementProgressionSystem":
        """Get the singleton instance of the achievement progression system."""
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._achievements: Dict[str, Achievement] = {}
        self._player_progressions: Dict[str, PlayerProgression] = {}
        self._statistics: Dict[str, Statistic] = {}
        self._rewards_granted: int = 0
        self._total_unlocks: int = 0
        self._unlock_listeners: List[Callable[[str, Achievement], None]] = []
        self._reward_listeners: List[Callable[[str, Reward], None]] = []
        self._level_up_listeners: List[Callable[[str, ProgressionTrack, int], None]] = []
        self._start_time: float = time.time()
        self._running: bool = False

    # ------------------------------------------------------------------
    # Initialization / Shutdown
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Initialize the achievement progression system.

        Sets up internal data structures, registers default statistics,
        and marks the system as running. Safe to call multiple times.
        """
        with self._lock:
            if self._running:
                return
            self._running = True
            self._start_time = time.time()

            # Register default progression tracks for all categories
            default_tracks: Dict[ProgressionCategory, Tuple[str, int, float]] = {
                ProgressionCategory.LEVEL: ("Player Level", 100, 1.5),
                ProgressionCategory.SKILL: ("Skill Mastery", 50, 1.3),
                ProgressionCategory.REPUTATION: ("Reputation", 30, 1.4),
                ProgressionCategory.BATTLE_PASS: ("Battle Pass", 100, 1.2),
                ProgressionCategory.SEASON: ("Season Rank", 50, 1.6),
                ProgressionCategory.CAREER: ("Career Milestones", 20, 2.0),
            }

            for category, (name, max_level, multiplier) in default_tracks.items():
                self._ensure_default_track(category, name, max_level, multiplier)

    def _ensure_default_track(
        self,
        category: ProgressionCategory,
        name: str,
        max_level: int,
        multiplier: float,
    ) -> None:
        """Ensure a default progression track template exists."""
        track = ProgressionTrack(
            track_id=f"default_{category.value}",
            category=category,
            name=name,
            max_level=max_level,
            level_multiplier=multiplier,
        )
        # Store as a template for new players
        if not hasattr(self, '_default_tracks'):
            self._default_tracks: Dict[str, ProgressionTrack] = {}
        self._default_tracks[category.value] = track

    def shutdown(self) -> None:
        """Perform a graceful shutdown of the achievement progression system.

        Clears all listeners, marks the system as not running, and preserves
        progression data for potential serialization or later restoration.
        """
        with self._lock:
            self._running = False
            self._unlock_listeners.clear()
            self._reward_listeners.clear()
            self._level_up_listeners.clear()

    # ------------------------------------------------------------------
    # Achievement Management
    # ------------------------------------------------------------------

    def register_achievement(self, achievement: Achievement) -> None:
        """Register a new achievement definition in the system.

        Args:
            achievement: The Achievement object to register.
        """
        with self._lock:
            self._achievements[achievement.achievement_id] = achievement

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """Retrieve an achievement definition by its ID.

        Args:
            achievement_id: The unique identifier of the achievement.

        Returns:
            The Achievement if found, None otherwise.
        """
        return self._achievements.get(achievement_id)

    def get_achievements(self, player_id: str) -> List[Dict[str, Any]]:
        """Get all achievements with their progress for a specific player.

        Args:
            player_id: The player to retrieve achievements for.

        Returns:
            A list of dictionaries containing achievement definitions
            merged with the player's progress data.
        """
        progression = self._get_or_create_progression(player_id)
        result: List[Dict[str, Any]] = []

        with self._lock:
            for achievement_id, achievement in self._achievements.items():
                progress = progression.achievement_progress.get(achievement_id)
                entry = achievement.to_dict()

                if achievement.is_hidden and (progress is None or progress.state == AchievementState.LOCKED):
                    entry["name"] = "???"
                    entry["description"] = "Hidden achievement"
                    entry["state"] = AchievementState.HIDDEN.value
                    entry["current_value"] = 0.0
                    entry["progress_percent"] = 0.0
                elif progress is not None:
                    entry["state"] = progress.state.value
                    entry["current_value"] = progress.current_value
                    entry["progress_percent"] = progress.progress_percent()
                    entry["unlocked_at"] = progress.unlocked_at
                    entry["claimed_at"] = progress.claimed_at
                else:
                    entry["state"] = AchievementState.LOCKED.value
                    entry["current_value"] = 0.0
                    entry["progress_percent"] = 0.0

                result.append(entry)

        return result

    def get_achievements_by_type(
        self,
        achievement_type: AchievementType,
    ) -> List[Achievement]:
        """Get all registered achievements of a specific type.

        Args:
            achievement_type: The achievement type to filter by.

        Returns:
            A list of matching Achievement definitions.
        """
        with self._lock:
            return [
                a for a in self._achievements.values()
                if a.achievement_type == achievement_type
            ]

    # ------------------------------------------------------------------
    # Progress Tracking
    # ------------------------------------------------------------------

    def update_progress(
        self,
        achievement_id: str,
        player_id: str,
        progress: float,
    ) -> Optional[AchievementProgress]:
        """Update a player's progress toward a specific achievement.

        Increments the progress value and evaluates whether the achievement
        should transition to unlocked status. If the achievement is already
        claimed, the progress update is ignored.

        Args:
            achievement_id: The achievement to update progress for.
            player_id: The player making progress.
            progress: The amount of progress to add (not set).

        Returns:
            The updated AchievementProgress record, or None if the
            achievement does not exist.
        """
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return None

        progression = self._get_or_create_progression(player_id)

        with self._lock:
            prog = self._ensure_progress_record(progression, achievement)

            if prog.state == AchievementState.CLAIMED:
                return prog

            prog.current_value += progress

            if prog.is_complete():
                prog.current_value = prog.target_value
                if prog.state != AchievementState.UNLOCKED:
                    prog.state = AchievementState.UNLOCKED
                    prog.unlocked_at = time.time()
                    prog.times_completed += 1
                    progression.achievements_unlocked += 1
                    progression.total_achievement_points += achievement.points
                    self._total_unlocks += 1
                    self._notify_unlock(player_id, achievement)
            elif prog.current_value > 0 and prog.state == AchievementState.LOCKED:
                prog.state = AchievementState.IN_PROGRESS

            progression.last_updated = time.time()

        return prog

    def _ensure_progress_record(
        self,
        progression: PlayerProgression,
        achievement: Achievement,
    ) -> AchievementProgress:
        """Get or create an AchievementProgress record for a player-achievement pair."""
        if achievement.achievement_id not in progression.achievement_progress:
            progression.achievement_progress[achievement.achievement_id] = AchievementProgress(
                player_id=progression.player_id,
                achievement_id=achievement.achievement_id,
                target_value=achievement.target_value,
            )
        return progression.achievement_progress[achievement.achievement_id]

    # ------------------------------------------------------------------
    # Unlock Checking
    # ------------------------------------------------------------------

    def check_unlocks(self, player_id: str) -> List[AchievementProgress]:
        """Check which achievements should unlock for a player.

        Evaluates all in-progress and locked achievements against the
        player's current statistics. For achievements with prerequisites,
        ensures all prerequisites are met before evaluating.

        Args:
            player_id: The player to check unlocks for.

        Returns:
            A list of AchievementProgress records that were newly unlocked.
        """
        progression = self._get_or_create_progression(player_id)
        newly_unlocked: List[AchievementProgress] = []

        with self._lock:
            for achievement_id, achievement in self._achievements.items():
                progress_record = progression.achievement_progress.get(achievement_id)

                # Skip if already unlocked or claimed
                if progress_record is not None and progress_record.state in (
                    AchievementState.UNLOCKED,
                    AchievementState.CLAIMED,
                ):
                    continue

                # Check prerequisites
                if achievement.prerequisite_ids:
                    if not self._prerequisites_met(progression, achievement.prerequisite_ids):
                        continue

                # Ensure progress record exists
                if progress_record is None:
                    progress_record = self._ensure_progress_record(progression, achievement)

                if progress_record.is_complete() and progress_record.state != AchievementState.UNLOCKED:
                    progress_record.state = AchievementState.UNLOCKED
                    progress_record.unlocked_at = time.time()
                    progress_record.times_completed += 1
                    progression.achievements_unlocked += 1
                    progression.total_achievement_points += achievement.points
                    self._total_unlocks += 1
                    newly_unlocked.append(progress_record)
                    self._notify_unlock(player_id, achievement)

            progression.last_updated = time.time()

        return newly_unlocked

    def _prerequisites_met(
        self,
        progression: PlayerProgression,
        prerequisite_ids: List[str],
    ) -> bool:
        """Check whether all prerequisite achievements are unlocked or claimed."""
        for pid in prerequisite_ids:
            prog = progression.achievement_progress.get(pid)
            if prog is None:
                return False
            if prog.state not in (AchievementState.UNLOCKED, AchievementState.CLAIMED):
                return False
        return True

    # ------------------------------------------------------------------
    # Reward Management
    # ------------------------------------------------------------------

    def grant_reward(self, player_id: str, reward: Reward) -> Dict[str, Any]:
        """Grant a reward to a player.

        Processes the reward based on its type, updating the player's
        progression data accordingly. Currency adds to tracked statistics,
        experience is routed to the appropriate progression track, and
        item/cosmetic/badge rewards are recorded for later retrieval.

        Args:
            player_id: The player receiving the reward.
            reward: The Reward to grant.

        Returns:
            A dictionary with success status and details of the granted reward.
        """
        progression = self._get_or_create_progression(player_id)

        with self._lock:
            self._rewards_granted += 1

            if reward.reward_type == RewardType.CURRENCY:
                stat_name = f"currency_{reward.item_id or 'gold'}"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + reward.value

            elif reward.reward_type == RewardType.EXPERIENCE:
                # Experience is routed to the LEVEL track by default
                self._add_experience_internal(progression, ProgressionCategory.LEVEL, reward.value)

            elif reward.reward_type == RewardType.ITEM:
                stat_name = f"items_received"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + 1

            elif reward.reward_type == RewardType.COSMETIC:
                stat_name = f"cosmetics_unlocked"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + 1

            elif reward.reward_type == RewardType.TITLE:
                stat_name = f"titles_earned"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + 1

            elif reward.reward_type == RewardType.UNLOCK:
                stat_name = f"unlocks_acquired"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + 1

            elif reward.reward_type == RewardType.BADGE:
                stat_name = f"badges_earned"
                progression.statistics[stat_name] = progression.statistics.get(stat_name, 0.0) + 1

            progression.rewards_claimed += 1
            progression.last_updated = time.time()

            self._notify_reward(player_id, reward)

        return {
            "success": True,
            "player_id": player_id,
            "reward": reward.to_dict(),
            "rewards_claimed": progression.rewards_claimed,
        }

    def claim_achievement_reward(
        self,
        player_id: str,
        achievement_id: str,
    ) -> List[Dict[str, Any]]:
        """Claim all rewards for an unlocked achievement.

        Transitions the achievement from UNLOCKED to CLAIMED status and
        grants all associated rewards to the player.

        Args:
            player_id: The player claiming the reward.
            achievement_id: The achievement whose rewards to claim.

        Returns:
            A list of dictionaries with the results of each granted reward.
        """
        achievement = self._achievements.get(achievement_id)
        if achievement is None:
            return [{"success": False, "error": "Achievement not found"}]

        progression = self._get_or_create_progression(player_id)
        progress_record = progression.achievement_progress.get(achievement_id)

        if progress_record is None:
            return [{"success": False, "error": "No progress record found"}]

        if progress_record.state != AchievementState.UNLOCKED:
            return [{"success": False, "error": f"Achievement is {progress_record.state.value}"}]

        results: List[Dict[str, Any]] = []
        with self._lock:
            for reward in achievement.rewards:
                result = self.grant_reward(player_id, reward)
                results.append(result)

            progress_record.state = AchievementState.CLAIMED
            progress_record.claimed_at = time.time()
            progression.last_updated = time.time()

        return results

    # ------------------------------------------------------------------
    # Progression / Experience
    # ------------------------------------------------------------------

    def add_experience(
        self,
        player_id: str,
        amount: float,
        category: ProgressionCategory = ProgressionCategory.LEVEL,
    ) -> Dict[str, Any]:
        """Add experience points to a player's progression track.

        Routes experience to the specified progression category. If a
        level-up occurs, listeners are notified with the new level.

        Args:
            player_id: The player receiving experience.
            amount: The amount of experience to add.
            category: The progression category to apply experience to.

        Returns:
            A dictionary with the track state after adding experience.
        """
        progression = self._get_or_create_progression(player_id)
        return self._add_experience_internal(progression, category, amount)

    def _add_experience_internal(
        self,
        progression: PlayerProgression,
        category: ProgressionCategory,
        amount: float,
    ) -> Dict[str, Any]:
        """Internal method to add experience with lock held."""
        track = progression.tracks.get(category.value)
        if track is None:
            # Create a default track for this category
            default_track = self._default_tracks.get(category.value) if hasattr(self, '_default_tracks') else None
            if default_track is not None:
                track = ProgressionTrack(
                    track_id=f"{progression.player_id}_{category.value}",
                    category=category,
                    name=default_track.name,
                    max_level=default_track.max_level,
                    level_multiplier=default_track.level_multiplier,
                )
            else:
                track = ProgressionTrack(
                    track_id=f"{progression.player_id}_{category.value}",
                    category=category,
                    name=category.value.title(),
                )
            progression.tracks[category.value] = track

        old_level = track.current_level
        leveled_up = track.add_experience(amount)
        progression.last_updated = time.time()

        if leveled_up:
            self._notify_level_up(progression.player_id, track, old_level)

        return {
            "player_id": progression.player_id,
            "category": category.value,
            "experience_added": amount,
            "current_level": track.current_level,
            "current_experience": track.current_experience,
            "experience_to_next": track.experience_to_next,
            "progress_percent": track.progress_percent(),
            "leveled_up": leveled_up,
            "levels_gained": track.current_level - old_level if leveled_up else 0,
        }

    # ------------------------------------------------------------------
    # Statistics Tracking
    # ------------------------------------------------------------------

    def track_statistic(self, stat_name: str, player_id: str, value: float) -> float:
        """Track a player statistic by name.

        Registers the statistic if not already defined, and updates the
        player's value. Supports cumulative (accumulating) and
        non-cumulative (set) tracking based on the statistic definition.

        Args:
            stat_name: The name of the statistic to track.
            player_id: The player whose statistic is being tracked.
            value: The value to track (added for cumulative, set for non-cumulative).

        Returns:
            The updated statistic value.
        """
        progression = self._get_or_create_progression(player_id)

        with self._lock:
            if stat_name not in self._statistics:
                self._statistics[stat_name] = Statistic(stat_name=stat_name, display_name=stat_name)

            stat_def = self._statistics[stat_name]

            if stat_def.is_cumulative:
                current = progression.statistics.get(stat_name, stat_def.default_value)
                progression.statistics[stat_name] = current + value
            else:
                progression.statistics[stat_name] = value

            progression.last_updated = time.time()

        return progression.statistics[stat_name]

    def get_statistic(self, stat_name: str, player_id: str) -> float:
        """Get the current value of a tracked statistic for a player.

        Args:
            stat_name: The name of the statistic.
            player_id: The player to query.

        Returns:
            The current statistic value, or 0.0 if not tracked.
        """
        progression = self._player_progressions.get(player_id)
        if progression is None:
            return 0.0
        return progression.statistics.get(stat_name, 0.0)

    def register_statistic(self, statistic: Statistic) -> None:
        """Register a new statistic definition in the system.

        Args:
            statistic: The Statistic definition to register.
        """
        with self._lock:
            self._statistics[statistic.stat_name] = statistic

    # ------------------------------------------------------------------
    # Player Queries
    # ------------------------------------------------------------------

    def get_player_progress(self, player_id: str) -> PlayerProgression:
        """Get complete player progression data.

        Creates and returns a new progression record if the player does
        not already have one.

        Args:
            player_id: The player to retrieve progression for.

        Returns:
            The PlayerProgression object for the player.
        """
        return self._get_or_create_progression(player_id)

    def _get_or_create_progression(self, player_id: str) -> PlayerProgression:
        """Get or create a PlayerProgression record for a player."""
        if player_id not in self._player_progressions:
            with self._lock:
                if player_id not in self._player_progressions:
                    progression = PlayerProgression(player_id=player_id)
                    # Initialize default tracks
                    if hasattr(self, '_default_tracks'):
                        for cat_value, template in self._default_tracks.items():
                            track = ProgressionTrack(
                                track_id=f"{player_id}_{cat_value}",
                                category=template.category,
                                name=template.name,
                                max_level=template.max_level,
                                level_multiplier=template.level_multiplier,
                            )
                            progression.tracks[cat_value] = track
                    self._player_progressions[player_id] = progression
        return self._player_progressions[player_id]

    def get_completion_summary(self, player_id: str) -> Dict[str, Any]:
        """Get a summary of achievement completion for a player.

        Args:
            player_id: The player to summarize.

        Returns:
            A dictionary with completion statistics.
        """
        progression = self._get_or_create_progression(player_id)

        with self._lock:
            total = len(self._achievements)
            unlocked = sum(
                1 for p in progression.achievement_progress.values()
                if p.state == AchievementState.UNLOCKED
            )
            claimed = sum(
                1 for p in progression.achievement_progress.values()
                if p.state == AchievementState.CLAIMED
            )
            in_progress = sum(
                1 for p in progression.achievement_progress.values()
                if p.state == AchievementState.IN_PROGRESS
            )
            locked = sum(
                1 for p in progression.achievement_progress.values()
                if p.state == AchievementState.LOCKED
            )

            by_type: Dict[str, Dict[str, int]] = {}
            for achievement_id, achievement in self._achievements.items():
                type_key = achievement.achievement_type.value
                if type_key not in by_type:
                    by_type[type_key] = {"total": 0, "unlocked": 0, "claimed": 0}
                by_type[type_key]["total"] += 1
                prog = progression.achievement_progress.get(achievement_id)
                if prog is not None:
                    if prog.state == AchievementState.UNLOCKED:
                        by_type[type_key]["unlocked"] += 1
                    elif prog.state == AchievementState.CLAIMED:
                        by_type[type_key]["claimed"] += 1

        completed = unlocked + claimed
        return {
            "player_id": player_id,
            "total_achievements": total,
            "locked": locked,
            "in_progress": in_progress,
            "unlocked": unlocked,
            "claimed": claimed,
            "completed": completed,
            "completion_percent": round((completed / total * 100) if total > 0 else 0.0, 2),
            "total_points": progression.total_achievement_points,
            "rewards_claimed": progression.rewards_claimed,
            "by_type": by_type,
        }

    # ------------------------------------------------------------------
    # Status & Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the achievement progression system.

        Returns:
            A dictionary with system-wide statistics including counts
            of achievements, players, unlocks, rewards, and uptime.
        """
        with self._lock:
            by_type: Dict[str, int] = {}
            for achievement in self._achievements.values():
                type_key = achievement.achievement_type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1

            return {
                "running": self._running,
                "total_achievements": len(self._achievements),
                "total_players": len(self._player_progressions),
                "total_unlocks": self._total_unlocks,
                "total_rewards_granted": self._rewards_granted,
                "statistics_registered": len(self._statistics),
                "achievements_by_type": by_type,
                "unlock_listeners": len(self._unlock_listeners),
                "reward_listeners": len(self._reward_listeners),
                "level_up_listeners": len(self._level_up_listeners),
                "uptime_seconds": time.time() - self._start_time,
            }

    def create_snapshot(self) -> AchievementSnapshot:
        """Create a snapshot of the current system state.

        Returns:
            An AchievementSnapshot capturing the system state at this moment.
        """
        with self._lock:
            by_type: Dict[str, int] = {}
            for achievement in self._achievements.values():
                type_key = achievement.achievement_type.value
                by_type[type_key] = by_type.get(type_key, 0) + 1

            return AchievementSnapshot(
                total_achievements=len(self._achievements),
                total_players=len(self._player_progressions),
                total_unlocks=self._total_unlocks,
                total_rewards_granted=self._rewards_granted,
                achievements_by_type=by_type,
                statistics_registered=len(self._statistics),
                system_uptime=time.time() - self._start_time,
            )

    # ------------------------------------------------------------------
    # Listener Management
    # ------------------------------------------------------------------

    def on_unlock(self, callback: Callable[[str, Achievement], None]) -> None:
        """Register a listener for achievement unlock events.

        Args:
            callback: A callable receiving (player_id, achievement).
        """
        self._unlock_listeners.append(callback)

    def on_reward(self, callback: Callable[[str, Reward], None]) -> None:
        """Register a listener for reward grant events.

        Args:
            callback: A callable receiving (player_id, reward).
        """
        self._reward_listeners.append(callback)

    def on_level_up(self, callback: Callable[[str, ProgressionTrack, int], None]) -> None:
        """Register a listener for level-up events.

        Args:
            callback: A callable receiving (player_id, track, old_level).
        """
        self._level_up_listeners.append(callback)

    def _notify_unlock(self, player_id: str, achievement: Achievement) -> None:
        """Notify all unlock listeners of a new achievement unlock."""
        for listener in self._unlock_listeners:
            try:
                listener(player_id, achievement)
            except Exception:
                pass

    def _notify_reward(self, player_id: str, reward: Reward) -> None:
        """Notify all reward listeners of a granted reward."""
        for listener in self._reward_listeners:
            try:
                listener(player_id, reward)
            except Exception:
                pass

    def _notify_level_up(self, player_id: str, track: ProgressionTrack, old_level: int) -> None:
        """Notify all level-up listeners of a level-up event."""
        for listener in self._level_up_listeners:
            try:
                listener(player_id, track, old_level)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Reset
    # ------------------------------------------------------------------

    def reset_player(self, player_id: str) -> None:
        """Reset all progression data for a specific player.

        Args:
            player_id: The player to reset.
        """
        with self._lock:
            if player_id in self._player_progressions:
                del self._player_progressions[player_id]

    def reset_all(self) -> None:
        """Reset all player progression data and achievement state.

        Clears all player progressions, unlock counters, and reward
        counters. Achievement definitions are preserved.
        """
        with self._lock:
            self._player_progressions.clear()
            self._total_unlocks = 0
            self._rewards_granted = 0


# ---------------------------------------------------------------------------
# Module-level Accessor
# ---------------------------------------------------------------------------


def get_achievement_progression_system() -> AchievementProgressionSystem:
    """Get the AchievementProgressionSystem singleton instance."""
    return AchievementProgressionSystem.get_instance()