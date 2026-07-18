"""
SparkLabs Backend - Game Fusion API Routes

REST API endpoints for the AI Game Fusion agent that merges the
strengths of multiple game variants into a single superior game.

Endpoints:
  GET  /game-fusion/status   - Fusion agent status
  GET  /game-fusion/history  - Recent fusion results
  POST /game-fusion/fuse     - Fuse multiple game variants
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _fusion():
    from sparkai.agent.agent_game_fusion import get_game_fusion
    return get_game_fusion()


@router.get("/game-fusion/status")
async def fusion_status():
    try:
        return JSONResponse({"status": "success", "data": _fusion().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-fusion/history")
async def fusion_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _fusion().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-fusion/fuse")
async def fusion_fuse(request: Request):
    """Fuse multiple game variants into a single superior game.

    Body:
      variants: list of {html: str, label?: str, source?: str}
      game_title: str (optional)
      genre: str (optional)
    """
    try:
        body = await request.json()
        variants = body.get("variants", [])
        if not isinstance(variants, list) or len(variants) < 2:
            return JSONResponse(
                {"status": "error", "message": "At least 2 variants are required"},
                status_code=400,
            )

        result = _fusion().fuse(
            variants=variants,
            game_title=body.get("game_title", "Fused Game"),
            genre=body.get("genre", ""),
        )
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=True),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
