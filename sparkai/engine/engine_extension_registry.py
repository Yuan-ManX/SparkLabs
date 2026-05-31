"""
SparkLabs Engine - Extension Registry

Modular extension ecosystem that manages behaviors, object types,
and feature extensions with versioning, dependency resolution, and
marketplace-style discovery. Provides a unified system for publishing,
installing, updating, and querying extensions across the engine.

Architecture:
  ExtensionRegistry
    |-- ExtensionDefinition (metadata, authorship, marketplace info)
    |-- ExtensionVersion (semantic versioning with changelogs)
    |-- BehaviorModule (reusable behavior scripts and parameters)
    |-- ObjectTypeModule (custom object types with properties)
    |-- ExtensionDependency (declared inter-extension requirements)

Registry Features:
  - PUBLISH: register new extensions with versioning and tags
  - INSTALL: install from marketplace, local, URL, repository, or bundled
  - RESOLVE: dependency graph traversal and conflict detection
  - COMPATIBILITY: engine version compatibility checks
  - SEARCH: query extensions by type, tags, or free-text
  - STATS: aggregate metrics on installed and published extensions
"""

from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ExtensionType(Enum):
    BEHAVIOR = "behavior"
    OBJECT = "object"
    FEATURE = "feature"
    PLUGIN = "plugin"
    THEME = "theme"
    TOOL = "tool"
    TEMPLATE = "template"
    ASSET_PACK = "asset_pack"


class ExtensionStatus(Enum):
    PUBLISHED = "published"
    DRAFT = "draft"
    REVIEWING = "reviewing"
    DEPRECATED = "deprecated"
    REMOVED = "removed"


class CompatibilityLevel(Enum):
    FULL = "full"
    PARTIAL = "partial"
    UNTESTED = "untested"
    INCOMPATIBLE = "incompatible"


class InstallSource(Enum):
    MARKETPLACE = "marketplace"
    LOCAL = "local"
    URL = "url"
    REPOSITORY = "repository"
    BUNDLED = "bundled"


@dataclass
class ExtensionDefinition:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    display_name: str = ""
    description: str = ""
    extension_type: ExtensionType = ExtensionType.FEATURE
    status: ExtensionStatus = ExtensionStatus.DRAFT
    author_id: str = ""
    author_name: str = ""
    installed_version: str = ""
    installed_source: InstallSource = InstallSource.LOCAL
    tags: List[str] = field(default_factory=list)
    icon_url: str = ""
    homepage_url: str = ""
    repository_url: str = ""
    license_name: str = "MIT"
    engine_version_min: str = "1.0.0"
    engine_version_max: str = ""
    published_at: float = 0.0
    updated_at: float = field(default_factory=time.time)
    download_count: int = 0
    rating: float = 0.0
    is_installed: bool = False
    installed_at: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id, name=self.name, display_name=self.display_name,
            description=self.description, extension_type=self.extension_type.value,
            status=self.status.value, author_id=self.author_id,
            author_name=self.author_name, installed_version=self.installed_version,
            installed_source=self.installed_source.value, tags=self.tags,
            icon_url=self.icon_url, homepage_url=self.homepage_url,
            repository_url=self.repository_url, license_name=self.license_name,
            engine_version_min=self.engine_version_min,
            engine_version_max=self.engine_version_max,
            published_at=self.published_at, updated_at=self.updated_at,
            download_count=self.download_count, rating=self.rating,
            is_installed=self.is_installed, installed_at=self.installed_at,
            metadata=self.metadata,
        )


@dataclass
class ExtensionVersion:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    version: str = "1.0.0"
    major: int = 1
    minor: int = 0
    patch: int = 0
    changelog: str = ""
    release_date: float = field(default_factory=time.time)
    download_url: str = ""
    file_size_bytes: int = 0
    sha256_checksum: str = ""
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    min_engine_version: str = "1.0.0"
    max_engine_version: str = ""
    is_prerelease: bool = False
    is_yanked: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id, extension_id=self.extension_id, version=self.version,
            major=self.major, minor=self.minor, patch=self.patch,
            changelog=self.changelog, release_date=self.release_date,
            download_url=self.download_url, file_size_bytes=self.file_size_bytes,
            sha256_checksum=self.sha256_checksum, dependencies=self.dependencies,
            min_engine_version=self.min_engine_version,
            max_engine_version=self.max_engine_version,
            is_prerelease=self.is_prerelease, is_yanked=self.is_yanked,
        )


@dataclass
class BehaviorModule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    name: str = ""
    description: str = ""
    category: str = ""
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    script_template: str = ""
    runtime_script: str = ""
    is_enabled: bool = True
    execution_priority: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id, extension_id=self.extension_id, name=self.name,
            description=self.description, category=self.category,
            parameters=self.parameters, script_template=self.script_template,
            runtime_script=self.runtime_script, is_enabled=self.is_enabled,
            execution_priority=self.execution_priority, tags=self.tags,
            metadata=self.metadata,
        )


@dataclass
class ObjectTypeModule:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    name: str = ""
    description: str = ""
    base_type: str = "Sprite"
    properties: List[Dict[str, Any]] = field(default_factory=list)
    default_behavior: str = ""
    icon_name: str = ""
    category: str = ""
    is_user_creatable: bool = True
    is_visible_in_editor: bool = True
    runtime_class: str = ""
    editor_script: str = ""
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id, extension_id=self.extension_id, name=self.name,
            description=self.description, base_type=self.base_type,
            properties=self.properties, default_behavior=self.default_behavior,
            icon_name=self.icon_name, category=self.category,
            is_user_creatable=self.is_user_creatable,
            is_visible_in_editor=self.is_visible_in_editor,
            runtime_class=self.runtime_class, editor_script=self.editor_script,
            tags=self.tags, metadata=self.metadata,
        )


@dataclass
class ExtensionDependency:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    extension_id: str = ""
    dependency_extension_id: str = ""
    dependency_name: str = ""
    version_requirement: str = ">=1.0.0"
    is_optional: bool = False
    is_resolved: bool = False
    resolved_version: str = ""
    conflict_with: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return dict(
            id=self.id, extension_id=self.extension_id,
            dependency_extension_id=self.dependency_extension_id,
            dependency_name=self.dependency_name,
            version_requirement=self.version_requirement,
            is_optional=self.is_optional, is_resolved=self.is_resolved,
            resolved_version=self.resolved_version,
            conflict_with=self.conflict_with, metadata=self.metadata,
        )


class ExtensionRegistry:
    """Modular extension ecosystem managing behaviors,
    object types, and feature extensions with dependency resolution."""

    _instance: Optional["ExtensionRegistry"] = None
    _lock = threading.RLock()

    MAX_SEARCH_RESULTS = 50
    MAX_INSTALL_LOG_ENTRIES = 200

    def __init__(self) -> None:
        self._extensions: Dict[str, ExtensionDefinition] = {}
        self._versions: Dict[str, List[ExtensionVersion]] = {}
        self._installed: Dict[str, ExtensionDefinition] = {}
        self._behaviors: Dict[str, BehaviorModule] = {}
        self._object_types: Dict[str, ObjectTypeModule] = {}
        self._dependency_graph: Dict[str, List[ExtensionDependency]] = {}
        self._install_log: List[Dict[str, Any]] = []
        self._engine_version: str = "1.0.0"

    @classmethod
    def get_instance(cls) -> "ExtensionRegistry":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    # ---- Publishing ----

    def publish_extension(self,
                          definition: ExtensionDefinition,
                          version: ExtensionVersion,
                          author_id: str,
                          tags: List[str],
                          dependencies: List[ExtensionDependency]) -> Optional[ExtensionDefinition]:
        if definition.id in self._extensions:
            existing = self._extensions[definition.id]
            if existing.status not in (ExtensionStatus.DRAFT, ExtensionStatus.REMOVED):
                return None

        definition.author_id = author_id
        definition.tags = tags
        definition.status = ExtensionStatus.PUBLISHED
        definition.published_at = time.time()
        definition.updated_at = time.time()

        self._extensions[definition.id] = definition
        self._versions.setdefault(definition.id, []).append(version)
        self._dependency_graph[definition.id] = list(dependencies)
        self._log("extension_published", definition=definition, version=version.version)
        return definition

    # ---- Installation ----

    def install_extension(self,
                          extension_id: str,
                          version: Optional[str] = None,
                          source: str = "marketplace") -> Optional[ExtensionDefinition]:
        definition = self._extensions.get(extension_id)
        if definition is None:
            return None

        src = self._parse_install_source(source)
        target_version = version or self._latest_version_for(extension_id)
        if target_version is None:
            return None

        definition.installed_version = target_version
        definition.installed_source = src
        definition.is_installed = True
        definition.installed_at = time.time()
        definition.download_count += 1
        self._installed[extension_id] = definition
        self._log("extension_installed", definition=definition,
                  version=target_version, source=src.value)
        return definition

    def uninstall_extension(self, extension_id: str) -> bool:
        definition = self._installed.pop(extension_id, None)
        if definition is None:
            return False

        definition.is_installed = False
        definition.installed_version = ""
        definition.installed_at = 0.0
        self._behaviors = {
            bid: bm for bid, bm in self._behaviors.items()
            if bm.extension_id != extension_id
        }
        self._object_types = {
            oid: ot for oid, ot in self._object_types.items()
            if ot.extension_id != extension_id
        }
        self._log("extension_uninstalled", definition=definition)
        return True

    # ---- Behavior Registration ----

    def register_behavior(self,
                          extension_id: str,
                          name: str,
                          description: str,
                          parameters: List[Dict[str, Any]],
                          script_template: str) -> Optional[BehaviorModule]:
        if extension_id not in self._installed:
            return None

        behavior = BehaviorModule(
            extension_id=extension_id, name=name, description=description,
            parameters=parameters, script_template=script_template,
        )
        self._behaviors[behavior.id] = behavior
        self._log("behavior_registered", behavior_id=behavior.id,
                  behavior_name=name, extension_id=extension_id)
        return behavior

    # ---- Object Type Registration ----

    def register_object_type(self,
                             extension_id: str,
                             name: str,
                             description: str,
                             base_type: str,
                             properties: List[Dict[str, Any]],
                             default_behavior: str) -> Optional[ObjectTypeModule]:
        if extension_id not in self._installed:
            return None

        object_type = ObjectTypeModule(
            extension_id=extension_id, name=name, description=description,
            base_type=base_type, properties=properties,
            default_behavior=default_behavior,
        )
        self._object_types[object_type.id] = object_type
        self._log("object_type_registered", object_type_id=object_type.id,
                  object_type_name=name, extension_id=extension_id)
        return object_type

    # ---- Dependency Resolution ----

    def resolve_dependencies(self, extension_id: str) -> List[ExtensionDependency]:
        dependencies = self._dependency_graph.get(extension_id, [])
        for dep in dependencies:
            if dep.dependency_extension_id in self._installed:
                dep.is_resolved = True
                dep.resolved_version = (
                    self._installed[dep.dependency_extension_id].installed_version
                )
            else:
                dep.is_resolved = False
                dep.resolved_version = ""
        return dependencies

    # ---- Compatibility ----

    def check_compatibility(self,
                            extension_id: str,
                            engine_version: str) -> CompatibilityLevel:
        definition = self._extensions.get(extension_id)
        if definition is None:
            return CompatibilityLevel.INCOMPATIBLE

        if not definition.engine_version_min and not definition.engine_version_max:
            return CompatibilityLevel.UNTESTED

        if definition.engine_version_min:
            if not self._version_ge(engine_version, definition.engine_version_min):
                return CompatibilityLevel.INCOMPATIBLE

        if definition.engine_version_max:
            if not self._version_le(engine_version, definition.engine_version_max):
                return CompatibilityLevel.PARTIAL

        if definition.status == ExtensionStatus.DEPRECATED:
            return CompatibilityLevel.PARTIAL

        return CompatibilityLevel.FULL

    # ---- Search ----

    def search_extensions(self,
                          query: str = "",
                          extension_type: Optional[str] = None,
                          tags: Optional[List[str]] = None) -> List[ExtensionDefinition]:
        results: List[ExtensionDefinition] = []

        for ext in self._extensions.values():
            if extension_type:
                try:
                    et = ExtensionType(extension_type.lower())
                except ValueError:
                    continue
                if ext.extension_type != et:
                    continue

            if tags and not any(t in ext.tags for t in tags):
                continue

            q = query.lower()
            if q and not (
                q in ext.name.lower() or q in ext.display_name.lower()
                or q in ext.description.lower()
            ):
                continue

            results.append(ext)

        results.sort(key=lambda e: e.download_count, reverse=True)
        return results[:self.MAX_SEARCH_RESULTS]

    # ---- Installed Extensions ----

    def get_installed_extensions(self,
                                 extension_type: Optional[str] = None) -> List[ExtensionDefinition]:
        installed = list(self._installed.values())
        if extension_type:
            try:
                et = ExtensionType(extension_type.lower())
            except ValueError:
                return []
            installed = [e for e in installed if e.extension_type == et]
        return sorted(installed, key=lambda e: e.installed_at, reverse=True)

    # ---- Update ----

    def update_extension(self,
                         extension_id: str,
                         to_version: str) -> Optional[ExtensionDefinition]:
        definition = self._installed.get(extension_id)
        if definition is None:
            return None

        previous_version = definition.installed_version
        definition.installed_version = to_version
        definition.updated_at = time.time()
        self._extensions[extension_id] = definition
        self._log("extension_updated", definition=definition,
                  from_version=previous_version, to_version=to_version)
        return definition

    # ---- Stats ----

    def get_stats(self) -> Dict[str, Any]:
        total_published = len(self._extensions)
        total_installed = len(self._installed)
        total_behaviors = len(self._behaviors)
        total_object_types = len(self._object_types)

        installed_by_type: Dict[str, int] = {}
        for ext in self._installed.values():
            key = ext.extension_type.value
            installed_by_type[key] = installed_by_type.get(key, 0) + 1

        published_by_status: Dict[str, int] = {}
        for ext in self._extensions.values():
            key = ext.status.value
            published_by_status[key] = published_by_status.get(key, 0) + 1

        unresolved_deps = sum(
            1 for dep_list in self._dependency_graph.values()
            for dep in dep_list
            if dep.dependency_extension_id not in self._installed
        )

        return {
            "total_published_extensions": total_published,
            "total_installed_extensions": total_installed,
            "total_behaviors": total_behaviors,
            "total_object_types": total_object_types,
            "installed_by_type": installed_by_type,
            "published_by_status": published_by_status,
            "unresolved_dependencies": unresolved_deps,
            "total_install_log_entries": len(self._install_log),
            "engine_version": self._engine_version,
            "max_search_results": self.MAX_SEARCH_RESULTS,
        }

    # ---- Helpers ----

    def _latest_version_for(self, extension_id: str) -> Optional[str]:
        versions = self._versions.get(extension_id, [])
        if not versions:
            return None
        filtered = [v for v in versions if not v.is_yanked]
        if not filtered:
            return None
        releases = [v for v in filtered if not v.is_prerelease]
        target = releases if releases else filtered
        target.sort(key=lambda v: (v.major, v.minor, v.patch), reverse=True)
        return target[0].version

    def _parse_install_source(self, source: str) -> InstallSource:
        try:
            return InstallSource(source.lower())
        except ValueError:
            return InstallSource.MARKETPLACE

    def _log(self, action: str, **fields: Any) -> None:
        entry: Dict[str, Any] = {"action": action, "timestamp": time.time()}
        entry.update(fields)
        self._install_log.append(entry)
        if len(self._install_log) > self.MAX_INSTALL_LOG_ENTRIES:
            self._install_log = self._install_log[-self.MAX_INSTALL_LOG_ENTRIES:]

    @staticmethod
    def _version_ge(a: str, b: str) -> bool:
        pa, pb = _parse_version_parts(a), _parse_version_parts(b)
        max_len = max(len(pa), len(pb))
        pa += [0] * (max_len - len(pa))
        pb += [0] * (max_len - len(pb))
        return pa >= pb

    @staticmethod
    def _version_le(a: str, b: str) -> bool:
        pa, pb = _parse_version_parts(a), _parse_version_parts(b)
        max_len = max(len(pa), len(pb))
        pa += [0] * (max_len - len(pa))
        pb += [0] * (max_len - len(pb))
        return pa <= pb


def _parse_version_parts(v: str) -> List[int]:
    return [int(x) for x in v.split(".")]


def get_extension_registry() -> ExtensionRegistry:
    return ExtensionRegistry.get_instance()