"""
SparkLabs Backend - Empathy Resonance Network Routes

REST API endpoints for AgentEmpathyResonanceNetwork: empathy emergence
through shared emotional experiences with ATTUNE/MIRROR/RESONATE/ABSORB/PROJECT cycle.
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
    baseline_valence: float = 0.0
    baseline_arousal: float = 0.3
    empathy_capacity: float = 0.5


class RecordEpisodeRequest(BaseModel):
    episode_id: str
    agent_id: str
    emotion: str
    valence: float = 0.0
    arousal: float = 0.3
    context: str = ""
    shared_with: Optional[List[str]] = None


class FormBondRequest(BaseModel):
    agent_a: str
    agent_b: str
    empathy_type: str
    mode: str = "sympathetic"
    initial_strength: float = 0.1


class ReinforceBondRequest(BaseModel):
    amount: float = 0.1


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Agent Routes
# =============================================================================

@router.get("/empathy-resonance/status")
async def empathy_resonance_status():
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.get_status()}


@router.post("/empathy-resonance/agents")
async def empathy_resonance_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.register_agent(
        agent_id=req.agent_id,
        baseline_valence=req.baseline_valence,
        baseline_arousal=req.baseline_arousal,
        empathy_capacity=req.empathy_capacity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathy-resonance/agents")
async def empathy_resonance_list_agents():
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.list_agents()}


@router.get("/empathy-resonance/agents/{agent_id}")
async def empathy_resonance_get_agent(agent_id: str):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.get_agent(agent_id)
    if result is None:
        return {"status": "error", "detail": f"Agent not found: {agent_id}"}
    return {"status": "ok", "data": result}


@router.delete("/empathy-resonance/agents/{agent_id}")
async def empathy_resonance_remove_agent(agent_id: str):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Episode Routes
# =============================================================================

@router.post("/empathy-resonance/episodes")
async def empathy_resonance_record_episode(req: RecordEpisodeRequest):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.record_episode(
        episode_id=req.episode_id,
        agent_id=req.agent_id,
        emotion=req.emotion,
        valence=req.valence,
        arousal=req.arousal,
        context=req.context,
        shared_with=req.shared_with,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathy-resonance/episodes")
async def empathy_resonance_get_episodes(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.get_episodes(limit)}


# =============================================================================
# Bond Routes
# =============================================================================

@router.post("/empathy-resonance/bonds")
async def empathy_resonance_form_bond(req: FormBondRequest):
    from sparkai.agent.agent_empathy_resonance_network import (
        AgentEmpathyResonanceNetwork, EmpathyType, ResonanceMode,
    )
    network = AgentEmpathyResonanceNetwork.get_instance()
    try:
        et = EmpathyType(req.empathy_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid empathy_type: {req.empathy_type}"}
    try:
        mode = ResonanceMode(req.mode)
    except ValueError:
        return {"status": "error", "detail": f"Invalid mode: {req.mode}"}
    result = network.form_bond(
        agent_a=req.agent_a,
        agent_b=req.agent_b,
        empathy_type=et,
        mode=mode,
        initial_strength=req.initial_strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathy-resonance/bonds")
async def empathy_resonance_list_bonds():
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.list_bonds()}


@router.get("/empathy-resonance/bonds/{bond_id}")
async def empathy_resonance_get_bond(bond_id: str):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.get_bond(bond_id)
    if result is None:
        return {"status": "error", "detail": f"Bond not found: {bond_id}"}
    return {"status": "ok", "data": result}


@router.post("/empathy-resonance/bonds/{bond_id}/reinforce")
async def empathy_resonance_reinforce_bond(bond_id: str, req: ReinforceBondRequest):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.reinforce_bond(bond_id, req.amount)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/empathy-resonance/bonds/{bond_id}")
async def empathy_resonance_sever_bond(bond_id: str):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.sever_bond(bond_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/empathy-resonance/actions")
async def empathy_resonance_get_actions(limit: int = Query(20, ge=1, le=100)):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.get_actions(limit)}


@router.get("/empathy-resonance/events")
async def empathy_resonance_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/empathy-resonance/cycle")
async def empathy_resonance_cycle():
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.cycle()}


@router.post("/empathy-resonance/simulate")
async def empathy_resonance_simulate(req: SimulateRequest):
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    result = network.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/empathy-resonance/reset")
async def empathy_resonance_reset():
    from sparkai.agent.agent_empathy_resonance_network import AgentEmpathyResonanceNetwork
    network = AgentEmpathyResonanceNetwork.get_instance()
    return {"status": "ok", "data": network.reset()}
