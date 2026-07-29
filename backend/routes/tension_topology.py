"""
SparkLabs Backend - Tension Topology Cartographer Routes

REST endpoints for the Engine Tension Topology Cartographer.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class SurveyPointRequest(BaseModel):
    point_id: str
    label: str
    tension_type: str = "conflict"      # conflict/suspense/mystery/dread/hope/dilemma/betrayal/revelation/pursuit/stakes
    x: float = 0.5
    y: float = 0.5
    elevation: float = 0.5
    description: str = ""
    stakeholders: List[str] = []


class UpdateElevationRequest(BaseModel):
    new_elevation: float


class ConnectPointsRequest(BaseModel):
    point_b: str


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/tension-topology/points")
async def topology_survey_point(req: SurveyPointRequest):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer, TensionType,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    try:
        tension_type = TensionType(req.tension_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid tension_type: {req.tension_type}"}
    result = cartographer.survey_point(
        point_id=req.point_id,
        label=req.label,
        tension_type=tension_type,
        x=req.x, y=req.y,
        elevation=req.elevation,
        description=req.description,
        stakeholders=req.stakeholders,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.patch("/tension-topology/points/{point_id}/elevation")
async def topology_update_elevation(point_id: str, req: UpdateElevationRequest):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    result = cartographer.update_elevation(point_id, req.new_elevation)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/tension-topology/points/{point_a}/connect")
async def topology_connect_points(point_a: str, req: ConnectPointsRequest):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    result = cartographer.connect_points(point_a, req.point_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/tension-topology/points")
async def topology_get_all_points():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_all_points()}


@router.get("/tension-topology/points/{point_id}")
async def topology_get_point(point_id: str):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    result = cartographer.get_point(point_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/tension-topology/contours")
async def topology_get_contours():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_contours()}


@router.get("/tension-topology/peaks")
async def topology_get_peaks():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_peaks()}


@router.get("/tension-topology/events")
async def topology_get_events(limit: int = 50):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_events_log(limit=limit)}


@router.get("/tension-topology/status")
async def topology_get_status():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_status()}


@router.post("/tension-topology/cycle")
async def topology_cycle():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.cycle()}


@router.post("/tension-topology/simulate")
async def topology_simulate(req: SimulateRequest):
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.simulate(cycles=req.cycles)}


@router.post("/tension-topology/reset")
async def topology_reset():
    from sparkai.engine.engine_tension_topology_cartographer import (
        EngineTensionTopologyCartographer,
    )
    cartographer = EngineTensionTopologyCartographer.get_instance()
    return {"status": "ok", "data": cartographer.reset()}
