"""
SparkAI Engine - Python Engine Interface

The SparkEngine integrates the ECS World with scene management,
providing a unified game engine API. AI agents interact with
the engine through this interface to create worlds, spawn entities,
and control the simulation loop.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sparkai.engine.ecs.world import World
from sparkai.engine.ecs.entity import Entity
from sparkai.engine.ecs.component import Component, ComponentRegistry
from sparkai.engine.ecs.system import System, SystemRegistry
from sparkai.engine.ecs.resource import ResourceManager


class SparkEngine:
    """
    Core game engine for SparkLabs.

    Manages ECS worlds, scenes, and the game loop.
    Provides the primary API for AI agents to interact with
    the game simulation.
    """

    _instance: Optional["SparkEngine"] = None

    def __init__(self):
        self._worlds: Dict[str, World] = {}
        self._active_world_id: Optional[str] = None
        self._resource_manager: ResourceManager = ResourceManager()
        self._running: bool = False
        self._delta_time: float = 0.016
        self._frame_count: int = 0
        self._scenes: Dict[str, "Scene"] = {}
        self._active_scene_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "SparkEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def create_world(self, name: str = "World") -> World:
        world = World(name=name)
        self._worlds[world.id] = world
        if not self._active_world_id:
            self._active_world_id = world.id
        return world

    def get_world(self, world_id: str) -> Optional[World]:
        return self._worlds.get(world_id)

    def get_active_world(self) -> Optional[World]:
        if self._active_world_id:
            return self._worlds.get(self._active_world_id)
        return None

    def set_active_world(self, world_id: str) -> bool:
        if world_id in self._worlds:
            self._active_world_id = world_id
            return True
        return False

    def list_worlds(self) -> List[Dict[str, Any]]:
        return [w.get_status() for w in self._worlds.values()]

    def delete_world(self, world_id: str) -> bool:
        if world_id in self._worlds:
            del self._worlds[world_id]
            if self._active_world_id == world_id:
                self._active_world_id = next(iter(self._worlds), None)
            return True
        return False

    @property
    def resources(self) -> ResourceManager:
        return self._resource_manager

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
        for world in self._worlds.values():
            world.start()

    def stop(self) -> None:
        self._running = False
        for world in self._worlds.values():
            world.stop()

    def update(self, delta_time: Optional[float] = None) -> None:
        if not self._running:
            return
        self._delta_time = delta_time or self._delta_time
        self._frame_count += 1
        for world in self._worlds.values():
            world.tick(self._delta_time)
        scene = self.get_active_scene()
        if scene:
            scene.update(self._delta_time)

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._running,
            "frame_count": self._frame_count,
            "world_count": len(self._worlds),
            "scene_count": len(self._scenes),
            "active_world": self._active_world_id,
            "active_scene": self._active_scene_id,
            "delta_time": self._delta_time,
            "component_types": ComponentRegistry.list_types(),
            "system_types": SystemRegistry.list_types(),
            "resource_count": self._resource_manager.count,
        }


@dataclass
class Scene:
    name: str = "Untitled Scene"
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    entities: Dict[str, "SceneEntity"] = field(default_factory=dict)

    def create_entity(self, name: str = "Entity", **kwargs) -> "SceneEntity":
        entity = SceneEntity(name=name, scene_id=self.id, **kwargs)
        self.entities[entity.id] = entity
        return entity

    def get_entity(self, entity_id: str) -> Optional["SceneEntity"]:
        return self.entities.get(entity_id)

    def find_entity_by_name(self, name: str) -> Optional["SceneEntity"]:
        for entity in self.entities.values():
            if entity.name == name:
                return entity
        return None

    def find_entities_by_tag(self, tag: str) -> List["SceneEntity"]:
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
class SceneEntity:
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
