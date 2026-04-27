"""
SparkLabs ECS - Resource Management

Handles loading, caching, and lifecycle of game resources
such as images, audio, scripts, and data files.
AI agents can query available resources and load new ones at runtime.
"""

from __future__ import annotations

import uuid
from enum import Enum
from typing import Any, Dict, List, Optional


class ResourceType(Enum):
    IMAGE = "image"
    AUDIO = "audio"
    SCRIPT = "script"
    DATA = "data"
    SCENE = "scene"
    PREFAB = "prefab"
    SHADER = "shader"
    FONT = "font"
    ANIMATION = "animation"
    MESH = "mesh"
    MATERIAL = "material"
    TEXTURE = "texture"


class Resource:
    """Represents a loadable game resource."""

    def __init__(
        self,
        name: str,
        resource_type: ResourceType,
        url: str = "",
        preload: bool = False,
    ):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.resource_type: ResourceType = resource_type
        self.url: str = url
        self.preload: bool = preload
        self.loaded: bool = False
        self.data: Any = None
        self.metadata: Dict[str, Any] = {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.resource_type.value,
            "url": self.url,
            "preload": self.preload,
            "loaded": self.loaded,
        }


class ResourceManager:
    """
    Manages game resources with loading, caching, and reference counting.

    AI agents can discover available resources, load new ones,
    and create resource bundles for procedural content.
    """

    def __init__(self):
        self._resources: Dict[str, Resource] = {}
        self._type_index: Dict[ResourceType, List[str]] = {}
        self._reference_counts: Dict[str, int] = {}

    def register(
        self,
        name: str,
        resource_type: ResourceType,
        url: str = "",
        preload: bool = False,
    ) -> Resource:
        resource = Resource(
            name=name,
            resource_type=resource_type,
            url=url,
            preload=preload,
        )
        self._resources[resource.id] = resource
        if resource_type not in self._type_index:
            self._type_index[resource_type] = []
        self._type_index[resource_type].append(resource.id)
        return resource

    def get(self, resource_id: str) -> Optional[Resource]:
        return self._resources.get(resource_id)

    def get_by_name(self, name: str) -> Optional[Resource]:
        for resource in self._resources.values():
            if resource.name == name:
                return resource
        return None

    def remove(self, resource_id: str) -> Optional[Resource]:
        resource = self._resources.pop(resource_id, None)
        if resource:
            type_list = self._type_index.get(resource.resource_type, [])
            if resource_id in type_list:
                type_list.remove(resource_id)
            self._reference_counts.pop(resource_id, None)
        return resource

    def list_by_type(self, resource_type: ResourceType) -> List[Resource]:
        ids = self._type_index.get(resource_type, [])
        return [self._resources[rid] for rid in ids if rid in self._resources]

    def list_all(self) -> List[Resource]:
        return list(self._resources.values())

    def retain(self, resource_id: str) -> None:
        self._reference_counts[resource_id] = self._reference_counts.get(resource_id, 0) + 1

    def release(self, resource_id: str) -> int:
        count = self._reference_counts.get(resource_id, 0)
        if count > 0:
            count -= 1
            self._reference_counts[resource_id] = count
            if count == 0:
                self.remove(resource_id)
        return count

    def get_preload_list(self) -> List[Resource]:
        return [r for r in self._resources.values() if r.preload and not r.loaded]

    @property
    def count(self) -> int:
        return len(self._resources)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "count": self.count,
            "resources": [r.to_dict() for r in self._resources.values()],
            "type_counts": {
                rt.value: len(ids) for rt, ids in self._type_index.items()
            },
        }
