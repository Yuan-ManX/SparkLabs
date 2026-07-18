"""
SparkLabs Backend - Game Analytics API Routes

REST API endpoints for the AI Game Analytics that predicts game
engagement metrics via Monte Carlo player simulation.

Endpoints:
  GET  /game-analytics/status    - Analytics status
  GET  /game-analytics/history   - Recent analysis runs
  POST /game-analytics/analyze   - Analyze game and predict metrics
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _analytics():
    from sparkai.agent.agent_game_analytics import get_game_analytics
    return get_game_analytics()


@router.get("/game-analytics/status")
async def analytics_status():
    try:
        return JSONResponse({"status": "success", "data": _analytics().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-analytics/history")
async def analytics_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _analytics().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-analytics/analyze")
async def analytics_analyze(request: Request):
    """Analyze a game and predict engagement metrics.

    Body:
      html: str                    - Game HTML for analysis
      genre: str                   - Optional genre hint
      simulations_per_persona: int - Simulations per persona (default 50)
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        genre = body.get("genre", "")
        sims = int(body.get("simulations_per_persona", 50))
        result = _analytics().analyze(
            html=html,
            genre=genre,
            simulations_per_persona=sims,
        )
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
