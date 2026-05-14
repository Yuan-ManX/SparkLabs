"""
SparkLabs Engine - Hot Reload System

Live code and asset hot-reloading subsystem for the SparkLabs
AI-native game engine. Monitors source files for changes during
development, applies reloads with dependency-aware ordering, and
preserves runtime state across reload boundaries. Supports
graceful rollback on reload failure.

Architecture:
  HotReloadSystem
    |-- FileWatcher (filesystem change detection via polling)
    |-- DependencyGraph (topological sort for reload ordering)
    |-- StatePreserver (snapshot capture and restoration)
    |-- RecoveryManager (failure rollback with old-state restore)
    |-- EventHistory (reload event log for auditing)

Reload Target Types:
  - SCRIPT: game logic source files
  - SHADER: vertex/fragment shader programs
  - TEXTURE: sprite sheets and image assets
  - AUDIO: sound effects and music tracks
  - SCENE: scene definition files
  - CONFIG: JSON/YAML configuration data
  - UI_LAYOUT: interface layout definitions
  - PREFAB: object template definitions

Lifecycle:
  1. register_asset()  -- declare a reloadable asset with dependencies
  2. watch_file()      -- begin filesystem monitoring
  3. detect_changes()  -- poll for modified files
  4. queue_reload()    -- enqueue changed assets for deferred processing
  5. reload_now()      -- execute immediate reload with state preservation
  6. rollback_reload() -- restore previous state on failure

Usage:
    hrs = HotReloadSystem()
    hrs.register_asset("scripts/player.lua", ReloadTargetType.SCRIPT)
    hrs.watch_file("scripts/")
    changes = hrs.detect_changes()
    for asset in changes:
        event = hrs.reload_now(asset.asset_id)
        if event.status == ReloadStatus.FAILED:
            hrs.rollback_reload(event.event_id)
"""
from __future__ import annotations

import hashlib
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ReloadTargetType(Enum):
    SCRIPT = auto()
    SHADER = auto()
    TEXTURE = auto()
    AUDIO = auto()
    SCENE = auto()
    CONFIG = auto()
    UI_LAYOUT = auto()
    PREFAB = auto()


class ReloadStatus(Enum):
    IDLE = auto()
    DETECTED = auto()
    QUEUED = auto()
    RELOADING = auto()
    COMPLETED = auto()
    FAILED = auto()
    ROLLED_BACK = auto()


class ReloadStrategy(Enum):
    IMMEDIATE = auto()
    DEFERRED = auto()
    BATCHED = auto()
    MANUAL = auto()


@dataclass
class ReloadableAsset:
    asset_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    file_path: str = ""
    target_type: ReloadTargetType = ReloadTargetType.SCRIPT
    dependencies: List[str] = field(default_factory=list)
    checksum: str = ""
    last_reloaded: float = 0.0
    reload_count: int = 0

    def compute_checksum(self) -> str:
        if os.path.exists(self.file_path):
            with open(self.file_path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        return ""

    def has_changed(self) -> bool:
        if not self.checksum:
            return os.path.exists(self.file_path)
        return self.compute_checksum() != self.checksum

    def update_checksum(self) -> None:
        self.checksum = self.compute_checksum()

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "file_path": self.file_path,
            "target_type": self.target_type.name,
            "dependencies": self.dependencies,
            "checksum": self.checksum[:8] if self.checksum else "",
            "last_reloaded": self.last_reloaded,
            "reload_count": self.reload_count,
        }


@dataclass
class ReloadEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    asset_id: str = ""
    target_type: ReloadTargetType = ReloadTargetType.SCRIPT
    status: ReloadStatus = ReloadStatus.IDLE
    strategy: ReloadStrategy = ReloadStrategy.DEFERRED
    duration_ms: float = 0.0
    old_state_snapshot: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "asset_id": self.asset_id,
            "target_type": self.target_type.name,
            "status": self.status.name,
            "strategy": self.strategy.name,
            "duration_ms": round(self.duration_ms, 2),
            "has_snapshot": self.old_state_snapshot is not None,
            "error": self.error_message,
            "timestamp": self.timestamp,
        }


class DependencyGraph:
    def __init__(self):
        self._forward: Dict[str, Set[str]] = defaultdict(set)
        self._reverse: Dict[str, Set[str]] = defaultdict(set)

    def add_edge(self, from_id: str, to_id: str) -> None:
        self._forward[from_id].add(to_id)
        self._reverse[to_id].add(from_id)

    def remove_node(self, node_id: str) -> None:
        for dep in self._forward.pop(node_id, set()):
            self._reverse[dep].discard(node_id)
        for parent in self._reverse.pop(node_id, set()):
            self._forward[parent].discard(node_id)

    def get_dependents(self, node_id: str) -> Set[str]:
        return self._forward.get(node_id, set())

    def get_dependencies(self, node_id: str) -> Set[str]:
        return self._reverse.get(node_id, set())

    def topological_sort(self, node_ids: Set[str]) -> List[str]:
        in_degree: Dict[str, int] = {}
        adjacency: Dict[str, List[str]] = {}

        for nid in node_ids:
            in_degree[nid] = 0
            adjacency[nid] = []

        for nid in node_ids:
            for dep in self._reverse.get(nid, set()):
                if dep in node_ids:
                    adjacency.setdefault(dep, []).append(nid)
                    in_degree[nid] = in_degree.get(nid, 0) + 1

        queue: deque[str] = deque()
        for nid in node_ids:
            if in_degree.get(nid, 0) == 0:
                queue.append(nid)

        result: List[str] = []
        while queue:
            current = queue.popleft()
            result.append(current)
            for neighbor in adjacency.get(current, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(result) != len(node_ids):
            remaining = node_ids - set(result)
            result.extend(remaining)

        return result


class FileWatcher:
    def __init__(self):
        self._watched_paths: Set[str] = set()
        self._file_mtimes: Dict[str, float] = {}
        self._file_sizes: Dict[str, int] = {}

    def add_path(self, path: str) -> None:
        self._watched_paths.add(os.path.abspath(path))

    def remove_path(self, path: str) -> None:
        self._watched_paths.discard(os.path.abspath(path))

    def scan(self) -> Dict[str, float]:
        results: Dict[str, float] = {}
        for watched in self._watched_paths:
            self._scan_directory(watched, results)
        return results

    def detect_changes(self) -> List[str]:
        changed: List[str] = []
        current_state = self.scan()
        for file_path, mtime in current_state.items():
            prev_mtime = self._file_mtimes.get(file_path)
            if prev_mtime is None or mtime > prev_mtime:
                changed.append(file_path)
        for file_path in self._file_mtimes:
            if file_path not in current_state:
                changed.append(file_path)
        self._file_mtimes = current_state
        return changed

    def _scan_directory(self, directory: str, results: Dict[str, float]) -> None:
        if not os.path.isdir(directory):
            if os.path.isfile(directory):
                try:
                    stat = os.stat(directory)
                    results[directory] = stat.st_mtime
                except OSError:
                    pass
            return

        try:
            for entry in os.scandir(directory):
                if entry.is_file():
                    try:
                        stat = entry.stat()
                        results[entry.path] = stat.st_mtime
                    except OSError:
                        pass
                elif entry.is_dir():
                    if not entry.name.startswith(".") and entry.name != "__pycache__":
                        self._scan_directory(entry.path, results)
        except PermissionError:
            pass


class StatePreserver:
    def __init__(self):
        self._snapshots: Dict[str, Dict[str, Any]] = {}
        self._capture_handlers: Dict[ReloadTargetType, Callable[[str], Dict[str, Any]]] = {}
        self._restore_handlers: Dict[ReloadTargetType, Callable[[str, Dict[str, Any]], bool]] = {}

    def register_capture_handler(
        self, target_type: ReloadTargetType, handler: Callable[[str], Dict[str, Any]]
    ) -> None:
        self._capture_handlers[target_type] = handler

    def register_restore_handler(
        self, target_type: ReloadTargetType, handler: Callable[[str, Dict[str, Any]], bool]
    ) -> None:
        self._restore_handlers[target_type] = handler

    def capture(self, asset_id: str, file_path: str, target_type: ReloadTargetType) -> Dict[str, Any]:
        handler = self._capture_handlers.get(target_type)
        if handler:
            snapshot = handler(file_path)
        else:
            snapshot = {"file_path": file_path, "target_type": target_type.name}

        self._snapshots[asset_id] = snapshot
        return snapshot

    def restore(self, asset_id: str, file_path: str, target_type: ReloadTargetType) -> bool:
        snapshot = self._snapshots.get(asset_id)
        if snapshot is None:
            return False

        handler = self._restore_handlers.get(target_type)
        if handler:
            return handler(file_path, snapshot)
        return True

    def get_snapshot(self, asset_id: str) -> Optional[Dict[str, Any]]:
        return self._snapshots.get(asset_id)

    def discard_snapshot(self, asset_id: str) -> None:
        self._snapshots.pop(asset_id, None)

    def clear(self) -> None:
        self._snapshots.clear()


class HotReloadSystem:
    """
    Hot-reload engine for live development iteration.

    Monitors file changes, preserves runtime state during reloads,
    and applies dependency-ordered updates. Provides automatic
    rollback when a reload fails so the game never enters an
    inconsistent state.

    Usage:
        hrs = HotReloadSystem()
        asset = hrs.register_asset("scripts/ai.lua", ReloadTargetType.SCRIPT,
                                    dependencies=["scripts/utils.lua"])
        hrs.watch_file("scripts/")
        changes = hrs.detect_changes()
        for ch in changes:
            print(f"Changed: {ch.file_path}")
        event = hrs.reload_now(asset.asset_id)
        if event.status == ReloadStatus.FAILED:
            hrs.rollback_reload(event.event_id)
    """

    _instance: Optional["HotReloadSystem"] = None

    def __init__(self):
        self._assets: Dict[str, ReloadableAsset] = {}
        self._events: Dict[str, ReloadEvent] = {}
        self._by_path: Dict[str, str] = {}
        self._dependency_graph = DependencyGraph()
        self._file_watcher = FileWatcher()
        self._state_preserver = StatePreserver()
        self._reload_queue: List[str] = []
        self._total_reloads: int = 0
        self._successful_reloads: int = 0
        self._total_reload_ms: float = 0.0
        self._active: bool = True

    @classmethod
    def get_instance(cls) -> "HotReloadSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register_asset(
        self,
        file_path: str,
        target_type: ReloadTargetType,
        dependencies: Optional[List[str]] = None,
    ) -> ReloadableAsset:
        abs_path = os.path.abspath(file_path)
        existing_id = self._by_path.get(abs_path)
        if existing_id and existing_id in self._assets:
            return self._assets[existing_id]

        asset = ReloadableAsset(
            file_path=abs_path,
            target_type=target_type,
            dependencies=list(dependencies or []),
        )
        asset.update_checksum()

        self._assets[asset.asset_id] = asset
        self._by_path[abs_path] = asset.asset_id

        for dep_path in asset.dependencies:
            dep_abs = os.path.abspath(dep_path)
            if dep_abs in self._by_path:
                self._dependency_graph.add_edge(asset.asset_id, self._by_path[dep_abs])

        return asset

    def unregister_asset(self, asset_id: str) -> bool:
        asset = self._assets.pop(asset_id, None)
        if not asset:
            return False
        self._by_path.pop(asset.file_path, None)
        self._dependency_graph.remove_node(asset_id)
        return True

    def get_asset(self, asset_id: str) -> Optional[ReloadableAsset]:
        return self._assets.get(asset_id)

    def find_asset_by_path(self, file_path: str) -> Optional[ReloadableAsset]:
        asset_id = self._by_path.get(os.path.abspath(file_path))
        if asset_id:
            return self._assets.get(asset_id)
        return None

    def watch_file(self, file_path: str) -> None:
        self._file_watcher.add_path(os.path.abspath(file_path))

    def unwatch_file(self, file_path: str) -> None:
        self._file_watcher.remove_path(os.path.abspath(file_path))

    def detect_changes(self) -> List[ReloadableAsset]:
        if not self._active:
            return []

        changed_paths = self._file_watcher.detect_changes()
        changed_assets: List[ReloadableAsset] = []

        for path in changed_paths:
            asset_id = self._by_path.get(path)
            if asset_id:
                asset = self._assets.get(asset_id)
                if asset and asset.has_changed():
                    if asset.status_internal is None:
                        asset.status_internal = ReloadStatus.DETECTED
                    changed_assets.append(asset)

            elif not path.startswith("."):
                asset = ReloadableAsset(
                    file_path=path,
                    target_type=self._infer_target_type(path),
                )
                asset.update_checksum()
                asset.status_internal = ReloadStatus.DETECTED
                self._assets[asset.asset_id] = asset
                self._by_path[path] = asset.asset_id
                changed_assets.append(asset)

        return changed_assets

    def queue_reload(
        self, asset_id: str, strategy: ReloadStrategy = ReloadStrategy.DEFERRED,
    ) -> Optional[ReloadEvent]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        if not hasattr(asset, "status_internal"):
            asset.status_internal = ReloadStatus.IDLE
        asset.status_internal = ReloadStatus.QUEUED

        event = ReloadEvent(
            asset_id=asset_id,
            target_type=asset.target_type,
            status=ReloadStatus.QUEUED,
            strategy=strategy,
        )
        self._events[event.event_id] = event
        self._reload_queue.append(event.event_id)
        return event

    def reload_now(self, asset_id: str) -> Optional[ReloadEvent]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None

        if not self._active:
            event = ReloadEvent(
                asset_id=asset_id,
                target_type=asset.target_type,
                status=ReloadStatus.FAILED,
                error_message="Hot reload system is deactivated",
            )
            self._events[event.event_id] = event
            return event

        old_snapshot = self._state_preserver.capture(
            asset_id, asset.file_path, asset.target_type,
        )

        event = ReloadEvent(
            asset_id=asset_id,
            target_type=asset.target_type,
            status=ReloadStatus.RELOADING,
            strategy=ReloadStrategy.IMMEDIATE,
            old_state_snapshot=old_snapshot,
        )

        start = time.monotonic()

        try:
            self._perform_reload(asset)

            event.status = ReloadStatus.COMPLETED
            event.duration_ms = (time.monotonic() - start) * 1000.0

            self._total_reloads += 1
            self._successful_reloads += 1
            self._total_reload_ms += event.duration_ms

            asset.last_reloaded = time.time()
            asset.reload_count += 1
            asset.update_checksum()

            self._state_preserver.discard_snapshot(asset_id)
        except Exception as exc:
            event.status = ReloadStatus.FAILED
            event.duration_ms = (time.monotonic() - start) * 1000.0
            event.error_message = str(exc)

            self._total_reloads += 1
            self._total_reload_ms += event.duration_ms

        if not hasattr(asset, "status_internal"):
            asset.status_internal = ReloadStatus.IDLE
        asset.status_internal = event.status

        self._events[event.event_id] = event
        return event

    def batch_reload(self, asset_ids: List[str]) -> List[ReloadEvent]:
        if not self._active:
            return []

        ordered = self.get_reload_order(asset_ids)
        events: List[ReloadEvent] = []

        for batch_asset_id in ordered:
            event = self.reload_now(batch_asset_id)
            if event is not None:
                events.append(event)
            if event and event.status == ReloadStatus.FAILED:
                rolled = self.rollback_reload(event.event_id)
                if rolled:
                    events.append(rolled)
                break

        return events

    def rollback_reload(self, event_id: str) -> Optional[ReloadEvent]:
        original_event = self._events.get(event_id)
        if original_event is None:
            return None

        asset = self._assets.get(original_event.asset_id)
        if not asset:
            return None

        if original_event.old_state_snapshot is None:
            rollback_event = ReloadEvent(
                asset_id=original_event.asset_id,
                target_type=original_event.target_type,
                status=ReloadStatus.FAILED,
                error_message="No snapshot available for rollback",
            )
            self._events[rollback_event.event_id] = rollback_event
            return rollback_event

        rollback_event = ReloadEvent(
            asset_id=original_event.asset_id,
            target_type=original_event.target_type,
            status=ReloadStatus.RELOADING,
            strategy=ReloadStrategy.IMMEDIATE,
        )

        start = time.monotonic()

        try:
            restored = self._state_preserver.restore(
                original_event.asset_id, asset.file_path, original_event.target_type,
            )
            if restored:
                rollback_event.status = ReloadStatus.ROLLED_BACK
            else:
                rollback_event.status = ReloadStatus.FAILED
                rollback_event.error_message = "State restore handler returned False"
        except Exception as exc:
            rollback_event.status = ReloadStatus.FAILED
            rollback_event.error_message = f"Rollback failed: {exc}"

        rollback_event.duration_ms = (time.monotonic() - start) * 1000.0

        if not hasattr(asset, "status_internal"):
            asset.status_internal = ReloadStatus.IDLE
        asset.status_internal = rollback_event.status

        self._events[rollback_event.event_id] = rollback_event
        return rollback_event

    def get_reload_order(self, asset_ids: List[str]) -> List[str]:
        valid_ids = {aid for aid in asset_ids if aid in self._assets}
        return self._dependency_graph.topological_sort(valid_ids)

    def preserve_state(self, asset_id: str) -> Optional[Dict[str, Any]]:
        asset = self._assets.get(asset_id)
        if not asset:
            return None
        return self._state_preserver.capture(
            asset_id, asset.file_path, asset.target_type,
        )

    def register_capture_handler(
        self, target_type: ReloadTargetType, handler: Callable[[str], Dict[str, Any]]
    ) -> None:
        self._state_preserver.register_capture_handler(target_type, handler)

    def register_restore_handler(
        self, target_type: ReloadTargetType, handler: Callable[[str, Dict[str, Any]], bool]
    ) -> None:
        self._state_preserver.register_restore_handler(target_type, handler)

    def get_event(self, event_id: str) -> Optional[ReloadEvent]:
        return self._events.get(event_id)

    def list_events(
        self,
        asset_id: Optional[str] = None,
        status_filter: Optional[ReloadStatus] = None,
    ) -> List[ReloadEvent]:
        results = list(self._events.values())
        if asset_id:
            results = [e for e in results if e.asset_id == asset_id]
        if status_filter:
            results = [e for e in results if e.status == status_filter]
        return sorted(results, key=lambda e: e.timestamp, reverse=True)

    def list_assets(
        self, target_type: Optional[ReloadTargetType] = None,
    ) -> List[ReloadableAsset]:
        if target_type:
            return [a for a in self._assets.values() if a.target_type == target_type]
        return list(self._assets.values())

    def get_stats(self) -> dict:
        total = self._total_reloads
        success_rate = round(
            (self._successful_reloads / max(total, 1)) * 100, 1
        )
        average_reload_ms = round(
            self._total_reload_ms / max(total, 1), 2
        )
        type_breakdown: Dict[str, int] = {}
        for asset in self._assets.values():
            tname = asset.target_type.name
            type_breakdown[tname] = type_breakdown.get(tname, 0) + 1

        return {
            "total_assets": len(self._assets),
            "total_reloads": total,
            "success_rate": success_rate,
            "average_reload_ms": average_reload_ms,
            "successful_reloads": self._successful_reloads,
            "queued_count": len(self._reload_queue),
            "event_count": len(self._events),
            "watched_paths": len(self._file_watcher._watched_paths),
            "type_breakdown": type_breakdown,
            "active": self._active,
        }

    def set_active(self, active: bool) -> None:
        self._active = active

    def clear_history(self) -> None:
        self._events.clear()
        self._total_reloads = 0
        self._successful_reloads = 0
        self._total_reload_ms = 0.0
        self._reload_queue.clear()

    def reset(self) -> None:
        self._assets.clear()
        self._events.clear()
        self._by_path.clear()
        self._dependency_graph = DependencyGraph()
        self._file_watcher = FileWatcher()
        self._state_preserver.clear()
        self._reload_queue.clear()
        self._total_reloads = 0
        self._successful_reloads = 0
        self._total_reload_ms = 0.0
        self._active = True

    def _perform_reload(self, asset: ReloadableAsset) -> None:
        asset.update_checksum()

    @staticmethod
    def _infer_target_type(file_path: str) -> ReloadTargetType:
        ext = os.path.splitext(file_path)[1].lower()
        if ext in (".lua", ".py", ".js", ".ts", ".cs", ".gd"):
            return ReloadTargetType.SCRIPT
        if ext in (".glsl", ".hlsl", ".shader", ".cg", ".vert", ".frag"):
            return ReloadTargetType.SHADER
        if ext in (".png", ".jpg", ".jpeg", ".bmp", ".tga", ".dds", ".ktx"):
            return ReloadTargetType.TEXTURE
        if ext in (".wav", ".mp3", ".ogg", ".flac", ".aiff", ".mod"):
            return ReloadTargetType.AUDIO
        if ext in (".scene", ".unity", ".tscn", ".level"):
            return ReloadTargetType.SCENE
        if ext in (".json", ".yaml", ".yml", ".toml", ".ini", ".cfg"):
            return ReloadTargetType.CONFIG
        if ext in (".ui", ".xml", ".rml", ".layout"):
            return ReloadTargetType.UI_LAYOUT
        if ext in (".prefab", ".template", ".entity"):
            return ReloadTargetType.PREFAB
        return ReloadTargetType.SCRIPT


def get_hot_reload_system() -> HotReloadSystem:
    return HotReloadSystem.get_instance()