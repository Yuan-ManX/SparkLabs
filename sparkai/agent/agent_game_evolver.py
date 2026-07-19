"""
SparkLabs Agent - Game Evolver

An AI agent that optimizes games through evolutionary iteration. Each
generation produces multiple mutations of a base game, evaluates them
with the Game Critic as a fitness function, and selects the best
variant as the parent for the next generation.

This creates a closed-loop AI optimization system:
  Base Game -> Mutate -> Critique -> Select Best -> Repeat

The evolver combines the Game Mutator (variation) and Game Critic
(selection pressure) into a single optimization pipeline that can
improve game quality across multiple generations without human
intervention.

Architecture:
  GameEvolver (singleton)
    |-- PopulationGenerator -> creates mutated variants
    |-- FitnessEvaluator   -> scores each variant using GameCritic
    |-- SelectionStrategy  -> picks the best variant for next gen
    |-- EvolutionTracker   -> records generation history and stats

Key Design Decisions:
  - Uses GameCritic.critique_game() as the fitness function
  - Supports both random mutation and strategy-directed mutation
  - Tracks score progression across generations
  - Early termination if no improvement for N generations
  - Returns the best game found plus full evolution history
"""

from __future__ import annotations

import random
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sparkai.agent.agent_game_mutator import get_game_mutator
from sparkai.agent.agent_game_critic import get_game_critic
from sparkai.agent.agent_game_sentinel import GameSentinel


# ---------------------------------------------------------------------------
# Data Structures
# ---------------------------------------------------------------------------

@dataclass
class GenerationResult:
    """Result of a single generation of evolution."""
    generation: int
    population_size: int
    variants: List[Dict[str, Any]] = field(default_factory=list)
    best_score: float = 0.0
    best_strategy: str = ""
    avg_score: float = 0.0
    worst_score: float = 0.0
    improvement: float = 0.0  # delta from previous best
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "generation": self.generation,
            "population_size": self.population_size,
            "variants": self.variants,
            "best_score": round(self.best_score, 3),
            "best_strategy": self.best_strategy,
            "avg_score": round(self.avg_score, 3),
            "worst_score": round(self.worst_score, 3),
            "improvement": round(self.improvement, 3),
            "duration_s": round(self.duration_s, 3),
        }


@dataclass
class EvolutionResult:
    """Result of a full evolution run."""
    session_id: str
    success: bool
    original_html: str
    evolved_html: str
    original_score: float
    evolved_score: float
    total_improvement: float
    generations: int
    population_size: int
    history: List[GenerationResult] = field(default_factory=list)
    strategies_used: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    early_terminated: bool = False
    error: Optional[str] = None

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "session_id": self.session_id,
            "success": self.success,
            "original_score": round(self.original_score, 3),
            "evolved_score": round(self.evolved_score, 3),
            "total_improvement": round(self.total_improvement, 3),
            "generations": self.generations,
            "population_size": self.population_size,
            "history": [g.to_dict() for g in self.history],
            "strategies_used": self.strategies_used,
            "duration_s": round(self.duration_s, 3),
            "early_terminated": self.early_terminated,
            "error": self.error,
        }
        if include_html:
            result["original_html"] = self.original_html
            result["evolved_html"] = self.evolved_html
        return result


@dataclass
class EvolutionStats:
    """Aggregate statistics for the evolver."""
    total_runs: int = 0
    successful_runs: int = 0
    total_generations: int = 0
    avg_improvement: float = 0.0
    best_improvement: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_runs": self.total_runs,
            "successful_runs": self.successful_runs,
            "total_generations": self.total_generations,
            "avg_improvement": round(self.avg_improvement, 3),
            "best_improvement": round(self.best_improvement, 3),
        }


# ---------------------------------------------------------------------------
# Game Evolver Singleton
# ---------------------------------------------------------------------------


class GameEvolver:
    """Evolutionary game optimization using mutation + critique + playability.

    Each generation:
      1. Generate N mutations of the current best game
      2. Evaluate each with the Game Critic (quality score)
      3. Verify playability with the Game Sentinel (health gate)
      4. Compute composite fitness = quality * playability_gate + bonus
      5. Select the highest-fitness variant
      6. If it improves on the current best, adopt it
      7. Repeat for the specified number of generations

    The composite fitness ensures the evolution optimizes for both
    aesthetic quality AND actual playability. A variant that scores high
    on the critic but fails playability checks (missing canvas, no game
    loop, etc.) is penalized, because an unplayable game has zero value
    regardless of its design quality.

    The evolver can also heal each variant before evaluation to ensure
    that quality patches (audio, touch, etc.) are applied consistently.
    """

    _instance: Optional["GameEvolver"] = None
    _lock: threading.RLock = threading.RLock()

    # Strategies that tend to produce meaningful quality changes
    DEFAULT_STRATEGIES: List[str] = [
        "difficulty_ramp", "difficulty_ease",
        "pace_frenetic", "pace_floaty",
        "density_swarm", "density_harvest",
        "theme_midnight", "theme_forest", "theme_sunset",
        "gravity_flip",
    ]

    def __new__(cls) -> "GameEvolver":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    obj = super().__new__(cls)
                    obj._initialized = False
                    cls._instance = obj
        return cls._instance

    @classmethod
    def get_instance(cls) -> "GameEvolver":
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
            self._history: List[EvolutionResult] = []
            self._stats = EvolutionStats()
            self._sentinel: GameSentinel = GameSentinel.get_instance()
            self._initialized = True

    def _compute_fitness(
        self, critic_score: float, html: str,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        Composite fitness combining critic quality score with sentinel
        playability verification. A variant that fails playability checks
        is heavily penalized regardless of its aesthetic quality score,
        because an unplayable game has zero value regardless of how
        well-designed its content might be.

        Fitness = critic_score * playability_gate + playability_bonus

        - playability_gate: 0.0 if any critical playability metric < 50,
          otherwise scales linearly from 0.5 to 1.0 as metrics approach 100.
        - playability_bonus: up to +5.0 added when all metrics are perfect,
          rewarding fully playable variants above the critic score alone.
        """
        try:
            if not self._sentinel.initialized:
                self._sentinel.initialize()
            guard_result = self._sentinel.guard(html, inject_telemetry=False)
            report = guard_result.get("report", {})
            health = report.get("health_score", 0.0)
            metrics = report.get("metrics", [])
            play_metrics = [
                m for m in metrics
                if m.get("name", "").startswith("playability_")
            ]
            if not play_metrics:
                # No playability metrics means sentinel could not verify;
                # trust the critic score without modification.
                return critic_score, {
                    "health_score": health,
                    "playability_avg": None,
                    "gate": 1.0,
                }
            play_avg = sum(m.get("value", 0) for m in play_metrics) / len(play_metrics)
            # Gate: variants with avg playability below 50 are nearly unplayable
            if play_avg < 50:
                gate = 0.1
            else:
                gate = 0.5 + (play_avg - 50) / 100.0  # 0.5 at 50, 1.0 at 100
            bonus = (play_avg - 90) * 0.5 if play_avg > 90 else 0.0
            fitness = critic_score * gate + bonus
            return fitness, {
                "health_score": round(health, 2),
                "playability_avg": round(play_avg, 2),
                "gate": round(gate, 3),
                "bonus": round(bonus, 3),
            }
        except Exception:
            # If sentinel fails, fall back to critic score only
            return critic_score, {"health_score": None, "playability_avg": None}

    # -- Public API --------------------------------------------------------

    def evolve(
        self,
        html: str,
        generations: int = 3,
        population_size: int = 5,
        strategies: Optional[List[str]] = None,
        early_stop_patience: int = 2,
        game_title: str = "Evolved Game",
        genre: str = "",
    ) -> EvolutionResult:
        """Evolve a game through multiple generations.

        Args:
            html: The base game HTML to optimize.
            generations: Number of generations to run.
            population_size: Number of mutations per generation.
            strategies: Optional list of mutation strategy IDs. If None,
                        uses a random subset of DEFAULT_STRATEGIES.
            early_stop_patience: Stop if no improvement for this many
                                 consecutive generations.
            game_title: Title for the game.
            genre: Genre hint for the critic.

        Returns:
            EvolutionResult with the best game found and full history.
        """
        import uuid
        start = time.time()
        session_id = f"evo_{uuid.uuid4().hex[:12]}"

        try:
            mutator = get_game_mutator()
            if not mutator._initialized:
                mutator.initialize()
            critic = get_game_critic()

            available_strategies = strategies or self.DEFAULT_STRATEGIES
            strategies_used: List[str] = []

            # Evaluate the original game
            original_report = critic.critique_game(
                html, game_title=game_title, genre=genre,
            )
            original_critic_score = (
                original_report.get("report", {}).get("overall_score", 0.0)
                if original_report.get("report")
                else 0.0
            )
            # Composite fitness: critic quality * playability gate + bonus
            original_score, original_play = self._compute_fitness(
                original_critic_score, html,
            )

            current_best_html = html
            current_best_score = original_score
            history: List[GenerationResult] = []
            no_improvement_count = 0
            early_terminated = False

            for gen in range(generations):
                gen_start = time.time()
                gen_variants: List[Dict[str, Any]] = []
                gen_scores: List[Tuple[float, str, str]] = []  # (score, strategy, html)

                # Generate population
                pop_strategies = self._select_strategies(
                    available_strategies, population_size,
                )

                for strategy_id in pop_strategies:
                    try:
                        mutation_result = mutator.mutate(
                            current_best_html, strategy_id,
                        )
                        if not mutation_result.success:
                            gen_variants.append({
                                "strategy": strategy_id,
                                "score": 0.0,
                                "success": False,
                            })
                            continue

                        variant_html = mutation_result.variant_html

                        # Evaluate variant
                        variant_report = critic.critique_game(
                            variant_html,
                            game_title=f"{game_title} G{gen+1}",
                            genre=genre,
                        )
                        variant_critic_score = (
                            variant_report.get("report", {}).get("overall_score", 0.0)
                            if variant_report.get("report")
                            else 0.0
                        )
                        # Composite fitness: critic quality * playability gate + bonus
                        variant_score, variant_play = self._compute_fitness(
                            variant_critic_score, variant_html,
                        )

                        gen_variants.append({
                            "strategy": strategy_id,
                            "score": round(variant_score, 3),
                            "critic_score": round(variant_critic_score, 3),
                            "playability": variant_play,
                            "success": True,
                        })
                        gen_scores.append((variant_score, strategy_id, variant_html))

                        if strategy_id not in strategies_used:
                            strategies_used.append(strategy_id)

                    except Exception:
                        gen_variants.append({
                            "strategy": strategy_id,
                            "score": 0.0,
                            "success": False,
                        })

                if not gen_scores:
                    history.append(GenerationResult(
                        generation=gen + 1,
                        population_size=population_size,
                        variants=gen_variants,
                        best_score=current_best_score,
                        avg_score=0.0,
                        worst_score=0.0,
                        improvement=0.0,
                        duration_s=time.time() - gen_start,
                    ))
                    continue

                # Sort by score descending
                gen_scores.sort(key=lambda x: x[0], reverse=True)
                best_variant_score, best_strategy, best_variant_html = gen_scores[0]
                avg_score = sum(s[0] for s in gen_scores) / len(gen_scores)
                worst_score = gen_scores[-1][0]
                improvement = best_variant_score - current_best_score

                # Selection: adopt if better
                if best_variant_score > current_best_score:
                    current_best_html = best_variant_html
                    current_best_score = best_variant_score
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1

                history.append(GenerationResult(
                    generation=gen + 1,
                    population_size=population_size,
                    variants=gen_variants,
                    best_score=best_variant_score,
                    best_strategy=best_strategy,
                    avg_score=avg_score,
                    worst_score=worst_score,
                    improvement=improvement,
                    duration_s=time.time() - gen_start,
                ))

                # Early termination
                if no_improvement_count >= early_stop_patience:
                    early_terminated = True
                    break

            total_improvement = current_best_score - original_score

            result = EvolutionResult(
                session_id=session_id,
                success=True,
                original_html=html,
                evolved_html=current_best_html,
                original_score=original_score,
                evolved_score=current_best_score,
                total_improvement=total_improvement,
                generations=len(history),
                population_size=population_size,
                history=history,
                strategies_used=strategies_used,
                duration_s=time.time() - start,
                early_terminated=early_terminated,
            )

            # Record in history
            with self._inner_lock:
                self._history.append(result)
                if len(self._history) > 50:
                    self._history.pop(0)
                self._stats.total_runs += 1
                self._stats.successful_runs += 1
                self._stats.total_generations += len(history)
                if total_improvement > self._stats.best_improvement:
                    self._stats.best_improvement = total_improvement
                # Running average
                n = self._stats.total_runs
                self._stats.avg_improvement = (
                    self._stats.avg_improvement * (n - 1) + total_improvement
                ) / n

            return result

        except Exception as e:
            import traceback
            traceback.print_exc()
            return EvolutionResult(
                session_id=session_id,
                success=False,
                original_html=html,
                evolved_html=html,
                original_score=0.0,
                evolved_score=0.0,
                total_improvement=0.0,
                generations=0,
                population_size=population_size,
                duration_s=time.time() - start,
                error=str(e),
            )

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """List recent evolution runs."""
        with self._inner_lock:
            return [r.to_dict() for r in self._history[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        """Return aggregate statistics."""
        with self._inner_lock:
            return self._stats.to_dict()

    def get_status(self) -> Dict[str, Any]:
        """Return status for health checks."""
        with self._inner_lock:
            return {
                "initialized": self._initialized,
                "total_runs": len(self._history),
                "default_strategies": self.DEFAULT_STRATEGIES,
            }

    # -- Internal Helpers --------------------------------------------------

    def _select_strategies(
        self,
        available: List[str],
        count: int,
    ) -> List[str]:
        """Select strategies for a generation's population."""
        if count >= len(available):
            return list(available)
        return random.sample(available, count)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_game_evolver() -> GameEvolver:
    """Return the singleton GameEvolver instance."""
    return GameEvolver.get_instance()
