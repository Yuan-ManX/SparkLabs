"""
SparkLabs Backend - AI-Native Integration API Routes

REST API endpoints for the AI-native integration layer that synchronizes
the cognitive architect, AI-native conductor, game brain, and runtime
bridge with the existing KernelEngineIntegrator.

Endpoints:
  GET  /ai-integration/status    - Integration status and participant stats
  POST /ai-integration/tick      - Run a single integration tick
  GET  /ai-integration/history   - Get recent tick history
  POST /ai-integration/reset     - Reset integration state
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/ai-integration/status")
async def ai_integration_status():
    """Get the AI-native integration status."""
    try:
        from sparkai.engine.engine_ai_native_integration import (
            get_integration,
        )
        integration = get_integration()
        if not integration._initialized:
            integration.initialize()
        return JSONResponse({"status": "success", "data": integration.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-integration/tick")
async def ai_integration_tick():
    """Run a single AI-native integration tick."""
    try:
        from sparkai.engine.engine_ai_native_integration import (
            run_integration_tick,
        )
        result = run_integration_tick()
        return JSONResponse({"status": "success", "data": result})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-integration/history")
async def ai_integration_history(limit: int = 16):
    """Get recent integration tick history."""
    try:
        from sparkai.engine.engine_ai_native_integration import (
            get_integration,
        )
        integration = get_integration()
        if not integration._initialized:
            integration.initialize()
        return JSONResponse({
            "status": "success",
            "data": integration.history(limit=limit),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-integration/learning")
async def ai_integration_learning():
    """Get learning metrics from the LEARN phase."""
    try:
        from sparkai.engine.engine_ai_native_integration import (
            get_integration,
        )
        integration = get_integration()
        if not integration._initialized:
            integration.initialize()
        return JSONResponse({
            "status": "success",
            "data": integration.learning_stats(),
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-integration/reset")
async def ai_integration_reset():
    """Reset the AI-native integration state."""
    try:
        from sparkai.engine.engine_ai_native_integration import (
            get_integration,
        )
        integration = get_integration()
        integration.reset()
        return JSONResponse({"status": "success", "data": integration.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
