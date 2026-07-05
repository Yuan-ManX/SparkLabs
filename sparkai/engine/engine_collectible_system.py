"""
SparkLabs Engine - Collectible System

Tracks collectible items that players discover and acquire throughout a
game. A collectible is a special item with a rarity tier, a category,
optional set membership, and acquisition conditions. The system
maintains per-player collection state, computes completion percentages,
and fires collection rewards when thresholds are met.

Architecture:
  CollectibleSystem (singleton)
    |-- CollectibleItem, CollectibleSet, CollectibleReward,
        CollectionState, AcquisitionRecord, CollectibleStats,
        CollectibleSnapshot, CollectibleEvent
    |-- CollectibleRarity, CollectibleCategory, RewardType,
        CollectibleEventKind

Core Capabilities:
  - register_collectible / update_collectible / get_collectible /
    list_collectibles / delete_collectible: collectible catalog
    management with rarity tiers, categories, and set membership.
  - create_set / update_set / get_set / list_sets: collection set
    definitions with completion thresholds and rewards.
  - create_reward / list_rewards / get_reward: reward definitions
    that fire when collection milestones are reached.
  - acquire / list_acquisitions / get_collection_state: per-player
    collection tracking with discovery timestamps and completion rates.
  - check_rewards / grant_reward: evaluate and grant collection rewards.
  - get_completion / get_set_completion: compute collection completion
    percentages at global and per-set levels.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


_MAX_COLLECTIBLES: int = 2000
_MAX_SETS: int = 200
_MAX_REWARDS: int = 500
_MAX_PLAYERS: int = 1000
_MAX_ACQUISITIONS_PER_PLAYER: int = 2000
_MAX_EVENTS: int = 5000


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


class CollectibleRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CollectibleCategory(Enum):
    COIN = "coin"
    GEM = "gem"
    ARTIFACT = "artifact"
    DOCUMENT = "document"
    KEY_ITEM = "key_item"
    COSMETIC = "cosmetic"
    RECIPE = "recipe"
    CARD = "card"
    FIGURINE = "figurine"
    STAMP = "stamp"
    MUSIC_TRACK = "music_track"
    CONCEPT_ART = "concept_art"
    CUSTOM = "custom"


class RewardType(Enum):
    UNLOCK_ITEM = "unlock_item"
    UNLOCK_ABILITY = "unlock_ability"
    UNLOCK_AREA = "unlock_area"
    UNLOCK_COSMETIC = "unlock_cosmetic"
    GIVE_CURRENCY = "give_currency"
    GIVE_EXPERIENCE = "give_experience"
    ACHIEVEMENT = "achievement"
    LORE_REVEAL = "lore_reveal"
    CUSTOM = "custom"


class CollectibleEventKind(Enum):
    COLLECTIBLE_REGISTERED = "collectible_registered"
    COLLECTIBLE_UPDATED = "collectible_updated"
    COLLECTIBLE_REMOVED = "collectible_removed"
    SET_CREATED = "set_created"
    SET_UPDATED = "set_updated"
    REWARD_CREATED = "reward_created"
    COLLECTIBLE_ACQUIRED = "collectible_acquired"
    REWARD_GRANTED = "reward_granted"
    SET_COMPLETED = "set_completed"
    COLLECTION_COMPLETED = "collection_completed"


@dataclass
class CollectibleItem:
    collectible_id: str
    name: str
    description: str = ""
    rarity: CollectibleRarity = CollectibleRarity.COMMON
    category: CollectibleCategory = CollectibleCategory.CUSTOM
    set_id: str = ""
    icon: str = ""
    model: str = ""
    lore_text: str = ""
    location_hint: str = ""
    acquisition_condition: str = ""
    is_hidden: bool = False
    is_unique: bool = False
    value: int = 0
    weight: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectibleSet:
    set_id: str
    name: str
    description: str = ""
    collectible_ids: List[str] = field(default_factory=list)
    completion_reward_ids: List[str] = field(default_factory=list)
    icon: str = ""
    is_hidden: bool = False
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectibleReward:
    reward_id: str
    name: str
    reward_type: RewardType = RewardType.CUSTOM
    description: str = ""
    target_id: str = ""
    quantity: int = 1
    trigger_type: str = "set_completion"
    trigger_set_id: str = ""
    trigger_threshold: float = 1.0
    is_granted: bool = False
    granted_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class AcquisitionRecord:
    acquisition_id: str
    player_id: str
    collectible_id: str
    acquired_at: str = field(default_factory=_now)
    location: str = ""
    method: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectionState:
    player_id: str
    acquired_collectible_ids: List[str] = field(default_factory=list)
    completed_set_ids: List[str] = field(default_factory=list)
    granted_reward_ids: List[str] = field(default_factory=list)
    total_collected: int = 0
    completion_percentage: float = 0.0
    last_acquired_at: str = ""
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectibleStats:
    total_collectibles: int = 0
    total_sets: int = 0
    total_rewards: int = 0
    total_players: int = 0
    total_acquisitions: int = 0
    total_events: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectibleSnapshot:
    collectibles: List[Dict[str, Any]] = field(default_factory=list)
    sets: List[Dict[str, Any]] = field(default_factory=list)
    rewards: List[Dict[str, Any]] = field(default_factory=list)
    players: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CollectibleEvent:
    event_id: str
    kind: CollectibleEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


class CollectibleSystem:
    """Engine module for tracking collectible items and collection completion."""

    _instance: Optional["CollectibleSystem"] = None
    _inner_lock = threading.RLock()
    _initialized: bool = False

    def __new__(cls) -> "CollectibleSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "CollectibleSystem":
        return cls()

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._collectibles: Dict[str, CollectibleItem] = {}
            self._sets: Dict[str, CollectibleSet] = {}
            self._rewards: Dict[str, CollectibleReward] = {}
            self._players: Dict[str, CollectionState] = {}
            self._acquisitions: Dict[str, List[AcquisitionRecord]] = {}
            self._events: List[CollectibleEvent] = []
            self._seed_data()
            self._initialized = True

    def _emit(self, kind: CollectibleEventKind, data: Dict[str, Any]) -> None:
        event = CollectibleEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def register_collectible(self, name: str, description: str = "",
                             rarity: CollectibleRarity = CollectibleRarity.COMMON,
                             category: CollectibleCategory = CollectibleCategory.CUSTOM,
                             set_id: str = "", icon: str = "", model: str = "",
                             lore_text: str = "", location_hint: str = "",
                             acquisition_condition: str = "",
                             is_hidden: bool = False, is_unique: bool = False,
                             value: int = 0, weight: float = 0.0,
                             metadata: Dict[str, Any] = None) -> CollectibleItem:
        with self._lock:
            item = CollectibleItem(
                collectible_id=_new_id("col"),
                name=name,
                description=description,
                rarity=rarity,
                category=category,
                set_id=set_id,
                icon=icon,
                model=model,
                lore_text=lore_text,
                location_hint=location_hint,
                acquisition_condition=acquisition_condition,
                is_hidden=is_hidden,
                is_unique=is_unique,
                value=value,
                weight=weight,
                metadata=metadata or {},
            )
            self._collectibles[item.collectible_id] = item
            _evict_fifo_dict(self._collectibles, _MAX_COLLECTIBLES)
            if set_id and set_id in self._sets:
                s = self._sets[set_id]
                if item.collectible_id not in s.collectible_ids:
                    s.collectible_ids.append(item.collectible_id)
                    s.updated_at = _now()
            self._emit(CollectibleEventKind.COLLECTIBLE_REGISTERED, {"collectible_id": item.collectible_id})
            return item

    def update_collectible(self, collectible_id: str, updates: Dict[str, Any]) -> Optional[CollectibleItem]:
        with self._lock:
            item = self._collectibles.get(collectible_id)
            if item is None:
                return None
            for k, v in updates.items():
                if k == "rarity" and isinstance(v, str):
                    try:
                        v = CollectibleRarity(v)
                    except ValueError:
                        continue
                elif k == "category" and isinstance(v, str):
                    try:
                        v = CollectibleCategory(v)
                    except ValueError:
                        continue
                if hasattr(item, k) and k not in ("collectible_id", "created_at"):
                    setattr(item, k, v)
            item.updated_at = _now()
            self._emit(CollectibleEventKind.COLLECTIBLE_UPDATED, {"collectible_id": collectible_id})
            return item

    def get_collectible(self, collectible_id: str) -> Optional[CollectibleItem]:
        with self._lock:
            return self._collectibles.get(collectible_id)

    def list_collectibles(self, rarity: CollectibleRarity = None,
                          category: CollectibleCategory = None,
                          set_id: str = None,
                          hidden: bool = None) -> List[CollectibleItem]:
        with self._lock:
            items = list(self._collectibles.values())
            if rarity is not None:
                items = [i for i in items if i.rarity == rarity]
            if category is not None:
                items = [i for i in items if i.category == category]
            if set_id is not None:
                items = [i for i in items if i.set_id == set_id]
            if hidden is not None:
                items = [i for i in items if i.is_hidden == hidden]
            return items

    def delete_collectible(self, collectible_id: str) -> bool:
        with self._lock:
            if collectible_id not in self._collectibles:
                return False
            del self._collectibles[collectible_id]
            for s in self._sets.values():
                if collectible_id in s.collectible_ids:
                    s.collectible_ids.remove(collectible_id)
                    s.updated_at = _now()
            self._emit(CollectibleEventKind.COLLECTIBLE_REMOVED, {"collectible_id": collectible_id})
            return True

    def create_set(self, name: str, description: str = "",
                   collectible_ids: List[str] = None,
                   icon: str = "", is_hidden: bool = False) -> CollectibleSet:
        with self._lock:
            s = CollectibleSet(
                set_id=_new_id("set"),
                name=name,
                description=description,
                collectible_ids=collectible_ids or [],
                icon=icon,
                is_hidden=is_hidden,
            )
            self._sets[s.set_id] = s
            _evict_fifo_dict(self._sets, _MAX_SETS)
            for cid in s.collectible_ids:
                item = self._collectibles.get(cid)
                if item and not item.set_id:
                    item.set_id = s.set_id
                    item.updated_at = _now()
            self._emit(CollectibleEventKind.SET_CREATED, {"set_id": s.set_id})
            return s

    def update_set(self, set_id: str, updates: Dict[str, Any]) -> Optional[CollectibleSet]:
        with self._lock:
            s = self._sets.get(set_id)
            if s is None:
                return None
            for k, v in updates.items():
                if hasattr(s, k) and k not in ("set_id", "created_at"):
                    setattr(s, k, v)
            s.updated_at = _now()
            self._emit(CollectibleEventKind.SET_UPDATED, {"set_id": set_id})
            return s

    def get_set(self, set_id: str) -> Optional[CollectibleSet]:
        with self._lock:
            return self._sets.get(set_id)

    def list_sets(self, hidden: bool = None) -> List[CollectibleSet]:
        with self._lock:
            items = list(self._sets.values())
            if hidden is not None:
                items = [s for s in items if s.is_hidden == hidden]
            return items

    def create_reward(self, name: str, reward_type: RewardType = RewardType.CUSTOM,
                      description: str = "", target_id: str = "", quantity: int = 1,
                      trigger_type: str = "set_completion",
                      trigger_set_id: str = "",
                      trigger_threshold: float = 1.0,
                      metadata: Dict[str, Any] = None) -> CollectibleReward:
        with self._lock:
            reward = CollectibleReward(
                reward_id=_new_id("rwd"),
                name=name,
                reward_type=reward_type,
                description=description,
                target_id=target_id,
                quantity=quantity,
                trigger_type=trigger_type,
                trigger_set_id=trigger_set_id,
                trigger_threshold=trigger_threshold,
                metadata=metadata or {},
            )
            self._rewards[reward.reward_id] = reward
            _evict_fifo_dict(self._rewards, _MAX_REWARDS)
            if trigger_set_id and trigger_set_id in self._sets:
                s = self._sets[trigger_set_id]
                if reward.reward_id not in s.completion_reward_ids:
                    s.completion_reward_ids.append(reward.reward_id)
                    s.updated_at = _now()
            self._emit(CollectibleEventKind.REWARD_CREATED, {"reward_id": reward.reward_id})
            return reward

    def list_rewards(self, trigger_set_id: str = None) -> List[CollectibleReward]:
        with self._lock:
            items = list(self._rewards.values())
            if trigger_set_id is not None:
                items = [r for r in items if r.trigger_set_id == trigger_set_id]
            return items

    def get_reward(self, reward_id: str) -> Optional[CollectibleReward]:
        with self._lock:
            return self._rewards.get(reward_id)

    def acquire(self, player_id: str, collectible_id: str,
                location: str = "", method: str = "",
                metadata: Dict[str, Any] = None) -> Optional[AcquisitionRecord]:
        with self._lock:
            if collectible_id not in self._collectibles:
                return None
            state = self._players.get(player_id)
            if state is None:
                state = CollectionState(player_id=player_id)
                self._players[player_id] = state
                _evict_fifo_dict(self._players, _MAX_PLAYERS)
            if collectible_id in state.acquired_collectible_ids:
                return None
            state.acquired_collectible_ids.append(collectible_id)
            state.total_collected = len(state.acquired_collectible_ids)
            state.last_acquired_at = _now()
            state.updated_at = _now()
            total = len(self._collectibles)
            if total > 0:
                state.completion_percentage = round(state.total_collected / total * 100, 2)
            record = AcquisitionRecord(
                acquisition_id=_new_id("acq"),
                player_id=player_id,
                collectible_id=collectible_id,
                location=location,
                method=method,
                metadata=metadata or {},
            )
            if player_id not in self._acquisitions:
                self._acquisitions[player_id] = []
            self._acquisitions[player_id].append(record)
            _evict_fifo_list(self._acquisitions[player_id], _MAX_ACQUISITIONS_PER_PLAYER)
            self._emit(CollectibleEventKind.COLLECTIBLE_ACQUIRED, {
                "player_id": player_id, "collectible_id": collectible_id,
            })
            for s in self._sets.values():
                if collectible_id in s.collectible_ids:
                    set_acquired = [cid for cid in s.collectible_ids if cid in state.acquired_collectible_ids]
                    if len(set_acquired) == len(s.collectible_ids) and s.set_id not in state.completed_set_ids:
                        state.completed_set_ids.append(s.set_id)
                        self._emit(CollectibleEventKind.SET_COMPLETED, {
                            "player_id": player_id, "set_id": s.set_id,
                        })
            if state.completion_percentage >= 100:
                self._emit(CollectibleEventKind.COLLECTION_COMPLETED, {"player_id": player_id})
            return record

    def list_acquisitions(self, player_id: str, limit: int = 100) -> List[AcquisitionRecord]:
        with self._lock:
            records = self._acquisitions.get(player_id, [])
            return list(records[:limit])

    def get_collection_state(self, player_id: str) -> Optional[CollectionState]:
        with self._lock:
            return self._players.get(player_id)

    def get_completion(self, player_id: str) -> Dict[str, Any]:
        with self._lock:
            state = self._players.get(player_id)
            total = len(self._collectibles)
            collected = state.total_collected if state else 0
            percentage = round(collected / total * 100, 2) if total > 0 else 0.0
            return {
                "player_id": player_id,
                "total_collectibles": total,
                "collected": collected,
                "completion_percentage": percentage,
            }

    def get_set_completion(self, player_id: str, set_id: str) -> Dict[str, Any]:
        with self._lock:
            s = self._sets.get(set_id)
            if s is None:
                return {"error": "set not found"}
            state = self._players.get(player_id)
            acquired = set(state.acquired_collectible_ids) if state else set()
            total = len(s.collectible_ids)
            collected = len([cid for cid in s.collectible_ids if cid in acquired])
            percentage = round(collected / total * 100, 2) if total > 0 else 0.0
            return {
                "player_id": player_id,
                "set_id": set_id,
                "set_name": s.name,
                "total_in_set": total,
                "collected_in_set": collected,
                "completion_percentage": percentage,
                "is_completed": collected == total and total > 0,
            }

    def check_rewards(self, player_id: str) -> List[CollectibleReward]:
        with self._lock:
            state = self._players.get(player_id)
            if state is None:
                return []
            newly_granted: List[CollectibleReward] = []
            for reward in self._rewards.values():
                if reward.reward_id in state.granted_reward_ids:
                    continue
                should_grant = False
                if reward.trigger_type == "set_completion" and reward.trigger_set_id:
                    if reward.trigger_set_id in state.completed_set_ids:
                        should_grant = True
                elif reward.trigger_type == "collection_threshold":
                    if state.completion_percentage >= reward.trigger_threshold * 100:
                        should_grant = True
                if should_grant:
                    reward.is_granted = True
                    reward.granted_at = _now()
                    state.granted_reward_ids.append(reward.reward_id)
                    newly_granted.append(reward)
                    self._emit(CollectibleEventKind.REWARD_GRANTED, {
                        "player_id": player_id, "reward_id": reward.reward_id,
                    })
            return newly_granted

    def grant_reward(self, player_id: str, reward_id: str) -> Optional[CollectibleReward]:
        with self._lock:
            reward = self._rewards.get(reward_id)
            if reward is None:
                return None
            state = self._players.get(player_id)
            if state is None:
                state = CollectionState(player_id=player_id)
                self._players[player_id] = state
            if reward_id in state.granted_reward_ids:
                return reward
            reward.is_granted = True
            reward.granted_at = _now()
            state.granted_reward_ids.append(reward_id)
            state.updated_at = _now()
            self._emit(CollectibleEventKind.REWARD_GRANTED, {
                "player_id": player_id, "reward_id": reward_id,
            })
            return reward

    def list_events(self, limit: int = 100) -> List[CollectibleEvent]:
        with self._lock:
            return list(self._events[:limit])

    def get_stats(self) -> CollectibleStats:
        with self._lock:
            return CollectibleStats(
                total_collectibles=len(self._collectibles),
                total_sets=len(self._sets),
                total_rewards=len(self._rewards),
                total_players=len(self._players),
                total_acquisitions=sum(len(v) for v in self._acquisitions.values()),
                total_events=len(self._events),
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_collectibles": len(self._collectibles),
                "total_sets": len(self._sets),
                "total_rewards": len(self._rewards),
                "total_players": len(self._players),
                "total_acquisitions": sum(len(v) for v in self._acquisitions.values()),
                "total_events": len(self._events),
                "capacities": {
                    "max_collectibles": _MAX_COLLECTIBLES,
                    "max_sets": _MAX_SETS,
                    "max_rewards": _MAX_REWARDS,
                    "max_players": _MAX_PLAYERS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_snapshot(self) -> CollectibleSnapshot:
        with self._lock:
            return CollectibleSnapshot(
                collectibles=[c.to_dict() for c in list(self._collectibles.values())[:100]],
                sets=[s.to_dict() for s in list(self._sets.values())[:50]],
                rewards=[r.to_dict() for r in list(self._rewards.values())[:50]],
                players=[p.to_dict() for p in list(self._players.values())[:50]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._collectibles.clear()
            self._sets.clear()
            self._rewards.clear()
            self._players.clear()
            self._acquisitions.clear()
            self._events.clear()
            self._seed_data()

    def _seed_data(self) -> None:
        s1 = self.create_set(
            name="Crystal Shards",
            description="Collect all seven crystal shards scattered across the realm.",
        )
        s2 = self.create_set(
            name="Ancient Tomes",
            description="Discover the lost texts of the old civilization.",
        )

        shard_ids = []
        for i in range(1, 8):
            rarities = [CollectibleRarity.COMMON, CollectibleRarity.UNCOMMON,
                        CollectibleRarity.RARE, CollectibleRarity.EPIC,
                        CollectibleRarity.LEGENDARY]
            item = self.register_collectible(
                name=f"Crystal Shard {i}",
                description=f"The {i}th shard of the legendary crystal.",
                rarity=rarities[i % len(rarities)],
                category=CollectibleCategory.GEM,
                set_id=s1.set_id,
                lore_text=f"Legends say the {i}th shard holds the power of {'fire' if i % 2 else 'ice'}.",
                location_hint=f"Hidden in zone {i}",
                value=100 * i,
            )
            shard_ids.append(item.collectible_id)

        tomes = []
        for i, title in enumerate(["Tome of Fire", "Tome of Water", "Tome of Earth", "Tome of Wind"]):
            item = self.register_collectible(
                name=title,
                description=f"Ancient text containing forgotten knowledge of {'elemental magic'}.",
                rarity=CollectibleRarity.RARE,
                category=CollectibleCategory.DOCUMENT,
                set_id=s2.set_id,
                lore_text=f"Written by the Sage Council, chapter {i+1}.",
                location_hint=f"Found in the Great Library, shelf {i+1}",
                value=500,
            )
            tomes.append(item.collectible_id)

        self.register_collectible(
            name="Golden Coin of Destiny",
            description="A legendary coin said to grant one wish.",
            rarity=CollectibleRarity.MYTHIC,
            category=CollectibleCategory.COIN,
            lore_text="Minted by the gods themselves.",
            is_hidden=True,
            is_unique=True,
            value=99999,
        )

        self.create_reward(
            name="Crystal Power Unlock",
            reward_type=RewardType.UNLOCK_ABILITY,
            description="Unlocks the Crystal Resonance ability.",
            target_id="ability_crystal_resonance",
            trigger_type="set_completion",
            trigger_set_id=s1.set_id,
        )
        self.create_reward(
            name="Ancient Knowledge",
            reward_type=RewardType.LORE_REVEAL,
            description="Reveals the true history of the realm.",
            target_id="lore_ancient_history",
            trigger_type="set_completion",
            trigger_set_id=s2.set_id,
        )
        self.create_reward(
            name="Master Collector",
            reward_type=RewardType.ACHIEVEMENT,
            description="Awarded for collecting 50% of all collectibles.",
            target_id="achievement_master_collector",
            trigger_type="collection_threshold",
            trigger_threshold=0.5,
        )

        self.acquire("player_seed_1", shard_ids[0], location="Zone 1", method="found")
        self.acquire("player_seed_1", shard_ids[1], location="Zone 2", method="found")
        self.acquire("player_seed_1", shard_ids[2], location="Zone 3", method="quest_reward")
        self.acquire("player_seed_1", tomes[0], location="Library", method="found")
        self.acquire("player_seed_1", tomes[1], location="Library", method="found")
        self.check_rewards("player_seed_1")


def get_collectible_system() -> CollectibleSystem:
    """Factory function to get the singleton CollectibleSystem instance."""
    return CollectibleSystem.get_instance()
