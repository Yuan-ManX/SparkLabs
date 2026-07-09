"""
SparkLabs Engine - Gacha System

A lottery-style reward acquisition system for the SparkLabs AI-native game
engine. Manages summon pools, rarity tiers, rate-up banners, pity mechanics,
pull history tracking, duplicate handling, and currency consumption.

Each gacha banner defines a pool of obtainable items with weighted drop
rates, optional rate-up entries, pity counter thresholds for guaranteed
high-rarity drops, and spark currency accumulation for exchange mechanics.
Designed for character summon gachas, weapon banners, cosmetic loot boxes,
and seasonal reward draws.

Architecture:
  GachaSystem (singleton)
    |-- BannerType, PullResult, RarityTier, GachaEventKind
    |-- GachaItem, RateUpEntry, PityState, GachaBanner,
       PullRecord, SparkExchange, GachaConfig, GachaStats,
       GachaSnapshot, GachaEvent
    |-- get_gacha_system

Core Capabilities:
  - register_banner / remove_banner / get_banner / list_banners: manage
    summon pool banners with item pools, rates, and pity rules.
  - activate_banner / deactivate_banner: control which banner is active.
  - pull / multi_pull: execute single or multi-pull draws with weighted
    random selection, pity enforcement, and rate-up adjustments.
  - get_pity / reset_pity: track and manage pity counters per banner.
  - get_pull_history: retrieve past pull records for a player.
  - register_spark_exchange / list_spark_exchanges / redeem_spark: manage
    spark currency accumulation and item exchange.
  - set_config / get_config: global tuning for max banners, pity limits,
    and spark accumulation rates.
  - tick: advance the simulation, handling banner rotation and timers.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GachaSystem.get_instance` or the module-level
:func:`get_gacha_system` factory.
"""

from __future__ import annotations

import math
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

_MAX_BANNERS: int = 100
_MAX_ITEMS_PER_BANNER: int = 500
_MAX_PULL_HISTORY: int = 10000
_MAX_SPARK_EXCHANGES: int = 200
_MAX_EVENTS: int = 5000


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

class BannerType(str, Enum):
    """Type of gacha banner."""
    CHARACTER = "character"
    WEAPON = "weapon"
    STANDARD = "standard"
    COSMETIC = "cosmetic"
    SEASONAL = "seasonal"
    LIMITED = "limited"
    NOVICE = "novice"


class RarityTier(str, Enum):
    """Rarity classification for gacha items."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class GachaEventKind(str, Enum):
    """Audit event types emitted by the gacha system."""
    BANNER_REGISTERED = "banner_registered"
    BANNER_REMOVED = "banner_removed"
    BANNER_ACTIVATED = "banner_activated"
    BANNER_DEACTIVATED = "banner_deactivated"
    PULL_EXECUTED = "pull_executed"
    MULTI_PULL_EXECUTED = "multi_pull_executed"
    PITY_TRIGGERED = "pity_triggered"
    SPARK_EARNED = "spark_earned"
    SPARK_REDEEMED = "spark_redeemed"
    DUPLICATE_CONVERTED = "duplicate_converted"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class GachaItem:
    """An item obtainable from a gacha banner."""
    item_id: str
    name: str = ""
    rarity: str = RarityTier.COMMON.value
    base_weight: float = 100.0
    is_rate_up: bool = False
    rate_up_weight: float = 0.0
    spark_value: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PityState:
    """Pity counter state for a player on a specific banner."""
    banner_id: str
    player_id: str
    soft_pity_count: int = 0
    hard_pity_count: int = 0
    guaranteed_featured: bool = False
    last_pull_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GachaBanner:
    """A summon pool banner with items, rates, and pity rules."""
    banner_id: str
    name: str = ""
    banner_type: str = BannerType.STANDARD.value
    description: str = ""
    items: List[GachaItem] = field(default_factory=list)
    featured_item_ids: List[str] = field(default_factory=list)
    active: bool = False
    cost_per_pull: int = 160
    currency_type: str = "premium_gem"
    soft_pity_threshold: int = 74
    hard_pity_threshold: int = 90
    soft_pity_bonus: float = 0.06
    featured_guarantee_pity: int = 180
    spark_per_pull: int = 1
    spark_exchange_id: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PullRecord:
    """Record of a single pull result."""
    pull_id: str
    banner_id: str
    player_id: str
    item_id: str
    item_name: str = ""
    rarity: str = RarityTier.COMMON.value
    is_duplicate: bool = False
    is_featured: bool = False
    spark_earned: int = 0
    pity_triggered: bool = False
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SparkExchange:
    """A spark currency exchange offer."""
    exchange_id: str
    banner_id: str
    name: str = ""
    target_item_id: str = ""
    target_item_name: str = ""
    spark_cost: int = 300
    available: bool = True
    max_redemptions: int = 1
    redemption_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GachaConfig:
    """Global tuning parameters for the gacha system."""
    max_banners: int = 50
    max_items_per_banner: int = 200
    max_pull_history: int = 5000
    default_soft_pity: int = 74
    default_hard_pity: int = 90
    default_soft_pity_bonus: float = 0.06
    default_featured_guarantee: int = 180
    default_spark_per_pull: int = 1
    enable_duplicate_conversion: bool = True
    tick_rate_hz: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GachaStats:
    """Aggregate statistics for the gacha system."""
    total_banners: int = 0
    active_banners: int = 0
    total_pulls: int = 0
    total_multi_pulls: int = 0
    total_spark_earned: int = 0
    total_spark_redeemed: int = 0
    total_duplicates: int = 0
    total_pity_triggers: int = 0
    rarity_counts: Dict[str, int] = field(default_factory=dict)
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GachaSnapshot:
    """Full state snapshot of the gacha system."""
    banners: List[Dict[str, Any]] = field(default_factory=list)
    spark_exchanges: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class GachaEvent:
    """An audit event emitted by the gacha system."""
    event_id: str
    kind: str
    timestamp: float
    banner_id: Optional[str] = None
    player_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Gacha System
# ---------------------------------------------------------------------------

class GachaSystem:
    """Manages gacha banners, pull mechanics, pity, and spark exchanges."""

    _instance: Optional["GachaSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._banners: Dict[str, GachaBanner] = {}
        self._pity_states: Dict[str, PityState] = {}
        self._pull_history: List[PullRecord] = []
        self._spark_balances: Dict[str, int] = {}
        self._spark_exchanges: Dict[str, SparkExchange] = {}
        self._events: List[GachaEvent] = []
        self._stats = GachaStats()
        self._config = GachaConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._pull_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "GachaSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed sample banners, items, and spark exchanges."""
        standard_items = [
            GachaItem(item_id="char_knight", name="Iron Knight", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_mage", name="Arcane Mage", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_archer", name="Forest Archer", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_priest", name="Dawn Priest", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_berserker", name="Blood Berserker", rarity=RarityTier.EPIC.value,
                      base_weight=20.0, spark_value=10),
            GachaItem(item_id="char_paladin", name="Holy Paladin", rarity=RarityTier.EPIC.value,
                      base_weight=20.0, spark_value=10),
            GachaItem(item_id="char_dragonlord", name="Dragon Lord", rarity=RarityTier.LEGENDARY.value,
                      base_weight=2.0, spark_value=50),
        ]
        standard_banner = GachaBanner(
            banner_id="banner_standard_01",
            name="Standard Summon",
            banner_type=BannerType.STANDARD.value,
            description="The permanent standard summon banner.",
            items=standard_items,
            active=True,
            cost_per_pull=160,
            currency_type="premium_gem",
        )
        self._banners[standard_banner.banner_id] = standard_banner

        featured_items = [
            GachaItem(item_id="char_frostqueen", name="Frost Queen", rarity=RarityTier.LEGENDARY.value,
                      base_weight=2.0, is_rate_up=True, rate_up_weight=10.0, spark_value=50),
            GachaItem(item_id="char_stormcaller", name="Stormcaller", rarity=RarityTier.EPIC.value,
                      base_weight=20.0, is_rate_up=True, rate_up_weight=40.0, spark_value=10),
            GachaItem(item_id="char_knight", name="Iron Knight", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_mage", name="Arcane Mage", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_archer", name="Forest Archer", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
            GachaItem(item_id="char_priest", name="Dawn Priest", rarity=RarityTier.RARE.value,
                      base_weight=100.0, spark_value=5),
        ]
        featured_banner = GachaBanner(
            banner_id="banner_frost_01",
            name="Frost Crown Banner",
            banner_type=BannerType.LIMITED.value,
            description="Limited-time banner featuring the Frost Queen.",
            items=featured_items,
            featured_item_ids=["char_frostqueen", "char_stormcaller"],
            active=False,
            cost_per_pull=160,
            currency_type="premium_gem",
            spark_exchange_id="exch_frost_01",
        )
        self._banners[featured_banner.banner_id] = featured_banner

        spark_exchange = SparkExchange(
            exchange_id="exch_frost_01",
            banner_id="banner_frost_01",
            name="Frost Queen Spark Exchange",
            target_item_id="char_frostqueen",
            target_item_name="Frost Queen",
            spark_cost=300,
        )
        self._spark_exchanges[spark_exchange.exchange_id] = spark_exchange

        self._stats.total_banners = len(self._banners)
        self._stats.active_banners = 1
        self._initialized = True

    # ------------------------------------------------------------------
    # Banner Management
    # ------------------------------------------------------------------

    def register_banner(self, banner: GachaBanner) -> Dict[str, Any]:
        if not banner.banner_id:
            banner.banner_id = f"banner_{_new_id()}"
        banner.created_at = _now()
        banner.updated_at = _now()
        if len(self._banners) >= _MAX_BANNERS:
            oldest = next(iter(self._banners), None)
            if oldest:
                self._banners.pop(oldest, None)
        self._banners[banner.banner_id] = banner
        self._stats.total_banners = len(self._banners)
        if banner.active:
            self._stats.active_banners += 1
        self._record_event(GachaEventKind.BANNER_REGISTERED, banner_id=banner.banner_id,
                           details={"name": banner.name, "type": banner.banner_type})
        return {"banner_id": banner.banner_id, "registered": True}

    def remove_banner(self, banner_id: str) -> Dict[str, Any]:
        banner = self._banners.pop(banner_id, None)
        if banner is None:
            return {"banner_id": banner_id, "removed": False}
        if banner.active:
            self._stats.active_banners = max(0, self._stats.active_banners - 1)
        self._stats.total_banners = len(self._banners)
        self._record_event(GachaEventKind.BANNER_REMOVED, banner_id=banner_id)
        return {"banner_id": banner_id, "removed": True}

    def get_banner(self, banner_id: str) -> Optional[GachaBanner]:
        return self._banners.get(banner_id)

    def list_banners(self, banner_type: Optional[str] = None, active: Optional[bool] = None,
                     limit: int = 100) -> List[GachaBanner]:
        result = []
        for b in self._banners.values():
            if banner_type is not None and b.banner_type != banner_type:
                continue
            if active is not None and b.active != active:
                continue
            result.append(b)
        return result[:limit]

    def activate_banner(self, banner_id: str) -> Dict[str, Any]:
        banner = self._banners.get(banner_id)
        if banner is None:
            return {"banner_id": banner_id, "activated": False, "reason": "not_found"}
        if not banner.active:
            banner.active = True
            banner.updated_at = _now()
            self._stats.active_banners += 1
        self._record_event(GachaEventKind.BANNER_ACTIVATED, banner_id=banner_id)
        return {"banner_id": banner_id, "activated": True}

    def deactivate_banner(self, banner_id: str) -> Dict[str, Any]:
        banner = self._banners.get(banner_id)
        if banner is None:
            return {"banner_id": banner_id, "deactivated": False, "reason": "not_found"}
        if banner.active:
            banner.active = False
            banner.updated_at = _now()
            self._stats.active_banners = max(0, self._stats.active_banners - 1)
        self._record_event(GachaEventKind.BANNER_DEACTIVATED, banner_id=banner_id)
        return {"banner_id": banner_id, "deactivated": True}

    # ------------------------------------------------------------------
    # Pull Mechanics
    # ------------------------------------------------------------------

    def _get_pity_state(self, banner_id: str, player_id: str) -> PityState:
        key = f"{banner_id}:{player_id}"
        state = self._pity_states.get(key)
        if state is None:
            state = PityState(banner_id=banner_id, player_id=player_id)
            self._pity_states[key] = state
        return state

    def _select_item(self, banner: GachaBanner, pity: PityState) -> Tuple[GachaItem, bool]:
        """Select an item from the banner using weighted random with pity adjustments."""
        items = [it for it in banner.items if it.base_weight > 0]
        if not items:
            return GachaItem(item_id="fallback", name="Fallback", rarity=RarityTier.COMMON.value), False

        soft_pity_active = pity.soft_pity_count >= banner.soft_pity_threshold
        hard_pity_active = pity.hard_pity_count >= banner.hard_pity_threshold - 1

        weights = []
        for it in items:
            w = it.base_weight
            if it.is_rate_up and it.rate_up_weight > 0:
                w = it.rate_up_weight
            if soft_pity_active and it.rarity in (RarityTier.LEGENDARY.value, RarityTier.EPIC.value):
                w *= (1.0 + banner.soft_pity_bonus * max(0, pity.soft_pity_count - banner.soft_pity_threshold + 1))
            weights.append(w)

        if hard_pity_active:
            legendary_items = [(i, it) for i, it in enumerate(items)
                               if it.rarity in (RarityTier.LEGENDARY.value, RarityTier.MYTHIC.value)]
            if legendary_items:
                total_w = sum(weights[i] for i, _ in legendary_items)
                if total_w > 0:
                    r = random.random() * total_w
                    cumulative = 0.0
                    for i, it in legendary_items:
                        cumulative += weights[i]
                        if r <= cumulative:
                            return it, True

        total_w = sum(weights)
        if total_w <= 0:
            return items[0], False
        r = random.random() * total_w
        cumulative = 0.0
        for i, it in enumerate(items):
            cumulative += weights[i]
            if r <= cumulative:
                pity_triggered = hard_pity_active and it.rarity in (RarityTier.LEGENDARY.value, RarityTier.MYTHIC.value)
                return it, pity_triggered
        return items[-1], False

    def pull(self, banner_id: str, player_id: str, owned_items: Optional[List[str]] = None) -> Dict[str, Any]:
        banner = self._banners.get(banner_id)
        if banner is None:
            return {"success": False, "reason": "banner_not_found"}
        if not banner.active:
            return {"success": False, "reason": "banner_inactive"}

        pity = self._get_pity_state(banner_id, player_id)
        item, pity_triggered = self._select_item(banner, pity)

        owned_set = set(owned_items) if owned_items else set()
        is_duplicate = item.item_id in owned_set
        is_featured = item.item_id in banner.featured_item_ids

        spark_earned = 0
        if is_duplicate and self._config.enable_duplicate_conversion:
            spark_earned = item.spark_value
        elif banner.spark_per_pull > 0:
            spark_earned = banner.spark_per_pull

        if spark_earned > 0:
            self._spark_balances[player_id] = self._spark_balances.get(player_id, 0) + spark_earned
            self._stats.total_spark_earned += spark_earned

        pity.soft_pity_count += 1
        pity.hard_pity_count += 1
        pity.last_pull_time = _now()

        pity_reset = False
        if item.rarity in (RarityTier.LEGENDARY.value, RarityTier.MYTHIC.value):
            pity.soft_pity_count = 0
            pity.hard_pity_count = 0
            pity_reset = True

        if is_featured and pity.guaranteed_featured:
            pity.guaranteed_featured = False
        elif item.rarity in (RarityTier.LEGENDARY.value, RarityTier.MYTHIC.value) and not is_featured:
            pity.guaranteed_featured = True

        pull_id = f"pull_{self._pull_counter}"
        self._pull_counter += 1
        record = PullRecord(
            pull_id=pull_id,
            banner_id=banner_id,
            player_id=player_id,
            item_id=item.item_id,
            item_name=item.name,
            rarity=item.rarity,
            is_duplicate=is_duplicate,
            is_featured=is_featured,
            spark_earned=spark_earned,
            pity_triggered=pity_triggered,
        )
        self._pull_history.append(record)
        _evict_fifo_list(self._pull_history, _MAX_PULL_HISTORY)

        self._stats.total_pulls += 1
        self._stats.rarity_counts[item.rarity] = self._stats.rarity_counts.get(item.rarity, 0) + 1
        if is_duplicate:
            self._stats.total_duplicates += 1
        if pity_triggered:
            self._stats.total_pity_triggers += 1

        self._record_event(GachaEventKind.PULL_EXECUTED, banner_id=banner_id, player_id=player_id,
                           details={"pull_id": pull_id, "item_id": item.item_id, "rarity": item.rarity,
                                     "pity_triggered": pity_triggered, "pity_reset": pity_reset})
        return {
            "success": True,
            "pull_id": pull_id,
            "item_id": item.item_id,
            "item_name": item.name,
            "rarity": item.rarity,
            "is_duplicate": is_duplicate,
            "is_featured": is_featured,
            "spark_earned": spark_earned,
            "pity_triggered": pity_triggered,
            "pity_reset": pity_reset,
        }

    def multi_pull(self, banner_id: str, player_id: str, count: int = 10,
                   owned_items: Optional[List[str]] = None) -> Dict[str, Any]:
        banner = self._banners.get(banner_id)
        if banner is None:
            return {"success": False, "reason": "banner_not_found"}
        if not banner.active:
            return {"success": False, "reason": "banner_inactive"}

        count = max(1, min(count, 100))
        results = []
        for _ in range(count):
            r = self.pull(banner_id, player_id, owned_items)
            if r.get("success"):
                results.append(r)
                if owned_items is not None and r.get("item_id"):
                    owned_items.append(r["item_id"])
            else:
                break

        self._stats.total_multi_pulls += 1
        self._record_event(GachaEventKind.MULTI_PULL_EXECUTED, banner_id=banner_id, player_id=player_id,
                           details={"count": len(results)})
        return {"success": len(results) > 0, "count": len(results), "results": results}

    # ------------------------------------------------------------------
    # Pity Management
    # ------------------------------------------------------------------

    def get_pity(self, banner_id: str, player_id: str) -> Dict[str, Any]:
        pity = self._get_pity_state(banner_id, player_id)
        return pity.to_dict()

    def reset_pity(self, banner_id: str, player_id: str) -> Dict[str, Any]:
        key = f"{banner_id}:{player_id}"
        if key in self._pity_states:
            self._pity_states[key].soft_pity_count = 0
            self._pity_states[key].hard_pity_count = 0
            self._pity_states[key].guaranteed_featured = False
        return {"banner_id": banner_id, "player_id": player_id, "reset": True}

    # ------------------------------------------------------------------
    # Pull History
    # ------------------------------------------------------------------

    def get_pull_history(self, player_id: Optional[str] = None, banner_id: Optional[str] = None,
                         limit: int = 100) -> List[PullRecord]:
        result = []
        for r in reversed(self._pull_history):
            if player_id is not None and r.player_id != player_id:
                continue
            if banner_id is not None and r.banner_id != banner_id:
                continue
            result.append(r)
            if len(result) >= limit:
                break
        return result

    # ------------------------------------------------------------------
    # Spark Exchange
    # ------------------------------------------------------------------

    def register_spark_exchange(self, exchange: SparkExchange) -> Dict[str, Any]:
        if not exchange.exchange_id:
            exchange.exchange_id = f"exch_{_new_id()}"
        if len(self._spark_exchanges) >= _MAX_SPARK_EXCHANGES:
            oldest = next(iter(self._spark_exchanges), None)
            if oldest:
                self._spark_exchanges.pop(oldest, None)
        self._spark_exchanges[exchange.exchange_id] = exchange
        self._record_event(GachaEventKind.SPARK_EARNED, banner_id=exchange.banner_id,
                           details={"exchange_id": exchange.exchange_id})
        return {"exchange_id": exchange.exchange_id, "registered": True}

    def list_spark_exchanges(self, banner_id: Optional[str] = None, limit: int = 100) -> List[SparkExchange]:
        result = []
        for e in self._spark_exchanges.values():
            if banner_id is not None and e.banner_id != banner_id:
                continue
            result.append(e)
        return result[:limit]

    def get_spark_balance(self, player_id: str) -> Dict[str, Any]:
        return {"player_id": player_id, "spark_balance": self._spark_balances.get(player_id, 0)}

    def redeem_spark(self, exchange_id: str, player_id: str) -> Dict[str, Any]:
        exchange = self._spark_exchanges.get(exchange_id)
        if exchange is None:
            return {"success": False, "reason": "exchange_not_found"}
        if not exchange.available:
            return {"success": False, "reason": "exchange_unavailable"}
        if exchange.redemption_count >= exchange.max_redemptions:
            return {"success": False, "reason": "max_redemptions_reached"}

        balance = self._spark_balances.get(player_id, 0)
        if balance < exchange.spark_cost:
            return {"success": False, "reason": "insufficient_spark", "balance": balance, "cost": exchange.spark_cost}

        self._spark_balances[player_id] = balance - exchange.spark_cost
        exchange.redemption_count += 1
        if exchange.redemption_count >= exchange.max_redemptions:
            exchange.available = False
        self._stats.total_spark_redeemed += exchange.spark_cost

        self._record_event(GachaEventKind.SPARK_REDEEMED, banner_id=exchange.banner_id, player_id=player_id,
                           details={"exchange_id": exchange_id, "target_item_id": exchange.target_item_id,
                                     "spark_cost": exchange.spark_cost})
        return {
            "success": True,
            "exchange_id": exchange_id,
            "target_item_id": exchange.target_item_id,
            "target_item_name": exchange.target_item_name,
            "spark_remaining": self._spark_balances[player_id],
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        current_time = _now()
        expired = []
        for banner_id, banner in self._banners.items():
            if banner.active and banner.end_time > 0 and current_time > banner.end_time:
                banner.active = False
                self._stats.active_banners = max(0, self._stats.active_banners - 1)
                expired.append(banner_id)
        if expired:
            self._record_event(GachaEventKind.TICK, details={"expired_banners": expired})
        return {"tick_count": self._tick_count, "expired_banners": expired}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> GachaConfig:
        return self._config

    def set_config(self, config: GachaConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(GachaEventKind.CONFIG_UPDATED)
        return {"updated": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _record_event(self, kind: GachaEventKind, banner_id: Optional[str] = None,
                      player_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        event_id = f"evt_{self._event_counter}"
        self._event_counter += 1
        event = GachaEvent(
            event_id=event_id,
            kind=kind.value,
            timestamp=_now(),
            banner_id=banner_id,
            player_id=player_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, banner_id: Optional[str] = None, player_id: Optional[str] = None,
                    kind: Optional[str] = None, limit: int = 100) -> List[GachaEvent]:
        result = []
        for e in reversed(self._events):
            if banner_id is not None and e.banner_id != banner_id:
                continue
            if player_id is not None and e.player_id != player_id:
                continue
            if kind is not None and e.kind != kind:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> GachaStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_banners": len(self._banners),
            "active_banners": self._stats.active_banners,
            "total_pulls": self._stats.total_pulls,
            "total_spark_earned": self._stats.total_spark_earned,
            "total_spark_redeemed": self._stats.total_spark_redeemed,
            "total_exchanges": len(self._spark_exchanges),
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> GachaSnapshot:
        return GachaSnapshot(
            banners=[b.to_dict() for b in self._banners.values()],
            spark_exchanges=[e.to_dict() for e in self._spark_exchanges.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._banners.clear()
            self._pity_states.clear()
            self._pull_history.clear()
            self._spark_balances.clear()
            self._spark_exchanges.clear()
            self._events.clear()
            self._stats = GachaStats()
            self._config = GachaConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._pull_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(GachaEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_gacha_system() -> GachaSystem:
    return GachaSystem.get_instance()
