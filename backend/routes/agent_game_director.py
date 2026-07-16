"""
SparkLabs Backend - Agent Game Director API Routes

REST API endpoints for the AI Game Director system.
The director orchestrates synthesis, runtime building, playtest simulation,
quality evaluation, and iterative refinement into a single creation pipeline.

Endpoints:
  GET  /game-director/status        - Pipeline status and recent sessions
  GET  /game-director/capabilities  - Supported genres, quality dimensions, tools
  POST /game-director/direct        - Run the full director pipeline on a prompt
  GET  /game-director/history       - List recent director sessions
  GET  /game-director/result/{sid}  - Retrieve a cached director result
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# In-memory result cache for retrieval by session_id
_result_cache: dict = {}


@router.get("/game-director/status")
async def game_director_status():
    """Get the Game Director system status."""
    try:
        from sparkai.agent.agent_game_director import get_game_director
        director = get_game_director()
        if not director._initialized:
            director.initialize()
        return JSONResponse({"status": "success", "data": director.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-director/capabilities")
async def game_director_capabilities():
    """List director capabilities: genres, quality dimensions, tools."""
    try:
        from sparkai.agent.agent_game_director import (
            QualityDimension, RefinementAction, ToolRegistry,
        )
        from sparkai.agent.agent_game_content_synthesizer import GameGenre

        genres = [{"value": g.value, "name": g.value.replace("_", " ").title()} for g in GameGenre]
        tools = ToolRegistry()

        return JSONResponse({
            "status": "success",
            "data": {
                "genres": genres,
                "quality_dimensions": [d.value for d in QualityDimension],
                "refinement_actions": [a.value for a in RefinementAction],
                "tools": tools.list_tools(),
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-director/direct")
async def game_director_direct(request: Request):
    """Run the full director pipeline: synthesize, build, simulate, evaluate, refine.

    Body:
      prompt: str          - Natural-language game description
      genre_hint: str      - Optional genre hint
      max_iterations: int  - Override max refinement iterations (default 3)
      return_html: bool    - Include HTML in response (default true)
    """
    try:
        from sparkai.agent.agent_game_director import get_game_director
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        genre_hint = body.get("genre_hint")
        max_iterations = body.get("max_iterations")
        return_html = body.get("return_html", True)

        if not prompt:
            return JSONResponse(
                {"status": "error", "message": "prompt is required"},
                status_code=400,
            )

        director = get_game_director()
        if not director._initialized:
            director.initialize()

        result = director.direct(
            prompt=prompt,
            genre_hint=genre_hint,
            max_iterations=max_iterations,
        )

        # Cache the result (always include HTML in cache)
        data = result.to_dict(include_html=True)
        _result_cache[result.session_id] = data

        # Optionally strip HTML to reduce payload
        if not return_html:
            data = dict(data)
            data["html"] = ""

        return JSONResponse({"status": "success", "data": data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-director/history")
async def game_director_history():
    """List recent director sessions."""
    try:
        from sparkai.agent.agent_game_director import get_game_director
        director = get_game_director()
        if not director._initialized:
            director.initialize()
        return JSONResponse({"status": "success", "data": director.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-director/result/{session_id}")
async def game_director_get_result(session_id: str):
    """Retrieve a cached director result by session_id."""
    try:
        result = _result_cache.get(session_id)
        if not result:
            return JSONResponse(
                {"status": "error", "message": "Session not found"},
                status_code=404,
            )
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
