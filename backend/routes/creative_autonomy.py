"""
SparkLabs Backend - Creative Autonomy API Routes

REST API endpoints for the CreativeAutonomyDirector that generates
proactive creative goals during live gameplay.

Endpoints:
  GET  /creative/status           - Director status and statistics
  POST /creative/snapshot          - Record a gameplay snapshot
  POST /creative/check             - Check for patterns and generate goals
  GET  /creative/goals             - Get active creative goals
  GET  /creative/goals/completed   - Get completed creative goals
  GET  /creative/steps/pending     - Get pending intervention steps
  POST /creative/steps/execute     - Mark a step as executed
  POST /creative/evaluate          - Evaluate a completed goal
  POST /creative/reset             - Reset the director state
  POST /creative/simulate          - Run a full simulation cycle
"""

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

router = APIRouter()


class SnapshotRequest(BaseModel):
    engagement: float = 0.5
    difficulty: float = 0.5
    variety: float = 0.5
    exploration: float = 0.0
    events: List[str] = []
    session_id: str = ""


class StepExecuteRequest(BaseModel):
    goal_id: str
    step_id: str
    result: Dict[str, Any] = {}


class EvaluateRequest(BaseModel):
    goal_id: str
    impact: Dict[str, float] = {}


class SimulateRequest(BaseModel):
    snapshots: int = 15
    session_id: str = "sim"


@router.get("/creative/status")
async def creative_status():
    """Get the creative autonomy director status."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        return JSONResponse({"status": "success", "data": director.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/snapshot")
async def creative_snapshot(req: SnapshotRequest):
    """Record a gameplay snapshot for pattern detection."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        director.record_gameplay_snapshot(
            engagement=req.engagement,
            difficulty=req.difficulty,
            variety=req.variety,
            exploration=req.exploration,
            events=req.events,
            session_id=req.session_id,
        )
        return JSONResponse({"status": "success", "data": {"snapshot_count": director.status()["snapshot_count"]}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/check")
async def creative_check():
    """Check for patterns and generate creative goals."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        new_goals = director.check_and_generate()
        return JSONResponse({
            "status": "success",
            "data": {
                "new_goals_count": len(new_goals),
                "new_goals": [
                    {
                        "goal_id": g.goal_id,
                        "goal_type": g.goal_type.value,
                        "trigger_pattern": g.trigger_pattern.value,
                        "description": g.description,
                        "priority": round(g.priority, 3),
                        "status": g.status.value,
                        "predicted_impact": g.predicted_impact,
                        "steps_count": len(g.intervention_steps),
                    }
                    for g in new_goals
                ],
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/creative/goals")
async def creative_goals():
    """Get currently active creative goals."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        return JSONResponse({"status": "success", "data": director.get_active_goals()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/creative/goals/completed")
async def creative_goals_completed(limit: int = Query(20, le=50)):
    """Get recently completed creative goals."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        return JSONResponse({"status": "success", "data": director.get_completed_goals(limit)})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/creative/steps/pending")
async def creative_steps_pending():
    """Get pending intervention steps ready for execution."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        pending = director.get_pending_steps()
        return JSONResponse({
            "status": "success",
            "data": [
                {
                    "goal_id": goal_id,
                    "step_id": step.step_id,
                    "phase": step.phase.value,
                    "action_type": step.action_type,
                    "params": step.params,
                    "delay_s": step.delay_s,
                }
                for goal_id, step in pending
            ]
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/steps/execute")
async def creative_steps_execute(req: StepExecuteRequest):
    """Mark an intervention step as executed."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        director.mark_step_executed(req.goal_id, req.step_id, req.result)
        return JSONResponse({"status": "success", "data": {"executed": True}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/evaluate")
async def creative_evaluate(req: EvaluateRequest):
    """Evaluate the outcome of a completed creative goal."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        director.evaluate_goal(req.goal_id, req.impact)
        return JSONResponse({"status": "success", "data": {"evaluated": True}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/reset")
async def creative_reset():
    """Reset the creative autonomy director state."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        director = get_creative_director()
        director.reset()
        return JSONResponse({"status": "success", "data": director.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/creative/simulate")
async def creative_simulate(req: SimulateRequest):
    """Run a full simulation cycle: record snapshots, detect patterns, generate goals."""
    try:
        from sparkai.agent.agent_creative_autonomy import get_creative_director
        import random as _r
        import time as _time

        director = get_creative_director()
        director.reset()

        # Simulate declining engagement and flat difficulty
        all_generated_goals = []
        for i in range(req.snapshots):
            # Simulate declining engagement after the first few snapshots
            if i < 3:
                engagement = 0.7
                difficulty = 0.5
            elif i < 8:
                engagement = max(0.3, 0.7 - (i - 3) * 0.08)
                difficulty = 0.5  # Flat
            else:
                engagement = 0.3
                difficulty = 0.52  # Still mostly flat

            variety = max(0.1, 0.8 - i * 0.05)
            exploration = 100 + i * 5
            events = ["jump", "move"] if i % 2 == 0 else ["jump"]  # Repetitive

            director.record_gameplay_snapshot(
                engagement=engagement,
                difficulty=difficulty,
                variety=variety,
                exploration=exploration,
                events=events,
                session_id=req.session_id,
            )

            # Check for patterns every few snapshots
            if i >= 5:
                new_goals = director.check_and_generate()
                if new_goals:
                    all_generated_goals.extend(new_goals)

                # Execute pending steps
                pending = director.get_pending_steps()
                for goal_id, step in pending:
                    director.mark_step_executed(goal_id, step.step_id, {"simulated": True})

            _time.sleep(0.01)  # Small delay for time-based logic

        # Evaluate any completed goals
        active = director.get_active_goals()
        for goal in active:
            if goal["status"] == "evaluating":
                director.evaluate_goal(goal["goal_id"], {
                    "engagement_delta": 0.15,
                    "variety_delta": 0.2,
                    "difficulty_delta": 0.1,
                })

        status = director.status()
        return JSONResponse({
            "status": "success",
            "data": {
                "snapshots_recorded": req.snapshots,
                "goals_generated": len(all_generated_goals),
                "status": status,
                "generated_goals": [
                    {
                        "goal_type": g.goal_type.value,
                        "trigger_pattern": g.trigger_pattern.value,
                        "description": g.description,
                        "priority": round(g.priority, 3),
                        "steps_count": len(g.intervention_steps),
                    }
                    for g in all_generated_goals
                ],
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
