"""
SparkLabs Backend - Somatic Marker Crucible Routes

REST endpoints for the Agent Somatic Marker Crucible.
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
    sensitivity: float = 0.5
    tempering_rate: float = 0.5
    alloy_threshold: int = 3


class SenseSituationRequest(BaseModel):
    marker_id: str
    archetype: str = "combat"        # combat/social/exploration/decision/loss/gain/betrayal/revelation/danger/intimacy/ritual/transition
    domain: str = "visceral"         # visceral/kinesthetic/thermal/cardiac/respiratory/facial/autonomic/proprioceptive
    label: str
    valence: str = "avoid"           # approach/avoid/ambivalent/neutral
    intensity: float = 0.5
    consistency: float = 0.5
    situation_tags: List[str] = []
    bodily_signature: str = ""


class TriggerMarkerRequest(BaseModel):
    situation_intensity: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/somatic-crucible/agents")
async def crucible_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    result = crucible.register_agent(
        agent_id=req.agent_id,
        sensitivity=req.sensitivity,
        tempering_rate=req.tempering_rate,
        alloy_threshold=req.alloy_threshold,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/somatic-crucible/agents/{agent_id}")
async def crucible_remove_agent(agent_id: str):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    result = crucible.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/somatic-crucible/agents/{agent_id}/markers")
async def crucible_sense_situation(agent_id: str, req: SenseSituationRequest):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible, SituationArchetype, SomaticDomain, ValencePolarity,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    try:
        archetype = SituationArchetype(req.archetype)
    except ValueError:
        return {"status": "error", "detail": f"Invalid archetype: {req.archetype}"}
    try:
        domain = SomaticDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    try:
        valence = ValencePolarity(req.valence)
    except ValueError:
        return {"status": "error", "detail": f"Invalid valence: {req.valence}"}
    result = crucible.sense_situation(
        agent_id=agent_id,
        marker_id=req.marker_id,
        archetype=archetype,
        domain=domain,
        label=req.label,
        valence=valence,
        intensity=req.intensity,
        consistency=req.consistency,
        situation_tags=req.situation_tags,
        bodily_signature=req.bodily_signature,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/somatic-crucible/agents/{agent_id}/markers/{marker_id}/trigger")
async def crucible_trigger_marker(agent_id: str, marker_id: str, req: TriggerMarkerRequest):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    result = crucible.trigger_marker(
        agent_id=agent_id,
        marker_id=marker_id,
        situation_intensity=req.situation_intensity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/somatic-crucible/agents/{agent_id}")
async def crucible_get_agent_state(agent_id: str):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    result = crucible.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/somatic-crucible/agents/{agent_id}/markers/{marker_id}")
async def crucible_get_marker(agent_id: str, marker_id: str):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    result = crucible.get_marker(agent_id, marker_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/somatic-crucible/events")
async def crucible_get_events(limit: int = 50):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    return {"status": "ok", "data": crucible.get_events_log(limit=limit)}


@router.get("/somatic-crucible/status")
async def crucible_get_status():
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    return {"status": "ok", "data": crucible.get_status()}


@router.post("/somatic-crucible/cycle")
async def crucible_cycle():
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    return {"status": "ok", "data": crucible.cycle()}


@router.post("/somatic-crucible/simulate")
async def crucible_simulate(req: SimulateRequest):
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    return {"status": "ok", "data": crucible.simulate(cycles=req.cycles)}


@router.post("/somatic-crucible/reset")
async def crucible_reset():
    from sparkai.agent.agent_somatic_marker_crucible import (
        AgentSomaticMarkerCrucible,
    )
    crucible = AgentSomaticMarkerCrucible.get_instance()
    return {"status": "ok", "data": crucible.reset()}
