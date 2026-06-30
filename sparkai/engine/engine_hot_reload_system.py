"""
SparkLabs Engine - Hot Reload System

Hot reload system for scripts, scenes, and resources. Watches paths for
modifications, dispatches registered callbacks when targets change, and
records a reload history with success/failure status and timing.

Architecture:
  HotReloadSystem (Singleton)
    |-- ReloadType    (categories of reloadable targets)
    |-- ReloadEvent   (a record of a single reload attempt)
    |-- WatchEntry    (a single watched path/target)
    |-- HotReloadSnapshot (immutable snapshot of system state)

Lifecycle:
  1. watch(path, reload_type, callback) -> WatchEntry
  2. unwatch(watch_id) -> bool
  3. reload(path) -> ReloadEvent
  4. reload_all(reload_type) -> List[ReloadEvent]
  5. get_snapshot() -> HotReloadSnapshot
  6. reset() -> None

Usage:
    system = get_hot_reload_system()
    system.watch("scripts/player.py", ReloadType.SCRIPT, on_reload)
    event = system.reload("scripts/player.py")
    print(event.to_dict())
"""

from __future__ import annotations

import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class ReloadType(Enum):
    """Types of reloadable targets in the engine."""
    SCRIPT = "script"
    SCENE = "scene"
    RESOURCE = "resource"
    CONFIG = "config"
    SHADER = "shader"
    ALL = "all"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ReloadEvent:
    """Record of a single reload attempt.

    Attributes:
        event_id: Unique identifier (auto-generated).
        reload_type: Category of the reloaded target.
        file_path: Filesystem path or logical identifier.
        timestamp: Time the event was created.
        success: Whether the reload succeeded.
        error_message: Optional error message if the reload failed.
        duration_ms: Time spent performing the reload in milliseconds.
    """
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    reload_type: ReloadType = ReloadType.RESOURCE
    file_path: str = ""
    timestamp: float = field(default_factory=time.time)
    success: bool = False
    error_message: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "reload_type": self.reload_type.value,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
        }


@dataclass
class WatchEntry:
    """A single watched path/target.

    Attributes:
        watch_id: Unique identifier (auto-generated).
        path: Filesystem path or logical identifier.
        reload_type: Category of the watched target.
        pattern: Optional glob pattern for matching related paths.
        callback: Callable invoked when the target changes. May be ``None``.
        is_active: Whether this watch is currently active.
    """
    watch_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    path: str = ""
    reload_type: ReloadType = ReloadType.RESOURCE
    pattern: str = "*"
    callback: Optional[Callable[[ReloadEvent], None]] = None
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        # Intentionally omits the callable, which is not serializable.
        return {
            "watch_id": self.watch_id,
            "path": self.path,
            "reload_type": self.reload_type.value,
            "pattern": self.pattern,
            "is_active": self.is_active,
        }


@dataclass
class HotReloadSnapshot:
    """Immutable snapshot of the hot reload system state at a point in time.

    Attributes:
        total_watches: Number of registered watches.
        active_watches: Number of active watches.
        total_events: Number of events in the history buffer.
        successful_reloads: Number of successful reloads recorded.
        failed_reloads: Number of failed reloads recorded.
        watches: Serialized watches captured at snapshot time.
        captured_at: Timestamp when the snapshot was taken.
    """
    total_watches: int = 0
    active_watches: int = 0
    total_events: int = 0
    successful_reloads: int = 0
    failed_reloads: int = 0
    watches: List[Dict[str, Any]] = field(default_factory=list)
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_watches": self.total_watches,
            "active_watches": self.active_watches,
            "total_events": self.total_events,
            "successful_reloads": self.successful_reloads,
            "failed_reloads": self.failed_reloads,
            "watches": list(self.watches),
            "captured_at": self.captured_at,
        }


# =============================================================================
# Hot Reload System (Singleton)
# =============================================================================


class HotReloadSystem:
    """Singleton hot reload system for scripts, scenes, and resources.

    Watches paths for modifications, dispatches registered callbacks when
    changes are detected, and keeps an event history with success/failure
    status and timing. All public methods are thread-safe.

    Typical usage::

        system = HotReloadSystem.get_instance()
        system.watch("scripts/player.py", ReloadType.SCRIPT, on_reload)
        event = system.reload("scripts/player.py")
        for event in system.reload_all(ReloadType.SCENE):
            print(event.to_dict())
    """

    _instance: Optional["HotReloadSystem"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY = 500

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "HotReloadSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._watches: Dict[str, WatchEntry] = {}
        self._path_to_watch: Dict[str, str] = {}
        self._history: List[ReloadEvent] = []
        self._total_reloads: int = 0
        self._successful_reloads: int = 0
        self._failed_reloads: int = 0

    @classmethod
    def get_instance(cls) -> "HotReloadSystem":
        """Return the singleton HotReloadSystem instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Watch Management
    # ------------------------------------------------------------------

    def watch(
        self,
        path: str,
        reload_type: ReloadType,
        callback: Optional[Callable[[ReloadEvent], None]] = None,
        pattern: str = "*",
    ) -> WatchEntry:
        """Register a path for change monitoring.

        If a watch for the same path already exists, it is updated with the
        new callback and reactivated.

        Args:
            path: Filesystem path or logical identifier.
            reload_type: Category of the watched target.
            callback: Callable invoked when the target changes.
            pattern: Optional glob pattern for matching related paths.

        Returns:
            The created (or updated) WatchEntry.
        """
        with self._instance_lock:
            existing_id = self._path_to_watch.get(path)
            if existing_id is not None:
                entry = self._watches[existing_id]
                entry.reload_type = reload_type
                entry.callback = callback
                entry.pattern = pattern
                entry.is_active = True
                return entry

            entry = WatchEntry(
                path=path,
                reload_type=reload_type,
                pattern=pattern,
                callback=callback,
                is_active=True,
            )
            self._watches[entry.watch_id] = entry
            self._path_to_watch[path] = entry.watch_id
            return entry

    def unwatch(self, watch_id: str) -> bool:
        """Remove a watch from the system.

        Args:
            watch_id: Identifier of the watch to remove.

        Returns:
            True if the watch was removed, False if not found.
        """
        with self._instance_lock:
            entry = self._watches.pop(watch_id, None)
            if entry is None:
                return False
            if self._path_to_watch.get(entry.path) == watch_id:
                self._path_to_watch.pop(entry.path, None)
            return True

    # ------------------------------------------------------------------
    # Reload Operations
    # ------------------------------------------------------------------

    def reload(self, path: str) -> ReloadEvent:
        """Perform an explicit reload of a single path.

        Dispatches the registered callback (if any) for the path and
        records the outcome in the reload history.

        Args:
            path: Filesystem path or logical identifier to reload.

        Returns:
            The ReloadEvent describing the outcome.
        """
        with self._instance_lock:
            watch_id = self._path_to_watch.get(path)
            entry = self._watches.get(watch_id) if watch_id else None
            reload_type = entry.reload_type if entry is not None else ReloadType.RESOURCE
            callback = entry.callback if entry is not None else None

            start = time.perf_counter()
            success = True
            error_message: Optional[str] = None

            try:
                if callback is not None:
                    # Build the event first so the callback receives it.
                    event = ReloadEvent(
                        reload_type=reload_type,
                        file_path=path,
                        success=True,
                    )
                    callback(event)
            except Exception as exc:
                success = False
                error_message = str(exc)

            duration_ms = (time.perf_counter() - start) * 1000.0
            event = ReloadEvent(
                reload_type=reload_type,
                file_path=path,
                success=success,
                error_message=error_message,
                duration_ms=round(duration_ms, 3),
            )
            self._record_event(event)
            return event

    def reload_all(self, reload_type: ReloadType) -> List[ReloadEvent]:
        """Reload every active watch matching the given reload type.

        When ``reload_type`` is :attr:`ReloadType.ALL`, every active watch
        is reloaded regardless of its category.

        Args:
            reload_type: Category filter for the watches to reload.

        Returns:
            A list of ReloadEvent records, one per reloaded watch.
        """
        with self._instance_lock:
            paths: List[str] = []
            for entry in self._watches.values():
                if not entry.is_active:
                    continue
                if reload_type == ReloadType.ALL or entry.reload_type == reload_type:
                    paths.append(entry.path)
            return [self.reload(path) for path in paths]

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_watched(self) -> List[WatchEntry]:
        """Return a copy of all registered watches."""
        with self._instance_lock:
            return list(self._watches.values())

    def get_reload_history(self) -> List[ReloadEvent]:
        """Return a copy of the reload event history."""
        with self._instance_lock:
            return list(self._history)

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._instance_lock:
            active = sum(1 for w in self._watches.values() if w.is_active)
            type_counts: Dict[str, int] = {}
            for w in self._watches.values():
                key = w.reload_type.value
                type_counts[key] = type_counts.get(key, 0) + 1
            return {
                "total_watches": len(self._watches),
                "active_watches": active,
                "total_reloads": self._total_reloads,
                "successful_reloads": self._successful_reloads,
                "failed_reloads": self._failed_reloads,
                "history_size": len(self._history),
                "watches_by_type": type_counts,
            }

    def get_snapshot(self) -> HotReloadSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            active = sum(1 for w in self._watches.values() if w.is_active)
            return HotReloadSnapshot(
                total_watches=len(self._watches),
                active_watches=active,
                total_events=len(self._history),
                successful_reloads=self._successful_reloads,
                failed_reloads=self._failed_reloads,
                watches=[w.to_dict() for w in self._watches.values()],
                captured_at=time.time(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all watches, history, and counters."""
        with self._instance_lock:
            self._watches.clear()
            self._path_to_watch.clear()
            self._history.clear()
            self._total_reloads = 0
            self._successful_reloads = 0
            self._failed_reloads = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record_event(self, event: ReloadEvent) -> None:
        """Append an event to the bounded history and update counters."""
        self._history.append(event)
        if len(self._history) > self.MAX_HISTORY:
            self._history = self._history[-self.MAX_HISTORY:]
        self._total_reloads += 1
        if event.success:
            self._successful_reloads += 1
        else:
            self._failed_reloads += 1


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_hot_reload_system() -> HotReloadSystem:
    """Return the singleton HotReloadSystem instance."""
    return HotReloadSystem.get_instance()
