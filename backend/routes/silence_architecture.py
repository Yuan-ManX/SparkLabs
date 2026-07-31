"""
SparkLabs Backend - Silence Architecture Composer Routes

REST endpoints for the Engine Silence Architecture Composer.
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
    default_function: str = "structural"  # structural/emotional/rhetorical/regulative/symbolic
    silence_tolerance: float = 0.5        # 0.0-1.0
    flow_pressure: float = 0.5            # 0.0-1.0


class IntroduceSilenceRequest(BaseModel):
    agent_id: str
    silence_id: str
    silence_type: str = "caesura"        # caesura/ellipsis/hesitation/reverence/defiance/grief/anticipation/absence
    function: str = "structural"         # structural/emotional/rhetorical/regulative/symbolic
    duration_ms: int = 500
    intensity: float = 0.5               # 0.0-1.0
    context: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/silence-architecture/agents")
async def silence_register_agent(req: RegisterAgentRequest):
    from sparkai.engine.engine_silence_architecture_composer import (
        EngineSilenceArchitectureComposer, SilenceFunction,
    )
    composer = EngineSilenceArchitectureComposer.get_instance()
    try:
        function = SilenceFunction(req.default_function)
    except ValueError:
        return {"status": "error", "detail": f"Invalid default_function: {req.default_function}"}
    result = composer.register_agent(
        agent_id=req.agent_id,
        default_function=function,
        silence_tolerance=req.silence_tolerance,
        flow_pressure=req.flow_pressure,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/silence-architecture/silences")
async def silence_introduce(req: IntroduceSilenceRequest):
    from sparkai.engine.engine_silence_architecture_composer import (
        EngineSilenceArchitectureComposer, SilenceType, SilenceFunction,
    )
    composer = EngineSilenceArchitectureComposer.get_instance()
    try:
        stype = SilenceType(req.silence_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid silence_type: {req.silence_type}"}
    try:
        function = SilenceFunction(req.function)
    except ValueError:
        return {"status": "error", "detail": f"Invalid function: {req.function}"}
    result = composer.introduce_silence(
        agent_id=req.agent_id,
        silence_id=req.silence_id,
        silence_type=stype,
        function=function,
        duration_ms=req.duration_ms,
        intensity=req.intensity,
        context=req.context,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/silence-architecture/agents/{agent_id}")
async def silence_get_agent_state(agent_id: str):
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    result = composer.get_agent_state(agent_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/silence-architecture/agents/{agent_id}/silences")
async def silence_get_silences(agent_id: str, limit: int = 20):
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    result = composer.get_silences(agent_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/silence-architecture/agents/{agent_id}/silences/{silence_id}")
async def silence_get_silence(agent_id: str, silence_id: str):
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    result = composer.get_silence(agent_id, silence_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/silence-architecture/events")
async def silence_get_events(limit: int = 50):
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit=limit)}


@router.get("/silence-architecture/status")
async def silence_get_status():
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/silence-architecture/cycle")
async def silence_cycle():
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/silence-architecture/simulate")
async def silence_simulate(req: SimulateRequest):
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(cycles=req.cycles)}


@router.post("/silence-architecture/reset")
async def silence_reset():
    from sparkai.engine.engine_silence_architecture_composer import EngineSilenceArchitectureComposer
    composer = EngineSilenceArchitectureComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
