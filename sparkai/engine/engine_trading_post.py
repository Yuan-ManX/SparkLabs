"""
SparkLabs Engine - Player-to-Player Trading & Auction House System

An original, self-contained commerce layer for the SparkLabs AI-native game
engine. The system lets players publish item listings (fixed price, want-to-
sell, want-to-buy, want-to-trade, bundles), negotiate through trade offers,
and run time-boxed auctions with bids, buyouts, and bid increments. All
economic activity flows through per-player wallets, and a price-history ledger
records observed transaction prices per item and currency so that fair-market
values can be derived.

Architecture:
  TradingPostSystem (singleton)
    |-- ItemListing            -- a seller's published item offer
    |-- TradeOffer             -- a buyer's bid/counter on a listing
    |-- Auction                -- a timed, competitive bidding container
    |-- Transaction            -- a settled economic exchange record
    |-- PlayerWallet           -- per-player multi-currency balances
    |-- PriceHistory           -- rolling observed-price ledger per item
    |-- TradingPostStats       -- aggregate counters
    |-- TradingPostSnapshot    -- immutable full-state snapshot
    |-- TradingPostEvent       -- audit log entry
    |-- ListingType, ListingStatus, OfferStatus, RarityTier, CurrencyType,
        AuctionState, TradingPostEventKind

Core Capabilities:
  - create_listing / get_listing / list_listings / update_listing /
    cancel_listing: full listing lifecycle with rarity tiers and currencies.
  - make_offer / get_offer / list_offers / accept_offer / reject_offer /
    counter_offer / withdraw_offer: negotiated trade offer workflow.
  - create_auction / get_auction / list_auctions / place_bid / settle_auction /
    cancel_auction: timed auctions with minimum increments and buyouts.
  - get_wallet / adjust_balance / suspend_wallet / reinstate_wallet: per-player
    multi-currency wallet management with reputation tracking.
  - get_price_history / record_price: rolling market-price aggregation.
  - get_transaction / list_transactions: settled-exchange history.
  - list_events / get_stats / get_status / get_snapshot / reset: observability
    and state management.

The module is written from scratch for SparkLabs. It depends only on the
Python standard library and follows the engine-wide singleton + reentrant-lock
conventions used across the SparkLabs engine modules.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_LISTINGS: int = 10000
_MAX_OFFERS: int = 10000
_MAX_TRANSACTIONS: int = 20000
_MAX_AUCTIONS: int = 5000
_MAX_WALLETS: int = 20000
_MAX_PRICE_HISTORY: int = 8000
_MAX_EVENTS: int = 8000
_MAX_RECENT_PRICES: int = 50  # rolling window of prices kept per item/currency

# Economic policy constants.
_FEE_RATE: float = 0.05  # 5% marketplace fee on the final price.
_TAX_RATE: float = 0.02  # 2% tax on the final price.
_DEFAULT_EXPIRY_HOURS: int = 168  # one week.
_DEFAULT_AUCTION_DURATION_HOURS: int = 24
_DEFAULT_MIN_INCREMENT: float = 1.0

# Starter grant for freshly created wallets so players can trade immediately.
_STARTER_GOLD: float = 5000.0
_STARTER_GEMS: float = 200.0
_STARTER_COINS: float = 1000.0
_STARTER_CREDITS: float = 100.0
_STARTER_TOKENS: float = 50.0
_STARTER_RUNES: float = 25.0


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a ``Z`` suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed.

    Args:
        prefix: Optional prefix joined to the generated identifier with an
            underscore. When empty, the raw hexadecimal identifier is returned.

    Returns:
        A short hexadecimal identifier, optionally prefixed.
    """
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict until it fits within ``max_size``.

    Eviction is FIFO based on dict insertion order. The capacity is floored at
    one so that a store can always retain its most recent entry.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list until it fits within ``max_size``.

    Eviction is FIFO by popping from the front of the list.
    """
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value into a JSON-friendly representation.

    Handles ``None``, ``Enum`` values (returns ``.value``), dicts, lists and
    tuples, and any object exposing a ``to_dict()`` method (such as the
    dataclasses defined in this module). All other values are returned
    unchanged.
    """
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, set):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return _dataclass_to_dict(value)
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    """Serialize a dataclass instance into a dict via ``_to_jsonable``.

    Iterates over ``__dataclass_fields__`` so that field order is preserved and
    every value is normalized through ``_to_jsonable``. Non-dataclass inputs
    degrade gracefully to an empty dict (or a copy when a plain dict is given).
    """
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


def _compute_fees(price: float) -> Tuple[float, float, float]:
    """Compute the marketplace fee, tax, and seller proceeds for a price.

    Returns a tuple of ``(fee, tax, seller_proceeds)`` where ``seller_proceeds``
    is the amount credited to the seller after fee and tax are deducted.
    """
    fee = round(max(0.0, price) * _FEE_RATE, 4)
    tax = round(max(0.0, price) * _TAX_RATE, 4)
    seller_proceeds = round(max(0.0, price) - fee - tax, 4)
    return fee, tax, seller_proceeds


def _iso_from_now(hours: float) -> str:
    """Return an ISO-8601 ``Z`` timestamp that is ``hours`` from now."""
    ts = datetime.utcnow().timestamp() + max(0.0, float(hours)) * 3600.0
    return datetime.utcfromtimestamp(ts).isoformat() + "Z"


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ListingType(Enum):
    """The commercial intent of an item listing."""

    FIXED_PRICE = "fixed_price"
    AUCTION = "auction"
    BUNDLE = "bundle"
    WTS = "want_to_sell"
    WTB = "want_to_buy"
    WTT = "want_to_trade"


class ListingStatus(Enum):
    """Lifecycle states for an item listing."""

    DRAFT = "draft"
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    RESERVED = "reserved"


class OfferStatus(Enum):
    """Lifecycle states for a trade offer."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    COUNTERED = "countered"
    EXPIRED = "expired"


class RarityTier(Enum):
    """Rarity classifications that influence listing perception and value."""

    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CurrencyType(Enum):
    """Currencies accepted by the trading post."""

    GOLD = "gold"
    GEMS = "gems"
    COINS = "coins"
    CREDITS = "credits"
    TOKENS = "tokens"
    RUNES = "runes"


class AuctionState(Enum):
    """Lifecycle states for an auction."""

    SCHEDULED = "scheduled"
    OPEN = "open"
    BIDDING_CLOSED = "bidding_closed"
    SETTLED = "settled"
    CANCELLED = "cancelled"


class TradingPostEventKind(Enum):
    """Audit event kinds emitted by the trading post system."""

    LISTING_CREATED = "listing_created"
    LISTING_UPDATED = "listing_updated"
    LISTING_CANCELLED = "listing_cancelled"
    LISTING_EXPIRED = "listing_expired"
    LISTING_SOLD = "listing_sold"
    OFFER_MADE = "offer_made"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    OFFER_COUNTERED = "offer_countered"
    OFFER_WITHDRAWN = "offer_withdrawn"
    AUCTION_STARTED = "auction_started"
    AUCTION_BID = "auction_bid"
    AUCTION_OUTBID = "auction_outbid"
    AUCTION_BUYOUT = "auction_buyout"
    AUCTION_SETTLED = "auction_settled"
    AUCTION_CANCELLED = "auction_cancelled"
    WALLET_CREATED = "wallet_created"
    WALLET_ADJUSTED = "wallet_adjusted"
    WALLET_SUSPENDED = "wallet_suspended"
    WALLET_REINSTATED = "wallet_reinstated"
    PRICE_RECORDED = "price_recorded"
    TRANSACTION_COMPLETED = "transaction_completed"
    SYSTEM_SEEDED = "system_seeded"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ItemListing:
    """A seller's published item offer on the trading post.

    Attributes:
        listing_id: Unique identifier for the listing.
        seller_id: The player offering the item.
        item_id: The catalog identifier of the item being sold.
        item_name: Human-readable name of the item.
        quantity: Number of units offered in this listing.
        listing_type: The ListingType commercial intent.
        price: Asking price in the listing currency.
        currency: The CurrencyType the price is denominated in.
        rarity: The RarityTier of the item.
        status: The current ListingStatus.
        created_at: ISO-8601 timestamp the listing was created.
        expires_at: ISO-8601 timestamp the listing expires.
        description: Free-form seller description.
        metadata: Free-form metadata bag.
    """

    listing_id: str = field(default_factory=lambda: _new_id("listing"))
    seller_id: str = ""
    item_id: str = ""
    item_name: str = ""
    quantity: int = 1
    listing_type: ListingType = ListingType.FIXED_PRICE
    price: float = 0.0
    currency: CurrencyType = CurrencyType.GOLD
    rarity: RarityTier = RarityTier.COMMON
    status: ListingStatus = ListingStatus.ACTIVE
    created_at: str = field(default_factory=_now)
    expires_at: str = field(default_factory=lambda: _iso_from_now(_DEFAULT_EXPIRY_HOURS))
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradeOffer:
    """A buyer's bid or counter-offer against an existing listing.

    Attributes:
        offer_id: Unique identifier for the offer.
        listing_id: The listing this offer targets.
        buyer_id: The player making the offer.
        offered_price: The price the buyer is willing to pay.
        offered_currency: The CurrencyType of the offered price.
        quantity: The number of units the offer covers.
        status: The current OfferStatus.
        message: Optional free-form message from the buyer.
        counter_price: A counter price proposed by the seller.
        created_at: ISO-8601 timestamp the offer was created.
        responded_at: ISO-8601 timestamp the seller responded.
    """

    offer_id: str = field(default_factory=lambda: _new_id("offer"))
    listing_id: str = ""
    buyer_id: str = ""
    offered_price: float = 0.0
    offered_currency: CurrencyType = CurrencyType.GOLD
    quantity: int = 1
    status: OfferStatus = OfferStatus.PENDING
    message: str = ""
    counter_price: Optional[float] = None
    created_at: str = field(default_factory=_now)
    responded_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Auction:
    """A timed, competitive bidding container tied to a listing.

    Attributes:
        auction_id: Unique identifier for the auction.
        listing_id: The listing this auction sells.
        starting_price: The minimum opening price.
        current_bid: The highest accepted bid so far.
        current_bidder: The player holding the highest bid.
        buyout_price: Optional instant-purchase price.
        min_increment: Minimum bid increment above the current bid.
        start_time: ISO-8601 timestamp the auction opened.
        end_time: ISO-8601 timestamp the auction closes.
        state: The current AuctionState.
        bid_count: Total number of bids placed.
        bids_history: Chronological log of all bids.
        winner_id: The winning bidder once settled.
        settled_at: ISO-8601 timestamp the auction was settled.
    """

    auction_id: str = field(default_factory=lambda: _new_id("auction"))
    listing_id: str = ""
    starting_price: float = 0.0
    current_bid: float = 0.0
    current_bidder: str = ""
    buyout_price: Optional[float] = None
    min_increment: float = _DEFAULT_MIN_INCREMENT
    start_time: str = field(default_factory=_now)
    end_time: str = field(default_factory=lambda: _iso_from_now(_DEFAULT_AUCTION_DURATION_HOURS))
    state: AuctionState = AuctionState.OPEN
    bid_count: int = 0
    bids_history: List[Dict[str, Any]] = field(default_factory=list)
    winner_id: str = ""
    settled_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Transaction:
    """A settled economic exchange recorded by the trading post.

    Attributes:
        transaction_id: Unique identifier for the transaction.
        listing_id: The listing that was exchanged.
        buyer_id: The purchasing player.
        seller_id: The selling player.
        item_id: The catalog identifier of the item exchanged.
        quantity: The number of units exchanged.
        final_price: The agreed price.
        currency: The CurrencyType of the final price.
        fee: Marketplace fee collected.
        tax: Tax collected.
        completed_at: ISO-8601 timestamp the transaction completed.
        type: A free-form label describing the transaction origin.
    """

    transaction_id: str = field(default_factory=lambda: _new_id("txn"))
    listing_id: str = ""
    buyer_id: str = ""
    seller_id: str = ""
    item_id: str = ""
    quantity: int = 1
    final_price: float = 0.0
    currency: CurrencyType = CurrencyType.GOLD
    fee: float = 0.0
    tax: float = 0.0
    completed_at: str = field(default_factory=_now)
    type: str = "sale"

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerWallet:
    """Per-player multi-currency wallet and reputation ledger.

    Attributes:
        player_id: The player this wallet belongs to.
        balances: Mapping of CurrencyType to current balance.
        total_transactions: Number of transactions the player has taken part in.
        total_spent: Lifetime amount spent (in the player's primary currency).
        total_earned: Lifetime amount earned (in the player's primary currency).
        reputation: A reputation score in [0.0, 100.0].
        is_suspended: Whether the wallet is currently suspended.
        created_at: ISO-8601 timestamp the wallet was created.
        updated_at: ISO-8601 timestamp the wallet was last updated.
    """

    player_id: str = ""
    balances: Dict[CurrencyType, float] = field(default_factory=dict)
    total_transactions: int = 0
    total_spent: float = 0.0
    total_earned: float = 0.0
    reputation: float = 50.0
    is_suspended: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PriceHistory:
    """Rolling observed-price ledger for a single item and currency.

    Attributes:
        item_id: The catalog identifier of the item.
        currency: The CurrencyType prices are denominated in.
        recent_prices: Chronological list of recently observed prices.
        avg_price: Average of the recent prices.
        min_price: Minimum of the recent prices.
        max_price: Maximum of the recent prices.
        trend: Direction of recent price movement (``up``/``down``/``flat``).
        last_updated: ISO-8601 timestamp of the most recent price update.
    """

    item_id: str = ""
    currency: CurrencyType = CurrencyType.GOLD
    recent_prices: List[float] = field(default_factory=list)
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    trend: str = "flat"
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingPostStats:
    """Aggregate counters describing the trading post system state.

    Attributes:
        total_listings: Number of listings ever created (still stored).
        active_listings: Number of listings currently ACTIVE.
        total_offers: Number of offers ever created (still stored).
        pending_offers: Number of offers currently PENDING.
        total_auctions: Number of auctions ever created (still stored).
        active_auctions: Number of auctions currently OPEN.
        total_transactions: Number of transactions recorded.
        total_volume: Sum of all transaction final prices.
        total_fees_collected: Sum of all fees and taxes collected.
        total_events: Number of audit events stored.
    """

    total_listings: int = 0
    active_listings: int = 0
    total_offers: int = 0
    pending_offers: int = 0
    total_auctions: int = 0
    active_auctions: int = 0
    total_transactions: int = 0
    total_volume: float = 0.0
    total_fees_collected: float = 0.0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingPostSnapshot:
    """An immutable snapshot of the entire trading post system state.

    Attributes:
        listings: Sample of current listings (as dicts).
        offers: Sample of current offers (as dicts).
        auctions: Sample of current auctions (as dicts).
        transactions: Sample of recent transactions (as dicts).
        stats: Aggregate statistics.
        timestamp: ISO-8601 timestamp the snapshot was taken.
    """

    listings: List[Dict[str, Any]] = field(default_factory=list)
    offers: List[Dict[str, Any]] = field(default_factory=list)
    auctions: List[Dict[str, Any]] = field(default_factory=list)
    transactions: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingPostEvent:
    """An audit event emitted by the trading post system.

    Attributes:
        event_id: Unique identifier for the event.
        kind: The TradingPostEventKind classification.
        timestamp: ISO-8601 timestamp when the event occurred.
        data: Event-specific payload data.
    """

    event_id: str = field(default_factory=lambda: _new_id("evt"))
    kind: TradingPostEventKind = TradingPostEventKind.LISTING_CREATED
    timestamp: str = field(default_factory=_now)
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Trading Post System (Singleton)
# ---------------------------------------------------------------------------


class TradingPostSystem:
    """Player-to-player trading and auction house orchestration engine.

    Manages item listings, trade offers, timed auctions, player wallets, and a
    price-history ledger. Implements the singleton pattern with double-checked
    locking for thread-safe access. All public methods are guarded by a
    re-entrant instance lock.
    """

    _instance: Optional["TradingPostSystem"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "TradingPostSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        with self._inner_lock:  # use _inner_lock; self._lock does not exist yet
            if self._initialized:
                return
            self._lock = threading.RLock()  # instance attribute set here
            # Primary stores keyed by their respective identifiers.
            self._listings: Dict[str, ItemListing] = {}
            self._offers: Dict[str, TradeOffer] = {}
            self._auctions: Dict[str, Auction] = {}
            self._transactions: Dict[str, Transaction] = {}
            self._wallets: Dict[str, PlayerWallet] = {}
            # Price history keyed by "{item_id}:{currency.value}".
            self._price_history: Dict[str, PriceHistory] = {}
            # Audit events kept in FIFO order with capacity eviction.
            self._events: List[TradingPostEvent] = []
            # Internal indexes for fast lookup / set semantics.
            self._suspended_players: Set[str] = set()
            self._offers_by_listing: Dict[str, List[str]] = {}
            self._auctions_by_listing: Dict[str, str] = {}
            # Running economic counters.
            self._total_volume: float = 0.0
            self._total_fees_collected: float = 0.0

            self._initialized = True
            self._seed_data()

    # ------------------------------------------------------------------
    # Event Helpers
    # ------------------------------------------------------------------

    def _emit(
        self, kind: TradingPostEventKind, data: Optional[Dict[str, Any]] = None
    ) -> TradingPostEvent:
        """Append an audit event to the in-memory event log."""
        event = TradingPostEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # ------------------------------------------------------------------
    # Internal Economic Helpers
    # ------------------------------------------------------------------

    def _ensure_wallet(self, player_id: str) -> PlayerWallet:
        """Return the wallet for ``player_id``, creating it with a starter grant if missing."""
        wallet = self._wallets.get(player_id)
        if wallet is not None:
            return wallet
        wallet = PlayerWallet(
            player_id=player_id,
            balances={
                CurrencyType.GOLD: _STARTER_GOLD,
                CurrencyType.GEMS: _STARTER_GEMS,
                CurrencyType.COINS: _STARTER_COINS,
                CurrencyType.CREDITS: _STARTER_CREDITS,
                CurrencyType.TOKENS: _STARTER_TOKENS,
                CurrencyType.RUNES: _STARTER_RUNES,
            },
        )
        self._wallets[player_id] = wallet
        _evict_fifo_dict(self._wallets, _MAX_WALLETS)
        self._emit(
            TradingPostEventKind.WALLET_CREATED,
            {"player_id": player_id, "starter_grant": True},
        )
        return wallet

    def _settle_transaction(
        self,
        listing: ItemListing,
        buyer_id: str,
        final_price: float,
        currency: CurrencyType,
        quantity: int,
        origin: str,
    ) -> Optional[Transaction]:
        """Record a settled transaction, move funds, and update the listing.

        Returns the new Transaction, or ``None`` if the buyer cannot afford
        the purchase or a wallet is suspended.
        """
        buyer_wallet = self._ensure_wallet(buyer_id)
        seller_wallet = self._ensure_wallet(listing.seller_id)
        if buyer_wallet.is_suspended or seller_wallet.is_suspended:
            return None
        if buyer_wallet.balances.get(currency, 0.0) < final_price:
            return None

        fee, tax, seller_proceeds = _compute_fees(final_price)
        # Debit the buyer and credit the seller.
        buyer_wallet.balances[currency] = round(
            buyer_wallet.balances.get(currency, 0.0) - final_price, 4
        )
        seller_wallet.balances[currency] = round(
            seller_wallet.balances.get(currency, 0.0) + seller_proceeds, 4
        )
        buyer_wallet.total_spent = round(buyer_wallet.total_spent + final_price, 4)
        buyer_wallet.total_transactions += 1
        seller_wallet.total_earned = round(seller_wallet.total_earned + seller_proceeds, 4)
        seller_wallet.total_transactions += 1
        buyer_wallet.updated_at = _now()
        seller_wallet.updated_at = _now()

        transaction = Transaction(
            transaction_id=_new_id("txn"),
            listing_id=listing.listing_id,
            buyer_id=buyer_id,
            seller_id=listing.seller_id,
            item_id=listing.item_id,
            quantity=quantity,
            final_price=round(final_price, 4),
            currency=currency,
            fee=fee,
            tax=tax,
            completed_at=_now(),
            type=origin,
        )
        self._transactions[transaction.transaction_id] = transaction
        _evict_fifo_dict(self._transactions, _MAX_TRANSACTIONS)
        self._total_volume = round(self._total_volume + final_price, 4)
        self._total_fees_collected = round(self._total_fees_collected + fee + tax, 4)

        listing.status = ListingStatus.SOLD
        self._record_price_internal(listing.item_id, currency, final_price)
        self._emit(
            TradingPostEventKind.TRANSACTION_COMPLETED,
            {
                "transaction_id": transaction.transaction_id,
                "listing_id": listing.listing_id,
                "buyer_id": buyer_id,
                "seller_id": listing.seller_id,
                "final_price": transaction.final_price,
                "currency": currency.value,
                "fee": fee,
                "tax": tax,
                "origin": origin,
            },
        )
        self._emit(
            TradingPostEventKind.LISTING_SOLD,
            {"listing_id": listing.listing_id, "transaction_id": transaction.transaction_id},
        )
        return transaction

    def _record_price_internal(
        self, item_id: str, currency: CurrencyType, price: float
    ) -> PriceHistory:
        """Update the rolling price-history ledger for an item and currency."""
        key = f"{item_id}:{currency.value}"
        history = self._price_history.get(key)
        if history is None:
            history = PriceHistory(item_id=item_id, currency=currency)
            self._price_history[key] = history
            _evict_fifo_dict(self._price_history, _MAX_PRICE_HISTORY)
        prices = history.recent_prices
        if prices:
            history.trend = "up" if price > prices[-1] else ("down" if price < prices[-1] else "flat")
        prices.append(round(float(price), 4))
        _evict_fifo_list(prices, _MAX_RECENT_PRICES)
        if prices:
            history.avg_price = round(sum(prices) / len(prices), 4)
            history.min_price = round(min(prices), 4)
            history.max_price = round(max(prices), 4)
        history.last_updated = _now()
        self._emit(
            TradingPostEventKind.PRICE_RECORDED,
            {"item_id": item_id, "currency": currency.value, "price": price},
        )
        return history

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Populate the engine with seed listings, offers, auctions, wallets, and prices."""
        # Seed wallets first so trades have funded participants.
        self._ensure_wallet("wallet_seed_1")
        self._ensure_wallet("wallet_seed_2")
        self._ensure_wallet("wallet_seed_3")

        # Seed listing 1: a fixed-price legendary sword.
        listing1 = ItemListing(
            listing_id="listing_seed_1",
            seller_id="wallet_seed_1",
            item_id="item_sword_of_dawn",
            item_name="Sword of Dawn",
            quantity=1,
            listing_type=ListingType.FIXED_PRICE,
            price=1500.0,
            currency=CurrencyType.GOLD,
            rarity=RarityTier.LEGENDARY,
            status=ListingStatus.ACTIVE,
            description="A legendary blade forged at the first sunrise.",
            metadata={"seed": True},
        )
        self._listings[listing1.listing_id] = listing1

        # Seed listing 2: a bundle of rare crafting reagents.
        listing2 = ItemListing(
            listing_id="listing_seed_2",
            seller_id="wallet_seed_2",
            item_id="item_ember_shards",
            item_name="Ember Shards",
            quantity=10,
            listing_type=ListingType.BUNDLE,
            price=320.0,
            currency=CurrencyType.GOLD,
            rarity=RarityTier.RARE,
            status=ListingStatus.ACTIVE,
            description="A bundle of ten rare ember shards for crafting.",
            metadata={"seed": True},
        )
        self._listings[listing2.listing_id] = listing2

        # Seed offer 1: a buyer underbids on the legendary sword.
        offer1 = TradeOffer(
            offer_id="offer_seed_1",
            listing_id=listing1.listing_id,
            buyer_id="wallet_seed_2",
            offered_price=1200.0,
            offered_currency=CurrencyType.GOLD,
            quantity=1,
            status=OfferStatus.PENDING,
            message="Would you take 1200 gold? I can pay immediately.",
            created_at=_now(),
        )
        self._offers[offer1.offer_id] = offer1
        self._offers_by_listing.setdefault(listing1.listing_id, []).append(offer1.offer_id)

        # Seed offer 2: a buyer offers gems for the sword (WTT-style).
        offer2 = TradeOffer(
            offer_id="offer_seed_2",
            listing_id=listing1.listing_id,
            buyer_id="wallet_seed_3",
            offered_price=80.0,
            offered_currency=CurrencyType.GEMS,
            quantity=1,
            status=OfferStatus.PENDING,
            message="Trade for 80 gems?",
            created_at=_now(),
        )
        self._offers[offer2.offer_id] = offer2
        self._offers_by_listing.setdefault(listing1.listing_id, []).append(offer2.offer_id)

        # Seed auction 1: an open auction on a mythic amulet listing.
        auction_listing = ItemListing(
            listing_id="listing_seed_auction_1",
            seller_id="wallet_seed_1",
            item_id="item_amulet_of_void",
            item_name="Amulet of the Void",
            quantity=1,
            listing_type=ListingType.AUCTION,
            price=2000.0,
            currency=CurrencyType.GOLD,
            rarity=RarityTier.MYTHIC,
            status=ListingStatus.ACTIVE,
            description="A mythic amulet pulsing with void energy.",
            metadata={"seed": True, "auction": True},
        )
        self._listings[auction_listing.listing_id] = auction_listing

        auction1 = Auction(
            auction_id="auction_seed_1",
            listing_id=auction_listing.listing_id,
            starting_price=1000.0,
            current_bid=1250.0,
            current_bidder="wallet_seed_2",
            buyout_price=3000.0,
            min_increment=50.0,
            start_time=_now(),
            end_time=_iso_from_now(48.0),
            state=AuctionState.OPEN,
            bid_count=2,
            bids_history=[
                {"bidder_id": "wallet_seed_3", "amount": 1100.0, "timestamp": _now()},
                {"bidder_id": "wallet_seed_2", "amount": 1250.0, "timestamp": _now()},
            ],
        )
        self._auctions[auction1.auction_id] = auction1
        self._auctions_by_listing[auction_listing.listing_id] = auction1.auction_id

        # Seed price history for the sword so market data exists out of the box.
        self._record_price_internal("item_sword_of_dawn", CurrencyType.GOLD, 1450.0)
        self._record_price_internal("item_sword_of_dawn", CurrencyType.GOLD, 1500.0)
        # Seed a dedicated price-history entry with the spec'd seed item id.
        # Stored under the standard "{item_id}:{currency}" key so it remains
        # queryable via get_price_history("price_seed_sword").
        seed_history = PriceHistory(
            item_id="price_seed_sword",
            currency=CurrencyType.GOLD,
            recent_prices=[1400.0, 1450.0, 1500.0],
            avg_price=1450.0,
            min_price=1400.0,
            max_price=1500.0,
            trend="up",
            last_updated=_now(),
        )
        self._price_history["price_seed_sword:gold"] = seed_history

        self._emit(
            TradingPostEventKind.SYSTEM_SEEDED,
            {
                "listings": 3,
                "offers": 2,
                "auctions": 1,
                "wallets": 3,
                "price_history": 2,
            },
        )

    # ------------------------------------------------------------------
    # Listing Management
    # ------------------------------------------------------------------

    def create_listing(
        self,
        seller_id: str,
        item_id: str,
        item_name: str,
        quantity: int,
        listing_type: ListingType,
        price: float,
        currency: CurrencyType,
        rarity: RarityTier = RarityTier.COMMON,
        description: str = "",
        expires_in_hours: int = _DEFAULT_EXPIRY_HOURS,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ItemListing]:
        """Create a new item listing on the trading post.

        Returns the new ItemListing, or ``None`` when arguments fail validation
        (empty seller/item, non-positive quantity or price).
        """
        with self._lock:
            if not seller_id or not item_id or not item_name:
                return None
            if quantity <= 0 or price < 0:
                return None
            listing = ItemListing(
                listing_id=_new_id("listing"),
                seller_id=seller_id,
                item_id=item_id,
                item_name=item_name,
                quantity=int(quantity),
                listing_type=listing_type,
                price=float(price),
                currency=currency,
                rarity=rarity,
                status=ListingStatus.ACTIVE,
                created_at=_now(),
                expires_at=_iso_from_now(expires_in_hours),
                description=description,
                metadata=metadata or {},
            )
            self._listings[listing.listing_id] = listing
            _evict_fifo_dict(self._listings, _MAX_LISTINGS)
            self._ensure_wallet(seller_id)
            self._emit(
                TradingPostEventKind.LISTING_CREATED,
                {
                    "listing_id": listing.listing_id,
                    "seller_id": seller_id,
                    "item_id": item_id,
                    "listing_type": listing_type.value,
                    "price": float(price),
                    "currency": currency.value,
                },
            )
            return listing

    def get_listing(self, listing_id: str) -> Optional[ItemListing]:
        """Return the listing with the given id, or ``None`` if not found."""
        with self._lock:
            return self._listings.get(listing_id)

    def list_listings(
        self,
        status: Optional[ListingStatus] = None,
        seller_id: Optional[str] = None,
        listing_type: Optional[ListingType] = None,
        limit: int = 100,
    ) -> List[ItemListing]:
        """List listings filtered by status, seller, and/or type."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_LISTINGS))
            results: List[ItemListing] = []
            for listing in self._listings.values():
                if status is not None and listing.status != status:
                    continue
                if seller_id is not None and listing.seller_id != seller_id:
                    continue
                if listing_type is not None and listing.listing_type != listing_type:
                    continue
                results.append(listing)
                if len(results) >= cap:
                    break
            return results

    def update_listing(
        self,
        listing_id: str,
        price: Optional[float] = None,
        description: Optional[str] = None,
        expires_in_hours: Optional[int] = None,
    ) -> Optional[ItemListing]:
        """Update mutable fields of a listing. Only ACTIVE listings can be updated."""
        with self._lock:
            listing = self._listings.get(listing_id)
            if listing is None:
                return None
            if listing.status != ListingStatus.ACTIVE:
                return None
            if price is not None and price >= 0:
                listing.price = float(price)
            if description is not None:
                listing.description = description
            if expires_in_hours is not None and expires_in_hours > 0:
                listing.expires_at = _iso_from_now(expires_in_hours)
            self._emit(
                TradingPostEventKind.LISTING_UPDATED,
                {"listing_id": listing_id, "price": price, "expires_in_hours": expires_in_hours},
            )
            return listing

    def cancel_listing(
        self, listing_id: str, reason: str = "user_cancelled"
    ) -> Optional[ItemListing]:
        """Cancel an active listing. Returns the updated listing, or ``None``."""
        with self._lock:
            listing = self._listings.get(listing_id)
            if listing is None:
                return None
            if listing.status not in (ListingStatus.ACTIVE, ListingStatus.RESERVED):
                return None
            listing.status = ListingStatus.CANCELLED
            # Cancel any pending offers on the listing as well.
            for offer_id in list(self._offers_by_listing.get(listing_id, [])):
                offer = self._offers.get(offer_id)
                if offer and offer.status == OfferStatus.PENDING:
                    offer.status = OfferStatus.EXPIRED
                    offer.responded_at = _now()
            # Cancel any associated open auction.
            auction_id = self._auctions_by_listing.get(listing_id)
            if auction_id:
                auction = self._auctions.get(auction_id)
                if auction and auction.state in (AuctionState.OPEN, AuctionState.SCHEDULED):
                    auction.state = AuctionState.CANCELLED
            self._emit(
                TradingPostEventKind.LISTING_CANCELLED,
                {"listing_id": listing_id, "reason": reason},
            )
            return listing

    # ------------------------------------------------------------------
    # Trade Offer Management
    # ------------------------------------------------------------------

    def make_offer(
        self,
        listing_id: str,
        buyer_id: str,
        offered_price: float,
        offered_currency: Optional[CurrencyType] = None,
        quantity: int = 1,
        message: str = "",
        counter_price: Optional[float] = None,
    ) -> Optional[TradeOffer]:
        """Create a trade offer against a listing.

        Returns the new TradeOffer, or ``None`` when the listing is missing,
        not active, or the buyer is the listing's seller.
        """
        with self._lock:
            listing = self._listings.get(listing_id)
            if listing is None or listing.status != ListingStatus.ACTIVE:
                return None
            if not buyer_id or buyer_id == listing.seller_id:
                return None
            if offered_price < 0 or quantity <= 0:
                return None
            currency = offered_currency if offered_currency is not None else listing.currency
            offer = TradeOffer(
                offer_id=_new_id("offer"),
                listing_id=listing_id,
                buyer_id=buyer_id,
                offered_price=float(offered_price),
                offered_currency=currency,
                quantity=int(quantity),
                status=OfferStatus.PENDING,
                message=message,
                counter_price=counter_price,
                created_at=_now(),
            )
            self._offers[offer.offer_id] = offer
            _evict_fifo_dict(self._offers, _MAX_OFFERS)
            self._offers_by_listing.setdefault(listing_id, []).append(offer.offer_id)
            self._ensure_wallet(buyer_id)
            self._emit(
                TradingPostEventKind.OFFER_MADE,
                {
                    "offer_id": offer.offer_id,
                    "listing_id": listing_id,
                    "buyer_id": buyer_id,
                    "offered_price": float(offered_price),
                    "offered_currency": currency.value,
                },
            )
            return offer

    def get_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Return the offer with the given id, or ``None`` if not found."""
        with self._lock:
            return self._offers.get(offer_id)

    def list_offers(
        self,
        listing_id: Optional[str] = None,
        buyer_id: Optional[str] = None,
        status: Optional[OfferStatus] = None,
        limit: int = 100,
    ) -> List[TradeOffer]:
        """List offers filtered by listing, buyer, and/or status."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_OFFERS))
            results: List[TradeOffer] = []
            for offer in self._offers.values():
                if listing_id is not None and offer.listing_id != listing_id:
                    continue
                if buyer_id is not None and offer.buyer_id != buyer_id:
                    continue
                if status is not None and offer.status != status:
                    continue
                results.append(offer)
                if len(results) >= cap:
                    break
            return results

    def accept_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Accept a pending offer, settling the transaction immediately.

        Returns the updated offer, or ``None`` when the offer or listing is
        missing, the offer is not pending, or the buyer cannot complete payment.
        """
        with self._lock:
            offer = self._offers.get(offer_id)
            if offer is None or offer.status != OfferStatus.PENDING:
                return None
            listing = self._listings.get(offer.listing_id)
            if listing is None or listing.status != ListingStatus.ACTIVE:
                return None
            transaction = self._settle_transaction(
                listing=listing,
                buyer_id=offer.buyer_id,
                final_price=offer.offered_price,
                currency=offer.offered_currency,
                quantity=min(offer.quantity, listing.quantity),
                origin="offer_accepted",
            )
            if transaction is None:
                return None
            offer.status = OfferStatus.ACCEPTED
            offer.responded_at = _now()
            # Reject the remaining pending offers on the same listing.
            for other_id in list(self._offers_by_listing.get(listing.listing_id, [])):
                other = self._offers.get(other_id)
                if other and other_id != offer_id and other.status == OfferStatus.PENDING:
                    other.status = OfferStatus.REJECTED
                    other.responded_at = _now()
            self._emit(
                TradingPostEventKind.OFFER_ACCEPTED,
                {"offer_id": offer_id, "transaction_id": transaction.transaction_id},
            )
            return offer

    def reject_offer(self, offer_id: str, reason: str = "") -> Optional[TradeOffer]:
        """Reject a pending offer. Returns the updated offer, or ``None``."""
        with self._lock:
            offer = self._offers.get(offer_id)
            if offer is None or offer.status != OfferStatus.PENDING:
                return None
            offer.status = OfferStatus.REJECTED
            offer.responded_at = _now()
            self._emit(
                TradingPostEventKind.OFFER_REJECTED,
                {"offer_id": offer_id, "reason": reason},
            )
            return offer

    def counter_offer(
        self, offer_id: str, counter_price: float
    ) -> Optional[TradeOffer]:
        """Counter a pending offer with a new price. Returns the updated offer."""
        with self._lock:
            offer = self._offers.get(offer_id)
            if offer is None or offer.status != OfferStatus.PENDING:
                return None
            if counter_price < 0:
                return None
            offer.counter_price = float(counter_price)
            offer.status = OfferStatus.COUNTERED
            offer.responded_at = _now()
            self._emit(
                TradingPostEventKind.OFFER_COUNTERED,
                {"offer_id": offer_id, "counter_price": float(counter_price)},
            )
            return offer

    def withdraw_offer(self, offer_id: str) -> Optional[TradeOffer]:
        """Withdraw a pending or countered offer. Returns the updated offer."""
        with self._lock:
            offer = self._offers.get(offer_id)
            if offer is None:
                return None
            if offer.status not in (OfferStatus.PENDING, OfferStatus.COUNTERED):
                return None
            offer.status = OfferStatus.WITHDRAWN
            offer.responded_at = _now()
            self._emit(
                TradingPostEventKind.OFFER_WITHDRAWN,
                {"offer_id": offer_id},
            )
            return offer

    # ------------------------------------------------------------------
    # Auction Management
    # ------------------------------------------------------------------

    def create_auction(
        self,
        listing_id: str,
        starting_price: float,
        duration_hours: int,
        buyout_price: Optional[float] = None,
        min_increment: float = _DEFAULT_MIN_INCREMENT,
    ) -> Optional[Auction]:
        """Create a new auction for an existing listing.

        The listing must be ACTIVE and not already attached to an auction.
        Returns the new Auction, or ``None`` on validation failure.
        """
        with self._lock:
            listing = self._listings.get(listing_id)
            if listing is None or listing.status != ListingStatus.ACTIVE:
                return None
            if listing_id in self._auctions_by_listing:
                return None
            if starting_price < 0 or duration_hours <= 0 or min_increment < 0:
                return None
            if buyout_price is not None and buyout_price < starting_price:
                return None
            listing.listing_type = ListingType.AUCTION
            auction = Auction(
                auction_id=_new_id("auction"),
                listing_id=listing_id,
                starting_price=float(starting_price),
                current_bid=float(starting_price),
                current_bidder="",
                buyout_price=float(buyout_price) if buyout_price is not None else None,
                min_increment=float(min_increment),
                start_time=_now(),
                end_time=_iso_from_now(duration_hours),
                state=AuctionState.OPEN,
            )
            self._auctions[auction.auction_id] = auction
            _evict_fifo_dict(self._auctions, _MAX_AUCTIONS)
            self._auctions_by_listing[listing_id] = auction.auction_id
            self._emit(
                TradingPostEventKind.AUCTION_STARTED,
                {
                    "auction_id": auction.auction_id,
                    "listing_id": listing_id,
                    "starting_price": float(starting_price),
                    "end_time": auction.end_time,
                },
            )
            return auction

    def get_auction(self, auction_id: str) -> Optional[Auction]:
        """Return the auction with the given id, or ``None`` if not found."""
        with self._lock:
            return self._auctions.get(auction_id)

    def list_auctions(
        self, state: Optional[AuctionState] = None, limit: int = 100
    ) -> List[Auction]:
        """List auctions filtered by state."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_AUCTIONS))
            results: List[Auction] = []
            for auction in self._auctions.values():
                if state is not None and auction.state != state:
                    continue
                results.append(auction)
                if len(results) >= cap:
                    break
            return results

    def place_bid(
        self, auction_id: str, bidder_id: str, bid_amount: float
    ) -> Optional[Auction]:
        """Place a bid on an open auction.

        The bid must exceed ``current_bid + min_increment``. If the bid meets or
        exceeds the buyout price, the auction is settled immediately. Returns the
        updated Auction, or ``None`` on validation failure.
        """
        with self._lock:
            auction = self._auctions.get(auction_id)
            if auction is None or auction.state != AuctionState.OPEN:
                return None
            listing = self._listings.get(auction.listing_id)
            if listing is None:
                return None
            if not bidder_id or bidder_id == listing.seller_id:
                return None
            required = auction.current_bid + auction.min_increment
            if bid_amount < required:
                return None
            # Outbid the previous high bidder.
            if auction.current_bidder and auction.current_bidder != bidder_id:
                self._emit(
                    TradingPostEventKind.AUCTION_OUTBID,
                    {
                        "auction_id": auction_id,
                        "outbid_player": auction.current_bidder,
                        "new_bidder": bidder_id,
                        "new_bid": float(bid_amount),
                    },
                )
            auction.current_bid = float(bid_amount)
            auction.current_bidder = bidder_id
            auction.bid_count += 1
            auction.bids_history.append(
                {"bidder_id": bidder_id, "amount": float(bid_amount), "timestamp": _now()}
            )
            self._emit(
                TradingPostEventKind.AUCTION_BID,
                {
                    "auction_id": auction_id,
                    "bidder_id": bidder_id,
                    "bid_amount": float(bid_amount),
                },
            )
            # Buyout: settle immediately when the buyout threshold is met.
            if auction.buyout_price is not None and bid_amount >= auction.buyout_price:
                self._emit(
                    TradingPostEventKind.AUCTION_BUYOUT,
                    {"auction_id": auction_id, "bidder_id": bidder_id, "amount": float(bid_amount)},
                )
                self._settle_auction_internal(auction, origin="auction_buyout")
            return auction

    def settle_auction(self, auction_id: str) -> Optional[Auction]:
        """Settle an open auction, recording the winning transaction.

        If no bids were placed, the auction is closed without a winner. Returns
        the updated Auction, or ``None`` if the auction is missing or not open.
        """
        with self._lock:
            auction = self._auctions.get(auction_id)
            if auction is None or auction.state != AuctionState.OPEN:
                return None
            self._settle_auction_internal(auction, origin="auction_settled")
            return auction

    def _settle_auction_internal(
        self, auction: Auction, origin: str
    ) -> Optional[Transaction]:
        """Internal helper that finalizes an auction and records the transaction."""
        listing = self._listings.get(auction.listing_id)
        if listing is None:
            auction.state = AuctionState.SETTLED
            auction.settled_at = _now()
            return None
        if not auction.current_bidder:
            # No bids: close the auction without a sale.
            auction.state = AuctionState.SETTLED
            auction.settled_at = _now()
            listing.status = ListingStatus.EXPIRED
            self._emit(
                TradingPostEventKind.AUCTION_SETTLED,
                {"auction_id": auction.auction_id, "winner_id": "", "settled": False},
            )
            return None
        transaction = self._settle_transaction(
            listing=listing,
            buyer_id=auction.current_bidder,
            final_price=auction.current_bid,
            currency=listing.currency,
            quantity=listing.quantity,
            origin=origin,
        )
        if transaction is None:
            auction.state = AuctionState.SETTLED
            auction.settled_at = _now()
            return None
        auction.state = AuctionState.SETTLED
        auction.winner_id = auction.current_bidder
        auction.settled_at = _now()
        self._emit(
            TradingPostEventKind.AUCTION_SETTLED,
            {
                "auction_id": auction.auction_id,
                "winner_id": auction.winner_id,
                "final_price": auction.current_bid,
                "transaction_id": transaction.transaction_id,
                "origin": origin,
            },
        )
        return transaction

    def cancel_auction(
        self, auction_id: str, reason: str = ""
    ) -> Optional[Auction]:
        """Cancel an open or scheduled auction. Returns the updated auction."""
        with self._lock:
            auction = self._auctions.get(auction_id)
            if auction is None:
                return None
            if auction.state not in (AuctionState.OPEN, AuctionState.SCHEDULED):
                return None
            auction.state = AuctionState.CANCELLED
            auction.settled_at = _now()
            listing = self._listings.get(auction.listing_id)
            if listing is not None and listing.status == ListingStatus.ACTIVE:
                listing.status = ListingStatus.CANCELLED
            self._emit(
                TradingPostEventKind.AUCTION_CANCELLED,
                {"auction_id": auction_id, "reason": reason},
            )
            return auction

    # ------------------------------------------------------------------
    # Wallet Management
    # ------------------------------------------------------------------

    def get_wallet(self, player_id: str) -> PlayerWallet:
        """Return the wallet for ``player_id``, creating one if it is missing."""
        with self._lock:
            return self._ensure_wallet(player_id)

    def adjust_balance(
        self, player_id: str, currency: CurrencyType, amount: float
    ) -> Optional[PlayerWallet]:
        """Adjust a player's balance in a currency by ``amount`` (may be negative).

        Returns the updated wallet, or ``None`` if the player is unknown here and
        the adjustment would be applied to a freshly suspended wallet.
        """
        with self._lock:
            if not player_id:
                return None
            wallet = self._ensure_wallet(player_id)
            if wallet.is_suspended:
                return None
            wallet.balances[currency] = round(
                wallet.balances.get(currency, 0.0) + float(amount), 4
            )
            wallet.updated_at = _now()
            self._emit(
                TradingPostEventKind.WALLET_ADJUSTED,
                {
                    "player_id": player_id,
                    "currency": currency.value,
                    "amount": float(amount),
                    "new_balance": wallet.balances[currency],
                },
            )
            return wallet

    def suspend_wallet(self, player_id: str, reason: str = "") -> Optional[PlayerWallet]:
        """Suspend a player's wallet, blocking further trade. Returns the wallet."""
        with self._lock:
            wallet = self._ensure_wallet(player_id)
            if wallet.is_suspended:
                return wallet
            wallet.is_suspended = True
            wallet.updated_at = _now()
            self._suspended_players.add(player_id)
            self._emit(
                TradingPostEventKind.WALLET_SUSPENDED,
                {"player_id": player_id, "reason": reason},
            )
            return wallet

    def reinstate_wallet(self, player_id: str) -> Optional[PlayerWallet]:
        """Reinstate a previously suspended wallet. Returns the wallet."""
        with self._lock:
            wallet = self._wallets.get(player_id)
            if wallet is None:
                return None
            wallet.is_suspended = False
            wallet.updated_at = _now()
            self._suspended_players.discard(player_id)
            self._emit(
                TradingPostEventKind.WALLET_REINSTATED,
                {"player_id": player_id},
            )
            return wallet

    # ------------------------------------------------------------------
    # Price History
    # ------------------------------------------------------------------

    def get_price_history(
        self, item_id: str, currency: CurrencyType = CurrencyType.GOLD
    ) -> PriceHistory:
        """Return the price history for an item/currency, creating an empty one if missing."""
        with self._lock:
            key = f"{item_id}:{currency.value}"
            history = self._price_history.get(key)
            if history is None:
                history = PriceHistory(item_id=item_id, currency=currency)
                self._price_history[key] = history
                _evict_fifo_dict(self._price_history, _MAX_PRICE_HISTORY)
            return history

    def record_price(
        self, item_id: str, currency: CurrencyType, price: float
    ) -> PriceHistory:
        """Record an observed price for an item/currency, updating aggregates."""
        with self._lock:
            return self._record_price_internal(item_id, currency, price)

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def get_transaction(self, transaction_id: str) -> Optional[Transaction]:
        """Return the transaction with the given id, or ``None`` if not found."""
        with self._lock:
            return self._transactions.get(transaction_id)

    def list_transactions(
        self,
        buyer_id: Optional[str] = None,
        seller_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Transaction]:
        """List transactions filtered by buyer and/or seller."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_TRANSACTIONS))
            results: List[Transaction] = []
            for transaction in self._transactions.values():
                if buyer_id is not None and transaction.buyer_id != buyer_id:
                    continue
                if seller_id is not None and transaction.seller_id != seller_id:
                    continue
                results.append(transaction)
                if len(results) >= cap:
                    break
            return results

    # ------------------------------------------------------------------
    # Events / Stats / Status / Snapshot / Reset
    # ------------------------------------------------------------------

    def list_events(
        self, limit: int = 100, kind: Optional[TradingPostEventKind] = None
    ) -> List[TradingPostEvent]:
        """List audit events, optionally filtered by event kind."""
        with self._lock:
            cap = max(1, min(int(limit), _MAX_EVENTS))
            results: List[TradingPostEvent] = []
            for event in self._events:
                if kind is not None and event.kind != kind:
                    continue
                results.append(event)
                if len(results) >= cap:
                    break
            return results

    def get_stats(self) -> TradingPostStats:
        """Compute and return aggregate statistics for the trading post."""
        with self._lock:
            active_listings = sum(
                1 for l in self._listings.values() if l.status == ListingStatus.ACTIVE
            )
            pending_offers = sum(
                1 for o in self._offers.values() if o.status == OfferStatus.PENDING
            )
            active_auctions = sum(
                1 for a in self._auctions.values() if a.state == AuctionState.OPEN
            )
            return TradingPostStats(
                total_listings=len(self._listings),
                active_listings=active_listings,
                total_offers=len(self._offers),
                pending_offers=pending_offers,
                total_auctions=len(self._auctions),
                active_auctions=active_auctions,
                total_transactions=len(self._transactions),
                total_volume=round(self._total_volume, 4),
                total_fees_collected=round(self._total_fees_collected, 4),
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        """Return a status dictionary describing the current system state."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "listings": len(self._listings),
                "offers": len(self._offers),
                "auctions": len(self._auctions),
                "transactions": len(self._transactions),
                "wallets": len(self._wallets),
                "price_history": len(self._price_history),
                "events": len(self._events),
                "suspended_players": len(self._suspended_players),
                "total_volume": round(self._total_volume, 4),
                "total_fees_collected": round(self._total_fees_collected, 4),
                "capacities": {
                    "max_listings": _MAX_LISTINGS,
                    "max_offers": _MAX_OFFERS,
                    "max_transactions": _MAX_TRANSACTIONS,
                    "max_auctions": _MAX_AUCTIONS,
                    "max_wallets": _MAX_WALLETS,
                    "max_price_history": _MAX_PRICE_HISTORY,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> TradingPostSnapshot:
        """Return an immutable snapshot of the entire system state."""
        with self._lock:
            stats = self.get_stats()
            return TradingPostSnapshot(
                listings=[l.to_dict() for l in list(self._listings.values())[:100]],
                offers=[o.to_dict() for o in list(self._offers.values())[:100]],
                auctions=[a.to_dict() for a in list(self._auctions.values())[:100]],
                transactions=[
                    t.to_dict() for t in list(self._transactions.values())[:100]
                ],
                stats=stats.to_dict(),
                timestamp=_now(),
            )

    def reset(self) -> None:
        """Clear all stores and re-seed the engine with default data."""
        with self._lock:
            self._listings.clear()
            self._offers.clear()
            self._auctions.clear()
            self._transactions.clear()
            self._wallets.clear()
            self._price_history.clear()
            self._events.clear()
            self._suspended_players.clear()
            self._offers_by_listing.clear()
            self._auctions_by_listing.clear()
            self._total_volume = 0.0
            self._total_fees_collected = 0.0
            self._emit(
                TradingPostEventKind.SYSTEM_RESET,
                {"reset_at": _now()},
            )
            self._seed_data()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_trading_post_system() -> TradingPostSystem:
    """Factory function returning the singleton TradingPostSystem instance."""
    return TradingPostSystem()
