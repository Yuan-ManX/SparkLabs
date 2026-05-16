"""
SparkAI Agent - Automated Playtest Simulator

AI-driven playtesting simulation that models different player archetypes
playing through game levels to detect design issues, pacing problems,
difficulty imbalances, and frustration points. Produces comprehensive
test reports with actionable recommendations.

Architecture:
  PlaytestSimulator
    |-- PlayerProfile (simulated player persona with archetype and stats)
    |-- PlaySession (individual simulated play-through record)
    |-- TestReport (comprehensive analysis with scores and recommendations)
    |-- FrustrationDetector (identifies player pain points)
    |-- PacingAnalyzer (evaluates level flow and rhythm)
    |-- DifficultyCurveAnalyzer (checks progression smoothness)

Simulation Overview:
  1. Create simulated player profiles based on player archetypes
  2. Run simulated play sessions through virtual levels
  3. Track deaths, items collected, frustration events, and stuck points
  4. Analyze results across multiple simulation runs
  5. Generate comprehensive test reports with recommendations
  6. Compare results across different player archetypes
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class PlayerArchetype(Enum):
    COMPLETIONIST = "completionist"
    SPEEDRUNNER = "speedrunner"
    EXPLORER = "explorer"
    CASUAL = "casual"
    HARDCORE = "hardcore"
    SOCIAL = "social"
    STORY_FOCUSED = "story_focused"


class SimulationMode(Enum):
    FULL_RUN = "full_run"
    FOCUSED_LEVEL = "focused_level"
    STRESS_TEST = "stress_test"
    EXPLORATION = "exploration"
    BALANCE_CHECK = "balance_check"


class TestOutcome(Enum):
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    INCONCLUSIVE = "inconclusive"


class FrustrationLevel(Enum):
    NONE = "none"
    MILD = "mild"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PlayerProfile:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    archetype: PlayerArchetype = PlayerArchetype.CASUAL
    skill_level: float = 0.5
    patience: float = 0.5
    preference_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "archetype": self.archetype.value,
            "skill_level": self.skill_level,
            "patience": self.patience,
            "preference_weights": dict(self.preference_weights),
        }


@dataclass
class FrustrationEvent:
    level_index: int = 0
    level_name: str = ""
    event_type: str = ""
    severity: FrustrationLevel = FrustrationLevel.MILD
    description: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "level_name": self.level_name,
            "event_type": self.event_type,
            "severity": self.severity.value,
            "description": self.description,
            "timestamp": self.timestamp,
        }


@dataclass
class StuckPoint:
    level_index: int = 0
    level_name: str = ""
    position_description: str = ""
    duration_seconds: float = 0.0
    cause: str = ""
    archetype: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "level_name": self.level_name,
            "position_description": self.position_description,
            "duration_seconds": self.duration_seconds,
            "cause": self.cause,
            "archetype": self.archetype,
        }


@dataclass
class PlaySession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    profile: Optional[PlayerProfile] = None
    duration: float = 0.0
    levels_completed: int = 0
    deaths: int = 0
    items_collected: int = 0
    frustration_events: List[FrustrationEvent] = field(default_factory=list)
    stuck_points: List[StuckPoint] = field(default_factory=list)
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "profile": self.profile.to_dict() if self.profile else None,
            "duration": self.duration,
            "levels_completed": self.levels_completed,
            "deaths": self.deaths,
            "items_collected": self.items_collected,
            "frustration_events": [e.to_dict() for e in self.frustration_events],
            "stuck_points": [s.to_dict() for s in self.stuck_points],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class PacingEntry:
    level_index: int = 0
    level_name: str = ""
    time_spent: float = 0.0
    expected_time: float = 0.0
    deviation: float = 0.0
    rating: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "level_name": self.level_name,
            "time_spent": self.time_spent,
            "expected_time": self.expected_time,
            "deviation": self.deviation,
            "rating": self.rating,
        }


@dataclass
class DifficultyPoint:
    level_index: int = 0
    level_name: str = ""
    difficulty_score: float = 0.0
    deaths: int = 0
    frustration_count: int = 0
    assessment: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "level_index": self.level_index,
            "level_name": self.level_name,
            "difficulty_score": self.difficulty_score,
            "deaths": self.deaths,
            "frustration_count": self.frustration_count,
            "assessment": self.assessment,
        }


@dataclass
class TestReport:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    overall_score: float = 0.0
    fun_rating: float = 0.0
    difficulty_assessment: str = ""
    pacing_analysis: List[PacingEntry] = field(default_factory=list)
    bugs_found: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    difficulty_curve: List[DifficultyPoint] = field(default_factory=list)
    outcome: TestOutcome = TestOutcome.INCONCLUSIVE
    sessions_analyzed: int = 0
    generated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "overall_score": self.overall_score,
            "fun_rating": self.fun_rating,
            "difficulty_assessment": self.difficulty_assessment,
            "pacing_analysis": [p.to_dict() for p in self.pacing_analysis],
            "bugs_found": list(self.bugs_found),
            "recommendations": list(self.recommendations),
            "difficulty_curve": [d.to_dict() for d in self.difficulty_curve],
            "outcome": self.outcome.value,
            "sessions_analyzed": self.sessions_analyzed,
            "generated_at": self.generated_at,
        }


class PlaytestSimulator:
    """
    Self-contained AI playtesting simulation engine.

    Models different player archetypes playing through virtual game
    levels to detect design flaws, pacing issues, difficulty spikes,
    and player frustration points. All simulation is self-contained
    with no external dependencies.
    """

    _instance: Optional["PlaytestSimulator"] = None

    def __init__(self):
        self._sessions: List[PlaySession] = []
        self._reports: List[TestReport] = []
        self._session_count: int = 0
        self._report_count: int = 0
        self._lock = threading.Lock()
        self._MAX_SESSIONS = 10000
        self._MAX_REPORTS = 5000

    @classmethod
    def get_instance(cls) -> "PlaytestSimulator":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_player_profile(self, archetype: PlayerArchetype) -> PlayerProfile:
        """
        Generate a simulated player persona based on the given archetype.
        Each archetype has distinct skill level, patience, and preference weights.
        """
        archetype_configs = {
            PlayerArchetype.COMPLETIONIST: {
                "skill_level": (0.6, 0.8),
                "patience": (0.7, 0.95),
                "preference_weights": {
                    "collectibles": random.uniform(0.85, 1.0),
                    "secrets": random.uniform(0.8, 1.0),
                    "completion": random.uniform(0.9, 1.0),
                    "speed": random.uniform(0.1, 0.3),
                    "combat": random.uniform(0.4, 0.7),
                    "exploration": random.uniform(0.6, 0.9),
                    "story": random.uniform(0.5, 0.8),
                },
            },
            PlayerArchetype.SPEEDRUNNER: {
                "skill_level": (0.8, 1.0),
                "patience": (0.1, 0.35),
                "preference_weights": {
                    "collectibles": random.uniform(0.05, 0.2),
                    "secrets": random.uniform(0.1, 0.4),
                    "completion": random.uniform(0.1, 0.3),
                    "speed": random.uniform(0.9, 1.0),
                    "combat": random.uniform(0.4, 0.7),
                    "exploration": random.uniform(0.1, 0.3),
                    "story": random.uniform(0.05, 0.2),
                },
            },
            PlayerArchetype.EXPLORER: {
                "skill_level": (0.3, 0.7),
                "patience": (0.7, 0.9),
                "preference_weights": {
                    "collectibles": random.uniform(0.5, 0.8),
                    "secrets": random.uniform(0.85, 1.0),
                    "completion": random.uniform(0.5, 0.75),
                    "speed": random.uniform(0.1, 0.35),
                    "combat": random.uniform(0.2, 0.5),
                    "exploration": random.uniform(0.9, 1.0),
                    "story": random.uniform(0.4, 0.7),
                },
            },
            PlayerArchetype.CASUAL: {
                "skill_level": (0.1, 0.4),
                "patience": (0.5, 0.8),
                "preference_weights": {
                    "collectibles": random.uniform(0.3, 0.6),
                    "secrets": random.uniform(0.2, 0.5),
                    "completion": random.uniform(0.3, 0.6),
                    "speed": random.uniform(0.2, 0.5),
                    "combat": random.uniform(0.3, 0.6),
                    "exploration": random.uniform(0.3, 0.6),
                    "story": random.uniform(0.5, 0.8),
                },
            },
            PlayerArchetype.HARDCORE: {
                "skill_level": (0.7, 1.0),
                "patience": (0.3, 0.6),
                "preference_weights": {
                    "collectibles": random.uniform(0.3, 0.6),
                    "secrets": random.uniform(0.4, 0.7),
                    "completion": random.uniform(0.5, 0.8),
                    "speed": random.uniform(0.3, 0.6),
                    "combat": random.uniform(0.8, 1.0),
                    "exploration": random.uniform(0.3, 0.6),
                    "story": random.uniform(0.3, 0.6),
                },
            },
            PlayerArchetype.SOCIAL: {
                "skill_level": (0.2, 0.6),
                "patience": (0.4, 0.7),
                "preference_weights": {
                    "collectibles": random.uniform(0.5, 0.8),
                    "secrets": random.uniform(0.3, 0.6),
                    "completion": random.uniform(0.4, 0.7),
                    "speed": random.uniform(0.3, 0.6),
                    "combat": random.uniform(0.3, 0.6),
                    "exploration": random.uniform(0.4, 0.7),
                    "story": random.uniform(0.5, 0.8),
                },
            },
            PlayerArchetype.STORY_FOCUSED: {
                "skill_level": (0.2, 0.5),
                "patience": (0.8, 1.0),
                "preference_weights": {
                    "collectibles": random.uniform(0.3, 0.6),
                    "secrets": random.uniform(0.4, 0.7),
                    "completion": random.uniform(0.3, 0.6),
                    "speed": random.uniform(0.1, 0.3),
                    "combat": random.uniform(0.2, 0.5),
                    "exploration": random.uniform(0.3, 0.6),
                    "story": random.uniform(0.9, 1.0),
                },
            },
        }

        config = archetype_configs.get(archetype, archetype_configs[PlayerArchetype.CASUAL])
        skill_min, skill_max = config["skill_level"]
        patience_min, patience_max = config["patience"]

        profile = PlayerProfile(
            archetype=archetype,
            skill_level=random.uniform(skill_min, skill_max),
            patience=random.uniform(patience_min, patience_max),
            preference_weights=dict(config["preference_weights"]),
        )
        return profile

    def run_simulation(
        self,
        profile: PlayerProfile,
        mode: SimulationMode,
        level_count: int = 5,
    ) -> PlaySession:
        """
        Simulate a full play session for a given player profile and mode.

        The simulation models level playthroughs with deaths, item collection,
        frustration events, and stuck points based on the player archetype's
        skill level, patience, and preference weights.
        """
        with self._lock:
            session = PlaySession(profile=profile)
            start_time = time.time()

            if mode == SimulationMode.FOCUSED_LEVEL:
                level_count = 1
            elif mode == SimulationMode.STRESS_TEST:
                level_count = max(level_count, 10)
                level_count = min(level_count, 50)
            elif mode == SimulationMode.EXPLORATION:
                level_count = min(level_count, 8)

            base_difficulty = 0.5
            difficulty_ramp = 0.05
            total_deaths = 0
            total_items = 0
            all_frustration_events: List[FrustrationEvent] = []
            all_stuck_points: List[StuckPoint] = []

            for level_idx in range(level_count):
                level_name = f"Level_{level_idx + 1}"
                level_difficulty = base_difficulty + (difficulty_ramp * level_idx)

                if mode == SimulationMode.STRESS_TEST:
                    level_difficulty = base_difficulty + (difficulty_ramp * level_idx * 2.5)
                elif mode == SimulationMode.BALANCE_CHECK:
                    level_difficulty = base_difficulty + (difficulty_ramp * level_idx)

                completion_chance = max(0.1, profile.skill_level - level_difficulty + 0.5)

                if random.random() < completion_chance:
                    level_deaths = self._calculate_deaths(profile, level_difficulty, mode)
                    items_collected = self._calculate_items_collected(profile, level_idx)
                    frustration_events = self._generate_frustration_events(
                        profile, level_idx, level_name, level_difficulty, mode
                    )
                    stuck_points = self._generate_stuck_points(
                        profile, level_idx, level_name, level_difficulty, mode
                    )

                    total_deaths += level_deaths
                    total_items += items_collected
                    all_frustration_events.extend(frustration_events)
                    all_stuck_points.extend(stuck_points)
                else:
                    level_deaths = self._calculate_deaths(profile, level_difficulty + 0.3, mode)
                    total_deaths += level_deaths

                    critical_event = FrustrationEvent(
                        level_index=level_idx,
                        level_name=level_name,
                        event_type="level_failed",
                        severity=FrustrationLevel.CRITICAL,
                        description=f"Player could not complete {level_name}",
                        timestamp=time.time(),
                    )
                    all_frustration_events.append(critical_event)

                    stuck_point = StuckPoint(
                        level_index=level_idx,
                        level_name=level_name,
                        position_description=f"Hard section near end of {level_name}",
                        duration_seconds=random.uniform(30.0, 120.0),
                        cause="High difficulty",
                        archetype=profile.archetype.value,
                    )
                    all_stuck_points.append(stuck_point)
                    break

            session.duration = time.time() - start_time
            session.levels_completed = min(
                level_idx + 1 if all_frustration_events and all_frustration_events[-1].event_type == "level_failed"
                else level_idx + 1,
                level_count,
            )
            session.deaths = total_deaths
            session.items_collected = total_items
            session.frustration_events = all_frustration_events
            session.stuck_points = all_stuck_points
            session.completed_at = time.time()

            self._sessions.append(session)
            self._session_count += 1

            if len(self._sessions) > self._MAX_SESSIONS:
                self._sessions = self._sessions[-self._MAX_SESSIONS:]

            return session

    def _calculate_deaths(
        self,
        profile: PlayerProfile,
        level_difficulty: float,
        mode: SimulationMode,
    ) -> int:
        base_deaths = int((level_difficulty / (profile.skill_level + 0.01)) * 5)
        base_deaths = max(0, base_deaths)

        if mode == SimulationMode.STRESS_TEST:
            base_deaths = int(base_deaths * 2.5)
        elif mode == SimulationMode.BALANCE_CHECK:
            base_deaths = base_deaths

        variance = random.randint(-1, 2)
        return max(0, base_deaths + variance)

    def _calculate_items_collected(
        self,
        profile: PlayerProfile,
        level_index: int,
    ) -> int:
        weights = profile.preference_weights
        collectibles_weight = weights.get("collectibles", 0.5)
        secrets_weight = weights.get("secrets", 0.5)

        base_items = random.randint(5, 15)
        extra_from_collectibles = int(base_items * collectibles_weight * 0.5)
        extra_from_secrets = int(base_items * secrets_weight * 0.3)

        return base_items + extra_from_collectibles + extra_from_secrets

    def _generate_frustration_events(
        self,
        profile: PlayerProfile,
        level_index: int,
        level_name: str,
        level_difficulty: float,
        mode: SimulationMode,
    ) -> List[FrustrationEvent]:
        events: List[FrustrationEvent] = []
        frustration_threshold = 1.0 - profile.patience

        base_frustration_count = int(level_difficulty * frustration_threshold * 4)

        if mode == SimulationMode.STRESS_TEST:
            base_frustration_count = int(base_frustration_count * 2.0)

        count = max(0, min(base_frustration_count, 5))
        event_types = ["puzzle_confusion", "difficulty_spike", "unclear_objective",
                       "camera_issue", "control_frustration", "enemy_overwhelm"]

        for _ in range(count):
            event_type = random.choice(event_types)
            severity_roll = random.random() + level_difficulty - profile.skill_level
            if severity_roll > 0.9:
                severity = FrustrationLevel.CRITICAL
            elif severity_roll > 0.7:
                severity = FrustrationLevel.HIGH
            elif severity_roll > 0.5:
                severity = FrustrationLevel.MODERATE
            else:
                severity = FrustrationLevel.MILD

            events.append(FrustrationEvent(
                level_index=level_index,
                level_name=level_name,
                event_type=event_type,
                severity=severity,
                description=f"{event_type.replace('_', ' ').title()} in {level_name}",
                timestamp=time.time(),
            ))

        return events

    def _generate_stuck_points(
        self,
        profile: PlayerProfile,
        level_index: int,
        level_name: str,
        level_difficulty: float,
        mode: SimulationMode,
    ) -> List[StuckPoint]:
        stuck_points: List[StuckPoint] = []
        stuck_threshold = (1.0 - profile.skill_level) * level_difficulty

        if mode == SimulationMode.STRESS_TEST:
            stuck_threshold *= 2.0

        if stuck_threshold > 0.35:
            count = random.randint(0, 2)
            stuck_causes = ["puzzle_too_obscure", "unmarked_path", "hidden_mechanic",
                            "precise_jump_required", "enemy_gauntlet"]

            for _ in range(count):
                stuck_points.append(StuckPoint(
                    level_index=level_index,
                    level_name=level_name,
                    position_description=f"Mid-section of {level_name}" if random.random() > 0.5
                    else f"Final section of {level_name}",
                    duration_seconds=random.uniform(10.0, 90.0),
                    cause=random.choice(stuck_causes),
                    archetype=profile.archetype.value,
                ))

        return stuck_points

    def detect_pacing_issues(self, report: TestReport) -> List[PacingEntry]:
        """
        Analyze level flow problems by evaluating time spent per level
        against expected durations and identifying pacing anomalies.
        """
        pacing_entries: List[PacingEntry] = []
        sessions = self._sessions

        if not sessions:
            return pacing_entries

        level_times: Dict[int, List[float]] = {}
        for session in sessions:
            if not session.frustration_events:
                continue
            events_by_level: Dict[int, List[FrustrationEvent]] = {}
            for event in session.frustration_events:
                events_by_level.setdefault(event.level_index, []).append(event)

            for level_idx, events in events_by_level.items():
                estimated_time = 60.0 + random.uniform(-15.0, 15.0)
                adjusted_time = estimated_time * (1.0 + len(events) * 0.15)
                level_times.setdefault(level_idx, []).append(adjusted_time)

        for level_idx, times in sorted(level_times.items()):
            avg_time = sum(times) / len(times)
            expected_time = 60.0

            if level_idx == 0:
                expected_time = 80.0
            elif level_idx < 3:
                expected_time = 70.0
            else:
                expected_time = 90.0

            deviation = avg_time - expected_time
            if deviation > 30.0:
                rating = "Too Slow"
            elif deviation < -30.0:
                rating = "Too Fast"
            elif abs(deviation) <= 15.0:
                rating = "Well Paced"
            else:
                rating = "Slightly Off"

            pacing_entries.append(PacingEntry(
                level_index=level_idx,
                level_name=f"Level_{level_idx + 1}",
                time_spent=round(avg_time, 2),
                expected_time=expected_time,
                deviation=round(deviation, 2),
                rating=rating,
            ))

        report.pacing_analysis = pacing_entries

        too_slow = [e for e in pacing_entries if e.rating == "Too Slow"]
        too_fast = [e for e in pacing_entries if e.rating == "Too Fast"]

        if too_slow:
            report.recommendations.append(
                f"Levels {', '.join(e.level_name for e in too_slow)} are too slow; "
                "consider reducing complexity or adding shortcuts."
            )
        if too_fast:
            report.recommendations.append(
                f"Levels {', '.join(e.level_name for e in too_fast)} are too fast; "
                "consider adding more content or obstacles."
            )

        return pacing_entries

    def analyze_difficulty_curve(self, report: TestReport) -> List[DifficultyPoint]:
        """
        Check the difficulty ramp across levels to ensure smooth progression.
        Identifies difficulty spikes that may frustrate players.
        """
        difficulty_points: List[DifficultyPoint] = []
        sessions = self._sessions

        if not sessions:
            return difficulty_points

        level_data: Dict[int, Dict[str, Any]] = {}
        for session in sessions:
            if not session.frustration_events:
                continue
            events_by_level: Dict[int, List[FrustrationEvent]] = {}
            for event in session.frustration_events:
                events_by_level.setdefault(event.level_index, []).append(event)

            for level_idx, events in events_by_level.items():
                profile_skill = session.profile.skill_level if session.profile else 0.5
                deaths_per_level = session.deaths / max(session.levels_completed, 1)

                difficulty_score = (deaths_per_level * 0.3 + len(events) * 0.15) / (profile_skill + 0.1)
                difficulty_score = min(difficulty_score, 1.0)

                data = level_data.setdefault(level_idx, {
                    "scores": [],
                    "total_deaths": 0,
                    "total_frustration": 0,
                })
                data["scores"].append(difficulty_score)

        for level_idx in sorted(level_data.keys()):
            data = level_data[level_idx]
            avg_score = sum(data["scores"]) / len(data["scores"])

            if avg_score < 0.3:
                assessment = "Too Easy"
            elif avg_score < 0.6:
                assessment = "Well Balanced"
            elif avg_score < 0.8:
                assessment = "Challenging"
            else:
                assessment = "Too Hard"

            difficulty_points.append(DifficultyPoint(
                level_index=level_idx,
                level_name=f"Level_{level_idx + 1}",
                difficulty_score=round(avg_score, 3),
                deaths=data.get("total_deaths", 0),
                frustration_count=data.get("total_frustration", 0),
                assessment=assessment,
            ))

        report.difficulty_curve = difficulty_points

        prev_score = None
        for dp in difficulty_points:
            if prev_score is not None and dp.difficulty_score - prev_score > 0.35:
                report.recommendations.append(
                    f"Difficulty spike detected at {dp.level_name}: "
                    f"score jumped from {prev_score:.2f} to {dp.difficulty_score:.2f}. "
                    "Consider smoothing the difficulty ramp."
                )
            prev_score = dp.difficulty_score

        too_hard = [dp for dp in difficulty_points if dp.assessment == "Too Hard"]
        if len(too_hard) > len(difficulty_points) * 0.4:
            report.recommendations.append(
                "More than 40% of levels are rated 'Too Hard'. "
                "Consider reducing overall difficulty or adding easier early levels."
            )

        return difficulty_points

    def find_stuck_points(self, sessions: List[PlaySession]) -> List[StuckPoint]:
        """
        Identify where players get stuck across multiple play sessions.
        Aggregates stuck point data and highlights recurring problem areas.
        """
        all_stuck_points: List[StuckPoint] = []
        for session in sessions:
            all_stuck_points.extend(session.stuck_points)

        location_counts: Dict[str, List[StuckPoint]] = {}
        for sp in all_stuck_points:
            key = f"{sp.level_name}:{sp.position_description}:{sp.cause}"
            location_counts.setdefault(key, []).append(sp)

        frequent_stuck_points: List[StuckPoint] = []
        for key, points in location_counts.items():
            if len(points) >= 2:
                representative = points[0]
                representative.duration_seconds = sum(p.duration_seconds for p in points) / len(points)
                frequent_stuck_points.append(representative)

        frequent_stuck_points.sort(key=lambda sp: sp.duration_seconds, reverse=True)
        return frequent_stuck_points

    def generate_test_report(self, sessions: List[PlaySession]) -> TestReport:
        """
        Generate a comprehensive test analysis from collected play sessions.
        Computes overall score, fun rating, difficulty assessment, and
        actionable recommendations.
        """
        with self._lock:
            report = TestReport()

            if not sessions:
                report.outcome = TestOutcome.INCONCLUSIVE
                report.recommendations.append("No session data available for analysis.")
                self._reports.append(report)
                self._report_count += 1
                return report

            report.sessions_analyzed = len(sessions)

            total_frustration = sum(len(s.frustration_events) for s in sessions)
            avg_deaths = sum(s.deaths for s in sessions) / len(sessions)
            avg_completion = sum(s.levels_completed for s in sessions) / len(sessions)
            avg_items = sum(s.items_collected for s in sessions) / len(sessions)
            avg_duration = sum(s.duration for s in sessions) / len(sessions)

            score_components: List[float] = []

            frustration_score = max(0.0, 1.0 - (total_frustration / (len(sessions) * 5.0)))
            score_components.append(frustration_score)

            death_score = max(0.0, 1.0 - (avg_deaths / 20.0))
            score_components.append(death_score)

            completion_score = min(1.0, avg_completion / max(5.0, avg_completion + 0.5))
            score_components.append(completion_score)

            report.overall_score = round(sum(score_components) / len(score_components) * 100.0, 1)

            fun_components = frustration_score * 0.4 + completion_score * 0.3 + min(1.0, avg_items / 50.0) * 0.3
            report.fun_rating = round(fun_components * 100.0, 1)

            if report.overall_score >= 80.0:
                report.difficulty_assessment = "Well-balanced for most player types"
            elif report.overall_score >= 60.0:
                report.difficulty_assessment = "Moderately challenging; some tuning needed"
            elif report.overall_score >= 40.0:
                report.difficulty_assessment = "Significantly too hard or unbalanced"
            else:
                report.difficulty_assessment = "Severe difficulty issues; major rebalancing needed"

            if avg_deaths > 15:
                report.recommendations.append(
                    f"Average deaths per session ({avg_deaths:.1f}) is too high. "
                    "Consider reducing enemy density or damage."
                )

            if total_frustration > len(sessions) * 10:
                report.recommendations.append(
                    "High frustration levels detected. Review puzzle clarity and checkpoint placement."
                )

            if report.fun_rating < 40.0:
                report.recommendations.append(
                    "Low fun rating. Consider adding more rewards, visual feedback, and satisfying mechanics."
                )
            if report.fun_rating >= 70.0:
                report.recommendations.append(
                    "Fun rating is solid. Focus on polishing existing mechanics rather than adding new ones."
                )

            self.detect_pacing_issues(report)
            self.analyze_difficulty_curve(report)

            stuck = self.find_stuck_points(sessions)
            if stuck:
                top_stuck = stuck[:3]
                for sp in top_stuck:
                    report.recommendations.append(
                        f"Players frequently stuck at {sp.position_description} "
                        f"(cause: {sp.cause.replace('_', ' ')}). "
                        f"Consider adding hints or alternative paths."
                    )

            if report.overall_score >= 75.0 and report.fun_rating >= 65.0:
                report.outcome = TestOutcome.PASSED
            elif report.overall_score < 35.0:
                report.outcome = TestOutcome.FAILED
            elif len(report.recommendations) > 5:
                report.outcome = TestOutcome.WARNING
            else:
                report.outcome = TestOutcome.INCONCLUSIVE

            self._reports.append(report)
            self._report_count += 1

            if len(self._reports) > self._MAX_REPORTS:
                self._reports = self._reports[-self._MAX_REPORTS:]

            return report

    def compare_archetypes(self, sessions: List[PlaySession]) -> Dict[str, Any]:
        """
        Compare simulation results across different player archetypes.
        Highlights which player types are best served by the current design
        and which may need additional support.
        """
        grouped: Dict[str, List[PlaySession]] = {}
        for session in sessions:
            if session.profile:
                archetype = session.profile.archetype.value
                grouped.setdefault(archetype, []).append(session)

        comparison: Dict[str, Any] = {
            "archetypes": {},
            "best_served": "",
            "worst_served": "",
            "recommendations": [],
        }

        if not grouped:
            return comparison

        best_score = -1.0
        worst_score = 2.0
        best_archetype = ""
        worst_archetype = ""

        for archetype, archetype_sessions in grouped.items():
            avg_completion = sum(s.levels_completed for s in archetype_sessions) / len(archetype_sessions)
            avg_deaths = sum(s.deaths for s in archetype_sessions) / len(archetype_sessions)
            avg_frustration = sum(len(s.frustration_events) for s in archetype_sessions) / len(archetype_sessions)
            avg_duration = sum(s.duration for s in archetype_sessions) / len(archetype_sessions)

            archetype_score = avg_completion / max(avg_deaths + 1, 1) - avg_frustration * 0.1

            entry = {
                "session_count": len(archetype_sessions),
                "avg_levels_completed": round(avg_completion, 2),
                "avg_deaths": round(avg_deaths, 2),
                "avg_frustration_events": round(avg_frustration, 2),
                "avg_duration": round(avg_duration, 2),
                "score": round(archetype_score, 2),
            }

            comparison["archetypes"][archetype] = entry

            if archetype_score > best_score:
                best_score = archetype_score
                best_archetype = archetype
            if archetype_score < worst_score:
                worst_score = archetype_score
                worst_archetype = archetype

        if best_archetype and worst_archetype:
            comparison["best_served"] = best_archetype
            comparison["worst_served"] = worst_archetype

            if worst_score < best_score * 0.5:
                comparison["recommendations"].append(
                    f"The game heavily favors {best_archetype} players over {worst_archetype} players. "
                    f"Consider adding difficulty options or accessibility features for {worst_archetype}."
                )

        for archetype, entry in comparison["archetypes"].items():
            if entry["avg_deaths"] > 15:
                comparison["recommendations"].append(
                    f"High death count for {archetype} players ({entry['avg_deaths']:.1f} avg). "
                    "Consider adding assist modes or difficulty settings."
                )
            if entry["avg_frustration_events"] > 8:
                comparison["recommendations"].append(
                    f"High frustration for {archetype} players ({entry['avg_frustration_events']:.1f} events). "
                    "Review level design for pain points."
                )

        return comparison

    def get_stats(self) -> Dict[str, Any]:
        """Return simulator statistics including session and report counts."""
        with self._lock:
            archetype_counts: Dict[str, int] = {}
            for session in self._sessions:
                if session.profile:
                    arch = session.profile.archetype.value
                    archetype_counts[arch] = archetype_counts.get(arch, 0) + 1

            outcome_counts: Dict[str, int] = {}
            for report in self._reports:
                outcome = report.outcome.value
                outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

            avg_overall_score = 0.0
            avg_fun_rating = 0.0
            if self._reports:
                avg_overall_score = sum(r.overall_score for r in self._reports) / len(self._reports)
                avg_fun_rating = sum(r.fun_rating for r in self._reports) / len(self._reports)

            return {
                "total_sessions": self._session_count,
                "total_reports": self._report_count,
                "stored_sessions": len(self._sessions),
                "stored_reports": len(self._reports),
                "sessions_by_archetype": archetype_counts,
                "reports_by_outcome": outcome_counts,
                "avg_overall_score": round(avg_overall_score, 2),
                "avg_fun_rating": round(avg_fun_rating, 2),
                "max_sessions": self._MAX_SESSIONS,
                "max_reports": self._MAX_REPORTS,
            }

    def clear(self) -> None:
        """Reset all simulator state."""
        with self._lock:
            self._sessions = []
            self._reports = []
            self._session_count = 0
            self._report_count = 0


def get_playtest_simulator() -> PlaytestSimulator:
    return PlaytestSimulator.get_instance()