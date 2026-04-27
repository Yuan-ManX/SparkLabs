"""
SparkLabs Backend - Scene Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import List, Optional

from sparkai.engine.engine import SparkEngine

router = APIRouter()


class EntityCreateRequest(BaseModel):
    scene_id: str
    name: str = "Entity"
    position: List[float] = [0, 0, 0]
    tags: List[str] = []


class EntityUpdateRequest(BaseModel):
    name: Optional[str] = None
    position: Optional[List[float]] = None
    rotation: Optional[List[float]] = None
    scale: Optional[List[float]] = None
    tags: Optional[List[str]] = None
    properties: Optional[dict] = None


@router.post("/entity/create")
async def create_entity(request: EntityCreateRequest):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(request.scene_id)
    if not scene:
        return {"error": "Scene not found"}
    entity = scene.create_entity(name=request.name)
    entity.set_position(*request.position)
    for tag in request.tags:
        entity.add_tag(tag)
    return entity.to_dict()


@router.get("/entity/{scene_id}/{entity_id}")
async def get_entity(scene_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if not scene:
        return {"error": "Scene not found"}
    entity = scene.get_entity(entity_id)
    if entity:
        return entity.to_dict()
    return {"error": "Entity not found"}


@router.put("/entity/{scene_id}/{entity_id}")
async def update_entity(scene_id: str, entity_id: str, request: EntityUpdateRequest):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if not scene:
        return {"error": "Scene not found"}
    entity = scene.get_entity(entity_id)
    if not entity:
        return {"error": "Entity not found"}
    if request.name:
        entity.name = request.name
    if request.position:
        entity.set_position(*request.position)
    if request.rotation:
        entity.set_rotation(*request.rotation)
    if request.scale:
        entity.set_scale(*request.scale)
    if request.tags:
        entity.tags = request.tags
    if request.properties:
        entity.properties.update(request.properties)
    return entity.to_dict()


@router.delete("/entity/{scene_id}/{entity_id}")
async def delete_entity(scene_id: str, entity_id: str):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if not scene:
        return {"error": "Scene not found"}
    success = scene.remove_entity(entity_id)
    return {"success": success}


@router.get("/entities/{scene_id}")
async def list_entities(scene_id: str):
    engine = SparkEngine.get_instance()
    scene = engine.get_scene(scene_id)
    if not scene:
        return {"error": "Scene not found"}
    return {"entities": [e.to_dict() for e in scene.entities.values()]}
