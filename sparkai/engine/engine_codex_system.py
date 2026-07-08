"""
SparkLabs Engine - Codex System

A discovery-driven knowledge compendium for the SparkLabs AI-native
game engine. It maintains a categorized archive of bestiary entries,
item lore, location atlases, character profiles, faction dossiers,
quest logs, artifact records, recipe schematics, and skill
descriptions. Entries progress through a discovery lifecycle (locked,
discovered, partial, completed, archived) and can be organized into
curated collections. The system tracks per-category completion
statistics and emits audit events for every lifecycle transition.

Architecture:
  CodexSystem (singleton)
    |-- CodexEntry, CodexCategory, CodexCollection,
       CodexStats, CodexSnapshot, CodexEvent
    |-- CodexCategoryKind, CodexEntryStatus, CodexRarityTier,
       CodexEventKind

Core Capabilities:
  - register_category / get_category / list_categories /
    remove_category: category lifecycle with display metadata.
  - register_entry / get_entry / list_entries / update_entry /
    remove_entry: entry lifecycle with category, rarity, and
    unlock conditions.
  - discover_entry / complete_entry: lifecycle transitions that
    advance entries through the discovery pipeline.
  - register_collection / get_collection / list_collections /
    update_collection / remove_collection: curated groupings of
    entries with ordering and visibility rules.
  - add_to_collection / remove_from_collection: membership
    management for collections.
  - search_entries: token-based search across names, tags, and
    summary text with optional category and status filters.
  - get_completion_stats: per-category and overall completion
    metrics that drive codex UI progress bars.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`CodexSystem.get_instance` or the module-level
:func:`get_codex_system` factory.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_CATEGORIES: int = 200
_MAX_ENTRIES: int = 20000
_MAX_COLLECTIONS: int = 1000
_MAX_EVENTS: int = 5000


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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class CodexCategoryKind(Enum):
    """Top-level classification of codex entries."""
    BESTIARY = "bestiary"
    ITEM = "item"
    LOCATION = "location"
    CHARACTER = "character"
    LORE = "lore"
    QUEST = "quest"
    FACTION = "faction"
    ARTIFACT = "artifact"
    RECIPE = "recipe"
    SKILL = "skill"


class CodexEntryStatus(Enum):
    """Lifecycle state of a codex entry."""
    LOCKED = "locked"
    DISCOVERED = "discovered"
    PARTIAL = "partial"
    COMPLETED = "completed"
    ARCHIVED = "archived"


class CodexRarityTier(Enum):
    """Rarity tier that influences visual treatment and discovery weight."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CodexEventKind(Enum):
    """Audit event types emitted by the codex system."""
    CATEGORY_REGISTERED = "category_registered"
    CATEGORY_REMOVED = "category_removed"
    ENTRY_REGISTERED = "entry_registered"
    ENTRY_UPDATED = "entry_updated"
    ENTRY_REMOVED = "entry_removed"
    ENTRY_DISCOVERED = "entry_discovered"
    ENTRY_COMPLETED = "entry_completed"
    COLLECTION_REGISTERED = "collection_registered"
    COLLECTION_UPDATED = "collection_updated"
    COLLECTION_REMOVED = "collection_removed"
    COLLECTION_MEMBER_ADDED = "collection_member_added"
    COLLECTION_MEMBER_REMOVED = "collection_member_removed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CodexCategory:
    """A top-level grouping for codex entries."""
    category_id: str = field(default_factory=lambda: _new_id("cat"))
    kind: str = CodexCategoryKind.LORE.value
    name: str = ""
    description: str = ""
    icon: str = ""
    color: str = "#FFFFFF"
    display_order: int = 0
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodexEntry:
    """A single knowledge record in the codex."""
    entry_id: str = field(default_factory=lambda: _new_id("cdx"))
    category_id: str = ""
    title: str = ""
    summary: str = ""
    body: str = ""
    status: str = CodexEntryStatus.LOCKED.value
    rarity: str = CodexRarityTier.COMMON.value
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    portrait: str = ""
    unlock_condition: str = ""
    discover_count: int = 0
    complete_count: int = 0
    sort_key: str = ""
    visible: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    discovered_at: str = ""
    completed_at: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodexCollection:
    """A curated grouping of codex entries."""
    collection_id: str = field(default_factory=lambda: _new_id("col"))
    name: str = ""
    description: str = ""
    entry_ids: List[str] = field(default_factory=list)
    icon: str = ""
    color: str = "#FFFFFF"
    visible: bool = True
    display_order: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodexStats:
    """Aggregate counters for the codex system."""
    total_categories: int = 0
    total_entries: int = 0
    total_collections: int = 0
    total_discovered: int = 0
    total_completed: int = 0
    total_archived: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodexSnapshot:
    """Immutable point-in-time capture of codex state."""
    categories: Dict[str, Any] = field(default_factory=dict)
    entries: Dict[str, Any] = field(default_factory=dict)
    collections: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CodexEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = CodexEventKind.ENTRY_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Static Lookup Tables
# ---------------------------------------------------------------------------

_RARITY_RANK: Dict[str, int] = {
    CodexRarityTier.COMMON.value: 0,
    CodexRarityTier.UNCOMMON.value: 1,
    CodexRarityTier.RARE.value: 2,
    CodexRarityTier.EPIC.value: 3,
    CodexRarityTier.LEGENDARY.value: 4,
    CodexRarityTier.MYTHIC.value: 5,
}

_STATUS_RANK: Dict[str, int] = {
    CodexEntryStatus.LOCKED.value: 0,
    CodexEntryStatus.DISCOVERED.value: 1,
    CodexEntryStatus.PARTIAL.value: 2,
    CodexEntryStatus.COMPLETED.value: 3,
    CodexEntryStatus.ARCHIVED.value: 4,
}


# ---------------------------------------------------------------------------
# Codex System Singleton
# ---------------------------------------------------------------------------


class CodexSystem:
    """Singleton engine module that maintains the discovery codex.

    The codex organizes knowledge entries into categories, tracks
    discovery lifecycle transitions, and curates collections of
    related entries. It exposes search, completion statistics, and
    audit observability for downstream UIs and agents.
    """

    _instance: Optional["CodexSystem"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._categories: Dict[str, CodexCategory] = {}
        self._entries: Dict[str, CodexEntry] = {}
        self._collections: Dict[str, CodexCollection] = {}
        self._audit: List[CodexEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "CodexSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = cls()
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_defaults(self) -> None:
        # Bestiary category with one discovered creature.
        cat_bestiary = CodexCategory(
            category_id="cat_bestiary",
            kind=CodexCategoryKind.BESTIARY.value,
            name="Bestiary",
            description="Catalogued creatures encountered across the world.",
            icon="book-skull",
            color="#8E44AD",
            display_order=1,
        )
        self._categories[cat_bestiary.category_id] = cat_bestiary
        self._audit.append(CodexEvent(
            kind=CodexEventKind.CATEGORY_REGISTERED.value,
            payload={"category_id": cat_bestiary.category_id},
        ))

        # Item category with one common item.
        cat_items = CodexCategory(
            category_id="cat_items",
            kind=CodexCategoryKind.ITEM.value,
            name="Items",
            description="Material records for every collectible item.",
            icon="backpack",
            color="#16A085",
            display_order=2,
        )
        self._categories[cat_items.category_id] = cat_items
        self._audit.append(CodexEvent(
            kind=CodexEventKind.CATEGORY_REGISTERED.value,
            payload={"category_id": cat_items.category_id},
        ))

        # Location category with one discovered region.
        cat_locations = CodexCategory(
            category_id="cat_locations",
            kind=CodexCategoryKind.LOCATION.value,
            name="Atlas",
            description="Cartographic survey of regions and landmarks.",
            icon="map",
            color="#2980B9",
            display_order=3,
        )
        self._categories[cat_locations.category_id] = cat_locations
        self._audit.append(CodexEvent(
            kind=CodexEventKind.CATEGORY_REGISTERED.value,
            payload={"category_id": cat_locations.category_id},
        ))

        # Seed entries.
        entry_goblin = CodexEntry(
            entry_id="cdx_forest_goblin",
            category_id="cat_bestiary",
            title="Forest Goblin",
            summary="A nimble verdant-skinned raider native to woodland biomes.",
            body="Forest goblins travel in packs of four to eight, favoring "
                 "ambush tactics at dawn. They are nocturnal by preference "
                 "but will defend territory aggressively when provoked. "
                 "Weak to fire and silvered weapons.",
            status=CodexEntryStatus.COMPLETED.value,
            rarity=CodexRarityTier.COMMON.value,
            tags=["creature", "forest", "humanoid", "nocturnal"],
            icon="goblin",
            unlock_condition="encounter_forest_goblin",
            discover_count=1,
            complete_count=1,
            sort_key="forest_goblin",
        )
        self._entries[entry_goblin.entry_id] = entry_goblin
        self._audit.append(CodexEvent(
            kind=CodexEventKind.ENTRY_REGISTERED.value,
            payload={"entry_id": entry_goblin.entry_id},
        ))

        entry_potion = CodexEntry(
            entry_id="cdx_moss_potion",
            category_id="cat_items",
            title="Mossback Potion",
            summary="A restorative draught brewed from river moss and honey.",
            body="Restores 40 vitality over 8 seconds. Commonly brewed by "
                 "village herbalists in the Greenway. The moss must be "
                 "harvested at moonrise to retain its curative potency.",
            status=CodexEntryStatus.DISCOVERED.value,
            rarity=CodexRarityTier.COMMON.value,
            tags=["consumable", "healing", "craftable"],
            icon="flask",
            unlock_condition="acquire_mossback_potion",
            discover_count=1,
            sort_key="moss_potion",
        )
        self._entries[entry_potion.entry_id] = entry_potion
        self._audit.append(CodexEvent(
            kind=CodexEventKind.ENTRY_REGISTERED.value,
            payload={"entry_id": entry_potion.entry_id},
        ))

        entry_glade = CodexEntry(
            entry_id="cdx_whispering_glade",
            category_id="cat_locations",
            title="Whispering Glade",
            summary="A serene clearing where the wind carries old voices.",
            body="Located in the heart of the Greenway, the Whispering "
                 "Glade is a pilgrimage site for those seeking counsel "
                 "with the ancient forest spirits. Visitors report hearing "
                 "fragments of forgotten conversations carried on the breeze.",
            status=CodexEntryStatus.PARTIAL.value,
            rarity=CodexRarityTier.RARE.value,
            tags=["landmark", "sacred", "forest"],
            icon="tree",
            unlock_condition="discover_whispering_glade",
            discover_count=1,
            sort_key="whispering_glade",
        )
        self._entries[entry_glade.entry_id] = entry_glade
        self._audit.append(CodexEvent(
            kind=CodexEventKind.ENTRY_REGISTERED.value,
            payload={"entry_id": entry_glade.entry_id},
        ))

        # Seed one curated collection.
        collection = CodexCollection(
            collection_id="col_greenway_primer",
            name="Greenway Primer",
            description="Essential entries for travelers entering the Greenway.",
            entry_ids=[entry_goblin.entry_id, entry_potion.entry_id, entry_glade.entry_id],
            icon="compass",
            color="#27AE60",
            display_order=1,
        )
        self._collections[collection.collection_id] = collection
        self._audit.append(CodexEvent(
            kind=CodexEventKind.COLLECTION_REGISTERED.value,
            payload={"collection_id": collection.collection_id},
        ))

    # ------------------------------------------------------------------
    # Category Lifecycle
    # ------------------------------------------------------------------

    def register_category(
        self,
        kind: str,
        name: str,
        description: str = "",
        icon: str = "",
        color: str = "#FFFFFF",
        display_order: int = 0,
        visible: bool = True,
        category_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            category_id = category_id or _new_id("cat")
            if category_id in self._categories:
                return {"ok": False, "error": "category_id already exists"}
            category = CodexCategory(
                category_id=category_id,
                kind=kind,
                name=name,
                description=description,
                icon=icon,
                color=color,
                display_order=int(display_order),
                visible=bool(visible),
                metadata=dict(metadata or {}),
            )
            self._categories[category_id] = category
            _evict_fifo_dict(self._categories, _MAX_CATEGORIES)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.CATEGORY_REGISTERED.value,
                payload={"category_id": category_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "category": category.to_dict()}

    def get_category(self, category_id: str) -> Dict[str, Any]:
        with self._lock:
            category = self._categories.get(category_id)
            if category is None:
                return {"ok": False, "error": "category not found"}
            return {"ok": True, "category": category.to_dict()}

    def list_categories(
        self,
        kind: str = "",
        visible_only: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for category in self._categories.values():
                if kind and category.kind != kind:
                    continue
                if visible_only and not category.visible:
                    continue
                out.append(category.to_dict())
            out.sort(key=lambda c: (c.get("display_order", 0), c.get("name", "")))
            return {"ok": True, "categories": out}

    def remove_category(self, category_id: str) -> Dict[str, Any]:
        with self._lock:
            if category_id not in self._categories:
                return {"ok": False, "error": "category not found"}
            self._categories.pop(category_id, None)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.CATEGORY_REMOVED.value,
                payload={"category_id": category_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True}

    # ------------------------------------------------------------------
    # Entry Lifecycle
    # ------------------------------------------------------------------

    def register_entry(
        self,
        category_id: str,
        title: str,
        summary: str = "",
        body: str = "",
        status: str = CodexEntryStatus.LOCKED.value,
        rarity: str = CodexRarityTier.COMMON.value,
        tags: Optional[List[str]] = None,
        icon: str = "",
        portrait: str = "",
        unlock_condition: str = "",
        sort_key: str = "",
        visible: bool = True,
        entry_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            if category_id and category_id not in self._categories:
                return {"ok": False, "error": "category not found"}
            entry_id = entry_id or _new_id("cdx")
            if entry_id in self._entries:
                return {"ok": False, "error": "entry_id already exists"}
            entry = CodexEntry(
                entry_id=entry_id,
                category_id=category_id,
                title=title,
                summary=summary,
                body=body,
                status=status,
                rarity=rarity,
                tags=list(tags or []),
                icon=icon,
                portrait=portrait,
                unlock_condition=unlock_condition,
                sort_key=sort_key or title,
                visible=bool(visible),
                metadata=dict(metadata or {}),
            )
            self._entries[entry_id] = entry
            _evict_fifo_dict(self._entries, _MAX_ENTRIES)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.ENTRY_REGISTERED.value,
                payload={"entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "entry": entry.to_dict()}

    def get_entry(self, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return {"ok": False, "error": "entry not found"}
            return {"ok": True, "entry": entry.to_dict()}

    def list_entries(
        self,
        category_id: str = "",
        status: str = "",
        rarity: str = "",
        tag: str = "",
        visible_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for entry in self._entries.values():
                if category_id and entry.category_id != category_id:
                    continue
                if status and entry.status != status:
                    continue
                if rarity and entry.rarity != rarity:
                    continue
                if tag and tag not in entry.tags:
                    continue
                if visible_only and not entry.visible:
                    continue
                out.append(entry.to_dict())
            out.sort(key=lambda e: (
                e.get("sort_key", "") or e.get("title", ""),
                e.get("entry_id", ""),
            ))
            total = len(out)
            limit = max(1, min(int(limit), 500))
            offset = max(0, int(offset))
            out = out[offset:offset + limit]
            return {"ok": True, "entries": out, "total": total}

    def update_entry(self, entry_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return {"ok": False, "error": "entry not found"}
            for key, value in fields.items():
                if not hasattr(entry, key):
                    continue
                if key == "entry_id":
                    continue
                if key == "tags" and isinstance(value, list):
                    setattr(entry, key, list(value))
                elif key == "metadata" and isinstance(value, dict):
                    merged = dict(entry.metadata)
                    merged.update(value)
                    setattr(entry, key, merged)
                else:
                    setattr(entry, key, value)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.ENTRY_UPDATED.value,
                payload={"entry_id": entry_id, "fields": list(fields.keys())},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "entry": entry.to_dict()}

    def remove_entry(self, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            if entry_id not in self._entries:
                return {"ok": False, "error": "entry not found"}
            self._entries.pop(entry_id, None)
            for collection in self._collections.values():
                while entry_id in collection.entry_ids:
                    collection.entry_ids.remove(entry_id)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.ENTRY_REMOVED.value,
                payload={"entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True}

    # ------------------------------------------------------------------
    # Discovery Lifecycle
    # ------------------------------------------------------------------

    def discover_entry(self, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return {"ok": False, "error": "entry not found"}
            entry.discover_count = int(entry.discover_count) + 1
            if _STATUS_RANK.get(entry.status, 0) < _STATUS_RANK.get(
                CodexEntryStatus.DISCOVERED.value, 0
            ):
                entry.status = CodexEntryStatus.DISCOVERED.value
            if not entry.discovered_at:
                entry.discovered_at = _now()
            self._audit.append(CodexEvent(
                kind=CodexEventKind.ENTRY_DISCOVERED.value,
                payload={"entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "entry": entry.to_dict()}

    def complete_entry(self, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            entry = self._entries.get(entry_id)
            if entry is None:
                return {"ok": False, "error": "entry not found"}
            entry.complete_count = int(entry.complete_count) + 1
            entry.status = CodexEntryStatus.COMPLETED.value
            entry.completed_at = _now()
            self._audit.append(CodexEvent(
                kind=CodexEventKind.ENTRY_COMPLETED.value,
                payload={"entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "entry": entry.to_dict()}

    # ------------------------------------------------------------------
    # Collection Lifecycle
    # ------------------------------------------------------------------

    def register_collection(
        self,
        name: str,
        description: str = "",
        entry_ids: Optional[List[str]] = None,
        icon: str = "",
        color: str = "#FFFFFF",
        visible: bool = True,
        display_order: int = 0,
        collection_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        with self._lock:
            collection_id = collection_id or _new_id("col")
            if collection_id in self._collections:
                return {"ok": False, "error": "collection_id already exists"}
            collection = CodexCollection(
                collection_id=collection_id,
                name=name,
                description=description,
                entry_ids=list(entry_ids or []),
                icon=icon,
                color=color,
                visible=bool(visible),
                display_order=int(display_order),
                metadata=dict(metadata or {}),
            )
            self._collections[collection_id] = collection
            _evict_fifo_dict(self._collections, _MAX_COLLECTIONS)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.COLLECTION_REGISTERED.value,
                payload={"collection_id": collection_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "collection": collection.to_dict()}

    def get_collection(self, collection_id: str) -> Dict[str, Any]:
        with self._lock:
            collection = self._collections.get(collection_id)
            if collection is None:
                return {"ok": False, "error": "collection not found"}
            return {"ok": True, "collection": collection.to_dict()}

    def list_collections(
        self,
        visible_only: bool = False,
    ) -> Dict[str, Any]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for collection in self._collections.values():
                if visible_only and not collection.visible:
                    continue
                out.append(collection.to_dict())
            out.sort(key=lambda c: (c.get("display_order", 0), c.get("name", "")))
            return {"ok": True, "collections": out}

    def update_collection(self, collection_id: str, **fields: Any) -> Dict[str, Any]:
        with self._lock:
            collection = self._collections.get(collection_id)
            if collection is None:
                return {"ok": False, "error": "collection not found"}
            for key, value in fields.items():
                if not hasattr(collection, key):
                    continue
                if key == "collection_id":
                    continue
                if key == "entry_ids" and isinstance(value, list):
                    setattr(collection, key, list(value))
                elif key == "metadata" and isinstance(value, dict):
                    merged = dict(collection.metadata)
                    merged.update(value)
                    setattr(collection, key, merged)
                else:
                    setattr(collection, key, value)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.COLLECTION_UPDATED.value,
                payload={"collection_id": collection_id, "fields": list(fields.keys())},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "collection": collection.to_dict()}

    def remove_collection(self, collection_id: str) -> Dict[str, Any]:
        with self._lock:
            if collection_id not in self._collections:
                return {"ok": False, "error": "collection not found"}
            self._collections.pop(collection_id, None)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.COLLECTION_REMOVED.value,
                payload={"collection_id": collection_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True}

    def add_to_collection(self, collection_id: str, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            collection = self._collections.get(collection_id)
            if collection is None:
                return {"ok": False, "error": "collection not found"}
            if entry_id not in self._entries:
                return {"ok": False, "error": "entry not found"}
            if entry_id not in collection.entry_ids:
                collection.entry_ids.append(entry_id)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.COLLECTION_MEMBER_ADDED.value,
                payload={"collection_id": collection_id, "entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "collection": collection.to_dict()}

    def remove_from_collection(self, collection_id: str, entry_id: str) -> Dict[str, Any]:
        with self._lock:
            collection = self._collections.get(collection_id)
            if collection is None:
                return {"ok": False, "error": "collection not found"}
            while entry_id in collection.entry_ids:
                collection.entry_ids.remove(entry_id)
            self._audit.append(CodexEvent(
                kind=CodexEventKind.COLLECTION_MEMBER_REMOVED.value,
                payload={"collection_id": collection_id, "entry_id": entry_id},
            ))
            _evict_fifo_list(self._audit, _MAX_EVENTS)
            return {"ok": True, "collection": collection.to_dict()}

    # ------------------------------------------------------------------
    # Search and Statistics
    # ------------------------------------------------------------------

    def search_entries(
        self,
        query: str,
        category_id: str = "",
        status: str = "",
        limit: int = 50,
    ) -> Dict[str, Any]:
        with self._lock:
            query_norm = (query or "").strip().lower()
            tokens = [t for t in query_norm.split() if t]
            results: List[Dict[str, Any]] = []
            for entry in self._entries.values():
                if category_id and entry.category_id != category_id:
                    continue
                if status and entry.status != status:
                    continue
                haystack = " ".join([
                    entry.title,
                    entry.summary,
                    entry.body,
                    " ".join(entry.tags),
                ]).lower()
                if tokens and not all(token in haystack for token in tokens):
                    continue
                results.append(entry.to_dict())
            results.sort(key=lambda e: (
                -_RARITY_RANK.get(e.get("rarity", ""), 0),
                e.get("title", ""),
            ))
            total = len(results)
            limit = max(1, min(int(limit), 200))
            results = results[:limit]
            return {"ok": True, "results": results, "total": total}

    def get_completion_stats(self, category_id: str = "") -> Dict[str, Any]:
        with self._lock:
            stats: Dict[str, Any] = {}
            overall_total = 0
            overall_completed = 0
            for cat_id, category in self._categories.items():
                if category_id and cat_id != category_id:
                    continue
                total = 0
                completed = 0
                discovered = 0
                partial = 0
                locked = 0
                for entry in self._entries.values():
                    if entry.category_id != cat_id:
                        continue
                    total += 1
                    if entry.status == CodexEntryStatus.COMPLETED.value:
                        completed += 1
                    elif entry.status == CodexEntryStatus.DISCOVERED.value:
                        discovered += 1
                    elif entry.status == CodexEntryStatus.PARTIAL.value:
                        partial += 1
                    elif entry.status == CodexEntryStatus.LOCKED.value:
                        locked += 1
                completion = (completed / total) if total > 0 else 0.0
                stats[cat_id] = {
                    "category_name": category.name,
                    "total": total,
                    "completed": completed,
                    "discovered": discovered,
                    "partial": partial,
                    "locked": locked,
                    "completion": round(completion, 4),
                }
                overall_total += total
                overall_completed += completed
            overall_completion = (
                overall_completed / overall_total if overall_total > 0 else 0.0
            )
            return {
                "ok": True,
                "categories": stats,
                "overall": {
                    "total": overall_total,
                    "completed": overall_completed,
                    "completion": round(overall_completion, 4),
                },
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(
        self,
        kind: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        with self._lock:
            out: List[Dict[str, Any]] = []
            for event in self._audit:
                if kind and event.kind != kind:
                    continue
                out.append(event.to_dict())
            out.reverse()
            total = len(out)
            limit = max(1, min(int(limit), 500))
            offset = max(0, int(offset))
            out = out[offset:offset + limit]
            return {"ok": True, "events": out, "total": total}

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_discovered = sum(
                1 for e in self._entries.values()
                if e.status != CodexEntryStatus.LOCKED.value
            )
            total_completed = sum(
                1 for e in self._entries.values()
                if e.status == CodexEntryStatus.COMPLETED.value
            )
            total_archived = sum(
                1 for e in self._entries.values()
                if e.status == CodexEntryStatus.ARCHIVED.value
            )
            stats = CodexStats(
                total_categories=len(self._categories),
                total_entries=len(self._entries),
                total_collections=len(self._collections),
                total_discovered=total_discovered,
                total_completed=total_completed,
                total_archived=total_archived,
            )
            return {"ok": True, "stats": stats.to_dict()}

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "categories": len(self._categories),
                "entries": len(self._entries),
                "collections": len(self._collections),
                "events": len(self._audit),
            }

    def get_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            snapshot = CodexSnapshot(
                categories={k: v.to_dict() for k, v in self._categories.items()},
                entries={k: v.to_dict() for k, v in self._entries.items()},
                collections={k: v.to_dict() for k, v in self._collections.items()},
                stats=self.get_stats().get("stats", {}),
            )
            return {"ok": True, "snapshot": snapshot.to_dict()}

    def reset(self) -> Dict[str, Any]:
        with self._lock:
            self._categories.clear()
            self._entries.clear()
            self._collections.clear()
            self._audit.clear()
            self._initialized = False
            self._initialize()
            return {"ok": True, "status": self.get_status()}


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_codex_system() -> CodexSystem:
    """Return the singleton CodexSystem instance."""
    return CodexSystem.get_instance()
