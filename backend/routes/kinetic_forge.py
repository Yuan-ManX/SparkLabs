"""
SparkLabs Backend - Kinetic Narrative Forge Routes

REST endpoints for the Engine Kinetic Narrative Forge.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class IgniteEventRequest(BaseModel):
    event_id: str
    label: str
    mass: str = "moderate"          # trivial/minor/moderate/major/critical/catastrophic
    velocity: float = 0.5
    thread_id: str = "default"
    description: str = ""


class PlaceObstacleRequest(BaseModel):
    obstacle_id: str
    label: str
    deflection_strength: float = 0.5
    redirect_direction: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/kinetic-forge/events")
async def forge_ignite_event(req: IgniteEventRequest):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge, NarrativeMass,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    try:
        mass = NarrativeMass(req.mass)
    except ValueError:
        return {"status": "error", "detail": f"Invalid mass: {req.mass}"}
    result = forge.ignite_event(
        event_id=req.event_id,
        label=req.label,
        mass=mass,
        velocity=req.velocity,
        thread_id=req.thread_id,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/kinetic-forge/obstacles")
async def forge_place_obstacle(req: PlaceObstacleRequest):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    result = forge.place_obstacle(
        obstacle_id=req.obstacle_id,
        label=req.label,
        deflection_strength=req.deflection_strength,
        redirect_direction=req.redirect_direction,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/kinetic-forge/threads")
async def forge_get_all_threads():
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.get_all_threads()}


@router.get("/kinetic-forge/threads/{thread_id}")
async def forge_get_thread(thread_id: str):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    result = forge.get_thread(thread_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/kinetic-forge/collisions")
async def forge_get_collisions(limit: int = 20):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.get_collisions(limit=limit)}


@router.get("/kinetic-forge/obstacles")
async def forge_get_obstacles():
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.get_obstacles()}


@router.get("/kinetic-forge/events")
async def forge_get_events(limit: int = 50):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit=limit)}


@router.get("/kinetic-forge/status")
async def forge_get_status():
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/kinetic-forge/cycle")
async def forge_cycle():
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.post("/kinetic-forge/simulate")
async def forge_simulate(req: SimulateRequest):
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.simulate(cycles=req.cycles)}


@router.post("/kinetic-forge/reset")
async def forge_reset():
    from sparkai.engine.engine_kinetic_narrative_forge import (
        EngineKineticNarrativeForge,
    )
    forge = EngineKineticNarrativeForge.get_instance()
    return {"status": "ok", "data": forge.reset()}
