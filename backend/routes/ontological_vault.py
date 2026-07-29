"""
SparkLabs Backend - Ontological Vault Architect Routes

REST endpoints for the Agent Ontological Vault Architect.
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
    openness: float = 0.3
    rigidity: float = 0.5
    integrative_capacity: float = 0.4


class CrystallizeCommitmentRequest(BaseModel):
    commitment_id: str
    label: str
    domain: str = "material"          # material/spiritual/causal/temporal/agency/identity/moral/epistemic
    proposition: str
    seal_depth: str = "deep"          # surface/shallow/deep/abyssal
    conviction: float = 0.7
    foundationality: float = 0.7
    support_anchors: List[str] = []
    content: str = ""


class ApplyStressRequest(BaseModel):
    stress_type: str = "evidential"   # evidential/coherence/revealatory/social/experiential/existential
    intensity: float = 0.5
    evidence_description: str = ""


class LinkAnchorRequest(BaseModel):
    anchor_id: str


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/ontological-vault/agents")
async def vault_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    result = arch.register_agent(
        agent_id=req.agent_id,
        openness=req.openness,
        rigidity=req.rigidity,
        integrative_capacity=req.integrative_capacity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/ontological-vault/agents/{agent_id}")
async def vault_remove_agent(agent_id: str):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    result = arch.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/ontological-vault/agents/{agent_id}/commitments")
async def vault_crystallize_commitment(agent_id: str, req: CrystallizeCommitmentRequest):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect, OntologicalDomain, SealDepth,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    try:
        domain = OntologicalDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    try:
        seal_depth = SealDepth(req.seal_depth)
    except ValueError:
        return {"status": "error", "detail": f"Invalid seal_depth: {req.seal_depth}"}
    result = arch.crystallize_commitment(
        agent_id=agent_id,
        commitment_id=req.commitment_id,
        label=req.label,
        domain=domain,
        proposition=req.proposition,
        seal_depth=seal_depth,
        conviction=req.conviction,
        foundationality=req.foundationality,
        support_anchors=req.support_anchors,
        content=req.content,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/ontological-vault/agents/{agent_id}/commitments/{commitment_id}/stress")
async def vault_apply_stress(agent_id: str, commitment_id: str, req: ApplyStressRequest):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect, StressType,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    try:
        stress_type = StressType(req.stress_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid stress_type: {req.stress_type}"}
    result = arch.apply_stress(
        agent_id=agent_id,
        commitment_id=commitment_id,
        stress_type=stress_type,
        intensity=req.intensity,
        evidence_description=req.evidence_description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/ontological-vault/agents/{agent_id}/commitments/{commitment_id}/anchors")
async def vault_link_anchor(agent_id: str, commitment_id: str, req: LinkAnchorRequest):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    result = arch.link_anchor(
        agent_id=agent_id,
        commitment_id=commitment_id,
        anchor_id=req.anchor_id,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/ontological-vault/agents/{agent_id}")
async def vault_get_agent_state(agent_id: str):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    result = arch.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/ontological-vault/agents/{agent_id}/commitments/{commitment_id}")
async def vault_get_commitment(agent_id: str, commitment_id: str):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    result = arch.get_commitment(agent_id, commitment_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/ontological-vault/stress-events")
async def vault_get_stress_events(agent_id: Optional[str] = None, limit: int = 50):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.get_stress_events(agent_id=agent_id, limit=limit)}


@router.get("/ontological-vault/transcendences")
async def vault_get_transcendences(agent_id: Optional[str] = None, limit: int = 20):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.get_transcendences(agent_id=agent_id, limit=limit)}


@router.get("/ontological-vault/events")
async def vault_get_events(limit: int = 50):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.get_events_log(limit=limit)}


@router.get("/ontological-vault/status")
async def vault_get_status():
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.get_status()}


@router.post("/ontological-vault/cycle")
async def vault_cycle():
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.cycle()}


@router.post("/ontological-vault/simulate")
async def vault_simulate(req: SimulateRequest):
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.simulate(cycles=req.cycles)}


@router.post("/ontological-vault/reset")
async def vault_reset():
    from sparkai.agent.agent_ontological_vault_architect import (
        AgentOntologicalVaultArchitect,
    )
    arch = AgentOntologicalVaultArchitect.get_instance()
    return {"status": "ok", "data": arch.reset()}
