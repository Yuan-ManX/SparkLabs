"""
SparkLabs Agent - AI Game Director

The creative intelligence that directs the entire AI-native game creation
lifecycle. Combines a tool-use registry with function calling,
a simulation engine for world evaluation, and an iteration
loop for iterative refinement into a single director that can
autonomously produce, evaluate, and refine games.

Architecture:
  GameDirector (Singleton)
    |-- ToolRegistry      -> named tools the director can invoke
    |-- SimulationEngine  -> simulates playtest sessions for evaluation
    |-- IterationLoop     -> generate -> evaluate -> refine -> regenerate
    |-- QualityMetrics    -> engagement, difficulty, variety, coherence
    |-- StrategySelector  -> chooses generation strategy based on prompt

The director is the primary interface for "make a great game" workflows.
It wraps the GameContentSynthesizer and GameRuntime, adding judgment,
iteration, and quality assurance on top of raw content generation.

Usage:
    director = GameDirector.get_instance()
    director.initialize()
    result = director.direct("Design a platformer with double-jump and gem collection")
    # result.html contains the final playable game
"""

from __future__ import annotations

import logging
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Enums
# =============================================================================


class DirectorPhase(Enum):
    """Phases of the director's creation pipeline."""
    ANALYZE = "analyze"
    STRATEGIZE = "strategize"
    SYNTHESIZE = "synthesize"
    BUILD = "build"
    SIMULATE = "simulate"
    EVALUATE = "evaluate"
    REFINE = "refine"
    FINALIZE = "finalize"


class QualityDimension(Enum):
    """Dimensions along which a game is evaluated."""
    ENGAGEMENT = "engagement"
    DIFFICULTY = "difficulty"
    VARIETY = "variety"
    COHERENCE = "coherence"
    PACING = "pacing"
    COMPLETENESS = "completeness"


class RefinementAction(Enum):
    """Actions the director can take to refine a game."""
    ADD_CONTENT = "add_content"
    REBALANCE = "rebalance"
    ADJUST_DIFFICULTY = "adjust_difficulty"
    INCREASE_VARIETY = "increase_variety"
    FIX_COHERENCE = "fix_coherence"
    IMPROVE_PACING = "improve_pacing"
    NONE = "none"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class QualityScore:
    """Multi-dimensional quality assessment of a game."""
    engagement: float = 0.0
    difficulty: float = 0.0
    variety: float = 0.0
    coherence: float = 0.0
    pacing: float = 0.0
    completeness: float = 0.0

    @property
    def overall(self) -> float:
        """Weighted overall quality score (0-10)."""
        weights = {
            "engagement": 0.25,
            "difficulty": 0.15,
            "variety": 0.15,
            "coherence": 0.20,
            "pacing": 0.10,
            "completeness": 0.15,
        }
        total = (
            self.engagement * weights["engagement"]
            + self.difficulty * weights["difficulty"]
            + self.variety * weights["variety"]
            + self.coherence * weights["coherence"]
            + self.pacing * weights["pacing"]
            + self.completeness * weights["completeness"]
        )
        return round(total, 2)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "engagement": round(self.engagement, 2),
            "difficulty": round(self.difficulty, 2),
            "variety": round(self.variety, 2),
            "coherence": round(self.coherence, 2),
            "pacing": round(self.pacing, 2),
            "completeness": round(self.completeness, 2),
            "overall": self.overall,
        }


@dataclass
class SimulationResult:
    """Result of a simulated playtest session."""
    session_id: str
    completion_rate: float  # 0-1, how far the simulated player got
    death_count: int
    collectible_rate: float  # 0-1, fraction of collectibles gathered
    time_to_first_death: float  # seconds
    engagement_score: float
    difficulty_score: float
    notes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "completion_rate": round(self.completion_rate, 3),
            "death_count": self.death_count,
            "collectible_rate": round(self.collectible_rate, 3),
            "time_to_first_death": round(self.time_to_first_death, 1),
            "engagement_score": round(self.engagement_score, 2),
            "difficulty_score": round(self.difficulty_score, 2),
            "notes": self.notes,
        }


@dataclass
class DirectorResult:
    """Final result of a director creation session."""
    session_id: str
    success: bool
    html: str
    quality: QualityScore
    simulations: List[SimulationResult]
    iterations: int
    refinement_actions: List[str]
    duration_s: float
    error: Optional[str]
    metadata: Dict[str, Any]

    def to_dict(self, include_html: bool = True) -> Dict[str, Any]:
        result = {
            "session_id": self.session_id,
            "success": self.success,
            "html_length": len(self.html),
            "quality": self.quality.to_dict(),
            "simulations": [s.to_dict() for s in self.simulations],
            "iterations": self.iterations,
            "refinement_actions": self.refinement_actions,
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
            "metadata": self.metadata,
        }
        if include_html:
            result["html"] = self.html
        return result


# =============================================================================
# Simulation Engine - Playtest simulation
# =============================================================================


class SimulationEngine:
    """
    Simulates playtest sessions to evaluate a game without requiring a
    human player. Uses heuristic models of player behavior to estimate
    completion rates, difficulty, and engagement.
    """

    def __init__(self) -> None:
        self._rng = random.Random(42)

    def simulate(
        self,
        game_config: Any,
        num_sessions: int = 3,
    ) -> List[SimulationResult]:
        """
        Run multiple simulated playtest sessions on a game configuration.

        Args:
            game_config: A GameConfig from the GameRuntime
            num_sessions: Number of simulated players to run

        Returns:
            List of SimulationResult, one per session
        """
        results: List[SimulationResult] = []

        levels = getattr(game_config, "levels", []) or []
        level_count = max(1, len(levels))
        enemy_count = getattr(game_config, "enemy_count", 0)
        collectible_count = getattr(game_config, "collectible_count", 0)
        lives = getattr(game_config, "lives", 3)
        gravity = getattr(game_config, "gravity", 0.0)
        move_speed = getattr(game_config, "move_speed", 3.0)
        genre = getattr(game_config, "genre", "custom")

        for session_idx in range(num_sessions):
            session_id = f"sim_{uuid.uuid4().hex[:8]}"

            # Model player skill with variation across sessions
            player_skill = 0.4 + self._rng.random() * 0.5  # 0.4 - 0.9

            # Simulate level-by-level progression
            deaths = 0
            levels_completed = 0
            collectibles_gathered = 0
            time_to_first_death = 0.0
            notes: List[str] = []

            for lvl_idx in range(level_count):
                level = levels[lvl_idx] if lvl_idx < len(levels) else None
                difficulty = getattr(level, "difficulty", 0.3 + lvl_idx * 0.12) if level else 0.3

                # Probability of completing this level
                # Higher player skill and lower difficulty = higher chance
                base_chance = player_skill * (1.0 - difficulty * 0.6)
                # Genre adjustments
                if genre in ("puzzle", "music"):
                    base_chance *= 1.1  # Puzzles are more deterministic
                elif genre in ("boss_battle", "shooter"):
                    base_chance *= 0.85  # Action games are harder

                # Random factor for replayability
                completion_chance = max(0.1, min(0.95, base_chance + self._rng.uniform(-0.1, 0.1)))

                if self._rng.random() < completion_chance:
                    levels_completed += 1
                    # Collect a fraction of collectibles
                    fraction = player_skill * (0.6 + self._rng.random() * 0.4)
                    collectibles_gathered += int(collectible_count * fraction)
                else:
                    # Player died on this level
                    if deaths == 0:
                        time_to_first_death = 15.0 + self._rng.uniform(0, 45.0)
                    deaths += 1
                    # Check if player has lives remaining
                    if deaths >= lives:
                        break
                    # Retry with slightly improved odds (learning)
                    player_skill = min(0.95, player_skill + 0.05)
                    if self._rng.random() < completion_chance * 1.15:
                        levels_completed += 1
                        collectibles_gathered += int(collectible_count * 0.4)

            completion_rate = levels_completed / level_count
            collectible_rate = collectibles_gathered / max(1, collectible_count * level_count)

            # Engagement: high completion + collectibles + low deaths
            engagement = (
                completion_rate * 40
                + min(1.0, collectible_rate) * 25
                + max(0, 1.0 - deaths / (lives * 2)) * 35
            )
            engagement = min(10.0, engagement)

            # Difficulty: balanced if completion is 40-80%
            if completion_rate > 0.8:
                difficulty_score = max(2.0, 8.0 - (completion_rate - 0.8) * 20)  # Too easy
                notes.append("Game may be too easy — consider increasing enemy count or difficulty")
            elif completion_rate < 0.3:
                difficulty_score = min(10.0, 8.0 + (0.3 - completion_rate) * 20)  # Too hard
                notes.append("Game may be too difficult — consider reducing enemy count or adding checkpoints")
            else:
                difficulty_score = 6.0 + self._rng.uniform(-1.0, 1.5)  # Well balanced
                notes.append("Difficulty feels well-balanced")

            if collectible_rate < 0.3:
                notes.append("Collectibles are hard to reach — consider repositioning")
            if gravity > 0 and move_speed < 3.5:
                notes.append("Player movement feels slow for a gravity-based game")

            results.append(SimulationResult(
                session_id=session_id,
                completion_rate=completion_rate,
                death_count=deaths,
                collectible_rate=min(1.0, collectible_rate),
                time_to_first_death=time_to_first_death,
                engagement_score=round(engagement, 2),
                difficulty_score=round(difficulty_score, 2),
                notes=notes,
            ))

        return results


# =============================================================================
# Quality Evaluator
# =============================================================================


class QualityEvaluator:
    """Evaluates game quality from simulation results and content analysis."""

    def evaluate(
        self,
        game_config: Any,
        simulations: List[SimulationResult],
        gdd: Any = None,
    ) -> QualityScore:
        """Compute multi-dimensional quality scores."""
        score = QualityScore()

        if not simulations:
            return score

        # Engagement: average engagement from simulations
        score.engagement = sum(s.engagement_score for s in simulations) / len(simulations)

        # Difficulty: average difficulty, penalize extremes
        avg_diff = sum(s.difficulty_score for s in simulations) / len(simulations)
        score.difficulty = avg_diff

        # Variety: based on entity types, level count, genre features
        levels = getattr(game_config, "levels", []) or []
        entity_types = set()
        for lvl in levels:
            for ent in getattr(lvl, "entities", []):
                entity_types.add(getattr(ent, "entity_type", "unknown"))
        variety = min(10.0, len(entity_types) * 1.2 + len(levels) * 0.8)
        score.variety = variety

        # Coherence: based on GDD quality score and narrative consistency
        gdd_quality = getattr(gdd, "quality_score", 5.0) if gdd else 5.0
        score.coherence = min(10.0, gdd_quality)

        # Pacing: based on level count and difficulty curve
        if len(levels) > 1:
            difficulties = [getattr(lvl, "difficulty", 0.5) for lvl in levels]
            # Good pacing = gradually increasing difficulty
            diffs_sorted = sorted(difficulties)
            pacing_score = 7.0
            if difficulties == diffs_sorted or all(
                difficulties[i] <= difficulties[i + 1] + 0.15
                for i in range(len(difficulties) - 1)
            ):
                pacing_score = 8.5
            score.pacing = pacing_score
        else:
            score.pacing = 5.0

        # Completeness: based on having all content sections filled
        completeness = 6.0
        if gdd:
            if getattr(gdd, "world", None) is not None:
                completeness += 0.8
            if getattr(gdd, "characters", None) and len(gdd.characters) > 0:
                completeness += 0.8
            if getattr(gdd, "narrative", None) is not None:
                completeness += 0.8
            if getattr(gdd, "mechanics", None) is not None:
                completeness += 0.8
            if getattr(gdd, "levels", None) is not None and len(gdd.levels.levels) > 0:
                completeness += 0.8
        score.completeness = min(10.0, completeness)

        return score


# =============================================================================
# Refinement Advisor
# =============================================================================


class RefinementAdvisor:
    """Analyzes quality scores and simulation results to suggest refinements."""

    def advise(
        self,
        quality: QualityScore,
        simulations: List[SimulationResult],
        game_config: Any,
    ) -> List[Tuple[RefinementAction, str]]:
        """Return a list of refinement actions with explanations."""
        actions: List[Tuple[RefinementAction, str]] = []

        # Check engagement
        if quality.engagement < 5.0:
            actions.append((
                RefinementAction.ADD_CONTENT,
                "Engagement is low — adding more interactive elements and collectibles",
            ))

        # Check difficulty balance
        avg_completion = sum(s.completion_rate for s in simulations) / max(1, len(simulations))
        if avg_completion > 0.85:
            actions.append((
                RefinementAction.ADJUST_DIFFICULTY,
                "Completion rate too high — increasing enemy count and difficulty",
            ))
        elif avg_completion < 0.3:
            actions.append((
                RefinementAction.ADJUST_DIFFICULTY,
                "Completion rate too low — reducing enemy count and adding collectibles",
            ))

        # Check variety
        if quality.variety < 5.0:
            actions.append((
                RefinementAction.INCREASE_VARIETY,
                "Low variety — diversifying entity types and level layouts",
            ))

        # Check coherence
        if quality.coherence < 6.0:
            actions.append((
                RefinementAction.FIX_COHERENCE,
                "Coherence issues detected — aligning narrative and mechanics",
            ))

        # Check pacing
        if quality.pacing < 6.0:
            actions.append((
                RefinementAction.IMPROVE_PACING,
                "Pacing needs work — smoothing the difficulty curve",
            ))

        if not actions:
            actions.append((
                RefinementAction.NONE,
                "Game quality is satisfactory — no refinement needed",
            ))

        return actions


# =============================================================================
# Tool Registry - Function calling
# =============================================================================


class ToolRegistry:
    """
    Registry of tools the director can invoke. Each tool is a named
    callable with a description, enabling a function-calling pattern
    where the director selects and executes tools based on context.
    """

    def __init__(self) -> None:
        self._tools: Dict[str, Dict[str, Any]] = {}
        self._register_builtin_tools()

    def _register_builtin_tools(self) -> None:
        """Register the built-in director tools."""
        self.register("synthesize", "Generate game content from a prompt", self._tool_synthesize)
        self.register("build", "Build playable HTML from a game design document", self._tool_build)
        self.register("simulate", "Run simulated playtest sessions", self._tool_simulate)
        self.register("evaluate", "Evaluate game quality across dimensions", self._tool_evaluate)
        self.register("refine", "Analyze and suggest refinements", self._tool_refine)

    def register(self, name: str, description: str, handler: Callable) -> None:
        """Register a new tool."""
        self._tools[name] = {
            "name": name,
            "description": description,
            "handler": handler,
        }

    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool handler by name."""
        entry = self._tools.get(name)
        return entry["handler"] if entry else None

    def list_tools(self) -> List[Dict[str, str]]:
        """List all registered tools."""
        return [{"name": t["name"], "description": t["description"]} for t in self._tools.values()]

    def _tool_synthesize(self, prompt: str, **kwargs: Any) -> Any:
        """Tool: synthesize game content."""
        from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
        synth = get_content_synthesizer()
        if not synth._initialized:
            synth.initialize()
        return synth.synthesize(prompt, **kwargs)

    def _tool_build(self, gdd: Any) -> Any:
        """Tool: build playable HTML."""
        from sparkai.engine.engine_game_runtime import get_game_runtime
        runtime = get_game_runtime()
        return runtime.build_from_gdd(gdd)

    def _tool_simulate(self, game_config: Any, num_sessions: int = 3) -> List[SimulationResult]:
        """Tool: simulate playtest sessions."""
        engine = SimulationEngine()
        return engine.simulate(game_config, num_sessions)

    def _tool_evaluate(self, game_config: Any, simulations: List[SimulationResult], gdd: Any = None) -> QualityScore:
        """Tool: evaluate quality."""
        evaluator = QualityEvaluator()
        return evaluator.evaluate(game_config, simulations, gdd)

    def _tool_refine(self, quality: QualityScore, simulations: List[SimulationResult], game_config: Any) -> List[Tuple[RefinementAction, str]]:
        """Tool: suggest refinements."""
        advisor = RefinementAdvisor()
        return advisor.advise(quality, simulations, game_config)


# =============================================================================
# Game Director - main entry point
# =============================================================================


class GameDirector:
    """
    The AI Game Director orchestrates the complete game creation lifecycle.

    Wraps the GameContentSynthesizer and GameRuntime with judgment,
    simulation, and iteration. Can autonomously produce, evaluate, and
    refine games to maximize quality.

    The director follows a generate-evaluate-refine loop:
    1. Synthesize content from the prompt
    2. Build a playable game
    3. Simulate playtest sessions
    4. Evaluate quality across dimensions
    5. If quality is below threshold, refine and regenerate
    6. Return the best game produced

    Usage:
        director = GameDirector.get_instance()
        director.initialize()
        result = director.direct("Design a platformer with gems")
    """

    _instance: Optional["GameDirector"] = None
    _instance_lock = threading.RLock()

    # Quality threshold for accepting a game without further refinement
    QUALITY_THRESHOLD: float = 6.5
    # Maximum refinement iterations
    MAX_ITERATIONS: int = 3

    def __init__(self) -> None:
        if GameDirector._instance is not None:
            raise RuntimeError("Use GameDirector.get_instance()")
        self._initialized: bool = False
        self._tools = ToolRegistry()
        self._simulator = SimulationEngine()
        self._evaluator = QualityEvaluator()
        self._advisor = RefinementAdvisor()
        self._session_history: deque = deque(maxlen=50)
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "GameDirector":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the director and its dependencies."""
        with self._lock:
            if self._initialized:
                return
            # Ensure synthesizer and runtime are available
            try:
                from sparkai.agent.agent_game_content_synthesizer import get_content_synthesizer
                synth = get_content_synthesizer()
                if not synth._initialized:
                    synth.initialize()
            except Exception as exc:
                logger.warning("Synthesizer init deferred: %s", exc)

            try:
                from sparkai.engine.engine_game_runtime import get_game_runtime
                get_game_runtime()  # Ensures singleton exists
            except Exception as exc:
                logger.warning("Runtime init deferred: %s", exc)

            self._initialized = True
            logger.info("GameDirector initialized")

    def direct(
        self,
        prompt: str,
        genre_hint: Optional[str] = None,
        max_iterations: Optional[int] = None,
    ) -> DirectorResult:
        """
        Direct the complete game creation lifecycle for a prompt.

        This is the primary entry point. Synthesizes content, builds the
        game, simulates playtests, evaluates quality, and iterates if needed.

        Args:
            prompt: Natural-language game description
            genre_hint: Optional genre hint
            max_iterations: Override max refinement iterations

        Returns:
            DirectorResult with the final playable game and quality metrics
        """
        if not self._initialized:
            self.initialize()

        session_id = f"director_{uuid.uuid4().hex[:12]}"
        start_time = time.time()
        max_iter = max_iterations or self.MAX_ITERATIONS

        try:
            # Phase 1: Synthesize
            synthesize_tool = self._tools.get_tool("synthesize")
            synth_result = synthesize_tool(
                prompt,
                genre_hint=genre_hint,
            )
            if not synth_result.success or synth_result.gdd is None:
                return DirectorResult(
                    session_id=session_id,
                    success=False,
                    html="",
                    quality=QualityScore(),
                    simulations=[],
                    iterations=0,
                    refinement_actions=[],
                    duration_s=round(time.time() - start_time, 3),
                    error=synth_result.error or "Synthesis failed",
                    metadata={},
                )

            gdd = synth_result.gdd

            # Phase 2: Build
            build_tool = self._tools.get_tool("build")
            build_result = build_tool(gdd)
            if not build_result.success:
                return DirectorResult(
                    session_id=session_id,
                    success=False,
                    html="",
                    quality=QualityScore(),
                    simulations=[],
                    iterations=0,
                    refinement_actions=[],
                    duration_s=round(time.time() - start_time, 3),
                    error=build_result.error or "Build failed",
                    metadata={},
                )

            game_config = build_result.config
            best_html = build_result.html
            best_quality = QualityScore()
            best_simulations: List[SimulationResult] = []
            all_refinement_actions: List[str] = []
            iterations_done = 0

            # Phase 3-5: Simulate, Evaluate, Refine loop
            for iteration in range(max_iter):
                iterations_done = iteration + 1

                # Simulate
                simulations = self._simulator.simulate(game_config, num_sessions=3)

                # Evaluate
                quality = self._evaluator.evaluate(game_config, simulations, gdd)

                # Track best result
                if quality.overall > best_quality.overall:
                    best_quality = quality
                    best_simulations = simulations
                    best_html = build_result.html

                # Check if quality is sufficient
                if quality.overall >= self.QUALITY_THRESHOLD:
                    logger.info(
                        "Director: quality %.2f >= threshold %.2f after %d iterations",
                        quality.overall, self.QUALITY_THRESHOLD, iterations_done,
                    )
                    break

                # Advise refinements
                actions = self._advisor.advise(quality, simulations, game_config)
                for action, explanation in actions:
                    all_refinement_actions.append(f"[Iter {iteration + 1}] {action.value}: {explanation}")

                # If no refinement needed, break
                if all(a[0] == RefinementAction.NONE for a in actions):
                    break

                # Apply refinements by re-synthesizing with adjusted parameters
                refined_prompt = self._apply_refinements(prompt, actions, quality)
                logger.info("Director: iteration %d, refining prompt: %s", iteration + 1, refined_prompt[:80])

                synth_result = synthesize_tool(refined_prompt, genre_hint=genre_hint)
                if synth_result.success and synth_result.gdd is not None:
                    gdd = synth_result.gdd
                    build_result = build_tool(gdd)
                    if build_result.success:
                        game_config = build_result.config

            # Finalize
            duration = time.time() - start_time
            result = DirectorResult(
                session_id=session_id,
                success=True,
                html=best_html,
                quality=best_quality,
                simulations=best_simulations,
                iterations=iterations_done,
                refinement_actions=all_refinement_actions,
                duration_s=round(duration, 3),
                error=None,
                metadata={
                    "prompt": prompt,
                    "genre": getattr(gdd.concept, "genre", "").value if hasattr(getattr(gdd.concept, "genre", ""), "value") else str(getattr(gdd.concept, "genre", "")),
                    "title": getattr(gdd.concept, "title", ""),
                    "quality_threshold": self.QUALITY_THRESHOLD,
                    "synthesis_result_id": synth_result.result_id,
                    "tools_available": self._tools.list_tools(),
                },
            )

            with self._lock:
                self._session_history.append({
                    "session_id": session_id,
                    "prompt": prompt[:100],
                    "quality": best_quality.overall,
                    "iterations": iterations_done,
                    "duration_s": round(duration, 3),
                    "timestamp": time.time(),
                })

            return result

        except Exception as exc:
            logger.exception("GameDirector.direct failed: %s", exc)
            return DirectorResult(
                session_id=session_id,
                success=False,
                html="",
                quality=QualityScore(),
                simulations=[],
                iterations=0,
                refinement_actions=[],
                duration_s=round(time.time() - start_time, 3),
                error=str(exc),
                metadata={},
            )

    def _apply_refinements(
        self,
        original_prompt: str,
        actions: List[Tuple[RefinementAction, str]],
        quality: QualityScore,
    ) -> str:
        """
        Apply refinement actions by modifying the prompt to guide re-synthesis.

        Instead of directly editing game data, the director adjusts the
        prompt to steer the synthesizer toward better content. This keeps
        the pipeline simple and lets the synthesizer handle the details.
        """
        modifiers: List[str] = []

        for action, _ in actions:
            if action == RefinementAction.ADJUST_DIFFICULTY:
                avg_completion = quality.engagement / 10.0
                if avg_completion > 0.7:
                    modifiers.append("with more enemies and challenging gameplay")
                else:
                    modifiers.append("with fewer enemies and more forgiving difficulty")
            elif action == RefinementAction.ADD_CONTENT:
                modifiers.append("with rich content, many collectibles, and varied encounters")
            elif action == RefinementAction.INCREASE_VARIETY:
                modifiers.append("with diverse environments, multiple enemy types, and varied level designs")
            elif action == RefinementAction.FIX_COHERENCE:
                modifiers.append("with a cohesive theme, consistent narrative, and unified visual style")
            elif action == RefinementAction.IMPROVE_PACING:
                modifiers.append("with smooth difficulty progression and well-paced levels")

        if not modifiers:
            return original_prompt

        # Append up to 2 modifiers to avoid overloading the prompt
        return f"{original_prompt} {', '.join(modifiers[:2])}"

    def get_status(self) -> Dict[str, Any]:
        """Return director status information."""
        return {
            "status": "ready" if self._initialized else "not_initialized",
            "sessions_completed": len(self._session_history),
            "quality_threshold": self.QUALITY_THRESHOLD,
            "max_iterations": self.MAX_ITERATIONS,
            "tools": self._tools.list_tools(),
            "recent_sessions": list(self._session_history)[-5:],
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return the director's session history."""
        with self._lock:
            return list(self._session_history)


def get_game_director() -> GameDirector:
    """Convenience function to access the singleton GameDirector."""
    return GameDirector.get_instance()
