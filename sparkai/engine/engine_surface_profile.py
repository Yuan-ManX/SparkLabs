"""
SparkLabs Engine - Surface Profile System

A cross-domain surface material mapper for the SparkLabs AI-native game
engine. Each surface profile binds a named surface kind (metal, wood,
stone, grass, water, sand, ice, glass, flesh, fabric, dirt, concrete,
snow, lava, slime) to properties across four domains:

  - Physics: friction, restitution, density
  - Audio: footstep sound id, impact sound id, roll sound id
  - Particles: impact effect id, footprint effect id, dust effect id
  - Gameplay: damage multiplier, movement speed modifier, slipperiness

This is distinct from the physics material library (which only handles
friction and restitution) and the rendering material system (which
handles shaders and textures). Surface profiles are the single source
of truth for "what happens when something touches this surface" across
all engine subsystems.

Architecture:
  SurfaceProfileSystem (singleton)
    |-- SurfaceProfile, SurfaceImpact, SurfaceStats, SurfaceSnapshot,
       SurfaceEvent
    |-- SurfaceKind, SurfaceEventKind

Core Capabilities:
  - register_profile / get_profile / list_profiles / update_profile /
    remove_profile: surface profile lifecycle.
  - resolve_surface: look up a profile by kind, returning full
    cross-domain property set.
  - compute_footstep: compute footstep audio and particle effect for a
    surface kind, scaled by speed and weight.
  - compute_impact: compute impact audio, particle effect, damage
    multiplier, and decal for a surface kind, scaled by impact speed
    and mass.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`SurfaceProfileSystem.get_instance` or the module-level
:func:`get_surface_profile` factory.
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

_MAX_PROFILES: int = 500
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


# Default surface profiles
_DEFAULT_PROFILES: Dict[str, Dict[str, Any]] = {
    "metal": {
        "friction": 0.3, "restitution": 0.2, "density": 7800.0,
        "footstep_sound": "sfx_fs_metal", "impact_sound": "sfx_imp_metal", "roll_sound": "sfx_roll_metal",
        "impact_effect": "vfx_spark_metal", "footprint_effect": "vfx_fp_metal", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 1.3, "speed_modifier": 0.95, "slipperiness": 0.1,
    },
    "wood": {
        "friction": 0.6, "restitution": 0.3, "density": 700.0,
        "footstep_sound": "sfx_fs_wood", "impact_sound": "sfx_imp_wood", "roll_sound": "sfx_roll_wood",
        "impact_effect": "vfx_chip_wood", "footprint_effect": "vfx_fp_wood", "dust_effect": "vfx_dust_wood",
        "damage_multiplier": 0.8, "speed_modifier": 1.0, "slipperiness": 0.15,
    },
    "stone": {
        "friction": 0.8, "restitution": 0.1, "density": 2700.0,
        "footstep_sound": "sfx_fs_stone", "impact_sound": "sfx_imp_stone", "roll_sound": "sfx_roll_stone",
        "impact_effect": "vfx_chip_stone", "footprint_effect": "vfx_fp_stone", "dust_effect": "vfx_dust_stone",
        "damage_multiplier": 1.0, "speed_modifier": 0.9, "slipperiness": 0.05,
    },
    "grass": {
        "friction": 0.5, "restitution": 0.15, "density": 100.0,
        "footstep_sound": "sfx_fs_grass", "impact_sound": "sfx_imp_grass", "roll_sound": "sfx_roll_grass",
        "impact_effect": "vfx_blade_grass", "footprint_effect": "vfx_fp_grass", "dust_effect": "vfx_dust_grass",
        "damage_multiplier": 0.5, "speed_modifier": 1.0, "slipperiness": 0.1,
    },
    "water": {
        "friction": 0.05, "restitution": 0.0, "density": 1000.0,
        "footstep_sound": "sfx_fs_water", "impact_sound": "sfx_imp_water", "roll_sound": "sfx_roll_water",
        "impact_effect": "vfx_splash_water", "footprint_effect": "vfx_fp_water", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 0.3, "speed_modifier": 0.6, "slipperiness": 0.8,
    },
    "sand": {
        "friction": 0.7, "restitution": 0.05, "density": 1600.0,
        "footstep_sound": "sfx_fs_sand", "impact_sound": "sfx_imp_sand", "roll_sound": "sfx_roll_sand",
        "impact_effect": "vfx_puff_sand", "footprint_effect": "vfx_fp_sand", "dust_effect": "vfx_dust_sand",
        "damage_multiplier": 0.4, "speed_modifier": 0.85, "slipperiness": 0.05,
    },
    "ice": {
        "friction": 0.02, "restitution": 0.05, "density": 920.0,
        "footstep_sound": "sfx_fs_ice", "impact_sound": "sfx_imp_ice", "roll_sound": "sfx_roll_ice",
        "impact_effect": "vfx_shard_ice", "footprint_effect": "vfx_fp_ice", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 0.9, "speed_modifier": 1.3, "slipperiness": 0.95,
    },
    "glass": {
        "friction": 0.4, "restitution": 0.3, "density": 2500.0,
        "footstep_sound": "sfx_fs_glass", "impact_sound": "sfx_imp_glass", "roll_sound": "sfx_roll_glass",
        "impact_effect": "vfx_shard_glass", "footprint_effect": "vfx_fp_glass", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 1.5, "speed_modifier": 1.0, "slipperiness": 0.2,
    },
    "flesh": {
        "friction": 0.9, "restitution": 0.05, "density": 1010.0,
        "footstep_sound": "sfx_fs_flesh", "impact_sound": "sfx_imp_flesh", "roll_sound": "sfx_roll_flesh",
        "impact_effect": "vfx_blood_flesh", "footprint_effect": "vfx_fp_flesh", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 1.8, "speed_modifier": 0.95, "slipperiness": 0.3,
    },
    "fabric": {
        "friction": 0.7, "restitution": 0.1, "density": 200.0,
        "footstep_sound": "sfx_fs_fabric", "impact_sound": "sfx_imp_fabric", "roll_sound": "sfx_roll_fabric",
        "impact_effect": "vfx_fiber_fabric", "footprint_effect": "vfx_fp_fabric", "dust_effect": "vfx_dust_none",
        "damage_multiplier": 0.6, "speed_modifier": 1.0, "slipperiness": 0.1,
    },
    "dirt": {
        "friction": 0.65, "restitution": 0.1, "density": 1300.0,
        "footstep_sound": "sfx_fs_dirt", "impact_sound": "sfx_imp_dirt", "roll_sound": "sfx_roll_dirt",
        "impact_effect": "vfx_clod_dirt", "footprint_effect": "vfx_fp_dirt", "dust_effect": "vfx_dust_dirt",
        "damage_multiplier": 0.7, "speed_modifier": 0.92, "slipperiness": 0.08,
    },
    "concrete": {
        "friction": 0.85, "restitution": 0.05, "density": 2400.0,
        "footstep_sound": "sfx_fs_concrete", "impact_sound": "sfx_imp_concrete", "roll_sound": "sfx_roll_concrete",
        "impact_effect": "vfx_chip_concrete", "footprint_effect": "vfx_fp_concrete", "dust_effect": "vfx_dust_concrete",
        "damage_multiplier": 1.1, "speed_modifier": 0.95, "slipperiness": 0.03,
    },
    "snow": {
        "friction": 0.3, "restitution": 0.1, "density": 300.0,
        "footstep_sound": "sfx_fs_snow", "impact_sound": "sfx_imp_snow", "roll_sound": "sfx_roll_snow",
        "impact_effect": "vfx_puff_snow", "footprint_effect": "vfx_fp_snow", "dust_effect": "vfx_dust_snow",
        "damage_multiplier": 0.6, "speed_modifier": 0.8, "slipperiness": 0.2,
    },
    "lava": {
        "friction": 0.4, "restitution": 0.0, "density": 3100.0,
        "footstep_sound": "sfx_fs_lava", "impact_sound": "sfx_imp_lava", "roll_sound": "sfx_roll_lava",
        "impact_effect": "vfx_bubble_lava", "footprint_effect": "vfx_fp_lava", "dust_effect": "vfx_ember_lava",
        "damage_multiplier": 3.0, "speed_modifier": 0.7, "slipperiness": 0.15,
    },
    "slime": {
        "friction": 0.15, "restitution": 0.2, "density": 1100.0,
        "footstep_sound": "sfx_fs_slime", "impact_sound": "sfx_imp_slime", "roll_sound": "sfx_roll_slime",
        "impact_effect": "vfx_splat_slime", "footprint_effect": "vfx_fp_slime", "dust_effect": "vfx_drip_slime",
        "damage_multiplier": 0.8, "speed_modifier": 0.75, "slipperiness": 0.7,
    },
}


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class SurfaceKind(Enum):
    """Named surface kinds with cross-domain properties."""
    METAL = "metal"
    WOOD = "wood"
    STONE = "stone"
    GRASS = "grass"
    WATER = "water"
    SAND = "sand"
    ICE = "ice"
    GLASS = "glass"
    FLESH = "flesh"
    FABRIC = "fabric"
    DIRT = "dirt"
    CONCRETE = "concrete"
    SNOW = "snow"
    LAVA = "lava"
    SLIME = "slime"


class SurfaceEventKind(Enum):
    """Audit event types emitted by the surface profile system."""
    PROFILE_REGISTERED = "profile_registered"
    PROFILE_REMOVED = "profile_removed"
    PROFILE_UPDATED = "profile_updated"
    SURFACE_RESOLVED = "surface_resolved"
    FOOTSTEP_COMPUTED = "footstep_computed"
    IMPACT_COMPUTED = "impact_computed"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class SurfaceProfile:
    """A cross-domain surface property profile."""
    surface_kind: str = SurfaceKind.STONE.value
    name: str = ""
    friction: float = 0.8
    restitution: float = 0.1
    density: float = 2700.0
    footstep_sound: str = ""
    impact_sound: str = ""
    roll_sound: str = ""
    impact_effect: str = ""
    footprint_effect: str = ""
    dust_effect: str = ""
    damage_multiplier: float = 1.0
    speed_modifier: float = 1.0
    slipperiness: float = 0.05
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SurfaceImpact:
    """Result of an impact computation on a surface."""
    surface_kind: str = SurfaceKind.STONE.value
    impact_sound: str = ""
    impact_effect: str = ""
    dust_effect: str = ""
    damage_multiplier: float = 1.0
    impact_speed: float = 0.0
    mass: float = 1.0
    computed_damage: float = 0.0
    decal_scale: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SurfaceStats:
    """Aggregate statistics for the surface profile system."""
    total_profiles: int = 0
    total_resolves: int = 0
    total_footsteps: int = 0
    total_impacts: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SurfaceSnapshot:
    """Point-in-time snapshot of surface system state."""
    total_profiles: int = 0
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SurfaceEvent:
    """An audit event emitted by the surface profile system."""
    event_id: str = ""
    kind: str = SurfaceEventKind.PROFILE_REGISTERED.value
    timestamp: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Surface Profile System Singleton
# ---------------------------------------------------------------------------


class SurfaceProfileSystem:
    """Cross-domain surface material mapper.

    Implements the singleton pattern with double-checked locking.
    """

    _instance: Optional["SurfaceProfileSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._initialized: bool = False
        self._profiles: Dict[str, SurfaceProfile] = {}
        self._events: List[SurfaceEvent] = []
        self._stats = SurfaceStats()
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "SurfaceProfileSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _seed(self) -> None:
        """Seed default surface profiles."""
        for kind, props in _DEFAULT_PROFILES.items():
            profile = SurfaceProfile(
                surface_kind=kind,
                name=kind.capitalize(),
                friction=props["friction"],
                restitution=props["restitution"],
                density=props["density"],
                footstep_sound=props["footstep_sound"],
                impact_sound=props["impact_sound"],
                roll_sound=props["roll_sound"],
                impact_effect=props["impact_effect"],
                footprint_effect=props["footprint_effect"],
                dust_effect=props["dust_effect"],
                damage_multiplier=props["damage_multiplier"],
                speed_modifier=props["speed_modifier"],
                slipperiness=props["slipperiness"],
                metadata={},
            )
            self._profiles[kind] = profile
        self._stats.total_profiles = len(self._profiles)
        self._initialized = True

    def _emit(self, kind: str, payload: Dict[str, Any]) -> None:
        event = SurfaceEvent(
            event_id=_new_id("sfe"),
            kind=kind,
            timestamp=_now(),
            payload=payload,
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Profile Lifecycle
    # ------------------------------------------------------------------

    def register_profile(self, profile: SurfaceProfile) -> SurfaceProfile:
        if not profile.surface_kind:
            profile.surface_kind = _new_id("srf")
        if not profile.name:
            profile.name = profile.surface_kind.capitalize()
        self._profiles[profile.surface_kind] = profile
        _evict_fifo_dict(self._profiles, _MAX_PROFILES)
        self._stats.total_profiles = len(self._profiles)
        self._emit(
            SurfaceEventKind.PROFILE_REGISTERED.value,
            {"surface_kind": profile.surface_kind},
        )
        return profile

    def get_profile(self, surface_kind: str) -> Optional[SurfaceProfile]:
        return self._profiles.get(surface_kind)

    def list_profiles(self, limit: int = 100) -> List[SurfaceProfile]:
        results = list(self._profiles.values())
        return results[:max(0, int(limit))]

    def update_profile(
        self, surface_kind: str, updates: Dict[str, Any]
    ) -> Optional[SurfaceProfile]:
        profile = self._profiles.get(surface_kind)
        if profile is None:
            return None
        if "name" in updates:
            profile.name = str(updates["name"])
        if "friction" in updates:
            profile.friction = _safe_float(updates["friction"], profile.friction)
        if "restitution" in updates:
            profile.restitution = _safe_float(updates["restitution"], profile.restitution)
        if "density" in updates:
            profile.density = _safe_float(updates["density"], profile.density)
        if "footstep_sound" in updates:
            profile.footstep_sound = str(updates["footstep_sound"])
        if "impact_sound" in updates:
            profile.impact_sound = str(updates["impact_sound"])
        if "roll_sound" in updates:
            profile.roll_sound = str(updates["roll_sound"])
        if "impact_effect" in updates:
            profile.impact_effect = str(updates["impact_effect"])
        if "footprint_effect" in updates:
            profile.footprint_effect = str(updates["footprint_effect"])
        if "dust_effect" in updates:
            profile.dust_effect = str(updates["dust_effect"])
        if "damage_multiplier" in updates:
            profile.damage_multiplier = _safe_float(updates["damage_multiplier"], profile.damage_multiplier)
        if "speed_modifier" in updates:
            profile.speed_modifier = _safe_float(updates["speed_modifier"], profile.speed_modifier)
        if "slipperiness" in updates:
            profile.slipperiness = _clamp(_safe_float(updates["slipperiness"], profile.slipperiness))
        if "metadata" in updates:
            profile.metadata = updates["metadata"]
        self._emit(
            SurfaceEventKind.PROFILE_UPDATED.value,
            {"surface_kind": surface_kind},
        )
        return profile

    def remove_profile(self, surface_kind: str) -> bool:
        existed = self._profiles.pop(surface_kind, None) is not None
        if existed:
            self._stats.total_profiles = len(self._profiles)
            self._emit(
                SurfaceEventKind.PROFILE_REMOVED.value,
                {"surface_kind": surface_kind},
            )
        return existed

    # ------------------------------------------------------------------
    # Surface Resolution
    # ------------------------------------------------------------------

    def resolve_surface(self, surface_kind: str) -> Dict[str, Any]:
        """Look up a surface profile by kind, returning all properties."""
        profile = self._profiles.get(surface_kind)
        self._stats.total_resolves += 1
        if profile is None:
            self._emit(
                SurfaceEventKind.SURFACE_RESOLVED.value,
                {"surface_kind": surface_kind, "found": False},
            )
            return {
                "found": False,
                "surface_kind": surface_kind,
                "friction": 0.5,
                "restitution": 0.1,
                "density": 1000.0,
                "footstep_sound": "",
                "impact_sound": "",
                "roll_sound": "",
                "impact_effect": "",
                "footprint_effect": "",
                "dust_effect": "",
                "damage_multiplier": 1.0,
                "speed_modifier": 1.0,
                "slipperiness": 0.1,
            }
        self._emit(
            SurfaceEventKind.SURFACE_RESOLVED.value,
            {"surface_kind": surface_kind, "found": True},
        )
        result = profile.to_dict()
        result["found"] = True
        return result

    # ------------------------------------------------------------------
    # Footstep Computation
    # ------------------------------------------------------------------

    def compute_footstep(
        self,
        surface_kind: str,
        speed: float = 1.0,
        weight: float = 1.0,
    ) -> Dict[str, Any]:
        """Compute footstep audio and particle effect for a surface."""
        profile = self._profiles.get(surface_kind)
        self._stats.total_footsteps += 1
        if profile is None:
            self._emit(
                SurfaceEventKind.FOOTSTEP_COMPUTED.value,
                {"surface_kind": surface_kind, "found": False},
            )
            return {
                "found": False,
                "surface_kind": surface_kind,
                "footstep_sound": "",
                "footprint_effect": "",
                "volume": 0.5,
                "particle_scale": 1.0,
            }
        speed_factor = _clamp(speed / 5.0)
        weight_factor = _clamp(weight / 70.0)
        volume = 0.3 + speed_factor * 0.5 + weight_factor * 0.2
        particle_scale = 0.5 + speed_factor * 1.0 + weight_factor * 0.5
        self._emit(
            SurfaceEventKind.FOOTSTEP_COMPUTED.value,
            {
                "surface_kind": surface_kind,
                "speed": speed,
                "weight": weight,
                "volume": volume,
            },
        )
        return {
            "found": True,
            "surface_kind": surface_kind,
            "footstep_sound": profile.footstep_sound,
            "footprint_effect": profile.footprint_effect,
            "dust_effect": profile.dust_effect,
            "volume": _clamp(volume),
            "particle_scale": particle_scale,
            "speed_modifier": profile.speed_modifier,
            "slipperiness": profile.slipperiness,
        }

    # ------------------------------------------------------------------
    # Impact Computation
    # ------------------------------------------------------------------

    def compute_impact(
        self,
        surface_kind: str,
        impact_speed: float = 1.0,
        mass: float = 1.0,
    ) -> Dict[str, Any]:
        """Compute impact audio, particle, and damage for a surface."""
        profile = self._profiles.get(surface_kind)
        self._stats.total_impacts += 1
        if profile is None:
            self._emit(
                SurfaceEventKind.IMPACT_COMPUTED.value,
                {"surface_kind": surface_kind, "found": False},
            )
            return {
                "found": False,
                "surface_kind": surface_kind,
                "impact_sound": "",
                "impact_effect": "",
                "dust_effect": "",
                "damage_multiplier": 1.0,
                "computed_damage": 0.0,
                "decal_scale": 1.0,
            }
        speed_factor = _clamp(impact_speed / 20.0)
        mass_factor = _clamp(mass / 10.0)
        computed_damage = impact_speed * mass * profile.damage_multiplier * 0.01
        decal_scale = 0.5 + speed_factor * 2.0 + mass_factor * 1.0
        volume = 0.2 + speed_factor * 0.6 + mass_factor * 0.2
        impact = SurfaceImpact(
            surface_kind=surface_kind,
            impact_sound=profile.impact_sound,
            impact_effect=profile.impact_effect,
            dust_effect=profile.dust_effect,
            damage_multiplier=profile.damage_multiplier,
            impact_speed=impact_speed,
            mass=mass,
            computed_damage=computed_damage,
            decal_scale=decal_scale,
            metadata={"volume": _clamp(volume)},
        )
        self._emit(
            SurfaceEventKind.IMPACT_COMPUTED.value,
            {
                "surface_kind": surface_kind,
                "impact_speed": impact_speed,
                "mass": mass,
                "damage": computed_damage,
            },
        )
        return impact.to_dict()

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, kind: str = "", limit: int = 50) -> List[SurfaceEvent]:
        results: List[SurfaceEvent] = []
        for e in reversed(self._events):
            if kind and e.kind != kind:
                continue
            results.append(e)
            if len(results) >= max(1, int(limit)):
                break
        return results

    def get_stats(self) -> SurfaceStats:
        self._stats.total_profiles = len(self._profiles)
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "profiles": len(self._profiles),
            "events": len(self._events),
        }

    def get_snapshot(self) -> SurfaceSnapshot:
        return SurfaceSnapshot(
            total_profiles=len(self._profiles),
            timestamp=_now(),
        )

    def reset(self) -> None:
        with self._init_lock:
            self._profiles.clear()
            self._events.clear()
            self._stats = SurfaceStats()
            self._seed()


# ---------------------------------------------------------------------------
# Module-level Factory
# ---------------------------------------------------------------------------


def get_surface_profile() -> SurfaceProfileSystem:
    """Return the singleton SurfaceProfileSystem instance."""
    return SurfaceProfileSystem.get_instance()
