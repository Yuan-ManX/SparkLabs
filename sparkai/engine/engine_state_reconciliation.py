"""
SparkLabs Engine - State Reconciliation Engine

Deterministic state reconciliation system for multiplayer and networked
game scenarios. Provides authoritative state management with client-side
prediction, rollback, and interpolation. Designed for lockstep and
rollback netcode architectures.

Architecture:
  StateReconciliationEngine (Singleton)
    |-- StateSnapshot (captured game state at a point in time)
    |-- StateDelta (difference between two state snapshots)
    |-- ReconciliationBuffer (ring buffer of recent states)
    |-- PredictionValidator (validates client predictions)
    |-- ConflictResolver (resolves state conflicts between peers)

Reconciliation Modes:
  - LOCKSTEP: deterministic simulation with input synchronization
  - ROLLBACK: client prediction with server rollback
  - INTERPOLATION: smooth interpolation between authoritative states
  - HYBRID: combination of prediction and interpolation

Usage:
    sr = StateReconciliationEngine.get_instance()
    sr.initialize()

    snapshot = sr.capture_snapshot("game_world", {"entities": [...], "time": 1.0})
    delta = sr.compute_delta("snapshot_1", "snapshot_2")
    sr.apply_delta("current_state", delta)
    sr.shutdown()
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# =============================================================================
# Enums
# =============================================================================


class ReconciliationMode(Enum):
    """Modes for state reconciliation."""
    LOCKSTEP = "lockstep"           # Deterministic simulation
    ROLLBACK = "rollback"           # Client prediction + rollback
    INTERPOLATION = "interpolation"  # Smooth interpolation
    HYBRID = "hybrid"               # Prediction + interpolation


class ConflictStrategy(Enum):
    """Strategies for resolving state conflicts."""
    AUTHORITATIVE = "authoritative"    # Server always wins
    MAJORITY = "majority"             # Most common state wins
    TIMESTAMP = "timestamp"            # Latest timestamp wins
    MERGE = "merge"                   # Merge non-conflicting fields
    CUSTOM = "custom"                 # Custom resolution function


class SnapshotType(Enum):
    """Types of state snapshots."""
    FULL = "full"        # Complete state capture
    DELTA = "delta"      # Only changed fields
    CHECKPOINT = "checkpoint"  # Periodic full capture
    KEYFRAME = "keyframe"     # Significant state change


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class StateSnapshot:
    """A captured game state at a specific point in time."""
    snapshot_id: str
    snapshot_type: SnapshotType = SnapshotType.FULL
    state: Dict[str, Any] = field(default_factory=dict)
    checksum: str = ""
    tick: int = 0
    timestamp: float = field(default_factory=time.time)
    source: str = "local"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def compute_checksum(self) -> str:
        """Compute a checksum of the state for verification."""
        state_str = json.dumps(self.state, sort_keys=True, default=str)
        return hashlib.md5(state_str.encode()).hexdigest()[:16]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "snapshot_type": self.snapshot_type.value,
            "state_keys": list(self.state.keys()),
            "checksum": self.checksum,
            "tick": self.tick,
            "timestamp": self.timestamp,
            "source": self.source,
            "metadata": self.metadata,
        }


@dataclass
class StateDelta:
    """The difference between two state snapshots."""
    delta_id: str
    base_snapshot_id: str
    target_snapshot_id: str
    added: Dict[str, Any] = field(default_factory=dict)
    removed: Dict[str, Any] = field(default_factory=dict)
    changed: Dict[str, Any] = field(default_factory=dict)
    unchanged: List[str] = field(default_factory=list)
    tick: int = 0
    timestamp: float = field(default_factory=time.time)

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.removed and not self.changed

    @property
    def change_count(self) -> int:
        return len(self.added) + len(self.removed) + len(self.changed)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "base_snapshot_id": self.base_snapshot_id,
            "target_snapshot_id": self.target_snapshot_id,
            "added_keys": list(self.added.keys()),
            "removed_keys": list(self.removed.keys()),
            "changed_keys": list(self.changed.keys()),
            "unchanged_count": len(self.unchanged),
            "change_count": self.change_count,
            "is_empty": self.is_empty,
            "tick": self.tick,
            "timestamp": self.timestamp,
        }


@dataclass
class ReconciliationEntry:
    """A single entry in the reconciliation buffer."""
    entry_id: str
    snapshot: StateSnapshot
    predicted_snapshot: Optional[StateSnapshot] = None
    was_rollback: bool = False
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    resolution_time_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "snapshot_id": self.snapshot.snapshot_id,
            "tick": self.snapshot.tick,
            "was_rollback": self.was_rollback,
            "conflict_count": len(self.conflicts),
            "resolution_time_ms": self.resolution_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class PredictionResult:
    """Result of client-side prediction."""
    prediction_id: str
    base_tick: int
    predicted_tick: int
    predicted_state: Dict[str, Any]
    confidence: float = 0.8
    inputs: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "base_tick": self.base_tick,
            "predicted_tick": self.predicted_tick,
            "confidence": self.confidence,
            "input_count": len(self.inputs),
            "timestamp": self.timestamp,
        }


# =============================================================================
# State Reconciliation Engine
# =============================================================================


class StateReconciliationEngine:
    """
    Deterministic state reconciliation engine for multiplayer games.
    Supports authoritative state management with rollback and prediction.
    """

    _instance: Optional["StateReconciliationEngine"] = None
    _instance_lock = threading.RLock()

    def __init__(self) -> None:
        if StateReconciliationEngine._instance is not None:
            raise RuntimeError("Use StateReconciliationEngine.get_instance()")
        self._initialized: bool = False
        self._mode: ReconciliationMode = ReconciliationMode.HYBRID
        self._snapshots: Dict[str, StateSnapshot] = {}
        self._deltas: Dict[str, StateDelta] = {}
        self._buffer: deque = deque(maxlen=300)  # Rolling buffer of recent states
        self._history: List[ReconciliationEntry] = []
        self._current_state: Dict[str, Any] = {}
        self._current_tick: int = 0
        self._authoritative: bool = True
        self._conflict_strategy: ConflictStrategy = ConflictStrategy.AUTHORITATIVE
        self._custom_resolver: Optional[Callable] = None
        self._prediction_fn: Optional[Callable] = None
        self._stats: Dict[str, Any] = {
            "total_snapshots": 0,
            "total_deltas": 0,
            "total_rollbacks": 0,
            "total_conflicts": 0,
            "total_predictions": 0,
            "successful_predictions": 0,
            "avg_delta_size": 0.0,
            "avg_resolution_time_ms": 0.0,
        }
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "StateReconciliationEngine":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self, mode: ReconciliationMode = ReconciliationMode.HYBRID,
                   authoritative: bool = True,
                   conflict_strategy: ConflictStrategy = ConflictStrategy.AUTHORITATIVE,
                   buffer_size: int = 300) -> None:
        """Initialize the state reconciliation engine."""
        with self._lock:
            if self._initialized:
                return
            self._mode = mode
            self._authoritative = authoritative
            self._conflict_strategy = conflict_strategy
            self._buffer = deque(maxlen=buffer_size)
            self._initialized = True

    def set_state(self, state: Dict[str, Any], tick: int = 0) -> None:
        """Set the current authoritative state."""
        with self._lock:
            self._current_state = state
            self._current_tick = tick

    def capture_snapshot(self, state: Optional[Dict[str, Any]] = None,
                         snapshot_type: SnapshotType = SnapshotType.FULL,
                         tick: Optional[int] = None,
                         source: str = "local") -> StateSnapshot:
        """Capture a state snapshot."""
        with self._lock:
            if state is None:
                state = dict(self._current_state)
            if tick is None:
                tick = self._current_tick

            snapshot_id = uuid.uuid4().hex[:12]
            snapshot = StateSnapshot(
                snapshot_id=snapshot_id,
                snapshot_type=snapshot_type,
                state=state,
                tick=tick,
                source=source,
            )
            snapshot.checksum = snapshot.compute_checksum()

            self._snapshots[snapshot_id] = snapshot
            self._buffer.append(snapshot)
            self._stats["total_snapshots"] += 1

            return snapshot

    def compute_delta(self, base_snapshot_id: str,
                      target_snapshot_id: str) -> Optional[StateDelta]:
        """Compute the delta between two snapshots."""
        with self._lock:
            base = self._snapshots.get(base_snapshot_id)
            target = self._snapshots.get(target_snapshot_id)
            if not base or not target:
                return None

            added: Dict[str, Any] = {}
            removed: Dict[str, Any] = {}
            changed: Dict[str, Any] = {}
            unchanged: List[str] = []

            all_keys = set(base.state.keys()) | set(target.state.keys())

            for key in all_keys:
                if key not in base.state:
                    added[key] = target.state[key]
                elif key not in target.state:
                    removed[key] = base.state[key]
                elif base.state[key] != target.state[key]:
                    changed[key] = {
                        "from": base.state[key],
                        "to": target.state[key],
                    }
                else:
                    unchanged.append(key)

            delta_id = uuid.uuid4().hex[:12]
            delta = StateDelta(
                delta_id=delta_id,
                base_snapshot_id=base_snapshot_id,
                target_snapshot_id=target_snapshot_id,
                added=added,
                removed=removed,
                changed=changed,
                unchanged=unchanged,
                tick=target.tick,
            )

            self._deltas[delta_id] = delta
            self._stats["total_deltas"] += 1

            # Update avg delta size
            total_deltas = self._stats["total_deltas"]
            self._stats["avg_delta_size"] = (
                (self._stats["avg_delta_size"] * (total_deltas - 1) + delta.change_count)
                / total_deltas
            )

            return delta

    def apply_delta(self, base_state: Dict[str, Any], delta: StateDelta) -> Dict[str, Any]:
        """Apply a delta to a base state to reconstruct the target state."""
        result = dict(base_state)

        # Remove keys
        for key in delta.removed:
            result.pop(key, None)

        # Add new keys
        result.update(delta.added)

        # Apply changes
        for key, change in delta.changed.items():
            result[key] = change["to"]

        return result

    def predict(self, base_state: Dict[str, Any], inputs: List[Dict[str, Any]],
                ticks_ahead: int = 1) -> PredictionResult:
        """Predict future state based on current state and inputs."""
        if self._prediction_fn:
            predicted_state = self._prediction_fn(base_state, inputs, ticks_ahead)
        else:
            predicted_state = dict(base_state)

        prediction = PredictionResult(
            prediction_id=uuid.uuid4().hex[:12],
            base_tick=self._current_tick,
            predicted_tick=self._current_tick + ticks_ahead,
            predicted_state=predicted_state,
            inputs=inputs,
        )

        self._stats["total_predictions"] += 1
        return prediction

    def validate_prediction(self, prediction: PredictionResult,
                            authoritative_state: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a client prediction against the authoritative state."""
        conflicts: List[Dict[str, Any]] = []
        resolved_state = dict(prediction.predicted_state)

        all_keys = set(prediction.predicted_state.keys()) | set(authoritative_state.keys())

        for key in all_keys:
            pred_val = prediction.predicted_state.get(key)
            auth_val = authoritative_state.get(key)
            if pred_val != auth_val:
                conflicts.append({
                    "key": key,
                    "predicted": pred_val,
                    "authoritative": auth_val,
                })
                # Resolve based on strategy
                resolved_state[key] = auth_val  # Authoritative by default

        if conflicts:
            self._stats["total_conflicts"] += len(conflicts)
            self._stats["total_rollbacks"] += 1
        else:
            self._stats["successful_predictions"] += 1

        return resolved_state

    def rollback(self, from_tick: int, to_state: Dict[str, Any]) -> Dict[str, Any]:
        """Rollback to a previous state."""
        with self._lock:
            self._stats["total_rollbacks"] += 1
            self._current_state = dict(to_state)
            self._current_tick = from_tick

            entry = ReconciliationEntry(
                entry_id=uuid.uuid4().hex[:12],
                snapshot=StateSnapshot(
                    snapshot_id=uuid.uuid4().hex[:12],
                    state=to_state,
                    tick=from_tick,
                ),
                was_rollback=True,
            )
            self._history.append(entry)

            return self._current_state

    def reconcile(self, local_state: Dict[str, Any],
                  remote_state: Dict[str, Any],
                  strategy: Optional[ConflictStrategy] = None) -> Dict[str, Any]:
        """Reconcile two conflicting states."""
        start_time = time.time()
        strategy = strategy or self._conflict_strategy

        if strategy == ConflictStrategy.AUTHORITATIVE:
            result = dict(remote_state) if self._authoritative else dict(local_state)

        elif strategy == ConflictStrategy.MERGE:
            result = dict(local_state)
            for key, value in remote_state.items():
                if key not in result:
                    result[key] = value
                elif isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = {**result[key], **value}
                elif isinstance(result[key], list) and isinstance(value, list):
                    result[key] = value
                else:
                    result[key] = value if self._authoritative else result[key]

        elif strategy == ConflictStrategy.TIMESTAMP:
            local_ts = local_state.get("_timestamp", 0)
            remote_ts = remote_state.get("_timestamp", 0)
            result = dict(remote_state) if remote_ts >= local_ts else dict(local_state)

        elif strategy == ConflictStrategy.CUSTOM and self._custom_resolver:
            result = self._custom_resolver(local_state, remote_state)

        else:
            result = dict(remote_state) if self._authoritative else dict(local_state)

        resolution_time = (time.time() - start_time) * 1000.0
        total_resolutions = self._stats["total_conflicts"] + self._stats["total_rollbacks"] + 1
        self._stats["avg_resolution_time_ms"] = (
            (self._stats["avg_resolution_time_ms"] * (total_resolutions - 1) + resolution_time)
            / total_resolutions
        )

        return result

    def verify_checksum(self, snapshot_id: str) -> bool:
        """Verify the integrity of a snapshot."""
        snapshot = self._snapshots.get(snapshot_id)
        if not snapshot:
            return False
        return snapshot.checksum == snapshot.compute_checksum()

    def interpolate(self, from_snapshot_id: str, to_snapshot_id: str,
                    alpha: float) -> Optional[Dict[str, Any]]:
        """Interpolate between two snapshots for smooth rendering."""
        with self._lock:
            from_snap = self._snapshots.get(from_snapshot_id)
            to_snap = self._snapshots.get(to_snapshot_id)
            if not from_snap or not to_snap:
                return None

            alpha = max(0.0, min(1.0, alpha))
            result: Dict[str, Any] = {}

            all_keys = set(from_snap.state.keys()) | set(to_snap.state.keys())

            for key in all_keys:
                from_val = from_snap.state.get(key)
                to_val = to_snap.state.get(key)

                if isinstance(from_val, (int, float)) and isinstance(to_val, (int, float)):
                    result[key] = from_val + (to_val - from_val) * alpha
                elif isinstance(from_val, list) and isinstance(to_val, list):
                    if len(from_val) == len(to_val) and all(
                        isinstance(a, (int, float)) and isinstance(b, (int, float))
                        for a, b in zip(from_val, to_val)
                    ):
                        result[key] = [
                            a + (b - a) * alpha for a, b in zip(from_val, to_val)
                        ]
                    else:
                        result[key] = to_val if alpha > 0.5 else from_val
                else:
                    result[key] = to_val if alpha > 0.5 else from_val

            return result

    def set_prediction_function(self, fn: Callable[[Dict[str, Any], List[Dict[str, Any]], int], Dict[str, Any]]) -> None:
        """Set a custom state prediction function."""
        with self._lock:
            self._prediction_fn = fn

    def set_custom_resolver(self, fn: Callable[[Dict[str, Any], Dict[str, Any]], Dict[str, Any]]) -> None:
        """Set a custom conflict resolution function."""
        with self._lock:
            self._custom_resolver = fn
            self._conflict_strategy = ConflictStrategy.CUSTOM

    def get_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Get a snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def get_delta(self, delta_id: str) -> Optional[StateDelta]:
        """Get a delta by ID."""
        return self._deltas.get(delta_id)

    def get_current_state(self) -> Dict[str, Any]:
        """Get the current authoritative state."""
        with self._lock:
            return dict(self._current_state)

    def get_history(self, limit: int = 50) -> List[ReconciliationEntry]:
        """Get recent reconciliation history."""
        return self._history[-limit:]

    def get_buffer(self, limit: int = 50) -> List[StateSnapshot]:
        """Get recent snapshots from the buffer."""
        return list(self._buffer)[-limit:]

    def get_status(self) -> Dict[str, Any]:
        """Get engine status and statistics."""
        with self._lock:
            return {
                "initialized": self._initialized,
                "mode": self._mode.value,
                "authoritative": self._authoritative,
                "conflict_strategy": self._conflict_strategy.value,
                "current_tick": self._current_tick,
                "snapshot_count": len(self._snapshots),
                "delta_count": len(self._deltas),
                "buffer_size": len(self._buffer),
                "history_size": len(self._history),
                "state_keys": list(self._current_state.keys()),
                "stats": self._stats,
            }

    def clear_history(self) -> None:
        """Clear reconciliation history."""
        with self._lock:
            self._history.clear()

    def shutdown(self) -> None:
        """Shutdown the reconciliation engine."""
        with self._lock:
            self._snapshots.clear()
            self._deltas.clear()
            self._buffer.clear()
            self._history.clear()
            self._current_state.clear()
            self._current_tick = 0
            self._initialized = False