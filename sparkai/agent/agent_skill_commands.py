"""
SparkLabs Agent - Skill Commands

Structured skill command system for the AI game engine agent.
Provides a slash-command interface that AI agents and users
can issue to trigger specific game development operations.
Commands span generation, analysis, building, and deployment
tasks — giving the agent a consistent action vocabulary.

Architecture:
  SkillCommandRegistry
    |-- CommandDef (name, description, category, parameters)
    |-- CommandHandler (validation + execution pipeline)
    |-- CommandRouter (parse text → resolve command → dispatch)
    |-- ParameterValidator (type checking, range validation)
    |-- CommandHistory (recent commands with results)

Command Categories:
  - GENERATE: /generate-sprite, /generate-level, /generate-code
  - ANALYZE: /analyze-scene, /analyze-performance, /analyze-assets
  - BUILD: /build-game, /build-asset, /build-scene
  - DEPLOY: /deploy-web, /deploy-mobile, /deploy-desktop
  - EDIT: /edit-object, /edit-scene, /edit-script
  - UTILITY: /help, /status, /clear, /undo, /redo
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class CommandCategory(Enum):
    GENERATE = "generate"
    ANALYZE = "analyze"
    BUILD = "build"
    DEPLOY = "deploy"
    EDIT = "edit"
    UTILITY = "utility"


@dataclass
class CommandParameter:
    name: str
    param_type: str = "string"
    description: str = ""
    required: bool = False
    default: Any = None
    choices: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None


@dataclass
class CommandDef:
    name: str
    description: str
    category: CommandCategory
    parameters: List[CommandParameter] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    handler: Optional[Callable] = None
    requires_project: bool = False
    requires_engine: bool = False
    cooldown_seconds: float = 0.0
    _last_used: float = 0.0


@dataclass
class CommandResult:
    command_name: str
    success: bool
    message: str
    data: Any = None
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "command": self.command_name,
            "success": self.success,
            "message": self.message,
            "data": self.data,
            "duration_ms": self.duration_ms,
        }


class SkillCommandRegistry:
    """
    Structured skill command system for AI game development.

    Provides a unified command vocabulary that both human users
    and AI agents use to trigger game development operations.
    Each command has defined parameters, validation, and
    execution logic. This gives the agent a consistent,
    discoverable interface for all game creation tasks.
    """

    _instance: Optional["SkillCommandRegistry"] = None

    def __init__(self):
        self._commands: Dict[str, CommandDef] = {}
        self._alias_map: Dict[str, str] = {}
        self._history: List[CommandResult] = []
        self._lock = threading.Lock()
        self._MAX_HISTORY = 500
        self._register_default_commands()

    @classmethod
    def get_instance(cls) -> "SkillCommandRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def register(
        self,
        name: str,
        description: str,
        category: CommandCategory,
        parameters: Optional[List[CommandParameter]] = None,
        aliases: Optional[List[str]] = None,
        handler: Optional[Callable] = None,
        **kwargs,
    ) -> CommandDef:
        with self._lock:
            cmd = CommandDef(
                name=name,
                description=description,
                category=category,
                parameters=parameters or [],
                aliases=aliases or [],
                handler=handler,
                **kwargs,
            )
            self._commands[name] = cmd
            for alias in cmd.aliases:
                self._alias_map[alias] = name
            return cmd

    def execute(
        self, command_text: str, **context
    ) -> CommandResult:
        parts = command_text.strip().split()
        if not parts:
            return CommandResult(
                command_name="",
                success=False,
                message="Empty command",
            )

        cmd_name = parts[0].lstrip("/")
        resolved = self._alias_map.get(cmd_name, cmd_name)
        cmd = self._commands.get(resolved)

        if not cmd:
            return CommandResult(
                command_name=cmd_name,
                success=False,
                message=f"Unknown command: /{cmd_name}",
            )

        now = time.time()
        if cmd.cooldown_seconds > 0:
            elapsed = now - cmd._last_used
            if elapsed < cmd.cooldown_seconds:
                return CommandResult(
                    command_name=cmd.name,
                    success=False,
                    message=f"Command on cooldown ({cmd.cooldown_seconds - elapsed:.1f}s remaining)",
                )

        args = {}
        raw_args = parts[1:]
        for param in cmd.parameters:
            if raw_args:
                args[param.name] = raw_args.pop(0)
            elif param.required:
                return CommandResult(
                    command_name=cmd.name,
                    success=False,
                    message=f"Missing required parameter: {param.name}",
                )
            elif param.default is not None:
                args[param.name] = param.default

        started = time.time()
        cmd._last_used = now

        try:
            if cmd.handler:
                result_data = cmd.handler(args, context)
            else:
                result_data = {"message": f"Executed /{cmd.name}", "args": args}

            result = CommandResult(
                command_name=cmd.name,
                success=True,
                message=f"/{cmd.name} completed",
                data=result_data,
                duration_ms=(time.time() - started) * 1000,
            )
        except Exception as e:
            result = CommandResult(
                command_name=cmd.name,
                success=False,
                message=str(e),
                duration_ms=(time.time() - started) * 1000,
            )

        with self._lock:
            self._history.append(result)
            if len(self._history) > self._MAX_HISTORY:
                self._history = self._history[-self._MAX_HISTORY:]

        return result

    def get(self, name: str) -> Optional[CommandDef]:
        return self._commands.get(name) or self._commands.get(
            self._alias_map.get(name, "")
        )

    def list_commands(self, category: Optional[CommandCategory] = None) -> List[CommandDef]:
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        return sorted(cmds, key=lambda c: c.name)

    def list_categories(self) -> List[CommandCategory]:
        return list(CommandCategory)

    def get_history(self, limit: int = 20) -> List[CommandResult]:
        return self._history[-limit:]

    def get_last_result(self) -> Optional[CommandResult]:
        return self._history[-1] if self._history else None

    def get_help(self, command_name: str = "") -> str:
        if command_name:
            cmd = self.get(command_name)
            if not cmd:
                return f"No help for: /{command_name}"
            params = ", ".join(
                f"<{p.name}>" if p.required else f"[{p.name}]"
                for p in cmd.parameters
            )
            return f"/{cmd.name} {params} — {cmd.description}"
        lines = ["Available commands:"]
        by_cat: Dict[str, List[str]] = {}
        for cmd in self._commands.values():
            by_cat.setdefault(cmd.category.value, []).append(
                f"  /{cmd.name} — {cmd.description}"
            )
        for cat, entries in by_cat.items():
            lines.append(f"\n[{cat}]")
            lines.extend(entries)
        return "\n".join(lines)

    def _register_default_commands(self) -> None:
        defaults = [
            ("generate-sprite", "Generate a sprite from description", CommandCategory.GENERATE,
             [CommandParameter("description", "string", "Sprite description", True)]),
            ("generate-level", "Generate a game level procedurally", CommandCategory.GENERATE,
             [CommandParameter("theme", "string", "Level theme", False, "grassland")]),
            ("generate-code", "Generate game code", CommandCategory.GENERATE,
             [CommandParameter("language", "string", "Target language", True)]),
            ("analyze-scene", "Analyze current scene", CommandCategory.ANALYZE, []),
            ("analyze-performance", "Analyze game performance", CommandCategory.ANALYZE, []),
            ("analyze-assets", "Analyze project assets", CommandCategory.ANALYZE, []),
            ("build-game", "Build the current game", CommandCategory.BUILD,
             [CommandParameter("platform", "string", "Target platform", False, "web")]),
            ("build-asset", "Build/compile an asset", CommandCategory.BUILD,
             [CommandParameter("asset_path", "string", "Asset path", True)]),
            ("deploy-web", "Deploy game to web", CommandCategory.DEPLOY, []),
            ("edit-object", "Edit a game object", CommandCategory.EDIT,
             [CommandParameter("object_id", "string", "Object identifier", True)]),
            ("edit-scene", "Edit a scene", CommandCategory.EDIT,
             [CommandParameter("scene_name", "string", "Scene name", True)]),
            ("help", "Show command help", CommandCategory.UTILITY, []),
            ("status", "Show agent status", CommandCategory.UTILITY, []),
            ("undo", "Undo last action", CommandCategory.UTILITY, []),
            ("redo", "Redo last undone action", CommandCategory.UTILITY, []),
        ]
        for entry in defaults:
            params = entry[3] if len(entry) > 3 else []
            self.register(entry[0], entry[1], entry[2], params)

    def get_stats(self) -> dict:
        with self._lock:
            by_cat: Dict[str, int] = {}
            for cmd in self._commands.values():
                c = cmd.category.value
                by_cat[c] = by_cat.get(c, 0) + 1
            return {
                "total_commands": len(self._commands),
                "aliases": len(self._alias_map),
                "history_size": len(self._history),
                "by_category": by_cat,
            }

    def reset(self) -> None:
        with self._lock:
            self._commands.clear()
            self._alias_map.clear()
            self._history.clear()
            self._register_default_commands()


def get_skill_command_registry() -> SkillCommandRegistry:
    return SkillCommandRegistry.get_instance()
