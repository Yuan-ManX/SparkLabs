"""
SparkAI Agent - Tool Executor

Execution engine for agent tools with validation, chaining,
caching, and result processing. The executor bridges the gap
between tool definitions and actual game engine operations.

Execution pipeline:
  1. Validate tool parameters against schema
  2. Check pre-conditions (hooks, rules)
  3. Execute the tool handler
  4. Process and validate the result
  5. Cache the result for future use
  6. Emit execution events
  7. Record execution history

Tool chains enable sequential execution of multiple tools
where each tool's output feeds into the next tool's input.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from sparkai.agent.toolkit import Tool, ToolRegistry, ToolParameter


class ExecutionStatus(Enum):
    PENDING = "pending"
    VALIDATING = "validating"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class ExecutionResult:
    """Result of a single tool execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    status: ExecutionStatus = ExecutionStatus.PENDING
    input_params: Dict[str, Any] = field(default_factory=dict)
    output: Any = None
    error: Optional[str] = None
    duration_ms: float = 0.0
    from_cache: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "status": self.status.value,
            "input_params": self.input_params,
            "output": str(self.output)[:500] if self.output else None,
            "error": self.error,
            "duration_ms": self.duration_ms,
            "from_cache": self.from_cache,
            "timestamp": self.timestamp,
        }


@dataclass
class ChainStep:
    """A step in a tool execution chain."""
    tool_name: str
    input_mapping: Dict[str, str] = field(default_factory=dict)
    constant_params: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class ChainResult:
    """Result of a tool chain execution."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    steps: List[ExecutionResult] = field(default_factory=list)
    status: ExecutionStatus = ExecutionStatus.PENDING
    total_duration_ms: float = 0.0
    final_output: Any = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status.value,
            "step_count": len(self.steps),
            "steps": [s.to_dict() for s in self.steps],
            "total_duration_ms": self.total_duration_ms,
            "final_output": str(self.final_output)[:500] if self.final_output else None,
        }


class ToolExecutor:
    """
    Execution engine for SparkLabs agent tools.

    Provides validated, cached, and traceable tool execution with
    support for tool chains and execution history.

    Features:
    - Parameter validation against tool schemas
    - Result caching with configurable TTL
    - Tool chain execution with output mapping
    - Execution history and replay
    - Pre/post execution hooks
    - Timeout and cancellation support
    """

    def __init__(
        self,
        registry: Optional[ToolRegistry] = None,
        cache_ttl: float = 300.0,
        max_history: int = 500,
        default_timeout: float = 30.0,
    ):
        self._registry = registry or ToolRegistry()
        self._cache_ttl = cache_ttl
        self._max_history = max_history
        self._default_timeout = default_timeout
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._history: List[ExecutionResult] = []
        self._pre_hooks: List[Callable] = []
        self._post_hooks: List[Callable] = []
        self._stats = {
            "total_executions": 0,
            "successful": 0,
            "failed": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_duration_ms": 0.0,
        }

    @property
    def registry(self) -> ToolRegistry:
        return self._registry

    def add_pre_hook(self, hook: Callable) -> None:
        """Add a pre-execution hook. Hook receives (tool_name, params) and can modify params."""
        self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable) -> None:
        """Add a post-execution hook. Hook receives (tool_name, result)."""
        self._post_hooks.append(hook)

    def validate_params(self, tool: Tool, params: Dict[str, Any]) -> List[str]:
        """Validate parameters against the tool schema. Returns list of errors."""
        errors = []
        param_map = {p.name: p for p in tool.parameters}

        for param_def in tool.parameters:
            if param_def.required and param_def.name not in params:
                if param_def.default is None:
                    errors.append(f"Missing required parameter: {param_def.name}")

        for key, value in params.items():
            if key not in param_map:
                continue
            param_def = param_map[key]
            type_checks = {
                "string": lambda v: isinstance(v, str),
                "number": lambda v: isinstance(v, (int, float)),
                "integer": lambda v: isinstance(v, int),
                "boolean": lambda v: isinstance(v, bool),
                "array": lambda v: isinstance(v, list),
                "object": lambda v: isinstance(v, dict),
            }
            checker = type_checks.get(param_def.type)
            if checker and not checker(value):
                errors.append(
                    f"Parameter '{key}' expected type {param_def.type}, got {type(value).__name__}"
                )

        return errors

    async def execute(
        self,
        tool_name: str,
        params: Dict[str, Any],
        use_cache: bool = True,
        timeout: Optional[float] = None,
    ) -> ExecutionResult:
        """
        Execute a tool by name with the given parameters.
        """
        result = ExecutionResult(
            tool_name=tool_name,
            input_params=params,
        )
        start_time = time.time()

        self._stats["total_executions"] += 1

        tool = self._registry.get(tool_name)
        if not tool:
            result.status = ExecutionStatus.FAILED
            result.error = f"Tool '{tool_name}' not found"
            self._stats["failed"] += 1
            self._add_to_history(result)
            return result

        validation_errors = self.validate_params(tool, params)
        if validation_errors:
            result.status = ExecutionStatus.FAILED
            result.error = f"Validation errors: {'; '.join(validation_errors)}"
            self._stats["failed"] += 1
            self._add_to_history(result)
            return result

        cache_key = self._make_cache_key(tool_name, params)
        if use_cache:
            cached = self._get_from_cache(cache_key)
            if cached is not None:
                result.status = ExecutionStatus.COMPLETED
                result.output = cached
                result.from_cache = True
                result.duration_ms = (time.time() - start_time) * 1000
                self._stats["cache_hits"] += 1
                self._stats["successful"] += 1
                self._add_to_history(result)
                return result
            self._stats["cache_misses"] += 1

        for hook in self._pre_hooks:
            try:
                modified = hook(tool_name, params)
                if isinstance(modified, dict):
                    params = modified
            except Exception:
                pass

        result.status = ExecutionStatus.RUNNING

        try:
            actual_timeout = timeout or self._default_timeout
            output = await asyncio.wait_for(
                tool.execute(params),
                timeout=actual_timeout,
            )

            result.status = ExecutionStatus.COMPLETED
            result.output = output
            result.duration_ms = (time.time() - start_time) * 1000
            self._stats["successful"] += 1
            self._stats["total_duration_ms"] += result.duration_ms

            if use_cache:
                self._add_to_cache(cache_key, output)

            for hook in self._post_hooks:
                try:
                    hook(tool_name, result)
                except Exception:
                    pass

        except asyncio.TimeoutError:
            result.status = ExecutionStatus.FAILED
            result.error = f"Tool execution timed out after {actual_timeout}s"
            result.duration_ms = (time.time() - start_time) * 1000
            self._stats["failed"] += 1

        except Exception as e:
            result.status = ExecutionStatus.FAILED
            result.error = str(e)
            result.duration_ms = (time.time() - start_time) * 1000
            self._stats["failed"] += 1

        self._add_to_history(result)
        return result

    async def execute_chain(
        self,
        steps: List[ChainStep],
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> ChainResult:
        """
        Execute a chain of tools sequentially, where each step's output
        feeds into the next step's input via input_mapping.
        """
        chain_result = ChainResult()
        chain_start = time.time()
        context = dict(initial_context or {})

        for step in steps:
            params = dict(step.constant_params)

            for target_key, source_key in step.input_mapping.items():
                if source_key in context:
                    params[target_key] = context[source_key]

            step_result = await self.execute(step.tool_name, params, use_cache=False)
            chain_result.steps.append(step_result)

            if step_result.status == ExecutionStatus.COMPLETED:
                if isinstance(step_result.output, dict):
                    context.update(step_result.output)
                context[f"_last_{step.tool_name}"] = step_result.output
            else:
                chain_result.status = ExecutionStatus.FAILED
                chain_result.total_duration_ms = (time.time() - chain_start) * 1000
                return chain_result

        chain_result.status = ExecutionStatus.COMPLETED
        chain_result.total_duration_ms = (time.time() - chain_start) * 1000
        chain_result.final_output = context
        return chain_result

    async def execute_batch(
        self,
        executions: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> List[ExecutionResult]:
        """Execute multiple tools concurrently with a concurrency limit."""
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _run(exec_spec: Dict[str, Any]) -> ExecutionResult:
            async with semaphore:
                return await self.execute(
                    exec_spec.get("tool_name", ""),
                    exec_spec.get("params", {}),
                    use_cache=exec_spec.get("use_cache", True),
                    timeout=exec_spec.get("timeout"),
                )

        results = await asyncio.gather(*[_run(spec) for spec in executions])
        return list(results)

    def _make_cache_key(self, tool_name: str, params: Dict[str, Any]) -> str:
        sorted_params = sorted(params.items())
        return f"{tool_name}:{sorted_params}"

    def _get_from_cache(self, key: str) -> Any:
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.time() - entry["timestamp"] > self._cache_ttl:
            del self._cache[key]
            return None
        return entry["value"]

    def _add_to_cache(self, key: str, value: Any) -> None:
        self._cache[key] = {"value": value, "timestamp": time.time()}
        if len(self._cache) > 1000:
            oldest_key = min(self._cache, key=lambda k: self._cache[k]["timestamp"])
            del self._cache[oldest_key]

    def _add_to_history(self, result: ExecutionResult) -> None:
        self._history.append(result)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

    def get_history(
        self,
        tool_name: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        results = self._history
        if tool_name:
            results = [r for r in results if r.tool_name == tool_name]
        if status:
            results = [r for r in results if r.status == status]
        return [r.to_dict() for r in results[-limit:]]

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._stats,
            "cache_size": len(self._cache),
            "history_size": len(self._history),
            "avg_duration_ms": (
                self._stats["total_duration_ms"] / self._stats["successful"]
                if self._stats["successful"] > 0
                else 0.0
            ),
        }

    def clear_cache(self) -> int:
        count = len(self._cache)
        self._cache.clear()
        return count

    def clear_history(self) -> None:
        self._history.clear()
