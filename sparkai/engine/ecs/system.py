"""
SparkLabs ECS - System Base, Registry, and Scheduler

Systems contain the logic that operates on entities with specific
component combinations. They implement the "behavior" of the game.

AI agents can create custom systems at runtime, enabling dynamic
gameplay behavior generation.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any, Dict, List, Optional, Set, Type, TypeVar

T = TypeVar("T", bound="System")


class SystemPriority(enum.IntEnum):
    INPUT = 100
    PHYSICS = 200
    AI = 300
    GAMEPLAY = 400
    ANIMATION = 500
    RENDER = 600
    AUDIO = 700
    UI = 800
    POST_PROCESS = 900


class System:
    """
    Base class for all ECS systems.

    Systems process entities that match their required components.
    Override `required_components` to specify which entities this
    system operates on.
    """

    system_type: str = "system"
    priority: int = SystemPriority.GAMEPLAY

    def __init__(self):
        self.id: str = str(uuid.uuid4())
        self.enabled: bool = True
        self._world: Optional[Any] = None

    @property
    def required_components(self) -> List[str]:
        return []

    def on_attach(self, world: Any) -> None:
        self._world = world

    def on_detach(self) -> None:
        self._world = None

    def on_enable(self) -> None:
        pass

    def on_disable(self) -> None:
        pass

    def update(self, delta_time: float, entities: List[Any]) -> None:
        raise NotImplementedError

    def to_dict(self) -> Dict[str, Any]:
        return {
            "system_type": self.system_type,
            "id": self.id,
            "enabled": self.enabled,
            "priority": self.priority,
            "required_components": self.required_components,
        }


class SystemRegistry:
    """
    Global registry for system types.

    AI agents can discover available system types and instantiate
    them dynamically.
    """

    _types: Dict[str, Type[System]] = {}

    @classmethod
    def register(cls, system_class: Type[System]) -> Type[System]:
        type_name = system_class.system_type
        cls._types[type_name] = system_class
        return system_class

    @classmethod
    def get(cls, type_name: str) -> Optional[Type[System]]:
        return cls._types.get(type_name)

    @classmethod
    def create(cls, type_name: str) -> Optional[System]:
        system_class = cls._types.get(type_name)
        if system_class:
            return system_class()
        return None

    @classmethod
    def list_types(cls) -> List[str]:
        return list(cls._types.keys())

    @classmethod
    def clear(cls) -> None:
        cls._types.clear()


def system(cls: Type[System]) -> Type[System]:
    """Decorator to auto-register a system class."""
    SystemRegistry.register(cls)
    return cls


class SystemScheduler:
    """
    Schedules and executes systems in priority order.

    Each frame, the scheduler:
    1. Sorts active systems by priority
    2. Queries entities matching each system's required components
    3. Calls system.update() with matching entities
    """

    def __init__(self):
        self._systems: Dict[str, System] = {}
        self._sorted_cache: Optional[List[System]] = None
        self._dirty: bool = True

    def add_system(self, system_instance: System) -> System:
        self._systems[system_instance.system_type] = system_instance
        self._dirty = True
        return system_instance

    def remove_system(self, system_type: str) -> Optional[System]:
        removed = self._systems.pop(system_type, None)
        if removed:
            removed.on_detach()
            self._dirty = True
        return removed

    def get_system(self, system_type: str) -> Optional[System]:
        return self._systems.get(system_type)

    def enable_system(self, system_type: str) -> None:
        sys_instance = self._systems.get(system_type)
        if sys_instance:
            sys_instance.enabled = True
            sys_instance.on_enable()

    def disable_system(self, system_type: str) -> None:
        sys_instance = self._systems.get(system_type)
        if sys_instance:
            sys_instance.enabled = False
            sys_instance.on_disable()

    def update(self, delta_time: float, entity_manager: Any) -> None:
        active_systems = self._get_sorted_active()
        for sys_instance in active_systems:
            required = sys_instance.required_components
            if required:
                entities = entity_manager.query(*required)
            else:
                entities = entity_manager.all_entities()
            sys_instance.update(delta_time, entities)

    def _get_sorted_active(self) -> List[System]:
        if self._dirty or self._sorted_cache is None:
            self._sorted_cache = sorted(
                [s for s in self._systems.values() if s.enabled],
                key=lambda s: s.priority,
            )
            self._dirty = False
        return self._sorted_cache

    @property
    def system_count(self) -> int:
        return len(self._systems)

    def list_systems(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._systems.values()]

    def clear(self) -> None:
        for sys_instance in self._systems.values():
            sys_instance.on_detach()
        self._systems.clear()
        self._dirty = True
