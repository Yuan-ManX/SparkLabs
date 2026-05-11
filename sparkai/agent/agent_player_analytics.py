"""
SparkLabs Agent - Player Analytics Engine

Behavioral prediction and gameplay pattern analysis for AI-native
games. Models player skill progression, engagement curves,
drop-off prediction, and session quality scoring. Provides data-driven
insights for game designers to optimize retention, difficulty pacing,
and content distribution based on real or simulated player telemetry.

Architecture:
  PlayerAnalyticsEngine
    |-- SkillModel (Bayesian skill estimation from gameplay data)
    |-- EngagementTracker (session duration, frequency, intensity)
    |-- ChurnPredictor (drop-off risk scoring with early warning)
    |-- SegmentClassifier (player archetype categorization)
    |-- SessionAnalyzer (per-session quality and frustration metrics)
    |-- TrendAggregator (cohort-level pattern detection)

Player Archetypes:
  - COMPLETIONIST: aims for 100% content coverage
  - SPEEDRUNNER: prioritizes completion time over exploration
  - EXPLORER: prioritizes discovery and world interaction
  - SOCIALIZER: values multiplayer and community features
  - CHALLENGER: seeks difficulty and mastery
  - CASUAL: values accessibility and low-friction sessions
"""

from __future__ import annotations

import math
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlayerArchetype(Enum):
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    EXPLORER = "explorer"
    SOCIALIZER = "socializer"
    CHALLENGER = "challenger"
    CASUAL = "casual"


class SessionQuality(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NEUTRAL = "neutral"
    FRUSTRATING = "frustrating"
    ABANDONED = "abandoned"


class ChurnRisk(Enum):
    LOW = (0.0, 0.2, "low")
    MODERATE = (0.2, 0.5, "moderate")
    HIGH = (0.5, 0.75, "high")
    CRITICAL = (0.75, 1.0, "critical")

    def __new__(cls, min_p, max_p, label):
        obj = object.__new__(cls)
        obj._value_ = label
        obj.min_prob = min_p
        obj.max_prob = max_p
        return obj

    @classmethod
    def from_prob(cls, prob: float):
        for tier in cls:
            if tier.min_prob <= prob <= tier.max_prob:
                return tier
        return cls.CRITICAL


@dataclass
class PlayerProfile:
    player_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    skill_rating: float = 0.5
    skill_confidence: float = 0.1
    engagement_score: float = 0.5
    churn_risk: float = 0.0
    total_sessions: int = 0
    total_playtime_minutes: float = 0.0
    avg_session_minutes: float = 0.0
    session_streak: int = 0
    days_since_last_session: float = 0.0
    frustration_index: float = 0.0
    favorite_mechanics: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "player_id": self.player_id,
            "archetype": self.archetype.value,
            "skill": round(self.skill_rating, 2),
            "engagement": round(self.engagement_score, 2),
            "churn_risk": round(self.churn_risk, 2),
            "churn_tier": ChurnRisk.from_prob(self.churn_risk).value,
            "total_sessions": self.total_sessions,
            "avg_session_mins": round(self.avg_session_minutes, 1),
            "streak": self.session_streak,
        }


@dataclass
class SessionRecord:
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    player_id: str = ""
    duration_minutes: float = 0.0
    actions_performed: int = 0
    deaths: int = 0
    items_collected: int = 0
    enemies_defeated: int = 0
    progress_pct: float = 0.0
    quality: SessionQuality = SessionQuality.NEUTRAL
    frustration_events: int = 0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "player_id": self.player_id,
            "duration_mins": round(self.duration_minutes, 1),
            "quality": self.quality.value,
            "progress_pct": round(self.progress_pct, 1),
        }


class PlayerAnalyticsEngine:
    _instance: Optional[PlayerAnalyticsEngine] = None

    @classmethod
    def get_instance(cls) -> PlayerAnalyticsEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._players: Dict[str, PlayerProfile] = {}
        self._sessions: Dict[str, List[SessionRecord]] = {}
        self._churn_events: List[Dict[str, Any]] = []
        self._total_players: int = 0

    def register_player(self, player_id: str) -> PlayerProfile:
        profile = PlayerProfile(player_id=player_id)
        self._players[player_id] = profile
        self._sessions[player_id] = []
        self._total_players += 1
        return profile

    def record_session(self, player_id: str, duration_minutes: float,
                       actions: int = 0, deaths: int = 0, items: int = 0,
                       enemies: int = 0, progress: float = 0.0,
                       frustration_events: int = 0) -> Optional[SessionRecord]:
        player = self._players.get(player_id)
        if player is None:
            return None

        session = SessionRecord(
            player_id=player_id,
            duration_minutes=duration_minutes,
            actions_performed=actions,
            deaths=deaths,
            items_collected=items,
            enemies_defeated=enemies,
            progress_pct=progress,
            frustration_events=frustration_events,
        )

        if frustration_events > 5:
            session.quality = SessionQuality.FRUSTRATING
        elif duration_minutes > 30 and progress > 10:
            session.quality = SessionQuality.EXCELLENT
        elif deaths > 10 and progress < 5:
            session.quality = SessionQuality.FRUSTRATING
        elif duration_minutes < 2:
            session.quality = SessionQuality.ABANDONED

        self._sessions[player_id].append(session)
        self._update_player_profile(player, session)
        return session

    def _update_player_profile(self, player: PlayerProfile, session: SessionRecord):
        player.total_sessions += 1
        player.total_playtime_minutes += session.duration_minutes
        player.avg_session_minutes = player.total_playtime_minutes / player.total_sessions

        if session.quality == SessionQuality.FRUSTRATING:
            player.frustration_index = min(1.0, player.frustration_index + 0.1)
        else:
            player.frustration_index = max(0.0, player.frustration_index - 0.02)

        player.days_since_last_session = 0.0
        player.session_streak += 1

        if player.total_sessions > 5:
            actions_rate = session.actions_performed / max(1, session.duration_minutes)
            player.skill_rating = player.skill_rating * 0.8 + min(1.0, actions_rate * 0.02) * 0.2
            player.skill_confidence = min(1.0, player.skill_confidence + 0.02)

        engagement = min(1.0, (
            player.session_streak * 0.1 +
            min(1.0, player.avg_session_minutes / 30) * 0.3 +
            min(1.0, player.total_sessions / 20) * 0.3 +
            (1.0 - player.frustration_index) * 0.3
        ))
        player.engagement_score = engagement

        player.churn_risk = max(0.0, min(1.0, (
            (1.0 - engagement) * 0.6 +
            player.frustration_index * 0.3 +
            (0.1 if session.quality == SessionQuality.ABANDONED else 0.0)
        )))

        self._classify_archetype(player)

    def _classify_archetype(self, player: PlayerProfile):
        if player.total_sessions < 3:
            return
        if player.frustration_index < 0.1 and player.skill_rating > 0.7:
            player.archetype = PlayerArchetype.CHALLENGER
        elif player.avg_session_minutes < 15 and player.skill_rating > 0.6:
            player.archetype = PlayerArchetype.SPEEDRUNNER
        elif player.avg_session_minutes > 40:
            player.archetype = PlayerArchetype.EXPLORER
        elif player.total_sessions > 15 and player.engagement_score > 0.7:
            player.archetype = PlayerArchetype.COMPLETIONIST
        elif player.avg_session_minutes < 20 and player.skill_rating < 0.4:
            player.archetype = PlayerArchetype.CASUAL

    def predict_churn(self, player_id: str) -> Dict[str, Any]:
        player = self._players.get(player_id)
        if player is None:
            return {"error": "Player not found"}
        return {
            "player_id": player_id,
            "churn_risk": round(player.churn_risk, 3),
            "tier": ChurnRisk.from_prob(player.churn_risk).value,
            "factors": {
                "engagement": round(player.engagement_score, 2),
                "frustration": round(player.frustration_index, 2),
                "streak": player.session_streak,
            },
        }

    def get_cohort_insights(self) -> Dict[str, Any]:
        if not self._players:
            return {"players": 0}
        total = len(self._players)
        churning = sum(1 for p in self._players.values() if p.churn_risk > 0.5)
        archetypes = {}
        for p in self._players.values():
            key = p.archetype.value
            archetypes[key] = archetypes.get(key, 0) + 1
        return {
            "total_players": total,
            "churning_players": churning,
            "churn_rate": round(churning / max(1, total), 3),
            "avg_engagement": round(sum(p.engagement_score for p in self._players.values()) / max(1, total), 2),
            "avg_skill": round(sum(p.skill_rating for p in self._players.values()) / max(1, total), 2),
            "archetype_distribution": archetypes,
        }

    def get_player(self, player_id: str) -> Optional[PlayerProfile]:
        return self._players.get(player_id)

    def get_player_sessions(self, player_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        sessions = self._sessions.get(player_id, [])
        return [s.to_dict() for s in sessions[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_players": self._total_players,
            "active_players": len(self._players),
            "total_sessions": sum(len(s) for s in self._sessions.values()),
            **self.get_cohort_insights(),
        }


def get_player_analytics() -> PlayerAnalyticsEngine:
    return PlayerAnalyticsEngine.get_instance()