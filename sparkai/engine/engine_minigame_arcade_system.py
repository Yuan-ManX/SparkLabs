"""
SparkLabs Engine - Minigame Arcade System

A minigame and arcade system for the SparkLabs AI-native game engine. Manages
playable minigames, score tracking, token rewards, daily challenges, and
leaderboards. Supports various minigame types (puzzle, racing, shooting,
rhythm, card, platformer) with difficulty levels, entry fees, and payout
structures.

Each minigame session is a self-contained playable instance with a defined
start, play, and end phase. The system tracks player high scores, total
plays, token earnings, and daily challenge completion. Tokens can be exchanged
for rewards through a prize shop.

Architecture:
  MinigameArcadeSystem (singleton)
    |-- MinigameType, MinigameState, DifficultyLevel, ArcadeEventKind
    |-- MinigameDefinition, MinigameSession, ScoreEntry, DailyChallenge,
       PrizeItem, TokenLedger, ArcadeConfig, ArcadeStats,
       ArcadeSnapshot, ArcadeEvent
    |-- get_minigame_arcade_system

Core Capabilities:
  - register_minigame / remove_minigame / get_minigame / list_minigames:
    manage the catalog of available minigames.
  - start_session / end_session / get_session / list_sessions: control
    individual play sessions with score tracking.
  - submit_score / get_high_scores / get_player_best: record scores and
    query leaderboard data.
  - register_daily_challenge / get_daily_challenge / complete_daily_challenge:
    manage rotating daily objectives with bonus rewards.
  - register_prize / remove_prize / list_prizes / redeem_prize: manage the
    token exchange shop.
  - award_tokens / spend_tokens / get_token_balance: track player token
    economy.
  - tick: advance session timers and daily challenge rotations.
  - set_config / get_config: global tuning for max sessions, games, etc.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`MinigameArcadeSystem.get_instance` or the module-level
:func:`get_minigame_arcade_system` factory.
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

_MAX_MINIGAMES: int = 200
_MAX_SESSIONS: int = 5000
_MAX_SCORES_PER_GAME: int = 1000
_MAX_DAILY_CHALLENGES: int = 50
_MAX_PRIZES: int = 200
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

class MinigameType(str, Enum):
    """Type of minigame."""
    PUZZLE = "puzzle"
    RACING = "racing"
    SHOOTING = "shooting"
    RHYTHM = "rhythm"
    CARD = "card"
    PLATFORMER = "platformer"
    ARCADE = "arcade"
    STRATEGY = "strategy"


class MinigameState(str, Enum):
    """Lifecycle state of a minigame session."""
    WAITING = "waiting"
    PLAYING = "playing"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    FAILED = "failed"


class DifficultyLevel(str, Enum):
    """Difficulty level for a minigame."""
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    EXPERT = "expert"
    NIGHTMARE = "nightmare"


class ArcadeEventKind(str, Enum):
    """Audit event types emitted by the minigame arcade system."""
    MINIGAME_REGISTERED = "minigame_registered"
    MINIGAME_REMOVED = "minigame_removed"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    SCORE_SUBMITTED = "score_submitted"
    DAILY_CHALLENGE_REGISTERED = "daily_challenge_registered"
    DAILY_CHALLENGE_COMPLETED = "daily_challenge_completed"
    PRIZE_REGISTERED = "prize_registered"
    PRIZE_REMOVED = "prize_removed"
    PRIZE_REDEEMED = "prize_redeemed"
    TOKENS_AWARDED = "tokens_awarded"
    TOKENS_SPENT = "tokens_spent"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class MinigameDefinition:
    """A minigame catalog entry."""
    minigame_id: str
    name: str = ""
    game_type: str = MinigameType.ARCADE.value
    description: str = ""
    difficulty: str = DifficultyLevel.NORMAL.value
    entry_fee: int = 0
    token_reward: int = 10
    duration_seconds: float = 120.0
    max_players: int = 1
    min_level: int = 1
    icon: str = ""
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ScoreEntry:
    """A score record for a minigame."""
    score_id: str
    minigame_id: str
    player_id: str
    score: float = 0.0
    difficulty: str = DifficultyLevel.NORMAL.value
    tokens_earned: int = 0
    achieved_at: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MinigameSession:
    """A single play session of a minigame."""
    session_id: str
    minigame_id: str
    player_id: str
    state: str = MinigameState.WAITING.value
    difficulty: str = DifficultyLevel.NORMAL.value
    score: float = 0.0
    tokens_earned: int = 0
    started_at: float = 0.0
    ended_at: float = 0.0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DailyChallenge:
    """A daily challenge with bonus rewards."""
    challenge_id: str
    minigame_id: str
    name: str = ""
    description: str = ""
    target_score: float = 0.0
    token_reward: int = 50
    active: bool = False
    date: str = ""
    completions: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PrizeItem:
    """A prize available for token redemption."""
    prize_id: str
    name: str = ""
    description: str = ""
    token_cost: int = 100
    item_id: str = ""
    item_quantity: int = 1
    rarity: str = "common"
    stock: int = -1
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TokenLedger:
    """Token balance and transaction history for a player."""
    player_id: str
    balance: int = 0
    total_earned: int = 0
    total_spent: int = 0
    transactions: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArcadeConfig:
    """Global tuning parameters for the arcade system."""
    max_minigames: int = 200
    max_sessions: int = 5000
    max_scores_per_game: int = 1000
    max_daily_challenges: int = 50
    max_prizes: int = 200
    base_token_reward: int = 10
    daily_challenge_bonus: int = 50
    session_timeout_seconds: float = 300.0
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArcadeStats:
    """Aggregate statistics for the arcade system."""
    total_minigames: int = 0
    total_sessions: int = 0
    active_sessions: int = 0
    completed_sessions: int = 0
    total_scores: int = 0
    total_daily_challenges: int = 0
    active_daily_challenges: int = 0
    total_prizes: int = 0
    total_tokens_earned: int = 0
    total_tokens_spent: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArcadeSnapshot:
    """Full state snapshot of the arcade system."""
    minigames: List[Dict[str, Any]] = field(default_factory=list)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    daily_challenges: List[Dict[str, Any]] = field(default_factory=list)
    prizes: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ArcadeEvent:
    """An audit event emitted by the arcade system."""
    event_id: str
    kind: str
    timestamp: float
    minigame_id: Optional[str] = None
    session_id: Optional[str] = None
    player_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Minigame Arcade System
# ---------------------------------------------------------------------------

class MinigameArcadeSystem:
    """Manages minigames, sessions, scores, daily challenges, and prize shop."""

    _instance: Optional["MinigameArcadeSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._minigames: Dict[str, MinigameDefinition] = {}
        self._sessions: Dict[str, MinigameSession] = {}
        self._scores: Dict[str, List[ScoreEntry]] = {}
        self._daily_challenges: Dict[str, DailyChallenge] = {}
        self._prizes: Dict[str, PrizeItem] = {}
        self._tokens: Dict[str, TokenLedger] = {}
        self._events: List[ArcadeEvent] = []
        self._stats = ArcadeStats()
        self._config = ArcadeConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._session_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "MinigameArcadeSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample minigames, scores, challenges, prizes, and tokens."""
        with self._init_lock:
            if self._initialized:
                return

            mg1 = MinigameDefinition(
                minigame_id="mg_crystal_puzzle",
                name="Crystal Puzzle",
                game_type=MinigameType.PUZZLE.value,
                description="Match crystals to clear the board.",
                difficulty=DifficultyLevel.NORMAL.value,
                entry_fee=5,
                token_reward=20,
                duration_seconds=180.0,
                icon="icon_crystal",
            )
            self._minigames[mg1.minigame_id] = mg1

            mg2 = MinigameDefinition(
                minigame_id="mg_neon_racer",
                name="Neon Racer",
                game_type=MinigameType.RACING.value,
                description="Race through neon tracks at high speed.",
                difficulty=DifficultyLevel.HARD.value,
                entry_fee=10,
                token_reward=35,
                duration_seconds=120.0,
                icon="icon_racer",
            )
            self._minigames[mg2.minigame_id] = mg2

            mg3 = MinigameDefinition(
                minigame_id="mg_rhythm_beat",
                name="Rhythm Beat",
                game_type=MinigameType.RHYTHM.value,
                description="Hit the beats in sync with the music.",
                difficulty=DifficultyLevel.EXPERT.value,
                entry_fee=15,
                token_reward=50,
                duration_seconds=240.0,
                icon="icon_rhythm",
            )
            self._minigames[mg3.minigame_id] = mg3

            session1 = MinigameSession(
                session_id="sess_starter_01",
                minigame_id="mg_crystal_puzzle",
                player_id="player_starter",
                state=MinigameState.COMPLETED.value,
                difficulty=DifficultyLevel.NORMAL.value,
                score=8500.0,
                tokens_earned=20,
                started_at=_now() - 200,
                ended_at=_now() - 120,
                duration=80.0,
            )
            self._sessions[session1.session_id] = session1

            score1 = ScoreEntry(
                score_id="score_starter_01",
                minigame_id="mg_crystal_puzzle",
                player_id="player_starter",
                score=8500.0,
                difficulty=DifficultyLevel.NORMAL.value,
                tokens_earned=20,
                achieved_at=_now() - 120,
            )
            self._scores.setdefault("mg_crystal_puzzle", []).append(score1)

            dc1 = DailyChallenge(
                challenge_id="dc_starter_01",
                minigame_id="mg_crystal_puzzle",
                name="Daily Crystal Master",
                description="Score 10000 in Crystal Puzzle.",
                target_score=10000.0,
                token_reward=100,
                active=True,
                date="2026-07-08",
            )
            self._daily_challenges[dc1.challenge_id] = dc1

            prize1 = PrizeItem(
                prize_id="prize_starter_01",
                name="Golden Trophy",
                description="A shiny golden trophy.",
                token_cost=500,
                item_id="item_golden_trophy",
                rarity="epic",
                stock=10,
            )
            self._prizes[prize1.prize_id] = prize1

            prize2 = PrizeItem(
                prize_id="prize_starter_02",
                name="Token Booster",
                description="Doubles token rewards for 1 hour.",
                token_cost=200,
                item_id="item_token_booster",
                rarity="rare",
                stock=-1,
            )
            self._prizes[prize2.prize_id] = prize2

            ledger1 = TokenLedger(
                player_id="player_starter",
                balance=350,
                total_earned=500,
                total_spent=150,
                transactions=[
                    {"type": "earn", "amount": 500, "time": _now() - 86400},
                    {"type": "spend", "amount": 150, "time": _now() - 43200},
                ],
            )
            self._tokens[ledger1.player_id] = ledger1

            self._stats.total_minigames = len(self._minigames)
            self._stats.total_sessions = len(self._sessions)
            self._stats.completed_sessions = 1
            self._stats.total_scores = 1
            self._stats.total_daily_challenges = len(self._daily_challenges)
            self._stats.active_daily_challenges = 1
            self._stats.total_prizes = len(self._prizes)
            self._stats.total_tokens_earned = 500
            self._stats.total_tokens_spent = 150

            self._initialized = True

    def _emit_event(self, kind: str, minigame_id: Optional[str] = None,
                    session_id: Optional[str] = None, player_id: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> None:
        event = ArcadeEvent(
            event_id=f"evt_{self._event_counter}",
            kind=kind,
            timestamp=_now(),
            minigame_id=minigame_id,
            session_id=session_id,
            player_id=player_id,
            details=details or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _get_or_create_ledger(self, player_id: str) -> TokenLedger:
        if player_id not in self._tokens:
            self._tokens[player_id] = TokenLedger(player_id=player_id)
        return self._tokens[player_id]

    # ------------------------------------------------------------------
    # Minigame Management
    # ------------------------------------------------------------------

    def register_minigame(self, minigame: MinigameDefinition) -> Dict[str, Any]:
        with self._lock:
            if minigame.minigame_id in self._minigames:
                return {"registered": False, "reason": "already_registered"}
            if len(self._minigames) >= _MAX_MINIGAMES:
                _evict_fifo_list(list(self._minigames.keys()), _MAX_MINIGAMES)
            self._minigames[minigame.minigame_id] = minigame
            self._stats.total_minigames = len(self._minigames)
            self._emit_event(ArcadeEventKind.MINIGAME_REGISTERED.value,
                             minigame_id=minigame.minigame_id)
            return {"registered": True, "minigame_id": minigame.minigame_id}

    def remove_minigame(self, minigame_id: str) -> Dict[str, Any]:
        with self._lock:
            if minigame_id not in self._minigames:
                return {"removed": False, "reason": "minigame_not_found"}
            del self._minigames[minigame_id]
            self._scores.pop(minigame_id, None)
            self._stats.total_minigames = len(self._minigames)
            self._emit_event(ArcadeEventKind.MINIGAME_REMOVED.value, minigame_id=minigame_id)
            return {"removed": True, "minigame_id": minigame_id}

    def get_minigame(self, minigame_id: str) -> Optional[MinigameDefinition]:
        with self._lock:
            return self._minigames.get(minigame_id)

    def list_minigames(self, game_type: Optional[str] = None,
                       enabled_only: bool = False, limit: int = 100) -> List[MinigameDefinition]:
        with self._lock:
            result = []
            for mg in self._minigames.values():
                if game_type and mg.game_type != game_type:
                    continue
                if enabled_only and not mg.enabled:
                    continue
                result.append(mg)
            return result[:limit]

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def start_session(self, minigame_id: str, player_id: str,
                      difficulty: str = "normal") -> Dict[str, Any]:
        with self._lock:
            mg = self._minigames.get(minigame_id)
            if mg is None:
                return {"success": False, "reason": "minigame_not_found"}
            if not mg.enabled:
                return {"success": False, "reason": "minigame_disabled"}
            if len(self._sessions) >= _MAX_SESSIONS:
                _evict_fifo_list(list(self._sessions.keys()), _MAX_SESSIONS)
            session_id = f"sess_{minigame_id}_{player_id}_{self._session_counter}"
            self._session_counter += 1
            session = MinigameSession(
                session_id=session_id,
                minigame_id=minigame_id,
                player_id=player_id,
                state=MinigameState.PLAYING.value,
                difficulty=difficulty,
                started_at=_now(),
            )
            self._sessions[session_id] = session
            self._stats.total_sessions = len(self._sessions)
            self._stats.active_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.PLAYING.value)
            self._emit_event(ArcadeEventKind.SESSION_STARTED.value,
                             minigame_id=minigame_id, session_id=session_id, player_id=player_id)
            return {"success": True, "session_id": session_id, "started_at": session.started_at}

    def end_session(self, session_id: str, state: str = "completed") -> Dict[str, Any]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"success": False, "reason": "session_not_found"}
            if session.state != MinigameState.PLAYING.value:
                return {"success": False, "reason": "session_not_playing"}
            session.state = state
            session.ended_at = _now()
            session.duration = session.ended_at - session.started_at
            self._stats.active_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.PLAYING.value)
            self._stats.completed_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.COMPLETED.value)
            self._emit_event(ArcadeEventKind.SESSION_ENDED.value,
                             session_id=session_id, player_id=session.player_id,
                             details={"state": state, "duration": session.duration})
            return {"success": True, "session_id": session_id, "ended_at": session.ended_at}

    def get_session(self, session_id: str) -> Optional[MinigameSession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, minigame_id: Optional[str] = None,
                      player_id: Optional[str] = None,
                      state: Optional[str] = None, limit: int = 100) -> List[MinigameSession]:
        with self._lock:
            result = []
            for s in self._sessions.values():
                if minigame_id and s.minigame_id != minigame_id:
                    continue
                if player_id and s.player_id != player_id:
                    continue
                if state and s.state != state:
                    continue
                result.append(s)
            result.sort(key=lambda x: x.started_at, reverse=True)
            return result[:limit]

    # ------------------------------------------------------------------
    # Score Management
    # ------------------------------------------------------------------

    def submit_score(self, minigame_id: str, player_id: str, score: float,
                     difficulty: str = "normal", session_id: str = "") -> Dict[str, Any]:
        with self._lock:
            mg = self._minigames.get(minigame_id)
            if mg is None:
                return {"success": False, "reason": "minigame_not_found"}
            score_id = f"score_{minigame_id}_{player_id}_{self._event_counter}"
            self._event_counter += 1
            tokens = mg.token_reward
            entry = ScoreEntry(
                score_id=score_id,
                minigame_id=minigame_id,
                player_id=player_id,
                score=score,
                difficulty=difficulty,
                tokens_earned=tokens,
            )
            self._scores.setdefault(minigame_id, []).append(entry)
            _evict_fifo_list(self._scores[minigame_id], _MAX_SCORES_PER_GAME)
            self._stats.total_scores = sum(len(v) for v in self._scores.values())
            if session_id:
                session = self._sessions.get(session_id)
                if session:
                    session.score = score
                    session.tokens_earned = tokens
            self._award_tokens(player_id, tokens, "score_submission")
            self._emit_event(ArcadeEventKind.SCORE_SUBMITTED.value,
                             minigame_id=minigame_id, session_id=session_id,
                             player_id=player_id,
                             details={"score": score, "tokens": tokens})
            return {"success": True, "score_id": score_id, "tokens_earned": tokens}

    def get_high_scores(self, minigame_id: str, limit: int = 10) -> Dict[str, Any]:
        with self._lock:
            scores = self._scores.get(minigame_id, [])
            sorted_scores = sorted(scores, key=lambda x: x.score, reverse=True)
            return {"found": True, "scores": [s.to_dict() for s in sorted_scores[:limit]]}

    def get_player_best(self, minigame_id: str, player_id: str) -> Dict[str, Any]:
        with self._lock:
            scores = self._scores.get(minigame_id, [])
            player_scores = [s for s in scores if s.player_id == player_id]
            if not player_scores:
                return {"found": False, "reason": "no_score"}
            best = max(player_scores, key=lambda x: x.score)
            return {"found": True, "score": best.to_dict()}

    # ------------------------------------------------------------------
    # Daily Challenge Management
    # ------------------------------------------------------------------

    def register_daily_challenge(self, challenge: DailyChallenge) -> Dict[str, Any]:
        with self._lock:
            if challenge.challenge_id in self._daily_challenges:
                return {"registered": False, "reason": "already_registered"}
            if len(self._daily_challenges) >= _MAX_DAILY_CHALLENGES:
                _evict_fifo_list(list(self._daily_challenges.keys()), _MAX_DAILY_CHALLENGES)
            self._daily_challenges[challenge.challenge_id] = challenge
            self._stats.total_daily_challenges = len(self._daily_challenges)
            self._stats.active_daily_challenges = sum(1 for c in self._daily_challenges.values() if c.active)
            self._emit_event(ArcadeEventKind.DAILY_CHALLENGE_REGISTERED.value,
                             minigame_id=challenge.minigame_id)
            return {"registered": True, "challenge_id": challenge.challenge_id}

    def get_daily_challenge(self, challenge_id: str) -> Optional[DailyChallenge]:
        with self._lock:
            return self._daily_challenges.get(challenge_id)

    def complete_daily_challenge(self, challenge_id: str, player_id: str,
                                 score: float = 0.0) -> Dict[str, Any]:
        with self._lock:
            challenge = self._daily_challenges.get(challenge_id)
            if challenge is None:
                return {"success": False, "reason": "challenge_not_found"}
            if not challenge.active:
                return {"success": False, "reason": "challenge_inactive"}
            if player_id in challenge.completions:
                return {"success": False, "reason": "already_completed"}
            if score < challenge.target_score and challenge.target_score > 0:
                return {"success": False, "reason": "score_below_target"}
            challenge.completions.append(player_id)
            self._award_tokens(player_id, challenge.token_reward, "daily_challenge")
            self._emit_event(ArcadeEventKind.DAILY_CHALLENGE_COMPLETED.value,
                             minigame_id=challenge.minigame_id, player_id=player_id,
                             details={"tokens": challenge.token_reward})
            return {"success": True, "tokens_earned": challenge.token_reward}

    def list_daily_challenges(self, active_only: bool = False, limit: int = 100) -> List[DailyChallenge]:
        with self._lock:
            result = []
            for c in self._daily_challenges.values():
                if active_only and not c.active:
                    continue
                result.append(c)
            return result[:limit]

    # ------------------------------------------------------------------
    # Prize Shop
    # ------------------------------------------------------------------

    def register_prize(self, prize: PrizeItem) -> Dict[str, Any]:
        with self._lock:
            if prize.prize_id in self._prizes:
                return {"registered": False, "reason": "already_registered"}
            if len(self._prizes) >= _MAX_PRIZES:
                _evict_fifo_list(list(self._prizes.keys()), _MAX_PRIZES)
            self._prizes[prize.prize_id] = prize
            self._stats.total_prizes = len(self._prizes)
            self._emit_event(ArcadeEventKind.PRIZE_REGISTERED.value)
            return {"registered": True, "prize_id": prize.prize_id}

    def remove_prize(self, prize_id: str) -> Dict[str, Any]:
        with self._lock:
            if prize_id not in self._prizes:
                return {"removed": False, "reason": "prize_not_found"}
            del self._prizes[prize_id]
            self._stats.total_prizes = len(self._prizes)
            self._emit_event(ArcadeEventKind.PRIZE_REMOVED.value)
            return {"removed": True, "prize_id": prize_id}

    def list_prizes(self, limit: int = 100) -> List[PrizeItem]:
        with self._lock:
            return list(self._prizes.values())[:limit]

    def redeem_prize(self, prize_id: str, player_id: str) -> Dict[str, Any]:
        with self._lock:
            prize = self._prizes.get(prize_id)
            if prize is None:
                return {"success": False, "reason": "prize_not_found"}
            ledger = self._get_or_create_ledger(player_id)
            if ledger.balance < prize.token_cost:
                return {"success": False, "reason": "insufficient_tokens"}
            if prize.stock == 0:
                return {"success": False, "reason": "out_of_stock"}
            self._spend_tokens(player_id, prize.token_cost, "prize_redemption")
            if prize.stock > 0:
                prize.stock -= 1
            self._emit_event(ArcadeEventKind.PRIZE_REDEEMED.value,
                             player_id=player_id,
                             details={"prize_id": prize_id, "cost": prize.token_cost})
            return {"success": True, "prize_id": prize_id, "remaining_balance": ledger.balance}

    # ------------------------------------------------------------------
    # Token Economy
    # ------------------------------------------------------------------

    def _award_tokens(self, player_id: str, amount: int, reason: str) -> None:
        ledger = self._get_or_create_ledger(player_id)
        ledger.balance += amount
        ledger.total_earned += amount
        ledger.transactions.append({"type": "earn", "amount": amount, "reason": reason, "time": _now()})
        self._stats.total_tokens_earned += amount
        self._emit_event(ArcadeEventKind.TOKENS_AWARDED.value, player_id=player_id,
                         details={"amount": amount, "reason": reason})

    def _spend_tokens(self, player_id: str, amount: int, reason: str) -> None:
        ledger = self._get_or_create_ledger(player_id)
        ledger.balance -= amount
        ledger.total_spent += amount
        ledger.transactions.append({"type": "spend", "amount": amount, "reason": reason, "time": _now()})
        self._stats.total_tokens_spent += amount
        self._emit_event(ArcadeEventKind.TOKENS_SPENT.value, player_id=player_id,
                         details={"amount": amount, "reason": reason})

    def award_tokens(self, player_id: str, amount: int, reason: str = "manual") -> Dict[str, Any]:
        with self._lock:
            self._award_tokens(player_id, amount, reason)
            return {"success": True, "player_id": player_id, "amount": amount}

    def spend_tokens(self, player_id: str, amount: int, reason: str = "manual") -> Dict[str, Any]:
        with self._lock:
            ledger = self._get_or_create_ledger(player_id)
            if ledger.balance < amount:
                return {"success": False, "reason": "insufficient_tokens"}
            self._spend_tokens(player_id, amount, reason)
            return {"success": True, "player_id": player_id, "amount": amount}

    def get_token_balance(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            ledger = self._get_or_create_ledger(player_id)
            return {"found": True, "balance": ledger.balance,
                    "total_earned": ledger.total_earned,
                    "total_spent": ledger.total_spent}

    # ------------------------------------------------------------------
    # Tick / Config / Observability
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            now = _now()
            timed_out = 0
            for session in self._sessions.values():
                if session.state == MinigameState.PLAYING.value and session.started_at > 0:
                    elapsed = now - session.started_at
                    if elapsed > self._config.session_timeout_seconds:
                        session.state = MinigameState.ABANDONED.value
                        session.ended_at = now
                        session.duration = elapsed
                        timed_out += 1
            if timed_out > 0:
                self._stats.active_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.PLAYING.value)
            self._emit_event(ArcadeEventKind.TICK.value,
                             details={"delta_time": delta_time, "timed_out": timed_out})
            return {"success": True, "tick_count": self._tick_count, "timed_out": timed_out}

    def set_config(self, config: ArcadeConfig) -> Dict[str, Any]:
        with self._lock:
            self._config = config
            self._emit_event(ArcadeEventKind.CONFIG_UPDATED.value)
            return {"success": True}

    def get_config(self) -> ArcadeConfig:
        with self._lock:
            return self._config

    def list_events(self, minigame_id: Optional[str] = None, player_id: Optional[str] = None,
                    limit: int = 100) -> List[ArcadeEvent]:
        with self._lock:
            result = []
            for e in self._events:
                if minigame_id and e.minigame_id != minigame_id:
                    continue
                if player_id and e.player_id != player_id:
                    continue
                result.append(e)
            return result[:limit]

    def get_stats(self) -> ArcadeStats:
        with self._lock:
            self._stats.total_minigames = len(self._minigames)
            self._stats.total_sessions = len(self._sessions)
            self._stats.active_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.PLAYING.value)
            self._stats.completed_sessions = sum(1 for s in self._sessions.values() if s.state == MinigameState.COMPLETED.value)
            self._stats.total_scores = sum(len(v) for v in self._scores.values())
            self._stats.total_daily_challenges = len(self._daily_challenges)
            self._stats.active_daily_challenges = sum(1 for c in self._daily_challenges.values() if c.active)
            self._stats.total_prizes = len(self._prizes)
            self._stats.tick_count = self._tick_count
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_minigames": len(self._minigames),
                "total_sessions": len(self._sessions),
                "active_sessions": sum(1 for s in self._sessions.values() if s.state == MinigameState.PLAYING.value),
                "total_scores": sum(len(v) for v in self._scores.values()),
                "total_daily_challenges": len(self._daily_challenges),
                "active_daily_challenges": sum(1 for c in self._daily_challenges.values() if c.active),
                "total_prizes": len(self._prizes),
                "tick_count": self._tick_count,
            }

    def get_snapshot(self) -> ArcadeSnapshot:
        with self._lock:
            return ArcadeSnapshot(
                minigames=[mg.to_dict() for mg in list(self._minigames.values())[:50]],
                sessions=[s.to_dict() for s in list(self._sessions.values())[:50]],
                daily_challenges=[c.to_dict() for c in self._daily_challenges.values()],
                prizes=[p.to_dict() for p in self._prizes.values()],
                stats=self.get_stats().to_dict(),
                config=self._config.to_dict(),
                tick_count=self._tick_count,
            )

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._minigames.clear()
            self._sessions.clear()
            self._scores.clear()
            self._daily_challenges.clear()
            self._prizes.clear()
            self._tokens.clear()
            self._events.clear()
            self._stats = ArcadeStats()
            self._config = ArcadeConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._session_counter = 0
            self._initialized = False
            self._emit_event(ArcadeEventKind.RESET.value)
            self._seed()
            return {"success": True, "reset": True}


def get_minigame_arcade_system() -> MinigameArcadeSystem:
    """Get the singleton MinigameArcadeSystem instance."""
    return MinigameArcadeSystem.get_instance()
