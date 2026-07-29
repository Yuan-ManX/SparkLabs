"""
SparkLabs Backend - Epistemic Horizon Scanner Routes

REST endpoints for the Agent Epistemic Horizon Scanner.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    curiosity: float = 0.5


class AddNodeRequest(BaseModel):
    node_id: str
    domain: str
    label: str
    zone: str = "unknown_unknown"
    confidence: float = 0.0
    content: str = ""
    dependencies: List[str] = Field(default_factory=list)


class DiscoverBlindSpotRequest(BaseModel):
    node_id: str
    domain: str
    label: str


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/epistemic-horizon/agents")
async def epistemic_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    result = scanner.register_agent(req.agent_id, req.curiosity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/epistemic-horizon/agents/{agent_id}")
async def epistemic_remove_agent(agent_id: str):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    result = scanner.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/epistemic-horizon/agents/{agent_id}/nodes")
async def epistemic_add_node(agent_id: str, req: AddNodeRequest):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner, KnowledgeDomain, KnowledgeZone,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    try:
        domain = KnowledgeDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    try:
        zone = KnowledgeZone(req.zone)
    except ValueError:
        return {"status": "error", "detail": f"Invalid zone: {req.zone}"}
    result = scanner.add_node(
        agent_id=agent_id,
        node_id=req.node_id,
        domain=domain,
        label=req.label,
        zone=zone,
        confidence=req.confidence,
        content=req.content,
        dependencies=req.dependencies,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/epistemic-horizon/agents/{agent_id}/explore/{node_id}")
async def epistemic_explore(agent_id: str, node_id: str):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    result = scanner.explore(agent_id, node_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/epistemic-horizon/agents/{agent_id}/discover")
async def epistemic_discover_blind_spot(agent_id: str, req: DiscoverBlindSpotRequest):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner, KnowledgeDomain,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    try:
        domain = KnowledgeDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = scanner.discover_blind_spot(agent_id, req.node_id, domain, req.label)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/epistemic-horizon/agents/{agent_id}/challenge/{node_id}")
async def epistemic_challenge(agent_id: str, node_id: str):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    result = scanner.challenge(agent_id, node_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/epistemic-horizon/cycle")
async def epistemic_cycle():
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.cycle()}


@router.post("/epistemic-horizon/simulate")
async def epistemic_simulate(req: SimulateRequest):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.simulate(req.cycles)}


@router.get("/epistemic-horizon/agents/{agent_id}")
async def epistemic_get_agent(agent_id: str):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    result = scanner.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/epistemic-horizon/inversions")
async def epistemic_get_inversions(limit: int = 20):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.get_inversions(limit)}


@router.get("/epistemic-horizon/events")
async def epistemic_get_events(limit: int = 50):
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.get_events_log(limit)}


@router.get("/epistemic-horizon/status")
async def epistemic_status():
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.get_status()}


@router.post("/epistemic-horizon/reset")
async def epistemic_reset():
    from sparkai.agent.agent_epistemic_horizon_scanner import (
        AgentEpistemicHorizonScanner,
    )
    scanner = AgentEpistemicHorizonScanner.get_instance()
    return {"status": "ok", "data": scanner.reset()}
