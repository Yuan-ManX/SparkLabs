"""
SparkLabs Engine - Gameplay Replay

Records, stores, and plays back gameplay sessions. Captures state
snapshots at configurable intervals and records discrete events, enabling
playback at variable speeds, jumping to specific timestamps, and
post-session analysis.

The replay system operates in three modes:
- RECORDING: actively capturing snapshots and events from a live session
- PLAYBACK: replaying a recorded session, advancing through snapshots
- IDLE: no active session

State snapshots are dict-based and opaque to the replay system itself;
external systems (scene managers, physics engines) provide the snapshot
data through registered capture callbacks. This keeps the replay system
decoupled from the specific data being recorded.
"""

from __future__ import annotations

import datetime
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple


_time_module = time

_DEFAULT_FPS: int = 60


# =============================================================================
# Enums
# =============================================================================


class ReplayMode(Enum):
    """Operational mode of the replay system for a session."""

    IDLE = "idle"
    RECORDING = "recording"
    PLAYBACK = "playback"
    PAUSED = "paused"


class PlaybackSpeed(Enum):
    """Playback speed multipliers exposed as string values for JSON safety."""

    QUARTER = "0.25x"
    HALF = "0.5x"
    NORMAL = "1.0x"
    DOUBLE = "2.0x"
    QUADRUPLE = "4.0x"

    @property
    def multiplier(self) -> float:
        """Return the numeric multiplier parsed from the string value."""
        return float(self.value.rstrip("x"))


class EventType(Enum):
    """Categories of discrete events recorded during a session."""

    STATE_SNAPSHOT = "state_snapshot"
    ENTITY_EVENT = "entity_event"
    PLAYER_INPUT = "player_input"
    SYSTEM_EVENT = "system_event"
    CAMERA_EVENT = "camera_event"
    CUSTOM = "custom"


class HighlightKind(Enum):
    """Kinds of highlight markers used to flag notable moments."""

    SCORE = "score"
    DEATH = "death"
    SPAWN = "spawn"
    ACHIEVEMENT = "achievement"
    COMBO = "combo"
    CRITICAL_HIT = "critical_hit"
    CUSTOM = "custom"


class ExportFormat(Enum):
    """Output formats supported by session export."""

    JSON = "json"
    BINARY = "binary"
    COMPRESSED = "compressed"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ReplayEvent:
    """A discrete event recorded at a point in time during a session.

    Attributes:
        id: Unique identifier (auto-generated).
        session_id: Identifier of the owning session.
        timestamp: Time in seconds from the start of the session.
        event_type: Category of the event.
        source: Entity id or system name that produced the event.
        payload: Arbitrary event-specific data.
        sequence_number: Monotonic counter preserved per session.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    timestamp: float = 0.0
    event_type: EventType = EventType.CUSTOM
    source: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    sequence_number: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type.value,
            "source": self.source,
            "payload": dict(self.payload),
            "sequence_number": self.sequence_number,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplayEvent":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", 0.0),
            event_type=EventType(data.get("event_type", "custom")),
            source=data.get("source", ""),
            payload=data.get("payload", {}),
            sequence_number=data.get("sequence_number", 0),
        )


@dataclass
class StateSnapshot:
    """A captured state snapshot for a session at a point in time.

    Attributes:
        id: Unique identifier (auto-generated).
        session_id: Identifier of the owning session.
        timestamp: Time in seconds from the start of the session.
        frame_number: Frame index derived from the timestamp.
        state_data: Merged state data from all active capture sources.
        metadata: Optional metadata describing the capture.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    timestamp: float = 0.0
    frame_number: int = 0
    state_data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "frame_number": self.frame_number,
            "state_data": dict(self.state_data),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateSnapshot":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", 0.0),
            frame_number=data.get("frame_number", 0),
            state_data=data.get("state_data", {}),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Highlight:
    """A marked moment in a session for review or analysis.

    Attributes:
        id: Unique identifier (auto-generated).
        session_id: Identifier of the owning session.
        timestamp: Time in seconds from the start of the session.
        kind: Category of the highlight.
        title: Short human-readable label.
        description: Optional longer description.
        event_ids: Event ids associated with the highlight.
        metadata: Optional highlight-specific metadata.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    timestamp: float = 0.0
    kind: HighlightKind = HighlightKind.CUSTOM
    title: str = ""
    description: str = ""
    event_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "kind": self.kind.value,
            "title": self.title,
            "description": self.description,
            "event_ids": list(self.event_ids),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Highlight":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", 0.0),
            kind=HighlightKind(data.get("kind", "custom")),
            title=data.get("title", ""),
            description=data.get("description", ""),
            event_ids=data.get("event_ids", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class ReplaySession:
    """Container for a single recorded gameplay session.

    Attributes:
        id: Unique identifier (auto-generated).
        name: Human-readable name.
        description: Optional longer description.
        mode: Current operational mode of the session.
        started_at: ISO timestamp marking when recording began.
        ended_at: ISO timestamp marking when recording finished.
        duration_seconds: Total recorded duration in seconds.
        snapshot_count: Number of snapshots stored for the session.
        event_count: Number of events stored for the session.
        highlight_count: Number of highlights stored for the session.
        metadata: Optional session-level metadata.
        status: Lifecycle status string of the session.
    """

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    description: str = ""
    mode: ReplayMode = ReplayMode.IDLE
    started_at: str = ""
    ended_at: str = ""
    duration_seconds: float = 0.0
    snapshot_count: int = 0
    event_count: int = 0
    highlight_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "idle"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "mode": self.mode.value,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
            "snapshot_count": self.snapshot_count,
            "event_count": self.event_count,
            "highlight_count": self.highlight_count,
            "metadata": dict(self.metadata),
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ReplaySession":
        return cls(
            id=data.get("id", uuid.uuid4().hex),
            name=data.get("name", ""),
            description=data.get("description", ""),
            mode=ReplayMode(data.get("mode", "idle")),
            started_at=data.get("started_at", ""),
            ended_at=data.get("ended_at", ""),
            duration_seconds=data.get("duration_seconds", 0.0),
            snapshot_count=data.get("snapshot_count", 0),
            event_count=data.get("event_count", 0),
            highlight_count=data.get("highlight_count", 0),
            metadata=data.get("metadata", {}),
            status=data.get("status", "idle"),
        )


@dataclass
class PlaybackState:
    """State of an active playback of a recorded session.

    Attributes:
        session_id: Identifier of the session being played back.
        current_timestamp: Current position in seconds from session start.
        current_frame: Frame index derived from the current timestamp.
        speed: Active playback speed.
        is_playing: Whether playback is actively advancing.
        loop: Whether playback wraps around at the end.
        playback_position: Normalized position in the range 0.0 to 1.0.
    """

    session_id: str = ""
    current_timestamp: float = 0.0
    current_frame: int = 0
    speed: PlaybackSpeed = PlaybackSpeed.NORMAL
    is_playing: bool = False
    loop: bool = False
    playback_position: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "current_timestamp": self.current_timestamp,
            "current_frame": self.current_frame,
            "speed": self.speed.value,
            "is_playing": self.is_playing,
            "loop": self.loop,
            "playback_position": self.playback_position,
        }


@dataclass
class CaptureSource:
    """A registered provider of state data for snapshot capture.

    Attributes:
        name: Unique name identifying the source.
        description: Optional human-readable description.
        capture_callback: Callable returning a dict of state data.
        is_active: Whether the source contributes to snapshots.
        snapshot_count: Number of snapshots this source has contributed to.
    """

    name: str = ""
    description: str = ""
    capture_callback: Callable[[], Dict[str, Any]] = field(default=lambda: dict)
    is_active: bool = True
    snapshot_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "is_active": self.is_active,
            "snapshot_count": self.snapshot_count,
        }


@dataclass
class ReplayStats:
    """Aggregate statistics across all sessions.

    Attributes:
        total_sessions: Number of sessions stored.
        total_snapshots: Total snapshots across all sessions.
        total_events: Total events across all sessions.
        total_highlights: Total highlights across all sessions.
        total_recording_time: Accumulated recording time in seconds.
        total_playback_time: Accumulated playback time in seconds.
        total_exports: Number of export operations performed.
        total_imports: Number of import operations performed.
        last_recording_at: Real-time timestamp of the last recording start.
        last_playback_at: Real-time timestamp of the last playback start.
    """

    total_sessions: int = 0
    total_snapshots: int = 0
    total_events: int = 0
    total_highlights: int = 0
    total_recording_time: float = 0.0
    total_playback_time: float = 0.0
    total_exports: int = 0
    total_imports: int = 0
    last_recording_at: float = 0.0
    last_playback_at: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_sessions": self.total_sessions,
            "total_snapshots": self.total_snapshots,
            "total_events": self.total_events,
            "total_highlights": self.total_highlights,
            "total_recording_time": self.total_recording_time,
            "total_playback_time": self.total_playback_time,
            "total_exports": self.total_exports,
            "total_imports": self.total_imports,
            "last_recording_at": self.last_recording_at,
            "last_playback_at": self.last_playback_at,
        }


@dataclass
class ReplaySnapshot:
    """Immutable snapshot of the replay engine state.

    Attributes:
        stats: Aggregate replay statistics.
        active_sessions: Total number of stored sessions.
        recording_sessions: Number of sessions currently recording.
        playback_sessions: Number of sessions currently in playback.
        timestamp: Real-time timestamp when the snapshot was taken.
    """

    stats: ReplayStats = field(default_factory=ReplayStats)
    active_sessions: int = 0
    recording_sessions: int = 0
    playback_sessions: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stats": self.stats.to_dict(),
            "active_sessions": self.active_sessions,
            "recording_sessions": self.recording_sessions,
            "playback_sessions": self.playback_sessions,
            "timestamp": self.timestamp,
        }


# =============================================================================
# Gameplay Replay Engine (Singleton)
# =============================================================================


class GameplayReplayEngine:
    """Singleton gameplay replay engine.

    Records, stores, and plays back gameplay sessions. State snapshots are
    captured from registered capture sources at configurable intervals, and
    discrete events are recorded with timestamps relative to session start.
    Playback advances through recorded data at variable speeds and supports
    seeking to arbitrary timestamps via the snapshot index.

    All public methods are thread-safe.
    """

    _instance: Optional["GameplayReplayEngine"] = None
    _lock = threading.RLock()

    MAX_SESSIONS: int = 500
    MAX_SNAPSHOTS_PER_SESSION: int = 100000
    MAX_EVENTS_PER_SESSION: int = 500000

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        # Sessions and their recorded data.
        self._sessions: Dict[str, ReplaySession] = {}
        self._snapshots: Dict[str, List[StateSnapshot]] = {}
        self._events: Dict[str, List[ReplayEvent]] = {}
        self._highlights: Dict[str, List[Highlight]] = {}
        # Capture sources registered for snapshot capture.
        self._capture_sources: Dict[str, CaptureSource] = {}
        # Playback state keyed by session id.
        self._playback_states: Dict[str, PlaybackState] = {}
        # Per-session recording bookkeeping.
        self._recording_starts: Dict[str, float] = {}
        self._last_snapshot_time: Dict[str, float] = {}
        self._snapshot_intervals: Dict[str, float] = {}
        self._sequence_counters: Dict[str, int] = {}
        # Event handlers keyed by handler id.
        self._event_handlers: Dict[str, Dict[str, Any]] = {}
        # Aggregate statistics.
        self._stats: ReplayStats = ReplayStats()
        # Seed default demo data.
        self._seed_demo_data()
        self._initialized: bool = True

    @classmethod
    def get_instance(cls) -> "GameplayReplayEngine":
        """Return the singleton GameplayReplayEngine instance (thread-safe)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def start_recording(
        self,
        name: str,
        description: str = "",
        snapshot_interval: float = 0.1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ReplaySession:
        """Start a new recording session.

        Args:
            name: Human-readable name for the session.
            description: Optional longer description.
            snapshot_interval: Seconds between automatic snapshots.
            metadata: Optional session-level metadata.

        Returns:
            The newly created ReplaySession in RECORDING mode.
        """
        with self._lock:
            session = ReplaySession(
                name=name or f"session_{uuid.uuid4().hex[:8]}",
                description=description,
                mode=ReplayMode.RECORDING,
                started_at=datetime.datetime.now().isoformat(),
                status="recording",
                metadata=dict(metadata) if metadata else {},
            )
            session_id = session.id
            self._sessions[session_id] = session
            self._snapshots[session_id] = []
            self._events[session_id] = []
            self._highlights[session_id] = []
            self._recording_starts[session_id] = _time_module.time()
            self._last_snapshot_time[session_id] = 0.0
            self._snapshot_intervals[session_id] = max(0.0, snapshot_interval)
            self._sequence_counters[session_id] = 0
            self._stats.total_sessions = len(self._sessions)
            self._stats.last_recording_at = _time_module.time()
            self._enforce_session_limit()
            return session

    def stop_recording(self, session_id: str) -> ReplaySession:
        """Stop recording and finalize the session.

        Args:
            session_id: Identifier of the session to stop.

        Returns:
            The finalized ReplaySession.

        Raises:
            KeyError: If the session id is unknown or not recording.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            if session.mode != ReplayMode.RECORDING:
                raise KeyError(f"Session is not recording: {session_id}")

            start_real = self._recording_starts.get(session_id, _time_module.time())
            duration = _time_module.time() - start_real
            session.duration_seconds = duration
            session.ended_at = datetime.datetime.now().isoformat()
            session.mode = ReplayMode.IDLE
            session.status = "completed"
            session.snapshot_count = len(self._snapshots.get(session_id, []))
            session.event_count = len(self._events.get(session_id, []))
            session.highlight_count = len(self._highlights.get(session_id, []))
            self._stats.total_recording_time += duration
            # Clean up recording bookkeeping.
            self._recording_starts.pop(session_id, None)
            self._last_snapshot_time.pop(session_id, None)
            self._snapshot_intervals.pop(session_id, None)
            self._refresh_stats()
            return session

    def get_session(self, session_id: str) -> Optional[ReplaySession]:
        """Return the session with the given id, if it exists."""
        with self._lock:
            return self._sessions.get(session_id)

    def list_sessions(self, mode: Optional[ReplayMode] = None) -> List[ReplaySession]:
        """Return sessions, optionally filtered by mode."""
        with self._lock:
            if mode is None:
                return list(self._sessions.values())
            return [s for s in self._sessions.values() if s.mode == mode]

    def remove_session(self, session_id: str) -> bool:
        """Remove a session and all of its recorded data.

        Args:
            session_id: Identifier of the session to remove.

        Returns:
            True if the session was removed, False if it was not found.
        """
        with self._lock:
            if session_id not in self._sessions:
                return False
            self._sessions.pop(session_id, None)
            self._snapshots.pop(session_id, None)
            self._events.pop(session_id, None)
            self._highlights.pop(session_id, None)
            self._recording_starts.pop(session_id, None)
            self._last_snapshot_time.pop(session_id, None)
            self._snapshot_intervals.pop(session_id, None)
            self._sequence_counters.pop(session_id, None)
            self._playback_states.pop(session_id, None)
            self._refresh_stats()
            return True

    def rename_session(
        self,
        session_id: str,
        name: str,
        description: Optional[str] = None,
    ) -> ReplaySession:
        """Rename a session and optionally update its description.

        Args:
            session_id: Identifier of the session to rename.
            name: New name for the session.
            description: Optional new description.

        Returns:
            The updated ReplaySession.

        Raises:
            KeyError: If the session id is unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            session.name = name
            if description is not None:
                session.description = description
            return session

    # ------------------------------------------------------------------
    # Capture sources
    # ------------------------------------------------------------------

    def register_capture_source(
        self,
        name: str,
        capture_callback: Callable[[], Dict[str, Any]],
        description: str = "",
    ) -> CaptureSource:
        """Register a callback that provides state data for snapshots.

        Args:
            name: Unique name identifying the source.
            capture_callback: Callable returning a dict of state data.
            description: Optional human-readable description.

        Returns:
            The registered CaptureSource.
        """
        with self._lock:
            source = CaptureSource(
                name=name,
                description=description,
                capture_callback=capture_callback,
                is_active=True,
                snapshot_count=0,
            )
            self._capture_sources[name] = source
            return source

    def remove_capture_source(self, name: str) -> bool:
        """Remove a registered capture source.

        Args:
            name: Name of the source to remove.

        Returns:
            True if the source was removed, False if it was not found.
        """
        with self._lock:
            if name not in self._capture_sources:
                return False
            self._capture_sources.pop(name, None)
            return True

    def list_capture_sources(self) -> List[CaptureSource]:
        """Return all registered capture sources."""
        with self._lock:
            return list(self._capture_sources.values())

    # ------------------------------------------------------------------
    # Recording
    # ------------------------------------------------------------------

    def capture_snapshot(
        self,
        session_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateSnapshot:
        """Manually capture a snapshot from all active capture sources.

        Args:
            session_id: Identifier of the recording session.
            metadata: Optional metadata to attach to the snapshot.

        Returns:
            The newly created StateSnapshot.

        Raises:
            KeyError: If the session id is unknown or not recording.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            if session.mode != ReplayMode.RECORDING:
                raise KeyError(f"Session is not recording: {session_id}")

            snapshots = self._snapshots.get(session_id)
            if snapshots is None:
                raise KeyError(f"Session is not recording: {session_id}")
            if len(snapshots) >= self.MAX_SNAPSHOTS_PER_SESSION:
                raise RuntimeError("Snapshot limit reached for session")

            start_real = self._recording_starts.get(session_id, _time_module.time())
            elapsed = _time_module.time() - start_real

            state_data: Dict[str, Any] = {}
            for source in self._capture_sources.values():
                if not source.is_active:
                    continue
                try:
                    partial = source.capture_callback() or {}
                except Exception:
                    partial = {}
                state_data.update(partial)
                source.snapshot_count += 1

            snapshot = StateSnapshot(
                session_id=session_id,
                timestamp=elapsed,
                frame_number=int(elapsed * _DEFAULT_FPS),
                state_data=state_data,
                metadata=dict(metadata) if metadata else {},
            )
            snapshots.append(snapshot)
            self._last_snapshot_time[session_id] = elapsed
            session.snapshot_count = len(snapshots)
            self._refresh_stats()
            return snapshot

    def record_event(
        self,
        session_id: str,
        event_type: EventType,
        source: str,
        payload: Dict[str, Any],
        timestamp: Optional[float] = None,
    ) -> ReplayEvent:
        """Record a discrete event during a recording session.

        Args:
            session_id: Identifier of the recording session.
            event_type: Category of the event.
            source: Entity id or system name that produced the event.
            payload: Event-specific data.
            timestamp: Optional explicit timestamp; defaults to elapsed time.

        Returns:
            The newly created ReplayEvent.

        Raises:
            KeyError: If the session id is unknown or not recording.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            if session.mode != ReplayMode.RECORDING:
                raise KeyError(f"Session is not recording: {session_id}")

            events = self._events.get(session_id)
            if events is None:
                raise KeyError(f"Session is not recording: {session_id}")
            if len(events) >= self.MAX_EVENTS_PER_SESSION:
                raise RuntimeError("Event limit reached for session")

            if timestamp is None:
                start_real = self._recording_starts.get(session_id, _time_module.time())
                timestamp = _time_module.time() - start_real

            seq = self._sequence_counters.get(session_id, 0)
            event = ReplayEvent(
                session_id=session_id,
                timestamp=timestamp,
                event_type=event_type,
                source=source,
                payload=dict(payload) if payload else {},
                sequence_number=seq,
            )
            self._sequence_counters[session_id] = seq + 1
            events.append(event)
            session.event_count = len(events)
            self._refresh_stats()

            # Invoke matching event handlers (reentrant lock allows callbacks).
            handlers_to_invoke: List[Callable[[ReplayEvent], None]] = []
            target_kind = event_type.value
            for entry in self._event_handlers.values():
                if entry.get("event_kind") == target_kind:
                    handler = entry.get("handler")
                    if callable(handler):
                        handlers_to_invoke.append(handler)
            for handler in handlers_to_invoke:
                try:
                    handler(event)
                except Exception:
                    pass
            return event

    def record_highlight(
        self,
        session_id: str,
        timestamp: float,
        kind: HighlightKind,
        title: str,
        description: str = "",
        event_ids: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Highlight:
        """Record a highlight marking a notable moment in a session.

        Args:
            session_id: Identifier of the recording session.
            timestamp: Time in seconds from the start of the session.
            kind: Category of the highlight.
            title: Short human-readable label.
            description: Optional longer description.
            event_ids: Optional event ids associated with the highlight.
            metadata: Optional highlight-specific metadata.

        Returns:
            The newly created Highlight.

        Raises:
            KeyError: If the session id is unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")

            highlights = self._highlights.setdefault(session_id, [])
            highlight = Highlight(
                session_id=session_id,
                timestamp=timestamp,
                kind=kind,
                title=title,
                description=description,
                event_ids=list(event_ids) if event_ids else [],
                metadata=dict(metadata) if metadata else {},
            )
            highlights.append(highlight)
            session.highlight_count = len(highlights)
            self._refresh_stats()
            return highlight

    def tick(self, session_id: str) -> Optional[StateSnapshot]:
        """Auto-capture a snapshot if the interval has elapsed.

        Args:
            session_id: Identifier of the recording session.

        Returns:
            The captured StateSnapshot, or None if no capture occurred.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None or session.mode != ReplayMode.RECORDING:
                return None
            start_real = self._recording_starts.get(session_id, _time_module.time())
            elapsed = _time_module.time() - start_real
            last = self._last_snapshot_time.get(session_id, 0.0)
            interval = self._snapshot_intervals.get(session_id, 0.1)
            if elapsed - last < interval:
                return None
            return self.capture_snapshot(session_id)

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def start_playback(
        self,
        session_id: str,
        speed: PlaybackSpeed = PlaybackSpeed.NORMAL,
        loop: bool = False,
    ) -> PlaybackState:
        """Begin playback of a recorded session.

        Args:
            session_id: Identifier of the session to play back.
            speed: Initial playback speed.
            loop: Whether playback wraps around at the end.

        Returns:
            The PlaybackState for the session.

        Raises:
            KeyError: If the session id is unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            pb = PlaybackState(
                session_id=session_id,
                current_timestamp=0.0,
                current_frame=0,
                speed=speed,
                is_playing=True,
                loop=loop,
                playback_position=0.0,
            )
            self._playback_states[session_id] = pb
            session.mode = ReplayMode.PLAYBACK
            session.status = "playing"
            self._stats.last_playback_at = _time_module.time()
            return pb

    def stop_playback(self, session_id: str) -> PlaybackState:
        """Stop playback of a session.

        Args:
            session_id: Identifier of the session.

        Returns:
            The final PlaybackState (is_playing set to False).

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            pb.is_playing = False
            session = self._sessions.get(session_id)
            if session is not None and session.mode == ReplayMode.PLAYBACK:
                session.mode = ReplayMode.IDLE
                session.status = "completed"
            return pb

    def pause_playback(self, session_id: str) -> PlaybackState:
        """Pause an active playback.

        Args:
            session_id: Identifier of the session.

        Returns:
            The updated PlaybackState.

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            pb.is_playing = False
            session = self._sessions.get(session_id)
            if session is not None:
                session.mode = ReplayMode.PAUSED
                session.status = "paused"
            return pb

    def resume_playback(self, session_id: str) -> PlaybackState:
        """Resume a paused playback.

        Args:
            session_id: Identifier of the session.

        Returns:
            The updated PlaybackState.

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            pb.is_playing = True
            session = self._sessions.get(session_id)
            if session is not None:
                session.mode = ReplayMode.PLAYBACK
                session.status = "playing"
            return pb

    def set_playback_speed(
        self,
        session_id: str,
        speed: PlaybackSpeed,
    ) -> PlaybackState:
        """Change the playback speed of an active playback.

        Args:
            session_id: Identifier of the session.
            speed: New playback speed.

        Returns:
            The updated PlaybackState.

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            pb.speed = speed
            return pb

    def seek(self, session_id: str, timestamp: float) -> PlaybackState:
        """Jump playback to a specific timestamp.

        Args:
            session_id: Identifier of the session.
            timestamp: Target time in seconds from session start.

        Returns:
            The updated PlaybackState.

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            session = self._sessions.get(session_id)
            duration = session.duration_seconds if session else 0.0
            if duration > 0:
                timestamp = max(0.0, min(timestamp, duration))
            else:
                timestamp = max(0.0, timestamp)
            pb.current_timestamp = timestamp
            pb.current_frame = int(timestamp * _DEFAULT_FPS)
            pb.playback_position = (
                min(timestamp / duration, 1.0) if duration > 0 else 0.0
            )
            return pb

    def seek_to_frame(self, session_id: str, frame_number: int) -> PlaybackState:
        """Jump playback to a specific frame number.

        Args:
            session_id: Identifier of the session.
            frame_number: Target frame index.

        Returns:
            The updated PlaybackState.

        Raises:
            KeyError: If no playback is active for the session.
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None:
                raise KeyError(f"No active playback for session: {session_id}")
            frame_number = max(0, frame_number)
            timestamp = frame_number / float(_DEFAULT_FPS)
            return self.seek(session_id, timestamp)

    def get_playback_state(self, session_id: str) -> Optional[PlaybackState]:
        """Return the playback state for a session, if one is active."""
        with self._lock:
            return self._playback_states.get(session_id)

    def advance_playback(
        self,
        session_id: str,
        delta_seconds: float,
    ) -> Tuple[Optional[StateSnapshot], List[ReplayEvent]]:
        """Advance playback by delta_seconds.

        Computes the new timestamp from the current position, the active
        speed multiplier, and the delta. Collects the snapshot at the new
        position and any events that occurred in the traversed time range.

        Args:
            session_id: Identifier of the session.
            delta_seconds: Amount of real time to advance.

        Returns:
            A tuple of (snapshot at the new position, events in range).
        """
        with self._lock:
            pb = self._playback_states.get(session_id)
            if pb is None or not pb.is_playing:
                return (None, [])
            session = self._sessions.get(session_id)
            if session is None:
                return (None, [])
            duration = session.duration_seconds
            if duration <= 0:
                return (None, [])

            events = self._events.get(session_id, [])
            speed_mult = pb.speed.multiplier
            advance_amount = delta_seconds * speed_mult
            prev_timestamp = pb.current_timestamp
            new_timestamp = prev_timestamp + advance_amount

            collected_events: List[ReplayEvent] = []

            if new_timestamp < duration:
                collected_events = [
                    e for e in events
                    if prev_timestamp < e.timestamp <= new_timestamp
                ]
            else:
                # Collect events from the previous position up to the end.
                collected_events = [
                    e for e in events
                    if prev_timestamp < e.timestamp <= duration
                ]
                if pb.loop:
                    overflow = new_timestamp - duration
                    new_timestamp = overflow
                    collected_events += [
                        e for e in events
                        if 0 < e.timestamp <= new_timestamp
                    ]
                else:
                    new_timestamp = duration
                    pb.is_playing = False
                    session.mode = ReplayMode.IDLE
                    session.status = "completed"

            pb.current_timestamp = new_timestamp
            pb.current_frame = int(new_timestamp * _DEFAULT_FPS)
            pb.playback_position = (
                min(new_timestamp / duration, 1.0) if duration > 0 else 0.0
            )

            snapshot = self._find_snapshot_at(session_id, new_timestamp)
            self._stats.total_playback_time += advance_amount
            return (snapshot, collected_events)

    # ------------------------------------------------------------------
    # Querying
    # ------------------------------------------------------------------

    def get_snapshots(
        self,
        session_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[StateSnapshot]:
        """Return snapshots for a session, optionally filtered by time range.

        Args:
            session_id: Identifier of the session.
            start_time: Optional inclusive lower timestamp bound.
            end_time: Optional inclusive upper timestamp bound.
            limit: Optional maximum number of snapshots to return.

        Returns:
            A list of matching StateSnapshot objects.
        """
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            result: List[StateSnapshot] = []
            for snap in snapshots:
                if start_time is not None and snap.timestamp < start_time:
                    continue
                if end_time is not None and snap.timestamp > end_time:
                    continue
                result.append(snap)
            if limit is not None:
                result = result[:limit]
            return result

    def get_events(
        self,
        session_id: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        event_type: Optional[EventType] = None,
        source: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[ReplayEvent]:
        """Return events for a session, optionally filtered.

        Args:
            session_id: Identifier of the session.
            start_time: Optional inclusive lower timestamp bound.
            end_time: Optional inclusive upper timestamp bound.
            event_type: Optional event type filter.
            source: Optional source filter.
            limit: Optional maximum number of events to return.

        Returns:
            A list of matching ReplayEvent objects.
        """
        with self._lock:
            events = self._events.get(session_id, [])
            result: List[ReplayEvent] = []
            for event in events:
                if start_time is not None and event.timestamp < start_time:
                    continue
                if end_time is not None and event.timestamp > end_time:
                    continue
                if event_type is not None and event.event_type != event_type:
                    continue
                if source is not None and event.source != source:
                    continue
                result.append(event)
            if limit is not None:
                result = result[:limit]
            return result

    def get_highlights(self, session_id: str) -> List[Highlight]:
        """Return all highlights for a session."""
        with self._lock:
            return list(self._highlights.get(session_id, []))

    def get_snapshot_at(
        self,
        session_id: str,
        timestamp: float,
    ) -> Optional[StateSnapshot]:
        """Find the snapshot closest to (but not after) the given timestamp.

        Args:
            session_id: Identifier of the session.
            timestamp: Target time in seconds from session start.

        Returns:
            The matching StateSnapshot, or None if no snapshot qualifies.
        """
        with self._lock:
            return self._find_snapshot_at(session_id, timestamp)

    def get_timeline(self, session_id: str) -> Dict[str, Any]:
        """Return a summary timeline for a session.

        Args:
            session_id: Identifier of the session.

        Returns:
            A dict with duration, snapshot count, event count, highlight
            count, and a mapping of event type values to counts.

        Raises:
            KeyError: If the session id is unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            events = self._events.get(session_id, [])
            event_types: Dict[str, int] = {}
            for event in events:
                key = event.event_type.value
                event_types[key] = event_types.get(key, 0) + 1
            return {
                "duration": session.duration_seconds,
                "snapshot_count": len(self._snapshots.get(session_id, [])),
                "event_count": len(events),
                "highlight_count": len(self._highlights.get(session_id, [])),
                "event_types": event_types,
            }

    # ------------------------------------------------------------------
    # Export / Import
    # ------------------------------------------------------------------

    def export_session(
        self,
        session_id: str,
        format: ExportFormat = ExportFormat.JSON,
    ) -> Dict[str, Any]:
        """Export full session data as a dict.

        Args:
            session_id: Identifier of the session to export.
            format: Desired output format (recorded in the output).

        Returns:
            A dict containing the session, snapshots, events, and
            highlights.

        Raises:
            KeyError: If the session id is unknown.
        """
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                raise KeyError(f"Unknown replay session: {session_id}")
            self._stats.total_exports += 1
            return {
                "format_version": 1,
                "format": format.value,
                "session": session.to_dict(),
                "snapshots": [s.to_dict() for s in self._snapshots.get(session_id, [])],
                "events": [e.to_dict() for e in self._events.get(session_id, [])],
                "highlights": [h.to_dict() for h in self._highlights.get(session_id, [])],
            }

    def import_session(self, data: Dict[str, Any]) -> ReplaySession:
        """Import a session from exported data.

        Args:
            data: Dict previously produced by :meth:`export_session`.

        Returns:
            The imported ReplaySession.

        Raises:
            ValueError: If the data format is unrecognized.
        """
        if data.get("format_version") != 1:
            raise ValueError("Unsupported replay export format version")
        session_data = data.get("session", {})
        session = ReplaySession.from_dict(session_data)
        session_id = session.id

        with self._lock:
            self._sessions[session_id] = session
            self._snapshots[session_id] = [
                StateSnapshot.from_dict(s) for s in data.get("snapshots", [])
            ]
            self._events[session_id] = [
                ReplayEvent.from_dict(e) for e in data.get("events", [])
            ]
            self._highlights[session_id] = [
                Highlight.from_dict(h) for h in data.get("highlights", [])
            ]
            session.snapshot_count = len(self._snapshots[session_id])
            session.event_count = len(self._events[session_id])
            session.highlight_count = len(self._highlights[session_id])
            self._stats.total_imports += 1
            self._enforce_session_limit()
            self._refresh_stats()
            return session

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    def register_event_handler(
        self,
        event_kind: Any,
        handler: Callable[[ReplayEvent], None],
    ) -> str:
        """Register a handler invoked when a matching event is recorded.

        Args:
            event_kind: EventType or string value to match against.
            handler: Callable receiving the recorded ReplayEvent.

        Returns:
            A handler id that can be used for reference.
        """
        with self._lock:
            kind_value = (
                event_kind.value if isinstance(event_kind, EventType) else str(event_kind)
            )
            handler_id = uuid.uuid4().hex
            self._event_handlers[handler_id] = {
                "id": handler_id,
                "event_kind": kind_value,
                "handler": handler,
            }
            return handler_id

    def list_event_handlers(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered event handlers."""
        with self._lock:
            return [
                {"id": h["id"], "event_kind": h["event_kind"]}
                for h in self._event_handlers.values()
            ]

    # ------------------------------------------------------------------
    # Status and snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current engine state."""
        with self._lock:
            self._refresh_stats()
            return {
                "total_sessions": self._stats.total_sessions,
                "total_snapshots": self._stats.total_snapshots,
                "total_events": self._stats.total_events,
                "total_highlights": self._stats.total_highlights,
                "total_recording_time": self._stats.total_recording_time,
                "total_playback_time": self._stats.total_playback_time,
                "total_exports": self._stats.total_exports,
                "total_imports": self._stats.total_imports,
                "last_recording_at": self._stats.last_recording_at,
                "last_playback_at": self._stats.last_playback_at,
                "capture_sources": len(self._capture_sources),
                "event_handlers": len(self._event_handlers),
            }

    def get_snapshot(self) -> ReplaySnapshot:
        """Capture an immutable snapshot of the engine state."""
        with self._lock:
            self._refresh_stats()
            recording = sum(
                1 for s in self._sessions.values() if s.mode == ReplayMode.RECORDING
            )
            playback = sum(
                1 for s in self._sessions.values() if s.mode == ReplayMode.PLAYBACK
            )
            return ReplaySnapshot(
                stats=self._stats,
                active_sessions=len(self._sessions),
                recording_sessions=recording,
                playback_sessions=playback,
                timestamp=_time_module.time(),
            )

    def reset(self) -> None:
        """Clear all sessions, capture sources, handlers, and statistics."""
        with self._lock:
            self._sessions.clear()
            self._snapshots.clear()
            self._events.clear()
            self._highlights.clear()
            self._capture_sources.clear()
            self._playback_states.clear()
            self._recording_starts.clear()
            self._last_snapshot_time.clear()
            self._snapshot_intervals.clear()
            self._sequence_counters.clear()
            self._event_handlers.clear()
            self._stats = ReplayStats()

    # ------------------------------------------------------------------
    # Internal utilities
    # ------------------------------------------------------------------

    def _find_snapshot_at(
        self,
        session_id: str,
        timestamp: float,
    ) -> Optional[StateSnapshot]:
        """Return the snapshot with the largest timestamp <= the given time."""
        snapshots = self._snapshots.get(session_id, [])
        best: Optional[StateSnapshot] = None
        for snap in snapshots:
            if snap.timestamp <= timestamp:
                if best is None or snap.timestamp > best.timestamp:
                    best = snap
        return best

    def _refresh_stats(self) -> None:
        """Recompute aggregate statistics from the stored sessions."""
        self._stats.total_sessions = len(self._sessions)
        self._stats.total_snapshots = sum(len(s) for s in self._snapshots.values())
        self._stats.total_events = sum(len(e) for e in self._events.values())
        self._stats.total_highlights = sum(len(h) for h in self._highlights.values())

    def _enforce_session_limit(self) -> None:
        """Evict the oldest sessions when the configured limit is exceeded."""
        if len(self._sessions) <= self.MAX_SESSIONS:
            return
        sorted_sessions = sorted(
            self._sessions.items(),
            key=lambda item: item[1].started_at or "",
        )
        remove_count = len(self._sessions) - self.MAX_SESSIONS
        for i in range(remove_count):
            oldest_id = sorted_sessions[i][0]
            if self._sessions.get(oldest_id) and self._sessions[oldest_id].mode == ReplayMode.RECORDING:
                continue
            self._sessions.pop(oldest_id, None)
            self._snapshots.pop(oldest_id, None)
            self._events.pop(oldest_id, None)
            self._highlights.pop(oldest_id, None)
            self._playback_states.pop(oldest_id, None)

    # ------------------------------------------------------------------
    # Default seed data
    # ------------------------------------------------------------------

    def _seed_demo_data(self) -> None:
        """Populate a default demo session and capture source."""
        now = datetime.datetime.now()
        started = now - datetime.timedelta(seconds=60)
        session = ReplaySession(
            name="Demo Battle Replay",
            description="A short demonstration battle session with sample events.",
            mode=ReplayMode.IDLE,
            started_at=started.isoformat(),
            ended_at=now.isoformat(),
            duration_seconds=60.0,
            snapshot_count=7,
            event_count=5,
            highlight_count=2,
            metadata={"demo": True},
            status="completed",
        )
        session_id = session.id
        self._sessions[session_id] = session

        snapshots: List[StateSnapshot] = []
        for ts in (0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0):
            snapshots.append(
                StateSnapshot(
                    session_id=session_id,
                    timestamp=ts,
                    frame_number=int(ts * _DEFAULT_FPS),
                    state_data={
                        "player": {"x": ts, "y": 0.0},
                        "entities": [],
                    },
                    metadata={"demo": True, "auto": True},
                )
            )
        self._snapshots[session_id] = snapshots

        demo_events: List[Tuple[float, EventType, str, Dict[str, Any]]] = [
            (2.0, EventType.ENTITY_EVENT, "player", {"action": "attack", "target": "goblin-1"}),
            (5.0, EventType.ENTITY_EVENT, "goblin-1", {"action": "death", "cause": "player_attack"}),
            (15.0, EventType.ENTITY_EVENT, "player", {"action": "pickup", "item": "sword"}),
            (30.0, EventType.SYSTEM_EVENT, "quest_system", {"event": "quest_complete", "quest": "defeat_goblins"}),
            (45.0, EventType.ENTITY_EVENT, "player", {"action": "level_up", "new_level": 5}),
        ]
        events: List[ReplayEvent] = []
        for index, (ts, etype, src, payload) in enumerate(demo_events):
            events.append(
                ReplayEvent(
                    session_id=session_id,
                    timestamp=ts,
                    event_type=etype,
                    source=src,
                    payload=payload,
                    sequence_number=index,
                )
            )
        self._events[session_id] = events

        highlights: List[Highlight] = [
            Highlight(
                session_id=session_id,
                timestamp=5.0,
                kind=HighlightKind.DEATH,
                title="First Kill",
                description="Player defeated the first goblin",
            ),
            Highlight(
                session_id=session_id,
                timestamp=30.0,
                kind=HighlightKind.ACHIEVEMENT,
                title="Quest Complete",
                description="Defeat Goblins quest completed",
            ),
        ]
        self._highlights[session_id] = highlights

        # Default capture source returning a static scene state.
        self._capture_sources["scene_state"] = CaptureSource(
            name="scene_state",
            description="Default scene state capture source.",
            capture_callback=lambda: {"player": {"x": 0, "y": 0}, "entities": []},
            is_active=True,
            snapshot_count=0,
        )

        self._refresh_stats()


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_gameplay_replay() -> GameplayReplayEngine:
    """Return the singleton GameplayReplayEngine instance."""
    return GameplayReplayEngine.get_instance()
