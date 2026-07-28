"""
SparkLabs Backend - Volition Genesis Reactor Routes

REST API endpoints for AgentVolitionGenesisReactor: volition emergence
with NUCLEATE/IGNITE/SUSTAIN/DECAY/TRANSMUTE cycle.
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


class AddDesireRequest(BaseModel):
    desire_id: str
    desire_type: str
    label: str
    intensity: float = 0.5
    volatility: float = 0.3


class AddBeliefRequest(BaseModel):
    belief_id: str
    label: str
    confidence: float = 0.5
    domain: str = "general"
    enables: Optional[List[str]] = None
    inhibits: Optional[List[str]] = None


class AddOpportunityRequest(BaseModel):
    opportunity_id: str
    label: str
    domain: str
    affinity_desires: Optional[List[str]] = None
    strength: float = 0.5
    urgency: float = 0.3


class BlockIntentionRequest(BaseModel):
    resistance: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Agent Routes
# =============================================================================

@router.get("/volition-reactor/status")
async def volition_reactor_status():
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    return {"status": "ok", "data": reactor.get_status()}


@router.post("/volition-reactor/agents")
async def volition_reactor_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.register_agent(req.agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/volition-reactor/agents/{agent_id}")
async def volition_reactor_remove_agent(agent_id: str):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/volition-reactor/agents")
async def volition_reactor_list_agents():
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    return {"status": "ok", "data": reactor.list_agents()}


@router.get("/volition-reactor/agents/{agent_id}")
async def volition_reactor_get_agent(agent_id: str):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.get_agent(agent_id)
    if result is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": result}


# =============================================================================
# Desire Routes
# =============================================================================

@router.post("/volition-reactor/agents/{agent_id}/desires")
async def volition_reactor_add_desire(agent_id: str, req: AddDesireRequest):
    from sparkai.agent.agent_volition_genesis_reactor import (
        AgentVolitionGenesisReactor, DesireType,
    )
    reactor = AgentVolitionGenesisReactor.get_instance()
    try:
        dt = DesireType(req.desire_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid desire_type: {req.desire_type}"}
    result = reactor.add_desire(
        agent_id=agent_id,
        desire_id=req.desire_id,
        desire_type=dt,
        label=req.label,
        intensity=req.intensity,
        volatility=req.volatility,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Belief Routes
# =============================================================================

@router.post("/volition-reactor/agents/{agent_id}/beliefs")
async def volition_reactor_add_belief(agent_id: str, req: AddBeliefRequest):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.add_belief(
        agent_id=agent_id,
        belief_id=req.belief_id,
        label=req.label,
        confidence=req.confidence,
        domain=req.domain,
        enables=req.enables,
        inhibits=req.inhibits,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Opportunity Routes
# =============================================================================

@router.post("/volition-reactor/agents/{agent_id}/opportunities")
async def volition_reactor_add_opportunity(agent_id: str, req: AddOpportunityRequest):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.add_opportunity(
        agent_id=agent_id,
        opportunity_id=req.opportunity_id,
        label=req.label,
        domain=req.domain,
        affinity_desires=req.affinity_desires,
        strength=req.strength,
        urgency=req.urgency,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Intention Routes
# =============================================================================

@router.post("/volition-reactor/agents/{agent_id}/intentions/{intention_id}/fulfill")
async def volition_reactor_fulfill_intention(agent_id: str, intention_id: str):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.fulfill_intention(agent_id, intention_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/volition-reactor/agents/{agent_id}/intentions/{intention_id}/block")
async def volition_reactor_block_intention(agent_id: str, intention_id: str, req: BlockIntentionRequest):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.block_intention(agent_id, intention_id, req.resistance)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/volition-reactor/cycle")
async def volition_reactor_cycle():
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    return {"status": "ok", "data": reactor.cycle()}


@router.post("/volition-reactor/simulate")
async def volition_reactor_simulate(req: SimulateRequest):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    result = reactor.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/volition-reactor/events")
async def volition_reactor_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    return {"status": "ok", "data": reactor.get_events_log(limit)}


@router.post("/volition-reactor/reset")
async def volition_reactor_reset():
    from sparkai.agent.agent_volition_genesis_reactor import AgentVolitionGenesisReactor
    reactor = AgentVolitionGenesisReactor.get_instance()
    return {"status": "ok", "data": reactor.reset()}
