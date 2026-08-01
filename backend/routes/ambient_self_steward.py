"""
SparkLabs Backend - Ambient Self Steward Routes

REST endpoints for the Agent Ambient Self Steward.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterDimensionRequest(BaseModel):
    dimension_id: str
    initial_value: float = 0.5            # 0.0-1.0
    note: str = ""


class SetDimensionRequest(BaseModel):
    value: float                           # 0.0-1.0
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/ambient-self-steward/dimensions")
async def steward_register_dimension(req: RegisterDimensionRequest):
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    result = steward.register_dimension(
        dimension_id=req.dimension_id,
        initial_value=req.initial_value,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/ambient-self-steward/dimensions/{dimension_id}/set")
async def steward_set_dimension(dimension_id: str, req: SetDimensionRequest):
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    result = steward.set_dimension(
        dimension_id=dimension_id,
        value=req.value,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/ambient-self-steward/cycle")
async def steward_cycle():
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.cycle()}


@router.get("/ambient-self-steward/status")
async def steward_get_status():
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.get_status()}


@router.get("/ambient-self-steward/dimensions")
async def steward_get_dimensions():
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.get_dimensions()}


@router.get("/ambient-self-steward/events")
async def steward_get_events(limit: int = 50):
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.get_events_log(limit=limit)}


@router.post("/ambient-self-steward/simulate")
async def steward_simulate(req: SimulateRequest):
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.simulate(cycles=req.cycles)}


@router.post("/ambient-self-steward/reset")
async def steward_reset():
    from sparkai.agent.agent_ambient_self_steward import AgentAmbientSelfSteward
    steward = AgentAmbientSelfSteward.get_instance()
    return {"status": "ok", "data": steward.reset()}
