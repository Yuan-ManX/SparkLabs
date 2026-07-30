"""
SparkLabs Backend - Intentional Drift Cartographer Routes

REST endpoints for the Agent Intentional Drift Cartographer.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterIntentionRequest(BaseModel):
    intention_id: str
    goal_label: str
    initial_position: float = 0.5            # 0.0-1.0


class LogTrackRequest(BaseModel):
    intention_id: str
    track_id: str
    position: float                            # 0.0-1.0
    fidelity: float = 0.7                      # 0.0-1.0


class SetStanceRequest(BaseModel):
    stance: str = "vigilant"                   # permissive/vigilant/strict


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/intentional-drift/intentions")
async def drift_register_intention(req: RegisterIntentionRequest):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.register_intention(
        intention_id=req.intention_id,
        goal_label=req.goal_label,
        initial_position=req.initial_position,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/intentional-drift/tracks")
async def drift_log_track(req: LogTrackRequest):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.log_track(
        intention_id=req.intention_id,
        track_id=req.track_id,
        position=req.position,
        fidelity=req.fidelity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/intentional-drift/stance")
async def drift_set_stance(req: SetStanceRequest):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer, CartographerStance,
    )
    try:
        stance = CartographerStance(req.stance)
    except ValueError:
        return {"status": "error", "detail": f"Invalid stance: {req.stance}"}
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.set_stance(stance)
    return {"status": "ok", "data": result}


@router.get("/intentional-drift/intentions/{intention_id}")
async def drift_get_intention_state(intention_id: str):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.get_intention_state(intention_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/intentional-drift/intentions/{intention_id}/tracks")
async def drift_get_tracks(intention_id: str, limit: int = 20):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.get_tracks(intention_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/intentional-drift/intentions/{intention_id}/model")
async def drift_get_model(intention_id: str):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    result = cartographer.get_model(intention_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/intentional-drift/events")
async def drift_get_events(limit: int = 50):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_events_log(limit=limit)}


@router.get("/intentional-drift/status")
async def drift_get_status():
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    return {"status": "ok", "data": cartographer.get_status()}


@router.post("/intentional-drift/cycle")
async def drift_cycle():
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    return {"status": "ok", "data": cartographer.cycle()}


@router.post("/intentional-drift/simulate")
async def drift_simulate(req: SimulateRequest):
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    return {"status": "ok", "data": cartographer.simulate(cycles=req.cycles)}


@router.post("/intentional-drift/reset")
async def drift_reset():
    from sparkai.agent.agent_intentional_drift_cartographer import (
        AgentIntentionalDriftCartographer,
    )
    cartographer = AgentIntentionalDriftCartographer.get_instance()
    return {"status": "ok", "data": cartographer.reset()}
