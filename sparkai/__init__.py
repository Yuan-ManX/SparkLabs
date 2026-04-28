"""
SparkAI - AI-Native Game Engine Agent Foundation
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentState, AgentRole, ExecutionPlan
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.memory import AgentMemory, MemoryType
from sparkai.agent.toolkit import (
    ToolRegistry, Tool, ToolParameter, Toolset, ToolsetRegistry,
    create_engine_tools, get_toolsets_for_role, get_tools_for_role,
)
from sparkai.agent.orchestrator import AgentOrchestrator
from sparkai.agent.skills.base import Skill, SkillRegistry
from sparkai.agent.skills.template import TemplateSkill, TemplateLibrary, GameTemplate
from sparkai.agent.skills.debug import DebugSkill, DebugProtocol, DebugEntry
from sparkai.agent.studio.directors import CreativeDirector, TechnicalDirector, Producer
from sparkai.agent.studio.leads import GameDesigner, LeadProgrammer, ArtDirector, NarrativeDirector, QALead
from sparkai.agent.studio.specialists import (
    GameplayProgrammer, EngineProgrammer, AIProgrammer,
    LevelDesigner, WorldBuilder, SoundDesigner, Writer, QATester,
)
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

__version__ = "3.0.0"
__all__ = [
    "SparkAgent",
    "AgentCapability",
    "AgentState",
    "AgentRole",
    "LLMProvider",
    "LLMConfig",
    "AgentMemory",
    "MemoryType",
    "ToolRegistry",
    "Tool",
    "ToolParameter",
    "Toolset",
    "ToolsetRegistry",
    "create_engine_tools",
    "get_toolsets_for_role",
    "get_tools_for_role",
    "AgentOrchestrator",
    "Skill",
    "SkillRegistry",
    "TemplateSkill",
    "TemplateLibrary",
    "GameTemplate",
    "DebugSkill",
    "DebugProtocol",
    "DebugEntry",
    "CreativeDirector",
    "TechnicalDirector",
    "Producer",
    "GameDesigner",
    "LeadProgrammer",
    "ArtDirector",
    "NarrativeDirector",
    "QALead",
    "GameplayProgrammer",
    "EngineProgrammer",
    "AIProgrammer",
    "LevelDesigner",
    "WorldBuilder",
    "SoundDesigner",
    "Writer",
    "QATester",
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
