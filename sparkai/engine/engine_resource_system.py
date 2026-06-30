"""
SparkLabs Engine - Resource System

Serializable resource system with a type registry. Resources of any
registered type (textures, materials, meshes, audio, scripts, prefabs,
animations, fonts, shaders, or custom types) can be created, loaded,
saved, referenced, and released. A type registry captures the schema and
validator for each known resource type so that resources remain
introspectable and verifiable.

Architecture:
  ResourceSystem (Singleton)
    |-- ResourceType      (built-in resource categories)
    |-- Resource          (a single resource instance)
    |-- ResourceTypeEntry (a registered type with schema and validator)
    |-- ResourceSystemSnapshot (immutable snapshot of system state)

Lifecycle:
  1. register_type(type_name, schema) -> bool
  2. create_resource(name, resource_type, data) -> Resource
  3. load_resource(path) -> Resource / save_resource(resource_id, path) -> bool
  4. reference_resource(resource_id) -> int / release_resource(resource_id) -> int
  5. get_snapshot() -> ResourceSystemSnapshot
  6. reset() -> None

Usage:
    system = get_resource_system()
    system.register_type("texture", {"width": int, "height": int})
    res = system.create_resource("hero_diffuse", ResourceType.TEXTURE, {"width": 256})
    system.reference_resource(res.resource_id)
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


# =============================================================================
# Enums
# =============================================================================


class ResourceType(Enum):
    """Built-in resource categories."""
    TEXTURE = "texture"
    MATERIAL = "material"
    MESH = "mesh"
    AUDIO = "audio"
    SCRIPT = "script"
    PREFAB = "prefab"
    ANIMATION = "animation"
    FONT = "font"
    SHADER = "shader"
    CUSTOM = "custom"


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class Resource:
    """A single resource instance.

    Attributes:
        resource_id: Unique identifier (auto-generated).
        name: Human-readable name of the resource.
        resource_type: Category of the resource.
        path: Filesystem path the resource was loaded from or saved to.
        data: Mutable data payload for the resource.
        refs: Current reference count.
        metadata: Auxiliary metadata bag.
    """
    resource_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    resource_type: ResourceType = ResourceType.CUSTOM
    path: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    refs: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "resource_id": self.resource_id,
            "name": self.name,
            "resource_type": self.resource_type.value,
            "path": self.path,
            "data": dict(self.data),
            "refs": self.refs,
            "metadata": dict(self.metadata),
        }


@dataclass
class ResourceTypeEntry:
    """A registered resource type with schema and validator.

    Attributes:
        type_name: Name of the type (matches a :class:`ResourceType` value
            or a custom string).
        schema: Schema describing the expected fields of the resource data.
        validator: Optional callable used to validate resource data. May
            be ``None``.
        instance_count: Number of resources currently using this type.
    """
    type_name: str = ""
    schema: Dict[str, Any] = field(default_factory=dict)
    validator: Optional[Callable[[Dict[str, Any]], bool]] = None
    instance_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        # Intentionally omits the callable, which is not serializable.
        return {
            "type_name": self.type_name,
            "schema": dict(self.schema),
            "instance_count": self.instance_count,
        }


@dataclass
class ResourceSystemSnapshot:
    """Immutable snapshot of the resource system state.

    Attributes:
        total_resources: Number of registered resources.
        total_types: Number of registered types.
        total_references: Sum of all resource reference counts.
        resources: Serialized resources captured at snapshot time.
        types: Serialized types captured at snapshot time.
        timestamp: Time the snapshot was taken.
    """
    total_resources: int = 0
    total_types: int = 0
    total_references: int = 0
    resources: List[Dict[str, Any]] = field(default_factory=list)
    types: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_resources": self.total_resources,
            "total_types": self.total_types,
            "total_references": self.total_references,
            "resources": list(self.resources),
            "types": list(self.types),
            "timestamp": self.timestamp,
        }


# =============================================================================
# Resource System (Singleton)
# =============================================================================


class ResourceSystem:
    """Singleton resource system with a type registry.

    Manages resource lifecycle (create, load, save, reference, release) and
    a type registry that captures the schema and validator for each known
    resource type. All public methods are thread-safe.

    Typical usage::

        system = ResourceSystem.get_instance()
        system.register_type("texture", {"width": int, "height": int})
        res = system.create_resource("hero", ResourceType.TEXTURE, {"width": 256})
        system.reference_resource(res.resource_id)
    """

    _instance: Optional["ResourceSystem"] = None
    _lock: threading.RLock = threading.RLock()

    # ------------------------------------------------------------------
    # Singleton management
    # ------------------------------------------------------------------

    def __new__(cls) -> "ResourceSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        # Guard against re-initialization of the singleton.
        if getattr(self, "_initialized", False):
            return
        self._instance_lock: threading.RLock = threading.RLock()
        self._initialized: bool = True
        self._resources: Dict[str, Resource] = {}
        self._types: Dict[str, ResourceTypeEntry] = {}
        # Seed the registry with the built-in types.
        for resource_type in ResourceType:
            self._types[resource_type.value] = ResourceTypeEntry(
                type_name=resource_type.value,
            )
        self._total_created: int = 0
        self._total_loaded: int = 0
        self._total_saved: int = 0

    @classmethod
    def get_instance(cls) -> "ResourceSystem":
        """Return the singleton ResourceSystem instance (thread-safe)."""
        return cls()

    # ------------------------------------------------------------------
    # Type Registry
    # ------------------------------------------------------------------

    def register_type(
        self,
        type_name: str,
        schema: Optional[Dict[str, Any]] = None,
        validator: Optional[Callable[[Dict[str, Any]], bool]] = None,
    ) -> bool:
        """Register a resource type with an optional schema and validator.

        If the type already exists, its schema and validator are updated.

        Args:
            type_name: Name of the type to register.
            schema: Schema describing the expected fields of the data.
            validator: Optional callable used to validate resource data.

        Returns:
            True if the type was newly registered, False if it already
            existed (and was updated).
        """
        with self._instance_lock:
            existed = type_name in self._types
            entry = self._types.get(type_name)
            if entry is None:
                entry = ResourceTypeEntry(type_name=type_name)
            entry.schema = dict(schema) if schema else {}
            entry.validator = validator
            self._types[type_name] = entry
            return not existed

    def get_types(self) -> List[ResourceTypeEntry]:
        """Return a copy of all registered resource types."""
        with self._instance_lock:
            return list(self._types.values())

    # ------------------------------------------------------------------
    # Resource Lifecycle
    # ------------------------------------------------------------------

    def create_resource(
        self,
        name: str,
        resource_type: ResourceType,
        data: Optional[Dict[str, Any]] = None,
    ) -> Resource:
        """Create and register a new resource.

        Args:
            name: Human-readable name of the resource.
            resource_type: Category of the resource.
            data: Initial data payload for the resource.

        Returns:
            The newly created Resource.
        """
        with self._instance_lock:
            payload = dict(data) if data else {}
            resource = Resource(
                name=name,
                resource_type=resource_type,
                data=payload,
                refs=0,
            )
            self._resources[resource.resource_id] = resource
            type_entry = self._types.get(resource_type.value)
            if type_entry is not None:
                type_entry.instance_count += 1
            self._total_created += 1
            return resource

    def load_resource(self, path: str) -> Resource:
        """Load a resource from a JSON file on disk.

        Args:
            path: Filesystem path to load from.

        Returns:
            The loaded Resource, registered with the system.

        Raises:
            FileNotFoundError: If the path does not exist.
            ValueError: If the file content is not a valid resource payload.
        """
        with self._instance_lock:
            if not os.path.exists(path):
                raise FileNotFoundError(f"Resource file not found: {path}")
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)

            type_value = payload.get("resource_type", ResourceType.CUSTOM.value)
            try:
                resource_type = ResourceType(type_value)
            except ValueError:
                resource_type = ResourceType.CUSTOM

            resource = Resource(
                resource_id=payload.get("resource_id") or uuid.uuid4().hex,
                name=payload.get("name", ""),
                resource_type=resource_type,
                path=path,
                data=dict(payload.get("data", {})),
                refs=0,
                metadata=dict(payload.get("metadata", {})),
            )
            self._resources[resource.resource_id] = resource
            type_entry = self._types.get(resource_type.value)
            if type_entry is not None:
                type_entry.instance_count += 1
            self._total_loaded += 1
            return resource

    def save_resource(self, resource_id: str, path: str) -> bool:
        """Persist a resource to a JSON file on disk.

        Args:
            resource_id: Identifier of the resource to save.
            path: Filesystem path to save to.

        Returns:
            True if the resource was saved, False if not found.
        """
        with self._instance_lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return False
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(resource.to_dict(), handle, indent=2)
            resource.path = path
            self._total_saved += 1
            return True

    # ------------------------------------------------------------------
    # Reference Counting
    # ------------------------------------------------------------------

    def reference_resource(self, resource_id: str) -> int:
        """Increment the reference count of a resource.

        Args:
            resource_id: Identifier of the resource.

        Returns:
            The new reference count, or -1 if the resource was not found.
        """
        with self._instance_lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return -1
            resource.refs += 1
            return resource.refs

    def release_resource(self, resource_id: str) -> int:
        """Decrement the reference count of a resource.

        When the count reaches zero the resource is removed from the system.

        Args:
            resource_id: Identifier of the resource.

        Returns:
            The new reference count, or -1 if the resource was not found.
        """
        with self._instance_lock:
            resource = self._resources.get(resource_id)
            if resource is None:
                return -1
            resource.refs = max(0, resource.refs - 1)
            if resource.refs == 0:
                type_entry = self._types.get(resource.resource_type.value)
                if type_entry is not None:
                    type_entry.instance_count = max(
                        0, type_entry.instance_count - 1
                    )
                del self._resources[resource_id]
                return 0
            return resource.refs

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """Return the resource with the given id, if registered."""
        with self._instance_lock:
            return self._resources.get(resource_id)

    def get_all_resources(self) -> List[Resource]:
        """Return a copy of all registered resources."""
        with self._instance_lock:
            return list(self._resources.values())

    # ------------------------------------------------------------------
    # Status and Snapshot
    # ------------------------------------------------------------------

    def get_status(self) -> Dict[str, Any]:
        """Return a summary of the current system state."""
        with self._instance_lock:
            total_refs = sum(r.refs for r in self._resources.values())
            return {
                "total_resources": len(self._resources),
                "total_types": len(self._types),
                "total_references": total_refs,
                "total_created": self._total_created,
                "total_loaded": self._total_loaded,
                "total_saved": self._total_saved,
            }

    def get_snapshot(self) -> ResourceSystemSnapshot:
        """Capture an immutable snapshot of the system state."""
        with self._instance_lock:
            total_refs = sum(r.refs for r in self._resources.values())
            return ResourceSystemSnapshot(
                total_resources=len(self._resources),
                total_types=len(self._types),
                total_references=total_refs,
                resources=[r.to_dict() for r in self._resources.values()],
                types=[t.to_dict() for t in self._types.values()],
                timestamp=time.time(),
            )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """Clear all resources, types, and counters.

        The built-in types are re-seeded after the clear so the registry
        remains usable without an explicit re-registration step.
        """
        with self._instance_lock:
            self._resources.clear()
            self._types.clear()
            for resource_type in ResourceType:
                self._types[resource_type.value] = ResourceTypeEntry(
                    type_name=resource_type.value,
                )
            self._total_created = 0
            self._total_loaded = 0
            self._total_saved = 0


# =============================================================================
# Module-Level Accessor
# =============================================================================


def get_resource_system() -> ResourceSystem:
    """Return the singleton ResourceSystem instance."""
    return ResourceSystem.get_instance()
