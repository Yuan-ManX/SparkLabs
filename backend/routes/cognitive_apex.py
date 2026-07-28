"""
SparkLabs Backend - Cognitive Apex Synthesizer Routes

REST endpoints for the Agent Cognitive Apex Synthesizer.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterAgentRequest(BaseModel):
    agent_id: str
    bandwidth: float = 1.0


class AddStreamRequest(BaseModel):
    stream_id: str
    stream_type: str  # perception, memory, reasoning, etc.
    layer: str  # BASE, META, META_META, APEX
    label: str
    amplitude: float = 0.5
    frequency: float = 0.3
    phase: float = 0.0
    coherence: float = 0.5
    source_apex: Optional[str] = None


class PulseStreamRequest(BaseModel):
    amplitude: float


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/cognitive-apex/agents")
async def cognitive_apex_register_agent(req: RegisterAgentRequest):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    result = synth.register_agent(req.agent_id, req.bandwidth)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/cognitive-apex/agents/{agent_id}")
async def cognitive_apex_remove_agent(agent_id: str):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    result = synth.remove_agent(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-apex/agents/{agent_id}/streams")
async def cognitive_apex_add_stream(agent_id: str, req: AddStreamRequest):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer, StreamType, StreamLayer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    try:
        stream_type = StreamType(req.stream_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid stream_type: {req.stream_type}"}
    try:
        layer = StreamLayer[req.layer]
    except KeyError:
        return {"status": "error", "detail": f"Invalid layer: {req.layer}"}
    result = synth.add_stream(
        agent_id=agent_id,
        stream_id=req.stream_id,
        stream_type=stream_type,
        layer=layer,
        label=req.label,
        amplitude=req.amplitude,
        frequency=req.frequency,
        phase=req.phase,
        coherence=req.coherence,
        source_apex=req.source_apex,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-apex/agents/{agent_id}/streams/{stream_id}/pulse")
async def cognitive_apex_pulse_stream(agent_id: str, stream_id: str, req: PulseStreamRequest):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    result = synth.pulse_stream(agent_id, stream_id, req.amplitude)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-apex/cycle")
async def cognitive_apex_cycle():
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.cycle()}


@router.post("/cognitive-apex/simulate")
async def cognitive_apex_simulate(req: SimulateRequest):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.simulate(req.cycles)}


@router.get("/cognitive-apex/agents/{agent_id}")
async def cognitive_apex_get_agent(agent_id: str):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    result = synth.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-apex/agents/{agent_id}/patterns")
async def cognitive_apex_get_patterns(agent_id: str, limit: int = 20):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_recent_patterns(agent_id, limit)}


@router.get("/cognitive-apex/events")
async def cognitive_apex_get_events(limit: int = 50):
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_events_log(limit)}


@router.get("/cognitive-apex/status")
async def cognitive_apex_status():
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.get_status()}


@router.post("/cognitive-apex/reset")
async def cognitive_apex_reset():
    from sparkai.agent.agent_cognitive_apex_synthesizer import (
        AgentCognitiveApexSynthesizer,
    )
    synth = AgentCognitiveApexSynthesizer.get_instance()
    return {"status": "ok", "data": synth.reset()}
