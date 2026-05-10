"""
SparkLabs Engine - Difficulty System

Dynamic difficulty adjustment engine for AI-native games.
Provides tier-based difficulty profiles, adaptive difficulty
based on player performance, and progressive challenge scaling.

Architecture:
  DifficultySystem
    |-- DifficultyProfile (preset difficulty configuration tiers)
    |-- AdaptiveController (real-time performance-based adjustment)
    |-- ProgressiveScaling (level-based challenge curves)
    |-- DifficultyEventBus (difficulty-change notifications)
    |-- PlayerMetricsTracker (skill estimation from gameplay data)

Difficulty Tiers:
  - BEGINNER: generous timing, reduced enemy count, extra lives
  - EASY: forgiving collisions, basic AI patterns
  - NORMAL: balanced defaults
  - HARD: tighter timing, advanced AI, fewer resources
  - EXPERT: minimal margin, perfect precision required
  - ADAPTIVE: adjusts automatically based on player performance
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class DifficultyTier(Enum):
    BEGINNER = "beginner"
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"
    ADAPTIVE = "adaptive"


class MetricType(Enum):
    DEATH_COUNT = "death_count"
    LEVEL_TIME = "level_time"
    ACCURACY = "accuracy"
    COLLECTIBLES_FOUND = "collectibles_found"
    DAMAGE_TAKEN = "damage_taken"
    RETRY_COUNT = "retry_count"


@dataclass
class DifficultyParams:
    enemy_health_mult: float = 1.0
    enemy_damage_mult: float = 1.0
    enemy_count_mult: float = 1.0
    enemy_speed_mult: float = 1.0
    player_health_mult: float = 1.0
    player_damage_mult: float = 1.0
    resource_spawn_rate: float = 1.0
    time_limit_mult: float = 1.0
    ai_aggression: float = 0.5
    ai_reaction_time: float = 0.5
    puzzle_hint_frequency: float = 0.0
    score_multiplier: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enemy_health_mult": round(self.enemy_health_mult, 2),
            "enemy_damage_mult": round(self.enemy_damage_mult, 2),
            "enemy_count_mult": round(self.enemy_count_mult, 2),
            "enemy_speed_mult": round(self.enemy_speed_mult, 2),
            "player_health_mult": round(self.player_health_mult, 2),
            "player_damage_mult": round(self.player_damage_mult, 2),
            "resource_spawn_rate": round(self.resource_spawn_rate, 2),
            "time_limit_mult": round(self.time_limit_mult, 2),
            "ai_aggression": round(self.ai_aggression, 2),
            "score_multiplier": round(self.score_multiplier, 2),
        }

    def lerp(self, other: "DifficultyParams", t: float) -> "DifficultyParams":
        t = max(0.0, min(1.0, t))
        return DifficultyParams(
            enemy_health_mult=self._lerp_scalar(self.enemy_health_mult, other.enemy_health_mult, t),
            enemy_damage_mult=self._lerp_scalar(self.enemy_damage_mult, other.enemy_damage_mult, t),
            enemy_count_mult=self._lerp_scalar(self.enemy_count_mult, other.enemy_count_mult, t),
            enemy_speed_mult=self._lerp_scalar(self.enemy_speed_mult, other.enemy_speed_mult, t),
            player_health_mult=self._lerp_scalar(self.player_health_mult, other.player_health_mult, t),
            player_damage_mult=self._lerp_scalar(self.player_damage_mult, other.player_damage_mult, t),
            resource_spawn_rate=self._lerp_scalar(self.resource_spawn_rate, other.resource_spawn_rate, t),
            time_limit_mult=self._lerp_scalar(self.time_limit_mult, other.time_limit_mult, t),
            ai_aggression=self._lerp_scalar(self.ai_aggression, other.ai_aggression, t),
            ai_reaction_time=self._lerp_scalar(self.ai_reaction_time, other.ai_reaction_time, t),
            puzzle_hint_frequency=self._lerp_scalar(self.puzzle_hint_frequency, other.puzzle_hint_frequency, t),
            score_multiplier=self._lerp_scalar(self.score_multiplier, other.score_multiplier, t),
        )

    @staticmethod
    def _lerp_scalar(a: float, b: float, t: float) -> float:
        return a + (b - a) * t


DIFFICULTY_PROFILES: Dict[DifficultyTier, DifficultyParams] = {
    DifficultyTier.BEGINNER: DifficultyParams(
        enemy_health_mult=0.5, enemy_damage_mult=0.4, enemy_count_mult=0.5,
        enemy_speed_mult=0.6, player_health_mult=2.0, player_damage_mult=1.5,
        resource_spawn_rate=2.0, time_limit_mult=1.5, ai_aggression=0.2,
        ai_reaction_time=0.8, puzzle_hint_frequency=0.8, score_multiplier=0.5,
    ),
    DifficultyTier.EASY: DifficultyParams(
        enemy_health_mult=0.75, enemy_damage_mult=0.6, enemy_count_mult=0.75,
        enemy_speed_mult=0.8, player_health_mult=1.5, player_damage_mult=1.25,
        resource_spawn_rate=1.5, time_limit_mult=1.25, ai_aggression=0.35,
        ai_reaction_time=0.6, puzzle_hint_frequency=0.4, score_multiplier=0.75,
    ),
    DifficultyTier.NORMAL: DifficultyParams(
        enemy_health_mult=1.0, enemy_damage_mult=1.0, enemy_count_mult=1.0,
        enemy_speed_mult=1.0, player_health_mult=1.0, player_damage_mult=1.0,
        resource_spawn_rate=1.0, time_limit_mult=1.0, ai_aggression=0.5,
        ai_reaction_time=0.4, puzzle_hint_frequency=0.2, score_multiplier=1.0,
    ),
    DifficultyTier.HARD: DifficultyParams(
        enemy_health_mult=1.5, enemy_damage_mult=1.5, enemy_count_mult=1.3,
        enemy_speed_mult=1.3, player_health_mult=0.75, player_damage_mult=0.85,
        resource_spawn_rate=0.7, time_limit_mult=0.8, ai_aggression=0.7,
        ai_reaction_time=0.2, puzzle_hint_frequency=0.0, score_multiplier=1.5,
    ),
    DifficultyTier.EXPERT: DifficultyParams(
        enemy_health_mult=2.5, enemy_damage_mult=2.5, enemy_count_mult=1.6,
        enemy_speed_mult=1.6, player_health_mult=0.5, player_damage_mult=0.7,
        resource_spawn_rate=0.4, time_limit_mult=0.6, ai_aggression=0.9,
        ai_reaction_time=0.1, puzzle_hint_frequency=0.0, score_multiplier=2.5,
    ),
}


@dataclass
class PlayerMetrics:
    deaths: int = 0
    level_time: float = 0.0
    accuracy: float = 0.0
    collectibles_found: int = 0
    collectibles_total: int = 0
    damage_taken: float = 0.0
    retry_count: int = 0
    score: float = 0.0

    def get_performance_ratio(self) -> float:
        ratios: List[float] = []
        if self.collectibles_total > 0:
            ratios.append(self.collectibles_found / self.collectibles_total)
        if self.accuracy > 0:
            ratios.append(self.accuracy)
        if self.damage_taken > 0:
            ratios.append(1.0 - min(self.damage_taken / 300.0, 1.0))
        if ratios:
            return sum(ratios) / len(ratios)
        return 0.5

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deaths": self.deaths,
            "level_time": round(self.level_time, 2),
            "accuracy": round(self.accuracy, 3),
            "collectibles_found": self.collectibles_found,
            "collectibles_total": self.collectibles_total,
            "damage_taken": round(self.damage_taken, 1),
            "retry_count": self.retry_count,
            "score": round(self.score, 1),
        }


class DifficultySystem:
    """
    Dynamic difficulty adjustment for AI-native games.

    Supports static difficulty tiers and adaptive mode that
    adjusts parameters based on player performance metrics.
    Used by AI agents to configure game balance dynamically.

    Usage:
        ds = DifficultySystem()
        ds.set_tier(DifficultyTier.ADAPTIVE)
        params = ds.get_current_params()
        ds.record_death()
        ds.record_level_complete(time_taken=45.2)
    """

    _instance: Optional["DifficultySystem"] = None

    def __init__(self):
        self._tier: DifficultyTier = DifficultyTier.NORMAL
        self._base_params: DifficultyParams = DIFFICULTY_PROFILES[DifficultyTier.NORMAL]
        self._current_params: DifficultyParams = DifficultyParams()
        self._metrics: PlayerMetrics = PlayerMetrics()
        self._current_level: int = 1
        self._target_performance: float = 0.65
        self._adjustment_rate: float = 0.1
        self._smoothing: float = 0.3
        self._params_history: List[Tuple[float, DifficultyParams]] = []
        self._stats: Dict[str, int] = {"tier_changes": 0, "adaptive_updates": 0}

    @classmethod
    def get_instance(cls) -> "DifficultySystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set_tier(self, tier: DifficultyTier) -> None:
        if tier != self._tier:
            self._stats["tier_changes"] += 1

        self._tier = tier
        if tier != DifficultyTier.ADAPTIVE:
            self._base_params = DIFFICULTY_PROFILES.get(tier, self._base_params)
            self._current_params = self._base_params
        else:
            self._current_params = DifficultyParams()

    def get_tier(self) -> DifficultyTier:
        return self._tier

    def get_current_params(self) -> DifficultyParams:
        return self._current_params

    def set_level(self, level: int) -> None:
        self._current_level = max(1, level)

    def get_level(self) -> int:
        return self._current_level

    def record_death(self) -> None:
        self._metrics.deaths += 1
        if self._tier == DifficultyTier.ADAPTIVE:
            self._apply_adaptive_adjustment()

    def record_level_complete(
        self,
        time_taken: float,
        accuracy: float = 0.0,
        collectibles_found: int = 0,
        collectibles_total: int = 0,
        damage_taken: float = 0.0,
        score: float = 0.0,
    ) -> None:
        self._metrics.level_time = time_taken
        self._metrics.accuracy = max(0.0, min(1.0, accuracy))
        self._metrics.collectibles_found = collectibles_found
        self._metrics.collectibles_total = collectibles_total
        self._metrics.damage_taken = damage_taken
        self._metrics.score = score

        if self._tier == DifficultyTier.ADAPTIVE:
            self._apply_adaptive_adjustment()

    def record_retry(self) -> None:
        self._metrics.retry_count += 1
        if self._tier == DifficultyTier.ADAPTIVE:
            self._apply_adaptive_adjustment()

    def record_metric(self, metric_type: MetricType, value: float) -> None:
        if metric_type == MetricType.DEATH_COUNT:
            self._metrics.deaths = int(value)
        elif metric_type == MetricType.LEVEL_TIME:
            self._metrics.level_time = value
        elif metric_type == MetricType.ACCURACY:
            self._metrics.accuracy = max(0.0, min(1.0, value))
        elif metric_type == MetricType.COLLECTIBLES_FOUND:
            self._metrics.collectibles_found = int(value)
        elif metric_type == MetricType.DAMAGE_TAKEN:
            self._metrics.damage_taken = value
        elif metric_type == MetricType.RETRY_COUNT:
            self._metrics.retry_count = int(value)

        if self._tier == DifficultyTier.ADAPTIVE:
            self._apply_adaptive_adjustment()

    def _apply_adaptive_adjustment(self) -> None:
        performance = self._metrics.get_performance_ratio()
        delta = performance - self._target_performance

        adjustment = delta * self._adjustment_rate * -1

        easy_params = DIFFICULTY_PROFILES[DifficultyTier.EASY]
        hard_params = DIFFICULTY_PROFILES[DifficultyTier.HARD]

        t = 0.5 + adjustment
        t = max(-1.0, min(2.0, t))

        target = easy_params.lerp(hard_params, t)

        if self._params_history:
            target = self._current_params.lerp(target, self._smoothing)

        self._current_params = target
        self._params_history.append((time.time(), self._current_params))
        self._stats["adaptive_updates"] += 1

        max_history = 100
        if len(self._params_history) > max_history:
            self._params_history = self._params_history[-max_history:]

    def reset_metrics(self) -> None:
        self._metrics = PlayerMetrics()

    def get_metrics(self) -> PlayerMetrics:
        return self._metrics

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tier": self._tier.value,
            "level": self._current_level,
            "params": self._current_params.to_dict(),
            "metrics": self._metrics.to_dict(),
            "performance_ratio": round(self._metrics.get_performance_ratio(), 3),
            **self._stats,
        }

    def apply_to_enemy(self, base_health: float, base_damage: float, base_speed: float) -> Tuple[float, float, float]:
        p = self._current_params
        return (
            base_health * p.enemy_health_mult,
            base_damage * p.enemy_damage_mult,
            base_speed * p.enemy_speed_mult,
        )

    def apply_to_player(self, base_health: float, base_damage: float) -> Tuple[float, float]:
        p = self._current_params
        return (
            base_health * p.player_health_mult,
            base_damage * p.player_damage_mult,
        )

    def get_score_multiplier(self) -> float:
        return self._current_params.score_multiplier


def get_difficulty_system() -> DifficultySystem:
    return DifficultySystem.get_instance()