"""
SparkLabs Engine - Casino, Betting & Wager System

Manages casino games, sports betting, wagers, and the in-game gambling
economy. Players can play slot machines, roulette, blackjack, dice games,
place bets on simulated events, create peer-to-peer wagers, and track
their gambling statistics and win/loss history.

The system supports multiple casino game types with configurable odds,
payouts, and house edges. Betting markets support event-based wagering
with dynamic odds. Peer wagers allow players to stake currency against
each other on custom conditions.

Architecture:
  CasinoBettingSystem (singleton)
    |-- GameType, GameOutcome, BetStatus, WagerStatus, CasinoEventKind
    |-- CasinoGame, GameSession, BetMarket, Bet, Wager, PlayerStats,
       CasinoConfig, CasinoStats, CasinoSnapshot, CasinoEvent
    |-- get_casino_betting_system

Core Capabilities:
  - register_game / remove_game / get_game / list_games: manage the
    catalog of available casino games with odds and payouts.
  - play_game / get_session / list_sessions: play casino games and track
    session history with win/loss outcomes.
  - register_market / remove_market / get_market / list_markets: manage
    betting markets for event-based wagering.
  - place_bet / cancel_bet / settle_bet / get_bet / list_bets: manage
    individual bets on betting markets.
  - create_wager / accept_wager / cancel_wager / settle_wager /
    get_wager / list_wagers: manage peer-to-peer wagers.
  - get_player_stats / get_leaderboard: track player gambling statistics.
  - tick / set_config / get_config: lifecycle and tuning.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CasinoBettingSystem.get_instance` or the module-level
:func:`get_casino_betting_system` factory.
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_GAMES: int = 100
_MAX_SESSIONS: int = 10000
_MAX_MARKETS: int = 200
_MAX_BETS: int = 50000
_MAX_WAGERS: int = 5000
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

class GameType(str, Enum):
    """Type of casino game."""
    SLOTS = "slots"
    ROULETTE = "roulette"
    BLACKJACK = "blackjack"
    DICE = "dice"
    POKER = "poker"
    WHEEL = "wheel"
    COIN_FLIP = "coin_flip"
    SCRATCH_CARD = "scratch_card"


class GameOutcome(str, Enum):
    """Outcome of a casino game session."""
    WIN = "win"
    LOSS = "loss"
    PUSH = "push"
    JACKPOT = "jackpot"


class BetStatus(str, Enum):
    """Status of a bet."""
    PENDING = "pending"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class WagerStatus(str, Enum):
    """Status of a peer-to-peer wager."""
    OPEN = "open"
    ACCEPTED = "accepted"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"
    SETTLED = "settled"


class CasinoEventKind(str, Enum):
    """Audit event types emitted by the casino betting system."""
    GAME_REGISTERED = "game_registered"
    GAME_REMOVED = "game_removed"
    SESSION_PLAYED = "session_played"
    MARKET_REGISTERED = "market_registered"
    MARKET_REMOVED = "market_removed"
    BET_PLACED = "bet_placed"
    BET_CANCELLED = "bet_cancelled"
    BET_SETTLED = "bet_settled"
    WAGER_CREATED = "wager_created"
    WAGER_ACCEPTED = "wager_accepted"
    WAGER_CANCELLED = "wager_cancelled"
    WAGER_SETTLED = "wager_settled"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class CasinoGame:
    """A casino game definition."""
    game_id: str
    name: str
    game_type: str = GameType.SLOTS.value
    description: str = ""
    min_bet: float = 1.0
    max_bet: float = 10000.0
    house_edge: float = 0.05
    base_payout: float = 2.0
    jackpot_payout: float = 100.0
    jackpot_chance: float = 0.001
    enabled: bool = True
    icon: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GameSession:
    """A single play session of a casino game."""
    session_id: str
    game_id: str
    player_id: str
    bet_amount: float = 0.0
    outcome: str = GameOutcome.LOSS.value
    payout: float = 0.0
    net_result: float = 0.0
    played_at: float = field(default_factory=_now)
    result_data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class BetMarket:
    """A betting market for event-based wagering."""
    market_id: str
    name: str
    description: str = ""
    options: List[Dict[str, Any]] = field(default_factory=list)
    state: str = "open"
    created_at: float = field(default_factory=_now)
    closes_at: float = 0.0
    settled_at: float = 0.0
    winning_option: str = ""
    total_pool: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Bet:
    """A bet placed on a betting market."""
    bet_id: str
    market_id: str
    player_id: str
    option: str = ""
    amount: float = 0.0
    odds: float = 2.0
    potential_payout: float = 0.0
    status: str = BetStatus.PENDING.value
    placed_at: float = field(default_factory=_now)
    settled_at: float = 0.0
    payout: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Wager:
    """A peer-to-peer wager between two players."""
    wager_id: str
    creator_id: str
    opponent_id: str = ""
    description: str = ""
    stake_amount: float = 0.0
    total_pot: float = 0.0
    status: str = WagerStatus.OPEN.value
    winner_id: str = ""
    loser_id: str = ""
    created_at: float = field(default_factory=_now)
    accepted_at: float = 0.0
    settled_at: float = 0.0
    expires_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerStats:
    """Gambling statistics for a player."""
    player_id: str
    total_sessions: int = 0
    total_wins: int = 0
    total_losses: int = 0
    total_pushes: int = 0
    total_jackpots: int = 0
    total_wagered: float = 0.0
    total_won: float = 0.0
    total_lost: float = 0.0
    net_profit: float = 0.0
    biggest_win: float = 0.0
    biggest_loss: float = 0.0
    current_streak: int = 0
    best_streak: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CasinoConfig:
    """Global tuning parameters for the casino betting system."""
    max_games: int = 100
    max_sessions: int = 10000
    max_markets: int = 200
    max_bets: int = 50000
    max_wagers: int = 5000
    default_min_bet: float = 1.0
    default_max_bet: float = 10000.0
    global_house_edge: float = 0.05
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CasinoStats:
    """Aggregate statistics for the casino betting system."""
    total_games: int = 0
    total_sessions: int = 0
    total_markets: int = 0
    total_bets: int = 0
    pending_bets: int = 0
    settled_bets: int = 0
    total_wagers: int = 0
    open_wagers: int = 0
    settled_wagers: int = 0
    total_wagered: float = 0.0
    total_payouts: float = 0.0
    house_revenue: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CasinoSnapshot:
    """Full state snapshot of the casino betting system."""
    games: List[Dict[str, Any]] = field(default_factory=list)
    markets: List[Dict[str, Any]] = field(default_factory=list)
    wagers: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CasinoEvent:
    """An audit event emitted by the casino betting system."""
    event_id: str
    kind: str
    timestamp: float
    game_id: str = ""
    market_id: str = ""
    bet_id: str = ""
    wager_id: str = ""
    player_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Casino Betting System
# ---------------------------------------------------------------------------

class CasinoBettingSystem:
    """Manages casino games, betting markets, and peer-to-peer wagers."""

    _instance: Optional["CasinoBettingSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._games: Dict[str, CasinoGame] = {}
        self._sessions: List[GameSession] = []
        self._markets: Dict[str, BetMarket] = {}
        self._bets: Dict[str, Bet] = {}
        self._wagers: Dict[str, Wager] = {}
        self._player_stats: Dict[str, PlayerStats] = {}
        self._events: List[CasinoEvent] = []
        self._stats = CasinoStats()
        self._config = CasinoConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._session_counter: int = 0
        self._bet_counter: int = 0
        self._wager_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "CasinoBettingSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial games, markets, wagers, and player stats."""
        with self._init_lock:
            if self._initialized:
                return

            # Casino games
            g1 = CasinoGame(
                game_id="game_slots_golden",
                name="Golden Slots",
                game_type=GameType.SLOTS.value,
                description="Classic 3-reel slot machine with gold theme.",
                min_bet=1.0,
                max_bet=5000.0,
                house_edge=0.05,
                base_payout=2.0,
                jackpot_payout=500.0,
                jackpot_chance=0.002,
                icon="icon_slots_golden",
            )
            self._games[g1.game_id] = g1

            g2 = CasinoGame(
                game_id="game_roulette_royal",
                name="Royal Roulette",
                game_type=GameType.ROULETTE.value,
                description="European roulette with single zero.",
                min_bet=5.0,
                max_bet=10000.0,
                house_edge=0.027,
                base_payout=2.0,
                jackpot_payout=36.0,
                jackpot_chance=0.027,
                icon="icon_roulette_royal",
            )
            self._games[g2.game_id] = g2

            g3 = CasinoGame(
                game_id="game_dice_highroller",
                name="High Roller Dice",
                game_type=GameType.DICE.value,
                description="Roll the dice for big payouts.",
                min_bet=1.0,
                max_bet=8000.0,
                house_edge=0.03,
                base_payout=2.0,
                jackpot_payout=6.0,
                jackpot_chance=0.167,
                icon="icon_dice_highroller",
            )
            self._games[g3.game_id] = g3

            g4 = CasinoGame(
                game_id="game_blackjack_classic",
                name="Classic Blackjack",
                game_type=GameType.BLACKJACK.value,
                description="Beat the dealer to 21.",
                min_bet=10.0,
                max_bet=15000.0,
                house_edge=0.005,
                base_payout=2.0,
                jackpot_payout=2.5,
                jackpot_chance=0.0,
                icon="icon_blackjack_classic",
            )
            self._games[g4.game_id] = g4

            g5 = CasinoGame(
                game_id="game_coinflip_lucky",
                name="Lucky Coin Flip",
                game_type=GameType.COIN_FLIP.value,
                description="Heads or tails, 50/50 chance.",
                min_bet=1.0,
                max_bet=20000.0,
                house_edge=0.0,
                base_payout=2.0,
                jackpot_payout=2.0,
                jackpot_chance=0.0,
                icon="icon_coinflip_lucky",
            )
            self._games[g5.game_id] = g5

            # Betting markets
            m1 = BetMarket(
                market_id="market_starter_01",
                name="Arena Championship Final",
                description="Bet on the winner of the arena championship.",
                options=[
                    {"option_id": "opt_warrior", "label": "Warrior", "odds": 2.5},
                    {"option_id": "opt_mage", "label": "Mage", "odds": 1.8},
                    {"option_id": "opt_rogue", "label": "Rogue", "odds": 3.2},
                ],
                state="open",
                closes_at=_now() + 3600.0,
                total_pool=5000.0,
            )
            self._markets[m1.market_id] = m1

            m2 = BetMarket(
                market_id="market_starter_02",
                name="Dragon Raid Outcome",
                description="Will the dragon raid succeed?",
                options=[
                    {"option_id": "opt_success", "label": "Success", "odds": 1.5},
                    {"option_id": "opt_fail", "label": "Failure", "odds": 2.8},
                ],
                state="settled",
                closes_at=_now() - 1800.0,
                settled_at=_now() - 900.0,
                winning_option="opt_success",
                total_pool=3200.0,
            )
            self._markets[m2.market_id] = m2

            # Wagers
            w1 = Wager(
                wager_id="wager_starter_01",
                creator_id="player_starter",
                opponent_id="player_veteran",
                description="Who can clear the dungeon first",
                stake_amount=500.0,
                total_pot=1000.0,
                status=WagerStatus.ACCEPTED.value,
                created_at=_now() - 7200.0,
                accepted_at=_now() - 3600.0,
                expires_at=_now() + 86400.0,
            )
            self._wagers[w1.wager_id] = w1

            w2 = Wager(
                wager_id="wager_starter_02",
                creator_id="player_starter",
                opponent_id="",
                description="Bet I can defeat the boss solo",
                stake_amount=200.0,
                total_pot=200.0,
                status=WagerStatus.OPEN.value,
                created_at=_now() - 3600.0,
                expires_at=_now() + 43200.0,
            )
            self._wagers[w2.wager_id] = w2

            # Player stats
            self._player_stats["player_starter"] = PlayerStats(
                player_id="player_starter",
                total_sessions=120,
                total_wins=45,
                total_losses=70,
                total_pushes=5,
                total_jackpots=0,
                total_wagered=25000.0,
                total_won=18000.0,
                total_lost=15000.0,
                net_profit=3000.0,
                biggest_win=2000.0,
                biggest_loss=800.0,
                current_streak=2,
                best_streak=5,
            )

            self._player_stats["player_veteran"] = PlayerStats(
                player_id="player_veteran",
                total_sessions=300,
                total_wins=140,
                total_losses=150,
                total_pushes=10,
                total_jackpots=2,
                total_wagered=100000.0,
                total_won=85000.0,
                total_lost=70000.0,
                net_profit=15000.0,
                biggest_win=15000.0,
                biggest_loss=3000.0,
                current_streak=-3,
                best_streak=12,
            )

            # A settled bet for player_starter
            b1 = Bet(
                bet_id="bet_starter_01",
                market_id="market_starter_02",
                player_id="player_starter",
                option="opt_success",
                amount=500.0,
                odds=1.5,
                potential_payout=750.0,
                status=BetStatus.WON.value,
                placed_at=_now() - 2700.0,
                settled_at=_now() - 900.0,
                payout=750.0,
            )
            self._bets[b1.bet_id] = b1

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from current state."""
        self._stats.total_games = len(self._games)
        self._stats.total_sessions = len(self._sessions)
        self._stats.total_markets = len(self._markets)
        self._stats.total_bets = len(self._bets)
        self._stats.pending_bets = sum(
            1 for b in self._bets.values() if b.status == BetStatus.PENDING.value
        )
        self._stats.settled_bets = sum(
            1 for b in self._bets.values()
            if b.status in (BetStatus.WON.value, BetStatus.LOST.value)
        )
        self._stats.total_wagers = len(self._wagers)
        self._stats.open_wagers = sum(
            1 for w in self._wagers.values()
            if w.status in (WagerStatus.OPEN.value, WagerStatus.ACCEPTED.value)
        )
        self._stats.settled_wagers = sum(
            1 for w in self._wagers.values()
            if w.status in (WagerStatus.WON.value, WagerStatus.LOST.value, WagerStatus.SETTLED.value)
        )
        self._stats.total_wagered = sum(
            ps.total_wagered for ps in self._player_stats.values()
        )
        self._stats.total_payouts = sum(
            ps.total_won for ps in self._player_stats.values()
        )
        self._stats.house_revenue = self._stats.total_wagered - self._stats.total_payouts
        self._stats.tick_count = self._tick_count

    def _record_event(
        self,
        kind: str,
        game_id: str = "",
        market_id: str = "",
        bet_id: str = "",
        wager_id: str = "",
        player_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> CasinoEvent:
        """Record an audit event."""
        self._event_counter += 1
        event = CasinoEvent(
            event_id=f"evt_{self._event_counter:08d}",
            kind=kind,
            timestamp=_now(),
            game_id=game_id,
            market_id=market_id,
            bet_id=bet_id,
            wager_id=wager_id,
            player_id=player_id,
            description=description,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _get_or_create_player_stats(self, player_id: str) -> PlayerStats:
        """Get or create player stats."""
        if player_id not in self._player_stats:
            self._player_stats[player_id] = PlayerStats(player_id=player_id)
        return self._player_stats[player_id]

    def _update_player_stats(
        self,
        player_id: str,
        bet_amount: float,
        outcome: str,
        payout: float,
    ) -> None:
        """Update player statistics after a game session."""
        ps = self._get_or_create_player_stats(player_id)
        ps.total_sessions += 1
        ps.total_wagered += bet_amount
        if outcome == GameOutcome.WIN.value:
            ps.total_wins += 1
            ps.total_won += payout
            if payout - bet_amount > ps.biggest_win:
                ps.biggest_win = payout - bet_amount
            if ps.current_streak >= 0:
                ps.current_streak += 1
            else:
                ps.current_streak = 1
            if ps.current_streak > ps.best_streak:
                ps.best_streak = ps.current_streak
        elif outcome == GameOutcome.JACKPOT.value:
            ps.total_jackpots += 1
            ps.total_wins += 1
            ps.total_won += payout
            if payout - bet_amount > ps.biggest_win:
                ps.biggest_win = payout - bet_amount
            ps.current_streak = max(1, ps.current_streak + 1)
            if ps.current_streak > ps.best_streak:
                ps.best_streak = ps.current_streak
        elif outcome == GameOutcome.LOSS.value:
            ps.total_losses += 1
            ps.total_lost += bet_amount
            if bet_amount > ps.biggest_loss:
                ps.biggest_loss = bet_amount
            if ps.current_streak <= 0:
                ps.current_streak -= 1
            else:
                ps.current_streak = -1
        elif outcome == GameOutcome.PUSH.value:
            ps.total_pushes += 1
            ps.total_won += payout
        ps.net_profit = ps.total_won - ps.total_lost

    # ------------------------------------------------------------------
    # Game Management
    # ------------------------------------------------------------------

    def register_game(
        self,
        game_id: str,
        name: str,
        game_type: str = GameType.SLOTS.value,
        description: str = "",
        min_bet: float = 1.0,
        max_bet: float = 10000.0,
        house_edge: float = 0.05,
        base_payout: float = 2.0,
        jackpot_payout: float = 100.0,
        jackpot_chance: float = 0.001,
        enabled: bool = True,
        icon: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CasinoGame]]:
        """Register a new casino game."""
        if not game_id or not name:
            return False, "game_id and name required", None
        if game_id in self._games:
            return False, "game_id already exists", None
        if len(self._games) >= _MAX_GAMES:
            return False, "game capacity reached", None
        game = CasinoGame(
            game_id=game_id,
            name=name,
            game_type=game_type,
            description=description,
            min_bet=_safe_float(min_bet, 1.0),
            max_bet=_safe_float(max_bet, 10000.0),
            house_edge=_clamp(_safe_float(house_edge, 0.05), 0.0, 1.0),
            base_payout=_safe_float(base_payout, 2.0),
            jackpot_payout=_safe_float(jackpot_payout, 100.0),
            jackpot_chance=_clamp(_safe_float(jackpot_chance, 0.001), 0.0, 1.0),
            enabled=enabled,
            icon=icon,
            metadata=metadata or {},
        )
        self._games[game_id] = game
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.GAME_REGISTERED.value,
            game_id=game_id,
            description=f"Game registered: {name}",
        )
        return True, "registered", game

    def remove_game(self, game_id: str) -> Tuple[bool, str]:
        """Remove a casino game."""
        if game_id not in self._games:
            return False, "not_found"
        del self._games[game_id]
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.GAME_REMOVED.value,
            game_id=game_id,
            description=f"Game removed: {game_id}",
        )
        return True, "removed"

    def get_game(self, game_id: str) -> Optional[CasinoGame]:
        """Get a casino game by ID."""
        return self._games.get(game_id)

    def list_games(
        self, game_type: Optional[str] = None, enabled_only: bool = False, limit: int = 100
    ) -> List[CasinoGame]:
        """List games optionally filtered by type and enabled state."""
        games = list(self._games.values())
        if game_type:
            games = [g for g in games if g.game_type == game_type]
        if enabled_only:
            games = [g for g in games if g.enabled]
        return games[:limit]

    def play_game(
        self,
        game_id: str,
        player_id: str,
        bet_amount: float = 1.0,
    ) -> Tuple[bool, str, Optional[GameSession]]:
        """Play a casino game and return the session result."""
        game = self._games.get(game_id)
        if game is None:
            return False, "game_not_found", None
        if not game.enabled:
            return False, "game_disabled", None
        bet = _safe_float(bet_amount, 0.0)
        if bet < game.min_bet:
            return False, "bet_below_minimum", None
        if bet > game.max_bet:
            return False, "bet_above_maximum", None
        # Determine outcome based on house edge
        roll = random.random()
        # Jackpot check
        if game.jackpot_chance > 0 and roll < game.jackpot_chance:
            outcome = GameOutcome.JACKPOT.value
            payout = bet * game.jackpot_payout
        elif roll < (1.0 - game.house_edge) / game.base_payout:
            outcome = GameOutcome.WIN.value
            payout = bet * game.base_payout
        elif roll < (1.0 - game.house_edge / 2):
            outcome = GameOutcome.PUSH.value
            payout = bet
        else:
            outcome = GameOutcome.LOSS.value
            payout = 0.0
        self._session_counter += 1
        session = GameSession(
            session_id=f"sess_{self._session_counter:08d}",
            game_id=game_id,
            player_id=player_id,
            bet_amount=bet,
            outcome=outcome,
            payout=payout,
            net_result=payout - bet,
            result_data={
                "game_type": game.game_type,
                "house_edge": game.house_edge,
                "roll": roll,
            },
        )
        self._sessions.append(session)
        _evict_fifo_list(self._sessions, _MAX_SESSIONS)
        self._update_player_stats(player_id, bet, outcome, payout)
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.SESSION_PLAYED.value,
            game_id=game_id,
            player_id=player_id,
            description=f"Game played: {game.name} by {player_id}",
            details={
                "outcome": outcome,
                "bet": bet,
                "payout": payout,
                "net": payout - bet,
            },
        )
        return True, outcome, session

    def get_session(self, session_id: str) -> Optional[GameSession]:
        """Get a game session by ID."""
        for s in self._sessions:
            if s.session_id == session_id:
                return s
        return None

    def list_sessions(
        self,
        player_id: Optional[str] = None,
        game_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[GameSession]:
        """List game sessions optionally filtered by player and game."""
        sessions = list(self._sessions)
        if player_id:
            sessions = [s for s in sessions if s.player_id == player_id]
        if game_id:
            sessions = [s for s in sessions if s.game_id == game_id]
        return sessions[-limit:]

    # ------------------------------------------------------------------
    # Betting Market Management
    # ------------------------------------------------------------------

    def register_market(
        self,
        market_id: str,
        name: str,
        description: str = "",
        options: Optional[List[Dict[str, Any]]] = None,
        closes_at: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[BetMarket]]:
        """Register a new betting market."""
        if not market_id or not name:
            return False, "market_id and name required", None
        if market_id in self._markets:
            return False, "market_id already exists", None
        if len(self._markets) >= _MAX_MARKETS:
            return False, "market capacity reached", None
        market = BetMarket(
            market_id=market_id,
            name=name,
            description=description,
            options=options or [],
            state="open",
            closes_at=closes_at if closes_at > 0 else _now() + 86400.0,
            metadata=metadata or {},
        )
        self._markets[market_id] = market
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.MARKET_REGISTERED.value,
            market_id=market_id,
            description=f"Market registered: {name}",
        )
        return True, "registered", market

    def remove_market(self, market_id: str) -> Tuple[bool, str]:
        """Remove a betting market."""
        if market_id not in self._markets:
            return False, "not_found"
        del self._markets[market_id]
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.MARKET_REMOVED.value,
            market_id=market_id,
            description=f"Market removed: {market_id}",
        )
        return True, "removed"

    def get_market(self, market_id: str) -> Optional[BetMarket]:
        """Get a betting market by ID."""
        return self._markets.get(market_id)

    def list_markets(
        self, state: Optional[str] = None, limit: int = 100
    ) -> List[BetMarket]:
        """List betting markets optionally filtered by state."""
        markets = list(self._markets.values())
        if state:
            markets = [m for m in markets if m.state == state]
        return markets[:limit]

    def place_bet(
        self,
        market_id: str,
        player_id: str,
        option: str,
        amount: float = 1.0,
    ) -> Tuple[bool, str, Optional[Bet]]:
        """Place a bet on a betting market."""
        market = self._markets.get(market_id)
        if market is None:
            return False, "market_not_found", None
        if market.state != "open":
            return False, "market_closed", None
        if _now() > market.closes_at and market.closes_at > 0:
            return False, "market_expired", None
        option_data = None
        for opt in market.options:
            if opt.get("option_id") == option:
                option_data = opt
                break
        if option_data is None:
            return False, "invalid_option", None
        amt = _safe_float(amount, 0.0)
        if amt <= 0:
            return False, "amount_must_be_positive", None
        odds = _safe_float(option_data.get("odds", 2.0), 2.0)
        self._bet_counter += 1
        bet = Bet(
            bet_id=f"bet_{self._bet_counter:08d}",
            market_id=market_id,
            player_id=player_id,
            option=option,
            amount=amt,
            odds=odds,
            potential_payout=amt * odds,
            status=BetStatus.PENDING.value,
        )
        self._bets[bet.bet_id] = bet
        market.total_pool += amt
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.BET_PLACED.value,
            market_id=market_id,
            bet_id=bet.bet_id,
            player_id=player_id,
            description=f"Bet placed: {amt} on {option}",
            details={"amount": amt, "option": option, "odds": odds},
        )
        return True, "placed", bet

    def cancel_bet(self, bet_id: str) -> Tuple[bool, str, Optional[Bet]]:
        """Cancel a pending bet."""
        bet = self._bets.get(bet_id)
        if bet is None:
            return False, "not_found", None
        if bet.status != BetStatus.PENDING.value:
            return False, "not_pending", None
        bet.status = BetStatus.CANCELLED.value
        market = self._markets.get(bet.market_id)
        if market:
            market.total_pool = max(0.0, market.total_pool - bet.amount)
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.BET_CANCELLED.value,
            bet_id=bet_id,
            player_id=bet.player_id,
            description=f"Bet cancelled: {bet_id}",
        )
        return True, "cancelled", bet

    def settle_bet(
        self,
        bet_id: str,
        won: bool,
    ) -> Tuple[bool, str, Optional[Bet]]:
        """Settle a pending bet."""
        bet = self._bets.get(bet_id)
        if bet is None:
            return False, "not_found", None
        if bet.status != BetStatus.PENDING.value:
            return False, "not_pending", None
        bet.status = BetStatus.WON.value if won else BetStatus.LOST.value
        bet.settled_at = _now()
        if won:
            bet.payout = bet.potential_payout
        else:
            bet.payout = 0.0
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.BET_SETTLED.value,
            bet_id=bet_id,
            player_id=bet.player_id,
            description=f"Bet settled: {bet_id} {'won' if won else 'lost'}",
            details={"won": won, "payout": bet.payout},
        )
        return True, "settled", bet

    def settle_market(
        self,
        market_id: str,
        winning_option: str,
    ) -> Tuple[bool, str, Optional[BetMarket]]:
        """Settle a betting market and all its pending bets."""
        market = self._markets.get(market_id)
        if market is None:
            return False, "not_found", None
        if market.state != "open":
            return False, "not_open", None
        market.state = "settled"
        market.winning_option = winning_option
        market.settled_at = _now()
        # Settle all pending bets
        for bet in self._bets.values():
            if bet.market_id == market_id and bet.status == BetStatus.PENDING.value:
                won = bet.option == winning_option
                bet.status = BetStatus.WON.value if won else BetStatus.LOST.value
                bet.settled_at = _now()
                if won:
                    bet.payout = bet.potential_payout
                else:
                    bet.payout = 0.0
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.MARKET_REGISTERED.value,
            market_id=market_id,
            description=f"Market settled: {market.name}, winning option: {winning_option}",
        )
        return True, "settled", market

    def get_bet(self, bet_id: str) -> Optional[Bet]:
        """Get a bet by ID."""
        return self._bets.get(bet_id)

    def list_bets(
        self,
        player_id: Optional[str] = None,
        market_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> List[Bet]:
        """List bets optionally filtered by player, market, and status."""
        bets = list(self._bets.values())
        if player_id:
            bets = [b for b in bets if b.player_id == player_id]
        if market_id:
            bets = [b for b in bets if b.market_id == market_id]
        if status:
            bets = [b for b in bets if b.status == status]
        return bets[-limit:]

    # ------------------------------------------------------------------
    # Wager Management
    # ------------------------------------------------------------------

    def create_wager(
        self,
        wager_id: str,
        creator_id: str,
        description: str = "",
        stake_amount: float = 0.0,
        expires_at: float = 0.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Wager]]:
        """Create a new peer-to-peer wager."""
        if not wager_id or not creator_id:
            return False, "wager_id and creator_id required", None
        if wager_id in self._wagers:
            return False, "wager_id already exists", None
        if len(self._wagers) >= _MAX_WAGERS:
            return False, "wager capacity reached", None
        stake = _safe_float(stake_amount, 0.0)
        if stake <= 0:
            return False, "stake_must_be_positive", None
        wager = Wager(
            wager_id=wager_id,
            creator_id=creator_id,
            description=description,
            stake_amount=stake,
            total_pot=stake,
            status=WagerStatus.OPEN.value,
            expires_at=expires_at if expires_at > 0 else _now() + 86400.0,
            metadata=metadata or {},
        )
        self._wagers[wager_id] = wager
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.WAGER_CREATED.value,
            wager_id=wager_id,
            player_id=creator_id,
            description=f"Wager created: {wager_id} by {creator_id}",
            details={"stake": stake},
        )
        return True, "created", wager

    def accept_wager(
        self,
        wager_id: str,
        opponent_id: str,
    ) -> Tuple[bool, str, Optional[Wager]]:
        """Accept an open wager."""
        wager = self._wagers.get(wager_id)
        if wager is None:
            return False, "not_found", None
        if wager.status != WagerStatus.OPEN.value:
            return False, "not_open", None
        if wager.creator_id == opponent_id:
            return False, "cannot_accept_own_wager", None
        wager.opponent_id = opponent_id
        wager.status = WagerStatus.ACCEPTED.value
        wager.accepted_at = _now()
        wager.total_pot = wager.stake_amount * 2
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.WAGER_ACCEPTED.value,
            wager_id=wager_id,
            player_id=opponent_id,
            description=f"Wager accepted: {wager_id} by {opponent_id}",
        )
        return True, "accepted", wager

    def cancel_wager(self, wager_id: str) -> Tuple[bool, str, Optional[Wager]]:
        """Cancel an open or accepted wager."""
        wager = self._wagers.get(wager_id)
        if wager is None:
            return False, "not_found", None
        if wager.status not in (WagerStatus.OPEN.value, WagerStatus.ACCEPTED.value):
            return False, "not_cancellable", None
        wager.status = WagerStatus.CANCELLED.value
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.WAGER_CANCELLED.value,
            wager_id=wager_id,
            description=f"Wager cancelled: {wager_id}",
        )
        return True, "cancelled", wager

    def settle_wager(
        self,
        wager_id: str,
        winner_id: str,
    ) -> Tuple[bool, str, Optional[Wager]]:
        """Settle a wager by specifying the winner."""
        wager = self._wagers.get(wager_id)
        if wager is None:
            return False, "not_found", None
        if wager.status != WagerStatus.ACCEPTED.value:
            return False, "not_accepted", None
        if winner_id not in (wager.creator_id, wager.opponent_id):
            return False, "invalid_winner", None
        wager.winner_id = winner_id
        wager.loser_id = wager.opponent_id if winner_id == wager.creator_id else wager.creator_id
        wager.status = WagerStatus.SETTLED.value
        wager.settled_at = _now()
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.WAGER_SETTLED.value,
            wager_id=wager_id,
            player_id=winner_id,
            description=f"Wager settled: {wager_id}, winner: {winner_id}",
            details={"winner": winner_id, "total_pot": wager.total_pot},
        )
        return True, "settled", wager

    def get_wager(self, wager_id: str) -> Optional[Wager]:
        """Get a wager by ID."""
        return self._wagers.get(wager_id)

    def list_wagers(
        self,
        status: Optional[str] = None,
        player_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Wager]:
        """List wagers optionally filtered by status and player."""
        wagers = list(self._wagers.values())
        if status:
            wagers = [w for w in wagers if w.status == status]
        if player_id:
            wagers = [
                w for w in wagers
                if w.creator_id == player_id or w.opponent_id == player_id
            ]
        return wagers[:limit]

    # ------------------------------------------------------------------
    # Player Stats and Leaderboard
    # ------------------------------------------------------------------

    def get_player_stats(self, player_id: str) -> Optional[PlayerStats]:
        """Get gambling statistics for a player."""
        return self._player_stats.get(player_id)

    def get_leaderboard(
        self, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get the gambling leaderboard sorted by net profit descending."""
        sorted_stats = sorted(
            self._player_stats.values(),
            key=lambda ps: ps.net_profit,
            reverse=True,
        )
        leaderboard = []
        for rank_idx, ps in enumerate(sorted_stats[:limit], 1):
            leaderboard.append({
                "rank": rank_idx,
                "player_id": ps.player_id,
                "net_profit": ps.net_profit,
                "total_wagered": ps.total_wagered,
                "total_wins": ps.total_wins,
                "total_jackpots": ps.total_jackpots,
            })
        return leaderboard

    # ------------------------------------------------------------------
    # Tick, Config, Events, Stats, Status, Snapshot, Reset
    # ------------------------------------------------------------------

    def tick(self, dt: float = 1.0) -> Dict[str, Any]:
        """Advance the simulation by dt seconds."""
        self._tick_count += 1
        now = _now()
        # Close expired markets
        for market in self._markets.values():
            if market.state == "open" and market.closes_at > 0 and now >= market.closes_at:
                market.state = "closed"
        # Expire open wagers
        for wager in self._wagers.values():
            if wager.status == WagerStatus.OPEN.value and wager.expires_at > 0 and now >= wager.expires_at:
                wager.status = WagerStatus.CANCELLED.value
        self._refresh_stats()
        self._record_event(
            CasinoEventKind.TICK.value,
            description=f"Tick {self._tick_count}",
            details={"dt": dt, "tick_count": self._tick_count},
        )
        return {
            "tick_count": self._tick_count,
            "total_sessions": self._stats.total_sessions,
            "open_wagers": self._stats.open_wagers,
        }

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, CasinoConfig]:
        """Update configuration parameters."""
        for k, v in kwargs.items():
            if hasattr(self._config, k):
                setattr(self._config, k, v)
        self._record_event(
            CasinoEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
            details=kwargs,
        )
        return True, "updated", self._config

    def get_config(self) -> CasinoConfig:
        """Get current configuration."""
        return self._config

    def list_events(
        self, kind: Optional[str] = None, limit: int = 100
    ) -> List[CasinoEvent]:
        """List events optionally filtered by kind."""
        events = list(self._events)
        if kind:
            events = [e for e in events if e.kind == kind]
        return events[-limit:]

    def get_stats(self) -> CasinoStats:
        """Get aggregate statistics."""
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Get system status summary."""
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_games": len(self._games),
            "total_sessions": len(self._sessions),
            "total_markets": len(self._markets),
            "total_bets": len(self._bets),
            "total_wagers": len(self._wagers),
            "total_player_stats": len(self._player_stats),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> CasinoSnapshot:
        """Get full state snapshot."""
        self._refresh_stats()
        return CasinoSnapshot(
            games=[g.to_dict() for g in list(self._games.values())[:50]],
            markets=[m.to_dict() for m in list(self._markets.values())[:50]],
            wagers=[w.to_dict() for w in list(self._wagers.values())[:50]],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        """Reset the system to seed state."""
        with self._init_lock:
            self._games.clear()
            self._sessions.clear()
            self._markets.clear()
            self._bets.clear()
            self._wagers.clear()
            self._player_stats.clear()
            self._events.clear()
            self._stats = CasinoStats()
            self._config = CasinoConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._session_counter = 0
            self._bet_counter = 0
            self._wager_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            CasinoEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_casino_betting_system() -> CasinoBettingSystem:
    """Factory function to get the CasinoBettingSystem singleton instance."""
    return CasinoBettingSystem.get_instance()
