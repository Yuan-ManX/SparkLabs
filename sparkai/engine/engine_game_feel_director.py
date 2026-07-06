"""
SparkLabs Engine - Game Feel Director

A game feel system for the SparkLabs AI-native game engine. It orchestrates
tactile feedback layers - screen shake, hit pause, camera kick, particle
bursts, audio stings, color flashes, and time scaling - that make games
feel responsive and satisfying. The director composes multi-layer feel
responses triggered by gameplay moments such as impacts, celebrations,
danger cues, and discoveries.

Architecture:
  GameFeelDirector (singleton)
    |-- FeelProfile, FeelLayer, FeelMoment, FeelResponse,
       FeelStats, FeelSnapshot, FeelEvent
    |-- FeelLayerType, MomentCategory, FeelIntensity, FeelEventKind

Core Capabilities:
  - register_profile / get_profile / list_profiles / update_profile /
    delete_profile: feel profile lifecycle management.
  - register_layer / get_layer / list_layers / remove_layer: individual
    feedback layer definitions with type, intensity, and duration.
  - trigger_moment / get_moment / list_moments: trigger a feel moment
    that composes all matching layers into a feel response.
  - set_default_profile / get_default_profile: designate a profile as
    the fallback for unprofiled moment categories.
  - compose_response: produce a composite feel response for a given
    moment category and intensity.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`GameFeelDirector.get_instance` or the module-level
:func:`get_game_feel_director` factory.
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

_MAX_PROFILES: int = 500
_MAX_LAYERS: int = 2000
_MAX_MOMENTS: int = 5000
_MAX_RESPONSES: int = 3000
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
    try:
        v = float(value)
    except (TypeError, ValueError):
        v = low
    if v < low:
        return low
    if v > high:
        return high
    return v


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class FeelLayerType(Enum):
    """Types of tactile feedback layers."""
    SCREEN_SHAKE = "screen_shake"
    HIT_PAUSE = "hit_pause"
    CAMERA_KICK = "camera_kick"
    PARTICLE_BURST = "particle_burst"
    AUDIO_STING = "audio_sting"
    COLOR_FLASH = "color_flash"
    TIME_SCALE = "time_scale"
    VIGNETTE = "vignette"
    CHROMATIC_ABERRATION = "chromatic_aberration"
    MOTION_BLUR = "motion_blur"


class MomentCategory(Enum):
    """Categories of gameplay moments that trigger feel responses."""
    IMPACT = "impact"
    HEAVY_IMPACT = "heavy_impact"
    KILL = "kill"
    CRITICAL_HIT = "critical_hit"
    LEVEL_UP = "level_up"
    ACHIEVEMENT = "achievement"
    DANGER = "danger"
    DISCOVERY = "discovery"
    FAILURE = "failure"
    DODGE = "dodge"
    PARRY = "parry"
    COLLECT = "collect"
    BOSS_PHASE = "boss_phase"
    NARRATIVE_BEAT = "narrative_beat"


class FeelIntensity(Enum):
    """Intensity tiers for feel responses."""
    SUBTLE = "subtle"
    LIGHT = "light"
    MEDIUM = "medium"
    STRONG = "strong"
    EXTREME = "extreme"


class FeelEventKind(Enum):
    """Audit event types emitted by the feel director."""
    PROFILE_REGISTERED = "profile_registered"
    PROFILE_UPDATED = "profile_updated"
    PROFILE_DELETED = "profile_deleted"
    LAYER_REGISTERED = "layer_registered"
    LAYER_REMOVED = "layer_removed"
    MOMENT_TRIGGERED = "moment_triggered"
    RESPONSE_COMPOSED = "response_composed"
    DEFAULT_SET = "default_set"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class FeelLayer:
    """A single feedback layer with type, parameters, and intensity curve."""
    layer_id: str = field(default_factory=lambda: _new_id("fl"))
    name: str = ""
    layer_type: str = FeelLayerType.SCREEN_SHAKE.value
    category: str = MomentCategory.IMPACT.value
    intensity: float = 0.5
    duration_ms: int = 200
    amplitude: float = 0.5
    frequency: float = 0.3
    decay: float = 0.7
    color: str = ""
    audio_clip: str = ""
    particle_count: int = 0
    time_scale: float = 1.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelProfile:
    """A composition of feel layers for a specific moment category."""
    profile_id: str = field(default_factory=lambda: _new_id("fp"))
    name: str = ""
    category: str = MomentCategory.IMPACT.value
    layer_ids: List[str] = field(default_factory=list)
    intensity_tier: str = FeelIntensity.MEDIUM.value
    intensity_multiplier: float = 1.0
    cooldown_ms: int = 100
    priority: int = 0
    enabled: bool = True
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelMoment:
    """A triggered gameplay moment that produced a feel response."""
    moment_id: str = field(default_factory=lambda: _new_id("fm"))
    category: str = MomentCategory.IMPACT.value
    intensity: float = 0.5
    position: Dict[str, float] = field(default_factory=dict)
    source_entity: str = ""
    target_entity: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    profile_id: str = ""
    triggered_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelResponse:
    """The composite feel response produced for a moment."""
    response_id: str = field(default_factory=lambda: _new_id("fr"))
    moment_id: str = ""
    profile_id: str = ""
    layers: List[Dict[str, Any]] = field(default_factory=list)
    total_duration_ms: int = 0
    peak_intensity: float = 0.0
    composed_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelStats:
    """Aggregate counters for the feel director."""
    total_profiles: int = 0
    total_layers: int = 0
    total_moments: int = 0
    total_responses: int = 0
    moments_by_category: Dict[str, int] = field(default_factory=dict)
    avg_response_layers: float = 0.0
    last_updated: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelSnapshot:
    """Immutable point-in-time capture of feel director state."""
    profiles: Dict[str, Any] = field(default_factory=dict)
    layers: Dict[str, Any] = field(default_factory=dict)
    moments: List[Dict[str, Any]] = field(default_factory=list)
    responses: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FeelEvent:
    """Audit log entry."""
    event_id: str = field(default_factory=lambda: _new_id("fev"))
    kind: str = FeelEventKind.PROFILE_REGISTERED.value
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Game Feel Director Singleton
# ---------------------------------------------------------------------------


class GameFeelDirector:
    """Singleton system that orchestrates game feel and tactile feedback.

    The director manages feel layers (individual feedback effects), feel
    profiles (compositions of layers for specific moment categories), and
    feel moments (triggered gameplay events). When a moment is triggered,
    the director composes a multi-layer feel response by scaling each
    layer's intensity by the moment's intensity and the profile's
    multiplier.
    """

    _instance: Optional["GameFeelDirector"] = None
    _inner_lock = threading.RLock()

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._initialized: bool = False
        self._profiles: Dict[str, FeelProfile] = {}
        self._layers: Dict[str, FeelLayer] = {}
        self._moments: Dict[str, FeelMoment] = {}
        self._responses: Dict[str, FeelResponse] = {}
        self._events: List[FeelEvent] = []
        self._default_profile_id: str = ""
        self._layers_by_category: Dict[str, List[str]] = {}
        self._profiles_by_category: Dict[str, List[str]] = {}
        self._moment_counter: int = 0
        self._response_counter: int = 0

    # ------------------------------------------------------------------
    # Singleton
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "GameFeelDirector":
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
        """Seed a small set of default layers and a default profile."""
        default_layers = [
            ("shake_impact", FeelLayerType.SCREEN_SHAKE, MomentCategory.IMPACT, 0.4, 150, 0.5, 0.3),
            ("shake_heavy", FeelLayerType.SCREEN_SHAKE, MomentCategory.HEAVY_IMPACT, 0.8, 300, 0.9, 0.4),
            ("pause_impact", FeelLayerType.HIT_PAUSE, MomentCategory.IMPACT, 0.3, 40, 0.0, 0.0),
            ("pause_heavy", FeelLayerType.HIT_PAUSE, MomentCategory.HEAVY_IMPACT, 0.7, 80, 0.0, 0.0),
            ("kick_impact", FeelLayerType.CAMERA_KICK, MomentCategory.IMPACT, 0.5, 200, 0.6, 0.0),
            ("particle_kill", FeelLayerType.PARTICLE_BURST, MomentCategory.KILL, 0.6, 500, 0.0, 0.0),
            ("sting_levelup", FeelLayerType.AUDIO_STING, MomentCategory.LEVEL_UP, 0.8, 600, 0.0, 0.0),
            ("flash_critical", FeelLayerType.COLOR_FLASH, MomentCategory.CRITICAL_HIT, 0.7, 120, 0.0, 0.0),
            ("slowmo_kill", FeelLayerType.TIME_SCALE, MomentCategory.KILL, 0.4, 300, 0.0, 0.0),
            ("vignette_danger", FeelLayerType.VIGNETTE, MomentCategory.DANGER, 0.5, 800, 0.0, 0.0),
        ]
        for name, lt, cat, intensity, dur, amp, freq in default_layers:
            layer = FeelLayer(
                layer_id=_new_id("fl"),
                name=name,
                layer_type=lt.value,
                category=cat.value,
                intensity=intensity,
                duration_ms=dur,
                amplitude=amp,
                frequency=freq,
            )
            self._layers[layer.layer_id] = layer
            self._index_append(self._layers_by_category, cat.value, layer.layer_id)

        # Default profile for impact
        impact_layer_ids = [
            lid for lid, l in self._layers.items()
            if l.category == MomentCategory.IMPACT.value
        ]
        default_profile = FeelProfile(
            profile_id=_new_id("fp"),
            name="Default Impact",
            category=MomentCategory.IMPACT.value,
            layer_ids=impact_layer_ids,
            intensity_tier=FeelIntensity.MEDIUM.value,
            intensity_multiplier=1.0,
        )
        self._profiles[default_profile.profile_id] = default_profile
        self._index_append(self._profiles_by_category, default_profile.category, default_profile.profile_id)
        self._default_profile_id = default_profile.profile_id

    def _index_append(self, index: Dict[str, List[str]], key: str, value: str) -> None:
        if key not in index:
            index[key] = []
        if value not in index[key]:
            index[key].append(value)

    def _emit_event(self, kind: FeelEventKind, payload: Dict[str, Any]) -> None:
        evt = FeelEvent(kind=kind.value, payload=payload)
        self._events.append(evt)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    # ------------------------------------------------------------------
    # Layer Management
    # ------------------------------------------------------------------

    def register_layer(self, name: str = "", layer_type: Any = "",
                       category: Any = "", intensity: float = 0.5,
                       duration_ms: int = 200, amplitude: float = 0.5,
                       frequency: float = 0.3, decay: float = 0.7,
                       color: str = "", audio_clip: str = "",
                       particle_count: int = 0, time_scale: float = 1.0,
                       layer_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> FeelLayer:
        with self._lock:
            lt_val = self._coerce_layer_type(layer_type).value
            cat_val = self._coerce_category(category).value
            lid = layer_id or _new_id("fl")
            layer = FeelLayer(
                layer_id=lid,
                name=name or f"{lt_val}_{cat_val}",
                layer_type=lt_val,
                category=cat_val,
                intensity=_clamp(intensity),
                duration_ms=max(0, _safe_int(duration_ms, 200)),
                amplitude=_clamp(amplitude),
                frequency=_clamp(frequency),
                decay=_clamp(decay),
                color=color,
                audio_clip=audio_clip,
                particle_count=max(0, _safe_int(particle_count, 0)),
                time_scale=_safe_float(time_scale, 1.0),
                metadata=metadata or {},
            )
            self._layers[lid] = layer
            self._index_append(self._layers_by_category, cat_val, lid)
            _evict_fifo_dict(self._layers, _MAX_LAYERS)
            self._emit_event(FeelEventKind.LAYER_REGISTERED, {"layer_id": lid})
            return layer

    def get_layer(self, layer_id: str) -> Optional[FeelLayer]:
        with self._lock:
            return self._layers.get(layer_id)

    def list_layers(self, category: Any = None, layer_type: Any = None,
                    limit: int = 100) -> List[FeelLayer]:
        with self._lock:
            items = list(self._layers.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [l for l in items if l.category == cat_val]
            if layer_type is not None and layer_type != "":
                lt_val = self._coerce_layer_type(layer_type).value
                items = [l for l in items if l.layer_type == lt_val]
            return items[-limit:]

    def remove_layer(self, layer_id: str) -> bool:
        with self._lock:
            layer = self._layers.pop(layer_id, None)
            if layer is None:
                return False
            cat_list = self._layers_by_category.get(layer.category, [])
            if layer_id in cat_list:
                cat_list.remove(layer_id)
            # Remove from any profiles that reference it
            for profile in self._profiles.values():
                if layer_id in profile.layer_ids:
                    profile.layer_ids = [lid for lid in profile.layer_ids if lid != layer_id]
            self._emit_event(FeelEventKind.LAYER_REMOVED, {"layer_id": layer_id})
            return True

    # ------------------------------------------------------------------
    # Profile Management
    # ------------------------------------------------------------------

    def register_profile(self, name: str = "", category: Any = "",
                         layer_ids: Optional[List[str]] = None,
                         intensity_tier: Any = "medium",
                         intensity_multiplier: float = 1.0,
                         cooldown_ms: int = 100, priority: int = 0,
                         profile_id: str = "", tags: Optional[List[str]] = None,
                         metadata: Optional[Dict[str, Any]] = None) -> FeelProfile:
        with self._lock:
            cat_val = self._coerce_category(category).value
            pid = profile_id or _new_id("fp")
            profile = FeelProfile(
                profile_id=pid,
                name=name or f"{cat_val}_profile",
                category=cat_val,
                layer_ids=list(layer_ids) if layer_ids else [],
                intensity_tier=self._coerce_intensity(intensity_tier).value,
                intensity_multiplier=_safe_float(intensity_multiplier, 1.0),
                cooldown_ms=max(0, _safe_int(cooldown_ms, 100)),
                priority=_safe_int(priority, 0),
                tags=list(tags) if tags else [],
                metadata=metadata or {},
            )
            self._profiles[pid] = profile
            self._index_append(self._profiles_by_category, cat_val, pid)
            _evict_fifo_dict(self._profiles, _MAX_PROFILES)
            self._emit_event(FeelEventKind.PROFILE_REGISTERED, {"profile_id": pid})
            return profile

    def get_profile(self, profile_id: str) -> Optional[FeelProfile]:
        with self._lock:
            return self._profiles.get(profile_id)

    def list_profiles(self, category: Any = None, limit: int = 100) -> List[FeelProfile]:
        with self._lock:
            items = list(self._profiles.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [p for p in items if p.category == cat_val]
            items.sort(key=lambda p: (-p.priority, p.name))
            return items[-limit:]

    def update_profile(self, profile_id: str, **kwargs: Any) -> Optional[FeelProfile]:
        with self._lock:
            profile = self._profiles.get(profile_id)
            if profile is None:
                return None
            for key, value in kwargs.items():
                if key == "name" and isinstance(value, str):
                    profile.name = value
                elif key == "layer_ids" and isinstance(value, list):
                    profile.layer_ids = list(value)
                elif key == "intensity_tier":
                    profile.intensity_tier = self._coerce_intensity(value).value
                elif key == "intensity_multiplier":
                    profile.intensity_multiplier = _safe_float(value, 1.0)
                elif key == "cooldown_ms":
                    profile.cooldown_ms = max(0, _safe_int(value, 100))
                elif key == "priority":
                    profile.priority = _safe_int(value, 0)
                elif key == "enabled" and isinstance(value, bool):
                    profile.enabled = value
                elif key == "tags" and isinstance(value, list):
                    profile.tags = list(value)
                elif key == "metadata" and isinstance(value, dict):
                    profile.metadata = dict(value)
            profile.updated_at = _now()
            self._emit_event(FeelEventKind.PROFILE_UPDATED, {"profile_id": profile_id})
            return profile

    def delete_profile(self, profile_id: str) -> bool:
        with self._lock:
            profile = self._profiles.pop(profile_id, None)
            if profile is None:
                return False
            cat_list = self._profiles_by_category.get(profile.category, [])
            if profile_id in cat_list:
                cat_list.remove(profile_id)
            if self._default_profile_id == profile_id:
                self._default_profile_id = ""
            self._emit_event(FeelEventKind.PROFILE_DELETED, {"profile_id": profile_id})
            return True

    def set_default_profile(self, profile_id: str) -> bool:
        with self._lock:
            if profile_id not in self._profiles:
                return False
            self._default_profile_id = profile_id
            self._emit_event(FeelEventKind.DEFAULT_SET, {"profile_id": profile_id})
            return True

    def get_default_profile(self) -> Optional[FeelProfile]:
        with self._lock:
            if not self._default_profile_id:
                return None
            return self._profiles.get(self._default_profile_id)

    # ------------------------------------------------------------------
    # Moment Triggering and Response Composition
    # ------------------------------------------------------------------

    def trigger_moment(self, category: Any = "", intensity: float = 0.5,
                       position: Optional[Dict[str, float]] = None,
                       source_entity: str = "", target_entity: str = "",
                       context: Optional[Dict[str, Any]] = None,
                       profile_id: str = "", moment_id: str = "") -> FeelMoment:
        with self._lock:
            cat_val = self._coerce_category(category).value
            mid = moment_id or _new_id("fm")
            moment = FeelMoment(
                moment_id=mid,
                category=cat_val,
                intensity=_clamp(intensity),
                position=dict(position) if position else {},
                source_entity=source_entity,
                target_entity=target_entity,
                context=dict(context) if context else {},
                profile_id=profile_id,
            )
            self._moments[mid] = moment
            self._moment_counter += 1
            _evict_fifo_dict(self._moments, _MAX_MOMENTS)

            # Compose the feel response
            response = self._compose_response(moment)
            self._responses[response.response_id] = response
            self._response_counter += 1
            _evict_fifo_dict(self._responses, _MAX_RESPONSES)

            self._emit_event(FeelEventKind.MOMENT_TRIGGERED, {
                "moment_id": mid,
                "category": cat_val,
                "response_id": response.response_id,
            })
            return moment

    def _compose_response(self, moment: FeelMoment) -> FeelResponse:
        """Compose a multi-layer feel response for a moment."""
        # Find the best profile: explicit > category match > default
        profile = None
        if moment.profile_id:
            profile = self._profiles.get(moment.profile_id)
        if profile is None:
            # Find highest-priority enabled profile for this category
            cat_profiles = self._profiles_by_category.get(moment.category, [])
            candidates = [self._profiles[pid] for pid in cat_profiles
                          if pid in self._profiles and self._profiles[pid].enabled]
            if candidates:
                candidates.sort(key=lambda p: -p.priority)
                profile = candidates[0]
        if profile is None:
            profile = self._profiles.get(self._default_profile_id)

        layer_ids = profile.layer_ids if profile else []
        composed_layers: List[Dict[str, Any]] = []
        peak = 0.0
        total_dur = 0

        for lid in layer_ids:
            layer = self._layers.get(lid)
            if layer is None or not layer.enabled:
                continue
            mult = profile.intensity_multiplier if profile else 1.0
            scaled_intensity = _clamp(layer.intensity * mult * moment.intensity)
            composed = {
                "layer_id": layer.layer_id,
                "name": layer.name,
                "layer_type": layer.layer_type,
                "intensity": round(scaled_intensity, 4),
                "duration_ms": layer.duration_ms,
                "amplitude": round(_clamp(layer.amplitude * mult), 4),
                "frequency": layer.frequency,
                "decay": layer.decay,
                "color": layer.color,
                "audio_clip": layer.audio_clip,
                "particle_count": int(layer.particle_count * mult),
                "time_scale": layer.time_scale,
            }
            composed_layers.append(composed)
            if scaled_intensity > peak:
                peak = scaled_intensity
            if layer.duration_ms > total_dur:
                total_dur = layer.duration_ms

        response = FeelResponse(
            moment_id=moment.moment_id,
            profile_id=profile.profile_id if profile else "",
            layers=composed_layers,
            total_duration_ms=total_dur,
            peak_intensity=round(peak, 4),
        )
        self._emit_event(FeelEventKind.RESPONSE_COMPOSED, {
            "response_id": response.response_id,
            "layer_count": len(composed_layers),
        })
        return response

    def compose_response(self, category: Any = "", intensity: float = 0.5,
                         profile_id: str = "") -> FeelResponse:
        """Compose a feel response without persisting a moment."""
        with self._lock:
            cat_val = self._coerce_category(category).value
            moment = FeelMoment(
                moment_id=_new_id("fm"),
                category=cat_val,
                intensity=_clamp(intensity),
                profile_id=profile_id,
            )
            return self._compose_response(moment)

    def get_moment(self, moment_id: str) -> Optional[FeelMoment]:
        with self._lock:
            return self._moments.get(moment_id)

    def list_moments(self, category: Any = None, limit: int = 100) -> List[FeelMoment]:
        with self._lock:
            items = list(self._moments.values())
            if category is not None and category != "":
                cat_val = self._coerce_category(category).value
                items = [m for m in items if m.category == cat_val]
            return items[-limit:]

    def get_response(self, response_id: str) -> Optional[FeelResponse]:
        with self._lock:
            return self._responses.get(response_id)

    def list_responses(self, moment_id: str = "", limit: int = 100) -> List[FeelResponse]:
        with self._lock:
            items = list(self._responses.values())
            if moment_id:
                items = [r for r in items if r.moment_id == moment_id]
            return items[-limit:]

    # ------------------------------------------------------------------
    # Enum Coercion Helpers
    # ------------------------------------------------------------------

    def _coerce_layer_type(self, value: Any) -> FeelLayerType:
        if isinstance(value, FeelLayerType):
            return value
        if isinstance(value, str) and value:
            try:
                return FeelLayerType(value)
            except ValueError:
                pass
        return FeelLayerType.SCREEN_SHAKE

    def _coerce_category(self, value: Any) -> MomentCategory:
        if isinstance(value, MomentCategory):
            return value
        if isinstance(value, str) and value:
            try:
                return MomentCategory(value)
            except ValueError:
                pass
        return MomentCategory.IMPACT

    def _coerce_intensity(self, value: Any) -> FeelIntensity:
        if isinstance(value, FeelIntensity):
            return value
        if isinstance(value, str) and value:
            try:
                return FeelIntensity(value)
            except ValueError:
                pass
        return FeelIntensity.MEDIUM

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 100) -> List[FeelEvent]:
        with self._lock:
            return list(self._events[-limit:])

    def get_stats(self) -> FeelStats:
        with self._lock:
            cat_counts: Dict[str, int] = {}
            for m in self._moments.values():
                cat_counts[m.category] = cat_counts.get(m.category, 0) + 1
            avg_layers = 0.0
            if self._responses:
                total = sum(len(r.layers) for r in self._responses.values())
                avg_layers = round(total / len(self._responses), 4)
            return FeelStats(
                total_profiles=len(self._profiles),
                total_layers=len(self._layers),
                total_moments=len(self._moments),
                total_responses=len(self._responses),
                moments_by_category=cat_counts,
                avg_response_layers=avg_layers,
            )

    def get_status(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "initialized": self._initialized,
                "profiles": len(self._profiles),
                "layers": len(self._layers),
                "moments": len(self._moments),
                "responses": len(self._responses),
                "events": len(self._events),
                "default_profile_id": self._default_profile_id,
            }

    def get_snapshot(self) -> FeelSnapshot:
        with self._lock:
            return FeelSnapshot(
                profiles={pid: p.to_dict() for pid, p in list(self._profiles.items())[:50]},
                layers={lid: l.to_dict() for lid, l in list(self._layers.items())[:50]},
                moments=[m.to_dict() for m in list(self._moments.values())[-50:]],
                responses=[r.to_dict() for r in list(self._responses.values())[-50:]],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        with self._lock:
            self._profiles.clear()
            self._layers.clear()
            self._moments.clear()
            self._responses.clear()
            self._events.clear()
            self._layers_by_category.clear()
            self._profiles_by_category.clear()
            self._default_profile_id = ""
            self._moment_counter = 0
            self._response_counter = 0
            self._seed_defaults()


def get_game_feel_director() -> GameFeelDirector:
    """Factory function to obtain the singleton GameFeelDirector."""
    return GameFeelDirector.get_instance()
