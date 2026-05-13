"""
SparkLabs Agent - Context Synchronization Subsystem

Bidirectional context synchronization between the agent's knowledge state
and the engine runtime state. Maintains coherence between what the agent
believes about the world and the actual game engine state, with automatic
diff detection, conflict resolution, checkpointing, and consistency verification.

Architecture:
    ContextSyncEngine
      |-- SyncState (per-scope state with dual views)
      |-- SyncDelta (individual change records with conflict tracking)
      |-- SyncCheckpoint (snapshot-and-rollback support)
      |-- PriorityQueue (schedules syncs by urgency)
      |-- ConflictDetector (identifies agent/engine divergence)
      |-- ConsistencyVerifier (validates state coherence)

Sync Flow:
  Agent Knowledge ←→ ContextSyncEngine ←→ Engine Runtime
       |                    |                      |
   push_agent_update    detect_conflicts    push_engine_update
       |                    |                      |
       └────── sync_now (BIDIRECTIONAL) ──────────┘
                         |
                   resolved deltas

Usage:
    sync = get_context_sync()
    sync.register_state("player_position", {"x": 0, "y": 0, "z": 0})
    sync.push_agent_update("player_position", "x", 42)
    sync.push_engine_update("player_position", "y", 10)
    resolved = sync.sync_now("player_position")
    sync.verify_consistency("player_position")
"""

from __future__ import annotations

import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class SyncDirection(Enum):
    AGENT_TO_ENGINE = "agent_to_engine"
    ENGINE_TO_AGENT = "engine_to_agent"
    BIDIRECTIONAL = "bidirectional"


class SyncPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class ConflictStrategy(Enum):
    AGENT_WINS = "agent_wins"
    ENGINE_WINS = "engine_wins"
    MERGE = "merge"
    MANUAL_RESOLVE = "manual_resolve"


@dataclass
class SyncState:
    state_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scope: str = ""
    agent_data: Dict[str, Any] = field(default_factory=dict)
    engine_data: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    last_synced: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "state_id": self.state_id,
            "scope": self.scope,
            "version": self.version,
            "last_synced": self.last_synced,
            "agent_keys": list(self.agent_data.keys()),
            "engine_keys": list(self.engine_data.keys()),
        }


@dataclass
class SyncDelta:
    delta_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_scope: str = ""
    direction: SyncDirection = SyncDirection.BIDIRECTIONAL
    changes: Dict[str, Tuple[Any, Any]] = field(default_factory=dict)
    priority: SyncPriority = SyncPriority.NORMAL
    conflict: bool = False
    timestamp: float = field(default_factory=time.time)
    resolved: bool = False
    resolved_by: Optional[ConflictStrategy] = None
    resolution_value: Any = None

    def key_paths(self) -> List[str]:
        return list(self.changes.keys())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "delta_id": self.delta_id,
            "state_scope": self.state_scope,
            "direction": self.direction.value,
            "key_paths": self.key_paths(),
            "priority": self.priority.name,
            "conflict": self.conflict,
            "resolved": self.resolved,
            "timestamp": self.timestamp,
        }


@dataclass
class SyncCheckpoint:
    checkpoint_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    state_scope: str = ""
    snapshot_data: Dict[str, Any] = field(default_factory=dict)
    version: int = 0
    created: float = field(default_factory=time.time)
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "state_scope": self.state_scope,
            "version": self.version,
            "created": self.created,
            "label": self.label,
            "age_seconds": time.time() - self.created,
        }


class ContextSyncEngine:
    """Bidirectional context synchronization engine — agent knowledge ↔ engine runtime."""

    _instance: Optional["ContextSyncEngine"] = None
    _lock = threading.Lock()

    MAX_PENDING_PER_SCOPE = 500
    MAX_CHECKPOINTS_PER_SCOPE = 20
    MAX_DELTA_HISTORY = 2000

    def __init__(self):
        self._states: Dict[str, SyncState] = {}
        self._pending_agent_deltas: Dict[str, List[SyncDelta]] = defaultdict(list)
        self._pending_engine_deltas: Dict[str, List[SyncDelta]] = defaultdict(list)
        self._delta_history: List[SyncDelta] = []
        self._checkpoints: Dict[str, List[SyncCheckpoint]] = defaultdict(list)
        self._priority_queues: Dict[SyncPriority, List[SyncDelta]] = {
            SyncPriority.CRITICAL: [],
            SyncPriority.HIGH: [],
            SyncPriority.NORMAL: [],
            SyncPriority.LOW: [],
        }
        self._total_synced: int = 0
        self._total_conflicts: int = 0
        self._total_resolved: int = 0

    @classmethod
    def get_instance(cls) -> "ContextSyncEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_state(self, scope: str, initial_data: Dict[str, Any]) -> SyncState:
        if not scope:
            raise ValueError("Scope must be a non-empty string")

        with self._lock:
            if scope in self._states:
                existing = self._states[scope]
                existing.agent_data.update(initial_data)
                existing.engine_data.update(initial_data)
                existing.version += 1
                return existing

            state = SyncState(
                scope=scope,
                agent_data=dict(initial_data),
                engine_data=dict(initial_data),
                version=1,
                last_synced=time.time(),
            )
            self._states[scope] = state
            return state

    def push_agent_update(self, scope: str, key_path: str, value: Any,
                          priority: SyncPriority = SyncPriority.NORMAL) -> SyncDelta:
        return self._push_update(scope, key_path, value, priority, SyncDirection.AGENT_TO_ENGINE)

    def push_engine_update(self, scope: str, key_path: str, value: Any,
                           priority: SyncPriority = SyncPriority.NORMAL) -> SyncDelta:
        return self._push_update(scope, key_path, value, priority, SyncDirection.ENGINE_TO_AGENT)

    def _push_update(self, scope: str, key_path: str, value: Any,
                     priority: SyncPriority, direction: SyncDirection) -> SyncDelta:
        if not scope:
            raise ValueError("Scope must be a non-empty string")
        if not key_path:
            raise ValueError("Key path must be a non-empty string")

        with self._lock:
            state = self._states.get(scope)
            if state is None:
                raise ValueError(f"Unknown scope: {scope}. Call register_state() first.")

            old_value = self._get_nested(state.agent_data if direction == SyncDirection.AGENT_TO_ENGINE
                                        else state.engine_data, key_path)

            self._set_nested(state.agent_data if direction == SyncDirection.AGENT_TO_ENGINE
                             else state.engine_data, key_path, value)

            state.version += 1

            delta = SyncDelta(
                state_scope=scope,
                direction=direction,
                changes={key_path: (old_value, value)},
                priority=priority,
                conflict=False,
            )

            if direction == SyncDirection.AGENT_TO_ENGINE:
                self._pending_agent_deltas[scope].append(delta)
                self._trim_list(self._pending_agent_deltas[scope], self.MAX_PENDING_PER_SCOPE)
            else:
                self._pending_engine_deltas[scope].append(delta)
                self._trim_list(self._pending_engine_deltas[scope], self.MAX_PENDING_PER_SCOPE)

            self._priority_queues[priority].append(delta)
            self._delta_history.append(delta)
            self._trim_list(self._delta_history, self.MAX_DELTA_HISTORY)

            if priority == SyncPriority.CRITICAL:
                self._sync_critical_now(scope)

            return delta

    def sync_now(self, scope: str, direction: SyncDirection = SyncDirection.BIDIRECTIONAL) -> List[SyncDelta]:
        if scope not in self._states:
            raise ValueError(f"Unknown scope: {scope}")

        resolved: List[SyncDelta] = []

        with self._lock:
            state = self._states[scope]
            agent_pending = list(self._pending_agent_deltas.get(scope, []))
            engine_pending = list(self._pending_engine_deltas.get(scope, []))

            conflicts = self._find_conflicts(agent_pending, engine_pending)
            for delta in conflicts:
                delta.conflict = True
                self._total_conflicts += 1

            if direction in (SyncDirection.AGENT_TO_ENGINE, SyncDirection.BIDIRECTIONAL):
                for delta in agent_pending:
                    if delta.conflict:
                        continue
                    for key_path, (_, new_val) in delta.changes.items():
                        self._set_nested(state.engine_data, key_path, new_val)
                    delta.resolved = True
                    resolved.append(delta)

            if direction in (SyncDirection.ENGINE_TO_AGENT, SyncDirection.BIDIRECTIONAL):
                for delta in engine_pending:
                    if delta.conflict:
                        continue
                    for key_path, (_, new_val) in delta.changes.items():
                        self._set_nested(state.agent_data, key_path, new_val)
                    delta.resolved = True
                    resolved.append(delta)

            self._pending_agent_deltas[scope] = [d for d in agent_pending if not d.resolved]
            self._pending_engine_deltas[scope] = [d for d in engine_pending if not d.resolved]

            state.last_synced = time.time()
            self._total_synced += len(resolved)

        return resolved

    def detect_conflicts(self, scope: str) -> List[SyncDelta]:
        if scope not in self._states:
            return []

        with self._lock:
            agent_pending = list(self._pending_agent_deltas.get(scope, []))
            engine_pending = list(self._pending_engine_deltas.get(scope, []))
            conflicts = self._find_conflicts(agent_pending, engine_pending)

            remaining_conflicts = []
            for ad, ed in conflicts:
                if not ad.resolved:
                    ad.conflict = True
                    remaining_conflicts.append(ad)
                if not ed.resolved:
                    ed.conflict = True
                    remaining_conflicts.append(ed)

            return remaining_conflicts

    def resolve_conflict(self, delta_id: str, strategy: ConflictStrategy = ConflictStrategy.MERGE) -> SyncDelta:
        target: Optional[SyncDelta] = None

        with self._lock:
            for scope, deltas in self._pending_agent_deltas.items():
                for d in deltas:
                    if d.delta_id == delta_id:
                        target = d
                        break
                if target:
                    scope_name = scope
                    break

            if target is None:
                for scope, deltas in self._pending_engine_deltas.items():
                    for d in deltas:
                        if d.delta_id == delta_id:
                            target = d
                            break
                    if target:
                        scope_name = scope
                        break

            if target is None:
                raise ValueError(f"Unresolved delta not found: {delta_id}")

            state = self._states.get(scope_name)
            if state is None:
                raise ValueError(f"State not found for scope: {scope_name}")

            target.conflict = False
            target.resolved = True
            target.resolved_by = strategy

            for key_path, (old_val, new_val) in target.changes.items():
                if strategy == ConflictStrategy.AGENT_WINS:
                    target.resolution_value = new_val
                    if target.direction == SyncDirection.ENGINE_TO_AGENT:
                        self._set_nested(state.engine_data, key_path, new_val)
                    else:
                        self._set_nested(state.engine_data, key_path, new_val)
                elif strategy == ConflictStrategy.ENGINE_WINS:
                    target.resolution_value = old_val
                    if target.direction == SyncDirection.AGENT_TO_ENGINE:
                        self._set_nested(state.agent_data, key_path, old_val)
                    else:
                        self._set_nested(state.agent_data, key_path, old_val)
                elif strategy == ConflictStrategy.MERGE:
                    merged = self._merge_values(old_val, new_val)
                    target.resolution_value = merged
                    self._set_nested(state.engine_data, key_path, merged)
                    self._set_nested(state.agent_data, key_path, merged)
                elif strategy == ConflictStrategy.MANUAL_RESOLVE:
                    target.resolved = False

            if target.resolved:
                self._total_resolved += 1

            self._pending_agent_deltas[scope_name] = [
                d for d in self._pending_agent_deltas.get(scope_name, [])
                if not d.resolved
            ]
            self._pending_engine_deltas[scope_name] = [
                d for d in self._pending_engine_deltas.get(scope_name, [])
                if not d.resolved
            ]

            state.last_synced = time.time()
            return target

    def create_checkpoint(self, scope: str, label: str = "") -> SyncCheckpoint:
        if scope not in self._states:
            raise ValueError(f"Unknown scope: {scope}")

        with self._lock:
            state = self._states[scope]
            snapshot = {
                "agent_data": dict(state.agent_data),
                "engine_data": dict(state.engine_data),
                "version": state.version,
                "last_synced": state.last_synced,
            }

            checkpoint = SyncCheckpoint(
                state_scope=scope,
                snapshot_data=snapshot,
                version=state.version,
                label=label or f"checkpoint_{state.version}",
            )

            self._checkpoints[scope].append(checkpoint)
            self._trim_list(self._checkpoints[scope], self.MAX_CHECKPOINTS_PER_SCOPE)
            return checkpoint

    def rollback_to_checkpoint(self, checkpoint_id: str) -> SyncState:
        with self._lock:
            for scope, checkpoints in self._checkpoints.items():
                for checkpoint in checkpoints:
                    if checkpoint.checkpoint_id == checkpoint_id:
                        state = self._states.get(scope)
                        if state is None:
                            raise ValueError(f"State not found for scope: {scope}")

                        snap = checkpoint.snapshot_data
                        state.agent_data = dict(snap.get("agent_data", {}))
                        state.engine_data = dict(snap.get("engine_data", {}))
                        state.version = snap.get("version", state.version)
                        state.last_synced = time.time()

                        self._pending_agent_deltas[scope].clear()
                        self._pending_engine_deltas[scope].clear()

                        return state

        raise ValueError(f"Checkpoint not found: {checkpoint_id}")

    def verify_consistency(self, scope: str) -> Dict[str, Any]:
        if scope not in self._states:
            return {"is_consistent": False, "discrepancies": [f"Unknown scope: {scope}"]}

        state = self._states[scope]
        discrepancies: List[Dict[str, Any]] = []

        all_keys = set(state.agent_data.keys()) | set(state.engine_data.keys())

        for key in sorted(all_keys):
            av = self._get_nested(state.agent_data, key)
            ev = self._get_nested(state.engine_data, key)

            if key not in state.agent_data:
                discrepancies.append({
                    "key": key,
                    "type": "missing_in_agent",
                    "engine_value": str(ev),
                })
            elif key not in state.engine_data:
                discrepancies.append({
                    "key": key,
                    "type": "missing_in_engine",
                    "agent_value": str(av),
                })
            elif av != ev:
                discrepancies.append({
                    "key": key,
                    "type": "value_mismatch",
                    "agent_value": str(av),
                    "engine_value": str(ev),
                })

        pending_agent = len(self._pending_agent_deltas.get(scope, []))
        pending_engine = len(self._pending_engine_deltas.get(scope, []))

        return {
            "is_consistent": len(discrepancies) == 0 and pending_agent == 0 and pending_engine == 0,
            "discrepancies": discrepancies,
            "pending_agent_deltas": pending_agent,
            "pending_engine_deltas": pending_engine,
            "scope": scope,
            "version": state.version,
            "last_synced": state.last_synced,
        }

    def get_stats(self) -> Dict[str, Any]:
        with self._lock:
            total_deltas = len(self._delta_history)
            pending_agent = sum(len(v) for v in self._pending_agent_deltas.values())
            pending_engine = sum(len(v) for v in self._pending_engine_deltas.values())
            total_checkpoints = sum(len(v) for v in self._checkpoints.values())

            scope_details = {}
            for scope, state in self._states.items():
                agent_pending = len(self._pending_agent_deltas.get(scope, []))
                engine_pending = len(self._pending_engine_deltas.get(scope, []))
                scope_checkpoints = len(self._checkpoints.get(scope, []))
                scope_details[scope] = {
                    "version": state.version,
                    "last_synced": state.last_synced,
                    "agent_keys": len(state.agent_data),
                    "engine_keys": len(state.engine_data),
                    "pending_agent_deltas": agent_pending,
                    "pending_engine_deltas": engine_pending,
                    "checkpoints": scope_checkpoints,
                }

            return {
                "registered_scopes": len(self._states),
                "total_deltas": total_deltas,
                "pending_syncs": pending_agent + pending_engine,
                "pending_agent_deltas": pending_agent,
                "pending_engine_deltas": pending_engine,
                "checkpoint_count": total_checkpoints,
                "total_synced": self._total_synced,
                "total_conflicts": self._total_conflicts,
                "total_resolved": self._total_resolved,
                "scopes": scope_details,
                "priority_queues": {
                    p.name: len(v) for p, v in self._priority_queues.items()
                },
            }

    def _find_conflicts(self, agent_deltas: List[SyncDelta],
                        engine_deltas: List[SyncDelta]) -> List[Tuple[SyncDelta, SyncDelta]]:
        conflicts: List[Tuple[SyncDelta, SyncDelta]] = []
        agent_paths = defaultdict(list)
        for delta in agent_deltas:
            for kp in delta.key_paths():
                agent_paths[kp].append(delta)

        for ed in engine_deltas:
            for kp in ed.key_paths():
                if kp in agent_paths:
                    for ad in agent_paths[kp]:
                        _, av = list(ad.changes.get(kp, (None, None)))
                        _, ev = list(ed.changes.get(kp, (None, None)))
                        if av != ev:
                            conflicts.append((ad, ed))
        return conflicts

    def _sync_critical_now(self, scope: str) -> None:
        self.sync_now(scope, SyncDirection.BIDIRECTIONAL)

    @staticmethod
    def _get_nested(data: Dict[str, Any], key_path: str) -> Any:
        if "." not in key_path:
            return data.get(key_path)

        parts = key_path.split(".")
        current = data
        for part in parts[:-1]:
            if isinstance(current, dict):
                current = current.get(part, {})
            else:
                return None
        return current.get(parts[-1]) if isinstance(current, dict) else None

    @staticmethod
    def _set_nested(data: Dict[str, Any], key_path: str, value: Any) -> None:
        if "." not in key_path:
            data[key_path] = value
            return

        parts = key_path.split(".")
        current = data
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part], dict):
                current[part] = {}
            current = current[part]
        current[parts[-1]] = value

    @staticmethod
    def _merge_values(old_val: Any, new_val: Any) -> Any:
        if isinstance(old_val, dict) and isinstance(new_val, dict):
            merged = dict(old_val)
            merged.update(new_val)
            return merged
        if isinstance(old_val, list) and isinstance(new_val, list):
            seen = set()
            merged = []
            for item in old_val + new_val:
                key = str(item)
                if key not in seen:
                    seen.add(key)
                    merged.append(item)
            return merged
        if isinstance(old_val, (int, float)) and isinstance(new_val, (int, float)):
            return (old_val + new_val) / 2.0
        return new_val

    @staticmethod
    def _trim_list(lst: List[Any], max_size: int) -> None:
        if len(lst) > max_size:
            overflow = len(lst) - max_size
            del lst[:overflow]

    def pending_deltas(self, scope: str, direction: Optional[SyncDirection] = None) -> List[SyncDelta]:
        if direction == SyncDirection.AGENT_TO_ENGINE:
            return list(self._pending_agent_deltas.get(scope, []))
        if direction == SyncDirection.ENGINE_TO_AGENT:
            return list(self._pending_engine_deltas.get(scope, []))
        return list(self._pending_agent_deltas.get(scope, [])) + list(
            self._pending_engine_deltas.get(scope, []))

    def checkpoint_history(self, scope: str) -> List[SyncCheckpoint]:
        return list(self._checkpoints.get(scope, []))

    def reset_scope(self, scope: str) -> bool:
        with self._lock:
            if scope not in self._states:
                return False
            del self._states[scope]
            self._pending_agent_deltas.pop(scope, None)
            self._pending_engine_deltas.pop(scope, None)
            self._checkpoints.pop(scope, None)
            return True

    def reset_all(self) -> None:
        with self._lock:
            self._states.clear()
            self._pending_agent_deltas.clear()
            self._pending_engine_deltas.clear()
            self._delta_history.clear()
            self._checkpoints.clear()
            for queue in self._priority_queues.values():
                queue.clear()
            self._total_synced = 0
            self._total_conflicts = 0
            self._total_resolved = 0


def get_context_sync() -> ContextSyncEngine:
    return ContextSyncEngine.get_instance()