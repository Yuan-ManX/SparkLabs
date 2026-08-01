"""
SparkLabs Backend - Causal Blame Arbiter Routes

REST endpoints for the Agent Causal Blame Arbiter.
"""
from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class ContributorModel(BaseModel):
    contributor_id: str
    role: str = ""
    intent_score: float = 0.0                  # 0.0-1.0
    foresight_score: float = 0.0               # 0.0-1.0
    negligence_score: float = 0.0              # 0.0-1.0
    proximate_strength: float = 0.0            # 0.0-1.0
    note: str = ""


class CausalLinkModel(BaseModel):
    from_id: str
    to_id: str
    strength: str = "moderate"                 # direct/strong/moderate/weak/tenuous
    note: str = ""


class RegisterEventRequest(BaseModel):
    event_id: str
    contributors: List[ContributorModel] = Field(default_factory=list)
    links: List[CausalLinkModel] = Field(default_factory=list)
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/causal-blame-arbiter/events")
async def arbiter_register_event(req: RegisterEventRequest):
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    result = arbiter.register_event(
        event_id=req.event_id,
        contributors=[c.model_dump() for c in req.contributors],
        links=[l.model_dump() for l in req.links],
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-blame-arbiter/cycle")
async def arbiter_cycle():
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.cycle()}


@router.get("/causal-blame-arbiter/events/{event_id}/verdict")
async def arbiter_get_verdict(event_id: str):
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    result = arbiter.get_verdict(event_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-blame-arbiter/status")
async def arbiter_get_status():
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.get_status()}


@router.get("/causal-blame-arbiter/ledger")
async def arbiter_get_ledger():
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.get_ledger()}


@router.get("/causal-blame-arbiter/events")
async def arbiter_get_events(limit: int = 50):
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.get_events_log(limit=limit)}


@router.post("/causal-blame-arbiter/simulate")
async def arbiter_simulate(req: SimulateRequest):
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.simulate(cycles=req.cycles)}


@router.post("/causal-blame-arbiter/reset")
async def arbiter_reset():
    from sparkai.agent.agent_causal_blame_arbiter import AgentCausalBlameArbiter
    arbiter = AgentCausalBlameArbiter.get_instance()
    return {"status": "ok", "data": arbiter.reset()}
