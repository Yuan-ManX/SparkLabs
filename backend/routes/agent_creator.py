"""
SparkLabs Backend - Agent Autonomous Creator & Interaction Loop Routes

API endpoints for autonomous content creation (level blueprints,
quest definitions, NPC profiles, generation stats) and interaction
loop engine (perception-action cycles, state management, history).
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for autonomous creator
_generated_content: Dict[str, Dict[str, Any]] = {}
_creator_stats: Dict[str, Any] = {
    "total_generated": 0,
    "by_category": {},
    "avg_complexity": 0.0,
    "total_seeds_used": 0,
}

# In-memory storage for interaction loop
_current_loop_state: Dict[str, Any] = {
    "phase": "IDLE",
    "cycle_count": 0,
    "last_action": None,
    "state": "initialized",
}
_cycle_history: List[Dict[str, Any]] = []


COMPLEXITY_MAP: Dict[str, float] = {
    "simple": 0.25,
    "moderate": 0.5,
    "complex": 0.75,
    "epic": 1.0,
}


class GenerateRequest(BaseModel):
    category: str = "level"
    theme: str = "default"
    complexity: str = "moderate"
    seed: str = "42"


class EnvironmentStateRequest(BaseModel):
    environment_state: Dict[str, Any] = {}


@router.post("/creator/generate")
async def generate_content(request: GenerateRequest):
    try:
        content_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        category = request.category
        theme = request.theme
        complexity_str = request.complexity.lower()
        complexity = COMPLEXITY_MAP.get(complexity_str, 0.5)
        seed = int(request.seed) if request.seed.isdigit() else 42

        content: Dict[str, Any] = {
            "content_id": content_id,
            "category": category,
            "theme": theme,
            "complexity": complexity,
            "seed": seed,
            "created_at": timestamp,
        }

        if category == "level":
            content["level_blueprint"] = {
                "name": f"{theme.capitalize()} Level",
                "width": int(10 + complexity * 20),
                "height": int(10 + complexity * 20),
                "tile_count": int((10 + complexity * 20) ** 2 // 2),
                "regions": [
                    {"name": "spawn", "x": 0, "y": 0, "width": 5, "height": 5},
                    {"name": "objective", "x": 5, "y": 5, "width": 5, "height": 5},
                ],
                "difficulty": round(complexity, 2),
            }
        elif category == "quest":
            content["quest_definition"] = {
                "title": f"The {theme.capitalize()} Quest",
                "description": f"A quest generated with seed {seed} and complexity {complexity}",
                "objectives": [
                    {"id": 1, "description": f"Explore the {theme} realm", "type": "EXPLORE"},
                    {"id": 2, "description": f"Defeat the {theme} guardian", "type": "COMBAT"},
                    {"id": 3, "description": f"Collect {theme} artifacts", "type": "COLLECT"},
                ],
                "rewards": {
                    "experience": int(100 * complexity),
                    "items": [f"{theme}_token", f"{theme}_gem"],
                },
                "difficulty": round(complexity, 2),
            }
        elif category == "npc":
            content["npc_profile"] = {
                "name": f"{theme.capitalize()} NPC",
                "role": ["MERCHANT", "QUEST_GIVER", "ALLY", "ENEMY"][seed % 4],
                "traits": {
                    "friendliness": round(0.3 + (seed % 70) / 100, 2),
                    "aggression": round(0.1 + (seed % 50) / 100, 2),
                    "intelligence": round(0.4 + (seed % 60) / 100, 2),
                },
                "dialogue_lines": [
                    f"Welcome to the {theme} area!",
                    f"I have a task for you in {theme}.",
                ],
                "inventory": [f"{theme}_item_{i}" for i in range(1, 4)],
            }
        else:
            content["generated"] = {
                "type": category,
                "name": f"{theme.capitalize()} {category.capitalize()}",
                "description": f"Generated {category} with theme '{theme}'",
                "attributes": {
                    "complexity": complexity,
                    "seed": seed,
                },
            }

        _generated_content[content_id] = content

        _creator_stats["total_generated"] += 1
        _creator_stats["by_category"][category] = _creator_stats["by_category"].get(category, 0) + 1
        _creator_stats["avg_complexity"] = (
            (_creator_stats["avg_complexity"] * (_creator_stats["total_generated"] - 1) + complexity)
            / _creator_stats["total_generated"]
        )
        _creator_stats["total_seeds_used"] += 1

        return {
            "status": "success",
            "data": content,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/creator/stats")
async def get_creator_stats():
    try:
        return {
            "status": "success",
            "data": _creator_stats,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/creator/content/all")
async def get_all_content():
    try:
        items = list(_generated_content.values())
        items.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {
            "status": "success",
            "items": items,
            "total_count": len(items),
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/creator/content/{content_id}")
async def get_content(content_id: str):
    try:
        content = _generated_content.get(content_id)

        if not content:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": f"Content not found: {content_id}"},
            )

        return {
            "status": "success",
            "data": content,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/loop/cycle")
async def run_interaction_cycle(request: EnvironmentStateRequest):
    try:
        cycle_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        env_state = request.environment_state
        cycle_count = _current_loop_state["cycle_count"] + 1

        phases = ["PERCEIVE", "DECIDE", "ACT", "OBSERVE"]
        current_phase = phases[cycle_count % len(phases)]

        perception_frame = {
            "entities_detected": len(env_state.get("entities", [])),
            "events_detected": len(env_state.get("events", [])),
            "threats": env_state.get("threats", []),
            "opportunities": env_state.get("opportunities", []),
            "confidence": round(0.7 + (cycle_count % 30) / 100, 2),
        }

        action_decision = {
            "action_type": ["MOVE", "INTERACT", "ATTACK", "DEFEND", "IDLE"][cycle_count % 5],
            "target": env_state.get("target", "none"),
            "priority": round(0.5 + (cycle_count % 50) / 100, 2),
            "reasoning": f"Decided based on phase {current_phase} with {len(env_state.get('entities', []))} entities",
        }

        execution_result = {
            "success": True,
            "outcome": f"Action executed successfully in phase {current_phase}",
            "state_changes": {
                "position_updated": True,
                "resources_consumed": int(cycle_count * 0.5),
                "new_entities": cycle_count % 3,
            },
            "duration_ms": round(50 + (cycle_count * 10), 2),
        }

        cycle = {
            "cycle_id": cycle_id,
            "cycle_number": cycle_count,
            "phase": current_phase,
            "perception_frame": perception_frame,
            "action_decision": action_decision,
            "execution_result": execution_result,
            "timestamp": timestamp,
        }

        _current_loop_state["phase"] = current_phase
        _current_loop_state["cycle_count"] = cycle_count
        _current_loop_state["last_action"] = action_decision["action_type"]
        _current_loop_state["state"] = "active"

        _cycle_history.append(cycle)

        return {
            "status": "success",
            "data": cycle,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/loop/state")
async def get_loop_state():
    try:
        return {
            "status": "success",
            "data": _current_loop_state,
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/loop/history")
async def get_cycle_history(limit: int = Query(default=20)):
    try:
        history = _cycle_history[-limit:]

        return {
            "status": "success",
            "data": {
                "cycles": history,
                "total_cycles": len(_cycle_history),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/loop/reset")
async def reset_loop():
    try:
        _current_loop_state["phase"] = "IDLE"
        _current_loop_state["cycle_count"] = 0
        _current_loop_state["last_action"] = None
        _current_loop_state["state"] = "reset"

        return {
            "status": "success",
            "data": {
                "message": "Interaction loop reset successfully",
                "state": _current_loop_state,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )