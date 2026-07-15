"""
SparkLabs Engine - Tournament & Esports Management System

Manages competitive gaming tournaments across multiple formats including
single elimination, double elimination, round robin, swiss, group stage,
and battle royale. Handles participant registration, check-in, seeding,
bracket generation, match lifecycle (create, start, complete, forfeit,
advance), prize pools with distribution, live standings, and a full audit
event log. Designed as a self-contained singleton system with seed data
for immediate integration testing.

Architecture:
  TournamentEsportsSystem (singleton)
    |-- TournamentFormat, TournamentStatus, MatchStatus, BracketType,
       SeedMethod, PrizeType, PlayerStatus
    |-- TournamentParticipant, TournamentMatch, PrizeEntry, TournamentBracket,
       Tournament, TournamentConfig, TournamentStats, TournamentSnapshot,
       TournamentEvent
    |-- get_tournament_esports_system

Core Capabilities:
  - register_tournament / get_tournament / list_tournaments / remove_tournament
  - register_participant / get_participant / list_participants /
    remove_participant / check_in_participant
  - generate_bracket / get_bracket / list_brackets
  - create_match / get_match / list_matches / start_match / complete_match /
    forfeit_match / advance_winner
  - register_prize / get_prize / list_prizes / distribute_prizes
  - get_standings / calculate_rounds_needed / seed_participants
  - list_events / get_status / get_stats / get_snapshot / get_config /
    set_config / tick / reset

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`TournamentEsportsSystem.get_instance` or the module-level
:func:`get_tournament_esports_system` factory.
"""

from __future__ import annotations

import math
import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TOURNAMENTS: int = 500
_MAX_PARTICIPANTS: int = 50000
_MAX_MATCHES: int = 100000
_MAX_BRACKETS: int = 5000
_MAX_PRIZES: int = 10000
_MAX_EVENTS: int = 10000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


def _safe_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TournamentFormat(str, Enum):
    """Supported tournament competition formats."""

    SINGLE_ELIMINATION = "single_elimination"
    DOUBLE_ELIMINATION = "double_elimination"
    ROUND_ROBIN = "round_robin"
    SWISS = "swiss"
    GROUP_STAGE = "group_stage"
    BATTLE_ROYALE = "battle_royale"


class TournamentStatus(str, Enum):
    """Lifecycle status of a tournament."""

    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    REGISTRATION_CLOSED = "registration_closed"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class MatchStatus(str, Enum):
    """Lifecycle status of an individual match."""

    PENDING = "pending"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FORFEITED = "forfeited"
    DISPUTED = "disputed"


class BracketType(str, Enum):
    """Bracket classification within a tournament."""

    WINNERS = "winners"
    LOSERS = "losers"
    GRAND_FINALS = "grand_finals"
    GROUP_A = "group_a"
    GROUP_B = "group_b"
    GROUP_C = "group_c"
    GROUP_D = "group_d"
    SWISS_ROUND = "swiss_round"


class SeedMethod(str, Enum):
    """Participant seeding strategies."""

    RANDOM = "random"
    SEEDED = "seeded"
    SNAKE = "snake"
    RESERVOIR = "reservoir"


class PrizeType(str, Enum):
    """Categories of tournament prizes."""

    CASH = "cash"
    IN_GAME_CURRENCY = "in_game_currency"
    PHYSICAL_ITEM = "physical_item"
    DIGITAL_ITEM = "digital_item"
    TITLE = "title"
    EMBLEM = "emblem"


class PlayerStatus(str, Enum):
    """Status of a participant within a tournament."""

    REGISTERED = "registered"
    CHECKED_IN = "checked_in"
    ELIMINATED = "eliminated"
    DISQUALIFIED = "disqualified"
    WITHDRAWN = "withdrawn"
    CHAMPION = "champion"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TournamentParticipant:
    """A player or team registered into a tournament."""

    participant_id: str = ""
    name: str = ""
    team_id: str = ""
    seed: int = 0
    status: str = PlayerStatus.REGISTERED.value
    wins: int = 0
    losses: int = 0
    bracket_position: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentMatch:
    """A single competitive match between two participants."""

    match_id: str = ""
    tournament_id: str = ""
    round: int = 0
    bracket_type: str = BracketType.WINNERS.value
    player1_id: str = ""
    player2_id: str = ""
    status: str = MatchStatus.PENDING.value
    winner_id: str = ""
    score_p1: int = 0
    score_p2: int = 0
    scheduled_time: str = ""
    completed_time: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PrizeEntry:
    """A prize awarded for a specific placement in a tournament."""

    prize_id: str = ""
    tournament_id: str = ""
    placement: int = 0
    prize_type: str = PrizeType.CASH.value
    value: float = 0.0
    description: str = ""
    recipient_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentBracket:
    """A bracket containing rounds of matches within a tournament."""

    bracket_id: str = ""
    tournament_id: str = ""
    bracket_type: str = BracketType.WINNERS.value
    rounds: int = 0
    total_rounds: int = 0
    matches: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Tournament:
    """A competitive tournament with participants, brackets, and prizes."""

    tournament_id: str = ""
    name: str = ""
    format: str = TournamentFormat.SINGLE_ELIMINATION.value
    status: str = TournamentStatus.DRAFT.value
    game_id: str = ""
    organizer_id: str = ""
    max_participants: int = 16
    current_participants: int = 0
    start_time: str = ""
    end_time: str = ""
    registration_deadline: str = ""
    seed_method: str = SeedMethod.SEEDED.value
    description: str = ""
    bracket_ids: List[str] = field(default_factory=list)
    prize_pool_ids: List[str] = field(default_factory=list)
    participant_ids: List[str] = field(default_factory=list)
    match_ids: List[str] = field(default_factory=list)
    champion_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentConfig:
    """Runtime configuration for the tournament system."""

    max_tournaments: int = 500
    max_participants_per_tournament: int = 256
    max_matches: int = 10000
    auto_advance: bool = False
    default_match_duration: int = 1800
    enable_seeding: bool = True
    enable_prize_distribution: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentStats:
    """Aggregate statistics for the tournament system."""

    total_tournaments: int = 0
    active_tournaments: int = 0
    completed_tournaments: int = 0
    total_participants: int = 0
    total_matches: int = 0
    total_prizes_distributed: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentSnapshot:
    """Point-in-time snapshot of the entire system state."""

    timestamp: str = ""
    tournaments: List[Dict[str, Any]] = field(default_factory=list)
    participants: List[Dict[str, Any]] = field(default_factory=list)
    matches: List[Dict[str, Any]] = field(default_factory=list)
    brackets: List[Dict[str, Any]] = field(default_factory=list)
    prizes: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TournamentEvent:
    """Audit event emitted by the tournament system."""

    event_id: str = ""
    event_type: str = ""
    timestamp: str = ""
    tournament_id: str = ""
    match_id: str = ""
    participant_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class TournamentEsportsSystem:
    """Manages the full lifecycle of competitive esports tournaments.

    The system is a process-wide singleton. Obtain it via
    :meth:`get_instance` or the module-level
    :func:`get_tournament_esports_system` factory; do not instantiate it
    directly in application code.
    """

    _instance: Optional["TournamentEsportsSystem"] = None
    _lock = threading.RLock()
    _init_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        self._tournaments: Dict[str, Tournament] = {}
        self._participants: Dict[str, TournamentParticipant] = {}
        self._matches: Dict[str, TournamentMatch] = {}
        self._brackets: Dict[str, TournamentBracket] = {}
        self._prizes: Dict[str, PrizeEntry] = {}
        self._events: List[TournamentEvent] = []
        self._config = TournamentConfig()
        self._stats = TournamentStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._match_counter: int = 0
        self._initialized: bool = False
        self._seed()

    @classmethod
    def get_instance(cls) -> "TournamentEsportsSystem":
        """Return the singleton instance, creating it on first call."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        tournament_id: str = "",
        match_id: str = "",
        participant_id: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> TournamentEvent:
        """Append an audit event to the in-memory event log."""
        event = TournamentEvent(
            event_id=f"evt_{self._event_counter:08d}",
            event_type=event_type,
            timestamp=_now(),
            tournament_id=tournament_id,
            match_id=match_id,
            participant_id=participant_id,
            data=data or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _new_match_id(self) -> str:
        """Return a fresh unique match id."""
        mid = f"match_{self._match_counter:04d}"
        self._match_counter += 1
        return mid

    def _update_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_tournaments = len(self._tournaments)
        self._stats.active_tournaments = sum(
            1
            for t in self._tournaments.values()
            if t.status
            in (
                TournamentStatus.IN_PROGRESS.value,
                TournamentStatus.REGISTRATION_OPEN.value,
            )
        )
        self._stats.completed_tournaments = sum(
            1
            for t in self._tournaments.values()
            if t.status == TournamentStatus.COMPLETED.value
        )
        self._stats.total_participants = len(self._participants)
        self._stats.total_matches = len(self._matches)
        self._stats.total_prizes_distributed = sum(
            1 for p in self._prizes.values() if p.recipient_id
        )
        self._stats.tick_count = self._tick_count

    def _participant_ids_for_tournament(self, tournament_id: str) -> List[str]:
        """Return participant ids belonging to a tournament."""
        result: List[str] = []
        for pid, part in self._participants.items():
            if part.metadata.get("tournament_id") == tournament_id:
                result.append(pid)
        return result

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed a realistic set of tournaments, participants, matches, brackets, and prizes."""
        with self._init_lock:
            if self._initialized:
                return

            now = _now()

            # ----------------------------------------------------------
            # Tournament 1: Spring Championship (single elimination, in progress)
            # ----------------------------------------------------------
            t1 = Tournament(
                tournament_id="tournament_spring_championship",
                name="Spring Championship 2026",
                format=TournamentFormat.SINGLE_ELIMINATION.value,
                status=TournamentStatus.IN_PROGRESS.value,
                game_id="game_battlegrounds",
                organizer_id="org_esports_league",
                max_participants=16,
                current_participants=16,
                start_time=now,
                end_time="",
                registration_deadline=now,
                seed_method=SeedMethod.SEEDED.value,
                description="Annual spring esports championship with 16 elite players.",
            )
            self._tournaments[t1.tournament_id] = t1

            spring_players = [
                "player_alpha", "player_beta", "player_gamma", "player_delta",
                "player_epsilon", "player_zeta", "player_eta", "player_theta",
                "player_iota", "player_kappa", "player_lambda", "player_mu",
                "player_nu", "player_xi", "player_omicron", "player_pi",
            ]
            spring_names = [
                "Alpha", "Beta", "Gamma", "Delta",
                "Epsilon", "Zeta", "Eta", "Theta",
                "Iota", "Kappa", "Lambda", "Mu",
                "Nu", "Xi", "Omicron", "Pi",
            ]
            for idx, pid in enumerate(spring_players):
                part = TournamentParticipant(
                    participant_id=pid,
                    name=spring_names[idx],
                    team_id=f"team_{idx % 4}",
                    seed=idx + 1,
                    status=PlayerStatus.CHECKED_IN.value,
                    bracket_position=idx + 1,
                    metadata={"tournament_id": t1.tournament_id},
                )
                self._participants[pid] = part
                t1.participant_ids.append(pid)

            # Winners bracket for spring championship (4 rounds for 16 players)
            bracket_spring = TournamentBracket(
                bracket_id="bracket_spring_winners",
                tournament_id=t1.tournament_id,
                bracket_type=BracketType.WINNERS.value,
                rounds=4,
                total_rounds=4,
                matches=[],
                metadata={"created_at": now},
            )
            self._brackets[bracket_spring.bracket_id] = bracket_spring
            t1.bracket_ids.append(bracket_spring.bracket_id)

            r1_pairs = [
                ("player_alpha", "player_beta", "player_alpha", 2, 1, MatchStatus.COMPLETED.value),
                ("player_gamma", "player_delta", "player_delta", 2, 0, MatchStatus.COMPLETED.value),
                ("player_epsilon", "player_zeta", "player_epsilon", 2, 1, MatchStatus.COMPLETED.value),
                ("player_eta", "player_theta", "player_theta", 2, 0, MatchStatus.COMPLETED.value),
                ("player_iota", "player_kappa", "", 1, 1, MatchStatus.IN_PROGRESS.value),
                ("player_lambda", "player_mu", "", 0, 0, MatchStatus.PENDING.value),
                ("player_nu", "player_xi", "", 0, 0, MatchStatus.PENDING.value),
                ("player_omicron", "player_pi", "", 0, 0, MatchStatus.PENDING.value),
            ]
            for m_idx, (p1, p2, winner, s1, s2, mstatus) in enumerate(r1_pairs, start=1):
                mid = f"match_spring_r1_m{m_idx}"
                match = TournamentMatch(
                    match_id=mid,
                    tournament_id=t1.tournament_id,
                    round=1,
                    bracket_type=BracketType.WINNERS.value,
                    player1_id=p1,
                    player2_id=p2,
                    status=mstatus,
                    winner_id=winner,
                    score_p1=s1,
                    score_p2=s2,
                    scheduled_time=now,
                    completed_time=now if mstatus == MatchStatus.COMPLETED.value else "",
                    metadata={"bracket_id": bracket_spring.bracket_id},
                )
                self._matches[mid] = match
                t1.match_ids.append(mid)
                bracket_spring.matches.append(mid)
                if winner:
                    self._participants[winner].wins += 1
                    loser = p1 if winner == p2 else p2
                    self._participants[loser].losses += 1

            r2_pairs = [
                ("player_alpha", "player_delta", "", 0, 0, MatchStatus.READY.value),
                ("player_epsilon", "player_theta", "", 0, 0, MatchStatus.READY.value),
            ]
            for m_idx, (p1, p2, winner, s1, s2, mstatus) in enumerate(r2_pairs, start=1):
                mid = f"match_spring_r2_m{m_idx}"
                match = TournamentMatch(
                    match_id=mid,
                    tournament_id=t1.tournament_id,
                    round=2,
                    bracket_type=BracketType.WINNERS.value,
                    player1_id=p1,
                    player2_id=p2,
                    status=mstatus,
                    winner_id=winner,
                    score_p1=s1,
                    score_p2=s2,
                    scheduled_time=now,
                    completed_time="",
                    metadata={"bracket_id": bracket_spring.bracket_id},
                )
                self._matches[mid] = match
                t1.match_ids.append(mid)
                bracket_spring.matches.append(mid)

            # Prize for spring championship (undistributed)
            prize_spring = PrizeEntry(
                prize_id="prize_spring_1st",
                tournament_id=t1.tournament_id,
                placement=1,
                prize_type=PrizeType.CASH.value,
                value=10000.0,
                description="Spring Championship Grand Prize",
                recipient_id="",
                metadata={"currency": "usd"},
            )
            self._prizes[prize_spring.prize_id] = prize_spring
            t1.prize_pool_ids.append(prize_spring.prize_id)

            # ----------------------------------------------------------
            # Tournament 2: Summer Swiss (swiss, registration open)
            # ----------------------------------------------------------
            t2 = Tournament(
                tournament_id="tournament_summer_swiss",
                name="Summer Swiss Series 2026",
                format=TournamentFormat.SWISS.value,
                status=TournamentStatus.REGISTRATION_OPEN.value,
                game_id="game_strategy_arena",
                organizer_id="org_esports_league",
                max_participants=32,
                current_participants=4,
                start_time="",
                end_time="",
                registration_deadline="",
                seed_method=SeedMethod.RANDOM.value,
                description="Open swiss-format summer series accepting registrations.",
            )
            self._tournaments[t2.tournament_id] = t2

            summer_players = [
                ("player_aqua", "Aqua"),
                ("player_blaze", "Blaze"),
                ("player_cyclone", "Cyclone"),
                ("player_drift", "Drift"),
            ]
            for idx, (pid, pname) in enumerate(summer_players):
                part = TournamentParticipant(
                    participant_id=pid,
                    name=pname,
                    team_id="",
                    seed=0,
                    status=PlayerStatus.REGISTERED.value,
                    bracket_position=0,
                    metadata={"tournament_id": t2.tournament_id},
                )
                self._participants[pid] = part
                t2.participant_ids.append(pid)

            # ----------------------------------------------------------
            # Tournament 3: World Cup (group stage, completed)
            # ----------------------------------------------------------
            t3 = Tournament(
                tournament_id="tournament_world_cup",
                name="World Cup 2026",
                format=TournamentFormat.GROUP_STAGE.value,
                status=TournamentStatus.COMPLETED.value,
                game_id="game_battlegrounds",
                organizer_id="org_world_esports",
                max_participants=8,
                current_participants=8,
                start_time=now,
                end_time=now,
                registration_deadline=now,
                seed_method=SeedMethod.SEEDED.value,
                description="World championship with group stage format.",
                champion_id="player_sigma",
            )
            self._tournaments[t3.tournament_id] = t3

            world_players = [
                ("player_rho", "Rho", PlayerStatus.ELIMINATED.value),
                ("player_sigma", "Sigma", PlayerStatus.CHAMPION.value),
                ("player_tau", "Tau", PlayerStatus.ELIMINATED.value),
                ("player_upsilon", "Upsilon", PlayerStatus.ELIMINATED.value),
                ("player_phi", "Phi", PlayerStatus.ELIMINATED.value),
                ("player_chi", "Chi", PlayerStatus.ELIMINATED.value),
                ("player_psi", "Psi", PlayerStatus.ELIMINATED.value),
                ("player_omega", "Omega", PlayerStatus.ELIMINATED.value),
            ]
            for idx, (pid, pname, pstatus) in enumerate(world_players):
                part = TournamentParticipant(
                    participant_id=pid,
                    name=pname,
                    team_id=f"team_world_{idx % 2}",
                    seed=idx + 1,
                    status=pstatus,
                    bracket_position=idx + 1,
                    metadata={"tournament_id": t3.tournament_id},
                )
                self._participants[pid] = part
                t3.participant_ids.append(pid)

            # Group A bracket
            bracket_world_a = TournamentBracket(
                bracket_id="bracket_worldcup_group_a",
                tournament_id=t3.tournament_id,
                bracket_type=BracketType.GROUP_A.value,
                rounds=3,
                total_rounds=3,
                matches=[],
                metadata={"group": "A", "created_at": now},
            )
            self._brackets[bracket_world_a.bracket_id] = bracket_world_a
            t3.bracket_ids.append(bracket_world_a.bracket_id)

            # Group B bracket
            bracket_world_b = TournamentBracket(
                bracket_id="bracket_worldcup_group_b",
                tournament_id=t3.tournament_id,
                bracket_type=BracketType.GROUP_B.value,
                rounds=3,
                total_rounds=3,
                matches=[],
                metadata={"group": "B", "created_at": now},
            )
            self._brackets[bracket_world_b.bracket_id] = bracket_world_b
            t3.bracket_ids.append(bracket_world_b.bracket_id)

            # Group A matches
            group_a_matches = [
                ("player_rho", "player_sigma", "player_sigma", 2, 1),
                ("player_tau", "player_upsilon", "player_tau", 2, 0),
                ("player_sigma", "player_tau", "player_sigma", 2, 1),
                ("player_rho", "player_upsilon", "player_upsilon", 1, 2),
            ]
            for m_idx, (p1, p2, winner, s1, s2) in enumerate(group_a_matches, start=1):
                mid = f"match_world_groupA_m{m_idx}"
                match = TournamentMatch(
                    match_id=mid,
                    tournament_id=t3.tournament_id,
                    round=((m_idx - 1) // 2) + 1,
                    bracket_type=BracketType.GROUP_A.value,
                    player1_id=p1,
                    player2_id=p2,
                    status=MatchStatus.COMPLETED.value,
                    winner_id=winner,
                    score_p1=s1,
                    score_p2=s2,
                    scheduled_time=now,
                    completed_time=now,
                    metadata={"bracket_id": bracket_world_a.bracket_id},
                )
                self._matches[mid] = match
                t3.match_ids.append(mid)
                bracket_world_a.matches.append(mid)
                self._participants[winner].wins += 1
                loser = p1 if winner == p2 else p2
                self._participants[loser].losses += 1

            # Group B matches
            group_b_matches = [
                ("player_phi", "player_chi", "player_phi", 2, 0),
                ("player_psi", "player_omega", "player_psi", 2, 1),
                ("player_phi", "player_psi", "player_phi", 2, 1),
                ("player_chi", "player_omega", "player_omega", 0, 2),
            ]
            for m_idx, (p1, p2, winner, s1, s2) in enumerate(group_b_matches, start=1):
                mid = f"match_world_groupB_m{m_idx}"
                match = TournamentMatch(
                    match_id=mid,
                    tournament_id=t3.tournament_id,
                    round=((m_idx - 1) // 2) + 1,
                    bracket_type=BracketType.GROUP_B.value,
                    player1_id=p1,
                    player2_id=p2,
                    status=MatchStatus.COMPLETED.value,
                    winner_id=winner,
                    score_p1=s1,
                    score_p2=s2,
                    scheduled_time=now,
                    completed_time=now,
                    metadata={"bracket_id": bracket_world_b.bracket_id},
                )
                self._matches[mid] = match
                t3.match_ids.append(mid)
                bracket_world_b.matches.append(mid)
                self._participants[winner].wins += 1
                loser = p1 if winner == p2 else p2
                self._participants[loser].losses += 1

            # Prizes for world cup (distributed)
            world_prizes = [
                ("prize_world_1st", 1, PrizeType.CASH.value, 50000.0,
                 "World Cup Champion Cash Prize", "player_sigma"),
                ("prize_world_2nd", 2, PrizeType.CASH.value, 25000.0,
                 "World Cup Runner-up Cash Prize", "player_phi"),
                ("prize_world_3rd", 3, PrizeType.IN_GAME_CURRENCY.value, 100000.0,
                 "World Cup Third Place Currency", "player_tau"),
            ]
            for pid, placement, ptype, val, desc, recipient in world_prizes:
                prize = PrizeEntry(
                    prize_id=pid,
                    tournament_id=t3.tournament_id,
                    placement=placement,
                    prize_type=ptype,
                    value=val,
                    description=desc,
                    recipient_id=recipient,
                    metadata={"currency": "usd" if ptype == PrizeType.CASH.value else "gold"},
                )
                self._prizes[pid] = prize
                t3.prize_pool_ids.append(pid)

            # Seed events
            self._emit("tournament_registered", tournament_id=t1.tournament_id,
                       data={"name": t1.name, "format": t1.format})
            self._emit("tournament_registered", tournament_id=t2.tournament_id,
                       data={"name": t2.name, "format": t2.format})
            self._emit("tournament_registered", tournament_id=t3.tournament_id,
                       data={"name": t3.name, "format": t3.format})
            self._emit("bracket_generated", tournament_id=t1.tournament_id,
                       data={"bracket_id": bracket_spring.bracket_id})
            self._emit("bracket_generated", tournament_id=t3.tournament_id,
                       data={"bracket_id": bracket_world_a.bracket_id})
            self._emit("bracket_generated", tournament_id=t3.tournament_id,
                       data={"bracket_id": bracket_world_b.bracket_id})
            self._emit("match_completed", tournament_id=t3.tournament_id,
                       match_id="match_world_groupA_m3",
                       participant_id="player_sigma",
                       data={"winner": "player_sigma"})
            self._emit("prize_distributed", tournament_id=t3.tournament_id,
                       data={"prizes": [p for p in t3.prize_pool_ids]})

            self._update_stats()
            self._initialized = True

    # ------------------------------------------------------------------
    # Tournament CRUD
    # ------------------------------------------------------------------

    def register_tournament(
        self,
        tournament_id: str,
        name: str,
        format: str,
        game_id: str,
        organizer_id: str,
        max_participants: int = 16,
        start_time: str = "",
        end_time: str = "",
        registration_deadline: str = "",
        seed_method: str = "random",
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Tournament]]:
        """Register a new tournament into the system."""
        with self._lock:
            if not tournament_id or not name or not game_id or not organizer_id:
                return False, "tournament_id, name, game_id, and organizer_id are required", None
            if tournament_id in self._tournaments:
                return False, f"tournament already exists: {tournament_id}", None
            if len(self._tournaments) >= self._config.max_tournaments:
                return False, "tournament capacity reached", None

            fmt = _coerce_enum(TournamentFormat, format, TournamentFormat.SINGLE_ELIMINATION)
            sm = _coerce_enum(SeedMethod, seed_method, SeedMethod.RANDOM)
            cap = max(2, _safe_int(max_participants, 16))

            tournament = Tournament(
                tournament_id=tournament_id,
                name=name,
                format=fmt.value,
                status=TournamentStatus.REGISTRATION_OPEN.value,
                game_id=game_id,
                organizer_id=organizer_id,
                max_participants=cap,
                current_participants=0,
                start_time=start_time,
                end_time=end_time,
                registration_deadline=registration_deadline,
                seed_method=sm.value,
                description=description,
                metadata=metadata or {},
            )
            self._tournaments[tournament_id] = tournament
            _evict_fifo_dict(self._tournaments, self._config.max_tournaments)
            self._emit(
                "tournament_registered",
                tournament_id=tournament_id,
                data={"name": name, "format": fmt.value, "game_id": game_id},
            )
            self._update_stats()
            return True, "registered", tournament

    def get_tournament(self, tournament_id: str) -> Optional[Tournament]:
        """Retrieve a tournament by id."""
        with self._lock:
            return self._tournaments.get(tournament_id)

    def list_tournaments(self, status_filter: str = "") -> List[Tournament]:
        """List tournaments, optionally filtered by status."""
        with self._lock:
            results = list(self._tournaments.values())
            if status_filter:
                results = [t for t in results if t.status == status_filter]
            return results

    def remove_tournament(self, tournament_id: str) -> Tuple[bool, str]:
        """Remove a tournament and its associated matches, brackets, and prizes."""
        with self._lock:
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, "not found"
            # Remove associated matches
            for mid in tournament.match_ids:
                self._matches.pop(mid, None)
            # Remove associated brackets
            for bid in tournament.bracket_ids:
                self._brackets.pop(bid, None)
            # Remove associated prizes
            for pid in tournament.prize_pool_ids:
                self._prizes.pop(pid, None)
            # Remove associated participants
            for pid in tournament.participant_ids:
                self._participants.pop(pid, None)
            self._tournaments.pop(tournament_id, None)
            self._emit(
                "tournament_removed",
                tournament_id=tournament_id,
                data={"name": tournament.name},
            )
            self._update_stats()
            return True, "removed"

    # ------------------------------------------------------------------
    # Participant Management
    # ------------------------------------------------------------------

    def register_participant(
        self,
        participant_id: str,
        tournament_id: str,
        name: str,
        team_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[TournamentParticipant]]:
        """Register a participant into a tournament."""
        with self._lock:
            if not participant_id or not tournament_id or not name:
                return False, "participant_id, tournament_id, and name are required", None
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", None
            if tournament.status not in (
                TournamentStatus.REGISTRATION_OPEN.value,
                TournamentStatus.DRAFT.value,
            ):
                return False, f"tournament is not open for registration: {tournament.status}", None
            if participant_id in self._participants:
                return False, f"participant already exists: {participant_id}", None
            if tournament.current_participants >= tournament.max_participants:
                return False, "tournament is at maximum capacity", None

            participant = TournamentParticipant(
                participant_id=participant_id,
                name=name,
                team_id=team_id,
                seed=0,
                status=PlayerStatus.REGISTERED.value,
                wins=0,
                losses=0,
                bracket_position=0,
                metadata={"tournament_id": tournament_id, **(metadata or {})},
            )
            self._participants[participant_id] = participant
            _evict_fifo_dict(self._participants, _MAX_PARTICIPANTS)
            tournament.participant_ids.append(participant_id)
            tournament.current_participants = len(tournament.participant_ids)
            self._emit(
                "participant_registered",
                tournament_id=tournament_id,
                participant_id=participant_id,
                data={"name": name, "team_id": team_id},
            )
            self._update_stats()
            return True, "registered", participant

    def get_participant(self, participant_id: str) -> Optional[TournamentParticipant]:
        """Retrieve a participant by id."""
        with self._lock:
            return self._participants.get(participant_id)

    def list_participants(self, tournament_id: str) -> List[TournamentParticipant]:
        """List all participants in a tournament."""
        with self._lock:
            results: List[TournamentParticipant] = []
            for pid, part in self._participants.items():
                if part.metadata.get("tournament_id") == tournament_id:
                    results.append(part)
            return results

    def remove_participant(self, participant_id: str) -> Tuple[bool, str]:
        """Remove a participant from their tournament."""
        with self._lock:
            participant = self._participants.get(participant_id)
            if participant is None:
                return False, "not found"
            tournament_id = participant.metadata.get("tournament_id", "")
            tournament = self._tournaments.get(tournament_id)
            if tournament is not None:
                if participant_id in tournament.participant_ids:
                    tournament.participant_ids.remove(participant_id)
                tournament.current_participants = len(tournament.participant_ids)
            self._participants.pop(participant_id, None)
            self._emit(
                "participant_removed",
                tournament_id=tournament_id,
                participant_id=participant_id,
                data={"name": participant.name},
            )
            self._update_stats()
            return True, "removed"

    def check_in_participant(
        self, participant_id: str
    ) -> Tuple[bool, str, Optional[TournamentParticipant]]:
        """Mark a registered participant as checked in."""
        with self._lock:
            participant = self._participants.get(participant_id)
            if participant is None:
                return False, "not found", None
            if participant.status != PlayerStatus.REGISTERED.value:
                return False, f"participant cannot check in from status: {participant.status}", None
            participant.status = PlayerStatus.CHECKED_IN.value
            self._emit(
                "participant_checked_in",
                tournament_id=participant.metadata.get("tournament_id", ""),
                participant_id=participant_id,
                data={"name": participant.name},
            )
            return True, "checked_in", participant

    # ------------------------------------------------------------------
    # Bracket Management
    # ------------------------------------------------------------------

    def generate_bracket(
        self, tournament_id: str
    ) -> Tuple[bool, str, Optional[TournamentBracket]]:
        """Generate a bracket for a tournament based on its format."""
        with self._lock:
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", None

            participants = self.list_participants(tournament_id)
            checked_in = [
                p for p in participants
                if p.status in (PlayerStatus.CHECKED_IN.value, PlayerStatus.REGISTERED.value)
            ]
            if len(checked_in) < 2:
                return False, "not enough participants to generate a bracket", None

            fmt = _coerce_enum(TournamentFormat, tournament.format, TournamentFormat.SINGLE_ELIMINATION)
            rounds_needed = self.calculate_rounds_needed(len(checked_in), fmt)

            if fmt == TournamentFormat.GROUP_STAGE:
                # Split into two groups and create two brackets
                created: List[TournamentBracket] = []
                mid = len(checked_in) // 2
                group_a = checked_in[:mid]
                group_b = checked_in[mid:]
                groups = [
                    (BracketType.GROUP_A, group_a),
                    (BracketType.GROUP_B, group_b),
                ]
                for btype, members in groups:
                    if not members:
                        continue
                    bid = _new_id("bracket")
                    bracket = TournamentBracket(
                        bracket_id=bid,
                        tournament_id=tournament_id,
                        bracket_type=btype.value,
                        rounds=max(1, len(members) - 1),
                        total_rounds=max(1, len(members) - 1),
                        matches=[],
                        metadata={"created_at": _now(), "group_size": len(members)},
                    )
                    self._brackets[bid] = bracket
                    tournament.bracket_ids.append(bid)
                    created.append(bracket)
                    self._emit(
                        "bracket_generated",
                        tournament_id=tournament_id,
                        data={"bracket_id": bid, "bracket_type": btype.value},
                    )
                self._update_stats()
                return True, "generated", created[0] if created else None

            # Single bracket for other formats
            btype = BracketType.WINNERS
            if fmt == TournamentFormat.SWISS:
                btype = BracketType.SWISS_ROUND
            bid = _new_id("bracket")
            bracket = TournamentBracket(
                bracket_id=bid,
                tournament_id=tournament_id,
                bracket_type=btype.value,
                rounds=rounds_needed,
                total_rounds=rounds_needed,
                matches=[],
                metadata={"created_at": _now()},
            )
            self._brackets[bid] = bracket
            tournament.bracket_ids.append(bid)

            # Seed participants into bracket positions
            for idx, part in enumerate(checked_in):
                part.bracket_position = idx + 1
                part.seed = idx + 1

            # Create round 1 matches for single elimination
            if fmt == TournamentFormat.SINGLE_ELIMINATION:
                paired = len(checked_in) // 2
                for i in range(paired):
                    p1 = checked_in[i * 2]
                    p2 = checked_in[i * 2 + 1]
                    mid_val = self._new_match_id()
                    match = TournamentMatch(
                        match_id=mid_val,
                        tournament_id=tournament_id,
                        round=1,
                        bracket_type=btype.value,
                        player1_id=p1.participant_id,
                        player2_id=p2.participant_id,
                        status=MatchStatus.READY.value,
                        scheduled_time=_now(),
                        metadata={"bracket_id": bid},
                    )
                    self._matches[mid_val] = match
                    _evict_fifo_dict(self._matches, self._config.max_matches)
                    tournament.match_ids.append(mid_val)
                    bracket.matches.append(mid_val)

            tournament.status = TournamentStatus.IN_PROGRESS.value
            self._emit(
                "bracket_generated",
                tournament_id=tournament_id,
                data={"bracket_id": bid, "bracket_type": btype.value, "rounds": rounds_needed},
            )
            self._update_stats()
            return True, "generated", bracket

    def get_bracket(self, bracket_id: str) -> Optional[TournamentBracket]:
        """Retrieve a bracket by id."""
        with self._lock:
            return self._brackets.get(bracket_id)

    def list_brackets(self, tournament_id: str) -> List[TournamentBracket]:
        """List all brackets in a tournament."""
        with self._lock:
            results: List[TournamentBracket] = []
            for bracket in self._brackets.values():
                if bracket.tournament_id == tournament_id:
                    results.append(bracket)
            return results

    # ------------------------------------------------------------------
    # Match Management
    # ------------------------------------------------------------------

    def create_match(
        self,
        tournament_id: str,
        round_num: int,
        bracket_type: str,
        player1_id: str,
        player2_id: str,
        scheduled_time: str = "",
    ) -> Tuple[bool, str, Optional[TournamentMatch]]:
        """Create a new match within a tournament."""
        with self._lock:
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", None
            if len(self._matches) >= self._config.max_matches:
                return False, "match capacity reached", None
            bt = _coerce_enum(BracketType, bracket_type, BracketType.WINNERS)
            mid = self._new_match_id()
            status = MatchStatus.PENDING.value
            if player1_id and player2_id:
                status = MatchStatus.READY.value
            match = TournamentMatch(
                match_id=mid,
                tournament_id=tournament_id,
                round=round_num,
                bracket_type=bt.value,
                player1_id=player1_id,
                player2_id=player2_id,
                status=status,
                scheduled_time=scheduled_time or _now(),
                metadata={"bracket_id": ""},
            )
            self._matches[mid] = match
            _evict_fifo_dict(self._matches, self._config.max_matches)
            tournament.match_ids.append(mid)
            self._emit(
                "match_created",
                tournament_id=tournament_id,
                match_id=mid,
                data={"round": round_num, "bracket_type": bt.value},
            )
            self._update_stats()
            return True, "created", match

    def get_match(self, match_id: str) -> Optional[TournamentMatch]:
        """Retrieve a match by id."""
        with self._lock:
            return self._matches.get(match_id)

    def list_matches(
        self,
        tournament_id: str,
        round_filter: int = 0,
        bracket_filter: str = "",
    ) -> List[TournamentMatch]:
        """List matches in a tournament with optional round and bracket filters."""
        with self._lock:
            results: List[TournamentMatch] = []
            for match in self._matches.values():
                if match.tournament_id != tournament_id:
                    continue
                if round_filter and match.round != round_filter:
                    continue
                if bracket_filter and match.bracket_type != bracket_filter:
                    continue
                results.append(match)
            return results

    def start_match(
        self, match_id: str
    ) -> Tuple[bool, str, Optional[TournamentMatch]]:
        """Transition a match into the in-progress state."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "not found", None
            if match.status not in (MatchStatus.READY.value, MatchStatus.PENDING.value):
                return False, f"match cannot start from status: {match.status}", None
            if not match.player1_id or not match.player2_id:
                return False, "match requires two participants before starting", None
            match.status = MatchStatus.IN_PROGRESS.value
            self._emit(
                "match_started",
                tournament_id=match.tournament_id,
                match_id=match_id,
                data={"player1_id": match.player1_id, "player2_id": match.player2_id},
            )
            return True, "started", match

    def complete_match(
        self,
        match_id: str,
        winner_id: str,
        score_p1: int = 0,
        score_p2: int = 0,
    ) -> Tuple[bool, str, Optional[TournamentMatch]]:
        """Complete a match by recording the winner and final scores."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "not found", None
            if match.status in (MatchStatus.COMPLETED.value, MatchStatus.FORFEITED.value):
                return False, f"match already finished with status: {match.status}", None
            if winner_id not in (match.player1_id, match.player2_id):
                return False, "winner must be one of the match participants", None

            match.winner_id = winner_id
            match.score_p1 = _safe_int(score_p1, 0)
            match.score_p2 = _safe_int(score_p2, 0)
            match.status = MatchStatus.COMPLETED.value
            match.completed_time = _now()

            # Update participant records
            winner = self._participants.get(winner_id)
            if winner is not None:
                winner.wins += 1
            loser_id = match.player2_id if winner_id == match.player1_id else match.player1_id
            loser = self._participants.get(loser_id)
            if loser is not None:
                loser.losses += 1

            self._emit(
                "match_completed",
                tournament_id=match.tournament_id,
                match_id=match_id,
                participant_id=winner_id,
                data={"winner": winner_id, "score_p1": match.score_p1, "score_p2": match.score_p2},
            )
            return True, "completed", match

    def forfeit_match(
        self, match_id: str, forfeiter_id: str
    ) -> Tuple[bool, str, Optional[TournamentMatch]]:
        """Forfeit a match; the non-forfeiting participant is declared winner."""
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "not found", None
            if match.status in (MatchStatus.COMPLETED.value, MatchStatus.FORFEITED.value):
                return False, f"match already finished with status: {match.status}", None
            if forfeiter_id not in (match.player1_id, match.player2_id):
                return False, "forfeiter must be one of the match participants", None

            winner_id = match.player2_id if forfeiter_id == match.player1_id else match.player1_id
            match.winner_id = winner_id
            match.status = MatchStatus.FORFEITED.value
            match.completed_time = _now()

            winner = self._participants.get(winner_id)
            if winner is not None:
                winner.wins += 1
            forfeiter = self._participants.get(forfeiter_id)
            if forfeiter is not None:
                forfeiter.losses += 1

            self._emit(
                "match_forfeited",
                tournament_id=match.tournament_id,
                match_id=match_id,
                participant_id=forfeiter_id,
                data={"winner": winner_id, "forfeiter": forfeiter_id},
            )
            return True, "forfeited", match

    def advance_winner(
        self, match_id: str
    ) -> Tuple[bool, str, Optional[TournamentMatch]]:
        """Advance the winner of a completed match into the next round.

        Creates or fills a match in the next round within the same bracket.
        If the match was the final round, the winner is crowned champion.
        """
        with self._lock:
            match = self._matches.get(match_id)
            if match is None:
                return False, "not found", None
            if match.status not in (MatchStatus.COMPLETED.value, MatchStatus.FORFEITED.value):
                return False, f"match must be completed before advancing: {match.status}", None
            if not match.winner_id:
                return False, "match has no winner to advance", None

            # Locate the bracket to determine total rounds
            bracket_id = match.metadata.get("bracket_id", "")
            bracket = self._brackets.get(bracket_id) if bracket_id else None
            total_rounds = bracket.total_rounds if bracket else 0

            # If this was the final round, crown the champion
            if total_rounds and match.round >= total_rounds:
                tournament = self._tournaments.get(match.tournament_id)
                if tournament is not None:
                    tournament.champion_id = match.winner_id
                    champion = self._participants.get(match.winner_id)
                    if champion is not None:
                        champion.status = PlayerStatus.CHAMPION.value
                    tournament.status = TournamentStatus.COMPLETED.value
                    self._emit(
                        "champion_crowned",
                        tournament_id=match.tournament_id,
                        match_id=match_id,
                        participant_id=match.winner_id,
                        data={"champion": match.winner_id},
                    )
                return True, "champion_crowned", match

            next_round = match.round + 1
            bt = match.bracket_type

            # Look for an existing next-round match with one empty slot
            next_match: Optional[TournamentMatch] = None
            for mid, candidate in self._matches.items():
                if (
                    candidate.tournament_id == match.tournament_id
                    and candidate.round == next_round
                    and candidate.bracket_type == bt
                    and candidate.status == MatchStatus.PENDING.value
                    and (not candidate.player1_id or not candidate.player2_id)
                ):
                    next_match = candidate
                    break

            if next_match is not None:
                # Fill the empty slot
                if not next_match.player1_id:
                    next_match.player1_id = match.winner_id
                else:
                    next_match.player2_id = match.winner_id
                if next_match.player1_id and next_match.player2_id:
                    next_match.status = MatchStatus.READY.value
                self._emit(
                    "winner_advanced",
                    tournament_id=match.tournament_id,
                    match_id=next_match.match_id,
                    participant_id=match.winner_id,
                    data={"from_match": match_id, "round": next_round},
                )
                return True, "advanced", next_match

            # No existing slot; create a new pending match with the winner
            new_mid = self._new_match_id()
            new_match = TournamentMatch(
                match_id=new_mid,
                tournament_id=match.tournament_id,
                round=next_round,
                bracket_type=bt,
                player1_id=match.winner_id,
                player2_id="",
                status=MatchStatus.PENDING.value,
                scheduled_time=_now(),
                metadata={"bracket_id": bracket_id},
            )
            self._matches[new_mid] = new_match
            tournament = self._tournaments.get(match.tournament_id)
            if tournament is not None:
                tournament.match_ids.append(new_mid)
            if bracket is not None:
                bracket.matches.append(new_mid)
            self._emit(
                "winner_advanced",
                tournament_id=match.tournament_id,
                match_id=new_mid,
                participant_id=match.winner_id,
                data={"from_match": match_id, "round": next_round},
            )
            return True, "advanced", new_match

    # ------------------------------------------------------------------
    # Prize Management
    # ------------------------------------------------------------------

    def register_prize(
        self,
        prize_id: str,
        tournament_id: str,
        placement: int,
        prize_type: str,
        value: float,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[PrizeEntry]]:
        """Register a prize entry for a tournament placement."""
        with self._lock:
            if not prize_id or not tournament_id:
                return False, "prize_id and tournament_id are required", None
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", None
            if prize_id in self._prizes:
                return False, f"prize already exists: {prize_id}", None
            pt = _coerce_enum(PrizeType, prize_type, PrizeType.CASH)
            prize = PrizeEntry(
                prize_id=prize_id,
                tournament_id=tournament_id,
                placement=_safe_int(placement, 0),
                prize_type=pt.value,
                value=_safe_float(value, 0.0),
                description=description,
                recipient_id="",
                metadata=metadata or {},
            )
            self._prizes[prize_id] = prize
            _evict_fifo_dict(self._prizes, _MAX_PRIZES)
            tournament.prize_pool_ids.append(prize_id)
            self._emit(
                "prize_registered",
                tournament_id=tournament_id,
                data={"prize_id": prize_id, "placement": prize.placement, "value": prize.value},
            )
            self._update_stats()
            return True, "registered", prize

    def get_prize(self, prize_id: str) -> Optional[PrizeEntry]:
        """Retrieve a prize entry by id."""
        with self._lock:
            return self._prizes.get(prize_id)

    def list_prizes(self, tournament_id: str) -> List[PrizeEntry]:
        """List all prize entries for a tournament."""
        with self._lock:
            results: List[PrizeEntry] = []
            for prize in self._prizes.values():
                if prize.tournament_id == tournament_id:
                    results.append(prize)
            return results

    def distribute_prizes(
        self, tournament_id: str
    ) -> Tuple[bool, str, List[PrizeEntry]]:
        """Distribute prizes to participants based on final standings.

        Assigns recipients by matching placement numbers against the
        computed standings ranking.
        """
        with self._lock:
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", []
            prizes = self.list_prizes(tournament_id)
            if not prizes:
                return False, "no prizes to distribute", []
            standings = self._get_standings_locked(tournament_id)
            distributed: List[PrizeEntry] = []
            for prize in prizes:
                idx = prize.placement - 1
                if 0 <= idx < len(standings):
                    recipient_id = standings[idx].get("participant_id", "")
                    prize.recipient_id = recipient_id
                    distributed.append(prize)
                    self._emit(
                        "prize_distributed",
                        tournament_id=tournament_id,
                        participant_id=recipient_id,
                        data={
                            "prize_id": prize.prize_id,
                            "placement": prize.placement,
                            "value": prize.value,
                        },
                    )
            self._update_stats()
            return True, "distributed", distributed

    # ------------------------------------------------------------------
    # Standings & Seeding
    # ------------------------------------------------------------------

    def _get_standings_locked(self, tournament_id: str) -> List[Dict[str, Any]]:
        """Compute standings (must be called while holding the lock)."""
        participants = self.list_participants(tournament_id)
        ranked = sorted(
            participants,
            key=lambda p: (-p.wins, p.losses, p.seed),
        )
        standings: List[Dict[str, Any]] = []
        for rank, part in enumerate(ranked, start=1):
            standings.append(
                {
                    "rank": rank,
                    "participant_id": part.participant_id,
                    "name": part.name,
                    "team_id": part.team_id,
                    "seed": part.seed,
                    "wins": part.wins,
                    "losses": part.losses,
                    "status": part.status,
                }
            )
        return standings

    def get_standings(self, tournament_id: str) -> List[Dict[str, Any]]:
        """Return current standings for a tournament sorted by wins."""
        with self._lock:
            return self._get_standings_locked(tournament_id)

    def calculate_rounds_needed(
        self, participant_count: int, format: Any
    ) -> int:
        """Calculate the number of rounds needed for a given format and count."""
        count = max(0, _safe_int(participant_count, 0))
        if count <= 1:
            return 0
        fmt = _coerce_enum(TournamentFormat, format, TournamentFormat.SINGLE_ELIMINATION)
        if fmt == TournamentFormat.SINGLE_ELIMINATION:
            return max(1, int(math.ceil(math.log2(count))))
        if fmt == TournamentFormat.DOUBLE_ELIMINATION:
            return max(2, int(math.ceil(math.log2(count))) * 2)
        if fmt == TournamentFormat.ROUND_ROBIN:
            # Each participant plays every other; rounds = n-1 (even) or n (odd)
            return count - 1 if count % 2 == 0 else count
        if fmt == TournamentFormat.SWISS:
            return max(1, int(math.ceil(math.log2(count))))
        if fmt == TournamentFormat.GROUP_STAGE:
            # Approximate rounds per group of 4
            groups = max(1, count // 4)
            per_group = max(1, (count // groups) - 1) if groups else 1
            return per_group
        if fmt == TournamentFormat.BATTLE_ROYALE:
            return 1
        return 1

    def seed_participants(
        self, tournament_id: str, method: str = "seeded"
    ) -> Tuple[bool, str, List[TournamentParticipant]]:
        """Seed participants within a tournament using the given method."""
        with self._lock:
            tournament = self._tournaments.get(tournament_id)
            if tournament is None:
                return False, f"tournament not found: {tournament_id}", []
            participants = self.list_participants(tournament_id)
            if not participants:
                return False, "no participants to seed", []
            sm = _coerce_enum(SeedMethod, method, SeedMethod.SEEDED)

            if sm == SeedMethod.RANDOM:
                random.shuffle(participants)
                for idx, part in enumerate(participants):
                    part.seed = idx + 1
                    part.bracket_position = idx + 1
            elif sm == SeedMethod.SEEDED:
                participants.sort(key=lambda p: p.name.lower())
                for idx, part in enumerate(participants):
                    part.seed = idx + 1
                    part.bracket_position = idx + 1
            elif sm == SeedMethod.SNAKE:
                participants.sort(key=lambda p: p.name.lower())
                n = len(participants)
                positions = [0] * n
                half = (n + 1) // 2
                for i in range(half):
                    positions[i * 2] = i
                for i in range(n - half):
                    positions[(i * 2) + 1] = half + i
                for pos, part in zip(positions, participants):
                    part.seed = pos + 1
                    part.bracket_position = pos + 1
            elif sm == SeedMethod.RESERVOIR:
                # Reservoir-style: keep a reservoir of top seeds, fill the rest randomly
                reservoir_size = min(4, len(participants))
                participants.sort(key=lambda p: p.name.lower())
                reservoir = participants[:reservoir_size]
                rest = participants[reservoir_size:]
                random.shuffle(rest)
                ordered = reservoir + rest
                for idx, part in enumerate(ordered):
                    part.seed = idx + 1
                    part.bracket_position = idx + 1

            self._emit(
                "participants_seeded",
                tournament_id=tournament_id,
                data={"method": sm.value, "count": len(participants)},
            )
            return True, "seeded", participants

    # ------------------------------------------------------------------
    # Events
    # ------------------------------------------------------------------

    def list_events(
        self,
        tournament_id: str = "",
        match_id: str = "",
        limit: int = 100,
    ) -> List[TournamentEvent]:
        """List audit events with optional tournament and match filters."""
        with self._lock:
            results = list(self._events)
            if tournament_id:
                results = [e for e in results if e.tournament_id == tournament_id]
            if match_id:
                results = [e for e in results if e.match_id == match_id]
            cap = _safe_int(limit, 100)
            if cap > 0:
                results = results[-cap:]
            return results

    # ------------------------------------------------------------------
    # System Operations
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._lock:
            self._update_stats()
            return {
                "initialized": self._initialized,
                "total_tournaments": len(self._tournaments),
                "total_participants": len(self._participants),
                "total_matches": len(self._matches),
                "total_brackets": len(self._brackets),
                "total_prizes": len(self._prizes),
                "total_events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> TournamentStats:
        """Return aggregate statistics for the system."""
        with self._lock:
            self._update_stats()
            return self._stats

    def get_snapshot(self) -> TournamentSnapshot:
        """Return a point-in-time snapshot of the full system state."""
        with self._lock:
            self._update_stats()
            return TournamentSnapshot(
                timestamp=_now(),
                tournaments=[t.to_dict() for t in self._tournaments.values()],
                participants=[p.to_dict() for p in self._participants.values()],
                matches=[m.to_dict() for m in self._matches.values()],
                brackets=[b.to_dict() for b in self._brackets.values()],
                prizes=[pr.to_dict() for pr in self._prizes.values()],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> TournamentConfig:
        """Return the current system configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs) -> Tuple[bool, str, TournamentConfig]:
        """Update system configuration fields from keyword arguments."""
        with self._lock:
            if "max_tournaments" in kwargs:
                self._config.max_tournaments = _safe_int(
                    kwargs["max_tournaments"], self._config.max_tournaments
                )
            if "max_participants_per_tournament" in kwargs:
                self._config.max_participants_per_tournament = _safe_int(
                    kwargs["max_participants_per_tournament"],
                    self._config.max_participants_per_tournament,
                )
            if "max_matches" in kwargs:
                self._config.max_matches = _safe_int(
                    kwargs["max_matches"], self._config.max_matches
                )
            if "auto_advance" in kwargs:
                self._config.auto_advance = bool(kwargs["auto_advance"])
            if "default_match_duration" in kwargs:
                self._config.default_match_duration = _safe_int(
                    kwargs["default_match_duration"], self._config.default_match_duration
                )
            if "enable_seeding" in kwargs:
                self._config.enable_seeding = bool(kwargs["enable_seeding"])
            if "enable_prize_distribution" in kwargs:
                self._config.enable_prize_distribution = bool(
                    kwargs["enable_prize_distribution"]
                )
            if "metadata" in kwargs and isinstance(kwargs["metadata"], dict):
                self._config.metadata = kwargs["metadata"]
            self._emit("config_updated", data=dict(kwargs))
            return True, "updated", self._config

    def tick(self) -> Dict[str, Any]:
        """Advance the system by one tick.

        When auto-advance is enabled, completed matches whose winners have
        not yet been advanced are processed automatically.
        """
        with self._lock:
            self._tick_count += 1
            advanced = 0
            if self._config.auto_advance:
                for match in list(self._matches.values()):
                    if match.status in (
                        MatchStatus.COMPLETED.value,
                        MatchStatus.FORFEITED.value,
                    ):
                        ok, _, _ = self.advance_winner(match.match_id)
                        if ok:
                            advanced += 1
            self._emit("tick", data={"tick_count": self._tick_count, "advanced": advanced})
            self._update_stats()
            return {
                "tick_count": self._tick_count,
                "advanced": advanced,
                "total_matches": len(self._matches),
                "total_tournaments": len(self._tournaments),
            }

    def reset(self) -> None:
        """Clear all state and re-seed the system from scratch."""
        with self._lock:
            self._tournaments.clear()
            self._participants.clear()
            self._matches.clear()
            self._brackets.clear()
            self._prizes.clear()
            self._events.clear()
            self._config = TournamentConfig()
            self._stats = TournamentStats()
            self._tick_count = 0
            self._event_counter = 0
            self._match_counter = 0
            self._initialized = False
            self._seed()
            self._emit("system_reset", data={})


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_tournament_esports_system() -> TournamentEsportsSystem:
    """Return the shared TournamentEsportsSystem singleton instance."""
    return TournamentEsportsSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "TournamentFormat",
    "TournamentStatus",
    "MatchStatus",
    "BracketType",
    "SeedMethod",
    "PrizeType",
    "PlayerStatus",
    # Data Classes
    "TournamentParticipant",
    "TournamentMatch",
    "PrizeEntry",
    "TournamentBracket",
    "Tournament",
    "TournamentConfig",
    "TournamentStats",
    "TournamentSnapshot",
    "TournamentEvent",
    # System
    "TournamentEsportsSystem",
    "get_tournament_esports_system",
]
