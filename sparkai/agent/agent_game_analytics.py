"""
SparkLabs Agent - Game Analytics

An AI agent that simulates virtual players to predict game engagement
metrics. Uses Monte Carlo simulation with different player personas
(casual, regular, hardcore, speedrunner) to model how each type would
experience the game, producing predictions for session length,
completion rate, retention, and churn risk.

This is a core AI-native capability: traditional engines require live
playtesting to gather metrics, but an AI-native engine can predict
player behavior from the game design itself.

Architecture:
  GameAnalytics (singleton)
    |-- DesignExtractor  -> extracts difficulty/pacing from HTML
    |-- PlayerPersona    -> models different player types
    |-- PlaySimulator    -> Monte Carlo simulation of playthroughs
    |-- MetricsAggregator -> aggregates results across personas
    |-- ReportGenerator  -> produces engagement predictions

Player Personas:
  - casual:      low skill (0.3), low persistence (0.3), short sessions
  - regular:     medium skill (0.5), medium persistence (0.6)
  - hardcore:    high skill (0.8), high persistence (0.9), completionist
  - speedrunner: very high skill (0.95), high persistence (0.85), fast

Predicted Metrics:
  - avg_session_length:  estimated minutes per session
  - completion_rate:     percentage of players who finish
  - avg_death_count:     average deaths per playthrough
  - d1_retention:        day-1 retention probability
  - d7_retention:        day-7 retention probability
  - churn_risk:          probability of player churning
  - engagement_score:    overall engagement (0-100)
  - difficulty_perception: how players perceive difficulty
"""

from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class PlayerPersona:
    """A simulated player persona."""
    name: str
    skill: float  # 0.0 to 1.0
    persistence: float  # 0.0 to 1.0
    patience: float  # 0.0 to 1.0
    speed_multiplier: float  # how fast they play (1.0 = normal)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "skill": round(self.skill, 2),
            "persistence": round(self.persistence, 2),
            "patience": round(self.patience, 2),
            "speed_multiplier": self.speed_multiplier,
            "description": self.description,
        }


@dataclass
class PlaythroughResult:
    """Result of a single simulated playthrough."""
    persona: str
    completed: bool
    levels_cleared: int
    total_levels: int
    deaths: int
    session_length_min: float
    final_score: int
    quit_reason: str  # "completed", "frustration", "boredom", "time"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "completed": self.completed,
            "levels_cleared": self.levels_cleared,
            "total_levels": self.total_levels,
            "deaths": self.deaths,
            "session_length_min": round(self.session_length_min, 2),
            "final_score": self.final_score,
            "quit_reason": self.quit_reason,
        }


@dataclass
class PersonaMetrics:
    """Aggregated metrics for a single persona."""
    persona: str
    playthroughs: int
    completion_rate: float
    avg_session_length: float
    avg_deaths: float
    avg_score: float
    avg_levels_cleared: float
    d1_retention: float
    d7_retention: float
    churn_risk: float
    engagement_score: float
    difficulty_perception: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "persona": self.persona,
            "playthroughs": self.playthroughs,
            "completion_rate": round(self.completion_rate, 3),
            "avg_session_length": round(self.avg_session_length, 2),
            "avg_deaths": round(self.avg_deaths, 2),
            "avg_score": round(self.avg_score, 1),
            "avg_levels_cleared": round(self.avg_levels_cleared, 2),
            "d1_retention": round(self.d1_retention, 3),
            "d7_retention": round(self.d7_retention, 3),
            "churn_risk": round(self.churn_risk, 3),
            "engagement_score": round(self.engagement_score, 1),
            "difficulty_perception": self.difficulty_perception,
        }


@dataclass
class AnalyticsResult:
    """Complete analytics result."""
    session_id: str
    success: bool
    genre: str
    design_params: Dict[str, Any]
    persona_metrics: List[PersonaMetrics]
    overall_metrics: Dict[str, Any]
    recommendations: List[str]
    sample_playthroughs: List[PlaythroughResult]
    duration_s: float
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "success": self.success,
            "genre": self.genre,
            "design_params": self.design_params,
            "persona_metrics": [m.to_dict() for m in self.persona_metrics],
            "overall_metrics": self.overall_metrics,
            "recommendations": self.recommendations,
            "sample_playthroughs": [p.to_dict() for p in self.sample_playthroughs],
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
        }


# ---------------------------------------------------------------------------
# Default Player Personas
# ---------------------------------------------------------------------------

DEFAULT_PERSONAS: List[PlayerPersona] = [
    PlayerPersona(
        name="casual",
        skill=0.30,
        persistence=0.30,
        patience=0.40,
        speed_multiplier=0.7,
        description="Plays for fun, gives up easily on hard sections",
    ),
    PlayerPersona(
        name="regular",
        skill=0.55,
        persistence=0.60,
        patience=0.65,
        speed_multiplier=1.0,
        description="Average gamer, moderate persistence",
    ),
    PlayerPersona(
        name="hardcore",
        skill=0.80,
        persistence=0.90,
        patience=0.85,
        speed_multiplier=1.1,
        description="Skilled player, high persistence, aims for completion",
    ),
    PlayerPersona(
        name="speedrunner",
        skill=0.95,
        persistence=0.85,
        patience=0.70,
        speed_multiplier=1.5,
        description="Elite player, minimal deaths, fast completion",
    ),
]


# ---------------------------------------------------------------------------
# Game Analytics Singleton
# ---------------------------------------------------------------------------


class GameAnalytics:
    """AI agent that predicts game engagement metrics via simulation.

    Analyzes game HTML to extract design parameters (difficulty, pacing,
    content density), then runs Monte Carlo simulations with different
    player personas to predict session length, completion rate, retention,
    and churn risk.
    """

    _instance: Optional["GameAnalytics"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "GameAnalytics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameAnalytics":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls()
        return cls._instance  # type: ignore[return-value]

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._inner_lock: threading.RLock = threading.RLock()
            self._history: List[AnalyticsResult] = []
            self._total_runs: int = 0
            self._initialized = True

    # -- Public API --------------------------------------------------------

    def analyze(
        self,
        html: str = "",
        genre: str = "",
        personas: Optional[List[PlayerPersona]] = None,
        simulations_per_persona: int = 50,
    ) -> AnalyticsResult:
        """Analyze a game and predict engagement metrics.

        Args:
            html: Game HTML for design parameter extraction.
            genre: Optional genre hint.
            personas: Optional custom personas. Uses DEFAULT_PERSONAS if None.
            simulations_per_persona: Number of Monte Carlo simulations per persona.

        Returns:
            AnalyticsResult with per-persona and overall metrics.
        """
        import time
        import uuid
        start = time.time()
        session_id = f"anly_{uuid.uuid4().hex[:12]}"

        try:
            # Extract design parameters from HTML
            design_params = self._extract_design_params(html, genre)
            if not genre:
                genre = design_params.get("genre", "default")

            # Use default personas if none provided
            if personas is None:
                personas = DEFAULT_PERSONAS

            # Run simulations for each persona
            persona_metrics: List[PersonaMetrics] = []
            all_playthroughs: List[PlaythroughResult] = []

            for persona in personas:
                playthroughs = self._simulate_persona(
                    persona, design_params, simulations_per_persona,
                )
                metrics = self._aggregate_persona_metrics(persona, playthroughs)
                persona_metrics.append(metrics)
                # Keep a few sample playthroughs
                all_playthroughs.extend(playthroughs[:3])

            # Calculate overall metrics (weighted average across personas)
            overall = self._calculate_overall_metrics(persona_metrics, design_params)

            # Generate recommendations
            recommendations = self._generate_recommendations(
                persona_metrics, overall, design_params,
            )

            result = AnalyticsResult(
                session_id=session_id,
                success=True,
                genre=genre,
                design_params=design_params,
                persona_metrics=persona_metrics,
                overall_metrics=overall,
                recommendations=recommendations,
                sample_playthroughs=all_playthroughs[:12],
                duration_s=time.time() - start,
            )

            with self._inner_lock:
                self._history.append(result)
                if len(self._history) > 30:
                    self._history.pop(0)
                self._total_runs += 1

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return AnalyticsResult(
                session_id=session_id,
                success=False,
                genre=genre,
                design_params={},
                persona_metrics=[],
                overall_metrics={},
                recommendations=[],
                sample_playthroughs=[],
                duration_s=time.time() - start,
                error=str(e),
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        with self._inner_lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def get_status(self) -> Dict[str, Any]:
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_runs": self._total_runs,
                "personas": [p.name for p in DEFAULT_PERSONAS],
            }

    # -- Design Parameter Extraction ---------------------------------------

    def _extract_design_params(self, html: str, genre: str = "") -> Dict[str, Any]:
        """Extract game design parameters from HTML."""
        import re

        params: Dict[str, Any] = {
            "html_size": len(html),
            "genre": genre or "default",
        }

        html_lower = html.lower()

        # Extract CONFIG values
        config_patterns = {
            "enemy_speed": re.compile(r'"enemySpeed":\s*([0-9.]+)', re.I),
            "move_speed": re.compile(r'"moveSpeed":\s*([0-9.]+)', re.I),
            "gravity": re.compile(r'"gravity":\s*([0-9.]+)', re.I),
            "lives": re.compile(r'"lives":\s*(\d+)', re.I),
            "enemy_count": re.compile(r'"enemyCount":\s*(\d+)', re.I),
            "collectible_count": re.compile(r'"collectibleCount":\s*(\d+)', re.I),
        }
        for key, pattern in config_patterns.items():
            match = pattern.search(html)
            if match:
                try:
                    val = float(match.group(1))
                    params[key] = val if key in ("enemy_speed", "move_speed", "gravity") else int(val)
                except ValueError:
                    pass

        # Count levels
        level_matches = re.findall(r'loadLevel\s*\(', html, re.I)
        params["level_count"] = max(1, len(level_matches))

        # Detect features
        params["has_save_load"] = "localstorage" in html_lower
        params["has_achievements"] = "achievement" in html_lower
        params["has_adaptive"] = "adaptive" in html_lower
        params["has_tutorial"] = "tutorial" in html_lower or "hint" in html_lower

        # Calculate difficulty score (0-1)
        enemy_speed = params.get("enemy_speed", 1.2)
        lives = params.get("lives", 3)
        enemy_count = params.get("enemy_count", 3)
        difficulty = 0.0
        difficulty += min(0.3, enemy_speed / 10.0)
        difficulty += min(0.2, enemy_count / 20.0)
        difficulty += max(0.0, 0.3 - lives * 0.06)  # fewer lives = harder
        difficulty = min(1.0, difficulty)
        params["difficulty_score"] = round(difficulty, 3)

        # Calculate pacing score (0-1)
        level_count = params["level_count"]
        pacing = min(1.0, level_count / 10.0)
        params["pacing_score"] = round(pacing, 3)

        # Content density
        collectibles = params.get("collectible_count", 5)
        density = min(1.0, (collectibles + enemy_count) / 20.0)
        params["content_density"] = round(density, 3)

        return params

    # -- Simulation --------------------------------------------------------

    def _simulate_persona(
        self,
        persona: PlayerPersona,
        design: Dict[str, Any],
        num_simulations: int,
    ) -> List[PlaythroughResult]:
        """Run Monte Carlo simulations for a single persona."""
        results: List[PlaythroughResult] = []
        rng = random.Random(hash(persona.name) & 0xFFFFFFFF)

        level_count = int(design.get("level_count", 5))
        difficulty = design.get("difficulty_score", 0.5)
        lives = int(design.get("lives", 3))
        content_density = design.get("content_density", 0.5)

        for _ in range(num_simulations):
            result = self._simulate_single_playthrough(
                persona, level_count, difficulty, lives, content_density, rng,
            )
            results.append(result)

        return results

    def _simulate_single_playthrough(
        self,
        persona: PlayerPersona,
        total_levels: int,
        difficulty: float,
        starting_lives: int,
        content_density: float,
        rng: random.Random,
    ) -> PlaythroughResult:
        """Simulate a single playthrough."""
        levels_cleared = 0
        deaths = 0
        lives = starting_lives
        session_time = 0.0  # in minutes
        score = 0
        quit_reason = "completed"

        for level in range(total_levels):
            # Level difficulty increases with level number
            level_difficulty = difficulty + (level * 0.05)
            level_difficulty = min(1.0, level_difficulty)

            # Probability of clearing the level
            skill_gap = level_difficulty - persona.skill
            if skill_gap <= 0:
                clear_prob = 0.95 - (level * 0.01)
            else:
                clear_prob = max(0.1, 0.7 - skill_gap * 0.8)

            # Time per level (affected by speed multiplier and difficulty)
            base_time = 2.0 + (level_difficulty * 3.0)
            level_time = base_time / persona.speed_multiplier
            # Add variance
            level_time *= rng.uniform(0.8, 1.3)

            # Death probability
            death_prob = max(0.0, skill_gap * 0.6)
            death_prob = min(0.8, death_prob)

            # Simulate level attempts
            level_cleared = False
            attempts = 0
            max_attempts = int(5 + persona.patience * 10)

            while attempts < max_attempts:
                attempts += 1
                session_time += level_time / max(1, attempts)

                # Score from collecting items
                score += int(content_density * 100 * rng.uniform(0.5, 1.5))

                if rng.random() < clear_prob:
                    level_cleared = True
                    levels_cleared += 1
                    break
                else:
                    # Failed attempt
                    if rng.random() < death_prob:
                        deaths += 1
                        lives -= 1
                        if lives <= 0:
                            # Game over
                            quit_reason = "frustration"
                            return PlaythroughResult(
                                persona=persona.name,
                                completed=False,
                                levels_cleared=levels_cleared,
                                total_levels=total_levels,
                                deaths=deaths,
                                session_length_min=session_time,
                                final_score=score,
                                quit_reason=quit_reason,
                            )

                    # Check if player quits due to frustration
                    frustration = (attempts / max_attempts) * (1.0 - persona.patience)
                    if rng.random() < frustration * 0.3:
                        quit_reason = "frustration"
                        return PlaythroughResult(
                            persona=persona.name,
                            completed=False,
                            levels_cleared=levels_cleared,
                            total_levels=total_levels,
                            deaths=deaths,
                            session_length_min=session_time,
                            final_score=score,
                            quit_reason=quit_reason,
                        )

            if not level_cleared:
                # Ran out of attempts
                if rng.random() > persona.persistence:
                    quit_reason = "boredom"
                    return PlaythroughResult(
                        persona=persona.name,
                        completed=False,
                        levels_cleared=levels_cleared,
                        total_levels=total_levels,
                        deaths=deaths,
                        session_length_min=session_time,
                        final_score=score,
                        quit_reason=quit_reason,
                    )
                else:
                    # Skip level (if game allows) or end
                    quit_reason = "frustration"
                    return PlaythroughResult(
                        persona=persona.name,
                        completed=False,
                        levels_cleared=levels_cleared,
                        total_levels=total_levels,
                        deaths=deaths,
                        session_length_min=session_time,
                        final_score=score,
                        quit_reason=quit_reason,
                    )

            # Check for boredom quit (session too long)
            if session_time > 30.0 and rng.random() > persona.patience:
                quit_reason = "time"
                return PlaythroughResult(
                    persona=persona.name,
                    completed=False,
                    levels_cleared=levels_cleared,
                    total_levels=total_levels,
                    deaths=deaths,
                    session_length_min=session_time,
                    final_score=score,
                    quit_reason=quit_reason,
                )

        # Completed all levels
        return PlaythroughResult(
            persona=persona.name,
            completed=True,
            levels_cleared=levels_cleared,
            total_levels=total_levels,
            deaths=deaths,
            session_length_min=session_time,
            final_score=score,
            quit_reason="completed",
        )

    # -- Metrics Aggregation -----------------------------------------------

    def _aggregate_persona_metrics(
        self,
        persona: PlayerPersona,
        playthroughs: List[PlaythroughResult],
    ) -> PersonaMetrics:
        """Aggregate simulation results for a persona."""
        n = len(playthroughs)
        if n == 0:
            return PersonaMetrics(
                persona=persona.name, playthroughs=0,
                completion_rate=0, avg_session_length=0, avg_deaths=0,
                avg_score=0, avg_levels_cleared=0,
                d1_retention=0, d7_retention=0, churn_risk=1.0,
                engagement_score=0, difficulty_perception="unknown",
            )

        completed = sum(1 for p in playthroughs if p.completed)
        completion_rate = completed / n
        avg_session = sum(p.session_length_min for p in playthroughs) / n
        avg_deaths = sum(p.deaths for p in playthroughs) / n
        avg_score = sum(p.final_score for p in playthroughs) / n
        avg_levels = sum(p.levels_cleared for p in playthroughs) / n

        # Frustration rate
        frustrated = sum(1 for p in playthroughs if p.quit_reason == "frustration")
        frustration_rate = frustrated / n

        # D1 retention: probability of returning next day
        # Based on completion rate, session length, and frustration
        d1 = 0.3 + (completion_rate * 0.3) + (min(avg_session, 20) / 20 * 0.2)
        d1 -= (frustration_rate * 0.3)
        d1 = max(0.05, min(0.95, d1))

        # D7 retention: decay from D1
        d7 = d1 * 0.5 + (completion_rate * 0.15)
        d7 = max(0.02, min(0.6, d7))

        # Churn risk: inverse of engagement
        churn = 1.0 - d1
        churn = max(0.05, min(0.95, churn))

        # Engagement score (0-100)
        engagement = (
            (completion_rate * 30) +
            (min(avg_session, 20) / 20 * 25) +
            (d1 * 25) +
            ((1 - frustration_rate) * 20)
        )
        engagement = max(0, min(100, engagement))

        # Difficulty perception
        if avg_deaths > 5 and frustration_rate > 0.4:
            diff_perception = "very hard"
        elif avg_deaths > 3 or frustration_rate > 0.25:
            diff_perception = "hard"
        elif avg_deaths > 1.5:
            diff_perception = "moderate"
        elif avg_deaths > 0.5:
            diff_perception = "easy"
        else:
            diff_perception = "very easy"

        return PersonaMetrics(
            persona=persona.name,
            playthroughs=n,
            completion_rate=completion_rate,
            avg_session_length=avg_session,
            avg_deaths=avg_deaths,
            avg_score=avg_score,
            avg_levels_cleared=avg_levels,
            d1_retention=d1,
            d7_retention=d7,
            churn_risk=churn,
            engagement_score=engagement,
            difficulty_perception=diff_perception,
        )

    def _calculate_overall_metrics(
        self,
        persona_metrics: List[PersonaMetrics],
        design: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate overall metrics across all personas."""
        n = len(persona_metrics)
        if n == 0:
            return {}

        # Weighted average (casual: 40%, regular: 35%, hardcore: 20%, speedrunner: 5%)
        weights = {"casual": 0.40, "regular": 0.35, "hardcore": 0.20, "speedrunner": 0.05}
        total_weight = 0.0
        weighted_completion = 0.0
        weighted_session = 0.0
        weighted_deaths = 0.0
        weighted_d1 = 0.0
        weighted_d7 = 0.0
        weighted_churn = 0.0
        weighted_engagement = 0.0

        for m in persona_metrics:
            w = weights.get(m.persona, 0.25)
            total_weight += w
            weighted_completion += m.completion_rate * w
            weighted_session += m.avg_session_length * w
            weighted_deaths += m.avg_deaths * w
            weighted_d1 += m.d1_retention * w
            weighted_d7 += m.d7_retention * w
            weighted_churn += m.churn_risk * w
            weighted_engagement += m.engagement_score * w

        if total_weight > 0:
            weighted_completion /= total_weight
            weighted_session /= total_weight
            weighted_deaths /= total_weight
            weighted_d1 /= total_weight
            weighted_d7 /= total_weight
            weighted_churn /= total_weight
            weighted_engagement /= total_weight

        # Overall difficulty perception
        diff_perceptions = [m.difficulty_perception for m in persona_metrics]
        if "very hard" in diff_perceptions:
            overall_difficulty = "challenging"
        elif "hard" in diff_perceptions:
            overall_difficulty = "moderate-hard"
        elif "moderate" in diff_perceptions:
            overall_difficulty = "balanced"
        else:
            overall_difficulty = "easy"

        return {
            "avg_completion_rate": round(weighted_completion, 3),
            "avg_session_length": round(weighted_session, 2),
            "avg_deaths": round(weighted_deaths, 2),
            "d1_retention": round(weighted_d1, 3),
            "d7_retention": round(weighted_d7, 3),
            "churn_risk": round(weighted_churn, 3),
            "engagement_score": round(weighted_engagement, 1),
            "difficulty_perception": overall_difficulty,
            "design_difficulty": design.get("difficulty_score", 0.5),
            "level_count": design.get("level_count", 1),
        }

    def _generate_recommendations(
        self,
        persona_metrics: List[PersonaMetrics],
        overall: Dict[str, Any],
        design: Dict[str, Any],
    ) -> List[str]:
        """Generate actionable recommendations based on analytics."""
        recs: List[str] = []

        # High churn risk
        if overall.get("churn_risk", 0) > 0.6:
            recs.append(
                f"High churn risk ({overall['churn_risk']:.0%}). "
                f"Consider reducing difficulty or adding more tutorials."
            )

        # Low completion rate
        if overall.get("avg_completion_rate", 0) < 0.3:
            recs.append(
                f"Low completion rate ({overall['avg_completion_rate']:.0%}). "
                f"Players are not finishing the game. Check difficulty curve."
            )

        # High death count
        if overall.get("avg_deaths", 0) > 4:
            recs.append(
                f"High average deaths ({overall['avg_deaths']:.1f}). "
                f"Consider adding checkpoints or reducing enemy speed."
            )

        # Low session length
        if overall.get("avg_session_length", 0) < 3.0:
            recs.append(
                f"Short sessions ({overall['avg_session_length']:.1f} min). "
                f"Add more content or engagement hooks to extend play time."
            )

        # Low D1 retention
        if overall.get("d1_retention", 0) < 0.3:
            recs.append(
                f"Low D1 retention ({overall['d1_retention']:.0%}). "
                f"First-session experience needs improvement."
            )

        # Casual player frustration
        casual_metrics = next((m for m in persona_metrics if m.persona == "casual"), None)
        if casual_metrics and casual_metrics.churn_risk > 0.7:
            recs.append(
                f"Casual players have {casual_metrics.churn_risk:.0%} churn risk. "
                f"Add an easy mode or adaptive difficulty."
            )

        # Speedrunner boredom
        speedrunner_metrics = next((m for m in persona_metrics if m.persona == "speedrunner"), None)
        if speedrunner_metrics and speedrunner_metrics.completion_rate > 0.9 and speedrunner_metrics.avg_deaths < 1:
            recs.append(
                "Game may be too easy for elite players. "
                "Consider adding a hard mode or time trials."
            )

        # Low engagement
        if overall.get("engagement_score", 0) < 40:
            recs.append(
                f"Low engagement score ({overall['engagement_score']:.0f}/100). "
                f"Review core loop and add more rewarding feedback systems."
            )

        # No recommendations if everything looks good
        if not recs:
            recs.append(
                "Metrics look healthy across all player personas. "
                "No critical issues detected."
            )

        return recs


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_game_analytics() -> GameAnalytics:
    """Return the singleton GameAnalytics instance."""
    return GameAnalytics.get_instance()
