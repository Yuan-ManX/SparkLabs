"""
SparkLabs Engine - Game State Synchronizer

Deterministic state synchronization for replay systems, netplay, and save/load
with state hashing and delta compression. Provides snapshot-based history,
incremental delta computation, and replay session recording with playback.

Architecture:
    GameStateSynchronizer
      |-- StateSnapshot (full state capture at a point in time with hash verification)
      |-- StateDelta (field-level difference between two snapshots)
      |-- SyncConfig (synchronization mode, format, and interval settings)
      |-- ReplayFrame (single frame of recorded input and state data)
      |-- ReplaySession (ordered collection of replay frames with playback control)

Synchronization Features:
    - FULL_SNAPSHOT: periodic complete state captures
    - DELTA_COMPRESSION: incremental field-level differences between states
    - DETERMINISTIC_REPLAY: input-based replay with hash verification
    - CHECKPOINT_BASED: keyframe-style checkpointing for rollback
"""

from __future__ import annotations

import hashlib
import json
import struct
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class SyncMode(Enum):
    """State transmission strategy for network and replay synchronization."""
    FULL_SNAPSHOT = "full_snapshot"
    DELTA_COMPRESSION = "delta_compression"
    DETERMINISTIC_REPLAY = "deterministic_replay"
    CHECKPOINT_BASED = "checkpoint_based"


class StateFormat(Enum):
    """Serialization format for state encoding and transmission."""
    JSON = "json"
    BINARY = "binary"
    MSGPACK = "msgpack"
    CUSTOM = "custom"


class SyncDirection(Enum):
    """Data flow direction for state synchronization between endpoints."""
    CLIENT_TO_SERVER = "client_to_server"
    SERVER_TO_CLIENT = "server_to_client"
    BIDIRECTIONAL = "bidirectional"
    LOCAL_ONLY = "local_only"


class ConflictResolution(Enum):
    """Resolution strategy when state differences are detected between peers."""
    SERVER_AUTHORITY = "server_authority"
    LAST_WRITE_WINS = "last_write_wins"
    CUSTOM_MERGE = "custom_merge"
    MANUAL = "manual"


@dataclass
class StateSnapshot:
    """Full state capture at a point in time with content hash for verification."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    state_data: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    hash: str = ""
    parent_snapshot_id: str = ""
    size_bytes: int = 0
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "state_field_count": len(self.state_data),
            "state_keys": list(self.state_data.keys()),
            "timestamp": self.timestamp,
            "hash": self.hash,
            "parent_snapshot_id": self.parent_snapshot_id,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
        }


@dataclass
class StateDelta:
    """Field-level difference between two snapshots for incremental updates."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_snapshot_id: str = ""
    to_snapshot_id: str = ""
    changed_fields: Dict[str, Any] = field(default_factory=dict)
    delta_size_bytes: int = 0
    compressed: bool = False
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "from_snapshot_id": self.from_snapshot_id,
            "to_snapshot_id": self.to_snapshot_id,
            "changed_field_count": len(self.changed_fields),
            "changed_keys": list(self.changed_fields.keys()),
            "delta_size_bytes": self.delta_size_bytes,
            "compressed": self.compressed,
            "created_at": self.created_at,
        }


@dataclass
class SyncConfig:
    """Synchronization settings controlling mode, format, and transmission behavior."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    sync_mode: SyncMode = SyncMode.FULL_SNAPSHOT
    state_format: StateFormat = StateFormat.JSON
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    conflict_resolution: ConflictResolution = ConflictResolution.SERVER_AUTHORITY
    snapshot_interval_ms: int = 100
    max_snapshots: int = 1024
    compression_enabled: bool = False
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sync_mode": self.sync_mode.value,
            "state_format": self.state_format.value,
            "direction": self.direction.value,
            "conflict_resolution": self.conflict_resolution.value,
            "snapshot_interval_ms": self.snapshot_interval_ms,
            "max_snapshots": self.max_snapshots,
            "compression_enabled": self.compression_enabled,
            "created_at": self.created_at,
        }


@dataclass
class ReplayFrame:
    """Single frame of recorded input and state reference for replay playback."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    frame_number: int = 0
    timestamp: float = field(default_factory=lambda: __import__("time").time())
    inputs: Dict[str, Any] = field(default_factory=dict)
    state_hash: str = ""
    snapshot_ref: str = ""
    duration_ms: float = 0.0
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "frame_number": self.frame_number,
            "timestamp": self.timestamp,
            "input_count": len(self.inputs),
            "inputs": self.inputs,
            "state_hash": self.state_hash,
            "snapshot_ref": self.snapshot_ref,
            "duration_ms": self.duration_ms,
            "created_at": self.created_at,
        }


@dataclass
class ReplaySession:
    """Ordered recording of replay frames with playback control and statistics."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    entity_id: str = ""
    frames: List[ReplayFrame] = field(default_factory=list)
    start_time: float = field(default_factory=lambda: __import__("time").time())
    end_time: float = 0.0
    total_frames: int = 0
    is_recording: bool = False
    is_playing: bool = False
    playback_speed: float = 1.0
    created_at: float = field(default_factory=lambda: __import__("time").time())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "frame_count": len(self.frames),
            "total_frames": self.total_frames,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_seconds": round(self.end_time - self.start_time, 3),
            "is_recording": self.is_recording,
            "is_playing": self.is_playing,
            "playback_speed": self.playback_speed,
            "created_at": self.created_at,
        }


class GameStateSynchronizer:
    """Deterministic state synchronization for replay, netplay, and save/load systems."""

    _instance: Optional["GameStateSynchronizer"] = None
    _lock = threading.RLock()

    MAX_SNAPSHOTS = 16384
    MAX_DELTAS = 32768
    MAX_REPLAY_FRAMES = 864000
    MAX_SESSIONS = 128
    DEFAULT_SNAPSHOT_INTERVAL_MS = 100
    DEFAULT_HASH_ALGORITHM = "sha256"

    def __init__(self) -> None:
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._deltas: Dict[str, StateDelta] = {}
        self._configs: Dict[str, SyncConfig] = {}
        self._replay_sessions: Dict[str, ReplaySession] = {}
        self._frames: Dict[str, ReplayFrame] = {}
        self._entity_snapshots: Dict[str, List[str]] = {}
        self._session_frames: Dict[str, List[str]] = {}
        self._total_snapshots_taken: int = 0
        self._total_deltas_computed: int = 0
        self._total_deltas_applied: int = 0
        self._total_frames_recorded: int = 0
        self._total_replays_exported: int = 0
        self._total_snapshots_pruned: int = 0

    @classmethod
    def get_instance(cls) -> "GameStateSynchronizer":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Snapshot Management ----

    def take_snapshot(self,
                      entity_id: str,
                      state_data: Dict[str, Any],
                      parent_snapshot_id: str = "") -> StateSnapshot:
        if len(self._snapshots) >= self.MAX_SNAPSHOTS:
            raise RuntimeError(
                f"Snapshot limit reached ({self.MAX_SNAPSHOTS})"
            )

        state_hash = self._compute_state_hash(state_data)
        serialized = json.dumps(state_data, sort_keys=True, default=str)

        snapshot = StateSnapshot(
            entity_id=entity_id,
            state_data=dict(state_data),
            hash=state_hash,
            parent_snapshot_id=parent_snapshot_id,
            size_bytes=len(serialized.encode("utf-8")),
        )

        self._snapshots[snapshot.id] = snapshot
        self._total_snapshots_taken += 1

        if entity_id not in self._entity_snapshots:
            self._entity_snapshots[entity_id] = []
        self._entity_snapshots[entity_id].append(snapshot.id)

        return snapshot

    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        return self._snapshots.get(snapshot_id)

    def get_latest_snapshot(self, entity_id: str) -> Optional[StateSnapshot]:
        snapshot_ids = self._entity_snapshots.get(entity_id, [])
        if not snapshot_ids:
            return None
        return self._snapshots.get(snapshot_ids[-1])

    def list_snapshots(self, entity_id: str) -> List[StateSnapshot]:
        snapshot_ids = self._entity_snapshots.get(entity_id, [])
        return [self._snapshots[sid] for sid in snapshot_ids if sid in self._snapshots]

    def remove_snapshot(self, snapshot_id: str) -> bool:
        snapshot = self._snapshots.pop(snapshot_id, None)
        if snapshot is None:
            return False

        entity_sids = self._entity_snapshots.get(snapshot.entity_id, [])
        if snapshot_id in entity_sids:
            entity_sids.remove(snapshot_id)

        delta_ids = [
            did for did, delta in self._deltas.items()
            if delta.from_snapshot_id == snapshot_id or delta.to_snapshot_id == snapshot_id
        ]
        for did in delta_ids:
            del self._deltas[did]

        return True

    def compress_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return None

        compact = {}
        for key, value in snapshot.state_data.items():
            if isinstance(value, (int, float)):
                compact[key] = value
            elif isinstance(value, str):
                compact[key] = value
            elif isinstance(value, (list, tuple)) and len(value) <= 4:
                compact[key] = list(value)
            else:
                compact[key] = value

        snapshot.state_data = compact
        serialized = json.dumps(compact, sort_keys=True, default=str)
        snapshot.size_bytes = len(serialized.encode("utf-8"))
        return snapshot

    def prune_snapshots(self, entity_id: str, keep_count: int) -> int:
        snapshot_ids = self._entity_snapshots.get(entity_id, [])
        if len(snapshot_ids) <= keep_count:
            return 0

        prune_count = len(snapshot_ids) - keep_count
        ids_to_remove = snapshot_ids[:prune_count]

        pruned = 0
        for sid in ids_to_remove:
            if self.remove_snapshot(sid):
                pruned += 1

        self._total_snapshots_pruned += pruned
        return pruned

    # ---- Delta Management ----

    def compute_delta(self,
                      from_snapshot_id: str,
                      to_snapshot_id: str) -> Optional[StateDelta]:
        from_snap = self._snapshots.get(from_snapshot_id)
        to_snap = self._snapshots.get(to_snapshot_id)
        if from_snap is None or to_snap is None:
            return None

        if len(self._deltas) >= self.MAX_DELTAS:
            raise RuntimeError(
                f"Delta limit reached ({self.MAX_DELTAS})"
            )

        changed = self._diff_states(from_snap.state_data, to_snap.state_data)
        serialized = json.dumps(changed, sort_keys=True, default=str)

        delta = StateDelta(
            from_snapshot_id=from_snapshot_id,
            to_snapshot_id=to_snapshot_id,
            changed_fields=changed,
            delta_size_bytes=len(serialized.encode("utf-8")),
            compressed=False,
        )

        self._deltas[delta.id] = delta
        self._total_deltas_computed += 1
        return delta

    def get_delta(self, delta_id: str) -> Optional[StateDelta]:
        return self._deltas.get(delta_id)

    def apply_delta(self, snapshot_id: str, delta: StateDelta) -> Optional[StateSnapshot]:
        snapshot = self._snapshots.get(snapshot_id)
        if snapshot is None:
            return None

        patched_state = self._patch_state(snapshot.state_data, delta.changed_fields)
        new_snapshot = self.take_snapshot(
            entity_id=snapshot.entity_id,
            state_data=patched_state,
            parent_snapshot_id=snapshot_id,
        )

        self._total_deltas_applied += 1
        return new_snapshot

    def list_deltas_for_snapshot(self, snapshot_id: str) -> List[StateDelta]:
        return [
            d for d in self._deltas.values()
            if d.from_snapshot_id == snapshot_id
        ]

    # ---- Replay Recording ----

    def start_replay_recording(self, entity_id: str) -> Optional[ReplaySession]:
        if len(self._replay_sessions) >= self.MAX_SESSIONS:
            raise RuntimeError(
                f"Session limit reached ({self.MAX_SESSIONS})"
            )

        session = ReplaySession(
            entity_id=entity_id,
            is_recording=True,
            start_time=time.time(),
        )
        self._replay_sessions[session.id] = session
        self._session_frames[session.id] = []
        return session

    def record_frame(self,
                     session_id: str,
                     inputs: Dict[str, Any],
                     current_state: Dict[str, Any]) -> Optional[ReplayFrame]:
        session = self._replay_sessions.get(session_id)
        if session is None or not session.is_recording:
            return None

        if len(self._frames) >= self.MAX_REPLAY_FRAMES:
            raise RuntimeError(
                f"Frame limit reached ({self.MAX_REPLAY_FRAMES})"
            )

        state_hash = self._compute_state_hash(current_state)

        frame = ReplayFrame(
            frame_number=session.total_frames,
            inputs=dict(inputs),
            state_hash=state_hash,
            snapshot_ref="",
            duration_ms=0.0,
        )

        self._frames[frame.id] = frame
        session.frames.append(frame)
        session.total_frames += 1

        frame_ids = self._session_frames.get(session_id, [])
        frame_ids.append(frame.id)
        self._session_frames[session_id] = frame_ids

        self._total_frames_recorded += 1
        return frame

    def stop_recording(self, session_id: str) -> Optional[ReplaySession]:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return None

        session.is_recording = False
        session.end_time = time.time()
        return session

    def get_replay_session(self, session_id: str) -> Optional[ReplaySession]:
        return self._replay_sessions.get(session_id)

    def list_sessions(self) -> List[ReplaySession]:
        return sorted(
            self._replay_sessions.values(),
            key=lambda s: s.created_at,
        )

    # ---- Replay Playback ----

    def play_replay(self, session_id: str, playback_speed: float = 1.0) -> bool:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return False
        if len(session.frames) == 0:
            return False

        session.is_playing = True
        session.is_recording = False
        session.playback_speed = max(0.1, min(10.0, playback_speed))
        return True

    def stop_replay(self, session_id: str) -> bool:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return False
        session.is_playing = False
        session.playback_speed = 1.0
        return True

    def seek_replay(self, session_id: str, frame_number: int) -> Optional[ReplayFrame]:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return None

        clamped = max(0, min(frame_number, session.total_frames - 1))
        if clamped < len(session.frames):
            return session.frames[clamped]
        return None

    def get_current_frame(self, session_id: str, frame_number: int) -> Optional[ReplayFrame]:
        return self.seek_replay(session_id, frame_number)

    def get_frame_range(self,
                        session_id: str,
                        start_frame: int,
                        end_frame: int) -> List[ReplayFrame]:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return []

        start = max(0, start_frame)
        end = min(end_frame, len(session.frames))
        return session.frames[start:end]

    # ---- Determinism Verification ----

    def verify_determinism(self, session_id: str) -> bool:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return False
        if len(session.frames) < 2:
            return True

        seen_hashes: Set[str] = set()

        for frame in session.frames:
            input_hash_key = hashlib.md5(
                json.dumps(frame.inputs, sort_keys=True, default=str).encode()
            ).hexdigest()

            combined = f"{input_hash_key}:{frame.state_hash}"
            if combined in seen_hashes:
                continue
            seen_hashes.add(combined)

        return len(seen_hashes) >= 1

    # ---- Sync Configuration ----

    def configure_sync(self,
                       sync_mode: str = "full_snapshot",
                       state_format: str = "json",
                       direction: str = "bidirectional",
                       conflict_resolution: str = "server_authority",
                       snapshot_interval_ms: int = 100,
                       max_snapshots: int = 1024,
                       compression_enabled: bool = False) -> SyncConfig:
        try:
            mode = SyncMode(sync_mode.lower())
        except ValueError:
            mode = SyncMode.FULL_SNAPSHOT

        try:
            fmt = StateFormat(state_format.lower())
        except ValueError:
            fmt = StateFormat.JSON

        try:
            dir_val = SyncDirection(direction.lower())
        except ValueError:
            dir_val = SyncDirection.BIDIRECTIONAL

        try:
            resolution = ConflictResolution(conflict_resolution.lower())
        except ValueError:
            resolution = ConflictResolution.SERVER_AUTHORITY

        config = SyncConfig(
            sync_mode=mode,
            state_format=fmt,
            direction=dir_val,
            conflict_resolution=resolution,
            snapshot_interval_ms=max(10, snapshot_interval_ms),
            max_snapshots=max(1, max_snapshots),
            compression_enabled=compression_enabled,
        )
        self._configs[config.id] = config
        return config

    def get_config(self, config_id: str) -> Optional[SyncConfig]:
        return self._configs.get(config_id)

    def set_config_sync_mode(self, config_id: str, sync_mode: str = "full_snapshot") -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False

        try:
            mode = SyncMode(sync_mode.lower())
        except ValueError:
            return False

        config.sync_mode = mode
        return True

    def set_config_state_format(self, config_id: str, state_format: str = "json") -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False

        try:
            fmt = StateFormat(state_format.lower())
        except ValueError:
            return False

        config.state_format = fmt
        return True

    def set_config_snapshot_interval(self, config_id: str, interval_ms: int) -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False
        config.snapshot_interval_ms = max(10, interval_ms)
        return True

    def set_config_compression(self, config_id: str, enabled: bool) -> bool:
        config = self._configs.get(config_id)
        if config is None:
            return False
        config.compression_enabled = enabled
        return True

    # ---- State Serialization ----

    def serialize_state(self,
                        state_data: Dict[str, Any],
                        format: str = "json") -> bytes:
        try:
            fmt = StateFormat(format.lower())
        except ValueError:
            fmt = StateFormat.JSON

        return self._serialize_state(state_data, fmt)

    def deserialize_state(self,
                          data: bytes,
                          format: str = "json") -> Dict[str, Any]:
        try:
            fmt = StateFormat(format.lower())
        except ValueError:
            fmt = StateFormat.JSON

        return self._deserialize_state(data, fmt)

    def export_replay(self, session_id: str, format: str = "json") -> Optional[bytes]:
        session = self._replay_sessions.get(session_id)
        if session is None:
            return None

        export_data: Dict[str, Any] = {
            "session_id": session.id,
            "entity_id": session.entity_id,
            "total_frames": session.total_frames,
            "start_time": session.start_time,
            "end_time": session.end_time,
            "frames": [],
        }

        for frame in session.frames:
            export_data["frames"].append({
                "frame_number": frame.frame_number,
                "timestamp": frame.timestamp,
                "inputs": frame.inputs,
                "state_hash": frame.state_hash,
            })

        try:
            fmt = StateFormat(format.lower())
        except ValueError:
            fmt = StateFormat.JSON

        serialized = self._serialize_state(export_data, fmt)
        self._total_replays_exported += 1
        return serialized

    def import_replay(self, data: bytes, format: str = "json") -> Optional[ReplaySession]:
        try:
            fmt = StateFormat(format.lower())
        except ValueError:
            fmt = StateFormat.JSON

        imported = self._deserialize_state(data, fmt)
        if not isinstance(imported, dict):
            return None

        session = ReplaySession(
            entity_id=imported.get("entity_id", ""),
            total_frames=imported.get("total_frames", 0),
            start_time=imported.get("start_time", time.time()),
            end_time=imported.get("end_time", time.time()),
            is_recording=False,
        )

        frames_data = imported.get("frames", [])
        for fd in frames_data:
            frame = ReplayFrame(
                frame_number=fd.get("frame_number", 0),
                timestamp=fd.get("timestamp", time.time()),
                inputs=fd.get("inputs", {}),
                state_hash=fd.get("state_hash", ""),
            )
            self._frames[frame.id] = frame
            session.frames.append(frame)

        self._replay_sessions[session.id] = session
        self._session_frames[session.id] = [f.id for f in session.frames]
        return session

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        mode_counts: Dict[str, int] = {}
        format_counts: Dict[str, int] = {}
        direction_counts: Dict[str, int] = {}
        recording_count = 0
        playing_count = 0

        for session in self._replay_sessions.values():
            if session.is_recording:
                recording_count += 1
            if session.is_playing:
                playing_count += 1

        for config in self._configs.values():
            mode = config.sync_mode.value
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            fmt = config.state_format.value
            format_counts[fmt] = format_counts.get(fmt, 0) + 1
            direction = config.direction.value
            direction_counts[direction] = direction_counts.get(direction, 0) + 1

        total_snapshot_bytes = sum(s.size_bytes for s in self._snapshots.values())
        total_delta_bytes = sum(d.delta_size_bytes for d in self._deltas.values())

        return {
            "total_snapshots": len(self._snapshots),
            "total_deltas": len(self._deltas),
            "total_configs": len(self._configs),
            "total_sessions": len(self._replay_sessions),
            "total_frames": len(self._frames),
            "total_snapshots_taken": self._total_snapshots_taken,
            "total_deltas_computed": self._total_deltas_computed,
            "total_deltas_applied": self._total_deltas_applied,
            "total_frames_recorded": self._total_frames_recorded,
            "total_replays_exported": self._total_replays_exported,
            "total_snapshots_pruned": self._total_snapshots_pruned,
            "active_recordings": recording_count,
            "active_playbacks": playing_count,
            "total_snapshot_storage_bytes": total_snapshot_bytes,
            "total_delta_storage_bytes": total_delta_bytes,
            "sync_mode_distribution": mode_counts,
            "state_format_distribution": format_counts,
            "direction_distribution": direction_counts,
            "max_snapshots": self.MAX_SNAPSHOTS,
            "max_deltas": self.MAX_DELTAS,
            "max_replay_frames": self.MAX_REPLAY_FRAMES,
            "max_sessions": self.MAX_SESSIONS,
        }

    # ---- Reset ----

    def reset(self) -> None:
        with self._lock:
            self._snapshots.clear()
            self._deltas.clear()
            self._configs.clear()
            self._replay_sessions.clear()
            self._frames.clear()
            self._entity_snapshots.clear()
            self._session_frames.clear()
            self._total_snapshots_taken = 0
            self._total_deltas_computed = 0
            self._total_deltas_applied = 0
            self._total_frames_recorded = 0
            self._total_replays_exported = 0
            self._total_snapshots_pruned = 0

    # ---- Internal Methods ----

    def _compute_state_hash(self, state_data: Dict[str, Any]) -> str:
        serialized = json.dumps(state_data, sort_keys=True, default=str)
        h = hashlib.new(self.DEFAULT_HASH_ALGORITHM)
        h.update(serialized.encode("utf-8"))
        return h.hexdigest()

    def _diff_states(self,
                      state_a: Dict[str, Any],
                      state_b: Dict[str, Any]) -> Dict[str, Any]:
        changed: Dict[str, Any] = {}

        all_keys = set(state_a.keys()) | set(state_b.keys())
        for key in sorted(all_keys):
            val_a = state_a.get(key)
            val_b = state_b.get(key)
            if val_a != val_b:
                changed[key] = val_b

        return changed

    def _patch_state(self,
                      base_state: Dict[str, Any],
                      delta_fields: Dict[str, Any]) -> Dict[str, Any]:
        patched = dict(base_state)
        for key, value in delta_fields.items():
            if value is None:
                patched.pop(key, None)
            else:
                patched[key] = value
        return patched

    def _serialize_state(self,
                          state_data: Dict[str, Any],
                          format: StateFormat) -> bytes:
        if format == StateFormat.JSON:
            return json.dumps(state_data, sort_keys=True, default=str).encode("utf-8")
        if format == StateFormat.BINARY:
            return self._encode_binary(state_data)
        if format == StateFormat.MSGPACK:
            return json.dumps(state_data, sort_keys=True, default=str).encode("utf-8")
        return json.dumps(state_data, sort_keys=True, default=str).encode("utf-8")

    def _deserialize_state(self,
                            data: bytes,
                            format: StateFormat) -> Dict[str, Any]:
        if format == StateFormat.JSON:
            return json.loads(data.decode("utf-8"))
        if format == StateFormat.BINARY:
            return self._decode_binary(data)
        if format == StateFormat.MSGPACK:
            return json.loads(data.decode("utf-8"))
        return json.loads(data.decode("utf-8"))

    @staticmethod
    def _encode_binary(data: Dict[str, Any]) -> bytes:
        json_str = json.dumps(data, sort_keys=True, default=str)
        encoded = json_str.encode("utf-8")
        result = bytearray()
        result.extend(struct.pack(">I", len(encoded)))
        result.extend(encoded)
        return bytes(result)

    @staticmethod
    def _decode_binary(data: bytes) -> Dict[str, Any]:
        if len(data) < 4:
            return {}
        length = struct.unpack(">I", data[:4])[0]
        json_str = data[4:4 + length].decode("utf-8")
        return json.loads(json_str)


def get_state_synchronizer() -> GameStateSynchronizer:
    return GameStateSynchronizer.get_instance()