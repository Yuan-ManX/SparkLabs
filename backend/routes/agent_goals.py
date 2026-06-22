"""
SparkLabs Backend - Agent Goals Routes

API endpoints for goal management including
goal creation, decomposition, and active goal tracking.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for goals
_goals: Dict[str, Dict[str, Any]] = {}


class GoalCreateRequest(BaseModel):
    agent_id: str = ""
    name: str = ""
    description: str = ""
    priority: float = 0.5
    parent_goal_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class GoalDecomposeRequest(BaseModel):
    strategy: str = "sequential"
    max_sub_goals: int = 5


@router.post("/goals/create")
async def create_goal(request: GoalCreateRequest):
    try:
        goal_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        goal = {
            "id": goal_id,
            "agent_id": request.agent_id,
            "name": request.name,
            "description": request.description,
            "priority": request.priority,
            "parent_goal_id": request.parent_goal_id,
            "metadata": request.metadata or {},
            "status": "active",
            "sub_goals": [],
            "progress": 0.0,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _goals[goal_id] = goal

        if request.parent_goal_id and request.parent_goal_id in _goals:
            _goals[request.parent_goal_id]["sub_goals"].append(goal_id)

        return {"status": "success", "data": goal}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/goals/active")
async def list_active_goals():
    try:
        active_goals = [g for g in _goals.values() if g.get("status") == "active"]
        active_goals = sorted(
            active_goals, key=lambda g: g.get("priority", 0), reverse=True
        )

        return {
            "status": "success",
            "data": {
                "goals": active_goals,
                "total_count": len(_goals),
                "active_count": len(active_goals),
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/goals/{goal_id}")
async def get_goal(goal_id: str):
    try:
        goal = _goals.get(goal_id)
        if goal:
            return {"status": "success", "data": goal}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Goal not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/goals/{goal_id}/decompose")
async def decompose_goal(goal_id: str, request: GoalDecomposeRequest):
    try:
        goal = _goals.get(goal_id)
        if not goal:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Goal not found"},
            )

        timestamp = datetime.utcnow().isoformat()
        sub_goals = []

        for i in range(request.max_sub_goals):
            sub_id = str(uuid.uuid4())
            sub_goal = {
                "id": sub_id,
                "agent_id": goal.get("agent_id", ""),
                "name": f"{goal.get('name', 'Goal')} - Sub-step {i + 1}",
                "description": f"Sub-goal derived from {goal.get('name', 'goal')}",
                "priority": goal.get("priority", 0.5) * (1.0 - i * 0.15),
                "parent_goal_id": goal_id,
                "metadata": {"strategy": request.strategy, "step": i + 1},
                "status": "active",
                "sub_goals": [],
                "progress": 0.0,
                "created_at": timestamp,
                "updated_at": timestamp,
            }
            _goals[sub_id] = sub_goal
            sub_goals.append(sub_id)

        goal["sub_goals"].extend(sub_goals)
        goal["updated_at"] = timestamp

        return {
            "status": "success",
            "data": {
                "goal_id": goal_id,
                "sub_goals_created": len(sub_goals),
                "sub_goal_ids": sub_goals,
                "strategy": request.strategy,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )