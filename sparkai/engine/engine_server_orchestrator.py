"""
SparkLabs Engine - Server Orchestrator

Central orchestration system for all engine subsystem servers. Manages server lifecycle, command queuing, resource
allocation, health monitoring, dependency discovery, and inter-server
communication coordination.

Architecture:
  EngineServerOrchestrator (Singleton)
    |-- ServerInstance (individual engine subsystem server)
    |-- CommandQueue (per-server FIFO command pipeline)
    |-- ResourceHandle (tracked resource allocation)
    |-- ServerHealthMetric (periodic health snapshot)
    |-- ServerType / ServerStatus / CommandPriority / ResourceType (enums)

Capabilities:
  - REGISTER: bring up isolated subsystem servers per type
  - LIFECYCLE: init, start, pause, resume, graceful/force shutdown
  - COMMAND: submit, query, cancel, drain per-server command queues
  - RESOURCE: allocate, release, lock, unlock server-scoped resources
  - HEALTH: per-server and cluster-wide health snapshots
  - DISCOVER: resolve inter-server dependency graph
  - OPTIMIZE: recommend thread pool and queue sizing per server
  - RECOVER: intelligent failure handling with impact analysis
  - BROADCAST: fan-out messages to server type groups
  - HEARTBEAT: periodic liveness checks across all servers
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
    RENDER = "render"
    PHYSICS = "physics"
    AUDIO = "audio"
    NAVIGATION = "navigation"
    AI = "ai"
    SCRIPTING = "scripting"
    INPUT = "input"
    NETWORK = "network"
    FILE_IO = "file_io"
    MEMORY = "memory"
    UI = "ui"
    ANIMATION = "animation"
    PARTICLE = "particle"
    WORLD = "world"


class ServerStatus(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    DRAINING = "draining"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    ERROR = "error"
    RECOVERING = "recovering"


class CommandPriority(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"
    BACKGROUND = "background"


class ResourceType(Enum):
    GPU_BUFFER = "gpu_buffer"
    TEXTURE = "texture"
    SHADER = "shader"
    MESH = "mesh"
    AUDIO_CLIP = "audio_clip"
    PHYSICS_WORLD = "physics_world"
    NAVIGATION_MESH = "navigation_mesh"
    AI_BEHAVIOR_TREE = "ai_behavior_tree"
    PARTICLE_SYSTEM = "particle_system"
    ANIMATION_CLIP = "animation_clip"
    NETWORK_SOCKET = "network_socket"
    FILE_HANDLE = "file_handle"
    FONT = "font"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ServerInstance:
    """Describes a registered engine subsystem server."""

    server_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    server_type: str = ServerType.AI.value
    name: str = ""
    status: str = ServerStatus.UNINITIALIZED.value
    priority: int = 0
    thread_pool_size: int = 4
    command_queue_size: int = 256
    is_initialized: bool = False
    is_active: bool = False
    resource_handle: str = ""
    uptime: float = 0.0
    processed_commands: int = 0
    failed_commands: int = 0
    avg_process_time: float = 0.0
    last_heartbeat: float = field(default_factory=_time_module.time)
    registered_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "server_id": self.server_id,
            "server_type": self.server_type,
            "name": self.name,
            "status": self.status,
            "priority": self.priority,
            "thread_pool_size": self.thread_pool_size,
            "command_queue_size": self.command_queue_size,
            "is_initialized": self.is_initialized,
            "is_active": self.is_active,
            "resource_handle": self.resource_handle,
            "uptime": round(self.uptime, 4),
            "processed_commands": self.processed_commands,
            "failed_commands": self.failed_commands,
            "avg_process_time": round(self.avg_process_time, 6),
            "last_heartbeat": self.last_heartbeat,
            "registered_at": self.registered_at,
        }


@dataclass
class CommandQueue:
    """FIFO command pipeline bound to a specific server."""

    queue_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    server_id: str = ""
    commands: List[Dict[str, Any]] = field(default_factory=list)
    max_size: int = 256
    current_size: int = 0
    is_processing: bool = False
    processing_started_at: float = 0.0
    last_drained: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "queue_id": self.queue_id,
            "server_id": self.server_id,
            "commands": list(self.commands),
            "max_size": self.max_size,
            "current_size": self.current_size,
            "is_processing": self.is_processing,
            "processing_started_at": self.processing_started_at,
            "last_drained": self.last_drained,
        }


@dataclass
class ResourceHandle:
    """Tracks a resource allocated to a server."""

    handle_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    server_id: str = ""
    resource_type: str = ResourceType.CUSTOM.value
    allocation_size: float = 0.0
    is_allocated: bool = False
    is_locked: bool = False
    created_at: float = field(default_factory=_time_module.time)
    last_accessed: float = field(default_factory=_time_module.time)
    lock_owner: str = ""
    reference_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "handle_id": self.handle_id,
            "server_id": self.server_id,
            "resource_type": self.resource_type,
            "allocation_size": round(self.allocation_size, 2),
            "is_allocated": self.is_allocated,
            "is_locked": self.is_locked,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "lock_owner": self.lock_owner,
            "reference_count": self.reference_count,
            "metadata": dict(self.metadata),
        }


@dataclass
class ServerHealthMetric:
    """Periodic health snapshot for a single server."""

    metric_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    server_id: str = ""
    cpu_usage: float = 0.0
    memory_usage: float = 0.0
    thread_count: int = 0
    queue_depth: int = 0
    command_throughput: float = 0.0
    error_rate: float = 0.0
    response_time_p95: float = 0.0
    connection_count: int = 0
    timestamp: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metric_id": self.metric_id,
            "server_id": self.server_id,
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_usage": round(self.memory_usage, 2),
            "thread_count": self.thread_count,
            "queue_depth": self.queue_depth,
            "command_throughput": round(self.command_throughput, 4),
            "error_rate": round(self.error_rate, 4),
            "response_time_p95": round(self.response_time_p95, 4),
            "connection_count": self.connection_count,
            "timestamp": self.timestamp,
        }


# ---------------------------------------------------------------------------
# Predefined Inter-Server Dependency Graph
# ---------------------------------------------------------------------------

_SERVER_DEPENDENCIES: Dict[str, List[str]] = {
    ServerType.RENDER.value:     [],
    ServerType.PHYSICS.value:    [],
    ServerType.AUDIO.value:      [ServerType.PHYSICS.value],
    ServerType.NAVIGATION.value: [ServerType.PHYSICS.value],
    ServerType.AI.value:         [ServerType.PHYSICS.value, ServerType.NAVIGATION.value],
    ServerType.SCRIPTING.value:  [ServerType.AI.value, ServerType.INPUT.value],
    ServerType.INPUT.value:      [],
    ServerType.NETWORK.value:    [],
    ServerType.FILE_IO.value:    [],
    ServerType.MEMORY.value:     [],
    ServerType.UI.value:         [ServerType.RENDER.value],
    ServerType.ANIMATION.value:  [ServerType.RENDER.value],
    ServerType.PARTICLE.value:   [ServerType.RENDER.value, ServerType.PHYSICS.value],
    ServerType.WORLD.value:      [ServerType.PHYSICS.value, ServerType.NAVIGATION.value, ServerType.RENDER.value],
}


# ---------------------------------------------------------------------------
# Singleton Orchestrator
# ---------------------------------------------------------------------------


class EngineServerOrchestrator:
    """
    Central orchestrator for all engine subsystem servers.

    Manages server lifecycle, command routing, resource tracking,
    health monitoring, dependency resolution, and inter-server
    communication across the entire engine architecture.
    """

    _instance: Optional["EngineServerOrchestrator"] = None
    _lock = threading.RLock()

    DEFAULT_THREAD_POOL_SIZE = 4
    DEFAULT_COMMAND_QUEUE_SIZE = 256
    HEARTBEAT_TIMEOUT = 10.0
    MAX_HEALTH_RECORDS = 100

    def __new__(cls) -> "EngineServerOrchestrator":
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

        self._servers: Dict[str, ServerInstance] = {}
        self._queues: Dict[str, CommandQueue] = {}
        self._resources: Dict[str, ResourceHandle] = {}
        self._health_records: Dict[str, List[ServerHealthMetric]] = {}
        self._failure_log: List[Dict[str, Any]] = []
        self._broadcast_log: List[Dict[str, Any]] = []

        self._total_servers_registered: int = 0
        self._total_commands_processed: int = 0
        self._total_resources_allocated: int = 0
        self._total_health_snapshots: int = 0

    @classmethod
    def get_instance(cls) -> "EngineServerOrchestrator":
        return cls()

    # ------------------------------------------------------------------
    # Server Lifecycle
    # ------------------------------------------------------------------

    def register_server(
        self,
        server_type: str,
        name: str = "",
        priority: int = 0,
        thread_pool_size: int = DEFAULT_THREAD_POOL_SIZE,
        command_queue_size: int = DEFAULT_COMMAND_QUEUE_SIZE,
    ) -> ServerInstance:
        try:
            ServerType(server_type.lower())
        except ValueError:
            server_type = ServerType.AI.value

        server = ServerInstance(
            server_type=server_type.lower(),
            name=name or f"{server_type}_server",
            priority=priority,
            thread_pool_size=max(1, thread_pool_size),
            command_queue_size=max(8, command_queue_size),
            status=ServerStatus.UNINITIALIZED.value,
        )

        self._servers[server.server_id] = server
        self._total_servers_registered += 1

        queue = CommandQueue(
            server_id=server.server_id,
            max_size=server.command_queue_size,
        )
        self._queues[queue.queue_id] = queue

        # Bookmark the queue id on the server for fast lookup
        server.resource_handle = queue.queue_id

        return server

    def initialize_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server is None:
            return False
        if server.status not in (ServerStatus.UNINITIALIZED.value, ServerStatus.ERROR.value):
            return False

        server.status = ServerStatus.INITIALIZING.value

        # Resolve dependencies — all must be READY or RUNNING
        deps = _SERVER_DEPENDENCIES.get(server.server_type, [])
        for dep_type in deps:
            dep_servers = [
                s for s in self._servers.values()
                if s.server_type == dep_type
                and s.status in (ServerStatus.READY.value, ServerStatus.RUNNING.value)
            ]
            if not dep_servers:
                server.status = ServerStatus.ERROR.value
                return False

        server.is_initialized = True
        server.status = ServerStatus.READY.value
        server.last_heartbeat = _time_module.time()
        return True

    def start_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server is None:
            return False
        if server.status not in (ServerStatus.READY.value, ServerStatus.PAUSED.value):
            return False

        server.status = ServerStatus.RUNNING.value
        server.is_active = True
        server.uptime = 0.0
        server.registered_at = _time_module.time()
        server.last_heartbeat = _time_module.time()
        return True

    def pause_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server is None:
            return False
        if server.status != ServerStatus.RUNNING.value:
            return False

        server.status = ServerStatus.PAUSED.value
        server.is_active = False
        server.uptime = _time_module.time() - server.registered_at

        # Pause the associated queue
        queue = self._find_queue_by_server(server_id)
        if queue:
            queue.is_processing = False

        return True

    def resume_server(self, server_id: str) -> bool:
        server = self._servers.get(server_id)
        if server is None:
            return False
        if server.status != ServerStatus.PAUSED.value:
            return False

        server.status = ServerStatus.RUNNING.value
        server.is_active = True
        server.registered_at = _time_module.time()
        server.last_heartbeat = _time_module.time()

        queue = self._find_queue_by_server(server_id)
        if queue:
            queue.is_processing = True
            queue.processing_started_at = _time_module.time()

        return True

    def shutdown_server(self, server_id: str, graceful: bool = True) -> bool:
        server = self._servers.get(server_id)
        if server is None:
            return False

        if graceful:
            server.status = ServerStatus.DRAINING.value
            drained = self.drain_command_queue(server_id)
            server.processed_commands += drained

        server.status = ServerStatus.SHUTTING_DOWN.value
        server.status = ServerStatus.STOPPED.value
        server.is_active = False
        server.is_initialized = False
        server.uptime = _time_module.time() - server.registered_at
        server.last_heartbeat = 0.0

        # Release all resources
        for handle in list(self._resources.values()):
            if handle.server_id == server_id:
                handle.is_allocated = False
                handle.is_locked = False
                handle.lock_owner = ""

        # Stop the queue
        queue = self._find_queue_by_server(server_id)
        if queue:
            queue.is_processing = False

        return True

    # ------------------------------------------------------------------
    # Command Queue Operations
    # ------------------------------------------------------------------

    def submit_command(
        self,
        server_id: str,
        command_type: str,
        payload: Optional[Dict[str, Any]] = None,
        priority: str = CommandPriority.NORMAL.value,
    ) -> str:
        server = self._servers.get(server_id)
        if server is None:
            return ""

        queue = self._find_queue_by_server(server_id)
        if queue is None:
            return ""

        if server.status not in (ServerStatus.READY.value, ServerStatus.RUNNING.value):
            return ""

        if queue.current_size >= queue.max_size:
            return ""

        command_id = self._generate_uid_stub()
        command = {
            "command_id": command_id,
            "type": command_type,
            "payload": payload or {},
            "priority": priority,
            "status": "queued",
            "submitted_at": _time_module.time(),
            "started_at": None,
            "completed_at": None,
            "result": None,
            "error": None,
        }

        queue.commands.append(command)
        queue.current_size = len(queue.commands)
        return command_id

    def get_command_result(self, server_id: str, command_id: str) -> Dict[str, Any]:
        queue = self._find_queue_by_server(server_id)
        if queue is None:
            return {}

        for cmd in queue.commands:
            if cmd["command_id"] == command_id:
                return dict(cmd)
        return {}

    def cancel_command(self, server_id: str, command_id: str) -> bool:
        queue = self._find_queue_by_server(server_id)
        if queue is None:
            return False

        for i, cmd in enumerate(queue.commands):
            if cmd["command_id"] == command_id:
                if cmd["status"] in ("queued",):
                    cmd["status"] = "cancelled"
                    cmd["completed_at"] = _time_module.time()
                    queue.last_drained = _time_module.time()
                    return True

        return False

    def drain_command_queue(self, server_id: str) -> int:
        server = self._servers.get(server_id)
        if server is None:
            return 0

        queue = self._find_queue_by_server(server_id)
        if queue is None:
            return 0

        processed = 0
        for cmd in queue.commands:
            if cmd["status"] == "queued":
                cmd["status"] = "processing"
                cmd["started_at"] = _time_module.time()

                # Simulate processing with a tiny delay indicating work
                process_start = _time_module.time()
                try:
                    cmd["result"] = {"status": "processed"}
                    cmd["status"] = "completed"
                    server.processed_commands += 1
                    self._total_commands_processed += 1
                    processed += 1
                except Exception:
                    cmd["error"] = "drain_error"
                    cmd["status"] = "failed"
                    server.failed_commands += 1

                process_time = _time_module.time() - process_start
                total_processed = max(1, server.processed_commands + server.failed_commands)
                server.avg_process_time = (
                    (server.avg_process_time * (total_processed - 1) + process_time)
                    / total_processed
                )
                cmd["completed_at"] = _time_module.time()

        queue.is_processing = False
        queue.last_drained = _time_module.time()
        queue.current_size = 0
        queue.commands.clear()

        return processed

    # ------------------------------------------------------------------
    # Resource Management
    # ------------------------------------------------------------------

    def allocate_resource(
        self,
        server_id: str,
        resource_type: str,
        allocation_size: float = 0.0,
    ) -> Optional[ResourceHandle]:
        server = self._servers.get(server_id)
        if server is None:
            return None

        try:
            ResourceType(resource_type.lower())
        except ValueError:
            resource_type = ResourceType.CUSTOM.value

        handle = ResourceHandle(
            server_id=server_id,
            resource_type=resource_type.lower(),
            allocation_size=max(0.0, allocation_size),
            is_allocated=True,
        )

        self._resources[handle.handle_id] = handle
        self._total_resources_allocated += 1

        return handle

    def release_resource(self, handle_id: str) -> bool:
        handle = self._resources.get(handle_id)
        if handle is None:
            return False
        if handle.is_locked:
            return False

        handle.is_allocated = False
        handle.reference_count = 0
        return True

    def lock_resource(self, handle_id: str, owner: str) -> bool:
        handle = self._resources.get(handle_id)
        if handle is None:
            return False
        if handle.is_locked and handle.lock_owner != owner:
            return False
        if not handle.is_allocated:
            return False

        handle.is_locked = True
        handle.lock_owner = owner
        handle.last_accessed = _time_module.time()
        handle.reference_count += 1
        return True

    def unlock_resource(self, handle_id: str) -> bool:
        handle = self._resources.get(handle_id)
        if handle is None:
            return False
        if not handle.is_locked:
            return False

        handle.is_locked = False
        handle.lock_owner = ""
        handle.last_accessed = _time_module.time()
        return True

    # ------------------------------------------------------------------
    # Health Monitoring
    # ------------------------------------------------------------------

    def get_server_health(self, server_id: str) -> Optional[ServerHealthMetric]:
        server = self._servers.get(server_id)
        if server is None:
            return None

        queue = self._find_queue_by_server(server_id)
        queue_depth = queue.current_size if queue else 0

        total_ops = max(1, server.processed_commands + server.failed_commands)
        error_rate = server.failed_commands / total_ops
        throughput = server.processed_commands / max(1.0, _time_module.time() - server.registered_at)

        metric = ServerHealthMetric(
            server_id=server_id,
            cpu_usage=round(random.uniform(5.0, 80.0), 2),
            memory_usage=round(random.uniform(20.0, 600.0), 2),
            thread_count=server.thread_pool_size,
            queue_depth=queue_depth,
            command_throughput=round(throughput, 4),
            error_rate=round(error_rate, 4),
            response_time_p95=round(server.avg_process_time * 1000 + random.uniform(0.5, 5.0), 4),
            connection_count=random.randint(0, 64),
        )

        if server_id not in self._health_records:
            self._health_records[server_id] = []

        records = self._health_records[server_id]
        records.append(metric)
        if len(records) > self.MAX_HEALTH_RECORDS:
            self._health_records[server_id] = records[-self.MAX_HEALTH_RECORDS:]

        self._total_health_snapshots += 1
        return metric

    def get_all_health(self) -> List[ServerHealthMetric]:
        results: List[ServerHealthMetric] = []
        for server_id in self._servers:
            metric = self.get_server_health(server_id)
            if metric:
                results.append(metric)
        return results

    # ------------------------------------------------------------------
    # Statistics & Overview
    # ------------------------------------------------------------------

    def get_server_stats(self, server_id: str) -> Dict[str, Any]:
        server = self._servers.get(server_id)
        if server is None:
            return {}

        queue = self._find_queue_by_server(server_id)
        total_ops = max(1, server.processed_commands + server.failed_commands)
        success_rate = server.processed_commands / total_ops

        return {
            "server_id": server.server_id,
            "server_type": server.server_type,
            "name": server.name,
            "status": server.status,
            "is_active": server.is_active,
            "uptime": round(server.uptime, 4),
            "processed_commands": server.processed_commands,
            "failed_commands": server.failed_commands,
            "success_rate": round(success_rate, 4),
            "avg_process_time": round(server.avg_process_time, 6),
            "queue_depth": queue.current_size if queue else 0,
            "queue_max": queue.max_size if queue else 0,
            "thread_pool_size": server.thread_pool_size,
            "priority": server.priority,
            "resource_count": sum(
                1 for h in self._resources.values()
                if h.server_id == server_id and h.is_allocated
            ),
        }

    def get_orchestration_overview(self) -> Dict[str, Any]:
        total_servers = len(self._servers)
        active_servers = sum(
            1 for s in self._servers.values()
            if s.status in (ServerStatus.RUNNING.value, ServerStatus.READY.value)
        )

        queue_depths = [
            q.current_size for q in self._queues.values()
            if q.server_id in self._servers
        ]
        avg_queue_depth = round(
            sum(queue_depths) / max(1, len(queue_depths)), 2
        )

        # System health score: weighted average across all server metrics
        health_records_flat: List[ServerHealthMetric] = []
        for records in self._health_records.values():
            if records:
                health_records_flat.append(records[-1])

        if health_records_flat:
            avg_error_rate = sum(m.error_rate for m in health_records_flat) / len(health_records_flat)
            avg_cpu = sum(m.cpu_usage for m in health_records_flat) / len(health_records_flat)
            health_score = max(0.0, 100.0 - (avg_error_rate * 1000) - (avg_cpu * 0.1))
            health_score = round(health_score, 2)
        else:
            health_score = 100.0

        return {
            "total_servers": total_servers,
            "active_servers": active_servers,
            "total_commands_processed": self._total_commands_processed,
            "total_resources": self._total_resources_allocated,
            "avg_queue_depth": avg_queue_depth,
            "system_health_score": health_score,
            "total_health_snapshots": self._total_health_snapshots,
        }

    # ------------------------------------------------------------------
    # Dependency Discovery
    # ------------------------------------------------------------------

    def discover_server_dependencies(self) -> Dict[str, Any]:
        results: Dict[str, Any] = {}

        for server_id, server in self._servers.items():
            server_type = server.server_type
            depends_on = _SERVER_DEPENDENCIES.get(server_type, [])

            depended_by = []
            for other_type, deps in _SERVER_DEPENDENCIES.items():
                if server_type in deps:
                    depended_by.append(other_type)

            results[server_id] = {
                "server_type": server_type,
                "name": server.name,
                "depends_on": depends_on,
                "depended_by": depended_by,
            }

        return results

    # ------------------------------------------------------------------
    # Optimization
    # ------------------------------------------------------------------

    def optimize_server_allocation(self) -> Dict[str, Any]:
        recommendations: Dict[str, Any] = {}

        for server_id, server in self._servers.items():
            processed = max(1, server.processed_commands)
            failed = server.failed_commands
            error_rate = failed / max(1, processed + failed)

            queue = self._find_queue_by_server(server_id)
            current_depth = queue.current_size if queue else 0
            max_queue = queue.max_size if queue else server.command_queue_size

            utilization = current_depth / max(1, max_queue)

            # Recommend thread pool
            if error_rate > 0.1:
                recommended_threads = min(server.thread_pool_size * 2, 32)
                rationale = f"High error rate ({error_rate:.2%}); increase thread pool for retry capacity."
            elif utilization > 0.8:
                recommended_threads = min(server.thread_pool_size + 2, 32)
                rationale = f"Queue near capacity ({utilization:.0%}); add threads for throughput."
            elif utilization < 0.2 and server.thread_pool_size > 1:
                recommended_threads = max(1, server.thread_pool_size - 1)
                rationale = "Low utilization; reduce threads to free pool resources."
            else:
                recommended_threads = server.thread_pool_size
                rationale = "Current allocation is adequate."

            # Recommend queue size
            if utilization > 0.9:
                recommended_queue = min(max_queue * 2, 65536)
                queue_rationale = "Queue consistently near capacity; double buffer size."
            elif utilization < 0.1 and max_queue > 64:
                recommended_queue = max(8, max_queue // 2)
                queue_rationale = "Queue underutilized; shrink to conserve memory."
            else:
                recommended_queue = max_queue
                queue_rationale = "Queue sizing is appropriate."

            recommendations[server_id] = {
                "server_type": server.server_type,
                "name": server.name,
                "recommended_thread_pool_size": recommended_threads,
                "recommended_queue_size": recommended_queue,
                "rationale": f"{rationale} {queue_rationale}",
            }

        return recommendations

    # ------------------------------------------------------------------
    # Failure Handling
    # ------------------------------------------------------------------

    def handle_server_failure(self, server_id: str) -> Dict[str, Any]:
        server = self._servers.get(server_id)
        if server is None:
            return {
                "error": "Server not found.",
                "affected_servers": [],
                "recovery_actions": [],
                "estimated_recovery_time": 0.0,
                "data_loss_risk": "unknown",
            }

        server.status = ServerStatus.ERROR.value
        server.is_active = False

        # Find downstream servers that depend on this server's type
        affected_servers: List[str] = []
        for sid, s in self._servers.items():
            if sid == server_id:
                continue
            deps = _SERVER_DEPENDENCIES.get(s.server_type, [])
            if server.server_type in deps:
                affected_servers.append(sid)

        recovery_actions: List[str] = []
        recovery_actions.append(f"Mark server '{server.name}' as ERROR.")
        recovery_actions.append("Drain and flush remaining command queue.")

        if server.server_type in (ServerType.RENDER.value, ServerType.PHYSICS.value):
            recovery_actions.append("Critical subsystem failure — initiate warm-standby handoff.")
            estimated_time = 5.0
            data_loss_risk = "moderate"
        elif server.server_type in (ServerType.AI.value, ServerType.SCRIPTING.value):
            recovery_actions.append("Non-realtime subsystem — safe to restart in background.")
            recovery_actions.append("Reinitialize dependent AI/Scripting servers after restart.")
            estimated_time = 3.0
            data_loss_risk = "low"
        elif server.server_type in (ServerType.FILE_IO.value, ServerType.MEMORY.value):
            recovery_actions.append("Data-plane failure — flush buffers before restart.")
            estimated_time = 2.0
            data_loss_risk = "high"
        else:
            recovery_actions.append("Standard recovery: restart and reinitialize.")
            estimated_time = 2.0
            data_loss_risk = "low"

        for affected in affected_servers:
            affected_server = self._servers.get(affected)
            if affected_server:
                affected_server.status = ServerStatus.ERROR.value
                affected_server.is_active = False
                recovery_actions.append(
                    f"Cascade: mark '{affected_server.name}' as ERROR (depends on '{server.server_type}')."
                )

        self._failure_log.append({
            "server_id": server_id,
            "server_type": server.server_type,
            "timestamp": _time_module.time(),
            "affected_servers": affected_servers,
        })

        return {
            "affected_servers": affected_servers,
            "recovery_actions": recovery_actions,
            "estimated_recovery_time": estimated_time,
            "data_loss_risk": data_loss_risk,
        }

    # ------------------------------------------------------------------
    # Broadcast & Heartbeat
    # ------------------------------------------------------------------

    def broadcast_to_servers(
        self,
        message: Dict[str, Any],
        server_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for server_id, server in self._servers.items():
            if server_types and server.server_type not in server_types:
                continue
            if server.status not in (ServerStatus.RUNNING.value, ServerStatus.READY.value):
                results.append({
                    "server_id": server_id,
                    "acknowledged": False,
                    "reason": "server not active",
                })
                continue

            results.append({
                "server_id": server_id,
                "acknowledged": True,
            })

        self._broadcast_log.append({
            "timestamp": _time_module.time(),
            "message": message,
            "recipients": [r["server_id"] for r in results],
            "acknowledged_count": sum(1 for r in results if r["acknowledged"]),
        })

        return results

    def heartbeat_check(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        now = _time_module.time()

        for server_id, server in self._servers.items():
            elapsed = now - server.last_heartbeat
            is_alive = elapsed < self.HEARTBEAT_TIMEOUT and server.status == ServerStatus.RUNNING.value

            if is_alive:
                records = self._health_records.get(server_id, [])
                if records:
                    last_metric = records[-1]
                    if last_metric.error_rate > 0.2:
                        health_status = "degraded"
                    elif last_metric.cpu_usage > 85.0:
                        health_status = "warning"
                    else:
                        health_status = "healthy"
                else:
                    health_status = "unknown"
            else:
                health_status = "unresponsive"

            results.append({
                "server_id": server_id,
                "last_heartbeat": server.last_heartbeat,
                "is_alive": is_alive,
                "health_status": health_status,
            })

        return results

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        self._servers.clear()
        self._queues.clear()
        self._resources.clear()
        self._health_records.clear()
        self._failure_log.clear()
        self._broadcast_log.clear()

        self._total_servers_registered = 0
        self._total_commands_processed = 0
        self._total_resources_allocated = 0
        self._total_health_snapshots = 0

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _find_queue_by_server(self, server_id: str) -> Optional[CommandQueue]:
        for queue in self._queues.values():
            if queue.server_id == server_id:
                return queue
        return None

    @staticmethod
    def _generate_uid_stub() -> str:
        return uuid.uuid4().hex


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_engine_server_orchestrator() -> EngineServerOrchestrator:
    return EngineServerOrchestrator.get_instance()