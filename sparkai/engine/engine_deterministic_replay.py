"""
SparkLabs Engine - Deterministic Replay

Provides deterministic game replay recording and playback. Captures
all input events, random seeds, and game state transitions frame-by-frame
so that entire gameplay sessions can be exactly replayed. Useful for
debugging, testing, and replay sharing.

Architecture:
  DeterministicReplay (singleton)
    |-- Recording: frames + events + random seeds captured
    |-- Snapshots: periodic full game-state captures for seeking
    |-- Playback: replay recorded sessions at configurable speed
    |-- Session management: list, query, delete recorded sessions

Event Categories:
  - INPUT: keyboard, mouse, gamepad, touch events
  - PHYSICS_STEP: per-physics-tick determinism markers
  - RANDOM_CALL: seed + parameters for random number generation
  - AI_DECISION: agent decision output with input context hash
  - NETWORK_EVENT: incoming packet data with timestamp
  - SPAWN / DESTROY: entity lifecycle events
  - STATE_SNAPSHOT: full or delta state capture
  - CUSTOM: user-defined game-specific events

Replay Flow:
  1. start_recording(name, random_seed) begins a new session
  2. record_event(frame_number, category, data) per-frame
  3. capture_snapshot(...) periodically for seeking support
  4. stop_recording() finalizes and stores the session
  5. start_playback(session_id, speed) replays events frame-by-frame
  6. seek_to_frame(session_id, frame) jumps to specific frame
"""

from __future__ import annotations

import bisect
import hashlib
import json
import threading
import time
import uuid
import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

_time_module = time


class ReplayState(Enum):
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    PLAYING = "playing"
    SEEKING = "seeking"


class EventCategory(Enum):
    INPUT = "input"
    PHYSICS_STEP = "physics_step"
    RANDOM_CALL = "random_call"
    AI_DECISION = "ai_decision"
    NETWORK_EVENT = "network_event"
    SPAWN = "spawn"
    DESTROY = "destroy"
    STATE_SNAPSHOT = "state_snapshot"
    CUSTOM = "custom"


class PlaybackSpeed(Enum):
    SLOW_05X = (0.5, "0.5x")
    NORMAL_1X = (1.0, "1x")
    FAST_2X = (2.0, "2x")
    FAST_4X = (4.0, "4x")
    MAX = (float("inf"), "max")

    def __init__(self, multiplier: float, label: str):
        self._multiplier = multiplier
        self._label = label

    @property
    def multiplier(self) -> float:
        return self._multiplier


class SnapFrequency(Enum):
    EVERY_FRAME = 1
    EVERY_10_FRAMES = 10
    EVERY_60_FRAMES = 60
    EVERY_300_FRAMES = 300
    MANUAL_ONLY = -1


@dataclass
class ReplayEvent:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    category: EventCategory = EventCategory.CUSTOM
    event_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "category": self.category.value,
            "event_data": self.event_data,
            "timestamp": self.timestamp,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayEvent":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            frame_number=data.get("frame_number", 0),
            category=EventCategory(data.get("category", "custom")),
            event_data=data.get("event_data", {}),
            timestamp=data.get("timestamp", 0.0),
            created_at=data.get("created_at", _time_module.time()),
        )


@dataclass
class ReplaySession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    state: ReplayState = ReplayState.IDLE
    initial_random_seed: int = 42
    frame_count: int = 0
    event_count: int = 0
    duration_seconds: float = 0.0
    snap_frequency: SnapFrequency = SnapFrequency.EVERY_60_FRAMES
    created_at: float = field(default_factory=_time_module.time)
    ended_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "state": self.state.value,
            "initial_random_seed": self.initial_random_seed,
            "frame_count": self.frame_count,
            "event_count": self.event_count,
            "duration_seconds": self.duration_seconds,
            "snap_frequency": self.snap_frequency.name,
            "created_at": self.created_at,
            "ended_at": self.ended_at,
        }


@dataclass
class StateSnapshot:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    frame_number: int = 0
    game_state_hash: str = ""
    full_state: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "frame_number": self.frame_number,
            "game_state_hash": self.game_state_hash,
            "full_state": self.full_state,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            session_id=data.get("session_id", ""),
            frame_number=data.get("frame_number", 0),
            game_state_hash=data.get("game_state_hash", ""),
            full_state=data.get("full_state", {}),
            created_at=data.get("created_at", _time_module.time()),
        )


class DeterministicReplay:
    """Singleton that provides deterministic game replay recording and playback.

    Captures all input events, random seeds, and game state transitions
    frame-by-frame so that entire gameplay sessions can be exactly replayed.
    """

    _instance: Optional["DeterministicReplay"] = None
    _lock = threading.RLock()

    MAX_EVENTS_PER_SESSION = 500000
    MAX_SNAPSHOTS_PER_SESSION = 10000
    MAX_SESSIONS = 500

    def __new__(cls) -> "DeterministicReplay":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._sessions: Dict[str, ReplaySession] = {}
                    instance._events: Dict[str, List[ReplayEvent]] = {}
                    instance._snapshots: Dict[str, List[StateSnapshot]] = {}
                    instance._current_recording_id: Optional[str] = None
                    instance._current_playback_id: Optional[str] = None
                    instance._recording_start_time: float = 0.0
                    instance._playback_frame: int = 0
                    instance._playback_speed: PlaybackSpeed = PlaybackSpeed.NORMAL_1X
                    instance._playback_start_real_time: float = 0.0
                    instance._playback_start_game_time: float = 0.0
                    instance._frame_event_index: Dict[str, List[int]] = {}
                    instance._pending_debug_lines: List[str] = []
                    cls._instance = instance
        return cls._instance

    @classmethod
    def get_instance(cls) -> "DeterministicReplay":
        return cls()

    # -- Recording --
    # ------------------------------------------------------------------

    def start_recording(
        self,
        name: str = "",
        random_seed: int = 42,
        snap_frequency: SnapFrequency = SnapFrequency.EVERY_60_FRAMES,
    ) -> ReplaySession:
        with self._lock:
            if self._current_recording_id is not None:
                self.stop_recording()

            session = ReplaySession(
                name=name or f"session_{uuid.uuid4().hex[:8]}",
                state=ReplayState.RECORDING,
                initial_random_seed=random_seed,
                snap_frequency=snap_frequency,
            )
            session_id = session.id
            self._sessions[session_id] = session
            self._events[session_id] = []
            self._snapshots[session_id] = []
            self._frame_event_index[session_id] = []
            self._current_recording_id = session_id
            self._recording_start_time = _time_module.time()
            return session

    def stop_recording(self) -> Optional[ReplaySession]:
        with self._lock:
            session_id = self._current_recording_id
            if session_id is None:
                return None

            session = self._sessions.get(session_id)
            if session is None:
                self._current_recording_id = None
                return None

            session.ended_at = _time_module.time()
            session.duration_seconds = session.ended_at - self._recording_start_time
            session.event_count = len(self._events.get(session_id, []))
            session.state = ReplayState.IDLE

            self._current_recording_id = None
            self._recording_start_time = 0.0
            self._enforce_session_limit()
            return session

    def record_event(
        self,
        frame_number: int,
        category: EventCategory,
        event_data: Dict[str, Any],
    ) -> Optional[ReplayEvent]:
        session_id = self._current_recording_id
        if session_id is None:
            return None
        if session_id not in self._sessions:
            return None
        if self._sessions[session_id].state != ReplayState.RECORDING:
            return None

        elapsed = _time_module.time() - self._recording_start_time
        event = ReplayEvent(
            frame_number=frame_number,
            category=category,
            event_data=event_data,
            timestamp=elapsed,
        )

        with self._lock:
            events = self._events.get(session_id)
            if events is None:
                return None
            if len(events) >= self.MAX_EVENTS_PER_SESSION:
                return None

            events.append(event)
            self._sessions[session_id].frame_count = max(
                self._sessions[session_id].frame_count, frame_number
            )
            events_len = len(events)
            frame_index = self._frame_event_index.get(session_id, [])
            if events_len > len(frame_index):
                frame_index.append(frame_number)
            return event

    def record_random_call(
        self,
        call_site: str,
        min_val: float,
        max_val: float,
        result: float,
    ) -> Optional[ReplayEvent]:
        return self.record_event(
            frame_number=0,
            category=EventCategory.RANDOM_CALL,
            event_data={
                "call_site": call_site,
                "min_val": min_val,
                "max_val": max_val,
                "result": result,
            },
        )

    def capture_snapshot(
        self,
        session_id: str,
        frame_number: int,
        game_state: Dict[str, Any],
    ) -> Optional[StateSnapshot]:
        with self._lock:
            if session_id not in self._sessions:
                return None

            state_json = json.dumps(game_state, sort_keys=True, default=str)
            state_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()

            snapshot = StateSnapshot(
                session_id=session_id,
                frame_number=frame_number,
                game_state_hash=state_hash,
                full_state=copy.deepcopy(game_state),
            )

            snapshots = self._snapshots.get(session_id)
            if snapshots is None:
                return None
            if len(snapshots) >= self.MAX_SNAPSHOTS_PER_SESSION:
                return None

            snapshots.append(snapshot)
            return snapshot

    def _auto_capture_snapshot(
        self,
        session_id: str,
        frame_number: int,
        game_state: Dict[str, Any],
    ) -> Optional[StateSnapshot]:
        session = self._sessions.get(session_id)
        if session is None:
            return None

        freq = session.snap_frequency
        if freq == SnapFrequency.MANUAL_ONLY:
            return None
        if freq.value == -1:
            return None
        if frame_number == 0:
            return self.capture_snapshot(session_id, frame_number, game_state)
        if frame_number % freq.value == 0:
            return self.capture_snapshot(session_id, frame_number, game_state)
        return None

    # -- Playback --
    # ------------------------------------------------------------------

    def start_playback(
        self,
        session_id: str,
        speed: PlaybackSpeed = PlaybackSpeed.NORMAL_1X,
    ) -> Optional[ReplaySession]:
        with self._lock:
            if session_id not in self._sessions:
                return None

            if self._current_playback_id is not None:
                self.stop_playback()

            session = self._sessions[session_id]
            session.state = ReplayState.PLAYING

            self._current_playback_id = session_id
            self._playback_frame = 0
            self._playback_speed = speed
            self._playback_start_real_time = _time_module.time()
            self._playback_start_game_time = 0.0
            return session

    def stop_playback(self) -> Optional[ReplaySession]:
        with self._lock:
            session_id = self._current_playback_id
            if session_id is None:
                return None

            session = self._sessions.get(session_id)
            if session is not None:
                session.state = ReplayState.IDLE

            self._current_playback_id = None
            self._playback_frame = 0
            self._playback_speed = PlaybackSpeed.NORMAL_1X
            self._playback_start_real_time = 0.0
            self._playback_start_game_time = 0.0
            return session

    def seek_to_frame(self, session_id: str, frame_number: int) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False

            session = self._sessions[session_id]
            previous_state = session.state
            session.state = ReplayState.SEEKING

            snapshot = self.get_nearest_snapshot(session_id, frame_number)
            if snapshot is not None:
                self._playback_frame = snapshot.frame_number
            else:
                self._playback_frame = 0

            if previous_state == ReplayState.PLAYING:
                self._playback_start_real_time = _time_module.time()
                self._playback_start_game_time = 0.0

            session.state = previous_state
            return True

    def get_current_playback_frame(self) -> int:
        session_id = self._current_playback_id
        if session_id is None:
            return 0

        real_elapsed = _time_module.time() - self._playback_start_real_time
        if self._playback_speed == PlaybackSpeed.MAX:
            session = self._sessions.get(session_id)
            if session is not None:
                return session.frame_count

        game_elapsed = real_elapsed * self._playback_speed.multiplier
        estimated_frame = int(game_elapsed * 60)
        session = self._sessions.get(session_id)
        if session is not None and estimated_frame > session.frame_count:
            estimated_frame = session.frame_count
        return estimated_frame

    def get_playback_progress(self) -> Tuple[int, int, float]:
        session_id = self._current_playback_id
        if session_id is None:
            return (0, 0, 0.0)

        current_frame = self.get_current_playback_frame()
        session = self._sessions.get(session_id)
        if session is None or session.frame_count == 0:
            return (current_frame, 0, 0.0)
        progress = current_frame / session.frame_count if session.frame_count > 0 else 0.0
        return (current_frame, session.frame_count, min(progress, 1.0))

    # -- Queries --
    # ------------------------------------------------------------------

    def get_events_for_frame(
        self,
        session_id: str,
        frame_number: int,
    ) -> List[ReplayEvent]:
        with self._lock:
            events = self._events.get(session_id)
            if not events:
                return []
            return [e for e in events if e.frame_number == frame_number]

    def get_events_range(
        self,
        session_id: str,
        start_frame: int,
        end_frame: int,
    ) -> List[ReplayEvent]:
        with self._lock:
            events = self._events.get(session_id)
            if not events:
                return []
            return [e for e in events if start_frame <= e.frame_number <= end_frame]

    def get_snapshot(
        self,
        session_id: str,
        frame_number: int,
    ) -> Optional[StateSnapshot]:
        with self._lock:
            snapshots = self._snapshots.get(session_id)
            if not snapshots:
                return None
            for snap in snapshots:
                if snap.frame_number == frame_number:
                    return snap
            return None

    def get_nearest_snapshot(
        self,
        session_id: str,
        frame_number: int,
    ) -> Optional[StateSnapshot]:
        with self._lock:
            snapshots = self._snapshots.get(session_id)
            if not snapshots:
                return None

            best: Optional[StateSnapshot] = None
            for snap in snapshots:
                if snap.frame_number <= frame_number:
                    if best is None or snap.frame_number > best.frame_number:
                        best = snap
            return best

    def get_session(self, session_id: str) -> Optional[ReplaySession]:
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self) -> List[ReplaySession]:
        with self._lock:
            return list(self._sessions.values())

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            if session_id not in self._sessions:
                return False

            if self._current_recording_id == session_id:
                self._current_recording_id = None
                self._recording_start_time = 0.0

            if self._current_playback_id == session_id:
                self._current_playback_id = None
                self._playback_frame = 0
                self._playback_speed = PlaybackSpeed.NORMAL_1X
                self._playback_start_real_time = 0.0
                self._playback_start_game_time = 0.0

            self._sessions.pop(session_id, None)
            self._events.pop(session_id, None)
            self._snapshots.pop(session_id, None)
            self._frame_event_index.pop(session_id, None)
            return True

    # -- Stats --
    # ------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_events = sum(len(evts) for evts in self._events.values())
            total_snapshots = sum(len(snaps) for snaps in self._snapshots.values())
            total_memory_estimate = self._estimate_memory_usage()

            session_states: Dict[str, int] = {}
            for session in self._sessions.values():
                state_key = session.state.value
                session_states[state_key] = session_states.get(state_key, 0) + 1

            largest_session: Optional[Dict[str, Any]] = None
            for session in self._sessions.values():
                evt_count = len(self._events.get(session.id, []))
                if largest_session is None or evt_count > largest_session.get("event_count", 0):
                    largest_session = {
                        "session_id": session.id,
                        "session_name": session.name,
                        "event_count": evt_count,
                        "frame_count": session.frame_count,
                        "duration_seconds": session.duration_seconds,
                    }

            return {
                "total_sessions": len(self._sessions),
                "total_events": total_events,
                "total_snapshots": total_snapshots,
                "estimated_memory_bytes": total_memory_estimate,
                "current_recording_id": self._current_recording_id,
                "current_playback_id": self._current_playback_id,
                "session_states": session_states,
                "largest_session": largest_session,
            }

    def _estimate_memory_usage(self) -> int:
        total = 0
        for events in self._events.values():
            for event in events:
                total += len(json.dumps(event.to_dict(), default=str))
        for snapshots in self._snapshots.values():
            for snap in snapshots:
                total += len(json.dumps(snap.to_dict(), default=str))
        for session in self._sessions.values():
            total += len(json.dumps(session.to_dict(), default=str))
        return total

    # -- Serialization --
    # ------------------------------------------------------------------

    def export_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            events = self._events.get(session_id, [])
            snapshots = self._snapshots.get(session_id, [])

            return {
                "format_version": 1,
                "session": session.to_dict(),
                "events": [e.to_dict() for e in events],
                "snapshots": [s.to_dict() for s in snapshots],
            }

    def import_session(self, data: Dict[str, Any]) -> Optional[ReplaySession]:
        if data.get("format_version") != 1:
            return None

        session_data = data.get("session", {})
        session_id = session_data.get("id", uuid.uuid4().hex)

        with self._lock:
            session = ReplaySession(
                id=session_id,
                name=session_data.get("name", ""),
                state=ReplayState.IDLE,
                initial_random_seed=session_data.get("initial_random_seed", 42),
                frame_count=session_data.get("frame_count", 0),
                event_count=session_data.get("event_count", 0),
                duration_seconds=session_data.get("duration_seconds", 0.0),
                created_at=session_data.get("created_at", _time_module.time()),
                ended_at=session_data.get("ended_at", 0.0),
            )
            try:
                session.snap_frequency = SnapFrequency[
                    session_data.get("snap_frequency", "EVERY_60_FRAMES")
                ]
            except KeyError:
                session.snap_frequency = SnapFrequency.EVERY_60_FRAMES

            self._sessions[session_id] = session
            self._events[session_id] = [
                ReplayEvent.from_dict(e) for e in data.get("events", [])
            ]
            self._snapshots[session_id] = [
                StateSnapshot.from_dict(s) for s in data.get("snapshots", [])
            ]

            frame_index: List[int] = []
            for event in self._events[session_id]:
                frame_index.append(event.frame_number)
            self._frame_event_index[session_id] = frame_index

            self._enforce_session_limit()
            return session

    # -- Pause / Resume --
    # ------------------------------------------------------------------

    def pause_recording(self) -> bool:
        with self._lock:
            session_id = self._current_recording_id
            if session_id is None:
                return False
            session = self._sessions.get(session_id)
            if session is None or session.state != ReplayState.RECORDING:
                return False
            session.state = ReplayState.PAUSED
            return True

    def resume_recording(self) -> bool:
        with self._lock:
            session_id = self._current_recording_id
            if session_id is None:
                return False
            session = self._sessions.get(session_id)
            if session is None or session.state != ReplayState.PAUSED:
                return False
            session.state = ReplayState.RECORDING
            return True

    def pause_playback(self) -> bool:
        with self._lock:
            session_id = self._current_playback_id
            if session_id is None:
                return False
            session = self._sessions.get(session_id)
            if session is None or session.state != ReplayState.PLAYING:
                return False
            session.state = ReplayState.PAUSED
            return True

    def resume_playback(self) -> bool:
        with self._lock:
            session_id = self._current_playback_id
            if session_id is None:
                return False
            session = self._sessions.get(session_id)
            if session is None or session.state != ReplayState.PAUSED:
                return False
            session.state = ReplayState.PLAYING
            self._playback_start_real_time = _time_module.time()
            return True

    # -- Internal Utilities --
    # ------------------------------------------------------------------

    def _enforce_session_limit(self) -> None:
        if len(self._sessions) <= self.MAX_SESSIONS:
            return

        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda item: item[1].created_at,
        )
        remove_count = len(self._sessions) - self.MAX_SESSIONS
        for i in range(remove_count):
            oldest_id = sorted_sessions[i][0]
            if oldest_id == self._current_recording_id:
                continue
            if oldest_id == self._current_playback_id:
                continue
            self._sessions.pop(oldest_id, None)
            self._events.pop(oldest_id, None)
            self._snapshots.pop(oldest_id, None)
            self._frame_event_index.pop(oldest_id, None)

    def _get_events_sorted_by_frame(self, session_id: str) -> List[ReplayEvent]:
        events = self._events.get(session_id, [])
        return sorted(events, key=lambda e: e.frame_number)

    # -- Validation --
    # ------------------------------------------------------------------

    def validate_session(self, session_id: str) -> Dict[str, Any]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return {"valid": False, "error": "Session not found"}

            issues: List[str] = []
            events = self._events.get(session_id, [])
            snapshots = self._snapshots.get(session_id, [])

            if not events:
                issues.append("Session has no recorded events")

            frame_numbers = sorted(set(e.frame_number for e in events))
            if frame_numbers:
                for i in range(1, len(frame_numbers)):
                    gap = frame_numbers[i] - frame_numbers[i - 1]
                    if gap > 600:
                        issues.append(
                            f"Large frame gap of {gap} between frame "
                            f"{frame_numbers[i - 1]} and {frame_numbers[i]}"
                        )

            if snapshots:
                snap_frames = [s.frame_number for s in snapshots]
                expected = sorted(snap_frames)
                if snap_frames != expected:
                    issues.append("Snapshots are not ordered by frame number")

            duplicate_ids: Dict[str, int] = {}
            for e in events:
                duplicate_ids[e.id] = duplicate_ids.get(e.id, 0) + 1
            dup_count = sum(1 for v in duplicate_ids.values() if v > 1)
            if dup_count > 0:
                issues.append(f"Found {dup_count} duplicate event IDs")

            event_count_matches = len(events) == session.event_count

            return {
                "valid": len(issues) == 0,
                "session_id": session_id,
                "session_name": session.name,
                "issues": issues,
                "frame_count": session.frame_count,
                "event_count": len(events),
                "stored_event_count": session.event_count,
                "event_count_matches": event_count_matches,
                "snapshot_count": len(snapshots),
                "duration_seconds": session.duration_seconds,
            }

    # -- Advanced Filtering --
    # ------------------------------------------------------------------

    def get_events_by_category(
        self,
        session_id: str,
        category: EventCategory,
    ) -> List[ReplayEvent]:
        with self._lock:
            events = self._events.get(session_id)
            if not events:
                return []
            return [e for e in events if e.category == category]

    def get_events_by_categories(
        self,
        session_id: str,
        categories: List[EventCategory],
    ) -> List[ReplayEvent]:
        with self._lock:
            events = self._events.get(session_id)
            if not events:
                return []
            cat_set = set(categories)
            return [e for e in events if e.category in cat_set]

    def get_first_event_frame(self, session_id: str) -> Optional[int]:
        events = self._events.get(session_id)
        if not events:
            return None
        return min(e.frame_number for e in events)

    def get_last_event_frame(self, session_id: str) -> Optional[int]:
        events = self._events.get(session_id)
        if not events:
            return None
        return max(e.frame_number for e in events)

    def get_total_event_count(self, session_id: str) -> int:
        events = self._events.get(session_id)
        if not events:
            return 0
        return len(events)

    def get_category_counts(self, session_id: str) -> Dict[str, int]:
        events = self._events.get(session_id)
        if not events:
            return {}
        counts: Dict[str, int] = {}
        for e in events:
            key = e.category.value
            counts[key] = counts.get(key, 0) + 1
        return counts

    def has_events_in_frame_range(
        self,
        session_id: str,
        start_frame: int,
        end_frame: int,
    ) -> bool:
        events = self._events.get(session_id)
        if not events:
            return False
        return any(start_frame <= e.frame_number <= end_frame for e in events)

    # -- Snapshot Utilities --
    # ------------------------------------------------------------------

    def get_snapshot_count(self, session_id: str) -> int:
        snapshots = self._snapshots.get(session_id)
        if not snapshots:
            return 0
        return len(snapshots)

    def get_snapshot_frames(self, session_id: str) -> List[int]:
        snapshots = self._snapshots.get(session_id)
        if not snapshots:
            return []
        return sorted(s.frame_number for s in snapshots)

    def compare_snapshots(
        self,
        session_id: str,
        frame_a: int,
        frame_b: int,
    ) -> Dict[str, Any]:
        snap_a = self.get_snapshot(session_id, frame_a)
        snap_b = self.get_snapshot(session_id, frame_b)

        if snap_a is None or snap_b is None:
            return {"error": "One or both snapshots not found"}

        keys_a = set(snap_a.full_state.keys())
        keys_b = set(snap_b.full_state.keys())
        added_keys = list(keys_b - keys_a)
        removed_keys = list(keys_a - keys_b)
        common_keys = list(keys_a & keys_b)

        changed_keys: List[str] = []
        for key in common_keys:
            if snap_a.full_state.get(key) != snap_b.full_state.get(key):
                changed_keys.append(key)

        return {
            "frame_a": frame_a,
            "frame_b": frame_b,
            "hash_a": snap_a.game_state_hash,
            "hash_b": snap_b.game_state_hash,
            "identical": snap_a.game_state_hash == snap_b.game_state_hash,
            "added_keys": added_keys,
            "removed_keys": removed_keys,
            "changed_keys": changed_keys,
            "total_keys_a": len(keys_a),
            "total_keys_b": len(keys_b),
        }

    # -- Compact Snapshot Creation with Delta Support --
    # ------------------------------------------------------------------

    def create_delta_snapshot(
        self,
        session_id: str,
        frame_number: int,
        game_state: Dict[str, Any],
        base_frame_number: int,
    ) -> Optional[StateSnapshot]:
        base_snapshot = self.get_nearest_snapshot(session_id, base_frame_number)
        if base_snapshot is None:
            return self.capture_snapshot(session_id, frame_number, game_state)

        base_state = base_snapshot.full_state
        delta: Dict[str, Any] = {}
        for key, value in game_state.items():
            if key not in base_state or base_state[key] != value:
                delta[key] = value

        removed_keys = [k for k in base_state if k not in game_state]

        compact_state = {
            "_delta_from": base_frame_number,
            "_delta_base_hash": base_snapshot.game_state_hash,
            "changed": delta,
            "removed": removed_keys,
        }

        state_json = json.dumps(compact_state, sort_keys=True, default=str)
        state_hash = hashlib.sha256(state_json.encode("utf-8")).hexdigest()

        with self._lock:
            if session_id not in self._sessions:
                return None
            snapshots = self._snapshots.get(session_id)
            if snapshots is None or len(snapshots) >= self.MAX_SNAPSHOTS_PER_SESSION:
                return None

            snapshot = StateSnapshot(
                session_id=session_id,
                frame_number=frame_number,
                game_state_hash=state_hash,
                full_state=compact_state,
            )
            snapshots.append(snapshot)
            return snapshot

    # -- Session Search --
    # ------------------------------------------------------------------

    def find_sessions_by_name(self, name: str) -> List[ReplaySession]:
        with self._lock:
            return [s for s in self._sessions.values() if name.lower() in s.name.lower()]

    def find_sessions_in_time_range(
        self,
        start_time: float,
        end_time: float,
    ) -> List[ReplaySession]:
        with self._lock:
            return [
                s
                for s in self._sessions.values()
                if start_time <= s.created_at <= end_time
            ]

    def get_most_recent_session(self) -> Optional[ReplaySession]:
        with self._lock:
            if not self._sessions:
                return None
            return max(self._sessions.values(), key=lambda s: s.created_at)

    def get_largest_session(self) -> Optional[ReplaySession]:
        with self._lock:
            if not self._sessions:
                return None
            return max(self._sessions.values(), key=lambda s: s.event_count)

    # -- Debug Logging --
    # ------------------------------------------------------------------

    def _debug_log(self, message: str) -> None:
        timestamp = _time_module.time()
        self._pending_debug_lines.append(
            f"[{timestamp:.4f}] {message}"
        )

    def get_debug_log(self, clear: bool = True) -> List[str]:
        lines = list(self._pending_debug_lines)
        if clear:
            self._pending_debug_lines.clear()
        return lines

    # -- Reset --
    # ------------------------------------------------------------------

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()
            self._events.clear()
            self._snapshots.clear()
            self._frame_event_index.clear()
            self._current_recording_id = None
            self._current_playback_id = None
            self._recording_start_time = 0.0
            self._playback_frame = 0
            self._playback_speed = PlaybackSpeed.NORMAL_1X
            self._playback_start_real_time = 0.0
            self._playback_start_game_time = 0.0
            self._pending_debug_lines.clear()


def get_deterministic_replay() -> DeterministicReplay:
    return DeterministicReplay.get_instance()