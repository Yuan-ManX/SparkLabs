"""
SparkAI Engine Package

Core engine providing ECS architecture, scene management,
and AI-native game development capabilities.
"""

from sparkai.engine.engine import SparkEngine
from sparkai.engine.ecs import (
    Component,
    ComponentRegistry,
    Entity,
    EntityManager,
    System,
    SystemPriority,
    SystemRegistry,
    SystemScheduler,
    World,
)
from sparkai.engine.ecs.components import (
    Transform,
    Renderable,
    SpriteRenderer,
    TextRenderer,
    PhysicsBody,
    Collider,
    Camera,
    AudioSource,
    Animator,
    InputReceiver,
    AIBrain,
    Script,
    Tween,
)
from sparkai.engine.ecs.systems import (
    TransformSystem,
    PhysicsSystem,
    RenderSystem,
    AnimationSystem,
    AudioSystem,
    InputSystem,
    AISystem,
    TweenSystem,
    ScriptSystem,
    CollisionSystem,
)
from sparkai.engine.ecs.resource import (
    Resource,
    ResourceManager,
    ResourceType,
)

__all__ = [
    "SparkEngine",
    "Component",
    "ComponentRegistry",
    "Entity",
    "EntityManager",
    "System",
    "SystemPriority",
    "SystemRegistry",
    "SystemScheduler",
    "World",
    "Transform",
    "Renderable",
    "SpriteRenderer",
    "TextRenderer",
    "PhysicsBody",
    "Collider",
    "Camera",
    "AudioSource",
    "Animator",
    "InputReceiver",
    "AIBrain",
    "Script",
    "Tween",
    "TransformSystem",
    "PhysicsSystem",
    "RenderSystem",
    "AnimationSystem",
    "AudioSystem",
    "InputSystem",
    "AISystem",
    "TweenSystem",
    "ScriptSystem",
    "CollisionSystem",
    "Resource",
    "ResourceManager",
    "ResourceType",
]
