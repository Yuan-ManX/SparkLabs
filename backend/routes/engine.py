"""
SparkLabs Backend - Engine Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

from sparkai.engine.engine import SparkEngine

router = APIRouter()


class SceneCreateRequest(BaseModel):
    name: str = "Untitled Scene"


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
