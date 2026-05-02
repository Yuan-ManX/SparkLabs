"""
Cloud Sync - Cloud save synchronization with conflict resolution.

Architecture:
    CloudSync/
    |-- SyncState (synchronization lifecycle states)
    |-- SaveData (serializable save container)
    |-- SyncOperation (sync direction enumeration)
    |-- ConflictStrategy (resolution approach enumeration)
    |-- SyncResult (operation outcome container)
    |-- CloudSync (unified synchronization orchestrator)

Manages cloud save/load with version tracking, delta synchronization,
conflict resolution strategies, and retry with exponential backoff.
"""

from __future__ import annotations

import hashlib
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class SyncState(Enum):
    LOCAL_ONLY = auto()
    SYNCED = auto()
    MODIFIED_LOCAL = auto()
    MODIFIED_REMOTE = auto()
    CONFLICT = auto()
    SYNCING = auto()
    OFFLINE = auto()
    ERROR = auto()


class SyncOperation(Enum):
    UPLOAD = auto()
    DOWNLOAD = auto()
    MERGE = auto()
    RESOLVE = auto()


class ConflictStrategy(Enum):
    LAST_WRITE_WINS = auto()
    LOCAL_WINS = auto()
    REMOTE_WINS = auto()
    MANUAL_MERGE = auto()
    KEEP_BOTH = auto()


@dataclass
class SaveData:
    save_id: str = ""
    owner_id: str = ""
    game_id: str = ""
    slot_name: str = "auto"
    data: Dict[str, Any] = field(default_factory=dict)
    version: int = 1
    timestamp: float = 0.0
    checksum: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    state: SyncState = SyncState.LOCAL_ONLY
    size_bytes: int = 0

    def __post_init__(self):
        if not self.save_id:
            self.save_id = uuid.uuid4().hex[:14]
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.checksum:
            self.compute_checksum()
        if not self.size_bytes:
            self.size_bytes = len(json.dumps(self.data, ensure_ascii=False))

    def compute_checksum(self) -> str:
        raw = json.dumps(self.data, sort_keys=True, ensure_ascii=False)
        self.checksum = hashlib.sha256(raw.encode()).hexdigest()
        return self.checksum

    def compute_delta(self, other: "SaveData") -> Optional[Dict[str, Any]]:
        """Compute changed fields between two saves."""
        delta: Dict[str, Any] = {"added": {}, "removed": [], "modified": {}}
        own_keys = set(self.data.keys())
        other_keys = set(other.data.keys())

        for key in other_keys - own_keys:
            delta["added"][key] = other.data[key]

        for key in own_keys - other_keys:
            delta["removed"].append(key)

        for key in own_keys & other_keys:
            if self.data[key] != other.data[key]:
                delta["modified"][key] = {
                    "old": self.data[key],
                    "new": other.data[key],
                }

        if not delta["added"] and not delta["removed"] and not delta["modified"]:
            return None
        return delta

    def apply_delta(self, delta: Dict[str, Any]) -> None:
        for key, value in delta.get("added", {}).items():
            self.data[key] = value
        for key in delta.get("removed", []):
            self.data.pop(key, None)
        for key, change in delta.get("modified", {}).items():
            self.data[key] = change["new"]
        self.version += 1
        self.timestamp = time.time()
        self.compute_checksum()
        self.size_bytes = len(json.dumps(self.data, ensure_ascii=False))

    def to_summary(self) -> Dict[str, Any]:
        return {
            "save_id": self.save_id,
            "owner_id": self.owner_id,
            "game_id": self.game_id,
            "slot_name": self.slot_name,
            "version": self.version,
            "timestamp": self.timestamp,
            "state": self.state.name.lower(),
            "size_bytes": self.size_bytes,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            **self.to_summary(),
            "data": self.data,
            "checksum": self.checksum,
            "metadata": self.metadata,
        }


@dataclass
class SyncResult:
    operation: SyncOperation
    success: bool
    save_id: str
    new_state: SyncState
    message: str = ""
    conflict_detected: bool = False
    bytes_transferred: int = 0
    duration_ms: float = 0.0
    resolved_save: Optional[SaveData] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "operation": self.operation.name.lower(),
            "success": self.success,
            "save_id": self.save_id,
            "new_state": self.new_state.name.lower(),
            "message": self.message,
            "conflict_detected": self.conflict_detected,
            "bytes_transferred": self.bytes_transferred,
            "duration_ms": self.duration_ms,
        }


class CloudSync:
    """Cloud save synchronization orchestrator with conflict resolution."""

    _instance: Optional["CloudSync"] = None

    def __init__(self):
        self._local_saves: Dict[str, SaveData] = {}
        self._remote_cache: Dict[str, SaveData] = {}
        self._sync_queue: List[Tuple[str, SyncOperation]] = []
        self._conflict_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS
        self._is_online: bool = False
        self._upload_fn: Optional[Callable] = None
        self._download_fn: Optional[Callable] = None
        self._total_syncs = 0
        self._total_conflicts = 0
        self._total_failures = 0
        self._max_retries: int = 3
        self._retry_delay_base: float = 1.0

    @classmethod
    def get_instance(cls) -> "CloudSync":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def configure(self, upload_fn: Callable, download_fn: Callable,
                  conflict_strategy: ConflictStrategy = ConflictStrategy.LAST_WRITE_WINS,
                  max_retries: int = 3) -> None:
        self._upload_fn = upload_fn
        self._download_fn = download_fn
        self._conflict_strategy = conflict_strategy
        self._max_retries = max_retries

    def set_online(self, online: bool) -> None:
        was_offline = not self._is_online
        self._is_online = online
        if online and was_offline and self._sync_queue:
            self.flush_queue()

    @property
    def is_online(self) -> bool:
        return self._is_online

    def create_save(self, owner_id: str, game_id: str, data: Dict[str, Any],
                    slot_name: str = "auto") -> SaveData:
        save = SaveData(
            owner_id=owner_id,
            game_id=game_id,
            data=data,
            slot_name=slot_name,
            state=SyncState.LOCAL_ONLY,
        )
        self._local_saves[save.save_id] = save
        return save

    def get_local_save(self, save_id: str) -> Optional[SaveData]:
        return self._local_saves.get(save_id)

    def list_local_saves(self, owner_id: Optional[str] = None,
                         game_id: Optional[str] = None) -> List[SaveData]:
        saves = list(self._local_saves.values())
        if owner_id:
            saves = [s for s in saves if s.owner_id == owner_id]
        if game_id:
            saves = [s for s in saves if s.game_id == game_id]
        return sorted(saves, key=lambda s: s.timestamp, reverse=True)

    def update_local_save(self, save_id: str, data: Dict[str, Any]) -> bool:
        save = self._local_saves.get(save_id)
        if not save:
            return False
        save.data = data
        save.version += 1
        save.timestamp = time.time()
        save.compute_checksum()
        if save.state == SyncState.SYNCED:
            save.state = SyncState.MODIFIED_LOCAL
        return True

    def delete_local_save(self, save_id: str) -> bool:
        if save_id in self._local_saves:
            del self._local_saves[save_id]
            return True
        return False

    def push(self, save_id: str) -> SyncResult:
        """Upload local save to cloud."""
        self._total_syncs += 1
        start = time.monotonic()

        save = self._local_saves.get(save_id)
        if not save:
            return SyncResult(SyncOperation.UPLOAD, False, save_id, SyncState.ERROR,
                              "Save not found")

        if not self._is_online:
            self._sync_queue.append((save_id, SyncOperation.UPLOAD))
            return SyncResult(SyncOperation.UPLOAD, False, save_id, SyncState.OFFLINE,
                              "Offline: queued for sync")

        save.state = SyncState.SYNCING

        if self._upload_fn:
            result = self._retry_operation(lambda: self._upload_fn(save.to_dict()))
            if not result:
                save.state = SyncState.MODIFIED_LOCAL
                self._total_failures += 1
                return SyncResult(SyncOperation.UPLOAD, False, save_id,
                                  SyncState.ERROR, "Upload failed after retries",
                                  bytes_transferred=0)

        self._remote_cache[save_id] = save
        save.state = SyncState.SYNCED

        duration = (time.monotonic() - start) * 1000
        return SyncResult(SyncOperation.UPLOAD, True, save_id, SyncState.SYNCED,
                          "Upload successful", bytes_transferred=save.size_bytes,
                          duration_ms=duration)

    def pull(self, save_id: str) -> SyncResult:
        """Download save from cloud to local."""
        self._total_syncs += 1
        start = time.monotonic()

        if not self._is_online:
            return SyncResult(SyncOperation.DOWNLOAD, False, save_id, SyncState.OFFLINE,
                              "Cannot pull while offline")

        remote_data = None
        if self._download_fn:
            result = self._retry_operation(lambda: self._download_fn(save_id))
            if result:
                remote_data = result

        if not remote_data:
            return SyncResult(SyncOperation.DOWNLOAD, False, save_id, SyncState.ERROR,
                              "Download failed")

        remote_save = SaveData(**remote_data) if isinstance(remote_data, dict) else None
        if not remote_save:
            return SyncResult(SyncOperation.DOWNLOAD, False, save_id, SyncState.ERROR,
                              "Invalid remote data format")

        local_save = self._local_saves.get(save_id)

        if local_save:
            conflict, resolved = self._detect_and_resolve_conflict(local_save, remote_save)
            if conflict:
                self._total_conflicts += 1
                if resolved:
                    self._local_saves[save_id] = resolved
                    duration = (time.monotonic() - start) * 1000
                    return SyncResult(SyncOperation.DOWNLOAD, True, save_id,
                                      SyncState.SYNCED, "Conflict resolved",
                                      conflict_detected=True,
                                      bytes_transferred=resolved.size_bytes,
                                      duration_ms=duration,
                                      resolved_save=resolved)
                return SyncResult(SyncOperation.DOWNLOAD, False, save_id,
                                  SyncState.CONFLICT, "Unresolved conflict",
                                  conflict_detected=True)

        self._local_saves[save_id] = remote_save
        remote_save.state = SyncState.SYNCED
        duration = (time.monotonic() - start) * 1000
        return SyncResult(SyncOperation.DOWNLOAD, True, save_id, SyncState.SYNCED,
                          "Download successful", bytes_transferred=remote_save.size_bytes,
                          duration_ms=duration)

    def sync(self, save_id: str) -> SyncResult:
        """Bidirectional sync: push local changes, pull remote updates."""
        local = self._local_saves.get(save_id)
        if not local:
            return self.pull(save_id)

        if local.state in (SyncState.LOCAL_ONLY, SyncState.MODIFIED_LOCAL):
            push_result = self.push(save_id)
            if not push_result.success:
                return push_result

        return self.pull(save_id)

    def _detect_and_resolve_conflict(self, local: SaveData,
                                     remote: SaveData) -> Tuple[bool, Optional[SaveData]]:
        if local.checksum == remote.checksum:
            return False, None

        strategy = self._conflict_strategy

        if strategy == ConflictStrategy.LAST_WRITE_WINS:
            winner = local if local.timestamp >= remote.timestamp else remote
            winner.state = SyncState.SYNCED
            return True, winner

        elif strategy == ConflictStrategy.LOCAL_WINS:
            local.state = SyncState.SYNCED
            return True, local

        elif strategy == ConflictStrategy.REMOTE_WINS:
            remote.state = SyncState.SYNCED
            return True, remote

        elif strategy == ConflictStrategy.KEEP_BOTH:
            backup = SaveData(
                owner_id=local.owner_id,
                game_id=local.game_id,
                data=dict(local.data),
                slot_name=f"{local.slot_name}_conflict_{uuid.uuid4().hex[:6]}",
            )
            self._local_saves[backup.save_id] = backup
            remote.state = SyncState.SYNCED
            return True, remote

        elif strategy == ConflictStrategy.MANUAL_MERGE:
            return True, None

        return False, None

    def resolve_conflict(self, save_id: str, choose_local: bool = True) -> bool:
        local = self._local_saves.get(save_id)
        if not local:
            return False
        local.state = SyncState.SYNCED if choose_local else SyncState.MODIFIED_REMOTE
        return True

    def _retry_operation(self, operation: Callable) -> Any:
        last_error = None
        for attempt in range(self._max_retries):
            try:
                result = operation()
                if result is not None:
                    return result
            except Exception as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    time.sleep(self._retry_delay_base * (2 ** attempt))
        return None

    def flush_queue(self) -> int:
        flushed = 0
        queue_copy = list(self._sync_queue)
        self._sync_queue.clear()
        for save_id, op in queue_copy:
            if op == SyncOperation.UPLOAD:
                result = self.push(save_id)
            elif op == SyncOperation.DOWNLOAD:
                result = self.pull(save_id)
            else:
                continue
            if result.success:
                flushed += 1
            else:
                self._sync_queue.append((save_id, op))
        return flushed

    def get_queue_size(self) -> int:
        return len(self._sync_queue)

    def verify_integrity(self, save_id: str) -> bool:
        save = self._local_saves.get(save_id)
        if not save:
            return False
        original_checksum = save.checksum
        save.compute_checksum()
        matches = save.checksum == original_checksum
        save.checksum = original_checksum
        return matches

    def get_stats(self) -> Dict[str, Any]:
        synced_count = sum(1 for s in self._local_saves.values()
                          if s.state == SyncState.SYNCED)
        conflict_count = sum(1 for s in self._local_saves.values()
                            if s.state == SyncState.CONFLICT)
        return {
            "total_saves": len(self._local_saves),
            "synced": synced_count,
            "conflicts": conflict_count,
            "offline": not self._is_online,
            "queue_size": len(self._sync_queue),
            "total_syncs": self._total_syncs,
            "total_conflicts": self._total_conflicts,
            "total_failures": self._total_failures,
            "conflict_rate": (self._total_conflicts / self._total_syncs * 100)
            if self._total_syncs > 0 else 0.0,
            "failure_rate": (self._total_failures / self._total_syncs * 100)
            if self._total_syncs > 0 else 0.0,
        }

    def clear(self) -> None:
        self._local_saves.clear()
        self._remote_cache.clear()
        self._sync_queue.clear()
        self._total_syncs = 0
        self._total_conflicts = 0
        self._total_failures = 0


def get_cloud_sync() -> CloudSync:
    return CloudSync.get_instance()
