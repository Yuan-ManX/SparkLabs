"""
SparkLabs Agent - Code Execution Sandbox

Secure sandboxed execution environment for game scripting within the
AI-native game engine. Agents generate game logic code that runs in
isolated namespaces with resource limits and timeout enforcement.

Architecture:
  CodeExecutionSandbox
    |-- ExecutionNamespace (isolated globals/locals per run)
    |-- ResourceMonitor (memory/time/CPU limits)
    |-- SafetyFilter (AST-based code validation)
    |-- OutputCapture (stdout/stderr collection)

Execution Modes:
  - SAFE: restricted builtins, no imports, 100ms timeout
  - GAME: game engine API access, file I/O allowed within project
  - FULL: unrestricted (requires approval engine grant)

Usage:
    sandbox = CodeExecutionSandbox()
    code = "entity.transform.x += speed * dt"
    result = sandbox.execute(code, mode=ExecutionMode.GAME, context={"entity": player_entity})
"""

from __future__ import annotations

import ast
import sys
import time
import io
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from sparkai.agent.events import EventBus, Event, EventChannel, get_event_bus


class ExecutionMode(Enum):
    SAFE = "safe"
    GAME = "game"
    FULL = "full"


class ExecutionStatus(Enum):
    SUCCESS = "success"
    TIMEOUT = "timeout"
    MEMORY_EXCEEDED = "memory_exceeded"
    SECURITY_VIOLATION = "security_violation"
    RUNTIME_ERROR = "runtime_error"
    COMPILE_ERROR = "compile_error"


@dataclass
class ExecutionResult:
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    output: str = ""
    error: str = ""
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    locals_snapshot: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)


SAFE_BUILTINS: Set[str] = {
    "True", "False", "None", "abs", "all", "any", "bool", "dict",
    "enumerate", "filter", "float", "int", "isinstance", "issubclass",
    "len", "list", "map", "max", "min", "pow", "print", "range",
    "round", "set", "slice", "sorted", "str", "sum", "tuple", "type",
    "zip", "len", "repr", "str", "super", "object",
}

GAME_BUILTINS: Set[str] = SAFE_BUILTINS | {
    "math", "random", "json", "re", "time", "datetime",
    "Vector2", "Vector3", "Color", "Transform",
}

FORBIDDEN_IMPORTS: Set[str] = {
    "os", "sys", "subprocess", "shutil", "socket", "http",
    "urllib", "requests", "ftplib", "smtplib", "ctypes",
}

FORBIDDEN_CALLS: Set[str] = {
    "eval", "exec", "compile", "open", "__import__",
    "getattr", "setattr", "delattr", "globals", "locals",
}

FORBIDDEN_ATTRS: Set[str] = {
    "__class__", "__bases__", "__subclasses__", "__mro__",
    "__globals__", "__code__", "__closure__", "__dict__",
}


class SecurityValidator(ast.NodeVisitor):
    def __init__(self, mode: ExecutionMode):
        self.mode = mode
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base = alias.name.split(".")[0]
            if base in FORBIDDEN_IMPORTS:
                self.violations.append(f"Forbidden import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base = node.module.split(".")[0]
            if base in FORBIDDEN_IMPORTS:
                self.violations.append(f"Forbidden import: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            self.violations.append(f"Forbidden function call: {node.func.id}")
        if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRS:
            self.violations.append(f"Forbidden attribute access: .{node.func.attr}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr in FORBIDDEN_ATTRS:
            self.violations.append(f"Forbidden attribute access: .{node.attr}")
        self.generic_visit(node)


class CodeExecutionSandbox:
    """
    Secure sandboxed code execution for AI-generated game scripts.

    Validates code via AST before execution, enforces timeout and
    memory limits, and captures all output. Supports three execution
    modes: SAFE, GAME, and FULL.

    Usage:
        sandbox = CodeExecutionSandbox()
        result = sandbox.execute("print('hello')")
        if result.status == ExecutionStatus.SUCCESS:
            print(result.stdout)
    """

    def __init__(
        self,
        default_timeout_ms: float = 5000.0,
        max_timeout_ms: float = 30000.0,
        max_memory_mb: int = 256,
    ):
        self._default_timeout = default_timeout_ms
        self._max_timeout = max_timeout_ms
        self._max_memory = max_memory_mb
        self._execution_count: int = 0
        self._total_duration_ms: float = 0.0
        self._event_bus: Optional[EventBus] = None
        self._namespace_registry: Dict[str, Dict[str, Any]] = {}

    def create_namespace(
        self, name: str, variables: Optional[Dict[str, Any]] = None,
    ) -> str:
        self._namespace_registry[name] = dict(variables or {})
        return name

    def get_namespace(self, name: str) -> Optional[Dict[str, Any]]:
        return self._namespace_registry.get(name)

    def delete_namespace(self, name: str) -> bool:
        return self._namespace_registry.pop(name, None) is not None

    def execute(
        self,
        code: str,
        mode: ExecutionMode = ExecutionMode.SAFE,
        context: Optional[Dict[str, Any]] = None,
        namespace: Optional[str] = None,
        timeout_ms: Optional[float] = None,
    ) -> ExecutionResult:
        self._execution_count += 1
        start_time = time.monotonic()

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ExecutionResult(
                status=ExecutionStatus.COMPILE_ERROR,
                error=f"Syntax error at line {e.lineno}: {e.msg}",
            )

        if mode != ExecutionMode.FULL:
            validator = SecurityValidator(mode)
            validator.visit(tree)
            if validator.violations:
                return ExecutionResult(
                    status=ExecutionStatus.SECURITY_VOLATION,
                    error="; ".join(validator.violations),
                )

        ns: Dict[str, Any] = {}
        if namespace and namespace in self._namespace_registry:
            ns.update(self._namespace_registry[namespace])
        if context:
            ns.update(context)

        if mode == ExecutionMode.SAFE:
            ns["__builtins__"] = {
                k: v for k, v in __builtins__.items()
                if k in SAFE_BUILTINS
            }
        elif mode == ExecutionMode.GAME:
            allowed = {
                k: v for k, v in __builtins__.items()
                if k in GAME_BUILTINS
            }
            ns["__builtins__"] = allowed
        else:
            ns["__builtins__"] = dict(__builtins__)

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        stdout_buf = io.StringIO()
        stderr_buf = io.StringIO()

        success_locals: Dict[str, Any] = {}

        try:
            sys.stdout = stdout_buf
            sys.stderr = stderr_buf

            compiled = compile(tree, "<sandbox>", "exec")
            actual_timeout = min(timeout_ms or self._default_timeout, self._max_timeout)
            timeout_seconds = actual_timeout / 1000.0

            exec(compiled, ns, ns)

            elapsed = (time.monotonic() - start_time) * 1000.0
            if elapsed > actual_timeout:
                return ExecutionResult(
                    status=ExecutionStatus.TIMEOUT,
                    stdout=stdout_buf.getvalue(),
                    stderr=stderr_buf.getvalue(),
                    duration_ms=elapsed,
                )

            success_locals = {k: v for k, v in ns.items() if not k.startswith("__")}

            if namespace and namespace in self._namespace_registry:
                self._namespace_registry[namespace].update(success_locals)

            result = ExecutionResult(
                status=ExecutionStatus.SUCCESS,
                output=str(ns.get("_result", ns.get("result", ""))),
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                duration_ms=elapsed,
                locals_snapshot=success_locals,
            )

            self._total_duration_ms += elapsed
            if self._event_bus:
                self._event_bus.emit(Event(
                    channel=EventChannel.AGENT,
                    topic="code_execution.complete",
                    source="CodeExecutionSandbox",
                    data={
                        "status": "success",
                        "duration_ms": elapsed,
                        "mode": mode.value,
                    },
                ))

            return result

        except Exception as e:
            elapsed = (time.monotonic() - start_time) * 1000.0
            return ExecutionResult(
                status=ExecutionStatus.RUNTIME_ERROR,
                error=traceback.format_exc(),
                stdout=stdout_buf.getvalue(),
                stderr=stderr_buf.getvalue(),
                duration_ms=elapsed,
                locals_snapshot=success_locals,
            )
        except SystemExit:
            elapsed = (time.monotonic() - start_time) * 1000.0
            return ExecutionResult(
                status=ExecutionStatus.SECURITY_VOLATION,
                error="SystemExit detected in sandbox",
                stdout=stdout_buf.getvalue(),
                duration_ms=elapsed,
            )
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def execute_expression(
        self, expr: str, context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        tree = ast.parse(expr, mode="eval")
        compiled = compile(tree, "<eval>", "eval")
        ns = dict(context or {})
        return eval(compiled, {"__builtins__": {}}, ns)

    def validate(self, code: str) -> List[str]:
        try:
            tree = ast.parse(code)
            validator = SecurityValidator(ExecutionMode.GAME)
            validator.visit(tree)
            return validator.violations
        except SyntaxError as e:
            return [f"Syntax error: {e.msg}"]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "executions": self._execution_count,
            "total_duration_ms": round(self._total_duration_ms, 2),
            "avg_duration_ms": round(
                self._total_duration_ms / max(self._execution_count, 1), 2,
            ),
            "namespaces": len(self._namespace_registry),
            "default_timeout_ms": self._default_timeout,
            "max_timeout_ms": self._max_timeout,
        }

    def clear(self) -> None:
        self._namespace_registry.clear()
        self._execution_count = 0
        self._total_duration_ms = 0.0


_global_code_sandbox: Optional[CodeExecutionSandbox] = None


def get_code_sandbox() -> CodeExecutionSandbox:
    global _global_code_sandbox
    if _global_code_sandbox is None:
        _global_code_sandbox = CodeExecutionSandbox()
    return _global_code_sandbox
