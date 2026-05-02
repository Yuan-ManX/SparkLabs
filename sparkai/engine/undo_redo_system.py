"""
Undo/Redo System - Command history for the AI-native game editor.

Architecture:
    UndoRedoSystem/
    |-- EditorCommand (reversible action dataclass)
    |-- CommandBatch (grouped operations dataclass)
    |-- CommandHistory (bounded undo/redo stack)
    |-- UndoRedoSystem (global editor command orchestration)

Provides the undo/redo infrastructure for the AI game editor. Every
editor mutation — object creation, property changes, scene modifications,
behavior attachments — is wrapped in a reversible command. Supports
batched operations, mergeable commands, and bounded history.
"""

from __future__ import annotations

import uuid
import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Callable, Dict, List, Optional


class CommandTarget(Enum):
    SCENE = auto()
    OBJECT = auto()
    BEHAVIOR = auto()
    VARIABLE = auto()
    LAYER = auto()
    SHADER = auto()
    LIGHTING = auto()
    UI_ELEMENT = auto()
    PROJECT = auto()


@dataclass
class EditorCommand:
    command_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    target: CommandTarget = CommandTarget.OBJECT
    target_id: str = ""
    timestamp: float = 0.0
    do_action: Optional[Callable[[], Any]] = None
    undo_action: Optional[Callable[[], Any]] = None
    data_before: Optional[Dict[str, Any]] = None
    data_after: Optional[Dict[str, Any]] = None
    mergable: bool = False
    merge_key: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "label": self.label,
            "target": self.target.name,
            "target_id": self.target_id,
            "timestamp": self.timestamp,
        }


@dataclass
class CommandBatch:
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = ""
    commands: List[EditorCommand] = field(default_factory=list)
    timestamp: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "batch_id": self.batch_id,
            "label": self.label,
            "command_count": len(self.commands),
            "commands": [c.to_dict() for c in self.commands],
        }


class CommandHistory:
    def __init__(self, max_size: int = 100):
        self._undo_stack: List[EditorCommand] = []
        self._redo_stack: List[EditorCommand] = []
        self._max_size: int = max_size
        self._total_executed: int = 0
        self._total_undone: int = 0

    def push(self, command: EditorCommand) -> None:
        command.timestamp = time.time()

        if command.mergable and self._undo_stack:
            last = self._undo_stack[-1]
            if last.mergable and last.merge_key == command.merge_key:
                last.data_after = command.data_after
                last.label = command.label
                return

        self._undo_stack.append(command)
        self._redo_stack.clear()
        self._total_executed += 1

        if len(self._undo_stack) > self._max_size:
            self._undo_stack = self._undo_stack[-self._max_size:]

    def undo(self) -> Optional[EditorCommand]:
        if not self._undo_stack:
            return None
        command = self._undo_stack.pop()
        if command.undo_action:
            command.undo_action()
        self._redo_stack.append(command)
        self._total_undone += 1
        return command

    def redo(self) -> Optional[EditorCommand]:
        if not self._redo_stack:
            return None
        command = self._redo_stack.pop()
        if command.do_action:
            command.do_action()
        self._undo_stack.append(command)
        self._total_executed += 1
        return command

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def can_redo(self) -> bool:
        return len(self._redo_stack) > 0

    def peek_undo(self) -> Optional[EditorCommand]:
        return self._undo_stack[-1] if self._undo_stack else None

    def peek_redo(self) -> Optional[EditorCommand]:
        return self._redo_stack[-1] if self._redo_stack else None

    def get_undo_stack_size(self) -> int:
        return len(self._undo_stack)

    def get_redo_stack_size(self) -> int:
        return len(self._redo_stack)

    def clear(self) -> None:
        self._undo_stack.clear()
        self._redo_stack.clear()

    def get_stats(self) -> Dict[str, Any]:
        return {
            "undo_size": len(self._undo_stack),
            "redo_size": len(self._redo_stack),
            "total_executed": self._total_executed,
            "total_undone": self._total_undone,
            "max_size": self._max_size,
            "last_undo": self.peek_undo().label if self._undo_stack else None,
            "last_redo": self.peek_redo().label if self._redo_stack else None,
        }


class UndoRedoSystem:
    _instance: Optional["UndoRedoSystem"] = None

    def __init__(self):
        self._history = CommandHistory()
        self._active_batch: Optional[CommandBatch] = None
        self._enabled: bool = True

    @classmethod
    def get_instance(cls) -> "UndoRedoSystem":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def execute(self, label: str, target: CommandTarget, target_id: str,
                do_action: Callable[[], Any],
                undo_action: Callable[[], Any],
                data_before: Optional[Dict[str, Any]] = None,
                data_after: Optional[Dict[str, Any]] = None,
                mergable: bool = False,
                merge_key: str = "") -> Optional[EditorCommand]:
        if not self._enabled:
            do_action()
            return None

        command = EditorCommand(
            label=label,
            target=target,
            target_id=target_id,
            do_action=do_action,
            undo_action=undo_action,
            data_before=data_before,
            data_after=data_after,
            mergable=mergable,
            merge_key=merge_key,
        )

        result = do_action()

        if self._active_batch:
            self._active_batch.commands.append(command)
        else:
            self._history.push(command)

        return command

    def begin_batch(self, label: str = "") -> CommandBatch:
        if self._active_batch:
            self.end_batch()
        self._active_batch = CommandBatch(label=label, timestamp=time.time())
        return self._active_batch

    def end_batch(self) -> Optional[CommandBatch]:
        if not self._active_batch:
            return None
        batch = self._active_batch
        self._active_batch = None

        if batch.commands:
            first_cmd = batch.commands[0]
            first_cmd.do_action = lambda: [c.do_action() for c in batch.commands if c.do_action]
            first_cmd.undo_action = lambda: [c.undo_action() for c in reversed(batch.commands) if c.undo_action]
            first_cmd.label = batch.label
            self._history.push(first_cmd)

        return batch

    def undo(self) -> Optional[EditorCommand]:
        if self._active_batch:
            self.end_batch()
        return self._history.undo()

    def redo(self) -> Optional[EditorCommand]:
        return self._history.redo()

    def can_undo(self) -> bool:
        return self._history.can_undo()

    def can_redo(self) -> bool:
        return self._history.can_redo()

    def get_undo_label(self) -> Optional[str]:
        cmd = self._history.peek_undo()
        return cmd.label if cmd else None

    def get_redo_label(self) -> Optional[str]:
        cmd = self._history.peek_redo()
        return cmd.label if cmd else None

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def clear_history(self) -> None:
        self._history.clear()

    def set_max_history(self, max_size: int) -> None:
        self._history._max_size = max(1, max_size)

    def get_stats(self) -> Dict[str, Any]:
        stats = self._history.get_stats()
        stats.update({
            "enabled": self._enabled,
            "has_active_batch": self._active_batch is not None,
        })
        return stats


def get_undo_redo_system() -> UndoRedoSystem:
    return UndoRedoSystem.get_instance()
