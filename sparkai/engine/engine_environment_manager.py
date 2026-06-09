"""
SparkLabs Engine - Environment Manager

Engine-level runtime environment lifecycle management for the
AI-native game engine. Handles environment provisioning, platform
configuration, resource allocation, dependency resolution, and
sandbox isolation for engine subsystems.

Architecture:
  EngineEnvironmentManager
    |-- EnvironmentProfile (per-platform runtime configuration)
    |-- ResourceAllocator (CPU/memory/GPU budget management)
    |-- DependencyResolver (plugin/module dependency graph)
    |-- SandboxController (isolated subsystem execution)
    |-- PlatformDetector (OS/hardware capability detection)
    |-- EnvVariableStore (environment variable management)
"""

from __future__ import annotations

import os
import platform
import threading
import time as _time_module
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlatformType(str, Enum):
    """Operating system platform."""
    WINDOWS = "windows"
    MACOS = "macos"
    LINUX = "linux"
    WEB = "web"
    ANDROID = "android"
    IOS = "ios"
    UNKNOWN = "unknown"


class ArchitectureType(str, Enum):
    """CPU architecture."""
    X86_64 = "x86_64"
    ARM64 = "arm64"
    X86 = "x86"
    ARM = "arm"
    WASM = "wasm"
    UNKNOWN = "unknown"


class EnvironmentProfile(str, Enum):
    """Runtime environment profile."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"
    HEADLESS = "headless"


class ResourceCategory(str, Enum):
    """Resource allocation categories."""
    RENDERING = "rendering"
    PHYSICS = "physics"
    AUDIO = "audio"
    AI = "ai"
    NETWORK = "network"
    IO = "io"
    GENERAL = "general"
    CUSTOM = "custom"


class SubsystemType(str, Enum):
    """Engine subsystem types."""
    RENDER = "render"
    PHYSICS = "physics"
    AUDIO = "audio"
    INPUT = "input"
    NETWORK = "network"
    AI = "ai"
    SCRIPT = "script"
    ASSET = "asset"
    SCENE = "scene"
    UI = "ui"
    CUSTOM = "custom"


class DependencyStatus(str, Enum):
    """Dependency resolution status."""
    RESOLVED = "resolved"
    MISSING = "missing"
    INCOMPATIBLE = "incompatible"
    OPTIONAL = "optional"
    CONFLICT = "conflict"


class IsolationLevel(str, Enum):
    """Sandbox isolation level."""
    NONE = "none"
    PROCESS = "process"
    THREAD = "thread"
    CONTAINER = "container"
    FULL = "full"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class PlatformInfo:
    """Detected platform information."""
    os_type: PlatformType = PlatformType.UNKNOWN
    architecture: ArchitectureType = ArchitectureType.UNKNOWN
    os_version: str = ""
    python_version: str = ""
    cpu_count: int = 1
    total_memory_mb: float = 0.0
    gpu_available: bool = False
    gpu_name: str = ""
    display_count: int = 1
    hostname: str = ""
    detected_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "os_type": self.os_type.value,
            "architecture": self.architecture.value,
            "os_version": self.os_version,
            "python_version": self.python_version,
            "cpu_count": self.cpu_count,
            "total_memory_mb": self.total_memory_mb,
            "gpu_available": self.gpu_available,
            "gpu_name": self.gpu_name,
            "display_count": self.display_count,
            "hostname": self.hostname,
            "detected_at": self.detected_at,
        }


@dataclass
class ResourceBudget:
    """Resource allocation budget for a subsystem."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: ResourceCategory = ResourceCategory.GENERAL
    cpu_cores: float = 1.0
    memory_mb: float = 256.0
    gpu_memory_mb: float = 0.0
    priority: int = 0
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "cpu_cores": self.cpu_cores,
            "memory_mb": self.memory_mb,
            "gpu_memory_mb": self.gpu_memory_mb,
            "priority": self.priority,
            "enabled": self.enabled,
        }


@dataclass
class DependencyNode:
    """A node in the dependency graph."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    version: str = "1.0.0"
    subsystem: SubsystemType = SubsystemType.CUSTOM
    status: DependencyStatus = DependencyStatus.RESOLVED
    dependencies: List[str] = field(default_factory=list)
    optional: bool = False
    loaded: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "subsystem": self.subsystem.value,
            "status": self.status.value,
            "dependencies": self.dependencies,
            "optional": self.optional,
            "loaded": self.loaded,
            "metadata": self.metadata,
        }


@dataclass
class SandboxConfig:
    """Sandbox configuration for subsystem isolation."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    subsystem: SubsystemType = SubsystemType.CUSTOM
    isolation_level: IsolationLevel = IsolationLevel.NONE
    max_memory_mb: float = 512.0
    max_cpu_time_ms: float = 10000.0
    allowed_paths: List[str] = field(default_factory=list)
    denied_paths: List[str] = field(default_factory=list)
    network_access: bool = False
    file_access: bool = True
    env_vars: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "subsystem": self.subsystem.value,
            "isolation_level": self.isolation_level.value,
            "max_memory_mb": self.max_memory_mb,
            "max_cpu_time_ms": self.max_cpu_time_ms,
            "allowed_paths": self.allowed_paths,
            "denied_paths": self.denied_paths,
            "network_access": self.network_access,
            "file_access": self.file_access,
            "env_vars": self.env_vars,
        }


@dataclass
class EnvironmentSnapshot:
    """Complete snapshot of the engine environment state."""
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
    platform: PlatformInfo = field(default_factory=PlatformInfo)
    budgets: List[ResourceBudget] = field(default_factory=list)
    dependencies: List[DependencyNode] = field(default_factory=list)
    sandboxes: List[SandboxConfig] = field(default_factory=list)
    env_variables: Dict[str, str] = field(default_factory=dict)
    startup_time: float = 0.0
    uptime_seconds: float = 0.0
    created_at: float = field(default_factory=_time_module.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "profile": self.profile.value,
            "platform": self.platform.to_dict(),
            "budgets": [b.to_dict() for b in self.budgets],
            "dependencies": [d.to_dict() for d in self.dependencies],
            "sandboxes": [s.to_dict() for s in self.sandboxes],
            "env_variables": self.env_variables,
            "startup_time": self.startup_time,
            "uptime_seconds": self.uptime_seconds,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# EngineEnvironmentManager
# ---------------------------------------------------------------------------

class EngineEnvironmentManager:
    """
    Engine-level environment lifecycle manager for the SparkLabs
    AI-native game engine.

    Manages the complete runtime environment: platform detection,
    resource allocation, dependency resolution, sandbox isolation,
    and environment variable configuration.
    """

    _instance: Optional["EngineEnvironmentManager"] = None
    _lock = threading.RLock()

    def __new__(cls) -> "EngineEnvironmentManager":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        self._profile: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT
        self._platform: PlatformInfo = self._detect_platform()
        self._budgets: Dict[str, ResourceBudget] = {}
        self._dependencies: Dict[str, DependencyNode] = {}
        self._sandboxes: Dict[str, SandboxConfig] = {}
        self._env_variables: Dict[str, str] = {}
        self._snapshots: List[EnvironmentSnapshot] = []
        self._startup_time: float = _time_module.time()
        self._initialized_subsystems: Set[str] = set()
        self._health_status: Dict[str, bool] = {}

        self._init_defaults()

    # ------------------------------------------------------------------
    # Platform Detection
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_platform() -> PlatformInfo:
        """Detect the current platform information."""
        system = platform.system().lower()
        arch = platform.machine().lower()

        if system == "darwin":
            os_type = PlatformType.MACOS
        elif system == "windows":
            os_type = PlatformType.WINDOWS
        elif system == "linux":
            os_type = PlatformType.LINUX
        else:
            os_type = PlatformType.UNKNOWN

        if arch in ("x86_64", "amd64"):
            arch_type = ArchitectureType.X86_64
        elif arch in ("arm64", "aarch64"):
            arch_type = ArchitectureType.ARM64
        elif arch == "x86":
            arch_type = ArchitectureType.X86
        elif arch.startswith("arm"):
            arch_type = ArchitectureType.ARM
        else:
            arch_type = ArchitectureType.UNKNOWN

        cpu_count = os.cpu_count() or 1

        try:
            import psutil
            total_memory = psutil.virtual_memory().total / (1024 * 1024)
        except ImportError:
            total_memory = cpu_count * 1024.0

        return PlatformInfo(
            os_type=os_type,
            architecture=arch_type,
            os_version=platform.version(),
            python_version=platform.python_version(),
            cpu_count=cpu_count,
            total_memory_mb=total_memory,
            gpu_available=False,
            hostname=platform.node(),
        )

    def get_platform_info(self) -> Dict[str, Any]:
        """Get current platform information."""
        return self._platform.to_dict()

    def refresh_platform_info(self) -> Dict[str, Any]:
        """Re-detect platform information."""
        self._platform = self._detect_platform()
        return self._platform.to_dict()

    # ------------------------------------------------------------------
    # Environment Profile Management
    # ------------------------------------------------------------------

    def set_profile(self, profile: str) -> None:
        """Set the active environment profile."""
        self._profile = EnvironmentProfile(profile)

    def get_profile(self) -> str:
        """Get the current environment profile."""
        return self._profile.value

    # ------------------------------------------------------------------
    # Resource Budget Management
    # ------------------------------------------------------------------

    def _init_defaults(self) -> None:
        """Initialize default resource budgets based on platform."""
        cpu_count = self._platform.cpu_count
        total_mem = self._platform.total_memory_mb

        default_budgets = [
            (ResourceCategory.RENDERING, cpu_count * 0.5, total_mem * 0.3, 10),
            (ResourceCategory.PHYSICS, cpu_count * 0.2, total_mem * 0.1, 8),
            (ResourceCategory.AUDIO, cpu_count * 0.05, total_mem * 0.05, 5),
            (ResourceCategory.AI, cpu_count * 0.15, total_mem * 0.2, 7),
            (ResourceCategory.NETWORK, cpu_count * 0.05, total_mem * 0.05, 4),
            (ResourceCategory.IO, cpu_count * 0.05, total_mem * 0.1, 3),
            (ResourceCategory.GENERAL, cpu_count * 0.0, total_mem * 0.2, 1),
        ]

        for category, cpu, mem, priority in default_budgets:
            budget = ResourceBudget(
                category=category,
                cpu_cores=cpu,
                memory_mb=mem,
                priority=priority,
            )
            self._budgets[budget.id] = budget

    def create_resource_budget(
        self,
        category: str,
        cpu_cores: float = 1.0,
        memory_mb: float = 256.0,
        gpu_memory_mb: float = 0.0,
        priority: int = 0,
    ) -> ResourceBudget:
        """Create a custom resource budget."""
        budget = ResourceBudget(
            category=ResourceCategory(category),
            cpu_cores=cpu_cores,
            memory_mb=memory_mb,
            gpu_memory_mb=gpu_memory_mb,
            priority=priority,
        )
        self._budgets[budget.id] = budget
        return budget

    def get_resource_budget(self, budget_id: str) -> Optional[Dict[str, Any]]:
        """Get a resource budget by ID."""
        budget = self._budgets.get(budget_id)
        return budget.to_dict() if budget else None

    def list_resource_budgets(self) -> List[Dict[str, Any]]:
        """List all resource budgets."""
        return [b.to_dict() for b in self._budgets.values()]

    def get_resource_usage(self) -> Dict[str, Any]:
        """Get current resource usage statistics."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            cpu_percent = psutil.cpu_percent(interval=0.1)
            return {
                "cpu_percent": cpu_percent,
                "memory_used_mb": mem.used / (1024 * 1024),
                "memory_total_mb": mem.total / (1024 * 1024),
                "memory_percent": mem.percent,
                "cpu_count": self._platform.cpu_count,
            }
        except ImportError:
            return {
                "cpu_percent": 0.0,
                "memory_used_mb": 0.0,
                "memory_total_mb": self._platform.total_memory_mb,
                "memory_percent": 0.0,
                "cpu_count": self._platform.cpu_count,
            }

    # ------------------------------------------------------------------
    # Dependency Management
    # ------------------------------------------------------------------

    def register_dependency(
        self,
        name: str,
        version: str = "1.0.0",
        subsystem: str = "custom",
        dependencies: Optional[List[str]] = None,
        optional: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DependencyNode:
        """Register a subsystem dependency."""
        node = DependencyNode(
            name=name,
            version=version,
            subsystem=SubsystemType(subsystem),
            dependencies=dependencies or [],
            optional=optional,
            metadata=metadata or {},
        )
        self._dependencies[node.id] = node
        return node

    def resolve_dependency(self, dependency_id: str) -> bool:
        """Resolve a dependency and its transitive dependencies."""
        node = self._dependencies.get(dependency_id)
        if not node:
            return False

        unresolved = set()
        self._resolve_tree(node, unresolved, set())

        if unresolved:
            node.status = DependencyStatus.MISSING
            return False

        node.status = DependencyStatus.RESOLVED
        node.loaded = True
        self._initialized_subsystems.add(node.subsystem.value)
        return True

    def _resolve_tree(
        self,
        node: DependencyNode,
        unresolved: Set[str],
        visited: Set[str],
    ) -> None:
        """Recursively resolve dependency tree."""
        if node.id in visited:
            return
        visited.add(node.id)

        for dep_id in node.dependencies:
            dep = self._dependencies.get(dep_id)
            if dep is None:
                unresolved.add(dep_id)
                continue
            if dep.status == DependencyStatus.MISSING and not dep.optional:
                unresolved.add(dep_id)
            self._resolve_tree(dep, unresolved, visited)

    def get_dependency(self, dependency_id: str) -> Optional[Dict[str, Any]]:
        """Get dependency information."""
        node = self._dependencies.get(dependency_id)
        return node.to_dict() if node else None

    def list_dependencies(
        self,
        subsystem: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List dependencies with optional filtering."""
        deps = list(self._dependencies.values())
        if subsystem:
            st = SubsystemType(subsystem)
            deps = [d for d in deps if d.subsystem == st]
        if status:
            ds = DependencyStatus(status)
            deps = [d for d in deps if d.status == ds]
        return [d.to_dict() for d in deps]

    def get_dependency_graph(self) -> Dict[str, Any]:
        """Get the full dependency graph for visualization."""
        nodes = []
        edges = []
        for node in self._dependencies.values():
            nodes.append({
                "id": node.id,
                "name": node.name,
                "subsystem": node.subsystem.value,
                "status": node.status.value,
            })
            for dep_id in node.dependencies:
                edges.append({
                    "from": node.id,
                    "to": dep_id,
                })
        return {"nodes": nodes, "edges": edges}

    # ------------------------------------------------------------------
    # Sandbox Management
    # ------------------------------------------------------------------

    def create_sandbox(
        self,
        subsystem: str,
        isolation_level: str = "none",
        max_memory_mb: float = 512.0,
        max_cpu_time_ms: float = 10000.0,
        allowed_paths: Optional[List[str]] = None,
        denied_paths: Optional[List[str]] = None,
        network_access: bool = False,
    ) -> SandboxConfig:
        """Create a sandbox for a subsystem."""
        sandbox = SandboxConfig(
            subsystem=SubsystemType(subsystem),
            isolation_level=IsolationLevel(isolation_level),
            max_memory_mb=max_memory_mb,
            max_cpu_time_ms=max_cpu_time_ms,
            allowed_paths=allowed_paths or [],
            denied_paths=denied_paths or [],
            network_access=network_access,
        )
        self._sandboxes[sandbox.id] = sandbox
        return sandbox

    def get_sandbox(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get sandbox configuration."""
        sandbox = self._sandboxes.get(sandbox_id)
        return sandbox.to_dict() if sandbox else None

    def list_sandboxes(self, subsystem: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all sandboxes."""
        sandboxes = list(self._sandboxes.values())
        if subsystem:
            st = SubsystemType(subsystem)
            sandboxes = [s for s in sandboxes if s.subsystem == st]
        return [s.to_dict() for s in sandboxes]

    # ------------------------------------------------------------------
    # Environment Variables
    # ------------------------------------------------------------------

    def set_env(self, key: str, value: str) -> None:
        """Set an environment variable."""
        self._env_variables[key] = value
        os.environ[key] = value

    def get_env(self, key: str, default: str = "") -> str:
        """Get an environment variable."""
        return self._env_variables.get(key, os.environ.get(key, default))

    def list_env_variables(self) -> Dict[str, str]:
        """List all managed environment variables."""
        return dict(self._env_variables)

    def delete_env(self, key: str) -> bool:
        """Remove an environment variable."""
        if key in self._env_variables:
            del self._env_variables[key]
            if key in os.environ:
                del os.environ[key]
            return True
        return False

    # ------------------------------------------------------------------
    # Subsystem Management
    # ------------------------------------------------------------------

    def initialize_subsystem(self, subsystem: str) -> Dict[str, Any]:
        """Initialize a named subsystem with its dependencies."""
        st = SubsystemType(subsystem)

        deps = [d for d in self._dependencies.values() if d.subsystem == st]
        resolved = 0
        failed = 0

        for dep in deps:
            if self.resolve_dependency(dep.id):
                resolved += 1
            else:
                failed += 1

        if resolved > 0:
            self._initialized_subsystems.add(subsystem)

        return {
            "subsystem": subsystem,
            "total_deps": len(deps),
            "resolved": resolved,
            "failed": failed,
            "initialized": subsystem in self._initialized_subsystems,
        }

    def is_subsystem_initialized(self, subsystem: str) -> bool:
        """Check if a subsystem has been initialized."""
        return subsystem in self._initialized_subsystems

    def list_initialized_subsystems(self) -> List[str]:
        """List all initialized subsystems."""
        return sorted(self._initialized_subsystems)

    # ------------------------------------------------------------------
    # Snapshot Management
    # ------------------------------------------------------------------

    def create_snapshot(self) -> EnvironmentSnapshot:
        """Create a snapshot of the current environment state."""
        snapshot = EnvironmentSnapshot(
            profile=self._profile,
            platform=self._platform,
            budgets=list(self._budgets.values()),
            dependencies=list(self._dependencies.values()),
            sandboxes=list(self._sandboxes.values()),
            env_variables=dict(self._env_variables),
            startup_time=self._startup_time,
            uptime_seconds=_time_module.time() - self._startup_time,
        )
        self._snapshots.append(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get the most recent environment snapshot."""
        if self._snapshots:
            return self._snapshots[-1].to_dict()
        return None

    def list_snapshots(self) -> List[Dict[str, Any]]:
        """List all environment snapshots."""
        return [s.to_dict() for s in self._snapshots]

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------

    def check_health(self) -> Dict[str, Any]:
        """Perform a health check on the environment."""
        issues = []

        cpu_count = self._platform.cpu_count
        if cpu_count < 1:
            issues.append("No CPU cores detected")

        total_mem = self._platform.total_memory_mb
        if total_mem < 256:
            issues.append(f"Low memory: {total_mem:.0f}MB")

        total_reserved = sum(b.memory_mb for b in self._budgets.values())
        if total_reserved > total_mem:
            issues.append(f"Over-allocated memory: reserved {total_reserved:.0f}MB of {total_mem:.0f}MB")

        missing_deps = [
            d.name for d in self._dependencies.values()
            if d.status == DependencyStatus.MISSING and not d.optional
        ]
        if missing_deps:
            issues.append(f"Missing dependencies: {', '.join(missing_deps)}")

        return {
            "healthy": len(issues) == 0,
            "issues": issues,
            "profile": self._profile.value,
            "uptime_seconds": _time_module.time() - self._startup_time,
            "initialized_subsystems": sorted(self._initialized_subsystems),
            "total_dependencies": len(self._dependencies),
            "total_sandboxes": len(self._sandboxes),
        }

    # ------------------------------------------------------------------
    # System Statistics
    # ------------------------------------------------------------------

    def get_system_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        return {
            "platform": self._platform.to_dict(),
            "profile": self._profile.value,
            "uptime_seconds": _time_module.time() - self._startup_time,
            "budgets": {
                "total": len(self._budgets),
                "total_reserved_memory_mb": sum(b.memory_mb for b in self._budgets.values()),
                "total_reserved_cpu": sum(b.cpu_cores for b in self._budgets.values()),
            },
            "dependencies": {
                "total": len(self._dependencies),
                "resolved": sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.RESOLVED),
                "missing": sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.MISSING),
                "incompatible": sum(1 for d in self._dependencies.values() if d.status == DependencyStatus.INCOMPATIBLE),
            },
            "sandboxes": {
                "total": len(self._sandboxes),
                "by_level": {
                    level.value: sum(1 for s in self._sandboxes.values() if s.isolation_level == level)
                    for level in IsolationLevel
                },
            },
            "initialized_subsystems": sorted(self._initialized_subsystems),
            "env_variables_count": len(self._env_variables),
            "snapshots_count": len(self._snapshots),
            "resource_usage": self.get_resource_usage(),
        }


# ---------------------------------------------------------------------------
# Global Accessor
# ---------------------------------------------------------------------------

def get_engine_environment_manager() -> EngineEnvironmentManager:
    """Get the global EngineEnvironmentManager singleton."""
    return EngineEnvironmentManager()