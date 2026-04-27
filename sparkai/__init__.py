"""
SparkAI - AI-Native Game Engine Agent Foundation
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentState, AgentRole, ExecutionPlan
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.memory import AgentMemory, MemoryType
from sparkai.agent.toolkit import ToolRegistry, Tool, create_engine_tools
from sparkai.agent.orchestrator import AgentOrchestrator
from sparkai.engine.engine import SparkEngine, Scene, SceneEntity
from sparkai.engine.ecs import (
    Component,
    ComponentRegistry,
    Entity,
    EntityManager,
    System,
    SystemPriority,
    SystemRegistry,
    SystemScheduler,
    World,
)
from sparkai.engine.ecs.components import (
    Transform,
    Renderable,
    SpriteRenderer,
    TextRenderer,
    PhysicsBody,
    Collider,
    Camera,
    AudioSource,
    Animator,
    InputReceiver,
    AIBrain,
    Script,
    Tween,
)
from sparkai.engine.ecs.systems import (
    TransformSystem,
    PhysicsSystem,
    RenderSystem,
    AnimationSystem,
    AudioSystem,
    InputSystem,
    AISystem,
    TweenSystem,
    ScriptSystem,
    CollisionSystem,
)
from sparkai.engine.ecs.resource import (
    Resource,
    ResourceManager,
    ResourceType,
)
from sparkai.workflow.graph import WorkflowGraph, WorkflowNode
from sparkai.workflow.executor import WorkflowExecutor
from sparkai.workflow.registry import NodeRegistry
from sparkai.npc.brain import NPCBrain
from sparkai.npc.personality import NPCPersonality, PersonalityTraits
from sparkai.npc.behavior import BehaviorTree, BehaviorNode
from sparkai.narrative.story import StoryGraph, StoryNode
from sparkai.narrative.quest import QuestGenerator, QuestTemplate
from sparkai.team.director import TeamDirector
from sparkai.team.lead import TeamLead
from sparkai.team.specialist import TeamSpecialist
from sparkai.team.quality import QualityGate, QualityStandard
from sparkai.config import SparkAIConfig

__version__ = "2.0.0"
__all__ = [
    "SparkAgent",
    "AgentCapability",
    "AgentState",
    "LLMProvider",
    "LLMConfig",
    "AgentMemory",
    "MemoryType",
    "ToolRegistry",
    "Tool",
    "create_engine_tools",
    "AgentOrchestrator",
    "SparkEngine",
    "Scene",
    "SceneEntity",
    "Component",
    "ComponentRegistry",
    "Entity",
    "EntityManager",
    "System",
    "SystemPriority",
    "SystemRegistry",
    "SystemScheduler",
    "World",
    "Transform",
    "Renderable",
    "SpriteRenderer",
    "TextRenderer",
    "PhysicsBody",
    "Collider",
    "Camera",
    "AudioSource",
    "Animator",
    "InputReceiver",
    "AIBrain",
    "Script",
    "Tween",
    "TransformSystem",
    "PhysicsSystem",
    "RenderSystem",
    "AnimationSystem",
    "AudioSystem",
    "InputSystem",
    "AISystem",
    "TweenSystem",
    "ScriptSystem",
    "CollisionSystem",
    "Resource",
    "ResourceManager",
    "ResourceType",
    "WorkflowGraph",
    "WorkflowNode",
    "WorkflowExecutor",
    "NodeRegistry",
    "NPCBrain",
    "NPCPersonality",
    "PersonalityTraits",
    "BehaviorTree",
    "BehaviorNode",
    "StoryGraph",
    "StoryNode",
    "QuestGenerator",
    "QuestTemplate",
    "TeamDirector",
    "TeamLead",
    "TeamSpecialist",
    "QualityGate",
    "QualityStandard",
    "SparkAIConfig",
]
