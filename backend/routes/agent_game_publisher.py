"""
SparkLabs Backend - Game Publisher API Routes

REST API endpoints for the AI Game Publisher agent that turns
polished game HTML into a deployment-ready package.

Endpoints:
  GET  /game-publisher/status    - Publisher agent status
  GET  /game-publisher/history   - Recent publish results
  POST /game-publisher/publish   - Publish game HTML to a deployable package
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _publisher():
    from sparkai.agent.agent_game_publisher import get_game_publisher
    return get_game_publisher()


@router.get("/game-publisher/status")
async def publisher_status():
    try:
        return JSONResponse({"status": "success", "data": _publisher().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-publisher/history")
async def publisher_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _publisher().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-publisher/publish")
async def publisher_publish(request: Request):
    """Publish polished game HTML to a deployment-ready package.

    Body:
      html: str (required)
      game_title: str (optional)
      version: str (optional, semantic version like "1.0.0")
      description: str (optional)
      share_url: str (optional)
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html or not html.strip():
            return JSONResponse(
                {"status": "error", "message": "HTML content is required"},
                status_code=400,
            )

        result = _publisher().publish(
            html=html,
            game_title=body.get("game_title", "Untitled Game"),
            version=body.get("version", ""),
            description=body.get("description", ""),
            share_url=body.get("share_url", ""),
        )
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=False, html=html),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
