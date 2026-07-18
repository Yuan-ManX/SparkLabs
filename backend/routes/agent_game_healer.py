"""
SparkLabs Backend - Game Healer API Routes

REST API endpoints for the AI Game Healer that automatically repairs
game quality issues by injecting JavaScript patches for missing features.

Endpoints:
  GET  /game-healer/status    - Healer status
  GET  /game-healer/stats     - Aggregate statistics
  GET  /game-healer/history   - Recent healing sessions
  POST /game-healer/heal      - Heal a game from HTML
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _healer():
    from sparkai.agent.agent_game_healer import get_game_healer
    return get_game_healer()


@router.get("/game-healer/status")
async def healer_status():
    try:
        return JSONResponse({"status": "success", "data": _healer().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-healer/stats")
async def healer_stats():
    try:
        return JSONResponse({"status": "success", "data": _healer().get_stats()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-healer/history")
async def healer_history(limit: int = 20):
    try:
        return JSONResponse({
            "status": "success",
            "data": _healer().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-healer/heal")
async def healer_heal(request: Request):
    """Heal a game from its HTML source.

    Body:
      html: str - The game HTML to heal
      signals: dict - Optional pre-extracted quality signals
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )
        signals = body.get("signals")
        result = _healer().heal(html, signals=signals)
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=True),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
