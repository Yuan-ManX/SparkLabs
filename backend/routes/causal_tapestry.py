"""
SparkLabs Backend - Causal Tapestry Loom Routes

REST API endpoints for AgentCausalTapestryLoom: agent causal reasoning
modeled as a weaving process with SPIN/DYE/WEAVE/MEND/UNRAVEL cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str


class ObserveEventRequest(BaseModel):
    event_id: str
    label: str
    domain: str
    properties: Optional[Dict[str, Any]] = None


class SpinThreadRequest(BaseModel):
    thread_id: str
    source_event: str
    target_event: str
    thread_type: str = "direct"
    strength: float = 0.5
    valence: float = 0.0
    salience: float = 0.5
    description: str = ""
    tense: str = "past"


class DyeThreadRequest(BaseModel):
    valence: Optional[float] = None
    salience: Optional[float] = None
    tags: Optional[List[str]] = None
    strength_boost: float = 0.0


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Agent Routes
# =============================================================================

@router.get("/causal-tapestry/status")
async def causal_tapestry_status():
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.get_status()}


@router.post("/causal-tapestry/agents")
async def causal_tapestry_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.register_agent(req.agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/causal-tapestry/agents/{agent_id}")
async def causal_tapestry_remove_agent(agent_id: str):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-tapestry/agents")
async def causal_tapestry_list_agents():
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.list_agents()}


@router.get("/causal-tapestry/agents/{agent_id}")
async def causal_tapestry_get_tapestry(agent_id: str):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.get_tapestry(agent_id)
    if result is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": result}


# =============================================================================
# Event Routes
# =============================================================================

@router.post("/causal-tapestry/agents/{agent_id}/events")
async def causal_tapestry_observe_event(agent_id: str, req: ObserveEventRequest):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.observe_event(
        agent_id=agent_id,
        event_id=req.event_id,
        label=req.label,
        domain=req.domain,
        properties=req.properties,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Thread Routes
# =============================================================================

@router.post("/causal-tapestry/agents/{agent_id}/threads")
async def causal_tapestry_spin_thread(agent_id: str, req: SpinThreadRequest):
    from sparkai.agent.agent_causal_tapestry_loom import (
        AgentCausalTapestryLoom, ThreadType, ThreadTense,
    )
    loom = AgentCausalTapestryLoom.get_instance()
    try:
        tt = ThreadType(req.thread_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid thread_type: {req.thread_type}"}
    try:
        tense = ThreadTense(req.tense)
    except ValueError:
        return {"status": "error", "detail": f"Invalid tense: {req.tense}"}
    result = loom.spin_thread(
        agent_id=agent_id,
        thread_id=req.thread_id,
        source_event=req.source_event,
        target_event=req.target_event,
        thread_type=tt,
        strength=req.strength,
        valence=req.valence,
        salience=req.salience,
        description=req.description,
        tense=tense,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.put("/causal-tapestry/agents/{agent_id}/threads/{thread_id}/dye")
async def causal_tapestry_dye_thread(agent_id: str, thread_id: str, req: DyeThreadRequest):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.dye_thread(
        agent_id=agent_id,
        thread_id=thread_id,
        valence=req.valence,
        salience=req.salience,
        tags=req.tags,
        strength_boost=req.strength_boost,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-tapestry/agents/{agent_id}/weave")
async def causal_tapestry_weave(agent_id: str):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.weave(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-tapestry/agents/{agent_id}/mend")
async def causal_tapestry_mend(agent_id: str):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.mend(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-tapestry/agents/{agent_id}/unravel")
async def causal_tapestry_unravel(agent_id: str, max_age: float = Query(3600.0, ge=0.0)):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.unravel(agent_id, max_age=max_age)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/causal-tapestry/agents/{agent_id}/regions")
async def causal_tapestry_get_regions(agent_id: str):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.get_regions(agent_id)}


@router.get("/causal-tapestry/agents/{agent_id}/gaps")
async def causal_tapestry_get_gaps(agent_id: str, limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.get_gaps(agent_id, limit)}


@router.get("/causal-tapestry/events")
async def causal_tapestry_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.get_events(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/causal-tapestry/cycle")
async def causal_tapestry_cycle():
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.cycle()}


@router.post("/causal-tapestry/simulate")
async def causal_tapestry_simulate(req: SimulateRequest):
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    result = loom.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-tapestry/reset")
async def causal_tapestry_reset():
    from sparkai.agent.agent_causal_tapestry_loom import AgentCausalTapestryLoom
    loom = AgentCausalTapestryLoom.get_instance()
    return {"status": "ok", "data": loom.reset()}
