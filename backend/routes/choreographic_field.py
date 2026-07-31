"""
SparkLabs Backend - Choreographic Field Weaver Routes

REST endpoints for the Engine Choreographic Field Weaver.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RegisterFieldRequest(BaseModel):
    field_id: str


class AddEntityRequest(BaseModel):
    field_id: str
    entity_id: str
    quality: str = "flowing"            # flowing/staccato/suspended/percussive/vibratory


class CoupleRequest(BaseModel):
    field_id: str
    bond_id: str
    line_a_id: str
    line_b_id: str
    relation: str = "mirror"            # lead_follow/mirror/counterpoint/unison
    strength: float = 0.5               # 0.0-1.0


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/choreographic-field/fields")
async def choreographic_register_field(req: RegisterFieldRequest):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    result = weaver.register_field(field_id=req.field_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/choreographic-field/fields/{field_id}/entities")
async def choreographic_add_entity(field_id: str, req: AddEntityRequest):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver, MovementQuality,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    # The route path carries field_id; the body may also carry it for symmetry.
    # Prefer the path parameter when they disagree.
    target_field = field_id or req.field_id
    try:
        quality = MovementQuality(req.quality)
    except ValueError:
        return {"status": "error", "detail": f"Invalid quality: {req.quality}"}
    result = weaver.add_entity(
        field_id=target_field,
        entity_id=req.entity_id,
        quality=quality,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/choreographic-field/fields/{field_id}/bonds")
async def choreographic_couple(field_id: str, req: CoupleRequest):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver, CoupleRelation,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    target_field = field_id or req.field_id
    try:
        relation = CoupleRelation(req.relation)
    except ValueError:
        return {"status": "error", "detail": f"Invalid relation: {req.relation}"}
    result = weaver.couple(
        field_id=target_field,
        bond_id=req.bond_id,
        line_a_id=req.line_a_id,
        line_b_id=req.line_b_id,
        relation=relation,
        strength=req.strength,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/choreographic-field/fields/{field_id}")
async def choreographic_get_field_state(field_id: str):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    result = weaver.get_field_state(field_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/choreographic-field/fields/{field_id}/lines")
async def choreographic_get_lines(field_id: str, limit: int = 20):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    result = weaver.get_lines(field_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/choreographic-field/fields/{field_id}/bonds")
async def choreographic_get_bonds(field_id: str, limit: int = 20):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    result = weaver.get_bonds(field_id, limit=limit)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/choreographic-field/fields/{field_id}/coherence")
async def choreographic_get_field_coherence(field_id: str):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    result = weaver.get_field_coherence(field_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/choreographic-field/events")
async def choreographic_get_events(limit: int = 50):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit=limit)}


@router.get("/choreographic-field/status")
async def choreographic_get_status():
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.post("/choreographic-field/cycle")
async def choreographic_cycle():
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.post("/choreographic-field/simulate")
async def choreographic_simulate(req: SimulateRequest):
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(cycles=req.cycles)}


@router.post("/choreographic-field/reset")
async def choreographic_reset():
    from sparkai.engine.engine_choreographic_field_weaver import (
        EngineChoreographicFieldWeaver,
    )
    weaver = EngineChoreographicFieldWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
