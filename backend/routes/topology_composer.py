"""
SparkLabs Backend - Emergent Topology Composer Routes

REST endpoints for the Engine Emergent Topology Composer.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class SeedPlaceRequest(BaseModel):
    place_id: str
    label: str
    place_type: str
    x: float
    y: float
    attraction: float = 0.5
    repulsion: float = 0.0
    narrative_weight: float = 0.0


class ConnectPlacesRequest(BaseModel):
    place_a: str
    place_b: str


class SpawnFlowRequest(BaseModel):
    flow_id: str
    flow_type: str
    source_place: str
    target_place: str
    intensity: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/topology-composer/places")
async def topology_composer_seed_place(req: SeedPlaceRequest):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer, PlaceType,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    try:
        ptype = PlaceType(req.place_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid place_type: {req.place_type}"}
    result = composer.seed_place(
        place_id=req.place_id,
        label=req.label,
        place_type=ptype,
        x=req.x,
        y=req.y,
        attraction=req.attraction,
        repulsion=req.repulsion,
        narrative_weight=req.narrative_weight,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/topology-composer/places/{place_id}")
async def topology_composer_remove_place(place_id: str):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    result = composer.remove_place(place_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/topology-composer/connect")
async def topology_composer_connect_places(req: ConnectPlacesRequest):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    result = composer.connect_places(req.place_a, req.place_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/topology-composer/flows")
async def topology_composer_spawn_flow(req: SpawnFlowRequest):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer, FlowType,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    try:
        ftype = FlowType(req.flow_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid flow_type: {req.flow_type}"}
    result = composer.spawn_flow(
        flow_id=req.flow_id,
        flow_type=ftype,
        source_place=req.source_place,
        target_place=req.target_place,
        intensity=req.intensity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/topology-composer/cycle")
async def topology_composer_cycle():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/topology-composer/simulate")
async def topology_composer_simulate(req: SimulateRequest):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(req.cycles)}


@router.get("/topology-composer/places")
async def topology_composer_get_places():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.get_all_places()}


@router.get("/topology-composer/places/{place_id}")
async def topology_composer_get_place(place_id: str):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    result = composer.get_place(place_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/topology-composer/regions")
async def topology_composer_get_regions():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.get_regions()}


@router.get("/topology-composer/flows")
async def topology_composer_get_flows():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.get_active_flows()}


@router.get("/topology-composer/events")
async def topology_composer_get_events(limit: int = 50):
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit)}


@router.get("/topology-composer/status")
async def topology_composer_status():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/topology-composer/reset")
async def topology_composer_reset():
    from sparkai.engine.engine_emergent_topology_composer import (
        EngineEmergentTopologyComposer,
    )
    composer = EngineEmergentTopologyComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
