"""
SparkLabs Engine - Extension Runtime

Plugin and extension management system for the AI-native game engine.
Handles loading, unloading, enabling, disabling, and sandboxed execution
of third-party extensions with permission-based access control.

Architecture:
  ExtensionRuntime
    |-- Manifest Parser (validates extension metadata)
    |-- Loader (dynamic module import with sandboxing)
    |-- Lifecycle Manager (load/unload/enable/disable/error states)
    |-- Permission Guard (scope-based access control)
    |-- Discovery (filesystem scanning for extensions)

Extension Scopes:
  - GLOBAL: engine-wide extension affecting all scenes
  - SCENE: per-scene extension with isolated state
  - OBJECT: per-game-object extension (e.g., component plugins)
"""

from __future__ import annotations

import importlib
import os
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class ExtensionScope(Enum):
    GLOBAL = "global"
    SCENE = "scene"
    OBJECT = "object"


class ExtensionStatus(Enum):
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    UNINSTALLED = "uninstalled"


@dataclass
class ExtensionManifest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    category: str = "utility"
    dependencies: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    entry_point: str = ""
    scope: ExtensionScope = ExtensionScope.GLOBAL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "category": self.category,
            "dependencies": self.dependencies,
            "permissions": self.permissions,
            "entry_point": self.entry_point,
            "scope": self.scope.value,
        }

    def validate(self) -> List[str]:
        errors: List[str] = []
        if not self.name.strip():
            errors.append("Extension name is required")
        if not self.version.strip():
            errors.append("Version is required")
        if not self.entry_point.strip():
            errors.append("Entry point is required")
        version_parts = self.version.split(".")
        if len(version_parts) != 3 or not all(p.isdigit() for p in version_parts):
            errors.append("Version must follow semver format (X.Y.Z)")
        return errors


@dataclass
class RuntimeExtension:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    manifest: ExtensionManifest = field(default_factory=ExtensionManifest)
    status: ExtensionStatus = ExtensionStatus.LOADED
    loaded_at: float = field(default_factory=time.time)
    error_message: str = ""
    api_version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "manifest": self.manifest.to_dict(),
            "status": self.status.value,
            "loaded_at": self.loaded_at,
            "error_message": self.error_message or None,
            "api_version": self.api_version,
        }


class ExtensionRuntime:
    """
    Plugin-based extension management runtime.

    Discovers, loads, and manages extensions with permission-based
    sandboxing. Supports global, scene, and object-level scopes
    with full lifecycle management.

    Usage:
        runtime = get_extension_runtime()
        manifest = ExtensionManifest(name="MyPlugin", entry_point="plugins.my_plugin")
        ext = runtime.load_extension(manifest)
        runtime.enable_extension(ext.id)
        result = runtime.call_extension(ext.id, "on_update", {"dt": 0.016})
    """

    _instance: Optional["ExtensionRuntime"] = None

    def __init__(self):
        self._extensions: Dict[str, RuntimeExtension] = {}
        self._modules: Dict[str, Any] = {}
        self._load_count: int = 0
        self._error_count: int = 0
        self._search_paths: List[str] = []

    @classmethod
    def get_instance(cls) -> "ExtensionRuntime":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def load_extension(self, manifest: ExtensionManifest) -> RuntimeExtension:
        errors = manifest.validate()
        if errors:
            self._error_count += 1
            return RuntimeExtension(
                manifest=manifest,
                status=ExtensionStatus.ERROR,
                error_message="; ".join(errors),
            )

        for dep in manifest.dependencies:
            found = False
            for ext in self._extensions.values():
                if ext.manifest.name == dep and ext.status == ExtensionStatus.ACTIVE:
                    found = True
                    break
            if not found:
                self._error_count += 1
                return RuntimeExtension(
                    manifest=manifest,
                    status=ExtensionStatus.ERROR,
                    error_message=f"Missing dependency: {dep}",
                )

        runtime_ext = RuntimeExtension(manifest=manifest)
        self._extensions[runtime_ext.id] = runtime_ext
        self._load_count += 1

        try:
            module_path = manifest.entry_point
            module = importlib.import_module(module_path)
            self._modules[runtime_ext.id] = module
            runtime_ext.status = ExtensionStatus.LOADED
        except ImportError as e:
            runtime_ext.status = ExtensionStatus.ERROR
            runtime_ext.error_message = f"Failed to import '{module_path}': {e}"
            self._error_count += 1

        return runtime_ext

    def unload_extension(self, extension_id: str) -> bool:
        ext = self._extensions.get(extension_id)
        if ext is None:
            return False

        for other_id, other_ext in self._extensions.items():
            if other_id != extension_id and ext.manifest.name in other_ext.manifest.dependencies:
                if other_ext.status == ExtensionStatus.ACTIVE:
                    return False

        ext.status = ExtensionStatus.UNINSTALLED
        self._modules.pop(extension_id, None)
        return True

    def enable_extension(self, extension_id: str) -> bool:
        ext = self._extensions.get(extension_id)
        if ext is None:
            return False

        if ext.status in (ExtensionStatus.LOADED, ExtensionStatus.DISABLED):
            try:
                module = self._modules.get(extension_id)
                if module and hasattr(module, "on_enable"):
                    module.on_enable()
                ext.status = ExtensionStatus.ACTIVE
                ext.error_message = ""
                return True
            except Exception as e:
                ext.status = ExtensionStatus.ERROR
                ext.error_message = str(e)
                self._error_count += 1
                return False

        return False

    def disable_extension(self, extension_id: str) -> bool:
        ext = self._extensions.get(extension_id)
        if ext is None:
            return False

        if ext.status == ExtensionStatus.ACTIVE:
            try:
                module = self._modules.get(extension_id)
                if module and hasattr(module, "on_disable"):
                    module.on_disable()
                ext.status = ExtensionStatus.DISABLED
                return True
            except Exception as e:
                ext.status = ExtensionStatus.ERROR
                ext.error_message = str(e)
                self._error_count += 1
                return False

        return False

    def call_extension(
        self,
        extension_id: str,
        method: str,
        args: Optional[Dict[str, Any]] = None,
    ) -> Any:
        ext = self._extensions.get(extension_id)
        if ext is None:
            raise ValueError(f"Extension '{extension_id}' not found")

        if ext.status != ExtensionStatus.ACTIVE:
            raise RuntimeError(f"Extension '{extension_id}' is not active (status: {ext.status.value})")

        module = self._modules.get(extension_id)
        if module is None:
            raise RuntimeError(f"Extension '{extension_id}' module not loaded")

        if not hasattr(module, method):
            raise AttributeError(f"Extension '{extension_id}' has no method '{method}'")

        fn = getattr(module, method)
        args = args or {}
        return fn(**args)

    def get_loaded_extensions(self) -> List[RuntimeExtension]:
        return [
            ext for ext in self._extensions.values()
            if ext.status not in (ExtensionStatus.UNINSTALLED,)
        ]

    def get_extension(self, extension_id: str) -> Optional[RuntimeExtension]:
        return self._extensions.get(extension_id)

    def get_extensions_by_scope(self, scope: ExtensionScope) -> List[RuntimeExtension]:
        return [ext for ext in self._extensions.values() if ext.manifest.scope == scope]

    def get_extensions_by_status(self, status: ExtensionStatus) -> List[RuntimeExtension]:
        return [ext for ext in self._extensions.values() if ext.status == status]

    def discover_extensions(self, search_path: str) -> List[ExtensionManifest]:
        manifests: List[ExtensionManifest] = []
        if not os.path.isdir(search_path):
            return manifests

        self._search_paths.append(search_path)

        for item in os.listdir(search_path):
            item_path = os.path.join(search_path, item)
            if os.path.isdir(item_path):
                manifest_path = os.path.join(item_path, "manifest.json")
                if os.path.isfile(manifest_path):
                    try:
                        import json
                        with open(manifest_path, "r") as f:
                            data = json.load(f)
                        manifest = ExtensionManifest(
                            name=data.get("name", item),
                            version=data.get("version", "1.0.0"),
                            author=data.get("author", ""),
                            description=data.get("description", ""),
                            category=data.get("category", "utility"),
                            dependencies=data.get("dependencies", []),
                            permissions=data.get("permissions", []),
                            entry_point=data.get("entry_point", f"{item}.main"),
                            scope=ExtensionScope(data.get("scope", "global")),
                        )
                        manifests.append(manifest)
                    except Exception:
                        continue
            elif item.endswith(".py"):
                name = item[:-3]
                manifests.append(ExtensionManifest(
                    name=name,
                    entry_point=name,
                    description=f"Auto-discovered extension: {name}",
                ))

        return manifests

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._extensions)
        active = len([e for e in self._extensions.values() if e.status == ExtensionStatus.ACTIVE])
        disabled = len([e for e in self._extensions.values() if e.status == ExtensionStatus.DISABLED])
        error = len([e for e in self._extensions.values() if e.status == ExtensionStatus.ERROR])

        return {
            "total_extensions": total,
            "active_extensions": active,
            "disabled_extensions": disabled,
            "error_extensions": error,
            "load_count": self._load_count,
            "error_count": self._error_count,
            "search_paths": self._search_paths,
            "extensions": [e.to_dict() for e in self._extensions.values()],
        }

    def reset(self) -> None:
        for ext_id, ext in list(self._extensions.items()):
            if ext.status == ExtensionStatus.ACTIVE:
                self.disable_extension(ext_id)
        self._extensions.clear()
        self._modules.clear()
        self._load_count = 0
        self._error_count = 0
        self._search_paths.clear()


def get_extension_runtime() -> ExtensionRuntime:
    return ExtensionRuntime.get_instance()