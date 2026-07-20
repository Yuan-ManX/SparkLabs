"""
SparkLabs Backend - Game Creation Orchestrator API Routes

REST API endpoints for the unified game creation pipeline that coordinates
the cognitive architect, AI-native conductor, runtime bridge, and
integration layer to produce playable games from natural-language prompts.

Endpoints:
  GET  /creation-pipeline/status        - Orchestrator status and last run
  POST /creation-pipeline/create        - Create a game from a prompt
  GET  /creation-pipeline/history       - List recent creation runs
  GET  /creation-pipeline/run/{run_id}  - Get a specific run (includes HTML)
  POST /creation-pipeline/reset         - Clear run history
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class CreateGameRequest(BaseModel):
    prompt: str
    genre_hint: Optional[str] = None


@router.get("/creation-pipeline/status")
async def orchestrator_status():
    """Get the orchestrator status and wiring information."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import (
            get_orchestrator,
        )
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        return JSONResponse({"status": "success", "data": orch.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/creation-pipeline/create")
async def orchestrator_create(req: CreateGameRequest):
    """Create a playable game from a natural-language prompt."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import (
            get_orchestrator,
        )
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()

        result = orch.create_game(req.prompt, genre_hint=req.genre_hint)

        # Return metadata without the full HTML to keep the payload small.
        # The HTML can be fetched separately via /run/{run_id}.
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=False),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/creation-pipeline/history")
async def orchestrator_history(limit: int = 16):
    """List recent creation runs (metadata only, no HTML)."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import (
            get_orchestrator,
        )
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        return JSONResponse({
            "status": "success",
            "data": orch.history(limit=limit),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.get("/creation-pipeline/run/{run_id}")
async def orchestrator_get_run(run_id: str):
    """Get a specific run by ID, including the playable HTML."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import (
            get_orchestrator,
        )
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        run = orch.get_run(run_id)
        if run is None:
            return JSONResponse(
                {"status": "error", "message": f"Run {run_id} not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": run})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


@router.post("/creation-pipeline/reset")
async def orchestrator_reset():
    """Clear the orchestrator run history."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import (
            get_orchestrator,
        )
        orch = get_orchestrator()
        orch.reset()
        return JSONResponse({"status": "success", "data": {"cleared": True}})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)}, status_code=500
        )


