"""
SparkLabs Backend - Dynamical Systems Attractor Routes

REST endpoints for the Engine Dynamical Systems Attractor.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterLandscapeRequest(BaseModel):
    landscape_id: str
    dimensions: List[str]
    attractors: Optional[List[Dict[str, Any]]] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/dynamical-systems-attractor/register")
async def dsa_register_landscape(req: RegisterLandscapeRequest):
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    result = engine.register_landscape(
        landscape_id=req.landscape_id,
        dimensions=req.dimensions,
        attractors=req.attractors,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/dynamical-systems-attractor/status")
async def dsa_get_status():
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.get("/dynamical-systems-attractor/landscapes")
async def dsa_get_landscapes():
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.get_landscapes()}


@router.get("/dynamical-systems-attractor/landscapes/{landscape_id}")
async def dsa_get_landscape(landscape_id: str):
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    result = engine.get_landscape(landscape_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/dynamical-systems-attractor/cycle")
async def dsa_cycle():
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.cycle()}


@router.get("/dynamical-systems-attractor/events")
async def dsa_get_events(limit: int = 50):
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.get_events_log(limit=limit)}


@router.post("/dynamical-systems-attractor/simulate")
async def dsa_simulate(req: SimulateRequest):
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.simulate(cycles=req.cycles)}


@router.post("/dynamical-systems-attractor/reset")
async def dsa_reset():
    from sparkai.engine.engine_dynamical_systems_attractor import (
        DynamicalSystemsAttractor,
    )
    engine = DynamicalSystemsAttractor.get_instance()
    return {"status": "ok", "data": engine.reset()}
