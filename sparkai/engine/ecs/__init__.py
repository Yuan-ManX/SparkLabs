"""
SparkLabs ECS - Entity Component System Core

The ECS architecture separates game objects into three core concepts:
- Entity: A lightweight container with a unique ID
- Component: Pure data containers that define entity properties
- System: Logic processors that operate on entities with specific components

This design enables AI-native game development where AI agents can
dynamically compose, modify, and reason about game entities at runtime.
"""

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
