"""
SparkLabs Engine - Inventory & Equipment System

A unified inventory and equipment system for the SparkLabs AI-native
game engine. It models slot-based inventories, weighted containers,
equipment loadouts, item stacking, nested containers, and gear sets.
The system tracks every item lifecycle event from acquisition through
use, repair, and disposal, enabling rich RPG and survival gameplay.

Architecture:
  InventorySystem (singleton)
    |-- ItemDefinition, InventoryItem, InventorySlot, EquipmentSlot,
       Loadout, Container, InventoryStats, InventorySnapshot,
       InventoryEvent
    |-- ItemRarity, ItemCategory, EquipmentSlotType, ItemBinding,
       InventoryEventKind

Core Capabilities:
  - register_item / get_item / list_items / update_item / remove_item:
    item definition lifecycle with rarity, category, weight, and tags.
  - create_container / get_container / list_containers / delete_container:
    container lifecycle with capacity, weight limit, and slot grid.
  - add_item_to_container / remove_item_from_container / move_item:
    item placement with stacking, weight enforcement, and slot rules.
  - equip_item / unequip_item / get_equipped / swap_equipment: equipment
    slot management with binding and stat aggregation hooks.
  - create_loadout / get_loadout / apply_loadout / list_loadouts: gear
    set presets for rapid equipment switching.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`InventorySystem.get_instance` or the module-level
:func:`get_inventory_system` factory.
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

_MAX_ITEM_DEFS: int = 5000
_MAX_CONTAINERS: int = 2000
_MAX_ITEMS: int = 20000
_MAX_LOADOUTS: int = 1000
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
    if isinstance(value, (list, tuple)):
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


class ItemRarity(Enum):
    """Rarity tiers that gate item power and drop probability."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"
    CURSED = "cursed"


class ItemCategory(Enum):
    """Top-level classification of items."""
    WEAPON = "weapon"
    ARMOR = "armor"
    ACCESSORY = "accessory"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    TOOL = "tool"
    KEY_ITEM = "key_item"
    CURRENCY = "currency"
    COSMETIC = "cosmetic"
    MISC = "misc"


class EquipmentSlotType(Enum):
    """Equipment slot categories for loadout management."""
    HEAD = "head"
    CHEST = "chest"
    HANDS = "hands"
    LEGS = "legs"
    FEET = "feet"
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    TWO_HAND = "two_hand"
    NECK = "neck"
    RING_1 = "ring_1"
    RING_2 = "ring_2"
    TRINKET = "trinket"
    BACK = "back"
    BELT = "belt"


class ItemBinding(Enum):
    """Binding policy that controls transferability."""
    NONE = "none"
    ON_PICKUP = "on_pickup"
    ON_EQUIP = "on_equip"
    ON_USE = "on_use"
    ACCOUNT = "account"


class InventoryEventKind(Enum):
    """Audit event types emitted by the inventory system."""
    ITEM_REGISTERED = "item_registered"
    ITEM_UPDATED = "item_updated"
    ITEM_REMOVED = "item_removed"
    CONTAINER_CREATED = "container_created"
    CONTAINER_DELETED = "container_deleted"
    ITEM_ADDED = "item_added"
    ITEM_REMOVED_FROM_CONTAINER = "item_removed_from_container"
    ITEM_MOVED = "item_moved"
    ITEM_EQUIPPED = "item_equipped"
    ITEM_UNEQUIPPED = "item_unequipped"
    LOADOUT_CREATED = "loadout_created"
    LOADOUT_APPLIED = "loadout_applied"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ItemDefinition:
    """A canonical item template registered with the system."""
    item_def_id: str = field(default_factory=lambda: _new_id("idf"))
    name: str = ""
    category: str = ItemCategory.MISC.value
    rarity: str = ItemRarity.COMMON.value
    max_stack: int = 1
    weight: float = 0.1
    value: int = 0
    equip_slot: str = ""
    binding: str = ItemBinding.NONE.value
    durability_max: int = 0
    tags: List[str] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    description: str = ""
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InventoryItem:
    """A live item instance placed in a container or equipment slot."""
    item_id: str = field(default_factory=lambda: _new_id("itm"))
    item_def_id: str = ""
    container_id: str = ""
    slot_index: int = 0
    stack_count: int = 1
    durability: int = 0
    custom_name: str = ""
    custom_stats: Dict[str, Any] = field(default_factory=dict)
    bound_owner: str = ""
    acquired_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InventorySlot:
    """A single slot within a container grid."""
    container_id: str = ""
    slot_index: int = 0
    item_id: str = ""
    locked: bool = False
    allowed_categories: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class EquipmentSlot:
    """An equipment slot on an actor with optional occupant."""
    actor_id: str = ""
    slot_type: str = EquipmentSlotType.MAIN_HAND.value
    item_id: str = ""
    locked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Container:
    """A weighted, slotted inventory container owned by an actor."""
    container_id: str = field(default_factory=lambda: _new_id("cnr"))
    name: str = ""
    owner_id: str = ""
    slot_count: int = 30
    weight_limit: float = 100.0
    is_equipment: bool = False
    parent_container_id: str = ""
    created_at: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Loadout:
    """A named equipment preset for rapid switching."""
    loadout_id: str = field(default_factory=lambda: _new_id("ldt"))
    name: str = ""
    actor_id: str = ""
    slot_assignments: Dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InventoryStats:
    """Aggregate counters for the inventory system."""
    total_item_defs: int = 0
    total_containers: int = 0
    total_items: int = 0
    total_loadouts: int = 0
    total_equipped: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InventorySnapshot:
    """Immutable point-in-time capture of inventory state."""
    item_defs: Dict[str, Any] = field(default_factory=dict)
    containers: Dict[str, Any] = field(default_factory=dict)
    items: Dict[str, Any] = field(default_factory=dict)
    loadouts: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InventoryEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = InventoryEventKind.ITEM_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Inventory System Singleton
# ---------------------------------------------------------------------------


class InventorySystem:
    """Singleton system that manages items, containers, and equipment.

    The system maintains item definitions, live item instances, containers,
    equipment slots per actor, and loadout presets. It enforces weight and
    slot constraints, handles stacking, and emits audit events for every
    item lifecycle change.
    """

    _instance: Optional["InventorySystem"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._item_defs: Dict[str, ItemDefinition] = {}
        self._containers: Dict[str, Container] = {}
        self._items: Dict[str, InventoryItem] = {}
        self._equipment: Dict[str, Dict[str, EquipmentSlot]] = {}
        self._loadouts: Dict[str, Loadout] = {}
        self._audit: List[InventoryEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "InventorySystem":
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
            self._seed_default_item_defs()
            self._initialized = True

    def _seed_default_item_defs(self) -> None:
        """Seed a small starter catalog of item definitions."""
        seeds = [
            ("Iron Sword", ItemCategory.WEAPON.value, ItemRarity.COMMON.value,
             1, 5.0, 50, EquipmentSlotType.MAIN_HAND.value, 100),
            ("Steel Helmet", ItemCategory.ARMOR.value, ItemRarity.UNCOMMON.value,
             1, 3.0, 80, EquipmentSlotType.HEAD.value, 120),
            ("Health Potion", ItemCategory.CONSUMABLE.value, ItemRarity.COMMON.value,
             10, 0.5, 25, "", 0),
            ("Iron Ore", ItemCategory.MATERIAL.value, ItemRarity.COMMON.value,
             99, 2.0, 5, "", 0),
            ("Ring of Vigor", ItemCategory.ACCESSORY.value, ItemRarity.RARE.value,
             1, 0.1, 200, EquipmentSlotType.RING_1.value, 0),
        ]
        for name, cat, rar, stack, wt, val, slot, dur in seeds:
            idef = ItemDefinition(
                item_def_id=_new_id("idf"),
                name=name,
                category=cat,
                rarity=rar,
                max_stack=stack,
                weight=wt,
                value=val,
                equip_slot=slot,
                durability_max=dur,
            )
            self._item_defs[idef.item_def_id] = idef
        _evict_fifo_dict(self._item_defs, _MAX_ITEM_DEFS)

    def _emit_event(self, kind: InventoryEventKind, payload: Dict[str, Any]) -> None:
        evt = InventoryEvent(kind=kind.value, payload=payload)
        self._audit.append(evt)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Item Definition Lifecycle
    # ------------------------------------------------------------------

    def register_item(self, item_def_id: str = "", name: str = "",
                      category: Any = ItemCategory.MISC.value,
                      rarity: Any = ItemRarity.COMMON.value,
                      max_stack: int = 1, weight: float = 0.1,
                      value: int = 0, equip_slot: str = "",
                      binding: Any = ItemBinding.NONE.value,
                      durability_max: int = 0, tags: List[str] = None,
                      stats: Dict[str, Any] = None,
                      description: str = "") -> ItemDefinition:
        with self._lock:
            iid = item_def_id or _new_id("idf")
            cat_val = self._coerce_category(category).value
            rar_val = self._coerce_rarity(rarity).value
            bind_val = self._coerce_binding(binding).value
            idef = ItemDefinition(
                item_def_id=iid,
                name=name,
                category=cat_val,
                rarity=rar_val,
                max_stack=max(1, _safe_int(max_stack, 1)),
                weight=max(0.0, _safe_float(weight, 0.1)),
                value=max(0, _safe_int(value, 0)),
                equip_slot=equip_slot,
                binding=bind_val,
                durability_max=max(0, _safe_int(durability_max, 0)),
                tags=list(tags) if tags else [],
                stats=dict(stats) if stats else {},
                description=description,
            )
            self._item_defs[iid] = idef
            _evict_fifo_dict(self._item_defs, _MAX_ITEM_DEFS)
            self._emit_event(InventoryEventKind.ITEM_REGISTERED, {
                "item_def_id": iid, "name": name, "category": cat_val,
            })
            return idef

    def get_item(self, item_def_id: str) -> Optional[ItemDefinition]:
        with self._lock:
            return self._item_defs.get(item_def_id)

    def list_items(self, category: Any = None, rarity: Any = None,
                   limit: int = 100) -> List[ItemDefinition]:
        with self._lock:
            items = list(self._item_defs.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [i for i in items if i.category == cat_val]
            if rarity is not None and rarity != "":
                rar_val = self._coerce_rarity(rarity).value
                items = [i for i in items if i.rarity == rar_val]
            return items[-limit:]

    def update_item(self, item_def_id: str, **kwargs: Any) -> Optional[ItemDefinition]:
        with self._lock:
            idef = self._item_defs.get(item_def_id)
            if idef is None:
                return None
            for key in ("name", "category", "rarity", "max_stack", "weight",
                        "value", "equip_slot", "binding", "durability_max",
                        "tags", "stats", "description"):
                if key in kwargs:
                    val = kwargs[key]
                    if key == "category":
                        val = self._coerce_category(val).value
                    elif key == "rarity":
                        val = self._coerce_rarity(val).value
                    elif key == "binding":
                        val = self._coerce_binding(val).value
                    elif key in ("max_stack", "value", "durability_max"):
                        val = _safe_int(val, getattr(idef, key))
                    elif key == "weight":
                        val = _safe_float(val, getattr(idef, key))
                    elif key in ("tags", "stats"):
                        val = list(val) if key == "tags" else dict(val)
                    setattr(idef, key, val)
            self._emit_event(InventoryEventKind.ITEM_UPDATED, {
                "item_def_id": item_def_id,
            })
            return idef

    def remove_item(self, item_def_id: str) -> bool:
        with self._lock:
            existed = self._item_defs.pop(item_def_id, None) is not None
            if existed:
                self._emit_event(InventoryEventKind.ITEM_REMOVED, {
                    "item_def_id": item_def_id,
                })
            return existed

    # ------------------------------------------------------------------
    # Container Lifecycle
    # ------------------------------------------------------------------

    def create_container(self, container_id: str = "", name: str = "",
                         owner_id: str = "", slot_count: int = 30,
                         weight_limit: float = 100.0,
                         is_equipment: bool = False,
                         parent_container_id: str = "",
                         metadata: Dict[str, Any] = None) -> Container:
        with self._lock:
            cid = container_id or _new_id("cnr")
            container = Container(
                container_id=cid,
                name=name,
                owner_id=owner_id,
                slot_count=max(1, _safe_int(slot_count, 30)),
                weight_limit=max(0.0, _safe_float(weight_limit, 100.0)),
                is_equipment=bool(is_equipment),
                parent_container_id=parent_container_id,
                metadata=dict(metadata) if metadata else {},
            )
            self._containers[cid] = container
            _evict_fifo_dict(self._containers, _MAX_CONTAINERS)
            self._emit_event(InventoryEventKind.CONTAINER_CREATED, {
                "container_id": cid, "owner_id": owner_id,
            })
            return container

    def get_container(self, container_id: str) -> Optional[Container]:
        with self._lock:
            return self._containers.get(container_id)

    def list_containers(self, owner_id: str = "", limit: int = 100) -> List[Container]:
        with self._lock:
            items = list(self._containers.values())
            if owner_id:
                items = [c for c in items if c.owner_id == owner_id]
            return items[-limit:]

    def delete_container(self, container_id: str) -> bool:
        with self._lock:
            existed = self._containers.pop(container_id, None) is not None
            if existed:
                # Orphan items in this container
                for item in self._items.values():
                    if item.container_id == container_id:
                        item.container_id = ""
                        item.slot_index = 0
                self._emit_event(InventoryEventKind.CONTAINER_DELETED, {
                    "container_id": container_id,
                })
            return existed

    # ------------------------------------------------------------------
    # Item Placement
    # ------------------------------------------------------------------

    def add_item_to_container(self, item_def_id: str, container_id: str,
                              stack_count: int = 1, slot_index: int = -1,
                              durability: int = -1, custom_name: str = "",
                              custom_stats: Dict[str, Any] = None,
                              metadata: Dict[str, Any] = None) -> Optional[InventoryItem]:
        with self._lock:
            idef = self._item_defs.get(item_def_id)
            if idef is None:
                return None
            container = self._containers.get(container_id)
            if container is None:
                return None

            count = max(1, _safe_int(stack_count, 1))
            dur = idef.durability_max if durability < 0 else durability

            # Try stacking into existing items of the same definition
            if idef.max_stack > 1:
                for existing in self._items.values():
                    if (existing.item_def_id == item_def_id and
                            existing.container_id == container_id and
                            existing.stack_count < idef.max_stack):
                        space = idef.max_stack - existing.stack_count
                        add = min(space, count)
                        existing.stack_count += add
                        count -= add
                        if count <= 0:
                            self._emit_event(InventoryEventKind.ITEM_ADDED, {
                                "item_id": existing.item_id,
                                "container_id": container_id,
                                "stack_count": existing.stack_count,
                            })
                            return existing

            # Place remaining count into new slots
            if count > 0:
                target_slot = self._resolve_slot(container, slot_index)
                if target_slot is None:
                    return None
                item = InventoryItem(
                    item_id=_new_id("itm"),
                    item_def_id=item_def_id,
                    container_id=container_id,
                    slot_index=target_slot,
                    stack_count=count,
                    durability=dur,
                    custom_name=custom_name,
                    custom_stats=dict(custom_stats) if custom_stats else {},
                    metadata=dict(metadata) if metadata else {},
                )
                # Apply binding policy
                if idef.binding == ItemBinding.ON_PICKUP.value:
                    item.bound_owner = container.owner_id
                self._items[item.item_id] = item
                _evict_fifo_dict(self._items, _MAX_ITEMS)
                self._emit_event(InventoryEventKind.ITEM_ADDED, {
                    "item_id": item.item_id,
                    "container_id": container_id,
                    "stack_count": count,
                })
                return item
            return None

    def _resolve_slot(self, container: Container, preferred: int) -> Optional[int]:
        """Find a free slot in the container."""
        used_slots = {it.slot_index for it in self._items.values()
                      if it.container_id == container.container_id}
        if preferred >= 0 and preferred < container.slot_count:
            if preferred not in used_slots:
                return preferred
        for i in range(container.slot_count):
            if i not in used_slots:
                return i
        return None

    def remove_item_from_container(self, item_id: str) -> bool:
        with self._lock:
            existed = self._items.pop(item_id, None) is not None
            if existed:
                self._emit_event(InventoryEventKind.ITEM_REMOVED_FROM_CONTAINER, {
                    "item_id": item_id,
                })
            return existed

    def move_item(self, item_id: str, target_container_id: str,
                  target_slot: int = -1) -> Optional[InventoryItem]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return None
            target_container = self._containers.get(target_container_id)
            if target_container is None:
                return None
            new_slot = self._resolve_slot(target_container, target_slot)
            if new_slot is None:
                return None
            old_container = item.container_id
            old_slot = item.slot_index
            item.container_id = target_container_id
            item.slot_index = new_slot
            self._emit_event(InventoryEventKind.ITEM_MOVED, {
                "item_id": item_id,
                "from_container": old_container,
                "from_slot": old_slot,
                "to_container": target_container_id,
                "to_slot": new_slot,
            })
            return item

    def get_item_instance(self, item_id: str) -> Optional[InventoryItem]:
        with self._lock:
            return self._items.get(item_id)

    def list_items_in_container(self, container_id: str,
                                limit: int = 100) -> List[InventoryItem]:
        with self._lock:
            items = [it for it in self._items.values()
                     if it.container_id == container_id]
            return items[-limit:]

    def container_weight(self, container_id: str) -> float:
        with self._lock:
            total = 0.0
            for item in self._items.values():
                if item.container_id == container_id:
                    idef = self._item_defs.get(item.item_def_id)
                    if idef:
                        total += idef.weight * item.stack_count
            return round(total, 4)

    # ------------------------------------------------------------------
    # Equipment Management
    # ------------------------------------------------------------------

    def _ensure_actor_equipment(self, actor_id: str) -> Dict[str, EquipmentSlot]:
        if actor_id not in self._equipment:
            slots = {slot.value: EquipmentSlot(actor_id=actor_id, slot_type=slot.value)
                     for slot in EquipmentSlotType}
            self._equipment[actor_id] = slots
        return self._equipment[actor_id]

    def equip_item(self, actor_id: str, item_id: str,
                   slot_type: str = "") -> Optional[EquipmentSlot]:
        with self._lock:
            item = self._items.get(item_id)
            if item is None:
                return None
            idef = self._item_defs.get(item.item_def_id)
            if idef is None:
                return None
            target_slot = slot_type or idef.equip_slot
            if not target_slot:
                return None
            slots = self._ensure_actor_equipment(actor_id)
            slot = slots.get(target_slot)
            if slot is None:
                return None
            if slot.locked:
                return None
            # Apply binding on equip
            if idef.binding == ItemBinding.ON_EQUIP.value:
                item.bound_owner = actor_id
            # Unequip existing occupant
            if slot.item_id:
                self._unequip_internal(actor_id, target_slot)
            slot.item_id = item_id
            # Remove from container (item is now equipped)
            item.container_id = ""
            item.slot_index = -1
            self._emit_event(InventoryEventKind.ITEM_EQUIPPED, {
                "actor_id": actor_id,
                "slot_type": target_slot,
                "item_id": item_id,
            })
            return slot

    def _unequip_internal(self, actor_id: str, slot_type: str) -> bool:
        slots = self._equipment.get(actor_id, {})
        slot = slots.get(slot_type)
        if slot is None or not slot.item_id:
            return False
        item_id = slot.item_id
        slot.item_id = ""
        self._emit_event(InventoryEventKind.ITEM_UNEQUIPPED, {
            "actor_id": actor_id,
            "slot_type": slot_type,
            "item_id": item_id,
        })
        return True

    def unequip_item(self, actor_id: str, slot_type: str,
                     target_container_id: str = "") -> bool:
        with self._lock:
            slots = self._equipment.get(actor_id, {})
            slot = slots.get(slot_type)
            if slot is None or not slot.item_id:
                return False
            item_id = slot.item_id
            slot.item_id = ""
            # Try to place item back into a container
            if target_container_id:
                item = self._items.get(item_id)
                if item:
                    target_container = self._containers.get(target_container_id)
                    if target_container:
                        new_slot = self._resolve_slot(target_container, -1)
                        if new_slot is not None:
                            item.container_id = target_container_id
                            item.slot_index = new_slot
            self._emit_event(InventoryEventKind.ITEM_UNEQUIPPED, {
                "actor_id": actor_id,
                "slot_type": slot_type,
                "item_id": item_id,
            })
            return True

    def swap_equipment(self, actor_id: str, slot_type: str,
                       new_item_id: str) -> Optional[EquipmentSlot]:
        with self._lock:
            slots = self._equipment.get(actor_id, {})
            slot = slots.get(slot_type)
            if slot is None:
                return None
            # Unequip current
            if slot.item_id:
                self._unequip_internal(actor_id, slot_type)
            # Equip new
            return self.equip_item(actor_id, new_item_id, slot_type)

    def get_equipped(self, actor_id: str) -> Dict[str, EquipmentSlot]:
        with self._lock:
            return dict(self._equipment.get(actor_id, {}))

    # ------------------------------------------------------------------
    # Loadout Management
    # ------------------------------------------------------------------

    def create_loadout(self, name: str, actor_id: str = "",
                       slot_assignments: Dict[str, str] = None,
                       loadout_id: str = "") -> Loadout:
        with self._lock:
            lid = loadout_id or _new_id("ldt")
            loadout = Loadout(
                loadout_id=lid,
                name=name,
                actor_id=actor_id,
                slot_assignments=dict(slot_assignments) if slot_assignments else {},
            )
            self._loadouts[lid] = loadout
            _evict_fifo_dict(self._loadouts, _MAX_LOADOUTS)
            self._emit_event(InventoryEventKind.LOADOUT_CREATED, {
                "loadout_id": lid, "name": name,
            })
            return loadout

    def get_loadout(self, loadout_id: str) -> Optional[Loadout]:
        with self._lock:
            return self._loadouts.get(loadout_id)

    def list_loadouts(self, actor_id: str = "", limit: int = 100) -> List[Loadout]:
        with self._lock:
            items = list(self._loadouts.values())
            if actor_id:
                items = [l for l in items if l.actor_id == actor_id]
            return items[-limit:]

    def apply_loadout(self, loadout_id: str, actor_id: str = "") -> Optional[Loadout]:
        with self._lock:
            loadout = self._loadouts.get(loadout_id)
            if loadout is None:
                return None
            target_actor = actor_id or loadout.actor_id
            if not target_actor:
                return None
            # Unequip all current slots
            slots = self._ensure_actor_equipment(target_actor)
            for slot_type in list(slots.keys()):
                self._unequip_internal(target_actor, slot_type)
            # Equip items from the loadout
            for slot_type, item_id in loadout.slot_assignments.items():
                if item_id and item_id in self._items:
                    self.equip_item(target_actor, item_id, slot_type)
            self._emit_event(InventoryEventKind.LOADOUT_APPLIED, {
                "loadout_id": loadout_id,
                "actor_id": target_actor,
            })
            return loadout

    def delete_loadout(self, loadout_id: str) -> bool:
        with self._lock:
            return self._loadouts.pop(loadout_id, None) is not None

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _coerce_category(value: Any) -> ItemCategory:
        if isinstance(value, ItemCategory):
            return value
        if isinstance(value, str):
            for cat in ItemCategory:
                if cat.value == value:
                    return cat
        return ItemCategory.MISC

    @staticmethod
    def _coerce_rarity(value: Any) -> ItemRarity:
        if isinstance(value, ItemRarity):
            return value
        if isinstance(value, str):
            for rar in ItemRarity:
                if rar.value == value:
                    return rar
        return ItemRarity.COMMON

    @staticmethod
    def _coerce_binding(value: Any) -> ItemBinding:
        if isinstance(value, ItemBinding):
            return value
        if isinstance(value, str):
            for bind in ItemBinding:
                if bind.value == value:
                    return bind
        return ItemBinding.NONE

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[InventoryEvent]:
        with self._lock:
            return list(self._audit[-limit:])

    def get_stats(self) -> InventoryStats:
        with self._lock:
            equipped_count = 0
            for slots in self._equipment.values():
                equipped_count += sum(1 for s in slots.values() if s.item_id)
            return InventoryStats(
                total_item_defs=len(self._item_defs),
                total_containers=len(self._containers),
                total_items=len(self._items),
                total_loadouts=len(self._loadouts),
                total_equipped=equipped_count,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "item_defs": len(self._item_defs),
                "containers": len(self._containers),
                "items": len(self._items),
                "loadouts": len(self._loadouts),
                "actors_tracked": len(self._equipment),
                "events": len(self._audit),
            }

    def get_snapshot(self) -> InventorySnapshot:
        with self._lock:
            return InventorySnapshot(
                item_defs={k: v.to_dict() for k, v in self._item_defs.items()},
                containers={k: v.to_dict() for k, v in self._containers.items()},
                items={k: v.to_dict() for k, v in self._items.items()},
                loadouts={k: v.to_dict() for k, v in self._loadouts.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._item_defs.clear()
            self._containers.clear()
            self._items.clear()
            self._equipment.clear()
            self._loadouts.clear()
            self._audit.clear()
            self._initialized = False
            self._initialize()


def get_inventory_system() -> InventorySystem:
    """Module-level factory for the InventorySystem singleton."""
    return InventorySystem.get_instance()
