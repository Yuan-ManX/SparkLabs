"""
SparkLabs Agent - Process Registry

Background process lifecycle management for game development workflows.
Tracks long-running processes: build servers, game previews, asset
compilation, dev servers. Adapted for game engine orchestration where
AI agents need to spawn, monitor, and control multi-process pipelines.

Architecture:
  ProcessRegistry
    |-- ProcessEntry (pid, command, status, resource usage)
    |-- ProcessPool (grouped processes per game project)
    |-- ResourceMonitor (CPU/memory tracking per process)
    |-- LifecycleHooks (on_start, on_exit, on_crash callbacks)
    |-- TimeoutManager (auto-kill hung processes)

Process States:
  - SPAWNING: process is being created
  - RUNNING: executing normally
  - IDLE: process alive but no activity
  - STALLED: no output for threshold period
  - STOPPING: termination requested
  - STOPPED: clean exit
  - CRASHED: non-zero exit or signal
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ProcessState(Enum):
    SPAWNING = "spawning"
    RUNNING = "running"
    IDLE = "idle"
    STALLED = "stalled"
    STOPPING = "stopping"
    STOPPED = "stopped"
    CRASHED = "crashed"


class ProcessType(Enum):
    BUILD = "build"
    PREVIEW = "preview"
    COMPILATION = "compilation"
    SERVER = "server"
    WATCHER = "watcher"
    TEST = "test"
    EXPORT = "export"
    CUSTOM = "custom"


@dataclass
class ProcessEntry:
    process_id: str
    name: str
    command: str
    process_type: ProcessType = ProcessType.CUSTOM
    pid: Optional[int] = None
    state: ProcessState = ProcessState.SPAWNING
    started_at: float = field(default_factory=time.time)
    stopped_at: Optional[float] = None
    exit_code: Optional[int] = None
    last_output: str = ""
    last_active_at: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "process_id": self.process_id,
            "name": self.name,
            "command": self.command,
            "process_type": self.process_type.value,
            "pid": self.pid,
            "state": self.state.value,
            "started_at": self.started_at,
            "stopped_at": self.stopped_at,
            "exit_code": self.exit_code,
            "last_output": self.last_output[:200],
            "cpu_percent": self.cpu_percent,
            "memory_mb": self.memory_mb,
            "tags": self.tags,
        }


@dataclass
class ProcessPool:
    pool_id: str
    project_id: str
    name: str
    processes: Dict[str, ProcessEntry] = field(default_factory=dict)
    max_concurrent: int = 4

    def active_count(self) -> int:
        return sum(
            1 for p in self.processes.values()
            if p.state in (ProcessState.RUNNING, ProcessState.SPAWNING)
        )

    def can_spawn(self) -> bool:
        return self.active_count() < self.max_concurrent


class ProcessRegistry:
    """
    Central registry for background process lifecycle management.

    Game development involves multiple long-running processes:
    build systems, preview servers, asset watchers, test runners.
    This registry provides the AI agent with unified process
    observability and control.
    """

    _instance: Optional["ProcessRegistry"] = None

    def __init__(self):
        self._processes: Dict[str, ProcessEntry] = {}
        self._pools: Dict[str, ProcessPool] = {}
        self._hooks: Dict[str, List[Callable]] = {
            "on_start": [],
            "on_exit": [],
            "on_crash": [],
            "on_stall": [],
        }
        self._stall_threshold: float = 300.0
        self._lock = threading.Lock()
        self._next_id: int = 0
        self._MAX_PROCESSES = 100

    @classmethod
    def get_instance(cls) -> "ProcessRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        command: str,
        process_type: ProcessType = ProcessType.CUSTOM,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessEntry:
        with self._lock:
            self._next_id += 1
            process_id = f"proc-{self._next_id:04d}"
            entry = ProcessEntry(
                process_id=process_id,
                name=name,
                command=command,
                process_type=process_type,
                tags=tags or [],
                metadata=metadata or {},
            )
            self._processes[process_id] = entry
            if len(self._processes) > self._MAX_PROCESSES:
                oldest = min(
                    self._processes.keys(),
                    key=lambda k: self._processes[k].started_at,
                )
                del self._processes[oldest]
            self._fire_hook("on_start", entry)
            return entry

    def update_state(
        self, process_id: str, state: ProcessState, **kwargs
    ) -> Optional[ProcessEntry]:
        with self._lock:
            entry = self._processes.get(process_id)
            if not entry:
                return None
            entry.state = state
            entry.last_active_at = time.time()
            if state == ProcessState.STOPPED:
                entry.stopped_at = time.time()
                self._fire_hook("on_exit", entry)
            elif state == ProcessState.CRASHED:
                entry.stopped_at = time.time()
                self._fire_hook("on_crash", entry)
            for key, value in kwargs.items():
                if hasattr(entry, key):
                    setattr(entry, key, value)
            return entry

    def set_output(self, process_id: str, output: str) -> None:
        with self._lock:
            entry = self._processes.get(process_id)
            if entry:
                entry.last_output = output[-500:]
                entry.last_active_at = time.time()

    def set_resources(
        self, process_id: str, cpu_percent: float, memory_mb: float
    ) -> None:
        with self._lock:
            entry = self._processes.get(process_id)
            if entry:
                entry.cpu_percent = cpu_percent
                entry.memory_mb = memory_mb

    def get(self, process_id: str) -> Optional[ProcessEntry]:
        return self._processes.get(process_id)

    def find_by_tag(self, tag: str) -> List[ProcessEntry]:
        return [p for p in self._processes.values() if tag in p.tags]

    def find_by_type(self, process_type: ProcessType) -> List[ProcessEntry]:
        return [p for p in self._processes.values() if p.process_type == process_type]

    def list_all(self) -> List[ProcessEntry]:
        return list(self._processes.values())

    def list_active(self) -> List[ProcessEntry]:
        return [
            p
            for p in self._processes.values()
            if p.state in (ProcessState.RUNNING, ProcessState.SPAWNING)
        ]

    def create_pool(
        self, project_id: str, name: str, max_concurrent: int = 4
    ) -> ProcessPool:
        with self._lock:
            pool_id = f"pool-{project_id}"
            pool = ProcessPool(
                pool_id=pool_id,
                project_id=project_id,
                name=name,
                max_concurrent=max_concurrent,
            )
            self._pools[pool_id] = pool
            return pool

    def add_to_pool(self, pool_id: str, process_id: str) -> bool:
        with self._lock:
            pool = self._pools.get(pool_id)
            entry = self._processes.get(process_id)
            if not pool or not entry:
                return False
            pool.processes[process_id] = entry
            return True

    def get_pool(self, pool_id: str) -> Optional[ProcessPool]:
        return self._pools.get(pool_id)

    def check_stalls(self) -> List[ProcessEntry]:
        stalled = []
        now = time.time()
        with self._lock:
            for entry in self._processes.values():
                if entry.state == ProcessState.RUNNING:
                    idle_time = now - entry.last_active_at
                    if idle_time > self._stall_threshold:
                        entry.state = ProcessState.STALLED
                        self._fire_hook("on_stall", entry)
                        stalled.append(entry)
        return stalled

    def kill(self, process_id: str) -> bool:
        with self._lock:
            entry = self._processes.get(process_id)
            if not entry:
                return False
            entry.state = ProcessState.STOPPING
            return True

    def kill_all(self, process_type: Optional[ProcessType] = None) -> int:
        count = 0
        with self._lock:
            for entry in list(self._processes.values()):
                if process_type and entry.process_type != process_type:
                    continue
                if entry.state in (ProcessState.RUNNING, ProcessState.SPAWNING):
                    entry.state = ProcessState.STOPPING
                    count += 1
        return count

    def on(self, event: str, callback: Callable) -> None:
        if event in self._hooks:
            self._hooks[event].append(callback)

    def _fire_hook(self, event: str, entry: ProcessEntry) -> None:
        for callback in self._hooks.get(event, []):
            try:
                callback(entry)
            except Exception:
                pass

    def set_stall_threshold(self, seconds: float) -> None:
        self._stall_threshold = max(30.0, seconds)

    def get_stats(self) -> dict:
        with self._lock:
            active = self.list_active()
            by_type = {}
            for entry in self._processes.values():
                t = entry.process_type.value
                by_type[t] = by_type.get(t, 0) + 1
            return {
                "total_registered": len(self._processes),
                "active": len(active),
                "by_type": by_type,
                "pools": len(self._pools),
                "stall_threshold": self._stall_threshold,
            }

    def reset(self) -> None:
        with self._lock:
            self._processes.clear()
            self._pools.clear()
            self._hooks = {k: [] for k in self._hooks}
            self._next_id = 0


def get_process_registry() -> ProcessRegistry:
    return ProcessRegistry.get_instance()
