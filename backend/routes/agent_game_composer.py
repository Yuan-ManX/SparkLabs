"""
SparkLabs Backend - Game Composer API Routes

REST API endpoints for the AI Game Composer that generates procedural
background music for games using the Web Audio API.

Endpoints:
  GET  /game-composer/status     - Composer status
  GET  /game-composer/history    - Recent compositions
  POST /game-composer/compose    - Compose BGM from genre/HTML
  POST /game-composer/inject     - Compose and inject into HTML
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _composer():
    from sparkai.agent.agent_game_composer import get_game_composer
    return get_game_composer()


@router.get("/game-composer/status")
async def composer_status():
    try:
        return JSONResponse({"status": "success", "data": _composer().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-composer/history")
async def composer_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _composer().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-composer/compose")
async def composer_compose(request: Request):
    """Compose procedural BGM.

    Body:
      genre: str  - Game genre (platformer, puzzle, shooter, etc.)
      html: str   - Optional game HTML for genre detection
      mood: str   - Optional mood override
      bars: int   - Number of bars (default 4)
    """
    try:
        body = await request.json()
        result = _composer().compose(
            genre=body.get("genre", ""),
            html=body.get("html", ""),
            mood_override=body.get("mood", ""),
            bars=int(body.get("bars", 4)),
        )
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-composer/inject")
async def composer_inject(request: Request):
    """Compose BGM and inject into game HTML.

    Body:
      html: str   - Game HTML
      genre: str  - Optional genre hint
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )
        healed_html, result = _composer().compose_and_inject(
            html, genre=body.get("genre", ""),
        )
        return JSONResponse({
            "status": "success",
            "data": {
                "composition": result.to_dict(include_js=False),
                "html": healed_html,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
