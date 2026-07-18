"""
SparkLabs Backend - Game Sentinel API Routes

REST API endpoints for the AI Game Sentinel agent that validates,
repairs, and instruments game HTML with runtime telemetry.

Endpoints:
  GET  /game-sentinel/status    - Sentinel agent status
  GET  /game-sentinel/history   - Recent guard results
  POST /game-sentinel/guard     - Validate and repair game HTML
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _sentinel():
    from sparkai.agent.agent_game_sentinel import GameSentinel
    return GameSentinel.get_instance()


@router.get("/game-sentinel/status")
async def sentinel_status():
    try:
        return JSONResponse({"status": "success", "data": _sentinel().status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-sentinel/history")
async def sentinel_history(limit: int = 10):
    try:
        history = _sentinel().get_history()
        return JSONResponse({
            "status": "success",
            "data": history[-limit:] if limit < len(history) else history,
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-sentinel/guard")
async def sentinel_guard(request: Request):
    """Validate, repair, and instrument game HTML.

    Body:
      html: str (required)
      inject_telemetry: bool (optional, default true)
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html or not html.strip():
            return JSONResponse(
                {"status": "error", "message": "HTML content is required"},
                status_code=400,
            )

        inject_telemetry = body.get("inject_telemetry", True)
        result = _sentinel().guard(html, inject_telemetry=inject_telemetry)
        return JSONResponse({
            "status": "success",
            "data": {
                "report": result["report"],
                "html_length": len(result["html"]),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
