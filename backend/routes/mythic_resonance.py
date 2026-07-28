"""
SparkLabs Backend - Mythic Resonance Chamber Routes

REST API endpoints for EngineMythicResonanceChamber: archetypal narrative
pattern resonance with ATTUNE/RESONATE/AMPLIFY/DISSOLVE/CRYSTALLIZE cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterArchetypeRequest(BaseModel):
    archetype_id: str
    label: str
    polarity: str = "neutral"
    domain: str
    frequency: float = 0.5
    description: str = ""


class LinkArchetypesRequest(BaseModel):
    archetype_b: str
    initial_tension: float = 0.0


class FeedEventRequest(BaseModel):
    event_id: str
    event_type: str
    source: str
    intensity: float = 0.5
    target_archetypes: Optional[List[str]] = None
    description: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Archetype Routes
# =============================================================================

@router.get("/mythic-resonance/status")
async def mythic_resonance_status():
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.get_status()}


@router.post("/mythic-resonance/archetypes")
async def mythic_resonance_register_archetype(req: RegisterArchetypeRequest):
    from sparkai.engine.engine_mythic_resonance_chamber import (
        EngineMythicResonanceChamber, ArchetypePolarity,
    )
    chamber = EngineMythicResonanceChamber.get_instance()
    try:
        polarity = ArchetypePolarity(req.polarity)
    except ValueError:
        return {"status": "error", "detail": f"Invalid polarity: {req.polarity}"}
    result = chamber.register_archetype(
        archetype_id=req.archetype_id,
        label=req.label,
        polarity=polarity,
        domain=req.domain,
        frequency=req.frequency,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mythic-resonance/archetypes")
async def mythic_resonance_list_archetypes():
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.list_archetypes()}


@router.get("/mythic-resonance/archetypes/{archetype_id}")
async def mythic_resonance_get_archetype(archetype_id: str):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.get_archetype(archetype_id)
    if result is None:
        return {"status": "error", "detail": f"Archetype not found: {archetype_id}"}
    return {"status": "ok", "data": result}


@router.delete("/mythic-resonance/archetypes/{archetype_id}")
async def mythic_resonance_remove_archetype(archetype_id: str):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.remove_archetype(archetype_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Tension Routes
# =============================================================================

@router.post("/mythic-resonance/archetypes/{archetype_a}/links")
async def mythic_resonance_link_archetypes(archetype_a: str, req: LinkArchetypesRequest):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.link_archetypes(
        archetype_a=archetype_a,
        archetype_b=req.archetype_b,
        initial_tension=req.initial_tension,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.delete("/mythic-resonance/archetypes/{archetype_a}/links/{archetype_b}")
async def mythic_resonance_unlink_archetypes(archetype_a: str, archetype_b: str):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.unlink_archetypes(archetype_a, archetype_b)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mythic-resonance/tensions")
async def mythic_resonance_get_tensions():
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.get_tensions()}


# =============================================================================
# Event Feeding Routes
# =============================================================================

@router.post("/mythic-resonance/events")
async def mythic_resonance_feed_event(req: FeedEventRequest):
    from sparkai.engine.engine_mythic_resonance_chamber import (
        EngineMythicResonanceChamber, MythicEventType,
    )
    chamber = EngineMythicResonanceChamber.get_instance()
    try:
        evt_type = MythicEventType(req.event_type)
    except ValueError:
        return {"status": "error", "detail": f"Invalid event_type: {req.event_type}"}
    result = chamber.feed_event(
        event_id=req.event_id,
        event_type=evt_type,
        source=req.source,
        intensity=req.intensity,
        target_archetypes=req.target_archetypes,
        description=req.description,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Crystallized Moments Routes
# =============================================================================

@router.get("/mythic-resonance/moments")
async def mythic_resonance_get_moments(limit: int = Query(20, ge=1, le=200)):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.get_crystallized_moments(limit)}


@router.post("/mythic-resonance/moments/{moment_id}/consume")
async def mythic_resonance_consume_moment(moment_id: str):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.consume_moment(moment_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/mythic-resonance/cycle")
async def mythic_resonance_cycle():
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.cycle()}


@router.post("/mythic-resonance/simulate")
async def mythic_resonance_simulate(req: SimulateRequest):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    result = chamber.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/mythic-resonance/events")
async def mythic_resonance_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.get_events_log(limit)}


@router.post("/mythic-resonance/reset")
async def mythic_resonance_reset():
    from sparkai.engine.engine_mythic_resonance_chamber import EngineMythicResonanceChamber
    chamber = EngineMythicResonanceChamber.get_instance()
    return {"status": "ok", "data": chamber.reset()}
