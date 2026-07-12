"""
SparkLabs Engine - Input Replay System

A deterministic input replay system for the SparkLabs AI-native game engine.
Captures player inputs (keyboard, mouse, gamepad, touch, motion, voice,
gesture) frame-by-frame with precise timestamps so that gameplay sessions
can be exactly replayed. Designed for debugging, automated testing, and
competitive multiplayer validation where frame-perfect input reproduction
is required.

The system pairs every recorded input frame with an optional checksum of
the surrounding game state. During playback each frame is verified against
the stored checksum so that divergences (desyncs) between the recorded
session and the live simulation are detected immediately. Detected desyncs
can be logged, corrected by resetting to the expected state, or surfaced
to anti-cheat and validation pipelines.

Architecture:
  InputReplaySystem (singleton)
    |-- InputType, InputAction, RecordingStatus, PlaybackStatus,
       ReplayMode, ChecksumType, ReplayEventKind, FrameStatus
    |-- InputFrame, InputSequence, PlaybackState, Checksum, DesyncReport,
       FrameSnapshot, RecordingSession, InputReplayConfig, InputReplayStats,
       InputReplaySnapshot, ReplayEvent
    |-- get_input_replay_system

Core Capabilities:
  - start_recording / stop_recording / pause_recording / resume_recording:
    control live input capture into a recording buffer.
  - record_input: capture a single input event with frame index, timestamp
    and optional state hash for deterministic verification.
  - save_sequence / load_sequence / delete_sequence / get_sequence /
    list_sequences / export_sequence / import_sequence: manage stored input
    sequences and serialize them for transfer.
  - start_playback / pause_playback / resume_playback / stop_playback /
    advance_frame / seek_to_frame / set_playback_speed: drive deterministic
    playback with frame stepping, seeking and speed control.
  - compute_checksum / verify_checksum / detect_desync / correct_desync:
    verify frame-level determinism and recover from divergences.
  - get_frame / get_frame_range / get_frame_count / get_frame_snapshot:
    inspect recorded frames.
  - compare_sequences / analyze_input_pattern / get_input_statistics /
    suggest_optimal_inputs: analyze captured inputs and produce insights.
  - tick: advance recording capture and playback simulation each step.
  - set_config / get_config / get_status / get_stats / get_snapshot /
    list_events: observability and tuning.

The class implements the singleton pattern with double-checked locking
using ``threading.RLock``; consumers should obtain the instance through
:meth:`InputReplaySystem.get_instance` or the module-level
:func:`get_input_replay_system` factory.
"""

from __future__ import annotations

import copy
import hashlib
import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Capacity Constants
# ---------------------------------------------------------------------------

_MAX_SEQUENCES: int = 200
_MAX_FRAMES_PER_SEQUENCE: int = 100000
_MAX_EVENTS: int = 5000
_MAX_DESYNC_REPORTS: int = 1000
_DEFAULT_FRAME_RATE_HZ: float = 60.0
_MAX_PLAYBACK_SPEED: float = 16.0
_MIN_PLAYBACK_SPEED: float = 0.0625
_FRAME_STEP_SECONDS: float = 1.0 / _DEFAULT_FRAME_RATE_HZ


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def _now() -> float:
    """Return the current monotonic-flavored wall-clock time in seconds."""
    return time.time()


def _new_id(prefix: str = "") -> str:
    """Generate a short unique identifier with an optional prefix."""
    base = uuid.uuid4().hex[:12]
    return f"{prefix}_{base}" if prefix else base


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Coerce a value to float, falling back to ``default`` on failure."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    """Coerce a value to int, falling back to ``default`` on failure."""
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp ``value`` to the inclusive range ``[lo, hi]``."""
    return max(lo, min(hi, value))


def _evict_fifo_list(store: List[Any], max_size: int) -> None:
    """Trim a list to ``max_size`` by dropping the oldest entries first."""
    cap = max(1, int(max_size))
    while len(store) > cap:
        if not store:
            break
        store.pop(0)


def _dataclass_to_dict(obj: Any) -> Dict[str, Any]:
    """Recursively convert a dataclass instance into a plain dict."""
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


def _hash_payload(payload: Any) -> str:
    """Produce a stable SHA-256 hex digest for a JSON-serializable payload."""
    try:
        serialized = json.dumps(payload, sort_keys=True, default=str)
    except (TypeError, ValueError):
        serialized = str(payload)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _hash_state(state: Optional[Dict[str, Any]]) -> str:
    """Hash a game-state dict; returns an empty string when state is absent."""
    if not state:
        return ""
    return _hash_payload(state)


def _frame_signature(frame: "InputFrame") -> Dict[str, Any]:
    """Build the deterministic payload used to hash a single input frame."""
    return {
        "frame_index": int(frame.frame_index),
        "input_type": str(frame.input_type),
        "action": str(frame.action),
        "key_code": int(frame.key_code),
        "position": [float(frame.position[0]), float(frame.position[1])],
        "delta": [float(frame.delta[0]), float(frame.delta[1])],
        "duration": float(frame.duration),
        "player_id": str(frame.player_id),
    }


def _hash_input_frame(frame: Optional["InputFrame"]) -> str:
    """Hash the deterministic portion of an input frame."""
    if frame is None:
        return ""
    return _hash_payload(_frame_signature(frame))


def _normalize_enum(value: Any, enum_cls: type) -> str:
    """Accept either an enum member or its string value and return the value."""
    if isinstance(value, enum_cls):
        return value.value
    if isinstance(value, str):
        # Allow matching by name or value
        for member in enum_cls:
            if member.value == value or member.name == value:
                return member.value
        return value
    if value is None:
        return enum_cls.__members__[list(enum_cls)[0].name].value
    return str(value)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class InputType(str, Enum):
    """Categories of physical or virtual input sources."""

    KEYBOARD = "keyboard"
    MOUSE = "mouse"
    GAMEPAD = "gamepad"
    TOUCH = "touch"
    MOTION = "motion"
    VOICE = "voice"
    GESTURE = "gesture"


class InputAction(str, Enum):
    """Discrete actions that can be performed on an input source."""

    PRESS = "press"
    RELEASE = "release"
    HOLD = "hold"
    MOVE = "move"
    SCROLL = "scroll"
    TAP = "tap"
    DRAG = "drag"
    PINCH = "pinch"
    ROTATE = "rotate"


class RecordingStatus(str, Enum):
    """Lifecycle state of a recording session."""

    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"
    SAVED = "saved"


class PlaybackStatus(str, Enum):
    """Lifecycle state of a playback session."""

    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class ReplayMode(str, Enum):
    """Determinism contract for a replay session."""

    DETERMINISTIC = "deterministic"
    NON_DETERMINISTIC = "non_deterministic"
    SYNCED = "synced"
    ASYNC = "async"


class ChecksumType(str, Enum):
    """Which portion of frame state a checksum covers."""

    STATE_HASH = "state_hash"
    FRAME_HASH = "frame_hash"
    INPUT_HASH = "input_hash"
    COMBINED = "combined"


class ReplayEventKind(str, Enum):
    """Audit event kinds emitted by the input replay system."""

    RECORDING_STARTED = "recording_started"
    RECORDING_STOPPED = "recording_stopped"
    INPUT_RECORDED = "input_recorded"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_COMPLETED = "playback_completed"
    PLAYBACK_FAILED = "playback_failed"
    DESYNC_DETECTED = "desync_detected"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    FRAME_ADVANCED = "frame_advanced"


class FrameStatus(str, Enum):
    """Verification outcome for a single replayed frame."""

    SYNCED = "synced"
    DESYNCED = "desynced"
    SKIPPED = "skipped"
    CORRECTED = "corrected"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class InputFrame:
    """A single captured input event at a specific frame index and time."""

    frame_index: int
    timestamp: float
    input_type: str = InputType.KEYBOARD.value
    action: str = InputAction.PRESS.value
    key_code: int = 0
    position: Tuple[float, float] = (0.0, 0.0)
    delta: Tuple[float, float] = (0.0, 0.0)
    duration: float = 0.0
    player_id: str = "player_01"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InputSequence:
    """A stored sequence of input frames captured during a session."""

    sequence_id: str
    name: str = ""
    frames: List[InputFrame] = field(default_factory=list)
    total_frames: int = 0
    duration: float = 0.0
    recording_started_at: float = 0.0
    recording_stopped_at: float = 0.0
    player_id: str = "player_01"
    game_state_hash: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class PlaybackState:
    """State of an active playback session over a stored sequence."""

    sequence_id: str
    current_frame: int = 0
    status: str = PlaybackStatus.IDLE.value
    speed_multiplier: float = 1.0
    loop: bool = False
    start_frame: int = 0
    end_frame: int = -1

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class Checksum:
    """Per-frame checksum bundle used for deterministic verification."""

    frame_index: int
    state_hash: str = ""
    input_hash: str = ""
    combined_hash: str = ""
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class DesyncReport:
    """A recorded divergence between expected and actual frame state."""

    report_id: str
    frame_index: int
    expected_hash: str = ""
    actual_hash: str = ""
    input_diff: Dict[str, Any] = field(default_factory=dict)
    state_diff: Dict[str, Any] = field(default_factory=dict)
    severity: str = "low"
    description: str = ""
    timestamp: float = 0.0
    corrected: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class FrameSnapshot:
    """A complete snapshot of a single frame: input, checksum and status."""

    frame_index: int
    timestamp: float
    input_frame: Optional[InputFrame] = None
    checksum: Optional[Checksum] = None
    status: str = FrameStatus.SYNCED.value

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class RecordingSession:
    """Metadata for an in-progress or completed recording session."""

    session_id: str
    sequence_id: str
    name: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    player_count: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InputReplayConfig:
    """Tuning parameters for the input replay system."""

    max_recording_length: int = _MAX_FRAMES_PER_SEQUENCE
    auto_checksum: bool = True
    checksum_interval: int = 1
    playback_speed_default: float = 1.0
    enable_desync_detection: bool = True
    enable_frame_correction: bool = True
    max_desync_corrections: int = 50

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InputReplayStats:
    """Aggregate counters for the input replay system."""

    total_sequences: int = 0
    total_recordings: int = 0
    total_playbacks: int = 0
    total_frames_recorded: int = 0
    total_frames_played: int = 0
    desyncs_detected: int = 0
    desyncs_corrected: int = 0
    tick_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class InputReplaySnapshot:
    """Full state snapshot of the input replay system."""

    sequences: List[Dict[str, Any]] = field(default_factory=list)
    active_recording: Optional[Dict[str, Any]] = None
    active_playback: Optional[Dict[str, Any]] = None
    desync_reports: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=_now)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


@dataclass
class ReplayEvent:
    """An audit event emitted by the input replay system."""

    event_id: str
    kind: str
    timestamp: float
    payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return _dataclass_to_dict(self)


# ---------------------------------------------------------------------------
# Input Replay System
# ---------------------------------------------------------------------------

class InputReplaySystem:
    """Manages deterministic input recording, playback and desync detection."""

    _instance: Optional["InputReplaySystem"] = None
    _lock = threading.RLock()

    def __init__(self) -> None:
        # Stored sequences keyed by sequence_id
        self._sequences: Dict[str, InputSequence] = {}
        # Per-sequence checksums keyed by sequence_id, then frame_index
        self._checksums: Dict[str, Dict[int, Checksum]] = {}
        # Active recording state
        self._active_recording: Optional[RecordingSession] = None
        self._recording_buffer: List[InputFrame] = []
        self._recording_status: str = RecordingStatus.IDLE.value
        self._recording_frame_index: int = 0
        self._recording_start_time: float = 0.0
        self._recording_pause_time: float = 0.0
        self._recording_paused_total: float = 0.0
        self._recording_game_state_hash: str = ""
        self._recording_player_id: str = "player_01"
        # Active playback state
        self._active_playback: Optional[PlaybackState] = None
        self._playback_sequence_id: str = ""
        self._playback_accumulator: float = 0.0
        # Desync and audit logs
        self._desync_reports: List[DesyncReport] = []
        self._events: List[ReplayEvent] = []
        # Counters and configuration
        self._stats = InputReplayStats()
        self._config = InputReplayConfig()
        self._tick_count: int = 0
        self._event_counter: int = 0
        self._sequence_counter: int = 0
        self._correction_counter: int = 0
        self._last_input_time: float = 0.0
        # Singleton bookkeeping
        self._initialized: bool = False
        self._init_lock = threading.RLock()
        self._seed()

    # ------------------------------------------------------------------
    # Singleton Lifecycle
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "InputReplaySystem":
        """Return the singleton instance, creating it on first access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, config: Optional[InputReplayConfig] = None) -> Tuple[bool, str]:
        """Initialize or re-initialize the system with optional configuration."""
        with self._init_lock:
            if config is not None:
                self._config = copy.deepcopy(config)
            self._initialized = True
            self._record_event(
                ReplayEventKind.RECORDING_STARTED,
                {"action": "initialize", "initialized": self._initialized},
            )
        return True, "initialized"

    @classmethod
    def reset_instance(cls) -> Tuple[bool, str]:
        """Destroy the singleton instance so the next access creates a fresh one."""
        with cls._lock:
            cls._instance = None
        return True, "reset"

    # ------------------------------------------------------------------
    # Seed Data
    # ------------------------------------------------------------------

    def _seed(self) -> None:
        """Populate the system with pre-recorded input sequences."""
        self._sequences.clear()
        self._checksums.clear()
        self._desync_reports.clear()
        self._events.clear()
        self._stats = InputReplayStats()
        self._sequence_counter = 0

        sequences = [
            self._build_combat_sequence(),
            self._build_movement_tutorial_sequence(),
            self._build_puzzle_solution_sequence(),
            self._build_speedrun_sequence(),
        ]

        for seq in sequences:
            self._sequences[seq.sequence_id] = seq
            self._sequence_counter += 1
            self._stats.total_sequences += 1
            self._stats.total_frames_recorded += seq.total_frames
            # Compute a baseline checksum for the first frame of each seed sequence
            if seq.frames:
                first = seq.frames[0]
                checksum = Checksum(
                    frame_index=first.frame_index,
                    state_hash=seq.game_state_hash,
                    input_hash=_hash_input_frame(first),
                    combined_hash=_hash_payload({
                        "state": seq.game_state_hash,
                        "input": _hash_input_frame(first),
                    }),
                    timestamp=first.timestamp,
                )
                self._checksums.setdefault(seq.sequence_id, {})[first.frame_index] = checksum

        self._event_counter = 0
        self._tick_count = 0
        self._initialized = True

    def _build_combat_sequence(self) -> InputSequence:
        """Build a combat scenario sequence with keyboard and mouse inputs."""
        frames: List[InputFrame] = []
        base_time = 1700000000.0
        # Player draws a weapon, aims, fires, dodges and uses an ability
        actions = [
            (InputType.KEYBOARD, InputAction.PRESS, 49, (0.0, 0.0), (0.0, 0.0), 0.0),     # draw weapon
            (InputType.MOUSE, InputAction.MOVE, 0, (320.0, 240.0), (12.0, -4.0), 0.0),    # aim
            (InputType.MOUSE, InputAction.PRESS, 0, (332.0, 236.0), (0.0, 0.0), 0.05),    # fire
            (InputType.MOUSE, InputAction.RELEASE, 0, (332.0, 236.0), (0.0, 0.0), 0.0),   # release fire
            (InputType.KEYBOARD, InputAction.PRESS, 32, (0.0, 0.0), (0.0, 0.0), 0.0),     # dodge (space)
            (InputType.KEYBOARD, InputAction.RELEASE, 32, (0.0, 0.0), (0.0, 0.0), 0.12),
            (InputType.KEYBOARD, InputAction.PRESS, 23, (0.0, 0.0), (0.0, 0.0), 0.0),     # ability (q)
            (InputType.KEYBOARD, InputAction.RELEASE, 23, (0.0, 0.0), (0.0, 0.0), 0.08),
            (InputType.MOUSE, InputAction.MOVE, 0, (340.0, 230.0), (8.0, -6.0), 0.0),     # re-aim
            (InputType.MOUSE, InputAction.PRESS, 1, (340.0, 230.0), (0.0, 0.0), 0.0),     # alt fire
            (InputType.MOUSE, InputAction.RELEASE, 1, (340.0, 230.0), (0.0, 0.0), 0.06),
            (InputType.KEYBOARD, InputAction.PRESS, 49, (0.0, 0.0), (0.0, 0.0), 0.0),     # sheathe weapon
        ]
        for i, (itype, action, key, pos, delta, dur) in enumerate(actions):
            frames.append(InputFrame(
                frame_index=i,
                timestamp=base_time + float(i) * _FRAME_STEP_SECONDS,
                input_type=itype.value,
                action=action.value,
                key_code=key,
                position=pos,
                delta=delta,
                duration=dur,
                player_id="player_combat_01",
                metadata={"scenario": "combat", "intent": f"step_{i}"},
            ))
        duration = float(len(frames)) * _FRAME_STEP_SECONDS
        return InputSequence(
            sequence_id="seq_combat_arena_01",
            name="Combat Scenario - Crystal Arena",
            frames=frames,
            total_frames=len(frames),
            duration=duration,
            recording_started_at=base_time,
            recording_stopped_at=base_time + duration,
            player_id="player_combat_01",
            game_state_hash=_hash_state({"scene": "crystal_arena", "wave": 3, "hp": 100}),
            metadata={"scenario": "combat", "difficulty": "hard"},
        )

    def _build_movement_tutorial_sequence(self) -> InputSequence:
        """Build a movement tutorial sequence covering walking and sprinting."""
        frames: List[InputFrame] = []
        base_time = 1700000100.0
        actions = [
            (InputType.KEYBOARD, InputAction.PRESS, 17, (0.0, 0.0), (0.0, 0.0), 0.0),   # forward (w)
            (InputType.KEYBOARD, InputAction.HOLD, 17, (0.0, 0.0), (0.0, 1.0), 0.5),    # hold forward
            (InputType.KEYBOARD, InputAction.PRESS, 30, (0.0, 0.0), (0.0, 0.0), 0.0),   # strafe right (d)
            (InputType.KEYBOARD, InputAction.HOLD, 30, (0.0, 0.0), (1.0, 0.0), 0.4),
            (InputType.KEYBOARD, InputAction.PRESS, 42, (0.0, 0.0), (0.0, 0.0), 0.0),   # sprint (shift)
            (InputType.KEYBOARD, InputAction.HOLD, 42, (0.0, 0.0), (0.0, 0.0), 0.8),
            (InputType.KEYBOARD, InputAction.RELEASE, 42, (0.0, 0.0), (0.0, 0.0), 0.0),
            (InputType.KEYBOARD, InputAction.RELEASE, 30, (0.0, 0.0), (0.0, 0.0), 0.0),
            (InputType.KEYBOARD, InputAction.RELEASE, 17, (0.0, 0.0), (0.0, 0.0), 0.0),
            (InputType.KEYBOARD, InputAction.PRESS, 31, (0.0, 0.0), (0.0, 0.0), 0.0),   # backward (s)
            (InputType.KEYBOARD, InputAction.HOLD, 31, (0.0, 0.0), (0.0, -1.0), 0.3),
            (InputType.KEYBOARD, InputAction.RELEASE, 31, (0.0, 0.0), (0.0, 0.0), 0.0),
        ]
        for i, (itype, action, key, pos, delta, dur) in enumerate(actions):
            frames.append(InputFrame(
                frame_index=i,
                timestamp=base_time + float(i) * _FRAME_STEP_SECONDS,
                input_type=itype.value,
                action=action.value,
                key_code=key,
                position=pos,
                delta=delta,
                duration=dur,
                player_id="player_move_01",
                metadata={"scenario": "movement_tutorial", "intent": f"step_{i}"},
            ))
        duration = float(len(frames)) * _FRAME_STEP_SECONDS
        return InputSequence(
            sequence_id="seq_movement_tutorial_01",
            name="Movement Tutorial - Basic Locomotion",
            frames=frames,
            total_frames=len(frames),
            duration=duration,
            recording_started_at=base_time,
            recording_stopped_at=base_time + duration,
            player_id="player_move_01",
            game_state_hash=_hash_state({"scene": "tutorial_plains", "speed": 1.0}),
            metadata={"scenario": "movement_tutorial", "difficulty": "easy"},
        )

    def _build_puzzle_solution_sequence(self) -> InputSequence:
        """Build a puzzle solution sequence driven by touch and gesture inputs."""
        frames: List[InputFrame] = []
        base_time = 1700000200.0
        actions = [
            (InputType.TOUCH, InputAction.TAP, 0, (120.0, 400.0), (0.0, 0.0), 0.0),
            (InputType.TOUCH, InputAction.TAP, 0, (260.0, 380.0), (0.0, 0.0), 0.0),
            (InputType.GESTURE, InputAction.DRAG, 0, (120.0, 400.0), (140.0, -20.0), 0.4),
            (InputType.GESTURE, InputAction.PINCH, 0, (200.0, 390.0), (40.0, 40.0), 0.3),
            (InputType.GESTURE, InputAction.ROTATE, 0, (200.0, 390.0), (15.0, 0.0), 0.3),
            (InputType.TOUCH, InputAction.TAP, 0, (410.0, 300.0), (0.0, 0.0), 0.0),
            (InputType.GESTURE, InputAction.DRAG, 0, (410.0, 300.0), (-60.0, 80.0), 0.5),
            (InputType.TOUCH, InputAction.TAP, 0, (330.0, 220.0), (0.0, 0.0), 0.0),
            (InputType.GESTURE, InputAction.PINCH, 0, (330.0, 220.0), (-30.0, -30.0), 0.25),
            (InputType.TOUCH, InputAction.TAP, 0, (250.0, 250.0), (0.0, 0.0), 0.0),
        ]
        for i, (itype, action, key, pos, delta, dur) in enumerate(actions):
            frames.append(InputFrame(
                frame_index=i,
                timestamp=base_time + float(i) * _FRAME_STEP_SECONDS,
                input_type=itype.value,
                action=action.value,
                key_code=key,
                position=pos,
                delta=delta,
                duration=dur,
                player_id="player_puzzle_01",
                metadata={"scenario": "puzzle_solution", "intent": f"step_{i}"},
            ))
        duration = float(len(frames)) * _FRAME_STEP_SECONDS
        return InputSequence(
            sequence_id="seq_puzzle_ruins_01",
            name="Puzzle Solution - Ancient Ruins",
            frames=frames,
            total_frames=len(frames),
            duration=duration,
            recording_started_at=base_time,
            recording_stopped_at=base_time + duration,
            player_id="player_puzzle_01",
            game_state_hash=_hash_state({"scene": "ancient_ruins", "puzzle_progress": 0}),
            metadata={"scenario": "puzzle_solution", "difficulty": "medium"},
        )

    def _build_speedrun_sequence(self) -> InputSequence:
        """Build a speedrun attempt sequence mixing movement, jumps and abilities."""
        frames: List[InputFrame] = []
        base_time = 1700000300.0
        actions = [
            (InputType.GAMEPAD, InputAction.MOVE, 0, (0.0, 0.0), (0.0, 1.0), 0.0),       # stick forward
            (InputType.GAMEPAD, InputAction.HOLD, 0, (0.0, 0.0), (0.0, 1.0), 1.2),
            (InputType.GAMEPAD, InputAction.PRESS, 0, (0.0, 0.0), (0.0, 0.0), 0.0),      # jump (A)
            (InputType.GAMEPAD, InputAction.RELEASE, 0, (0.0, 0.0), (0.0, 0.0), 0.1),
            (InputType.GAMEPAD, InputAction.MOVE, 0, (0.0, 0.0), (1.0, 1.0), 0.0),       # diagonal
            (InputType.GAMEPAD, InputAction.HOLD, 0, (0.0, 0.0), (1.0, 1.0), 0.6),
            (InputType.GAMEPAD, InputAction.PRESS, 2, (0.0, 0.0), (0.0, 0.0), 0.0),      # dash (X)
            (InputType.GAMEPAD, InputAction.RELEASE, 2, (0.0, 0.0), (0.0, 0.0), 0.08),
            (InputType.GAMEPAD, InputAction.PRESS, 3, (0.0, 0.0), (0.0, 0.0), 0.0),      # ability (Y)
            (InputType.GAMEPAD, InputAction.RELEASE, 3, (0.0, 0.0), (0.0, 0.0), 0.12),
            (InputType.GAMEPAD, InputAction.MOVE, 0, (0.0, 0.0), (0.0, 1.0), 0.0),
            (InputType.GAMEPAD, InputAction.HOLD, 0, (0.0, 0.0), (0.0, 1.0), 0.9),
            (InputType.GAMEPAD, InputAction.PRESS, 0, (0.0, 0.0), (0.0, 0.0), 0.0),      # jump
            (InputType.GAMEPAD, InputAction.RELEASE, 0, (0.0, 0.0), (0.0, 0.0), 0.1),
            (InputType.GAMEPAD, InputAction.MOVE, 0, (0.0, 0.0), (0.7, 0.7), 0.0),
            (InputType.GAMEPAD, InputAction.HOLD, 0, (0.0, 0.0), (0.7, 0.7), 0.5),
        ]
        for i, (itype, action, key, pos, delta, dur) in enumerate(actions):
            frames.append(InputFrame(
                frame_index=i,
                timestamp=base_time + float(i) * _FRAME_STEP_SECONDS,
                input_type=itype.value,
                action=action.value,
                key_code=key,
                position=pos,
                delta=delta,
                duration=dur,
                player_id="player_speedrun_01",
                metadata={"scenario": "speedrun", "intent": f"step_{i}", "split": "segment_a"},
            ))
        duration = float(len(frames)) * _FRAME_STEP_SECONDS
        return InputSequence(
            sequence_id="seq_speedrun_any_percent_01",
            name="Speedrun Attempt - Any Percent",
            frames=frames,
            total_frames=len(frames),
            duration=duration,
            recording_started_at=base_time,
            recording_stopped_at=base_time + duration,
            player_id="player_speedrun_01",
            game_state_hash=_hash_state({"scene": "full_game", "split": 0, "timer": 0.0}),
            metadata={"scenario": "speedrun", "difficulty": "extreme", "category": "any_percent"},
        )

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: ReplayEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> ReplayEvent:
        """Append an audit event to the in-memory log."""
        event = ReplayEvent(
            event_id=_new_id("evt"),
            kind=kind.value if isinstance(kind, ReplayEventKind) else str(kind),
            timestamp=_now(),
            payload=payload or {},
        )
        self._events.append(event)
        self._event_counter += 1
        _evict_fifo_list(self._events, _MAX_EVENTS)
        return event

    def _resolve_sequence(self, sequence_id: str) -> Optional[InputSequence]:
        """Look up a sequence by id, returning None when absent."""
        if not sequence_id:
            return None
        return self._sequences.get(sequence_id)

    def _resolve_playback_sequence(self) -> Optional[InputSequence]:
        """Return the sequence bound to the active playback, if any."""
        if not self._playback_sequence_id:
            return None
        return self._sequences.get(self._playback_sequence_id)

    def _ensure_playback_bounds(self, state: PlaybackState, seq: InputSequence) -> None:
        """Clamp playback start/end frame indices to the sequence length."""
        total = max(0, seq.total_frames)
        if state.end_frame < 0 or state.end_frame >= total:
            state.end_frame = total - 1 if total > 0 else 0
        if state.start_frame < 0:
            state.start_frame = 0
        if state.start_frame > state.end_frame and total > 0:
            state.start_frame = 0

    def _sequence_summary(self, seq: InputSequence) -> Dict[str, Any]:
        """Build a lightweight summary dict for a sequence."""
        return {
            "sequence_id": seq.sequence_id,
            "name": seq.name,
            "total_frames": seq.total_frames,
            "duration": seq.duration,
            "player_id": seq.player_id,
            "game_state_hash": seq.game_state_hash,
            "metadata": dict(seq.metadata),
        }

    # ------------------------------------------------------------------
    # Recording Management
    # ------------------------------------------------------------------

    def start_recording(
        self,
        name: str = "",
        player_id: str = "player_01",
        game_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[RecordingSession]]:
        """Begin a new recording session, returning the session descriptor."""
        with self._init_lock:
            if self._recording_status == RecordingStatus.RECORDING.value:
                return False, "already_recording", self._active_recording
            if self._recording_status == RecordingStatus.PAUSED.value:
                # Resume an existing paused session instead of starting fresh
                return self.resume_recording()

            session_id = _new_id("rec")
            sequence_id = _new_id("seq")
            now = _now()
            state_hash = _hash_state(game_state)
            session = RecordingSession(
                session_id=session_id,
                sequence_id=sequence_id,
                name=name or f"Recording {self._sequence_counter + 1}",
                start_time=now,
                end_time=0.0,
                player_count=1,
                metadata=metadata or {},
            )
            self._active_recording = session
            self._recording_buffer = []
            self._recording_status = RecordingStatus.RECORDING.value
            self._recording_frame_index = 0
            self._recording_start_time = now
            self._recording_paused_total = 0.0
            self._recording_pause_time = 0.0
            self._recording_game_state_hash = state_hash
            self._recording_player_id = player_id
            self._stats.total_recordings += 1
            self._record_event(
                ReplayEventKind.RECORDING_STARTED,
                {
                    "session_id": session_id,
                    "sequence_id": sequence_id,
                    "name": session.name,
                    "player_id": player_id,
                    "game_state_hash": state_hash,
                },
            )
            return True, "recording_started", session

    def stop_recording(
        self,
        save: bool = True,
    ) -> Tuple[bool, str, Optional[InputSequence]]:
        """Stop the active recording and optionally save it as a sequence."""
        with self._init_lock:
            if self._recording_status == RecordingStatus.IDLE.value:
                return False, "not_recording", None
            if self._recording_status == RecordingStatus.PAUSED.value:
                # Finalize from a paused state
                self._recording_paused_total += _now() - self._recording_pause_time

            now = _now()
            session = self._active_recording
            if session is None:
                return False, "no_active_session", None
            session.end_time = now
            duration = max(0.0, now - self._recording_start_time - self._recording_paused_total)

            sequence = InputSequence(
                sequence_id=session.sequence_id,
                name=session.name,
                frames=list(self._recording_buffer),
                total_frames=len(self._recording_buffer),
                duration=duration,
                recording_started_at=self._recording_start_time,
                recording_stopped_at=now,
                player_id=self._recording_player_id,
                game_state_hash=self._recording_game_state_hash,
                metadata=dict(session.metadata),
            )

            saved = False
            if save and sequence.total_frames > 0:
                if len(self._sequences) >= _MAX_SEQUENCES:
                    # Evict the oldest non-seed sequence to make room
                    oldest_id = next(iter(self._sequences))
                    self._sequences.pop(oldest_id, None)
                    self._checksums.pop(oldest_id, None)
                    self._stats.total_sequences -= 1
                self._sequences[sequence.sequence_id] = sequence
                self._sequence_counter += 1
                self._stats.total_sequences += 1
                self._stats.total_frames_recorded += sequence.total_frames
                saved = True

            self._recording_status = RecordingStatus.SAVED.value if save else RecordingStatus.STOPPED.value
            self._record_event(
                ReplayEventKind.RECORDING_STOPPED,
                {
                    "session_id": session.session_id,
                    "sequence_id": sequence.sequence_id,
                    "saved": saved,
                    "total_frames": sequence.total_frames,
                    "duration": duration,
                },
            )
            # Reset recording state but keep the buffer for one last inspection
            self._active_recording = None
            self._recording_status = RecordingStatus.IDLE.value
            self._recording_buffer = []
            self._recording_frame_index = 0
            return True, "recording_saved" if saved else "recording_stopped", sequence

    def pause_recording(self) -> Tuple[bool, str]:
        """Pause the active recording session."""
        with self._init_lock:
            if self._recording_status != RecordingStatus.RECORDING.value:
                return False, "not_recording"
            self._recording_status = RecordingStatus.PAUSED.value
            self._recording_pause_time = _now()
            self._record_event(ReplayEventKind.RECORDING_STOPPED, {"action": "pause"})
            return True, "recording_paused"

    def resume_recording(self) -> Tuple[bool, str, Optional[RecordingSession]]:
        """Resume a paused recording session."""
        with self._init_lock:
            if self._recording_status != RecordingStatus.PAUSED.value:
                return False, "not_paused", self._active_recording
            self._recording_paused_total += _now() - self._recording_pause_time
            self._recording_status = RecordingStatus.RECORDING.value
            self._record_event(ReplayEventKind.RECORDING_STARTED, {"action": "resume"})
            return True, "recording_resumed", self._active_recording

    def record_input(
        self,
        input_type: Any,
        action: Any,
        key_code: int = 0,
        position: Optional[Tuple[float, float]] = None,
        delta: Optional[Tuple[float, float]] = None,
        duration: float = 0.0,
        player_id: Optional[str] = None,
        timestamp: Optional[float] = None,
        game_state: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tuple[bool, str, Optional[InputFrame]]:
        """Capture a single input event into the active recording buffer."""
        with self._init_lock:
            if self._recording_status != RecordingStatus.RECORDING.value:
                return False, "not_recording", None

            itype_val = _normalize_enum(input_type, InputType)
            action_val = _normalize_enum(action, InputAction)
            pos = position if position is not None else (0.0, 0.0)
            delt = delta if delta is not None else (0.0, 0.0)
            ts = timestamp if timestamp is not None else _now()
            pid = player_id or self._recording_player_id

            frame = InputFrame(
                frame_index=self._recording_frame_index,
                timestamp=ts,
                input_type=itype_val,
                action=action_val,
                key_code=int(key_code),
                position=(float(pos[0]), float(pos[1])),
                delta=(float(delt[0]), float(delt[1])),
                duration=float(duration),
                player_id=pid,
                metadata=metadata or {},
            )

            if self._recording_frame_index >= self._config.max_recording_length:
                return False, "recording_length_exceeded", None

            self._recording_buffer.append(frame)
            self._recording_frame_index += 1
            self._stats.total_frames_recorded += 1
            self._last_input_time = ts

            # Optionally compute an automatic checksum for the captured frame
            if self._config.auto_checksum and self._active_recording is not None:
                interval = max(1, int(self._config.checksum_interval))
                if frame.frame_index % interval == 0:
                    self.compute_checksum(
                        frame.frame_index,
                        game_state=game_state,
                        input_frame=frame,
                        sequence_id=self._active_recording.sequence_id,
                        record=False,
                    )

            self._record_event(
                ReplayEventKind.INPUT_RECORDED,
                {
                    "frame_index": frame.frame_index,
                    "input_type": itype_val,
                    "action": action_val,
                    "player_id": pid,
                },
            )
            return True, "input_recorded", frame

    def get_recording_status(self) -> RecordingStatus:
        """Return the current recording lifecycle status."""
        return RecordingStatus(self._recording_status)

    # ------------------------------------------------------------------
    # Sequence Management
    # ------------------------------------------------------------------

    def save_sequence(
        self,
        sequence: InputSequence,
        overwrite: bool = False,
    ) -> Tuple[bool, str, Optional[InputSequence]]:
        """Persist an input sequence into the store."""
        with self._init_lock:
            if sequence is None:
                return False, "invalid_sequence", None
            existing = self._sequences.get(sequence.sequence_id)
            if existing is not None and not overwrite:
                return False, "sequence_exists", existing
            if len(self._sequences) >= _MAX_SEQUENCES and existing is None:
                oldest_id = next(iter(self._sequences))
                self._sequences.pop(oldest_id, None)
                self._checksums.pop(oldest_id, None)
                self._stats.total_sequences -= 1
            sequence.total_frames = len(sequence.frames)
            self._sequences[sequence.sequence_id] = sequence
            if existing is None:
                self._stats.total_sequences += 1
            self._record_event(
                ReplayEventKind.INPUT_RECORDED,
                {"action": "save_sequence", "sequence_id": sequence.sequence_id},
            )
            return True, "sequence_saved", sequence

    def load_sequence(self, sequence_id: str) -> Tuple[bool, str, Optional[InputSequence]]:
        """Load a sequence from the store by id."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return False, "sequence_not_found", None
        return True, "sequence_loaded", copy.deepcopy(seq)

    def delete_sequence(self, sequence_id: str) -> Tuple[bool, str]:
        """Remove a sequence and its checksums from the store."""
        with self._init_lock:
            if sequence_id not in self._sequences:
                return False, "sequence_not_found"
            self._sequences.pop(sequence_id, None)
            self._checksums.pop(sequence_id, None)
            self._stats.total_sequences = max(0, self._stats.total_sequences - 1)
            self._record_event(
                ReplayEventKind.RECORDING_STOPPED,
                {"action": "delete_sequence", "sequence_id": sequence_id},
            )
            return True, "sequence_deleted"

    def get_sequence(self, sequence_id: str) -> Optional[InputSequence]:
        """Return a sequence by id without removing it."""
        return self._resolve_sequence(sequence_id)

    def list_sequences(self) -> List[Dict[str, Any]]:
        """Return lightweight summaries of all stored sequences."""
        return [self._sequence_summary(seq) for seq in self._sequences.values()]

    def export_sequence(self, sequence_id: str) -> Tuple[bool, str, Optional[str]]:
        """Serialize a sequence to a JSON string for transfer or storage."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return False, "sequence_not_found", None
        try:
            payload = {
                "sequence": seq.to_dict(),
                "checksums": {
                    str(idx): chk.to_dict()
                    for idx, chk in self._checksums.get(sequence_id, {}).items()
                },
            }
            serialized = json.dumps(payload, sort_keys=True, default=str)
            return True, "sequence_exported", serialized
        except (TypeError, ValueError) as exc:
            return False, f"export_failed:{exc}", None

    def import_sequence(self, data: str, sequence_id: Optional[str] = None) -> Tuple[bool, str, Optional[InputSequence]]:
        """Import a sequence from a JSON string produced by export_sequence."""
        with self._init_lock:
            try:
                payload = json.loads(data)
            except (TypeError, ValueError, json.JSONDecodeError) as exc:
                return False, f"import_failed:{exc}", None

            seq_data = payload.get("sequence") if isinstance(payload, dict) else payload
            if not isinstance(seq_data, dict):
                return False, "invalid_payload", None

            frames_data = seq_data.get("frames", []) or []
            frames: List[InputFrame] = []
            for i, fd in enumerate(frames_data):
                if not isinstance(fd, dict):
                    continue
                pos = fd.get("position", [0.0, 0.0]) or [0.0, 0.0]
                delt = fd.get("delta", [0.0, 0.0]) or [0.0, 0.0]
                frames.append(InputFrame(
                    frame_index=_safe_int(fd.get("frame_index", i), i),
                    timestamp=_safe_float(fd.get("timestamp", 0.0)),
                    input_type=str(fd.get("input_type", InputType.KEYBOARD.value)),
                    action=str(fd.get("action", InputAction.PRESS.value)),
                    key_code=_safe_int(fd.get("key_code", 0)),
                    position=(float(pos[0]), float(pos[1])),
                    delta=(float(delt[0]), float(delt[1])),
                    duration=_safe_float(fd.get("duration", 0.0)),
                    player_id=str(fd.get("player_id", "player_01")),
                    metadata=dict(fd.get("metadata", {})),
                ))

            target_id = sequence_id or seq_data.get("sequence_id") or _new_id("seq")
            sequence = InputSequence(
                sequence_id=target_id,
                name=str(seq_data.get("name", "")),
                frames=frames,
                total_frames=len(frames),
                duration=_safe_float(seq_data.get("duration", 0.0)),
                recording_started_at=_safe_float(seq_data.get("recording_started_at", 0.0)),
                recording_stopped_at=_safe_float(seq_data.get("recording_stopped_at", 0.0)),
                player_id=str(seq_data.get("player_id", "player_01")),
                game_state_hash=str(seq_data.get("game_state_hash", "")),
                metadata=dict(seq_data.get("metadata", {})),
            )

            # Import checksums when present
            checksums_data = payload.get("checksums", {}) if isinstance(payload, dict) else {}
            if isinstance(checksums_data, dict):
                bucket: Dict[int, Checksum] = {}
                for idx_str, cd in checksums_data.items():
                    if not isinstance(cd, dict):
                        continue
                    idx = _safe_int(idx_str)
                    bucket[idx] = Checksum(
                        frame_index=idx,
                        state_hash=str(cd.get("state_hash", "")),
                        input_hash=str(cd.get("input_hash", "")),
                        combined_hash=str(cd.get("combined_hash", "")),
                        timestamp=_safe_float(cd.get("timestamp", 0.0)),
                    )
                if bucket:
                    self._checksums[target_id] = bucket

            # Track as a new sequence when the id was not already present
            is_new = target_id not in self._sequences
            self._sequences[target_id] = sequence
            if is_new:
                self._stats.total_sequences += 1
            self._stats.total_frames_recorded += sequence.total_frames
            self._record_event(
                ReplayEventKind.INPUT_RECORDED,
                {"action": "import_sequence", "sequence_id": target_id},
            )
            return True, "sequence_imported", sequence

    # ------------------------------------------------------------------
    # Playback Control
    # ------------------------------------------------------------------

    def start_playback(
        self,
        sequence_id: str,
        speed_multiplier: float = 1.0,
        loop: bool = False,
        start_frame: int = 0,
        end_frame: int = -1,
    ) -> Tuple[bool, str, Optional[PlaybackState]]:
        """Begin deterministic playback of a stored sequence."""
        with self._init_lock:
            seq = self._resolve_sequence(sequence_id)
            if seq is None:
                return False, "sequence_not_found", None
            if seq.total_frames <= 0:
                return False, "sequence_empty", None

            speed = _clamp(
                _safe_float(speed_multiplier, self._config.playback_speed_default),
                _MIN_PLAYBACK_SPEED,
                _MAX_PLAYBACK_SPEED,
            )
            state = PlaybackState(
                sequence_id=sequence_id,
                current_frame=max(0, int(start_frame)),
                status=PlaybackStatus.PLAYING.value,
                speed_multiplier=speed,
                loop=bool(loop),
                start_frame=max(0, int(start_frame)),
                end_frame=int(end_frame),
            )
            self._ensure_playback_bounds(state, seq)

            self._active_playback = state
            self._playback_sequence_id = sequence_id
            self._playback_accumulator = 0.0
            self._stats.total_playbacks += 1
            self._record_event(
                ReplayEventKind.PLAYBACK_STARTED,
                {
                    "sequence_id": sequence_id,
                    "speed_multiplier": speed,
                    "loop": bool(loop),
                    "start_frame": state.start_frame,
                    "end_frame": state.end_frame,
                },
            )
            return True, "playback_started", state

    def pause_playback(self) -> Tuple[bool, str]:
        """Pause the active playback session."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback"
            if self._active_playback.status != PlaybackStatus.PLAYING.value:
                return False, "playback_not_playing"
            self._active_playback.status = PlaybackStatus.PAUSED.value
            self._record_event(ReplayEventKind.PLAYBACK_PAUSED, {})
            return True, "playback_paused"

    def resume_playback(self) -> Tuple[bool, str]:
        """Resume a paused playback session."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback"
            if self._active_playback.status != PlaybackStatus.PAUSED.value:
                return False, "playback_not_paused"
            self._active_playback.status = PlaybackStatus.PLAYING.value
            self._record_event(ReplayEventKind.PLAYBACK_RESUMED, {})
            return True, "playback_resumed"

    def stop_playback(self) -> Tuple[bool, str]:
        """Stop the active playback session."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback"
            self._active_playback.status = PlaybackStatus.STOPPED.value
            self._record_event(ReplayEventKind.PLAYBACK_COMPLETED, {"action": "stop"})
            self._active_playback = None
            self._playback_sequence_id = ""
            self._playback_accumulator = 0.0
            return True, "playback_stopped"

    def advance_frame(
        self,
        game_state: Optional[Dict[str, Any]] = None,
        steps: int = 1,
    ) -> Tuple[bool, str, Optional[InputFrame]]:
        """Advance playback by one or more frames and verify determinism."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback", None
            state = self._active_playback
            if state.status not in (PlaybackStatus.PLAYING.value, PlaybackStatus.PAUSED.value):
                return False, "playback_not_active", None

            seq = self._resolve_playback_sequence()
            if seq is None:
                state.status = PlaybackStatus.FAILED.value
                self._record_event(ReplayEventKind.PLAYBACK_FAILED, {"reason": "sequence_missing"})
                return False, "sequence_missing", None

            count = max(1, int(steps))
            last_frame: Optional[InputFrame] = None
            for _ in range(count):
                if state.current_frame > state.end_frame:
                    if state.loop:
                        state.current_frame = state.start_frame
                    else:
                        state.status = PlaybackStatus.COMPLETED.value
                        self._record_event(ReplayEventKind.PLAYBACK_COMPLETED, {})
                        return True, "playback_completed", last_frame

                if state.current_frame < 0 or state.current_frame >= seq.total_frames:
                    state.status = PlaybackStatus.FAILED.value
                    self._record_event(ReplayEventKind.PLAYBACK_FAILED, {"reason": "frame_out_of_range"})
                    return False, "frame_out_of_range", None

                frame = seq.frames[state.current_frame]
                last_frame = frame

                # Determinism verification: compare stored checksum against live state
                if self._config.enable_desync_detection:
                    bucket = self._checksums.get(seq.sequence_id, {})
                    stored = bucket.get(frame.frame_index)
                    if stored is not None and game_state is not None:
                        actual_hash = _hash_state(game_state)
                        if actual_hash and stored.state_hash and actual_hash != stored.state_hash:
                            report = self._register_desync(
                                frame.frame_index,
                                expected_hash=stored.state_hash,
                                actual_hash=actual_hash,
                                state_diff=game_state,
                            )
                            if self._config.enable_frame_correction:
                                self.correct_desync(report.report_id)

                state.current_frame += 1
                self._stats.total_frames_played += 1
                self._record_event(
                    ReplayEventKind.FRAME_ADVANCED,
                    {"frame_index": frame.frame_index, "input_type": frame.input_type},
                )

            return True, "frame_advanced", last_frame

    def seek_to_frame(self, frame_index: int) -> Tuple[bool, str]:
        """Jump the playback cursor to a specific frame index."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback"
            seq = self._resolve_playback_sequence()
            if seq is None:
                return False, "sequence_missing"
            target = int(frame_index)
            if target < 0 or target >= seq.total_frames:
                return False, "frame_out_of_range"
            self._active_playback.current_frame = target
            self._playback_accumulator = 0.0
            self._record_event(ReplayEventKind.FRAME_ADVANCED, {"action": "seek", "frame_index": target})
            return True, "seek_complete"

    def set_playback_speed(self, speed_multiplier: float) -> Tuple[bool, str]:
        """Adjust the playback speed multiplier on the active session."""
        with self._init_lock:
            if self._active_playback is None:
                return False, "no_active_playback"
            speed = _clamp(
                _safe_float(speed_multiplier, 1.0),
                _MIN_PLAYBACK_SPEED,
                _MAX_PLAYBACK_SPEED,
            )
            self._active_playback.speed_multiplier = speed
            self._record_event(ReplayEventKind.PLAYBACK_RESUMED, {"action": "speed", "speed": speed})
            return True, "speed_set"

    def get_playback_state(self) -> Optional[PlaybackState]:
        """Return the active playback state, or None when idle."""
        return self._active_playback

    # ------------------------------------------------------------------
    # Checksum and Desync Management
    # ------------------------------------------------------------------

    def compute_checksum(
        self,
        frame_index: int,
        game_state: Optional[Dict[str, Any]] = None,
        input_frame: Optional[InputFrame] = None,
        sequence_id: Optional[str] = None,
        checksum_type: ChecksumType = ChecksumType.COMBINED,
        record: bool = True,
    ) -> Optional[Checksum]:
        """Compute and store a checksum for a frame's state and/or input."""
        with self._init_lock:
            target_seq = sequence_id or self._playback_sequence_id
            if not target_seq and self._active_recording is not None:
                target_seq = self._active_recording.sequence_id
            if not target_seq:
                return None

            state_hash = _hash_state(game_state) if checksum_type in (
                ChecksumType.STATE_HASH, ChecksumType.COMBINED
            ) else ""
            input_hash = _hash_input_frame(input_frame) if checksum_type in (
                ChecksumType.INPUT_HASH, ChecksumType.COMBINED, ChecksumType.FRAME_HASH
            ) else ""

            combined = ""
            if checksum_type == ChecksumType.COMBINED:
                combined = _hash_payload({"state": state_hash, "input": input_hash})
            elif checksum_type == ChecksumType.FRAME_HASH:
                combined = input_hash
            elif checksum_type == ChecksumType.STATE_HASH:
                combined = state_hash

            checksum = Checksum(
                frame_index=int(frame_index),
                state_hash=state_hash,
                input_hash=input_hash,
                combined_hash=combined,
                timestamp=_now(),
            )

            if record:
                bucket = self._checksums.setdefault(target_seq, {})
                bucket[int(frame_index)] = checksum
            return checksum

    def verify_checksum(
        self,
        frame_index: int,
        game_state: Optional[Dict[str, Any]] = None,
        sequence_id: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """Verify a stored checksum against a live game state for a frame."""
        target_seq = sequence_id or self._playback_sequence_id
        if not target_seq:
            return False, "no_sequence"
        bucket = self._checksums.get(target_seq, {})
        stored = bucket.get(int(frame_index))
        if stored is None:
            return False, "no_stored_checksum"
        if not stored.state_hash:
            return True, "no_state_hash_to_verify"
        actual_hash = _hash_state(game_state)
        if not actual_hash:
            return False, "no_actual_state"
        if actual_hash == stored.state_hash:
            return True, "checksum_matched"
        self._record_event(
            ReplayEventKind.CHECKSUM_MISMATCH,
            {
                "frame_index": int(frame_index),
                "expected": stored.state_hash,
                "actual": actual_hash,
            },
        )
        return False, "checksum_mismatch"

    def detect_desync(
        self,
        frame_index: int,
        actual_state: Optional[Dict[str, Any]] = None,
        expected_state: Optional[Dict[str, Any]] = None,
        sequence_id: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[DesyncReport]]:
        """Compare expected and actual state hashes for a frame."""
        target_seq = sequence_id or self._playback_sequence_id
        if not target_seq:
            return False, "no_sequence", None
        bucket = self._checksums.get(target_seq, {})
        stored = bucket.get(int(frame_index))

        expected_hash = ""
        if expected_state is not None:
            expected_hash = _hash_state(expected_state)
        elif stored is not None:
            expected_hash = stored.state_hash

        actual_hash = _hash_state(actual_state)
        if not expected_hash or not actual_hash:
            return False, "missing_hash_for_comparison", None
        if expected_hash == actual_hash:
            return True, "in_sync", None

        report = self._register_desync(
            frame_index=int(frame_index),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            state_diff=actual_state or {},
        )
        return True, "desync_detected", report

    def _register_desync(
        self,
        frame_index: int,
        expected_hash: str,
        actual_hash: str,
        state_diff: Optional[Dict[str, Any]] = None,
        input_diff: Optional[Dict[str, Any]] = None,
        severity: str = "high",
        description: str = "",
    ) -> DesyncReport:
        """Create, store and announce a desync report."""
        report = DesyncReport(
            report_id=_new_id("desync"),
            frame_index=int(frame_index),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            input_diff=input_diff or {},
            state_diff=state_diff or {},
            severity=severity,
            description=description or f"State hash mismatch at frame {frame_index}",
            timestamp=_now(),
            corrected=False,
        )
        self._desync_reports.append(report)
        self._stats.desyncs_detected += 1
        _evict_fifo_list(self._desync_reports, _MAX_DESYNC_REPORTS)
        self._record_event(
            ReplayEventKind.DESYNC_DETECTED,
            {
                "report_id": report.report_id,
                "frame_index": int(frame_index),
                "severity": severity,
            },
        )
        return report

    def correct_desync(self, report_id: str) -> Tuple[bool, str]:
        """Mark a desync report as corrected and reset toward the expected state."""
        with self._init_lock:
            report = next((r for r in self._desync_reports if r.report_id == report_id), None)
            if report is None:
                return False, "report_not_found"
            if self._correction_counter >= self._config.max_desync_corrections:
                return False, "correction_limit_reached"
            report.corrected = True
            report.description = (report.description + " | corrected").strip(" |")
            self._correction_counter += 1
            self._stats.desyncs_corrected += 1

            # When correcting during playback, rewind the cursor so the next
            # advance re-applies the expected frame from the recorded sequence.
            if self._active_playback is not None and self._playback_sequence_id:
                seq = self._resolve_sequence(self._playback_sequence_id)
                if seq is not None and 0 <= report.frame_index < seq.total_frames:
                    self._active_playback.current_frame = report.frame_index

            self._record_event(
                ReplayEventKind.CHECKSUM_MISMATCH,
                {"action": "correct", "report_id": report_id, "frame_index": report.frame_index},
            )
            return True, "desync_corrected"

    def get_desync_reports(self) -> List[DesyncReport]:
        """Return all recorded desync reports."""
        return list(self._desync_reports)

    def clear_desync_reports(self) -> Tuple[bool, str]:
        """Clear all stored desync reports."""
        with self._init_lock:
            cleared = len(self._desync_reports)
            self._desync_reports.clear()
            self._correction_counter = 0
            self._record_event(
                ReplayEventKind.CHECKSUM_MISMATCH,
                {"action": "clear_desync_reports", "cleared": cleared},
            )
            return True, "desync_reports_cleared"

    # ------------------------------------------------------------------
    # Frame Management
    # ------------------------------------------------------------------

    def get_frame(
        self,
        sequence_id: str,
        frame_index: int,
    ) -> Optional[InputFrame]:
        """Return a single frame from a stored sequence."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return None
        if frame_index < 0 or frame_index >= seq.total_frames:
            return None
        return seq.frames[frame_index]

    def get_frame_range(
        self,
        sequence_id: str,
        start_frame: int = 0,
        end_frame: int = -1,
    ) -> List[InputFrame]:
        """Return a contiguous range of frames from a stored sequence."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return []
        total = seq.total_frames
        if total <= 0:
            return []
        start = max(0, int(start_frame))
        end = int(end_frame)
        if end < 0 or end >= total:
            end = total - 1
        if start > end:
            return []
        return list(seq.frames[start:end + 1])

    def get_frame_count(self, sequence_id: str) -> int:
        """Return the number of frames stored in a sequence."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return 0
        return seq.total_frames

    def get_frame_snapshot(
        self,
        sequence_id: str,
        frame_index: int,
    ) -> Optional[FrameSnapshot]:
        """Return a full snapshot (input, checksum, status) for a frame."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return None
        if frame_index < 0 or frame_index >= seq.total_frames:
            return None
        frame = seq.frames[frame_index]
        bucket = self._checksums.get(sequence_id, {})
        checksum = bucket.get(frame_index)
        status = FrameStatus.SYNCED.value
        # If any desync report targets this frame, reflect its corrected state
        for report in self._desync_reports:
            if report.frame_index == frame_index:
                status = FrameStatus.CORRECTED.value if report.corrected else FrameStatus.DESYNCED.value
                break
        return FrameSnapshot(
            frame_index=frame_index,
            timestamp=frame.timestamp,
            input_frame=frame,
            checksum=checksum,
            status=status,
        )

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------

    def compare_sequences(
        self,
        sequence_id_a: str,
        sequence_id_b: str,
    ) -> Dict[str, Any]:
        """Compare two sequences frame-by-frame and summarize differences."""
        seq_a = self._resolve_sequence(sequence_id_a)
        seq_b = self._resolve_sequence(sequence_id_b)
        if seq_a is None or seq_b is None:
            return {"success": False, "reason": "sequence_not_found"}

        max_frames = max(seq_a.total_frames, seq_b.total_frames)
        matched = 0
        mismatched = 0
        differences: List[Dict[str, Any]] = []

        for i in range(max_frames):
            fa = seq_a.frames[i] if i < seq_a.total_frames else None
            fb = seq_b.frames[i] if i < seq_b.total_frames else None
            if fa is None or fb is None:
                mismatched += 1
                differences.append({"frame_index": i, "reason": "missing_frame"})
                continue
            sig_a = _frame_signature(fa)
            sig_b = _frame_signature(fb)
            if sig_a == sig_b:
                matched += 1
            else:
                mismatched += 1
                diff_keys = [k for k in sig_a if sig_a.get(k) != sig_b.get(k)]
                differences.append({
                    "frame_index": i,
                    "diff_keys": diff_keys,
                    "a": sig_a,
                    "b": sig_b,
                })

        similarity = (matched / max_frames * 100.0) if max_frames > 0 else 0.0
        return {
            "success": True,
            "sequence_a": sequence_id_a,
            "sequence_b": sequence_id_b,
            "frames_a": seq_a.total_frames,
            "frames_b": seq_b.total_frames,
            "matched": matched,
            "mismatched": mismatched,
            "similarity_percent": round(similarity, 2),
            "differences": differences[:200],
        }

    def analyze_input_pattern(self, sequence_id: str) -> Dict[str, Any]:
        """Analyze the input pattern of a sequence and return distribution stats."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return {"success": False, "reason": "sequence_not_found"}

        type_counts: Dict[str, int] = {}
        action_counts: Dict[str, int] = {}
        player_counts: Dict[str, int] = {}
        total_delta_x = 0.0
        total_delta_y = 0.0
        total_duration = 0.0

        for frame in seq.frames:
            type_counts[frame.input_type] = type_counts.get(frame.input_type, 0) + 1
            action_counts[frame.action] = action_counts.get(frame.action, 0) + 1
            player_counts[frame.player_id] = player_counts.get(frame.player_id, 0) + 1
            total_delta_x += float(frame.delta[0])
            total_delta_y += float(frame.delta[1])
            total_duration += float(frame.duration)

        dominant_type = max(type_counts, key=type_counts.get) if type_counts else ""
        dominant_action = max(action_counts, key=action_counts.get) if action_counts else ""
        avg_frame_interval = (seq.duration / seq.total_frames) if seq.total_frames > 0 else 0.0

        return {
            "success": True,
            "sequence_id": sequence_id,
            "total_frames": seq.total_frames,
            "duration": seq.duration,
            "type_counts": type_counts,
            "action_counts": action_counts,
            "player_counts": player_counts,
            "dominant_type": dominant_type,
            "dominant_action": dominant_action,
            "total_delta": [round(total_delta_x, 4), round(total_delta_y, 4)],
            "total_input_duration": round(total_duration, 4),
            "avg_frame_interval": round(avg_frame_interval, 6),
        }

    def get_input_statistics(self) -> Dict[str, Any]:
        """Return aggregate input statistics across all stored sequences."""
        total_frames = 0
        total_duration = 0.0
        type_counts: Dict[str, int] = {}
        action_counts: Dict[str, int] = {}

        for seq in self._sequences.values():
            total_frames += seq.total_frames
            total_duration += seq.duration
            for frame in seq.frames:
                type_counts[frame.input_type] = type_counts.get(frame.input_type, 0) + 1
                action_counts[frame.action] = action_counts.get(frame.action, 0) + 1

        avg_frames_per_sequence = (total_frames / len(self._sequences)) if self._sequences else 0
        return {
            "total_sequences": len(self._sequences),
            "total_frames": total_frames,
            "total_duration": round(total_duration, 4),
            "type_counts": type_counts,
            "action_counts": action_counts,
            "avg_frames_per_sequence": round(avg_frames_per_sequence, 2),
            "desyncs_detected": self._stats.desyncs_detected,
            "desyncs_corrected": self._stats.desyncs_corrected,
            "frames_played": self._stats.total_frames_played,
        }

    def suggest_optimal_inputs(self, sequence_id: str) -> List[Dict[str, Any]]:
        """Suggest input optimizations for a sequence based on pattern analysis."""
        seq = self._resolve_sequence(sequence_id)
        if seq is None:
            return []

        suggestions: List[Dict[str, Any]] = []
        analysis = self.analyze_input_pattern(sequence_id)
        type_counts: Dict[str, int] = analysis.get("type_counts", {})
        action_counts: Dict[str, int] = analysis.get("action_counts", {})

        # Suggestion: reduce redundant consecutive identical inputs
        redundant = 0
        previous_sig: Optional[Dict[str, Any]] = None
        for frame in seq.frames:
            sig = _frame_signature(frame)
            if previous_sig is not None and sig == previous_sig:
                redundant += 1
            previous_sig = sig
        if redundant > 0:
            suggestions.append({
                "kind": "redundant_inputs",
                "count": redundant,
                "suggestion": "Merge consecutive identical inputs to shrink the sequence size.",
            })

        # Suggestion: balance input types if one dominates heavily
        if type_counts:
            dominant = max(type_counts, key=type_counts.get)
            dominant_ratio = type_counts[dominant] / max(1, seq.total_frames)
            if dominant_ratio > 0.7 and len(type_counts) > 1:
                suggestions.append({
                    "kind": "input_diversity",
                    "dominant_type": dominant,
                    "ratio": round(dominant_ratio, 2),
                    "suggestion": "Consider diversifying input sources to reduce reliance on a single device.",
                })

        # Suggestion: flag long holds that could be combined
        holds = [f for f in seq.frames if f.action == InputAction.HOLD.value]
        long_holds = [h for h in holds if h.duration > 0.5]
        if long_holds:
            suggestions.append({
                "kind": "long_holds",
                "count": len(long_holds),
                "max_duration": round(max(h.duration for h in long_holds), 4),
                "suggestion": "Long hold inputs detected; verify they map to intended sustained actions.",
            })

        # Suggestion: detect potential desync risk via checksum coverage
        coverage = len(self._checksums.get(sequence_id, {}))
        coverage_ratio = coverage / max(1, seq.total_frames)
        if coverage_ratio < 0.5:
            suggestions.append({
                "kind": "checksum_coverage",
                "coverage_ratio": round(coverage_ratio, 2),
                "suggestion": "Increase checksum density to improve desync detection fidelity.",
            })

        # Suggestion: total duration optimization for speedrun-style sequences
        if seq.metadata.get("scenario") == "speedrun" and seq.duration > 0:
            actions_per_second = seq.total_frames / seq.duration
            suggestions.append({
                "kind": "actions_per_second",
                "value": round(actions_per_second, 2),
                "suggestion": "Higher actions per second may indicate input density worth optimizing.",
            })

        return suggestions

    # ------------------------------------------------------------------
    # System Operations
    # ------------------------------------------------------------------

    def tick(self, dt: float) -> Dict[str, Any]:
        """Advance the system by ``dt`` seconds, driving recording and playback."""
        with self._init_lock:
            delta = _safe_float(dt, 0.0)
            self._tick_count += 1
            self._stats.tick_count += 1

            recording_status = self._recording_status
            playback_status = PlaybackStatus.IDLE.value
            advanced_frames = 0
            completed = False

            # Advance playback based on elapsed time and speed multiplier
            if self._active_playback is not None:
                state = self._active_playback
                playback_status = state.status
                if state.status == PlaybackStatus.PLAYING.value:
                    seq = self._resolve_playback_sequence()
                    if seq is not None:
                        self._playback_accumulator += delta * state.speed_multiplier
                        step_seconds = _FRAME_STEP_SECONDS
                        while self._playback_accumulator >= step_seconds:
                            self._playback_accumulator -= step_seconds
                            ok, reason, _ = self.advance_frame()
                            if not ok or reason == "playback_completed":
                                if reason == "playback_completed":
                                    completed = True
                                break
                            advanced_frames += 1
                            if state.status != PlaybackStatus.PLAYING.value:
                                break
                        playback_status = state.status

            return {
                "tick": self._tick_count,
                "dt": delta,
                "recording_status": recording_status,
                "playback_status": playback_status,
                "frames_advanced": advanced_frames,
                "playback_completed": completed,
                "active_recording": self._active_recording.session_id if self._active_recording else None,
                "active_playback_sequence": self._playback_sequence_id or None,
            }

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system status."""
        return {
            "initialized": self._initialized,
            "recording_status": self._recording_status,
            "playback_status": self._active_playback.status if self._active_playback else PlaybackStatus.IDLE.value,
            "active_recording": self._active_recording.to_dict() if self._active_recording else None,
            "active_playback": self._active_playback.to_dict() if self._active_playback else None,
            "stored_sequences": len(self._sequences),
            "desync_reports": len(self._desync_reports),
            "tick_count": self._tick_count,
        }

    def get_stats(self) -> InputReplayStats:
        """Return aggregate statistics for the system."""
        return self._stats

    def get_snapshot(self) -> InputReplaySnapshot:
        """Return a full snapshot of the system state."""
        return InputReplaySnapshot(
            sequences=[self._sequence_summary(seq) for seq in self._sequences.values()],
            active_recording=self._active_recording.to_dict() if self._active_recording else None,
            active_playback=self._active_playback.to_dict() if self._active_playback else None,
            desync_reports=[r.to_dict() for r in self._desync_reports],
            events=[e.to_dict() for e in self._events[-100:]],
        )

    def get_config(self) -> InputReplayConfig:
        """Return the current configuration."""
        return self._config

    def set_config(self, **kwargs: Any) -> Tuple[bool, str, InputReplayConfig]:
        """Update configuration fields and return the resulting configuration."""
        with self._init_lock:
            if not kwargs:
                return False, "no_fields_provided", self._config
            updated: List[str] = []
            for key, value in kwargs.items():
                if not hasattr(self._config, key):
                    continue
                if key == "max_recording_length":
                    value = max(1, _safe_int(value, self._config.max_recording_length))
                elif key == "checksum_interval":
                    value = max(1, _safe_int(value, self._config.checksum_interval))
                elif key == "playback_speed_default":
                    value = _clamp(
                        _safe_float(value, self._config.playback_speed_default),
                        _MIN_PLAYBACK_SPEED,
                        _MAX_PLAYBACK_SPEED,
                    )
                elif key in ("auto_checksum", "enable_desync_detection", "enable_frame_correction"):
                    value = bool(value)
                elif key == "max_desync_corrections":
                    value = max(0, _safe_int(value, self._config.max_desync_corrections))
                else:
                    value = value
                setattr(self._config, key, value)
                updated.append(key)
            if not updated:
                return False, "no_valid_fields", self._config
            self._record_event(
                ReplayEventKind.RECORDING_STARTED,
                {"action": "set_config", "fields": updated},
            )
            return True, "config_updated", self._config

    def list_events(self, limit: int = 100) -> List[ReplayEvent]:
        """Return the most recent audit events, newest last."""
        cap = max(1, int(limit))
        if cap >= len(self._events):
            return list(self._events)
        return list(self._events[-cap:])

    def reset(self) -> Dict[str, Any]:
        """Reset the system to its seeded state."""
        with self._init_lock:
            self._active_recording = None
            self._recording_buffer = []
            self._recording_status = RecordingStatus.IDLE.value
            self._recording_frame_index = 0
            self._recording_start_time = 0.0
            self._recording_pause_time = 0.0
            self._recording_paused_total = 0.0
            self._recording_game_state_hash = ""
            self._recording_player_id = "player_01"
            self._active_playback = None
            self._playback_sequence_id = ""
            self._playback_accumulator = 0.0
            self._correction_counter = 0
            self._initialized = False
            self._seed()
        return {"reset": True, "initialized": self._initialized}


# ---------------------------------------------------------------------------
# Module-Level Factory
# ---------------------------------------------------------------------------

def get_input_replay_system() -> InputReplaySystem:
    """Return the singleton InputReplaySystem instance."""
    return InputReplaySystem.get_instance()
