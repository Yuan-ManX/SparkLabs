"""
SparkLabs Backend - Game Evolver API Routes

REST API endpoints for the AI Game Evolver that optimizes games through
evolutionary iteration using mutation + critique as fitness function.

Endpoints:
  GET  /game-evolver/status    - Evolver status
  GET  /game-evolver/stats     - Aggregate statistics
  GET  /game-evolver/history   - Recent evolution runs
  GET  /game-evolver/strategies - List default strategies
  POST /game-evolver/evolve    - Evolve a game from HTML
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


def _evolver():
    from sparkai.agent.agent_game_evolver import get_game_evolver
    return get_game_evolver()


@router.get("/game-evolver/status")
async def evolver_status():
    try:
        return JSONResponse({"status": "success", "data": _evolver().get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-evolver/stats")
async def evolver_stats():
    try:
        return JSONResponse({"status": "success", "data": _evolver().get_stats()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-evolver/history")
async def evolver_history(limit: int = 10):
    try:
        return JSONResponse({
            "status": "success",
            "data": _evolver().get_history(limit=limit),
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-evolver/strategies")
async def evolver_strategies():
    try:
        return JSONResponse({
            "status": "success",
            "data": {"strategies": _evolver().DEFAULT_STRATEGIES},
        })
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-evolver/evolve")
async def evolver_evolve(request: Request):
    """Evolve a game through multiple generations.

    Body:
      html: str             - The base game HTML
      generations: int      - Number of generations (default 3)
      population_size: int  - Mutations per generation (default 5)
      strategies: list      - Optional list of strategy IDs
      game_title: str       - Optional title
      genre: str            - Optional genre hint
    """
    try:
        body = await request.json()
        html = body.get("html", "")
        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )
        result = _evolver().evolve(
            html=html,
            generations=int(body.get("generations", 3)),
            population_size=int(body.get("population_size", 5)),
            strategies=body.get("strategies"),
            game_title=body.get("game_title", "Evolved Game"),
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
