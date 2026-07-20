"""
SparkLabs Backend - AI Runtime Bridge API Routes

REST API endpoints for the AI runtime bridge that connects the cognitive
layer to the game generation pipeline. The bridge wraps GameRuntime with
AI-driven pre-build reasoning, config adaptation, and post-build telemetry
and adaptive difficulty injection.

Endpoints:
  GET  /ai-bridge/status          - Bridge status and build history
  POST /ai-bridge/build-from-gdd  - Build a game from a GDD with AI adaptation
  POST /ai-bridge/build-from-prompt - Build a game from a prompt with AI adaptation
  GET  /ai-bridge/last-overrides  - Get the last AI-derived parameter overrides
  POST /ai-bridge/reset           - Reset the bridge state
"""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, Optional

router = APIRouter()


class BuildFromPromptRequest(BaseModel):
    prompt: str
    genre_hint: Optional[str] = None


@router.get("/ai-bridge/status")
async def ai_bridge_status():
    """Get the AI runtime bridge status."""
    try:
        from sparkai.engine.engine_ai_runtime_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        if not bridge._initialized:
            bridge.initialize()
        return JSONResponse({"status": "success", "data": bridge.status()})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-bridge/build-from-prompt")
async def ai_bridge_build_from_prompt(req: BuildFromPromptRequest):
    """Build a game from a prompt with AI-driven adaptation."""
    try:
        from sparkai.engine.engine_ai_runtime_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        if not bridge._initialized:
            bridge.initialize()
        result = bridge.build_from_prompt(req.prompt, genre_hint=req.genre_hint)
        # Strip the HTML to reduce payload if the build is large
        html = result.html if result.html else ""
        # Truncate HTML in the response if it's very large (keep first 50KB for preview)
        html_preview = html[:50000] if len(html) > 50000 else html
        html_truncated = len(html) > 50000
        return JSONResponse({"status": "success", "data": {
            "success": result.success,
            "error": result.error,
            "duration_s": result.duration_s,
            "ai_session_id": result.ai_session_id,
            "ai_overrides": result.ai_overrides,
            "ai_reasoning_conclusion": result.ai_reasoning_conclusion,
            "html_length": len(html),
            "html_preview": html_preview,
            "html_truncated": html_truncated,
            "metadata": result.metadata,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-bridge/build-from-gdd")
async def ai_bridge_build_from_gdd(request: Request):
    """Build a game from a GDD with AI-driven adaptation."""
    try:
        from sparkai.engine.engine_ai_runtime_bridge import get_ai_bridge
        body = await request.json()
        gdd_data = body.get("gdd")
        prompt = body.get("prompt", "")

        if not gdd_data:
            return JSONResponse(
                {"status": "error", "message": "gdd is required"},
                status_code=400,
            )

        bridge = get_ai_bridge()
        if not bridge._initialized:
            bridge.initialize()

        # Reconstruct a minimal GDD-like object from the JSON
        # The actual GDD class is in agent_game_content_synthesizer
        from sparkai.agent.agent_game_content_synthesizer import GameDesignDocument
        gdd = GameDesignDocument.from_dict(gdd_data) if hasattr(GameDesignDocument, "from_dict") else None

        result = bridge.build_from_gdd(gdd, prompt=prompt)
        html = result.html if result.html else ""
        html_preview = html[:50000] if len(html) > 50000 else html
        html_truncated = len(html) > 50000

        return JSONResponse({"status": "success", "data": {
            "success": result.success,
            "error": result.error,
            "duration_s": result.duration_s,
            "ai_session_id": result.ai_session_id,
            "ai_overrides": result.ai_overrides,
            "ai_reasoning_conclusion": result.ai_reasoning_conclusion,
            "html_length": len(html),
            "html_preview": html_preview,
            "html_truncated": html_truncated,
            "metadata": result.metadata,
        }})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/ai-bridge/last-overrides")
async def ai_bridge_last_overrides():
    """Get the last AI-derived parameter overrides."""
    try:
        from sparkai.engine.engine_ai_runtime_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        return JSONResponse({"status": "success", "data": bridge.get_last_overrides()})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.post("/ai-bridge/reset")
async def ai_bridge_reset():
    """Reset the bridge state."""
    try:
        from sparkai.engine.engine_ai_runtime_bridge import get_ai_bridge
        bridge = get_ai_bridge()
        bridge.reset()
        return JSONResponse({"status": "success", "data": {"reset": True}})
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
