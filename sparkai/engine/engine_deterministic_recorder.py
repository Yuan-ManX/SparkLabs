"""
SparkLabs Engine - Deterministic Recorder

A singleton deterministic gameplay recording and replay system
for the SparkLabs game engine. Captures player inputs, random
seeds, and system state snapshots to enable perfect replay,
ghost playback, and debugging reconstruction.

Architecture:
  DeterministicRecorder (singleton)
    |-- FrameInput (per-tick input capture: keys, mouse, gamepad)
    |-- StateSnapshot (periodic full state for seek/reconstruction)
    |-- RecordSession (container for a full recording run)
    |-- ReplayController (active playback state machine)
"""

from __future__ import annotations

import math
import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


_time_module = time


class RecordMode(Enum):
    INPUT_ONLY = "input_only"
    FULL_STATE = "full_state"
    HYBRID = "hybrid"
    GHOST = "ghost"


class ReplaySpeed(Enum):
    PAUSE = "pause"
    SLOW = "slow"
    NORMAL = "normal"
    FAST = "fast"
    INSTANT = "instant"


class RecordStatus(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    SAVING = "saving"
    READY = "ready"
    REPLAYING = "replaying"


MAX_RECORD_TICKS: int = 18000
SNAPSHOT_INTERVAL: int = 60
MAX_SNAPSHOT_SIZE: int = 10485760


@dataclass
class FrameInput:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tick: int = 0
    delta_time: float = 0.0
    keys: Dict[str, bool] = field(default_factory=dict)
    mouse_pos: Tuple[float, float] = (0.0, 0.0)
    mouse_buttons: Dict[str, bool] = field(default_factory=dict)
    gamepad_state: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "delta_time": self.delta_time,
            "keys": dict(self.keys),
            "mouse_pos": self.mouse_pos,
            "mouse_buttons": dict(self.mouse_buttons),
            "gamepad_state": dict(self.gamepad_state),
            "timestamp": self.timestamp,
        }


@dataclass
class StateSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    tick: int = 0
    entities: List[Dict[str, Any]] = field(default_factory=list)
    random_seed: int = 0
    game_time: float = 0.0
    physics_step: int = 0
    camera_state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tick": self.tick,
            "entities": [dict(e) for e in self.entities],
            "random_seed": self.random_seed,
            "game_time": self.game_time,
            "physics_step": self.physics_step,
            "camera_state": dict(self.camera_state),
        }


@dataclass
class RecordSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    mode: RecordMode = RecordMode.HYBRID
    status: RecordStatus = RecordStatus.IDLE
    start_tick: int = 0
    end_tick: int = 0
    tick_count: int = 0
    frames: List[FrameInput] = field(default_factory=list)
    snapshots: List[StateSnapshot] = field(default_factory=list)
    random_seed_sequence: List[int] = field(default_factory=list)
    file_size_bytes: int = 0
    duration_seconds: float = 0.0
    tags: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "mode": self.mode.value,
            "status": self.status.value,
            "start_tick": self.start_tick,
            "end_tick": self.end_tick,
            "tick_count": self.tick_count,
            "frames_count": len(self.frames),
            "snapshots_count": len(self.snapshots),
            "file_size_bytes": self.file_size_bytes,
            "duration_seconds": self.duration_seconds,
            "tags": list(self.tags),
            "created_at": self.created_at,
        }


@dataclass
class ReplayController:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    current_tick: int = 0
    speed: ReplaySpeed = ReplaySpeed.NORMAL
    is_looping: bool = False
    playback_position: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "current_tick": self.current_tick,
            "speed": self.speed.value,
            "is_looping": self.is_looping,
            "playback_position": self.playback_position,
        }


SPEED_MULTIPLIERS: Dict[ReplaySpeed, float] = {
    ReplaySpeed.PAUSE: 0.0,
    ReplaySpeed.SLOW: 0.5,
    ReplaySpeed.NORMAL: 1.0,
    ReplaySpeed.FAST: 2.0,
    ReplaySpeed.INSTANT: float("inf"),
}


class DeterministicRecorder:
    """Singleton deterministic gameplay recording and replay system.

    Captures player inputs, random seeds, and system state snapshots
    to enable perfect replay, ghost playback, and debugging
    reconstruction of any gameplay session.
    """

    _instance: Optional[DeterministicRecorder] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> DeterministicRecorder:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> DeterministicRecorder:
        if cls._instance is None:
            cls()
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._sessions: List[RecordSession] = []
        self._active_session: Optional[RecordSession] = None
        self._replay_controllers: Dict[str, ReplayController] = {}
        self._recording_paused: bool = False
        self._tick_counter: int = 0

    def _get_or_create_singleton(self) -> DeterministicRecorder:
        return self.get_instance()

    def get_stats(self) -> Dict[str, Any]:
        total_frames = sum(len(s.frames) for s in self._sessions)
        total_snapshots = sum(len(s.snapshots) for s in self._sessions)
        total_size = sum(s.file_size_bytes for s in self._sessions)
        return {
            "total_sessions": len(self._sessions),
            "active_session": self._active_session.id if self._active_session else None,
            "is_recording": self._active_session is not None and self._active_session.status == RecordStatus.RECORDING,
            "is_replaying": len(self._replay_controllers) > 0,
            "active_replays": len(self._replay_controllers),
            "total_recorded_frames": total_frames,
            "total_snapshots": total_snapshots,
            "total_size_bytes": total_size,
            "recording_paused": self._recording_paused,
        }

    def start_recording(
        self, name: str, mode: str = "hybrid", tags: Optional[List[str]] = None
    ) -> RecordSession:
        if self._active_session is not None and self._active_session.status == RecordStatus.RECORDING:
            raise RuntimeError("A recording session is already active. Stop it before starting a new one.")

        session = RecordSession(
            name=name,
            mode=RecordMode(mode),
            status=RecordStatus.RECORDING,
            tags=tags if tags else [],
        )
        self._active_session = session
        self._tick_counter = 0
        self._recording_paused = False
        return session

    def record_frame(
        self,
        tick: int,
        delta_time: float,
        keys: Dict[str, bool],
        mouse_pos: Tuple[float, float],
        mouse_buttons: Dict[str, bool],
        gamepad_state: Optional[Dict[str, Any]] = None,
    ) -> FrameInput:
        if self._active_session is None or self._active_session.status != RecordStatus.RECORDING:
            raise RuntimeError("No active recording session.")
        if self._recording_paused:
            raise RuntimeError("Recording is paused. Resume before recording frames.")
        if tick > MAX_RECORD_TICKS:
            raise RuntimeError(f"Tick {tick} exceeds maximum record ticks of {MAX_RECORD_TICKS}.")

        frame = FrameInput(
            tick=tick,
            delta_time=delta_time,
            keys=dict(keys),
            mouse_pos=mouse_pos,
            mouse_buttons=dict(mouse_buttons),
            gamepad_state=dict(gamepad_state) if gamepad_state else {},
        )

        if self._active_session.start_tick == 0 and tick > 0:
            self._active_session.start_tick = tick
            if len(self._active_session.frames) == 0:
                self._active_session.start_tick = tick

        if not self._active_session.frames:
            self._active_session.start_tick = tick

        self._active_session.frames.append(frame)
        self._active_session.end_tick = tick
        self._active_session.tick_count = self._active_session.end_tick - self._active_session.start_tick + 1

        return frame

    def capture_snapshot(
        self,
        tick: int,
        entities: List[Dict[str, Any]],
        random_seed: int,
        game_time: float,
        physics_step: int,
        camera_state: Optional[Dict[str, Any]] = None,
    ) -> StateSnapshot:
        if self._active_session is None:
            raise RuntimeError("No active session.")

        import sys

        snapshot = StateSnapshot(
            tick=tick,
            entities=entities,
            random_seed=random_seed,
            game_time=game_time,
            physics_step=physics_step,
            camera_state=dict(camera_state) if camera_state else {},
        )

        snapshot_size = sys.getsizeof(str(snapshot.to_dict()))
        if snapshot_size > MAX_SNAPSHOT_SIZE:
            raise RuntimeError(
                f"Snapshot size {snapshot_size} exceeds maximum of {MAX_SNAPSHOT_SIZE} bytes."
            )

        self._active_session.snapshots.append(snapshot)
        return snapshot

    def stop_recording(self) -> Optional[RecordSession]:
        if self._active_session is None:
            return None

        session = self._active_session
        session.status = RecordStatus.SAVING
        session.duration_seconds = _time_module.time() - session.created_at
        session.file_size_bytes = self._serialize_session(session)
        session.status = RecordStatus.READY

        self._sessions.append(session)
        self._active_session = None
        self._recording_paused = False
        self._tick_counter = 0

        return session

    def start_replay(
        self, session_id: str, speed: str = "normal", looping: bool = False
    ) -> Optional[ReplayController]:
        session = None
        for s in self._sessions:
            if s.id == session_id:
                session = s
                break

        if session is None:
            return None

        controller = ReplayController(
            session_id=session_id,
            current_tick=session.start_tick,
            speed=ReplaySpeed(speed),
            is_looping=looping,
            playback_position=0.0,
        )

        session.status = RecordStatus.REPLAYING
        self._replay_controllers[controller.id] = controller
        return controller

    def get_next_frame(self, controller_id: str) -> Optional[Dict[str, Any]]:
        controller = self._replay_controllers.get(controller_id)
        if controller is None:
            return None

        session = None
        for s in self._sessions:
            if s.id == controller.session_id:
                session = s
                break

        if session is None:
            return None

        frame_index = None
        for i, f in enumerate(session.frames):
            if f.tick == controller.current_tick:
                frame_index = i
                break

        if frame_index is None and session.frames:
            frame_index = 0
            controller.current_tick = session.frames[0].tick

        if frame_index is None:
            return None

        result = session.frames[frame_index].to_dict()

        nearest_snapshot = None
        for snap in session.snapshots:
            if snap.tick <= controller.current_tick:
                nearest_snapshot = snap

        if nearest_snapshot:
            result["snapshot"] = nearest_snapshot.to_dict()

        total_ticks = session.end_tick - session.start_tick
        if total_ticks > 0:
            controller.playback_position = (controller.current_tick - session.start_tick) / total_ticks

        speed_mult = SPEED_MULTIPLIERS.get(controller.speed, 1.0)
        ticks_to_advance = max(1, int(speed_mult))

        next_tick = controller.current_tick + ticks_to_advance
        if next_tick > session.end_tick:
            if controller.is_looping:
                controller.current_tick = session.start_tick
                controller.playback_position = 0.0
            else:
                controller.current_tick = session.end_tick
                controller.playback_position = 1.0
        else:
            controller.current_tick = next_tick

        return result

    def seek_replay(self, controller_id: str, tick: int) -> Optional[Dict[str, Any]]:
        controller = self._replay_controllers.get(controller_id)
        if controller is None:
            return None

        session = None
        for s in self._sessions:
            if s.id == controller.session_id:
                session = s
                break

        if session is None:
            return None

        tick = max(session.start_tick, min(tick, session.end_tick))
        controller.current_tick = tick

        total_ticks = session.end_tick - session.start_tick
        if total_ticks > 0:
            controller.playback_position = (controller.current_tick - session.start_tick) / total_ticks

        nearest_frame = None
        for f in session.frames:
            if f.tick <= tick:
                nearest_frame = f

        nearest_snapshot = None
        for snap in session.snapshots:
            if snap.tick <= tick:
                nearest_snapshot = snap

        result: Dict[str, Any] = {}
        if nearest_frame:
            result = nearest_frame.to_dict()
        if nearest_snapshot:
            result["snapshot"] = nearest_snapshot.to_dict()

        return result if result else None

    def pause_replay(self, controller_id: str) -> bool:
        controller = self._replay_controllers.get(controller_id)
        if controller is None:
            return False
        controller.speed = ReplaySpeed.PAUSE
        return True

    def resume_replay(self, controller_id: str) -> bool:
        controller = self._replay_controllers.get(controller_id)
        if controller is None:
            return False
        if controller.speed == ReplaySpeed.PAUSE:
            controller.speed = ReplaySpeed.NORMAL
        return True

    def stop_replay(self, controller_id: str) -> bool:
        controller = self._replay_controllers.pop(controller_id, None)
        if controller is None:
            return False

        for s in self._sessions:
            if s.id == controller.session_id:
                s.status = RecordStatus.READY
                break

        return True

    def list_sessions(self) -> List[RecordSession]:
        return list(self._sessions)

    def _serialize_session(self, session: RecordSession) -> int:
        import json
        import sys

        raw = json.dumps({
            "id": session.id,
            "name": session.name,
            "mode": session.mode.value,
            "start_tick": session.start_tick,
            "end_tick": session.end_tick,
            "tick_count": session.tick_count,
            "frames": [f.to_dict() for f in session.frames],
            "snapshots": [s.to_dict() for s in session.snapshots],
            "random_seed_sequence": list(session.random_seed_sequence),
            "tags": list(session.tags),
            "created_at": session.created_at,
            "duration_seconds": session.duration_seconds,
        })

        return sys.getsizeof(raw)


def get_deterministic_recorder() -> DeterministicRecorder:
    return DeterministicRecorder.get_instance()