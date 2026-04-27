"""
SparkLabs Backend - Narrative Routes
"""

from fastapi import APIRouter
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
    story = StoryGraph(name=request.name)
    _stories[story.id] = story
    return story.to_dict()


@router.get("/story/list")
async def list_stories():
    return {"stories": [s.to_dict() for s in _stories.values()]}


@router.get("/story/{story_id}")
async def get_story(story_id: str):
    story = _stories.get(story_id)
    if story:
        return story.to_dict()
    return {"error": "Story not found"}


@router.post("/story/node/create")
async def create_story_node(request: StoryNodeCreateRequest):
    story = _stories.get(request.story_id)
    if not story:
        return {"error": "Story not found"}
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
    return node.to_dict()


@router.post("/story/advance")
async def advance_story(request: StoryAdvanceRequest):
    story = _stories.get(request.story_id)
    if not story:
        return {"error": "Story not found"}
    next_node = story.advance(request.choice_index)
    if next_node:
        return next_node.to_dict()
    return {"error": "No next node available"}


@router.get("/story/{story_id}/current")
async def get_current_node(story_id: str):
    story = _stories.get(story_id)
    if not story:
        return {"error": "Story not found"}
    current = story.get_current_node()
    if current:
        return current.to_dict()
    return {"error": "No current node"}


@router.post("/quest/generate")
async def generate_quest(request: QuestGenerateRequest):
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
    return quest


@router.get("/quest/templates")
async def list_quest_templates():
    return {"templates": _quest_generator.list_templates()}
