"""
SparkLabs Backend - Cognitive Simulation API Routes

REST API endpoints for the CognitiveSimulationRunner. The simulation
runner creates a self-playing game where a virtual player navigates a
level while the cognitive engine observes and adapts the game in
real-time. This demonstrates the full AI-native game engine in action.

Endpoints:
  POST /cognitive-simulation/configure - Configure simulation parameters
  POST /cognitive-simulation/start     - Start a new simulation run
  POST /cognitive-simulation/step      - Run one simulation frame
  POST /cognitive-simulation/step-batch - Run N simulation frames
  POST /cognitive-simulation/pause     - Pause the simulation
  POST /cognitive-simulation/resume    - Resume a paused simulation
  POST /cognitive-simulation/stop      - Stop and return final result
  POST /cognitive-simulation/reset     - Reset to idle state
  GET  /cognitive-simulation/status    - Get current simulation status
  GET  /cognitive-simulation/history   - Get recent simulation frames
  GET  /cognitive-simulation/trajectory - Get full player trajectory
  GET  /cognitive-simulation/result    - Get last completed result
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


# =============================================================================
# Request Models
# =============================================================================

class ConfigureRequest(BaseModel):
    strategy: str = "speedrun"  # speedrun, cautious, explorer, aggressive, random
    max_ticks: int = 600
    goal_x: float = 1500.0


class StepBatchRequest(BaseModel):
    count: int = 60


# =============================================================================
# Endpoints
# =============================================================================

@router.post("/cognitive-simulation/configure")
async def configure_simulation(req: ConfigureRequest):
    """Configure simulation parameters before starting."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        runner.configure(
            strategy=req.strategy,
            max_ticks=req.max_ticks,
            goal_x=req.goal_x,
        )
        return JSONResponse({
            "status": "success",
            "data": {
                "strategy": req.strategy,
                "max_ticks": req.max_ticks,
                "goal_x": req.goal_x,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/start")
async def start_simulation():
    """Start a new simulation run."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.start()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/step")
async def step_simulation():
    """Run one simulation frame."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.step()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/step-batch")
async def step_batch_simulation(req: StepBatchRequest):
    """Run multiple simulation frames."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.step_batch(req.count)
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/pause")
async def pause_simulation():
    """Pause the simulation."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.pause()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/resume")
async def resume_simulation():
    """Resume a paused simulation."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.resume()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/stop")
async def stop_simulation():
    """Stop the simulation and return the final result."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.stop()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/cognitive-simulation/reset")
async def reset_simulation():
    """Reset the simulation to idle state."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.reset()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-simulation/status")
async def simulation_status():
    """Get the current simulation status."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.status()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-simulation/history")
async def simulation_history(limit: int = 60):
    """Get recent simulation frames."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.history(limit)
        return JSONResponse({
            "status": "success",
            "data": {"frames": result, "count": len(result)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-simulation/trajectory")
async def simulation_trajectory():
    """Get the full player trajectory."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.trajectory()
        return JSONResponse({
            "status": "success",
            "data": {"trajectory": result, "count": len(result)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/cognitive-simulation/result")
async def simulation_result():
    """Get the last completed simulation result."""
    try:
        from sparkai.engine.engine_cognitive_simulation_runner import (
            get_simulation_runner,
        )
        runner = get_simulation_runner()
        result = runner.last_result()
        if result is None:
            return JSONResponse({
                "status": "success",
                "data": None,
                "message": "No completed simulation result yet.",
            })
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )
