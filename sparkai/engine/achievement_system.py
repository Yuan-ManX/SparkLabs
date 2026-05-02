"""
Achievement System - Achievement tracking and unlocking engine.

Architecture:
    AchievementSystem/
    |-- AchievementCategory (achievement classification)
    |-- AchievementState (unlock lifecycle states)
    |-- AchievementCondition (unlock criteria definition)
    |-- Achievement (achievement definition with rewards)
    |-- PlayerStats (cumulative stat tracking)
    |-- AchievementSystem (unified achievement orchestrator)

Tracks player progress, evaluates unlock conditions, grants rewards,
and manages the complete achievement lifecycle across game sessions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class AchievementCategory(Enum):
    MILESTONE = auto()
    COLLECTION = auto()
    SKILL = auto()
    PROGRESS = auto()
    HIDDEN = auto()
    CHALLENGE = auto()
    SOCIAL = auto()
    EXPLORATION = auto()


class AchievementState(Enum):
    LOCKED = auto()
    IN_PROGRESS = auto()
    UNLOCKED = auto()


@dataclass
class AchievementCondition:
    condition_id: str = ""
    stat_name: str = ""
    target_value: float = 1.0
    comparison: str = "gte"
    description: str = ""

    def __post_init__(self):
        if not self.condition_id:
            self.condition_id = uuid.uuid4().hex[:10]

    def evaluate(self, current_value: float) -> bool:
        comparisons = {
            "gte": lambda a, b: a >= b,
            "lte": lambda a, b: a <= b,
            "eq": lambda a, b: a == b,
            "gt": lambda a, b: a > b,
            "lt": lambda a, b: a < b,
        }
        fn = comparisons.get(self.comparison, comparisons["gte"])
        return fn(current_value, self.target_value)

    def get_progress(self, current_value: float) -> float:
        if self.target_value <= 0:
            return 100.0
        return min(100.0, (current_value / self.target_value) * 100.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "condition_id": self.condition_id,
            "stat_name": self.stat_name,
            "target_value": self.target_value,
            "comparison": self.comparison,
            "description": self.description,
        }


@dataclass
class Achievement:
    achievement_id: str = ""
    name: str = "Unknown Achievement"
    description: str = ""
    category: AchievementCategory = AchievementCategory.MILESTONE
    conditions: List[AchievementCondition] = field(default_factory=list)
    rewards: Dict[str, Any] = field(default_factory=dict)
    icon_path: str = ""
    points: int = 0
    hidden: bool = False
    secret: bool = False
    prerequisite_ids: List[str] = field(default_factory=list)
    state: AchievementState = AchievementState.LOCKED
    unlocked_at: Optional[float] = None
    unlock_order: int = 0

    def __post_init__(self):
        if not self.achievement_id:
            self.achievement_id = uuid.uuid4().hex[:12]
        if self.secret:
            self.hidden = True

    def can_unlock(self, stats: Dict[str, float]) -> bool:
        if self.state == AchievementState.UNLOCKED:
            return False
        if not self.conditions:
            return False
        return all(
            c.evaluate(stats.get(c.stat_name, 0.0))
            for c in self.conditions
        )

    def get_progress(self, stats: Dict[str, float]) -> float:
        if not self.conditions:
            return 0.0
        progress_values = [
            c.get_progress(stats.get(c.stat_name, 0.0))
            for c in self.conditions
        ]
        return sum(progress_values) / len(progress_values)

    def unlock(self, order: int, timestamp: Optional[float] = None) -> None:
        import time
        self.state = AchievementState.UNLOCKED
        self.unlocked_at = timestamp or time.time()
        self.unlock_order = order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "achievement_id": self.achievement_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.name.lower(),
            "conditions": [c.to_dict() for c in self.conditions],
            "rewards": self.rewards,
            "points": self.points,
            "hidden": self.hidden,
            "secret": self.secret,
            "state": self.state.name.lower(),
            "unlocked_at": self.unlocked_at,
            "progress": getattr(self, "_cached_progress", 0.0),
        }


@dataclass
class PlayerStats:
    owner_id: str
    stats: Dict[str, float] = field(default_factory=dict)
    unlocked_achievements: List[str] = field(default_factory=list)
    total_points: int = 0

    def get_stat(self, name: str) -> float:
        return self.stats.get(name, 0.0)

    def set_stat(self, name: str, value: float) -> None:
        self.stats[name] = value

    def increment_stat(self, name: str, amount: float = 1.0) -> float:
        current = self.stats.get(name, 0.0)
        new_value = current + amount
        self.stats[name] = new_value
        return new_value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "stat_count": len(self.stats),
            "unlocked_count": len(self.unlocked_achievements),
            "total_points": self.total_points,
        }


class AchievementSystem:
    """Unified achievement tracking and unlocking orchestration."""

    _instance: Optional["AchievementSystem"] = None

    def __init__(self):
        self._achievements: Dict[str, Achievement] = {}
        self._player_stats: Dict[str, PlayerStats] = {}
        self._total_unlocked = 0
        self._unlock_order_counter = 0
        self._unlock_listeners: List[Callable] = []
        self._progress_listeners: List[Callable] = []

    @classmethod
    def get_instance(cls) -> "AchievementSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_achievement(self, achievement: Achievement) -> None:
        self._achievements[achievement.achievement_id] = achievement

    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        return self._achievements.get(achievement_id)

    def get_all_achievements(self) -> List[Achievement]:
        return list(self._achievements.values())

    def get_achievements_by_category(self, category: AchievementCategory) -> List[Achievement]:
        return [a for a in self._achievements.values() if a.category == category]

    def create_player_stats(self, owner_id: str) -> PlayerStats:
        stats = PlayerStats(owner_id=owner_id)
        self._player_stats[owner_id] = stats
        return stats

    def get_player_stats(self, owner_id: str) -> Optional[PlayerStats]:
        return self._player_stats.get(owner_id)

    def get_or_create_player_stats(self, owner_id: str) -> PlayerStats:
        if owner_id not in self._player_stats:
            return self.create_player_stats(owner_id)
        return self._player_stats[owner_id]

    def update_stat(self, owner_id: str, stat_name: str, value: float) -> List[Achievement]:
        """Update a player stat and check for newly unlocked achievements."""
        stats = self.get_or_create_player_stats(owner_id)
        stats.set_stat(stat_name, value)
        return self.check_achievements(owner_id)

    def increment_stat(self, owner_id: str, stat_name: str, amount: float = 1.0) -> List[Achievement]:
        """Increment a stat and check achievements."""
        stats = self.get_or_create_player_stats(owner_id)
        new_value = stats.increment_stat(stat_name, amount)

        self._notify_progress(owner_id, stat_name, new_value)
        return self.check_achievements(owner_id)

    def check_achievements(self, owner_id: str) -> List[Achievement]:
        """Check all locked achievements for potential unlocks."""
        stats = self.get_player_stats(owner_id)
        if not stats:
            return []

        newly_unlocked: List[Achievement] = []

        for achievement in self._achievements.values():
            if achievement.state != AchievementState.UNLOCKED:
                if achievement.prerequisite_ids:
                    prereqs_met = all(
                        self._achievements.get(pid) and
                        self._achievements[pid].state == AchievementState.UNLOCKED
                        for pid in achievement.prerequisite_ids
                    )
                    if not prereqs_met:
                        continue

                progress = achievement.get_progress(stats.stats)
                achievement._cached_progress = progress

                if progress > 0:
                    achievement.state = AchievementState.IN_PROGRESS

                if achievement.can_unlock(stats.stats):
                    self._unlock_order_counter += 1
                    achievement.unlock(self._unlock_order_counter)
                    achievement._cached_progress = 100.0
                    stats.unlocked_achievements.append(achievement.achievement_id)
                    stats.total_points += achievement.points
                    self._total_unlocked += 1
                    newly_unlocked.append(achievement)
                    self._notify_unlock(owner_id, achievement)

        return newly_unlocked

    def is_unlocked(self, achievement_id: str) -> bool:
        achievement = self._achievements.get(achievement_id)
        return achievement is not None and achievement.state == AchievementState.UNLOCKED

    def get_unlocked_achievements(self, owner_id: str) -> List[Achievement]:
        stats = self.get_player_stats(owner_id)
        if not stats:
            return []
        return [
            self._achievements[aid] for aid in stats.unlocked_achievements
            if aid in self._achievements
        ]

    def get_unlock_summary(self, owner_id: str) -> Dict[str, Any]:
        stats = self.get_player_stats(owner_id)
        total = len(self._achievements)
        unlocked = len(stats.unlocked_achievements) if stats else 0
        return {
            "total_achievements": total,
            "unlocked": unlocked,
            "locked": total - unlocked,
            "total_points": stats.total_points if stats else 0,
            "completion_percent": (unlocked / total * 100) if total > 0 else 0.0,
        }

    def get_visible_achievements(self, owner_id: str) -> List[Dict[str, Any]]:
        """Get achievements visible to the player (hide secret locked ones)."""
        stats = self.get_player_stats(owner_id)
        result = []
        for achievement in self._achievements.values():
            if achievement.secret and achievement.state == AchievementState.LOCKED:
                continue
            if stats:
                progress = achievement.get_progress(stats.stats)
                achievement._cached_progress = progress
            result.append(achievement.to_dict())
        return result

    def on_unlock(self, callback: Callable) -> None:
        self._unlock_listeners.append(callback)

    def on_progress(self, callback: Callable) -> None:
        self._progress_listeners.append(callback)

    def _notify_unlock(self, owner_id: str, achievement: Achievement) -> None:
        for listener in self._unlock_listeners:
            try:
                listener(owner_id, achievement)
            except Exception:
                pass

    def _notify_progress(self, owner_id: str, stat_name: str, value: float) -> None:
        for listener in self._progress_listeners:
            try:
                listener(owner_id, stat_name, value)
            except Exception:
                pass

    def grant_rewards(self, owner_id: str, achievement_id: str) -> Dict[str, Any]:
        """Grant rewards for a specific achievement."""
        achievement = self._achievements.get(achievement_id)
        if not achievement or achievement.state != AchievementState.UNLOCKED:
            return {"success": False, "error": "Achievement not unlocked"}

        rewards = dict(achievement.rewards)

        if "gold" in rewards:
            from sparkai.engine.inventory_system import get_inventory_system
            inv_sys = get_inventory_system()
            inv = inv_sys.get_or_create_inventory(owner_id)
            inv.add_gold(rewards["gold"])

        return {"success": True, "rewards": rewards}

    def reset_all(self) -> None:
        for achievement in self._achievements.values():
            achievement.state = AchievementState.LOCKED
            achievement.unlocked_at = None
            achievement.unlock_order = 0
            achievement._cached_progress = 0.0
        self._total_unlocked = 0
        self._unlock_order_counter = 0

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_achievements": len(self._achievements),
            "total_unlocked": self._total_unlocked,
            "player_count": len(self._player_stats),
            "categories": {c.name.lower(): len(self.get_achievements_by_category(c))
                          for c in AchievementCategory},
            "unlock_rate": (self._total_unlocked / len(self._achievements) * 100)
            if self._achievements else 0.0,
        }


def get_achievement_system() -> AchievementSystem:
    return AchievementSystem.get_instance()
