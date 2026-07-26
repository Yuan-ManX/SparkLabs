"""
SparkLabs Backend - Cognitive Tide & Chromatic Aurora Routes

REST API endpoints for:
  - AgentCognitiveTideOrchestrator: attention as tidal system
  - EngineChromaticAuroraProjector: atmospheric lighting as aurora phenomena

Routes use /cognitive-tide/ and /chromatic-aurora/ prefixes.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models - Cognitive Tide
# =============================================================================

class RegisterBodyRequest(BaseModel):
    body_id: str
    body_type: str
    label: str
    mass: Optional[float] = None
    orbital_distance: Optional[float] = None
    orbital_angle: Optional[float] = None


class SetBodyMassRequest(BaseModel):
    mass: float


class RegisterTideZoneRequest(BaseModel):
    zone_id: str
    label: str
    baseline_depth: float = 0.5
    tidal_amplitude: float = 0.3


class SimulateTideRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Request Models - Chromatic Aurora
# =============================================================================

class RegisterAuroraZoneRequest(BaseModel):
    zone_id: str
    label: str
    zone_type: str = "twilight"
    excitation: Optional[float] = None
    hue: Optional[float] = None
    saturation: Optional[float] = None
    luminance: Optional[float] = None


class SetExcitationRequest(BaseModel):
    excitation: float
    description: str = ""


class LinkZonesRequest(BaseModel):
    target_id: str
    field_strength: float = 0.5
    polarity: bool = True


class EmitParticleRequest(BaseModel):
    particle_type: str = "photon"
    energy: float = 0.5
    target_zone_id: Optional[str] = None


class SimulateAuroraRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Cognitive Tide Routes
# =============================================================================

@router.get("/cognitive-tide/status")
async def cognitive_tide_status():
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.get_status()}


@router.post("/cognitive-tide/bodies")
async def cognitive_tide_register_body(req: RegisterBodyRequest):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.register_body(
        req.body_id, req.body_type, req.label,
        req.mass, req.orbital_distance, req.orbital_angle,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-tide/bodies/{body_id}")
async def cognitive_tide_get_body(body_id: str):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.get_body(body_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-tide/bodies")
async def cognitive_tide_list_bodies(limit: int = Query(30, ge=1, le=100)):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.list_bodies(limit)}


@router.delete("/cognitive-tide/bodies/{body_id}")
async def cognitive_tide_remove_body(body_id: str):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.remove_body(body_id)
    return {"status": "ok", "data": result}


@router.put("/cognitive-tide/bodies/{body_id}/mass")
async def cognitive_tide_set_body_mass(body_id: str, req: SetBodyMassRequest):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.set_body_mass(body_id, req.mass)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/cognitive-tide/zones")
async def cognitive_tide_register_zone(req: RegisterTideZoneRequest):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.register_zone(
        req.zone_id, req.label, req.baseline_depth, req.tidal_amplitude,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-tide/zones/{zone_id}")
async def cognitive_tide_get_zone(zone_id: str):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.get_zone(zone_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/cognitive-tide/zones")
async def cognitive_tide_list_zones():
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.list_zones()}


@router.delete("/cognitive-tide/zones/{zone_id}")
async def cognitive_tide_remove_zone(zone_id: str):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    result = orchestrator.remove_zone(zone_id)
    return {"status": "ok", "data": result}


@router.post("/cognitive-tide/cycle")
async def cognitive_tide_run_cycle():
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.run_cycle()}


@router.post("/cognitive-tide/simulate")
async def cognitive_tide_simulate(req: SimulateTideRequest):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": orchestrator.simulate(cycles)}


@router.get("/cognitive-tide/events")
async def cognitive_tide_get_events(
    zone_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.get_events(zone_id, limit)}


@router.post("/cognitive-tide/reset")
async def cognitive_tide_reset():
    from sparkai.agent.agent_cognitive_tide_orchestrator import AgentCognitiveTideOrchestrator
    orchestrator = AgentCognitiveTideOrchestrator.get_instance()
    return {"status": "ok", "data": orchestrator.reset()}


# =============================================================================
# Chromatic Aurora Routes
# =============================================================================

@router.get("/chromatic-aurora/status")
async def chromatic_aurora_status():
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.get_status()}


@router.post("/chromatic-aurora/zones")
async def chromatic_aurora_register_zone(req: RegisterAuroraZoneRequest):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.register_zone(
        req.zone_id, req.label, req.zone_type,
        req.excitation, req.hue, req.saturation, req.luminance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chromatic-aurora/zones/{zone_id}")
async def chromatic_aurora_get_zone(zone_id: str):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.get_zone(zone_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chromatic-aurora/zones")
async def chromatic_aurora_list_zones():
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.list_zones()}


@router.delete("/chromatic-aurora/zones/{zone_id}")
async def chromatic_aurora_remove_zone(zone_id: str):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.remove_zone(zone_id)
    return {"status": "ok", "data": result}


@router.put("/chromatic-aurora/zones/{zone_id}/excitation")
async def chromatic_aurora_set_excitation(zone_id: str, req: SetExcitationRequest):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.set_zone_excitation(zone_id, req.excitation, req.description)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chromatic-aurora/zones/{zone_id}/links")
async def chromatic_aurora_link_zones(zone_id: str, req: LinkZonesRequest):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.link_zones(zone_id, req.target_id, req.field_strength, req.polarity)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/chromatic-aurora/zones/{zone_id}/links/{target_id}")
async def chromatic_aurora_unlink_zones(zone_id: str, target_id: str):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.unlink_zones(zone_id, target_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/chromatic-aurora/zones/{zone_id}/links")
async def chromatic_aurora_get_links(zone_id: str):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.get_field_lines(zone_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chromatic-aurora/zones/{zone_id}/particles")
async def chromatic_aurora_emit_particle(zone_id: str, req: EmitParticleRequest):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    result = projector.emit_particle(
        zone_id, req.particle_type, req.energy, req.target_zone_id,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/chromatic-aurora/cycle")
async def chromatic_aurora_run_cycle():
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.run_cycle()}


@router.post("/chromatic-aurora/simulate")
async def chromatic_aurora_simulate(req: SimulateAuroraRequest):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    cycles = max(1, min(100, int(req.cycles)))
    return {"status": "ok", "data": projector.simulate(cycles)}


@router.get("/chromatic-aurora/events")
async def chromatic_aurora_get_events(
    zone_id: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.get_events(zone_id, limit)}


@router.get("/chromatic-aurora/curtains")
async def chromatic_aurora_get_curtains(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.get_curtains(limit)}


@router.post("/chromatic-aurora/reset")
async def chromatic_aurora_reset():
    from sparkai.engine.engine_chromatic_aurora_projector import EngineChromaticAuroraProjector
    projector = EngineChromaticAuroraProjector.get_instance()
    return {"status": "ok", "data": projector.reset()}
