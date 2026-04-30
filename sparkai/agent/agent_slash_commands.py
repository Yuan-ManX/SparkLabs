"""
SparkLabs Slash Command System

Workflow-oriented command system for AI-native game engine operations.
Provides structured slash commands for game design, development, QA, and production.
"""

from __future__ import annotations

import uuid
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple


class CommandCategory(Enum):
    ONBOARDING = "onboarding"
    DESIGN = "design"
    ART = "art"
    ARCHITECTURE = "architecture"
    DEVELOPMENT = "development"
    QA = "qa"
    PRODUCTION = "production"
    CREATIVE = "creative"
    TEAM = "team"
    SYSTEM = "system"


class CommandScope(Enum):
    GLOBAL = "global"
    PROJECT = "project"
    AGENT = "agent"
    SESSION = "session"


@dataclass
class CommandParam:
    name: str
    type: str = "string"
    required: bool = False
    default: Any = None
    description: str = ""
    choices: List[str] = field(default_factory=list)


@dataclass
class SlashCommand:
    name: str
    category: CommandCategory
    scope: CommandScope
    description: str = ""
    params: List[CommandParam] = field(default_factory=list)
    handler: Optional[Callable] = None
    aliases: List[str] = field(default_factory=list)
    tier_required: str = "worker"
    examples: List[str] = field(default_factory=list)


@dataclass
class CommandResult:
    command: str = ""
    success: bool = False
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommandExecution:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    result: Optional[CommandResult] = None
    started_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class SlashCommandSystem:
    """
    Unified slash command system for SparkLabs game engine workflows.

    Provides structured commands for every phase of game development,
    from brainstorming and design through development, QA, and release.
    """

    def __init__(self):
        self._commands: Dict[str, SlashCommand] = {}
        self._executions: List[CommandExecution] = []
        self._category_handlers: Dict[CommandCategory, List[Callable]] = {}
        self._max_executions = 500
        self._seed_commands()

    def _seed_commands(self):
        onboarding_commands = [
            SlashCommand(
                name="/start",
                category=CommandCategory.ONBOARDING,
                scope=CommandScope.GLOBAL,
                description="Initialize a new game project or resume existing work",
                params=[
                    CommandParam(name="template", type="string", required=False, choices=["platformer", "rpg", "puzzle", "strategy", "shooter", "sandbox", "narrative", "simulation"]),
                    CommandParam(name="name", type="string", required=False),
                ],
                aliases=["/init", "/new"],
                tier_required="worker",
                examples=["/start template=rpg name=MyQuest", "/start"],
            ),
            SlashCommand(
                name="/help",
                category=CommandCategory.ONBOARDING,
                scope=CommandScope.GLOBAL,
                description="Show available commands and usage information",
                params=[
                    CommandParam(name="category", type="string", required=False, choices=[c.value for c in CommandCategory]),
                ],
                aliases=["/commands", "/?"],
                tier_required="worker",
                examples=["/help", "/help category=design"],
            ),
            SlashCommand(
                name="/adopt",
                category=CommandCategory.ONBOARDING,
                scope=CommandScope.PROJECT,
                description="Adopt an existing project into SparkLabs workspace",
                params=[
                    CommandParam(name="path", type="string", required=True),
                ],
                tier_required="specialist",
                examples=["/adopt path=./my-game"],
            ),
        ]

        design_commands = [
            SlashCommand(
                name="/brainstorm",
                category=CommandCategory.DESIGN,
                scope=CommandScope.PROJECT,
                description="Generate creative game concepts and mechanics",
                params=[
                    CommandParam(name="genre", type="string", required=False),
                    CommandParam(name="theme", type="string", required=False),
                    CommandParam(name="mechanics", type="string", required=False),
                ],
                aliases=["/idea"],
                tier_required="worker",
                examples=["/brainstorm genre=rpg theme=space", "/brainstorm mechanics=deck-building"],
            ),
            SlashCommand(
                name="/design-system",
                category=CommandCategory.DESIGN,
                scope=CommandScope.PROJECT,
                description="Design a game system with rules, parameters, and interactions",
                params=[
                    CommandParam(name="name", type="string", required=True),
                    CommandParam(name="type", type="string", required=False, choices=["combat", "economy", "progression", "crafting", "dialogue", "ai", "physics"]),
                ],
                aliases=["/sys"],
                tier_required="lead",
                examples=["/design-system name=combat type=combat"],
            ),
            SlashCommand(
                name="/map-systems",
                category=CommandCategory.DESIGN,
                scope=CommandScope.PROJECT,
                description="Map relationships and dependencies between game systems",
                params=[],
                aliases=["/systems-map"],
                tier_required="lead",
                examples=["/map-systems"],
            ),
            SlashCommand(
                name="/quick-design",
                category=CommandCategory.DESIGN,
                scope=CommandScope.PROJECT,
                description="Rapidly prototype a game design from a brief description",
                params=[
                    CommandParam(name="description", type="string", required=True),
                ],
                aliases=["/qd"],
                tier_required="specialist",
                examples=["/quick-design description='A puzzle game where gravity flips'"],
            ),
        ]

        art_commands = [
            SlashCommand(
                name="/art-bible",
                category=CommandCategory.ART,
                scope=CommandScope.PROJECT,
                description="Create or update the art direction bible for the project",
                params=[
                    CommandParam(name="style", type="string", required=False, choices=["pixel", "low-poly", "hand-drawn", "realistic", "stylized", "voxel"]),
                    CommandParam(name="palette", type="string", required=False),
                ],
                aliases=["/artstyle"],
                tier_required="lead",
                examples=["/art-bible style=pixel palette=warm"],
            ),
            SlashCommand(
                name="/asset-spec",
                category=CommandCategory.ART,
                scope=CommandScope.PROJECT,
                description="Generate asset specifications for a game element",
                params=[
                    CommandParam(name="element", type="string", required=True),
                    CommandParam(name="type", type="string", required=False, choices=["character", "environment", "prop", "effect", "ui", "animation"]),
                ],
                aliases=["/spec"],
                tier_required="specialist",
                examples=["/asset-spec element=player type=character"],
            ),
        ]

        architecture_commands = [
            SlashCommand(
                name="/create-architecture",
                category=CommandCategory.ARCHITECTURE,
                scope=CommandScope.PROJECT,
                description="Design the technical architecture for the game",
                params=[
                    CommandParam(name="pattern", type="string", required=False, choices=["ecs", "mvc", "event-driven", "data-oriented", "hybrid"]),
                ],
                aliases=["/arch"],
                tier_required="lead",
                examples=["/create-architecture pattern=ecs"],
            ),
            SlashCommand(
                name="/architecture-decision",
                category=CommandCategory.ARCHITECTURE,
                scope=CommandScope.PROJECT,
                description="Record an architecture decision with rationale",
                params=[
                    CommandParam(name="title", type="string", required=True),
                    CommandParam(name="decision", type="string", required=True),
                    CommandParam(name="rationale", type="string", required=False),
                ],
                aliases=["/adr"],
                tier_required="lead",
                examples=["/adr title='State Management' decision='ECS' rationale='Performance'"],
            ),
        ]

        development_commands = [
            SlashCommand(
                name="/create-epics",
                category=CommandCategory.DEVELOPMENT,
                scope=CommandScope.PROJECT,
                description="Break down the game design into development epics",
                params=[
                    CommandParam(name="from_design", type="string", required=False),
                ],
                aliases=["/epics"],
                tier_required="lead",
                examples=["/create-epics", "/create-epics from_design=combat_system"],
            ),
            SlashCommand(
                name="/create-stories",
                category=CommandCategory.DEVELOPMENT,
                scope=CommandScope.PROJECT,
                description="Generate user stories from an epic",
                params=[
                    CommandParam(name="epic", type="string", required=True),
                ],
                aliases=["/stories"],
                tier_required="specialist",
                examples=["/create-stories epic=player_movement"],
            ),
            SlashCommand(
                name="/dev-story",
                category=CommandCategory.DEVELOPMENT,
                scope=CommandScope.PROJECT,
                description="Implement a specific user story",
                params=[
                    CommandParam(name="story_id", type="string", required=True),
                    CommandParam(name="approach", type="string", required=False, choices=["incremental", "spike", "refactor"]),
                ],
                aliases=["/implement"],
                tier_required="specialist",
                examples=["/dev-story story_id=MOV-001 approach=incremental"],
            ),
            SlashCommand(
                name="/story-done",
                category=CommandCategory.DEVELOPMENT,
                scope=CommandScope.PROJECT,
                description="Mark a story as complete with verification",
                params=[
                    CommandParam(name="story_id", type="string", required=True),
                    CommandParam(name="notes", type="string", required=False),
                ],
                aliases=["/done"],
                tier_required="specialist",
                examples=["/story-done story_id=MOV-001 notes='All tests passing'"],
            ),
        ]

        qa_commands = [
            SlashCommand(
                name="/qa-plan",
                category=CommandCategory.QA,
                scope=CommandScope.PROJECT,
                description="Create a quality assurance plan for the project",
                params=[
                    CommandParam(name="scope", type="string", required=False, choices=["full", "smoke", "regression", "performance"]),
                ],
                aliases=["/test-plan"],
                tier_required="lead",
                examples=["/qa-plan scope=full"],
            ),
            SlashCommand(
                name="/smoke-check",
                category=CommandCategory.QA,
                scope=CommandScope.PROJECT,
                description="Run a quick smoke test to verify basic functionality",
                params=[],
                aliases=["/smoke"],
                tier_required="worker",
                examples=["/smoke-check"],
            ),
            SlashCommand(
                name="/bug-report",
                category=CommandCategory.QA,
                scope=CommandScope.PROJECT,
                description="File a bug report with reproduction steps",
                params=[
                    CommandParam(name="title", type="string", required=True),
                    CommandParam(name="severity", type="string", required=False, choices=["blocker", "critical", "major", "minor"]),
                    CommandParam(name="steps", type="string", required=False),
                ],
                aliases=["/bug"],
                tier_required="worker",
                examples=["/bug title='Player falls through floor' severity=critical"],
            ),
            SlashCommand(
                name="/gate-check",
                category=CommandCategory.QA,
                scope=CommandScope.PROJECT,
                description="Run quality gate checks against the current build",
                params=[
                    CommandParam(name="gates", type="string", required=False, choices=["build", "visual", "performance", "all"]),
                ],
                aliases=["/gate"],
                tier_required="lead",
                examples=["/gate-check gates=all"],
            ),
        ]

        production_commands = [
            SlashCommand(
                name="/sprint-plan",
                category=CommandCategory.PRODUCTION,
                scope=CommandScope.PROJECT,
                description="Plan a development sprint with story assignments",
                params=[
                    CommandParam(name="duration", type="string", required=False, default="1w"),
                    CommandParam(name="capacity", type="string", required=False),
                ],
                aliases=["/sprint"],
                tier_required="lead",
                examples=["/sprint-plan duration=2w capacity=5"],
            ),
            SlashCommand(
                name="/milestone-review",
                category=CommandCategory.PRODUCTION,
                scope=CommandScope.PROJECT,
                description="Review progress against a milestone",
                params=[
                    CommandParam(name="milestone", type="string", required=False),
                ],
                aliases=["/review"],
                tier_required="director",
                examples=["/milestone-review milestone=alpha"],
            ),
            SlashCommand(
                name="/release-checklist",
                category=CommandCategory.PRODUCTION,
                scope=CommandScope.PROJECT,
                description="Generate a release readiness checklist",
                params=[
                    CommandParam(name="target", type="string", required=False, choices=["alpha", "beta", "rc", "gold"]),
                ],
                aliases=["/release"],
                tier_required="director",
                examples=["/release-checklist target=beta"],
            ),
        ]

        creative_commands = [
            SlashCommand(
                name="/prototype",
                category=CommandCategory.CREATIVE,
                scope=CommandScope.PROJECT,
                description="Create a rapid prototype of a game mechanic or feature",
                params=[
                    CommandParam(name="feature", type="string", required=True),
                    CommandParam(name="engine", type="string", required=False, choices=["canvas", "webgl", "dom"]),
                ],
                aliases=["/proto"],
                tier_required="specialist",
                examples=["/prototype feature=gravity-gun engine=canvas"],
            ),
            SlashCommand(
                name="/generate",
                category=CommandCategory.CREATIVE,
                scope=CommandScope.PROJECT,
                description="Generate game content using AI (levels, characters, dialogue, etc.)",
                params=[
                    CommandParam(name="type", type="string", required=True, choices=["level", "character", "dialogue", "quest", "item", "enemy", "music", "sfx"]),
                    CommandParam(name="prompt", type="string", required=True),
                    CommandParam(name="count", type="number", required=False, default=1),
                ],
                aliases=["/gen"],
                tier_required="worker",
                examples=["/generate type=level prompt='dungeon with traps' count=3"],
            ),
        ]

        team_commands = [
            SlashCommand(
                name="/team-combat",
                category=CommandCategory.TEAM,
                scope=CommandScope.PROJECT,
                description="Assemble a team for combat system development",
                params=[],
                aliases=["/team-fight"],
                tier_required="director",
                examples=["/team-combat"],
            ),
            SlashCommand(
                name="/team-ui",
                category=CommandCategory.TEAM,
                scope=CommandScope.PROJECT,
                description="Assemble a team for UI/UX development",
                params=[],
                aliases=["/team-ux"],
                tier_required="director",
                examples=["/team-ui"],
            ),
            SlashCommand(
                name="/team-qa",
                category=CommandCategory.TEAM,
                scope=CommandScope.PROJECT,
                description="Assemble a team for quality assurance",
                params=[],
                aliases=["/team-test"],
                tier_required="director",
                examples=["/team-qa"],
            ),
        ]

        system_commands = [
            SlashCommand(
                name="/doctor",
                category=CommandCategory.SYSTEM,
                scope=CommandScope.GLOBAL,
                description="Run a health check on the SparkLabs engine and all subsystems",
                params=[],
                aliases=["/health", "/check"],
                tier_required="worker",
                examples=["/doctor"],
            ),
            SlashCommand(
                name="/status",
                category=CommandCategory.SYSTEM,
                scope=CommandScope.GLOBAL,
                description="Show current project and engine status",
                params=[
                    CommandParam(name="detail", type="string", required=False, choices=["summary", "full", "agents", "skills"]),
                ],
                aliases=["/info"],
                tier_required="worker",
                examples=["/status", "/status detail=agents"],
            ),
            SlashCommand(
                name="/config",
                category=CommandCategory.SYSTEM,
                scope=CommandScope.GLOBAL,
                description="View or update engine configuration",
                params=[
                    CommandParam(name="key", type="string", required=False),
                    CommandParam(name="value", type="string", required=False),
                ],
                aliases=["/set"],
                tier_required="lead",
                examples=["/config key=max_agents value=20", "/config"],
            ),
        ]

        all_commands = (
            onboarding_commands + design_commands + art_commands +
            architecture_commands + development_commands + qa_commands +
            production_commands + creative_commands + team_commands + system_commands
        )

        for cmd in all_commands:
            self._commands[cmd.name] = cmd
            for alias in cmd.aliases:
                self._commands[alias] = cmd

    def register_command(self, command: SlashCommand) -> str:
        self._commands[command.name] = command
        for alias in command.aliases:
            self._commands[alias] = command
        return command.name

    def get_command(self, name: str) -> Optional[SlashCommand]:
        return self._commands.get(name)

    def list_commands(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        seen = set()
        results = []
        for name, cmd in self._commands.items():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)
            if category and cmd.category.value != category:
                continue
            results.append({
                "name": cmd.name,
                "category": cmd.category.value,
                "scope": cmd.scope.value,
                "description": cmd.description,
                "params": [
                    {"name": p.name, "type": p.type, "required": p.required, "default": p.default, "description": p.description, "choices": p.choices}
                    for p in cmd.params
                ],
                "aliases": cmd.aliases,
                "tier_required": cmd.tier_required,
                "examples": cmd.examples,
            })
        return results

    def parse_command(self, input_str: str) -> Tuple[Optional[str], Dict[str, Any]]:
        input_str = input_str.strip()
        if not input_str.startswith("/"):
            return None, {}

        parts = input_str.split()
        command_name = parts[0].lower()
        params = {}

        for part in parts[1:]:
            if "=" in part:
                key, _, value = part.partition("=")
                params[key.strip()] = value.strip()
            else:
                if "_positional" not in params:
                    params["_positional"] = []
                params["_positional"].append(part)

        return command_name, params

    def execute(self, command_input: str, context: Optional[Dict[str, Any]] = None) -> CommandResult:
        start_time = time.time()
        command_name, params = self.parse_command(command_input)

        if not command_name:
            return CommandResult(
                command=command_input,
                success=False,
                error="Not a slash command. Commands start with /",
                duration_ms=(time.time() - start_time) * 1000,
            )

        cmd = self._commands.get(command_name)
        if not cmd:
            return CommandResult(
                command=command_name,
                success=False,
                error=f"Unknown command: {command_name}. Type /help for available commands.",
                duration_ms=(time.time() - start_time) * 1000,
            )

        for param in cmd.params:
            if param.required and param.name not in params:
                if "_positional" in params and params["_positional"]:
                    params[param.name] = params["_positional"].pop(0)
                else:
                    return CommandResult(
                        command=command_name,
                        success=False,
                        error=f"Missing required parameter: {param.name}",
                        duration_ms=(time.time() - start_time) * 1000,
                    )

        execution = CommandExecution(command=command_name, params=params)

        if cmd.handler:
            try:
                result = cmd.handler(params, context or {})
                execution.result = CommandResult(
                    command=command_name,
                    success=True,
                    output=result,
                    duration_ms=(time.time() - start_time) * 1000,
                )
            except Exception as e:
                execution.result = CommandResult(
                    command=command_name,
                    success=False,
                    error=str(e),
                    duration_ms=(time.time() - start_time) * 1000,
                )
        else:
            execution.result = CommandResult(
                command=command_name,
                success=True,
                output={
                    "command": command_name,
                    "description": cmd.description,
                    "params_received": params,
                    "status": "dispatched",
                    "category": cmd.category.value,
                },
                duration_ms=(time.time() - start_time) * 1000,
            )

        execution.completed_at = time.time()
        self._executions.append(execution)
        if len(self._executions) > self._max_executions:
            self._executions = self._executions[-self._max_executions:]

        return execution.result

    def get_execution_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        return [
            {
                "id": ex.id,
                "command": ex.command,
                "params": ex.params,
                "success": ex.result.success if ex.result else None,
                "duration_ms": ex.result.duration_ms if ex.result else None,
                "started_at": ex.started_at,
                "completed_at": ex.completed_at,
            }
            for ex in self._executions[-limit:]
        ]

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._executions)
        successful = sum(1 for ex in self._executions if ex.result and ex.result.success)
        category_counts = {}
        for name, cmd in self._commands.items():
            if cmd.name == name:
                cat = cmd.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1
        return {
            "total_commands": len(set(cmd.name for cmd in self._commands.values())),
            "total_executions": total,
            "successful_executions": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "category_distribution": category_counts,
        }
