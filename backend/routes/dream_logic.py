"""
SparkLabs Backend - Dream Logic Synthesizer Routes

REST endpoints for the Agent Dream Logic Synthesizer.
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
    lucidity: float = 0.1


class AddMemoryRequest(BaseModel):
    memory_id: str
    label: str
    emotional_charge: float = 0.5
    clarity: float = 0.5


class EnterDreamRequest(BaseModel):
    lens: str = "clarity"   # clarity/fear/desire/nostalgia/guilt/hope/rage/wonder


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/dream-logic/agents")
async def dream_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    result = synth.register_agent(req.agent_id, lucidity=req.lucidity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/dream-logic/agents/{agent_id}")
async def dream_remove_agent(agent_id: str):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    result = synth.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/dream-logic/agents/{agent_id}/memories")
async def dream_add_memory(agent_id: str, req: AddMemoryRequest):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    result = synth.add_memory(
        agent_id=agent_id,
        memory_id=req.memory_id,
        label=req.label,
        emotional_charge=req.emotional_charge,
        clarity=req.clarity,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/dream-logic/agents/{agent_id}/dream")
async def dream_enter(agent_id: str, req: EnterDreamRequest):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    result = synth.enter_dream(agent_id, lens=req.lens)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/dream-logic/agents/{agent_id}")
async def dream_get_agent_state(agent_id: str):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    result = synth.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/dream-logic/agents/{agent_id}/fragments")
async def dream_get_fragments(agent_id: str):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_fragments(agent_id)}


@router.get("/dream-logic/agents/{agent_id}/insights")
async def dream_get_insights(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_insights(agent_id, limit=limit)}


@router.get("/dream-logic/events")
async def dream_get_events(limit: int = 50):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_events_log(limit=limit)}


@router.get("/dream-logic/status")
async def dream_get_status():
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_status()}


@router.post("/dream-logic/cycle")
async def dream_cycle():
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.cycle()}


@router.post("/dream-logic/simulate")
async def dream_simulate(req: SimulateRequest):
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.simulate(cycles=req.cycles)}


@router.post("/dream-logic/reset")
async def dream_reset():
    from sparkai.agent.agent_dream_logic_synthesizer import (
        AgentDreamLogicSynthesizer,
    )
    synth = AgentDreamLogicSynthesizer.get_instance()
    return {"status": "ok", "data": synth.reset()}
