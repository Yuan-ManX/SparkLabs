"""
SparkLabs Backend - Agent Game Creation Routes

API endpoints for natural-language game creation including
description parsing, project management, blueprint refinement,
and genre templates.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

router = APIRouter()

# In-memory storage for game projects
_projects: Dict[str, Dict[str, Any]] = {}

# Game genre templates
_genres: List[str] = [
    "rpg", "platformer", "puzzle", "strategy",
    "simulation", "action", "adventure", "shooter",
    "racing", "sports", "roguelike", "sandbox",
]
_mechanics_list: List[str] = [
    "turn-based-combat", "real-time-combat", "physics-puzzle",
    "resource-management", "dialogue-tree", "crafting",
    "stealth", "exploration", "procedural-generation",
    "skill-tree", "quest-system", "inventory-system",
]
_visual_styles: List[str] = [
    "pixel-art", "low-poly", "cel-shaded", "realistic",
    "stylized", "voxel", "hand-drawn", "isometric",
    "top-down", "side-scrolling", "first-person", "third-person",
]


class ParseDescriptionRequest(BaseModel):
    description: str
    target_platform: str = "web"


class CreateProjectRequest(BaseModel):
    name: str
    genre: str
    description: str
    mechanics: List[str]
    visual_style: str


class RefineProjectRequest(BaseModel):
    feedback: str
    aspect: str = "gameplay"


@router.post("/game-creation/parse")
async def parse_game_description(request: ParseDescriptionRequest):
    try:
        description_lower = request.description.lower()

        detected_genre = "adventure"
        for genre in _genres:
            if genre in description_lower:
                detected_genre = genre
                break

        detected_mechanics = [
            m for m in _mechanics_list
            if any(word in description_lower for word in m.replace("-", " ").split("-"))
        ]
        if not detected_mechanics:
            detected_mechanics = ["exploration"]

        detected_style = "stylized"
        for style in _visual_styles:
            if style.replace("-", " ") in description_lower:
                detected_style = style
                break

        blueprint = {
            "genre": detected_genre,
            "mechanics": detected_mechanics,
            "visual_style": detected_style,
            "target_platform": request.target_platform,
            "estimated_complexity": "medium",
            "core_loop": f"Players explore the {detected_genre} world using {', '.join(detected_mechanics)} mechanics.",
            "suggested_features": [
                "main_menu",
                "settings_menu",
                "save_system",
                "audio_system",
            ],
            "description_summary": request.description[:200],
        }

        return {
            "status": "success",
            "data": {
                "blueprint": blueprint,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/game-creation/create")
async def create_game_project(request: CreateProjectRequest):
    try:
        project_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        blueprint = {
            "name": request.name,
            "genre": request.genre,
            "description": request.description,
            "mechanics": request.mechanics,
            "visual_style": request.visual_style,
            "scenes": [],
            "assets": [],
            "settings": {
                "resolution": "1920x1080",
                "target_fps": 60,
                "physics_enabled": True,
            },
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        project = {
            "id": project_id,
            "name": request.name,
            "genre": request.genre,
            "status": "created",
            "blueprint": blueprint,
            "created_at": timestamp,
            "updated_at": timestamp,
        }

        _projects[project_id] = project

        return {
            "status": "success",
            "data": {
                "project_id": project_id,
                "blueprint": blueprint,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-creation/projects")
async def list_projects():
    try:
        projects_list = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "genre": p.get("genre"),
                "status": p.get("status"),
                "created_at": p.get("created_at"),
            }
            for p in _projects.values()
        ]

        return {
            "status": "success",
            "data": {
                "projects": projects_list,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-creation/project/{project_id}")
async def get_project(project_id: str):
    try:
        project = _projects.get(project_id)
        if project:
            return {"status": "success", "data": {"project": project}}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Project not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/game-creation/project/{project_id}/refine")
async def refine_project(project_id: str, request: RefineProjectRequest):
    try:
        project = _projects.get(project_id)
        if not project:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Project not found"},
            )

        timestamp = datetime.utcnow().isoformat()
        blueprint = project.get("blueprint", {})

        if request.aspect == "gameplay":
            blueprint["mechanics"] = list(
                set(blueprint.get("mechanics", []) + ["refined-mechanic"])
            )
        elif request.aspect == "visual":
            blueprint["visual_style"] = "refined-stylized"
        elif request.aspect == "narrative":
            blueprint["description"] = (
                blueprint.get("description", "") + f"\n[Refined]: {request.feedback}"
            )

        blueprint["feedback_history"] = blueprint.get("feedback_history", [])
        blueprint["feedback_history"].append({
            "feedback": request.feedback,
            "aspect": request.aspect,
            "timestamp": timestamp,
        })
        blueprint["updated_at"] = timestamp

        project["blueprint"] = blueprint
        project["updated_at"] = timestamp
        project["status"] = "refined"

        return {
            "status": "success",
            "data": {
                "updated_blueprint": blueprint,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/game-creation/templates")
async def get_templates():
    try:
        return {
            "status": "success",
            "data": {
                "genres": _genres,
                "mechanics": _mechanics_list,
                "visual_styles": _visual_styles,
            },
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )