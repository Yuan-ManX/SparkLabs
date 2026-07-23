"""
SparkLabs Backend - Agent Chat Controller

Connects the frontend agent chat to the LLM router, enabling users to
chat with the agent and have it route requests to the optimal model for
each task. The controller classifies the task type from the chat message,
routes to the best model, executes the request (or simulates when no API
keys are configured), and returns the response with routing metadata.

Endpoints:
  POST /chat/message        - Send a chat message and get a model-routed response
  GET  /chat/models         - List all available models grouped by type
  GET  /chat/task-types     - List all supported task types
  GET  /chat/strategies     - List routing strategies
  POST /chat/strategy       - Set the active routing strategy
  POST /chat/simulation     - Toggle simulation mode
  GET  /chat/history        - Get chat history
  POST /chat/generate       - Generate multimodal content (image/audio/video/3D)
  GET  /chat/status         - Get router status and simulation mode
"""

from __future__ import annotations

import time
import uuid
from collections import deque
from typing import Any, Deque, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory chat history (per session)
_chat_history: Deque[Dict[str, Any]] = deque(maxlen=200)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class ChatMessageRequest(BaseModel):
    message: str
    system_prompt: str = ""
    session_id: str = "default"
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    task_type: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    images: Optional[List[str]] = None


class SetStrategyRequest(BaseModel):
    strategy: str


class SetSimulationRequest(BaseModel):
    enabled: bool


class GenerateRequest(BaseModel):
    prompt: str
    modality: str  # image, audio, video, 3d
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    width: int = 1024
    height: int = 1024
    duration: int = 5
    voice: str = "alloy"
    n: int = 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_router():
    """Get the LLM router singleton."""
    from sparkai.agent.agent_llm_router import get_llm_router
    return get_llm_router()


def _classify_task(message: str) -> str:
    """Classify the chat message into a task type using keyword matching."""
    msg_lower = message.lower()
    task_keywords = {
        "world_building": ["world", "terrain", "map", "environment", "landscape", "biome"],
        "character_design": ["character", "hero", "player", "npc", "protagonist", "avatar"],
        "dialogue": ["dialogue", "conversation", "talk", "speak", "chat", "say"],
        "code_gen": ["code", "function", "class", "script", "implement", "program", "api"],
        "asset_image": ["image", "picture", "sprite", "texture", "icon", "draw", "paint"],
        "asset_video": ["video", "animation", "cinematic", "cutscene", "clip"],
        "asset_3d": ["3d", "model", "mesh", "geometry", "render", "obj", "fbx"],
        "asset_audio": ["audio", "sound", "sfx", "effect", "noise"],
        "music_gen": ["music", "song", "melody", "soundtrack", "bgm", "theme"],
        "voice_acting": ["voice", "speech", "narrate", "tts", "dub", "vocal"],
        "bug_analysis": ["bug", "error", "fix", "debug", "crash", "issue", "broken"],
        "balance_test": ["balance", "difficulty", "tune", "adjust", "scale", "curve"],
        "narrative": ["story", "narrative", "plot", "quest", "arc", "lore", "tale"],
        "translation": ["translate", "localize", "language", "i18n"],
        "summarization": ["summarize", "brief", "tldr", "overview", "condense"],
    }
    best_task = "dialogue"
    best_score = 0
    for task, keywords in task_keywords.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_task = task
    return best_task


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat/message")
async def chat_message(req: ChatMessageRequest):
    """Send a chat message and get a model-routed response.

    The controller classifies the task type from the message, routes to
    the best model via the LLM router, and returns the response. When no
    API keys are configured, the router returns a simulated response.
    """
    try:
        from sparkai.agent.agent_llm_router import (
            ModelRequest, TaskType, GenerationConfig,
        )

        llm_router = _get_router()

        # Classify task type if not specified
        task_type_str = req.task_type or _classify_task(req.message)
        task_type_map = {tt.value: tt for tt in TaskType}
        task_type = task_type_map.get(task_type_str, TaskType.DIALOGUE)

        # Build model request
        config = GenerationConfig(
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        model_request = ModelRequest(
            task_type=task_type,
            prompt=req.message,
            system_prompt=req.system_prompt or (
                "You are the SparkLabs AI Game Engine assistant. "
                "You help users design, build, and optimize games. "
                "Provide clear, actionable responses with code when relevant."
            ),
            model_id=req.model_id,
            provider_id=req.provider_id,
            config=config,
            images=req.images or [],
            use_cache=True,
        )

        # Execute request through the router
        response = llm_router.execute_request(model_request)

        # Record in chat history
        entry = {
            "id": str(uuid.uuid4()),
            "session_id": req.session_id,
            "timestamp": time.time(),
            "user_message": req.message,
            "agent_response": response.content,
            "task_type": task_type_str,
            "provider_id": response.provider_id,
            "model_id": response.model_id,
            "simulated": response.simulated,
            "cached": response.cached,
            "fallback_used": response.fallback_used,
            "latency_ms": response.latency_ms,
            "input_tokens": response.input_tokens,
            "output_tokens": response.output_tokens,
            "cost": response.cost,
        }
        _chat_history.append(entry)

        return JSONResponse({
            "status": "success",
            "data": {
                "response": response.content,
                "content_urls": response.content_urls,
                "task_type": task_type_str,
                "provider_id": response.provider_id,
                "model_id": response.model_id,
                "simulated": response.simulated,
                "cached": response.cached,
                "fallback_used": response.fallback_used,
                "latency_ms": response.latency_ms,
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost": response.cost,
                "finish_reason": response.finish_reason,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat/models")
async def chat_models():
    """List all available models grouped by modality type."""
    try:
        llm_router = _get_router()
        models = llm_router.list_models()

        # Group by model type
        by_type: Dict[str, List[Dict[str, Any]]] = {}
        for m in models:
            mtype = m.get("model_type", "text") if isinstance(m, dict) else "text"
            by_type.setdefault(mtype, []).append(m)

        return JSONResponse({
            "status": "success",
            "data": {
                "total_count": len(models),
                "by_type": by_type,
                "all_models": models,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat/task-types")
async def chat_task_types():
    """List all supported task types with descriptions."""
    try:
        from sparkai.agent.agent_llm_router import TaskType

        task_descriptions = {
            "world_building": "Generate game worlds, terrain, environments",
            "character_design": "Create characters with abilities and animations",
            "dialogue": "Generate character dialogue and conversations",
            "code_gen": "Write game code, scripts, and systems",
            "asset_image": "Generate images, sprites, and textures",
            "asset_video": "Generate videos and cutscenes",
            "asset_3d": "Generate 3D models and meshes",
            "asset_audio": "Generate sound effects and audio",
            "music_gen": "Compose music and soundtracks",
            "voice_acting": "Generate voice narration and TTS",
            "bug_analysis": "Analyze and diagnose bugs",
            "balance_test": "Balance difficulty and game metrics",
            "narrative": "Design story narratives and quests",
            "translation": "Translate and localize content",
            "summarization": "Summarize and condense content",
        }

        task_types = [
            {
                "value": tt.value,
                "name": tt.name,
                "description": task_descriptions.get(tt.value, ""),
            }
            for tt in TaskType
        ]
        return JSONResponse({
            "status": "success",
            "data": {"task_types": task_types, "count": len(task_types)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat/strategies")
async def chat_strategies():
    """List all routing strategies and the active one."""
    try:
        from sparkai.agent.agent_llm_router import RoutingStrategy

        llm_router = _get_router()
        strategies = [
            {"value": s.value, "name": s.name} for s in RoutingStrategy
        ]
        active = llm_router.get_routing_strategy().value
        return JSONResponse({
            "status": "success",
            "data": {"strategies": strategies, "active": active},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/chat/strategy")
async def chat_set_strategy(req: SetStrategyRequest):
    """Set the active routing strategy."""
    try:
        from sparkai.agent.agent_llm_router import RoutingStrategy

        strategy_map = {s.value: s for s in RoutingStrategy}
        strategy = strategy_map.get(req.strategy)
        if strategy is None:
            return JSONResponse(
                status_code=400,
                content={"status": "error", "message": f"Unknown strategy: {req.strategy}"},
            )
        llm_router = _get_router()
        llm_router.set_routing_strategy(strategy)
        return JSONResponse({
            "status": "success",
            "data": {"active": strategy.value},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/chat/simulation")
async def chat_set_simulation(req: SetSimulationRequest):
    """Toggle simulation mode on or off."""
    try:
        llm_router = _get_router()
        llm_router.set_simulation_mode(req.enabled)
        return JSONResponse({
            "status": "success",
            "data": {"simulation_mode": req.enabled},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat/history")
async def chat_history(session_id: str = "", limit: int = 50):
    """Get chat history, optionally filtered by session_id."""
    try:
        history = list(_chat_history)
        if session_id:
            history = [h for h in history if h.get("session_id") == session_id]
        history = history[-limit:]
        return JSONResponse({
            "status": "success",
            "data": {"history": history, "count": len(history)},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/chat/generate")
async def chat_generate(req: GenerateRequest):
    """Generate multimodal content (image, audio, video, 3D) through the router."""
    try:
        from sparkai.agent.agent_llm_router import (
            ModelRequest, TaskType, GenerationConfig,
        )

        llm_router = _get_router()

        # Map modality to task type
        modality_task_map = {
            "image": TaskType.ASSET_IMAGE,
            "audio": TaskType.ASSET_AUDIO,
            "video": TaskType.ASSET_VIDEO,
            "3d": TaskType.ASSET_3D,
            "music": TaskType.MUSIC_GEN,
            "voice": TaskType.VOICE_ACTING,
        }
        task_type = modality_task_map.get(req.modality, TaskType.ASSET_IMAGE)

        config = GenerationConfig()
        model_request = ModelRequest(
            task_type=task_type,
            prompt=req.prompt,
            model_id=req.model_id,
            provider_id=req.provider_id,
            config=config,
            use_cache=False,
        )

        response = llm_router.execute_request(model_request)

        return JSONResponse({
            "status": "success",
            "data": {
                "content": response.content,
                "content_urls": response.content_urls,
                "modality": req.modality,
                "provider_id": response.provider_id,
                "model_id": response.model_id,
                "simulated": response.simulated,
                "latency_ms": response.latency_ms,
                "cost": response.cost,
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat/status")
async def chat_status():
    """Get the LLM router status, including simulation mode and provider count."""
    try:
        llm_router = _get_router()
        providers = llm_router.list_providers()
        models = llm_router.list_models()
        return JSONResponse({
            "status": "success",
            "data": {
                "router_active": True,
                "simulation_mode": llm_router.get_simulation_mode(),
                "routing_strategy": llm_router.get_routing_strategy().value,
                "provider_count": len(providers),
                "model_count": len(models),
                "cache_stats": llm_router.get_cache_stats(),
                "chat_history_count": len(_chat_history),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )
