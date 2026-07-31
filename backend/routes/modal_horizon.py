"""
SparkLabs Backend - Modal Horizon Expander Routes

REST endpoints for the Engine Modal Horizon Expander.
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


class AddConstraintRequest(BaseModel):
    constraint_id: str
    label: str
    weight: float = 0.5                  # 0.0-1.0


class IntroduceTensionRequest(BaseModel):
    world_id: str
    tension_id: str
    origin: str = "tension"              # tension/divergence/opportunity/residual
    description: str = ""
    magnitude: float = 0.5               # 0.0-1.0


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/modal-horizon/worlds")
async def horizon_register_world(req: RegisterWorldRequest):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.register_world(world_id=req.world_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/modal-horizon/worlds/{world_id}/constraints")
async def horizon_add_constraint(world_id: str, req: AddConstraintRequest):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.add_constraint(
        world_id=world_id,
        constraint_id=req.constraint_id,
        label=req.label,
        weight=req.weight,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/modal-horizon/worlds/{world_id}/tensions")
async def horizon_introduce_tension(world_id: str, req: IntroduceTensionRequest):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander, CandidateOrigin,
    )
    expander = EngineModalHorizonExpander.get_instance()
    try:
        origin = CandidateOrigin(req.origin)
    except ValueError:
        return {"status": "error", "detail": f"Invalid origin: {req.origin}"}
    result = expander.introduce_tension(
        world_id=world_id,
        tension_id=req.tension_id,
        origin=origin,
        description=req.description,
        magnitude=req.magnitude,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/modal-horizon/worlds/{world_id}")
async def horizon_get_world_state(world_id: str):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.get_world_state(world_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/modal-horizon/worlds/{world_id}/candidates")
async def horizon_get_candidates(world_id: str, limit: int = 20):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.get_candidates(world_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/modal-horizon/worlds/{world_id}/horizons")
async def horizon_get_open_horizons(world_id: str, limit: int = 12):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.get_open_horizons(world_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/modal-horizon/worlds/{world_id}/constraints")
async def horizon_get_constraints(world_id: str, limit: int = 20):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    result = expander.get_constraints(world_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/modal-horizon/events")
async def horizon_get_events(limit: int = 50):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    return {"status": "ok", "data": expander.get_events_log(limit=limit)}


@router.get("/modal-horizon/status")
async def horizon_get_status():
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    return {"status": "ok", "data": expander.get_status()}


@router.post("/modal-horizon/cycle")
async def horizon_cycle():
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    return {"status": "ok", "data": expander.cycle()}


@router.post("/modal-horizon/simulate")
async def horizon_simulate(req: SimulateRequest):
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    return {"status": "ok", "data": expander.simulate(cycles=req.cycles)}


@router.post("/modal-horizon/reset")
async def horizon_reset():
    from sparkai.engine.engine_modal_horizon_expander import (
        EngineModalHorizonExpander,
    )
    expander = EngineModalHorizonExpander.get_instance()
    return {"status": "ok", "data": expander.reset()}
