"""
SparkLabs Agent - Loot Reward Curator

A loot and reward curation agent for the SparkLabs AI-native game engine.
It generates contextual loot tables, schedules reward pulses to maintain
engagement curves, curates rarity rolls against live-ops events, and
adapts drop distribution to per-player reward profiles. The curator
fuses procedural reward design, dopamine pacing, and runtime economy
balance into a single intelligent surface.

Architecture:
  LootRewardCurator (singleton)
    |-- LootEntry, LootTable, RewardPulse, DropPolicy,
       PlayerRewardProfile, CuratorStats, CuratorSnapshot, CuratorEvent
    |-- LootRewardKind, LootRarityTier, CurationStrategy,
       CuratorEventKind

Core Capabilities:
  - register_table / get_table / list_tables / update_table /
    remove_table: loot table lifecycle with weighted entries.
  - add_entry / remove_entry: compose loot tables with rarity and
    weight metadata.
  - roll_loot: deterministic-weighted random roll over a table that
    respects rarity tiers and luck modifiers.
  - register_pulse / get_pulse / list_pulses / remove_pulse: scheduled
    reward pulses that inject generosity into the engagement curve.
  - register_profile / get_profile / list_profiles / update_profile:
    per-player reward profiles that tune drop distribution to
    playstyle, fatigue, and retention signals.
  - curate_for_player: contextual loot generation that fuses the
    active table, profile, and live-ops context.
  - suggest_pulse_timing: predict the next optimal reward pulse based
    on time-since-last-reward and engagement decay.
  - assess_engagement: score engagement from recent reward history.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`LootRewardCurator.get_instance` or the module-level
:func:`get_loot_reward_curator` factory.
"""

from __future__ import annotations

import random
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_TABLES: int = 2000
_MAX_ENTRIES: int = 20000
_MAX_PULSES: int = 1000
_MAX_PROFILES: int = 5000
_MAX_ROLLS_LOG: int = 5000
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


class LootRewardKind(Enum):
    """Functional classification of loot rewards."""
    CURRENCY = "currency"
    ITEM = "item"
    GEAR = "gear"
    COSMETIC = "cosmetic"
    CONSUMABLE = "consumable"
    BLUEPRINT = "blueprint"
    ACHIEVEMENT = "achievement"
    EXPERIENCE = "experience"
    KEY = "key"
    CHEST = "chest"


class LootRarityTier(Enum):
    """Rarity tiers that drive drop probability and visual treatment."""
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


class CurationStrategy(Enum):
    """Strategy that controls how the curator biases drop distribution."""
    BALANCED = "balanced"
    DOPAMINE_SPIKE = "dopamine_spike"
    STINGY = "stingy"
    GENEROUS = "generous"
    ADAPTIVE = "adaptive"


class CuratorEventKind(Enum):
    """Audit event types emitted by the loot reward curator."""
    TABLE_REGISTERED = "table_registered"
    TABLE_UPDATED = "table_updated"
    TABLE_REMOVED = "table_removed"
    ENTRY_ADDED = "entry_added"
    ENTRY_REMOVED = "entry_removed"
    LOOT_ROLLED = "loot_rolled"
    PULSE_REGISTERED = "pulse_registered"
    PULSE_REMOVED = "pulse_removed"
    PULSE_TRIGGERED = "pulse_triggered"
    PROFILE_REGISTERED = "profile_registered"
    PROFILE_UPDATED = "profile_updated"
    CURATION_PERFORMED = "curation_performed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class LootEntry:
    """A single weighted entry inside a loot table."""
    entry_id: str = field(default_factory=lambda: _new_id("ent"))
    reward_kind: str = LootRewardKind.ITEM.value
    reward_id: str = ""
    display_name: str = ""
    rarity: str = LootRarityTier.COMMON.value
    weight: float = 1.0
    min_quantity: int = 1
    max_quantity: int = 1
    luck_multiplier: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class LootTable:
    """A weighted collection of loot entries."""
    table_id: str = field(default_factory=lambda: _new_id("tbl"))
    name: str = ""
    description: str = ""
    strategy: str = CurationStrategy.BALANCED.value
    base_luck: float = 1.0
    entries: List[LootEntry] = field(default_factory=list)
    drop_count_min: int = 1
    drop_count_max: int = 1
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RewardPulse:
    """A scheduled surge of generosity to maintain engagement."""
    pulse_id: str = field(default_factory=lambda: _new_id("pls"))
    name: str = ""
    description: str = ""
    trigger_at_ms: int = 0
    duration_ms: int = 60000
    luck_boost: float = 1.5
    rarity_shift: float = 0.1
    target_table_id: str = ""
    target_player_id: str = ""
    triggered: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DropPolicy:
    """Tuning parameters that govern a single roll."""
    luck: float = 1.0
    rarity_floor: str = LootRarityTier.COMMON.value
    rarity_ceiling: str = LootRarityTier.MYTHIC.value
    strategy_override: str = ""
    pulse_luck_boost: float = 1.0
    pulse_rarity_shift: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlayerRewardProfile:
    """Per-player tuning profile that adapts drop distribution."""
    profile_id: str = field(default_factory=lambda: _new_id("prf"))
    player_id: str = ""
    playstyle: str = "balanced"
    fatigue_score: float = 0.0
    retention_score: float = 0.5
    generosity_bias: float = 0.0
    last_reward_at_ms: int = 0
    recent_legendary_count: int = 0
    total_rolls: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CuratorStats:
    """Aggregate counters for the loot reward curator."""
    total_tables: int = 0
    total_entries: int = 0
    total_pulses: int = 0
    total_profiles: int = 0
    total_rolls: int = 0
    total_curations: int = 0
    total_pulses_triggered: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CuratorSnapshot:
    """Immutable point-in-time capture of curator state."""
    tables: Dict[str, Any] = field(default_factory=dict)
    pulses: Dict[str, Any] = field(default_factory=dict)
    profiles: Dict[str, Any] = field(default_factory=dict)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CuratorEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("aud"))
    kind: str = CuratorEventKind.TABLE_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Static Lookup Tables
# ---------------------------------------------------------------------------

_RARITY_WEIGHTS: Dict[str, float] = {
    LootRarityTier.COMMON.value: 1.0,
    LootRarityTier.UNCOMMON.value: 0.55,
    LootRarityTier.RARE.value: 0.30,
    LootRarityTier.EPIC.value: 0.12,
    LootRarityTier.LEGENDARY.value: 0.04,
    LootRarityTier.MYTHIC.value: 0.01,
}

_RARITY_RANK: Dict[str, int] = {
    LootRarityTier.COMMON.value: 0,
    LootRarityTier.UNCOMMON.value: 1,
    LootRarityTier.RARE.value: 2,
    LootRarityTier.EPIC.value: 3,
    LootRarityTier.LEGENDARY.value: 4,
    LootRarityTier.MYTHIC.value: 5,
}

_STRATEGY_LUCK_BIAS: Dict[str, float] = {
    CurationStrategy.BALANCED.value: 1.0,
    CurationStrategy.DOPAMINE_SPIKE.value: 1.8,
    CurationStrategy.STINGY.value: 0.6,
    CurationStrategy.GENEROUS.value: 1.4,
    CurationStrategy.ADAPTIVE.value: 1.0,
}


# ---------------------------------------------------------------------------
# Loot Reward Curator Singleton
# ---------------------------------------------------------------------------


class LootRewardCurator:
    """Singleton agent that curates loot and schedules reward pulses.

    The curator maintains loot tables, scheduled reward pulses, and
    per-player reward profiles. It performs weighted-random rolls,
    curates contextual loot for specific players, and predicts the
    next optimal reward pulse to maintain engagement.
    """

    _instance: Optional["LootRewardCurator"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._tables: Dict[str, LootTable] = {}
        self._pulses: Dict[str, RewardPulse] = {}
        self._profiles: Dict[str, PlayerRewardProfile] = {}
        self._profiles_by_player: Dict[str, str] = {}
        self._rolls_log: List[Dict[str, Any]] = []
        self._curations_performed: int = 0
        self._pulses_triggered: int = 0
        self._audit: List[CuratorEvent] = []

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "LootRewardCurator":
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

    def _seed_defaults(self) -> None:
        """Seed a small set of default loot tables and a sample profile."""
        # Default combat drop table
        combat_table = LootTable(
            table_id="tbl_combat_drops",
            name="Combat Drops",
            description="Standard loot table for defeated enemies.",
            strategy=CurationStrategy.BALANCED.value,
            base_luck=1.0,
            drop_count_min=1,
            drop_count_max=3,
            tags=["combat", "enemy"],
        )
        combat_table.entries = [
            LootEntry(
                entry_id="ent_gold_small",
                reward_kind=LootRewardKind.CURRENCY.value,
                reward_id="gold",
                display_name="Gold Coins",
                rarity=LootRarityTier.COMMON.value,
                weight=10.0,
                min_quantity=5,
                max_quantity=50,
            ),
            LootEntry(
                entry_id="ent_health_potion",
                reward_kind=LootRewardKind.CONSUMABLE.value,
                reward_id="health_potion",
                display_name="Health Potion",
                rarity=LootRarityTier.UNCOMMON.value,
                weight=4.0,
                min_quantity=1,
                max_quantity=3,
            ),
            LootEntry(
                entry_id="ent_iron_sword",
                reward_kind=LootRewardKind.GEAR.value,
                reward_id="iron_sword",
                display_name="Iron Sword",
                rarity=LootRarityTier.RARE.value,
                weight=1.5,
                min_quantity=1,
                max_quantity=1,
            ),
            LootEntry(
                entry_id="ent_dragon_scale",
                reward_kind=LootRewardKind.ITEM.value,
                reward_id="dragon_scale",
                display_name="Dragon Scale",
                rarity=LootRarityTier.EPIC.value,
                weight=0.4,
                min_quantity=1,
                max_quantity=2,
            ),
            LootEntry(
                entry_id="ent_excalibur",
                reward_kind=LootRewardKind.GEAR.value,
                reward_id="excalibur",
                display_name="Excalibur",
                rarity=LootRarityTier.LEGENDARY.value,
                weight=0.05,
                min_quantity=1,
                max_quantity=1,
            ),
        ]
        self._tables[combat_table.table_id] = combat_table
        self._record_event(CuratorEventKind.TABLE_REGISTERED, {
            "table_id": combat_table.table_id, "name": combat_table.name,
        })
        for entry in combat_table.entries:
            self._record_event(CuratorEventKind.ENTRY_ADDED, {
                "table_id": combat_table.table_id, "entry_id": entry.entry_id,
            })

        # Default boss drop table
        boss_table = LootTable(
            table_id="tbl_boss_drops",
            name="Boss Drops",
            description="High-stakes loot table for boss encounters.",
            strategy=CurationStrategy.DOPAMINE_SPIKE.value,
            base_luck=1.2,
            drop_count_min=2,
            drop_count_max=4,
            tags=["combat", "boss"],
        )
        boss_table.entries = [
            LootEntry(
                entry_id="ent_boss_gold",
                reward_kind=LootRewardKind.CURRENCY.value,
                reward_id="gold",
                display_name="Boss Gold",
                rarity=LootRarityTier.UNCOMMON.value,
                weight=8.0,
                min_quantity=100,
                max_quantity=500,
            ),
            LootEntry(
                entry_id="ent_boss_chest",
                reward_kind=LootRewardKind.CHEST.value,
                reward_id="boss_chest",
                display_name="Boss Chest",
                rarity=LootRarityTier.RARE.value,
                weight=3.0,
                min_quantity=1,
                max_quantity=1,
            ),
            LootEntry(
                entry_id="ent_boss_relic",
                reward_kind=LootRewardKind.ITEM.value,
                reward_id="boss_relic",
                display_name="Ancient Relic",
                rarity=LootRarityTier.LEGENDARY.value,
                weight=0.5,
                min_quantity=1,
                max_quantity=1,
            ),
        ]
        self._tables[boss_table.table_id] = boss_table
        self._record_event(CuratorEventKind.TABLE_REGISTERED, {
            "table_id": boss_table.table_id, "name": boss_table.name,
        })

        # Sample reward pulse
        sample_pulse = RewardPulse(
            pulse_id="pls_welcome",
            name="Welcome Boost",
            description="Generosity pulse for new players in the first hour.",
            trigger_at_ms=300000,
            duration_ms=600000,
            luck_boost=2.0,
            rarity_shift=0.15,
            target_table_id="tbl_combat_drops",
            target_player_id="",
        )
        self._pulses[sample_pulse.pulse_id] = sample_pulse
        self._record_event(CuratorEventKind.PULSE_REGISTERED, {
            "pulse_id": sample_pulse.pulse_id, "name": sample_pulse.name,
        })

        # Sample player profile
        sample_profile = PlayerRewardProfile(
            profile_id="prf_sample_1",
            player_id="player_1",
            playstyle="balanced",
            fatigue_score=0.2,
            retention_score=0.7,
            generosity_bias=0.1,
            last_reward_at_ms=0,
            recent_legendary_count=0,
            total_rolls=0,
        )
        self._profiles[sample_profile.profile_id] = sample_profile
        self._profiles_by_player[sample_profile.player_id] = sample_profile.profile_id
        self._record_event(CuratorEventKind.PROFILE_REGISTERED, {
            "profile_id": sample_profile.profile_id,
            "player_id": sample_profile.player_id,
        })

    # ------------------------------------------------------------------
    # Audit Helpers
    # ------------------------------------------------------------------

    def _record_event(self, kind: CuratorEventKind, payload: Dict[str, Any]) -> None:
        event = CuratorEvent(kind=kind.value, payload=payload)
        self._audit.append(event)
        _evict_fifo_list(self._audit, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Loot Table Lifecycle
    # ------------------------------------------------------------------

    def register_table(
        self,
        table_id: str = "",
        name: str = "",
        description: str = "",
        strategy: str = CurationStrategy.BALANCED.value,
        base_luck: float = 1.0,
        drop_count_min: int = 1,
        drop_count_max: int = 1,
        entries: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> LootTable:
        with self._lock:
            tid = table_id or _new_id("tbl")
            table = LootTable(
                table_id=tid,
                name=name,
                description=description,
                strategy=strategy,
                base_luck=_safe_float(base_luck, 1.0),
                drop_count_min=_safe_int(drop_count_min, 1),
                drop_count_max=_safe_int(drop_count_max, 1),
                tags=list(tags or []),
                metadata=dict(metadata or {}),
            )
            for entry_dict in entries or []:
                table.entries.append(self._build_entry(entry_dict))
            self._tables[tid] = table
            _evict_fifo_dict(self._tables, _MAX_TABLES)
            self._record_event(CuratorEventKind.TABLE_REGISTERED, {
                "table_id": tid, "name": name,
            })
            return table

    def _build_entry(self, data: Dict[str, Any]) -> LootEntry:
        return LootEntry(
            entry_id=data.get("entry_id", "") or _new_id("ent"),
            reward_kind=data.get("reward_kind", LootRewardKind.ITEM.value),
            reward_id=data.get("reward_id", ""),
            display_name=data.get("display_name", ""),
            rarity=data.get("rarity", LootRarityTier.COMMON.value),
            weight=_safe_float(data.get("weight", 1.0), 1.0),
            min_quantity=_safe_int(data.get("min_quantity", 1), 1),
            max_quantity=_safe_int(data.get("max_quantity", 1), 1),
            luck_multiplier=_safe_float(data.get("luck_multiplier", 1.0), 1.0),
            metadata=dict(data.get("metadata", {})),
        )

    def get_table(self, table_id: str) -> Optional[LootTable]:
        with self._lock:
            return self._tables.get(table_id)

    def list_tables(
        self,
        strategy: str = "",
        tag: str = "",
        limit: int = 100,
    ) -> List[LootTable]:
        with self._lock:
            results: List[LootTable] = []
            for table in self._tables.values():
                if strategy and table.strategy != strategy:
                    continue
                if tag and tag not in table.tags:
                    continue
                results.append(table)
            return results[:max(0, int(limit))]

    def update_table(self, table_id: str, **kwargs: Any) -> Optional[LootTable]:
        with self._lock:
            table = self._tables.get(table_id)
            if table is None:
                return None
            for key, value in kwargs.items():
                if hasattr(table, key) and key not in ("table_id", "created_at", "entries"):
                    setattr(table, key, value)
            self._record_event(CuratorEventKind.TABLE_UPDATED, {"table_id": table_id})
            return table

    def remove_table(self, table_id: str) -> bool:
        with self._lock:
            existed = self._tables.pop(table_id, None) is not None
            if existed:
                self._record_event(CuratorEventKind.TABLE_REMOVED, {"table_id": table_id})
            return existed

    # ------------------------------------------------------------------
    # Entry Composition
    # ------------------------------------------------------------------

    def add_entry(self, table_id: str, entry: Dict[str, Any]) -> Optional[LootEntry]:
        with self._lock:
            table = self._tables.get(table_id)
            if table is None:
                return None
            built = self._build_entry(entry)
            table.entries.append(built)
            _evict_fifo_list(table.entries, _MAX_ENTRIES)
            self._record_event(CuratorEventKind.ENTRY_ADDED, {
                "table_id": table_id, "entry_id": built.entry_id,
            })
            return built

    def remove_entry(self, table_id: str, entry_id: str) -> bool:
        with self._lock:
            table = self._tables.get(table_id)
            if table is None:
                return False
            for i, entry in enumerate(table.entries):
                if entry.entry_id == entry_id:
                    table.entries.pop(i)
                    self._record_event(CuratorEventKind.ENTRY_REMOVED, {
                        "table_id": table_id, "entry_id": entry_id,
                    })
                    return True
            return False

    # ------------------------------------------------------------------
    # Loot Rolling
    # ------------------------------------------------------------------

    def roll_loot(
        self,
        table_id: str,
        policy: Optional[DropPolicy] = None,
        seed: Optional[int] = None,
    ) -> List[LootEntry]:
        """Perform a weighted-random roll over a loot table."""
        with self._lock:
            table = self._tables.get(table_id)
            if table is None:
                return []
            policy = policy or DropPolicy()
            rng = random.Random(seed) if seed is not None else random.Random()
            strategy_bias = _STRATEGY_LUCK_BIAS.get(table.strategy, 1.0)
            override_bias = _STRATEGY_LUCK_BIAS.get(policy.strategy_override, 1.0) if policy.strategy_override else strategy_bias
            effective_luck = (
                table.base_luck
                * policy.luck
                * override_bias
                * policy.pulse_luck_boost
            )
            floor_rank = _RARITY_RANK.get(policy.rarity_floor, 0)
            ceiling_rank = _RARITY_RANK.get(policy.rarity_ceiling, 5)
            drop_count = rng.randint(
                max(1, table.drop_count_min),
                max(1, table.drop_count_max),
            )
            rolled: List[LootEntry] = []
            for _ in range(drop_count):
                candidate = self._roll_single(table, effective_luck, policy.pulse_rarity_shift, floor_rank, ceiling_rank, rng)
                if candidate is not None:
                    rolled.append(candidate)
            log_entry = {
                "table_id": table_id,
                "drop_count": len(rolled),
                "luck": effective_luck,
                "rolled_at": _now(),
            }
            self._rolls_log.append(log_entry)
            _evict_fifo_list(self._rolls_log, _MAX_ROLLS_LOG)
            self._record_event(CuratorEventKind.LOOT_ROLLED, log_entry)
            return rolled

    def _roll_single(
        self,
        table: LootTable,
        effective_luck: float,
        rarity_shift: float,
        floor_rank: int,
        ceiling_rank: int,
        rng: random.Random,
    ) -> Optional[LootEntry]:
        if not table.entries:
            return None
        weights: List[float] = []
        candidates: List[LootEntry] = []
        for entry in table.entries:
            rarity_rank = _RARITY_RANK.get(entry.rarity, 0)
            if rarity_rank < floor_rank or rarity_rank > ceiling_rank:
                continue
            base_weight = entry.weight
            rarity_weight = _RARITY_WEIGHTS.get(entry.rarity, 1.0)
            adjusted = (
                base_weight
                * entry.luck_multiplier
                * effective_luck
                * (rarity_weight + rarity_shift)
            )
            weights.append(max(0.0, adjusted))
            candidates.append(entry)
        if not candidates:
            return None
        total = sum(weights)
        if total <= 0:
            return None
        pick = rng.random() * total
        cumulative = 0.0
        for cand, w in zip(candidates, weights):
            cumulative += w
            if pick <= cumulative:
                qty = rng.randint(cand.min_quantity, max(cand.min_quantity, cand.max_quantity))
                rolled = LootEntry(
                    entry_id=cand.entry_id,
                    reward_kind=cand.reward_kind,
                    reward_id=cand.reward_id,
                    display_name=cand.display_name,
                    rarity=cand.rarity,
                    weight=cand.weight,
                    min_quantity=qty,
                    max_quantity=qty,
                    luck_multiplier=cand.luck_multiplier,
                    metadata=dict(cand.metadata),
                )
                return rolled
        return candidates[-1]

    # ------------------------------------------------------------------
    # Reward Pulses
    # ------------------------------------------------------------------

    def register_pulse(
        self,
        pulse_id: str = "",
        name: str = "",
        description: str = "",
        trigger_at_ms: int = 0,
        duration_ms: int = 60000,
        luck_boost: float = 1.5,
        rarity_shift: float = 0.1,
        target_table_id: str = "",
        target_player_id: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> RewardPulse:
        with self._lock:
            pid = pulse_id or _new_id("pls")
            pulse = RewardPulse(
                pulse_id=pid,
                name=name,
                description=description,
                trigger_at_ms=_safe_int(trigger_at_ms, 0),
                duration_ms=_safe_int(duration_ms, 60000),
                luck_boost=_safe_float(luck_boost, 1.5),
                rarity_shift=_safe_float(rarity_shift, 0.1),
                target_table_id=target_table_id,
                target_player_id=target_player_id,
                metadata=dict(metadata or {}),
            )
            self._pulses[pid] = pulse
            _evict_fifo_dict(self._pulses, _MAX_PULSES)
            self._record_event(CuratorEventKind.PULSE_REGISTERED, {
                "pulse_id": pid, "name": name,
            })
            return pulse

    def get_pulse(self, pulse_id: str) -> Optional[RewardPulse]:
        with self._lock:
            return self._pulses.get(pulse_id)

    def list_pulses(
        self,
        target_table_id: str = "",
        target_player_id: str = "",
        triggered: Optional[bool] = None,
        limit: int = 100,
    ) -> List[RewardPulse]:
        with self._lock:
            results: List[RewardPulse] = []
            for pulse in self._pulses.values():
                if target_table_id and pulse.target_table_id != target_table_id:
                    continue
                if target_player_id and pulse.target_player_id not in ("", target_player_id):
                    continue
                if triggered is not None and pulse.triggered != triggered:
                    continue
                results.append(pulse)
            return results[:max(0, int(limit))]

    def remove_pulse(self, pulse_id: str) -> bool:
        with self._lock:
            existed = self._pulses.pop(pulse_id, None) is not None
            if existed:
                self._record_event(CuratorEventKind.PULSE_REMOVED, {"pulse_id": pulse_id})
            return existed

    def trigger_pulse(self, pulse_id: str) -> Optional[RewardPulse]:
        with self._lock:
            pulse = self._pulses.get(pulse_id)
            if pulse is None:
                return None
            pulse.triggered = True
            self._pulses_triggered += 1
            self._record_event(CuratorEventKind.PULSE_TRIGGERED, {"pulse_id": pulse_id})
            return pulse

    # ------------------------------------------------------------------
    # Player Reward Profiles
    # ------------------------------------------------------------------

    def register_profile(
        self,
        profile_id: str = "",
        player_id: str = "",
        playstyle: str = "balanced",
        fatigue_score: float = 0.0,
        retention_score: float = 0.5,
        generosity_bias: float = 0.0,
        last_reward_at_ms: int = 0,
        recent_legendary_count: int = 0,
        total_rolls: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PlayerRewardProfile:
        with self._lock:
            pid = profile_id or _new_id("prf")
            profile = PlayerRewardProfile(
                profile_id=pid,
                player_id=player_id,
                playstyle=playstyle,
                fatigue_score=_clamp(_safe_float(fatigue_score, 0.0)),
                retention_score=_clamp(_safe_float(retention_score, 0.5)),
                generosity_bias=_safe_float(generosity_bias, 0.0),
                last_reward_at_ms=_safe_int(last_reward_at_ms, 0),
                recent_legendary_count=_safe_int(recent_legendary_count, 0),
                total_rolls=_safe_int(total_rolls, 0),
                metadata=dict(metadata or {}),
            )
            self._profiles[pid] = profile
            if player_id:
                self._profiles_by_player[player_id] = pid
            _evict_fifo_dict(self._profiles, _MAX_PROFILES)
            self._record_event(CuratorEventKind.PROFILE_REGISTERED, {
                "profile_id": pid, "player_id": player_id,
            })
            return profile

    def get_profile(self, profile_id: str) -> Optional[PlayerRewardProfile]:
        with self._lock:
            return self._profiles.get(profile_id)

    def get_profile_by_player(self, player_id: str) -> Optional[PlayerRewardProfile]:
        with self._lock:
            pid = self._profiles_by_player.get(player_id)
            if pid is None:
                return None
            return self._profiles.get(pid)

    def list_profiles(
        self,
        playstyle: str = "",
        limit: int = 100,
    ) -> List[PlayerRewardProfile]:
        with self._lock:
            results: List[PlayerRewardProfile] = []
            for profile in self._profiles.values():
                if playstyle and profile.playstyle != playstyle:
                    continue
                results.append(profile)
            return results[:max(0, int(limit))]

    def update_profile(self, profile_id: str, **kwargs: Any) -> Optional[PlayerRewardProfile]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            old_player_id = profile.player_id
            for key, value in kwargs.items():
                if hasattr(profile, key) and key not in ("profile_id", "created_at"):
                    if key in ("fatigue_score", "retention_score"):
                        setattr(profile, key, _clamp(_safe_float(value, getattr(profile, key))))
                    elif key in ("last_reward_at_ms", "recent_legendary_count", "total_rolls"):
                        setattr(profile, key, _safe_int(value, getattr(profile, key)))
                    else:
                        setattr(profile, key, value)
            if "player_id" in kwargs and profile.player_id != old_player_id:
                self._profiles_by_player.pop(old_player_id, None)
                if profile.player_id:
                    self._profiles_by_player[profile.player_id] = profile.profile_id
            self._record_event(CuratorEventKind.PROFILE_UPDATED, {
                "profile_id": profile_id,
            })
            return profile

    # ------------------------------------------------------------------
    # Curation Intelligence
    # ------------------------------------------------------------------

    def curate_for_player(
        self,
        player_id: str,
        table_id: str,
        liveops_context: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Curate a contextual loot drop for a specific player.

        Fuses the active table, the player's reward profile, and the
        live-ops context to produce an adaptive drop.
        """
        with self._lock:
            table = self._tables.get(table_id)
            if table is None:
                return {"error": "table_not_found", "table_id": table_id}
            profile = self.get_profile_by_player(player_id)
            liveops_context = liveops_context or {}
            # Effective luck combines table, profile, and live-ops signals
            table_luck = table.base_luck
            profile_generosity = profile.generosity_bias if profile else 0.0
            profile_fatigue = profile.fatigue_score if profile else 0.0
            liveops_boost = _safe_float(liveops_context.get("luck_boost", 0.0), 0.0)
            effective_luck = (
                table_luck
                * (1.0 + profile_generosity - 0.5 * profile_fatigue)
                * (1.0 + liveops_boost)
            )
            effective_luck = max(0.1, effective_luck)
            rarity_shift = _safe_float(liveops_context.get("rarity_shift", 0.0), 0.0)
            strategy_override = liveops_context.get("strategy_override", "")
            policy = DropPolicy(
                luck=effective_luck,
                rarity_floor=liveops_context.get("rarity_floor", LootRarityTier.COMMON.value),
                rarity_ceiling=liveops_context.get("rarity_ceiling", LootRarityTier.MYTHIC.value),
                strategy_override=strategy_override,
                pulse_luck_boost=1.0,
                pulse_rarity_shift=rarity_shift,
            )
            rolled = self.roll_loot(table_id, policy=policy, seed=seed)
            # Update profile counters
            if profile is not None:
                profile.total_rolls += 1
                profile.last_reward_at_ms = _safe_int(liveops_context.get("now_ms", 0), 0)
                legendary_count = sum(
                    1 for r in rolled if r.rarity == LootRarityTier.LEGENDARY.value
                )
                legendary_count += sum(
                    1 for r in rolled if r.rarity == LootRarityTier.MYTHIC.value
                )
                profile.recent_legendary_count += legendary_count
            self._curations_performed += 1
            self._record_event(CuratorEventKind.CURATION_PERFORMED, {
                "player_id": player_id,
                "table_id": table_id,
                "drop_count": len(rolled),
            })
            return {
                "player_id": player_id,
                "table_id": table_id,
                "drops": [r.to_dict() for r in rolled],
                "effective_luck": effective_luck,
                "rarity_shift": rarity_shift,
                "strategy_override": strategy_override,
            }

    def suggest_pulse_timing(
        self,
        player_id: str,
        now_ms: int,
        target_engagement: float = 0.7,
    ) -> Dict[str, Any]:
        """Predict the next optimal reward pulse based on engagement decay."""
        with self._lock:
            profile = self.get_profile_by_player(player_id)
            if profile is None:
                return {
                    "player_id": player_id,
                    "recommended_at_ms": now_ms + 600000,
                    "recommended_luck_boost": 1.5,
                    "reason": "no_profile",
                }
            time_since_last = max(0, now_ms - profile.last_reward_at_ms)
            # Engagement decay model: simple exponential decay
            decay_rate = 0.0001
            current_engagement = profile.retention_score * (
                1.0 - (1.0 - pow(2.71828, -decay_rate * time_since_last))
            )
            current_engagement = _clamp(current_engagement)
            # Time until engagement drops below target
            if current_engagement >= target_engagement:
                gap = max(0.0, target_engagement - 0.05)
                if gap > 0:
                    time_to_threshold = int(
                        -pow(decay_rate, -1) * pow(2.71828, -1) * (
                            pow(profile.retention_score, -1) * gap
                        )
                    )
                else:
                    time_to_threshold = 600000
            else:
                time_to_threshold = 0
            recommended_at = now_ms + max(0, time_to_threshold)
            # Pulse strength scales with fatigue and engagement gap
            fatigue_factor = 1.0 + profile.fatigue_score
            engagement_gap = max(0.0, target_engagement - current_engagement)
            recommended_boost = 1.5 * fatigue_factor * (1.0 + engagement_gap)
            return {
                "player_id": player_id,
                "now_ms": now_ms,
                "current_engagement": current_engagement,
                "target_engagement": target_engagement,
                "recommended_at_ms": recommended_at,
                "recommended_luck_boost": round(recommended_boost, 3),
                "fatigue_score": profile.fatigue_score,
                "time_since_last_reward_ms": time_since_last,
            }

    def assess_engagement(
        self,
        player_id: str,
        now_ms: int,
    ) -> Dict[str, Any]:
        """Score engagement from recent reward history."""
        with self._lock:
            profile = self.get_profile_by_player(player_id)
            if profile is None:
                return {
                    "player_id": player_id,
                    "engagement_score": 0.0,
                    "verdict": "no_profile",
                }
            time_since_last = max(0, now_ms - profile.last_reward_at_ms)
            # Engagement = retention * (1 - decay) - fatigue penalty
            decay = 1.0 - pow(2.71828, -0.0001 * time_since_last)
            decay = _clamp(decay)
            engagement = profile.retention_score * (1.0 - decay) - 0.3 * profile.fatigue_score
            engagement = _clamp(engagement)
            if engagement >= 0.7:
                verdict = "high"
            elif engagement >= 0.4:
                verdict = "moderate"
            elif engagement >= 0.2:
                verdict = "low"
            else:
                verdict = "critical"
            return {
                "player_id": player_id,
                "engagement_score": round(engagement, 3),
                "retention_score": profile.retention_score,
                "fatigue_score": profile.fatigue_score,
                "time_since_last_reward_ms": time_since_last,
                "total_rolls": profile.total_rolls,
                "recent_legendary_count": profile.recent_legendary_count,
                "verdict": verdict,
            }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[CuratorEvent]:
        with self._lock:
            return list(self._audit[:max(0, int(limit))])

    def get_stats(self) -> CuratorStats:
        with self._lock:
            total_entries = sum(len(t.entries) for t in self._tables.values())
            return CuratorStats(
                total_tables=len(self._tables),
                total_entries=total_entries,
                total_pulses=len(self._pulses),
                total_profiles=len(self._profiles),
                total_rolls=len(self._rolls_log),
                total_curations=self._curations_performed,
                total_pulses_triggered=self._pulses_triggered,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "tables": len(self._tables),
                "pulses": len(self._pulses),
                "profiles": len(self._profiles),
                "rolls_logged": len(self._rolls_log),
                "curations_performed": self._curations_performed,
                "pulses_triggered": self._pulses_triggered,
                "events": len(self._audit),
            }

    def get_snapshot(self) -> CuratorSnapshot:
        with self._lock:
            return CuratorSnapshot(
                tables={tid: t.to_dict() for tid, t in self._tables.items()},
                pulses={pid: p.to_dict() for pid, p in self._pulses.items()},
                profiles={pid: p.to_dict() for pid, p in self._profiles.items()},
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._tables.clear()
            self._pulses.clear()
            self._profiles.clear()
            self._profiles_by_player.clear()
            self._rolls_log.clear()
            self._curations_performed = 0
            self._pulses_triggered = 0
            self._audit.clear()
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_loot_reward_curator() -> LootRewardCurator:
    return LootRewardCurator.get_instance()
