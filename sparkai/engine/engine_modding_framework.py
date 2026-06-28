"""
SparkLabs Engine - Modding Framework

A comprehensive modding framework for the SparkLabs AI-native game engine.
Provides mod loading, sandboxed execution, version compatibility checking,
asset replacement, script hooking, and a modding API surface for community
content creation.

Architecture:
  ModdingFramework (Singleton)
    |-- ModConfig              — configuration for mod loading
    |-- ModDescriptor         — mod metadata descriptor
    |-- ModDependency         — a declared dependency on another mod
    |-- ModConflict           — a detected conflict between mods
    |-- ModAPI                — modding API surface granted to a loaded mod
    |-- ModdingFrameworkSnapshot — complete modding system snapshot

Framework Features:
  - REGISTRY:  register, query, and manage community mods
  - LIFECYCLE: load, unload, enable, disable mods with state machine
  - ORDERING:  resolve load order based on dependencies and load phases
  - CONFLICTS: detect asset/script conflicts and resolve with strategies
  - SANDBOX:   isolated execution context with permission scoping
  - HOOKS:     script hook registration and invocation pipeline
  - ASSETS:    asset replacement registry with override precedence
  - VERSION:   semantic version compatibility checking
  - API:       stable modding API surface for community content

Usage:
    fw = get_modding_framework()
    fw.initialize(ModConfig(mods_directory="mods", sandbox_enabled=True))
    descriptor = ModDescriptor(mod_id="my_mod", name="My Mod", version="1.0.0")
    fw.register_mod(descriptor)
    fw.load_mod("my_mod")
    fw.enable_mod("my_mod")
    snapshot = fw.get_status()
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ModState(Enum):
    """Lifecycle state of a mod within the framework."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    CONFLICT = "conflict"


class ModType(Enum):
    """Classification of a mod by the kind of content it provides."""
    CONTENT = "content"
    CODE = "code"
    ASSET = "asset"
    TOTAL_CONVERSION = "total_conversion"
    LIBRARY = "library"
    CONFIG = "config"


class LoadOrder(Enum):
    """Phase in the engine lifecycle when a mod should be loaded."""
    BEFORE_ENGINE = "before_engine"
    AFTER_ENGINE = "after_engine"
    BEFORE_GAME = "before_game"
    AFTER_GAME = "after_game"
    ON_DEMAND = "on_demand"


class ConflictResolution(Enum):
    """Strategy for resolving a conflict between two mods."""
    FIRST_WINS = "first_wins"
    LAST_WINS = "last_wins"
    MERGE = "merge"
    REPORT = "report"
    AUTO_RESOLVE = "auto_resolve"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------

@dataclass
class ModConfig:
    """Configuration parameters governing mod loading behavior."""
    mods_directory: str = "mods"
    sandbox_enabled: bool = True
    auto_load_dependencies: bool = True
    auto_resolve_conflicts: bool = False
    default_load_order: LoadOrder = LoadOrder.AFTER_ENGINE
    default_conflict_strategy: ConflictResolution = ConflictResolution.REPORT
    enable_hot_reload: bool = False
    max_loaded_mods: int = 128
    allowed_permissions: List[str] = field(default_factory=lambda: [
        "read_assets", "register_hooks", "provide_content",
    ])
    engine_version: str = "1.0.0"
    signature_verification: bool = False
    trusted_authors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            mods_directory=self.mods_directory,
            sandbox_enabled=self.sandbox_enabled,
            auto_load_dependencies=self.auto_load_dependencies,
            auto_resolve_conflicts=self.auto_resolve_conflicts,
            default_load_order=self.default_load_order.value,
            default_conflict_strategy=self.default_conflict_strategy.value,
            enable_hot_reload=self.enable_hot_reload,
            max_loaded_mods=self.max_loaded_mods,
            allowed_permissions=list(self.allowed_permissions),
            engine_version=self.engine_version,
            signature_verification=self.signature_verification,
            trusted_authors=list(self.trusted_authors),
            metadata=dict(self.metadata),
        )


@dataclass
class ModDescriptor:
    """Metadata descriptor describing a mod and its declarations."""
    mod_id: str = ""
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    mod_type: ModType = ModType.CONTENT
    load_order: LoadOrder = LoadOrder.AFTER_ENGINE
    entry_point: str = ""
    homepage_url: str = ""
    repository_url: str = ""
    license_name: str = "MIT"
    min_engine_version: str = "1.0.0"
    max_engine_version: str = ""
    dependencies: List["ModDependency"] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    asset_overrides: List[str] = field(default_factory=list)
    script_hooks: List[str] = field(default_factory=list)
    priority: int = 0
    is_signed: bool = False
    checksum: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            mod_id=self.mod_id,
            name=self.name,
            version=self.version,
            author=self.author,
            description=self.description,
            mod_type=self.mod_type.value,
            load_order=self.load_order.value,
            entry_point=self.entry_point,
            homepage_url=self.homepage_url,
            repository_url=self.repository_url,
            license_name=self.license_name,
            min_engine_version=self.min_engine_version,
            max_engine_version=self.max_engine_version,
            dependencies=[d.to_dict() for d in self.dependencies],
            conflicts=list(self.conflicts),
            tags=list(self.tags),
            permissions=list(self.permissions),
            asset_overrides=list(self.asset_overrides),
            script_hooks=list(self.script_hooks),
            priority=self.priority,
            is_signed=self.is_signed,
            checksum=self.checksum,
            created_at=self.created_at,
            updated_at=self.updated_at,
            metadata=dict(self.metadata),
        )


@dataclass
class ModDependency:
    """A declared dependency of a mod on another mod or engine component."""
    dependency_id: str = ""
    version_requirement: str = ">=1.0.0"
    is_optional: bool = False
    is_resolved: bool = False
    resolved_version: str = ""
    dependency_type: str = "mod"

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            dependency_id=self.dependency_id,
            version_requirement=self.version_requirement,
            is_optional=self.is_optional,
            is_resolved=self.is_resolved,
            resolved_version=self.resolved_version,
            dependency_type=self.dependency_type,
        )


@dataclass
class ModConflict:
    """A detected conflict between two mods over a shared resource."""
    conflict_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mod_id_a: str = ""
    mod_id_b: str = ""
    resource_key: str = ""
    resource_type: str = "asset"
    description: str = ""
    strategy: ConflictResolution = ConflictResolution.REPORT
    winner: str = ""
    is_resolved: bool = False
    detected_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            conflict_id=self.conflict_id,
            mod_id_a=self.mod_id_a,
            mod_id_b=self.mod_id_b,
            resource_key=self.resource_key,
            resource_type=self.resource_type,
            description=self.description,
            strategy=self.strategy.value,
            winner=self.winner,
            is_resolved=self.is_resolved,
            detected_at=self.detected_at,
            resolved_at=self.resolved_at,
            metadata=dict(self.metadata),
        )


@dataclass
class ModAPI:
    """The modding API surface granted to a loaded mod.

    Provides a controlled interface through which mod code can interact
    with the engine: register hooks, declare asset overrides, emit
    events, and query engine state without compromising the sandbox.
    """
    api_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    mod_id: str = ""
    permissions: List[str] = field(default_factory=list)
    registered_hooks: List[str] = field(default_factory=list)
    declared_overrides: List[str] = field(default_factory=list)
    emitted_events: int = 0
    api_version: str = "1.0.0"
    is_sandboxed: bool = True
    granted_at: float = field(default_factory=time.time)
    revoked_at: float = 0.0
    is_active: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            api_id=self.api_id,
            mod_id=self.mod_id,
            permissions=list(self.permissions),
            registered_hooks=list(self.registered_hooks),
            declared_overrides=list(self.declared_overrides),
            emitted_events=self.emitted_events,
            api_version=self.api_version,
            is_sandboxed=self.is_sandboxed,
            granted_at=self.granted_at,
            revoked_at=self.revoked_at,
            is_active=self.is_active,
            metadata=dict(self.metadata),
        )

    def grant_permission(self, permission: str) -> None:
        """Grant a permission to this API instance if not already present."""
        if permission and permission not in self.permissions:
            self.permissions.append(permission)

    def revoke(self) -> None:
        """Mark this API instance as revoked and inactive."""
        self.is_active = False
        self.revoked_at = time.time()


@dataclass
class ModdingFrameworkSnapshot:
    """Complete snapshot of the modding framework state at a point in time."""
    is_initialized: bool = False
    config: Dict[str, Any] = field(default_factory=dict)
    registered_mods: List[Dict[str, Any]] = field(default_factory=list)
    loaded_mods: List[Dict[str, Any]] = field(default_factory=list)
    enabled_mods: List[str] = field(default_factory=list)
    load_order: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)
    unresolved_conflicts: int = 0
    apis: List[Dict[str, Any]] = field(default_factory=list)
    asset_overrides: Dict[str, str] = field(default_factory=dict)
    script_hooks: Dict[str, List[str]] = field(default_factory=dict)
    state_counts: Dict[str, int] = field(default_factory=dict)
    captured_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            is_initialized=self.is_initialized,
            config=dict(self.config),
            registered_mods=list(self.registered_mods),
            loaded_mods=list(self.loaded_mods),
            enabled_mods=list(self.enabled_mods),
            load_order=list(self.load_order),
            conflicts=list(self.conflicts),
            unresolved_conflicts=self.unresolved_conflicts,
            apis=list(self.apis),
            asset_overrides=dict(self.asset_overrides),
            script_hooks={k: list(v) for k, v in self.script_hooks.items()},
            state_counts=dict(self.state_counts),
            captured_at=self.captured_at,
        )


# ---------------------------------------------------------------------------
# Internal Runtime Record
# ---------------------------------------------------------------------------

@dataclass
class _ModRuntime:
    """Internal runtime tracking record for a registered mod."""
    descriptor: ModDescriptor
    state: ModState = ModState.UNLOADED
    loaded_at: float = 0.0
    enabled_at: float = 0.0
    error_message: str = ""
    api: Optional[ModAPI] = None
    instance_ref: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            mod_id=self.descriptor.mod_id,
            name=self.descriptor.name,
            version=self.descriptor.version,
            state=self.state.value,
            loaded_at=self.loaded_at,
            enabled_at=self.enabled_at,
            error_message=self.error_message,
            api=self.api.to_dict() if self.api else None,
        )


# ---------------------------------------------------------------------------
# Main Class: ModdingFramework
# ---------------------------------------------------------------------------

class ModdingFramework:
    """Singleton modding framework managing the full mod lifecycle.

    Provides mod registration, dependency-aware load order resolution,
    conflict detection and resolution, sandboxed API distribution, and
    asset/script hook registries. All public methods are thread-safe.
    """

    _instance: Optional["ModdingFramework"] = None
    _lock = threading.RLock()

    MAX_CONFLICT_LOG = 256
    MAX_HOOK_RESULTS = 128

    def __init__(self) -> None:
        self._config: Optional[ModConfig] = None
        self._registry: Dict[str, _ModRuntime] = {}
        self._load_order: List[str] = []
        self._conflicts: List[ModConflict] = []
        self._asset_overrides: Dict[str, str] = {}
        self._script_hooks: Dict[str, List[Tuple[str, Callable[..., Any]]]] = {}
        self._apis: Dict[str, ModAPI] = {}
        self._is_initialized: bool = False
        self._operation_lock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton access
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls) -> "ModdingFramework":
        """Get the singleton ModdingFramework instance (double-checked locking)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def initialize(self, config: Optional[ModConfig] = None) -> bool:
        """Initialize the modding framework with the given configuration."""
        with self._operation_lock:
            if self._is_initialized:
                return True
            self._config = config or ModConfig()
            self._is_initialized = True
            return True

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_mod(self, descriptor: ModDescriptor) -> bool:
        """Register a mod descriptor with the framework."""
        if not descriptor.mod_id:
            return False
        with self._operation_lock:
            if descriptor.mod_id in self._registry:
                return False
            runtime = _ModRuntime(descriptor=descriptor)
            self._registry[descriptor.mod_id] = runtime
            for hook_name in descriptor.script_hooks:
                self._script_hooks.setdefault(hook_name, [])
            return True

    # ------------------------------------------------------------------
    # Loading / Unloading
    # ------------------------------------------------------------------

    def load_mod(self, mod_id: str) -> bool:
        """Load a specific mod by transitioning it to the LOADED state."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None:
                return False
            if runtime.state in (ModState.LOADED, ModState.ENABLED):
                return True
            if runtime.state == ModState.ERROR:
                runtime.error_message = ""
            if len(self._loaded_mods_ids()) >= self._effective_max_mods():
                runtime.state = ModState.ERROR
                runtime.error_message = "Maximum loaded mod count reached"
                return False
            runtime.state = ModState.LOADING
            if not self._check_dependencies(mod_id):
                runtime.state = ModState.ERROR
                runtime.error_message = "Unresolved required dependencies"
                return False
            if not self._check_engine_compatibility(runtime.descriptor):
                runtime.state = ModState.ERROR
                runtime.error_message = "Incompatible with engine version"
                return False
            runtime.loaded_at = time.time()
            runtime.state = ModState.LOADED
            self._register_overrides(mod_id)
            self._grant_api(mod_id)
            if mod_id not in self._load_order:
                self._load_order.append(mod_id)
            return True

    def unload_mod(self, mod_id: str) -> bool:
        """Unload a mod and release its associated resources."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None:
                return False
            if runtime.state == ModState.UNLOADED:
                return True
            dependents = self._find_dependents(mod_id)
            if dependents:
                runtime.state = ModState.ERROR
                runtime.error_message = (
                    f"Cannot unload: required by {', '.join(dependents)}"
                )
                return False
            self._revoke_api(mod_id)
            self._remove_overrides(mod_id)
            self._remove_hooks(mod_id)
            runtime.state = ModState.UNLOADED
            runtime.loaded_at = 0.0
            runtime.enabled_at = 0.0
            if mod_id in self._load_order:
                self._load_order.remove(mod_id)
            return True

    # ------------------------------------------------------------------
    # Enable / Disable
    # ------------------------------------------------------------------

    def enable_mod(self, mod_id: str) -> bool:
        """Enable a loaded mod, making its hooks and overrides active."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None:
                return False
            if runtime.state == ModState.ENABLED:
                return True
            if runtime.state != ModState.LOADED:
                if not self.load_mod(mod_id):
                    return False
            runtime.state = ModState.ENABLED
            runtime.enabled_at = time.time()
            if runtime.api is not None:
                runtime.api.is_active = True
            return True

    def disable_mod(self, mod_id: str) -> bool:
        """Disable a mod, suspending its hooks and overrides without unloading."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None:
                return False
            if runtime.state == ModState.DISABLED:
                return True
            if runtime.state not in (ModState.ENABLED, ModState.LOADED, ModState.ERROR):
                return False
            runtime.state = ModState.DISABLED
            if runtime.api is not None:
                runtime.api.is_active = False
            return True

    # ------------------------------------------------------------------
    # Load Order Resolution
    # ------------------------------------------------------------------

    def resolve_load_order(self) -> List[str]:
        """Resolve and return the mod load order based on dependencies and phases."""
        with self._operation_lock:
            order: List[str] = []
            visited: Set[str] = set()
            visiting: Set[str] = set()

            def visit(node: str) -> None:
                if node in visited:
                    return
                if node in visiting:
                    return  # cycle detected; skip to avoid infinite recursion
                visiting.add(node)
                runtime = self._registry.get(node)
                if runtime is not None:
                    for dep in runtime.descriptor.dependencies:
                        if dep.dependency_id in self._registry and not dep.is_optional:
                            visit(dep.dependency_id)
                visiting.discard(node)
                visited.add(node)
                order.append(node)

            phase_order = [
                LoadOrder.BEFORE_ENGINE,
                LoadOrder.AFTER_ENGINE,
                LoadOrder.BEFORE_GAME,
                LoadOrder.AFTER_GAME,
                LoadOrder.ON_DEMAND,
            ]
            for phase in phase_order:
                phase_mods = [
                    mid for mid, rt in self._registry.items()
                    if rt.descriptor.load_order == phase
                ]
                phase_mods.sort(key=lambda m: self._registry[m].descriptor.priority)
                for mid in phase_mods:
                    visit(mid)

            self._load_order = list(order)
            return list(self._load_order)

    # ------------------------------------------------------------------
    # Conflict Detection / Resolution
    # ------------------------------------------------------------------

    def detect_conflicts(self) -> List[ModConflict]:
        """Detect conflicts between loaded mods over shared resources."""
        with self._operation_lock:
            self._conflicts.clear()
            overrides_by_mod: Dict[str, List[str]] = {}
            for mid, runtime in self._registry.items():
                if runtime.state in (ModState.LOADED, ModState.ENABLED):
                    overrides_by_mod[mid] = list(runtime.descriptor.asset_overrides)

            asset_to_mods: Dict[str, List[str]] = {}
            for mid, assets in overrides_by_mod.items():
                for asset in assets:
                    asset_to_mods.setdefault(asset, []).append(mid)

            for asset, mods in asset_to_mods.items():
                if len(mods) < 2:
                    continue
                for i in range(len(mods)):
                    for j in range(i + 1, len(mods)):
                        conflict = ModConflict(
                            mod_id_a=mods[i],
                            mod_id_b=mods[j],
                            resource_key=asset,
                            resource_type="asset",
                            description=(
                                f"Mods '{mods[i]}' and '{mods[j]}' both override "
                                f"asset '{asset}'"
                            ),
                            strategy=self._effective_conflict_strategy(),
                        )
                        self._conflicts.append(conflict)
                        self._mark_conflicted(mods[i])
                        self._mark_conflicted(mods[j])

            explicit = self._detect_explicit_conflicts()
            for c in explicit:
                if not any(
                    existing.resource_key == c.resource_key
                    and {existing.mod_id_a, existing.mod_id_b} == {c.mod_id_a, c.mod_id_b}
                    for existing in self._conflicts
                ):
                    self._conflicts.append(c)

            self._trim_conflict_log()
            return list(self._conflicts)

    def resolve_conflict(self, conflict: ModConflict,
                         strategy: ConflictResolution) -> ModConflict:
        """Resolve a mod conflict using the given strategy."""
        with self._operation_lock:
            conflict.strategy = strategy
            if strategy == ConflictResolution.FIRST_WINS:
                conflict.winner = conflict.mod_id_a
                self._apply_override_winner(conflict.resource_key, conflict.mod_id_a)
            elif strategy == ConflictResolution.LAST_WINS:
                conflict.winner = conflict.mod_id_b
                self._apply_override_winner(conflict.resource_key, conflict.mod_id_b)
            elif strategy == ConflictResolution.MERGE:
                conflict.winner = "merged"
                # Merge keeps both overrides; the asset registry retains the
                # latest declared override while logging both contributors.
            elif strategy == ConflictResolution.REPORT:
                conflict.winner = ""
            elif strategy == ConflictResolution.AUTO_RESOLVE:
                runtime_a = self._registry.get(conflict.mod_id_a)
                runtime_b = self._registry.get(conflict.mod_id_b)
                if runtime_a is not None and runtime_b is not None:
                    winner_mod = (
                        conflict.mod_id_a
                        if runtime_a.descriptor.priority >= runtime_b.descriptor.priority
                        else conflict.mod_id_b
                    )
                else:
                    winner_mod = conflict.mod_id_a
                conflict.winner = winner_mod
                self._apply_override_winner(conflict.resource_key, winner_mod)

            conflict.is_resolved = strategy != ConflictResolution.REPORT
            conflict.resolved_at = time.time() if conflict.is_resolved else 0.0
            if conflict.is_resolved:
                self._clear_conflict_state(conflict.mod_id_a)
                self._clear_conflict_state(conflict.mod_id_b)
            return conflict

    # ------------------------------------------------------------------
    # Modding API
    # ------------------------------------------------------------------

    def get_mod_api(self, mod_id: str) -> Optional[ModAPI]:
        """Get the modding API surface for a loaded mod."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None:
                return None
            if runtime.api is None:
                self._grant_api(mod_id)
            return runtime.api

    def register_script_hook(self, mod_id: str, hook_name: str,
                             handler: Callable[..., Any]) -> bool:
        """Register a script hook handler contributed by a mod."""
        with self._operation_lock:
            runtime = self._registry.get(mod_id)
            if runtime is None or runtime.state == ModState.UNLOADED:
                return False
            hooks = self._script_hooks.setdefault(hook_name, [])
            for existing_mod, _ in hooks:
                if existing_mod == mod_id:
                    return False
            hooks.append((mod_id, handler))
            if runtime.api is not None and hook_name not in runtime.api.registered_hooks:
                runtime.api.registered_hooks.append(hook_name)
            return True

    def invoke_script_hooks(self, hook_name: str, *args: Any,
                            **kwargs: Any) -> List[Any]:
        """Invoke all registered handlers for a script hook in priority order."""
        with self._operation_lock:
            hooks = self._script_hooks.get(hook_name, [])
            results: List[Any] = []
            for mod_id, handler in list(hooks):
                runtime = self._registry.get(mod_id)
                if runtime is None or runtime.state != ModState.ENABLED:
                    continue
                if runtime.api is not None:
                    runtime.api.emitted_events += 1
                try:
                    results.append(handler(*args, **kwargs))
                except Exception as exc:  # noqa: BLE001 - sandbox isolation
                    results.append({"error": str(exc), "mod_id": mod_id})
                if len(results) >= self.MAX_HOOK_RESULTS:
                    break
            return results

    # ------------------------------------------------------------------
    # Query APIs
    # ------------------------------------------------------------------

    def get_loaded_mods(self) -> List[Dict[str, Any]]:
        """Get all currently loaded mods as a list of dictionaries."""
        with self._operation_lock:
            return [
                rt.to_dict() for rt in self._registry.values()
                if rt.state in (ModState.LOADED, ModState.ENABLED)
            ]

    def get_status(self) -> ModdingFrameworkSnapshot:
        """Get a complete snapshot of the modding framework state."""
        with self._operation_lock:
            state_counts: Dict[str, int] = {}
            for runtime in self._registry.values():
                key = runtime.state.value
                state_counts[key] = state_counts.get(key, 0) + 1
            enabled_mods = [
                mid for mid, rt in self._registry.items()
                if rt.state == ModState.ENABLED
            ]
            unresolved = sum(1 for c in self._conflicts if not c.is_resolved)
            snapshot = ModdingFrameworkSnapshot(
                is_initialized=self._is_initialized,
                config=self._config.to_dict() if self._config else {},
                registered_mods=[rt.to_dict() for rt in self._registry.values()],
                loaded_mods=self.get_loaded_mods(),
                enabled_mods=enabled_mods,
                load_order=list(self._load_order),
                conflicts=[c.to_dict() for c in self._conflicts],
                unresolved_conflicts=unresolved,
                apis=[api.to_dict() for api in self._apis.values()],
                asset_overrides=dict(self._asset_overrides),
                script_hooks={
                    name: [mid for mid, _ in hooks]
                    for name, hooks in self._script_hooks.items()
                },
                state_counts=state_counts,
            )
            return snapshot

    # ------------------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------------------

    def shutdown(self) -> bool:
        """Gracefully shut down the modding framework, unloading all mods."""
        with self._operation_lock:
            for mod_id in list(self._load_order):
                self._revoke_api(mod_id)
                self._remove_overrides(mod_id)
                self._remove_hooks(mod_id)
                runtime = self._registry.get(mod_id)
                if runtime is not None:
                    runtime.state = ModState.UNLOADED
                    runtime.loaded_at = 0.0
                    runtime.enabled_at = 0.0
            for runtime in self._registry.values():
                if runtime.api is not None:
                    runtime.api.revoke()
                    runtime.api = None
            self._load_order.clear()
            self._conflicts.clear()
            self._asset_overrides.clear()
            self._script_hooks.clear()
            self._apis.clear()
            self._is_initialized = False
            self._config = None
            return True

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _effective_max_mods(self) -> int:
        """Return the configured maximum number of loaded mods."""
        return self._config.max_loaded_mods if self._config else 128

    def _effective_conflict_strategy(self) -> ConflictResolution:
        """Return the configured default conflict resolution strategy."""
        if self._config is not None:
            return self._config.default_conflict_strategy
        return ConflictResolution.REPORT

    def _loaded_mods_ids(self) -> List[str]:
        """Return the mod IDs currently in LOADED or ENABLED state."""
        return [
            mid for mid, rt in self._registry.items()
            if rt.state in (ModState.LOADED, ModState.ENABLED)
        ]

    def _check_dependencies(self, mod_id: str) -> bool:
        """Verify that all required dependencies of a mod are available."""
        runtime = self._registry.get(mod_id)
        if runtime is None:
            return False
        for dep in runtime.descriptor.dependencies:
            if dep.is_optional:
                continue
            dep_runtime = self._registry.get(dep.dependency_id)
            if dep_runtime is None:
                dep.is_resolved = False
                dep.resolved_version = ""
                return False
            if dep_runtime.state == ModState.ERROR:
                dep.is_resolved = False
                return False
            if not self._satisfies_version(dep_runtime.descriptor.version,
                                            dep.version_requirement):
                dep.is_resolved = False
                return False
            dep.is_resolved = True
            dep.resolved_version = dep_runtime.descriptor.version
        return True

    def _check_engine_compatibility(self, descriptor: ModDescriptor) -> bool:
        """Check whether a descriptor is compatible with the engine version."""
        engine_version = self._config.engine_version if self._config else "1.0.0"
        if descriptor.min_engine_version:
            if not _version_ge(engine_version, descriptor.min_engine_version):
                return False
        if descriptor.max_engine_version:
            if not _version_le(engine_version, descriptor.max_engine_version):
                return False
        return True

    def _satisfies_version(self, available: str, requirement: str) -> bool:
        """Check whether an available version satisfies a version requirement."""
        try:
            requirement = requirement.strip()
            for op in (">=", "<=", "==", ">", "<", "^", "~"):
                if requirement.startswith(op):
                    target = requirement[len(op):].strip()
                    if op == ">=":
                        return _version_ge(available, target)
                    if op == "<=":
                        return _version_le(available, target)
                    if op == "==":
                        return available == target
                    if op == ">":
                        return _version_gt(available, target)
                    if op == "<":
                        return _version_lt(available, target)
                    if op == "^":
                        return _version_caret(available, target)
                    if op == "~":
                        return _version_tilde(available, target)
            return available == requirement
        except (ValueError, IndexError):
            return False

    def _find_dependents(self, mod_id: str) -> List[str]:
        """Find loaded mods that declare a hard dependency on the given mod."""
        dependents: List[str] = []
        for mid, runtime in self._registry.items():
            if mid == mod_id:
                continue
            if runtime.state not in (ModState.LOADED, ModState.ENABLED):
                continue
            for dep in runtime.descriptor.dependencies:
                if dep.dependency_id == mod_id and not dep.is_optional:
                    dependents.append(mid)
                    break
        return dependents

    def _register_overrides(self, mod_id: str) -> None:
        """Register a mod's declared asset overrides in the global registry."""
        runtime = self._registry.get(mod_id)
        if runtime is None:
            return
        for asset in runtime.descriptor.asset_overrides:
            existing = self._asset_overrides.get(asset)
            if existing is None or self._should_override(existing, mod_id):
                self._asset_overrides[asset] = mod_id
            if runtime.api is not None and asset not in runtime.api.declared_overrides:
                runtime.api.declared_overrides.append(asset)

    def _should_override(self, current_owner: str, new_owner: str) -> bool:
        """Decide whether a new mod should replace the current override owner."""
        current = self._registry.get(current_owner)
        new = self._registry.get(new_owner)
        if current is None or new is None:
            return False
        return new.descriptor.priority > current.descriptor.priority

    def _remove_overrides(self, mod_id: str) -> None:
        """Remove all asset overrides owned by a mod."""
        for asset in list(self._asset_overrides.keys()):
            if self._asset_overrides[asset] == mod_id:
                del self._asset_overrides[asset]

    def _remove_hooks(self, mod_id: str) -> None:
        """Remove all script hooks registered by a mod."""
        for hook_name in list(self._script_hooks.keys()):
            self._script_hooks[hook_name] = [
                (mid, h) for mid, h in self._script_hooks[hook_name]
                if mid != mod_id
            ]
            if not self._script_hooks[hook_name]:
                del self._script_hooks[hook_name]

    def _grant_api(self, mod_id: str) -> None:
        """Create and grant a modding API surface for a mod."""
        runtime = self._registry.get(mod_id)
        if runtime is None or runtime.api is not None:
            return
        descriptor = runtime.descriptor
        api = ModAPI(
            mod_id=mod_id,
            permissions=list(descriptor.permissions),
            api_version="1.0.0",
            is_sandboxed=bool(self._config and self._config.sandbox_enabled),
            is_active=runtime.state == ModState.ENABLED,
        )
        runtime.api = api
        self._apis[api.api_id] = api

    def _revoke_api(self, mod_id: str) -> None:
        """Revoke the modding API surface previously granted to a mod."""
        runtime = self._registry.get(mod_id)
        if runtime is None or runtime.api is None:
            return
        api = runtime.api
        api.revoke()
        self._apis.pop(api.api_id, None)
        runtime.api = None

    def _mark_conflicted(self, mod_id: str) -> None:
        """Mark a mod as being in a conflict state if currently loaded."""
        runtime = self._registry.get(mod_id)
        if runtime is None:
            return
        if runtime.state in (ModState.LOADED, ModState.ENABLED):
            runtime.state = ModState.CONFLICT

    def _clear_conflict_state(self, mod_id: str) -> None:
        """Restore a mod to LOADED state after its conflicts are resolved."""
        runtime = self._registry.get(mod_id)
        if runtime is None or runtime.state != ModState.CONFLICT:
            return
        still_conflicted = any(
            (c.mod_id_a == mod_id or c.mod_id_b == mod_id) and not c.is_resolved
            for c in self._conflicts
        )
        if not still_conflicted:
            runtime.state = ModState.LOADED

    def _apply_override_winner(self, asset: str, winner_mod: str) -> None:
        """Set the winning mod as the owner of an asset override."""
        self._asset_overrides[asset] = winner_mod

    def _detect_explicit_conflicts(self) -> List[ModConflict]:
        """Detect conflicts explicitly declared in mod descriptors."""
        conflicts: List[ModConflict] = []
        for mid, runtime in self._registry.items():
            if runtime.state not in (ModState.LOADED, ModState.ENABLED):
                continue
            for other_id in runtime.descriptor.conflicts:
                other = self._registry.get(other_id)
                if other is None or other.state not in (
                    ModState.LOADED, ModState.ENABLED
                ):
                    continue
                conflicts.append(ModConflict(
                    mod_id_a=mid,
                    mod_id_b=other_id,
                    resource_key=f"declared:{mid}:{other_id}",
                    resource_type="declared",
                    description=(
                        f"Mod '{mid}' explicitly declares conflict with "
                        f"'{other_id}'"
                    ),
                    strategy=self._effective_conflict_strategy(),
                ))
        return conflicts

    def _trim_conflict_log(self) -> None:
        """Cap the size of the conflict log to the configured maximum."""
        if len(self._conflicts) > self.MAX_CONFLICT_LOG:
            self._conflicts = self._conflicts[-self.MAX_CONFLICT_LOG:]


# ---------------------------------------------------------------------------
# Version Helpers
# ---------------------------------------------------------------------------

def _parse_version_parts(v: str) -> List[int]:
    """Parse a dotted version string into a list of integers."""
    parts: List[int] = []
    for piece in v.split("."):
        piece = piece.strip()
        if piece.isdigit():
            parts.append(int(piece))
        else:
            parts.append(0)
    return parts


def _version_ge(a: str, b: str) -> bool:
    """Return True if version a is greater than or equal to version b."""
    pa, pb = _parse_version_parts(a), _parse_version_parts(b)
    max_len = max(len(pa), len(pb))
    pa += [0] * (max_len - len(pa))
    pb += [0] * (max_len - len(pb))
    return pa >= pb


def _version_le(a: str, b: str) -> bool:
    """Return True if version a is less than or equal to version b."""
    pa, pb = _parse_version_parts(a), _parse_version_parts(b)
    max_len = max(len(pa), len(pb))
    pa += [0] * (max_len - len(pa))
    pb += [0] * (max_len - len(pb))
    return pa <= pb


def _version_gt(a: str, b: str) -> bool:
    """Return True if version a is strictly greater than version b."""
    return _version_ge(a, b) and a != b


def _version_lt(a: str, b: str) -> bool:
    """Return True if version a is strictly less than version b."""
    return _version_le(a, b) and a != b


def _version_caret(available: str, target: str) -> bool:
    """Implement semver caret (^) compatibility: compatible with target."""
    pa = _parse_version_parts(available)
    pt = _parse_version_parts(target)
    if not pt:
        return True
    if not _version_ge(available, target):
        return False
    if pt[0] >= 1:
        return len(pa) >= 1 and pa[0] == pt[0]
    if len(pt) >= 2 and pt[1] >= 1:
        return len(pa) >= 2 and pa[0] == pt[0] and pa[1] == pt[1]
    return len(pa) >= 2 and pa[0] == 0 and pa[1] == 0


def _version_tilde(available: str, target: str) -> bool:
    """Implement semver tilde (~) compatibility: patch-level compatible."""
    pa = _parse_version_parts(available)
    pt = _parse_version_parts(target)
    if not pt:
        return True
    if not _version_ge(available, target):
        return False
    if len(pt) >= 2:
        return len(pa) >= 2 and pa[0] == pt[0] and pa[1] == pt[1]
    return len(pa) >= 1 and pa[0] == pt[0]


# ---------------------------------------------------------------------------
# Factory Function
# ---------------------------------------------------------------------------

def get_modding_framework() -> ModdingFramework:
    """Get the ModdingFramework singleton instance."""
    return ModdingFramework.get_instance()
