"""
SparkLabs Backend - Adaptive Difficulty Director API Routes

REST API endpoints for the AI Adaptive Difficulty Director that
generates real-time player adaptation rules for generated games.

Endpoints:
  GET  /adaptive/status       - Director status and history count
  POST /adaptive/generate     - Generate adaptive profile + JS from prompt
  GET  /adaptive/history      - List recent adaptation sessions
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/adaptive/status")
async def adaptive_status():
    """Get the Adaptive Director status."""
    try:
        from sparkai.agent.agent_adaptive_director import get_adaptive_director
        director = get_adaptive_director()
        if not director._initialized:
            director.initialize()
        return JSONResponse({"status": "success", "data": director.get_status()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/adaptive/generate")
async def adaptive_generate(request: Request):
    """Generate an adaptive difficulty profile and JS code.

    Body:
      prompt: str - Game description (same as conductor prompt)
    """
    try:
        from sparkai.agent.agent_adaptive_director import get_adaptive_director
        body = await request.json()
        prompt = body.get("prompt", "").strip()

        if not prompt:
            return JSONResponse(
                {"status": "error", "message": "prompt is required"},
                status_code=400,
            )

        director = get_adaptive_director()
        if not director._initialized:
            director.initialize()

        result = director.generate(prompt=prompt)
        return JSONResponse({"status": "success", "data": result.to_dict()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/adaptive/history")
async def adaptive_history():
    """List recent adaptation sessions."""
    try:
        from sparkai.agent.agent_adaptive_director import get_adaptive_director
        director = get_adaptive_director()
        if not director._initialized:
            director.initialize()
        return JSONResponse({"status": "success", "data": director.get_history()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
