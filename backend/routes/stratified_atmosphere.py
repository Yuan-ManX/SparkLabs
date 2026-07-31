"""
SparkLabs Backend - Stratified Atmosphere Weaver Routes

REST endpoints for the Engine Stratified Atmosphere Weaver.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterWorldRequest(BaseModel):
    world_id: str


class AddLayerRequest(BaseModel):
    layer_id: str
    kind: str = "surface"                  # surface/wind/light/sound/social
    intensity: float = 0.5                 # 0.0-1.0
    hue: float = 0.5                       # 0.0-1.0
    texture_note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/stratified-atmosphere/worlds")
async def atmosphere_register_world(req: RegisterWorldRequest):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    result = weaver.register_world(world_id=req.world_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/stratified-atmosphere/worlds/{world_id}/layers")
async def atmosphere_add_layer(world_id: str, req: AddLayerRequest):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver, AtmosphereLayerKind,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    try:
        kind = AtmosphereLayerKind(req.kind)
    except ValueError:
        return {"status": "error", "detail": f"Invalid kind: {req.kind}"}
    result = weaver.add_layer(
        world_id=world_id,
        layer_id=req.layer_id,
        kind=kind,
        intensity=req.intensity,
        hue=req.hue,
        texture_note=req.texture_note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/stratified-atmosphere/worlds/{world_id}")
async def atmosphere_get_world_state(world_id: str):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    result = weaver.get_world_state(world_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/stratified-atmosphere/worlds/{world_id}/layers")
async def atmosphere_get_layers(world_id: str, limit: int = 20):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    result = weaver.get_layers(world_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/stratified-atmosphere/worlds/{world_id}/edges")
async def atmosphere_get_edges(world_id: str, limit: int = 30):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    result = weaver.get_edges(world_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/stratified-atmosphere/worlds/{world_id}/mood")
async def atmosphere_get_mood(world_id: str):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    result = weaver.get_mood(world_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/stratified-atmosphere/events")
async def atmosphere_get_events(limit: int = 50):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit=limit)}


@router.get("/stratified-atmosphere/status")
async def atmosphere_get_status():
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/stratified-atmosphere/cycle")
async def atmosphere_cycle():
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.post("/stratified-atmosphere/simulate")
async def atmosphere_simulate(req: SimulateRequest):
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(cycles=req.cycles)}


@router.post("/stratified-atmosphere/reset")
async def atmosphere_reset():
    from sparkai.engine.engine_stratified_atmosphere_weaver import (
        EngineStratifiedAtmosphereWeaver,
    )
    weaver = EngineStratifiedAtmosphereWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
