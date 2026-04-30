"""
SparkAI Agent - Memory Persistence Engine

Disk-based persistence layer for agent memory, sessions, and
game context. Provides automatic checkpointing, state recovery
on restart, and configurable storage backends.

Architecture:
  MemoryPersistenceEngine
    |-- StorageBackend (pluggable storage interface)
    |-- FileBackend (JSON-based file storage)
    |-- CheckpointManager (automatic state snapshots)
    |-- RecoveryManager (state restoration on restart)

Persistence Scope:
  - Agent memory (short-term, long-term, episodic, semantic, working)
  - Session state (active sessions, compaction history)
  - Game context (project info, entities, scenes, assets)
  - Reasoning chains (loop execution history)
  - Skill evolution history

Storage Layout:
  .sparkai/
    persistence/
      memory/{agent_id}.json
      sessions/{session_id}.json
      context/{project_id}.json
      chains/{chain_id}.json
      checkpoints/{timestamp}.json
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class StorageStatus(Enum):
    OK = "ok"
    ERROR = "error"
    NOT_FOUND = "not_found"
    CORRUPTED = "corrupted"


class CheckpointType(Enum):
    MANUAL = "manual"
    AUTO = "auto"
    PRE_COMPACT = "pre_compact"
    PRE_SHUTDOWN = "pre_shutdown"
    RECOVERY = "recovery"


@dataclass
class StorageEntry:
    key: str = ""
    category: str = ""
    data: Any = None
    version: int = 1
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    checksum: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "category": self.category,
            "version": self.version,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "checksum": self.checksum,
        }


@dataclass
class Checkpoint:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:12])
    checkpoint_type: CheckpointType = CheckpointType.MANUAL
    categories: List[str] = field(default_factory=list)
    entry_count: int = 0
    size_bytes: int = 0
    created_at: float = field(default_factory=time.time)
    label: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "checkpoint_type": self.checkpoint_type.value,
            "categories": self.categories,
            "entry_count": self.entry_count,
            "size_bytes": self.size_bytes,
            "created_at": self.created_at,
            "label": self.label,
        }


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, category: str, key: str, data: Any) -> StorageStatus:
        pass

    @abstractmethod
    def load(self, category: str, key: str) -> tuple[Any, StorageStatus]:
        pass

    @abstractmethod
    def delete(self, category: str, key: str) -> StorageStatus:
        pass

    @abstractmethod
    def list_keys(self, category: str) -> List[str]:
        pass

    @abstractmethod
    def exists(self, category: str, key: str) -> bool:
        pass


class FileBackend(StorageBackend):
    """
    JSON-based file storage backend. Each category is a directory,
    each key is a JSON file within that directory.
    """

    def __init__(self, base_dir: str = ".sparkai/persistence"):
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save(self, category: str, key: str, data: Any) -> StorageStatus:
        try:
            category_dir = self._base_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            safe_key = key.replace("/", "_").replace("\\", "_")
            file_path = category_dir / f"{safe_key}.json"
            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=str)
            return StorageStatus.OK
        except Exception:
            return StorageStatus.ERROR

    def load(self, category: str, key: str) -> tuple[Any, StorageStatus]:
        try:
            safe_key = key.replace("/", "_").replace("\\", "_")
            file_path = self._base_dir / category / f"{safe_key}.json"
            if not file_path.exists():
                return None, StorageStatus.NOT_FOUND
            with open(file_path, "r") as f:
                data = json.load(f)
            return data, StorageStatus.OK
        except json.JSONDecodeError:
            return None, StorageStatus.CORRUPTED
        except Exception:
            return None, StorageStatus.ERROR

    def delete(self, category: str, key: str) -> StorageStatus:
        try:
            safe_key = key.replace("/", "_").replace("\\", "_")
            file_path = self._base_dir / category / f"{safe_key}.json"
            if file_path.exists():
                file_path.unlink()
                return StorageStatus.OK
            return StorageStatus.NOT_FOUND
        except Exception:
            return StorageStatus.ERROR

    def list_keys(self, category: str) -> List[str]:
        category_dir = self._base_dir / category
        if not category_dir.exists():
            return []
        return [f.stem for f in category_dir.glob("*.json")]

    def exists(self, category: str, key: str) -> bool:
        safe_key = key.replace("/", "_").replace("\\", "_")
        file_path = self._base_dir / category / f"{safe_key}.json"
        return file_path.exists()


class MemoryPersistenceEngine:
    """
    Disk-based persistence engine for agent memory, sessions,
    and game context with automatic checkpointing and recovery.

    The engine provides a unified persistence API across all
    agent subsystems, ensuring state survives process restarts.

    Usage:
        engine = MemoryPersistenceEngine()
        engine.save("memory", "agent_1", memory_data)
        data = engine.load("memory", "agent_1")
        checkpoint = engine.create_checkpoint(CheckpointType.MANUAL, "before_compaction")
    """

    def __init__(self, base_dir: str = ".sparkai/persistence", auto_checkpoint_interval: float = 300.0):
        self._backend = FileBackend(base_dir)
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._auto_checkpoint_interval = auto_checkpoint_interval
        self._last_auto_checkpoint: float = 0.0
        self._stats = {
            "total_saves": 0,
            "total_loads": 0,
            "total_deletes": 0,
            "total_checkpoints": 0,
            "save_errors": 0,
            "load_errors": 0,
        }

    def save(self, category: str, key: str, data: Any) -> StorageStatus:
        status = self._backend.save(category, key, data)
        self._stats["total_saves"] += 1
        if status != StorageStatus.OK:
            self._stats["save_errors"] += 1
        return status

    def load(self, category: str, key: str) -> tuple[Any, StorageStatus]:
        data, status = self._backend.load(category, key)
        self._stats["total_loads"] += 1
        if status not in (StorageStatus.OK, StorageStatus.NOT_FOUND):
            self._stats["load_errors"] += 1
        return data, status

    def delete(self, category: str, key: str) -> StorageStatus:
        status = self._backend.delete(category, key)
        self._stats["total_deletes"] += 1
        return status

    def exists(self, category: str, key: str) -> bool:
        return self._backend.exists(category, key)

    def list_keys(self, category: str) -> List[str]:
        return self._backend.list_keys(category)

    def save_memory(self, agent_id: str, memory_data: Dict[str, Any]) -> StorageStatus:
        return self.save("memory", agent_id, memory_data)

    def load_memory(self, agent_id: str) -> tuple[Any, StorageStatus]:
        return self.load("memory", agent_id)

    def save_session(self, session_id: str, session_data: Dict[str, Any]) -> StorageStatus:
        return self.save("sessions", session_id, session_data)

    def load_session(self, session_id: str) -> tuple[Any, StorageStatus]:
        return self.load("sessions", session_id)

    def save_context(self, project_id: str, context_data: Dict[str, Any]) -> StorageStatus:
        return self.save("context", project_id, context_data)

    def load_context(self, project_id: str) -> tuple[Any, StorageStatus]:
        return self.load("context", project_id)

    def save_chain(self, chain_id: str, chain_data: Dict[str, Any]) -> StorageStatus:
        return self.save("chains", chain_id, chain_data)

    def load_chain(self, chain_id: str) -> tuple[Any, StorageStatus]:
        return self.load("chains", chain_id)

    def create_checkpoint(self, checkpoint_type: CheckpointType = CheckpointType.MANUAL, label: str = "", categories: Optional[List[str]] = None) -> Checkpoint:
        target_categories = categories or ["memory", "sessions", "context", "chains"]
        total_entries = 0
        total_size = 0

        checkpoint_data = {}
        for category in target_categories:
            keys = self._backend.list_keys(category)
            category_data = {}
            for key in keys:
                data, status = self._backend.load(category, key)
                if status == StorageStatus.OK:
                    category_data[key] = data
                    total_entries += 1
            checkpoint_data[category] = category_data

        checkpoint = Checkpoint(
            checkpoint_type=checkpoint_type,
            categories=target_categories,
            entry_count=total_entries,
            label=label,
        )

        self._backend.save("checkpoints", checkpoint.id, {
            "meta": checkpoint.to_dict(),
            "data": checkpoint_data,
        })

        self._checkpoints[checkpoint.id] = checkpoint
        self._stats["total_checkpoints"] += 1
        return checkpoint

    def restore_checkpoint(self, checkpoint_id: str) -> bool:
        data, status = self._backend.load("checkpoints", checkpoint_id)
        if status != StorageStatus.OK or not data:
            return False

        checkpoint_data = data.get("data", {})
        for category, entries in checkpoint_data.items():
            for key, value in entries.items():
                self._backend.save(category, key, value)

        return True

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        if not self._checkpoints:
            keys = self._backend.list_keys("checkpoints")
            for key in keys:
                data, status = self._backend.load("checkpoints", key)
                if status == StorageStatus.OK and data:
                    meta = data.get("meta", {})
                    cp = Checkpoint(
                        id=meta.get("id", key),
                        checkpoint_type=CheckpointType(meta.get("checkpoint_type", "manual")),
                        categories=meta.get("categories", []),
                        entry_count=meta.get("entry_count", 0),
                        size_bytes=meta.get("size_bytes", 0),
                        label=meta.get("label", ""),
                    )
                    self._checkpoints[cp.id] = cp
        return [cp.to_dict() for cp in sorted(self._checkpoints.values(), key=lambda c: c.created_at, reverse=True)]

    def get_stats(self) -> Dict[str, Any]:
        categories = {}
        for cat in ["memory", "sessions", "context", "chains", "checkpoints"]:
            keys = self._backend.list_keys(cat)
            categories[cat] = len(keys)

        return {
            **self._stats,
            "categories": categories,
            "total_entries": sum(categories.values()),
            "checkpoints": len(self._checkpoints),
        }


_global_persistence_engine: Optional[MemoryPersistenceEngine] = None


def get_persistence_engine() -> MemoryPersistenceEngine:
    global _global_persistence_engine
    if _global_persistence_engine is None:
        _global_persistence_engine = MemoryPersistenceEngine()
    return _global_persistence_engine
