"""
SparkLabs Backend - Game Tournament API Routes

REST API endpoints for the AI Game Tournament that runs competitive
brackets between game variants, evaluating each through the Game Critic
and Game Analytics to crown a champion.

Endpoints:
  GET  /game-tournament/status   - Tournament agent status
  GET  /game-tournament/history  - Recent tournament results
  POST /game-tournament/run      - Run a tournament with game variants
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _tournament():
    from sparkai.agent.agent_game_tournament import get_game_tournament
    return get_game_tournament()


@router.get("/game-tournament/status")
async def tournament_status():
    try:
        return JSONResponse({"status": "success", "data": _tournament().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-tournament/history")
async def tournament_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _tournament().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-tournament/run")
async def tournament_run(request: Request):
    """Run a tournament with multiple game variants.

    Body:
      variants: list of {html: str, label?: str, source?: str}
      game_title: str (optional)
      genre: str (optional)
      critic_weight: float (optional, 0-1)
      analytics_weight: float (optional, 0-1)
    """
    try:
        body = await request.json()
        variants = body.get("variants", [])
        if not isinstance(variants, list) or len(variants) < 2:
            return JSONResponse(
                {"status": "error", "message": "At least 2 variants are required"},
                status_code=400,
            )

        result = _tournament().run(
            variants=variants,
            game_title=body.get("game_title", "Untitled Tournament"),
            genre=body.get("genre", ""),
            critic_weight=body.get("critic_weight"),
            analytics_weight=body.get("analytics_weight"),
        )
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=True),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
