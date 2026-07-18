"""
SparkLabs Backend - Game Polish API Routes

REST API endpoints for the AI Game Polish agent that applies
production-ready polish to game HTML.

Endpoints:
  GET  /game-polish/status   - Polish agent status
  GET  /game-polish/history  - Recent polish results
  POST /game-polish/apply    - Apply production-ready polish to game HTML
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _polish():
    from sparkai.agent.agent_game_polish import get_game_polish
    return get_game_polish()


@router.get("/game-polish/status")
async def polish_status():
    try:
        return JSONResponse({"status": "success", "data": _polish().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-polish/history")
async def polish_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _polish().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-polish/apply")
async def polish_apply(request: Request):
    """Apply production-ready polish to game HTML.

    Body:
      html: str (required)
      game_title: str (optional)
      description: str (optional)
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html or not html.strip():
            return JSONResponse(
                {"status": "error", "message": "HTML content is required"},
                status_code=400,
            )

        result = _polish().polish(
            html=html,
            game_title=body.get("game_title", "Untitled Game"),
            description=body.get("description", ""),
        )
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=True),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
