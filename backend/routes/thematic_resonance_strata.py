"""
SparkLabs Backend - Thematic Resonance Strata Routes

REST endpoints for the Engine Thematic Resonance Strata field.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterThemeRequest(BaseModel):
    theme_id: str
    note: str = ""


class SetPresenceRequest(BaseModel):
    surface: float = 0.0                  # 0.0-1.0, literal stated presence
    mid: float = 0.0                      # 0.0-1.0, recurring motif presence
    deep: float = 0.0                     # 0.0-1.0, archetypal presence
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/thematic-resonance-strata/themes")
async def resonance_register_theme(req: RegisterThemeRequest):
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    result = engine.register_theme(theme_id=req.theme_id, note=req.note)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/thematic-resonance-strata/themes/{theme_id}/presence")
async def resonance_set_presence(theme_id: str, req: SetPresenceRequest):
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    result = engine.set_theme_presence(
        theme_id=theme_id,
        surface=req.surface,
        mid=req.mid,
        deep=req.deep,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/thematic-resonance-strata/cycle")
async def resonance_cycle():
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.cycle()}


@router.get("/thematic-resonance-strata/themes/{theme_id}/resonance")
async def resonance_get_reading(theme_id: str):
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    result = engine.get_resonance(theme_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/thematic-resonance-strata/status")
async def resonance_get_status():
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.get_status()}


@router.get("/thematic-resonance-strata/themes")
async def resonance_get_themes():
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.get_themes()}


@router.get("/thematic-resonance-strata/events")
async def resonance_get_events(limit: int = 50):
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.get_events_log(limit=limit)}


@router.post("/thematic-resonance-strata/simulate")
async def resonance_simulate(req: SimulateRequest):
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.simulate(cycles=req.cycles)}


@router.post("/thematic-resonance-strata/reset")
async def resonance_reset():
    from sparkai.engine.engine_thematic_resonance_strata import (
        EngineThematicResonanceStrata,
    )
    engine = EngineThematicResonanceStrata.get_instance()
    return {"status": "ok", "data": engine.reset()}
