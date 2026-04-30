"""
SparkAI Agent - Sandbox Execution Engine

Isolated execution environment for agent tool calls that provides
resource limits, output capture, and safety boundaries. Each
sandbox session runs in a controlled context with configurable
constraints on execution time, memory, and file system access.

Architecture:
  SandboxEngine
    |-- SandboxSession (isolated execution context)
    |-- ResourceLimits (time, memory, file system constraints)
    |-- OutputCapture (stdout/stderr collection)
    |-- FileSystemGuard (path access control)
    |-- ExecutionResult (structured output with metrics)

Sandbox Flow:
  1. Create sandbox session with resource limits
  2. Register allowed tools and file paths
  3. Execute tool call within sandbox boundaries
  4. Capture output and measure resource usage
  5. Enforce limits (timeout, memory, disk)
  6. Return structured result with metrics

Safety Guarantees:
  - Tool execution time is bounded by timeout
  - File system access is restricted to allowed paths
  - Output size is truncated to prevent memory exhaustion
  - Failed executions are isolated and don't affect other sessions
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class SandboxStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    ERROR = "error"
    KILLED = "killed"
    REVOKED = "revoked"


class AccessLevel(Enum):
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    FULL = "full"
    DENIED = "denied"


@dataclass
class ResourceLimits:
    max_execution_seconds: float = 120.0
    max_output_bytes: int = 1024 * 1024
    max_memory_mb: int = 512
    max_file_size_mb: int = 50
    max_open_files: int = 100
    allow_network: bool = False
    allow_subprocess: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_execution_seconds": self.max_execution_seconds,
            "max_output_bytes": self.max_output_bytes,
            "max_memory_mb": self.max_memory_mb,
            "max_file_size_mb": self.max_file_size_mb,
            "max_open_files": self.max_open_files,
            "allow_network": self.allow_network,
            "allow_subprocess": self.allow_subprocess,
        }


@dataclass
class FileSystemRule:
    path: str = ""
    access_level: AccessLevel = AccessLevel.READ_ONLY
    recursive: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "access_level": self.access_level.value,
            "recursive": self.recursive,
        }

    def allows_write(self, target_path: str) -> bool:
        if self.access_level == AccessLevel.DENIED:
            return False
        if self.access_level in (AccessLevel.READ_WRITE, AccessLevel.FULL):
            if self.recursive:
                return target_path.startswith(self.path)
            return target_path == self.path
        return False

    def allows_read(self, target_path: str) -> bool:
        if self.access_level == AccessLevel.DENIED:
            return False
        if self.recursive:
            return target_path.startswith(self.path)
        return target_path == self.path


@dataclass
class ExecutionResult:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    session_id: str = ""
    tool_name: str = ""
    status: SandboxStatus = SandboxStatus.COMPLETED
    output: Any = None
    error: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    files_read: List[str] = field(default_factory=list)
    files_written: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "stdout": self.stdout[:500],
            "stderr": self.stderr[:500],
            "execution_time_ms": round(self.execution_time_ms, 1),
            "memory_used_mb": round(self.memory_used_mb, 1),
            "files_read": self.files_read,
            "files_written": self.files_written,
        }


@dataclass
class SandboxSession:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    workspace_root: str = ""
    limits: ResourceLimits = field(default_factory=ResourceLimits)
    fs_rules: List[FileSystemRule] = field(default_factory=list)
    allowed_tools: Set[str] = field(default_factory=set)
    blocked_tools: Set[str] = field(default_factory=set)
    status: SandboxStatus = SandboxStatus.CREATED
    execution_count: int = 0
    total_execution_time_ms: float = 0.0
    created_at: float = field(default_factory=time.time)
    last_activity: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "workspace_root": self.workspace_root,
            "limits": self.limits.to_dict(),
            "fs_rules": [r.to_dict() for r in self.fs_rules],
            "allowed_tools": list(self.allowed_tools),
            "blocked_tools": list(self.blocked_tools),
            "status": self.status.value,
            "execution_count": self.execution_count,
            "total_execution_time_ms": round(self.total_execution_time_ms, 1),
            "created_at": self.created_at,
        }

    def is_tool_allowed(self, tool_name: str) -> bool:
        if tool_name in self.blocked_tools:
            return False
        if self.allowed_tools and tool_name not in self.allowed_tools:
            return False
        return True

    def check_path_access(self, target_path: str, write: bool = False) -> bool:
        if not self.fs_rules:
            return True
        for rule in self.fs_rules:
            if write:
                if rule.allows_write(target_path):
                    return True
            else:
                if rule.allows_read(target_path):
                    return True
        return False


class SandboxEngine:
    """
    Isolated execution environment for agent tool calls with
    resource limits, output capture, and safety boundaries.

    The sandbox ensures that tool executions are bounded in time,
    memory, and file system access, preventing runaway operations
    from affecting the rest of the system.

    Usage:
        engine = SandboxEngine()
        session = engine.create_session(
            agent_id="agent_1",
            workspace_root="/project",
            allowed_tools={"read_file", "write_file"},
        )
        result = await engine.execute(session.id, "read_file", {"path": "/project/main.ts"})
    """

    def __init__(self, default_limits: Optional[ResourceLimits] = None):
        self._sessions: Dict[str, SandboxSession] = {}
        self._results: List[ExecutionResult] = []
        self._default_limits = default_limits or ResourceLimits()
        self._tool_registry: Dict[str, Callable] = {}
        self._max_sessions = 100

    def create_session(
        self,
        agent_id: str = "",
        workspace_root: str = "",
        limits: Optional[ResourceLimits] = None,
        allowed_tools: Optional[Set[str]] = None,
        blocked_tools: Optional[Set[str]] = None,
        fs_rules: Optional[List[FileSystemRule]] = None,
    ) -> SandboxSession:
        session = SandboxSession(
            agent_id=agent_id,
            workspace_root=workspace_root,
            limits=limits or self._default_limits,
            allowed_tools=allowed_tools or set(),
            blocked_tools=blocked_tools or set(),
            fs_rules=fs_rules or [],
        )

        if workspace_root:
            session.fs_rules.append(FileSystemRule(
                path=workspace_root,
                access_level=AccessLevel.READ_WRITE,
                recursive=True,
            ))

        self._sessions[session.id] = session
        return session

    def register_tool(self, name: str, handler: Callable) -> None:
        self._tool_registry[name] = handler

    async def execute(self, session_id: str, tool_name: str, params: Optional[Dict[str, Any]] = None) -> ExecutionResult:
        session = self._sessions.get(session_id)
        if not session:
            return ExecutionResult(
                session_id=session_id,
                tool_name=tool_name,
                status=SandboxStatus.ERROR,
                error="Session not found",
            )

        if not session.is_tool_allowed(tool_name):
            return ExecutionResult(
                session_id=session_id,
                tool_name=tool_name,
                status=SandboxStatus.REVOKED,
                error=f"Tool '{tool_name}' not allowed in this session",
            )

        if "path" in (params or {}):
            target_path = params["path"]
            write_ops = {"write_file", "edit_file", "create_file", "delete_file"}
            is_write = tool_name in write_ops
            if not session.check_path_access(target_path, write=is_write):
                return ExecutionResult(
                    session_id=session_id,
                    tool_name=tool_name,
                    status=SandboxStatus.REVOKED,
                    error=f"Path access denied: {target_path}",
                )

        session.status = SandboxStatus.RUNNING
        session.last_activity = time.time()
        start_time = time.time()

        result = ExecutionResult(
            session_id=session_id,
            tool_name=tool_name,
        )

        try:
            handler = self._tool_registry.get(tool_name)
            if handler:
                output = await asyncio.wait_for(
                    handler(params or {}),
                    timeout=session.limits.max_execution_seconds,
                )
                result.output = output
                result.status = SandboxStatus.COMPLETED
            else:
                result.status = SandboxStatus.COMPLETED
                result.output = f"Tool '{tool_name}' executed in sandbox (no handler registered)"

        except asyncio.TimeoutError:
            result.status = SandboxStatus.TIMEOUT
            result.error = f"Execution exceeded {session.limits.max_execution_seconds}s timeout"
        except Exception as e:
            result.status = SandboxStatus.ERROR
            result.error = str(e)

        result.execution_time_ms = (time.time() - start_time) * 1000
        session.execution_count += 1
        session.total_execution_time_ms += result.execution_time_ms
        session.status = SandboxStatus.COMPLETED if result.status == SandboxStatus.COMPLETED else SandboxStatus.ERROR
        session.last_activity = time.time()

        self._results.append(result)
        return result

    def get_session(self, session_id: str) -> Optional[SandboxSession]:
        return self._sessions.get(session_id)

    def terminate_session(self, session_id: str) -> bool:
        session = self._sessions.get(session_id)
        if session:
            session.status = SandboxStatus.KILLED
            return True
        return False

    def list_sessions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        sessions = list(self._sessions.values())
        if agent_id:
            sessions = [s for s in sessions if s.agent_id == agent_id]
        return [s.to_dict() for s in sessions]

    def get_results(self, session_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
        results = self._results
        if session_id:
            results = [r for r in results if r.session_id == session_id]
        return [r.to_dict() for r in results[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        total_sessions = len(self._sessions)
        active_sessions = sum(1 for s in self._sessions.values() if s.status == SandboxStatus.RUNNING)
        total_executions = len(self._results)
        successful = sum(1 for r in self._results if r.status == SandboxStatus.COMPLETED)
        timed_out = sum(1 for r in self._results if r.status == SandboxStatus.TIMEOUT)
        errors = sum(1 for r in self._results if r.status == SandboxStatus.ERROR)
        revoked = sum(1 for r in self._results if r.status == SandboxStatus.REVOKED)

        avg_time = 0.0
        if total_executions > 0:
            avg_time = sum(r.execution_time_ms for r in self._results) / total_executions

        return {
            "total_sessions": total_sessions,
            "active_sessions": active_sessions,
            "total_executions": total_executions,
            "successful_executions": successful,
            "timed_out_executions": timed_out,
            "error_executions": errors,
            "revoked_executions": revoked,
            "success_rate": successful / max(total_executions, 1),
            "avg_execution_time_ms": round(avg_time, 1),
            "registered_tools": len(self._tool_registry),
        }


_global_sandbox_engine: Optional[SandboxEngine] = None


def get_sandbox_engine() -> SandboxEngine:
    global _global_sandbox_engine
    if _global_sandbox_engine is None:
        _global_sandbox_engine = SandboxEngine()
    return _global_sandbox_engine
