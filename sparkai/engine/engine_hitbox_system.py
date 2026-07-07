"""
SparkLabs Engine - Hitbox System

A combat hitbox/hurtbox runtime for the SparkLabs AI-native game engine.
Hitboxes are active attack volumes that deal damage when they overlap
hurtboxes. Hurtboxes are vulnerable body volumes that receive hits. This
system is distinct from the general physics collision system: it operates
on frame-based activation windows, limb damage multipliers, invulnerability
frames, and team filtering — the precise data structures that melee and
projectile combat games require.

Architecture:
  HitboxSystem (singleton)
    |-- HitboxInstance, HurtboxInstance, LimbProfile,
       HitboxStats, HitboxSnapshot, HitboxEvent
    |-- HitboxShape, HitboxGroup, HitboxStatus, HitboxEventKind

Core Capabilities:
  - register_hitbox / get_hitbox / list_hitboxes / remove_hitbox /
    activate_hitbox / deactivate_hitbox: attack volume lifecycle with
    frame-based activation windows.
  - register_hurtbox / get_hurtbox / list_hurtboxes / remove_hurtbox:
    vulnerable body volume lifecycle with limb multipliers.
  - register_limb / get_limb / list_limbs / remove_limb: limb damage
    profiles with multipliers and critical flags.
  - set_invulnerability: set invulnerability window for an owner.
  - query_hits: check active hitboxes against hurtboxes, returning hit
    results with limb multipliers and team filtering.
  - tick: advance the frame counter, expire finished hitboxes.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`HitboxSystem.get_instance` or the module-level
:func:`get_hitbox_system` factory.
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

_MAX_HITBOXES: int = 5000
_MAX_HURTBOXES: int = 10000
_MAX_LIMBS: int = 500
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


# Default limb damage multipliers
_DEFAULT_LIMB_MULTIPLIERS: Dict[str, float] = {
    "head": 2.0,
    "neck": 1.8,
    "torso": 1.0,
    "arm": 0.7,
    "hand": 0.6,
    "leg": 0.8,
    "foot": 0.5,
    "wing": 1.2,
    "tail": 0.6,
}

_TEAM_FILTER_MODES: Dict[str, str] = {
    "enemy_only": "enemy_only",
    "all": "all",
    "ally_only": "ally_only",
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class HitboxShape(Enum):
    """Geometric shapes for hitbox and hurtbox volumes."""
    BOX = "box"
    SPHERE = "sphere"
    CAPSULE = "capsule"
    CYLINDER = "cylinder"


class HitboxGroup(Enum):
    """Functional groups classifying hitbox purpose."""
    ATTACK = "attack"
    BODY = "body"
    SHIELD = "shield"
    PROJECTILE = "projectile"
    ENVIRONMENT = "environment"


class HitboxStatus(Enum):
    """Lifecycle status of a hitbox instance."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"


class HitboxEventKind(Enum):
    """Audit event types emitted by the hitbox system."""
    HITBOX_REGISTERED = "hitbox_registered"
    HITBOX_REMOVED = "hitbox_removed"
    HITBOX_ACTIVATED = "hitbox_activated"
    HITBOX_DEACTIVATED = "hitbox_deactivated"
    HURTBOX_REGISTERED = "hurtbox_registered"
    HURTBOX_REMOVED = "hurtbox_removed"
    LIMB_REGISTERED = "limb_registered"
    LIMB_REMOVED = "limb_removed"
    INVULN_SET = "invuln_set"
    HIT_DETECTED = "hit_detected"
    HITBOX_EXPIRED = "hitbox_expired"
    FRAME_TICKED = "frame_ticked"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class LimbProfile:
    """Damage profile for a body limb."""
    limb_name: str = ""
    damage_multiplier: float = 1.0
    is_critical: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HitboxInstance:
    """An active attack volume with frame-based activation window."""
    instance_id: str = ""
    owner_id: str = ""
    group: str = HitboxGroup.ATTACK.value
    shape: str = HitboxShape.BOX.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    damage_multiplier: float = 1.0
    active_frames_start: int = 0
    active_frames_end: int = 30
    current_frame: int = 0
    limb_name: str = ""
    team_id: str = ""
    team_filter_mode: str = "enemy_only"
    status: str = HitboxStatus.INACTIVE.value
    hit_targets: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HurtboxInstance:
    """A vulnerable body volume that receives hits."""
    instance_id: str = ""
    owner_id: str = ""
    group: str = HitboxGroup.BODY.value
    shape: str = HitboxShape.BOX.value
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    dimensions: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    limb_name: str = "torso"
    limb_multiplier: float = 1.0
    team_id: str = ""
    invulnerable_until_frame: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HitboxStats:
    """Aggregate statistics for the hitbox system."""
    total_hitboxes: int = 0
    total_hurtboxes: int = 0
    total_limbs: int = 0
    active_hitboxes: int = 0
    total_hits_detected: int = 0
    total_expired: int = 0
    total_ticks: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HitboxSnapshot:
    """Point-in-time snapshot of hitbox system state."""
    total_hitboxes: int = 0
    total_hurtboxes: int = 0
    total_limbs: int = 0
    active_hitboxes: int = 0
    current_frame: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HitboxEvent:
    """An audit event emitted by the hitbox system."""
    event_id: str = ""
    kind: str = HitboxEventKind.HITBOX_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# HitboxSystem Singleton
# ---------------------------------------------------------------------------


class HitboxSystem:
    """Combat hitbox/hurtbox runtime with frame-based activation.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["HitboxSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._hitboxes: Dict[str, HitboxInstance] = {}
        self._hurtboxes: Dict[str, HurtboxInstance] = {}
        self._limbs: Dict[str, LimbProfile] = {}
        self._invuln_windows: Dict[str, int] = {}
        self._events: List[HitboxEvent] = []
        self._current_frame: int = 0
        self._stats = HitboxStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "HitboxSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed initial limb profiles, hitboxes, and hurtboxes."""
        for limb_name, mult in _DEFAULT_LIMB_MULTIPLIERS.items():
            is_crit = limb_name in ("head", "neck")
            self._limbs[limb_name] = LimbProfile(
                limb_name=limb_name,
                damage_multiplier=mult,
                is_critical=is_crit,
            )

        seeded_hurtboxes = [
            HurtboxInstance(
                instance_id="htb_hero_torso",
                owner_id="actor_hero_1",
                group=HitboxGroup.BODY.value,
                shape=HitboxShape.BOX.value,
                position=(0.0, 1.0, 0.0),
                dimensions=(0.6, 0.8, 0.3),
                limb_name="torso",
                limb_multiplier=1.0,
                team_id="team_blue",
            ),
            HurtboxInstance(
                instance_id="htb_hero_head",
                owner_id="actor_hero_1",
                group=HitboxGroup.BODY.value,
                shape=HitboxShape.SPHERE.value,
                position=(0.0, 1.7, 0.0),
                dimensions=(0.25, 0.25, 0.25),
                limb_name="head",
                limb_multiplier=2.0,
                team_id="team_blue",
            ),
            HurtboxInstance(
                instance_id="htb_enemy_torso",
                owner_id="actor_grunt_1",
                group=HitboxGroup.BODY.value,
                shape=HitboxShape.BOX.value,
                position=(5.0, 1.0, 0.0),
                dimensions=(0.6, 0.8, 0.3),
                limb_name="torso",
                limb_multiplier=1.0,
                team_id="team_red",
            ),
            HurtboxInstance(
                instance_id="htb_enemy_head",
                owner_id="actor_grunt_1",
                group=HitboxGroup.BODY.value,
                shape=HitboxShape.SPHERE.value,
                position=(5.0, 1.7, 0.0),
                dimensions=(0.25, 0.25, 0.25),
                limb_name="head",
                limb_multiplier=2.0,
                team_id="team_red",
            ),
        ]
        for hb in seeded_hurtboxes:
            self._hurtboxes[hb.instance_id] = hb

        seeded_hitboxes = [
            HitboxInstance(
                instance_id="htb_hero_swing",
                owner_id="actor_hero_1",
                group=HitboxGroup.ATTACK.value,
                shape=HitboxShape.BOX.value,
                position=(1.0, 1.0, 0.5),
                dimensions=(1.2, 0.8, 0.5),
                damage_multiplier=1.5,
                active_frames_start=5,
                active_frames_end=15,
                current_frame=0,
                limb_name="hand",
                team_id="team_blue",
                team_filter_mode="enemy_only",
                status=HitboxStatus.INACTIVE.value,
            ),
            HitboxInstance(
                instance_id="htb_enemy_slam",
                owner_id="actor_grunt_1",
                group=HitboxGroup.ATTACK.value,
                shape=HitboxShape.SPHERE.value,
                position=(4.0, 0.5, 0.0),
                dimensions=(1.5, 1.5, 1.5),
                damage_multiplier=1.2,
                active_frames_start=10,
                active_frames_end=25,
                current_frame=0,
                limb_name="hand",
                team_id="team_red",
                team_filter_mode="enemy_only",
                status=HitboxStatus.INACTIVE.value,
            ),
        ]
        for hb in seeded_hitboxes:
            self._hitboxes[hb.instance_id] = hb

        self._stats.total_hitboxes = len(self._hitboxes)
        self._stats.total_hurtboxes = len(self._hurtboxes)
        self._stats.total_limbs = len(self._limbs)
        self._initialized = True

    def _emit(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> None:
        event = HitboxEvent(
            event_id=_new_id("evt"),
            kind=kind,
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Hitbox Lifecycle
    # ------------------------------------------------------------------

    def register_hitbox(self, hitbox: HitboxInstance) -> HitboxInstance:
        if not hitbox.instance_id:
            hitbox.instance_id = _new_id("htb")
        if hitbox.limb_name and hitbox.limb_name in self._limbs:
            limb = self._limbs[hitbox.limb_name]
            if hitbox.damage_multiplier == 1.0:
                hitbox.damage_multiplier = limb.damage_multiplier
        self._hitboxes[hitbox.instance_id] = hitbox
        _evict_fifo_dict(self._hitboxes, _MAX_HITBOXES)
        self._stats.total_hitboxes = len(self._hitboxes)
        self._emit(HitboxEventKind.HITBOX_REGISTERED.value, {"instance_id": hitbox.instance_id})
        return hitbox

    def get_hitbox(self, instance_id: str) -> Optional[HitboxInstance]:
        return self._hitboxes.get(instance_id)

    def list_hitboxes(
        self,
        owner_id: str = "",
        group: str = "",
        status: str = "",
        team_id: str = "",
        limit: int = 50,
    ) -> List[HitboxInstance]:
        results: List[HitboxInstance] = []
        for hb in self._hitboxes.values():
            if owner_id and hb.owner_id != owner_id:
                continue
            if group and hb.group != group:
                continue
            if status and hb.status != status:
                continue
            if team_id and hb.team_id != team_id:
                continue
            results.append(hb)
        return results[:max(0, int(limit))]

    def remove_hitbox(self, instance_id: str) -> bool:
        existed = self._hitboxes.pop(instance_id, None) is not None
        if existed:
            self._stats.total_hitboxes = len(self._hitboxes)
            self._emit(HitboxEventKind.HITBOX_REMOVED.value, {"instance_id": instance_id})
        return existed

    def activate_hitbox(self, instance_id: str) -> Optional[HitboxInstance]:
        hb = self._hitboxes.get(instance_id)
        if hb is None:
            return None
        hb.status = HitboxStatus.ACTIVE.value
        hb.current_frame = 0
        self._emit(HitboxEventKind.HITBOX_ACTIVATED.value, {"instance_id": instance_id})
        return hb

    def deactivate_hitbox(self, instance_id: str) -> Optional[HitboxInstance]:
        hb = self._hitboxes.get(instance_id)
        if hb is None:
            return None
        hb.status = HitboxStatus.INACTIVE.value
        self._emit(HitboxEventKind.HITBOX_DEACTIVATED.value, {"instance_id": instance_id})
        return hb

    # ------------------------------------------------------------------
    # Hurtbox Lifecycle
    # ------------------------------------------------------------------

    def register_hurtbox(self, hurtbox: HurtboxInstance) -> HurtboxInstance:
        if not hurtbox.instance_id:
            hurtbox.instance_id = _new_id("htb")
        if hurtbox.limb_name and hurtbox.limb_name in self._limbs:
            limb = self._limbs[hurtbox.limb_name]
            if hurtbox.limb_multiplier == 1.0:
                hurtbox.limb_multiplier = limb.damage_multiplier
        self._hurtboxes[hurtbox.instance_id] = hurtbox
        _evict_fifo_dict(self._hurtboxes, _MAX_HURTBOXES)
        self._stats.total_hurtboxes = len(self._hurtboxes)
        self._emit(HitboxEventKind.HURTBOX_REGISTERED.value, {"instance_id": hurtbox.instance_id})
        return hurtbox

    def get_hurtbox(self, instance_id: str) -> Optional[HurtboxInstance]:
        return self._hurtboxes.get(instance_id)

    def list_hurtboxes(
        self,
        owner_id: str = "",
        group: str = "",
        team_id: str = "",
        limit: int = 50,
    ) -> List[HurtboxInstance]:
        results: List[HurtboxInstance] = []
        for hb in self._hurtboxes.values():
            if owner_id and hb.owner_id != owner_id:
                continue
            if group and hb.group != group:
                continue
            if team_id and hb.team_id != team_id:
                continue
            results.append(hb)
        return results[:max(0, int(limit))]

    def remove_hurtbox(self, instance_id: str) -> bool:
        existed = self._hurtboxes.pop(instance_id, None) is not None
        if existed:
            self._stats.total_hurtboxes = len(self._hurtboxes)
            self._emit(HitboxEventKind.HURTBOX_REMOVED.value, {"instance_id": instance_id})
        return existed

    # ------------------------------------------------------------------
    # Limb Profiles
    # ------------------------------------------------------------------

    def register_limb(self, limb: LimbProfile) -> LimbProfile:
        if not limb.limb_name:
            limb.limb_name = _new_id("lmb")
        self._limbs[limb.limb_name] = limb
        _evict_fifo_dict(self._limbs, _MAX_LIMBS)
        self._stats.total_limbs = len(self._limbs)
        self._emit(HitboxEventKind.LIMB_REGISTERED.value, {"limb_name": limb.limb_name})
        return limb

    def get_limb(self, limb_name: str) -> Optional[LimbProfile]:
        return self._limbs.get(limb_name)

    def list_limbs(self, limit: int = 50) -> List[LimbProfile]:
        return list(self._limbs.values())[:max(0, int(limit))]

    def remove_limb(self, limb_name: str) -> bool:
        existed = self._limbs.pop(limb_name, None) is not None
        if existed:
            self._stats.total_limbs = len(self._limbs)
            self._emit(HitboxEventKind.LIMB_REMOVED.value, {"limb_name": limb_name})
        return existed

    # ------------------------------------------------------------------
    # Invulnerability
    # ------------------------------------------------------------------

    def set_invulnerability(self, owner_id: str, until_frame: int) -> int:
        self._invuln_windows[owner_id] = _safe_int(until_frame, 0)
        self._emit(
            HitboxEventKind.INVULN_SET.value,
            {"owner_id": owner_id, "until_frame": until_frame},
        )
        return until_frame

    def is_invulnerable(self, owner_id: str, frame: int = -1) -> bool:
        check_frame = frame if frame >= 0 else self._current_frame
        until = self._invuln_windows.get(owner_id, 0)
        return check_frame < until

    # ------------------------------------------------------------------
    # Hit Query and Tick
    # ------------------------------------------------------------------

    def query_hits(self, active_only: bool = True) -> Dict[str, Any]:
        """Query active hitboxes against hurtboxes, returning hit results.

        Returns dict with ok, hits, hit_count.
        """
        hits: List[Dict[str, Any]] = []
        for hb in self._hitboxes.values():
            if active_only and hb.status != HitboxStatus.ACTIVE.value:
                continue
            if not (hb.active_frames_start <= hb.current_frame <= hb.active_frames_end):
                continue
            for htb in self._hurtboxes.values():
                if hb.owner_id == htb.owner_id:
                    continue
                if hb.team_filter_mode == "enemy_only" and hb.team_id == htb.team_id:
                    continue
                if hb.team_filter_mode == "ally_only" and hb.team_id != htb.team_id:
                    continue
                if self.is_invulnerable(htb.owner_id, hb.current_frame):
                    continue
                if htb.owner_id in hb.hit_targets:
                    continue
                pos_diff = (
                    abs(hb.position[0] - htb.position[0]),
                    abs(hb.position[1] - htb.position[1]),
                    abs(hb.position[2] - htb.position[2]),
                )
                overlap = (
                    pos_diff[0] < (hb.dimensions[0] + htb.dimensions[0]) * 0.5
                    and pos_diff[1] < (hb.dimensions[1] + htb.dimensions[1]) * 0.5
                    and pos_diff[2] < (hb.dimensions[2] + htb.dimensions[2]) * 0.5
                )
                if not overlap:
                    continue
                limb_mult = htb.limb_multiplier
                if htb.limb_name in self._limbs:
                    limb_mult = self._limbs[htb.limb_name].damage_multiplier
                final_damage = hb.damage_multiplier * limb_mult
                hb.hit_targets.append(htb.owner_id)
                hits.append({
                    "hitbox_id": hb.instance_id,
                    "hurtbox_id": htb.instance_id,
                    "attacker_id": hb.owner_id,
                    "victim_id": htb.owner_id,
                    "limb_name": htb.limb_name,
                    "base_multiplier": hb.damage_multiplier,
                    "limb_multiplier": limb_mult,
                    "final_damage": round(final_damage, 4),
                    "frame": hb.current_frame,
                })
        self._stats.total_hits_detected += len(hits)
        if hits:
            self._emit(
                HitboxEventKind.HIT_DETECTED.value,
                {"hit_count": len(hits)},
            )
        return {"ok": True, "hits": hits, "hit_count": len(hits)}

    def tick(self, frames: int = 1) -> Dict[str, Any]:
        """Advance the frame counter and expire finished hitboxes.

        Returns dict with ok, frame, expired_count.
        """
        advance = max(1, _safe_int(frames, 1))
        self._current_frame += advance
        expired_count = 0
        for hb in self._hitboxes.values():
            if hb.status != HitboxStatus.ACTIVE.value:
                continue
            hb.current_frame += advance
            if hb.current_frame > hb.active_frames_end:
                hb.status = HitboxStatus.EXPIRED.value
                expired_count += 1
        self._stats.total_expired += expired_count
        self._stats.total_ticks += 1
        active_count = sum(
            1 for hb in self._hitboxes.values()
            if hb.status == HitboxStatus.ACTIVE.value
        )
        self._stats.active_hitboxes = active_count
        if expired_count > 0:
            self._emit(
                HitboxEventKind.HITBOX_EXPIRED.value,
                {"expired_count": expired_count},
            )
        self._emit(
            HitboxEventKind.FRAME_TICKED.value,
            {"frame": self._current_frame, "expired": expired_count},
        )
        return {
            "ok": True,
            "frame": self._current_frame,
            "expired_count": expired_count,
            "active_hitboxes": active_count,
        }

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[HitboxEvent]:
        results: List[HitboxEvent] = []
        for event in reversed(self._events):
            if kind and event.kind != kind:
                continue
            results.append(event)
            if len(results) >= max(0, int(limit)):
                break
        return results

    def get_stats(self) -> HitboxStats:
        self._stats.total_hitboxes = len(self._hitboxes)
        self._stats.total_hurtboxes = len(self._hurtboxes)
        self._stats.total_limbs = len(self._limbs)
        self._stats.active_hitboxes = sum(
            1 for hb in self._hitboxes.values()
            if hb.status == HitboxStatus.ACTIVE.value
        )
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "hitboxes": len(self._hitboxes),
            "hurtboxes": len(self._hurtboxes),
            "limbs": len(self._limbs),
            "active_hitboxes": sum(
                1 for hb in self._hitboxes.values()
                if hb.status == HitboxStatus.ACTIVE.value
            ),
            "current_frame": self._current_frame,
            "events": len(self._events),
        }

    def get_snapshot(self) -> HitboxSnapshot:
        return HitboxSnapshot(
            total_hitboxes=len(self._hitboxes),
            total_hurtboxes=len(self._hurtboxes),
            total_limbs=len(self._limbs),
            active_hitboxes=sum(
                1 for hb in self._hitboxes.values()
                if hb.status == HitboxStatus.ACTIVE.value
            ),
            current_frame=self._current_frame,
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._hitboxes.clear()
            self._hurtboxes.clear()
            self._limbs.clear()
            self._invuln_windows.clear()
            self._events.clear()
            self._current_frame = 0
            self._stats = HitboxStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_hitbox_system() -> HitboxSystem:
    """Get the singleton HitboxSystem instance."""
    return HitboxSystem.get_instance()
