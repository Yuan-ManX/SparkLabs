"""
Session Snapshot - Per-session JSON persistence for agent state recovery
and cross-session continuity within SparkLabs AI game development studio.

Architecture:
    SessionSnapshotSystem/
    |-- SnapshotMode (FULL, DELTA, CHECKPOINT enumeration)
    |-- SnapshotState (ACTIVE, ARCHIVED, CORRUPT enumeration)
    |-- CompressionType (NONE, GZIP, ZSTD enumeration)
    |-- SessionSnapshot (complete state capture dataclass)
    |-- SnapshotDelta (incremental change record dataclass)
    |-- RecoveryPoint (automatic safe-state marker dataclass)
    |-- SessionMetadata (session context descriptor dataclass)
    |-- SessionSnapshotSystem (global snapshot orchestration)

Captures agent operational state at arbitrary granularity for hot-reload
recovery, cross-session handoff, and multi-agent workspace continuity.
Supports full snapshots, delta-based incremental saves, and labeled
checkpoints for iterative game development workflows.
"""

from __future__ import annotations

import uuid
import time
import json
import zlib
import hashlib
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple


class SnapshotMode(Enum):
    FULL = auto()
    DELTA = auto()
    CHECKPOINT = auto()


class SnapshotState(Enum):
    ACTIVE = auto()
    ARCHIVED = auto()
    CORRUPT = auto()


class CompressionType(Enum):
    NONE = auto()
    GZIP = auto()
    ZSTD = auto()


@dataclass
class SessionMetadata:
    session_id: str = ""
    agent_id: str = ""
    project_name: str = ""
    created_at: float = 0.0
    last_snapshot_at: float = 0.0
    snapshot_count: int = 0
    total_size_bytes: int = 0
    tags: List[str] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "project_name": self.project_name,
            "created_at": self.created_at,
            "last_snapshot_at": self.last_snapshot_at,
            "snapshot_count": self.snapshot_count,
            "total_size_bytes": self.total_size_bytes,
            "tags": self.tags,
        }


@dataclass
class SessionSnapshot:
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    agent_id: str = ""
    mode: SnapshotMode = SnapshotMode.FULL
    state: SnapshotState = SnapshotState.ACTIVE
    compression: CompressionType = CompressionType.NONE
    version: int = 1
    label: str = ""
    created_at: float = 0.0
    state_data: Dict[str, Any] = field(default_factory=dict)
    agent_context: Dict[str, Any] = field(default_factory=dict)
    tool_state: Dict[str, Any] = field(default_factory=dict)
    memory_state: Dict[str, Any] = field(default_factory=dict)
    engine_state: Dict[str, Any] = field(default_factory=dict)
    parent_snapshot_id: Optional[str] = None
    content_hash: str = ""
    size_bytes: int = 0
    tags: List[str] = field(default_factory=list)

    def compute_hash(self) -> str:
        raw = json.dumps({
            "state_data": self.state_data,
            "agent_context": self.agent_context,
            "tool_state": self.tool_state,
            "memory_state": self.memory_state,
            "engine_state": self.engine_state,
        }, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "mode": self.mode.name,
            "state": self.state.name,
            "compression": self.compression.name,
            "version": self.version,
            "label": self.label,
            "age_seconds": round(time.time() - self.created_at, 1),
            "size_bytes": self.size_bytes,
            "parent_id": self.parent_snapshot_id,
            "content_hash": self.content_hash[:16],
            "tags": self.tags,
        }


@dataclass
class SnapshotDelta:
    delta_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    from_snapshot_id: str = ""
    to_snapshot_id: str = ""
    session_id: str = ""
    version: int = 1
    created_at: float = 0.0
    changed_keys: List[str] = field(default_factory=list)
    added_keys: List[str] = field(default_factory=list)
    removed_keys: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    size_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "from": self.from_snapshot_id,
            "to": self.to_snapshot_id,
            "session_id": self.session_id,
            "version": self.version,
            "changed": len(self.changed_keys),
            "added": len(self.added_keys),
            "removed": len(self.removed_keys),
            "size_bytes": self.size_bytes,
        }


@dataclass
class RecoveryPoint:
    recovery_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    snapshot_id: str = ""
    label: str = ""
    created_at: float = 0.0
    is_auto: bool = False
    trigger_reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recovery_id": self.recovery_id,
            "snapshot_id": self.snapshot_id,
            "label": self.label,
            "auto": self.is_auto,
            "trigger": self.trigger_reason,
            "age_seconds": round(time.time() - self.created_at, 1),
        }


class SessionSnapshotSystem:
    _instance: Optional["SessionSnapshotSystem"] = None
    _lock = threading.RLock()
    _MAX_SNAPSHOTS_PER_SESSION = 100
    _MAX_DELTAS_PER_SESSION = 200
    _RECOVERY_POINT_INTERVAL = 10

    def __init__(self):
        self._snapshots: Dict[str, List[SessionSnapshot]] = {}
        self._deltas: Dict[str, List[SnapshotDelta]] = {}
        self._recovery_points: Dict[str, List[RecoveryPoint]] = {}
        self._session_meta: Dict[str, SessionMetadata] = {}
        self._snapshot_index: Dict[str, SessionSnapshot] = {}
        self._total_created: int = 0
        self._total_restored: int = 0
        self._total_pruned: int = 0

    @classmethod
    def get_instance(cls) -> "SessionSnapshotSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _ensure_session(self, session_id: str, agent_id: str, project_name: str = "") -> SessionMetadata:
        with self._lock:
            if session_id not in self._session_meta:
                self._session_meta[session_id] = SessionMetadata(
                    session_id=session_id,
                    agent_id=agent_id,
                    project_name=project_name,
                    created_at=time.time(),
                )
                self._snapshots[session_id] = []
                self._deltas[session_id] = []
                self._recovery_points[session_id] = []
            return self._session_meta[session_id]

    def _compress_payload(self, data: Dict[str, Any], compression: CompressionType) -> Tuple[bytes, int]:
        raw = json.dumps(data, sort_keys=True, default=str).encode("utf-8")
        original_size = len(raw)
        if compression == CompressionType.NONE:
            return raw, original_size
        elif compression == CompressionType.GZIP:
            compressed = zlib.compress(raw, level=6)
            return compressed, original_size
        elif compression == CompressionType.ZSTD:
            try:
                import zstandard
                cctx = zstandard.ZstdCompressor()
                compressed = cctx.compress(raw)
                return compressed, original_size
            except ImportError:
                return zlib.compress(raw, level=6), original_size
        return raw, original_size

    def _decompress_payload(self, payload: bytes, compression: CompressionType) -> Dict[str, Any]:
        if compression == CompressionType.NONE:
            return json.loads(payload.decode("utf-8"))
        elif compression == CompressionType.GZIP:
            raw = zlib.decompress(payload)
            return json.loads(raw.decode("utf-8"))
        elif compression == CompressionType.ZSTD:
            try:
                import zstandard
                dctx = zstandard.ZstdDecompressor()
                raw = dctx.decompress(payload)
                return json.loads(raw.decode("utf-8"))
            except ImportError:
                raw = zlib.decompress(payload)
                return json.loads(raw.decode("utf-8"))
        return {}

    def _diff_state(self, old_state: Dict[str, Any], new_state: Dict[str, Any]) -> Dict[str, Any]:
        changed = []
        added = []
        removed = []
        all_keys = set(old_state.keys()) | set(new_state.keys())
        for key in all_keys:
            if key in old_state and key not in new_state:
                removed.append(key)
            elif key not in old_state and key in new_state:
                added.append(key)
            elif old_state[key] != new_state[key]:
                changed.append(key)
        return {
            "changed": changed,
            "added": added,
            "removed": removed,
            "changed_data": {k: new_state[k] for k in changed},
            "added_data": {k: new_state[k] for k in added},
        }

    def create_snapshot(
        self,
        session_id: str,
        agent_id: str,
        state_data: Dict[str, Any],
        mode: SnapshotMode = SnapshotMode.FULL,
        compression: CompressionType = CompressionType.GZIP,
        label: str = "",
        tags: Optional[List[str]] = None,
    ) -> Optional[SessionSnapshot]:
        self._ensure_session(session_id, agent_id)
        with self._lock:
            snapshots = self._snapshots[session_id]
            if len(snapshots) >= self._MAX_SNAPSHOTS_PER_SESSION:
                self._prune_oldest(session_id, keep=10)

            parent_id: Optional[str] = None
            if mode == SnapshotMode.DELTA and snapshots:
                parent_id = snapshots[-1].snapshot_id

            combined_state = dict(state_data)
            snapshot = SessionSnapshot(
                session_id=session_id,
                agent_id=agent_id,
                mode=mode,
                compression=compression,
                version=len(snapshots) + 1,
                label=label or f"snap_{len(snapshots) + 1}",
                created_at=time.time(),
                state_data=combined_state,
                agent_context=state_data.get("agent", {}),
                tool_state=state_data.get("tools", {}),
                memory_state=state_data.get("memory", {}),
                engine_state=state_data.get("engine", {}),
                parent_snapshot_id=parent_id,
                tags=tags or [],
            )

            _, original_size = self._compress_payload(combined_state, compression)
            snapshot.size_bytes = original_size
            snapshot.content_hash = snapshot.compute_hash()

            snapshots.append(snapshot)
            self._snapshot_index[snapshot.snapshot_id] = snapshot
            self._total_created += 1

            meta = self._session_meta[session_id]
            meta.snapshot_count = len(snapshots)
            meta.last_snapshot_at = snapshot.created_at
            meta.total_size_bytes += snapshot.size_bytes

            if mode == SnapshotMode.DELTA and parent_id and parent_id in self._snapshot_index:
                parent = self._snapshot_index[parent_id]
                diff = self._diff_state(parent.state_data, combined_state)
                delta = SnapshotDelta(
                    from_snapshot_id=parent_id,
                    to_snapshot_id=snapshot.snapshot_id,
                    session_id=session_id,
                    version=snapshot.version,
                    created_at=time.time(),
                    changed_keys=diff["changed"],
                    added_keys=diff["added"],
                    removed_keys=diff["removed"],
                    payload=diff["changed_data"],
                    size_bytes=len(json.dumps(diff["changed_data"], default=str)),
                )
                self._deltas[session_id].append(delta)
                if len(self._deltas[session_id]) > self._MAX_DELTAS_PER_SESSION:
                    self._deltas[session_id] = self._deltas[session_id][-self._MAX_DELTAS_PER_SESSION:]

            return snapshot

    def restore_session(
        self,
        session_id: str,
        target_version: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            if not snapshots:
                return None

            target: Optional[SessionSnapshot] = None
            if target_version is not None:
                for snap in snapshots:
                    if snap.version == target_version:
                        target = snap
                        break
            else:
                target = snapshots[-1]

            if target is None or target.state == SnapshotState.CORRUPT:
                return None

            self._total_restored += 1
            return dict(target.state_data)

    def apply_delta(
        self,
        session_id: str,
        from_version: int,
        to_version: int,
    ) -> Optional[Dict[str, Any]]:
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            base_snapshot: Optional[SessionSnapshot] = None
            for snap in snapshots:
                if snap.version == from_version:
                    base_snapshot = snap
                    break
            if base_snapshot is None:
                return None

            accumulated = dict(base_snapshot.state_data)
            deltas = self._deltas.get(session_id, [])
            version_range = range(from_version, to_version)
            for delta in deltas:
                if delta.version in version_range:
                    for key in delta.removed_keys:
                        accumulated.pop(key, None)
                    accumulated.update(delta.added_keys and {} or {})
                    accumulated.update(delta.payload)

            self._total_restored += 1
            return accumulated

    def create_checkpoint(
        self,
        session_id: str,
        label: str,
        state_data: Optional[Dict[str, Any]] = None,
        is_auto: bool = False,
    ) -> Optional[RecoveryPoint]:
        snapshots = self._snapshots.get(session_id, [])
        if not snapshots:
            if state_data is None:
                return None
            snapshot = self.create_snapshot(
                session_id=session_id,
                agent_id="checkpoint",
                state_data=state_data,
                mode=SnapshotMode.CHECKPOINT,
                label=label,
            )
            if snapshot is None:
                return None
            target_snapshot_id = snapshot.snapshot_id
        else:
            target_snapshot_id = snapshots[-1].snapshot_id

        with self._lock:
            recovery = RecoveryPoint(
                session_id=session_id,
                snapshot_id=target_snapshot_id,
                label=label,
                created_at=time.time(),
                is_auto=is_auto,
                trigger_reason="manual" if not is_auto else "interval",
            )
            self._recovery_points[session_id].append(recovery)
            return recovery

    def list_snapshots(
        self,
        session_id: str,
        mode: Optional[SnapshotMode] = None,
        state: Optional[SnapshotState] = None,
        limit: int = 50,
    ) -> List[SessionSnapshot]:
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            if mode:
                snapshots = [s for s in snapshots if s.mode == mode]
            if state:
                snapshots = [s for s in snapshots if s.state == state]
            return snapshots[-limit:]

    def compare_snapshots(self, from_id: str, to_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            from_snap = self._snapshot_index.get(from_id)
            to_snap = self._snapshot_index.get(to_id)
            if from_snap is None or to_snap is None:
                return None

            diff = self._diff_state(from_snap.state_data, to_snap.state_data)
            return {
                "from": {"id": from_id, "version": from_snap.version, "label": from_snap.label},
                "to": {"id": to_id, "version": to_snap.version, "label": to_snap.label},
                "changed_keys": diff["changed"],
                "added_keys": diff["added"],
                "removed_keys": diff["removed"],
                "changed_count": len(diff["changed"]),
                "added_count": len(diff["added"]),
                "removed_count": len(diff["removed"]),
                "from_size": from_snap.size_bytes,
                "to_size": to_snap.size_bytes,
                "size_delta": to_snap.size_bytes - from_snap.size_bytes,
            }

    def prune_snapshots(
        self,
        session_id: str,
        keep_last: int = 10,
    ) -> int:
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            if len(snapshots) <= keep_last:
                return 0

            pruned = snapshots[:-keep_last]
            for snap in pruned:
                self._snapshot_index.pop(snap.snapshot_id, None)
                snap.state = SnapshotState.ARCHIVED

            self._snapshots[session_id] = snapshots[-keep_last:]
            self._total_pruned += len(pruned)

            remaining_deltas = [
                d for d in self._deltas.get(session_id, [])
                if d.to_snapshot_id in {s.snapshot_id for s in self._snapshots[session_id]}
            ]
            self._deltas[session_id] = remaining_deltas

            self._recovery_points[session_id] = [
                r for r in self._recovery_points.get(session_id, [])
                if r.snapshot_id in {s.snapshot_id for s in self._snapshots[session_id]}
            ]

            return len(pruned)

    def verify_integrity(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            snapshot = self._snapshot_index.get(snapshot_id)
            if snapshot is None:
                return None

            current_hash = snapshot.compute_hash()
            is_valid = current_hash == snapshot.content_hash

            issues: List[str] = []
            if not is_valid:
                issues.append("content_hash_mismatch")
            if snapshot.state == SnapshotState.CORRUPT:
                issues.append("marked_as_corrupt")
            if snapshot.size_bytes == 0:
                issues.append("zero_size")
            if not snapshot.session_id:
                issues.append("missing_session_id")

            if issues and not is_valid:
                snapshot.state = SnapshotState.CORRUPT

            return {
                "snapshot_id": snapshot_id,
                "valid": is_valid and len(issues) == 0,
                "hash_match": is_valid,
                "issues": issues,
                "state": snapshot.state.name,
                "size_bytes": snapshot.size_bytes,
                "version": snapshot.version,
            }

    def get_snapshot(self, snapshot_id: str) -> Optional[SessionSnapshot]:
        with self._lock:
            return self._snapshot_index.get(snapshot_id)

    def get_latest_snapshot(self, session_id: str) -> Optional[SessionSnapshot]:
        with self._lock:
            snapshots = self._snapshots.get(session_id, [])
            return snapshots[-1] if snapshots else None

    def get_recovery_points(self, session_id: str) -> List[RecoveryPoint]:
        with self._lock:
            return list(self._recovery_points.get(session_id, []))

    def export_snapshot(self, snapshot_id: str) -> Optional[str]:
        with self._lock:
            snapshot = self._snapshot_index.get(snapshot_id)
            if snapshot is None:
                return None
            return json.dumps(snapshot.to_dict(), default=str, indent=2)

    def delete_session(self, session_id: str) -> bool:
        with self._lock:
            existed = False
            if session_id in self._snapshots:
                for snap in self._snapshots[session_id]:
                    self._snapshot_index.pop(snap.snapshot_id, None)
                del self._snapshots[session_id]
                existed = True
            self._deltas.pop(session_id, None)
            self._recovery_points.pop(session_id, None)
            self._session_meta.pop(session_id, None)
            return existed

    def _prune_oldest(self, session_id: str, keep: int) -> None:
        snapshots = self._snapshots.get(session_id, [])
        if len(snapshots) <= keep:
            return
        pruned = snapshots[: -(keep)]
        for snap in pruned:
            snap.state = SnapshotState.ARCHIVED
            self._snapshot_index.pop(snap.snapshot_id, None)
        self._snapshots[session_id] = snapshots[-(keep):]

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_snapshots = sum(len(v) for v in self._snapshots.values())
            total_deltas = sum(len(v) for v in self._deltas.values())
            total_recovery = sum(len(v) for v in self._recovery_points.values())
            total_size = sum(
                s.size_bytes for snaps in self._snapshots.values() for s in snaps
            )

            by_mode: Dict[str, int] = {}
            by_state: Dict[str, int] = {}
            for snaps in self._snapshots.values():
                for s in snaps:
                    by_mode[s.mode.name] = by_mode.get(s.mode.name, 0) + 1
                    by_state[s.state.name] = by_state.get(s.state.name, 0) + 1

            return {
                "session_count": len(self._snapshots),
                "total_snapshots": total_snapshots,
                "total_deltas": total_deltas,
                "total_recovery_points": total_recovery,
                "total_created": self._total_created,
                "total_restored": self._total_restored,
                "total_pruned": self._total_pruned,
                "total_size_bytes": total_size,
                "by_mode": by_mode,
                "by_state": by_state,
                "sessions": [
                    {
                        "session_id": sid,
                        "snapshots": len(snaps),
                        "project": self._session_meta.get(sid, SessionMetadata()).project_name,
                    }
                    for sid, snaps in self._snapshots.items()
                ],
            }


def get_session_snapshot() -> SessionSnapshotSystem:
    return SessionSnapshotSystem.get_instance()