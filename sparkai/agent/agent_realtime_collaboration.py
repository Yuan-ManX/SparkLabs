"""
SparkLabs Agent - Real-Time Collaboration Engine

Multi-user co-editing system with operational transforms, conflict
resolution, and granular file locking. Enables concurrent editing
across the game development workflow for AI-native game creation.

Architecture:
  RealtimeCollaborationEngine
    |-- CollaborativeOperation (atomic edit operation with transform)
    |-- CollaborationSession (shared editing context)
    |-- OperationTransformer (OT-based conflict resolution)
    |-- LockManager (granular file region locking)
    |-- VersionVector (causal ordering and convergence)
    |-- ConflictResolver (merge conflict detection and resolution)

Collaboration Modes:
  - ASYNCHRONOUS: non-blocking edits with delayed sync
  - REAL_TIME: concurrent editing with immediate transforms
  - REVIEW_CYCLE: staged review with approval gates
  - APPROVAL_FLOW: sequential approval chain
  - PAIR_PROGRAMMING: synchronous collaborative editing
"""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class CollaborationMode(Enum):
    ASYNCHRONOUS = "asynchronous"
    REAL_TIME = "real_time"
    REVIEW_CYCLE = "review_cycle"
    APPROVAL_FLOW = "approval_flow"
    PAIR_PROGRAMMING = "pair_programming"


class OperationType(Enum):
    INSERT = "insert"
    DELETE = "delete"
    REPLACE = "replace"
    MOVE = "move"
    RENAME = "rename"
    FORMAT = "format"
    MERGE = "merge"


class LockGranularity(Enum):
    PROJECT = "project"
    SCENE = "scene"
    FILE = "file"
    FUNCTION = "function"
    LINE = "line"
    CHARACTER = "character"


@dataclass
class CollaborativeOperation:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    session_id: str = ""
    user_id: str = ""
    operation_type: OperationType = OperationType.INSERT
    target_path: str = ""
    position_offset: int = 0
    content_before: str = ""
    content_after: str = ""
    timestamp: float = field(default_factory=time.time)
    sequence_number: int = 0
    parent_operation_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "operation_type": self.operation_type.value,
            "target_path": self.target_path,
            "position_offset": self.position_offset,
            "content_before": self.content_before[:100],
            "content_after": self.content_after[:100],
            "timestamp": self.timestamp,
            "sequence_number": self.sequence_number,
            "parent_operation_id": self.parent_operation_id,
        }


@dataclass
class CollaborationSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mode: CollaborationMode = CollaborationMode.REAL_TIME
    participants: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    active_files: List[str] = field(default_factory=list)
    operations: List[CollaborativeOperation] = field(default_factory=list)
    locked_regions: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    last_activity: float = field(default_factory=time.time)
    version_vector: Dict[str, int] = field(default_factory=dict)
    conflict_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "mode": self.mode.value,
            "participant_count": len(self.participants),
            "participants": {
                uid: {"name": data.get("name", uid), "role": data.get("role", "")}
                for uid, data in self.participants.items()
            },
            "active_files": self.active_files,
            "operation_count": len(self.operations),
            "locked_regions": {
                path: len(locks) for path, locks in self.locked_regions.items()
            },
            "last_activity": self.last_activity,
            "version_vector": self.version_vector,
            "conflict_count": self.conflict_count,
        }


class RealtimeCollaborationEngine:
    """
    Real-time collaboration engine for AI-native game creation.

    Manages multi-user co-editing with operational transforms,
    conflict resolution, and granular file locking across the
    development workflow.
    """

    _instance: Optional[RealtimeCollaborationEngine] = None

    @classmethod
    def get_instance(cls) -> RealtimeCollaborationEngine:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self._sessions: Dict[str, CollaborationSession] = {}
        self._session_count: int = 0
        self._operation_count: int = 0
        self._conflict_count: int = 0
        self._resolved_count: int = 0
        self._user_sessions: Dict[str, Set[str]] = defaultdict(set)
        self._session_timeout: float = 3600.0

    def create_session(self, mode: str = "real_time") -> CollaborationSession:
        session = CollaborationSession(
            mode=CollaborationMode(mode),
        )
        self._sessions[session.id] = session
        self._session_count += 1
        return session

    def join_session(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False

        if user_id not in session.participants:
            session.participants[user_id] = {
                "name": user_id,
                "role": "editor",
                "joined_at": time.time(),
                "cursor_position": {},
            }
            session.version_vector[user_id] = 0

        self._user_sessions[user_id].add(session_id)
        session.last_activity = time.time()
        return True

    def leave_session(self, session_id: str, user_id: str) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False

        if user_id in session.participants:
            del session.participants[user_id]

        if session_id in self._user_sessions.get(user_id, set()):
            self._user_sessions[user_id].discard(session_id)

        session.last_activity = time.time()

        if not session.participants:
            session.last_activity = 0

        return True

    def submit_operation(
        self,
        session_id: str,
        op: Dict[str, Any],
    ) -> str:
        session = self._sessions.get(session_id)
        if not session:
            return ""

        user_id = op.get("user_id", "")
        if user_id not in session.participants:
            return ""

        sequence = session.version_vector.get(user_id, 0) + 1
        session.version_vector[user_id] = sequence

        operation = CollaborativeOperation(
            session_id=session_id,
            user_id=user_id,
            operation_type=OperationType(op.get("operation_type", "insert")),
            target_path=op.get("target_path", ""),
            position_offset=op.get("position_offset", 0),
            content_before=op.get("content_before", ""),
            content_after=op.get("content_after", ""),
            sequence_number=sequence,
            parent_operation_id=op.get("parent_operation_id", ""),
        )

        conflict = self._detect_conflict(session, operation)
        if conflict:
            operation = self._transform_operation(operation, conflict)
            session.conflict_count += 1
            self._conflict_count += 1

        session.operations.append(operation)
        session.last_activity = time.time()
        self._operation_count += 1

        return operation.id

    def resolve_conflict(
        self,
        session_id: str,
        conflict_id: str,
        resolution: str,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session:
            return False

        for op in session.operations:
            if op.id == conflict_id:
                if resolution == "accept_mine":
                    pass
                elif resolution == "accept_theirs":
                    op.content_after = op.content_before
                elif resolution == "merge":
                    op.content_after = op.content_before + "\n" + op.content_after
                else:
                    return False

                self._resolved_count += 1
                return True

        return False

    def get_file_locks(
        self,
        session_id: str,
        file_path: str,
    ) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []

        locks = session.locked_regions.get(file_path, [])
        return [
            {
                "user_id": lock["user_id"],
                "granularity": lock.get("granularity", "file"),
                "start_offset": lock.get("start_offset", 0),
                "end_offset": lock.get("end_offset", 0),
                "acquired_at": lock.get("acquired_at", 0),
            }
            for lock in locks
        ]

    def acquire_lock(
        self,
        session_id: str,
        user_id: str,
        file_path: str,
        granularity: str = "file",
        start_offset: int = 0,
        end_offset: int = 0,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session or user_id not in session.participants:
            return False

        if file_path not in session.locked_regions:
            session.locked_regions[file_path] = []

        existing = session.locked_regions[file_path]
        lock_range = (start_offset, end_offset) if granularity != "file" else (0, 0)

        for lock in existing:
            existing_range = (
                (lock.get("start_offset", 0), lock.get("end_offset", 0))
                if lock.get("granularity") != "file"
                else (0, 0)
            )
            if self._ranges_overlap(lock_range, existing_range):
                return False

        existing.append({
            "user_id": user_id,
            "granularity": granularity,
            "start_offset": start_offset,
            "end_offset": end_offset,
            "acquired_at": time.time(),
        })

        session.last_activity = time.time()
        return True

    def release_lock(
        self,
        session_id: str,
        user_id: str,
        file_path: str,
    ) -> bool:
        session = self._sessions.get(session_id)
        if not session or file_path not in session.locked_regions:
            return False

        before_count = len(session.locked_regions[file_path])
        session.locked_regions[file_path] = [
            lock for lock in session.locked_regions[file_path]
            if lock["user_id"] != user_id
        ]

        if not session.locked_regions[file_path]:
            del session.locked_regions[file_path]

        session.last_activity = time.time()
        return len(session.locked_regions.get(file_path, [])) < before_count

    def get_active_sessions(self) -> List[Dict[str, Any]]:
        now = time.time()
        active: List[Dict[str, Any]] = []

        for session in self._sessions.values():
            if session.participants and (now - session.last_activity) < self._session_timeout:
                active.append(session.to_dict())

        return sorted(active, key=lambda s: s["last_activity"], reverse=True)

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if session:
            return session.to_dict()
        return None

    def get_operations(
        self,
        session_id: str,
        since_sequence: int = 0,
    ) -> List[Dict[str, Any]]:
        session = self._sessions.get(session_id)
        if not session:
            return []

        return [
            op.to_dict()
            for op in session.operations
            if op.sequence_number > since_sequence
        ]

    def get_user_sessions(self, user_id: str) -> List[str]:
        return list(self._user_sessions.get(user_id, set()))

    def cleanup_stale_sessions(self) -> int:
        now = time.time()
        removed = 0

        stale_ids = []
        for sid, session in self._sessions.items():
            if not session.participants:
                if now - session.last_activity > self._session_timeout:
                    stale_ids.append(sid)
            elif now - session.last_activity > self._session_timeout * 2:
                stale_ids.append(sid)

        for sid in stale_ids:
            session = self._sessions[sid]
            for user_id in session.participants:
                self._user_sessions[user_id].discard(sid)
            del self._sessions[sid]
            removed += 1

        return removed

    def _detect_conflict(
        self,
        session: CollaborationSession,
        operation: CollaborativeOperation,
    ) -> Optional[CollaborativeOperation]:
        recent_window = 5.0
        now = time.time()

        for existing_op in session.operations:
            if existing_op.user_id == operation.user_id:
                continue

            if now - existing_op.timestamp > recent_window:
                continue

            if existing_op.target_path != operation.target_path:
                continue

            existing_range = (
                existing_op.position_offset,
                existing_op.position_offset + len(existing_op.content_after),
            )
            new_range = (
                operation.position_offset,
                operation.position_offset + len(operation.content_after),
            )

            if self._ranges_overlap(existing_range, new_range):
                return existing_op

        return None

    def _transform_operation(
        self,
        operation: CollaborativeOperation,
        conflict: CollaborativeOperation,
    ) -> CollaborativeOperation:
        conflict_end = conflict.position_offset + len(conflict.content_after)

        if operation.position_offset >= conflict_end:
            shift = len(conflict.content_after) - len(conflict.content_before)
            operation.position_offset += shift

        return operation

    def _ranges_overlap(
        self,
        range_a: Tuple[int, int],
        range_b: Tuple[int, int],
    ) -> bool:
        start_a, end_a = range_a
        start_b, end_b = range_b

        if start_a == 0 and end_a == 0:
            return True
        if start_b == 0 and end_b == 0:
            return True

        return start_a < end_b and start_b < end_a

    def get_stats(self) -> Dict[str, Any]:
        mode_counts: Dict[str, int] = {}
        active_users: Set[str] = set()

        for session in self._sessions.values():
            mode_counts[session.mode.value] = mode_counts.get(session.mode.value, 0) + 1
            for uid in session.participants:
                active_users.add(uid)

        total_participants = sum(
            len(s.participants) for s in self._sessions.values()
        )

        return {
            "total_sessions": self._session_count,
            "active_sessions": len([
                s for s in self._sessions.values() if s.last_activity > 0
            ]),
            "total_operations": self._operation_count,
            "total_conflicts": self._conflict_count,
            "resolved_conflicts": self._resolved_count,
            "conflict_rate": (
                self._conflict_count / self._operation_count
                if self._operation_count > 0 else 0.0
            ),
            "total_participants": total_participants,
            "unique_users": len(active_users),
            "by_mode": mode_counts,
            "available_modes": [m.value for m in CollaborationMode],
            "available_operations": [o.value for o in OperationType],
            "available_granularities": [g.value for g in LockGranularity],
            "session_timeout_seconds": self._session_timeout,
            "avg_participants_per_session": (
                total_participants / self._session_count
                if self._session_count > 0 else 0
            ),
        }


def get_realtime_collaboration() -> RealtimeCollaborationEngine:
    return RealtimeCollaborationEngine.get_instance()