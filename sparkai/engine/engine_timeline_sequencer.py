"""
SparkLabs Engine - Timeline Sequencer

This module provides a scripted sequence playback engine for creating and
running cutscenes, tutorials, cinematic sequences, and timed game events.
It models a timeline as a collection of tracks, each containing keyframes
that fire at specific timestamps during playback. Tracks are typed by the
kind of content they drive: camera movements, dialogue lines, animation
triggers, audio cues, and arbitrary game events.

The sequencer supports standard playback controls (play, pause, stop,
seek, loop) and emits observable events as keyframes are reached during
playback. A simulation tick drives the timeline forward; the caller is
responsible for invoking ``tick(delta_time)`` from the game loop.

Architecture:
  TimelineSequencer (Singleton, double-checked locking, threading.RLock)
    |-- Sequence        -- a complete scripted timeline with tracks
    |-- TimelineTrack   -- a typed track containing keyframes
    |-- Keyframe        -- a single timed event on a track
    |-- PlaybackState   -- the live state of a sequence playback
    |-- SequencerStats  -- aggregate sequencer statistics
    |-- SequencerEvent  -- observable engine lifecycle event

All public mutating methods are protected by a re-entrant lock so the
sequencer is safe to call from multiple threads. Bounded in-memory stores
use FIFO eviction when their capacity constants are exceeded.
"""

from __future__ import annotations

import datetime
import threading
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Union


# ---------------------------------------------------------------------------
# Capacity constants
# ---------------------------------------------------------------------------

_MAX_SEQUENCES: int = 500
_MAX_PLAYBACKS: int = 50
_MAX_EVENTS: int = 3000


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    """Return a UTC ISO-8601 timestamp string terminated with 'Z'."""
    return datetime.datetime.utcnow().isoformat() + "Z"


def _new_id(prefix: str = "seq") -> str:
    """Generate a short unique identifier with a readable prefix."""
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _evict_fifo_dict(store: Dict[str, Any], max_size: int) -> None:
    """Evict the oldest inserted entries from a dict until within bounds."""
    while len(store) > max_size:
        oldest_key = next(iter(store))
        store.pop(oldest_key, None)


def _evict_fifo_deque(store: deque, max_size: int) -> None:
    """Evict the oldest inserted entries from a deque until within bounds."""
    while len(store) > max_size:
        try:
            store.popleft()
        except IndexError:
            break


def _to_jsonable(value: Any) -> Any:
    """Recursively convert a value to a JSON-friendly form."""
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_jsonable(v) for v in value]
    if hasattr(value, "to_dict") and callable(value.to_dict):
        return value.to_dict()
    return value


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class TrackType(Enum):
    """The kind of content a timeline track drives."""
    CAMERA = "camera"
    DIALOGUE = "dialogue"
    ANIMATION = "animation"
    AUDIO = "audio"
    EVENT = "event"
    VISUAL_EFFECT = "visual_effect"
    ACTIVATION = "activation"


class PlaybackStatus(Enum):
    """The live status of a sequence playback."""
    IDLE = "idle"
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    COMPLETED = "completed"


class LoopMode(Enum):
    """How a sequence loops during playback."""
    NONE = "none"
    LOOP = "loop"
    PING_PONG = "ping_pong"


class SequencerEventKind(Enum):
    """Observable lifecycle events emitted by the sequencer."""
    SEQUENCE_CREATED = "sequence_created"
    SEQUENCE_DELETED = "sequence_deleted"
    PLAYBACK_STARTED = "playback_started"
    PLAYBACK_PAUSED = "playback_paused"
    PLAYBACK_RESUMED = "playback_resumed"
    PLAYBACK_STOPPED = "playback_stopped"
    PLAYBACK_COMPLETED = "playback_completed"
    PLAYBACK_SEEKED = "playback_seeked"
    KEYFRAME_FIRED = "keyframe_fired"
    TRACK_ADDED = "track_added"
    KEYFRAME_ADDED = "keyframe_added"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class Keyframe:
    """A single timed event on a timeline track."""
    keyframe_id: str
    time: float
    value: Dict[str, Any]
    interpolation: str
    duration: float

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this keyframe to a JSON-friendly dictionary."""
        return {
            "keyframe_id": self.keyframe_id,
            "time": round(self.time, 6),
            "value": _to_jsonable(self.value),
            "interpolation": self.interpolation,
            "duration": round(self.duration, 6),
        }


@dataclass
class TimelineTrack:
    """A typed track containing keyframes."""
    track_id: str
    track_type: TrackType
    name: str
    keyframes: List[Keyframe]
    enabled: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this track to a JSON-friendly dictionary."""
        return {
            "track_id": self.track_id,
            "track_type": self.track_type.value,
            "name": self.name,
            "keyframes": [k.to_dict() for k in self.keyframes],
            "enabled": self.enabled,
        }

    @property
    def duration(self) -> float:
        """Return the end time of the last keyframe on this track."""
        if not self.keyframes:
            return 0.0
        last = self.keyframes[-1]
        return last.time + last.duration


@dataclass
class Sequence:
    """A complete scripted timeline with tracks."""
    sequence_id: str
    name: str
    description: str
    tracks: List[TimelineTrack]
    loop_mode: LoopMode
    playback_speed: float
    created_at: str
    updated_at: str
    tags: List[str]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this sequence to a JSON-friendly dictionary."""
        return {
            "sequence_id": self.sequence_id,
            "name": self.name,
            "description": self.description,
            "tracks": [t.to_dict() for t in self.tracks],
            "loop_mode": self.loop_mode.value,
            "playback_speed": round(self.playback_speed, 6),
            "duration": round(self.duration, 6),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": list(self.tags),
        }

    @property
    def duration(self) -> float:
        """Return the total duration of this sequence across all tracks."""
        if not self.tracks:
            return 0.0
        return max(t.duration for t in self.tracks)


@dataclass
class PlaybackState:
    """The live state of a sequence playback."""
    playback_id: str
    sequence_id: str
    status: PlaybackStatus
    current_time: float
    direction: int
    fired_keyframe_ids: List[str]
    started_at: str
    last_ticked_at: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this playback state to a JSON-friendly dictionary."""
        return {
            "playback_id": self.playback_id,
            "sequence_id": self.sequence_id,
            "status": self.status.value,
            "current_time": round(self.current_time, 6),
            "direction": self.direction,
            "fired_keyframe_count": len(self.fired_keyframe_ids),
            "started_at": self.started_at,
            "last_ticked_at": self.last_ticked_at,
        }


@dataclass
class SequencerStats:
    """Aggregate statistics about the sequencer."""
    total_sequences: int
    total_tracks: int
    total_keyframes: int
    active_playbacks: int
    total_playbacks_started: int
    total_playbacks_completed: int
    total_events: int

    def to_dict(self) -> Dict[str, Any]:
        """Serialize these stats to a JSON-friendly dictionary."""
        return {
            "total_sequences": self.total_sequences,
            "total_tracks": self.total_tracks,
            "total_keyframes": self.total_keyframes,
            "active_playbacks": self.active_playbacks,
            "total_playbacks_started": self.total_playbacks_started,
            "total_playbacks_completed": self.total_playbacks_completed,
            "total_events": self.total_events,
        }


@dataclass
class SequencerEvent:
    """An observable lifecycle event emitted by the sequencer."""
    event_id: str
    kind: SequencerEventKind
    payload: Dict[str, Any]
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        """Serialize this event to a JSON-friendly dictionary."""
        return {
            "event_id": self.event_id,
            "kind": self.kind.value,
            "payload": _to_jsonable(self.payload),
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------


class TimelineSequencer:
    """Scripted sequence playback engine for cutscenes and timed events.

    Implemented as a thread-safe singleton with double-checked locking.
    All public mutating methods acquire ``self._lock`` (a re-entrant lock)
    so the sequencer is safe to call from the game loop thread.
    """

    _instance: Optional["TimelineSequencer"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "TimelineSequencer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        with self._lock:
            if self._initialized:
                return
            self._initialized: bool = True
            self._sequences: Dict[str, Sequence] = {}
            self._playbacks: Dict[str, PlaybackState] = {}
            self._events: deque[SequencerEvent] = deque(maxlen=_MAX_EVENTS)
            self._sequence_counter = 0
            self._track_counter = 0
            self._keyframe_counter = 0
            self._playback_counter = 0
            self._playbacks_started = 0
            self._playbacks_completed = 0
            self._event_counter = 0
            self._seed_data()

    # ------------------------------------------------------------------
    # Seeding
    # ------------------------------------------------------------------

    def _seed_data(self) -> None:
        """Seed the sequencer with sample sequences."""
        intro = self.create_sequence(
            name="Intro Cutscene",
            description="Opening cinematic with camera pan and title",
        )
        cam_track = self.add_track(intro.sequence_id, TrackType.CAMERA, "Camera Pan")
        self.add_keyframe(intro.sequence_id, cam_track.track_id, 0.0, {"action": "set_position", "x": 0, "y": 5, "z": -10})
        self.add_keyframe(intro.sequence_id, cam_track.track_id, 2.0, {"action": "pan_to", "x": 0, "y": 8, "z": 0}, duration=3.0)
        dlg_track = self.add_track(intro.sequence_id, TrackType.DIALOGUE, "Narrator")
        self.add_keyframe(intro.sequence_id, dlg_track.track_id, 1.0, {"speaker": "Narrator", "text": "Welcome to the world."}, duration=2.0)

        tutorial = self.create_sequence(
            name="Tutorial Sequence",
            description="Step-by-step controls tutorial",
        )
        evt_track = self.add_track(tutorial.sequence_id, TrackType.EVENT, "Tutorial Events")
        self.add_keyframe(tutorial.sequence_id, evt_track.track_id, 0.0, {"event": "show_hint", "text": "Press SPACE to jump"})
        self.add_keyframe(tutorial.sequence_id, evt_track.track_id, 3.0, {"event": "show_hint", "text": "Press E to interact"})
        self.add_keyframe(tutorial.sequence_id, evt_track.track_id, 6.0, {"event": "complete_tutorial"})

    # ------------------------------------------------------------------
    # Internal event recording
    # ------------------------------------------------------------------

    def _record_event(
        self,
        kind: SequencerEventKind,
        payload: Optional[Dict[str, Any]] = None,
    ) -> SequencerEvent:
        """Record an audit event (caller must hold ``self._lock``)."""
        event = SequencerEvent(
            event_id=_new_id("tev"),
            kind=kind,
            payload=dict(payload) if payload else {},
            timestamp=_now(),
        )
        _evict_fifo_deque(self._events, _MAX_EVENTS)
        self._events.append(event)
        self._event_counter += 1
        return event

    # ------------------------------------------------------------------
    # Sequence management
    # ------------------------------------------------------------------

    def create_sequence(
        self,
        name: str,
        description: str = "",
        loop_mode: Union[LoopMode, str] = LoopMode.NONE,
        playback_speed: float = 1.0,
        tags: Optional[List[str]] = None,
    ) -> Sequence:
        """Create a new empty timeline sequence."""
        with self._lock:
            resolved_loop = _resolve_loop(loop_mode) or LoopMode.NONE
            seq_id = _new_id("seq")
            now = _now()
            seq = Sequence(
                sequence_id=seq_id,
                name=name or "Untitled Sequence",
                description=description,
                tracks=[],
                loop_mode=resolved_loop,
                playback_speed=max(0.01, float(playback_speed)),
                created_at=now,
                updated_at=now,
                tags=list(tags) if tags else [],
            )
            self._sequences[seq_id] = seq
            self._sequence_counter += 1
            _evict_fifo_dict(self._sequences, _MAX_SEQUENCES)
            self._record_event(
                SequencerEventKind.SEQUENCE_CREATED,
                {"sequence_id": seq_id, "name": seq.name},
            )
            return seq

    def get_sequence(self, sequence_id: str) -> Optional[Sequence]:
        """Return a sequence by id."""
        with self._lock:
            return self._sequences.get(sequence_id)

    def list_sequences(self, tag: Optional[str] = None) -> List[Sequence]:
        """Return all sequences, optionally filtered by tag."""
        with self._lock:
            if not tag:
                return list(self._sequences.values())
            return [s for s in self._sequences.values() if tag in s.tags]

    def delete_sequence(self, sequence_id: str) -> bool:
        """Delete a sequence by id."""
        with self._lock:
            seq = self._sequences.pop(sequence_id, None)
            if seq is None:
                return False
            to_stop = [
                pid for pid, pb in self._playbacks.items()
                if pb.sequence_id == sequence_id
            ]
            for pid in to_stop:
                self._playbacks.pop(pid, None)
            self._record_event(
                SequencerEventKind.SEQUENCE_DELETED,
                {"sequence_id": sequence_id},
            )
            return True

    def update_sequence(
        self,
        sequence_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        loop_mode: Optional[Union[LoopMode, str]] = None,
        playback_speed: Optional[float] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Sequence]:
        """Update properties of an existing sequence."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return None
            if name is not None:
                seq.name = name
            if description is not None:
                seq.description = description
            if loop_mode is not None:
                resolved = _resolve_loop(loop_mode)
                if resolved is not None:
                    seq.loop_mode = resolved
            if playback_speed is not None:
                seq.playback_speed = max(0.01, float(playback_speed))
            if tags is not None:
                seq.tags = list(tags)
            seq.updated_at = _now()
            return seq

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def add_track(
        self,
        sequence_id: str,
        track_type: Union[TrackType, str],
        name: str = "",
    ) -> Optional[TimelineTrack]:
        """Add a new track to a sequence."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return None
            resolved_type = _resolve_track_type(track_type)
            if resolved_type is None:
                return None
            track = TimelineTrack(
                track_id=_new_id("trk"),
                track_type=resolved_type,
                name=name or resolved_type.value,
                keyframes=[],
                enabled=True,
            )
            seq.tracks.append(track)
            seq.updated_at = _now()
            self._track_counter += 1
            self._record_event(
                SequencerEventKind.TRACK_ADDED,
                {"sequence_id": sequence_id, "track_id": track.track_id},
            )
            return track

    def remove_track(self, sequence_id: str, track_id: str) -> bool:
        """Remove a track from a sequence."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return False
            before = len(seq.tracks)
            seq.tracks = [t for t in seq.tracks if t.track_id != track_id]
            if len(seq.tracks) == before:
                return False
            seq.updated_at = _now()
            return True

    def toggle_track(self, sequence_id: str, track_id: str, enabled: bool) -> bool:
        """Enable or disable a track."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return False
            for t in seq.tracks:
                if t.track_id == track_id:
                    t.enabled = enabled
                    seq.updated_at = _now()
                    return True
            return False

    # ------------------------------------------------------------------
    # Keyframe management
    # ------------------------------------------------------------------

    def add_keyframe(
        self,
        sequence_id: str,
        track_id: str,
        time: float,
        value: Dict[str, Any],
        interpolation: str = "step",
        duration: float = 0.0,
    ) -> Optional[Keyframe]:
        """Add a keyframe to a track at the given time."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return None
            track = None
            for t in seq.tracks:
                if t.track_id == track_id:
                    track = t
                    break
            if track is None:
                return None
            kf = Keyframe(
                keyframe_id=_new_id("kf"),
                time=max(0.0, float(time)),
                value=dict(value) if value else {},
                interpolation=interpolation,
                duration=max(0.0, float(duration)),
            )
            track.keyframes.append(kf)
            track.keyframes.sort(key=lambda k: k.time)
            seq.updated_at = _now()
            self._keyframe_counter += 1
            self._record_event(
                SequencerEventKind.KEYFRAME_ADDED,
                {"sequence_id": sequence_id, "track_id": track_id, "keyframe_id": kf.keyframe_id},
            )
            return kf

    def remove_keyframe(self, sequence_id: str, track_id: str, keyframe_id: str) -> bool:
        """Remove a keyframe from a track."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return False
            for t in seq.tracks:
                if t.track_id == track_id:
                    before = len(t.keyframes)
                    t.keyframes = [k for k in t.keyframes if k.keyframe_id != keyframe_id]
                    if len(t.keyframes) < before:
                        seq.updated_at = _now()
                        return True
                    return False
            return False

    # ------------------------------------------------------------------
    # Playback control
    # ------------------------------------------------------------------

    def play(self, sequence_id: str) -> Optional[PlaybackState]:
        """Start playing a sequence from the beginning."""
        with self._lock:
            seq = self._sequences.get(sequence_id)
            if seq is None:
                return None
            pb_id = _new_id("pb")
            now = _now()
            pb = PlaybackState(
                playback_id=pb_id,
                sequence_id=sequence_id,
                status=PlaybackStatus.PLAYING,
                current_time=0.0,
                direction=1,
                fired_keyframe_ids=[],
                started_at=now,
                last_ticked_at=now,
            )
            self._playbacks[pb_id] = pb
            self._playback_counter += 1
            self._playbacks_started += 1
            _evict_fifo_dict(self._playbacks, _MAX_PLAYBACKS)
            self._record_event(
                SequencerEventKind.PLAYBACK_STARTED,
                {"playback_id": pb_id, "sequence_id": sequence_id},
            )
            return pb

    def pause(self, playback_id: str) -> Optional[PlaybackState]:
        """Pause a playing sequence."""
        with self._lock:
            pb = self._playbacks.get(playback_id)
            if pb is None:
                return None
            if pb.status != PlaybackStatus.PLAYING:
                return pb
            pb.status = PlaybackStatus.PAUSED
            self._record_event(
                SequencerEventKind.PLAYBACK_PAUSED,
                {"playback_id": playback_id},
            )
            return pb

    def resume(self, playback_id: str) -> Optional[PlaybackState]:
        """Resume a paused sequence."""
        with self._lock:
            pb = self._playbacks.get(playback_id)
            if pb is None:
                return None
            if pb.status != PlaybackStatus.PAUSED:
                return pb
            pb.status = PlaybackStatus.PLAYING
            self._record_event(
                SequencerEventKind.PLAYBACK_RESUMED,
                {"playback_id": playback_id},
            )
            return pb

    def stop(self, playback_id: str) -> Optional[PlaybackState]:
        """Stop a sequence playback."""
        with self._lock:
            pb = self._playbacks.pop(playback_id, None)
            if pb is None:
                return None
            pb.status = PlaybackStatus.STOPPED
            self._record_event(
                SequencerEventKind.PLAYBACK_STOPPED,
                {"playback_id": playback_id},
            )
            return pb

    def seek(self, playback_id: str, time: float) -> Optional[PlaybackState]:
        """Seek to a specific time in the sequence."""
        with self._lock:
            pb = self._playbacks.get(playback_id)
            if pb is None:
                return None
            pb.current_time = max(0.0, float(time))
            pb.fired_keyframe_ids = []
            self._record_event(
                SequencerEventKind.PLAYBACK_SEEKED,
                {"playback_id": playback_id, "time": pb.current_time},
            )
            return pb

    def get_playback(self, playback_id: str) -> Optional[PlaybackState]:
        """Return the playback state for a given playback id."""
        with self._lock:
            return self._playbacks.get(playback_id)

    def list_playbacks(self) -> List[PlaybackState]:
        """Return all active playbacks."""
        with self._lock:
            return list(self._playbacks.values())

    # ------------------------------------------------------------------
    # Tick / update
    # ------------------------------------------------------------------

    def tick(self, playback_id: str, delta_time: float) -> List[Keyframe]:
        """Advance a playback by ``delta_time`` seconds and return fired keyframes.

        This method should be called from the game loop with the frame
        delta time. It advances the playback's current time, checks all
        tracks for keyframes that should fire, and returns the list of
        keyframes that fired during this tick. Handles looping according
        to the sequence's loop mode.
        """
        with self._lock:
            pb = self._playbacks.get(playback_id)
            if pb is None or pb.status != PlaybackStatus.PLAYING:
                return []
            seq = self._sequences.get(pb.sequence_id)
            if seq is None:
                return []

            dt = max(0.0, float(delta_time)) * seq.playback_speed
            old_time = pb.current_time
            new_time = old_time + dt * pb.direction
            seq_duration = seq.duration

            fired: List[Keyframe] = []

            if seq_duration <= 0:
                pb.current_time = 0.0
            else:
                if new_time >= seq_duration:
                    if seq.loop_mode == LoopMode.LOOP:
                        pb.current_time = new_time % seq_duration
                        pb.fired_keyframe_ids = []
                    elif seq.loop_mode == LoopMode.PING_PONG:
                        pb.direction = -1
                        pb.current_time = seq_duration - (new_time - seq_duration)
                        pb.fired_keyframe_ids = []
                    else:
                        pb.current_time = seq_duration
                        pb.status = PlaybackStatus.COMPLETED
                        self._playbacks_completed += 1
                        self._record_event(
                            SequencerEventKind.PLAYBACK_COMPLETED,
                            {"playback_id": playback_id},
                        )
                elif new_time <= 0 and pb.direction < 0:
                    if seq.loop_mode == LoopMode.PING_PONG:
                        pb.direction = 1
                        pb.current_time = 0.0
                        pb.fired_keyframe_ids = []
                    else:
                        pb.current_time = 0.0
                else:
                    pb.current_time = new_time

            time_lo = min(old_time, pb.current_time)
            time_hi = max(old_time, pb.current_time)

            for track in seq.tracks:
                if not track.enabled:
                    continue
                for kf in track.keyframes:
                    if kf.keyframe_id in pb.fired_keyframe_ids:
                        continue
                    if time_lo <= kf.time <= time_hi:
                        pb.fired_keyframe_ids.append(kf.keyframe_id)
                        fired.append(kf)
                        self._record_event(
                            SequencerEventKind.KEYFRAME_FIRED,
                            {
                                "playback_id": playback_id,
                                "track_id": track.track_id,
                                "keyframe_id": kf.keyframe_id,
                                "time": kf.time,
                            },
                        )

            pb.last_ticked_at = _now()
            return fired

    def tick_all(self, delta_time: float) -> Dict[str, List[Keyframe]]:
        """Advance all active playbacks by ``delta_time`` seconds.

        Returns a dict mapping playback_id to the list of keyframes that
        fired during this tick for that playback.
        """
        with self._lock:
            results: Dict[str, List[Keyframe]] = {}
            for pb_id in list(self._playbacks.keys()):
                fired = self.tick(pb_id, delta_time)
                if fired:
                    results[pb_id] = fired
            return results

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def list_events(self, limit: int = 50) -> List[SequencerEvent]:
        """Return the most recent sequencer lifecycle events."""
        with self._lock:
            limit = max(1, min(int(limit), _MAX_EVENTS))
            return list(self._events)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Return a compact status summary for monitoring."""
        with self._lock:
            total_tracks = sum(len(s.tracks) for s in self._sequences.values())
            total_kfs = sum(
                len(t.keyframes)
                for s in self._sequences.values()
                for t in s.tracks
            )
            return {
                "initialized": self._initialized,
                "total_sequences": len(self._sequences),
                "total_tracks": total_tracks,
                "total_keyframes": total_kfs,
                "active_playbacks": len(self._playbacks),
                "total_events": len(self._events),
                "sequence_counter": self._sequence_counter,
                "track_counter": self._track_counter,
                "keyframe_counter": self._keyframe_counter,
                "playback_counter": self._playback_counter,
                "playbacks_started": self._playbacks_started,
                "playbacks_completed": self._playbacks_completed,
                "event_counter": self._event_counter,
                "capacities": {
                    "max_sequences": _MAX_SEQUENCES,
                    "max_playbacks": _MAX_PLAYBACKS,
                    "max_events": _MAX_EVENTS,
                },
            }

    def get_stats(self) -> SequencerStats:
        """Return aggregate sequencer statistics."""
        with self._lock:
            total_tracks = sum(len(s.tracks) for s in self._sequences.values())
            total_kfs = sum(
                len(t.keyframes)
                for s in self._sequences.values()
                for t in s.tracks
            )
            return SequencerStats(
                total_sequences=len(self._sequences),
                total_tracks=total_tracks,
                total_keyframes=total_kfs,
                active_playbacks=len(self._playbacks),
                total_playbacks_started=self._playbacks_started,
                total_playbacks_completed=self._playbacks_completed,
                total_events=len(self._events),
            )

    def reset(self) -> None:
        """Reset the sequencer to its seeded state."""
        with self._lock:
            self._sequences.clear()
            self._playbacks.clear()
            self._events.clear()
            self._sequence_counter = 0
            self._track_counter = 0
            self._keyframe_counter = 0
            self._playback_counter = 0
            self._playbacks_started = 0
            self._playbacks_completed = 0
            self._event_counter = 0
            self._seed_data()


# ---------------------------------------------------------------------------
# Enum resolvers
# ---------------------------------------------------------------------------


def _resolve_track_type(value: Union[TrackType, str, None]) -> Optional[TrackType]:
    """Coerce a value into a :class:`TrackType` enum instance."""
    if value is None:
        return None
    if isinstance(value, TrackType):
        return value
    if isinstance(value, str):
        try:
            return TrackType(value)
        except ValueError:
            return None
    return None


def _resolve_loop(value: Union[LoopMode, str, None]) -> Optional[LoopMode]:
    """Coerce a value into a :class:`LoopMode` enum instance."""
    if value is None:
        return None
    if isinstance(value, LoopMode):
        return value
    if isinstance(value, str):
        try:
            return LoopMode(value)
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# Module-level singleton accessor
# ---------------------------------------------------------------------------


def get_timeline_sequencer() -> TimelineSequencer:
    """Return the shared :class:`TimelineSequencer` singleton instance."""
    return TimelineSequencer()
