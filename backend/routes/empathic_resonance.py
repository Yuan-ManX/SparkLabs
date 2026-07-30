"""
SparkLabs Backend - Empathic Resonance Weaver Routes

REST endpoints for the Agent Empathic Resonance Weaver.
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
    empathy_capacity: float = 0.5
    emotional_intelligence: float = 0.3


class SetEmotionRequest(BaseModel):
    frequency: str = "joy"          # joy/grief/anger/fear/surprise/disgust/trust/anticipation/serenity/melancholy/zeal/dread
    intensity: float = 0.5


class FormBondRequest(BaseModel):
    agent_a: str
    agent_b: str


class ExperienceTogetherRequest(BaseModel):
    agent_a: str
    agent_b: str
    context_label: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/empathic-resonance/agents")
async def weaver_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.register_agent(
        agent_id=req.agent_id,
        empathy_capacity=req.empathy_capacity,
        emotional_intelligence=req.emotional_intelligence,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/empathic-resonance/agents/{agent_id}")
async def weaver_remove_agent(agent_id: str):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/empathic-resonance/agents/{agent_id}/emotion")
async def weaver_set_emotion(agent_id: str, req: SetEmotionRequest):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver, EmotionalFrequency,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    try:
        freq = EmotionalFrequency(req.frequency)
    except ValueError:
        return {"status": "error", "detail": f"Invalid frequency: {req.frequency}"}
    result = weaver.set_emotion(
        agent_id=agent_id,
        frequency=freq,
        intensity=req.intensity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/empathic-resonance/bonds")
async def weaver_form_bond(req: FormBondRequest):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.form_bond(req.agent_a, req.agent_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/empathic-resonance/experience")
async def weaver_experience_together(req: ExperienceTogetherRequest):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.experience_together(
        agent_a=req.agent_a,
        agent_b=req.agent_b,
        context_label=req.context_label,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathic-resonance/agents/{agent_id}")
async def weaver_get_agent_state(agent_id: str):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathic-resonance/bonds")
async def weaver_get_all_bonds():
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_all_bonds()}


@router.get("/empathic-resonance/bonds/{bond_id}")
async def weaver_get_bond(bond_id: str):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    result = weaver.get_bond(bond_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/empathic-resonance/agents/{agent_id}/reflections")
async def weaver_get_reflections(agent_id: str, limit: int = 10):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_reflections(agent_id, limit=limit)}


@router.get("/empathic-resonance/events")
async def weaver_get_events(limit: int = 50):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit=limit)}


@router.get("/empathic-resonance/status")
async def weaver_get_status():
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/empathic-resonance/cycle")
async def weaver_cycle():
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.post("/empathic-resonance/simulate")
async def weaver_simulate(req: SimulateRequest):
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(cycles=req.cycles)}


@router.post("/empathic-resonance/reset")
async def weaver_reset():
    from sparkai.agent.agent_empathic_resonance_weaver import (
        AgentEmpathicResonanceWeaver,
    )
    weaver = AgentEmpathicResonanceWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
