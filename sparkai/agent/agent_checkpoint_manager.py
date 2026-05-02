"""
SparkLabs Agent - Checkpoint Manager

Session state snapshot and rollback system for agent sessions.
Creates automatic state snapshots before agent operations,
enabling rollback to any previous checkpoint. Supports full-session
and per-entity snapshots with incremental deltas.

Architecture:
  CheckpointManager
    |-- SessionCheckpoint (full state snapshot at point in time)
    |-- DeltaTracker (incremental changes between checkpoints)
    |-- RollbackEngine (restores session to checkpoint state)
    |-- PrunePolicy (retention-based cleanup of old checkpoints)

Checkpoint Operations:
  - create: snapshot current session state
  - list: enumerate available checkpoints
  - diff: show changes between checkpoint and current state
  - rollback: restore session to checkpoint state
  - prune: remove old checkpoints beyond retention limit

Usage:
    cm = CheckpointManager(max_checkpoints=50)
    checkpoint_id = cm.create_checkpoint(session_id, {"reason": "before major change"})
    checkpoints = cm.list_checkpoints(session_id)
    cm.rollback(session_id, checkpoint_id)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CheckpointState(Enum):
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"
    PRUNED = "pruned"


@dataclass
class SnapshotEntry:
    key: str = ""
    value: Any = None
    timestamp: float = 0.0


@dataclass
class SessionCheckpoint:
    checkpoint_id: str = ""
    session_id: str = ""
    reason: str = ""
    created_at: float = 0.0
    state: CheckpointState = CheckpointState.ACTIVE
    snapshot: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "session_id": self.session_id,
            "reason": self.reason,
            "created_at": self.created_at,
            "state": self.state.value,
            "state_size": len(str(self.snapshot)),
            "keys": list(self.snapshot.keys()) if isinstance(self.snapshot, dict) else [],
            "metadata": self.metadata,
        }


@dataclass
class CheckpointDelta:
    added: Dict[str, Any] = field(default_factory=dict)
    modified: Dict[str, Any] = field(default_factory=dict)
    removed: List[str] = field(default_factory=list)
    key_count: int = 0


class CheckpointManager:
    """
    Session state checkpoint engine for SparkLabs agents.

    Captures full session snapshots and supports diff-based
    comparison and rollback. Manages a bounded checkpoint ring
    per session with automatic pruning of oldest entries.

    Usage:
        cm = CheckpointManager(max_checkpoints=50)

        # Before a risky game generation pipeline step
        cid = cm.create_checkpoint(
            session_id="session-1",
            state={"worlds": [...], "entities": [...], "systems": [...]},
            reason="Before pipeline stage 3",
        )

        # After failure, rollback to checkpoint
        cm.rollback("session-1", cid)
    """

    def __init__(self, max_checkpoints: int = 50):
        self._max_checkpoints = max_checkpoints
        self._checkpoints: Dict[str, Dict[str, SessionCheckpoint]] = {}
        self._current_states: Dict[str, Any] = {}
        self._rollback_history: Dict[str, List[str]] = {}
        self._total_created: int = 0
        self._total_rollbacks: int = 0

    def create_checkpoint(
        self,
        session_id: str,
        state: Any,
        reason: str = "auto",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        checkpoint_id = f"cp_{uuid.uuid4().hex[:12]}"
        now = time.time()

        snapshot = self._serialize_state(state)

        checkpoint = SessionCheckpoint(
            checkpoint_id=checkpoint_id,
            session_id=session_id,
            reason=reason,
            created_at=now,
            snapshot=snapshot,
            metadata=metadata or {},
        )

        session_checkpoints = self._checkpoints.setdefault(session_id, {})
        session_checkpoints[checkpoint_id] = checkpoint
        self._current_states[session_id] = snapshot
        self._total_created += 1

        self._prune_session(session_id)

        return checkpoint_id

    def update_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
        state: Any,
    ) -> bool:
        checkpoint = self._get_checkpoint(session_id, checkpoint_id)
        if not checkpoint:
            return False
        checkpoint.snapshot = self._serialize_state(state)
        self._current_states[session_id] = checkpoint.snapshot
        return True

    def list_checkpoints(
        self, session_id: str,
    ) -> List[Dict[str, Any]]:
        checkpoints = self._checkpoints.get(session_id, {})
        result = sorted(
            [cp.to_dict() for cp in checkpoints.values()],
            key=lambda c: c["created_at"],
            reverse=True,
        )
        return result

    def get_checkpoint(
        self, session_id: str, checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        checkpoint = self._get_checkpoint(session_id, checkpoint_id)
        if not checkpoint:
            return None
        return checkpoint.to_dict()

    def diff_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
        current_state: Any,
    ) -> CheckpointDelta:
        checkpoint = self._get_checkpoint(session_id, checkpoint_id)
        if not checkpoint:
            return CheckpointDelta()

        previous = checkpoint.snapshot if isinstance(checkpoint.snapshot, dict) else {}
        current = self._serialize_state(current_state) if isinstance(current_state, dict) else {}

        delta = CheckpointDelta()
        delta.key_count = len(current)

        for key, value in current.items():
            if key not in previous:
                delta.added[key] = value
            elif previous[key] != value:
                delta.modified[key] = value

        for key in previous:
            if key not in current:
                delta.removed.append(key)

        return delta

    def rollback(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> Optional[Dict[str, Any]]:
        checkpoint = self._get_checkpoint(session_id, checkpoint_id)
        if not checkpoint:
            return None

        checkpoint.state = CheckpointState.ROLLED_BACK

        rolled_data = dict(checkpoint.snapshot) if isinstance(checkpoint.snapshot, dict) else checkpoint.snapshot

        self._rollback_history.setdefault(session_id, []).append(checkpoint_id)
        self._current_states[session_id] = rolled_data
        self._total_rollbacks += 1

        return rolled_data

    def remove_checkpoint(
        self, session_id: str, checkpoint_id: str,
    ) -> bool:
        session_checkpoints = self._checkpoints.get(session_id, {})
        if checkpoint_id in session_checkpoints:
            del session_checkpoints[checkpoint_id]
            if not session_checkpoints:
                self._checkpoints.pop(session_id, None)
            return True
        return False

    def remove_session(self, session_id: str) -> int:
        count = len(self._checkpoints.pop(session_id, {}))
        self._current_states.pop(session_id, None)
        self._rollback_history.pop(session_id, None)
        return count

    def get_rollback_history(
        self, session_id: str,
    ) -> List[str]:
        return list(self._rollback_history.get(session_id, []))

    def get_current_state(
        self, session_id: str,
    ) -> Optional[Any]:
        return self._current_states.get(session_id)

    def get_stats(self) -> Dict[str, Any]:
        total_checkpoints = sum(len(cps) for cps in self._checkpoints.values())
        return {
            "session_count": len(self._checkpoints),
            "total_checkpoints": total_checkpoints,
            "total_created": self._total_created,
            "total_rollbacks": self._total_rollbacks,
            "max_per_session": self._max_checkpoints,
            "sessions": {
                sid: {
                    "checkpoint_count": len(cps),
                    "rollback_history": len(self._rollback_history.get(sid, [])),
                    "has_current_state": sid in self._current_states,
                }
                for sid, cps in self._checkpoints.items()
            },
        }

    def clear(self) -> None:
        self._checkpoints.clear()
        self._current_states.clear()
        self._rollback_history.clear()
        self._total_created = 0
        self._total_rollbacks = 0

    def _get_checkpoint(
        self, session_id: str, checkpoint_id: str,
    ) -> Optional[SessionCheckpoint]:
        return self._checkpoints.get(session_id, {}).get(checkpoint_id)

    def _prune_session(self, session_id: str) -> None:
        checkpoints = self._checkpoints.get(session_id, {})
        if len(checkpoints) <= self._max_checkpoints:
            return

        sorted_cps = sorted(
            checkpoints.values(), key=lambda cp: cp.created_at,
        )
        to_remove = sorted_cps[:len(sorted_cps) - self._max_checkpoints]

        for cp in to_remove:
            cp.state = CheckpointState.PRUNED
            checkpoints.pop(cp.checkpoint_id, None)

    @staticmethod
    def _serialize_state(state: Any) -> Any:
        if isinstance(state, dict):
            return dict(state)
        if isinstance(state, list):
            return list(state)
        return state


_global_checkpoint_manager: Optional[CheckpointManager] = None


def get_checkpoint_manager() -> CheckpointManager:
    global _global_checkpoint_manager
    if _global_checkpoint_manager is None:
        _global_checkpoint_manager = CheckpointManager()
    return _global_checkpoint_manager
