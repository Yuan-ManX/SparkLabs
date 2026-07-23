"""
SparkLabs Backend - Chat-to-Editor Bridge

Connects the agent chat to the game editor, enabling users to control
the editor through natural language. The bridge classifies chat messages
into editor actions, routes through the LLM router for model responses,
and executes the corresponding editor operations.

This is the capstone that makes the AI-native editor truly conversational:
users can say "create a platformer level with moving platforms" and the
bridge will route the request to the optimal model, parse the response,
and execute the editor action.

Editor Actions:
  create_game     - Create a full playable game from a description
  create_entity   - Create a single entity (character, enemy, item, etc.)
  create_scene    - Create a scene from a natural language description
  generate_code   - Generate game code or scripts
  generate_asset  - Generate an image, 3D model, or audio asset
  analyze_bug     - Analyze and diagnose a bug from description
  balance_game    - Balance game difficulty and metrics
  list_scene      - List entities in the current scene
  editor_status   - Get the current editor state

Endpoints:
  POST /chat-editor/execute   - Execute a chat-driven editor action
  GET  /chat-editor/actions   - List available editor actions
  GET  /chat-editor/status    - Get bridge status
  POST /chat-editor/reset     - Reset the bridge state
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

# Action history
_action_history: Deque[Dict[str, Any]] = deque(maxlen=100)


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class EditorActionRequest(BaseModel):
    message: str
    action_type: Optional[str] = None  # auto-classify if not specified
    session_id: str = "default"
    model_id: Optional[str] = None
    provider_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# Action Classifier
# ---------------------------------------------------------------------------

ACTION_KEYWORDS = {
    "create_game": [
        "create a game", "make a game", "build a game", "generate a game",
        "new game", "start a game", "design a game", "full game",
        "create game", "make game", "build game",
    ],
    "create_entity": [
        "create entity", "add entity", "make entity", "spawn entity",
        "create character", "add character", "make character", "create enemy",
        "add enemy", "create item", "add item", "create npc", "add npc",
        "create obstacle", "add obstacle", "create platform", "add platform",
        "add a character", "create a character", "create an enemy",
    ],
    "create_scene": [
        "create scene", "make scene", "build scene", "new scene",
        "create level", "make level", "build level", "design level",
        "create environment", "design environment", "create a scene",
        "create a level", "design a level",
    ],
    "generate_code": [
        "write code", "generate code", "create script", "write script",
        "implement function", "write function", "create class",
        "generate python", "write python", "code a", "program a",
        "write a function", "write a python", "implement a", "python function",
        "generate a function", "write a script", "code", "function",
        "implement", "script", "python",
    ],
    "generate_asset": [
        "generate image", "create image", "make image", "draw",
        "generate sprite", "create sprite", "generate texture",
        "generate 3d", "create 3d", "make 3d model", "generate model",
        "generate audio", "create sound", "make sound", "generate music",
        "generate an image", "create an image", "image of",
    ],
    "analyze_bug": [
        "bug", "error", "crash", "broken", "not working", "fix",
        "debug", "diagnose", "issue", "problem", "wrong",
        "falls through", "doesn't work", "fails",
    ],
    "balance_game": [
        "balance", "difficulty", "too hard", "too easy", "tune",
        "adjust difficulty", "scale", "curve", " pacing",
        "balance the", "balance combat",
    ],
    "list_scene": [
        "list entities", "show entities", "what entities", "list scene",
        "show scene", "what's in the scene", "current scene",
    ],
    "editor_status": [
        "editor status", "status", "what mode", "current state",
        "editor info", "editor state", "what can you do",
    ],
    "create_dialogue": [
        "create dialogue", "write dialogue", "generate dialogue",
        "create conversation", "write conversation", "npc dialogue",
        "character speech", "voice line", "create speech",
        "branching dialogue", "dialogue tree",
        "dialogue", "conversation", "speech", "voice line",
    ],
    "generate_level": [
        "generate level", "create level layout", "design level layout",
        "procedural level", "level generator", "map generator",
        "create dungeon", "generate dungeon", "create terrain",
        "generate terrain", "create world map", "level design",
        "level layout", "dungeon", "terrain", "map generator",
    ],
    "create_animation": [
        "create animation", "generate animation", "animate",
        "create walk cycle", "create idle animation", "create attack animation",
        "sprite animation", "bone animation", "rig animation",
        "keyframe animation", "animation clip",
        "animation", "walk cycle", "keyframe",
    ],
}


def _classify_action(message: str) -> str:
    """Classify a chat message into an editor action type."""
    msg_lower = message.lower()
    best_action = "create_entity"  # default
    best_score = 0
    for action, keywords in ACTION_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in msg_lower)
        if score > best_score:
            best_score = score
            best_action = action
    return best_action


# ---------------------------------------------------------------------------
# Action Executors
# ---------------------------------------------------------------------------

def _execute_create_game(message: str, context: Optional[Dict]) -> Dict[str, Any]:
    """Execute a game creation action through the orchestrator."""
    try:
        from sparkai.engine.engine_game_creation_orchestrator import get_orchestrator
        orch = get_orchestrator()
        if not orch._initialized:
            orch.initialize()
        result = orch.create_game(message)
        return {
            "success": True,
            "action": "create_game",
            "result": result.to_dict(include_html=False),
            "run_id": result.run_id,
        }
    except Exception as e:
        return {"success": False, "action": "create_game", "error": str(e)}


def _execute_create_entity(message: str, context: Optional[Dict]) -> Dict[str, Any]:
    """Execute an entity creation action."""
    try:
        entity_id = f"entity_{uuid.uuid4().hex[:8]}"
        # Parse entity type from message
        msg_lower = message.lower()
        if "character" in msg_lower or "player" in msg_lower or "hero" in msg_lower:
            entity_type = "character"
        elif "enemy" in msg_lower or "monster" in msg_lower or "boss" in msg_lower:
            entity_type = "enemy"
        elif "item" in msg_lower or "pickup" in msg_lower or "collectible" in msg_lower:
            entity_type = "item"
        elif "npc" in msg_lower:
            entity_type = "npc"
        elif "platform" in msg_lower or "obstacle" in msg_lower:
            entity_type = "obstacle"
        else:
            entity_type = "generic"

        entity_data = {
            "entity_id": entity_id,
            "name": message[:50],
            "type": entity_type,
            "position": {"x": 0, "y": 0},
            "components": ["transform", "renderer"],
            "properties": {"description": message},
            "created_at": time.time(),
        }
        return {
            "success": True,
            "action": "create_entity",
            "result": entity_data,
            "entity_id": entity_id,
        }
    except Exception as e:
        return {"success": False, "action": "create_entity", "error": str(e)}


def _execute_create_scene(message: str, context: Optional[Dict]) -> Dict[str, Any]:
    """Execute a scene creation action."""
    try:
        scene_id = f"scene_{uuid.uuid4().hex[:8]}"
        scene_data = {
            "scene_id": scene_id,
            "name": message[:60],
            "description": message,
            "entities": [],
            "ambient": "day",
            "created_at": time.time(),
        }
        return {
            "success": True,
            "action": "create_scene",
            "result": scene_data,
            "scene_id": scene_id,
        }
    except Exception as e:
        return {"success": False, "action": "create_scene", "error": str(e)}


def _execute_generate_code(message: str, context: Optional[Dict],
                           provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute a code generation action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.CODE_GEN,
            prompt=message,
            system_prompt=(
                "You are a game code generation expert. "
                "Generate clean, well-commented code based on the request. "
                "Use Python unless otherwise specified."
            ),
            config=GenerationConfig(temperature=0.3, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "generate_code",
            "result": {
                "code": response.content,
                "language": "python",
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "generate_code", "error": str(e)}


def _execute_generate_asset(message: str, context: Optional[Dict],
                            provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute an asset generation action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        # Determine modality from message
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["3d", "model", "mesh"]):
            task_type = TaskType.ASSET_3D
            modality = "3d"
        elif any(w in msg_lower for w in ["audio", "sound", "music", "sfx"]):
            task_type = TaskType.ASSET_AUDIO
            modality = "audio"
        elif any(w in msg_lower for w in ["video", "animation", "cinematic"]):
            task_type = TaskType.ASSET_VIDEO
            modality = "video"
        else:
            task_type = TaskType.ASSET_IMAGE
            modality = "image"

        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=task_type,
            prompt=message,
            config=GenerationConfig(),
            use_cache=False,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "generate_asset",
            "result": {
                "modality": modality,
                "content": response.content,
                "content_urls": response.content_urls,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "generate_asset", "error": str(e)}


def _execute_analyze_bug(message: str, context: Optional[Dict],
                         provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute a bug analysis action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.BUG_ANALYSIS,
            prompt=message,
            system_prompt=(
                "You are a game debugging expert. Analyze the described issue, "
                "identify the root cause, and provide a fix with code."
            ),
            config=GenerationConfig(temperature=0.2, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "analyze_bug",
            "result": {
                "analysis": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "analyze_bug", "error": str(e)}


def _execute_balance_game(message: str, context: Optional[Dict],
                          provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute a game balance action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.BALANCE_TEST,
            prompt=message,
            system_prompt=(
                "You are a game balance expert. Analyze the difficulty curve, "
                "suggest adjustments, and provide concrete tuning values."
            ),
            config=GenerationConfig(temperature=0.4, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "balance_game",
            "result": {
                "suggestions": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "balance_game", "error": str(e)}


def _execute_list_scene(message: str, context: Optional[Dict]) -> Dict[str, Any]:
    """List entities in the current scene."""
    return {
        "success": True,
        "action": "list_scene",
        "result": {
            "scene_id": "main_scene",
            "entity_count": 0,
            "entities": [],
            "message": "No entities in the current scene. Use 'create entity' to add one.",
        },
    }


def _execute_editor_status(message: str, context: Optional[Dict]) -> Dict[str, Any]:
    """Get the current editor status."""
    return {
        "success": True,
        "action": "editor_status",
        "result": {
            "mode": "idle",
            "active_scene": "main_scene",
            "entity_count": 0,
            "available_actions": list(ACTION_KEYWORDS.keys()),
        },
    }


def _execute_create_dialogue(message: str, context: Optional[Dict],
                             provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute a dialogue creation action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.DIALOGUE,
            prompt=message,
            system_prompt=(
                "You are a game narrative expert. Create branching dialogue "
                "with multiple choices. Format as JSON with 'nodes' array, "
                "each node has 'id', 'speaker', 'text', 'choices' array."
            ),
            config=GenerationConfig(temperature=0.7, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "create_dialogue",
            "result": {
                "dialogue": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "create_dialogue", "error": str(e)}


def _execute_generate_level(message: str, context: Optional[Dict],
                            provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute a level generation action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.WORLD_BUILDING,
            prompt=message,
            system_prompt=(
                "You are a level design expert. Generate a level layout "
                "with platforms, obstacles, enemies, and collectibles. "
                "Format as JSON with 'width', 'height', 'tiles' array, "
                "'entities' array, 'spawn_point' object."
            ),
            config=GenerationConfig(temperature=0.6, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "generate_level",
            "result": {
                "level_data": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "generate_level", "error": str(e)}


def _execute_create_animation(message: str, context: Optional[Dict],
                              provider_id: str = None, model_id: str = None) -> Dict[str, Any]:
    """Execute an animation creation action through the LLM router."""
    try:
        from sparkai.agent.agent_llm_router import (
            get_llm_router, ModelRequest, TaskType, GenerationConfig,
        )
        # Determine animation type from message
        msg_lower = message.lower()
        if any(w in msg_lower for w in ["walk", "run", "move"]):
            anim_type = "locomotion"
        elif any(w in msg_lower for w in ["attack", "hit", "slash"]):
            anim_type = "combat"
        elif any(w in msg_lower for w in ["idle", "stand", "breath"]):
            anim_type = "idle"
        elif any(w in msg_lower for w in ["jump", "fall", "land"]):
            anim_type = "movement"
        else:
            anim_type = "custom"

        llm_router = get_llm_router()
        model_request = ModelRequest(
            task_type=TaskType.CODE_GEN,
            prompt=(
                f"Create an animation specification for: {message}\n"
                f"Animation type: {anim_type}\n"
                "Format as JSON with 'name', 'duration_frames', "
                "'keyframes' array (each with 'frame', 'bone', 'rotation', 'position'), "
                "'loop' boolean."
            ),
            system_prompt=(
                "You are a game animation expert. Generate animation "
                "keyframe data for game characters and objects."
            ),
            config=GenerationConfig(temperature=0.5, max_tokens=2048),
            use_cache=True,
            provider_id=provider_id,
            model_id=model_id,
        )
        response = llm_router.execute_request(model_request)
        return {
            "success": True,
            "action": "create_animation",
            "result": {
                "animation_type": anim_type,
                "animation_data": response.content,
                "provider": response.provider_id,
                "model": response.model_id,
                "simulated": response.simulated,
            },
        }
    except Exception as e:
        return {"success": False, "action": "create_animation", "error": str(e)}


# Action executor map
ACTION_EXECUTORS = {
    "create_game": _execute_create_game,
    "create_entity": _execute_create_entity,
    "create_scene": _execute_create_scene,
    "generate_code": _execute_generate_code,
    "generate_asset": _execute_generate_asset,
    "analyze_bug": _execute_analyze_bug,
    "balance_game": _execute_balance_game,
    "list_scene": _execute_list_scene,
    "editor_status": _execute_editor_status,
    "create_dialogue": _execute_create_dialogue,
    "generate_level": _execute_generate_level,
    "create_animation": _execute_create_animation,
}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/chat-editor/execute")
async def execute_editor_action(req: EditorActionRequest):
    """Execute a chat-driven editor action.

    The bridge classifies the message into an editor action, routes
    through the LLM router for model responses, and executes the action.
    """
    try:
        # Classify action if not specified
        action_type = req.action_type or _classify_action(req.message)
        executor = ACTION_EXECUTORS.get(action_type)

        if executor is None:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": f"Unknown action type: {action_type}",
                    "available_actions": list(ACTION_EXECUTORS.keys()),
                },
            )

        # Execute the action
        start_time = time.time()
        # Pass provider_id and model_id to executors that support them
        try:
            result = executor(req.message, req.context,
                              provider_id=req.provider_id, model_id=req.model_id)
        except TypeError:
            # Executor doesn't accept provider_id/model_id
            result = executor(req.message, req.context)
        elapsed_ms = (time.time() - start_time) * 1000

        # Build response
        response_data = {
            "action_type": action_type,
            "message": req.message,
            "success": result.get("success", False),
            "result": result.get("result", {}),
            "error": result.get("error"),
            "elapsed_ms": round(elapsed_ms, 1),
            "timestamp": time.time(),
            "session_id": req.session_id,
        }

        # If there's a model response, include routing metadata
        if "result" in result and isinstance(result["result"], dict):
            model_result = result["result"]
            if "provider" in model_result:
                response_data["provider_id"] = model_result["provider"]
                response_data["model_id"] = model_result["model"]
                response_data["simulated"] = model_result.get("simulated", False)

        # Record in history
        _action_history.append({
            "id": str(uuid.uuid4()),
            "session_id": req.session_id,
            "action_type": action_type,
            "message": req.message,
            "success": result.get("success", False),
            "elapsed_ms": round(elapsed_ms, 1),
            "timestamp": time.time(),
        })

        return JSONResponse({
            "status": "success" if result.get("success") else "error",
            "data": response_data,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/chat-editor/actions")
async def list_actions():
    """List all available editor actions with descriptions."""
    actions = [
        {
            "action": "create_game",
            "description": "Create a full playable game from a natural language description",
            "examples": ["Create a platformer game with double jump", "Make a space shooter game"],
        },
        {
            "action": "create_entity",
            "description": "Create a single entity like a character, enemy, item, or obstacle",
            "examples": ["Create a player character with sword", "Add a flying enemy"],
        },
        {
            "action": "create_scene",
            "description": "Create a scene or level from a description",
            "examples": ["Create a forest level with trees", "Design a dungeon scene"],
        },
        {
            "action": "generate_code",
            "description": "Generate game code or scripts from a description",
            "examples": ["Write a player controller script", "Generate enemy AI code"],
        },
        {
            "action": "generate_asset",
            "description": "Generate images, 3D models, or audio assets",
            "examples": ["Generate a castle image", "Create a 3D sword model", "Make a coin pickup sound"],
        },
        {
            "action": "analyze_bug",
            "description": "Analyze and diagnose a bug from a description",
            "examples": ["Player falls through the floor", "Game crashes when collecting items"],
        },
        {
            "action": "balance_game",
            "description": "Balance game difficulty and metrics",
            "examples": ["The game is too hard", "Balance the weapon damage"],
        },
        {
            "action": "list_scene",
            "description": "List entities in the current scene",
            "examples": ["What entities are in the scene?", "List all objects"],
        },
        {
            "action": "editor_status",
            "description": "Get the current editor status and available actions",
            "examples": ["Editor status", "What can you do?"],
        },
        {
            "action": "create_dialogue",
            "description": "Create branching dialogue with multiple choices for NPCs",
            "examples": ["Create NPC dialogue for a shopkeeper", "Write branching conversation"],
        },
        {
            "action": "generate_level",
            "description": "Generate a level layout with platforms, obstacles, and entities",
            "examples": ["Generate a dungeon level", "Create a platformer level layout"],
        },
        {
            "action": "create_animation",
            "description": "Generate animation keyframe data for characters and objects",
            "examples": ["Create a walk cycle animation", "Generate an attack animation"],
        },
    ]
    return JSONResponse({
        "status": "success",
        "data": {"actions": actions, "count": len(actions)},
    })


@router.get("/chat-editor/status")
async def bridge_status():
    """Get the bridge status and action history."""
    return JSONResponse({
        "status": "success",
        "data": {
            "active": True,
            "total_actions": len(_action_history),
            "action_types": list(ACTION_EXECUTORS.keys()),
            "recent_actions": list(_action_history)[-10:],
        },
    })


@router.post("/chat-editor/reset")
async def bridge_reset():
    """Reset the bridge state and clear action history."""
    _action_history.clear()
    return JSONResponse({
        "status": "success",
        "data": {"total_actions": 0},
    })
