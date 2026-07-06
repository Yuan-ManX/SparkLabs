"""
SparkLabs Engine - Haptics & Force Feedback System

Manages gamepad rumble, vibration patterns, and force feedback envelopes
for the SparkLabs game engine. Patterns are composed of one or more
haptic layers, each targeting a specific motor (low-frequency rumble,
high-frequency vibration, or adaptive triggers) with a temporal shape
and optional amplitude envelope. Devices advertise their capabilities
so the system can skip unsupported layers automatically. Named events
bind a pattern to a priority, target device, intensity scale, and
cooldown, letting gameplay code trigger feedback by intent rather than
by raw motor parameters.

Architecture:
  HapticsSystem (singleton)
    |-- HapticPattern, HapticLayer, HapticEvent, DeviceProfile,
    |   HapticEnvelope, ActiveRumble, HapticsStats, HapticsSnapshot,
    |   HapticsLogEvent
    |-- RumbleMotor, HapticIntensity, HapticShape, DeviceType,
        HapticPriority, HapticEventKind

Core Capabilities:
  - register_pattern / update_pattern / get_pattern / list_patterns /
    delete_pattern: haptic pattern catalog with layered motors,
    shapes, and envelopes.
  - play_pattern / stop_pattern / stop_all: start and stop rumble
    instances with per-device capability checks and priority-based
    preemption.
  - register_device / get_device / list_devices / set_device_enabled:
    device profile management with motor and HD-haptic capabilities.
  - create_event / trigger_event: named gameplay events that resolve
    to a pattern with priority, intensity scale, and cooldown.
  - list_active / list_events_log / get_stats / get_status /
    get_snapshot / reset: observability and lifecycle management.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_PATTERNS: int = 1000
_MAX_DEVICES: int = 64
_MAX_EVENTS: int = 1000
_MAX_ACTIVE_RUMBLES: int = 32
_MAX_EVENT_COOLDOWNS: int = 500
_MAX_LOG_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return the current UTC time as an ISO-8601 string with a 'Z' suffix."""
    return datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier, optionally prefixed."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest entries from a dict to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        oldest_key = next(iter(store), None)
        if oldest_key is None:
            break
        store.pop(oldest_key, None)


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Evict the oldest entries from a list to keep ``len(store) <= max_size``."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _to_jsonable(value: Any) -> Any:
    """Convert ``value`` into something safe to drop into a JSON payload."""
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
    """Convert a dataclass instance to a plain dictionary."""
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


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class RumbleMotor(Enum):
    """Target motor / actuator for a haptic layer."""
    LEFT_LOW_FREQ = "left_low_freq"
    RIGHT_HIGH_FREQ = "right_high_freq"
    BOTH = "both"
    TRIGGER_LEFT = "trigger_left"
    TRIGGER_RIGHT = "trigger_right"


class HapticIntensity(Enum):
    """Named intensity presets mapping to amplitude multipliers."""
    SUBTLE = "subtle"
    LIGHT = "light"
    MEDIUM = "medium"
    STRONG = "strong"
    INTENSE = "intense"


class HapticShape(Enum):
    """Temporal shape of a haptic layer's amplitude curve."""
    CONSTANT = "constant"
    RAMP_UP = "ramp_up"
    RAMP_DOWN = "ramp_down"
    PULSE = "pulse"
    HEARTBEAT = "heartbeat"
    IMPACT = "impact"
    DECAY = "decay"


class DeviceType(Enum):
    """Known haptic device families."""
    DUALSENSE = "dualsense"
    XBOX_ONE = "xbox_one"
    SWITCH_PRO = "switch_pro"
    MOBILE = "mobile"
    GENERIC = "generic"


class HapticPriority(Enum):
    """Priority tier for a haptic event; higher tiers preempt lower ones."""
    BACKGROUND = "background"
    AMBIENT = "ambient"
    GAMEPLAY = "gameplay"
    FEEDBACK = "feedback"
    CINEMATIC = "cinematic"


class HapticEventKind(Enum):
    """Audit event kinds emitted by the haptics system."""
    PATTERN_REGISTERED = "pattern_registered"
    PATTERN_UPDATED = "pattern_updated"
    PATTERN_DELETED = "pattern_deleted"
    PATTERN_PLAYED = "pattern_played"
    PATTERN_STOPPED = "pattern_stopped"
    ALL_STOPPED = "all_stopped"
    DEVICE_REGISTERED = "device_registered"
    DEVICE_ENABLED = "device_enabled"
    DEVICE_DISABLED = "device_disabled"
    EVENT_CREATED = "event_created"
    EVENT_TRIGGERED = "event_triggered"
    EVENT_BLOCKED_COOLDOWN = "event_blocked_cooldown"
    EVENT_BLOCKED_PRIORITY = "event_blocked_priority"
    SYSTEM_RESET = "system_reset"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

# Intensity preset -> default amplitude multiplier.
_INTENSITY_AMPLITUDE: Dict[HapticIntensity, float] = {
    HapticIntensity.SUBTLE: 0.15,
    HapticIntensity.LIGHT: 0.35,
    HapticIntensity.MEDIUM: 0.55,
    HapticIntensity.STRONG: 0.8,
    HapticIntensity.INTENSE: 1.0,
}

# Priority ordering value; higher numbers win during preemption.
_PRIORITY_RANK: Dict[HapticPriority, int] = {
    HapticPriority.BACKGROUND: 0,
    HapticPriority.AMBIENT: 1,
    HapticPriority.GAMEPLAY: 2,
    HapticPriority.FEEDBACK: 3,
    HapticPriority.CINEMATIC: 4,
}


@dataclass
class HapticEnvelope:
    """Amplitude envelope defined as a list of (time, amplitude) points."""
    points: List[Tuple[float, float]] = field(default_factory=list)
    loop: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HapticLayer:
    """A single layer of haptic feedback within a pattern."""
    layer_id: str
    motor: RumbleMotor = RumbleMotor.BOTH
    intensity: HapticIntensity = HapticIntensity.MEDIUM
    shape: HapticShape = HapticShape.CONSTANT
    amplitude: float = 0.5  # 0.0 .. 1.0, multiplied by intensity preset
    frequency_hz: float = 0.0  # 0.0 means device default
    duration_seconds: float = 0.5
    pulse_count: int = 0  # number of pulses for pulse / heartbeat shapes
    pulse_interval_seconds: float = 0.1
    envelope: Optional[HapticEnvelope] = None
    enabled: bool = True
    created_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def effective_amplitude(self) -> float:
        """Compute the layer's effective amplitude after intensity scaling."""
        base = max(0.0, min(1.0, float(self.amplitude)))
        preset = _INTENSITY_AMPLITUDE.get(self.intensity, 0.5)
        return max(0.0, min(1.0, base * preset))


@dataclass
class HapticPattern:
    """A named haptic pattern composed of one or more layers."""
    pattern_id: str
    name: str
    description: str = ""
    layers: List[HapticLayer] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    looping: bool = False
    priority: HapticPriority = HapticPriority.GAMEPLAY
    tags: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def compute_duration(self) -> float:
        """Return the longest layer duration, falling back to the stored total."""
        if not self.layers:
            return float(self.total_duration_seconds)
        longest = max(
            (l.duration_seconds for l in self.layers if l.enabled),
            default=0.0,
        )
        return max(longest, float(self.total_duration_seconds))


@dataclass
class DeviceProfile:
    """A haptic device and its capabilities."""
    device_id: str
    name: str
    device_type: DeviceType = DeviceType.GENERIC
    supports_low_freq: bool = True
    supports_high_freq: bool = True
    supports_trigger_l: bool = False
    supports_trigger_r: bool = False
    supports_hd_haptics: bool = False
    max_frequency_hz: float = 250.0
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)

    def supports_motor(self, motor: RumbleMotor) -> bool:
        """Return whether this device can drive the given motor."""
        if motor == RumbleMotor.LEFT_LOW_FREQ:
            return self.supports_low_freq
        if motor == RumbleMotor.RIGHT_HIGH_FREQ:
            return self.supports_high_freq
        if motor == RumbleMotor.BOTH:
            return self.supports_low_freq or self.supports_high_freq
        if motor == RumbleMotor.TRIGGER_LEFT:
            return self.supports_trigger_l
        if motor == RumbleMotor.TRIGGER_RIGHT:
            return self.supports_trigger_r
        return False


@dataclass
class HapticEvent:
    """A named event that maps to a pattern with priority and target device."""
    event_id: str
    name: str
    pattern_id: str
    device_id: str = ""  # empty means default device
    priority: HapticPriority = HapticPriority.FEEDBACK
    intensity_scale: float = 1.0  # multiplier applied to pattern amplitudes
    cooldown_seconds: float = 0.0
    description: str = ""
    created_at: str = field(default_factory=_now)
    updated_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ActiveRumble:
    """A currently playing haptic rumble instance."""
    instance_id: str
    pattern_id: str
    event_id: str = ""
    device_id: str = ""
    priority: HapticPriority = HapticPriority.GAMEPLAY
    started_at: str = field(default_factory=_now)
    duration_seconds: float = 0.0
    looping: bool = False
    intensity_scale: float = 1.0
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HapticsStats:
    """Aggregate statistics for the haptics system."""
    total_patterns: int = 0
    total_devices: int = 0
    total_events: int = 0
    active_rumbles: int = 0
    total_plays: int = 0
    total_stops: int = 0
    total_triggers: int = 0
    blocked_by_cooldown: int = 0
    blocked_by_priority: int = 0
    pattern_counter: int = 0
    device_counter: int = 0
    event_counter: int = 0
    log_counter: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HapticsSnapshot:
    """A point-in-time snapshot of the entire haptics system state."""
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    devices: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    active: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    taken_at: str = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HapticsLogEvent:
    """An audit log event emitted by the haptics system."""
    log_id: str
    kind: HapticEventKind
    timestamp: str
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Haptics System Singleton
# ---------------------------------------------------------------------------


class HapticsSystem:
    """Engine-level haptics and force feedback manager.

    Tracks haptic patterns, device profiles, named events, and active
    rumble instances. Enforces device capability checks, per-event
    cooldowns, and priority-based preemption when the active rumble
    capacity is reached.
    """

    _instance: Optional["HapticsSystem"] = None
    _inner_lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "HapticsSystem":
        if cls._instance is None:
            with cls._inner_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._inner_lock:
            if self._initialized:
                return
            self._lock = threading.RLock()
            self._patterns: Dict[str, HapticPattern] = {}
            self._devices: Dict[str, DeviceProfile] = {}
            self._events: Dict[str, HapticEvent] = {}
            self._active: Dict[str, ActiveRumble] = {}
            self._cooldowns: Dict[str, str] = {}  # event_id -> expires_at ISO
            self._log: List[HapticsLogEvent] = []
            self._stats = HapticsStats()
            self._default_device_id: str = ""
            self._seed_data()
            self._initialized = True

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(self, kind: HapticEventKind, data: Dict[str, Any]) -> None:
        log_event = HapticsLogEvent(
            log_id=_new_id("log"),
            kind=kind,
            timestamp=_now(),
            data=data,
        )
        self._log.append(log_event)
        self._stats.log_counter += 1
        _evict_fifo_list(self._log, _MAX_LOG_EVENTS)

    def _resolve_device(self, device_id: str) -> Optional[DeviceProfile]:
        """Resolve a device id, falling back to the default device."""
        if device_id:
            return self._devices.get(device_id)
        if self._default_device_id:
            return self._devices.get(self._default_device_id)
        # Fall back to the first enabled device.
        for device in self._devices.values():
            if device.enabled:
                return device
        return None

    def _preempt_for_priority(self, new_priority: HapticPriority) -> bool:
        """If active capacity is full, evict the lowest-priority rumble
        when ``new_priority`` outranks it. Returns True if a slot is available.
        """
        if len(self._active) < _MAX_ACTIVE_RUMBLES:
            return True
        if not self._active:
            return True
        # Find the lowest priority active rumble.
        lowest_id = None
        lowest_rank = None
        for iid, rumble in self._active.items():
            rank = _PRIORITY_RANK.get(rumble.priority, 0)
            if lowest_rank is None or rank < lowest_rank:
                lowest_rank = rank
                lowest_id = iid
        new_rank = _PRIORITY_RANK.get(new_priority, 0)
        if lowest_id is not None and new_rank > (lowest_rank or 0):
            self._stop_instance(lowest_id, emit=False)
            return True
        return False

    def _stop_instance(self, instance_id: str, emit: bool = True) -> bool:
        """Internal stop that does not acquire the lock."""
        rumble = self._active.get(instance_id)
        if rumble is None:
            return False
        rumble.active = False
        del self._active[instance_id]
        self._stats.total_stops += 1
        if emit:
            self._emit(HapticEventKind.PATTERN_STOPPED, {
                "instance_id": instance_id,
                "pattern_id": rumble.pattern_id,
            })
        return True

    def _seed_data(self) -> None:
        """Seed demo device profiles, haptic patterns, and events."""
        # Devices
        dualsense = DeviceProfile(
            device_id="dev_dualsense",
            name="DualSense Controller",
            device_type=DeviceType.DUALSENSE,
            supports_low_freq=True,
            supports_high_freq=True,
            supports_trigger_l=True,
            supports_trigger_r=True,
            supports_hd_haptics=True,
            max_frequency_hz=250.0,
            metadata={"vendor": "sony", "voice_coils": 2},
        )
        xbox = DeviceProfile(
            device_id="dev_xbox_one",
            name="Xbox One Controller",
            device_type=DeviceType.XBOX_ONE,
            supports_low_freq=True,
            supports_high_freq=True,
            supports_trigger_l=False,
            supports_trigger_r=False,
            supports_hd_haptics=False,
            max_frequency_hz=200.0,
            metadata={"vendor": "microsoft", "trigger_rumble": False},
        )
        self._devices[dualsense.device_id] = dualsense
        self._devices[xbox.device_id] = xbox
        self._stats.device_counter = 2
        self._stats.total_devices = 2
        self._default_device_id = dualsense.device_id

        # Pattern: explosion_impact
        explosion_layers = [
            HapticLayer(
                layer_id="exp_low",
                motor=RumbleMotor.LEFT_LOW_FREQ,
                intensity=HapticIntensity.INTENSE,
                shape=HapticShape.IMPACT,
                amplitude=1.0,
                duration_seconds=0.45,
                envelope=HapticEnvelope(
                    points=[(0.0, 1.0), (0.05, 0.85), (0.2, 0.4), (0.45, 0.0)],
                ),
            ),
            HapticLayer(
                layer_id="exp_high",
                motor=RumbleMotor.RIGHT_HIGH_FREQ,
                intensity=HapticIntensity.STRONG,
                shape=HapticShape.DECAY,
                amplitude=0.8,
                frequency_hz=180.0,
                duration_seconds=0.3,
            ),
            HapticLayer(
                layer_id="exp_trigger_l",
                motor=RumbleMotor.TRIGGER_LEFT,
                intensity=HapticIntensity.STRONG,
                shape=HapticShape.RAMP_DOWN,
                amplitude=0.7,
                duration_seconds=0.25,
            ),
        ]
        explosion = HapticPattern(
            pattern_id="pat_explosion_impact",
            name="Explosion Impact",
            description="Heavy low-frequency impact with high-frequency debris and trigger kickback.",
            layers=explosion_layers,
            total_duration_seconds=0.45,
            looping=False,
            priority=HapticPriority.FEEDBACK,
            tags=["combat", "explosion", "impact"],
        )
        self._patterns[explosion.pattern_id] = explosion

        # Pattern: heartbeat_low_health
        heartbeat_layers = [
            HapticLayer(
                layer_id="hb_low",
                motor=RumbleMotor.LEFT_LOW_FREQ,
                intensity=HapticIntensity.MEDIUM,
                shape=HapticShape.HEARTBEAT,
                amplitude=0.6,
                duration_seconds=1.2,
                pulse_count=2,
                pulse_interval_seconds=0.18,
            ),
            HapticLayer(
                layer_id="hb_high",
                motor=RumbleMotor.RIGHT_HIGH_FREQ,
                intensity=HapticIntensity.SUBTLE,
                shape=HapticShape.PULSE,
                amplitude=0.25,
                frequency_hz=80.0,
                duration_seconds=1.2,
                pulse_count=2,
                pulse_interval_seconds=0.18,
            ),
        ]
        heartbeat = HapticPattern(
            pattern_id="pat_heartbeat_low_health",
            name="Heartbeat - Low Health",
            description="Looping dual-beat heartbeat that signals critical player health.",
            layers=heartbeat_layers,
            total_duration_seconds=1.2,
            looping=True,
            priority=HapticPriority.AMBIENT,
            tags=["ui", "health", "loop"],
        )
        self._patterns[heartbeat.pattern_id] = heartbeat
        self._stats.pattern_counter = 2
        self._stats.total_patterns = 2

        # Events
        event_explosion = HapticEvent(
            event_id="evt_explosion",
            name="explosion",
            pattern_id=explosion.pattern_id,
            device_id="",
            priority=HapticPriority.FEEDBACK,
            intensity_scale=1.0,
            cooldown_seconds=0.15,
            description="Triggered when an explosion affects the player.",
        )
        event_heartbeat = HapticEvent(
            event_id="evt_low_health",
            name="low_health",
            pattern_id=heartbeat.pattern_id,
            device_id="",
            priority=HapticPriority.AMBIENT,
            intensity_scale=0.9,
            cooldown_seconds=0.0,
            description="Triggered when player health drops below the critical threshold.",
        )
        self._events[event_explosion.event_id] = event_explosion
        self._events[event_heartbeat.event_id] = event_heartbeat
        self._stats.event_counter = 2
        self._stats.total_events = 2

        # Seed audit log
        self._emit(HapticEventKind.DEVICE_REGISTERED, {
            "device_id": dualsense.device_id,
            "name": dualsense.name,
        })
        self._emit(HapticEventKind.DEVICE_REGISTERED, {
            "device_id": xbox.device_id,
            "name": xbox.name,
        })
        self._emit(HapticEventKind.PATTERN_REGISTERED, {
            "pattern_id": explosion.pattern_id,
            "name": explosion.name,
        })
        self._emit(HapticEventKind.PATTERN_REGISTERED, {
            "pattern_id": heartbeat.pattern_id,
            "name": heartbeat.name,
        })
        self._emit(HapticEventKind.EVENT_CREATED, {
            "event_id": event_explosion.event_id,
            "name": event_explosion.name,
        })

    # ------------------------------------------------------------------
    # Pattern management
    # ------------------------------------------------------------------

    def register_pattern(
        self,
        name: str,
        layers: Optional[List[HapticLayer]] = None,
        description: str = "",
        total_duration_seconds: float = 0.0,
        looping: bool = False,
        priority: HapticPriority = HapticPriority.GAMEPLAY,
        tags: Optional[List[str]] = None,
        pattern_id: Optional[str] = None,
    ) -> HapticPattern:
        """Register a new haptic pattern."""
        with self._lock:
            pid = pattern_id or _new_id("pat")
            if pid in self._patterns:
                raise ValueError(f"Haptic pattern already exists: {pid}")
            pattern = HapticPattern(
                pattern_id=pid,
                name=name,
                description=description,
                layers=layers or [],
                total_duration_seconds=total_duration_seconds,
                looping=looping,
                priority=priority,
                tags=tags or [],
            )
            if pattern.total_duration_seconds <= 0.0:
                pattern.total_duration_seconds = pattern.compute_duration()
            self._patterns[pid] = pattern
            self._stats.pattern_counter += 1
            self._stats.total_patterns = len(self._patterns)
            _evict_fifo_dict(self._patterns, _MAX_PATTERNS)
            self._emit(HapticEventKind.PATTERN_REGISTERED, {
                "pattern_id": pid,
                "name": name,
            })
            return pattern

    def update_pattern(self, pattern_id: str, updates: Dict[str, Any]) -> HapticPattern:
        """Update an existing haptic pattern."""
        with self._lock:
            if pattern_id not in self._patterns:
                raise KeyError(f"Haptic pattern not found: {pattern_id}")
            pattern = self._patterns[pattern_id]
            for key, value in updates.items():
                if key in ("pattern_id", "created_at"):
                    continue
                if key == "priority" and isinstance(value, str):
                    value = HapticPriority(value)
                elif key == "layers" and isinstance(value, list):
                    rebuilt: List[HapticLayer] = []
                    for item in value:
                        if isinstance(item, HapticLayer):
                            rebuilt.append(item)
                        elif isinstance(item, dict):
                            rebuilt.append(self._layer_from_dict(item))
                        else:
                            continue
                    value = rebuilt
                elif key == "tags" and isinstance(value, list):
                    value = [str(t) for t in value]
                if hasattr(pattern, key):
                    setattr(pattern, key, value)
            pattern.updated_at = _now()
            if pattern.total_duration_seconds <= 0.0:
                pattern.total_duration_seconds = pattern.compute_duration()
            self._emit(HapticEventKind.PATTERN_UPDATED, {"pattern_id": pattern_id})
            return pattern

    def _layer_from_dict(self, data: Dict[str, Any]) -> HapticLayer:
        """Build a HapticLayer from a dict, used during pattern updates."""
        envelope = data.get("envelope")
        env_obj: Optional[HapticEnvelope] = None
        if isinstance(envelope, dict):
            pts = [
                (float(p[0]), float(p[1]))
                for p in envelope.get("points", [])
                if isinstance(p, (list, tuple)) and len(p) >= 2
            ]
            env_obj = HapticEnvelope(points=pts, loop=bool(envelope.get("loop", False)))
        elif isinstance(envelope, HapticEnvelope):
            env_obj = envelope
        motor_raw = data.get("motor", "both")
        intensity_raw = data.get("intensity", "medium")
        shape_raw = data.get("shape", "constant")
        return HapticLayer(
            layer_id=str(data.get("layer_id") or _new_id("lyr")),
            motor=RumbleMotor(motor_raw) if isinstance(motor_raw, str) else motor_raw,
            intensity=HapticIntensity(intensity_raw) if isinstance(intensity_raw, str) else intensity_raw,
            shape=HapticShape(shape_raw) if isinstance(shape_raw, str) else shape_raw,
            amplitude=float(data.get("amplitude", 0.5)),
            frequency_hz=float(data.get("frequency_hz", 0.0)),
            duration_seconds=float(data.get("duration_seconds", 0.5)),
            pulse_count=int(data.get("pulse_count", 0)),
            pulse_interval_seconds=float(data.get("pulse_interval_seconds", 0.1)),
            envelope=env_obj,
            enabled=bool(data.get("enabled", True)),
        )

    def get_pattern(self, pattern_id: str) -> Optional[HapticPattern]:
        """Get a haptic pattern by id."""
        with self._lock:
            return self._patterns.get(pattern_id)

    def list_patterns(
        self,
        priority: Optional[HapticPriority] = None,
        tag: Optional[str] = None,
        looping: Optional[bool] = None,
    ) -> List[HapticPattern]:
        """List haptic patterns with optional filters."""
        with self._lock:
            result: List[HapticPattern] = []
            for pattern in self._patterns.values():
                if priority is not None and pattern.priority != priority:
                    continue
                if tag is not None and tag not in pattern.tags:
                    continue
                if looping is not None and pattern.looping != looping:
                    continue
                result.append(pattern)
            return result

    def delete_pattern(self, pattern_id: str) -> bool:
        """Delete a haptic pattern. Active rumbles using it are stopped."""
        with self._lock:
            if pattern_id not in self._patterns:
                return False
            del self._patterns[pattern_id]
            self._stats.total_patterns = len(self._patterns)
            # Stop active rumbles that referenced this pattern.
            to_stop = [
                iid for iid, r in self._active.items() if r.pattern_id == pattern_id
            ]
            for iid in to_stop:
                self._stop_instance(iid, emit=False)
            # Remove events that referenced this pattern.
            to_remove = [
                eid for eid, evt in self._events.items() if evt.pattern_id == pattern_id
            ]
            for eid in to_remove:
                del self._events[eid]
            self._stats.total_events = len(self._events)
            self._emit(HapticEventKind.PATTERN_DELETED, {"pattern_id": pattern_id})
            return True

    # ------------------------------------------------------------------
    # Playback management
    # ------------------------------------------------------------------

    def play_pattern(
        self,
        pattern_id: str,
        device_id: str = "",
        intensity_scale: float = 1.0,
        duration_override: Optional[float] = None,
        priority: Optional[HapticPriority] = None,
        event_id: str = "",
    ) -> ActiveRumble:
        """Start playing a haptic pattern on a device."""
        with self._lock:
            if pattern_id not in self._patterns:
                raise KeyError(f"Haptic pattern not found: {pattern_id}")
            pattern = self._patterns[pattern_id]
            device = self._resolve_device(device_id)
            if device is None:
                raise ValueError("No haptic device available")
            if not device.enabled:
                raise ValueError(f"Device is disabled: {device.device_id}")
            # Validate that the device can drive at least one layer.
            supported_layers = [
                l for l in pattern.layers if l.enabled and device.supports_motor(l.motor)
            ]
            if not supported_layers and pattern.layers:
                raise ValueError(
                    f"Device {device.device_id} cannot drive any layer of pattern {pattern_id}"
                )
            effective_priority = priority or pattern.priority
            if not self._preempt_for_priority(effective_priority):
                self._stats.blocked_by_priority += 1
                self._emit(HapticEventKind.EVENT_BLOCKED_PRIORITY, {
                    "pattern_id": pattern_id,
                    "device_id": device.device_id,
                    "priority": effective_priority.value,
                })
                raise RuntimeError("Active rumble capacity reached; priority too low to preempt")
            duration = duration_override if duration_override is not None else pattern.compute_duration()
            rumble = ActiveRumble(
                instance_id=_new_id("rum"),
                pattern_id=pattern_id,
                event_id=event_id,
                device_id=device.device_id,
                priority=effective_priority,
                duration_seconds=float(duration),
                looping=bool(pattern.looping),
                intensity_scale=max(0.0, float(intensity_scale)),
            )
            self._active[rumble.instance_id] = rumble
            self._stats.total_plays += 1
            self._emit(HapticEventKind.PATTERN_PLAYED, {
                "instance_id": rumble.instance_id,
                "pattern_id": pattern_id,
                "device_id": device.device_id,
                "priority": effective_priority.value,
                "duration_seconds": rumble.duration_seconds,
            })
            return rumble

    def stop_pattern(self, instance_id: str) -> bool:
        """Stop a single active rumble by instance id."""
        with self._lock:
            return self._stop_instance(instance_id, emit=True)

    def stop_all(self) -> int:
        """Stop all active rumbles. Returns the number stopped."""
        with self._lock:
            count = len(self._active)
            for iid in list(self._active.keys()):
                self._stop_instance(iid, emit=False)
            if count > 0:
                self._emit(HapticEventKind.ALL_STOPPED, {"stopped": count})
            return count

    def list_active(self, device_id: Optional[str] = None) -> List[ActiveRumble]:
        """List currently active rumble instances."""
        with self._lock:
            result = list(self._active.values())
            if device_id is not None:
                result = [r for r in result if r.device_id == device_id]
            return result

    # ------------------------------------------------------------------
    # Device management
    # ------------------------------------------------------------------

    def register_device(
        self,
        name: str,
        device_type: DeviceType = DeviceType.GENERIC,
        supports_low_freq: bool = True,
        supports_high_freq: bool = True,
        supports_trigger_l: bool = False,
        supports_trigger_r: bool = False,
        supports_hd_haptics: bool = False,
        max_frequency_hz: float = 250.0,
        enabled: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        device_id: Optional[str] = None,
    ) -> DeviceProfile:
        """Register a new haptic device profile."""
        with self._lock:
            did = device_id or _new_id("dev")
            if did in self._devices:
                raise ValueError(f"Device already exists: {did}")
            device = DeviceProfile(
                device_id=did,
                name=name,
                device_type=device_type,
                supports_low_freq=supports_low_freq,
                supports_high_freq=supports_high_freq,
                supports_trigger_l=supports_trigger_l,
                supports_trigger_r=supports_trigger_r,
                supports_hd_haptics=supports_hd_haptics,
                max_frequency_hz=max_frequency_hz,
                enabled=enabled,
                metadata=metadata or {},
            )
            self._devices[did] = device
            self._stats.device_counter += 1
            self._stats.total_devices = len(self._devices)
            if not self._default_device_id and enabled:
                self._default_device_id = did
            _evict_fifo_dict(self._devices, _MAX_DEVICES)
            self._emit(HapticEventKind.DEVICE_REGISTERED, {
                "device_id": did,
                "name": name,
                "device_type": device_type.value,
            })
            return device

    def get_device(self, device_id: str) -> Optional[DeviceProfile]:
        """Get a device profile by id."""
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(
        self,
        device_type: Optional[DeviceType] = None,
        enabled_only: bool = False,
    ) -> List[DeviceProfile]:
        """List device profiles with optional filters."""
        with self._lock:
            result: List[DeviceProfile] = []
            for device in self._devices.values():
                if device_type is not None and device.device_type != device_type:
                    continue
                if enabled_only and not device.enabled:
                    continue
                result.append(device)
            return result

    def set_device_enabled(self, device_id: str, enabled: bool) -> DeviceProfile:
        """Enable or disable a device. Disabling stops its active rumbles."""
        with self._lock:
            if device_id not in self._devices:
                raise KeyError(f"Device not found: {device_id}")
            device = self._devices[device_id]
            device.enabled = bool(enabled)
            device.updated_at = _now()
            if not enabled:
                # Stop active rumbles on the disabled device.
                to_stop = [
                    iid for iid, r in self._active.items() if r.device_id == device_id
                ]
                for iid in to_stop:
                    self._stop_instance(iid, emit=False)
                self._emit(HapticEventKind.DEVICE_DISABLED, {"device_id": device_id})
            else:
                self._emit(HapticEventKind.DEVICE_ENABLED, {"device_id": device_id})
            return device

    # ------------------------------------------------------------------
    # Event management
    # ------------------------------------------------------------------

    def create_event(
        self,
        name: str,
        pattern_id: str,
        device_id: str = "",
        priority: HapticPriority = HapticPriority.FEEDBACK,
        intensity_scale: float = 1.0,
        cooldown_seconds: float = 0.0,
        description: str = "",
        event_id: Optional[str] = None,
    ) -> HapticEvent:
        """Create a named haptic event bound to a pattern."""
        with self._lock:
            if pattern_id not in self._patterns:
                raise KeyError(f"Haptic pattern not found: {pattern_id}")
            eid = event_id or _new_id("evt")
            if eid in self._events:
                raise ValueError(f"Haptic event already exists: {eid}")
            event = HapticEvent(
                event_id=eid,
                name=name,
                pattern_id=pattern_id,
                device_id=device_id,
                priority=priority,
                intensity_scale=max(0.0, float(intensity_scale)),
                cooldown_seconds=max(0.0, float(cooldown_seconds)),
                description=description,
            )
            self._events[eid] = event
            self._stats.event_counter += 1
            self._stats.total_events = len(self._events)
            _evict_fifo_dict(self._events, _MAX_EVENTS)
            self._emit(HapticEventKind.EVENT_CREATED, {
                "event_id": eid,
                "name": name,
                "pattern_id": pattern_id,
            })
            return event

    def trigger_event(
        self,
        event_id: str,
        device_id: str = "",
        intensity_scale: Optional[float] = None,
    ) -> Optional[ActiveRumble]:
        """Trigger a named haptic event, enforcing cooldown and priority."""
        with self._lock:
            if event_id not in self._events:
                raise KeyError(f"Haptic event not found: {event_id}")
            event = self._events[event_id]
            # Cooldown check.
            if event.cooldown_seconds > 0.0:
                expires_at = self._cooldowns.get(event_id)
                if expires_at:
                    try:
                        expires_dt = datetime.fromisoformat(expires_at.rstrip("Z"))
                    except ValueError:
                        expires_dt = None
                    if expires_dt is not None and expires_dt > datetime.utcnow():
                        self._stats.blocked_by_cooldown += 1
                        self._emit(HapticEventKind.EVENT_BLOCKED_COOLDOWN, {
                            "event_id": event_id,
                            "expires_at": expires_at,
                        })
                        return None
            target_device = device_id or event.device_id
            scale = event.intensity_scale if intensity_scale is None else float(intensity_scale)
            rumble = self.play_pattern(
                pattern_id=event.pattern_id,
                device_id=target_device,
                intensity_scale=scale,
                priority=event.priority,
                event_id=event_id,
            )
            self._stats.total_triggers += 1
            # Register cooldown window.
            if event.cooldown_seconds > 0.0:
                expires = datetime.utcnow() + timedelta(seconds=event.cooldown_seconds)
                self._cooldowns[event_id] = expires.isoformat() + "Z"
                _evict_fifo_dict(self._cooldowns, _MAX_EVENT_COOLDOWNS)
            self._emit(HapticEventKind.EVENT_TRIGGERED, {
                "event_id": event_id,
                "pattern_id": event.pattern_id,
                "instance_id": rumble.instance_id,
            })
            return rumble

    # ------------------------------------------------------------------
    # Observability and lifecycle
    # ------------------------------------------------------------------

    def list_events_log(self, limit: int = 100) -> List[HapticsLogEvent]:
        """List recent audit log events."""
        with self._lock:
            return list(self._log[-limit:])

    def get_stats(self) -> HapticsStats:
        """Return aggregate statistics."""
        with self._lock:
            self._stats.total_patterns = len(self._patterns)
            self._stats.total_devices = len(self._devices)
            self._stats.total_events = len(self._events)
            self._stats.active_rumbles = len(self._active)
            return self._stats

    def get_status(self) -> Dict[str, Any]:
        """Return a status summary."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "total_patterns": len(self._patterns),
                "total_devices": len(self._devices),
                "total_events": len(self._events),
                "active_rumbles": len(self._active),
                "total_plays": self._stats.total_plays,
                "total_stops": self._stats.total_stops,
                "total_triggers": self._stats.total_triggers,
                "blocked_by_cooldown": self._stats.blocked_by_cooldown,
                "blocked_by_priority": self._stats.blocked_by_priority,
                "total_log_events": len(self._log),
                "default_device_id": self._default_device_id,
                "capacities": {
                    "max_patterns": _MAX_PATTERNS,
                    "max_devices": _MAX_DEVICES,
                    "max_events": _MAX_EVENTS,
                    "max_active_rumbles": _MAX_ACTIVE_RUMBLES,
                    "max_event_cooldowns": _MAX_EVENT_COOLDOWNS,
                    "max_log_events": _MAX_LOG_EVENTS,
                },
            }

    def get_snapshot(self) -> HapticsSnapshot:
        """Capture a snapshot of the entire system state."""
        with self._lock:
            return HapticsSnapshot(
                patterns=[p.to_dict() for p in self._patterns.values()],
                devices=[d.to_dict() for d in self._devices.values()],
                events=[e.to_dict() for e in self._events.values()],
                active=[r.to_dict() for r in self._active.values()],
                stats=self.get_stats().to_dict(),
            )

    def reset(self) -> None:
        """Reset the system to an empty state (clears all data)."""
        with self._lock:
            self._patterns.clear()
            self._devices.clear()
            self._events.clear()
            self._active.clear()
            self._cooldowns.clear()
            self._log.clear()
            self._default_device_id = ""
            self._stats = HapticsStats()
            self._emit(HapticEventKind.SYSTEM_RESET, {})


def get_haptics_system() -> HapticsSystem:
    """Return the singleton HapticsSystem instance."""
    return HapticsSystem()
