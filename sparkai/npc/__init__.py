"""
SparkAI NPC Package
"""

from sparkai.npc.brain import NPCBrain, EmotionalState, EmotionType, NPCGoal, AttentionTarget
from sparkai.npc.personality import NPCPersonality, PersonalityTraits
from sparkai.npc.behavior import BehaviorTree, BehaviorNode, NodeStatus

__all__ = [
    "NPCBrain",
    "EmotionalState",
    "EmotionType",
    "NPCGoal",
    "AttentionTarget",
    "NPCPersonality",
    "PersonalityTraits",
    "BehaviorTree",
    "BehaviorNode",
    "NodeStatus",
]
