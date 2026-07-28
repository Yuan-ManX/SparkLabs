"""
SparkLabs Backend - Chronosynthesis Director Routes

REST endpoints for the Engine Chronosynthesis Director.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterRegionRequest(BaseModel):
    region_id: str
    label: str


class AddMemoryRequest(BaseModel):
    memory_id: str
    label: str
    valence: str
    significance: float = 0.5
    original_meaning: str = ""


class AddActionRequest(BaseModel):
    action_id: str
    label: str
    agency: float = 0.5
    target_memories: List[str] = Field(default_factory=list)
    target_futures: List[str] = Field(default_factory=list)


class AddFutureRequest(BaseModel):
    possibility_id: str
    label: str
    branch: str
    probability: float = 0.3
    pull_strength: float = 0.2


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/chronosynthesis/regions")
async def chronosynthesis_register_region(req: RegisterRegionRequest):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    result = director.register_region(req.region_id, req.label)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/chronosynthesis/regions/{region_id}")
async def chronosynthesis_remove_region(region_id: str):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    result = director.remove_region(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chronosynthesis/regions/{region_id}/memories")
async def chronosynthesis_add_memory(region_id: str, req: AddMemoryRequest):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector, MemoryValence,
    )
    director = EngineChronosynthesisDirector.get_instance()
    try:
        valence = MemoryValence(req.valence)
    except ValueError:
        return {"status": "error", "detail": f"Invalid valence: {req.valence}"}
    result = director.add_memory(
        region_id=region_id,
        memory_id=req.memory_id,
        label=req.label,
        valence=valence,
        significance=req.significance,
        original_meaning=req.original_meaning,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chronosynthesis/regions/{region_id}/actions")
async def chronosynthesis_add_action(region_id: str, req: AddActionRequest):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    result = director.add_action(
        region_id=region_id,
        action_id=req.action_id,
        label=req.label,
        agency=req.agency,
        target_memories=req.target_memories,
        target_futures=req.target_futures,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chronosynthesis/regions/{region_id}/futures")
async def chronosynthesis_add_future(region_id: str, req: AddFutureRequest):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector, FutureBranch,
    )
    director = EngineChronosynthesisDirector.get_instance()
    try:
        branch = FutureBranch(req.branch)
    except ValueError:
        return {"status": "error", "detail": f"Invalid branch: {req.branch}"}
    result = director.add_future(
        region_id=region_id,
        possibility_id=req.possibility_id,
        label=req.label,
        branch=branch,
        probability=req.probability,
        pull_strength=req.pull_strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chronosynthesis/cycle")
async def chronosynthesis_cycle():
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.cycle()}


@router.post("/chronosynthesis/simulate")
async def chronosynthesis_simulate(req: SimulateRequest):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.simulate(req.cycles)}


@router.get("/chronosynthesis/regions/{region_id}")
async def chronosynthesis_get_region(region_id: str):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    result = director.get_region_state(region_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chronosynthesis/regions/{region_id}/contradictions")
async def chronosynthesis_get_contradictions(region_id: str, limit: int = 20):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.get_contradictions(region_id, limit)}


@router.get("/chronosynthesis/events")
async def chronosynthesis_get_events(limit: int = 50):
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.get_events_log(limit)}


@router.get("/chronosynthesis/status")
async def chronosynthesis_status():
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.get_status()}


@router.post("/chronosynthesis/reset")
async def chronosynthesis_reset():
    from sparkai.engine.engine_chronosynthesis_director import (
        EngineChronosynthesisDirector,
    )
    director = EngineChronosynthesisDirector.get_instance()
    return {"status": "ok", "data": director.reset()}
