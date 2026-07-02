"""
SparkLabs Engine - Leaderboard, Scoring, and Ranking System

A comprehensive leaderboard, scoring, and ranking system for the SparkLabs
AI-native game engine. Players submit scores to leaderboards, compete for
top positions on ranked leaderboards, and participate in ranked seasons
with tier progression (Bronze through Legend).

Architecture:
  LeaderboardSystemEngine (singleton)
    |-- Leaderboard          — leaderboard definition with scope and sort order
    |-- LeaderboardEntry     — per-player entry with rank and submission stats
    |-- ScoreRecord          — atomic validated score submission
    |-- RankingSeason        — time-boxed ranked season lifecycle
    |-- PlayerRank           — per-player tier and ranking within a season
    |-- LeaderboardStats     — aggregate counters
    |-- LeaderboardSnapshot  — immutable state snapshot
    |-- LeaderboardEvent     — audit log entry
    |-- ScoreType            — 10 score classifications
    |-- SortOrder            — ascending / descending ranking direction
    |-- LeaderboardScope     — 5 leaderboard audience scopes
    |-- SeasonStatus         — 3 season lifecycle states
    |-- RankTier             — 8 competitive tiers
    |-- LeaderboardEventKind — 8 audit event kinds

Core Capabilities:
  - create_leaderboard / list_leaderboards / get_leaderboard: leaderboard registry
  - submit_score: record a score, update the player entry, recompute ranks
  - get_entry / list_entries / get_rank / get_top_entries / get_neighbors: ranking queries
  - create_season / list_seasons / get_season / start_season / end_season: season lifecycle
  - assign_tier / list_player_ranks / get_player_rank: tier assignment per season
  - get_stats / get_status / get_snapshot / list_events: observability
  - reset: clear all stores and re-seed with default data
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_LEADERBOARDS: int = 200
_MAX_ENTRIES: int = 20000
_MAX_SCORES: int = 100000
_MAX_SEASONS: int = 100
_MAX_PLAYER_RANKS: int = 20000
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current time as a Unix epoch float."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _clamp(value: int, low: int, high: int) -> int:
    """Clamp an integer value to the inclusive [low, high] range.

    Args:
        value: The value to clamp.
        low: The inclusive lower bound.
        high: The inclusive upper bound.

    Returns:
        The clamped value.
    """
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ScoreType(Enum):
    """Classification of score values tracked by leaderboards."""

    SCORE = "score"
    TIME = "time"
    KILLS = "kills"
    WINS = "wins"
    LEVEL = "level"
    ASSISTS = "assists"
    COMBO = "combo"
    DISTANCE = "distance"
    COLLECTIBLES = "collectibles"
    CUSTOM = "custom"


class SortOrder(Enum):
    """Direction used to rank entries on a leaderboard."""

    DESCENDING = "descending"
    ASCENDING = "ascending"


class LeaderboardScope(Enum):
    """Audience scope for a leaderboard."""

    GLOBAL = "global"
    REGIONAL = "regional"
    FRIENDS = "friends"
    GUILD = "guild"
    CUSTOM = "custom"


class SeasonStatus(Enum):
    """Lifecycle states for a ranked season."""

    UPCOMING = "upcoming"
    ACTIVE = "active"
    ENDED = "ended"


class RankTier(Enum):
    """Competitive tiers ordered from lowest to highest."""

    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"
    PLATINUM = "platinum"
    DIAMOND = "diamond"
    MASTER = "master"
    GRANDMASTER = "grandmaster"
    LEGEND = "legend"


class LeaderboardEventKind(Enum):
    """Audit event kinds emitted by the leaderboard system."""

    LEADERBOARD_CREATED = "leaderboard_created"
    SCORE_SUBMITTED = "score_submitted"
    ENTRY_UPDATED = "entry_updated"
    RANK_CHANGED = "rank_changed"
    SEASON_CREATED = "season_created"
    SEASON_STARTED = "season_started"
    SEASON_ENDED = "season_ended"
    TIER_ASSIGNED = "tier_assigned"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class Leaderboard:
    """A leaderboard definition.

    Attributes:
        leaderboard_id: Unique identifier for the leaderboard.
        name: Display name of the leaderboard.
        description: Human-readable description.
        score_type: The ScoreType used to interpret score values.
        sort_order: The SortOrder used to rank entries.
        scope: The LeaderboardScope audience.
        max_entries: Maximum number of entries permitted on the leaderboard.
        created_at: Timestamp when the leaderboard was created.
        metadata: Free-form metadata bag.
    """

    leaderboard_id: str = field(default_factory=lambda: _new_id("lb"))
    name: str = "Untitled Leaderboard"
    description: str = ""
    score_type: ScoreType = ScoreType.SCORE
    sort_order: SortOrder = SortOrder.DESCENDING
    scope: LeaderboardScope = LeaderboardScope.GLOBAL
    max_entries: int = 1000
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "leaderboard_id": self.leaderboard_id,
            "name": self.name,
            "description": self.description,
            "score_type": self.score_type.value,
            "sort_order": self.sort_order.value,
            "scope": self.scope.value,
            "max_entries": self.max_entries,
            "created_at": self.created_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LeaderboardEntry:
    """A per-player entry on a leaderboard.

    Attributes:
        entry_id: Unique identifier for the entry.
        leaderboard_id: The leaderboard this entry belongs to.
        player_id: The player identifier.
        player_name: Display name of the player.
        score: The current best score for the player on this leaderboard.
        rank: The current rank position (1-based).
        previous_rank: The rank position before the most recent recompute.
        submissions_count: Number of score submissions made by this player.
        first_submitted_at: Timestamp of the first submission.
        last_submitted_at: Timestamp of the most recent submission.
        metadata: Free-form metadata bag.
    """

    entry_id: str = field(default_factory=lambda: _new_id("entry"))
    leaderboard_id: str = ""
    player_id: str = ""
    player_name: str = ""
    score: float = 0.0
    rank: int = 0
    previous_rank: Optional[int] = None
    submissions_count: int = 0
    first_submitted_at: float = field(default_factory=_now)
    last_submitted_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "leaderboard_id": self.leaderboard_id,
            "player_id": self.player_id,
            "player_name": self.player_name,
            "score": self.score,
            "rank": self.rank,
            "previous_rank": self.previous_rank,
            "submissions_count": self.submissions_count,
            "first_submitted_at": self.first_submitted_at,
            "last_submitted_at": self.last_submitted_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class ScoreRecord:
    """An atomic validated score submission record.

    Attributes:
        score_id: Unique identifier for the score record.
        leaderboard_id: The leaderboard the score was submitted to.
        player_id: The player who submitted the score.
        score_value: The raw score value submitted.
        submitted_at: Timestamp when the score was submitted.
        validated: Whether the score passed validation.
        metadata: Free-form metadata bag.
    """

    score_id: str = field(default_factory=lambda: _new_id("score"))
    leaderboard_id: str = ""
    player_id: str = ""
    score_value: float = 0.0
    submitted_at: float = field(default_factory=_now)
    validated: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "score_id": self.score_id,
            "leaderboard_id": self.leaderboard_id,
            "player_id": self.player_id,
            "score_value": self.score_value,
            "submitted_at": self.submitted_at,
            "validated": self.validated,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class RankingSeason:
    """A time-boxed ranked season tied to a leaderboard.

    Attributes:
        season_id: Unique identifier for the season.
        name: Display name of the season.
        leaderboard_id: The leaderboard this season ranks.
        status: The current SeasonStatus.
        start_at: Timestamp when the season starts (or started).
        end_at: Timestamp when the season ends (or ended).
        current_day: The current day index within the season.
        total_days: The total number of days the season spans.
        participant_count: Number of participants in the season.
        metadata: Free-form metadata bag.
    """

    season_id: str = field(default_factory=lambda: _new_id("season"))
    name: str = "Untitled Season"
    leaderboard_id: str = ""
    status: SeasonStatus = SeasonStatus.UPCOMING
    start_at: float = field(default_factory=_now)
    end_at: float = field(default_factory=_now)
    current_day: int = 0
    total_days: int = 30
    participant_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "season_id": self.season_id,
            "name": self.name,
            "leaderboard_id": self.leaderboard_id,
            "status": self.status.value,
            "start_at": self.start_at,
            "end_at": self.end_at,
            "current_day": self.current_day,
            "total_days": self.total_days,
            "participant_count": self.participant_count,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class PlayerRank:
    """A per-player tier and ranking within a season.

    Attributes:
        rank_id: Unique identifier for the player rank record.
        season_id: The season this rank belongs to.
        player_id: The player identifier.
        tier: The RankTier assigned to the player.
        rank_position: The numeric rank position within the season.
        score: The score used to derive the rank.
        games_played: Number of games played in the season.
        wins: Number of wins in the season.
        losses: Number of losses in the season.
        win_rate: Computed win rate as a fraction in [0.0, 1.0].
        assigned_at: Timestamp when the tier was assigned.
        metadata: Free-form metadata bag.
    """

    rank_id: str = field(default_factory=lambda: _new_id("rank"))
    season_id: str = ""
    player_id: str = ""
    tier: RankTier = RankTier.BRONZE
    rank_position: int = 0
    score: float = 0.0
    games_played: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0
    assigned_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank_id": self.rank_id,
            "season_id": self.season_id,
            "player_id": self.player_id,
            "tier": self.tier.value,
            "rank_position": self.rank_position,
            "score": self.score,
            "games_played": self.games_played,
            "wins": self.wins,
            "losses": self.losses,
            "win_rate": self.win_rate,
            "assigned_at": self.assigned_at,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass
class LeaderboardStats:
    """Aggregate counters describing the leaderboard system state.

    Attributes:
        total_leaderboards: Number of registered leaderboards.
        total_entries: Number of entries across all leaderboards.
        total_scores: Number of score records stored.
        total_seasons: Number of seasons created.
        total_player_ranks: Number of player rank records stored.
        avg_entries_per_leaderboard: Average entries per leaderboard.
    """

    total_leaderboards: int = 0
    total_entries: int = 0
    total_scores: int = 0
    total_seasons: int = 0
    total_player_ranks: int = 0
    avg_entries_per_leaderboard: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_leaderboards": self.total_leaderboards,
            "total_entries": self.total_entries,
            "total_scores": self.total_scores,
            "total_seasons": self.total_seasons,
            "total_player_ranks": self.total_player_ranks,
            "avg_entries_per_leaderboard": self.avg_entries_per_leaderboard,
        }


@dataclass
class LeaderboardEvent:
    """An audit event emitted by the leaderboard system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The LeaderboardEventKind classification.
        timestamp: When the event occurred.
        payload: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: LeaderboardEventKind = LeaderboardEventKind.SCORE_SUBMITTED
    timestamp: float = field(default_factory=_now)
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "timestamp": self.timestamp,
            "payload": dict(self.payload) if self.payload else {},
        }


@dataclass
class LeaderboardSnapshot:
    """An immutable snapshot of the entire leaderboard system state.

    Attributes:
        initialized: Whether the engine has completed initialization.
        leaderboards: List of all leaderboards.
        entries: List of all entries.
        scores: List of all score records.
        seasons: List of all seasons.
        player_ranks: List of all player rank records.
        events: List of all audit events.
        stats: Aggregate statistics.
    """

    initialized: bool = False
    leaderboards: List[Leaderboard] = field(default_factory=list)
    entries: List[LeaderboardEntry] = field(default_factory=list)
    scores: List[ScoreRecord] = field(default_factory=list)
    seasons: List[RankingSeason] = field(default_factory=list)
    player_ranks: List[PlayerRank] = field(default_factory=list)
    events: List[LeaderboardEvent] = field(default_factory=list)
    stats: LeaderboardStats = field(default_factory=LeaderboardStats)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "initialized": self.initialized,
            "leaderboards": [lb.to_dict() for lb in self.leaderboards],
            "entries": [e.to_dict() for e in self.entries],
            "scores": [s.to_dict() for s in self.scores],
            "seasons": [s.to_dict() for s in self.seasons],
            "player_ranks": [r.to_dict() for r in self.player_ranks],
            "events": [e.to_dict() for e in self.events],
            "stats": self.stats.to_dict(),
        }


# ---------------------------------------------------------------------------
# Leaderboard System Engine (Singleton)
# ---------------------------------------------------------------------------


class LeaderboardSystemEngine:
    """Comprehensive leaderboard, scoring, and ranking orchestration engine.

    Manages leaderboard definitions, player entries, score submissions,
    ranked seasons, and tier assignments. Implements the singleton pattern
    with double-checked locking for thread-safe access. All public methods
    are guarded by a re-entrant lock.
    """

    _instance: Optional["LeaderboardSystemEngine"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "LeaderboardSystemEngine":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "LeaderboardSystemEngine":
        """Get the singleton instance of the leaderboard system engine.

        Does not reset the ``_initialized`` flag; only constructs the
        instance if it has not been created yet.
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return

            # Leaderboard registry keyed by leaderboard id.
            self._leaderboards: Dict[str, Leaderboard] = {}
            # Entries keyed by composite "{leaderboard_id}:{player_id}".
            self._entries: Dict[str, LeaderboardEntry] = {}
            # Score records keyed by score id.
            self._scores: Dict[str, ScoreRecord] = {}
            # Seasons keyed by season id.
            self._seasons: Dict[str, RankingSeason] = {}
            # Player ranks keyed by composite "{season_id}:{player_id}".
            self._player_ranks: Dict[str, PlayerRank] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[LeaderboardEvent] = []

            # Counters maintained for fast stats retrieval.
            self._leaderboard_counter: int = 0
            self._entry_counter: int = 0
            self._score_counter: int = 0
            self._season_counter: int = 0
            self._player_rank_counter: int = 0
            self._event_counter: int = 0

            self._initialized: bool = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed leaderboards, entries, a season, and ranks."""
        # Leaderboard 1: Global High Score (descending score).
        lb1 = self._create_leaderboard_internal(
            name="Global High Score",
            description="Top scores across all players worldwide.",
            score_type=ScoreType.SCORE,
            sort_order=SortOrder.DESCENDING,
            scope=LeaderboardScope.GLOBAL,
            max_entries=1000,
            metadata={"seed": True},
        )

        # Leaderboard 2: Speed Run Times (ascending time).
        lb2 = self._create_leaderboard_internal(
            name="Speed Run Times",
            description="Fastest completion times for the main campaign.",
            score_type=ScoreType.TIME,
            sort_order=SortOrder.ASCENDING,
            scope=LeaderboardScope.GLOBAL,
            max_entries=500,
            metadata={"seed": True},
        )

        # Entries for leaderboard 1: descending scores 10000 -> 6500.
        lb1_players = [
            ("Alex", 10000.0),
            ("Beth", 9500.0),
            ("Chen", 9000.0),
            ("Dana", 8500.0),
            ("Ezra", 8000.0),
            ("Finn", 7500.0),
            ("Gina", 7000.0),
            ("Hugo", 6500.0),
        ]
        for idx, (player_name, score_value) in enumerate(lb1_players):
            player_id = f"player_{idx + 1}"
            self._submit_score_internal(
                leaderboard_id=lb1.leaderboard_id,
                player_id=player_id,
                player_name=player_name,
                score_value=score_value,
                metadata={"seed": True},
            )

        # Entries for leaderboard 2: ascending times 120.5 -> 158.3.
        lb2_players = [
            ("Alex", 120.5),
            ("Beth", 135.2),
            ("Chen", 142.8),
            ("Dana", 158.3),
        ]
        for idx, (player_name, score_value) in enumerate(lb2_players):
            player_id = f"player_{idx + 1}"
            self._submit_score_internal(
                leaderboard_id=lb2.leaderboard_id,
                player_id=player_id,
                player_name=player_name,
                score_value=score_value,
                metadata={"seed": True},
            )

        # One active season tied to leaderboard 1.
        season = self._create_season_internal(
            name="Season 1 - Genesis",
            leaderboard_id=lb1.leaderboard_id,
            total_days=90,
            start_at=_now(),
            metadata={"seed": True},
        )
        # Seed season is already active with day 15 and 8 participants.
        season.status = SeasonStatus.ACTIVE
        season.current_day = 15
        season.participant_count = 8
        season.end_at = season.start_at + (season.total_days * 86400.0)
        self._record_event(
            LeaderboardEventKind.SEASON_STARTED,
            {"season_id": season.season_id, "name": season.name},
        )

        # Five player ranks for the seed season.
        seed_ranks = [
            ("player_1", "Alex", RankTier.DIAMOND, 10000.0),
            ("player_2", "Beth", RankTier.PLATINUM, 9500.0),
            ("player_3", "Chen", RankTier.GOLD, 9000.0),
            ("player_4", "Dana", RankTier.SILVER, 8500.0),
            ("player_5", "Ezra", RankTier.BRONZE, 8000.0),
        ]
        for position, (player_id, player_name, tier, score_value) in enumerate(
            seed_ranks, start=1
        ):
            self._assign_tier_internal(
                season_id=season.season_id,
                player_id=player_id,
                tier=tier,
                score=score_value,
                games_played=10,
                wins=6,
                losses=4,
                rank_position=position,
                metadata={"seed": True, "player_name": player_name},
            )

    # ------------------------------------------------------------------
    # Leaderboard Management
    # ------------------------------------------------------------------

    def create_leaderboard(
        self,
        name: str,
        description: str,
        score_type: ScoreType,
        sort_order: SortOrder,
        scope: LeaderboardScope,
        max_entries: int = 1000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Leaderboard:
        """Create a new leaderboard definition.

        Args:
            name: Display name of the leaderboard.
            description: Human-readable description.
            score_type: The ScoreType used to interpret score values.
            sort_order: The SortOrder used to rank entries.
            scope: The LeaderboardScope audience.
            max_entries: Maximum number of entries permitted.
            metadata: Optional free-form metadata bag.

        Returns:
            The newly created Leaderboard.
        """
        with self._lock:
            return self._create_leaderboard_internal(
                name=name,
                description=description,
                score_type=score_type,
                sort_order=sort_order,
                scope=scope,
                max_entries=max_entries,
                metadata=metadata,
            )

    def _create_leaderboard_internal(
        self,
        name: str,
        description: str,
        score_type: ScoreType,
        sort_order: SortOrder,
        scope: LeaderboardScope,
        max_entries: int = 1000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Leaderboard:
        """Internal leaderboard creation (caller must hold self._lock)."""
        if len(self._leaderboards) >= _MAX_LEADERBOARDS:
            # FIFO eviction: drop the oldest leaderboard.
            oldest_id = next(iter(self._leaderboards), None)
            if oldest_id is not None:
                self._leaderboards.pop(oldest_id, None)

        leaderboard = Leaderboard(
            name=name,
            description=description,
            score_type=score_type,
            sort_order=sort_order,
            scope=scope,
            max_entries=max(1, max_entries),
            metadata=dict(metadata) if metadata else {},
        )
        self._leaderboards[leaderboard.leaderboard_id] = leaderboard
        self._leaderboard_counter += 1

        self._record_event(
            LeaderboardEventKind.LEADERBOARD_CREATED,
            {
                "leaderboard_id": leaderboard.leaderboard_id,
                "name": name,
                "scope": scope.value,
                "score_type": score_type.value,
            },
        )
        return leaderboard

    def list_leaderboards(
        self,
        scope: Optional[LeaderboardScope] = None,
        score_type: Optional[ScoreType] = None,
    ) -> List[Leaderboard]:
        """Return leaderboards optionally filtered by scope and score type.

        Args:
            scope: Optional scope filter.
            score_type: Optional score type filter.

        Returns:
            A list of matching Leaderboard objects.
        """
        with self._lock:
            leaderboards = list(self._leaderboards.values())
        result: List[Leaderboard] = []
        for leaderboard in leaderboards:
            if scope is not None and leaderboard.scope != scope:
                continue
            if score_type is not None and leaderboard.score_type != score_type:
                continue
            result.append(leaderboard)
        return result

    def get_leaderboard(self, leaderboard_id: str) -> Optional[Leaderboard]:
        """Retrieve a leaderboard by its identifier.

        Args:
            leaderboard_id: The unique identifier of the leaderboard.

        Returns:
            The Leaderboard if found, otherwise None.
        """
        with self._lock:
            return self._leaderboards.get(leaderboard_id)

    # ------------------------------------------------------------------
    # Score Submission and Entries
    # ------------------------------------------------------------------

    def submit_score(
        self,
        leaderboard_id: str,
        player_id: str,
        player_name: str,
        score_value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScoreRecord:
        """Submit a score to a leaderboard.

        Creates a score record, updates or creates the player's entry, and
        recomputes ranks for that leaderboard. The entry's score is updated
        to the better of the current and new score according to the
        leaderboard's sort order.

        Args:
            leaderboard_id: The target leaderboard.
            player_id: The player submitting the score.
            player_name: Display name of the player.
            score_value: The raw score value.
            metadata: Optional free-form metadata bag.

        Returns:
            The created ScoreRecord.
        """
        with self._lock:
            return self._submit_score_internal(
                leaderboard_id=leaderboard_id,
                player_id=player_id,
                player_name=player_name,
                score_value=score_value,
                metadata=metadata,
            )

    def _submit_score_internal(
        self,
        leaderboard_id: str,
        player_id: str,
        player_name: str,
        score_value: float,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ScoreRecord:
        """Internal score submission (caller must hold self._lock)."""
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard is None:
            raise KeyError(f"Leaderboard not found: {leaderboard_id}")

        # Enforce the score store capacity with FIFO eviction.
        if len(self._scores) >= _MAX_SCORES:
            oldest_score_id = next(iter(self._scores), None)
            if oldest_score_id is not None:
                self._scores.pop(oldest_score_id, None)

        score_record = ScoreRecord(
            leaderboard_id=leaderboard_id,
            player_id=player_id,
            score_value=score_value,
            validated=True,
            metadata=dict(metadata) if metadata else {},
        )
        self._scores[score_record.score_id] = score_record
        self._score_counter += 1

        self._record_event(
            LeaderboardEventKind.SCORE_SUBMITTED,
            {
                "score_id": score_record.score_id,
                "leaderboard_id": leaderboard_id,
                "player_id": player_id,
                "score_value": score_value,
            },
        )

        # Update or create the player's entry.
        entry_key = f"{leaderboard_id}:{player_id}"
        now = _now()
        entry = self._entries.get(entry_key)
        is_new_best = False
        if entry is None:
            # Enforce the entry store capacity with FIFO eviction.
            if len(self._entries) >= _MAX_ENTRIES:
                oldest_entry_key = next(iter(self._entries), None)
                if oldest_entry_key is not None:
                    self._entries.pop(oldest_entry_key, None)
            entry = LeaderboardEntry(
                leaderboard_id=leaderboard_id,
                player_id=player_id,
                player_name=player_name,
                score=score_value,
                submissions_count=1,
                first_submitted_at=now,
                last_submitted_at=now,
                metadata=dict(metadata) if metadata else {},
            )
            self._entries[entry_key] = entry
            self._entry_counter += 1
            is_new_best = True
        else:
            entry.submissions_count += 1
            entry.last_submitted_at = now
            entry.player_name = player_name or entry.player_name
            # Determine whether the new score is an improvement.
            if leaderboard.sort_order == SortOrder.DESCENDING:
                if score_value > entry.score:
                    entry.score = score_value
                    is_new_best = True
            else:
                if score_value < entry.score:
                    entry.score = score_value
                    is_new_best = True
            if metadata:
                entry.metadata.update(metadata)

        self._record_event(
            LeaderboardEventKind.ENTRY_UPDATED,
            {
                "entry_id": entry.entry_id,
                "leaderboard_id": leaderboard_id,
                "player_id": player_id,
                "score": entry.score,
                "submissions_count": entry.submissions_count,
                "new_best": is_new_best,
            },
        )

        # Recompute ranks for the affected leaderboard.
        self._recompute_ranks(leaderboard_id)

        return score_record

    def get_entry(
        self,
        leaderboard_id: str,
        player_id: str,
    ) -> Optional[LeaderboardEntry]:
        """Retrieve a player's entry on a leaderboard.

        Args:
            leaderboard_id: The target leaderboard.
            player_id: The player identifier.

        Returns:
            The LeaderboardEntry if found, otherwise None.
        """
        with self._lock:
            return self._entries.get(f"{leaderboard_id}:{player_id}")

    def list_entries(
        self,
        leaderboard_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> List[LeaderboardEntry]:
        """Return entries on a leaderboard sorted by rank.

        Args:
            leaderboard_id: The target leaderboard.
            limit: Maximum number of entries to return.
            offset: Number of entries to skip before returning.

        Returns:
            A list of LeaderboardEntry objects ordered by rank.
        """
        with self._lock:
            entries = [
                e
                for e in self._entries.values()
                if e.leaderboard_id == leaderboard_id
            ]
            entries.sort(key=lambda e: (e.rank if e.rank > 0 else len(entries) + 1))
            start = max(0, offset)
            end = start + max(0, limit)
            return entries[start:end]

    def get_rank(self, leaderboard_id: str, player_id: str) -> Optional[int]:
        """Return the player's rank position on a leaderboard.

        Args:
            leaderboard_id: The target leaderboard.
            player_id: The player identifier.

        Returns:
            The 1-based rank position, or None if the player has no entry.
        """
        with self._lock:
            entry = self._entries.get(f"{leaderboard_id}:{player_id}")
            if entry is None:
                return None
            return entry.rank

    def get_top_entries(
        self,
        leaderboard_id: str,
        count: int = 10,
    ) -> List[LeaderboardEntry]:
        """Return the top-ranked entries on a leaderboard.

        Args:
            leaderboard_id: The target leaderboard.
            count: Maximum number of top entries to return.

        Returns:
            A list of LeaderboardEntry objects ordered by rank.
        """
        with self._lock:
            entries = [
                e
                for e in self._entries.values()
                if e.leaderboard_id == leaderboard_id
            ]
            entries.sort(key=lambda e: (e.rank if e.rank > 0 else len(entries) + 1))
            return entries[: max(0, count)]

    def get_neighbors(
        self,
        leaderboard_id: str,
        player_id: str,
        window: int = 5,
    ) -> List[LeaderboardEntry]:
        """Return entries around the player's rank on a leaderboard.

        Returns up to ``2 * window + 1`` entries centered on the player's
        rank, clamped to the valid rank range.

        Args:
            leaderboard_id: The target leaderboard.
            player_id: The player identifier.
            window: Number of entries to include on each side of the player.

        Returns:
            A list of LeaderboardEntry objects around the player's rank.
        """
        with self._lock:
            entries = [
                e
                for e in self._entries.values()
                if e.leaderboard_id == leaderboard_id
            ]
            entries.sort(key=lambda e: (e.rank if e.rank > 0 else len(entries) + 1))
            if not entries:
                return []

            target = self._entries.get(f"{leaderboard_id}:{player_id}")
            if target is None or target.rank <= 0:
                return entries[: max(0, window)]

            target_rank = target.rank
            low = max(1, target_rank - window)
            high = min(len(entries), target_rank + window)
            result: List[LeaderboardEntry] = []
            for entry in entries:
                if entry.rank <= 0:
                    continue
                if low <= entry.rank <= high:
                    result.append(entry)
            return result

    # ------------------------------------------------------------------
    # Rank Recomputation
    # ------------------------------------------------------------------

    def _recompute_ranks(self, leaderboard_id: str) -> None:
        """Recompute ranks for a leaderboard (caller must hold self._lock).

        Sorts entries by score according to the leaderboard's sort order,
        assigns sequential 1-based ranks, and records each entry's previous
        rank so rank-change deltas can be observed.
        """
        leaderboard = self._leaderboards.get(leaderboard_id)
        if leaderboard is None:
            return

        # Collect the entries for this leaderboard.
        entries = [
            e
            for e in self._entries.values()
            if e.leaderboard_id == leaderboard_id
        ]
        if not entries:
            return

        # Capture current ranks as previous_rank before reassigning.
        for entry in entries:
            entry.previous_rank = entry.rank if entry.rank > 0 else None

        # Sort according to the leaderboard's sort order.
        if leaderboard.sort_order == SortOrder.DESCENDING:
            entries.sort(key=lambda e: e.score, reverse=True)
        else:
            entries.sort(key=lambda e: e.score, reverse=False)

        # Assign sequential 1-based ranks and emit rank-change events.
        for position, entry in enumerate(entries, start=1):
            old_rank = entry.previous_rank
            entry.rank = position
            if old_rank is not None and old_rank != position:
                self._record_event(
                    LeaderboardEventKind.RANK_CHANGED,
                    {
                        "entry_id": entry.entry_id,
                        "leaderboard_id": leaderboard_id,
                        "player_id": entry.player_id,
                        "previous_rank": old_rank,
                        "new_rank": position,
                    },
                )

    # ------------------------------------------------------------------
    # Season Management
    # ------------------------------------------------------------------

    def create_season(
        self,
        name: str,
        leaderboard_id: str,
        total_days: int,
        start_at: Optional[float] = None,
    ) -> RankingSeason:
        """Create a new ranked season in the UPCOMING status.

        Args:
            name: Display name of the season.
            leaderboard_id: The leaderboard this season ranks.
            total_days: Total number of days the season spans.
            start_at: Optional start timestamp; defaults to now.

        Returns:
            The newly created RankingSeason.
        """
        with self._lock:
            return self._create_season_internal(
                name=name,
                leaderboard_id=leaderboard_id,
                total_days=total_days,
                start_at=start_at,
                metadata=None,
            )

    def _create_season_internal(
        self,
        name: str,
        leaderboard_id: str,
        total_days: int,
        start_at: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RankingSeason:
        """Internal season creation (caller must hold self._lock)."""
        if leaderboard_id not in self._leaderboards:
            raise KeyError(f"Leaderboard not found: {leaderboard_id}")

        if len(self._seasons) >= _MAX_SEASONS:
            # FIFO eviction: drop the oldest season.
            oldest_season_id = next(iter(self._seasons), None)
            if oldest_season_id is not None:
                self._seasons.pop(oldest_season_id, None)

        now = _now()
        begin = start_at if start_at is not None else now
        season = RankingSeason(
            name=name,
            leaderboard_id=leaderboard_id,
            status=SeasonStatus.UPCOMING,
            start_at=begin,
            end_at=begin + max(1, total_days) * 86400.0,
            current_day=0,
            total_days=max(1, total_days),
            participant_count=0,
            metadata=dict(metadata) if metadata else {},
        )
        self._seasons[season.season_id] = season
        self._season_counter += 1

        self._record_event(
            LeaderboardEventKind.SEASON_CREATED,
            {
                "season_id": season.season_id,
                "name": name,
                "leaderboard_id": leaderboard_id,
                "total_days": season.total_days,
            },
        )
        return season

    def list_seasons(
        self,
        leaderboard_id: Optional[str] = None,
        status: Optional[SeasonStatus] = None,
    ) -> List[RankingSeason]:
        """Return seasons optionally filtered by leaderboard and status.

        Args:
            leaderboard_id: Optional leaderboard filter.
            status: Optional season status filter.

        Returns:
            A list of matching RankingSeason objects.
        """
        with self._lock:
            seasons = list(self._seasons.values())
        result: List[RankingSeason] = []
        for season in seasons:
            if leaderboard_id is not None and season.leaderboard_id != leaderboard_id:
                continue
            if status is not None and season.status != status:
                continue
            result.append(season)
        return result

    def get_season(self, season_id: str) -> Optional[RankingSeason]:
        """Retrieve a season by its identifier.

        Args:
            season_id: The unique identifier of the season.

        Returns:
            The RankingSeason if found, otherwise None.
        """
        with self._lock:
            return self._seasons.get(season_id)

    def start_season(self, season_id: str) -> Optional[RankingSeason]:
        """Start a season by transitioning it to ACTIVE status.

        Args:
            season_id: The unique identifier of the season.

        Returns:
            The updated RankingSeason, or None if not found.
        """
        with self._lock:
            season = self._seasons.get(season_id)
            if season is None:
                return None
            season.status = SeasonStatus.ACTIVE
            season.start_at = _now() if season.start_at <= 0 else season.start_at
            self._record_event(
                LeaderboardEventKind.SEASON_STARTED,
                {"season_id": season_id, "name": season.name},
            )
            return season

    def end_season(self, season_id: str) -> Optional[RankingSeason]:
        """End a season by transitioning it to ENDED status.

        Args:
            season_id: The unique identifier of the season.

        Returns:
            The updated RankingSeason, or None if not found.
        """
        with self._lock:
            season = self._seasons.get(season_id)
            if season is None:
                return None
            season.status = SeasonStatus.ENDED
            season.end_at = _now()
            self._record_event(
                LeaderboardEventKind.SEASON_ENDED,
                {"season_id": season_id, "name": season.name},
            )
            return season

    # ------------------------------------------------------------------
    # Tier Assignment
    # ------------------------------------------------------------------

    def assign_tier(
        self,
        season_id: str,
        player_id: str,
        tier: RankTier,
        score: float,
        games_played: int = 0,
        wins: int = 0,
        losses: int = 0,
    ) -> PlayerRank:
        """Assign a tier to a player for a season.

        Computes the win rate from games played, wins, and losses. If a
        player rank already exists for the season it is updated, otherwise
        a new PlayerRank is created.

        Args:
            season_id: The target season.
            player_id: The player identifier.
            tier: The RankTier to assign.
            score: The score used to derive the rank.
            games_played: Number of games played in the season.
            wins: Number of wins in the season.
            losses: Number of losses in the season.

        Returns:
            The created or updated PlayerRank.
        """
        with self._lock:
            return self._assign_tier_internal(
                season_id=season_id,
                player_id=player_id,
                tier=tier,
                score=score,
                games_played=games_played,
                wins=wins,
                losses=losses,
                rank_position=None,
                metadata=None,
            )

    def _assign_tier_internal(
        self,
        season_id: str,
        player_id: str,
        tier: RankTier,
        score: float,
        games_played: int = 0,
        wins: int = 0,
        losses: int = 0,
        rank_position: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlayerRank:
        """Internal tier assignment (caller must hold self._lock)."""
        if season_id not in self._seasons:
            raise KeyError(f"Season not found: {season_id}")

        rank_key = f"{season_id}:{player_id}"
        existing = self._player_ranks.get(rank_key)

        total_games = max(0, games_played)
        total_wins = max(0, wins)
        total_losses = max(0, losses)
        if total_games <= 0:
            total_games = total_wins + total_losses
        win_rate = (total_wins / total_games) if total_games > 0 else 0.0

        if existing is None:
            # Enforce the player rank store capacity with FIFO eviction.
            if len(self._player_ranks) >= _MAX_PLAYER_RANKS:
                oldest_rank_key = next(iter(self._player_ranks), None)
                if oldest_rank_key is not None:
                    self._player_ranks.pop(oldest_rank_key, None)
            player_rank = PlayerRank(
                season_id=season_id,
                player_id=player_id,
                tier=tier,
                rank_position=rank_position if rank_position is not None else 0,
                score=score,
                games_played=total_games,
                wins=total_wins,
                losses=total_losses,
                win_rate=win_rate,
                metadata=dict(metadata) if metadata else {},
            )
            self._player_ranks[rank_key] = player_rank
            self._player_rank_counter += 1
        else:
            existing.tier = tier
            if rank_position is not None:
                existing.rank_position = rank_position
            existing.score = score
            existing.games_played = total_games
            existing.wins = total_wins
            existing.losses = total_losses
            existing.win_rate = win_rate
            existing.assigned_at = _now()
            if metadata:
                existing.metadata.update(metadata)
            player_rank = existing

        self._record_event(
            LeaderboardEventKind.TIER_ASSIGNED,
            {
                "rank_id": player_rank.rank_id,
                "season_id": season_id,
                "player_id": player_id,
                "tier": tier.value,
                "score": score,
                "win_rate": win_rate,
            },
        )
        return player_rank

    def list_player_ranks(
        self,
        season_id: Optional[str] = None,
        player_id: Optional[str] = None,
        tier: Optional[RankTier] = None,
    ) -> List[PlayerRank]:
        """Return player ranks optionally filtered by season, player, and tier.

        Args:
            season_id: Optional season filter.
            player_id: Optional player filter.
            tier: Optional tier filter.

        Returns:
            A list of matching PlayerRank objects.
        """
        with self._lock:
            ranks = list(self._player_ranks.values())
        result: List[PlayerRank] = []
        for rank in ranks:
            if season_id is not None and rank.season_id != season_id:
                continue
            if player_id is not None and rank.player_id != player_id:
                continue
            if tier is not None and rank.tier != tier:
                continue
            result.append(rank)
        return result

    def get_player_rank(
        self,
        season_id: str,
        player_id: str,
    ) -> Optional[PlayerRank]:
        """Retrieve a player's rank for a specific season.

        Args:
            season_id: The target season.
            player_id: The player identifier.

        Returns:
            The PlayerRank if found, otherwise None.
        """
        with self._lock:
            return self._player_ranks.get(f"{season_id}:{player_id}")

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: LeaderboardEventKind,
        payload: Dict[str, Any],
    ) -> LeaderboardEvent:
        """Record an audit event (caller must hold self._lock).

        Args:
            kind: The LeaderboardEventKind classification.
            payload: Event-specific payload data.

        Returns:
            The created LeaderboardEvent.
        """
        event = LeaderboardEvent(
            kind=kind,
            payload=dict(payload) if payload else {},
        )
        if len(self._events) >= _MAX_EVENTS:
            # FIFO eviction: drop the oldest event.
            self._events.pop(0, None)
        self._events.append(event)
        self._event_counter += 1
        return event

    def list_events(self, limit: int = 100) -> List[LeaderboardEvent]:
        """Return audit events limited to the most recent ``limit`` entries.

        Args:
            limit: Maximum number of events to return.

        Returns:
            A list of LeaderboardEvent objects ordered from oldest to newest.
        """
        with self._lock:
            events = list(self._events)
        if limit > 0:
            return events[-limit:]
        return events

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def get_stats(self) -> LeaderboardStats:
        """Return aggregate statistics about the leaderboard system.

        Returns:
            A LeaderboardStats instance with current counts.
        """
        with self._lock:
            total_leaderboards = len(self._leaderboards)
            total_entries = len(self._entries)
            total_scores = len(self._scores)
            total_seasons = len(self._seasons)
            total_player_ranks = len(self._player_ranks)
            avg_entries = (
                total_entries / total_leaderboards
                if total_leaderboards > 0
                else 0.0
            )
            return LeaderboardStats(
                total_leaderboards=total_leaderboards,
                total_entries=total_entries,
                total_scores=total_scores,
                total_seasons=total_seasons,
                total_player_ranks=total_player_ranks,
                avg_entries_per_leaderboard=avg_entries,
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current leaderboard system state.

        The ``initialized`` flag is always the first key in the returned
        dictionary, followed by store counts and aggregate statistics.

        Returns:
            A dictionary with the system status.
        """
        with self._lock:
            stats = self.get_stats()
            return {
                "initialized": self._initialized,
                "total_leaderboards": len(self._leaderboards),
                "total_entries": len(self._entries),
                "total_scores": len(self._scores),
                "total_seasons": len(self._seasons),
                "total_player_ranks": len(self._player_ranks),
                "total_events": len(self._events),
                "leaderboard_counter": self._leaderboard_counter,
                "entry_counter": self._entry_counter,
                "score_counter": self._score_counter,
                "season_counter": self._season_counter,
                "player_rank_counter": self._player_rank_counter,
                "event_counter": self._event_counter,
                "stats": stats.to_dict(),
            }

    def get_snapshot(self) -> LeaderboardSnapshot:
        """Capture an immutable snapshot of the leaderboard system state.

        Returns:
            A LeaderboardSnapshot capturing the system state at this moment.
        """
        with self._lock:
            stats = self.get_stats()
            return LeaderboardSnapshot(
                initialized=self._initialized,
                leaderboards=list(self._leaderboards.values()),
                entries=list(self._entries.values()),
                scores=list(self._scores.values()),
                seasons=list(self._seasons.values()),
                player_ranks=list(self._player_ranks.values()),
                events=list(self._events),
                stats=stats,
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data.

        Restores the engine to its initial state, including the seed
        leaderboards, entries, season, and player ranks.
        """
        with self._lock:
            self._leaderboards.clear()
            self._entries.clear()
            self._scores.clear()
            self._seasons.clear()
            self._player_ranks.clear()
            self._events.clear()
            self._leaderboard_counter = 0
            self._entry_counter = 0
            self._score_counter = 0
            self._season_counter = 0
            self._player_rank_counter = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_leaderboard_system() -> LeaderboardSystemEngine:
    """Return the singleton LeaderboardSystemEngine instance."""
    return LeaderboardSystemEngine.get_instance()
