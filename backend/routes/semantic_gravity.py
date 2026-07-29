"""
SparkLabs Backend - Semantic Gravity Well Routes

REST endpoints for the Engine Semantic Gravity Well.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class AddMassRequest(BaseModel):
    mass_id: str
    label: str
    mass_type: str = "concept"          # location/character/object/event/concept/narrative
    polarity: str = "order"             # order/chaos/life/death/light/shadow/mind/spirit
    weight: float = 0.5
    x: float = 0.5
    y: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/semantic-gravity/masses")
async def gravity_add_mass(req: AddMassRequest):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell, MassType, SemanticPolarity,
    )
    well = EngineSemanticGravityWell.get_instance()
    try:
        mtype = MassType(req.mass_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid mass_type: {req.mass_type}"}
    try:
        polarity = SemanticPolarity(req.polarity)
    except ValueError:
        return {"status": "error", "detail": f"Invalid polarity: {req.polarity}"}
    result = well.add_mass(
        mass_id=req.mass_id,
        label=req.label,
        mass_type=mtype,
        polarity=polarity,
        weight=req.weight,
        x=req.x,
        y=req.y,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/semantic-gravity/masses/{mass_id}")
async def gravity_remove_mass(mass_id: str):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    result = well.remove_mass(mass_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/semantic-gravity/masses")
async def gravity_get_all_masses():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_all_masses()}


@router.get("/semantic-gravity/masses/{mass_id}")
async def gravity_get_mass(mass_id: str):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    result = well.get_mass(mass_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/semantic-gravity/wells")
async def gravity_get_wells():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_wells()}


@router.get("/semantic-gravity/singularities")
async def gravity_get_singularities():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_singularities()}


@router.get("/semantic-gravity/tidal-stretches")
async def gravity_get_tidal_stretches(limit: int = 20):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_tidal_stretches(limit)}


@router.post("/semantic-gravity/cycle")
async def gravity_cycle():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.cycle()}


@router.post("/semantic-gravity/simulate")
async def gravity_simulate(req: SimulateRequest):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.simulate(req.cycles)}


@router.get("/semantic-gravity/events")
async def gravity_get_events(limit: int = 50):
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_events_log(limit)}


@router.get("/semantic-gravity/status")
async def gravity_status():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.get_status()}


@router.post("/semantic-gravity/reset")
async def gravity_reset():
    from sparkai.engine.engine_semantic_gravity_well import (
        EngineSemanticGravityWell,
    )
    well = EngineSemanticGravityWell.get_instance()
    return {"status": "ok", "data": well.reset()}
