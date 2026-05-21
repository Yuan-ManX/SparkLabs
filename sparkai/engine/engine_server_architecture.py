"""
SparkLabs Engine - Game Server Architecture

Godot-style dedicated server process pool managing isolated server
instances for rendering, physics, audio, networking, and AI subsystems.
Provides server lifecycle orchestration, health monitoring, load-aware
allocation, elastic scaling policies, and inter-server communication
coordination.

Architecture:
  GameServerPool
    |-- ServerInstance (individual server node representation)
    |-- ServerProcess (OS-level process tracking and binding)
    |-- HealthCheck (periodic resource and performance monitoring)
    |-- LoadBalancer (per-role auto-scaling and distribution logic)

Pool Features:
  - SPAWN: dedicate server processes per subsystem role
  - HEALTH: cpu, memory, latency, and throughput pulse checks
  - ALLOCATE: capacity-aware server selection for incoming work
  - SCALE: fixed, elastic, on-demand, and predictive scaling policies
  - MONITOR: cluster-wide status overview and statistics
  - RECOVER: automated restart, drain, and crash handling
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ServerRole(Enum):
    RENDER = "render"
    PHYSICS = "physics"
    AUDIO = "audio"
    NETWORK = "network"
    AI = "ai"
    LOGIC = "logic"
    DATABASE = "database"
    CACHE = "cache"
    ANALYTICS = "analytics"


class ServerState(Enum):
    BOOTING = "booting"
    IDLE = "idle"
    BUSY = "busy"
    OVERLOADED = "overloaded"
    DRAINING = "draining"
    OFFLINE = "offline"
    CRASHED = "crashed"


class ScalingPolicy(Enum):
    FIXED = "fixed"
    ELASTIC = "elastic"
    ON_DEMAND = "on_demand"
    PREDICTIVE = "predictive"


class HealthStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class ServerInstance:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: ServerRole = ServerRole.LOGIC
    state: ServerState = ServerState.BOOTING
    host: str = "127.0.0.1"
    port: int = 9000
    pid: int = 0
    cpu_usage: float = 0.0
    memory_mb: float = 0.0
    capacity: float = 100.0
    current_load: float = 0.0
    max_connections: int = 256
    active_connections: int = 0
    throughput: float = 0.0
    uptime: float = 0.0
    started_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    config: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "state": self.state.value,
            "host": self.host,
            "port": self.port,
            "pid": self.pid,
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_mb": round(self.memory_mb, 1),
            "capacity": round(self.capacity, 1),
            "current_load": round(self.current_load, 1),
            "max_connections": self.max_connections,
            "active_connections": self.active_connections,
            "throughput": round(self.throughput, 1),
            "uptime": round(self.uptime, 1),
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "labels": self.labels,
        }


@dataclass
class ServerProcess:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    server_id: str = ""
    pid: int = 0
    command: str = ""
    started_at: float = field(default_factory=time.time)
    exited_at: Optional[float] = None
    exit_code: Optional[int] = None
    restart_count: int = 0
    max_restarts: int = 5
    stdout_capture: List[str] = field(default_factory=list)
    stderr_capture: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "server_id": self.server_id,
            "pid": self.pid,
            "command": self.command,
            "started_at": self.started_at,
            "exited_at": self.exited_at,
            "exit_code": self.exit_code,
            "restart_count": self.restart_count,
            "max_restarts": self.max_restarts,
        }


@dataclass
class HealthCheck:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    server_id: str = ""
    timestamp: float = field(default_factory=time.time)
    cpu_usage: float = 0.0
    memory_mb: float = 0.0
    latency_ms: float = 0.0
    throughput: float = 0.0
    error_rate: float = 0.0
    disk_io_mbps: float = 0.0
    network_io_mbps: float = 0.0
    status: HealthStatus = HealthStatus.UNKNOWN

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "server_id": self.server_id,
            "timestamp": self.timestamp,
            "cpu_usage": round(self.cpu_usage, 2),
            "memory_mb": round(self.memory_mb, 1),
            "latency_ms": round(self.latency_ms, 1),
            "throughput": round(self.throughput, 1),
            "error_rate": round(self.error_rate, 4),
            "disk_io_mbps": round(self.disk_io_mbps, 2),
            "network_io_mbps": round(self.network_io_mbps, 2),
            "status": self.status.value,
        }


@dataclass
class LoadBalancer:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    role: ServerRole = ServerRole.LOGIC
    policy: ScalingPolicy = ScalingPolicy.FIXED
    min_instances: int = 1
    max_instances: int = 10
    current_instances: int = 0
    load_threshold_high: float = 80.0
    load_threshold_low: float = 30.0
    cooldown_seconds: float = 60.0
    last_scale_action: float = 0.0
    target_instances: int = 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role.value,
            "policy": self.policy.value,
            "min_instances": self.min_instances,
            "max_instances": self.max_instances,
            "current_instances": self.current_instances,
            "load_threshold_high": self.load_threshold_high,
            "load_threshold_low": self.load_threshold_low,
            "cooldown_seconds": self.cooldown_seconds,
            "last_scale_action": self.last_scale_action,
            "target_instances": self.target_instances,
        }


class GameServerPool:
    """Dedicated server process pool managing isolated subsystem instances."""

    _instance: Optional["GameServerPool"] = None
    _lock = threading.RLock()

    DEFAULT_BASE_PORT = 9000
    MAX_HEALTH_RECORDS = 200
    HEARTBEAT_TIMEOUT = 30.0

    def __init__(self) -> None:
        self._servers: Dict[str, ServerInstance] = {}
        self._processes: Dict[str, ServerProcess] = {}
        self._health_records: Dict[str, List[HealthCheck]] = {}
        self._load_balancers: Dict[ServerRole, LoadBalancer] = {}
        self._next_port: Dict[ServerRole, int] = {}
        self._scale_log: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> "GameServerPool":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Server Lifecycle ----

    def spawn_server(self,
                     role: str,
                     host: str = "127.0.0.1",
                     port: Optional[int] = None,
                     config: Optional[Dict[str, Any]] = None) -> Optional[ServerInstance]:
        try:
            sr = ServerRole(role.lower())
        except ValueError:
            return None

        if sr not in self._next_port:
            self._next_port[sr] = port if port else self.DEFAULT_BASE_PORT

        assigned_port = port if port else self._next_port[sr]
        self._next_port[sr] = assigned_port + 1

        instance = ServerInstance(
            role=sr,
            host=host,
            port=assigned_port,
            state=ServerState.BOOTING,
            config=config or {},
        )

        spawn_pid = abs(hash(instance.id)) % 65535 + 1024
        instance.pid = spawn_pid

        proc = ServerProcess(
            server_id=instance.id,
            pid=spawn_pid,
            command=f"{sr.value}_server --port {assigned_port} --host {host}",
        )
        self._processes[proc.id] = proc

        instance.state = ServerState.IDLE
        self._servers[instance.id] = instance

        if sr not in self._load_balancers:
            self._load_balancers[sr] = LoadBalancer(role=sr)
        lb = self._load_balancers[sr]
        lb.current_instances = sum(
            1 for s in self._servers.values()
            if s.role == sr and s.state != ServerState.CRASHED
        )

        return instance

    def terminate_server(self, server_id: str) -> bool:
        instance = self._servers.get(server_id)
        if instance is None:
            return False

        instance.state = ServerState.DRAINING
        instance.last_heartbeat = 0.0

        process = self._find_process_by_server(server_id)
        if process:
            process.exit_code = 0
            process.exited_at = time.time()

        instance.state = ServerState.OFFLINE

        role = instance.role
        if role in self._load_balancers:
            lb = self._load_balancers[role]
            lb.current_instances = sum(
                1 for s in self._servers.values()
                if s.role == role and s.state not in (
                    ServerState.OFFLINE, ServerState.CRASHED,
                )
            )

        return True

    def restart_server(self, server_id: str) -> Optional[ServerInstance]:
        instance = self._servers.get(server_id)
        if instance is None:
            return None

        process = self._find_process_by_server(server_id)
        if process and process.restart_count >= process.max_restarts:
            instance.state = ServerState.CRASHED
            return None

        old_config = instance.config
        old_host = instance.host
        old_port = instance.port
        old_role = instance.role

        self.terminate_server(server_id)

        if process:
            process.restart_count += 1

        new_instance = self.spawn_server(
            role=old_role.value,
            host=old_host,
            port=old_port,
            config=old_config,
        )
        return new_instance

    # ---- Health Monitoring ----

    def register_health_check(self,
                              server_id: str,
                              cpu_usage: float = 0.0,
                              memory_mb: float = 0.0,
                              latency_ms: float = 0.0,
                              throughput: float = 0.0) -> Optional[HealthCheck]:
        instance = self._servers.get(server_id)
        if instance is None:
            return None

        if cpu_usage > 90.0 or memory_mb > 18000:
            status = HealthStatus.CRITICAL
        elif cpu_usage > 70.0 or memory_mb > 12000 or latency_ms > 200:
            status = HealthStatus.DEGRADED
        elif cpu_usage > 50.0 or latency_ms > 100:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        check = HealthCheck(
            server_id=server_id,
            cpu_usage=cpu_usage,
            memory_mb=memory_mb,
            latency_ms=latency_ms,
            throughput=throughput,
            status=status,
            error_rate=max(0.0, (cpu_usage / 100.0) * 0.1),
        )

        instance.cpu_usage = cpu_usage
        instance.memory_mb = memory_mb
        instance.throughput = throughput
        instance.current_load = cpu_usage
        instance.last_heartbeat = time.time()
        instance.uptime = time.time() - instance.started_at

        if server_id not in self._health_records:
            self._health_records[server_id] = []

        records = self._health_records[server_id]
        records.append(check)
        if len(records) > self.MAX_HEALTH_RECORDS:
            self._health_records[server_id] = records[-self.MAX_HEALTH_RECORDS:]

        if status == HealthStatus.CRITICAL and instance.state != ServerState.DRAINING:
            instance.state = ServerState.DEGRADED if cpu_usage < 95.0 else ServerState.CRASHED

        return check

    def get_server_health(self, server_id: str) -> HealthStatus:
        instance = self._servers.get(server_id)
        if instance is None:
            return HealthStatus.UNKNOWN

        if instance.state == ServerState.CRASHED:
            return HealthStatus.CRITICAL
        if instance.state == ServerState.OFFLINE:
            return HealthStatus.UNKNOWN

        if time.time() - instance.last_heartbeat > self.HEARTBEAT_TIMEOUT:
            return HealthStatus.UNKNOWN

        records = self._health_records.get(server_id, [])
        if not records:
            return HealthStatus.UNKNOWN

        return records[-1].status

    # ---- Allocation ----

    def allocate_server(self,
                        role: str,
                        min_capacity: float = 10.0) -> Optional[ServerInstance]:
        try:
            sr = ServerRole(role.lower())
        except ValueError:
            return None

        candidates = [
            s for s in self._servers.values()
            if s.role == sr
            and s.state in (ServerState.IDLE, ServerState.BUSY)
            and s.capacity - s.current_load >= min_capacity
            and time.time() - s.last_heartbeat <= self.HEARTBEAT_TIMEOUT
        ]

        if not candidates:
            return None

        candidates.sort(
            key=lambda s: (s.current_load / max(s.capacity, 1.0))
        )
        return candidates[0]

    # ---- Scaling ----

    def set_scaling_policy(self,
                           role: str,
                           policy: str,
                           min_instances: int = 1,
                           max_instances: int = 10) -> Optional[LoadBalancer]:
        try:
            sr = ServerRole(role.lower())
            sp = ScalingPolicy(policy.lower())
        except ValueError:
            return None

        min_instances = max(1, min(100, min_instances))
        max_instances = max(min_instances, min(200, max_instances))

        if sr in self._load_balancers:
            lb = self._load_balancers[sr]
        else:
            lb = LoadBalancer(role=sr)
            self._load_balancers[sr] = lb

        lb.policy = sp
        lb.min_instances = min_instances
        lb.max_instances = max_instances
        lb.current_instances = sum(
            1 for s in self._servers.values()
            if s.role == sr and s.state != ServerState.CRASHED
        )

        return lb

    def auto_scale(self) -> Dict[str, Any]:
        actions: Dict[str, List[str]] = {
            "scale_up": [],
            "scale_down": [],
            "no_action": [],
        }
        now = time.time()

        for role, lb in self._load_balancers.items():
            if lb.policy == ScalingPolicy.FIXED:
                actions["no_action"].append(role.value)
                continue

            if now - lb.last_scale_action < lb.cooldown_seconds:
                actions["no_action"].append(role.value)
                continue

            active_servers = [
                s for s in self._servers.values()
                if s.role == role and s.state not in (
                    ServerState.OFFLINE, ServerState.CRASHED, ServerState.DRAINING,
                )
            ]
            alive_count = len(active_servers)

            if alive_count < lb.min_instances:
                needed = lb.min_instances - alive_count
                for _ in range(needed):
                    result = self.spawn_server(role=role.value)
                    if result:
                        actions["scale_up"].append(
                            f"{role.value}:{result.id}"
                        )
                lb.current_instances = max(lb.min_instances, alive_count + needed)
                lb.last_scale_action = now
                continue

            avg_load = (
                sum(s.current_load for s in active_servers) / alive_count
                if alive_count > 0 else 0.0
            )
            lb.current_instances = alive_count

            if avg_load > lb.load_threshold_high and alive_count < lb.max_instances:
                result = self.spawn_server(role=role.value)
                if result:
                    actions["scale_up"].append(f"{role.value}:{result.id}")
                    lb.current_instances = alive_count + 1
                    lb.last_scale_action = now

            elif avg_load < lb.load_threshold_low and alive_count > lb.min_instances:
                to_drain = active_servers[-1]
                self.terminate_server(to_drain.id)
                actions["scale_down"].append(f"{role.value}:{to_drain.id}")
                lb.current_instances = alive_count - 1
                lb.last_scale_action = now

            else:
                actions["no_action"].append(role.value)

        self._scale_log.append({
            "timestamp": now,
            "actions": actions,
        })
        return actions

    # ---- Query ----

    def list_servers(self,
                     role: Optional[str] = None,
                     state: Optional[str] = None) -> List[ServerInstance]:
        results = list(self._servers.values())

        if role is not None:
            try:
                sr = ServerRole(role.lower())
                results = [s for s in results if s.role == sr]
            except ValueError:
                return []

        if state is not None:
            try:
                ss = ServerState(state.lower())
                results = [s for s in results if s.state == ss]
            except ValueError:
                return []

        return results

    def get_cluster_status(self) -> Dict[str, Any]:
        role_summary: Dict[str, Dict[str, Any]] = {}
        for role in ServerRole:
            role_servers = [s for s in self._servers.values() if s.role == role]
            role_summary[role.value] = {
                "total": len(role_servers),
                "idle": sum(1 for s in role_servers if s.state == ServerState.IDLE),
                "busy": sum(1 for s in role_servers if s.state == ServerState.BUSY),
                "overloaded": sum(1 for s in role_servers if s.state == ServerState.OVERLOADED),
                "offline": sum(1 for s in role_servers if s.state == ServerState.OFFLINE),
                "crashed": sum(1 for s in role_servers if s.state == ServerState.CRASHED),
                "avg_load": round(
                    sum(s.current_load for s in role_servers) / max(len(role_servers), 1), 1
                ),
            }

        total_servers = len(self._servers)
        healthy_count = sum(
            1 for sid in self._servers
            if self.get_server_health(sid) == HealthStatus.HEALTHY
        )

        return {
            "total_servers": total_servers,
            "healthy_servers": healthy_count,
            "unhealthy_servers": total_servers - healthy_count,
            "total_processes": len(self._processes),
            "roles": role_summary,
            "scaling_policies": {
                role.value: lb.to_dict()
                for role, lb in self._load_balancers.items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        total_active = sum(
            1 for s in self._servers.values()
            if s.state not in (ServerState.OFFLINE, ServerState.CRASHED)
        )
        total_cpu = sum(s.cpu_usage for s in self._servers.values())
        total_memory = sum(s.memory_mb for s in self._servers.values())
        total_health_records = sum(
            len(records) for records in self._health_records.values()
        )

        return {
            "total_servers": len(self._servers),
            "active_servers": total_active,
            "offline_servers": sum(
                1 for s in self._servers.values()
                if s.state == ServerState.OFFLINE
            ),
            "crashed_servers": sum(
                1 for s in self._servers.values()
                if s.state == ServerState.CRASHED
            ),
            "aggregate_cpu_usage": round(total_cpu, 2),
            "aggregate_memory_mb": round(total_memory, 1),
            "total_health_records": total_health_records,
            "load_balancer_count": len(self._load_balancers),
            "process_count": len(self._processes),
            "scale_actions_logged": len(self._scale_log),
            "heartbeat_timeout": self.HEARTBEAT_TIMEOUT,
            "max_health_records_per_server": self.MAX_HEALTH_RECORDS,
        }

    # ---- Internal Helpers ----

    def _find_process_by_server(self, server_id: str) -> Optional[ServerProcess]:
        for proc in self._processes.values():
            if proc.server_id == server_id:
                return proc
        return None


def get_server_pool() -> GameServerPool:
    return GameServerPool.get_instance()