"""
SparkLabs Engine - Input Recorder

Records and replays player inputs for testing, debugging, and
automated QA. Captures keyboard, mouse, touch, and gamepad
events with precise timing, enabling deterministic replay
of gameplay sessions for bug reproduction and AI training.

Architecture:
  InputRecorder
    |-- RecordingSession (capture input events with timestamps)
    |-- ReplaySession (playback recorded inputs)
    |-- InputSerializer (save/load recording files)
    |-- TimeKeeper (frame-accurate event timing)
    |-- DeltaCompressor (remove redundant idle frames)

Recording Modes:
  - RECORD: capture live input events
  - REPLAY: playback recorded events deterministically
  - GHOST: overlay ghost inputs on live gameplay
  - COMPARE: side-by-side comparison of two recordings
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class InputEventType(Enum):
    KEY_DOWN = "key_down"
    KEY_UP = "key_up"
    MOUSE_DOWN = "mouse_down"
    MOUSE_UP = "mouse_up"
    MOUSE_MOVE = "mouse_move"
    MOUSE_WHEEL = "mouse_wheel"
    TOUCH_START = "touch_start"
    TOUCH_MOVE = "touch_move"
    TOUCH_END = "touch_end"
    GAMEPAD_BUTTON = "gamepad_button"
    GAMEPAD_AXIS = "gamepad_axis"


class RecorderMode(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    REPLAYING = "replaying"
    GHOST = "ghost"


@dataclass
class InputEvent:
    event_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    event_type: InputEventType = InputEventType.KEY_DOWN
    code: int = 0
    value: float = 0.0
    x: float = 0.0
    y: float = 0.0
    frame: int = 0
    timestamp: float = field(default_factory=time.time)
    delta_from_start: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "type": self.event_type.value,
            "code": self.code,
            "value": self.value,
            "x": self.x,
            "y": self.y,
            "frame": self.frame,
            "delta_from_start": round(self.delta_from_start, 4),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InputEvent":
        event_type = data.get("type", "key_down")
        try:
            et = InputEventType(event_type)
        except ValueError:
            et = InputEventType.KEY_DOWN
        return cls(
            event_type=et,
            code=data.get("code", 0),
            value=data.get("value", 0.0),
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            frame=data.get("frame", 0),
            delta_from_start=data.get("delta_from_start", 0.0),
        )


@dataclass
class RecordingSession:
    session_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    events: List[InputEvent] = field(default_factory=list)
    start_time: float = 0.0
    duration_seconds: float = 0.0
    frame_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def event_count(self) -> int:
        return len(self.events)

    def get_events_for_frame(self, frame: int) -> List[InputEvent]:
        return [e for e in self.events if e.frame == frame]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "name": self.name,
            "event_count": self.event_count,
            "duration_s": round(self.duration_seconds, 2),
            "frame_count": self.frame_count,
            "metadata": self.metadata,
        }

    def to_full_dict(self) -> Dict[str, Any]:
        return {
            **self.to_dict(),
            "events": [e.to_dict() for e in self.events],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_full_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "RecordingSession":
        data = json.loads(json_str)
        session = cls(
            session_id=data.get("session_id", ""),
            name=data.get("name", ""),
            duration_seconds=data.get("duration_s", 0.0),
            frame_count=data.get("frame_count", 0),
            metadata=data.get("metadata", {}),
        )
        session.events = [
            InputEvent.from_dict(e) for e in data.get("events", [])
        ]
        return session


class InputRecorder:
    """Input recording and replay for game testing and debugging."""

    _instance: Optional["InputRecorder"] = None
    _lock = threading.Lock()

    MAX_RECORDINGS = 50
    MAX_EVENTS_PER_SESSION = 100000

    def __init__(self):
        self._recordings: Dict[str, RecordingSession] = {}
        self._active_session: Optional[RecordingSession] = None
        self._replay_session: Optional[RecordingSession] = None
        self._mode: RecorderMode = RecorderMode.IDLE
        self._replay_index: int = 0
        self._frame_counter: int = 0
        self._start_time: float = 0.0

    @classmethod
    def get_instance(cls) -> "InputRecorder":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def start_recording(self, name: str = "") -> RecordingSession:
        session = RecordingSession(name=name)
        session.start_time = time.time()
        self._recordings[session.session_id] = session
        self._active_session = session
        self._mode = RecorderMode.RECORDING
        self._frame_counter = 0
        self._start_time = time.time()
        return session

    def stop_recording(self) -> Optional[RecordingSession]:
        if self._active_session:
            self._active_session.duration_seconds = time.time() - self._active_session.start_time
            self._active_session.frame_count = self._frame_counter
        session = self._active_session
        self._active_session = None
        self._mode = RecorderMode.IDLE
        return session

    def record_event(
        self,
        event_type: InputEventType,
        code: int = 0,
        value: float = 0.0,
        x: float = 0.0,
        y: float = 0.0,
    ) -> Optional[InputEvent]:
        if self._mode != RecorderMode.RECORDING or not self._active_session:
            return None
        if len(self._active_session.events) >= self.MAX_EVENTS_PER_SESSION:
            return None

        event = InputEvent(
            event_type=event_type,
            code=code,
            value=value,
            x=x,
            y=y,
            frame=self._frame_counter,
            delta_from_start=time.time() - self._start_time,
        )
        self._active_session.events.append(event)
        return event

    def advance_frame(self) -> None:
        self._frame_counter += 1

    def get_current_frame_events(self) -> List[InputEvent]:
        if self._mode != RecorderMode.REPLAYING or not self._replay_session:
            return []
        events = []
        while (
            self._replay_index < len(self._replay_session.events)
            and self._replay_session.events[self._replay_index].frame == self._frame_counter
        ):
            events.append(self._replay_session.events[self._replay_index])
            self._replay_index += 1
        return events

    def start_replay(self, session_id: str) -> bool:
        session = self._recordings.get(session_id)
        if not session:
            return False
        self._replay_session = session
        self._mode = RecorderMode.REPLAYING
        self._replay_index = 0
        self._frame_counter = 0
        return True

    def stop_replay(self) -> None:
        self._replay_session = None
        self._replay_index = 0
        self._mode = RecorderMode.IDLE

    def is_replay_finished(self) -> bool:
        if not self._replay_session:
            return True
        return self._replay_index >= len(self._replay_session.events)

    def save_recording(self, session_id: str) -> Optional[str]:
        session = self._recordings.get(session_id)
        if not session:
            return None
        return session.to_json()

    def load_recording(self, json_str: str) -> Optional[RecordingSession]:
        session = RecordingSession.from_json(json_str)
        self._recordings[session.session_id] = session
        return session

    def get_recording(self, session_id: str) -> Optional[RecordingSession]:
        return self._recordings.get(session_id)

    def list_recordings(self) -> List[RecordingSession]:
        return list(self._recordings.values())

    def delete_recording(self, session_id: str) -> bool:
        if session_id in self._recordings:
            if self._active_session and self._active_session.session_id == session_id:
                self._active_session = None
                self._mode = RecorderMode.IDLE
            del self._recordings[session_id]
            return True
        return False

    def get_mode(self) -> RecorderMode:
        return self._mode

    def get_stats(self) -> Dict[str, Any]:
        total_events = sum(r.event_count for r in self._recordings.values())
        total_duration = sum(r.duration_seconds for r in self._recordings.values())
        return {
            "recordings": len(self._recordings),
            "total_events": total_events,
            "total_duration_s": round(total_duration, 2),
            "mode": self._mode.value,
            "active_session": self._active_session.session_id if self._active_session else None,
            "replay_session": self._replay_session.session_id if self._replay_session else None,
            "frame_counter": self._frame_counter,
        }


def get_input_recorder() -> InputRecorder:
    return InputRecorder.get_instance()