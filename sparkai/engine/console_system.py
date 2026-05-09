"""
SparkLabs Engine - Console System

In-game developer console for runtime debugging, command
execution, and live system inspection. Provides a Godot-style
command interface with auto-completion, command history,
variable inspection, and system control during gameplay.

Architecture:
  ConsoleSystem
    |-- CommandRegistry (register/unregister console commands)
    |-- CommandParser (tokenize and validate input strings)
    |-- HistoryBuffer (navigate previous commands with up/down)
    |-- AutoComplete (tab-completion for commands and arguments)
    |-- OutputBuffer (scrollable console output with color tags)

Command Categories:
  - SYSTEM: engine control (pause, step, quit)
  - ENTITY: spawn, destroy, list entities
  - DEBUG: log levels, draw modes, profiling
  - SCENE: scene switching, loading
  - PHYSICS: gravity, constraints debug
  - GRAPHICS: FPS display, wireframe mode
"""

from __future__ import annotations

import shlex
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class ConsoleLogLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    COMMAND = "command"


@dataclass
class ConsoleLine:
    text: str = ""
    level: ConsoleLogLevel = ConsoleLogLevel.INFO
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "level": self.level.value,
            "timestamp": self.timestamp,
        }


@dataclass
class CommandDef:
    name: str = ""
    description: str = ""
    category: str = "system"
    syntax: str = ""
    handler: Optional[Callable] = None
    arg_count: int = 0
    usage: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "syntax": self.syntax,
            "usage": self.usage,
        }


class ConsoleSystem:
    """In-game developer console for runtime debugging and control."""

    _instance: Optional["ConsoleSystem"] = None
    _lock = threading.Lock()

    MAX_HISTORY = 500
    MAX_OUTPUT_LINES = 2000
    MAX_COMMANDS = 300

    def __init__(self):
        self._commands: Dict[str, CommandDef] = {}
        self._history: deque = deque(maxlen=self.MAX_HISTORY)
        self._output: deque = deque(maxlen=self.MAX_OUTPUT_LINES)
        self._cvars: Dict[str, Any] = {}
        self._history_index: int = 0
        self._enabled: bool = True
        self._register_default_commands()

    @classmethod
    def get_instance(cls) -> "ConsoleSystem":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _register_default_commands(self) -> None:
        defaults = [
            CommandDef("help", "Show available commands", "system", "help [command]"),
            CommandDef("echo", "Print message to console", "system", "echo <text>", arg_count=1),
            CommandDef("clear", "Clear console output", "system", "clear"),
            CommandDef("quit", "Exit the game", "system", "quit"),
            CommandDef("pause", "Pause/unpause game", "system", "pause"),
            CommandDef("step", "Advance one frame", "system", "step"),
            CommandDef("fps", "Show/hide FPS counter", "graphics", "fps [on/off]", arg_count=1),
            CommandDef("wireframe", "Toggle wireframe rendering", "graphics", "wireframe"),
            CommandDef("list_entities", "List all active entities", "entity", "list_entities [filter]", arg_count=1),
            CommandDef("entity_count", "Show entity count", "entity", "entity_count"),
            CommandDef("spawn", "Spawn an entity at position", "entity", "spawn <type> <x> <y>", arg_count=3),
            CommandDef("destroy", "Destroy entity by ID", "entity", "destroy <entity_id>", arg_count=1),
            CommandDef("list_scenes", "List loaded scenes", "scene", "list_scenes"),
            CommandDef("load_scene", "Load a scene by name", "scene", "load_scene <name>", arg_count=1),
            CommandDef("gravity", "Set/get gravity", "physics", "gravity [value]", arg_count=1),
            CommandDef("debug_collision", "Show collision shapes", "debug", "debug_collision [on/off]", arg_count=1),
            CommandDef("log_level", "Set log verbosity", "debug", "log_level <0-3>", arg_count=1),
            CommandDef("profile", "Start/stop profiler", "debug", "profile [start/stop]"),
            CommandDef("stats", "Show engine statistics", "system", "stats"),
            CommandDef("time_scale", "Set game time scale", "system", "time_scale <value>", arg_count=1),
        ]
        for cmd in defaults:
            self._commands[cmd.name] = cmd

    def register_command(
        self,
        name: str,
        description: str = "",
        category: str = "system",
        syntax: str = "",
        handler: Optional[Callable] = None,
    ) -> CommandDef:
        cmd = CommandDef(
            name=name,
            description=description,
            category=category,
            syntax=syntax,
            handler=handler,
            usage=syntax,
        )
        self._commands[name] = cmd
        return cmd

    def register_cvar(self, name: str, default_value: Any) -> None:
        self._cvars[name] = default_value

    def get_cvar(self, name: str) -> Optional[Any]:
        return self._cvars.get(name)

    def set_cvar(self, name: str, value: Any) -> bool:
        if name in self._cvars:
            self._cvars[name] = value
            return True
        return False

    def execute(self, command_line: str) -> str:
        if not command_line.strip():
            return ""

        self._history.append(command_line)
        self._history_index = len(self._history)
        self._write(command_line, ConsoleLogLevel.COMMAND)

        parts = shlex.split(command_line)
        if not parts:
            return ""

        cmd_name = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd_name not in self._commands:
            msg = f"Unknown command: '{cmd_name}'. Type 'help' for available commands."
            self._write(msg, ConsoleLogLevel.ERROR)
            return msg

        cmd = self._commands[cmd_name]

        if cmd.handler:
            try:
                result = cmd.handler(args)
                self._write(str(result), ConsoleLogLevel.SUCCESS)
                return str(result)
            except Exception as exc:
                msg = f"Command error: {exc}"
                self._write(msg, ConsoleLogLevel.ERROR)
                return msg

        return self._execute_builtin(cmd_name, args)

    def _execute_builtin(self, cmd_name: str, args: List[str]) -> str:
        if cmd_name == "help":
            if args:
                cmd = self._commands.get(args[0])
                if cmd:
                    msg = f"  {cmd.name} - {cmd.description}\n  Usage: {cmd.usage}"
                else:
                    msg = f"No command: {args[0]}"
            else:
                cats: Dict[str, List[str]] = {}
                for cmd in self._commands.values():
                    cats.setdefault(cmd.category, []).append(cmd.name)
                lines = ["Available commands:"]
                for cat, names in sorted(cats.items()):
                    lines.append(f"  [{cat}] {', '.join(names)}")
                msg = "\n".join(lines)
            self._write(msg, ConsoleLogLevel.INFO)
            return msg

        elif cmd_name == "echo":
            msg = " ".join(args)
            self._write(msg, ConsoleLogLevel.INFO)
            return msg

        elif cmd_name == "clear":
            self._output.clear()
            return ""

        elif cmd_name == "stats":
            msg = (
                f"Commands: {len(self._commands)}\n"
                f"CVars: {len(self._cvars)}\n"
                f"History: {len(self._history)}\n"
                f"Output lines: {len(self._output)}"
            )
            self._write(msg, ConsoleLogLevel.INFO)
            return msg

        elif cmd_name == "list_entities":
            filter_term = args[0] if args else ""
            msg = f"Entity list (filter: '{filter_term}'): mock engine data"
            self._write(msg, ConsoleLogLevel.INFO)
            return msg

        elif cmd_name in ("fps", "wireframe", "debug_collision", "pause", "step", "profile"):
            arg = args[0] if args else "toggled"
            msg = f"{cmd_name}: {arg}"
            self._write(msg, ConsoleLogLevel.SUCCESS)
            return msg

        elif cmd_name == "quit":
            self._write("Shutting down...", ConsoleLogLevel.WARNING)
            return "quit"

        return ""

    def _write(self, text: str, level: ConsoleLogLevel = ConsoleLogLevel.INFO) -> None:
        self._output.append(ConsoleLine(text=text, level=level))

    def get_output(
        self, limit: int = 50, level: Optional[ConsoleLogLevel] = None
    ) -> List[ConsoleLine]:
        lines = list(self._output)
        if level:
            lines = [l for l in lines if l.level == level]
        return lines[-limit:]

    def get_history(self, limit: int = 20) -> List[str]:
        return list(self._history)[-limit:]

    def autocomplete(self, prefix: str) -> List[str]:
        if not prefix:
            return []
        prefix_l = prefix.lower()
        return [
            name for name in self._commands
            if name.startswith(prefix_l)
        ]

    def navigate_history(self, direction: int) -> Optional[str]:
        """direction: -1 for up (previous), 1 for down (next)"""
        if not self._history:
            return None
        self._history_index += direction
        self._history_index = max(0, min(len(self._history) - 1, self._history_index))
        if 0 <= self._history_index < len(self._history):
            return list(self._history)[self._history_index]
        return None

    def get_command(self, name: str) -> Optional[CommandDef]:
        return self._commands.get(name)

    def list_commands(self, category: Optional[str] = None) -> List[CommandDef]:
        cmds = list(self._commands.values())
        if category:
            cmds = [c for c in cmds if c.category == category]
        return cmds

    def list_categories(self) -> List[str]:
        return sorted(set(c.category for c in self._commands.values()))

    def get_stats(self) -> Dict[str, Any]:
        return {
            "commands": len(self._commands),
            "categories": len(self.list_categories()),
            "cvars": len(self._cvars),
            "history_lines": len(self._history),
            "output_lines": len(self._output),
            "enabled": self._enabled,
        }


def get_console_system() -> ConsoleSystem:
    return ConsoleSystem.get_instance()