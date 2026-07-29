"""
SparkLabs Backend - Phase Harmonics Director Routes

REST endpoints for the Engine Phase Harmonics Director.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class TunePhaseRequest(BaseModel):
    frequency: float = 0.5
    amplitude: float = 0.5
    phase: Optional[float] = None


class ModulateRequest(BaseModel):
    freq_shift: float = 0.0
    amp_shift: float = 0.0
    source: str = ""
    duration: int = 3


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/phase-harmonics/phases/{dimension}/tune")
async def harmonics_tune_phase(dimension: str, req: TunePhaseRequest):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector, PhaseDimension,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    try:
        dim = PhaseDimension(dimension)
    except ValueError:
        return {"status": "error", "detail": f"Invalid dimension: {dimension}"}
    result = director.tune_phase(
        dimension=dim,
        frequency=req.frequency,
        amplitude=req.amplitude,
        phase=req.phase,
    )
    return {"status": "ok", "data": result}


@router.post("/phase-harmonics/phases/{dimension}/modulate")
async def harmonics_modulate(dimension: str, req: ModulateRequest):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector, PhaseDimension,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    try:
        dim = PhaseDimension(dimension)
    except ValueError:
        return {"status": "error", "detail": f"Invalid dimension: {dimension}"}
    result = director.modulate(
        dimension=dim,
        freq_shift=req.freq_shift,
        amp_shift=req.amp_shift,
        source=req.source,
        duration=req.duration,
    )
    return {"status": "ok", "data": result}


@router.get("/phase-harmonics/phases")
async def harmonics_get_all_phases():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_phase_state()}


@router.get("/phase-harmonics/phases/{dimension}")
async def harmonics_get_phase(dimension: str):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector, PhaseDimension,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    try:
        dim = PhaseDimension(dimension)
    except ValueError:
        return {"status": "error", "detail": f"Invalid dimension: {dimension}"}
    return {"status": "ok", "data": director.get_phase_state(dim)}


@router.get("/phase-harmonics/chord")
async def harmonics_get_active_chord():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_active_chord()}


@router.get("/phase-harmonics/chords")
async def harmonics_get_all_chords():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_all_chords()}


@router.get("/phase-harmonics/relations")
async def harmonics_get_relations(limit: int = 30):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_relations(limit=limit)}


@router.get("/phase-harmonics/events")
async def harmonics_get_events(limit: int = 50):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_events_log(limit=limit)}


@router.get("/phase-harmonics/status")
async def harmonics_get_status():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.get_status()}


@router.post("/phase-harmonics/cycle")
async def harmonics_cycle():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.cycle()}


@router.post("/phase-harmonics/simulate")
async def harmonics_simulate(req: SimulateRequest):
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.simulate(cycles=req.cycles)}


@router.post("/phase-harmonics/reset")
async def harmonics_reset():
    from sparkai.engine.engine_phase_harmonics_director import (
        EnginePhaseHarmonicsDirector,
    )
    director = EnginePhaseHarmonicsDirector.get_instance()
    return {"status": "ok", "data": director.reset()}
