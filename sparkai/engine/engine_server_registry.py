"""
SparkLabs Engine - Server Registry

Central registry that manages all engine subsystems as independent
servers. Each server represents a core engine subsystem (rendering,
physics, audio, etc.) that can be started, stopped, paused, resumed,
and monitored independently. Inspired by the server architecture
pattern used in Godot Engine.

Architecture:
  ServerRegistry (Singleton)
    |-- ServerConfig (per-server configuration presets)
    |-- ServerInfo (runtime state and statistics per server)
    |-- ServerType / ServerStatus / ServerPriority (enums)

Registry Features:
  - REGISTER: add engine subsystem servers with configuration
  - LIFECYCLE: start, stop, pause, resume individual or all servers
  - MONITOR: per-server runtime statistics and error tracking
  - TICK: simulate per-frame processing for each server
  - SHUTDOWN: clean teardown of all registered servers
  - STATUS: aggregate registry-wide health overview
"""

from __future__ import annotations

import random
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enums
# ---------------------------------------------------------------------------


class ServerType(Enum):
    """Categories of engine subsystem servers."""
    RENDERING = "rendering"
    PHYSICS = "physics"
    AUDIO = "audio"
    INPUT = "input"
    SCRIPTING = "scripting"
    NETWORKING = "networking"
    AI = "ai"
    UI = "ui"
    SCENE = "scene"
    ASSET = "asset"
    PARTICLE = "particle"
    ANIMATION = "animation"
    SPATIAL = "spatial"
    PATHFINDING = "pathfinding"


class ServerStatus(Enum):
    """Runtime lifecycle states for a registered server."""
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    ERROR = "error"


class ServerPriority(Enum):
    """Startup and resource allocation priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ServerConfig:
    """Configuration preset for a registered engine subsystem server."""

    server_type: ServerType = ServerType.SCENE
    priority: ServerPriority = ServerPriority.NORMAL
    auto_start: bool = True
    thread_affinity: int = 0
    max_fps: int = 60
    memory_limit_mb: int = 256
    config: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_type": self.server_type.value,
            "priority": self.priority.value,
            "auto_start": self.auto_start,
            "thread_affinity": self.thread_affinity,
            "max_fps": self.max_fps,
            "memory_limit_mb": self.memory_limit_mb,
            "config": dict(self.config),
        }


@dataclass
class ServerInfo:
    """Runtime state and performance statistics for a registered server."""

    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    server_type: ServerType = ServerType.SCENE
    status: ServerStatus = ServerStatus.STOPPED
    priority: ServerPriority = ServerPriority.NORMAL
    uptime_seconds: float = 0.0
    frame_count: int = 0
    error_count: int = 0
    last_error: Optional[str] = None
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "server_type": self.server_type.value,
            "status": self.status.value,
            "priority": self.priority.value,
            "uptime_seconds": round(self.uptime_seconds, 4),
            "frame_count": self.frame_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_usage": round(self.memory_usage, 2),
            "metadata": dict(self.metadata),
        }


# ---------------------------------------------------------------------------
# Predefined Default Server Configurations
# ---------------------------------------------------------------------------

_DEFAULT_CONFIGS: Dict[ServerType, Dict[str, Any]] = {
    ServerType.RENDERING:   {"priority": ServerPriority.CRITICAL,   "auto_start": True,  "thread_affinity": 0, "max_fps": 144, "memory_limit_mb": 2048},
    ServerType.PHYSICS:     {"priority": ServerPriority.CRITICAL,   "auto_start": True,  "thread_affinity": 1, "max_fps": 60,  "memory_limit_mb": 512},
    ServerType.AUDIO:       {"priority": ServerPriority.HIGH,       "auto_start": True,  "thread_affinity": 2, "max_fps": 60,  "memory_limit_mb": 256},
    ServerType.INPUT:       {"priority": ServerPriority.CRITICAL,   "auto_start": True,  "thread_affinity": 0, "max_fps": 240, "memory_limit_mb": 64},
    ServerType.SCRIPTING:   {"priority": ServerPriority.HIGH,       "auto_start": True,  "thread_affinity": 3, "max_fps": 60,  "memory_limit_mb": 512},
    ServerType.NETWORKING:  {"priority": ServerPriority.NORMAL,     "auto_start": False, "thread_affinity": 4, "max_fps": 30,  "memory_limit_mb": 256},
    ServerType.AI:          {"priority": ServerPriority.NORMAL,     "auto_start": True,  "thread_affinity": 5, "max_fps": 30,  "memory_limit_mb": 512},
    ServerType.UI:          {"priority": ServerPriority.HIGH,       "auto_start": True,  "thread_affinity": 0, "max_fps": 60,  "memory_limit_mb": 128},
    ServerType.SCENE:       {"priority": ServerPriority.CRITICAL,   "auto_start": True,  "thread_affinity": 0, "max_fps": 60,  "memory_limit_mb": 1024},
    ServerType.ASSET:       {"priority": ServerPriority.NORMAL,     "auto_start": True,  "thread_affinity": 6, "max_fps": 30,  "memory_limit_mb": 1024},
    ServerType.PARTICLE:    {"priority": ServerPriority.LOW,        "auto_start": True,  "thread_affinity": 7, "max_fps": 60,  "memory_limit_mb": 128},
    ServerType.ANIMATION:   {"priority": ServerPriority.NORMAL,     "auto_start": True,  "thread_affinity": 3, "max_fps": 60,  "memory_limit_mb": 256},
    ServerType.SPATIAL:     {"priority": ServerPriority.NORMAL,     "auto_start": True,  "thread_affinity": 1, "max_fps": 30,  "memory_limit_mb": 512},
    ServerType.PATHFINDING: {"priority": ServerPriority.LOW,        "auto_start": True,  "thread_affinity": 5, "max_fps": 15,  "memory_limit_mb": 256},
}

_SERVER_DEPENDENCIES: Dict[ServerType, List[ServerType]] = {
    ServerType.RENDERING:   [],
    ServerType.PHYSICS:     [],
    ServerType.AUDIO:       [ServerType.PHYSICS],
    ServerType.INPUT:       [],
    ServerType.SCRIPTING:   [ServerType.SCENE],
    ServerType.NETWORKING:  [],
    ServerType.AI:          [ServerType.PHYSICS, ServerType.PATHFINDING],
    ServerType.UI:          [ServerType.RENDERING, ServerType.INPUT],
    ServerType.SCENE:       [],
    ServerType.ASSET:       [],
    ServerType.PARTICLE:    [ServerType.RENDERING, ServerType.PHYSICS],
    ServerType.ANIMATION:   [ServerType.RENDERING],
    ServerType.SPATIAL:     [ServerType.PHYSICS],
    ServerType.PATHFINDING: [ServerType.SPATIAL],
}

_FALLBACK_DEFAULTS: Dict[str, Any] = {
    "priority": ServerPriority.NORMAL, "auto_start": False,
    "thread_affinity": -1, "max_fps": 30, "memory_limit_mb": 128,
}


# ---------------------------------------------------------------------------
# Singleton Registry
# ---------------------------------------------------------------------------


class ServerRegistry:
    """
    Central registry managing all engine subsystem servers.

    Each server represents a core engine subsystem that can be
    started, stopped, paused, resumed, and monitored independently.
    Provides lifecycle management, dependency-aware startup ordering,
    per-frame tick simulation, and aggregate status reporting.
    """

    _instance: Optional["ServerRegistry"] = None
    _lock = threading.RLock()

    MAX_ERROR_LOG_ENTRIES = 50
    SIMULATED_STARTUP_DELAY = 0.02
    SIMULATED_SHUTDOWN_DELAY = 0.01

    def __new__(cls) -> "ServerRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True

        self._servers: Dict[ServerType, ServerInfo] = {}
        self._configs: Dict[ServerType, ServerConfig] = {}
        self._error_log: List[Dict[str, Any]] = []
        self._startup_order: List[ServerType] = []
        self._total_ticks: int = 0
        self._is_initialized: bool = False

    @classmethod
    def get_instance(cls) -> "ServerRegistry":
        return cls()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self) -> None:
        """Set up the registry with default server configurations.

        Registers all predefined engine subsystem servers with their
        default configurations. Call start_all() separately to begin
        running servers marked with auto_start.
        """
        with self._lock:
            for server_type, defaults in _DEFAULT_CONFIGS.items():
                config = ServerConfig(
                    server_type=server_type,
                    priority=defaults["priority"],
                    auto_start=defaults["auto_start"],
                    thread_affinity=defaults["thread_affinity"],
                    max_fps=defaults["max_fps"],
                    memory_limit_mb=defaults["memory_limit_mb"],
                )
                info = ServerInfo(
                    server_type=server_type,
                    status=ServerStatus.STOPPED,
                    priority=config.priority,
                )
                self._servers[server_type] = info
                self._configs[server_type] = config

            self._compute_startup_order()
            self._is_initialized = True

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_server(self,
                        server_type: ServerType,
                        config: Optional[ServerConfig] = None) -> ServerInfo:
        """Register a new engine subsystem server.

        Args:
            server_type: The type of server to register.
            config: Optional configuration; defaults are used if omitted.

        Returns:
            The newly created ServerInfo instance.

        Raises:
            ValueError: If the server type is already registered.
        """
        with self._lock:
            if server_type in self._servers:
                raise ValueError(
                    f"Server type '{server_type.value}' is already registered."
                )

            if config is None:
                defaults = _DEFAULT_CONFIGS.get(server_type, _FALLBACK_DEFAULTS)
                config = ServerConfig(
                    server_type=server_type,
                    priority=defaults["priority"],
                    auto_start=defaults["auto_start"],
                    thread_affinity=defaults["thread_affinity"],
                    max_fps=defaults["max_fps"],
                    memory_limit_mb=defaults["memory_limit_mb"],
                )
            else:
                config.server_type = server_type

            info = ServerInfo(
                server_type=server_type,
                status=ServerStatus.STOPPED,
                priority=config.priority,
            )
            self._servers[server_type] = info
            self._configs[server_type] = config
            self._compute_startup_order()

            return info

    def unregister_server(self, server_type: ServerType) -> bool:
        """Remove a server from the registry.

        The server must be in STOPPED or ERROR state to be removed.
        Returns True if the server was removed, False otherwise.
        """
        with self._lock:
            info = self._servers.get(server_type)
            if info is None:
                return False
            if info.status not in (ServerStatus.STOPPED, ServerStatus.ERROR):
                return False

            # Reject if any running server depends on this type
            for other_type, other_info in self._servers.items():
                if other_type == server_type:
                    continue
                deps = _SERVER_DEPENDENCIES.get(other_type, [])
                if server_type in deps and other_info.status == ServerStatus.RUNNING:
                    return False

            del self._servers[server_type]
            self._configs.pop(server_type, None)
            self._compute_startup_order()
            return True

    # ------------------------------------------------------------------
    # Lifecycle: Start / Stop
    # ------------------------------------------------------------------

    def start_server(self, server_type: ServerType) -> bool:
        """Start a specific server.

        Validates that all dependencies are running before starting.
        Simulates a startup delay and a small (~3%) chance of failure.
        Returns True if the server was started successfully.
        """
        with self._lock:
            info = self._servers.get(server_type)
            if info is None:
                return False
            if info.status not in (ServerStatus.STOPPED, ServerStatus.ERROR):
                return False

            # Verify dependencies are running
            for dep_type in _SERVER_DEPENDENCIES.get(server_type, []):
                dep_info = self._servers.get(dep_type)
                if dep_info is None or dep_info.status != ServerStatus.RUNNING:
                    info.status = ServerStatus.ERROR
                    info.last_error = f"Dependency '{dep_type.value}' is not running."
                    info.error_count += 1
                    self._record_error(info, f"start_failed: {info.last_error}")
                    return False

            info.status = ServerStatus.STARTING

        _time_module.sleep(self.SIMULATED_STARTUP_DELAY)

        with self._lock:
            info = self._servers.get(server_type)
            if info is None or info.status != ServerStatus.STARTING:
                return False

            if random.random() < 0.03:
                info.status = ServerStatus.ERROR
                info.last_error = "Simulated startup failure."
                info.error_count += 1
                self._record_error(info, "start_failed: simulated")
                return False

            info.status = ServerStatus.RUNNING
            info.uptime_seconds = 0.0
            info.frame_count = 0
            info.cpu_usage = 0.0
            info.memory_usage = 0.0
            info.last_error = None
            return True

    def stop_server(self, server_type: ServerType) -> bool:
        """Stop a specific server.

        The server must be in RUNNING, PAUSED, or ERROR state.
        Simulates a shutdown delay. Returns True if stopped.
        """
        with self._lock:
            info = self._servers.get(server_type)
            if info is None:
                return False
            if info.status not in (
                ServerStatus.RUNNING, ServerStatus.PAUSED, ServerStatus.ERROR,
            ):
                return False

            # Reject if any running server depends on this type
            for other_type, other_info in self._servers.items():
                if other_type == server_type:
                    continue
                deps = _SERVER_DEPENDENCIES.get(other_type, [])
                if server_type in deps and other_info.status == ServerStatus.RUNNING:
                    return False

            info.status = ServerStatus.STOPPING

        _time_module.sleep(self.SIMULATED_SHUTDOWN_DELAY)

        with self._lock:
            info = self._servers.get(server_type)
            if info is None:
                return False
            info.status = ServerStatus.STOPPED
            info.cpu_usage = 0.0
            info.memory_usage = 0.0
            return True

    def start_all(self) -> Dict[str, Any]:
        """Start all registered servers in dependency order.

        Servers marked with auto_start=False are skipped.
        Returns a dict with 'started', 'failed', 'skipped',
        and 'already_running' lists.
        """
        results: Dict[str, Any] = {
            "started": [], "failed": [], "skipped": [], "already_running": [],
        }

        with self._lock:
            order = list(self._startup_order)

        for server_type in order:
            with self._lock:
                info = self._servers.get(server_type)
                if info is None:
                    continue
                if info.status == ServerStatus.RUNNING:
                    results["already_running"].append(server_type.value)
                    continue
                config = self._configs.get(server_type)
                if config is not None and not config.auto_start:
                    results["skipped"].append(server_type.value)
                    continue

            success = self.start_server(server_type)
            key = "started" if success else "failed"
            results[key].append(server_type.value)

        return results

    def stop_all(self) -> Dict[str, Any]:
        """Stop all registered servers in reverse dependency order.

        Returns a dict with 'stopped', 'failed', and
        'already_stopped' lists.
        """
        results: Dict[str, Any] = {
            "stopped": [], "failed": [], "already_stopped": [],
        }

        with self._lock:
            order = list(reversed(self._startup_order))

        for server_type in order:
            with self._lock:
                info = self._servers.get(server_type)
                if info is None:
                    continue
                if info.status == ServerStatus.STOPPED:
                    results["already_stopped"].append(server_type.value)
                    continue

            success = self.stop_server(server_type)
            key = "stopped" if success else "failed"
            results[key].append(server_type.value)

        return results

    # ------------------------------------------------------------------
    # Lifecycle: Pause / Resume
    # ------------------------------------------------------------------

    def pause_server(self, server_type: ServerType) -> bool:
        """Pause a running server. Only RUNNING servers can be paused."""
        with self._lock:
            info = self._servers.get(server_type)
            if info is None or info.status != ServerStatus.RUNNING:
                return False
            info.status = ServerStatus.PAUSED
            return True

    def resume_server(self, server_type: ServerType) -> bool:
        """Resume a paused server. Only PAUSED servers can be resumed."""
        with self._lock:
            info = self._servers.get(server_type)
            if info is None or info.status != ServerStatus.PAUSED:
                return False
            info.status = ServerStatus.RUNNING
            return True

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_server_info(self, server_type: ServerType) -> Optional[ServerInfo]:
        """Get runtime information for a specific server."""
        with self._lock:
            return self._servers.get(server_type)

    def get_all_servers(self) -> List[ServerInfo]:
        """Get all registered servers in startup order."""
        with self._lock:
            return [
                self._servers[st] for st in self._startup_order
                if st in self._servers
            ]

    def get_status(self) -> Dict[str, Any]:
        """Return overall registry status with per-server breakdown."""
        with self._lock:
            status_counts = {
                "running": 0, "paused": 0, "stopped": 0,
                "error": 0, "starting": 0, "stopping": 0,
            }
            for s in self._servers.values():
                status_counts[s.status.value] = status_counts.get(s.status.value, 0) + 1

            total_cpu = sum(s.cpu_usage for s in self._servers.values())
            total_memory = sum(s.memory_usage for s in self._servers.values())
            total_frames = sum(s.frame_count for s in self._servers.values())
            total_errors = sum(s.error_count for s in self._servers.values())

            server_breakdown: Dict[str, Dict[str, Any]] = {}
            for st in self._startup_order:
                info = self._servers.get(st)
                if info is None:
                    continue
                cfg = self._configs.get(st)
                server_breakdown[st.value] = {
                    "status": info.status.value,
                    "priority": info.priority.value,
                    "uptime_seconds": round(info.uptime_seconds, 4),
                    "frame_count": info.frame_count,
                    "error_count": info.error_count,
                    "cpu_usage": round(info.cpu_usage, 2),
                    "memory_usage": round(info.memory_usage, 2),
                    "max_fps": cfg.max_fps if cfg else 0,
                    "memory_limit_mb": cfg.memory_limit_mb if cfg else 0,
                    "auto_start": cfg.auto_start if cfg else False,
                }

            return {
                "total_servers": len(self._servers),
                **status_counts,
                "total_cpu_usage": round(total_cpu, 2),
                "total_memory_usage": round(total_memory, 2),
                "total_frame_count": total_frames,
                "total_errors": total_errors,
                "total_ticks": self._total_ticks,
                "is_initialized": self._is_initialized,
                "servers": server_breakdown,
            }

    # ------------------------------------------------------------------
    # Frame Tick Simulation
    # ------------------------------------------------------------------

    def tick_server(self, server_type: ServerType) -> bool:
        """Simulate a single frame tick for a server.

        Updates the frame counter, uptime, and simulated resource usage.
        Only processes RUNNING servers. Each tick has a ~1% chance of
        simulating a transient error.
        """
        with self._lock:
            info = self._servers.get(server_type)
            if info is None or info.status != ServerStatus.RUNNING:
                return False

            config = self._configs.get(server_type)
            max_fps = config.max_fps if config else 60

            info.frame_count += 1
            info.uptime_seconds += 1.0 / max_fps

            # Simulate CPU usage based on priority with jitter
            base_cpu = {
                ServerPriority.CRITICAL: 8.0, ServerPriority.HIGH: 5.0,
                ServerPriority.NORMAL: 3.0, ServerPriority.LOW: 1.5,
                ServerPriority.BACKGROUND: 0.5,
            }.get(info.priority, 3.0)
            info.cpu_usage = max(0.0, min(100.0,
                base_cpu + random.uniform(-2.0, 4.0)))

            # Simulate memory usage between ~30% and full allocation
            memory_limit = config.memory_limit_mb if config else 256
            info.memory_usage = max(0.0, min(float(memory_limit),
                (memory_limit * 0.3) + random.uniform(-10.0, 30.0)))

            # ~1% chance of transient error per tick
            if random.random() < 0.01:
                info.last_error = random.choice([
                    f"Transient frame drop on tick {info.frame_count}",
                    f"Resource allocation delay on tick {info.frame_count}",
                    f"Subsystem buffer overflow on tick {info.frame_count}",
                ])
                info.error_count += 1
                self._record_error(info, info.last_error)

            self._total_ticks += 1
            return True

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> Dict[str, Any]:
        """Perform a clean shutdown of all servers.

        Stops all running servers in reverse dependency order, clears
        internal state, and returns a shutdown summary.
        """
        stop_results = self.stop_all()

        with self._lock:
            total_servers = len(self._servers)
            total_frames = sum(s.frame_count for s in self._servers.values())
            total_errors = sum(s.error_count for s in self._servers.values())

            self._servers.clear()
            self._configs.clear()
            self._error_log.clear()
            self._startup_order.clear()
            self._total_ticks = 0
            self._is_initialized = False

        return {
            "shutdown_complete": True,
            "servers_stopped": stop_results["stopped"],
            "servers_already_stopped": stop_results["already_stopped"],
            "servers_failed_to_stop": stop_results["failed"],
            "total_servers_cleared": total_servers,
            "total_frames_processed": total_frames,
            "total_errors_encountered": total_errors,
        }

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _compute_startup_order(self) -> None:
        """Compute topological sort order from the dependency graph."""
        visited: set[ServerType] = set()
        temp_mark: set[ServerType] = set()
        order: List[ServerType] = []

        def visit(st: ServerType) -> None:
            if st in temp_mark or st in visited:
                return
            if st not in self._servers:
                return
            temp_mark.add(st)
            for dep in _SERVER_DEPENDENCIES.get(st, []):
                if dep in self._servers:
                    visit(dep)
            temp_mark.discard(st)
            visited.add(st)
            order.append(st)

        for st in self._servers:
            visit(st)

        self._startup_order = order

    def _record_error(self, info: ServerInfo, message: str) -> None:
        """Record an error entry in the internal error log."""
        self._error_log.append({
            "server_id": info.id,
            "server_type": info.server_type.value,
            "timestamp": _time_module.time(),
            "frame_count": info.frame_count,
            "message": message,
        })
        if len(self._error_log) > self.MAX_ERROR_LOG_ENTRIES:
            self._error_log = self._error_log[-self.MAX_ERROR_LOG_ENTRIES:]


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_server_registry() -> ServerRegistry:
    """Convenience accessor for the singleton ServerRegistry instance."""
    return ServerRegistry.get_instance()