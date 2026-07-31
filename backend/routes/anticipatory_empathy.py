"""
SparkLabs Backend - Anticipatory Empathy Weaver Routes

REST endpoints for the Agent Anticipatory Empathy Weaver.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterTargetRequest(BaseModel):
    target_id: str


class RecordReadingRequest(BaseModel):
    target_id: str
    reading_id: str
    valence: float = 0.5                   # 0.0-1.0, unpleasant to pleasant
    arousal: float = 0.5                   # 0.0-1.0, calm to activated
    trajectory: str = "plateau"            # rising/falling/plateau/oscillating/spiking


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/anticipatory-empathy/targets")
async def empathy_register_target(req: RegisterTargetRequest):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    result = weaver.register_target(target_id=req.target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/anticipatory-empathy/readings")
async def empathy_record_reading(req: RecordReadingRequest):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver, EmotionalTrajectory,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    try:
        trajectory = EmotionalTrajectory(req.trajectory)
    except ValueError:
        return {"status": "error", "detail": f"Invalid trajectory: {req.trajectory}"}
    result = weaver.record_reading(
        target_id=req.target_id,
        reading_id=req.reading_id,
        valence=req.valence,
        arousal=req.arousal,
        trajectory=trajectory,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/anticipatory-empathy/targets/{target_id}")
async def empathy_get_target_state(target_id: str):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    result = weaver.get_target_state(target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/anticipatory-empathy/targets/{target_id}/threads")
async def empathy_get_threads(target_id: str, limit: int = 20):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    result = weaver.get_threads(target_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/anticipatory-empathy/events")
async def empathy_get_events(limit: int = 50):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit=limit)}


@router.get("/anticipatory-empathy/status")
async def empathy_get_status():
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/anticipatory-empathy/cycle")
async def empathy_cycle():
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.post("/anticipatory-empathy/simulate")
async def empathy_simulate(req: SimulateRequest):
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(cycles=req.cycles)}


@router.post("/anticipatory-empathy/reset")
async def empathy_reset():
    from sparkai.agent.agent_anticipatory_empathy_weaver import (
        AgentAnticipatoryEmpathyWeaver,
    )
    weaver = AgentAnticipatoryEmpathyWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
