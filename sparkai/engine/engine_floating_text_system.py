"""
SparkLabs Engine - Floating Text System

A world-anchored floating text and combat feedback system for the SparkLabs
AI-native game engine. This system manages transient text popups — damage
numbers, healing values, critical hit callouts, combo counters, experience
gains, loot notifications, status effect labels, and custom messages — that
rise from a world position, animate according to their kind, and fade out
after a configurable lifetime.

The system is distinct from the game feel director (which handles screen
shake, hit pause, and time scaling) and the HUD system (which manages
persistent UI elements). Floating text is transient, world-anchored, and
combines with combo tracking to reward sustained player performance.

Architecture:
  FloatingTextSystem (singleton)
    |-- FloatingTextEntry, ComboState, FloatKindConfig, FloatingTextConfig,
       FloatingTextStats, FloatingTextSnapshot, FloatingTextEvent
    |-- TextKind, AnimationStyle, FloatingTextEventKind

Core Capabilities:
  - spawn_text: create a floating text entry at a world position with a
    numeric value, kind, and optional color override.
  - spawn_damage / spawn_heal / spawn_crit / spawn_miss / spawn_experience:
    convenience methods for common combat feedback.
  - get_text / list_active / remove_text: lifecycle for individual entries.
  - register_combo / get_combo / break_combo: combo tracking with multiplier
    growth, timeout decay, and kind filtering.
  - merge_stacks: combine nearby entries of the same kind within a merge
    radius into a single accumulated value.
  - set_kind_config / get_kind_config: per-kind tuning for color, font size,
    animation style, lifetime, and rise speed.
  - tick: advance the simulation — update positions, apply animations,
    expire lifetime, decay combos.
  - set_config / get_config: global tuning for max active entries, default
    lifetime, merge radius, and combo timeout.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`FloatingTextSystem.get_instance` or the module-level
:func:`get_floating_text_system` factory.
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

_MAX_ENTRIES: int = 2000
_MAX_EVENTS: int = 5000
_MAX_COMBO_HISTORY: int = 2000

_DEFAULT_LIFETIME: float = 1.5
_DEFAULT_RISE_SPEED: float = 60.0
_DEFAULT_FONT_SIZE: int = 24
_DEFAULT_MERGE_RADIUS: float = 2.0
_DEFAULT_COMBO_TIMEOUT: float = 3.0
_DEFAULT_COMBO_MULTIPLIER_STEP: float = 0.1
_DEFAULT_COMBO_MAX_MULTIPLIER: float = 5.0


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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _distance2d(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TextKind(Enum):
    """Classification of floating text entry types."""
    DAMAGE = "damage"
    HEAL = "heal"
    CRIT = "crit"
    MISS = "miss"
    DODGE = "dodge"
    BLOCK = "block"
    EXPERIENCE = "experience"
    LEVEL_UP = "level_up"
    COMBO = "combo"
    LOOT = "loot"
    STATUS = "status"
    CURRENCY = "currency"
    CUSTOM = "custom"


class AnimationStyle(Enum):
    """Animation patterns for floating text movement."""
    RISE = "rise"
    RISE_FADE = "rise_fade"
    SCALE_POP = "scale_pop"
    SHAKE = "shake"
    ARC = "arc"
    SPIRAL = "spiral"


class FloatingTextEventKind(Enum):
    """Audit event types emitted by the floating text system."""
    TEXT_SPAWNED = "text_spawned"
    TEXT_REMOVED = "text_removed"
    TEXT_EXPIRED = "text_expired"
    TEXT_MERGED = "text_merged"
    COMBO_REGISTERED = "combo_registered"
    COMBO_BROKEN = "combo_broken"
    COMBO_EXTENDED = "combo_extended"
    KIND_CONFIG_UPDATED = "kind_config_updated"
    CONFIG_UPDATED = "config_updated"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class TextKindConfig:
    """Per-kind visual configuration for floating text."""
    kind: str = TextKind.DAMAGE.value
    color: str = "#FFFFFF"
    font_size: int = _DEFAULT_FONT_SIZE
    animation: str = AnimationStyle.RISE_FADE.value
    lifetime: float = _DEFAULT_LIFETIME
    rise_speed: float = _DEFAULT_RISE_SPEED
    prefix: str = ""
    suffix: str = ""
    bold: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FloatingTextEntry:
    """A single floating text popup anchored to a world position."""
    entry_id: str = ""
    kind: str = TextKind.DAMAGE.value
    value: float = 0.0
    text: str = ""
    world_position: Tuple[float, float] = (0.0, 0.0)
    screen_offset: Tuple[float, float] = (0.0, 0.0)
    color: str = "#FFFFFF"
    font_size: int = _DEFAULT_FONT_SIZE
    animation: str = AnimationStyle.RISE_FADE.value
    lifetime: float = _DEFAULT_LIFETIME
    elapsed: float = 0.0
    rise_speed: float = _DEFAULT_RISE_SPEED
    target_id: str = ""
    combo_id: str = ""
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def remaining(self) -> float:
        return max(0.0, self.lifetime - self.elapsed)

    @property
    def alpha(self) -> float:
        if self.lifetime <= 0:
            return 1.0
        return _clamp(1.0 - self.elapsed / self.lifetime, 0.0, 1.0)

    def to_dict(self) -> Dict[str, Any]:
        d = _dataclass_to_dict(self)
        d["remaining"] = round(self.remaining, 4)
        d["alpha"] = round(self.alpha, 4)
        return d


@dataclass
class ComboState:
    """Active combo tracking for a target."""
    combo_id: str = ""
    target_id: str = ""
    kind: str = TextKind.DAMAGE.value
    count: int = 0
    multiplier: float = 1.0
    total_value: float = 0.0
    started_at: str = ""
    last_hit_at: str = ""
    last_hit_time_secs: float = 0.0
    timeout: float = _DEFAULT_COMBO_TIMEOUT
    broken: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FloatingTextConfig:
    """Global tuning parameters for the floating text system."""
    max_active_entries: int = 500
    default_lifetime: float = _DEFAULT_LIFETIME
    default_rise_speed: float = _DEFAULT_RISE_SPEED
    default_font_size: int = _DEFAULT_FONT_SIZE
    merge_radius: float = _DEFAULT_MERGE_RADIUS
    merge_enabled: bool = True
    combo_timeout: float = _DEFAULT_COMBO_TIMEOUT
    combo_multiplier_step: float = _DEFAULT_COMBO_MULTIPLIER_STEP
    combo_max_multiplier: float = _DEFAULT_COMBO_MAX_MULTIPLIER
    combo_enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FloatingTextStats:
    """Aggregate statistics for the floating text system."""
    total_spawned: int = 0
    total_expired: int = 0
    total_merged: int = 0
    total_combos_started: int = 0
    total_combos_broken: int = 0
    active_entries: int = 0
    active_combos: int = 0
    max_combo_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FloatingTextSnapshot:
    """Full state snapshot of the floating text system."""
    entries: List[FloatingTextEntry] = field(default_factory=list)
    combos: List[ComboState] = field(default_factory=list)
    kind_configs: Dict[str, TextKindConfig] = field(default_factory=dict)
    config: FloatingTextConfig = field(default_factory=FloatingTextConfig)
    stats: FloatingTextStats = field(default_factory=FloatingTextStats)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FloatingTextEvent:
    """An audit event emitted by the floating text system."""
    timestamp: str = ""
    kind: str = ""
    entity_id: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Singleton System
# ---------------------------------------------------------------------------


class FloatingTextSystem:
    """World-anchored floating text and combat feedback system.

    Manages transient text popups (damage numbers, healing, combos, loot
    notifications) that rise from world positions and fade over time.
    Includes combo tracking with multiplier growth and stack merging for
    nearby same-kind entries.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["FloatingTextSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._entries: Dict[str, FloatingTextEntry] = {}
        self._combos: Dict[str, ComboState] = {}
        self._kind_configs: Dict[str, TextKindConfig] = {}
        self._events: List[FloatingTextEvent] = []
        self._combo_history: List[Dict[str, Any]] = []
        self._config: FloatingTextConfig = FloatingTextConfig()
        self._stats: FloatingTextStats = FloatingTextStats()
        self._tick_count: int = 0
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "FloatingTextSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed the system with default kind configurations and sample entries."""
        default_configs = [
            TextKindConfig(kind=TextKind.DAMAGE.value, color="#FF4444", font_size=26, animation=AnimationStyle.RISE_FADE.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.HEAL.value, color="#44FF44", font_size=24, animation=AnimationStyle.RISE_FADE.value, prefix="+", suffix=""),
            TextKindConfig(kind=TextKind.CRIT.value, color="#FFAA00", font_size=34, animation=AnimationStyle.SCALE_POP.value, prefix="", suffix="!", bold=True),
            TextKindConfig(kind=TextKind.MISS.value, color="#AAAAAA", font_size=20, animation=AnimationStyle.SHAKE.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.DODGE.value, color="#8888FF", font_size=20, animation=AnimationStyle.SHAKE.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.BLOCK.value, color="#CCCCAA", font_size=22, animation=AnimationStyle.RISE.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.EXPERIENCE.value, color="#44DDFF", font_size=18, animation=AnimationStyle.RISE_FADE.value, prefix="+", suffix=" XP"),
            TextKindConfig(kind=TextKind.LEVEL_UP.value, color="#FFDD00", font_size=36, animation=AnimationStyle.SCALE_POP.value, prefix="LEVEL ", suffix="!", bold=True),
            TextKindConfig(kind=TextKind.COMBO.value, color="#FF6600", font_size=28, animation=AnimationStyle.SCALE_POP.value, prefix="x", suffix=" COMBO", bold=True),
            TextKindConfig(kind=TextKind.LOOT.value, color="#DDDD44", font_size=22, animation=AnimationStyle.ARC.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.STATUS.value, color="#FF44FF", font_size=20, animation=AnimationStyle.RISE.value, prefix="", suffix=""),
            TextKindConfig(kind=TextKind.CURRENCY.value, color="#FFD700", font_size=22, animation=AnimationStyle.RISE_FADE.value, prefix="+", suffix=" gold"),
            TextKindConfig(kind=TextKind.CUSTOM.value, color="#FFFFFF", font_size=24, animation=AnimationStyle.RISE_FADE.value, prefix="", suffix=""),
        ]
        for cfg in default_configs:
            self._kind_configs[cfg.kind] = cfg

        # Seed sample entries
        sample_entries = [
            FloatingTextEntry(
                entry_id="ft_sample_dmg_1",
                kind=TextKind.DAMAGE.value,
                value=125.0,
                text="125",
                world_position=(10.0, 5.0),
                color="#FF4444",
                font_size=26,
                animation=AnimationStyle.RISE_FADE.value,
                lifetime=1.5,
                target_id="tgt_goblin",
            ),
            FloatingTextEntry(
                entry_id="ft_sample_crit_1",
                kind=TextKind.CRIT.value,
                value=340.0,
                text="340!",
                world_position=(10.5, 5.5),
                color="#FFAA00",
                font_size=34,
                animation=AnimationStyle.SCALE_POP.value,
                lifetime=2.0,
                target_id="tgt_goblin",
            ),
            FloatingTextEntry(
                entry_id="ft_sample_heal_1",
                kind=TextKind.HEAL.value,
                value=80.0,
                text="+80",
                world_position=(-5.0, 3.0),
                color="#44FF44",
                font_size=24,
                animation=AnimationStyle.RISE_FADE.value,
                lifetime=1.5,
                target_id="plr_hero",
            ),
            FloatingTextEntry(
                entry_id="ft_sample_xp_1",
                kind=TextKind.EXPERIENCE.value,
                value=450.0,
                text="+450 XP",
                world_position=(0.0, 0.0),
                color="#44DDFF",
                font_size=18,
                animation=AnimationStyle.RISE_FADE.value,
                lifetime=2.0,
                target_id="plr_hero",
            ),
        ]
        for entry in sample_entries:
            self._entries[entry.entry_id] = entry

        # Seed a sample combo
        sample_combo = ComboState(
            combo_id="cmb_sample_1",
            target_id="tgt_goblin",
            kind=TextKind.DAMAGE.value,
            count=3,
            multiplier=1.2,
            total_value=565.0,
            started_at=_now(),
            last_hit_at=_now(),
            last_hit_time_secs=0.0,
        )
        self._combos[sample_combo.combo_id] = sample_combo

        self._stats.total_spawned = len(sample_entries)
        self._stats.active_entries = len(self._entries)
        self._stats.active_combos = len(self._combos)
        self._stats.max_combo_count = sample_combo.count
        self._initialized = True

    # ------------------------------------------------------------------
    # Private Helpers
    # ------------------------------------------------------------------

    def _emit_event(self, kind: str, entity_id: str, details: Optional[Dict[str, Any]] = None) -> None:
        event = FloatingTextEvent(
            timestamp=_now(),
            kind=kind,
            entity_id=entity_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _recompute_stats(self) -> None:
        self._stats.active_entries = len(self._entries)
        self._stats.active_combos = sum(1 for c in self._combos.values() if not c.broken)
        max_combo = max((c.count for c in self._combos.values()), default=0)
        self._stats.max_combo_count = max(self._stats.max_combo_count, max_combo)

    def _get_kind_config(self, kind: str) -> TextKindConfig:
        """Retrieve the kind config, falling back to a default."""
        cfg = self._kind_configs.get(kind)
        if cfg is None:
            cfg = TextKindConfig(kind=kind)
            self._kind_configs[kind] = cfg
        return cfg

    def _format_text(self, value: float, kind: str, custom_text: str = "") -> str:
        """Format the display text for a floating text entry."""
        if custom_text:
            return custom_text
        cfg = self._get_kind_config(kind)
        # Format value: show as integer if whole, else 1 decimal
        if value == int(value):
            val_str = str(int(value))
        else:
            val_str = f"{value:.1f}"
        return f"{cfg.prefix}{val_str}{cfg.suffix}"

    # ------------------------------------------------------------------
    # Text Spawning
    # ------------------------------------------------------------------

    def spawn_text(
        self,
        kind: str,
        value: float,
        world_position: Tuple[float, float],
        target_id: str = "",
        custom_text: str = "",
        color_override: str = "",
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> FloatingTextEntry:
        """Spawn a floating text entry at a world position."""
        cfg = self._get_kind_config(kind)
        entry = FloatingTextEntry(
            entry_id=_new_id("ft"),
            kind=kind,
            value=value,
            text=self._format_text(value, kind, custom_text),
            world_position=world_position,
            screen_offset=(0.0, 0.0),
            color=color_override if color_override else cfg.color,
            font_size=cfg.font_size,
            animation=cfg.animation,
            lifetime=cfg.lifetime,
            elapsed=0.0,
            rise_speed=cfg.rise_speed,
            target_id=target_id,
            priority=priority,
            metadata=metadata or {},
        )
        self._entries[entry.entry_id] = entry
        _evict_fifo_dict(self._entries, _MAX_ENTRIES)

        # Combo tracking
        if self._config.combo_enabled and target_id and kind in (TextKind.DAMAGE.value, TextKind.CRIT.value):
            self._extend_or_create_combo(target_id, kind, value)

        self._stats.total_spawned += 1
        self._emit_event(FloatingTextEventKind.TEXT_SPAWNED.value, entry.entry_id, {"kind": kind, "value": value, "target_id": target_id})
        self._recompute_stats()
        return entry

    def spawn_damage(self, value: float, world_position: Tuple[float, float], target_id: str = "") -> FloatingTextEntry:
        """Convenience method for spawning a damage number."""
        return self.spawn_text(TextKind.DAMAGE.value, value, world_position, target_id)

    def spawn_heal(self, value: float, world_position: Tuple[float, float], target_id: str = "") -> FloatingTextEntry:
        """Convenience method for spawning a heal number."""
        return self.spawn_text(TextKind.HEAL.value, value, world_position, target_id)

    def spawn_crit(self, value: float, world_position: Tuple[float, float], target_id: str = "") -> FloatingTextEntry:
        """Convenience method for spawning a critical hit number."""
        return self.spawn_text(TextKind.CRIT.value, value, world_position, target_id)

    def spawn_miss(self, world_position: Tuple[float, float], target_id: str = "") -> FloatingTextEntry:
        """Convenience method for spawning a miss indicator."""
        return self.spawn_text(TextKind.MISS.value, 0.0, world_position, target_id, custom_text="MISS")

    def spawn_experience(self, value: float, world_position: Tuple[float, float], target_id: str = "") -> FloatingTextEntry:
        """Convenience method for spawning an experience gain."""
        return self.spawn_text(TextKind.EXPERIENCE.value, value, world_position, target_id)

    def get_text(self, entry_id: str) -> Optional[FloatingTextEntry]:
        """Retrieve a floating text entry by ID."""
        return self._entries.get(entry_id)

    def list_active(self, kind: Optional[str] = None, target_id: Optional[str] = None, limit: int = 100) -> List[FloatingTextEntry]:
        """List active floating text entries with optional filters."""
        results = list(self._entries.values())
        if kind:
            results = [e for e in results if e.kind == kind]
        if target_id:
            results = [e for e in results if e.target_id == target_id]
        results.sort(key=lambda e: e.elapsed, reverse=False)
        return results[:max(0, int(limit))]

    def remove_text(self, entry_id: str) -> bool:
        """Remove a floating text entry by ID."""
        if entry_id not in self._entries:
            return False
        self._entries.pop(entry_id, None)
        self._emit_event(FloatingTextEventKind.TEXT_REMOVED.value, entry_id, {})
        self._recompute_stats()
        return True

    # ------------------------------------------------------------------
    # Combo System
    # ------------------------------------------------------------------

    def _extend_or_create_combo(self, target_id: str, kind: str, value: float, current_time: float = 0.0) -> ComboState:
        """Find or create a combo for the target, extending its count."""
        # Find an existing active combo for this target and kind
        combo = None
        for c in self._combos.values():
            if c.target_id == target_id and c.kind == kind and not c.broken:
                combo = c
                break

        if combo is None:
            combo = ComboState(
                combo_id=_new_id("cmb"),
                target_id=target_id,
                kind=kind,
                count=1,
                multiplier=1.0,
                total_value=value,
                started_at=_now(),
                last_hit_at=_now(),
                last_hit_time_secs=current_time,
                timeout=self._config.combo_timeout,
            )
            self._combos[combo.combo_id] = combo
            self._stats.total_combos_started += 1
            self._emit_event(FloatingTextEventKind.COMBO_REGISTERED.value, combo.combo_id, {"target_id": target_id, "kind": kind})
        else:
            combo.count += 1
            combo.total_value += value
            combo.last_hit_at = _now()
            combo.last_hit_time_secs = current_time
            # Grow multiplier
            combo.multiplier = _clamp(
                1.0 + (combo.count - 1) * self._config.combo_multiplier_step,
                1.0,
                self._config.combo_max_multiplier,
            )
            self._emit_event(FloatingTextEventKind.COMBO_EXTENDED.value, combo.combo_id, {"count": combo.count, "multiplier": combo.multiplier})

        return combo

    def register_combo(self, target_id: str, kind: str = TextKind.DAMAGE.value, value: float = 0.0, current_time: float = 0.0) -> ComboState:
        """Explicitly register or extend a combo for a target."""
        return self._extend_or_create_combo(target_id, kind, value, current_time)

    def get_combo(self, combo_id: str) -> Optional[ComboState]:
        """Retrieve a combo by ID."""
        return self._combos.get(combo_id)

    def break_combo(self, combo_id: str) -> bool:
        """Break an active combo."""
        combo = self._combos.get(combo_id)
        if combo is None or combo.broken:
            return False
        combo.broken = True
        self._stats.total_combos_broken += 1
        self._combo_history.append({
            "timestamp": _now(),
            "combo_id": combo_id,
            "target_id": combo.target_id,
            "final_count": combo.count,
            "final_multiplier": combo.multiplier,
            "total_value": combo.total_value,
        })
        _evict_fifo_list(self._combo_history, _MAX_COMBO_HISTORY)
        self._emit_event(FloatingTextEventKind.COMBO_BROKEN.value, combo_id, {"final_count": combo.count, "total_value": combo.total_value})
        self._recompute_stats()
        return True

    def list_combos(self, target_id: Optional[str] = None, active_only: bool = False, limit: int = 50) -> List[ComboState]:
        """List combos with optional filters."""
        results = list(self._combos.values())
        if target_id:
            results = [c for c in results if c.target_id == target_id]
        if active_only:
            results = [c for c in results if not c.broken]
        return results[:max(0, int(limit))]

    # ------------------------------------------------------------------
    # Stack Merging
    # ------------------------------------------------------------------

    def merge_stacks(self, merge_radius: Optional[float] = None, kind: Optional[str] = None) -> int:
        """Merge nearby same-kind entries within the merge radius.

        Returns the number of entries merged away.
        """
        if not self._config.merge_enabled:
            return 0
        radius = merge_radius if merge_radius is not None else self._config.merge_radius
        entries = list(self._entries.values())
        if kind:
            entries = [e for e in entries if e.kind == kind]

        merged_count = 0
        consumed: set = set()

        for i, entry in enumerate(entries):
            if entry.entry_id in consumed:
                continue
            for j in range(i + 1, len(entries)):
                other = entries[j]
                if other.entry_id in consumed:
                    continue
                if other.kind != entry.kind:
                    continue
                dist = _distance2d(entry.world_position, other.world_position)
                if dist <= radius:
                    # Merge: accumulate value, keep the first entry
                    entry.value += other.value
                    entry.text = self._format_text(entry.value, entry.kind)
                    consumed.add(other.entry_id)
                    merged_count += 1

        # Remove consumed entries
        for entry_id in consumed:
            self._entries.pop(entry_id, None)

        if merged_count > 0:
            self._stats.total_merged += merged_count
            self._emit_event(FloatingTextEventKind.TEXT_MERGED.value, "", {"merged_count": merged_count, "radius": radius})
            self._recompute_stats()

        return merged_count

    # ------------------------------------------------------------------
    # Kind Configuration
    # ------------------------------------------------------------------

    def set_kind_config(self, config: TextKindConfig) -> TextKindConfig:
        """Update the visual configuration for a text kind."""
        self._kind_configs[config.kind] = config
        self._emit_event(FloatingTextEventKind.KIND_CONFIG_UPDATED.value, config.kind, {"color": config.color, "font_size": config.font_size})
        return config

    def get_kind_config(self, kind: str) -> TextKindConfig:
        """Retrieve the visual configuration for a text kind."""
        return self._get_kind_config(kind)

    def list_kind_configs(self) -> List[TextKindConfig]:
        """List all kind configurations."""
        return list(self._kind_configs.values())

    # ------------------------------------------------------------------
    # Simulation Tick
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 1.0, current_time: float = 0.0) -> Dict[str, Any]:
        """Advance the floating text simulation by one tick.

        Updates entry positions (rise), applies alpha decay, expires entries
        past their lifetime, and breaks combos past their timeout.
        """
        self._tick_count += 1
        expired = 0
        combos_broken = 0

        # Update and expire entries
        to_expire: List[str] = []
        for entry in self._entries.values():
            entry.elapsed += delta_time
            # Apply rise animation
            entry.screen_offset = (entry.screen_offset[0], entry.screen_offset[1] + entry.rise_speed * delta_time)
            if entry.elapsed >= entry.lifetime:
                to_expire.append(entry.entry_id)

        for entry_id in to_expire:
            self._entries.pop(entry_id, None)
            expired += 1
            self._stats.total_expired += 1
            self._emit_event(FloatingTextEventKind.TEXT_EXPIRED.value, entry_id, {})

        # Break expired combos
        for combo in list(self._combos.values()):
            if combo.broken:
                continue
            if current_time - combo.last_hit_time_secs > combo.timeout and combo.last_hit_time_secs > 0:
                combo.broken = True
                combos_broken += 1
                self._stats.total_combos_broken += 1
                self._combo_history.append({
                    "timestamp": _now(),
                    "combo_id": combo.combo_id,
                    "target_id": combo.target_id,
                    "final_count": combo.count,
                    "final_multiplier": combo.multiplier,
                    "total_value": combo.total_value,
                })
                _evict_fifo_list(self._combo_history, _MAX_COMBO_HISTORY)
                self._emit_event(FloatingTextEventKind.COMBO_BROKEN.value, combo.combo_id, {"reason": "timeout", "final_count": combo.count})

        self._recompute_stats()
        return {
            "tick": self._tick_count,
            "expired_entries": expired,
            "combos_broken": combos_broken,
            "active_entries": len(self._entries),
            "active_combos": sum(1 for c in self._combos.values() if not c.broken),
        }

    # ------------------------------------------------------------------
    # Configuration and Observability
    # ------------------------------------------------------------------

    def set_config(self, config: FloatingTextConfig) -> FloatingTextConfig:
        """Update global tuning parameters."""
        self._config = config
        self._emit_event(FloatingTextEventKind.CONFIG_UPDATED.value, "", {"max_active_entries": config.max_active_entries})
        return self._config

    def get_config(self) -> FloatingTextConfig:
        """Retrieve the current configuration."""
        return self._config

    def list_events(self, limit: int = 100) -> List[FloatingTextEvent]:
        """Retrieve recent audit events."""
        return self._events[-max(0, int(limit)):]

    def get_stats(self) -> FloatingTextStats:
        """Retrieve aggregate statistics."""
        self._recompute_stats()
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Retrieve a lightweight status summary."""
        return {
            "initialized": self._initialized,
            "active_entries": len(self._entries),
            "active_combos": sum(1 for c in self._combos.values() if not c.broken),
            "total_combos_started": self._stats.total_combos_started,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> FloatingTextSnapshot:
        """Retrieve a full state snapshot."""
        self._recompute_stats()
        return FloatingTextSnapshot(
            entries=list(self._entries.values()),
            combos=list(self._combos.values()),
            kind_configs=dict(self._kind_configs),
            config=self._config,
            stats=self._stats,
        )

    def reset(self) -> None:
        """Reset the system to its initial seeded state."""
        self._entries.clear()
        self._combos.clear()
        self._kind_configs.clear()
        self._events.clear()
        self._combo_history.clear()
        self._config = FloatingTextConfig()
        self._stats = FloatingTextStats()
        self._tick_count = 0
        self._seed()


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------


def get_floating_text_system() -> FloatingTextSystem:
    """Return the singleton FloatingTextSystem instance."""
    return FloatingTextSystem.get_instance()
