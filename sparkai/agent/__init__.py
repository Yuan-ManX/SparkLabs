"""
SparkAI Agent Package
"""

from sparkai.agent.base import SparkAgent, AgentCapability, AgentState, AgentTask, AgentMessage, AgentRole, ExecutionPlan
from sparkai.agent.llm import LLMProvider, LLMConfig
from sparkai.agent.memory import AgentMemory, MemoryType, MemoryEntry
from sparkai.agent.toolkit import (
    ToolRegistry, Tool, ToolParameter, Toolset, ToolsetRegistry,
    create_engine_tools, create_engine_toolset, create_asset_toolset,
    create_npc_toolset, create_narrative_toolset, create_gameplay_toolset,
    create_code_toolset, create_workflow_toolset, create_testing_toolset,
    create_orchestration_toolset, create_audio_toolset, create_video_toolset,
    get_toolsets_for_role, get_tools_for_role,
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

__all__ = [
    "SparkAgent",
    "AgentCapability",
    "AgentState",
    "AgentTask",
    "AgentMessage",
    "AgentRole",
    "ExecutionPlan",
    "LLMProvider",
    "LLMConfig",
    "AgentMemory",
    "MemoryType",
    "MemoryEntry",
    "ToolRegistry",
    "Tool",
    "ToolParameter",
    "Toolset",
    "ToolsetRegistry",
    "create_engine_tools",
    "create_engine_toolset",
    "create_asset_toolset",
    "create_npc_toolset",
    "create_narrative_toolset",
    "create_gameplay_toolset",
    "create_code_toolset",
    "create_workflow_toolset",
    "create_testing_toolset",
    "create_orchestration_toolset",
    "create_audio_toolset",
    "create_video_toolset",
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
]
