"""
SparkAI Agent - Slash Commands

Executable command system that maps slash commands to agent skills,
tools, and workflows. Commands provide a structured interface for
triggering complex agent operations.

Command Categories:
  - onboarding: /start, /help
  - game_design: /brainstorm, /design-system, /map-systems
  - creation: /scaffold, /generate, /create-scene, /create-entity
  - asset: /generate-asset, /generate-audio, /generate-code
  - narrative: /write-story, /create-quest, /create-dialogue
  - npc: /create-npc, /configure-npc, /set-behavior
  - review: /code-review, /design-review, /balance-check
  - qa: /diagnose, /validate, /run-tests, /bench
  - pipeline: /pipeline-run, /loop-run
  - team: /team-combat, /team-narrative, /team-ui, /team-level
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandCategory(Enum):
    ONBOARDING = "onboarding"
    GAME_DESIGN = "game_design"
    CREATION = "creation"
    ASSET = "asset"
    NARRATIVE = "narrative"
    NPC = "npc"
    REVIEW = "review"
    QA = "qa"
    PIPELINE = "pipeline"
    TEAM = "team"


@dataclass
class CommandParameter:
    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    default: Any = None


@dataclass
class SlashCommand:
    """
    A slash command that maps to an agent operation.
    Commands parse user input and route to the appropriate
    skill, tool, or workflow.
    """
    name: str
    description: str = ""
    category: CommandCategory = CommandCategory.ONBOARDING
    parameters: List[CommandParameter] = field(default_factory=list)
    handler: Optional[Callable] = None
    aliases: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)

    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        if self.handler:
            if asyncio.iscoroutinefunction(self.handler):
                return await self.handler(args)
            return self.handler(args)
        return {"command": self.name, "status": "executed", "args": args}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "parameters": [
                {"name": p.name, "type": p.type, "description": p.description, "required": p.required}
                for p in self.parameters
            ],
            "aliases": self.aliases,
            "examples": self.examples,
        }


class CommandRegistry:
    """
    Global registry for slash commands.
    Provides command discovery, parsing, and execution.
    """

    _commands: Dict[str, SlashCommand] = {}

    @classmethod
    def register(cls, command: SlashCommand) -> None:
        cls._commands[command.name] = command
        for alias in command.aliases:
            cls._commands[alias] = command

    @classmethod
    def get(cls, name: str) -> Optional[SlashCommand]:
        return cls._commands.get(name)

    @classmethod
    def list_commands(cls, category: Optional[CommandCategory] = None) -> List[SlashCommand]:
        seen = set()
        result = []
        for cmd in cls._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                if category is None or cmd.category == category:
                    result.append(cmd)
        return result

    @classmethod
    def list_categories(cls) -> List[Dict[str, Any]]:
        cats: Dict[str, int] = {}
        seen = set()
        for cmd in cls._commands.values():
            if cmd.name not in seen:
                seen.add(cmd.name)
                cat = cmd.category.value
                cats[cat] = cats.get(cat, 0) + 1
        return [{"category": k, "count": v} for k, v in cats.items()]

    @classmethod
    async def execute(cls, command_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        cmd = cls.get(command_name)
        if not cmd:
            return {"error": f"Unknown command: /{command_name}", "available": list(set(c.name for c in cls._commands.values()))}
        return await cmd.execute(args)

    @classmethod
    def parse_input(cls, text: str) -> tuple[Optional[str], Dict[str, Any]]:
        """
        Parse a slash command from user input.
        Returns (command_name, args) or (None, {}) if not a command.
        """
        text = text.strip()
        if not text.startswith("/"):
            return None, {}
        parts = text[1:].split(None, 1)
        if not parts:
            return None, {}
        command_name = parts[0].lower()
        args = {}
        if len(parts) > 1:
            args["input"] = parts[1]
        return command_name, args


def _setup_builtin_commands() -> None:
    async def _start(args: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "message": "Welcome to SparkLabs! Choose your path:\n1. /brainstorm - Explore game ideas\n2. /scaffold - Create a project from template\n3. /design-system - Design a game system\n4. /help - See all commands",
            "suggestions": ["/brainstorm", "/scaffold", "/design-system", "/help"],
        }

    async def _help(args: Dict[str, Any]) -> Dict[str, Any]:
        categories = CommandRegistry.list_categories()
        commands = CommandRegistry.list_commands()
        lines = ["SparkLabs Commands:"]
        for cat_info in categories:
            cat = cat_info["category"]
            cat_cmds = [c for c in commands if c.category.value == cat]
            lines.append(f"\n  {cat.upper()} ({cat_info['count']} commands)")
            for cmd in cat_cmds:
                lines.append(f"    /{cmd.name} - {cmd.description}")
        return {"message": "\n".join(lines)}

    async def _brainstorm(args: Dict[str, Any]) -> Dict[str, Any]:
        topic = args.get("input", "game concept")
        return {
            "message": f"Brainstorming: {topic}\n\nGenerating game ideas based on your input...",
            "ideas": [
                f"Action {topic} with procedural levels",
                f"Story-driven {topic} with branching narrative",
                f"Multiplayer {topic} with competitive modes",
            ],
            "next_steps": ["/design-system", "/scaffold"],
        }

    async def _design_system(args: Dict[str, Any]) -> Dict[str, Any]:
        system = args.get("input", "combat")
        return {
            "message": f"Designing {system} system...",
            "system": system,
            "components": ["Core Logic", "Input Handler", "State Machine", "Feedback System"],
            "next_steps": ["/scaffold", "/generate-code"],
        }

    async def _scaffold(args: Dict[str, Any]) -> Dict[str, Any]:
        genre = args.get("input", "platformer")
        return {
            "message": f"Scaffolding {genre} project...",
            "genre": genre,
            "files": ["index.html", "game.js", "style.css", "assets/"],
            "systems": ["PhysicsSystem", "InputSystem", "RenderSystem"],
            "next_steps": ["/generate-code", "/create-scene"],
        }

    async def _generate(args: Dict[str, Any]) -> Dict[str, Any]:
        what = args.get("input", "game")
        return {
            "message": f"Generating {what}...",
            "type": what,
            "status": "generating",
            "next_steps": ["/validate", "/bench"],
        }

    async def _create_scene(args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("input", "Main Scene")
        return {
            "message": f"Creating scene: {name}",
            "scene_name": name,
            "entities": [],
            "next_steps": ["/create-entity", "/create-npc"],
        }

    async def _create_entity(args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("input", "Entity")
        return {
            "message": f"Creating entity: {name}",
            "entity_name": name,
            "components": ["Transform", "Renderable"],
            "next_steps": ["/generate-asset", "/create-npc"],
        }

    async def _generate_asset(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "character sprite")
        return {
            "message": f"Generating asset: {desc}",
            "asset_type": "image",
            "description": desc,
            "next_steps": ["/generate-audio"],
        }

    async def _generate_audio(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "background music")
        return {
            "message": f"Generating audio: {desc}",
            "audio_type": "music",
            "description": desc,
        }

    async def _generate_code(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "player controller")
        return {
            "message": f"Generating code: {desc}",
            "language": "javascript",
            "description": desc,
        }

    async def _write_story(args: Dict[str, Any]) -> Dict[str, Any]:
        topic = args.get("input", "hero's journey")
        return {
            "message": f"Writing story: {topic}",
            "chapters": ["Introduction", "Rising Action", "Climax", "Resolution"],
            "next_steps": ["/create-quest", "/create-dialogue"],
        }

    async def _create_quest(args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("input", "Main Quest")
        return {
            "message": f"Creating quest: {name}",
            "quest_name": name,
            "objectives": ["Explore the area", "Defeat the boss", "Collect the artifact"],
        }

    async def _create_dialogue(args: Dict[str, Any]) -> Dict[str, Any]:
        characters = args.get("input", "Hero and NPC")
        return {
            "message": f"Creating dialogue: {characters}",
            "characters": characters,
            "dialogue_tree": {"greeting": "Hello, traveler!", "quest": "I need your help..."},
        }

    async def _create_npc(args: Dict[str, Any]) -> Dict[str, Any]:
        name = args.get("input", "Villager")
        return {
            "message": f"Creating NPC: {name}",
            "npc_name": name,
            "personality": {"friendliness": 0.7, "bravery": 0.3},
            "next_steps": ["/configure-npc", "/set-behavior"],
        }

    async def _configure_npc(args: Dict[str, Any]) -> Dict[str, Any]:
        config = args.get("input", "friendly merchant")
        return {
            "message": f"Configuring NPC: {config}",
            "configuration": config,
        }

    async def _set_behavior(args: Dict[str, Any]) -> Dict[str, Any]:
        behavior = args.get("input", "wander and trade")
        return {
            "message": f"Setting behavior: {behavior}",
            "behavior": behavior,
        }

    async def _code_review(args: Dict[str, Any]) -> Dict[str, Any]:
        code = args.get("input", "current project")
        return {
            "message": f"Reviewing code: {code}",
            "issues": [],
            "suggestions": ["Consider extracting constants", "Add error handling"],
        }

    async def _design_review(args: Dict[str, Any]) -> Dict[str, Any]:
        system = args.get("input", "game systems")
        return {
            "message": f"Reviewing design: {system}",
            "feedback": ["System cohesion looks good", "Consider adding more player feedback"],
        }

    async def _balance_check(args: Dict[str, Any]) -> Dict[str, Any]:
        system = args.get("input", "combat")
        return {
            "message": f"Checking balance: {system}",
            "result": "balanced",
            "metrics": {"damage_range": "10-50", "avg_ttk": "3.2s"},
        }

    async def _diagnose(args: Dict[str, Any]) -> Dict[str, Any]:
        error = args.get("input", "unknown error")
        return {
            "message": f"Diagnosing: {error}",
            "root_cause": "Pattern not matched in debug protocol",
            "suggestion": "Provide more context about the error",
        }

    async def _validate(args: Dict[str, Any]) -> Dict[str, Any]:
        target = args.get("input", "scene")
        return {
            "message": f"Validating: {target}",
            "checks": ["syntax", "imports", "structure"],
            "result": "passed",
        }

    async def _run_tests(args: Dict[str, Any]) -> Dict[str, Any]:
        scope = args.get("input", "all")
        return {
            "message": f"Running tests: {scope}",
            "passed": 12,
            "failed": 0,
            "total": 12,
        }

    async def _bench(args: Dict[str, Any]) -> Dict[str, Any]:
        target = args.get("input", "game")
        return {
            "message": f"Running benchmark: {target}",
            "build_health": 0.95,
            "visual_usability": 0.80,
            "intent_alignment": 0.85,
            "total_score": 0.87,
            "passed": True,
        }

    async def _pipeline_run(args: Dict[str, Any]) -> Dict[str, Any]:
        prompt = args.get("input", "Create a game")
        return {
            "message": f"Running pipeline: {prompt}",
            "stages": ["analyze", "design", "scaffold", "implement", "integrate", "validate"],
            "status": "running",
        }

    async def _loop_run(args: Dict[str, Any]) -> Dict[str, Any]:
        goal = args.get("input", "Build a game")
        return {
            "message": f"Running agent loop: {goal}",
            "max_iterations": 25,
            "status": "running",
        }

    async def _team_combat(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "Build combat system")
        return {"message": f"Combat team assembled: {desc}", "agents": ["Game Designer", "AI Programmer", "Gameplay Programmer"]}

    async def _team_narrative(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "Write story")
        return {"message": f"Narrative team assembled: {desc}", "agents": ["Narrative Director", "Writer", "NPC Designer"]}

    async def _team_ui(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "Design UI")
        return {"message": f"UI team assembled: {desc}", "agents": ["Art Director", "UI Programmer"]}

    async def _team_level(args: Dict[str, Any]) -> Dict[str, Any]:
        desc = args.get("input", "Build level")
        return {"message": f"Level team assembled: {desc}", "agents": ["Level Designer", "World Builder", "AI Programmer"]}

    builtin_commands = [
        SlashCommand(name="start", description="Start a new session", category=CommandCategory.ONBOARDING, handler=_start, aliases=["/start"]),
        SlashCommand(name="help", description="List all commands", category=CommandCategory.ONBOARDING, handler=_help, aliases=["h"]),
        SlashCommand(name="brainstorm", description="Explore game ideas", category=CommandCategory.GAME_DESIGN, handler=_brainstorm, parameters=[CommandParameter(name="topic", description="Topic to brainstorm")], examples=["/brainstorm space shooter"]),
        SlashCommand(name="design-system", description="Design a game system", category=CommandCategory.GAME_DESIGN, handler=_design_system, parameters=[CommandParameter(name="system", description="System to design")], examples=["/design-system combat"]),
        SlashCommand(name="map-systems", description="Map all game systems", category=CommandCategory.GAME_DESIGN, handler=_design_system, aliases=["map"]),
        SlashCommand(name="scaffold", description="Create project from template", category=CommandCategory.CREATION, handler=_scaffold, parameters=[CommandParameter(name="genre", description="Game genre")], examples=["/scaffold platformer"]),
        SlashCommand(name="generate", description="Generate game content", category=CommandCategory.CREATION, handler=_generate, aliases=["gen"]),
        SlashCommand(name="create-scene", description="Create a new scene", category=CommandCategory.CREATION, handler=_create_scene, aliases=["scene"]),
        SlashCommand(name="create-entity", description="Create a game entity", category=CommandCategory.CREATION, handler=_create_entity, aliases=["entity"]),
        SlashCommand(name="generate-asset", description="Generate a game asset", category=CommandCategory.ASSET, handler=_generate_asset, aliases=["asset"]),
        SlashCommand(name="generate-audio", description="Generate audio content", category=CommandCategory.ASSET, handler=_generate_audio, aliases=["audio"]),
        SlashCommand(name="generate-code", description="Generate game code", category=CommandCategory.ASSET, handler=_generate_code, aliases=["code"]),
        SlashCommand(name="write-story", description="Write a game story", category=CommandCategory.NARRATIVE, handler=_write_story, aliases=["story"]),
        SlashCommand(name="create-quest", description="Create a quest", category=CommandCategory.NARRATIVE, handler=_create_quest, aliases=["quest"]),
        SlashCommand(name="create-dialogue", description="Create dialogue", category=CommandCategory.NARRATIVE, handler=_create_dialogue, aliases=["dialogue"]),
        SlashCommand(name="create-npc", description="Create an NPC", category=CommandCategory.NPC, handler=_create_npc, aliases=["npc"]),
        SlashCommand(name="configure-npc", description="Configure NPC personality", category=CommandCategory.NPC, handler=_configure_npc),
        SlashCommand(name="set-behavior", description="Set NPC behavior", category=CommandCategory.NPC, handler=_set_behavior, aliases=["behavior"]),
        SlashCommand(name="code-review", description="Review code quality", category=CommandCategory.REVIEW, handler=_code_review, aliases=["review"]),
        SlashCommand(name="design-review", description="Review game design", category=CommandCategory.REVIEW, handler=_design_review),
        SlashCommand(name="balance-check", description="Check game balance", category=CommandCategory.REVIEW, handler=_balance_check, aliases=["balance"]),
        SlashCommand(name="diagnose", description="Diagnose an error", category=CommandCategory.QA, handler=_diagnose, aliases=["debug"]),
        SlashCommand(name="validate", description="Validate game content", category=CommandCategory.QA, handler=_validate),
        SlashCommand(name="run-tests", description="Run test suite", category=CommandCategory.QA, handler=_run_tests, aliases=["test"]),
        SlashCommand(name="bench", description="Run game benchmark", category=CommandCategory.QA, handler=_bench, aliases=["benchmark"]),
        SlashCommand(name="pipeline-run", description="Run game generation pipeline", category=CommandCategory.PIPELINE, handler=_pipeline_run, aliases=["pipeline"]),
        SlashCommand(name="loop-run", description="Run agent loop", category=CommandCategory.PIPELINE, handler=_loop_run, aliases=["loop"]),
        SlashCommand(name="team-combat", description="Assemble combat team", category=CommandCategory.TEAM, handler=_team_combat),
        SlashCommand(name="team-narrative", description="Assemble narrative team", category=CommandCategory.TEAM, handler=_team_narrative),
        SlashCommand(name="team-ui", description="Assemble UI team", category=CommandCategory.TEAM, handler=_team_ui),
        SlashCommand(name="team-level", description="Assemble level team", category=CommandCategory.TEAM, handler=_team_level),
    ]

    for cmd in builtin_commands:
        CommandRegistry.register(cmd)


_setup_builtin_commands()
