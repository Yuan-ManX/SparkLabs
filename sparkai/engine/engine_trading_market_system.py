"""
SparkLabs Engine - Trading & Market System

Provides auction house listings, player shops, trade offers, buy/sell orders,
price history tracking, and market analytics. Designed as a self-contained
singleton system with seed data for immediate integration testing.
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

_LOCK = threading.RLock()


def _now() -> float:
    return time.time()


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:10]}"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


_MAX_LISTINGS = 2000
_MAX_ORDERS = 2000
_MAX_SHOPS = 500
_MAX_OFFERS = 1000
_MAX_PRICE_HISTORY = 5000


def _evict_fifo_list(items: List[Any], max_size: int) -> None:
    while len(items) > max_size:
        items.pop(0)


def _dataclass_to_dict(obj: Any) -> Any:
    if obj is None:
        return None
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for field_name in obj.__dataclass_fields__:
            val = getattr(obj, field_name)
            if hasattr(val, "to_dict") and callable(val.to_dict):
                result[field_name] = val.to_dict()
            elif isinstance(val, list):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, tuple):
                result[field_name] = [_dataclass_to_dict(item) for item in val]
            elif isinstance(val, dict):
                result[field_name] = {k: _dataclass_to_dict(v) for k, v in val.items()}
            else:
                result[field_name] = val
        return result
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, tuple):
        return [_dataclass_to_dict(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items()}
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ListingType(str, Enum):
    AUCTION = "auction"
    DIRECT_SALE = "direct_sale"


class ListingStatus(str, Enum):
    ACTIVE = "active"
    SOLD = "sold"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OrderType(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    FILLED = "filled"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class OfferStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class ShopStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"
    SUSPENDED = "suspended"


class PricePointType(str, Enum):
    LISTING = "listing"
    SALE = "sale"
    ORDER_FILL = "order_fill"


class TradingEventKind(str, Enum):
    LISTING_CREATED = "listing_created"
    LISTING_SOLD = "listing_sold"
    LISTING_CANCELLED = "listing_cancelled"
    LISTING_EXPIRED = "listing_expired"
    BID_PLACED = "bid_placed"
    ORDER_PLACED = "order_placed"
    ORDER_FILLED = "order_filled"
    ORDER_CANCELLED = "order_cancelled"
    OFFER_CREATED = "offer_created"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_REJECTED = "offer_rejected"
    SHOP_OPENED = "shop_opened"
    SHOP_CLOSED = "shop_closed"
    PRICE_RECORDED = "price_recorded"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class Bid:
    bid_id: str
    bidder_id: str
    bidder_name: str = ""
    amount: float = 0.0
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MarketListing:
    listing_id: str
    seller_id: str
    seller_name: str = ""
    item_id: str = ""
    item_name: str = ""
    item_quantity: int = 1
    listing_type: str = ListingType.DIRECT_SALE.value
    price: float = 100.0
    currency: str = "gold"
    buyout_price: float = 0.0
    status: str = ListingStatus.ACTIVE.value
    created_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    sold_at: float = 0.0
    buyer_id: str = ""
    buyer_name: str = ""
    bids: List[Bid] = field(default_factory=list)
    category: str = "misc"
    rarity: str = "common"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradeOrder:
    order_id: str
    trader_id: str
    trader_name: str = ""
    order_type: str = OrderType.BUY.value
    item_id: str = ""
    item_name: str = ""
    quantity: int = 1
    filled_quantity: int = 0
    price_per_unit: float = 100.0
    currency: str = "gold"
    status: str = OrderStatus.PENDING.value
    created_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    filled_at: float = 0.0
    total_cost: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradeOfferItem:
    item_id: str
    item_name: str = ""
    quantity: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradeOffer:
    offer_id: str
    offerer_id: str
    offerer_name: str = ""
    target_id: str = ""
    target_name: str = ""
    offered_items: List[TradeOfferItem] = field(default_factory=list)
    requested_items: List[TradeOfferItem] = field(default_factory=list)
    offered_gold: float = 0.0
    requested_gold: float = 0.0
    status: str = OfferStatus.PENDING.value
    created_at: float = field(default_factory=_now)
    expires_at: float = 0.0
    responded_at: float = 0.0
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ShopListing:
    listing_id: str
    item_id: str
    item_name: str = ""
    quantity: int = 1
    price: float = 100.0
    currency: str = "gold"
    category: str = "misc"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerShop:
    shop_id: str
    owner_id: str
    owner_name: str = ""
    name: str = ""
    description: str = ""
    status: str = ShopStatus.OPEN.value
    listings: List[ShopListing] = field(default_factory=list)
    total_sales: int = 0
    total_revenue: float = 0.0
    created_at: float = field(default_factory=_now)
    location: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PriceHistoryPoint:
    point_id: str
    item_id: str
    price_type: str = PricePointType.SALE.value
    price: float = 0.0
    quantity: int = 1
    timestamp: float = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MarketAnalytics:
    item_id: str = ""
    item_name: str = ""
    total_listings: int = 0
    total_sales: int = 0
    total_volume: float = 0.0
    avg_price: float = 0.0
    min_price: float = 0.0
    max_price: float = 0.0
    median_price: float = 0.0
    price_trend: str = "stable"
    last_sale_price: float = 0.0
    last_sale_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingConfig:
    max_listings: int = 2000
    max_orders: int = 2000
    max_shops: int = 500
    max_offers: int = 1000
    max_bids_per_listing: int = 50
    max_price_history: int = 5000
    listing_duration_seconds: float = 86400.0
    order_duration_seconds: float = 3600.0
    offer_duration_seconds: float = 1800.0
    tax_rate: float = 0.05
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingStats:
    total_listings: int = 0
    active_listings: int = 0
    sold_listings: int = 0
    total_orders: int = 0
    active_orders: int = 0
    filled_orders: int = 0
    total_shops: int = 0
    open_shops: int = 0
    total_offers: int = 0
    pending_offers: int = 0
    total_sales_volume: float = 0.0
    total_tax_collected: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingSnapshot:
    config: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    listings: List[Dict[str, Any]] = field(default_factory=list)
    orders: List[Dict[str, Any]] = field(default_factory=list)
    shops: List[Dict[str, Any]] = field(default_factory=list)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class TradingEvent:
    event_id: str
    kind: str
    timestamp: float
    listing_id: str = ""
    order_id: str = ""
    offer_id: str = ""
    shop_id: str = ""
    player_id: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

# ---------------------------------------------------------------------------
# Trading Market System
# ---------------------------------------------------------------------------

class TradingMarketSystem:
    """Manages auction house listings, player shops, trade orders, offers, and analytics."""

    _instance: Optional["TradingMarketSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._listings: Dict[str, MarketListing] = {}
        self._orders: Dict[str, TradeOrder] = {}
        self._offers: Dict[str, TradeOffer] = {}
        self._shops: Dict[str, PlayerShop] = {}
        self._price_history: List[PriceHistoryPoint] = []
        self._events: List[TradingEvent] = []
        self._stats = TradingStats()
        self._config = TradingConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._listing_counter: int = 0
        self._order_counter: int = 0
        self._offer_counter: int = 0
        self._shop_counter: int = 0
        self._bid_counter: int = 0
        self._price_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "TradingMarketSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed initial listings, orders, shops, and offers."""
        with self._init_lock:
            if self._initialized:
                return

            # Listings
            listing1 = MarketListing(
                listing_id="listing_starter_01",
                seller_id="player_starter",
                seller_name="StarterHero",
                item_id="item_flame_sword",
                item_name="Flame Sword of Fury",
                item_quantity=1,
                listing_type=ListingType.DIRECT_SALE.value,
                price=15000.0,
                currency="gold",
                status=ListingStatus.ACTIVE.value,
                expires_at=_now() + 86400,
                category="weapon",
                rarity="epic",
            )
            self._listings[listing1.listing_id] = listing1

            listing2 = MarketListing(
                listing_id="listing_starter_02",
                seller_id="player_mage",
                seller_name="ArcaneMind",
                item_id="item_mana_crystal",
                item_name="Brilliant Mana Crystal",
                item_quantity=50,
                listing_type=ListingType.DIRECT_SALE.value,
                price=5000.0,
                currency="gold",
                status=ListingStatus.ACTIVE.value,
                expires_at=_now() + 86400 * 3,
                category="material",
                rarity="rare",
            )
            self._listings[listing2.listing_id] = listing2

            listing3 = MarketListing(
                listing_id="listing_starter_03",
                seller_id="player_veteran",
                seller_name="VeteranGuard",
                item_id="item_dragon_helm",
                item_name="Ancient Dragon Helm",
                item_quantity=1,
                listing_type=ListingType.AUCTION.value,
                price=1000.0,
                buyout_price=50000.0,
                currency="gold",
                status=ListingStatus.ACTIVE.value,
                expires_at=_now() + 3600 * 12,
                category="armor",
                rarity="legendary",
                bids=[
                    Bid(
                        bid_id="bid_001",
                        bidder_id="player_warrior",
                        bidder_name="IronFist",
                        amount=1500.0,
                        timestamp=_now() - 3600,
                    ),
                    Bid(
                        bid_id="bid_002",
                        bidder_id="player_paladin",
                        bidder_name="HolyLight",
                        amount=2200.0,
                        timestamp=_now() - 1800,
                    ),
                ],
            )
            self._listings[listing3.listing_id] = listing3

            listing4 = MarketListing(
                listing_id="listing_starter_04",
                seller_id="player_crafter",
                seller_name="MasterForge",
                item_id="item_iron_ingot",
                item_name="Refined Iron Ingot",
                item_quantity=100,
                listing_type=ListingType.DIRECT_SALE.value,
                price=2000.0,
                currency="gold",
                status=ListingStatus.SOLD.value,
                sold_at=_now() - 3600 * 6,
                buyer_id="player_starter",
                buyer_name="StarterHero",
                category="material",
                rarity="common",
            )
            self._listings[listing4.listing_id] = listing4

            # Orders
            order1 = TradeOrder(
                order_id="order_starter_01",
                trader_id="player_starter",
                trader_name="StarterHero",
                order_type=OrderType.BUY.value,
                item_id="item_iron_ingot",
                item_name="Refined Iron Ingot",
                quantity=200,
                filled_quantity=50,
                price_per_unit=25.0,
                currency="gold",
                status=OrderStatus.PARTIAL.value,
                expires_at=_now() + 3600,
                total_cost=1250.0,
            )
            self._orders[order1.order_id] = order1

            order2 = TradeOrder(
                order_id="order_starter_02",
                trader_id="player_mage",
                trader_name="ArcaneMind",
                order_type=OrderType.SELL.value,
                item_id="item_mana_potion",
                item_name="Greater Mana Potion",
                quantity=100,
                filled_quantity=0,
                price_per_unit=50.0,
                currency="gold",
                status=OrderStatus.PENDING.value,
                expires_at=_now() + 3600 * 4,
            )
            self._orders[order2.order_id] = order2

            order3 = TradeOrder(
                order_id="order_starter_03",
                trader_id="player_veteran",
                trader_name="VeteranGuard",
                order_type=OrderType.BUY.value,
                item_id="item_dragon_scale",
                item_name="Dragon Scale",
                quantity=10,
                filled_quantity=10,
                price_per_unit=5000.0,
                currency="gold",
                status=OrderStatus.FILLED.value,
                filled_at=_now() - 3600 * 2,
                total_cost=50000.0,
            )
            self._orders[order3.order_id] = order3

            # Shops
            shop1 = PlayerShop(
                shop_id="shop_starter_01",
                owner_id="player_crafter",
                owner_name="MasterForge",
                name="Master Forge Emporium",
                description="Quality weapons and armor at fair prices.",
                status=ShopStatus.OPEN.value,
                total_sales=145,
                total_revenue=320000.0,
                created_at=_now() - 86400 * 20,
                location="market_district_a",
                listings=[
                    ShopListing(
                        listing_id="sl_001",
                        item_id="item_iron_sword",
                        item_name="Iron Sword",
                        quantity=5,
                        price=500.0,
                        category="weapon",
                    ),
                    ShopListing(
                        listing_id="sl_002",
                        item_id="item_steel_helm",
                        item_name="Steel Helm",
                        quantity=3,
                        price=800.0,
                        category="armor",
                    ),
                    ShopListing(
                        listing_id="sl_003",
                        item_id="item_iron_shield",
                        item_name="Iron Shield",
                        quantity=2,
                        price=1200.0,
                        category="armor",
                    ),
                ],
            )
            self._shops[shop1.shop_id] = shop1

            shop2 = PlayerShop(
                shop_id="shop_starter_02",
                owner_id="player_alchemist",
                owner_name="PotionBrewer",
                name="Alchemy Corner",
                description="Potions, elixirs, and scrolls.",
                status=ShopStatus.OPEN.value,
                total_sales=82,
                total_revenue=95000.0,
                created_at=_now() - 86400 * 10,
                location="market_district_b",
                listings=[
                    ShopListing(
                        listing_id="sl_004",
                        item_id="item_health_potion",
                        item_name="Health Potion",
                        quantity=50,
                        price=100.0,
                        category="consumable",
                    ),
                    ShopListing(
                        listing_id="sl_005",
                        item_id="item_mana_potion",
                        item_name="Mana Potion",
                        quantity=50,
                        price=120.0,
                        category="consumable",
                    ),
                ],
            )
            self._shops[shop2.shop_id] = shop2

            shop3 = PlayerShop(
                shop_id="shop_starter_03",
                owner_id="player_starter",
                owner_name="StarterHero",
                name="Starter's Bargain Bin",
                description="Selling loot from adventures.",
                status=ShopStatus.CLOSED.value,
                total_sales=12,
                total_revenue=8500.0,
                created_at=_now() - 86400 * 3,
            )
            self._shops[shop3.shop_id] = shop3

            # Trade Offers
            offer1 = TradeOffer(
                offer_id="offer_starter_01",
                offerer_id="player_warrior",
                offerer_name="IronFist",
                target_id="player_mage",
                target_name="ArcaneMind",
                offered_items=[
                    TradeOfferItem(item_id="item_iron_ingot", item_name="Iron Ingot", quantity=20),
                ],
                requested_items=[
                    TradeOfferItem(item_id="item_mana_potion", item_name="Mana Potion", quantity=10),
                ],
                offered_gold=500.0,
                status=OfferStatus.PENDING.value,
                expires_at=_now() + 1800,
                message="Want to trade iron for potions?",
            )
            self._offers[offer1.offer_id] = offer1

            offer2 = TradeOffer(
                offer_id="offer_starter_02",
                offerer_id="player_healer",
                offerer_name="LightTouch",
                target_id="player_starter",
                target_name="StarterHero",
                offered_items=[
                    TradeOfferItem(item_id="item_health_potion", item_name="Health Potion", quantity=30),
                ],
                requested_items=[
                    TradeOfferItem(item_id="item_gem_ruby", item_name="Ruby Gem", quantity=2),
                ],
                status=OfferStatus.ACCEPTED.value,
                responded_at=_now() - 3600,
            )
            self._offers[offer2.offer_id] = offer2

            # Price History
            self._price_history = [
                PriceHistoryPoint(
                    point_id="ph_001",
                    item_id="item_iron_ingot",
                    price_type=PricePointType.SALE.value,
                    price=22.0,
                    quantity=100,
                    timestamp=_now() - 86400,
                ),
                PriceHistoryPoint(
                    point_id="ph_002",
                    item_id="item_iron_ingot",
                    price_type=PricePointType.SALE.value,
                    price=25.0,
                    quantity=100,
                    timestamp=_now() - 3600 * 6,
                ),
                PriceHistoryPoint(
                    point_id="ph_003",
                    item_id="item_mana_potion",
                    price_type=PricePointType.SALE.value,
                    price=45.0,
                    quantity=50,
                    timestamp=_now() - 86400 * 2,
                ),
                PriceHistoryPoint(
                    point_id="ph_004",
                    item_id="item_mana_potion",
                    price_type=PricePointType.SALE.value,
                    price=50.0,
                    quantity=50,
                    timestamp=_now() - 3600 * 12,
                ),
                PriceHistoryPoint(
                    point_id="ph_005",
                    item_id="item_dragon_scale",
                    price_type=PricePointType.SALE.value,
                    price=5000.0,
                    quantity=10,
                    timestamp=_now() - 3600 * 2,
                ),
            ]

            self._refresh_stats()
            self._initialized = True

    def _refresh_stats(self) -> None:
        self._stats.total_listings = len(self._listings)
        self._stats.active_listings = sum(
            1 for l in self._listings.values() if l.status == ListingStatus.ACTIVE.value
        )
        self._stats.sold_listings = sum(
            1 for l in self._listings.values() if l.status == ListingStatus.SOLD.value
        )
        self._stats.total_orders = len(self._orders)
        self._stats.active_orders = sum(
            1 for o in self._orders.values()
            if o.status in (OrderStatus.PENDING.value, OrderStatus.PARTIAL.value)
        )
        self._stats.filled_orders = sum(
            1 for o in self._orders.values() if o.status == OrderStatus.FILLED.value
        )
        self._stats.total_shops = len(self._shops)
        self._stats.open_shops = sum(
            1 for s in self._shops.values() if s.status == ShopStatus.OPEN.value
        )
        self._stats.total_offers = len(self._offers)
        self._stats.pending_offers = sum(
            1 for o in self._offers.values() if o.status == OfferStatus.PENDING.value
        )
        self._stats.total_sales_volume = sum(
            l.price for l in self._listings.values() if l.status == ListingStatus.SOLD.value
        )

    def _record_event(
        self,
        kind: str,
        listing_id: str = "",
        order_id: str = "",
        offer_id: str = "",
        shop_id: str = "",
        player_id: str = "",
        description: str = "",
        details: Optional[Dict[str, Any]] = None,
    ) -> TradingEvent:
        event = TradingEvent(
            event_id=f"evt_{self._event_counter:06d}",
            kind=kind,
            timestamp=_now(),
            listing_id=listing_id,
            order_id=order_id,
            offer_id=offer_id,
            shop_id=shop_id,
            player_id=player_id,
            description=description,
            details=details or {},
        )
        self._event_counter += 1
        self._events.append(event)
        _evict_fifo_list(self._events, 2000)
        return event

    def _record_price(
        self,
        item_id: str,
        price: float,
        quantity: int = 1,
        price_type: str = PricePointType.SALE.value,
    ) -> PriceHistoryPoint:
        point = PriceHistoryPoint(
            point_id=f"ph_{self._price_counter:06d}",
            item_id=item_id,
            price_type=price_type,
            price=price,
            quantity=quantity,
        )
        self._price_counter += 1
        self._price_history.append(point)
        _evict_fifo_list(self._price_history, self._config.max_price_history)
        return point

    # ------------------------------------------------------------------
    # Listing management
    # ------------------------------------------------------------------

    def register_listing(
        self,
        listing_id: str,
        seller_id: str,
        seller_name: str = "",
        item_id: str = "",
        item_name: str = "",
        item_quantity: int = 1,
        listing_type: str = ListingType.DIRECT_SALE.value,
        price: float = 100.0,
        currency: str = "gold",
        buyout_price: float = 0.0,
        category: str = "misc",
        rarity: str = "common",
        duration_seconds: float = 86400.0,
    ) -> Tuple[bool, str, Optional[MarketListing]]:
        if listing_id in self._listings:
            return False, "exists", None
        if len(self._listings) >= _MAX_LISTINGS:
            return False, "capacity", None
        listing = MarketListing(
            listing_id=listing_id,
            seller_id=seller_id,
            seller_name=seller_name,
            item_id=item_id,
            item_name=item_name,
            item_quantity=item_quantity,
            listing_type=listing_type,
            price=price,
            currency=currency,
            buyout_price=buyout_price,
            category=category,
            rarity=rarity,
            expires_at=_now() + duration_seconds if duration_seconds > 0 else 0,
        )
        self._listings[listing_id] = listing
        self._record_price(item_id, price, item_quantity, PricePointType.LISTING.value)
        self._record_event(
            TradingEventKind.LISTING_CREATED.value,
            listing_id=listing_id,
            player_id=seller_id,
            description=f"Listing '{item_name}' created at {price} {currency}",
        )
        return True, "registered", listing

    def remove_listing(self, listing_id: str) -> Tuple[bool, str]:
        listing = self._listings.get(listing_id)
        if listing is None:
            return False, "not_found"
        if listing.status == ListingStatus.SOLD.value:
            return False, "already_sold"
        listing.status = ListingStatus.CANCELLED.value
        del self._listings[listing_id]
        self._record_event(
            TradingEventKind.LISTING_CANCELLED.value,
            listing_id=listing_id,
            description=f"Listing '{listing.item_name}' cancelled",
        )
        return True, "removed"

    def buy_listing(
        self, listing_id: str, buyer_id: str, buyer_name: str = ""
    ) -> Tuple[bool, str, Optional[MarketListing]]:
        listing = self._listings.get(listing_id)
        if listing is None:
            return False, "not_found", None
        if listing.status != ListingStatus.ACTIVE.value:
            return False, "not_active", None
        listing.status = ListingStatus.SOLD.value
        listing.sold_at = _now()
        listing.buyer_id = buyer_id
        listing.buyer_name = buyer_name
        tax = listing.price * self._config.tax_rate
        self._stats.total_tax_collected += tax
        self._record_price(
            listing.item_id, listing.price, listing.item_quantity, PricePointType.SALE.value
        )
        self._record_event(
            TradingEventKind.LISTING_SOLD.value,
            listing_id=listing_id,
            player_id=buyer_id,
            description=f"Listing '{listing.item_name}' sold to {buyer_name}",
            details={"price": listing.price, "tax": tax},
        )
        return True, "sold", listing

    def place_bid(
        self, listing_id: str, bidder_id: str, bidder_name: str = "", amount: float = 0.0
    ) -> Tuple[bool, str, Optional[Bid]]:
        listing = self._listings.get(listing_id)
        if listing is None:
            return False, "not_found", None
        if listing.listing_type != ListingType.AUCTION.value:
            return False, "not_auction", None
        if listing.status != ListingStatus.ACTIVE.value:
            return False, "not_active", None
        if amount <= 0:
            return False, "invalid_amount", None
        current_max = max([b.amount for b in listing.bids], default=listing.price)
        if amount <= current_max:
            return False, "bid_too_low", None
        if len(listing.bids) >= self._config.max_bids_per_listing:
            return False, "capacity", None
        bid = Bid(
            bid_id=f"bid_{self._bid_counter:06d}",
            bidder_id=bidder_id,
            bidder_name=bidder_name,
            amount=amount,
        )
        self._bid_counter += 1
        listing.bids.append(bid)
        self._record_event(
            TradingEventKind.BID_PLACED.value,
            listing_id=listing_id,
            player_id=bidder_id,
            description=f"Bid of {amount} placed by {bidder_name}",
        )
        return True, "bid_placed", bid

    def buyout_listing(
        self, listing_id: str, buyer_id: str, buyer_name: str = ""
    ) -> Tuple[bool, str, Optional[MarketListing]]:
        listing = self._listings.get(listing_id)
        if listing is None:
            return False, "not_found", None
        if listing.listing_type != ListingType.AUCTION.value:
            return False, "not_auction", None
        if listing.status != ListingStatus.ACTIVE.value:
            return False, "not_active", None
        if listing.buyout_price <= 0:
            return False, "no_buyout", None
        listing.status = ListingStatus.SOLD.value
        listing.sold_at = _now()
        listing.buyer_id = buyer_id
        listing.buyer_name = buyer_name
        listing.price = listing.buyout_price
        tax = listing.price * self._config.tax_rate
        self._stats.total_tax_collected += tax
        self._record_price(
            listing.item_id, listing.price, listing.item_quantity, PricePointType.SALE.value
        )
        self._record_event(
            TradingEventKind.LISTING_SOLD.value,
            listing_id=listing_id,
            player_id=buyer_id,
            description=f"Listing '{listing.item_name}' bought out by {buyer_name}",
        )
        return True, "bought_out", listing

    def get_listing(self, listing_id: str) -> Optional[MarketListing]:
        return self._listings.get(listing_id)

    def list_listings(
        self,
        status: str = "",
        category: str = "",
        seller_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[MarketListing]:
        listings = list(self._listings.values())
        if status:
            listings = [l for l in listings if l.status == status]
        if category:
            listings = [l for l in listings if l.category == category]
        if seller_id:
            listings = [l for l in listings if l.seller_id == seller_id]
        return listings[offset : offset + limit]

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------

    def place_order(
        self,
        order_id: str,
        trader_id: str,
        trader_name: str = "",
        order_type: str = OrderType.BUY.value,
        item_id: str = "",
        item_name: str = "",
        quantity: int = 1,
        price_per_unit: float = 100.0,
        currency: str = "gold",
        duration_seconds: float = 3600.0,
    ) -> Tuple[bool, str, Optional[TradeOrder]]:
        if order_id in self._orders:
            return False, "exists", None
        if len(self._orders) >= _MAX_ORDERS:
            return False, "capacity", None
        order = TradeOrder(
            order_id=order_id,
            trader_id=trader_id,
            trader_name=trader_name,
            order_type=order_type,
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            price_per_unit=price_per_unit,
            currency=currency,
            expires_at=_now() + duration_seconds if duration_seconds > 0 else 0,
        )
        self._orders[order_id] = order
        self._record_event(
            TradingEventKind.ORDER_PLACED.value,
            order_id=order_id,
            player_id=trader_id,
            description=f"{order_type} order for {quantity}x {item_name} at {price_per_unit}/ea",
        )
        return True, "placed", order

    def cancel_order(self, order_id: str) -> Tuple[bool, str, Optional[TradeOrder]]:
        order = self._orders.get(order_id)
        if order is None:
            return False, "not_found", None
        if order.status in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value):
            return False, "invalid_state", None
        order.status = OrderStatus.CANCELLED.value
        self._record_event(
            TradingEventKind.ORDER_CANCELLED.value,
            order_id=order_id,
            description=f"Order '{order_id}' cancelled",
        )
        return True, "cancelled", order

    def fill_order(
        self, order_id: str, fill_quantity: int = 0, filler_id: str = ""
    ) -> Tuple[bool, str, Optional[TradeOrder]]:
        order = self._orders.get(order_id)
        if order is None:
            return False, "not_found", None
        if order.status in (OrderStatus.FILLED.value, OrderStatus.CANCELLED.value, OrderStatus.EXPIRED.value):
            return False, "invalid_state", None
        fill_qty = fill_quantity if fill_quantity > 0 else order.quantity - order.filled_quantity
        remaining = order.quantity - order.filled_quantity
        if fill_qty > remaining:
            fill_qty = remaining
        order.filled_quantity += fill_qty
        fill_cost = fill_qty * order.price_per_unit
        order.total_cost += fill_cost
        if order.filled_quantity >= order.quantity:
            order.status = OrderStatus.FILLED.value
            order.filled_at = _now()
        else:
            order.status = OrderStatus.PARTIAL.value
        self._record_price(
            order.item_id, order.price_per_unit, fill_qty, PricePointType.ORDER_FILL.value
        )
        self._record_event(
            TradingEventKind.ORDER_FILLED.value,
            order_id=order_id,
            player_id=filler_id,
            description=f"Order filled {fill_qty}x at {order.price_per_unit}/ea",
            details={"fill_quantity": fill_qty, "fill_cost": fill_cost},
        )
        return True, "filled", order

    def get_order(self, order_id: str) -> Optional[TradeOrder]:
        return self._orders.get(order_id)

    def list_orders(
        self,
        status: str = "",
        order_type: str = "",
        item_id: str = "",
        trader_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[TradeOrder]:
        orders = list(self._orders.values())
        if status:
            orders = [o for o in orders if o.status == status]
        if order_type:
            orders = [o for o in orders if o.order_type == order_type]
        if item_id:
            orders = [o for o in orders if o.item_id == item_id]
        if trader_id:
            orders = [o for o in orders if o.trader_id == trader_id]
        return orders[offset : offset + limit]

    # ------------------------------------------------------------------
    # Offer management
    # ------------------------------------------------------------------

    def create_offer(
        self,
        offer_id: str,
        offerer_id: str,
        offerer_name: str = "",
        target_id: str = "",
        target_name: str = "",
        offered_gold: float = 0.0,
        requested_gold: float = 0.0,
        message: str = "",
        duration_seconds: float = 1800.0,
    ) -> Tuple[bool, str, Optional[TradeOffer]]:
        if offer_id in self._offers:
            return False, "exists", None
        if len(self._offers) >= _MAX_OFFERS:
            return False, "capacity", None
        offer = TradeOffer(
            offer_id=offer_id,
            offerer_id=offerer_id,
            offerer_name=offerer_name,
            target_id=target_id,
            target_name=target_name,
            offered_gold=offered_gold,
            requested_gold=requested_gold,
            message=message,
            expires_at=_now() + duration_seconds if duration_seconds > 0 else 0,
        )
        self._offers[offer_id] = offer
        self._record_event(
            TradingEventKind.OFFER_CREATED.value,
            offer_id=offer_id,
            player_id=offerer_id,
            description=f"Trade offer created to {target_name}",
        )
        return True, "created", offer

    def accept_offer(self, offer_id: str) -> Tuple[bool, str, Optional[TradeOffer]]:
        offer = self._offers.get(offer_id)
        if offer is None:
            return False, "not_found", None
        if offer.status != OfferStatus.PENDING.value:
            return False, "not_pending", None
        offer.status = OfferStatus.ACCEPTED.value
        offer.responded_at = _now()
        self._record_event(
            TradingEventKind.OFFER_ACCEPTED.value,
            offer_id=offer_id,
            description=f"Trade offer '{offer_id}' accepted",
        )
        return True, "accepted", offer

    def reject_offer(self, offer_id: str) -> Tuple[bool, str, Optional[TradeOffer]]:
        offer = self._offers.get(offer_id)
        if offer is None:
            return False, "not_found", None
        if offer.status != OfferStatus.PENDING.value:
            return False, "not_pending", None
        offer.status = OfferStatus.REJECTED.value
        offer.responded_at = _now()
        self._record_event(
            TradingEventKind.OFFER_REJECTED.value,
            offer_id=offer_id,
            description=f"Trade offer '{offer_id}' rejected",
        )
        return True, "rejected", offer

    def cancel_offer(self, offer_id: str) -> Tuple[bool, str, Optional[TradeOffer]]:
        offer = self._offers.get(offer_id)
        if offer is None:
            return False, "not_found", None
        if offer.status != OfferStatus.PENDING.value:
            return False, "not_pending", None
        offer.status = OfferStatus.CANCELLED.value
        offer.responded_at = _now()
        return True, "cancelled", offer

    def get_offer(self, offer_id: str) -> Optional[TradeOffer]:
        return self._offers.get(offer_id)

    def list_offers(
        self,
        status: str = "",
        offerer_id: str = "",
        target_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[TradeOffer]:
        offers = list(self._offers.values())
        if status:
            offers = [o for o in offers if o.status == status]
        if offerer_id:
            offers = [o for o in offers if o.offerer_id == offerer_id]
        if target_id:
            offers = [o for o in offers if o.target_id == target_id]
        return offers[offset : offset + limit]

    # ------------------------------------------------------------------
    # Shop management
    # ------------------------------------------------------------------

    def open_shop(
        self,
        shop_id: str,
        owner_id: str,
        owner_name: str = "",
        name: str = "",
        description: str = "",
        location: str = "",
    ) -> Tuple[bool, str, Optional[PlayerShop]]:
        if shop_id in self._shops:
            return False, "exists", None
        if len(self._shops) >= _MAX_SHOPS:
            return False, "capacity", None
        shop = PlayerShop(
            shop_id=shop_id,
            owner_id=owner_id,
            owner_name=owner_name,
            name=name,
            description=description,
            location=location,
            status=ShopStatus.OPEN.value,
        )
        self._shops[shop_id] = shop
        self._record_event(
            TradingEventKind.SHOP_OPENED.value,
            shop_id=shop_id,
            player_id=owner_id,
            description=f"Shop '{name}' opened",
        )
        return True, "opened", shop

    def close_shop(self, shop_id: str) -> Tuple[bool, str, Optional[PlayerShop]]:
        shop = self._shops.get(shop_id)
        if shop is None:
            return False, "not_found", None
        shop.status = ShopStatus.CLOSED.value
        self._record_event(
            TradingEventKind.SHOP_CLOSED.value,
            shop_id=shop_id,
            description=f"Shop '{shop.name}' closed",
        )
        return True, "closed", shop

    def remove_shop(self, shop_id: str) -> Tuple[bool, str]:
        shop = self._shops.get(shop_id)
        if shop is None:
            return False, "not_found"
        del self._shops[shop_id]
        return True, "removed"

    def add_shop_listing(
        self,
        shop_id: str,
        item_id: str,
        item_name: str = "",
        quantity: int = 1,
        price: float = 100.0,
        currency: str = "gold",
        category: str = "misc",
    ) -> Tuple[bool, str, Optional[ShopListing]]:
        shop = self._shops.get(shop_id)
        if shop is None:
            return False, "shop_not_found", None
        if shop.status != ShopStatus.OPEN.value:
            return False, "shop_closed", None
        listing = ShopListing(
            listing_id=f"sl_{self._listing_counter:06d}",
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            price=price,
            currency=currency,
            category=category,
        )
        self._listing_counter += 1
        shop.listings.append(listing)
        return True, "added", listing

    def buy_from_shop(
        self, shop_id: str, listing_id: str, buyer_id: str = "", quantity: int = 1
    ) -> Tuple[bool, str, Optional[ShopListing]]:
        shop = self._shops.get(shop_id)
        if shop is None:
            return False, "shop_not_found", None
        if shop.status != ShopStatus.OPEN.value:
            return False, "shop_closed", None
        listing = next((l for l in shop.listings if l.listing_id == listing_id), None)
        if listing is None:
            return False, "listing_not_found", None
        if listing.quantity < quantity:
            return False, "insufficient_stock", None
        listing.quantity -= quantity
        revenue = listing.price * quantity
        shop.total_sales += quantity
        shop.total_revenue += revenue
        tax = revenue * self._config.tax_rate
        self._stats.total_tax_collected += tax
        self._record_price(listing.item_id, listing.price, quantity, PricePointType.SALE.value)
        if listing.quantity <= 0:
            shop.listings.remove(listing)
        return True, "purchased", listing

    def get_shop(self, shop_id: str) -> Optional[PlayerShop]:
        return self._shops.get(shop_id)

    def list_shops(
        self,
        status: str = "",
        owner_id: str = "",
        limit: int = 50,
        offset: int = 0,
    ) -> List[PlayerShop]:
        shops = list(self._shops.values())
        if status:
            shops = [s for s in shops if s.status == status]
        if owner_id:
            shops = [s for s in shops if s.owner_id == owner_id]
        return shops[offset : offset + limit]

    # ------------------------------------------------------------------
    # Price history & analytics
    # ------------------------------------------------------------------

    def get_price_history(
        self, item_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[PriceHistoryPoint]:
        history = self._price_history
        if item_id:
            history = [p for p in history if p.item_id == item_id]
        return history[offset : offset + limit]

    def get_market_analytics(self, item_id: str) -> MarketAnalytics:
        points = [p for p in self._price_history if p.item_id == item_id]
        listings = [l for l in self._listings.values() if l.item_id == item_id]
        sales = [l for l in listings if l.status == ListingStatus.SOLD.value]
        if not points and not listings:
            return MarketAnalytics(item_id=item_id)
        prices = [p.price for p in points]
        if not prices:
            prices = [l.price for l in listings]
        avg_price = sum(prices) / len(prices) if prices else 0.0
        sorted_prices = sorted(prices)
        median = sorted_prices[len(sorted_prices) // 2] if sorted_prices else 0.0
        last_sale = max(
            (l for l in sales if l.sold_at > 0),
            default=None,
            key=lambda l: l.sold_at,
        )
        trend = "stable"
        if len(prices) >= 2:
            if prices[-1] > prices[0] * 1.05:
                trend = "rising"
            elif prices[-1] < prices[0] * 0.95:
                trend = "falling"
        return MarketAnalytics(
            item_id=item_id,
            item_name=listings[0].item_name if listings else "",
            total_listings=len(listings),
            total_sales=len(sales),
            total_volume=sum(l.price for l in sales),
            avg_price=avg_price,
            min_price=min(prices) if prices else 0.0,
            max_price=max(prices) if prices else 0.0,
            median_price=median,
            price_trend=trend,
            last_sale_price=last_sale.price if last_sale else 0.0,
            last_sale_at=last_sale.sold_at if last_sale else 0.0,
        )

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    def tick(self) -> Dict[str, Any]:
        self._tick_count += 1
        now = _now()
        for listing in self._listings.values():
            if (
                listing.status == ListingStatus.ACTIVE.value
                and listing.expires_at > 0
                and now > listing.expires_at
            ):
                listing.status = ListingStatus.EXPIRED.value
                self._record_event(
                    TradingEventKind.LISTING_EXPIRED.value,
                    listing_id=listing.listing_id,
                    description=f"Listing '{listing.item_name}' expired",
                )
        for order in self._orders.values():
            if (
                order.status in (OrderStatus.PENDING.value, OrderStatus.PARTIAL.value)
                and order.expires_at > 0
                and now > order.expires_at
            ):
                order.status = OrderStatus.EXPIRED.value
        for offer in self._offers.values():
            if (
                offer.status == OfferStatus.PENDING.value
                and offer.expires_at > 0
                and now > offer.expires_at
            ):
                offer.status = OfferStatus.EXPIRED.value
        self._refresh_stats()
        self._record_event(TradingEventKind.TICK.value, description=f"Tick #{self._tick_count}")
        return self.get_status()

    def set_config(self, config: Dict[str, Any]) -> TradingConfig:
        if "max_listings" in config:
            self._config.max_listings = _safe_int(config["max_listings"], self._config.max_listings)
        if "max_orders" in config:
            self._config.max_orders = _safe_int(config["max_orders"], self._config.max_orders)
        if "tax_rate" in config:
            self._config.tax_rate = _safe_float(config["tax_rate"], self._config.tax_rate)
        if "listing_duration_seconds" in config:
            self._config.listing_duration_seconds = _safe_float(
                config["listing_duration_seconds"], self._config.listing_duration_seconds
            )
        self._record_event(
            TradingEventKind.CONFIG_UPDATED.value,
            description="Configuration updated",
        )
        return self._config

    def get_config(self) -> TradingConfig:
        return self._config

    def list_events(
        self, listing_id: str = "", limit: int = 50, offset: int = 0
    ) -> List[TradingEvent]:
        events = self._events
        if listing_id:
            events = [e for e in events if e.listing_id == listing_id]
        return events[offset : offset + limit]

    def get_stats(self) -> TradingStats:
        self._refresh_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        self._refresh_stats()
        return {
            "initialized": self._initialized,
            "total_listings": len(self._listings),
            "active_listings": sum(
                1 for l in self._listings.values() if l.status == ListingStatus.ACTIVE.value
            ),
            "total_orders": len(self._orders),
            "active_orders": sum(
                1 for o in self._orders.values()
                if o.status in (OrderStatus.PENDING.value, OrderStatus.PARTIAL.value)
            ),
            "total_shops": len(self._shops),
            "open_shops": sum(
                1 for s in self._shops.values() if s.status == ShopStatus.OPEN.value
            ),
            "total_offers": len(self._offers),
            "pending_offers": sum(
                1 for o in self._offers.values() if o.status == OfferStatus.PENDING.value
            ),
            "price_history_points": len(self._price_history),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> TradingSnapshot:
        self._refresh_stats()
        return TradingSnapshot(
            config=self._config.to_dict(),
            stats=self._stats.to_dict(),
            listings=[l.to_dict() for l in list(self._listings.values())[:50]],
            orders=[o.to_dict() for o in list(self._orders.values())[:50]],
            shops=[s.to_dict() for s in list(self._shops.values())[:50]],
            tick_count=self._tick_count,
            timestamp=_now(),
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._listings.clear()
            self._orders.clear()
            self._offers.clear()
            self._shops.clear()
            self._price_history.clear()
            self._events.clear()
            self._stats = TradingStats()
            self._config = TradingConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._listing_counter = 0
            self._order_counter = 0
            self._offer_counter = 0
            self._shop_counter = 0
            self._bid_counter = 0
            self._price_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(
            TradingEventKind.RESET.value,
            description="System reset to seed state",
        )
        return self.get_status()


def get_trading_market_system() -> TradingMarketSystem:
    """Factory function to get the TradingMarketSystem singleton instance."""
    return TradingMarketSystem.get_instance()
