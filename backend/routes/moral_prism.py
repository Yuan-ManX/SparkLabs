"""
SparkLabs Backend - Moral Prism Refractor Routes

REST endpoints for the Agent Moral Prism Refractor.
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
    lens_curvatures: Optional[Dict[str, float]] = None
    # lens keys: virtue/consequence/duty/care/justice/authority/liberty


class EncounterDilemmaRequest(BaseModel):
    agent_id: str
    dilemma_id: str
    label: str
    domain: str = "justice"             # combat/loyalty/survival/truth/justice/resource/identity/power
    options: Optional[List[str]] = None
    stakes: float = 0.5                 # 0.0-1.0
    context: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/moral-prism/agents")
async def moral_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor, EthicalLens
    refractor = AgentMoralPrismRefractor.get_instance()
    lens_curvatures: Optional[Dict[EthicalLens, float]] = None
    if req.lens_curvatures:
        lens_curvatures = {}
        for lens_name, curvature in req.lens_curvatures.items():
            try:
                lens_curvatures[EthicalLens(lens_name)] = curvature
            except ValueError:
                return {"status": "error", "detail": f"Invalid lens: {lens_name}"}
    result = refractor.register_agent(req.agent_id, lens_curvatures=lens_curvatures)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/moral-prism/dilemmas")
async def moral_encounter_dilemma(req: EncounterDilemmaRequest):
    from sparkai.agent.agent_moral_prism_refractor import (
        AgentMoralPrismRefractor, DilemmaDomain,
    )
    refractor = AgentMoralPrismRefractor.get_instance()
    try:
        domain = DilemmaDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = refractor.encounter_dilemma(
        agent_id=req.agent_id,
        dilemma_id=req.dilemma_id,
        label=req.label,
        domain=domain,
        options=req.options,
        stakes=req.stakes,
        context=req.context,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/moral-prism/agents/{agent_id}")
async def moral_get_agent_state(agent_id: str):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    result = refractor.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/moral-prism/agents/{agent_id}/stances")
async def moral_get_stances(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    result = refractor.get_stances(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/moral-prism/agents/{agent_id}/stances/{dilemma_id}")
async def moral_get_stance(agent_id: str, dilemma_id: str):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    result = refractor.get_stance(agent_id, dilemma_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/moral-prism/events")
async def moral_get_events(limit: int = 50):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    return {"status": "ok", "data": refractor.get_events_log(limit=limit)}


@router.get("/moral-prism/status")
async def moral_get_status():
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    return {"status": "ok", "data": refractor.get_status()}


@router.post("/moral-prism/cycle")
async def moral_cycle():
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    return {"status": "ok", "data": refractor.cycle()}


@router.post("/moral-prism/simulate")
async def moral_simulate(req: SimulateRequest):
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    return {"status": "ok", "data": refractor.simulate(cycles=req.cycles)}


@router.post("/moral-prism/reset")
async def moral_reset():
    from sparkai.agent.agent_moral_prism_refractor import AgentMoralPrismRefractor
    refractor = AgentMoralPrismRefractor.get_instance()
    return {"status": "ok", "data": refractor.reset()}
