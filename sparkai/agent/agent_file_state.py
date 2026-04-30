"""
SparkAI Agent - File State Coordination Engine

Tracks which agent reads and writes which file to prevent
stale-cache bugs in multi-agent workflows. Provides write-lock
coordination, stale-cache detection, and file versioning.
"""

import asyncio
import hashlib
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class FileAccess(Enum):
    READ = "read"
    WRITE = "write"
    CREATE = "create"
    DELETE = "delete"


class LockState(Enum):
    FREE = "free"
    READ_LOCKED = "read_locked"
    WRITE_LOCKED = "write_locked"


@dataclass
class FileVersion:
    version: int = 1
    content_hash: str = ""
    modified_at: float = field(default_factory=time.time)
    modified_by: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "content_hash": self.content_hash,
            "modified_at": self.modified_at,
            "modified_by": self.modified_by,
        }


@dataclass
class FileAccessRecord:
    agent_id: str
    file_path: str
    access: FileAccess
    timestamp: float = field(default_factory=time.time)
    version_at_access: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "file_path": self.file_path,
            "access": self.access.value,
            "timestamp": self.timestamp,
            "version_at_access": self.version_at_access,
        }


@dataclass
class StaleCacheAlert:
    agent_id: str
    file_path: str
    cached_version: int
    current_version: int
    stale_by: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "file_path": self.file_path,
            "cached_version": self.cached_version,
            "current_version": self.current_version,
            "stale_by": self.stale_by,
            "timestamp": self.timestamp,
        }


@dataclass
class WriteLock:
    file_path: str
    agent_id: str
    acquired_at: float = field(default_factory=time.time)
    timeout_seconds: float = 300.0

    @property
    def is_expired(self) -> bool:
        return time.time() - self.acquired_at > self.timeout_seconds

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "agent_id": self.agent_id,
            "acquired_at": self.acquired_at,
            "timeout_seconds": self.timeout_seconds,
            "is_expired": self.is_expired,
        }


class FileStateEngine:
    """
    Coordinates file access across multiple agents to prevent
    stale-cache bugs, write conflicts, and data loss.
    """

    def __init__(self):
        self._versions: Dict[str, FileVersion] = {}
        self._access_log: List[FileAccessRecord] = []
        self._write_locks: Dict[str, WriteLock] = {}
        self._agent_reads: Dict[str, Dict[str, int]] = {}
        self._stale_alerts: List[StaleCacheAlert] = []
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
        self._stats = {
            "reads": 0,
            "writes": 0,
            "conflicts_detected": 0,
            "locks_acquired": 0,
            "locks_expired": 0,
            "stale_cache_alerts": 0,
        }

    def register_read(self, agent_id: str, file_path: str) -> FileVersion:
        version = self._versions.get(file_path)
        current_version = version.version if version else 0

        record = FileAccessRecord(
            agent_id=agent_id,
            file_path=file_path,
            access=FileAccess.READ,
            version_at_access=current_version,
        )
        self._access_log.append(record)

        if agent_id not in self._agent_reads:
            self._agent_reads[agent_id] = {}
        self._agent_reads[agent_id][file_path] = current_version

        self._stats["reads"] += 1
        return version or FileVersion()

    def register_write(self, agent_id: str, file_path: str, content: str = "") -> FileVersion:
        current = self._versions.get(file_path)
        new_version = (current.version + 1) if current else 1

        content_hash = ""
        if content:
            content_hash = hashlib.md5(content.encode()).hexdigest()[:12]

        version = FileVersion(
            version=new_version,
            content_hash=content_hash,
            modified_by=agent_id,
        )
        self._versions[file_path] = version

        record = FileAccessRecord(
            agent_id=agent_id,
            file_path=file_path,
            access=FileAccess.WRITE,
            version_at_access=new_version,
        )
        self._access_log.append(record)

        self._check_stale_reads(agent_id, file_path, new_version)

        self._stats["writes"] += 1
        return version

    def register_create(self, agent_id: str, file_path: str, content: str = "") -> FileVersion:
        version = FileVersion(
            version=1,
            content_hash=hashlib.md5(content.encode()).hexdigest()[:12] if content else "",
            modified_by=agent_id,
        )
        self._versions[file_path] = version

        record = FileAccessRecord(
            agent_id=agent_id,
            file_path=file_path,
            access=FileAccess.CREATE,
            version_at_access=1,
        )
        self._access_log.append(record)
        self._stats["writes"] += 1
        return version

    def register_delete(self, agent_id: str, file_path: str) -> None:
        if file_path in self._versions:
            del self._versions[file_path]

        record = FileAccessRecord(
            agent_id=agent_id,
            file_path=file_path,
            access=FileAccess.DELETE,
        )
        self._access_log.append(record)
        self._stats["writes"] += 1

    def _check_stale_reads(self, writer_id: str, file_path: str, new_version: int) -> None:
        for agent_id, reads in self._agent_reads.items():
            if agent_id == writer_id:
                continue
            if file_path in reads and reads[file_path] < new_version:
                alert = StaleCacheAlert(
                    agent_id=agent_id,
                    file_path=file_path,
                    cached_version=reads[file_path],
                    current_version=new_version,
                    stale_by=writer_id,
                )
                self._stale_alerts.append(alert)
                self._stats["stale_cache_alerts"] += 1

    def check_stale(self, agent_id: str, file_path: str) -> Optional[StaleCacheAlert]:
        reads = self._agent_reads.get(agent_id, {})
        if file_path not in reads:
            return None
        cached_version = reads[file_path]
        current = self._versions.get(file_path)
        if current and current.version > cached_version:
            return StaleCacheAlert(
                agent_id=agent_id,
                file_path=file_path,
                cached_version=cached_version,
                current_version=current.version,
                stale_by=current.modified_by,
            )
        return None

    def get_stale_alerts(self, agent_id: str) -> List[StaleCacheAlert]:
        return [a for a in self._stale_alerts if a.agent_id == agent_id]

    def acquire_write_lock(self, agent_id: str, file_path: str, timeout: float = 300.0) -> Tuple[bool, Optional[str]]:
        existing = self._write_locks.get(file_path)
        if existing:
            if existing.is_expired:
                self._stats["locks_expired"] += 1
                del self._write_locks[file_path]
            elif existing.agent_id != agent_id:
                self._stats["conflicts_detected"] += 1
                return False, f"File locked by agent {existing.agent_id}"

        self._write_locks[file_path] = WriteLock(
            file_path=file_path,
            agent_id=agent_id,
            timeout_seconds=timeout,
        )
        self._stats["locks_acquired"] += 1
        return True, None

    def release_write_lock(self, agent_id: str, file_path: str) -> bool:
        existing = self._write_locks.get(file_path)
        if existing and existing.agent_id == agent_id:
            del self._write_locks[file_path]
            return True
        return False

    def get_lock_state(self, file_path: str) -> LockState:
        lock = self._write_locks.get(file_path)
        if lock and not lock.is_expired:
            return LockState.WRITE_LOCKED
        return LockState.FREE

    def get_file_version(self, file_path: str) -> Optional[FileVersion]:
        return self._versions.get(file_path)

    def get_agent_files(self, agent_id: str) -> Dict[str, int]:
        return dict(self._agent_reads.get(agent_id, {}))

    def get_access_history(self, file_path: str, limit: int = 50) -> List[Dict[str, Any]]:
        records = [r for r in self._access_log if r.file_path == file_path]
        records.sort(key=lambda r: r.timestamp, reverse=True)
        return [r.to_dict() for r in records[:limit]]

    def writes_since(self, agent_id: str, since_version: int, file_path: str) -> List[FileAccessRecord]:
        return [
            r for r in self._access_log
            if r.file_path == file_path
            and r.agent_id != agent_id
            and r.access in (FileAccess.WRITE, FileAccess.CREATE, FileAccess.DELETE)
            and r.version_at_access > since_version
        ]

    def get_stats(self) -> Dict[str, Any]:
        expired_locks = sum(1 for l in self._write_locks.values() if l.is_expired)
        return {
            **self._stats,
            "tracked_files": len(self._versions),
            "active_locks": len(self._write_locks) - expired_locks,
            "expired_locks": expired_locks,
            "total_access_records": len(self._access_log),
            "agents_with_reads": len(self._agent_reads),
            "pending_stale_alerts": len(self._stale_alerts),
        }


_global_engine: Optional[FileStateEngine] = None


def get_file_state_engine() -> FileStateEngine:
    global _global_engine
    if _global_engine is None:
        _global_engine = FileStateEngine()
    return _global_engine


def reset_file_state_engine() -> None:
    global _global_engine
    _global_engine = None
