"""
SparkAI Engine - Python Engine Interface
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


class SparkEngine:
    """
    Python interface to the SparkLabs C++ game engine.
    Provides scene management, entity creation, and engine control.
    """

    _instance: Optional["SparkEngine"] = None

    def __init__(self):
        self._scenes: Dict[str, "Scene"] = {}
        self._active_scene_id: Optional[str] = None
        self._running = False
        self._delta_time = 0.016
        self._frame_count = 0

    @classmethod
    def get_instance(cls) -> "SparkEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_scene(self, name: str = "Untitled Scene") -> "Scene":
        scene = Scene(name=name)
        self._scenes[scene.id] = scene
        if not self._active_scene_id:
            self._active_scene_id = scene.id
        return scene

    def get_scene(self, scene_id: str) -> Optional["Scene"]:
        return self._scenes.get(scene_id)

    def get_active_scene(self) -> Optional["Scene"]:
        if self._active_scene_id:
            return self._scenes.get(self._active_scene_id)
        return None

    def set_active_scene(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            self._active_scene_id = scene_id
            return True
        return False

    def list_scenes(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._scenes.values()]

    def delete_scene(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            if self._active_scene_id == scene_id:
                self._active_scene_id = next(iter(self._scenes), None)
            return True
        return False

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False

    def update(self, delta_time: Optional[float] = None) -> None:
        if not self._running:
            return
        self._delta_time = delta_time or self._delta_time
        self._frame_count += 1
        scene = self.get_active_scene()
        if scene:
            scene.update(self._delta_time)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "scene_count": len(self._scenes),
            "active_scene": self._active_scene_id,
            "delta_time": self._delta_time,
        }


@dataclass
class Scene:
    name: str = "Untitled Scene"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entities: Dict[str, "Entity"] = field(default_factory=dict)

    def create_entity(self, name: str = "Entity", **kwargs) -> "Entity":
        entity = Entity(name=name, scene_id=self.id, **kwargs)
        self.entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional["Entity"]:
        return self.entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional["Entity"]:
        for entity in self.entities.values():
            if entity.name == name:
                return entity
        return None

    def find_entities_by_tag(self, tag: str) -> List["Entity"]:
        return [e for e in self.entities.values() if tag in e.tags]

    def remove_entity(self, entity_id: str) -> bool:
        if entity_id in self.entities:
            del self.entities[entity_id]
            return True
        return False

    def update(self, delta_time: float) -> None:
        for entity in self.entities.values():
            entity.update(delta_time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entity_count": len(self.entities),
            "entities": [e.to_dict() for e in self.entities.values()],
        }


@dataclass
class Entity:
    name: str = "Entity"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    scene_id: str = ""
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    rotation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    scale: List[float] = field(default_factory=lambda: [1.0, 1.0, 1.0])
    tags: List[str] = field(default_factory=list)
    components: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    properties: Dict[str, Any] = field(default_factory=dict)

    def add_component(self, component_type: str, data: Optional[Dict] = None) -> None:
        self.components[component_type] = data or {}

    def remove_component(self, component_type: str) -> bool:
        if component_type in self.components:
            del self.components[component_type]
            return True
        return False

    def add_tag(self, tag: str) -> None:
        if tag not in self.tags:
            self.tags.append(tag)

    def set_position(self, x: float, y: float, z: float) -> None:
        self.position = [x, y, z]

    def set_rotation(self, x: float, y: float, z: float) -> None:
        self.rotation = [x, y, z]

    def set_scale(self, x: float, y: float, z: float) -> None:
        self.scale = [x, y, z]

    def update(self, delta_time: float) -> None:
        pass

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "position": self.position,
            "rotation": self.rotation,
            "scale": self.scale,
            "tags": self.tags,
            "components": self.components,
            "properties": self.properties,
        }
