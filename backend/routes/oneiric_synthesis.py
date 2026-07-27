"""
SparkLabs Backend - Oneiric Synthesis Routes

REST API endpoints for the AgentOneiricSynthesisEngine, which performs
offline dream synthesis where agents rehearse futures, recombine memories,
and consolidate insights.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class FeedMemoryRequest(BaseModel):
    memory_id: str
    label: str
    valence: float = 0.0
    arousal: float = 0.3
    salience: float = 0.5
    tags: Optional[List[str]] = None


class RegisterAgentRequest(BaseModel):
    agent_id: str


class SimulateRequest(BaseModel):
    cycles: int = 10


class SetMutationBiasRequest(BaseModel):
    bias: Dict[str, float]


class ApplyInsightRequest(BaseModel):
    insight_id: str


# =============================================================================
# Routes
# =============================================================================

@router.get("/oneiric/status")
async def oneiric_status():
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.post("/oneiric/agents")
async def oneiric_register(req: RegisterAgentRequest):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.register_agent(req.agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/oneiric/agents/{agent_id}")
async def oneiric_remove(agent_id: str):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/oneiric/agents")
async def oneiric_list_agents(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.list_agents(limit)}


@router.get("/oneiric/agents/{agent_id}")
async def oneiric_get_agent(agent_id: str):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    data = engine.get_agent(agent_id)
    if data is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": data}


@router.post("/oneiric/agents/{agent_id}/memories")
async def oneiric_feed_memory(agent_id: str, req: FeedMemoryRequest):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.feed_memory(
        agent_id=agent_id,
        memory_id=req.memory_id,
        label=req.label,
        valence=req.valence,
        arousal=req.arousal,
        salience=req.salience,
        tags=req.tags,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/oneiric/agents/{agent_id}/memories")
async def oneiric_list_memories(agent_id: str, limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.list_memories(agent_id, limit)}


@router.post("/oneiric/agents/{agent_id}/descend")
async def oneiric_descend(agent_id: str):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.descend(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/oneiric/cycle")
async def oneiric_cycle():
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.cycle()}


@router.post("/oneiric/simulate")
async def oneiric_simulate(req: SimulateRequest):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.simulate(req.cycles)}


@router.get("/oneiric/agents/{agent_id}/branches")
async def oneiric_get_branches(agent_id: str, limit: int = Query(30, ge=1, le=200)):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.get_branches(agent_id, limit)}


@router.get("/oneiric/agents/{agent_id}/insights")
async def oneiric_get_insights(agent_id: str, limit: int = Query(30, ge=1, le=200)):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.get_insights(agent_id, limit)}


@router.post("/oneiric/agents/{agent_id}/insights/apply")
async def oneiric_apply_insight(agent_id: str, req: ApplyInsightRequest):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.apply_insight(agent_id, req.insight_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/oneiric/agents/{agent_id}/mutation-bias")
async def oneiric_set_mutation_bias(agent_id: str, req: SetMutationBiasRequest):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    result = engine.set_mutation_bias(agent_id, req.bias)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/oneiric/events")
async def oneiric_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.get_events(limit)}


@router.post("/oneiric/reset")
async def oneiric_reset():
    from sparkai.agent.agent_oneiric_synthesis_engine import AgentOneiricSynthesisEngine
    engine = AgentOneiricSynthesisEngine.get_instance()
    return {"status": "ok", "data": engine.reset()}
