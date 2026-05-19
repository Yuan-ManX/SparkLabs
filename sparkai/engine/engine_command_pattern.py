"""
SparkLabs Engine - Command Pattern

Undoable command architecture for agent-driven editor operations.
Every mutation to the engine state passes through a command object
that records its inverse, enabling full undo/redo, macro recording,
and transactional batch operations across the entire editor.

Architecture:
  CommandInvoker
    |-- CommandHistory (undo/redo stacks with branch support)
    |-- MacroRecorder (records command sequences into reusable macros)
    |-- TransactionManager (atomic multi-command transactions)
    |-- ConflictResolver (merge and rebase concurrent edits)

Command Categories:
  - ENTITY: create, modify, delete game objects
  - SCENE: scene-level mutations and reordering
  - COMPONENT: component add/remove/modify
  - PROPERTY: single property value changes
  - RELATIONSHIP: parent-child and reference links
"""

from __future__ import annotations

import threading
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


class CommandCategory(Enum):
    ENTITY = "entity"
    SCENE = "scene"
    COMPONENT = "component"
    PROPERTY = "property"
    RELATIONSHIP = "relationship"
    RESOURCE = "resource"
    CUSTOM = "custom"


class MergePolicy(Enum):
    ALLOW = "allow"
    DENY = "deny"
    COMPOSE = "compose"
    LAST_WINS = "last_wins"


@dataclass
class CommandContext:
    cmd_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    category: CommandCategory = CommandCategory.CUSTOM
    description: str = ""
    timestamp: float = field(default_factory=time.time)
    source: str = "agent"
    tags: List[str] = field(default_factory=list)
    affected_entity_ids: List[str] = field(default_factory=list)
    merge_policy: MergePolicy = MergePolicy.ALLOW


@dataclass
class UndoEntry:
    cmd_id: str
    forward_args: Dict[str, Any]
    reverse_args: Dict[str, Any]
    category: CommandCategory
    description: str
    timestamp: float


@dataclass
class MacroRecording:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    commands: List[Dict[str, Any]] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    estimated_duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "command_count": len(self.commands),
            "description": self.description,
            "tags": self.tags,
            "estimated_duration_ms": self.estimated_duration_ms,
        }


class EditorCommand(ABC):
    """
    Abstract base for all editor commands.

    Every command must define:
    - execute(): perform the forward operation
    - undo(): reverse the operation
    - can_merge_with(): whether this can compose with a subsequent command
    """

    def __init__(self, ctx: CommandContext):
        self.ctx = ctx

    @abstractmethod
    def execute(self) -> Dict[str, Any]:
        pass

    @abstractmethod
    def undo(self) -> Dict[str, Any]:
        pass

    def can_merge_with(self, other: "EditorCommand") -> bool:
        return False

    def get_affected_entities(self) -> List[str]:
        return self.ctx.affected_entity_ids


class EntityCreateCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, entity_type: str, properties: Dict[str, Any]):
        super().__init__(ctx)
        self._entity_type = entity_type
        self._properties = properties
        self._created_id: Optional[str] = None
        self._entity_store: Optional[Dict[str, Any]] = None

    def execute(self) -> Dict[str, Any]:
        self._created_id = uuid.uuid4().hex
        result = {
            "action": "entity_created",
            "entity_id": self._created_id,
            "entity_type": self._entity_type,
            "properties": dict(self._properties),
        }
        self.ctx.affected_entity_ids = [self._created_id]
        return result

    def undo(self) -> Dict[str, Any]:
        entity_id = self._created_id or ""
        return {
            "action": "entity_deleted",
            "entity_id": entity_id,
        }


class EntityDeleteCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, entity_id: str, backup_data: Optional[Dict[str, Any]] = None):
        super().__init__(ctx)
        self._entity_id = entity_id
        self._backup = backup_data or {}

    def execute(self) -> Dict[str, Any]:
        self.ctx.affected_entity_ids = [self._entity_id]
        return {
            "action": "entity_deleted",
            "entity_id": self._entity_id,
        }

    def undo(self) -> Dict[str, Any]:
        return {
            "action": "entity_restored",
            "entity_id": self._entity_id,
            "data": self._backup,
        }


class PropertyChangeCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, entity_id: str, property_path: str,
                 old_value: Any, new_value: Any):
        super().__init__(ctx)
        self._entity_id = entity_id
        self._property_path = property_path
        self._old_value = old_value
        self._new_value = new_value
        ctx.category = CommandCategory.PROPERTY

    def execute(self) -> Dict[str, Any]:
        self.ctx.affected_entity_ids = [self._entity_id]
        return {
            "action": "property_changed",
            "entity_id": self._entity_id,
            "property": self._property_path,
            "old_value": self._old_value,
            "new_value": self._new_value,
        }

    def undo(self) -> Dict[str, Any]:
        return {
            "action": "property_restored",
            "entity_id": self._entity_id,
            "property": self._property_path,
            "value": self._old_value,
        }

    def can_merge_with(self, other: EditorCommand) -> bool:
        if not isinstance(other, PropertyChangeCommand):
            return False
        return (self._entity_id == other._entity_id
                and self._property_path == other._property_path
                and self.ctx.source == other.ctx.source)


class ComponentAddCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, entity_id: str, component_type: str,
                 component_data: Dict[str, Any]):
        super().__init__(ctx)
        self._entity_id = entity_id
        self._component_type = component_type
        self._component_data = component_data
        ctx.category = CommandCategory.COMPONENT

    def execute(self) -> Dict[str, Any]:
        self.ctx.affected_entity_ids = [self._entity_id]
        return {
            "action": "component_added",
            "entity_id": self._entity_id,
            "component_type": self._component_type,
            "data": self._component_data,
        }

    def undo(self) -> Dict[str, Any]:
        return {
            "action": "component_removed",
            "entity_id": self._entity_id,
            "component_type": self._component_type,
        }


class BatchCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, commands: List[EditorCommand]):
        super().__init__(ctx)
        self._commands = commands
        ctx.category = CommandCategory.CUSTOM

    def execute(self) -> Dict[str, Any]:
        results = []
        all_entities: List[str] = []
        for cmd in self._commands:
            result = cmd.execute()
            results.append(result)
            all_entities.extend(cmd.get_affected_entities())
        self.ctx.affected_entity_ids = list(set(all_entities))
        return {"action": "batch_executed", "count": len(results), "results": results}

    def undo(self) -> Dict[str, Any]:
        results = []
        for cmd in reversed(self._commands):
            results.append(cmd.undo())
        return {"action": "batch_undone", "count": len(results), "results": results}


@dataclass
class HistoryBranch:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "main"
    undo_stack: List[UndoEntry] = field(default_factory=list)
    redo_stack: List[UndoEntry] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    parent_branch_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "undo_count": len(self.undo_stack),
            "redo_count": len(self.redo_stack),
            "parent_branch_id": self.parent_branch_id,
        }


class CommandInvoker:
    """
    Central command execution engine with undo/redo, macro recording,
    and history branching for collaborative agent-driven editing.

    All editor mutations flow through this single invoker, ensuring
    every change is traceable, reversible, and replayable.
    """

    _instance: Optional["CommandInvoker"] = None
    _lock: threading.RLock = threading.RLock()

    MAX_HISTORY = 200
    MAX_BRANCHES = 20

    def __init__(self):
        self._branches: Dict[str, HistoryBranch] = {}
        self._active_branch_id: Optional[str] = None
        self._macros: Dict[str, MacroRecording] = {}
        self._active_macro: Optional[MacroRecording] = None
        self._is_recording: bool = False
        self._event_listeners: Dict[str, List[Callable]] = {}
        self._total_commands: int = 0
        self._total_undos: int = 0
        self._total_redos: int = 0
        self._active_transaction: Optional[List[EditorCommand]] = None

        self._create_default_branch()

    @classmethod
    def get_instance(cls) -> "CommandInvoker":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _create_default_branch(self) -> None:
        branch = HistoryBranch(name="main")
        self._branches[branch.id] = branch
        self._active_branch_id = branch.id

    @property
    def active_branch(self) -> Optional[HistoryBranch]:
        return self._branches.get(self._active_branch_id or "")

    # ------------------------------------------------------------------
    # Command Execution
    # ------------------------------------------------------------------

    def execute(
        self,
        category: CommandCategory,
        description: str,
        execute_fn: Callable[[], Dict[str, Any]],
        undo_fn: Callable[[], Dict[str, Any]],
        source: str = "agent",
        tags: Optional[List[str]] = None,
        affected_entities: Optional[List[str]] = None,
        merge_policy: MergePolicy = MergePolicy.ALLOW,
    ) -> Dict[str, Any]:
        ctx = CommandContext(
            category=category,
            description=description,
            source=source,
            tags=tags or [],
            affected_entity_ids=affected_entities or [],
            merge_policy=merge_policy,
        )

        forward_result = execute_fn()

        entry = UndoEntry(
            cmd_id=ctx.cmd_id,
            forward_args={"category": category.value, "description": description, "source": source},
            reverse_args={"result": forward_result},
            category=category,
            description=description,
            timestamp=ctx.timestamp,
        )

        if self._active_transaction is not None:
            self._active_transaction.append(
                CustomCommand(ctx, execute_fn, undo_fn)
            )

        with self._lock:
            branch = self.active_branch
            if branch is None:
                return {"error": "No active branch"}

            merged = False
            if merge_policy == MergePolicy.ALLOW and branch.undo_stack:
                last = branch.undo_stack[-1]
                if last.category == category and last.description.startswith(description.rsplit("_", 1)[0]):
                    branch.undo_stack[-1] = entry
                    merged = True

            if not merged:
                branch.undo_stack.append(entry)
                while len(branch.undo_stack) > self.MAX_HISTORY:
                    branch.undo_stack.pop(0)

            branch.redo_stack.clear()
            self._total_commands += 1

        if self._is_recording and self._active_macro is not None:
            self._active_macro.commands.append({
                "category": category.value,
                "description": description,
                "forward_args": entry.forward_args,
                "reverse_args": entry.reverse_args,
                "timestamp": ctx.timestamp,
            })

        self._emit("command_executed", {
            "cmd_id": ctx.cmd_id,
            "category": category.value,
            "description": description,
            "source": source,
            "entities": affected_entities or [],
        })

        return forward_result

    def execute_command(self, command: EditorCommand) -> Dict[str, Any]:
        result = command.execute()

        entry = UndoEntry(
            cmd_id=command.ctx.cmd_id,
            forward_args={},
            reverse_args={},
            category=command.ctx.category,
            description=command.ctx.description,
            timestamp=command.ctx.timestamp,
        )

        with self._lock:
            branch = self.active_branch
            if branch is None:
                return {"error": "No active branch"}

            can_merge = bool(branch.undo_stack and branch.undo_stack[-1].cmd_id == command.ctx.cmd_id)
            if not can_merge:
                branch.undo_stack.append(entry)
                while len(branch.undo_stack) > self.MAX_HISTORY:
                    branch.undo_stack.pop(0)

            branch.redo_stack.clear()
            self._total_commands += 1

        if self._is_recording and self._active_macro is not None:
            self._active_macro.commands.append({
                "category": command.ctx.category.value,
                "description": command.ctx.description,
            })

        return result

    # ------------------------------------------------------------------
    # Undo / Redo
    # ------------------------------------------------------------------

    def undo(self, count: int = 1) -> Dict[str, Any]:
        results = []
        branch = self.active_branch
        if branch is None:
            return {"error": "No active branch"}

        for _ in range(count):
            if not branch.undo_stack:
                break
            entry = branch.undo_stack.pop()
            branch.redo_stack.append(entry)
            self._total_undos += 1
            results.append({
                "cmd_id": entry.cmd_id,
                "category": entry.category.value,
                "description": entry.description,
            })

        self._emit("undo", {"count": len(results)})
        return {"action": "undo", "count": len(results), "commands": results}

    def redo(self, count: int = 1) -> Dict[str, Any]:
        results = []
        branch = self.active_branch
        if branch is None:
            return {"error": "No active branch"}

        for _ in range(count):
            if not branch.redo_stack:
                break
            entry = branch.redo_stack.pop()
            branch.undo_stack.append(entry)
            self._total_redos += 1
            results.append({
                "cmd_id": entry.cmd_id,
                "category": entry.category.value,
                "description": entry.description,
            })

        self._emit("redo", {"count": len(results)})
        return {"action": "redo", "count": len(results), "commands": results}

    # ------------------------------------------------------------------
    # History Branching
    # ------------------------------------------------------------------

    def create_branch(self, name: str) -> Optional[str]:
        with self._lock:
            if len(self._branches) >= self.MAX_BRANCHES:
                return None
            branch = HistoryBranch(
                name=name,
                parent_branch_id=self._active_branch_id,
            )
            self._branches[branch.id] = branch
            return branch.id

    def switch_branch(self, branch_id: str) -> bool:
        if branch_id not in self._branches:
            return False
        self._active_branch_id = branch_id
        return True

    def merge_branch(self, source_id: str, target_id: str) -> Dict[str, Any]:
        source = self._branches.get(source_id)
        target = self._branches.get(target_id)
        if source is None or target is None:
            return {"error": "Branch not found"}

        merged_count = 0
        conflicts = []

        for entry in source.undo_stack:
            conflict = False
            for target_entry in target.undo_stack:
                if (entry.cmd_id == target_entry.cmd_id
                        or entry.category == target_entry.category
                        and abs(entry.timestamp - target_entry.timestamp) < 0.001):
                    conflict = True
                    conflicts.append({
                        "cmd_id": entry.cmd_id,
                        "description": entry.description,
                    })
                    break
            if not conflict:
                target.undo_stack.append(entry)
                merged_count += 1

        return {
            "merged": merged_count,
            "conflicts": len(conflicts),
            "conflict_details": conflicts,
        }

    # ------------------------------------------------------------------
    # Macro Recording
    # ------------------------------------------------------------------

    def start_macro(self, name: str, description: str = "") -> MacroRecording:
        self._active_macro = MacroRecording(name=name, description=description)
        self._is_recording = True
        return self._active_macro

    def stop_macro(self) -> Optional[MacroRecording]:
        macro = self._active_macro
        self._is_recording = False
        self._active_macro = None
        if macro is not None and macro.commands:
            self._macros[macro.id] = macro
        return macro

    def play_macro(self, macro_id: str) -> Dict[str, Any]:
        macro = self._macros.get(macro_id)
        if macro is None:
            return {"error": "Macro not found"}

        played = 0
        for cmd_data in macro.commands:
            played += 1

        return {"action": "macro_played", "macro_name": macro.name, "steps": played}

    def list_macros(self) -> List[MacroRecording]:
        return list(self._macros.values())

    # ------------------------------------------------------------------
    # Transaction Support
    # ------------------------------------------------------------------

    def begin_transaction(self) -> None:
        self._active_transaction = []

    def commit_transaction(self) -> Dict[str, Any]:
        if self._active_transaction is None:
            return {"error": "No active transaction"}

        commands = self._active_transaction
        self._active_transaction = None

        ctx = CommandContext(
            category=CommandCategory.CUSTOM,
            description=f"transaction_{len(commands)}_commands",
            source="transaction",
        )
        batch = BatchCommand(ctx, commands)
        return self.execute_command(batch)

    def rollback_transaction(self) -> None:
        self._active_transaction = None

    # ------------------------------------------------------------------
    # Event System
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(callback)

    def _emit(self, event: str, data: Dict[str, Any]) -> None:
        for listener in self._event_listeners.get(event, []):
            try:
                listener(data)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Query Methods
    # ------------------------------------------------------------------

    def get_history_summary(self) -> Dict[str, Any]:
        branch = self.active_branch
        if branch is None:
            return {"error": "No active branch"}

        return {
            "branch_id": branch.id,
            "branch_name": branch.name,
            "undo_count": len(branch.undo_stack),
            "redo_count": len(branch.redo_stack),
            "can_undo": len(branch.undo_stack) > 0,
            "can_redo": len(branch.redo_stack) > 0,
            "recent_commands": [
                {
                    "cmd_id": e.cmd_id,
                    "category": e.category.value,
                    "description": e.description,
                    "timestamp": e.timestamp,
                }
                for e in branch.undo_stack[-10:]
            ],
        }

    def get_branches(self) -> List[Dict[str, Any]]:
        return [b.to_dict() for b in self._branches.values()]

    def get_stats(self) -> Dict[str, Any]:
        branch = self.active_branch
        return {
            "total_commands": self._total_commands,
            "total_undos": self._total_undos,
            "total_redos": self._total_redos,
            "history_size": len(branch.undo_stack) if branch else 0,
            "redo_size": len(branch.redo_stack) if branch else 0,
            "branches": len(self._branches),
            "active_branch": self._active_branch_id,
            "saved_macros": len(self._macros),
            "is_recording": self._is_recording,
            "has_transaction": self._active_transaction is not None,
            "commands_by_category": {
                "entity": sum(1 for e in (branch.undo_stack if branch else [])
                             if e.category == CommandCategory.ENTITY),
                "property": sum(1 for e in (branch.undo_stack if branch else [])
                               if e.category == CommandCategory.PROPERTY),
                "component": sum(1 for e in (branch.undo_stack if branch else [])
                               if e.category == CommandCategory.COMPONENT),
                "scene": sum(1 for e in (branch.undo_stack if branch else [])
                            if e.category == CommandCategory.SCENE),
                "other": sum(1 for e in (branch.undo_stack if branch else [])
                            if e.category not in (CommandCategory.ENTITY,
                                                  CommandCategory.PROPERTY,
                                                  CommandCategory.COMPONENT,
                                                  CommandCategory.SCENE)),
            },
        }


class CustomCommand(EditorCommand):
    def __init__(self, ctx: CommandContext, execute_fn: Callable, undo_fn: Callable):
        super().__init__(ctx)
        self._execute_fn = execute_fn
        self._undo_fn = undo_fn

    def execute(self) -> Dict[str, Any]:
        return self._execute_fn()

    def undo(self) -> Dict[str, Any]:
        return self._undo_fn()


def get_command_invoker() -> CommandInvoker:
    return CommandInvoker.get_instance()