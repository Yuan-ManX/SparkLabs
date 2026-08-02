"""
SparkLabs Backend - Causal Timeline Weaver Routes

REST endpoints for the Engine Causal Timeline Weaver.
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, List

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class RecordEventRequest(BaseModel):
    event_id: str
    kind: str = "occurrence"            # action/decision/occurrence/reaction/turning_point/catalyst
    description: str = ""
    cause_ids: List[str] = []
    region: str = ""
    link_strengths: Dict[str, str] = {}  # cause_id -> strength label
    note: str = ""


class SimulateRequest(BaseModel):
    cycles: int = 5


# =============================================================================
# Routes
# =============================================================================

@router.post("/causal-timeline-weaver/events")
async def weaver_record_event(req: RecordEventRequest):
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    result = weaver.record_event(
        event_id=req.event_id,
        kind=req.kind,
        description=req.description,
        cause_ids=req.cause_ids,
        region=req.region,
        link_strengths=req.link_strengths,
        note=req.note,
    )
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.post("/causal-timeline-weaver/cycle")
async def weaver_cycle():
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.cycle()}


@router.get("/causal-timeline-weaver/events/{event_id}")
async def weaver_get_event(event_id: str):
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    result = weaver.get_event(event_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-timeline-weaver/threads/{thread_id}")
async def weaver_get_thread(thread_id: str):
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    result = weaver.get_thread(thread_id)
    if "error" in result:
        return {"status": "error", "detail": result["error"]}
    return {"status": "ok", "data": result}


@router.get("/causal-timeline-weaver/causal-map")
async def weaver_get_causal_map():
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_causal_map()}


@router.get("/causal-timeline-weaver/status")
async def weaver_get_status():
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_status()}


@router.get("/causal-timeline-weaver/events")
async def weaver_get_events(limit: int = 50):
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.get_events_log(limit=limit)}


@router.post("/causal-timeline-weaver/simulate")
async def weaver_simulate(req: SimulateRequest):
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.simulate(cycles=req.cycles)}


@router.post("/causal-timeline-weaver/reset")
async def weaver_reset():
    from sparkai.engine.engine_causal_timeline_weaver import (
        EngineCausalTimelineWeaver,
    )
    weaver = EngineCausalTimelineWeaver.get_instance()
    return {"status": "ok", "data": weaver.reset()}
