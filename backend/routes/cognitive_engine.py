"""
SparkLabs Backend - Cognitive Game Engine API Routes

REST API endpoints for the unified cognitive game engine where agent
cognition and engine execution share a single tick. Each call to
/tick runs perceive -> reason -> plan -> act -> reflect -> learn.

Endpoints:
  GET  /cognitive-engine/status    - Engine status and last tick summary
  POST /cognitive-engine/tick      - Run one cognitive tick
  POST /cognitive-engine/tick-batch - Run N cognitive ticks in sequence
  POST /cognitive-engine/start     - Start the engine (initializes if cold)
  POST /cognitive-engine/pause     - Pause the engine
  POST /cognitive-engine/resume    - Resume a paused engine
  POST /cognitive-engine/reset     - Reset the engine to cold state
  GET  /cognitive-engine/history   - List recent tick results
  GET  /cognitive-engine/memory    - Query the memory bank
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class TickBatchRequest(BaseModel):
    count: int = 10
    dt: float = 1.0 / 60.0


class MemoryQueryRequest(BaseModel):
    tier: Optional[str] = None
    domain: Optional[str] = None
    limit: int = 8


def _get_engine():
    from sparkai.engine.engine_cognitive_game_engine import get_cognitive_engine
    return get_cognitive_engine()


@router.get("/cognitive-engine/status")
async def cognitive_engine_status():
    """Get the cognitive engine status, including subsystem telemetry."""
    try:
        engine = _get_engine()
        return JSONResponse({"status": "success", "data": engine.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/tick")
async def cognitive_engine_tick():
    """Run a single cognitive tick (perceive -> reason -> plan -> act -> reflect -> learn)."""
    try:
        engine = _get_engine()
        if engine._state.value == "cold":
            engine.initialize()
        result = engine.cognitive_tick()
        return JSONResponse({
            "status": "success",
            "data": {
                "tick": result.tick,
                "phase": result.phase.value,
                "actions_planned": [
                    {
                        "action_id": a.action_id,
                        "action_type": a.action_type.value,
                        "target_id": a.target_id,
                        "params": a.params,
                        "expected_outcome": a.expected_outcome,
                        "confidence": a.confidence,
                        "rationale": a.rationale,
                    } for a in result.actions_planned
                ],
                "actions_executed": result.actions_executed,
                "outcome": {
                    "action_id": result.outcome.action_id,
                    "success": result.outcome.success,
                    "observed_delta": result.outcome.observed_delta,
                    "notes": result.outcome.notes,
                } if result.outcome else None,
                "lesson": result.lesson,
                "duration_s": result.duration_s,
                "confidence": result.confidence,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/tick-batch")
async def cognitive_engine_tick_batch(req: TickBatchRequest):
    """Run N cognitive ticks in sequence and return the final status."""
    try:
        engine = _get_engine()
        if engine._state.value == "cold":
            engine.initialize()
        count = max(1, min(req.count, 200))  # bound to 200 max
        last_result = None
        for _ in range(count):
            last_result = engine.cognitive_tick(req.dt)
        return JSONResponse({
            "status": "success",
            "data": {
                "ticks_run": count,
                "last_tick": {
                    "tick": last_result.tick,
                    "actions_executed": last_result.actions_executed,
                    "confidence": last_result.confidence,
                    "duration_s": last_result.duration_s,
                    "lesson": last_result.lesson,
                } if last_result else None,
                "engine_status": engine.status(),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/start")
async def cognitive_engine_start():
    """Start the cognitive engine (initializes if cold)."""
    try:
        engine = _get_engine()
        engine.start()
        return JSONResponse({
            "status": "success",
            "data": {"state": engine._state.value, "tick": engine._tick},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/pause")
async def cognitive_engine_pause():
    """Pause the cognitive engine."""
    try:
        engine = _get_engine()
        engine.pause()
        return JSONResponse({
            "status": "success",
            "data": {"state": engine._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/resume")
async def cognitive_engine_resume():
    """Resume a paused cognitive engine."""
    try:
        engine = _get_engine()
        engine.resume()
        return JSONResponse({
            "status": "success",
            "data": {"state": engine._state.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/reset")
async def cognitive_engine_reset():
    """Reset the cognitive engine to cold state."""
    try:
        engine = _get_engine()
        engine.reset()
        return JSONResponse({"status": "success", "data": {"state": engine._state.value}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-engine/history")
async def cognitive_engine_history(limit: int = 10):
    """List recent cognitive tick results."""
    try:
        engine = _get_engine()
        return JSONResponse({
            "status": "success",
            "data": engine.history(limit=min(max(1, limit), 64)),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-engine/memory")
async def cognitive_engine_memory_query(req: MemoryQueryRequest):
    """Query the unified memory bank by tier and/or domain."""
    try:
        from sparkai.engine.engine_cognitive_game_engine import MemoryTier
        engine = _get_engine()
        tier = None
        if req.tier:
            try:
                tier = MemoryTier(req.tier)
            except ValueError:
                return JSONResponse(
                    {"status": "error",
                     "message": f"Invalid tier: {req.tier}. Must be one of: {[t.value for t in MemoryTier]}"},
                    status_code=400,
                )
        records = engine._memory.query(tier=tier, domain=req.domain, limit=req.limit)
        return JSONResponse({
            "status": "success",
            "data": [
                {
                    "record_id": r.record_id,
                    "tier": r.tier.value,
                    "domain": r.domain,
                    "content": r.content,
                    "salience": r.salience,
                    "confidence": r.confidence,
                    "access_count": r.access_count,
                    "created_at": r.created_at,
                } for r in records
            ],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )
