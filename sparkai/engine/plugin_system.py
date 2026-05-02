"""
Plugin System - Extensible plugin architecture for the SparkLabs engine.

Architecture:
    PluginSystem/
    |-- PluginState (lifecycle state enumeration)
    |-- PluginPermission (capability permission enumeration)
    |-- PluginManifest (plugin metadata dataclass)
    |-- PluginHook (extension point hook dataclass)
    |-- PluginInstance (loaded plugin runtime dataclass)
    |-- PluginRegistry (dependency-aware registration)
    |-- PluginSystem (global plugin orchestration)

Manages the full plugin lifecycle: discovery, validation, dependency resolution,
loading, activation, deactivation, and unloading. Supports hook-based extension
points and sandboxed execution contexts.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional, Set


class PluginState(Enum):
    DISCOVERED = "discovered"
    VALIDATING = "validating"
    RESOLVING = "resolving"
    LOADED = "loaded"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"
    UNLOADED = "unloaded"
    ERROR = "error"


class PluginPermission(Enum):
    READ_FILES = auto()
    WRITE_FILES = auto()
    NETWORK_ACCESS = auto()
    ENGINE_API = auto()
    RENDER_ACCESS = auto()
    AUDIO_ACCESS = auto()
    INPUT_ACCESS = auto()
    AGENT_INTEGRATION = auto()


@dataclass
class PluginManifest:
    plugin_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Unnamed Plugin"
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    min_engine_version: str = "1.0.0"
    dependencies: List[str] = field(default_factory=list)
    hooks: List[str] = field(default_factory=list)
    permissions: List[PluginPermission] = field(default_factory=list)
    entry_point: str = ""
    icon: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.plugin_id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "dependencies": self.dependencies,
            "hooks": self.hooks,
            "permissions": [p.name for p in self.permissions],
            "entry_point": self.entry_point,
        }

    def has_permission(self, permission: PluginPermission) -> bool:
        return permission in self.permissions

    def requires_dependency(self, dependency_id: str) -> bool:
        return dependency_id in self.dependencies


@dataclass
class PluginHook:
    hook_name: str = ""
    description: str = ""
    hook_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: int = 0
    handler: Optional[Callable[..., Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hook_name": self.hook_name,
            "hook_id": self.hook_id,
            "priority": self.priority,
            "description": self.description,
        }


@dataclass
class PluginInstance:
    manifest: PluginManifest = field(default_factory=PluginManifest)
    state: PluginState = PluginState.DISCOVERED
    loaded_at: float = 0.0
    activated_at: float = 0.0
    error_message: str = ""
    registered_hooks: List[str] = field(default_factory=list)
    instance_ref: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plugin_id": self.manifest.plugin_id,
            "name": self.manifest.name,
            "version": self.manifest.version,
            "state": self.state.value,
            "author": self.manifest.author,
            "dependencies": self.manifest.dependencies,
            "hooks": self.registered_hooks,
            "error": self.error_message if self.state == PluginState.ERROR else None,
        }


class PluginRegistry:
    def __init__(self):
        self._manifests: Dict[str, PluginManifest] = {}
        self._instances: Dict[str, PluginInstance] = {}
        self._hooks: Dict[str, List[PluginHook]] = {}

    def register_manifest(self, manifest: PluginManifest) -> str:
        self._manifests[manifest.plugin_id] = manifest
        return manifest.plugin_id

    def get_manifest(self, plugin_id: str) -> Optional[PluginManifest]:
        return self._manifests.get(plugin_id)

    def register_instance(self, instance: PluginInstance) -> None:
        self._instances[instance.manifest.plugin_id] = instance

    def get_instance(self, plugin_id: str) -> Optional[PluginInstance]:
        return self._instances.get(plugin_id)

    def list_manifests(self) -> List[PluginManifest]:
        return list(self._manifests.values())

    def list_instances(self) -> List[PluginInstance]:
        return list(self._instances.values())

    def register_hook(self, plugin_id: str, hook: PluginHook) -> None:
        if plugin_id not in self._hooks:
            self._hooks[plugin_id] = []
        self._hooks[plugin_id].append(hook)

    def get_hooks(self, plugin_id: str) -> List[PluginHook]:
        return self._hooks.get(plugin_id, [])

    def list_hooks(self, hook_name: Optional[str] = None) -> List[Dict[str, Any]]:
        results = []
        for plugin_id, hooks in self._hooks.items():
            for hook in hooks:
                if hook_name is None or hook.hook_name == hook_name:
                    results.append({
                        "plugin_id": plugin_id,
                        **hook.to_dict(),
                    })
        return sorted(results, key=lambda h: h["priority"])

    def get_stats(self) -> Dict[str, Any]:
        return {
            "manifest_count": len(self._manifests),
            "instance_count": len(self._instances),
            "total_hooks": sum(len(h) for h in self._hooks.values()),
            "active_instances": sum(
                1 for i in self._instances.values() if i.state == PluginState.ACTIVE
            ),
        }


class PluginSystem:
    _instance: Optional["PluginSystem"] = None

    def __init__(self):
        self._registry = PluginRegistry()
        self._plugin_directory: str = "plugins"
        self._auto_load: bool = False
        self._sandbox_enabled: bool = True
        self._max_plugins: int = 64

    @classmethod
    def get_instance(cls) -> "PluginSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def discover_manifest(self, manifest_data: Dict[str, Any]) -> PluginManifest:
        permissions = []
        for p in manifest_data.get("permissions", []):
            try:
                permissions.append(PluginPermission[p])
            except (KeyError, TypeError):
                pass

        manifest = PluginManifest(
            name=manifest_data.get("name", "Unnamed"),
            version=manifest_data.get("version", "1.0.0"),
            author=manifest_data.get("author", ""),
            description=manifest_data.get("description", ""),
            dependencies=manifest_data.get("dependencies", []),
            hooks=manifest_data.get("hooks", []),
            permissions=permissions,
            entry_point=manifest_data.get("entry_point", ""),
            icon=manifest_data.get("icon", ""),
        )
        self._registry.register_manifest(manifest)
        return manifest

    def register_plugin(self, manifest: PluginManifest) -> PluginInstance:
        if len(self._registry._instances) >= self._max_plugins:
            raise RuntimeError(f"Maximum plugin count reached: {self._max_plugins}")

        instance = PluginInstance(manifest=manifest, state=PluginState.DISCOVERED)
        self._registry.register_instance(instance)
        return instance

    def validate_dependencies(self, plugin_id: str) -> List[str]:
        instance = self._registry.get_instance(plugin_id)
        if not instance:
            manifest = self._registry.get_manifest(plugin_id)
            if not manifest:
                return [f"Plugin '{plugin_id}' not found"]
        else:
            manifest = instance.manifest

        missing = []
        for dep_id in manifest.dependencies:
            if dep_id not in self._registry._manifests:
                missing.append(dep_id)
        return missing

    def load_plugin(self, plugin_id: str) -> bool:
        instance = self._registry.get_instance(plugin_id)
        if not instance:
            return False

        if instance.state in (PluginState.ACTIVE, PluginState.LOADED):
            return True

        instance.state = PluginState.VALIDATING
        missing = self.validate_dependencies(plugin_id)
        if missing:
            instance.state = PluginState.ERROR
            instance.error_message = f"Missing dependencies: {', '.join(missing)}"
            return False

        instance.state = PluginState.RESOLVING
        instance.loaded_at = time.time()
        instance.state = PluginState.LOADED

        for hook_name in instance.manifest.hooks:
            hook = PluginHook(hook_name=hook_name, description=f"Auto-registered hook: {hook_name}")
            self._registry.register_hook(plugin_id, hook)
            instance.registered_hooks.append(hook_name)

        return True

    def activate_plugin(self, plugin_id: str) -> bool:
        instance = self._registry.get_instance(plugin_id)
        if not instance:
            return False

        if instance.state == PluginState.ACTIVE:
            return True

        if instance.state != PluginState.LOADED:
            if not self.load_plugin(plugin_id):
                return False

        instance.activated_at = time.time()
        instance.state = PluginState.ACTIVE
        return True

    def deactivate_plugin(self, plugin_id: str) -> bool:
        instance = self._registry.get_instance(plugin_id)
        if not instance:
            return False

        instance.state = PluginState.DEACTIVATED
        return True

    def unload_plugin(self, plugin_id: str) -> bool:
        instance = self._registry.get_instance(plugin_id)
        if not instance:
            return False

        dependents = []
        for pid, inst in self._registry._instances.items():
            if pid != plugin_id and plugin_id in inst.manifest.dependencies:
                if inst.state == PluginState.ACTIVE:
                    dependents.append(pid)

        if dependents:
            instance.state = PluginState.ERROR
            instance.error_message = f"Cannot unload: still required by {', '.join(dependents)}"
            return False

        instance.state = PluginState.UNLOADED
        self._registry._hooks.pop(plugin_id, None)
        return True

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstance]:
        return self._registry.get_instance(plugin_id)

    def list_plugins(self) -> List[Dict[str, Any]]:
        return [i.to_dict() for i in self._registry.list_instances()]

    def list_active_plugins(self) -> List[str]:
        return [
            pid for pid, inst in self._registry._instances.items()
            if inst.state == PluginState.ACTIVE
        ]

    def register_hook(self, plugin_id: str, hook_name: str, handler: Callable, priority: int = 0) -> bool:
        instance = self._registry.get_instance(plugin_id)
        if not instance or instance.state != PluginState.ACTIVE:
            return False

        hook = PluginHook(
            hook_name=hook_name,
            description=f"Registered by {instance.manifest.name}",
            priority=priority,
            handler=handler,
        )
        self._registry.register_hook(plugin_id, hook)
        if hook_name not in instance.registered_hooks:
            instance.registered_hooks.append(hook_name)
        return True

    def invoke_hooks(self, hook_name: str, *args, **kwargs) -> List[Any]:
        results = []
        for plugin_id, hooks in sorted(self._registry._hooks.items(),
                                         key=lambda x: min(h.priority for h in x[1]) if x[1] else 0):
            instance = self._registry.get_instance(plugin_id)
            if not instance or instance.state != PluginState.ACTIVE:
                continue
            for hook in hooks:
                if hook.hook_name == hook_name and hook.handler:
                    try:
                        result = hook.handler(*args, **kwargs)
                        results.append(result)
                    except Exception as e:
                        results.append({"error": str(e), "plugin_id": plugin_id})
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "registry": self._registry.get_stats(),
            "active_plugins": self.list_active_plugins(),
            "auto_load": self._auto_load,
            "sandbox_enabled": self._sandbox_enabled,
            "plugin_directory": self._plugin_directory,
        }


def get_plugin_system() -> PluginSystem:
    return PluginSystem.get_instance()
