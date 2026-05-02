"""
Inventory System - Item management with categories, stacking, and equipping.

Architecture:
    InventorySystem/
    |-- ItemCategory (item classification enumeration)
    |-- ItemRarity (rarity tier classification)
    |-- EquipmentSlot (equippable slot positions)
    |-- Item (item definition dataclass)
    |-- InventorySlot (slot with item and quantity)
    |-- Inventory (per-entity inventory container)
    |-- InventorySystem (global inventory orchestration)
    |-- TransferResult (cross-inventory transfer outcome)

Manages game items with full lifecycle: creation, stacking, categorization,
equipping/unequipping, sorting, filtering, and cross-inventory transfers.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Set, Tuple


class ItemCategory(Enum):
    WEAPON = auto()
    ARMOR = auto()
    CONSUMABLE = auto()
    KEY_ITEM = auto()
    MATERIAL = auto()
    QUEST_ITEM = auto()
    TOOL = auto()
    COSMETIC = auto()
    MISC = auto()


class ItemRarity(Enum):
    COMMON = auto()
    UNCOMMON = auto()
    RARE = auto()
    EPIC = auto()
    LEGENDARY = auto()
    MYTHIC = auto()

    @property
    def color_hex(self) -> str:
        return {
            ItemRarity.COMMON: "#aaaaaa",
            ItemRarity.UNCOMMON: "#1eff00",
            ItemRarity.RARE: "#0070dd",
            ItemRarity.EPIC: "#a335ee",
            ItemRarity.LEGENDARY: "#ff8000",
            ItemRarity.MYTHIC: "#e6cc80",
        }.get(self, "#ffffff")


class EquipmentSlot(Enum):
    HEAD = auto()
    CHEST = auto()
    LEGS = auto()
    FEET = auto()
    MAIN_HAND = auto()
    OFF_HAND = auto()
    ACCESSORY_1 = auto()
    ACCESSORY_2 = auto()
    BACK = auto()
    HANDS = auto()
    WAIST = auto()


@dataclass
class Item:
    item_id: str = ""
    name: str = "Unknown Item"
    description: str = ""
    category: ItemCategory = ItemCategory.MISC
    rarity: ItemRarity = ItemRarity.COMMON
    stackable: bool = True
    max_stack: int = 99
    weight: float = 0.0
    value: int = 0
    level_requirement: int = 0
    equipment_slot: Optional[EquipmentSlot] = None
    properties: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    icon_path: str = ""
    use_effect: Optional[str] = None
    is_unique: bool = False

    def __post_init__(self):
        if not self.item_id:
            self.item_id = uuid.uuid4().hex[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "description": self.description,
            "category": self.category.name.lower(),
            "rarity": self.rarity.name.lower(),
            "rarity_color": self.rarity.color_hex,
            "stackable": self.stackable,
            "max_stack": self.max_stack,
            "weight": self.weight,
            "value": self.value,
            "equipment_slot": self.equipment_slot.name.lower() if self.equipment_slot else None,
            "properties": self.properties,
            "tags": self.tags,
            "is_unique": self.is_unique,
        }


@dataclass
class InventorySlot:
    item: Item
    quantity: int = 1

    @property
    def is_full(self) -> bool:
        return self.quantity >= self.item.max_stack

    @property
    def available_space(self) -> int:
        if not self.item.stackable:
            return 0
        return max(0, self.item.max_stack - self.quantity)

    def add(self, amount: int) -> int:
        space = self.available_space
        to_add = min(amount, space)
        self.quantity += to_add
        return amount - to_add

    def remove(self, amount: int) -> Tuple[int, int]:
        to_remove = min(amount, self.quantity)
        self.quantity -= to_remove
        return to_remove, self.quantity

    def to_dict(self) -> Dict[str, Any]:
        return {
            "item": self.item.to_dict(),
            "quantity": self.quantity,
            "is_full": self.is_full,
            "available_space": self.available_space,
        }


class Inventory:
    """Per-entity inventory container with capacity management."""

    def __init__(self, owner_id: str, max_slots: int = 20, max_weight: float = 100.0):
        self.owner_id = owner_id
        self.max_slots = max_slots
        self.max_weight = max_weight
        self._slots: List[InventorySlot] = []
        self._gold: int = 0
        self._equipment: Dict[EquipmentSlot, Item] = {}
        self._on_change_callbacks: List[callable] = []

    @property
    def slot_count(self) -> int:
        return len(self._slots)

    @property
    def is_full(self) -> bool:
        return len(self._slots) >= self.max_slots

    @property
    def current_weight(self) -> float:
        return sum(s.item.weight * s.quantity for s in self._slots)

    @property
    def is_overweight(self) -> bool:
        return self.current_weight > self.max_weight

    @property
    def gold(self) -> int:
        return self._gold

    def on_change(self, callback: callable) -> None:
        self._on_change_callbacks.append(callback)

    def _notify_change(self) -> None:
        for cb in self._on_change_callbacks:
            try:
                cb(self)
            except Exception:
                pass

    def add_item(self, item: Item, quantity: int = 1) -> Tuple[int, int]:
        """Add item(s) to inventory. Returns (added, remaining)."""
        if quantity <= 0:
            return 0, quantity

        remaining = quantity
        added = 0

        if item.stackable:
            for slot in self._slots:
                if slot.item.item_id == item.item_id and not slot.is_full:
                    remaining = slot.add(remaining)
                    added = quantity - remaining
                    if remaining == 0:
                        break

        while remaining > 0 and not self.is_full:
            stack_qty = min(remaining, item.max_stack)
            self._slots.append(InventorySlot(item=item, quantity=stack_qty))
            remaining -= stack_qty
            added += stack_qty

        self._notify_change()
        return added, remaining

    def remove_item(self, item_id: str, quantity: int = 1) -> Tuple[int, bool]:
        """Remove item(s) from inventory. Returns (removed, completely_removed)."""
        to_remove = quantity
        removed = 0

        self._slots = [s for s in self._slots if not (
            s.item.item_id == item_id and to_remove > 0 and not (
                removed := removed + s.remove(min(to_remove, s.quantity))[0]
            ) and (
                to_remove := to_remove - min(to_remove, s.quantity)
            ) and s.quantity == 0
        )]

        self._slots = [s for s in self._slots if s.quantity > 0]

        self._notify_change()
        return removed, removed >= quantity

    def has_item(self, item_id: str, quantity: int = 1) -> bool:
        total = sum(s.quantity for s in self._slots if s.item.item_id == item_id)
        return total >= quantity

    def get_item_count(self, item_id: str) -> int:
        return sum(s.quantity for s in self._slots if s.item.item_id == item_id)

    def get_slots_by_category(self, category: ItemCategory) -> List[InventorySlot]:
        return [s for s in self._slots if s.item.category == category]

    def get_slots_by_tag(self, tag: str) -> List[InventorySlot]:
        return [s for s in self._slots if tag in s.item.tags]

    def equip(self, item_id: str) -> bool:
        """Equip an item from inventory."""
        for slot in self._slots:
            if slot.item.item_id == item_id and slot.item.equipment_slot:
                equip_slot = slot.item.equipment_slot
                old_equipped = self._equipment.get(equip_slot)
                if old_equipped:
                    self.add_item(old_equipped, 1)
                self._equipment[equip_slot] = slot.item
                self.remove_item(item_id, 1)
                self._notify_change()
                return True
        return False

    def unequip(self, slot: EquipmentSlot) -> Optional[Item]:
        """Unequip an item and return it to inventory."""
        if slot in self._equipment:
            item = self._equipment.pop(slot)
            self.add_item(item, 1)
            self._notify_change()
            return item
        return None

    def get_equipped(self, slot: EquipmentSlot) -> Optional[Item]:
        return self._equipment.get(slot)

    def get_all_equipped(self) -> Dict[EquipmentSlot, Item]:
        return dict(self._equipment)

    def add_gold(self, amount: int) -> int:
        self._gold = max(0, self._gold + amount)
        self._notify_change()
        return self._gold

    def remove_gold(self, amount: int) -> bool:
        if self._gold >= amount:
            self._gold -= amount
            self._notify_change()
            return True
        return False

    def sort(self, by: str = "name") -> None:
        key_map = {
            "name": lambda s: s.item.name.lower(),
            "category": lambda s: s.item.category.value,
            "rarity": lambda s: s.item.rarity.value,
            "quantity": lambda s: -s.quantity,
            "weight": lambda s: s.item.weight,
            "value": lambda s: -s.item.value,
        }
        key_fn = key_map.get(by, key_map["name"])
        self._slots.sort(key=key_fn)

    def clear(self) -> None:
        self._slots.clear()
        self._equipment.clear()
        self._gold = 0
        self._notify_change()

    def get_all_slots(self) -> List[InventorySlot]:
        return list(self._slots)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner_id": self.owner_id,
            "max_slots": self.max_slots,
            "max_weight": self.max_weight,
            "slot_count": len(self._slots),
            "is_full": self.is_full,
            "current_weight": round(self.current_weight, 2),
            "is_overweight": self.is_overweight,
            "gold": self._gold,
            "equipped": {k.name.lower(): v.item_id for k, v in self._equipment.items()},
            "slots": [s.to_dict() for s in self._slots],
        }


@dataclass
class TransferResult:
    success: bool
    amount_transferred: int
    source_remaining: int
    destination_added: int
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "amount_transferred": self.amount_transferred,
            "error": self.error_message,
        }


class InventorySystem:
    """Global inventory orchestration system."""

    _instance: Optional["InventorySystem"] = None

    def __init__(self):
        self._inventories: Dict[str, Inventory] = {}
        self._item_registry: Dict[str, Item] = {}
        self._total_created = 0
        self._total_transfers = 0

    @classmethod
    def get_instance(cls) -> "InventorySystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_item(self, item: Item) -> None:
        self._item_registry[item.item_id] = item

    def get_item_definition(self, item_id: str) -> Optional[Item]:
        return self._item_registry.get(item_id)

    def create_item(self, name: str, category: ItemCategory = ItemCategory.MISC,
                    rarity: ItemRarity = ItemRarity.COMMON,
                    properties: Optional[Dict[str, Any]] = None) -> Item:
        item = Item(
            name=name, category=category, rarity=rarity,
            properties=properties or {},
        )
        self._item_registry[item.item_id] = item
        self._total_created += 1
        return item

    def create_inventory(self, owner_id: str, max_slots: int = 20,
                         max_weight: float = 100.0) -> Inventory:
        inv = Inventory(owner_id=owner_id, max_slots=max_slots, max_weight=max_weight)
        self._inventories[owner_id] = inv
        return inv

    def get_inventory(self, owner_id: str) -> Optional[Inventory]:
        return self._inventories.get(owner_id)

    def get_or_create_inventory(self, owner_id: str) -> Inventory:
        if owner_id not in self._inventories:
            return self.create_inventory(owner_id)
        return self._inventories[owner_id]

    def remove_inventory(self, owner_id: str) -> bool:
        if owner_id in self._inventories:
            del self._inventories[owner_id]
            return True
        return False

    def transfer(self, source_id: str, target_id: str, item_id: str,
                 quantity: int = 1) -> TransferResult:
        """Transfer items between two inventories."""
        self._total_transfers += 1

        source = self._inventories.get(source_id)
        target = self._inventories.get(target_id)

        if not source:
            return TransferResult(False, 0, 0, 0, f"Source inventory '{source_id}' not found")
        if not target:
            return TransferResult(False, 0, 0, 0, f"Target inventory '{target_id}' not found")

        if not source.has_item(item_id, quantity):
            return TransferResult(False, 0, 0, 0,
                                  f"Source does not have enough of item '{item_id}'")

        item_def = self._item_registry.get(item_id)
        if not item_def:
            for slot in source._slots:
                if slot.item.item_id == item_id:
                    item_def = slot.item
                    break

        if not item_def:
            return TransferResult(False, 0, 0, 0, f"Item '{item_id}' not found")

        removed, _ = source.remove_item(item_id, quantity)
        added, remaining = target.add_item(item_def, removed)

        if remaining > 0:
            source.add_item(item_def, remaining)

        return TransferResult(
            success=remaining == 0,
            amount_transferred=added,
            source_remaining=source.get_item_count(item_id),
            destination_added=added,
        )

    def list_registered_items(self, category: Optional[ItemCategory] = None) -> List[Dict[str, Any]]:
        items = list(self._item_registry.values())
        if category:
            items = [i for i in items if i.category == category]
        return [i.to_dict() for i in items]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "inventory_count": len(self._inventories),
            "registered_items": len(self._item_registry),
            "total_created": self._total_created,
            "total_transfers": self._total_transfers,
            "total_items_across_inventories": sum(
                sum(s.quantity for s in inv._slots) for inv in self._inventories.values()
            ),
        }


def get_inventory_system() -> InventorySystem:
    return InventorySystem.get_instance()
