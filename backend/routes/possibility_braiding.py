"""
SparkLabs Backend - Possibility Braiding Loom Routes

REST endpoints for the Agent Possibility Braiding Loom.
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
    braiding_tolerance: float = 0.5        # 0.0-1.0


class IntroduceThreadRequest(BaseModel):
    agent_id: str
    thread_id: str
    label: str
    valence: str = "expected"              # hoped/feared/expected/wildcard
    plausibility: float = 0.5              # 0.0-1.0
    grounding: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/possibility-braiding/agents")
async def braiding_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    result = loom.register_agent(
        agent_id=req.agent_id,
        braiding_tolerance=req.braiding_tolerance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/possibility-braiding/threads")
async def braiding_introduce_thread(req: IntroduceThreadRequest):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom, ThreadValence,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    try:
        valence = ThreadValence(req.valence)
    except ValueError:
        return {"status": "error", "detail": f"Invalid valence: {req.valence}"}
    result = loom.introduce_thread(
        agent_id=req.agent_id,
        thread_id=req.thread_id,
        label=req.label,
        valence=valence,
        plausibility=req.plausibility,
        grounding=req.grounding,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/possibility-braiding/agents/{agent_id}")
async def braiding_get_agent_state(agent_id: str):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    result = loom.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/possibility-braiding/agents/{agent_id}/threads")
async def braiding_get_threads(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    result = loom.get_threads(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/possibility-braiding/agents/{agent_id}/threads/{thread_id}")
async def braiding_get_thread(agent_id: str, thread_id: str):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    result = loom.get_thread(agent_id, thread_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/possibility-braiding/agents/{agent_id}/crossings")
async def braiding_get_crossings(agent_id: str, limit: int = 30):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    result = loom.get_crossings(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/possibility-braiding/events")
async def braiding_get_events(limit: int = 50):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    return {"status": "ok", "data": loom.get_events_log(limit=limit)}


@router.get("/possibility-braiding/status")
async def braiding_get_status():
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    return {"status": "ok", "data": loom.get_status()}


@router.post("/possibility-braiding/cycle")
async def braiding_cycle():
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    return {"status": "ok", "data": loom.cycle()}


@router.post("/possibility-braiding/simulate")
async def braiding_simulate(req: SimulateRequest):
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    return {"status": "ok", "data": loom.simulate(cycles=req.cycles)}


@router.post("/possibility-braiding/reset")
async def braiding_reset():
    from sparkai.agent.agent_possibility_braiding_loom import (
        AgentPossibilityBraidingLoom,
    )
    loom = AgentPossibilityBraidingLoom.get_instance()
    return {"status": "ok", "data": loom.reset()}
