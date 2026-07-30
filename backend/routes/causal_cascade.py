"""
SparkLabs Backend - Causal Cascade Composer Routes

REST endpoints for the Engine Causal Cascade Composer.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class SeedEventRequest(BaseModel):
    event_id: str
    label: str
    event_type: str = "action"      # action/decision/environmental/social/narrative/combat/economic/political/magical/technological
    source_entity: str = ""
    energy: float = 0.7
    x: float = 0.5
    y: float = 0.5
    description: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/causal-cascade/events")
async def cascade_seed_event(req: SeedEventRequest):
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer, CausalEventType,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    try:
        event_type = CausalEventType(req.event_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid event_type: {req.event_type}"}
    result = composer.seed_event(
        event_id=req.event_id,
        label=req.label,
        event_type=event_type,
        source_entity=req.source_entity,
        energy=req.energy,
        x=req.x, y=req.y,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-cascade/ripples")
async def cascade_get_all_ripples():
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.get_all_ripples()}


@router.get("/causal-cascade/ripples/{ripple_id}")
async def cascade_get_ripple(ripple_id: str):
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    result = composer.get_ripple(ripple_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-cascade/convergences")
async def cascade_get_convergences(limit: int = 20):
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.get_convergences(limit=limit)}


@router.get("/causal-cascade/consequences")
async def cascade_get_settled_consequences():
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.get_settled_consequences()}


@router.get("/causal-cascade/events")
async def cascade_get_events(limit: int = 50):
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit=limit)}


@router.get("/causal-cascade/status")
async def cascade_get_status():
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/causal-cascade/cycle")
async def cascade_cycle():
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/causal-cascade/simulate")
async def cascade_simulate(req: SimulateRequest):
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(cycles=req.cycles)}


@router.post("/causal-cascade/reset")
async def cascade_reset():
    from sparkai.engine.engine_causal_cascade_composer import (
        EngineCausalCascadeComposer,
    )
    composer = EngineCausalCascadeComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
