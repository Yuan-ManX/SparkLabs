"""
SparkLabs Backend - Luminous Narrative Flux Routes

REST API endpoints for EngineLuminousNarrativeFlux: narrative meaning as
luminous flux with EMIT/FLOW/REFRACT/CONVERGE/ILLUMINATE cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class EmitBeatRequest(BaseModel):
    beat_id: str
    label: str
    luminosity: float = 0.5
    chromaticity: str = "white"
    polarization: str = "lateral"
    wavelength: float = 0.5
    source_position: List[float] = [0.0, 0.0, 0.0]
    description: str = ""


class RegisterMediumRequest(BaseModel):
    medium_id: str
    label: str
    medium_type: str
    position: List[float] = [0.0, 0.0, 0.0]
    radius: float = 1.0
    density: float = 0.5
    refraction_index: float = 1.0
    absorption: float = 0.0


class RegisterShadowRequest(BaseModel):
    shadow_id: str
    label: str
    darkness: float = 0.5
    position: List[float] = [0.0, 0.0, 0.0]


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Beat Routes
# =============================================================================

@router.get("/luminous-flux/status")
async def luminous_flux_status():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.get_status()}


@router.post("/luminous-flux/beats")
async def luminous_flux_emit_beat(req: EmitBeatRequest):
    from sparkai.engine.engine_luminous_narrative_flux import (
        EngineLuminousNarrativeFlux, NarrativeChromaticity, BeatPolarization,
    )
    flux = EngineLuminousNarrativeFlux.get_instance()
    try:
        chroma = NarrativeChromaticity(req.chromaticity)
    except ValueError:
        return {"status": "error", "detail": f"Invalid chromaticity: {req.chromaticity}"}
    try:
        polar = BeatPolarization(req.polarization)
    except ValueError:
        return {"status": "error", "detail": f"Invalid polarization: {req.polarization}"}
    pos = tuple(req.source_position) if len(req.source_position) == 3 else (0.0, 0.0, 0.0)
    result = flux.emit_beat(
        beat_id=req.beat_id,
        label=req.label,
        luminosity=req.luminosity,
        chromaticity=chroma,
        polarization=polar,
        wavelength=req.wavelength,
        source_position=pos,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/luminous-flux/beats")
async def luminous_flux_list_beats():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.list_beats()}


# =============================================================================
# Medium Routes
# =============================================================================

@router.post("/luminous-flux/media")
async def luminous_flux_register_medium(req: RegisterMediumRequest):
    from sparkai.engine.engine_luminous_narrative_flux import (
        EngineLuminousNarrativeFlux, MediumType,
    )
    flux = EngineLuminousNarrativeFlux.get_instance()
    try:
        mt = MediumType(req.medium_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid medium_type: {req.medium_type}"}
    pos = tuple(req.position) if len(req.position) == 3 else (0.0, 0.0, 0.0)
    result = flux.register_medium(
        medium_id=req.medium_id,
        label=req.label,
        medium_type=mt,
        position=pos,
        radius=req.radius,
        density=req.density,
        refraction_index=req.refraction_index,
        absorption=req.absorption,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/luminous-flux/media")
async def luminous_flux_list_media():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.list_media()}


# =============================================================================
# Shadow Routes
# =============================================================================

@router.post("/luminous-flux/shadows")
async def luminous_flux_register_shadow(req: RegisterShadowRequest):
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    pos = tuple(req.position) if len(req.position) == 3 else (0.0, 0.0, 0.0)
    result = flux.register_shadow(
        shadow_id=req.shadow_id,
        label=req.label,
        darkness=req.darkness,
        position=pos,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/luminous-flux/shadows")
async def luminous_flux_list_shadows():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.get_shadows()}


@router.post("/luminous-flux/shadows/{shadow_id}/reveal")
async def luminous_flux_reveal_shadow(shadow_id: str):
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    result = flux.reveal_shadow(shadow_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/luminous-flux/patterns")
async def luminous_flux_get_patterns():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.get_patterns()}


@router.get("/luminous-flux/moments")
async def luminous_flux_get_moments(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.get_moments(limit)}


@router.get("/luminous-flux/events")
async def luminous_flux_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/luminous-flux/cycle")
async def luminous_flux_cycle():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.cycle()}


@router.post("/luminous-flux/simulate")
async def luminous_flux_simulate(req: SimulateRequest):
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    result = flux.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/luminous-flux/reset")
async def luminous_flux_reset():
    from sparkai.engine.engine_luminous_narrative_flux import EngineLuminousNarrativeFlux
    flux = EngineLuminousNarrativeFlux.get_instance()
    return {"status": "ok", "data": flux.reset()}
