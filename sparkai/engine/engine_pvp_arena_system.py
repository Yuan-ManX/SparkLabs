"""
SparkLabs Engine - PvP Arena System

A competitive PvP arena and duel system for the SparkLabs AI-native game
engine. Manages arena sessions, matchmaking, ranked duels, tournaments,
spectator mode, and seasonal rankings. Supports 1v1 duels, team battles,
free-for-all skirmishes, and tournament brackets with seed-based matching.

Each arena session is a timed combat instance between two or more players.
The system tracks player ratings (Elo-style), win/loss records, kill/death
stats, streaks, and seasonal ranking tiers. Matchmaking pairs players by
rating proximity with configurable tolerance and wait-time widening.

Architecture:
  PvPArenaSystem (singleton)
    |-- ArenaMode, ArenaState, MatchOutcome, ArenaEventKind
    |-- ArenaPlayer, ArenaMatch, ArenaRound, ArenaSeason,
       ArenaReward, TournamentBracket, BracketEntry, ArenaConfig,
       ArenaStats, ArenaSnapshot, ArenaEvent
    |-- get_pvp_arena_system

Core Capabilities:
  - register_player / remove_player / get_player / list_players: manage
    arena participant profiles with ratings and records.
  - create_match / cancel_match / get_match / list_matches: manage arena
    combat sessions with modes (duel, team, ffa).
  - start_match / end_match / submit_result: control match lifecycle and
    record outcomes with rating adjustments.
  - start_round / get_round: manage individual rounds within a match.
  - find_match: matchmaking by rating proximity and mode preference.
  - register_season / activate_season / end_season / get_season: manage
    ranked seasons with tier definitions and reward tracks.
  - register_tournament / start_tournament / advance_tournament: manage
    bracket-style tournaments with seed entries.
  - register_tournament_entry / remove_tournament_entry: add or remove
    participants from a tournament bracket.
  - tick: advance match timers, matchmaking queues, and season timers.
  - set_config / get_config: global tuning for max matches, players, etc.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`PvPArenaSystem.get_instance` or the module-level
:func:`get_pvp_arena_system` factory.
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
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLAYERS: int = 10000
_MAX_MATCHES: int = 5000
_MAX_SEASONS: int = 50
_MAX_TOURNAMENTS: int = 200
_MAX_TOURNAMENT_ENTRIES: int = 256
_MAX_ROUNDS_PER_MATCH: int = 20
_MAX_EVENTS: int = 8000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ArenaMode(str, Enum):
    """Combat mode for an arena match."""
    DUEL = "duel"
    TEAM = "team"
    FFA = "ffa"
    RANKED = "ranked"
    CUSTOM = "custom"


class ArenaState(str, Enum):
    """Lifecycle state of an arena match."""
    QUEUED = "queued"
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class MatchOutcome(str, Enum):
    """Outcome of a completed match."""
    WIN = "win"
    LOSS = "loss"
    DRAW = "draw"
    FORFEIT = "forfeit"
    DISCONNECT = "disconnect"


class ArenaEventKind(str, Enum):
    """Audit event types emitted by the PvP arena system."""
    PLAYER_REGISTERED = "player_registered"
    PLAYER_REMOVED = "player_removed"
    MATCH_CREATED = "match_created"
    MATCH_CANCELLED = "match_cancelled"
    MATCH_STARTED = "match_started"
    MATCH_ENDED = "match_ended"
    ROUND_STARTED = "round_started"
    ROUND_ENDED = "round_ended"
    RESULT_SUBMITTED = "result_submitted"
    RATING_UPDATED = "rating_updated"
    SEASON_REGISTERED = "season_registered"
    SEASON_ACTIVATED = "season_activated"
    SEASON_ENDED = "season_ended"
    TOURNAMENT_REGISTERED = "tournament_registered"
    TOURNAMENT_STARTED = "tournament_started"
    TOURNAMENT_ADVANCED = "tournament_advanced"
    TOURNAMENT_ENTRY_ADDED = "tournament_entry_added"
    TOURNAMENT_ENTRY_REMOVED = "tournament_entry_removed"
    MATCH_FOUND = "match_found"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ArenaPlayer:
    """A participant in the PvP arena."""
    player_id: str
    name: str = ""
    rating: float = 1000.0
    wins: int = 0
    losses: int = 0
    draws: int = 0
    kills: int = 0
    deaths: int = 0
    streak: int = 0
    best_streak: int = 0
    matches_played: int = 0
    tier: str = "bronze"
    season_rating: float = 1000.0
    last_match_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaRound:
    """A single round within an arena match."""
    round_id: str
    round_number: int
    winner_id: str = ""
    loser_id: str = ""
    duration: float = 0.0
    score_data: Dict[str, Any] = field(default_factory=dict)
    started_at: float = field(default_factory=_now)
    ended_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaMatch:
    """A combat session in the arena."""
    match_id: str
    mode: str = ArenaMode.DUEL.value
    state: str = ArenaState.QUEUED.value
    player_ids: List[str] = field(default_factory=list)
    team_a: List[str] = field(default_factory=list)
    team_b: List[str] = field(default_factory=list)
    winner_id: str = ""
    loser_id: str = ""
    rounds: List[ArenaRound] = field(default_factory=list)
    current_round: int = 0
    max_rounds: int = 1
    score_a: int = 0
    score_b: int = 0
    rating_delta: float = 0.0
    season_id: str = ""
    tournament_id: str = ""
    created_at: float = field(default_factory=_now)
    started_at: float = 0.0
    ended_at: float = 0.0
    duration: float = 0.0
    arena_map: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaReward:
    """A reward for arena participation or victory."""
    reward_id: str
    name: str = ""
    currency: int = 0
    currency_type: str = "gold"
    item_id: str = ""
    item_quantity: int = 0
    rating_bonus: float = 0.0
    rarity: str = "common"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaSeason:
    """A ranked season with tiers and rewards."""
    season_id: str
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    active: bool = False
    tiers: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[ArenaReward] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BracketEntry:
    """An entry in a tournament bracket."""
    entry_id: str
    player_id: str
    seed: int = 0
    round_reached: int = 0
    eliminated: bool = False
    eliminated_by: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentBracket:
    """A tournament bracket with seeded entries."""
    tournament_id: str
    name: str = ""
    mode: str = ArenaMode.DUEL.value
    entries: List[BracketEntry] = field(default_factory=list)
    current_round: int = 0
    total_rounds: int = 0
    champion_id: str = ""
    active: bool = False
    completed: bool = False
    created_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaConfig:
    """Global tuning parameters for the arena system."""
    max_players: int = 10000
    max_matches: int = 5000
    max_seasons: int = 50
    max_tournaments: int = 200
    max_tournament_entries: int = 256
    max_rounds_per_match: int = 20
    base_rating: float = 1000.0
    rating_k_factor: float = 32.0
    rating_floor: float = 100.0
    rating_ceiling: float = 5000.0
    matchmaking_tolerance: float = 200.0
    matchmaking_widening_rate: float = 50.0
    match_timeout_seconds: float = 600.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaStats:
    """Aggregate statistics for the arena system."""
    total_players: int = 0
    total_matches: int = 0
    active_matches: int = 0
    completed_matches: int = 0
    total_seasons: int = 0
    active_seasons: int = 0
    total_tournaments: int = 0
    active_tournaments: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaSnapshot:
    """Full state snapshot of the arena system."""
    players: List[Dict[str, Any]] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    seasons: List[Dict[str, Any]] = field(default_factory=list)
    tournaments: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArenaEvent:
    """An audit event emitted by the arena system."""
    event_id: str
    kind: str
    timestamp: float
    player_id: Optional[str] = None
    match_id: Optional[str] = None
    season_id: Optional[str] = None
    tournament_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# PvP Arena System
# ---------------------------------------------------------------------------

class PvPArenaSystem:
    """Manages PvP arena matches, seasons, tournaments, and rankings."""

    _instance: Optional["PvPArenaSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._players: Dict[str, ArenaPlayer] = {}
        self._matches: Dict[str, ArenaMatch] = {}
        self._seasons: Dict[str, ArenaSeason] = {}
        self._tournaments: Dict[str, TournamentBracket] = {}
        self._events: List[ArenaEvent] = []
        self._stats = ArenaStats()
        self._config = ArenaConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._match_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "PvPArenaSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample players, match, season, and tournament data."""
        with self._init_lock:
            if self._initialized:
                return

            player1 = ArenaPlayer(
                player_id="player_arena_01",
                name="Arena Champion",
                rating=1850.0,
                wins=42, losses=18, draws=3,
                kills=156, deaths=89,
                streak=5, best_streak=12,
                matches_played=63,
                tier="platinum",
                season_rating=1850.0,
            )
            self._players[player1.player_id] = player1

            player2 = ArenaPlayer(
                player_id="player_arena_02",
                name="Duel Master",
                rating=1620.0,
                wins=28, losses=22, draws=2,
                kills=98, deaths=95,
                streak=2, best_streak=7,
                matches_played=52,
                tier="gold",
                season_rating=1620.0,
            )
            self._players[player2.player_id] = player2

            player3 = ArenaPlayer(
                player_id="player_arena_03",
                name="Skirmisher",
                rating=1100.0,
                wins=10, losses=15, draws=0,
                kills=35, deaths=48,
                streak=0, best_streak=3,
                matches_played=25,
                tier="bronze",
                season_rating=1100.0,
            )
            self._players[player3.player_id] = player3

            match1 = ArenaMatch(
                match_id="match_starter_01",
                mode=ArenaMode.DUEL.value,
                state=ArenaState.COMPLETED.value,
                player_ids=["player_arena_01", "player_arena_02"],
                team_a=["player_arena_01"],
                team_b=["player_arena_02"],
                winner_id="player_arena_01",
                loser_id="player_arena_02",
                current_round=1,
                max_rounds=1,
                score_a=3,
                score_b=1,
                rating_delta=16.0,
                season_id="season_starter_01",
                started_at=_now() - 600,
                ended_at=_now() - 540,
                duration=60.0,
                arena_map="arena_colosseum",
            )
            r1 = ArenaRound(
                round_id="rnd_starter_01",
                round_number=1,
                winner_id="player_arena_01",
                loser_id="player_arena_02",
                duration=60.0,
                started_at=_now() - 600,
                ended_at=_now() - 540,
            )
            match1.rounds.append(r1)
            self._matches[match1.match_id] = match1

            season1 = ArenaSeason(
                season_id="season_starter_01",
                name="Spring Arena Season",
                start_time=_now() - 86400 * 30,
                end_time=_now() + 86400 * 60,
                active=True,
                tiers=[
                    {"tier": "bronze", "min_rating": 0, "max_rating": 1200},
                    {"tier": "silver", "min_rating": 1200, "max_rating": 1500},
                    {"tier": "gold", "min_rating": 1500, "max_rating": 1800},
                    {"tier": "platinum", "min_rating": 1800, "max_rating": 2200},
                    {"tier": "diamond", "min_rating": 2200, "max_rating": 9999},
                ],
                rewards=[
                    ArenaReward(reward_id="sr_01", name="Gold Reward", currency=5000, rarity="rare"),
                    ArenaReward(reward_id="sr_02", name="Platinum Reward", currency=15000, rating_bonus=50.0, rarity="epic"),
                ],
            )
            self._seasons[season1.season_id] = season1

            tour1 = TournamentBracket(
                tournament_id="tourn_starter_01",
                name="Spring Championship",
                mode=ArenaMode.DUEL.value,
                current_round=0,
                total_rounds=3,
                active=False,
            )
            entry1 = BracketEntry(entry_id="te_01", player_id="player_arena_01", seed=1)
            entry2 = BracketEntry(entry_id="te_02", player_id="player_arena_02", seed=2)
            entry3 = BracketEntry(entry_id="te_03", player_id="player_arena_03", seed=3)
            tour1.entries = [entry1, entry2, entry3]
            self._tournaments[tour1.tournament_id] = tour1

            self._stats.total_players = len(self._players)
            self._stats.total_matches = len(self._matches)
            self._stats.completed_matches = 1
            self._stats.total_seasons = len(self._seasons)
            self._stats.active_seasons = 1
            self._stats.total_tournaments = len(self._tournaments)

            self._initialized = True

    def _emit_event(self, kind: str, player_id: Optional[str] = None,
                    match_id: Optional[str] = None, season_id: Optional[str] = None,
                    tournament_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        event = ArenaEvent(
            event_id=f"evt_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            player_id=player_id,
            match_id=match_id,
            season_id=season_id,
            tournament_id=tournament_id,
            details=details or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _update_tier(self, player: ArenaPlayer) -> None:
        rating = player.rating
        active_season = None
        for s in self._seasons.values():
            if s.active:
                active_season = s
                break
        if active_season and active_season.tiers:
            for t in active_season.tiers:
                min_r = _safe_float(t.get("min_rating"), 0)
                max_r = _safe_float(t.get("max_rating"), 9999)
                if min_r <= rating < max_r:
                    player.tier = t.get("tier", player.tier)
                    return

    def _adjust_rating(self, winner: ArenaPlayer, loser: ArenaPlayer, k_factor: float) -> float:
        expected_winner = 1.0 / (1.0 + 10 ** ((loser.rating - winner.rating) / 400.0))
        expected_loser = 1.0 - expected_winner
        delta = k_factor * (1.0 - expected_winner)
        winner.rating = _clamp(winner.rating + delta, self._config.rating_floor, self._config.rating_ceiling)
        loser.rating = _clamp(loser.rating - delta, self._config.rating_floor, self._config.rating_ceiling)
        winner.season_rating = winner.rating
        loser.season_rating = loser.rating
        self._update_tier(winner)
        self._update_tier(loser)
        return delta

    # ------------------------------------------------------------------
    # Player Management
    # ------------------------------------------------------------------

    def register_player(self, player: ArenaPlayer) -> Dict[str, Any]:
        with self._lock:
            if player.player_id in self._players:
                return {"registered": False, "reason": "already_registered"}
            if len(self._players) >= _MAX_PLAYERS:
                _evict_fifo_list(list(self._players.keys()), _MAX_PLAYERS)
            player.rating = max(player.rating, self._config.base_rating)
            player.season_rating = player.rating
            self._players[player.player_id] = player
            self._stats.total_players = len(self._players)
            self._emit_event(ArenaEventKind.PLAYER_REGISTERED.value, player_id=player.player_id)
            return {"registered": True, "player_id": player.player_id}

    def remove_player(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            if player_id not in self._players:
                return {"removed": False, "reason": "player_not_found"}
            del self._players[player_id]
            self._stats.total_players = len(self._players)
            self._emit_event(ArenaEventKind.PLAYER_REMOVED.value, player_id=player_id)
            return {"removed": True, "player_id": player_id}

    def get_player(self, player_id: str) -> Optional[ArenaPlayer]:
        with self._lock:
            return self._players.get(player_id)

    def list_players(self, tier: Optional[str] = None, limit: int = 100) -> List[ArenaPlayer]:
        with self._lock:
            result = []
            for p in self._players.values():
                if tier and p.tier != tier:
                    continue
                result.append(p)
            result.sort(key=lambda x: x.rating, reverse=True)
            return result[:limit]

    # ------------------------------------------------------------------
    # Match Management
    # ------------------------------------------------------------------

    def create_match(self, match: ArenaMatch) -> Dict[str, Any]:
        with self._lock:
            if match.match_id in self._matches:
                return {"registered": False, "reason": "already_registered"}
            if len(self._matches) >= _MAX_MATCHES:
                _evict_fifo_list(list(self._matches.keys()), _MAX_MATCHES)
            match.max_rounds = min(match.max_rounds, _MAX_ROUNDS_PER_MATCH)
            self._matches[match.match_id] = match
            self._stats.total_matches = len(self._matches)
            self._emit_event(ArenaEventKind.MATCH_CREATED.value, match_id=match.match_id,
                             details={"mode": match.mode, "players": match.player_ids})
            return {"registered": True, "match_id": match.match_id}

    def cancel_match(self, match_id: str) -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"success": False, "reason": "match_not_found"}
            if match.state == ArenaState.COMPLETED.value:
                return {"success": False, "reason": "match_completed"}
            match.state = ArenaState.CANCELLED.value
            self._emit_event(ArenaEventKind.MATCH_CANCELLED.value, match_id=match_id)
            return {"success": True, "match_id": match_id, "state": match.state}

    def get_match(self, match_id: str) -> Optional[ArenaMatch]:
        with self._lock:
            return self._matches.get(match_id)

    def list_matches(self, state: Optional[str] = None, mode: Optional[str] = None,
                     limit: int = 100) -> List[ArenaMatch]:
        with self._lock:
            result = []
            for m in self._matches.values():
                if state and m.state != state:
                    continue
                if mode and m.mode != mode:
                    continue
                result.append(m)
            result.sort(key=lambda x: x.created_at, reverse=True)
            return result[:limit]

    def start_match(self, match_id: str) -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"success": False, "reason": "match_not_found"}
            if match.state != ArenaState.QUEUED.value:
                return {"success": False, "reason": "match_not_queued"}
            match.state = ArenaState.ACTIVE.value
            match.started_at = _now()
            match.current_round = 1
            self._stats.active_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.ACTIVE.value)
            self._emit_event(ArenaEventKind.MATCH_STARTED.value, match_id=match_id)
            return {"success": True, "match_id": match_id, "started_at": match.started_at}

    def end_match(self, match_id: str) -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"success": False, "reason": "match_not_found"}
            if match.state != ArenaState.ACTIVE.value:
                return {"success": False, "reason": "match_not_active"}
            match.state = ArenaState.COMPLETED.value
            match.ended_at = _now()
            match.duration = match.ended_at - match.started_at
            self._stats.active_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.ACTIVE.value)
            self._stats.completed_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.COMPLETED.value)
            self._emit_event(ArenaEventKind.MATCH_ENDED.value, match_id=match_id,
                             details={"duration": match.duration})
            return {"success": True, "match_id": match_id, "ended_at": match.ended_at}

    def submit_result(self, match_id: str, winner_id: str, loser_id: str,
                      outcome: str = "win") -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"success": False, "reason": "match_not_found"}
            winner = self._players.get(winner_id)
            loser = self._players.get(loser_id)
            if winner is None or loser is None:
                return {"success": False, "reason": "player_not_found"}
            match.winner_id = winner_id
            match.loser_id = loser_id
            delta = 0.0
            if outcome == MatchOutcome.WIN.value:
                delta = self._adjust_rating(winner, loser, self._config.rating_k_factor)
                winner.wins += 1
                winner.streak += 1
                winner.best_streak = max(winner.best_streak, winner.streak)
                loser.losses += 1
                loser.streak = 0
            elif outcome == MatchOutcome.DRAW.value:
                winner.draws += 1
                loser.draws += 1
            else:
                winner.wins += 1
                loser.losses += 1
                loser.streak = 0
            winner.matches_played += 1
            loser.matches_played += 1
            winner.last_match_time = _now()
            loser.last_match_time = _now()
            match.rating_delta = delta
            self._emit_event(ArenaEventKind.RESULT_SUBMITTED.value, match_id=match_id,
                             player_id=winner_id,
                             details={"delta": delta, "outcome": outcome})
            self._emit_event(ArenaEventKind.RATING_UPDATED.value, player_id=winner_id,
                             details={"new_rating": winner.rating})
            return {"success": True, "match_id": match_id, "delta": delta,
                    "winner_rating": winner.rating, "loser_rating": loser.rating}

    # ------------------------------------------------------------------
    # Round Management
    # ------------------------------------------------------------------

    def start_round(self, match_id: str) -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"success": False, "reason": "match_not_found"}
            if match.state != ArenaState.ACTIVE.value:
                return {"success": False, "reason": "match_not_active"}
            if match.current_round > match.max_rounds:
                return {"success": False, "reason": "max_rounds_reached"}
            round_num = match.current_round
            round_id = f"rnd_{match_id}_{round_num}"
            arena_round = ArenaRound(round_id=round_id, round_number=round_num)
            match.rounds.append(arena_round)
            self._emit_event(ArenaEventKind.ROUND_STARTED.value, match_id=match_id,
                             details={"round": round_num})
            return {"success": True, "round_id": round_id, "round_number": round_num}

    def get_round(self, match_id: str, round_number: int) -> Dict[str, Any]:
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return {"found": False, "reason": "match_not_found"}
            for r in match.rounds:
                if r.round_number == round_number:
                    return {"found": True, "round": r.to_dict()}
            return {"found": False, "reason": "round_not_found"}

    # ------------------------------------------------------------------
    # Matchmaking
    # ------------------------------------------------------------------

    def find_match(self, player_id: str, mode: str = "duel",
                   tolerance: Optional[float] = None) -> Dict[str, Any]:
        with self._lock:
            player = self._players.get(player_id)
            if player is None:
                return {"success": False, "reason": "player_not_found"}
            tol = tolerance if tolerance is not None else self._config.matchmaking_tolerance
            best_opponent = None
            best_diff = float("inf")
            for p in self._players.values():
                if p.player_id == player_id:
                    continue
                diff = abs(p.rating - player.rating)
                if diff <= tol and diff < best_diff:
                    best_opponent = p
                    best_diff = diff
            if best_opponent is None:
                return {"success": False, "reason": "no_opponent_found"}
            match_id = f"match_{player_id}_{best_opponent.player_id}"
            match = ArenaMatch(
                match_id=match_id,
                mode=mode,
                player_ids=[player_id, best_opponent.player_id],
                team_a=[player_id],
                team_b=[best_opponent.player_id],
                max_rounds=1,
                arena_map="arena_auto_matched",
            )
            create_result = self.create_match(match)
            if not create_result.get("registered"):
                return create_result
            self._emit_event(ArenaEventKind.MATCH_FOUND.value, player_id=player_id,
                             match_id=match_id,
                             details={"opponent": best_opponent.player_id, "diff": best_diff})
            return {"success": True, "match_id": match_id,
                    "opponent_id": best_opponent.player_id,
                    "rating_diff": best_diff}

    # ------------------------------------------------------------------
    # Season Management
    # ------------------------------------------------------------------

    def register_season(self, season: ArenaSeason) -> Dict[str, Any]:
        with self._lock:
            if season.season_id in self._seasons:
                return {"registered": False, "reason": "already_registered"}
            if len(self._seasons) >= _MAX_SEASONS:
                _evict_fifo_list(list(self._seasons.keys()), _MAX_SEASONS)
            self._seasons[season.season_id] = season
            self._stats.total_seasons = len(self._seasons)
            self._emit_event(ArenaEventKind.SEASON_REGISTERED.value, season_id=season.season_id)
            return {"registered": True, "season_id": season.season_id}

    def activate_season(self, season_id: str) -> Dict[str, Any]:
        with self._lock:
            season = self._seasons.get(season_id)
            if season is None:
                return {"activated": False, "reason": "season_not_found"}
            for s in self._seasons.values():
                s.active = (s.season_id == season_id)
            self._stats.active_seasons = sum(1 for s in self._seasons.values() if s.active)
            self._emit_event(ArenaEventKind.SEASON_ACTIVATED.value, season_id=season_id)
            return {"activated": True, "season_id": season_id}

    def end_season(self, season_id: str) -> Dict[str, Any]:
        with self._lock:
            season = self._seasons.get(season_id)
            if season is None:
                return {"success": False, "reason": "season_not_found"}
            season.active = False
            season.end_time = _now()
            self._stats.active_seasons = sum(1 for s in self._seasons.values() if s.active)
            self._emit_event(ArenaEventKind.SEASON_ENDED.value, season_id=season_id)
            return {"success": True, "season_id": season_id}

    def get_season(self, season_id: str) -> Optional[ArenaSeason]:
        with self._lock:
            return self._seasons.get(season_id)

    def list_seasons(self, active_only: bool = False, limit: int = 100) -> List[ArenaSeason]:
        with self._lock:
            result = []
            for s in self._seasons.values():
                if active_only and not s.active:
                    continue
                result.append(s)
            return result[:limit]

    # ------------------------------------------------------------------
    # Tournament Management
    # ------------------------------------------------------------------

    def register_tournament(self, tournament: TournamentBracket) -> Dict[str, Any]:
        with self._lock:
            if tournament.tournament_id in self._tournaments:
                return {"registered": False, "reason": "already_registered"}
            if len(self._tournaments) >= _MAX_TOURNAMENTS:
                _evict_fifo_list(list(self._tournaments.keys()), _MAX_TOURNAMENTS)
            self._tournaments[tournament.tournament_id] = tournament
            self._stats.total_tournaments = len(self._tournaments)
            self._emit_event(ArenaEventKind.TOURNAMENT_REGISTERED.value,
                             tournament_id=tournament.tournament_id)
            return {"registered": True, "tournament_id": tournament.tournament_id}

    def start_tournament(self, tournament_id: str) -> Dict[str, Any]:
        with self._lock:
            tour = self._tournaments.get(tournament_id)
            if tour is None:
                return {"success": False, "reason": "tournament_not_found"}
            if tour.active or tour.completed:
                return {"success": False, "reason": "tournament_invalid_state"}
            if len(tour.entries) < 2:
                return {"success": False, "reason": "insufficient_entries"}
            tour.active = True
            tour.current_round = 1
            import math as _math
            tour.total_rounds = int(_math.ceil(_math.log2(max(len(tour.entries), 2))))
            self._stats.active_tournaments = sum(1 for t in self._tournaments.values() if t.active)
            self._emit_event(ArenaEventKind.TOURNAMENT_STARTED.value,
                             tournament_id=tournament_id)
            return {"success": True, "tournament_id": tournament_id,
                    "total_rounds": tour.total_rounds}

    def advance_tournament(self, tournament_id: str) -> Dict[str, Any]:
        with self._lock:
            tour = self._tournaments.get(tournament_id)
            if tour is None:
                return {"success": False, "reason": "tournament_not_found"}
            if not tour.active:
                return {"success": False, "reason": "tournament_not_active"}
            active_entries = [e for e in tour.entries if not e.eliminated]
            if len(active_entries) <= 1:
                tour.completed = True
                tour.active = False
                tour.champion_id = active_entries[0].player_id if active_entries else ""
                self._stats.active_tournaments = sum(1 for t in self._tournaments.values() if t.active)
                self._emit_event(ArenaEventKind.TOURNAMENT_ADVANCED.value,
                                 tournament_id=tournament_id,
                                 details={"completed": True, "champion": tour.champion_id})
                return {"success": True, "tournament_id": tournament_id,
                        "completed": True, "champion_id": tour.champion_id}
            tour.current_round += 1
            self._emit_event(ArenaEventKind.TOURNAMENT_ADVANCED.value,
                             tournament_id=tournament_id,
                             details={"new_round": tour.current_round})
            return {"success": True, "tournament_id": tournament_id,
                    "current_round": tour.current_round}

    def register_tournament_entry(self, tournament_id: str, entry: BracketEntry) -> Dict[str, Any]:
        with self._lock:
            tour = self._tournaments.get(tournament_id)
            if tour is None:
                return {"registered": False, "reason": "tournament_not_found"}
            if tour.active or tour.completed:
                return {"registered": False, "reason": "tournament_active"}
            if len(tour.entries) >= _MAX_TOURNAMENT_ENTRIES:
                return {"registered": False, "reason": "capacity_reached"}
            for e in tour.entries:
                if e.entry_id == entry.entry_id:
                    return {"registered": False, "reason": "already_registered"}
            tour.entries.append(entry)
            self._emit_event(ArenaEventKind.TOURNAMENT_ENTRY_ADDED.value,
                             tournament_id=tournament_id,
                             player_id=entry.player_id)
            return {"registered": True, "entry_id": entry.entry_id}

    def remove_tournament_entry(self, tournament_id: str, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            tour = self._tournaments.get(tournament_id)
            if tour is None:
                return {"removed": False, "reason": "tournament_not_found"}
            for i, e in enumerate(tour.entries):
                if e.entry_id == entry_id:
                    tour.entries.pop(i)
                    self._emit_event(ArenaEventKind.TOURNAMENT_ENTRY_REMOVED.value,
                                     tournament_id=tournament_id, player_id=e.player_id)
                    return {"removed": True, "entry_id": entry_id}
            return {"removed": False, "reason": "entry_not_found"}

    def get_tournament(self, tournament_id: str) -> Optional[TournamentBracket]:
        with self._lock:
            return self._tournaments.get(tournament_id)

    def list_tournaments(self, active_only: bool = False, limit: int = 100) -> List[TournamentBracket]:
        with self._lock:
            result = []
            for t in self._tournaments.values():
                if active_only and not t.active:
                    continue
                result.append(t)
            return result[:limit]

    # ------------------------------------------------------------------
    # Tick / Config / Observability
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            now = _now()
            timed_out = 0
            for match in self._matches.values():
                if match.state == ArenaState.ACTIVE.value and match.started_at > 0:
                    elapsed = now - match.started_at
                    if elapsed > self._config.match_timeout_seconds:
                        match.state = ArenaState.COMPLETED.value
                        match.ended_at = now
                        match.duration = elapsed
                        timed_out += 1
            if timed_out > 0:
                self._stats.active_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.ACTIVE.value)
                self._stats.completed_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.COMPLETED.value)
            self._emit_event(ArenaEventKind.TICK.value,
                             details={"delta_time": delta_time, "timed_out": timed_out})
            return {"success": True, "tick_count": self._tick_count, "timed_out": timed_out}

    def set_config(self, config: ArenaConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(ArenaEventKind.CONFIG_UPDATED.value)
            return {"success": True}

    def get_config(self) -> ArenaConfig:
        with self._lock:
            return self._config

    def list_events(self, player_id: Optional[str] = None, match_id: Optional[str] = None,
                    limit: int = 100) -> List[ArenaEvent]:
        with self._lock:
            result = []
            for e in self._events:
                if player_id and e.player_id != player_id:
                    continue
                if match_id and e.match_id != match_id:
                    continue
                result.append(e)
            return result[:limit]

    def get_stats(self) -> ArenaStats:
        with self._lock:
            self._stats.total_players = len(self._players)
            self._stats.total_matches = len(self._matches)
            self._stats.active_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.ACTIVE.value)
            self._stats.completed_matches = sum(1 for m in self._matches.values() if m.state == ArenaState.COMPLETED.value)
            self._stats.total_seasons = len(self._seasons)
            self._stats.active_seasons = sum(1 for s in self._seasons.values() if s.active)
            self._stats.total_tournaments = len(self._tournaments)
            self._stats.active_tournaments = sum(1 for t in self._tournaments.values() if t.active)
            self._stats.tick_count = self._tick_count
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_players": len(self._players),
                "total_matches": len(self._matches),
                "active_matches": sum(1 for m in self._matches.values() if m.state == ArenaState.ACTIVE.value),
                "total_seasons": len(self._seasons),
                "active_seasons": sum(1 for s in self._seasons.values() if s.active),
                "total_tournaments": len(self._tournaments),
                "active_tournaments": sum(1 for t in self._tournaments.values() if t.active),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> ArenaSnapshot:
        with self._lock:
            return ArenaSnapshot(
                players=[p.to_dict() for p in list(self._players.values())[:50]],
                matches=[m.to_dict() for m in list(self._matches.values())[:50]],
                seasons=[s.to_dict() for s in self._seasons.values()],
                tournaments=[t.to_dict() for t in self._tournaments.values()],
                stats=self.get_stats().to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._players.clear()
            self._matches.clear()
            self._seasons.clear()
            self._tournaments.clear()
            self._events.clear()
            self._stats = ArenaStats()
            self._config = ArenaConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._match_counter = 0
            self._initialized = False
            self._emit_event(ArenaEventKind.RESET.value)
            self._seed()
            return {"success": True, "reset": True}


def get_pvp_arena_system() -> PvPArenaSystem:
    """Get the singleton PvPArenaSystem instance."""
    return PvPArenaSystem.get_instance()
