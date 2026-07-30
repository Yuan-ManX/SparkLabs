"""
SparkLabs Backend - Metacognitive Self-Model Routes

REST endpoints for the Agent Metacognitive Self-Model.
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
    introspection_bias: float = 0.5         # 0.0-1.0


class ObserveEventRequest(BaseModel):
    agent_id: str
    event_id: str
    description: str
    mode: str = "deliberate"                # deliberate/reactive/imitative/creative/habitual
    confidence: float = 0.5                 # 0.0-1.0
    context: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/metacognitive-self/agents")
async def metacog_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    result = model.register_agent(
        agent_id=req.agent_id,
        introspection_bias=req.introspection_bias,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/metacognitive-self/events")
async def metacog_observe_event(req: ObserveEventRequest):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel, CognitiveMode,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    try:
        mode = CognitiveMode(req.mode)
    except ValueError:
        return {"status": "error", "detail": f"Invalid mode: {req.mode}"}
    result = model.observe_event(
        agent_id=req.agent_id,
        event_id=req.event_id,
        description=req.description,
        mode=mode,
        confidence=req.confidence,
        context=req.context,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/metacognitive-self/agents/{agent_id}")
async def metacog_get_agent_state(agent_id: str):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    result = model.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/metacognitive-self/agents/{agent_id}/events")
async def metacog_get_events(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    result = model.get_events(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/metacognitive-self/agents/{agent_id}/events/{event_id}")
async def metacog_get_event(agent_id: str, event_id: str):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    result = model.get_event(agent_id, event_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/metacognitive-self/agents/{agent_id}/probes")
async def metacog_get_probes(agent_id: str, limit: int = 30):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    result = model.get_probes(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/metacognitive-self/events")
async def metacog_get_log_events(limit: int = 50):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    return {"status": "ok", "data": model.get_events_log(limit=limit)}


@router.get("/metacognitive-self/status")
async def metacog_get_status():
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    return {"status": "ok", "data": model.get_status()}


@router.post("/metacognitive-self/cycle")
async def metacog_cycle():
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    return {"status": "ok", "data": model.cycle()}


@router.post("/metacognitive-self/simulate")
async def metacog_simulate(req: SimulateRequest):
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    return {"status": "ok", "data": model.simulate(cycles=req.cycles)}


@router.post("/metacognitive-self/reset")
async def metacog_reset():
    from sparkai.agent.agent_metacognitive_self_model import (
        AgentMetacognitiveSelfModel,
    )
    model = AgentMetacognitiveSelfModel.get_instance()
    return {"status": "ok", "data": model.reset()}
