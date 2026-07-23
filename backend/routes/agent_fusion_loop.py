"""
SparkLabs Backend - Agent-Engine Fusion Loop API Routes

REST API endpoints for the AgentEngineFusionLoop that tightly couples
the AgentKernel with the AINativeEngineCore in a real-time bidirectional
feedback cycle.

Endpoints:
  GET  /fusion/status       - Fusion loop status and statistics
  POST /fusion/start        - Start the fusion loop
  POST /fusion/stop         - Stop the fusion loop
  POST /fusion/tick         - Run a single fusion tick manually
  GET  /fusion/ticks        - Get recent tick history
  GET  /fusion/goals        - Get active autonomous goals
  GET  /fusion/actions      - Get recent fusion actions
  POST /fusion/reset        - Reset fusion loop state
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/fusion/status")
async def fusion_status():
    """Get the fusion loop status."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        return JSONResponse({"status": "success", "data": loop.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/fusion/start")
async def fusion_start(frequency_hz: float = Query(10.0)):
    """Start the fusion loop at the given frequency."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        loop.start(frequency_hz=frequency_hz)
        return JSONResponse({"status": "success", "data": loop.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/fusion/stop")
async def fusion_stop():
    """Stop the fusion loop."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        loop.stop()
        return JSONResponse({"status": "success", "data": loop.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/fusion/tick")
async def fusion_tick():
    """Run a single fusion tick manually."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        result = loop.tick()
        return JSONResponse({
            "status": "success",
            "data": {
                "tick_id": result.tick_id,
                "cycle_count": result.cycle_count,
                "phase": result.phase.value,
                "fps": result.snapshot.fps if result.snapshot else 0.0,
                "frame_time_ms": result.snapshot.frame_time_ms if result.snapshot else 0.0,
                "entity_count": result.snapshot.entity_count if result.snapshot else 0,
                "anomalies": [a.value for a in result.anomalies_detected],
                "goals": [
                    {
                        "goal_id": g.goal_id,
                        "type": g.goal_type.value,
                        "description": g.description,
                        "priority": round(g.priority, 3),
                        "anomaly": g.anomaly.value,
                        "status": g.status.value,
                    }
                    for g in result.goals_generated
                ],
                "actions": [
                    {
                        "action_id": a.action_id,
                        "command": a.engine_command,
                        "status": a.status.value,
                        "duration_ms": round(a.duration_ms, 2),
                    }
                    for a in result.actions_executed
                ],
                "reasoning_mode": result.reasoning_mode,
                "effectiveness": round(result.effectiveness, 3),
                "duration_s": round(result.duration_s, 4),
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/fusion/ticks")
async def fusion_ticks(limit: int = Query(20, le=200)):
    """Get recent fusion tick history."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        return JSONResponse({"status": "success", "data": loop.get_recent_ticks(limit)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/fusion/goals")
async def fusion_goals():
    """Get currently active autonomous goals."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        return JSONResponse({"status": "success", "data": loop.get_active_goals()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/fusion/actions")
async def fusion_actions(limit: int = Query(20, le=300)):
    """Get recent fusion actions."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        return JSONResponse({"status": "success", "data": loop.get_recent_actions(limit)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/fusion/reset")
async def fusion_reset():
    """Reset the fusion loop state."""
    try:
        from sparkai.agent.agent_engine_fusion_loop import get_fusion_loop
        loop = get_fusion_loop()
        loop.reset()
        return JSONResponse({"status": "success", "data": loop.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
