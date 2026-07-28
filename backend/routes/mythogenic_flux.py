"""
SparkLabs Backend - Mythogenic Flux Conductor Routes

REST endpoints for the Agent Mythogenic Flux Conductor.
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
    temperament: str
    receptivity: float = 0.5


class OpenChannelRequest(BaseModel):
    channel_id: str
    agent_a: str
    agent_b: str
    conductance_type: str
    bandwidth: float = 0.5
    clarity: float = 0.7


class SeedMythRequest(BaseModel):
    myth_id: str
    origin_agent: str
    myth_type: str
    title: str
    content: str
    initial_charge: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/mythogenic-flux/agents")
async def mythogenic_flux_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor, CarrierTemperament,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    try:
        temp = CarrierTemperament(req.temperament)
    except ValueError:
        return {"status": "error", "detail": f"Invalid temperament: {req.temperament}"}
    result = conductor.register_agent(req.agent_id, temp, req.receptivity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/mythogenic-flux/agents/{agent_id}")
async def mythogenic_flux_remove_agent(agent_id: str):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    result = conductor.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mythogenic-flux/channels")
async def mythogenic_flux_open_channel(req: OpenChannelRequest):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor, ConductanceType,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    try:
        ctype = ConductanceType(req.conductance_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid conductance_type: {req.conductance_type}"}
    result = conductor.open_channel(
        channel_id=req.channel_id,
        agent_a=req.agent_a,
        agent_b=req.agent_b,
        conductance_type=ctype,
        bandwidth=req.bandwidth,
        clarity=req.clarity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mythogenic-flux/myths")
async def mythogenic_flux_seed_myth(req: SeedMythRequest):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor, MythType,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    try:
        mtype = MythType(req.myth_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid myth_type: {req.myth_type}"}
    result = conductor.seed_myth(
        myth_id=req.myth_id,
        origin_agent=req.origin_agent,
        myth_type=mtype,
        title=req.title,
        content=req.content,
        initial_charge=req.initial_charge,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/mythogenic-flux/cycle")
async def mythogenic_flux_cycle():
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.cycle()}


@router.post("/mythogenic-flux/simulate")
async def mythogenic_flux_simulate(req: SimulateRequest):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.simulate(req.cycles)}


@router.get("/mythogenic-flux/agents/{agent_id}")
async def mythogenic_flux_get_agent(agent_id: str):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    result = conductor.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mythogenic-flux/myths")
async def mythogenic_flux_get_myths():
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.get_all_myths()}


@router.get("/mythogenic-flux/myths/{myth_id}")
async def mythogenic_flux_get_myth(myth_id: str):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    result = conductor.get_myth(myth_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mythogenic-flux/legends")
async def mythogenic_flux_get_legends():
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.get_legends()}


@router.get("/mythogenic-flux/channels")
async def mythogenic_flux_get_channels(agent_id: Optional[str] = None):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.get_channels(agent_id)}


@router.get("/mythogenic-flux/events")
async def mythogenic_flux_get_events(limit: int = 50):
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.get_events_log(limit)}


@router.get("/mythogenic-flux/status")
async def mythogenic_flux_status():
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.get_status()}


@router.post("/mythogenic-flux/reset")
async def mythogenic_flux_reset():
    from sparkai.agent.agent_mythogenic_flux_conductor import (
        AgentMythogenicFluxConductor,
    )
    conductor = AgentMythogenicFluxConductor.get_instance()
    return {"status": "ok", "data": conductor.reset()}
