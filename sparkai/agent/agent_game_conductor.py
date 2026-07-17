"""
SparkLabs Agent - Game Conductor

The top-level orchestrator that unifies the GameDirector, GameIntelligenceEngine,
and GameDesignReasoner into a single intelligent game creation pipeline.

Architecture:
  GameConductor (Singleton)
    |-- GameDirector           -> produces a playable game with quality metrics
    |-- GameIntelligenceEngine -> analyzes design patterns, player experience, balance
    |-- GameDesignReasoner     -> mathematical balance and difficulty curve analysis

The conductor runs the director's creation pipeline, then layers rich intelligence
analysis on top of the produced game to produce a ConductorResult with both the
playable artifact and a deep IntelligenceReport.

Usage:
    conductor = GameConductor.get_instance()
    conductor.initialize()
    result = conductor.conduct("Design a platformer with double-jump and gem collection")
    # result.html contains the playable game
    # result.intelligence contains the analysis report
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.agent.agent_game_director import (
    GameDirector,
    DirectorResult,
    QualityScore,
    SimulationResult,
    get_game_director,
)
from sparkai.agent.agent_game_intelligence import (
    GameIntelligenceEngine,
    DesignAnalysis,
    QualityEvaluation,
    ImprovementSuggestion,
    PlayerExperienceModel,
    GameBalanceReport,
    PlayerArchetype,
    GameStateSnapshot,
)
from sparkai.agent.agent_game_reasoner import (
    GameDesignReasoner,
    DesignAnalysis as ReasonerAnalysis,
    DesignSuggestion,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class IntelligenceReport:
    """Rich analysis from the intelligence engine and design reasoner."""

    design_patterns: List[str] = field(default_factory=list)
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    opportunities: List[str] = field(default_factory=list)
    threats: List[str] = field(default_factory=list)
    balance_report: Dict[str, Any] = field(default_factory=dict)
    difficulty_curve: List[Dict[str, Any]] = field(default_factory=list)
    player_experience: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[Dict[str, Any]] = field(default_factory=list)
    innovation_score: float = 0.0
    coherence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "design_patterns": list(self.design_patterns),
            "strengths": list(self.strengths),
            "weaknesses": list(self.weaknesses),
            "opportunities": list(self.opportunities),
            "threats": list(self.threats),
            "balance_report": dict(self.balance_report),
            "difficulty_curve": list(self.difficulty_curve),
            "player_experience": dict(self.player_experience),
            "suggestions": list(self.suggestions),
            "innovation_score": round(self.innovation_score, 2),
            "coherence_score": round(self.coherence_score, 2),
        }


@dataclass
class ConductorResult:
    """Complete result from the conductor pipeline."""

    session_id: str
    success: bool
    html: str
    quality: QualityScore
    simulations: List[SimulationResult]
    iterations: int
    refinement_actions: List[str]
    duration_s: float
    error: Optional[str]
    intelligence: Optional[IntelligenceReport]
    metadata: Dict[str, Any]

    def to_dict(self, include_html: bool = True) -> Dict[str, Any]:
        result = {
            "session_id": self.session_id,
            "success": self.success,
            "html_length": len(self.html),
            "quality": self.quality.to_dict(),
            "simulations": [s.to_dict() for s in self.simulations],
            "iterations": self.iterations,
            "refinement_actions": list(self.refinement_actions),
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
            "intelligence": self.intelligence.to_dict() if self.intelligence else None,
            "metadata": dict(self.metadata),
        }
        if include_html:
            result["html"] = self.html
        return result


# =============================================================================
# Game Conductor
# =============================================================================


class GameConductor:
    """
    Top-level orchestrator that unifies the GameDirector, GameIntelligenceEngine,
    and GameDesignReasoner into a single intelligent game creation pipeline.

    The conductor runs the director's creation pipeline to produce a playable
    game, then layers rich intelligence analysis (design patterns, balance,
    difficulty curves, player experience) on top of the produced game.

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GameConductor"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameConductor._instance is not None:
            raise RuntimeError("Use GameConductor.get_instance()")
        self._initialized: bool = False
        self._director: Optional[GameDirector] = None
        self._intelligence: Optional[GameIntelligenceEngine] = None
        self._reasoner: Optional[GameDesignReasoner] = None
        self._session_history: deque = deque(maxlen=50)
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameConductor":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the conductor and acquire subsystem singletons."""
        with self._lock:
            if self._initialized:
                return
            # Acquire singletons without forcing heavy initialization
            try:
                self._director = GameDirector.get_instance()
            except Exception as exc:
                logger.warning("GameDirector acquisition failed: %s", exc)
                self._director = None

            try:
                self._intelligence = GameIntelligenceEngine.get_instance()
            except Exception as exc:
                logger.warning("GameIntelligenceEngine acquisition failed: %s", exc)
                self._intelligence = None

            try:
                self._reasoner = GameDesignReasoner.get_instance()
            except Exception as exc:
                logger.warning("GameDesignReasoner acquisition failed: %s", exc)
                self._reasoner = None

            self._initialized = True
            logger.info("GameConductor initialized")

    def conduct(
        self,
        prompt: str,
        genre_hint: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> ConductorResult:
        """
        Run the full conductor pipeline:
        1. Call GameDirector.direct() to create the game
        2. Extract game config from the director's metadata
        3. Run intelligence engine analysis (patterns, player experience)
        4. Run design reasoner analysis (balance, difficulty curve)
        5. Combine into IntelligenceReport
        6. Return ConductorResult with both game and intelligence
        """
        if not self._initialized:
            self.initialize()

        session_id = f"conductor_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        # Phase 1: Direct the game creation
        director = self._director or GameDirector.get_instance()
        director_result = director.direct(
            prompt, genre_hint=genre_hint, max_iterations=max_iterations
        )

        # Phases 2-5: Run intelligence analysis on the produced game
        intelligence_report: Optional[IntelligenceReport] = None
        if director_result.success:
            try:
                game_config_dict = self._build_game_config(
                    director_result, prompt, genre_hint
                )
                mechanics = self._build_mechanics(director_result)
                intelligence_report = self._analyze_intelligence(
                    game_config_dict, mechanics
                )
            except Exception as exc:
                logger.exception(
                    "GameConductor intelligence analysis failed: %s", exc
                )
                intelligence_report = None

        duration = time.time() - start_time

        # Build combined metadata
        combined_metadata: Dict[str, Any] = dict(director_result.metadata)
        combined_metadata.update(
            {
                "conductor_session_id": session_id,
                "prompt": prompt,
                "genre_hint": genre_hint,
                "max_iterations": max_iterations,
                "intelligence_available": intelligence_report is not None,
            }
        )

        result = ConductorResult(
            session_id=session_id,
            success=director_result.success,
            html=director_result.html,
            quality=director_result.quality,
            simulations=director_result.simulations,
            iterations=director_result.iterations,
            refinement_actions=director_result.refinement_actions,
            duration_s=round(duration, 3),
            error=director_result.error,
            intelligence=intelligence_report,
            metadata=combined_metadata,
        )

        # Track session history
        with self._lock:
            self._session_history.append(
                {
                    "session_id": session_id,
                    "director_session_id": director_result.session_id,
                    "prompt": prompt[:100],
                    "success": director_result.success,
                    "quality": director_result.quality.overall,
                    "iterations": director_result.iterations,
                    "duration_s": round(duration, 3),
                    "intelligence_available": intelligence_report is not None,
                    "timestamp": time.time(),
                }
            )

        return result

    def _analyze_intelligence(
        self,
        game_config_dict: Dict[str, Any],
        mechanics: Dict[str, Any],
    ) -> IntelligenceReport:
        """Run intelligence engine and reasoner analysis."""
        report = IntelligenceReport()

        # --- Intelligence Engine: design patterns ---
        try:
            intelligence = self._intelligence or GameIntelligenceEngine.get_instance()
            patterns = intelligence.detect_patterns(game_config_dict)
            report.design_patterns = [p.value for p in patterns]
        except Exception as exc:
            logger.warning("Pattern detection failed: %s", exc)

        # --- Intelligence Engine: SWOT via game state analysis ---
        design_analysis: Optional[DesignAnalysis] = None
        try:
            intelligence = self._intelligence or GameIntelligenceEngine.get_instance()
            snapshot = self._build_state_snapshot(game_config_dict)
            design_analysis = intelligence.analyze_game_state(snapshot)
            report.strengths = list(design_analysis.strengths)
            report.weaknesses = list(design_analysis.weaknesses)
            report.opportunities = list(design_analysis.opportunities)
            report.threats = list(design_analysis.threats)
        except Exception as exc:
            logger.warning("Game state analysis failed: %s", exc)

        # --- Intelligence Engine: balance report and difficulty curve ---
        try:
            intelligence = self._intelligence or GameIntelligenceEngine.get_instance()
            balance = intelligence.generate_balance_report(mechanics)
            report.balance_report = balance.to_dict()
            # Convert difficulty curve tuples into level-by-level dicts
            report.difficulty_curve = [
                {"level": lvl, "difficulty": diff}
                for lvl, diff in balance.difficulty_curve
            ]
        except Exception as exc:
            logger.warning("Balance report generation failed: %s", exc)

        # --- Intelligence Engine: player experience modeling ---
        try:
            intelligence = self._intelligence or GameIntelligenceEngine.get_instance()
            player_experience: Dict[str, Any] = {}
            for archetype in (
                PlayerArchetype.CASUAL,
                PlayerArchetype.HARDCORE,
                PlayerArchetype.ACHIEVER,
                PlayerArchetype.EXPLORER,
            ):
                model = intelligence.model_player_experience(
                    archetype, game_config_dict
                )
                player_experience[archetype.value] = model.to_dict()
            report.player_experience = player_experience
        except Exception as exc:
            logger.warning("Player experience modeling failed: %s", exc)

        # --- Intelligence Engine: improvement suggestions ---
        try:
            intelligence = self._intelligence or GameIntelligenceEngine.get_instance()
            if design_analysis is not None:
                suggestions = intelligence.generate_suggestions(design_analysis)
                for suggestion in suggestions:
                    report.suggestions.append(suggestion.to_dict())
        except Exception as exc:
            logger.warning("Suggestion generation failed: %s", exc)

        # --- Design Reasoner: design analysis across aspects ---
        try:
            reasoner = self._reasoner or GameDesignReasoner.get_instance()
            game_state = self._build_game_state(game_config_dict, mechanics)
            aspects = [
                "balance",
                "difficulty",
                "progression",
                "economy",
                "pacing",
                "accessibility",
                "replayability",
                "engagement",
            ]
            analyses = reasoner.analyze_game_design(game_state, aspects=aspects)
            for analysis in analyses:
                for suggestion_text in analysis.suggestions:
                    report.suggestions.append(
                        {
                            "source": "design_reasoner",
                            "aspect": analysis.aspect.value,
                            "suggestion": suggestion_text,
                            "confidence": analysis.confidence.value,
                            "analysis": analysis.analysis,
                        }
                    )
        except Exception as exc:
            logger.warning("Design reasoner analysis failed: %s", exc)

        # --- Scores: prefer intelligence engine scores, fall back to heuristics ---
        try:
            if design_analysis is not None:
                report.innovation_score = float(design_analysis.innovation_score)
                report.coherence_score = float(design_analysis.coherence_score)
            else:
                report.innovation_score = self._compute_innovation_score(report)
                report.coherence_score = self._compute_coherence_score(report)
        except Exception as exc:
            logger.warning("Score computation failed: %s", exc)

        return report

    # ---- Helpers: build analysis inputs from the director result ----

    def _build_game_config(
        self,
        director_result: DirectorResult,
        prompt: str,
        genre_hint: Optional[str],
    ) -> Dict[str, Any]:
        """
        Build a game configuration dict from the director's metadata.

        The dict is consumed by pattern detection and player experience
        modeling, which scan its JSON representation for indicator words.
        Including the prompt, genre, and title ensures rich keyword coverage.
        """
        metadata = director_result.metadata or {}
        quality = director_result.quality

        genre = (
            metadata.get("genre")
            or genre_hint
            or "custom"
        )
        title = metadata.get("title") or "Untitled Game"

        # Derive feature keywords from quality dimensions so pattern detection
        # has meaningful signal even when the synthesizer did not emit details.
        features: List[str] = []
        if quality.engagement >= 6.0:
            features.extend(["rewards", "score", "combo", "multiplier", "achievement"])
        if quality.variety >= 5.0:
            features.extend(
                ["diverse_environments", "multiple_enemy_types", "varied_levels"]
            )
        if quality.pacing >= 6.0:
            features.extend(["smooth_difficulty", "well_paced_levels"])
        if quality.coherence >= 6.0:
            features.extend(["cohesive_theme", "consistent_narrative"])
        if quality.completeness >= 6.0:
            features.extend(["collectibles", "unlock", "progression", "upgrade"])

        # Pull simulation notes into the config so analysis can see them
        simulation_notes: List[str] = []
        for sim in director_result.simulations:
            simulation_notes.extend(sim.notes)

        return {
            "title": title,
            "genre": genre,
            "prompt": prompt,
            "features": features,
            "simulation_notes": simulation_notes,
            "quality": quality.to_dict(),
            "iterations": director_result.iterations,
            "refinement_actions": director_result.refinement_actions,
        }

    def _build_mechanics(
        self, director_result: DirectorResult
    ) -> Dict[str, Any]:
        """
        Build a mechanics dict for the balance report generator.

        The balance report expects numeric-ish entries (it assigns each
        mechanic a balance score) plus an optional num_levels used to size
        the difficulty curve.
        """
        quality = director_result.quality

        # Estimate level count from variety and simulation signals
        sim_count = len(director_result.simulations)
        avg_completion = 0.0
        if director_result.simulations:
            avg_completion = sum(
                s.completion_rate for s in director_result.simulations
            ) / len(director_result.simulations)

        num_levels = max(
            5,
            int(quality.variety) + sim_count + 3,
        )

        return {
            "num_levels": num_levels,
            "combat": round(quality.difficulty / 10.0, 2),
            "economy": round(quality.completeness / 10.0, 2),
            "progression": round(quality.pacing / 10.0, 2),
            "exploration": round(quality.variety / 10.0, 2),
            "narrative": round(quality.coherence / 10.0, 2),
            "engagement_loop": round(quality.engagement / 10.0, 2),
            "avg_completion": round(avg_completion, 3),
        }

    def _build_state_snapshot(
        self, game_config_dict: Dict[str, Any]
    ) -> GameStateSnapshot:
        """
        Build a synthetic GameStateSnapshot representing the produced game
        in its gameplay phase, so the intelligence engine can derive SWOT.
        """
        quality_dict = game_config_dict.get("quality", {})
        engagement = float(quality_dict.get("engagement", 5.0))
        variety = float(quality_dict.get("variety", 5.0))

        # Heuristic entity and interaction counts derived from quality signals
        entities_count = int(variety * 5) + 10
        interaction_count = int(engagement * 10) + 5

        return GameStateSnapshot(
            active_scene=game_config_dict.get("title", "gameplay_scene"),
            game_phase="gameplay",
            entities_count=entities_count,
            fps=60.0,
            memory_usage=512.0,
            interaction_count=interaction_count,
        )

    def _build_game_state(
        self,
        game_config_dict: Dict[str, Any],
        mechanics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build a game state dict for the design reasoner.

        Each aspect analyzer reads specific keys; we derive them from the
        quality scores and mechanics so the reasoner has consistent input
        across all aspects.
        """
        quality_dict = game_config_dict.get("quality", {})
        difficulty = float(quality_dict.get("difficulty", 5.0)) / 10.0
        pacing = float(quality_dict.get("pacing", 5.0)) / 10.0
        variety = float(quality_dict.get("variety", 5.0)) / 10.0
        engagement = float(quality_dict.get("engagement", 5.0)) / 10.0
        completeness = float(quality_dict.get("completeness", 5.0)) / 10.0
        coherence = float(quality_dict.get("coherence", 5.0)) / 10.0

        num_levels = int(mechanics.get("num_levels", 10))
        avg_completion = float(mechanics.get("avg_completion", 0.5))

        return {
            # Balance aspect
            "options_count": max(3, int(variety * 10)),
            "viable_options": max(1, int(variety * 8)),
            # Difficulty aspect
            "difficulty": round(difficulty, 3),
            "ramp_smoothness": round(pacing, 3),
            # Progression aspect
            "unlocks_per_hour": max(1, int(engagement * 8)),
            "total_levels": num_levels,
            # Economy aspect
            "sink_faucet_ratio": round(0.5 + coherence * 0.3, 3),
            "inflation": round(max(0.0, 0.1 - coherence * 0.08), 3),
            # Pacing aspect
            "action_density": round(engagement, 3),
            "rest_periods": max(1, int((1.0 - engagement) * 6)),
            # Accessibility aspect
            "difficulty_presets": 2 if completeness >= 0.6 else 1,
            "input_options": 3 if variety >= 0.5 else 2,
            # Replayability aspect
            "procedural_content": round(variety, 3),
            "branching_paths": max(2, int(variety * 5)),
            # Engagement aspect
            "flow_state_uptime": round(engagement, 3),
            "retention_rate": round(max(avg_completion, completeness), 3),
            # Frustration signals
            "frustration_indicators": []
            if difficulty <= 0.7 else ["high_difficulty"],
        }

    def _compute_innovation_score(self, report: IntelligenceReport) -> float:
        """Heuristic innovation score derived from pattern diversity."""
        pattern_count = len(report.design_patterns)
        score = 0.3 + pattern_count * 0.08
        return round(max(0.0, min(1.0, score)), 2)

    def _compute_coherence_score(self, report: IntelligenceReport) -> float:
        """Heuristic coherence score derived from strengths vs weaknesses."""
        strengths = len(report.strengths)
        weaknesses = len(report.weaknesses)
        score = 0.5 + strengths * 0.05 - weaknesses * 0.07
        return round(max(0.0, min(1.0, score)), 2)

    # ---- Status and history ----

    def get_status(self) -> Dict[str, Any]:
        """Return conductor status information."""
        with self._lock:
            return {
                "status": "ready" if self._initialized else "not_initialized",
                "sessions_completed": len(self._session_history),
                "director_available": self._director is not None,
                "intelligence_available": self._intelligence is not None,
                "reasoner_available": self._reasoner is not None,
                "recent_sessions": list(self._session_history)[-5:],
            }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the conductor's session history."""
        with self._lock:
            return list(self._session_history)


# =============================================================================
# Module-level convenience
# =============================================================================


def get_game_conductor() -> GameConductor:
    """Convenience function to access the singleton GameConductor."""
    return GameConductor.get_instance()
