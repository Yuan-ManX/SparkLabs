"""
SparkLabs Backend - Temporal Self Projection Routes

REST endpoints for the Agent Temporal Self Projection module.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    initial_traits: Dict[str, float] = {}


class RecordObservationRequest(BaseModel):
    agent_id: str
    observed_traits: Dict[str, float]


class ProjectSelfRequest(BaseModel):
    agent_id: str
    projection_id: str
    direction: str = "future"               # past/future
    horizon_cycles: int = 3
    stance: str = "pragmatic"               # aspirational/feared/nostalgic/pragmatic


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/temporal-self-projection/agents")
async def temporal_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    result = projector.register_agent(
        agent_id=req.agent_id,
        initial_traits=req.initial_traits,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/temporal-self-projection/observations")
async def temporal_record_observation(req: RecordObservationRequest):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    result = projector.record_observation(
        agent_id=req.agent_id,
        observed_traits=req.observed_traits,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/temporal-self-projection/projections")
async def temporal_project_self(req: ProjectSelfRequest):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection, ProjectionDirection, ProjectionStance,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    try:
        direction = ProjectionDirection(req.direction)
    except ValueError:
        return {"status": "error", "detail": f"Invalid direction: {req.direction}"}
    try:
        stance = ProjectionStance(req.stance)
    except ValueError:
        return {"status": "error", "detail": f"Invalid stance: {req.stance}"}
    result = projector.project_self(
        agent_id=req.agent_id,
        projection_id=req.projection_id,
        direction=direction,
        horizon_cycles=req.horizon_cycles,
        stance=stance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-self-projection/agents/{agent_id}")
async def temporal_get_agent_state(agent_id: str):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    result = projector.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-self-projection/agents/{agent_id}/projections")
async def temporal_get_projections(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    result = projector.get_projections(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-self-projection/agents/{agent_id}/encounters")
async def temporal_get_encounters(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    result = projector.get_encounters(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-self-projection/events")
async def temporal_get_events(limit: int = 50):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    return {"status": "ok", "data": projector.get_events_log(limit=limit)}


@router.get("/temporal-self-projection/status")
async def temporal_get_status():
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    return {"status": "ok", "data": projector.get_status()}


@router.post("/temporal-self-projection/cycle")
async def temporal_cycle():
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    return {"status": "ok", "data": projector.cycle()}


@router.post("/temporal-self-projection/simulate")
async def temporal_simulate(req: SimulateRequest):
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    return {"status": "ok", "data": projector.simulate(cycles=req.cycles)}


@router.post("/temporal-self-projection/reset")
async def temporal_reset():
    from sparkai.agent.agent_temporal_self_projection import (
        AgentTemporalSelfProjection,
    )
    projector = AgentTemporalSelfProjection.get_instance()
    return {"status": "ok", "data": projector.reset()}
