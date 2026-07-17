"""
SparkLabs Backend - Agent Game Conductor API Routes

REST API endpoints for the AI Game Conductor system.
The conductor unifies the GameDirector, GameIntelligenceEngine, and
GameDesignReasoner into a single intelligent creation pipeline that
produces both a playable game and a rich intelligence report.

Endpoints:
  GET  /game-conductor/status        - Pipeline status and recent sessions
  GET  /game-conductor/capabilities  - Conductor capabilities and subsystems
  POST /game-conductor/conduct       - Run the full conductor pipeline on a prompt
  GET  /game-conductor/history       - List recent conductor sessions
  GET  /game-conductor/result/{sid}  - Retrieve a cached conductor result
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# In-memory result cache for retrieval by session_id
_result_cache: dict = {}


@router.get("/game-conductor/status")
async def game_conductor_status():
    """Get the Game Conductor system status."""
    try:
        from sparkai.agent.agent_game_conductor import get_game_conductor
        conductor = get_game_conductor()
        if not conductor._initialized:
            conductor.initialize()
        return JSONResponse({"status": "success", "data": conductor.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-conductor/capabilities")
async def game_conductor_capabilities():
    """List conductor capabilities: subsystems and analysis types."""
    try:
        return JSONResponse({
            "status": "success",
            "data": {
                "subsystems": [
                    "game_director",
                    "game_intelligence_engine",
                    "game_design_reasoner",
                ],
                "analysis_types": [
                    "design_patterns",
                    "strengths_weaknesses",
                    "balance_report",
                    "difficulty_curve",
                    "player_experience",
                    "improvement_suggestions",
                ],
                "player_archetypes": [
                    "casual", "hardcore", "achiever", "explorer",
                ],
                "design_aspects": [
                    "balance", "difficulty", "progression", "economy",
                    "pacing", "accessibility", "replayability", "engagement",
                ],
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-conductor/conduct")
async def game_conductor_conduct(request: Request):
    """Run the full conductor pipeline: direct, analyze, report.

    Body:
      prompt: str          - Natural-language game description
      genre_hint: str      - Optional genre hint
      max_iterations: int  - Override max refinement iterations
      return_html: bool    - Include HTML in response (default true)
    """
    try:
        from sparkai.agent.agent_game_conductor import get_game_conductor
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

        conductor = get_game_conductor()
        if not conductor._initialized:
            conductor.initialize()

        result = conductor.conduct(
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


@router.get("/game-conductor/history")
async def game_conductor_history():
    """List recent conductor sessions."""
    try:
        from sparkai.agent.agent_game_conductor import get_game_conductor
        conductor = get_game_conductor()
        if not conductor._initialized:
            conductor.initialize()
        return JSONResponse({"status": "success", "data": conductor.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-conductor/result/{session_id}")
async def game_conductor_get_result(session_id: str):
    """Retrieve a cached conductor result by session_id."""
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
