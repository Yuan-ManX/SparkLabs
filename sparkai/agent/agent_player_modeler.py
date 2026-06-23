"""
SparkLabs Agent - Player Modeler Engine

Player behavior modeling system that classifies playstyles, estimates
skill dimensions, tracks engagement levels, and generates adaptive
difficulty profiles. The engine analyzes session records to build
comprehensive player profiles and predict future behavior for
personalized gameplay experiences.

Architecture:
  PlayerModelerEngine (Singleton)
    |-- PlayerProfile (playstyle, skill ratings, engagement history)
    |-- SessionRecord (actions, decisions, successes, failures)
    |-- DifficultyProfile (adaptive parameters, adjustment history)
    |-- PlayerPrediction (predicted actions with confidence)

Core Capabilities:
  - Create and maintain player profiles with multi-dimensional skill ratings
  - Record gameplay sessions with detailed action and decision metrics
  - Classify playstyles based on behavioral patterns
  - Estimate skill across reaction, strategy, precision, adaptation, persistence
  - Predict player behavior with confidence scoring
  - Compute engagement levels to detect flow, boredom, and frustration
  - Suggest adaptive difficulty adjustments for optimal player experience
  - Generate behavioral insights from session history
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlaystyleType(Enum):
    """Player playstyle archetypes."""
    AGGRESSIVE = "aggressive"
    EXPLORER = "explorer"
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    SOCIAL = "social"
    STRATEGIST = "strategist"


class SkillDimension(Enum):
    """Dimensions of player skill for multi-faceted estimation."""
    REACTION = "reaction"
    STRATEGY = "strategy"
    PRECISION = "precision"
    ADAPTATION = "adaptation"
    PERSISTENCE = "persistence"


class EngagementLevel(Enum):
    """Player engagement states based on flow theory."""
    BORED = "bored"
    ENGAGED = "engaged"
    FLOW = "flow"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"


class SessionPhase(Enum):
    """Phases of a gameplay session."""
    TUTORIAL = "tutorial"
    EARLY_GAME = "early_game"
    MID_GAME = "mid_game"
    LATE_GAME = "late_game"
    END_GAME = "end_game"


# ---------------------------------------------------------------------------
# Playstyle Classification Rules
# ---------------------------------------------------------------------------

_PLAYSTYLE_INDICATORS: Dict[PlaystyleType, Dict[str, float]] = {
    PlaystyleType.AGGRESSIVE: {
        "attack_frequency": 0.3,
        "damage_dealt": 0.25,
        "risk_taking": 0.25,
        "combat_engagement": 0.2,
    },
    PlaystyleType.EXPLORER: {
        "area_explored": 0.3,
        "secrets_found": 0.25,
        "movement_distance": 0.25,
        "non_critical_path": 0.2,
    },
    PlaystyleType.COMPLETIONIST: {
        "objectives_completed": 0.3,
        "collectibles_found": 0.25,
        "side_quests": 0.25,
        "thoroughness": 0.2,
    },
    PlaystyleType.SPEEDRUNNER: {
        "completion_speed": 0.35,
        "efficiency": 0.3,
        "skip_rate": 0.2,
        "movement_optimization": 0.15,
    },
    PlaystyleType.SOCIAL: {
        "interactions": 0.3,
        "communication": 0.25,
        "cooperation": 0.25,
        "social_events": 0.2,
    },
    PlaystyleType.STRATEGIST: {
        "planning_time": 0.3,
        "resource_efficiency": 0.25,
        "tactical_decisions": 0.25,
        "win_rate": 0.2,
    },
}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class PlayerProfile:
    """A comprehensive player profile with behavioral and skill data.

    Tracks the player's playstyle classification, multi-dimensional
    skill ratings, engagement history, session statistics, preferred
    mechanics, and frustration triggers for personalized gameplay.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    playstyle: PlaystyleType = PlaystyleType.EXPLORER
    skill_ratings: Dict[str, float] = field(default_factory=dict)
    engagement_history: List[Dict[str, Any]] = field(default_factory=list)
    session_count: int = 0
    total_playtime: float = 0.0
    preferred_mechanics: List[str] = field(default_factory=list)
    frustration_triggers: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "playstyle": self.playstyle.value,
            "skill_ratings": {k: round(v, 4) for k, v in self.skill_ratings.items()},
            "engagement_entries": len(self.engagement_history),
            "session_count": self.session_count,
            "total_playtime": round(self.total_playtime, 2),
            "preferred_mechanics": self.preferred_mechanics,
            "frustration_triggers": self.frustration_triggers,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def get_skill(self, dimension: SkillDimension) -> float:
        return self.skill_ratings.get(dimension.value, 0.5)

    def set_skill(self, dimension: SkillDimension, value: float) -> None:
        self.skill_ratings[dimension.value] = max(0.0, min(1.0, value))
        self.updated_at = time.time()

    def get_average_skill(self) -> float:
        if not self.skill_ratings:
            return 0.5
        return sum(self.skill_ratings.values()) / len(self.skill_ratings)

    def record_engagement(self, level: EngagementLevel, score: float = 0.5) -> None:
        self.engagement_history.append({
            "level": level.value,
            "score": round(max(0.0, min(1.0, score)), 4),
            "timestamp": time.time(),
        })
        if len(self.engagement_history) > 200:
            self.engagement_history = self.engagement_history[-200:]


@dataclass
class SessionRecord:
    """A recorded gameplay session with detailed metrics.

    Captures the player's actions, decisions, failures, successes,
    time spent, and the phase of the game for each session. These
    records feed into skill estimation and playstyle classification.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    session_id: str = ""
    actions: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    failures: List[Dict[str, Any]] = field(default_factory=list)
    successes: List[Dict[str, Any]] = field(default_factory=list)
    time_spent: float = 0.0
    phase: SessionPhase = SessionPhase.EARLY_GAME
    metrics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "session_id": self.session_id,
            "action_count": len(self.actions),
            "decision_count": len(self.decisions),
            "failure_count": len(self.failures),
            "success_count": len(self.successes),
            "time_spent": round(self.time_spent, 2),
            "phase": self.phase.value,
            "metrics": self.metrics,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }

    def add_action(self, action_type: str, result: str = "", context: Optional[Dict[str, Any]] = None) -> None:
        self.actions.append({
            "action_type": action_type,
            "result": result,
            "context": context or {},
            "timestamp": time.time(),
        })

    def add_decision(self, decision: str, outcome: str = "", quality: float = 0.5) -> None:
        self.decisions.append({
            "decision": decision,
            "outcome": outcome,
            "quality": round(max(0.0, min(1.0, quality)), 4),
            "timestamp": time.time(),
        })

    def add_success(self, description: str, difficulty: float = 0.5) -> None:
        self.successes.append({
            "description": description,
            "difficulty": round(max(0.0, min(1.0, difficulty)), 4),
            "timestamp": time.time(),
        })

    def add_failure(self, description: str, cause: str = "") -> None:
        self.failures.append({
            "description": description,
            "cause": cause,
            "timestamp": time.time(),
        })

    def get_success_rate(self) -> float:
        total = len(self.successes) + len(self.failures)
        if total == 0:
            return 1.0
        return len(self.successes) / total

    def get_actions_per_minute(self) -> float:
        if self.time_spent <= 0:
            return 0.0
        return len(self.actions) / (self.time_spent / 60.0)


@dataclass
class DifficultyProfile:
    """Adaptive difficulty profile for a player.

    Tracks the current difficulty tier, parameters that can be
    adjusted in real-time, a history of adjustments, and the target
    engagement level for optimal player experience.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    current_tier: float = 0.5
    adaptive_parameters: Dict[str, float] = field(default_factory=dict)
    adjustment_history: List[Dict[str, Any]] = field(default_factory=list)
    target_engagement: EngagementLevel = EngagementLevel.FLOW
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "current_tier": round(self.current_tier, 4),
            "adaptive_parameters": self.adaptive_parameters,
            "adjustment_count": len(self.adjustment_history),
            "adjustment_history": self.adjustment_history[-10:],
            "target_engagement": self.target_engagement.value,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def record_adjustment(self, reason: str, delta: float, previous_tier: float) -> None:
        self.adjustment_history.append({
            "reason": reason,
            "delta": round(delta, 4),
            "previous_tier": round(previous_tier, 4),
            "new_tier": round(self.current_tier, 4),
            "timestamp": time.time(),
        })
        if len(self.adjustment_history) > 100:
            self.adjustment_history = self.adjustment_history[-100:]

    def adjust_tier(self, delta: float, reason: str = "") -> None:
        previous = self.current_tier
        self.current_tier = max(0.0, min(1.0, self.current_tier + delta))
        self.updated_at = time.time()
        if reason:
            self.record_adjustment(reason, delta, previous)


@dataclass
class PlayerPrediction:
    """A predicted player action with confidence and alternatives.

    Generated by the player modeler to anticipate what the player
    will do next, with confidence scoring and alternative actions
    ranked by likelihood.
    """
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    predicted_action: str = ""
    confidence: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    alternatives: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "player_id": self.player_id,
            "predicted_action": self.predicted_action,
            "confidence": round(self.confidence, 4),
            "context": self.context,
            "alternatives": self.alternatives,
            "alternative_count": len(self.alternatives),
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# PlayerModelerEngine
# ---------------------------------------------------------------------------

class PlayerModelerEngine:
    """Thread-safe singleton engine for player behavior modeling.

    Builds and maintains player profiles, records gameplay sessions,
    classifies playstyles, estimates skill dimensions, predicts
    behavior, computes engagement, and generates adaptive difficulty
    suggestions for personalized gameplay experiences.
    """

    _instance: Optional["PlayerModelerEngine"] = None
    _lock = threading.RLock()

    _MAX_PROFILES: int = 10000
    _MAX_SESSION_RECORDS: int = 100000
    _MAX_DIFFICULTY_PROFILES: int = 10000
    _MAX_PREDICTIONS: int = 5000
    _DEFAULT_SKILL: float = 0.5
    _SKILL_LEARNING_RATE: float = 0.1
    _ENGAGEMENT_WINDOW: int = 20

    def __init__(self) -> None:
        self._profiles: Dict[str, PlayerProfile] = {}
        self._profiles_by_player: Dict[str, str] = {}
        self._session_records: Dict[str, SessionRecord] = {}
        self._sessions_by_player: Dict[str, List[str]] = {}
        self._difficulty_profiles: Dict[str, DifficultyProfile] = {}
        self._difficulty_by_player: Dict[str, str] = {}
        self._predictions: Dict[str, PlayerPrediction] = {}
        self._predictions_by_player: Dict[str, List[str]] = {}
        self._total_profiles_created: int = 0
        self._total_sessions_recorded: int = 0
        self._total_predictions_made: int = 0
        self._total_insights_generated: int = 0

    @classmethod
    def get_instance(cls) -> "PlayerModelerEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def create_profile(
        self,
        player_id: str,
        playstyle: PlaystyleType = PlaystyleType.EXPLORER,
        skill_ratings: Optional[Dict[str, float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlayerProfile:
        with self._lock:
            existing_id = self._profiles_by_player.get(player_id)
            if existing_id is not None and existing_id in self._profiles:
                return self._profiles[existing_id]

            self._enforce_max_profiles()

            default_skills: Dict[str, float] = {}
            for dim in SkillDimension:
                default_skills[dim.value] = self._DEFAULT_SKILL
            if skill_ratings:
                default_skills.update({k: max(0.0, min(1.0, v)) for k, v in skill_ratings.items()})

            profile = PlayerProfile(
                player_id=player_id,
                playstyle=playstyle,
                skill_ratings=default_skills,
                metadata=metadata or {},
            )
            self._profiles[profile.id] = profile
            self._profiles_by_player[player_id] = profile.id
            self._total_profiles_created += 1
            return profile

    def get_profile(self, player_id: str) -> Optional[PlayerProfile]:
        with self._lock:
            pid = self._profiles_by_player.get(player_id)
            if pid is None:
                return None
            return self._profiles.get(pid)

    def list_profiles(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._profiles.values()]

    # ------------------------------------------------------------------
    # Session Recording
    # ------------------------------------------------------------------

    def record_session(
        self,
        player_id: str,
        session_id: str = "",
        actions: Optional[List[Dict[str, Any]]] = None,
        decisions: Optional[List[Dict[str, Any]]] = None,
        failures: Optional[List[Dict[str, Any]]] = None,
        successes: Optional[List[Dict[str, Any]]] = None,
        time_spent: float = 0.0,
        phase: SessionPhase = SessionPhase.EARLY_GAME,
        metrics: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SessionRecord:
        with self._lock:
            self._enforce_max_session_records()

            profile = self.get_profile(player_id)
            if profile is None:
                profile = self.create_profile(player_id)

            record = SessionRecord(
                player_id=player_id,
                session_id=session_id or f"session_{self._total_sessions_recorded + 1}",
                actions=list(actions) if actions else [],
                decisions=list(decisions) if decisions else [],
                failures=list(failures) if failures else [],
                successes=list(successes) if successes else [],
                time_spent=time_spent,
                phase=phase,
                metrics=metrics or {},
                metadata=metadata or {},
            )
            self._session_records[record.id] = record
            self._total_sessions_recorded += 1

            if player_id not in self._sessions_by_player:
                self._sessions_by_player[player_id] = []
            self._sessions_by_player[player_id].append(record.id)

            profile.session_count += 1
            profile.total_playtime += time_spent
            profile.updated_at = time.time()

            self._update_skill_estimates(player_id, record)
            self._update_playstyle(player_id)

            return record

    def get_player_sessions(self, player_id: str, limit: int = 50) -> List[SessionRecord]:
        with self._lock:
            record_ids = self._sessions_by_player.get(player_id, [])
            records = [
                self._session_records[rid]
                for rid in reversed(record_ids[-limit:])
                if rid in self._session_records
            ]
            return records

    # ------------------------------------------------------------------
    # Playstyle Classification
    # ------------------------------------------------------------------

    def classify_playstyle(self, player_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return None

            sessions = self.get_player_sessions(player_id, limit=50)
            if not sessions:
                return {"player_id": player_id, "playstyle": profile.playstyle.value, "confidence": 0.0}

            scores: Dict[str, float] = {}
            for playstyle, indicators in _PLAYSTYLE_INDICATORS.items():
                score = 0.0
                total_weight = 0.0
                for metric, weight in indicators.items():
                    metric_value = self._extract_metric(sessions, metric)
                    score += metric_value * weight
                    total_weight += weight
                if total_weight > 0:
                    scores[playstyle.value] = score / total_weight
                else:
                    scores[playstyle.value] = 0.0

            best_playstyle = max(scores, key=scores.get)
            best_score = scores[best_playstyle]

            profile.playstyle = PlaystyleType(best_playstyle)
            profile.updated_at = time.time()

            return {
                "player_id": player_id,
                "playstyle": best_playstyle,
                "confidence": round(best_score, 4),
                "all_scores": {k: round(v, 4) for k, v in scores.items()},
            }

    # ------------------------------------------------------------------
    # Skill Estimation
    # ------------------------------------------------------------------

    def estimate_skill(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return {"player_id": player_id, "error": "Profile not found"}

            sessions = self.get_player_sessions(player_id, limit=50)
            if not sessions:
                return {
                    "player_id": player_id,
                    "skill_ratings": profile.skill_ratings,
                    "average_skill": profile.get_average_skill(),
                }

            estimated: Dict[str, float] = {}

            reaction_score = self._estimate_reaction(sessions)
            estimated[SkillDimension.REACTION.value] = round(reaction_score, 4)

            strategy_score = self._estimate_strategy(sessions)
            estimated[SkillDimension.STRATEGY.value] = round(strategy_score, 4)

            precision_score = self._estimate_precision(sessions)
            estimated[SkillDimension.PRECISION.value] = round(precision_score, 4)

            adaptation_score = self._estimate_adaptation(sessions)
            estimated[SkillDimension.ADAPTATION.value] = round(adaptation_score, 4)

            persistence_score = self._estimate_persistence(sessions)
            estimated[SkillDimension.PERSISTENCE.value] = round(persistence_score, 4)

            for dim, value in estimated.items():
                previous = profile.skill_ratings.get(dim, self._DEFAULT_SKILL)
                profile.skill_ratings[dim] = previous + self._SKILL_LEARNING_RATE * (value - previous)
                profile.skill_ratings[dim] = max(0.0, min(1.0, profile.skill_ratings[dim]))

            profile.updated_at = time.time()

            return {
                "player_id": player_id,
                "skill_ratings": {k: round(v, 4) for k, v in profile.skill_ratings.items()},
                "average_skill": round(profile.get_average_skill(), 4),
                "session_count": len(sessions),
            }

    # ------------------------------------------------------------------
    # Behavior Prediction
    # ------------------------------------------------------------------

    def predict_behavior(
        self,
        player_id: str,
        context: Optional[Dict[str, Any]] = None,
        action_candidates: Optional[List[str]] = None,
    ) -> Optional[PlayerPrediction]:
        with self._lock:
            self._enforce_max_predictions()

            profile = self.get_profile(player_id)
            if profile is None:
                return None

            sessions = self.get_player_sessions(player_id, limit=20)
            if not sessions:
                return None

            action_counts: Dict[str, int] = {}
            action_results: Dict[str, List[str]] = {}

            for session in sessions:
                for action in session.actions:
                    at = action.get("action_type", "unknown")
                    action_counts[at] = action_counts.get(at, 0) + 1
                    result = action.get("result", "")
                    if at not in action_results:
                        action_results[at] = []
                    action_results[at].append(result)

            if not action_counts:
                return None

            total_actions = sum(action_counts.values())
            action_probs = {
                at: count / total_actions
                for at, count in action_counts.items()
            }

            candidates = action_candidates or list(action_probs.keys())
            ranked = sorted(
                [(a, action_probs.get(a, 0.0)) for a in candidates if a in action_probs],
                key=lambda x: x[1],
                reverse=True,
            )

            if not ranked:
                return None

            predicted = ranked[0]
            alternatives = [
                {"action": a, "probability": round(p, 4)}
                for a, p in ranked[1:6]
            ]

            prediction = PlayerPrediction(
                player_id=player_id,
                predicted_action=predicted[0],
                confidence=predicted[1],
                context=context or {},
                alternatives=alternatives,
            )
            self._predictions[prediction.id] = prediction
            self._total_predictions_made += 1

            if player_id not in self._predictions_by_player:
                self._predictions_by_player[player_id] = []
            self._predictions_by_player[player_id].append(prediction.id)

            return prediction

    # ------------------------------------------------------------------
    # Engagement Computation
    # ------------------------------------------------------------------

    def compute_engagement(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return {"player_id": player_id, "error": "Profile not found"}

            sessions = self.get_player_sessions(player_id, limit=self._ENGAGEMENT_WINDOW)
            if not sessions:
                return {
                    "player_id": player_id,
                    "engagement_level": EngagementLevel.NEUTRAL.value,
                    "engagement_score": 0.5,
                }

            success_rates = []
            action_rates = []
            failure_rates = []
            for session in sessions:
                success_rates.append(session.get_success_rate())
                action_rates.append(session.get_actions_per_minute())
                total = len(session.successes) + len(session.failures)
                if total > 0:
                    failure_rates.append(len(session.failures) / total)

            avg_success = sum(success_rates) / len(success_rates) if success_rates else 0.5
            avg_action_rate = sum(action_rates) / len(action_rates) if action_rates else 0.0
            avg_failure_rate = sum(failure_rates) / len(failure_rates) if failure_rates else 0.0

            if avg_success > 0.9 and avg_action_rate > 10:
                level = EngagementLevel.BORED
                score = 0.2
            elif avg_success < 0.3 and avg_failure_rate > 0.5:
                level = EngagementLevel.FRUSTRATED
                score = 0.3
            elif avg_success < 0.2:
                level = EngagementLevel.OVERWHELMED
                score = 0.1
            elif 0.4 <= avg_success <= 0.8 and avg_action_rate > 0:
                level = EngagementLevel.FLOW
                score = 0.85
            elif avg_success > 0.6:
                level = EngagementLevel.ENGAGED
                score = 0.65
            else:
                level = EngagementLevel.ENGAGED
                score = 0.5

            profile.record_engagement(level, score)

            return {
                "player_id": player_id,
                "engagement_level": level.value,
                "engagement_score": round(score, 4),
                "avg_success_rate": round(avg_success, 4),
                "avg_actions_per_minute": round(avg_action_rate, 2),
                "avg_failure_rate": round(avg_failure_rate, 4),
                "sessions_analyzed": len(sessions),
            }

    # ------------------------------------------------------------------
    # Difficulty Suggestion
    # ------------------------------------------------------------------

    def suggest_difficulty(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            profile = self.get_profile(player_id)
            if profile is None:
                return {"player_id": player_id, "error": "Profile not found"}

            engagement = self.compute_engagement(player_id)
            skill = self.estimate_skill(player_id)

            difficulty_id = self._difficulty_by_player.get(player_id)
            if difficulty_id is None:
                diff_profile = DifficultyProfile(
                    player_id=player_id,
                    current_tier=skill.get("average_skill", 0.5),
                )
                self._difficulty_profiles[diff_profile.id] = diff_profile
                self._difficulty_by_player[player_id] = diff_profile.id
            else:
                diff_profile = self._difficulty_profiles.get(difficulty_id)
                if diff_profile is None:
                    diff_profile = DifficultyProfile(
                        player_id=player_id,
                        current_tier=skill.get("average_skill", 0.5),
                    )
                    self._difficulty_profiles[diff_profile.id] = diff_profile
                    self._difficulty_by_player[player_id] = diff_profile.id

            eng_level = engagement.get("engagement_level", "engaged")
            suggested_delta = 0.0

            if eng_level == EngagementLevel.BORED.value:
                suggested_delta = 0.08
            elif eng_level == EngagementLevel.FLOW.value:
                suggested_delta = 0.02
            elif eng_level == EngagementLevel.FRUSTRATED.value:
                suggested_delta = -0.06
            elif eng_level == EngagementLevel.OVERWHELMED.value:
                suggested_delta = -0.10
            elif eng_level == EngagementLevel.ENGAGED.value:
                suggested_delta = 0.02

            diff_profile.adjust_tier(suggested_delta, f"engagement_{eng_level}")

            return {
                "player_id": player_id,
                "current_tier": round(diff_profile.current_tier, 4),
                "suggested_delta": round(suggested_delta, 4),
                "engagement_level": eng_level,
                "average_skill": skill.get("average_skill", 0.5),
                "target_engagement": diff_profile.target_engagement.value,
            }

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    def generate_insights(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            self._total_insights_generated += 1

            profile = self.get_profile(player_id)
            if profile is None:
                return {"player_id": player_id, "error": "Profile not found"}

            playstyle = self.classify_playstyle(player_id)
            skill = self.estimate_skill(player_id)
            engagement = self.compute_engagement(player_id)

            sessions = self.get_player_sessions(player_id, limit=100)

            insights: List[str] = []

            if playstyle:
                ps = playstyle.get("playstyle", "unknown")
                insights.append(f"Player exhibits a {ps} playstyle with {playstyle.get('confidence', 0):.0%} confidence.")

            avg_skill = skill.get("average_skill", 0.5)
            if avg_skill > 0.7:
                insights.append("Player demonstrates high overall skill across all dimensions.")
            elif avg_skill < 0.3:
                insights.append("Player may benefit from additional tutorial support.")

            eng_level = engagement.get("engagement_level", "neutral")
            if eng_level == EngagementLevel.FLOW.value:
                insights.append("Player is currently in an optimal flow state.")
            elif eng_level == EngagementLevel.BORED.value:
                insights.append("Player appears bored — consider increasing difficulty or introducing new mechanics.")
            elif eng_level == EngagementLevel.FRUSTRATED.value:
                insights.append("Player shows signs of frustration — consider reducing difficulty or providing hints.")

            if sessions:
                latest_success = sessions[-1].get_success_rate() if sessions else 0.5
                if latest_success > 0.8:
                    insights.append("Recent performance is strong — player is mastering current content.")
                elif latest_success < 0.3:
                    insights.append("Recent performance is struggling — player may need assistance.")

            if profile.frustration_triggers:
                triggers = ", ".join(profile.frustration_triggers[:3])
                insights.append(f"Identified frustration triggers: {triggers}")

            return {
                "player_id": player_id,
                "insight_count": len(insights),
                "insights": insights,
                "playstyle": playstyle,
                "skill": skill,
                "engagement": engagement,
                "sessions_analyzed": len(sessions),
                "total_playtime_minutes": round(profile.total_playtime / 60.0, 2),
            }

    # ------------------------------------------------------------------
    # Statistics
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            playstyle_dist: Dict[str, int] = {}
            for profile in self._profiles.values():
                ps = profile.playstyle.value
                playstyle_dist[ps] = playstyle_dist.get(ps, 0) + 1

            avg_skills: Dict[str, float] = {}
            skill_counts: Dict[str, int] = {}
            for profile in self._profiles.values():
                for dim, value in profile.skill_ratings.items():
                    avg_skills[dim] = avg_skills.get(dim, 0.0) + value
                    skill_counts[dim] = skill_counts.get(dim, 0) + 1
            for dim in avg_skills:
                if skill_counts[dim] > 0:
                    avg_skills[dim] = round(avg_skills[dim] / skill_counts[dim], 4)

            total_successes = 0
            total_failures = 0
            for record in self._session_records.values():
                total_successes += len(record.successes)
                total_failures += len(record.failures)

            return {
                "total_profiles_created": self._total_profiles_created,
                "total_profiles_stored": len(self._profiles),
                "total_sessions_recorded": self._total_sessions_recorded,
                "total_sessions_stored": len(self._session_records),
                "total_predictions_made": self._total_predictions_made,
                "total_insights_generated": self._total_insights_generated,
                "total_difficulty_profiles": len(self._difficulty_profiles),
                "playstyle_distribution": playstyle_dist,
                "average_skills": avg_skills,
                "total_successes": total_successes,
                "total_failures": total_failures,
                "global_success_rate": round(
                    total_successes / (total_successes + total_failures), 4
                ) if (total_successes + total_failures) > 0 else 0.0,
                "max_profiles": self._MAX_PROFILES,
                "max_session_records": self._MAX_SESSION_RECORDS,
            }

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._profiles_by_player.clear()
            self._session_records.clear()
            self._sessions_by_player.clear()
            self._difficulty_profiles.clear()
            self._difficulty_by_player.clear()
            self._predictions.clear()
            self._predictions_by_player.clear()
            self._total_profiles_created = 0
            self._total_sessions_recorded = 0
            self._total_predictions_made = 0
            self._total_insights_generated = 0

    # ------------------------------------------------------------------
    # Internal: Skill Estimation
    # ------------------------------------------------------------------

    def _update_skill_estimates(self, player_id: str, record: SessionRecord) -> None:
        profile = self.get_profile(player_id)
        if profile is None:
            return

        success_rate = record.get_success_rate()
        if len(record.successes) + len(record.failures) < 3:
            return

        previous_reaction = profile.skill_ratings.get(SkillDimension.REACTION.value, self._DEFAULT_SKILL)
        apm = record.get_actions_per_minute()
        normalized_apm = min(1.0, apm / 60.0)
        profile.skill_ratings[SkillDimension.REACTION.value] = round(
            previous_reaction + self._SKILL_LEARNING_RATE * (normalized_apm - previous_reaction), 4
        )

        previous_precision = profile.skill_ratings.get(SkillDimension.PRECISION.value, self._DEFAULT_SKILL)
        profile.skill_ratings[SkillDimension.PRECISION.value] = round(
            previous_precision + self._SKILL_LEARNING_RATE * (success_rate - previous_precision), 4
        )

        profile.updated_at = time.time()

    def _update_playstyle(self, player_id: str) -> None:
        self.classify_playstyle(player_id)

    def _extract_metric(self, sessions: List[SessionRecord], metric: str) -> float:
        if metric == "attack_frequency":
            counts = [
                sum(1 for a in s.actions if "attack" in a.get("action_type", "").lower())
                for s in sessions
            ]
            return min(1.0, sum(counts) / max(1, len(sessions) * 10))
        if metric == "damage_dealt":
            return min(1.0, sum(s.metrics.get("damage", 0) for s in sessions) / max(1, len(sessions) * 100))
        if metric == "risk_taking":
            return min(1.0, sum(1 for s in sessions if s.metrics.get("risky_actions", 0) > 3) / max(1, len(sessions)))
        if metric == "combat_engagement":
            return min(1.0, sum(s.metrics.get("combat_time", 0) for s in sessions) / max(1, sum(s.time_spent for s in sessions)))
        if metric == "area_explored":
            return min(1.0, sum(s.metrics.get("exploration", 0) for s in sessions) / max(1, len(sessions) * 100))
        if metric == "secrets_found":
            return min(1.0, sum(s.metrics.get("secrets", 0) for s in sessions) / max(1, len(sessions) * 5))
        if metric == "movement_distance":
            return min(1.0, sum(s.metrics.get("distance", 0) for s in sessions) / max(1, len(sessions) * 1000))
        if metric == "non_critical_path":
            return min(1.0, sum(s.metrics.get("off_path_time", 0) for s in sessions) / max(1, sum(s.time_spent for s in sessions)))
        if metric == "objectives_completed":
            return min(1.0, sum(s.metrics.get("objectives", 0) for s in sessions) / max(1, len(sessions) * 5))
        if metric == "collectibles_found":
            return min(1.0, sum(s.metrics.get("collectibles", 0) for s in sessions) / max(1, len(sessions) * 10))
        if metric == "side_quests":
            return min(1.0, sum(s.metrics.get("side_quests", 0) for s in sessions) / max(1, len(sessions) * 3))
        if metric == "thoroughness":
            return min(1.0, sum(s.metrics.get("completion", 0) for s in sessions) / max(1, len(sessions) * 100))
        if metric == "completion_speed":
            return min(1.0, 1.0 - (sum(s.time_spent for s in sessions) / max(1, len(sessions) * 3600)))
        if metric == "efficiency":
            return min(1.0, sum(s.get_success_rate() for s in sessions) / max(1, len(sessions)))
        if metric == "skip_rate":
            return min(1.0, sum(s.metrics.get("skipped", 0) for s in sessions) / max(1, len(sessions) * 5))
        if metric == "movement_optimization":
            return min(1.0, sum(s.metrics.get("optimization", 0) for s in sessions) / max(1, len(sessions) * 100))
        if metric == "interactions":
            return min(1.0, sum(s.metrics.get("interactions", 0) for s in sessions) / max(1, len(sessions) * 20))
        if metric == "communication":
            return min(1.0, sum(s.metrics.get("messages", 0) for s in sessions) / max(1, len(sessions) * 10))
        if metric == "cooperation":
            return min(1.0, sum(s.metrics.get("coop_actions", 0) for s in sessions) / max(1, len(sessions) * 10))
        if metric == "social_events":
            return min(1.0, sum(s.metrics.get("social_events", 0) for s in sessions) / max(1, len(sessions) * 10))
        if metric == "planning_time":
            return min(1.0, sum(s.metrics.get("planning_time", 0) for s in sessions) / max(1, sum(s.time_spent for s in sessions)))
        if metric == "resource_efficiency":
            return min(1.0, sum(s.metrics.get("efficiency", 0) for s in sessions) / max(1, len(sessions) * 100))
        if metric == "tactical_decisions":
            return min(1.0, sum(1 for s in sessions if s.metrics.get("tactical_actions", 0) > 2) / max(1, len(sessions)))
        if metric == "win_rate":
            return min(1.0, sum(s.get_success_rate() for s in sessions) / max(1, len(sessions)))
        return 0.5

    def _estimate_reaction(self, sessions: List[SessionRecord]) -> float:
        apms = [s.get_actions_per_minute() for s in sessions if s.time_spent > 0]
        if not apms:
            return self._DEFAULT_SKILL
        avg_apm = sum(apms) / len(apms)
        return min(1.0, avg_apm / 30.0)

    def _estimate_strategy(self, sessions: List[SessionRecord]) -> float:
        decision_qualities = [
            d.get("quality", 0.5)
            for s in sessions
            for d in s.decisions
        ]
        if not decision_qualities:
            return self._DEFAULT_SKILL
        return sum(decision_qualities) / len(decision_qualities)

    def _estimate_precision(self, sessions: List[SessionRecord]) -> float:
        rates = [s.get_success_rate() for s in sessions]
        if not rates:
            return self._DEFAULT_SKILL
        return sum(rates) / len(rates)

    def _estimate_adaptation(self, sessions: List[SessionRecord]) -> float:
        if len(sessions) < 2:
            return self._DEFAULT_SKILL
        rates = [s.get_success_rate() for s in sessions]
        improvements = 0
        for i in range(1, len(rates)):
            if rates[i] > rates[i - 1]:
                improvements += 1
        return min(1.0, improvements / (len(rates) - 1) + 0.3)

    def _estimate_persistence(self, sessions: List[SessionRecord]) -> float:
        if not sessions:
            return self._DEFAULT_SKILL
        avg_time = sum(s.time_spent for s in sessions) / len(sessions)
        avg_failures = sum(len(s.failures) for s in sessions) / len(sessions)
        persistence = min(1.0, avg_time / 3600.0) * 0.5 + min(1.0, avg_failures / 20.0) * 0.5
        return persistence

    # ------------------------------------------------------------------
    # Internal: Limit Enforcement
    # ------------------------------------------------------------------

    def _enforce_max_profiles(self) -> None:
        if len(self._profiles) >= self._MAX_PROFILES:
            sorted_profiles = sorted(
                self._profiles.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._profiles) - self._MAX_PROFILES + 1
            for pid, profile in sorted_profiles[:overflow]:
                self._profiles.pop(pid, None)
                if self._profiles_by_player.get(profile.player_id) == pid:
                    del self._profiles_by_player[profile.player_id]

    def _enforce_max_session_records(self) -> None:
        if len(self._session_records) >= self._MAX_SESSION_RECORDS:
            sorted_records = sorted(
                self._session_records.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._session_records) - self._MAX_SESSION_RECORDS + 1
            for rid, record in sorted_records[:overflow]:
                self._session_records.pop(rid, None)
                player_sessions = self._sessions_by_player.get(record.player_id, [])
                if rid in player_sessions:
                    player_sessions.remove(rid)

    def _enforce_max_predictions(self) -> None:
        if len(self._predictions) >= self._MAX_PREDICTIONS:
            sorted_preds = sorted(
                self._predictions.items(),
                key=lambda item: item[1].created_at,
            )
            overflow = len(self._predictions) - self._MAX_PREDICTIONS + 1
            for pid, pred in sorted_preds[:overflow]:
                self._predictions.pop(pid, None)
                player_preds = self._predictions_by_player.get(pred.player_id, [])
                if pid in player_preds:
                    player_preds.remove(pid)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_player_modeler() -> PlayerModelerEngine:
    """Return the singleton PlayerModelerEngine instance."""
    return PlayerModelerEngine.get_instance()