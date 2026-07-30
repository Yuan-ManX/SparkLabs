"""
SparkLabs Backend - Edge-of-Chaos Stabilizer Routes

REST endpoints for the Engine Edge-of-Chaos Stabilizer.
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
    domain: str = "agent"                # narrative/behavior/dialogue/emotion/world/combat/puzzle/agent
    target_entropy: float = 0.5          # 0.0-1.0
    mode: str = "active"                 # passive/active/aggressive


class SenseRequest(BaseModel):
    agent_id: str
    sample_id: str
    observed_entropy: float              # 0.0-1.0
    volatility: float = 0.3              # 0.0-1.0
    domain: Optional[str] = None         # override the agent's domain if needed
    context: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/edge-of-chaos/agents")
async def chaos_register_agent(req: RegisterAgentRequest):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import (
        EngineEdgeOfChaosStabilizer, SystemDomain, StabilizerMode,
    )
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    try:
        domain = SystemDomain(req.domain)
    except ValueError:
        return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    try:
        mode = StabilizerMode(req.mode)
    except ValueError:
        return {"status": "error", "detail": f"Invalid mode: {req.mode}"}
    result = stabilizer.register_agent(
        agent_id=req.agent_id,
        domain=domain,
        target_entropy=req.target_entropy,
        mode=mode,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/edge-of-chaos/samples")
async def chaos_sense(req: SenseRequest):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import (
        EngineEdgeOfChaosStabilizer, SystemDomain,
    )
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    domain: Optional[SystemDomain] = None
    if req.domain is not None:
        try:
            domain = SystemDomain(req.domain)
        except ValueError:
            return {"status": "error", "detail": f"Invalid domain: {req.domain}"}
    result = stabilizer.sense(
        agent_id=req.agent_id,
        sample_id=req.sample_id,
        observed_entropy=req.observed_entropy,
        volatility=req.volatility,
        domain=domain,
        context=req.context,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/edge-of-chaos/agents/{agent_id}")
async def chaos_get_agent_state(agent_id: str):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    result = stabilizer.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/edge-of-chaos/agents/{agent_id}/samples")
async def chaos_get_samples(agent_id: str, limit: int = 20):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    result = stabilizer.get_samples(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/edge-of-chaos/agents/{agent_id}/samples/{sample_id}")
async def chaos_get_sample(agent_id: str, sample_id: str):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    result = stabilizer.get_sample(agent_id, sample_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/edge-of-chaos/events")
async def chaos_get_events(limit: int = 50):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    return {"status": "ok", "data": stabilizer.get_events_log(limit=limit)}


@router.get("/edge-of-chaos/status")
async def chaos_get_status():
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    return {"status": "ok", "data": stabilizer.get_status()}


@router.post("/edge-of-chaos/cycle")
async def chaos_cycle():
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    return {"status": "ok", "data": stabilizer.cycle()}


@router.post("/edge-of-chaos/simulate")
async def chaos_simulate(req: SimulateRequest):
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    return {"status": "ok", "data": stabilizer.simulate(cycles=req.cycles)}


@router.post("/edge-of-chaos/reset")
async def chaos_reset():
    from sparkai.engine.engine_edge_of_chaos_stabilizer import EngineEdgeOfChaosStabilizer
    stabilizer = EngineEdgeOfChaosStabilizer.get_instance()
    return {"status": "ok", "data": stabilizer.reset()}
