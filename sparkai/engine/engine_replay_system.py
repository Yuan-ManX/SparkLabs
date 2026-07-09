"""
SparkLabs Engine - Replay System

A gameplay recording and playback system for the SparkLabs AI-native game
engine. Captures entity transforms, input events, and game state snapshots
into replay buffers that can be scrubbed, played back, exported, and
spectated. Supports highlight marking, timeline navigation, multi-camera
playback, and deterministic reproduction of recorded sessions.

Each replay recording stores a sequence of keyframes (entity positions,
rotations, velocities) and input events (button presses, analog sticks,
touch gestures) sampled at a configurable capture rate. Designed for
esports replay systems, content creation tools, anti-cheat verification,
and gameplay analysis.

Architecture:
  ReplaySystem (singleton)
    |-- ReplayState, ReplayEventKind, HighlightType
    |-- EntityKeyframe, InputEvent, ReplayRecording, HighlightMarker,
       ReplayPlayback, ReplayConfig, ReplayStats, ReplaySnapshot,
       ReplayEvent
    |-- get_replay_system

Core Capabilities:
  - start_recording / stop_recording / pause_recording / resume_recording:
    control live gameplay capture into a replay buffer.
  - get_recording / list_recordings / remove_recording: manage stored
    replay recordings.
  - add_keyframe / add_input_event: inject captured data points during
    recording.
  - start_playback / stop_playback / seek_playback / set_playback_speed:
    control replay playback with timeline scrubbing and speed adjustment.
  - get_playback / get_playback_state: retrieve current playback position
    and state.
  - add_highlight / remove_highlight / list_highlights: mark and manage
    highlight moments within a recording.
  - tick: advance recording capture and playback simulation.
  - set_config / get_config: global tuning for max recordings, capture
    rate, and buffer sizes.
  - list_events / get_stats / get_status / get_snapshot / reset:
    observability and state management.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`ReplaySystem.get_instance` or the module-level
:func:`get_replay_system` factory.
"""

from __future__ import annotations

import math
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_RECORDINGS: int = 100
_MAX_KEYFRAMES_PER_RECORDING: int = 50000
_MAX_INPUT_EVENTS_PER_RECORDING: int = 50000
_MAX_HIGHLIGHTS_PER_RECORDING: int = 200
_MAX_EVENTS: int = 5000


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    return time.time()


def _new_id(prefix: str = "") -> str:
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


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


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    if hasattr(obj, "__dataclass_fields__"):
        result: Dict[str, Any] = {}
        for k in obj.__dataclass_fields__:
            v = getattr(obj, k)
            if hasattr(v, "to_dict") and callable(v.to_dict):
                result[k] = v.to_dict()
            elif isinstance(v, list):
                result[k] = [_dataclass_to_dict(i) for i in v]
            elif isinstance(v, dict):
                result[k] = {kk: _dataclass_to_dict(vv) for kk, vv in v.items()}
            elif isinstance(v, tuple):
                result[k] = list(v)
            else:
                result[k] = v
        return result
    return obj


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ReplayState(str, Enum):
    """State of a recording or playback session."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PLAYING = "playing"
    STOPPED = "stopped"
    COMPLETED = "completed"
    ERROR = "error"


class HighlightType(str, Enum):
    """Type of highlight marker."""
    KILL = "kill"
    DEATH = "death"
    OBJECTIVE = "objective"
    SKILL = "skill"
    INTERACTION = "interaction"
    CUSTOM = "custom"


class ReplayEventKind(str, Enum):
    """Audit event types emitted by the replay system."""
    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    RECORDING_PAUSED = "recording_paused"
    RECORDING_RESUMED = "recording_resumed"
    KEYFRAME_ADDED = "keyframe_added"
    INPUT_EVENT_ADDED = "input_event_added"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_STOPPED = "playback_stopped"
    PLAYBACK_SEEKED = "playback_seeked"
    PLAYBACK_SPEED_CHANGED = "playback_speed_changed"
    HIGHLIGHT_ADDED = "highlight_added"
    HIGHLIGHT_REMOVED = "highlight_removed"
    RECORDING_REMOVED = "recording_removed"
    CONFIG_UPDATED = "config_updated"
    RESET = "reset"
    TICK = "tick"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class EntityKeyframe:
    """A captured entity state at a specific timestamp."""
    timestamp: float
    entity_id: str
    position: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation: Tuple[float, float, float, float] = (0.0, 0.0, 0.0, 1.0)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    scale: Tuple[float, float, float] = (1.0, 1.0, 1.0)
    animation_state: str = ""
    health: float = 100.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InputEvent:
    """A captured player input event."""
    timestamp: float
    player_id: str
    input_type: str = "button"
    action: str = ""
    value: float = 0.0
    duration: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class HighlightMarker:
    """A marked highlight moment within a recording."""
    highlight_id: str
    timestamp: float
    duration: float = 5.0
    highlight_type: str = HighlightType.CUSTOM.value
    label: str = ""
    entity_id: str = ""
    player_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayRecording:
    """A stored gameplay replay recording."""
    recording_id: str
    name: str = ""
    map_id: str = ""
    game_mode: str = ""
    player_ids: List[str] = field(default_factory=list)
    state: str = ReplayState.IDLE.value
    keyframes: List[EntityKeyframe] = field(default_factory=list)
    input_events: List[InputEvent] = field(default_factory=list)
    highlights: List[HighlightMarker] = field(default_factory=list)
    capture_rate_hz: float = 30.0
    duration: float = 0.0
    current_time: float = 0.0
    file_size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_now)
    updated_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayPlayback:
    """State of an active playback session."""
    playback_id: str
    recording_id: str
    state: str = ReplayState.IDLE.value
    current_time: float = 0.0
    playback_speed: float = 1.0
    loop: bool = False
    camera_entity_id: str = ""
    spectator_id: str = ""
    started_at: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayConfig:
    """Global tuning parameters for the replay system."""
    max_recordings: int = 50
    max_keyframes_per_recording: int = 30000
    max_input_events_per_recording: int = 30000
    default_capture_rate_hz: float = 30.0
    max_playback_speed: float = 8.0
    min_playback_speed: float = 0.1
    auto_stop_on_disconnect: bool = True
    compress_keyframes: bool = True
    tick_rate_hz: float = 30.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayStats:
    """Aggregate statistics for the replay system."""
    total_recordings: int = 0
    active_recordings: int = 0
    total_playbacks: int = 0
    active_playbacks: int = 0
    total_keyframes: int = 0
    total_input_events: int = 0
    total_highlights: int = 0
    total_recording_time: float = 0.0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplaySnapshot:
    """Full state snapshot of the replay system."""
    recordings: List[Dict[str, Any]] = field(default_factory=list)
    active_playbacks: List[Dict[str, Any]] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    tick_count: int = 0
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayEvent:
    """An audit event emitted by the replay system."""
    event_id: str
    kind: str
    timestamp: float
    recording_id: Optional[str] = None
    playback_id: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Replay System
# ---------------------------------------------------------------------------

class ReplaySystem:
    """Manages gameplay recording, playback, and highlight tracking."""

    _instance: Optional["ReplaySystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        self._recordings: Dict[str, ReplayRecording] = {}
        self._playbacks: Dict[str, ReplayPlayback] = {}
        self._active_recording_id: Optional[str] = None
        self._events: List[ReplayEvent] = []
        self._stats = ReplayStats()
        self._config = ReplayConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._playback_counter: int = 0
        self._highlight_counter: int = 0
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    @classmethod
    def get_instance(cls) -> "ReplaySystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Seed a sample completed recording."""
        recording = ReplayRecording(
            recording_id="replay_demo_01",
            name="Demo Match - Crystal Arena",
            map_id="map_crystal_arena",
            game_mode="team_deathmatch",
            player_ids=["player_01", "player_02", "player_03", "player_04"],
            state=ReplayState.COMPLETED.value,
            capture_rate_hz=30.0,
            duration=180.0,
            current_time=0.0,
        )
        for i in range(10):
            ts = float(i) * 0.033
            recording.keyframes.append(EntityKeyframe(
                timestamp=ts,
                entity_id="player_01",
                position=(float(i), 0.0, float(i)),
                velocity=(1.0, 0.0, 1.0),
                health=100.0 - float(i) * 5,
            ))
        recording.input_events.append(InputEvent(
            timestamp=1.0,
            player_id="player_01",
            input_type="button",
            action="fire",
            value=1.0,
        ))
        recording.highlights.append(HighlightMarker(
            highlight_id="hl_0",
            timestamp=5.0,
            duration=3.0,
            highlight_type=HighlightType.KILL.value,
            label="First Blood",
            entity_id="player_01",
            player_id="player_01",
        ))
        recording.file_size_bytes = len(recording.keyframes) * 128
        self._recordings[recording.recording_id] = recording
        self._stats.total_recordings = 1
        self._stats.total_keyframes = len(recording.keyframes)
        self._stats.total_input_events = len(recording.input_events)
        self._stats.total_highlights = len(recording.highlights)
        self._stats.total_recording_time = recording.duration
        self._initialized = True

    # ------------------------------------------------------------------
    # Recording Management
    # ------------------------------------------------------------------

    def start_recording(self, name: str = "", map_id: str = "", game_mode: str = "",
                        player_ids: Optional[List[str]] = None,
                        capture_rate_hz: Optional[float] = None) -> Dict[str, Any]:
        if self._active_recording_id is not None:
            return {"success": False, "reason": "already_recording",
                    "active_recording_id": self._active_recording_id}
        recording_id = f"replay_{_new_id()}"
        rate = capture_rate_hz if capture_rate_hz else self._config.default_capture_rate_hz
        recording = ReplayRecording(
            recording_id=recording_id,
            name=name or f"Recording {recording_id}",
            map_id=map_id,
            game_mode=game_mode,
            player_ids=player_ids or [],
            state=ReplayState.RECORDING.value,
            capture_rate_hz=rate,
        )
        if len(self._recordings) >= _MAX_RECORDINGS:
            oldest = next(iter(self._recordings), None)
            if oldest:
                self._recordings.pop(oldest, None)
        self._recordings[recording_id] = recording
        self._active_recording_id = recording_id
        self._stats.total_recordings = len(self._recordings)
        self._stats.active_recordings = 1
        self._record_event(ReplayEventKind.RECORDING_STARTED, recording_id=recording_id,
                           details={"name": name, "map_id": map_id, "rate": rate})
        return {"success": True, "recording_id": recording_id}

    def stop_recording(self) -> Dict[str, Any]:
        if self._active_recording_id is None:
            return {"success": False, "reason": "not_recording"}
        recording = self._recordings.get(self._active_recording_id)
        if recording is None:
            self._active_recording_id = None
            return {"success": False, "reason": "recording_not_found"}
        recording.state = ReplayState.STOPPED.value
        recording.duration = recording.current_time
        recording.updated_at = _now()
        self._stats.total_recording_time += recording.duration
        self._stats.active_recordings = 0
        self._record_event(ReplayEventKind.RECORDING_STOPPED, recording_id=recording.recording_id,
                           details={"duration": recording.duration,
                                     "keyframes": len(recording.keyframes),
                                     "input_events": len(recording.input_events)})
        self._active_recording_id = None
        return {"success": True, "recording_id": recording.recording_id,
                "duration": recording.duration,
                "keyframe_count": len(recording.keyframes),
                "input_event_count": len(recording.input_events)}

    def pause_recording(self) -> Dict[str, Any]:
        if self._active_recording_id is None:
            return {"success": False, "reason": "not_recording"}
        recording = self._recordings.get(self._active_recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        recording.state = ReplayState.PAUSED.value
        self._record_event(ReplayEventKind.RECORDING_PAUSED, recording_id=recording.recording_id)
        return {"success": True, "recording_id": recording.recording_id, "state": recording.state}

    def resume_recording(self) -> Dict[str, Any]:
        if self._active_recording_id is None:
            return {"success": False, "reason": "not_recording"}
        recording = self._recordings.get(self._active_recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        recording.state = ReplayState.RECORDING.value
        self._record_event(ReplayEventKind.RECORDING_RESUMED, recording_id=recording.recording_id)
        return {"success": True, "recording_id": recording.recording_id, "state": recording.state}

    def get_recording(self, recording_id: str) -> Optional[ReplayRecording]:
        return self._recordings.get(recording_id)

    def list_recordings(self, map_id: Optional[str] = None, game_mode: Optional[str] = None,
                        limit: int = 100) -> List[ReplayRecording]:
        result = []
        for r in self._recordings.values():
            if map_id is not None and r.map_id != map_id:
                continue
            if game_mode is not None and r.game_mode != game_mode:
                continue
            result.append(r)
        return result[:limit]

    def remove_recording(self, recording_id: str) -> Dict[str, Any]:
        recording = self._recordings.pop(recording_id, None)
        if recording is None:
            return {"recording_id": recording_id, "removed": False}
        if self._active_recording_id == recording_id:
            self._active_recording_id = None
            self._stats.active_recordings = 0
        self._stats.total_recordings = len(self._recordings)
        self._record_event(ReplayEventKind.RECORDING_REMOVED, recording_id=recording_id)
        return {"recording_id": recording_id, "removed": True}

    # ------------------------------------------------------------------
    # Keyframe and Input Event Capture
    # ------------------------------------------------------------------

    def add_keyframe(self, keyframe: EntityKeyframe) -> Dict[str, Any]:
        if self._active_recording_id is None:
            return {"success": False, "reason": "not_recording"}
        recording = self._recordings.get(self._active_recording_id)
        if recording is None or recording.state != ReplayState.RECORDING.value:
            return {"success": False, "reason": "not_recording"}
        if len(recording.keyframes) >= _MAX_KEYFRAMES_PER_RECORDING:
            _evict_fifo_list(recording.keyframes, _MAX_KEYFRAMES_PER_RECORDING)
        recording.keyframes.append(keyframe)
        recording.current_time = max(recording.current_time, keyframe.timestamp)
        self._stats.total_keyframes += 1
        return {"success": True, "keyframe_count": len(recording.keyframes)}

    def add_input_event(self, event: InputEvent) -> Dict[str, Any]:
        if self._active_recording_id is None:
            return {"success": False, "reason": "not_recording"}
        recording = self._recordings.get(self._active_recording_id)
        if recording is None or recording.state != ReplayState.RECORDING.value:
            return {"success": False, "reason": "not_recording"}
        if len(recording.input_events) >= _MAX_INPUT_EVENTS_PER_RECORDING:
            _evict_fifo_list(recording.input_events, _MAX_INPUT_EVENTS_PER_RECORDING)
        recording.input_events.append(event)
        self._stats.total_input_events += 1
        return {"success": True, "input_event_count": len(recording.input_events)}

    # ------------------------------------------------------------------
    # Highlight Management
    # ------------------------------------------------------------------

    def add_highlight(self, recording_id: str, timestamp: float, highlight_type: str = HighlightType.CUSTOM.value,
                      label: str = "", duration: float = 5.0, entity_id: str = "",
                      player_id: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        recording = self._recordings.get(recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        highlight_id = f"hl_{self._highlight_counter}"
        self._highlight_counter += 1
        highlight = HighlightMarker(
            highlight_id=highlight_id,
            timestamp=timestamp,
            duration=duration,
            highlight_type=highlight_type,
            label=label,
            entity_id=entity_id,
            player_id=player_id,
            metadata=metadata or {},
        )
        if len(recording.highlights) >= _MAX_HIGHLIGHTS_PER_RECORDING:
            _evict_fifo_list(recording.highlights, _MAX_HIGHLIGHTS_PER_RECORDING)
        recording.highlights.append(highlight)
        recording.updated_at = _now()
        self._stats.total_highlights += 1
        self._record_event(ReplayEventKind.HIGHLIGHT_ADDED, recording_id=recording_id,
                           details={"highlight_id": highlight_id, "timestamp": timestamp, "type": highlight_type})
        return {"success": True, "highlight_id": highlight_id}

    def remove_highlight(self, recording_id: str, highlight_id: str) -> Dict[str, Any]:
        recording = self._recordings.get(recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        original_len = len(recording.highlights)
        recording.highlights = [h for h in recording.highlights if h.highlight_id != highlight_id]
        if len(recording.highlights) < original_len:
            self._stats.total_highlights = max(0, self._stats.total_highlights - 1)
            self._record_event(ReplayEventKind.HIGHLIGHT_REMOVED, recording_id=recording_id,
                               details={"highlight_id": highlight_id})
            return {"success": True, "highlight_id": highlight_id, "removed": True}
        return {"success": False, "reason": "highlight_not_found"}

    def list_highlights(self, recording_id: str, highlight_type: Optional[str] = None,
                        limit: int = 100) -> List[HighlightMarker]:
        recording = self._recordings.get(recording_id)
        if recording is None:
            return []
        result = []
        for h in recording.highlights:
            if highlight_type is not None and h.highlight_type != highlight_type:
                continue
            result.append(h)
        return result[:limit]

    # ------------------------------------------------------------------
    # Playback Control
    # ------------------------------------------------------------------

    def start_playback(self, recording_id: str, spectator_id: str = "",
                       camera_entity_id: str = "", playback_speed: float = 1.0,
                       loop: bool = False) -> Dict[str, Any]:
        recording = self._recordings.get(recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        if recording.duration <= 0:
            return {"success": False, "reason": "empty_recording"}
        playback_id = f"play_{self._playback_counter}"
        self._playback_counter += 1
        speed = _clamp(playback_speed, self._config.min_playback_speed, self._config.max_playback_speed)
        playback = ReplayPlayback(
            playback_id=playback_id,
            recording_id=recording_id,
            state=ReplayState.PLAYING.value,
            current_time=0.0,
            playback_speed=speed,
            loop=loop,
            camera_entity_id=camera_entity_id,
            spectator_id=spectator_id,
        )
        self._playbacks[playback_id] = playback
        self._stats.total_playbacks += 1
        self._stats.active_playbacks += 1
        self._record_event(ReplayEventKind.PLAYBACK_STARTED, recording_id=recording_id,
                           playback_id=playback_id,
                           details={"speed": speed, "loop": loop})
        return {"success": True, "playback_id": playback_id}

    def stop_playback(self, playback_id: str) -> Dict[str, Any]:
        playback = self._playbacks.pop(playback_id, None)
        if playback is None:
            return {"success": False, "reason": "playback_not_found"}
        playback.state = ReplayState.STOPPED.value
        self._stats.active_playbacks = max(0, self._stats.active_playbacks - 1)
        self._record_event(ReplayEventKind.PLAYBACK_STOPPED, recording_id=playback.recording_id,
                           playback_id=playback_id)
        return {"success": True, "playback_id": playback_id}

    def seek_playback(self, playback_id: str, timestamp: float) -> Dict[str, Any]:
        playback = self._playbacks.get(playback_id)
        if playback is None:
            return {"success": False, "reason": "playback_not_found"}
        recording = self._recordings.get(playback.recording_id)
        if recording is None:
            return {"success": False, "reason": "recording_not_found"}
        playback.current_time = _clamp(timestamp, 0.0, recording.duration)
        self._record_event(ReplayEventKind.PLAYBACK_SEEKED, recording_id=playback.recording_id,
                           playback_id=playback_id, details={"timestamp": playback.current_time})
        return {"success": True, "playback_id": playback_id, "current_time": playback.current_time}

    def set_playback_speed(self, playback_id: str, speed: float) -> Dict[str, Any]:
        playback = self._playbacks.get(playback_id)
        if playback is None:
            return {"success": False, "reason": "playback_not_found"}
        playback.playback_speed = _clamp(speed, self._config.min_playback_speed, self._config.max_playback_speed)
        self._record_event(ReplayEventKind.PLAYBACK_SPEED_CHANGED, recording_id=playback.recording_id,
                           playback_id=playback_id, details={"speed": playback.playback_speed})
        return {"success": True, "playback_id": playback_id, "speed": playback.playback_speed}

    def get_playback(self, playback_id: str) -> Optional[ReplayPlayback]:
        return self._playbacks.get(playback_id)

    def get_playback_state(self, playback_id: str) -> Dict[str, Any]:
        playback = self._playbacks.get(playback_id)
        if playback is None:
            return {"found": False}
        recording = self._recordings.get(playback.recording_id)
        duration = recording.duration if recording else 0.0
        return {
            "found": True,
            "playback_id": playback.playback_id,
            "recording_id": playback.recording_id,
            "state": playback.state,
            "current_time": playback.current_time,
            "duration": duration,
            "progress": (playback.current_time / duration) if duration > 0 else 0.0,
            "playback_speed": playback.playback_speed,
            "loop": playback.loop,
        }

    # ------------------------------------------------------------------
    # Simulation
    # ------------------------------------------------------------------

    def tick(self, delta_time: float = 0.033) -> Dict[str, Any]:
        self._tick_count += 1
        self._stats.tick_count = self._tick_count
        completed_playbacks = []
        for playback_id, playback in list(self._playbacks.items()):
            if playback.state != ReplayState.PLAYING.value:
                continue
            recording = self._recordings.get(playback.recording_id)
            if recording is None:
                continue
            playback.current_time += delta_time * playback.playback_speed
            if playback.current_time >= recording.duration:
                if playback.loop:
                    playback.current_time = 0.0
                else:
                    playback.current_time = recording.duration
                    playback.state = ReplayState.COMPLETED.value
                    completed_playbacks.append(playback_id)
                    self._stats.active_playbacks = max(0, self._stats.active_playbacks - 1)
        return {"tick_count": self._tick_count, "completed_playbacks": completed_playbacks}

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def get_config(self) -> ReplayConfig:
        return self._config

    def set_config(self, config: ReplayConfig) -> Dict[str, Any]:
        self._config = config
        self._record_event(ReplayEventKind.CONFIG_UPDATED)
        return {"updated": True}

    # ------------------------------------------------------------------
    # Observability
    # ------------------------------------------------------------------

    def _record_event(self, kind: ReplayEventKind, recording_id: Optional[str] = None,
                      playback_id: Optional[str] = None, details: Optional[Dict[str, Any]] = None) -> None:
        event_id = f"evt_{self._event_counter}"
        self._event_counter += 1
        event = ReplayEvent(
            event_id=event_id,
            kind=kind.value,
            timestamp=_now(),
            recording_id=recording_id,
            playback_id=playback_id,
            details=details or {},
        )
        self._events.append(event)
        _evict_fifo_list(self._events, _MAX_EVENTS)

    def list_events(self, recording_id: Optional[str] = None, playback_id: Optional[str] = None,
                    kind: Optional[str] = None, limit: int = 100) -> List[ReplayEvent]:
        result = []
        for e in reversed(self._events):
            if recording_id is not None and e.recording_id != recording_id:
                continue
            if playback_id is not None and e.playback_id != playback_id:
                continue
            if kind is not None and e.kind != kind:
                continue
            result.append(e)
            if len(result) >= limit:
                break
        return result

    def get_stats(self) -> ReplayStats:
        return self._stats

    def get_status(self) -> Dict[str, Any]:
        return {
            "initialized": self._initialized,
            "total_recordings": len(self._recordings),
            "active_recording": self._active_recording_id is not None,
            "active_playbacks": self._stats.active_playbacks,
            "total_keyframes": self._stats.total_keyframes,
            "total_input_events": self._stats.total_input_events,
            "total_highlights": self._stats.total_highlights,
            "tick_count": self._tick_count,
        }

    def get_snapshot(self) -> ReplaySnapshot:
        return ReplaySnapshot(
            recordings=[{"recording_id": r.recording_id, "name": r.name, "state": r.state,
                          "duration": r.duration, "keyframe_count": len(r.keyframes),
                          "highlight_count": len(r.highlights)}
                         for r in self._recordings.values()],
            active_playbacks=[p.to_dict() for p in self._playbacks.values()],
            stats=self._stats.to_dict(),
            config=self._config.to_dict(),
            tick_count=self._tick_count,
        )

    def reset(self) -> Dict[str, Any]:
        with self._init_lock:
            self._recordings.clear()
            self._playbacks.clear()
            self._active_recording_id = None
            self._events.clear()
            self._stats = ReplayStats()
            self._config = ReplayConfig()
            self._tick_count = 0
            self._event_counter = 0
            self._playback_counter = 0
            self._highlight_counter = 0
            self._initialized = False
            self._seed()
        self._record_event(ReplayEventKind.RESET)
        return {"reset": True, "initialized": self._initialized}


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_replay_system() -> ReplaySystem:
    return ReplaySystem.get_instance()
