"""
SparkLabs Engine - UGC Workshop System

A comprehensive user-generated content workshop that empowers players to create,
upload, review, rate, subscribe to, and share game content. The system provides
a complete content lifecycle pipeline from draft creation through moderation,
publication, discovery, and monetization.

Architecture:
  UGCWorkshopSystem (Singleton)
    |-- UGCItem — content entries with type, status, monetization, and stats
    |-- ItemReview — moderation reviews with verdicts and reviewer notes
    |-- ItemRating — player ratings with helpfulness voting
    |-- ItemSubscription — player subscriptions with auto-update tracking
    |-- ItemCollection — curated collections of items
    |-- ItemReport — player-submitted reports for moderation
    |-- MonetizationSplit — revenue distribution between authors and platform

Core Capabilities:
  - register_item / get_item / list_items / update_item / remove_item: full
    item lifecycle management with type, status, and author filtering.
  - submit_for_review / start_review / complete_review / approve_item /
    reject_item / request_revision: moderation pipeline with verdict tracking.
  - rate_item / get_rating / list_ratings / remove_rating: player rating system
    with helpfulness counting.
  - subscribe / unsubscribe / get_subscription / list_subscriptions:
    subscription management with auto-update preferences.
  - create_collection / get_collection / list_collections / add_to_collection /
    remove_from_collection / remove_collection: curated item collections.
  - report_item / resolve_report / list_reports / get_report: player reporting
    and moderation resolution.
  - set_monetization / get_monetization / process_revenue: monetization splits
    and revenue processing.
  - feature_item / unfeature_item / get_featured / discover_items: discovery
    and featuring with multiple sort modes.
  - get_status / get_stats / get_snapshot / get_config / set_config / tick /
    reset / list_events: observability, tuning, and lifecycle control.
"""

from __future__ import annotations

import math
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_ITEMS: int = 50000
_MAX_REVIEWS: int = 20000
_MAX_RATINGS: int = 100000
_MAX_SUBSCRIPTIONS: int = 100000
_MAX_COLLECTIONS: int = 10000
_MAX_REPORTS: int = 20000
_MAX_SPLITS: int = 20000
_MAX_EVENTS: int = 20000
_MAX_ITEMS_PER_COLLECTION: int = 500
_MAX_RATINGS_PER_ITEM: int = 5000

# Rating bounds
_RATING_MIN: float = 0.0
_RATING_MAX: float = 5.0

# Revenue share bounds
_SHARE_MIN: float = 0.0
_SHARE_MAX: float = 1.0

# Discovery limits
_DEFAULT_DISCOVERY_LIMIT: int = 50
_MAX_DISCOVERY_LIMIT: int = 200


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _mean(values: List[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _parse_iso(ts: str) -> Optional[datetime]:
    if not ts:
        return None
    try:
        cleaned = ts.rstrip("Z")
        return datetime.fromisoformat(cleaned)
    except (ValueError, TypeError):
        return None


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------

class UGCItemType(str, Enum):
    """Categories of user-generated content."""
    MAP = "map"
    MOD = "mod"
    SKIN = "skin"
    MODEL = "model"
    SCENARIO = "scenario"
    SCRIPT = "script"
    MUSIC = "music"
    SOUND_FX = "sound_fx"
    PARTICLE_EFFECT = "particle_effect"
    UI_THEME = "ui_theme"
    PREFAB = "prefab"
    COLLECTION = "collection"
    PLUGIN = "plugin"
    CONFIG = "config"


class UGCItemStatus(str, Enum):
    """Lifecycle states of a UGC item."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    PUBLISHED = "published"
    UNLISTED = "unlisted"
    REMOVED = "removed"
    ARCHIVED = "archived"


class ReviewVerdict(str, Enum):
    """Possible verdicts from a content review."""
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ESCALATED = "escalated"


class ContentRating(str, Enum):
    """Age-appropriateness ratings for content."""
    EVERYONE = "everyone"
    TEEN = "teen"
    MATURE = "mature"
    ADULT = "adult"
    UNRATED = "unrated"


class MonetizationModel(str, Enum):
    """Monetization models for UGC items."""
    FREE = "free"
    PAID = "paid"
    PAY_WHAT_YOU_WANT = "pay_what_you_want"
    FREEMIUM = "freemium"
    SUBSCRIPTION = "subscription"


class SubscriptionStatus(str, Enum):
    """States of a player subscription to an item."""
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    PENDING = "pending"


class DiscoverySort(str, Enum):
    """Sort modes for item discovery."""
    NEWEST = "newest"
    MOST_SUBSCRIBED = "most_subscribed"
    TOP_RATED = "top_rated"
    TRENDING = "trending"
    MOST_DOWNLOADED = "most_downloaded"
    FEATURED = "featured"


class ReportReason(str, Enum):
    """Reasons a player can report an item for."""
    INAPPROPRIATE = "inappropriate"
    COPYRIGHT = "copyright"
    SPAM = "spam"
    MALICIOUS = "malicious"
    BUGGY = "buggy"
    OFFENSIVE = "offensive"
    OTHER = "other"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class UGCItem:
    """A user-generated content entry.

    Holds the content metadata, lifecycle status, monetization model, pricing,
    versioning, and aggregate statistics (subscriptions, downloads, ratings).
    """
    item_id: str
    title: str
    description: str
    author_id: str
    item_type: UGCItemType
    status: UGCItemStatus = UGCItemStatus.DRAFT
    content_rating: ContentRating = ContentRating.UNRATED
    monetization: MonetizationModel = MonetizationModel.FREE
    price: float = 0.0
    version: str = "1.0.0"
    download_url: str = ""
    thumbnail_url: str = ""
    tags: List[str] = field(default_factory=list)
    category: str = ""
    subscription_count: int = 0
    download_count: int = 0
    rating_average: float = 0.0
    rating_count: int = 0
    is_featured: bool = False
    created_at: str = ""
    updated_at: str = ""
    published_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemReview:
    """A moderation review for a UGC item.

    Captures the reviewer, verdict, notes, quality rating, and timestamp.
    Each item may go through multiple reviews if revisions are needed.
    """
    review_id: str
    item_id: str
    reviewer_id: str
    verdict: ReviewVerdict
    notes: str = ""
    rating: float = 0.0
    reviewed_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemRating:
    """A player rating for a UGC item.

    Stores the score (0-5), optional review text, and helpfulness vote count
    from other players who found the rating useful.
    """
    rating_id: str
    item_id: str
    user_id: str
    score: float = 0.0
    review_text: str = ""
    helpful_count: int = 0
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemSubscription:
    """A player subscription to a UGC item.

    Tracks whether the player is actively subscribed, when they subscribed,
    and whether they want automatic updates when the item is updated.
    """
    subscription_id: str
    user_id: str
    item_id: str
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    subscribed_at: str = ""
    auto_update: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemCollection:
    """A curated collection of UGC items.

    Collections are created by curators to group related items together.
    They can be featured and followed by other players.
    """
    collection_id: str
    title: str
    description: str
    curator_id: str
    item_ids: List[str] = field(default_factory=list)
    is_featured: bool = False
    follower_count: int = 0
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ItemReport:
    """A player-submitted report about a UGC item.

    Reports are used for moderation: inappropriate content, copyright issues,
    spam, malicious code, bugs, or offensive material.
    """
    report_id: str
    item_id: str
    reporter_id: str
    reason: ReportReason
    description: str = ""
    status: str = "pending"
    resolved_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class MonetizationSplit:
    """Revenue distribution configuration for a UGC item.

    Defines how revenue is split between the author, the platform, and any
    collaborators. The shares must sum to 1.0.
    """
    split_id: str
    item_id: str
    author_share: float = 0.7
    platform_share: float = 0.3
    collaborator_shares: Dict[str, float] = field(default_factory=dict)
    total_revenue: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class UGCWorkshopConfig:
    """Configuration for the UGC workshop system."""
    max_items: int = 50000
    max_reviews_per_item: int = 20
    max_ratings_per_item: int = 5000
    auto_approve_free: bool = False
    require_review_for_paid: bool = True
    featured_rotation_days: int = 7
    default_monetization: MonetizationModel = MonetizationModel.FREE
    min_rating_threshold: float = 2.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class UGCWorkshopStats:
    """Aggregate statistics for the UGC workshop."""
    total_items: int = 0
    total_published: int = 0
    total_subscriptions: int = 0
    total_downloads: int = 0
    total_revenue: float = 0.0
    pending_reviews: int = 0
    active_collections: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class UGCWorkshopSnapshot:
    """Point-in-time snapshot of the workshop state."""
    timestamp: str = ""
    items: List[Dict[str, Any]] = field(default_factory=list)
    collections: List[Dict[str, Any]] = field(default_factory=list)
    reports: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class UGCWorkshopEvent:
    """An event emitted by the workshop system."""
    event_id: str
    timestamp: str
    event_type: str
    item_id: str = ""
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Main System
# ---------------------------------------------------------------------------

class UGCWorkshopSystem:
    """Singleton UGC workshop system managing all player-created content.

    Provides a complete content lifecycle: creation, moderation, publication,
    discovery, subscription, rating, collection, reporting, and monetization.
    All operations are thread-safe via an internal RLock.
    """

    _instance: Optional["UGCWorkshopSystem"] = None
    _init_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized = False
        # Storage containers
        self._items: Dict[str, UGCItem] = {}
        self._reviews: Dict[str, ItemReview] = {}
        self._ratings: Dict[str, ItemRating] = {}
        self._subscriptions: Dict[str, ItemSubscription] = {}
        self._collections: Dict[str, ItemCollection] = {}
        self._reports: Dict[str, ItemReport] = {}
        self._splits: Dict[str, MonetizationSplit] = {}
        self._events: List[UGCWorkshopEvent] = []
        # Indexes for fast lookups
        self._item_reviews: Dict[str, List[str]] = {}
        self._item_ratings: Dict[str, List[str]] = {}
        self._item_subscriptions: Dict[str, List[str]] = {}
        self._user_subscriptions: Dict[str, List[str]] = {}
        self._item_reports: Dict[str, List[str]] = {}
        # Config and stats
        self._config = UGCWorkshopConfig()
        self._stats = UGCWorkshopStats()
        self._tick_count: int = 0
        self.initialize()

    @classmethod
    def get_instance(cls) -> "UGCWorkshopSystem":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Populate the workshop with seed data."""
        base_time = datetime.utcnow()

        # --- UGC Items (12) ---
        item_seeds = [
            ("item_map_forest_01", "Mystic Forest Map", "A dense forest with hidden paths",
             "creator_001", UGCItemType.MAP, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.FREE, 0.0, "2.1.0",
             "ugc/maps/forest_01.zip", "ugc/thumbs/forest_01.png",
             ["forest", "nature", "adventure"], "Environment"),
            ("item_map_desert_01", "Scorched Desert", "A vast desert with ruins",
             "creator_002", UGCItemType.MAP, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAID, 2.99, "1.3.0",
             "ugc/maps/desert_01.zip", "ugc/thumbs/desert_01.png",
             ["desert", "ruins", "exploration"], "Environment"),
            ("item_skin_warrior_01", "Golden Warrior Skin", "A shiny golden warrior outfit",
             "creator_003", UGCItemType.SKIN, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAID, 4.99, "1.0.0",
             "ugc/skins/warrior_01.zip", "ugc/thumbs/warrior_01.png",
             ["warrior", "golden", "cosmetic"], "Cosmetic"),
            ("item_skin_mage_01", "Arcane Mage Skin", "A mystical mage with glowing runes",
             "creator_003", UGCItemType.SKIN, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAY_WHAT_YOU_WANT, 0.0, "1.2.0",
             "ugc/skins/mage_01.zip", "ugc/thumbs/mage_01.png",
             ["mage", "arcane", "cosmetic"], "Cosmetic"),
            ("item_mod_weather_01", "Dynamic Weather Mod", "Adds realistic weather effects",
             "creator_004", UGCItemType.MOD, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.FREE, 0.0, "3.0.1",
             "ugc/mods/weather_01.zip", "ugc/thumbs/weather_01.png",
             ["weather", "immersion", "atmosphere"], "Gameplay"),
            ("item_mod_ui_01", "Modern UI Overhaul", "Redesigned UI with dark theme",
             "creator_005", UGCItemType.MOD, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.FREEMIUM, 0.0, "2.4.0",
             "ugc/mods/ui_01.zip", "ugc/thumbs/ui_01.png",
             ["ui", "interface", "theme"], "Interface"),
            ("item_model_sword_01", "Crystal Sword Model", "A glowing crystal sword",
             "creator_006", UGCItemType.MODEL, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAID, 1.99, "1.0.0",
             "ugc/models/sword_01.zip", "ugc/thumbs/sword_01.png",
             ["sword", "weapon", "crystal"], "Weapon"),
            ("item_music_battle_01", "Epic Battle Theme", "Orchestral battle music",
             "creator_007", UGCItemType.MUSIC, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAID, 0.99, "1.0.0",
             "ugc/music/battle_01.zip", "ugc/thumbs/battle_01.png",
             ["music", "battle", "orchestral"], "Audio"),
            ("item_script_quest_01", "Side Quest Generator", "Procedural quest generation",
             "creator_008", UGCItemType.SCRIPT, UGCItemStatus.PUBLISHED,
             ContentRating.TEEN, MonetizationModel.FREE, 0.0, "1.5.2",
             "ugc/scripts/quest_01.zip", "ugc/thumbs/quest_01.png",
             ["quest", "procedural", "content"], "Gameplay"),
            ("item_prefab_castle_01", "Modular Castle Prefab", "A buildable castle kit",
             "creator_009", UGCItemType.PREFAB, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAID, 3.99, "2.0.0",
             "ugc/prefabs/castle_01.zip", "ugc/thumbs/castle_01.png",
             ["castle", "building", "modular"], "Structure"),
            ("item_scenario_dungeon_01", "Dungeon Crawl Scenario", "A challenging dungeon scenario",
             "creator_010", UGCItemType.SCENARIO, UGCItemStatus.PENDING_REVIEW,
             ContentRating.TEEN, MonetizationModel.FREE, 0.0, "1.0.0",
             "ugc/scenarios/dungeon_01.zip", "ugc/thumbs/dungeon_01.png",
             ["dungeon", "challenge", "scenario"], "Gameplay"),
            ("item_effect_fire_01", "Fire Particle Pack", "Various fire particle effects",
             "creator_006", UGCItemType.PARTICLE_EFFECT, UGCItemStatus.PUBLISHED,
             ContentRating.EVERYONE, MonetizationModel.PAY_WHAT_YOU_WANT, 0.0, "1.1.0",
             "ugc/effects/fire_01.zip", "ugc/thumbs/fire_01.png",
             ["fire", "particle", "effect"], "Visual"),
        ]

        for (iid, title, desc, author, itype, status, rating, monet,
             price, ver, dl, thumb, tags, cat) in item_seeds:
            ts = (base_time - timedelta(hours=len(item_seeds) - item_seeds.index(
                (iid, title, desc, author, itype, status, rating, monet,
                 price, ver, dl, thumb, tags, cat)))).isoformat() + "Z"
            pub_ts = ts if status == UGCItemStatus.PUBLISHED else ""
            sub_count = max(0, 50 - item_seeds.index(
                (iid, title, desc, author, itype, status, rating, monet,
                 price, ver, dl, thumb, tags, cat)) * 3)
            dl_count = sub_count * 4 + 10
            item = UGCItem(
                item_id=iid, title=title, description=desc, author_id=author,
                item_type=itype, status=status, content_rating=rating,
                monetization=monet, price=price, version=ver,
                download_url=dl, thumbnail_url=thumb, tags=tags, category=cat,
                subscription_count=sub_count, download_count=dl_count,
                rating_average=round(3.5 + (sub_count % 10) * 0.1, 2),
                rating_count=sub_count // 2 + 1,
                is_featured=(iid in ("item_map_forest_01", "item_mod_weather_01")),
                created_at=ts, updated_at=ts, published_at=pub_ts,
                metadata={"seed": True},
            )
            self._items[iid] = item

        # --- Reviews (6) ---
        review_seeds = [
            ("review_001", "item_map_forest_01", "moderator_001", ReviewVerdict.APPROVED,
             "Great map design with good detail.", 4.5),
            ("review_002", "item_map_desert_01", "moderator_001", ReviewVerdict.APPROVED,
             "Solid work, approved for publication.", 4.0),
            ("review_003", "item_skin_warrior_01", "moderator_002", ReviewVerdict.APPROVED,
             "High quality skin, no issues found.", 5.0),
            ("review_004", "item_mod_weather_01", "moderator_002", ReviewVerdict.APPROVED,
             "Excellent mod, enhances gameplay.", 4.5),
            ("review_005", "item_scenario_dungeon_01", "moderator_001", ReviewVerdict.NEEDS_REVISION,
             "Difficulty curve needs adjustment.", 3.0),
            ("review_006", "item_music_battle_01", "moderator_003", ReviewVerdict.APPROVED,
             "Great composition, approved.", 4.0),
        ]
        for rid, iid, rev_id, verdict, notes, rating in review_seeds:
            review = ItemReview(
                review_id=rid, item_id=iid, reviewer_id=rev_id,
                verdict=verdict, notes=notes, rating=rating,
                reviewed_at=_now(), metadata={"seed": True},
            )
            self._reviews[rid] = review
            self._item_reviews.setdefault(iid, []).append(rid)

        # --- Ratings (10) ---
        rating_seeds = [
            ("rating_001", "item_map_forest_01", "player_001", 5.0, "Amazing map!"),
            ("rating_002", "item_map_forest_01", "player_002", 4.0, "Pretty good."),
            ("rating_003", "item_map_desert_01", "player_001", 4.0, "Nice desert."),
            ("rating_004", "item_skin_warrior_01", "player_003", 5.0, "Best skin!"),
            ("rating_005", "item_skin_warrior_01", "player_004", 4.0, ""),
            ("rating_006", "item_mod_weather_01", "player_001", 5.0, "Love the rain!"),
            ("rating_007", "item_mod_weather_01", "player_005", 4.0, "Good effects."),
            ("rating_008", "item_music_battle_01", "player_002", 5.0, "Epic music!"),
            ("rating_009", "item_script_quest_01", "player_006", 4.0, "Fun quests."),
            ("rating_010", "item_prefab_castle_01", "player_003", 5.0, "Great castle!"),
        ]
        for rid, iid, uid, score, text in rating_seeds:
            rating = ItemRating(
                rating_id=rid, item_id=iid, user_id=uid,
                score=score, review_text=text, helpful_count=0,
                created_at=_now(), metadata={"seed": True},
            )
            self._ratings[rid] = rating
            self._item_ratings.setdefault(iid, []).append(rid)

        # --- Subscriptions (8) ---
        sub_seeds = [
            ("sub_001", "player_001", "item_map_forest_01", SubscriptionStatus.ACTIVE, True),
            ("sub_002", "player_001", "item_mod_weather_01", SubscriptionStatus.ACTIVE, True),
            ("sub_003", "player_002", "item_map_desert_01", SubscriptionStatus.ACTIVE, False),
            ("sub_004", "player_003", "item_skin_warrior_01", SubscriptionStatus.ACTIVE, True),
            ("sub_005", "player_004", "item_skin_warrior_01", SubscriptionStatus.CANCELLED, False),
            ("sub_006", "player_005", "item_mod_weather_01", SubscriptionStatus.ACTIVE, True),
            ("sub_007", "player_006", "item_script_quest_01", SubscriptionStatus.ACTIVE, True),
            ("sub_008", "player_001", "item_music_battle_01", SubscriptionStatus.ACTIVE, True),
        ]
        for sid, uid, iid, status, auto in sub_seeds:
            sub = ItemSubscription(
                subscription_id=sid, user_id=uid, item_id=iid,
                status=status, subscribed_at=_now(), auto_update=auto,
                metadata={"seed": True},
            )
            self._subscriptions[sid] = sub
            self._item_subscriptions.setdefault(iid, []).append(sid)
            self._user_subscriptions.setdefault(uid, []).append(sid)

        # --- Collections (4) ---
        collection_seeds = [
            ("col_001", "Best Maps", "Top-rated community maps",
             "curator_001", ["item_map_forest_01", "item_map_desert_01"], True, 120),
            ("col_002", "Essential Mods", "Must-have gameplay mods",
             "curator_001", ["item_mod_weather_01", "item_mod_ui_01"], True, 85),
            ("col_003", "Cosmetic Pack", "Skins and visual upgrades",
             "curator_002", ["item_skin_warrior_01", "item_skin_mage_01", "item_effect_fire_01"], False, 42),
            ("col_004", "Creator Tools", "Assets for game creators",
             "curator_002", ["item_prefab_castle_01", "item_model_sword_01", "item_script_quest_01"], False, 30),
        ]
        for cid, title, desc, curator, item_ids, featured, followers in collection_seeds:
            col = ItemCollection(
                collection_id=cid, title=title, description=desc,
                curator_id=curator, item_ids=item_ids, is_featured=featured,
                follower_count=followers, created_at=_now(),
                metadata={"seed": True},
            )
            self._collections[cid] = col

        # --- Reports (4) ---
        report_seeds = [
            ("report_001", "item_map_desert_01", "player_005", ReportReason.BUGGY,
             "Map has a hole in the terrain near the ruins.", "pending"),
            ("report_002", "item_mod_ui_01", "player_003", ReportReason.INAPPROPRIATE,
             "Some text in the UI is inappropriate.", "pending"),
            ("report_003", "item_skin_warrior_01", "player_007", ReportReason.COPYRIGHT,
             "This design looks copied from another game.", "resolved"),
            ("report_004", "item_script_quest_01", "player_008", ReportReason.MALICIOUS,
             "Script may contain harmful code.", "pending"),
        ]
        for rid, iid, reporter, reason, desc, status in report_seeds:
            report = ItemReport(
                report_id=rid, item_id=iid, reporter_id=reporter,
                reason=reason, description=desc, status=status,
                resolved_at=_now() if status == "resolved" else "",
                metadata={"seed": True},
            )
            self._reports[rid] = report
            self._item_reports.setdefault(iid, []).append(rid)

        # --- Monetization Splits (4) ---
        split_seeds = [
            ("split_001", "item_map_desert_01", 0.7, 0.3, {}, 89.70),
            ("split_002", "item_skin_warrior_01", 0.6, 0.3, {"collaborator_001": 0.1}, 149.70),
            ("split_003", "item_music_battle_01", 0.8, 0.2, {}, 19.80),
            ("split_004", "item_prefab_castle_01", 0.65, 0.25, {"collaborator_002": 0.1}, 79.80),
        ]
        for sid, iid, author_s, platform_s, collab, total in split_seeds:
            split = MonetizationSplit(
                split_id=sid, item_id=iid, author_share=author_s,
                platform_share=platform_s, collaborator_shares=collab,
                total_revenue=total, metadata={"seed": True},
            )
            self._splits[sid] = split

        # --- Events (5) ---
        event_seeds = [
            ("evt_001", "item_published", "item_map_forest_01", "Item published to workshop"),
            ("evt_002", "item_subscribed", "item_mod_weather_01", "New subscription received"),
            ("evt_003", "review_completed", "item_skin_warrior_01", "Review approved"),
            ("evt_004", "item_featured", "item_map_forest_01", "Item featured on front page"),
            ("evt_005", "report_filed", "item_mod_ui_01", "Report filed by player"),
        ]
        for eid, etype, iid, desc in event_seeds:
            event = UGCWorkshopEvent(
                event_id=eid, timestamp=_now(), event_type=etype,
                item_id=iid, description=desc, metadata={"seed": True},
            )
            self._events.append(event)

        self._refresh_stats()
        self._initialized = True

    def initialize(self) -> None:
        """Initialize the workshop system with seed data."""
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._seed()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, item_id: str = "", description: str = "",
              data: Optional[Dict[str, Any]] = None) -> None:
        event = UGCWorkshopEvent(
            event_id=_new_id("evt"),
            timestamp=_now(),
            event_type=event_type,
            item_id=item_id,
            description=description,
            metadata=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_items = len(self._items)
        self._stats.total_published = sum(
            1 for i in self._items.values()
            if i.status == UGCItemStatus.PUBLISHED
        )
        self._stats.total_subscriptions = sum(
            1 for s in self._subscriptions.values()
            if s.status == SubscriptionStatus.ACTIVE
        )
        self._stats.total_downloads = sum(i.download_count for i in self._items.values())
        self._stats.total_revenue = sum(s.total_revenue for s in self._splits.values())
        self._stats.pending_reviews = sum(
            1 for i in self._items.values()
            if i.status in (UGCItemStatus.PENDING_REVIEW, UGCItemStatus.UNDER_REVIEW)
        )
        self._stats.active_collections = len(self._collections)
        self._stats.tick_count = self._tick_count

    def _recompute_item_ratings(self, item_id: str) -> None:
        rating_ids = self._item_ratings.get(item_id, [])
        if not rating_ids:
            return
        scores = []
        for rid in rating_ids:
            r = self._ratings.get(rid)
            if r is not None:
                scores.append(r.score)
        if scores:
            item = self._items.get(item_id)
            if item is not None:
                item.rating_average = round(_mean(scores), 2)
                item.rating_count = len(scores)
                item.updated_at = _now()

    def _recompute_item_subscriptions(self, item_id: str) -> None:
        sub_ids = self._item_subscriptions.get(item_id, [])
        count = sum(
            1 for sid in sub_ids
            if self._subscriptions.get(sid) is not None
            and self._subscriptions[sid].status == SubscriptionStatus.ACTIVE
        )
        item = self._items.get(item_id)
        if item is not None:
            item.subscription_count = count

    # ------------------------------------------------------------------
    # Item Lifecycle
    # ------------------------------------------------------------------

    def register_item(self, item_id: str, title: str, description: str,
                      author_id: str, item_type: str, status: str = "draft",
                      content_rating: str = "unrated", monetization: str = "free",
                      price: float = 0.0, version: str = "1.0.0",
                      download_url: str = "", thumbnail_url: str = "",
                      tags: Optional[List[str]] = None, category: str = "",
                      metadata: Optional[Dict[str, Any]] = None
                      ) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            if item_id in self._items:
                return False, f"Item {item_id} already exists", None
            if len(self._items) >= _MAX_ITEMS:
                return False, "Maximum items reached", None
            itype = _coerce_enum(UGCItemType, item_type, UGCItemType.MAP)
            istatus = _coerce_enum(UGCItemStatus, status, UGCItemStatus.DRAFT)
            irating = _coerce_enum(ContentRating, content_rating, ContentRating.UNRATED)
            imonet = _coerce_enum(MonetizationModel, monetization, MonetizationModel.FREE)
            now = _now()
            item = UGCItem(
                item_id=item_id, title=title, description=description,
                author_id=author_id, item_type=itype, status=istatus,
                content_rating=irating, monetization=imonet,
                price=_safe_float(price, 0.0), version=version,
                download_url=download_url, thumbnail_url=thumbnail_url,
                tags=tags or [], category=category,
                created_at=now, updated_at=now, metadata=metadata or {},
            )
            self._items[item_id] = item
            self._refresh_stats()
            self._emit("item_registered", item_id, f"Item {title} registered")
            return True, "success", item

    def get_item(self, item_id: str) -> Optional[UGCItem]:
        with self._lock:
            return self._items.get(item_id)

    def list_items(self, item_type: Optional[str] = None,
                   status: Optional[str] = None,
                   author_id: Optional[str] = None,
                   sort: str = "newest",
                   limit: int = 50) -> List[UGCItem]:
        with self._lock:
            items = list(self._items.values())
            if item_type is not None:
                itype = _coerce_enum(UGCItemType, item_type)
                if itype is not None:
                    items = [i for i in items if i.item_type == itype]
            if status is not None:
                istatus = _coerce_enum(UGCItemStatus, status)
                if istatus is not None:
                    items = [i for i in items if i.status == istatus]
            if author_id is not None:
                items = [i for i in items if i.author_id == author_id]
            sort_enum = _coerce_enum(DiscoverySort, sort, DiscoverySort.NEWEST)
            if sort_enum == DiscoverySort.NEWEST:
                items.sort(key=lambda x: x.created_at, reverse=True)
            elif sort_enum == DiscoverySort.MOST_SUBSCRIBED:
                items.sort(key=lambda x: x.subscription_count, reverse=True)
            elif sort_enum == DiscoverySort.TOP_RATED:
                items.sort(key=lambda x: x.rating_average, reverse=True)
            elif sort_enum == DiscoverySort.MOST_DOWNLOADED:
                items.sort(key=lambda x: x.download_count, reverse=True)
            elif sort_enum == DiscoverySort.FEATURED:
                items.sort(key=lambda x: (x.is_featured, x.subscription_count), reverse=True)
            elif sort_enum == DiscoverySort.TRENDING:
                items.sort(key=lambda x: (x.download_count + x.subscription_count * 2), reverse=True)
            cap = min(_safe_int(limit, 50), _MAX_DISCOVERY_LIMIT)
            return items[:cap]

    def update_item(self, item_id: str, **kwargs: Any) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            for key in ("title", "description", "version", "download_url",
                        "thumbnail_url", "category", "price"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(item, key, kwargs[key])
            if "status" in kwargs and kwargs["status"] is not None:
                item.status = _coerce_enum(UGCItemStatus, kwargs["status"], item.status)
            if "content_rating" in kwargs and kwargs["content_rating"] is not None:
                item.content_rating = _coerce_enum(ContentRating, kwargs["content_rating"], item.content_rating)
            if "monetization" in kwargs and kwargs["monetization"] is not None:
                item.monetization = _coerce_enum(MonetizationModel, kwargs["monetization"], item.monetization)
            if "tags" in kwargs and kwargs["tags"] is not None:
                item.tags = list(kwargs["tags"])
            if "is_featured" in kwargs and kwargs["is_featured"] is not None:
                item.is_featured = bool(kwargs["is_featured"])
            if "metadata" in kwargs and kwargs["metadata"] is not None:
                item.metadata.update(kwargs["metadata"])
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("item_updated", item_id, f"Item {item_id} updated")
            return True, "success", item

    def remove_item(self, item_id: str) -> Tuple[bool, str]:
        with self._lock:
            if item_id not in self._items:
                return False, f"Item {item_id} not found"
            del self._items[item_id]
            # Clean up indexes
            for rid in self._item_reviews.pop(item_id, []):
                self._reviews.pop(rid, None)
            for rid in self._item_ratings.pop(item_id, []):
                self._ratings.pop(rid, None)
            for sid in self._item_subscriptions.pop(item_id, []):
                sub = self._subscriptions.pop(sid, None)
                if sub is not None:
                    user_subs = self._user_subscriptions.get(sub.user_id, [])
                    if sid in user_subs:
                        user_subs.remove(sid)
            for rpid in self._item_reports.pop(item_id, []):
                self._reports.pop(rpid, None)
            self._splits.pop(item_id, None)
            # Remove from collections
            for col in self._collections.values():
                if item_id in col.item_ids:
                    col.item_ids.remove(item_id)
            self._refresh_stats()
            self._emit("item_removed", item_id, f"Item {item_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Review Pipeline
    # ------------------------------------------------------------------

    def submit_for_review(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            if item.status not in (UGCItemStatus.DRAFT, UGCItemStatus.REJECTED,
                                   UGCItemStatus.NEEDS_REVISION if hasattr(UGCItemStatus, 'NEEDS_REVISION') else UGCItemStatus.DRAFT):
                return False, f"Item {item_id} cannot be submitted in status {item.status.value}", None
            item.status = UGCItemStatus.PENDING_REVIEW
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("item_submitted", item_id, f"Item {item_id} submitted for review")
            return True, "success", item

    def start_review(self, item_id: str, reviewer_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            if item.status != UGCItemStatus.PENDING_REVIEW:
                return False, f"Item {item_id} is not pending review", None
            item.status = UGCItemStatus.UNDER_REVIEW
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("review_started", item_id, f"Review started by {reviewer_id}")
            return True, "success", item

    def complete_review(self, review_id: str, item_id: str, reviewer_id: str,
                        verdict: str, notes: str = "", rating: float = 0.0,
                        metadata: Optional[Dict[str, Any]] = None
                        ) -> Tuple[bool, str, Optional[ItemReview]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            if review_id in self._reviews:
                return False, f"Review {review_id} already exists", None
            iverdict = _coerce_enum(ReviewVerdict, verdict, ReviewVerdict.ESCALATED)
            review = ItemReview(
                review_id=review_id, item_id=item_id, reviewer_id=reviewer_id,
                verdict=iverdict, notes=notes,
                rating=_clamp(_safe_float(rating, 0.0), 0.0, 5.0),
                reviewed_at=_now(), metadata=metadata or {},
            )
            self._reviews[review_id] = review
            self._item_reviews.setdefault(item_id, []).append(review_id)
            _evict_fifo_list(self._item_reviews[item_id], self._config.max_reviews_per_item)
            # Update item status based on verdict
            if iverdict == ReviewVerdict.APPROVED:
                item.status = UGCItemStatus.APPROVED
            elif iverdict == ReviewVerdict.REJECTED:
                item.status = UGCItemStatus.REJECTED
            elif iverdict == ReviewVerdict.NEEDS_REVISION:
                item.status = UGCItemStatus.PENDING_REVIEW
            elif iverdict == ReviewVerdict.ESCALATED:
                item.status = UGCItemStatus.UNDER_REVIEW
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("review_completed", item_id, f"Review {verdict}: {notes}")
            return True, "success", review

    def approve_item(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            item.status = UGCItemStatus.APPROVED
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("item_approved", item_id, f"Item {item_id} approved")
            return True, "success", item

    def reject_item(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            item.status = UGCItemStatus.REJECTED
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("item_rejected", item_id, f"Item {item_id} rejected")
            return True, "success", item

    def request_revision(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            item.status = UGCItemStatus.PENDING_REVIEW
            item.updated_at = _now()
            self._refresh_stats()
            self._emit("revision_requested", item_id, f"Item {item_id} needs revision")
            return True, "success", item

    def list_reviews(self, item_id: Optional[str] = None) -> List[ItemReview]:
        with self._lock:
            if item_id is not None:
                rids = self._item_reviews.get(item_id, [])
                return [self._reviews[rid] for rid in rids if rid in self._reviews]
            return list(self._reviews.values())

    def get_review(self, review_id: str) -> Optional[ItemReview]:
        with self._lock:
            return self._reviews.get(review_id)

    # ------------------------------------------------------------------
    # Ratings
    # ------------------------------------------------------------------

    def rate_item(self, rating_id: str, item_id: str, user_id: str,
                  score: float, review_text: str = "",
                  metadata: Optional[Dict[str, Any]] = None
                  ) -> Tuple[bool, str, Optional[ItemRating]]:
        with self._lock:
            if item_id not in self._items:
                return False, f"Item {item_id} not found", None
            if rating_id in self._ratings:
                return False, f"Rating {rating_id} already exists", None
            rids = self._item_ratings.get(item_id, [])
            if len(rids) >= _MAX_RATINGS_PER_ITEM:
                return False, "Maximum ratings for this item reached", None
            # Check if user already rated
            for rid in rids:
                existing = self._ratings.get(rid)
                if existing is not None and existing.user_id == user_id:
                    return False, f"User {user_id} already rated this item", None
            clamped_score = _clamp(_safe_float(score, 0.0), _RATING_MIN, _RATING_MAX)
            rating = ItemRating(
                rating_id=rating_id, item_id=item_id, user_id=user_id,
                score=clamped_score, review_text=review_text,
                helpful_count=0, created_at=_now(), metadata=metadata or {},
            )
            self._ratings[rating_id] = rating
            self._item_ratings.setdefault(item_id, []).append(rating_id)
            self._recompute_item_ratings(item_id)
            self._refresh_stats()
            self._emit("item_rated", item_id, f"Item rated {clamped_score} by {user_id}")
            return True, "success", rating

    def get_rating(self, rating_id: str) -> Optional[ItemRating]:
        with self._lock:
            return self._ratings.get(rating_id)

    def list_ratings(self, item_id: Optional[str] = None) -> List[ItemRating]:
        with self._lock:
            if item_id is not None:
                rids = self._item_ratings.get(item_id, [])
                return [self._ratings[rid] for rid in rids if rid in self._ratings]
            return list(self._ratings.values())

    def remove_rating(self, rating_id: str) -> Tuple[bool, str]:
        with self._lock:
            rating = self._ratings.get(rating_id)
            if rating is None:
                return False, f"Rating {rating_id} not found"
            del self._ratings[rating_id]
            rids = self._item_ratings.get(rating.item_id, [])
            if rating_id in rids:
                rids.remove(rating_id)
            self._recompute_item_ratings(rating.item_id)
            self._refresh_stats()
            self._emit("rating_removed", rating.item_id, f"Rating {rating_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Subscriptions
    # ------------------------------------------------------------------

    def subscribe(self, subscription_id: str, user_id: str, item_id: str,
                  auto_update: bool = True,
                  metadata: Optional[Dict[str, Any]] = None
                  ) -> Tuple[bool, str, Optional[ItemSubscription]]:
        with self._lock:
            if item_id not in self._items:
                return False, f"Item {item_id} not found", None
            if subscription_id in self._subscriptions:
                return False, f"Subscription {subscription_id} already exists", None
            # Check if already subscribed
            for sid in self._user_subscriptions.get(user_id, []):
                existing = self._subscriptions.get(sid)
                if existing is not None and existing.item_id == item_id and \
                   existing.status == SubscriptionStatus.ACTIVE:
                    return False, f"User {user_id} already subscribed to {item_id}", None
            sub = ItemSubscription(
                subscription_id=subscription_id, user_id=user_id, item_id=item_id,
                status=SubscriptionStatus.ACTIVE, subscribed_at=_now(),
                auto_update=auto_update, metadata=metadata or {},
            )
            self._subscriptions[subscription_id] = sub
            self._item_subscriptions.setdefault(item_id, []).append(subscription_id)
            self._user_subscriptions.setdefault(user_id, []).append(subscription_id)
            self._recompute_item_subscriptions(item_id)
            item = self._items.get(item_id)
            if item is not None:
                item.download_count += 1
            self._refresh_stats()
            self._emit("item_subscribed", item_id, f"User {user_id} subscribed")
            return True, "success", sub

    def unsubscribe(self, subscription_id: str) -> Tuple[bool, str]:
        with self._lock:
            sub = self._subscriptions.get(subscription_id)
            if sub is None:
                return False, f"Subscription {subscription_id} not found"
            sub.status = SubscriptionStatus.CANCELLED
            self._recompute_item_subscriptions(sub.item_id)
            self._refresh_stats()
            self._emit("item_unsubscribed", sub.item_id, f"Subscription {subscription_id} cancelled")
            return True, "success"

    def get_subscription(self, subscription_id: str) -> Optional[ItemSubscription]:
        with self._lock:
            return self._subscriptions.get(subscription_id)

    def list_subscriptions(self, user_id: Optional[str] = None,
                           item_id: Optional[str] = None) -> List[ItemSubscription]:
        with self._lock:
            if user_id is not None:
                sids = self._user_subscriptions.get(user_id, [])
                return [self._subscriptions[sid] for sid in sids if sid in self._subscriptions]
            if item_id is not None:
                sids = self._item_subscriptions.get(item_id, [])
                return [self._subscriptions[sid] for sid in sids if sid in self._subscriptions]
            return list(self._subscriptions.values())

    # ------------------------------------------------------------------
    # Collections
    # ------------------------------------------------------------------

    def create_collection(self, collection_id: str, title: str, description: str,
                          curator_id: str, item_ids: Optional[List[str]] = None,
                          is_featured: bool = False,
                          metadata: Optional[Dict[str, Any]] = None
                          ) -> Tuple[bool, str, Optional[ItemCollection]]:
        with self._lock:
            if collection_id in self._collections:
                return False, f"Collection {collection_id} already exists", None
            if len(self._collections) >= _MAX_COLLECTIONS:
                return False, "Maximum collections reached", None
            valid_items = [iid for iid in (item_ids or []) if iid in self._items]
            if len(valid_items) > _MAX_ITEMS_PER_COLLECTION:
                valid_items = valid_items[:_MAX_ITEMS_PER_COLLECTION]
            col = ItemCollection(
                collection_id=collection_id, title=title, description=description,
                curator_id=curator_id, item_ids=valid_items,
                is_featured=is_featured, follower_count=0,
                created_at=_now(), metadata=metadata or {},
            )
            self._collections[collection_id] = col
            self._refresh_stats()
            self._emit("collection_created", "", f"Collection {title} created")
            return True, "success", col

    def get_collection(self, collection_id: str) -> Optional[ItemCollection]:
        with self._lock:
            return self._collections.get(collection_id)

    def list_collections(self, featured_only: bool = False) -> List[ItemCollection]:
        with self._lock:
            cols = list(self._collections.values())
            if featured_only:
                cols = [c for c in cols if c.is_featured]
            return cols

    def add_to_collection(self, collection_id: str, item_id: str) -> Tuple[bool, str, Optional[ItemCollection]]:
        with self._lock:
            col = self._collections.get(collection_id)
            if col is None:
                return False, f"Collection {collection_id} not found", None
            if item_id not in self._items:
                return False, f"Item {item_id} not found", None
            if item_id in col.item_ids:
                return False, f"Item {item_id} already in collection", None
            if len(col.item_ids) >= _MAX_ITEMS_PER_COLLECTION:
                return False, "Collection is full", None
            col.item_ids.append(item_id)
            self._emit("collection_updated", item_id, f"Item added to collection {collection_id}")
            return True, "success", col

    def remove_from_collection(self, collection_id: str, item_id: str) -> Tuple[bool, str, Optional[ItemCollection]]:
        with self._lock:
            col = self._collections.get(collection_id)
            if col is None:
                return False, f"Collection {collection_id} not found", None
            if item_id not in col.item_ids:
                return False, f"Item {item_id} not in collection", None
            col.item_ids.remove(item_id)
            self._emit("collection_updated", item_id, f"Item removed from collection {collection_id}")
            return True, "success", col

    def remove_collection(self, collection_id: str) -> Tuple[bool, str]:
        with self._lock:
            if collection_id not in self._collections:
                return False, f"Collection {collection_id} not found"
            del self._collections[collection_id]
            self._refresh_stats()
            self._emit("collection_removed", "", f"Collection {collection_id} removed")
            return True, "success"

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    def report_item(self, report_id: str, item_id: str, reporter_id: str,
                    reason: str, description: str = "",
                    metadata: Optional[Dict[str, Any]] = None
                    ) -> Tuple[bool, str, Optional[ItemReport]]:
        with self._lock:
            if item_id not in self._items:
                return False, f"Item {item_id} not found", None
            if report_id in self._reports:
                return False, f"Report {report_id} already exists", None
            ireason = _coerce_enum(ReportReason, reason, ReportReason.OTHER)
            report = ItemReport(
                report_id=report_id, item_id=item_id, reporter_id=reporter_id,
                reason=ireason, description=description, status="pending",
                resolved_at="", metadata=metadata or {},
            )
            self._reports[report_id] = report
            self._item_reports.setdefault(item_id, []).append(report_id)
            self._refresh_stats()
            self._emit("report_filed", item_id, f"Report filed: {reason}")
            return True, "success", report

    def resolve_report(self, report_id: str, resolution: str = "resolved") -> Tuple[bool, str, Optional[ItemReport]]:
        with self._lock:
            report = self._reports.get(report_id)
            if report is None:
                return False, f"Report {report_id} not found", None
            report.status = resolution
            report.resolved_at = _now()
            self._emit("report_resolved", report.item_id, f"Report {report_id} resolved: {resolution}")
            return True, "success", report

    def list_reports(self, item_id: Optional[str] = None,
                     status: Optional[str] = None) -> List[ItemReport]:
        with self._lock:
            if item_id is not None:
                rids = self._item_reports.get(item_id, [])
                reports = [self._reports[rid] for rid in rids if rid in self._reports]
            else:
                reports = list(self._reports.values())
            if status is not None:
                reports = [r for r in reports if r.status == status]
            return reports

    def get_report(self, report_id: str) -> Optional[ItemReport]:
        with self._lock:
            return self._reports.get(report_id)

    # ------------------------------------------------------------------
    # Monetization
    # ------------------------------------------------------------------

    def set_monetization(self, split_id: str, item_id: str, author_share: float,
                         platform_share: float,
                         collaborator_shares: Optional[Dict[str, float]] = None,
                         metadata: Optional[Dict[str, Any]] = None
                         ) -> Tuple[bool, str, Optional[MonetizationSplit]]:
        with self._lock:
            if item_id not in self._items:
                return False, f"Item {item_id} not found", None
            author_s = _clamp(_safe_float(author_share, 0.7), _SHARE_MIN, _SHARE_MAX)
            platform_s = _clamp(_safe_float(platform_share, 0.3), _SHARE_MIN, _SHARE_MAX)
            total = author_s + platform_s
            collab = collaborator_shares or {}
            for v in collab.values():
                total += _safe_float(v, 0.0)
            if abs(total - 1.0) > 0.01:
                return False, f"Shares must sum to 1.0, got {total:.4f}", None
            split = MonetizationSplit(
                split_id=split_id, item_id=item_id, author_share=author_s,
                platform_share=platform_s, collaborator_shares=collab,
                total_revenue=0.0, metadata=metadata or {},
            )
            self._splits[split_id] = split
            self._emit("monetization_set", item_id, f"Monetization split configured")
            return True, "success", split

    def get_monetization(self, item_id: str) -> Optional[MonetizationSplit]:
        with self._lock:
            for split in self._splits.values():
                if split.item_id == item_id:
                    return split
            return None

    def process_revenue(self, item_id: str, amount: float) -> Tuple[bool, str, Optional[MonetizationSplit]]:
        with self._lock:
            split = None
            for s in self._splits.values():
                if s.item_id == item_id:
                    split = s
                    break
            if split is None:
                return False, f"No monetization split for item {item_id}", None
            amt = _safe_float(amount, 0.0)
            if amt < 0:
                return False, "Revenue amount cannot be negative", None
            split.total_revenue += amt
            self._refresh_stats()
            self._emit("revenue_processed", item_id, f"Revenue {amt} processed for item {item_id}")
            return True, "success", split

    # ------------------------------------------------------------------
    # Discovery and Featuring
    # ------------------------------------------------------------------

    def feature_item(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            item.is_featured = True
            item.updated_at = _now()
            self._emit("item_featured", item_id, f"Item {item_id} featured")
            return True, "success", item

    def unfeature_item(self, item_id: str) -> Tuple[bool, str, Optional[UGCItem]]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return False, f"Item {item_id} not found", None
            item.is_featured = False
            item.updated_at = _now()
            self._emit("item_unfeatured", item_id, f"Item {item_id} unfeatured")
            return True, "success", item

    def get_featured(self) -> List[UGCItem]:
        with self._lock:
            return [i for i in self._items.values() if i.is_featured]

    def discover_items(self, query: str = "", item_type: Optional[str] = None,
                       sort: str = "newest", limit: int = 50) -> List[UGCItem]:
        with self._lock:
            items = [i for i in self._items.values()
                     if i.status == UGCItemStatus.PUBLISHED]
            if query:
                q_lower = query.lower()
                items = [i for i in items
                         if q_lower in i.title.lower() or
                         q_lower in i.description.lower() or
                         any(q_lower in t.lower() for t in i.tags)]
            if item_type is not None:
                itype = _coerce_enum(UGCItemType, item_type)
                if itype is not None:
                    items = [i for i in items if i.item_type == itype]
            sort_enum = _coerce_enum(DiscoverySort, sort, DiscoverySort.NEWEST)
            if sort_enum == DiscoverySort.NEWEST:
                items.sort(key=lambda x: x.created_at, reverse=True)
            elif sort_enum == DiscoverySort.MOST_SUBSCRIBED:
                items.sort(key=lambda x: x.subscription_count, reverse=True)
            elif sort_enum == DiscoverySort.TOP_RATED:
                items.sort(key=lambda x: x.rating_average, reverse=True)
            elif sort_enum == DiscoverySort.MOST_DOWNLOADED:
                items.sort(key=lambda x: x.download_count, reverse=True)
            elif sort_enum == DiscoverySort.FEATURED:
                items.sort(key=lambda x: (x.is_featured, x.subscription_count), reverse=True)
            elif sort_enum == DiscoverySort.TRENDING:
                items.sort(key=lambda x: (x.download_count + x.subscription_count * 2), reverse=True)
            cap = min(_safe_int(limit, _DEFAULT_DISCOVERY_LIMIT), _MAX_DISCOVERY_LIMIT)
            return items[:cap]

    # ------------------------------------------------------------------
    # System Lifecycle
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_items": len(self._items),
                "total_reviews": len(self._reviews),
                "total_ratings": len(self._ratings),
                "total_subscriptions": len(self._subscriptions),
                "total_collections": len(self._collections),
                "total_reports": len(self._reports),
                "total_splits": len(self._splits),
            }

    def get_stats(self) -> UGCWorkshopStats:
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> UGCWorkshopSnapshot:
        with self._lock:
            self._refresh_stats()
            return UGCWorkshopSnapshot(
                timestamp=_now(),
                items=[i.to_dict() for i in list(self._items.values())[:20]],
                collections=[c.to_dict() for c in list(self._collections.values())[:20]],
                reports=[r.to_dict() for r in list(self._reports.values())[:20]],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> UGCWorkshopConfig:
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, UGCWorkshopConfig]:
        with self._lock:
            for key in ("max_items", "max_reviews_per_item", "max_ratings_per_item",
                        "featured_rotation_days"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, _safe_int(kwargs[key], getattr(self._config, key)))
            for key in ("auto_approve_free", "require_review_for_paid"):
                if key in kwargs and kwargs[key] is not None:
                    setattr(self._config, key, bool(kwargs[key]))
            if "default_monetization" in kwargs and kwargs["default_monetization"] is not None:
                self._config.default_monetization = _coerce_enum(
                    MonetizationModel, kwargs["default_monetization"],
                    self._config.default_monetization)
            if "min_rating_threshold" in kwargs and kwargs["min_rating_threshold"] is not None:
                self._config.min_rating_threshold = _clamp(
                    _safe_float(kwargs["min_rating_threshold"], 2.0), 0.0, 5.0)
            return True, "success", self._config

    def tick(self, dt: float = 0.016) -> Dict[str, Any]:
        with self._lock:
            self._tick_count += 1
            # Auto-expire old reports (simplified: resolve reports older than rotation days)
            rotation_seconds = self._config.featured_rotation_days * 86400
            now = datetime.utcnow()
            expired_count = 0
            for report in self._reports.values():
                if report.status == "pending":
                    created = _parse_iso(report.resolved_at) if report.resolved_at else None
                    # In a real system, check report age; here we just count
            self._refresh_stats()
            return {
                "tick": self._tick_count,
                "dt": _safe_float(dt, 0.016),
                "total_items": len(self._items),
                "total_published": self._stats.total_published,
                "pending_reviews": self._stats.pending_reviews,
                "active_subscriptions": self._stats.total_subscriptions,
                "total_collections": len(self._collections),
                "total_reports": len(self._reports),
            }

    def reset(self) -> None:
        with self._lock:
            self._items.clear()
            self._reviews.clear()
            self._ratings.clear()
            self._subscriptions.clear()
            self._collections.clear()
            self._reports.clear()
            self._splits.clear()
            self._events.clear()
            self._item_reviews.clear()
            self._item_ratings.clear()
            self._item_subscriptions.clear()
            self._user_subscriptions.clear()
            self._item_reports.clear()
            self._config = UGCWorkshopConfig()
            self._stats = UGCWorkshopStats()
            self._tick_count = 0
            self._initialized = False
            self._seed()

    def list_events(self, limit: int = 100) -> List[UGCWorkshopEvent]:
        with self._lock:
            cap = min(_safe_int(limit, 100), _MAX_EVENTS)
            return list(self._events[-cap:])


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_ugc_workshop_system() -> UGCWorkshopSystem:
    """Return the shared UGCWorkshopSystem singleton instance."""
    return UGCWorkshopSystem.get_instance()


# ---------------------------------------------------------------------------
# Exported Symbols
# ---------------------------------------------------------------------------

__all__ = [
    # Enums
    "UGCItemType",
    "UGCItemStatus",
    "ReviewVerdict",
    "ContentRating",
    "MonetizationModel",
    "SubscriptionStatus",
    "DiscoverySort",
    "ReportReason",
    # Data classes
    "UGCItem",
    "ItemReview",
    "ItemRating",
    "ItemSubscription",
    "ItemCollection",
    "ItemReport",
    "MonetizationSplit",
    "UGCWorkshopConfig",
    "UGCWorkshopStats",
    "UGCWorkshopSnapshot",
    "UGCWorkshopEvent",
    # Main system
    "UGCWorkshopSystem",
    "get_ugc_workshop_system",
]
