"""
SparkLabs Backend - Identity Crystallization Forge Routes

REST API endpoints for AgentIdentityCrystallizationForge: identity formation
and transformation with DISTILL/CRYSTALLIZE/TEMPER/FRACTURE/REFRACT cycle.
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
    confidence: float = 0.5
    openness: float = 0.5


class AddFacetRequest(BaseModel):
    facet_id: str
    domain: str
    label: str
    description: str = ""
    initial_weight: float = 0.1


class DepositExperienceRequest(BaseModel):
    deposit_id: str
    agent_id: str
    label: str
    domain: str
    valence: float = 0.0
    intensity: float = 0.5
    target_facets: Optional[List[str]] = None
    is_contradiction: bool = False
    description: str = ""


class AlignFacetsRequest(BaseModel):
    facet_a: str
    facet_b: str


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Agent Routes
# =============================================================================

@router.get("/identity-forge/status")
async def identity_forge_status():
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.get_status()}


@router.post("/identity-forge/agents")
async def identity_forge_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.register_agent(
        agent_id=req.agent_id,
        confidence=req.confidence,
        openness=req.openness,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/identity-forge/agents")
async def identity_forge_list_agents():
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.list_agents()}


@router.get("/identity-forge/agents/{agent_id}")
async def identity_forge_get_agent(agent_id: str):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.get_agent(agent_id)
    if result is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": result}


@router.delete("/identity-forge/agents/{agent_id}")
async def identity_forge_remove_agent(agent_id: str):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Facet Routes
# =============================================================================

@router.post("/identity-forge/agents/{agent_id}/facets")
async def identity_forge_add_facet_for_agent(agent_id: str, req: AddFacetRequest):
    from sparkai.agent.agent_identity_crystallization_forge import (
        AgentIdentityCrystallizationForge, FacetDomain,
    )
    forge = AgentIdentityCrystallizationForge.get_instance()
    try:
        domain = FacetDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = forge.add_facet(
        agent_id=agent_id,
        facet_id=req.facet_id,
        domain=domain,
        label=req.label,
        description=req.description,
        initial_weight=req.initial_weight,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/identity-forge/facets")
async def identity_forge_list_facets(agent_id: Optional[str] = Query(None), limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.list_facets(agent_id, limit)}


@router.get("/identity-forge/facets/{facet_id}")
async def identity_forge_get_facet(facet_id: str):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.get_facet(facet_id)
    if result is None:
        return {"status": "error", "detail": f"Facet not found: {facet_id}"}
    return {"status": "ok", "data": result}


@router.post("/identity-forge/facets/align")
async def identity_forge_align_facets(req: AlignFacetsRequest):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.align_facets(req.facet_a, req.facet_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/identity-forge/facets/oppose")
async def identity_forge_oppose_facets(req: AlignFacetsRequest):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.oppose_facets(req.facet_a, req.facet_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Experience Deposit Routes
# =============================================================================

@router.post("/identity-forge/deposits")
async def identity_forge_deposit_experience(req: DepositExperienceRequest):
    from sparkai.agent.agent_identity_crystallization_forge import (
        AgentIdentityCrystallizationForge, FacetDomain,
    )
    forge = AgentIdentityCrystallizationForge.get_instance()
    try:
        domain = FacetDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = forge.deposit_experience(
        deposit_id=req.deposit_id,
        agent_id=req.agent_id,
        label=req.label,
        domain=domain,
        valence=req.valence,
        intensity=req.intensity,
        target_facets=req.target_facets,
        is_contradiction=req.is_contradiction,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/identity-forge/deposits")
async def identity_forge_get_deposits(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.get_deposits(limit)}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/identity-forge/crises")
async def identity_forge_get_crises(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.get_crises(limit)}


@router.get("/identity-forge/events")
async def identity_forge_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/identity-forge/cycle")
async def identity_forge_cycle():
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.cycle()}


@router.post("/identity-forge/simulate")
async def identity_forge_simulate(req: SimulateRequest):
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    result = forge.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/identity-forge/reset")
async def identity_forge_reset():
    from sparkai.agent.agent_identity_crystallization_forge import AgentIdentityCrystallizationForge
    forge = AgentIdentityCrystallizationForge.get_instance()
    return {"status": "ok", "data": forge.reset()}
