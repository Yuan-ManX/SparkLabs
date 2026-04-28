"""
SparkAI Agent - Team Orchestration

Coordinated multi-agent workflows for game development.
Teams of agents work together on complex features with
defined roles, communication channels, and quality gates.

Team Types:
  - combat: Gameplay + AI + Animation + Audio
  - narrative: Story + NPC + Quest + Dialogue
  - ui: UX + Art + Programming
  - level: World + Level + AI + Physics
  - audio: Sound + Music + Voice
  - release: QA + Performance + DevOps
  - polish: Art + Animation + VFX + Audio
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from sparkai.agent.base import SparkAgent, AgentCapability, AgentRole, AgentTask
from sparkai.agent.orchestrator import AgentOrchestrator, DelegationResult


class TeamType(Enum):
    COMBAT = "combat"
    NARRATIVE = "narrative"
    UI = "ui"
    LEVEL = "level"
    AUDIO = "audio"
    RELEASE = "release"
    POLISH = "polish"
    CUSTOM = "custom"


@dataclass
class TeamConfig:
    team_type: TeamType
    name: str = ""
    description: str = ""
    max_concurrent: int = 3
    quality_gates: List[str] = field(default_factory=list)
    required_capabilities: List[AgentCapability] = field(default_factory=list)


@dataclass
class TeamTask:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    team_type: TeamType = TeamType.CUSTOM
    subtasks: List[AgentTask] = field(default_factory=list)
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    result: Optional[Any] = None


_TEAM_CONFIGS: Dict[TeamType, TeamConfig] = {
    TeamType.COMBAT: TeamConfig(
        team_type=TeamType.COMBAT,
        name="Combat Team",
        description="Coordinates combat system development",
        max_concurrent=3,
        quality_gates=["combat_balance", "input_responsiveness", "ai_behavior"],
        required_capabilities=[
            AgentCapability.GAMEPLAY_DESIGN,
            AgentCapability.CODE_GENERATION,
            AgentCapability.NPC_CONTROL,
        ],
    ),
    TeamType.NARRATIVE: TeamConfig(
        team_type=TeamType.NARRATIVE,
        name="Narrative Team",
        description="Coordinates story and NPC development",
        max_concurrent=3,
        quality_gates=["character_consistency", "quest_flow", "dialogue_quality"],
        required_capabilities=[
            AgentCapability.NARRATIVE_GENERATION,
            AgentCapability.NPC_CONTROL,
        ],
    ),
    TeamType.UI: TeamConfig(
        team_type=TeamType.UI,
        name="UI Team",
        description="Coordinates user interface development",
        max_concurrent=2,
        quality_gates=["accessibility", "responsiveness", "usability"],
        required_capabilities=[
            AgentCapability.CODE_GENERATION,
            AgentCapability.ASSET_GENERATION,
        ],
    ),
    TeamType.LEVEL: TeamConfig(
        team_type=TeamType.LEVEL,
        name="Level Design Team",
        description="Coordinates level and world building",
        max_concurrent=3,
        quality_gates=["playability", "performance", "visual_quality"],
        required_capabilities=[
            AgentCapability.WORLD_BUILDING,
            AgentCapability.GAMEPLAY_DESIGN,
            AgentCapability.ASSET_GENERATION,
        ],
    ),
    TeamType.AUDIO: TeamConfig(
        team_type=TeamType.AUDIO,
        name="Audio Team",
        description="Coordinates audio and music production",
        max_concurrent=2,
        quality_gates=["audio_quality", "mix_balance", "spatial_accuracy"],
        required_capabilities=[
            AgentCapability.AUDIO_GENERATION,
        ],
    ),
    TeamType.RELEASE: TeamConfig(
        team_type=TeamType.RELEASE,
        name="Release Team",
        description="Coordinates QA, optimization, and deployment",
        max_concurrent=3,
        quality_gates=["test_coverage", "performance_budget", "crash_free_rate"],
        required_capabilities=[
            AgentCapability.QUALITY_REVIEW,
            AgentCapability.TESTING,
            AgentCapability.DEPLOYMENT,
        ],
    ),
    TeamType.POLISH: TeamConfig(
        team_type=TeamType.POLISH,
        name="Polish Team",
        description="Coordinates visual and audio polish",
        max_concurrent=3,
        quality_gates=["visual_fidelity", "animation_smoothness", "audio_sync"],
        required_capabilities=[
            AgentCapability.ASSET_GENERATION,
            AgentCapability.AUDIO_GENERATION,
        ],
    ),
}


class Team:
    """
    A coordinated group of agents working on a shared objective.
    Teams decompose tasks into subtasks, assign them to
    appropriate agents, and verify results through quality gates.
    """

    def __init__(
        self,
        team_type: TeamType,
        orchestrator: AgentOrchestrator,
        config: Optional[TeamConfig] = None,
    ):
        self.id = str(uuid.uuid4())
        self.team_type = team_type
        self.orchestrator = orchestrator
        self.config = config or _TEAM_CONFIGS.get(team_type, TeamConfig(team_type=team_type))
        self._tasks: List[TeamTask] = []
        self._active: bool = False
        self._results: List[Dict[str, Any]] = []

    def decompose_task(self, title: str, description: str) -> TeamTask:
        """
        Decompose a high-level task into subtasks for team members.
        Each team type has a standard decomposition pattern.
        """
        team_task = TeamTask(
            title=title,
            description=description,
            team_type=self.team_type,
        )

        if self.team_type == TeamType.COMBAT:
            team_task.subtasks = [
                AgentTask(title="Design combat mechanics", description=f"Design combat system for: {description}"),
                AgentTask(title="Implement combat code", description=f"Implement combat logic for: {description}"),
                AgentTask(title="Create AI behaviors", description=f"Create AI combat behaviors for: {description}"),
                AgentTask(title="Add combat effects", description=f"Add visual/audio effects for: {description}"),
                AgentTask(title="Balance testing", description=f"Test and balance combat for: {description}"),
            ]
        elif self.team_type == TeamType.NARRATIVE:
            team_task.subtasks = [
                AgentTask(title="Write story outline", description=f"Create story outline for: {description}"),
                AgentTask(title="Design characters", description=f"Design characters for: {description}"),
                AgentTask(title="Create dialogue", description=f"Write dialogue for: {description}"),
                AgentTask(title="Build quest system", description=f"Build quest system for: {description}"),
                AgentTask(title="Test narrative flow", description=f"Test narrative flow for: {description}"),
            ]
        elif self.team_type == TeamType.UI:
            team_task.subtasks = [
                AgentTask(title="Design UI layout", description=f"Design UI layout for: {description}"),
                AgentTask(title="Implement UI code", description=f"Implement UI components for: {description}"),
                AgentTask(title="Create UI assets", description=f"Create visual assets for: {description}"),
                AgentTask(title="Test usability", description=f"Test UI usability for: {description}"),
            ]
        elif self.team_type == TeamType.LEVEL:
            team_task.subtasks = [
                AgentTask(title="Design level layout", description=f"Design level layout for: {description}"),
                AgentTask(title="Build world geometry", description=f"Build world geometry for: {description}"),
                AgentTask(title="Place entities", description=f"Place entities and NPCs for: {description}"),
                AgentTask(title="Configure AI paths", description=f"Configure AI navigation for: {description}"),
                AgentTask(title="Playtest level", description=f"Playtest level for: {description}"),
            ]
        elif self.team_type == TeamType.AUDIO:
            team_task.subtasks = [
                AgentTask(title="Design audio landscape", description=f"Design audio for: {description}"),
                AgentTask(title="Generate sound effects", description=f"Generate SFX for: {description}"),
                AgentTask(title="Create music", description=f"Create music for: {description}"),
                AgentTask(title="Mix and master", description=f"Mix audio for: {description}"),
            ]
        elif self.team_type == TeamType.RELEASE:
            team_task.subtasks = [
                AgentTask(title="Run test suite", description=f"Run tests for: {description}"),
                AgentTask(title="Performance audit", description=f"Audit performance for: {description}"),
                AgentTask(title="Bug triage", description=f"Triage bugs for: {description}"),
                AgentTask(title="Build release", description=f"Build release for: {description}"),
            ]
        elif self.team_type == TeamType.POLISH:
            team_task.subtasks = [
                AgentTask(title="Visual polish", description=f"Polish visuals for: {description}"),
                AgentTask(title="Animation refinement", description=f"Refine animations for: {description}"),
                AgentTask(title="VFX additions", description=f"Add VFX for: {description}"),
                AgentTask(title="Audio sync", description=f"Sync audio for: {description}"),
            ]
        else:
            team_task.subtasks = [
                AgentTask(title=title, description=description),
            ]

        self._tasks.append(team_task)
        return team_task

    async def execute(self, team_task: TeamTask) -> List[DelegationResult]:
        """
        Execute a team task by delegating subtasks to agents.
        Subtasks run with concurrency control.
        """
        self._active = True
        team_task.status = "executing"

        semaphore = asyncio.Semaphore(self.config.max_concurrent)

        async def _run_subtask(subtask: AgentTask) -> DelegationResult:
            async with semaphore:
                capability = self._infer_capability(subtask.title)
                return await self.orchestrator.delegate_task(subtask, capability)

        results = await asyncio.gather(
            *[_run_subtask(st) for st in team_task.subtasks]
        )

        team_task.status = "completed"
        team_task.result = [r.to_dict() if hasattr(r, 'to_dict') else str(r) for r in results]
        self._active = False
        self._results.extend(team_task.result)
        return list(results)

    async def run(self, title: str, description: str) -> List[DelegationResult]:
        """
        Decompose and execute a task in one call.
        """
        team_task = self.decompose_task(title, description)
        return await self.execute(team_task)

    def _infer_capability(self, title: str) -> AgentCapability:
        title_lower = title.lower()
        mapping = {
            "design": AgentCapability.GAMEPLAY_DESIGN,
            "implement": AgentCapability.CODE_GENERATION,
            "create": AgentCapability.ASSET_GENERATION,
            "build": AgentCapability.WORLD_BUILDING,
            "write": AgentCapability.NARRATIVE_GENERATION,
            "test": AgentCapability.TESTING,
            "audit": AgentCapability.QUALITY_REVIEW,
            "generate": AgentCapability.ASSET_GENERATION,
            "mix": AgentCapability.AUDIO_GENERATION,
            "polish": AgentCapability.ASSET_GENERATION,
            "refine": AgentCapability.CODE_GENERATION,
            "place": AgentCapability.SCENE_MANAGEMENT,
            "configure": AgentCapability.NPC_CONTROL,
            "playtest": AgentCapability.TESTING,
            "triage": AgentCapability.QUALITY_REVIEW,
        }
        for key, cap in mapping.items():
            if key in title_lower:
                return cap
        return AgentCapability.REASONING

    def get_status(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "team_type": self.team_type.value,
            "name": self.config.name,
            "active": self._active,
            "task_count": len(self._tasks),
            "result_count": len(self._results),
            "quality_gates": self.config.quality_gates,
            "max_concurrent": self.config.max_concurrent,
        }


class TeamOrchestrator:
    """
    Manages multiple teams and coordinates cross-team workflows.
    Provides team creation, task routing, and progress tracking.
    """

    def __init__(self, agent_orchestrator: AgentOrchestrator):
        self._agent_orchestrator = agent_orchestrator
        self._teams: Dict[str, Team] = {}

    def create_team(self, team_type: TeamType, config: Optional[TeamConfig] = None) -> Team:
        team = Team(team_type, self._agent_orchestrator, config)
        self._teams[team.id] = team
        return team

    def get_team(self, team_id: str) -> Optional[Team]:
        return self._teams.get(team_id)

    def list_teams(self) -> List[Dict[str, Any]]:
        return [team.get_status() for team in self._teams.values()]

    async def run_team(self, team_type: TeamType, title: str, description: str) -> List[DelegationResult]:
        team = self.create_team(team_type)
        return await team.run(title, description)

    def get_team_types(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": tt.value,
                "name": cfg.name,
                "description": cfg.description,
                "quality_gates": cfg.quality_gates,
                "max_concurrent": cfg.max_concurrent,
            }
            for tt, cfg in _TEAM_CONFIGS.items()
        ]
