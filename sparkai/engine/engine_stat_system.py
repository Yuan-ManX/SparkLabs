"""
SparkLabs Engine - Stat System

A foundational stat and attribute director for the SparkLabs AI-native game
engine. It manages base attributes (strength, dexterity, intellect, etc.),
derived stats (max_hp, crit_chance, armor, move_speed), modifier stacking
from equipment/buffs/level-ups, and stat pools with clamping and recalculation.
The system is the single source of truth for RPG-style numeric progression
and feeds combat, UI, and save systems through a clean query interface.

Architecture:
  StatSystem (singleton)
    |-- StatDefinition, StatBlock, StatModifier,
       StatStats, StatSnapshot, StatEvent
    |-- StatKind, StatOp, StatEventKind

Core Capabilities:
  - register_definition / get_definition / list_definitions /
    remove_definition: stat type lifecycle with kind, formula, and bounds.
  - register_stat_block / get_stat_block / list_stat_blocks /
    update_stat_block / remove_stat_block: per-actor attribute blocks with
    base values and growth curves.
  - apply_modifier / get_modifier / list_modifiers / remove_modifier:
    transient or persistent modifiers with stacking operations.
  - recompute_derived: recalculate derived stats from base + modifiers.
  - get_stat / get_pool / set_pool / refill_pool: query and mutate stat
    values with clamping.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`StatSystem.get_instance` or the module-level :func:`get_stat_system`
factory.
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

_MAX_DEFINITIONS: int = 500
_MAX_BLOCKS: int = 10000
_MAX_MODIFIERS: int = 50000
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


def _clamp_value(value: float, low: Optional[float], high: Optional[float]) -> float:
    if low is not None and value < low:
        return low
    if high is not None and value > high:
        return high
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class StatKind(Enum):
    """Classification of a stat definition."""
    BASE = "base"
    DERIVED = "derived"
    POOL = "pool"


class StatOp(Enum):
    """Modifier stacking operations."""
    ADD = "add"
    MUL = "mul"
    OVERRIDE = "override"


class StatEventKind(Enum):
    """Audit event types emitted by the stat system."""
    DEFINITION_REGISTERED = "definition_registered"
    DEFINITION_REMOVED = "definition_removed"
    BLOCK_REGISTERED = "block_registered"
    BLOCK_UPDATED = "block_updated"
    BLOCK_REMOVED = "block_removed"
    MODIFIER_APPLIED = "modifier_applied"
    MODIFIER_REMOVED = "modifier_removed"
    DERIVED_RECOMPUTED = "derived_recomputed"
    POOL_MUTATED = "pool_mutated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class StatDefinition:
    """Defines a stat type with kind, formula, and bounds."""
    stat_id: str = ""
    name: str = ""
    description: str = ""
    kind: str = StatKind.BASE.value
    formula: str = ""
    default_base: float = 0.0
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    growth_per_level: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StatBlock:
    """Per-actor attribute block with base values and current pools."""
    block_id: str = ""
    actor_id: str = ""
    level: int = 1
    base_values: Dict[str, float] = field(default_factory=dict)
    derived_values: Dict[str, float] = field(default_factory=dict)
    pool_current: Dict[str, float] = field(default_factory=dict)
    pool_max: Dict[str, float] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StatModifier:
    """A modifier that alters a stat for an actor."""
    modifier_id: str = ""
    block_id: str = ""
    stat_id: str = ""
    source_id: str = ""
    op: str = StatOp.ADD.value
    magnitude: float = 0.0
    duration_seconds: float = 0.0
    remaining_seconds: float = 0.0
    priority: int = 0
    is_persistent: bool = True
    applied_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StatStats:
    """Aggregate statistics for the stat system."""
    total_definitions: int = 0
    total_blocks: int = 0
    total_modifiers: int = 0
    recompute_count: int = 0
    pool_mutations: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StatSnapshot:
    """Point-in-time snapshot of system state."""
    definitions: int = 0
    blocks: int = 0
    modifiers: int = 0
    events: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class StatEvent:
    """Audit event emitted by the stat system."""
    event_id: str = ""
    kind: str = StatEventKind.BLOCK_REGISTERED.value
    block_id: str = ""
    stat_id: str = ""
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class StatSystem:
    """Foundational stat and attribute director with modifier stacking."""

    _instance: Optional["StatSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._definitions: Dict[str, StatDefinition] = {}
        self._blocks: Dict[str, StatBlock] = {}
        self._modifiers: Dict[str, StatModifier] = {}
        self._events: List[StatEvent] = []
        self._stats = StatStats()

    @classmethod
    def get_instance(cls) -> "StatSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # -- lifecycle -------------------------------------------------------

    def initialize(self) -> None:
        with self._lock:
            if self._initialized:
                return
            self._seed_defaults()
            self._initialized = True

    def _seed_defaults(self) -> None:
        # Base attribute definitions
        base_defs = [
            ("stat_strength", "Strength", "Physical power and melee damage.", 10.0, 1.5),
            ("stat_dexterity", "Dexterity", "Agility and attack speed.", 10.0, 1.5),
            ("stat_intellect", "Intellect", "Magical potency and mana.", 10.0, 1.5),
            ("stat_constitution", "Constitution", "Health and resilience.", 10.0, 2.0),
        ]
        for sid, name, desc, default, growth in base_defs:
            self._definitions[sid] = StatDefinition(
                stat_id=sid,
                name=name,
                description=desc,
                kind=StatKind.BASE.value,
                default_base=default,
                min_value=1.0,
                growth_per_level=growth,
            )

        # Derived stat definitions
        derived_defs = [
            ("stat_max_hp", "Max HP", "Maximum health points.", StatKind.DERIVED.value,
             "constitution * 10 + strength * 2", 0.0, 1.0, 99999.0),
            ("stat_max_mp", "Max MP", "Maximum mana points.", StatKind.DERIVED.value,
             "intellect * 8", 0.0, 0.0, 9999.0),
            ("stat_attack", "Attack", "Raw physical attack power.", StatKind.DERIVED.value,
             "strength * 2", 0.0, 0.0, 9999.0),
            ("stat_defense", "Defense", "Physical damage reduction.", StatKind.DERIVED.value,
             "constitution * 1.5", 0.0, 0.0, 9999.0),
            ("stat_crit_chance", "Crit Chance", "Critical hit probability.", StatKind.DERIVED.value,
             "dexterity * 0.005", 0.05, 0.0, 1.0),
            ("stat_move_speed", "Move Speed", "Movement speed in m/s.", StatKind.DERIVED.value,
             "5.0 + dexterity * 0.05", 5.0, 0.0, 30.0),
        ]
        for sid, name, desc, kind, formula, default, lo, hi in derived_defs:
            self._definitions[sid] = StatDefinition(
                stat_id=sid,
                name=name,
                description=desc,
                kind=kind,
                formula=formula,
                default_base=default,
                min_value=lo,
                max_value=hi,
            )

        # Pool definitions
        pool_defs = [
            ("stat_hp", "HP", "Current health pool.", "stat_max_hp"),
            ("stat_mp", "MP", "Current mana pool.", "stat_max_mp"),
        ]
        for sid, name, desc, max_stat in pool_defs:
            self._definitions[sid] = StatDefinition(
                stat_id=sid,
                name=name,
                description=desc,
                kind=StatKind.POOL.value,
                formula=max_stat,
                default_base=0.0,
                min_value=0.0,
            )

        # Seed one stat block for a sample actor
        block = StatBlock(
            block_id="stb_hero_1",
            actor_id="actor_hero_1",
            level=5,
            base_values={
                "stat_strength": 14.0,
                "stat_dexterity": 12.0,
                "stat_intellect": 10.0,
                "stat_constitution": 13.0,
            },
            created_at=_now(),
            updated_at=_now(),
        )
        self._blocks[block.block_id] = block
        self._recompute_derived_locked(block)

        # Seed one persistent modifier (equipment bonus)
        mod = StatModifier(
            modifier_id="stm_hero_sword",
            block_id="stb_hero_1",
            stat_id="stat_attack",
            source_id="eq_iron_sword",
            op=StatOp.ADD.value,
            magnitude=5.0,
            duration_seconds=0.0,
            remaining_seconds=0.0,
            priority=10,
            is_persistent=True,
            applied_at=_now(),
        )
        self._modifiers[mod.modifier_id] = mod
        self._recompute_derived_locked(block)

        self._stats.total_definitions = len(self._definitions)
        self._stats.total_blocks = len(self._blocks)
        self._stats.total_modifiers = len(self._modifiers)

        self._emit(
            StatEventKind.BLOCK_REGISTERED,
            block_id=block.block_id,
            payload={"actor_id": block.actor_id, "level": block.level},
        )
        for sid in self._definitions:
            self._emit(
                StatEventKind.DEFINITION_REGISTERED,
                stat_id=sid,
                payload={"name": self._definitions[sid].name},
            )
        self._emit(
            StatEventKind.MODIFIER_APPLIED,
            block_id="stb_hero_1",
            stat_id="stat_attack",
            payload={"modifier_id": "stm_hero_sword", "magnitude": 5.0},
        )

    def _emit(
        self,
        kind: StatEventKind,
        block_id: str = "",
        stat_id: str = "",
        payload: Optional[Dict[str, Any]] = None,
    ) -> StatEvent:
        event = StatEvent(
            event_id=_new_id("evt"),
            kind=kind.value,
            block_id=block_id,
            stat_id=stat_id,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    # -- definition CRUD -------------------------------------------------

    def register_definition(self, definition: StatDefinition) -> StatDefinition:
        with self._lock:
            if not definition.stat_id:
                definition.stat_id = _new_id("stat")
            self._definitions[definition.stat_id] = definition
            _evict_fifo_dict(self._definitions, _MAX_DEFINITIONS)
            self._stats.total_definitions = len(self._definitions)
            self._emit(
                StatEventKind.DEFINITION_REGISTERED,
                stat_id=definition.stat_id,
                payload={"name": definition.name, "kind": definition.kind},
            )
            return definition

    def get_definition(self, stat_id: str) -> Optional[StatDefinition]:
        return self._definitions.get(stat_id)

    def list_definitions(
        self,
        kind: Optional[str] = None,
        limit: int = 100,
    ) -> List[StatDefinition]:
        limit = max(1, min(int(limit), 500))
        results: List[StatDefinition] = []
        for d in self._definitions.values():
            if kind and d.kind != kind:
                continue
            results.append(d)
        return results[:limit]

    def remove_definition(self, stat_id: str) -> bool:
        with self._lock:
            removed = self._definitions.pop(stat_id, None)
            if removed is None:
                return False
            self._stats.total_definitions = len(self._definitions)
            self._emit(
                StatEventKind.DEFINITION_REMOVED,
                stat_id=stat_id,
            )
            return True

    # -- block CRUD ------------------------------------------------------

    def register_stat_block(self, block: StatBlock) -> StatBlock:
        with self._lock:
            if not block.block_id:
                block.block_id = _new_id("stb")
            if not block.created_at:
                block.created_at = _now()
            block.updated_at = _now()
            # Fill in default base values for missing base stats
            for sid, d in self._definitions.items():
                if d.kind == StatKind.BASE.value and sid not in block.base_values:
                    block.base_values[sid] = d.default_base
            self._blocks[block.block_id] = block
            _evict_fifo_dict(self._blocks, _MAX_BLOCKS)
            self._stats.total_blocks = len(self._blocks)
            self._recompute_derived_locked(block)
            self._emit(
                StatEventKind.BLOCK_REGISTERED,
                block_id=block.block_id,
                payload={"actor_id": block.actor_id, "level": block.level},
            )
            return block

    def get_stat_block(self, block_id: str) -> Optional[StatBlock]:
        return self._blocks.get(block_id)

    def list_stat_blocks(
        self,
        actor_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StatBlock]:
        limit = max(1, min(int(limit), 200))
        results: List[StatBlock] = []
        for b in self._blocks.values():
            if actor_id and b.actor_id != actor_id:
                continue
            results.append(b)
        return results[:limit]

    def update_stat_block(self, block_id: str, updates: Dict[str, Any]) -> Optional[StatBlock]:
        with self._lock:
            block = self._blocks.get(block_id)
            if block is None:
                return None
            if "level" in updates:
                block.level = max(1, _safe_int(updates["level"], block.level))
            if "base_values" in updates and isinstance(updates["base_values"], dict):
                for k, v in updates["base_values"].items():
                    block.base_values[str(k)] = _safe_float(v, 0.0)
            if "actor_id" in updates:
                block.actor_id = str(updates["actor_id"])
            block.updated_at = _now()
            self._recompute_derived_locked(block)
            self._emit(
                StatEventKind.BLOCK_UPDATED,
                block_id=block_id,
                payload={"fields": list(updates.keys())},
            )
            return block

    def remove_stat_block(self, block_id: str) -> bool:
        with self._lock:
            removed = self._blocks.pop(block_id, None)
            if removed is None:
                return False
            # Remove associated modifiers
            mod_ids = [mid for mid, m in self._modifiers.items() if m.block_id == block_id]
            for mid in mod_ids:
                self._modifiers.pop(mid, None)
            self._stats.total_blocks = len(self._blocks)
            self._stats.total_modifiers = len(self._modifiers)
            self._emit(
                StatEventKind.BLOCK_REMOVED,
                block_id=block_id,
            )
            return True

    # -- modifiers -------------------------------------------------------

    def apply_modifier(self, modifier: StatModifier) -> StatModifier:
        with self._lock:
            if not modifier.modifier_id:
                modifier.modifier_id = _new_id("stm")
            if not modifier.applied_at:
                modifier.applied_at = _now()
            self._modifiers[modifier.modifier_id] = modifier
            _evict_fifo_dict(self._modifiers, _MAX_MODIFIERS)
            self._stats.total_modifiers = len(self._modifiers)
            # Recompute the affected block
            block = self._blocks.get(modifier.block_id)
            if block is not None:
                self._recompute_derived_locked(block)
            self._emit(
                StatEventKind.MODIFIER_APPLIED,
                block_id=modifier.block_id,
                stat_id=modifier.stat_id,
                payload={
                    "modifier_id": modifier.modifier_id,
                    "op": modifier.op,
                    "magnitude": modifier.magnitude,
                    "source": modifier.source_id,
                },
            )
            return modifier

    def get_modifier(self, modifier_id: str) -> Optional[StatModifier]:
        return self._modifiers.get(modifier_id)

    def list_modifiers(
        self,
        block_id: Optional[str] = None,
        stat_id: Optional[str] = None,
        source_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[StatModifier]:
        limit = max(1, min(int(limit), 200))
        results: List[StatModifier] = []
        for m in self._modifiers.values():
            if block_id and m.block_id != block_id:
                continue
            if stat_id and m.stat_id != stat_id:
                continue
            if source_id and m.source_id != source_id:
                continue
            results.append(m)
        return results[:limit]

    def remove_modifier(self, modifier_id: str) -> bool:
        with self._lock:
            removed = self._modifiers.pop(modifier_id, None)
            if removed is None:
                return False
            self._stats.total_modifiers = len(self._modifiers)
            # Recompute the affected block
            block = self._blocks.get(removed.block_id)
            if block is not None:
                self._recompute_derived_locked(block)
            self._emit(
                StatEventKind.MODIFIER_REMOVED,
                block_id=removed.block_id,
                stat_id=removed.stat_id,
                payload={"modifier_id": modifier_id},
            )
            return True

    # -- computation -----------------------------------------------------

    def _recompute_derived_locked(self, block: StatBlock) -> None:
        """Recompute derived stats and pool maxima for a block. Caller holds lock."""
        # Build a context of base + additive modifiers
        context: Dict[str, float] = dict(block.base_values)

        # Group modifiers by stat_id, applying by priority
        mods_by_stat: Dict[str, List[StatModifier]] = {}
        for m in self._modifiers.values():
            if m.block_id != block.block_id:
                continue
            mods_by_stat.setdefault(m.stat_id, []).append(m)

        # Apply modifiers to base values for BASE stats
        for stat_id, mods in mods_by_stat.items():
            definition = self._definitions.get(stat_id)
            if definition is None or definition.kind != StatKind.BASE.value:
                continue
            base_val = block.base_values.get(stat_id, definition.default_base)
            sorted_mods = sorted(mods, key=lambda x: x.priority)
            for m in sorted_mods:
                if m.op == StatOp.ADD.value:
                    base_val += m.magnitude
                elif m.op == StatOp.MUL.value:
                    base_val *= m.magnitude
                elif m.op == StatOp.OVERRIDE.value:
                    base_val = m.magnitude
            context[stat_id] = base_val

        # Compute derived stats using simple formula evaluation
        derived_values: Dict[str, float] = {}
        for sid, d in self._definitions.items():
            if d.kind != StatKind.DERIVED.value:
                continue
            val = self._eval_formula(d.formula, context, d.default_base)
            val = _clamp_value(val, d.min_value, d.max_value)
            derived_values[sid] = val
            context[sid] = val

        # Apply modifiers to derived stats
        for stat_id, mods in mods_by_stat.items():
            definition = self._definitions.get(stat_id)
            if definition is None or definition.kind != StatKind.DERIVED.value:
                continue
            val = derived_values.get(stat_id, definition.default_base)
            sorted_mods = sorted(mods, key=lambda x: x.priority)
            for m in sorted_mods:
                if m.op == StatOp.ADD.value:
                    val += m.magnitude
                elif m.op == StatOp.MUL.value:
                    val *= m.magnitude
                elif m.op == StatOp.OVERRIDE.value:
                    val = m.magnitude
            val = _clamp_value(val, definition.min_value, definition.max_value)
            derived_values[stat_id] = val
            context[stat_id] = val

        block.derived_values = derived_values

        # Compute pool maxima from derived stats
        pool_max: Dict[str, float] = {}
        for sid, d in self._definitions.items():
            if d.kind != StatKind.POOL.value:
                continue
            # Formula references the max stat
            max_val = context.get(d.formula, d.default_base)
            pool_max[sid] = _clamp_value(max_val, d.min_value, d.max_value)

        block.pool_max = pool_max
        # Initialize pool_current if missing, clamp to max
        for sid, mx in pool_max.items():
            if sid not in block.pool_current:
                block.pool_current[sid] = mx
            else:
                block.pool_current[sid] = _clamp_value(
                    block.pool_current[sid], 0.0, mx
                )

        self._stats.recompute_count += 1

    def _eval_formula(
        self,
        formula: str,
        context: Dict[str, float],
        default: float,
    ) -> float:
        """Evaluate a simple arithmetic formula referencing stat ids."""
        if not formula:
            return default
        try:
            # Replace stat_id tokens with their values; stat_ids start with 'stat_'
            expr = formula
            for sid, val in context.items():
                expr = expr.replace(sid, str(val))
            # Also handle bare names like 'strength' -> use stat_strength if present
            bare_map = {
                "strength": context.get("stat_strength", 0.0),
                "dexterity": context.get("stat_dexterity", 0.0),
                "intellect": context.get("stat_intellect", 0.0),
                "constitution": context.get("stat_constitution", 0.0),
            }
            for name, val in bare_map.items():
                expr = expr.replace(name, str(val))
            # Safe eval: only allow arithmetic operations
            allowed = set("0123456789.+-*/() ")
            if not all(c in allowed for c in expr):
                return default
            return float(eval(expr, {"__builtins__": {}}, {}))
        except Exception:
            return default

    def recompute_derived(self, block_id: str) -> Optional[StatBlock]:
        with self._lock:
            block = self._blocks.get(block_id)
            if block is None:
                return None
            self._recompute_derived_locked(block)
            block.updated_at = _now()
            self._emit(
                StatEventKind.DERIVED_RECOMPUTED,
                block_id=block_id,
                payload={"derived_count": len(block.derived_values)},
            )
            return block

    def get_stat(self, block_id: str, stat_id: str) -> Dict[str, Any]:
        block = self._blocks.get(block_id)
        if block is None:
            return {"ok": False, "reason": "block_not_found"}
        definition = self._definitions.get(stat_id)
        if definition is None:
            return {"ok": False, "reason": "stat_not_found"}
        if definition.kind == StatKind.BASE.value:
            value = block.base_values.get(stat_id, definition.default_base)
        elif definition.kind == StatKind.DERIVED.value:
            value = block.derived_values.get(stat_id, definition.default_base)
        else:  # POOL
            value = block.pool_current.get(stat_id, 0.0)
        return {
            "ok": True,
            "block_id": block_id,
            "stat_id": stat_id,
            "name": definition.name,
            "kind": definition.kind,
            "value": value,
            "min": definition.min_value,
            "max": definition.max_value,
        }

    def get_pool(self, block_id: str, stat_id: str) -> Dict[str, Any]:
        block = self._blocks.get(block_id)
        if block is None:
            return {"ok": False, "reason": "block_not_found"}
        definition = self._definitions.get(stat_id)
        if definition is None or definition.kind != StatKind.POOL.value:
            return {"ok": False, "reason": "pool_not_found"}
        current = block.pool_current.get(stat_id, 0.0)
        maximum = block.pool_max.get(stat_id, 0.0)
        return {
            "ok": True,
            "block_id": block_id,
            "stat_id": stat_id,
            "current": current,
            "max": maximum,
            "ratio": (current / maximum) if maximum > 0 else 0.0,
        }

    def set_pool(self, block_id: str, stat_id: str, value: float) -> Optional[StatBlock]:
        with self._lock:
            block = self._blocks.get(block_id)
            if block is None:
                return None
            definition = self._definitions.get(stat_id)
            if definition is None or definition.kind != StatKind.POOL.value:
                return None
            maximum = block.pool_max.get(stat_id, 0.0)
            new_val = _clamp_value(_safe_float(value, 0.0), 0.0, maximum)
            block.pool_current[stat_id] = new_val
            block.updated_at = _now()
            self._stats.pool_mutations += 1
            self._emit(
                StatEventKind.POOL_MUTATED,
                block_id=block_id,
                stat_id=stat_id,
                payload={"new_value": new_val, "max": maximum},
            )
            return block

    def refill_pool(self, block_id: str, stat_id: str, amount: Optional[float] = None) -> Optional[StatBlock]:
        with self._lock:
            block = self._blocks.get(block_id)
            if block is None:
                return None
            definition = self._definitions.get(stat_id)
            if definition is None or definition.kind != StatKind.POOL.value:
                return None
            maximum = block.pool_max.get(stat_id, 0.0)
            current = block.pool_current.get(stat_id, 0.0)
            if amount is None:
                new_val = maximum
            else:
                new_val = _clamp_value(current + _safe_float(amount, 0.0), 0.0, maximum)
            block.pool_current[stat_id] = new_val
            block.updated_at = _now()
            self._stats.pool_mutations += 1
            self._emit(
                StatEventKind.POOL_MUTATED,
                block_id=block_id,
                stat_id=stat_id,
                payload={"refilled_to": new_val, "max": maximum},
            )
            return block

    # -- observability ---------------------------------------------------

    def list_events(self, limit: int = 50) -> List[StatEvent]:
        limit = max(1, min(int(limit), 200))
        return list(self._events[-limit:])

    def get_stats(self) -> StatStats:
        self._stats.total_definitions = len(self._definitions)
        self._stats.total_blocks = len(self._blocks)
        self._stats.total_modifiers = len(self._modifiers)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "definitions": len(self._definitions),
            "blocks": len(self._blocks),
            "modifiers": len(self._modifiers),
            "events": len(self._events),
            "recompute_count": self._stats.recompute_count,
            "pool_mutations": self._stats.pool_mutations,
        }

    def get_snapshot(self) -> StatSnapshot:
        return StatSnapshot(
            definitions=len(self._definitions),
            blocks=len(self._blocks),
            modifiers=len(self._modifiers),
            events=len(self._events),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._lock:
            self._definitions.clear()
            self._blocks.clear()
            self._modifiers.clear()
            self._events.clear()
            self._stats = StatStats()
            self._initialized = False
            self._seed_defaults()
            self._initialized = True


# ---------------------------------------------------------------------------
# Module Factory
# ---------------------------------------------------------------------------


def get_stat_system() -> StatSystem:
    instance = StatSystem.get_instance()
    if not instance._initialized:
        instance.initialize()
    return instance
