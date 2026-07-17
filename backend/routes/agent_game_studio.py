"""
SparkLabs Backend - Agent Game Studio API Routes

REST API endpoints for the multi-agent Game Studio system.
The studio orchestrates specialist agents (Designer, Programmer, Artist,
Tester, Composer) that collaborate to produce a consolidated game blueprint.

Endpoints:
  GET  /game-studio/status        - Studio status and recent sessions
  GET  /game-studio/agents        - List studio agents and their roles
  POST /game-studio/collaborate   - Run a collaboration session on a prompt
  GET  /game-studio/history       - List recent studio sessions
  GET  /game-studio/result/{sid}  - Retrieve a cached studio result
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()

# In-memory result cache for retrieval by session_id
_result_cache: dict = {}


@router.get("/game-studio/status")
async def game_studio_status():
    """Get the Game Studio system status."""
    try:
        from sparkai.agent.agent_game_studio import get_game_studio
        studio = get_game_studio()
        if not studio._initialized:
            studio.initialize()
        return JSONResponse({"status": "success", "data": studio.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-studio/agents")
async def game_studio_agents():
    """List the studio agents and their roles."""
    try:
        return JSONResponse({
            "status": "success",
            "data": {
                "agents": [
                    {"name": "Designer", "role": "game_design", "expertise": "mechanics, rules, balance, progression"},
                    {"name": "Programmer", "role": "technical_architecture", "expertise": "logic, feasibility, performance"},
                    {"name": "Artist", "role": "visual_design", "expertise": "style, palette, atmosphere"},
                    {"name": "Tester", "role": "quality_assurance", "expertise": "playtesting, edge cases, risk mitigation"},
                    {"name": "Composer", "role": "audio_design", "expertise": "mood, tempo, SFX landscape"},
                ],
                "collaboration_rounds": 3,
                "process": [
                    "Round 1: Independent domain proposals",
                    "Round 2: Cross-agent feedback and review",
                    "Round 3: Consensus and blueprint consolidation",
                ],
            },
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-studio/collaborate")
async def game_studio_collaborate(request: Request):
    """Run a multi-agent collaboration session.

    Body:
      prompt: str   - Natural-language game description
      rounds: int   - Number of collaboration rounds (default 3)
    """
    try:
        from sparkai.agent.agent_game_studio import get_game_studio
        body = await request.json()
        prompt = body.get("prompt", "").strip()
        rounds = body.get("rounds", 3)

        if not prompt:
            return JSONResponse(
                {"status": "error", "message": "prompt is required"},
                status_code=400,
            )

        studio = get_game_studio()
        if not studio._initialized:
            studio.initialize()

        result = studio.collaborate(prompt=prompt, rounds=rounds)

        data = result.to_dict()
        _result_cache[result.session_id] = data

        return JSONResponse({"status": "success", "data": data})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-studio/history")
async def game_studio_history():
    """List recent studio sessions."""
    try:
        from sparkai.agent.agent_game_studio import get_game_studio
        studio = get_game_studio()
        if not studio._initialized:
            studio.initialize()
        return JSONResponse({"status": "success", "data": studio.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-studio/result/{session_id}")
async def game_studio_get_result(session_id: str):
    """Retrieve a cached studio result by session_id."""
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
