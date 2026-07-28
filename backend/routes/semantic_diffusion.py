"""
SparkLabs Backend - Semantic Diffusion Field Routes

REST API endpoints for AgentSemanticDiffusionField: knowledge diffusion
through agent populations with EMIT/PROPAGATE/ABSORB/DECAY/CRYSTALLIZE cycle.
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
    role: str = "conduit"
    permeability: float = 0.5
    retention: float = 0.5


class SetResistanceRequest(BaseModel):
    knowledge_type: str
    resistance: float


class ConnectRequest(BaseModel):
    target_id: str
    bandwidth: float = 0.5
    latency: float = 0.0
    filter_types: Optional[List[str]] = None


class EmitRequest(BaseModel):
    knowledge_id: str
    label: str
    knowledge_type: str
    origin_id: str
    strength: float = 1.0
    description: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Agent Routes
# =============================================================================

@router.get("/semantic-diffusion/status")
async def semantic_diffusion_status():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.get_status()}


@router.post("/semantic-diffusion/agents")
async def semantic_diffusion_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_semantic_diffusion_field import (
        AgentSemanticDiffusionField, AgentRole,
    )
    field = AgentSemanticDiffusionField.get_instance()
    try:
        role = AgentRole(req.role)
    except ValueError:
        return {"status": "error", "detail": f"Invalid role: {req.role}"}
    result = field.register_agent(
        agent_id=req.agent_id,
        role=role,
        permeability=req.permeability,
        retention=req.retention,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/semantic-diffusion/agents/{agent_id}")
async def semantic_diffusion_remove_agent(agent_id: str):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/semantic-diffusion/agents")
async def semantic_diffusion_list_agents():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.list_agents()}


@router.get("/semantic-diffusion/agents/{agent_id}")
async def semantic_diffusion_get_agent(agent_id: str):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.get_agent(agent_id)
    if result is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": result}


@router.put("/semantic-diffusion/agents/{agent_id}/resistance")
async def semantic_diffusion_set_resistance(agent_id: str, req: SetResistanceRequest):
    from sparkai.agent.agent_semantic_diffusion_field import (
        AgentSemanticDiffusionField, KnowledgeType,
    )
    field = AgentSemanticDiffusionField.get_instance()
    try:
        kt = KnowledgeType(req.knowledge_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid knowledge_type: {req.knowledge_type}"}
    result = field.set_resistance(agent_id, kt, req.resistance)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Connection Routes
# =============================================================================

@router.post("/semantic-diffusion/agents/{source_id}/connections")
async def semantic_diffusion_connect(source_id: str, req: ConnectRequest):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.connect(
        source_id=source_id,
        target_id=req.target_id,
        bandwidth=req.bandwidth,
        latency=req.latency,
        filter_types=req.filter_types,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/semantic-diffusion/agents/{source_id}/connections/{target_id}")
async def semantic_diffusion_disconnect(source_id: str, target_id: str):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.disconnect(source_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Knowledge Routes
# =============================================================================

@router.post("/semantic-diffusion/knowledge")
async def semantic_diffusion_emit(req: EmitRequest):
    from sparkai.agent.agent_semantic_diffusion_field import (
        AgentSemanticDiffusionField, KnowledgeType,
    )
    field = AgentSemanticDiffusionField.get_instance()
    try:
        kt = KnowledgeType(req.knowledge_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid knowledge_type: {req.knowledge_type}"}
    result = field.emit(
        knowledge_id=req.knowledge_id,
        label=req.label,
        knowledge_type=kt,
        origin_id=req.origin_id,
        strength=req.strength,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/semantic-diffusion/knowledge")
async def semantic_diffusion_list_packets():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.list_packets()}


@router.get("/semantic-diffusion/knowledge/{knowledge_id}")
async def semantic_diffusion_get_packet(knowledge_id: str):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.get_packet(knowledge_id)
    if result is None:
        return {"status": "error", "detail": f"Knowledge not found: {knowledge_id}"}
    return {"status": "ok", "data": result}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/semantic-diffusion/beliefs")
async def semantic_diffusion_get_beliefs():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.get_beliefs()}


@router.get("/semantic-diffusion/waves")
async def semantic_diffusion_get_waves(limit: int = Query(20, ge=1, le=200)):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.get_waves(limit)}


@router.get("/semantic-diffusion/events")
async def semantic_diffusion_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/semantic-diffusion/cycle")
async def semantic_diffusion_cycle():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.cycle()}


@router.post("/semantic-diffusion/simulate")
async def semantic_diffusion_simulate(req: SimulateRequest):
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    result = field.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/semantic-diffusion/reset")
async def semantic_diffusion_reset():
    from sparkai.agent.agent_semantic_diffusion_field import AgentSemanticDiffusionField
    field = AgentSemanticDiffusionField.get_instance()
    return {"status": "ok", "data": field.reset()}
