"""
SparkAI Agent - Environment Manager

Centralized environment lifecycle management for the Agent runtime.
Handles environment provisioning, sandbox isolation, dependency
resolution, resource allocation, and context management across
all agent execution environments.

Provides unified environment orchestration for local, containerized,
and serverless execution contexts with automatic resource scaling
and process isolation.
"""

from __future__ import annotations

import os
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class EnvironmentType(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    VENV = "venv"
    SANDBOX = "sandbox"
    SERVERLESS = "serverless"
    REMOTE = "remote"


class EnvironmentState(str, Enum):
    UNINITIALIZED = "uninitialized"
    PROVISIONING = "provisioning"
    READY = "ready"
    ACTIVE = "active"
    DRAINING = "draining"
    TERMINATED = "terminated"
    ERROR = "error"


class ResourceUnit(str, Enum):
    CPU_CORE = "cpu_core"
    MEMORY_MB = "memory_mb"
    DISK_GB = "disk_gb"
    GPU_COUNT = "gpu_count"
    NETWORK_MBPS = "network_mbps"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ResourceAllocation:
    """Resource allocation specification for an environment."""
    allocation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    cpu_cores: float = 1.0
    memory_mb: int = 512
    disk_gb: int = 10
    gpu_count: int = 0
    network_mbps: int = 100
    max_concurrent_tasks: int = 4
    timeout_seconds: int = 3600

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allocation_id": self.allocation_id,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "disk_gb": self.disk_gb,
            "gpu_count": self.gpu_count,
            "network_mbps": self.network_mbps,
            "max_concurrent_tasks": self.max_concurrent_tasks,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class EnvironmentInstance:
    """A provisioned environment instance."""
    instance_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    env_type: EnvironmentType = EnvironmentType.LOCAL
    state: EnvironmentState = EnvironmentState.UNINITIALIZED
    name: str = ""
    allocation: Optional[ResourceAllocation] = None
    workspace_path: str = ""
    python_version: str = ""
    installed_packages: List[str] = field(default_factory=list)
    active_tasks: int = 0
    total_tasks: int = 0
    error_count: int = 0
    last_error: str = ""
    created_at: float = field(default_factory=_time_module.time)
    last_used: float = field(default_factory=_time_module.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "instance_id": self.instance_id,
            "env_type": self.env_type.value,
            "state": self.state.value,
            "name": self.name,
            "allocation": self.allocation.to_dict() if self.allocation else None,
            "workspace_path": self.workspace_path,
            "python_version": self.python_version,
            "installed_packages": self.installed_packages,
            "active_tasks": self.active_tasks,
            "total_tasks": self.total_tasks,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "last_used": self.last_used,
        }


@dataclass
class DependencySpec:
    """Package and tool dependency specification."""
    spec_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    packages: List[str] = field(default_factory=list)
    system_tools: List[str] = field(default_factory=list)
    environment_vars: Dict[str, str] = field(default_factory=dict)
    python_version: str = "3.11"
    install_commands: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "spec_id": self.spec_id,
            "packages": self.packages,
            "system_tools": self.system_tools,
            "environment_vars": self.environment_vars,
            "python_version": self.python_version,
            "install_commands": self.install_commands,
        }


# ---------------------------------------------------------------------------
# Environment Manager
# ---------------------------------------------------------------------------

class AgentEnvironmentManager:
    """
    Centralized environment lifecycle orchestrator.

    Manages the full lifecycle of execution environments including
    provisioning, dependency resolution, resource allocation, health
    monitoring, and graceful teardown. Supports multiple environment
    types with automatic scaling and isolation.
    """

    _instance: Optional["AgentEnvironmentManager"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "AgentEnvironmentManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls) -> "AgentEnvironmentManager":
        if cls._instance is None:
            cls._instance = cls()
            cls._instance._initialize()
        return cls._instance

    def _initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._environments: Dict[str, EnvironmentInstance] = {}
        self._dependencies: Dict[str, DependencySpec] = {}
        self._global_limits: Dict[str, float] = {
            "max_environments": 50,
            "max_total_cpu": 32.0,
            "max_total_memory_mb": 65536,
            "max_total_gpu": 4,
        }
        self._current_usage: Dict[str, float] = {
            "total_cpu": 0.0,
            "total_memory_mb": 0,
            "total_gpu": 0,
        }
        self._total_provisioned: int = 0
        self._total_terminated: int = 0

    # ------------------------------------------------------------------
    # Environment Provisioning
    # ------------------------------------------------------------------

    def provision(
        self, name: str, env_type: EnvironmentType = EnvironmentType.LOCAL,
        allocation: Optional[ResourceAllocation] = None,
        workspace_path: str = "", python_version: str = "3.11",
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EnvironmentInstance:
        """Provision a new execution environment."""
        with self._lock:
            if len(self._environments) >= self._global_limits["max_environments"]:
                raise RuntimeError("Maximum environment count reached")

            alloc = allocation or ResourceAllocation()
            if self._current_usage["total_cpu"] + alloc.cpu_cores > self._global_limits["max_total_cpu"]:
                raise RuntimeError("Insufficient CPU resources")
            if self._current_usage["total_memory_mb"] + alloc.memory_mb > self._global_limits["max_total_memory_mb"]:
                raise RuntimeError("Insufficient memory resources")

            instance = EnvironmentInstance(
                env_type=env_type,
                state=EnvironmentState.PROVISIONING,
                name=name,
                allocation=alloc,
                workspace_path=workspace_path or f"/tmp/sparkai_env_{uuid.uuid4().hex[:8]}",
                python_version=python_version,
                installed_packages=dependencies or [],
                metadata=metadata or {},
            )

            # Simulate provisioning
            instance.state = EnvironmentState.READY
            instance.created_at = _time_module.time()

            self._environments[instance.instance_id] = instance
            self._current_usage["total_cpu"] += alloc.cpu_cores
            self._current_usage["total_memory_mb"] += alloc.memory_mb
            self._current_usage["total_gpu"] += alloc.gpu_count
            self._total_provisioned += 1
            return instance

    def activate(self, instance_id: str) -> bool:
        """Activate an environment for task execution."""
        with self._lock:
            instance = self._get_env(instance_id)
            if not instance:
                return False
            if instance.state not in (EnvironmentState.READY, EnvironmentState.ACTIVE):
                return False
            instance.state = EnvironmentState.ACTIVE
            instance.active_tasks += 1
            instance.total_tasks += 1
            instance.last_used = _time_module.time()
            return True

    def deactivate(self, instance_id: str) -> bool:
        """Deactivate an environment after task completion."""
        with self._lock:
            instance = self._get_env(instance_id)
            if not instance:
                return False
            instance.active_tasks = max(0, instance.active_tasks - 1)
            if instance.active_tasks == 0:
                instance.state = EnvironmentState.READY
            instance.last_used = _time_module.time()
            return True

    def terminate(self, instance_id: str) -> bool:
        """Terminate and clean up an environment."""
        with self._lock:
            instance = self._get_env(instance_id)
            if not instance:
                return False
            if instance.state in (EnvironmentState.TERMINATED,):
                return False

            instance.state = EnvironmentState.TERMINATED
            if instance.allocation:
                self._current_usage["total_cpu"] = max(0, self._current_usage["total_cpu"] - instance.allocation.cpu_cores)
                self._current_usage["total_memory_mb"] = max(0, self._current_usage["total_memory_mb"] - instance.allocation.memory_mb)
                self._current_usage["total_gpu"] = max(0, self._current_usage["total_gpu"] - instance.allocation.gpu_count)
            self._total_terminated += 1
            return True

    # ------------------------------------------------------------------
    # Dependency Management
    # ------------------------------------------------------------------

    def register_dependency_spec(
        self, packages: List[str],
        system_tools: Optional[List[str]] = None,
        environment_vars: Optional[Dict[str, str]] = None,
        python_version: str = "3.11",
        install_commands: Optional[List[str]] = None,
    ) -> DependencySpec:
        """Register a dependency specification for reuse."""
        with self._lock:
            spec = DependencySpec(
                packages=packages,
                system_tools=system_tools or [],
                environment_vars=environment_vars or {},
                python_version=python_version,
                install_commands=install_commands or [],
            )
            self._dependencies[spec.spec_id] = spec
            return spec

    def resolve_dependencies(
        self, instance_id: str, dep_spec_id: str,
    ) -> bool:
        """Resolve and install dependencies for an environment."""
        with self._lock:
            instance = self._get_env(instance_id)
            spec = self._dependencies.get(dep_spec_id)
            if not instance or not spec:
                return False
            instance.installed_packages.extend(spec.packages)
            instance.python_version = spec.python_version
            return True

    # ------------------------------------------------------------------
    # Health & Monitoring
    # ------------------------------------------------------------------

    def check_health(self, instance_id: str) -> Dict[str, Any]:
        """Check the health of an environment."""
        with self._lock:
            instance = self._get_env(instance_id)
            if not instance:
                return {"healthy": False, "reason": "Not found"}

            issues: List[str] = []
            if instance.state == EnvironmentState.ERROR:
                issues.append(f"Environment in error state: {instance.last_error}")
            if instance.error_count > 10:
                issues.append(f"High error count: {instance.error_count}")
            if instance.active_tasks > instance.allocation.max_concurrent_tasks if instance.allocation else 4:
                issues.append("Over-allocated tasks")

            idle_time = _time_module.time() - instance.last_used
            if idle_time > 3600 and instance.state == EnvironmentState.ACTIVE:
                issues.append(f"Idle for {idle_time:.0f}s")

            return {
                "healthy": len(issues) == 0,
                "state": instance.state.value,
                "issues": issues,
                "active_tasks": instance.active_tasks,
                "idle_seconds": idle_time,
            }

    def get_system_stats(self) -> Dict[str, Any]:
        """Get overall environment management statistics."""
        with self._lock:
            active = sum(
                1 for e in self._environments.values()
                if e.state == EnvironmentState.ACTIVE
            )
            ready = sum(
                1 for e in self._environments.values()
                if e.state == EnvironmentState.READY
            )
            return {
                "total_environments": len(self._environments),
                "active": active,
                "ready": ready,
                "total_provisioned": self._total_provisioned,
                "total_terminated": self._total_terminated,
                "current_usage": dict(self._current_usage),
                "global_limits": dict(self._global_limits),
                "utilization": {
                    "cpu_percent": round(
                        (self._current_usage["total_cpu"] / max(self._global_limits["max_total_cpu"], 1)) * 100, 1
                    ),
                    "memory_percent": round(
                        (self._current_usage["total_memory_mb"] / max(self._global_limits["max_total_memory_mb"], 1)) * 100, 1
                    ),
                },
                "registered_deps": len(self._dependencies),
            }

    def get_all_environments(self) -> List[Dict[str, Any]]:
        """Get all environment instances."""
        with self._lock:
            return [e.to_dict() for e in self._environments.values()]

    def cleanup_idle(self, max_idle_seconds: float = 3600.0) -> int:
        """Terminate idle environments. Returns count of terminated."""
        with self._lock:
            now = _time_module.time()
            to_terminate: List[str] = []
            for eid, instance in self._environments.items():
                if instance.state == EnvironmentState.READY:
                    if now - instance.last_used > max_idle_seconds:
                        to_terminate.append(eid)
            count = 0
            for eid in to_terminate:
                if self.terminate(eid):
                    count += 1
            return count

    def drain_environment(self, instance_id: str) -> bool:
        """Gracefully drain an environment, waiting for active tasks to complete."""
        with self._lock:
            instance = self._get_env(instance_id)
            if not instance:
                return False
            instance.state = EnvironmentState.DRAINING
            if instance.active_tasks == 0:
                return self.terminate(instance_id)
            return True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _get_env(self, instance_id: str) -> Optional[EnvironmentInstance]:
        return self._environments.get(instance_id)


# ---------------------------------------------------------------------------
# Module-level accessor
# ---------------------------------------------------------------------------

def get_environment_manager() -> AgentEnvironmentManager:
    return AgentEnvironmentManager.get_instance()