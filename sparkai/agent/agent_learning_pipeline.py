"""
SparkLabs Agent - Learning Pipeline

An observation-driven learning system for the AI-native game engine that
monitors player behavior, discovers patterns, and generates actionable
insights to continuously refine game design.

Architecture:
  LearningPipeline (singleton)
    |-- PlayerObservation (atomic behavioral data point)
    |-- LearnedInsight (derived knowledge with confidence)
    |-- PlayerProfile (aggregated player model)
    |-- LearningModel (trained prediction capability)

Core Capabilities:
  - Session lifecycle management (start, record, end)
  - Pattern analysis (repeated action sequences, failure points, preferred paths)
  - Anomaly detection (unusual behavior, exploits, outlier performance)
  - Trend identification (engagement shifts, difficulty evolution, speed changes)
  - Recommendation generation (design changes based on data)
  - Player profiling (skill level, play style, preferences)
  - Retention/churn prediction (engagement patterns, session frequency)
  - Player segmentation (casual, core, hardcore, explorer, achiever)
"""

from __future__ import annotations

import json
import math
import random
import statistics
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

_time_module = time


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ObservationType(Enum):
    PLAYER_ACTION = "player_action"
    GAME_EVENT = "game_event"
    PERFORMANCE = "performance"
    INTERACTION = "interaction"
    PROGRESSION = "progression"
    ERROR = "error"
    ENGAGEMENT = "engagement"
    RETENTION = "retention"


class InsightType(Enum):
    PATTERN = "pattern"
    ANOMALY = "anomaly"
    TREND = "trend"
    CORRELATION = "correlation"
    PREDICTION = "prediction"
    RECOMMENDATION = "recommendation"


class ConfidenceLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PlayerObservation:
    obs_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    session_id: str = ""
    obs_type: ObservationType = ObservationType.GAME_EVENT
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "obs_id": self.obs_id,
            "player_id": self.player_id,
            "session_id": self.session_id,
            "obs_type": self.obs_type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "context": self.context,
        }


@dataclass
class LearnedInsight:
    insight_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    insight_type: InsightType = InsightType.PATTERN
    title: str = ""
    description: str = ""
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    evidence: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    validated: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "insight_id": self.insight_id,
            "insight_type": self.insight_type.value,
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence.value,
            "evidence": self.evidence,
            "recommendations": self.recommendations,
            "generated_at": self.generated_at,
            "validated": self.validated,
        }


@dataclass
class PlayerProfile:
    profile_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    player_id: str = ""
    total_sessions: int = 0
    total_playtime: float = 0.0
    actions_per_minute: float = 0.0
    preferred_actions: Dict[str, int] = field(default_factory=dict)
    skill_level: float = 0.5
    frustration_points: List[str] = field(default_factory=list)
    engagement_score: float = 0.5
    retention_probability: float = 0.5
    segments: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "player_id": self.player_id,
            "total_sessions": self.total_sessions,
            "total_playtime": round(self.total_playtime, 1),
            "actions_per_minute": round(self.actions_per_minute, 2),
            "preferred_actions": self.preferred_actions,
            "skill_level": round(self.skill_level, 3),
            "frustration_points": self.frustration_points,
            "engagement_score": round(self.engagement_score, 3),
            "retention_probability": round(self.retention_probability, 3),
            "segments": self.segments,
        }


@dataclass
class LearningModel:
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    insight_type: InsightType = InsightType.PATTERN
    training_samples: int = 0
    accuracy: float = 0.0
    last_trained: float = 0.0
    features: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "name": self.name,
            "insight_type": self.insight_type.value,
            "training_samples": self.training_samples,
            "accuracy": round(self.accuracy, 4),
            "last_trained": self.last_trained,
            "features": self.features,
        }


# ---------------------------------------------------------------------------
# Learning Pipeline
# ---------------------------------------------------------------------------

class LearningPipeline:
    """
    Observation-driven learning system for continuous game design improvement.

    Collects player observations, analyzes behavioral patterns, detects
    anomalies, identifies trends, and generates design recommendations.
    """

    _instance: Optional["LearningPipeline"] = None
    _lock = threading.RLock()

    # Session outcome taxonomy
    _SESSION_OUTCOMES = frozenset({
        "completed", "abandoned", "frustrated", "satisfied",
        "timeout", "disconnected", "error",
    })

    # Player segment archetypes with characteristic thresholds
    _SEGMENT_PROFILES: Dict[str, Dict[str, Tuple[float, float]]] = {
        "casual": {
            "sessions_per_week": (0.0, 3.0),
            "avg_session_minutes": (0.0, 30.0),
            "skill_level": (0.0, 0.4),
            "exploration_ratio": (0.0, 0.3),
        },
        "core": {
            "sessions_per_week": (2.0, 6.0),
            "avg_session_minutes": (20.0, 90.0),
            "skill_level": (0.3, 0.7),
            "exploration_ratio": (0.2, 0.6),
        },
        "hardcore": {
            "sessions_per_week": (5.0, 20.0),
            "avg_session_minutes": (60.0, 300.0),
            "skill_level": (0.6, 1.0),
            "exploration_ratio": (0.4, 1.0),
        },
        "explorer": {
            "sessions_per_week": (2.0, 8.0),
            "avg_session_minutes": (30.0, 120.0),
            "skill_level": (0.2, 0.6),
            "exploration_ratio": (0.7, 1.0),
        },
        "achiever": {
            "sessions_per_week": (4.0, 12.0),
            "avg_session_minutes": (40.0, 150.0),
            "skill_level": (0.5, 0.9),
            "exploration_ratio": (0.3, 0.7),
        },
    }

    def __init__(self) -> None:
        # Active sessions: session_id -> metadata dict
        self._sessions: Dict[str, Dict[str, Any]] = {}
        # Observations: session_id -> list of PlayerObservation
        self._observations: Dict[str, List[PlayerObservation]] = defaultdict(list)
        # Cumulative observations per player
        self._player_observations: Dict[str, List[PlayerObservation]] = defaultdict(list)
        # Session history: player_id -> list of session summaries
        self._session_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # Generated insights: player_id -> list of LearnedInsight
        self._insights: Dict[str, List[LearnedInsight]] = defaultdict(list)
        # Global insights (not player-specific)
        self._global_insights: List[LearnedInsight] = []
        # Player profiles
        self._profiles: Dict[str, PlayerProfile] = {}
        # Trained models
        self._models: List[LearningModel] = []
        # Action sequence tracking for pattern analysis
        self._action_sequences: Dict[str, List[Tuple[str, float]]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> "LearningPipeline":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Session Lifecycle ----

    def start_session(self, player_id: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Begin a new observation session for a player.

        Returns the session_id that should be used for subsequent
        record_observation and end_session calls.
        """
        with self._lock:
            session_id = uuid.uuid4().hex[:12]
            now = _time_module.time()

            self._sessions[session_id] = {
                "player_id": player_id,
                "started_at": now,
                "active": True,
                "metadata": metadata or {},
                "observation_count": 0,
                "game_id": (metadata or {}).get("game_id", ""),
            }
            return session_id

    def record_observation(
        self,
        session_id: str,
        player_id: str,
        obs_type: ObservationType,
        data: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> PlayerObservation:
        """
        Record a single player behavioral observation within an active session.
        """
        if not isinstance(obs_type, ObservationType):
            raise ValueError(f"Invalid observation type: {obs_type}")

        obs = PlayerObservation(
            player_id=player_id,
            session_id=session_id,
            obs_type=obs_type,
            data=data,
            timestamp=_time_module.time(),
            context=context or {},
        )

        with self._lock:
            self._observations[session_id].append(obs)
            self._player_observations[player_id].append(obs)

            if session_id in self._sessions:
                self._sessions[session_id]["observation_count"] += 1

            # Track action sequences for pattern analysis
            if obs_type == ObservationType.PLAYER_ACTION:
                action_name = data.get("action", data.get("name", "unknown"))
                self._action_sequences[player_id].append((action_name, obs.timestamp))

        return obs

    def end_session(
        self,
        session_id: str,
        player_id: str,
        outcome: str,
    ) -> Dict[str, Any]:
        """
        Close an active session and produce a session summary.
        """
        with self._lock:
            now = _time_module.time()
            session = self._sessions.get(session_id)

            if session is None:
                raise ValueError(f"Unknown session: {session_id}")

            session["active"] = False
            session["ended_at"] = now
            session["outcome"] = outcome
            duration = now - session.get("started_at", now)

            obs_list = self._observations.get(session_id, [])
            action_obs = [o for o in obs_list if o.obs_type == ObservationType.PLAYER_ACTION]
            error_obs = [o for o in obs_list if o.obs_type == ObservationType.ERROR]
            engagement_obs = [o for o in obs_list if o.obs_type == ObservationType.ENGAGEMENT]

            summary = {
                "session_id": session_id,
                "player_id": player_id,
                "duration_seconds": round(duration, 2),
                "observation_count": len(obs_list),
                "action_count": len(action_obs),
                "error_count": len(error_obs),
                "engagement_signals": len(engagement_obs),
                "outcome": outcome,
                "started_at": session["started_at"],
                "ended_at": now,
                "game_id": session.get("game_id", ""),
            }

            self._session_history[player_id].append(summary)
            return summary

    # ---- Pattern Analysis ----

    def analyze_patterns(self, player_id: str) -> List[LearnedInsight]:
        """
        Analyze player observations to discover repeated behavioral patterns.

        Looks for:
        - Repeated action sequences (N-gram analysis on action streams)
        - Common failure points (clusters of errors at specific game states)
        - Preferred paths (frequently observed progression sequences)
        """
        insights: List[LearnedInsight] = []
        obs_list = self._player_observations.get(player_id, [])
        sessions = self._session_history.get(player_id, [])

        if len(obs_list) < 3:
            return insights

        # Pattern 1: Analyze action sequences for recurring N-grams
        actions = self._action_sequences.get(player_id, [])
        if len(actions) >= 5:
            action_names = [a[0] for a in actions]
            bigrams: Dict[Tuple[str, str], int] = {}
            for i in range(len(action_names) - 1):
                bg = (action_names[i], action_names[i + 1])
                bigrams[bg] = bigrams.get(bg, 0) + 1

            frequent_bigrams = sorted(bigrams.items(), key=lambda x: -x[1])[:5]
            if frequent_bigrams and frequent_bigrams[0][1] >= 2:
                top_bigrams_str = ", ".join(
                    f"{bg[0]}→{bg[1]}" for bg, cnt in frequent_bigrams if cnt >= 2
                )
                if top_bigrams_str:
                    insights.append(LearnedInsight(
                        insight_type=InsightType.PATTERN,
                        title="Recurring Action Sequence",
                        description=f"Player repeatedly executes sequences: {top_bigrams_str}",
                        confidence=ConfidenceLevel.HIGH if frequent_bigrams[0][1] >= 4
                        else ConfidenceLevel.MEDIUM,
                        evidence=[
                            f"Bigram '{bg[0]}→{bg[1]}' observed {cnt} times"
                            for bg, cnt in frequent_bigrams if cnt >= 2
                        ],
                        recommendations=["Consider optimizing the flow between these frequent actions"],
                    ))

        # Pattern 2: Identify common failure points from error observations
        error_obs = [o for o in obs_list if o.obs_type == ObservationType.ERROR]
        if error_obs:
            failure_locations: Dict[str, int] = {}
            for eo in error_obs:
                loc = eo.data.get("location", eo.data.get("context", "unknown"))
                failure_locations[loc] = failure_locations.get(loc, 0) + 1

            top_failures = sorted(failure_locations.items(), key=lambda x: -x[1])[:3]
            if top_failures:
                total_errors = len(error_obs)
                failures_desc = "; ".join(
                    f"{loc} ({cnt} errors, {100*cnt/total_errors:.0f}%)"
                    for loc, cnt in top_failures
                )
                insights.append(LearnedInsight(
                    insight_type=InsightType.PATTERN,
                    title="Common Failure Points",
                    description=f"Player encounters repeated errors at: {failures_desc}",
                    confidence=ConfidenceLevel.HIGH if total_errors >= 10
                    else ConfidenceLevel.MEDIUM,
                    evidence=[
                        f"Location '{loc}' caused {cnt} errors out of {total_errors} total"
                        for loc, cnt in top_failures
                    ],
                    recommendations=[
                        "Review difficulty balance at identified failure points",
                        "Add clearer guidance or tutorials at these locations",
                    ],
                ))

        # Pattern 3: Preferred paths from progression observations
        progression_obs = [
            o for o in obs_list if o.obs_type == ObservationType.PROGRESSION
        ]
        if len(progression_obs) >= 3:
            path_counts: Dict[str, int] = {}
            for po in progression_obs:
                path = po.data.get("path", po.data.get("route", "unknown"))
                path_counts[path] = path_counts.get(path, 0) + 1

            top_paths = sorted(path_counts.items(), key=lambda x: -x[1])[:3]
            if top_paths:
                insights.append(LearnedInsight(
                    insight_type=InsightType.PATTERN,
                    title="Preferred Progression Paths",
                    description=f"Player favors paths: {', '.join(p for p, _ in top_paths)}",
                    confidence=ConfidenceLevel.MEDIUM,
                    evidence=[
                        f"Path '{p}' taken {c} times" for p, c in top_paths
                    ],
                    recommendations=["Ensure less-traveled paths have sufficient reward incentives"],
                ))

        # Pattern 4: Session consistency patterns
        if len(sessions) >= 3:
            durations = [s.get("duration_seconds", 0) for s in sessions]
            avg_duration = statistics.mean(durations) if durations else 0
            std_duration = statistics.stdev(durations) if len(durations) >= 2 else 0

            if std_duration > 0 and avg_duration > 0:
                cv = std_duration / avg_duration
                if cv < 0.3 and avg_duration > 60:
                    insights.append(LearnedInsight(
                        insight_type=InsightType.PATTERN,
                        title="Consistent Session Duration",
                        description=f"Player sessions are consistently around {avg_duration/60:.1f} minutes (CV={cv:.2f})",
                        confidence=ConfidenceLevel.HIGH,
                        evidence=[f"Average duration: {avg_duration:.0f}s, stddev: {std_duration:.0f}s"],
                        recommendations=["Match content pacing to this natural session length"],
                    ))

        # Store and return
        with self._lock:
            self._insights[player_id].extend(insights)

        return insights

    # ---- Anomaly Detection ----

    def detect_anomalies(self, player_id: str) -> List[LearnedInsight]:
        """
        Detect unusual behavior patterns, potential exploits, and outlier
        performance metrics from player observations.
        """
        insights: List[LearnedInsight] = []
        obs_list = self._player_observations.get(player_id, [])
        sessions = self._session_history.get(player_id, [])

        if len(obs_list) < 5 or len(sessions) < 2:
            return insights

        # Anomaly 1: Unusually high actions per minute (potential bot/exploit)
        for session in sessions:
            duration = session.get("duration_seconds", 0)
            action_count = session.get("action_count", 0)
            if duration > 10 and action_count > 0:
                apm = action_count / (duration / 60.0)
                if apm > 300:
                    insights.append(LearnedInsight(
                        insight_type=InsightType.ANOMALY,
                        title="Suspicious Action Rate",
                        description=f"Session {session['session_id']} shows {apm:.0f} APM — potential automation",
                        confidence=ConfidenceLevel.HIGH if apm > 600 else ConfidenceLevel.MEDIUM,
                        evidence=[
                            f"Actions: {action_count} in {duration/60:.1f} minutes",
                            f"Typical human APM range: 30-200",
                        ],
                        recommendations=["Investigate for botting or macro usage"],
                    ))

        # Anomaly 2: Outlier performance metrics
        performance_obs = [o for o in obs_list if o.obs_type == ObservationType.PERFORMANCE]
        if performance_obs:
            scores = [
                o.data.get("score", o.data.get("value", 0))
                for o in performance_obs
                if isinstance(o.data.get("score", o.data.get("value")), (int, float))
            ]
            if len(scores) >= 5:
                mean_score = statistics.mean(scores)
                std_score = statistics.stdev(scores) if len(scores) >= 2 else 1.0
                if std_score > 0:
                    for i, s in enumerate(scores):
                        z = abs(s - mean_score) / std_score
                        if z > 3.0:
                            insights.append(LearnedInsight(
                                insight_type=InsightType.ANOMALY,
                                title="Outlier Performance Event",
                                description=f"Performance score {s} deviates {z:.1f} standard deviations from mean {mean_score:.1f}",
                                confidence=ConfidenceLevel.HIGH if z > 4 else ConfidenceLevel.MEDIUM,
                                evidence=[
                                    f"Score: {s}, Mean: {mean_score:.1f}, StdDev: {std_score:.1f}",
                                    f"Z-score: {z:.2f}",
                                ],
                                recommendations=["Check for exploits or game bugs at the time of this event"],
                            ))
                            break  # Report only the most extreme outlier

        # Anomaly 3: Unusual error spikes
        session_error_counts = [
            (s["session_id"], s.get("error_count", 0))
            for s in sessions
        ]
        if len(session_error_counts) >= 3:
            error_counts = [c for _, c in session_error_counts]
            mean_err = statistics.mean(error_counts)
            std_err = statistics.stdev(error_counts) if len(error_counts) >= 2 else 1.0
            for sid, cnt in session_error_counts:
                if std_err > 0 and cnt > mean_err + 3 * std_err:
                    insights.append(LearnedInsight(
                        insight_type=InsightType.ANOMALY,
                        title="Error Spike Detected",
                        description=f"Session {sid} had {cnt} errors vs. average of {mean_err:.1f}",
                        confidence=ConfidenceLevel.HIGH,
                        evidence=[f"Error count {cnt} exceeds mean+3σ threshold of {mean_err + 3*std_err:.1f}"],
                        recommendations=["Review game stability during this session"],
                    ))

        # Anomaly 4: Sudden skill change
        if len(sessions) >= 4:
            recent_sessions = sessions[-3:]
            older_sessions = sessions[:-3] if len(sessions) > 3 else sessions[:1]
            recent_errors = sum(s.get("error_count", 0) for s in recent_sessions)
            older_errors = sum(s.get("error_count", 0) for s in older_sessions)
            if older_errors > 0 and recent_errors / max(1, older_errors) < 0.2:
                insights.append(LearnedInsight(
                    insight_type=InsightType.ANOMALY,
                    title="Sudden Skill Improvement",
                    description="Dramatic drop in error rate suggests skill spike or changed play conditions",
                    confidence=ConfidenceLevel.MEDIUM,
                    evidence=[
                        f"Recent session errors: {recent_errors}",
                        f"Earlier session errors: {older_errors}",
                    ],
                    recommendations=["Verify that difficulty hasn't unintentionally decreased"],
                ))

        with self._lock:
            self._insights[player_id].extend(insights)

        return insights

    # ---- Trend Identification ----

    def identify_trends(self, game_id: str) -> List[LearnedInsight]:
        """
        Identify macro-level trends across all players for a given game.

        Analyzes rising/falling engagement, difficulty evolution, and
        progression speed changes over time.
        """
        insights: List[LearnedInsight] = []
        all_observations: Dict[str, List[PlayerObservation]] = {}

        with self._lock:
            for pid, obs_list in self._player_observations.items():
                # Check if any session for this player is in the target game
                relevant = False
                for sid, session in self._sessions.items():
                    if session.get("game_id") == game_id and session.get("player_id") == pid:
                        relevant = True
                        break
                if relevant or not game_id:
                    all_observations.setdefault(pid, []).extend(obs_list)

        if not all_observations:
            return insights

        # Trend 1: Engagement trajectory over time
        engagement_by_day: Dict[str, List[float]] = defaultdict(list)
        for obs_list in all_observations.values():
            for o in obs_list:
                if o.obs_type == ObservationType.ENGAGEMENT:
                    day = _time_module.strftime("%Y-%m-%d", _time_module.localtime(o.timestamp))
                    val = o.data.get("score", o.data.get("value", 0.5))
                    if isinstance(val, (int, float)):
                        engagement_by_day[day].append(val)

        if len(engagement_by_day) >= 3:
            sorted_days = sorted(engagement_by_day.keys())
            daily_avgs = [
                statistics.mean(engagement_by_day[d]) for d in sorted_days
            ]
            if len(daily_avgs) >= 3:
                first_half = statistics.mean(daily_avgs[: len(daily_avgs) // 2])
                second_half = statistics.mean(daily_avgs[len(daily_avgs) // 2:])

                if first_half > 0:
                    change_pct = (second_half - first_half) / first_half * 100
                    if abs(change_pct) > 10:
                        direction = "rising" if change_pct > 0 else "falling"
                        severity = abs(change_pct)
                        insights.append(LearnedInsight(
                            insight_type=InsightType.TREND,
                            title=f"{direction.capitalize()} Engagement Trend",
                            description=f"Player engagement is {direction} ({change_pct:+.1f}% over observed period)",
                            confidence=ConfidenceLevel.HIGH if severity > 25
                            else ConfidenceLevel.MEDIUM,
                            evidence=[
                                f"Early average engagement: {first_half:.3f}",
                                f"Recent average engagement: {second_half:.3f}",
                                f"Days analyzed: {len(sorted_days)}",
                            ],
                            recommendations=[
                                "Investigate recent content updates for engagement impact"
                                if change_pct < -10
                                else "Identify what is driving engagement improvements",
                            ],
                        ))

        # Trend 2: Difficulty trend from error rates
        error_rates_by_day: Dict[str, Tuple[int, int]] = {}
        for obs_list in all_observations.values():
            day_buckets: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 0))
            for o in obs_list:
                day = _time_module.strftime("%Y-%m-%d", _time_module.localtime(o.timestamp))
                total, errors = day_buckets[day]
                day_buckets[day] = (total + 1, errors + (1 if o.obs_type == ObservationType.ERROR else 0))
            for day, (total, errors) in day_buckets.items():
                prev_total, prev_errors = error_rates_by_day.get(day, (0, 0))
                error_rates_by_day[day] = (prev_total + total, prev_errors + errors)

        if len(error_rates_by_day) >= 3:
            sorted_days = sorted(error_rates_by_day.keys())
            rates = [
                error_rates_by_day[d][1] / max(1, error_rates_by_day[d][0])
                for d in sorted_days
            ]
            if len(rates) >= 3:
                early_rate = statistics.mean(rates[: len(rates) // 2])
                late_rate = statistics.mean(rates[len(rates) // 2:])
                if early_rate > 0 and abs(late_rate - early_rate) / early_rate > 0.3:
                    direction = "increasing" if late_rate > early_rate else "decreasing"
                    insights.append(LearnedInsight(
                        insight_type=InsightType.TREND,
                        title=f"{direction.capitalize()} Error Rate Trend",
                        description=f"Error rate is {direction} from {early_rate:.1%} to {late_rate:.1%}",
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence=[
                            f"Early average error rate: {early_rate:.1%}",
                            f"Recent average error rate: {late_rate:.1%}",
                        ],
                        recommendations=[
                            "Game difficulty may be increasing — review recent changes"
                            if late_rate > early_rate
                            else "Players are adapting well — consider gradual difficulty increase",
                        ],
                    ))

        # Trend 3: Progression speed changes
        progression_times: Dict[str, List[float]] = defaultdict(list)
        for obs_list in all_observations.values():
            for o in obs_list:
                if o.obs_type == ObservationType.PROGRESSION:
                    day = _time_module.strftime("%Y-%m-%d", _time_module.localtime(o.timestamp))
                    prog_time = o.data.get("time_to_complete", o.data.get("duration"))
                    if isinstance(prog_time, (int, float)) and prog_time > 0:
                        progression_times[day].append(prog_time)

        if len(progression_times) >= 3:
            sorted_days = sorted(progression_times.keys())
            daily_medians = [
                statistics.median(progression_times[d]) for d in sorted_days
            ]
            if len(daily_medians) >= 3:
                first_half = statistics.mean(daily_medians[: len(daily_medians) // 2])
                second_half = statistics.mean(daily_medians[len(daily_medians) // 2:])
                if first_half > 0 and abs(second_half - first_half) / first_half > 0.2:
                    direction = "slower" if second_half > first_half else "faster"
                    insights.append(LearnedInsight(
                        insight_type=InsightType.TREND,
                        title="Progression Speed Shift",
                        description=f"Players are progressing {direction} than before ({second_half/first_half:.1f}x change)",
                        confidence=ConfidenceLevel.MEDIUM,
                        evidence=[
                            f"Early median progression time: {first_half:.1f}s",
                            f"Recent median progression time: {second_half:.1f}s",
                        ],
                        recommendations=["Adjust progression scaling to maintain intended pacing"],
                    ))

        with self._lock:
            self._global_insights.extend(insights)

        return insights

    # ---- Recommendation Generation ----

    def generate_recommendations(self, game_id: str) -> List[LearnedInsight]:
        """
        Generate actionable design recommendations based on accumulated
        patterns, anomalies, and trends for a given game.
        """
        insights: List[LearnedInsight] = []

        # Collect all relevant insights
        all_relevant: List[LearnedInsight] = []
        with self._lock:
            for ins_list in self._insights.values():
                all_relevant.extend(ins_list)
            all_relevant.extend(self._global_insights)

        if not all_relevant:
            return insights

        # Group by insight type
        by_type: Dict[InsightType, List[LearnedInsight]] = defaultdict(list)
        for ins in all_relevant:
            by_type[ins.insight_type].append(ins)

        # Recommendation 1: From patterns — suggest UX flow optimizations
        patterns = by_type.get(InsightType.PATTERN, [])
        if patterns:
            pattern_titles = [p.title for p in patterns[:3]]
            insights.append(LearnedInsight(
                insight_type=InsightType.RECOMMENDATION,
                title="Optimize Core Game Loops",
                description=(
                    f"Based on observed patterns ({', '.join(pattern_titles)}), "
                    "consider refining the core interaction loop to reduce friction."
                ),
                confidence=ConfidenceLevel.MEDIUM,
                evidence=[f"Pattern: {p.title}" for p in patterns[:3]],
                recommendations=[
                    "Streamline transitions between frequent action pairs",
                    "Add shortcuts for commonly repeated sequences",
                    "Reduce unnecessary confirmation steps in high-frequency flows",
                ],
            ))

        # Recommendation 2: From anomalies — security and balance fixes
        anomalies = by_type.get(InsightType.ANOMALY, [])
        if anomalies:
            insights.append(LearnedInsight(
                insight_type=InsightType.RECOMMENDATION,
                title="Address Anomalous Behavior",
                description=f"Detected {len(anomalies)} anomalous events that may indicate balance or security issues.",
                confidence=ConfidenceLevel.HIGH,
                evidence=[f"Anomaly: {a.title}" for a in anomalies[:3]],
                recommendations=[
                    "Audit game systems for exploitable mechanics",
                    "Add rate-limiting to fast-repeating actions",
                    "Implement server-side validation for performance outliers",
                ],
            ))

        # Recommendation 3: From trends — adjust difficulty and pacing
        trends = by_type.get(InsightType.TREND, [])
        engagement_trends = [t for t in trends if "engagement" in t.title.lower()]
        error_trends = [t for t in trends if "error" in t.title.lower()]
        if engagement_trends or error_trends:
            recs: List[str] = []
            if engagement_trends:
                recs.append("Review recent content updates for engagement impact")
            if error_trends:
                recs.append("Conduct a difficulty audit of recent game sections")
            recs.append("Consider A/B testing difficulty variants")
            insights.append(LearnedInsight(
                insight_type=InsightType.RECOMMENDATION,
                title="Adjust Game Balance Based on Trends",
                description="Engagement and difficulty trends suggest the need for balance tuning.",
                confidence=ConfidenceLevel.MEDIUM,
                evidence=[f"Trend: {t.title}" for t in engagement_trends + error_trends[:2]],
                recommendations=recs,
            ))

        # Recommendation 4: General content improvement
        if len(all_relevant) >= 5:
            insights.append(LearnedInsight(
                insight_type=InsightType.RECOMMENDATION,
                title="Prioritize High-Impact Polish Areas",
                description=(
                    "With sufficient data collected, focus polishing efforts on the "
                    "areas where players spend the most time and encounter the most issues."
                ),
                confidence=ConfidenceLevel.MEDIUM,
                evidence=["Multiple patterns, anomalies, and trends identified"],
                recommendations=[
                    "Create a priority backlog sorted by player impact",
                    "Focus on the top 3 frustration points first",
                    "Incrementally roll out improvements and measure effect",
                ],
            ))

        with self._lock:
            self._global_insights.extend(insights)

        return insights

    # ---- Player Profiling ----

    def build_player_profile(self, player_id: str) -> PlayerProfile:
        """
        Aggregate all observations and session data into a comprehensive
        player profile including skill level, play style, and preferences.
        """
        obs_list = self._player_observations.get(player_id, [])
        sessions = self._session_history.get(player_id, [])

        total_sessions = len(sessions)
        total_playtime = sum(s.get("duration_seconds", 0) for s in sessions)

        # Actions per minute
        total_actions = sum(s.get("action_count", 0) for s in sessions)
        total_minutes = total_playtime / 60.0
        actions_per_minute = total_actions / max(1.0, total_minutes)

        # Preferred actions
        action_counter: Dict[str, int] = {}
        for o in obs_list:
            if o.obs_type == ObservationType.PLAYER_ACTION:
                name = o.data.get("action", o.data.get("name", "unknown"))
                action_counter[name] = action_counter.get(name, 0) + 1
        preferred_actions = dict(
            sorted(action_counter.items(), key=lambda x: -x[1])[:10]
        )

        # Skill level estimation
        skill_level = self._estimate_skill(player_id, sessions, obs_list)

        # Frustration points
        frustration_points = self._identify_frustration_points(obs_list)

        # Engagement score
        engagement_score = self._compute_engagement(obs_list, sessions)

        # Retention probability
        retention_probability = self._compute_retention_probability(
            player_id, sessions
        )

        # Segments
        segments = self._classify_segments(
            total_sessions, total_playtime, actions_per_minute,
            skill_level, obs_list,
        )

        profile = PlayerProfile(
            player_id=player_id,
            total_sessions=total_sessions,
            total_playtime=total_playtime,
            actions_per_minute=actions_per_minute,
            preferred_actions=preferred_actions,
            skill_level=skill_level,
            frustration_points=frustration_points,
            engagement_score=engagement_score,
            retention_probability=retention_probability,
            segments=segments,
        )

        with self._lock:
            self._profiles[player_id] = profile

        return profile

    def _estimate_skill(
        self,
        player_id: str,
        sessions: List[Dict[str, Any]],
        obs_list: List[PlayerObservation],
    ) -> float:
        """Estimate player skill level from error rate, success rate, and performance data."""
        if not sessions and not obs_list:
            return 0.5

        factors: List[float] = []

        # Factor 1: Error rate (inverted)
        total_errors = sum(s.get("error_count", 0) for s in sessions)
        total_observations = sum(s.get("observation_count", 0) for s in sessions)
        if total_observations > 0:
            error_rate = total_errors / total_observations
            factors.append(1.0 - min(1.0, error_rate * 5))

        # Factor 2: Performance scores
        performance_obs = [o for o in obs_list if o.obs_type == ObservationType.PERFORMANCE]
        scores = [
            o.data.get("score", o.data.get("value", 0))
            for o in performance_obs
            if isinstance(o.data.get("score", o.data.get("value")), (int, float))
        ]
        if scores:
            normalized = min(1.0, statistics.mean(scores) / max(1.0, max(scores)))
            factors.append(normalized)

        # Factor 3: Session completion rate
        completed = sum(
            1 for s in sessions
            if s.get("outcome") in ("completed", "satisfied")
        )
        if sessions:
            factors.append(completed / len(sessions))

        # Factor 4: Progression speed relative to session count
        progression_obs = [o for o in obs_list if o.obs_type == ObservationType.PROGRESSION]
        if progression_obs and sessions:
            prog_per_session = len(progression_obs) / len(sessions)
            factors.append(min(1.0, prog_per_session / 5.0))

        if not factors:
            return 0.5

        return round(statistics.mean(factors), 3)

    def _identify_frustration_points(
        self, obs_list: List[PlayerObservation],
    ) -> List[str]:
        """Identify locations and events associated with player frustration."""
        points: Dict[str, float] = {}

        for o in obs_list:
            loc = o.data.get("location", o.data.get("area", ""))
            if not loc:
                continue

            weight = 0.0
            if o.obs_type == ObservationType.ERROR:
                weight = 1.0
            elif o.obs_type == ObservationType.PERFORMANCE:
                score = o.data.get("score", o.data.get("value", 0.5))
                if isinstance(score, (int, float)) and score < 0.4:
                    weight = 0.5

            if weight > 0:
                points[loc] = points.get(loc, 0.0) + weight

        sorted_points = sorted(points.items(), key=lambda x: -x[1])
        return [loc for loc, _ in sorted_points[:5]]

    def _compute_engagement(
        self,
        obs_list: List[PlayerObservation],
        sessions: List[Dict[str, Any]],
    ) -> float:
        """Compute overall engagement score from multiple signals."""
        if not sessions:
            return 0.5

        factors: List[float] = []

        # Session frequency (sessions per day over the observed period)
        if len(sessions) >= 2:
            timestamps = [
                s.get("started_at", s.get("ended_at", 0))
                for s in sessions
            ]
            valid_ts = [t for t in timestamps if t > 0]
            if len(valid_ts) >= 2:
                span_days = (max(valid_ts) - min(valid_ts)) / 86400.0
                if span_days > 0:
                    sessions_per_day = len(valid_ts) / span_days
                    factors.append(min(1.0, sessions_per_day / 3.0))

        # Average session duration relative to expected
        avg_duration = (
            sum(s.get("duration_seconds", 0) for s in sessions) / len(sessions)
        )
        factors.append(min(1.0, avg_duration / 1800.0))

        # Engagement signals
        engagement_obs = [o for o in obs_list if o.obs_type == ObservationType.ENGAGEMENT]
        if engagement_obs:
            scores = [
                o.data.get("score", o.data.get("value", 0.5))
                for o in engagement_obs
                if isinstance(o.data.get("score", o.data.get("value")), (int, float))
            ]
            if scores:
                factors.append(statistics.mean(scores))

        # Session outcome ratio
        positive_outcomes = sum(
            1 for s in sessions
            if s.get("outcome") in ("completed", "satisfied")
        )
        factors.append(positive_outcomes / len(sessions))

        if not factors:
            return 0.5

        return round(statistics.mean(factors), 3)

    def _compute_retention_probability(
        self,
        player_id: str,
        sessions: List[Dict[str, Any]],
    ) -> float:
        """Estimate the probability that the player will return for another session."""
        if not sessions:
            return 0.5

        factors: List[float] = []

        # Factor 1: Recent session count
        if len(sessions) >= 2:
            recent = sessions[-3:]
            older = sessions[:-3] if len(sessions) > 3 else sessions[:1]
            recent_count = len(recent)
            older_count = len(older)
            if older_count > 0:
                trend_ratio = recent_count / older_count
                factors.append(min(1.0, trend_ratio))

        # Factor 2: Last session outcome
        last_outcome = sessions[-1].get("outcome", "")
        outcome_score = {
            "completed": 0.9, "satisfied": 0.85, "neutral": 0.5,
            "abandoned": 0.3, "frustrated": 0.2, "error": 0.1,
            "disconnected": 0.35, "timeout": 0.4,
        }
        factors.append(outcome_score.get(last_outcome, 0.5))

        # Factor 3: Time since last session
        if sessions:
            now = _time_module.time()
            last_ended = sessions[-1].get("ended_at", sessions[-1].get("started_at", now))
            hours_since_last = (now - last_ended) / 3600.0
            recency = math.exp(-hours_since_last / 168.0)  # Decay over ~1 week
            factors.append(recency)

        # Factor 4: Total sessions as indicator of investment
        factors.append(min(1.0, len(sessions) / 10.0))

        return round(statistics.mean(factors), 3)

    def _classify_segments(
        self,
        total_sessions: int,
        total_playtime: float,
        actions_per_minute: float,
        skill_level: float,
        obs_list: List[PlayerObservation],
    ) -> List[str]:
        """Classify the player into behavioral segments."""
        segments: List[str] = []

        avg_session_minutes = (
            total_playtime / max(1, total_sessions) / 60.0
        )

        # Estimate sessions per week (simplified: use total sessions)
        sessions_per_week = min(20.0, total_sessions / max(1.0, 2.0))

        # Compute exploration ratio from progression and interaction observations
        total_events = len(obs_list)
        exploration_events = sum(
            1 for o in obs_list
            if o.obs_type in (ObservationType.INTERACTION, ObservationType.PROGRESSION)
            and o.data.get("type") in ("explore", "discover", "wander", "side_content")
        )
        exploration_ratio = exploration_events / max(1.0, total_events)

        # Score each segment profile
        best_segment = ""
        best_score = -1.0

        for seg_name, thresholds in self._SEGMENT_PROFILES.items():
            score = 0.0
            checks = 0

            for metric, (lo, hi) in thresholds.items():
                checks += 1
                if metric == "sessions_per_week":
                    val = sessions_per_week
                elif metric == "avg_session_minutes":
                    val = avg_session_minutes
                elif metric == "skill_level":
                    val = skill_level
                elif metric == "exploration_ratio":
                    val = exploration_ratio
                else:
                    val = 0.5

                # Score: 1.0 if within range, decreasing outside
                mid = (lo + hi) / 2.0
                span = (hi - lo) / 2.0
                if span > 0:
                    dist = abs(val - mid) / span
                    score += max(0.0, 1.0 - dist * 0.5)
                else:
                    score += 1.0

            avg_score = score / max(1, checks)
            if avg_score > best_score:
                best_score = avg_score
                best_segment = seg_name

        if best_segment:
            segments.append(best_segment)

        # Secondary segment: if close to another archetype
        secondary_scores = []
        for seg_name, thresholds in self._SEGMENT_PROFILES.items():
            if seg_name == best_segment:
                continue
            score = 0.0
            for metric, (lo, hi) in thresholds.items():
                if metric == "sessions_per_week":
                    val = sessions_per_week
                elif metric == "avg_session_minutes":
                    val = avg_session_minutes
                elif metric == "skill_level":
                    val = skill_level
                elif metric == "exploration_ratio":
                    val = exploration_ratio
                else:
                    val = 0.5
                mid = (lo + hi) / 2.0
                span = (hi - lo) / 2.0
                dist = abs(val - mid) / max(0.001, span)
                score += max(0.0, 1.0 - dist * 0.5)
            avg_score = score / len(thresholds)
            secondary_scores.append((seg_name, avg_score))

        secondary_scores.sort(key=lambda x: -x[1])
        if secondary_scores and secondary_scores[0][1] > 0.5:
            segments.append(secondary_scores[0][0])

        return segments

    # ---- Prediction ----

    def predict_retention(self, player_id: str) -> Dict[str, Any]:
        """
        Predict the player's likelihood of continued engagement based on
        behavioral patterns, session history, and engagement signals.
        """
        sessions = self._session_history.get(player_id, [])
        obs_list = self._player_observations.get(player_id, [])
        retention_prob = self._compute_retention_probability(player_id, sessions)

        # Estimate days until next session
        if sessions:
            if len(sessions) >= 2:
                intervals: List[float] = []
                timestamps = sorted([
                    s.get("started_at", s.get("ended_at", 0))
                    for s in sessions
                ])
                for i in range(1, len(timestamps)):
                    gap = timestamps[i] - timestamps[i - 1]
                    if gap > 0:
                        intervals.append(gap)
                if intervals:
                    avg_gap = statistics.mean(intervals)
                    days_until_next = round(avg_gap / 86400.0, 1)
                else:
                    days_until_next = 7.0
            else:
                days_until_next = 3.0
        else:
            days_until_next = -1.0

        # Estimated lifetime
        total_days = 0.0
        if len(sessions) >= 2:
            timestamps = sorted([
                s.get("started_at", s.get("ended_at", 0))
                for s in sessions if s.get("started_at", 0) > 0
            ])
            if len(timestamps) >= 2:
                total_days = (max(timestamps) - min(timestamps)) / 86400.0

        estimated_retention_days = round(
            total_days * (1.0 + retention_prob * 2.0), 1
        )

        result = {
            "player_id": player_id,
            "retention_probability": round(retention_prob, 3),
            "estimated_days_until_next_session": days_until_next,
            "estimated_retention_days": estimated_retention_days,
            "total_sessions": len(sessions),
            "data_points": len(obs_list),
            "confidence": (
                "high" if len(sessions) >= 10
                else "medium" if len(sessions) >= 4
                else "low"
            ),
        }

        return result

    def predict_churn(self, player_id: str) -> Dict[str, Any]:
        """
        Predict the likelihood that a player will stop playing (churn),
        identifying key risk factors from behavioral data.
        """
        sessions = self._session_history.get(player_id, [])
        obs_list = self._player_observations.get(player_id, [])
        retention_prob = self._compute_retention_probability(player_id, sessions)
        churn_risk = round(1.0 - retention_prob, 3)

        # Identify churn risk factors
        risk_factors: List[str] = []

        if len(sessions) >= 2:
            # Decreasing session frequency
            recent_sessions = sessions[-3:]
            older_sessions = sessions[:-3] if len(sessions) > 3 else sessions[:1]
            if len(recent_sessions) < len(older_sessions):
                risk_factors.append("Declining session frequency")

            # Decreasing session duration
            recent_duration = statistics.mean([
                s.get("duration_seconds", 0) for s in recent_sessions
            ])
            older_duration = statistics.mean([
                s.get("duration_seconds", 0) for s in older_sessions
            ])
            if older_duration > 0 and recent_duration < older_duration * 0.7:
                risk_factors.append("Shortening session duration")

        # High frustration ratio
        frustration_obs = sum(
            1 for o in obs_list
            if o.obs_type == ObservationType.ERROR
            and o.data.get("severity") in ("high", "critical")
        )
        if frustration_obs >= 3:
            risk_factors.append("Multiple high-severity errors encountered")

        # Last session was negative
        if sessions and sessions[-1].get("outcome") in ("frustrated", "abandoned", "error"):
            risk_factors.append("Last session ended negatively")

        # Low engagement signals
        engagement_obs = [o for o in obs_list if o.obs_type == ObservationType.ENGAGEMENT]
        if engagement_obs:
            scores = [
                o.data.get("score", 0.5)
                for o in engagement_obs
                if isinstance(o.data.get("score"), (int, float))
            ]
            if scores and statistics.mean(scores) < 0.3:
                risk_factors.append("Consistently low engagement scores")

        # Long gap since last session
        if sessions:
            now = _time_module.time()
            last_ended = sessions[-1].get("ended_at", sessions[-1].get("started_at", now))
            hours_since = (now - last_ended) / 3600.0
            if hours_since > 168:  # > 1 week
                risk_factors.append(f"Inactive for {hours_since/24:.0f} days")

        risk_level = (
            "critical" if churn_risk > 0.7
            else "high" if churn_risk > 0.5
            else "moderate" if churn_risk > 0.3
            else "low"
        )

        result = {
            "player_id": player_id,
            "churn_risk": churn_risk,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "retention_probability": round(retention_prob, 3),
            "total_sessions": len(sessions),
            "data_points": len(obs_list),
            "recommendations": self._churn_recommendations(risk_factors, churn_risk),
        }

        return result

    def _churn_recommendations(
        self, risk_factors: List[str], churn_risk: float,
    ) -> List[str]:
        """Generate targeted recommendations to reduce churn risk."""
        recs: List[str] = []

        for factor in risk_factors:
            if "frequency" in factor.lower():
                recs.append("Send re-engagement notification with new content highlight")
            elif "duration" in factor.lower():
                recs.append("Offer shorter, more digestible content sessions")
            elif "error" in factor.lower():
                recs.append("Prioritize bug fixes causing player frustration")
            elif "negative" in factor.lower():
                recs.append("Follow up with positive reinforcement or bonus reward")
            elif "engagement" in factor.lower():
                recs.append("Introduce new mechanics or content to refresh interest")
            elif "inactive" in factor.lower():
                recs.append("Trigger comeback bonus or limited-time event")

        if churn_risk > 0.5 and not recs:
            recs.append("Conduct personalized outreach to understand player concerns")

        return recs

    # ---- Player Segmentation ----

    def segment_players(self, game_id: str) -> Dict[str, Any]:
        """
        Cluster all players for a game into behavioral segments: casual, core,
        hardcore, explorer, achiever.
        """
        segment_results: Dict[str, List[str]] = {
            seg: [] for seg in self._SEGMENT_PROFILES
        }
        player_details: Dict[str, Dict[str, Any]] = {}

        for player_id in list(self._player_observations.keys()):
            # Include if in target game or if game_id not filtered
            include = False
            with self._lock:
                for sid, session in self._sessions.items():
                    if session.get("player_id") == player_id:
                        if not game_id or session.get("game_id") == game_id:
                            include = True
                            break
            if not include and game_id:
                continue

            profile = self.build_player_profile(player_id)
            for seg in profile.segments:
                if seg in segment_results:
                    segment_results[seg].append(player_id)

            player_details[player_id] = {
                "segments": profile.segments,
                "skill_level": profile.skill_level,
                "engagement_score": profile.engagement_score,
                "retention_probability": profile.retention_probability,
                "total_sessions": profile.total_sessions,
            }

        total_players = len(player_details)
        distribution = {
            seg: {
                "count": len(players),
                "percentage": round(
                    len(players) / max(1, total_players) * 100, 1
                ),
            }
            for seg, players in segment_results.items()
        }

        return {
            "game_id": game_id,
            "total_players": total_players,
            "segments_distribution": distribution,
            "player_details": player_details,
            "segment_descriptions": {
                "casual": "Plays in short bursts, low skill investment, prefers accessible content",
                "core": "Regular player with moderate skill and consistent engagement",
                "hardcore": "High-skill, high-time-investment player seeking challenge",
                "explorer": "Prioritizes discovery and content breadth over optimization",
                "achiever": "Goal-driven player focused on completion and mastery",
            },
        }

    # ---- Statistics ----

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics about the learning pipeline state."""
        with self._lock:
            total_observations = sum(
                len(obs) for obs in self._observations.values()
            )
            total_insights = sum(
                len(ins) for ins in self._insights.values()
            ) + len(self._global_insights)

            active_sessions = sum(
                1 for s in self._sessions.values() if s.get("active", False)
            )
            total_sessions = len(self._sessions)

            obs_by_type: Dict[str, int] = {}
            for obs_list in self._observations.values():
                for o in obs_list:
                    key = o.obs_type.value
                    obs_by_type[key] = obs_by_type.get(key, 0) + 1

            insight_by_type: Dict[str, int] = {}
            for ins_list in self._insights.values():
                for ins in ins_list:
                    key = ins.insight_type.value
                    insight_by_type[key] = insight_by_type.get(key, 0) + 1
            for ins in self._global_insights:
                key = ins.insight_type.value
                insight_by_type[key] = insight_by_type.get(key, 0) + 1

            unique_players = len(self._player_observations)

            return {
                "total_observations": total_observations,
                "observations_by_type": obs_by_type,
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "unique_players": unique_players,
                "player_profiles": len(self._profiles),
                "total_insights": total_insights,
                "insights_by_type": insight_by_type,
                "trained_models": len(self._models),
                "global_insights": len(self._global_insights),
            }


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------

def get_learning_pipeline() -> LearningPipeline:
    """Return the singleton LearningPipeline instance."""
    return LearningPipeline.get_instance()