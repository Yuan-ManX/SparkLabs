"""
SparkAI Agent - Subagent Spawner Engine

Provides hierarchical subagent spawning with isolated context,
restricted toolsets, depth bounds, and result collection.
Prevents unbounded recursive delegation and resource exhaustion.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set


class SubagentRole(Enum):
    WORKER = "worker"
    RESEARCHER = "researcher"
    CODER = "coder"
    REVIEWER = "reviewer"
    TESTER = "tester"


class SubagentState(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMED_OUT = "timed_out"
    CANCELLED = "cancelled"


BLOCKED_TOOLS_DEFAULT = {
    "delegate_task",
    "spawn_subagent",
    "send_message",
    "manage_credentials",
}

BLOCKED_TOOLS_WORKER = {
    "delegate_task",
    "spawn_subagent",
    "send_message",
    "manage_credentials",
    "create_agent",
    "modify_policy",
}

BLOCKED_TOOLS_REVIEWER = {
    "delegate_task",
    "spawn_subagent",
    "manage_credentials",
    "create_agent",
    "modify_policy",
    "write_file",
    "delete_file",
}


@dataclass
class SubagentConfig:
    role: SubagentRole = SubagentRole.WORKER
    max_spawn_depth: int = 2
    timeout_seconds: float = 600.0
    max_iterations: int = 20
    inherit_memory: bool = False
    inherit_game_context: bool = True
    allowed_tools: Optional[Set[str]] = None
    blocked_tools: Set[str] = field(default_factory=lambda: BLOCKED_TOOLS_DEFAULT)
    system_prompt_override: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_effective_blocked_tools(self) -> Set[str]:
        if self.role == SubagentRole.WORKER:
            return self.blocked_tools | BLOCKED_TOOLS_WORKER
        elif self.role == SubagentRole.REVIEWER:
            return self.blocked_tools | BLOCKED_TOOLS_REVIEWER
        return self.blocked_tools

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role.value,
            "max_spawn_depth": self.max_spawn_depth,
            "timeout_seconds": self.timeout_seconds,
            "max_iterations": self.max_iterations,
            "inherit_memory": self.inherit_memory,
            "inherit_game_context": self.inherit_game_context,
            "blocked_tools": list(self.get_effective_blocked_tools()),
        }


@dataclass
class SubagentResult:
    subagent_id: str
    parent_id: str
    task_description: str
    state: SubagentState = SubagentState.PENDING
    output: Any = None
    error: Optional[str] = None
    iterations_used: int = 0
    tools_called: List[str] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    spawn_depth: int = 0

    @property
    def duration_seconds(self) -> float:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subagent_id": self.subagent_id,
            "parent_id": self.parent_id,
            "task_description": self.task_description[:200],
            "state": self.state.value,
            "error": self.error[:200] if self.error else None,
            "iterations_used": self.iterations_used,
            "tools_called": self.tools_called,
            "files_read": self.files_read,
            "files_written": self.files_written,
            "duration_seconds": self.duration_seconds,
            "spawn_depth": self.spawn_depth,
        }


@dataclass
class SpawnRequest:
    parent_id: str
    task_description: str
    config: SubagentConfig = field(default_factory=SubagentConfig)
    input_data: Dict[str, Any] = field(default_factory=dict)
    current_depth: int = 0


class SubagentSpawner:
    """
    Manages hierarchical subagent spawning with depth bounds,
    restricted toolsets, and result collection.
    """

    MAX_SPAWN_DEPTH = 3
    MAX_CONCURRENT_SUBAGENTS = 8

    def __init__(self):
        self._active_subagents: Dict[str, SubagentResult] = {}
        self._completed_subagents: Dict[str, SubagentResult] = {}
        self._spawn_history: List[Dict[str, Any]] = []
        self._stats = {
            "total_spawned": 0,
            "total_completed": 0,
            "total_failed": 0,
            "total_timed_out": 0,
            "depth_violations": 0,
            "concurrency_limit_hits": 0,
        }

    def can_spawn(self, current_depth: int) -> bool:
        if current_depth >= self.MAX_SPAWN_DEPTH:
            self._stats["depth_violations"] += 1
            return False
        if len(self._active_subagents) >= self.MAX_CONCURRENT_SUBAGENTS:
            self._stats["concurrency_limit_hits"] += 1
            return False
        return True

    def create_subagent(self, request: SpawnRequest) -> SubagentResult:
        if not self.can_spawn(request.current_depth):
            result = SubagentResult(
                subagent_id=str(uuid.uuid4())[:12],
                parent_id=request.parent_id,
                task_description=request.task_description,
                state=SubagentState.FAILED,
                error=f"Cannot spawn: depth={request.current_depth}, max={self.MAX_SPAWN_DEPTH}",
                spawn_depth=request.current_depth,
            )
            return result

        subagent_id = str(uuid.uuid4())[:12]
        result = SubagentResult(
            subagent_id=subagent_id,
            parent_id=request.parent_id,
            task_description=request.task_description,
            state=SubagentState.PENDING,
            spawn_depth=request.current_depth + 1,
        )

        self._active_subagents[subagent_id] = result
        self._stats["total_spawned"] += 1

        self._spawn_history.append({
            "subagent_id": subagent_id,
            "parent_id": request.parent_id,
            "task": request.task_description[:100],
            "depth": request.current_depth + 1,
            "role": request.config.role.value,
            "timestamp": time.time(),
        })

        return result

    def start_subagent(self, subagent_id: str) -> None:
        if subagent_id in self._active_subagents:
            self._active_subagents[subagent_id].state = SubagentState.RUNNING
            self._active_subagents[subagent_id].started_at = time.time()

    def complete_subagent(self, subagent_id: str, output: Any = None) -> None:
        if subagent_id in self._active_subagents:
            result = self._active_subagents.pop(subagent_id)
            result.state = SubagentState.COMPLETED
            result.output = output
            result.completed_at = time.time()
            self._completed_subagents[subagent_id] = result
            self._stats["total_completed"] += 1

    def fail_subagent(self, subagent_id: str, error: str) -> None:
        if subagent_id in self._active_subagents:
            result = self._active_subagents.pop(subagent_id)
            result.state = SubagentState.FAILED
            result.error = error
            result.completed_at = time.time()
            self._completed_subagents[subagent_id] = result
            self._stats["total_failed"] += 1

    def timeout_subagent(self, subagent_id: str) -> None:
        if subagent_id in self._active_subagents:
            result = self._active_subagents.pop(subagent_id)
            result.state = SubagentState.TIMED_OUT
            result.completed_at = time.time()
            self._completed_subagents[subagent_id] = result
            self._stats["total_timed_out"] += 1

    def cancel_subagent(self, subagent_id: str) -> None:
        if subagent_id in self._active_subagents:
            result = self._active_subagents.pop(subagent_id)
            result.state = SubagentState.CANCELLED
            result.completed_at = time.time()
            self._completed_subagents[subagent_id] = result

    def get_subagent(self, subagent_id: str) -> Optional[SubagentResult]:
        if subagent_id in self._active_subagents:
            return self._active_subagents[subagent_id]
        return self._completed_subagents.get(subagent_id)

    def get_active_subagents(self, parent_id: Optional[str] = None) -> List[SubagentResult]:
        results = list(self._active_subagents.values())
        if parent_id:
            results = [r for r in results if r.parent_id == parent_id]
        return results

    def get_children(self, parent_id: str) -> List[SubagentResult]:
        children = []
        for r in self._completed_subagents.values():
            if r.parent_id == parent_id:
                children.append(r)
        for r in self._active_subagents.values():
            if r.parent_id == parent_id:
                children.append(r)
        return children

    def check_stale_files(self, parent_id: str) -> List[Dict[str, Any]]:
        children = self.get_children(parent_id)
        stale = []
        parent_files_read = set()
        child_files_written = set()

        from sparkai.agent.agent_file_state import get_file_state_engine
        file_state = get_file_state_engine()
        for access in file_state._access_log.get(parent_id, []):
            parent_files_read.add(access.file_path)

        for child in children:
            child_files_written.update(child.files_written)

        for f in parent_files_read & child_files_written:
            stale.append({
                "file": f,
                "reason": "Child subagent modified a file the parent previously read",
            })
        return stale

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "active_subagents": len(self._active_subagents),
            "completed_subagents": len(self._completed_subagents),
            "max_spawn_depth": self.MAX_SPAWN_DEPTH,
            "max_concurrent": self.MAX_CONCURRENT_SUBAGENTS,
        }


_global_spawner: Optional[SubagentSpawner] = None


def get_subagent_spawner() -> SubagentSpawner:
    global _global_spawner
    if _global_spawner is None:
        _global_spawner = SubagentSpawner()
    return _global_spawner


def reset_subagent_spawner() -> None:
    global _global_spawner
    _global_spawner = None
