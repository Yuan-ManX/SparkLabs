"""
SparkLabs Agent - Game Tournament

The capstone agent of the AI-native game pipeline. It takes multiple game
HTML variants and runs them through a competitive tournament bracket where
each game is evaluated by the Game Critic (quality) and Game Analytics
(engagement). A composite tournament score determines the winner of each
head-to-head match, and the champion emerges as the final victor.

Architecture:
  GameTournament (Singleton)
    |-- GameCriticAgent     -> quality scores across 10 dimensions (0-10)
    |-- GameAnalytics       -> engagement prediction via Monte Carlo (0-100)
    |-- Bracket Engine      -> single-elimination tournament brackets

Tournament scoring formula:
  composite = critic_overall * 10 * critic_weight + engagement_score * analytics_weight
  (both normalized to 0-100 scale, then weighted sum)

Usage:
    tourney = GameTournament.get_instance()
    tourney.initialize()
    result = tourney.run(variants, game_title="My Game")
    # result.champion_html contains the winning game
    # result.bracket contains the full match history
"""

from __future__ import annotations

import logging
import math
import random
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class GameEntry:
    """A single game variant entered into the tournament."""

    entry_id: str
    label: str
    html: str
    source: str  # "conductor", "mutator", "manual", etc.
    seed_rank: int  # initial seeding rank (1 = best seed)

    # Evaluation results (filled during tournament)
    critic_score: float = 0.0  # 0-10 scale
    engagement_score: float = 0.0  # 0-100 scale
    composite_score: float = 0.0  # 0-100 scale
    critic_report: Optional[Dict[str, Any]] = None
    analytics_result: Optional[Dict[str, Any]] = None
    evaluated: bool = False

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "entry_id": self.entry_id,
            "label": self.label,
            "source": self.source,
            "seed_rank": self.seed_rank,
            "critic_score": round(self.critic_score, 2),
            "engagement_score": round(self.engagement_score, 1),
            "composite_score": round(self.composite_score, 2),
            "evaluated": self.evaluated,
        }
        if include_html:
            result["html"] = self.html
        return result


@dataclass
class MatchResult:
    """Result of a single head-to-head match."""

    match_id: str
    round_num: int
    match_num: int
    entry_a_id: str
    entry_b_id: str
    entry_a_label: str
    entry_b_label: str
    score_a: float
    score_b: float
    winner_id: str
    winner_label: str
    loser_id: str
    margin: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "match_id": self.match_id,
            "round_num": self.round_num,
            "match_num": self.match_num,
            "entry_a_id": self.entry_a_id,
            "entry_b_id": self.entry_b_id,
            "entry_a_label": self.entry_a_label,
            "entry_b_label": self.entry_b_label,
            "score_a": round(self.score_a, 2),
            "score_b": round(self.score_b, 2),
            "winner_id": self.winner_id,
            "winner_label": self.winner_label,
            "loser_id": self.loser_id,
            "margin": round(self.margin, 2),
        }


@dataclass
class TournamentResult:
    """Complete result of a tournament run."""

    tournament_id: str
    success: bool
    game_title: str
    entry_count: int
    rounds: int
    champion: Optional[GameEntry]
    runner_up: Optional[GameEntry]
    bracket: List[MatchResult]
    all_entries: List[GameEntry]
    standings: List[Dict[str, Any]]
    duration_s: float
    error: Optional[str] = None
    scoring_weights: Dict[str, float] = field(default_factory=dict)

    def to_dict(self, include_html: bool = False) -> Dict[str, Any]:
        return {
            "tournament_id": self.tournament_id,
            "success": self.success,
            "game_title": self.game_title,
            "entry_count": self.entry_count,
            "rounds": self.rounds,
            "champion": self.champion.to_dict(include_html=include_html) if self.champion else None,
            "runner_up": self.runner_up.to_dict(include_html=False) if self.runner_up else None,
            "bracket": [m.to_dict() for m in self.bracket],
            "all_entries": [e.to_dict(include_html=False) for e in self.all_entries],
            "standings": list(self.standings),
            "duration_s": round(self.duration_s, 3),
            "error": self.error,
            "scoring_weights": dict(self.scoring_weights),
        }


# =============================================================================
# Game Tournament Agent
# =============================================================================


class GameTournament:
    """
    Capstone agent that runs competitive tournaments between game variants.

    Each variant is evaluated by the Game Critic (quality) and Game Analytics
    (predicted engagement). A composite score determines match winners in a
    single-elimination bracket. The champion is the variant that survives all
    rounds.

    Implements a thread-safe singleton pattern.
    """

    _instance: Optional["GameTournament"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if GameTournament._instance is not None:
            raise RuntimeError("Use GameTournament.get_instance()")
        self._initialized: bool = False
        self._critic: Any = None
        self._analytics: Any = None
        self._history: deque = deque(maxlen=30)
        self._total_tournaments: int = 0
        self._lock = threading.RLock()

        # Scoring weights (critic_weight + analytics_weight = 1.0)
        self._critic_weight: float = 0.55
        self._analytics_weight: float = 0.45

        # Simulations per persona for analytics evaluation
        self._sims_per_persona: int = 30

    @classmethod
    def get_instance(cls) -> "GameTournament":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Initialize the tournament agent by acquiring subsystem singletons."""
        with self._lock:
            if self._initialized:
                return
            try:
                from sparkai.agent.agent_game_critic import GameCriticAgent
                self._critic = GameCriticAgent.get_instance()
            except Exception as exc:
                logger.warning("GameCriticAgent acquisition failed: %s", exc)
                self._critic = None

            try:
                from sparkai.agent.agent_game_analytics import GameAnalytics
                self._analytics = GameAnalytics.get_instance()
            except Exception as exc:
                logger.warning("GameAnalytics acquisition failed: %s", exc)
                self._analytics = None

            self._initialized = True
            logger.info("GameTournament initialized")

    # -- Public API --------------------------------------------------------

    def run(
        self,
        variants: List[Dict[str, Any]],
        game_title: str = "Untitled Tournament",
        critic_weight: Optional[float] = None,
        analytics_weight: Optional[float] = None,
        genre: str = "",
    ) -> TournamentResult:
        """
        Run a full tournament with the given game variants.

        Args:
            variants: List of dicts with keys "html" (required), "label"
                      (optional), "source" (optional)
            game_title: Title for the tournament
            critic_weight: Weight for critic score (0-1, default 0.55)
            analytics_weight: Weight for analytics score (0-1, default 0.45)
            genre: Optional genre hint for evaluation

        Returns:
            TournamentResult with champion, bracket, and standings
        """
        if not self._initialized:
            self.initialize()

        tournament_id = f"tourney_{uuid.uuid4().hex[:12]}"
        start_time = time.time()

        # Update weights if provided
        if critic_weight is not None:
            self._critic_weight = max(0.0, min(1.0, critic_weight))
        if analytics_weight is not None:
            self._analytics_weight = max(0.0, min(1.0, analytics_weight))
        # Ensure weights sum to 1.0
        total_w = self._critic_weight + self._analytics_weight
        if total_w > 0:
            self._critic_weight /= total_w
            self._analytics_weight /= total_w

        try:
            # Phase 1: Create game entries from variants
            entries = self._create_entries(variants)
            if len(entries) < 2:
                return TournamentResult(
                    tournament_id=tournament_id,
                    success=False,
                    game_title=game_title,
                    entry_count=len(entries),
                    rounds=0,
                    champion=None,
                    runner_up=None,
                    bracket=[],
                    all_entries=entries,
                    standings=[],
                    duration_s=time.time() - start_time,
                    error="At least 2 game variants are required for a tournament",
                    scoring_weights=self._weights_dict(),
                )

            # Phase 2: Evaluate all entries through Critic + Analytics
            for entry in entries:
                self._evaluate_entry(entry, game_title, genre)

            # Phase 3: Seed the bracket by composite score (highest = seed 1)
            entries.sort(key=lambda e: e.composite_score, reverse=True)
            for i, entry in enumerate(entries):
                entry.seed_rank = i + 1

            # Phase 4: Run the single-elimination bracket
            bracket = self._run_bracket(entries)

            # Phase 5: Determine champion and runner-up
            champion = entries[0] if entries else None
            runner_up = entries[1] if len(entries) > 1 else None

            # Phase 6: Build standings
            standings = self._build_standings(entries, bracket)

            duration = time.time() - start_time
            result = TournamentResult(
                tournament_id=tournament_id,
                success=True,
                game_title=game_title,
                entry_count=len(entries),
                rounds=self._count_rounds(len(entries)),
                champion=champion,
                runner_up=runner_up,
                bracket=bracket,
                all_entries=entries,
                standings=standings,
                duration_s=duration,
                scoring_weights=self._weights_dict(),
            )

            with self._lock:
                self._history.append(result)
                self._total_tournaments += 1

            logger.info(
                "Tournament %s complete: champion=%s (%.2f), %d entries, %d rounds",
                tournament_id,
                champion.label if champion else "N/A",
                champion.composite_score if champion else 0,
                len(entries),
                result.rounds,
            )
            return result

        except Exception as exc:
            logger.exception("Tournament %s failed: %s", tournament_id, exc)
            return TournamentResult(
                tournament_id=tournament_id,
                success=False,
                game_title=game_title,
                entry_count=len(variants),
                rounds=0,
                champion=None,
                runner_up=None,
                bracket=[],
                all_entries=[],
                standings=[],
                duration_s=time.time() - start_time,
                error=str(exc),
                scoring_weights=self._weights_dict(),
            )

    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the tournament agent."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_tournaments": self._total_tournaments,
                "critic_weight": round(self._critic_weight, 2),
                "analytics_weight": round(self._analytics_weight, 2),
                "min_entries": 2,
                "max_entries": 16,
            }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent tournament results."""
        with self._lock:
            return [r.to_dict(include_html=False) for r in list(self._history)[-limit:]]

    # -- Internal: Entry Creation ------------------------------------------

    def _create_entries(self, variants: List[Dict[str, Any]]) -> List[GameEntry]:
        """Create GameEntry objects from variant dicts."""
        entries: List[GameEntry] = []
        for i, v in enumerate(variants):
            html = v.get("html", "")
            if not html or not html.strip():
                continue
            label = v.get("label", f"Variant {i + 1}")
            source = v.get("source", "manual")
            entry = GameEntry(
                entry_id=f"entry_{uuid.uuid4().hex[:8]}",
                label=label,
                html=html,
                source=source,
                seed_rank=0,
            )
            entries.append(entry)
        return entries

    # -- Internal: Evaluation ----------------------------------------------

    def _evaluate_entry(
        self,
        entry: GameEntry,
        game_title: str,
        genre: str,
    ) -> None:
        """Evaluate a single entry through Critic and Analytics."""
        # -- Critic evaluation --
        critic_score = 5.0  # default neutral score
        critic_report = None
        if self._critic is not None:
            try:
                result = self._critic.critique_game(
                    html=entry.html,
                    game_title=f"{game_title} - {entry.label}",
                    genre=genre,
                )
                report = result.get("report")
                if report:
                    critic_score = report.get("overall_score", 5.0)
                    critic_report = report
            except Exception as exc:
                logger.warning("Critic evaluation failed for %s: %s", entry.label, exc)

        # -- Analytics evaluation --
        engagement_score = 50.0  # default neutral score
        analytics_result = None
        if self._analytics is not None:
            try:
                result = self._analytics.analyze(
                    html=entry.html,
                    genre=genre,
                    simulations_per_persona=self._sims_per_persona,
                )
                data = result.to_dict()
                overall = data.get("overall_metrics", {})
                engagement_score = overall.get("engagement_score", 50.0)
                analytics_result = data
            except Exception as exc:
                logger.warning("Analytics evaluation failed for %s: %s", entry.label, exc)

        # -- Composite score (0-100 scale) --
        # Critic is 0-10, so multiply by 10 to get 0-100
        critic_normalized = critic_score * 10.0
        composite = (
            critic_normalized * self._critic_weight
            + engagement_score * self._analytics_weight
        )

        entry.critic_score = critic_score
        entry.engagement_score = engagement_score
        entry.composite_score = composite
        entry.critic_report = critic_report
        entry.analytics_result = analytics_result
        entry.evaluated = True

    # -- Internal: Bracket Engine ------------------------------------------

    def _run_bracket(self, entries: List[GameEntry]) -> List[MatchResult]:
        """
        Run a single-elimination bracket tournament.

        Seeds are matched so that seed 1 plays the lowest seed, seed 2 plays
        the second-lowest, etc. Byes are given to top seeds when the entry
        count is not a power of 2.
        """
        matches: List[MatchResult] = []
        n = len(entries)
        if n < 2:
            return matches

        # Standard seeding: pair top seeds with bottom seeds
        bracket_order = self._seed_bracket(n)

        # Create the initial round
        current_round: List[GameEntry] = [entries[i] for i in bracket_order]
        round_num = 1

        while len(current_round) > 1:
            next_round: List[GameEntry] = []
            match_num = 1

            for i in range(0, len(current_round), 2):
                if i + 1 >= len(current_round):
                    # Bye: odd number of entries, this one advances automatically
                    next_round.append(current_round[i])
                    continue

                entry_a = current_round[i]
                entry_b = current_round[i + 1]

                match = self._play_match(entry_a, entry_b, round_num, match_num)
                matches.append(match)

                winner = entry_a if match.winner_id == entry_a.entry_id else entry_b
                next_round.append(winner)
                match_num += 1

            current_round = next_round
            round_num += 1

        return matches

    def _play_match(
        self,
        entry_a: GameEntry,
        entry_b: GameEntry,
        round_num: int,
        match_num: int,
    ) -> MatchResult:
        """Play a single match between two entries. Higher composite score wins."""
        score_a = entry_a.composite_score
        score_b = entry_b.composite_score

        # Tiebreaker: add tiny random jitter to avoid exact ties
        if abs(score_a - score_b) < 0.01:
            score_a += random.uniform(-0.005, 0.005)
            score_b += random.uniform(-0.005, 0.005)

        if score_a >= score_b:
            winner = entry_a
            loser = entry_b
        else:
            winner = entry_b
            loser = entry_a

        margin = abs(score_a - score_b)

        return MatchResult(
            match_id=f"match_{uuid.uuid4().hex[:8]}",
            round_num=round_num,
            match_num=match_num,
            entry_a_id=entry_a.entry_id,
            entry_b_id=entry_b.entry_id,
            entry_a_label=entry_a.label,
            entry_b_label=entry_b.label,
            score_a=score_a,
            score_b=score_b,
            winner_id=winner.entry_id,
            winner_label=winner.label,
            loser_id=loser.entry_id,
            margin=margin,
        )

    def _seed_bracket(self, n: int) -> List[int]:
        """
        Generate standard tournament seeding for n entries.

        Returns a list of indices [0, n) arranged so that seed 1 plays the
        lowest seed, seed 2 plays the second-lowest, etc. This uses the
        recursive bit-reversal method for power-of-2 sizes, with byes for
        non-power-of-2 sizes.
        """
        # Find the next power of 2 >= n
        size = 1
        while size < n:
            size *= 2

        # Generate seeds for the full power-of-2 bracket
        seeds = self._generate_seeds(size)

        # Map seeds to actual entry indices (seeds > n are byes)
        result: List[int] = []
        for s in seeds:
            if s <= n:
                result.append(s - 1)  # convert to 0-based index

        return result

    def _generate_seeds(self, size: int) -> List[int]:
        """Generate standard single-elimination seeding for a power-of-2 size."""
        if size == 1:
            return [1]
        if size == 2:
            return [1, 2]

        # Recursive: split into two halves, interleave
        half = size // 2
        half_seeds = self._generate_seeds(half)
        # The second half seeds are: for each seed s in first half,
        # the matching seed is (size + 1 - s)
        full: List[int] = []
        for s in half_seeds:
            full.append(s)
            full.append(size + 1 - s)
        return full

    # -- Internal: Standings -----------------------------------------------

    def _build_standings(
        self,
        entries: List[GameEntry],
        bracket: List[MatchResult],
    ) -> List[Dict[str, Any]]:
        """Build final standings sorted by composite score."""
        standings: List[Dict[str, Any]] = []
        for rank, entry in enumerate(entries, 1):
            # Count wins and losses from bracket
            wins = sum(1 for m in bracket if m.winner_id == entry.entry_id)
            losses = sum(1 for m in bracket if m.loser_id == entry.entry_id)
            standings.append({
                "rank": rank,
                "entry_id": entry.entry_id,
                "label": entry.label,
                "source": entry.source,
                "critic_score": round(entry.critic_score, 2),
                "engagement_score": round(entry.engagement_score, 1),
                "composite_score": round(entry.composite_score, 2),
                "wins": wins,
                "losses": losses,
                "is_champion": rank == 1,
            })
        return standings

    # -- Internal: Utilities -----------------------------------------------

    def _count_rounds(self, n: int) -> int:
        """Count the number of rounds in a single-elimination bracket."""
        if n <= 1:
            return 0
        return math.ceil(math.log2(n))

    def _weights_dict(self) -> Dict[str, float]:
        """Return the current scoring weights as a dict."""
        return {
            "critic": round(self._critic_weight, 2),
            "analytics": round(self._analytics_weight, 2),
        }


# =============================================================================
# Module-level accessor
# =============================================================================


def get_game_tournament() -> GameTournament:
    """Get the singleton GameTournament instance."""
    return GameTournament.get_instance()
