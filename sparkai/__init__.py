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
from sparkai.agent.hooks import HookManager, Hook, HookEvent, HookResult
from sparkai.agent.rules import RuleEngine, Rule, RuleScope, RuleSeverity, RuleViolation
from sparkai.agent.team_orch import TeamOrchestrator, Team, TeamType, TeamConfig
from sparkai.agent.bench import GameBench, BenchResult, BenchDimension
from sparkai.agent.session import SessionManager, AgentSession, SessionState
from sparkai.agent.loop import AgentLoop, Pipeline, ReasoningChain, LoopState, LoopIteration
from sparkai.agent.commands import SlashCommand, CommandRegistry, CommandCategory
from sparkai.agent.memory_v2 import AgentMemorySystem, MemoryLayer, MemoryLayerStore
from sparkai.agent.events import EventBus, Event, EventChannel, Subscription
from sparkai.agent.context import (
    GameContext, GameGenre, PipelinePhase, AssetType,
    EntityRecord, SceneRecord, AssetRecord, PipelineState,
    WorldModel, ContextSnapshot,
)
from sparkai.agent.llm_router import LLMRouter, TaskType, ProviderCapability, ProviderProfile, RoutingDecision
from sparkai.agent.executor import ToolExecutor, ExecutionResult, ExecutionStatus, ChainStep, ChainResult
from sparkai.agent.runtime import AgentRuntime, RuntimeState, RuntimeConfig
from sparkai.agent.protocol import AgentProtocol, ProtocolMessage, MessageType, MessagePriority
from sparkai.agent.skill_forge import SkillForge, SkillBlueprint, SkillEvolution, SkillMaturity
from sparkai.agent.mesh import AgentMesh, AgentNode, Cluster, NodeState, ClusterState
from sparkai.agent.health import HealthChecker, HealthReport, HealthStatus, CheckCategory
from sparkai.agent.game_coder import GameCoder, CodeGenProject, CodeGenPhase, CodeFile, CodeLanguage, get_game_coder
from sparkai.agent.world_builder import WorldBuilder as WorldBuilderAgent, WorldData, WorldPhase, BiomeType, get_world_builder
from sparkai.agent.game_skill import GameSkillSystem, TemplateEntry, DebugEntry, get_game_skill_system
from sparkai.agent.quality_gate import QualityGateSystem, GateVerdict, GateCategory, QualityReport, get_quality_gate_system
from sparkai.agent.workflow_skills import WorkflowSkillSystem, WorkflowSkill, WorkflowCategory, get_workflow_skill_system
from sparkai.agent.agent_session import AgentSessionManager, SessionState, MessageRole, get_agent_session_manager
from sparkai.agent.game_pipeline import GamePipelineSystem, PipelineStage, EvalDimension, get_game_pipeline_system
from sparkai.agent.studio_coordinator import StudioCoordinator, AgentTier, Department, get_studio_coordinator
from sparkai.agent.agent_swarm import AgentSwarm, SwarmRole, ConsensusType, DecompositionStrategy, get_agent_swarm
from sparkai.agent.studio_command import StudioCommandSystem, CommandCategory, get_studio_command_system
from sparkai.agent.game_template import GameTemplateLibrary, GameGenre, TemplateMaturity, get_game_template_library
from sparkai.agent.agent_blueprint import BlueprintEngine, BlueprintState, get_blueprint_engine
from sparkai.agent.agent_playtest import PlaytestEngine, PlaytestStatus, ScenarioType, get_playtest_engine
from sparkai.agent.agent_composer import ComposerEngine, CompositionState, TaskType, get_composer_engine
from sparkai.agent.agent_knowledge import KnowledgeGraph, KnowledgeDomain, get_knowledge_graph
from sparkai.agent.agent_toolchain import ToolChainEngine, ChainStatus, get_toolchain_engine
from sparkai.agent.agent_reflex import ReflexEngine, MetricType, get_reflex_engine
from sparkai.agent.agent_dialogue import DialogueEngine, DialogueType, get_dialogue_engine
from sparkai.agent.agent_asset import AssetPipelineEngine, AssetCategory, get_asset_engine
from sparkai.agent.agent_validator import ValidatorEngine, ValidationSeverity, get_validator_engine
from sparkai.agent.agent_orchestrator import OrchestratorEngine, TaskPriority, get_orchestrator_engine
from sparkai.agent.agent_skill_evolution import SkillEvolutionEngine, SkillDomain, get_skill_evolution_engine
from sparkai.agent.agent_evaluator import GameEvaluatorEngine, EvalDimension, get_game_evaluator
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

__version__ = "17.0.0"
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
    "HookManager",
    "Hook",
    "HookEvent",
    "HookResult",
    "RuleEngine",
    "Rule",
    "RuleScope",
    "RuleSeverity",
    "RuleViolation",
    "TeamOrchestrator",
    "Team",
    "TeamType",
    "TeamConfig",
    "GameBench",
    "BenchResult",
    "BenchDimension",
    "SessionManager",
    "AgentSession",
    "SessionState",
    "AgentLoop",
    "Pipeline",
    "ReasoningChain",
    "LoopState",
    "LoopIteration",
    "SlashCommand",
    "CommandRegistry",
    "CommandCategory",
    "AgentMemorySystem",
    "MemoryLayer",
    "MemoryLayerStore",
    "EventBus",
    "Event",
    "EventChannel",
    "Subscription",
    "GameContext",
    "GameGenre",
    "PipelinePhase",
    "AssetType",
    "EntityRecord",
    "SceneRecord",
    "AssetRecord",
    "PipelineState",
    "WorldModel",
    "ContextSnapshot",
    "LLMRouter",
    "TaskType",
    "ProviderCapability",
    "ProviderProfile",
    "RoutingDecision",
    "ToolExecutor",
    "ExecutionResult",
    "ExecutionStatus",
    "ChainStep",
    "ChainResult",
    "AgentRuntime",
    "RuntimeState",
    "RuntimeConfig",
    "AgentProtocol",
    "ProtocolMessage",
    "MessageType",
    "MessagePriority",
    "SkillForge",
    "SkillBlueprint",
    "SkillEvolution",
    "SkillMaturity",
    "AgentMesh",
    "AgentNode",
    "Cluster",
    "NodeState",
    "ClusterState",
    "HealthChecker",
    "HealthReport",
    "HealthStatus",
    "CheckCategory",
    "GameCoder",
    "CodeGenProject",
    "CodeGenPhase",
    "CodeFile",
    "CodeLanguage",
    "get_game_coder",
    "WorldBuilderAgent",
    "WorldData",
    "WorldPhase",
    "BiomeType",
    "get_world_builder",
    "KnowledgeGraph",
    "KnowledgeDomain",
    "get_knowledge_graph",
    "ToolChainEngine",
    "ChainStatus",
    "get_toolchain_engine",
    "ReflexEngine",
    "MetricType",
    "get_reflex_engine",
    "DialogueEngine",
    "DialogueType",
    "get_dialogue_engine",
    "AssetPipelineEngine",
    "AssetCategory",
    "get_asset_engine",
    "ValidatorEngine",
    "ValidationSeverity",
    "get_validator_engine",
    "OrchestratorEngine",
    "TaskPriority",
    "get_orchestrator_engine",
    "SkillEvolutionEngine",
    "SkillDomain",
    "get_skill_evolution_engine",
    "GameEvaluatorEngine",
    "EvalDimension",
    "get_game_evaluator",
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
