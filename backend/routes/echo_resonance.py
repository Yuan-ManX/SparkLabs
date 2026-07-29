"""
SparkLabs Backend - Echo Resonance Composer Routes

REST endpoints for the Engine Echo Resonance Composer.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class EmitEchoRequest(BaseModel):
    event_id: str
    label: str
    description: str
    frequency: str = "daily"          # instant/rapid/daily/seasonal/generational/eternal
    valence: str = "tense"            # glorious/tragic/ominous/joyful/wrathful/mournful/mystic/tense
    amplitude: float = 0.7
    x: float = 0.5
    y: float = 0.5
    phase: float = 0.0
    parent_event: Optional[str] = None


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/echo-resonance/echoes")
async def echo_emit(req: EmitEchoRequest):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer, EchoFrequency, EchoValence,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    try:
        frequency = EchoFrequency(req.frequency)
    except ValueError:
        return {"status": "error", "detail": f"Invalid frequency: {req.frequency}"}
    try:
        valence = EchoValence(req.valence)
    except ValueError:
        return {"status": "error", "detail": f"Invalid valence: {req.valence}"}
    result = composer.emit_echo(
        event_id=req.event_id,
        label=req.label,
        description=req.description,
        frequency=frequency,
        valence=valence,
        amplitude=req.amplitude,
        x=req.x,
        y=req.y,
        phase=req.phase,
        parent_event=req.parent_event,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/echo-resonance/echoes")
async def echo_get_all():
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_all_echoes()}


@router.get("/echo-resonance/echoes/{event_id}")
async def echo_get_one(event_id: str):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    result = composer.get_echo(event_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/echo-resonance/standing-waves")
async def echo_get_waves():
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_standing_waves()}


@router.get("/echo-resonance/interferences")
async def echo_get_interferences(limit: int = 50):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_interferences(limit=limit)}


@router.get("/echo-resonance/memory")
async def echo_get_memory(limit: int = 50):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_memory(limit=limit)}


@router.get("/echo-resonance/events")
async def echo_get_events(limit: int = 50):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_events_log(limit=limit)}


@router.get("/echo-resonance/status")
async def echo_get_status():
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.get_status()}


@router.post("/echo-resonance/cycle")
async def echo_cycle():
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.cycle()}


@router.post("/echo-resonance/simulate")
async def echo_simulate(req: SimulateRequest):
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.simulate(cycles=req.cycles)}


@router.post("/echo-resonance/reset")
async def echo_reset():
    from sparkai.engine.engine_echo_resonance_composer import (
        EngineEchoResonanceComposer,
    )
    composer = EngineEchoResonanceComposer.get_instance()
    return {"status": "ok", "data": composer.reset()}
