"""
SparkLabs Engine - Spectator Director System

Manages live spectator viewing of in-progress games. The system owns the full
camera graph for every spectated match, tracks each connected spectator
session, lays out viewports for multi-camera compositions, and drives an
automated director that selects cameras, records highlight moments, and
switches the active feed based on match activity.

The director can run in manual, automated, hybrid, or fully AI-directed
modes. Highlight moments capture noteworthy match events together with the
camera state that observed them, enabling instant replay and rewind. Camera
presets bundle a camera mode, transform, field of view, and transition so
that operators or the auto-director can recall a framing in one call.

Architecture:
  SpectatorDirectorSystem (singleton)
    |-- CameraMode, DirectorMode, SpectatorStatus, ViewportLayout,
       HighlightType, CameraPreset, TransitionType
    |-- CameraState, SpectatorSession, ViewportConfig, CameraPresetConfig,
       HighlightMoment, DirectorDecision, SpectatorConfig, SpectatorStats,
       SpectatorSnapshot, SpectatorEvent
    |-- get_spectator_director_system

Core Capabilities:
  - register_match / remove_match: create and tear down a spectating context
    for a live match.
  - register_camera / get_camera / list_cameras / remove_camera /
    update_camera / set_camera_mode / follow_entity: manage the camera graph
    for a match and steer individual cameras.
  - register_session / get_session / list_sessions / remove_session /
    switch_camera / set_viewport_layout: manage spectator sessions and the
    camera each session is currently watching.
  - create_viewport / get_viewport / list_viewports / remove_viewport:
    compose multi-camera layouts (picture-in-picture, split, quad).
  - register_preset / get_preset / list_presets / apply_preset /
    remove_preset: recallable camera framing presets.
  - record_highlight / get_highlight / list_highlights / remove_highlight:
    capture and query noteworthy match moments with their camera state.
  - start_rewind / stop_rewind: scrub a session back through the rewind
    buffer and resume live viewing.
  - auto_director_tick / list_director_decisions / set_director_mode:
    automated camera selection and director audit trail.
  - list_events / get_stats / get_status / get_snapshot / get_config /
    set_config / tick / reset: observability, tuning, and lifecycle control.

The class implements the singleton pattern with double-checked locking using
``threading.RLock``; consumers should obtain the instance through
:meth:`SpectatorDirectorSystem.get_instance` or the module-level
:func:`get_spectator_director_system` factory.
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

_MAX_MATCHES: int = 100
_MAX_SESSIONS: int = 200
_MAX_CAMERAS: int = 1000
_MAX_CAMERAS_PER_MATCH: int = 30
_MAX_VIEWPORTS: int = 1000
_MAX_VIEWPORTS_PER_SESSION: int = 16
_MAX_PRESETS: int = 200
_MAX_HIGHLIGHTS: int = 5000
_MAX_HIGHLIGHTS_PER_MATCH: int = 200
_MAX_DIRECTOR_DECISIONS: int = 4000
_MAX_EVENTS: int = 8000
_SNAPSHOT_LIMIT: int = 50


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


def _coerce_enum(enum_cls: Any, value: Any, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except (ValueError, KeyError):
        return default


def _to_jsonable(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "__dataclass_fields__"):
        return _dataclass_to_dict(value)
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


def _dataclass_to_dict(instance: Any) -> Dict[str, Any]:
    if instance is None:
        return {}
    if not hasattr(instance, "__dataclass_fields__"):
        if isinstance(instance, dict):
            return {str(k): _to_jsonable(v) for k, v in instance.items()}
        if hasattr(instance, "to_dict") and callable(instance.to_dict):
            return instance.to_dict()
        return {}
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


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class CameraMode(str, Enum):
    """Operating mode of a spectator camera."""

    FREECAM = "freecam"
    FOLLOW = "follow"
    ORBITAL = "orbital"
    CINEMATIC = "cinematic"
    FIRST_PERSON = "first_person"
    THIRD_PERSON = "third_person"
    TOP_DOWN = "top_down"
    ISOMETRIC = "isometric"


class DirectorMode(str, Enum):
    """Strategy used by the auto-director for a match."""

    MANUAL = "manual"
    AUTOMATED = "automated"
    HYBRID = "hybrid"
    AI_DIRECTED = "ai_directed"


class SpectatorStatus(str, Enum):
    """Lifecycle state of a spectator session."""

    OBSERVING = "observing"
    IDLE = "idle"
    FOLLOWING = "following"
    REWIND = "rewind"
    PAUSED = "paused"
    DISCONNECTED = "disconnected"


class ViewportLayout(str, Enum):
    """Composition layout for one or more cameras on a spectator viewport."""

    SINGLE = "single"
    PIP = "pip"
    SPLIT_HORIZONTAL = "split_horizontal"
    SPLIT_VERTICAL = "split_vertical"
    QUAD = "quad"
    PICTURE_IN_PICTURE = "picture_in_picture"


class HighlightType(str, Enum):
    """Category of a captured highlight moment."""

    KILL = "kill"
    OBJECTIVE = "objective"
    TEAMFIGHT = "teamfight"
    ESCAPE = "escape"
    CLUTCH = "clutch"
    ACE = "ace"
    COMEBACK = "comeback"
    RECORD_BREAK = "record_break"


class CameraPreset(str, Enum):
    """Named framing presets that map to a stored CameraPresetConfig."""

    OVERVIEW = "overview"
    PLAYER_FOCUS = "player_focus"
    OBJECTIVE_VIEW = "objective_view"
    SPECTATOR_DEFAULT = "spectator_default"
    CINEMATIC_INTRO = "cinematic_intro"
    REPLAY_ANGLE = "replay_angle"


class TransitionType(str, Enum):
    """Visual transition applied when switching to a camera or preset."""

    CUT = "cut"
    DISSOLVE = "dissolve"
    PAN = "pan"
    ZOOM = "zoom"
    WIPE = "wipe"
    FADE = "fade"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class CameraState:
    """Transform and mode of a single spectator camera."""

    camera_id: str
    match_id: str
    position_x: float = 0.0
    position_y: float = 10.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    rotation_z: float = 0.0
    fov: float = 60.0
    mode: str = CameraMode.FREECAM.value
    target_entity_id: str = ""
    speed: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpectatorSession:
    """A single spectator observing a match."""

    session_id: str
    spectator_id: str
    match_id: str
    status: str = SpectatorStatus.OBSERVING.value
    current_camera_id: str = ""
    viewport_layout: str = ViewportLayout.SINGLE.value
    following_entity_id: str = ""
    rewind_position: float = 0.0
    joined_time: str = field(default_factory=_now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ViewportConfig:
    """A rectangular viewport binding one camera within a session layout."""

    viewport_id: str
    session_id: str
    layout: str = ViewportLayout.SINGLE.value
    camera_id: str = ""
    position_x: float = 0.0
    position_y: float = 0.0
    width: float = 1.0
    height: float = 1.0
    opacity: float = 1.0
    is_primary: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class CameraPresetConfig:
    """A recallable camera framing with an associated transition."""

    preset_id: str
    name: str
    camera_mode: str = CameraMode.FREECAM.value
    position_x: float = 0.0
    position_y: float = 0.0
    position_z: float = 0.0
    rotation_x: float = 0.0
    rotation_y: float = 0.0
    fov: float = 60.0
    transition_type: str = TransitionType.CUT.value
    transition_duration: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HighlightMoment:
    """A noteworthy match moment captured with its observing camera state."""

    highlight_id: str
    match_id: str
    timestamp: str = field(default_factory=_now)
    highlight_type: str = HighlightType.KILL.value
    description: str = ""
    camera_state_json: str = ""
    duration: float = 5.0
    importance_score: float = 0.5
    entity_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DirectorDecision:
    """A single auto-director camera selection decision for a match."""

    decision_id: str
    match_id: str
    timestamp: str = field(default_factory=_now)
    action_type: str = "switch_camera"
    target_camera_id: str = ""
    target_entity_id: str = ""
    reason: str = ""
    confidence: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpectatorConfig:
    """Global tuning parameters for the spectator director system."""

    max_sessions: int = 200
    max_cameras_per_match: int = 30
    max_highlights_per_match: int = 200
    auto_director_enabled: bool = True
    highlight_detection_enabled: bool = True
    rewind_buffer_seconds: float = 30.0
    default_camera_mode: str = CameraMode.FREECAM.value
    default_viewport_layout: str = ViewportLayout.SINGLE.value
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpectatorStats:
    """Aggregate statistics for the spectator director system."""

    total_sessions: int = 0
    active_sessions: int = 0
    total_matches_spectated: int = 0
    total_highlights: int = 0
    total_camera_switches: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpectatorSnapshot:
    """Full state snapshot of the spectator director system."""

    timestamp: str = field(default_factory=_now)
    sessions: List[Dict[str, Any]] = field(default_factory=list)
    cameras: List[Dict[str, Any]] = field(default_factory=list)
    highlights: List[Dict[str, Any]] = field(default_factory=list)
    director_decisions: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class SpectatorEvent:
    """An audit event emitted by the spectator director system."""

    event_id: str
    event_type: str
    timestamp: str = field(default_factory=_now)
    session_id: str = ""
    match_id: str = ""
    camera_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Spectator Director System
# ---------------------------------------------------------------------------


class SpectatorDirectorSystem:
    """Manages spectator cameras, sessions, viewports, presets, highlights,
    and the automated director for one or more live matches."""

    _instance: Optional["SpectatorDirectorSystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._matches: Dict[str, Dict[str, Any]] = {}
        self._cameras: Dict[str, CameraState] = {}
        self._sessions: Dict[str, SpectatorSession] = {}
        self._viewports: Dict[str, ViewportConfig] = {}
        self._viewports_by_session: Dict[str, List[str]] = {}
        self._presets: Dict[str, CameraPresetConfig] = {}
        self._highlights: Dict[str, HighlightMoment] = {}
        self._director_decisions: List[DirectorDecision] = []
        self._director_modes: Dict[str, str] = {}
        self._events: List[SpectatorEvent] = []
        self._config = SpectatorConfig()
        self._stats = SpectatorStats()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._switch_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "SpectatorDirectorSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _emit(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        session_id: str = "",
        match_id: str = "",
        camera_id: str = "",
    ) -> None:
        event = SpectatorEvent(
            event_id=_new_id("evt"),
            event_type=event_type,
            timestamp=_now(),
            session_id=session_id,
            match_id=match_id,
            camera_id=camera_id,
            data=data or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def _refresh_stats(self) -> None:
        self._stats.total_sessions = len(self._sessions)
        self._stats.active_sessions = sum(
            1
            for s in self._sessions.values()
            if s.status
            in (
                SpectatorStatus.OBSERVING.value,
                SpectatorStatus.FOLLOWING.value,
                SpectatorStatus.REWIND.value,
            )
        )
        self._stats.total_matches_spectated = len(self._matches)
        self._stats.total_highlights = len(self._highlights)
        self._stats.total_camera_switches = self._switch_counter
        self._stats.tick_count = self._tick_count

    def _match_cameras(self, match_id: str) -> List[CameraState]:
        ctx = self._matches.get(match_id)
        if not ctx:
            return []
        out: List[CameraState] = []
        for cid in ctx.get("cameras", []):
            cam = self._cameras.get(cid)
            if cam is not None:
                out.append(cam)
        return out

    def _ensure_session_viewports(self, session_id: str) -> List[str]:
        if session_id not in self._viewports_by_session:
            self._viewports_by_session[session_id] = []
        return self._viewports_by_session[session_id]

    # ------------------------------------------------------------------
    # Match Management
    # ------------------------------------------------------------------

    def register_match(
        self,
        match_id: str,
        name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """Create a spectating context for a live match."""
        if not match_id:
            return False, "match_id required", None
        with self._lock:
            if match_id in self._matches:
                return False, "match_id already exists", None
            if len(self._matches) >= _MAX_MATCHES:
                return False, "match capacity reached", None
            ctx: Dict[str, Any] = {
                "match_id": match_id,
                "name": name or match_id,
                "cameras": [],
                "sessions": [],
                "highlights": [],
                "director_mode": DirectorMode.AUTOMATED.value,
                "created_time": _now(),
                "metadata": metadata or {},
            }
            self._matches[match_id] = ctx
            self._director_modes[match_id] = DirectorMode.AUTOMATED.value
            self._refresh_stats()
            self._emit(
                "match_registered",
                {"name": ctx["name"]},
                match_id=match_id,
            )
            return True, "registered", ctx

    def remove_match(self, match_id: str) -> Tuple[bool, str]:
        """Remove a match and its associated spectating context."""
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "not found"
            # Clean up cameras owned by this match.
            for cid in list(ctx.get("cameras", [])):
                self._cameras.pop(cid, None)
            # Clean up sessions observing this match.
            for sid in list(ctx.get("sessions", [])):
                sess = self._sessions.pop(sid, None)
                if sess:
                    self._viewports_by_session.pop(sid, None)
            # Clean up highlights recorded for this match.
            for hid in list(ctx.get("highlights", [])):
                self._highlights.pop(hid, None)
            self._director_modes.pop(match_id, None)
            del self._matches[match_id]
            self._refresh_stats()
            self._emit("match_removed", {"match_id": match_id}, match_id=match_id)
            return True, "removed"

    # ------------------------------------------------------------------
    # Camera Management
    # ------------------------------------------------------------------

    def register_camera(
        self,
        camera_id: str,
        match_id: str,
        mode: str = "freecam",
        position_x: float = 0,
        position_y: float = 10,
        position_z: float = 0,
        rotation_x: float = 0,
        rotation_y: float = 0,
        rotation_z: float = 0,
        fov: float = 60,
        target_entity_id: str = "",
        speed: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CameraState]]:
        """Register a new spectator camera for a match."""
        if not camera_id or not match_id:
            return False, "camera_id and match_id required", None
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "match not found", None
            if camera_id in self._cameras:
                return False, "camera_id already exists", None
            if len(self._cameras) >= _MAX_CAMERAS:
                return False, "camera capacity reached", None
            if len(ctx["cameras"]) >= self._config.max_cameras_per_match:
                return False, "per-match camera capacity reached", None
            mode_enum = _coerce_enum(CameraMode, mode, CameraMode.FREECAM)
            cam = CameraState(
                camera_id=camera_id,
                match_id=match_id,
                position_x=_safe_float(position_x, 0.0),
                position_y=_safe_float(position_y, 10.0),
                position_z=_safe_float(position_z, 0.0),
                rotation_x=_safe_float(rotation_x, 0.0),
                rotation_y=_safe_float(rotation_y, 0.0),
                rotation_z=_safe_float(rotation_z, 0.0),
                fov=_safe_float(fov, 60.0),
                mode=mode_enum.value,
                target_entity_id=target_entity_id or "",
                speed=_safe_float(speed, 1.0),
                metadata=metadata or {},
            )
            self._cameras[camera_id] = cam
            ctx["cameras"].append(camera_id)
            self._refresh_stats()
            self._emit(
                "camera_registered",
                {"mode": cam.mode, "match_id": match_id},
                match_id=match_id,
                camera_id=camera_id,
            )
            return True, "registered", cam

    def get_camera(self, camera_id: str) -> Optional[CameraState]:
        """Get a camera by ID."""
        with self._lock:
            return self._cameras.get(camera_id)

    def list_cameras(self, match_id: str) -> List[CameraState]:
        """List all cameras for a match."""
        with self._lock:
            return self._match_cameras(match_id)

    def remove_camera(self, camera_id: str) -> Tuple[bool, str]:
        """Remove a camera from the system."""
        with self._lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "not found"
            ctx = self._matches.get(cam.match_id)
            if ctx and camera_id in ctx.get("cameras", []):
                ctx["cameras"].remove(camera_id)
            # Clear links from sessions and viewports.
            for sess in self._sessions.values():
                if sess.current_camera_id == camera_id:
                    sess.current_camera_id = ""
            for vp in self._viewports.values():
                if vp.camera_id == camera_id:
                    vp.camera_id = ""
            del self._cameras[camera_id]
            self._refresh_stats()
            self._emit(
                "camera_removed",
                {"camera_id": camera_id},
                match_id=cam.match_id,
                camera_id=camera_id,
            )
            return True, "removed"

    def update_camera(
        self, camera_id: str, **kwargs: Any
    ) -> Tuple[bool, str, Optional[CameraState]]:
        """Update one or more fields on an existing camera."""
        with self._lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "not found", None
            for key, value in kwargs.items():
                if key == "mode":
                    mode_enum = _coerce_enum(CameraMode, value, None)
                    if mode_enum is None:
                        return False, "invalid camera mode", None
                    cam.mode = mode_enum.value
                elif key == "metadata" and isinstance(value, dict):
                    cam.metadata = dict(value)
                elif key in (
                    "position_x",
                    "position_y",
                    "position_z",
                    "rotation_x",
                    "rotation_y",
                    "rotation_z",
                    "fov",
                    "speed",
                ):
                    setattr(cam, key, _safe_float(value, getattr(cam, key)))
                elif key in ("camera_id", "match_id"):
                    # Identity keys are immutable; skip silently.
                    continue
                elif hasattr(cam, key):
                    setattr(cam, key, value)
            self._emit(
                "camera_updated",
                {"keys": list(kwargs.keys())},
                match_id=cam.match_id,
                camera_id=camera_id,
            )
            return True, "updated", cam

    def set_camera_mode(
        self, camera_id: str, mode: Any
    ) -> Tuple[bool, str, Optional[CameraState]]:
        """Set the operating mode of a camera."""
        mode_enum = _coerce_enum(CameraMode, mode, None)
        if mode_enum is None:
            return False, "invalid camera mode", None
        with self._lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "not found", None
            cam.mode = mode_enum.value
            self._emit(
                "camera_mode_set",
                {"mode": cam.mode},
                match_id=cam.match_id,
                camera_id=camera_id,
            )
            return True, "mode set", cam

    def follow_entity(
        self, camera_id: str, entity_id: str
    ) -> Tuple[bool, str, Optional[CameraState]]:
        """Point a camera at an entity and switch it to follow mode."""
        if not entity_id:
            return False, "entity_id required", None
        with self._lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "not found", None
            cam.target_entity_id = entity_id
            cam.mode = CameraMode.FOLLOW.value
            self._emit(
                "camera_follow",
                {"entity_id": entity_id},
                match_id=cam.match_id,
                camera_id=camera_id,
            )
            return True, "following", cam

    # ------------------------------------------------------------------
    # Session Management
    # ------------------------------------------------------------------

    def register_session(
        self,
        session_id: str,
        spectator_id: str,
        match_id: str,
        viewport_layout: str = "single",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[SpectatorSession]]:
        """Register a new spectator session for a match."""
        if not session_id or not spectator_id or not match_id:
            return False, "session_id, spectator_id and match_id required", None
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "match not found", None
            if session_id in self._sessions:
                return False, "session_id already exists", None
            if len(self._sessions) >= self._config.max_sessions:
                return False, "session capacity reached", None
            layout_enum = _coerce_enum(
                ViewportLayout, viewport_layout, ViewportLayout.SINGLE
            )
            # Default the session to the first camera of the match, if any.
            cameras = ctx.get("cameras", [])
            current_cam = cameras[0] if cameras else ""
            sess = SpectatorSession(
                session_id=session_id,
                spectator_id=spectator_id,
                match_id=match_id,
                status=SpectatorStatus.OBSERVING.value,
                current_camera_id=current_cam,
                viewport_layout=layout_enum.value,
                metadata=metadata or {},
            )
            self._sessions[session_id] = sess
            ctx["sessions"].append(session_id)
            self._ensure_session_viewports(session_id)
            self._refresh_stats()
            self._emit(
                "session_registered",
                {"spectator_id": spectator_id, "layout": sess.viewport_layout},
                session_id=session_id,
                match_id=match_id,
            )
            return True, "registered", sess

    def get_session(self, session_id: str) -> Optional[SpectatorSession]:
        """Get a spectator session by ID."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, match_id: str = "") -> List[SpectatorSession]:
        """List spectator sessions, optionally filtered by match."""
        with self._lock:
            sessions = list(self._sessions.values())
            if match_id:
                sessions = [s for s in sessions if s.match_id == match_id]
            return sessions

    def remove_session(self, session_id: str) -> Tuple[bool, str]:
        """Remove a spectator session and its viewports."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "not found"
            ctx = self._matches.get(sess.match_id)
            if ctx and session_id in ctx.get("sessions", []):
                ctx["sessions"].remove(session_id)
            for vid in list(self._viewports_by_session.get(session_id, [])):
                self._viewports.pop(vid, None)
            self._viewports_by_session.pop(session_id, None)
            del self._sessions[session_id]
            self._refresh_stats()
            self._emit(
                "session_removed",
                {"session_id": session_id},
                session_id=session_id,
                match_id=sess.match_id,
            )
            return True, "removed"

    def switch_camera(
        self, session_id: str, camera_id: str
    ) -> Tuple[bool, str, Optional[SpectatorSession]]:
        """Switch the camera a session is currently observing."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "session not found", None
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "camera not found", None
            if cam.match_id != sess.match_id:
                return False, "camera belongs to a different match", None
            sess.current_camera_id = camera_id
            sess.status = SpectatorStatus.OBSERVING.value
            self._switch_counter += 1
            self._refresh_stats()
            self._emit(
                "camera_switched",
                {"camera_id": camera_id},
                session_id=session_id,
                match_id=sess.match_id,
                camera_id=camera_id,
            )
            return True, "switched", sess

    def set_viewport_layout(
        self, session_id: str, layout: Any
    ) -> Tuple[bool, str, Optional[SpectatorSession]]:
        """Set the viewport composition layout for a session."""
        layout_enum = _coerce_enum(ViewportLayout, layout, None)
        if layout_enum is None:
            return False, "invalid viewport layout", None
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "session not found", None
            sess.viewport_layout = layout_enum.value
            self._emit(
                "viewport_layout_set",
                {"layout": sess.viewport_layout},
                session_id=session_id,
                match_id=sess.match_id,
            )
            return True, "layout set", sess

    # ------------------------------------------------------------------
    # Viewport Management
    # ------------------------------------------------------------------

    def create_viewport(
        self,
        viewport_id: str,
        session_id: str,
        layout: Any,
        camera_id: str,
        position_x: float = 0,
        position_y: float = 0,
        width: float = 1,
        height: float = 1,
        opacity: float = 1.0,
        is_primary: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[ViewportConfig]]:
        """Create a viewport binding a camera within a session layout."""
        if not viewport_id or not session_id:
            return False, "viewport_id and session_id required", None
        layout_enum = _coerce_enum(ViewportLayout, layout, None)
        if layout_enum is None:
            return False, "invalid viewport layout", None
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "session not found", None
            if viewport_id in self._viewports:
                return False, "viewport_id already exists", None
            if len(self._viewports) >= _MAX_VIEWPORTS:
                return False, "viewport capacity reached", None
            vp_list = self._ensure_session_viewports(session_id)
            if len(vp_list) >= _MAX_VIEWPORTS_PER_SESSION:
                return False, "per-session viewport capacity reached", None
            vp = ViewportConfig(
                viewport_id=viewport_id,
                session_id=session_id,
                layout=layout_enum.value,
                camera_id=camera_id or "",
                position_x=_safe_float(position_x, 0.0),
                position_y=_safe_float(position_y, 0.0),
                width=_safe_float(width, 1.0),
                height=_safe_float(height, 1.0),
                opacity=_clamp(_safe_float(opacity, 1.0), 0.0, 1.0),
                is_primary=bool(is_primary),
                metadata=metadata or {},
            )
            self._viewports[viewport_id] = vp
            vp_list.append(viewport_id)
            # If marked primary, demote any other primary viewport.
            if vp.is_primary:
                for other_id in vp_list:
                    if other_id == viewport_id:
                        continue
                    other = self._viewports.get(other_id)
                    if other and other.is_primary:
                        other.is_primary = False
            self._emit(
                "viewport_created",
                {"layout": vp.layout, "camera_id": vp.camera_id},
                session_id=session_id,
                match_id=sess.match_id,
                camera_id=camera_id,
            )
            return True, "created", vp

    def get_viewport(self, viewport_id: str) -> Optional[ViewportConfig]:
        """Get a viewport by ID."""
        with self._lock:
            return self._viewports.get(viewport_id)

    def list_viewports(self, session_id: str) -> List[ViewportConfig]:
        """List all viewports belonging to a session."""
        with self._lock:
            out: List[ViewportConfig] = []
            for vid in self._viewports_by_session.get(session_id, []):
                vp = self._viewports.get(vid)
                if vp is not None:
                    out.append(vp)
            return out

    def remove_viewport(self, viewport_id: str) -> Tuple[bool, str]:
        """Remove a viewport from a session."""
        with self._lock:
            vp = self._viewports.get(viewport_id)
            if not vp:
                return False, "not found"
            vp_list = self._viewports_by_session.get(vp.session_id, [])
            if viewport_id in vp_list:
                vp_list.remove(viewport_id)
            del self._viewports[viewport_id]
            self._emit(
                "viewport_removed",
                {"viewport_id": viewport_id},
                session_id=vp.session_id,
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Camera Preset Management
    # ------------------------------------------------------------------

    def register_preset(
        self,
        preset_id: str,
        name: str,
        camera_mode: Any,
        position_x: float = 0,
        position_y: float = 0,
        position_z: float = 0,
        rotation_x: float = 0,
        rotation_y: float = 0,
        fov: float = 60,
        transition_type: str = "cut",
        transition_duration: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[CameraPresetConfig]]:
        """Register a recallable camera framing preset."""
        if not preset_id or not name:
            return False, "preset_id and name required", None
        mode_enum = _coerce_enum(CameraMode, camera_mode, None)
        if mode_enum is None:
            return False, "invalid camera mode", None
        transition_enum = _coerce_enum(TransitionType, transition_type, TransitionType.CUT)
        with self._lock:
            if preset_id in self._presets:
                return False, "preset_id already exists", None
            if len(self._presets) >= _MAX_PRESETS:
                return False, "preset capacity reached", None
            preset = CameraPresetConfig(
                preset_id=preset_id,
                name=name,
                camera_mode=mode_enum.value,
                position_x=_safe_float(position_x, 0.0),
                position_y=_safe_float(position_y, 0.0),
                position_z=_safe_float(position_z, 0.0),
                rotation_x=_safe_float(rotation_x, 0.0),
                rotation_y=_safe_float(rotation_y, 0.0),
                fov=_safe_float(fov, 60.0),
                transition_type=transition_enum.value,
                transition_duration=_safe_float(transition_duration, 0.5),
                metadata=metadata or {},
            )
            self._presets[preset_id] = preset
            self._emit(
                "preset_registered",
                {"name": name, "camera_mode": preset.camera_mode},
            )
            return True, "registered", preset

    def get_preset(self, preset_id: str) -> Optional[CameraPresetConfig]:
        """Get a camera preset by ID."""
        with self._lock:
            return self._presets.get(preset_id)

    def list_presets(self) -> List[CameraPresetConfig]:
        """List all registered camera presets."""
        with self._lock:
            return list(self._presets.values())

    def apply_preset(
        self, camera_id: str, preset_id: str
    ) -> Tuple[bool, str, Optional[CameraState]]:
        """Apply a preset's framing and mode to an existing camera."""
        with self._lock:
            cam = self._cameras.get(camera_id)
            if not cam:
                return False, "camera not found", None
            preset = self._presets.get(preset_id)
            if not preset:
                return False, "preset not found", None
            cam.mode = preset.camera_mode
            cam.position_x = preset.position_x
            cam.position_y = preset.position_y
            cam.position_z = preset.position_z
            cam.rotation_x = preset.rotation_x
            cam.rotation_y = preset.rotation_y
            cam.fov = preset.fov
            self._emit(
                "preset_applied",
                {
                    "preset_id": preset_id,
                    "transition_type": preset.transition_type,
                    "transition_duration": preset.transition_duration,
                },
                match_id=cam.match_id,
                camera_id=camera_id,
            )
            return True, "applied", cam

    def remove_preset(self, preset_id: str) -> Tuple[bool, str]:
        """Remove a camera preset."""
        with self._lock:
            if preset_id not in self._presets:
                return False, "not found"
            del self._presets[preset_id]
            self._emit(
                "preset_removed",
                {"preset_id": preset_id},
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Highlight Management
    # ------------------------------------------------------------------

    def record_highlight(
        self,
        highlight_id: str,
        match_id: str,
        highlight_type: Any,
        description: str = "",
        timestamp: str = "",
        duration: float = 5.0,
        importance_score: float = 0.5,
        entity_ids: Optional[List[str]] = None,
        camera_state_json: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[HighlightMoment]]:
        """Record a noteworthy match moment with its observing camera state."""
        if not highlight_id or not match_id:
            return False, "highlight_id and match_id required", None
        type_enum = _coerce_enum(HighlightType, highlight_type, None)
        if type_enum is None:
            return False, "invalid highlight type", None
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "match not found", None
            if highlight_id in self._highlights:
                return False, "highlight_id already exists", None
            if len(ctx.get("highlights", [])) >= self._config.max_highlights_per_match:
                return False, "per-match highlight capacity reached", None
            if len(self._highlights) >= _MAX_HIGHLIGHTS:
                return False, "highlight capacity reached", None
            hl = HighlightMoment(
                highlight_id=highlight_id,
                match_id=match_id,
                timestamp=timestamp or _now(),
                highlight_type=type_enum.value,
                description=description or "",
                camera_state_json=camera_state_json or "",
                duration=_safe_float(duration, 5.0),
                importance_score=_clamp(_safe_float(importance_score, 0.5), 0.0, 1.0),
                entity_ids=list(entity_ids) if entity_ids else [],
                metadata=metadata or {},
            )
            self._highlights[highlight_id] = hl
            ctx["highlights"].append(highlight_id)
            self._refresh_stats()
            self._emit(
                "highlight_recorded",
                {
                    "highlight_type": hl.highlight_type,
                    "importance_score": hl.importance_score,
                },
                match_id=match_id,
            )
            return True, "recorded", hl

    def get_highlight(self, highlight_id: str) -> Optional[HighlightMoment]:
        """Get a highlight moment by ID."""
        with self._lock:
            return self._highlights.get(highlight_id)

    def list_highlights(
        self, match_id: str = "", highlight_type: str = ""
    ) -> List[HighlightMoment]:
        """List highlight moments, optionally filtered by match and type."""
        with self._lock:
            items = list(self._highlights.values())
            if match_id:
                items = [h for h in items if h.match_id == match_id]
            if highlight_type:
                items = [h for h in items if h.highlight_type == highlight_type]
            return items

    def remove_highlight(self, highlight_id: str) -> Tuple[bool, str]:
        """Remove a recorded highlight moment."""
        with self._lock:
            hl = self._highlights.get(highlight_id)
            if not hl:
                return False, "not found"
            ctx = self._matches.get(hl.match_id)
            if ctx and highlight_id in ctx.get("highlights", []):
                ctx["highlights"].remove(highlight_id)
            del self._highlights[highlight_id]
            self._refresh_stats()
            self._emit(
                "highlight_removed",
                {"highlight_id": highlight_id},
                match_id=hl.match_id,
            )
            return True, "removed"

    # ------------------------------------------------------------------
    # Rewind Control
    # ------------------------------------------------------------------

    def start_rewind(
        self, session_id: str, seconds_back: float
    ) -> Tuple[bool, str, Optional[SpectatorSession]]:
        """Begin rewinding a session by the requested number of seconds."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "session not found", None
            back = _safe_float(seconds_back, 0.0)
            if back < 0:
                back = 0.0
            buffer_cap = _safe_float(self._config.rewind_buffer_seconds, 30.0)
            back = _clamp(back, 0.0, buffer_cap)
            sess.status = SpectatorStatus.REWIND.value
            sess.rewind_position = back
            self._emit(
                "rewind_started",
                {"seconds_back": back, "buffer_cap": buffer_cap},
                session_id=session_id,
                match_id=sess.match_id,
            )
            return True, "rewinding", sess

    def stop_rewind(
        self, session_id: str
    ) -> Tuple[bool, str, Optional[SpectatorSession]]:
        """Stop rewinding a session and resume live observation."""
        with self._lock:
            sess = self._sessions.get(session_id)
            if not sess:
                return False, "session not found", None
            sess.status = SpectatorStatus.OBSERVING.value
            sess.rewind_position = 0.0
            self._emit(
                "rewind_stopped",
                {},
                session_id=session_id,
                match_id=sess.match_id,
            )
            return True, "live", sess

    # ------------------------------------------------------------------
    # Auto Director
    # ------------------------------------------------------------------

    def auto_director_tick(
        self, match_id: str
    ) -> Tuple[bool, str, Optional[DirectorDecision]]:
        """Run one auto-director step for a match and return the decision."""
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "match not found", None
            mode = self._director_modes.get(
                match_id, DirectorMode.AUTOMATED.value
            )
            if mode == DirectorMode.MANUAL.value:
                return False, "director in manual mode", None
            cameras = self._match_cameras(match_id)
            if not cameras:
                return False, "no cameras available", None
            # Rotate through cameras based on the current tick count so the
            # selection is deterministic but advances over time.
            idx = self._tick_count % len(cameras)
            target = cameras[idx]
            highlights = [
                h for h in self._highlights.values() if h.match_id == match_id
            ]
            # Confidence grows with recent highlight density, capped at 0.95.
            confidence = _clamp(0.55 + 0.04 * len(highlights), 0.0, 0.95)
            decision = DirectorDecision(
                decision_id=_new_id("dec"),
                match_id=match_id,
                timestamp=_now(),
                action_type="switch_camera",
                target_camera_id=target.camera_id,
                target_entity_id=target.target_entity_id,
                reason=f"auto-director selected {target.camera_id} ({mode})",
                confidence=confidence,
                metadata={
                    "mode": mode,
                    "camera_mode": target.mode,
                    "camera_count": len(cameras),
                },
            )
            self._director_decisions.append(decision)
            _evict_fifo_list(self._director_decisions, _MAX_DIRECTOR_DECISIONS)
            # Apply the decision to every active session on this match.
            for sess in self._sessions.values():
                if sess.match_id != match_id:
                    continue
                if sess.status == SpectatorStatus.REWIND.value:
                    continue
                if sess.current_camera_id != target.camera_id:
                    sess.current_camera_id = target.camera_id
                    self._switch_counter += 1
            self._refresh_stats()
            self._emit(
                "director_decision",
                {
                    "decision_id": decision.decision_id,
                    "target_camera_id": target.camera_id,
                    "confidence": confidence,
                    "mode": mode,
                },
                match_id=match_id,
                camera_id=target.camera_id,
            )
            return True, "decided", decision

    def list_director_decisions(
        self, match_id: str = "", limit: int = 50
    ) -> List[DirectorDecision]:
        """List director decisions, optionally filtered by match."""
        with self._lock:
            items = list(self._director_decisions)
            if match_id:
                items = [d for d in items if d.match_id == match_id]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def set_director_mode(
        self, match_id: str, mode: Any
    ) -> Tuple[bool, str]:
        """Set the director mode for a match."""
        mode_enum = _coerce_enum(DirectorMode, mode, None)
        if mode_enum is None:
            return False, "invalid director mode"
        with self._lock:
            ctx = self._matches.get(match_id)
            if not ctx:
                return False, "match not found"
            ctx["director_mode"] = mode_enum.value
            self._director_modes[match_id] = mode_enum.value
            self._emit(
                "director_mode_set",
                {"mode": mode_enum.value},
                match_id=match_id,
            )
            return True, "set"

    # ------------------------------------------------------------------
    # Events, Stats, Status, Snapshot, Config, Tick, Reset
    # ------------------------------------------------------------------

    def list_events(
        self,
        session_id: str = "",
        match_id: str = "",
        limit: int = 100,
    ) -> List[SpectatorEvent]:
        """List audit events, optionally filtered by session and match."""
        with self._lock:
            items = list(self._events)
            if session_id:
                items = [e for e in items if e.session_id == session_id]
            if match_id:
                items = [e for e in items if e.match_id == match_id]
            if limit and limit > 0:
                items = items[-limit:]
            return items

    def get_status(self) -> Dict[str, Any]:
        """Get a system status summary."""
        with self._lock:
            self._refresh_stats()
            return {
                "initialized": self._initialized,
                "matches": len(self._matches),
                "cameras": len(self._cameras),
                "sessions": len(self._sessions),
                "viewports": len(self._viewports),
                "presets": len(self._presets),
                "highlights": len(self._highlights),
                "director_decisions": len(self._director_decisions),
                "events": len(self._events),
                "tick_count": self._tick_count,
            }

    def get_stats(self) -> SpectatorStats:
        """Get aggregate statistics."""
        with self._lock:
            self._refresh_stats()
            return self._stats

    def get_snapshot(self) -> SpectatorSnapshot:
        """Get a full state snapshot."""
        with self._lock:
            self._refresh_stats()
            return SpectatorSnapshot(
                timestamp=_now(),
                sessions=[
                    s.to_dict() for s in list(self._sessions.values())[:_SNAPSHOT_LIMIT]
                ],
                cameras=[
                    c.to_dict() for c in list(self._cameras.values())[:_SNAPSHOT_LIMIT]
                ],
                highlights=[
                    h.to_dict() for h in list(self._highlights.values())[:_SNAPSHOT_LIMIT]
                ],
                director_decisions=[
                    d.to_dict()
                    for d in list(self._director_decisions)[-_SNAPSHOT_LIMIT:]
                ],
                stats=self._stats.to_dict(),
            )

    def get_config(self) -> SpectatorConfig:
        """Get the current configuration."""
        with self._lock:
            return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, SpectatorConfig]:
        """Update one or more configuration parameters."""
        with self._lock:
            for key, value in kwargs.items():
                if key == "metadata" and isinstance(value, dict):
                    self._config.metadata.update(value)
                elif hasattr(self._config, key):
                    setattr(self._config, key, value)
            self._emit(
                "config_updated",
                {"keys": list(kwargs.keys())},
            )
            return True, "updated", self._config

    def tick(self) -> Dict[str, Any]:
        """Advance the simulation by one tick."""
        with self._lock:
            self._tick_count += 1
            decisions = 0
            if self._config.auto_director_enabled:
                for match_id in list(self._matches.keys()):
                    mode = self._director_modes.get(
                        match_id, DirectorMode.AUTOMATED.value
                    )
                    if mode == DirectorMode.MANUAL.value:
                        continue
                    ok, _, _ = self.auto_director_tick(match_id)
                    if ok:
                        decisions += 1
            self._refresh_stats()
            self._emit(
                "tick",
                {
                    "tick_count": self._tick_count,
                    "director_decisions": decisions,
                },
            )
            return {
                "tick_count": self._tick_count,
                "director_decisions": decisions,
                "active_sessions": self._stats.active_sessions,
                "total_cameras": len(self._cameras),
                "total_highlights": len(self._highlights),
            }

    def reset(self) -> None:
        """Reset the system to the seed state."""
        with self._init_lock:
            self._matches.clear()
            self._cameras.clear()
            self._sessions.clear()
            self._viewports.clear()
            self._viewports_by_session.clear()
            self._presets.clear()
            self._highlights.clear()
            self._director_decisions.clear()
            self._director_modes.clear()
            self._events.clear()
            self._config = SpectatorConfig()
            self._stats = SpectatorStats()
            self._tick_count = 0
            self._event_counter = 0
            self._switch_counter = 0
            self._initialized = False
            self._seed()

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with a canonical spectating dataset."""
        with self._init_lock:
            if self._initialized:
                return

            # ----------------------------------------------------------
            # Matches (3)
            # ----------------------------------------------------------
            self._seed_matches()

            # ----------------------------------------------------------
            # Cameras (10 across all matches)
            # ----------------------------------------------------------
            self._seed_cameras()

            # ----------------------------------------------------------
            # Spectator Sessions (5)
            # ----------------------------------------------------------
            self._seed_sessions()

            # ----------------------------------------------------------
            # Viewports (5)
            # ----------------------------------------------------------
            self._seed_viewports()

            # ----------------------------------------------------------
            # Camera Presets (6)
            # ----------------------------------------------------------
            self._seed_presets()

            # ----------------------------------------------------------
            # Highlight Moments (5)
            # ----------------------------------------------------------
            self._seed_highlights()

            # ----------------------------------------------------------
            # Director Decisions (5)
            # ----------------------------------------------------------
            self._seed_director_decisions()

            self._refresh_stats()
            self._emit(
                "system_seeded",
                {
                    "matches": len(self._matches),
                    "cameras": len(self._cameras),
                    "sessions": len(self._sessions),
                    "viewports": len(self._viewports),
                    "presets": len(self._presets),
                    "highlights": len(self._highlights),
                    "director_decisions": len(self._director_decisions),
                },
            )
            self._initialized = True

    def _seed_matches(self) -> None:
        matches = [
            (
                "match_grand_final",
                "Grand Final - World Championship",
                {"stage": "grand_final", "region": "global"},
            ),
            (
                "match_semifinal_1",
                "Semifinal 1 - World Championship",
                {"stage": "semifinal", "region": "global"},
            ),
            (
                "match_semifinal_2",
                "Semifinal 2 - World Championship",
                {"stage": "semifinal", "region": "global"},
            ),
        ]
        for match_id, name, meta in matches:
            ctx: Dict[str, Any] = {
                "match_id": match_id,
                "name": name,
                "cameras": [],
                "sessions": [],
                "highlights": [],
                "director_mode": DirectorMode.HYBRID.value,
                "created_time": _now(),
                "metadata": dict(meta),
            }
            self._matches[match_id] = ctx
            self._director_modes[match_id] = DirectorMode.HYBRID.value

    def _seed_cameras(self) -> None:
        cameras = [
            # Grand final cameras.
            ("cam_overview_01", "match_grand_final", CameraMode.FREECAM,
             0, 60, 0, -90, 0, 75, "", 1.0),
            ("cam_player_focus_01", "match_grand_final", CameraMode.FOLLOW,
             12, 8, 14, -15, 25, 55, "player_alpha", 1.2),
            ("cam_objective_01", "match_grand_final", CameraMode.ORBITAL,
             30, 12, 30, -30, 45, 60, "objective_core", 0.8),
            ("cam_cinematic_01", "match_grand_final", CameraMode.CINEMATIC,
             -20, 5, -20, -10, 60, 50, "", 0.5),
            # Semifinal 1 cameras.
            ("cam_overview_02", "match_semifinal_1", CameraMode.FREECAM,
             0, 55, 0, -90, 0, 70, "", 1.0),
            ("cam_player_focus_02", "match_semifinal_1", CameraMode.FOLLOW,
             10, 7, 12, -12, 22, 55, "player_bravo", 1.1),
            ("cam_objective_02", "match_semifinal_1", CameraMode.ORBITAL,
             25, 10, 25, -25, 40, 58, "objective_shard", 0.8),
            ("cam_topdown_02", "match_semifinal_1", CameraMode.TOP_DOWN,
             0, 80, 0, -90, 0, 65, "", 1.0),
            # Semifinal 2 cameras.
            ("cam_overview_03", "match_semifinal_2", CameraMode.FREECAM,
             0, 58, 0, -90, 0, 72, "", 1.0),
            ("cam_player_focus_03", "match_semifinal_2", CameraMode.THIRD_PERSON,
             8, 6, 10, -10, 20, 60, "player_charlie", 1.3),
        ]
        for (
            camera_id,
            match_id,
            mode_enum,
            px,
            py,
            pz,
            rx,
            ry,
            fov,
            target,
            speed,
        ) in cameras:
            cam = CameraState(
                camera_id=camera_id,
                match_id=match_id,
                position_x=float(px),
                position_y=float(py),
                position_z=float(pz),
                rotation_x=float(rx),
                rotation_y=float(ry),
                rotation_z=0.0,
                fov=float(fov),
                mode=mode_enum.value,
                target_entity_id=target,
                speed=float(speed),
                metadata={"seeded": True},
            )
            self._cameras[camera_id] = cam
            self._matches[match_id]["cameras"].append(camera_id)

    def _seed_sessions(self) -> None:
        sessions = [
            ("spec_session_001", "spectator_001", "match_grand_final",
             ViewportLayout.SINGLE, "cam_overview_01"),
            ("spec_session_002", "spectator_002", "match_grand_final",
             ViewportLayout.PIP, "cam_player_focus_01"),
            ("spec_session_003", "spectator_003", "match_semifinal_1",
             ViewportLayout.SPLIT_HORIZONTAL, "cam_overview_02"),
            ("spec_session_004", "spectator_004", "match_semifinal_1",
             ViewportLayout.QUAD, "cam_player_focus_02"),
            ("spec_session_005", "spectator_005", "match_semifinal_2",
             ViewportLayout.SINGLE, "cam_player_focus_03"),
        ]
        for session_id, spectator_id, match_id, layout_enum, camera_id in sessions:
            sess = SpectatorSession(
                session_id=session_id,
                spectator_id=spectator_id,
                match_id=match_id,
                status=SpectatorStatus.OBSERVING.value,
                current_camera_id=camera_id,
                viewport_layout=layout_enum.value,
                metadata={"seeded": True},
            )
            self._sessions[session_id] = sess
            self._matches[match_id]["sessions"].append(session_id)
            self._ensure_session_viewports(session_id)

    def _seed_viewports(self) -> None:
        viewports = [
            ("viewport_001", "spec_session_001", ViewportLayout.SINGLE,
             "cam_overview_01", 0.0, 0.0, 1.0, 1.0, 1.0, True),
            ("viewport_002", "spec_session_002", ViewportLayout.PIP,
             "cam_player_focus_01", 0.6, 0.6, 0.35, 0.35, 0.9, False),
            ("viewport_003", "spec_session_002", ViewportLayout.PIP,
             "cam_cinematic_01", 0.0, 0.0, 1.0, 1.0, 1.0, True),
            ("viewport_004", "spec_session_003", ViewportLayout.SPLIT_HORIZONTAL,
             "cam_overview_02", 0.0, 0.0, 0.5, 1.0, 1.0, True),
            ("viewport_005", "spec_session_005", ViewportLayout.SINGLE,
             "cam_player_focus_03", 0.0, 0.0, 1.0, 1.0, 1.0, True),
        ]
        for (
            viewport_id,
            session_id,
            layout_enum,
            camera_id,
            px,
            py,
            w,
            h,
            opacity,
            primary,
        ) in viewports:
            vp = ViewportConfig(
                viewport_id=viewport_id,
                session_id=session_id,
                layout=layout_enum.value,
                camera_id=camera_id,
                position_x=float(px),
                position_y=float(py),
                width=float(w),
                height=float(h),
                opacity=float(opacity),
                is_primary=bool(primary),
                metadata={"seeded": True},
            )
            self._viewports[viewport_id] = vp
            self._ensure_session_viewports(session_id).append(viewport_id)

    def _seed_presets(self) -> None:
        presets = [
            ("preset_overview", "Overview", CameraMode.FREECAM,
             0, 60, 0, -90, 0, 75, TransitionType.PAN, 1.2),
            ("preset_player_follow", "Player Follow", CameraMode.FOLLOW,
             12, 8, 14, -15, 25, 55, TransitionType.DISSOLVE, 0.6),
            ("preset_objective", "Objective View", CameraMode.ORBITAL,
             30, 12, 30, -30, 45, 60, TransitionType.ZOOM, 0.8),
            ("preset_cinematic_intro", "Cinematic Intro", CameraMode.CINEMATIC,
             -20, 5, -20, -10, 60, 50, TransitionType.FADE, 2.0),
            ("preset_replay_angle", "Replay Angle", CameraMode.THIRD_PERSON,
             8, 6, 10, -10, 20, 60, TransitionType.WIPE, 0.5),
            ("preset_default", "Spectator Default", CameraMode.THIRD_PERSON,
             10, 7, 12, -12, 22, 58, TransitionType.CUT, 0.4),
        ]
        for (
            preset_id,
            name,
            mode_enum,
            px,
            py,
            pz,
            rx,
            ry,
            fov,
            trans_enum,
            trans_dur,
        ) in presets:
            preset = CameraPresetConfig(
                preset_id=preset_id,
                name=name,
                camera_mode=mode_enum.value,
                position_x=float(px),
                position_y=float(py),
                position_z=float(pz),
                rotation_x=float(rx),
                rotation_y=float(ry),
                fov=float(fov),
                transition_type=trans_enum.value,
                transition_duration=float(trans_dur),
                metadata={"seeded": True},
            )
            self._presets[preset_id] = preset

    def _seed_highlights(self) -> None:
        highlights = [
            ("highlight_ace_001", "match_grand_final", HighlightType.ACE,
             "Quad kill secured by player_alpha on the grand final stage.",
             12.0, 0.95, ["player_alpha", "player_delta", "player_echo"]),
            ("highlight_clutch_001", "match_grand_final", HighlightType.CLUTCH,
             "1v3 clutch defended the objective core in the final minute.",
             8.0, 0.88, ["player_bravo"]),
            ("highlight_teamfight_001", "match_semifinal_1", HighlightType.TEAMFIGHT,
             "Extended teamfight around the shard objective.",
             15.0, 0.72, ["player_bravo", "player_foxtrot"]),
            ("highlight_objective_001", "match_semifinal_1", HighlightType.OBJECTIVE,
             "Shard objective captured after a coordinated push.",
             6.0, 0.65, ["player_bravo"]),
            ("highlight_comeback_001", "match_semifinal_2", HighlightType.COMEBACK,
             "Down two rounds, the underdog roster tied the series.",
             10.0, 0.81, ["player_charlie"]),
        ]
        for (
            highlight_id,
            match_id,
            type_enum,
            description,
            duration,
            importance,
            entities,
        ) in highlights:
            hl = HighlightMoment(
                highlight_id=highlight_id,
                match_id=match_id,
                timestamp=_now(),
                highlight_type=type_enum.value,
                description=description,
                camera_state_json="{}",
                duration=float(duration),
                importance_score=float(importance),
                entity_ids=list(entities),
                metadata={"seeded": True},
            )
            self._highlights[highlight_id] = hl
            self._matches[match_id]["highlights"].append(highlight_id)

    def _seed_director_decisions(self) -> None:
        decisions = [
            ("decision_001", "match_grand_final", "cam_player_focus_01",
             "player_alpha", "highlight ace detected", 0.92),
            ("decision_002", "match_grand_final", "cam_cinematic_01",
             "", "cinematic break between rounds", 0.6),
            ("decision_003", "match_semifinal_1", "cam_player_focus_02",
             "player_bravo", "engagement started near shard", 0.78),
            ("decision_004", "match_semifinal_1", "cam_objective_02",
             "objective_shard", "objective capture in progress", 0.83),
            ("decision_005", "match_semifinal_2", "cam_player_focus_03",
             "player_charlie", "comeback sequence detected", 0.86),
        ]
        for (
            decision_id,
            match_id,
            target_cam,
            target_entity,
            reason,
            confidence,
        ) in decisions:
            decision = DirectorDecision(
                decision_id=decision_id,
                match_id=match_id,
                timestamp=_now(),
                action_type="switch_camera",
                target_camera_id=target_cam,
                target_entity_id=target_entity,
                reason=reason,
                confidence=float(confidence),
                metadata={"seeded": True},
            )
            self._director_decisions.append(decision)


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------


def get_spectator_director_system() -> SpectatorDirectorSystem:
    """Factory function returning the singleton SpectatorDirectorSystem."""
    return SpectatorDirectorSystem.get_instance()


__all__ = [
    # Enums
    "CameraMode",
    "DirectorMode",
    "SpectatorStatus",
    "ViewportLayout",
    "HighlightType",
    "CameraPreset",
    "TransitionType",
    # Data classes
    "CameraState",
    "SpectatorSession",
    "ViewportConfig",
    "CameraPresetConfig",
    "HighlightMoment",
    "DirectorDecision",
    "SpectatorConfig",
    "SpectatorStats",
    "SpectatorSnapshot",
    "SpectatorEvent",
    # System
    "SpectatorDirectorSystem",
    "get_spectator_director_system",
]
