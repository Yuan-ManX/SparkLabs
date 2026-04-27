"""
SparkLabs Backend - NPC Routes
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Optional, List, Any

from sparkai.npc.brain import NPCBrain
from sparkai.npc.personality import NPCPersonality, PersonalityTraits
from sparkai.npc.behavior import BehaviorTree, BehaviorNode

router = APIRouter()

_npcs: Dict[str, NPCBrain] = {}


class NPCCreateRequest(BaseModel):
    npc_id: str = ""
    name: str = "NPC"
    personality_traits: Optional[Dict[str, float]] = None
    background: str = ""
    speech_style: str = "neutral"


class NPCDecideRequest(BaseModel):
    npc_id: str
    context: Optional[Dict[str, Any]] = None


class NPCDialogueRequest(BaseModel):
    npc_id: str
    player_input: str
    context: Optional[Dict[str, Any]] = None


class NPCEmotionRequest(BaseModel):
    npc_id: str
    stimulus: str
    intensity: float = 0.5


class NPCGoalRequest(BaseModel):
    npc_id: str
    name: str
    priority: float = 0.5


class BehaviorTreeRequest(BaseModel):
    npc_id: str
    root_type: str = "selector"


@router.post("/create")
async def create_npc(request: NPCCreateRequest):
    traits = PersonalityTraits()
    if request.personality_traits:
        for key, value in request.personality_traits.items():
            if hasattr(traits, key):
                setattr(traits, key, value)

    personality = NPCPersonality(
        name=request.name,
        traits=traits,
        background=request.background,
        speech_style=request.speech_style,
    )

    brain = NPCBrain(npc_id=request.npc_id, personality=personality)
    _npcs[brain.id] = brain
    return brain.get_status()


@router.get("/list")
async def list_npcs():
    return {"npcs": [npc.get_status() for npc in _npcs.values()]}


@router.get("/{npc_id}")
async def get_npc(npc_id: str):
    npc = _npcs.get(npc_id)
    if npc:
        return npc.get_status()
    return {"error": "NPC not found"}


@router.post("/decide")
async def npc_decide(request: NPCDecideRequest):
    npc = _npcs.get(request.npc_id)
    if not npc:
        return {"error": "NPC not found"}
    decision = await npc.decide(request.context)
    return {"npc_id": request.npc_id, "decision": decision}


@router.post("/dialogue")
async def npc_dialogue(request: NPCDialogueRequest):
    npc = _npcs.get(request.npc_id)
    if not npc:
        return {"error": "NPC not found"}
    response = await npc.generate_dialogue(request.player_input, request.context)
    return {"npc_id": request.npc_id, "response": response}


@router.post("/emotion")
async def npc_emotion(request: NPCEmotionRequest):
    npc = _npcs.get(request.npc_id)
    if not npc:
        return {"error": "NPC not found"}
    npc.update_emotion(request.stimulus, request.intensity)
    return {"npc_id": request.npc_id, "emotion": npc.emotional_state.emotion.value}


@router.post("/goal")
async def npc_add_goal(request: NPCGoalRequest):
    npc = _npcs.get(request.npc_id)
    if not npc:
        return {"error": "NPC not found"}
    npc.add_goal(request.name, request.priority)
    return {"npc_id": request.npc_id, "goals": [{"name": g.name, "priority": g.priority} for g in npc.goals]}


@router.post("/behavior-tree")
async def set_behavior_tree(request: BehaviorTreeRequest):
    npc = _npcs.get(request.npc_id)
    if not npc:
        return {"error": "NPC not found"}
    tree = BehaviorTree()
    root = BehaviorNode(name="Root", node_type=request.root_type)
    tree.set_root(root)
    npc.set_behavior_tree(tree)
    return {"npc_id": request.npc_id, "behavior_tree": tree.to_dict()}


@router.delete("/{npc_id}")
async def delete_npc(npc_id: str):
    if npc_id in _npcs:
        del _npcs[npc_id]
        return {"success": True}
    return {"error": "NPC not found"}
