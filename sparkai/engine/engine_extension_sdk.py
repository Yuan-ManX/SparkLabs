"""
SparkLabs Engine - Extension SDK

Plugin framework that enables dynamic loading of engine extensions.
Extensions can provide new object types, behaviors, actions, conditions,
and expressions. Each extension has a declarative IDE definition and a
runtime implementation with full lifecycle management.

Architecture:
  ExtensionSDK
    |-- ExtensionManifest (metadata, authorship, versioning, status)
    |-- ExtensionCapability (declared features with scope and parameters)
    |-- ExtensionAPI (programmatic interface endpoints and schema)
    |-- SDKConfig (global SDK configuration and policy controls)

SDK Features:
  - REGISTER: add new extensions with manifest and capability declarations
  - LOAD/UNLOAD: dynamic runtime lifecycle management
  - ENABLE/DISABLE: toggle extension activation without unloading
  - CAPABILITIES: query available features by scope or extension type
  - SEARCH: discover extensions by query, category, or source
  - INSTALL: install extensions from package files with dependency checks
  - CREATE: scaffold new extension projects from templates
  - VALIDATE: integrity verification and schema validation
  - EXPORT: package extensions for distribution and sharing
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set

_time_module = time


# ---------------------------------------------------------------------------
# Domain Enumerations
# ---------------------------------------------------------------------------


class ExtensionType(Enum):
    OBJECT = "object"
    BEHAVIOR = "behavior"
    ACTION = "action"
    CONDITION = "condition"
    EXPRESSION = "expression"
    EFFECT = "effect"
    IMPORTER = "importer"
    EXPORTER = "exporter"
    SYSTEM = "system"


class ExtensionStatus(Enum):
    REGISTERED = "registered"
    LOADED = "loaded"
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"
    NEEDS_UPDATE = "needs_update"


class ExtensionSource(Enum):
    BUILT_IN = "built_in"
    REVIEWED = "reviewed"
    COMMUNITY = "community"
    PROJECT_LOCAL = "project_local"
    EXTERNAL = "external"


class CapabilityScope(Enum):
    SCENE = "scene"
    OBJECT = "object"
    BEHAVIOR = "behavior"
    GLOBAL = "global"


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------


@dataclass
class ExtensionManifest:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    extension_type: ExtensionType = ExtensionType.SYSTEM
    source: ExtensionSource = ExtensionSource.PROJECT_LOCAL
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    status: ExtensionStatus = ExtensionStatus.REGISTERED
    entry_point: str = ""
    created_at: float = field(default_factory=_time_module.time)
    updated_at: float = field(default_factory=_time_module.time)
    tags: List[str] = field(default_factory=list)
    icon: str = ""
    min_engine_version: str = "1.0.0"
    max_engine_version: str = ""
    license_name: str = "MIT"
    homepage_url: str = ""
    repository_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id,
            name=self.name,
            version=self.version,
            author=self.author,
            description=self.description,
            extension_type=self.extension_type.value,
            source=self.source.value,
            dependencies=list(self.dependencies),
            capabilities=list(self.capabilities),
            status=self.status.value,
            entry_point=self.entry_point,
            created_at=self.created_at,
            updated_at=self.updated_at,
            tags=list(self.tags),
            icon=self.icon,
            min_engine_version=self.min_engine_version,
            max_engine_version=self.max_engine_version,
            license_name=self.license_name,
            homepage_url=self.homepage_url,
            repository_url=self.repository_url,
            metadata=dict(self.metadata),
        )

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
class ExtensionCapability:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    name: str = ""
    description: str = ""
    scope: CapabilityScope = CapabilityScope.GLOBAL
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    return_type: str = "void"
    icon: str = ""
    category: str = ""
    tags: List[str] = field(default_factory=list)
    is_deprecated: bool = False
    min_engine_version: str = "1.0.0"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id,
            extension_id=self.extension_id,
            name=self.name,
            description=self.description,
            scope=self.scope.value,
            parameters=list(self.parameters),
            return_type=self.return_type,
            icon=self.icon,
            category=self.category,
            tags=list(self.tags),
            is_deprecated=self.is_deprecated,
            min_engine_version=self.min_engine_version,
            metadata=dict(self.metadata),
        )


@dataclass
class ExtensionAPI:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    endpoints: List[Dict[str, Any]] = field(default_factory=list)
    auth_required: bool = False
    rate_limit: int = 0
    documentation_url: str = ""
    schema_version: str = "1.0.0"
    api_key: str = ""
    timeout_ms: int = 5000
    retry_count: int = 3
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id,
            extension_id=self.extension_id,
            endpoints=list(self.endpoints),
            auth_required=self.auth_required,
            rate_limit=self.rate_limit,
            documentation_url=self.documentation_url,
            schema_version=self.schema_version,
            timeout_ms=self.timeout_ms,
            retry_count=self.retry_count,
            metadata=dict(self.metadata),
        )


@dataclass
class SDKConfig:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Default SDK Configuration"
    enabled_extensions: List[str] = field(default_factory=list)
    auto_update: bool = False
    sandbox_enabled: bool = True
    max_load_time_ms: int = 5000
    allowed_sources: List[str] = field(default_factory=list)
    max_extensions: int = 128
    discovery_paths: List[str] = field(default_factory=list)
    log_level: str = "info"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id,
            name=self.name,
            enabled_extensions=list(self.enabled_extensions),
            auto_update=self.auto_update,
            sandbox_enabled=self.sandbox_enabled,
            max_load_time_ms=self.max_load_time_ms,
            allowed_sources=list(self.allowed_sources),
            max_extensions=self.max_extensions,
            discovery_paths=list(self.discovery_paths),
            log_level=self.log_level,
            metadata=dict(self.metadata),
        )


# ---------------------------------------------------------------------------
# Extension SDK (Singleton)
# ---------------------------------------------------------------------------


class ExtensionSDK:
    """Plugin framework that enables dynamic loading of engine extensions.

    Extensions can provide new object types, behaviors, actions, conditions,
    and expressions. Each extension has a declarative IDE definition and a
    runtime implementation with full lifecycle management.

    Usage:
        sdk = get_extension_sdk()
        manifest = ExtensionManifest(name="MyPlugin", entry_point="plugins.my_plugin")
        caps = [ExtensionCapability(name="NewAction", scope=CapabilityScope.OBJECT)]
        sdk.register_extension(manifest, caps)
        sdk.load_extension(manifest.id)
        sdk.enable_extension(manifest.id)
    """

    _instance: Optional["ExtensionSDK"] = None
    _lock = threading.RLock()

    MAX_SEARCH_RESULTS = 50
    MAX_LOG_ENTRIES = 500

    def __init__(self) -> None:
        self._extensions: Dict[str, ExtensionManifest] = {}
        self._capabilities: Dict[str, ExtensionCapability] = {}
        self._apis: Dict[str, ExtensionAPI] = {}
        self._loaded_modules: Dict[str, Any] = {}
        self._config: SDKConfig = SDKConfig()
        self._event_log: List[Dict[str, Any]] = []
        self._load_errors: Dict[str, str] = {}
        self._dependency_graph: Dict[str, Set[str]] = {}

    @classmethod
    def get_instance(cls) -> "ExtensionSDK":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Registration ----

    def register_extension(
        self,
        manifest: ExtensionManifest,
        capabilities: Optional[List[ExtensionCapability]] = None,
    ) -> Optional[ExtensionManifest]:
        if manifest.id in self._extensions:
            existing = self._extensions[manifest.id]
            if existing.status not in (ExtensionStatus.ERROR, ExtensionStatus.NEEDS_UPDATE):
                self._log("extension_register_duplicate", extension_id=manifest.id,
                          name=manifest.name, existing_status=existing.status.value)
                return None

        errors = manifest.validate()
        if errors:
            manifest.status = ExtensionStatus.ERROR
            self._log("extension_register_invalid", extension_id=manifest.id,
                      name=manifest.name, errors=errors)
            return None

        if len(self._extensions) >= self._config.max_extensions:
            self._log("extension_register_limit_reached",
                      limit=self._config.max_extensions)
            return None

        manifest.updated_at = _time_module.time()
        manifest.status = ExtensionStatus.REGISTERED
        self._extensions[manifest.id] = manifest

        caps = capabilities or []
        for cap in caps:
            cap.extension_id = manifest.id
            self._capabilities[cap.id] = cap
            if cap.id not in manifest.capabilities:
                manifest.capabilities.append(cap.id)

        self._dependency_graph[manifest.id] = set(manifest.dependencies)
        self._log("extension_registered", extension_id=manifest.id,
                  name=manifest.name, capability_count=len(caps))
        return manifest

    # ---- Loading / Unloading ----

    def load_extension(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        if manifest.status == ExtensionStatus.ACTIVE:
            return True

        if not self._check_dependency_tree(extension_id):
            manifest.status = ExtensionStatus.ERROR
            self._load_errors[extension_id] = "Unresolved dependencies"
            self._log("extension_load_dependency_failure",
                      extension_id=extension_id, name=manifest.name)
            return False

        source_name = manifest.source.value
        if self._config.allowed_sources and source_name not in self._config.allowed_sources:
            manifest.status = ExtensionStatus.ERROR
            self._load_errors[extension_id] = f"Source '{source_name}' not allowed"
            self._log("extension_load_source_blocked",
                      extension_id=extension_id, name=manifest.name, source=source_name)
            return False

        for dep_id in manifest.dependencies:
            dep = self._extensions.get(dep_id)
            if dep is None or dep.status != ExtensionStatus.ACTIVE:
                dep_loaded = self.load_extension(dep_id) if dep else False
                if not dep_loaded:
                    manifest.status = ExtensionStatus.ERROR
                    self._load_errors[extension_id] = f"Failed to load dependency: {dep_id}"
                    self._log("extension_load_dependency_failure",
                              extension_id=extension_id, dep_id=dep_id)
                    return False

        manifest.updated_at = _time_module.time()
        manifest.status = ExtensionStatus.LOADED
        self._log("extension_loaded", extension_id=extension_id, name=manifest.name)
        return True

    def unload_extension(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        for other_id, other in self._extensions.items():
            if other_id != extension_id and extension_id in other.dependencies:
                if other.status == ExtensionStatus.ACTIVE:
                    self._log("extension_unload_blocked_by_dependent",
                              extension_id=extension_id, dependent_id=other_id)
                    return False

        if manifest.status == ExtensionStatus.ACTIVE:
            self._deactivate_extension_internal(extension_id)

        self._loaded_modules.pop(extension_id, None)
        self._load_errors.pop(extension_id, None)

        manifest.updated_at = _time_module.time()
        manifest.status = ExtensionStatus.REGISTERED
        self._log("extension_unloaded", extension_id=extension_id, name=manifest.name)
        return True

    # ---- Enable / Disable ----

    def enable_extension(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        if manifest.status == ExtensionStatus.ACTIVE:
            return True

        if manifest.status not in (ExtensionStatus.LOADED, ExtensionStatus.DISABLED):
            if not self.load_extension(extension_id):
                return False

        manifest.updated_at = _time_module.time()
        manifest.status = ExtensionStatus.ACTIVE
        self._log("extension_enabled", extension_id=extension_id, name=manifest.name)
        return True

    def disable_extension(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        if manifest.status != ExtensionStatus.ACTIVE:
            return False

        dependents = []
        for other_id, other in self._extensions.items():
            if other_id != extension_id and extension_id in other.dependencies:
                if other.status == ExtensionStatus.ACTIVE:
                    dependents.append(other_id)

        if dependents:
            self._log("extension_disable_blocked_by_dependents",
                      extension_id=extension_id, dependents=dependents)
            return False

        return self._deactivate_extension_internal(extension_id)

    def _deactivate_extension_internal(self, extension_id: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        manifest.updated_at = _time_module.time()
        manifest.status = ExtensionStatus.DISABLED
        self._log("extension_disabled", extension_id=extension_id, name=manifest.name)
        return True

    # ---- Capabilities ----

    def get_capabilities(
        self,
        scope: Optional[str] = None,
        extension_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []

        for cap_id, cap in self._capabilities.items():
            manifest = self._extensions.get(cap.extension_id)
            if manifest is None or manifest.status != ExtensionStatus.ACTIVE:
                continue

            if scope:
                try:
                    target_scope = CapabilityScope(scope.lower())
                except ValueError:
                    continue
                if cap.scope != target_scope:
                    continue

            if extension_type:
                try:
                    target_type = ExtensionType(extension_type.lower())
                except ValueError:
                    continue
                if manifest.extension_type != target_type:
                    continue

            results.append({
                "capability": cap.to_dict(),
                "extension_name": manifest.name,
                "extension_id": manifest.id,
            })

        return results

    def get_capabilities_by_extension(self, extension_id: str) -> List[ExtensionCapability]:
        return [
            cap for cap in self._capabilities.values()
            if cap.extension_id == extension_id
        ]

    # ---- Search ----

    def search_extensions(
        self,
        query: str = "",
        category: Optional[str] = None,
        source: Optional[str] = None,
    ) -> List[ExtensionManifest]:
        results: List[ExtensionManifest] = []

        for ext in self._extensions.values():
            if source:
                try:
                    target_source = ExtensionSource(source.lower())
                except ValueError:
                    continue
                if ext.source != target_source:
                    continue

            if category:
                if category.lower() not in [t.lower() for t in ext.tags]:
                    caps = self.get_capabilities_by_extension(ext.id)
                    if not any(c.category.lower() == category.lower() for c in caps):
                        continue

            q = query.lower()
            if q:
                if not (
                    q in ext.name.lower()
                    or q in ext.description.lower()
                    or q in ext.author.lower()
                    or any(q in t.lower() for t in ext.tags)
                ):
                    continue

            if ext.status != ExtensionStatus.ERROR:
                results.append(ext)

        results.sort(key=lambda e: e.updated_at, reverse=True)
        return results[:self.MAX_SEARCH_RESULTS]

    # ---- Install ----

    def install_extension(self, package_path: str) -> Optional[ExtensionManifest]:
        try:
            with open(package_path, "r") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self._log("extension_install_package_read_error",
                      package_path=package_path, error=str(e))
            return None

        manifest_data = data.get("manifest", {})
        capabilities_data = data.get("capabilities", [])

        try:
            ext_type = ExtensionType(manifest_data.get("extension_type", "system"))
        except ValueError:
            ext_type = ExtensionType.SYSTEM

        try:
            ext_source = ExtensionSource(manifest_data.get("source", "project_local"))
        except ValueError:
            ext_source = ExtensionSource.PROJECT_LOCAL

        manifest = ExtensionManifest(
            name=manifest_data.get("name", ""),
            version=manifest_data.get("version", "1.0.0"),
            author=manifest_data.get("author", ""),
            description=manifest_data.get("description", ""),
            extension_type=ext_type,
            source=ext_source,
            dependencies=manifest_data.get("dependencies", []),
            entry_point=manifest_data.get("entry_point", ""),
            tags=manifest_data.get("tags", []),
            icon=manifest_data.get("icon", ""),
            min_engine_version=manifest_data.get("min_engine_version", "1.0.0"),
            max_engine_version=manifest_data.get("max_engine_version", ""),
            license_name=manifest_data.get("license_name", "MIT"),
            homepage_url=manifest_data.get("homepage_url", ""),
            repository_url=manifest_data.get("repository_url", ""),
            metadata=manifest_data.get("metadata", {}),
        )

        capabilities = []
        for cap_data in capabilities_data:
            try:
                cap_scope = CapabilityScope(cap_data.get("scope", "global"))
            except ValueError:
                cap_scope = CapabilityScope.GLOBAL

            capabilities.append(ExtensionCapability(
                name=cap_data.get("name", ""),
                description=cap_data.get("description", ""),
                scope=cap_scope,
                parameters=cap_data.get("parameters", []),
                return_type=cap_data.get("return_type", "void"),
                icon=cap_data.get("icon", ""),
                category=cap_data.get("category", ""),
                tags=cap_data.get("tags", []),
                is_deprecated=cap_data.get("is_deprecated", False),
                min_engine_version=cap_data.get("min_engine_version", "1.0.0"),
                metadata=cap_data.get("metadata", {}),
            ))

        return self.register_extension(manifest, capabilities)

    # ---- Dependencies ----

    def check_dependencies(self, extension_id: str) -> Dict[str, Any]:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return {
                "extension_id": extension_id,
                "found": False,
                "dependencies": [],
                "resolved": False,
            }

        result_deps: List[Dict[str, Any]] = []
        all_resolved = True

        for dep_id in manifest.dependencies:
            dep = self._extensions.get(dep_id)
            resolved = dep is not None and dep.status == ExtensionStatus.ACTIVE
            if not resolved:
                all_resolved = False

            result_deps.append({
                "dependency_id": dep_id,
                "dependency_name": dep.name if dep else "unknown",
                "resolved": resolved,
                "status": dep.status.value if dep else "not_found",
            })

        return {
            "extension_id": extension_id,
            "extension_name": manifest.name,
            "found": True,
            "dependencies": result_deps,
            "resolved": all_resolved,
            "total_dependencies": len(manifest.dependencies),
        }

    def _check_dependency_tree(self, extension_id: str) -> bool:
        visited: Set[str] = set()
        return self._traverse_dependencies(extension_id, visited)

    def _traverse_dependencies(self, extension_id: str, visited: Set[str]) -> bool:
        if extension_id in visited:
            return True

        visited.add(extension_id)
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return False

        for dep_id in manifest.dependencies:
            if not self._traverse_dependencies(dep_id, visited):
                return False

        return True

    # ---- Create ----

    def create_extension(
        self,
        name: str,
        extension_type: str,
        description: str = "",
    ) -> Optional[ExtensionManifest]:
        if not name.strip():
            return None

        try:
            ext_type = ExtensionType(extension_type.lower())
        except ValueError:
            ext_type = ExtensionType.SYSTEM

        manifest = ExtensionManifest(
            name=name.strip(),
            extension_type=ext_type,
            description=description,
            entry_point=f"extensions.{name.lower().replace(' ', '_')}",
            version="0.1.0",
        )

        self._extensions[manifest.id] = manifest
        self._dependency_graph[manifest.id] = set()
        self._log("extension_created", extension_id=manifest.id,
                  name=manifest.name, extension_type=ext_type.value)
        return manifest

    # ---- Validation ----

    def validate_extension(self, extension_id: str) -> Dict[str, Any]:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            return {
                "extension_id": extension_id,
                "valid": False,
                "errors": ["Extension not found"],
                "warnings": [],
            }

        errors: List[str] = []
        warnings: List[str] = []

        schema_errors = manifest.validate()
        errors.extend(schema_errors)

        if not manifest.capabilities:
            warnings.append("Extension has no declared capabilities")

        dep_check = self.check_dependencies(extension_id)
        if not dep_check.get("resolved", False):
            unresolved = [
                d["dependency_id"] for d in dep_check.get("dependencies", [])
                if not d["resolved"]
            ]
            errors.append(f"Unresolved dependencies: {', '.join(unresolved)}")

        for dep_id in manifest.dependencies:
            dep = self._extensions.get(dep_id)
            if dep and dep.status == ExtensionStatus.ERROR:
                warnings.append(f"Dependency '{dep_id}' is in error state")

        if manifest.source == ExtensionSource.EXTERNAL:
            warnings.append("External source extensions may pose security risks")

        return {
            "extension_id": extension_id,
            "extension_name": manifest.name,
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "status": manifest.status.value,
            "source": manifest.source.value,
        }

    # ---- Stats ----

    def get_sdk_stats(self) -> Dict[str, Any]:
        total = len(self._extensions)
        total_capabilities = len(self._capabilities)
        total_apis = len(self._apis)

        status_counts: Dict[str, int] = {}
        for ext in self._extensions.values():
            key = ext.status.value
            status_counts[key] = status_counts.get(key, 0) + 1

        type_counts: Dict[str, int] = {}
        for ext in self._extensions.values():
            key = ext.extension_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        source_counts: Dict[str, int] = {}
        for ext in self._extensions.values():
            key = ext.source.value
            source_counts[key] = source_counts.get(key, 0) + 1

        scope_counts: Dict[str, int] = {}
        for cap in self._capabilities.values():
            key = cap.scope.value
            scope_counts[key] = scope_counts.get(key, 0) + 1

        unresolved_deps = 0
        for ext in self._extensions.values():
            dep_result = self.check_dependencies(ext.id)
            if not dep_result.get("resolved", False):
                unresolved_deps += 1

        return {
            "total_extensions": total,
            "total_capabilities": total_capabilities,
            "total_apis": total_apis,
            "by_status": status_counts,
            "by_type": type_counts,
            "by_source": source_counts,
            "capabilities_by_scope": scope_counts,
            "unresolved_extensions": unresolved_deps,
            "load_errors": len(self._load_errors),
            "log_entries": len(self._event_log),
            "config": {
                "sandbox_enabled": self._config.sandbox_enabled,
                "auto_update": self._config.auto_update,
                "max_load_time_ms": self._config.max_load_time_ms,
                "max_extensions": self._config.max_extensions,
            },
        }

    # ---- Export ----

    def export_extension(self, extension_id: str, output_path: str) -> bool:
        manifest = self._extensions.get(extension_id)
        if manifest is None:
            self._log("extension_export_not_found", extension_id=extension_id)
            return False

        capabilities = self.get_capabilities_by_extension(extension_id)
        api = self._apis.get(extension_id)

        export_data: Dict[str, Any] = {
            "format_version": "1.0.0",
            "exported_at": _time_module.time(),
            "manifest": manifest.to_dict(),
            "capabilities": [cap.to_dict() for cap in capabilities],
        }

        if api:
            export_data["api"] = api.to_dict()

        try:
            with open(output_path, "w") as f:
                json.dump(export_data, f, indent=2)
        except OSError as e:
            self._log("extension_export_write_error",
                      extension_id=extension_id, path=output_path, error=str(e))
            return False

        self._log("extension_exported", extension_id=extension_id,
                  name=manifest.name, path=output_path)
        return True

    # ---- Config ----

    def configure_sdk(self, config: SDKConfig) -> None:
        self._config = config
        self._log("sdk_configured", config_name=config.name,
                  sandbox_enabled=config.sandbox_enabled)

    def get_config(self) -> SDKConfig:
        return self._config

    # ---- Extension Access ----

    def get_extension(self, extension_id: str) -> Optional[ExtensionManifest]:
        return self._extensions.get(extension_id)

    def list_extensions(
        self,
        extension_type: Optional[str] = None,
    ) -> List[ExtensionManifest]:
        extensions = list(self._extensions.values())
        if extension_type:
            try:
                et = ExtensionType(extension_type.lower())
            except ValueError:
                return []
            extensions = [e for e in extensions if e.extension_type == et]
        return sorted(extensions, key=lambda e: e.updated_at, reverse=True)

    def list_active_extensions(self) -> List[ExtensionManifest]:
        return [
            ext for ext in self._extensions.values()
            if ext.status == ExtensionStatus.ACTIVE
        ]

    # ---- API Registration ----

    def register_api(self, api: ExtensionAPI) -> bool:
        manifest = self._extensions.get(api.extension_id)
        if manifest is None:
            return False

        self._apis[api.extension_id] = api
        self._log("api_registered", extension_id=api.extension_id,
                  api_id=api.id, schema_version=api.schema_version)
        return True

    def get_api(self, extension_id: str) -> Optional[ExtensionAPI]:
        return self._apis.get(extension_id)

    # ---- Event Log ----

    def get_event_log(self, limit: int = 100) -> List[Dict[str, Any]]:
        return self._event_log[-limit:] if limit > 0 else list(self._event_log)

    def clear_event_log(self) -> None:
        self._event_log.clear()

    # ---- Helpers ----

    def _log(self, event: str, **fields: Any) -> None:
        entry: Dict[str, Any] = {
            "event": event,
            "timestamp": _time_module.time(),
        }
        entry.update(fields)
        self._event_log.append(entry)
        if len(self._event_log) > self.MAX_LOG_ENTRIES:
            self._event_log = self._event_log[-self.MAX_LOG_ENTRIES:]

    def reset(self) -> None:
        for ext_id, ext in list(self._extensions.items()):
            if ext.status == ExtensionStatus.ACTIVE:
                self.disable_extension(ext_id)
        self._extensions.clear()
        self._capabilities.clear()
        self._apis.clear()
        self._loaded_modules.clear()
        self._event_log.clear()
        self._load_errors.clear()
        self._dependency_graph.clear()
        self._config = SDKConfig()

    def get_stats(self) -> Dict[str, Any]:
        active_extensions = sum(
            1 for ext in self._extensions.values()
            if ext.status == ExtensionStatus.ACTIVE
        )

        return {
            "total_extensions": len(self._extensions),
            "active_extensions": active_extensions,
            "total_capabilities": len(self._capabilities),
            "registered_apis": len(self._apis),
        }


# ---------------------------------------------------------------------------
# Module Accessor
# ---------------------------------------------------------------------------


def get_extension_sdk() -> ExtensionSDK:
    return ExtensionSDK.get_instance()