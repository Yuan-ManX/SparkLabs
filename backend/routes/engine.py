"""
SparkLabs Backend - Engine Routes

API endpoints for engine control, ECS world management,
scene management, and component/system registry.
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

from sparkai.engine.engine import SparkEngine
from sparkai.engine.ecs.component import ComponentRegistry
from sparkai.engine.ecs.system import SystemRegistry
from sparkai.engine.ecs.components import (
    Transform, Renderable, SpriteRenderer, TextRenderer,
    PhysicsBody, Collider, Camera, AudioSource, Animator,
    InputReceiver, AIBrain, Script, Tween,
)
from sparkai.engine.ecs.systems import (
    TransformSystem, PhysicsSystem, RenderSystem,
    AnimationSystem, AudioSystem, InputSystem, AISystem,
    TweenSystem, ScriptSystem, CollisionSystem,
)

router = APIRouter()


class SceneCreateRequest(BaseModel):
    name: str = "Untitled Scene"


class WorldCreateRequest(BaseModel):
    name: str = "World"


class EntityCreateRequest(BaseModel):
    name: str = "Entity"
    components: Optional[List[Dict[str, Any]]] = None
    tags: Optional[List[str]] = None


class ComponentAddRequest(BaseModel):
    component_type: str
    data: Optional[Dict[str, Any]] = None


class SystemAddRequest(BaseModel):
    system_type: str


# Engine control

@router.get("/status")
async def get_engine_status():
    engine = SparkEngine.get_instance()
    return engine.get_status()


@router.post("/start")
async def start_engine():
    engine = SparkEngine.get_instance()
    engine.start()
    return {"status": "started"}


@router.post("/stop")
async def stop_engine():
    engine = SparkEngine.get_instance()
    engine.stop()
    return {"status": "stopped"}


# ECS Registry

@router.get("/ecs/component-types")
async def list_component_types():
    return {"component_types": ComponentRegistry.list_types()}


@router.get("/ecs/component-types/{type_name}/schema")
async def get_component_schema(type_name: str):
    schema = ComponentRegistry.get_schema(type_name)
    if schema:
        return {"schema": schema}
    return {"error": "Component type not found"}


@router.get("/ecs/system-types")
async def list_system_types():
    return {"system_types": SystemRegistry.list_types()}


# World management

@router.post("/worlds/create")
async def create_world(request: WorldCreateRequest):
    engine = SparkEngine.get_instance()
    world = engine.create_world(name=request.name)
    return world.get_status()


@router.get("/worlds")
async def list_worlds():
    engine = SparkEngine.get_instance()
    return {"worlds": engine.list_worlds()}


@router.get("/worlds/{world_id}")
async def get_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        return world.get_status()
    return {"error": "World not found"}


@router.get("/worlds/{world_id}/status")
async def get_world_status(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        return world.get_status()
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/start")
async def start_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.start()
        return {"status": "started"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/stop")
async def stop_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.stop()
        return {"status": "stopped"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/pause")
async def pause_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.pause()
        return {"status": "paused"}
    return {"error": "World not found"}


@router.post("/worlds/{world_id}/resume")
async def resume_world(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if world:
        world.resume()
        return {"status": "resumed"}
    return {"error": "World not found"}


@router.delete("/worlds/{world_id}")
async def delete_world(world_id: str):
    engine = SparkEngine.get_instance()
    success = engine.delete_world(world_id)
    return {"success": success}


# Entity management within a world

@router.post("/worlds/{world_id}/entities/create")
async def create_world_entity(world_id: str, request: EntityCreateRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.create_entity(name=request.name)
    if request.tags:
        for tag in request.tags:
            entity.add_tag(tag)
    if request.components:
        for comp_data in request.components:
            comp_type = comp_data.get("type", "")
            comp_params = comp_data.get("data", {})
            component = ComponentRegistry.create(comp_type, **comp_params)
            if component:
                entity.add_component(component)
    return entity.to_dict()


@router.get("/worlds/{world_id}/entities")
async def list_world_entities(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    return world.entities.to_dict()


@router.get("/worlds/{world_id}/entities/{entity_id}")
async def get_world_entity(world_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if entity:
        return entity.to_dict()
    return {"error": "Entity not found"}


@router.delete("/worlds/{world_id}/entities/{entity_id}")
async def delete_world_entity(world_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.destroy_entity(entity_id)
    if entity:
        return {"success": True}
    return {"error": "Entity not found"}


@router.post("/worlds/{world_id}/entities/{entity_id}/components")
async def add_entity_component(world_id: str, entity_id: str, request: ComponentAddRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    component = ComponentRegistry.create(request.component_type, **(request.data or {}))
    if component:
        entity.add_component(component)
        world.entities.on_component_added(entity_id, request.component_type)
        return component.to_dict()
    return {"error": "Component type not found"}


@router.delete("/worlds/{world_id}/entities/{entity_id}/components/{component_type}")
async def remove_entity_component(world_id: str, entity_id: str, component_type: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    entity = world.entities.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    removed = entity.remove_component(component_type)
    if removed:
        world.entities.on_component_removed(entity_id, component_type)
        return {"success": True}
    return {"error": "Component not found"}


# System management within a world

@router.post("/worlds/{world_id}/systems/add")
async def add_world_system(world_id: str, request: SystemAddRequest):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    system_instance = SystemRegistry.create(request.system_type)
    if system_instance:
        world.add_system(system_instance)
        return system_instance.to_dict()
    return {"error": "System type not found"}


@router.get("/worlds/{world_id}/systems")
async def list_world_systems(world_id: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    return {"systems": world.systems.list_systems()}


@router.delete("/worlds/{world_id}/systems/{system_type}")
async def remove_world_system(world_id: str, system_type: str):
    engine = SparkEngine.get_instance()
    world = engine.get_world(world_id)
    if not world:
        return {"error": "World not found"}
    removed = world.remove_system(system_type)
    if removed:
        return {"success": True}
    return {"error": "System not found"}


# Scene management (legacy)

@router.post("/scenes/create")
async def create_scene(request: SceneCreateRequest):
    engine = SparkEngine.get_instance()
    scene = engine.create_scene(name=request.name)
    return scene.to_dict()


@router.get("/scenes")
async def list_scenes():
    engine = SparkEngine.get_instance()
    return {"scenes": engine.list_scenes()}


@router.get("/scenes/{scene_id}")
async def get_scene(scene_id: str):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if scene:
        return scene.to_dict()
    return {"error": "Scene not found"}


@router.delete("/scenes/{scene_id}")
async def delete_scene(scene_id: str):
    engine = SparkEngine.get_instance()
    success = engine.delete_scene(scene_id)
    return {"success": success}
