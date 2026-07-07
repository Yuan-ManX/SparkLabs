"""
SparkLabs Agent - AI Matchmaking Director

An AI-driven matchmaking system for the SparkLabs AI-native game engine.
This agent manages player profiles with skill ratings, processes match
tickets, and assembles balanced match sessions using a multi-factor scoring
algorithm. It fuses Hermes Agent's decision-making patterns with genagents'
simulation strategies to produce fair, latency-aware, and engaging matches.

Architecture:
  MatchmakingDirector (singleton)
    |-- PlayerProfile, MatchTicket, MatchSession, TeamAssignment,
       MatchQuality, MatchmakingConfig, MatchmakingStats,
       MatchmakingSnapshot, MatchmakingEvent
    |-- TicketStatus, MatchKind, Region, MatchmakingEventKind

Core Capabilities:
  - register_player / get_player / list_players / remove_player: player
    profile lifecycle with skill rating, region, and playstyle tags.
  - create_ticket / get_ticket / list_tickets / cancel_ticket: match
    request lifecycle with party size, region preference, and priority.
  - find_match: AI-driven matching algorithm scoring candidates by
    skill_proximity*0.4 + region_affinity*0.3 + wait_urgency*0.2 +
    playstyle_match*0.1.
  - create_session / get_session / list_sessions / end_session: assembled
    match lifecycle with team assignments and quality assessment.
  - evaluate_match: post-match quality scoring (balance, duration, outcome).
  - tick: process pending tickets, attempt matches, expire stale tickets.
  - set_config / get_config: tuning parameters for the matching algorithm.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`MatchmakingDirector.get_instance` or the module-level
:func:`get_matchmaking_director` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PLAYERS: int = 50000
_MAX_TICKETS: int = 5000
_MAX_SESSIONS: int = 2000
_MAX_EVENTS: int = 5000
_MAX_PARTY_SIZE: int = 8


# ---------------------------------------------------------------------------
# Scoring Weights
# ---------------------------------------------------------------------------

_SKILL_WEIGHT: float = 0.4
_REGION_WEIGHT: float = 0.3
_WAIT_WEIGHT: float = 0.2
_PLAYSTYLE_WEIGHT: float = 0.1

_SKILL_TOLERANCE: float = 200.0
_WAIT_URGENCY_THRESHOLD: float = 30.0


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


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        return dict(instance) if isinstance(instance, dict) else {}
    out: Dict[str, Any] = {}
    for name in getattr(instance, "__dataclass_fields__", {}).keys():
        try:
            raw = getattr(instance, name)
        except Exception:
            continue
        out[name] = _to_jsonable(raw)
    return out


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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TicketStatus(Enum):
    """Lifecycle states for a match ticket."""
    PENDING = "pending"
    MATCHED = "matched"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class MatchKind(Enum):
    """Types of matches the director can assemble."""
    CASUAL = "casual"
    RANKED = "ranked"
    TOURNAMENT = "tournament"
    COOP = "coop"
    CUSTOM = "custom"


class Region(Enum):
    """Geographic regions for latency-aware matching."""
    NA_EAST = "na_east"
    NA_WEST = "na_west"
    EU_WEST = "eu_west"
    EU_EAST = "eu_east"
    ASIA_EAST = "asia_east"
    ASIA_SOUTH = "asia_south"
    OCEANIA = "oceania"
    SOUTH_AMERICA = "south_america"


class MatchmakingEventKind(Enum):
    """Audit event types emitted by the matchmaking director."""
    PLAYER_REGISTERED = "player_registered"
    PLAYER_REMOVED = "player_removed"
    TICKET_CREATED = "ticket_created"
    TICKET_CANCELLED = "ticket_cancelled"
    TICKET_EXPIRED = "ticket_expired"
    MATCH_FOUND = "match_found"
    SESSION_CREATED = "session_created"
    SESSION_ENDED = "session_ended"
    MATCH_EVALUATED = "match_evaluated"
    CONFIG_UPDATED = "config_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class PlayerProfile:
    """A player's matchmaking profile."""
    player_id: str = ""
    name: str = ""
    skill_rating: float = 1000.0
    region: str = Region.NA_EAST.value
    playstyle_tags: List[str] = field(default_factory=list)
    wins: int = 0
    losses: int = 0
    matches_played: int = 0
    preferred_kind: str = MatchKind.CASUAL.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def win_rate(self) -> float:
        if self.matches_played == 0:
            return 0.5
        return self.wins / max(1, self.matches_played)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["win_rate"] = round(self.win_rate, 4)
        return d


@dataclass
class MatchTicket:
    """A player's request to join a match."""
    ticket_id: str = ""
    player_id: str = ""
    kind: str = MatchKind.CASUAL.value
    region: str = Region.NA_EAST.value
    party_size: int = 1
    party_player_ids: List[str] = field(default_factory=list)
    priority: int = 0
    status: str = TicketStatus.PENDING.value
    created_at: str = ""
    wait_seconds: float = 0.0
    max_wait: float = 120.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TeamAssignment:
    """A player's assignment within a match session."""
    player_id: str = ""
    team: int = 0
    role: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchSession:
    """An assembled match with teams and quality metrics."""
    session_id: str = ""
    kind: str = MatchKind.CASUAL.value
    region: str = Region.NA_EAST.value
    team_size: int = 5
    assignments: List[TeamAssignment] = field(default_factory=list)
    ticket_ids: List[str] = field(default_factory=list)
    avg_skill: float = 0.0
    skill_spread: float = 0.0
    quality_score: float = 0.0
    created_at: str = ""
    ended: bool = False
    winner_team: int = -1
    duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchQuality:
    """Quality assessment of a completed match."""
    session_id: str = ""
    balance_score: float = 0.0
    duration_score: float = 0.0
    outcome_score: float = 0.0
    overall: float = 0.0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchmakingConfig:
    """Tuning parameters for the matching algorithm."""
    team_size: int = 5
    skill_tolerance: float = _SKILL_TOLERANCE
    max_wait_seconds: float = 120.0
    cross_region: bool = False
    skill_weight: float = _SKILL_WEIGHT
    region_weight: float = _REGION_WEIGHT
    wait_weight: float = _WAIT_WEIGHT
    playstyle_weight: float = _PLAYSTYLE_WEIGHT

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchmakingStats:
    """Aggregate statistics for the matchmaking director."""
    total_players: int = 0
    total_tickets: int = 0
    total_sessions: int = 0
    total_matches_found: int = 0
    total_cancellations: int = 0
    total_expirations: int = 0
    avg_wait_time: float = 0.0
    avg_quality: float = 0.0
    pending_tickets: int = 0
    active_sessions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchmakingSnapshot:
    """Full state snapshot of the matchmaking director."""
    players: List[PlayerProfile] = field(default_factory=list)
    tickets: List[MatchTicket] = field(default_factory=list)
    sessions: List[MatchSession] = field(default_factory=list)
    config: MatchmakingConfig = field(default_factory=MatchmakingConfig)
    stats: MatchmakingStats = field(default_factory=MatchmakingStats)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MatchmakingEvent:
    """An audit event emitted by the matchmaking director."""
    timestamp: str = ""
    kind: str = ""
    entity_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class MatchmakingDirector:
    """AI-driven matchmaking system for multiplayer game sessions.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["MatchmakingDirector"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._players: Dict[str, PlayerProfile] = {}
        self._tickets: Dict[str, MatchTicket] = {}
        self._sessions: Dict[str, MatchSession] = {}
        self._config: MatchmakingConfig = MatchmakingConfig()
        self._events: List[MatchmakingEvent] = []
        self._stats = MatchmakingStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "MatchmakingDirector":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed with sample players and pending tickets."""
        player_seeds = [
            PlayerProfile(
                player_id="plr_ace_vanguard",
                name="Ace Vanguard",
                skill_rating=1850.0,
                region=Region.NA_EAST.value,
                playstyle_tags=["aggressive", "flanker"],
                wins=140, losses=90, matches_played=230,
                preferred_kind=MatchKind.RANKED.value,
            ),
            PlayerProfile(
                player_id="plr_blaze_falcon",
                name="Blaze Falcon",
                skill_rating=1820.0,
                region=Region.NA_EAST.value,
                playstyle_tags=["aggressive", "sniper"],
                wins=120, losses=85, matches_played=205,
                preferred_kind=MatchKind.RANKED.value,
            ),
            PlayerProfile(
                player_id="plr_cyrus_tank",
                name="Cyrus Tank",
                skill_rating=1700.0,
                region=Region.NA_WEST.value,
                playstyle_tags=["defensive", "support"],
                wins=95, losses=80, matches_played=175,
                preferred_kind=MatchKind.CASUAL.value,
            ),
            PlayerProfile(
                player_id="plr_dawn_reaper",
                name="Dawn Reaper",
                skill_rating=1900.0,
                region=Region.EU_WEST.value,
                playstyle_tags=["aggressive", "flanker"],
                wins=160, losses=70, matches_played=230,
                preferred_kind=MatchKind.TOURNAMENT.value,
            ),
            PlayerProfile(
                player_id="plr_echo_sage",
                name="Echo Sage",
                skill_rating=1750.0,
                region=Region.NA_EAST.value,
                playstyle_tags=["tactical", "support"],
                wins=110, losses=95, matches_played=205,
                preferred_kind=MatchKind.RANKED.value,
            ),
            PlayerProfile(
                player_id="plr_frost_warden",
                name="Frost Warden",
                skill_rating=1680.0,
                region=Region.NA_EAST.value,
                playstyle_tags=["defensive", "tank"],
                wins=85, losses=75, matches_played=160,
                preferred_kind=MatchKind.CASUAL.value,
            ),
        ]
        for p in player_seeds:
            self._players[p.player_id] = p

        ticket_seeds = [
            MatchTicket(
                ticket_id="tkt_ace_ranked",
                player_id="plr_ace_vanguard",
                kind=MatchKind.RANKED.value,
                region=Region.NA_EAST.value,
                party_size=1,
                priority=5,
                created_at=_now(),
                max_wait=120.0,
            ),
            MatchTicket(
                ticket_id="tkt_blaze_ranked",
                player_id="plr_blaze_falcon",
                kind=MatchKind.RANKED.value,
                region=Region.NA_EAST.value,
                party_size=1,
                priority=5,
                created_at=_now(),
                max_wait=120.0,
            ),
            MatchTicket(
                ticket_id="tkt_echo_ranked",
                player_id="plr_echo_sage",
                kind=MatchKind.RANKED.value,
                region=Region.NA_EAST.value,
                party_size=1,
                priority=3,
                created_at=_now(),
                max_wait=90.0,
            ),
        ]
        for t in ticket_seeds:
            self._tickets[t.ticket_id] = t

        self._stats.total_players = len(self._players)
        self._stats.total_tickets = len(self._tickets)
        self._stats.pending_tickets = sum(
            1 for t in self._tickets.values()
            if t.status == TicketStatus.PENDING.value
        )
        self._initialized = True

    # ------------------------------------------------------------------
    # Player Lifecycle
    # ------------------------------------------------------------------

    def register_player(self, player: PlayerProfile) -> PlayerProfile:
        with self._init_lock:
            if not player.player_id:
                player.player_id = _new_id("plr")
            self._players[player.player_id] = player
            _evict_fifo_dict(self._players, _MAX_PLAYERS)
            self._stats.total_players = len(self._players)
            self._emit(
                MatchmakingEventKind.PLAYER_REGISTERED.value,
                player.player_id,
                {"skill_rating": player.skill_rating, "region": player.region},
            )
            return player

    def get_player(self, player_id: str) -> Optional[PlayerProfile]:
        return self._players.get(player_id)

    def list_players(
        self,
        region: str = "",
        kind: str = "",
        limit: int = 100,
    ) -> List[PlayerProfile]:
        result: List[PlayerProfile] = []
        for p in self._players.values():
            if region and p.region != region:
                continue
            if kind and p.preferred_kind != kind:
                continue
            result.append(p)
            if len(result) >= limit:
                break
        return result

    def remove_player(self, player_id: str) -> bool:
        with self._init_lock:
            existed = self._players.pop(player_id, None) is not None
            if existed:
                self._stats.total_players = len(self._players)
                self._emit(
                    MatchmakingEventKind.PLAYER_REMOVED.value,
                    player_id,
                    {},
                )
            return existed

    # ------------------------------------------------------------------
    # Ticket Lifecycle
    # ------------------------------------------------------------------

    def create_ticket(self, ticket: MatchTicket) -> MatchTicket:
        with self._init_lock:
            if not ticket.ticket_id:
                ticket.ticket_id = _new_id("tkt")
            if not ticket.created_at:
                ticket.created_at = _now()
            ticket.status = TicketStatus.PENDING.value
            self._tickets[ticket.ticket_id] = ticket
            _evict_fifo_dict(self._tickets, _MAX_TICKETS)
            self._stats.total_tickets = len(self._tickets)
            self._stats.pending_tickets = sum(
                1 for t in self._tickets.values()
                if t.status == TicketStatus.PENDING.value
            )
            self._emit(
                MatchmakingEventKind.TICKET_CREATED.value,
                ticket.ticket_id,
                {"player_id": ticket.player_id, "kind": ticket.kind},
            )
            return ticket

    def get_ticket(self, ticket_id: str) -> Optional[MatchTicket]:
        return self._tickets.get(ticket_id)

    def list_tickets(
        self,
        status: str = "",
        kind: str = "",
        limit: int = 100,
    ) -> List[MatchTicket]:
        result: List[MatchTicket] = []
        for t in self._tickets.values():
            if status and t.status != status:
                continue
            if kind and t.kind != kind:
                continue
            result.append(t)
            if len(result) >= limit:
                break
        return result

    def cancel_ticket(self, ticket_id: str) -> Dict[str, Any]:
        with self._init_lock:
            ticket = self._tickets.get(ticket_id)
            if ticket is None:
                return {"ok": False, "reason": "ticket not found"}
            if ticket.status != TicketStatus.PENDING.value:
                return {"ok": False, "reason": f"ticket is {ticket.status}"}
            ticket.status = TicketStatus.CANCELLED.value
            self._stats.total_cancellations += 1
            self._stats.pending_tickets = sum(
                1 for t in self._tickets.values()
                if t.status == TicketStatus.PENDING.value
            )
            self._emit(
                MatchmakingEventKind.TICKET_CANCELLED.value,
                ticket_id,
                {},
            )
            return {"ok": True, "ticket_id": ticket_id}

    # ------------------------------------------------------------------
    # AI-Driven Matching
    # ------------------------------------------------------------------

    def _score_candidate(
        self,
        ticket: MatchTicket,
        candidate: MatchTicket,
        player: PlayerProfile,
        candidate_player: PlayerProfile,
    ) -> float:
        """Score a candidate ticket for matching (0.0 to 1.0)."""
        # Skill proximity
        skill_diff = abs(player.skill_rating - candidate_player.skill_rating)
        skill_score = max(0.0, 1.0 - skill_diff / self._config.skill_tolerance)

        # Region affinity
        region_score = 1.0 if player.region == candidate_player.region else (
            0.3 if self._config.cross_region else 0.0
        )

        # Wait urgency (candidates waiting longer get higher scores)
        wait_score = min(1.0, candidate.wait_seconds / _WAIT_URGENCY_THRESHOLD)

        # Playstyle compatibility
        common_tags = set(player.playstyle_tags) & set(candidate_player.playstyle_tags)
        playstyle_score = min(1.0, len(common_tags) / 3.0)

        overall = (
            skill_score * self._config.skill_weight
            + region_score * self._config.region_weight
            + wait_score * self._config.wait_weight
            + playstyle_score * self._config.playstyle_weight
        )
        return round(overall, 4)

    def find_match(self, ticket_id: str) -> Dict[str, Any]:
        """Find the best match candidates for a ticket."""
        ticket = self._tickets.get(ticket_id)
        if ticket is None:
            return {"ok": False, "reason": "ticket not found"}
        if ticket.status != TicketStatus.PENDING.value:
            return {"ok": False, "reason": f"ticket is {ticket.status}"}

        player = self._players.get(ticket.player_id)
        if player is None:
            return {"ok": False, "reason": "player not found"}

        needed = max(1, self._config.team_size * 2 - ticket.party_size)
        candidates: List[Dict[str, Any]] = []

        for other in self._tickets.values():
            if other.ticket_id == ticket_id:
                continue
            if other.status != TicketStatus.PENDING.value:
                continue
            if other.kind != ticket.kind:
                continue
            if not self._config.cross_region and other.region != ticket.region:
                continue

            other_player = self._players.get(other.player_id)
            if other_player is None:
                continue

            score = self._score_candidate(ticket, other, player, other_player)
            candidates.append({
                "ticket_id": other.ticket_id,
                "player_id": other.player_id,
                "player_name": other_player.name,
                "skill_rating": other_player.skill_rating,
                "region": other_player.region,
                "score": score,
            })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        top = candidates[:needed]

        self._emit(
            MatchmakingEventKind.MATCH_FOUND.value,
            ticket_id,
            {"candidate_count": len(top), "needed": needed},
        )
        self._stats.total_matches_found += 1

        return {
            "ok": True,
            "ticket_id": ticket_id,
            "needed": needed,
            "candidates": top,
            "candidate_count": len(top),
        }

    def create_session(
        self,
        ticket_ids: List[str],
        kind: str = MatchKind.CASUAL.value,
        region: str = Region.NA_EAST.value,
        team_size: int = 5,
    ) -> Dict[str, Any]:
        """Assemble a match session from a list of ticket IDs."""
        with self._init_lock:
            assignments: List[TeamAssignment] = []
            valid_tickets: List[str] = []
            ratings: List[float] = []

            for i, tid in enumerate(ticket_ids):
                ticket = self._tickets.get(tid)
                if ticket is None or ticket.status != TicketStatus.PENDING.value:
                    continue
                player = self._players.get(ticket.player_id)
                if player is None:
                    continue
                team = i // team_size
                assignments.append(TeamAssignment(
                    player_id=player.player_id,
                    team=team,
                    role="player",
                ))
                valid_tickets.append(tid)
                ratings.append(player.skill_rating)
                ticket.status = TicketStatus.MATCHED.value

            if not assignments:
                return {"ok": False, "reason": "no valid tickets"}

            avg_skill = sum(ratings) / len(ratings) if ratings else 0.0
            skill_spread = max(ratings) - min(ratings) if ratings else 0.0
            quality = max(0.0, 1.0 - skill_spread / self._config.skill_tolerance)

            session = MatchSession(
                session_id=_new_id("ses"),
                kind=kind,
                region=region,
                team_size=team_size,
                assignments=assignments,
                ticket_ids=valid_tickets,
                avg_skill=round(avg_skill, 2),
                skill_spread=round(skill_spread, 2),
                quality_score=round(quality, 4),
                created_at=_now(),
            )
            self._sessions[session.session_id] = session
            _evict_fifo_dict(self._sessions, _MAX_SESSIONS)
            self._stats.total_sessions = len(self._sessions)
            self._stats.active_sessions = sum(
                1 for s in self._sessions.values() if not s.ended
            )
            self._stats.pending_tickets = sum(
                1 for t in self._tickets.values()
                if t.status == TicketStatus.PENDING.value
            )
            self._emit(
                MatchmakingEventKind.SESSION_CREATED.value,
                session.session_id,
                {"player_count": len(assignments), "quality": round(quality, 4)},
            )
            return {"ok": True, "session": session.to_dict()}

    def get_session(self, session_id: str) -> Optional[MatchSession]:
        return self._sessions.get(session_id)

    def list_sessions(
        self,
        kind: str = "",
        active_only: bool = False,
        limit: int = 100,
    ) -> List[MatchSession]:
        result: List[MatchSession] = []
        for s in self._sessions.values():
            if kind and s.kind != kind:
                continue
            if active_only and s.ended:
                continue
            result.append(s)
            if len(result) >= limit:
                break
        return result

    def end_session(
        self,
        session_id: str,
        winner_team: int = -1,
        duration_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        with self._init_lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"ok": False, "reason": "session not found"}
            if session.ended:
                return {"ok": False, "reason": "session already ended"}
            session.ended = True
            session.winner_team = winner_team
            session.duration_seconds = duration_seconds
            self._stats.active_sessions = sum(
                1 for s in self._sessions.values() if not s.ended
            )
            self._emit(
                MatchmakingEventKind.SESSION_ENDED.value,
                session_id,
                {"winner_team": winner_team, "duration": duration_seconds},
            )
            return {"ok": True, "session": session.to_dict()}

    def evaluate_match(self, session_id: str) -> Dict[str, Any]:
        """Assess match quality after completion."""
        session = self._sessions.get(session_id)
        if session is None:
            return {"ok": False, "reason": "session not found"}

        balance_score = session.quality_score
        ideal_duration = 600.0
        duration_score = max(0.0, 1.0 - abs(session.duration_seconds - ideal_duration) / ideal_duration)
        outcome_score = 1.0 if session.winner_team >= 0 else 0.5
        overall = (
            balance_score * 0.5
            + duration_score * 0.3
            + outcome_score * 0.2
        )

        quality = MatchQuality(
            session_id=session_id,
            balance_score=round(balance_score, 4),
            duration_score=round(duration_score, 4),
            outcome_score=round(outcome_score, 4),
            overall=round(overall, 4),
        )
        self._emit(
            MatchmakingEventKind.MATCH_EVALUATED.value,
            session_id,
            {"overall": round(overall, 4)},
        )
        return {"ok": True, "quality": quality.to_dict()}

    # ------------------------------------------------------------------
    # Tick: Process Pending Tickets
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance wait times and expire stale tickets."""
        with self._init_lock:
            expired = 0
            matched = 0
            pending = 0
            for ticket in self._tickets.values():
                if ticket.status != TicketStatus.PENDING.value:
                    continue
                ticket.wait_seconds += dt
                if ticket.wait_seconds >= ticket.max_wait:
                    ticket.status = TicketStatus.EXPIRED.value
                    expired += 1
                else:
                    pending += 1
            self._stats.total_expirations += expired
            self._stats.pending_tickets = pending
            return {
                "ok": True,
                "expired": expired,
                "pending": pending,
                "dt": dt,
            }

    # ------------------------------------------------------------------
    # Config
    # ------------------------------------------------------------------

    def set_config(self, config: MatchmakingConfig) -> MatchmakingConfig:
        with self._init_lock:
            self._config = config
            self._emit(
                MatchmakingEventKind.CONFIG_UPDATED.value,
                "",
                {"team_size": config.team_size, "skill_tolerance": config.skill_tolerance},
            )
            return self._config

    def get_config(self) -> MatchmakingConfig:
        return self._config

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _emit(self, kind: str, entity_id: str, details: Dict[str, Any]) -> None:
        self._events.append(
            MatchmakingEvent(
                timestamp=_now(),
                kind=kind,
                entity_id=entity_id,
                details=details,
            )
        )
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, kind: str = "", limit: int = 50) -> List[MatchmakingEvent]:
        result: List[MatchmakingEvent] = []
        for e in reversed(self._events):
            if kind and e.kind != kind:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> MatchmakingStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_players": len(self._players),
            "pending_tickets": self._stats.pending_tickets,
            "active_sessions": self._stats.active_sessions,
            "team_size": self._config.team_size,
        }

    def get_snapshot(self) -> MatchmakingSnapshot:
        return MatchmakingSnapshot(
            players=list(self._players.values()),
            tickets=list(self._tickets.values()),
            sessions=list(self._sessions.values()),
            config=self._config,
            stats=self._stats,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._players.clear()
            self._tickets.clear()
            self._sessions.clear()
            self._config = MatchmakingConfig()
            self._events.clear()
            self._stats = MatchmakingStats()
            self._seed()
            return {"ok": True, "message": "matchmaking director reset"}


def get_matchmaking_director() -> MatchmakingDirector:
    """Factory function to get the singleton MatchmakingDirector instance."""
    return MatchmakingDirector.get_instance()
