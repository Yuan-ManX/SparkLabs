"""
SparkLabs Backend - Game Mutation Engine API Routes

REST API endpoints for the Game Mutation Engine that creates
controlled variations of generated games.

Endpoints:
  GET  /game-mutator/status       - Mutator status and strategy count
  GET  /game-mutator/strategies    - List all mutation strategies
  POST /game-mutator/mutate        - Apply a mutation strategy to game HTML
  POST /game-mutator/mutate-batch  - Apply multiple strategies to the same HTML
  GET  /game-mutator/history       - List recent mutation sessions
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/game-mutator/status")
async def mutator_status():
    """Get the Game Mutator status."""
    try:
        from sparkai.agent.agent_game_mutator import get_game_mutator
        mutator = get_game_mutator()
        if not mutator._initialized:
            mutator.initialize()
        return JSONResponse({"status": "success", "data": mutator.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-mutator/strategies")
async def mutator_strategies():
    """List all available mutation strategies."""
    try:
        from sparkai.agent.agent_game_mutator import get_game_mutator
        mutator = get_game_mutator()
        if not mutator._initialized:
            mutator.initialize()
        return JSONResponse({"status": "success", "data": mutator.get_strategies()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-mutator/mutate")
async def mutator_mutate(request: Request):
    """Apply a single mutation strategy to game HTML.

    Body:
      html: str          - The original game HTML
      strategy_id: str   - Which mutation strategy to apply
    """
    try:
        from sparkai.agent.agent_game_mutator import get_game_mutator
        body = await request.json()
        html = body.get("html", "")
        strategy_id = body.get("strategy_id", "")

        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )
        if not strategy_id:
            return JSONResponse(
                {"status": "error", "message": "strategy_id is required"},
                status_code=400,
            )

        mutator = get_game_mutator()
        if not mutator._initialized:
            mutator.initialize()

        result = mutator.mutate(html, strategy_id)
        return JSONResponse({
            "status": "success",
            "data": result.to_dict(include_html=True),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/game-mutator/mutate-batch")
async def mutator_mutate_batch(request: Request):
    """Apply multiple mutation strategies to the same game HTML.

    Body:
      html: str                  - The original game HTML
      strategy_ids: List[str]    - Which strategies to apply (optional, defaults to all)
    """
    try:
        from sparkai.agent.agent_game_mutator import get_game_mutator
        body = await request.json()
        html = body.get("html", "")
        strategy_ids = body.get("strategy_ids")

        if not html:
            return JSONResponse(
                {"status": "error", "message": "html is required"},
                status_code=400,
            )

        mutator = get_game_mutator()
        if not mutator._initialized:
            mutator.initialize()

        results = mutator.mutate_batch(html, strategy_ids)
        return JSONResponse({
            "status": "success",
            "data": [r.to_dict(include_html=False) for r in results],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/game-mutator/history")
async def mutator_history():
    """List recent mutation sessions."""
    try:
        from sparkai.agent.agent_game_mutator import get_game_mutator
        mutator = get_game_mutator()
        if not mutator._initialized:
            mutator.initialize()
        return JSONResponse({"status": "success", "data": mutator.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
