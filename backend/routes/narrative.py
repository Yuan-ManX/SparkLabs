"""
SparkLabs Backend - Narrative Routes
"""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from sparkai.narrative.story import StoryGraph, StoryNode, StoryNodeType
from sparkai.narrative.quest import QuestGenerator, QuestType

router = APIRouter()

_stories: Dict[str, StoryGraph] = {}
_quest_generator = QuestGenerator()


class StoryCreateRequest(BaseModel):
    name: str = "Untitled Story"


class StoryNodeCreateRequest(BaseModel):
    story_id: str
    name: str = "Story Node"
    node_type: str = "plot_point"
    content: str = ""
    possible_next: List[str] = []


class StoryAdvanceRequest(BaseModel):
    story_id: str
    choice_index: int = 0


class QuestGenerateRequest(BaseModel):
    template: str = "hunt"
    name: Optional[str] = None
    quest_type: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@router.post("/story/create")
async def create_story(request: StoryCreateRequest):
    try:
        story = StoryGraph(name=request.name)
        _stories[story.id] = story
        return {"status": "success", "data": story.to_dict()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/story/list")
async def list_stories():
    try:
        return {
            "status": "success",
            "data": {"stories": [s.to_dict() for s in _stories.values()]},
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/story/{story_id}")
async def get_story(story_id: str):
    try:
        story = _stories.get(story_id)
        if story:
            return {"status": "success", "data": story.to_dict()}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "Story not found"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/story/node/create")
async def create_story_node(request: StoryNodeCreateRequest):
    try:
        story = _stories.get(request.story_id)
        if not story:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Story not found"},
            )
        try:
            node_type = StoryNodeType(request.node_type)
        except ValueError:
            node_type = StoryNodeType.PLOT_POINT
        node = StoryNode(
            name=request.name,
            node_type=node_type,
            content=request.content,
            possible_next=request.possible_next,
        )
        story.add_node(node)
        return {"status": "success", "data": node.to_dict()}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/story/advance")
async def advance_story(request: StoryAdvanceRequest):
    try:
        story = _stories.get(request.story_id)
        if not story:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Story not found"},
            )
        next_node = story.advance(request.choice_index)
        if next_node:
            return {"status": "success", "data": next_node.to_dict()}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No next node available"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/story/{story_id}/current")
async def get_current_node(story_id: str):
    try:
        story = _stories.get(story_id)
        if not story:
            return JSONResponse(
                status_code=404,
                content={"status": "error", "message": "Story not found"},
            )
        current = story.get_current_node()
        if current:
            return {"status": "success", "data": current.to_dict()}
        return JSONResponse(
            status_code=404,
            content={"status": "error", "message": "No current node"},
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.post("/quest/generate")
async def generate_quest(request: QuestGenerateRequest):
    try:
        quest_type = None
        if request.quest_type:
            try:
                quest_type = QuestType(request.quest_type)
            except ValueError:
                pass
        quest = _quest_generator.generate_quest(
            template_name=request.template,
            name=request.name,
            quest_type=quest_type,
            context=request.context,
        )
        return {"status": "success", "data": quest}
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )


@router.get("/quest/templates")
async def list_quest_templates():
    try:
        return {
            "status": "success",
            "data": {"templates": _quest_generator.list_templates()},
        }
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)},
        )