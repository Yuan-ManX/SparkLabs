"""
SparkLabs Engine - Adaptive Content System

A comprehensive adaptive game content engine that dynamically adjusts
game content based on real-time player behavior analysis, archetype
classification, performance metrics, and engagement prediction. Provides
personalized content variant selection with difficulty scaling and
economy balancing for optimal player experience.

Core Capabilities:
  - Player archetype classification from behavioral fingerprints
  - Real-time difficulty adjustment through performance curve analysis
  - Content variant selection optimized for player skill and preference
  - Reward curve modulation based on challenge-to-skill ratio
  - Adaptive encounter generation tailored to individual playstyles
  - Player engagement forecasting with churn risk detection
  - In-game economy balancing through dynamic content scaling

Architecture:
  EngineAdaptiveContent (Singleton)
    |-- ContentProfile (player behavioral archetype and preferences)
    |-- AdaptiveDifficulty (dynamic difficulty state and history)
    |-- ContentVariant (optimized content selection for player)
    |-- PlayerArchetype (behavioral classification enum)
    |-- ContentType (game content category enum)
    |-- DifficultyTier (adaptive difficulty levels)
"""

from __future__ import annotations

import math
import random
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlayerArchetype(Enum):
    EXPLORER = "explorer"
    ACHIEVER = "achiever"
    SOCIALIZER = "socializer"
    KILLER = "killer"
    SPEEDRUNNER = "speedrunner"
    COMPLETIONIST = "completionist"


class ContentType(Enum):
    COMBAT = "combat"
    PUZZLE = "puzzle"
    EXPLORATION = "exploration"
    NARRATIVE = "narrative"
    COLLECTION = "collection"
    STEALTH = "stealth"


class DifficultyTier(Enum):
    CASUAL = "casual"
    NORMAL = "normal"
    CHALLENGING = "challenging"
    HARDCORE = "hardcore"
    NIGHTMARE = "nightmare"


_ARHCETYPE_PREFERENCE_PROFILES: Dict[str, Dict[str, Any]] = {
    "explorer": {
        "content_weights": {
            ContentType.EXPLORATION.value: 0.40,
            ContentType.COLLECTION.value: 0.25,
            ContentType.NARRATIVE.value: 0.15,
            ContentType.PUZZLE.value: 0.10,
            ContentType.COMBAT.value: 0.05,
            ContentType.STEALTH.value: 0.05,
        },
        "preferred_difficulty": DifficultyTier.NORMAL.value,
        "session_duration_minutes": 65.0,
        "session_frequency_per_week": 4.0,
        "completion_drive": 0.55,
        "risk_tolerance": 0.40,
        "novelty_seeking": 0.85,
        "social_orientation": 0.25,
    },
    "achiever": {
        "content_weights": {
            ContentType.COMBAT.value: 0.30,
            ContentType.COLLECTION.value: 0.30,
            ContentType.PUZZLE.value: 0.20,
            ContentType.EXPLORATION.value: 0.10,
            ContentType.NARRATIVE.value: 0.05,
            ContentType.STEALTH.value: 0.05,
        },
        "preferred_difficulty": DifficultyTier.CHALLENGING.value,
        "session_duration_minutes": 90.0,
        "session_frequency_per_week": 5.0,
        "completion_drive": 0.95,
        "risk_tolerance": 0.60,
        "novelty_seeking": 0.40,
        "social_orientation": 0.35,
    },
    "socializer": {
        "content_weights": {
            ContentType.NARRATIVE.value: 0.35,
            ContentType.EXPLORATION.value: 0.25,
            ContentType.COLLECTION.value: 0.15,
            ContentType.COMBAT.value: 0.10,
            ContentType.PUZZLE.value: 0.10,
            ContentType.STEALTH.value: 0.05,
        },
        "preferred_difficulty": DifficultyTier.NORMAL.value,
        "session_duration_minutes": 55.0,
        "session_frequency_per_week": 3.5,
        "completion_drive": 0.45,
        "risk_tolerance": 0.30,
        "novelty_seeking": 0.60,
        "social_orientation": 0.90,
    },
    "killer": {
        "content_weights": {
            ContentType.COMBAT.value: 0.55,
            ContentType.STEALTH.value: 0.20,
            ContentType.PUZZLE.value: 0.10,
            ContentType.EXPLORATION.value: 0.08,
            ContentType.COLLECTION.value: 0.05,
            ContentType.NARRATIVE.value: 0.02,
        },
        "preferred_difficulty": DifficultyTier.HARDCORE.value,
        "session_duration_minutes": 75.0,
        "session_frequency_per_week": 4.5,
        "completion_drive": 0.70,
        "risk_tolerance": 0.85,
        "novelty_seeking": 0.50,
        "social_orientation": 0.20,
    },
    "speedrunner": {
        "content_weights": {
            ContentType.COMBAT.value: 0.25,
            ContentType.PUZZLE.value: 0.25,
            ContentType.STEALTH.value: 0.20,
            ContentType.EXPLORATION.value: 0.15,
            ContentType.COLLECTION.value: 0.10,
            ContentType.NARRATIVE.value: 0.05,
        },
        "preferred_difficulty": DifficultyTier.NIGHTMARE.value,
        "session_duration_minutes": 30.0,
        "session_frequency_per_week": 6.0,
        "completion_drive": 0.85,
        "risk_tolerance": 0.95,
        "novelty_seeking": 0.35,
        "social_orientation": 0.15,
    },
    "completionist": {
        "content_weights": {
            ContentType.COLLECTION.value: 0.30,
            ContentType.EXPLORATION.value: 0.25,
            ContentType.NARRATIVE.value: 0.15,
            ContentType.PUZZLE.value: 0.15,
            ContentType.COMBAT.value: 0.10,
            ContentType.STEALTH.value: 0.05,
        },
        "preferred_difficulty": DifficultyTier.NORMAL.value,
        "session_duration_minutes": 100.0,
        "session_frequency_per_week": 4.0,
        "completion_drive": 1.00,
        "risk_tolerance": 0.35,
        "novelty_seeking": 0.55,
        "social_orientation": 0.30,
    },
}

_CONTENT_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "combat_arena": {
        "content_type": ContentType.COMBAT.value,
        "base_difficulty": DifficultyTier.NORMAL.value,
        "base_rewards_multiplier": 1.0,
        "encounter_density": 0.6,
        "pacing_curve": [0.2, 0.4, 0.7, 0.9, 1.0],
        "rest_intervals": 3,
        "completion_time_minutes": 15.0,
    },
    "stealth_infiltration": {
        "content_type": ContentType.STEALTH.value,
        "base_difficulty": DifficultyTier.CHALLENGING.value,
        "base_rewards_multiplier": 1.3,
        "encounter_density": 0.3,
        "pacing_curve": [0.1, 0.3, 0.6, 0.8, 1.0],
        "rest_intervals": 2,
        "completion_time_minutes": 22.0,
    },
    "puzzle_chamber": {
        "content_type": ContentType.PUZZLE.value,
        "base_difficulty": DifficultyTier.NORMAL.value,
        "base_rewards_multiplier": 1.1,
        "encounter_density": 0.0,
        "pacing_curve": [0.1, 0.2, 0.5, 0.7, 1.0],
        "rest_intervals": 1,
        "completion_time_minutes": 18.0,
    },
    "exploration_zone": {
        "content_type": ContentType.EXPLORATION.value,
        "base_difficulty": DifficultyTier.CASUAL.value,
        "base_rewards_multiplier": 0.8,
        "encounter_density": 0.2,
        "pacing_curve": [0.0, 0.15, 0.3, 0.5, 1.0],
        "rest_intervals": 5,
        "completion_time_minutes": 30.0,
    },
    "narrative_sequence": {
        "content_type": ContentType.NARRATIVE.value,
        "base_difficulty": DifficultyTier.CASUAL.value,
        "base_rewards_multiplier": 0.7,
        "encounter_density": 0.1,
        "pacing_curve": [0.05, 0.2, 0.5, 0.8, 1.0],
        "rest_intervals": 2,
        "completion_time_minutes": 25.0,
    },
    "collection_hunt": {
        "content_type": ContentType.COLLECTION.value,
        "base_difficulty": DifficultyTier.NORMAL.value,
        "base_rewards_multiplier": 1.0,
        "encounter_density": 0.4,
        "pacing_curve": [0.0, 0.1, 0.3, 0.6, 1.0],
        "rest_intervals": 4,
        "completion_time_minutes": 20.0,
    },
}

_DIFFICULTY_TIER_VALUES: Dict[str, float] = {
    DifficultyTier.CASUAL.value: 0.2,
    DifficultyTier.NORMAL.value: 0.4,
    DifficultyTier.CHALLENGING.value: 0.6,
    DifficultyTier.HARDCORE.value: 0.8,
    DifficultyTier.NIGHTMARE.value: 0.95,
}

_DIFFICULTY_ADJUSTMENT_RULES: Dict[str, Dict[str, float]] = {
    "player_too_skilled": {
        "performance_threshold": 0.85,
        "difficulty_step": 0.15,
        "max_tier_index": 4,
    },
    "player_struggling": {
        "performance_threshold": 0.30,
        "difficulty_step": -0.15,
        "min_tier_index": 0,
    },
    "player_bored": {
        "engagement_threshold": 0.25,
        "difficulty_step": 0.10,
        "content_novelty_boost": 0.30,
    },
    "player_frustrated": {
        "engagement_threshold": 0.15,
        "death_rate_threshold": 0.40,
        "difficulty_step": -0.20,
        "content_novelty_boost": -0.10,
    },
}


@dataclass
class ContentProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    archetype: str = PlayerArchetype.EXPLORER.value
    archetype_confidence: float = 0.7
    content_weights: Dict[str, float] = field(default_factory=dict)
    preferred_difficulty: str = DifficultyTier.NORMAL.value
    session_duration_minutes: float = 45.0
    session_frequency_per_week: float = 3.0
    completion_drive: float = 0.6
    risk_tolerance: float = 0.5
    novelty_seeking: float = 0.5
    social_orientation: float = 0.3
    recent_content_history: List[str] = field(default_factory=list)
    total_sessions_analyzed: int = 0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "archetype": self.archetype,
            "archetype_confidence": round(self.archetype_confidence, 3),
            "content_weights": {k: round(v, 3) for k, v in self.content_weights.items()},
            "preferred_difficulty": self.preferred_difficulty,
            "session_duration_minutes": round(self.session_duration_minutes, 1),
            "session_frequency_per_week": round(self.session_frequency_per_week, 1),
            "completion_drive": round(self.completion_drive, 3),
            "risk_tolerance": round(self.risk_tolerance, 3),
            "novelty_seeking": round(self.novelty_seeking, 3),
            "social_orientation": round(self.social_orientation, 3),
            "recent_content_history": self.recent_content_history[-20:],
            "total_sessions_analyzed": self.total_sessions_analyzed,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class AdaptiveDifficulty:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    current_tier: str = DifficultyTier.NORMAL.value
    current_numeric_difficulty: float = 0.4
    skill_estimation: float = 0.5
    skill_confidence: float = 0.3
    challenge_rating: float = 0.5
    performance_avg: float = 0.5
    performance_variance: float = 0.1
    death_rate_avg: float = 0.1
    completion_rate_avg: float = 0.5
    adjustment_history: List[Dict[str, Any]] = field(default_factory=list)
    stability_counter: int = 0
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "current_tier": self.current_tier,
            "current_numeric_difficulty": round(self.current_numeric_difficulty, 3),
            "skill_estimation": round(self.skill_estimation, 3),
            "skill_confidence": round(self.skill_confidence, 3),
            "challenge_rating": round(self.challenge_rating, 3),
            "performance_avg": round(self.performance_avg, 3),
            "performance_variance": round(self.performance_variance, 3),
            "death_rate_avg": round(self.death_rate_avg, 3),
            "completion_rate_avg": round(self.completion_rate_avg, 3),
            "adjustment_count": len(self.adjustment_history),
            "stability_counter": self.stability_counter,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ContentVariant:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    content_type: str = ContentType.COMBAT.value
    template_key: str = ""
    difficulty_tier: str = DifficultyTier.NORMAL.value
    player_skill_match_score: float = 0.5
    rewards_multiplier: float = 1.0
    encounter_count: int = 5
    treasure_count: int = 3
    puzzle_count: int = 1
    stealth_segments: int = 0
    narrative_beats: int = 2
    estimated_completion_minutes: float = 15.0
    engagement_potential: float = 0.6
    novelty_factor: float = 0.5
    risk_level: float = 0.3
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "content_type": self.content_type,
            "template_key": self.template_key,
            "difficulty_tier": self.difficulty_tier,
            "player_skill_match_score": round(self.player_skill_match_score, 3),
            "rewards_multiplier": round(self.rewards_multiplier, 2),
            "encounter_count": self.encounter_count,
            "treasure_count": self.treasure_count,
            "puzzle_count": self.puzzle_count,
            "stealth_segments": self.stealth_segments,
            "narrative_beats": self.narrative_beats,
            "estimated_completion_minutes": round(self.estimated_completion_minutes, 1),
            "engagement_potential": round(self.engagement_potential, 3),
            "novelty_factor": round(self.novelty_factor, 3),
            "risk_level": round(self.risk_level, 3),
            "created_at": self.created_at,
        }


class EngineAdaptiveContent:
    _instance: Optional["EngineAdaptiveContent"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "EngineAdaptiveContent":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EngineAdaptiveContent":
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._profiles: Dict[str, ContentProfile] = {}
        self._difficulties: Dict[str, AdaptiveDifficulty] = {}
        self._variants: Dict[str, List[ContentVariant]] = {}
        self._engagement_predictions: Dict[str, Dict[str, Any]] = {}
        self._economy_snapshots: Dict[str, Dict[str, Any]] = {}

        self._total_profiles_created: int = 0
        self._total_variants_generated: int = 0
        self._total_difficulty_adjustments: int = 0

    def analyze_player_profile(
        self,
        player_id: str,
        session_data: Optional[List[Dict[str, Any]]] = None,
        content_preferences: Optional[Dict[str, float]] = None,
        gameplay_metrics: Optional[Dict[str, Any]] = None,
    ) -> ContentProfile:
        _time_module.sleep(0.001)

        session_data = session_data or []
        content_preferences = content_preferences or {}
        gameplay_metrics = gameplay_metrics or {}

        session_count = len(session_data)
        avg_session_minutes = 45.0
        if session_data:
            avg_session_minutes = sum(
                s.get("duration_minutes", 45.0) for s in session_data
            ) / session_count

        avg_death_rate = gameplay_metrics.get("death_rate", 0.1)
        avg_completion_rate = gameplay_metrics.get("completion_rate", 0.5)
        avg_accuracy = gameplay_metrics.get("accuracy", 0.5)

        archetype_scores: Dict[str, float] = {}
        for archetype_key, profile in _ARHCETYPE_PREFERENCE_PROFILES.items():
            score = 0.0

            if content_preferences:
                profile_weights = profile["content_weights"]
                for ct_key, ct_weight in content_preferences.items():
                    expected = profile_weights.get(ct_key, 0.0)
                    score += 1.0 - abs(ct_weight - expected)

            session_diff = abs(avg_session_minutes - profile["session_duration_minutes"])
            score += max(0.0, 1.0 - session_diff / 120.0)

            completion_diff = abs(avg_completion_rate - profile["completion_drive"])
            score += max(0.0, 1.0 - completion_diff)

            difficulty_map: Dict[str, float] = {
                DifficultyTier.CASUAL.value: 0.2,
                DifficultyTier.NORMAL.value: 0.4,
                DifficultyTier.CHALLENGING.value: 0.6,
                DifficultyTier.HARDCORE.value: 0.8,
                DifficultyTier.NIGHTMARE.value: 0.95,
            }
            preferred_diff_val = difficulty_map.get(
                profile["preferred_difficulty"], 0.4
            )
            actual_diff_val = difficulty_map.get(
                gameplay_metrics.get("preferred_difficulty", DifficultyTier.NORMAL.value), 0.4
            )
            score += max(0.0, 1.0 - abs(actual_diff_val - preferred_diff_val))

            archetype_scores[archetype_key] = score / 4.0

        best_archetype = max(archetype_scores, key=lambda k: archetype_scores[k])
        best_score = archetype_scores[best_archetype]
        sorted_scores = sorted(archetype_scores.values(), reverse=True)
        confidence = best_score
        if len(sorted_scores) > 1:
            margin = sorted_scores[0] - sorted_scores[1]
            confidence = min(0.95, best_score * (0.5 + 0.5 * margin / max(sorted_scores[0], 0.01)))

        archetype_profile = _ARHCETYPE_PREFERENCE_PROFILES[best_archetype]

        profile = ContentProfile(
            player_id=player_id,
            archetype=best_archetype,
            archetype_confidence=round(confidence, 3),
            content_weights=content_preferences or archetype_profile["content_weights"],
            preferred_difficulty=gameplay_metrics.get(
                "preferred_difficulty", archetype_profile["preferred_difficulty"]
            ),
            session_duration_minutes=avg_session_minutes,
            session_frequency_per_week=gameplay_metrics.get(
                "sessions_per_week", archetype_profile["session_frequency_per_week"]
            ),
            completion_drive=avg_completion_rate,
            risk_tolerance=gameplay_metrics.get(
                "risk_tolerance", archetype_profile["risk_tolerance"]
            ),
            novelty_seeking=gameplay_metrics.get(
                "novelty_seeking", archetype_profile["novelty_seeking"]
            ),
            social_orientation=gameplay_metrics.get(
                "social_orientation", archetype_profile["social_orientation"]
            ),
            total_sessions_analyzed=session_count,
        )

        if session_data:
            profile.recent_content_history = [
                s.get("content_type", ContentType.COMBAT.value)
                for s in session_data[-20:]
            ]

        self._profiles[player_id] = profile
        self._total_profiles_created += 1
        return profile

    def compute_adaptive_difficulty(
        self,
        player_id: str,
        recent_performance: Optional[Dict[str, Any]] = None,
        deaths: int = 0,
        completion_time_seconds: float = 120.0,
        expected_time_seconds: float = 120.0,
        accuracy: float = 0.7,
    ) -> AdaptiveDifficulty:
        _time_module.sleep(0.001)

        recent_performance = recent_performance or {}
        difficulty_state = self._difficulties.get(player_id)
        if difficulty_state is None:
            difficulty_state = AdaptiveDifficulty(player_id=player_id)
            self._difficulties[player_id] = difficulty_state

        time_ratio = expected_time_seconds / max(completion_time_seconds, 1.0)
        time_performance = min(1.0, max(0.0, time_ratio * 0.8 + 0.1))

        death_count = deaths + recent_performance.get("additional_deaths", 0)
        death_rate = min(1.0, death_count / max(death_count + 5, 1))
        survival_performance = 1.0 - death_rate

        raw_performance = (
            time_performance * 0.35
            + survival_performance * 0.35
            + accuracy * 0.30
        )

        alpha = 0.3
        difficulty_state.performance_avg = (
            alpha * raw_performance
            + (1.0 - alpha) * difficulty_state.performance_avg
        )
        difficulty_state.performance_variance = (
            0.9 * difficulty_state.performance_variance
            + 0.1 * (raw_performance - difficulty_state.performance_avg) ** 2
        )
        difficulty_state.death_rate_avg = (
            0.8 * difficulty_state.death_rate_avg + 0.2 * death_rate
        )
        difficulty_state.completion_rate_avg = (
            0.8 * difficulty_state.completion_rate_avg + 0.2 * time_performance
        )

        skill_delta = raw_performance - 0.6
        skill_adjustment = skill_delta * 0.15
        difficulty_state.skill_estimation = max(
            0.1, min(0.98, difficulty_state.skill_estimation + skill_adjustment)
        )
        difficulty_state.skill_confidence = min(
            0.95, difficulty_state.skill_confidence + 0.02
        )

        target_difficulty = raw_performance

        adjustment_record = {
            "timestamp": _time_module.time(),
            "previous_difficulty": difficulty_state.current_numeric_difficulty,
            "raw_performance": round(raw_performance, 3),
            "death_rate": round(death_rate, 3),
            "skill_estimation": round(difficulty_state.skill_estimation, 3),
        }

        if raw_performance > _DIFFICULTY_ADJUSTMENT_RULES["player_too_skilled"]["performance_threshold"]:
            target_difficulty += _DIFFICULTY_ADJUSTMENT_RULES["player_too_skilled"]["difficulty_step"]
        elif raw_performance < _DIFFICULTY_ADJUSTMENT_RULES["player_struggling"]["performance_threshold"]:
            target_difficulty += _DIFFICULTY_ADJUSTMENT_RULES["player_struggling"]["difficulty_step"]

        if death_rate > _DIFFICULTY_ADJUSTMENT_RULES["player_frustrated"]["death_rate_threshold"]:
            target_difficulty += _DIFFICULTY_ADJUSTMENT_RULES["player_frustrated"]["difficulty_step"]

        smoothing = 0.4
        difficulty_state.current_numeric_difficulty = max(
            0.1, min(0.98,
                smoothing * target_difficulty
                + (1.0 - smoothing) * difficulty_state.current_numeric_difficulty
            )
        )

        tier_boundaries = [
            (0.0, 0.30, DifficultyTier.CASUAL.value),
            (0.30, 0.50, DifficultyTier.NORMAL.value),
            (0.50, 0.70, DifficultyTier.CHALLENGING.value),
            (0.70, 0.88, DifficultyTier.HARDCORE.value),
            (0.88, 1.01, DifficultyTier.NIGHTMARE.value),
        ]
        for lo, hi, tier_name in tier_boundaries:
            if lo <= difficulty_state.current_numeric_difficulty < hi:
                difficulty_state.current_tier = tier_name
                break

        difficulty_state.challenge_rating = (
            difficulty_state.current_numeric_difficulty * 0.6
            + (1.0 - difficulty_state.skill_estimation) * 0.4
        )

        adjustment_record["new_difficulty"] = difficulty_state.current_numeric_difficulty
        adjustment_record["new_tier"] = difficulty_state.current_tier
        difficulty_state.adjustment_history.append(adjustment_record)

        if len(difficulty_state.adjustment_history) > 50:
            difficulty_state.adjustment_history = difficulty_state.adjustment_history[-50:]

        stability_tolerance = 0.03
        if abs(skill_adjustment) < stability_tolerance:
            difficulty_state.stability_counter += 1
        else:
            difficulty_state.stability_counter = max(0, difficulty_state.stability_counter - 1)

        difficulty_state.updated_at = _time_module.time()
        self._total_difficulty_adjustments += 1
        return difficulty_state

    def select_content_variant(
        self,
        player_id: str,
        available_templates: Optional[List[str]] = None,
        content_history: Optional[List[str]] = None,
    ) -> ContentVariant:
        _time_module.sleep(0.001)

        profile = self._profiles.get(player_id)
        if profile is None:
            profile = self.analyze_player_profile(player_id)

        difficulty_state = self._difficulties.get(player_id)
        if difficulty_state is None:
            difficulty_state = self.compute_adaptive_difficulty(player_id)

        available_templates = available_templates or list(_CONTENT_TEMPLATES.keys())
        content_history = content_history or profile.recent_content_history

        content_scores: Dict[str, float] = {}
        for template_key in available_templates:
            template = _CONTENT_TEMPLATES.get(template_key)
            if template is None:
                continue

            ct = template["content_type"]
            preference_weight = profile.content_weights.get(ct, 0.1)

            template_difficulty = _DIFFICULTY_TIER_VALUES.get(
                template["base_difficulty"], 0.4
            )
            player_skill = difficulty_state.skill_estimation
            difficulty_match = 1.0 - abs(template_difficulty - player_skill)

            novelty_bonus = 0.0
            if ct not in content_history[-5:]:
                novelty_bonus = 0.25

            history_count = content_history.count(ct)
            fatigue_penalty = max(0.0, history_count * 0.05)

            score = (
                preference_weight * 0.45
                + difficulty_match * 0.35
                + novelty_bonus * 0.15
                - fatigue_penalty * 0.05
            )
            content_scores[template_key] = score

        best_template_key = max(content_scores, key=lambda k: content_scores[k])
        best_template = _CONTENT_TEMPLATES[best_template_key]

        skill_diff = difficulty_state.skill_estimation - _DIFFICULTY_TIER_VALUES.get(
            best_template["base_difficulty"], 0.4
        )
        match_score = 1.0 - abs(skill_diff) / 0.8
        match_score = max(0.1, min(1.0, match_score))

        rewards_base = best_template["base_rewards_multiplier"]
        difficulty_multiplier = 1.0 + (difficulty_state.current_numeric_difficulty - 0.4) * 0.5
        skill_multiplier = 1.0 + (1.0 - match_score) * 0.3
        rewards_multiplier = rewards_base * difficulty_multiplier * skill_multiplier
        rewards_multiplier = max(0.3, min(3.0, rewards_multiplier))

        density = best_template["encounter_density"]
        encounter_count = max(1, int(density * 12 * difficulty_state.current_numeric_difficulty + 5))
        treasure_count = max(1, int(encounter_count * 0.5 + 1))
        puzzle_count = 1 if best_template["content_type"] == ContentType.PUZZLE.value else max(0, int(encounter_count * 0.15))
        stealth_segments = max(0, int(encounter_count * 0.1)) if best_template["content_type"] == ContentType.STEALTH.value else 0
        narrative_beats = 3 if best_template["content_type"] == ContentType.NARRATIVE.value else max(1, int(encounter_count * 0.2))

        engagement_base = match_score * 0.5 + profile.novelty_seeking * 0.3 + (1.0 - fatigue_penalty) * 0.2
        engagement_potential = max(0.1, min(1.0, engagement_base))

        variant = ContentVariant(
            player_id=player_id,
            content_type=best_template["content_type"],
            template_key=best_template_key,
            difficulty_tier=difficulty_state.current_tier,
            player_skill_match_score=round(match_score, 3),
            rewards_multiplier=round(rewards_multiplier, 2),
            encounter_count=encounter_count,
            treasure_count=treasure_count,
            puzzle_count=puzzle_count,
            stealth_segments=stealth_segments,
            narrative_beats=narrative_beats,
            estimated_completion_minutes=best_template.get("completion_time_minutes", 15.0)
            * (0.8 + 0.4 * difficulty_state.current_numeric_difficulty),
            engagement_potential=round(engagement_potential, 3),
            novelty_factor=round(profile.novelty_seeking, 3),
            risk_level=round(difficulty_state.current_numeric_difficulty, 3),
        )

        if player_id not in self._variants:
            self._variants[player_id] = []
        self._variants[player_id].append(variant)
        self._total_variants_generated += 1

        profile.recent_content_history.append(best_template["content_type"])
        if len(profile.recent_content_history) > 20:
            profile.recent_content_history = profile.recent_content_history[-20:]
        profile.updated_at = _time_module.time()

        return variant

    def adjust_reward_curves(
        self,
        player_id: str,
        base_rewards: Optional[Dict[str, float]] = None,
        reward_velocity: float = 1.0,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        base_rewards = base_rewards or {
            "experience": 100.0,
            "currency": 50.0,
            "items": 3.0,
            "rare_items": 0.0,
        }

        difficulty_state = self._difficulties.get(player_id)
        profile = self._profiles.get(player_id)

        difficulty_mult = 1.0
        if difficulty_state is not None:
            difficulty_mult = 1.0 + (difficulty_state.current_numeric_difficulty - 0.4) * 1.5

        completion_bonus = 1.0
        if profile is not None:
            completion_bonus = 1.0 + profile.completion_drive * 0.5

        risk_multiplier = 0.8
        if profile is not None and profile.risk_tolerance > 0.6:
            risk_multiplier = 1.0 + profile.risk_tolerance * 0.8

        adjusted_rewards: Dict[str, float] = {}
        for reward_key, base_value in base_rewards.items():
            if reward_key == "rare_items":
                adjusted_rewards[reward_key] = base_value + difficulty_mult * 0.3 + completion_bonus * 0.2
            elif reward_key == "experience":
                adjusted_rewards[reward_key] = base_value * difficulty_mult * completion_bonus
            else:
                adjusted_rewards[reward_key] = base_value * difficulty_mult * risk_multiplier

        adjusted_rewards = {
            k: max(0.0, round(v * reward_velocity, 2))
            for k, v in adjusted_rewards.items()
        }

        pacing_bonus = 1.0
        if difficulty_state is not None and difficulty_state.stability_counter > 5:
            pacing_bonus = 1.15

        return {
            "player_id": player_id,
            "adjusted_rewards": adjusted_rewards,
            "difficulty_multiplier": round(difficulty_mult, 2),
            "completion_bonus": round(completion_bonus, 2),
            "risk_multiplier": round(risk_multiplier, 2),
            "pacing_bonus": round(pacing_bonus, 2),
            "effective_velocity": round(reward_velocity * pacing_bonus, 3),
        }

    def generate_adaptive_encounters(
        self,
        player_id: str,
        encounter_count: int = 5,
        content_type: str = ContentType.COMBAT.value,
        target_difficulty: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        _time_module.sleep(0.001)

        difficulty_state = self._difficulties.get(player_id)
        if difficulty_state is None:
            difficulty_state = self.compute_adaptive_difficulty(player_id)

        profile = self._profiles.get(player_id)
        skill_level = difficulty_state.skill_estimation
        if target_difficulty is None:
            target_difficulty = difficulty_state.current_numeric_difficulty

        rng = random.Random(hash(player_id) % (2**31))

        encounters: List[Dict[str, Any]] = []
        for i in range(encounter_count):
            position_in_sequence = i / max(encounter_count - 1, 1)
            progression_mult = 0.7 + position_in_sequence * 0.6

            variance = rng.uniform(-0.15, 0.15)
            encounter_difficulty = max(0.1, min(0.98, target_difficulty * progression_mult + variance))

            skill_gap = encounter_difficulty - skill_level
            challenge_category = "optimal"
            if skill_gap > 0.15:
                challenge_category = "stretch"
            elif skill_gap < -0.15:
                challenge_category = "comfort"

            enemy_count = max(1, int(2 + encounter_difficulty * 6 + rng.randint(-1, 1)))
            if content_type == ContentType.STEALTH.value:
                enemy_count = max(1, int(enemy_count * 0.6))
            elif content_type == ContentType.NARRATIVE.value:
                enemy_count = max(0, int(enemy_count * 0.3))

            base_health = 50.0 + encounter_difficulty * 150.0
            base_damage = 8.0 + encounter_difficulty * 25.0

            if profile is not None and profile.risk_tolerance > 0.7:
                base_health *= 1.15
                base_damage *= 1.10

            encounter = {
                "encounter_id": uuid.uuid4().hex[:12],
                "index": i,
                "difficulty": round(encounter_difficulty, 3),
                "challenge_category": challenge_category,
                "enemy_count": enemy_count,
                "enemy_base_health": round(base_health, 1),
                "enemy_base_damage": round(base_damage, 1),
                "content_type": content_type,
                "completion_time_estimate": round(60.0 + encounter_difficulty * 180.0, 1),
                "xp_reward": round(50.0 + encounter_difficulty * 200.0, 1),
            }
            encounters.append(encounter)

        return encounters

    def predict_player_engagement(
        self,
        player_id: str,
        recent_session_data: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        profile = self._profiles.get(player_id)
        difficulty_state = self._difficulties.get(player_id)
        recent_session_data = recent_session_data or []

        session_count = len(recent_session_data)
        avg_duration = 0.0
        session_completion_rate = 0.5
        session_frequency = 0.0

        if session_count > 0:
            avg_duration = sum(
                s.get("duration_minutes", 0.0) for s in recent_session_data
            ) / session_count
            session_completion_rate = sum(
                1.0 if s.get("completed", False) else 0.0 for s in recent_session_data
            ) / session_count

            if session_count >= 2:
                timestamps = sorted(s.get("timestamp", 0.0) for s in recent_session_data)
                intervals = [
                    timestamps[i + 1] - timestamps[i]
                    for i in range(len(timestamps) - 1)
                ]
                avg_interval = sum(intervals) / len(intervals)
                session_frequency = 86400.0 / max(avg_interval, 3600.0)

        engagement_score = 0.5
        churn_risk = 0.3

        if profile is not None:
            duration_match = 1.0
            if session_count > 0 and profile.session_duration_minutes > 0:
                duration_ratio = avg_duration / profile.session_duration_minutes
                duration_match = 1.0 - abs(duration_ratio - 1.0) * 0.5
                duration_match = max(0.0, min(1.0, duration_match))

            engagement_score = (
                duration_match * 0.25
                + session_completion_rate * 0.30
                + profile.completion_drive * 0.20
                + min(1.0, session_frequency / 5.0) * 0.15
                + profile.novelty_seeking * 0.10
            )

        if difficulty_state is not None:
            performance_variance_factor = min(1.0, difficulty_state.performance_variance * 10.0)
            skill_challenge_balance = 1.0 - abs(
                difficulty_state.skill_estimation - difficulty_state.current_numeric_difficulty
            ) / 0.5

            churn_risk = (
                (1.0 - engagement_score) * 0.40
                + (1.0 - session_completion_rate) * 0.25
                + (1.0 - skill_challenge_balance) * 0.20
                + performance_variance_factor * 0.15
            )
            churn_risk = max(0.0, min(1.0, churn_risk))

            if difficulty_state.stability_counter > 10:
                churn_risk *= 0.85

        if session_count >= 3:
            durations = [s.get("duration_minutes", 0.0) for s in recent_session_data[-3:]]
            if all(d < 10.0 for d in durations):
                churn_risk = min(1.0, churn_risk + 0.15)
            if durations and durations[-1] < durations[-2] < durations[-3]:
                churn_risk = min(1.0, churn_risk + 0.10)

        risk_label = "low"
        if churn_risk > 0.6:
            risk_label = "high"
        elif churn_risk > 0.35:
            risk_label = "moderate"

        intervention = None
        if risk_label in ("high", "moderate") and profile is not None:
            if churn_risk > 0.5:
                intervention = {
                    "type": "difficulty_reduction",
                    "magnitude": 0.15,
                    "message": "Introduce easier content variants to rebuild confidence",
                }
            else:
                intervention = {
                    "type": "novelty_injection",
                    "magnitude": 0.2,
                    "message": "Introduce fresh content types to re-engage player",
                }

        prediction = {
            "player_id": player_id,
            "engagement_score": round(engagement_score, 3),
            "churn_risk": round(churn_risk, 3),
            "churn_risk_label": risk_label,
            "sessions_analyzed": session_count,
            "avg_session_duration": round(avg_duration, 1),
            "session_completion_rate": round(session_completion_rate, 3),
            "weekly_session_estimate": round(session_frequency, 1),
            "recommended_intervention": intervention,
            "prediction_timestamp": _time_module.time(),
        }

        self._engagement_predictions[player_id] = prediction
        return prediction

    def balance_game_economy(
        self,
        player_id: str,
        current_inventory: Optional[Dict[str, float]] = None,
        market_prices: Optional[Dict[str, float]] = None,
        inflation_rate: float = 1.0,
    ) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        current_inventory = current_inventory or {
            "currency": 500.0,
            "resources": 100.0,
            "rare_items": 2.0,
        }
        market_prices = market_prices or {
            "health_potion": 10.0,
            "mana_potion": 12.0,
            "weapon_upgrade": 200.0,
            "armor_upgrade": 180.0,
            "rare_material": 75.0,
        }

        profile = self._profiles.get(player_id)
        difficulty_state = self._difficulties.get(player_id)

        purchase_power = current_inventory.get("currency", 0.0)
        resource_stock = current_inventory.get("resources", 0.0)
        rare_stock = current_inventory.get("rare_items", 0.0)

        difficulty_scale = 1.0
        if difficulty_state is not None:
            difficulty_scale = 1.0 + (difficulty_state.current_numeric_difficulty - 0.4) * 1.2

        completion_scale = 1.0
        if profile is not None:
            completion_scale = 1.0 + (1.0 - profile.completion_drive) * 0.4

        adjusted_prices: Dict[str, float] = {}
        for item_name, base_price in market_prices.items():
            scaled_price = base_price * difficulty_scale * completion_scale * inflation_rate
            if purchase_power > 5000.0:
                scaled_price *= 1.10
            elif purchase_power < 200.0:
                scaled_price *= 0.85

            if "rare" in item_name.lower() and rare_stock > 10:
                scaled_price *= 0.90

            adjusted_prices[item_name] = round(max(1.0, scaled_price), 2)

        supply_demand_ratio = 1.0
        if resource_stock > 1000:
            supply_demand_ratio = max(0.5, 1.0 - (resource_stock - 1000) / 5000.0)
        elif resource_stock < 50:
            supply_demand_ratio = min(1.5, 1.0 + (50 - resource_stock) / 100.0)

        for item_name in adjusted_prices:
            if "resource" in item_name.lower() or "material" in item_name.lower():
                adjusted_prices[item_name] = round(
                    adjusted_prices[item_name] * supply_demand_ratio, 2
                )

        affordable_items = [
            name for name, price in adjusted_prices.items()
            if price <= purchase_power
        ]
        affordability_ratio = len(affordable_items) / max(len(adjusted_prices), 1)

        economy_health = 0.5
        if affordability_ratio > 0.7:
            economy_health = 0.75
        elif affordability_ratio < 0.2:
            economy_health = 0.3

        loot_multiplier = 1.0
        if economy_health < 0.4:
            loot_multiplier = 1.3
        elif economy_health > 0.7:
            loot_multiplier = 0.85

        snapshot = {
            "player_id": player_id,
            "adjusted_prices": adjusted_prices,
            "purchase_power": round(purchase_power, 2),
            "supply_demand_ratio": round(supply_demand_ratio, 3),
            "affordability_ratio": round(affordability_ratio, 3),
            "economy_health_score": round(economy_health, 2),
            "recommended_loot_multiplier": round(loot_multiplier, 2),
            "inflation_rate_applied": round(inflation_rate, 3),
            "difficulty_cost_scale": round(difficulty_scale, 3),
            "completion_cost_scale": round(completion_scale, 3),
            "snapshot_timestamp": _time_module.time(),
        }

        self._economy_snapshots[player_id] = snapshot
        return snapshot

    def get_player_profile(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Return a player content profile by ID."""
        _time_module.sleep(0.001)
        profile = self._profiles.get(player_id)
        return profile.to_dict() if profile else None

    def get_difficulty_state(self, player_id: str) -> Optional[Dict[str, Any]]:
        """Return the current difficulty state for a player."""
        _time_module.sleep(0.001)
        state = self._difficulty_states.get(player_id)
        return state.to_dict() if state else None

    def get_stats(self) -> Dict[str, Any]:
        _time_module.sleep(0.001)

        archetype_counts: Dict[str, int] = {}
        difficulty_tier_counts: Dict[str, int] = {}

        for profile in self._profiles.values():
            arch = profile.archetype
            archetype_counts[arch] = archetype_counts.get(arch, 0) + 1

        for diff in self._difficulties.values():
            tier = diff.current_tier
            difficulty_tier_counts[tier] = difficulty_tier_counts.get(tier, 0) + 1

        total_variants = 0
        variant_type_counts: Dict[str, int] = {}
        for variants in self._variants.values():
            total_variants += len(variants)
            for v in variants:
                ct = v.content_type
                variant_type_counts[ct] = variant_type_counts.get(ct, 0) + 1

        avg_engagement = 0.0
        avg_churn_risk = 0.0
        prediction_count = len(self._engagement_predictions)
        if prediction_count > 0:
            avg_engagement = sum(
                p.get("engagement_score", 0.5) for p in self._engagement_predictions.values()
            ) / prediction_count
            avg_churn_risk = sum(
                p.get("churn_risk", 0.3) for p in self._engagement_predictions.values()
            ) / prediction_count

        return {
            "total_profiles_created": self._total_profiles_created,
            "active_profiles": len(self._profiles),
            "total_variants_generated": self._total_variants_generated,
            "total_difficulty_adjustments": self._total_difficulty_adjustments,
            "total_engagement_predictions": prediction_count,
            "total_economy_snapshots": len(self._economy_snapshots),
            "archetype_distribution": archetype_counts,
            "difficulty_tier_distribution": difficulty_tier_counts,
            "content_type_distribution": variant_type_counts,
            "average_engagement_score": round(avg_engagement, 3),
            "average_churn_risk": round(avg_churn_risk, 3),
            "available_content_templates": len(_CONTENT_TEMPLATES),
            "available_archetype_profiles": len(_ARHCETYPE_PREFERENCE_PROFILES),
            "difficulty_adjustment_rules": len(_DIFFICULTY_ADJUSTMENT_RULES),
        }


def get_adaptive_content_engine() -> EngineAdaptiveContent:
    return EngineAdaptiveContent.get_instance()