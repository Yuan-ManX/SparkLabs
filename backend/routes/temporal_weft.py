"""
SparkLabs Backend - Temporal Weft Loom Routes

REST API endpoints for EngineTemporalWeftLoom: time as woven fabric with
WARP/WEFT/TENSION/DARN/UNRAVEL cycle.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class SpawnThreadRequest(BaseModel):
    thread_id: str
    label: str
    region: str
    direction: str = "forward"
    flow_rate: float = 1.0


class WeaveWeftRequest(BaseModel):
    thread_a: str
    thread_b: str
    alignment: float = 0.5
    strength: float = 0.3
    bidirectional: bool = True


class RecordMomentRequest(BaseModel):
    moment_id: str
    thread_id: str
    label: str
    importance: float = 0.5


class SimulateRequest(BaseModel):
    cycles: int = 10


# =============================================================================
# Thread Routes
# =============================================================================

@router.get("/temporal-weft/status")
async def temporal_weft_status():
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.get_status()}


@router.post("/temporal-weft/threads")
async def temporal_weft_spawn_thread(req: SpawnThreadRequest):
    from sparkai.engine.engine_temporal_weft_loom import (
        EngineTemporalWeftLoom, ThreadDirection,
    )
    loom = EngineTemporalWeftLoom.get_instance()
    try:
        direction = ThreadDirection(req.direction)
    except ValueError:
        return {"status": "error", "detail": f"Invalid direction: {req.direction}"}
    result = loom.spawn_thread(
        thread_id=req.thread_id,
        label=req.label,
        region=req.region,
        direction=direction,
        flow_rate=req.flow_rate,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-weft/threads")
async def temporal_weft_list_threads():
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.list_threads()}


@router.get("/temporal-weft/threads/{thread_id}")
async def temporal_weft_get_thread(thread_id: str):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    result = loom.get_thread(thread_id)
    if result is None:
        return {"status": "error", "detail": f"Thread not found: {thread_id}"}
    return {"status": "ok", "data": result}


@router.delete("/temporal-weft/threads/{thread_id}")
async def temporal_weft_remove_thread(thread_id: str):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    result = loom.remove_thread(thread_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


# =============================================================================
# Weft Routes
# =============================================================================

@router.post("/temporal-weft/wefts")
async def temporal_weft_weave(req: WeaveWeftRequest):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    result = loom.weave_weft(
        thread_a=req.thread_a,
        thread_b=req.thread_b,
        alignment=req.alignment,
        strength=req.strength,
        bidirectional=req.bidirectional,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-weft/wefts")
async def temporal_weft_list_wefts():
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.list_wefts()}


# =============================================================================
# Moment Routes
# =============================================================================

@router.post("/temporal-weft/moments")
async def temporal_weft_record_moment(req: RecordMomentRequest):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    result = loom.record_moment(
        moment_id=req.moment_id,
        thread_id=req.thread_id,
        label=req.label,
        importance=req.importance,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/temporal-weft/moments")
async def temporal_weft_get_moments(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.get_moments(limit)}


# =============================================================================
# Query Routes
# =============================================================================

@router.get("/temporal-weft/tangles")
async def temporal_weft_get_tangles(limit: int = Query(20, ge=1, le=100)):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.get_tangles(limit)}


@router.get("/temporal-weft/events")
async def temporal_weft_events(limit: int = Query(50, ge=1, le=200)):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.get_events_log(limit)}


# =============================================================================
# Cycle Routes
# =============================================================================

@router.post("/temporal-weft/cycle")
async def temporal_weft_cycle():
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.cycle()}


@router.post("/temporal-weft/simulate")
async def temporal_weft_simulate(req: SimulateRequest):
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    result = loom.simulate(req.cycles)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/temporal-weft/reset")
async def temporal_weft_reset():
    from sparkai.engine.engine_temporal_weft_loom import EngineTemporalWeftLoom
    loom = EngineTemporalWeftLoom.get_instance()
    return {"status": "ok", "data": loom.reset()}
