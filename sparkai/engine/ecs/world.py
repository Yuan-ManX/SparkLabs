"""
SparkLabs ECS - World

The World is the top-level container for an ECS instance.
It holds the EntityManager, SystemScheduler, and provides
the game loop that drives all systems.

AI agents interact with the World to create/destroy entities,
add/remove systems, and control the simulation.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from sparkai.engine.ecs.component import Component, ComponentRegistry
from sparkai.engine.ecs.entity import Entity, EntityManager
from sparkai.engine.ecs.system import System, SystemScheduler, SystemRegistry


class World:
    """
    The central ECS world.

    Contains all entities and systems. Provides the game loop
    and event bus for inter-system and AI agent communication.
    """

    def __init__(self, name: str = "World"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self._entity_manager: EntityManager = EntityManager()
        self._system_scheduler: SystemScheduler = SystemScheduler()
        self._running: bool = False
        self._paused: bool = False
        self._delta_time: float = 0.016
        self._frame_count: int = 0
        self._total_time: float = 0.0
        self._last_update_time: float = 0.0
        self._target_fps: int = 60
        self._event_handlers: Dict[str, List[Callable]] = {}
        self._world_data: Dict[str, Any] = {}

    @property
    def entities(self) -> EntityManager:
        return self._entity_manager

    @property
    def systems(self) -> SystemScheduler:
        return self._system_scheduler

    @property
    def running(self) -> bool:
        return self._running

    @property
    def paused(self) -> bool:
        return self._paused

    @property
    def frame_count(self) -> int:
        return self._frame_count

    @property
    def delta_time(self) -> float:
        return self._delta_time

    @property
    def total_time(self) -> float:
        return self._total_time

    def create_entity(self, name: str = "Entity") -> Entity:
        entity = self._entity_manager.create_entity(name)
        self.emit("entity_created", {"entity_id": entity.id, "name": name})
        return entity

    def destroy_entity(self, entity_id: str) -> Optional[Entity]:
        entity = self._entity_manager.remove_entity(entity_id)
        if entity:
            self.emit("entity_destroyed", {"entity_id": entity_id})
        return entity

    def add_system(self, system_instance: System) -> System:
        system_instance.on_attach(self)
        self._system_scheduler.add_system(system_instance)
        self.emit("system_added", {"system_type": system_instance.system_type})
        return system_instance

    def remove_system(self, system_type: str) -> Optional[System]:
        removed = self._system_scheduler.remove_system(system_type)
        if removed:
            self.emit("system_removed", {"system_type": system_type})
        return removed

    def start(self) -> None:
        self._running = True
        self._paused = False
        self._last_update_time = time.time()
        self.emit("world_started", {"world_id": self.id})

    def stop(self) -> None:
        self._running = False
        self._paused = False
        self.emit("world_stopped", {"world_id": self.id})

    def pause(self) -> None:
        if self._running and not self._paused:
            self._paused = True
            self.emit("world_paused", {})

    def resume(self) -> None:
        if self._running and self._paused:
            self._paused = False
            self._last_update_time = time.time()
            self.emit("world_resumed", {})

    def tick(self, delta_time: Optional[float] = None) -> None:
        if not self._running or self._paused:
            return
        self._delta_time = delta_time or self._delta_time
        self._total_time += self._delta_time
        self._frame_count += 1
        self._system_scheduler.update(self._delta_time, self._entity_manager)
        self.emit("world_tick", {
            "frame": self._frame_count,
            "delta_time": self._delta_time,
        })

    def update(self) -> None:
        now = time.time()
        delta = now - self._last_update_time
        self._last_update_time = now
        self.tick(delta)

    def on(self, event: str, handler: Callable) -> None:
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)

    def off(self, event: str, handler: Callable) -> None:
        if event in self._event_handlers:
            self._event_handlers[event] = [
                h for h in self._event_handlers[event] if h != handler
            ]

    def emit(self, event: str, data: Any = None) -> None:
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                try:
                    handler(data)
                except Exception:
                    pass

    def set_data(self, key: str, value: Any) -> None:
        self._world_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        return self._world_data.get(key, default)

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "running": self._running,
            "paused": self._paused,
            "frame_count": self._frame_count,
            "delta_time": self._delta_time,
            "total_time": self._total_time,
            "target_fps": self._target_fps,
            "entity_count": self._entity_manager.count,
            "system_count": self._system_scheduler.system_count,
            "component_types": ComponentRegistry.list_types(),
            "system_types": [
                s["system_type"] for s in self._system_scheduler.list_systems()
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "entities": self._entity_manager.to_dict(),
            "systems": self._system_scheduler.list_systems(),
            "status": self.get_status(),
        }

    def __repr__(self) -> str:
        return (
            f"World({self.name}, entities={self._entity_manager.count}, "
            f"systems={self._system_scheduler.system_count})"
        )
