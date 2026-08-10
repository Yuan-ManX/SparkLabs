"""
SparkLabs ECS - Entity Component System Core"""

from sparkai.engine.ecs.component import (
    Component,
    ComponentRegistry,
)
from sparkai.engine.ecs.entity import (
    Entity,
    EntityManager,
)
from sparkai.engine.ecs.system import (
    System,
    SystemPriority,
    SystemRegistry,
    SystemScheduler,
)
from sparkai.engine.ecs.world import World

__all__ = [
    "Component",
    "ComponentRegistry",
    "Entity",
    "EntityManager",
    "System",
    "SystemPriority",
    "SystemRegistry",
    "SystemScheduler",
    "World",
]
