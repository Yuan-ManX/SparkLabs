"""
SparkLabs Agent Team Factory - Multi-Agent Team Orchestration

Comprehensive team architecture factory supporting 6 patterns for
coordinating specialized agent teams across game development workflows.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class TeamPattern(Enum):
    """Multi-agent team architecture patterns."""
    PIPELINE = "pipeline"               # Sequential dependent tasks
    FAN_OUT = "fan_out"                # Parallel independent tasks
    EXPERT_POOL = "expert_pool"        # Context-dependent selective invocation
    PRODUCER_REVIEWER = "producer_reviewer"  # Generate then verify
    SUPERVISOR = "supervisor"          # Central agent with dynamic dispatch
    HIERARCHICAL = "hierarchical"      # Top-down recursive delegation


class AgentRole(Enum):
    """Predefined agent roles for game development."""
    ARCHITECT = "architect"            # System design and architecture
    DEVELOPER = "developer"            # Implementation and coding
    REVIEWER = "reviewer"              # Quality review and validation
    DESIGNER = "designer"              # Game design and mechanics
    ARTIST = "artist"                  # Visual and audio assets
    TESTER = "tester"                  # Testing and QA
    ORCHESTRATOR = "orchestrator"      # Team coordination
    ANALYST = "analyst"                # Data analysis and insights
    WRITER = "writer"                  # Narrative and dialogue
    OPTIMIZER = "optimizer"            # Performance optimization


class CommunicationProtocol(Enum):
    """Inter-agent communication methods."""
    MESSAGE = "message"                # Direct message passing
    TASK = "task"                      # Task-based delegation
    SHARED_STATE = "shared_state"      # Shared state/blackboard
    EVENT = "event"                    # Event-driven pub/sub
    PIPELINE = "pipeline"              # Sequential data flow


@dataclass
class AgentDefinition:
    """Definition of a specialized agent in a team."""
    agent_id: str
    name: str
    role: AgentRole
    description: str
    principles: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    input_protocol: CommunicationProtocol = CommunicationProtocol.MESSAGE
    output_protocol: CommunicationProtocol = CommunicationProtocol.MESSAGE
    quality_gates: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "role": self.role.value,
            "description": self.description,
            "principles": self.principles,
            "capabilities": self.capabilities,
            "input_protocol": self.input_protocol.value,
            "output_protocol": self.output_protocol.value,
            "quality_gates": self.quality_gates,
            "tools": self.tools,
            "dependencies": self.dependencies,
        }


@dataclass
class TeamBlueprint:
    """Complete team architecture blueprint."""
    blueprint_id: str
    name: str
    pattern: TeamPattern
    domain: str
    description: str
    agents: List[AgentDefinition] = field(default_factory=list)
    communication_rules: Dict[str, Any] = field(default_factory=dict)
    error_handling: Dict[str, Any] = field(default_factory=dict)
    max_concurrent: int = 5
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "blueprint_id": self.blueprint_id,
            "name": self.name,
            "pattern": self.pattern.value,
            "domain": self.domain,
            "description": self.description,
            "agents": [a.to_dict() for a in self.agents],
            "communication_rules": self.communication_rules,
            "error_handling": self.error_handling,
            "max_concurrent": self.max_concurrent,
            "created_at": self.created_at,
        }


@dataclass
class TeamTask:
    """A task assigned to a team."""
    task_id: str
    description: str
    assigned_team: str
    status: str = "pending"  # pending, in_progress, completed, failed
    assigned_agent: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "description": self.description,
            "assigned_team": self.assigned_team,
            "status": self.status,
            "assigned_agent": self.assigned_agent,
            "dependencies": self.dependencies,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


class TeamFactory:
    """Generates domain-specific agent team blueprints.

    Supports 6 architecture patterns:
    - Pipeline: Sequential processing with ordered stages
    - Fan-out: Parallel execution with result aggregation
    - Expert Pool: Smart routing based on task context
    - Producer-Reviewer: Creation with quality verification
    - Supervisor: Central coordinator with dynamic dispatch
    - Hierarchical: Recursive task decomposition
    """

    _instance: Optional["TeamFactory"] = None
    _instance_lock = threading.RLock()

    # Predefined team configurations for game development
    GAME_DEV_TEAMS: Dict[str, Dict[str, Any]] = {
        "code_generation": {
            "pattern": TeamPattern.PRODUCER_REVIEWER,
            "agents": [
                {"role": AgentRole.DEVELOPER, "name": "Code Generator",
                 "description": "Generates game code from specifications"},
                {"role": AgentRole.REVIEWER, "name": "Code Reviewer",
                 "description": "Reviews generated code for quality and correctness"},
                {"role": AgentRole.TESTER, "name": "Test Runner",
                 "description": "Validates code through automated testing"},
            ],
        },
        "game_design": {
            "pattern": TeamPattern.EXPERT_POOL,
            "agents": [
                {"role": AgentRole.DESIGNER, "name": "Mechanics Designer",
                 "description": "Designs core game mechanics and systems"},
                {"role": AgentRole.DESIGNER, "name": "Level Designer",
                 "description": "Creates level layouts and progression"},
                {"role": AgentRole.ANALYST, "name": "Balance Analyst",
                 "description": "Analyzes and balances game parameters"},
                {"role": AgentRole.WRITER, "name": "Narrative Designer",
                 "description": "Crafts story and dialogue elements"},
            ],
        },
        "asset_pipeline": {
            "pattern": TeamPattern.PIPELINE,
            "agents": [
                {"role": AgentRole.DESIGNER, "name": "Concept Artist",
                 "description": "Generates concept art and style guides"},
                {"role": AgentRole.ARTIST, "name": "Asset Creator",
                 "description": "Creates final game assets from concepts"},
                {"role": AgentRole.REVIEWER, "name": "Quality Checker",
                 "description": "Validates asset quality and consistency"},
                {"role": AgentRole.OPTIMIZER, "name": "Asset Optimizer",
                 "description": "Optimizes assets for runtime performance"},
            ],
        },
        "testing_suite": {
            "pattern": TeamPattern.FAN_OUT,
            "agents": [
                {"role": AgentRole.TESTER, "name": "Unit Tester",
                 "description": "Runs unit tests on game modules"},
                {"role": AgentRole.TESTER, "name": "Integration Tester",
                 "description": "Tests cross-module integration"},
                {"role": AgentRole.TESTER, "name": "Performance Tester",
                 "description": "Measures runtime performance metrics"},
                {"role": AgentRole.TESTER, "name": "Playtest Simulator",
                 "description": "Simulates player behavior for testing"},
            ],
        },
        "world_building": {
            "pattern": TeamPattern.HIERARCHICAL,
            "agents": [
                {"role": AgentRole.ARCHITECT, "name": "World Architect",
                 "description": "Designs overall world structure and layout"},
                {"role": AgentRole.DESIGNER, "name": "Region Designer",
                 "description": "Creates individual region content"},
                {"role": AgentRole.ARTIST, "name": "Environment Artist",
                 "description": "Generates environment visuals"},
                {"role": AgentRole.OPTIMIZER, "name": "World Optimizer",
                 "description": "Optimizes world streaming and LOD"},
            ],
        },
        "full_development": {
            "pattern": TeamPattern.SUPERVISOR,
            "agents": [
                {"role": AgentRole.ORCHESTRATOR, "name": "Dev Supervisor",
                 "description": "Coordinates all development activities"},
                {"role": AgentRole.ARCHITECT, "name": "System Architect",
                 "description": "Designs technical architecture"},
                {"role": AgentRole.DEVELOPER, "name": "Core Developer",
                 "description": "Implements core systems"},
                {"role": AgentRole.DESIGNER, "name": "Game Designer",
                 "description": "Creates game design documents"},
                {"role": AgentRole.REVIEWER, "name": "QA Lead",
                 "description": "Ensures quality across all deliverables"},
            ],
        },
    }

    def __init__(self) -> None:
        if self._instance is not None:
            raise RuntimeError("Use TeamFactory.get_instance()")
        self._blueprints: Dict[str, TeamBlueprint] = {}
        self._active_teams: Dict[str, List[TeamTask]] = {}
        self._completed_tasks: List[TeamTask] = []
        self._initialized: bool = False
        self._lock = threading.RLock()

    @classmethod
    def get_instance(cls) -> "TeamFactory":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        with self._lock:
            self._initialized = True

    def create_team(self, domain: str, team_type: str,
                    custom_agents: Optional[List[Dict[str, Any]]] = None
                    ) -> TeamBlueprint:
        """Create a team blueprint for a specific domain."""
        blueprint_id = f"team_{uuid.uuid4().hex[:12]}"

        # Use predefined team or build custom
        if team_type in self.GAME_DEV_TEAMS and not custom_agents:
            template = self.GAME_DEV_TEAMS[team_type]
            pattern = template["pattern"]
            agents = []
            for i, agent_def in enumerate(template["agents"]):
                agent = AgentDefinition(
                    agent_id=f"agent_{uuid.uuid4().hex[:8]}",
                    name=agent_def["name"],
                    role=agent_def["role"],
                    description=agent_def["description"],
                    principles=self._get_role_principles(agent_def["role"]),
                    capabilities=self._get_role_capabilities(agent_def["role"]),
                    quality_gates=self._get_quality_gates(agent_def["role"]),
                )
                agents.append(agent)
        else:
            pattern = TeamPattern.EXPERT_POOL
            agents = []
            if custom_agents:
                for agent_def in custom_agents:
                    try:
                        role = AgentRole(agent_def.get("role", "developer"))
                    except ValueError:
                        role = AgentRole.DEVELOPER
                    agent = AgentDefinition(
                        agent_id=f"agent_{uuid.uuid4().hex[:8]}",
                        name=agent_def.get("name", f"Agent_{i}"),
                        role=role,
                        description=agent_def.get("description", ""),
                        principles=agent_def.get("principles", []),
                        capabilities=agent_def.get("capabilities", []),
                        quality_gates=agent_def.get("quality_gates", []),
                    )
                    agents.append(agent)

        blueprint = TeamBlueprint(
            blueprint_id=blueprint_id,
            name=f"{domain}_{team_type}",
            pattern=pattern,
            domain=domain,
            description=f"Team for {domain} using {pattern.value} pattern",
            agents=agents,
            communication_rules=self._get_communication_rules(pattern),
            error_handling=self._get_error_handling(pattern),
        )

        with self._lock:
            self._blueprints[blueprint_id] = blueprint
        return blueprint

    def dispatch_task(self, blueprint_id: str, task_description: str,
                      context: Optional[Dict[str, Any]] = None) -> TeamTask:
        """Dispatch a task to a team for execution."""
        with self._lock:
            blueprint = self._blueprints.get(blueprint_id)
            if not blueprint:
                raise ValueError(f"Team blueprint '{blueprint_id}' not found")

            task = TeamTask(
                task_id=f"task_{uuid.uuid4().hex[:12]}",
                description=task_description,
                assigned_team=blueprint_id,
            )

            # Route task based on team pattern
            target_agent = self._route_task(blueprint, task_description)
            task.assigned_agent = target_agent.agent_id if target_agent else None
            task.status = "in_progress"
            task.started_at = time.time()

            if blueprint_id not in self._active_teams:
                self._active_teams[blueprint_id] = []
            self._active_teams[blueprint_id].append(task)

            return task

    def complete_task(self, task_id: str, result: Dict[str, Any],
                      success: bool = True) -> Optional[TeamTask]:
        """Mark a task as completed with results."""
        with self._lock:
            for tasks in self._active_teams.values():
                for task in tasks:
                    if task.task_id == task_id:
                        task.status = "completed" if success else "failed"
                        task.result = result
                        task.completed_at = time.time()
                        if not success:
                            task.error = result.get("error", "Unknown error")
                        self._completed_tasks.append(task)
                        tasks.remove(task)
                        return task
        return None

    def get_team_blueprint(self, blueprint_id: str) -> Optional[TeamBlueprint]:
        return self._blueprints.get(blueprint_id)

    def list_blueprints(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._blueprints.values()]

    def list_team_types(self) -> List[Dict[str, Any]]:
        return [
            {"type": name, "pattern": config["pattern"].value,
             "agent_count": len(config["agents"])}
            for name, config in self.GAME_DEV_TEAMS.items()
        ]

    def get_active_tasks(self, blueprint_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if blueprint_id:
            return [t.to_dict() for t in self._active_teams.get(blueprint_id, [])]
        all_tasks = []
        for tasks in self._active_teams.values():
            all_tasks.extend(tasks)
        return [t.to_dict() for t in all_tasks]

    def get_completed_tasks(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._completed_tasks[-limit:]]

    def get_statistics(self) -> Dict[str, Any]:
        with self._lock:
            completed = len(self._completed_tasks)
            successful = sum(1 for t in self._completed_tasks if t.status == "completed")
            failed = sum(1 for t in self._completed_tasks if t.status == "failed")
            active = sum(len(t) for t in self._active_teams.values())
            return {
                "blueprints": len(self._blueprints),
                "team_types": len(self.GAME_DEV_TEAMS),
                "active_tasks": active,
                "completed_tasks": completed,
                "successful": successful,
                "failed": failed,
                "success_rate": successful / max(completed, 1),
            }

    def _route_task(self, blueprint: TeamBlueprint,
                    task_description: str) -> Optional[AgentDefinition]:
        """Route a task to the most appropriate agent based on team pattern."""
        if not blueprint.agents:
            return None

        if blueprint.pattern == TeamPattern.SUPERVISOR:
            # Supervisor always routes to orchestrator first
            for agent in blueprint.agents:
                if agent.role == AgentRole.ORCHESTRATOR:
                    return agent

        # Simple keyword matching for routing
        desc_lower = task_description.lower()
        for agent in blueprint.agents:
            for capability in agent.capabilities:
                if capability.lower() in desc_lower:
                    return agent

        # Default to first agent
        return blueprint.agents[0]

    def _get_role_principles(self, role: AgentRole) -> List[str]:
        principles = {
            AgentRole.ARCHITECT: [
                "Design for scalability and maintainability",
                "Follow established architectural patterns",
                "Document all design decisions",
            ],
            AgentRole.DEVELOPER: [
                "Write clean, testable code",
                "Follow coding standards",
                "Handle errors gracefully",
            ],
            AgentRole.REVIEWER: [
                "Verify correctness and completeness",
                "Check for edge cases",
                "Provide actionable feedback",
            ],
            AgentRole.DESIGNER: [
                "Focus on player experience",
                "Balance creativity with constraints",
                "Iterate based on feedback",
            ],
            AgentRole.TESTER: [
                "Test edge cases thoroughly",
                "Document reproduction steps",
                "Verify fixes completely",
            ],
            AgentRole.ORCHESTRATOR: [
                "Coordinate team activities",
                "Resolve conflicts efficiently",
                "Track progress and report status",
            ],
        }
        return principles.get(role, ["Complete assigned tasks accurately"])

    def _get_role_capabilities(self, role: AgentRole) -> List[str]:
        capabilities = {
            AgentRole.ARCHITECT: ["system_design", "api_design", "data_modeling",
                                  "architecture_review"],
            AgentRole.DEVELOPER: ["code_generation", "debugging", "refactoring",
                                  "implementation"],
            AgentRole.REVIEWER: ["code_review", "quality_assessment", "security_audit",
                                 "standards_enforcement"],
            AgentRole.DESIGNER: ["game_design", "level_design", "mechanic_creation",
                                 "balance_tuning"],
            AgentRole.TESTER: ["unit_testing", "integration_testing", "performance_testing",
                               "regression_testing"],
            AgentRole.ORCHESTRATOR: ["task_routing", "progress_tracking", "conflict_resolution",
                                     "team_coordination"],
            AgentRole.ARTIST: ["asset_generation", "visual_design", "animation",
                               "style_consistency"],
            AgentRole.ANALYST: ["data_analysis", "metric_collection", "insight_generation",
                                "reporting"],
            AgentRole.WRITER: ["narrative_design", "dialogue_creation", "story_development",
                               "character_writing"],
            AgentRole.OPTIMIZER: ["performance_analysis", "resource_optimization",
                                  "bottleneck_identification", "profiling"],
        }
        return capabilities.get(role, ["general_task_execution"])

    def _get_quality_gates(self, role: AgentRole) -> List[str]:
        gates = {
            AgentRole.DEVELOPER: ["linting_passed", "tests_passing", "no_security_issues"],
            AgentRole.REVIEWER: ["all_checks_complete", "feedback_provided", "issues_tracked"],
            AgentRole.TESTER: ["coverage_threshold_met", "regression_free",
                               "performance_within_budget"],
        }
        return gates.get(role, ["task_completed", "output_validated"])

    def _get_communication_rules(self, pattern: TeamPattern) -> Dict[str, Any]:
        rules = {
            TeamPattern.PIPELINE: {
                "flow": "sequential",
                "handoff": "output_to_input",
                "coordination": "none",
            },
            TeamPattern.FAN_OUT: {
                "flow": "parallel",
                "handoff": "broadcast",
                "coordination": "aggregator",
            },
            TeamPattern.EXPERT_POOL: {
                "flow": "selective",
                "handoff": "routed",
                "coordination": "registry",
            },
            TeamPattern.PRODUCER_REVIEWER: {
                "flow": "bidirectional",
                "handoff": "submit_review",
                "coordination": "iteration",
            },
            TeamPattern.SUPERVISOR: {
                "flow": "centralized",
                "handoff": "dispatched",
                "coordination": "supervisor",
            },
            TeamPattern.HIERARCHICAL: {
                "flow": "recursive",
                "handoff": "delegation",
                "coordination": "parent_child",
            },
        }
        return rules.get(pattern, {})

    def _get_error_handling(self, pattern: TeamPattern) -> Dict[str, Any]:
        return {
            "retry_count": 3,
            "fallback_strategy": "escalate" if pattern == TeamPattern.SUPERVISOR else "skip",
            "timeout_seconds": 300,
            "error_propagation": "aggregate",
        }


def get_team_factory() -> TeamFactory:
    """Get the global TeamFactory instance."""
    return TeamFactory.get_instance()